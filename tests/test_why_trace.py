import os
import unittest

from cv_core.why_trace import WhyTracer


class TestWhyTrace(unittest.TestCase):
    def test_from_env_disabled_by_default(self) -> None:
        os.environ.pop("KOLOS_TRACE_WHY", None)
        t = WhyTracer.from_env()
        self.assertFalse(t.enabled)

    def test_from_env_enabled(self) -> None:
        os.environ["KOLOS_TRACE_WHY"] = "1"
        t = WhyTracer.from_env()
        self.assertTrue(t.enabled)

    def test_trace_id_increments(self) -> None:
        t = WhyTracer(enabled=True)
        a = t.next_trace_id()
        b = t.next_trace_id()
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith("t"))
        self.assertTrue(b.startswith("t"))

