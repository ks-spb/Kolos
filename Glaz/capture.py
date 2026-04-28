"""
Модуль захвата экрана для приложения Glaz
"""

import mss
from PIL import Image
from typing import Callable, Optional
import threading
import time


class ScreenCapture:
    """Класс для захвата скриншотов экрана."""
    
    def __init__(self):
        self.sct = mss.mss()
        self._is_capturing = False
        self._capture_thread: Optional[threading.Thread] = None
        self._selected_monitor: Optional[int] = None
        self._monitor_info: Optional[dict] = None
        self._interval_s: float = 0.16
        self._interval_lock = threading.Lock()
    
    @property
    def is_capturing(self) -> bool:
        """Статус захвата."""
        return self._is_capturing
    
    @property
    def monitor_info(self) -> Optional[dict]:
        """Информация о текущем мониторе."""
        return self._monitor_info
    
    @property
    def selected_monitor(self) -> Optional[int]:
        """Номер выбранного монитора."""
        return self._selected_monitor
    
    @selected_monitor.setter
    def selected_monitor(self, value: int):
        """Установка номера монитора."""
        self._selected_monitor = value
    
    def get_monitors(self) -> list[str]:
        """
        Получение списка доступных мониторов.
        
        Returns:
            list: Список строк с информацией о мониторах
        """
        monitors = []
        # Пропускаем первый элемент (все мониторы вместе)
        for i, monitor in enumerate(self.sct.monitors[1:], 1):
            monitors.append(f"Монитор {i} ({monitor['width']}x{monitor['height']})")
        return monitors
    
    def start(self, on_frame: Callable[[Image.Image], None], 
              on_error: Callable[[str], None],
              interval: float = 0.16):
        """
        Запуск захвата экрана.
        
        Args:
            on_frame: Callback для каждого захваченного кадра
            on_error: Callback для ошибок
            interval: Интервал между захватами в секундах
        """
        if self._selected_monitor is None:
            on_error("Монитор не выбран")
            return

        with self._interval_lock:
            self._interval_s = float(max(0.001, interval))
        self._is_capturing = True
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            args=(on_frame, on_error),
            daemon=True
        )
        self._capture_thread.start()
    
    def set_interval(self, interval: float) -> None:
        """Обновить интервал захвата (сек), можно вызывать во время захвата."""
        with self._interval_lock:
            self._interval_s = float(max(0.001, interval))

    def stop(self):
        """Остановка захвата экрана."""
        self._is_capturing = False
        self._monitor_info = None
    
    def _capture_loop(self, on_frame: Callable[[Image.Image], None],
                      on_error: Callable[[str], None]):
        """
        Внутренний цикл захвата.
        
        Args:
            on_frame: Callback для кадра
            on_error: Callback для ошибок
        """
        # Создаём экземпляр mss в этом потоке (thread-local ресурсы)
        with mss.mss() as sct:
            while self._is_capturing:
                try:
                    monitor = sct.monitors[self._selected_monitor]
                    self._monitor_info = monitor
                    screenshot = sct.grab(monitor)
                    
                    # Конвертируем в PIL Image
                    img = Image.frombytes(
                        "RGB", 
                        screenshot.size, 
                        screenshot.bgra, 
                        "raw", 
                        "BGRX"
                    )
                    
                    on_frame(img)
                    with self._interval_lock:
                        interval_s = self._interval_s
                    time.sleep(interval_s)
                    
                except Exception as e:
                    on_error(str(e))
                    break
