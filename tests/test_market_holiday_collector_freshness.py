"""Cash-session retention and health regressions over synthetic, isolated stores."""
from datetime import date, datetime, timezone

import pandas as pd
import pytest

from collectors import base
from engine import hk_freshness, tushare_freshness

NOW = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW if tz else NOW.replace(tzinfo=None)


def frame(day, value=1):
    return pd.DataFrame({"close": [value]}, index=pd.to_datetime([day]))


@pytest.fixture
def runner(monkeypatch):
    saved = {}
    writes = []
    monkeypatch.setattr(base, "datetime", Clock)
    monkeypatch.setattr(base, "_breaker_state", lambda: {})
    monkeypatch.setattr(base, "_write_stale_series", lambda rows: None)
    monkeypatch.setattr(base, "_emit_dark_columns", lambda rows: [])
    monkeypatch.setattr(base.store, "read", lambda group, name: saved.get((group, name)))

    def upsert(group, name, df, **kwargs):
        writes.append((name, df.copy()))
        old = saved.get((group, name))
        merged = df.combine_first(old) if old is not None else df
        saved[group, name] = merged
        return merged

    monkeypatch.setattr(base.store, "upsert", upsert)
    return saved, writes


def adapter(frames, market="CN"):
    class Cash(base.Adapter):
        name = "test_cash"
        group = "test_cash"
        session_calendar = market
        stale_after_days = 1

        def fetch(self, full_history=False):
            return frames

    return Cash()


def test_closed_cn_retain_last_good_without_holiday_or_future_write(runner):
    saved, writes = runner
    saved["test_cash", "daily"] = frame("2026-09-30", 7)
    incoming = pd.concat([frame("2026-10-07", 9), frame("2026-10-08", 10)])
    result = base.run_adapter(adapter({"daily": incoming}))
    assert writes == []
    assert saved["test_cash", "daily"].iloc[-1, 0] == 7
    assert result.status == "ok" and result.last_date == "2026-09-30"
    assert result.rows == 0 and result.notes


def test_closed_cn_does_not_hide_preholiday_outage(runner):
    saved, writes = runner
    saved["test_cash", "daily"] = frame("2026-09-23")
    result = base.run_adapter(adapter({"daily": frame("2026-10-07")}))
    assert result.status == "stale" and writes == []


def test_closed_cn_no_prior_data_is_not_ok(runner):
    _, writes = runner
    result = base.run_adapter(adapter({"daily": frame("2026-10-07")}))
    assert result.status == "stale" and result.last_date is None and writes == []


def test_valid_open_hk_observation_and_corrections_continue(runner):
    _, writes = runner
    result = base.run_adapter(adapter({"daily": frame("2026-10-07")}, "HK"))
    assert result.status == "ok" and len(writes) == 1
    assert writes[0][1].index.max().date() == date(2026, 10, 7)


def test_valid_developing_hk_row_is_not_discarded(runner, monkeypatch):
    monkeypatch.setattr(Clock, "now", classmethod(lambda cls, tz=None: datetime(2026, 10, 7, 3, tzinfo=timezone.utc)))
    result = base.run_adapter(adapter({"daily": frame("2026-10-07")}, "HK"))
    assert result.status == "ok" and len(runner[1]) == 1


def test_vendor_error_stays_failed_during_closure(runner):
    a = adapter({})
    a.fetch = lambda **kwargs: (_ for _ in ()).throw(ValueError("vendor outage"))
    assert base.run_adapter(a).status == "failed"


def test_unopted_operational_heartbeat_keeps_wall_clock(runner):
    a = adapter({"run_log": frame("2026-10-07")}, None)
    result = base.run_adapter(a)
    assert result.status == "ok" and len(runner[1]) == 1


def test_per_series_clock_keeps_mixed_crypto_active(runner):
    a = adapter({"600519.SS": frame("2026-10-07"), "BTC-USD": frame("2026-10-07")}, None)
    a.session_calendar_for_series = lambda name: "CN" if name.endswith(".SS") else None
    base.run_adapter(a)
    assert [name for name, df in runner[1]] == ["BTC-USD"]


def test_frozen_tail_detector_exempts_closure_but_keeps_outage(monkeypatch):
    monkeypatch.setattr(base, "datetime", Clock)
    assert base.detect_stale_series("x", {"daily": frame("2026-09-30")}, 1,
                                   session_calendars={"daily": "CN"}) == []
    rows = base.detect_stale_series("x", {"daily": frame("2026-09-23")}, 1,
                                   session_calendars={"daily": "CN"})
    assert rows and rows[0]["lag_sessions"] == 4


def write_tushare(tmp_path, table, day, col="trade_date"):
    target = tmp_path / "tushare"
    target.mkdir(exist_ok=True)
    pd.DataFrame({col: [day], "value": [1]}).to_parquet(target / f"{table}.parquet")


def test_daily_tushare_current_during_cn_closure(monkeypatch, tmp_path):
    monkeypatch.setattr(tushare_freshness.config, "data_dir", lambda: tmp_path)
    write_tushare(tmp_path, "moneyflow", "20260930")
    badge = tushare_freshness.staleness_badge("moneyflow", ref=pd.Timestamp(NOW))
    assert badge["state"] == "fresh" and badge["lag_sessions"] == 0
    assert badge["lag_days"] == 7


def test_daily_tushare_preholiday_freeze_is_still_stale(monkeypatch, tmp_path):
    monkeypatch.setattr(tushare_freshness.config, "data_dir", lambda: tmp_path)
    write_tushare(tmp_path, "valuation", "20260923")
    badge = tushare_freshness.staleness_badge("valuation", ref=pd.Timestamp(NOW))
    assert badge["state"] == "stale" and badge["lag_sessions"] == 4


def test_periodic_announcement_retains_calendar_cadence(monkeypatch, tmp_path):
    monkeypatch.setattr(tushare_freshness.config, "data_dir", lambda: tmp_path)
    write_tushare(tmp_path, "forecast", "20260930", "ann_date")
    badge = tushare_freshness.staleness_badge("forecast", expected_cadence_days=1, ref=pd.Timestamp(NOW))
    assert badge["state"] == "stale" and badge["lag_days"] == 7
    assert badge.get("lag_sessions") is None


def test_tushare_preference_counts_real_sessions_across_break():
    tv = pd.DataFrame({"trade_date": ["20260930"], "v": [1]})
    free = pd.DataFrame({"date": ["20261008"], "v": [2]})
    assert tushare_freshness.prefer_tushare(tv, free)[1] == "tushare"
    free["date"] = "20261009"
    assert tushare_freshness.prefer_tushare(tv, free)[1] == "free"


def test_hk_badge_counts_sessions_over_easter():
    badge = hk_freshness._badge(date(2026, 4, 2), date(2026, 4, 8))
    assert badge["lag_sessions"] == 1 and badge["lag_days"] == 6
    assert badge["state"] == "slow"


def test_connect_badge_uses_intersection_during_cn_closure():
    badge = hk_freshness._badge(date(2026, 9, 30), date(2026, 9, 30), market="CONNECT")
    assert badge["lag_sessions"] == 0 and badge["state"] == "fresh"


def test_missing_hk_badge_remains_dead():
    assert hk_freshness._badge(None, date(2026, 10, 7))["state"] == "dead"


def fake_hk_sentinel(monkeypatch, tmp_path, *, prices, standouts, regime, holdings):
    monkeypatch.setattr(hk_freshness.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(hk_freshness.config, "ROOT", tmp_path)
    monkeypatch.setattr(hk_freshness.config, "load", lambda: {"storage": {"site_dir": "isolated_site"}})
    monkeypatch.setattr(hk_freshness, "_parquet_index_max",
                        lambda path: holdings if path.name == "holdings.parquet" else prices)
    monkeypatch.setattr(hk_freshness, "_json_field",
                        lambda path, field: str(standouts if field == "as_of" else regime))
    monkeypatch.setattr(hk_freshness, "_load_state", lambda path: {})
    monkeypatch.setattr(hk_freshness, "_save_state", lambda *args: None)


def test_real_hk_sentinel_coherence_skips_easter_closures(monkeypatch, tmp_path):
    fake_hk_sentinel(monkeypatch, tmp_path, prices=date(2026, 4, 8),
                     standouts=date(2026, 4, 8), regime=date(2026, 4, 2), holdings=date(2026, 4, 8))
    result = hk_freshness.hk_freshness_sentinel(datetime(2026, 4, 8, 12, tzinfo=timezone.utc))
    assert result["coherence"]["ok"] is True
    assert result["coherence"]["gap_sessions"] == 1
    assert result["verdict"] == "ok"


def test_real_hk_sentinel_connect_does_not_follow_open_hk_during_cn_break(monkeypatch, tmp_path):
    fake_hk_sentinel(monkeypatch, tmp_path, prices=date(2026, 10, 7),
                     standouts=date(2026, 10, 7), regime=date(2026, 10, 7), holdings=date(2026, 9, 30))
    result = hk_freshness.hk_freshness_sentinel(NOW)
    assert result["stores"]["southbound"]["state"] == "fresh"
    assert result["stores"]["southbound"]["expected_session"] == "2026-09-30"
    assert result["verdict"] == "ok"


def test_canada_tailwind_gate_does_not_count_good_friday(monkeypatch, tmp_path):
    # Execute the actual production function without importing unrelated renderer dependencies.
    import ast
    import logging
    from pathlib import Path
    from lib import config
    source = Path(__file__).parents[1] / "scripts" / "build_canada.py"
    tree = ast.parse(source.read_text())
    target = next(node for node in tree.body
                  if isinstance(node, ast.FunctionDef) and node.name == "_tailwind_freshness_gate")
    scope = {"pd": pd, "config": config, "log": logging.getLogger("canada_test"),
             "_board_asof": lambda latest: "2026-04-08"}
    exec(compile(ast.Module(body=[target], type_ignores=[]), str(source), "exec"), scope)
    search = tmp_path / "canada_search"
    search.mkdir()
    frame("2026-04-02").to_parquet(search / "closes.parquet")
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    setups = {"buy": []}
    assert scope["_tailwind_freshness_gate"](setups, {}) is None
    assert setups["tailwind_stale_days"] == 3
    assert setups["tailwind_suppressed"] is False


def test_correction_for_last_real_session_still_writes_during_closure(runner):
    saved, writes = runner
    saved["test_cash", "daily"] = frame("2026-09-30", 7)
    incoming = pd.concat([frame("2026-09-30", 8), frame("2026-10-07", 9)])
    result = base.run_adapter(adapter({"daily": incoming}))
    assert result.status == "ok" and result.rows == 1
    assert saved["test_cash", "daily"].iloc[-1, 0] == 8
    assert len(writes) == 1 and len(writes[0][1]) == 1


def test_store_basis_rejection_is_not_quieted_by_holiday(runner, monkeypatch):
    monkeypatch.setattr(base.store, "upsert",
                        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("older adjusted basis")))
    result = base.run_adapter(adapter({"daily": frame("2026-09-30")}))
    assert result.status == "failed" and "older adjusted basis" in result.error


def test_real_yahoo_symbol_clock_does_not_gate_futures_or_crypto():
    from collectors.yahoo import YahooAdapter
    adapter = object.__new__(YahooAdapter)
    assert adapter.session_calendar_for_series("600519.SS") == "cn"
    assert adapter.session_calendar_for_series("9988.HK") == "hk"
    assert adapter.session_calendar_for_series("RY.TO") == "ca"
    assert adapter.session_calendar_for_series("SPY") == "us"
    assert adapter.session_calendar_for_series("BTC-USD") is None
    assert adapter.session_calendar_for_series("CL=F") is None
    assert adapter.session_calendar_for_series("EURUSD=X") is None


@pytest.mark.parametrize("stored", [None, "2026-09-23"])
def test_declared_ok_cannot_clear_cash_observation_fault(runner, stored):
    if stored:
        runner[0]["test_cash", "daily"] = frame(stored)
    a = adapter({"daily": frame("2026-10-07")})
    a.fetch_result_status = lambda frames: "ok"
    result = base.run_adapter(a)
    assert result.status == "stale"


def test_non_cash_declared_status_protocol_is_preserved(runner):
    a = adapter({"receipt": frame("2026-09-23")}, None)
    a.fetch_result_status = lambda frames: "ok"
    assert base.run_adapter(a).status == "ok"


def test_unverified_future_calendar_keeps_provider_weekday_with_explicit_note(runner, monkeypatch):
    instant = datetime(2027, 1, 5, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(Clock, "now", classmethod(lambda cls, tz=None: instant))
    saved, writes = runner
    saved["test_cash", "daily"] = frame("2026-12-31", 7)
    a = adapter({"daily": frame("2027-01-01", 9)})
    a.fetch_result_status = lambda frames: "ok"
    result = base.run_adapter(a)
    assert len(writes) == 1 and saved["test_cash", "daily"].iloc[-1, 0] == 9
    assert result.status == "stale" and result.rows == 1
    assert any("unverified calendar" in note for note in result.notes)


def test_unknown_future_observation_dates_do_not_replace_last_good(runner):
    saved, writes = runner
    saved["test_cash", "daily"] = frame("2026-09-30", 7)
    result = base.run_adapter(adapter({"daily": frame("2027-01-05", 9)}))
    assert result.status == "ok" and result.rows == 0
    assert writes == [] and saved["test_cash", "daily"].iloc[-1, 0] == 7


def test_unverified_year_rejects_weekends_future_but_retains_historical_weekdays(runner, monkeypatch):
    instant = datetime(2027, 1, 5, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(Clock, "now", classmethod(lambda cls, tz=None: instant))
    saved, writes = runner
    saved["test_cash", "daily"] = frame("2026-12-31", 7)
    incoming = pd.concat([frame("2027-01-02", 8), frame("2027-01-06", 9), frame("2025-05-01", 10)])
    result = base.run_adapter(adapter({"daily": incoming}))
    assert len(writes) == 1 and result.status == "stale"
    assert writes[0][1].index.tolist() == [pd.Timestamp("2025-05-01")]
    assert result.last_date == "2026-12-31" and result.rows == 1


def test_connect_badge_cannot_use_an_unverified_comparison_calendar():
    now = datetime(2027, 10, 6, 12, tzinfo=timezone.utc)
    badge = hk_freshness._badge(date(2027, 9, 30), date(2027, 9, 30), market="CONNECT", now=now)
    assert badge["state"] == "error"
    assert badge["data_state"] == "unverified"
    assert badge["calendar_verified"] is False
    assert badge["lag_sessions"] is None


def test_hk_badge_accepts_a_real_historical_weekday_without_verified_notice():
    badge = hk_freshness._badge(date(2021, 12, 28), date(2026, 10, 7), now=NOW)
    assert badge["state"] == "stale"
    assert badge["data_state"] == "late"
    assert badge["calendar_verified"] is True


def test_hk_coherence_does_not_promote_an_unverified_calendar(monkeypatch, tmp_path):
    stamp = date(2028, 10, 6)
    fake_hk_sentinel(monkeypatch, tmp_path, prices=stamp, standouts=stamp, regime=stamp, holdings=stamp)
    result = hk_freshness.hk_freshness_sentinel(datetime(2028, 10, 6, 12, tzinfo=timezone.utc))
    assert result["coherence"]["ok"] is False
    assert result["coherence"]["calendar_verified"] is False
    assert result["coherence"]["data_state"] == "unverified"
    assert result["verdict"] == "stale"


def test_hk_coherence_accepts_provider_trusted_historical_weekday(monkeypatch, tmp_path):
    stamp = date(2021, 12, 28)
    fake_hk_sentinel(monkeypatch, tmp_path, prices=stamp, standouts=stamp, regime=stamp, holdings=stamp)
    result = hk_freshness.hk_freshness_sentinel(NOW)
    assert result["coherence"]["ok"] is True
    assert result["coherence"]["calendar_verified"] is True
    assert result["verdict"] == "stale"


@pytest.mark.parametrize("day,instant,expected_rows", [
    ("2026-07-03", datetime(2026, 7, 3, 16, tzinfo=timezone.utc), 0),
    ("2026-07-06", datetime(2026, 7, 6, 22, tzinfo=timezone.utc), 1),
])
def test_actual_stock_price_adapter_filters_cash_dates(runner, monkeypatch, day, instant, expected_rows):
    from collectors.sector_holdings import StockPriceAdapter
    monkeypatch.setattr(Clock, "now", classmethod(lambda cls, tz=None: instant))
    monkeypatch.setattr(base.config, "load", lambda: {"yahoo": {}})
    saved, writes = runner
    saved["stocks", "AAPL"] = frame("2026-07-02", 100.0)
    stock_adapter = StockPriceAdapter()
    monkeypatch.setattr(stock_adapter, "fetch", lambda full_history=False: {"AAPL": frame(day, 110.0)})
    result = base.run_adapter(stock_adapter)
    assert result.status == "ok"
    assert result.rows == expected_rows
    assert len(writes) == expected_rows
    if expected_rows:
        assert saved["stocks", "AAPL"].loc[day, "close"] == 110.0
        assert result.last_date == day
    else:
        pd.testing.assert_frame_equal(saved["stocks", "AAPL"], frame("2026-07-02", 100.0))
        assert result.last_date == "2026-07-02"


@pytest.mark.parametrize("symbol,market", [("AAPL", "us"), ("BRK-B", "us"),
    ("RY.TO", "ca"), ("0700.HK", "hk"), ("VOD.L", None), ("ES=F", None),
    ("BTC-USD", None), ("USDCNY=X", None)])
def test_stock_price_adapter_uses_shared_per_symbol_cash_classification(symbol, market):
    from collectors.sector_holdings import StockPriceAdapter
    # Classification has no constructor/provider dependency.
    stock_adapter = StockPriceAdapter.__new__(StockPriceAdapter)
    assert stock_adapter.session_calendar_for_series(symbol) == market
