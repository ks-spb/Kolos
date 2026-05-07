from __future__ import annotations

import unittest
from pathlib import Path


class TestKolosScreenWriteGuard(unittest.TestCase):
    """Checks that Kolos no longer depends on current-screen resolution."""

    def _main_text(self) -> str:
        root = Path(__file__).resolve().parents[1]
        return (root / "main.py").read_text(encoding="utf-8", errors="replace")

    def test_user_input_dispatches_without_screen_guard(self) -> None:
        text = self._main_text()
        branch_start = text.index('elif vvedeno_luboe != "":')
        branch_end = text.index("else:", branch_start)
        branch = text[branch_start:branch_end]

        self.assertIn("_dispatch_input_symbols", branch)
        self.assertNotIn("ensure_current_screen_before_input", branch)
        self.assertNotIn("_enqueue_pending_input", branch)

    def test_positive_reaction_does_not_bind_to_old_screen(self) -> None:
        text = self._main_text()
        branch_start = text.index("elif vvedeno_luboe in [' 1', '1']:")
        branch_end = text.index("elif vvedeno_luboe in [' 2', '2']:", branch_start)
        branch = text[branch_start:branch_end]

        self.assertNotIn("command_1_bind_to_screen", branch)
        self.assertNotIn("obrabotka_symbol(old_ekran)", branch)

    def test_kolos_does_not_start_screen_capture(self) -> None:
        text = self._main_text()

        self.assertIn("screen_capture_enabled = False", text)
        self.assertNotIn("screen.start()", text)


if __name__ == "__main__":
    unittest.main()
