from __future__ import annotations

import unittest


class TestMouseKbPlayClickPrefersGlazCenter(unittest.TestCase):
    def test_play_one_click_uses_glaz_center_xy_first(self) -> None:
        import mous_kb_record as mkr

        calls: list[tuple[int, int]] = []

        # patch pyautogui.click
        orig_click = mkr.pyautogui.click
        mkr.pyautogui.click = lambda x=None, y=None, *a, **k: calls.append((int(x), int(y)))  # type: ignore[assignment]

        # patch legacy path to ensure it would fail if reached
        orig_get_hash_element = mkr.screen.get_hash_element
        mkr.screen.get_hash_element = lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("legacy path used"))  # type: ignore[assignment]

        try:
            p = mkr.Play()
            action = {
                "type": "mouse",
                "event": "click",
                "refined_id": 7,
                "glaz_center_xy": (123, 456),
                "image": "hash_should_not_be_used",
            }
            p.play_one(action)
            self.assertEqual(calls, [(123, 456)])
        finally:
            mkr.pyautogui.click = orig_click  # type: ignore[assignment]
            mkr.screen.get_hash_element = orig_get_hash_element  # type: ignore[assignment]


if __name__ == "__main__":
    unittest.main()

