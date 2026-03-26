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
)

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
        # Троттлинг обновления: полный цикл ~450 ms → не чаще 1 раза в секунду, чтобы UI не зависал
        self._update_frame_interval = 1.0  # с
        self._last_update_frame_time: float = 0.0
        self._last_processing_log_time: float = 0.0

        # Фоновая обработка full-res: пики + детекция объектов (latest-frame-wins)
        self._processing_executor = ThreadPoolExecutor(max_workers=1)
        self._processing_lock = threading.Lock()
        self._processing_future: Future | None = None
        self._pending_processing_request: tuple[Image.Image, int, bool] | None = None
        self._completed_processing_result: ProcessingResult | None = None

        # Скриншоты лупы при определении объекта
        self._do_screenshots_var = tk.BooleanVar(value=True)
        self._project_dir = os.path.dirname(os.path.abspath(__file__))
        self._screenshots_dir = os.path.join(self._project_dir, "object_screenshots")
        self._contour_screenshots_dir = os.path.join(self._project_dir, "contour_screenshots")
        self._step1_loupe_image: Image.Image | None = None  # копия лупы на шаге 1 (грубое)
        self._preview_zoomed_photo: ImageTk.PhotoImage | None = None
        self._preview_full_photo: ImageTk.PhotoImage | None = None

        self._setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_root_close)
        self._init_loupe_controller()
        self._setup_hotkeys()
        
        # Автозапуск захвата экрана после инициализации
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
        
        # Средняя панель: превью скриншотов лупы (грубое и полное разрешение)
        self._middle_frame = ttk.Frame(self._main_pane, width=140)
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
        """Средняя панель: текущая лупа и превью скриншотов."""
        # Текущая лупа (в реальном времени)
        current_loupe_frame = ttk.LabelFrame(self._middle_frame, text="Текущая лупа", padding=5)
        current_loupe_frame.pack(fill="x", pady=(0, 5))
        self._current_loupe_label = ttk.Label(current_loupe_frame, text="—", anchor="center")
        self._current_loupe_label.pack(fill="x")
        self._current_loupe_photo: ImageTk.PhotoImage | None = None
        
        # Грубое определение (сохранённый скриншот)
        zoomed_preview_frame = ttk.LabelFrame(self._middle_frame, text="Грубое определение", padding=5)
        zoomed_preview_frame.pack(fill="x", pady=(0, 5))
        self._preview_zoomed_label = ttk.Label(zoomed_preview_frame, text="—", anchor="center")
        self._preview_zoomed_label.pack(fill="x")
        
        full_preview_frame = ttk.LabelFrame(self._middle_frame, text="Полное разрешение", padding=5)
        full_preview_frame.pack(fill="x")
        self._preview_full_label = ttk.Label(full_preview_frame, text="—", anchor="center")
        self._preview_full_label.pack(fill="x")
    
    def _update_screenshot_previews(self, zoomed_image: Image.Image | None, full_image: Image.Image | None):
        """Обновление превью в средней области. PIL Image -> PhotoImage для Label."""
        if zoomed_image is not None:
            img = zoomed_image.copy()
            if img.mode != "RGB":
                img = img.convert("RGB")
            self._preview_zoomed_photo = ImageTk.PhotoImage(img)
            self._preview_zoomed_label.configure(image=self._preview_zoomed_photo, text="")
        else:
            self._preview_zoomed_label.configure(image="", text="—")
        if full_image is not None:
            img = full_image.copy()
            if img.mode != "RGB":
                img = img.convert("RGB")
            self._preview_full_photo = ImageTk.PhotoImage(img)
            self._preview_full_label.configure(image=self._preview_full_photo, text="")
        else:
            self._preview_full_label.configure(image="", text="—")
    
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

        detector_frame = ttk.LabelFrame(self._right_frame, text="Режим детектора", padding=10)
        detector_frame.pack(fill="both", expand=True)
        self._detector_mode_var = tk.StringVar(value=ImageProcessor.lines_detector_mode())
        self._detector_mode_label = ttk.Label(
            detector_frame,
            textvariable=self._detector_mode_var,
            font=("Consolas", 16, "bold"),
            anchor="center",
        )
        self._detector_mode_label.pack(fill="both", expand=True)
    
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
        self._objects_repo.save(self._full_signature_to_ids, self._zoomed_signature_to_ids, self._next_refined_id)
        self._processing_executor.shutdown(wait=False, cancel_futures=True)
        self.root.destroy()
    
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
        
        self.capture.start(
            on_frame=self._on_frame_captured,
            on_error=self._on_capture_error
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
        self._request_processing()
        now = time.time()
        if now - self._last_update_frame_time < self._update_frame_interval:
            return
        self._last_update_frame_time = now  # резервируем слот (обновим при старте _update_frame)
        self.root.after(0, self._update_frame)
    
    def _update_frame(self):
        """Синхронное обновление всех компонентов в правильном порядке."""
        # Троттлинг по факту старта в главном потоке (не по планированию из потока захвата)
        self._last_update_frame_time = time.time()
        self._consume_processing_result()
        # Лупа обновляется до отрисовки и проверки контура/сегментов при наведении на объект
        self._update_loupe()
        self._update_display()
        self._process_signature_if_pending()  # Снятие подписи ПОСЛЕ отрисовки лупы
        self._event_bus.emit("frame_captured")

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
        self._detector_mode_var.set(result.detector_mode)
        now = time.time()
        if now - self._last_processing_log_time >= 2.0:
            self._last_processing_log_time = now
            self.status_var.set(
                f"Обработка: пики {result.timings_ms['peaks']:.0f}ms, "
                f"детекция {result.timings_ms['detect']:.0f}ms, "
                f"итого {result.timings_ms['total']:.0f}ms, "
                f"detector={result.detector_mode}"
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
        
        # Вычисляем масштаб
        scale_x = canvas_width / img_width
        scale_y = canvas_height / img_height
        scale = min(scale_x, scale_y, 1.0)
        self.current_scale = scale
        
        if scale < 1.0:
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            display_img = self.current_image.resize(
                (new_width, new_height),
                Image.Resampling.LANCZOS
            )
        else:
            display_img = self.current_image
        
        self.photo = ImageTk.PhotoImage(display_img)
        
        self.canvas.delete("image")
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo, tags="image")
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
        # Обновляем пики (только рендер уже вычисленного full-res результата)
        self._update_peaks_display()
        self._process_mouse_over_object(display_img.size)

        self.status_var.set(f"Отображен скриншот {display_img.size[0]}x{display_img.size[1]}")
    
    def _update_peaks_display(self):
        """Обновление пиков: fit-to-canvas рендер готового full-res изображения."""
        if self.current_peaks_image is None:
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
        
        self.peaks_canvas.delete("image")
        self.peaks_canvas.create_image(0, 0, anchor="nw", image=self.peaks_photo, tags="image")
        # Лупа рисуется до _update_display; поднимаем её элементы поверх изображения пиков
        for tag in ("loupe", "loupe_border", "loupe_crosshair"):
            self.peaks_canvas.tag_raise(tag)
    
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
            if self._do_screenshots_var.get():
                zoomed_path = os.path.join(self._screenshots_dir, f"object_{refined_id}_zoomed.png")
                zoomed_img = None
                if os.path.isfile(zoomed_path):
                    with Image.open(zoomed_path) as im:
                        zoomed_img = im.copy()
                self._update_screenshot_previews(zoomed_img, None)
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
            self._update_objects_table()
            if self._do_screenshots_var.get():
                os.makedirs(self._screenshots_dir, exist_ok=True)
                zoomed_img = self._step1_loupe_image
                if zoomed_img is not None:
                    zoomed_path = os.path.join(self._screenshots_dir, f"object_{refined_id}_zoomed.png")
                    zoomed_img.save(zoomed_path)
                self._update_screenshot_previews(zoomed_img, None)

        # Завершаем процесс определения
        self._recognition_state = RecognitionIdle()
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
