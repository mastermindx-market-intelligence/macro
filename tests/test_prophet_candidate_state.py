from dataclasses import dataclass

from engine.prophet_candidate_state import (
    project_candidate_states,
    validate_candidate_state_projection,
)

GEN = "peg:" + "a" * 64


@dataclass(frozen=True)
class Gen:
    episodes: tuple


@dataclass(frozen=True)
class Snap:
    generation_id: str
    generation: Gen


def ep(eid, state="ACTIVE", terminal_reason=None, superseded_by=None):
    return {
        "schema": "prophet.candidate_episode/v1",
        "episode_id": eid,
        "security_id": "SEC:US-XNAS-AAPL",
        "company_id": "ISS:US-XNAS-AAPL",
        "episode_state": state,
        "terminal_reason": terminal_reason,
        "superseded_by": superseded_by,
        "opened_at": "2026-09-17T20:00:00Z",
        "opened_session": "2026-09-17",
        "correction_state": "current",
    }


def test_lifecycle_mapping_preserves_source_truth_and_supersession_precedence():
    rows = (
        ep("pe:3", state="RESOLVED", terminal_reason="target"),
        ep("pe:1", state="ACTIVE", superseded_by="pe:9"),
        ep("pe:2", state="RETRACTED", terminal_reason="source retracted"),
        ep("pe:4", state="EXPIRED", terminal_reason="expired"),
    )
    out = project_candidate_states(
        Snap(GEN, Gen(rows)),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
    )
    got = {r["episode_id"]: r["episode_lifecycle"] for r in out["rows"]}
    assert got["pe:1"]["state"] == "SUPERSEDED"
    assert got["pe:1"]["source_state"] == "ACTIVE"
    assert got["pe:1"]["superseded_by"] == "pe:9"
    assert got["pe:2"]["state"] == "RETRACTED"
    assert got["pe:3"]["state"] == "CLOSED" and got["pe:3"]["source_state"] == "RESOLVED"
    assert got["pe:4"]["state"] == "CLOSED" and got["pe:4"]["source_state"] == "EXPIRED"


def test_maturity_maps_only_explicit_incumbent_stage_words():
    snapshot = Snap(
        GEN,
        Gen((ep("pe:1"), ep("pe:2"), ep("pe:3"), ep("pe:4"))),
    )
    out = project_candidate_states(
        snapshot,
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
        maturity_stage_by_episode={
            "pe:1": "EARLY",
            "pe:2": "CONFIRMING",
            "pe:3": "CONFIRMED",
            "pe:4": "topping",
        },
    )
    got = {r["episode_id"]: r["maturity_state"] for r in out["rows"]}
    assert got["pe:1"]["state"] == "PRE_CONFIRMATION"
    assert got["pe:2"]["state"] == "EARLY_CONFIRMATION"
    assert got["pe:3"]["state"] == "CONFIRMED"
    assert got["pe:4"]["state"] == "UNESTIMABLE"
    assert got["pe:4"]["source_token"] == "topping"


def test_legacy_live_forming_does_not_manufacture_b3_emergence():
    snapshot = Snap(GEN, Gen((ep("pe:1"),)))
    out = project_candidate_states(
        snapshot,
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
        emergence_by_episode={
            "pe:1": {
                "state": "UNESTIMABLE",
                "source_system": "prophet_live",
                "source_token": "forming",
                "source_ref": "pl:1",
            }
        },
    )
    row = out["rows"][0]
    assert row["emergence_state"]["state"] == "UNESTIMABLE"
    assert row["emergence_state"]["source_token"] == "forming"


def test_b4_slot_is_unavailable_even_when_legacy_entry_status_looks_actionable():
    episode = ep("pe:1")
    episode["entry_status"] = "buy_now"
    episode["plan_lifecycle"] = "active"
    out = project_candidate_states(
        Snap(GEN, Gen((episode,))),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
    )
    row = out["rows"][0]
    assert row["entry_availability"] == {
        "state": "UNAVAILABLE_DATA",
        "reason": "B4_NOT_AVAILABLE",
    }
    assert "entry_status" not in row and "plan_lifecycle" not in row


def test_projection_is_deterministic_sorted_and_has_no_authority():
    a, b = ep("pe:z"), ep("pe:a")
    one = project_candidate_states(
        Snap(GEN, Gen((a, b))),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
    )
    two = project_candidate_states(
        Snap(GEN, Gen((b, a))),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
    )
    assert one == two
    assert [r["episode_id"] for r in one["rows"]] == ["pe:a", "pe:z"]
    assert not any(one["authority"].values())
    assert all(not any(r["authority"].values()) for r in one["rows"])
    validate_candidate_state_projection(one)
