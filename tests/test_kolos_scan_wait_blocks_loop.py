from __future__ import annotations

import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


class TestKolosScanWaitBlocksLoop(unittest.TestCase):
    @staticmethod
    def _main_text() -> str:
        root = Path(__file__).resolve().parents[1]
        return (root / "main.py").read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def _load_main_module():
        root = Path(__file__).resolve().parents[1]
        spec = spec_from_file_location("kolos_root_main_scan_wait", root / "main.py")
        assert spec and spec.loader
        app = module_from_spec(spec)
        spec.loader.exec_module(app)
        return app

    def test_pending_scan_is_polled_before_schetchik_increment(self) -> None:
        text = self._main_text()
        loop_pos = text.index("while A:")
        body = text[loop_pos:]

        wait_pos = body.index("if _poll_pending_scan_and_block_loop():")
        increment_pos = body.index("schetchik += 1")

        self.assertLess(wait_pos, increment_pos)

    def test_pending_scan_without_result_blocks_loop(self) -> None:
        app = self._load_main_module()
        app._pending_scan_request_id = "req-1"
        app._printed_scan_result_for_request_id = None
        app._printed_scan_requested_for_request_id = None
        app._scan_poll_attempts = 0
        app._scan_poll_attempts_max = 3
        app._print_scan_results_if_ready = lambda *, request_id: False
        app.sleep = lambda *_args, **_kwargs: None

        self.assertTrue(app._poll_pending_scan_and_block_loop())
        self.assertEqual(app._pending_scan_request_id, "req-1")
        self.assertEqual(app._scan_poll_attempts, 1)

    def test_pending_scan_with_result_unblocks_loop(self) -> None:
        app = self._load_main_module()
        app._pending_scan_request_id = "req-1"
        app._printed_scan_result_for_request_id = None
        app._printed_scan_requested_for_request_id = None
        app._scan_poll_attempts = 0
        app._scan_poll_attempts_max = 3
        app._print_scan_results_if_ready = lambda *, request_id: True
        app.sleep = lambda *_args, **_kwargs: None

        self.assertFalse(app._poll_pending_scan_and_block_loop())
        self.assertIsNone(app._pending_scan_request_id)
        self.assertEqual(app._scan_poll_attempts, 1)

    def test_pending_scan_timeout_unblocks_loop_with_warning(self) -> None:
        app = self._load_main_module()
        app._pending_scan_request_id = "req-1"
        app._printed_scan_result_for_request_id = None
        app._printed_scan_requested_for_request_id = "req-1"
        app._scan_poll_attempts = 3
        app._scan_poll_attempts_max = 3
        app._print_scan_results_if_ready = lambda *, request_id: False
        app.sleep = lambda *_args, **_kwargs: None

        self.assertFalse(app._poll_pending_scan_and_block_loop())
        self.assertIsNone(app._pending_scan_request_id)


if __name__ == "__main__":
    unittest.main()
