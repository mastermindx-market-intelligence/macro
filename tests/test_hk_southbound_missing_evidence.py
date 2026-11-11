"""Missing accumulation is absent evidence, not an observed neutral screen leg."""
from datetime import datetime, timezone
import itertools

import numpy as np
import pandas as pd
import pytest

from engine import hk_southbound_stocks as sb
from engine import hk_stock_signals as signals
from lib import config, market_session

TICKERS = [f"{i:04d}.HK" for i in range(1, 11)]


def test_all_constant_presence_masks_keep_missing():
    for mask in itertools.product([False, True], repeat=10):
        source = pd.Series([2.0 if present else np.nan for present in mask], index=TICKERS)
        result = sb._zscore(source)
        assert result.notna().tolist() == list(mask)
        assert (result.dropna() == 0.0).all()


@pytest.mark.parametrize("value", [None, "", "not-a-number", float("nan")])
def test_raw_missing_payload_stays_absent_through_disk_and_edge(tmp_path, monkeypatch, value):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    # Freeze only current clock; native CONNECT calendars and admission run.
    monkeypatch.setattr(market_session, "_now", lambda now=None: datetime(2026, 11, 11, 12, tzinfo=timezone.utc))
    rows = [{
        "SECUCODE": f"{i:05d}.HK", "SECURITY_NAME": f"Fixture {i}",
        "HOLD_DATE": "2026-11-10", "HOLD_SHARES": 1000000,
        "HOLD_MARKET_CAP": 1e9, "HOLD_SHARES_RATIO": 2.0,
        "FREE_SHARES_RATIO": 3.0, "CLOSE_PRICE": 10.0,
        "ADD_SHARES_AMP": value, "HOLD_MARKETCAP_CHG5": value,
        "HOLD_MARKETCAP_CHG10": value,
    } for i in range(1, 11)]
    monkeypatch.setattr(sb, "_fetch_page", lambda page, retries, timeout: rows if page == 1 else [])
    snap = sb.fetch_snapshot(persist=True)
    assert snap is not None and len(snap) == 10
    assert (tmp_path / "hk_southbound/holdings.parquet").is_file()
    readback = sb.latest_holdings(allow_fetch=False)
    pd.testing.assert_frame_equal(snap.astype({"date": "datetime64[ns]"}).sort_index(),
                                  readback.astype({"date": "datetime64[ns]"}).sort_index(), check_freq=False)
    actual = sb.signal(TICKERS, snap=readback)
    assert actual == {}
    for regime in ("Risk-off", "neutral", "Risk-on"):
        kwargs = dict(ah_value={}, bnrs={t: 2.0 for t in TICKERS}, betas_pt={}, risk_state=regime)
        assert signals.hk_edge(TICKERS, southbound=actual, **kwargs) == signals.hk_edge(TICKERS, southbound={}, **kwargs)
        assert signals.hk_edge(TICKERS, southbound=actual, ah_value={}, bnrs={}, betas_pt={}, risk_state=regime) == {}


@pytest.mark.parametrize("history", [False, True])
@pytest.mark.parametrize("present", [0, 1, 5, 10])
@pytest.mark.parametrize("observed", [0.0, 2.0])
def test_signal_map_preserves_observed_constant_and_missing(monkeypatch, history, present, observed):
    snapshot = pd.DataFrame({
        "hold_mktcap": [1e9] * 10, "own_pct": [2.] * 10,
        "add_amp": [observed if i < present else np.nan for i in range(10)],
        "chg5_v": [np.nan] * 10, "chg10_v": [np.nan] * 10,
    }, index=TICKERS)
    flow = pd.Series([observed if i < present else np.nan for i in range(10)], index=TICKERS)
    monkeypatch.setattr(sb, "_share_flow_5d", lambda tickers: flow if history else None)
    actual = sb.signal(TICKERS, snap=snapshot)
    assert set(actual) == set(TICKERS[:present])
    assert all(row["accum_z"] == 0.0 and row["label"] == "steady" for row in actual.values())
    assert all(row["basis"] == ("net-share flow (5d)" if history else "holding growth (value + share-add)") for row in actual.values())


def test_healthy_finite_formula_parity():
    rng = np.random.default_rng(272)
    for _ in range(300):
        s = pd.Series(rng.normal(size=30))
        expected = ((s - s.mean()) / s.std(ddof=0)).clip(-3, 3)
        pd.testing.assert_series_equal(sb._zscore(s), expected)


def test_healthy_signal_dictionaries_unchanged(monkeypatch):
    rng = np.random.default_rng(272)
    current = sb._zscore

    def legacy(series):
        if series is None or not isinstance(series, pd.Series):
            return pd.Series(dtype=float)
        series = pd.to_numeric(series, errors="coerce")
        mean, sd = series.mean(), series.std(ddof=0)
        if not sd or np.isnan(sd):
            return pd.Series(0.0, index=series.index)
        return ((series - mean) / sd).clip(-3.0, 3.0)

    for trial in range(300):
        frame = pd.DataFrame({
            "hold_mktcap": rng.uniform(1e8, 1e10, 10),
            "own_pct": rng.uniform(0, 30, 10),
            "add_amp": rng.normal(0, 5, 10),
            "chg5_v": rng.normal(0, 1e7, 10),
            "chg10_v": rng.normal(0, 2e7, 10),
        }, index=TICKERS)
        flow = pd.Series(rng.normal(size=10), index=TICKERS) if trial % 2 else None
        monkeypatch.setattr(sb, "_share_flow_5d", lambda tickers, flow=flow: flow)
        monkeypatch.setattr(sb, "_zscore", legacy)
        expected = sb.signal(TICKERS, snap=frame)
        monkeypatch.setattr(sb, "_zscore", current)
        assert sb.signal(TICKERS, snap=frame) == expected
