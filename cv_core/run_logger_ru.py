"""Русский рантайм-логгер Колоса (человекочитаемый + опционально NDJSON).

Цель: дать понятный "почему-лог" во время работы программы:
- какое текущее состояние (точка с max signal),
- почему создалась связь,
- какие точки участвуют (id/name/type/signal),
- что пришло на вход (ввод/запись/прошивка/исполнение).

Лог рассчитан на просмотр "вживую" (PowerShell):
    Get-Content .\\logi_dly_otvetov.txt -Wait

Принципы:
- Никаких исключений наружу: логирование не должно ломать основной цикл.
- Файл открывается на запись на каждую строку (минимизируем блокировки).
- Текст — по-русски, коротко и структурировано.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping, Protocol


class _DbLike(Protocol):
    """Минимальный протокол курсора БД (sqlite wrapper в проекте)."""

    def execute(self, query: str, values: Any | None = None):  # pragma: no cover
        ...


def _env_flag(name: str, default: str = "1") -> bool:
    v = os.environ.get(name, default).strip().lower()
    return v in ("1", "true", "yes", "y", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)).strip() or str(default))
    except Exception:
        return default


def _ts_ms() -> int:
    return int(time.time() * 1000)


def _hms() -> str:
    t = time.localtime()
    return f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}"


def _safe_short(v: Any, *, limit: int = 240) -> str:
    if v is None:
        return "None"
    if isinstance(v, (int, float, bool)):
        return str(v)
    s = str(v).replace("\n", "\\n").replace("\r", "\\r")
    if len(s) > limit:
        return s[: limit - 3] + "..."
    return s


def _fmt_point(p: Mapping[str, Any] | None) -> str:
    if not p:
        return "нет"
    return (
        f"id={p.get('id')} name={_safe_short(p.get('name'))} "
        f"type={p.get('type')} signal={p.get('signal')}"
    )


def get_point_by_id(db: _DbLike, point_id: int | str | None) -> dict[str, Any] | None:
    """Получить точку по id в удобном виде для логов."""
    if point_id is None:
        return None
    try:
        row = db.execute("SELECT id, name, type, signal FROM points WHERE id = ?", (point_id,)).fetchone()
        if not row:
            return None
        return {"id": row[0], "name": row[1], "type": row[2], "signal": row[3]}
    except Exception:
        return None


def get_max_signal_point(db: _DbLike) -> dict[str, Any] | None:
    """Получить точку с максимальным signal (текущее состояние)."""
    try:
        row = db.execute(
            "SELECT id, name, type, signal FROM points ORDER BY signal DESC, id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        return {"id": row[0], "name": row[1], "type": row[2], "signal": row[3]}
    except Exception:
        return None


@dataclass(slots=True)
class RunLoggerRU:
    """Рантайм-логгер: человекочитаемый + опционально NDJSON."""

    text_path: str = "logi_dly_otvetov.txt"
    ndjson_path: str = "kolos-ru.ndjson"
    enabled: bool = True
    ndjson_enabled: bool = False
    level: int = 1

    @classmethod
    def from_env(cls) -> "RunLoggerRU":
        text_path = os.environ.get("KOLOS_RU_LOG_TEXT_PATH", "logi_dly_otvetov.txt").strip() or "logi_dly_otvetov.txt"
        ndjson_path = os.environ.get("KOLOS_RU_LOG_NDJSON_PATH", "kolos-ru.ndjson").strip() or "kolos-ru.ndjson"
        enabled = _env_flag("KOLOS_RU_LOG", "1")
        ndjson_enabled = _env_flag("KOLOS_RU_LOG_NDJSON", "0")
        level = max(0, min(3, _env_int("KOLOS_RU_LOG_LEVEL", 1)))
        return cls(
            text_path=text_path,
            ndjson_path=ndjson_path,
            enabled=enabled,
            ndjson_enabled=ndjson_enabled,
            level=level,
        )

    def log(
        self,
        *,
        event: str,
        message: str,
        data: Mapping[str, Any] | None = None,
        db: _DbLike | None = None,
        state_before: Mapping[str, Any] | None = None,
        state_after: Mapping[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> None:
        if not self.enabled:
            return
        try:
            self._write_text(
                event=event,
                message=message,
                data=data,
                db=db,
                state_before=state_before,
                state_after=state_after,
                trace_id=trace_id,
            )
        except Exception:
            # Логи не должны ломать рантайм.
            pass
        if not self.ndjson_enabled:
            return
        try:
            self._write_ndjson(
                event=event,
                message=message,
                data=data,
                state_before=state_before,
                state_after=state_after,
                trace_id=trace_id,
            )
        except Exception:
            pass

    def _write_text(
        self,
        *,
        event: str,
        message: str,
        data: Mapping[str, Any] | None,
        db: _DbLike | None,
        state_before: Mapping[str, Any] | None,
        state_after: Mapping[str, Any] | None,
        trace_id: str | None,
    ) -> None:
        now = _hms()
        parts: list[str] = [f"[{now}] {event}: {message}"]
        if trace_id:
            parts.append(f"  trace_id: {trace_id}")
        if db is not None and (state_before is None and state_after is None):
            # Если снимки не передали — берём текущее состояние как справку.
            cur = get_max_signal_point(db)
            parts.append(f"  состояние сейчас (max signal): {_fmt_point(cur)}")
        if state_before is not None:
            parts.append(f"  состояние ДО: {_fmt_point(state_before)}")
        if state_after is not None:
            parts.append(f"  состояние ПОСЛЕ: {_fmt_point(state_after)}")
        if data and self.level >= 1:
            parts.append("  данные: " + self._fmt_data(data))
        line = "\n".join(parts) + "\n"
        with open(self.text_path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()

    def _write_ndjson(
        self,
        *,
        event: str,
        message: str,
        data: Mapping[str, Any] | None,
        state_before: Mapping[str, Any] | None,
        state_after: Mapping[str, Any] | None,
        trace_id: str | None,
    ) -> None:
        payload: MutableMapping[str, Any] = {
            "ts_ms": _ts_ms(),
            "event": event,
            "сообщение": message,
        }
        if trace_id:
            payload["trace_id"] = trace_id
        if state_before is not None:
            payload["состояние_до"] = dict(state_before)
        if state_after is not None:
            payload["состояние_после"] = dict(state_after)
        if data:
            payload["данные"] = dict(data)
        with open(self.ndjson_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            f.flush()

    def _fmt_data(self, data: Mapping[str, Any]) -> str:
        # Плоский формат, пригодный для глаз.
        chunks: list[str] = []
        for k in sorted(data.keys()):
            chunks.append(f"{k}={_safe_short(data[k])}")
        return ", ".join(chunks)

