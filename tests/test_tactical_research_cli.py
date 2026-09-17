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

class _EveryDayCalendar:
    def window(self, day):
        return (570, 580)


def _two_bar_day(day, base, close):
    return [
        {"event_start_utc":base,"display_epoch":base,"date":day,"minute":570,"o":100.,"h":101.,"l":99.,"c":100.,"v":10.},
        {"event_start_utc":base+300,"display_epoch":base+300,"date":day,"minute":575,"o":100.,"h":max(101.,close),"l":99.,"c":close,"v":10.},
    ]


def test_daily_return_never_bridges_a_missing_scheduled_session():
    s=study(); days=["2026-09-01","2026-09-02","2026-09-03"]
    frame=pd.DataFrame(_two_bar_day(days[0],1_000_000,100.) + _two_bar_day(days[2],1_200_000,110.)).set_index("event_start_utc")
    daily=s._daily_tables({"A":frame},days,_EveryDayCalendar())["A"]
    assert list(daily.index)==days
    assert pd.isna(daily.at[days[1],"c"])
    assert pd.isna(daily.at[days[2],"return"]), "a missing scheduled day must not become a two-day return labeled one-day"


def test_segment_evidence_end_uses_last_positive_volume_bar():
    s=study(); day="2026-09-01"
    frame=pd.DataFrame([
        {"event_start_utc":1_000_000,"display_epoch":1,"date":day,"minute":240,"o":100.,"h":101.,"l":99.,"c":100.,"v":1.},
        {"event_start_utc":1_000_300,"display_epoch":2,"date":day,"minute":245,"o":100.,"h":101.,"l":99.,"c":100.,"v":1.},
        {"event_start_utc":1_000_600,"display_epoch":3,"date":day,"minute":250,"o":100.,"h":101.,"l":99.,"c":100.,"v":0.},
    ]).set_index("event_start_utc")
    _,features=s._segment(frame,day,240,255)
    assert features["last_end_minute"]==250, "zero-volume rows remain visible but cannot extend price-evidence recency"


def test_invalid_segment_is_local_unavailable_not_global_failure():
    s=study(); day="2026-09-01"
    frame=pd.DataFrame([
        {"event_start_utc":1_000_000,"display_epoch":1,"date":day,"minute":240,"o":100.,"h":101.,"l":99.,"c":float("nan"),"v":1.},
    ]).set_index("event_start_utc")
    _,features=s._segment(frame,day,240,245)
    assert features["invalid"] is True and features["observations"]==0


def test_invalid_regular_session_is_missing_for_that_day_only():
    s=study(); day="2026-09-01"
    rows=_two_bar_day(day,1_000_000,100.); rows[1]["c"]=float("nan")
    frame=pd.DataFrame(rows).set_index("event_start_utc")
    assert s._regular(frame,day,_EveryDayCalendar()) is None
