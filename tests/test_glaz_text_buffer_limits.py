"""Тесты утилит ограничения текстового буфера (Glaz UI)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Glaz"))

from utils import compute_lines_to_delete  # noqa: E402


class TestGlazTextBufferLimits(unittest.TestCase):
    def test_no_delete_when_under_limit(self) -> None:
        self.assertEqual(compute_lines_to_delete(10, 100), 0)

    def test_delete_when_over_limit(self) -> None:
        self.assertEqual(compute_lines_to_delete(105, 100), 5)

    def test_delete_when_limit_zero(self) -> None:
        self.assertEqual(compute_lines_to_delete(7, 0), 7)


if __name__ == "__main__":
    unittest.main()

