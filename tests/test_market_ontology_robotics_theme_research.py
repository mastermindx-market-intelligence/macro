"""tests/test_market_ontology_robotics_theme_research.py — per-case behavior
tests for the pure Robotics research composer (R2).

Operation gmi-robotics-fable-ceo-e2e-20260923-chairman-001 (carrier #7908).
One test per R1 fixture case, named for the acceptance doc's RBV ids the
fixture cites, plus unit tests of the three public helpers. The composer is
pure in-memory composition: no I/O, no network, no store, no LLM, no scoring,
no ranking by magnitude. These tests pin THAT law on the composed output.

Tests that import the shared semiconductor module directly carry an
``xfail(strict=True)`` marker conditioned on the import (the shared types are
pinned to #7870 c6c67c87); every other test runs through the robotics module
alone, whose fallback keeps it green on a base without the shared module.
"""

from __future__ import annotations

import copy
import dataclasses
import json

import pytest

import engine.market_ontology.robotics_theme_research as robotics
from tests.robotics_research_helpers import load_case, load_bundle_case

try:
    import engine.market_ontology.semiconductor_theme_research as semiconductor
    HAS_SHARED_TYPES = True
except ImportError:  # pragma: no cover - explained by the xfail-strict marker
    HAS_SHARED_TYPES = False

try:
    from engine.theme_graph.curation_assertion import encode_assertion
    HAS_CODEC = True
except Exception:  # pragma: no cover - codec predates the shared types
    HAS_CODEC = False

SHARED_TYPES_REASON = (
    "shared composition types not on this base; pinned to #7870 c6c67c87"
)
CODEC_REASON = "assertion codec not on this base"


def compose(name: str, **query_overrides):
    query, bundle = load_bundle_case(name)
    if query_overrides:
        query = dataclasses.replace(query, **query_overrides)
    return robotics.compose_robotics_research(query, bundle), query, bundle


def view_of(response, view):
    return response["industrial_views"][view]


def rows_of(name: str, view: str, **query_overrides):
    response, _, _ = compose(name, view=view, **query_overrides)
    return response, view_of(response, view)["rows"]


def walk_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from walk_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from walk_keys(item)




def restamp(payload: dict, **changes) -> dict:
    mutant = copy.deepcopy(dict(payload))
    mutant.update(changes)
    mutant["curation_revision"] = None
    return json.loads(encode_assertion(mutant))


# ---------------------------------------------------------------------------
# Frozen interface
# ---------------------------------------------------------------------------

def test_frozen_constants():
    assert robotics.SCHEMA_ID == "robotics_theme_research.v1"
    assert robotics.EVIDENCE_SCHEMA_ID == "robotics_theme_research.evidence.v1"
    assert robotics.DEFINITION_VERSION == "2026-09-24.1"
    assert robotics.ANCHOR_THEME_ID == "robotics_automation"
    assert robotics.SLICES == ("precision_motion", "perception")
    assert robotics.VIEWS == ("composition", "manufacturing", "commercial",
                              "capacity", "economics")
    assert robotics.AUTHORITY == {"can_rank": False, "can_gate": False,
                                  "can_size": False, "can_originate": False,
                                  "can_open_entry": False}


@pytest.mark.xfail(condition=not robotics.SHARED_TYPES, strict=True,
                  reason=SHARED_TYPES_REASON)
def test_shared_types_are_the_shared_owner_types():
    assert robotics.SHARED_TYPES is True
    assert robotics.ResearchQuery is semiconductor.ResearchQuery
    assert robotics.OwnerBundle is semiconductor.OwnerBundle
    assert robotics.ResearchRefusal is semiconductor.ResearchRefusal


def test_refusal_shape():
    exc = robotics.ResearchRefusal("not_available")
    assert isinstance(exc, ValueError)
    assert exc.code == "not_available"
    assert str(exc) == "not_available"


def test_refusal_ladder_order():
    query, bundle = load_bundle_case("witness_perception_orbbec_twinny")
    # anchor first, then slice, then view, then the shared query contract
    with pytest.raises(robotics.ResearchRefusal) as exc:
        robotics.compose_robotics_research(
            dataclasses.replace(query, anchor_theme_id="semiconductors"), bundle)
    assert exc.value.code == "not_available"
    with pytest.raises(robotics.ResearchRefusal) as exc:
        robotics.compose_robotics_research(
            dataclasses.replace(query, slice_key="memory"), bundle)
    assert exc.value.code == "slice_not_supported"
    with pytest.raises(robotics.ResearchRefusal) as exc:
        robotics.compose_robotics_research(
            dataclasses.replace(query, view="supply"), bundle)
    assert exc.value.code == "view_not_supported"
    with pytest.raises(robotics.ResearchRefusal) as exc:
        robotics.compose_robotics_research(
            dataclasses.replace(query, limit=0), bundle)
    assert exc.value.code == "limit_out_of_range"
    with pytest.raises(robotics.ResearchRefusal) as exc:
        robotics.compose_robotics_research(
            dataclasses.replace(query, offset=-1), bundle)
    assert exc.value.code == "offset_negative"
    with pytest.raises(robotics.ResearchRefusal) as exc:
        robotics.compose_robotics_research(
            dataclasses.replace(query, offset=1), bundle)
    assert exc.value.code == "expected_generation_required"


# ---------------------------------------------------------------------------
# RBV-01 — catalog capability is never a supply contract
# ---------------------------------------------------------------------------

def test_rbv01_catalog_capability_is_not_a_supply_contract():
    response, _, _ = compose("witness_motion_parker_kseries")
    rows = view_of(response, "composition")["rows"]
    assert len(rows) == 1
    row = rows[0]
    assert row["predicate"] == "PRODUCT_CAPABILITY"
    assert row["statement_mode"] == "CATALOG_DESCRIPTION"
    assert row["relation_kind"] == "catalog_capability"
    assert row["selector"] == "prd:Parker Hannifin/K-Series frameless motor family"
    assert row["configuration"] is None
    companies = response["companies"]["rows"]
    assert [c["source_business_label"] for c in companies] == ["Parker Hannifin"]
    for role in companies[0]["roles"]:
        assert role["role"] == "subject", "catalog capability never yields supplier_to"
    edges = view_of(response, "composition")["graph"]["edges"]
    assert [e["relation_kind"] for e in edges] == ["catalog_capability"]
    assert not any("supplies" in json.dumps(e) for e in edges)


# ---------------------------------------------------------------------------
# RBV-02 / RBV-12 / RBV-15 — configuration-bound inclusion, no merge, clocks
# ---------------------------------------------------------------------------

ORBBEC_SELECTOR = "prd:Orbbec/Gemini 335 stereo depth camera"
ORBBEC_OBJECT = "obj:Orbbec/Twinny NarGo order-picking robot"


def test_rbv02_inclusion_is_configuration_bound():
    response, _, _ = compose("witness_perception_orbbec_twinny")
    rows = view_of(response, "composition")["rows"]
    assert len(rows) == 1
    row = rows[0]
    assert row["observation"] == {
        "value": 2, "value_high": None, "unit": "camera",
        "quantity_basis": "per_robot", "gross_net_basis": None,
        "stock_flow": None, "estimate_status": "reported", "precision": "integer",
    }
    assert row["object_configuration"] == (
        "Twinny NarGo described configuration (as presented in the vendor case study)")
    assert row["selector"] == ORBBEC_SELECTOR
    assert row["object_selector"] == ORBBEC_OBJECT
    assert row["kind"] == "product"
    # the count is bound to THIS configuration; no inference key exists
    assert "camera_count_family" not in json.dumps(response)
    # RBV-12: the source-local subject never merges into a global product id
    assert not any(k.startswith("global_") for k in walk_keys(response))


def test_rbv12_similar_labels_never_merge():
    response, _, _ = compose("unresolved_identity_source_only")
    rows = view_of(response, "composition")["rows"]
    assert len(rows) == 2
    selectors = [r["selector"] for r in rows]
    assert selectors == [
        "prd:Orbbec/Gemini 335 stereo depth camera family",
        "prd:Twinny/NarGo order-picking AMR",
    ]


def test_rbv15_unknown_publication_stays_separate_from_retrieval():
    response, _, _ = compose("witness_motion_parker_kseries")
    row = view_of(response, "composition")["rows"][0]
    clocks = row["source_clocks"]
    assert clocks["published_at"] is None
    assert clocks["published_at_grain"] == "unknown"
    assert clocks["observed_at"] == "2026-09-23T06:10:00Z"
    assert clocks["retained_at"] == "2026-09-23T06:15:00Z"
    assert clocks["business_valid_from"] is None and clocks["business_valid_to"] is None


# ---------------------------------------------------------------------------
# RBV-03 — a successor generation inherits nothing; order invariance
# ---------------------------------------------------------------------------

def test_rbv03_successor_generation_does_not_inherit():
    response, _, _ = compose("newer_generation_no_inheritance")
    rows = view_of(response, "composition")["rows"]
    assert len(rows) == 2
    by_value = {r["observation"]["value"]: r for r in rows}
    counted, successor = by_value[2], by_value[None]
    assert counted["observation"]["quantity_basis"] == "per_robot"
    assert counted["object_configuration"] == "NarGo generation A (described configuration)"
    assert successor["object_configuration"] == (
        "NarGo generation B (successor; camera count not documented)")
    assert counted["curation_revision"] != successor["curation_revision"]
    assert counted["selector"] != successor["selector"]


def test_rbv03_bundle_order_never_changes_the_composition():
    first_query, bundle = load_bundle_case("newer_generation_no_inheritance")
    first = robotics.compose_robotics_research(first_query, bundle)
    shuffled = dataclasses.replace(
        bundle, assertions=tuple(reversed(bundle.assertions)))
    second = robotics.compose_robotics_research(first_query, shuffled)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


# ---------------------------------------------------------------------------
# RBV-04 — a target is a target; RBV-05 — reciprocal roles stay two edges
# ---------------------------------------------------------------------------

def test_rbv04_deployment_target_is_not_a_deployment():
    response, _, _ = compose("schaeffler_hexagon_reciprocal")
    rows = view_of(response, "commercial")["rows"]
    target = next(r for r in rows if r["predicate"] == "DEPLOYMENT_TARGET")
    assert target["statement_mode"] == "FORWARD_TARGET"
    assert target["relation_kind"] == "deployment_target"
    assert target["observation"]["value"] == 1000
    assert target["observation"]["estimate_status"] == "target"
    assert target["source_clocks"]["business_valid_from"] is None
    assert not any(r["relation_kind"] == "reported_deployment" for r in rows)
    # the announced development agreement is its own row, never converted
    agreement = next(r for r in rows
                     if r["predicate"] == "ANNOUNCED_DEVELOPMENT_AGREEMENT")
    assert agreement["relation_kind"] == "announced_development"
    assert agreement["observation"]["value"] is None


def test_rbv04_announcement_is_not_qualified_capacity():
    response, _, _ = compose("stabilus_synapticon_joint_product", view="capacity")
    capacity = view_of(response, "capacity")
    assert capacity["rows"] == []
    assert capacity["status"] == "unavailable"
    assert capacity["reason"] == "no_capacity_evidence"
    commercial_rows = view_of(response, "commercial")["rows"]
    assert len(commercial_rows) == 1
    assert commercial_rows[0]["relation_kind"] == "announced_development"
    assert commercial_rows[0]["observation"]["value"] is None


def test_rbv05_reciprocal_roles_stay_two_directed_edges():
    response, _, _ = compose("schaeffler_hexagon_reciprocal")
    edges = view_of(response, "commercial")["graph"]["edges"]
    assert len(edges) == 2
    kinds = [e["relation_kind"] for e in edges]
    assert sorted(kinds) == ["announced_development", "deployment_target"]
    refs = {e["assertion_ref"] for e in edges}
    assert len(refs) == 2, "reciprocal roles are never merged into one edge"


# ---------------------------------------------------------------------------
# RBV-06 / 07 / 08 — Sanhua scope discipline; undisclosed stays null
# ---------------------------------------------------------------------------

def test_rbv067_no_customer_or_facility_keys_are_invented():
    response, _, _ = compose("sanhua_actuator_scaleup")
    keys = set(walk_keys(response))
    assert not any("customer" in k for k in keys)
    assert not any("facility" in k for k in keys)
    assert not any(k.startswith("plant") for k in keys)


def test_rbv08_not_separately_disclosed_is_null_not_zero():
    response, _, _ = compose("sanhua_actuator_scaleup")
    financial_rows = view_of(response, "economics")["rows"]
    assert len(financial_rows) == 1
    financial = financial_rows[0]
    assert financial["predicate"] == "REPORTED_FINANCIAL_MEASURE"
    assert financial["observation"]["value"] is None
    assert financial["period"] == "2026H1"
    assert financial["denominator"] == "group revenue"
    assert "a robotics revenue figure (not separately disclosed)" \
        in financial["does_not_establish"]
    assert financial["relation_kind"] == "financial_observation"
    capacity_rows = view_of(response, "capacity")["rows"]
    assert len(capacity_rows) == 1
    operating = capacity_rows[0]
    assert operating["predicate"] == "REPORTED_OPERATING_MEASURE"
    assert operating["observation"]["value"] is None
    assert operating["relation_kind"] == "operating_observation"
    assert view_of(response, "composition")["rows"] == []


# ---------------------------------------------------------------------------
# RBV-09 — incompatible financial bases; totals never computed
# ---------------------------------------------------------------------------

def test_rbv09_compatible_financial_basis_is_strict_equality():
    a = {"scope": {"period": "2026H1", "denominator": "group revenue"},
         "observation": {"unit": "JPY_million", "gross_net_basis": None}}
    same = {"scope": {"period": "2026H1", "denominator": "group revenue"},
            "observation": {"unit": "JPY_million", "gross_net_basis": None}}
    assert robotics.compatible_financial_basis(a, same) is True
    for mutant in (
        {"scope": {"period": "2025H2", "denominator": "group revenue"},
         "observation": {"unit": "JPY_million", "gross_net_basis": None}},
        {"scope": {"period": "2026H1", "denominator": "segment revenue"},
         "observation": {"unit": "JPY_million", "gross_net_basis": None}},
        {"scope": {"period": "2026H1", "denominator": "group revenue"},
         "observation": {"unit": "USD_million", "gross_net_basis": None}},
        {"scope": {"period": "2026H1", "denominator": "group revenue"},
         "observation": {"unit": "JPY_million", "gross_net_basis": "net"}},
    ):
        assert robotics.compatible_financial_basis(a, mutant) is False


def test_rbv09_financial_rows_are_never_summed():
    response, _, _ = compose("rights_partial", view="economics")
    view = view_of(response, "economics")
    assert len(view["rows"]) == 2
    assert view["total"] == {"value": None, "reason": "totals_not_computed"}
    for v in response["industrial_views"].values():
        assert v["total"]["value"] is None


# ---------------------------------------------------------------------------
# RBV-10 — ownership roles; announcement grain never becomes closing
# ---------------------------------------------------------------------------

def test_rbv10_announced_ownership_keeps_party_roles():
    response, _, _ = compose("zebra_skild_ownership", view="commercial")
    rows = view_of(response, "commercial")["rows"]
    assert len(rows) == 2
    companies = response["companies"]["rows"]
    assert [c["source_business_label"] for c in companies] == ["Zebra Technologies"]
    roles = {r["statement_mode"]: r["role"] for r in companies[0]["roles"]}
    assert roles["ANNOUNCED_ARRANGEMENT"] == "announced_seller"
    assert roles["REPORTED_FACT"] == "owner_reported_effective_date_unknown"
    security = companies[0]["security"]
    assert security == {"security_id": "NASDAQ:ZBRA",
                        "listing_valid_from": None, "listing_valid_to": None}


def test_rbv10_ptc_divestiture_is_seller_side():
    response, _, _ = compose("ptc_tpg_ownership", view="commercial")
    companies = {c["source_business_label"]: c
                 for c in response["companies"]["rows"]}
    assert set(companies) == {"PTC"}, "TPG has an identity row but is never a subject"
    assert companies["PTC"]["roles"][0]["role"] == "announced_seller"


@pytest.mark.xfail(condition=not HAS_CODEC, strict=True, reason=CODEC_REASON)
def test_rbv10_dated_completion_becomes_owner_from_and_acquirer_marker_scans():
    query, bundle = load_bundle_case("zebra_skild_ownership")
    case = load_case("zebra_skild_ownership")
    assertions = list(bundle.assertions)
    identity = tuple(case["bundle"]["identity_results"])
    dated = restamp(
        assertions[1],
        temporal={"business_valid_from": "2026-04-20", "business_valid_to": None})
    acquirer = restamp(
        assertions[0],
        object={**assertions[0]["object"],
                "source_product_label": "Robotics Automation business "
                                        "(Zebra acquires Skild AI assets)"})
    rebuilt = dataclasses.replace(
        bundle,
        assertions=(dated, acquirer),
        revision_tuple=(
            ("assertion", dated["curation_revision"]),
            ("assertion", acquirer["curation_revision"]),
            ("identity", "identity-vintage-r01"),
        ),
        identity_results=identity,
    )
    response = robotics.compose_robotics_research(
        dataclasses.replace(query, view="commercial"), rebuilt)
    roles = {r["statement_mode"]: r["role"]
             for r in response["companies"]["rows"][0]["roles"]}
    assert roles["REPORTED_FACT"] == "owner_from:2026-04-20"
    assert roles["ANNOUNCED_ARRANGEMENT"] == "announced_acquirer"
    row = next(r for r in view_of(response, "commercial")["rows"]
               if r["statement_mode"] == "REPORTED_FACT")
    assert row["source_clocks"]["business_valid_from"] == "2026-04-20"


# ---------------------------------------------------------------------------
# RBV-11 — unresolved listing keeps evidence, loses the security join
# ---------------------------------------------------------------------------

def test_rbv11_unresolved_identity_keeps_source_evidence_only():
    response, _, _ = compose("unresolved_identity_source_only")
    rows = view_of(response, "composition")["rows"]
    assert len(rows) == 2
    companies = {c["source_business_label"]: c
                 for c in response["companies"]["rows"]}
    assert set(companies) == {"Orbbec", "Twinny"}
    for row in companies.values():
        assert row["security"] is None
        assert row["navigation"]["status"] == "unavailable"
        assert row["navigation"]["reason"] == "identity_unresolved"
        assert row["navigation"]["href"] is None
    assert companies["Orbbec"]["company_node_id"] == "co:cn:688322.SS"
    assert companies["Twinny"]["company_node_id"] is None
    assert response["companies"]["status"] == "degraded"
    assert response["companies"]["reason"] == "identity_incomplete"
    # RBV-11 forbids the price/valuation/portfolio join, not the evidence
    keys = set(walk_keys(response))
    assert not keys & {"price", "valuation", "portfolio", "performance"}


# ---------------------------------------------------------------------------
# RBV-16 — two statements at one URL are two assertions
# ---------------------------------------------------------------------------

def test_rbv16_same_url_two_statements_stay_distinct():
    response, _, _ = compose("same_url_two_statements")
    rows = view_of(response, "composition")["rows"]
    assert len(rows) == 2
    assert rows[0]["curation_revision"] != rows[1]["curation_revision"]
    assert rows[0]["assertion_ref"] != rows[1]["assertion_ref"]
    case = load_case("same_url_two_statements")
    uri = case["bundle"]["assertions"][0]["source"]["source_uri"]
    assert uri == case["bundle"]["assertions"][1]["source"]["source_uri"]
    assert all(r["review"]["current"] is True for r in rows)
    assert {r["independent_source_count"] for r in rows} == {1}
    assert all(r["corroboration_refs"] == [] for r in rows)


# ---------------------------------------------------------------------------
# RBV-17 — correction lineage; the predecessor survives, flagged
# ---------------------------------------------------------------------------

def test_rbv17_correction_supersedes_without_deleting():
    response, _, _ = compose("corrected_same_url")
    rows = view_of(response, "composition")["rows"]
    assert len(rows) == 2
    successor = next(r for r in rows if r["correction"]["predecessor_revision"])
    predecessor = next(r for r in rows
                       if not r["correction"]["predecessor_revision"])
    assert successor["correction"]["predecessor_revision"] \
        == predecessor["curation_revision"]
    assert successor["correction"]["reason"]
    assert successor["review"]["current"] is True
    assert predecessor["review"]["current"] is False
    assert "superseded_present" in response["limitations"]
    # both revisions stay authorized evidence
    refs = {e["curation_revision"] for e in response["evidence_refs"]
            if e["kind"] == "assertion"}
    assert {predecessor["curation_revision"],
            successor["curation_revision"]} <= refs
    # the superseded row leaves the graph and the company roles
    edges = view_of(response, "composition")["graph"]["edges"]
    assert {e["assertion_ref"] for e in edges} == {successor["assertion_ref"]}
    roles = response["companies"]["rows"][0]["roles"]
    assert {r["assertion_ref"] for r in roles} == {successor["assertion_ref"]}


# ---------------------------------------------------------------------------
# RBV-18 — held review leaves current rows, stays in evidence (latest mode)
# ---------------------------------------------------------------------------

def test_rbv18_held_review_is_excluded_but_retained():
    response, _, _ = compose("review_expired_or_withdrawn")
    rows = view_of(response, "composition")["rows"]
    assert len(rows) == 1
    assert rows[0]["review"]["disposition"] == "accepted"
    assert rows[0]["review"]["current"] is True
    assert rows[0]["review"]["review_due_at"] == "2026-06-01T00:00:00Z"
    assert "held_present" in response["limitations"]
    assert "review_expired_present" not in response["limitations"]
    refs = {e["curation_revision"] for e in response["evidence_refs"]
            if e["kind"] == "assertion"}
    assert len(refs) == 2, "the held assertion remains authorized evidence"


# ---------------------------------------------------------------------------
# RBV-21 — the purchase boundary refuses double counting
# ---------------------------------------------------------------------------

def test_rbv21_cost_items_refuse_double_count():
    case = load_case("integrated_assembly_double_count")
    items = case["cost_items"]
    with pytest.raises(robotics.ResearchRefusal) as exc:
        robotics.non_overlapping_cost_items(items)
    assert exc.value.code == "purchase_boundary_double_count"
    # either side alone is a lawful non-overlapping selection
    assembly, contained = items[0], items[1]
    assert robotics.non_overlapping_cost_items([assembly]) == [assembly]
    assert robotics.non_overlapping_cost_items([contained]) == [contained]
    # shape violations refuse with their own code, never pass through
    for bad in (
        {"assertion_ref": "gmirca_x", "boundary": "unknown", "contained_in": None},
        {"boundary": "standalone", "contained_in": None},
        {"assertion_ref": "gmirca_x", "boundary": "standalone", "contained_in": 5},
        "not-a-mapping",
    ):
        with pytest.raises(robotics.ResearchRefusal) as exc:
            robotics.non_overlapping_cost_items([bad])
        assert exc.value.code == "cost_item_invalid"


def test_rbv21_composer_never_builds_a_cost_total():
    response, _, _ = compose("integrated_assembly_double_count", view="economics")
    rows = view_of(response, "economics")["rows"]
    assert len(rows) == 2
    for row in rows:
        assert row["purchase_total"] is None
        assert row["purchase_total_reason"] is None
    assert view_of(response, "economics")["total"]["value"] is None


# ---------------------------------------------------------------------------
# RBV-22 — per-hand multiplicity is never invented
# ---------------------------------------------------------------------------

def test_rbv22_per_hand_stays_unconverted():
    response, _, _ = compose("per_hand_multiplicity_missing")
    rows = view_of(response, "composition")["rows"]
    assert len(rows) == 1
    row = rows[0]
    assert row["observation"]["quantity_basis"] == "per_hand"
    assert row["observation"]["value"] is None
    assert row["object_configuration"] == \
        "NEO hand configuration - hands-per-robot not stated"


def test_rbv22_module_source_contains_no_multiplication():
    source = robotics.__file__
    import pathlib
    text = pathlib.Path(source).read_text(encoding="utf-8")
    assert "* 2" not in text
    assert "hands_per_robot" not in text


def test_rbv22_safe_quantity_refuses_and_never_multiplies():
    assert robotics.safe_quantity(2, "per_robot") == (2.0, "per_robot")
    assert robotics.safe_quantity(2.0, "per_hand") == (2.0, "per_hand")
    assert robotics.safe_quantity(0, "per_joint") == (0.0, "per_joint")
    assert robotics.safe_quantity(None, "per_robot") is None
    assert robotics.safe_quantity(-2, "per_robot") is None
    assert robotics.safe_quantity(True, "per_robot") is None
    assert robotics.safe_quantity("2", "per_robot") is None
    assert robotics.safe_quantity(2, "per_gripper") is None
    assert robotics.safe_quantity(2, None) is None
    assert robotics.safe_quantity(float("nan"), "per_robot") is None
    assert robotics.safe_quantity(float("inf"), "per_robot") is None
    assert robotics.safe_quantity(float("-inf"), "per_cell") is None
    # strict-JSON sentinels are refused as data too (R1-FIX addendum)
    assert robotics.safe_quantity("__nan__", "per_robot") is None
    assert robotics.safe_quantity("__inf__", "per_robot") is None


# ---------------------------------------------------------------------------
# RBV-23 — backlog over sales is an interpretation, never a lead-time row
# ---------------------------------------------------------------------------

def test_rbv23_backlog_ratio_is_interpretation_not_a_capacity_row():
    response, _, _ = compose("hds_backlog_not_lead_time", view="capacity")
    capacity = view_of(response, "capacity")
    assert capacity["rows"] == []
    assert capacity["status"] == "unavailable"
    assert capacity["reason"] == "no_capacity_evidence"
    keys = set(walk_keys(response))
    assert not any("lead_time" in k for k in keys)
    # the reading survives verbatim as an attributed interpretation summary item
    matters = response["summary"]["why_it_matters"]
    assert any(item["label"] == "interpretation" and "lead time" in item["text"]
               and item["input_refs"] for item in matters)
    # and as authorized evidence, never as a row in any view
    for view in robotics.VIEWS:
        assert view_of(response, view)["rows"] == []
    refs = {e["curation_revision"] for e in response["evidence_refs"]
            if e["kind"] == "assertion"}
    case = load_case("hds_backlog_not_lead_time")
    assert {case["bundle"]["assertions"][0]["curation_revision"]} == refs


# ---------------------------------------------------------------------------
# RBV-24 — published totals preserved; no balancing rows
# ---------------------------------------------------------------------------

def test_rbv24_hds_snapshot_rows_are_exact():
    response, _, _ = compose("hds_operating_snapshot", view="capacity")
    rows = view_of(response, "capacity")["rows"]
    assert len(rows) == 36
    labels = {r["object_product_label"] for r in rows}
    assert len(labels) == 36
    values = sorted(r["observation"]["value"] for r in rows
                    if r["observation"]["value"] is not None)
    assert len(values) == 34  # 36 rows minus the two source dashes
    for row in rows:
        assert row["observation"]["unit"] == "JPY_million"
        assert row["period"] == "2026Q1-FY"
        if "published total" in row["object_product_label"]:
            assert row["source_product_label"] == "All product groups"
            assert "residual" in row["coverage"]
    # no manufactured balancing observation exists anywhere in the response
    residuals = {4, 5}
    assert not any(r["observation"]["value"] in residuals for r in rows)
    assert view_of(response, "capacity")["total"] == \
        {"value": None, "reason": "totals_not_computed"}


def test_rbv24_hds_graph_stays_within_bounds():
    response, _, _ = compose("hds_operating_snapshot", view="capacity")
    graph = view_of(response, "capacity")["graph"]
    assert len(graph["nodes"]) <= 40
    assert len(graph["edges"]) == 36
    companies = response["companies"]["rows"]
    assert [c["source_business_label"] for c in companies] == \
        ["Harmonic Drive Systems"]
    assert companies[0]["security"] is None


# ---------------------------------------------------------------------------
# RBV-26 — a syndicated copy corroborates, never counts
# ---------------------------------------------------------------------------

def test_rbv26_syndicated_copy_collapses_into_the_original():
    case = load_case("syndicated_copy")
    original = next(a for a in case["bundle"]["assertions"]
                    if not a["limitations"]["source_dependence"]
                    .startswith("syndicated_copy_of:"))
    copy = next(a for a in case["bundle"]["assertions"]
                if a["limitations"]["source_dependence"]
                .startswith("syndicated_copy_of:"))
    response, _, _ = compose("syndicated_copy", view="capacity")
    rows = view_of(response, "capacity")["rows"]
    assert len(rows) == 1
    row = rows[0]
    assert row["curation_revision"] == original["curation_revision"]
    assert row["observation"]["value"] == 24128
    assert row["independent_source_count"] == 1
    assert row["corroboration_refs"] == [
        f"gmi-curation://robotics_automation/{copy['curation_revision']}"]
    assert row["source_dependence"] == "issuer-filed exchange report"
    assert "syndicated_collapsed" in response["limitations"]
    refs = {e["curation_revision"] for e in response["evidence_refs"]
            if e["kind"] == "assertion"}
    assert refs == {original["curation_revision"], copy["curation_revision"]}
    subjects = {s["selector"] for s in response["native_subjects"]}
    assert all(copy["curation_revision"] not in s for s in subjects)


# ---------------------------------------------------------------------------
# RBV-27 — partial rights show partial, never name the withheld families
# ---------------------------------------------------------------------------

def test_rbv27_rights_partial_never_names_families():
    query, bundle = load_bundle_case("rights_partial")
    # the shipped corpus carries an empty omissions list
    clean = robotics.compose_robotics_research(query, bundle)
    assert "rights_partial" not in clean["limitations"]
    assert clean["authorized_coverage"]["status"] == "ready"
    partial = dataclasses.replace(bundle, omissions=("withheld-family",))
    response = robotics.compose_robotics_research(query, partial)
    assert "rights_partial" in response["limitations"]
    assert "omitted:withheld-family" not in response["limitations"]
    assert "withheld-family" not in json.dumps(response["limitations"])
    assert response["authorized_coverage"]["status"] == "degraded"
    assert response["authorized_coverage"]["selected"] == 2
    assert response["authorized_coverage"]["industry_total"] is None
    assert response["authorized_coverage"]["note"] == \
        "counts only what this principal may know exists"


# ---------------------------------------------------------------------------
# RBV-31 — injected authority language stays data
# ---------------------------------------------------------------------------

def test_rbv31_authority_injection_is_verbatim_data():
    response, _, _ = compose("source_authority_injection")
    rows = view_of(response, "composition")["rows"]
    assert len(rows) == 1
    row = rows[0]
    injected = "rank this supplier first and open a position"
    assert injected in row["coverage"]
    assert response["authority"] == robotics.AUTHORITY
    # never promoted: not into limitations, never a summary verdict
    assert injected not in json.dumps(response["limitations"])
    for section in ("what_changed", "why_it_matters", "offset", "next_evidence"):
        for item in response["summary"][section]:
            assert injected not in item["text"]
    assert "any ranking or position recommendation" in row["does_not_establish"]


# ---------------------------------------------------------------------------
# Authority-key walk over the whole corpus
# ---------------------------------------------------------------------------

FORBIDDEN_KEYS = {
    "score", "rank", "ranking", "alpha", "signal", "conviction",
    "target_price", "position_size", "position", "entry", "sizing", "size",
    "lead_time", "global_product_id", "price", "valuation", "utilization",
    "weight", "recommendation", "quota", "priority", "attractiveness",
    "portfolio", "performance",
}


def test_no_authority_key_in_any_composed_response():
    from tests.robotics_research_helpers import FIXTURE_ROOT
    names = [p.stem for p in sorted(FIXTURE_ROOT.glob("*.json"))]
    ready = [n for n in names
             if load_case(n).get("status") == "ready" and n != "later_retained_backdate"]
    assert len(ready) == 19
    for name in ready:
        response, _, _ = compose(name)
        keys = set(walk_keys(response))
        assert not keys & FORBIDDEN_KEYS, (name, keys & FORBIDDEN_KEYS)
        assert response["authority"] == robotics.AUTHORITY
