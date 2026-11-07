"""Explicit cohort acquisition through the incumbent Yahoo request/extraction owner.

Provider calls are controlled fixtures. These tests do not assert live availability
or authorize runtime ownership transfer.
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from collectors import yahoo
from lib import config, market_session, store
from lib.yahoo_runtime_profile import (
    MIN_SECTOR_HISTORY_SESSIONS, SECTOR_CLOSE_TICKERS, VerifiedYahooCohort,
    YahooRuntimeBindingError, YahooRuntimeProfile, bind_snapshot,
)

SYMBOLS = SECTOR_CLOSE_TICKERS
NOW = datetime(2026, 11, 3, 23, tzinfo=timezone.utc)
CFG = {"batch_size": 14, "retries": 2, "backoff_base_s": 0, "upsert_basis_tol": .001}


def history(rows=1100, end="2026-11-03", value=100.0):
    dates = pd.bdate_range(end=end, periods=rows + 150)
    dates = dates[[market_session.is_session_date("US", d.date()) for d in dates]][-rows:]
    assert len(dates) == rows
    values = value + np.arange(rows) / 100
    return pd.DataFrame({"close_price": values + 10, "close": values,
                         "volume": np.repeat(1000, rows)}, index=dates)


def provider(frame):
    return frame.rename(columns={"close_price": "Close", "close": "Adj Close",
                                 "volume": "Volume"}).copy(deep=True)


def batch_payload(batch, frames):
    return pd.concat({ticker: provider(frames[ticker]) for ticker in batch}, axis=1)


@pytest.fixture
def full():
    return {t: history(value=100 + n) for n, t in enumerate(SYMBOLS)}


def forbidden(*args, **kwargs):
    raise AssertionError("Ambient repository read/write reached")


def attach(monkeypatch, adapter, full, *, windows=None, recoveries=None):
    calls = []
    def download(batch, period, *, request_settings):
        calls.append((tuple(batch), period, request_settings))
        values = recoveries if period == "max" and recoveries is not None else full
        if period != "max":
            values = windows if windows is not None else {t: f.iloc[-25:] for t, f in full.items()}
        if isinstance(values, Exception):
            raise values
        return batch_payload(batch, values)
    monkeypatch.setattr(adapter, "_download", download)
    return calls


def acquire(adapter, priors, **kwargs):
    return adapter.acquire_cycle_benchmarks(
        SYMBOLS, prior_frames=priors, evaluation_instant=NOW, **kwargs)


def test_real_explicit_constructor_and_acquisition_never_resolve_ambient_store(monkeypatch, full):
    monkeypatch.setattr(config, "load", forbidden)
    monkeypatch.setattr(config, "data_dir", forbidden)
    monkeypatch.setattr(store, "read", forbidden)
    monkeypatch.setattr(store, "upsert", forbidden)
    adapter = yahoo.YahooAdapter(yahoo_config=CFG)
    monkeypatch.setattr(adapter, "all_tickers", forbidden)
    monkeypatch.setattr(adapter, "_fill_missing_extras", forbidden)
    monkeypatch.setattr(adapter, "_rebase_shifted", forbidden)
    calls = attach(monkeypatch, adapter, full)
    before = {t: f.copy(deep=True) for t, f in full.items()}
    result = acquire(adapter, full)
    assert result.accepted and result.returned == SYMBOLS
    assert [(batch, period) for batch, period, _ in calls] == [(SYMBOLS, "1mo")]
    for t in SYMBOLS:
        pd.testing.assert_frame_equal(result.frames[t], full[t])
        assert len(result.frames[t]) == 1100
        pd.testing.assert_frame_equal(full[t], before[t])
    result.frames["SPY"].iloc[0, 0] = 9999
    pd.testing.assert_frame_equal(full["SPY"], before["SPY"])
    assert result.clocks["known"]["expected_session"] == "2026-11-03"


@pytest.mark.parametrize("symbols", [
    SYMBOLS[:-1], SYMBOLS + ("AAPL",), SYMBOLS[:-1] + (SYMBOLS[0],),
    tuple("spy" if t == "SPY" else t for t in SYMBOLS), "SPY",
])
def test_closed_cohort_refuses_subsets_aliases_and_duplicates_before_request(monkeypatch, full, symbols):
    adapter = yahoo.YahooAdapter(yahoo_config=CFG)
    monkeypatch.setattr(adapter, "_download", forbidden)
    with pytest.raises(ValueError, match="14"):
        adapter.acquire_cycle_benchmarks(symbols, prior_frames=full, evaluation_instant=NOW)


@pytest.mark.parametrize("kind", ["missing", "extra", "case_collision", "empty", "nan", "missing_basis", "future"])
def test_explicit_prior_contract_refuses_before_request(monkeypatch, full, kind):
    priors = dict(full)
    if kind == "missing":
        del priors["SPY"]
    elif kind == "extra":
        priors["AAPL"] = full["SPY"]
    elif kind == "case_collision":
        priors["spy"] = priors.pop("SPY")
    elif kind == "empty":
        priors["SPY"] = full["SPY"].iloc[:0]
    elif kind == "nan":
        priors["SPY"] = full["SPY"].copy()
        priors["SPY"].iloc[0, 0] = np.nan
    elif kind == "missing_basis":
        priors["SPY"] = full["SPY"].drop(columns="close_price")
    else:
        priors["SPY"] = history(end="2026-11-04")
    adapter = yahoo.YahooAdapter(yahoo_config=CFG)
    monkeypatch.setattr(adapter, "_download", forbidden)
    with pytest.raises(ValueError):
        acquire(adapter, priors)


@pytest.mark.parametrize("field,value", [
    ("batch_size", True), ("batch_size", 0), ("retries", False), ("retries", 0),
    ("backoff_base_s", np.nan), ("backoff_base_s", -1), ("upsert_basis_tol", np.inf),
    ("upsert_basis_tol", True), ("upsert_basis_tol", -1),
])
def test_invalid_request_configuration_refuses_before_request(monkeypatch, full, field, value):
    adapter = yahoo.YahooAdapter(yahoo_config={**CFG, field: value})
    monkeypatch.setattr(adapter, "_download", forbidden)
    with pytest.raises(ValueError):
        acquire(adapter, full)


def test_absent_priors_trigger_one_full_history_recovery(monkeypatch, full):
    adapter = yahoo.YahooAdapter(yahoo_config=CFG)
    calls = attach(monkeypatch, adapter, full)
    result = acquire(adapter, {t: None for t in SYMBOLS})
    assert result.accepted
    assert [p for _, p, _ in calls] == ["1mo", "max"]
    assert all(len(f) == 1100 for f in result.frames.values())
    assert all(result.lineage[t]["prior"] == "absent" for t in SYMBOLS)


@pytest.mark.parametrize("basis", ["close", "close_price"])
def test_either_basis_shift_requires_full_history_without_old_prefix(monkeypatch, full, basis):
    shifted = {t: f.copy() for t, f in full.items()}
    shifted["SPY"][basis] *= 1.1
    adapter = yahoo.YahooAdapter(yahoo_config=CFG)
    calls = attach(monkeypatch, adapter, shifted)
    result = acquire(adapter, full)
    assert result.accepted
    assert [(b, p) for b, p, _ in calls] == [(SYMBOLS, "1mo"), (("SPY",), "max")]
    pd.testing.assert_frame_equal(result.frames["SPY"], shifted["SPY"])
    assert result.lineage["SPY"]["basis_comparison"][basis] == "shifted"


@pytest.mark.parametrize("failure", ["thin_max", "old_target", "missing_basis", "boolean_basis",
                                     "string_basis", "infinite_basis", "zero_basis", "no_response"])
def test_bad_max_response_cannot_replace_any_part_of_cohort(monkeypatch, full, failure):
    bad = {t: f.copy() for t, f in full.items()}
    if failure == "thin_max":
        bad["SPY"] = bad["SPY"].iloc[-999:]
    elif failure == "old_target":
        bad["SPY"] = bad["SPY"].iloc[:-1]
    elif failure == "missing_basis":
        bad["SPY"] = bad["SPY"].drop(columns="close_price")
    elif failure in ("boolean_basis", "string_basis"):
        bad["SPY"]["close_price"] = True if failure == "boolean_basis" else "100"
    elif failure in ("infinite_basis", "zero_basis"):
        bad["SPY"].iloc[-1, 0] = np.inf if failure == "infinite_basis" else 0
    else:
        bad = RuntimeError("provider unavailable")
    adapter = yahoo.YahooAdapter(yahoo_config=CFG)
    calls = attach(monkeypatch, adapter, full, recoveries=bad)
    result = acquire(adapter, {t: None for t in SYMBOLS})
    assert not result.accepted and not result.frames and not result.returned
    assert "SPY" in result.failed
    assert [p for _, p, _ in calls] == ["1mo", "max"]


def test_initial_max_is_not_repeated_when_it_returns_only_a_window(monkeypatch, full):
    adapter = yahoo.YahooAdapter(yahoo_config=CFG)
    calls = attach(monkeypatch, adapter, full,
                   recoveries={t: f.iloc[-25:] for t, f in full.items()})
    result = acquire(adapter, full, period="max")
    assert not result.accepted and not result.frames
    assert [p for _, p, _ in calls] == ["max"]
    assert set(result.failure_reasons.values()) == {"archive_truncated"}


def test_flat_multi_symbol_response_is_never_fanned_out(monkeypatch, full):
    adapter = yahoo.YahooAdapter(yahoo_config=CFG)
    calls = []
    def download(batch, period, *, request_settings):
        calls.append(period)
        return provider(full["SPY"])
    monkeypatch.setattr(adapter, "_download", download)
    result = acquire(adapter, full)
    assert not result.accepted and not result.frames
    assert set(result.failure_reasons.values()) == {"ambiguous_batch_identity"}
    assert calls == ["1mo", "max"]


def test_flat_single_symbol_response_is_valid_only_for_actual_single_request(monkeypatch, full):
    adapter = yahoo.YahooAdapter(yahoo_config={**CFG, "batch_size": 1})
    calls = []
    def download(batch, period, *, request_settings):
        assert len(batch) == 1
        calls.append(tuple(batch))
        return provider(full[batch[0]].iloc[-25:])
    monkeypatch.setattr(adapter, "_download", download)
    result = acquire(adapter, full)
    assert result.accepted and calls == [(t,) for t in SYMBOLS]


def test_missing_and_null_rows_own_the_original_fresh_span(monkeypatch, full):
    windows = {t: f.iloc[-25:].copy() for t, f in full.items()}
    null_date = windows["SPY"].index[0]
    missing_date = windows["SPY"].index[5]
    windows["SPY"].loc[null_date, ["close", "close_price"]] = np.nan
    windows["SPY"] = windows["SPY"].drop(index=missing_date)
    adapter = yahoo.YahooAdapter(yahoo_config=CFG)
    calls = attach(monkeypatch, adapter, full, windows=windows)
    result = acquire(adapter, full)
    assert result.accepted and len(calls) == 1
    assert null_date not in result.frames["SPY"].index
    assert missing_date not in result.frames["SPY"].index
    assert len(result.frames["SPY"]) == 1098
    assert null_date in full["SPY"].index and missing_date in full["SPY"].index


def test_calendar_target_is_required_even_when_provider_matches_old_prior(monkeypatch, full):
    old = {t: f.iloc[:-1].copy() for t, f in full.items()}
    adapter = yahoo.YahooAdapter(yahoo_config=CFG)
    calls = attach(monkeypatch, adapter, old)
    result = acquire(adapter, old)
    assert not result.accepted and not result.frames
    assert set(result.failure_reasons.values()) == {"missing_target_session"}
    assert [p for _, p, _ in calls] == ["1mo", "max"]


@pytest.mark.parametrize("instant", [
    datetime(2024, 11, 5, 23, tzinfo=timezone.utc),
    datetime(2026, 1, 2, 15, tzinfo=timezone.utc),
    datetime(2026, 11, 3, 23),
])
def test_unverified_calendar_or_naive_clock_refuses_before_request(monkeypatch, full, instant):
    adapter = yahoo.YahooAdapter(yahoo_config=CFG)
    monkeypatch.setattr(adapter, "_download", forbidden)
    with pytest.raises(ValueError):
        adapter.acquire_cycle_benchmarks(SYMBOLS, prior_frames=full,
                                        evaluation_instant=instant)


def test_developing_policy_cannot_be_enabled(monkeypatch, full):
    adapter = yahoo.YahooAdapter(yahoo_config=CFG)
    monkeypatch.setattr(adapter, "_download", forbidden)
    with pytest.raises(ValueError, match="completed"):
        acquire(adapter, full, completed_sessions_only=False)


def test_alias_collision_is_refused_before_request(monkeypatch, full):
    adapter = yahoo.YahooAdapter(yahoo_config=CFG)
    monkeypatch.setattr(yahoo, "fetch_symbol", lambda t: "SPY")
    monkeypatch.setattr(adapter, "_download", forbidden)
    with pytest.raises(ValueError, match="identities"):
        acquire(adapter, full)


def test_request_settings_survive_config_changes_between_batches_and_recovery(monkeypatch, full):
    adapter = yahoo.YahooAdapter(yahoo_config={**CFG, "batch_size": 7})
    seen = []
    def download(batch, period, *, request_settings):
        seen.append(request_settings)
        adapter.cfg.update(batch_size=1, retries=99, backoff_base_s=99, upsert_basis_tol=.5)
        values = full if period == "max" else {t: f.iloc[-25:] for t, f in full.items()}
        return batch_payload(batch, values)
    monkeypatch.setattr(adapter, "_download", download)
    result = acquire(adapter, {t: None for t in SYMBOLS})
    assert result.accepted and len(seen) == 4
    assert all(s is seen[0] for s in seen)
    assert (seen[0].batch_size, seen[0].retries, seen[0].backoff_base_s) == (7, 2, 0)
    assert result.clocks["known"]["retries"] == 2


def test_actual_downloader_uses_explicit_retry_settings_without_metadata_mutation(monkeypatch, full):
    adapter = yahoo.YahooAdapter(yahoo_config=CFG)
    marker = object()
    adapter._wti_download_context = marker
    adapter._capture_temporal_metadata = True
    settings = yahoo.YahooRequestSettings.capture(adapter.cfg)
    calls = []
    def download(batch, **kwargs):
        calls.append(kwargs)
        adapter.cfg.update(retries=0, backoff_base_s=999)
        if len(calls) == 1:
            raise RuntimeError("temporary failure")
        return provider(full["SPY"])
    waits = []
    monkeypatch.setattr(yahoo.yf, "download", download)
    monkeypatch.setattr(yahoo.time, "sleep", waits.append)
    response = adapter._download(["SPY"], "max", request_settings=settings)
    assert not response.empty and len(calls) == 2 and waits == [0]
    assert adapter._wti_download_context is marker
    assert all(c == {"period": "max", "auto_adjust": False, "progress": False,
                     "group_by": "ticker", "threads": True} for c in calls)


def test_strict_comparison_never_calls_nonfinite_overlap_aligned():
    old = history(20)
    new = old.copy()
    new.iloc[-1, 0] = np.inf
    assert store.compare_basis(old, new, col="close_price", strict=True).status == "incomparable"
    new.iloc[-1, 0] = np.nan
    assert store.compare_basis(old, new, col="close_price", strict=True).status == "incomparable"


def test_pure_merge_preserves_legacy_default_and_explicit_span(monkeypatch):
    monkeypatch.setattr(store, "read", forbidden)
    monkeypatch.setattr(config, "data_dir", forbidden)
    old = history(20)
    new = old.iloc[-5:].copy()
    start = new.index[0]
    new = new.iloc[1:]
    new.iloc[1, 0] = np.nan
    legacy = store.merge_frames(old, new)
    pd.testing.assert_frame_equal(legacy, new.combine_first(old).sort_index(), check_freq=False)
    explicit = store.merge_frames(old, new, overwrite_overlap=True, refresh_start=start)
    assert start not in explicit.index
    assert pd.isna(explicit.loc[new.index[1], "close_price"])
    assert not pd.isna(old.loc[new.index[1], "close_price"])


def test_binding_uses_same_minimum_and_cannot_accept_a_window(full):
    frames = {t: f.iloc[-(MIN_SECTOR_HISTORY_SESSIONS - 1):] for t, f in full.items()}
    with pytest.raises(YahooRuntimeBindingError, match="HISTORY_INSUFFICIENT"):
        with bind_snapshot(YahooRuntimeProfile(mode="runtime"),
                           VerifiedYahooCohort("g1", "2026-11-03", frames)):
            pass


def test_missing_initial_basis_can_recover_without_old_failure_metadata(monkeypatch, full):
    windows = {t: f.iloc[-25:].copy() for t, f in full.items()}
    windows["SPY"] = windows["SPY"].drop(columns="close_price")
    adapter = yahoo.YahooAdapter(yahoo_config=CFG)
    calls = attach(monkeypatch, adapter, full, windows=windows)
    result = acquire(adapter, full)
    assert result.accepted
    assert [(b, p) for b, p, _ in calls] == [(SYMBOLS, "1mo"), (("SPY",), "max")]
    assert result.lineage["SPY"]["status"] == "accepted"
    assert not result.failure_reasons


def test_half_day_target_is_captured_once_and_unsettled_rows_do_not_advance_it(monkeypatch):
    frames = {t: history(end="2026-11-27") for t in SYMBOLS}
    priors = {t: f.iloc[:-1].copy() for t, f in frames.items()}
    expected = market_session.expected_session
    calls = []
    def capture_target(market, instant):
        calls.append((market, instant))
        return expected(market, instant)
    monkeypatch.setattr(market_session, "expected_session", capture_target)
    adapter = yahoo.YahooAdapter(yahoo_config=CFG)
    attach(monkeypatch, adapter, frames)
    for instant, target in [
        (datetime(2026, 11, 27, 18, 59, tzinfo=timezone.utc), "2026-11-25"),
        (datetime(2026, 11, 27, 19, 0, tzinfo=timezone.utc), "2026-11-27"),
    ]:
        calls.clear()
        result = adapter.acquire_cycle_benchmarks(SYMBOLS, prior_frames=priors,
                                                  evaluation_instant=instant)
        assert result.accepted
        assert len(calls) == 1
        assert result.clocks["known"]["expected_session"] == target
        assert all(f.index[-1].date().isoformat() == target for f in result.frames.values())


def test_no_overlap_requires_full_archive_recovery(monkeypatch):
    frames = {t: history(rows=1200) for t in SYMBOLS}
    priors = {t: f.iloc[:-50].copy() for t, f in frames.items()}
    adapter = yahoo.YahooAdapter(yahoo_config=CFG)
    calls = attach(monkeypatch, adapter, frames)
    result = acquire(adapter, priors)
    assert result.accepted and [p for _, p, _ in calls] == ["1mo", "max"]
    assert all(len(f) == 1200 for f in result.frames.values())
    assert all(set(result.lineage[t]["basis_comparison"].values()) == {"no_overlap"}
               for t in SYMBOLS)


def _base_store():
    import importlib.util
    from pathlib import Path
    path = Path(__file__).parent / "fixtures/base_store_d923.py"
    spec = importlib.util.spec_from_file_location("base_store_d923", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("overwrite", [False, True])
@pytest.mark.parametrize("case", ["normal", "duplicate", "null", "omitted", "stale", "outlier_empty", "intraday"])
def test_legacy_upsert_matches_actual_pre_extraction_base(monkeypatch, tmp_path, overwrite, case):
    base = _base_store()
    old = history(20)
    new = old.iloc[-5:].copy()
    new.iloc[-1, 0] += 1
    normalize = case != "intraday"
    if case == "duplicate":
        new = pd.concat([new, new.iloc[-1:]])
    elif case == "null":
        new.iloc[1, 0] = np.nan
    elif case == "omitted":
        new = new.drop(index=new.index[1])
    elif case == "stale":
        new = old.iloc[-10:-5]
    elif case == "intraday":
        old.index = old.index + pd.Timedelta(hours=10)
        new.index = new.index + pd.Timedelta(hours=10)
    outcomes, writes = [], []
    monkeypatch.setattr(pd.DataFrame, "to_parquet",
                        lambda frame, path: writes.append((str(path), frame.copy(deep=True))))
    for module in (base, store):
        monkeypatch.setattr(module, "read", lambda *args: old.copy(deep=True), raising=False)
        monkeypatch.setattr(module, "_path", lambda *args: tmp_path / "store.parquet", raising=False)
        monkeypatch.setattr(module, "_guard_outliers",
            lambda group, name, prior, incoming, col:
                incoming.iloc[:0] if case == "outlier_empty" else incoming,
            raising=False)
        try:
            result = module.upsert("yahoo", "SPY", new.copy(deep=True),
                outlier_col="close", normalize_index=normalize, overwrite_overlap=overwrite)
            outcomes.append(("ok", result))
        except ValueError as exc:
            outcomes.append(("error", str(exc)))
    assert outcomes[0][0] == outcomes[1][0]
    if outcomes[0][0] == "error":
        assert outcomes[0][1] == outcomes[1][1]
        assert not writes
    else:
        pd.testing.assert_frame_equal(outcomes[0][1], outcomes[1][1])
        assert len(writes) == 2 and writes[0][0] == writes[1][0]
        pd.testing.assert_frame_equal(writes[0][1], writes[1][1])


@pytest.mark.parametrize("case", ["same", "shifted", "no_overlap", "all_nan", "bad_numeric", "no_prior"])
def test_legacy_basis_boolean_matches_actual_pre_extraction_base(monkeypatch, case):
    base = _base_store()
    old = history(20)
    new = old.iloc[-5:].copy()
    if case == "shifted":
        new["close"] *= 1.2
    elif case == "no_overlap":
        new.index = new.index + pd.Timedelta(days=100)
    elif case == "all_nan":
        new["close"] = np.nan
    elif case == "bad_numeric":
        new["close"] = "invalid"
    elif case == "no_prior":
        old = None
    for module in (base, store):
        monkeypatch.setattr(module, "read", lambda *args: old, raising=False)
    assert base.basis_shifted("yahoo", "SPY", new) == store.basis_shifted("yahoo", "SPY", new)


@pytest.mark.parametrize("bad_day", ["2026-10-31", "2026-07-03"])
def test_weekend_or_holiday_prior_cannot_satisfy_history_depth(monkeypatch, full, bad_day):
    bad = dict(full)
    frame = full["SPY"]
    extra = frame.iloc[:1].copy()
    extra.index = pd.DatetimeIndex([bad_day])
    bad["SPY"] = pd.concat([frame, extra]).sort_index()
    adapter = yahoo.YahooAdapter(yahoo_config=CFG)
    monkeypatch.setattr(adapter, "_download", forbidden)
    with pytest.raises(ValueError, match="prior"):
        acquire(adapter, bad)
    with pytest.raises(YahooRuntimeBindingError, match="HISTORY_SESSION_INVALID"):
        with bind_snapshot(YahooRuntimeProfile(mode="runtime"),
                           VerifiedYahooCohort("bad-calendar", "2026-11-03", bad)):
            pass


def test_strict_basis_comparison_has_no_artificial_small_price_floor():
    old = history(20)
    fresh = old.copy()
    old["close"] = 1e-14
    fresh["close"] = 2e-14
    strict = store.compare_basis(old, fresh, strict=True)
    assert strict.status == "shifted"
    assert strict.worst_relative_diff == pytest.approx(.5)
    # The preexisting legacy policy retains its numerical floor.
    assert store.compare_basis(old, fresh).status == "aligned"
