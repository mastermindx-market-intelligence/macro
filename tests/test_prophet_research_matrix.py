from __future__ import annotations

from engine.entry_radar.entry_events import build_radar_native_event
from engine.prophet_research_matrix import (
    CONTROL_SCHEMA,
    MATRIX_SCHEMA,
    POPULATION_SCOPE,
    ResearchMatrixContractError,
    build_pit_research_matrix,
)
from engine.stock_identity import fingerprint
from engine.us_candidate_episode import apply_commands, reconcile_observations


ERA = "candidate-episode-v1-2026-08-25"
ANCHOR = {
    "kind": "turn_watch_reset_low",
    "time": "2026-08-24T20:00:00Z",
    "price": 42.1,
    "basis": "adjusted_close",
    "source_receipt": "sha256:anchor-owner",
}


def _open_observation(**extra):
    row = {
        "security_id": "SEC:US-XNAS-XYZ",
        "company_id": "ISS:US-XNAS-XYZ",
        "ticker_at_observation": "XYZ",
        "identity_epoch": "epoch_0",
        "identity_epoch_state": "provisional",
        "identity_spec_schema": "stock_identity.fingerprint_spec.v1",
        "identity_spec_hash": fingerprint.spec_hash(),
        "anchor": ANCHOR,
        "intake_class": "technical_emergence",
        "occurred_at": "2026-08-24T20:00:00Z",
        "known_at": "2026-08-24T20:00:00Z",
        "source_system": "turn_watch",
        "source_schema": "turn_watch.candidate_input/v1",
        "source_event_id": "turn-watch:XYZ:2026-08-24",
        "source_receipt": "sha256:turn-watch-input",
    }
    row.update(extra)
    return row


def _opened(recorded_at: str = "2026-08-25T01:00:00Z"):
    return reconcile_observations(
        [], [_open_observation()], recorded_at=recorded_at, definition_era=ERA
    )


def _radar_event(*, known_at: str | None = "2026-08-25T01:30:00Z"):
    return build_radar_native_event(
        detector_id="C2_TURN@1",
        detector_spec_hash="spec:test",
        ticker="XYZ",
        family="radar_1d_turn",
        subtype="c2a_kd_cross",
        signal_ts="2026-08-25T01:20:00Z",
        signal_known_ts=known_at,
        market_session="2026-08-24",
        bar_state="provisional",
        context={"reason": "test-only"},
    )


def _with_expert(recorded_at: str = "2026-08-25T01:45:00Z"):
    opened = _opened()
    radar = _radar_event()
    expert = _open_observation(
        anchor=None,
        source_system="entry_radar",
        source_schema="mastermind.entry_event.v1",
        source_event_id=radar.event_id,
        expert_event_id=radar.event_id,
        intake_class="radar_expert",
        occurred_at="2026-08-25T01:20:00Z",
        known_at="2026-08-25T01:30:00Z",
        source_receipt="sha256:radar-expert-input",
    )
    attached = reconcile_observations(
        opened.events, [expert], recorded_at=recorded_at, definition_era=ERA
    )
    return attached, radar


def test_rq1_matrix_is_asof_authority_false_and_resolves_exact_radar_event():
    attached, radar = _with_expert()
    matrix = build_pit_research_matrix(
        events=attached.events,
        generation_id="gen:test",
        decision_at="2026-08-25T02:00:00Z",
        radar_events={radar.event_id: radar},
    )
    assert matrix["schema"] == MATRIX_SCHEMA
    assert matrix["population_scope"] == POPULATION_SCOPE
    assert matrix["eligible_population_n"] == 1
    assert matrix["matrix_receipt"].startswith("sha256:")
    assert all(value is False for value in matrix["authority"].values())

    row = matrix["rows"][0]
    assert row["candidate_episode_id"] == attached.episodes[0]["episode_id"]
    assert row["security_id"] == "SEC:US-XNAS-XYZ"
    assert row["incumbent_control"]["status"] == "NOT_SUPPLIED"
    assert "INCUMBENT_CONTROL_NOT_SUPPLIED" in row["missingness"]
    expert = row["expert_observations"][0]
    assert expert["expert_event_id"] == radar.event_id
    assert expert["resolution_status"] == "RESOLVED"
    assert expert["family"] == "radar_1d_turn"
    assert expert["subtype"] == "c2a_kd_cross"
    assert all(value is False for value in expert["authority"].values())


def test_future_recorded_attachment_and_later_correction_do_not_leak_backward():
    attached, radar = _with_expert(recorded_at="2026-08-25T03:00:00Z")
    episode_id = attached.episodes[0]["episode_id"]
    corrected = apply_commands(
        attached.events,
        [{
            "event_type": "CORRECTED",
            "episode_id": episode_id,
            "source_system": "operator",
            "source_schema": "operator.command/v1",
            "source_event_id": "operator:later-correction",
            "occurred_at": "2026-08-25T03:05:00Z",
            "known_at": "2026-08-25T03:05:00Z",
            "source_receipt": "sha256:operator-later",
            "correction_of": attached.events[0]["event_id"],
            "payload": {"patch": {"ticker_at_observation": "XYZ2"}},
        }],
        recorded_at="2026-08-25T03:10:00Z",
        definition_era=ERA,
    )
    matrix = build_pit_research_matrix(
        events=corrected.events,
        generation_id="gen:test",
        decision_at="2026-08-25T02:00:00Z",
        radar_events={radar.event_id: radar},
    )
    row = matrix["rows"][0]
    assert row["episode_correction_state"] == "current"
    assert row["expert_observations"] == []


def test_missing_radar_owner_bytes_remain_missing_not_negative():
    attached, _ = _with_expert()
    matrix = build_pit_research_matrix(
        events=attached.events,
        generation_id="gen:test",
        decision_at="2026-08-25T02:00:00Z",
    )
    row = matrix["rows"][0]
    assert row["expert_observations"][0]["resolution_status"] == "OWNER_EVENT_NOT_SUPPLIED"
    assert "RADAR_OWNER_EVENT_NOT_SUPPLIED" in row["missingness"]
    assert matrix["source_law"]["unknown_becomes_zero"] is False


def test_owner_supplied_control_requires_pit_clock_and_sha_receipt():
    opened = _opened()
    episode_id = opened.episodes[0]["episode_id"]
    receipt = "sha256:" + "a" * 64
    control = {
        "schema": CONTROL_SCHEMA,
        "episode_id": episode_id,
        "control_id": "v3-priority/control@1",
        "known_at": "2026-08-25T01:30:00Z",
        "source_system": "prophet-v3-control-owner",
        "source_receipt": receipt,
        "payload": {"priority": 0.42},
    }
    matrix = build_pit_research_matrix(
        events=opened.events,
        generation_id="gen:test",
        decision_at="2026-08-25T02:00:00Z",
        incumbent_controls={episode_id: control},
    )
    row = matrix["rows"][0]
    assert row["incumbent_control"]["status"] == "OBSERVED"
    assert row["incumbent_control"]["payload"] == {"priority": 0.42}
    assert "INCUMBENT_CONTROL_NOT_SUPPLIED" not in row["missingness"]

    future = {**control, "known_at": "2026-08-25T02:01:00Z"}
    try:
        build_pit_research_matrix(
            events=opened.events,
            generation_id="gen:test",
            decision_at="2026-08-25T02:00:00Z",
            incumbent_controls={episode_id: future},
        )
    except ResearchMatrixContractError as exc:
        assert "future-known" in str(exc)
    else:
        raise AssertionError("future-known incumbent control must fail closed")
