from __future__ import annotations

import json
import os
import tempfile
import unittest


class TestGlazIpcScanRequestAndResults(unittest.TestCase):
    def test_scan_request_roundtrip_and_ttl(self) -> None:
        from cv_core import glaz_ipc

        with tempfile.TemporaryDirectory() as td:
            req_path = os.path.join(td, "scan_request.json")
            orig = glaz_ipc.scan_request_path
            glaz_ipc.scan_request_path = lambda: req_path  # type: ignore[assignment]
            try:
                rid = glaz_ipc.write_scan_request(reason="svyazi_insert", timestamp=100.0, request_id="r1")
                self.assertEqual(rid, "r1")
                req = glaz_ipc.read_scan_request(max_age_sec=2.0, now=101.0)
                self.assertIsNotNone(req)
                assert req is not None
                self.assertEqual(req.request_id, "r1")
                self.assertAlmostEqual(req.timestamp, 100.0, places=6)
                self.assertEqual(req.reason, "svyazi_insert")

                self.assertIsNone(glaz_ipc.read_scan_request(max_age_sec=2.0, now=103.0))
            finally:
                glaz_ipc.scan_request_path = orig  # type: ignore[assignment]

    def test_scan_results_roundtrip_and_ttl(self) -> None:
        from cv_core import glaz_ipc

        with tempfile.TemporaryDirectory() as td:
            res_path = os.path.join(td, "scan_results.json")
            orig = glaz_ipc.scan_results_path
            glaz_ipc.scan_results_path = lambda: res_path  # type: ignore[assignment]
            try:
                results = glaz_ipc.ScanResults(
                    request_id="r2",
                    timestamp=100.0,
                    items=(
                        glaz_ipc.ScanResultItem(refined_id=12, count=3, is_new=False),
                        glaz_ipc.ScanResultItem(refined_id=99, count=1, is_new=True),
                    ),
                )
                glaz_ipc.write_scan_results(results, timestamp=100.0)
                got = glaz_ipc.read_scan_results(max_age_sec=2.0, now=101.0)
                self.assertIsNotNone(got)
                assert got is not None
                self.assertEqual(got.request_id, "r2")
                self.assertAlmostEqual(got.timestamp, 100.0, places=6)
                self.assertEqual(len(got.items), 2)
                self.assertEqual(got.items[0].refined_id, 12)
                self.assertEqual(got.items[0].count, 3)
                self.assertFalse(got.items[0].is_new)
                self.assertEqual(got.items[1].refined_id, 99)
                self.assertEqual(got.items[1].count, 1)
                self.assertTrue(got.items[1].is_new)

                self.assertIsNone(glaz_ipc.read_scan_results(max_age_sec=2.0, now=103.0))
            finally:
                glaz_ipc.scan_results_path = orig  # type: ignore[assignment]

    def test_scan_results_read_rejects_invalid_payload(self) -> None:
        from cv_core import glaz_ipc

        with tempfile.TemporaryDirectory() as td:
            res_path = os.path.join(td, "scan_results.json")
            with open(res_path, "w", encoding="utf-8") as f:
                json.dump({"request_id": "x", "timestamp": 1.0, "items": "not-a-list"}, f)
            orig = glaz_ipc.scan_results_path
            glaz_ipc.scan_results_path = lambda: res_path  # type: ignore[assignment]
            try:
                self.assertIsNone(glaz_ipc.read_scan_results(max_age_sec=10.0, now=2.0))
            finally:
                glaz_ipc.scan_results_path = orig  # type: ignore[assignment]


if __name__ == "__main__":
    unittest.main()

