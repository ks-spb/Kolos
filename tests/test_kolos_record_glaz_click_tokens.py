from __future__ import annotations

import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


class TestKolosRecordGlazClickTokens(unittest.TestCase):
    @staticmethod
    def _load_main_module():
        root = Path(__file__).resolve().parents[1]
        spec = spec_from_file_location("kolos_root_main_record_tokens", root / "main.py")
        assert spec and spec.loader
        app = module_from_spec(spec)
        spec.loader.exec_module(app)
        return app

    def test_glaz_click_record_becomes_position_object_then_click_tokens(self) -> None:
        app = self._load_main_module()

        event = {
            "type": "mouse",
            "event": "click",
            "x": 500,
            "y": 300,
            "refined_id": 42,
            "target_name": "glaz.42",
        }

        self.assertEqual(app._record_event_to_tokens(event), ["position.500.300", "glaz.42", "click"])

    def test_legacy_image_click_record_keeps_compatibility_tokens(self) -> None:
        app = self._load_main_module()

        event = {
            "type": "mouse",
            "event": "click",
            "x": 500,
            "y": 300,
            "image": "abcdef1234567890",
        }

        self.assertEqual(
            app._record_event_to_tokens(event),
            ["position.500.300", "abcdef1234567890.click"],
        )

    def test_unresolved_click_record_uses_position_then_plain_click(self) -> None:
        app = self._load_main_module()

        event = {
            "type": "mouse",
            "event": "click",
            "x": 500,
            "y": 300,
            "target_name": None,
        }

        self.assertEqual(app._record_event_to_tokens(event), ["position.500.300", "click"])


if __name__ == "__main__":
    unittest.main()
