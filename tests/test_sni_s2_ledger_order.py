"""S2 ledger order (seat budget rule): the declared_budget row precedes every
outcome row of its family for P04/P05/P06, and no ledger output exists before
the budget row. Tests use tmp_path + synthetic ledgers only; the committed
evidence ledger (research/, never data/) is asserted as the artifact receipt.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "event_response"))

from engine.trial_ledger import TrialLedger, register_trials  # noqa: E402
from s2_seal import (FAMILY_BUDGET, PROTOCOLS,  # noqa: E402
                     ledger_family)

EVIDENCE_LEDGER = (ROOT / "research" / "single_name_intelligence" / "runs"
                   / "s2_event_response" / "trial_ledger.jsonl")


def _rows(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def test_declared_budget_precedes_every_outcome_row_committed_evidence() -> None:
    if not EVIDENCE_LEDGER.exists():  # pragma: no cover - evidence run pending
        pytest.skip("committed evidence ledger not present")
    rows = _rows(EVIDENCE_LEDGER)
    for pid in PROTOCOLS:
        fam = ledger_family(pid)
        fam_rows = [r for r in rows if r.get("family") == fam]
        assert fam_rows, f"no ledger rows for {fam}"
        first = fam_rows[0]
        assert first.get("kind") == "declared_budget", (
            f"{fam}: first family row is not the declared_budget row")
        assert first["n"] == FAMILY_BUDGET
        for r in fam_rows[1:]:
            assert "kind" not in r or r.get("kind") != "declared_budget"
            assert r.get("kind") is None  # every later row is an outcome/retirement trial


def test_no_ledger_file_before_budget_row_enters(tmp_path: Path) -> None:
    path = tmp_path / "trial_ledger.jsonl"
    ledger = TrialLedger(path=path)
    fam = ledger_family("P04")
    with register_trials(fam, budget=FAMILY_BUDGET,
                         reason="test floor", ledger=ledger):
        assert path.exists(), "budget row was not written on __enter__"
        rows = _rows(path)
        assert len(rows) == 1 and rows[0]["kind"] == "declared_budget"
        ledger.log_trial({"cfg": "x"}, family=fam, source="test")
        ledger.log_trial({"cfg": "y"}, family=fam, source="test")
    rows = _rows(path)
    assert rows[0]["kind"] == "declared_budget"
    outcome_idx = [i for i, r in enumerate(rows)
                   if r.get("kind") != "declared_budget"]
    assert outcome_idx and min(outcome_idx) > 0


def test_budget_is_a_floor_effective_n_never_below_it(tmp_path: Path) -> None:
    path = tmp_path / "trial_ledger.jsonl"
    ledger = TrialLedger(path=path)
    fam = ledger_family("P05")
    with register_trials(fam, budget=FAMILY_BUDGET,
                         reason="test floor", ledger=ledger):
        ledger.log_trial({"only": "one"}, family=fam, source="test")
    assert ledger.literal_n(family=fam) == 1
    assert ledger.declared_budget(family=fam) == FAMILY_BUDGET
    assert ledger.effective_n(family=fam) >= FAMILY_BUDGET


def test_committed_evidence_ledger_shape_and_budgets() -> None:
    if not EVIDENCE_LEDGER.exists():  # pragma: no cover
        pytest.skip("committed evidence ledger not present")
    rows = _rows(EVIDENCE_LEDGER)
    budgets = [r for r in rows if r.get("kind") == "declared_budget"]
    assert {b["family"] for b in budgets} == {ledger_family(p) for p in PROTOCOLS}
    for pid in PROTOCOLS:
        fam = ledger_family(pid)
        cfgs = [r for r in rows
                if r.get("family") == fam and r.get("kind") is None
                and r.get("source") == "sni_s2_historical_descriptive"]
        assert len(cfgs) == 12, f"{fam}: expected 12 itemized configs, got {len(cfgs)}"
