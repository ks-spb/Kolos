"""Регрессия: справочник цифр Kolos в Glaz."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Glaz"))

from kolos_digits_hint import KOLOS_DIGITS_HINT_RU  # noqa: E402


class TestKolosDigitsHint(unittest.TestCase):
    """Все десять цифр упомянуты, формат строк с пояснением."""

    def test_covers_0_through_9(self) -> None:
        for prefix in (f"{d} —" for d in "0123456789"):
            self.assertIn(prefix, KOLOS_DIGITS_HINT_RU)

    def test_nonempty_lines(self) -> None:
        lines = [ln.strip() for ln in KOLOS_DIGITS_HINT_RU.strip().splitlines() if ln.strip()]
        self.assertGreaterEqual(len(lines), 10)


if __name__ == "__main__":
    unittest.main()
