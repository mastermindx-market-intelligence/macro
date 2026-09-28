"""Interpretation blocks resolve only against what the same query may know (R-ENE-31).

A block's inputs are looked up among the records that pass this query's scope,
rights, cohort and time gates, before review. An input the query may not know
about makes the block absent here, never stale, so nothing outside the query
decides what it shows. A review-withheld input is still known: a block citing
one is shown, marked stale. A replay never reads a block reviewed after its
cutoff, not even to count it.
"""

from __future__ import annotations

import dataclasses

import pytest

from engine.market_ontology import nuclear_theme_research as nuclear
from tests.nuclear_research_helpers import N04, nuclear_bundle, nuclear_query, variant

QUERY = nuclear_query("nuclear_components", "economics")
REPLAY = nuclear_query(
    "nuclear_components", "economics", time_mode="system_replay",
    source_cutoff="2026-12-31T00:00:00Z", recorded_cutoff="2026-12-31")
LATER = "2027-06-01T00:00:00Z"
ABSENT = "interpretation_inputs_absent:1"

UNKNOWABLE_INPUT = {
    "other_slice": ({"scope": {"technology_facet": "fuel_cycle"},
                     "subject": {"company_node_id": "co:us:CCJ",
                                 "source_business_label": "Cameco"}}, QUERY),
    "rights_refused": ({"source": {
        "source_uri": "https://www.nrc.gov/synthetic/interpretation"}}, QUERY),
    "outside_cohort": ({"subject": {"company_node_id": "co:us:SMR",
                                    "source_business_label": "NuScale Power"}},
                       QUERY),
    "not_yet_recorded": ({"source": {"observed_at": LATER, "retained_at": LATER}},
                         REPLAY),
}


def interpretation(revisions, reviewed_at="2026-09-20"):
    return {
        "interpretation_id": "synthetic-interpretation", "input_revisions": revisions,
        "freshness": "current", "reviewed_at": reviewed_at,
        "mechanism": "Synthetic demand mechanism.", "offset": "Synthetic model offset.",
        "falsifier": "Synthetic falsifier.", "missing_measurement": None,
    }


def compose(query, *assertions, blocks=()):
    bundle = dataclasses.replace(
        nuclear_bundle(*assertions), interpretation_blocks=tuple(blocks))
    return nuclear.compose_nuclear_research(query, bundle)


def shown(payload, revision):
    return [item["text"] for item in payload["summary"]["why_it_matters"]
            if item["input_refs"] == [revision]]


def counted_absent(payload):
    return [code for code in payload["limitations"]
            if code.startswith("interpretation_inputs_absent:")]


@pytest.mark.parametrize("case", sorted(UNKNOWABLE_INPUT))
def test_a_block_citing_an_input_this_query_may_not_know_is_absent_not_stale(case):
    changes, query = UNKNOWABLE_INPUT[case]
    unknowable = variant("N05", f"K1{case}", **changes)
    revision = unknowable["curation_revision"]
    payload = compose(query, N04, unknowable, blocks=[interpretation([revision])])
    assert shown(payload, revision) == []
    assert counted_absent(payload) == [ABSENT]
    assert "interpretation_stale" not in payload["limitations"]


def test_a_replay_answers_the_same_with_or_without_a_later_record():
    later = variant("N05", "K2", source={"observed_at": LATER, "retained_at": LATER})
    block = interpretation([later["curation_revision"]])
    with_later = compose(REPLAY, N04, later, blocks=[block])
    without = compose(REPLAY, N04, blocks=[block])
    assert with_later["summary"] == without["summary"]
    assert sorted(with_later["limitations"]) == sorted(without["limitations"])


def test_a_replay_never_counts_a_block_reviewed_after_its_cutoff():
    block = interpretation(["gmirca_" + "c" * 32], reviewed_at="2027-01-15")
    assert counted_absent(compose(REPLAY, N04, blocks=[block])) == []


def test_a_replay_never_shows_a_block_reviewed_after_its_cutoff():
    block = interpretation([N04["curation_revision"]], reviewed_at="2027-01-15")
    assert shown(compose(REPLAY, N04, blocks=[block]), N04["curation_revision"]) == []
    block = interpretation([N04["curation_revision"]])
    assert shown(compose(REPLAY, N04, blocks=[block]), N04["curation_revision"]) != []


def test_a_block_citing_a_review_withheld_input_is_still_shown_stale():
    held = variant("N05", "K5", review={
        "disposition": "held", "reviewer": "synthetic-energy-test",
        "reviewed_at": "2026-09-20T00:00:00Z", "review_due_at": None})
    revision = held["curation_revision"]
    payload = compose(QUERY, N04, held, blocks=[interpretation([revision])])
    assert shown(payload, revision) == [
        "[stale interpretation] Synthetic demand mechanism."]
    assert "interpretation_stale" in payload["limitations"]
    assert counted_absent(payload) == []
