"""Compatibility hash helpers for old Kolos API."""

from __future__ import annotations

import hashlib
from typing import Iterable


def _quantize_int(value: int, step: int) -> int:
    """
    Quantize integer to a grid to reduce jitter sensitivity.

    Step must be positive.
    """
    s = int(step)
    if s <= 1:
        return int(value)
    # Round-to-nearest bucket with half-step bias.
    # With step=8, this makes +/-2 px jitter very likely to stay in the same bucket.
    v = int(value)
    half = s // 2
    return ((v + half) // s) * s


def _quantize_bbox_ltrb(
    bbox: tuple[int, int, int, int], *, step: int
) -> tuple[int, int, int, int]:
    l, t, r, b = bbox
    return (
        _quantize_int(l, step),
        _quantize_int(t, step),
        _quantize_int(r, step),
        _quantize_int(b, step),
    )


def object_hash_for_bbox_signature(bbox: tuple[int, int, int, int], signature: Iterable[int]) -> str:
    """Build stable object id compatible with old hash API."""
    # Critical: object hashes must be stable across minor bbox jitter (1-2 px),
    # otherwise the same UI screen will fragment into many "new" screens.
    q_step = 8
    left, top, right, bottom = _quantize_bbox_ltrb(bbox, step=q_step)
    sig_q = sorted(_quantize_int(int(x), q_step) for x in signature)
    payload = f"{left}:{top}:{right}:{bottom}|{','.join(map(str, sig_q))}"
    return hashlib.blake2b(payload.encode("utf-8"), digest_size=8).hexdigest()


def screen_hash_for_frame(size: tuple[int, int], object_hashes: Iterable[str]) -> str:
    """Build stable screen id from frame size and objects."""
    width, height = size
    payload = f"{width}x{height}|{','.join(sorted(object_hashes))}"
    return hashlib.blake2b(payload.encode("utf-8"), digest_size=8).hexdigest()

