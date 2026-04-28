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
    """
    Вернуть "стабильные" объекты для ТЕКУЩЕГО кадра.

    Важно: нельзя возвращать объекты, которых нет в текущем кадре — иначе при смене экрана
    в окно стабилизации начинают "протекать" хэши из предыдущего экрана и резолв дрожит.
    """
    if not frames:
        return set()
    raw = set(frames[-1])  # текущий кадр
    if not raw:
        return set()
    w = max(1, int(window))
    k = max(1, int(min_hits))
    if w <= 1 and k <= 1:
        return raw
    recent = list(frames)[-w:]
    counts: Counter[str] = Counter()
    for s in recent:
        counts.update(s)
    stable_now = {h for h in raw if counts.get(h, 0) >= k}
    # Если фильтр оказался слишком жёстким — не возвращаем пустоту (это ломает резолв).
    return stable_now or raw


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

    def _dbg_dd836d(self, hypothesis_id: str, location: str, message: str, data: dict) -> None:
        """NDJSON debug log for session dd836d (no secrets)."""
        try:
            import json, time  # noqa: E401
            payload = {
                "sessionId": "dd836d",
                "runId": "pre-fix",
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data,
                "timestamp": int(time.time() * 1000),
            }
            with open("debug-dd836d.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            pass

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
        # NOTE: _filter_volatile_objects уже гарантирует, что filtered ⊆ raw (или == raw fallback),
        # поэтому "подмешивать" raw нельзя — это снова включит шум.

        (stay_recall_min, stay_precision_min), (switch_recall_min, switch_precision_min) = _thresholds(
            self._cfg
        )

        # region agent log
        self._dbg_dd836d(
            "H4",
            "cv_core/screen_resolver.py:ScreenResolver.update:entry",
            "resolver update entry",
            {
                "raw_count": len(raw),
                "filtered_count": len(filtered),
                "window_size": int(self._cfg.window_size),
                "stable_required": int(self._cfg.stable_required),
                "stable_delay_sec": float(self._cfg.stable_delay_sec),
                "switch_recall_min": float(switch_recall_min),
                "switch_precision_min": float(switch_precision_min),
                "candidate_exists": self._candidate_objects is not None,
                "current_exists": self._current_screen_id is not None,
            },
        )
        # endregion

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
            # region agent log
            self._dbg_dd836d(
                "H4",
                "cv_core/screen_resolver.py:ScreenResolver.update:init_candidate",
                "initialized candidate objects",
                {"candidate_count": len(self._candidate_objects), "stable_flags": list(self._stable_flags)},
            )
            # endregion
            return None

        overlap, old_size, new_size = _overlap_sizes(self._candidate_objects, filtered)
        recall, precision = _recall_precision(overlap, old_size, new_size)
        stable_frame = recall >= switch_recall_min and precision >= switch_precision_min
        self._stable_flags.append(bool(stable_frame))

        # region agent log
        self._dbg_dd836d(
            "H4",
            "cv_core/screen_resolver.py:ScreenResolver.update:stability",
            "stability computed",
            {
                "overlap": int(overlap),
                "old_size": int(old_size),
                "new_size": int(new_size),
                "recall": float(recall),
                "precision": float(precision),
                "stable_frame": bool(stable_frame),
                "stable_flags": list(self._stable_flags),
            },
        )
        # endregion

        # Если новый кадр "расширил" множество (кандидат ⊂ filtered),
        # то precision падает из-за роста new_size, хотя recall остаётся высоким.
        # В этом случае обновляем кандидата до filtered и заново набираем стабильность.
        if (
            not stable_frame
            and recall >= switch_recall_min
            and precision < switch_precision_min
            and self._candidate_objects is not None
            and self._candidate_objects.issubset(filtered)
        ):
            self._candidate_objects = set(filtered)
            self._candidate_since = now
            self._stable_flags.clear()
            self._stable_flags.append(True)
            # region agent log
            self._dbg_dd836d(
                "H4",
                "cv_core/screen_resolver.py:ScreenResolver.update:expand_candidate",
                "expanded candidate to match larger filtered set",
                {"new_candidate_count": len(self._candidate_objects), "old_size": int(old_size), "new_size": int(new_size)},
            )
            # endregion
            return None

        # N-of-M stabilization: don't reset on a single bad frame.
        m = max(1, int(self._cfg.window_size))
        n = max(1, int(self._cfg.stable_required))
        if n > m:
            n = m

        if len(self._stable_flags) == m and sum(1 for x in self._stable_flags if x) < n:
            self._candidate_objects = set(filtered)
            self._candidate_since = now
            self._stable_flags.clear()
            # region agent log
            self._dbg_dd836d(
                "H4",
                "cv_core/screen_resolver.py:ScreenResolver.update:reset_candidate",
                "candidate reset due to insufficient stable frames",
                {"m": m, "n": n},
            )
            # endregion
            return None

        # Множество уже похоже на кандидата достаточно; ждём задержку стабильности
        if self._candidate_since is None:
            self._candidate_since = now
            return None

        if (now - self._candidate_since) < self._cfg.stable_delay_sec:
            # region agent log
            self._dbg_dd836d(
                "H4",
                "cv_core/screen_resolver.py:ScreenResolver.update:delay_wait",
                "waiting stable_delay_sec",
                {"age_sec": float(now - self._candidate_since)},
            )
            # endregion
            return None
        if len(self._stable_flags) < n or sum(1 for x in self._stable_flags if x) < n:
            # region agent log
            self._dbg_dd836d(
                "H4",
                "cv_core/screen_resolver.py:ScreenResolver.update:not_enough_stable",
                "not enough stable frames yet",
                {
                    "stable_len": len(self._stable_flags),
                    "stable_true": sum(1 for x in self._stable_flags if x),
                    "n": n,
                },
            )
            # endregion
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
            # region agent log
            self._dbg_dd836d(
                "H4",
                "cv_core/screen_resolver.py:ScreenResolver.update:resolved_existing",
                "resolved to existing screen",
                {"screen_id": int(best.screen_id), "recall": float(best.recall), "precision": float(best.precision)},
            )
            # endregion
            return best.screen_id

        created = self._repo.create_screen(
            set(filtered),
            monitor_idx=monitor_idx,
            frame_size=frame_size,
        )
        self._current_screen_id = created
        self._current_objects = set(filtered)
        self._current_image_hash = str(image_hash) if image_hash else None
        # region agent log
        self._dbg_dd836d(
            "H4",
            "cv_core/screen_resolver.py:ScreenResolver.update:created_new",
            "created new screen",
            {"screen_id": int(created), "objects_count": len(filtered)},
        )
        # endregion
        return created

