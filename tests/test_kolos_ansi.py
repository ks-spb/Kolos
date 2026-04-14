"""Тесты снятия ANSI и определения красных строк вывода Kolos."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Glaz"))

from kolos_ansi import line_looks_red_in_terminal, strip_sgr  # noqa: E402


class TestKolosAnsi(unittest.TestCase):
    """Примеры как в main.py: \\033[0m / \\033[31m."""

    def test_strip_removes_sgr(self) -> None:
        raw = "\x1b[0m **********************************\n"
        self.assertEqual(strip_sgr(raw), " **********************************\n")

    def test_strip_red_line(self) -> None:
        raw = "\x1b[31m Ответ программы:\n"
        self.assertEqual(strip_sgr(raw), " Ответ программы:\n")
        self.assertTrue(line_looks_red_in_terminal(raw))

    def test_reset_line_not_red(self) -> None:
        raw = "\x1b[0m **********************************\n"
        self.assertFalse(line_looks_red_in_terminal(raw))

    def test_id_line_red(self) -> None:
        raw = "\x1b[31m id_ekran_e75d486e7b85e901\n"
        self.assertTrue(line_looks_red_in_terminal(raw))
        self.assertIn("id_ekran", strip_sgr(raw))


if __name__ == "__main__":
    unittest.main()
