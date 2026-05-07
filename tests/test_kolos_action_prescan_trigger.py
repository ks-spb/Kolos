from __future__ import annotations

import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


class TestKolosActionPrescanTrigger(unittest.TestCase):
    """Regression tests for action-only Glaz prescan requests."""

    @staticmethod
    def _main_text() -> str:
        root = Path(__file__).resolve().parents[1]
        return (root / "main.py").read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def _load_main_module():
        root = Path(__file__).resolve().parents[1]
        spec = spec_from_file_location("kolos_root_main_action_prescan", root / "main.py")
        assert spec and spec.loader
        app = module_from_spec(spec)
        spec.loader.exec_module(app)
        return app

    def test_sozdat_svyaz_does_not_write_scan_request_directly(self) -> None:
        text = self._main_text()
        start = text.index("def sozdat_svyaz")
        end = text.index("def sozdat_new_tochky", start)
        body = text[start:end]

        self.assertNotIn("write_scan_request", body)
        self.assertNotIn("_request_objects_prescan", body)

    def test_obrabotka_symbol_requests_prescan_after_action_link(self) -> None:
        text = self._main_text()
        start = text.index("def obrabotka_symbol")
        end = text.index("def sozdat_svyaz", start)
        body = text[start:end]

        link_pos = body.index("sozdat_svyaz(nayti_id_max_signal[0], new_tochka_name)")
        guard_pos = body.index("if _is_action_symbol(symbol):")
        request_pos = body.index('_request_objects_prescan(reason="action_point_link")')

        self.assertLess(link_pos, guard_pos)
        self.assertLess(guard_pos, request_pos)

    def test_out_red_requests_prescan_after_executing_action(self) -> None:
        text = self._main_text()
        start = text.index("def out_red")
        end = text.index("def poisk_id_s_max_signal_points", start)
        body = text[start:end]

        play_pos = body.index("play.play_one(event)")
        request_pos = body.index("_request_prescan_after_action_execution(text[i])")
        helper_pos = text.index("def _request_prescan_after_action_execution")
        reason_pos = text.index('reason="action_executed"', helper_pos)

        self.assertLess(play_pos, request_pos)
        self.assertGreater(reason_pos, helper_pos)

    def test_is_action_symbol_accepts_explicit_action_tokens(self) -> None:
        app = self._load_main_module()

        for symbol in ("click", "hash123.click", "click.hash123", "position.10.20", "Key.enter", "Button.left"):
            with self.subTest(symbol=symbol):
                self.assertTrue(app._is_action_symbol(symbol))

    def test_is_action_symbol_rejects_non_action_tokens(self) -> None:
        app = self._load_main_module()

        for symbol in ("hello", "a", "1", "poz", "id_ekran_42", "position.bad", "", None):
            with self.subTest(symbol=symbol):
                self.assertFalse(app._is_action_symbol(symbol))


if __name__ == "__main__":
    unittest.main()
