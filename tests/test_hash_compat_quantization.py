from __future__ import annotations

import unittest


class TestHashCompatQuantization(unittest.TestCase):
    def test_object_hash_is_stable_under_small_bbox_jitter(self) -> None:
        from cv_core.hash_compat import object_hash_for_bbox_signature

        # Simulate the shape of signature produced by DetectionService:
        # (left, top, right, bottom, cx, cy) — all ints.
        bbox1 = (100, 200, 160, 260)
        sig1 = (100, 200, 160, 260, 130, 230)

        # Small jitter (+/-2 px) should not change object hash after quantization.
        bbox2 = (102, 199, 162, 261)
        sig2 = (102, 199, 162, 261, 131, 231)

        h1 = object_hash_for_bbox_signature(bbox1, sig1)
        h2 = object_hash_for_bbox_signature(bbox2, sig2)
        self.assertEqual(h1, h2)


if __name__ == "__main__":
    unittest.main()

