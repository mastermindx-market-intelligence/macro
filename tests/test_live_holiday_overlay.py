"""A holiday must never create a new daily bar or a fresh actionable quote."""
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from engine import live_overlay as lo
from engine import live_quotes as lq


def _fixture(asof="2026-09-30"):
    close = pd.Series(np.linspace(80, 100, 100),
                      index=pd.bdate_range(end=asof, periods=100))
    baseline = {"ticker": "600519.SS", "asof": asof,
                "tech": {"price": 100.0, "rsi14": 55.0},
                "conviction": {"score": 71, "verdict": "Own it", "size": {"pct": 4.0}}}
    return baseline, close


def _quote(now, price=110.0):
    return {"price": price, "source": "tencent", "price_basis": "trade",
            "quote_ts": now.isoformat(), "delay_min": 0.0, "prev_close": 100.0}


def test_fresh_vendor_refresh_on_cn_holiday_retains_observation_and_no_signal():
    now = datetime(2026, 10, 7, 3, tzinfo=timezone.utc)
    baseline, close = _fixture()
    saved = close.copy()
    quote = _quote(now)
    rec = lo.build_ticker_overlay("600519.SS", baseline, quote, close, 20, now)
    assert rec["price"] == 100.0
    assert rec["tech"] == baseline["tech"]
    pd.testing.assert_series_equal(close, saved)
    assert rec["data_through"] == "2026-09-30"
    assert rec["quote_ts"] == quote["quote_ts"]
    assert rec["data_frozen"] is True
    assert rec["data_state"] == "current"
    assert rec["baseline_stale"] is False
    assert rec["session_state"] == "holiday"
    assert rec["stale"] is True  # carried observation is not a live trade
    assert rec["divergence"]["severity"] == "info"
    merged = lo.merge_baseline(baseline, rec)
    assert merged["act_on_live"] is False
    assert merged["conviction"] == 71
    assert merged["as_of_baseline"] == "2026-09-30"
    assert merged["data_state"] == "current"
    assert merged["data_frozen"] is True


@pytest.mark.parametrize("asof,state", [("2026-09-29", "late"), ("2026-10-01", "invalid")])
def test_holiday_does_not_promote_old_or_invalid_baseline(asof, state):
    now = datetime(2026, 10, 7, 3, tzinfo=timezone.utc)
    baseline, close = _fixture(asof)
    rec = lo.build_ticker_overlay("600519.SS", baseline, _quote(now), close, 20, now)
    assert rec["data_state"] == state
    assert rec["baseline_stale"] is True
    assert rec["data_through"] == asof
    assert rec["price"] == 100.0
    assert rec["stale"] is True


def test_holiday_with_no_history_never_claims_healthy_retained_data():
    now = datetime(2026, 10, 7, 3, tzinfo=timezone.utc)
    baseline, _ = _fixture()
    rec = lo.build_ticker_overlay("600519.SS", baseline, _quote(now), None, 20, now)
    assert rec["data_state"] == "missing"
    assert rec["baseline_stale"] is True


def test_holiday_bad_print_keeps_rejection_visible():
    now = datetime(2026, 10, 7, 3, tzinfo=timezone.utc)
    baseline, close = _fixture()
    rec = lo.build_ticker_overlay("600519.SS", baseline, _quote(now, 300), close, 20, now)
    assert rec["divergence"]["flag"] == "bad_print"
    assert rec["data_state"] == "current"
    assert rec["quote_state"] == "invalid"
    assert "bad print" in rec["stale_reason"]


@pytest.mark.parametrize("clock", ["real", "synthetic", "missing", "malformed", "future"])
def test_bad_print_keeps_independent_quote_clock_integrity(clock):
    now = datetime(2026, 10, 8, 2, tzinfo=timezone.utc)
    baseline, close = _fixture()
    quote = _quote(now, 300)
    if clock == "synthetic":
        quote["quote_ts_synthetic"] = True
    elif clock == "missing":
        quote["quote_ts"] = None
    elif clock == "malformed":
        quote["quote_ts"] = "not-a-time"
    elif clock == "future":
        quote["quote_ts"] = "2026-10-09T02:00:00+00:00"
    rec = lo.build_ticker_overlay("600519.SS", baseline, quote, close, 20, now)
    assert rec["quote_clock_invalid"] is (clock != "real")
    assert rec["quote_state"] == "invalid"
    assert rec["divergence"]["flag"] == "bad_print"
    assert rec["data_state"] == "current" and rec["price"] == 100.0


def test_reopened_cn_tape_uses_local_session_date_without_holiday_baseline_age():
    now = datetime(2026, 10, 8, 2, tzinfo=timezone.utc)
    baseline, close = _fixture()
    rec = lo.build_ticker_overlay("600519.SS", baseline, _quote(now, 101), close, 20, now)
    assert rec["session_open"] is True
    assert rec["data_frozen"] is False
    assert rec["baseline_stale"] is False
    assert rec["price"] == 101.0


@pytest.mark.parametrize("symbol", ["BTC-USD", "ES=F", "USDCNY=X", "7203.T"])
def test_closed_us_calendar_never_freezes_other_asset_classes(symbol):
    now = datetime(2026, 7, 3, 15, tzinfo=timezone.utc)
    baseline, close = _fixture("2026-07-02")
    rec = lo.build_ticker_overlay(symbol, baseline, _quote(now, 101), close, 20, now)
    assert rec.get("data_frozen", False) is False
    assert rec["stale"] is False
    assert rec["price"] == 101.0


@pytest.mark.parametrize("region,instant,state", [
    ("cn", "2026-10-07T03:00:00+00:00", "holiday"),
    ("hk", "2026-10-07T03:00:00+00:00", "open"),
    ("connect", "2026-10-07T03:00:00+00:00", "holiday"),
    ("us", "2026-11-27T18:00:00+00:00", "postclose"),
    ("ca", "2026-12-28T16:00:00+00:00", "holiday"),
])
def test_incumbent_live_session_routes_through_verified_calendar(region, instant, state):
    result = lo.market_session(region, datetime.fromisoformat(instant))
    assert result["state"] == state
    assert result["calendar_verified"] is True


@pytest.mark.parametrize("instant,want", [
    ("2026-07-03T15:00:00+00:00", True),
    ("2026-11-27T17:59:00+00:00", False),
    ("2026-11-27T18:00:00+00:00", True),
    ("2026-12-24T18:00:00+00:00", True),
    ("2026-10-12T15:00:00+00:00", False),
])
def test_us_settle_routing_respects_exchange_holidays_and_half_days(instant, want):
    assert lq._us_settle_window(datetime.fromisoformat(instant)) is want


def test_quote_timestamp_age_cannot_be_reset_by_vendor_delay_hint():
    now = datetime(2026, 10, 8, 3, tzinfo=timezone.utc)
    stale_quote = _quote(datetime(2026, 9, 30, 7, tzinfo=timezone.utc))
    result = lo.staleness(stale_quote, 20, now, session_open=True)
    assert result["stale"] is True
    assert result["age_min"] > 1000


def test_future_quote_timestamp_is_invalid_even_with_zero_vendor_delay():
    now = datetime(2026, 10, 8, 3, tzinfo=timezone.utc)
    quote = _quote(datetime(2026, 10, 9, 3, tzinfo=timezone.utc))
    result = lo.staleness(quote, 20, now, session_open=True)
    assert result["stale"] is True


@pytest.mark.parametrize("symbol,closed", [("600519.SS", True), ("0700.HK", False),
                                           ("ES=F", False), ("BTC-USD", False)])
def test_allocation_mark_cannot_bypass_cash_holiday(symbol, closed):
    from scripts.build_live_overlay import _usable_mark
    now = datetime(2026, 10, 7, 3, tzinfo=timezone.utc)
    price, change, stale = _usable_mark(_quote(now, 101), 100, 20, 35, now, symbol=symbol)
    assert stale is closed
    if closed:
        assert price is None and change is None
    else:
        assert price == 101.0


def test_market_context_carries_real_data_date_and_market_closure(monkeypatch):
    from scripts import build_live_overlay as builder
    now = datetime(2026, 7, 3, 15, tzinfo=timezone.utc)
    _, close = _fixture("2026-07-02")
    monkeypatch.setattr(builder.config, "load", lambda: {"live": {"market_context": ["SPY"]}})
    monkeypatch.setattr(builder.live_overlay, "read_close", lambda symbol: close)
    rec = builder._market_context({"SPY": _quote(now, 110)}, 20, 35, now)["SPY"]
    assert rec["price"] == 100.0
    assert rec["stale"] is True
    assert rec["data_frozen"] is True
    assert rec["data_through"] == "2026-07-02"


@pytest.mark.parametrize("kind", ["missing", "synthetic"])
def test_reopened_cash_tape_requires_a_real_observation_clock(kind):
    now = datetime(2026, 10, 8, 3, tzinfo=timezone.utc)
    baseline, close = _fixture()
    quote = _quote(now, 110)
    if kind == "missing":
        quote.pop("quote_ts")
    else:
        quote["quote_ts_synthetic"] = True
    rec = lo.build_ticker_overlay("600519.SS", baseline, quote, close, 20, now)
    assert rec["price"] == 100.0
    assert rec["stale"] is True
    assert rec["quote_state"] == "invalid"
    assert rec["data_state"] == "current"
    assert lo.merge_baseline(baseline, rec)["act_on_live"] is False


def test_polygon_synthetic_refresh_clock_cannot_mark_a_cash_allocation():
    from scripts.build_live_overlay import _usable_mark
    now = datetime(2026, 7, 6, 15, tzinfo=timezone.utc)
    raw = lq.parse_polygon_snapshot({"tickers": [
        {"ticker": "AAPL", "lastTrade": {"p": 110.0}, "prevDay": {"c": 100.0}}
    ]}, now)
    assert raw["AAPL"]["quote_ts_synthetic"] is True
    assert _usable_mark(raw["AAPL"], 100, 20, 35, now, symbol="AAPL") == (None, None, True)


def test_worker_snapshot_preserves_synthetic_timestamp_warning():
    from scripts.build_live_quotes import to_worker_quotes
    now = datetime(2026, 7, 6, 15, tzinfo=timezone.utc)
    quote = {**_quote(now), "quote_ts_synthetic": True}
    out = to_worker_quotes({"AAPL": quote})["AAPL"]
    assert out["ts"] is None
    assert out["tsSynthetic"] is True


def test_canonical_hk_region_matches_the_session_for_configured_indices():
    assert lo.region_for("^HSCC") == "hk"
    assert lo.region_for("^HSIL") == "hk"


def test_holiday_baseline_does_not_hide_missing_history():
    now = datetime(2026, 10, 7, 3, tzinfo=timezone.utc)
    baseline, close = _fixture()
    close = close.loc[:"2026-09-23"]
    rec = lo.build_ticker_overlay("600519.SS", baseline, _quote(now), close, 20, now)
    assert rec["data_state"] == "late"
    assert rec["history_through"] == "2026-09-23"
    assert rec["baseline_data_state"] == "current"
    assert rec["baseline_stale"] is True
    assert rec["price"] == 100.0


def test_reopen_technicals_exclude_old_phantom_holiday_rows():
    now = datetime(2026, 10, 8, 3, tzinfo=timezone.utc)
    baseline, close = _fixture()
    contaminated = close.copy()
    contaminated.loc[pd.Timestamp("2026-10-05")] = 500.0
    clean_rec = lo.build_ticker_overlay("600519.SS", baseline, _quote(now, 101), close, 20, now)
    dirty_rec = lo.build_ticker_overlay("600519.SS", baseline, _quote(now, 101), contaminated, 20, now)
    assert dirty_rec["tech"] == clean_rec["tech"]
    assert contaminated.loc[pd.Timestamp("2026-10-05")] == 500.0  # projection only


@pytest.mark.parametrize("symbol,group", [("600519.SS", "china"), ("0700.HK", "hk"), ("XIU.TO", "canada")])
def test_live_reader_reuses_regional_daily_store(tmp_path, monkeypatch, symbol, group):
    from lib import config
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    (tmp_path / group).mkdir()
    pd.DataFrame({"close": [100.0]}, index=pd.to_datetime(["2026-09-30"])).to_parquet(
        tmp_path / group / (symbol.replace("/", "_") + ".parquet"))
    out = lo.read_close(symbol)
    assert out is not None and float(out.iloc[-1]) == 100.0


def test_canadian_wide_cache_is_available_to_live_reader(tmp_path, monkeypatch):
    from lib import config
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    (tmp_path / "canada_search").mkdir()
    pd.DataFrame({"RY.TO": [120.0]}, index=pd.to_datetime(["2026-09-30"])).to_parquet(
        tmp_path / "canada_search" / "closes.parquet")
    out = lo.read_close("RY.TO")
    assert out is not None and float(out.iloc[-1]) == 120.0


def test_regional_reader_selects_a_whole_freshest_adjustment_basis(tmp_path, monkeypatch):
    from lib import config
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    (tmp_path / "china_search").mkdir()
    (tmp_path / "china_stocks").mkdir()
    pd.DataFrame({"600519.SS": [99.0, 100.0]}, index=pd.to_datetime(["2026-09-29", "2026-09-30"])).to_parquet(
        tmp_path / "china_search" / "closes.parquet")
    pd.DataFrame({"close": [49.0, 49.5]}, index=pd.to_datetime(["2026-09-28", "2026-09-29"])).to_parquet(
        tmp_path / "china_stocks" / "600519.SS.parquet")
    out = lo.read_close("600519.SS")
    assert out is not None and out.tolist() == [99.0, 100.0]
    assert out.index[0] == pd.Timestamp("2026-09-29")


@pytest.mark.parametrize("symbol,directory", [("600519.SS", "chinastockdata"), ("0700.HK", "hkstockdata"),
                                              ("RY.TO", "canadastockdata")])
def test_live_baseline_uses_the_regional_metadata_owner(tmp_path, monkeypatch, symbol, directory):
    import json
    from scripts import build_live_overlay as builder
    monkeypatch.setattr(builder.config, "ROOT", tmp_path)
    monkeypatch.setattr(builder.config, "load", lambda: {"storage": {"site_dir": "site"}})
    path = tmp_path / "site" / directory
    path.mkdir(parents=True)
    baseline = {"ticker": symbol, "asof": "2026-09-30", "tech": {"price": 100.0}, "regional": True}
    (path / (symbol + ".json")).write_text(json.dumps(baseline))
    assert builder._load_baseline(symbol, None) == baseline


@pytest.mark.parametrize("symbol", ["AAPL", "BTC-USD"])
def test_existing_us_and_noncash_reader_keeps_yahoo_precedence(tmp_path, monkeypatch, symbol):
    from lib import config
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    for group, day, value in [("yahoo", "2026-09-29", 100.0), ("stocks", "2026-09-30", 50.0)]:
        (tmp_path / group).mkdir()
        pd.DataFrame({"close": [value]}, index=pd.to_datetime([day])).to_parquet(
            tmp_path / group / (symbol + ".parquet"))
    result = lo.read_close(symbol)
    assert result.tolist() == [100.0]
    assert str(result.index[-1].date()) == "2026-09-29"


@pytest.mark.parametrize("symbol", ["ES=F", "USDCNY=X", "BTC-USD"])
def test_noncash_overlay_does_not_assert_a_us_cash_closure(symbol):
    now = datetime(2026, 7, 3, 15, tzinfo=timezone.utc)
    close = pd.Series([100.0] * 80, index=pd.bdate_range(end="2026-07-02", periods=80))
    baseline = {"ticker": symbol, "asof": "2026-07-02", "tech": {"price": 100.0}}
    quote = {"price": 101.0, "quote_ts": now.isoformat(), "delay_min": 0, "source": "fixture"}
    rec = lo.build_ticker_overlay(symbol, baseline, quote, close, 20, now)
    assert rec["session_open"] is None
    assert rec.get("data_frozen", False) is False
    assert rec["stale"] is False
    assert rec["price"] == 101.0


def test_minutely_quote_snapshot_carries_all_market_status_during_asia_hours(tmp_path, monkeypatch):
    from scripts import build_live_quotes as builder
    class AsiaClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 7, 3, tzinfo=timezone.utc)
    monkeypatch.setattr(builder, "datetime", AsiaClock)
    monkeypatch.setattr(builder.config, "load", lambda: {"live": {}})
    requests = []
    def fetch(symbols, **kwargs):
        requests.append(symbols)
        return {}
    monkeypatch.setattr(builder.live_quotes, "fetch_quotes", fetch)
    snapshot = builder.build(tmp_path, symbols=["0700.HK", "600519.SS"])
    assert requests == [["0700.HK", "600519.SS"]]  # no additional provider requests
    assert snapshot["sessions"]["hk"]["state"] == "open"
    assert snapshot["sessions"]["cn"]["state"] == "holiday"
    assert snapshot["sessions"]["connect"]["state"] == "holiday"
    assert snapshot["sessions"]["cn"]["expected_session"] == "2026-09-30"
    assert set(snapshot["sessions"]) == {"us", "cn", "hk", "ca", "connect"}
