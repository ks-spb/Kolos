from __future__ import annotations

import sqlite3
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


class TestKolosGoldenPath(unittest.TestCase):
    @staticmethod
    def _load_main_module():
        root = Path(__file__).resolve().parents[1]
        spec = spec_from_file_location("kolos_root_main_golden_path", root / "main.py")
        assert spec and spec.loader
        app = module_from_spec(spec)
        spec.loader.exec_module(app)
        return app

    @staticmethod
    def _db() -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE points (id INTEGER PRIMARY KEY, name TEXT, type TEXT, signal INTEGER)")
        conn.execute("CREATE TABLE svyazi (ID INTEGER PRIMARY KEY, id_start INTEGER, id_finish INTEGER)")
        conn.executemany(
            "INSERT INTO points (id, name, type, signal) VALUES (?, ?, ?, ?)",
            [
                (1, "poz", "REAC", 0),
                (2, "neg", "REAC", 0),
                (3, "ney", "REAC", 0),
                (10, "o1", "in", 10),
                (20, "position.10.20", "in", 0),
                (21, "glaz.42", "in", 0),
                (22, "click", "in", 0),
                (50, "position.50.60", "in", 0),
            ],
        )
        return conn

    def test_find_golden_path_reaches_positive_reaction(self) -> None:
        app = self._load_main_module()
        conn = self._db()
        conn.executemany(
            "INSERT INTO svyazi (ID, id_start, id_finish) VALUES (?, ?, ?)",
            [
                (30, 10, 20),
                (31, 20, 21),
                (32, 21, 22),
                (33, 22, 1),
            ],
        )

        self.assertEqual(
            app._find_shortest_golden_path(conn, 10),
            [(20, 30), (21, 31), (22, 32), (1, 33)],
        )

    def test_find_golden_path_prefers_shortest_success_path(self) -> None:
        app = self._load_main_module()
        conn = self._db()
        conn.executemany(
            "INSERT INTO svyazi (ID, id_start, id_finish) VALUES (?, ?, ?)",
            [
                (30, 10, 20),
                (31, 20, 21),
                (32, 21, 22),
                (33, 22, 1),
                (40, 10, 50),
                (41, 50, 1),
            ],
        )

        self.assertEqual(app._find_shortest_golden_path(conn, 10), [(50, 40), (1, 41)])

    def test_find_golden_path_rejects_negative_and_broken_paths(self) -> None:
        app = self._load_main_module()
        conn = self._db()
        conn.executemany(
            "INSERT INTO svyazi (ID, id_start, id_finish) VALUES (?, ?, ?)",
            [
                (30, 10, 20),
                (31, 20, 2),
                (40, 10, 50),
                (41, 999, 1),
            ],
        )

        self.assertEqual(app._find_shortest_golden_path(conn, 10), [])

    def test_install_golden_path_sets_zolotoy_and_pyt(self) -> None:
        app = self._load_main_module()
        conn = self._db()
        conn.executemany(
            "INSERT INTO svyazi (ID, id_start, id_finish) VALUES (?, ?, ?)",
            [
                (30, 10, 20),
                (31, 20, 1),
            ],
        )
        app.cursor = conn
        app.poisk_id_s_max_signal_points = lambda: 10

        self.assertTrue(app._install_golden_path_for_current_task("o1"))
        self.assertEqual(app.zolotoy_pyt, [(20, 30), (1, 31)])
        self.assertEqual(app.pyt, [(20, 30), (1, 31)])
        self.assertIsNone(app.blocked_target)
        self.assertEqual(app.remaining_golden_path, [])

    def test_clear_golden_runtime_state_clears_runtime_memory(self) -> None:
        app = self._load_main_module()
        app.pyt = [(20, 30)]
        app.zolotoy_pyt = [(20, 30)]
        app.blocked_target = 20
        app.remaining_golden_path = [(20, 30)]
        app.in_pamyat = [10]
        app.in_pamyat_name = ["o1"]

        app._clear_golden_runtime_state()

        self.assertEqual(app.pyt, [])
        self.assertEqual(app.zolotoy_pyt, [])
        self.assertIsNone(app.blocked_target)
        self.assertEqual(app.remaining_golden_path, [])
        self.assertEqual(app.in_pamyat, [])
        self.assertEqual(app.in_pamyat_name, [])

    def test_mark_golden_path_blocked_saves_remaining_path(self) -> None:
        app = self._load_main_module()
        app.pyt = [(20, 30), (21, 31), (1, 32)]
        app.zolotoy_pyt = [(20, 30), (21, 31), (1, 32)]
        app.blocked_target = None
        app.remaining_golden_path = []

        app._mark_golden_path_blocked(21)

        self.assertEqual(app.blocked_target, 21)
        self.assertEqual(app.remaining_golden_path, [(21, 31), (1, 32)])

    def test_out_red_positive_reaction_clears_golden_state(self) -> None:
        app = self._load_main_module()
        conn = self._db()
        conn.execute("INSERT INTO svyazi (ID, id_start, id_finish) VALUES (?, ?, ?)", (9, 10, 20))
        app.cursor = conn
        app.pyt = [(1, 32)]
        app.zolotoy_pyt = [(20, 30), (1, 32)]
        app.blocked_target = 20
        app.remaining_golden_path = [(1, 32)]
        app.in_pamyat = [10]
        app.in_pamyat_name = ["o1"]

        class LogStub:
            def log(self, **_kwargs) -> None:
                return None

        class WhyStub:
            def trace(self, **_kwargs) -> None:
                return None

        app._ru_log = LogStub()
        app._why = WhyStub()
        app._why_trace_id = None
        app.get_max_signal_point = lambda _cursor: None
        app.get_point_by_id = lambda _cursor, point_id: {"name": str(point_id), "type": "REAC"}

        app.out_red(1)

        self.assertEqual(app.pyt, [])
        self.assertEqual(app.zolotoy_pyt, [])
        self.assertIsNone(app.blocked_target)
        self.assertEqual(app.remaining_golden_path, [])
        self.assertEqual(app.in_pamyat, [])
        self.assertEqual(app.in_pamyat_name, [])
        self.assertEqual(
            conn.execute("SELECT id_start, id_finish FROM svyazi WHERE ID = 10").fetchone(),
            (1, 3),
        )


if __name__ == "__main__":
    unittest.main()
