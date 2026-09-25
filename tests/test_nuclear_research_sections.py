"""Robotics-parity section behaviour for Nuclear research."""

from __future__ import annotations

import dataclasses

from engine.market_ontology import nuclear_theme_research as nuclear
from tests.nuclear_research_helpers import N03, N03B, N04, X08, X09, X10, clone
from tests.nuclear_research_helpers import nuclear_bundle, nuclear_query


def bundle(*assertions, **changes):
    return dataclasses.replace(nuclear_bundle(*assertions), **changes)


def resolved_identity():
    return ({
            "source_business_label": "BWX Technologies", "resolution": "RESOLVED",
            "company_node_id": "co:us:BWXT", "security_id": "synthetic:BWXT",
        "listing_valid_from": "2026-01-01", "listing_valid_to": None,
        "mapping_learned_at": "2026-01-01",
    },)


def interpretation(*, freshness="current", revisions):
    return {
        "interpretation_id": "synthetic-interpretation", "input_revisions": revisions,
        "freshness": freshness, "reviewed_at": "2026-09-20",
        "mechanism": "Synthetic demand mechanism.", "offset": "Synthetic model offset.",
        "falsifier": "Synthetic falsifier.", "missing_measurement": None,
    }


def test_stale_interpretation_marks_items_and_degrades_summary():
    query = nuclear_query("nuclear_components", "economics")
    fixture_bundle = bundle(N04, interpretation_blocks=(
        interpretation(freshness="stale", revisions=[]),))
    payload = nuclear.compose_nuclear_research(query, fixture_bundle)
    assert payload["summary"]["status"] == "degraded"
    assert payload["summary"]["reason"] == "interpretation_stale"
    assert payload["summary"]["why_it_matters"][0]["stale"] is True
    assert payload["summary"]["why_it_matters"][0]["text"].startswith("[stale interpretation] ")
    assert "interpretation_stale" in payload["limitations"]


def test_no_current_assertion_has_a_summary_reason():
    assertion = clone("N04")
    assertion["review"]["disposition"] = "held"
    payload = nuclear.compose_nuclear_research(
        nuclear_query("nuclear_components", "economics"), bundle(assertion))
    assert payload["summary"]["status"] == "unavailable"
    assert payload["summary"]["reason"] == "no_current_assertions"


def test_unresolved_company_identity_degrades_companies():
    fixture_bundle = dataclasses.replace(
        nuclear_bundle(N04), identity_results=({
            "source_business_label": "BWX Technologies", "resolution": "UNRESOLVED",
            "company_node_id": None, "security_id": None,
            "listing_valid_from": None, "listing_valid_to": None,
            "mapping_learned_at": None,
        },))
    payload = nuclear.compose_nuclear_research(
        nuclear_query("nuclear_components", "economics"), fixture_bundle)
    assert payload["companies"]["status"] == "degraded"
    assert payload["companies"]["reason"] == "identity_incomplete"
    assert payload["companies"]["rows"][0]["navigation"]["status"] == "unavailable"


def test_resolved_company_identity_and_ownership_roles_are_reported():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("reactor_technology", "commercial"),
        bundle(X09, X10, identity_results=({
            "source_business_label": "NuScale", "resolution": "RESOLVED",
            "company_node_id": "co:us:SMR", "security_id": "synthetic:SMR",
            "listing_valid_from": "2026-01-01", "listing_valid_to": None,
            "mapping_learned_at": None,
        },)))
    roles = payload["companies"]["rows"][0]["roles"]
    assert "owner_from:2026-02-01" in {role["role"] for role in roles}
    assert "announced_party" in {role["role"] for role in roles}
    assert payload["companies"]["status"] == "ready"


def test_milestones_never_leave_limitations_for_summary_text():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("reactor_technology", "commercial"), nuclear_bundle(N03, N03B))
    milestone_strings = {
        text
        for assertion in (N03, N03B)
        for text in assertion["limitations"]["establishes"]
        + assertion["limitations"]["does_not_establish"]
    }
    summary_text = {
        item["text"]
        for field in ("what_changed", "why_it_matters", "offset", "next_evidence")
        for item in payload["summary"][field]
    }
    assert not summary_text & milestone_strings
    assert N03["curation_revision"] in {
        revision for item in payload["summary"]["next_evidence"]
        for revision in item["input_refs"]}
    assert N03B["curation_revision"] not in {
        revision for item in payload["summary"]["next_evidence"]
        for revision in item["input_refs"]}
    row = next(row for row in payload["industrial_views"]["commercial"]["rows"]
               if row["curation_revision"] == N03["curation_revision"])
    assert row["establishes"] == N03["limitations"]["establishes"]
    assert row["does_not_establish"] == N03["limitations"]["does_not_establish"]


def test_businessless_product_selector_and_application_subjects():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("reactor_technology", "composition"), bundle(X08, application_assertion()))
    assert "prd:None" not in str(payload)
    subjects = {subject["selector"]: subject for subject in payload["native_subjects"]}
    assert subjects["prd:Synthetic product only"]["source_label"] == "Synthetic product only"
    assert subjects["app:Synthetic enrichment"]["kind"] == "application"
    assert subjects["app:Synthetic enrichment"]["source_label"] == "Synthetic enrichment"


def application_assertion():
    from tests.nuclear_research_helpers import clone
    value = clone("N03D")
    value["scope"]["application"] = "Synthetic enrichment"
    value["curation_revision"] = None
    from engine.theme_graph.curation_assertion import encode_assertion
    import json
    return json.loads(encode_assertion(value))
