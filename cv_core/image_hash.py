"""Perceptual image hashing helpers for stable screen anchoring.

We use dHash (difference hash) to build a compact representation of a screen.
It is robust to small UI jitter and tolerant to minor noise, especially when
combined with masking (taskbar region, cursor neighborhood).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from PIL import Image, ImageDraw


@dataclass(frozen=True)
class ImageAnchorConfig:
    """Configuration for image anchor hashing."""

    taskbar_exclude_ratio: float = 0.05
    cursor_mask_size_px: int = 120  # 0 disables cursor masking
    dhash_width: int = 8
    dhash_height: int = 8


def _clamp_int(v: int, lo: int, hi: int) -> int:
    return max(int(lo), min(int(hi), int(v)))


def _apply_taskbar_crop(img: Image.Image, *, exclude_ratio: float) -> Image.Image:
    w, h = img.size
    r = float(exclude_ratio)
    if r <= 0.0:
        return img
    if r >= 0.9:
        return img
    crop_h = int(round(h * (1.0 - r)))
    crop_h = _clamp_int(crop_h, 1, h)
    return img.crop((0, 0, w, crop_h))


def _apply_cursor_mask(img: Image.Image, cursor_xy: tuple[int, int] | None, *, size_px: int) -> Image.Image:
    if not cursor_xy:
        return img
    s = int(size_px)
    if s <= 0:
        return img

    w, h = img.size
    cx, cy = int(cursor_xy[0]), int(cursor_xy[1])
    half = s // 2
    l = _clamp_int(cx - half, 0, w)
    t = _clamp_int(cy - half, 0, h)
    r = _clamp_int(cx + half, 0, w)
    b = _clamp_int(cy + half, 0, h)
    if r <= l or b <= t:
        return img

    out = img.copy()
    dr = ImageDraw.Draw(out)
    # Fill with mid-gray to avoid introducing high-contrast edges.
    dr.rectangle([l, t, r, b], fill=128)
    return out


def dhash64_hex(
    frame: Image.Image,
    *,
    cfg: ImageAnchorConfig | None = None,
    cursor_xy: tuple[int, int] | None = None,
) -> str:
    """Compute dHash64 (8x8) as 16-hex-character string."""
    cfg = cfg or ImageAnchorConfig()
    img = frame.convert("L")
    img = _apply_taskbar_crop(img, exclude_ratio=cfg.taskbar_exclude_ratio)
    img = _apply_cursor_mask(img, cursor_xy, size_px=cfg.cursor_mask_size_px)

    w = max(2, int(cfg.dhash_width) + 1)
    h = max(1, int(cfg.dhash_height))
    small = img.resize((w, h), resample=Image.Resampling.BILINEAR)
    px = list(small.getdata())

    # Compare adjacent pixels horizontally.
    bits: list[int] = []
    for y in range(h):
        row = px[y * w : (y + 1) * w]
        for x in range(w - 1):
            bits.append(1 if row[x] > row[x + 1] else 0)

    # Pack bits into 64-bit integer.
    v = 0
    for b in bits[:64]:
        v = (v << 1) | int(b)
    return f"{v:016x}"


def hamming_distance_hex64(a: str, b: str) -> int:
    """Hamming distance between two 64-bit hex hashes."""
    try:
        va = int(str(a), 16)
        vb = int(str(b), 16)
    except Exception:
        return 64
    return int((va ^ vb).bit_count())


def min_hamming_to_any(target: str, candidates: Iterable[str]) -> int:
    """Utility for tests/diagnostics: minimal Hamming distance to any candidate."""
    best = 64
    for c in candidates:
        d = hamming_distance_hex64(target, c)
        if d < best:
            best = d
    return best

