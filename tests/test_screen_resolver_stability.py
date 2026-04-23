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


class TestScreenResolverStability(unittest.TestCase):
    def test_single_noisy_frame_does_not_force_new_screen(self) -> None:
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
                    ResolverConfig(
                        stable_delay_sec=0.0,
                        recall_min=0.8,
                        precision_min=0.8,
                        window_size=6,
                        stable_required=4,
                        volatile_window=1,  # disable volatile filter effect for this synthetic test
                        volatile_min_hits=1,
                    ),
                )

                good = {f"o{i}" for i in range(80)} | {f"x{i}" for i in range(20)}  # recall=0.8 precision=0.8
                noisy = {f"z{i}" for i in range(100)}  # completely different

                # Feed: 3 good, 1 noisy, 3 good -> should still resolve to existing screen s1.
                seq = [good, good, good, noisy, good, good, good]
                got = None
                t = 1.0
                for s in seq:
                    got = resolver.update(set(s), now=t)
                    t += 0.1

                self.assertEqual(got, s1)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()

