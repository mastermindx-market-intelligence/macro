"""L1-L8 laws for Nuclear composition."""

from __future__ import annotations

import dataclasses

from engine.market_ontology import nuclear_theme_research as nuclear
from tests.nuclear_research_helpers import (
    N01, N02, N03, N04, N05, N07, N08, N09, N10, N11, N12,
    X01, X02, X04, nuclear_bundle, nuclear_query,
)


def rows(payload, view):
    return payload["industrial_views"][view]["rows"]


def refs(payload):
    return {row["assertion_ref"] for row in payload["evidence_refs"] if row["kind"] == "assertion"}


def test_supplemental_witnesses_never_in_primary_slices():
    bundle = nuclear_bundle(N01, N02, N03, N07, N08, N09, N10, N11, N12)
    for view in nuclear.VIEWS:
        payload = nuclear.compose_nuclear_research(nuclear_query("reactor_technology", view), bundle)
        assert all(row["source_business_label"] not in {"Cameco", "Centrus"} for row in rows(payload, view))
        serialized = str(payload)
        assert "nuclear_power membership" not in serialized


def test_fuel_cycle_carries_supplemental_limitation():
    payload = nuclear.compose_nuclear_research(nuclear_query("fuel_cycle"), nuclear_bundle(N09))
    assert "supplemental_basket_witnesses" in payload["limitations"]
    assert "slice_scope_unowned" in payload["limitations"]


def test_misfaceted_supplemental_assertion_is_dropped_and_counted():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("reactor_technology", "capacity"), nuclear_bundle(X04))
    assert rows(payload, "capacity") == []
    assert "witness_cohort_excluded:1" in payload["limitations"]


def test_milestones_are_echoed_limitations_never_rows():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("reactor_technology", "commercial"), nuclear_bundle(N03))
    row = rows(payload, "commercial")[0]
    assert row["establishes"] == ["a separate test reactor reached first criticality (technical milestone)"]
    assert row["predicate"] == "DEPLOYMENT_TARGET"
    assert row["statement_mode"] == "FORWARD_TARGET"
    assert "current operation" in row["does_not_establish"]


def test_every_response_carries_milestone_predicate_unavailable():
    for slice_key in nuclear.SLICES:
        for view in nuclear.VIEWS:
            payload = nuclear.compose_nuclear_research(
                nuclear_query(slice_key, view), nuclear_bundle())
            assert "milestone_predicate_unavailable" in payload["limitations"]


def test_contingent_backlog_rows_never_summed_or_funded():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("fuel_cycle", "economics"), nuclear_bundle(N10, N11))
    values = [row["observation"]["value"] for row in rows(payload, "economics")]
    assert values == [1, 3]
    assert payload["industrial_views"]["economics"]["total"] == {"value": None, "reason": "totals_not_computed"}
    for row in rows(payload, "economics"):
        if row["observation"]["value"] == 1:
            assert "additive with the total" in row["does_not_establish"]
            assert "funded revenue" in row["does_not_establish"]


def test_equity_method_investee_never_consolidated():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("fuel_cycle", "commercial"), nuclear_bundle(N09))
    row = rows(payload, "commercial")[0]
    assert row["predicate"] == "OWNERSHIP_EVENT"
    assert "consolidated revenue" in row["does_not_establish"]
    assert row["observation"]["value"] is None


def test_attributed_interpretation_is_never_a_view_row():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("nuclear_components", "commercial"), nuclear_bundle(X01))
    assert rows(payload, "commercial") == []
    assert any("synthetic interpretation was attributed" in item["text"]
               for item in payload["summary"]["why_it_matters"])


def test_unmapped_rights_source_is_excluded_from_rows_and_evidence():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("nuclear_components", "economics"), nuclear_bundle(X02))
    assert rows(payload, "economics") == []
    assert "unmapped_rights_source_excluded:1" in payload["limitations"]


def test_manufacturing_view_is_structurally_empty_with_reason():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("nuclear_components", "manufacturing"), nuclear_bundle(N04))
    view = payload["industrial_views"]["manufacturing"]
    assert view["rows"] == [] and view["reason"] == "no_manufacturing_evidence"


def test_rows_order_is_deterministic_never_by_magnitude():
    query = nuclear_query("nuclear_components", "economics")
    a = nuclear.compose_nuclear_research(query, nuclear_bundle(N04, N05))
    b = nuclear.compose_nuclear_research(query, nuclear_bundle(N05, N04))
    assert a["industrial_views"]["economics"] == b["industrial_views"]["economics"]
    keys = [(row["selector"], row["object_selector"], row["curation_revision"])
            for row in rows(a, "economics")]
    assert keys == sorted(keys)


def test_nulls_stay_null_never_zero():
    bundle = nuclear_bundle()
    payload = nuclear.compose_nuclear_research(nuclear_query("fuel_cycle", "economics"), bundle)
    assert payload["economics"]["management"] is None
    assert payload["expectations"]["management"]["roles"] is None
    assert payload["authorized_coverage"]["industry_total"] is None


def test_generation_is_a_content_fingerprint():
    query = nuclear_query("nuclear_components", "economics")
    bundle = nuclear_bundle(N04)
    first = nuclear.compose_nuclear_research(query, bundle)
    stable = nuclear.compose_nuclear_research(dataclasses.replace(
        query, offset=1, limit=1,
        expected_generation=first["generation"]), bundle)
    changed = nuclear.compose_nuclear_research(query, nuclear_bundle(N05))
    assert first["generation"] == stable["generation"]
    assert first["generation"] != changed["generation"]
