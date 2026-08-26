"""
Модуль лупы для приложения Glaz
"""

import json
import math
import os
import time as _time_module
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
from typing import Optional, List
from dataclasses import dataclass

from image_processor import ImageProcessor
from utils import get_cursor_pos

_DEBUG_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cursor", "debug.log")

# Сегменты, которые подсвечиваются при 1 пикселе и не записываются в подпись (БД)
DISPLAY_ONLY_SEGMENT_IDS = {4, 9, 14, 19, 48, 49, 50, 51, 52, 53, 54, 55}


@dataclass
class LoupeConfig:
    """Конфигурация лупы."""
    size: int = 100
    border_color: str = "red"
    border_width: int = 2
    crosshair_color: str = "blue"
    crosshair_highlight_color: str = "red"  # Цвет подсветки при обнаружении пиков
    crosshair_width: int = 1
    peak_sequence_threshold: int = 3  # Минимум последовательных пиковых пикселей под сегментом для подсветки
    peak_sequence_threshold_arc: int = 3  # То же для дуг


@dataclass
class LoupeData:
    """Данные о текущем состоянии лупы для сохранения."""
    image: Optional[Image.Image] = None  # PIL изображение лупы
    x: int = 0  # X координата на canvas
    y: int = 0  # Y координата на canvas
    width: int = 0  # Ширина
    height: int = 0  # Высота
    is_visible: bool = False  # Видна ли лупа
    highlighted_segment_ids: tuple[int, ...] = ()  # Индексы сегментов геометрии, загоревших красным
    peaks_invert: bool = False  # Инверсия пиков при отрисовке лупы
    geometry_scale: float = 1.0  # Масштаб геометрии (большой круг описывает объект при наведении)
    crop_bbox_source: Optional[tuple[int, int, int, int]] = None  # (left, top, right, bottom) вырезки лупы в координатах источника


class Loupe:
    """Класс для отображения лупы на canvas."""
    
    # Теги для элементов на canvas
    TAG_IMAGE = "loupe"
    TAG_BORDER = "loupe_border"
    TAG_CROSSHAIR = "loupe_crosshair"
    
    def __init__(self, canvas: tk.Canvas, config: Optional[LoupeConfig] = None):
        """
        Инициализация лупы.
        
        Args:
            canvas: Canvas для отображения лупы
            config: Конфигурация лупы
        """
        self.canvas = canvas
        self.config = config or LoupeConfig()
        self._photo: Optional[ImageTk.PhotoImage] = None
    
    def clear(self):
        """Очистка лупы с canvas."""
        self.canvas.delete(self.TAG_IMAGE)
        self.canvas.delete(self.TAG_BORDER)
        self.canvas.delete(self.TAG_CROSSHAIR)
    
    def draw(self, image: ImageTk.PhotoImage, x: int, y: int,
             width: int, height: int, peaks_pil_image: Optional[Image.Image] = None,
             out_highlighted_ids: Optional[List[int]] = None, peaks_invert: bool = False,
             geometry_scale: float = 1.0):
        """
        Отрисовка лупы на canvas.

        Args:
            image: Изображение для отображения
            x: X координата (левый верхний угол)
            y: Y координата (левый верхний угол)
            width: Ширина области
            height: Высота области
            peaks_pil_image: PIL изображение пиков для анализа перекрестия
            out_highlighted_ids: Если задан, сюда записываются индексы сегментов, загоревших красным
            peaks_invert: При True пики на изображении — белые
            geometry_scale: Масштаб геометрии (1.0 = по умолчанию, большой круг описывает объект при >1)
        """
        self.clear()

        # Сохраняем ссылку на изображение
        self._photo = image

        # Рисуем изображение
        self.canvas.create_image(x, y, anchor="nw", image=image, tags=self.TAG_IMAGE)

        # Рисуем рамку
        self.canvas.create_rectangle(
            x, y, x + width, y + height,
            outline=self.config.border_color,
            width=self.config.border_width,
            tags=self.TAG_BORDER
        )

        # Рисуем перекрестие с анализом пиков
        if peaks_pil_image is not None:
            self._draw_smart_crosshair(x, y, width, height, peaks_pil_image, out_highlighted_ids, peaks_invert, geometry_scale)
    
    def _has_peak_sequence(self, pixels: list, threshold: int = 3, peaks_invert: bool = False) -> bool:
        """
        Проверка наличия последовательности пиков.
        
        Args:
            pixels: Список значений пикселей (0 = чёрный, 255 = белый)
            threshold: Минимальное количество последовательных пиков
            peaks_invert: При True пик = белый (>= 128), иначе пик = чёрный (< 128)
            
        Returns:
            True если найдена последовательность >= threshold
        """
        is_peak = (lambda p: p >= 128) if peaks_invert else (lambda p: p < 128)
        consecutive = 0
        for pixel in pixels:
            if is_peak(pixel):
                consecutive += 1
                if consecutive >= threshold:
                    return True
            else:
                consecutive = 0
        return False
    
    def _get_line_pixels(self, x1: int, y1: int, x2: int, y2: int, 
                         pixels, img_width: int, img_height: int) -> list:
        """
        Получение значений пикселей вдоль линии (алгоритм Брезенхема).
        
        Args:
            x1, y1: Начальная точка (локальные координаты)
            x2, y2: Конечная точка (локальные координаты)
            pixels: Доступ к пикселям изображения
            img_width, img_height: Размеры изображения
            
        Returns:
            Список значений пикселей вдоль линии
        """
        result = []
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        x, y = x1, y1
        while True:
            if 0 <= x < img_width and 0 <= y < img_height:
                result.append(pixels[x, y])
            
            if x == x2 and y == y2:
                break
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        
        return result
    
    def _get_line_color(self, x1: int, y1: int, x2: int, y2: int,
                        pixels, img_width: int, img_height: int,
                        threshold: int, default_color: str, highlight_color: str,
                        peaks_invert: bool = False) -> str:
        """
        Определение цвета линии на основе анализа пикселей под ней.

        Returns:
            Цвет линии (default или highlight)
        """
        line_pixels = self._get_line_pixels(x1, y1, x2, y2, pixels, img_width, img_height)
        return highlight_color if self._has_peak_sequence(line_pixels, threshold, peaks_invert) else default_color
    
    def _get_arc_pixels(self, cx: int, cy: int, radius: float, 
                        start_angle: float, end_angle: float,
                        pixels, img_width: int, img_height: int) -> list:
        """
        Получение значений пикселей вдоль дуги.
        
        Args:
            cx, cy: Центр круга (локальные координаты)
            radius: Радиус
            start_angle, end_angle: Углы в градусах (против часовой от оси X)
            pixels: Доступ к пикселям изображения
            img_width, img_height: Размеры изображения
            
        Returns:
            Список значений пикселей вдоль дуги
        """
        result = []
        last_x, last_y = None, None
        arc_length = abs(end_angle - start_angle) * math.pi * radius / 180
        num_points = max(int(arc_length * 2), 10)
        
        for i in range(num_points + 1):
            angle = math.radians(start_angle + (end_angle - start_angle) * i / num_points)
            x = int(cx + radius * math.cos(angle))
            y = int(cy - radius * math.sin(angle))  # Y инвертирован
            if 0 <= x < img_width and 0 <= y < img_height and (x, y) != (last_x, last_y):
                result.append(pixels[x, y])
                last_x, last_y = x, y
        return result

    def _get_arc_pixel_coords(self, cx: int, cy: int, radius: float,
                              start_angle: float, end_angle: float,
                              img_width: int, img_height: int) -> list:
        """Координаты (x, y) пикселей вдоль дуги (без повторов)."""
        result = []
        last_x, last_y = None, None
        arc_length = abs(end_angle - start_angle) * math.pi * radius / 180
        num_points = max(int(arc_length * 2), 10)
        for i in range(num_points + 1):
            angle = math.radians(start_angle + (end_angle - start_angle) * i / num_points)
            px = int(cx + radius * math.cos(angle))
            py = int(cy - radius * math.sin(angle))
            if 0 <= px < img_width and 0 <= py < img_height and (px, py) != (last_x, last_y):
                result.append((px, py))
                last_x, last_y = px, py
        return result

    def _draw_smart_crosshair(self, x: int, y: int, width: int, height: int,
                               peaks_image: Image.Image,
                               out_highlighted_ids: Optional[List[int]] = None,
                               peaks_invert: bool = False,
                               geometry_scale: float = 1.0):
        """
        Отрисовка перекрестия с подсветкой сегментов при обнаружении пиков.

        Args:
            x: X координата левого верхнего угла на canvas
            y: Y координата левого верхнего угла на canvas
            width: Ширина области
            height: Высота области
            peaks_image: PIL изображение пиков для анализа
            out_highlighted_ids: Если задан, сюда добавляются индексы подсвеченных сегментов
            peaks_invert: При True пики на изображении — белые
            geometry_scale: Масштаб геометрии (большой круг описывает объект при наведении)
        """
        cx_canvas = x + width // 2  # Центр на canvas
        cy_canvas = y + height // 2
        cx_local = width // 2  # Центр в локальных координатах
        cy_local = height // 2

        threshold = self.config.peak_sequence_threshold
        default_color = self.config.crosshair_color
        highlight_color = self.config.crosshair_highlight_color

        pixels = peaks_image.load()
        img_w, img_h = peaks_image.size
        seg_idx = [0]  # счётчик сегментов в замыкании

        is_peak_pixel = (lambda p: p >= 128) if peaks_invert else (lambda p: p < 128)

        def draw_line(x1_local, y1_local, x2_local, y2_local, x1_canvas, y1_canvas, x2_canvas, y2_canvas):
            eff_threshold = 1 if seg_idx[0] in DISPLAY_ONLY_SEGMENT_IDS else threshold
            color = self._get_line_color(x1_local, y1_local, x2_local, y2_local,
                                         pixels, img_w, img_h, eff_threshold, default_color, highlight_color, peaks_invert)
            if out_highlighted_ids is not None and color == highlight_color and seg_idx[0] not in DISPLAY_ONLY_SEGMENT_IDS:
                out_highlighted_ids.append(seg_idx[0])
            seg_idx[0] += 1
            self.canvas.create_line(x1_canvas, y1_canvas, x2_canvas, y2_canvas,
                                    fill=color, width=self.config.crosshair_width, tags=self.TAG_CROSSHAIR)

        def draw_line_per_pixel(x1_local, y1_local, x2_local, y2_local, x_origin, y_origin):
            """Отрисовка луча по 1 пикселю: каждый пиксель зажигается отдельно (сегменты 4, 9, 14, 19)."""
            if y1_local == y2_local:
                # Горизонталь
                x_start, x_end = min(x1_local, x2_local), max(x1_local, x2_local)
                for px in range(x_start, x_end + 1):
                    if 0 <= px < img_w and 0 <= y1_local < img_h:
                        val = pixels[px, y1_local]
                        color = highlight_color if is_peak_pixel(val) else default_color
                        self.canvas.create_line(
                            x_origin + px, y_origin + y1_local,
                            x_origin + px + 1, y_origin + y1_local,
                            fill=color, width=self.config.crosshair_width, tags=self.TAG_CROSSHAIR
                        )
            else:
                # Вертикаль
                y_start, y_end = min(y1_local, y2_local), max(y1_local, y2_local)
                for py in range(y_start, y_end + 1):
                    if 0 <= x1_local < img_w and 0 <= py < img_h:
                        val = pixels[x1_local, py]
                        color = highlight_color if is_peak_pixel(val) else default_color
                        self.canvas.create_line(
                            x_origin + x1_local, y_origin + py,
                            x_origin + x1_local, y_origin + py + 1,
                            fill=color, width=self.config.crosshair_width, tags=self.TAG_CROSSHAIR
                        )
            seg_idx[0] += 1

        # Базовые радиусы (масштабируются geometry_scale)
        s = geometry_scale
        r6 = 6 * s
        r12 = 12 * s
        r_small = int(6 * math.sqrt(2) * s)   # ≈ 8 для квадрата 12x12
        r_large = int(12 * math.sqrt(2) * s)  # ≈ 17 для квадрата 24x24
        
        # === Перекрестие (20 сегментов: по 5 на каждое направление) ===
        # Влево: центр → -r6 → -r_small → -r12 → -r_large → край
        draw_line(cx_local, cy_local, cx_local-r6, cy_local, cx_canvas, cy_canvas, cx_canvas-r6, cy_canvas)
        draw_line(cx_local-r6, cy_local, cx_local-r_small, cy_local, cx_canvas-r6, cy_canvas, cx_canvas-r_small, cy_canvas)
        draw_line(cx_local-r_small, cy_local, cx_local-r12, cy_local, cx_canvas-r_small, cy_canvas, cx_canvas-r12, cy_canvas)
        draw_line(cx_local-r12, cy_local, cx_local-r_large, cy_local, cx_canvas-r12, cy_canvas, cx_canvas-r_large, cy_canvas)
        draw_line_per_pixel(cx_local - r_large, cy_local, 0, cy_local, x, y)
        # Вправо: центр → +r6 → +r_small → +r12 → +r_large → край
        draw_line(cx_local, cy_local, cx_local+r6, cy_local, cx_canvas, cy_canvas, cx_canvas+r6, cy_canvas)
        draw_line(cx_local+r6, cy_local, cx_local+r_small, cy_local, cx_canvas+r6, cy_canvas, cx_canvas+r_small, cy_canvas)
        draw_line(cx_local+r_small, cy_local, cx_local+r12, cy_local, cx_canvas+r_small, cy_canvas, cx_canvas+r12, cy_canvas)
        draw_line(cx_local+r12, cy_local, cx_local+r_large, cy_local, cx_canvas+r12, cy_canvas, cx_canvas+r_large, cy_canvas)
        draw_line_per_pixel(cx_local + r_large, cy_local, width - 1, cy_local, x, y)
        # Вверх: центр → -r6 → -r_small → -r12 → -r_large → край
        draw_line(cx_local, cy_local, cx_local, cy_local-r6, cx_canvas, cy_canvas, cx_canvas, cy_canvas-r6)
        draw_line(cx_local, cy_local-r6, cx_local, cy_local-r_small, cx_canvas, cy_canvas-r6, cx_canvas, cy_canvas-r_small)
        draw_line(cx_local, cy_local-r_small, cx_local, cy_local-r12, cx_canvas, cy_canvas-r_small, cx_canvas, cy_canvas-r12)
        draw_line(cx_local, cy_local-r12, cx_local, cy_local-r_large, cx_canvas, cy_canvas-r12, cx_canvas, cy_canvas-r_large)
        draw_line_per_pixel(cx_local, cy_local - r_large, cx_local, 0, x, y)
        # Вниз: центр → +r6 → +r_small → +r12 → +r_large → край
        draw_line(cx_local, cy_local, cx_local, cy_local+r6, cx_canvas, cy_canvas, cx_canvas, cy_canvas+r6)
        draw_line(cx_local, cy_local+r6, cx_local, cy_local+r_small, cx_canvas, cy_canvas+r6, cx_canvas, cy_canvas+r_small)
        draw_line(cx_local, cy_local+r_small, cx_local, cy_local+r12, cx_canvas, cy_canvas+r_small, cx_canvas, cy_canvas+r12)
        draw_line(cx_local, cy_local+r12, cx_local, cy_local+r_large, cx_canvas, cy_canvas+r12, cx_canvas, cy_canvas+r_large)
        draw_line_per_pixel(cx_local, cy_local + r_large, cx_local, height - 1, x, y)
        
        # === Квадрат 12x12 (8 сегментов: по 2 на каждую сторону) ===
        draw_line(cx_local-r6, cy_local-r6, cx_local, cy_local-r6, cx_canvas-r6, cy_canvas-r6, cx_canvas, cy_canvas-r6)
        draw_line(cx_local, cy_local-r6, cx_local+r6, cy_local-r6, cx_canvas, cy_canvas-r6, cx_canvas+r6, cy_canvas-r6)
        draw_line(cx_local+r6, cy_local-r6, cx_local+r6, cy_local, cx_canvas+r6, cy_canvas-r6, cx_canvas+r6, cy_canvas)
        draw_line(cx_local+r6, cy_local, cx_local+r6, cy_local+r6, cx_canvas+r6, cy_canvas, cx_canvas+r6, cy_canvas+r6)
        draw_line(cx_local+r6, cy_local+r6, cx_local, cy_local+r6, cx_canvas+r6, cy_canvas+r6, cx_canvas, cy_canvas+r6)
        draw_line(cx_local, cy_local+r6, cx_local-r6, cy_local+r6, cx_canvas, cy_canvas+r6, cx_canvas-r6, cy_canvas+r6)
        draw_line(cx_local-r6, cy_local+r6, cx_local-r6, cy_local, cx_canvas-r6, cy_canvas+r6, cx_canvas-r6, cy_canvas)
        draw_line(cx_local-r6, cy_local, cx_local-r6, cy_local-r6, cx_canvas-r6, cy_canvas, cx_canvas-r6, cy_canvas-r6)
        
        # === Квадрат 24x24 (8 сегментов: по 2 на каждую сторону) ===
        draw_line(cx_local-r12, cy_local-r12, cx_local, cy_local-r12, cx_canvas-r12, cy_canvas-r12, cx_canvas, cy_canvas-r12)
        draw_line(cx_local, cy_local-r12, cx_local+r12, cy_local-r12, cx_canvas, cy_canvas-r12, cx_canvas+r12, cy_canvas-r12)
        draw_line(cx_local+r12, cy_local-r12, cx_local+r12, cy_local, cx_canvas+r12, cy_canvas-r12, cx_canvas+r12, cy_canvas)
        draw_line(cx_local+r12, cy_local, cx_local+r12, cy_local+r12, cx_canvas+r12, cy_canvas, cx_canvas+r12, cy_canvas+r12)
        draw_line(cx_local+r12, cy_local+r12, cx_local, cy_local+r12, cx_canvas+r12, cy_canvas+r12, cx_canvas, cy_canvas+r12)
        draw_line(cx_local, cy_local+r12, cx_local-r12, cy_local+r12, cx_canvas, cy_canvas+r12, cx_canvas-r12, cy_canvas+r12)
        draw_line(cx_local-r12, cy_local+r12, cx_local-r12, cy_local, cx_canvas-r12, cy_canvas+r12, cx_canvas-r12, cy_canvas)
        draw_line(cx_local-r12, cy_local, cx_local-r12, cy_local-r12, cx_canvas-r12, cy_canvas, cx_canvas-r12, cy_canvas-r12)
        
        # === Ромб (4 стороны) ===
        draw_line(cx_local, cy_local-r12, cx_local+r12, cy_local, cx_canvas, cy_canvas-r12, cx_canvas+r12, cy_canvas)
        draw_line(cx_local+r12, cy_local, cx_local, cy_local+r12, cx_canvas+r12, cy_canvas, cx_canvas, cy_canvas+r12)
        draw_line(cx_local, cy_local+r12, cx_local-r12, cy_local, cx_canvas, cy_canvas+r12, cx_canvas-r12, cy_canvas)
        draw_line(cx_local-r12, cy_local, cx_local, cy_local-r12, cx_canvas-r12, cy_canvas, cx_canvas, cy_canvas-r12)
        
        # === Круги, описывающие квадраты ===
        r_small_f = 6 * math.sqrt(2) * s
        r_large_f = 12 * math.sqrt(2) * s

        threshold_arc = self.config.peak_sequence_threshold_arc

        def draw_arc(radius: float, start_angle: float, end_angle: float):
            arc_pixels = self._get_arc_pixels(cx_local, cy_local, radius,
                                              start_angle, end_angle, pixels, img_w, img_h)
            eff_threshold_arc = 1 if seg_idx[0] in DISPLAY_ONLY_SEGMENT_IDS else threshold_arc
            color = highlight_color if self._has_peak_sequence(arc_pixels, eff_threshold_arc, peaks_invert) else default_color
            if out_highlighted_ids is not None and color == highlight_color and seg_idx[0] not in DISPLAY_ONLY_SEGMENT_IDS:
                out_highlighted_ids.append(seg_idx[0])
            seg_idx[0] += 1
            bbox = [cx_canvas - radius, cy_canvas - radius,
                    cx_canvas + radius, cy_canvas + radius]
            self.canvas.create_arc(bbox, start=start_angle, extent=end_angle-start_angle,
                                   style='arc', outline=color,
                                   width=self.config.crosshair_width, tags=self.TAG_CROSSHAIR)

        def draw_arc_per_pixel(radius: float, start_angle: float, end_angle: float, x_origin: int, y_origin: int):
            """Отрисовка дуги по 1 пикселю (сегменты 48-55): каждый пиксель зажигается отдельно."""
            coords = self._get_arc_pixel_coords(cx_local, cy_local, radius, start_angle, end_angle, img_w, img_h)
            for px, py in coords:
                val = pixels[px, py]
                color = highlight_color if is_peak_pixel(val) else default_color
                self.canvas.create_line(
                    x_origin + px, y_origin + py,
                    x_origin + px + 1, y_origin + py,
                    fill=color, width=self.config.crosshair_width, tags=self.TAG_CROSSHAIR
                )
            seg_idx[0] += 1
        
        # Круг для квадрата 12x12 (8 сегментов: пересечения с центральными линиями и ромбом)
        draw_arc(r_small_f, 0, 45)
        draw_arc(r_small_f, 45, 90)
        draw_arc(r_small_f, 90, 135)
        draw_arc(r_small_f, 135, 180)
        draw_arc(r_small_f, 180, 225)
        draw_arc(r_small_f, 225, 270)
        draw_arc(r_small_f, 270, 315)
        draw_arc(r_small_f, 315, 360)
        
        # Круг для квадрата 24x24 (8 сегментов): по 1 пикселю
        draw_arc_per_pixel(r_large_f, 0, 45, x, y)
        draw_arc_per_pixel(r_large_f, 45, 90, x, y)
        draw_arc_per_pixel(r_large_f, 90, 135, x, y)
        draw_arc_per_pixel(r_large_f, 135, 180, x, y)
        draw_arc_per_pixel(r_large_f, 180, 225, x, y)
        draw_arc_per_pixel(r_large_f, 225, 270, x, y)
        draw_arc_per_pixel(r_large_f, 270, 315, x, y)
        draw_arc_per_pixel(r_large_f, 315, 360, x, y)


class LoupeController:
    """Контроллер для управления лупами на основном canvas и canvas пиков."""
    
    def __init__(self, main_canvas: Optional[tk.Canvas], peaks_canvas: tk.Canvas,
                 loupe_size: int = 100):
        """
        Инициализация контроллера луп.
        
        Args:
            main_canvas: Основной canvas для скриншота; None, если он скрыт
            peaks_canvas: Canvas для пиков
            loupe_size: Размер лупы в пикселях
        """
        self.loupe_size = loupe_size
        
        # Основная лупа не создаётся, когда предпросмотр скриншота скрыт.
        self.main_loupe = Loupe(main_canvas) if main_canvas is not None else None
        self.peaks_loupe = Loupe(peaks_canvas)
        
        # Хранение PhotoImage для предотвращения сборки мусора
        self._main_photo: Optional[ImageTk.PhotoImage] = None
        self._peaks_photo: Optional[ImageTk.PhotoImage] = None
        
        # Данные о текущей лупе пиков для сохранения
        self._peaks_loupe_data = LoupeData()
        self._last_highlighted_segment_ids: tuple = ()
        self._last_peaks_image: Optional[Image.Image] = None  # Последнее изображение пиков лупы

    @property
    def peaks_loupe_data(self) -> LoupeData:
        """Данные о лупе пиков для сохранения."""
        return self._peaks_loupe_data

    def get_last_highlighted_segment_ids(self) -> tuple:
        """Индексы сегментов геометрии лупы, загоревших красным при последней отрисовке."""
        return self._last_highlighted_segment_ids

    @staticmethod
    def _spiral_find_first_peak(pixels, w: int, h: int, is_peak) -> Optional[tuple[int, int]]:
        """Поиск ближайшей к центру пиковой точки спиралью от центра с шагом радиуса 2 px."""
        cx, cy = w // 2, h // 2
        max_r = min(w, h) // 2 + 1
        for r in range(0, max_r, 2):
            if r == 0:
                if 0 <= cx < w and 0 <= cy < h and is_peak(pixels[cx, cy]):
                    return (cx, cy)
                continue
            num_steps = max(8, int(2 * math.pi * r / 2))
            for i in range(num_steps):
                angle = 2 * math.pi * i / num_steps
                x = int(cx + r * math.cos(angle))
                y = int(cy + r * math.sin(angle))
                if 0 <= x < w and 0 <= y < h and is_peak(pixels[x, y]):
                    return (x, y)
        return None

    @staticmethod
    def _trace_contour_4(pixels, w: int, h: int, start_x: int, start_y: int, is_peak) -> List[tuple[int, int]]:
        """Обход контура по 4-связности, приоритет направлений: вверх, вправо, вниз, влево."""
        # (dx, dy): вверх, вправо, вниз, влево
        steps = [(0, -1), (1, 0), (0, 1), (-1, 0)]
        contour: List[tuple[int, int]] = [(start_x, start_y)]
        current = (start_x, start_y)
        prev = None
        max_iter = 4 * w * h
        for _ in range(max_iter):
            found = None
            for dx, dy in steps:
                nx, ny = current[0] + dx, current[1] + dy
                if not (0 <= nx < w and 0 <= ny < h):
                    continue
                if (nx, ny) == prev:
                    continue
                if is_peak(pixels[nx, ny]):
                    found = (nx, ny)
                    break
            if found is None:
                break
            if found == (start_x, start_y) and len(contour) >= 3:
                break
            contour.append(found)
            prev = current
            current = found
        return contour

    def find_contour_center_and_image(self) -> tuple[Optional[Image.Image], Optional[float], Optional[float]]:
        """
        Спиральный поиск первой пиковой точки, обход контура, рисование геометрии и центр bbox.
        Returns:
            (PIL Image с нарисованным контуром для сохранения, center_x, center_y в координатах лупы)
            или (None, None, None) если пик не найден или контур пустой.
        """
        data = self._peaks_loupe_data
        if not data.is_visible or data.image is None:
            return (None, None, None)
        img = data.image
        pixels = img.load()
        w, h = img.size
        is_peak = (lambda p: p >= 128) if data.peaks_invert else (lambda p: p < 128)
        first = self._spiral_find_first_peak(pixels, w, h, is_peak)
        if first is None:
            return (None, None, None)
        sx, sy = first
        contour = self._trace_contour_4(pixels, w, h, sx, sy, is_peak)
        if len(contour) < 2:
            return (None, None, None)
        xs = [p[0] for p in contour]
        ys = [p[1] for p in contour]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0
        # Рисуем контур на отдельном изображении (белый фон, контур чёрный)
        out = Image.new("RGB", (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(out)
        for i in range(len(contour) - 1):
            x1, y1 = contour[i]
            x2, y2 = contour[i + 1]
            draw.line([(x1, y1), (x2, y2)], fill=(0, 0, 0), width=1)
        if len(contour) > 1:
            draw.line([contour[-1], contour[0]], fill=(0, 0, 0), width=1)
        # Отмечаем центр
        r = 2
        draw.ellipse((center_x - r, center_y - r, center_x + r, center_y + r), fill=(255, 0, 0), outline=(255, 0, 0))
        return (out, center_x, center_y)

    def has_segment14_and_53_or_54_peaks(self) -> tuple:
        """
        Проверка: есть ли горящий пиксель на сегменте 14 (луч вверх) и на одной из дуг 53 или 54.
        Returns:
            (has_peak_on_segment_14, has_peak_on_53_or_54)
        """
        data = self._peaks_loupe_data
        if not data.is_visible or data.image is None:
            return (False, False)
        img = data.image
        pixels = img.load()
        w, h = img.size
        cx_local = w // 2
        cy_local = h // 2
        s = data.geometry_scale
        r_large = 12 * math.sqrt(2) * s
        r_large_int = int(r_large)
        is_peak = (lambda p: p >= 128) if data.peaks_invert else (lambda p: p < 128)

        seg14_peak_coords = []
        seg14_sample_values = []
        for py in range(0, cy_local - r_large_int + 1):
            if 0 <= cx_local < w and 0 <= py < h:
                val = pixels[cx_local, py]
                if len(seg14_sample_values) < 10:
                    seg14_sample_values.append((py, val))
                if is_peak(val):
                    seg14_peak_coords.append(py)
        has_14 = len(seg14_peak_coords) > 0

        # Сегмент 53: верхняя левая часть (90-135°)
        coords_53 = self._get_arc_pixel_coords(cx_local, cy_local, r_large, 90, 135, w, h)
        # Сегмент 54: верхняя правая часть (45-90°)
        coords_54 = self._get_arc_pixel_coords(cx_local, cy_local, r_large, 45, 90, w, h)
        seg53_peak_coords = []
        seg54_peak_coords = []
        seg53_sample_values = []
        seg54_sample_values = []
        for px, py in coords_53:
            val = pixels[px, py]
            if len(seg53_sample_values) < 10:
                seg53_sample_values.append(((px, py), val))
            if is_peak(val):
                seg53_peak_coords.append((px, py))
        for px, py in coords_54:
            val = pixels[px, py]
            if len(seg54_sample_values) < 10:
                seg54_sample_values.append(((px, py), val))
            if is_peak(val):
                seg54_peak_coords.append((px, py))
        has_53 = len(seg53_peak_coords) > 0
        has_54 = len(seg54_peak_coords) > 0
        has_53_54 = has_53 or has_54

        # #region agent log
        try:
            with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as _f:
                _f.write(json.dumps({"location": "loupe.py:has_segment14_and_53_or_54_peaks", "message": "segment_check_detailed", "data": {"has_14": has_14, "has_53": has_53, "has_54": has_54, "has_53_54": has_53_54, "w": w, "h": h, "r_large": r_large, "r_large_int": r_large_int, "cy_local": cy_local, "cx_local": cx_local, "seg14_y_range": [0, cy_local - r_large_int + 1], "seg14_peak_count": len(seg14_peak_coords), "seg14_peak_y_coords": seg14_peak_coords[:10], "seg14_sample_values": seg14_sample_values, "num_coords_53": len(coords_53), "num_coords_54": len(coords_54), "seg53_peak_count": len(seg53_peak_coords), "seg53_peak_coords": seg53_peak_coords[:10], "seg53_sample_values": seg53_sample_values, "seg54_peak_count": len(seg54_peak_coords), "seg54_peak_coords": seg54_peak_coords[:10], "seg54_sample_values": seg54_sample_values, "peaks_invert": data.peaks_invert}, "timestamp": _time_module.time()}, ensure_ascii=False) + "\n")
        except OSError:
            pass
        # #endregion
        return (has_14, has_53_54)

    def clear_all(self):
        """Очистка всех луп."""
        if self.main_loupe is not None:
            self.main_loupe.clear()
        self.peaks_loupe.clear()
        self._peaks_loupe_data = LoupeData()
        self._last_highlighted_segment_ids = ()
    
    def update(self, current_image: Optional[Image.Image],
               monitor_info: Optional[dict],
               current_scale: float,
               peaks_scale_percent: int,
               peaks_threshold: int,
               peaks_invert: bool,
               loupe_size_override: Optional[int] = None,
               crop_bbox_source: Optional[tuple[int, int, int, int]] = None,
               obj_bbox_source: Optional[tuple[float, float, float, float]] = None):
        """
        Обновление луп на основе позиции курсора.

        Args:
            current_image: Текущее захваченное изображение
            monitor_info: Информация о мониторе
            current_scale: Текущий масштаб отображения
            peaks_scale_percent: Масштаб пиков в процентах
            peaks_threshold: Порог для детекции пиков
            peaks_invert: Инверсия пиков
            loupe_size_override: Если задан — вырезается область размером loupe_size_override и масштабируется до loupe_size.
                                 > loupe_size: отдаление (больший вырез уменьшается)
                                 < loupe_size: приближение (меньший вырез увеличивается)
            crop_bbox_source: Если задан — вырезается область по этим координатам (left, top, right, bottom)
                              в координатах исходного изображения вместо вырезки вокруг курсора
            obj_bbox_source: Bbox объекта (left, top, right, bottom) в координатах источника.
                             Используется для масштабирования геометрии: большой круг описывает объект.
        """
        if current_image is None or monitor_info is None:
            self.clear_all()
            return
        
        # Получаем координаты для позиционирования лупы
        cursor_x, cursor_y = get_cursor_pos()
        rel_x = cursor_x - monitor_info['left']
        rel_y = cursor_y - monitor_info['top']
        
        # Проверяем, находится ли курсор на сканируемом мониторе
        if (rel_x < 0 or rel_y < 0 or 
            rel_x >= monitor_info['width'] or rel_y >= monitor_info['height']):
            self.clear_all()
            return
        
        img_width, img_height = current_image.size
        
        # Определяем координаты вырезки и geometry_scale
        geometry_scale = 1.0
        if crop_bbox_source is not None:
            # Вырезка по bbox объекта (в координатах исходного изображения)
            left, top, right, bottom = crop_bbox_source
            left = max(0, min(left, img_width))
            top = max(0, min(top, img_height))
            right = max(0, min(right, img_width))
            bottom = max(0, min(bottom, img_height))
            use_bbox_crop = True
            # Центр лупы — центр объекта (crop центрирован на объекте)
            rel_x = (left + right) / 2.0
            rel_y = (top + bottom) / 2.0
            # Вычисляем geometry_scale: большой круг описывает объект
            if obj_bbox_source is not None:
                ol, ot, or_, ob = obj_bbox_source
                obj_w = or_ - ol
                obj_h = ob - ot
                crop_w = right - left
                crop_h = bottom - top
                if crop_w > 0 and crop_h > 0:
                    obj_w_loupe = obj_w * self.loupe_size / crop_w
                    obj_h_loupe = obj_h * self.loupe_size / crop_h
                    obj_diag_loupe = math.hypot(obj_w_loupe, obj_h_loupe)
                    r_large_base = 12 * math.sqrt(2)
                    geometry_scale = (obj_diag_loupe / 2.0) / r_large_base if r_large_base > 0 else 1.0
                    # Cap 2.0: при scale >2 отрисовка 48 линий+16 дуг зависает UI (Windows/tkinter)
                    geometry_scale = max(0.4, min(2.0, geometry_scale))
        else:
            # Вырезка вокруг курсора (стандартный режим)
            crop_size = loupe_size_override if loupe_size_override is not None else self.loupe_size
            half_crop = crop_size // 2
            left = max(0, rel_x - half_crop)
            top = max(0, rel_y - half_crop)
            right = min(img_width, rel_x + half_crop)
            bottom = min(img_height, rel_y + half_crop)
            use_bbox_crop = False
        
        # Если область слишком маленькая, не показываем лупу
        if right - left < 10 or bottom - top < 10:
            self._peaks_loupe_data = LoupeData()
            self._last_highlighted_segment_ids = ()
            return
        
        # Вырезаем область из изображения
        loupe_img = current_image.crop((left, top, right, bottom))
        # Масштабируем вырез до стандартного размера лупы
        # Для bbox всегда масштабируем, для курсора только если crop_size != loupe_size
        if use_bbox_crop or (not use_bbox_crop and crop_size != self.loupe_size):
            loupe_img = loupe_img.resize((self.loupe_size, self.loupe_size), Image.Resampling.LANCZOS)

        loupe_width = self.loupe_size
        loupe_height = self.loupe_size
        # Позиция на main canvas: центр лупы совпадает с курсором
        canvas_x = int(rel_x * current_scale)
        canvas_y = int(rel_y * current_scale)
        loupe_canvas_x = canvas_x - loupe_width // 2
        loupe_canvas_y = canvas_y - loupe_height // 2
        
        # Отрисовка на основном canvas (без перекрестия), если он видим.
        if self.main_loupe is not None:
            self._main_photo = ImageTk.PhotoImage(loupe_img)
            self.main_loupe.draw(
                self._main_photo,
                loupe_canvas_x, loupe_canvas_y,
                loupe_width, loupe_height,
                peaks_pil_image=None  # Без перекрестия
            )
        
        # Для bbox crop не нормализуем — crop уже центрирован на объекте, нормализация
        # краёв обрезала объект. Для курсорной лупы используем оригинал.
        loupe_img_normalized = loupe_img

        # Создаём изображение пиков для лупы (с нормализованным фоном)
        loupe_peaks = ImageProcessor.detect_color_peaks(
            loupe_img_normalized, peaks_threshold, peaks_invert
        )
        self._peaks_photo = ImageTk.PhotoImage(loupe_peaks)
        
        # Позиция на peaks canvas
        scale_factor = peaks_scale_percent / 100.0
        peaks_canvas_x = int(loupe_canvas_x * scale_factor)
        peaks_canvas_y = int(loupe_canvas_y * scale_factor)
        
        # Сбор индексов подсвеченных сегментов
        highlighted_ids: List[int] = []
        # Отдать управление event loop перед тяжёлой отрисовкой — иначе при большом
        # geometry_scale отрисовка 48 линий + 16 дуг может зависнуть UI (Windows/tkinter)
        try:
            root = self.peaks_loupe.canvas.winfo_toplevel()
            root.update_idletasks()
        except Exception:
            pass
        # Отрисовка на peaks canvas (с умным перекрестием)
        self.peaks_loupe.draw(
            self._peaks_photo,
            peaks_canvas_x, peaks_canvas_y,
            loupe_width, loupe_height,
            peaks_pil_image=loupe_peaks,
            out_highlighted_ids=highlighted_ids,
            peaks_invert=peaks_invert,
            geometry_scale=geometry_scale,
        )
        self._last_highlighted_segment_ids = tuple(highlighted_ids)
        # Сохраняем данные о лупе пиков для возможности сохранения
        self._peaks_loupe_data = LoupeData(
            image=loupe_peaks,
            x=peaks_canvas_x,
            y=peaks_canvas_y,
            width=loupe_width,
            height=loupe_height,
            is_visible=True,
            highlighted_segment_ids=self._last_highlighted_segment_ids,
            peaks_invert=peaks_invert,
            geometry_scale=geometry_scale,
            crop_bbox_source=(int(left), int(top), int(right), int(bottom)),
        )
        # Сохраняем копию изображения пиков только когда используется crop_bbox_source
        if crop_bbox_source is not None:
            self._last_peaks_image = loupe_peaks.copy()

    def _has_peak_sequence(self, pixels: list, threshold: int = 3, peaks_invert: bool = False) -> bool:
        """
        Проверка наличия последовательности пиков.
        peaks_invert: при True пик = белый (>= 128), иначе чёрный (< 128).
        """
        is_peak = (lambda p: p >= 128) if peaks_invert else (lambda p: p < 128)
        consecutive = 0
        for pixel in pixels:
            if is_peak(pixel):
                consecutive += 1
                if consecutive >= threshold:
                    return True
            else:
                consecutive = 0
        return False
    
    def _get_line_pixels(self, x1: int, y1: int, x2: int, y2: int, 
                         pixels, img_width: int, img_height: int) -> list:
        """Получение значений пикселей вдоль линии (алгоритм Брезенхема)."""
        result = []
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        x, y = x1, y1
        while True:
            if 0 <= x < img_width and 0 <= y < img_height:
                result.append(pixels[x, y])
            if x == x2 and y == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        return result
    
    def _get_arc_pixels(self, cx: int, cy: int, radius: float, 
                        start_angle: float, end_angle: float,
                        pixels, img_width: int, img_height: int) -> list:
        """Получение значений пикселей вдоль дуги (без повторного учёта одного пикселя)."""
        result = []
        last_x, last_y = None, None
        arc_length = abs(end_angle - start_angle) * math.pi * radius / 180
        num_points = max(int(arc_length * 2), 10)
        
        for i in range(num_points + 1):
            angle = math.radians(start_angle + (end_angle - start_angle) * i / num_points)
            x = int(cx + radius * math.cos(angle))
            y = int(cy - radius * math.sin(angle))
            if 0 <= x < img_width and 0 <= y < img_height and (x, y) != (last_x, last_y):
                result.append(pixels[x, y])
                last_x, last_y = x, y
        return result

    def _get_arc_pixel_coords(self, cx: int, cy: int, radius: float,
                              start_angle: float, end_angle: float,
                              img_width: int, img_height: int) -> list:
        """Координаты (x, y) пикселей вдоль дуги (без повторов)."""
        result = []
        last_x, last_y = None, None
        arc_length = abs(end_angle - start_angle) * math.pi * radius / 180
        num_points = max(int(arc_length * 2), 10)
        for i in range(num_points + 1):
            angle = math.radians(start_angle + (end_angle - start_angle) * i / num_points)
            px = int(cx + radius * math.cos(angle))
            py = int(cy - radius * math.sin(angle))
            if 0 <= px < img_width and 0 <= py < img_height and (px, py) != (last_x, last_y):
                result.append((px, py))
                last_x, last_y = px, py
        return result

    def _draw_loupe_geometry(
        self,
        draw: ImageDraw.ImageDraw,
        image: Image.Image,
        x_origin: int,
        y_origin: int,
        w: int,
        h: int,
        config: LoupeConfig,
        peaks_invert: bool,
        geometry_scale: float = 1.0,
    ) -> None:
        """
        Отрисовка геометрии лупы (рамка, перекрестие, сегменты красный/синий) на заданной области.
        x_origin, y_origin — левый верхний угол области отрисовки (для кадра лупы передать 0, 0).
        geometry_scale: масштаб геометрии (большой круг описывает объект при наведении).
        """
        s = geometry_scale
        r6 = 6 * s
        r12 = 12 * s
        r_small_int = int(6 * math.sqrt(2) * s)
        r_large_int = int(12 * math.sqrt(2) * s)

        cx_canvas = x_origin + w // 2
        cy_canvas = y_origin + h // 2
        cx_local = w // 2
        cy_local = h // 2
        threshold = config.peak_sequence_threshold
        threshold_arc = config.peak_sequence_threshold_arc
        default_color = config.crosshair_color
        highlight_color = config.crosshair_highlight_color
        pixels = image.load()
        img_w, img_h = image.size

        draw.rectangle(
            [x_origin, y_origin, x_origin + w, y_origin + h],
            outline=config.border_color,
            width=config.border_width,
        )

        seg_idx = [0]
        is_peak_pixel = (lambda p: p >= 128) if peaks_invert else (lambda p: p < 128)

        def draw_line(x1_local, y1_local, x2_local, y2_local, x1_canvas, y1_canvas, x2_canvas, y2_canvas):
            eff_threshold = 1 if seg_idx[0] in DISPLAY_ONLY_SEGMENT_IDS else threshold
            line_pixels = self._get_line_pixels(x1_local, y1_local, x2_local, y2_local, pixels, img_w, img_h)
            color = highlight_color if self._has_peak_sequence(line_pixels, eff_threshold, peaks_invert) else default_color
            draw.line([(x1_canvas, y1_canvas), (x2_canvas, y2_canvas)], fill=color, width=config.crosshair_width)
            seg_idx[0] += 1

        def draw_line_per_pixel(x1_local, y1_local, x2_local, y2_local):
            """Отрисовка луча по 1 пикселю (сегменты 4, 9, 14, 19)."""
            if y1_local == y2_local:
                x_start, x_end = min(x1_local, x2_local), max(x1_local, x2_local)
                for px in range(x_start, x_end + 1):
                    if 0 <= px < img_w and 0 <= y1_local < img_h:
                        val = pixels[px, y1_local]
                        color = highlight_color if is_peak_pixel(val) else default_color
                        draw.line(
                            [(x_origin + px, y_origin + y1_local), (x_origin + px + 1, y_origin + y1_local)],
                            fill=color, width=config.crosshair_width
                        )
            else:
                y_start, y_end = min(y1_local, y2_local), max(y1_local, y2_local)
                for py in range(y_start, y_end + 1):
                    if 0 <= x1_local < img_w and 0 <= py < img_h:
                        val = pixels[x1_local, py]
                        color = highlight_color if is_peak_pixel(val) else default_color
                        draw.line(
                            [(x_origin + x1_local, y_origin + py), (x_origin + x1_local, y_origin + py + 1)],
                            fill=color, width=config.crosshair_width
                        )
            seg_idx[0] += 1

        # Перекрестие (20 сегментов)
        draw_line(cx_local, cy_local, cx_local - r6, cy_local, cx_canvas, cy_canvas, cx_canvas - r6, cy_canvas)
        draw_line(cx_local - r6, cy_local, cx_local - r_small_int, cy_local, cx_canvas - r6, cy_canvas, cx_canvas - r_small_int, cy_canvas)
        draw_line(cx_local - r_small_int, cy_local, cx_local - r12, cy_local, cx_canvas - r_small_int, cy_canvas, cx_canvas - r12, cy_canvas)
        draw_line(cx_local - r12, cy_local, cx_local - r_large_int, cy_local, cx_canvas - r12, cy_canvas, cx_canvas - r_large_int, cy_canvas)
        draw_line_per_pixel(cx_local - r_large_int, cy_local, 0, cy_local)
        draw_line(cx_local, cy_local, cx_local + r6, cy_local, cx_canvas, cy_canvas, cx_canvas + r6, cy_canvas)
        draw_line(cx_local + r6, cy_local, cx_local + r_small_int, cy_local, cx_canvas + r6, cy_canvas, cx_canvas + r_small_int, cy_canvas)
        draw_line(cx_local + r_small_int, cy_local, cx_local + r12, cy_local, cx_canvas + r_small_int, cy_canvas, cx_canvas + r12, cy_canvas)
        draw_line(cx_local + r12, cy_local, cx_local + r_large_int, cy_local, cx_canvas + r12, cy_canvas, cx_canvas + r_large_int, cy_canvas)
        draw_line_per_pixel(cx_local + r_large_int, cy_local, w - 1, cy_local)
        draw_line(cx_local, cy_local, cx_local, cy_local - r6, cx_canvas, cy_canvas, cx_canvas, cy_canvas - r6)
        draw_line(cx_local, cy_local - r6, cx_local, cy_local - r_small_int, cx_canvas, cy_canvas - r6, cx_canvas, cy_canvas - r_small_int)
        draw_line(cx_local, cy_local - r_small_int, cx_local, cy_local - r12, cx_canvas, cy_canvas - r_small_int, cx_canvas, cy_canvas - r12)
        draw_line(cx_local, cy_local - r12, cx_local, cy_local - r_large_int, cx_canvas, cy_canvas - r12, cx_canvas, cy_canvas - r_large_int)
        draw_line_per_pixel(cx_local, cy_local - r_large_int, cx_local, 0)
        draw_line(cx_local, cy_local, cx_local, cy_local + r6, cx_canvas, cy_canvas, cx_canvas, cy_canvas + r6)
        draw_line(cx_local, cy_local + r6, cx_local, cy_local + r_small_int, cx_canvas, cy_canvas + r6, cx_canvas, cy_canvas + r_small_int)
        draw_line(cx_local, cy_local + r_small_int, cx_local, cy_local + r12, cx_canvas, cy_canvas + r_small_int, cx_canvas, cy_canvas + r12)
        draw_line(cx_local, cy_local + r12, cx_local, cy_local + r_large_int, cx_canvas, cy_canvas + r12, cx_canvas, cy_canvas + r_large_int)
        draw_line_per_pixel(cx_local, cy_local + r_large_int, cx_local, h - 1)
        # Квадрат 12x12
        draw_line(cx_local - r6, cy_local - r6, cx_local, cy_local - r6, cx_canvas - r6, cy_canvas - r6, cx_canvas, cy_canvas - r6)
        draw_line(cx_local, cy_local - r6, cx_local + r6, cy_local - r6, cx_canvas, cy_canvas - r6, cx_canvas + r6, cy_canvas - r6)
        draw_line(cx_local + r6, cy_local - r6, cx_local + r6, cy_local, cx_canvas + r6, cy_canvas - r6, cx_canvas + r6, cy_canvas)
        draw_line(cx_local + r6, cy_local, cx_local + r6, cy_local + r6, cx_canvas + r6, cy_canvas, cx_canvas + r6, cy_canvas + r6)
        draw_line(cx_local + r6, cy_local + r6, cx_local, cy_local + r6, cx_canvas + r6, cy_canvas + r6, cx_canvas, cy_canvas + r6)
        draw_line(cx_local, cy_local + r6, cx_local - r6, cy_local + r6, cx_canvas, cy_canvas + r6, cx_canvas - r6, cy_canvas + r6)
        draw_line(cx_local - r6, cy_local + r6, cx_local - r6, cy_local, cx_canvas - r6, cy_canvas + r6, cx_canvas - r6, cy_canvas)
        draw_line(cx_local - r6, cy_local, cx_local - r6, cy_local - r6, cx_canvas - r6, cy_canvas, cx_canvas - r6, cy_canvas - r6)
        # Квадрат 24x24
        draw_line(cx_local - r12, cy_local - r12, cx_local, cy_local - r12, cx_canvas - r12, cy_canvas - r12, cx_canvas, cy_canvas - r12)
        draw_line(cx_local, cy_local - r12, cx_local + r12, cy_local - r12, cx_canvas, cy_canvas - r12, cx_canvas + r12, cy_canvas - r12)
        draw_line(cx_local + r12, cy_local - r12, cx_local + r12, cy_local, cx_canvas + r12, cy_canvas - r12, cx_canvas + r12, cy_canvas)
        draw_line(cx_local + r12, cy_local, cx_local + r12, cy_local + r12, cx_canvas + r12, cy_canvas, cx_canvas + r12, cy_canvas + r12)
        draw_line(cx_local + r12, cy_local + r12, cx_local, cy_local + r12, cx_canvas + r12, cy_canvas + r12, cx_canvas, cy_canvas + r12)
        draw_line(cx_local, cy_local + r12, cx_local - r12, cy_local + r12, cx_canvas, cy_canvas + r12, cx_canvas - r12, cy_canvas + r12)
        draw_line(cx_local - r12, cy_local + r12, cx_local - r12, cy_local, cx_canvas - r12, cy_canvas + r12, cx_canvas - r12, cy_canvas)
        draw_line(cx_local - r12, cy_local, cx_local - r12, cy_local - r12, cx_canvas - r12, cy_canvas, cx_canvas - r12, cy_canvas - r12)
        # Ромб
        draw_line(cx_local, cy_local - r12, cx_local + r12, cy_local, cx_canvas, cy_canvas - r12, cx_canvas + r12, cy_canvas)
        draw_line(cx_local + r12, cy_local, cx_local, cy_local + r12, cx_canvas + r12, cy_canvas, cx_canvas, cy_canvas + r12)
        draw_line(cx_local, cy_local + r12, cx_local - r12, cy_local, cx_canvas, cy_canvas + r12, cx_canvas - r12, cy_canvas)
        draw_line(cx_local - r12, cy_local, cx_local, cy_local - r12, cx_canvas - r12, cy_canvas, cx_canvas, cy_canvas - r12)
        # Круги
        r_small = 6 * math.sqrt(2) * s
        r_large = 12 * math.sqrt(2) * s

        def draw_arc(radius: float, start_angle: float, end_angle: float):
            eff_threshold_arc = 1 if seg_idx[0] in DISPLAY_ONLY_SEGMENT_IDS else threshold_arc
            arc_pixels = self._get_arc_pixels(cx_local, cy_local, radius, start_angle, end_angle, pixels, img_w, img_h)
            color = highlight_color if self._has_peak_sequence(arc_pixels, eff_threshold_arc, peaks_invert) else default_color
            bbox = [cx_canvas - radius, cy_canvas - radius, cx_canvas + radius, cy_canvas + radius]
            draw.arc(bbox, start=start_angle, end=end_angle, fill=color, width=config.crosshair_width)
            seg_idx[0] += 1

        def draw_arc_per_pixel(radius: float, start_angle: float, end_angle: float):
            """Отрисовка дуги по 1 пикселю (сегменты 48-55)."""
            coords = self._get_arc_pixel_coords(cx_local, cy_local, radius, start_angle, end_angle, img_w, img_h)
            for px, py in coords:
                val = pixels[px, py]
                color = highlight_color if is_peak_pixel(val) else default_color
                draw.line(
                    [(x_origin + px, y_origin + py), (x_origin + px + 1, y_origin + py)],
                    fill=color, width=config.crosshair_width
                )
            seg_idx[0] += 1

        for start, end in [(0, 45), (45, 90), (90, 135), (135, 180), (180, 225), (225, 270), (270, 315), (315, 360)]:
            draw_arc(r_small, start, end)
        for start, end in [(0, 45), (45, 90), (90, 135), (135, 180), (180, 225), (225, 270), (270, 315), (315, 360)]:
            draw_arc_per_pixel(r_large, start, end)

    def render_loupe_tile_with_geometry(self, use_saved: bool = False) -> Optional[Image.Image]:
        """
        Рендер кадра лупы с геометрией и сегментами (красный/синий) на момент вызова.
        
        Args:
            use_saved: Если True, использует _last_peaks_image вместо текущей лупы
        
        Returns:
            PIL Image размером с лупу или None, если лупа не видна.
        """
        if use_saved and self._last_peaks_image is not None:
            # Используем сохранённое изображение пиков
            result = self._last_peaks_image.convert("RGB").copy()
            draw = ImageDraw.Draw(result)
            w, h = self.loupe_size, self.loupe_size
            self._draw_loupe_geometry(
                draw, self._last_peaks_image, 0, 0, w, h,
                self.peaks_loupe.config, self._peaks_loupe_data.peaks_invert,
                self._peaks_loupe_data.geometry_scale,
            )
            return result
        
        # Стандартный рендеринг текущей лупы
        loupe_data = self._peaks_loupe_data
        if not loupe_data.is_visible or loupe_data.image is None:
            return None
        result = loupe_data.image.convert("RGB").copy()
        draw = ImageDraw.Draw(result)
        w, h = loupe_data.width, loupe_data.height
        self._draw_loupe_geometry(
            draw, loupe_data.image, 0, 0, w, h,
            self.peaks_loupe.config, loupe_data.peaks_invert,
            loupe_data.geometry_scale,
        )
        return result

    def compose_peaks_with_loupe(self, peaks_image: Image.Image) -> Image.Image:
        """
        Создание композитного изображения пиков с лупой.
        """
        result = peaks_image.convert("RGB")
        loupe_data = self._peaks_loupe_data
        if not loupe_data.is_visible or loupe_data.image is None:
            return result
        loupe_rgb = loupe_data.image.convert("RGB")
        result.paste(loupe_rgb, (loupe_data.x, loupe_data.y))
        draw = ImageDraw.Draw(result)
        x, y = loupe_data.x, loupe_data.y
        w, h = loupe_data.width, loupe_data.height
        self._draw_loupe_geometry(
            draw, loupe_data.image, x, y, w, h,
            self.peaks_loupe.config, loupe_data.peaks_invert,
            loupe_data.geometry_scale,
        )
        return result
