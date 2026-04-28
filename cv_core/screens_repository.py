"""Хранилище экранов (screen_id -> множество object_hash) в SQLite.

Цель: не плодить экраны из-за шума детекции.
Экран считается одинаковым, если множества объектов достаточно похожи.

Схема (создаётся автоматически):
- screens: метаданные и размер множества
- screen_objects: состав экрана (уникальные object_hash)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ScreenMatch:
    """Результат сопоставления множеств объектов."""

    screen_id: int
    overlap: int
    new_size: int
    old_size: int

    @property
    def recall(self) -> float:
        # overlap / old_size
        return self.overlap / self.old_size if self.old_size else 0.0

    @property
    def precision(self) -> float:
        # overlap / new_size
        return self.overlap / self.new_size if self.new_size else 0.0


class ScreensRepository:
    """Репозиторий экранов на базе существующего Database.execute API."""

    def __init__(self, db) -> None:
        self._db = db

    def ensure_schema(self) -> None:
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS screens (
                screen_id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at_ms INTEGER NOT NULL,
                last_seen_at_ms INTEGER NOT NULL,
                monitor_idx INTEGER,
                frame_w INTEGER,
                frame_h INTEGER,
                objects_count INTEGER NOT NULL
            )
            """
        )
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS screen_objects (
                screen_id INTEGER NOT NULL,
                object_hash TEXT NOT NULL,
                PRIMARY KEY (screen_id, object_hash)
            )
            """
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_screen_objects_object ON screen_objects(object_hash)"
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_screen_objects_screen ON screen_objects(screen_id)"
        )

    def find_best_match(
        self,
        object_hashes: set[str],
        *,
        recall_min: float,
        precision_min: float,
        limit_candidates: int = 200,
    ) -> ScreenMatch | None:
        if not object_hashes:
            return None

        placeholders = ",".join("?" for _ in object_hashes)
        rows = self._db.execute(
            f"""
            SELECT so.screen_id, COUNT(*) AS overlap
            FROM screen_objects AS so
            WHERE so.object_hash IN ({placeholders})
            GROUP BY so.screen_id
            ORDER BY overlap DESC
            LIMIT ?
            """,
            (*object_hashes, int(limit_candidates)),
        ).fetchall()

        if not rows:
            return None

        best: ScreenMatch | None = None
        new_size = len(object_hashes)
        considered: list[dict] = []
        for screen_id, overlap in rows:
            old_size_row = self._db.execute(
                "SELECT objects_count FROM screens WHERE screen_id = ?",
                (int(screen_id),),
            ).fetchone()
            if not old_size_row:
                continue
            old_size = int(old_size_row[0] or 0)
            cand = ScreenMatch(
                screen_id=int(screen_id),
                overlap=int(overlap),
                new_size=new_size,
                old_size=old_size,
            )
            if len(considered) < 8:
                considered.append(
                    {
                        "screen_id": cand.screen_id,
                        "overlap": cand.overlap,
                        "old_size": cand.old_size,
                        "new_size": cand.new_size,
                        "recall": cand.recall,
                        "precision": cand.precision,
                        "passes_threshold": (cand.recall >= recall_min and cand.precision >= precision_min),
                    }
                )
            if cand.recall < recall_min or cand.precision < precision_min:
                continue
            if best is None:
                best = cand
                continue
            if (cand.recall, cand.precision, cand.overlap) > (
                best.recall,
                best.precision,
                best.overlap,
            ):
                best = cand

        return best

    def touch(self, screen_id: int) -> None:
        now_ms = int(time.time() * 1000)
        self._db.execute(
            "UPDATE screens SET last_seen_at_ms = ? WHERE screen_id = ?",
            (now_ms, int(screen_id)),
        )

    def create_screen(
        self,
        object_hashes: set[str],
        *,
        monitor_idx: int | None = None,
        frame_size: tuple[int, int] | None = None,
    ) -> int:
        now_ms = int(time.time() * 1000)
        w: int | None = None
        h: int | None = None
        if frame_size is not None:
            w, h = int(frame_size[0]), int(frame_size[1])

        self._db.execute(
            """
            INSERT INTO screens(created_at_ms, last_seen_at_ms, monitor_idx, frame_w, frame_h, objects_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (now_ms, now_ms, monitor_idx, w, h, len(object_hashes)),
        )
        screen_id = int(self._db.get_last_id())

        if object_hashes:
            self._insert_objects(screen_id, object_hashes)
        return screen_id

    def _insert_objects(self, screen_id: int, object_hashes: Iterable[str]) -> None:
        # executemany нет в Database API; вставляем в цикле.
        for h in object_hashes:
            self._db.execute(
                "INSERT OR IGNORE INTO screen_objects(screen_id, object_hash) VALUES (?, ?)",
                (int(screen_id), str(h)),
            )

