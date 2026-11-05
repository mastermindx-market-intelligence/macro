"""test_sni_s1_ledger_order.py — the declared_budget row precedes every
log_trial row of its family, for all three families, and the runner writes no
output before the budget row (seat budget rule; D11)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/residual"))

import pytest  # noqa: E402

import run_s1  # noqa: E402
from engine.trial_ledger import TrialLedger, register_trials  # noqa: E402
from s1_synth import synth_frames, write_synthetic_repo  # noqa: E402


def _rows(path):
    import json
    return [json.loads(l) for l in path.read_text("utf-8").splitlines() if l.strip()]


def test_register_trials_writes_budget_row_before_anything_else(tmp_path):
    led = TrialLedger(path=tmp_path / "led.jsonl")
    with register_trials("fam.x", budget=3, reason="itemized grid", ledger=led):
        rows = _rows(tmp_path / "led.jsonl")
        assert len(rows) == 1 and rows[0]["kind"] == "declared_budget"
        assert rows[0]["n"] == 3
        led.log_trial(config={"a": 1}, family="fam.x")
        led.log_trial(config={"a": 2}, family="fam.x")
    rows = _rows(tmp_path / "led.jsonl")
    assert rows[0]["kind"] == "declared_budget"
    assert all(r.get("kind") != "declared_budget" for r in rows[1:])
    assert led.literal_n("fam.x") == 2
    assert led.effective_n("fam.x") == 3          # budget is a floor
    assert led.declared_budget("fam.x") == 3


def test_full_pipeline_budget_rows_precede_all_outcome_rows(tmp_path):
    frames = synth_frames(leak=False)
    store = write_synthetic_repo(tmp_path, frames)
    run_s1.DETECTED_AT = "2026-10-11T16:59:47-05:00"
    ledger_path = tmp_path / "trial_ledger.jsonl"
    out_dir = tmp_path / "out"
    run_s1.run_pipeline(store, tmp_path, out_dir, str(ledger_path))
    rows = _rows(ledger_path)
    for fam in ("sni.s1_residual.P01", "sni.s1_residual.P02", "sni.s1_residual.P03"):
        fam_rows = [r for r in rows if r["family"] == fam]
        assert fam_rows, fam
        assert fam_rows[0]["kind"] == "declared_budget", fam
        for r in fam_rows[1:]:
            assert r.get("kind") != "declared_budget"
            assert r.get("source") in ("sni_s1_historical_descriptive",
                                       "sni_s0_holdout_retirement")
    # itemized counts: P01 6 configs (+1 retirement only under a leak — none here)
    counts = {fam: sum(1 for r in rows if r["family"] == fam
                       and r.get("kind") != "declared_budget")
              for fam in ("sni.s1_residual.P01", "sni.s1_residual.P02",
                          "sni.s1_residual.P03")}
    assert counts["sni.s1_residual.P01"] == 6
    assert counts["sni.s1_residual.P02"] == 12
    assert counts["sni.s1_residual.P03"] == 21


def test_effective_n_floors_and_never_hides(tmp_path):
    led = TrialLedger(path=tmp_path / "led.jsonl")
    with register_trials("fam.y", budget=4, reason="floor check", ledger=led):
        for i in range(9):
            led.log_trial(config={"i": i}, family="fam.y")
    assert led.literal_n("fam.y") == 9
    assert led.effective_n("fam.y") == 9      # exceeding the budget raises it, visibly
    lane_like = {"literal_n": led.literal_n("fam.y"),
                 "effective_n": led.effective_n("fam.y"),
                 "declared_budget": led.declared_budget("fam.y")}
    assert lane_like["effective_n"] >= lane_like["declared_budget"]
