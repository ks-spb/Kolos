"""Тесты вспомогательных функций встроенного Kolos в Glaz."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Glaz"))

from kolos_subprocess import project_root_from_glaz_file  # noqa: E402


class TestKolosUtf8Env(unittest.TestCase):
    """Kolos-подпроцесс должен писать в пайп в UTF-8 (иначе кракозябры в Tk)."""

    def test_subprocess_module_sets_pythonioencoding(self) -> None:
        src = (ROOT / "Glaz" / "kolos_subprocess.py").read_text(encoding="utf-8")
        self.assertIn("PYTHONIOENCODING", src)
        self.assertIn("utf-8", src.split("PYTHONIOENCODING", 1)[1][:80].lower())


class TestProjectRootFromGlaz(unittest.TestCase):
    """Корень репозитория из пути к Glaz/app.py."""

    def test_points_to_repo_with_main_py(self) -> None:
        glaz_app = ROOT / "Glaz" / "app.py"
        r = project_root_from_glaz_file(glaz_app)
        self.assertEqual(r.resolve(), ROOT.resolve())
        self.assertTrue((r / "main.py").is_file())


class TestRunMainBat(unittest.TestCase):
    """run_main: только Glaz; Kolos поднимается из окна Glaz."""

    def test_starts_glaz_only(self) -> None:
        text = (ROOT / "run_main.bat").read_text(encoding="utf-8", errors="replace")
        low = text.replace("\r\n", "\n").lower()
        self.assertIn("glaz", low)
        self.assertRegex(low, r"py\s+-3.*glaz.*main\.py")
        # не запускать корневой main.py второй строкой из bat
        self.assertNotIn("py -3 main.py", low)
        self.assertNotIn("py-3 main.py", low.replace(" ", ""))


if __name__ == "__main__":
    unittest.main()
