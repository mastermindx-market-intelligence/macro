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

# ---------------------------------------------------------------------------
# TTI R1-B v4 empirical study runner — admission and causal aggregation
# ---------------------------------------------------------------------------

R1B_SCRIPT = ROOT / "scripts/research/terminal_tactical_r1b_study.py"


def r1b_study():
    return importlib.import_module("scripts.research.terminal_tactical_r1b_study")


def test_r1b_v4_admission_accepts_exact_registered_repo_state():
    receipt = r1b_study().verify_admission()
    assert receipt["study_id"] == "tti-r1b-exhaustion-reclaim-v4"
    assert receipt["study_cells"] == 60
    assert receipt["registration_commit"] == "350c57e1c6aab6e064c022a483389c905d2b7ad0"
    assert receipt["market_outcomes_opened_before_registration"] is False


def test_r1b_v4_admission_refuses_config_mutation_before_any_input_loader(tmp_path):
    s = r1b_study()
    config = ROOT / "research/species/tti_r1b/config_v4.json"
    prereg = ROOT / "research/species/TTI_R1B_V4_PREREG.md"
    receipt = ROOT / "research/species/tti_r1b/REGISTRATION_RECEIPT_V4.json"
    ledger = ROOT / "data/trial_ledger.jsonl"
    changed = tmp_path / "config.json"
    doc = json.loads(config.read_text()); doc["local_touch_atr"] = 9.0
    changed.write_text(json.dumps(doc, sort_keys=True))
    touched = []
    with pytest.raises(ValueError, match="config_sha256"):
        s.verify_admission(config_path=changed, prereg_path=prereg,
                           receipt_path=receipt, ledger_path=ledger,
                           before_input=lambda: touched.append(True))
    assert touched == [], "admission failure must precede every market-input callback"


def test_r1b_v4_admission_refuses_missing_registered_cell(tmp_path):
    s=r1b_study()
    source=ROOT/"data/trial_ledger.jsonl"
    rows=[json.loads(x) for x in source.read_text().splitlines() if x.strip()]
    target=[i for i,row in enumerate(rows)
            if row.get("family")=="entry_radar" and isinstance(row.get("config"),dict)
            and row["config"].get("study_id")=="tti-r1b-exhaustion-reclaim-v4"]
    assert len(target)==60
    rows.pop(target[-1])
    ledger=tmp_path/"ledger.jsonl"; ledger.write_text("\n".join(map(json.dumps,rows))+"\n")
    with pytest.raises(ValueError, match="registered_grid"):
        s.verify_admission(ledger_path=ledger, enforce_receipt_ledger_sha=False)


def test_r1b_v4_verify_only_cli_reads_no_market_inputs():
    result=subprocess.run([sys.executable,str(R1B_SCRIPT),"--verify-only"],cwd=ROOT,
                          text=True,capture_output=True)
    assert result.returncode==0,result.stderr
    body=json.loads(result.stdout)
    assert body["study_id"]=="tti-r1b-exhaustion-reclaim-v4"
    assert body["study_cells"]==60
    assert body["market_data_read"] is False
    assert body["outcomes_computed"] is False


def test_r1b_v4_market_sign_requires_exact_positive_volume_prefix():
    s=r1b_study()
    start=pd.Timestamp("2026-09-17T13:30:00Z")
    idx=pd.date_range(start, periods=4, freq="5min")
    frame=pd.DataFrame({"open":[100,100,100,100],"high":[101]*4,"low":[99]*4,
                        "close":[100.1,100.2,100.2,100.3],"volume":[1,1,1,1]},index=idx)
    assert s.qqq_open_to_decision_sign(frame,start+pd.Timedelta(minutes=20))==1
    assert s.qqq_open_to_decision_sign(frame.drop(idx[1]),start+pd.Timedelta(minutes=20)) is None
    broken=frame.copy(); broken.loc[idx[2],"volume"]=0
    assert s.qqq_open_to_decision_sign(broken,start+pd.Timedelta(minutes=20)) is None
