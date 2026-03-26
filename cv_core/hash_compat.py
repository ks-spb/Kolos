"""Compatibility hash helpers for old Kolos API."""

from __future__ import annotations

import hashlib
from typing import Iterable


def object_hash_for_bbox_signature(bbox: tuple[int, int, int, int], signature: Iterable[int]) -> str:
    """Build stable object id compatible with old hash API."""
    left, top, right, bottom = bbox
    payload = f"{left}:{top}:{right}:{bottom}|{','.join(map(str, sorted(signature)))}"
    return hashlib.blake2b(payload.encode("utf-8"), digest_size=8).hexdigest()


def screen_hash_for_frame(size: tuple[int, int], object_hashes: Iterable[str]) -> str:
    """Build stable screen id from frame size and objects."""
    width, height = size
    payload = f"{width}x{height}|{','.join(sorted(object_hashes))}"
    return hashlib.blake2b(payload.encode("utf-8"), digest_size=8).hexdigest()

