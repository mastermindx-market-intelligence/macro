"""L1-L8 laws for Nuclear composition."""

from __future__ import annotations

import dataclasses

import pytest

from engine.market_ontology import nuclear_theme_research as nuclear
from engine.theme_graph.curation_assertion import source_ref_for
from tests.nuclear_research_helpers import (
    N01, N02, N03, N04, N05, N07, N08, N09, N10, N11, N12, N13, N14,
    X01, X02, X02B, X04, X04B, X04C, X05, X06, X07,
    nuclear_bundle, nuclear_query, variant,
)

def rows(payload, view):
    return payload["industrial_views"][view]["rows"]

def refs(payload):
    return {row["assertion_ref"] for row in payload["evidence_refs"] if row["kind"] == "assertion"}

def all_input_refs(payload):
    return {
        revision
        for section in payload["industrial_views"].values()
        for revision in section["input_refs"]
    } | set(payload["authorized_coverage"]["input_refs"])

def test_supplemental_witnesses_never_in_primary_slices():
    bundle = nuclear_bundle(N01, N02, N03, N07, N08, N09, N10, N11, N12)
    for view in nuclear.VIEWS:
        payload = nuclear.compose_nuclear_research(nuclear_query("reactor_technology", view), bundle)
        assert all(row["source_business_label"] not in {"Cameco", "Centrus"} for row in rows(payload, view))

def test_fuel_cycle_carries_supplemental_limitation():
    payload = nuclear.compose_nuclear_research(nuclear_query("fuel_cycle"), nuclear_bundle(N09))
    assert "supplemental_basket_witnesses" in payload["limitations"]
    assert "slice_scope_unowned" in payload["limitations"]

def test_out_of_cohort_assertions_are_dropped_counted_and_absent_everywhere():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("nuclear_components", "economics"),
        nuclear_bundle(variant("N04", "N04X", subject={
            "company_node_id": "co:us:SMR"}), variant("N05", "N05X", subject={
            "company_node_id": "co:us:SMR"})))
    assert rows(payload, "economics") == []
    assert all(subject["kind"] != "business" for subject in payload["native_subjects"])
    assert payload["companies"]["input_refs"] == []
    assert payload["evidence_refs"] == []
    assert "witness_cohort_excluded:2" in payload["limitations"]
    with pytest.raises(nuclear.ResearchRefusal):
        nuclear.select_authorized_evidence(
            nuclear_query("nuclear_components", "capacity"),
            nuclear_bundle(X04C, X04), source_ref_for(X04C))

def test_fuel_cycle_supplemental_witnesses_appear_only_in_that_slice():
    bundle = nuclear_bundle(N07, X04B)
    primary = nuclear.compose_nuclear_research(
        nuclear_query("reactor_technology", "capacity"), bundle)
    supplemental = nuclear.compose_nuclear_research(
        nuclear_query("fuel_cycle", "capacity"), bundle)
    assert primary["evidence_refs"] == []
    assert len(supplemental["evidence_refs"]) == 1
    assert [row["source_business_label"] for row in rows(supplemental, "capacity")] == [
        "Cameco"]
    assert "supplemental_basket_witnesses" in supplemental["limitations"]

def test_facet_matches_but_witness_cohort_is_excluded():
    query = nuclear_query("nuclear_components", "capacity")
    payload = nuclear.compose_nuclear_research(query, nuclear_bundle(X04C))
    assert payload["evidence_refs"] == []
    assert "witness_cohort_excluded:1" in payload["limitations"]
    with pytest.raises(nuclear.ResearchRefusal) as refusal:
        nuclear.select_authorized_evidence(
            query, nuclear_bundle(X04C), source_ref_for(X04C))
    assert refusal.value.args[0] == "not_available"

def test_review_gate_refuses_held_rejected_and_expired_evidence():
    query = nuclear_query("nuclear_components", "economics")
    dispositions = (
        variant("N04", "HELD", review={
            "disposition": "held", "reviewer": "synthetic-energy-test",
            "reviewed_at": "2026-09-20T00:00:00Z", "review_due_at": None}),
        variant("N04", "REJECTED", review={
            "disposition": "rejected", "reviewer": "synthetic-energy-test",
            "reviewed_at": "2026-09-20T00:00:00Z", "review_due_at": None}),
        variant("N04", "EXPIRED", review={
            "disposition": "accepted", "reviewer": "synthetic-energy-test",
            "reviewed_at": "2026-09-20T00:00:00Z",
            "review_due_at": "2026-09-19T00:00:00Z"}),
    )
    for assertion in dispositions:
        with pytest.raises(nuclear.ResearchRefusal) as refusal:
            nuclear.select_authorized_evidence(
                query, nuclear_bundle(assertion), source_ref_for(assertion))
        assert refusal.value.args[0] == "not_available"

def test_advertised_and_corroborating_evidence_round_trips():
    corrected = variant(
        "N04", "X04D", correction={
            "predecessor_revision": N04["curation_revision"],
            "reason": "synthetic correction"})
    syndicated = variant(
        "N04", "X04SYN", source={"publisher": "Synthetic Wire"},
        limitations={"source_dependence": "syndicated_copy_of:Synthetic Energy Filings"})
    query = nuclear_query("nuclear_components", "economics")
    bundle = nuclear_bundle(N04, corrected, syndicated)
    payload = nuclear.compose_nuclear_research(query, bundle)
    refs = {ref["assertion_ref"] for ref in payload["evidence_refs"] if ref["kind"] == "assertion"}
    refs.update(ref for row in rows(payload, "economics") for ref in row["corroboration_refs"])
    assert refs
    for assertion_ref in refs:
        evidence = nuclear.select_authorized_evidence(query, bundle, assertion_ref)
        assert evidence["assertion_ref"] == assertion_ref

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
        nuclear_query("fuel_cycle", "economics"), nuclear_bundle(N13, N14))
    economics = payload["industrial_views"]["economics"]
    assert [row["observation"]["value"] for row in economics["rows"]] == [100, 50]
    assert economics["total"] == {"value": None, "reason": "totals_not_computed"}
    assert 150 not in numeric_values(payload)
    assert 50 not in numeric_values(economics["rows"][0])
    row_by_value = {row["observation"]["value"]: row for row in economics["rows"]}
    assert row_by_value[100]["establishes"] == N13["limitations"]["establishes"]
    assert row_by_value[100]["does_not_establish"] == N13["limitations"]["does_not_establish"]
    assert row_by_value[50]["establishes"] == N14["limitations"]["establishes"]
    assert row_by_value[50]["does_not_establish"] == N14["limitations"]["does_not_establish"]

def numeric_values(value):
    if isinstance(value, dict):
        return [item for child in value.values() for item in numeric_values(child)]
    if isinstance(value, list):
        return [item for child in value for item in numeric_values(child)]
    return [value] if isinstance(value, (int, float)) and not isinstance(value, bool) else []

def test_attributed_interpretation_is_never_a_view_row():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("nuclear_components", "commercial"), nuclear_bundle(X01))
    assert rows(payload, "commercial") == []
    assert any("Synthetic coverage statement for X01." in item["text"]
               for item in payload["summary"]["why_it_matters"])

def test_composer_defence_in_depth_excludes_unmapped_rights_source():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("nuclear_components", "economics"), nuclear_bundle(X02, X02B))
    assert rows(payload, "economics") == []
    assert payload["evidence_refs"] == []
    assert "unmapped_rights_source_excluded:2" in payload["limitations"]
    with pytest.raises(nuclear.ResearchRefusal):
        nuclear.select_authorized_evidence(
            nuclear_query("nuclear_components", "economics"),
            nuclear_bundle(X02, X02B), source_ref_for(X02))

def test_syndicated_copy_collapses_into_its_single_original():
    bundle = nuclear_bundle(N04, X05)
    payload = nuclear.compose_nuclear_research(
        nuclear_query("nuclear_components", "economics"), bundle)
    economics = payload["industrial_views"]["economics"]
    assert [row["curation_revision"] for row in economics["rows"]] == [N04["curation_revision"]]
    assert economics["rows"][0]["corroboration_refs"] == [source_ref_for(X05)]
    assert economics["rows"][0]["independent_source_count"] == 1
    assert "syndicated_collapsed" in payload["limitations"]
    assert X05["curation_revision"] not in all_input_refs(payload)
    assert X05["curation_revision"] not in {
        row["curation_revision"] for row in economics["rows"]}

def test_ambiguous_syndication_never_guesses_an_original():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("nuclear_components", "economics"),
        nuclear_bundle(N04, X05, N05))
    assert len(rows(payload, "economics")) == 3
    assert "syndicated_collapsed" not in payload["limitations"]

def test_syndication_with_absent_publisher_stays_its_own_row():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("nuclear_components", "economics"), nuclear_bundle(X05))
    assert len(rows(payload, "economics")) == 1
    assert "syndicated_collapsed" not in payload["limitations"]

def test_manufacturing_view_is_structurally_empty_with_reason():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("nuclear_components", "manufacturing"), nuclear_bundle(N04))
    view = payload["industrial_views"]["manufacturing"]
    assert view["rows"] == [] and view["reason"] == "no_manufacturing_evidence"

def test_rows_order_is_deterministic_never_by_magnitude():
    query = nuclear_query("reactor_technology", "composition")
    fixtures = (X06, X07)
    a = nuclear.compose_nuclear_research(query, nuclear_bundle(*fixtures))
    b = nuclear.compose_nuclear_research(query, nuclear_bundle(*reversed(fixtures)))
    view = "composition"
    assert a["industrial_views"][view] == b["industrial_views"][view]
    assert [row["observation"]["value"] for row in rows(a, view)] == [10, 200]
    assert [row["curation_revision"] for row in rows(a, view)] == [
        X06["curation_revision"], X07["curation_revision"]]
    keys = [(row["selector"], row["object_selector"], row["curation_revision"])
            for row in rows(a, view)]
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


def test_misfaceted_supplemental_assertion_is_dropped_and_counted():
    query = nuclear_query("reactor_technology", "capacity")
    bundle = nuclear_bundle(X04)
    payload = nuclear.compose_nuclear_research(query, bundle)
    assert rows(payload, "capacity") == []
    assert payload["evidence_refs"] == []
    assert "witness_cohort_excluded:1" in payload["limitations"]
    with pytest.raises(nuclear.ResearchRefusal) as refusal:
        nuclear.select_authorized_evidence(query, bundle, source_ref_for(X04))
    assert refusal.value.args[0] == "not_available"


LEU_IN_COMPONENTS = variant("X04C", "X04L", subject={"company_node_id": "co:us:LEU"})


@pytest.mark.parametrize(("slice_key", "intruders"), [
    ("reactor_technology", (X04, X04B)),
    ("nuclear_components", (X04C, LEU_IN_COMPONENTS)),
])
def test_fuel_cycle_companies_are_out_of_cohort_in_both_primary_slices(slice_key, intruders):
    query = nuclear_query(slice_key, "capacity")
    bundle = nuclear_bundle(*intruders)
    payload = nuclear.compose_nuclear_research(query, bundle)
    assert rows(payload, "capacity") == []
    assert payload["evidence_refs"] == []
    assert f"witness_cohort_excluded:{len(intruders)}" in payload["limitations"]
    for intruder in intruders:
        with pytest.raises(nuclear.ResearchRefusal) as refusal:
            nuclear.select_authorized_evidence(query, bundle, source_ref_for(intruder))
        assert refusal.value.args[0] == "not_available"


def test_witness_cohort_is_the_packet_cohort():
    assert nuclear.WITNESS_COHORT == {
        "reactor_technology": ("co:us:SMR", "co:us:OKLO"),
        "nuclear_components": ("co:us:BWXT",),
        "fuel_cycle": ("co:us:CCJ", "co:us:LEU"),
    }


def test_collapsed_copy_and_correction_pair_round_trip():
    original = variant("N05", "N05P", source={"publisher": "Synthetic Trade Journal"})
    corrected = variant(
        "N05", "N05R", source={"publisher": "Synthetic Trade Journal"},
        correction={"predecessor_revision": original["curation_revision"],
                    "reason": "synthetic correction"})
    copy = variant(
        "N04", "N04S", source={"publisher": "Synthetic Wire"},
        limitations={"source_dependence": "syndicated_copy_of:Synthetic Energy Filings"})
    query = nuclear_query("nuclear_components", "economics")
    bundle = nuclear_bundle(N04, original, corrected, copy)
    payload = nuclear.compose_nuclear_research(query, bundle)
    assert "syndicated_collapsed" in payload["limitations"]
    assert "superseded_present" in payload["limitations"]
    corroboration = [
        ref for row in rows(payload, "economics") for ref in row["corroboration_refs"]]
    assert corroboration == [source_ref_for(copy)]
    advertised = {
        ref["assertion_ref"] for ref in payload["evidence_refs"] if ref["kind"] == "assertion"}
    assert source_ref_for(corrected) in advertised
    for assertion_ref in advertised | set(corroboration):
        evidence = nuclear.select_authorized_evidence(query, bundle, assertion_ref)
        assert evidence["assertion_ref"] == assertion_ref
