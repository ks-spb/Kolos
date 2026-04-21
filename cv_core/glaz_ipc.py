"""
Межпроцессный обмен для привязки кликов к объектам Glaz.

Glaz (GUI) пишет "последний подтверждённый объект" в файл, Kolos (CLI/подпроцесс)
читает его с TTL и использует при записи кликов.

Файл хранится в ``~/.glaz/last_target.json`` рядом с ``objects.json``.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Optional


def _glaz_dir() -> str:
    home = os.path.expanduser("~")
    path = os.path.join(home, ".glaz")
    os.makedirs(path, exist_ok=True)
    return path


def last_target_path() -> str:
    """Путь к файлу последнего подтверждённого объекта."""
    return os.path.join(_glaz_dir(), "last_target.json")


@dataclass(frozen=True)
class LastConfirmedTarget:
    refined_id: int
    timestamp: float


def write_last_confirmed_target(refined_id: int, *, timestamp: float | None = None) -> None:
    """
    Записать последний подтверждённый объект.

    Args:
        refined_id: канонический ID объекта (из базы Glaz)
        timestamp: unix-время; если None — берём time.time()
    """
    ts = time.time() if timestamp is None else float(timestamp)
    payload = {"refined_id": int(refined_id), "timestamp": ts}
    try:
        with open(last_target_path(), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    except OSError:
        # IPC — best effort: запись не должна валить основной поток.
        return


def _parse_last_target(raw: Any) -> Optional[LastConfirmedTarget]:
    if not isinstance(raw, dict):
        return None
    refined_id = raw.get("refined_id")
    timestamp = raw.get("timestamp")
    if refined_id is None or timestamp is None:
        return None
    try:
        return LastConfirmedTarget(refined_id=int(refined_id), timestamp=float(timestamp))
    except (TypeError, ValueError):
        return None


def read_last_confirmed_target(*, max_age_sec: float = 2.0, now: float | None = None) -> Optional[LastConfirmedTarget]:
    """
    Прочитать последний подтверждённый объект (если он не протух).

    Args:
        max_age_sec: TTL в секундах
        now: unix-время "сейчас" (для тестов); если None — берём time.time()
    """
    now_ts = time.time() if now is None else float(now)
    try:
        with open(last_target_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    target = _parse_last_target(data)
    if target is None:
        return None
    if max_age_sec < 0:
        return target
    if (now_ts - target.timestamp) > float(max_age_sec):
        return None
    return target

