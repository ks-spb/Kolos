from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest


class _Db:
    """Минимальный адаптер под интерфейс db.Database для тестов."""

    def __init__(self, path: str) -> None:
        self._conn = sqlite3.connect(path)

    def execute(self, query: str, values=None):
        cur = self._conn.cursor()
        if values is None:
            return cur.execute(query)
        return cur.execute(query, values)

    def get_last_id(self) -> int:
        return int(self.execute("SELECT last_insert_rowid()").fetchone()[0])

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.commit()
        self._conn.close()


class TestScreenMatching(unittest.TestCase):
    def test_reuses_screen_with_80_percent_overlap(self) -> None:
        from cv_core.screens_repository import ScreensRepository
        from cv_core.screen_resolver import ScreenResolver, ResolverConfig

        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "t.db")
            db = _Db(db_path)
            try:
                repo = ScreensRepository(db)
                repo.ensure_schema()

                base = {f"o{i}" for i in range(100)}
                s1 = repo.create_screen(base, monitor_idx=1, frame_size=(100, 100))
                self.assertIsInstance(s1, int)

                resolver = ScreenResolver(
                    repo,
                    ResolverConfig(stable_delay_sec=0.0, recall_min=0.8, precision_min=0.8, limit_candidates=200),
                )

                # 80 совпали, 20 новых => recall=0.8, precision=0.8
                new = {f"o{i}" for i in range(80)} | {f"x{i}" for i in range(20)}
                # 1й вызов — установка кандидата, 2й — резолв
                resolver.update(new, now=1.0)
                got = resolver.update(new, now=1.0)
                self.assertEqual(got, s1)
            finally:
                db.close()

    def test_creates_new_screen_when_overlap_below_threshold(self) -> None:
        from cv_core.screens_repository import ScreensRepository
        from cv_core.screen_resolver import ScreenResolver, ResolverConfig

        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "t.db")
            db = _Db(db_path)
            try:
                repo = ScreensRepository(db)
                repo.ensure_schema()

                base = {f"o{i}" for i in range(100)}
                s1 = repo.create_screen(base, monitor_idx=1, frame_size=(100, 100))

                resolver = ScreenResolver(
                    repo,
                    ResolverConfig(stable_delay_sec=0.0, recall_min=0.8, precision_min=0.8, limit_candidates=200),
                )

                # 70 совпали, 30 новых => precision=0.7 (ниже порога)
                new = {f"o{i}" for i in range(70)} | {f"x{i}" for i in range(30)}
                resolver.update(new, now=1.0)
                got = resolver.update(new, now=1.0)
                self.assertIsInstance(got, int)
                self.assertNotEqual(got, s1)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()

