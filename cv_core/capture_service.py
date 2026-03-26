"""Capture service based on Glaz screen capture."""

from __future__ import annotations

import threading
from typing import Optional

from PIL import Image

from Glaz.capture import ScreenCapture


class CaptureService:
    """Thread-safe wrapper around Glaz ScreenCapture."""

    def __init__(self) -> None:
        self._capture = ScreenCapture()
        self._lock = threading.Lock()
        self._last_frame: Optional[Image.Image] = None
        self._error: Optional[str] = None

    @property
    def monitor_info(self) -> Optional[dict]:
        """Current monitor info from Glaz capture."""
        return self._capture.monitor_info

    @property
    def is_running(self) -> bool:
        """Capture active flag."""
        return self._capture.is_capturing

    def available_monitors(self) -> list[str]:
        """List available monitors."""
        return self._capture.get_monitors()

    def start(self, monitor_idx: int = 1, interval: float = 0.12) -> None:
        """Start background screen capture."""
        self._capture.selected_monitor = monitor_idx
        self._capture.start(self._on_frame, self._on_error, interval=interval)

    def stop(self) -> None:
        """Stop capture."""
        self._capture.stop()

    def latest_frame(self) -> Optional[Image.Image]:
        """Return a copy of latest frame."""
        with self._lock:
            if self._last_frame is None:
                return None
            return self._last_frame.copy()

    def last_error(self) -> Optional[str]:
        """Return latest capture error message."""
        with self._lock:
            return self._error

    def _on_frame(self, image: Image.Image) -> None:
        with self._lock:
            self._last_frame = image.copy()

    def _on_error(self, message: str) -> None:
        with self._lock:
            self._error = message

