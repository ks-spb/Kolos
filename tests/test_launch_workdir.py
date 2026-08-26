"""Тесты установки рабочей директории при запуске."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from db import KOLOS_DATABASE_PATH
from launch_workdir import ensure_script_directory_is_cwd


class TestEnsureScriptDirectoryIsCwd(unittest.TestCase):
    """Проверка, что cwd совпадает с каталогом скрипта."""

    def test_changes_to_parent_directory_of_script(self) -> None:
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            nested = base / "nested"
            nested.mkdir()
            script = nested / "fake_entry.py"
            script.write_text("#", encoding="utf-8")
            try:
                os.chdir(base)
                ensure_script_directory_is_cwd(script)
                self.assertEqual(Path.cwd(), nested)
            finally:
                # До выхода из TemporaryDirectory: иначе cleanup на Windows падает.
                os.chdir(previous)

    def test_main_sets_workdir_before_importing_keyboard_recorder(self) -> None:
        """Защита от открытия пустой SQLite БД из cwd ярлыка."""
        root = Path(__file__).resolve().parents[1]
        source = (root / "main.py").read_text(encoding="utf-8")

        self.assertLess(
            source.index("ensure_script_directory_is_cwd(__file__)"),
            source.index("from mous_kb_record import rec, play"),
        )

    def test_default_database_has_required_hotkey_table(self) -> None:
        """Используем отслеживаемую project-БД, а не пустую legacy-БД."""
        import sqlite3

        self.assertEqual(KOLOS_DATABASE_PATH.name, "db_v4.db")
        with sqlite3.connect(KOLOS_DATABASE_PATH) as conn:
            table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = ? AND name = ?",
                ("table", "hotkey"),
            ).fetchone()

        self.assertEqual(table, (1,))


if __name__ == "__main__":
    unittest.main()
