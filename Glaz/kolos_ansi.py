"""Обработка ANSI SGR в выводе Kolos: снятие кодов и определение красного текста (код 31)."""

from __future__ import annotations

import re

# Стандартные SGR последовательности вида ESC [ ... m
_SGR = re.compile(r"\x1b\[[0-9;]*m")
# Строка задаётся как красная (foreground 31), в т.ч. 1;31, 0;31
_RED_SGR = re.compile(r"\x1b\[[^m]*31m")


def strip_sgr(text: str) -> str:
    """Удалить escape-последовательности из текста (для отображения в Tk)."""
    return _SGR.sub("", text)


def line_looks_red_in_terminal(text: str) -> bool:
    """True, если в строке был SGR с цветом 31 (красный), как в print(..., 31m)."""
    return bool(_RED_SGR.search(text))
