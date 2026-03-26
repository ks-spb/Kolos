"""Shared runtime state of current screen and detections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from PIL import Image

from .detection_service import DetectedRecord
from .hash_compat import screen_hash_for_frame


@dataclass
class ScreenSnapshot:
    """Data exposed to compatibility API."""

    screenshot_np: np.ndarray
    screenshot_hash: str
    hashes_elements: dict[str, list[int]]
    elements_map: dict[str, DetectedRecord]


class ScreenState:
    """Thread-safe container for latest screen snapshot."""

    def __init__(self) -> None:
        self._snapshot: Optional[ScreenSnapshot] = None

    def update(self, frame: Image.Image, records: list[DetectedRecord]) -> ScreenSnapshot:
        """Replace snapshot from frame + records."""
        frame_np = np.array(frame.convert("RGB"))[:, :, ::-1].copy()
        hashes_elements = {r.hash_id: [*r.bbox_xywh] for r in records}
        screenshot_hash = screen_hash_for_frame(frame.size, hashes_elements.keys())
        elements_map = {r.hash_id: r for r in records}
        self._snapshot = ScreenSnapshot(
            screenshot_np=frame_np,
            screenshot_hash=screenshot_hash,
            hashes_elements=hashes_elements,
            elements_map=elements_map,
        )
        return self._snapshot

    def get(self) -> Optional[ScreenSnapshot]:
        """Read last snapshot."""
        return self._snapshot

