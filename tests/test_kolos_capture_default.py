from __future__ import annotations

import os
import unittest
from pathlib import Path


class TestKolosCaptureDefault(unittest.TestCase):
    def test_capture_disabled_by_default_via_env(self) -> None:
        root = Path(__file__).resolve().parents[1]
        text = (root / "main.py").read_text(encoding="utf-8", errors="replace")
        self.assertIn("KOLOS_CAPTURE", text)
        # По умолчанию должно быть "1" (захват включён)
        self.assertIn('os.environ.get("KOLOS_CAPTURE", "1")', text)

    def test_env_monitor_idx_is_supported_in_compat_adapter(self) -> None:
        root = Path(__file__).resolve().parents[1]
        text = (root / "cv_core" / "compat_adapter.py").read_text(encoding="utf-8", errors="replace")
        self.assertIn("KOLOS_MONITOR_IDX", text)

    def test_read_env_monitor_idx_parses_and_rejects_zero(self) -> None:
        from cv_core.compat_adapter import _read_env_monitor_idx

        self.assertEqual(_read_env_monitor_idx({"KOLOS_MONITOR_IDX": "2"}), 2)
        self.assertIsNone(_read_env_monitor_idx({"KOLOS_MONITOR_IDX": ""}))
        self.assertIsNone(_read_env_monitor_idx({"KOLOS_MONITOR_IDX": "0"}))
        self.assertIsNone(_read_env_monitor_idx({"KOLOS_MONITOR_IDX": "-1"}))
        self.assertIsNone(_read_env_monitor_idx({"KOLOS_MONITOR_IDX": "abc"}))


if __name__ == "__main__":
    unittest.main()

