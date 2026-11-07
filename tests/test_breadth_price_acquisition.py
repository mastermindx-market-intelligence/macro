"""Controlled breadth capture, shared legacy transport, and archive correctness."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from types import MappingProxyType

import numpy as np
import pandas as pd
import pytest

from collectors import breadth
from collectors.smallcap_breadth import SmallCapBreadthAdapter
from collectors.midcap_breadth import MidCap400BreadthAdapter
from lib import config, delisted_symbols, market_session
from lib import adjusted_price_capture as values

NOW = datetime(2026, 11, 3, 23, tzinfo=timezone.utc)
SOURCE = "2026-11-03"
CFG = {"ma_windows": [50, 200], "nhnl_window": 252, "lookback_days_live": 1100, "ticker_fixups": {}}
YCFG = {"batch_size": 1000, "retries": 2, "backoff_base_s": 0, "upsert_basis_tol": .001}


@pytest.fixture(scope="module")
def panels():
    index = pd.bdate_range(end=SOURCE, periods=350)
    index = index[[market_session.is_session_date("US", t.date()) for t in index]][-300:].as_unit("ns")
    symbols = [f"T{i:04d}" for i in range(600)]
    close = pd.DataFrame(100 + np.arange(len(index))[:, None] / 10 + np.arange(len(symbols))[None, :] / 20,
                         index=index, columns=symbols)
    return {"close": close, "high": close + 2, "low": close - 2, "volume": close * 0 + 1000}


def members(count=400):
    return pd.DataFrame({"symbol": [f"T{i:04d}" for i in range(count)],
                         "name": [f"Company {i}" for i in range(count)], "sector": ["Industrials"] * count})


def selected(panels, count=400):
    return {field: panel.iloc[:, :count].copy(deep=True) for field, panel in panels.items()}


def capture(panels, symbols):
    panels = {field: panel.reindex(columns=symbols).copy(deep=True) for field, panel in panels.items()}
    span = (panels["close"].index[0], panels["close"].index[-1])
    return values.AdjustedPriceCapture(panels, {ticker: span for ticker in symbols}, tuple(symbols))


def forbidden(*args, **kwargs):
    raise AssertionError("ambient config/path/ledger/write reached")


def install_provider(monkeypatch, panels, calls, transform=None):
    def download(batch, *, period, **kwargs):
        calls.append((tuple(batch), period, kwargs))
        raw = {field: panel.reindex(columns=batch) for field, panel in panels.items()}
        if period == "1mo": raw = {field: panel.iloc[-25:] for field, panel in raw.items()}
        if transform is not None: raw = transform(batch, period, raw)
        return pd.concat({vendor: raw[field] for field, vendor in
            zip(values.FIELDS, ("Close", "High", "Low", "Volume"))}, axis=1)
    monkeypatch.setattr(breadth.yf, "download", download)
    monkeypatch.setattr(breadth.time, "sleep", lambda seconds: None)


def acquire(adapter, prior, *, population=None, aliases=None, period="1mo", exclusions=frozenset()):
    return adapter.acquire_adjusted_prices(members=members() if population is None else population,
        prior_panels=prior, excluded_symbols=exclusions, aliases={} if aliases is None else aliases,
        evaluation_instant=NOW, period=period)


def test_explicit_acquisition_has_no_ambient_reads_or_legacy_effects(panels, monkeypatch):
    for owner, name in [(config, "load"), (config, "data_dir"), (delisted_symbols, "tickers"),
                        (pd, "read_parquet"), (pd.DataFrame, "to_parquet")]:
        monkeypatch.setattr(owner, name, forbidden)
    cfg, ycfg = deepcopy(CFG), deepcopy(YCFG)
    adapter = breadth.BreadthAdapter(breadth_config=cfg, yahoo_config=ycfg)
    cfg["ma_windows"][0] = 999; ycfg["batch_size"] = 1
    prior = selected(panels)
    for field in prior: prior[field] = prior[field].iloc[:-1]
    snapshots = {field: panel.copy(deep=True) for field, panel in prior.items()}
    calls = []; install_provider(monkeypatch, panels, calls)
    result = acquire(adapter, prior)
    assert result.accepted and result.current == tuple(members()["symbol"])
    assert len(calls) == 1 and calls[0][1] == "1mo"
    assert calls[0][2]["auto_adjust"] is True and calls[0][2]["group_by"] == "column"
    assert result.evidence["request"]["batch_size"] == 1000
    assert result.source_session == SOURCE and result.evidence["required_current"] == 320
    assert not hasattr(adapter, "_last_extras") and adapter.cache_path is None
    for field in prior:
        pd.testing.assert_frame_equal(prior[field], snapshots[field])
        assert result.panels[field].index[-1] == pd.Timestamp(SOURCE)
    result.panels["close"].iloc[0, 0] = -999
    assert prior["close"].iloc[0, 0] > 0
    with pytest.raises(ValueError, match="Explicit breadth configuration"):
        adapter.fetch()


@pytest.mark.parametrize("klass,floor", [(breadth.BreadthAdapter, 400), (SmallCapBreadthAdapter, 450), (MidCap400BreadthAdapter, 350)])
def test_each_constituent_floor_applies_after_repair_dedup_exclusion(panels, monkeypatch, klass, floor):
    adapter = klass(breadth_config=CFG, yahoo_config=YCFG)
    monkeypatch.setattr(adapter, "_download_adjusted_capture", forbidden)
    population = pd.concat([members(floor - 1), members(1)], ignore_index=True)
    with pytest.raises(ValueError, match="suspicious"):
        acquire(adapter, selected(panels), population=population)
    with pytest.raises(ValueError, match="suspicious"):
        acquire(adapter, selected(panels), population=members(floor), exclusions=frozenset({"T0000"}))


@pytest.mark.parametrize("available,accepted", [(319, False), (320, True)])
def test_target_coverage_ignores_historical_and_departed_columns(panels, monkeypatch, available, accepted):
    prior = selected(panels)
    for field in prior: prior[field]["OLDONE"] = prior[field].iloc[:, 0]
    def transform(batch, period, raw):
        for field in raw: raw[field] = raw[field].copy(); raw[field].iloc[:, available:] = np.nan
        return raw
    calls = []; install_provider(monkeypatch, panels, calls, transform)
    result = acquire(breadth.BreadthAdapter(breadth_config=CFG, yahoo_config=YCFG), prior, period="max")
    assert result.accepted is accepted and len(result.current) == available
    assert result.departed == ("OLDONE",)
    assert len(result.unresolved) == 400 - available
    for field in prior: pd.testing.assert_series_equal(result.panels[field]["OLDONE"], prior[field]["OLDONE"])
    assert "T0399" not in result.current and result.panels["close"].at[pd.Timestamp(SOURCE), "T0399"] > 0
    assert len(calls) == 1


def test_three_adjusted_price_fields_and_volume_repair_together(panels, monkeypatch):
    prior = selected(panels)
    fresh = selected(panels)
    for field in values.PRICES: fresh[field]["T0000"] *= 1.01
    calls = []; install_provider(monkeypatch, fresh, calls)
    result = acquire(breadth.BreadthAdapter(breadth_config=CFG, yahoo_config=YCFG), prior)
    assert result.accepted and result.repaired == ("T0000",) and not result.unresolved
    assert [(len(c[0]), c[1]) for c in calls] == [(400, "1mo"), (1, "max")]
    for field in values.FIELDS:
        pd.testing.assert_series_equal(result.panels[field]["T0000"], fresh[field]["T0000"])
    assert result.evidence["members"]["T0000"]["repair_reason"] == "basis_unqualified"


@pytest.mark.parametrize("mode", ["thin", "missing_middle", "field_gap", "provider_failure"])
def test_failed_or_thin_repair_preserves_original_whole_column(panels, monkeypatch, mode):
    prior = selected(panels)
    fresh = selected(panels)
    for field in values.PRICES: fresh[field]["T0000"] *= .5
    def transform(batch, period, raw):
        if period == "max":
            if mode == "provider_failure": raise RuntimeError("controlled provider failure")
            raw = {field: panel.copy(deep=True) for field, panel in raw.items()}
            if mode == "thin": raw = {field: panel.iloc[-1:] for field, panel in raw.items()}
            if mode == "missing_middle":
                for field in raw: raw[field].iloc[100, :] = np.nan
            if mode == "field_gap": raw["volume"].iloc[100, :] = np.nan
        return raw
    calls = []; install_provider(monkeypatch, fresh, calls, transform)
    result = acquire(breadth.BreadthAdapter(breadth_config=CFG, yahoo_config=YCFG), prior)
    assert result.accepted and result.unresolved == ("T0000",) and not result.repaired
    assert "T0000" not in result.current
    for field in values.FIELDS:
        pd.testing.assert_series_equal(result.panels[field]["T0000"], prior[field]["T0000"])


def test_fresh_span_owns_nulls_and_omitted_dates_in_every_field(panels):
    prior = {field: panel.iloc[:, :1].copy() for field, panel in panels.items()}
    fresh = {field: panel.iloc[-25:].copy() for field, panel in prior.items()}
    missing = fresh["close"].index[10]
    for field in fresh:
        fresh[field] = fresh[field].drop(index=missing)
        fresh[field].iloc[5, 0] = np.nan
    result = values.merge_adjusted_capture(prior=prior, fresh=capture(fresh, ("T0000",)), active=("T0000",),
        source_session=SOURCE, basis_tolerance=.001, minimum_repair_sessions=252)
    assert not result.needs_repair and result.current == ("T0000",)
    for field in values.FIELDS:
        assert pd.isna(result.panels[field].at[missing, "T0000"])
        assert pd.isna(result.panels[field].at[fresh[field].index[5], "T0000"])
        assert result.panels[field].iloc[0, 0] == prior[field].iloc[0, 0]


def test_stale_initial_target_does_not_borrow_a_current_prior(panels):
    prior = {field: panel.iloc[:, :1].copy() for field, panel in panels.items()}
    fresh = {field: panel.iloc[-25:-1].copy() for field, panel in prior.items()}
    result = values.merge_adjusted_capture(prior=prior, fresh=capture(fresh, ("T0000",)), active=("T0000",),
        source_session=SOURCE, basis_tolerance=.001, minimum_repair_sessions=252)
    assert not result.current and result.unresolved == ("T0000",)
    assert result.panels["close"].at[pd.Timestamp(SOURCE), "T0000"] == prior["close"].iloc[-1, 0]


def test_repair_requires_joint_history_not_separate_field_counts(panels):
    sample = {field: panel.iloc[:, :1].copy() for field, panel in panels.items()}
    for number, field in enumerate(values.FIELDS):
        keep = list(range(number * 50, number * 50 + 100)) + [299]
        sample[field].loc[~sample[field].index.isin(sample[field].index[keep]), "T0000"] = np.nan
    result = values.merge_adjusted_capture(prior={field: None for field in values.FIELDS},
        fresh=capture(sample, ("T0000",)), active=("T0000",), source_session=SOURCE,
        basis_tolerance=.001, minimum_repair_sessions=100, full_replacement=True)
    assert result.unresolved == ("T0000",) and not result.current
    assert result.panels["close"]["T0000"].isna().all()


@pytest.mark.parametrize("kind", ["collision", "invalid"])
def test_alias_mapping_refuses_before_provider(panels, monkeypatch, kind):
    adapter = breadth.BreadthAdapter(breadth_config=CFG, yahoo_config=YCFG)
    monkeypatch.setattr(adapter, "_download_adjusted_capture", forbidden)
    aliases = {"T0000": "T0001" if kind == "collision" else "../bad"}
    with pytest.raises(values.AdjustedCaptureError, match="vendor_alias_collision_or_invalid"):
        acquire(adapter, selected(panels), aliases=aliases)


def test_requested_alias_identity_is_remapped_without_global_inverse(panels, monkeypatch):
    prior = selected(panels)
    vendor = {field: panel.rename(columns={"T0000": "RENAMED"}) for field, panel in panels.items()}
    calls = []; install_provider(monkeypatch, vendor, calls)
    result = acquire(breadth.BreadthAdapter(breadth_config=CFG, yahoo_config=YCFG), prior,
        aliases={"T0000": "RENAMED", "UNREQUESTED": "T0001"})
    assert result.accepted and "T0000" in result.current and "RENAMED" not in result.panels["close"]
    assert calls[0][0][0] == "RENAMED"
    assert result.evidence["members"]["T0000"]["vendor_symbol"] == "RENAMED"


@pytest.mark.parametrize("mode", ["multi", "flat", "retry", "empty_extras"])
def test_shared_transport_preserves_frozen_legacy_downloader(panels, monkeypatch, mode):
    import importlib.util
    from pathlib import Path
    fixture = Path(__file__).parent / "fixtures/base_breadth_download_c3cd.py"
    spec = importlib.util.spec_from_file_location("frozen_breadth_download", fixture)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    state = {"calls": [], "sleeps": [], "attempt": 0}
    def download(batch, **kwargs):
        state["attempt"] += 1
        state["calls"].append((tuple(batch), kwargs))
        if mode == "retry" and state["attempt"] == 1: raise RuntimeError("controlled first failure")
        raw = pd.concat({vendor: panels[field].iloc[-10:].reindex(columns=batch)
            for field, vendor in zip(values.FIELDS, ("Close", "High", "Low", "Volume"))}, axis=1)
        if mode == "flat": raw.columns = raw.columns.get_level_values(0)
        if mode == "empty_extras": raw = raw[["Close"]]
        return raw
    monkeypatch.setattr(breadth.yf, "download", download)
    monkeypatch.setattr(breadth.time, "sleep", lambda seconds: state["sleeps"].append(seconds))
    original = module.FrozenBreadthDownload(); original.ycfg = {**YCFG, "batch_size": 2, "backoff_base_s": .1}
    candidate = breadth.BreadthAdapter(breadth_config=CFG, yahoo_config=original.ycfg)
    tickers = ["T0000"] if mode == "flat" else ["T0000", "T0001", "T0002"]
    expected = original._download_closes(tickers, "1mo")
    events = deepcopy(state)
    state.update(calls=[], sleeps=[], attempt=0)
    actual = candidate._download_closes(tickers, "1mo")
    assert state == events
    pd.testing.assert_frame_equal(actual, expected)
    assert set(candidate._last_extras) == set(original._last_extras)
    for field in original._last_extras:
        pd.testing.assert_frame_equal(candidate._last_extras[field], original._last_extras[field])


def test_same_count_repair_cannot_delete_a_prior_observation(panels):
    prior = {field: panel.iloc[:, :1].copy() for field, panel in panels.items()}
    next_target = pd.Timestamp("2026-11-04")
    replacement = {}
    for field, panel in prior.items():
        extension = panel.iloc[[-1]].copy(); extension.index = pd.DatetimeIndex([next_target])
        replacement[field] = pd.concat([panel, extension]).drop(index=panel.index[100])
    assert len(replacement["close"]) == len(prior["close"])
    result = values.merge_adjusted_capture(prior=prior, fresh=capture(replacement, ("T0000",)),
        active=("T0000",), source_session="2026-11-04", basis_tolerance=.001,
        minimum_repair_sessions=252, full_replacement=True)
    assert result.unresolved == ("T0000",) and not result.current
    for field in values.FIELDS:
        assert result.panels[field].at[prior[field].index[100], "T0000"] == prior[field].iloc[100, 0]
        assert pd.isna(result.panels[field].at[next_target, "T0000"])


@pytest.mark.parametrize("kind", ["timezone", "unsorted", "duplicate", "nonfinite", "negative_volume", "unknown_symbol", "flat_batch"])
def test_malformed_provider_response_refuses_without_repair(panels, kind):
    raw = pd.concat({vendor: panels[field].iloc[-5:, :2].copy()
        for field, vendor in zip(values.FIELDS, ("Close", "High", "Low", "Volume"))}, axis=1)
    if kind == "timezone": raw.index = raw.index.tz_localize("UTC")
    elif kind == "unsorted": raw = raw.iloc[::-1]
    elif kind == "duplicate": raw.index = pd.DatetimeIndex([raw.index[0], *raw.index[:-1]])
    elif kind == "nonfinite": raw.iloc[-1, 0] = np.inf
    elif kind == "negative_volume": raw.loc[raw.index[-1], ("Volume", "T0000")] = -1
    elif kind == "unknown_symbol": raw = raw.rename(columns={"T0000": "FOREIGN"}, level=1)
    else: raw.columns = raw.columns.get_level_values(0)
    with pytest.raises(values.AdjustedCaptureError):
        values.capture_adjusted_response(raw, requested=("T0000", "T0001"), source_session=SOURCE)


def test_completed_target_excludes_live_provider_tail_and_preserves_zero_volume(panels):
    raw_panels = {field: panel.iloc[-5:, :1].copy() for field, panel in panels.items()}
    for field, panel in raw_panels.items():
        tail = panel.iloc[[-1]].copy(); tail.index = pd.DatetimeIndex(["2026-11-04"])
        raw_panels[field] = pd.concat([panel, tail])
    raw_panels["volume"].loc[pd.Timestamp(SOURCE), "T0000"] = 0
    raw = pd.concat({vendor: raw_panels[field] for field, vendor in zip(values.FIELDS, ("Close", "High", "Low", "Volume"))}, axis=1)
    captured = values.capture_adjusted_response(raw, requested=("T0000",), source_session=SOURCE)
    assert captured.spans["T0000"][1] == pd.Timestamp(SOURCE)
    assert captured.panels["volume"].at[pd.Timestamp(SOURCE), "T0000"] == 0
    assert all(frame.index[-1] == pd.Timestamp(SOURCE) for frame in captured.panels.values())


def test_capture_and_union_bounds_precede_allocation(panels, monkeypatch):
    prior = {field: panel.iloc[-5:, :1].copy() for field, panel in panels.items()}
    monkeypatch.setattr(values, "MAX_PANEL_CELLS", 4)
    with pytest.raises(values.AdjustedCaptureError, match="invalid_adjusted_panel"):
        values.capture_panels(prior, source_session=SOURCE)
    monkeypatch.setattr(values, "MAX_PANEL_CELLS", 5)
    fresh = {field: panel.rename(columns={"T0000": "T0001"}) for field, panel in prior.items()}
    with pytest.raises(values.AdjustedCaptureError, match="adjusted_union_bound"):
        values.merge_adjusted_capture(prior=prior, fresh=capture(fresh, ("T0001",)), active=("T0001",),
            source_session=SOURCE, basis_tolerance=.001, minimum_repair_sessions=1)


def test_declared_span_cannot_hide_observations_outside_it(panels):
    prior = {field: panel.iloc[-10:, :1].copy() for field, panel in panels.items()}
    forged = values.AdjustedPriceCapture(prior,
        {"T0000": (prior["close"].index[-5], prior["close"].index[-1])}, ("T0000",))
    with pytest.raises(values.AdjustedCaptureError, match="observations_outside_fresh_span"):
        values.merge_adjusted_capture(prior=prior, fresh=forged, active=("T0000",),
            source_session=SOURCE, basis_tolerance=.001, minimum_repair_sessions=1)


@pytest.mark.parametrize("kind", ["sector_list", "sector_dict", "name_dict", "oversized_alias"])
def test_unsafe_membership_and_alias_fail_before_request(panels, monkeypatch, kind):
    adapter = breadth.BreadthAdapter(breadth_config=CFG, yahoo_config=YCFG)
    monkeypatch.setattr(adapter, "_download_adjusted_capture", forbidden)
    population = members().astype({"name": object, "sector": object})
    aliases = {}
    if kind == "sector_list": population.at[0, "sector"] = ["Industrials"]
    elif kind == "sector_dict": population.at[0, "sector"] = {"name": "Industrials"}
    elif kind == "name_dict": population.at[0, "name"] = {"name": "Issuer"}
    else: aliases = {"T0000": "A" * 25}
    with pytest.raises(values.AdjustedCaptureError):
        acquire(adapter, selected(panels), population=population, aliases=aliases)
