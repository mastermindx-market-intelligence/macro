from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json

import pytest

from engine.prophet_candidate_state import (
    CandidateStateContractError,
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


def ep(
    eid,
    state="ACTIVE",
    terminal_reason=None,
    superseded_by=None,
    identity_epoch="epoch_0",
):
    return {
        "schema": "prophet.candidate_episode/v1",
        "episode_id": eid,
        "security_id": "SEC:US-XNAS-AAPL",
        "company_id": "ISS:US-XNAS-AAPL",
        "identity_epoch": identity_epoch,
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

def _rehash_projection(payload):
    material = {key: value for key, value in payload.items() if key != "projection_id"}
    canonical = json.dumps(
        material, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    payload["projection_id"] = "pcs:" + sha256(canonical.encode("utf-8")).hexdigest()


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("generated_at", "garbageZ"),
        ("generated_at", "2026-99-99T25:61:61Z"),
        ("market_session", "2026-99-99"),
        ("market_session", "2026-02-31"),
    ],
)
def test_projection_rejects_impossible_decision_clocks(field, bad_value):
    kwargs = {
        "market_session": "2026-09-17",
        "generated_at": "2026-09-18T01:00:00Z",
    }
    kwargs[field] = bad_value
    with pytest.raises(CandidateStateContractError):
        project_candidate_states(Snap(GEN, Gen((ep("pe:1"),))), **kwargs)


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("generated_at", "garbageZ"),
        ("generated_at", "2026-99-99T25:61:61Z"),
        ("market_session", "2026-99-99"),
        ("market_session", "2026-02-31"),
    ],
)
def test_validator_rejects_rehashed_impossible_decision_clocks(field, bad_value):
    out = project_candidate_states(
        Snap(GEN, Gen((ep("pe:1"),))),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
    )
    tampered = deepcopy(out)
    tampered[field] = bad_value
    _rehash_projection(tampered)
    with pytest.raises(CandidateStateContractError):
        validate_candidate_state_projection(tampered)


def test_validator_rejects_rehashed_trigger_without_source_provenance():
    out = project_candidate_states(
        Snap(GEN, Gen((ep("pe:1"),))),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
        emergence_by_episode={
            "pe:1": {
                "state": "TRIGGERED",
                "reason": None,
                "source_system": "turn_watch",
                "source_token": "OPENED",
                "source_ref": "tw:1",
            }
        },
    )
    tampered = deepcopy(out)
    tampered["rows"][0]["emergence_state"] = {
        "state": "TRIGGERED",
        "reason": None,
        "source_system": None,
        "source_token": None,
        "source_ref": None,
    }
    _rehash_projection(tampered)
    with pytest.raises(CandidateStateContractError):
        validate_candidate_state_projection(tampered)


def test_validator_rejects_rehashed_incoherent_lifecycle():
    out = project_candidate_states(
        Snap(GEN, Gen((ep("pe:1"),))),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
    )
    tampered = deepcopy(out)
    tampered["rows"][0]["episode_lifecycle"]["state"] = "CLOSED"
    _rehash_projection(tampered)
    with pytest.raises(CandidateStateContractError):
        validate_candidate_state_projection(tampered)


def test_validator_rejects_rehashed_incoherent_maturity():
    out = project_candidate_states(
        Snap(GEN, Gen((ep("pe:1"),))),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
        maturity_stage_by_episode={"pe:1": "EARLY"},
    )
    tampered = deepcopy(out)
    tampered["rows"][0]["maturity_state"]["state"] = "MATURE"
    _rehash_projection(tampered)
    with pytest.raises(CandidateStateContractError):
        validate_candidate_state_projection(tampered)


def test_projection_preserves_b1_identity_epoch_for_b4_keying():
    out = project_candidate_states(
        Snap(
            GEN,
            Gen(
                (
                    ep("pe:epoch0", identity_epoch="epoch_0"),
                    ep("pe:epoch1", identity_epoch="epoch_1"),
                )
            ),
        ),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
    )
    got = {row["episode_id"]: row["identity_epoch"] for row in out["rows"]}
    assert got == {"pe:epoch0": "epoch_0", "pe:epoch1": "epoch_1"}


def test_validator_rejects_rehashed_missing_or_empty_identity_epoch():
    out = project_candidate_states(
        Snap(GEN, Gen((ep("pe:1", identity_epoch="epoch_0"),))),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
    )

    missing = deepcopy(out)
    missing["rows"][0].pop("identity_epoch")
    _rehash_projection(missing)
    with pytest.raises(CandidateStateContractError):
        validate_candidate_state_projection(missing)

    empty = deepcopy(out)
    empty["rows"][0]["identity_epoch"] = ""
    _rehash_projection(empty)
    with pytest.raises(CandidateStateContractError):
        validate_candidate_state_projection(empty)
