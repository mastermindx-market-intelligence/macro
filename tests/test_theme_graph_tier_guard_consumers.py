"""W-C2b tier guard, two more consumers: state-of-themes research priority and capability.

Sub-theme and micro-theme nodes gain company members through the curated activity
route (company -> sub_theme / micro_theme MEMBER_OF). Those memberships must not change
what these consumers produce: the research-priority evidence count, and the capability
classification (a hierarchy node never becomes a measurement_candidate).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

from engine.theme_graph import capability
from engine.theme_graph.ontology import is_hierarchy_tier_node

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_state_of_themes_under_test", REPO_ROOT / "scripts" / "build_state_of_themes.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _node(node_id, *, kind="theme", tier="theme"):
    return {"node_id": node_id, "kind": kind, "tier": tier, "market_scope": "us",
            "name_en": node_id, "name_zh": node_id, "status": "canonical"}


def _edge(src, dst, typ, when="2026-10-01"):
    return {"src": src, "dst": dst, "type": typ, "evidence_time": when, "valid_to": None}


NODES = [
    _node("theme:cat", tier="macro_category"),
    _node("theme:t1", tier="theme"),
    _node("theme:sub1", tier="sub_theme"),
    _node("theme:micro1", tier="micro_theme"),
    _node("theme:legacy", tier=None),
    _node("co:us:AAA", kind="company", tier=None),
    _node("co:us:BBB", kind="company", tier=None),
    _node("co:us:CCC", kind="company", tier=None),
]

BASE_EDGES = [
    _edge("theme:cat", "theme:t1", "PARENT_OF", "2026-09-01"),
    _edge("theme:t1", "theme:sub1", "PARENT_OF", "2026-09-02"),
    _edge("theme:sub1", "theme:micro1", "PARENT_OF", "2026-09-03"),
    _edge("basket:b1", "theme:t1", "EXPRESSES", "2026-09-04"),
]

#: What the activity route adds when a curated pilot lands.
ACTIVITY_EDGES = [
    _edge("co:us:AAA", "theme:sub1", "MEMBER_OF", "2026-11-12"),
    _edge("co:us:BBB", "theme:sub1", "MEMBER_OF", "2026-11-12"),
    _edge("co:us:AAA", "theme:micro1", "MEMBER_OF", "2026-11-12"),
    _edge("co:us:BBB", "theme:micro1", "MEMBER_OF", "2026-11-12"),
    _edge("co:us:CCC", "theme:micro1", "MEMBER_OF", "2026-11-12"),
]


def test_tier_rule_alias():
    assert is_hierarchy_tier_node(_node("theme:sub1", tier="sub_theme"))
    assert is_hierarchy_tier_node(_node("theme:micro1", tier="micro_theme"))
    assert is_hierarchy_tier_node(_node("theme:cat", tier="macro_category"))
    assert not is_hierarchy_tier_node(_node("theme:t1", tier="theme"))
    assert not is_hierarchy_tier_node(_node("theme:legacy", tier=None))
    assert not is_hierarchy_tier_node(_node("co:us:AAA", kind="company", tier=None))


def _evidence(builder, edges):
    nodes = pd.DataFrame(NODES)
    theme_nodes = {r["node_id"]: (r["name_en"], r["name_zh"])
                   for r in NODES if r["kind"] == "theme"}
    hierarchy_ids = {r["node_id"] for r in NODES if is_hierarchy_tier_node(r)}
    assert set(nodes.columns) >= {"node_id", "kind", "tier"}
    return builder._research_priority_evidence(theme_nodes, hierarchy_ids, pd.DataFrame(edges))


def test_research_priority_ignores_activity_memberships_into_hierarchy_nodes():
    builder = _load_builder()
    before = _evidence(builder, BASE_EDGES)
    after = _evidence(builder, BASE_EDGES + ACTIVITY_EDGES)
    assert before == after
    # The parent links still count, exactly as before the guard.
    touched, dates = before
    assert "theme:sub1" in touched and dates["theme:sub1"] == ["2026-09-02", "2026-09-03"]


def test_research_priority_still_counts_membership_into_a_theme_tier_node():
    builder = _load_builder()
    extra = [_edge("co:us:AAA", "theme:t1", "MEMBER_OF", "2026-11-12"),
             _edge("co:us:AAA", "theme:legacy", "MEMBER_OF", "2026-11-12")]
    _, dates = _evidence(builder, BASE_EDGES + extra)
    assert "2026-11-12" in dates["theme:t1"]
    assert "2026-11-12" in dates["theme:legacy"]


def test_legacy_null_tier_survives_the_parquet_round_trip(tmp_path):
    """The store reads a null tier back as float NaN; that legacy theme must stay
    canonical (not hierarchy), so its membership dates still count."""
    path = tmp_path / "nodes.parquet"
    pd.DataFrame(NODES).to_parquet(path, index=False)
    rows = {r["node_id"]: r for r in pd.read_parquet(path).to_dict("records")}
    assert not is_hierarchy_tier_node(rows["theme:legacy"])
    assert not is_hierarchy_tier_node(rows["theme:t1"])
    assert is_hierarchy_tier_node(rows["theme:micro1"])


def test_research_priority_without_type_column_is_unchanged():
    builder = _load_builder()
    edges = pd.DataFrame(BASE_EDGES).drop(columns=["type"])
    theme_nodes = {r["node_id"]: (r["name_en"], r["name_zh"])
                   for r in NODES if r["kind"] == "theme"}
    touched, _ = builder._research_priority_evidence(theme_nodes, {"theme:sub1"}, edges)
    assert "theme:sub1" in touched


class _AllPriced:
    """Substrate stub: every symbol resolves to a price artifact."""

    def resolve(self, symbol, market):
        return "stocks"


def test_capability_never_classifies_hierarchy_nodes_even_when_asked():
    rows = capability.derive_rows(
        NODES, BASE_EDGES + ACTIVITY_EDGES, substrate=_AllPriced(),
        computed_at="2026-11-12T00:00:00Z", engine_version="test",
        kinds=("local_theme", "theme"),
    )
    ids = {r["node_id"] for r in rows}
    assert "theme:micro1" not in ids and "theme:sub1" not in ids and "theme:cat" not in ids
    assert {"theme:t1", "theme:legacy"} <= ids


def test_capability_default_kinds_unchanged_by_activity_memberships():
    local = [{"node_id": "ltheme:x", "kind": "local_theme", "market_scope": "us"}]
    member_edges = [_edge(f"co:us:{s}", "ltheme:x", "MEMBER_OF") for s in ("AAA", "BBB", "CCC")]
    kwargs = dict(substrate=_AllPriced(), computed_at="2026-11-12T00:00:00Z",
                  engine_version="test")
    before = capability.derive_rows(NODES + local, BASE_EDGES + member_edges, **kwargs)
    after = capability.derive_rows(NODES + local, BASE_EDGES + member_edges + ACTIVITY_EDGES,
                                   **kwargs)
    assert before == after
    assert [r["capability"] for r in before] == ["measurement_candidate"]
