#!/usr/bin/env python3
"""
Glaz - Программа для захвата и анализа экрана
Точка входа в приложение
"""

import tkinter as tk
from app import ScreenCaptureApp


def main():
    """Запуск приложения."""
    root = tk.Tk()
    ScreenCaptureApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
