"""C19 WP24 DQ3 — consumers say WHY a short-data field is empty.

A missing FINRA file, an unreadable one and an empty one used to collapse into
the same None, and FINRA's 999.99 days-to-cover sentinel (average daily volume
~0) was rendered as a real 999.99. The short-volume reader now returns a named
state, the short-interest collector flags the censored sentinel, and the stock
page's positioning block nulls a censored days-to-cover and marks why.

Healthy inputs must produce byte-identical output: the new keys appear only on
the censored and parse-error paths.

Every test is hermetic: config.data_dir points at tmp_path and the network
entry points are monkeypatched, so nothing touches the real data/ tree.
"""
from __future__ import annotations

import logging

import pandas as pd
import pytest

from collectors import finra
from engine import short_volume as sv
from engine import stock_fundamentals as sf
from lib import config


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    return tmp_path


def _panel(n: int = 3) -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.date_range("2026-10-01", periods=n).strftime("%Y-%m-%d"),
        "ticker": ["AAA"] * n,
        "short_vol": [100.0] * n,
        "total_vol": [400.0] * n,
    })


# ---------------------------------------------------------------------------
# engine/short_volume.py — panel_state / load_panel
# ---------------------------------------------------------------------------

def test_panel_state_missing_file_is_unavailable(tmp_path):
    assert sv.panel_state(tmp_path / "nope.parquet") == (None, sv.UNAVAILABLE)
    assert sv.load_panel(tmp_path / "nope.parquet") is None


def test_panel_state_corrupt_file_is_parse_error(tmp_path, caplog):
    p = tmp_path / "panel.parquet"
    p.write_bytes(b"not a parquet file")
    with caplog.at_level(logging.WARNING, logger="engine.short_volume"):
        df, state = sv.panel_state(p)
    assert (df, state) == (None, sv.PARSE_ERROR)
    assert "unreadable" in caplog.text
    assert sv.load_panel(p) is None


def test_panel_state_missing_columns_is_parse_error(tmp_path, caplog):
    p = tmp_path / "panel.parquet"
    _panel().drop(columns=["total_vol"]).to_parquet(p)
    with caplog.at_level(logging.WARNING, logger="engine.short_volume"):
        df, state = sv.panel_state(p)
    assert (df, state) == (None, sv.PARSE_ERROR)
    assert "total_vol" in caplog.text


def test_panel_state_empty_panel_is_no_observation(tmp_path):
    p = tmp_path / "panel.parquet"
    _panel().iloc[0:0].to_parquet(p)
    assert sv.panel_state(p) == (None, sv.NO_OBSERVATION)
    assert sv.load_panel(p) is None


def test_panel_state_valid_panel_is_observed_and_load_panel_agrees(tmp_path):
    p = tmp_path / "panel.parquet"
    _panel().to_parquet(p)
    df, state = sv.panel_state(p)
    assert state == sv.OBSERVED
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    pd.testing.assert_frame_equal(sv.load_panel(p), df)


def test_panel_state_default_path_reads_data_dir(data_root):
    assert sv.panel_state() == (None, sv.UNAVAILABLE)
    (data_root / "finra_short_volume").mkdir()
    _panel().to_parquet(data_root / "finra_short_volume" / "panel.parquet")
    assert sv.panel_state()[1] == sv.OBSERVED


# ---------------------------------------------------------------------------
# engine/short_volume.py — ticker_state over one signal_map() entry
# ---------------------------------------------------------------------------

_FULL = {"short_ratio": 0.25, "ratio_recent": 0.25, "ratio_baseline": 0.2,
         "trend_pp": 5.0, "ratio_z": 1.1, "n_days": 40, "asof": "2026-10-09"}


@pytest.mark.parametrize("sig, state", [
    (None, sv.NO_OBSERVATION),
    ({}, sv.NO_OBSERVATION),
    ({**_FULL, "n_days": 19}, sv.PARTIAL),
    ({**_FULL, "ratio_z": None}, sv.PARTIAL),
    ({**_FULL, "ratio_recent": 0.0}, sv.OBSERVED_ZERO),
    (_FULL, sv.OBSERVED),
], ids=["none", "empty", "short_history", "no_z", "zero_recent", "full"])
def test_ticker_state(sig, state):
    assert sv.ticker_state(sig) == state


def test_ticker_state_honours_baseline():
    assert sv.ticker_state({**_FULL, "n_days": 10}, baseline=10) == sv.OBSERVED


# ---------------------------------------------------------------------------
# collectors/finra.py — dtc_capped on the snapshot, never in the history
# ---------------------------------------------------------------------------

def _si_snapshot(settlement: str) -> pd.DataFrame:
    df = pd.DataFrame({
        "ticker": ["AAA", "ZZZ"],
        "short_shares": [1000.0, 50.0],
        "prev_short_shares": [900.0, 50.0],
        "avg_daily_vol": [200.0, 0.0],
        "days_to_cover": [5.0, 999.99],
        "si_change_pct": [11.1, 0.0],
    })
    df["settlement_date"] = settlement
    return df.set_index("ticker")


def test_short_interest_flags_censored_dtc_and_keeps_history_schema(data_root, monkeypatch):
    monkeypatch.setattr(finra, "_latest_settlement", lambda: "2026-09-30")
    monkeypatch.setattr(finra, "_snapshot", _si_snapshot)
    monkeypatch.setattr(finra, "_universe_tickers", lambda: set())
    finra.fetch_short_interest(force=True)

    snap = pd.read_parquet(data_root / "finra" / "short_interest.parquet")
    assert bool(snap.loc["ZZZ", "dtc_capped"]) is True
    assert bool(snap.loc["AAA", "dtc_capped"]) is False
    assert snap.loc["ZZZ", "days_to_cover"] == 999.99, "the raw value is kept, only flagged"

    hist = pd.read_parquet(data_root / "finra" / "short_interest_history.parquet")
    assert "dtc_capped" not in hist.columns
    assert "asof" not in hist.columns
    assert "capture_date" in hist.columns


# ---------------------------------------------------------------------------
# engine/stock_fundamentals.py — _load_short_state
# ---------------------------------------------------------------------------

def test_load_short_state_missing_is_unavailable(data_root):
    assert sf._load_short_state() == (None, sv.UNAVAILABLE)


def test_load_short_state_corrupt_is_parse_error(data_root, caplog):
    (data_root / "finra").mkdir()
    (data_root / "finra" / "short_interest.parquet").write_bytes(b"garbage")
    with caplog.at_level(logging.WARNING, logger="engine.stock_fundamentals"):
        assert sf._load_short_state() == (None, sv.PARSE_ERROR)
    assert "unreadable" in caplog.text


def test_load_short_state_empty_is_no_observation(data_root):
    (data_root / "finra").mkdir()
    _si_snapshot("2026-09-30").iloc[0:0].to_parquet(data_root / "finra" / "short_interest.parquet")
    assert sf._load_short_state() == (None, sv.NO_OBSERVATION)


def test_load_short_state_valid_is_observed(data_root):
    (data_root / "finra").mkdir()
    _si_snapshot("2026-09-30").to_parquet(data_root / "finra" / "short_interest.parquet")
    df, state = sf._load_short_state()
    assert state == sv.OBSERVED
    assert set(df.index) == {"AAA", "ZZZ"}


# ---------------------------------------------------------------------------
# engine/stock_fundamentals.py — _positioning
# ---------------------------------------------------------------------------

_F = {"shares": 10000.0}


def test_positioning_healthy_row_is_unchanged():
    short = _si_snapshot("2026-09-30")
    short["dtc_capped"] = short["days_to_cover"].ge(finra.DTC_SENTINEL)
    block = sf._positioning("AAA", _F, short, None, None, short_state=sv.OBSERVED)
    assert block == {"short": {"pct_float": 10.0, "days_to_cover": 5.0,
                               "si_change_pct": 11.1, "settlement": "2026-09-30"}}


@pytest.mark.parametrize("flagged", [True, False], ids=["collector_flag", "sentinel_only"])
def test_positioning_censored_dtc_is_null_with_state(flagged):
    short = _si_snapshot("2026-09-30")
    if flagged:
        short["dtc_capped"] = short["days_to_cover"].ge(finra.DTC_SENTINEL)
    block = sf._positioning("ZZZ", _F, short, None, None)
    assert block["short"]["days_to_cover"] is None
    assert block["short"]["dtc_state"] == sv.CENSORED_LOWER_BOUND
    assert block["short"]["pct_float"] == 0.5


def test_positioning_parse_error_is_marked():
    block = sf._positioning("AAA", _F, None, None, None, short_state=sv.PARSE_ERROR)
    assert block == {"short_state": sv.PARSE_ERROR}


@pytest.mark.parametrize("state", [None, sv.UNAVAILABLE, sv.NO_OBSERVATION])
def test_positioning_absent_short_data_stays_none(state):
    assert sf._positioning("AAA", _F, None, None, None, short_state=state) is None


def test_positioning_ticker_absent_from_snapshot_carries_no_state():
    short = _si_snapshot("2026-09-30")
    assert sf._positioning("QQQ", _F, short, None, None, short_state=sv.OBSERVED) is None


def test_positioning_full_short_flow_is_unchanged():
    block = sf._positioning("AAA", _F, None, None, _FULL)
    assert block == {"short_flow": {"short_ratio_pct": 25.0, "trend_pp": 5.0, "ratio_z": 1.1,
                                    "n_days": 40, "asof": "2026-10-09"}}


@pytest.mark.parametrize("sig, state", [
    ({**_FULL, "n_days": 12}, sv.PARTIAL),
    ({**_FULL, "ratio_z": None}, sv.PARTIAL),
    ({**_FULL, "ratio_recent": 0.0}, sv.OBSERVED_ZERO),
], ids=["short_history", "no_z", "zero_recent"])
def test_positioning_qualified_short_flow_carries_state(sig, state):
    assert sf._positioning("AAA", _F, None, None, sig)["short_flow"]["state"] == state



def test_short_flow_state_disclosure_node():
    """Execute the shipped short-flow JS block; Node absence is explicit."""
    import shutil
    import subprocess
    from pathlib import Path
    node = shutil.which('node')
    if not node:
        pytest.skip('Node required for actual short-flow block rendering')
    subprocess.run([node, str(Path(__file__).with_name('test_short_flow_disclosure.cjs'))], check=True)


_SHORT_FLOW_CASES = (
    "healthy", "partial", "genuine_zero", "rounded_positive", "missing_short",
    "missing_total", "all_missing", "infinite_total", "old_invalid",
    "invalid_latest_ratio", "optional_latest_absent", "baseline_missing",
    "mixed_invalid_missing", "zero_recent", "latest_zero_only", "no_ratio_column",
)


def _short_flow_fixture(case):
    from collectors.finra_short_volume import _parse

    n = 8 if case == "partial" else 30
    short, total = ((0, 100) if case == "genuine_zero" else
                    (1, 100_000_000) if case == "rounded_positive" else (50, 100))
    text = "Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market\n" + "\n".join(
        f"{day:%Y%m%d}|AAA|{short}|0|{total}|Q"
        for day in pd.date_range("2026-10-01", periods=n)
    )
    panel = _parse(text, universe={"AAA"})
    assert len(panel) == n and set(panel["ticker"]) == {"AAA"}
    # Fresh malformed pairs are rejected by _parse. These deliberate mutations
    # exercise corruption/missingness retained in an existing Parquet store.
    if case in {"missing_short", "missing_total"}:
        panel.loc[n - 1, "short_vol" if case == "missing_short" else "total_vol"] = float("nan")
    elif case == "all_missing":
        panel[["short_vol", "total_vol"]] = float("nan")
    elif case == "infinite_total":
        panel.loc[n - 1, "total_vol"] = float("inf")
    elif case == "old_invalid":
        panel.loc[0, "short_vol"] = -1.0
    elif case == "invalid_latest_ratio":
        panel.loc[n - 1, "short_ratio"] = 1.2
    elif case == "optional_latest_absent":
        panel.loc[n - 1, "short_vol"] = 70.0
        panel.loc[n - 1, "short_ratio"] = float("nan")
    elif case == "baseline_missing":
        panel.loc[n - 10, "short_vol"] = float("nan")
    elif case == "mixed_invalid_missing":
        panel.loc[n - 1, "short_vol"] = float("nan")
        panel.loc[n - 2, "total_vol"] = -1.0
    elif case in {"zero_recent", "latest_zero_only"}:
        panel.loc[n - (5 if case == "zero_recent" else 1):, ["short_vol", "short_ratio"]] = 0.0
    elif case == "no_ratio_column":
        panel = panel.drop(columns=["short_ratio"])
    return panel


@pytest.mark.parametrize("case", _SHORT_FLOW_CASES)
def test_native_short_flow_producer_to_disclosure(tmp_path, monkeypatch, case):
    import json
    import shutil
    import subprocess
    from pathlib import Path

    node = shutil.which("node")
    if not node:
        pytest.skip("Node required for producer-to-render qualification")
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    panel_path = tmp_path / "finra_short_volume" / "panel.parquet"
    panel_path.parent.mkdir()
    _short_flow_fixture(case).to_parquet(panel_path)
    panel, panel_status = sv.panel_state(panel_path)
    assert panel_status == sv.OBSERVED
    direct = sv.signal_map(panel)
    assert direct and direct == sf._load_short_volume(), "the catch-all reader must not hide an exception"
    block = sf._positioning("AAA", _F, None, None, direct["AAA"])
    flow = block["short_flow"]
    expected_state = {
        "partial": sv.PARTIAL, "genuine_zero": sv.OBSERVED_ZERO,
        "missing_short": sv.UNAVAILABLE, "missing_total": sv.UNAVAILABLE,
        "all_missing": sv.NO_OBSERVATION, "infinite_total": sv.PARSE_ERROR,
        "old_invalid": sv.PARSE_ERROR, "invalid_latest_ratio": sv.PARSE_ERROR,
        "optional_latest_absent": sv.PARTIAL, "baseline_missing": sv.UNAVAILABLE,
        "mixed_invalid_missing": sv.PARSE_ERROR, "zero_recent": sv.OBSERVED_ZERO,
        "no_ratio_column": sv.PARTIAL,
    }.get(case)
    assert flow.get("state") == expected_state
    if case in {"missing_short", "missing_total", "all_missing", "infinite_total", "mixed_invalid_missing"}:
        assert flow["short_ratio_pct"] is None and flow["trend_pp"] is None and flow["ratio_z"] is None
    elif case == "old_invalid":
        assert flow["short_ratio_pct"] == 50.0 and flow["trend_pp"] == 0.0 and flow["ratio_z"] is None
        assert set(flow["coverage"]) == {"history_z"}
    elif case == "invalid_latest_ratio":
        assert flow["short_ratio_pct"] is None and flow["trend_pp"] == 0.0
        assert set(flow["coverage"]) == {"latest", "history_z"}
    elif case == "baseline_missing":
        assert flow["short_ratio_pct"] == 50.0 and flow["trend_pp"] is None
        assert set(flow["coverage"]) == {"baseline", "history_z"}
    elif case == "optional_latest_absent":
        assert (flow["short_ratio_pct"], flow["trend_pp"], flow["ratio_z"]) == (54.0, 3.0, None)
    elif case in {"rounded_positive", "genuine_zero", "latest_zero_only", "zero_recent"}:
        assert flow["short_ratio_pct"] == 0.0
    if "coverage" in flow:
        assert flow["coverage"] == direct["AAA"]["coverage"]
    file = tmp_path / "positioning.json"
    file.write_text(json.dumps(block, allow_nan=False, sort_keys=True))
    run = subprocess.run(
        [node, str(Path(__file__).with_name("test_short_flow_disclosure.cjs")), str(file)],
        check=True, capture_output=True, text=True,
    )
    result = json.loads(run.stdout)
    assert set(result["rendered"]) == {"en", "zh"} and result["passed"] > 0
    for locale, rendered in result["rendered"].items():
        zero_note = "Reported zero" if locale == "en" else "报告的卖空成交量为零"
        assert (zero_note in rendered["html"]) == (expected_state == sv.OBSERVED_ZERO)
