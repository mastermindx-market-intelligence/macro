"""test_sni_s1_info_leak.py — the D10 predicate: a step in the TUNE window
retires TUNE with a ledger row and a manifest row; no step does not; HK stays
VINTAGE_UNVERIFIABLE; TRAIN is never retired."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/residual"))

import run_s1  # noqa: E402
from engine.trial_ledger import TrialLedger  # noqa: E402
from s1_infoleak import detect, vintage_series  # noqa: E402
from s1_synth import synth_frames, write_synthetic_repo  # noqa: E402


def test_step_in_tune_window_produces_retirement_end_to_end(tmp_path):
    frames = synth_frames(leak=True)
    store = write_synthetic_repo(tmp_path, frames)
    run_s1.DETECTED_AT = "2026-10-11T16:59:47-05:00"
    ledger_path = tmp_path / "trial_ledger.jsonl"
    out = tmp_path / "out"
    res = run_s1.run_pipeline(store, tmp_path, out, str(ledger_path))
    lane = json_load(out / "LANE_MANIFEST.json")
    retired = [r for r in lane["retirements"]]
    assert [r["protocol_id"] for r in retired] == ["P01", "P03"]
    for r in retired:
        assert r["split"] == "TUNE"
        assert r["contamination_class"] == "information_leak"
        assert r["successor"] == f"{r['protocol_id']} v2 — not drafted; owner = seat/S0"
        assert r["detected_at"] == "2026-10-11T16:59:47-05:00"
    # the ledger carries the retirement rows, after the budget row
    rows = [json_load_line(l) for l in ledger_path.read_text().splitlines() if l.strip()]
    for fam in ("sni.s1_residual.P01", "sni.s1_residual.P03"):
        fam_rows = [r for r in rows if r["family"] == fam]
        assert fam_rows[0]["kind"] == "declared_budget"
        hit = [r for r in fam_rows if r.get("config", {}).get("event") == "holdout_retired"]
        assert len(hit) == 1 and hit[0]["source"] == "sni_s0_holdout_retirement"
        assert hit[0]["config"]["contamination_class"] == "information_leak"
    # TUNE still computed and printed, labelled retired
    blocks = json_load(out / "results" / "P01.json")["blocks"]
    tune_keys = [k for k in blocks if "|TUNE (" in k]
    assert tune_keys
    assert all("NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)"
               in blocks[k]["analysis_set"] for k in tune_keys)
    # TRAIN is never retired
    train_keys = [k for k in blocks if "|TRAIN|" in k]
    assert train_keys
    assert all("RETIRED" not in blocks[k]["analysis_set"] for k in train_keys)
    assert res["lane"]["a23_retirement_visible"] is True


def test_no_step_means_no_retirement(tmp_path):
    frames = synth_frames(leak=False)
    store = write_synthetic_repo(tmp_path, frames)
    run_s1.DETECTED_AT = "2026-10-11T16:59:47-05:00"
    out = tmp_path / "out"
    res = run_s1.run_pipeline(store, tmp_path, out, str(tmp_path / "trial_ledger.jsonl"))
    lane = json_load(out / "LANE_MANIFEST.json")
    assert lane["retirements"] == []
    assert res["leak"]["BABA"]["detection"] is None
    assert lane["families"]["P01"]["literal_n"] == 6


def test_hk_series_is_vintage_unverifiable_and_never_retired(tmp_path):
    frames = synth_frames(leak=True)
    store = write_synthetic_repo(tmp_path, frames)
    run_s1.DETECTED_AT = "2026-10-11T16:59:47-05:00"
    out = tmp_path / "out"
    res = run_s1.run_pipeline(store, tmp_path, out, str(tmp_path / "trial_ledger.jsonl"))
    assert res["leak"]["0700"]["state"] == "VINTAGE_UNVERIFIABLE"
    assert res["leak"]["9988"]["state"] == "VINTAGE_UNVERIFIABLE"
    lane = json_load(out / "LANE_MANIFEST.json")
    assert [r["protocol_id"] for r in lane["retirements"]] == ["P01", "P03"]
    assert "P02" not in [r["protocol_id"] for r in lane["retirements"]]
    assert lane["vintage_states"]["2800.HK"] == "VINTAGE_UNVERIFIABLE"


def test_predicate_details():
    dates = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 6, 13), date(2024, 6, 14)]
    close = [100.0, 101.0, 210.0, 210.525]
    close_price = [100.0, 101.0, 200.0, 200.5]
    steps, state = vintage_series(dates, close, close_price)
    assert state == "OK"
    # q = 1.0, 1.0, 1.05, ~1.0499 -> one step at 2024-06-13
    hit = detect(steps, state, date(2024, 1, 2), date(2024, 12, 31))
    assert hit is not None
    assert hit["first_offending_date"] == "2024-06-13"
    assert hit["count_of_steps_in_window"] == 1
    assert hit["contamination_class"] == "information_leak"
    # a step before the earliest TUNE anchor is not an offence
    assert detect(steps, state, date(2024, 7, 1), date(2024, 12, 31)) is None
    # HK: no raw column
    steps2, state2 = vintage_series(dates, close, [None] * 4)
    assert state2 == "VINTAGE_UNVERIFIABLE" and steps2 == []
    assert detect(steps2, state2, date(2024, 1, 2), date(2024, 12, 31)) is None


def json_load(p):
    import json
    return json.loads(p.read_text("utf-8"))


def json_load_line(line):
    import json
    return json.loads(line)
