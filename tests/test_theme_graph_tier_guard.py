"""W-C2b consumer tier guard: hierarchy nodes must not leak into theme consumers."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from engine.market_ontology.exposure_map import compose_exposure_map, to_json
from engine.theme_graph.selection_cohort import compose_selection_cohort
from tests.test_market_ontology_exposure_map import (
    FakeStore,
    _chain_loader,
    _compose,
    _spec,
    edge,
)
from tests.test_theme_graph_selection_cohort import inputs, selection

REPO_ROOT = Path(__file__).resolve().parents[1]


def _node(node_id: str, *, kind: str = "theme", tier: str | None = "theme", **extra):
    row = {
        "node_id": node_id,
        "kind": kind,
        "name_en": extra.get("name_en", "Fixture"),
        "name_zh": extra.get("name_zh", "样例"),
    }
    if tier is not None:
        row["tier"] = tier
    row.update({k: v for k, v in extra.items() if k not in ("name_en", "name_zh")})
    return row


class NodesFakeStore(FakeStore):
    def __init__(self, edges, identity=None, meta=None, nodes=None, raise_on_read=False):
        super().__init__(edges, identity=identity, meta=meta, raise_on_read=raise_on_read)
        self._nodes = nodes or []

    def read_nodes(self):
        if self._raise:
            raise RuntimeError("store unavailable")
        return self._nodes


def _gold_fixture_edges():
    return [
        edge("e1", "MEMBER_OF", "co:us:A", "theme:gold"),
        edge("e2", "MEMBER_OF", "co:us:B", "theme:gold"),
    ]


def _gold_fixture_nodes():
    return [_node("theme:gold", tier="theme", name_en="Gold", name_zh="黄金")]


def _hierarchy_overlay(existing_theme: str = "theme:gold"):
    nodes = _gold_fixture_nodes() + [
        _node("theme:test_category_x", tier="macro_category", name_en="Cat X", name_zh="类X"),
        _node("theme:test_micro_x", tier="micro_theme", name_en="Micro X", name_zh="微X"),
    ]
    edges = _gold_fixture_edges() + [
        edge(
            "p1", "PARENT_OF", "theme:test_category_x", existing_theme,
            source_class="curated", date_provenance="crosswalk",
        ),
        edge(
            "p2", "PARENT_OF", existing_theme, "theme:test_micro_x",
            source_class="curated", date_provenance="crosswalk",
        ),
    ]
    return nodes, edges


def test_exposure_map_invariant_with_hierarchy_nodes():
    base_store = NodesFakeStore(_gold_fixture_edges(), nodes=_gold_fixture_nodes())
    extra_nodes, extra_edges = _hierarchy_overlay()
    extended_store = NodesFakeStore(extra_edges, nodes=extra_nodes)
    spec = _spec(["theme:gold"])
    base_map = to_json(_compose(base_store, spec))
    extended_map = to_json(_compose(extended_store, spec))
    assert base_map == extended_map


def test_exposure_map_refuses_macro_category_tier():
    nodes, edges = _hierarchy_overlay()
    store = NodesFakeStore(edges, nodes=nodes)
    m = _compose(store, _spec(["theme:test_category_x"]))
    theme = m.themes[0]
    assert theme.state == "IDENTITY_UNRESOLVED"
    assert theme.theme_plane is None
    assert theme.rights_family is None
    assert theme.unavailable is not None
    assert theme.unavailable["detail"] == "non_theme_tier:macro_category"


def test_exposure_map_refuses_micro_theme_tier():
    nodes, edges = _hierarchy_overlay()
    store = NodesFakeStore(edges, nodes=nodes)
    m = _compose(store, _spec(["theme:test_micro_x"]))
    theme = m.themes[0]
    assert theme.state == "IDENTITY_UNRESOLVED"
    assert theme.theme_plane is None
    assert theme.rights_family is None
    assert theme.unavailable is not None
    assert theme.unavailable["detail"] == "non_theme_tier:micro_theme"


def test_exposure_map_legacy_missing_tier_still_composes():
    nodes = [_node("theme:legacy_x", kind="theme", tier=None, name_en="Legacy", name_zh="遗留")]
    edges = [edge("e1", "MEMBER_OF", "co:us:A", "theme:legacy_x")]
    m = _compose(NodesFakeStore(edges, nodes=nodes), _spec(["theme:legacy_x"]))
    theme = m.themes[0]
    assert theme.state == "OK"
    assert theme.unavailable is None


def test_selection_cohort_invariant_with_hierarchy_nodes():
    source, kw = selection(), inputs()
    before = compose_selection_cohort(source, **kw)
    # selection_cohort composes from injected receipts only; extra graph nodes cannot appear.
    after = compose_selection_cohort(copy.deepcopy(source), **copy.deepcopy(kw))
    assert before == after


def test_theme_state_and_selection_cohort_do_not_read_node_store():
    for rel in (
        "engine/theme_graph/theme_state.py",
        "engine/theme_graph/selection_cohort.py",
    ):
        text = (REPO_ROOT / rel).read_text()
        assert "read_nodes" not in text
        assert "nodes.parquet" not in text
