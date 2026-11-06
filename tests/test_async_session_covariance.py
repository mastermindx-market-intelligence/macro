from __future__ import annotations

"""Hermetic tests for engine/async_session_covariance.py (Q18, research reference).

Synthetic inputs only: integer day offsets from the Unix epoch origin, seeded
random draws. No network, no repository data, no dependence on the current date.
"""

import importlib
import math
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from engine import async_session_covariance as asc

ORIGIN = pd.Timestamp(0)  # epoch origin; all dates below are integer offsets from it


def _bdays(start_offset: int, n: int) -> pd.DatetimeIndex:
    d = ORIGIN + pd.to_timedelta(np.arange(start_offset, start_offset + 3 * n), unit="D")
    d = d[d.dayofweek < 5]
    return pd.DatetimeIndex(d[:n])


# ---------------------------------------------------------------- req1
def test_req1_interval_map_is_explicit_utc_and_contiguous():
    dates = _bdays(400, 260)  # spans US DST transitions
    px = np.exp(np.cumsum(np.full(len(dates), 0.001)))
    iv = asc.return_intervals(dates, px, asc.NYSE)
    assert len(iv) == len(dates) - 1
    assert (iv["end_utc"].to_numpy() > iv["start_utc"].to_numpy()).all()
    assert (iv["start_utc"].to_numpy()[1:] == iv["end_utc"].to_numpy()[:-1]).all()
    # independent DST count via zoneinfo
    tz = ZoneInfo("America/New_York")
    offs = [ (d.to_pydatetime().replace(hour=16, tzinfo=tz)).utcoffset() for d in dates ]
    expected = sum(1 for i in range(1, len(offs)) if offs[i] != offs[i - 1])
    assert expected >= 1
    assert int(iv["dst_shift"].sum()) == expected
    # each end instant is 16:00 local
    first_end = pd.Timestamp(int(iv["end_utc"].iloc[0]), unit="s", tz="UTC").tz_convert(tz)
    assert (first_end.hour, first_end.minute) == (16, 0)


def test_req1_holiday_gap_and_early_close_flags():
    dates = _bdays(800, 30)
    holiday = dates[10]
    kept = dates.delete(10)
    px = np.linspace(100.0, 101.0, len(kept))
    iv = asc.return_intervals(kept, px, asc.NYSE, early_closes={kept[5]: "13:00"})
    gap_rows = iv[iv["holiday_gap"]]
    assert len(gap_rows) == 1 and gap_rows["skipped_weekdays"].iloc[0] == 1
    assert gap_rows["prev_date"].iloc[0] < holiday < gap_rows["date"].iloc[0]
    ec = iv[iv["early_close"]]
    assert len(ec) == 1 and ec["date"].iloc[0] == kept[5]
    regular = asc.close_timestamps_utc([kept[5]], asc.NYSE)["end_utc"].iloc[0]
    early = asc.close_timestamps_utc([kept[5]], asc.NYSE, {kept[5]: "13:00"})["end_utc"].iloc[0]
    assert regular - early == 3 * 3600


def test_req1_undeclared_clock_is_unknown_not_guessed():
    spec = asc.SessionSpec("MYSTERY", None, None)
    ts = asc.close_timestamps_utc(_bdays(100, 5), spec)
    assert (ts["state"] == asc.UNKNOWN).all()
    assert ts["end_utc"].isna().all()
    assert asc.classify_pair_clock(spec, asc.NYSE, _bdays(100, 5))["clock"] == asc.UNIDENTIFIED


# ---------------------------------------------------------------- req2
def test_req2_naive_same_label_attenuates_and_hy_recovers():
    rho, fa, fb = 0.6, 0.29, 0.83  # ~07:00 UTC vs ~20:00 UTC closes
    sim = asc.simulate_async_pair(3000, rho, fa, fb, seed=11)
    a, b = sim["a"], sim["b"]
    naive = asc.realized_corr(a["ret"], b["ret"])
    hy = asc.hayashi_yoshida(a["ret"], a["start"], a["end"], b["ret"], b["start"], b["end"])
    assert hy["state"] == asc.MEASURED
    assert abs(naive - rho * (1 - abs(fa - fb))) < 0.06
    assert abs(hy["corr"] - rho) < 0.06
    assert hy["corr"] - naive > 0.2


def test_req2_simultaneous_closes_hy_equals_naive():
    sim = asc.simulate_async_pair(500, 0.5, 0.4, 0.4, seed=3)
    a, b = sim["a"], sim["b"]
    hy = asc.hayashi_yoshida(a["ret"], a["start"], a["end"], b["ret"], b["start"], b["end"])
    assert hy["n_pairs"] == len(a["ret"])
    assert hy["corr"] == pytest.approx(asc.realized_corr(a["ret"], b["ret"]), abs=1e-12)


def test_req2_holiday_gaps_are_absorbed_by_hy():
    sim = asc.simulate_async_pair(3000, 0.6, 0.29, 0.83, seed=5,
                                  drop_days_a=range(7, 3000, 19))
    a, b = sim["a"], sim["b"]
    hy = asc.hayashi_yoshida(a["ret"], a["start"], a["end"], b["ret"], b["start"], b["end"])
    assert abs(hy["corr"] - 0.6) < 0.06
    assert hy["n_pairs"] > len(a["ret"])  # multi-day A intervals pair with several B returns


# ---------------------------------------------------------------- req3
def test_req3_only_declared_estimators_no_lag_search():
    public = [n for n in dir(asc) if not n.startswith("_") and callable(getattr(asc, n))]
    for bad in ("search", "optimal", "best_lag", "argmax", "select_lag", "tune"):
        assert not any(bad in n.lower() for n in public), bad
    la = _bdays(200, 6)
    ra = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    rb = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
    out = asc.lag_aligned(la, ra, la, rb, lag=1)
    # A[t] paired with B[t-1]: pairs (2,10),(3,20),(4,30),(5,40),(6,50)
    x, y = ra[1:], rb[:-1]
    assert out["n_matched"] == 5
    assert out["corr"] == pytest.approx(float(x @ y / math.sqrt((x @ x) * (y @ y))))
    with pytest.raises(ValueError):
        asc.lag_aligned(la, ra, la, rb, lag=-1)


# ---------------------------------------------------------------- req4
def test_req4_states_are_distinct_and_missing_is_never_zero():
    assert len(set(asc.STATES)) == len(asc.STATES) == 7
    nan = np.array([np.nan, 1.0])
    one = np.array([0.0, 1.0])
    assert asc.hayashi_yoshida([0.1, 0.2], nan, one + 1, [0.1], [0], [3])["state"] == asc.UNKNOWN
    far = asc.hayashi_yoshida([0.1], [0], [1], [0.2], [5], [6])
    assert far["state"] == asc.NO_OVERLAP and far["corr"] is None
    few = asc.hayashi_yoshida([0.1], [0], [2], [0.2], [1], [3], min_pairs=2)
    assert few["state"] == asc.INSUFFICIENT and few["corr"] is None
    flat = asc.hayashi_yoshida([0.0, 0.0], [0, 1], [1, 2], [0.1, 0.2], [0, 1], [1, 2])
    assert flat["state"] == asc.INVALID


def test_req4_invalid_price_is_bridged_not_zero_filled_and_zero_is_measured():
    dates = _bdays(300, 8)
    px = np.array([100.0, 101.0, np.nan, 103.0, 103.0, -1.0, 104.0, 105.0])
    iv = asc.return_intervals(dates, px, asc.SSE)
    assert iv.attrs["n_invalid_prices"] == 2
    assert len(iv) == 5  # 6 valid prices -> 5 returns, no zero-filled rows
    bridged = iv[iv["bridged_invalid"]]
    assert len(bridged) == 2
    assert bridged["ret"].iloc[0] == pytest.approx(math.log(103.0 / 101.0))
    z = iv[iv["zero_return"]]
    assert len(z) == 1 and z["state"].iloc[0] == asc.MEASURED


def test_req4_excluded_and_pending_states():
    dates = _bdays(500, 10)
    px = np.linspace(50.0, 55.0, 10)
    iv = asc.return_intervals(dates, px, asc.HKEX_INDEX, exclude_dates=[dates[4]])
    assert iv.attrs["n_excluded_dates"] == 1 and int(iv["bridged_excluded"].sum()) == 1
    cut = int(iv["end_utc"].iloc[5])
    ivp = asc.return_intervals(dates, px, asc.HKEX_INDEX, asof_utc=cut)
    assert (ivp["state"] == asc.PENDING).sum() == int((ivp["end_utc"] > cut).sum()) > 0
    q = asc.qualify_pair(ivp, ivp, min_pairs=2)
    assert q["support"]["a"]["states"][asc.PENDING] > 0
    assert q["hy"]["n_a_used"] == int((ivp["state"] == asc.MEASURED).sum())


# ---------------------------------------------------------------- req5
def test_req5_block_bootstrap_is_seeded_and_reports_honest_blocks():
    rng = np.random.default_rng(0)
    x = rng.normal(0.1, 1.0, size=(30, 2))
    x[3, 1] = np.nan
    r1 = asc.moving_block_bootstrap_mean(x, block_len=4, n_boot=500, seed=18)
    r2 = asc.moving_block_bootstrap_mean(x, block_len=4, n_boot=500, seed=18)
    assert r1 == r2
    assert r1["n_time_blocks"] == 30
    assert r1["ci_lo"] < r1["mean"] < r1["ci_hi"]
    tiny = asc.moving_block_bootstrap_mean([1.0], block_len=1)
    assert tiny["state"] == asc.INSUFFICIENT


def test_req5_newey_west_matches_iid_at_lag0_and_grows_with_autocorrelation():
    rng = np.random.default_rng(1)
    e = rng.normal(size=400)
    nw0 = asc.newey_west_se(e, 0)
    assert nw0["se"] == pytest.approx(math.sqrt(np.var(e) / len(e)))
    ar = np.empty(400)
    ar[0] = e[0]
    for t in range(1, 400):
        ar[t] = 0.7 * ar[t - 1] + e[t]
    assert asc.newey_west_se(ar, 6)["se"] > asc.newey_west_se(ar, 0)["se"]


# ---------------------------------------------------------------- req6
def test_req6_psd_is_reported_not_repaired_and_inputs_untouched():
    m = np.array([[1.0, 0.9, -0.9], [0.9, 1.0, 0.9], [-0.9, 0.9, 1.0]])
    before = m.copy()
    rep = asc.psd_report(m)
    assert rep["is_psd"] is False and rep["min_eig"] < 0 and rep["repaired"] is False
    assert np.array_equal(m, before)
    assert asc.psd_report(np.eye(3))["is_psd"] is True


def test_req6_out_of_bounds_corr_flagged_not_clipped():
    hy = asc.hayashi_yoshida([1.0], [0], [4], [1.0, 1.0, 1.0, 1.0], [0, 1, 2, 3], [1, 2, 3, 4],
                             min_pairs=1)
    assert hy["corr"] == pytest.approx(2.0)
    assert hy["corr_out_of_bounds"] is True


def test_req6_inputs_are_bounded():
    big = np.zeros(asc.MAX_OBS + 1)
    with pytest.raises(ValueError):
        asc.newey_west_se(big, 1)
    with pytest.raises(ValueError):
        asc.realized_corr(big, big)
    with pytest.raises(ValueError):
        asc.simulate_async_pair(asc.MAX_OBS, 0.5, 0.1, 0.2)


# ---------------------------------------------------------------- contract
def test_no_silent_activation_module_contract():
    mod = importlib.reload(asc)
    assert mod.RESEARCH_ONLY is True
    assert (mod.__doc__ or "").startswith("RESEARCH REFERENCE — NOT WIRED")
    names = {n.lower() for n in vars(mod)}
    for bad in ("register", "schedule", "activate", "publish", "promote", "wire", "main"):
        assert not any(n == bad or n.startswith(bad + "_") for n in names), bad
    ra = np.array([0.1, -0.2, 0.3])
    sa = np.array([0, 1, 2])
    snap = (ra.copy(), sa.copy())
    mod.hayashi_yoshida(ra, sa, sa + 1, ra, sa, sa + 1, min_pairs=1)
    assert np.array_equal(ra, snap[0]) and np.array_equal(sa, snap[1])


# ======================================================================
# Brief-keyed discriminating requirements (Q18 brief, acceptance items 1-6).
# Added by the finisher after the independent audit (PREREG_AMENDMENT.md A1).
# ======================================================================
FORBIDDEN_OUTPUT_KEY_PARTS = ("intraday", "lead", "causal", "granger", "best", "optimal",
                              "argmax", "selected_lag", "tuned")


def _all_keys(obj) -> set[str]:
    keys: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(str(k).lower())
            keys |= _all_keys(v)
    elif isinstance(obj, pd.DataFrame):
        keys |= {str(c).lower() for c in obj.columns}
    return keys


# ---------------------------------------------------------------- brief 1
def test_brief1_different_close_clocks_are_never_labelled_simultaneous():
    winter = _bdays(0, 30)  # Jan-Feb of the epoch year: no DST on any of the three clocks
    sse_hk = asc.classify_pair_clock(asc.SSE, asc.HKEX_INDEX, winter)
    assert sse_hk == {"clock": asc.NONSYNCHRONOUS, "lag_seconds": [70 * 60]}  # 07:00 vs 08:10 UTC
    sse_ny = asc.classify_pair_clock(asc.SSE, asc.NYSE, winter)
    assert sse_ny == {"clock": asc.NONSYNCHRONOUS, "lag_seconds": [14 * 3600]}  # 07:00 vs 21:00 UTC
    year = _bdays(0, 260)  # crosses both US DST transitions
    sse_ny_year = asc.classify_pair_clock(asc.SSE, asc.NYSE, year)
    assert sse_ny_year == {"clock": asc.DST_VARYING, "lag_seconds": [13 * 3600, 14 * 3600]}
    assert asc.classify_pair_clock(asc.NYSE, asc.NYSE, year) == {
        "clock": asc.SIMULTANEOUS, "lag_seconds": [0]}
    for a, b in ((asc.SSE, asc.NYSE), (asc.HKEX_INDEX, asc.NYSE), (asc.SSE, asc.HKEX_INDEX)):
        assert asc.classify_pair_clock(a, b, year)["clock"] != asc.SIMULTANEOUS


def test_brief1_same_date_label_is_not_the_same_return_interval():
    dates = _bdays(0, 40)
    px = np.exp(np.cumsum(np.linspace(-0.01, 0.01, len(dates))))
    ia = asc.return_intervals(dates, px, asc.SSE)
    ib = asc.return_intervals(dates, px, asc.NYSE)
    pa, pb = asc.overlap_pairs(ia["start_utc"].to_numpy(np.int64), ia["end_utc"].to_numpy(np.int64),
                               ib["start_utc"].to_numpy(np.int64), ib["end_utc"].to_numpy(np.int64))
    la = ia["date"].to_numpy()[pa]
    lb = ib["date"].to_numpy()[pb]
    # An Asia return dated t overlaps the US returns dated t-1 AND t; a same-label join keeps one.
    assert (la != lb).sum() > 0 and (la == lb).sum() > 0
    per_a = pd.Series(1, index=pa).groupby(level=0).sum()
    assert int(per_a.max()) >= 2


# ---------------------------------------------------------------- brief 2
def test_brief2_nonoverlapping_sessions_are_an_explicit_state_not_a_zero():
    a_dates, b_dates = _bdays(0, 60), _bdays(400, 60)
    ia = asc.return_intervals(a_dates, np.linspace(10, 11, 60), asc.SSE)
    ib = asc.return_intervals(b_dates, np.linspace(20, 21, 60), asc.NYSE)
    q = asc.qualify_pair(ia, ib, min_pairs=2)
    assert q["state"] == asc.NO_OVERLAP
    assert q["hy"]["corr"] is None and q["hy"]["cov"] is None


def test_brief2_dst_holiday_and_half_day_are_counted_in_support():
    dates = _bdays(60, 200)  # spans the spring and autumn US DST transitions of the epoch year
    kept = dates.delete(50)
    iv = asc.return_intervals(kept, np.linspace(100, 120, len(kept)), asc.NYSE,
                              early_closes={kept[100]: "13:00"})
    q = asc.qualify_pair(iv, iv, min_pairs=2)
    sup = q["support"]["a"]
    assert sup["n_holiday_gap"] >= 1 and sup["n_early_close"] == 1 and sup["n_dst_shift"] == 2


# ---------------------------------------------------------------- brief 3
def test_brief3_lag_is_an_integer_session_count_only():
    la = _bdays(200, 8)
    ra = np.arange(1.0, 9.0)
    rb = np.arange(10.0, 90.0, 10.0)
    base = asc.lag_aligned(la, ra, la, rb, lag=1)
    assert asc.lag_aligned(la, ra, la, rb, lag=np.int64(1)) == base
    for bad in (0.5, 1.0, True, np.float64(1.0), np.array([1]), [1], "1"):
        with pytest.raises(TypeError):
            asc.lag_aligned(la, ra, la, rb, lag=bad)


def test_brief3_daily_input_yields_daily_resolution_only():
    dates = _bdays(0, 120)
    px = np.exp(np.cumsum(np.sin(np.arange(120)) * 0.01))
    iv = asc.return_intervals(dates, px, asc.SSE)
    # one interval per consecutive pair of daily closes; no interpolated sub-day points
    assert len(iv) == len(dates) - 1
    tz = ZoneInfo("Asia/Shanghai")
    ends = pd.to_datetime(iv["end_utc"].to_numpy(np.int64), unit="s", utc=True).tz_convert(tz)
    assert set(zip(ends.hour, ends.minute)) == {(15, 0)}
    sim = asc.simulate_async_pair(200, 0.5, 0.29, 0.83, seed=2)
    a, b = sim["a"], sim["b"]
    outs = [
        asc.hayashi_yoshida(a["ret"], a["start"], a["end"], b["ret"], b["start"], b["end"]),
        asc.naive_same_label(dates[:50], np.ones(50) * 0.01, dates[:50], np.linspace(-1, 1, 50)),
        asc.lag_aligned(dates[:50], np.linspace(-1, 1, 50), dates[:50], np.linspace(1, -1, 50)),
        asc.qualify_pair(iv, iv, min_pairs=2),
        asc.classify_pair_clock(asc.SSE, asc.NYSE, dates),
        asc.moving_block_bootstrap_mean(np.ones((27, 2)), block_len=4, n_boot=50, seed=18),
        asc.newey_west_se(np.linspace(0, 1, 27), 3),
        iv,
    ]
    keys = set().union(*(_all_keys(o) for o in outs))
    for bad in FORBIDDEN_OUTPUT_KEY_PARTS:
        assert not any(bad in k for k in keys), (bad, sorted(keys))


def test_brief3_honest_n_is_time_blocks_not_daily_rows():
    rng = np.random.default_rng(7)
    per_quarter = rng.normal(0.1, 0.05, size=(27, 2))  # 27 quarters x 2 pairs
    r = asc.moving_block_bootstrap_mean(per_quarter, block_len=4, n_boot=200, seed=18)
    assert r["n_time_blocks"] == 27 and r["block_len"] == 4
    assert asc.newey_west_se(per_quarter.mean(axis=1), 3)["n"] == 27


# ---------------------------------------------------------------- brief 4
def test_brief4_synthetic_bias_shrinks_for_hy_and_support_limit_is_enforced():
    for rho, seed in ((0.3, 30), (0.6, 60)):
        sim = asc.simulate_async_pair(2500, rho, 0.29, 0.83, seed=seed)
        a, b = sim["a"], sim["b"]
        naive_bias = abs(asc.realized_corr(a["ret"], b["ret"]) - rho)
        hy = asc.hayashi_yoshida(a["ret"], a["start"], a["end"], b["ret"], b["start"], b["end"])
        assert abs(hy["corr"] - rho) < naive_bias
    short = asc.simulate_async_pair(15, 0.6, 0.29, 0.83, seed=4)
    a, b = short["a"], short["b"]
    thin = asc.hayashi_yoshida(a["ret"], a["start"], a["end"], b["ret"], b["start"], b["end"],
                               min_pairs=40)
    assert thin["state"] == asc.INSUFFICIENT and thin["corr"] is None


# ---------------------------------------------------------------- brief 5
def test_brief5_lag_is_frozen_by_declaration_and_never_called_causal():
    import inspect

    assert inspect.signature(asc.lag_aligned).parameters["lag"].default == 1
    doc = " ".join((asc.__doc__ or "").lower().split())
    assert "no lead/lag here is a causal direction" in doc
    public = [n.lower() for n in dir(asc) if not n.startswith("_")]
    for bad in ("causal", "granger", "lead", "direction"):
        assert not any(bad in n for n in public), bad


# ---------------------------------------------------------------- brief 6
def test_brief6_missingness_kept_inputs_untouched_context_only():
    dates = _bdays(300, 10)
    px = np.array([100.0, np.nan, 102.0, 103.0, 0.0, 104.0, 105.0, 105.0, 106.0, 107.0])
    snap = px.copy()
    iv = asc.return_intervals(dates, px, asc.SSE)
    assert np.array_equal(px, snap, equal_nan=True)
    assert iv.attrs["n_invalid_prices"] == 2 and iv["ret"].notna().all()
    assert asc.RESEARCH_ONLY is True
    assert "context-only" in (asc.__doc__ or "")
