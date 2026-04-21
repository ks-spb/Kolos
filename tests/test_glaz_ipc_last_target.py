from __future__ import annotations

import json
import os
import tempfile
import unittest


class TestGlazIpcLastTarget(unittest.TestCase):
    def test_roundtrip_write_and_read(self) -> None:
        from cv_core import glaz_ipc

        with tempfile.TemporaryDirectory() as td:
            # Подменяем путь, чтобы не трогать реальный ~/.glaz
            path = os.path.join(td, "last_target.json")

            orig = glaz_ipc.last_target_path
            glaz_ipc.last_target_path = lambda: path  # type: ignore[assignment]
            try:
                glaz_ipc.write_last_confirmed_target(12, timestamp=100.0)
                target = glaz_ipc.read_last_confirmed_target(max_age_sec=2.0, now=101.0)
                self.assertIsNotNone(target)
                assert target is not None
                self.assertEqual(target.refined_id, 12)
                self.assertAlmostEqual(target.timestamp, 100.0, places=6)
            finally:
                glaz_ipc.last_target_path = orig  # type: ignore[assignment]

    def test_read_rejects_expired(self) -> None:
        from cv_core import glaz_ipc

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "last_target.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"refined_id": 7, "timestamp": 10.0}, f)

            orig = glaz_ipc.last_target_path
            glaz_ipc.last_target_path = lambda: path  # type: ignore[assignment]
            try:
                self.assertIsNone(glaz_ipc.read_last_confirmed_target(max_age_sec=2.0, now=13.1))
            finally:
                glaz_ipc.last_target_path = orig  # type: ignore[assignment]


if __name__ == "__main__":
    unittest.main()

