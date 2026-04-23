"""Uniform preview scaling for global peaks/object detection (full-res is source of truth)."""

from __future__ import annotations

import os
from typing import Optional

_DEFAULT_GLOBAL_PEAKS_SCALE = 0.5
_ENV_KEYS = (
    "KOLOS_GLOBAL_PEAKS_SCALE",
    "GLAZ_GLOBAL_PEAKS_SCALE",
)


def _parse_positive_float(value: str) -> Optional[float]:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        s = float(raw)
    except ValueError:
        return None
    if s <= 0.0 or s > 1.0:
        return None
    return s


def read_global_peaks_scale_from_env(
    env: dict[str, str] | None = None,
) -> float:
    """
    Read preview scale (0 < s <= 1) from environment.

    First non-empty valid variable wins, in order:
    KOLOS_GLOBAL_PEAKS_SCALE, GLAZ_GLOBAL_PEAKS_SCALE.
    If none set/valid — default 0.5.
    """
    env = os.environ if env is None else env
    for key in _ENV_KEYS:
        s = _parse_positive_float(env.get(key, ""))
        if s is not None:
            return float(s)
    return _DEFAULT_GLOBAL_PEAKS_SCALE


def uniform_preview_size(
    full_width: int, full_height: int, scale: float
) -> tuple[int, int, float]:
    """
    Compute preview (w, h) and actual uniform scale s applied.

    Rounded sizes can make sx != sy; we apply one scale s = min(sx, sy) to keep uniformity.
    """
    fw = max(1, int(full_width))
    fh = max(1, int(full_height))
    s = float(scale)
    if s >= 0.999:
        return fw, fh, 1.0
    w = max(1, int(round(fw * s)))
    h = max(1, int(round(fh * s)))
    sx = w / float(fw)
    sy = h / float(fh)
    s_eff = min(sx, sy)
    w2 = max(1, int(round(fw * s_eff)))
    h2 = max(1, int(round(fh * s_eff)))
    return w2, h2, s_eff
