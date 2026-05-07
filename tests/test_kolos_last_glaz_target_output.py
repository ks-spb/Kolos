from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace


class TestKolosLastGlazTargetOutput(unittest.TestCase):
    """Регрессионные тесты вывода последнего объекта Glaz в out_red."""

    @staticmethod
    def _root() -> Path:
        return Path(__file__).resolve().parents[1]

    @classmethod
    def _load_main_module(cls):
        spec = spec_from_file_location("kolos_root_main_last_glaz_target", cls._root() / "main.py")
        assert spec and spec.loader
        app = module_from_spec(spec)
        spec.loader.exec_module(app)
        return app

    def test_print_last_glaz_target_outputs_confirmed_target(self) -> None:
        app = self._load_main_module()
        app.read_last_confirmed_target = lambda *, max_age_sec: SimpleNamespace(
            refined_id=42,
            center_xy=(10, 20),
            bbox_ltrb=(1, 2, 30, 40),
        )

        out = io.StringIO()
        with redirect_stdout(out):
            target = app._print_last_glaz_target(max_age_sec=10.0)

        self.assertEqual(target.refined_id, 42)
        self.assertIn(
            "Последний объект Glaz: refined_id=42, center=(10, 20), bbox=(1, 2, 30, 40)",
            out.getvalue(),
        )

    def test_print_last_glaz_target_outputs_absence_when_missing(self) -> None:
        app = self._load_main_module()
        app.read_last_confirmed_target = lambda *, max_age_sec: None

        out = io.StringIO()
        with redirect_stdout(out):
            target = app._print_last_glaz_target(max_age_sec=10.0)

        self.assertIsNone(target)
        self.assertIn("Последний объект Glaz: нет актуального подтверждённого объекта", out.getvalue())

    def test_print_last_glaz_target_is_best_effort(self) -> None:
        app = self._load_main_module()

        def _raise(*, max_age_sec):
            raise OSError("broken ipc")

        app.read_last_confirmed_target = _raise

        out = io.StringIO()
        with redirect_stdout(out):
            target = app._print_last_glaz_target(max_age_sec=10.0)

        self.assertIsNone(target)
        self.assertIn("Последний объект Glaz: нет актуального подтверждённого объекта", out.getvalue())

    def test_out_red_image_branch_uses_glaz_last_target_not_cursor_probe(self) -> None:
        text = (self._root() / "main.py").read_text(encoding="utf-8", errors="replace")
        start = text.index("def out_red")
        end = text.index("def poisk_id_s_max_signal_points", start)
        body = text[start:end]

        self.assertIn("_print_last_glaz_target(max_age_sec=10.0)", body)
        self.assertNotIn("screen.element_under_cursor()", body)
        self.assertNotIn("Объект под курсором мыши:", body)
        self.assertNotIn("Объект под курсором:", body)


if __name__ == "__main__":
    unittest.main()
