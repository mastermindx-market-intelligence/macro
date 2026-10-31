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
from engine.theme_graph.membership_evidence import MICRO_EXPANSION_ASSERTED_ON
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


#: The ratified 2026-10-21 micro-theme expansion (additive display tier;
#: ratification receipts: research/theme_graph/micro_expansion_20261021/).
#: Frozen R-C3/L17 assertions below run on rows asserted BEFORE
#: MICRO_EXPANSION_ASSERTED_ON — the frozen acceptance table must stay exactly
#: what it was — while the appended rows themselves are asserted in
#: tests/test_theme_graph_micro_expansion_20261021.py.
def _frozen(section: str) -> list:
    """Hierarchy rows asserted before the 2026-10-21 expansion — the frozen table."""
    return [row for row in DOC["hierarchy"][section]
            if row["asserted_on"] < MICRO_EXPANSION_ASSERTED_ON]


def _sub_asserted_on() -> str:
    return DOC["hierarchy"]["sub_themes"][0]["asserted_on"]


#: L17 sub_theme population day (Taxonomy V2). Deliberately AFTER the R-C3
#: hierarchy date: a build at belief_time < D must not see any of these rows.
D = "2026-10-13"

#: The frozen L17 sub_theme table (Taxonomy V2 lane L17, seat 6f14c2da). These
#: constants restate §FROZEN SPEC; the frozen crosswalk must agree with them.
SUB_THEME_IDS = frozenset({
    "theme:wfe_process_tools",
    "theme:ai_compute_silicon",
    "theme:missile_munition_chain",
    "theme:satellite_connectivity_services",
    "theme:robot_arm_systems",
    "theme:glp1_therapy_products",
    "theme:glp1_supply_chain",
    "theme:rare_earth_processing_magnets",
    "theme:copper_supply_chain",
    "theme:multi_omics_platforms",
    "theme:pv_manufacturing_chain",
    "theme:ai_clinical_data_devices",
})

THEME_TO_SUB = frozenset({
    ("theme:semicap_equipment", "theme:wfe_process_tools"),
    ("theme:ai_semiconductors", "theme:ai_compute_silicon"),
    ("theme:defense_aerospace", "theme:missile_munition_chain"),
    ("theme:space_satellite", "theme:satellite_connectivity_services"),
    ("theme:robotics_automation", "theme:robot_arm_systems"),
    ("theme:glp1_obesity", "theme:glp1_therapy_products"),
    ("theme:glp1_obesity", "theme:glp1_supply_chain"),
    ("theme:rare_earth_critical_min", "theme:rare_earth_processing_magnets"),
    ("theme:copper_steel_electrify", "theme:copper_supply_chain"),
    ("theme:diagnostics_lifesci", "theme:multi_omics_platforms"),
    ("theme:solar", "theme:pv_manufacturing_chain"),
    ("theme:medical_devices", "theme:ai_clinical_data_devices"),
})

SUB_TO_MICRO = frozenset({
    ("theme:wfe_process_tools", "theme:lithography_tools"),
    ("theme:wfe_process_tools", "theme:etch_deposition_equipment"),
    ("theme:wfe_process_tools", "theme:process_metrology_inspection"),
    ("theme:ai_compute_silicon", "theme:gpu_merchant_accelerators"),
    ("theme:ai_compute_silicon", "theme:custom_asic_silicon"),
    ("theme:missile_munition_chain", "theme:missiles_munitions_effects"),
    ("theme:missile_munition_chain", "theme:missile_propulsion_supply"),
    ("theme:satellite_connectivity_services", "theme:satellite_broadband_services"),
    ("theme:satellite_connectivity_services", "theme:direct_to_device_connectivity"),
    ("theme:robot_arm_systems", "theme:collaborative_robot_arms"),
    ("theme:robot_arm_systems", "theme:industrial_robot_arms"),
    ("theme:glp1_therapy_products", "theme:glp1_incretin_therapies"),
    ("theme:glp1_therapy_products", "theme:oral_glp1_formulations"),
    ("theme:glp1_supply_chain", "theme:glp1_api_manufacturing"),
    ("theme:glp1_supply_chain", "theme:fill_finish_delivery_devices"),
    ("theme:rare_earth_processing_magnets", "theme:rare_earth_separation_refining"),
    ("theme:rare_earth_processing_magnets", "theme:ndfeb_permanent_magnets"),
    ("theme:copper_supply_chain", "theme:copper_mining"),
    ("theme:copper_supply_chain", "theme:refined_copper"),
    ("theme:copper_supply_chain", "theme:copper_wire_cable"),
    ("theme:multi_omics_platforms", "theme:liquid_biopsy_assays"),
    ("theme:multi_omics_platforms", "theme:genomic_sequencing"),
    ("theme:multi_omics_platforms", "theme:proteomics_discovery_platforms"),
    ("theme:pv_manufacturing_chain", "theme:polysilicon_solar_feedstock"),
    ("theme:pv_manufacturing_chain", "theme:pv_cell_module_manufacturing"),
    ("theme:ai_clinical_data_devices", "theme:medical_imaging"),
    ("theme:ai_clinical_data_devices", "theme:remote_patient_monitoring"),
})

#: value_chain_position is a DISPLAY attribute on exactly these 4 sub rows. The
#: node store is write-once on node_id (store.NODE_KEY, append keeps the FIRST
#: row), so micro/category rows must never carry it in this lane — a later
#: attribute on an existing id would be silently dropped by the store.
SUB_VCP = {
    "theme:satellite_connectivity_services": "downstream",
    "theme:robot_arm_systems": "midstream",
    "theme:glp1_therapy_products": "midstream",
    "theme:ai_clinical_data_devices": "midstream",
}

#: Micros that keep their TWO theme parents directly — no sub parent for them.
MULTI_PARENT_MICROS = frozenset({
    "theme:hbm_packaging",
    "theme:hv_transformers_switchgear",
    "theme:military_space_communications",
    "theme:surgical_robotics_systems",
})


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
        if row.get("tier") not in ("macro_category", "sub_theme", "micro_theme")
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
    # Date-scoped (2026-10-21 micro expansion): the frozen R-C3 table is read
    # from rows asserted before the expansion date; the appended display-tier
    # rows are additive and asserted separately.
    assert len(_frozen("categories")) == 10
    assert len(_frozen("micro_themes")) == 68
    assert len(hierarchy["micro_themes"]) > len(_frozen("micro_themes"))
    # R-C3 parents: dated at the incumbent asserted_on. The L17 sub_theme rows
    # (dated D) are counted separately — the R-C3 table itself is unchanged.
    rc3 = _asserted_on()
    rc3_parents = [row for row in hierarchy["parents"] if row["asserted_on"] == rc3]
    assert len(rc3_parents) == 93
    assert len(_frozen("parents")) == 132
    category_ids = {row["id"] for row in _frozen("categories")}
    cat_to_theme = sum(1 for row in rc3_parents if row["parent"] in category_ids)
    assert cat_to_theme == 21
    assert len(rc3_parents) - cat_to_theme == 72

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


# ---------------------------------------------------------------------------
# L17 — sub_theme tier population (Taxonomy V2)
# ---------------------------------------------------------------------------


def test_l17_sub_theme_rows_match_the_frozen_table():
    """YAML-only pin: the crosswalk's frozen sub_theme block IS the frozen L17 table.

    Date-scoped (2026-10-21 micro expansion): rows asserted on/after the
    expansion date are the additive display tier, pinned in
    tests/test_theme_graph_micro_expansion_20261021.py — every assertion here
    reads the frozen subset."""
    hierarchy = DOC["hierarchy"]
    sub_rows = _frozen("sub_themes")
    assert len(sub_rows) == 12
    assert {row["id"] for row in sub_rows} == set(SUB_THEME_IDS)

    parents = _frozen("parents")
    rc3 = _asserted_on()
    assert {row["asserted_on"] for row in sub_rows} == {D}
    assert D > rc3
    dated_d = [row for row in parents if row["asserted_on"] != rc3]
    assert len(dated_d) == 39
    assert {row["asserted_on"] for row in dated_d} == {D}

    t2s = {(row["parent"], row["child"]) for row in dated_d
           if row["child"] in set(SUB_THEME_IDS)}
    s2m = {(row["parent"], row["child"]) for row in dated_d
           if row["parent"] in set(SUB_THEME_IDS)}
    assert t2s == set(THEME_TO_SUB)
    assert s2m == set(SUB_TO_MICRO)
    assert len(t2s) + len(s2m) == 39  # the D-dated parents are exactly these

    cat_ids = {row["id"] for row in _frozen("categories")}
    micro_ids = {row["id"] for row in _frozen("micro_themes")}
    canonical_theme_ids = {row["theme_node_id"] for row in DOC["themes"]}
    parents_of: dict[str, set[str]] = {}
    for row in dated_d:
        parents_of.setdefault(row["child"], set()).add(row["parent"])
    micro_children_of: dict[str, set[str]] = {}
    for parent, child in s2m:
        micro_children_of.setdefault(parent, set()).add(child)
    for sub in sorted(SUB_THEME_IDS):
        ups = parents_of.get(sub, set())
        assert len(ups) == 1, f"{sub} must have exactly one theme parent"
        parent = next(iter(ups))
        assert parent in canonical_theme_ids, f"{sub} parent {parent!r} is not a theme"
        assert parent not in cat_ids | set(SUB_THEME_IDS) | micro_ids
        assert micro_children_of.get(sub), f"{sub} has no micro_theme child"

    vcp = {
        row["id"]: row["value_chain_position"]
        for section in ("categories", "sub_themes", "micro_themes")
        for row in _frozen(section)
        if "value_chain_position" in row
    }
    assert vcp == SUB_VCP

    sub_children = {child for _, child in s2m}
    assert not (sub_children & set(MULTI_PARENT_MICROS))

    for row in sub_rows:
        assert row["name_en"], row["id"]
        assert row["name_zh"], row["id"]
        assert row["nominated_from"].startswith("research:"), row["id"]


@pytest.mark.needs_full_checkout("data")
def test_l17_production_build_at_d_emits_the_full_132_edge_hierarchy(production_build):
    view = production_build.build(CROSSWALK, D)
    parent_edges = [row for row in view.edges if row["type"] == "PARENT_OF"]
    rc3 = _asserted_on()
    assert len(parent_edges) == 132
    assert sum(1 for row in parent_edges if row["valid_from"] == rc3) == 93
    assert sum(1 for row in parent_edges if row["valid_from"] == D) == 39
    for row in parent_edges:
        assert row["valid_to"] is None
        assert row["source_class"] == "curated"
        assert row["date_provenance"] == "crosswalk"

    assert sum(1 for row in view.nodes if row.get("tier") == "macro_category") == 10
    assert sum(1 for row in view.nodes if row.get("tier") == "sub_theme") == 12
    assert sum(1 for row in view.nodes if row.get("tier") == "micro_theme") == 68

    hierarchy = DOC["hierarchy"]
    rows_by_id = {
        row["id"]: row
        for section in ("sub_themes", "micro_themes")
        for row in hierarchy[section]
    }
    nodes_by_id = {row["node_id"]: row for row in view.nodes}
    for sub_id in sorted(SUB_THEME_IDS):
        node = nodes_by_id[sub_id]
        expected = {"nominated_from": rows_by_id[sub_id]["nominated_from"]}
        if sub_id in SUB_VCP:
            expected["value_chain_position"] = SUB_VCP[sub_id]
        assert json.loads(node["source_meta"]) == expected, sub_id
        assert node["kind"] == "theme"
        assert node["provenance"] == "crosswalk:config/theme_crosswalk.yml"
    for micro in _frozen("micro_themes"):
        node = nodes_by_id[micro["id"]]
        assert json.loads(node["source_meta"]) == {
            "nominated_from": micro["nominated_from"]}, micro["id"]

    # PIT law at the expansion boundary: no row asserted on/after the
    # 2026-10-21 expansion date may appear in a build believed at D.
    expansion_ids = {
        row["id"]
        for section in ("sub_themes", "micro_themes")
        for row in hierarchy[section]
        if row["asserted_on"] >= MICRO_EXPANSION_ASSERTED_ON
    }
    assert not (expansion_ids & set(nodes_by_id))
    assert all(row["valid_from"] < MICRO_EXPANSION_ASSERTED_ON for row in parent_edges)

    for row in parent_edges:
        for endpoint in (row["src"], row["dst"]):
            node = nodes_by_id[endpoint]
            assert node["kind"] == "theme"
            assert node["provenance"] == "crosswalk:config/theme_crosswalk.yml"
        for ref in row.get("evidence_refs") or []:
            evidence = next(e for e in view.evidence if e["evidence_id"] == ref)
            assert evidence["source_ref"] == "config/theme_crosswalk.yml"


@pytest.mark.needs_full_checkout("data")
def test_l17_production_build_the_day_before_d_has_no_sub_themes(production_build):
    view = production_build.build(CROSSWALK, "2026-10-12")
    assert sum(1 for row in view.edges if row["type"] == "PARENT_OF") == 93
    assert not [row for row in view.nodes if row.get("tier") == "sub_theme"]


@pytest.mark.needs_full_checkout("data")
def test_l17_sub_theme_population_is_additive_at_d(production_build, tmp_path):
    """Removing the L17 rows must change NOTHING except the 12 sub nodes and the
    39 new PARENT_OF edges — the write-once store forbids anything subtler.

    Date-scoped (2026-10-21 micro expansion): the reduced document is the
    FROZEN table (rows asserted before the expansion date) minus its L17 slice,
    so no expansion parent endpoint dangles; at D the expansion rows are
    PIT-invisible anyway, so the full-vs-reduced delta is still exactly the
    L17 sub nodes and the 39 D-dated PARENT_OF edges."""
    reduced = copy.deepcopy(DOC)
    for section in ("categories", "sub_themes", "micro_themes", "parents"):
        reduced["hierarchy"][section] = [
            row for row in reduced["hierarchy"][section]
            if row["asserted_on"] < MICRO_EXPANSION_ASSERTED_ON
        ]
    reduced["hierarchy"]["sub_themes"] = [
        row for row in reduced["hierarchy"]["sub_themes"] if row["asserted_on"] != D
    ]
    reduced["hierarchy"]["parents"] = [
        row for row in reduced["hierarchy"]["parents"] if row["asserted_on"] != D
    ]
    reduced_path = tmp_path / "theme_crosswalk_reduced.yml"
    reduced_path.write_text(
        yaml.safe_dump(reduced, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    full = production_build.build(CROSSWALK, D)
    base = production_build.build(reduced_path, D)

    full_nodes = {row["node_id"]: row for row in full.nodes}
    base_nodes = {row["node_id"]: row for row in base.nodes}
    assert set(full_nodes) - set(base_nodes) == set(SUB_THEME_IDS)
    assert not set(base_nodes) - set(full_nodes)
    for node_id in sorted(set(full_nodes) & set(base_nodes)):
        for col in store.NODE_COLUMNS:
            assert full_nodes[node_id].get(col) == base_nodes[node_id].get(col), (
                node_id, col)

    full_edges = {row["edge_id"]: row for row in full.edges}
    base_edges = {row["edge_id"]: row for row in base.edges}
    added_edges = set(full_edges) - set(base_edges)
    assert len(added_edges) == 39
    assert all(full_edges[eid]["type"] == "PARENT_OF" for eid in added_edges)
    assert not set(base_edges) - set(full_edges)
    for edge_id in sorted(set(full_edges) & set(base_edges)):
        for col in store.EDGE_COLUMNS:
            assert full_edges[edge_id].get(col) == base_edges[edge_id].get(col), (
                edge_id, col)


@pytest.mark.needs_full_checkout("data")
def test_l17_graph_view_outside_the_hierarchy_is_byte_identical_at_d(
        production_build, tmp_path):
    with_node_bytes = _parquet_bytes(
        _non_hierarchy_nodes(production_build.build(CROSSWALK, D).nodes),
        store.NODE_COLUMNS,
        tmp_path / "with_nodes.parquet",
        sort_key="node_id",
    )
    without_node_bytes = _parquet_bytes(
        _non_hierarchy_nodes(
            production_build.build(production_build.crosswalk_without, D).nodes),
        store.NODE_COLUMNS,
        tmp_path / "without_nodes.parquet",
        sort_key="node_id",
    )
    with_edge_bytes = _parquet_bytes(
        _non_hierarchy_edges(production_build.build(CROSSWALK, D).edges),
        store.EDGE_COLUMNS,
        tmp_path / "with_edges.parquet",
        sort_key="edge_id",
    )
    without_edge_bytes = _parquet_bytes(
        _non_hierarchy_edges(
            production_build.build(production_build.crosswalk_without, D).edges),
        store.EDGE_COLUMNS,
        tmp_path / "without_edges.parquet",
        sort_key="edge_id",
    )

    assert with_node_bytes == without_node_bytes
    assert with_edge_bytes == without_edge_bytes

    with_ev = pd.DataFrame(_evidence_without_hierarchy(
        production_build.build(CROSSWALK, D), D))
    without_ev = pd.DataFrame(_evidence_without_hierarchy(
        production_build.build(production_build.crosswalk_without, D), D))
    if not with_ev.empty or not without_ev.empty:
        with_ev = with_ev.sort_values(by=list(with_ev.columns)).reset_index(drop=True)
        without_ev = without_ev.sort_values(by=list(without_ev.columns)).reset_index(drop=True)
        assert with_ev.equals(without_ev)


@pytest.mark.needs_full_checkout("data")
def test_l17_expresses_and_member_of_edges_untouched_by_sub_themes_at_d(
        production_build):
    def expresses_ids(view):
        return {row["edge_id"] for row in view.edges if row["type"] == "EXPRESSES"}

    full = production_build.build(CROSSWALK, D)
    without = production_build.build(production_build.crosswalk_without, D)
    full_ids = expresses_ids(full)
    assert full_ids == expresses_ids(without)
    assert len(full_ids) > 0

    for view in (full, without):
        for row in view.edges:
            if row["type"] in ("EXPRESSES", "MEMBER_OF"):
                assert row["src"] not in SUB_THEME_IDS, row["edge_id"]
                assert row["dst"] not in SUB_THEME_IDS, row["edge_id"]


@pytest.mark.needs_full_checkout("data")
def test_l17_production_store_at_d_has_no_hierarchy_breaches(production_build, tmp_path):
    view = production_build.build(CROSSWALK, D)
    root = _write_store(
        tmp_path / "at_d", nodes=view.nodes, edges=view.edges, evidence=view.evidence)
    breaks_file = tmp_path / "breaks.yml"
    breaks_file.write_text("breaks: []\n", encoding="utf-8")
    assert _hierarchy_breaches(root, breaks_file) == []
