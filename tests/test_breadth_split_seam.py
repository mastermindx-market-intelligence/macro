"""Split-seam repair guard for the breadth close caches (BreadthAdapter._merge_refreshed).

yfinance auto_adjust back-adjusts only the freshly downloaded window, so the
tail refresh (fresh 1mo combine_first cached) leaves cached pre-window rows on
the pre-split basis after a stock split. Observed 2026-07-10 in the live S&P
500 cache: KLAC $1,842.80 -> $180.90 across 2026-05-11/12 (fake -90.2% day from
the 10:1 split of 2026-06-12; the seam sits where the 1mo window stopped
rewriting), plus CRWD 4:1 and a DD re-basing. Poisons pct_above_50/200, 252d
NH/NL, adv/dec and the OHLCV extras caches until the lookback rolls past.

Pure-function tests (no network): the yfinance downloader is monkeypatched.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors.breadth import BreadthAdapter, seam_suspects  # noqa: E402

# 120 business days of history; the fresh refresh window covers the last 20
DATES = pd.bdate_range("2026-01-05", periods=120)
FRESH_START = 100


def _frame(cols: dict) -> pd.DataFrame:
    return pd.DataFrame(cols, index=DATES)


def _drifting(base: float, seed: int = 7) -> pd.Series:
    """A gently drifting price path — daily moves well inside the seam bounds."""
    rng = np.random.default_rng(seed)
    steps = 1 + rng.uniform(-0.02, 0.02, len(DATES))
    return pd.Series(base * np.cumprod(steps), index=DATES)


def _adapter(repull: pd.DataFrame | Exception | None, calls: list) -> BreadthAdapter:
    # skip __init__/config.load — _merge_refreshed reads cfg/name + _download_closes
    a = BreadthAdapter.__new__(BreadthAdapter)
    a.cfg = {"lookback_days_live": 1100}
    a._last_extras = {}

    def fake_download(tickers, period):
        calls.append((sorted(tickers), period))
        if isinstance(repull, Exception):
            raise repull
        assert repull is not None, "unexpected repair download"
        a._last_extras = getattr(a, "_repull_extras", {})
        return repull[[t for t in sorted(tickers) if t in repull.columns]]

    a._download_closes = fake_download
    return a


def _split_universe():
    """AAA has a 10:1 split during the fresh window; BBB is a clean control.

    truth = the coherent back-adjusted history a full re-pull returns.
    cached = truth on the PRE-split basis (10x) — what the cache held before.
    fresh  = last 20 days of truth — the auto-adjusted refresh window.
    """
    truth = _frame({"AAA": _drifting(100.0, 1), "BBB": _drifting(50.0, 2)})
    cached = truth.iloc[:-5].copy()
    cached["AAA"] *= 10
    fresh = truth.iloc[-20:]
    return truth, cached, fresh


def test_boundary_seam_detected_and_repaired():
    truth, cached, fresh = _split_universe()
    calls: list = []
    a = _adapter(truth, calls)
    merged = a._merge_refreshed(fresh, cached)
    # the repair re-pulled exactly the seamed ticker, at the full live window
    assert calls == [(["AAA"], "4y")]
    # pre-window history is now on the adjusted basis — no fake -90% day left
    pd.testing.assert_series_equal(merged["AAA"], truth["AAA"], check_names=False)
    r = merged / merged.shift(1)
    assert float(r.min().min()) > 0.60 and float(r.max().max()) < 1.65
    # the clean ticker is untouched
    pd.testing.assert_series_equal(merged["BBB"], truth["BBB"], check_names=False)


def test_legacy_mid_history_seam_repaired():
    # cache already part-healed by later refreshes (the live KLAC shape): the
    # seam sits mid-history, so cached and fresh AGREE on the overlap and only
    # the residual-jump scan can see it
    truth, _, fresh = _split_universe()
    cached = truth.iloc[:-5].copy()
    cached.loc[: DATES[60], "AAA"] *= 10
    calls: list = []
    a = _adapter(truth, calls)
    merged = a._merge_refreshed(fresh, cached)
    assert calls == [(["AAA"], "4y")]
    pd.testing.assert_series_equal(merged["AAA"], truth["AAA"], check_names=False)


def test_real_crash_survives_repair():
    # a genuine -62% day trips the scan; the re-pull returns the same data and
    # the "repair" must preserve the crash, not smooth it away
    crash = _drifting(100.0, 3)
    crash.iloc[40:] *= 0.38
    truth = _frame({"AAA": crash, "BBB": _drifting(50.0, 4)})
    cached, fresh = truth.iloc[:-5], truth.iloc[-20:]
    calls: list = []
    a = _adapter(truth, calls)
    merged = a._merge_refreshed(fresh, cached)
    assert calls == [(["AAA"], "4y")]
    pd.testing.assert_series_equal(merged["AAA"], truth["AAA"], check_names=False)


def test_dividend_scale_basis_does_not_trigger():
    # dividend re-adjustment shifts the cached basis by ~1.5% — below tolerance
    truth = _frame({"AAA": _drifting(100.0, 5), "BBB": _drifting(50.0, 6)})
    cached = truth.iloc[:-5].copy()
    cached["AAA"] *= 1.015
    fresh = truth.iloc[-20:]
    calls: list = []
    a = _adapter(None, calls)
    merged = a._merge_refreshed(fresh, cached)
    assert calls == []  # no repair download
    # plain combine_first result
    pd.testing.assert_frame_equal(merged, fresh.combine_first(cached))


def test_failed_repull_keeps_poisoned_column_for_retry():
    # repair download dies -> the seam must stay visible (NOT truncated), so
    # the scan re-flags it next run instead of silently orphaning the ticker
    truth, cached, fresh = _split_universe()
    calls: list = []
    a = _adapter(RuntimeError("yf down"), calls)
    merged = a._merge_refreshed(fresh, cached)
    assert calls == [(["AAA"], "4y")]
    assert seam_suspects(None, None, merged) == ["AAA"]
    pd.testing.assert_series_equal(merged["BBB"], truth["BBB"], check_names=False)


def test_extras_grafted_over_fresh_window():
    # the repaired ticker's OHLCV extras must span the full re-pulled window so
    # the later combine_first against the extras cache overrides poisoned rows
    truth, cached, fresh = _split_universe()
    calls: list = []
    a = _adapter(truth, calls)
    a._last_extras = {"high": fresh * 1.01, "volume": fresh * 0 + 1000}
    a._repull_extras = {"high": truth * 1.01, "volume": truth * 0 + 1000}
    merged = a._merge_refreshed(fresh, cached)
    assert calls == [(["AAA"], "4y")]
    high = a._last_extras["high"]
    # AAA's extras now reach back over the whole cached window on the new basis
    assert high["AAA"].first_valid_index() == DATES[0]
    assert float(high["AAA"].iloc[0]) == pytest.approx(float(truth["AAA"].iloc[0]) * 1.01)
    # BBB's extras still only cover the fresh window (cache fills the rest)
    assert high["BBB"].first_valid_index() == fresh.index[0]
    pd.testing.assert_series_equal(merged["AAA"], truth["AAA"], check_names=False)


def test_extras_grafted_for_a_ticker_absent_from_the_fresh_window():
    """2026-08-06 split-basis incident: the graft must NOT be filtered by the fresh
    window's columns.

    yfinance can return no High/Low for a name in a given 1mo batch. The old filter
    (`t in w.columns`) skipped exactly that ticker — healing its closes while its
    high/low kept the pre-split basis. That is the one split shape nothing in the
    tree can see: seam_suspects reads only the closes matrix, so both repair paths
    report success and the extras rot silently. Only ATR reads H/L and C together,
    and it fails as a blown-up true range, not as an error.
    """
    truth, cached, fresh = _split_universe()
    calls: list = []
    a = _adapter(truth, calls)
    # AAA — the ticker being healed — is missing from the fresh window's High frame.
    a._last_extras = {"high": (fresh * 1.01)[["BBB"]]}
    a._repull_extras = {"high": truth * 1.01}
    merged = a._merge_refreshed(fresh, cached)
    assert calls == [(["AAA"], "4y")]
    high = a._last_extras["high"]
    assert "AAA" in high.columns, "healed ticker dropped from the extras graft"
    # and it carries the POST-split basis over the whole cached window, so the
    # combine_first in fetch() overrides the poisoned cache rows instead of keeping them
    assert high["AAA"].first_valid_index() == DATES[0]
    assert float(high["AAA"].iloc[0]) == pytest.approx(float(truth["AAA"].iloc[0]) * 1.01)
    # the invariant the guard checks: close never sits outside its own [low, high]
    assert (merged["AAA"] <= high["AAA"].reindex(merged.index) * 1.000001).all()


def test_seam_scan_sees_across_nan_gaps():
    # a suspension gap ending exactly at the seam: without ffill the 1-day
    # ratio at the basis break is NaN/NaN and the seam is invisible
    truth, cached, fresh = _split_universe()
    cached.loc[DATES[95]:DATES[99], "AAA"] = np.nan
    merged = fresh.combine_first(cached)
    assert "AAA" in seam_suspects(None, None, merged)



@pytest.mark.parametrize('cached_kind', ['dividend', 'historical_staircase', 'healthy', 'corrupt', 'missing_rows'])
def test_fetch_replaces_cache_with_one_adjustment_vintage(tmp_path, monkeypatch, cached_kind):
    """Warm cache cannot contribute old-basis rows to a new 200DMA."""
    from lib import config
    monkeypatch.setattr(config, 'data_dir', lambda: tmp_path)
    dates = pd.bdate_range(end=pd.Timestamp.now().normalize(), periods=260)
    names = [f'T{i:03}' for i in range(400)]
    # Last close above a coherent MA, but below the mixed-vintage MA.
    values = np.full(260, 99.0); values[-1] = 99.5
    coherent = pd.DataFrame({n: values for n in names}, index=dates)
    cached = coherent.copy()
    if cached_kind == 'dividend':
        cached.iloc[:-20] *= 1.02
    elif cached_kind == 'historical_staircase':
        cached.iloc[:100] *= 1.04; cached.iloc[100:200] *= 1.02
    if cached_kind == 'missing_rows':
        coherent.iloc[:10, :10] = np.nan
    a = BreadthAdapter.__new__(BreadthAdapter)
    a.cfg = {'lookback_days_live': 1100, 'ma_windows': [50, 200], 'nhnl_window': 252}
    a.cache_path = tmp_path / '_closes_cache.parquet'
    if cached_kind == 'corrupt':
        a.cache_path.write_bytes(b'not parquet')
    else:
        cached.to_parquet(a.cache_path)
    a.constituents = lambda: pd.DataFrame({'symbol': names, 'name': names, 'sector': ['Tech']*400})
    calls = []
    def download(tickers, period):
        calls.append((tickers, period))
        a._last_extras = {}
        return coherent.iloc[-20:].copy() if period == '1mo' else coherent.copy()
    a._download_closes = download
    result = a.fetch()
    assert calls == [(names, '4y')]
    pd.testing.assert_frame_equal(pd.read_parquet(a.cache_path), coherent, check_freq=False)
    assert result['breadth'].iloc[-1]['pct_above_200'] == 100
    assert result['sector_breadth'].iloc[-1]['Tech|pct_above_200'] == 100


def test_failed_full_vintage_download_preserves_existing_cache(tmp_path):
    a = BreadthAdapter.__new__(BreadthAdapter)
    a.cfg = {'lookback_days_live': 1100}
    a.cache_path = tmp_path / '_closes_cache.parquet'
    original = b'retained cache, never a fallback success'
    a.cache_path.write_bytes(original)
    names = [f'T{i:03}' for i in range(400)]
    a.constituents = lambda: pd.DataFrame({'symbol': names})
    calls = []
    def download(tickers, period):
        calls.append(period)
        raise RuntimeError('provider unavailable')
    a._download_closes = download
    with pytest.raises(RuntimeError, match='provider unavailable'):
        a.fetch()
    assert calls == ['4y']
    assert a.cache_path.read_bytes() == original


@pytest.mark.parametrize('case', ['short20', 'short60', 'short199', 'short250', 'one_full', 'stale', 'threshold', 'complete', 'early_gaps'])
@pytest.mark.parametrize('runner', [False, True])
def test_replacement_window_admission_precedes_all_writes(tmp_path, monkeypatch, case, runner):
    from collectors import breadth as module, base
    from lib import config, store
    monkeypatch.setattr(config, 'data_dir', lambda: tmp_path)
    monkeypatch.setattr(config, 'ROOT', tmp_path)
    monkeypatch.setattr(config, 'load', lambda: {'storage': {'run_status_file': 'run_status.json'}})
    names = [f'T{i:03}' for i in range(400)]
    dates = pd.bdate_range(end=pd.Timestamp.now().normalize(), periods=260)
    values = np.full((260, 400), 99.0); values[-1] = 99.5
    old = pd.DataFrame(values, index=dates, columns=names)
    fresh = old.copy()
    if case.startswith('short'):
        fresh = fresh.tail(int(case[5:]))
    elif case == 'one_full':
        fresh.iloc[:-60, 1:] = np.nan
    elif case == 'stale':
        fresh.index = fresh.index - pd.Timedelta(days=28)
    elif case == 'threshold':
        fresh = fresh.iloc[:, :320]
    elif case == 'early_gaps':
        fresh.iloc[:10, :10] = np.nan
    a = BreadthAdapter.__new__(BreadthAdapter)
    a.cfg = {'lookback_days_live':1100, 'ma_windows':[50,200], 'nhnl_window':252}
    a.ycfg = {'batch_size':80, 'retries':2, 'backoff_base_s':0}
    a.cache_path = tmp_path/'_closes_cache.parquet'
    members = pd.DataFrame({'symbol':names, 'name':names, 'sector':['Tech']*400})
    a.constituents = lambda: members.copy()
    old.to_parquet(a.cache_path)
    original = a.cache_path.read_bytes()
    constituents = tmp_path/'constituents.parquet'
    constituents.write_bytes(b'previous membership')
    extras = tmp_path/'_high_cache.parquet'
    extras.write_bytes(b'previous extras')
    calls=[]
    def download(batch, **kw):
        calls.append(kw['period'])
        f = fresh[[n for n in batch if n in fresh.columns]]
        return pd.concat({'Close':f}, axis=1)
    monkeypatch.setattr(module.yf, 'download', download)
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    reject = case not in ('threshold', 'complete', 'early_gaps')
    if runner:
        for key, frame in {'breadth':a.compute(old), 'sector_breadth':a.compute_sectors(old,members)}.items():
            store.upsert(a.group,key,frame)
        aggregate = tmp_path/'breadth/breadth.parquet'
        aggregate_before=aggregate.read_bytes()
        receipt=base.run_adapter(a)
        assert receipt.status == ('failed' if reject else 'ok')
        if reject: assert aggregate.read_bytes()==aggregate_before
    elif reject:
        with pytest.raises(RuntimeError, match='temporal coverage|precedes retained'):
            a.fetch()
    else:
        result=a.fetch()
        assert result['breadth'].iloc[-1]['pct_above_200']==100
    assert calls and set(calls)=={'4y'}
    if reject:
        assert a.cache_path.read_bytes()==original
        assert constituents.read_bytes()==b'previous membership'
        assert extras.read_bytes()==b'previous extras'
    else:
        pd.testing.assert_frame_equal(pd.read_parquet(a.cache_path), fresh, check_freq=False)

@pytest.mark.parametrize('full_history, windows, nhnl, should_refuse', [
    (True, [50,200], 252, False),
    (False, [50,300], 252, True),
    (False, [50,200], 300, True),
])
def test_window_admission_uses_config_and_preserves_full_history(tmp_path, monkeypatch, full_history, windows, nhnl, should_refuse):
    from lib import config
    monkeypatch.setattr(config, 'data_dir', lambda: tmp_path)
    names=[f'T{i:03}' for i in range(400)]
    a=BreadthAdapter.__new__(BreadthAdapter)
    a.cfg={'lookback_days_live':1100, 'ma_windows':windows, 'nhnl_window':nhnl}
    a.cache_path=tmp_path/'_closes_cache.parquet'
    a.cache_path.write_bytes(b'original cache')
    a.constituents=lambda: pd.DataFrame({'symbol':names,'name':names,'sector':['Tech']*400})
    rows=20 if full_history else 260
    frame=pd.DataFrame(99.0,index=pd.bdate_range(end=pd.Timestamp.now().normalize(),periods=rows),columns=names)
    calls=[]
    def download(tickers, period):
        calls.append(period)
        return frame
    a._download_closes=download
    if should_refuse:
        with pytest.raises(RuntimeError,match='temporal coverage'):
            a.fetch(full_history=full_history)
    else:
        assert a.fetch(full_history=True)['breadth'].empty
    assert a.cache_path.read_bytes()==b'original cache'
    assert calls==(['max'] if full_history else ['4y'])
