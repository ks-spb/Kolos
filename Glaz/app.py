"""
Главный класс приложения Glaz
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from PIL import Image, ImageTk
import time
import os
import math
import json
import numpy as np
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass

try:
    import cv2
    _HAS_OPENCV = True
    _OPENCV_ERROR = None
except Exception as e:
    _HAS_OPENCV = False
    _OPENCV_ERROR = str(e)

from capture import ScreenCapture
from image_processor import ImageProcessor, DetectedObject, LineBasedDetector, ObjectDetector
from event_bus import EventBus
from loupe import LoupeController
from objects_repository import ObjectsRepository
from recognition_state import RecognitionIdle, RecognitionState, RecognitionStep1
from utils import (
    get_downloads_path,
    generate_filename,
    get_cursor_pos,
    set_cursor_pos,
    compute_lines_to_delete,
    decide_processing_schedule,
)
from kolos_ansi import line_looks_red_in_terminal, line_looks_user_input, strip_sgr
from kolos_digits_hint import KOLOS_DIGITS_HINT_RU
from kolos_subprocess import KolosSubprocessController, project_root_from_glaz_file
from cv_core.glaz_ipc import (
    read_scan_request,
    write_last_confirmed_target,
    write_scan_results,
    ScanResults,
    ScanResultItem,
)

from loupe_signature import LoupeSignatureAnalyzer

# Путь к файлу отладочных логов (инструментация)
_DEBUG_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cursor", "debug.log")


@dataclass
class ProcessingResult:
    """Результат фоновой обработки кадра."""
    peaks_image: Image.Image
    objects: list[DetectedObject]
    timings_ms: dict[str, float]
    detector_mode: str


class ScreenCaptureApp:
    """Главный класс приложения для захвата и анализа экрана."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Glaz - Захват экрана")
        
        # Компоненты приложения
        self.capture = ScreenCapture()
        self._object_detector: ObjectDetector = LineBasedDetector()
        self._event_bus = EventBus()
        self._objects_repo = ObjectsRepository()

        # Подписчики на события (паттерн Observer)
        self._event_bus.subscribe("capture_error", self._on_capture_error_event)
        self._event_bus.subscribe("object_recognized", self._on_object_recognized_event)

        # Размещаем окно на мониторе 2 и разворачиваем на весь экран
        self._setup_window_position()
        self.loupe_controller: LoupeController = None  # Инициализируется после создания canvas
        
        # Текущие данные
        self.current_image: Image.Image = None
        self.current_peaks_image: Image.Image = None
        self.current_scale = 1.0
        
        # Переменные для настроек
        self.peaks_threshold = tk.IntVar(value=100)
        self.peaks_scale = tk.IntVar(value=100)
        self.peaks_invert = tk.BooleanVar(value=False)
        self.segment_peak_threshold = tk.IntVar(value=3)  # минимум подряд пиковых пикселей для зажигания сегмента
        
        # Переменные для PhotoImage (предотвращение сборки мусора)
        self.photo = None
        self.peaks_photo = None

        # UI render throttling (ускорение без влияния на качество детекции):
        # - логика обработки/распознавания работает как прежде
        # - ограничиваем только частоту перерисовки превью (Tk)
        self._render_interval_screenshot_s: float = 0.25  # 4 FPS
        self._render_interval_peaks_s: float = 0.25  # 4 FPS
        self._last_render_screenshot_time: float = 0.0
        self._last_render_peaks_time: float = 0.0
        self._screenshot_canvas_image_id: int | None = None
        self._peaks_canvas_image_id: int | None = None
        self._screenshot_preview_resample = Image.Resampling.BILINEAR

        # Объекты на Пиках (логика без отдельного экрана)
        self._detected_objects: list[DetectedObject] = []
        # Два словаря подписей: полные (исторические) и уменьшенные (используются для определения)
        self._full_signature_to_ids, self._zoomed_signature_to_ids, self._next_refined_id = self._objects_repo.load()
        self._object_id_to_refined: dict[int, int] = {}
        self._last_hovered_object_id: int | None = None
        
        # Состояние процесса определения объекта (паттерн State: idle -> step1 -> idle)
        self._recognition_state: RecognitionState = RecognitionIdle()
        self._zoomed_signature_temp: tuple[int, ...] = ()  # временная уменьшенная подпись (шаг 1)
        self._zoomed_match_count: int = 0  # количество совпадений на шаге 1
        
        # Радиус большого круга в лупе (пиксели отображаемой лупы; лупа 50x50)
        # r_large = 12 * sqrt(2) ≈ 16.97 — описанный круг для квадрата 24x24
        self._loupe_big_circle_radius = 12 * math.sqrt(2)
        # Эффективный размер лупы (масштаб); 100 = стандарт (loupe_size), >100 = отдаление, <100 = приближение
        self._loupe_size_effective: int = 100
        # Задержка стабильности курсора (с) перед авто-центрированием
        self._cursor_stable_delay = 0.5
        # Допуск при сравнении подписей: отличие > этого порога (0.2 = 20%) — другой объект
        self._signature_match_max_pct = 0.2
        # Удержание курсора в центре объекта на время определения (чтобы не сдвинул мышь)
        self._cursor_hold_position: tuple[int, int] | None = None
        self._cursor_hold_until: float = 0.0
        self._cursor_hold_after_center = 1.0  # удержание курсора после авто-центрирования (с)
        self._cursor_center_target: tuple[int, int] | None = None  # ожидаемая точка центрирования
        self._cursor_center_tolerance_px = 2  # допуск подтверждения центрирования
        self._cursor_centered_confirmed = False  # курсор подтверждён в центре объекта
        
        # Отслеживание стабильности курсора (ждём пока пользователь перестанет двигать мышь)
        self._last_cursor_pos: tuple[int, int] | None = None  # последняя позиция курсора
        self._cursor_stable_since: float | None = None  # время когда курсор стал стабильным
        self._object_already_recognized: bool = False  # объект уже определён в текущей сессии наведения
        # Частоты работы (умный режим): idle 4–6 FPS, step1 быстрее
        self._idle_interval_s: float = 0.20  # 5 FPS
        self._step1_interval_s: float = 0.08  # ~12.5 FPS
        self._active_interval_s: float = self._idle_interval_s

        # Троттлинг обновления UI
        self._update_frame_interval = self._active_interval_s  # с
        self._last_update_frame_time: float = 0.0
        self._last_processing_log_time: float = 0.0
        # Троттлинг фоновой обработки (пики+детекция) — иначе воркер будет молотить на каждом кадре захвата
        self._processing_interval_s: float = self._active_interval_s
        self._last_processing_request_time: float = 0.0
        # Адаптивный запуск обработки:
        # - в idle при движении мыши обрабатываем редко (heartbeat)
        # - при стабильном курсоре или в step1 — как обычно
        self._idle_processing_period_s: float = 1.5
        self._last_idle_processing_time: float = 0.0
        self._processing_last_cursor_pos: tuple[int, int] | None = None
        self._processing_cursor_stable_since: float | None = None

        # Встроенный Kolos (stdout/stderr → панель справа)
        self._kolos_controller: KolosSubprocessController | None = None
        self._kolos_max_lines: int = 10_000

        # Фоновая обработка full-res: пики + детекция объектов (latest-frame-wins)
        self._processing_executor = ThreadPoolExecutor(max_workers=1)
        self._processing_lock = threading.Lock()
        self._processing_future: Future | None = None
        self._pending_processing_request: tuple[Image.Image, int, bool] | None = None
        self._completed_processing_result: ProcessingResult | None = None

        # Предскан объектов по IPC (latest-request-wins + debounce)
        self._scan_executor = ThreadPoolExecutor(max_workers=1)
        self._scan_lock = threading.Lock()
        self._scan_future: Future | None = None
        self._scan_pending_request_id: str | None = None
        self._scan_last_handled_request_id: str | None = None
        self._scan_last_request_seen_ts: float = 0.0
        self._scan_debounce_sec: float = 1.0
        self._scan_last_run_ts: float = 0.0
        self._scan_signature_analyzer = LoupeSignatureAnalyzer()
        self._scan_last_results: dict[int, tuple[int, bool]] = {}  # refined_id -> (count, is_new_any)

        # Скриншоты лупы при определении объекта
        self._do_screenshots_var = tk.BooleanVar(value=True)
        self._project_dir = os.path.dirname(os.path.abspath(__file__))
        self._screenshots_dir = os.path.join(self._project_dir, "object_screenshots")
        self._contour_screenshots_dir = os.path.join(self._project_dir, "contour_screenshots")
        self._step1_loupe_image: Image.Image | None = None  # копия лупы на шаге 1 (грубое)

        self._setup_ui()
        self._start_kolos_embedded()
        self.root.protocol("WM_DELETE_WINDOW", self._on_root_close)
        self._init_loupe_controller()
        self._setup_hotkeys()
        
        # Автозапуск захвата экрана: по умолчанию выключен.
        # Включение при необходимости: установить переменную окружения GLAZ_AUTOSTART=1
        autostart = os.environ.get("GLAZ_AUTOSTART", "0").strip().lower() in (
            "1",
            "true",
            "yes",
            "y",
            "on",
        )
        if autostart:
            self.root.after(500, self._start_capture)
    
    def _setup_window_position(self):
        """Размещение окна на мониторе 2 в полноэкранном режиме."""
        import mss
        with mss.mss() as sct:
            monitors = sct.monitors
            # monitors[0] - все мониторы вместе, monitors[1] - монитор 1, monitors[2] - монитор 2
            if len(monitors) > 2:
                # Есть монитор 2
                monitor = monitors[2]
                x = monitor['left']
                y = monitor['top']
                # Устанавливаем позицию окна на монитор 2
                self.root.geometry(f"+{x}+{y}")
            else:
                # Только один монитор - используем его
                self.root.geometry("900x850")
        
        # Разворачиваем на весь экран после небольшой задержки
        self.root.after(100, lambda: self.root.state('zoomed'))
    
    def _setup_ui(self):
        """Настройка пользовательского интерфейса."""
        main_container = ttk.Frame(self.root)
        main_container.pack(fill="both", expand=True)
        
        self._main_pane = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        self._main_pane.pack(fill="both", expand=True)
        
        self._left_frame = ttk.Frame(self._main_pane)
        self._main_pane.add(self._left_frame, weight=1)
        
        # Средняя панель: лупа + справка по цифрам Kolos
        self._middle_frame = ttk.Frame(self._main_pane, width=280)
        self._middle_frame.pack_propagate(0)
        self._main_pane.add(self._middle_frame, weight=0)
        
        # Правая панель с таблицами: ширина в 3 раза больше (80+180)*3 ≈ 780, можно менять перетаскиванием
        self._right_frame = ttk.Frame(self._main_pane, width=780)
        self._right_frame.pack_propagate(0)
        self._main_pane.add(self._right_frame, weight=0)
        
        self._setup_monitor_frame()
        self._setup_screenshot_frame()
        self._setup_peaks_frame()
        self._setup_error_frame()
        self._setup_status_bar()
        self._setup_screenshot_previews()
        self._setup_objects_table()
        self._update_objects_table()
        
        self.log_message("Программа запущена. Выберите монитор для захвата скриншотов.")

    def _debug_log(self, message: str, data: dict) -> None:
        """Записать одну строку NDJSON в файл отладочных логов (без изменения логики приложения)."""
        try:
            payload = {"message": message, "data": data, "timestamp": time.time()}
            with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def _setup_monitor_frame(self):
        """Настройка фрейма выбора монитора."""
        monitor_frame = ttk.LabelFrame(self._left_frame, text="Выбор монитора", padding=10)
        monitor_frame.pack(fill="x", padx=10, pady=5)

        controls_row = ttk.Frame(monitor_frame)
        controls_row.pack(fill="x")

        # Выпадающий список мониторов
        monitors = self.capture.get_monitors()
        self.monitor_var = tk.StringVar()
        self.monitor_combo = ttk.Combobox(
            controls_row,
            textvariable=self.monitor_var,
            values=monitors,
            state="readonly"
        )
        self.monitor_combo.pack(side="left", padx=(0, 10))
        self.monitor_combo.bind('<<ComboboxSelected>>', self._on_monitor_selected)
        
        # Устанавливаем Монитор 1 по умолчанию
        if monitors:
            self.monitor_combo.current(0)
            self.capture.selected_monitor = 1
        
        # Кнопка захвата
        self.capture_btn = ttk.Button(
            controls_row,
            text="Захватить экран",
            command=self._start_capture
        )
        self.capture_btn.pack(side="left")
        
        # Кнопка остановки
        self.stop_btn = ttk.Button(
            controls_row,
            text="Остановить",
            command=self._stop_capture,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=(10, 0))

        # Кнопка очистки БД объектов справа от "Остановить"
        self.clear_db_btn = ttk.Button(
            controls_row,
            text="Очистить БД объектов",
            command=self._clear_objects_db
        )
        self.clear_db_btn.pack(side="left", padx=(10, 0))

        # Переключатель скриншотов справа от кнопки очистки БД
        ttk.Checkbutton(
            controls_row,
            text="Делать скриншоты",
            variable=self._do_screenshots_var
        ).pack(side="left", padx=(12, 0))
    
    def _setup_screenshot_frame(self):
        """Настройка фрейма скриншота."""
        image_frame = ttk.LabelFrame(self._left_frame, text="Скриншот", padding=10)
        image_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Область отображения скриншота закреплена слева; справа остаётся пустое место.
        self._screenshot_view_frame = ttk.Frame(image_frame)
        self._screenshot_view_frame.pack(fill="both", expand=True)
        self._screenshot_view_frame.bind("<Configure>", self._on_screenshot_view_resize)

        self.canvas = tk.Canvas(self._screenshot_view_frame, bg="gray")
        self.canvas.pack(side="left", anchor="nw", expand=False)
        
        # Полосы прокрутки
        h_scrollbar = ttk.Scrollbar(image_frame, orient="horizontal", command=self.canvas.xview)
        h_scrollbar.pack(side="bottom", fill="x")
        v_scrollbar = ttk.Scrollbar(image_frame, orient="vertical", command=self.canvas.yview)
        v_scrollbar.pack(side="right", fill="y")
        
        self.canvas.configure(
            xscrollcommand=h_scrollbar.set,
            yscrollcommand=v_scrollbar.set
        )

    def _on_screenshot_view_resize(self, event=None):
        """Ограничить область «Скриншот»: ширина 50%, высота 90%."""
        if event is None:
            return
        target_width = max(1, int(event.width * 0.5))
        target_height = max(1, int(event.height * 0.9))
        self.canvas.configure(width=target_width, height=target_height)
    
    def _setup_peaks_frame(self):
        """Настройка фрейма пиков."""
        peaks_frame = ttk.LabelFrame(self._left_frame, text="Пики", padding=10)
        peaks_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Панель настроек (разбита на строки, чтобы длинные подписи не обрезались)
        settings_frame = ttk.Frame(peaks_frame)
        settings_frame.pack(fill="x", pady=(0, 5))

        tuning_row = ttk.Frame(settings_frame)
        tuning_row.pack(fill="x")

        # Чувствительность
        ttk.Label(tuning_row, text="Чувствительность:").pack(side="left")
        self.threshold_scale = ttk.Scale(
            tuning_row,
            from_=1, to=255,
            variable=self.peaks_threshold,
            orient="horizontal",
            length=100
        )
        self.threshold_scale.pack(side="left", padx=(5, 0))
        self.threshold_entry_var = tk.StringVar(value=str(self.peaks_threshold.get()))
        self.threshold_entry = ttk.Entry(
            tuning_row,
            textvariable=self.threshold_entry_var,
            width=4
        )
        self.threshold_entry.pack(side="left", padx=(5, 0))
        self.threshold_entry.bind("<Return>", self._apply_threshold_from_entry)
        self.threshold_entry.bind("<FocusOut>", self._apply_threshold_from_entry)
        self.peaks_threshold.trace_add("write", self._on_threshold_changed)
        
        # Масштаб
        ttk.Label(tuning_row, text="Масштаб:").pack(side="left")
        self.scale_combo = ttk.Combobox(
            tuning_row,
            textvariable=self.peaks_scale,
            values=[25, 50, 100],
            state="readonly",
            width=5
        )
        self.scale_combo.pack(side="left", padx=(5, 0))
        ttk.Label(tuning_row, text="%").pack(side="left", padx=(0, 15))
        
        # Инверсия
        ttk.Checkbutton(
            tuning_row,
            text="Инверсия",
            variable=self.peaks_invert
        ).pack(side="left", padx=(0, 15))

        # Пикселей для зажигания сегмента
        ttk.Label(tuning_row, text="Пикселей для сегмента:").pack(side="left", padx=(10, 5))
        segment_spin = ttk.Spinbox(
            tuning_row,
            from_=1,
            to=30,
            width=4,
            textvariable=self.segment_peak_threshold
        )
        segment_spin.pack(side="left", padx=(0, 15))
        segment_spin.bind("<Return>", self._apply_segment_threshold)
        segment_spin.bind("<FocusOut>", self._apply_segment_threshold)
        
        # Кнопка скачивания + кнопки контуров справа от "Пикселей для сегмента"
        download_and_contours_frame = ttk.Frame(tuning_row)
        download_and_contours_frame.pack(side="left", padx=(10, 0), anchor="n")
        self.download_peaks_btn = ttk.Button(
            download_and_contours_frame,
            text="Скачать",
            command=self._save_peaks_image
        )
        self.download_peaks_btn.pack(fill="x")

        # Кнопки контуров: bbox-центр и центр массы (расположены вертикально)
        contours_buttons_frame = ttk.Frame(download_and_contours_frame)
        contours_buttons_frame.pack(fill="x", pady=(4, 0))
        self.contours_all_btn = ttk.Button(
            contours_buttons_frame,
            text="Контуры bbox",
            command=self._detect_all_contours
        )
        self.contours_all_btn.pack(fill="x")
        self.contours_mass_btn = ttk.Button(
            contours_buttons_frame,
            text="Контуры масс.",
            command=self._detect_all_contours_mass_center
        )
        self.contours_mass_btn.pack(fill="x", pady=(4, 0))

        # Подсказка о горячей клавише
        ttk.Label(tuning_row, text="(левый Shift)", foreground="gray").pack(side="left", padx=(10, 0))
        
        # Canvas для пиков
        self._peaks_view_frame = ttk.Frame(peaks_frame)
        self._peaks_view_frame.pack(fill="both", expand=True)
        self.peaks_canvas = tk.Canvas(self._peaks_view_frame, bg="white")
        self.peaks_canvas.pack(fill="both", expand=True)
    
    def _setup_error_frame(self):
        """Настройка фрейма ошибок."""
        error_frame = ttk.LabelFrame(self._left_frame, text="Ошибки и сообщения", padding=5)
        error_frame.pack(fill="x", padx=10, pady=5)
        
        clear_btn = ttk.Button(
            error_frame,
            text="Очистить",
            command=self._clear_errors
        )
        clear_btn.pack(anchor="e", pady=(0, 5))
        
        self.error_text = scrolledtext.ScrolledText(
            error_frame,
            height=4,
            wrap=tk.WORD,
            state="disabled",
            font=("Consolas", 9)
        )
        self.error_text.tag_configure("green", foreground="green")
        self.error_text.pack(fill="x", expand=True)
    
    def _setup_status_bar(self):
        """Настройка статус-бара."""
        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = ttk.Label(
            self._left_frame,
            textvariable=self.status_var,
            relief="sunken",
            anchor="w"
        )
        status_bar.pack(fill="x", padx=10, pady=(0, 10))
    
    def _setup_screenshot_previews(self):
        """Средняя панель: текущая лупа и справка по цифрам Kolos."""
        current_loupe_frame = ttk.LabelFrame(self._middle_frame, text="Текущая лупа", padding=5)
        current_loupe_frame.pack(fill="x", pady=(0, 5))
        self._current_loupe_label = ttk.Label(current_loupe_frame, text="—", anchor="center")
        self._current_loupe_label.pack(fill="x")
        self._current_loupe_photo: ImageTk.PhotoImage | None = None

        hint_frame = ttk.LabelFrame(self._middle_frame, text="Цифры Kolos", padding=5)
        hint_frame.pack(fill="both", expand=True)
        self._kolos_digits_hint = scrolledtext.ScrolledText(
            hint_frame,
            height=14,
            width=34,
            wrap=tk.WORD,
            font=("Segoe UI", 9),
            state=tk.DISABLED,
            relief="flat",
        )
        self._kolos_digits_hint.pack(fill="both", expand=True)
        self._kolos_digits_hint.configure(state=tk.NORMAL)
        self._kolos_digits_hint.insert("1.0", KOLOS_DIGITS_HINT_RU)
        self._kolos_digits_hint.configure(state=tk.DISABLED)
    
    def _setup_objects_table(self):
        """Правая панель: таблица грубых объектов и индикатор режима детектора."""
        # Грубые объекты (уменьшенная лупа)
        zoomed_frame = ttk.LabelFrame(self._right_frame, text="Грубые объекты (уменьшенная лупа)", padding=5)
        zoomed_frame.pack(fill="both", expand=True, pady=(0, 5))
        self._zoomed_tree = ttk.Treeview(zoomed_frame, columns=("id", "segments"), show="headings", height=8)
        self._zoomed_tree.heading("id", text="ID")
        self._zoomed_tree.heading("segments", text="Сегменты (горящие)")
        self._zoomed_tree.column("id", width=240)
        self._zoomed_tree.column("segments", width=540)
        zoomed_scroll = ttk.Scrollbar(zoomed_frame, orient="vertical", command=self._zoomed_tree.yview)
        self._zoomed_tree.pack(side="left", fill="both", expand=True)
        zoomed_scroll.pack(side="right", fill="y")
        self._zoomed_tree.configure(yscrollcommand=zoomed_scroll.set)

        kolos_frame = ttk.LabelFrame(self._right_frame, text="Kolos", padding=5)
        kolos_frame.pack(fill="both", expand=True)
        self._kolos_text = scrolledtext.ScrolledText(
            kolos_frame, height=14, wrap=tk.WORD, font=("Consolas", 9), state=tk.NORMAL
        )
        self._kolos_text.tag_configure("kolos_red", foreground="#b71c1c")
        self._kolos_text.tag_configure("kolos_user_input", foreground="#0b2a5b", background="#cfe3ff")
        self._configure_copyable_readonly_text(self._kolos_text)
        self._make_text_readonly(self._kolos_text)
        self._kolos_text.pack(fill="both", expand=True)
        kolos_inp = ttk.Frame(kolos_frame)
        kolos_inp.pack(fill="x", pady=(6, 0))
        ttk.Label(kolos_inp, text="Ввод → Kolos (Enter):").pack(side=tk.LEFT)
        self._kolos_input_var = tk.StringVar()
        self._kolos_entry = ttk.Entry(kolos_inp, textvariable=self._kolos_input_var)
        self._kolos_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=(6, 0))
        self._kolos_entry.bind("<Return>", self._on_kolos_input_return)
    
    def _update_objects_table(self):
        """Обновление таблицы грубых объектов из _zoomed_signature_to_ids."""
        for item in self._zoomed_tree.get_children():
            self._zoomed_tree.delete(item)
        for sig, ids in self._zoomed_signature_to_ids.items():
            ids_str = ", ".join(str(i) for i in ids)
            seg_str = ", ".join(str(s) for s in sig)
            self._zoomed_tree.insert("", tk.END, values=(ids_str, seg_str))
    
    def _init_loupe_controller(self):
        """Инициализация контроллера луп после создания canvas."""
        self.loupe_controller = LoupeController(
            self.canvas,
            self.peaks_canvas,
            loupe_size=100
        )
    
    def _setup_hotkeys(self):
        """Настройка горячих клавиш."""
        self.root.bind_all("<Shift_L>", self._on_shift_pressed)
        self.root.bind_all("<Escape>", self._on_escape_pressed)
        for combo in (self.monitor_combo, self.scale_combo):
            combo.bind("<Shift_L>", self._on_shift_pressed)
            combo.bind("<Escape>", self._on_escape_pressed)

    def _on_root_close(self):
        """Сохранение базы объектов и закрытие приложения."""
        if self._kolos_controller is not None:
            self._kolos_controller.stop()
            self._kolos_controller = None
        self._objects_repo.save(self._full_signature_to_ids, self._zoomed_signature_to_ids, self._next_refined_id)
        self._processing_executor.shutdown(wait=False, cancel_futures=True)
        self.root.destroy()

    def _start_kolos_embedded(self) -> None:
        """Поднять Kolos в подпроцессе; вывод в панель, ввод из поля."""
        root = project_root_from_glaz_file(__file__)
        self._kolos_controller = KolosSubprocessController(root, self._kolos_thread_event)
        err = self._kolos_controller.start(monitor_idx=self.capture.selected_monitor)
        if err:
            self._kolos_append_main_thread(f"Kolos: {err}\n")
        else:
            self._kolos_entry.focus_set()

    def _kolos_thread_event(self, stream: str, payload: str) -> None:
        """Вызывается из потоков чтения подпроцесса — только маршрутизация в UI-поток."""
        self.root.after(0, lambda: self._kolos_handle_event(stream, payload))

    def _kolos_handle_event(self, stream: str, payload: str) -> None:
        if stream == "_exit":
            self._kolos_append_main_thread(f"[Kolos завершён, код {payload}]\n")
            return
        prefix = "[err] " if stream == "stderr" else ""
        self._kolos_append_main_thread(f"{prefix}{payload}\n")

    def _kolos_append_main_thread(self, text: str) -> None:
        """Добавить текст в панель Kolos (только из главного потока Tk)."""
        for line in text.splitlines(keepends=True):
            clean = strip_sgr(line)
            if line_looks_user_input(line):
                self._kolos_text.insert(tk.END, clean, ("kolos_user_input",))
            elif line_looks_red_in_terminal(line):
                self._kolos_text.insert(tk.END, clean, ("kolos_red",))
            else:
                self._kolos_text.insert(tk.END, clean)
        self._enforce_text_max_lines(self._kolos_text, self._kolos_max_lines)
        self._kolos_text.see(tk.END)

    def _configure_copyable_readonly_text(self, widget: tk.Text) -> None:
        """
        Разрешить выделение и копирование из read-only Text/ScrolledText.

        Примечание: state=DISABLED сохраняем, чтобы пользователь не мог редактировать вывод.
        """
        widget.bind("<Control-c>", lambda e: self._copy_text_selection(widget, e, "Control-c"))
        widget.bind("<Control-C>", lambda e: self._copy_text_selection(widget, e, "Control-C"))
        widget.bind("<Control-Shift-c>", lambda e: self._copy_text_selection(widget, e, "Control-Shift-c"))
        widget.bind("<Control-Shift-C>", lambda e: self._copy_text_selection(widget, e, "Control-Shift-C"))
        widget.bind("<<Copy>>", lambda e: self._copy_text_selection(widget, e, "<<Copy>>"))
        # Раскладка клавиатуры может менять keysym (ru/en). На Windows keycode для C обычно 67.
        widget.bind("<Control-KeyPress>", lambda e: self._copy_on_ctrl_keypress(widget, e))
        widget.bind("<Button-3>", lambda e: self._show_copy_context_menu(widget, e))

    def _copy_on_ctrl_keypress(self, widget: tk.Text, event) -> str | None:
        keycode = getattr(event, "keycode", None)
        # VK_C = 67 на Windows
        if keycode == 67:
            return self._copy_text_selection(widget, event, "Control-KeyPress(VK_C)")
        return None

    def _make_text_readonly(self, widget: tk.Text) -> None:
        """Запретить редактирование Text, сохранив выделение и копирование."""
        widget.configure(insertontime=0, cursor="arrow")
        # Блокируем редактирующие клавиши, но не мешаем копированию/навигации/выделению.
        widget.bind("<Key>", lambda e: self._readonly_key_filter(widget, e))
        # Блокируем вставку/вырезание.
        for seq in ("<Control-v>", "<Control-V>", "<Shift-Insert>", "<<Paste>>", "<Control-x>", "<Control-X>", "<<Cut>>"):
            widget.bind(seq, lambda e: "break")

    def _readonly_key_filter(self, widget: tk.Text, event) -> str | None:
        """
        Фильтр клавиш для read-only Text:
        - разрешаем навигацию и сочетания копирования
        - остальное блокируем, чтобы нельзя было редактировать
        """
        keysym = getattr(event, "keysym", None)
        state = getattr(event, "state", None)
        keycode = getattr(event, "keycode", None)
        # Маска Ctrl для Tk на Windows обычно 0x0008 (8). Проверяем бит.
        ctrl = bool(state & 0x0008) if isinstance(state, int) else False
        # Разрешаем копирование (пусть отработают специализированные биндинги)
        if ctrl and (keysym in ("c", "C") or keycode == 67):
            return None
        # Разрешаем навигацию/прокрутку
        if keysym in ("Left", "Right", "Up", "Down", "Home", "End", "Prior", "Next"):
            return None
        # Разрешаем служебные модификаторы
        if keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R"):
            return None
        return "break"

    def _copy_text_selection(self, widget: tk.Text, event=None, source: str = "?") -> str:
        """Скопировать выделенный текст в clipboard."""
        try:
            selected = widget.get(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            return "break"
        widget.clipboard_clear()
        widget.clipboard_append(selected)
        return "break"

    def _show_copy_context_menu(self, widget: tk.Text, event) -> str:
        """ПКМ → меню Copy (если есть выделение)."""
        menu = tk.Menu(widget, tearoff=0)
        try:
            widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            has_sel = True
        except tk.TclError:
            has_sel = False
        menu.add_command(label="Copy", command=lambda: self._copy_text_selection(widget), state=("normal" if has_sel else "disabled"))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    def _enforce_text_max_lines(self, widget: tk.Text, max_lines: int) -> None:
        """Ограничить буфер Text до последних max_lines строк."""
        if max_lines <= 0:
            return
        try:
            end_index = widget.index("end-1c")
            current_lines = int(end_index.split(".", 1)[0])
        except (tk.TclError, ValueError):
            return
        to_delete = compute_lines_to_delete(current_lines, max_lines)
        if to_delete <= 0:
            return
        # Удаляем целые строки: если нужно удалить N строк, удаляем [1..N] → до (N+1).0
        widget.delete("1.0", f"{to_delete + 1}.0")

    def _on_kolos_input_return(self, event=None):
        """Передать строку в stdin Kolos (аналог консольного ввода)."""
        if self._kolos_controller is None or not self._kolos_controller.is_running:
            return "break"
        line = self._kolos_input_var.get()
        self._kolos_input_var.set("")
        self._kolos_controller.send_line(line)
        return "break"
    
    def _on_shift_pressed(self, event=None):
        """Обработчик нажатия левого Shift - сохранение пиков."""
        if self.capture.is_capturing:
            self._save_peaks_image()
            return "break"
    
    def _on_escape_pressed(self, event=None):
        """Обработчик нажатия Escape - остановка захвата."""
        if self.capture.is_capturing:
            self._stop_capture()
            return "break"
    
    def _clear_objects_db(self):
        """Очистка базы объектов: файл и память. Новые объекты будут записываться с нуля."""
        self._full_signature_to_ids = {}
        self._zoomed_signature_to_ids = {}
        self._next_refined_id = 1
        self._object_id_to_refined = {}
        self._recognition_state = RecognitionIdle()
        self._zoomed_signature_temp = ()
        self._objects_repo.save(self._full_signature_to_ids, self._zoomed_signature_to_ids, self._next_refined_id)
        self._update_objects_table()
        
        # Удаление всех скриншотов из папки object_screenshots
        if os.path.isdir(self._screenshots_dir):
            try:
                for filename in os.listdir(self._screenshots_dir):
                    filepath = os.path.join(self._screenshots_dir, filename)
                    if os.path.isfile(filepath):
                        try:
                            os.remove(filepath)
                        except OSError:
                            pass
            except OSError:
                pass
        
        self.log_message("БД объектов очищена. Скриншоты удалены.")
    
    # === Обработчики событий ===
    
    def _on_monitor_selected(self, event=None):
        """Обработчик выбора монитора."""
        selection = self.monitor_var.get()
        if selection:
            monitor_index = int(selection.split()[1])
            self.capture.selected_monitor = monitor_index
            self.status_var.set(f"Выбран {selection}")
            self.log_message(f"Выбран монитор: {selection}")
    
    def _on_threshold_changed(self, *args):
        """Обработчик изменения чувствительности (слайдер). Синхронизирует поле ввода."""
        try:
            v = self.peaks_threshold.get()
            self.threshold_entry_var.set(str(v))
        except tk.TclError:
            pass

    def _apply_threshold_from_entry(self, event=None):
        """Применить значение чувствительности из поля ввода (Enter или уход фокуса)."""
        try:
            s = self.threshold_entry_var.get().strip()
            v = int(s) if s else self.peaks_threshold.get()
            v = max(1, min(255, v))
            self.peaks_threshold.set(v)
            self.threshold_entry_var.set(str(v))
        except ValueError:
            self.threshold_entry_var.set(str(self.peaks_threshold.get()))

    def _apply_segment_threshold(self, event=None):
        """Ограничить «пикселей для сегмента» диапазоном 1–30 и применить к конфигу лупы."""
        try:
            v = self.segment_peak_threshold.get()
        except tk.TclError:
            v = 3
        v = max(1, min(30, int(v)))
        self.segment_peak_threshold.set(v)
        if hasattr(self, "loupe_controller") and self.loupe_controller is not None:
            self.loupe_controller.peaks_loupe.config.peak_sequence_threshold = v
            self.loupe_controller.peaks_loupe.config.peak_sequence_threshold_arc = v
    
    def _start_capture(self):
        """Запуск захвата экрана."""
        if self.capture.selected_monitor is None:
            self.log_message("Предупреждение: выберите монитор перед началом захвата", error=True)
            return
        
        self.capture_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_var.set("Захват экрана...")
        self.log_message("Начало захвата скриншотов")
        
        self._set_performance_mode_idle()
        self.capture.start(
            on_frame=self._on_frame_captured,
            on_error=self._on_capture_error,
            interval=self._processing_interval_s,
        )
    
    def _stop_capture(self):
        """Остановка захвата экрана."""
        self.capture.stop()
        self.capture_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_var.set("Захват остановлен")
        self.log_message("Захват скриншотов остановлен")
        self.loupe_controller.clear_all()
    
    def _on_frame_captured(self, image: Image.Image):
        """Callback при захвате кадра. Троттлинг: не чаще _update_frame_interval с."""
        self.current_image = image
        now = time.time()
        cursor_pos = get_cursor_pos()
        should_process, last_pos, stable_since, last_idle = decide_processing_schedule(
            now=now,
            cursor_pos=cursor_pos,
            recognition_is_idle=self._recognition_state.is_idle,
            cursor_stable_delay_s=self._cursor_stable_delay,
            idle_processing_period_s=self._idle_processing_period_s,
            last_cursor_pos=self._processing_last_cursor_pos,
            cursor_stable_since=self._processing_cursor_stable_since,
            last_idle_processing_time=self._last_idle_processing_time,
        )
        self._processing_last_cursor_pos = last_pos
        self._processing_cursor_stable_since = stable_since
        self._last_idle_processing_time = last_idle
        if should_process:
            self._request_processing_throttled()
        if now - self._last_update_frame_time < self._update_frame_interval:
            return
        self._last_update_frame_time = now  # резервируем слот (обновим при старте _update_frame)
        self.root.after(0, self._update_frame)
    
    def _request_processing_throttled(self) -> None:
        """Запросить фоновую обработку не чаще заданного интервала."""
        now = time.time()
        if now - self._last_processing_request_time < self._processing_interval_s:
            return
        self._last_processing_request_time = now
        self._request_processing()

    def _apply_intervals(self, interval_s: float) -> None:
        """Применить интервал для захвата/обработки/обновления UI."""
        interval_s = float(max(0.01, interval_s))
        self._active_interval_s = interval_s
        self._update_frame_interval = interval_s
        self._processing_interval_s = interval_s
        if self.capture.is_capturing:
            # Обновляем интервал захвата на лету, чтобы не перегружать CPU
            self.capture.set_interval(interval_s)

    def _set_performance_mode_idle(self) -> None:
        """Idle: 4–6 FPS."""
        self._apply_intervals(self._idle_interval_s)

    def _set_performance_mode_step1(self) -> None:
        """Step1: ускоренный режим для точного определения."""
        self._apply_intervals(self._step1_interval_s)

    def _update_frame(self):
        """Синхронное обновление всех компонентов в правильном порядке."""
        # Троттлинг по факту старта в главном потоке (не по планированию из потока захвата)
        self._last_update_frame_time = time.time()
        self._consume_processing_result()
        self._poll_scan_request_and_maybe_run()
        # Лупа обновляется до отрисовки и проверки контура/сегментов при наведении на объект
        self._update_loupe()
        self._update_display()
        self._process_signature_if_pending()  # Снятие подписи ПОСЛЕ отрисовки лупы
        self._event_bus.emit("frame_captured")

    def _poll_scan_request_and_maybe_run(self) -> None:
        """Проверить IPC scan_request и запустить предскан (debounce, idle-only)."""
        # Не мешаем step1: если идёт определение объекта, отложим.
        if not self._recognition_state.is_idle:
            return

        now = time.time()
        req = read_scan_request(max_age_sec=10.0, now=now)
        if req is not None:
            if req.request_id != self._scan_last_handled_request_id:
                # Запоминаем последний запрос (latest wins)
                self._scan_pending_request_id = req.request_id
                self._scan_last_request_seen_ts = req.timestamp

        if self._scan_pending_request_id is None:
            return

        if (now - self._scan_last_run_ts) < self._scan_debounce_sec:
            return

        with self._scan_lock:
            if self._scan_future is not None and not self._scan_future.done():
                return
            snapshot = self._build_scan_snapshot(request_id=self._scan_pending_request_id)
            if snapshot is None:
                return
            self._scan_last_run_ts = now
            self._scan_future = self._scan_executor.submit(self._compute_prescan, snapshot)
            self._scan_future.add_done_callback(self._on_scan_done)

    def _build_scan_snapshot(self, *, request_id: str) -> dict | None:
        """Собрать данные для фонового предскана (без ссылок на mutable UI state)."""
        if self.current_image is None:
            return None
        if not self._detected_objects:
            return None
        try:
            threshold = int(self.peaks_threshold.get())
            invert = bool(self.peaks_invert.get())
        except Exception:
            threshold = 100
            invert = False

        # Копируем кадр, чтобы воркер не зависел от обновлений.
        frame = self.current_image.copy()
        objects = list(self._detected_objects)
        return {
            "request_id": str(request_id),
            "frame": frame,
            "objects": objects,
            "threshold": threshold,
            "invert": invert,
        }

    def _compute_prescan(self, snapshot: dict) -> dict:
        """Фоновый расчёт подписей по bbox объектов (без изменения БД)."""
        request_id = snapshot["request_id"]
        frame: Image.Image = snapshot["frame"]
        objects: list[DetectedObject] = snapshot["objects"]
        threshold: int = snapshot["threshold"]
        invert: bool = snapshot["invert"]

        loupe_size = 100
        try:
            if self.loupe_controller is not None:
                loupe_size = int(getattr(self.loupe_controller, "loupe_size", 100))
        except Exception:
            loupe_size = 100

        out: list[tuple[int, tuple[int, ...]]] = []
        for obj in objects:
            sig = self._signature_for_object_bbox(
                frame=frame,
                obj=obj,
                loupe_size=loupe_size,
                threshold=threshold,
                invert=invert,
            )
            if sig:
                out.append((int(obj.id), sig))
        return {"request_id": request_id, "signatures": out}

    def _signature_for_object_bbox(
        self,
        *,
        frame: Image.Image,
        obj: DetectedObject,
        loupe_size: int,
        threshold: int,
        invert: bool,
    ) -> tuple[int, ...]:
        """
        Построить подпись геометрии лупы для bbox объекта.

        Возвращает пустой кортеж, если объект слишком мал или подпись пустая.
        """
        try:
            left, top, right, bottom = obj.bbox
            if (right - left) * (bottom - top) < 36:
                return ()
        except Exception:
            return ()

        crop_bbox, obj_bbox_source = self._object_bbox_to_source_coords(obj, margin_percent=0.2)
        img_w, img_h = frame.size
        l, t, r, b = crop_bbox
        l = max(0, min(int(l), img_w))
        t = max(0, min(int(t), img_h))
        r = max(0, min(int(r), img_w))
        b = max(0, min(int(b), img_h))
        if r - l < 10 or b - t < 10:
            return ()

        crop = frame.crop((l, t, r, b)).resize((int(loupe_size), int(loupe_size)), Image.Resampling.LANCZOS)

        loupe_peaks = ImageProcessor.detect_color_peaks(crop, int(threshold), bool(invert))

        # geometry_scale: большой круг должен описывать объект, как в loupe.update()
        try:
            ol, ot, or_, ob = obj_bbox_source
            obj_w = float(or_ - ol)
            obj_h = float(ob - ot)
            crop_w = float(r - l)
            crop_h = float(b - t)
            if crop_w <= 0 or crop_h <= 0:
                geometry_scale = 1.0
            else:
                obj_w_loupe = obj_w * float(loupe_size) / crop_w
                obj_h_loupe = obj_h * float(loupe_size) / crop_h
                obj_diag_loupe = math.hypot(obj_w_loupe, obj_h_loupe)
                r_large_base = 12 * math.sqrt(2)
                geometry_scale = (obj_diag_loupe / 2.0) / r_large_base if r_large_base > 0 else 1.0
                geometry_scale = max(0.4, min(2.0, float(geometry_scale)))
        except Exception:
            geometry_scale = 1.0

        sig = self._scan_signature_analyzer.compute(
            loupe_peaks, peaks_invert=bool(invert), geometry_scale=float(geometry_scale)
        ).highlighted_segment_ids
        return tuple(sorted(sig)) if sig else ()

    def _on_scan_done(self, future: Future) -> None:
        """Завершение фонового скана: применяем в UI-потоке."""
        try:
            result = future.result()
        except Exception:
            return
        self.root.after(0, lambda r=result: self._apply_scan_result(r))

    def _apply_scan_result(self, result: dict) -> None:
        """Применить результат скана: распознать/зарегистрировать и записать IPC scan_results."""
        request_id = str(result.get("request_id") or "")
        if not request_id:
            return

        # Если уже обработали — не повторяем.
        if request_id == self._scan_last_handled_request_id:
            return

        signatures: list[tuple[int, tuple[int, ...]]] = list(result.get("signatures") or [])
        if not signatures:
            self._scan_last_handled_request_id = request_id
            self._scan_pending_request_id = None
            write_scan_results(ScanResults(request_id=request_id, timestamp=time.time(), items=tuple()))
            return

        # Группировка по refined_id после распознавания/регистрации.
        counts: dict[int, int] = {}
        is_new_any: dict[int, bool] = {}
        any_new = False

        # Распознаём последовательно в UI-потоке, чтобы не конфликтовать с step1/сохранением.
        for _obj_id, sig in signatures:
            if not sig:
                continue
            match = self._objects_repo.find_similar(sig, self._zoomed_signature_to_ids, max_diff_pct=self._signature_match_max_pct)
            if match:
                known_sig, _ = match
                refined_id = self._zoomed_signature_to_ids[known_sig][0]
                is_new = False
            else:
                refined_id = self._next_refined_id
                self._next_refined_id += 1
                self._zoomed_signature_to_ids.setdefault(sig, []).append(refined_id)
                is_new = True
                any_new = True

            counts[int(refined_id)] = int(counts.get(int(refined_id), 0) + 1)
            is_new_any[int(refined_id)] = bool(is_new_any.get(int(refined_id), False) or is_new)

        if any_new:
            self._objects_repo.save(self._full_signature_to_ids, self._zoomed_signature_to_ids, self._next_refined_id)

        items = tuple(
            ScanResultItem(refined_id=int(rid), count=int(cnt), is_new=bool(is_new_any.get(int(rid), False)))
            for rid, cnt in sorted(counts.items(), key=lambda kv: kv[0])
        )
        write_scan_results(ScanResults(request_id=request_id, timestamp=time.time(), items=items))

        # Запоминаем последние результаты (для потенциального UI-использования)
        self._scan_last_results = {int(it.refined_id): (int(it.count), bool(it.is_new)) for it in items}

        self._scan_last_handled_request_id = request_id
        self._scan_pending_request_id = None

    def _request_processing(self) -> None:
        """Запросить фоновую обработку последнего кадра (latest-frame-wins)."""
        if self.current_image is None:
            return
        request = (
            self.current_image.copy(),
            int(self.peaks_threshold.get()),
            bool(self.peaks_invert.get()),
        )
        with self._processing_lock:
            if self._processing_future is None or self._processing_future.done():
                self._submit_processing(request)
            else:
                self._pending_processing_request = request

    def _submit_processing(self, request: tuple[Image.Image, int, bool]) -> None:
        """Отправить задачу обработки кадра в worker."""
        image, threshold, invert = request
        self._processing_future = self._processing_executor.submit(
            self._compute_peaks_and_objects, image, threshold, invert
        )
        self._processing_future.add_done_callback(self._on_processing_done)

    def _on_processing_done(self, future: Future) -> None:
        """Завершение фоновой обработки: сохранить результат и запустить следующую заявку."""
        try:
            result = future.result()
        except Exception:
            result = None
        with self._processing_lock:
            if result is not None:
                self._completed_processing_result = result
            pending = self._pending_processing_request
            self._pending_processing_request = None
            if pending is not None:
                self._submit_processing(pending)

    def _compute_peaks_and_objects(self, image: Image.Image, threshold: int, invert: bool) -> ProcessingResult:
        """Вычислить full-res пики и объекты в фоне с таймингами."""
        t0 = time.perf_counter()
        peaks_img = ImageProcessor.detect_color_peaks(image, threshold, invert)
        t1 = time.perf_counter()
        objects = self._object_detector.detect(peaks_img)
        t2 = time.perf_counter()
        return ProcessingResult(
            peaks_image=peaks_img,
            objects=objects,
            timings_ms={
                "peaks": (t1 - t0) * 1000.0,
                "detect": (t2 - t1) * 1000.0,
                "total": (t2 - t0) * 1000.0,
            },
            detector_mode=ImageProcessor.lines_detector_mode(),
        )

    def _consume_processing_result(self) -> None:
        """Забрать готовый результат фоновой обработки в UI-потоке."""
        with self._processing_lock:
            result = self._completed_processing_result
            self._completed_processing_result = None
        if result is None:
            return
        self.current_peaks_image = result.peaks_image
        self._detected_objects = result.objects
        now = time.time()
        if now - self._last_processing_log_time >= 2.0:
            self._last_processing_log_time = now
            self.status_var.set(
                f"Обработка: пики {result.timings_ms['peaks']:.0f}ms, "
                f"детекция {result.timings_ms['detect']:.0f}ms, "
                f"итого {result.timings_ms['total']:.0f}ms"
            )

    def _on_capture_error(self, error_msg: str):
        """Callback при ошибке захвата (вызывается из потока захвата)."""
        self._event_bus.emit("capture_error", message=error_msg)

    def _on_capture_error_event(self, message: str):
        """Подписчик: логирование ошибки захвата в UI (в главном потоке)."""
        self.root.after(0, lambda m=message: self.log_message(f"Ошибка захвата экрана: {m}", error=True))

    def _on_object_recognized_event(self, refined_id: int, is_new: bool, message: str | None = None):
        """Подписчик: логирование результата определения объекта."""
        if is_new:
            self.log_message(f"Новый объект № {refined_id}")
        else:
            self.log_message(message or f"Объект № {refined_id}", color="green")
    
    def _hold_cursor_if_active(self):
        """Принудительно удерживать курсор в центре объекта, если идёт процесс определения."""
        if self._cursor_hold_position is None:
            return
        if time.time() <= self._cursor_hold_until:
            set_cursor_pos(*self._cursor_hold_position)
            return
        self._cursor_hold_position = None
        self._cursor_hold_until = 0.0
    
    def _update_loupe(self):
        """Обновление лупы."""
        # Удерживаем курсор перед обновлением лупы
        self._hold_cursor_if_active()
        loupe_override = self._loupe_size_effective

        try:
            n = max(1, min(30, self.segment_peak_threshold.get()))
        except (tk.TclError, TypeError):
            n = 3
        self.loupe_controller.peaks_loupe.config.peak_sequence_threshold = n
        self.loupe_controller.peaks_loupe.config.peak_sequence_threshold_arc = n
        
        # Всегда вырезка по курсору — чтобы отображение не менялось при переходе на объект
        self.loupe_controller.update(
            current_image=self.current_image,
            monitor_info=self.capture.monitor_info,
            current_scale=self.current_scale,
            peaks_scale_percent=self.peaks_scale.get(),
            peaks_threshold=self.peaks_threshold.get(),
            peaks_invert=self.peaks_invert.get(),
            loupe_size_override=loupe_override,
            crop_bbox_source=None,  # не переключаться на crop по объекту
            obj_bbox_source=None,
        )
        # Превью «Текущая лупа» — только во время определения объекта (снижает нагрузку в idle)
        if not self._recognition_state.is_idle:
            self._update_current_loupe_preview()
    
    def _update_current_loupe_preview(self):
        """Обновление превью текущей лупы с геометрией в средней панели."""
        loupe_img = self.loupe_controller.render_loupe_tile_with_geometry()
        if loupe_img is not None:
            if loupe_img.mode != "RGB":
                loupe_img = loupe_img.convert("RGB")
            self._current_loupe_photo = ImageTk.PhotoImage(loupe_img)
            self._current_loupe_label.configure(image=self._current_loupe_photo, text="")
        else:
            self._current_loupe_label.configure(image="", text="—")
    
    def _update_display(self):
        """Обновление отображения скриншота."""
        # Удерживаем курсор перед обновлением дисплея
        self._hold_cursor_if_active()
        
        if self.current_image is None:
            return
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            return
        
        img_width, img_height = self.current_image.size
        
        # Вычисляем геометрию отображения всегда (нужно для корректной логики наведения),
        # даже если пропускаем тяжёлый рендер превью.
        scale = self._compute_display_scale(canvas_width, canvas_height, img_width, img_height)
        self.current_scale = scale
        display_size = self._compute_display_size(img_width, img_height, scale)

        # Логика наведения/step1 не должна зависеть от частоты перерисовки UI.
        self._process_mouse_over_object(display_size)

        # Тяжёлый рендер превью скриншота — по отдельному троттлингу
        if self._should_render_screenshot():
            display_img = self._build_screenshot_preview(scale, display_size)
            self.photo = ImageTk.PhotoImage(display_img)
            if self._screenshot_canvas_image_id is None:
                self._screenshot_canvas_image_id = self.canvas.create_image(
                    0, 0, anchor="nw", image=self.photo, tags="image"
                )
            else:
                self.canvas.itemconfig(self._screenshot_canvas_image_id, image=self.photo)
            self.canvas.config(scrollregion=self.canvas.bbox("all"))
            self.status_var.set(f"Отображен скриншот {display_size[0]}x{display_size[1]}")

        # Обновляем пики (только рендер уже вычисленного full-res результата)
        self._update_peaks_display()
    
    def _update_peaks_display(self):
        """Обновление пиков: fit-to-canvas рендер готового full-res изображения."""
        if self.current_peaks_image is None:
            return
        if not self._should_render_peaks():
            return
        peaks_img = self.current_peaks_image
        # Визуализация всегда fit-to-canvas; peaks_scale используется только для вычислений.
        canvas_w = max(1, self.peaks_canvas.winfo_width())
        canvas_h = max(1, self.peaks_canvas.winfo_height())
        img_w, img_h = peaks_img.size
        fit_scale = min(canvas_w / img_w, canvas_h / img_h)
        fit_scale = max(fit_scale, 1e-6)
        preview_w = max(1, int(img_w * fit_scale))
        preview_h = max(1, int(img_h * fit_scale))
        peaks_preview = peaks_img.resize((preview_w, preview_h), Image.Resampling.NEAREST)
        self.peaks_photo = ImageTk.PhotoImage(peaks_preview)
        
        if self._peaks_canvas_image_id is None:
            self._peaks_canvas_image_id = self.peaks_canvas.create_image(
                0, 0, anchor="nw", image=self.peaks_photo, tags="image"
            )
        else:
            self.peaks_canvas.itemconfig(self._peaks_canvas_image_id, image=self.peaks_photo)
        # Лупа рисуется до _update_display; поднимаем её элементы поверх изображения пиков
        for tag in ("loupe", "loupe_border", "loupe_crosshair"):
            self.peaks_canvas.tag_raise(tag)

    def _compute_display_scale(
        self,
        canvas_width: int,
        canvas_height: int,
        img_width: int,
        img_height: int,
    ) -> float:
        """Масштаб предпросмотра скриншота (0..1)."""
        scale_x = canvas_width / img_width
        scale_y = canvas_height / img_height
        return float(min(scale_x, scale_y, 1.0))

    def _compute_display_size(self, img_width: int, img_height: int, scale: float) -> tuple[int, int]:
        """Размер предпросмотра (в пикселях canvas) для заданного масштаба."""
        if scale < 1.0:
            return (max(1, int(img_width * scale)), max(1, int(img_height * scale)))
        return (int(img_width), int(img_height))

    def _build_screenshot_preview(
        self, scale: float, display_size: tuple[int, int]
    ) -> Image.Image:
        """Построить PIL изображение предпросмотра для canvas."""
        if scale < 1.0:
            return self.current_image.resize(display_size, self._screenshot_preview_resample)
        return self.current_image

    def _should_render_screenshot(self) -> bool:
        """Решить, нужно ли перерисовать предпросмотр скриншота сейчас."""
        now = time.time()
        if now - self._last_render_screenshot_time < self._render_interval_screenshot_s:
            return False
        self._last_render_screenshot_time = now
        return True

    def _should_render_peaks(self) -> bool:
        """Решить, нужно ли перерисовать предпросмотр пиков сейчас."""
        now = time.time()
        if now - self._last_render_peaks_time < self._render_interval_peaks_s:
            return False
        self._last_render_peaks_time = now
        return True
    
    def _save_peaks_image(self):
        """Сохранение изображения пиков с лупой."""
        if self.current_peaks_image is None:
            self.log_message("Нет изображения для сохранения", error=True)
            return
        
        downloads_path = get_downloads_path()
        filename = generate_filename("peaks")
        filepath = os.path.join(downloads_path, filename)
        
        try:
            # Создаём композитное изображение с лупой
            image_to_save = self.loupe_controller.compose_peaks_with_loupe(
                self.current_peaks_image
            )
            image_to_save.save(filepath)
            self.log_message(f"Изображение сохранено: {filepath}")
            self.status_var.set(f"Сохранено: {filename}")
        except Exception as e:
            self.log_message(f"Ошибка сохранения: {e}", error=True)

    def _detect_all_contours(self):
        """Сохранить контуры всех объектов с центрами по bbox."""
        self._detect_all_contours_with_center_mode("bbox")

    def _detect_all_contours_mass_center(self):
        """Сохранить контуры всех объектов с центрами по центру массы контура."""
        self._detect_all_contours_with_center_mode("mass")

    def _detect_all_contours_with_center_mode(self, center_mode: str):
        """Общий экспорт контуров с выбором типа центра: bbox или mass."""
        if not _HAS_OPENCV:
            msg = "OpenCV недоступен. Установите в том же Python, из которого запускаете программу: pip install opencv-python"
            if _OPENCV_ERROR:
                msg += f". Ошибка при загрузке: {_OPENCV_ERROR}"
            self.log_message(msg, error=True)
            return
        if self.current_peaks_image is None:
            self.log_message("Нет изображения пиков. Включите отображение пиков.", error=True)
            return
        # Используем те же данные, что и при наведении:
        # current_peaks_image + тот же детектор объектов.
        peaks_arr = np.array(self.current_peaks_image)
        if peaks_arr.ndim > 2:
            peaks_arr = peaks_arr[:, :, 0]
        objects = self._object_detector.detect(self.current_peaks_image)
        result = cv2.cvtColor(peaks_arr, cv2.COLOR_GRAY2BGR)
        for obj in objects:
            left, top, right, bottom = obj.bbox
            cv2.rectangle(result, (left, top), (right - 1, bottom - 1), (0, 255, 0), 1)
        if center_mode == "mass":
            contour_centers = [obj.center_peaks for obj in objects]
        else:
            contour_centers = [
                ((obj.bbox[0] + obj.bbox[2]) / 2.0, (obj.bbox[1] + obj.bbox[3]) / 2.0)
                for obj in objects
            ]
        for cx, cy in contour_centers:
            cv2.circle(result, (int(round(cx)), int(round(cy))), 3, (0, 0, 255), -1, lineType=cv2.LINE_AA)
        os.makedirs(self._contour_screenshots_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        center_type = "mass" if center_mode == "mass" else "bbox"
        filename = f"contours_{center_type}_{timestamp}.png"
        path = os.path.join(self._contour_screenshots_dir, filename)
        cv2.imwrite(path, result)
        self.log_message(f"Контуры сохранены: {path}")
        self.status_var.set(f"Контуры: {filename}")

    def _clear_errors(self):
        """Очистка области ошибок."""
        self.error_text.config(state="normal")
        self.error_text.delete("1.0", tk.END)
        self.error_text.config(state="disabled")
        self.log_message("Область ошибок очищена")

    def _update_detected_objects(self):
        """Совместимость: детекция теперь выполняется в фоне."""
        return

    def _mouse_to_peaks_coords(self, display_width: int, display_height: int) -> tuple[float, float] | None:
        """Преобразование позиции мыши (монитор) в full-res координаты изображения Пики."""
        monitor = self.capture.monitor_info
        if monitor is None or self.current_peaks_image is None:
            return None
        cursor_x, cursor_y = get_cursor_pos()
        rel_x = cursor_x - monitor["left"]
        rel_y = cursor_y - monitor["top"]
        if rel_x < 0 or rel_y < 0 or rel_x >= monitor["width"] or rel_y >= monitor["height"]:
            return None
        img_w, img_h = self.current_peaks_image.size
        peak_px = rel_x * (img_w / monitor["width"])
        peak_py = rel_y * (img_h / monitor["height"])
        return peak_px, peak_py

    def _object_center_to_monitor_coords(self, cx_peaks: float, cy_peaks: float) -> tuple[int, int]:
        """Центр объекта (full-res Пики) -> глобальные экранные координаты."""
        monitor = self.capture.monitor_info
        if monitor is None or self.current_peaks_image is None:
            return 0, 0
        img_w, img_h = self.current_peaks_image.size
        if img_w <= 0 or img_h <= 0:
            return monitor["left"], monitor["top"]
        mx = cx_peaks * (monitor["width"] / img_w)
        my = cy_peaks * (monitor["height"] / img_h)
        return int(monitor["left"] + mx), int(monitor["top"] + my)

    def _object_bbox_to_source_size(self, obj: DetectedObject) -> tuple[float, float]:
        """Размер bbox объекта в координатах исходного изображения (монитора): (ширина, высота)."""
        left, top, right, bottom = obj.bbox
        w = float(right - left)
        h = float(bottom - top)
        return w, h
    
    def _object_bbox_to_source_coords(self, obj: DetectedObject, margin_percent: float = 0.2) -> tuple[tuple[int, int, int, int], tuple[float, float, float, float]]:
        """
        Преобразование bbox объекта из координат пиков в координаты исходного изображения.
        Crop = объект + margin, центрированный. Геометрия лупы масштабируется так,
        чтобы большой круг описывал объект.
        
        Returns:
            ((crop_left, crop_top, crop_right, crop_bottom), (obj_left, obj_top, obj_right, obj_bottom))
            в координатах исходного изображения (current_image)
        """
        left_p, top_p, right_p, bottom_p = obj.bbox
        left_src = float(left_p)
        top_src = float(top_p)
        right_src = float(right_p)
        bottom_src = float(bottom_p)
        
        w = right_src - left_src
        h = bottom_src - top_src
        cx_src = (left_src + right_src) / 2.0
        cy_src = (top_src + bottom_src) / 2.0
        
        # Crop = объект + margin (20%), квадрат, центрирован на объекте.
        # Минимум 4 px margin для антиалиаса и округления.
        margin = max(max(w, h) * margin_percent, 4.0)
        crop_side = max(w, h) + 2 * margin
        half_side = crop_side / 2.0
        left_final = int(math.floor(cx_src - half_side))
        top_final = int(math.floor(cy_src - half_side))
        right_final = int(math.ceil(cx_src + half_side))
        bottom_final = int(math.ceil(cy_src + half_side))
        
        crop_bbox = (left_final, top_final, right_final, bottom_final)
        obj_bbox_source = (left_src, top_src, right_src, bottom_src)
        return crop_bbox, obj_bbox_source

    def _reset_object_state(self):
        """Сброс состояния отслеживания объекта."""
        self._last_hovered_object_id = None
        self._loupe_size_effective = 100
        self._last_cursor_pos = None
        self._cursor_stable_since = None
        self._object_already_recognized = False
        self._cursor_center_target = None
        self._cursor_centered_confirmed = False

    def _process_mouse_over_object(self, display_size: tuple[int, int]):
        """При попадании курсора на объект: масштаб под большой круг и запуск грубого определения."""
        now = time.time()
        
        # Если уже идёт процесс определения (step1) — не начинаем новый
        if not self._recognition_state.is_idle:
            return
        if not self.capture.is_capturing:
            self._reset_object_state()
            return
        
        if not self._detected_objects or self.capture.monitor_info is None:
            self._reset_object_state()
            return
        
        peak_coords = self._mouse_to_peaks_coords(display_size[0], display_size[1])
        if peak_coords is None:
            self._reset_object_state()
            return
        
        px, py = peak_coords
        current_cursor = get_cursor_pos()

        containing = [o for o in self._detected_objects if o.contains_point(px, py)]
        if not containing:
            self._reset_object_state()
            return
        obj = min(
            containing,
            key=lambda o: (o.center_peaks[0] - px) ** 2 + (o.center_peaks[1] - py) ** 2,
        )

        # Первый вход на этот объект — начинаем отслеживать стабильность курсора
        if self._last_hovered_object_id != obj.id:
            self._last_hovered_object_id = obj.id
            self._last_cursor_pos = current_cursor
            self._cursor_stable_since = now
            self._object_already_recognized = False  # Новый объект — сброс флага
            self._loupe_size_effective = 100
            self._cursor_centered_confirmed = False
            self._cursor_center_target = None
            return

        # Проверяем, двигается ли курсор
        if self._last_cursor_pos != current_cursor:
            self._last_cursor_pos = current_cursor
            self._cursor_stable_since = now
            return

        if self._cursor_stable_since is None:
            return
        if now - self._cursor_stable_since < self._cursor_stable_delay:
            return
        if self._object_already_recognized:
            return
        moved = self._move_cursor_to_mass_center(obj, px, py)
        if moved:
            # Принудительно обновляем лупу уже после центрирования курсора,
            # чтобы подпись/скриншот брались из актуальной позиции.
            self._update_loupe()
            self._recognition_state = RecognitionStep1()
            self._set_performance_mode_step1()
        else:
            self._reset_object_state()
        return

    def _is_cursor_at_target(self) -> bool:
        """Проверить, что курсор находится в ожидаемой точке центрирования."""
        if self._cursor_center_target is None:
            return False
        cx, cy = get_cursor_pos()
        tx, ty = self._cursor_center_target
        return abs(cx - tx) <= self._cursor_center_tolerance_px and abs(cy - ty) <= self._cursor_center_tolerance_px

    def _move_cursor_to_mass_center(self, obj: DetectedObject, px: float, py: float) -> bool:
        """Переместить курсор в центр массы объекта и удерживать 1 секунду."""
        if self.capture.monitor_info is None:
            return False
        cx_peaks, cy_peaks = obj.center_peaks
        screen_x, screen_y = self._object_center_to_monitor_coords(cx_peaks, cy_peaks)
        self._cursor_center_target = (screen_x, screen_y)
        self._cursor_centered_confirmed = False
        set_cursor_pos(screen_x, screen_y)
        if not self._is_cursor_at_target():
            return False
        self._cursor_centered_confirmed = True
        self._cursor_hold_position = (screen_x, screen_y)
        self._cursor_hold_until = time.time() + self._cursor_hold_after_center
        return True

    def _process_signature_if_pending(self):
        """
        Процесс определения объекта по грубой подписи (state machine).

        Состояния:
        - idle: ожидание входа на объект
        - step1: объект в увеличенной лупе, снятие уменьшенной подписи и определение по ней
        """
        if not self._recognition_state.is_step1:
            return

        # Принудительно удерживаем курсор перед снятием подписи
        self._hold_cursor_if_active()
        if not self._cursor_centered_confirmed and self._is_cursor_at_target():
            self._cursor_centered_confirmed = True
        if not self._cursor_centered_confirmed:
            return

        # Динамическая подгонка больше не нужна - вырезка идёт точно по bbox объекта

        # Снять уменьшенную подпись (объект в увеличенной лупе)
        self._zoomed_signature_temp = tuple(sorted(
            self.loupe_controller.get_last_highlighted_segment_ids()
        ))

        # Сохранить кадр лупы с геометрией и сегментами (красный/синий) для скриншота (если галочка включена)
        # Используем сохранённое изображение пиков (_last_peaks_image) для защиты от перезаписи
        if self._do_screenshots_var.get():
            self._step1_loupe_image = self.loupe_controller.render_loupe_tile_with_geometry(use_saved=True)
        else:
            self._step1_loupe_image = None

        # Поиск по грубой подписи: отличие ≤ 20% — тот же объект, > 20% — новый
        match_result = self._objects_repo.find_similar(
            self._zoomed_signature_temp,
            self._zoomed_signature_to_ids,
            max_diff_pct=self._signature_match_max_pct
        )
        if match_result:
            similar_zoomed, diff_pct = match_result
            ids_list = self._zoomed_signature_to_ids[similar_zoomed]
            self._zoomed_match_count = len(ids_list)
        else:
            similar_zoomed = None
            diff_pct = 1.0
            ids_list = []
            self._zoomed_match_count = 0

        obj_id = self._last_hovered_object_id

        if similar_zoomed and ids_list:
            # Знакомая грубая подпись — объект уже известен
            refined_id = ids_list[0]
            if obj_id is not None:
                self._object_id_to_refined[obj_id] = refined_id
            msg = f"Определён знакомый объект № {refined_id}"
            if diff_pct > 0:
                msg += ". Объект практически тот же самый, отличие менее 20%"
            self._event_bus.emit("object_recognized", refined_id=refined_id, is_new=False, message=msg)
            obj = None
            if obj_id is not None:
                obj = next((o for o in self._detected_objects if o.id == obj_id), None)
            if obj is not None:
                cx_peaks, cy_peaks = obj.center_peaks
                center_xy = self._object_center_to_monitor_coords(cx_peaks, cy_peaks)
                bbox_l, bbox_t, bbox_r, bbox_b = obj.bbox
                monitor = self.capture.monitor_info
                if monitor is not None and self.current_peaks_image is not None:
                    img_w, img_h = self.current_peaks_image.size
                    if img_w > 0 and img_h > 0:
                        l = int(monitor["left"] + bbox_l * (monitor["width"] / img_w))
                        t = int(monitor["top"] + bbox_t * (monitor["height"] / img_h))
                        r = int(monitor["left"] + bbox_r * (monitor["width"] / img_w))
                        b = int(monitor["top"] + bbox_b * (monitor["height"] / img_h))
                        bbox_ltrb = (l, t, r, b)
                    else:
                        bbox_ltrb = None
                else:
                    bbox_ltrb = None
            else:
                center_xy = None
                bbox_ltrb = None
            write_last_confirmed_target(refined_id, center_xy=center_xy, bbox_ltrb=bbox_ltrb)
        else:
            # Новый объект — записываем только грубую подпись
            refined_id = self._next_refined_id
            self._next_refined_id += 1
            if self._zoomed_signature_temp in self._zoomed_signature_to_ids:
                self._zoomed_signature_to_ids[self._zoomed_signature_temp].append(refined_id)
            else:
                self._zoomed_signature_to_ids[self._zoomed_signature_temp] = [refined_id]
            if obj_id is not None:
                self._object_id_to_refined[obj_id] = refined_id
            self._event_bus.emit("object_recognized", refined_id=refined_id, is_new=True)
            self._objects_repo.save(
                self._full_signature_to_ids,
                self._zoomed_signature_to_ids,
                self._next_refined_id
            )
            obj = None
            if obj_id is not None:
                obj = next((o for o in self._detected_objects if o.id == obj_id), None)
            if obj is not None:
                cx_peaks, cy_peaks = obj.center_peaks
                center_xy = self._object_center_to_monitor_coords(cx_peaks, cy_peaks)
                bbox_l, bbox_t, bbox_r, bbox_b = obj.bbox
                monitor = self.capture.monitor_info
                if monitor is not None and self.current_peaks_image is not None:
                    img_w, img_h = self.current_peaks_image.size
                    if img_w > 0 and img_h > 0:
                        l = int(monitor["left"] + bbox_l * (monitor["width"] / img_w))
                        t = int(monitor["top"] + bbox_t * (monitor["height"] / img_h))
                        r = int(monitor["left"] + bbox_r * (monitor["width"] / img_w))
                        b = int(monitor["top"] + bbox_b * (monitor["height"] / img_h))
                        bbox_ltrb = (l, t, r, b)
                    else:
                        bbox_ltrb = None
                else:
                    bbox_ltrb = None
            else:
                center_xy = None
                bbox_ltrb = None
            write_last_confirmed_target(refined_id, center_xy=center_xy, bbox_ltrb=bbox_ltrb)
            self._update_objects_table()
            if self._do_screenshots_var.get():
                os.makedirs(self._screenshots_dir, exist_ok=True)
                zoomed_img = self._step1_loupe_image
                if zoomed_img is not None:
                    zoomed_path = os.path.join(self._screenshots_dir, f"object_{refined_id}_zoomed.png")
                    zoomed_img.save(zoomed_path)

        # Завершаем процесс определения
        self._recognition_state = RecognitionIdle()
        self._set_performance_mode_idle()
        self._zoomed_signature_temp = ()
        self._object_already_recognized = True  # Объект определён, не определять повторно
        self._cursor_center_target = None
        self._cursor_centered_confirmed = False

    def log_message(self, message: str, error: bool = False, color: str | None = None):
        """
        Добавление сообщения в лог.

        Args:
            message: Текст сообщения
            error: Является ли сообщение ошибкой
            color: Цвет текста (например "green" для известного объекта)
        """
        self.error_text.config(state="normal")
        timestamp = time.strftime("%H:%M:%S")
        prefix = "[ОШИБКА]" if error else "[ИНФО]"
        line = f"{timestamp} {prefix} {message}\n"
        if color and color in ("green",):
            self.error_text.insert(tk.END, line, color)
        else:
            self.error_text.insert(tk.END, line)
        self.error_text.see(tk.END)
        self.error_text.config(state="disabled")
        
        # Ограничение количества строк
        lines = self.error_text.get("1.0", tk.END).splitlines()
        if len(lines) > 100:
            self.error_text.config(state="normal")
            self.error_text.delete("1.0", f"{len(lines) - 100}.0")
            self.error_text.config(state="disabled")
