"""Review-gate closure for Nuclear research (R-ENE-27, #7870 RULING 9).

A held, rejected or review-expired record never counts as coverage, never
changes a view's reason and never supports an interpretation block.
"""

from __future__ import annotations

import dataclasses

import pytest

from engine.market_ontology import nuclear_theme_research as nuclear
from tests.nuclear_research_helpers import N04, X05, nuclear_bundle, nuclear_query, variant


def review(disposition, due=None):
    return {"disposition": disposition, "reviewer": "synthetic-energy-test",
            "reviewed_at": "2026-09-20T00:00:00Z", "review_due_at": due}


WITHHELD = {
    "held": review("held"),
    "rejected": review("rejected"),
    "expired": review("accepted", "2026-09-19T00:00:00Z"),
}


def interpretation(revisions):
    return {
        "interpretation_id": "synthetic-interpretation", "input_revisions": revisions,
        "freshness": "current", "reviewed_at": "2026-09-20",
        "mechanism": "Synthetic demand mechanism.", "offset": "Synthetic model offset.",
        "falsifier": "Synthetic falsifier.", "missing_measurement": None,
    }


def compose(*assertions, blocks=()):
    bundle = dataclasses.replace(
        nuclear_bundle(*assertions), interpretation_blocks=tuple(blocks))
    return nuclear.compose_nuclear_research(
        nuclear_query("nuclear_components", "economics"), bundle)


def cited(items, revision):
    return next(item for item in items if item["input_refs"] == [revision])


@pytest.mark.parametrize("case", sorted(WITHHELD))
def test_withheld_records_are_not_counted_as_coverage(case):
    withheld = variant("N04", f"R9{case.upper()}", review=WITHHELD[case])
    payload = compose(withheld)
    coverage = payload["authorized_coverage"]
    assert coverage["status"] == "unavailable"
    assert coverage["selected"] == 0
    assert coverage["input_refs"] == []
    for view, section in payload["industrial_views"].items():
        assert section["status"] == "unavailable"
        assert section["reason"] == (
            "no_manufacturing_evidence" if view == "manufacturing"
            else "no_selected_assertions")
    assert [ref for ref in payload["evidence_refs"] if ref["kind"] == "assertion"] == []


def test_selected_counts_exactly_the_served_input_refs():
    rejected = variant("N05", "R9N05", review=WITHHELD["rejected"])
    payload = compose(N04, X05, rejected)
    coverage = payload["authorized_coverage"]
    assert coverage["input_refs"] == [N04["curation_revision"]]
    assert coverage["selected"] == len(coverage["input_refs"]) == 1
    assert coverage["status"] == "ready"
    assert {"syndicated_collapsed", "rejected_present"} <= set(payload["limitations"])


@pytest.mark.parametrize("case", sorted(WITHHELD))
def test_interpretation_citing_a_withheld_record_is_stale(case):
    withheld = variant("N05", f"R9{case.upper()}", review=WITHHELD[case])
    revision = withheld["curation_revision"]
    payload = compose(N04, withheld, blocks=[interpretation([revision])])
    summary = payload["summary"]
    for item in (cited(summary["why_it_matters"], revision),
                 cited(summary["offset"], revision)):
        assert item["stale"] is True
        assert item["text"].startswith("[stale interpretation] ")
        assert item["input_refs"] == [revision]
    assert summary["status"] == "degraded"
    assert summary["reason"] == "interpretation_stale"
    assert "interpretation_stale" in payload["limitations"]


@pytest.mark.parametrize("fixtures, revision", [
    ((N04,), N04["curation_revision"]),
    ((N04, X05), X05["curation_revision"]),
], ids=["current_record", "collapsed_copy"])
def test_interpretation_citing_a_served_record_stays_supported(fixtures, revision):
    payload = compose(*fixtures, blocks=[interpretation([revision])])
    summary = payload["summary"]
    for item in (cited(summary["why_it_matters"], revision),
                 cited(summary["offset"], revision)):
        assert "stale" not in item
        assert not item["text"].startswith("[stale interpretation] ")
    assert summary["status"] == "ready"
    assert "interpretation_stale" not in payload["limitations"]
