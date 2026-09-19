from pathlib import Path

import pytest

from engine.prophet_candidate_state_sources import (
    CandidateStateSourceError,
    emergence_inputs,
    index_radar_rows,
    index_turn_watch_events,
    load_radar_fact_index,
)

GEN = "peg:" + "a" * 64


class G:
    def __init__(self, episodes):
        self.episodes = tuple(episodes)


class S:
    def __init__(self, episodes):
        self.generation_id = GEN
        self.generation = G(episodes)


def episode(eid="pe:1", *, experts=()):
    return {
        "schema": "prophet.candidate_episode/v1",
        "episode_id": eid,
        "security_id": "SEC:US-XNAS-AAPL",
        "company_id": "ISS:US-XNAS-AAPL",
        "expert_events": list(experts),
    }


def opened(eid="pe:1", source_id="turn_watch:" + "1" * 64):
    return {
        "schema": "prophet.candidate_episode_event/v1",
        "event_id": "pev:" + "2" * 64,
        "event_type": "OPENED",
        "episode_id": eid,
        "source_system": "turn_watch",
        "source_schema": "prophet.candidate_episode_input.turn_watch/v1",
        "source_event_id": source_id,
        "source_receipt": "sha256:" + "3" * 64,
        "occurred_at": "2026-09-17T20:00:00Z",
        "known_at": "2026-09-17T20:00:00Z",
        "payload": {"structural_anchor": {"kind": "turn_watch_reset_low"}},
    }


def radar(eid="ere:1", *, family="radar_1d_turn", subtype="x"):
    return {
        "episode_address": eid,
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


def test_turn_watch_index_uses_only_exact_b1_owner_relation():
    good = opened()
    foreign = dict(good)
    foreign["event_id"] = "pev:" + "5" * 64
    foreign["source_system"] = "candidate"
    index = index_turn_watch_events([foreign, good], candidate_generation_id=GEN)

    assert list(index.facts_by_event_id) == [good["source_event_id"]]
    fact = index.facts_by_event_id[good["source_event_id"]]
    assert fact["episode_id"] == "pe:1"
    assert fact["source_receipt"] == good["source_receipt"]
    assert fact["known_at"] == good["known_at"]
    assert index.degraded_reasons == ()


def test_radar_duplicate_same_content_collapses_and_order_is_irrelevant():
    a, b = radar("ere:b"), radar("ere:a")
    one = index_radar_rows([a, b, a], source_receipt={"sha256": "sha256:" + "6" * 64, "bytes": 1})
    two = index_radar_rows([b, a], source_receipt={"sha256": "sha256:" + "6" * 64, "bytes": 1})

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


def test_emergence_uses_exact_relations_and_preserves_unresolved_expert():
    tw = index_turn_watch_events([opened()], candidate_generation_id=GEN)
    rd = index_radar_rows(
        [radar("ere:found")],
        source_receipt={"sha256": "sha256:" + "6" * 64, "bytes": 1},
    )
    snapshot = S([episode(experts=("ere:found", "ere:missing"))])

    emergence, degraded = emergence_inputs(snapshot, turn_watch=tw, radar=rd)

    assert emergence["pe:1"]["state"] == "TRIGGERED"
    assert emergence["pe:1"]["source_system"] == "entry_radar"
    assert emergence["pe:1"]["source_ref"] == "ere:found"
    assert "RADAR_EVENT_UNRESOLVED:ere:missing" in degraded["pe:1"]


def test_turn_watch_open_alone_is_a_source_proven_trigger():
    tw = index_turn_watch_events([opened()], candidate_generation_id=GEN)
    rd = index_radar_rows([], source_receipt={"sha256": "sha256:" + "6" * 64, "bytes": 0})
    emergence, degraded = emergence_inputs(S([episode()]), turn_watch=tw, radar=rd)

    assert emergence["pe:1"] == {
        "state": "TRIGGERED",
        "reason": None,
        "source_system": "turn_watch",
        "source_token": "B1_OPENED",
        "source_ref": "turn_watch:" + "1" * 64,
    }
    assert degraded["pe:1"] == ()
