"""Extras acquisition proves the actual thematic selection, without legacy effects."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from scripts import fetch_basket_extras as extras
from lib import config, adjusted_price_capture as values
from lib.closes_panel import resolve_thematic_close_panel

NOW = datetime(2026, 11, 3, 23, tzinfo=timezone.utc)
SOURCE = "2026-11-03"
POLICY = {"batch_size": 60, "retries": 2, "backoff_base_s": 0}


@pytest.fixture
def tapes():
    index = pd.bdate_range(end=SOURCE, periods=12).as_unit("ns")
    primary = pd.DataFrame({"DEEP": 100 + np.arange(12), "TIE": 200 + np.arange(12),
                            "LAG": 300 + np.arange(12)}, index=index, dtype=float)
    prior = pd.DataFrame({"TIE": 190 + np.arange(12), "LAG": 300 + np.arange(12),
                         "OLD": 90 + np.arange(12)}, index=index, dtype=float)
    prior.loc[index[-1], "LAG"] = np.nan
    provider = primary.copy()
    provider["IPO"] = np.nan
    provider.loc[index[-2:], "IPO"] = [20, 21]
    return primary, prior, provider


def membership(*symbols):
    return {"baskets": {"fixture": {"members": [{"ticker": ticker} for ticker in symbols]}}}


def forbidden(*args, **kwargs):
    raise AssertionError("legacy config/path/proxy/writer reached")


def provider(monkeypatch, panel, calls, *, transform=None):
    import yfinance as yf
    def download(batch, **kwargs):
        calls.append((tuple(batch), deepcopy(kwargs)))
        raw = panel.reindex(columns=batch).copy(deep=True)
        raw = raw.loc[raw.index >= pd.Timestamp(kwargs["start"])]
        if transform is not None: raw = transform(batch, raw)
        return pd.concat({"Close": raw, "High": raw + 1, "Low": raw - 1, "Volume": raw * 0 + 100}, axis=1)
    monkeypatch.setattr(yf, "download", download)
    monkeypatch.setattr(extras.time, "sleep", lambda seconds: None)


def acquire(primary, prior, *symbols, **kwargs):
    arguments = dict(membership=membership(*symbols), primary_panel=primary, prior_extras=prior,
        qualified_primary_members=frozenset(primary.columns), primary_history_threshold=5,
        evaluation_instant=NOW, yahoo_config=POLICY, aliases={}, history_start="2023-01-01")
    arguments.update(kwargs)
    return extras.acquire_extras_from_inputs(**arguments)


def test_actual_selection_controls_skip_and_same_date_correction(tapes, monkeypatch):
    primary, prior, fresh = tapes
    calls = []; provider(monkeypatch, fresh, calls)
    result = acquire(primary, prior, "DEEP", "LAG", "TIE")
    assert result.status == "complete" and result.downloaded == ("TIE",)
    assert [c[0] for c in calls] == [("TIE",)]
    assert result.evidence["skipped_qualified_primary"] == ["DEEP", "LAG"]
    pd.testing.assert_series_equal(result.archive["TIE"], fresh["TIE"])
    pd.testing.assert_series_equal(result.archive["OLD"], prior["OLD"])
    assert result.resolution["selection_reason"]["TIE"] == "tie_supplemental"
    assert result.evidence["members"]["TIE"]["chosen_acquired_this_attempt"] is True
    assert result.evidence["members"]["TIE"]["target_observed"] is True
    assert result.evidence["members"]["TIE"]["chosen_prior_retained"] is False
    assert result.resolution["source_basis"]["primary_breadth"] == "unrecorded"
    assert result.resolution["adjustment_vintage"] == "unrecorded"
    assert result.evidence["members"]["TIE"]["acquisition_basis"] == "provider_auto_adjusted"


def test_current_retained_tie_is_not_a_successful_refresh(tapes, monkeypatch):
    primary, prior, fresh = tapes
    def failing(batch, raw): raise RuntimeError("controlled outage")
    calls = []; provider(monkeypatch, fresh, calls, transform=failing)
    result = acquire(primary, prior, "TIE")
    assert result.status == "partial" and result.unresolved == ("TIE",) and not result.downloaded
    pd.testing.assert_frame_equal(result.archive, prior.reindex(columns=sorted(prior.columns)))
    fact = result.evidence["members"]["TIE"]
    assert fact["target_observed"] is True and fact["chosen_prior_retained"] is True
    assert fact["refresh_unresolved"] is True and fact["chosen_acquired_this_attempt"] is False
    assert fact["refresh_reason"] == "download_failed" and fact["acquisition_basis"] is None
    assert len(calls) == 2


def test_recent_ipo_keeps_actual_short_history_without_depth_gate(tapes, monkeypatch):
    primary, _, fresh = tapes
    calls = []; provider(monkeypatch, fresh, calls)
    result = acquire(primary, None, "IPO", primary_history_threshold=1000)
    assert result.status == "complete" and result.downloaded == ("IPO",)
    fact = result.evidence["members"]["IPO"]
    assert fact["selected_history_sessions"] == 2 and fact["target_observed"] is True
    assert result.archive["IPO"].notna().sum() == 2
    assert result.archive["IPO"].iloc[:-2].isna().all()
    assert result.effective_as_of == SOURCE


@pytest.mark.parametrize("kind", ["thin", "missing_middle", "start_excludes_prior"])
def test_replacement_cannot_erase_established_history(tapes, monkeypatch, kind):
    primary, prior, fresh = tapes
    def transform(batch, raw):
        if kind == "thin": return raw.iloc[[-1]]
        if kind == "missing_middle": return raw.drop(index=raw.index[5])
        return raw
    calls = []; provider(monkeypatch, fresh, calls, transform=transform)
    start = "2026-11-02" if kind == "start_excludes_prior" else "2023-01-01"
    result = acquire(primary, prior, "TIE", history_start=start)
    assert result.unresolved == ("TIE",) and not result.downloaded
    pd.testing.assert_series_equal(result.archive["TIE"], prior["TIE"])
    assert all(call[1]["start"] == start for call in calls)


def test_extras_cannot_advance_the_frozen_primary_calendar(tapes, monkeypatch):
    primary, prior, fresh = tapes
    primary = primary.iloc[:-1]
    calls = []; provider(monkeypatch, fresh, calls)
    result = acquire(primary, prior, "TIE")
    assert result.downloaded == ("TIE",) and result.source_session == SOURCE
    assert result.effective_as_of == "2026-11-02"
    assert result.resolved_panel.index[-1] == pd.Timestamp("2026-11-02")
    fact = result.evidence["members"]["TIE"]
    assert fact["returned_span"][-1] == SOURCE and fact["target_observed"] is False
    assert fact["desk_observed"] is True and result.status == "partial"


def test_primary_skip_requires_qualified_actual_column_and_depth(tapes, monkeypatch):
    primary, _, fresh = tapes
    primary["DEEP"] = np.nan
    primary.loc[primary.index[-2:], "DEEP"] = fresh["DEEP"].iloc[-2:]
    calls = []; provider(monkeypatch, fresh, calls)
    result = acquire(primary, None, "DEEP", "LAG", qualified_primary_members=frozenset({"DEEP"}))
    assert result.evidence["skipped_qualified_primary"] == []
    assert set(calls[0][0]) == {"DEEP", "LAG"}
    assert set(result.downloaded) == {"DEEP", "LAG"}


def test_explicit_extras_has_no_legacy_reads_writes_or_proxy_seed(tapes, monkeypatch):
    primary, prior, fresh = tapes
    for owner, name in [(config, "load"), (config, "data_dir"), (pd, "read_parquet"),
        (pd.DataFrame, "to_parquet"), (extras, "_seed_proxies"), (extras, "_membership_tickers"),
        (extras, "_deep_cache_columns")]: monkeypatch.setattr(owner, name, forbidden)
    calls = []; provider(monkeypatch, fresh, calls)
    result = acquire(primary, prior, "TIE")
    assert result.status == "complete" and len(calls) == 1


def test_request_and_inputs_detach_before_provider_mutation(tapes, monkeypatch):
    primary, prior, fresh = tapes
    old = prior.copy(deep=True)
    document = membership("TIE")
    aliases = {"TIE": "RENAMED"}
    policy = dict(POLICY)
    vendor = fresh.rename(columns={"TIE": "RENAMED"})
    def mutate(batch, raw):
        primary.loc[:, "TIE"] = 9999
        prior.loc[:, "OLD"] = 9999
        document["baskets"]["fixture"]["members"][0]["ticker"] = "CHANGED"
        aliases["TIE"] = "CHANGED"
        policy["retries"] = 99
        return raw
    calls = []; provider(monkeypatch, vendor, calls, transform=mutate)
    result = acquire(primary, prior, "TIE", membership=document, aliases=aliases, yahoo_config=policy)
    assert result.requested == ("TIE",) and result.downloaded == ("TIE",)
    assert result.evidence["request"]["retries"] == 2
    assert result.evidence["members"]["TIE"]["vendor_symbol"] == "RENAMED"
    pd.testing.assert_series_equal(result.archive["OLD"], old["OLD"])
    assert result.resolved_panel["TIE"].iloc[-1] == fresh["TIE"].iloc[-1]


def test_membership_effective_dates_use_existing_population_owner(tapes, monkeypatch):
    primary, prior, fresh = tapes
    document = membership("TIE", "DEEP", "LAG")
    document["baskets"]["fixture"]["members"][1]["added"] = "2026-11-04"
    document["baskets"]["fixture"]["members"][2]["removed"] = "2026-11-03"
    calls = []; provider(monkeypatch, fresh, calls)
    result = acquire(primary, prior, membership=document)
    assert result.requested == ("DEEP", "LAG", "TIE")
    assert result.evidence["basket_populations"]["fixture"] == ["TIE"]
    assert result.evidence["currently_eligible"] == ["TIE"]
    assert result.evidence["no_visible_history_obligation"] == ["DEEP"]
    assert "LAG" in result.resolved_panel
    assert calls[0][0] == ("TIE",)


@pytest.mark.parametrize("kind", ["alias_collision", "oversized_alias", "bad_date", "naive_clock", "future_prior"])
def test_invalid_inputs_refuse_before_any_provider(tapes, monkeypatch, kind):
    primary, prior, _ = tapes
    monkeypatch.setattr(extras, "_download_closes", forbidden)
    kwargs = {}
    if kind == "alias_collision": kwargs["aliases"] = {"TIE": "LAG"}
    elif kind == "oversized_alias": kwargs["aliases"] = {"TIE": "A" * 25}
    elif kind == "bad_date": kwargs["history_start"] = "2026-02-30"
    elif kind == "naive_clock": kwargs["evaluation_instant"] = NOW.replace(tzinfo=None)
    else:
        prior = prior.copy(); prior.index = pd.bdate_range(end="2026-11-04", periods=len(prior))
    with pytest.raises(values.AdjustedCaptureError): acquire(primary, prior, "TIE", "LAG", **kwargs)


def test_explicit_basis_receipt_is_detached_and_legacy_default_retained(tapes):
    primary, prior, _ = tapes
    _, legacy = resolve_thematic_close_panel(primary, prior, ["TIE"])
    assert legacy["source_basis"] == {"primary_breadth": "closes_cache_UNADJUSTED", "baskets_extras": "tradj"}
    basis = {"primary_breadth": "provider_auto_adjusted", "baskets_extras": "unrecorded"}
    _, explicit = resolve_thematic_close_panel(primary, prior, ["TIE"], source_basis=basis)
    basis["primary_breadth"] = "changed"
    assert explicit["source_basis"]["primary_breadth"] == "provider_auto_adjusted"
    assert explicit["adjustment_vintage"] == "unrecorded"
    assert explicit["price_source"] == legacy["price_source"] and explicit["selection_reason"] == legacy["selection_reason"]



def test_unobserved_primary_tail_cannot_be_advanced_by_extras(tapes, monkeypatch):
    primary, prior, _ = tapes
    primary.iloc[-1, :] = np.nan
    monkeypatch.setattr(extras, "_download_closes", forbidden)
    with pytest.raises(values.AdjustedCaptureError, match="observed_frozen_primary_tail_required"):
        acquire(primary, prior, "TIE")


def test_removed_member_history_is_resolved_and_can_be_backfilled(tapes, monkeypatch):
    primary, prior, fresh = tapes
    document = membership("TIE", "LAG")
    document["baskets"]["fixture"]["members"][1]["removed"] = "2026-11-03"
    primary["LAG"] = np.nan
    prior = prior.drop(columns="LAG")
    fresh.loc[fresh.index[-1], "LAG"] = np.nan
    calls = []; provider(monkeypatch, fresh, calls)
    result = acquire(primary, prior, membership=document)
    assert result.downloaded == ("LAG", "TIE") and result.status == "complete"
    assert "LAG" in result.resolved_panel and result.resolved_panel["LAG"].notna().sum() == 11
    fact = result.evidence["members"]["LAG"]
    assert fact["currently_eligible"] is False and fact["target_observed"] is False
    assert fact["required_history_end"] == "2026-11-02" and fact["required_history_end_observed"] is True


def test_resolver_projection_bound_precedes_any_resolver_allocation(tapes, monkeypatch):
    import lib.closes_panel as owner
    primary, _, _ = tapes
    primary = primary[["DEEP"]]
    prior = pd.DataFrame({"TIE": [1.0], "LAG": [2.0]}, index=primary.index[-1:])
    monkeypatch.setattr(values, "MAX_PANEL_CELLS", len(primary))
    monkeypatch.setattr(owner, "resolve_thematic_close_panel", forbidden)
    monkeypatch.setattr(extras, "_download_closes", forbidden)
    with pytest.raises(values.AdjustedCaptureError, match="extras_resolver_projection_bound"):
        acquire(primary, prior, "TIE", "LAG")



def test_successful_historical_download_does_not_prove_final_selection(tapes, monkeypatch):
    primary, _, fresh = tapes
    primary["LAG"] = np.nan
    primary.loc[primary.index[-1], "LAG"] = 999
    fresh["LAG"] = np.nan
    fresh.loc[fresh.index[-2], "LAG"] = 200
    document = membership("LAG")
    document["baskets"]["fixture"]["members"][0]["removed"] = "2026-11-03"
    calls = []; provider(monkeypatch, fresh, calls)
    result = acquire(primary, None, membership=document)
    assert result.downloaded == ("LAG",) and not result.unresolved
    assert result.archive["LAG"].loc[pd.Timestamp("2026-11-02")] == 200
    fact = result.evidence["members"]["LAG"]
    assert fact["selected_source"] == "primary_breadth" and fact["required_history_end_observed"] is False
    assert result.evidence["selection_history_shortfalls"] == ["LAG"]
    assert fact["selection_history_shortfall"] is True and result.status == "partial"


@pytest.mark.parametrize("mode", ["multi", "flat", "retry"])
def test_explicit_extension_preserves_literal_legacy_extras_downloader(tapes, monkeypatch, mode):
    import importlib.util
    from pathlib import Path
    import yfinance as yf
    path = Path(__file__).parent / "fixtures/base_extras_download_765cd.py"
    spec = importlib.util.spec_from_file_location("frozen_extras_download", path)
    original = importlib.util.module_from_spec(spec); spec.loader.exec_module(original)
    monkeypatch.setattr(original, "BATCH", 2); monkeypatch.setattr(extras, "BATCH", 2)
    panel = tapes[2]
    state = {"calls": [], "sleeps": [], "attempt": 0}
    def download(batch, **kwargs):
        state["attempt"] += 1; state["calls"].append((tuple(batch), deepcopy(kwargs)))
        if mode == "retry" and state["attempt"] == 1: raise RuntimeError("controlled first failure")
        frame = pd.concat({"Close": panel.reindex(columns=batch)}, axis=1)
        if mode == "flat": frame.columns = frame.columns.get_level_values(0)
        return frame
    monkeypatch.setattr(yf, "download", download)
    monkeypatch.setattr(extras.time, "sleep", lambda seconds: state["sleeps"].append(seconds))
    tickers = ["DEEP"] if mode == "flat" else ["DEEP", "LAG", "TIE"]
    expected = original._download_closes(tickers)
    events = deepcopy(state); state.update(calls=[], sleeps=[], attempt=0)
    actual = extras._download_closes(tickers)
    pd.testing.assert_frame_equal(actual, expected)
    assert state == events
