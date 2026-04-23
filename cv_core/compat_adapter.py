"""Backward-compatible Screen API powered by Glaz pipeline."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
import pyautogui

from .capture_service import CaptureService
from .config import (
    CAPTURE_INTERVAL_SEC,
    DEFAULT_LINE_MIN_LENGTH,
    DEFAULT_PEAKS_INVERT,
    DEFAULT_PEAKS_THRESHOLD,
)
from .detection_service import DetectionService
from .image_hash import ImageAnchorConfig
from .screen_state import ScreenState


def screenshot(x_reg: int = 0, y_reg: int = 0, region: int = 0):
    """Legacy helper: one-shot screenshot in OpenCV format."""
    if region:
        image = pyautogui.screenshot(region=(x_reg, y_reg, region, region))
    else:
        image = pyautogui.screenshot()
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


@dataclass
class _CompatConfig:
    threshold: int = DEFAULT_PEAKS_THRESHOLD
    invert: bool = DEFAULT_PEAKS_INVERT
    min_line_length: int = DEFAULT_LINE_MIN_LENGTH
    monitor_idx: int = 1


def _read_env_monitor_idx(env: dict[str, str] | None = None) -> int | None:
    """
    Прочитать индекс монитора из окружения.

    Правила:
    - переменная: KOLOS_MONITOR_IDX
    - 1..N — физические мониторы (mss)
    - 0 запрещён (виртуальный «все мониторы вместе»)
    - при ошибке парсинга/диапазона: вернуть None (значит использовать дефолт)
    """
    env = os.environ if env is None else env
    raw = (env.get("KOLOS_MONITOR_IDX") or "").strip()
    if not raw:
        return None
    try:
        idx = int(raw)
    except ValueError:
        return None
    if idx <= 0:
        return None
    return idx


class ScreenCompat:
    """Drop-in replacement for old `screen.Screen` instance API."""

    VERBOSE = False

    def __init__(self) -> None:
        self._capture = CaptureService()
        self._detection = DetectionService()
        self._state = ScreenState()
        self._cfg = _CompatConfig()
        env_monitor = _read_env_monitor_idx()
        if env_monitor is not None:
            self._cfg.monitor_idx = env_monitor
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._last_update = 0.0

        self.screenshot = None
        self.screenshot_hash = None
        self.image_anchor_hash = None
        self.hashes_elements: dict[str, list[int]] = {}
        self._anchor_cfg = ImageAnchorConfig(taskbar_exclude_ratio=0.05, cursor_mask_size_px=120)

    @property
    def monitor_idx(self) -> int:
        """Текущий индекс монитора для захвата (1..N)."""
        return int(self._cfg.monitor_idx)

    @property
    def queue_hashes(self):
        """Compatibility attribute, unused with Glaz pipeline."""
        return None

    @queue_hashes.setter
    def queue_hashes(self, _value) -> None:
        """Ignore old queue assignment from main.py."""
        return

    def start(self) -> None:
        """Start capture + processing loop once."""
        if self._thread and self._thread.is_alive():
            return
        self._capture.start(monitor_idx=self._cfg.monitor_idx, interval=CAPTURE_INTERVAL_SEC)
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop background loop."""
        self._stop.set()
        self._capture.stop()

    def _run(self) -> None:
        while not self._stop.is_set():
            frame = self._capture.latest_frame()
            if frame is not None:
                _, records = self._detection.process(
                    frame=frame,
                    threshold=self._cfg.threshold,
                    invert=self._cfg.invert,
                    min_line_length=self._cfg.min_line_length,
                )
                try:
                    pos = pyautogui.position()
                    cursor_xy = (int(pos.x), int(pos.y))
                except Exception:
                    cursor_xy = None
                snap = self._state.update(frame, records, cursor_xy=cursor_xy, anchor_cfg=self._anchor_cfg)
                self.screenshot = snap.screenshot_np
                self.screenshot_hash = snap.screenshot_hash
                self.image_anchor_hash = snap.image_anchor_hash
                self.hashes_elements = snap.hashes_elements
                self._last_update = time.time()
            time.sleep(0.02)

    def force_refresh_after_move(self, dwell: float = 0.6) -> None:
        """Compatibility replacement for old force-refresh API."""
        if dwell > 0:
            time.sleep(float(dwell))
        frame = self._capture.latest_frame()
        if frame is None:
            return
        _, records = self._detection.process(
            frame=frame,
            threshold=self._cfg.threshold,
            invert=self._cfg.invert,
            min_line_length=self._cfg.min_line_length,
        )
        try:
            pos = pyautogui.position()
            cursor_xy = (int(pos.x), int(pos.y))
        except Exception:
            cursor_xy = None
        snap = self._state.update(frame, records, cursor_xy=cursor_xy, anchor_cfg=self._anchor_cfg)
        self.screenshot = snap.screenshot_np
        self.screenshot_hash = snap.screenshot_hash
        self.image_anchor_hash = snap.image_anchor_hash
        self.hashes_elements = snap.hashes_elements
        self._last_update = time.time()

    def get_screen(self) -> bool:
        """Legacy API: data already pushed by background loop."""
        self.start()
        return self.screenshot is not None

    def tekysie_hash(self):
        return list(self.hashes_elements.keys())

    def get_all_hashes(self):
        return list(self.hashes_elements.keys())

    def list_search(self, x_point, y_point, inside_pad: int = 0):
        self.get_screen()
        candidate = None
        min_sq = None
        for hash_id, (x, y, w, h) in self.hashes_elements.items():
            if (x - inside_pad) <= x_point <= (x + w + inside_pad) and (y - inside_pad) <= y_point <= (y + h + inside_pad):
                sq = w * h
                if min_sq is None or sq < min_sq:
                    min_sq = sq
                    candidate = hash_id
        return candidate

    def element_under_cursor(self):
        pos = pyautogui.position()
        return self.list_search(pos.x, pos.y, inside_pad=1)

    def get_element(self, hash_id):
        if hash_id is None or self.screenshot is None:
            return None
        box = self.hashes_elements.get(hash_id)
        if not box:
            return None
        x, y, w, h = box
        return self.screenshot[y:y + h, x:x + w]

    def get_hash_element(self, hash_id):
        box = self.hashes_elements.get(hash_id)
        if not box:
            return None
        x, y, w, h = box
        return x + (w // 2), y + (h // 2)

    @property
    def last_update(self):
        return self._last_update


screen = ScreenCompat()

