"""Read-only interactive graph viewer for the Kolos SQLite memory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_PATH = PROJECT_DIR / "db_v4.db"
DEFAULT_OUTPUT_PATH = PROJECT_DIR / "kolos_graph.html"

REQUIRED_COLUMNS = {
    "tochki": {"id", "name", "type"},
    "svyazi": {"id", "id_start", "id_finish"},
}
MISSING_WEIGHT_LABEL = "— (нет поля weight)"

KNOWN_TYPE_COLORS = {
    "mozg": "#2563eb",
    "print": "#16a34a",
    "reakciya": "#f59e0b",
    "time": "#7c3aed",
}
TYPE_COLOR_PALETTE = (
    "#0891b2",
    "#0d9488",
    "#4f46e5",
    "#c026d3",
    "#db2777",
    "#ea580c",
    "#65a30d",
)


class GraphViewerError(RuntimeError):
    """A user-facing error raised while loading or rendering the graph."""


@dataclass(frozen=True)
class GraphNode:
    node_id: int
    fields: Mapping[str, Any]
    synthetic: bool = False
    diagnostic: bool = False


@dataclass(frozen=True)
class EdgeRecord:
    edge_id: int
    weight: Any


@dataclass(frozen=True)
class GraphEdge:
    source: int
    target: int
    records: tuple[EdgeRecord, ...]

    @property
    def edge_ids(self) -> tuple[int, ...]:
        return tuple(record.edge_id for record in self.records)


@dataclass(frozen=True)
class GraphData:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    warnings: tuple[str, ...] = ()


def default_database_path(environment: Mapping[str, str] | None = None) -> Path:
    """Return the Kolos v4 database path without touching the filesystem."""

    env = os.environ if environment is None else environment
    configured = env.get("KOLOS_GRAPH_DATABASE_PATH")
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_DATABASE_PATH


def _read_only_uri(database_path: Path) -> str:
    return f"{database_path.resolve().as_uri()}?mode=ro"


def _column_map(connection: sqlite3.Connection, table_name: str) -> dict[str, str]:
    rows = connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    if not rows:
        raise GraphViewerError(f'В базе отсутствует таблица "{table_name}".')

    columns = {str(row[1]).casefold(): str(row[1]) for row in rows}
    missing = sorted(REQUIRED_COLUMNS[table_name] - columns.keys())
    if missing:
        missing_text = ", ".join(missing)
        raise GraphViewerError(
            f'В таблице "{table_name}" отсутствуют обязательные поля: {missing_text}.'
        )
    return columns


def _coerce_integer(value: Any, description: str) -> int:
    if isinstance(value, bool):
        raise GraphViewerError(f"{description} должен быть целым числом, получено {value!r}.")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and re.fullmatch(r"[+-]?\d+", value.strip()):
        return int(value)
    raise GraphViewerError(f"{description} должен быть целым числом, получено {value!r}.")


def _serializable_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return value.hex()
    return str(value)


def load_graph_data(database_path: Path | str) -> GraphData:
    """Load all nodes and links from an existing SQLite database in read-only mode."""

    path = Path(database_path).expanduser()
    if not path.is_file():
        raise GraphViewerError(
            f"База памяти не найдена: {path}. "
            "Укажите путь через --database или KOLOS_GRAPH_DATABASE_PATH."
        )

    try:
        connection = sqlite3.connect(_read_only_uri(path), uri=True)
    except sqlite3.Error as error:
        raise GraphViewerError(f"Не удалось открыть базу только для чтения: {error}") from error

    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only = ON")
        node_columns = _column_map(connection, "tochki")
        edge_columns = _column_map(connection, "svyazi")
        node_rows = connection.execute('SELECT * FROM "tochki"').fetchall()
        edge_rows = connection.execute('SELECT * FROM "svyazi"').fetchall()
    except GraphViewerError:
        raise
    except sqlite3.Error as error:
        raise GraphViewerError(f"Не удалось прочитать граф из SQLite: {error}") from error
    finally:
        connection.close()

    nodes_by_id: dict[int, GraphNode] = {}
    for row_number, row in enumerate(node_rows, start=1):
        node_id = _coerce_integer(
            row[node_columns["id"]], f"tochki.ID в строке {row_number}"
        )
        if node_id in nodes_by_id:
            raise GraphViewerError(
                f"В таблице tochki повторяется ID вершины {node_id}; "
                "однозначное построение графа невозможно."
            )
        fields = {key: _serializable_value(row[key]) for key in row.keys()}
        nodes_by_id[node_id] = GraphNode(node_id=node_id, fields=fields)

    grouped_edges: dict[tuple[int, int], list[EdgeRecord]] = {}
    referenced_ids: set[int] = set()
    for row_number, row in enumerate(edge_rows, start=1):
        edge_id = _coerce_integer(
            row[edge_columns["id"]], f"svyazi.ID в строке {row_number}"
        )
        source = _coerce_integer(
            row[edge_columns["id_start"]],
            f"svyazi.id_start в строке {row_number}",
        )
        target = _coerce_integer(
            row[edge_columns["id_finish"]],
            f"svyazi.id_finish в строке {row_number}",
        )
        weight_column = edge_columns.get("weight")
        weight = (
            _serializable_value(row[weight_column])
            if weight_column is not None
            else MISSING_WEIGHT_LABEL
        )
        grouped_edges.setdefault((source, target), []).append(
            EdgeRecord(edge_id=edge_id, weight=weight)
        )
        referenced_ids.update((source, target))

    warnings: list[str] = []
    if 0 in referenced_ids and 0 not in nodes_by_id:
        nodes_by_id[0] = GraphNode(
            node_id=0,
            fields={
                "ID": 0,
                "name": "внешний вход",
                "type": "external",
                "status": "служебная вершина; в базу не записывается",
            },
            synthetic=True,
        )

    for missing_id in sorted(referenced_ids - nodes_by_id.keys()):
        message = (
            f"Связь ссылается на отсутствующую вершину ID {missing_id}; "
            "добавлена диагностическая вершина."
        )
        warnings.append(message)
        nodes_by_id[missing_id] = GraphNode(
            node_id=missing_id,
            fields={
                "ID": missing_id,
                "name": "отсутствует в tochki",
                "type": "missing",
                "status": message,
            },
            synthetic=True,
            diagnostic=True,
        )

    edges = tuple(
        GraphEdge(
            source=source,
            target=target,
            records=tuple(
                sorted(records, key=lambda record: (record.edge_id, str(record.weight)))
            ),
        )
        for (source, target), records in sorted(grouped_edges.items())
    )
    nodes = tuple(nodes_by_id[node_id] for node_id in sorted(nodes_by_id))
    return GraphData(nodes=nodes, edges=edges, warnings=tuple(warnings))


def _field_value(fields: Mapping[str, Any], wanted_name: str) -> Any:
    wanted = wanted_name.casefold()
    for name, value in fields.items():
        if name.casefold() == wanted:
            return value
    return None


def _node_label(node: GraphNode) -> str:
    name = _field_value(node.fields, "name")
    readable_name = "(без названия)" if name is None else str(name)
    return f"ID {node.node_id}\n{readable_name}"


def _node_title(node: GraphNode) -> str:
    return f"ID {node.node_id}"


def _type_color(node: GraphNode) -> str:
    if node.diagnostic:
        return "#ef4444"
    if node.node_id == 0 and node.synthetic:
        return "#64748b"

    node_type = str(_field_value(node.fields, "type") or "без типа").casefold()
    if node_type in KNOWN_TYPE_COLORS:
        return KNOWN_TYPE_COLORS[node_type]
    digest = hashlib.sha256(node_type.encode("utf-8")).digest()
    return TYPE_COLOR_PALETTE[int.from_bytes(digest[:2], "big") % len(TYPE_COLOR_PALETTE)]


def _edge_title(edge: GraphEdge) -> str:
    edge_ids = ", ".join(str(edge_id) for edge_id in edge.edge_ids)
    return f"ID {edge_ids}"


def _network_options() -> dict[str, Any]:
    return {
        "autoResize": True,
        "interaction": {
            "dragNodes": True,
            "dragView": True,
            "hover": True,
            "keyboard": {"enabled": True},
            "multiselect": True,
            "navigationButtons": True,
            "tooltipDelay": 120,
            "zoomView": True,
        },
        "layout": {
            "hierarchical": {
                "enabled": True,
                "direction": "LR",
                # db_v4.db contains many cycles. Hub-based levels keep the
                # overview compact while arrowheads retain edge direction.
                "sortMethod": "hubsize",
                "levelSeparation": 180,
                "nodeSpacing": 160,
                "treeSpacing": 210,
                "blockShifting": True,
                "edgeMinimization": True,
                "parentCentralization": True,
                "shakeTowards": "roots",
            }
        },
        "physics": {
            "enabled": True,
            "solver": "hierarchicalRepulsion",
            "hierarchicalRepulsion": {
                "nodeDistance": 190,
                "centralGravity": 0.0,
                "springLength": 220,
                "springConstant": 0.01,
                "damping": 0.15,
                "avoidOverlap": 1,
            },
            "stabilization": {
                "enabled": True,
                "iterations": 500,
                "updateInterval": 25,
                "fit": True,
            },
        },
        "nodes": {
            "borderWidth": 1.5,
            "borderWidthSelected": 3,
            "font": {"face": "Arial", "size": 15, "color": "#0f172a"},
            "margin": 12,
            "shape": "box",
        },
        "edges": {
            "arrows": {"to": {"enabled": True, "scaleFactor": 0.85}},
            "color": {
                "color": "#64748b",
                "highlight": "#0f172a",
                "hover": "#2563eb",
                "inherit": False,
                "opacity": 0.82,
            },
            "font": {
                "align": "middle",
                "size": 12,
                "color": "#334155",
                "strokeWidth": 5,
                "strokeColor": "#ffffff",
            },
            "selfReferenceSize": 38,
            "smooth": {
                "enabled": True,
                "type": "cubicBezier",
                "forceDirection": "horizontal",
                "roundness": 0.3,
            },
            "width": 1.8,
        },
    }


TOOLBAR_HTML = """
<div id="kolos-toolbar">
  <div class="kolos-title">Граф памяти Kolos</div>
  <label>Поиск вершины
    <input id="kolos-search" type="search" placeholder="ID или текст">
  </label>
  <label>Поле
    <select id="kolos-filter-field"></select>
  </label>
  <label>Значение
    <input id="kolos-filter-value" type="search" placeholder="часть значения">
  </label>
  <button id="kolos-reset" type="button">Сбросить</button>
  <span id="kolos-status" aria-live="polite"></span>
</div>
"""

TOOLBAR_STYLE = """
<style>
  html, body { height: 100%; margin: 0; background: #f8fafc; font-family: Arial, sans-serif; }
  #kolos-toolbar {
    box-sizing: border-box; min-height: 78px; padding: 10px 14px; display: flex;
    flex-wrap: wrap; align-items: end; gap: 10px 14px; color: #0f172a;
    background: #ffffff; border-bottom: 1px solid #cbd5e1;
  }
  #kolos-toolbar .kolos-title { align-self: center; margin-right: 8px; font-size: 18px; font-weight: 700; }
  #kolos-toolbar label { display: grid; gap: 4px; font-size: 12px; font-weight: 600; }
  #kolos-toolbar input, #kolos-toolbar select, #kolos-toolbar button {
    box-sizing: border-box; min-width: 170px; height: 34px; padding: 6px 9px;
    border: 1px solid #94a3b8; border-radius: 6px; background: #ffffff; color: #0f172a;
  }
  #kolos-toolbar button { min-width: 100px; cursor: pointer; font-weight: 600; }
  #kolos-toolbar button:hover { background: #e2e8f0; }
  #kolos-status { align-self: center; color: #475569; font-size: 13px; }
  #mynetwork { background: #ffffff; }
</style>
"""

TOOLBAR_SCRIPT = """
<script>
(function () {
  var searchInput = document.getElementById("kolos-search");
  var fieldSelect = document.getElementById("kolos-filter-field");
  var filterInput = document.getElementById("kolos-filter-value");
  var resetButton = document.getElementById("kolos-reset");
  var status = document.getElementById("kolos-status");
  if (!searchInput || typeof network === "undefined") {
    return;
  }

  var originalNodes = new Map();
  var originalEdges = new Map();
  nodes.get().forEach(function (node) {
    originalNodes.set(node.id, {
      color: node.color,
      opacity: node.opacity == null ? 1 : node.opacity
    });
  });
  edges.get().forEach(function (edge) {
    originalEdges.set(edge.id, {
      color: edge.color,
      width: edge.width == null ? 1.8 : edge.width
    });
  });

  var fieldNames = new Set();
  nodes.get().forEach(function (node) {
    Object.keys(node.kolos_fields || {}).forEach(function (name) {
      fieldNames.add(name);
    });
  });
  var allOption = document.createElement("option");
  allOption.value = "";
  allOption.textContent = "Все поля";
  fieldSelect.appendChild(allOption);
  Array.from(fieldNames).sort().forEach(function (name) {
    var option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    fieldSelect.appendChild(option);
  });

  function searchableText(node, fieldName) {
    var fields = node.kolos_fields || {};
    if (fieldName) {
      return String(fields[fieldName] == null ? "" : fields[fieldName]).toLowerCase();
    }
    return (
      String(node.id) + " " + String(node.label || "") + " " +
      Object.keys(fields).map(function (key) { return key + " " + fields[key]; }).join(" ")
    ).toLowerCase();
  }

  function restoreHighlight() {
    nodes.update(nodes.get().map(function (node) {
      var original = originalNodes.get(node.id);
      return {id: node.id, color: original.color, opacity: original.opacity};
    }));
    edges.update(edges.get().map(function (edge) {
      var original = originalEdges.get(edge.id);
      return {id: edge.id, color: original.color, width: original.width};
    }));
  }

  function highlightNeighborhood(nodeId) {
    restoreHighlight();
    var relatedNodes = new Set(network.getConnectedNodes(nodeId));
    relatedNodes.add(nodeId);
    var relatedEdges = new Set(network.getConnectedEdges(nodeId));
    nodes.update(nodes.get().map(function (node) {
      return {id: node.id, opacity: relatedNodes.has(node.id) ? 1 : 0.16};
    }));
    edges.update(edges.get().map(function (edge) {
      if (relatedEdges.has(edge.id)) {
        return {id: edge.id, width: 3.2};
      }
      return {id: edge.id, color: {color: "#cbd5e1", opacity: 0.12}, width: 1};
    }));
  }

  function applyFilter() {
    var fieldName = fieldSelect.value;
    var value = filterInput.value.trim().toLowerCase();
    restoreHighlight();
    network.unselectAll();
    var visible = new Set();
    nodes.get().forEach(function (node) {
      var show = !value || searchableText(node, fieldName).indexOf(value) !== -1;
      if (show) {
        visible.add(node.id);
      }
      nodes.update({id: node.id, hidden: !show});
    });
    edges.get().forEach(function (edge) {
      edges.update({id: edge.id, hidden: !(visible.has(edge.from) && visible.has(edge.to))});
    });
    status.textContent = "Показано вершин: " + visible.size + " из " + nodes.length;
    if (visible.size) {
      network.fit({animation: {duration: 250, easingFunction: "easeInOutQuad"}});
    }
  }

  function runSearch() {
    var query = searchInput.value.trim().toLowerCase();
    if (!query) {
      network.unselectAll();
      restoreHighlight();
      status.textContent = "Вершин: " + nodes.length + ", связей: " + edges.length;
      return;
    }
    var matches = nodes.get({
      filter: function (node) {
        return !node.hidden && searchableText(node, "").indexOf(query) !== -1;
      }
    }).map(function (node) { return node.id; });
    network.selectNodes(matches, false);
    status.textContent = "Найдено вершин: " + matches.length;
    if (matches.length) {
      highlightNeighborhood(matches[0]);
      network.focus(matches[0], {
        scale: 1.15,
        animation: {duration: 350, easingFunction: "easeInOutQuad"}
      });
    }
  }

  searchInput.addEventListener("input", runSearch);
  fieldSelect.addEventListener("change", applyFilter);
  filterInput.addEventListener("input", applyFilter);
  resetButton.addEventListener("click", function () {
    searchInput.value = "";
    fieldSelect.value = "";
    filterInput.value = "";
    applyFilter();
    status.textContent = "Вершин: " + nodes.length + ", связей: " + edges.length;
  });
  network.on("hoverNode", function (params) { highlightNeighborhood(params.node); });
  network.on("blurNode", function () {
    if (!network.getSelectedNodes().length) { restoreHighlight(); }
  });
  network.on("hoverEdge", function (params) {
    var edge = edges.get(params.edge);
    if (edge) {
      highlightNeighborhood(edge.from);
      nodes.update({id: edge.to, opacity: 1});
      edges.update({id: edge.id, width: 3.6});
    }
  });
  network.on("blurEdge", function () {
    if (!network.getSelectedNodes().length) { restoreHighlight(); }
  });
  network.on("selectNode", function (params) { highlightNeighborhood(params.nodes[0]); });
  network.on("deselectNode", restoreHighlight);
  network.on("click", function (params) {
    if (!params.nodes.length && !params.edges.length) { restoreHighlight(); }
  });
  status.textContent = "Вершин: " + nodes.length + ", связей: " + edges.length;
})();
</script>
"""


def _inject_controls(document: str) -> str:
    if "</head>" not in document or "<body>" not in document or "</body>" not in document:
        raise GraphViewerError("PyVis вернул HTML неожиданного формата.")
    document = document.replace("</head>", f"{TOOLBAR_STYLE}\n</head>", 1)
    document = document.replace("<body>", f"<body>\n{TOOLBAR_HTML}", 1)
    return document.replace("</body>", f"{TOOLBAR_SCRIPT}\n</body>", 1)


def _remove_remote_resources(document: str) -> str:
    """Remove PyVis template extras that would make the document non-standalone."""

    document = re.sub(
        r"<link\b[^>]*href\s*=\s*['\"]https?://[^>]*>",
        "",
        document,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return re.sub(
        r"<script\b[^>]*src\s*=\s*['\"]https?://[^>]*>\s*</script>",
        "",
        document,
        flags=re.IGNORECASE | re.DOTALL,
    )


def _assert_no_remote_resources(document: str) -> None:
    remote_tag = re.search(
        r"<(?:script|link)\b[^>]*(?:src|href)\s*=\s*['\"]https?://",
        document,
        flags=re.IGNORECASE,
    )
    if remote_tag:
        raise GraphViewerError(
            "Не удалось создать автономный HTML: PyVis добавил внешний ресурс."
        )


def render_graph(graph: GraphData, output_path: Path | str) -> Path:
    """Render a standalone HTML document and return its resolved path."""

    try:
        from pyvis.network import Network
    except ImportError as error:
        raise GraphViewerError(
            "PyVis не установлен. Выполните: python -m pip install -r requirements.txt"
        ) from error

    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    network = Network(
        height="calc(100vh - 80px)",
        width="100%",
        directed=True,
        notebook=False,
        cdn_resources="in_line",
        heading="",
    )
    network.set_options(json.dumps(_network_options(), ensure_ascii=False))

    for node in graph.nodes:
        background = _type_color(node)
        border = "#991b1b" if node.diagnostic else "#334155"
        network.add_node(
            node.node_id,
            label=_node_label(node),
            title=_node_title(node),
            shape="box",
            color={
                "background": background,
                "border": border,
                "highlight": {"background": "#fde68a", "border": "#0f172a"},
                "hover": {"background": "#fef3c7", "border": "#2563eb"},
            },
            font={"color": "#ffffff" if not node.diagnostic else "#ffffff"},
            kolos_fields=dict(node.fields),
            synthetic=node.synthetic,
            diagnostic=node.diagnostic,
        )

    edge_pairs = {(edge.source, edge.target) for edge in graph.edges}
    for edge in graph.edges:
        label = ", ".join(str(edge_id) for edge_id in edge.edge_ids)
        is_loop = edge.source == edge.target
        has_reverse = not is_loop and (edge.target, edge.source) in edge_pairs
        if is_loop:
            smooth = {"enabled": True, "type": "curvedCW", "roundness": 0.55}
        elif has_reverse:
            # The same curvature direction on oppositely directed edges places
            # their arcs on opposite sides of the node pair.
            smooth = {"enabled": True, "type": "curvedCW", "roundness": 0.28}
        else:
            smooth = {
                "enabled": True,
                "type": "cubicBezier",
                "forceDirection": "horizontal",
                "roundness": 0.3,
            }
        network.add_edge(
            edge.source,
            edge.target,
            id=f"{edge.source}->{edge.target}",
            label=label,
            title=_edge_title(edge),
            arrows="to",
            smooth=smooth,
            selfReferenceSize=44 if is_loop else 38,
        )

    try:
        document = network.generate_html(notebook=False)
        document = _remove_remote_resources(document)
        document = _inject_controls(document)
        _assert_no_remote_resources(document)
        output.write_text(document, encoding="utf-8")
    except GraphViewerError:
        raise
    except (OSError, ValueError, TypeError) as error:
        raise GraphViewerError(f"Не удалось сохранить HTML {output}: {error}") from error
    return output


def build_graph(
    database_path: Path | str,
    output_path: Path | str = DEFAULT_OUTPUT_PATH,
    *,
    open_browser: bool = True,
) -> GraphData:
    """Load, render, and optionally open the Kolos graph."""

    database = Path(database_path).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()
    same_file = database == output
    if not same_file and database.exists() and output.exists():
        try:
            same_file = os.path.samefile(database, output)
        except OSError:
            same_file = False
    if same_file:
        raise GraphViewerError(
            "Путь --output совпадает с SQLite-базой; перезапись памяти запрещена."
        )

    graph = load_graph_data(database)
    output = render_graph(graph, output)
    if open_browser:
        try:
            opened = webbrowser.open(output.as_uri())
        except webbrowser.Error as error:
            raise GraphViewerError(
                f"HTML создан ({output}), но браузер открыть не удалось: {error}"
            ) from error
        if not opened:
            print(
                f"HTML создан: {output}. Браузер не подтвердил открытие файла.",
                file=sys.stderr,
            )
    return graph


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Построить интерактивный граф памяти Kolos из SQLite."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help=(
            "Путь к SQLite-базе. По умолчанию: KOLOS_GRAPH_DATABASE_PATH, "
            "затем db_v4.db рядом с graph_viewer.py."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Путь к HTML (по умолчанию kolos_graph.html рядом со скриптом).",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Создать HTML, но не открывать браузер.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _argument_parser().parse_args(argv)
    database = args.database if args.database is not None else default_database_path()
    try:
        graph = build_graph(
            database,
            args.output,
            open_browser=not args.no_open,
        )
    except GraphViewerError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 2

    for warning in graph.warnings:
        print(f"Предупреждение: {warning}", file=sys.stderr)
    print(
        f"Граф создан: {Path(args.output).expanduser().resolve()} "
        f"(вершин: {len(graph.nodes)}, направлений связей: {len(graph.edges)})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
