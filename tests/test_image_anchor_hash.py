from __future__ import annotations

import unittest

from PIL import Image, ImageDraw


class TestImageAnchorHash(unittest.TestCase):
    def test_taskbar_bottom_5_percent_is_ignored(self) -> None:
        from cv_core.image_hash import ImageAnchorConfig, dhash64_hex, hamming_distance_hex64

        w, h = 400, 200
        base = Image.new("RGB", (w, h), (255, 255, 255))

        img1 = base.copy()
        img2 = base.copy()

        # Draw different content only in the bottom 5% (taskbar region).
        y0 = int(h * 0.95)
        d1 = ImageDraw.Draw(img1)
        d2 = ImageDraw.Draw(img2)
        d1.rectangle([0, y0, w, h], fill=(0, 0, 0))
        d2.rectangle([0, y0, w, h], fill=(0, 0, 255))

        cfg = ImageAnchorConfig(taskbar_exclude_ratio=0.05, cursor_mask_size_px=0)
        h1 = dhash64_hex(img1, cfg=cfg, cursor_xy=None)
        h2 = dhash64_hex(img2, cfg=cfg, cursor_xy=None)
        self.assertLessEqual(hamming_distance_hex64(h1, h2), 2)

    def test_cursor_area_mask_reduces_sensitivity(self) -> None:
        from cv_core.image_hash import ImageAnchorConfig, dhash64_hex, hamming_distance_hex64

        w, h = 320, 240
        base = Image.new("RGB", (w, h), (200, 200, 200))
        cursor = (160, 120)

        img1 = base.copy()
        img2 = base.copy()

        # Change a small square around cursor (hover/tooltip-like change).
        d2 = ImageDraw.Draw(img2)
        d2.rectangle([150, 110, 170, 130], fill=(0, 0, 0))

        cfg_nomask = ImageAnchorConfig(taskbar_exclude_ratio=0.05, cursor_mask_size_px=0)
        cfg_mask = ImageAnchorConfig(taskbar_exclude_ratio=0.05, cursor_mask_size_px=120)

        a1 = dhash64_hex(img1, cfg=cfg_nomask, cursor_xy=cursor)
        a2 = dhash64_hex(img2, cfg=cfg_nomask, cursor_xy=cursor)
        b1 = dhash64_hex(img1, cfg=cfg_mask, cursor_xy=cursor)
        b2 = dhash64_hex(img2, cfg=cfg_mask, cursor_xy=cursor)

        self.assertGreaterEqual(hamming_distance_hex64(a1, a2), hamming_distance_hex64(b1, b2))


if __name__ == "__main__":
    unittest.main()

