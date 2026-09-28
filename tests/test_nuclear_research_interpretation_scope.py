"""Interpretation blocks resolve only against what the same query may know (R-ENE-31).

A block's inputs are looked up among the records that pass this query's scope,
rights, cohort and time gates, before review. An input the query may not know
about makes the block absent here, never stale, so nothing outside the query
decides what it shows. A review-withheld input is still known: a block citing
one is shown, marked stale. A replay never reads a block reviewed after its
cutoff, not even to count it, and treats a block without a readable review
time the same way (R-ENE-34). Only a replay reads the review time, and only
against the recorded cutoff; when either side is date-only, a review on the
cutoff day is by the cutoff (R-ENE-33). An instant review time is readable,
and against an instant cutoff it compares as an instant (R-ENE-36). The guard
judges readability from the block's clock alone; wherever it then compares a
readable review time with the recorded cutoff, a malformed cutoff raises
instead of withholding the block (R-ENE-35).
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


EARLY = variant("N05", "SV1", source={
    "published_at": "2026-01-15", "observed_at": "2026-01-15T00:00:00Z",
    "retained_at": "2026-01-15T00:00:00Z"})
SUPPORTED = ["Synthetic demand mechanism."]


def test_a_replay_counts_an_unknown_input_block_reviewed_by_its_cutoff():
    block = interpretation(["gmirca_" + "c" * 32])
    assert counted_absent(compose(REPLAY, N04, blocks=[block])) == [ABSENT]


def test_a_replay_shows_a_block_reviewed_on_its_cutoff_day():
    revision = EARLY["curation_revision"]
    block = interpretation([revision], reviewed_at="2026-12-31")
    assert shown(compose(REPLAY, EARLY, blocks=[block]), revision) == SUPPORTED


def test_a_replay_reads_review_time_against_the_recorded_cutoff():
    split = nuclear_query(
        "nuclear_components", "economics", time_mode="system_replay",
        source_cutoff="2026-06-30T00:00:00Z", recorded_cutoff="2026-12-31")
    revision = EARLY["curation_revision"]
    block = interpretation([revision])
    assert shown(compose(split, EARLY, blocks=[block]), revision) == SUPPORTED


def test_only_a_system_replay_reads_review_time():
    history = nuclear_query(
        "nuclear_components", "economics", time_mode="source_history",
        source_cutoff="2026-12-31T00:00:00Z", recorded_cutoff="2026-12-31")
    revision = EARLY["curation_revision"]
    block = interpretation([revision], reviewed_at="2027-01-15")
    assert shown(compose(history, EARLY, blocks=[block]), revision) == SUPPORTED


@pytest.mark.parametrize(
    "reviewed_at", [None, "", "not-a-date", "2026-13-45", "20260920"])
def test_a_replay_withholds_a_block_without_a_readable_review_time(reviewed_at):
    revision = EARLY["curation_revision"]
    block = interpretation([revision], reviewed_at=reviewed_at)
    assert shown(compose(REPLAY, EARLY, blocks=[block]), revision) == []
    block = interpretation(["gmirca_" + "c" * 32], reviewed_at=reviewed_at)
    assert counted_absent(compose(REPLAY, EARLY, blocks=[block])) == []


@pytest.mark.parametrize("recorded_cutoff", ["not-a-date", "2026-13-45", "20261231"])
def test_the_review_guard_never_swallows_a_malformed_replay_cutoff(recorded_cutoff):
    malformed = dataclasses.replace(REPLAY, recorded_cutoff=recorded_cutoff)
    elsewhere = variant("N05", "K1other_slice", **UNKNOWABLE_INPUT["other_slice"][0])
    block = interpretation([elsewhere["curation_revision"]])
    for assertions in ((elsewhere,), ()):
        assert counted_absent(compose(REPLAY, *assertions, blocks=[block])) == [ABSENT]
        with pytest.raises(ValueError):
            compose(malformed, *assertions, blocks=[block])


def test_a_replay_reads_an_instant_review_time():
    revision = EARLY["curation_revision"]
    block = interpretation([revision], reviewed_at="2026-09-20T00:00:00Z")
    assert shown(compose(REPLAY, EARLY, blocks=[block]), revision) == SUPPORTED


@pytest.mark.parametrize(("reviewed_at", "expected"), [
    ("2026-12-31T11:00:00Z", SUPPORTED), ("2026-12-31T23:00:00Z", []),
    ("2026-12-31T12:00:00Z", SUPPORTED), ("2026-12-31T19:00:00+08:00", SUPPORTED),
    ("2026-12-31T08:00:00-05:00", [])])
def test_a_replay_compares_an_instant_review_time_with_an_instant_cutoff(
        reviewed_at, expected):
    noon = dataclasses.replace(REPLAY, recorded_cutoff="2026-12-31T12:00:00Z")
    revision = EARLY["curation_revision"]
    block = interpretation([revision], reviewed_at=reviewed_at)
    assert shown(compose(noon, EARLY, blocks=[block]), revision) == expected


@pytest.mark.parametrize("reviewed_at", [None, "", "not-a-date"])
@pytest.mark.parametrize("time_mode", ["latest", "source_history"])
def test_outside_a_replay_the_review_time_is_never_read(time_mode, reviewed_at):
    cutoffs = {} if time_mode == "latest" else {
        "source_cutoff": "2026-12-31T00:00:00Z", "recorded_cutoff": "2026-12-31"}
    query = nuclear_query(
        "nuclear_components", "economics", time_mode=time_mode, **cutoffs)
    revision = EARLY["curation_revision"]
    block = interpretation([revision], reviewed_at=reviewed_at)
    assert shown(compose(query, EARLY, blocks=[block]), revision) == SUPPORTED


@pytest.mark.parametrize(("reviewed_at", "expected"), [
    ("2026-12-31", SUPPORTED), ("2027-01-01", [])])
def test_a_replay_reads_a_date_review_time_against_an_instant_cutoff_by_day(
        reviewed_at, expected):
    noon = dataclasses.replace(REPLAY, recorded_cutoff="2026-12-31T12:00:00Z")
    revision = EARLY["curation_revision"]
    block = interpretation([revision], reviewed_at=reviewed_at)
    assert shown(compose(noon, EARLY, blocks=[block]), revision) == expected
