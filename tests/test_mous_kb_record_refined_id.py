from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path


class TestMouseKbRecordRefinedId(unittest.TestCase):
    def test_recorder_click_does_not_probe_legacy_screen_target(self) -> None:
        root = Path(__file__).resolve().parents[1]
        text = (root / "mous_kb_record.py").read_text(encoding="utf-8", errors="replace")
        start = text.index("    def on_click")
        end = text.index("    def on_scroll", start)
        body = text[start:end]

        self.assertNotIn("screen.element_under_cursor()", body)
        self.assertIn("_read_click_glaz_target", body)

    def test_click_event_contains_glaz_target_name_when_bbox_contains_click(self) -> None:
        import mous_kb_record as mkr

        class _Target:
            refined_id = 42
            center_xy = (10, 20)
            bbox_ltrb = (1, 2, 30, 40)

        orig_reader = mkr.read_last_confirmed_target
        mkr.read_last_confirmed_target = lambda max_age_sec=2.0: _Target()  # type: ignore[assignment]
        try:
            r = mkr.Recorder()
            r.record.clear()
            out = io.StringIO()
            with redirect_stdout(out):
                r.on_click(10, 20, None, True)

            self.assertEqual(len(r.record), 1)
            ev = r.record[0]
            self.assertEqual(ev["event"], "click")
            self.assertEqual(ev["refined_id"], 42)
            self.assertEqual(ev["target_name"], "glaz.42")
            self.assertFalse(ev["unresolved"])
            self.assertNotIn("image", ev)
            self.assertEqual(ev["glaz_center_xy"], (10, 20))
            self.assertEqual(ev["glaz_bbox_ltrb"], (1, 2, 30, 40))
            self.assertEqual(ev["x"], 10)
            self.assertEqual(ev["y"], 20)
            self.assertIn("Объекты определены. Можно продолжать действия.", out.getvalue())
        finally:
            mkr.read_last_confirmed_target = orig_reader  # type: ignore[assignment]

    def test_click_event_is_unresolved_when_bbox_misses_click(self) -> None:
        import mous_kb_record as mkr

        class _Target:
            refined_id = 42
            center_xy = (10, 20)
            bbox_ltrb = (1, 2, 5, 6)

        orig_reader = mkr.read_last_confirmed_target
        mkr.read_last_confirmed_target = lambda max_age_sec=2.0: _Target()  # type: ignore[assignment]
        try:
            r = mkr.Recorder()
            r.record.clear()
            out = io.StringIO()
            with redirect_stdout(out):
                r.on_click(10, 20, None, True)

            ev = r.record[0]
            self.assertIsNone(ev["refined_id"])
            self.assertIsNone(ev["target_name"])
            self.assertTrue(ev["unresolved"])
            self.assertNotIn("image", ev)
            self.assertIn("Объекты пока не подтверждены", out.getvalue())
        finally:
            mkr.read_last_confirmed_target = orig_reader  # type: ignore[assignment]

    def test_glaz_status_prints_only_on_change(self) -> None:
        import mous_kb_record as mkr

        r = mkr.Recorder()
        out = io.StringIO()
        with redirect_stdout(out):
            r._set_glaz_status("detecting")
            r._set_glaz_status("detecting")
            r._set_glaz_status("ready")

        text = out.getvalue()
        self.assertEqual(text.count("Объекты экрана определяются"), 1)
        self.assertEqual(text.count("Объекты определены"), 1)


if __name__ == "__main__":
    unittest.main()
