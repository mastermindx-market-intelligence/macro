"""Current-evidence passports for BTC impulse observations.

These tests pin two independent clocks:
* the model gate is current only for validation age 0 or 1 UTC days;
* a date-only BTC event loses timing authority at the START of event_date+3.

The validator's existing artifact has no schema/model-version field.  Absence is
reported, never invented and never used to self-certify the evidence.
"""
from __future__ import annotations

from datetime import date

import pytest

from engine import btc_impulse_radar as radar
from engine import signal_evidence as E


def _gate(*, asof="2026-09-10", d2="leading", d3="leading", u1="leading",
          ok=True, label="fwd(3d) +-5%"):
    statuses = {"d2": d2, "d3": d3, "u1": u1}
    specs = {
        "d2": {"dir": "down", "floor": 1.5, "label": "Vol-of-vol jolt (DVOL range)"},
        "d3": {"dir": "down", "floor": 1.3, "label": "SOPR profit-take spike"},
        "u1": {"dir": "up", "floor": 1.3, "label": "SOPR capitulation (wash-out)"},
    }
    legs = {}
    for key, status in statuses.items():
        row = {
            "status": status,
            "pass": status == "leading",
            "dir": specs[key]["dir"],
            "label": specs[key]["label"],
            "floor": specs[key]["floor"],
            "min_holdout_n": 30,
            "lift_holdout": {"d2": 1.826, "d3": 1.198, "u1": 1.7}[key],
            "perm_p": {"d2": 0.4343, "d3": 0.4213, "u1": 0.0025}[key],
            "n_fires_holdout": {"d2": 61, "d3": 31, "u1": 14}[key],
        }
        if status == "no_data":
            row = {"status": "no_data", "pass": None, "label": specs[key]["label"]}
        legs[key] = row
    return {
        "ok": ok,
        "asof": asof,
        "all_pass": all(row.get("pass") is True for row in legs.values()),
        "holdout_start": "2024-01-01",
        "label": label,
        "legs": legs,
    }


def test_model_permission_uses_existing_gate_contract_without_inventing_version():
    gate = _gate()
    gate["all_pass"] = False  # a sibling summary never vetoes an eligible exact leg
    out = radar.resolve_leg_permission(gate, "d2", date(2026, 9, 10))
    assert out["permitted"] is True
    assert out["reason"] == "eligible"
    assert out["identity"] == "d2"
    assert out["direction"] == "down"
    assert out["validation_asof"] == "2026-09-10"
    assert out["model_version"] is None
    assert out["version_state"] == "absent"
    assert out["stats"][0]["n_fires_holdout"] == 61


@pytest.mark.parametrize(
    ("snapshot", "identity", "evaluation", "reason"),
    [
        ({"read_state": "missing", "artifact": None, "path": "/missing"}, "d2", "2026-09-10", "gate_missing"),
        ({"read_state": "corrupt", "artifact": None, "path": "/bad"}, "d2", "2026-09-10", "gate_corrupt"),
        ({}, "d2", "2026-09-10", "gate_unavailable"),
        (_gate(ok=False), "d2", "2026-09-10", "gate_unavailable"),
        (_gate(label="fwd(5d) +-10%"), "d2", "2026-09-10", "target_mismatch"),
        (_gate(asof="not-a-date"), "d2", "2026-09-10", "validation_time_invalid"),
        (_gate(asof="2026-09-11"), "d2", "2026-09-10", "future_validation"),
        (_gate(asof="2026-09-08"), "d2", "2026-09-10", "stale_validation"),
        (_gate(), "d9", "2026-09-10", "unknown_identity"),
        (_gate(), "d2", None, "evaluation_time_invalid"),
    ],
)
def test_model_permission_fails_closed(snapshot, identity, evaluation, reason):
    out = radar.resolve_leg_permission(snapshot, identity, evaluation)
    assert out["permitted"] is False
    assert out["reason"] == reason


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda g: g["legs"].__setitem__("d2", "leading"), "leg_malformed"),
        (lambda g: g["legs"]["d2"].__setitem__("status", "mystery"), "unknown_status"),
        (lambda g: g["legs"]["d2"].__setitem__("pass", False), "inconsistent_verdict"),
        (lambda g: g["legs"]["d2"].__setitem__("dir", "up"), "leg_contract_mismatch"),
        (lambda g: g["legs"]["d2"].__setitem__("floor", 999.0), "leg_contract_mismatch"),
        (lambda g: g["legs"]["d2"].__setitem__("min_holdout_n", 29), "leg_contract_mismatch"),
        (lambda g: g["legs"]["d2"].__setitem__("label", "different"), "leg_contract_mismatch"),
        (lambda g: g["legs"].__setitem__("extra", {}), "legs_contract_mismatch"),
    ],
)
def test_model_permission_rejects_malformed_or_conflicting_leg_rows(mutate, reason):
    gate = _gate()
    mutate(gate)
    out = radar.resolve_leg_permission(gate, "d2", "2026-09-10")
    assert out["permitted"] is False
    assert out["reason"] == reason


def test_model_permission_preserves_observed_nonleading_statuses_and_composite_is_exact():
    gate = _gate(d2="demoted", d3="leading", u1="insufficient_n")
    assert radar.resolve_leg_permission(gate, "d2", "2026-09-10")["reason"] == "demoted"
    assert radar.resolve_leg_permission(gate, "u1", "2026-09-10")["reason"] == "insufficient_n"
    combo = radar.resolve_leg_permission(gate, "d2+d3", "2026-09-10")
    assert combo["permitted"] is False
    assert combo["reason"] == "demoted"
    gate2 = _gate(d2="leading", d3="leading", u1="demoted")
    assert radar.resolve_leg_permission(gate2, "d2+d3", "2026-09-10")["permitted"] is True


def test_date_only_event_is_active_through_age_two_and_expires_at_start_of_age_three():
    # Source freshness belongs to the event's observation clock, not the later
    # board day.  A two-day-old event can remain inside its declared forward
    # window without pretending its source observation happened today.
    active = E.impulse_passport(
        "d2", event_at="2026-09-07", event_precision="date",
        board_date=date(2026, 9, 9), source_asof="2026-09-07",
        gate=_gate(asof="2026-09-09"),
    )
    expired = E.impulse_passport(
        "d2", event_at="2026-09-07", event_precision="date",
        board_date=date(2026, 9, 10), source_asof="2026-09-07",
        gate=_gate(asof="2026-09-10"),
    )
    assert active["event_state"] == "active"
    assert active["source_state"] == "current"
    assert active["source_asof"] == "2026-09-07"
    assert active["event_expires_on"] == "2026-09-10"
    assert active["claim_eligible"] is True
    assert expired["event_state"] == "expired"
    assert expired["source_state"] == "current"
    assert expired["event_expires_on"] == "2026-09-10"
    assert expired["claim_eligible"] is False
    assert expired["expiry_convention"] == "date-only BTC event expires at 00:00 UTC on event_date+3"


def test_event_gate_and_source_clocks_remain_independent():
    gate = _gate(d2="demoted")
    p = E.impulse_passport(
        "d2", event_at="2026-09-07", event_precision="date",
        board_date="2026-09-10", source_asof="2026-09-07", gate=gate,
    )
    assert p["gate_status"] == "demoted"
    assert p["validation_state"] == "current"
    assert p["event_state"] == "expired"
    assert p["source_state"] == "current"
    assert p["status"] == "demoted"  # current evidence is the primary refusal
    assert p["permitted_use"] == "history_only"


def test_source_clock_is_evaluated_at_event_time_not_refreshed_by_board_day():
    # This is the key no-self-freshening falsifier: a later board render must not
    # make an event-era source observation stale merely because the event remains
    # inside its measured window, nor accept a source dated after the event.
    current = E.impulse_passport(
        "d2", event_at="2026-09-08", event_precision="date",
        board_date="2026-09-10", source_asof="2026-09-08",
        gate=_gate(asof="2026-09-10"),
    )
    future_at_issue = E.impulse_passport(
        "d2", event_at="2026-09-08", event_precision="date",
        board_date="2026-09-10", source_asof="2026-09-09",
        gate=_gate(asof="2026-09-10"),
    )
    assert current["event_state"] == "active"
    assert current["source_state"] == "current"
    assert current["claim_eligible"] is True
    assert future_at_issue["source_state"] == "future_source"
    assert future_at_issue["claim_eligible"] is False


@pytest.mark.parametrize(
    ("event_at", "source_asof", "status"),
    [
        (None, "2026-09-10", "unknown_event_time"),
        ("2026-09-11", "2026-09-10", "future_event"),
        ("2026-09-10", None, "source_time_invalid"),
        ("2026-09-10", "2026-09-11", "future_source"),
        ("2026-09-10", "2026-09-08", "stale_source"),
    ],
)
def test_event_or_source_clock_cannot_silently_authorize(event_at, source_asof, status):
    p = E.impulse_passport(
        "d2", event_at=event_at, event_precision="date",
        board_date="2026-09-10", source_asof=source_asof, gate=_gate(),
    )
    assert p["claim_eligible"] is False
    assert status in {p["status"], p["event_state"], p["source_state"]}


def test_unknown_identity_returns_an_observable_refusal_instead_of_raising():
    p = E.impulse_passport(
        "mystery", event_at="2026-09-10", event_precision="date",
        board_date="2026-09-10", source_asof="2026-09-10", gate=_gate(),
    )
    assert p["claim_eligible"] is False
    assert p["status"] == "unknown_identity"
    assert p["signal_id"] is None
    assert p["anchor"] == "signal-lab-btc-impulse"


# CANONICAL GATE LOADER REGRESSIONS

def test_default_gate_loader_uses_evaluator_loader_once(monkeypatch, tmp_path):
    from engine import btc_impulse_radar_backtest as evaluator

    path = tmp_path / "impulse_legs_gate.json"
    path.write_text("{}")
    calls = {"n": 0}

    def load():
        calls["n"] += 1
        return _gate()

    monkeypatch.setattr(evaluator, "gate_path", lambda: path)
    monkeypatch.setattr(evaluator, "load_gate", load)
    out = E.load_btc_gate()
    assert calls["n"] == 1
    assert out == {"read_state": "ok", "artifact": _gate(), "path": str(path)}


def test_default_gate_loader_distinguishes_missing_from_unreadable(monkeypatch, tmp_path):
    from engine import btc_impulse_radar_backtest as evaluator

    missing = tmp_path / "missing.json"
    monkeypatch.setattr(evaluator, "gate_path", lambda: missing)
    monkeypatch.setattr(evaluator, "load_gate", lambda: {})
    assert E.load_btc_gate()["read_state"] == "missing"

    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not-json")
    monkeypatch.setattr(evaluator, "gate_path", lambda: corrupt)
    assert E.load_btc_gate()["read_state"] == "corrupt"
