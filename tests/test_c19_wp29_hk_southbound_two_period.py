"""C19 WP29: pin HK southbound two-period share-flow and missing-not-zero.

Offline pins for engine/hk_southbound_stocks.py. The store is monkeypatched to
tmp_path; this file never reads or writes the repo data/ tree.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engine import hk_southbound_stocks as sb
from lib import config

TICK = [f"{i:04d}.HK" for i in range(1, 11)]
PAYLOAD_KEYS = {
    "accum_z", "own_z", "own_pct", "chg5_pct", "hold_b", "label", "basis",
}


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    store = tmp_path / "hk_southbound" / "holdings.parquet"
    monkeypatch.setattr(sb, "_store_path", lambda: store)
    return store


def _write_history(store, frames):
    """Create store.parent and write a (date, ticker) MultiIndex parquet."""
    store.parent.mkdir(parents=True, exist_ok=True)
    df = frames if isinstance(frames, pd.DataFrame) else pd.DataFrame(frames)
    if not isinstance(df.index, pd.MultiIndex):
        df = df.set_index(["date", "ticker"])
    df.index = df.index.set_names(["date", "ticker"])
    cols = ["hold_shares"] + [c for c in ("hold_mktcap", "close") if c in df.columns]
    df.loc[:, cols].astype({c: float for c in cols}).to_parquet(store)


def _two_date_t1_frame():
    """T1 first history: share-count % independent of close / hold_mktcap."""
    rows = []
    for i, t in enumerate(TICK):
        rows.append({
            "date": pd.Timestamp("2026-10-02"),
            "ticker": t,
            "hold_shares": 100.0,
            "close": 10.0,
            "hold_mktcap": 1_000.0,
        })
        rows.append({
            "date": pd.Timestamp("2026-10-05"),
            "ticker": t,
            "hold_shares": 100.0 * (1.0 + 0.01 * i),
            "close": 20.0,
            "hold_mktcap": 3_000.0,
        })
    return pd.DataFrame(rows)


@pytest.fixture
def SNAP():
    return pd.DataFrame(
        {
            "hold_mktcap": np.linspace(1e9, 5e9, 10),
            "add_amp": np.linspace(-2, 2, 10),
            "chg5_v": np.linspace(-1e8, 1e8, 10),
            "chg10_v": np.linspace(-2e8, 2e8, 10),
            "own_pct": np.linspace(1, 20, 10),
        },
        index=pd.Index(TICK, name="ticker"),
    )


def test_share_flow_5d_compares_two_hold_dates_on_share_counts(_isolated_store):
    store = _isolated_store
    _write_history(store, _two_date_t1_frame())
    flow = sb._share_flow_5d(TICK)
    assert isinstance(flow, pd.Series)
    for i, t in enumerate(TICK):
        assert flow[t] == pytest.approx(1.0 * i)

    dates = pd.date_range("2026-10-01", periods=7, freq="D")
    rows = []
    for j, day in enumerate(dates):
        for i, t in enumerate(TICK):
            if t == TICK[0]:
                shares = 100.0 if j == 0 else 200.0
            else:
                shares = 100.0 * (1.01 ** j)
            rows.append({
                "date": day,
                "ticker": t,
                "hold_shares": shares,
                "close": 10.0 * (2 ** j),
                "hold_mktcap": 1_000.0 * (3 ** j),
            })
    _write_history(store, pd.DataFrame(rows))
    flow7 = sb._share_flow_5d(TICK)
    assert isinstance(flow7, pd.Series)
    assert flow7[TICK[0]] == pytest.approx(0.0)
    assert flow7[TICK[1]] == pytest.approx((1.01 ** 5 - 1) * 100)

    rows = []
    for i, t in enumerate(TICK):
        rows.append({
            "date": pd.Timestamp("2026-10-02"),
            "ticker": t,
            "hold_shares": 100.0,
        })
        rows.append({
            "date": pd.Timestamp("2026-10-05"),
            "ticker": t,
            "hold_shares": 200.0 if t == TICK[9] else 100.0 * (1.0 + 0.01 * i),
        })
    _write_history(store, pd.DataFrame(rows))
    clipped = sb._share_flow_5d(TICK)
    assert isinstance(clipped, pd.Series)
    assert clipped[TICK[9]] == pytest.approx(60.0)


def test_share_flow_5d_returns_none_when_fewer_than_two_dates(_isolated_store):
    store = _isolated_store

    assert not store.exists()
    assert sb._share_flow_5d(TICK) is None

    one = pd.DataFrame({
        "date": [pd.Timestamp("2026-10-02")] * len(TICK),
        "ticker": TICK,
        "hold_shares": [100.0] * len(TICK),
    })
    _write_history(store, one)
    assert sb._share_flow_5d(TICK) is None

    seven = []
    for t in TICK[:7]:
        seven.append({
            "date": pd.Timestamp("2026-10-02"), "ticker": t, "hold_shares": 100.0,
        })
        seven.append({
            "date": pd.Timestamp("2026-10-05"), "ticker": t, "hold_shares": 110.0,
        })
    _write_history(store, pd.DataFrame(seven))
    assert sb._share_flow_5d(TICK) is None

    store.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {"hold_shares": [100.0] * len(TICK)},
        index=pd.Index(TICK, name="ticker"),
    ).to_parquet(store)
    assert sb._share_flow_5d(TICK) is None

    idx = pd.MultiIndex.from_product(
        [pd.to_datetime(["2026-10-02", "2026-10-05"]), TICK],
        names=["date", "ticker"],
    )
    pd.DataFrame({"close": 1.0}, index=idx).to_parquet(store)
    assert sb._share_flow_5d(TICK) is None


def test_normalize_keeps_hk_listing_suffix():
    assert sb._normalize("00700.HK") == "0700.HK"
    assert sb._normalize("09988.HK") == "9988.HK"
    assert sb._normalize("00005.HK") == "0005.HK"
    assert sb._normalize("700") is None
    assert sb._normalize("X0700.HK") is None
    for raw in ("00700.HK", "09988.HK", "00005.HK"):
        got = sb._normalize(raw)
        assert got is not None
        assert got.endswith(".HK")
        numeric = got[: -len(".HK")]
        assert numeric.isdigit() and len(numeric) == 4


def test_signal_payload_is_connect_holdings_not_ccass_or_13f(_isolated_store, SNAP):
    assert not _isolated_store.exists()
    out = sb.signal(TICK, SNAP)
    assert len(out) == 10
    for t in TICK:
        payload = out[t]
        assert set(payload.keys()) == PAYLOAD_KEYS
        for k, v in payload.items():
            assert "ccass" not in k.lower()
            assert "13f" not in k.lower()
            if isinstance(v, str):
                assert "ccass" not in v.lower()
                assert "13f" not in v.lower()
        assert payload["basis"] == "holding growth (value + share-add)"
        assert payload["hold_b"] == round(float(SNAP.loc[t, "hold_mktcap"]) / 1e9, 1)

    _write_history(_isolated_store, _two_date_t1_frame())
    out_flow = sb.signal(TICK, SNAP)
    assert len(out_flow) == 10
    for t in TICK:
        assert out_flow[t]["basis"] == "net-share flow (5d)"


def test_signal_does_not_consume_rev_z_or_revision_z(SNAP):
    SNAP2 = SNAP.copy()
    SNAP2["rev_z"] = np.linspace(-3, 3, 10)
    SNAP2["revision_z"] = np.linspace(3, -3, 10)
    assert sb.signal(TICK, SNAP2) == sb.signal(TICK, SNAP)


def test_missing_chg5_column_does_not_become_zero_hold(SNAP):
    out = sb.signal(TICK, SNAP.drop(columns=["chg5_v"]))
    assert len(out) == 10
    for t in TICK:
        assert out[t]["chg5_pct"] is None
        assert out[t]["hold_b"] == round(float(SNAP.loc[t, "hold_mktcap"]) / 1e9, 1)

    SNAP3 = SNAP.copy()
    SNAP3.loc[TICK[3], "chg5_v"] = np.nan

    def _expected_and_zero(frame):
        add = sb._zscore(frame["add_amp"].clip(-30, 30))
        chg5p = sb._zscore(sb._value_pct(frame["chg5_v"], frame["hold_mktcap"]))
        chg10p = sb._zscore(sb._value_pct(frame["chg10_v"], frame["hold_mktcap"]))
        legs = pd.DataFrame({"add": add, "chg5p": chg5p, "chg10p": chg10p})
        w = pd.Series({"add": 1.0, "chg5p": 1.0, "chg10p": 1.0})
        den = (legs.notna() * w).sum(axis=1)
        expected = sb._zscore((legs.fillna(0.0) * w).sum(axis=1) / den.where(den > 0))
        zero_fill = sb._zscore((legs.fillna(0.0) * w).sum(axis=1) / 3.0)
        return expected, zero_fill

    expected, zero_fill = _expected_and_zero(SNAP3)
    t3 = TICK[3]
    if abs(round(float(zero_fill[t3]), 2) - round(float(expected[t3]), 2)) <= 0.05:
        SNAP3.loc[t3, "add_amp"] = 25.0
        SNAP3.loc[t3, "chg10_v"] = 5e8
        expected, zero_fill = _expected_and_zero(SNAP3)

    out3 = sb.signal(TICK, SNAP3)
    assert out3[t3]["chg5_pct"] is None
    assert out3[t3]["accum_z"] == round(float(expected[t3]), 2)
    assert round(float(zero_fill[t3]), 2) != round(float(expected[t3]), 2)
    assert abs(round(float(zero_fill[t3]), 2) - round(float(expected[t3]), 2)) > 0.05
