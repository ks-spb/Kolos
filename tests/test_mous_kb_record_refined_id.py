from __future__ import annotations

import unittest


class TestMouseKbRecordRefinedId(unittest.TestCase):
    def test_click_event_contains_refined_id_fields(self) -> None:
        # Импортируем модуль и подменяем IPC reader, чтобы не зависеть от файловой системы.
        import mous_kb_record as mkr

        class _Target:
            refined_id = 42

        # patch read_last_confirmed_target
        orig_reader = mkr.read_last_confirmed_target
        mkr.read_last_confirmed_target = lambda max_age_sec=2.0: _Target()  # type: ignore[assignment]

        # patch screen.element_under_cursor to make deterministic
        orig_euc = mkr.screen.element_under_cursor
        mkr.screen.element_under_cursor = lambda: "hash123"  # type: ignore[assignment]

        # patch report IO
        orig_circle = mkr.report.circle_an_object
        orig_save = mkr.report.save
        mkr.report.circle_an_object = lambda *a, **k: None  # type: ignore[assignment]
        mkr.report.save = lambda *a, **k: None  # type: ignore[assignment]

        # patch screenshot to avoid real capture
        orig_screenshot = mkr.screenshot
        mkr.screenshot = lambda *a, **k: None  # type: ignore[assignment]

        try:
            r = mkr.Recorder()
            r.record.clear()
            r.on_click(10, 20, None, True)
            self.assertEqual(len(r.record), 1)
            ev = r.record[0]
            self.assertEqual(ev["event"], "click")
            self.assertEqual(ev["refined_id"], 42)
            self.assertFalse(ev["unresolved"])
            self.assertEqual(ev["image"], "hash123")
            self.assertEqual(ev["x"], 10)
            self.assertEqual(ev["y"], 20)
        finally:
            mkr.read_last_confirmed_target = orig_reader  # type: ignore[assignment]
            mkr.screen.element_under_cursor = orig_euc  # type: ignore[assignment]
            mkr.report.circle_an_object = orig_circle  # type: ignore[assignment]
            mkr.report.save = orig_save  # type: ignore[assignment]
            mkr.screenshot = orig_screenshot  # type: ignore[assignment]


if __name__ == "__main__":
    unittest.main()

