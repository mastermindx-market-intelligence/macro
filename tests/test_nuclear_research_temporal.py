"""Reproducible temporal laws for Nuclear research."""

from __future__ import annotations

from engine.market_ontology import nuclear_theme_research as nuclear
from tests.nuclear_research_helpers import (
    N03, N03B, N03C, N03D, nuclear_bundle, nuclear_query,
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


def test_explicit_latest_cutoff_still_decides_target_windows():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("reactor_technology", "commercial", source_cutoff="2026-12-31"),
        nuclear_bundle(N03, N03B))
    assert retrospective_by_revision(payload) == {
        N03["curation_revision"]: False,
        N03B["curation_revision"]: True,
    }
    assert "target_windows_judged_at:2026-09-20" not in payload["limitations"]


def test_same_retention_and_publication_still_judges_only_the_target_window():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("reactor_technology", "commercial"), nuclear_bundle(N03C, N03D))
    assert retrospective_by_revision(payload) == {
        N03C["curation_revision"]: True,
        N03D["curation_revision"]: False,
    }
