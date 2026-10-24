"""Tests for collectors.russell_breadth — RussellBreadthAdapter.

Contract:
  - Constituent floor: ≥1,600 rows; stale/absent JSON keeps last committed
    constituents.parquet (never-shrink-the-ledger semantics).
  - Stale-JSON guard: idx_rut.json older than 7 days is rejected.
  - GROUPS in engine.universe_history contains "russell_breadth": "r2000".
  - Adapter registered in scripts.collect.all_adapters().
  - _download_closes chunking override: patches batch_size to 250.
  - compute() drops rows with n_members < 1,200.

No network calls: all I/O is mocked/patched.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import collectors.russell_breadth as rb
from collectors.russell_breadth import RussellBreadthAdapter, _CONSTITUENTS_FLOOR, _JSON_MAX_AGE_DAYS, _N_REPORTING_FLOOR


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_payload(n: int, age_days: float = 0.0) -> dict:
    """Build a minimal idx_rut.json payload with n rows."""
    from datetime import timedelta
    as_of_dt = datetime.now(timezone.utc) - timedelta(days=age_days)
    rows = [
        {"ticker": f"T{i:04d}", "company": f"Company {i}", "sector": "Technology"}
        for i in range(n)
    ]
    return {
        "filter": "idx_rut",
        "as_of": as_of_dt.strftime("%Y-%m-%d %H:%M UTC"),
        "n": n,
        "rows": rows,
    }


def _make_constituents_parquet(tmp_path, n: int = 1800) -> None:
    """Write a committed constituents.parquet with n rows."""
    cpath = tmp_path / "russell_breadth" / "constituents.parquet"
    cpath.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        {"name": [f"Company {i}" for i in range(n)],
         "sector": ["Technology"] * n},
        index=pd.Index([f"T{i:04d}" for i in range(n)], name="symbol"),
    )
    df.to_parquet(cpath)


# ---------------------------------------------------------------------------
# constituents() — happy path: valid JSON with enough rows
# ---------------------------------------------------------------------------

def test_constituents_from_valid_json(tmp_path, monkeypatch):
    payload = _make_payload(1900, age_days=0.5)
    monkeypatch.setattr(rb, "_load_finviz_json", lambda: payload)
    monkeypatch.setattr("lib.config.data_dir", lambda: tmp_path)
    adapter = RussellBreadthAdapter.__new__(RussellBreadthAdapter)
    adapter.cache_path = tmp_path / "russell_breadth" / "_closes_cache.parquet"
    adapter.cfg = {}  # _repair() reads cfg.ticker_fixups; runtime __init__ always sets it

    members = adapter.constituents()
    assert len(members) == 1900
    assert set(members.columns) >= {"symbol", "name", "sector"}
    assert members["symbol"].iloc[0] == "T0000"


# ---------------------------------------------------------------------------
# Stale-JSON guard: JSON older than _JSON_MAX_AGE_DAYS → use parquet fallback
# ---------------------------------------------------------------------------

def test_stale_json_falls_back_to_parquet(tmp_path, monkeypatch, caplog):
    _make_constituents_parquet(tmp_path, n=1850)
    payload = _make_payload(1900, age_days=_JSON_MAX_AGE_DAYS + 1)
    monkeypatch.setattr(rb, "_load_finviz_json", lambda: payload)
    monkeypatch.setattr("lib.config.data_dir", lambda: tmp_path)
    adapter = RussellBreadthAdapter.__new__(RussellBreadthAdapter)
    adapter.cache_path = tmp_path / "russell_breadth" / "_closes_cache.parquet"
    adapter.cfg = {}  # _repair() reads cfg.ticker_fixups; runtime __init__ always sets it

    import logging
    with caplog.at_level(logging.WARNING, logger="collectors.russell_breadth"):
        members = adapter.constituents()

    assert len(members) == 1850
    assert "stale" in caplog.text.lower() or "idx_rut.json" in caplog.text


# ---------------------------------------------------------------------------
# Floor guard: JSON with too few rows → use parquet fallback (never-shrink)
# ---------------------------------------------------------------------------

def test_small_json_falls_back_to_parquet(tmp_path, monkeypatch, caplog):
    _make_constituents_parquet(tmp_path, n=1800)
    payload = _make_payload(_CONSTITUENTS_FLOOR - 1, age_days=0.5)
    monkeypatch.setattr(rb, "_load_finviz_json", lambda: payload)
    monkeypatch.setattr("lib.config.data_dir", lambda: tmp_path)
    adapter = RussellBreadthAdapter.__new__(RussellBreadthAdapter)
    adapter.cache_path = tmp_path / "russell_breadth" / "_closes_cache.parquet"
    adapter.cfg = {}  # _repair() reads cfg.ticker_fixups; runtime __init__ always sets it

    import logging
    with caplog.at_level(logging.WARNING, logger="collectors.russell_breadth"):
        members = adapter.constituents()

    assert len(members) == 1800
    assert "floor" in caplog.text.lower() or "idx_rut.json" in caplog.text


# ---------------------------------------------------------------------------
# Absent JSON + present parquet → use parquet (never-shrink, no error)
# ---------------------------------------------------------------------------

def test_absent_json_uses_parquet(tmp_path, monkeypatch):
    _make_constituents_parquet(tmp_path, n=1750)
    monkeypatch.setattr(rb, "_load_finviz_json", lambda: None)
    monkeypatch.setattr("lib.config.data_dir", lambda: tmp_path)
    adapter = RussellBreadthAdapter.__new__(RussellBreadthAdapter)
    adapter.cache_path = tmp_path / "russell_breadth" / "_closes_cache.parquet"
    adapter.cfg = {}  # _repair() reads cfg.ticker_fixups; runtime __init__ always sets it

    members = adapter.constituents()
    assert len(members) == 1750


# ---------------------------------------------------------------------------
# Absent JSON + absent parquet → RuntimeError (nothing to fall back to)
# ---------------------------------------------------------------------------

def test_absent_json_and_absent_parquet_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(rb, "_load_finviz_json", lambda: None)
    monkeypatch.setattr("lib.config.data_dir", lambda: tmp_path)
    adapter = RussellBreadthAdapter.__new__(RussellBreadthAdapter)
    adapter.cache_path = tmp_path / "russell_breadth" / "_closes_cache.parquet"
    adapter.cfg = {}  # _repair() reads cfg.ticker_fixups; runtime __init__ always sets it

    with pytest.raises(RuntimeError, match="absent/unusable"):
        adapter.constituents()


# ---------------------------------------------------------------------------
# constituents_checked: raises when below floor
# ---------------------------------------------------------------------------

def test_constituents_checked_raises_below_floor():
    adapter = RussellBreadthAdapter.__new__(RussellBreadthAdapter)
    small = pd.DataFrame({"symbol": [f"T{i}" for i in range(_CONSTITUENTS_FLOOR - 1)],
                          "name": ["X"] * (_CONSTITUENTS_FLOOR - 1),
                          "sector": ["Tech"] * (_CONSTITUENTS_FLOOR - 1)})
    with pytest.raises(ValueError, match="suspicious"):
        adapter.constituents_checked(small)


def test_constituents_checked_passes_above_floor():
    adapter = RussellBreadthAdapter.__new__(RussellBreadthAdapter)
    ok = pd.DataFrame({"symbol": [f"T{i}" for i in range(_CONSTITUENTS_FLOOR)],
                       "name": ["X"] * _CONSTITUENTS_FLOOR,
                       "sector": ["Tech"] * _CONSTITUENTS_FLOOR})
    assert len(adapter.constituents_checked(ok)) == _CONSTITUENTS_FLOOR


# ---------------------------------------------------------------------------
# compute(): rows with n_members < _N_REPORTING_FLOOR are dropped
# ---------------------------------------------------------------------------

def test_compute_drops_rows_below_n_reporting_floor():
    """compute() must drop days with n_members < 1200 (data-gap filter)."""
    from collectors.breadth import BreadthAdapter

    # Build a minimal closes DataFrame with enough rows for the rolling MA
    # window (need ≥200 rows for min_periods=200) plus a few "thin" rows
    n_tickers = _N_REPORTING_FLOOR + 100   # 1300 tickers total
    dates = pd.date_range("2025-01-01", periods=220, freq="B")
    rng = pd.RangeIndex(n_tickers)
    closes = pd.DataFrame(
        {f"T{i}": [10.0 + i * 0.01 + d * 0.001 for d in range(len(dates))]
         for i in range(n_tickers)},
        index=dates,
    )
    # Force the FINAL 5 days below the floor: only 900 tickers report (< 1200).
    # These rows MUST be dropped by the n_members filter — the load-bearing case.
    import numpy as np
    closes.iloc[-5:, 900:] = np.nan

    # Patch in a minimal cfg so the base class compute() can read ma_windows etc.
    adapter = RussellBreadthAdapter.__new__(RussellBreadthAdapter)
    adapter.cfg = {"ma_windows": [50, 200], "nhnl_window": 252}

    # Run compute (no network, pure math)
    out = adapter.compute(closes)

    # The thin final rows (n_members=900) must be gone; earlier full rows survive.
    assert not out.empty, "full-coverage rows must survive the floor"
    assert (out["n_members"] >= _N_REPORTING_FLOOR).all(), (
        f"compute() left rows below n_members floor {_N_REPORTING_FLOOR}: "
        f"min={out['n_members'].min()}"
    )
    assert out.index.max() < dates[-5], "thin trailing rows were not dropped"


# ---------------------------------------------------------------------------
# _download_closes chunking: batch_size is overridden to 250
# ---------------------------------------------------------------------------

def test_download_closes_uses_chunk_size_250(monkeypatch):
    """_download_closes must pass batch_size=250 to the super() call."""
    from collectors.russell_breadth import _CHUNK_SIZE

    captured_batch_sizes = []

    def fake_download_closes(self_inner, tickers, period):
        captured_batch_sizes.append(self_inner.ycfg.get("batch_size"))
        # Return a minimal DataFrame so the caller doesn't fail
        return pd.DataFrame(
            {"T0000": [10.0, 11.0, 12.0]},
            index=pd.date_range("2025-01-02", periods=3, freq="B"),
        )

    from collectors import breadth as breadth_mod
    monkeypatch.setattr(breadth_mod.BreadthAdapter, "_download_closes", fake_download_closes)

    adapter = RussellBreadthAdapter.__new__(RussellBreadthAdapter)
    adapter.cfg = {"ma_windows": [50, 200], "nhnl_window": 252, "lookback_days_live": 730}
    adapter.ycfg = {"batch_size": 80, "retries": 3, "backoff_base_s": 5}

    _ = adapter._download_closes(["T0000"], "2y")

    assert len(captured_batch_sizes) == 1
    assert captured_batch_sizes[0] == _CHUNK_SIZE, (
        f"Expected batch_size={_CHUNK_SIZE}, got {captured_batch_sizes[0]}"
    )


# ---------------------------------------------------------------------------
# engine.universe_history.GROUPS includes "russell_breadth": "r2000"
# ---------------------------------------------------------------------------

def test_groups_contains_r2000():
    from engine.universe_history import GROUPS
    assert "russell_breadth" in GROUPS, (
        "GROUPS dict must contain 'russell_breadth' key"
    )
    assert GROUPS["russell_breadth"] == "r2000", (
        f"Expected GROUPS['russell_breadth']='r2000', got {GROUPS['russell_breadth']!r}"
    )


# ---------------------------------------------------------------------------
# scripts.collect.all_adapters() registers RussellBreadthAdapter
# ---------------------------------------------------------------------------

def test_collect_registers_russell_breadth():
    from scripts.collect import all_adapters
    registry = all_adapters()
    assert "russell_breadth" in registry, (
        "all_adapters() must register 'russell_breadth'"
    )
    from collectors.russell_breadth import RussellBreadthAdapter
    assert registry["russell_breadth"] is RussellBreadthAdapter


# Normal Russell updates must not turn partial Yahoo closes into an apparently
# successful current-session panel or overwrite a recoverable canonical cache.
def _russell_completed_adapter(tmp_path):
    adapter = RussellBreadthAdapter.__new__(RussellBreadthAdapter)
    adapter.cache_path = tmp_path / "russell_breadth" / "_closes_cache.parquet"
    adapter.cache_path.parent.mkdir(parents=True, exist_ok=True)
    adapter.cfg = {"lookback_days_live": 730}
    adapter.ycfg = {"batch_size": 80, "retries": 2, "backoff_base_s": 1}
    return adapter


def _russell_partial_frame(n=1700, valid=400, *, include_completed=True):
    import numpy as np

    names = [f"R{i:04d}" for i in range(n)]
    dates = pd.to_datetime(["2026-10-07", "2026-10-14"]) if include_completed else pd.to_datetime(
        ["2026-10-07", "2026-10-15"]
    )
    frame = pd.DataFrame(np.full((2, n), 10.0), index=dates, columns=names)
    frame.iloc[-1, valid:] = np.nan
    return names, frame


def test_russell_normal_partial_download_fails_before_replacing_last_good_cache(tmp_path, monkeypatch):
    from collectors import breadth as b
    from datetime import date

    adapter = _russell_completed_adapter(tmp_path)
    original = pd.DataFrame({"KEEP": [4.5]}, index=pd.to_datetime(["2026-10-07"]))
    original.to_parquet(adapter.cache_path)
    before = adapter.cache_path.read_bytes()
    tickers, incomplete = _russell_partial_frame()
    monkeypatch.setattr(b.BreadthAdapter, "_download_closes", lambda self, names, period: incomplete)
    monkeypatch.setattr("lib.nyse_calendar.expected_last_session", lambda now=None: date(2026, 10, 14))

    with pytest.raises(RuntimeError, match="completed-session"):
        adapter._download_closes(tickers, "1mo")
    assert adapter.cache_path.read_bytes() == before


def test_russell_future_only_and_nonfinite_completed_closes_do_not_pass(tmp_path, monkeypatch):
    from collectors import breadth as b
    from datetime import date
    import numpy as np

    adapter = _russell_completed_adapter(tmp_path)
    original = pd.DataFrame({"KEEP": [4.5]}, index=pd.to_datetime(["2026-10-07"]))
    original.to_parquet(adapter.cache_path)
    tickers, future = _russell_partial_frame(include_completed=False, valid=1700)
    monkeypatch.setattr(b.BreadthAdapter, "_download_closes", lambda self, names, period: future)
    monkeypatch.setattr("lib.nyse_calendar.expected_last_session", lambda now=None: date(2026, 10, 14))
    with pytest.raises(RuntimeError, match="completed-session"):
        adapter._download_closes(tickers, "1mo")

    _, corrupt = _russell_partial_frame(valid=1700)
    corrupt.iloc[-1, :600] = np.inf
    corrupt.iloc[-1, 600:1200] = 0.0
    monkeypatch.setattr(b.BreadthAdapter, "_download_closes", lambda self, names, period: corrupt)
    with pytest.raises(RuntimeError, match="completed-session"):
        adapter._download_closes(tickers, "1mo")


def test_russell_completed_coverage_permits_qualified_close_but_keeps_cache_for_owner(tmp_path, monkeypatch):
    from collectors import breadth as b
    from datetime import date

    adapter = _russell_completed_adapter(tmp_path)
    original = pd.DataFrame({"KEEP": [4.5]}, index=pd.to_datetime(["2026-10-07"]))
    original.to_parquet(adapter.cache_path)
    before = adapter.cache_path.read_bytes()
    tickers, healthy = _russell_partial_frame(valid=1500)
    monkeypatch.setattr(b.BreadthAdapter, "_download_closes", lambda self, names, period: healthy)
    monkeypatch.setattr("lib.nyse_calendar.expected_last_session", lambda now=None: date(2026, 10, 14))
    result = adapter._download_closes(tickers, "1mo")
    assert result.equals(healthy)
    assert adapter.cache_path.read_bytes() == before
    assert adapter.ycfg["batch_size"] == 80


def test_russell_seam_repull_must_not_overwrite_preexisting_cache(tmp_path, monkeypatch):
    from collectors import breadth as b

    adapter = _russell_completed_adapter(tmp_path)
    original = pd.DataFrame({"KEEP": [4.5]}, index=pd.to_datetime(["2026-10-07"]))
    original.to_parquet(adapter.cache_path)
    before = adapter.cache_path.read_bytes()
    repair = pd.DataFrame({"R1": [11.0]}, index=pd.to_datetime(["2026-10-14"]))
    monkeypatch.setattr(b.BreadthAdapter, "_download_closes", lambda self, names, period: repair)
    assert adapter._download_closes(["R1"], "2y").equals(repair)
    assert adapter.cache_path.read_bytes() == before


def test_russell_first_backfill_still_preserves_partial_seed(tmp_path, monkeypatch):
    from collectors import breadth as b

    adapter = _russell_completed_adapter(tmp_path)
    assert not adapter.cache_path.exists()
    tickers, partial = _russell_partial_frame(n=10, valid=4)
    monkeypatch.setattr(b.BreadthAdapter, "_download_closes", lambda self, names, period: partial)
    result = adapter._download_closes(tickers, "2y")
    assert result.equals(partial)
    assert pd.read_parquet(adapter.cache_path).equals(partial)


@pytest.mark.parametrize("fresh_count,expect_ok", [(400, False), (1500, True)])
def test_russell_native_fetch_owns_post_validation_cache_commit(
    tmp_path, monkeypatch, fresh_count, expect_ok
):
    """Actual inherited fetch, not a hand-called validator: last-good survives refusal."""
    from collectors import breadth as b
    from datetime import date

    adapter = _russell_completed_adapter(tmp_path)
    tickers, fresh = _russell_partial_frame(valid=fresh_count)
    original = pd.DataFrame(
        [10.0] * len(tickers), index=tickers
    ).T.set_axis(pd.to_datetime(["2026-10-07"]), axis="index")
    original.to_parquet(adapter.cache_path)
    before = adapter.cache_path.read_bytes()
    members = pd.DataFrame({
        "symbol": tickers, "name": tickers, "sector": ["Industrials"] * len(tickers)
    })
    monkeypatch.setattr(adapter, "constituents", lambda: members)
    monkeypatch.setattr(adapter, "constituents_checked", lambda m: m)
    monkeypatch.setattr(adapter, "compute", lambda c: pd.DataFrame({"n_members": [len(c.columns)]}))
    monkeypatch.setattr(adapter, "compute_sectors", lambda c, m: pd.DataFrame())
    monkeypatch.setattr(b.BreadthAdapter, "_download_closes", lambda self, names, period: fresh)
    monkeypatch.setattr("lib.nyse_calendar.expected_last_session", lambda now=None: date(2026, 10, 14))

    if not expect_ok:
        with pytest.raises(RuntimeError, match="completed-session"):
            adapter.fetch()
        assert adapter.cache_path.read_bytes() == before
        assert not (adapter.cache_path.parent / "constituents.parquet").exists()
    else:
        result = adapter.fetch()
        assert "breadth" in result
        disk = pd.read_parquet(adapter.cache_path)
        assert disk.index.max() == pd.Timestamp("2026-10-14")
        assert disk.loc[pd.Timestamp("2026-10-07"), tickers[0]] == 10.0
        assert disk.loc[pd.Timestamp("2026-10-14"), tickers[0]] == 10.0
        assert (adapter.cache_path.parent / "constituents.parquet").exists()


@pytest.mark.parametrize("present,qualifies", [(1359, False), (1360, True)])
def test_russell_completed_session_exact_80pct_boundary(tmp_path, monkeypatch, present, qualifies):
    """The full-cohort freshness bar is ceil(0.8 * 1,700), not a rounded shortcut."""
    from collectors import breadth as b
    from datetime import date

    adapter = _russell_completed_adapter(tmp_path)
    pd.DataFrame({"KEEP": [4.5]}, index=pd.to_datetime(["2026-10-07"])).to_parquet(adapter.cache_path)
    saved = adapter.cache_path.read_bytes()
    tickers, frame = _russell_partial_frame(n=1700, valid=present)
    monkeypatch.setattr(b.BreadthAdapter, "_download_closes", lambda self, names, period: frame)
    monkeypatch.setattr("lib.nyse_calendar.expected_last_session", lambda now=None: date(2026, 10, 14))

    if qualifies:
        assert adapter._download_closes(tickers, "1mo").equals(frame)
    else:
        with pytest.raises(RuntimeError, match="completed-session"):
            adapter._download_closes(tickers, "1mo")
    assert adapter.cache_path.read_bytes() == saved


def test_russell_cold_full_universe_keeps_partial_seed_but_reports_failure(tmp_path, monkeypatch):
    """A first-night recovery cache is not evidence of a healthy completed close."""
    from collectors import breadth as b
    from datetime import date

    adapter = _russell_completed_adapter(tmp_path)
    tickers, incomplete = _russell_partial_frame(n=1700, valid=400)
    assert not adapter.cache_path.exists()
    monkeypatch.setattr(b.BreadthAdapter, "_download_closes",
                        lambda self, names, period: incomplete)
    monkeypatch.setattr("lib.nyse_calendar.expected_last_session",
                        lambda now=None: date(2026, 10, 14))

    with pytest.raises(RuntimeError, match="completed-session"):
        adapter._download_closes(tickers, "2y")
    # Retain the original cold-start partial history for the NEXT eligible run,
    # but prevent a false 'source healthy' receipt on this run.
    assert adapter.cache_path.exists()
    assert pd.read_parquet(adapter.cache_path).equals(incomplete)


def test_russell_cold_full_universe_healthy_completed_close_is_eligible(tmp_path, monkeypatch):
    from collectors import breadth as b
    from datetime import date

    adapter = _russell_completed_adapter(tmp_path)
    tickers, healthy = _russell_partial_frame(n=1700, valid=1500)
    monkeypatch.setattr(b.BreadthAdapter, "_download_closes",
                        lambda self, names, period: healthy)
    monkeypatch.setattr("lib.nyse_calendar.expected_last_session",
                        lambda now=None: date(2026, 10, 14))
    result = adapter._download_closes(tickers, "2y")
    assert result.equals(healthy)
    assert adapter.cache_path.exists()


def test_russell_session_reference_is_frozen_before_yahoo_request(tmp_path, monkeypatch):
    """A four-hour provider call must not quietly switch sessions mid-request."""
    from collectors import breadth as b
    from datetime import date

    adapter = _russell_completed_adapter(tmp_path)
    pd.DataFrame({"KEEP": [4.5]}, index=pd.to_datetime(["2026-10-07"])).to_parquet(
        adapter.cache_path
    )
    tickers, completed_data = _russell_partial_frame(n=1700, valid=1500)
    state = {"session": date(2026, 10, 14), "calendar_reads": []}

    def expected(now=None):
        state["calendar_reads"].append(state["session"])
        return state["session"]

    def downloaded(self, names, period):
        assert state["calendar_reads"] == [date(2026, 10, 14)], (
            "the completed-session reference must precede source availability"
        )
        state["session"] = date(2026, 10, 15)
        return completed_data

    monkeypatch.setattr("lib.nyse_calendar.expected_last_session", expected)
    monkeypatch.setattr(b.BreadthAdapter, "_download_closes", downloaded)
    assert adapter._download_closes(tickers, "1mo").equals(completed_data)
    assert state["calendar_reads"] == [date(2026, 10, 14)]
