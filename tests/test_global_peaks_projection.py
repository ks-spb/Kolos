from __future__ import annotations

import os
import unittest
from unittest import mock

from PIL import Image

from cv_core.detection_service import DetectionService
from cv_core.global_peaks_scale import uniform_preview_size, read_global_peaks_scale_from_env
from cv_core.peaks_coordinate_map import ltrb_preview_to_full


class TestGlobalPeaksProjection(unittest.TestCase):
    def test_uniform_preview_preserves_aspect_single_scale(self) -> None:
        w, h, s = uniform_preview_size(1920, 1080, 0.5)
        self.assertEqual((w, h), (960, 540))
        self.assertAlmostEqual(s, 0.5, places=6)

    def test_ltrb_preview_to_full_floor_ceil(self) -> None:
        l, t, r, b = ltrb_preview_to_full(10, 20, 30, 40, inv_scale=2.0)
        self.assertEqual((l, t, r, b), (20, 40, 60, 80))

    def test_detection_service_scales_peaks_and_maps_records_to_full(self) -> None:
        # White image with a thick black vertical bar; stable for line detector.
        img = Image.new("RGB", (200, 100), (255, 255, 255))
        for x in range(40, 45):
            for y in range(0, 100):
                img.putpixel((x, y), (0, 0, 0))

        with mock.patch.dict(os.environ, {"KOLOS_GLOBAL_PEAKS_SCALE": "0.5"}, clear=False):
            svc = DetectionService()
            self.assertEqual(read_global_peaks_scale_from_env(), 0.5)

            peaks, records = svc.process(img, threshold=30, invert=False, min_line_length=3)

        self.assertEqual(peaks.size, (100, 50))
        self.assertGreater(len(records), 0)
        r0 = records[0]
        l, t, r, b = r0.bbox_ltrb
        self.assertGreaterEqual(l, 0)
        self.assertGreaterEqual(t, 0)
        self.assertLessEqual(r, 200)
        self.assertLessEqual(b, 100)


if __name__ == "__main__":
    unittest.main()
