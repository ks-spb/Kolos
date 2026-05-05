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

try:
    import uuid as _uuid
except Exception:  # pragma: no cover
    _uuid = None  # type: ignore[assignment]


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
    center_xy: tuple[int, int] | None = None
    bbox_ltrb: tuple[int, int, int, int] | None = None


def write_last_confirmed_target(
    refined_id: int,
    *,
    timestamp: float | None = None,
    center_xy: tuple[int, int] | None = None,
    bbox_ltrb: tuple[int, int, int, int] | None = None,
) -> None:
    """
    Записать последний подтверждённый объект.

    Args:
        refined_id: канонический ID объекта (из базы Glaz)
        timestamp: unix-время; если None — берём time.time()
    """
    ts = time.time() if timestamp is None else float(timestamp)
    payload: dict[str, Any] = {"refined_id": int(refined_id), "timestamp": ts}
    if center_xy is not None:
        payload["center_xy"] = [int(center_xy[0]), int(center_xy[1])]
    if bbox_ltrb is not None:
        l, t, r, b = bbox_ltrb
        payload["bbox_ltrb"] = [int(l), int(t), int(r), int(b)]
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
    center_xy_raw = raw.get("center_xy")
    bbox_raw = raw.get("bbox_ltrb")
    try:
        center_xy: tuple[int, int] | None = None
        if isinstance(center_xy_raw, (list, tuple)) and len(center_xy_raw) == 2:
            center_xy = (int(center_xy_raw[0]), int(center_xy_raw[1]))
        bbox_ltrb: tuple[int, int, int, int] | None = None
        if isinstance(bbox_raw, (list, tuple)) and len(bbox_raw) == 4:
            bbox_ltrb = (int(bbox_raw[0]), int(bbox_raw[1]), int(bbox_raw[2]), int(bbox_raw[3]))
        return LastConfirmedTarget(
            refined_id=int(refined_id),
            timestamp=float(timestamp),
            center_xy=center_xy,
            bbox_ltrb=bbox_ltrb,
        )
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
        path = last_target_path()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    target = _parse_last_target(data)
    if target is None:
        return None
    if max_age_sec < 0:
        return target
    age_sec = float(now_ts - target.timestamp)
    # Небольшой запас на джиттер таймера/планировщика: иначе легко получить age_sec чуть > max_age_sec
    # при реальном сценарии "подтвердил → кликнул" (см. debug-83a292.log: 2.0227s vs 2.0s).
    effective_max = float(max_age_sec) + 0.35
    if age_sec > effective_max:
        return None
    return target


def scan_request_path() -> str:
    """Путь к IPC-файлу запроса предскана объектов."""
    return os.path.join(_glaz_dir(), "scan_request.json")


@dataclass(frozen=True)
class ScanRequest:
    request_id: str
    timestamp: float
    reason: str


def _new_request_id() -> str:
    """Сгенерировать request_id без новых зависимостей."""
    try:
        if _uuid is not None:
            return str(_uuid.uuid4())
    except Exception:
        pass
    # Fallback: достаточно уникально для IPC-сценария.
    return f"req_{int(time.time() * 1000)}"


def write_scan_request(
    *,
    reason: str,
    timestamp: float | None = None,
    request_id: str | None = None,
) -> str | None:
    """
    Записать запрос на предскан объектов (Kolos -> Glaz).

    Returns:
        request_id, если запись удалась (best-effort), иначе None.
    """
    ts = time.time() if timestamp is None else float(timestamp)
    rid = str(request_id) if request_id is not None else _new_request_id()
    payload: dict[str, Any] = {"request_id": rid, "timestamp": ts, "reason": str(reason)}
    try:
        with open(scan_request_path(), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        return rid
    except OSError:
        return None


def _parse_scan_request(raw: Any) -> Optional[ScanRequest]:
    if not isinstance(raw, dict):
        return None
    request_id = raw.get("request_id")
    timestamp = raw.get("timestamp")
    reason = raw.get("reason")
    if request_id is None or timestamp is None or reason is None:
        return None
    try:
        return ScanRequest(
            request_id=str(request_id),
            timestamp=float(timestamp),
            reason=str(reason),
        )
    except (TypeError, ValueError):
        return None


def read_scan_request(*, max_age_sec: float = 10.0, now: float | None = None) -> Optional[ScanRequest]:
    """Прочитать запрос предскана (если не протух)."""
    now_ts = time.time() if now is None else float(now)
    try:
        with open(scan_request_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    req = _parse_scan_request(data)
    if req is None:
        return None
    if max_age_sec < 0:
        return req
    age_sec = float(now_ts - req.timestamp)
    effective_max = float(max_age_sec) + 0.35
    if age_sec > effective_max:
        return None
    return req


def scan_results_path() -> str:
    """Путь к IPC-файлу результатов предскана (Glaz -> Kolos)."""
    return os.path.join(_glaz_dir(), "scan_results.json")


@dataclass(frozen=True)
class ScanResultItem:
    refined_id: int
    count: int
    is_new: bool


@dataclass(frozen=True)
class ScanResults:
    request_id: str
    timestamp: float
    items: tuple[ScanResultItem, ...]


def write_scan_results(
    results: ScanResults,
    *,
    timestamp: float | None = None,
) -> None:
    """Записать результаты предскана (best-effort)."""
    ts = time.time() if timestamp is None else float(timestamp)
    payload: dict[str, Any] = {
        "request_id": str(results.request_id),
        "timestamp": ts,
        "items": [
            {"refined_id": int(it.refined_id), "count": int(it.count), "is_new": bool(it.is_new)}
            for it in results.items
        ],
    }
    try:
        with open(scan_results_path(), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    except OSError:
        return


def _parse_scan_results(raw: Any) -> Optional[ScanResults]:
    if not isinstance(raw, dict):
        return None
    request_id = raw.get("request_id")
    timestamp = raw.get("timestamp")
    items_raw = raw.get("items")
    if request_id is None or timestamp is None or not isinstance(items_raw, list):
        return None
    items: list[ScanResultItem] = []
    try:
        for it in items_raw:
            if not isinstance(it, dict):
                continue
            rid = it.get("refined_id")
            cnt = it.get("count")
            is_new = it.get("is_new")
            if rid is None or cnt is None or is_new is None:
                continue
            items.append(ScanResultItem(refined_id=int(rid), count=int(cnt), is_new=bool(is_new)))
        return ScanResults(
            request_id=str(request_id),
            timestamp=float(timestamp),
            items=tuple(items),
        )
    except (TypeError, ValueError):
        return None


def read_scan_results(*, max_age_sec: float = 10.0, now: float | None = None) -> Optional[ScanResults]:
    """Прочитать результаты предскана (если не протухли)."""
    now_ts = time.time() if now is None else float(now)
    try:
        with open(scan_results_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    res = _parse_scan_results(data)
    if res is None:
        return None
    if max_age_sec < 0:
        return res
    age_sec = float(now_ts - res.timestamp)
    effective_max = float(max_age_sec) + 0.35
    if age_sec > effective_max:
        return None
    return res

