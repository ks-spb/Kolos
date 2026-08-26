from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pytest

import graph_viewer


PROJECT_DIR = Path(__file__).resolve().parents[1]
GRAPH_VIEWER_LAUNCHER = PROJECT_DIR / "Запустить граф Kolos.bat"


def _create_database(
    path: Path,
    *,
    nodes: list[tuple[int, str, str]] | None = None,
    edges: list[tuple[int, int, int]] | None = None,
    include_weight: bool = False,
) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE tochki (
                ID INTEGER,
                name TEXT,
                work INTEGER DEFAULT 0,
                type TEXT,
                func TEXT,
                porog INTEGER DEFAULT 1,
                signal REAL DEFAULT 0,
                puls INTEGER DEFAULT 1,
                rod1 INTEGER,
                rod2 INTEGER,
                name2 TEXT
            )
            """
        )
        weight_column = ", weight REAL DEFAULT 0.1" if include_weight else ""
        connection.execute(
            "CREATE TABLE svyazi ("
            "ID INTEGER, id_start INTEGER, id_finish INTEGER"
            f"{weight_column})"
        )
        connection.executemany(
            "INSERT INTO tochki (ID, name, type) VALUES (?, ?, ?)",
            nodes or [],
        )
        connection.executemany(
            "INSERT INTO svyazi (ID, id_start, id_finish) VALUES (?, ?, ?)",
            edges or [],
        )


def _edges_by_pair(graph: graph_viewer.GraphData) -> dict[tuple[int, int], graph_viewer.GraphEdge]:
    return {(edge.source, edge.target): edge for edge in graph.edges}


def _pyvis_dataset(document: str, variable_name: str) -> list[dict[str, object]]:
    match = re.search(
        rf"{variable_name}\s*=\s*new vis\.DataSet\((\[.*?\])\);",
        document,
        flags=re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


def test_double_click_launcher_runs_from_its_own_directory() -> None:
    text = GRAPH_VIEWER_LAUNCHER.read_text(encoding="utf-8")

    assert 'cd /d "%~dp0"' in text
    assert '"%~dp0graph_viewer.py"' in text


def test_double_click_launcher_prefers_venv_and_pauses_on_error() -> None:
    text = GRAPH_VIEWER_LAUNCHER.read_text(encoding="utf-8")

    assert r".venv\Scripts\python.exe" in text
    assert 'py -3 "%~dp0graph_viewer.py"' in text
    assert 'python "%~dp0graph_viewer.py"' in text
    assert "if errorlevel 1" in text
    assert "pause" in text


def test_default_database_path_prefers_environment_override(tmp_path: Path) -> None:
    configured = tmp_path / "configured.db"
    assert graph_viewer.default_database_path(
        {"KOLOS_GRAPH_DATABASE_PATH": str(configured)}
    ) == configured


def test_default_database_path_is_project_v4_database() -> None:
    assert graph_viewer.default_database_path({}) == graph_viewer.DEFAULT_DATABASE_PATH
    assert graph_viewer.DEFAULT_DATABASE_PATH.name == "db_v4.db"


def test_project_v4_database_loads_its_tochki_and_svyazi_read_only() -> None:
    database = graph_viewer.default_database_path({})
    before = database.read_bytes()

    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        node_count = connection.execute("SELECT COUNT(*) FROM tochki").fetchone()[0]
        edge_pair_count = connection.execute(
            "SELECT COUNT(*) FROM ("
            "SELECT id_start, id_finish FROM svyazi GROUP BY id_start, id_finish"
            ")"
        ).fetchone()[0]
        weight_columns = {
            row[1].casefold() for row in connection.execute("PRAGMA table_info(svyazi)")
        }

    graph = graph_viewer.load_graph_data(database)

    assert database.read_bytes() == before
    assert len(graph.nodes) == node_count + 1  # Служебный внешний вход ID 0.
    assert len(graph.edges) == edge_pair_count
    assert any("func" in node.fields for node in graph.nodes if not node.synthetic)
    assert "weight" not in weight_columns
    assert all(
        record.weight == graph_viewer.MISSING_WEIGHT_LABEL
        for edge in graph.edges
        for record in edge.records
    )


def test_v4_layout_is_compact_and_avoids_overlap() -> None:
    options = graph_viewer._network_options()
    hierarchical = options["layout"]["hierarchical"]

    assert hierarchical["direction"] == "LR"
    assert hierarchical["sortMethod"] == "hubsize"
    assert hierarchical["edgeMinimization"] is True
    assert options["physics"]["hierarchicalRepulsion"]["avoidOverlap"] == 1


def test_load_groups_parallel_edges_and_keeps_reverse_separate(tmp_path: Path) -> None:
    database = tmp_path / "memory.db"
    _create_database(
        database,
        nodes=[(1, "Альфа", "mozg"), (2, "Бета", "print")],
        edges=[
            (44, 1, 2),
            (12, 1, 2),
            (31, 1, 2),
            (18, 1, 2),
            (50, 2, 1),
        ],
    )

    before = database.read_bytes()
    graph = graph_viewer.load_graph_data(database)
    after = database.read_bytes()

    assert before == after
    edges = _edges_by_pair(graph)
    assert set(edges) == {(1, 2), (2, 1)}
    assert edges[(1, 2)].edge_ids == (12, 18, 31, 44)
    assert edges[(2, 1)].edge_ids == (50,)
    assert [record.weight for record in edges[(1, 2)].records] == [
        graph_viewer.MISSING_WEIGHT_LABEL
    ] * 4


def test_optional_weight_column_is_included_when_present(tmp_path: Path) -> None:
    database = tmp_path / "weighted.db"
    _create_database(
        database,
        nodes=[(1, "Альфа", "mozg"), (2, "Бета", "print")],
        edges=[(7, 1, 2)],
        include_weight=True,
    )
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE svyazi SET weight = 2.75 WHERE ID = 7")

    graph = graph_viewer.load_graph_data(database)

    assert graph.edges[0].records[0].weight == 2.75


def test_load_adds_external_and_missing_diagnostic_nodes(tmp_path: Path) -> None:
    database = tmp_path / "memory.db"
    _create_database(
        database,
        nodes=[(1, "Старт", "mozg")],
        edges=[(3, 0, 1), (4, 1, 99)],
    )

    graph = graph_viewer.load_graph_data(database)
    nodes = {node.node_id: node for node in graph.nodes}

    assert nodes[0].synthetic is True
    assert nodes[0].diagnostic is False
    assert nodes[0].fields["name"] == "внешний вход"
    assert nodes[99].synthetic is True
    assert nodes[99].diagnostic is True
    assert nodes[99].fields["name"] == "отсутствует в tochki"
    assert graph.warnings and "ID 99" in graph.warnings[0]


def test_duplicate_node_id_is_data_error(tmp_path: Path) -> None:
    database = tmp_path / "duplicates.db"
    _create_database(
        database,
        nodes=[(1, "Первый", "mozg"), (1, "Второй", "time")],
    )

    with pytest.raises(graph_viewer.GraphViewerError, match="повторяется ID вершины 1"):
        graph_viewer.load_graph_data(database)


def test_invalid_schema_has_clear_error(tmp_path: Path) -> None:
    database = tmp_path / "invalid.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE tochki (ID INTEGER, name TEXT)")
        connection.execute(
            "CREATE TABLE svyazi (ID INTEGER, id_start INTEGER, id_finish INTEGER)"
        )

    with pytest.raises(graph_viewer.GraphViewerError, match="обязательные поля"):
        graph_viewer.load_graph_data(database)


def test_empty_tables_render_to_standalone_html(tmp_path: Path) -> None:
    database = tmp_path / "empty.db"
    output = tmp_path / "empty.html"
    _create_database(database)

    graph = graph_viewer.load_graph_data(database)
    rendered = graph_viewer.render_graph(graph, output)
    document = output.read_text(encoding="utf-8")

    assert rendered == output.resolve()
    assert graph.nodes == ()
    assert graph.edges == ()
    assert 'id="kolos-search"' in document
    assert 'id="kolos-filter-field"' in document
    assert not re.search(
        r"<(?:script|link)\b[^>]*(?:src|href)\s*=\s*['\"]https?://",
        document,
        flags=re.IGNORECASE,
    )


def test_render_contains_labels_compact_id_tooltips_and_loops(tmp_path: Path) -> None:
    database = tmp_path / "content.db"
    output = tmp_path / "graph.html"
    _create_database(
        database,
        nodes=[
            (1, '<script>alert("x")</script>&', "mozg"),
            (2, "Финиш", "print"),
        ],
        edges=[
            (44, 1, 2),
            (12, 1, 2),
            (7, 1, 1),
            (50, 2, 1),
        ],
    )

    graph = graph_viewer.load_graph_data(database)
    graph_viewer.render_graph(graph, output)
    document = output.read_text(encoding="utf-8")
    rendered_nodes = _pyvis_dataset(document, "nodes")
    rendered_edges = _pyvis_dataset(document, "edges")
    nodes_by_id = {node["id"]: node for node in rendered_nodes}
    edges_by_id = {edge["id"]: edge for edge in rendered_edges}

    assert nodes_by_id[1]["label"] == 'ID 1\n<script>alert("x")</script>&'
    assert nodes_by_id[2]["label"] == "ID 2\nФиниш"
    assert nodes_by_id[1]["shape"] == "box"
    assert nodes_by_id[1]["title"] == "ID 1"
    assert nodes_by_id[2]["title"] == "ID 2"
    assert edges_by_id["1->2"]["label"] == "12, 44"
    assert edges_by_id["1->2"]["title"] == "ID 12, 44"
    assert edges_by_id["1->1"]["title"] == "ID 7"
    assert edges_by_id["2->1"]["title"] == "ID 50"
    assert edges_by_id["1->1"]["selfReferenceSize"] == 44
    assert edges_by_id["1->1"]["smooth"]["type"] == "curvedCW"
    assert edges_by_id["1->2"]["smooth"] == edges_by_id["2->1"]["smooth"]


def test_no_open_cli_creates_html_without_browser(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = tmp_path / "memory.db"
    output = tmp_path / "out.html"
    _create_database(
        database,
        nodes=[(1, "Один", "mozg"), (2, "Два", "print")],
        edges=[(1, 1, 2)],
    )

    def unexpected_browser_call(_url: str) -> bool:
        raise AssertionError("browser must not be opened with --no-open")

    monkeypatch.setattr(graph_viewer.webbrowser, "open", unexpected_browser_call)
    result = graph_viewer.main(
        [
            "--database",
            str(database),
            "--output",
            str(output),
            "--no-open",
        ]
    )

    assert result == 0
    assert output.is_file()


def test_build_graph_opens_generated_file_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "memory.db"
    output = tmp_path / "out.html"
    _create_database(database, nodes=[(1, "Один", "mozg")])
    opened_urls: list[str] = []

    monkeypatch.setattr(
        graph_viewer.webbrowser,
        "open",
        lambda url: opened_urls.append(url) or True,
    )
    graph_viewer.build_graph(database, output)

    assert opened_urls == [output.resolve().as_uri()]


def test_missing_database_returns_nonzero_and_is_not_created(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = tmp_path / "does-not-exist.db"
    output = tmp_path / "must-not-exist.html"

    result = graph_viewer.main(
        [
            "--database",
            str(database),
            "--output",
            str(output),
            "--no-open",
        ]
    )

    captured = capsys.readouterr()
    assert result != 0
    assert "База памяти не найдена" in captured.err
    assert not database.exists()
    assert not output.exists()


def test_output_cannot_overwrite_database(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    database = tmp_path / "memory.db"
    _create_database(database, nodes=[(1, "Сохранить", "mozg")])
    before = database.read_bytes()

    result = graph_viewer.main(
        [
            "--database",
            str(database),
            "--output",
            str(database),
            "--no-open",
        ]
    )

    captured = capsys.readouterr()
    assert result != 0
    assert "перезапись памяти запрещена" in captured.err
    assert database.read_bytes() == before
