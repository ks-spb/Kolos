"""Detection service using Glaz image processor."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from PIL import Image

from Glaz.image_processor import DetectedObject, ImageProcessor, LineBasedDetector

from .global_peaks_scale import read_global_peaks_scale_from_env, uniform_preview_size
from .hash_compat import object_hash_for_bbox_signature
from .peaks_coordinate_map import (
    ltrb_preview_to_full,
    point_preview_to_full,
    scale_min_line_length_for_preview,
    scale_threshold_for_preview,
)


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
        self._global_peaks_scale = float(read_global_peaks_scale_from_env())

    def process(
        self,
        frame: Image.Image,
        threshold: int,
        invert: bool,
        min_line_length: int,
    ) -> tuple[Image.Image, list[DetectedRecord]]:
        """Run peaks + object detection and convert to compat records."""
        fw, fh = map(int, frame.size)
        pw, ph, s_eff = uniform_preview_size(fw, fh, self._global_peaks_scale)
        if s_eff >= 0.999 or (pw, ph) == (fw, fh):
            peaks = ImageProcessor.detect_color_peaks(frame, threshold, invert)
            objects = self._detector.detect(
                peaks,
                black_threshold=128,
                min_line_length=min_line_length,
            )
            return peaks, self._map_objects(objects)

        inv = 1.0 / s_eff
        preview = frame.resize((pw, ph), resample=Image.Resampling.BILINEAR)
        thr_p = scale_threshold_for_preview(threshold, s_eff)
        mll_p = scale_min_line_length_for_preview(min_line_length, s_eff)
        peaks = ImageProcessor.detect_color_peaks(preview, thr_p, invert)
        objects = self._detector.detect(
            peaks,
            black_threshold=128,
            min_line_length=mll_p,
        )
        return peaks, self._map_objects(self._to_full_res_objects(objects, inv))

    @staticmethod
    def _to_full_res_objects(
        objects: Iterable[DetectedObject], inv_scale: float
    ) -> list[DetectedObject]:
        out: list[DetectedObject] = []
        for obj in objects:
            l, t, r, b = ltrb_preview_to_full(
                *obj.bbox, inv_scale=float(inv_scale)
            )
            cxf, cyf = point_preview_to_full(
                float(obj.center_peaks[0]), float(obj.center_peaks[1]), inv_scale=float(inv_scale)
            )
            out.append(
                replace(
                    obj,
                    bbox=(l, t, r, b),
                    center_peaks=(cxf, cyf),
                )
            )
        return out

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

