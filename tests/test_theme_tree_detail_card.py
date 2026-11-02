"""Tests for the U2 micro-theme detail card on /theme_tree.html.

Covers the "not done unless" clauses of SPEC_U2: typed nulls (orphan →
unknown, zero instruments → none, never a 0), the forbidden-key walk over
the card blob, no vendor-internal ids in the blob or chips, ``</`` escaping,
one detail entry per chip, and a market qualifier on every instrument.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from engine.theme_graph import hierarchy_breadth_display as hb  # noqa: E402
from scripts.build_theme_tree_page import (  # noqa: E402
    _build_details,
    _details_json,
    _node_name_index,
    compose,
    render,
)
from tests.test_build_theme_tree_page import _mk_edges, _mk_nodes  # noqa: E402

_VENDOR = re.compile(r"ltheme:|ths_concepts|baskets_china_ths|finviz")
_BLOB_RE = re.compile(r'id="tt-detail-data">(.*?)</script>', re.S)
_CHIP_RE = re.compile(r'<button type="button" class="tt-chip"[^>]*>', re.S)


def _fixtures():
    """macroA → t1 → micro1 (proxied by a US and a China basket) and
    t1 → s1 → micro2; t2 → micro3 has no basket; micro_orphan has no parent.
    A vendor-derived basket also EXPRESSES t1 and must never surface."""
    nodes = _mk_nodes(
        {"node_id": "theme:macroA", "name_en": "Energy", "name_zh": "能源",
         "tier": "macro_category"},
        {"node_id": "theme:t1", "name_en": "Grid </script>", "name_zh": "电网",
         "tier": "theme"},
        {"node_id": "theme:t2", "name_en": "Storage", "name_zh": "储能",
         "tier": "theme"},
        {"node_id": "theme:s1", "name_en": "Lines", "name_zh": "线路",
         "tier": "sub_theme"},
        {"node_id": "theme:micro1", "name_en": "Transformers", "name_zh": "变压器",
         "tier": "micro_theme"},
        {"node_id": "theme:micro2", "name_en": "Cables", "name_zh": "电缆",
         "tier": "micro_theme"},
        {"node_id": "theme:micro3", "name_en": "Cells", "name_zh": "电芯",
         "tier": "micro_theme"},
        {"node_id": "theme:micro_orphan", "name_en": "Loose", "name_zh": "游离",
         "tier": "micro_theme"},
        {"node_id": "basket:baskets:grid", "kind": "basket",
         "name_en": "Grid basket", "name_zh": "电网篮子", "tier": ""},
        {"node_id": "basket:baskets_china:grid", "kind": "basket",
         "name_en": "China grid", "name_zh": "中国电网", "tier": ""},
        {"node_id": "basket:baskets_china_ths:grid", "kind": "basket",
         "name_en": "Vendor grid", "name_zh": "供应商电网", "tier": ""},
    )
    edges = _mk_edges(
        {"src": "theme:macroA", "dst": "theme:t1"},
        {"src": "theme:macroA", "dst": "theme:t2"},
        {"src": "theme:t1", "dst": "theme:micro1"},
        {"src": "theme:t1", "dst": "theme:s1"},
        {"src": "theme:s1", "dst": "theme:micro2"},
        {"src": "theme:t2", "dst": "theme:micro3"},
        {"type": "EXPRESSES", "src": "basket:baskets:grid", "dst": "theme:t1",
         "edge_id": "EXPRESSES:us"},
        {"type": "EXPRESSES", "src": "basket:baskets_china:grid", "dst": "theme:t1",
         "edge_id": "EXPRESSES:cn"},
        {"type": "EXPRESSES", "src": "basket:baskets_china_ths:grid",
         "dst": "theme:t1", "edge_id": "EXPRESSES:ths"},
    )
    return nodes, edges


def _details(tmp_path=None):
    nodes, edges = _fixtures()
    envs = hb.hierarchy_breadth_table(nodes=nodes, edges=edges)
    site = tmp_path if tmp_path is not None else Path("/nonexistent-site")
    return _build_details(envs, _node_name_index(nodes), nodes, edges, site)


def _html():
    nodes, edges = _fixtures()
    return render(REPO, ctx=compose(REPO, nodes=nodes, edges=edges))


def _blob(html: str) -> dict:
    m = _BLOB_RE.search(html)
    assert m, "detail blob missing"
    return json.loads(m.group(1))


def test_orphan_micro_proxy_state_is_unknown():
    d = _details()
    assert d["theme:micro_orphan"]["proxy_state"] == "unknown"
    assert d["theme:micro_orphan"]["instruments"] == []
    assert d["theme:micro_orphan"]["chains"] == []


def test_zero_instruments_is_typed_none_never_zero():
    d = _details()
    assert d["theme:micro3"]["proxy_state"] == "none"
    assert d["theme:micro3"]["instruments"] == []
    html = _html()
    assert "No public proxy basket for this theme yet." in html
    assert "该主题暂无可公开的代理篮子。" in html


def test_available_instruments_carry_market_and_exclude_vendor():
    d = _details()
    insts = d["theme:micro1"]["instruments"]
    assert d["theme:micro1"]["proxy_state"] == "available"
    assert {i["name_en"] for i in insts} == {"Grid basket", "China grid"}
    for inst in insts:
        assert inst["market_en"] and inst["market_zh"]
    # Proxied via the parent theme across the sub_theme too.
    assert {i["name_en"] for i in d["theme:micro2"]["instruments"]} == {
        "Grid basket", "China grid"}


def test_chains_run_micro_to_root_without_self():
    d = _details()
    assert [[r["node_id"] for r in c] for c in d["theme:micro2"]["chains"]] == [
        ["theme:macroA", "theme:t1", "theme:s1"]]
    assert d["theme:micro2"]["breadth"][0]["micro_count"] == 2


def test_href_only_when_basket_page_exists(tmp_path):
    (tmp_path / "basket").mkdir()
    (tmp_path / "basket" / "grid.html").write_text("x")
    insts = {i["name_en"]: i for i in _details(tmp_path)["theme:micro1"]["instruments"]}
    assert insts["Grid basket"]["href"] == "basket/grid.html"
    assert insts["China grid"]["href"] is None


def test_blob_passes_forbidden_key_walk():
    blob = _blob(_html())
    assert hb.validate_no_forbidden_keys(blob) == []
    text = json.dumps(blob)
    for key in ("weight", "share", "score", "rank", "exposure_pct"):
        assert f'"{key}"' not in text


def test_no_vendor_ids_in_blob_or_chips():
    html = _html()
    raw = _BLOB_RE.search(html).group(1)
    assert not _VENDOR.search(raw)
    for chip in _CHIP_RE.findall(html):
        assert not _VENDOR.search(chip)


def test_blob_escapes_script_close():
    nodes, edges = _fixtures()
    envs = hb.hierarchy_breadth_table(nodes=nodes, edges=edges)
    out = _details_json(envs, _node_name_index(nodes), nodes, edges, Path("/x"))
    assert "</" not in out and "<\\/script>" in out


def test_every_chip_has_a_detail_entry():
    html = _html()
    blob = _blob(html)
    chips = set(re.findall(r'class="tt-chip" data-node="([^"]+)"', html))
    assert chips and chips <= set(blob)
    # Direct micros under a theme that also has sub-themes are on the map.
    assert "theme:micro1" in chips and "theme:micro2" in chips


def test_card_chrome_is_bilingual_and_accessible():
    html = _html()
    assert 'id="tt-detail"' in html and 'aria-live="polite"' in html
    assert 'aria-controls="tt-detail"' in html
    assert "Watch instead" in html and "可替代观察" in html
