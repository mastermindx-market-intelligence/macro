"""Tests for scripts/skew_accrual_gate.py — the ThetaData EOD freshness gate.

All tests use tmp_path fixtures (no real store / network). The gate is the
load-bearing safety property the skew-accrual runner depends on: a stale
accretion would corrupt the validation panel the lane is accruing toward.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "skew_accrual_gate.py"


def _import_gate():
    """Import scripts/skew_accrual_gate as a module."""
    spec = importlib.util.spec_from_file_location("skew_accrual_gate", GATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_eod_shard(store: Path, root: str, year: int, latest_date_iso: str):
    """Write one synthetic EOD shard with a single 'date' column."""
    base = store / "eod" / root
    base.mkdir(parents=True, exist_ok=True)
    shard = base / f"{year}.parquet"
    table = pa.table({"date": pa.array([latest_date_iso], type=pa.string())})
    pq.write_table(table, shard)
    return shard


def test_check_fresh_returns_ok_when_shard_meets_required(tmp_path):
    """latest >= required → FRESH (gate exit 0)."""
    mod = _import_gate()
    store = tmp_path / "store"
    today = date(2026, 9, 22)
    required = today - timedelta(days=1)  # T-1 floor
    _write_eod_shard(store, "SPY", required.year, required.isoformat())
    code, status, info = mod.check(store, repo=None, root="SPY",
                                    required_iso=required.isoformat())
    assert code == mod.EXIT_OK
    assert status == "FRESH"
    assert info["latest"] == required.isoformat()


def test_check_stale_when_shard_is_before_required(tmp_path):
    """latest < required → STALE (gate exit 1)."""
    mod = _import_gate()
    store = tmp_path / "store"
    today = date(2026, 9, 22)
    required = today - timedelta(days=1)
    stale_date = required - timedelta(days=3)
    _write_eod_shard(store, "SPY", stale_date.year, stale_date.isoformat())
    code, status, info = mod.check(store, repo=None, root="SPY",
                                    required_iso=required.isoformat())
    assert code == mod.EXIT_STALE
    assert status == "STALE"
    assert info["latest_reason"] == "ok"


def test_check_resolve_error_when_tier_missing(tmp_path):
    """Store path exists but no eod/ tier → RESOLVE_ERROR (exit 2)."""
    mod = _import_gate()
    store = tmp_path / "store"
    store.mkdir()  # no tier subdirs
    code, status, info = mod.check(store, repo=None, root="SPY",
                                    required_iso=date(2026, 9, 22).isoformat())
    assert code == mod.EXIT_RESOLVE_ERROR
    assert status == "RESOLVE_ERROR"


def test_check_resolve_error_when_store_path_absent(tmp_path):
    mod = _import_gate()
    store = tmp_path / "missing"
    code, status, _ = mod.check(store, repo=None, root="SPY",
                                 required_iso=date(2026, 9, 22).isoformat())
    assert code == mod.EXIT_RESOLVE_ERROR


def test_check_usage_error_when_neither_repo_nor_required_given(tmp_path):
    """Without --required-date and without --repo, the floor cannot resolve."""
    mod = _import_gate()
    store = tmp_path / "store"
    _write_eod_shard(store, "SPY", 2026, "2026-09-21")
    code, status, info = mod.check(store, repo=None, root="SPY",
                                    required_iso=None)
    assert code == mod.EXIT_USAGE_ERROR
    assert status == "USAGE_ERROR"
    assert "could not resolve required floor" in info["reason"]


def test_check_required_date_overrides_calendar(tmp_path):
    """--required-date wins over the lib.nyse_calendar resolution."""
    mod = _import_gate()
    store = tmp_path / "store"
    _write_eod_shard(store, "SPY", 2026, "2026-09-15")
    # Required is 2026-09-15 (explicit); shard latest == 2026-09-15 → FRESH
    code, status, _ = mod.check(store, repo=None, root="SPY",
                                 required_iso="2026-09-15")
    assert code == mod.EXIT_OK
    assert status == "FRESH"


def test_check_at_least_floor_passes_when_shard_ahead_of_calendar(tmp_path):
    """A store ahead of the calendar (e.g., post-holiday correction) passes."""
    mod = _import_gate()
    store = tmp_path / "store"
    today = date(2026, 9, 22)
    required = today - timedelta(days=1)
    ahead_date = required + timedelta(days=2)
    _write_eod_shard(store, "SPY", ahead_date.year, ahead_date.isoformat())
    code, status, _ = mod.check(store, repo=None, root="SPY",
                                 required_iso=required.isoformat())
    assert code == mod.EXIT_OK
    assert status == "FRESH"


def test_check_handles_date_as_datetime_or_string(tmp_path):
    """date column may be datetime.date or ISO string — both must parse."""
    mod = _import_gate()
    store = tmp_path / "store"
    base = store / "eod" / "SPY"
    base.mkdir(parents=True, exist_ok=True)
    # Use timestamp type
    table = pa.table({"date": pa.array([pa.scalar("2026-09-21").cast(pa.string())],
                                        type=pa.string())})
    pq.write_table(table, base / "2026.parquet")
    code, status, info = mod.check(store, repo=None, root="SPY",
                                    required_iso="2026-09-21")
    assert code == mod.EXIT_OK
    assert info["latest"] == "2026-09-21"


def test_check_uses_newest_shard_not_first(tmp_path):
    """Latest shard wins; a partial-year store still satisfies the gate."""
    mod = _import_gate()
    store = tmp_path / "store"
    base = store / "eod" / "SPY"
    base.mkdir(parents=True, exist_ok=True)
    # 2024: old
    pq.write_table(pa.table({"date": ["2024-12-31"]}), base / "2024.parquet")
    # 2026: fresh
    pq.write_table(pa.table({"date": ["2026-09-21"]}), base / "2026.parquet")
    # 2025: middle (older than 2026, but newer than 2024)
    pq.write_table(pa.table({"date": ["2025-06-15"]}), base / "2025.parquet")
    code, status, info = mod.check(store, repo=None, root="SPY",
                                    required_iso="2026-09-21")
    assert code == mod.EXIT_OK
    assert info["latest"] == "2026-09-21"


def test_check_no_shard_under_root_is_resolve_error(tmp_path):
    """Tier dir exists but no SPY shard → RESOLVE_ERROR (no quiet stale)."""
    mod = _import_gate()
    store = tmp_path / "store"
    (store / "eod").mkdir(parents=True)
    # no SPY dir under eod/
    code, status, info = mod.check(store, repo=None, root="SPY",
                                    required_iso="2026-09-21")
    assert code == mod.EXIT_RESOLVE_ERROR
    # The gate's check() walks (store / tier / root) and reports `no_tier`
    # when the tier directory itself is missing; the per-root `no_shard`
    # reason only fires when the tier exists but lacks a SPY subdir. Either
    # way the gate MUST exit RESOLVE_ERROR — never a quiet STALE on missing
    # data. The runner distinguishes USAGE_ERROR from RESOLVE_ERROR so the
    # reason string itself is informational, not load-bearing for the lane.
    assert info["latest_reason"] in ("no_shard", "no_tier")


def test_main_prints_status_word_on_stdout(tmp_path):
    """The runner reads stdout for the status word; confirm exactly that shape."""
    mod = _import_gate()
    store = tmp_path / "store"
    _write_eod_shard(store, "SPY", 2026, "2026-09-21")
    rc = subprocess.run(
        [sys.executable, str(GATE), "--store", str(store),
         "--required-date", "2026-09-21"],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == 0
    # The status word is the FIRST non-empty stdout line.
    first = next((l for l in rc.stdout.splitlines() if l.strip()), "")
    assert first == "FRESH"


def test_main_exit_code_is_part_of_contract(tmp_path):
    """Exit codes are load-bearing — the runner's retry loop reads them."""
    mod = _import_gate()
    store = tmp_path / "store"
    _write_eod_shard(store, "SPY", 2026, "2026-09-15")
    rc = subprocess.run(
        [sys.executable, str(GATE), "--store", str(store),
         "--required-date", "2026-09-21"],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == mod.EXIT_STALE
    first = next((l for l in rc.stdout.splitlines() if l.strip()), "")
    assert first == "STALE"


def test_check_no_rows_in_shard_is_resolve_error(tmp_path):
    """Empty shard → RESOLVE_ERROR (cannot return a verdict on zero rows)."""
    mod = _import_gate()
    store = tmp_path / "store"
    base = store / "eod" / "SPY"
    base.mkdir(parents=True)
    pq.write_table(pa.table({"date": pa.array([], type=pa.string())}),
                   base / "2026.parquet")
    code, status, info = mod.check(store, repo=None, root="SPY",
                                    required_iso="2026-09-21")
    assert code == mod.EXIT_RESOLVE_ERROR
    assert info["latest_reason"] == "no_rows"

def test_main_receipt_writer_emits_exactly_one_physical_line(tmp_path):
    """MINOR-2 fix (2026-09-22): the gate's stderr `::gate-info::` receipt
    must be EXACTLY one physical line per call. The dict's str() can span
    multiple lines on its own, and embedded newlines in a `reason` value
    can spill them too — that would anchor two log rows to one receipt
    call (silent green / doubled entries in the launchd log). Pin the
    contract: either stderr is empty OR stderr has exactly one non-empty
    line starting with `::gate-info::`. The runner reads stdout's status
    word (always one line) and stderr's `::gate-info::` body."""
    mod = _import_gate()
    store = tmp_path / "store"
    _write_eod_shard(store, "SPY", 2026, "2026-09-21")
    rc = subprocess.run(
        [sys.executable, "-m", "scripts.skew_accrual_gate",
         "--store", str(store),
         "--required-date", "2026-09-21"],
        capture_output=True, text=True, cwd=str(ROOT), check=False,
    )
    assert rc.returncode == mod.EXIT_OK
    # stdout: one line on receipt (status word)
    stdout_lines = [l for l in rc.stdout.splitlines() if l.strip()]
    assert stdout_lines == ["FRESH"], stdout_lines
    # stderr: zero OR one line starting with `::gate-info::`.
    receipt_lines = [
        l for l in rc.stderr.splitlines()
        if l.startswith("::gate-info::")
    ]
    assert len(receipt_lines) <= 1, (
        f"gate emitted {len(receipt_lines)} ::gate-info:: lines, "
        f"expected at most 1:\n" + "\n".join(receipt_lines)
    )
    if receipt_lines:
        # Verify the receipt line itself contains no embedded newlines
        # by checking the byte count of the recorded line equals the
        # number of `\n` characters we'd see if it had been split.
        body = receipt_lines[0]
        assert "\n" not in body, body
