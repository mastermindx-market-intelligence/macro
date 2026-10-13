"""Reproducible temporal laws for Nuclear research."""

from __future__ import annotations

from engine.market_ontology import nuclear_theme_research as nuclear
from engine.theme_graph.curation_assertion import source_ref_for
from tests.nuclear_research_helpers import (
    N01, N03, N03B, N03C, N03D, N04, X03, nuclear_bundle, nuclear_query, variant,
)

def retrospective_by_revision(payload):
    return {
        row["curation_revision"]: row["retrospective"]
        for row in payload["industrial_views"]["commercial"]["rows"]
    }

def test_latest_without_cutoff_uses_the_evidence_frontier_for_targets():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("reactor_technology", "commercial"), nuclear_bundle(N03, N03B))
    assert retrospective_by_revision(payload) == {
        N03["curation_revision"]: False,
        N03B["curation_revision"]: True,
    }
    assert "target_windows_judged_at:2026-09-20" in payload["limitations"]

def test_latest_selects_currently_available_evidence():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("nuclear_components", "economics"), nuclear_bundle(N04))
    assert len(payload["industrial_views"]["economics"]["rows"]) == 1

def test_source_history_preserves_rows_and_passed_target_is_retrospective():
    query = nuclear_query(
        "reactor_technology", "commercial", time_mode="source_history",
        source_cutoff="2026-12-31")
    payload = nuclear.compose_nuclear_research(query, nuclear_bundle(N03, N03B))
    targets = {
        row["curation_revision"]: row["retrospective"]
        for row in payload["industrial_views"]["commercial"]["rows"]
    }
    assert targets == {
        N03["curation_revision"]: True,
        N03B["curation_revision"]: True,
    }

def test_explicit_latest_cutoff_still_decides_target_windows():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("reactor_technology", "commercial", source_cutoff="2026-12-31"),
        nuclear_bundle(N03, N03B))
    assert retrospective_by_revision(payload) == {
        N03["curation_revision"]: False,
        N03B["curation_revision"]: True,
    }
    assert not any(
        limitation.startswith("target_windows_judged_at:")
        for limitation in payload["limitations"])

def test_passed_forward_target_stays_a_retrospective_target():
    query = nuclear_query(
        "reactor_technology", "commercial", source_cutoff="2026-12-31")
    payload = nuclear.compose_nuclear_research(query, nuclear_bundle(N03B))
    row = payload["industrial_views"]["commercial"]["rows"][0]
    assert row["predicate"] == "DEPLOYMENT_TARGET"
    assert row["statement_mode"] == "FORWARD_TARGET"
    assert row["retrospective"] is True

def test_same_retention_and_publication_still_judges_only_the_target_window():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("reactor_technology", "commercial"), nuclear_bundle(N03C, N03D))
    assert retrospective_by_revision(payload) == {
        N03C["curation_revision"]: True,
        N03D["curation_revision"]: False,
    }

def test_source_history_window_only_target_boundary():
    payload = nuclear.compose_nuclear_research(
        nuclear_query(
            "reactor_technology", "commercial", time_mode="source_history",
            source_cutoff="2026-12-31"),
        nuclear_bundle(N03C, N03D))
    assert retrospective_by_revision(payload) == {
        N03C["curation_revision"]: True,
        N03D["curation_revision"]: False,
    }

def test_reference_day_ignores_a_rejected_record():
    late_rejected = variant(
        "N04", "LATEREJ",
        source={"published_at": "2028-06-01", "retained_at": "2028-06-01T00:00:00Z",
                "observed_at": "2028-06-01T00:00:00Z"},
        scope={"technology_facet": "reactor_technology"},
        subject={"company_node_id": "co:us:OKLO", "source_business_label": "Oklo"},
        review={"disposition": "rejected", "reviewer": "synthetic-energy-test",
                "reviewed_at": "2026-09-20T00:00:00Z", "review_due_at": None})
    query = nuclear_query("reactor_technology", "commercial")
    payload = nuclear.compose_nuclear_research(query, nuclear_bundle(N03, late_rejected))
    row = payload["industrial_views"]["commercial"]["rows"][0]
    assert row["retrospective"] is False
    assert row["curation_revision"] in {
        revision for item in payload["summary"]["next_evidence"]
        for revision in item["input_refs"]
    }
    assert "target_windows_judged_at:2026-09-20" in payload["limitations"]

def test_reference_day_ignores_a_collapsed_syndicated_copy():
    late_copy = variant(
        "N03", "LATECOPY",
        source={"publisher": "Synthetic Wire", "published_at": "2028-06-01",
                "retained_at": "2028-06-01T00:00:00Z",
                "observed_at": "2028-06-01T00:00:00Z"},
        limitations={"source_dependence": "syndicated_copy_of:Synthetic Energy Filings"})
    query = nuclear_query("reactor_technology", "commercial")
    payload = nuclear.compose_nuclear_research(query, nuclear_bundle(N03, late_copy))
    row = payload["industrial_views"]["commercial"]["rows"][0]
    assert row["retrospective"] is False
    assert row["corroboration_refs"] == [source_ref_for(late_copy)]
    assert row["curation_revision"] in {
        revision for item in payload["summary"]["next_evidence"]
        for revision in item["input_refs"]
    }
    assert "target_windows_judged_at:2026-09-20" in payload["limitations"]

def test_no_target_disclosure_when_the_only_target_is_rejected():
    rejected = variant(
        "N03", "REJT", review={
            "disposition": "rejected", "reviewer": "synthetic-energy-test",
            "reviewed_at": "2026-09-20T00:00:00Z", "review_due_at": None})
    payload = nuclear.compose_nuclear_research(
        nuclear_query("reactor_technology", "commercial"),
        nuclear_bundle(N01, rejected))
    assert payload["industrial_views"]["commercial"]["rows"] == []
    assert not any(
        limitation.startswith("target_windows_judged_at:")
        for limitation in payload["limitations"])

def test_valid_to_equal_to_reference_day_is_retrospective():
    equal_day = variant("N03", "EQDAY", temporal={"business_valid_to": "2026-09-20"})
    payload = nuclear.compose_nuclear_research(
        nuclear_query("reactor_technology", "commercial"),
        nuclear_bundle(equal_day))
    assert retrospective_by_revision(payload) == {
        equal_day["curation_revision"]: True}

def test_correction_pair_supersedes_without_deleting():
    bundle = nuclear_bundle(N04, X03)
    query = nuclear_query("nuclear_components", "economics")
    payload = nuclear.compose_nuclear_research(query, bundle)
    rows = payload["industrial_views"]["economics"]["rows"]
    assert [row["observation"]["value"] for row in rows] == [100, 101]
    assert [row["review"]["current"] for row in rows] == [False, True]
    assert "superseded_present" in payload["limitations"]
    evidence = nuclear.select_authorized_evidence(query, bundle, source_ref_for(X03))
    assert evidence["lineage"] == [source_ref_for(N04)]

def test_system_replay_uses_recorded_cutoff():
    query = nuclear_query(
        "nuclear_components", "economics", time_mode="system_replay",
        source_cutoff="2026-01-01", recorded_cutoff="2026-12-31")
    payload = nuclear.compose_nuclear_research(query, nuclear_bundle(N04))
    assert payload["request"]["recorded_cutoff"] == "2026-12-31"


def test_archival_record_of_an_open_target_stays_next_evidence():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("reactor_technology", "commercial",
                      time_mode="source_history", source_cutoff="2026-12-31"),
        nuclear_bundle(N03, N03B))
    assert retrospective_by_revision(payload)[N03["curation_revision"]] is True
    assert N03["curation_revision"] in {
        revision for item in payload["summary"]["next_evidence"]
        for revision in item["input_refs"]}
