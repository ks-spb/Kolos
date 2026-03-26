"""Tkinter UI for Kolos launcher."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from .process_manager import ProcessManager


class LauncherApp:
    """Simple dialog launcher for Kolos and Glaz."""

    def __init__(self, root: tk.Tk, project_root: Path) -> None:
        self._root = root
        self._manager = ProcessManager(project_root)
        self._status_var = tk.StringVar(value="Готово к запуску.")

        self._setup_window()
        self._build_layout()
        self._refresh_status()

    def _setup_window(self) -> None:
        self._root.title("Kolos Launcher")
        self._root.geometry("480x190")
        self._root.resizable(False, False)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self) -> None:
        frame = ttk.Frame(self._root, padding=14)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Запуск Колос/Glaz", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(frame, text="Все процессы запускаются в отдельных консолях Windows.").pack(anchor=tk.W, pady=(2, 10))

        button_row = ttk.Frame(frame)
        button_row.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(button_row, text="Запустить Колос", command=self._on_start_kolos).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Запустить Glaz", command=self._on_start_glaz).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(button_row, text="Остановить", command=self._on_stop_all).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(frame, text="Статус:").pack(anchor=tk.W)
        ttk.Label(frame, textvariable=self._status_var, wraplength=440).pack(anchor=tk.W, pady=(2, 6))

    def _on_start_kolos(self) -> None:
        self._set_status(self._manager.start_kolos())

    def _on_start_glaz(self) -> None:
        self._set_status(self._manager.start_glaz())

    def _on_stop_all(self) -> None:
        self._set_status(self._manager.stop_all())

    def _set_status(self, message: str) -> None:
        text = f"{message} | {self._manager.status_text()}"
        self._status_var.set(text)

    def _refresh_status(self) -> None:
        self._status_var.set(self._manager.status_text())
        self._root.after(1000, self._refresh_status)

    def _on_close(self) -> None:
        self._manager.stop_all_on_exit()
        self._root.destroy()

