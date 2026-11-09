"""Hierarchy breadth display reader (Taxonomy V2) — display-tier breadth of one
theme node: tier, active PARENT_OF parents, legal-tier children, distinct
micro_theme descendants, sub_theme layer. Synthetic in-memory frames only; the
data/** store is never read.
"""
from __future__ import annotations

import json
import random

import pandas as pd
import pytest

from engine.theme_graph import hierarchy_breadth_display as hbd
from engine.theme_graph import store

SCHEMA_VERSION = "gmi.hierarchy_breadth_display.v1"
SOURCE = {
    "owner": "engine/theme_graph/store.py",
    "artifact": "data/theme_graph/nodes.parquet+edges.parquet",
    "field": "PARENT_OF",
}
ENVELOPE_KEYS = [
    "schema_version", "subject_id", "status", "reason_code",
    "value", "labels", "quality", "source",
]
VALUE_KEYS = [
    "tier", "parents", "children", "child_counts",
    "descendant_micro_theme_count", "has_sub_theme_layer",
]


# ---------------------------------------------------------------------------
# In-memory fixtures (never data/**)
# ---------------------------------------------------------------------------

def _node(node_id: str, tier: str, *, kind: str = "theme",
          status: str = "canonical") -> tuple:
    return (node_id, kind, tier, status)


def _edge(edge_id: str, src: str, dst: str, *, valid_to=None,
          type_: str = "PARENT_OF") -> tuple:
    return (edge_id, type_, src, dst, valid_to)


def _nodes(rows: list[tuple]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["node_id", "kind", "tier", "status"])


def _edges(rows: list[tuple]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["edge_id", "type", "src", "dst", "valid_to"])


def _hierarchy_nodes() -> pd.DataFrame:
    return _nodes([
        _node("theme:compute", "macro_category"),
        _node("theme:ai", "theme"),
        _node("theme:vision", "theme"),
        _node("theme:ai_models", "sub_theme"),
        _node("theme:transformers", "micro_theme"),
        _node("theme:chips", "micro_theme"),
        _node("theme:cameras", "micro_theme"),
        _node("theme:dead_sub", "sub_theme", status="retired"),
        _node("theme:ghost_micro", "micro_theme", status="retired"),
    ])


def _hierarchy_edges() -> pd.DataFrame:
    return _edges([
        _edge("e1", "theme:compute", "theme:ai"),
        _edge("e2", "theme:compute", "theme:vision"),
        _edge("e3", "theme:ai", "theme:ai_models"),
        _edge("e4", "theme:ai_models", "theme:transformers"),
        _edge("e5", "theme:ai", "theme:transformers"),  # micro under sub AND theme
        _edge("e6", "theme:ai", "theme:chips"),
        _edge("e7", "theme:vision", "theme:cameras"),
        _edge("e8", "theme:ai", "theme:dead_sub"),
        _edge("e9", "theme:dead_sub", "theme:ghost_micro"),
    ])


def _read(subject, nodes=None, edges=None) -> dict:
    return hbd.read_hierarchy_breadth(
        subject,
        nodes=_hierarchy_nodes() if nodes is None else nodes,
        edges=_hierarchy_edges() if edges is None else edges,
    )


# ---------------------------------------------------------------------------
# Adjacency grouping per tier (SPEC §1)
# ---------------------------------------------------------------------------

def test_adjacency_grouping_per_tier():
    macro = _read("theme:compute")["value"]
    assert list(macro["children"]) == ["theme"]
    assert macro["children"] == {"theme": ["theme:ai", "theme:vision"]}
    assert macro["child_counts"] == {"theme": 2}

    theme = _read("theme:ai")["value"]
    assert list(theme["children"]) == ["sub_theme", "micro_theme"]
    assert theme["children"] == {
        "sub_theme": ["theme:ai_models"],
        "micro_theme": ["theme:chips", "theme:transformers"],
    }
    assert theme["child_counts"] == {"sub_theme": 1, "micro_theme": 2}

    sub = _read("theme:ai_models")["value"]
    assert list(sub["children"]) == ["micro_theme"]
    assert sub["children"] == {"micro_theme": ["theme:transformers"]}
    assert sub["child_counts"] == {"micro_theme": 1}

    micro = _read("theme:transformers")["value"]
    assert micro["children"] == {}
    assert micro["child_counts"] == {}


def test_adjacency_keys_exactly_the_legal_child_tiers():
    expected = {
        "macro_category": ["theme"],
        "theme": ["sub_theme", "micro_theme"],
        "sub_theme": ["micro_theme"],
        "micro_theme": [],
    }
    subjects = {
        "macro_category": "theme:compute",
        "theme": "theme:ai",
        "sub_theme": "theme:ai_models",
        "micro_theme": "theme:transformers",
    }
    for tier, subject in subjects.items():
        value = _read(subject)["value"]
        assert value["tier"] == tier
        assert list(value["children"]) == expected[tier]
        assert list(value["child_counts"]) == expected[tier]


# ---------------------------------------------------------------------------
# sub_theme layer
# ---------------------------------------------------------------------------

def test_theme_with_and_without_sub_theme_layer():
    with_layer = _read("theme:ai")["value"]
    assert with_layer["has_sub_theme_layer"] is True
    # a theme -> micro_theme edge without a sub_theme stays valid and counted
    without_layer = _read("theme:vision")["value"]
    assert without_layer["has_sub_theme_layer"] is False
    assert without_layer["children"]["sub_theme"] == []
    assert without_layer["children"]["micro_theme"] == ["theme:cameras"]
    assert without_layer["child_counts"]["micro_theme"] == 1
    assert without_layer["descendant_micro_theme_count"] == 1


# ---------------------------------------------------------------------------
# Descendants
# ---------------------------------------------------------------------------

def test_descendant_dedupe_micro_under_sub_theme_and_theme():
    # theme:transformers hangs under theme:ai directly (e5) and via
    # theme:ai_models (e4) — one distinct micro, counted once.
    value = _read("theme:ai")["value"]
    assert value["descendant_micro_theme_count"] == 2  # transformers + chips
    assert value["child_counts"]["micro_theme"] == 2

    sub = _read("theme:ai_models")["value"]
    assert sub["descendant_micro_theme_count"] == 1

    macro = _read("theme:compute")["value"]
    assert macro["descendant_micro_theme_count"] == 3  # transformers, chips, cameras

    micro = _read("theme:transformers")["value"]
    assert micro["descendant_micro_theme_count"] == 0


def test_cycle_safe_traversal():
    nodes = _nodes([
        _node("theme:cyc_a", "theme"),
        _node("theme:cyc_b", "sub_theme"),
        _node("theme:cyc_micro", "micro_theme"),
    ])
    edges = _edges([
        _edge("c1", "theme:cyc_a", "theme:cyc_b"),
        _edge("c2", "theme:cyc_b", "theme:cyc_a"),   # the cycle
        _edge("c3", "theme:cyc_a", "theme:cyc_micro"),
        _edge("c4", "theme:cyc_b", "theme:cyc_micro"),
    ])
    value = hbd.read_hierarchy_breadth("theme:cyc_a", nodes=nodes, edges=edges)["value"]
    assert value["descendant_micro_theme_count"] == 1
    assert value["children"] == {
        "sub_theme": ["theme:cyc_b"],
        "micro_theme": ["theme:cyc_micro"],
    }
    assert value["parents"] == ["theme:cyc_b"]  # the reader reads, never validates
    value_b = hbd.read_hierarchy_breadth("theme:cyc_b", nodes=nodes, edges=edges)["value"]
    assert value_b["descendant_micro_theme_count"] == 1
    assert value_b["parents"] == ["theme:cyc_a"]


def test_retired_child_excluded_everywhere():
    value = _read("theme:ai")["value"]
    assert value["children"]["sub_theme"] == ["theme:ai_models"]  # dead_sub gone
    assert value["child_counts"]["sub_theme"] == 1
    assert value["descendant_micro_theme_count"] == 2  # ghost_micro gone
    # a retired PARENT is excluded from the parent list too
    nodes = _nodes([
        _node("theme:compute", "macro_category"),
        _node("theme:old_root", "macro_category", status="retired"),
        _node("theme:vision", "theme"),
        _node("theme:cameras", "micro_theme"),
    ])
    edges = _edges([
        _edge("p1", "theme:compute", "theme:vision"),
        _edge("p2", "theme:old_root", "theme:vision"),
        _edge("p3", "theme:vision", "theme:cameras"),
    ])
    vision = hbd.read_hierarchy_breadth("theme:vision", nodes=nodes, edges=edges)["value"]
    assert vision["parents"] == ["theme:compute"]


# ---------------------------------------------------------------------------
# Retired / merged subjects
# ---------------------------------------------------------------------------

def test_retired_subject_is_not_applicable_retired_entity():
    envelope = _read("theme:dead_sub")
    assert envelope["status"] == "not_applicable"
    assert envelope["reason_code"] == "retired_entity"
    assert envelope["value"] is None


def test_merged_subject_is_not_applicable_superseded_entity():
    nodes = _nodes([
        _node("theme:compute", "macro_category"),
        _node("theme:old_name", "theme", status="merged"),
    ])
    edges = _edges([_edge("m1", "theme:compute", "theme:old_name")])
    envelope = hbd.read_hierarchy_breadth("theme:old_name", nodes=nodes, edges=edges)
    assert envelope["status"] == "not_applicable"
    assert envelope["reason_code"] == "superseded_entity"
    assert envelope["value"] is None
    # the merged subject is absent from the table: not an active theme-kind node
    table = hbd.hierarchy_breadth_table(nodes=nodes, edges=edges)
    assert [row["subject_id"] for row in table] == ["theme:compute"]


# ---------------------------------------------------------------------------
# Edge intervals
# ---------------------------------------------------------------------------

def test_closed_edge_valid_to_set_is_ignored():
    edges = _edges([
        _edge("e1", "theme:compute", "theme:ai"),
        _edge("e2", "theme:ai", "theme:transformers"),
        _edge("e3", "theme:ai", "theme:chips", valid_to="2026-01-01"),  # closed
    ])
    value = hbd.read_hierarchy_breadth("theme:ai", nodes=_hierarchy_nodes(),
                                       edges=edges)["value"]
    assert value["children"]["micro_theme"] == ["theme:transformers"]
    assert value["child_counts"]["micro_theme"] == 1
    assert value["descendant_micro_theme_count"] == 1
    # a closed edge INTO the subject removes that parent too
    edges_into = _edges([
        _edge("e1", "theme:compute", "theme:ai", valid_to="2026-01-01"),
        _edge("e2", "theme:compute", "theme:vision"),
        _edge("e7", "theme:vision", "theme:cameras"),
    ])
    ai = hbd.read_hierarchy_breadth("theme:ai", nodes=_hierarchy_nodes(),
                                    edges=edges_into)["value"]
    assert ai["parents"] == []
    # NaN valid_to is an open edge (parquet nulls arrive as NaN)
    edges_nan = _edges([_edge("e1", "theme:compute", "theme:ai", valid_to=float("nan"))])
    assert hbd.read_hierarchy_breadth(
        "theme:ai", nodes=_hierarchy_nodes(), edges=edges_nan)["value"]["parents"] == \
        ["theme:compute"]


# ---------------------------------------------------------------------------
# Gate #2 — internal-only vendor ids
# ---------------------------------------------------------------------------

def test_internal_only_ids_never_appear_anywhere():
    nodes = _nodes([
        _node("theme:compute", "macro_category"),
        _node("theme:ai", "theme"),
        _node("theme:chips", "micro_theme"),
        _node("ltheme:finviz:ai", "theme"),          # vendor local theme, kind=theme
        _node("theme:finviz_themes", "sub_theme"),   # suite id smuggled into a slug
        _node("theme:ths_concepts_extra", "micro_theme"),
    ])
    edges = _edges([
        _edge("g1", "theme:compute", "theme:ai"),
        _edge("g2", "theme:compute", "ltheme:finviz:ai"),
        _edge("g3", "theme:ai", "theme:finviz_themes"),
        _edge("g4", "theme:ai", "theme:ths_concepts_extra"),
        _edge("g5", "ltheme:finviz:ai", "theme:chips"),
    ])
    table = hbd.hierarchy_breadth_table(nodes=nodes, edges=edges)
    subjects = [row["subject_id"] for row in table]
    assert subjects == ["theme:ai", "theme:chips", "theme:compute"]
    blob = json.dumps(table)
    for banned in ("ltheme:", "finviz_themes", "ths_concepts"):
        assert banned not in blob

    ai = hbd.read_hierarchy_breadth("theme:ai", nodes=nodes, edges=edges)["value"]
    assert ai["children"]["sub_theme"] == []
    assert ai["children"]["micro_theme"] == []
    assert ai["descendant_micro_theme_count"] == 0
    assert ai["parents"] == ["theme:compute"]

    for banned_subject in ("ltheme:finviz:ai", "theme:finviz_themes",
                           "theme:ths_concepts_extra"):
        envelope = hbd.read_hierarchy_breadth(banned_subject, nodes=nodes, edges=edges)
        assert envelope["status"] == "not_applicable"
        assert envelope["reason_code"] == "not_applicable"
        assert envelope["value"] is None


# ---------------------------------------------------------------------------
# Typed nulls
# ---------------------------------------------------------------------------

def test_unknown_subject_is_unknown_value_missing():
    envelope = _read("theme:absent")
    assert envelope["status"] == "unknown"
    assert envelope["reason_code"] == "value_missing"
    assert envelope["value"] is None
    assert envelope["subject_id"] == "theme:absent"


def test_non_theme_kind_subject_is_not_applicable():
    nodes = _nodes([
        _node("theme:compute", "macro_category"),
        _node("etf:SMH", "micro_theme", kind="etf"),
        _node("basket:ths:semis", "micro_theme", kind="basket"),
    ])
    edges = _edges([_edge("k1", "theme:compute", "etf:SMH")])
    for subject in ("etf:SMH", "basket:ths:semis"):
        envelope = hbd.read_hierarchy_breadth(subject, nodes=nodes, edges=edges)
        assert envelope["status"] == "not_applicable"
        assert envelope["reason_code"] == "not_applicable"
        assert envelope["value"] is None
    # the etf child is not grouped under the theme's legal child tiers either
    value = hbd.read_hierarchy_breadth("theme:compute", nodes=nodes, edges=edges)["value"]
    assert value["children"] == {"theme": []}


# ---------------------------------------------------------------------------
# Envelope + value contract
# ---------------------------------------------------------------------------

def test_envelope_contract_across_whole_table():
    table = hbd.hierarchy_breadth_table(nodes=_hierarchy_nodes(),
                                        edges=_hierarchy_edges())
    assert table
    for envelope in table:
        assert list(envelope) == ENVELOPE_KEYS
        assert envelope["schema_version"] == SCHEMA_VERSION
        assert envelope["quality"] == "display_only"
        assert envelope["labels"] == ["house_curated"]
        assert envelope["source"] == SOURCE
        assert envelope["status"] in ("available", "unknown", "not_applicable")
        assert (envelope["reason_code"] is None) == (envelope["status"] == "available")
        assert (envelope["value"] is None) == (envelope["status"] != "available")
        assert list(envelope["value"]) == VALUE_KEYS
        assert envelope["value"]["has_sub_theme_layer"] in (True, False)
        assert isinstance(envelope["value"]["descendant_micro_theme_count"], int)


def test_no_forbidden_keys_anywhere_in_table_output():
    table = hbd.hierarchy_breadth_table(nodes=_hierarchy_nodes(),
                                        edges=_hierarchy_edges())
    assert hbd.validate_no_forbidden_keys(table) == []
    # positive control: the helper actually detects, at depth, in lists
    poisoned = {"ok": [{"nested": {"sub_score": 1, "fine": [{"share_pct": 2}]}}]}
    problems = hbd.validate_no_forbidden_keys(poisoned)
    assert len(problems) == 2
    assert any("sub_score" in problem for problem in problems)
    assert any("share_pct" in problem for problem in problems)


# ---------------------------------------------------------------------------
# Table shape, determinism, store discipline
# ---------------------------------------------------------------------------

def test_table_is_one_envelope_per_active_theme_node_sorted():
    table = hbd.hierarchy_breadth_table(nodes=_hierarchy_nodes(),
                                        edges=_hierarchy_edges())
    subjects = [row["subject_id"] for row in table]
    assert subjects == sorted(subjects)
    assert len(set(subjects)) == len(subjects)
    # every active theme-kind node; retired nodes are never subjects
    assert subjects == [
        "theme:ai", "theme:ai_models", "theme:cameras", "theme:chips",
        "theme:compute", "theme:transformers", "theme:vision",
    ]


def test_determinism_under_shuffled_input_frames():
    base = hbd.hierarchy_breadth_table(nodes=_hierarchy_nodes(),
                                       edges=_hierarchy_edges())
    canonical = json.dumps(base, sort_keys=True)
    rng = random.Random(20261017)
    for _ in range(3):
        node_rows = _hierarchy_nodes().sample(frac=1, random_state=rng.randrange(2**31))
        edge_rows = _hierarchy_edges().sample(frac=1, random_state=rng.randrange(2**31))
        shuffled = hbd.hierarchy_breadth_table(nodes=node_rows, edges=edge_rows)
        assert json.dumps(shuffled, sort_keys=True) == canonical


def test_store_inputs_loaded_at_most_once(monkeypatch):
    calls = {"nodes": 0, "edges": 0}

    def fake_read_nodes(*, current=False):
        assert current is True
        calls["nodes"] += 1
        return _hierarchy_nodes()

    def fake_read_edges(**kwargs):
        calls["edges"] += 1
        return _hierarchy_edges()

    monkeypatch.setattr(store, "read_nodes", fake_read_nodes)
    monkeypatch.setattr(store, "read_edges", fake_read_edges)
    table = hbd.hierarchy_breadth_table()
    assert calls == {"nodes": 1, "edges": 1}
    assert len(table) == 7
    # the single-subject reader resolves both inputs when not injected
    hbd.read_hierarchy_breadth("theme:ai")
    assert calls == {"nodes": 2, "edges": 2}


def test_module_constants_are_the_frozen_ones():
    assert hbd.SCHEMA_VERSION == SCHEMA_VERSION
    assert hbd.LABELS == ["house_curated"]
    assert hbd.QUALITY == "display_only"
    assert hbd.TIERS == ("macro_category", "theme", "sub_theme", "micro_theme")
    assert hbd.LEGAL_CHILD_TIERS == {
        "macro_category": ("theme",),
        "theme": ("sub_theme", "micro_theme"),
        "sub_theme": ("micro_theme",),
        "micro_theme": (),
    }


@pytest.mark.parametrize("subject,tier,parents", [
    ("theme:compute", "macro_category", []),
    ("theme:ai", "theme", ["theme:compute"]),
    ("theme:ai_models", "sub_theme", ["theme:ai"]),
    ("theme:transformers", "micro_theme", ["theme:ai", "theme:ai_models"]),
])
def test_parents_are_active_open_parent_of_sources(subject, tier, parents):
    envelope = _read(subject)
    assert envelope["status"] == "available"
    value = envelope["value"]
    assert value["tier"] == tier
    assert value["parents"] == parents


def test_retired_subject_value_is_null_even_with_edges():
    envelope = _read("theme:ghost_micro")
    assert envelope["status"] == "not_applicable"
    assert envelope["reason_code"] == "retired_entity"
    assert envelope["value"] is None
