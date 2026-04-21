#!/usr/bin/env python3
"""
Glaz - Программа для захвата и анализа экрана
Точка входа в приложение
"""

import sys
from pathlib import Path

import tkinter as tk

# Запуск из папки Glaz не видит соседний пакет cv_core.
# Добавляем корень репозитория в sys.path до импортов приложения.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app import ScreenCaptureApp


def main():
    """Запуск приложения."""
    root = tk.Tk()
    ScreenCaptureApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
