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


def _r1b_admission_paths():
    return {
        "config_path": ROOT / "research/species/tti_r1b/config_v4.json",
        "prereg_path": ROOT / "research/species/TTI_R1B_V4_PREREG.md",
        "receipt_path": ROOT / "research/species/tti_r1b/REGISTRATION_RECEIPT_V4.json",
    }


def _r1b_ledger_lines_bytes():
    return [ln for ln in (ROOT / "data/trial_ledger.jsonl").read_bytes().split(b"\n") if ln.strip()]


def _r1b_write_ledger(tmp_path, lines: list[bytes]) -> Path:
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_bytes(b"\n".join(lines) + b"\n")
    return ledger


def _r1b_registered_line_indices(s, lines: list[bytes]) -> list[int]:
    registered = set(s.registered_rows(b"\n".join(lines) + b"\n"))
    return [i for i, ln in enumerate(lines) if ln in registered]


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
        s.verify_admission(ledger_path=ledger, **_r1b_admission_paths())


def test_r1b_admission_passes_branch_ledger_as_is(tmp_path):
    s = r1b_study()
    ledger = _r1b_write_ledger(tmp_path, _r1b_ledger_lines_bytes())
    receipt = s.verify_admission(ledger_path=ledger, **_r1b_admission_paths())
    assert receipt["study_cells"] == 60
    assert receipt["registered_rows_sha256"] == (
        "8fc5a844886cfa2d69ec25f38fd6948b4a4556e01829bea76338e94570def281"
    )


def test_r1b_admission_passes_when_other_rows_surround_and_interleave(tmp_path):
    s = r1b_study()
    lines = _r1b_ledger_lines_bytes()
    idx = _r1b_registered_line_indices(s, lines)
    assert len(idx) == 60
    foreign = json.dumps({"family": "cortex", "config": {"study_id": "someone-else"}}).encode()
    lines = lines[:idx[0]] + [foreign] + lines[idx[0]:]
    idx = _r1b_registered_line_indices(s, lines)
    mid = len(idx) // 2
    lines = lines[: idx[mid] + 1] + [foreign] + lines[idx[mid] + 1 :]
    lines = lines + [foreign]
    ledger = _r1b_write_ledger(tmp_path, lines)
    receipt = s.verify_admission(ledger_path=ledger, **_r1b_admission_paths())
    assert receipt["registered_rows_sha256"] == (
        "8fc5a844886cfa2d69ec25f38fd6948b4a4556e01829bea76338e94570def281"
    )
    assert receipt["ledger_lines"] == len(_r1b_ledger_lines_bytes()) + 3


@pytest.mark.parametrize(
    "mutator,match",
    [
        ("remove_one", "registered_grid_row_count_mismatch:59/60"),
        ("append_dup", "registered_grid_row_count_mismatch:61/60"),
        ("append_all", "registered_grid_row_count_mismatch:120/60"),
    ],
)
def test_r1b_admission_refuses_wrong_row_counts(tmp_path, mutator, match):
    s = r1b_study()
    lines = list(_r1b_ledger_lines_bytes())
    idx = _r1b_registered_line_indices(s, lines)
    registered = [lines[i] for i in idx]
    if mutator == "remove_one":
        lines.pop(idx[-1])
    elif mutator == "append_dup":
        lines.append(registered[0])
    else:
        lines.extend(registered)
    ledger = _r1b_write_ledger(tmp_path, lines)
    touched = []
    with pytest.raises(ValueError, match=match):
        s.verify_admission(
            ledger_path=ledger,
            before_input=lambda: touched.append(True),
            **_r1b_admission_paths(),
        )
    assert touched == []


def test_r1b_admission_refuses_a_one_character_change_in_any_registered_row(tmp_path):
    s = r1b_study()
    lines = _r1b_ledger_lines_bytes()
    idx = _r1b_registered_line_indices(s, lines)
    assert len(idx) == 60
    for pos in idx:
        trial = list(lines)
        row = json.loads(trial[pos])
        ts = row["ts"]
        row["ts"] = ts[:-1] + ("0" if ts[-1] != "0" else "1")
        trial[pos] = json.dumps(row, separators=(",", ":"), sort_keys=True).encode()
        ledger = _r1b_write_ledger(tmp_path, trial)
        with pytest.raises(ValueError, match="registered_rows_sha256_mismatch"):
            s.verify_admission(ledger_path=ledger, **_r1b_admission_paths())


def test_r1b_admission_refuses_reordered_registered_rows(tmp_path):
    s = r1b_study()
    lines = list(_r1b_ledger_lines_bytes())
    idx = _r1b_registered_line_indices(s, lines)
    i, j = idx[0], idx[1]
    lines[i], lines[j] = lines[j], lines[i]
    ledger = _r1b_write_ledger(tmp_path, lines)
    touched = []
    with pytest.raises(ValueError, match="registered_rows_sha256_mismatch"):
        s.verify_admission(
            ledger_path=ledger,
            before_input=lambda: touched.append(True),
            **_r1b_admission_paths(),
        )
    assert touched == []


def test_r1b_admission_refuses_prereg_and_receipt_edited_together(tmp_path):
    import hashlib

    s = r1b_study()
    paths = _r1b_admission_paths()
    prereg = paths["prereg_path"].read_bytes()
    changed_prereg = tmp_path / "prereg.md"
    changed_prereg.write_bytes(prereg[:-1] + (b" " if prereg[-1:] != b" " else b"x"))
    new_sha = hashlib.sha256(changed_prereg.read_bytes()).hexdigest()
    receipt_doc = json.loads(paths["receipt_path"].read_text())
    receipt_doc["prereg_sha256"] = new_sha
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps(receipt_doc, sort_keys=True))
    ledger = _r1b_write_ledger(tmp_path, _r1b_ledger_lines_bytes())
    touched = []
    with pytest.raises(ValueError, match="prereg_sha256_mismatch"):
        s.verify_admission(
            prereg_path=changed_prereg,
            receipt_path=receipt,
            ledger_path=ledger,
            before_input=lambda: touched.append(True),
            config_path=paths["config_path"],
        )
    assert touched == []


def test_r1b_admission_refuses_receipt_grid_edit(tmp_path):
    s = r1b_study()
    paths = _r1b_admission_paths()
    receipt_doc = json.loads(paths["receipt_path"].read_text())
    receipt_doc["grid_sha256"] = "0" * 64
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps(receipt_doc, sort_keys=True))
    ledger = _r1b_write_ledger(tmp_path, _r1b_ledger_lines_bytes())
    touched = []
    with pytest.raises(ValueError, match="grid_sha256_mismatch"):
        s.verify_admission(
            receipt_path=receipt,
            ledger_path=ledger,
            before_input=lambda: touched.append(True),
            **{k: v for k, v in paths.items() if k != "receipt_path"},
        )
    assert touched == []


def test_r1b_admission_refuses_unparseable_row_naming_the_study(tmp_path):
    s = r1b_study()
    lines = list(_r1b_ledger_lines_bytes())
    lines.append(
        b'{"family":"entry_radar","config":{"study_id":"tti-r1b-exhaustion-reclaim-v4"'
    )
    ledger = _r1b_write_ledger(tmp_path, lines)
    touched = []
    with pytest.raises(ValueError, match="registered_row_unparseable"):
        s.verify_admission(
            ledger_path=ledger,
            before_input=lambda: touched.append(True),
            **_r1b_admission_paths(),
        )
    assert touched == []


def test_r1b_admission_ignores_a_foreign_row_that_only_mentions_the_study(tmp_path):
    s = r1b_study()
    lines = list(_r1b_ledger_lines_bytes())
    lines.append(
        json.dumps(
            {
                "family": "entry_radar",
                "config": {"study_id": "a-later-study"},
                "note": "follows tti-r1b-exhaustion-reclaim-v4",
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
    )
    ledger = _r1b_write_ledger(tmp_path, lines)
    receipt = s.verify_admission(ledger_path=ledger, **_r1b_admission_paths())
    assert receipt["study_cells"] == 60


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


def _r1b_synthetic_daily_and_session():
    from datetime import date
    from engine.session_digest import session_window_et
    from lib.nyse_calendar import session_n_back
    day=date(2026,9,17)
    prior_days=[session_n_back(day,n) for n in range(70,0,-1)]
    q=100.; stock=100.; qs=[]; ss=[]
    for i,_d in enumerate(prior_days):
        r=(.0004+(i%7)*.0001)*(1 if i%2==0 else -1)
        q*=1+r; stock*=1+2*r; qs.append(q); ss.append(stock)
    sd=pd.DataFrame({'high':[x+1 for x in ss],'low':[x-1 for x in ss],'close':ss},
                    index=pd.DatetimeIndex(prior_days))
    qd=pd.DataFrame({'close':qs},index=pd.DatetimeIndex(prior_days))
    start,close=session_window_et(day); idx=pd.date_range(start,close-pd.Timedelta(minutes=5),freq='5min')
    base=[[100,100.2,99,99.4,100],[99.4,99.5,98.8,99,100],[99,99.1,98.6,98.98,100],
          [98.98,99.1,98.55,98.95,100],[98.95,99.2,98.8,99.1,100],[99.1,99.5,99,99.4,100]]
    rows=base+[[99.4,99.6,99.2,99.45,100] for _ in range(len(idx)-len(base))]
    sf=pd.DataFrame(rows,index=idx,columns=['open','high','low','close','volume'],dtype=float)
    qrows=[]
    for i in range(len(idx)):
        px=100.+i*.01; qrows.append([px,px+.05,px-.05,px+.01,100.])
    qf=pd.DataFrame(qrows,index=idx,columns=sf.columns,dtype=float)
    return day,sd,qd,sf,qf


def test_r1b_v4_construct_one_day_decorates_candidate_time_market_context_only():
    s=r1b_study(); day,sd,qd,sf,qf=_r1b_synthetic_daily_and_session()
    got=s.construct_one_day('AMD',day,sf,qf,sd,qd)
    assert got['normalization']['availability']=='AVAILABLE'
    assert got['events']
    selected=next(x for x in got['events'] if x['selector']=='EXHAUSTION_RECLAIM')
    assert selected['qqq_open_to_decision_sign']==1
    assert selected['beta']==pytest.approx(got['normalization']['beta'])
    assert selected['market_outcomes_computed'] is False
    assert got['controls'] and all(x['future_family_labels_used'] is False for x in got['controls'])
    assert all(x['qqq_open_to_decision_sign']==1 for x in got['controls'])


def test_r1b_v4_measure_event_grid_preserves_all_12_cells_and_censors_missing_path():
    s=r1b_study(); day,sd,qd,sf,qf=_r1b_synthetic_daily_and_session()
    built=s.construct_one_day('AMD',day,sf,qf,sd,qd)
    event=next(x for x in built['events'] if x['selector']=='EXHAUSTION_RECLAIM')
    rows=s.measure_event_grid(event,sf,qf,session=day)
    assert len(rows)==12
    assert {(x['horizon'],x['cost_bps']) for x in rows}=={
        (h,c) for h in ('30m','60m','120m','close') for c in (10,25,50)}
    broken=sf.drop(pd.Timestamp(event['entry_reference_at'])+pd.Timedelta(minutes=10))
    censored=s.measure_event_grid(event,broken,qf,session=day)
    short=[x for x in censored if x['horizon']=='30m']
    assert len(short)==3 and all(x['status']=='censored' for x in short)
    assert all(x['selector']=='EXHAUSTION_RECLAIM' for x in short)
