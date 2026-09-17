"""Study-runner contract tests; market outcomes remain synthetic here."""
from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/research/terminal_tactical_r1_study.py"


def study():
    return importlib.import_module("scripts.research.terminal_tactical_r1_study")


def cfg():
    return json.loads((ROOT / "research/species/tti_r1/config.json").read_text())


def test_grid_identity_is_exactly_registered_84_cells():
    cells = study().grid_cells(cfg())
    assert len(cells) == len({json.dumps(x, sort_keys=True) for x in cells}) == 84
    assert {x["selector"] for x in cells} == set(cfg()["selectors"])


def test_registration_refuses_missing_cell(tmp_path):
    cells = study().grid_cells(cfg())
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("\n".join(json.dumps({"family":"entry_radar","config":x}) for x in cells[:-1]) + "\n")
    with pytest.raises(ValueError, match="registered_grid"):
        study().verify_registered_grid(ledger, cfg())


def test_registration_accepts_exact_superset_family(tmp_path):
    cells = study().grid_cells(cfg())
    rows = [{"family":"entry_radar","config":x} for x in cells]
    rows.append({"family":"entry_radar","config":{"other":"preexisting"}})
    ledger = tmp_path / "ledger.jsonl"; ledger.write_text("\n".join(map(json.dumps, rows)) + "\n")
    receipt = study().verify_registered_grid(ledger, cfg())
    assert receipt["study_cells"] == 84 and receipt["family_rows"] == 85


def test_segment_eligibility_distinguishes_ah_and_premarket():
    c = cfg(); f = {"observations":6,"span_minutes":120,"max_gap_minutes":60,
                    "last_end_minute":565,"return":.01,"efficiency":.4,
                    "above_bar_vwap_fraction":.8}
    assert study().segment_eligible(f, "pre", c)
    assert not study().segment_eligible({**f,"last_end_minute":560}, "pre", c)
    assert not study().segment_eligible(f, "ah", c)
    assert study().segment_eligible({**f,"last_end_minute":1170}, "ah", c)


def test_date_matched_delta_never_uses_unmatched_baseline():
    rows = pd.DataFrame([
        {"date":"2026-09-01","arm":"PERSISTENT","net_beta_residual":.02,"ticker":"A"},
        {"date":"2026-09-01","arm":"ALL_EARLY","net_beta_residual":.01,"ticker":"A"},
        {"date":"2026-09-02","arm":"PERSISTENT","net_beta_residual":.03,"ticker":"B"},
    ])
    got = study().date_matched_deltas(rows, "PERSISTENT", "ALL_EARLY")
    assert got.to_dict("records") == [{"date":"2026-09-01","delta":pytest.approx(.01)}]


def test_week_block_bootstrap_is_deterministic_and_prints_blocks():
    dated = pd.DataFrame({"date":["2026-08-03","2026-08-04","2026-08-10","2026-08-11"],
                          "delta":[.01,.02,-.01,.00]})
    a = study().week_block_interval(dated, repetitions=200, seed=7)
    b = study().week_block_interval(dated, repetitions=200, seed=7)
    assert a == b and a["blocks"] == 2 and a["repetitions"] == 200


def test_register_only_real_subprocess_reads_existing_ledger():
    result = subprocess.run([sys.executable, str(SCRIPT), "--register-only"], cwd=ROOT,
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["registered_grid"]["study_cells"] == 84
    assert receipt["study_id"] == "tti-r1-extended-session-v1"
