"""Запуск Kolos (main.py) как подпроцесса: stdout/stderr в UI, stdin из строки ввода."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable, Optional

StreamName = str  # "stdout" | "stderr" | "_exit"


def project_root_from_glaz_file(glaz_module_file: str | Path) -> Path:
    """Корень репозитория Kolos: родитель каталога Glaz."""
    return Path(glaz_module_file).resolve().parent.parent


class KolosSubprocessController:
    """Управляет жизненным циклом ``main.py`` и потоками чтения stdout/stderr."""

    def __init__(
        self,
        project_root: Path,
        on_event: Callable[[StreamName, str], None],
    ) -> None:
        self._project_root = project_root
        self._on_event = on_event
        self._proc: Optional[subprocess.Popen[str]] = None
        self._threads: list[threading.Thread] = []

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self, *, monitor_idx: int | None = None) -> str:
        """Запуск Kolos. Возвращает сообщение об ошибке или пустую строку при успехе."""
        main_py = self._project_root / "main.py"
        if not main_py.is_file():
            return f"Не найден {main_py}"

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        # Иначе на Windows пайп получает cp1251/OEM, а читаем как UTF-8 — «» вместо русского текста.
        env["PYTHONIOENCODING"] = "utf-8"
        if monitor_idx is not None:
            env["KOLOS_MONITOR_IDX"] = str(int(monitor_idx))

        creationflags = 0
        if sys.platform == "win32":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            self._proc = subprocess.Popen(
                [sys.executable, str(main_py)],
                cwd=str(self._project_root),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                creationflags=creationflags,
            )
        except OSError as e:
            return f"Не удалось запустить Kolos: {e}"

        assert self._proc.stdout is not None and self._proc.stderr is not None

        self._threads = [
            threading.Thread(
                target=self._read_stream,
                args=(self._proc.stdout, "stdout"),
                daemon=True,
            ),
            threading.Thread(
                target=self._read_stream,
                args=(self._proc.stderr, "stderr"),
                daemon=True,
            ),
            threading.Thread(target=self._wait_process, daemon=True),
        ]
        for t in self._threads:
            t.start()
        return ""

    def send_line(self, text: str) -> None:
        """Отправить одну строку в stdin Kolos (как ``input()``)."""
        if not self.is_running or self._proc is None or self._proc.stdin is None:
            return
        try:
            self._proc.stdin.write(text if text.endswith("\n") else text + "\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError):
            pass

    def stop(self, timeout_sec: float = 3.0) -> None:
        """Завершить Kolos."""
        if self._proc is None:
            return
        if self._proc.poll() is None:
            try:
                self._proc.terminate()
            except OSError:
                pass
            try:
                self._proc.wait(timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                try:
                    self._proc.kill()
                except OSError:
                    pass
        self._proc = None
        self._threads = []

    def _read_stream(self, stream, name: StreamName) -> None:
        for line in iter(stream.readline, ""):
            self._on_event(name, line.rstrip("\r\n"))
        try:
            stream.close()
        except OSError:
            pass

    def _wait_process(self) -> None:
        if self._proc is None:
            return
        code = self._proc.wait()
        self._on_event("_exit", str(code))
