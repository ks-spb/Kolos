"""
Модуль обработки изображений для приложения Glaz
"""

import numpy as np
from PIL import Image
from dataclasses import dataclass
from collections import deque
from typing import Protocol

try:
    import cv2
    _HAS_OPENCV = True
except Exception:
    _HAS_OPENCV = False


class ObjectDetector(Protocol):
    """Протокол детектора объектов на изображении пиков."""

    def detect(self, peaks_image: Image.Image, **kwargs) -> list["DetectedObject"]:
        """Вернуть список обнаруженных объектов."""
        ...


@dataclass
class DetectedObject:
    """Обнаруженный объект — связная область на изображении Пики (blob или по линиям)."""
    id: int  # Номер объекта 1..N
    bbox: tuple[int, int, int, int]  # (left, top, right, bottom) в координатах пиков
    center_peaks: tuple[float, float]  # (cx, cy) центр в координатах изображения пиков

    def contains_point(self, px: float, py: float) -> bool:
        """Проверка, попадает ли точка (в координатах пиков) внутрь bbox."""
        l, t, r, b = self.bbox
        return l <= px < r and t <= py < b


class ImageProcessor:
    """Класс для обработки изображений и детекции пиков."""

    @staticmethod
    def lines_detector_mode() -> str:
        """Текущий режим детекции линий: cv2 или bfs."""
        return "cv2" if _HAS_OPENCV else "bfs"
    
    @staticmethod
    def detect_color_peaks(image: Image.Image, threshold: int, invert: bool = False) -> Image.Image:
        """
        Обнаружение резких изменений цвета по осям X и Y.
        
        Args:
            image: Исходное PIL изображение
            threshold: Порог чувствительности (1-255)
            invert: Инвертировать цвета (белые пики на чёрном фоне)
            
        Returns:
            PIL Image: Изображение с отмеченными пиками (суммарно по градиентам X и Y)
        """
        img_array = np.array(image)
        height, width = img_array.shape[:2]
        
        # Создаём массив для результата
        if invert:
            # Инверсия: чёрный фон, белые пики
            peaks = np.zeros((height, width), dtype=np.uint8)
        else:
            # Обычный: белый фон, чёрные пики
            peaks = np.ones((height, width), dtype=np.uint8) * 255
        
        peak_value = 255 if invert else 0

        # Градиент по оси X: разница между соседними пикселями по горизонтали
        if len(img_array.shape) == 3:
            diff_x = np.abs(
                img_array[:, 1:, :].astype(np.int16) - 
                img_array[:, :-1, :].astype(np.int16)
            )
            total_diff_x = np.sum(diff_x, axis=2)
        else:
            diff_x = np.abs(
                img_array[:, 1:].astype(np.int16) - 
                img_array[:, :-1].astype(np.int16)
            )
            total_diff_x = diff_x
        peaks[:, 1:][total_diff_x > threshold] = peak_value

        # Градиент по оси Y: разница между соседними пикселями по вертикали
        if len(img_array.shape) == 3:
            diff_y = np.abs(
                img_array[1:, :, :].astype(np.int16) - 
                img_array[:-1, :, :].astype(np.int16)
            )
            total_diff_y = np.sum(diff_y, axis=2)
        else:
            diff_y = np.abs(
                img_array[1:, :].astype(np.int16) - 
                img_array[:-1, :].astype(np.int16)
            )
            total_diff_y = diff_y
        peaks[1:, :][total_diff_y > threshold] = peak_value

        return Image.fromarray(peaks, mode='L')

    @staticmethod
    def detect_objects(peaks_image: Image.Image, black_threshold: int = 128) -> list[DetectedObject]:
        """
        Поиск связных областей (blob) чёрных пикселей на изображении Пики.
        4-связность: только соседи по горизонтали и вертикали.

        Args:
            peaks_image: PIL Image в режиме 'L' (0 = чёрный, 255 = белый)
            black_threshold: Пиксель считается чёрным, если значение < black_threshold

        Returns:
            Список DetectedObject, отсортированный по id (порядок обхода).
        """
        arr = np.array(peaks_image)
        if arr.ndim > 2:
            arr = arr[:, :, 0]
        h, w = arr.shape
        is_black = (arr < black_threshold)
        visited = np.zeros((h, w), dtype=bool)
        objects: list[DetectedObject] = []
        obj_id = 0
        # 4 соседа: только по горизонтали и вертикали
        neighbors = ((-1, 0), (1, 0), (0, -1), (0, 1))

        for y in range(h):
            for x in range(w):
                if not is_black[y, x] or visited[y, x]:
                    continue
                obj_id += 1
                q = deque([(x, y)])
                visited[y, x] = True
                xs, ys = [x], [y]
                while q:
                    cx, cy = q.popleft()
                    for dx, dy in neighbors:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and is_black[ny, nx] and not visited[ny, nx]:
                            visited[ny, nx] = True
                            q.append((nx, ny))
                            xs.append(nx)
                            ys.append(ny)
                left, right = min(xs), max(xs) + 1
                top, bottom = min(ys), max(ys) + 1
                cx = sum(xs) / len(xs)
                cy = sum(ys) / len(ys)
                objects.append(DetectedObject(
                    id=obj_id,
                    bbox=(left, top, right, bottom),
                    center_peaks=(cx, cy),
                ))

        return objects

    @staticmethod
    def _detect_objects_by_lines_cv2(line_mask: np.ndarray) -> list[DetectedObject]:
        """Быстрая детекция объектов через OpenCV connectedComponents (8-связность)."""
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            line_mask, connectivity=8, ltype=cv2.CV_32S
        )
        objects: list[DetectedObject] = []
        obj_id = 0
        for label in range(1, num_labels):
            left = int(stats[label, cv2.CC_STAT_LEFT])
            top = int(stats[label, cv2.CC_STAT_TOP])
            width = int(stats[label, cv2.CC_STAT_WIDTH])
            height = int(stats[label, cv2.CC_STAT_HEIGHT])
            if width <= 0 or height <= 0:
                continue
            right = left + width
            bottom = top + height
            cx = float(centroids[label][0])
            cy = float(centroids[label][1])
            obj_id += 1
            objects.append(
                DetectedObject(
                    id=obj_id,
                    bbox=(left, top, right, bottom),
                    center_peaks=(cx, cy),
                )
            )
        return objects

    @staticmethod
    def _detect_objects_by_lines_bfs(line_mask: np.ndarray) -> list[DetectedObject]:
        """Fallback-детекция объектов через BFS (8-связность)."""
        h, w = line_mask.shape
        visited = np.zeros((h, w), dtype=bool)
        objects: list[DetectedObject] = []
        obj_id = 0
        neighbors = (
            (-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (-1, 1), (1, -1), (1, 1),
        )
        for y in range(h):
            for x in range(w):
                if not line_mask[y, x] or visited[y, x]:
                    continue
                obj_id += 1
                q = deque([(x, y)])
                visited[y, x] = True
                xs, ys = [x], [y]
                while q:
                    cx, cy = q.popleft()
                    for dx, dy in neighbors:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and line_mask[ny, nx] and not visited[ny, nx]:
                            visited[ny, nx] = True
                            q.append((nx, ny))
                            xs.append(nx)
                            ys.append(ny)
                left, right = min(xs), max(xs) + 1
                top, bottom = min(ys), max(ys) + 1
                cx = sum(xs) / len(xs)
                cy = sum(ys) / len(ys)
                objects.append(
                    DetectedObject(
                        id=obj_id,
                        bbox=(left, top, right, bottom),
                        center_peaks=(cx, cy),
                    )
                )
        return objects

    @staticmethod
    def _mask_solid_lines(
        arr: np.ndarray,
        black_threshold: int,
        min_line_length: int,
    ) -> np.ndarray:
        """
        Маска пикселей, лежащих на сплошных линиях (горизонталь, вертикаль, диагонали).
        Пиксель в маске, если он входит в серию из >= min_line_length чёрных подряд по одному из направлений.
        """
        h, w = arr.shape
        is_black = (arr < black_threshold).astype(np.uint8)
        out = np.zeros((h, w), dtype=np.uint8)

        # Горизонталь: по строкам
        for y in range(h):
            run = 0
            for x in range(w):
                if is_black[y, x]:
                    run += 1
                else:
                    if run >= min_line_length:
                        out[y, x - run : x] = 1
                    run = 0
            if run >= min_line_length:
                out[y, w - run : w] = 1

        # Вертикаль: по столбцам
        for x in range(w):
            run = 0
            for y in range(h):
                if is_black[y, x]:
                    run += 1
                else:
                    if run >= min_line_length:
                        out[y - run : y, x] = 1
                    run = 0
            if run >= min_line_length:
                out[h - run : h, x] = 1

        # Диагональ \ (x+k, y+k)
        for start in range(-h + 1, w):
            run = 0
            pts = []
            for k in range(max(0, -start), min(h, w - start)):
                y, x = k, start + k
                if 0 <= y < h and 0 <= x < w:
                    if is_black[y, x]:
                        run += 1
                        pts.append((y, x))
                    else:
                        if run >= min_line_length:
                            for py, px in pts:
                                out[py, px] = 1
                        run = 0
                        pts = []
            if run >= min_line_length:
                for py, px in pts:
                    out[py, px] = 1

        # Диагональ / (x+k, y-k)
        for start in range(0, w + h - 1):
            run = 0
            pts = []
            for k in range(max(0, start - w + 1), min(h, start + 1)):
                y = k
                x = start - k
                if 0 <= y < h and 0 <= x < w:
                    if is_black[y, x]:
                        run += 1
                        pts.append((y, x))
                    else:
                        if run >= min_line_length:
                            for py, px in pts:
                                out[py, px] = 1
                        run = 0
                        pts = []
            if run >= min_line_length:
                for py, px in pts:
                    out[py, px] = 1

        return out

    @staticmethod
    def get_4connected_bbox_at_point(
        peaks_image: Image.Image,
        px: float,
        py: float,
        black_threshold: int = 128,
        min_line_length: int = 3,
        limit_bbox: tuple[int, int, int, int] | None = None,
    ) -> tuple[int, int, int, int] | None:
        """
        Bbox 4-связной компоненты (по линиям), содержащей точку (px, py).
        Если задан limit_bbox (left, top, right, bottom), заливка только внутри него —
        тогда при курсоре на иконке берётся только иконка, без подписи.
        """
        arr = np.array(peaks_image)
        if arr.ndim > 2:
            arr = arr[:, :, 0]
        h, w = arr.shape
        line_mask = ImageProcessor._mask_solid_lines(arr, black_threshold, min_line_length)
        x0, y0 = int(round(px)), int(round(py))
        if x0 < 0 or x0 >= w or y0 < 0 or y0 >= h:
            return None
        if limit_bbox is not None:
            llim, tlim, rlim, blim = limit_bbox
            if x0 < llim or x0 >= rlim or y0 < tlim or y0 >= blim:
                return None
        if not line_mask[y0, x0]:
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    nx, ny = x0 + dx, y0 + dy
                    if 0 <= nx < w and 0 <= ny < h and line_mask[ny, nx]:
                        if limit_bbox is not None and (nx < llim or nx >= rlim or ny < tlim or ny >= blim):
                            continue
                        x0, y0 = nx, ny
                        break
                else:
                    continue
                break
            else:
                return None
        neighbors_4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
        visited = np.zeros((h, w), dtype=bool)
        q = deque([(x0, y0)])
        visited[y0, x0] = True
        xs, ys = [x0], [y0]
        while q:
            cx, cy = q.popleft()
            for dx, dy in neighbors_4:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < w and 0 <= ny < h and line_mask[ny, nx] and not visited[ny, nx]:
                    if limit_bbox is not None and (nx < llim or nx >= rlim or ny < tlim or ny >= blim):
                        continue
                    visited[ny, nx] = True
                    q.append((nx, ny))
                    xs.append(nx)
                    ys.append(ny)
        if not xs:
            return None
        left = min(xs)
        right = max(xs) + 1
        top = min(ys)
        bottom = max(ys) + 1
        return (left, top, right, bottom)

    @staticmethod
    def detect_objects_by_lines(
        peaks_image: Image.Image,
        black_threshold: int = 128,
        min_line_length: int = 3,
    ) -> list[DetectedObject]:
        """
        Поиск объектов по сплошным линиям (вертикаль, горизонталь, диагонали).
        Объект — связная компонента пикселей, лежащих на таких линиях (8-связность).

        Args:
            peaks_image: PIL Image в режиме 'L' (0 = чёрный, 255 = белый)
            black_threshold: Пиксель считается чёрным, если значение < black_threshold
            min_line_length: Минимальная длина линии в пикселях

        Returns:
            Список DetectedObject с полями id, bbox, center_peaks.
        """
        arr = np.array(peaks_image)
        if arr.ndim > 2:
            arr = arr[:, :, 0]
        line_mask = ImageProcessor._mask_solid_lines(arr, black_threshold, min_line_length)
        if _HAS_OPENCV:
            return ImageProcessor._detect_objects_by_lines_cv2(line_mask)
        return ImageProcessor._detect_objects_by_lines_bfs(line_mask)


class LineBasedDetector:
    """Детектор объектов по сплошным линиям (стратегия по умолчанию)."""

    def detect(
        self,
        peaks_image: Image.Image,
        black_threshold: int = 128,
        min_line_length: int = 3,
        **kwargs,
    ) -> list[DetectedObject]:
        return ImageProcessor.detect_objects_by_lines(
            peaks_image, black_threshold, min_line_length
        )
