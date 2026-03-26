"""Launcher entrypoint for Kolos and Glaz."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

from launcher.ui import LauncherApp


def main() -> None:
    """Run launcher window."""
    root = tk.Tk()
    LauncherApp(root, Path(__file__).resolve().parent)
    root.mainloop()


if __name__ == "__main__":
    main()

