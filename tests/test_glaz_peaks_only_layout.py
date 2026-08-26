"""Тесты компоновки Glaz с единственным видимым экраном пиков."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "Glaz"))

import app as glaz_app  # noqa: E402
import loupe as glaz_loupe  # noqa: E402


class _FakeWidget:
    def __init__(self, *args, **kwargs) -> None:
        self.children = []

    def pack(self, *args, **kwargs) -> None:
        return None

    def pack_propagate(self, *args, **kwargs) -> None:
        return None

    def add(self, child, *args, **kwargs) -> None:
        self.children.append(child)


class TestGlazPeaksOnlyLayout(unittest.TestCase):
    def test_setup_ui_omits_screenshot_and_places_peaks_after_monitor(self) -> None:
        instance = glaz_app.ScreenCaptureApp.__new__(glaz_app.ScreenCaptureApp)
        instance.root = object()
        calls: list[str] = []

        for name in (
            "_setup_monitor_frame",
            "_setup_peaks_frame",
            "_setup_error_frame",
            "_setup_status_bar",
            "_setup_screenshot_previews",
            "_setup_objects_table",
            "_update_objects_table",
        ):
            setattr(instance, name, Mock(side_effect=lambda n=name: calls.append(n)))
        instance._setup_screenshot_frame = Mock()
        instance.log_message = Mock()

        with (
            patch.object(glaz_app.ttk, "Frame", _FakeWidget),
            patch.object(glaz_app.ttk, "PanedWindow", _FakeWidget),
        ):
            instance._setup_ui()

        instance._setup_screenshot_frame.assert_not_called()
        self.assertEqual(calls[:2], ["_setup_monitor_frame", "_setup_peaks_frame"])

    def test_loupe_controller_runs_without_screenshot_canvas(self) -> None:
        peaks_canvas = Mock()
        controller = glaz_loupe.LoupeController(None, peaks_canvas, loupe_size=20)
        frame = Image.new("RGB", (100, 100), "white")

        with (
            patch.object(glaz_loupe, "get_cursor_pos", return_value=(50, 50)),
            patch.object(glaz_loupe.ImageTk, "PhotoImage", return_value=object()),
        ):
            controller.update(
                current_image=frame,
                monitor_info={"left": 0, "top": 0, "width": 100, "height": 100},
                current_scale=1.0,
                peaks_scale_percent=100,
                peaks_threshold=100,
                peaks_invert=False,
            )

        self.assertIsNone(controller.main_loupe)
        self.assertTrue(controller.peaks_loupe_data.is_visible)


if __name__ == "__main__":
    unittest.main()
