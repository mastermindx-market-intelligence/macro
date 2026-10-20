from pathlib import Path

import pytest

from engine.prophet_candidate_state_sources import (
    CandidateStateSourceError,
    emergence_inputs,
    index_radar_rows,
    index_turn_watch_events,
    load_radar_fact_index,
)
from engine.us_candidate_episode import (
    CandidateEpisodeStoreSnapshot,
    ValidatedCandidateEpisodeGeneration,
)

GEN = "peg:" + "a" * 64
GEN_OTHER = "peg:" + "b" * 64
RECORDED = "2026-09-18T09:08:31Z"
OLDER_RECORDED = "2026-09-17T09:08:31Z"
TURN_SCHEMA = "prophet.candidate_episode_input.turn_watch/v1"


def generation_receipt(*, recorded_at=RECORDED, mapped=1):
    return {
        "schema": "prophet.candidate_episode_reconcile_receipt/v1",
        "recorded_at": recorded_at,
        "source_counts": {"turn_watch": {"mapped": mapped}},
    }


def snapshot(
    episodes,
    *,
    events=(),
    generation_id=GEN,
    recorded_at=RECORDED,
    mapped=None,
):
    events = tuple(events)
    if mapped is None:
        mapped = sum(
            1
            for event in events
            if event.get("event_type") in {"OPENED", "OBSERVED"}
            and event.get("source_system") == "turn_watch"
            and event.get("source_schema") == TURN_SCHEMA
            and event.get("recorded_at") == recorded_at
        )
    generation = ValidatedCandidateEpisodeGeneration(
        path=Path("/validated-b1-generation"),
        events=events,
        suppressions=(),
        episodes=tuple(episodes),
        receipt=generation_receipt(recorded_at=recorded_at, mapped=mapped),
    )
    return CandidateEpisodeStoreSnapshot(
        generation_id=generation_id,
        generation=generation,
    )


def episode(eid="pe:1", *, experts=()):
    return {
        "schema": "prophet.candidate_episode/v1",
        "episode_id": eid,
        "security_id": "SEC:US-XNAS-AAPL",
        "company_id": "ISS:US-XNAS-AAPL",
        "expert_events": list(experts),
    }


def turn_relation(
    eid="pe:1",
    *,
    event_type="OPENED",
    source_id="turn_watch:" + "1" * 64,
    relation_id="pee:" + "2" * 64,
    recorded_at=RECORDED,
    known_at="2026-09-17T20:00:00Z",
    occurred_at=None,
):
    return {
        "schema": "prophet.candidate_episode_event/v1",
        "event_id": relation_id,
        "event_type": event_type,
        "episode_id": eid,
        "source_system": "turn_watch",
        "source_schema": TURN_SCHEMA,
        "source_event_id": source_id,
        "source_receipt": "sha256:" + "3" * 64,
        "occurred_at": occurred_at or known_at,
        "known_at": known_at,
        "recorded_at": recorded_at,
        "correction_of": None,
        "payload": {"structural_anchor": {"kind": "turn_watch_reset_low"}},
    }


def retract_relation(
    target_relation_id,
    *,
    eid="pe:1",
    relation_id="pee:" + "f" * 64,
):
    return {
        "schema": "prophet.candidate_episode_event/v1",
        "event_id": relation_id,
        "event_type": "RETRACTED",
        "episode_id": eid,
        "source_system": "candidate_episode_correction",
        "source_schema": "prophet.candidate_episode_correction/v1",
        "source_event_id": "correction:" + "e" * 64,
        "source_receipt": "sha256:" + "d" * 64,
        "occurred_at": "2026-09-18T09:09:00Z",
        "known_at": "2026-09-18T09:09:00Z",
        "recorded_at": "2026-09-18T09:09:01Z",
        "correction_of": target_relation_id,
        "payload": {"reason": "withdrawn owner relation"},
    }


def radar(address="AAPL|C1|2026-09-17", *, family="radar_1d_turn", subtype="x"):
    return {
        "episode_address": address,
        "ticker": "AAPL",
        "detector_id": "C1",
        "family": family,
        "subtype": subtype,
        "decision_session": "2026-09-17",
        "signal_ts": "2026-09-17T18:00:00Z",
        "signal_known_ts": "2026-09-17T18:01:00Z",
        "observed_at": "2026-09-17T18:02:00Z",
        "observed_at_basis": "spool_envelope",
        "bar_state": "confirmed",
        "final": True,
        "detector_spec_hash": "4" * 64,
        "lobe_enlisted": None,
        "lobe_ids": None,
        "state": "LIVE_FORWARD",
        "first_seen_session": "2026-09-17",
        "spool_path": None,
    }


def tw_index(rows, *, mapped=None, recorded_at=RECORDED, generation_id=GEN):
    return index_turn_watch_events(
        snapshot(
            [],
            events=list(rows),
            generation_id=generation_id,
            recorded_at=recorded_at,
            mapped=mapped,
        )
    )


def empty_radar():
    return index_radar_rows(
        [],
        source_receipt={"sha256": "sha256:" + "6" * 64, "bytes": 0},
    )


def test_turn_watch_index_is_bound_to_atomic_snapshot_and_keeps_relation_provenance():
    current_open = turn_relation()
    current_observed = turn_relation(
        event_type="OBSERVED",
        source_id="turn_watch:" + "4" * 64,
        relation_id="pee:" + "5" * 64,
        known_at="2026-09-17T20:05:00Z",
    )
    historical = turn_relation(
        relation_id="pee:" + "6" * 64,
        recorded_at=OLDER_RECORDED,
    )
    foreign = dict(current_open)
    foreign["event_id"] = "pee:" + "7" * 64
    foreign["source_system"] = "candidate"

    source_snapshot = snapshot(
        [episode()],
        events=[historical, foreign, current_observed, current_open],
        mapped=2,
    )
    index = index_turn_watch_events(source_snapshot)

    assert list(index.facts_by_event_id) == sorted(
        [current_open["event_id"], current_observed["event_id"]]
    )
    fact = index.facts_by_event_id[current_open["event_id"]]
    assert fact["episode_id"] == "pe:1"
    assert fact["relation_event_type"] == "OPENED"
    assert fact["relation_event_id"] == current_open["event_id"]
    assert fact["source_event_id"] == current_open["source_event_id"]
    assert fact["source_receipt"] == current_open["source_receipt"]
    assert fact["known_at"] == current_open["known_at"]
    assert fact["occurred_at"] == current_open["occurred_at"]
    assert fact["recorded_at"] == RECORDED
    assert index.receipt["candidate_generation_id"] == GEN
    assert index.receipt["generation_recorded_at"] == RECORDED
    assert index.receipt["source_mapped"] == 2
    assert index.receipt["facts"] == 2
    assert index.receipt["withdrawn_relations"] == 0
    assert str(index.receipt["generation_receipt_sha256"]).startswith("sha256:")
    assert index.degraded_reasons == ()


def test_detached_generation_receipt_components_are_no_longer_an_api():
    with pytest.raises(TypeError):
        index_turn_watch_events(
            [turn_relation()],
            candidate_generation_id=GEN_OTHER,
            generation_receipt=generation_receipt(recorded_at=OLDER_RECORDED),
        )


def test_retracted_b1_relation_cannot_survive_into_b3_emergence():
    observed = turn_relation(
        event_type="OBSERVED",
        relation_id="pee:" + "8" * 64,
        source_id="turn_watch:" + "8" * 64,
    )
    withdrawn = retract_relation(observed["event_id"])
    source_snapshot = snapshot(
        [episode()],
        events=[observed, withdrawn],
        mapped=1,
    )
    index = index_turn_watch_events(source_snapshot)
    assert dict(index.facts_by_event_id) == {}
    assert index.receipt["withdrawn_relations"] == 1

    emergence, degraded = emergence_inputs(source_snapshot, radar=empty_radar())
    assert emergence["pe:1"]["state"] == "UNESTIMABLE"
    assert emergence["pe:1"]["reason"] == "SOURCE_NOT_SUPPLIED"
    assert degraded["pe:1"] == ()


def test_turn_watch_old_open_plus_current_observed_uses_current_observation_only():
    historical_open = turn_relation(recorded_at=OLDER_RECORDED)
    current_observed = turn_relation(
        event_type="OBSERVED",
        source_id="turn_watch:" + "8" * 64,
        relation_id="pee:" + "9" * 64,
        known_at="2026-09-17T20:10:00Z",
    )
    source_snapshot = snapshot(
        [episode()],
        events=[historical_open, current_observed],
        mapped=1,
    )
    emergence, degraded = emergence_inputs(source_snapshot, radar=empty_radar())

    assert emergence["pe:1"] == {
        "state": "TRIGGERED",
        "reason": None,
        "source_system": "turn_watch",
        "source_token": "B1_OBSERVED",
        "source_ref": current_observed["event_id"],
    }
    assert degraded["pe:1"] == ()


def test_historical_only_turn_watch_open_does_not_promote_current_emergence():
    source_snapshot = snapshot(
        [episode()],
        events=[turn_relation(recorded_at=OLDER_RECORDED)],
        mapped=1,
    )
    emergence, _ = emergence_inputs(source_snapshot, radar=empty_radar())
    assert emergence["pe:1"]["state"] == "UNESTIMABLE"
    assert emergence["pe:1"]["reason"] == "SOURCE_NOT_SUPPLIED"


def test_generation_receipt_recorded_at_mismatch_cannot_relabel_history_current():
    index = tw_index(
        [turn_relation()],
        mapped=1,
        recorded_at="2026-09-19T09:08:31Z",
    )
    assert dict(index.facts_by_event_id) == {}
    assert index.receipt["generation_recorded_at"] == "2026-09-19T09:08:31Z"


def test_generation_local_relations_cannot_exceed_receipt_mapped_count():
    with pytest.raises(CandidateStateSourceError, match="exceed receipt mapped"):
        tw_index([turn_relation()], mapped=0)


def test_emergence_requires_atomic_b1_snapshot_not_shape_compatible_parts():
    class FakeSnapshot:
        generation_id = GEN
        generation = object()

    with pytest.raises(CandidateStateSourceError, match="CandidateEpisodeStoreSnapshot"):
        emergence_inputs(FakeSnapshot(), radar=empty_radar())


def test_radar_forward_addresses_remain_provisional_even_when_hex_shaped():
    natural = radar()
    hex_shaped = radar("a" * 16)
    index = index_radar_rows(
        [natural, hex_shaped],
        source_receipt={"sha256": "sha256:" + "6" * 64, "bytes": 2},
    )

    for address in (natural["episode_address"], hex_shaped["episode_address"]):
        fact = index.facts_by_event_id[address]
        assert fact["source_system"] == "entry_radar"
        assert fact["source_schema"] is None
        assert fact["canonical_event_id"] is None
        assert (
            fact["source_contract_state"]
            == "PROVISIONAL_UNVERSIONED_EPISODE_ADDRESS"
        )
    assert index.receipt["source_schema"] is None


def test_radar_duplicate_same_content_collapses_and_order_is_irrelevant():
    a, b = radar("ere:b"), radar("ere:a")
    one = index_radar_rows(
        [a, b, a],
        source_receipt={"sha256": "sha256:" + "6" * 64, "bytes": 1},
    )
    two = index_radar_rows(
        [b, a],
        source_receipt={"sha256": "sha256:" + "6" * 64, "bytes": 1},
    )
    assert list(one.facts_by_event_id) == ["ere:a", "ere:b"]
    assert dict(one.facts_by_event_id) == dict(two.facts_by_event_id)


def test_radar_conflicting_duplicate_fails_closed():
    first = radar("ere:1")
    changed = {**first, "observed_at": "2026-09-17T19:00:00Z"}
    with pytest.raises(CandidateStateSourceError, match="conflicting duplicate"):
        index_radar_rows(
            [first, changed],
            source_receipt={"sha256": "sha256:" + "6" * 64, "bytes": 2},
        )


def test_missing_radar_source_is_named_degraded_not_clean_empty(tmp_path: Path):
    index = load_radar_fact_index(tmp_path / "missing.parquet")
    assert dict(index.facts_by_event_id) == {}
    assert index.degraded_reasons == ("RADAR_SOURCE_MISSING",)
    assert index.receipt["state"] == "MISSING"


def test_unversioned_radar_relation_cannot_manufacture_triggered_state():
    expert_id = "a" * 16
    source_snapshot = snapshot([episode(experts=(expert_id,))], events=[], mapped=0)
    rd = index_radar_rows(
        [radar(expert_id)],
        source_receipt={"sha256": "sha256:" + "6" * 64, "bytes": 1},
    )
    emergence, degraded = emergence_inputs(source_snapshot, radar=rd)

    assert emergence["pe:1"]["state"] == "UNESTIMABLE"
    assert emergence["pe:1"]["reason"] == "SOURCE_RELATION_UNRESOLVED"
    assert degraded["pe:1"] == (f"RADAR_EVENT_ID_UNPROVEN:{expert_id}",)


def test_current_turn_watch_open_is_a_source_proven_trigger():
    relation = turn_relation()
    source_snapshot = snapshot([episode()], events=[relation], mapped=1)
    emergence, degraded = emergence_inputs(source_snapshot, radar=empty_radar())
    assert emergence["pe:1"] == {
        "state": "TRIGGERED",
        "reason": None,
        "source_system": "turn_watch",
        "source_token": "B1_OPENED",
        "source_ref": relation["event_id"],
    }
    assert degraded["pe:1"] == ()


@pytest.mark.parametrize(
    ("earlier", "later"),
    [
        ("2026-09-17T18:00:00Z", "2026-09-17T18:00:00.100000Z"),
        ("2026-09-17T18:00:00.100000Z", "2026-09-17T18:00:00.200000Z"),
        ("2026-09-17T18:00:00.900000Z", "2026-09-17T18:00:01Z"),
    ],
)
def test_turn_watch_latest_fact_uses_parsed_utc_time_not_raw_string(earlier, later):
    first = turn_relation(
        source_id="turn_watch:a",
        relation_id="pee:a",
        known_at=earlier,
        occurred_at=earlier,
    )
    second = turn_relation(
        source_id="turn_watch:b",
        relation_id="pee:b",
        known_at=later,
        occurred_at=later,
    )
    source_snapshot = snapshot([episode()], events=[first, second], mapped=2)
    emergence, _ = emergence_inputs(source_snapshot, radar=empty_radar())
    assert emergence["pe:1"]["source_ref"] == "pee:b"


def test_equal_instant_uses_stable_source_id_tie_break():
    same = "2026-09-17T18:00:00.100000Z"
    first = turn_relation(
        source_id="turn_watch:a",
        relation_id="pee:z",
        known_at=same,
        occurred_at=same,
    )
    second = turn_relation(
        source_id="turn_watch:z",
        relation_id="pee:a",
        known_at=same,
        occurred_at=same,
    )
    source_snapshot = snapshot([episode()], events=[second, first], mapped=2)
    emergence, _ = emergence_inputs(source_snapshot, radar=empty_radar())
    assert emergence["pe:1"]["source_ref"] == "pee:a"


def test_mixed_historical_current_input_is_order_independent():
    old = turn_relation(
        recorded_at=OLDER_RECORDED,
        source_id="turn_watch:old",
        relation_id="pee:old",
        known_at="2026-09-16T18:00:00Z",
    )
    a = turn_relation(
        source_id="turn_watch:a",
        relation_id="pee:a",
        known_at="2026-09-17T18:00:00Z",
    )
    b = turn_relation(
        event_type="OBSERVED",
        source_id="turn_watch:b",
        relation_id="pee:b",
        known_at="2026-09-17T19:00:00Z",
    )
    one = snapshot([episode()], events=[old, a, b], mapped=2)
    two = snapshot([episode()], events=[b, old, a], mapped=2)

    got_one = emergence_inputs(one, radar=empty_radar())[0]
    got_two = emergence_inputs(two, radar=empty_radar())[0]
    assert got_one == got_two
    assert got_one["pe:1"]["source_token"] == "B1_OBSERVED"
    assert got_one["pe:1"]["source_ref"] == "pee:b"
