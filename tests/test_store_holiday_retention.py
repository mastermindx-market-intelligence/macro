"""Adjusted-store retention when a holiday-time vendor response falls behind.

Every parquet and quarantine output is redirected to tmp_path. Stale windows
must never delete newer retained data or splice a changed older basis into it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lib import config, store


@pytest.fixture
def cached(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    index = pd.bdate_range("2026-09-21", "2026-09-30")
    old = pd.DataFrame({
        "close": np.arange(len(index), dtype=float) + 100,
        "volume": np.arange(len(index), dtype=float) + 1000,
    }, index=index)
    store.upsert("holiday_fixture", "TEST", old)
    path = tmp_path / "holiday_fixture" / "TEST.parquet"
    return old, path


def assert_retained(old, path, before):
    assert path.read_bytes() == before
    pd.testing.assert_frame_equal(store.read("holiday_fixture", "TEST"), old, check_freq=False)


@pytest.mark.parametrize("basis_factor", [1.0, 0.5])
def test_older_window_rejected_without_erasing_latest_or_mixing_basis(cached, basis_factor):
    old, path = cached
    before = path.read_bytes()
    stale = old.iloc[2:-2].copy()
    stale["close"] *= basis_factor

    with pytest.raises(ValueError, match="stale.*overwrite_overlap.*retained"):
        store.upsert("holiday_fixture", "TEST", stale, overwrite_overlap=True)

    assert_retained(old, path, before)


@pytest.mark.parametrize("incoming", [None, pd.DataFrame()])
def test_empty_vendor_response_retains_entire_cache(cached, incoming):
    old, path = cached
    before = path.read_bytes()
    with pytest.raises(ValueError, match="empty frame"):
        store.upsert("holiday_fixture", "TEST", incoming, overwrite_overlap=True)
    assert_retained(old, path, before)


@pytest.mark.parametrize("reject_all", [False, True])
def test_outlier_filter_cannot_turn_current_response_into_destructive_stale_window(
    cached, monkeypatch, reject_all,
):
    old, path = cached
    before = path.read_bytes()
    incoming = pd.concat([
        old.iloc[-3:],
        pd.DataFrame({"close": [10000.0], "volume": [1000.0]},
                     index=pd.to_datetime(["2026-10-08"])),
    ])
    # A filtering guard may remove the latest returned bar or the whole frame.
    filtered = incoming.iloc[:0] if reject_all else incoming.iloc[:1]
    monkeypatch.setattr(store, "_guard_outliers", lambda *args: filtered)
    with pytest.raises(ValueError, match="overwrite_overlap.*retained"):
        store.upsert("holiday_fixture", "TEST", incoming,
                     outlier_col="close", overwrite_overlap=True)
    assert_retained(old, path, before)


def test_current_incomplete_overlap_owns_span_without_backfilling_old_basis(cached):
    old, path = cached
    start = old.index[2]
    omitted = old.index[4]
    incoming = old.loc[start:].drop(index=omitted).copy()
    incoming["close"] *= 0.5
    result = store.upsert("holiday_fixture", "TEST", incoming, overwrite_overlap=True)
    expected = pd.concat([old.loc[old.index < start], incoming])

    assert omitted not in result.index
    pd.testing.assert_frame_equal(result, expected, check_freq=False)
    pd.testing.assert_frame_equal(pd.read_parquet(path), expected, check_freq=False)
    assert result.index.max() == old.index.max()


def test_newer_adjusted_window_replaces_overlap_and_preserves_deep_history(cached):
    old, path = cached
    incoming = old.iloc[-3:].copy()
    incoming["close"] *= 0.5
    incoming.loc[pd.Timestamp("2026-10-08")] = [56.0, 1100.0]
    result = store.upsert("holiday_fixture", "TEST", incoming, overwrite_overlap=True)
    expected = pd.concat([old.iloc[:-3], incoming])

    pd.testing.assert_frame_equal(result, expected, check_freq=False)
    pd.testing.assert_frame_equal(pd.read_parquet(path), expected, check_freq=False)
    assert result.index.max() == pd.Timestamp("2026-10-08")


def test_full_range_adjustment_rebases_entire_store(cached):
    old, path = cached
    full = old.copy()
    full["close"] *= 0.5
    result = store.upsert("holiday_fixture", "TEST", full, overwrite_overlap=True)
    pd.testing.assert_frame_equal(result, full, check_freq=False)
    pd.testing.assert_frame_equal(pd.read_parquet(path), full, check_freq=False)


def test_nonadjusted_backfill_keeps_ordinary_new_wins_semantics(cached):
    old, _path = cached
    backfill = old.iloc[1:3].copy()
    backfill["close"] += 10
    result = store.upsert("holiday_fixture", "TEST", backfill)
    expected = old.copy()
    expected.loc[backfill.index] = backfill
    pd.testing.assert_frame_equal(result, expected, check_freq=False)


def test_cold_start_adjusted_store_still_accepts_first_frame(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    incoming = pd.DataFrame({"close": [12.0]}, index=pd.to_datetime(["2026-09-30"]))
    result = store.upsert("holiday_fixture", "TEST", incoming, overwrite_overlap=True)
    pd.testing.assert_frame_equal(result, incoming)


def test_intraday_retention_compares_latest_timestamp_not_only_date(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    old = pd.DataFrame({"close": [10.0, 11.0, 12.0]},
                       index=pd.to_datetime(["2026-09-30 09:30", "2026-09-30 10:30", "2026-09-30 11:30"]))
    store.upsert("holiday_fixture", "TEST", old, normalize_index=False)
    path = tmp_path / "holiday_fixture" / "TEST.parquet"
    before = path.read_bytes()
    stale = old.iloc[:2] * 0.5
    with pytest.raises(ValueError, match="stale.*overwrite_overlap.*retained"):
        store.upsert("holiday_fixture", "TEST", stale,
                     normalize_index=False, overwrite_overlap=True)
    assert_retained(old, path, before)
