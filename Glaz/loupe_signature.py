"""
Чистое (без Tk/Canvas) вычисление "грубой подписи" по геометрии лупы.

Задача модуля: по изображению пиков (PIL 'L') определить, какие сегменты геометрии
должны считаться "подсвеченными", используя ту же логику, что и визуальная лупа.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from PIL import Image

from loupe import DISPLAY_ONLY_SEGMENT_IDS, LoupeConfig


@dataclass(frozen=True)
class LoupeSignature:
    """Результат вычисления подписи."""

    highlighted_segment_ids: tuple[int, ...]


class LoupeSignatureAnalyzer:
    """
    Вычисляет сегменты, которые "горят" на изображении пиков.

    Важно:
    - DISPLAY_ONLY сегменты (например 4, 9, 14, 19, 48-55) НЕ входят в подпись.
    - Порог для DISPLAY_ONLY принудительно 1 (как в UI), но он используется только
      для "визуального" понимания; в подпись они не попадают.
    """

    def __init__(self, config: LoupeConfig | None = None) -> None:
        self._config = config or LoupeConfig()

    def compute(
        self,
        peaks_image: Image.Image,
        *,
        peaks_invert: bool,
        geometry_scale: float = 1.0,
    ) -> LoupeSignature:
        """
        Вычислить подсвеченные сегменты геометрии.

        Args:
            peaks_image: PIL Image (mode 'L') с пиками
            peaks_invert: True если пик = белый (>=128), иначе пик = чёрный (<128)
            geometry_scale: масштаб геометрии (как в UI)
        """
        if peaks_image.mode != "L":
            peaks_image = peaks_image.convert("L")
        w, h = peaks_image.size
        if w <= 0 or h <= 0:
            return LoupeSignature(())
        pixels = peaks_image.load()

        cx = w // 2
        cy = h // 2

        is_peak = (lambda p: p >= 128) if peaks_invert else (lambda p: p < 128)

        highlighted: list[int] = []
        seg_idx = 0

        def mark_if(segment_pixels: Iterable[int], *, is_arc: bool) -> None:
            nonlocal seg_idx
            threshold = (
                int(self._config.peak_sequence_threshold_arc)
                if is_arc
                else int(self._config.peak_sequence_threshold)
            )
            eff_threshold = 1 if seg_idx in DISPLAY_ONLY_SEGMENT_IDS else threshold
            if self._has_peak_sequence(segment_pixels, eff_threshold, is_peak):
                if seg_idx not in DISPLAY_ONLY_SEGMENT_IDS:
                    highlighted.append(seg_idx)
            seg_idx += 1

        s = float(geometry_scale) if geometry_scale else 1.0
        r6 = 6 * s
        r12 = 12 * s
        r_small = int(6 * math.sqrt(2) * s)
        r_large = int(12 * math.sqrt(2) * s)

        # 20 сегментов перекрестия (в той же последовательности, что в UI)
        # Влево
        mark_if(self._line_pixels(pixels, w, h, cx, cy, int(cx - r6), cy), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx - r6), cy, int(cx - r_small), cy), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx - r_small), cy, int(cx - r12), cy), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx - r12), cy, int(cx - r_large), cy), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx - r_large), cy, 0, cy), is_arc=False)  # per-pixel in UI
        # Вправо
        mark_if(self._line_pixels(pixels, w, h, cx, cy, int(cx + r6), cy), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx + r6), cy, int(cx + r_small), cy), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx + r_small), cy, int(cx + r12), cy), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx + r12), cy, int(cx + r_large), cy), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx + r_large), cy, w - 1, cy), is_arc=False)  # per-pixel in UI
        # Вверх
        mark_if(self._line_pixels(pixels, w, h, cx, cy, cx, int(cy - r6)), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, cx, int(cy - r6), cx, int(cy - r_small)), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, cx, int(cy - r_small), cx, int(cy - r12)), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, cx, int(cy - r12), cx, int(cy - r_large)), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, cx, int(cy - r_large), cx, 0), is_arc=False)  # per-pixel in UI
        # Вниз
        mark_if(self._line_pixels(pixels, w, h, cx, cy, cx, int(cy + r6)), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, cx, int(cy + r6), cx, int(cy + r_small)), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, cx, int(cy + r_small), cx, int(cy + r12)), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, cx, int(cy + r12), cx, int(cy + r_large)), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, cx, int(cy + r_large), cx, h - 1), is_arc=False)  # per-pixel in UI

        # Квадрат 12x12 (8)
        mark_if(self._line_pixels(pixels, w, h, int(cx - r6), int(cy - r6), cx, int(cy - r6)), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, cx, int(cy - r6), int(cx + r6), int(cy - r6)), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx + r6), int(cy - r6), int(cx + r6), cy), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx + r6), cy, int(cx + r6), int(cy + r6)), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx + r6), int(cy + r6), cx, int(cy + r6)), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, cx, int(cy + r6), int(cx - r6), int(cy + r6)), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx - r6), int(cy + r6), int(cx - r6), cy), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx - r6), cy, int(cx - r6), int(cy - r6)), is_arc=False)

        # Квадрат 24x24 (8)
        mark_if(self._line_pixels(pixels, w, h, int(cx - r12), int(cy - r12), cx, int(cy - r12)), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, cx, int(cy - r12), int(cx + r12), int(cy - r12)), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx + r12), int(cy - r12), int(cx + r12), cy), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx + r12), cy, int(cx + r12), int(cy + r12)), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx + r12), int(cy + r12), cx, int(cy + r12)), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, cx, int(cy + r12), int(cx - r12), int(cy + r12)), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx - r12), int(cy + r12), int(cx - r12), cy), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx - r12), cy, int(cx - r12), int(cy - r12)), is_arc=False)

        # Ромб (4)
        mark_if(self._line_pixels(pixels, w, h, cx, int(cy - r12), int(cx + r12), cy), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx + r12), cy, cx, int(cy + r12)), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, cx, int(cy + r12), int(cx - r12), cy), is_arc=False)
        mark_if(self._line_pixels(pixels, w, h, int(cx - r12), cy, cx, int(cy - r12)), is_arc=False)

        # Круг для квадрата 12x12 (8 дуг)
        r_small_f = 6 * math.sqrt(2) * s
        for start, end in (
            (0, 45),
            (45, 90),
            (90, 135),
            (135, 180),
            (180, 225),
            (225, 270),
            (270, 315),
            (315, 360),
        ):
            mark_if(self._arc_pixels(pixels, w, h, cx, cy, r_small_f, start, end), is_arc=True)

        # Круг для квадрата 24x24 (8 дуг) — в UI рисуется per-pixel, но для подписи важен факт пиков на дуге
        r_large_f = 12 * math.sqrt(2) * s
        for start, end in (
            (0, 45),
            (45, 90),
            (90, 135),
            (135, 180),
            (180, 225),
            (225, 270),
            (270, 315),
            (315, 360),
        ):
            mark_if(self._arc_pixels(pixels, w, h, cx, cy, r_large_f, start, end), is_arc=True)

        return LoupeSignature(tuple(sorted(set(highlighted))))

    @staticmethod
    def _has_peak_sequence(values: Iterable[int], threshold: int, is_peak) -> bool:
        consecutive = 0
        for v in values:
            if is_peak(v):
                consecutive += 1
                if consecutive >= int(threshold):
                    return True
            else:
                consecutive = 0
        return False

    @staticmethod
    def _line_pixels(pixels, w: int, h: int, x1: int, y1: int, x2: int, y2: int) -> list[int]:
        """Пиксели вдоль линии (Брезенхем)."""
        x1 = int(round(x1))
        y1 = int(round(y1))
        x2 = int(round(x2))
        y2 = int(round(y2))
        result: list[int] = []
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        x, y = x1, y1
        while True:
            if 0 <= x < w and 0 <= y < h:
                result.append(int(pixels[x, y]))
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

    @staticmethod
    def _arc_pixels(
        pixels,
        w: int,
        h: int,
        cx: int,
        cy: int,
        radius: float,
        start_angle: float,
        end_angle: float,
    ) -> list[int]:
        """Пиксели вдоль дуги (без повторов)."""
        result: list[int] = []
        last = None
        arc_length = abs(end_angle - start_angle) * math.pi * float(radius) / 180.0
        num_points = max(int(arc_length * 2), 10)
        for i in range(num_points + 1):
            angle = math.radians(start_angle + (end_angle - start_angle) * i / num_points)
            x = int(cx + float(radius) * math.cos(angle))
            y = int(cy - float(radius) * math.sin(angle))
            if 0 <= x < w and 0 <= y < h and (x, y) != last:
                result.append(int(pixels[x, y]))
                last = (x, y)
        return result

