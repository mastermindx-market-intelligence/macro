"""Isolated R10 benchmark-freshness experiments — synthetic sources, no provider I/O."""
import numpy as np
import pandas as pd
import pytest
from engine import intl_performance as P


def _prices(end, *, n=315, seed=4):
    idx = pd.bdate_range(end=end, periods=n)
    values = 100 * np.exp(np.cumsum(np.random.default_rng(seed).normal(.0005,.006,n)))
    return pd.DataFrame({"close": values}, index=idx)


def _intl_frame():
    idx=pd.bdate_range(end="2026-10-14",periods=315)
    return pd.DataFrame({"^N225": np.linspace(100,175,len(idx)),"^KS11":np.linspace(103,150,len(idx))},index=idx)

@pytest.mark.parametrize("primary_date,spy_date,expected_ticker,need_note", [
    ("2026-10-14", None, "^GSPC", False),
    ("2026-09-01", "2026-10-13", "SPY", True),
    ("2026-09-01", "2026-09-03", None, True),
    ("2026-09-01", None, None, True),
    (None, "2026-10-13", "SPY", True),
    (None, None, None, True),
    ("2026-10-16", "2026-10-13", "SPY", True),
])
def test_r10_benchmark_source_admission(monkeypatch,primary_date,spy_date,expected_ticker,need_note):
    feeds={"^GSPC":_prices(primary_date,seed=41) if primary_date else None,
           "SPY":_prices(spy_date,seed=42) if spy_date else None}
    monkeypatch.setattr(P,"_pcfg",lambda:{"benchmark":"^GSPC"})
    monkeypatch.setattr(P.store,"read",lambda area,ticker: feeds[ticker] if area=="yahoo" else None)
    result,note=P._bench_series_fresh(_intl_frame())
    if expected_ticker is None:
        assert result is None, f"unqualified source returned with date {result.index[-1]}"
    else:
        assert result is not None
        assert result.equals(feeds[expected_ticker]["close"])
    assert bool(note)==need_note


def test_r10_benchmark_withheld_on_missing_reference_clock(monkeypatch):
    monkeypatch.setattr(P,"_pcfg",lambda:{"benchmark":"^GSPC"})
    monkeypatch.setattr(P.store,"read",lambda area,ticker: _prices("2026-10-14"))
    series,note=P._bench_series_fresh(pd.DataFrame())
    assert series is None and note


def test_r10_explicitly_withheld_cannot_reload_raw_benchmark(monkeypatch):
    def forbidden():
        raise AssertionError("raw benchmark reload defeats saved freshness refusal")
    monkeypatch.setattr(P,"_bench_series",forbidden)
    frame=_intl_frame()
    assert P.relative_to_us(closes=frame,bench=None,usd_map={}) is None
    result=P.correlation_matrix(closes=frame,bench=None,usd_map={})
    assert result is None or "US" not in result["order"]


def test_r10_missing_argument_uses_checked_benchmark_not_raw_loader(monkeypatch):
    frame=_intl_frame()
    def forbidden():
        raise AssertionError("raw US benchmark loader is not source-qualified")
    calls=[]
    def qualified(*,intl_closes):
        calls.append(intl_closes)
        return None,"benchmark withheld"
    monkeypatch.setattr(P,"_bench_series",forbidden)
    monkeypatch.setattr(P,"_bench_series_fresh",qualified)
    assert P.relative_to_us(closes=frame,usd_map={}) is None
    assert P.correlation_matrix(closes=frame,usd_map={}) is None
    assert len(calls)==2


def test_r10_performance_panel_does_not_resurrect_withheld_benchmark(monkeypatch):
    frame=_intl_frame()
    idx=frame.index
    usd={"JP":pd.Series(np.linspace(100,160,len(idx)),index=idx),
         "KR":pd.Series(125+np.sin(np.arange(len(idx))/7.)*5+np.arange(len(idx))*.1,index=idx),
         "TW":pd.Series(145+np.cos(np.arange(len(idx))/4.)*6+np.arange(len(idx))*.07,index=idx)}
    monkeypatch.setattr(P,"_usd_map",lambda close:usd)
    monkeypatch.setattr(P,"usd_leaderboard",lambda close,usd_map:[])
    monkeypatch.setattr(P,"risk_appetite",lambda close,usd_map,extra_closes,states:None)
    monkeypatch.setattr(P,"global_read",lambda records,board,rrg,risk:None)
    monkeypatch.setattr(P,"_bench_series_fresh",lambda intl_closes:(None,"stale ^GSPC and SPY withheld"))
    def forbidden():raise AssertionError("unqualified raw benchmark reloaded")
    monkeypatch.setattr(P,"_bench_series",forbidden)
    panel=P.performance_panel(closes=frame,records=[])
    assert panel["bench"] is None and panel["bench_note"]
    assert panel["rrg"] is None
    assert panel["correlation"] is not None
    assert "US" not in panel["correlation"]["order"]
    assert set(panel["correlation"]["order"])=={"JP","KR","TW"}


@pytest.mark.parametrize("primary_date,qualified", [
    ("2026-10-07", True),  # exactly five business days before Oct 14
    ("2026-10-06", False), # six business days is not current
])
def test_r10_benchmark_five_business_day_boundary(monkeypatch, primary_date, qualified):
    primary = _prices(primary_date)
    monkeypatch.setattr(P, "_pcfg", lambda: {"benchmark": "^GSPC"})
    monkeypatch.setattr(P.store, "read",
                        lambda area, ticker: primary if area == "yahoo" and ticker == "^GSPC" else None)
    result, note = P._bench_series_fresh(_intl_frame())
    assert (result is not None) == qualified
    assert (note is None) == qualified


def test_r10_flat_positive_index_observation_still_has_a_clock(monkeypatch):
    # Zero return is valid, but a zero *price level* is not an index close.
    # Repeated positive closes prove a real dated observation, without a gain.
    frame = pd.DataFrame({"^N225": [100.0, 100.0]},
                         index=pd.DatetimeIndex(["2026-10-13", "2026-10-14"]))
    primary = _prices("2026-10-14")
    monkeypatch.setattr(P, "_pcfg", lambda: {"benchmark": "^GSPC"})
    monkeypatch.setattr(P.store, "read",
                        lambda area, ticker: primary if area == "yahoo" and ticker == "^GSPC" else None)
    result, note = P._bench_series_fresh(frame)
    assert result is not None and note is None


def test_r10_exchange_local_dates_do_not_require_same_time_zone(monkeypatch):
    # Two independently dated EOD stores can carry different intraday/tz values
    # for the same calendar day. Compare their local observation dates, not instants.
    frame = _intl_frame()
    frame.index = frame.index.tz_localize("Asia/Tokyo")
    primary = _prices("2026-10-14")
    primary.index = primary.index.tz_localize("America/New_York") + pd.Timedelta(hours=16)
    monkeypatch.setattr(P, "_pcfg", lambda: {"benchmark": "^GSPC"})
    monkeypatch.setattr(P.store, "read",
                        lambda area, ticker: primary if area == "yahoo" and ticker == "^GSPC" else None)
    result, note = P._bench_series_fresh(frame)
    assert result is not None and note is None


def test_r10_untyped_international_clock_withholds_without_raw_reload(monkeypatch):
    monkeypatch.setattr(P, "_pcfg", lambda: {"benchmark": "^GSPC"})
    def forbidden(*args):
        raise AssertionError("untyped calendar cannot admit any source")
    monkeypatch.setattr(P.store, "read", forbidden)
    frame = pd.DataFrame({"^N225": [100.0]}, index=["2026-10-14"])
    result, note = P._bench_series_fresh(frame)
    assert result is None and "clock unavailable" in note


def test_r10_stale_source_disclosure_contains_both_actual_dates(monkeypatch):
    primary, spy = _prices("2026-09-01"), _prices("2026-09-03")
    monkeypatch.setattr(P, "_pcfg", lambda: {"benchmark": "^GSPC"})
    monkeypatch.setattr(P.store, "read",
                        lambda area, ticker: {"^GSPC": primary, "SPY": spy}[ticker])
    result, note = P._bench_series_fresh(_intl_frame())
    assert result is None
    assert "2026-09-01" in note and "2026-09-03" in note
    assert "2026-10-14" in note


@pytest.mark.parametrize("bad_close", [0.0, -1.0, float("inf"), float("-inf")])
def test_r10_bad_current_benchmark_price_cannot_admit_relative_claims(monkeypatch, bad_close):
    primary = _prices("2026-10-14")
    primary.iloc[-1, 0] = bad_close
    monkeypatch.setattr(P, "_pcfg", lambda: {"benchmark": "^GSPC"})
    monkeypatch.setattr(P.store, "read",
                        lambda area, ticker: primary if area == "yahoo" and ticker == "^GSPC" else None)
    series, note = P._bench_series_fresh(_intl_frame())
    assert series is None and "withheld" in note


def test_r10_non_numeric_benchmark_prices_fail_closed(monkeypatch):
    primary = _prices("2026-10-14")
    primary["close"] = primary["close"].astype(object)
    primary.iloc[-1, 0] = "unqualified source"
    monkeypatch.setattr(P, "_pcfg", lambda: {"benchmark": "^GSPC"})
    monkeypatch.setattr(P.store, "read",
                        lambda area, ticker: primary if area == "yahoo" and ticker == "^GSPC" else None)
    series, note = P._bench_series_fresh(_intl_frame())
    assert series is None and "withheld" in note


@pytest.mark.parametrize("bad_index_price", [0.0, -2.0, float("inf"), float("-inf")])
@pytest.mark.parametrize("late_fx_only", [False, True])
def test_r10_invalid_trailing_index_close_cannot_advance_clock(
        monkeypatch, bad_index_price, late_fx_only):
    # Actual _intl_closes carries primary equity indexes and FX legs. The US
    # comparator's date must come from a *valid equity close*, not a zero/inf
    # pseudo-bar nor an FX-only update on a later calendar day.
    fx = P.intl_inputs.countries()["JP"]["fx"]
    columns = {"^N225": [110.0, bad_index_price]}
    if late_fx_only:
        columns[fx] = [145.0, 146.0]
    frame = pd.DataFrame(columns, index=pd.DatetimeIndex([
        "2026-10-09", "2026-10-26"]))
    primary = _prices("2026-10-09")
    monkeypatch.setattr(P, "_pcfg", lambda: {"benchmark": "^GSPC"})
    monkeypatch.setattr(P.store, "read",
                        lambda area, ticker: primary if area == "yahoo" and ticker == "^GSPC" else None)
    result, note = P._bench_series_fresh(frame)
    assert result is not None and result.equals(primary["close"])
    assert note is None


def test_r10_valid_later_primary_close_really_advances_clock(monkeypatch):
    frame = pd.DataFrame({"^N225": [110.0, 112.0]},
                         index=pd.DatetimeIndex(["2026-10-09", "2026-10-26"]))
    primary = _prices("2026-10-09")
    monkeypatch.setattr(P, "_pcfg", lambda: {"benchmark": "^GSPC"})
    monkeypatch.setattr(P.store, "read",
                        lambda area, ticker: primary if area == "yahoo" and ticker == "^GSPC" else None)
    result, note = P._bench_series_fresh(frame)
    assert result is None and "2026-10-26" in note


def test_r10_fx_only_clock_is_not_an_equity_benchmark_comparison(monkeypatch):
    fx = P.intl_inputs.countries()["JP"]["fx"]
    frame = pd.DataFrame({fx: [145.0]},
                         index=pd.DatetimeIndex(["2026-10-14"]))
    primary = _prices("2026-10-14")
    monkeypatch.setattr(P, "_pcfg", lambda: {"benchmark": "^GSPC"})
    monkeypatch.setattr(P.store, "read",
                        lambda area, ticker: primary if area == "yahoo" and ticker == "^GSPC" else None)
    result, note = P._bench_series_fresh(frame)
    assert result is None and "clock unavailable" in note
