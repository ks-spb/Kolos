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


class TestScreenResolverImageAnchor(unittest.TestCase):
    def test_stays_on_current_screen_when_image_hash_close(self) -> None:
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
                        window_size=2,
                        stable_required=1,
                        volatile_window=1,
                        volatile_min_hits=1,
                        use_image_anchor=True,
                        stay_hamming_max=6,
                        switch_hamming_min=12,
                    ),
                )

                good = {f"o{i}" for i in range(80)} | {f"x{i}" for i in range(20)}
                noisy = {f"z{i}" for i in range(100)}

                # Resolve initial screen with some image hash.
                resolver.update(good, image_hash="0" * 16, now=1.0)
                got = resolver.update(good, image_hash="0" * 16, now=1.0)
                self.assertEqual(got, s1)

                # Now provide wildly different objects but almost same image hash.
                stay = resolver.update(noisy, image_hash="0" * 16, now=2.0)
                self.assertEqual(stay, s1)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()

