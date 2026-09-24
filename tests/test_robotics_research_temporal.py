"""tests/test_robotics_research_temporal.py — time-mode tests for the
Robotics research composer (R2).

Operation gmi-robotics-fable-ceo-e2e-20260923-chairman-001 (carrier #7908).
The three time modes (latest / source_history / system_replay) follow the
shared owner's semantics: a Robotics assertion has no ``available_at``, so
the composer feeds the shared filter an adapted source whose availability is
the observation clock; the retention gate, the same-day grain ambiguity, the
review-expiry now-of-query and the replay identity-mapping gate are the
behaviors under test here (RBV-18/19/20 territory).
"""

from __future__ import annotations

import copy
import dataclasses
import json

import pytest

try:  # the composer needs the shared assertion contract (#7870, RR9: main alone must
    # still collect); when that module is absent every test here is a strict xfail.
    import engine.market_ontology.robotics_theme_research as robotics
    HAS_SHARED = True
except ImportError:  # pragma: no cover - carrier base without the shared foundation
    robotics = None  # type: ignore[assignment]
    HAS_SHARED = False

pytestmark = pytest.mark.xfail(
    condition=not HAS_SHARED,
    strict=True,
    reason="engine.theme_graph.curation_assertion (#7870 shared foundation) is not on "
           "this base; flips loudly the day it lands",
)
from tests.robotics_research_helpers import load_case, load_bundle_case

try:
    from engine.theme_graph.curation_assertion import encode_assertion
    HAS_CODEC = True
except Exception:  # pragma: no cover
    HAS_CODEC = False

CODEC_REASON = "assertion codec not on this base"


def compose(name: str, **query_overrides):
    query, bundle = load_bundle_case(name)
    if query_overrides:
        query = dataclasses.replace(query, **query_overrides)
    return robotics.compose_robotics_research(query, bundle), query, bundle


def restamp(payload: dict, **changes) -> dict:
    mutant = copy.deepcopy(dict(payload))
    mutant.update(changes)
    mutant["curation_revision"] = None
    return json.loads(encode_assertion(mutant))


# ---------------------------------------------------------------------------
# RBV-19 — later-retained evidence cannot support a claim before retention
# ---------------------------------------------------------------------------

def test_later_retained_query_as_stored_refuses():
    query, bundle = load_bundle_case("later_retained_backdate")
    assert query.time_mode == "system_replay"
    assert query.source_cutoff is None
    with pytest.raises(robotics.ResearchRefusal) as exc:
        robotics.compose_robotics_research(query, bundle)
    assert exc.value.code == "replay_cutoffs_required"


def test_replay_before_retention_excludes_the_backlog():
    response, _, _ = compose(
        "later_retained_backdate", view="capacity",
        source_cutoff="2026-09-24T00:00:00Z",
        recorded_cutoff="2026-09-24T00:00:00Z")
    assert response["authorized_coverage"]["selected"] == 0
    capacity = response["industrial_views"]["capacity"]
    assert capacity["rows"] == []
    assert capacity["status"] == "unavailable"
    assert capacity["reason"] == "no_selected_assertions"
    assert response["evidence_refs"] == []


def test_replay_after_retention_includes_the_backlog():
    response, _, _ = compose(
        "later_retained_backdate", view="capacity",
        source_cutoff="2026-09-24T00:00:00Z",
        recorded_cutoff="2026-09-26T00:00:00Z")
    assert response["authorized_coverage"]["selected"] == 1
    rows = response["industrial_views"]["capacity"]["rows"]
    assert len(rows) == 1
    assert rows[0]["observation"]["value"] == 29457
    assert rows[0]["observation"]["stock_flow"] == "stock"
    assert rows[0]["retrospective"] is False


def test_replay_before_observation_excludes_even_with_late_cutoff():
    # the observation clock gates availability: a replay whose source cutoff
    # predates the observation cannot see the row regardless of retention
    response, _, _ = compose(
        "later_retained_backdate", view="capacity",
        source_cutoff="2026-09-23T08:00:00Z",
        recorded_cutoff="2026-09-26T00:00:00Z")
    assert response["authorized_coverage"]["selected"] == 0


# ---------------------------------------------------------------------------
# RBV-18 — withdrawal / overdue review: current applicability vs retention
# ---------------------------------------------------------------------------

def test_latest_mode_keeps_the_accepted_row_current():
    response, _, _ = compose("review_expired_or_withdrawn")
    rows = response["industrial_views"]["composition"]["rows"]
    assert len(rows) == 1
    assert rows[0]["review"]["current"] is True
    assert "held_present" in response["limitations"]
    assert "review_expired_present" not in response["limitations"]


def test_replay_after_review_due_expires_both_rows():
    response, _, _ = compose(
        "review_expired_or_withdrawn",
        source_cutoff="2026-09-24T00:00:00Z",
        recorded_cutoff="2026-09-24T00:00:00Z")
    assert response["industrial_views"]["composition"]["rows"] == []
    assert "held_present" in response["limitations"]
    assert "review_expired_present" in response["limitations"]
    # historical retention: both assertions remain authorized evidence
    refs = {e["curation_revision"] for e in response["evidence_refs"]
            if e["kind"] == "assertion"}
    assert len(refs) == 2
    assert response["companies"]["status"] == "unavailable"
    assert response["companies"]["reason"] == "no_companies"


# ---------------------------------------------------------------------------
# RBV-17 — correction lineage under source_history
# ---------------------------------------------------------------------------

def test_source_history_between_the_two_observations_unsupersedes():
    early, _, _ = compose("corrected_same_url",
                          time_mode="source_history",
                          source_cutoff="2026-09-23T08:15:00Z")
    rows = early["industrial_views"]["composition"]["rows"]
    assert len(rows) == 1
    case = load_case("corrected_same_url")
    predecessor = next(a for a in case["bundle"]["assertions"]
                       if not a["correction"]["predecessor_revision"])
    assert rows[0]["curation_revision"] == predecessor["curation_revision"]
    assert rows[0]["review"]["current"] is True
    assert "superseded_present" not in early["limitations"]


def test_source_history_after_both_observations_resupersedes():
    late, _, _ = compose("corrected_same_url",
                         time_mode="source_history",
                         source_cutoff="2026-09-23T08:30:00Z")
    rows = late["industrial_views"]["composition"]["rows"]
    assert len(rows) == 2
    predecessor = next(r for r in rows
                       if not r["correction"]["predecessor_revision"])
    assert predecessor["review"]["current"] is False
    assert "superseded_present" in late["limitations"]


# ---------------------------------------------------------------------------
# RBV-20 — a date-only publication is not intraday replay proof
# ---------------------------------------------------------------------------

@pytest.mark.xfail(condition=not HAS_CODEC, strict=True, reason=CODEC_REASON)
def test_same_day_publication_is_grain_ambiguous_under_instant_cutoff():
    query, bundle = load_bundle_case("hds_operating_snapshot")
    case = load_case("hds_operating_snapshot")
    row = restamp(
        case["bundle"]["assertions"][0],
        source={**case["bundle"]["assertions"][0]["source"],
                "published_at": "2026-09-23", "published_at_grain": "date",
                "observed_at": "2026-09-23T06:00:00Z",
                "retained_at": "2026-09-23T06:05:00Z"})
    rebuilt = dataclasses.replace(
        bundle, assertions=(row,),
        revision_tuple=(("assertion", row["curation_revision"]),))
    instant = robotics.compose_robotics_research(
        dataclasses.replace(query, view="capacity", time_mode="system_replay",
                            source_cutoff="2026-09-23T12:00:00Z",
                            recorded_cutoff="2026-09-26T00:00:00Z"), rebuilt)
    assert instant["authorized_coverage"]["selected"] == 0
    assert "same_day_grain_ambiguous" in instant["limitations"]

    day = robotics.compose_robotics_research(
        dataclasses.replace(query, view="capacity", time_mode="system_replay",
                            source_cutoff="2026-09-23",
                            recorded_cutoff="2026-09-26T00:00:00Z"), rebuilt)
    assert day["authorized_coverage"]["selected"] == 1
    assert day["industrial_views"]["capacity"]["rows"][0][
        "curation_revision"] == row["curation_revision"]


# ---------------------------------------------------------------------------
# Retrospective labelling is source_history-only
# ---------------------------------------------------------------------------

def test_hds_rows_are_retrospective_only_in_source_history():
    history, _, _ = compose("hds_operating_snapshot", view="capacity",
                            time_mode="source_history",
                            source_cutoff="2026-09-23T23:59:59Z")
    rows = history["industrial_views"]["capacity"]["rows"]
    assert len(rows) == 36
    assert all(r["retrospective"] is True for r in rows)
    latest, _, _ = compose("hds_operating_snapshot", view="capacity")
    assert all(r["retrospective"] is False
               for r in latest["industrial_views"]["capacity"]["rows"])


# ---------------------------------------------------------------------------
# Replay identity: a mapping learned after the cutoff never resolves
# ---------------------------------------------------------------------------

def test_replay_identity_not_yet_learned():
    query, bundle = load_bundle_case("witness_perception_orbbec_twinny")
    case = load_case("witness_perception_orbbec_twinny")
    learned_late = tuple({
        **row, "mapping_learned_at": "2026-09-24T00:00:00Z"}
        for row in case["bundle"]["identity_results"])
    rebuilt = dataclasses.replace(bundle, identity_results=learned_late)
    replay_kwargs = dict(time_mode="system_replay",
                         source_cutoff="2026-09-23T06:30:00Z",
                         recorded_cutoff="2026-09-23T06:30:00Z")
    response = robotics.compose_robotics_research(
        dataclasses.replace(query, **replay_kwargs), rebuilt)
    company = response["companies"]["rows"][0]
    assert company["company_node_id"] is None
    assert company["security"] is None
    assert company["navigation"]["reason"] == "identity_not_yet_learned"
    # the unmodified mapping date resolves inside the same replay
    unchanged = robotics.compose_robotics_research(
        dataclasses.replace(query, **replay_kwargs), bundle)
    same_company = unchanged["companies"]["rows"][0]
    assert same_company["company_node_id"] == "co:cn:688322.SS"
    assert same_company["navigation"]["reason"] == "identity_unresolved"


# ---------------------------------------------------------------------------
# Interpretation blocks: replay filter + staleness law
# ---------------------------------------------------------------------------

def test_replay_excludes_unreviewed_interpretation_blocks():
    query, bundle = load_bundle_case("witness_perception_orbbec_twinny")
    response = robotics.compose_robotics_research(
        dataclasses.replace(query, time_mode="system_replay",
                            source_cutoff="2026-09-23T06:30:00Z",
                            recorded_cutoff="2026-09-23T06:30:00Z"), bundle)
    assert response["summary"]["why_it_matters"] == []
    latest, _, _ = compose("witness_perception_orbbec_twinny")
    matters = latest["summary"]["why_it_matters"]
    case = load_case("witness_perception_orbbec_twinny")
    block = case["bundle"]["interpretation_blocks"][0]
    assert any(item["text"] == block["mechanism"]
               and item["input_refs"] == block["input_revisions"]
               and item["label"] == "interpretation" for item in matters)


def test_stale_interpretation_is_marked_not_hidden():
    query, bundle = load_bundle_case("witness_perception_orbbec_twinny")
    case = load_case("witness_perception_orbbec_twinny")
    block = {**case["bundle"]["interpretation_blocks"][0],
             "input_revisions": ["gmirca_" + "0" * 32]}
    rebuilt = dataclasses.replace(bundle,
                                  interpretation_blocks=(block,))
    response = robotics.compose_robotics_research(query, rebuilt)
    (item,) = [i for i in response["summary"]["why_it_matters"]
               if i["text"].endswith(case["bundle"]["interpretation_blocks"][0]
                                     ["mechanism"])]
    assert item["stale"] is True
    assert item["text"].startswith("[stale interpretation] ")
    assert "interpretation_stale" in response["limitations"]
    assert response["summary"]["status"] == "degraded"
    # the observation it leaned on stays visible in the composition view
    assert len(response["industrial_views"]["composition"]["rows"]) == 1
