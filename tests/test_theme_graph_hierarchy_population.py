"""W-C4 production hierarchy population — frozen R-C.3 table, PIT, rights, outputs unchanged."""
from __future__ import annotations

import ast
import copy
import json
import re
import shutil
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
import yaml

from engine.market_ontology.exposure_map import to_json
from engine.theme_graph import materialize, store
from engine.theme_graph import rights
from engine.theme_graph.selection_cohort import compose_selection_cohort
from scripts import check_theme_graph_contracts as guard
from tests.test_market_ontology_exposure_map import (
    _chain_loader,
    _compose,
    _spec,
)
from tests.test_theme_graph_hierarchy_contract import (
    _hierarchy_breaches,
    _hierarchy_chain_nodes_edges,
    _write_store,
)
from tests.test_theme_graph_selection_cohort import inputs, selection
from tests.test_theme_graph_tier_guard import NodesFakeStore

ROOT = Path(__file__).resolve().parents[1]
CROSSWALK = ROOT / "config" / "theme_crosswalk.yml"
MEMBERSHIP = ROOT / "data" / "baskets" / "membership.json"

DOC = yaml.safe_load(CROSSWALK.read_text(encoding="utf-8"))

EXCLUDED_BASKET_CATEGORIES = {"US Sectors (EW)"}
# Equal-weight sector-index baskets are the sector axis, not semantic-theme navigation.

ALLOWED_BASKET_PREFIXES = (
    "basket:baskets:",
    "basket:baskets_china:",
    "basket:baskets_hk:",
    "basket:baskets_canada:",
    "basket:baskets_intl:",
)

VENDOR_SUBSTRINGS = ("finviz_themes", "ths_concepts", "baskets_china_ths")
VENDOR_TOKENS = frozenset({"finviz", "ths"})

PRODUCTION_THEME_NODE_IDS = tuple(
    row["theme_node_id"] for row in DOC["themes"] if row.get("theme_node_id")
)

BASKET_NOTE_RE = re.compile(
    r"^basket categories:\s*(.+?)\.\s*$", re.IGNORECASE)


def _asserted_on() -> str:
    return DOC["hierarchy"]["categories"][0]["asserted_on"]


def _walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from _walk_strings(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_strings(item)


def _basket_categories_from_note(note: str | None) -> set[str]:
    if not note:
        return set()
    match = BASKET_NOTE_RE.match(note.strip())
    if not match:
        return set()
    return {part.strip() for part in match.group(1).split("|") if part.strip()}


def _non_hierarchy_nodes(nodes):
    return [
        row for row in nodes
        if row.get("tier") not in ("macro_category", "micro_theme")
    ]


def _non_hierarchy_edges(edges):
    return [row for row in edges if row.get("type") != "PARENT_OF"]


def _parquet_bytes(rows, columns: tuple[str, ...], path: Path, *, sort_key: str) -> bytes:
    ordered = sorted(rows, key=lambda row: row[sort_key])
    frame = pd.DataFrame(ordered).reindex(columns=list(columns))
    frame.to_parquet(path, index=False)
    return path.read_bytes()


def _hierarchy_evidence_ids(view) -> set[str]:
    refs: set[str] = set()
    for row in view.edges:
        if row.get("type") != "PARENT_OF":
            continue
        for ref in row.get("evidence_refs") or []:
            refs.add(str(ref))
    return refs


def _evidence_without_hierarchy(view, asserted_on: str):
    hide = _hierarchy_evidence_ids(view)
    return [
        row for row in view.evidence
        if row.get("evidence_id") not in hide
        and not (
            row.get("kind") == "operator_curation"
            and row.get("source_ref") == "config/theme_crosswalk.yml"
            and row.get("published_at") == asserted_on
            and row.get("evidence_id") in hide
        )
    ]


@pytest.fixture
def production_build(tmp_path, monkeypatch):
    if not MEMBERSHIP.is_file():
        pytest.skip("needs_full_checkout: data/baskets/membership.json")

    data_root = tmp_path / "data"
    (data_root / "baskets").mkdir(parents=True)
    (data_root / "baskets_china_ths").mkdir(parents=True)
    shutil.copy(MEMBERSHIP, data_root / "baskets" / "membership.json")

    asserted_on = _asserted_on()
    doc_without = copy.deepcopy(DOC)
    doc_without.pop("hierarchy", None)
    crosswalk_without = tmp_path / "theme_crosswalk_no_hierarchy.yml"
    crosswalk_without.write_text(
        yaml.safe_dump(doc_without, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    from engine.theme_graph import identity
    from lib import config

    monkeypatch.setattr(identity, "load_breaks", lambda *a, **k: {})
    monkeypatch.setattr(config, "data_dir", lambda: data_root)

    ths_history = pd.DataFrame(
        columns=["snapshot_date", "suite", "basket_id", "ticker", "source_shape"]
    )
    raw_snapshot = (asserted_on, {})

    def _build(crosswalk_path: Path, belief_time: str):
        return materialize.build(
            era="reconstruction",
            belief_time=belief_time,
            computed_at=f"{belief_time}T00:00:00Z",
            data_dir=data_root,
            crosswalk_path=crosswalk_path,
            raw_snapshot=raw_snapshot,
            ths_history=ths_history,
        )

    with_block = _build(CROSSWALK, asserted_on)
    without_block = _build(crosswalk_without, asserted_on)

    return SimpleNamespace(
        with_block=with_block,
        without_block=without_block,
        asserted_on=asserted_on,
        build=_build,
        crosswalk_without=crosswalk_without,
        data_root=data_root,
    )


@pytest.mark.needs_full_checkout("data")
def test_production_block_is_the_frozen_r_c3_table():
    hierarchy = DOC["hierarchy"]
    assert len(hierarchy["categories"]) == 10
    assert len(hierarchy["micro_themes"]) == 68
    assert len(hierarchy["parents"]) == 93
    category_ids = {row["id"] for row in hierarchy["categories"]}
    cat_to_theme = sum(1 for row in hierarchy["parents"] if row["parent"] in category_ids)
    assert cat_to_theme == 21
    assert len(hierarchy["parents"]) - cat_to_theme == 72

    hbm = next(row for row in hierarchy["micro_themes"] if row["id"] == "theme:hbm_packaging")
    assert hbm["nominated_from"] == "research:config/theme_pathways.yml"
    hbm_parents = {
        row["parent"]
        for row in hierarchy["parents"]
        if row["child"] == "theme:hbm_packaging"
    }
    assert hbm_parents == {"theme:ai_semiconductors", "theme:memory_storage"}

    crosswalk_text = CROSSWALK.read_text(encoding="utf-8")
    assert "sic_gan_specialty" not in crosswalk_text


@pytest.mark.needs_full_checkout("data")
def test_production_fixture_build_emits_exactly_93_parent_of(production_build):
    view = production_build.with_block
    parent_edges = [row for row in view.edges if row["type"] == "PARENT_OF"]
    assert len(parent_edges) == 93
    for row in parent_edges:
        assert row["valid_from"] == production_build.asserted_on
        assert row["valid_to"] is None
        assert row["source_class"] == "curated"
        assert row["date_provenance"] == "crosswalk"

    tiers = {row["tier"] for row in view.nodes}
    assert sum(1 for row in view.nodes if row.get("tier") == "macro_category") == 10
    assert sum(1 for row in view.nodes if row.get("tier") == "micro_theme") == 68


@pytest.mark.needs_full_checkout("data")
def test_production_build_before_asserted_on_has_no_hierarchy(production_build):
    day_before = (date.fromisoformat(production_build.asserted_on) - timedelta(days=1)).isoformat()
    view = production_build.build(production_build.crosswalk_without, day_before)
    view_with = production_build.build(CROSSWALK, day_before)
    for candidate in (view, view_with):
        assert not [row for row in candidate.edges if row["type"] == "PARENT_OF"]
        assert not [row for row in candidate.nodes if row.get("tier") in ("macro_category", "micro_theme")]


@pytest.mark.needs_full_checkout("data")
def test_every_parent_of_endpoint_is_mastermind_curated(production_build):
    view = production_build.with_block
    family = rights.family_for_source_ref("config/theme_crosswalk.yml")
    assert family == "mastermind_curated"
    assert rights.emission_allowed(family) is True

    nodes_by_id = {row["node_id"]: row for row in view.nodes}
    for row in view.edges:
        if row["type"] != "PARENT_OF":
            continue
        for endpoint in (row["src"], row["dst"]):
            node = nodes_by_id[endpoint]
            assert node["kind"] == "theme"
            assert node["provenance"] == "crosswalk:config/theme_crosswalk.yml"
        for ref in row.get("evidence_refs") or []:
            evidence = next(e for e in view.evidence if e["evidence_id"] == ref)
            assert evidence["source_ref"] == "config/theme_crosswalk.yml"


@pytest.mark.needs_full_checkout("data")
def test_no_vendor_token_in_the_hierarchy_block():
    for text in _walk_strings(DOC["hierarchy"]):
        for bad in VENDOR_SUBSTRINGS:
            assert bad not in text
        for token in re.split(r"[:/_.\-\s|]+", text):
            if token:
                assert token not in VENDOR_TOKENS
        if text.startswith("basket:"):
            assert any(text.startswith(prefix) for prefix in ALLOWED_BASKET_PREFIXES)


@pytest.mark.needs_full_checkout("data")
def test_every_basket_category_is_accounted_for():
    membership = json.loads(MEMBERSHIP.read_text(encoding="utf-8"))
    basket_categories = {
        meta.get("category")
        for meta in membership.get("baskets", {}).values()
        if meta.get("category")
    }

    mapped: set[str] = set()
    for row in DOC["hierarchy"]["categories"]:
        cats = _basket_categories_from_note(row.get("note"))
        assert cats, f"category {row['id']!r} has no basket categories in note"
        assert not (mapped & cats), f"overlap on {mapped & cats}"
        mapped |= cats

    unmapped = basket_categories - mapped - EXCLUDED_BASKET_CATEGORIES
    unknown = mapped - basket_categories
    assert not unmapped and not unknown, (
        f"unmapped={unmapped!r}; unknown mapped={unknown!r}; "
        "remedy is a seat-ruled hierarchy row, never editing this test"
    )
    assert mapped | EXCLUDED_BASKET_CATEGORIES == basket_categories
    for row in DOC["hierarchy"]["categories"]:
        cats = _basket_categories_from_note(row.get("note"))
        assert cats & basket_categories, f"{row['id']!r} maps no live basket category"


@pytest.mark.needs_full_checkout("data")
def test_graph_view_outside_the_hierarchy_is_byte_identical(production_build, tmp_path):
    asserted_on = production_build.asserted_on

    with_node_bytes = _parquet_bytes(
        _non_hierarchy_nodes(production_build.with_block.nodes),
        store.NODE_COLUMNS,
        tmp_path / "with_nodes.parquet",
        sort_key="node_id",
    )
    without_node_bytes = _parquet_bytes(
        _non_hierarchy_nodes(production_build.without_block.nodes),
        store.NODE_COLUMNS,
        tmp_path / "without_nodes.parquet",
        sort_key="node_id",
    )
    with_edge_bytes = _parquet_bytes(
        _non_hierarchy_edges(production_build.with_block.edges),
        store.EDGE_COLUMNS,
        tmp_path / "with_edges.parquet",
        sort_key="edge_id",
    )
    without_edge_bytes = _parquet_bytes(
        _non_hierarchy_edges(production_build.without_block.edges),
        store.EDGE_COLUMNS,
        tmp_path / "without_edges.parquet",
        sort_key="edge_id",
    )

    assert with_node_bytes == without_node_bytes
    assert with_edge_bytes == without_edge_bytes

    with_ev = pd.DataFrame(_evidence_without_hierarchy(production_build.with_block, asserted_on))
    without_ev = pd.DataFrame(_evidence_without_hierarchy(production_build.without_block, asserted_on))
    if not with_ev.empty or not without_ev.empty:
        with_ev = with_ev.sort_values(by=list(with_ev.columns)).reset_index(drop=True)
        without_ev = without_ev.sort_values(by=list(without_ev.columns)).reset_index(drop=True)
        assert with_ev.equals(without_ev)


@pytest.mark.needs_full_checkout("data")
def test_expresses_edge_ids_unchanged_and_non_empty(production_build):
    def expresses_ids(view):
        return {row["edge_id"] for row in view.edges if row["type"] == "EXPRESSES"}

    with_ids = expresses_ids(production_build.with_block)
    without_ids = expresses_ids(production_build.without_block)
    assert with_ids == without_ids
    assert len(with_ids) > 0


@pytest.mark.needs_full_checkout("data")
def test_exposure_map_unchanged_by_the_production_block(production_build):
    asserted_on = production_build.asserted_on
    asof = asserted_on

    with_store = NodesFakeStore(
        list(production_build.with_block.edges),
        nodes=list(production_build.with_block.nodes),
    )
    without_store = NodesFakeStore(
        list(production_build.without_block.edges),
        nodes=list(production_build.without_block.nodes),
    )

    parent_edges = [row for row in with_store.read_edges() if row["type"] == "PARENT_OF"]
    assert len(parent_edges) == 93
    for row in parent_edges:
        assert row["valid_from"] <= asof
        assert row["valid_to"] is None
        assert row["belief_time"] <= asof
    with_nodes = with_store.read_nodes()
    assert sum(row.get("tier") == "macro_category" for row in with_nodes) == 10
    assert sum(row.get("tier") == "micro_theme" for row in with_nodes) == 68

    spec = _spec(list(PRODUCTION_THEME_NODE_IDS))
    day_before = (date.fromisoformat(asserted_on) - timedelta(days=1)).isoformat()
    for clock_name, clock_args in (
        ("default_clock", {}),
        ("knowledge_cutoff_before_asserted_on", {"knowledge_cutoff": day_before}),
    ):
        with_map = to_json(
            _compose(with_store, spec, asof=asof, chain_loader=_chain_loader, **clock_args)
        )
        without_map = to_json(
            _compose(without_store, spec, asof=asof, chain_loader=_chain_loader, **clock_args)
        )
        assert with_map == without_map, f"exposure changed under {clock_name}"
    assert asof >= asserted_on


def test_theme_state_and_selection_cohort_unchanged():
    pending = [
        "engine/theme_graph/theme_state.py",
        "engine/theme_graph/selection_cohort.py",
    ]
    closure: set[str] = set()
    theme_graph_imports: set[str] = set()
    while pending:
        rel = pending.pop()
        if rel in closure:
            continue
        closure.add(rel)
        text = (ROOT / rel).read_text(encoding="utf-8")
        for forbidden in (
            "theme_crosswalk", "read_nodes", "read_edges", "nodes.parquet", "edges.parquet",
        ):
            assert forbidden not in text, f"{rel}: forbidden dependency {forbidden}"
        for node in ast.walk(ast.parse(text, filename=rel)):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("engine.theme_graph.")
            ):
                theme_graph_imports.add(node.module)
                pending.append(node.module.replace(".", "/") + ".py")
    assert theme_graph_imports, "theme-state/selection-cohort import closure is empty"

    source, kw = selection(), inputs()
    before = compose_selection_cohort(source, **kw)
    after = compose_selection_cohort(copy.deepcopy(source), **copy.deepcopy(kw))
    assert before == after


def test_checker_accepts_theme_slug_parent_of_endpoints(tmp_path):
    breaks = tmp_path / "breaks.yml"
    breaks.write_text("breaks: []\n", encoding="utf-8")
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    root = _write_store(tmp_path / "ok", nodes=nodes, edges=edges, evidence=ev)
    breaches = _hierarchy_breaches(root, breaks)
    assert not any("theme id grammar" in b for b in breaches)


def test_checker_refuses_parent_of_endpoint_outside_theme_id_grammar(tmp_path):
    breaks = tmp_path / "breaks.yml"
    breaks.write_text("breaks: []\n", encoding="utf-8")
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    bad = "theme:Bad-Slug"
    nodes = [
        nodes[0],
        {**nodes[1], "node_id": bad},
        nodes[2],
    ]
    edges = [
        {**edges[0], "src": nodes[0]["node_id"], "dst": bad,
         "edge_id": f"parent_of:{nodes[0]['node_id']}->{bad}@2024-01-01"},
        edges[1],
    ]
    root = _write_store(tmp_path / "bad", nodes=nodes, edges=edges, evidence=ev)
    breaches = _hierarchy_breaches(root, breaks)
    assert any("theme id grammar" in b and bad in b for b in breaches)
