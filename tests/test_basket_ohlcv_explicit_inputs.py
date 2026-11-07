"""Genuine five-field refreshes, whole-history retention, and legacy four-field parity."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

from collectors.yahoo import YahooRequestSettings
from lib import adjusted_price_capture as captured
from scripts import fetch_basket_ohlcv as fetch

SOURCE = "2026-11-03"
NOW = datetime(2026, 11, 3, 23, tzinfo=timezone.utc)
DATES = pd.to_datetime(["2026-10-26", "2026-10-27", "2026-10-28", "2026-10-29",
                        "2026-10-30", "2026-11-02", SOURCE]).as_unit("ns")
POLICY = YahooRequestSettings.capture({"batch_size": 2, "retries": 1,
    "backoff_base_s": 0, "upsert_basis_tol": .001})


def frame(index=DATES, offset=0):
    close = 100 + offset + np.arange(len(index), dtype=float)
    return pd.DataFrame({"open": close - .25, "high": close + 2,
        "low": close - 2, "close": close, "volume": 1000 + close}, index=index)


def panels(frames, fields=captured.OHLCV_FIELDS):
    return {field: pd.concat({ticker: value[field] if field in value else
        pd.Series(np.nan, index=value.index) for ticker, value in frames.items()}, axis=1)
        if frames else pd.DataFrame(index=pd.DatetimeIndex([])) for field in fields}


def observed(frames, fields=captured.OHLCV_FIELDS, owner=captured):
    values = panels(frames, fields)
    spans = {ticker: (value.index[0], value.index[-1]) for ticker, value in frames.items()
             if len(value) and "close" in value and value["close"].notna().any()}
    return owner.AdjustedPriceCapture(values, spans, tuple(frames))


def merge(prior, fresh, *, active=("A",)):
    return captured.merge_adjusted_ohlcv_capture(
        prior=panels(prior), fresh=observed(fresh), active=active,
        source_session=SOURCE, basis_tolerance=.001, minimum_repair_sessions=1,
        full_replacement=True, allow_historical_replacement=True)


def acquire(monkeypatch, fresh, prior=None, *, requested=("A",), aliases=None, excluded=frozenset()):
    calls = []
    def download(tickers, **kwargs):
        calls.append((tickers, kwargs))
        return deepcopy(fresh)
    monkeypatch.setattr(fetch, "_download_ohlcv", download)
    result = fetch.acquire_ohlcv_from_inputs(
        requested=requested, prior_frames={} if prior is None else prior,
        aliases={} if aliases is None else aliases, excluded_symbols=excluded,
        request_settings=POLICY, history_start="2014-01-01", evaluation_instant=NOW)
    return result, calls


def test_open_survives_parse_combine_remap_and_whole_history_merge():
    blocks = []
    for ticker, offset in (("AA", 0), ("BB", 30)):
        raw = pd.concat({field.title(): frame(offset=offset)[[field]].rename(columns={field: ticker})
                         for field in captured.OHLCV_FIELDS}, axis=1)
        blocks.append(captured.capture_adjusted_ohlcv_response(raw, requested=(ticker,), source_session=SOURCE))
    combined = captured.combine_adjusted_ohlcv_captures(blocks, requested=("AA", "BB"))
    remapped = captured.remap_adjusted_ohlcv_capture(combined, canonical_to_vendor={"A": "AA", "B": "BB"})
    result = captured.merge_adjusted_ohlcv_capture(
        prior=panels({}), fresh=remapped, active=("A", "B"), source_session=SOURCE,
        basis_tolerance=.001, minimum_repair_sessions=1, full_replacement=True,
        allow_historical_replacement=True)
    assert result.current == result.repaired == ("A", "B")
    for ticker, offset in (("A", 0), ("B", 30)):
        for field in captured.OHLCV_FIELDS:
            pd.testing.assert_series_equal(result.panels[field][ticker], frame(offset=offset)[field], check_names=False)
    assert result.panels["open"].at[DATES[-1], "A"] != result.panels["close"].at[DATES[-1], "A"]


@pytest.mark.parametrize("case", ["missing_open", "missing_prior_date", "mixed_tip", "newer_prior", "short_response"])
def test_incomplete_replacement_retains_all_five_prior_columns(case):
    prior, fresh = frame(), frame() * .5
    if case == "missing_open":
        fresh = fresh.drop(columns="open")
    elif case == "missing_prior_date":
        fresh.loc[DATES[2], "open"] = np.nan
    elif case == "mixed_tip":
        fresh.loc[DATES[-1], "volume"] = np.nan
    elif case == "newer_prior":
        fresh = fresh.iloc[:-1]
    else:
        fresh = fresh.iloc[-1:]
    result = merge({"A": prior}, {"A": fresh})
    assert result.unresolved == ("A",) and result.repaired == result.current == ()
    for field in captured.OHLCV_FIELDS:
        pd.testing.assert_series_equal(result.panels[field]["A"], prior[field], check_names=False, check_freq=False)


@pytest.mark.parametrize("prior_end,factor,null_suffix", [(6, .5, False), (3, 1.0, False), (6, .5, True)])
def test_complete_historical_replacement_is_accepted_but_not_current(prior_end, factor, null_suffix):
    prior = frame().iloc[:prior_end]
    fresh = frame().iloc[:-1] * factor
    if null_suffix:
        fresh = fresh.reindex(DATES)
    result = merge({"A": prior}, {"A": fresh})
    assert result.repaired == ("A",) and result.current == result.unresolved == ()
    assert result.reasons["A"] == "historical_only"
    for field in captured.OHLCV_FIELDS:
        pd.testing.assert_series_equal(result.panels[field]["A"], fresh[field], check_names=False, check_freq=False)


def test_one_genuine_ipo_bar_is_admitted_and_zero_volume_is_observed(monkeypatch):
    one = frame().iloc[-1:].copy(); one["volume"] = 0.0
    result, calls = acquire(monkeypatch, {"A": one})
    assert result.status == "complete" and result.current == result.acquired == ("A",)
    assert len(calls) == 1 and calls[0][1]["history_start"] == "2014-01-01"
    assert result.frames["A"].at[DATES[-1], "volume"] == 0
    assert result.evidence["members"]["A"]["observed_fields"]["open"]["count"] == 1
    assert result.evidence["unknown"]["provider_available_at"]


def test_excluded_history_is_preserved_without_download_or_current_claim(monkeypatch):
    prior = {"A": frame()}
    result, calls = acquire(monkeypatch, {}, prior, excluded=frozenset({"A"}))
    assert not calls and result.status == "partial"
    assert result.retained == ("A",) and result.current == result.acquired == ()
    pd.testing.assert_frame_equal(result.frames["A"], prior["A"])
    assert result.evidence["members"]["A"]["prior_qualification"] == "not_requalified"


@pytest.mark.parametrize("requested,aliases", [(("^VIX",), {}), (("A",), {"A": "^SPX"}),
    (("0700.HK",), {}), (("A", "B"), {"A": "AA", "B": "AA"})])
def test_invalid_cash_identity_is_refused_before_downloader(monkeypatch, requested, aliases):
    def forbidden(*args, **kwargs):
        raise AssertionError("provider must not be reached")
    monkeypatch.setattr(fetch, "_download_ohlcv", forbidden)
    with pytest.raises(ValueError, match="unique_us_cash"):
        fetch.acquire_ohlcv_from_inputs(requested=requested, prior_frames={}, aliases=aliases,
            excluded_symbols=frozenset(), request_settings=POLICY, history_start="2014-01-01",
            evaluation_instant=NOW)


@pytest.mark.parametrize("field,value", [("high", 90), ("open", 110), ("low", 108)])
def test_positive_but_impossible_bars_are_rejected(field, value):
    bad = frame(); bad.loc[DATES[0], field] = value
    with pytest.raises(ValueError, match="ohlcv_geometry"):
        captured.capture_ohlcv_panels(panels({"A": bad}), source_session=SOURCE)


def test_geometry_checks_preserve_different_panel_axes():
    data = panels({"A": frame()})
    data["open"] = data["open"].iloc[1:]
    result = captured.capture_ohlcv_panels(data, source_session=SOURCE)
    for field in data:
        pd.testing.assert_frame_equal(result[field], data[field])
    data["open"].iloc[0, 0] = 10000
    with pytest.raises(ValueError, match="ohlcv_geometry"):
        captured.capture_ohlcv_panels(data, source_session=SOURCE)


def test_placeholder_hole_retains_raw_span_and_refuses_archive_erasure(monkeypatch):
    raw = frame(); raw.loc[DATES[2], ["open", "high", "low", "close"]] = 0
    original = raw.copy(deep=True)
    result, _ = acquire(monkeypatch, {"A": raw}, {"A": frame()})
    assert result.unresolved == ("A",) and result.retained == ("A",)
    assert result.evidence["members"]["A"]["response_span"] == [str(DATES[0].date()), SOURCE]
    for field in captured.OHLCV_FIELDS:
        assert result.evidence["members"]["A"]["observed_fields"][field]["count"] == 6
    pd.testing.assert_frame_equal(result.frames["A"], frame())
    pd.testing.assert_frame_equal(raw, original)


def test_placeholder_target_suffix_keeps_actual_historical_clock(monkeypatch):
    raw = frame(); raw.loc[DATES[-1], ["open", "high", "low", "close"]] = -1
    result, _ = acquire(monkeypatch, {"A": raw}, {"A": frame().iloc[:-1]})
    assert result.status == "partial" and result.acquired == ("A",) and result.current == ()
    member = result.evidence["members"]["A"]
    assert member["reason"] == "historical_only" and member["response_span"][-1] == SOURCE
    assert member["selected_fields"]["close"]["last"] == "2026-11-02"
    assert result.evidence["current_session_shortfalls"] == ["A"]


def test_placeholder_only_ticker_has_no_observed_span(monkeypatch):
    raw = frame(); raw[["open", "high", "low", "close"]] = 0.0
    result, _ = acquire(monkeypatch, {"A": raw, "B": frame(offset=20)}, requested=("A", "B"))
    assert result.status == "partial" and result.current == ("B",)
    assert result.evidence["members"]["A"]["response_span"] is None
    assert "A" not in result.frames


@pytest.mark.parametrize("value", [-np.inf, np.inf, True, "0", 1+2j])
def test_invalid_scalars_cannot_disappear_inside_placeholder_cleanup(monkeypatch, value):
    raw = frame()
    for field in ("open", "high", "low", "close"):
        raw[field] = raw[field].astype(object) if isinstance(value, (bool, str, complex)) else raw[field]
        raw.loc[DATES[0], field] = value
    with pytest.raises(ValueError, match="invalid_adjusted_value"):
        acquire(monkeypatch, {"A": raw})


def test_negative_volume_is_not_a_price_placeholder(monkeypatch):
    raw = frame(); raw.loc[DATES[0], "volume"] = -1
    with pytest.raises(ValueError, match="invalid_adjusted_value"):
        acquire(monkeypatch, {"A": raw})


@pytest.mark.parametrize("multi", [True, False])
def test_incumbent_downloader_strict_branch_keeps_fields_spans_and_request_policy(monkeypatch, multi):
    import yfinance as yf
    raw = frame(); raw.loc[DATES[0], ["open", "high", "low", "close"]] = 0.0
    raw = raw.rename(columns=str.title)
    future = raw.iloc[-1:].copy(); future.index = pd.to_datetime(["2026-11-04"])
    raw = pd.concat([raw, future])
    response = pd.concat({"AA": raw}, axis=1) if multi else raw
    calls = []
    def download(batch, **kwargs):
        calls.append((batch, kwargs)); return response.copy(deep=True)
    monkeypatch.setattr(yf, "download", download)
    monkeypatch.setattr(fetch.time, "sleep", lambda _: None)
    result = fetch._download_ohlcv(["AA"], request_settings=POLICY,
        history_start="2014-01-01", source_session=SOURCE)
    assert len(calls) == 1 and calls[0][1]["auto_adjust"] is True
    assert calls[0][1]["group_by"] == "ticker" and calls[0][1]["start"] == "2014-01-01"
    assert list(result["AA"].columns) == list(captured.OHLCV_FIELDS)
    assert result["AA"].index.equals(DATES) and result["AA"].iloc[0].isna().all()
    assert result["AA"]["open"].iloc[-1] != result["AA"]["close"].iloc[-1]


def test_flat_multi_symbol_response_is_not_assigned_to_the_first_symbol(monkeypatch):
    import yfinance as yf
    calls = []
    monkeypatch.setattr(yf, "download", lambda batch, **kwargs: calls.append(batch) or frame().rename(columns=str.title))
    monkeypatch.setattr(fetch.time, "sleep", lambda _: None)
    assert fetch._download_ohlcv(["A", "B"], request_settings=POLICY,
        history_start="2014-01-01", source_session=SOURCE) == {}
    assert calls == [["A", "B"]]


def test_explicit_acquisition_has_no_ambient_reads_writes_or_input_aliases(monkeypatch):
    from lib import config, delisted_symbols, store
    def forbidden(*args, **kwargs):
        raise AssertionError("ambient acquisition or persistence reached")
    for owner, name in ((config, "load"), (config, "data_dir"), (delisted_symbols, "tickers"),
                        (store, "read"), (pd, "read_parquet"), (pd.DataFrame, "to_parquet")):
        monkeypatch.setattr(owner, name, forbidden)
    prior = {"A": frame().iloc[:-1].copy()}; snapshot = deepcopy(prior)
    result, calls = acquire(monkeypatch, {"AA": frame()}, prior, aliases={"A": "AA"})
    assert calls[0][0] == ["AA"] and result.status == "complete"
    pd.testing.assert_frame_equal(prior["A"], snapshot["A"])
    result.frames["A"].iloc[0, 0] = -10
    assert prior["A"].iloc[0, 0] > 0


@pytest.mark.parametrize("case", ["aligned", "basis", "missing_field", "missing_target", "full"])
def test_four_field_capture_and_merge_remain_exact_against_literal_original(case):
    path = Path(__file__).parent / "fixtures/base_adjusted_price_capture_4eddd4.py"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "d763d9bdbd8bbb8f4077b94f132f9178fcc14212d0be73d9ccaf65090778b307"
    spec = importlib.util.spec_from_file_location("frozen_adjusted_price_4eddd4", path)
    original = importlib.util.module_from_spec(spec); sys.modules[spec.name] = original; spec.loader.exec_module(original)
    prior = {"A": frame().iloc[:-1]}; fresh = {"A": frame()}
    if case == "basis": fresh["A"] = fresh["A"] * .5
    if case == "missing_field": fresh["A"] = fresh["A"].drop(columns="high")
    if case == "missing_target": fresh["A"] = fresh["A"].iloc[:-1]
    kwargs = dict(prior=panels(prior, captured.FIELDS), active=("A",), source_session=SOURCE,
                  basis_tolerance=.001, minimum_repair_sessions=3, full_replacement=case == "full")
    before = original.merge_adjusted_capture(fresh=observed(fresh, original.FIELDS, original), **kwargs)
    after = captured.merge_adjusted_capture(fresh=observed(fresh, captured.FIELDS), **kwargs)
    for field in captured.FIELDS:
        pd.testing.assert_frame_equal(after.panels[field], before.panels[field])
    for field in ("needs_repair", "repaired", "unresolved", "current", "reasons"):
        assert getattr(after, field) == getattr(before, field)
