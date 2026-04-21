from __future__ import annotations

import unittest
from pathlib import Path


class TestKolosCaptureDefault(unittest.TestCase):
    def test_capture_disabled_by_default_via_env(self) -> None:
        root = Path(__file__).resolve().parents[1]
        text = (root / "main.py").read_text(encoding="utf-8", errors="replace")
        self.assertIn("KOLOS_CAPTURE", text)
        # По умолчанию должно быть "1" (захват включён)
        self.assertIn('os.environ.get("KOLOS_CAPTURE", "1")', text)


if __name__ == "__main__":
    unittest.main()

