"""Detection service using Glaz image processor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from PIL import Image

from Glaz.image_processor import DetectedObject, ImageProcessor, LineBasedDetector

from .hash_compat import object_hash_for_bbox_signature


@dataclass(frozen=True)
class DetectedRecord:
    """Detected object mapped to old Kolos shape."""

    hash_id: str
    bbox_xywh: tuple[int, int, int, int]
    bbox_ltrb: tuple[int, int, int, int]
    center: tuple[int, int]
    signature: tuple[int, ...]
    object_id: int


class DetectionService:
    """Facade over Glaz processor and detector strategy."""

    def __init__(self) -> None:
        self._detector = LineBasedDetector()

    def process(
        self,
        frame: Image.Image,
        threshold: int,
        invert: bool,
        min_line_length: int,
    ) -> tuple[Image.Image, list[DetectedRecord]]:
        """Run peaks + object detection and convert to compat records."""
        peaks = ImageProcessor.detect_color_peaks(frame, threshold, invert)
        objects = self._detector.detect(
            peaks,
            black_threshold=128,
            min_line_length=min_line_length,
        )
        records = self._map_objects(objects)
        return peaks, records

    @staticmethod
    def _signature_from_bbox(obj: DetectedObject) -> tuple[int, ...]:
        """Compact signature from bbox and rounded center."""
        left, top, right, bottom = obj.bbox
        cx, cy = obj.center_peaks
        return (
            left,
            top,
            right,
            bottom,
            int(round(cx)),
            int(round(cy)),
        )

    def _map_objects(self, objects: Iterable[DetectedObject]) -> list[DetectedRecord]:
        records: list[DetectedRecord] = []
        for obj in objects:
            left, top, right, bottom = obj.bbox
            w = max(0, right - left)
            h = max(0, bottom - top)
            signature = self._signature_from_bbox(obj)
            hash_id = object_hash_for_bbox_signature(obj.bbox, signature)
            records.append(
                DetectedRecord(
                    hash_id=hash_id,
                    bbox_xywh=(left, top, w, h),
                    bbox_ltrb=obj.bbox,
                    center=(int(round(obj.center_peaks[0])), int(round(obj.center_peaks[1]))),
                    signature=signature,
                    object_id=obj.id,
                )
            )
        return records

