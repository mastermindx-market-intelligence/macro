"""Review-gate closure for Nuclear research (R-ENE-27, #7870 RULING 9).

A held, rejected or review-expired record never counts as coverage, never
changes a view's reason and never supports an interpretation block. A replay
judges review expiry at its recorded cutoff, never at its source cutoff or
the newest review time. Outside a replay the expiry clock is the newest
reviewed_at of the time-filtered selection, so a recorded cutoff does not
move it: an early cutoff still expires a review due 2026-09-19. A malformed
recorded cutoff still fails the query instead of being swallowed (R-ENE-40).
"""

from __future__ import annotations

import dataclasses

import pytest

from engine.market_ontology import nuclear_theme_research as nuclear
from tests.nuclear_research_helpers import N04, X01, X05, nuclear_bundle, nuclear_query, variant


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


EARLY = {"published_at": "2026-01-15", "observed_at": "2026-01-15T00:00:00Z",
         "retained_at": "2026-01-15T00:00:00Z"}


def replay_expired(recorded_cutoff, due):
    dated = variant("N04", "R11DUE", source=EARLY, review={
        **review("accepted", due), "reviewed_at": "2026-05-01T00:00:00Z"})
    later = variant("N04", "R11LATER", source=EARLY, review=review("accepted"))
    query = nuclear_query("nuclear_components", "economics", time_mode="system_replay",
                          source_cutoff="2026-06-30T00:00:00Z", recorded_cutoff=recorded_cutoff)
    payload = nuclear.compose_nuclear_research(query, nuclear_bundle(dated, later))
    return "review_expired_present" in payload["limitations"]


@pytest.mark.parametrize(("recorded_cutoff", "due", "expired"), [
    ("2026-12-31", "2026-12-31T23:00:00Z", True),
    ("2026-12-31", "2027-01-01T00:00:00Z", False),
    ("2026-12-31T12:00:00Z", "2026-12-31T12:00:00Z", True),
    ("2026-12-31T12:00:00Z", "2026-12-31T18:00:00Z", False),
    ("2026-07-31", "2026-08-01T00:00:00Z", False),
])
def test_a_replay_judges_review_expiry_at_the_recorded_cutoff(recorded_cutoff, due, expired):
    assert replay_expired(recorded_cutoff, due) is expired


@pytest.mark.parametrize("recorded_cutoff", ["not-a-date", "2026-13-45", "20261231"])
@pytest.mark.parametrize("time_mode", ["latest", "source_history"])
def test_the_expiry_gate_never_swallows_a_malformed_recorded_cutoff(time_mode, recorded_cutoff):
    bundle = nuclear_bundle(variant("N04", "R11DUE", review=review("accepted", "2027-01-01T00:00:00Z")))
    query = nuclear_query("nuclear_components", "economics", time_mode=time_mode)
    assert nuclear.compose_nuclear_research(query, bundle)["authorized_coverage"]["selected"] == 1
    malformed = dataclasses.replace(query, recorded_cutoff=recorded_cutoff)
    with pytest.raises(ValueError):
        nuclear.compose_nuclear_research(malformed, bundle)


def test_latest_with_an_early_recorded_cutoff_still_expires_the_review():
    """Outside a replay, recorded_cutoff is not the expiry clock.

    reviewed_at is 2026-09-20 and review_due_at is 2026-09-19, so the review
    is already due. An early recorded cutoff must not serve it.
    """
    dated = variant("N04", "R12DUE", review=review("accepted", "2026-09-19T00:00:00Z"))
    query = nuclear_query(
        "nuclear_components", "economics", time_mode="latest",
        recorded_cutoff="2026-09-01")
    payload = nuclear.compose_nuclear_research(query, nuclear_bundle(dated))
    assert "review_expired_present" in payload["limitations"]
    assert payload["authorized_coverage"]["selected"] == 0


def _paired_block(interpretation_id, freshness, mechanism, revision):
    return {
        "interpretation_id": interpretation_id,
        "input_revisions": [revision],
        "freshness": freshness,
        "reviewed_at": "2026-09-20",
        "mechanism": mechanism,
        "offset": mechanism.replace("mechanism.", "offset."),
        "falsifier": None,
        "missing_measurement": None,
    }


def test_stale_prefix_follows_the_producing_interpretation():
    """Two blocks that share input_revisions: only the stale block is prefixed."""
    revision = N04["curation_revision"]
    payload = compose(N04, blocks=[
        _paired_block("block-fresh", "current", "FRESH mechanism.", revision),
        _paired_block("block-stale", "stale", "STALE mechanism.", revision),
    ])
    summary = payload["summary"]
    assert summary["status"] == "degraded"
    assert summary["reason"] == "interpretation_stale"
    why = {item["text"]: item for item in summary["why_it_matters"]}
    assert "stale" not in why["FRESH mechanism."]
    assert "_interpretation_id" not in why["FRESH mechanism."]
    assert why["[stale interpretation] STALE mechanism."]["stale"] is True
    offset = {item["text"]: item for item in summary["offset"]}
    assert "stale" not in offset["FRESH offset."]
    assert offset["[stale interpretation] STALE offset."]["stale"] is True
    assert all("_interpretation_id" not in item for item in summary["why_it_matters"])
    assert all("_interpretation_id" not in item for item in summary["offset"])


def test_swapped_interpretations_keep_their_own_why_it_matters():
    """Two interpretations that share a revision keep their own why text.

    The attributed statement cites that same revision. Swapping block order
    must not paint its text with the other interpretation's stale prefix.
    """
    revision = X01["curation_revision"]
    # "a-stale" sorts before "z-fresh", so a first-match on input_revisions
    # takes the stale block.
    fresh = _paired_block("z-fresh", "current", "FRESH mechanism.", revision)
    stale = _paired_block("a-stale", "stale", "STALE mechanism.", revision)
    coverage = X01["limitations"]["coverage"]

    def why_text(blocks):
        payload = compose(X01, blocks=blocks)
        return sorted(item["text"] for item in payload["summary"]["why_it_matters"])

    forward = why_text([fresh, stale])
    backward = why_text([stale, fresh])
    assert forward == backward
    assert coverage in forward
    assert "[stale interpretation] " + coverage not in forward
    assert "FRESH mechanism." in forward
    assert "[stale interpretation] STALE mechanism." in forward
    assert "[stale interpretation] FRESH mechanism." not in forward
