"""Latest, source-history and system-replay temporal laws."""

from __future__ import annotations

from engine.market_ontology import nuclear_theme_research as nuclear
from engine.theme_graph.curation_assertion import source_ref_for
from tests.nuclear_research_helpers import N03, N03B, N04, X03, nuclear_bundle, nuclear_query


def test_latest_selects_currently_available_evidence():
    payload = nuclear.compose_nuclear_research(nuclear_query("nuclear_components", "economics"), nuclear_bundle(N04))
    assert len(payload["industrial_views"]["economics"]["rows"]) == 1


def test_source_history_preserves_rows_and_passed_target_is_retrospective():
    query = nuclear_query(
        "reactor_technology", "commercial", time_mode="source_history",
        source_cutoff="2026-12-31")
    payload = nuclear.compose_nuclear_research(query, nuclear_bundle(N03, N03B))
    targets = {row["observation"]["value"]: row["retrospective"] for row in payload["industrial_views"]["commercial"]["rows"]}
    assert targets == {6: True}


def test_passed_forward_target_stays_a_retrospective_target():
    query = nuclear_query("reactor_technology", "commercial", source_cutoff="2026-12-31")
    payload = nuclear.compose_nuclear_research(query, nuclear_bundle(N03B))
    row = payload["industrial_views"]["commercial"]["rows"][0]
    assert row["predicate"] == "DEPLOYMENT_TARGET"
    assert row["statement_mode"] == "FORWARD_TARGET"
    assert row["retrospective"] is True


def test_correction_pair_supersedes_without_deleting():
    bundle = nuclear_bundle(N04, X03)
    payload = nuclear.compose_nuclear_research(nuclear_query("nuclear_components", "economics"), bundle)
    rows = payload["industrial_views"]["economics"]["rows"]
    assert [row["observation"]["value"] for row in rows] == [100, 101]
    assert [row["review"]["current"] for row in rows] == [False, True]
    evidence = nuclear.select_authorized_evidence(
        nuclear_query("nuclear_components", "economics"), bundle, source_ref_for(X03))
    assert evidence["lineage"] == [source_ref_for(N04)]


def test_system_replay_uses_recorded_cutoff():
    query = nuclear_query(
        "nuclear_components", "economics", time_mode="system_replay",
        source_cutoff="2026-01-01", recorded_cutoff="2026-12-31")
    payload = nuclear.compose_nuclear_research(query, nuclear_bundle(N04))
    assert payload["request"]["recorded_cutoff"] == "2026-12-31"
