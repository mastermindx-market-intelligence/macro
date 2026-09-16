"""The current US session needs actual prices, not a dated volume-only row."""
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from collectors import breadth
from lib import nyse_calendar


SESSION = date(2026, 9, 15)
DATES = pd.to_datetime(["2026-09-11", "2026-09-14", "2026-09-15"])
SYMBOLS = ["AAA", "BBB", "CCC", "DDD", "EEE"]


def _response(tickers, *, current=103.0, volume=700.0, dates=DATES):
    frames = {}
    for field, adjustment in (("Open", -1), ("Close", 0), ("High", 1), ("Low", -2)):
        frames[field] = pd.DataFrame(
            {ticker: [100.0 + adjustment, 101.0 + adjustment, current + adjustment]
             for ticker in tickers}, index=dates,
        )
    frames["Volume"] = pd.DataFrame(volume, index=dates, columns=tickers)
    return pd.concat(frames, axis=1)


def _adapter(tmp_path, monkeypatch, *, name="breadth", batch_size=5, retries=2):
    adapter = breadth.BreadthAdapter.__new__(breadth.BreadthAdapter)
    adapter.name = name
    adapter.cfg = {"ma_windows": [2, 3], "nhnl_window": 3, "lookback_days_live": 400}
    adapter.ycfg = {"batch_size": batch_size, "retries": retries, "backoff_base_s": 0}
    adapter.cache_path = tmp_path / name / "_closes_cache.parquet"
    members = pd.DataFrame({"symbol": SYMBOLS, "name": SYMBOLS, "sector": ["Test"] * 5})
    monkeypatch.setattr(adapter, "constituents", lambda: members.copy())
    # These five synthetic names exercise the full price path, not Wikipedia's 400-name floor.
    monkeypatch.setattr(adapter, "constituents_checked", lambda frame: frame)
    monkeypatch.setattr(nyse_calendar, "expected_last_session", lambda now=None: SESSION)
    monkeypatch.setattr(breadth.time, "sleep", lambda _seconds: None)
    return adapter


def _seed_all_caches(adapter):
    adapter.cache_path.parent.mkdir(parents=True)
    files = []
    for field in ("closes", "high", "low", "volume"):
        path = adapter.cache_path.parent / f"_{field}_cache.parquet"
        pd.DataFrame(100.0, index=DATES[:2], columns=SYMBOLS).to_parquet(path)
        files.append(path)
    return {path: path.read_bytes() for path in files}


@pytest.mark.parametrize("name", ("breadth", "smallcap_breadth", "midcap_breadth"))
def test_volume_only_current_row_uses_existing_retry_before_success(tmp_path, monkeypatch, name):
    adapter = _adapter(tmp_path, monkeypatch, name=name)
    calls = []

    def download(tickers, **kwargs):
        calls.append(kwargs)
        return _response(tickers, current=np.nan if len(calls) == 1 else 103.0,
                         volume=99999 if len(calls) == 1 else 700)

    monkeypatch.setattr(breadth.yf, "download", download)
    result = adapter.fetch()

    assert len(calls) == 2, "a successful transport with no completed closes must retry"
    assert all(call["auto_adjust"] is True for call in calls)
    stored = pd.read_parquet(adapter.cache_path)
    assert stored.loc[str(SESSION), "AAA"] == 103.0
    assert result["breadth"].index.max().date() == SESSION
    volume = pd.read_parquet(adapter.cache_path.parent / "_volume_cache.parquet")
    assert volume.loc[str(SESSION), "AAA"] == 700, "extras must come from the accepted attempt"


def test_exhausted_incomplete_responses_preserve_every_existing_cache(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path, monkeypatch)
    before = _seed_all_caches(adapter)
    calls = []

    def download(tickers, **kwargs):
        calls.append(tickers)
        return _response(tickers, current=np.nan)

    monkeypatch.setattr(breadth.yf, "download", download)
    with pytest.raises(RuntimeError, match="completed session"):
        adapter.fetch()
    assert len(calls) == adapter.ycfg["retries"]
    assert {path: path.read_bytes() for path in before} == before
    assert not (adapter.cache_path.parent / "constituents.parquet").exists()


@pytest.mark.parametrize("bad", (np.nan, np.inf, -np.inf, 0.0, -1.0))
def test_invalid_completed_prices_cannot_be_fresh(tmp_path, monkeypatch, bad):
    adapter = _adapter(tmp_path, monkeypatch)
    monkeypatch.setattr(breadth.yf, "download", lambda tickers, **kw: _response(tickers, current=bad))
    with pytest.raises(RuntimeError, match="completed session"):
        adapter.fetch()
    assert not adapter.cache_path.exists()


def test_future_prices_do_not_cover_the_missing_completed_session(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path, monkeypatch)
    dates = pd.to_datetime(["2026-09-11", "2026-09-14", "2026-09-16"])
    monkeypatch.setattr(breadth.yf, "download", lambda tickers, **kw: _response(tickers, dates=dates))
    with pytest.raises(RuntimeError, match="completed session"):
        adapter.fetch()
    assert not adapter.cache_path.exists()


def test_preclose_uses_the_existing_calendar_not_the_future_panel_row(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path, monkeypatch)
    observed = []

    def expected(now=None):
        observed.append(now)
        return date(2026, 9, 14)

    monkeypatch.setattr(nyse_calendar, "expected_last_session", expected)
    calls = []
    monkeypatch.setattr(breadth.yf, "download", lambda tickers, **kw: calls.append(kw) or _response(tickers, current=np.nan))
    adapter.fetch()
    assert len(observed) == 1, "one fetch must use one completed-session observation"
    assert len(calls) == 1, "the current provisional null row is not yesterday's outage"
    assert pd.read_parquet(adapter.cache_path).loc["2026-09-14", "AAA"] == 101.0


def test_existing_eighty_percent_partial_coverage_is_not_changed_to_all_or_nothing(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path, monkeypatch, batch_size=1)
    calls = []

    def download(tickers, **kw):
        calls.append(tickers[0])
        return _response(tickers, current=np.nan if tickers == ["EEE"] else 103.0)

    monkeypatch.setattr(breadth.yf, "download", download)
    adapter.fetch()
    assert calls.count("EEE") == 2
    stored = pd.read_parquet(adapter.cache_path)
    assert stored.loc[str(SESSION)].notna().sum() == 4
    assert pd.isna(stored.loc[str(SESSION), "EEE"]), "never fabricate the unreturned close"


def test_seam_repair_cannot_remove_completed_prices_before_persistence(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path, monkeypatch)
    before = _seed_all_caches(adapter)
    monkeypatch.setattr(breadth.yf, "download", lambda tickers, **kw: _response(tickers))

    def torn_merge(fresh, cached):
        changed = fresh.copy()
        changed.loc[str(SESSION)] = np.nan
        return changed

    monkeypatch.setattr(adapter, "_merge_refreshed", torn_merge)
    with pytest.raises(RuntimeError, match="completed session"):
        adapter.fetch()
    assert {path: path.read_bytes() for path in before} == before


def test_non_us_adapter_keeps_its_own_calendar_and_call_shape(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path, monkeypatch, name="hk_breadth")

    def forbidden_clock(now=None):
        pytest.fail("US expected-session guard leaked into another calendar")

    monkeypatch.setattr(nyse_calendar, "expected_last_session", forbidden_clock)
    monkeypatch.setattr(breadth.yf, "download", lambda tickers, **kw: _response(tickers, current=np.nan))
    # Direct base downloader is also the interface used by the regional overrides.
    result = adapter._download_closes(SYMBOLS, "1mo")
    assert result.loc["2026-09-14", "AAA"] == 101.0


@pytest.mark.parametrize("warm", (False, True))
def test_current_close_guard_covers_cold_and_tail_refresh(tmp_path, monkeypatch, warm):
    adapter = _adapter(tmp_path, monkeypatch)
    if warm:
        _seed_all_caches(adapter)
    calls = []

    def download(tickers, **kw):
        calls.append(kw)
        return _response(tickers, current=np.nan if len(calls) == 1 else 103.0)

    monkeypatch.setattr(breadth.yf, "download", download)
    adapter.fetch()
    assert len(calls) == 2
    assert calls[0]["period"] == ("1mo" if warm else "2y")
    assert pd.read_parquet(adapter.cache_path).loc[str(SESSION), "AAA"] == 103.0


def test_full_history_validates_but_preserves_its_no_live_cache_write_contract(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path, monkeypatch)
    calls = []

    def download(tickers, **kw):
        calls.append(kw)
        return _response(tickers, current=np.nan if len(calls) == 1 else 103.0)

    monkeypatch.setattr(breadth.yf, "download", download)
    result = adapter.fetch(full_history=True)
    assert len(calls) == 2 and all(c["period"] == "max" for c in calls)
    assert result["breadth"].index.max().date() == SESSION
    assert not adapter.cache_path.exists()


def test_ambiguous_duplicate_completed_date_cannot_be_persisted(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path, monkeypatch)
    dates = pd.to_datetime(["2026-09-14", "2026-09-15", "2026-09-15"])
    monkeypatch.setattr(breadth.yf, "download", lambda tickers, **kw: _response(tickers, dates=dates))
    with pytest.raises(RuntimeError, match="completed session"):
        adapter.fetch()
    assert not adapter.cache_path.exists()


def test_us_market_local_daily_dates_do_not_shift_through_utc(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path, monkeypatch)
    dates = DATES.tz_localize("America/New_York")
    monkeypatch.setattr(breadth.yf, "download", lambda tickers, **kw: _response(tickers, dates=dates))
    frame = adapter._download_closes(SYMBOLS, "1mo", expected_session=SESSION)
    assert breadth._completed_close_count(frame, SYMBOLS, SESSION) == 5


def test_transport_error_and_incomplete_response_share_one_retry_budget(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path, monkeypatch, retries=3)
    calls = []

    def download(tickers, **kw):
        calls.append(kw)
        if len(calls) == 1:
            raise ConnectionError("provider unavailable")
        return _response(tickers, current=np.nan if len(calls) == 2 else 103.0)

    monkeypatch.setattr(breadth.yf, "download", download)
    adapter.fetch()
    assert len(calls) == 3
    assert pd.read_parquet(adapter.cache_path).loc[str(SESSION), "AAA"] == 103.0


def test_other_base_fetch_preserves_its_calendar_and_two_argument_override(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path, monkeypatch, name="russell_breadth")
    calls = []

    def download(tickers, period):
        calls.append((tickers, period))
        return _response(tickers)["Close"]

    monkeypatch.setattr(adapter, "_download_closes", download)
    monkeypatch.setattr(nyse_calendar, "expected_last_session", lambda *a: pytest.fail("US-only clock leaked"))
    adapter.fetch()
    assert len(calls) == 1


def test_missing_close_field_never_enters_the_close_matrix_as_volume(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path, monkeypatch, batch_size=1)

    def download(tickers, **kw):
        frame = _response(tickers)
        if tickers == ["EEE"]:
            return frame.loc[:, frame.columns.get_level_values(0) == "Volume"]
        return frame

    monkeypatch.setattr(breadth.yf, "download", download)
    adapter.fetch()
    closes = pd.read_parquet(adapter.cache_path)
    assert not isinstance(closes.columns, pd.MultiIndex)
    assert set(closes.columns) == set(SYMBOLS[:-1])
    assert "Volume" not in closes.columns


def test_existing_collector_health_consumer_reports_failure_not_success(tmp_path, monkeypatch):
    from collectors import base

    adapter = _adapter(tmp_path, monkeypatch)
    before = _seed_all_caches(adapter)
    monkeypatch.setattr(base, "_breaker_state", lambda: {})
    monkeypatch.setattr(breadth.yf, "download", lambda tickers, **kw: _response(tickers, current=np.nan))
    monkeypatch.setattr(base.store, "upsert", lambda *a, **kw: pytest.fail("failed source must not publish aggregates"))
    result = base.run_adapter(adapter, stale_after_days=3)
    assert result.status == "failed"
    assert "completed session 2026-09-15" in result.error
    assert "0/5" in result.error
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize("dtype", (bool, object, "boolean"))
def test_boolean_close_never_counts_as_a_price(tmp_path, monkeypatch, dtype):
    """Both built-in and pandas/NumPy Boolean price values remain invalid."""
    adapter = _adapter(tmp_path, monkeypatch)
    before = _seed_all_caches(adapter)
    calls = []

    def download(tickers, **kwargs):
        calls.append(kwargs)
        frame = _response(tickers)
        for ticker in tickers:
            frame[("Close", ticker)] = pd.Series([True, True, True], index=DATES, dtype=dtype)
        return frame

    monkeypatch.setattr(breadth.yf, "download", download)
    with pytest.raises(RuntimeError, match="completed session"):
        adapter.fetch()
    assert len(calls) == adapter.ycfg["retries"]
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize("value, expected", ((True, 0), (np.bool_(True), 0), (False, 0), (1, 1), (1.0, 1), (101.25, 1)))
def test_completed_close_rejects_boolean_without_rejecting_numeric_one(value, expected):
    frame = pd.DataFrame({"AAA": pd.Series([value], index=[pd.Timestamp(SESSION)], dtype=object)})
    assert breadth._completed_close_count(frame, ["AAA"], SESSION) == expected


@pytest.mark.parametrize("invalid", (True, np.bool_(True), np.inf, -np.inf, 0.0, -1.0))
def test_partial_invalid_prices_do_not_reach_stored_or_computed_breadth(tmp_path, monkeypatch, invalid):
    """The 80% coverage floor is not permission to persist the invalid remainder."""
    adapter = _adapter(tmp_path, monkeypatch)
    calls = []

    def download(tickers, **kwargs):
        calls.append(kwargs)
        response = _response(tickers)
        response[("Close", "EEE")] = response[("Close", "EEE")].astype(object)
        response.loc[str(SESSION), ("Close", "EEE")] = invalid
        return response

    monkeypatch.setattr(breadth.yf, "download", download)
    result = adapter.fetch()
    assert len(calls) == 1, "four actual closes still meet the existing partial floor"
    saved = pd.read_parquet(adapter.cache_path)
    assert pd.isna(saved.loc[str(SESSION), "EEE"]), "invalid current price must remain a hole"
    assert saved.loc["2026-09-14", "EEE"] == 101.0, "do not delete its valid history"
    assert breadth._completed_close_count(saved, SYMBOLS, SESSION) == 4
    assert result["breadth"].loc[str(SESSION), "n_members"] == 4


def test_post_seam_invalid_minority_is_missing_not_a_published_price(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path, monkeypatch)
    _seed_all_caches(adapter)
    monkeypatch.setattr(breadth.yf, "download", lambda tickers, **kw: _response(tickers))

    def changed_merge(fresh, cached):
        merged = fresh.copy()
        merged.loc[str(SESSION), "EEE"] = np.inf
        return merged

    monkeypatch.setattr(adapter, "_merge_refreshed", changed_merge)
    result = adapter.fetch()
    saved = pd.read_parquet(adapter.cache_path)
    assert pd.isna(saved.loc[str(SESSION), "EEE"])
    assert result["breadth"].loc[str(SESSION), "n_members"] == 4


def test_invalid_current_prices_are_missing_before_split_seam_merge(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path, monkeypatch)
    _seed_all_caches(adapter)

    def download(tickers, **kwargs):
        response = _response(tickers)
        response[("Close", "EEE")] = response[("Close", "EEE")].astype(object)
        response.loc[str(SESSION), ("Close", "EEE")] = True
        return response

    def merge(fresh, cached):
        assert pd.isna(fresh.loc[str(SESSION), "EEE"]), "seam detection must not see a false price 1"
        return fresh.combine_first(cached)

    monkeypatch.setattr(breadth.yf, "download", download)
    monkeypatch.setattr(adapter, "_merge_refreshed", merge)
    adapter.fetch()
    assert pd.isna(pd.read_parquet(adapter.cache_path).loc[str(SESSION), "EEE"])


def test_current_price_mask_preserves_history_input_and_healthy_identity():
    frame = pd.DataFrame({"AAA": [100.0, 101.0, 102.0], "BBB": [30.0, 31.0, -1.0]}, index=DATES)
    before = frame.copy(deep=True)
    cleaned = breadth._mask_invalid_completed_closes(frame, ["AAA", "BBB"], SESSION)
    pd.testing.assert_frame_equal(frame, before)
    pd.testing.assert_frame_equal(cleaned.iloc[:-1], before.iloc[:-1])
    assert cleaned.loc[str(SESSION), "AAA"] == 102.0
    assert pd.isna(cleaned.loc[str(SESSION), "BBB"])
    assert breadth._mask_invalid_completed_closes(cleaned, ["AAA", "BBB"], SESSION) is cleaned
