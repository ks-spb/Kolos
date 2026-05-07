from __future__ import annotations

import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


class TestScreenDisabledAllowsInput(unittest.TestCase):
    def test_guard_allows_input_without_screen_resolution(self) -> None:
        """
        Регрессия: ввод/обучение должны продолжаться независимо от текущего экрана,
        а guard не должен пытаться резолвить экран или трогать screen.get_screen().
        """
        # Важно: некоторые тесты добавляют `Glaz/` в sys.path, из-за чего `import main`
        # может подтянуть `Glaz/main.py`. Здесь нужен корневой `main.py` проекта.
        root = Path(__file__).resolve().parents[1]
        spec = spec_from_file_location("kolos_root_main", root / "main.py")
        assert spec and spec.loader
        app = module_from_spec(spec)
        spec.loader.exec_module(app)

        app.screen_capture_enabled = True
        app.old_ekran = 0

        def _boom(*_args, **_kwargs):
            raise AssertionError("Экранная логика не должна вызываться при выключенных экранах")

        app.perenos_sostoyaniya = _boom  # type: ignore[assignment]
        app.tekyshiy_ekran = _boom  # type: ignore[assignment]

        ok = app.ensure_current_screen_before_input(context="unit_test")
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()

