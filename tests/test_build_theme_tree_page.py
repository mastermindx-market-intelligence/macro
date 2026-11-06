"""Tests for scripts/build_theme_tree_page.py (U1 Theme Map page).

Verifies the §0 gates of the FROZEN SPEC (U1_THEME_TREE_CENSUS_2026-10-17):

  * Gate #2 — counts equal the reader output for the same frames (this test).
  * Gate #3 — empty macros render the typed empty state.
  * Gate #4 — no forbidden vendor ids in HTML text or data attributes.
  * Gate #5 — no CJK inside any title=; every visible string carries EN+ZH spans.
  * Gate render() never raises when the store is unreadable.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.build_theme_tree_page import compose, render  # noqa: E402

# Vendor-internal strings forbidden anywhere in user-facing HTML (SPEC §0 / Gate #4).
_FORBIDDEN_VENDOR = re.compile(
    r"ltheme:|finviz_themes|ths_concepts|china_ths",
)
_CJK_RE = re.compile(r"[一-鿿㐀-䶿　-〿＀-￯]")


# ---------------------------------------------------------------------------
# Frame builders — match store.read_nodes(current=True) / read_edges() exactly
# ---------------------------------------------------------------------------


def _mk_nodes(*rows: dict) -> pd.DataFrame:
    """theme-kind nodes only, in the same column shape as the store emits."""
    cols = ["node_id", "kind", "name_en", "name_zh", "market_scope", "tier",
            "status", "merged_into", "birth_date", "retire_date",
            "identity_epoch", "external_ids", "provenance", "computed_at",
            "engine_version", "source_meta"]
    base = {c: ("" if c not in ("identity_epoch",) else 0) for c in cols}
    base.update({"kind": "theme", "market_scope": "US", "status": "active",
                 "merged_into": None, "retire_date": None,
                 "birth_date": "2026-01-01", "identity_epoch": 1,
                 "external_ids": "{}", "provenance": "{}",
                 "computed_at": "2026-10-17T00:00:00Z",
                 "engine_version": "theme_graph.v1",
                 "source_meta": "{}"})
    records = []
    for r in rows:
        row = dict(base)
        row.update(r)
        records.append(row)
    return pd.DataFrame(records, columns=cols)


def _mk_edges(*rows: dict) -> pd.DataFrame:
    """PARENT_OF edges only, in the same column shape as the store emits."""
    cols = [
        "edge_id", "type", "src", "dst", "valid_from", "valid_to",
        "provenance", "evidence_ref", "weight", "confidence",
        "computed_at", "engine_version", "source_meta",
    ] + [f"col_{i}" for i in range(24 - len([
        "edge_id", "type", "src", "dst", "valid_from", "valid_to",
        "provenance", "evidence_ref", "weight", "confidence",
        "computed_at", "engine_version", "source_meta",
    ]))]
    base = {c: ("" if c not in ("weight", "confidence") else 1.0) for c in cols}
    base.update({"type": "PARENT_OF", "valid_from": "2026-01-01",
                 "valid_to": None, "provenance": "{}",
                 "evidence_ref": "{}", "computed_at": "2026-10-17T00:00:00Z",
                 "engine_version": "theme_graph.v1", "source_meta": "{}"})
    records = []
    for r in rows:
        row = dict(base)
        row.update(r)
        # autofill edge_id by composition
        if "edge_id" not in r:
            row["edge_id"] = f"PARENT_OF:{r['src']}->{r['dst']}"
        records.append(row)
    return pd.DataFrame(records, columns=cols)


# ---------------------------------------------------------------------------
# Frame fixtures — every test builds its own DATA so counts are computed, not
# hard-coded (SPEC §0 Gate #2 and §3).
# ---------------------------------------------------------------------------


def _fixtures_two_macros():
    """macro1: macro_cat A → theme1, theme2 (no sub_theme); theme1 → micro1, micro2.
       theme2 → sub_theme1 → micro3.
       macro2: macro_cat B → theme3 → micro4.
       micro2 has an extra parent (theme3), so multi-parent tip lines exist.
    """
    nodes = _mk_nodes(
        {"node_id": "theme:macroA", "name_en": "Energy & power",
         "name_zh": "能源电力", "tier": "macro_category"},
        {"node_id": "theme:macroB", "name_en": "Technology software",
         "name_zh": "技术软件", "tier": "macro_category"},
        {"node_id": "theme:t1", "name_en": "AI compute",
         "name_zh": "AI 算力", "tier": "theme"},
        {"node_id": "theme:t2", "name_en": "Power delivery",
         "name_zh": "电力输送", "tier": "theme"},
        {"node_id": "theme:t3", "name_en": "Software stacks",
         "name_zh": "软件栈", "tier": "theme"},
        {"node_id": "theme:s1", "name_en": "Sub-grid",
         "name_zh": "子电网", "tier": "sub_theme"},
        {"node_id": "theme:micro1", "name_en": "Compute silicon",
         "name_zh": "计算芯片", "tier": "micro_theme"},
        {"node_id": "theme:micro2", "name_en": "Cooling systems",
         "name_zh": "冷却系统", "tier": "micro_theme"},
        {"node_id": "theme:micro3", "name_en": "Transformers",
         "name_zh": "变压器", "tier": "micro_theme"},
        {"node_id": "theme:micro4", "name_en": "Developer tools",
         "name_zh": "开发工具", "tier": "micro_theme"},
    )
    edges = _mk_edges(
        {"src": "theme:macroA", "dst": "theme:t1"},
        {"src": "theme:macroA", "dst": "theme:t2"},
        {"src": "theme:macroB", "dst": "theme:t3"},
        {"src": "theme:t1", "dst": "theme:micro1"},
        {"src": "theme:t1", "dst": "theme:micro2"},
        {"src": "theme:t3", "dst": "theme:micro2"},  # multi-parent micro
        {"src": "theme:t2", "dst": "theme:s1"},
        {"src": "theme:s1", "dst": "theme:micro3"},
        {"src": "theme:t3", "dst": "theme:micro4"},
    )
    return nodes, edges


# ---------------------------------------------------------------------------
# compose() — gate #2: counts equal the reader's envelope counts
# ---------------------------------------------------------------------------


def test_compose_counts_equal_reader_tier_counts():
    nodes, edges = _fixtures_two_macros()
    ctx = compose(REPO, nodes=nodes, edges=edges)
    s = ctx["summary"]
    # reader-derived totals (computed not hard-coded, SPEC Gate #2):
    assert s["macro_count"] == 2
    assert s["theme_count"] == 3
    assert s["sub_theme_count"] == 1
    assert s["micro_count"] == 4


def test_compose_no_crash_on_empty_frames():
    """Injected empty frames — no reader walks, zero counts, render path safe."""
    nodes = _mk_nodes()
    edges = _mk_edges()
    ctx = compose(REPO, nodes=nodes, edges=edges)
    assert ctx["available"] is True
    assert ctx["summary"] == {"macro_count": 0, "theme_count": 0,
                              "sub_theme_count": 0, "micro_count": 0,
                              "missing_count": 0}


# ---------------------------------------------------------------------------
# render() — gates #3, #4, #5, fail-open (#5)
# ---------------------------------------------------------------------------


def test_render_unreadable_store_yields_empty_state(monkeypatch):
    """Gate #5 — render() never raises when the store is unreadable.

    We monkeypatch the loader to raise so the live I/O path is replaced.
    """
    import scripts.build_theme_tree_page as mod
    monkeypatch.setattr(mod, "_load_frames",
                        lambda root: (None, None))
    html = render(REPO, ctx=mod.compose(REPO))
    assert "tt-empty" in html
    assert "The theme map could not be loaded" in html
    assert "主题地图无法加载" in html
    # U2: the header carries no summary/missing lines over an empty store
    header = html.split('<header class="tt-hero">', 1)[1].split("</header>", 1)[0]
    assert "tt-summary" not in header
    assert "tt-missing" not in header
    assert "As of" not in header


def test_render_unknown_date_reads_date_unavailable_without_as_of():
    nodes, edges = _fixtures_two_macros()
    ctx = compose(REPO, nodes=nodes, edges=edges)
    ctx["as_of"] = ""
    html = render(REPO, ctx=ctx)
    header = html.split('<header class="tt-hero">', 1)[1].split("</header>", 1)[0]
    assert "Date unavailable" in header and "日期未知" in header
    assert "As of" not in header and "截至" not in header
    ctx["as_of"] = "2026-10-17"
    html = render(REPO, ctx=ctx)
    assert "As of 2026-10-17" in html and "截至 2026-10-17" in html


def test_template_has_no_inline_style_attributes():
    tpl = (REPO / "templates" / "theme_tree.html.j2").read_text(encoding="utf-8")
    assert 'style="' not in tpl


def test_render_full_layout_carries_counts_and_zones():
    nodes, edges = _fixtures_two_macros()
    html = render(REPO, ctx=compose(REPO, nodes=nodes, edges=edges))
    # bilingual summary counts (Jinja may emit whitespace + tags between the
    # number and the noun; regex-pin so the assertion is layout-agnostic).
    assert re.search(r"<b>\s*2\s*</b>\s*categories", html), \
        "EN macro count missing"
    assert re.search(r"<b>\s*2\s*</b>\s*个大类", html), \
        "ZH macro count missing"
    assert re.search(r"<b>\s*3\s*</b>\s*themes", html)
    assert re.search(r"<b>\s*3\s*</b>\s*个主题", html)
    assert re.search(r"<b>\s*4\s*</b>\s*micro-themes", html)
    # U2: exactly one footnote (fine print at the bottom, never in the header)
    assert html.count("A map of how we group companies") == 1
    assert html.count("这是我们对公司归类的地图") == 1
    header = html.split("</header>", 1)[0]
    assert "A map of how we group companies" not in header
    # breadth strip ticks present
    assert 'tt-strip-tick' in html
    # both categories rendered as <details>
    assert html.count('class="tt-cat"') == 2


def test_render_categorizes_empty_macro_typed_state():
    """SPEC §3 — an empty category gets the typed "Nothing mapped here yet" line,
    computed by the builder (no fixtures → not hard-coded)."""
    nodes, edges = _fixtures_two_macros()
    # Truncate so macroA has zero children.
    edges = edges[edges["dst"] != "theme:t1"]
    edges = edges[edges["dst"] != "theme:t2"]
    edges = edges[edges["dst"] != "theme:micro1"]
    edges = edges[edges["dst"] != "theme:micro2"]
    edges = edges[edges["dst"] != "theme:micro3"]
    html = render(REPO, ctx=compose(REPO, nodes=nodes, edges=edges))
    assert "Nothing mapped here yet" in html
    assert "尚未归入任何主题" in html
    # Hollow tick outline present for the empty category
    assert 'tt-strip-tick-empty' in html


def test_render_no_vendor_ids_in_page_body():
    """Gate #4 — no ltheme: / finviz_themes / ths_concepts / china_ths in the
    page's own markup. The shared navlinks include carries one URL
    (``baskets_china_ths.html``) that exists on every page; we exclude the
    nav block to keep the gate scoped to U1 surfaces.
    """
    nodes, edges = _fixtures_two_macros()
    html = render(REPO, ctx=compose(REPO, nodes=nodes, edges=edges))
    # Slice from our own hero onward; the nav include ends at <body>'s next
    # sibling, which on this template is the <div class="wrap"> opening tag.
    wrap_at = html.find('class="wrap"')
    assert wrap_at != -1, "wrap block missing"
    wrap = html[wrap_at:]
    hits = _FORBIDDEN_VENDOR.search(wrap)
    assert not hits, f"vendor id leaked into U1 body: {hits.group(0)!r}"


def test_render_no_vendor_ids_in_data_attributes():
    """Gate #4 — data-* attrs must not carry vendor ids even when name_en is generic."""
    # Inject a node whose name_en would never carry the token, but with a vendor id.
    nodes = _mk_nodes(
        {"node_id": "ltheme:hidden", "name_en": "My chip",
         "name_zh": "我的芯片", "tier": "micro_theme"},
        {"node_id": "theme:m1", "name_en": "Macro",
         "name_zh": "宏观大类", "tier": "macro_category"},
    )
    edges = _mk_edges(
        {"src": "theme:m1", "dst": "ltheme:hidden"},
    )
    html = render(REPO, ctx=compose(REPO, nodes=nodes, edges=edges))
    # The internal-only subject is dropped by the reader (hierarchy_breadth_table),
    # so the page never carries its data-* attribute on a chip.
    assert "data-node=\"ltheme:" not in html
    assert "ltheme:" not in html


def test_render_no_title_bilingual_and_no_cjk_in_titles():
    """Gate #5 — no CJK inside any title= attribute."""
    nodes, edges = _fixtures_two_macros()
    html = render(REPO, ctx=compose(REPO, nodes=nodes, edges=edges))
    for m in re.finditer(r'title\s*=\s*"([^"]*)"', html):
        assert not _CJK_RE.search(m.group(1)), \
            f"CJK inside title= at {m.start()}: {m.group(1)!r}"


def test_render_bilingual_structure_on_every_chip_and_header():
    """Gate #5 — every visible string carries EN + ZH spans.

    Autoescape turns '&' into '&amp;' so the assertion must accept either form.
    """
    nodes, edges = _fixtures_two_macros()
    html = render(REPO, ctx=compose(REPO, nodes=nodes, edges=edges))
    assert ('<span class="l-en">Energy &amp; power</span>' in html) or (
        '<span class="l-en">Energy & power</span>' in html)
    assert '<span class="l-zh">能源电力</span>' in html
    assert '<span class="l-en">AI compute</span>' in html
    assert '<span class="l-zh">AI 算力</span>' in html


def test_render_multi_parent_micro_chip_carries_also_under_tip():
    nodes, edges = _fixtures_two_macros()
    html = render(REPO, ctx=compose(REPO, nodes=nodes, edges=edges))
    # micro2 is under macroA/t1 AND macroB/t3, so when listed under t1 the chip
    # carries an "Also under: Software stacks" tip in EN.
    assert "Also under: Software stacks" in html
    assert "同时属于：Software stacks" in html


# ---------------------------------------------------------------------------
# Source-level (template-level) checks — gate #8: tokens only, no raw color
# ---------------------------------------------------------------------------


def test_template_uses_only_token_vars_no_raw_hex_or_rgb():
    src = (REPO / "templates" / "theme_tree.html.j2").read_text(encoding="utf-8")
    raw_color = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgb\s*\(|rgba\s*\(|hsl\s*\(|hsla\s*\(")
    # Strip the JS block where we deliberately run `setAttribute('style', ...)`-free
    # code (the existing state_of_themes.html.j2 idiom uses `style.display = 'block'`).
    visible = re.sub(r"<script\b.*?</script>", "", src, flags=re.S)
    visible = re.sub(r"\{#.*?#\}", "", visible, flags=re.S)
    hits = [m.group(0) for m in raw_color.finditer(visible)]
    assert not hits, f"raw color in template: {hits[:5]}"


def test_template_no_runtime_style_cssText_or_textContent_in_js():
    """Gate #8 — the ratchet forbids cssText and style.textContent = in JS."""
    src = (REPO / "templates" / "theme_tree.html.j2").read_text(encoding="utf-8")
    js = "".join(re.findall(r"<script\b.*?</script>", src, re.S))
    # setting individual .style.X = "..." is allowed (state_of_themes does the same);
    # cssText and style.textContent are the ratchet patterns.
    assert ".cssText" not in js
    assert "style.textContent" not in js
    assert "cssText" not in js


def test_compose_real_graph_summary_matches_reader(monkeypatch):
    """REAL graph path — skip if the artifact is missing. SPEC Gate §0 'NOT DONE UNLESS':
    'renders from hierarchy_breadth_table() + store.read_nodes(current=True)'."""
    nodes_path = REPO / "data" / "theme_graph" / "nodes.parquet"
    if not nodes_path.exists():
        pytest.skip("data/theme_graph/nodes.parquet missing in this sparse tree")
    ctx = compose(REPO)
    assert ctx["available"] is True
    s = ctx["summary"]
    # The census recorded 10 / 18 / 12 / 68 — assert the page's summary equals it
    # (the real reader emits these exact counts).
    assert s == {"macro_count": 10, "theme_count": 18,
                 "sub_theme_count": 12, "micro_count": 68,
                 "missing_count": 0}, f"real-graph summary drift: {s}"


def test_as_of_reads_store_belief_time_and_rejects_garbage(tmp_path):
    import scripts.build_theme_tree_page as mod
    meta = tmp_path / "_meta.json"
    meta.write_text('{"belief_time": "2026-10-17", "computed_at": "x"}', encoding="utf-8")
    assert mod._as_of_date(meta) == "2026-10-17"
    meta.write_text('{"belief_time": "soon"}', encoding="utf-8")
    assert mod._as_of_date(meta) == ""
    assert mod._as_of_date(tmp_path / "missing.json") == ""
