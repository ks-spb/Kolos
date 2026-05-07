from __future__ import annotations

import unittest

from cv_core.glaz_geometry_cache import geometry_hash_from_bboxes, quantize_bbox_ltrb


class TestGlazGeometryCache(unittest.TestCase):
    def test_hash_is_order_independent(self) -> None:
        first = geometry_hash_from_bboxes([(10, 20, 50, 60), (100, 120, 150, 160)])
        second = geometry_hash_from_bboxes([(100, 120, 150, 160), (10, 20, 50, 60)])

        self.assertEqual(first, second)

    def test_hash_ignores_small_jitter_with_quantization(self) -> None:
        first = geometry_hash_from_bboxes([(10, 20, 50, 60)], step=8)
        second = geometry_hash_from_bboxes([(11, 21, 49, 61)], step=8)

        self.assertEqual(first, second)

    def test_hash_changes_for_significant_geometry_change(self) -> None:
        first = geometry_hash_from_bboxes([(10, 20, 50, 60)], step=8)
        second = geometry_hash_from_bboxes([(40, 80, 120, 180)], step=8)

        self.assertNotEqual(first, second)

    def test_quantize_rejects_invalid_bbox(self) -> None:
        self.assertIsNone(quantize_bbox_ltrb((1, 2, 3), step=8))


if __name__ == "__main__":
    unittest.main()
