"""Observation-date bounds for contextual rotation receipts (no signal promotion)."""
from __future__ import annotations

import copy
import json

import numpy as np
import pandas as pd
import pytest

from engine import rotation_events as RE
from engine import rotation_flows as RF

ASOF = "2026-10-06"


def put(root, feed, name, values, dates):
    path = root / feed / f"{name}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(values, index=pd.to_datetime(dates)).to_parquet(path)
    return path


@pytest.mark.parametrize("reader,feed,column,value_key,date_key,values", [
    (RF.options_receipt, "options_flow", "net_premium_mn", "net_premium_mn",
     "options_asof", [7.25, 9.5, -999999.0]),
    (RF.gamma_receipt, "polygon_gex", "gamma_regime", "gamma_regime",
     "gex_asof", ["positive", "negative", "future-shock"]),
])
def test_future_observations_cannot_change_historical_receipt(
        tmp_path, reader, feed, column, value_key, date_key, values):
    put(tmp_path, feed, "summary_XLP", {column: values[:2]},
        ["2026-10-05", ASOF])
    before = reader("XLP", tmp_path, as_of=ASOF)
    put(tmp_path, feed, "summary_XLP", {column: values},
        ["2026-10-05", ASOF, "2026-10-07"])
    after = reader("XLP", tmp_path, as_of=ASOF)
    assert after == before
    assert after[value_key] == values[1]
    assert after[date_key] == ASOF
    assert after["status"] == "AS_OF"
    assert after["availability"] == {"status": "UNKNOWN", "available_at": None}


@pytest.mark.parametrize("reader,feed,column,value_key,date_key,value", [
    (RF.options_receipt, "options_flow", "net_premium_mn", "net_premium_mn",
     "options_asof", 4.25),
    (RF.gamma_receipt, "polygon_gex", "gamma_regime", "gamma_regime",
     "gex_asof", "negative"),
])
@pytest.mark.parametrize("bounded", [False, True])
def test_last_nonnull_value_keeps_its_own_date_and_stale_qualification(
        tmp_path, reader, feed, column, value_key, date_key, value, bounded):
    put(tmp_path, feed, "summary_XLP", {column: [value, None, None]},
        ["2026-10-02", "2026-10-05", ASOF])
    out = reader("XLP", tmp_path, **({"as_of": ASOF} if bounded else {}))
    assert out[value_key] == value
    assert out[date_key] == "2026-10-02"
    assert out["latest_row_as_of"] == ASOF
    assert out["status"] == "STALE"
    assert "2026-10-02" in out["note"]
    assert ASOF in out["note"]


@pytest.mark.parametrize("reader,feed,column,value_key,date_key,value", [
    (RF.options_receipt, "options_flow", "net_premium_mn", "net_premium_mn",
     "options_asof", 8.0),
    (RF.gamma_receipt, "polygon_gex", "gamma_regime", "gamma_regime",
     "gex_asof", "negative"),
])
def test_all_future_or_no_usable_values_are_explicitly_unavailable(
        tmp_path, reader, feed, column, value_key, date_key, value):
    put(tmp_path, feed, "summary_XLP", {column: [value]}, ["2026-10-07"])
    out = reader("XLP", tmp_path, as_of=ASOF)
    assert out[value_key] is None and out[date_key] is None
    assert out["latest_row_as_of"] is None
    assert out["status"] == "UNAVAILABLE"
    assert out["requested_as_of"] == ASOF
    assert out["note"]
    put(tmp_path, feed, "summary_XLP", {column: [None]}, [ASOF])
    out = reader("XLP", tmp_path, as_of=ASOF)
    assert out[value_key] is None and out[date_key] is None
    assert out["status"] == "UNAVAILABLE"


def test_etf_cutoff_precedes_diff_and_retains_last_five_valid_change_meaning(tmp_path):
    dates = ["2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01",
             "2026-10-02", "2026-10-05", ASOF]
    put(tmp_path, "flows", "XLP",
        {"so_mn": list(range(100, 107)), "nav": list(range(10, 17))}, dates)
    before = RF.etf_flow_receipt("XLP", tmp_path, as_of="2026-10-05")
    # The future shock is physically before old rows: slice and sort before diff.
    put(tmp_path, "flows", "XLP",
        {"so_mn": [1e8, *range(100, 107)],
         "nav": [1e6, *range(10, 17)]}, ["2026-10-07", *dates])
    after = RF.etf_flow_receipt("XLP", tmp_path, as_of="2026-10-05")
    assert after == before
    assert after["flow_5d_mn"] == 65.0
    assert after["flow_asof"] == "2026-10-05"
    assert after["window"] == {
        "basis": "last_five_nonnull_changes", "observations": 5,
        "first_value_as_of": "2026-09-29", "last_value_as_of": "2026-10-05",
    }


def test_etf_last_valid_change_is_not_relabelled_by_later_null_row(tmp_path):
    put(tmp_path, "flows", "XLP",
        {"so_mn": [100.0, 101.0, np.nan], "nav": [10.0, 20.0, 30.0]},
        ["2026-10-01", "2026-10-02", ASOF])
    out = RF.etf_flow_receipt("XLP", tmp_path, as_of=ASOF)
    assert out["flow_5d_mn"] == 20.0
    assert out["flow_asof"] == "2026-10-02"
    assert out["status"] == "STALE"
    assert out["window"]["observations"] == 1
    assert out["window"]["last_value_as_of"] == "2026-10-02"


def test_etf_all_future_is_unavailable(tmp_path):
    put(tmp_path, "flows", "XLP", {"so_mn": [100.0, 999.0], "nav": [10.0, 50.0]},
        ["2026-10-07", "2026-10-08"])
    out = RF.etf_flow_receipt("XLP", tmp_path, as_of=ASOF)
    assert out["flow_5d_mn"] is None and out["flow_asof"] is None
    assert out["status"] == "UNAVAILABLE"


def test_duplicate_retained_dates_fail_closed_but_future_duplicates_do_not_poison(tmp_path):
    put(tmp_path, "options_flow", "summary_XLP",
        {"net_premium_mn": [2.0, 3.0, 100.0, 200.0]},
        ["2026-10-05", ASOF, "2026-10-07", "2026-10-07"])
    out = RF.options_receipt("XLP", tmp_path, as_of=ASOF)
    assert out["net_premium_mn"] == 3.0
    put(tmp_path, "options_flow", "summary_XLP",
        {"net_premium_mn": [2.0, 3.0, 4.0]}, [ASOF, ASOF, "2026-10-07"])
    out = RF.options_receipt("XLP", tmp_path, as_of=ASOF)
    assert out["net_premium_mn"] is None
    assert out["status"] == "UNAVAILABLE"
    assert "duplicate" in out["note"].lower()


def test_live_default_still_reads_latest_usable_value_without_inventing_availability(tmp_path):
    put(tmp_path, "options_flow", "summary_XLP", {"net_premium_mn": [1.0, 9.123]},
        ["2026-10-05", ASOF])
    out = RF.options_receipt("XLP", tmp_path)
    assert out["net_premium_mn"] == 9.12
    assert out["options_asof"] == ASOF
    assert out["requested_as_of"] is None
    assert out["status"] == "AVAILABLE"
    assert out["availability"]["available_at"] is None
    json.dumps(out, allow_nan=False)


def test_combined_owner_threads_cutoff_and_exposes_each_observation_clock(tmp_path):
    put(tmp_path, "flows", "XLP", {"so_mn": [10, 11, 999], "nav": [2, 3, 100]},
        ["2026-10-01", "2026-10-02", "2026-10-07"])
    put(tmp_path, "options_flow", "summary_XLP", {"net_premium_mn": [7.0, -999.0]},
        [ASOF, "2026-10-07"])
    put(tmp_path, "polygon_gex", "summary_XLP", {"gamma_regime": ["negative", "future"]},
        ["2026-10-05", "2026-10-07"])
    out = RF.flow_receipt_for_series(
        {"key": "xlp", "kind": "etf", "ticker": "XLP"}, tmp_path, as_of=ASOF)
    assert (out["flow_asof"], out["options_asof"], out["gex_asof"]) == (
        "2026-10-02", ASOF, "2026-10-05")
    assert (out["flow_status"], out["options_status"], out["gex_status"]) == (
        "STALE", "AS_OF", "STALE")
    assert out["flow_5d_mn"] == 3.0
    assert out["net_premium_mn"] == 7.0 and out["gamma_regime"] == "negative"
    assert out["requested_as_of"] == ASOF
    assert out["availability"] == {"status": "UNKNOWN", "available_at": None}


def test_missing_feed_and_invalid_cutoff_are_unavailable(tmp_path):
    missing = RF.options_receipt("XLP", tmp_path, as_of=ASOF)
    assert missing["status"] == "UNAVAILABLE" and missing["note"]
    put(tmp_path, "options_flow", "summary_XLP", {"net_premium_mn": [9.0]}, [ASOF])
    invalid = RF.options_receipt("XLP", tmp_path, as_of="not-a-date")
    assert invalid["net_premium_mn"] is None
    assert invalid["status"] == "UNAVAILABLE"


def test_gamma_keeps_existing_non_session_guard(tmp_path):
    put(tmp_path, "polygon_gex", "summary_XLP", {"gamma_regime": ["negative", "weekend"]},
        ["2026-10-02", "2026-10-03"])
    out = RF.gamma_receipt("XLP", tmp_path, as_of="2026-10-03")
    assert out["gamma_regime"] == "negative"
    assert out["gex_asof"] == "2026-10-02"


def test_actual_nightly_caller_uses_benchmark_cutoff_not_old_event_clock(tmp_path, monkeypatch):
    from engine.oracle import ratio_lens as RL
    from tests.test_rotation_early_context import levels
    from tests.test_rotation_events_v2 import _make_minimal_sectors

    sectors = _make_minimal_sectors()
    for spec in sectors.values():
        for series in [spec["etf_close"], *spec["legs"].values()]:
            series.index = levels(end="2026-10-05", n=len(series)).index
    universe = {
        "bench": {"key": "spy"},
        "series": [{"key": "xlp", "kind": "etf", "ticker": "XLP",
                    "label_en": "Staples", "label_zh": "必需消费"}],
        "pairs": [], "velocity_series": ["xlp"], "contagion_pairs": [],
    }
    closes = {"spy": levels(n=400), "xlp": levels(n=400)}
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    monkeypatch.setattr(RL, "registered_short_horizon_context", lambda root, *, as_of: {
        "schema": "ratio_lens.short_horizons/v1", "as_of": as_of, "pairs": [],
        "reason_codes": ["TEST_REGISTRY_UNAVAILABLE"],
    })
    payloads = []
    for name, future in [("prefix", False), ("future", True)]:
        root = tmp_path / name
        dates = ["2026-10-05", ASOF] + (["2026-10-07"] if future else [])
        put(root, "options_flow", "summary_XLP",
            {"net_premium_mn": [1.0, 7.0] + ([-999999.0] if future else [])}, dates)
        payloads.append(RE.run_nightly(
            copy.deepcopy(sectors), root, generated_utc="2026-10-07T01:00:00Z",
            universe=universe, closes=closes,
        ))
    first, shocked = payloads
    assert first["as_of"] == "2026-10-05"
    flow = first["velocity_board"]["rows"][0]["flow"]
    assert flow["requested_as_of"] == ASOF
    assert flow["options_asof"] == ASOF and flow["net_premium_mn"] == 7.0
    assert shocked == first
    def state_bytes(root):
        return {p.name: p.read_bytes() for p in (root / "rotation_events").iterdir()
                if p.is_file()}
    assert state_bytes(tmp_path / "future") == state_bytes(tmp_path / "prefix")
