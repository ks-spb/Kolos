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

    def test_user_input_dispatch_calls_screen_guard_before_writing_symbols(self) -> None:
        root = Path(__file__).resolve().parents[1]
        text = (root / "main.py").read_text(encoding="utf-8", errors="replace")

        guard_call = 'ensure_current_screen_before_input(context="user_input_dispatch")'
        loop = "for vvedeno_luboe1 in vvedeno_luboe:"
        self.assertIn(guard_call, text)
        self.assertIn(loop, text)
        self.assertLess(text.index(guard_call), text.index(loop))

    def test_command_1_branch_guards_before_obrabotka_old_ekran(self) -> None:
        root = Path(__file__).resolve().parents[1]
        text = (root / "main.py").read_text(encoding="utf-8", errors="replace")

        guard_call = 'ensure_current_screen_before_input(context="command_1_bind_to_screen")'
        call = "obrabotka_symbol(old_ekran)"
        self.assertIn(guard_call, text)
        self.assertIn(call, text)
        self.assertLess(text.index(guard_call), text.index(call))


if __name__ == "__main__":
    unittest.main()

