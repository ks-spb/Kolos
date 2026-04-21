from __future__ import annotations

import unittest
from pathlib import Path


class TestKolosScreenWriteGuard(unittest.TestCase):
    def test_perenos_sostoyaniya_returns_before_obrabotka_when_same_screen(self) -> None:
        root = Path(__file__).resolve().parents[1]
        text = (root / "main.py").read_text(encoding="utf-8", errors="replace")

        # Проверяем порядок: guard должен быть раньше вызова obrabotka_symbol(new_name_id_ekran)
        guard = "if old_ekran == new_name_id_ekran"
        call = "obrabotka_symbol(new_name_id_ekran)"
        self.assertIn(guard, text)
        self.assertIn(call, text)
        self.assertLess(text.index(guard), text.index(call))


if __name__ == "__main__":
    unittest.main()

