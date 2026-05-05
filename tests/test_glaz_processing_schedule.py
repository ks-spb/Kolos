"""Тесты адаптивного планировщика обработки кадров (Glaz)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Glaz"))

from utils import decide_processing_schedule  # noqa: E402


class TestGlazProcessingSchedule(unittest.TestCase):
    def test_non_idle_always_process(self) -> None:
        should, last_pos, stable_since, last_idle = decide_processing_schedule(
            now=10.0,
            cursor_pos=(100, 200),
            recognition_is_idle=False,
            cursor_stable_delay_s=0.5,
            idle_processing_period_s=1.5,
            last_cursor_pos=None,
            cursor_stable_since=None,
            last_idle_processing_time=0.0,
        )
        self.assertTrue(should)
        self.assertEqual(last_pos, (100, 200))
        self.assertEqual(stable_since, 10.0)
        self.assertEqual(last_idle, 0.0)

    def test_idle_process_when_cursor_stable(self) -> None:
        # Курсор не менялся 0.6с при задержке 0.5с => stable => should_process=True
        should, last_pos, stable_since, last_idle = decide_processing_schedule(
            now=10.6,
            cursor_pos=(10, 10),
            recognition_is_idle=True,
            cursor_stable_delay_s=0.5,
            idle_processing_period_s=999.0,
            last_cursor_pos=(10, 10),
            cursor_stable_since=10.0,
            last_idle_processing_time=0.0,
        )
        self.assertTrue(should)
        self.assertEqual(last_pos, (10, 10))
        self.assertEqual(stable_since, 10.0)
        self.assertEqual(last_idle, 0.0)

    def test_idle_moving_cursor_uses_heartbeat_period(self) -> None:
        # Движение => stable_since обновится, stable=False.
        # Период 1.5с: на 10.0 (после 8.0) можно, на 10.4 нельзя.
        should1, last_pos1, stable_since1, last_idle1 = decide_processing_schedule(
            now=10.0,
            cursor_pos=(1, 1),
            recognition_is_idle=True,
            cursor_stable_delay_s=0.5,
            idle_processing_period_s=1.5,
            last_cursor_pos=(0, 0),
            cursor_stable_since=9.9,
            last_idle_processing_time=8.0,
        )
        self.assertTrue(should1)
        self.assertEqual(last_pos1, (1, 1))
        self.assertEqual(stable_since1, 10.0)
        self.assertEqual(last_idle1, 10.0)

        should2, last_pos2, stable_since2, last_idle2 = decide_processing_schedule(
            now=10.4,
            cursor_pos=(2, 1),
            recognition_is_idle=True,
            cursor_stable_delay_s=0.5,
            idle_processing_period_s=1.5,
            last_cursor_pos=last_pos1,
            cursor_stable_since=stable_since1,
            last_idle_processing_time=last_idle1,
        )
        self.assertFalse(should2)
        self.assertEqual(last_pos2, (2, 1))
        self.assertEqual(stable_since2, 10.4)
        self.assertEqual(last_idle2, 10.0)


if __name__ == "__main__":
    unittest.main()

