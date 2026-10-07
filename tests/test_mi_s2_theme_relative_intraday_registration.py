"""S2 theme-relative intraday prospective registration (outcome-blind)."""

from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import date
from pathlib import Path

import pytest

from engine.prophet_entry_policy import (
    SESSION_POLICY_ERA,
    EntryPolicyContractError,
    _EARLY_CLOSE_DATES,
    _SUPPORTED_SESSION_YEARS,
    evaluate_session_eligibility,
)
from engine.prophet_strategy_definition import build_early_leadership_sector_rotation_definition
from engine.trial_ledger import TrialLedger
from lib import nyse_calendar
from scripts.research.freeze_mi_s2_theme_relative_intraday_registration import (
    AUTHORITY,
    FAMILY,
    FIRST_ELIGIBLE_DECISION_AT,
    OWNER_ACCEPTANCE_AT,
    build_registration,
    freeze,
    trial_config,
)

ROOT = Path(__file__).resolve().parents[1]
FREEZE_SCRIPT = ROOT / "scripts/research/freeze_mi_s2_theme_relative_intraday_registration.py"


def test_s2_registration_formation_boundary_after_owner_acceptance():
    reg = build_registration(base_pin="0" * 40, frozen_at="2026-10-07T12:00:00Z")
    assert reg["formation_boundary"]["owner_acceptance_at"] == OWNER_ACCEPTANCE_AT
    assert reg["formation_boundary"]["first_eligible_decision_at"] == FIRST_ELIGIBLE_DECISION_AT
    assert FIRST_ELIGIBLE_DECISION_AT > OWNER_ACCEPTANCE_AT


def test_s2_registration_canonical_hash_is_stable():
    reg_a = build_registration(base_pin="abc", frozen_at="2026-10-07T12:00:00Z")
    reg_b = build_registration(base_pin="abc", frozen_at="2026-10-07T12:00:00Z")
    assert reg_a["registration_sha256"] == reg_b["registration_sha256"]
    assert reg_a["frozen_parameters_sha256"] == reg_b["frozen_parameters_sha256"]


def test_s2_trial_ledger_logs_one_distinct_trial_idempotently(tmp_path):
    ledger_path = tmp_path / "trial_ledger.jsonl"
    reg = build_registration(base_pin="def", frozen_at="2026-10-07T12:00:00Z")
    ledger = TrialLedger(path=ledger_path, family=FAMILY)
    cfg = trial_config(reg)
    assert ledger.log_trial(cfg, info_cutoff="2026-10-07", source="MI-S2-TRI-HOURLY-RTH") is True
    assert ledger.log_trial(cfg, info_cutoff="2026-10-07", source="MI-S2-TRI-HOURLY-RTH") is False
    assert ledger.effective_n(FAMILY) == 1
    lines = [ln for ln in ledger_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    trial_rows = [json.loads(ln) for ln in lines if json.loads(ln).get("family") == FAMILY]
    assert len(trial_rows) == 1


def test_s2_registration_authority_remains_false():
    reg = build_registration(base_pin="ghi", frozen_at="2026-10-07T12:00:00Z")
    assert reg["authority"] == AUTHORITY
    assert all(value is False for key, value in reg["authority"].items() if key.startswith("can_"))


def test_s2_session_policy_material_lists_2026_2027_and_early_closes():
    reg = build_registration(base_pin="jkl", frozen_at="2026-10-07T12:00:00Z")
    mat = reg["frozen_parameters"]["session_policy_binding"]
    assert mat["supported_session_years"] == [2026, 2027]
    assert mat["session_policy_era"] == SESSION_POLICY_ERA
    assert set(mat["early_close_dates"]) == {d.isoformat() for d in _EARLY_CLOSE_DATES}
    assert _SUPPORTED_SESSION_YEARS == frozenset({2026, 2027})


def _session_policy(decision_at: str, market_session: str):
    return evaluate_session_eligibility(
        strategy_definition=build_early_leadership_sector_rotation_definition(),
        decision_at=decision_at,
        market_session=market_session,
    )


def test_s2_entry_policy_2027_regular_session_rth():
    out = _session_policy("2027-01-04T15:00:00Z", "2027-01-04")
    assert out["verdict"] == "PASS"
    assert out["session_close"].endswith("16:00:00-05:00")
    assert out["supported_session_years"] == [2026, 2027]
    assert out["session_policy_era"] == SESSION_POLICY_ERA
    assert all(value is False for value in out["authority"].values())


def test_s2_entry_policy_2027_early_close_and_holidays():
    early = _session_policy("2027-11-26T17:59:59Z", "2027-11-26")
    assert early["verdict"] == "PASS"
    assert early["session_close"].endswith("13:00:00-05:00")

    after_early = _session_policy("2027-11-26T18:00:00Z", "2027-11-26")
    assert after_early["verdict"] == "FAIL"
    assert after_early["session_phase"] == "AFTER_HOURS"

    thanksgiving = _session_policy("2027-11-25T15:00:00Z", "2027-11-25")
    assert (thanksgiving["verdict"], thanksgiving["session_phase"]) == (
        "FAIL",
        "NON_SESSION",
    )

    christmas_observed = _session_policy("2027-12-24T15:00:00Z", "2027-12-24")
    assert (christmas_observed["verdict"], christmas_observed["session_phase"]) == (
        "FAIL",
        "NON_SESSION",
    )


def test_s2_entry_policy_2028_fail_closed_unsupported():
    with pytest.raises(EntryPolicyContractError, match="outside NYSE_RTH_2026_2027"):
        _session_policy("2028-01-03T15:00:00Z", "2028-01-03")


def test_s2_nyse_calendar_holidays_for_2027_registration():
    assert nyse_calendar.is_session(date(2027, 11, 25)) is False
    assert nyse_calendar.is_session(date(2027, 12, 24)) is False
    assert nyse_calendar.is_session(date(2027, 11, 26)) is True


def test_s2_freeze_script_has_no_outcome_execution_paths():
    text = FREEZE_SCRIPT.read_text(encoding="utf-8")
    assert "build_polygon_intraday" not in text
    assert "data/intraday" not in text
    assert "parquet" not in text
    assert "import pandas" not in text
    for token in ("can_rank: True", "can_gate: True", "can_execute: True"):
        assert token not in text


def test_s2_freeze_writes_artifacts(tmp_path, monkeypatch):
    out_json = tmp_path / "reg.json"
    out_md = tmp_path / "reg.md"
    monkeypatch.setattr(
        "scripts.research.freeze_mi_s2_theme_relative_intraday_registration.OUT_JSON",
        out_json,
    )
    monkeypatch.setattr(
        "scripts.research.freeze_mi_s2_theme_relative_intraday_registration.OUT_MD",
        out_md,
    )
    freeze(register_trial=False)
    assert out_json.exists()
    assert out_md.exists()
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["schema"] == "mastermind.mi_s2_prospective_registration.v1"
    assert "OUTCOME-BLIND" in out_md.read_text(encoding="utf-8")
