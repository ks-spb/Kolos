"""Why-trace (человеко-читаемый): что произошло и почему.

Модуль предназначен для минимально-инвазивной трассировки решений в рантайме.
Трассировка выводится в stdout и включается переменными окружения.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Mapping


def _env_flag(name: str, default: str = "0") -> bool:
    v = os.environ.get(name, default).strip().lower()
    return v in ("1", "true", "yes", "y", "on")


def _now_hms() -> str:
    t = time.localtime()
    return f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}"


def _safe_value(v: Any) -> str:
    if v is None:
        return "None"
    if isinstance(v, (int, float, bool)):
        return str(v)
    s = str(v)
    s = s.replace("\n", "\\n").replace("\r", "\\r")
    if len(s) > 160:
        s = s[:157] + "..."
    return s


def _format_kv(data: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for k in sorted(data.keys()):
        parts.append(f"{k}={_safe_value(data[k])}")
    return " ".join(parts)


@dataclass(slots=True)
class WhyTracer:
    """Печатает why-trace строки в stdout при включённом флаге."""

    enabled: bool
    level: int = 1
    prefix: str = "[WHY]"
    _seq: int = 0

    @classmethod
    def from_env(cls) -> "WhyTracer":
        enabled = _env_flag("KOLOS_TRACE_WHY", "0")
        try:
            level = int(os.environ.get("KOLOS_TRACE_WHY_LEVEL", "1").strip() or "1")
        except ValueError:
            level = 1
        level = max(0, min(5, level))
        return cls(enabled=enabled, level=level)

    def next_trace_id(self) -> str:
        self._seq += 1
        return f"t{self._seq:06d}"

    def trace(self, *, trace_id: str, event: str, why: str, data: Mapping[str, Any] | None = None, lvl: int = 1) -> None:
        """Записать строку трассировки.

        Args:
            trace_id: ID одной «цепочки» (обычно один пользовательский ввод).
            event: Короткое имя события (INPUT_READ, PROSHIVKA_PICK, ...).
            why: Человеко-читаемое «почему».
            data: Доп. факты (ключевые переменные), коротко.
            lvl: Уровень детализации (1..5). Печатается, если lvl <= self.level.
        """
        if not self.enabled or lvl > self.level:
            return
        payload = {"event": event, "why": why}
        if data:
            payload.update(dict(data))
        kv = _format_kv(payload)
        print(f"{self.prefix} { _now_hms() } trace_id={trace_id} {kv}")

