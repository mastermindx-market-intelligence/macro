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
_RULE_EN = "When the date and that day's count match, the list runs by name."
_RULE_ZH = "日期和当天条数都相同时，按名称排列。"
_STANCE_EN = (
    "Start at the top. The list runs by the date something was last written down "
    "about each theme, newest first; themes written down on the same day run by "
    "how many statements were recorded that day. It is not where the best idea is."
)
_STANCE_ZH = (
    "从最上面开始看。这份清单按每个主题最后一次被记录下内容的日期排列，最新的在前；"
    "同一天记录的主题，按当天记录的条数排列。排在最上面的并不代表它是最好的想法。"
)
_TRUNC_EN = "Showing the 12 most recently updated of {n} dated themes."
_TRUNC_ZH = "共 {n} 个有日期的主题，显示最近更新的 12 个。"
_NO_ORDER_EN = (
    "No tracked theme carries a dated entry yet, so there is no reading order to show."
)
_NO_ORDER_ZH = "目前没有任何主题带有日期记录，因此暂时没有可显示的阅读顺序。"
_UNDATED_COUNT_EN_ONE = "1 tracked theme has no dated entry yet."
_UNDATED_COUNT_EN_MANY = "{k} tracked themes have no dated entry yet."
_UNDATED_COUNT_ZH = "另有 {k} 个主题尚无带日期的记录。"


def _undated_count_en(k: int) -> str:
    """Seat ruling R1: the EN count carries a singular branch, as the per-row
    statement count at the same template already does. The ZH half is invariant."""
    return _UNDATED_COUNT_EN_ONE if k == 1 else _UNDATED_COUNT_EN_MANY.format(k=k)

_ALLOWED_INT_KEYS = frozenset(
    {"position", "statements_recorded", "n_total", "n_dated", "n_undated", "max_items"}
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


def _payload_from_themes(themes, *, state: str = "ok"):
    """Every ordering-dependent render test goes through the producer."""
    from engine.research_priority_ordering import (
        max_recorded_date,
        order_items,
        to_payload,
    )

    items = order_items(themes)
    return to_payload(items, asof=max_recorded_date(items), state=state)


def _populated_payload():
    return _payload_from_themes(
        (
            _te("theme:power_grid", "Power grid", "电网",
                "2026-09-08", "2026-09-08", "2026-09-08", "2026-09-08"),
            _te("theme:copper", "Copper", "铜", "2026-09-08"),
            _te("theme:alpha", "Alpha", "阿尔法", "2026-09-01", "2026-09-01"),
            _te("theme:undated_a", "Quiet story", "安静主题"),
        )
    )


def _truncated_payload(n: int = 18):
    """A payload whose dated count exceeds MAX_ITEMS, so the truncation line renders."""
    themes = tuple(
        _te(f"theme:n{i:02d}", f"Name {i:02d}", f"名{i:02d}", "2026-09-08")
        for i in range(n)
    )
    return _payload_from_themes(themes)


def _eleven_dated_seven_undated():
    dated = tuple(
        _te(
            f"theme:d{i:02d}",
            f"Dated {i:02d}",
            f"有日{i:02d}",
            f"2026-09-{8 - i:02d}" if i < 8 else "2026-08-30",
        )
        for i in range(11)
    )
    undated = tuple(
        _te(f"theme:u{i:02d}", f"Quiet {i:02d}", f"安静{i:02d}")
        for i in range(7)
    )
    return dated + undated


def _fifteen_dated_three_undated():
    dated = tuple(
        _te(
            f"theme:d{i:02d}",
            f"Dated {i:02d}",
            f"有日{i:02d}",
            f"2026-09-{15 - i:02d}" if i < 15 else "2026-08-01",
        )
        for i in range(15)
    )
    undated = tuple(
        _te(f"theme:u{i:02d}", f"Quiet {i:02d}", f"安静{i:02d}")
        for i in range(3)
    )
    return dated + undated


def _write_theme_store(store_dir: Path, nodes: list[dict], edges: list[dict],
                       lifecycle: list[dict] | None = None) -> None:
    """Write a REAL parquet store, so the loader meets the real read conditions."""
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    from engine.theme_graph.store import (
        EDGE_COLUMNS,
        NODE_COLUMNS,
        NODE_LIFECYCLE_COLUMNS,
    )

    store_dir.mkdir(parents=True, exist_ok=True)
    node_frame = pd.DataFrame(nodes, columns=list(NODE_COLUMNS))
    edge_frame = pd.DataFrame(edges, columns=list(EDGE_COLUMNS))
    life_frame = pd.DataFrame(
        lifecycle or [], columns=list(NODE_LIFECYCLE_COLUMNS)
    )
    node_frame.to_parquet(store_dir / "nodes.parquet", index=False)
    edge_frame.to_parquet(store_dir / "edges.parquet", index=False)
    life_frame.to_parquet(store_dir / "node_lifecycle.parquet", index=False)


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
    assert [it.position for it in items if it.last_recorded_date] == [1, 2]
    assert all(it.position is None for it in items if not it.last_recorded_date)


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
    assert items[1].position is None
    assert items[2].position is None
    assert items[1].statements_recorded == 0
    assert items[2].statements_recorded == 0


def test_order_items_never_emits_an_undated_item_before_a_dated_one():
    from engine.research_priority_ordering import order_items

    themes = (
        _te("theme:undated_z", "Zed", "末"),
        _te("theme:dated_old", "Old", "旧", "2026-01-01"),
        _te("theme:undated_a", "Aed", "首"),
        _te("theme:dated_new", "New", "新", "2026-09-08"),
    )
    for perm in itertools.permutations(themes):
        items = order_items(perm)
        seen_undated = False
        for item in items:
            if item.last_recorded_date is None:
                seen_undated = True
                assert item.position is None
            else:
                assert not seen_undated
                assert item.position is not None


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


def test_missing_store_renders_the_unavailable_line_not_a_dash(tmp_path):
    """§2.8 frozen name: unavailable copy, no dash, no list."""
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


def test_empty_store_renders_the_empty_line_not_a_dash(tmp_path):
    """§2.8 frozen name: empty copy, no dash, no list."""
    from engine.research_priority_ordering import to_payload

    _copy_templates(tmp_path)
    payload = to_payload((), asof=None, state="empty")
    html = _render(tmp_path, _base_ctx(research_priority=payload))
    block = _rp_block(html)
    assert "We have not recorded new evidence for any theme yet." in block
    assert "目前还没有记录到任何主题的新证据。" in block
    # Seat ruling R7l: plain wording, not release-engineering vocabulary.
    assert "This list fills in after the next update." in block
    assert "下一次更新后，这里会显示内容。" in block
    assert "nightly build" not in block
    assert "夜间构建" not in block
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


def test_import_failure_fallback_matches_the_to_payload_key_set(tmp_path):
    """Seat ruling R7a: the rp-is-None branch (the module import itself failed)
    emits exactly the key set to_payload emits — n_dated and n_undated included —
    so site/basketdata/research_priority.json carries one schema, not two."""
    import scripts.build_state_of_themes as sot
    from engine.research_priority_ordering import to_payload

    produced = to_payload((), asof=None, state="unavailable")
    fallback = sot._research_priority_unavailable(None)
    assert set(fallback) == set(produced)
    assert fallback == produced
    assert fallback["state"] == "unavailable"
    assert fallback["n_dated"] == 0
    assert fallback["n_undated"] == 0
    # And the page still renders the honest unavailable line from it.
    _copy_templates(tmp_path)
    block = _rp_block(_render(tmp_path, _base_ctx(research_priority=fallback)))
    assert "The evidence record could not be read" in block
    assert "无法读取证据记录" in block


def test_corrupt_parquet_loads_as_unavailable(tmp_path, monkeypatch):
    """A truncated/garbage parquet is unreadable, not empty."""
    import scripts.build_state_of_themes as sot

    pytest.importorskip("pandas")
    store_dir = tmp_path / "theme_graph"
    store_dir.mkdir(parents=True)
    (store_dir / "nodes.parquet").write_bytes(b"PAR1 this is not a parquet file")
    (store_dir / "edges.parquet").write_bytes(b"PAR1 this is not a parquet file")
    (store_dir / "node_lifecycle.parquet").write_bytes(b"PAR1 this is not a parquet file")
    _point_store_at(monkeypatch, store_dir)
    payload = sot.load_research_priority(tmp_path)
    assert payload["state"] == "unavailable"
    assert payload["items"] == []
    assert payload["asof"] is None


def test_corrupt_node_lifecycle_loads_as_unavailable(tmp_path, monkeypatch):
    """node_lifecycle.parquet is on the §2.4 readability probe; garbage is unavailable."""
    import scripts.build_state_of_themes as sot

    store_dir = tmp_path / "theme_graph"
    _write_theme_store(
        store_dir,
        nodes=[_node("theme:solar", "Solar", "太阳能")],
        edges=[_edge("e1", "company:acme", "theme:solar", "2026-07-09")],
    )
    (store_dir / "node_lifecycle.parquet").write_bytes(b"PAR1 this is not a parquet file")
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


def test_to_payload_derives_asof_from_items_so_the_caller_cannot_rebind_it():
    from engine.research_priority_ordering import (
        max_recorded_date,
        order_items,
        to_payload,
    )

    items = order_items((_te("theme:solar", "Solar", "太阳能", "2026-07-09"),))
    payload = to_payload(items, asof="2099-01-01", state="ok")
    assert payload["asof"] == max_recorded_date(items) == "2026-07-09"
    assert payload["asof"] != "2099-01-01"


def test_compose_binds_asof_from_the_payload_items(tmp_path, monkeypatch):
    """compose() cannot re-bind asof: to_payload derives it from the items."""
    import scripts.build_state_of_themes as sot
    from engine.research_priority_ordering import max_recorded_date, order_items

    nwd = tmp_path / "site" / "neuralwebdata"
    nwd.mkdir(parents=True)
    nwd.joinpath("theme_state.json").write_text(
        json.dumps(
            {
                "as_of": "2026-09-09",
                "n_themes": 1,
                "themes": [{"theme_id": "theme:solar"}],
            }
        ),
        encoding="utf-8",
    )
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
    ctx = sot.compose(tmp_path)
    payload = ctx["research_priority"]
    assert payload["state"] == "ok"
    assert payload["asof"] == "2026-07-09"
    assert payload["asof"] != ctx["as_of"]
    reconstructed = order_items(
        (
            _te("theme:solar", "Solar", "太阳能", "2026-07-09", "2026-07-09"),
            _te("theme:copper", "Copper", "铜", "2026-06-30"),
        )
    )
    assert payload["asof"] == max_recorded_date(reconstructed)
    dated = [item["last_recorded_date"] for item in payload["items"] if item["last_recorded_date"]]
    assert payload["asof"] == max(dated)


def test_page_omits_the_asof_line_when_no_evidence_date_is_known(tmp_path):
    """No dated evidence -> the line is omitted, never printed with a dash.

    Seat ruling R2: this payload is state 'ok' with n_dated == 0, so the same
    render must also withhold the stance and print the honest sentence in its
    place. Asserted here, not only in the dedicated R2 test below.
    """
    _copy_templates(tmp_path)
    payload = _payload_from_themes((_te("theme:quiet", "Quiet story", "安静主题"),))
    assert payload["state"] == "ok"
    assert payload["n_dated"] == 0
    block = _rp_block(_render(tmp_path, _base_ctx(research_priority=payload)))
    assert block
    assert "Evidence recorded up to" not in block
    assert "证据记录截至" not in block
    # …and no lone-dash placeholder is left standing in its place.
    assert re.search(r">\s*—\s*<", block) is None
    assert _STANCE_EN not in block
    assert _STANCE_ZH not in block
    assert _NO_ORDER_EN in block
    assert _NO_ORDER_ZH in block


def test_all_undated_population_shows_no_order_and_no_stance(tmp_path):
    """Seat ruling R2: state 'ok' with zero dated themes never prints the stance,
    the tie-break sentence or an empty <ol>. It prints the honest sentence and
    then every undated name."""
    _copy_templates(tmp_path)
    themes = tuple(
        _te(f"theme:u{i:02d}", f"Quiet {i:02d}", f"安静{i:02d}") for i in range(4)
    )
    payload = _payload_from_themes(themes)
    assert payload["state"] == "ok"
    assert payload["n_dated"] == 0
    assert payload["n_undated"] == 4
    assert payload["asof"] is None
    block = _rp_block(_render(tmp_path, _base_ctx(research_priority=payload)))
    assert block
    # The stance, the tie-break rule and the ordered list are all withheld.
    assert _STANCE_EN not in block
    assert _STANCE_ZH not in block
    assert _RULE_EN not in block
    assert _RULE_ZH not in block
    head = block.split('class="rp-undated"', 1)[0]
    assert "<ol" not in head
    assert 'class="rp-pos"' not in block
    # The honest sentence stands in their place, in both languages…
    assert _NO_ORDER_EN in block
    assert _NO_ORDER_ZH in block
    # …and every undated theme is still named on screen.
    undated_html = block.split('class="rp-undated"', 1)[1]
    for i in range(4):
        assert f"Quiet {i:02d}" in undated_html
        assert f"安静{i:02d}" in undated_html
    assert _undated_count_en(4) in block
    assert _UNDATED_COUNT_ZH.format(k=4) in block


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
    # state 'ok' with zero dated themes (seat ruling R2) is a rendered state too.
    no_order_html = _rp_block(
        _render(
            tmp_path,
            _base_ctx(
                research_priority=_payload_from_themes(
                    (_te("theme:quiet", "Quiet story", "安静主题"),)
                )
            ),
        )
    )
    pairs = [
        ("What to look at first", "先看哪些主题"),
        (_STANCE_EN, _STANCE_ZH),
        (
            _TRUNC_EN.format(n=18),
            _TRUNC_ZH.format(n=18),
        ),
        (_RULE_EN, _RULE_ZH),
        (_REFUSAL_EN, _REFUSAL_ZH),
        ("New evidence recorded", "记录到新证据"),
        ("1 statement that day", "当天有 1 条记录"),
        ("4 statements that day", "当天有 4 条记录"),
        ("No dated evidence yet", "尚无带日期的证据"),
        (
            "These themes are tracked, but nothing we hold about them carries a date, so they cannot take a place in the order above.",
            "这些主题在追踪范围内，但我们掌握的内容都没有日期，因此无法排入上面的顺序。",
        ),
        ("How this order is made", "这个顺序是怎么排的"),
        (_DETAILS_EN, _DETAILS_ZH),
        ("Evidence recorded up to", "证据记录截至"),
        ("We have not recorded new evidence for any theme yet.", "目前还没有记录到任何主题的新证据。"),
        ("This list fills in after the next update.", "下一次更新后，这里会显示内容。"),
        (
            "The evidence record could not be read, so this list is not shown.",
            "无法读取证据记录，因此这份清单暂不显示。",
        ),
        (
            _undated_count_en(1),
            _UNDATED_COUNT_ZH.format(k=1),
        ),
        (_NO_ORDER_EN, _NO_ORDER_ZH),
    ]
    for en, zh in pairs:
        haystack = ok_html + empty_html + unavail_html + more_html + no_order_html
        assert en in haystack, en
        assert zh in haystack, zh


def test_truncation_line_states_the_same_criterion_as_the_order(tmp_path):
    """Seat R1 frozen truncation copy counts dated themes only."""
    _copy_templates(tmp_path)
    block = _rp_block(_render(tmp_path, _base_ctx(research_priority=_truncated_payload(18))))
    assert block
    assert _TRUNC_EN.format(n=18) in block
    assert _TRUNC_ZH.format(n=18) in block
    assert "in that order" not in block
    assert "按该顺序显示其中" not in block


def test_truncation_sentence_follows_the_payload_max_items(tmp_path, monkeypatch):
    """Seat ruling R7e: the sentence prints research_priority.max_items, never a
    literal 12. Move MAX_ITEMS and the copy must move with it, in EN and ZH."""
    import engine.research_priority_ordering as rp_mod

    _copy_templates(tmp_path)
    monkeypatch.setattr(rp_mod, "MAX_ITEMS", 9)
    payload = _payload_from_themes(
        tuple(
            _te(f"theme:d{i:02d}", f"Dated {i:02d}", f"有日{i:02d}", "2026-09-08")
            for i in range(11)
        )
    )
    assert payload["max_items"] == 9
    assert payload["n_dated"] == 11
    assert len(payload["items"]) == 9
    block = _rp_block(_render(tmp_path, _base_ctx(research_priority=payload)))
    assert "Showing the 9 most recently updated of 11 dated themes." in block
    assert "共 11 个有日期的主题，显示最近更新的 9 个。" in block
    assert "Showing the 12" not in block
    assert "显示最近更新的 12 个" not in block


def test_eleven_dated_and_seven_undated_shows_every_name_and_no_truncation(tmp_path):
    """11 dated + 7 undated: no truncation line; 11 numbered rows; 7 undated names."""
    _copy_templates(tmp_path)
    payload = _payload_from_themes(_eleven_dated_seven_undated())
    assert payload["n_dated"] == 11
    assert payload["n_undated"] == 7
    assert payload["n_total"] == 18
    assert len([i for i in payload["items"] if i["last_recorded_date"]]) == 11
    assert len([i for i in payload["items"] if not i["last_recorded_date"]]) == 7
    block = _rp_block(_render(tmp_path, _base_ctx(research_priority=payload)))
    assert _TRUNC_EN.format(n=11) not in block
    assert _TRUNC_ZH.format(n=11) not in block
    assert "Showing the 12 most recently updated" not in block
    assert "显示最近更新的 12 个" not in block
    assert _undated_count_en(7) in block
    assert _UNDATED_COUNT_ZH.format(k=7) in block
    numbered = re.findall(
        r'<span class="rp-pos">(\d+)\.</span>',
        block.split('class="rp-undated"', 1)[0],
    )
    assert numbered == [str(i) for i in range(1, 12)]
    undated_html = block.split('class="rp-undated"', 1)[1]
    assert 'class="rp-pos"' not in undated_html
    for i in range(11):
        assert f"Dated {i:02d}" in block
        assert f"有日{i:02d}" in block
    for i in range(7):
        assert f"Quiet {i:02d}" in undated_html
        assert f"安静{i:02d}" in undated_html


def test_fifteen_dated_and_three_undated_truncates_dated_and_lists_every_undated(
    tmp_path,
):
    """15 dated + 3 undated: truncation names 12 of 15; 3 undated names."""
    _copy_templates(tmp_path)
    payload = _payload_from_themes(_fifteen_dated_three_undated())
    assert payload["n_dated"] == 15
    assert payload["n_undated"] == 3
    assert len([i for i in payload["items"] if i["last_recorded_date"]]) == 12
    assert len([i for i in payload["items"] if not i["last_recorded_date"]]) == 3
    block = _rp_block(_render(tmp_path, _base_ctx(research_priority=payload)))
    assert _TRUNC_EN.format(n=15) in block
    assert _TRUNC_ZH.format(n=15) in block
    assert _undated_count_en(3) in block
    assert _UNDATED_COUNT_ZH.format(k=3) in block
    numbered = re.findall(
        r'<span class="rp-pos">(\d+)\.</span>',
        block.split('class="rp-undated"', 1)[0],
    )
    assert numbered == [str(i) for i in range(1, 13)]
    undated_html = block.split('class="rp-undated"', 1)[1]
    assert 'class="rp-pos"' not in undated_html
    shown_dated = [i for i in payload["items"] if i["last_recorded_date"]]
    hidden_dated = [
        theme
        for theme in _fifteen_dated_three_undated()
        if theme.recorded_dates
        and theme.node_id not in {item["node_id"] for item in shown_dated}
    ]
    assert len(hidden_dated) == 3
    for item in shown_dated:
        assert item["name_en"] in block
        assert item["name_zh"] in block
    for theme in hidden_dated:
        assert theme.name_en not in block
        assert theme.name_zh not in block
    for i in range(3):
        assert f"Quiet {i:02d}" in undated_html
        assert f"安静{i:02d}" in undated_html


def test_undated_count_line_is_singular_for_one_undated_theme(tmp_path):
    """Seat ruling R1: n_undated == 1 reads "1 tracked theme has", never "themes have"."""
    _copy_templates(tmp_path)
    payload = _payload_from_themes(
        (
            _te("theme:d", "Dated one", "有日一", "2026-09-08"),
            _te("theme:u", "Quiet one", "安静一"),
        )
    )
    assert payload["n_undated"] == 1
    block = _rp_block(_render(tmp_path, _base_ctx(research_priority=payload)))
    assert "1 tracked theme has no dated entry yet." in block
    assert "1 tracked themes have no dated entry yet." not in block
    assert _UNDATED_COUNT_ZH.format(k=1) in block


def test_undated_count_line_is_plural_for_two_undated_themes(tmp_path):
    """Seat ruling R1: n_undated == 2 keeps the plural verb and noun."""
    _copy_templates(tmp_path)
    payload = _payload_from_themes(
        (
            _te("theme:d", "Dated one", "有日一", "2026-09-08"),
            _te("theme:u1", "Quiet one", "安静一"),
            _te("theme:u2", "Quiet two", "安静二"),
        )
    )
    assert payload["n_undated"] == 2
    block = _rp_block(_render(tmp_path, _base_ctx(research_priority=payload)))
    assert "2 tracked themes have no dated entry yet." in block
    assert "2 tracked theme has no dated entry yet." not in block
    assert _UNDATED_COUNT_ZH.format(k=2) in block


def test_undated_rows_carry_no_ordinal_in_payload_or_template(tmp_path):
    _copy_templates(tmp_path)
    payload = _populated_payload()
    undated = [item for item in payload["items"] if not item["last_recorded_date"]]
    assert undated
    assert all(item["position"] is None for item in undated)
    dated = [item for item in payload["items"] if item["last_recorded_date"]]
    assert [item["position"] for item in dated] == list(range(1, len(dated) + 1))
    block = _rp_block(_render(tmp_path, _base_ctx(research_priority=payload)))
    undated_html = block.split('class="rp-undated"', 1)[1]
    assert 'class="rp-pos"' not in undated_html
    assert "Quiet story" in undated_html
    assert "4." not in undated_html


def test_store_sourced_theme_names_render_in_a_plain_lang_span(tmp_path):
    _copy_templates(tmp_path)
    payload = _populated_payload()
    block = _rp_block(_render(tmp_path, _base_ctx(research_priority=payload)))
    assert '<span class="l-en" lang="en">Power grid</span>' in block
    assert '<span class="l-zh" lang="zh">电网</span>' in block
    assert '<span class="l-en" lang="en">Quiet story</span>' in block
    assert '<span class="l-zh" lang="zh">安静主题</span>' in block
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    rp_section = template.split('{% if research_priority %}', 1)[1].split(
        '{# ── SIGNATURE: lifecycle ribbon ── #}', 1
    )[0]
    assert "t(item.name_en" not in rp_section
    assert "t(item.name_zh" not in rp_section


def test_blank_name_zh_falls_back_to_the_english_name(tmp_path):
    """Seat ruling R7c: a blank or whitespace-only name_zh never renders an empty
    span; the ZH slot carries the English name in a plain lang="en" span."""
    _copy_templates(tmp_path)
    payload = _payload_from_themes(
        (
            _te("theme:blank", "Blank ZH", "", "2026-09-08"),
            _te("theme:space", "Spaces ZH", "   ", "2026-09-07"),
            _te("theme:undated_blank", "Undated blank ZH", ""),
        )
    )
    block = _rp_block(_render(tmp_path, _base_ctx(research_priority=payload)))
    assert '<span class="l-zh" lang="en">Blank ZH</span>' in block
    assert '<span class="l-zh" lang="en">Spaces ZH</span>' in block
    assert '<span class="l-zh" lang="en">Undated blank ZH</span>' in block
    assert '<span class="l-zh" lang="zh"></span>' not in block
    assert re.search(r'<span class="l-zh" lang="zh">\s*</span>', block) is None


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
    assert payload["n_dated"] == 18
    assert payload["n_undated"] == 0
    assert len(payload["items"]) == 12
    assert payload["items"][0]["position"] == 1
    assert payload["items"][-1]["position"] == 12
