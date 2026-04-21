"""Стабилизация и сопоставление экранов по множествам объектов.

Задача:
- не создавать новый экран на каждый кадр;
- считать экран равным существующему, если recall/precision достаточно высоки.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .screens_repository import ScreensRepository


@dataclass(frozen=True)
class ResolverConfig:
    stable_delay_sec: float = 0.45
    recall_min: float = 0.8
    precision_min: float = 0.8
    limit_candidates: int = 200


def _overlap_sizes(a: set[str], b: set[str]) -> tuple[int, int, int]:
    """(overlap, a_size, b_size)"""
    if not a or not b:
        return 0, len(a), len(b)
    if len(a) < len(b):
        overlap = sum(1 for x in a if x in b)
    else:
        overlap = sum(1 for x in b if x in a)
    return overlap, len(a), len(b)


def _recall_precision(overlap: int, old_size: int, new_size: int) -> tuple[float, float]:
    recall = overlap / old_size if old_size else 0.0
    precision = overlap / new_size if new_size else 0.0
    return recall, precision


class ScreenResolver:
    """Держит локальное состояние стабильности и выдаёт screen_id."""

    def __init__(self, repo: ScreensRepository, cfg: ResolverConfig | None = None) -> None:
        self._repo = repo
        self._cfg = cfg or ResolverConfig()

        self._candidate_objects: set[str] | None = None
        self._candidate_since: float | None = None
        self._current_screen_id: int | None = None

    @property
    def current_screen_id(self) -> int | None:
        return self._current_screen_id

    def update(
        self,
        object_hashes: set[str],
        *,
        monitor_idx: int | None = None,
        frame_size: tuple[int, int] | None = None,
        now: float | None = None,
    ) -> int | None:
        """Обновить кандидата; вернуть screen_id, когда экран стабилен."""
        now = time.time() if now is None else float(now)

        if self._candidate_objects is None:
            self._candidate_objects = set(object_hashes)
            self._candidate_since = now
            return None

        overlap, old_size, new_size = _overlap_sizes(self._candidate_objects, object_hashes)
        recall, precision = _recall_precision(overlap, old_size, new_size)
        stable = recall >= self._cfg.recall_min and precision >= self._cfg.precision_min

        if not stable:
            self._candidate_objects = set(object_hashes)
            self._candidate_since = now
            return None

        # Множество уже похоже на кандидата достаточно; ждём задержку стабильности
        if self._candidate_since is None:
            self._candidate_since = now
            return None

        if (now - self._candidate_since) < self._cfg.stable_delay_sec:
            return None

        # Кандидат стабилен: резолвим в БД (поиск похожего экрана с теми же порогами)
        best = self._repo.find_best_match(
            set(object_hashes),
            recall_min=self._cfg.recall_min,
            precision_min=self._cfg.precision_min,
            limit_candidates=self._cfg.limit_candidates,
        )
        if best is not None:
            self._repo.touch(best.screen_id)
            self._current_screen_id = best.screen_id
            return best.screen_id

        created = self._repo.create_screen(
            set(object_hashes),
            monitor_idx=monitor_idx,
            frame_size=frame_size,
        )
        self._current_screen_id = created
        return created

