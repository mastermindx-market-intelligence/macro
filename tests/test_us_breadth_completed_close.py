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
    # The same fixed input session must keep exercising the tail/seam path after
    # the calendar advances; otherwise a 14-day cache-age branch hides the case.
    monkeypatch.setattr(pd.Timestamp, "utcnow", staticmethod(
        lambda: pd.Timestamp("2026-09-16T12:00:00Z")))
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


def test_cached_current_session_value_cannot_fill_a_missing_fresh_close(tmp_path, monkeypatch):
    """A prior intraday value is not evidence of the completed close."""
    adapter = _adapter(tmp_path, monkeypatch)
    adapter.cache_path.parent.mkdir(parents=True)
    cached = _response(SYMBOLS)["Close"]
    cached.loc[str(SESSION), "EEE"] = 102.0
    cached.to_parquet(adapter.cache_path)

    def download(tickers, **kwargs):
        response = _response(tickers)
        response.loc[str(SESSION), ("Close", "EEE")] = np.nan
        return response

    monkeypatch.setattr(breadth.yf, "download", download)
    result = adapter.fetch()
    stored = pd.read_parquet(adapter.cache_path)
    assert pd.isna(stored.loc[str(SESSION), "EEE"])
    assert stored.loc["2026-09-14", "EEE"] == 101.0
    assert result["breadth"].loc[str(SESSION), "n_members"] == 4


@pytest.mark.parametrize(
    ("field", "cache_key", "cached_value", "fresh_prior"),
    (("High", "high", 999.0, 102.0),
     ("Low", "low", 1.0, 99.0),
     ("Volume", "volume", 999999.0, 700.0)),
)
def test_cached_current_session_extra_cannot_fill_missing_fresh_extra(
        tmp_path, monkeypatch, field, cache_key, cached_value, fresh_prior):
    """Earlier same-date High/Low/Volume is not a completed-session extra."""
    adapter = _adapter(tmp_path, monkeypatch)
    adapter.cache_path.parent.mkdir(parents=True)
    cached = pd.DataFrame(100.0, index=DATES, columns=SYMBOLS)
    cached.loc[str(SESSION), "EEE"] = cached_value
    extra_path = adapter.cache_path.parent / f"_{cache_key}_cache.parquet"
    cached.to_parquet(extra_path)

    def download(tickers, **kwargs):
        response = _response(tickers)
        response.loc[str(SESSION), (field, "EEE")] = np.nan
        return response

    monkeypatch.setattr(breadth.yf, "download", download)
    adapter.fetch()
    stored = pd.read_parquet(extra_path)
    assert pd.isna(stored.loc[str(SESSION), "EEE"])
    assert stored.loc["2026-09-14", "EEE"] == fresh_prior


@pytest.mark.parametrize(
    ("field", "cache_key", "cached_value"),
    (("High", "high", 999.0), ("Low", "low", 1.0), ("Volume", "volume", 999999.0)),
)
def test_absent_completed_session_extra_quarantines_existing_current_cache(
        tmp_path, monkeypatch, field, cache_key, cached_value):
    """An omitted whole field cannot leave its old same-date cache row current."""
    adapter = _adapter(tmp_path, monkeypatch)
    adapter.cache_path.parent.mkdir(parents=True)
    cached = pd.DataFrame(100.0, index=DATES, columns=SYMBOLS)
    cached.loc[str(SESSION)] = cached_value
    extra_path = adapter.cache_path.parent / f"_{cache_key}_cache.parquet"
    cached.to_parquet(extra_path)

    def download(tickers, **kwargs):
        response = _response(tickers)
        keep = response.columns.get_level_values(0) != field
        return response.loc[:, keep]

    monkeypatch.setattr(breadth.yf, "download", download)
    adapter.fetch()
    stored = pd.read_parquet(extra_path)
    assert stored.loc[str(SESSION), SYMBOLS].isna().all()
    assert (stored.loc["2026-09-14", SYMBOLS] == 100.0).all()


def test_seam_repair_cannot_remove_completed_prices_before_persistence(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path, monkeypatch)
    before = _seed_all_caches(adapter)
    monkeypatch.setattr(breadth.yf, "download", lambda tickers, **kw: _response(tickers))

    def torn_merge(fresh, cached, **kwargs):
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


def test_missing_completed_close_masks_same_response_high_low_and_volume(tmp_path, monkeypatch):
    """A name without settlement cannot publish an independently current OHLCV row."""
    adapter = _adapter(tmp_path, monkeypatch)

    def download(tickers, **kwargs):
        response = _response(tickers)
        response.loc[str(SESSION), ("Close", "EEE")] = np.nan
        return response

    monkeypatch.setattr(breadth.yf, "download", download)
    adapter.fetch()
    for cache_key, fresh_prior in (("high", 102.0), ("low", 99.0), ("volume", 700.0)):
        saved = pd.read_parquet(adapter.cache_path.parent / f"_{cache_key}_cache.parquet")
        assert pd.isna(saved.loc[str(SESSION), "EEE"])
        assert saved.loc["2026-09-14", "EEE"] == fresh_prior


def test_post_seam_invalid_minority_is_missing_not_a_published_price(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path, monkeypatch)
    _seed_all_caches(adapter)
    monkeypatch.setattr(breadth.yf, "download", lambda tickers, **kw: _response(tickers))

    def changed_merge(fresh, cached, **kwargs):
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

    def merge(fresh, cached, **kwargs):
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


# Real detector + fetch regressions for review 5233152327 / request 5711674324.
def _seed_seam_caches(adapter):
    adapter.cache_path.parent.mkdir(parents=True)
    dates = pd.to_datetime(["2026-09-10", "2026-09-11", "2026-09-14", "2026-09-15"])
    cached = pd.DataFrame(100.0, index=dates, columns=SYMBOLS)
    cached["EEE"] = 200.0
    files = {}
    for kind in ("closes", "high", "low", "volume"):
        path = adapter.cache_path.parent / f"_{kind}_cache.parquet"
        cached.to_parquet(path)
        files[path] = path.read_bytes()
    return files


def _seam_response(tickers, mode):
    frame = _response(tickers)
    if mode == "current_close_missing":
        frame.loc[str(SESSION), ("Close", "EEE")] = np.nan
        for field, value in (("High", 160.0), ("Low", 80.0), ("Volume", 900.0)):
            frame.loc[str(SESSION), (field, "EEE")] = value
        return frame
    for field in ("Open", "Close", "High", "Low"):
        frame[field] = frame[field] * 0.5
    if mode.endswith("_field_missing"):
        absent = mode.split("_", 1)[0].title()
        return frame.loc[:, frame.columns.get_level_values(0) != absent]
    if mode == "high_cell_missing":
        frame.loc[str(SESSION), ("High", "EEE")] = np.nan
    return frame


@pytest.mark.parametrize("name", ("breadth", "smallcap_breadth", "midcap_breadth"))
@pytest.mark.parametrize("mode", ("current_close_missing", "high_field_missing",
                                  "low_field_missing", "volume_field_missing", "high_cell_missing"))
def test_seam_incomplete_replacement_refuses_before_any_cache_write(tmp_path, monkeypatch, name, mode):
    adapter = _adapter(tmp_path, monkeypatch, name=name)
    before = _seed_seam_caches(adapter)
    calls = []

    def download(tickers, **kw):
        calls.append((list(tickers), kw["period"]))
        return _seam_response(tickers, mode) if tickers == ["EEE"] else _response(tickers)

    monkeypatch.setattr(breadth.yf, "download", download)
    with pytest.raises(RuntimeError, match="seam"):
        adapter.fetch()
    assert calls[0] == (SYMBOLS, "1mo")
    assert calls[1:] == [(["EEE"], "2y")] * (2 if mode == "current_close_missing" else 1)
    assert {path: path.read_bytes() for path in before} == before
    assert not (adapter.cache_path.parent / "constituents.parquet").exists()


@pytest.mark.parametrize("name", ("breadth", "smallcap_breadth", "midcap_breadth"))
def test_seam_coherent_replacement_keeps_all_fields_on_selected_basis(tmp_path, monkeypatch, name):
    adapter = _adapter(tmp_path, monkeypatch, name=name)
    _seed_seam_caches(adapter)
    calls = []
    clock_calls = []
    monkeypatch.setattr(nyse_calendar, "expected_last_session", lambda now=None: clock_calls.append(now) or SESSION)

    def download(tickers, **kw):
        calls.append((list(tickers), kw["period"]))
        return _seam_response(tickers, "coherent") if tickers == ["EEE"] else _response(tickers)

    monkeypatch.setattr(breadth.yf, "download", download)
    adapter.fetch()
    assert calls == [(SYMBOLS, "1mo"), (["EEE"], "2y")]
    assert len(clock_calls) == 1
    expected = {"closes": 51.5, "high": 52.0, "low": 50.5, "volume": 700.0}
    for kind, value in expected.items():
        stored = pd.read_parquet(adapter.cache_path.parent / f"_{kind}_cache.parquet")
        assert stored.loc[str(SESSION), "EEE"] == value
        assert pd.Timestamp("2026-09-10") in stored.index
    assert pd.read_parquet(adapter.cache_path).loc[str(SESSION), "AAA"] == 103.0


def test_post_seam_selection_masks_extras_for_a_missing_current_close(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path, monkeypatch)
    _seed_all_caches(adapter)
    monkeypatch.setattr(breadth.yf, "download", lambda tickers, **kw: _response(tickers))

    def final_selection(fresh, cached, **kwargs):
        result = fresh.combine_first(cached)
        result.loc[str(SESSION), "EEE"] = np.nan
        return result

    monkeypatch.setattr(adapter, "_merge_refreshed", final_selection)
    adapter.fetch()
    for kind in ("closes", "high", "low", "volume"):
        values = pd.read_parquet(adapter.cache_path.parent / f"_{kind}_cache.parquet")
        assert pd.isna(values.loc[str(SESSION), "EEE"]), kind
        assert values.loc[str(SESSION), "AAA"] > 0


@pytest.mark.parametrize("current_names, succeeds", ((4, True), (3, False)))
def test_seam_replacement_keeps_eighty_percent_policy_and_null_companions(tmp_path, monkeypatch, current_names, succeeds):
    adapter = _adapter(tmp_path, monkeypatch)
    before = _seed_seam_caches(adapter)
    for path in before:
        frame = pd.read_parquet(path)
        frame.loc[:, :] = 200.0  # the REAL seam detector must select all five names
        frame.to_parquet(path)
    before = {path: path.read_bytes() for path in before}
    calls = []

    def download(tickers, **kw):
        calls.append((list(tickers), kw["period"]))
        result = _response(tickers)
        if kw["period"] != "1mo":
            for field in ("Open", "Close", "High", "Low"):
                result[field] = result[field] * 0.5
            for ticker in SYMBOLS[current_names:]:
                result.loc[str(SESSION), ("Close", ticker)] = np.nan
        return result

    monkeypatch.setattr(breadth.yf, "download", download)
    if not succeeds:
        with pytest.raises(RuntimeError, match="seam"):
            adapter.fetch()
        assert len(calls) == 1 + adapter.ycfg["retries"]
        assert {path: path.read_bytes() for path in before} == before
        return
    adapter.fetch()
    assert calls == [(SYMBOLS, "1mo"), (SYMBOLS, "2y")]
    for kind in ("closes", "high", "low", "volume"):
        values = pd.read_parquet(adapter.cache_path.parent / f"_{kind}_cache.parquet")
        assert values.loc[str(SESSION)].notna().sum() == current_names
        assert pd.isna(values.loc[str(SESSION), "EEE"])


def test_seam_new_companion_field_is_grafted_when_not_in_initial_response(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path, monkeypatch)
    _seed_seam_caches(adapter)

    def download(tickers, **kw):
        frame = _seam_response(tickers, "coherent") if tickers == ["EEE"] else _response(tickers)
        if kw["period"] == "1mo":
            frame = frame.loc[:, frame.columns.get_level_values(0) != "High"]
        return frame

    monkeypatch.setattr(breadth.yf, "download", download)
    adapter.fetch()
    high = pd.read_parquet(adapter.cache_path.parent / "_high_cache.parquet")
    assert high.loc[str(SESSION), "EEE"] == 52.0
    assert pd.isna(high.loc[str(SESSION), "AAA"])


def test_seam_refusal_reaches_existing_collector_health_without_publishing(tmp_path, monkeypatch):
    from collectors import base

    adapter = _adapter(tmp_path, monkeypatch)
    before = _seed_seam_caches(adapter)
    monkeypatch.setattr(base, "_breaker_state", lambda: {})
    monkeypatch.setattr(base.store, "upsert", lambda *a, **kw: pytest.fail("incoherent seam cannot publish aggregates"))
    monkeypatch.setattr(breadth.yf, "download", lambda tickers, **kw:
                        _seam_response(tickers, "high_field_missing") if tickers == ["EEE"] else _response(tickers))
    result = base.run_adapter(adapter, stale_after_days=3)
    assert result.status == "failed"
    assert "seam repair omitted high for EEE" in result.error
    assert {path: path.read_bytes() for path in before} == before
