"""End-to-end current-authority projection for alert trust."""
from __future__ import annotations

from datetime import date

import pandas as pd

from engine import alert_triage as at
from engine import btc_alerts


def _gate(*, asof="2026-09-10", d2="leading", d3="leading", u1="leading"):
    specs = {
        "d2": ("down", 1.5, "Vol-of-vol jolt (DVOL range)"),
        "d3": ("down", 1.3, "SOPR profit-take spike"),
        "u1": ("up", 1.3, "SOPR capitulation (wash-out)"),
    }
    statuses = {"d2": d2, "d3": d3, "u1": u1}
    return {
        "ok": True, "asof": asof, "all_pass": False,
        "holdout_start": "2024-01-01", "label": "fwd(3d) +-5%",
        "legs": {
            k: {
                "status": st, "pass": st == "leading", "dir": specs[k][0],
                "label": specs[k][2], "floor": specs[k][1], "min_holdout_n": 30,
                "lift_holdout": 1.7, "perm_p": 0.01, "n_fires_holdout": 40,
            }
            for k, st in statuses.items()
        },
    }


def _event(*, type_="impulse_warn_down", event_id="impulse_warn_down:2026-09-10T00:00:d2",
           tier="act", context=None, evidence=None, validation_evidence=None,
           source="vector", asset="vector", severity="high", headline="Observed fire"):
    return {
        "id": event_id, "ts": "2026-09-10T00:00:00", "source": source,
        "asset": asset, "type": type_, "severity": severity, "tier": tier,
        "headline": headline, "headline_zh": headline, "detail": "detail",
        "detail_zh": "detail", "edge": "old issue-time claim",
        "edge_zh": "旧触发时声明", "forward": "", "forward_zh": "",
        "anchor": "#impulse", "source_asof": "2026-09-10",
        "context": context or {"leg": "d2", "evidence_key": "d2"},
        "evidence": evidence, "validation_evidence": validation_evidence,
    }


def test_emitter_loads_one_gate_snapshot_and_keeps_raw_ids_and_original_claim(monkeypatch):
    idx = pd.date_range("2026-09-01", periods=10, freq="D")
    fires = pd.DataFrame({
        "d2": [False] * 9 + [True], "d3": [False] * 10, "u1": [False] * 10,
    }, index=idx)
    sig = pd.DataFrame({"close": 60000.0}, index=idx)
    monkeypatch.setattr("engine.btc_impulse_radar.fire_series", lambda frame=None: fires)
    calls = {"n": 0}
    def load():
        calls["n"] += 1
        return _gate(d2="demoted")
    monkeypatch.setattr("engine.btc_impulse_radar_backtest.load_gate", load)

    rows = btc_alerts.impulse_radar_events(sig, board_date=date(2026, 9, 10))
    assert calls["n"] == 1
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == "impulse_warn_down:2026-09-10T00:00:d2"
    assert row["tier"] == "context" and row["observed_tier"] == "act"
    assert row["claim_eligible"] is False
    assert row["original_claim"]["event_id"] == row["id"]
    assert "old issue-time claim" not in row["edge"]
    assert row["evidence"]["reason"] == "demoted"


def test_emitter_stamps_event_specific_source_asof_not_latest_rebuild_day(monkeypatch):
    idx = pd.date_range("2026-09-01", periods=10, freq="D")
    fires = pd.DataFrame({
        "d2": [False] * 7 + [True, False, False],
        "d3": [False] * 10,
        "u1": [False] * 10,
    }, index=idx)
    sig = pd.DataFrame({"close": 60000.0}, index=idx)
    monkeypatch.setattr("engine.btc_impulse_radar.fire_series", lambda frame=None: fires)

    rows = btc_alerts.impulse_radar_events(
        sig, gate=_gate(), board_date=date(2026, 9, 10),
    )
    row = next(r for r in rows if r["id"].startswith("impulse_warn_down:2026-09-08"))
    assert row["source_asof"] == "2026-09-08"
    assert row["evidence"]["source_state"] == "current"
    assert row["evidence"]["event_state"] == "active"
    assert row["claim_eligible"] is True


def test_persisted_issue_time_claim_survives_recomputation_of_same_id(monkeypatch, tmp_path):
    idx = pd.date_range("2026-09-01", periods=10, freq="D")
    sig = pd.DataFrame({
        "close": 60000.0,
        "risk_regime": "low_risk", "risk_index": 10.0,
        "structure_state": "neutral", "structure": 0.0,
        "momentum_state": "neutral", "momentum": 0.0,
        "alloc_optimal": 0.0,
    }, index=idx)
    fires = pd.DataFrame({
        "d2": [False] * 9 + [True], "d3": [False] * 10, "u1": [False] * 10,
    }, index=idx)
    monkeypatch.setattr("engine.btc_impulse_radar.fire_series", lambda frame=None: fires)
    monkeypatch.setattr(btc_alerts, "risk_extreme_events", lambda *_: [])
    monkeypatch.setattr(btc_alerts, "leverage_derisk_events", lambda *_: [])
    monkeypatch.setattr(btc_alerts, "flash_events", lambda *_: [])
    old = _event()
    old["headline"] = "Original persisted headline"
    old["detail"] = "Original persisted detail"
    old["edge"] = "Original persisted predictive claim"
    monkeypatch.setattr(btc_alerts, "load_events", lambda: [old])

    rows = btc_alerts.compute_all_events(sig, gate=_gate(d2="demoted"), board_date=date(2026, 9, 10))
    row = next(r for r in rows if r["id"] == old["id"])
    claim = row["original_claim"]
    assert claim["headline"] == old["headline"]
    assert claim["detail"] == old["detail"]
    assert claim["edge"] == old["edge"]
    assert row["edge"] != old["edge"]
    assert row["tier"] == "context"


def test_jsonl_normalizer_preserves_typed_provenance(monkeypatch):
    raw = _event()
    raw["observed_tier"] = "act"
    raw["direction"] = "down"
    raw["signal_id"] = "btc_impulse.d2"
    raw["original_claim"] = {"headline": "issued", "event_id": raw["id"]}
    monkeypatch.setattr(btc_alerts, "load_events", lambda: [raw])
    out = at._jsonl_raw("vector", date(2026, 9, 10), date(2026, 8, 1), {})
    row = out["events"][0]
    assert row["event_id"] == raw["id"]
    assert row["context"]["evidence_key"] == "d2"
    assert row["original_claim"]["headline"] == "issued"
    assert row["observed_tier"] == "act"
    assert row["direction"] == "down"
    assert row["signal_id"] == "btc_impulse.d2"


def test_arbitrary_vector_prose_is_not_calibration_evidence():
    reg = at._registry_index()
    prose = at._validation("vector", "risk_regime", "Sounds proven.", "", reg)
    assert prose["backtested"] is False
    assert prose["verdict"] == "documented"
    explicit = at._validation(
        "vector", "risk_regime", "Sounds proven.", "", reg,
        validation_evidence={
            "kind": "calibration", "artifact": "data/vector/calibration.json",
            "signal_key": "risk_index", "asof": "2026-09-05",
            "verdict": "DIRECTIONAL (one half weak)",
        },
    )
    assert explicit["backtested"] == "engine"
    assert explicit["verdict"] == "calibrated"


def test_current_impulse_passport_controls_tier_action_priority_and_exact_link(monkeypatch):
    event = _event()
    monkeypatch.setattr(btc_alerts, "load_events", lambda: [event])
    monkeypatch.setattr("engine.btc_impulse_radar_backtest.load_gate", lambda: _gate(d2="demoted"))
    # Isolate every other source and the backdrop so this is a real assembler test,
    # not a dependency on the repository's mutable data snapshot.
    monkeypatch.setattr(at, "_load_context", lambda: {"_state": at.READ_OK, "cross_asset": {}, "risk_backdrop": {}})
    monkeypatch.setattr(at, "_macro_raw", lambda *_: at._read("macro", at.READ_OK_ZERO, []))
    original_jsonl = at._jsonl_raw
    def only_vector(source, today, cutoff, tier_map):
        if source == "vector":
            return original_jsonl(source, today, cutoff, tier_map)
        return at._read(source, at.READ_OK_ZERO, [])
    monkeypatch.setattr(at, "_jsonl_raw", only_vector)

    payload = at.build_triage(today=date(2026, 9, 10))
    row = payload["alerts"][0]
    assert row["tier"] == "context"
    assert row["severity"] == "minor"
    assert row["action"] == "context"
    assert row["priority"] < 60
    assert row["validation"]["current_permitted"] is False
    assert row["validation"]["link"] == "signal_lab.html#signal-lab-btc-impulse-d2"
    assert row["original_claim"]["edge"] == "old issue-time claim"


def test_demoted_expired_impulse_validation_exposes_both_current_facts():
    from engine import signal_evidence

    passport = signal_evidence.impulse_passport(
        "d2", event_at="2026-09-03", event_precision="date",
        board_date="2026-09-10", source_asof="2026-09-03",
        gate=_gate(asof="2026-09-10", d2="demoted"),
    )
    validation = at._validation(
        "vector", "impulse_warn_down", "", "", {}, passport=passport,
    )
    assert validation["current_status"] == "demoted"
    assert validation["verdict"] == "no_edge"
    assert "demoted" in validation["note"].lower()
    assert "2026-09-06" in validation["note"]
    assert "closed" in validation["note"].lower()
    assert validation["current_permitted"] is False


def test_expired_leading_impulse_renders_as_observation_not_current_backtest_call():
    from engine import signal_evidence

    passport = signal_evidence.impulse_passport(
        "d2", event_at="2026-09-03", event_precision="date",
        board_date="2026-09-10", source_asof="2026-09-03",
        gate=_gate(asof="2026-09-10", d2="leading"),
    )
    validation = at._validation(
        "vector", "impulse_warn_down", "", "", {}, passport=passport,
    )
    assert passport["event_state"] == "expired"
    assert validation["current_status"] == "expired"
    assert validation["verdict"] == "display"
    assert "2026-09-06" in validation["note"]
    assert validation["current_permitted"] is False


def test_pressure_direction_uses_typed_identity_not_alert_volume():
    relief = _event(source="commodity", asset="oil", type_="risk_regime",
                    event_id="commodity:oil:risk_regime:2026-09-10T00:00:low_risk",
                    context={"risk_index": 6})
    bearish = dict(relief, id="commodity:oil:risk_regime:2026-09-10T00:00:high_risk")
    nondirectional = _event(source="macro", type_="transition_state_change",
                            event_id="macro-transition", context={})
    bounce = _event(type_="impulse_warn_up", event_id="impulse_warn_up:2026-09-10T00:00:u1",
                    context={"leg": "u1", "evidence_key": "u1"})
    bounce["claim_eligible"] = True
    bounce["direction"] = "up"
    directionless = _event(
        type_="impulse_warn_up", event_id="impulse_warn_up:2026-09-10T00:00:u1",
        context={"leg": "u1", "evidence_key": "u1"},
    )
    directionless["claim_eligible"] = True
    denied_down = _event()
    denied_down["claim_eligible"] = False

    assert at.pressure_effect(relief) == "relief"
    assert at.pressure_effect(bearish) == "risk_off"
    assert at.pressure_effect(nondirectional) == "nondirectional"
    assert at.pressure_effect(bounce) == "risk_on"
    assert at.pressure_effect(directionless) == "unknown"
    assert at.pressure_effect(denied_down) == "unknown"


def test_relief_bounce_nondirectional_and_unknown_do_not_inflate_bearish_board_score():
    base = {"tier": "act", "severity": "critical", "cluster": "stress",
            "cross_asset_tag": "neutral", "pressure_effect": "relief"}
    rows = [
        dict(base, pressure_effect="relief"),
        dict(base, pressure_effect="risk_on"),
        dict(base, pressure_effect="nondirectional"),
        dict(base, pressure_effect="unknown"),
    ]
    quiet = at._board_read([], {"cross_asset": {}, "risk_backdrop": {}})
    nonbearish = at._board_read(rows, {"cross_asset": {}, "risk_backdrop": {}})
    bearish = at._board_read(
        rows + [dict(base, pressure_effect="risk_off")],
        {"cross_asset": {}, "risk_backdrop": {}},
    )
    assert nonbearish["score"] == quiet["score"] == 0
    assert nonbearish["stance"] == "constructive"
    assert bearish["score"] > nonbearish["score"]


def test_partial_coverage_still_withholds_whole_tape_stance():
    row = {"tier": "act", "severity": "critical", "cluster": "stress",
           "cross_asset_tag": "confirm", "pressure_effect": "risk_off"}
    out = at._board_read(
        [row], {"cross_asset": {"verdict": "concentrated"}, "risk_backdrop": {}},
        {"state": "partial", "blocking": ["Bonds"], "blocking_zh": ["债券"],
         "unavailable": [], "unavailable_zh": [], "backdrop_missing": False},
    )
    assert out["stance"] == "partial"
    assert out["score"] is None


def test_predictive_impulse_push_requires_current_permission():
    denied = {"source": "vector", "type": "impulse_warn_down", "priority": 100,
              "validation": {"current_permitted": False}}
    allowed = {"source": "vector", "type": "impulse_warn_down", "priority": 60,
               "validation": {"current_permitted": True}}
    urgent_fact = {"source": "vector", "type": "flash_crash", "priority": 100,
                   "validation": {"current_permitted": False}}
    assert at._push_candidate(denied, 60) is False
    assert at._push_candidate(allowed, 60) is True
    assert at._push_candidate(urgent_fact, 60) is True


# SOL REVIEW ROUND 1 REGRESSIONS

def test_denied_legacy_impulse_moves_issue_time_authority_out_of_live_fields(monkeypatch):
    event = _event()
    stale = (
        "Forward de-risk window from a verified LEADING precursor cross. "
        "Holdout-validated; act early."
    )
    event["edge"] = stale
    event["edge_zh"] = "经验证的领先前兆；应尽早行动。"
    event["forward"] = "Reduce risk now."
    monkeypatch.setattr(btc_alerts, "load_events", lambda: [event])
    monkeypatch.setattr("engine.btc_impulse_radar_backtest.load_gate", lambda: _gate(d2="demoted"))
    monkeypatch.setattr(at, "_load_context", lambda: {
        "_state": at.READ_OK, "cross_asset": {}, "risk_backdrop": {},
    })
    monkeypatch.setattr(at, "_macro_raw", lambda *_: at._read("macro", at.READ_OK_ZERO, []))
    original_jsonl = at._jsonl_raw

    def only_vector(source, today, cutoff, tier_map):
        if source == "vector":
            return original_jsonl(source, today, cutoff, tier_map)
        return at._read(source, at.READ_OK_ZERO, [])

    monkeypatch.setattr(at, "_jsonl_raw", only_vector)
    row = at.build_triage(today=date(2026, 9, 10))["alerts"][0]

    assert row["original_claim"]["edge"] == stale
    assert row["original_claim"]["forward"] == "Reduce risk now."
    for phrase in ("verified LEADING", "Holdout-validated", "act early", "Reduce risk now"):
        assert phrase not in (row.get("edge") or "")
        assert phrase not in (row.get("forward") or "")
    assert row["tier"] == "context"
    assert row["claim_eligible"] is False


def test_unknown_only_complete_board_withholds_constructive_stance():
    row = {
        "tier": "act", "severity": "critical", "cluster": "stress",
        "cross_asset_tag": "neutral", "pressure_effect": "unknown",
    }
    out = at._board_read([row], {"cross_asset": {}, "risk_backdrop": {}})
    assert out["stance"] == "uncertain"
    assert out["score"] is None
    assert "constructive" not in out["one_liner"].lower()
    assert "unknown" in out["one_liner"].lower() or "direction" in out["one_liner"].lower()


def test_net_liquidity_direction_never_parses_free_form_detail():
    contracting = {
        "source": "macro", "type": "net_liquidity_roc_flip",
        "detail": "Net liquidity turned contracting and negative.",
    }
    expanding = {
        "source": "macro", "type": "net_liquidity_roc_flip",
        "detail": "Net liquidity turned expanding and positive.",
    }
    assert at.pressure_effect(contracting) == "unknown"
    assert at.pressure_effect(expanding) == "unknown"
    assert at.pressure_effect({**contracting, "pressure_effect": "risk_off"}) == "risk_off"


def test_rebuild_retains_unreproduced_persisted_impulse_as_history(monkeypatch):
    idx = pd.date_range("2026-09-01", periods=10, freq="D")
    sig = pd.DataFrame({"close": 60000.0}, index=idx)
    old = _event(
        event_id="impulse_warn_down:2026-09-01T00:00:d2",
        context={"leg": "d2", "evidence_key": "d2"},
    )
    old["ts"] = "2026-09-01T00:00:00"
    old["source_asof"] = "2026-09-10"
    old["edge"] = "verified LEADING; Holdout-validated; act early"
    monkeypatch.setattr(btc_alerts, "daily_state_events", lambda *_: [])
    monkeypatch.setattr(btc_alerts, "risk_extreme_events", lambda *_: [])
    monkeypatch.setattr(btc_alerts, "impulse_radar_events", lambda *_, **__: [])
    monkeypatch.setattr(btc_alerts, "leverage_derisk_events", lambda *_: [])
    monkeypatch.setattr(btc_alerts, "flash_events", lambda *_: [])
    monkeypatch.setattr(btc_alerts, "load_events", lambda: [old])
    monkeypatch.setattr(btc_alerts.store, "read", lambda *_: None)

    rows = btc_alerts.compute_all_events(
        sig, gate=_gate(d2="demoted"), board_date=date(2026, 9, 10),
    )
    row = next(r for r in rows if r["id"] == old["id"])
    assert row["original_claim"]["edge"] == old["edge"]
    assert row["tier"] == "context"
    assert row["claim_eligible"] is False
    assert "verified LEADING" not in row["edge"]



def test_triage_loads_the_shared_typed_gate_receipt(monkeypatch):
    from engine import signal_evidence

    receipt = {"read_state": "corrupt", "artifact": None, "path": "/typed-corrupt"}
    calls = {"n": 0}

    def load():
        calls["n"] += 1
        return receipt

    monkeypatch.setattr(signal_evidence, "load_btc_gate", load)
    assert at._load_impulse_gate_receipt() == receipt
    assert calls["n"] == 1
