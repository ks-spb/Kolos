"""Тесты нормальной геометрии окна Glaz между максимизациями."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Glaz"))

from app import _normal_window_geometry  # noqa: E402


class TestGlazWindowGeometry(unittest.TestCase):
    def test_restore_size_fits_full_hd_secondary_monitor(self) -> None:
        monitor = {"left": 1920, "top": 0, "width": 1920, "height": 1080}

        self.assertEqual(_normal_window_geometry(monitor), "1600x900+2080+90")

    def test_small_monitor_and_negative_coordinates_stay_in_bounds(self) -> None:
        monitor = {"left": -1280, "top": -200, "width": 1280, "height": 720}

        self.assertEqual(_normal_window_geometry(monitor), "1200x640-1240-160")

    def test_tiny_monitor_never_produces_zero_or_negative_size(self) -> None:
        monitor = {"left": 0, "top": 0, "width": 40, "height": 30}

        self.assertEqual(_normal_window_geometry(monitor), "1x1+19+14")

    def test_window_position_sets_restore_geometry_before_idle_maximize(self) -> None:
        from app import ScreenCaptureApp

        class FakeRoot:
            def __init__(self) -> None:
                self.geometry_value = ""
                self.idle_callback = None
                self.state_value = "normal"

            def geometry(self, value: str) -> None:
                self.geometry_value = value

            def after_idle(self, callback) -> None:
                self.idle_callback = callback

            def state(self, value: str) -> None:
                self.state_value = value

        class FakeMssContext:
            monitors = [
                {"left": 0, "top": 0, "width": 3840, "height": 1080},
                {"left": 0, "top": 0, "width": 1920, "height": 1080},
                {"left": 1920, "top": 0, "width": 1920, "height": 1080},
            ]

            def __enter__(self):
                return self

            def __exit__(self, *_args) -> None:
                return None

        root = FakeRoot()
        application = ScreenCaptureApp.__new__(ScreenCaptureApp)
        application.root = root
        fake_mss = types.SimpleNamespace(mss=FakeMssContext)

        with patch.dict(sys.modules, {"mss": fake_mss}):
            application._setup_window_position()

        self.assertEqual(root.geometry_value, "1600x900+2080+90")
        self.assertEqual(root.state_value, "normal")
        self.assertIsNotNone(root.idle_callback)
        root.idle_callback()
        self.assertEqual(root.state_value, "zoomed")


if __name__ == "__main__":
    unittest.main()
