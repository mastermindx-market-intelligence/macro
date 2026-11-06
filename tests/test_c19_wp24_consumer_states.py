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
