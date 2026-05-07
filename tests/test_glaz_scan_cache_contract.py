from __future__ import annotations

import unittest
from pathlib import Path


class TestGlazScanCacheContract(unittest.TestCase):
    @staticmethod
    def _app_text() -> str:
        root = Path(__file__).resolve().parents[1]
        return (root / "Glaz" / "app.py").read_text(encoding="utf-8", errors="replace")

    def test_scan_cache_writes_current_request_id(self) -> None:
        text = self._app_text()
        start = text.index("    def _try_write_cached_scan_results")
        end = text.index("    def _compute_prescan", start)
        body = text[start:end]

        self.assertIn("request_id=str(request_id)", body)
        self.assertIn("items=self._scan_cached_items", body)
        self.assertIn("self._scan_cache_ready", body)
        self.assertIn("self._scan_pending_request_id = None", body)

    def test_scan_cache_is_checked_before_background_prescan(self) -> None:
        text = self._app_text()
        cache_pos = text.index("self._try_write_cached_scan_results")
        submit_pos = text.index("self._scan_executor.submit(self._compute_prescan")

        self.assertLess(cache_pos, submit_pos)

    def test_scan_result_updates_geometry_cache(self) -> None:
        text = self._app_text()
        start = text.index("    def _apply_scan_result")
        end = text.index("    def _request_processing", start)
        body = text[start:end]

        self.assertIn("self._scan_geometry_hash = geometry_hash", body)
        self.assertIn("self._scan_cached_items = items", body)


if __name__ == "__main__":
    unittest.main()
