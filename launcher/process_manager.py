"""Process control service for Kolos/Glaz launcher."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from .models import ManagedProcess, ProcessSpec


class ProcessManager:
    """Starts and stops Kolos/Glaz in separate console windows."""

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root
        self._kolos = ManagedProcess(ProcessSpec("Kolos", project_root / "main.py"))
        self._glaz = ManagedProcess(ProcessSpec("Glaz", project_root / "Glaz" / "main.py"))

    def start_kolos(self) -> str:
        """Start Kolos if not already running."""
        return self._start(self._kolos)

    def start_glaz(self) -> str:
        """Start Glaz if not already running."""
        return self._start(self._glaz)

    def stop_all(self) -> str:
        """Stop both managed processes."""
        parts = [self._stop(self._kolos), self._stop(self._glaz)]
        return " | ".join(parts)

    def stop_all_on_exit(self) -> None:
        """Silent stop for window close hook."""
        self._stop(self._kolos)
        self._stop(self._glaz)

    def status_text(self) -> str:
        """Short status line for UI."""
        return f"Kolos: {self._state(self._kolos)} | Glaz: {self._state(self._glaz)}"

    def _state(self, proc: ManagedProcess) -> str:
        return "запущен" if proc.is_running() else "остановлен"

    def _start(self, managed: ManagedProcess) -> str:
        if managed.is_running():
            return f"{managed.spec.name} уже запущен."
        if not managed.spec.script_path.exists():
            return f"Файл не найден: {managed.spec.script_path}"

        creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        managed.process = subprocess.Popen(
            [sys.executable, str(managed.spec.script_path)],
            cwd=str(self._project_root),
            creationflags=creationflags,
        )
        return f"{managed.spec.name} запущен."

    def _stop(self, managed: ManagedProcess) -> str:
        if not managed.is_running():
            return f"{managed.spec.name} уже остановлен."
        assert managed.process is not None
        managed.process.terminate()
        if self._wait_for_exit(managed.process, timeout_sec=2.0):
            managed.process = None
            return f"{managed.spec.name} остановлен."
        managed.process.kill()
        self._wait_for_exit(managed.process, timeout_sec=1.0)
        managed.process = None
        return f"{managed.spec.name} принудительно остановлен."

    @staticmethod
    def _wait_for_exit(process: subprocess.Popen, timeout_sec: float) -> bool:
        """Wait for process completion with timeout polling."""
        end = time.time() + timeout_sec
        while time.time() < end:
            if process.poll() is not None:
                return True
            time.sleep(0.05)
        return process.poll() is not None

