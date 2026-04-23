"""Map detections on preview peaks image back to full-res coordinates."""

from __future__ import annotations

import math
from dataclasses import replace
from typing import TypeVar

T = TypeVar("T", int, float)


def scale_threshold_for_preview(threshold: int, effective_scale: float) -> int:
    """Map UI threshold to preview space: diffs scale ~ linearly with image scale."""
    s = float(effective_scale)
    if s >= 0.999:
        return int(threshold)
    t = int(round(int(threshold) * s))
    return max(1, min(255, t))


def scale_min_line_length_for_preview(min_line_length: int, effective_scale: float) -> int:
    s = float(effective_scale)
    if s >= 0.999:
        return int(min_line_length)
    return max(1, int(round(int(min_line_length) * s)))


def ltrb_preview_to_full(
    left: T,
    top: T,
    right: T,
    bottom: T,
    inv_scale: float,
) -> tuple[int, int, int, int]:
    """inv_scale = 1 / s_eff, where preview = full * s_eff (uniform)."""
    k = float(inv_scale)
    lf = float(left) * k
    tf = float(top) * k
    rf = float(right) * k
    bf = float(bottom) * k
    l_i = int(math.floor(lf))
    t_i = int(math.floor(tf))
    r_i = int(math.ceil(rf))
    b_i = int(math.ceil(bf))
    if r_i <= l_i:
        r_i = l_i + 1
    if b_i <= t_i:
        b_i = t_i + 1
    return l_i, t_i, r_i, b_i


def point_preview_to_full(x: float, y: float, inv_scale: float) -> tuple[float, float]:
    k = float(inv_scale)
    return float(x) * k, float(y) * k


def map_detected_object_ltrb(
    left: int,
    top: int,
    right: int,
    bottom: int,
    cx: float,
    cy: float,
    inv_scale: float,
) -> tuple[tuple[int, int, int, int], tuple[float, float]]:
    ltrb = ltrb_preview_to_full(left, top, right, bottom, inv_scale)
    cxf, cyf = point_preview_to_full(cx, cy, inv_scale)
    return ltrb, (cxf, cyf)
