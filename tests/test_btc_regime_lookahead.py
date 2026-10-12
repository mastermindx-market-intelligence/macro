"""T13 look-ahead gate for regime and cycle labels.

Protocol: compute the label as of t, append rows dated after t, recompute as of
the same t. The label must match. A fixture-level oracle that peeks at the
eventual extreme must NOT match, so a green run means the harness can still
tell a leak from a causal label.

The cycle-thesis case calls ``monitor`` with the longer frame and ``asof=t``
(the function's own clock). It fails on the current engine: ``_extreme`` reads
``peak_date ± 21d`` on the unsliced series (engine/btc_cycle_thesis.py:62-69,
123). The clip is in
``research/crypto_science/patches/cx-t13p-20261012__btc_cycle_thesis.patch``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engine import btc_regime
from engine.btc_cycle_thesis import monitor
from engine.btc_mtf import confluence_verdict, mtf_ladder
from engine.crypto_market_state import build_market_state, class_regimes
from engine.cycles import find_troughs


def _leaky_full_sample_extreme(close: pd.Series, as_of) -> str:
    """Fixture oracle. Ignores ``as_of`` and labels from the eventual minimum."""
    trough = close.idxmin()
    return "after_trough" if pd.Timestamp(as_of) >= trough else "before_trough"


def _causal_running_extreme(close: pd.Series, as_of) -> str:
    hist = close.loc[:pd.Timestamp(as_of)]
    return "at_low" if float(hist.iloc[-1]) <= float(hist.min()) else "off_low"


def test_harness_catches_a_leaky_full_sample_extreme():
    idx = pd.date_range("2020-01-01", periods=40, freq="D")
    t = idx[20]
    close = pd.Series(100.0, index=idx)
    close.iloc[20] = 80.0
    close.iloc[30] = 40.0  # eventual trough, after t
    before = _leaky_full_sample_extreme(close.loc[:t], t)
    after = _leaky_full_sample_extreme(close, t)
    assert before == "after_trough"
    assert after == "before_trough"


def test_causal_running_extreme_is_stable_when_future_rows_are_appended():
    idx = pd.date_range("2020-01-01", periods=40, freq="D")
    t = idx[20]
    close = pd.Series(100.0, index=idx)
    close.iloc[20] = 80.0
    close.iloc[30] = 40.0
    assert _causal_running_extreme(close.loc[:t], t) == _causal_running_extreme(close, t)


def _regime_frame(n=420, seed=13):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    close = 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.02, n)))
    df = pd.DataFrame(
        {
            "close": close,
            "net_liq_roc": rng.normal(0, 1, n),
            "global_m2_yoy": rng.normal(0.05, 0.01, n),
            "real_yield": rng.normal(0.01, 0.002, n),
            "dxy": 100 + np.cumsum(rng.normal(0, 0.2, n)),
            "vix": np.abs(rng.normal(18, 3, n)),
            "hy_oas": np.abs(rng.normal(4, 0.4, n)),
            "mvrv_z": rng.normal(0, 1, n),
            "etf_flow_z": rng.normal(0, 1, n),
            "stbl_growth_z": rng.normal(0, 1, n),
        },
        index=idx,
    )
    return df


def test_regime_band_at_t_ignores_rows_after_t():
    df = _regime_frame()
    t = df.index[300]
    shocked = df.copy()
    shocked.loc[df.index[301]:, "close"] *= 3
    shocked.loc[df.index[301]:, "vix"] = 80
    short = btc_regime.composite_frame(df.loc[:t])
    long = btc_regime.composite_frame(shocked)
    for col in ("index", "index_thin", "composite", "n_live"):
        a, b = short.loc[t, col], long.loc[t, col]
        if pd.isna(a) and pd.isna(b):
            continue
        assert a == b, col
    score = btc_regime.compute(df.loc[:t])
    raw = long.loc[t, "index"]
    if pd.isna(raw):
        raw = long.loc[t, "index_thin"]
    band = btc_regime._band_label(None if pd.isna(raw) else float(raw))["label"]
    assert score["ok"] is True
    assert score["asof"] == str(pd.Timestamp(t).date())
    assert score["band"] == band
    assert score["band"] in {
        "STRONG TAILWIND", "TAILWIND", "NEUTRAL", "HEADWIND", "STRONG HEADWIND", "n/a",
    }


def _tones(cap: pd.Series) -> pd.Series:
    clean = cap.dropna().sort_index()
    out = pd.Series(index=clean.index, dtype=object)
    for seg in class_regimes(clean):
        start, end = pd.Timestamp(seg["start"]), pd.Timestamp(seg["end"])
        out.loc[(out.index >= start) & (out.index <= end)] = seg["tone"]
    return out


def test_class_regime_tone_through_t_ignores_rows_after_t():
    rng = np.random.default_rng(7)
    idx = pd.date_range("2019-01-01", periods=420, freq="D")
    t = idx[300]
    cap = pd.Series(np.exp(np.cumsum(rng.normal(0.002, 0.015, len(idx)))) * 1e12, index=idx)
    future = cap.copy()
    future.loc[idx[301]:] *= 0.25
    short = _tones(cap.loc[:t])
    long = _tones(future)
    assert short.notna().all()
    assert long.loc[:t].equals(short)
    # The open segment's end is the last print (duration so far), so the
    # segment list itself grows. The tone on each date <= t does not.
    assert class_regimes(future)[-1]["end"] != class_regimes(cap.loc[:t])[-1]["end"]


def _market_frames(idx: pd.DatetimeIndex, close: np.ndarray) -> dict:
    n = len(idx)
    dom = np.linspace(52, 50, n)
    return {
        ("coinmetrics", "mcap_usd"): pd.DataFrame({"mcap_usd": close * 1e6}, index=idx),
        ("bgeo", "btc_dominance"): pd.DataFrame({"btc_dominance": dom}, index=idx),
        ("sentiment_crypto", "fear_greed"): pd.DataFrame(
            {"fear_greed": np.full(n, 50.0)}, index=idx
        ),
        ("defillama", "stablecoins"): pd.DataFrame(
            {"stablecoin_mcap_usd": np.full(n, 1.5e11)}, index=idx
        ),
        ("coinbase", "btc_daily"): pd.DataFrame(
            {"close": close, "volume": np.full(n, 1e9)}, index=idx
        ),
        ("yahoo", "ETH-USD"): pd.DataFrame({"close": close * 0.05}, index=idx),
        ("farside", "etf_flows"): pd.DataFrame({"total": np.full(n, 0.0)}, index=idx),
        ("vector", "signals"): pd.DataFrame(
            {
                "funding_annual_pct": np.full(n, 0.0),
                "oi_mcap_ratio": np.full(n, 0.02),
                "oi_mcap_pctile": np.full(n, 50.0),
                "dvol": np.full(n, 40.0),
                "dvol_pctile": np.full(n, 50.0),
            },
            index=idx,
        ),
    }


def _stance(frames, as_of=None) -> str:
    def reader(group, name):
        frame = frames.get((group, name))
        if frame is None:
            return pd.DataFrame()
        if as_of is None:
            return frame
        return frame.loc[:as_of]

    return build_market_state(reader)["stance"]


def test_market_state_stance_at_t_requires_the_caller_to_withhold_later_rows():
    idx = pd.date_range("2021-01-01", periods=200, freq="D")
    t = idx[150]
    close = np.full(len(idx), 100.0)
    frames = _market_frames(idx, close)
    # Flat through t. The crash sits inside the endpoint's own 30-day window
    # (a crash already 30 days old leaves both ends of that window on the new
    # level, so the 30-day change stays flat and the stance does not move).
    frames[("coinmetrics", "mcap_usd")].loc[idx[185]:, "mcap_usd"] = 40.0 * 1e6
    pinned = _stance(frames, as_of=t)
    endpoint = _stance(frames, as_of=None)
    assert pinned == "Range-bound, waiting for participation"
    assert endpoint != pinned
    assert _stance(
        {k: v.loc[:t] for k, v in frames.items()}, as_of=None
    ) == pinned


def _mtf_grade(close: pd.Series, high: pd.Series, as_of) -> dict:
    ladder = mtf_ladder(close.loc[:as_of], high.loc[:as_of])
    verdict = confluence_verdict(ladder)
    return {
        "grade": verdict.get("grade"),
        "regime": verdict.get("regime"),
        "ladder_state": verdict.get("ladder_state"),
        "headline": verdict.get("headline"),
    }


def test_mtf_verdict_at_t_ignores_rows_after_t():
    rng = np.random.default_rng(3)
    idx = pd.date_range("2018-01-01", periods=900, freq="D")
    t = idx[700]
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0002, 0.02, len(idx)))), index=idx)
    high = close * 1.01
    future = close.copy()
    future.loc[idx[701]:] *= 0.3
    assert _mtf_grade(close, high, t) == _mtf_grade(future, future * 1.01, t)


def test_full_sample_trough_merge_rewrites_a_trough_the_prefix_had_confirmed():
    """``find_troughs`` on a longer sample can drop a trough the prefix had
    already confirmed, when a later lower trough falls inside ``TROUGH_MIN_GAP``.

    That is look-ahead if a backtest paints history from one full-sample call.
    The live label path avoids it only by truncating at the series end
    (engine/cycles.py:399-420). Pinning as_of by truncation keeps the prefix set.
    """
    idx = pd.date_range("2020-01-01", periods=80, freq="D")
    # Strictly rising except two dips, so a flat tie cannot mint extra troughs.
    close = pd.Series(np.arange(len(idx), dtype=float) + 100.0, index=idx)
    close.iloc[30] = 50.0
    close.iloc[47] = 40.0
    t = idx[49]  # iloc 30 is confirmable (needs +10 bars); iloc 47 is not yet
    prefix = tuple(find_troughs(close.loc[:t]))
    # Full-sample troughs whose DATES are <= t. iloc 47 is dated before t, but
    # it only becomes a confirmed trough once ten bars exist after it.
    leaked = tuple(ts for ts in find_troughs(close) if ts <= t)
    assert prefix == (idx[30],)
    assert leaked == (idx[47],)
    assert tuple(find_troughs(close.loc[:t])) == prefix


def _thesis_cfg():
    return {
        "cycle_clock": {"halving_dates": []},
        "cycle_phase_clock": {
            "tops": ["2019-01-01"],
            "bottoms": ["2020-01-06"],
        },
    }


def _thesis_path():
    """One completed bear whose bottom window still reaches past ``as_of``.

    Bottom 2020-01-06, as_of 2020-01-11 (inside the +21d slack). A print of 20
    on 2020-01-21 is inside that slack and after as_of, so an unsliced
    ``_extreme`` revises the prior-bear depth.
    """
    idx = pd.date_range("2018-06-01", "2020-02-15", freq="D")
    px = pd.Series(60.0, index=idx)
    top = pd.Timestamp("2019-01-01")
    bot = pd.Timestamp("2020-01-06")
    now = pd.Timestamp("2020-01-11")
    px.loc[top - pd.Timedelta(days=30): top + pd.Timedelta(days=30)] = 90.0
    px.loc[top - pd.Timedelta(days=2): top + pd.Timedelta(days=2)] = 100.0
    span = px.loc["2019-02-15":bot]
    px.loc[span.index] = np.linspace(90, 48, len(span))
    px.loc[bot:now] = 50.0
    px.loc[bot] = 48.0
    px.loc[pd.Timestamp("2020-01-21")] = 20.0
    return px, now


def _thesis_decision(close, as_of):
    out = monitor(close, cfg=_thesis_cfg(), asof=as_of)
    return {
        "ok": out.get("ok"),
        "asof": out.get("asof"),
        "thesis_status": out.get("thesis_status"),
        "time_status": out.get("time_status"),
        "dampening": out.get("dampening"),
        "prior_bear_mean": out.get("prior_bear_mean"),
        "peak_price": out.get("peak_price"),
        "flags": tuple((f["key"], f["level"]) for f in out.get("flags") or []),
    }


@pytest.mark.xfail(strict=True, reason="T13 look-ahead defect in engine/btc_cycle_thesis.py monitor(); fixed by research/crypto_science/patches/cx-t13p-20261012__btc_cycle_thesis.patch — remove this marker in the same commit that applies the patch")
def test_cycle_thesis_label_at_t_ignores_rows_after_t():
    close, as_of = _thesis_path()
    pinned = _thesis_decision(close.loc[:as_of], as_of)
    leaked = _thesis_decision(close, as_of)
    assert pinned["ok"] is True and pinned["asof"] == "2020-01-11"
    assert pinned == leaked
