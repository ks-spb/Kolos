"""Стабилизация и сопоставление экранов по множествам объектов.

Задача:
- не создавать новый экран на каждый кадр;
- считать экран равным существующему, если recall/precision достаточно высоки.
"""

from __future__ import annotations

from collections import Counter, deque
import time
from dataclasses import dataclass

from .screens_repository import ScreensRepository
from .image_hash import hamming_distance_hex64


@dataclass(frozen=True)
class ResolverConfig:
    stable_delay_sec: float = 0.45
    # Legacy thresholds (kept for backward compatibility).
    recall_min: float = 0.8
    precision_min: float = 0.8
    limit_candidates: int = 200
    # Windowed stabilization: require N stable frames out of last M.
    # Defaults preserve historical behavior (fast resolve); main.py can override to 6/4.
    window_size: int = 2
    stable_required: int = 1
    # Volatile object filtering: object must appear at least K times in last W frames.
    # Defaults keep filtering effectively off for backward compatibility.
    volatile_window: int = 1
    volatile_min_hits: int = 1
    # Hysteresis thresholds.
    # - stay_*: keep current screen id even if some noise appears.
    # - switch_*: accept candidate as a (potentially) new screen / DB match.
    stay_recall_min: float | None = None
    stay_precision_min: float | None = None
    switch_recall_min: float | None = None
    switch_precision_min: float | None = None
    # Image anchor (perceptual hash) hysteresis.
    use_image_anchor: bool = True
    stay_hamming_max: int = 6
    switch_hamming_min: int = 12


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


def _filter_volatile_objects(
    frames: deque[set[str]],
    *,
    window: int,
    min_hits: int,
) -> set[str]:
    if not frames:
        return set()
    w = max(1, int(window))
    k = max(1, int(min_hits))
    recent = list(frames)[-w:]
    counts: Counter[str] = Counter()
    for s in recent:
        counts.update(s)
    return {h for h, c in counts.items() if c >= k}


def _thresholds(cfg: ResolverConfig) -> tuple[tuple[float, float], tuple[float, float]]:
    switch_recall = cfg.switch_recall_min if cfg.switch_recall_min is not None else cfg.recall_min
    switch_precision = (
        cfg.switch_precision_min if cfg.switch_precision_min is not None else cfg.precision_min
    )
    # Default hysteresis: stay thresholds are softer than switch thresholds.
    stay_recall = cfg.stay_recall_min if cfg.stay_recall_min is not None else min(0.65, switch_recall)
    stay_precision = (
        cfg.stay_precision_min if cfg.stay_precision_min is not None else min(0.55, switch_precision)
    )
    return (stay_recall, stay_precision), (switch_recall, switch_precision)


class ScreenResolver:
    """Держит локальное состояние стабильности и выдаёт screen_id."""

    def __init__(self, repo: ScreensRepository, cfg: ResolverConfig | None = None) -> None:
        self._repo = repo
        self._cfg = cfg or ResolverConfig()

        self._frames: deque[set[str]] = deque(maxlen=max(1, int(self._cfg.window_size)))
        self._stable_flags: deque[bool] = deque(maxlen=max(1, int(self._cfg.window_size)))
        self._candidate_objects: set[str] | None = None
        self._candidate_since: float | None = None
        self._current_screen_id: int | None = None
        self._current_objects: set[str] | None = None
        self._current_image_hash: str | None = None

    @property
    def current_screen_id(self) -> int | None:
        return self._current_screen_id

    def update(
        self,
        object_hashes: set[str],
        *,
        image_hash: str | None = None,
        monitor_idx: int | None = None,
        frame_size: tuple[int, int] | None = None,
        now: float | None = None,
    ) -> int | None:
        """Обновить кандидата; вернуть screen_id, когда экран стабилен."""
        now = time.time() if now is None else float(now)
        raw = set(object_hashes)
        self._frames.append(raw)
        filtered = _filter_volatile_objects(
            self._frames,
            window=self._cfg.volatile_window,
            min_hits=self._cfg.volatile_min_hits,
        )
        # Always keep at least the current frame's objects; volatile filter is only for "extras".
        # This prevents "empty" frames from freezing the resolver.
        if raw:
            filtered |= raw

        (stay_recall_min, stay_precision_min), (switch_recall_min, switch_precision_min) = _thresholds(
            self._cfg
        )

        # Strongest hysteresis: keep current screen if image anchor is close enough.
        if (
            self._cfg.use_image_anchor
            and self._current_screen_id is not None
            and self._current_image_hash is not None
            and image_hash
        ):
            d = hamming_distance_hex64(self._current_image_hash, image_hash)
            if d <= int(self._cfg.stay_hamming_max):
                return self._current_screen_id

        # Hysteresis: if we already have a current screen, keep it under softer thresholds.
        if self._current_screen_id is not None and self._current_objects is not None:
            overlap, old_size, new_size = _overlap_sizes(self._current_objects, filtered)
            recall, precision = _recall_precision(overlap, old_size, new_size)
            if recall >= stay_recall_min and precision >= stay_precision_min:
                return self._current_screen_id

        if self._candidate_objects is None:
            self._candidate_objects = set(filtered)
            self._candidate_since = now
            self._stable_flags.clear()
            # Treat the initial candidate frame as stable against itself,
            # so small-window configs can resolve in 2 calls (backward-friendly).
            self._stable_flags.append(True)
            return None

        overlap, old_size, new_size = _overlap_sizes(self._candidate_objects, filtered)
        recall, precision = _recall_precision(overlap, old_size, new_size)
        stable_frame = recall >= switch_recall_min and precision >= switch_precision_min
        self._stable_flags.append(bool(stable_frame))

        # N-of-M stabilization: don't reset on a single bad frame.
        m = max(1, int(self._cfg.window_size))
        n = max(1, int(self._cfg.stable_required))
        if n > m:
            n = m

        if len(self._stable_flags) == m and sum(1 for x in self._stable_flags if x) < n:
            self._candidate_objects = set(filtered)
            self._candidate_since = now
            self._stable_flags.clear()
            return None

        # Множество уже похоже на кандидата достаточно; ждём задержку стабильности
        if self._candidate_since is None:
            self._candidate_since = now
            return None

        if (now - self._candidate_since) < self._cfg.stable_delay_sec:
            return None
        if len(self._stable_flags) < n or sum(1 for x in self._stable_flags if x) < n:
            return None

        # Кандидат стабилен: резолвим в БД (поиск похожего экрана с теми же порогами)
        best = self._repo.find_best_match(
            set(filtered),
            recall_min=switch_recall_min,
            precision_min=switch_precision_min,
            limit_candidates=self._cfg.limit_candidates,
        )
        if best is not None:
            self._repo.touch(best.screen_id)
            self._current_screen_id = best.screen_id
            self._current_objects = set(filtered)
            self._current_image_hash = str(image_hash) if image_hash else None
            return best.screen_id

        created = self._repo.create_screen(
            set(filtered),
            monitor_idx=monitor_idx,
            frame_size=frame_size,
        )
        self._current_screen_id = created
        self._current_objects = set(filtered)
        self._current_image_hash = str(image_hash) if image_hash else None
        return created

