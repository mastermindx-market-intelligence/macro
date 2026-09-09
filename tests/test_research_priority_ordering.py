"""A-F04-W4-1 uncalibrated research-priority ordering (MO-DELTA-006).

The module under test is engine/research_priority_ordering.py (seat ruling R1).
No test reads data/theme_graph/, shells out to git, or requires a browser.
"""
from __future__ import annotations

import ast
import itertools
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO / "engine" / "research_priority_ordering.py"
RP1_PATH = REPO / "engine" / "entry_radar" / "research_priority.py"
BUILDER_PATH = REPO / "scripts" / "build_state_of_themes.py"
TEMPLATE_PATH = REPO / "templates" / "state_of_themes.html.j2"
NAVLINKS_PATH = REPO / "templates" / "_navlinks.html.j2"

_SUPPORT_PARTIALS = (
    "_site_nav.html.j2",
    "_navlinks.html.j2",
    "_seo_head.html.j2",
)

_FORBIDDEN_RENDER = (
    "probability",
    "confidence",
    "conviction",
    "expected impact",
    "expected return",
    "priced in",
    "direction",
    "rank",
    "score",
    "edge",
    "buy",
    "sell",
    "validated",
    "概率",
    "把握",
    "置信",
    "信心",
    "信念",
    "预期影响",
    "预期收益",
    "已消化",
    "已计入价格",
    "方向",
    "看多",
    "看空",
    "做多",
    "做空",
    "排名",
    "评分",
    "得分",
    "优势",
    "买入",
    "卖出",
    "已验证",
    "经验证",
    "经过验证",
    "申报",
)

_REFUSAL_EN = (
    "This is a reading order, not a score. It does not say a theme is more likely "
    "to work, worth more, or already in the price."
)
_REFUSAL_ZH = "这只是阅读顺序，不是评分。它并不表示某个主题更可能奏效、价值更高，或已被价格消化。"
_DETAILS_EN = (
    "Every line here comes from the theme evidence record. We read two things only: "
    "the day a statement about the theme was written down, and how many were written "
    "down that day. We do not read, and this page does not show, any measure of size, "
    "direction, how sure we are, or how much is already in the price — those are not "
    "built yet."
)
_DETAILS_ZH = (
    "这里的每一行都来自主题证据记录。我们只读两样东西：关于该主题的说法是哪一天记录的，"
    "以及当天记录了多少条。我们不读取、本页也不显示任何关于幅度、方向、把握程度或价格已消化程度的度量——这些尚未建成。"
)
_RULE_EN = (
    "Ordered by when we last recorded new evidence about each theme — newest first. "
    "Themes recorded on the same day are ordered by how many statements were recorded "
    "that day, then by name."
)
_RULE_ZH = (
    "按我们最近一次记录到该主题新证据的时间排序，最新的排在前面。"
    "同一天记录的主题，按当天记录的条数排序，条数相同再按名称排序。"
)

_ALLOWED_INT_KEYS = frozenset(
    {"position", "statements_recorded", "n_total", "max_items"}
)


def _te(node_id: str, name_en: str, name_zh: str, *dates: str):
    from engine.research_priority_ordering import ThemeEvidence

    return ThemeEvidence(
        node_id=node_id,
        name_en=name_en,
        name_zh=name_zh,
        recorded_dates=tuple(dates),
    )


def _copy_templates(root: Path) -> None:
    templates = root / "templates"
    templates.mkdir(parents=True, exist_ok=True)
    templates.joinpath("state_of_themes.html.j2").write_bytes(TEMPLATE_PATH.read_bytes())
    for name in _SUPPORT_PARTIALS:
        src = REPO / "templates" / name
        templates.joinpath(name).write_bytes(src.read_bytes())


def _base_ctx(**kwargs):
    ctx = {
        "as_of": "2026-09-09",
        "n_themes": 1,
        "lanes": [],
        "ribbon": [],
        "hero_en": "",
        "hero_zh": "",
        "n_working": 0,
        "n_early": 0,
        "n_caution": 0,
        "n_review": 0,
        "n_falsifier_fired": 0,
        "n_stale_legs": 0,
        "chip_secular_at_cyclical": 0,
        "chip_bottleneck_tight": 0,
        "chip_thesis_review": 0,
        "chip_crowded": 0,
        "themes": [{"theme_id": "fixture"}],
        "weekly_transitions": [],
        "weekly_fired": [],
        "collision_note_en": "",
        "collision_note_zh": "",
        "trade_flows_page_note_en": "",
        "trade_flows_page_note_zh": "",
    }
    ctx.update(kwargs)
    return ctx


def _populated_payload():
    from engine.research_priority_ordering import (
        PriorityItem,
        max_recorded_date,
        to_payload,
    )

    items = (
        PriorityItem(1, "theme:power_grid", "Power grid", "电网", "2026-09-08", 4),
        PriorityItem(2, "theme:copper", "Copper", "铜", "2026-09-08", 1),
        PriorityItem(3, "theme:alpha", "Alpha", "阿尔法", "2026-09-01", 2),
        PriorityItem(4, "theme:undated_a", "Quiet story", "安静主题", None, 0),
    )
    return to_payload(items, asof=max_recorded_date(items), state="ok")


def _truncated_payload(n: int = 18):
    """A payload whose n_total exceeds MAX_ITEMS, so `rp.more` renders."""
    from engine.research_priority_ordering import (
        PriorityItem,
        max_recorded_date,
        to_payload,
    )

    items = tuple(
        PriorityItem(
            i + 1,
            f"theme:n{i:02d}",
            f"Name {i:02d}",
            f"名{i:02d}",
            "2026-09-08",
            1,
        )
        for i in range(n)
    )
    return to_payload(items, asof=max_recorded_date(items), state="ok")


def _write_theme_store(store_dir: Path, nodes: list[dict], edges: list[dict]) -> None:
    """Write a REAL parquet store, so the loader meets the real read conditions."""
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    from engine.theme_graph.store import EDGE_COLUMNS, NODE_COLUMNS

    store_dir.mkdir(parents=True, exist_ok=True)
    node_frame = pd.DataFrame(nodes, columns=list(NODE_COLUMNS))
    edge_frame = pd.DataFrame(edges, columns=list(EDGE_COLUMNS))
    node_frame.to_parquet(store_dir / "nodes.parquet", index=False)
    edge_frame.to_parquet(store_dir / "edges.parquet", index=False)


def _node(node_id: str, name_en: str, name_zh: str, *, kind: str = "theme",
          status: str = "canonical") -> dict:
    return {
        "node_id": node_id, "kind": kind, "name_en": name_en, "name_zh": name_zh,
        "market_scope": "us", "tier": "1", "status": status, "merged_into": None,
        "birth_date": "2026-01-01", "retire_date": None, "identity_epoch": "1",
        "external_ids": None, "provenance": "test", "computed_at": "2026-09-01T00:00:00Z",
        "engine_version": "test", "source_meta": None,
    }


def _edge(edge_id: str, src: str, dst: str, evidence_time: str) -> dict:
    return {
        "edge_id": edge_id, "type": "EXPOSED_TO", "src": src, "dst": dst,
        "valid_from": "2026-01-01", "valid_to": None, "evidence_time": evidence_time,
        "belief_time": "2026-09-01T00:00:00Z", "era": "current", "source_class": "internal",
        "date_provenance": "as_reported", "evidence_refs": None, "confidence_basis": None,
        "economic_share": None, "trading_beta": None, "attention_share": None,
        "economic_share_formula_id": None, "trading_beta_formula_id": None,
        "attention_share_formula_id": None, "economic_share_display": None,
        "trading_beta_display": None, "attention_share_display": None,
        "computed_at": "2026-09-01T00:00:00Z", "engine_version": "test",
    }


def _point_store_at(monkeypatch, store_dir: Path) -> None:
    """Redirect the REAL store readers at a tmp directory. Nothing else is faked:
    nodes_path/edges_path/node_lifecycle_path all derive from store_dir()."""
    monkeypatch.setattr("engine.theme_graph.store.store_dir", lambda: store_dir)


def _render(root: Path, ctx: dict) -> str:
    import scripts.build_state_of_themes as sot

    return sot.render(root, ctx)


def _rp_block(html: str) -> str:
    match = re.search(r'<section class="rp">.*?</section>', html, re.S)
    return match.group(0) if match else ""


def _visible_text(html: str) -> str:
    stripped = re.sub(r"<script\b.*?</script>", " ", html, flags=re.S | re.I)
    stripped = re.sub(r"<style\b.*?</style>", " ", stripped, flags=re.S | re.I)
    stripped = re.sub(r"<[^>]+>", " ", stripped)
    return re.sub(r"\s+", " ", stripped).strip()


def _strip_refusals(html: str) -> str:
    out = html
    for blob in (_REFUSAL_EN, _REFUSAL_ZH, _DETAILS_EN, _DETAILS_ZH):
        out = out.replace(blob, "")
    return out


# ---------------------------------------------------------------------------
# Ordering rule
# ---------------------------------------------------------------------------


def test_orders_by_last_recorded_date_descending():
    from engine.research_priority_ordering import order_items

    items = order_items(
        (
            _te("theme:old", "Old", "旧", "2026-01-01"),
            _te("theme:new", "New", "新", "2026-09-08"),
            _te("theme:mid", "Mid", "中", "2026-06-01"),
        )
    )
    assert [it.node_id for it in items] == [
        "theme:new",
        "theme:mid",
        "theme:old",
    ]


def test_same_date_orders_by_statement_count_descending():
    from engine.research_priority_ordering import order_items

    items = order_items(
        (
            _te("theme:one", "One", "一", "2026-09-08"),
            _te("theme:four", "Four", "四", "2026-09-08", "2026-09-08", "2026-09-08", "2026-09-08"),
            _te("theme:two", "Two", "二", "2026-09-08", "2026-09-08"),
        )
    )
    assert [it.node_id for it in items] == [
        "theme:four",
        "theme:two",
        "theme:one",
    ]
    assert [it.statements_recorded for it in items] == [4, 2, 1]


def test_same_date_and_count_orders_by_name_then_node_id_ascending():
    from engine.research_priority_ordering import order_items

    items = order_items(
        (
            _te("theme:b", "Beta", "乙", "2026-09-08"),
            _te("theme:a2", "Alpha", "甲", "2026-09-08"),
            _te("theme:a1", "Alpha", "甲", "2026-09-08"),
        )
    )
    assert [it.node_id for it in items] == ["theme:a1", "theme:a2", "theme:b"]


def test_ordering_is_invariant_under_input_permutation():
    from engine.research_priority_ordering import order_items

    base = (
        _te("theme:c", "Cee", "丙", "2026-09-01", "2026-09-01"),
        _te("theme:a", "Aee", "甲", "2026-09-08"),
        _te("theme:b", "Bee", "乙", "2026-09-08", "2026-09-08"),
        _te("theme:z", "Zee", "癸"),
    )
    expected = [it.node_id for it in order_items(base)]
    for perm in itertools.permutations(base):
        got = [it.node_id for it in order_items(perm)]
        assert got == expected


def test_positions_are_dense_one_based_and_unique():
    from engine.research_priority_ordering import order_items

    items = order_items(
        (
            _te("theme:a", "A", "甲", "2026-09-08"),
            _te("theme:b", "B", "乙", "2026-09-07"),
            _te("theme:c", "C", "丙"),
        )
    )
    positions = [it.position for it in items]
    assert positions == [1, 2, 3]


def test_undated_themes_form_a_separate_bucket_appended_last():
    from engine.research_priority_ordering import order_items

    items = order_items(
        (
            _te("theme:undated_z", "Zed", "末"),
            _te("theme:dated", "Dated", "有日期", "2026-01-01"),
            _te("theme:undated_a", "Aed", "首"),
        )
    )
    assert [it.node_id for it in items] == [
        "theme:dated",
        "theme:undated_a",
        "theme:undated_z",
    ]
    assert items[0].last_recorded_date == "2026-01-01"
    assert items[1].last_recorded_date is None
    assert items[2].last_recorded_date is None
    assert items[1].statements_recorded == 0
    assert items[2].statements_recorded == 0


def test_malformed_date_is_skipped_not_raised_and_never_becomes_today():
    from engine.research_priority_ordering import order_items

    items = order_items(
        (
            _te(
                "theme:messy",
                "Messy",
                "乱",
                "not-a-date",
                "2026-13-40",
                "",
                "2026-09-08T00:00:00Z",
            ),
        )
    )
    assert len(items) == 1
    assert items[0].last_recorded_date == "2026-09-08"
    assert items[0].statements_recorded == 1


def test_empty_input_returns_empty_tuple():
    from engine.research_priority_ordering import order_items

    assert order_items(()) == ()
    assert order_items([]) == ()


# ---------------------------------------------------------------------------
# Authority ceiling
# ---------------------------------------------------------------------------


def test_no_calibrated_or_probabilistic_field_exists_anywhere_in_payload():
    from engine.research_priority_ordering import FORBIDDEN_PAYLOAD_KEYS, to_payload

    payload = _populated_payload()

    def walk(obj, key=None):
        if isinstance(obj, dict):
            for child_key, value in obj.items():
                assert child_key not in FORBIDDEN_PAYLOAD_KEYS, child_key
                walk(value, child_key)
        elif isinstance(obj, (list, tuple)):
            for value in obj:
                walk(value, key)
        elif type(obj) is int:
            assert key in _ALLOWED_INT_KEYS, key
        elif type(obj) is float:
            assert not (0.0 <= obj <= 1.0), (key, obj)

    walk(payload)


def test_no_calibrated_field_appears_in_rendered_output(tmp_path):
    _copy_templates(tmp_path)
    html = _render(tmp_path, _base_ctx(research_priority=_populated_payload()))
    block = _rp_block(html)
    assert block
    scanned = _strip_refusals(block).lower()
    for token in _FORBIDDEN_RENDER:
        assert token.lower() not in scanned, token


def test_module_never_reads_a_held_column():
    from engine.research_priority_ordering import HELD_COLUMNS

    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    held_assign = None
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == "HELD_COLUMNS":
            held_assign = node
            break
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", None) == "HELD_COLUMNS" for t in node.targets
        ):
            held_assign = node
            break
    assert held_assign is not None
    skip_lines = set(range(held_assign.lineno, held_assign.end_lineno + 1))
    # Docstring of the module plus the comment immediately above HELD_COLUMNS.
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        skip_lines.update(range(tree.body[0].lineno, tree.body[0].end_lineno + 1))

    lines = source.splitlines()
    for i, line in enumerate(lines, start=1):
        if i in skip_lines:
            continue
        stripped = line.split("#", 1)[0]
        for col in HELD_COLUMNS:
            assert col not in stripped, f"{col} at line {i}"

    builder = BUILDER_PATH.read_text(encoding="utf-8")
    tree_b = ast.parse(builder)
    fn = None
    for node in tree_b.body:
        if isinstance(node, ast.FunctionDef) and node.name == "load_research_priority":
            fn = node
            break
    assert fn is not None
    fn_src = ast.get_source_segment(builder, fn) or ""
    for col in HELD_COLUMNS:
        assert col not in fn_src, col


def test_module_does_not_import_or_name_entry_radar_research_priority():
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "entry_radar" not in source
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "entry_radar" not in alias.name
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "entry_radar" not in node.module

    other = RP1_PATH.read_text(encoding="utf-8")
    assert "research_priority_ordering" not in other

    def imported_modules(path: Path) -> set[str]:
        tree_i = ast.parse(path.read_text(encoding="utf-8"))
        names: set[str] = set()
        for node in ast.walk(tree_i):
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module)
        return names

    ours = imported_modules(MODULE_PATH)
    theirs = imported_modules(RP1_PATH)
    assert "engine.entry_radar.research_priority" not in ours
    assert "engine.research_priority_ordering" not in theirs
    assert "engine.entry_radar" not in ours


def test_module_is_pure_no_clock_no_io_no_subprocess():
    source = MODULE_PATH.read_text(encoding="utf-8")
    banned = (
        "datetime.now",
        "datetime.utcnow",
        "time.time",
        "open(",
        "read_text",
        "read_parquet",
        "requests",
        "subprocess",
        "os.environ",
    )
    for token in banned:
        assert token not in source, token


def test_payload_stamps_schema_ordering_rule_and_authority_ceiling():
    from engine.research_priority_ordering import (
        AUTHORITY_CEILING,
        LEDGER_ROW,
        ORDERING_RULE_ID,
        SCHEMA,
        to_payload,
    )

    payload = to_payload((), asof="2026-09-09", state="empty")
    assert payload["schema"] == SCHEMA == "mastermind.research_priority_ordering.v1"
    assert payload["ordering_rule_id"] == ORDERING_RULE_ID
    assert payload["authority_ceiling"] == AUTHORITY_CEILING == "research_priority_only"
    assert payload["ledger_row"] == LEDGER_ROW == "MO-DELTA-006"


def test_page_states_the_ordering_rule_in_one_sentence(tmp_path):
    _copy_templates(tmp_path)
    html = _render(tmp_path, _base_ctx(research_priority=_populated_payload()))
    block = _rp_block(html)
    assert _RULE_EN in block
    assert _RULE_ZH in block


def test_page_states_that_position_is_not_a_score(tmp_path):
    _copy_templates(tmp_path)
    html = _render(tmp_path, _base_ctx(research_priority=_populated_payload()))
    block = _rp_block(html)
    assert _REFUSAL_EN in block
    assert _REFUSAL_ZH in block


# ---------------------------------------------------------------------------
# Honest nulls and tolerance
# ---------------------------------------------------------------------------


def test_unavailable_payload_renders_the_unavailable_line_not_a_dash(tmp_path):
    """Template test (renamed from test_missing_store_...): it renders a hand-built
    payload and asserts the copy. The STORE conditions are exercised end to end by
    test_missing_store_files_load_as_unavailable and its siblings below."""
    from engine.research_priority_ordering import to_payload

    _copy_templates(tmp_path)
    payload = to_payload((), asof=None, state="unavailable")
    html = _render(tmp_path, _base_ctx(research_priority=payload))
    block = _rp_block(html)
    assert "The evidence record could not be read, so this list is not shown." in block
    assert "无法读取证据记录，因此这份清单暂不显示。" in block
    assert "<ol" not in block
    visible = _visible_text(block)
    assert "—" not in visible
    assert re.search(r"\b0\b", visible) is None
    assert re.search(r"\bunavailable\b", visible, re.I) is None


def test_empty_payload_renders_the_empty_line_not_a_dash(tmp_path):
    """Template test (renamed from test_empty_store_...) — see the note above."""
    from engine.research_priority_ordering import to_payload

    _copy_templates(tmp_path)
    payload = to_payload((), asof=None, state="empty")
    html = _render(tmp_path, _base_ctx(research_priority=payload))
    block = _rp_block(html)
    assert "We have not recorded new evidence for any theme yet." in block
    assert "目前还没有记录到任何主题的新证据。" in block
    assert "<ol" not in block
    visible = _visible_text(block)
    assert "—" not in visible
    assert re.search(r"\b0\b", visible) is None
    assert re.search(r"\bempty\b", visible, re.I) is None


def test_loader_never_raises_on_a_corrupt_store(tmp_path, monkeypatch):
    import scripts.build_state_of_themes as sot

    _copy_templates(tmp_path)
    (tmp_path / "site" / "neuralwebdata").mkdir(parents=True)
    (tmp_path / "site" / "neuralwebdata" / "theme_state.json").write_text(
        json.dumps({"as_of": "2026-09-09", "n_themes": 1, "themes": [{"theme_id": "x"}]}),
        encoding="utf-8",
    )

    def _boom(*, current=True, latest_belief=True):
        raise RuntimeError("corrupt store")

    monkeypatch.setattr("engine.theme_graph.store.read_nodes", _boom)
    monkeypatch.setattr("engine.theme_graph.store.read_edges", _boom)

    payload = sot.load_research_priority(tmp_path)
    assert payload["state"] == "unavailable"
    html = _render(tmp_path, _base_ctx(research_priority=payload, themes=[{"theme_id": "x"}]))
    assert "<!DOCTYPE html>" in html
    assert "The evidence record could not be read" in html


def test_missing_store_files_load_as_unavailable(tmp_path, monkeypatch):
    """No parquet on disk -> 'unavailable'. The distinction §2.4 draws is the point:
    store._read returns an EMPTY frame for a missing file, so a loader that trusts
    read_nodes/read_edges would say 'empty' about a record it never opened."""
    import scripts.build_state_of_themes as sot

    pytest.importorskip("pandas")
    _point_store_at(monkeypatch, tmp_path / "theme_graph")
    payload = sot.load_research_priority(tmp_path)
    assert payload["state"] == "unavailable"
    assert payload["items"] == []
    assert payload["n_total"] == 0
    assert payload["asof"] is None


def test_corrupt_parquet_loads_as_unavailable(tmp_path, monkeypatch):
    """A truncated/garbage parquet is unreadable, not empty."""
    import scripts.build_state_of_themes as sot

    pytest.importorskip("pandas")
    store_dir = tmp_path / "theme_graph"
    store_dir.mkdir(parents=True)
    (store_dir / "nodes.parquet").write_bytes(b"PAR1 this is not a parquet file")
    (store_dir / "edges.parquet").write_bytes(b"PAR1 this is not a parquet file")
    _point_store_at(monkeypatch, store_dir)
    payload = sot.load_research_priority(tmp_path)
    assert payload["state"] == "unavailable"
    assert payload["items"] == []
    assert payload["asof"] is None


def test_readable_store_with_no_theme_edges_loads_as_empty(tmp_path, monkeypatch):
    """Readable parquet, zero current-view edges touching a theme -> 'empty'."""
    import scripts.build_state_of_themes as sot

    store_dir = tmp_path / "theme_graph"
    _write_theme_store(
        store_dir,
        nodes=[_node("theme:solar", "Solar", "太阳能")],
        edges=[_edge("e1", "company:acme", "sector:utilities", "2026-07-09")],
    )
    _point_store_at(monkeypatch, store_dir)
    payload = sot.load_research_priority(tmp_path)
    assert payload["state"] == "empty"
    assert payload["items"] == []
    assert payload["n_total"] == 0
    assert payload["asof"] is None


def test_populated_store_loads_as_ok_with_asof_from_the_evidence_rows(tmp_path, monkeypatch):
    """A populated store -> 'ok', and asof is the newest evidence_time actually read —
    never a page snapshot clock (seat ruling R1)."""
    import scripts.build_state_of_themes as sot

    store_dir = tmp_path / "theme_graph"
    _write_theme_store(
        store_dir,
        nodes=[
            _node("theme:solar", "Solar", "太阳能"),
            _node("theme:copper", "Copper", "铜"),
        ],
        edges=[
            _edge("e1", "company:acme", "theme:solar", "2026-07-09"),
            _edge("e2", "company:brox", "theme:solar", "2026-07-09"),
            _edge("e3", "company:crux", "theme:copper", "2026-06-30"),
        ],
    )
    _point_store_at(monkeypatch, store_dir)
    payload = sot.load_research_priority(tmp_path)
    assert payload["state"] == "ok"
    assert payload["n_total"] == 2
    assert payload["asof"] == "2026-07-09"
    assert [item["node_id"] for item in payload["items"]] == ["theme:solar", "theme:copper"]
    assert payload["items"][0]["statements_recorded"] == 2


def test_retired_and_merged_themes_are_excluded_from_the_order_and_the_total(
    tmp_path, monkeypatch
):
    """store.read_nodes(current=True) overlays lifecycle but REMOVES no row; an
    active-only population must filter on status itself (store.py:246-254)."""
    import scripts.build_state_of_themes as sot

    store_dir = tmp_path / "theme_graph"
    _write_theme_store(
        store_dir,
        nodes=[
            _node("theme:solar", "Solar", "太阳能"),
            _node("theme:dead", "Old story", "旧主题", status="retired"),
            _node("theme:gone", "Folded story", "并入主题", status="merged"),
        ],
        edges=[
            _edge("e1", "company:acme", "theme:solar", "2026-07-09"),
            _edge("e2", "company:brox", "theme:dead", "2026-08-31"),
            _edge("e3", "company:crux", "theme:gone", "2026-08-30"),
        ],
    )
    _point_store_at(monkeypatch, store_dir)
    payload = sot.load_research_priority(tmp_path)
    assert payload["state"] == "ok"
    assert payload["n_total"] == 1
    assert [item["node_id"] for item in payload["items"]] == ["theme:solar"]
    # The retired theme carried the newest date; it must not set the horizon either.
    assert payload["asof"] == "2026-07-09"


def test_asof_never_outruns_the_newest_row_the_page_shows(tmp_path):
    """The closing line and the newest row are measured from the same population."""
    from engine.research_priority_ordering import max_recorded_date

    _copy_templates(tmp_path)
    payload = _populated_payload()
    newest = max(
        item["last_recorded_date"]
        for item in payload["items"]
        if item["last_recorded_date"]
    )
    assert payload["asof"] == newest == "2026-09-08"
    assert max_recorded_date(()) is None
    block = _rp_block(_render(tmp_path, _base_ctx(research_priority=payload)))
    assert "Evidence recorded up to 8 September 2026" in block
    assert "证据记录截至 2026年9月8日" in block


def test_page_omits_the_asof_line_when_no_evidence_date_is_known(tmp_path):
    """No dated evidence -> the line is omitted, never printed with a dash."""
    from engine.research_priority_ordering import PriorityItem, to_payload

    _copy_templates(tmp_path)
    payload = to_payload(
        (PriorityItem(1, "theme:quiet", "Quiet story", "安静主题", None, 0),),
        asof=None,
        state="ok",
    )
    block = _rp_block(_render(tmp_path, _base_ctx(research_priority=payload)))
    assert block
    assert "Evidence recorded up to" not in block
    assert "证据记录截至" not in block
    # …and no lone-dash placeholder is left standing in its place.
    assert re.search(r">\s*—\s*<", block) is None


def test_page_renders_unchanged_when_research_priority_is_absent_from_ctx(tmp_path):
    _copy_templates(tmp_path)
    ctx = _base_ctx()
    assert "research_priority" not in ctx
    html = _render(tmp_path, ctx)
    assert 'class="rp"' not in html
    assert "What to look at first" not in html
    assert "先看哪些主题" not in html
    html_again = _render(tmp_path, ctx)
    assert html == html_again


# ---------------------------------------------------------------------------
# Copy and product law
# ---------------------------------------------------------------------------


def test_every_new_label_has_both_en_and_zh(tmp_path):
    from engine.research_priority_ordering import to_payload

    _copy_templates(tmp_path)
    ok_html = _rp_block(_render(tmp_path, _base_ctx(research_priority=_populated_payload())))
    empty_html = _rp_block(
        _render(
            tmp_path,
            _base_ctx(research_priority=to_payload((), asof="2026-09-09", state="empty")),
        )
    )
    unavail_html = _rp_block(
        _render(
            tmp_path,
            _base_ctx(
                research_priority=to_payload((), asof=None, state="unavailable")
            ),
        )
    )
    # 18 > MAX_ITEMS, so rp.more is in the rendered HTML and not merely in the payload.
    more_html = _rp_block(
        _render(tmp_path, _base_ctx(research_priority=_truncated_payload(18)))
    )
    pairs = [
        ("What to look at first", "先看哪些主题"),
        (
            "Start at the top. The list runs by the date something was last written down about each theme, newest first; themes written down on the same day run by how many statements were recorded that day. It is not where the best idea is.",
            "从最上面开始看。这份清单按每个主题最后一次被记录下内容的日期排列，最新的在前；同一天记录的主题，按当天记录的条数排列。它并不是最好的主意所在。",
        ),
        (
            "Showing 12 of 18 themes in that order.",
            "共 18 个主题，按该顺序显示其中 12 个。",
        ),
        (_RULE_EN, _RULE_ZH),
        (_REFUSAL_EN, _REFUSAL_ZH),
        ("New evidence recorded", "记录到新证据"),
        ("1 statement that day", "当天 1 条"),
        ("4 statements that day", "当天 4 条"),
        ("No dated evidence yet", "尚无带日期的证据"),
        (
            "These themes are tracked, but nothing we hold about them carries a date, so they cannot take a place in the order above.",
            "这些主题在追踪范围内，但我们掌握的内容都没有日期，因此无法排入上面的顺序。",
        ),
        ("How this order is made", "这个顺序是怎么排的"),
        (_DETAILS_EN, _DETAILS_ZH),
        ("Evidence recorded up to", "证据记录截至"),
        ("We have not recorded new evidence for any theme yet.", "目前还没有记录到任何主题的新证据。"),
        (
            "The evidence record could not be read, so this list is not shown.",
            "无法读取证据记录，因此这份清单暂不显示。",
        ),
    ]
    for en, zh in pairs:
        haystack = ok_html + empty_html + unavail_html + more_html
        assert en in haystack, en
        assert zh in haystack, zh


def test_truncation_line_states_the_same_criterion_as_the_order(tmp_path):
    """rp.more must not claim a recency selection the tie-break actually made.

    Every item here shares one date, so 'most recently updated' would be false of
    all 18; the head was chosen by the ordering key, and the sentence says so.
    """
    _copy_templates(tmp_path)
    block = _rp_block(_render(tmp_path, _base_ctx(research_priority=_truncated_payload(18))))
    assert block
    assert "Showing 12 of 18 themes in that order." in block
    assert "共 18 个主题，按该顺序显示其中 12 个。" in block
    assert "most recently updated" not in block
    assert "显示最近更新的" not in block


def test_truncation_line_counts_only_the_dated_rows(tmp_path):
    """An undated theme is rendered under its own heading and takes no place in the
    order, so it may not be counted among the themes shown 'in that order'."""
    from engine.research_priority_ordering import (
        PriorityItem,
        max_recorded_date,
        to_payload,
    )

    _copy_templates(tmp_path)
    items = tuple(
        PriorityItem(i + 1, f"theme:n{i:02d}", f"Name {i:02d}", f"名{i:02d}",
                     "2026-09-08", 1)
        for i in range(11)
    ) + (
        PriorityItem(12, "theme:quiet", "Quiet story", "安静主题", None, 0),
    ) + tuple(
        PriorityItem(i + 13, f"theme:m{i:02d}", f"Later {i:02d}", f"后{i:02d}",
                     "2026-09-07", 1)
        for i in range(6)
    )
    payload = to_payload(items, asof=max_recorded_date(items), state="ok")
    assert payload["n_total"] == 18
    block = _rp_block(_render(tmp_path, _base_ctx(research_priority=payload)))
    # 12 payload rows, one of them undated -> 11 sit in the order.
    assert "Showing 11 of 18 themes in that order." in block
    assert "No dated evidence yet" in block


def test_no_machine_text_in_the_rendered_block(tmp_path):
    _copy_templates(tmp_path)
    html = _render(tmp_path, _base_ctx(research_priority=_populated_payload()))
    block = _rp_block(html)
    visible = _visible_text(block)
    assert "theme:power_grid" not in block
    assert "theme:copper" not in visible
    assert re.search(r"\d{4}-\d{2}-\d{2}T", block) is None
    assert re.search(r"\b(ok|empty|unavailable)\b", visible, re.I) is None


def test_zh_copy_never_uses_shenbao():
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    # Only the new section is in scope; the word must not appear anywhere new.
    assert "申报" not in template
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "申报" not in source


def test_no_validated_claim_in_the_new_block(tmp_path):
    _copy_templates(tmp_path)
    html = _render(tmp_path, _base_ctx(research_priority=_populated_payload()))
    block = _rp_block(html).lower()
    for token in ("validated", "已验证", "经验证", "经过验证"):
        assert token not in block


def test_navlinks_template_carries_no_research_priority_markup():
    text = NAVLINKS_PATH.read_text(encoding="utf-8")
    assert "rp-" not in text
    assert "research_priority" not in text


# ---------------------------------------------------------------------------
# Artifact
# ---------------------------------------------------------------------------


def test_artifact_round_trips_through_json_and_is_ascii_safe():
    payload = _populated_payload()
    dumped = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    loaded = json.loads(dumped)
    assert loaded == payload
    # Round-trip also holds when ASCII-escaped.
    dumped_ascii = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    assert json.loads(dumped_ascii) == payload


def test_artifact_truncates_to_max_items_and_discloses_the_total():
    from engine.research_priority_ordering import MAX_ITEMS

    payload = _truncated_payload(18)
    assert payload["max_items"] == MAX_ITEMS == 12
    assert payload["asof"] == "2026-09-08"
    assert payload["n_total"] == 18
    assert len(payload["items"]) == 12
    assert payload["items"][0]["position"] == 1
    assert payload["items"][-1]["position"] == 12
