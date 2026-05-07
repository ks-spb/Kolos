"""Helpers for stable Glaz object-geometry cache keys."""

from __future__ import annotations

import hashlib
from typing import Iterable

BBoxLTRB = tuple[int, int, int, int]


def quantize_value(value: int | float, *, step: int = 8) -> int:
    """Place a coordinate into a stable grid bucket."""
    if step <= 0:
        step = 1
    return int(float(value) // float(step)) * int(step)


def quantize_bbox_ltrb(bbox: Iterable[int | float], *, step: int = 8) -> BBoxLTRB | None:
    """Normalize a bbox to a quantized left/top/right/bottom tuple."""
    try:
        left, top, right, bottom = bbox
    except Exception:
        return None
    return (
        quantize_value(left, step=step),
        quantize_value(top, step=step),
        quantize_value(right, step=step),
        quantize_value(bottom, step=step),
    )


def geometry_hash_from_bboxes(bboxes: Iterable[Iterable[int | float]], *, step: int = 8) -> str:
    """Build an order-independent hash from quantized object bboxes."""
    normalized = []
    for bbox in bboxes:
        item = quantize_bbox_ltrb(bbox, step=step)
        if item is not None:
            normalized.append(item)
    normalized.sort()
    payload = repr(normalized).encode("utf-8")
    return hashlib.sha1(payload).hexdigest()
