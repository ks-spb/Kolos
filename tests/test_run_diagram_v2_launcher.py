"""Tests for the Diagram v2 double-click launcher."""

from __future__ import annotations

from pathlib import Path


def test_diagram_v2_launcher_uses_script_directory() -> None:
    """The launcher should work from Explorer, shortcuts, and arbitrary cwd."""
    text = Path("run_diagram_v2.bat").read_text(encoding="utf-8")

    assert 'cd /d "%~dp0"' in text
    assert '"%~dp0Diagram_new.py"' in text


def test_diagram_v2_launcher_prefers_local_venv() -> None:
    """Prefer project venv because Diagram_new.py depends on installed packages."""
    text = Path("run_diagram_v2.bat").read_text(encoding="utf-8")

    assert r".venv\Scripts\python.exe" in text
    assert 'py -3 "%~dp0Diagram_new.py"' in text
