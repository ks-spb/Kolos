"""Установка рабочей директории при запуске из проводника или ярлыка."""

from __future__ import annotations

import os
from pathlib import Path


def ensure_script_directory_is_cwd(script_file: str | Path) -> None:
    """Устанавливает текущую рабочую папку в каталог, где лежит указанный скрипт.

    При двойном щелчке по ``.py`` в Windows ``cwd`` часто не совпадает с корнем
    проекта, из‑за чего ломаются относительные пути к SQLite и прочим файлам.
    """
    os.chdir(Path(script_file).resolve().parent)
