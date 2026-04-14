"""Тесты установки рабочей директории при запуске."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
