"""Tests for scripts/skew_accrual_verify_ledger.py — the post-accrue gate.

This helper is the BLOCKER-3 fix: the W2-1b snapshot() can return 0
without writing rows (chain=None, no rows, or dedup-only). The runner
MUST verify the ledger has content BEFORE publishing — otherwise the
R2 leg would advertise a no-op put as a successful publish. All tests
use tmp_path fixtures (synthetic parquet, no real store).
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "scripts" / "skew_accrual_verify_ledger.py"


def _import_verify():
    """Import scripts/skew_accrual_verify_ledger as a module under a unique name."""
    spec = importlib.util.spec_from_file_location(
        "skew_accrual_verify_ledger_under_test", VERIFY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_ledger(path: Path, rows: list[dict] | None) -> Path:
    """Write a synthetic ledger parquet. None → 0-row file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows is None:
        # Write a 0-row parquet so the file exists but carries no data.
        pd.DataFrame(columns=["date", "underlying", "skew"]).to_parquet(path)
    else:
        pd.DataFrame(rows).to_parquet(path)
    return path


# ── behavioural unit tests ───────────────────────────────────────────────── #


def test_check_returns_ok_when_ledger_has_rows(tmp_path):
    """A ledger with at least one row (no pre_rows recorded) → exit 0."""
    mod = _import_verify()
    ledger = _write_ledger(tmp_path / "snapshots.parquet", [
        {"date": "2026-09-22", "underlying": "SPY", "skew": 0.05},
    ])
    code, info = mod.check(ledger)
    assert code == mod.EXIT_OK
    assert info["rows"] == 1
    assert info["bytes"] > 0
    assert "content" in info["reason"]


def test_check_returns_ok_when_ledger_grew_under_accrue(tmp_path):
    """BLOCKER-2 RED-first: post-accrue rows > pre_rows → exit 0.
    This is the load-bearing case for a successful run."""
    mod = _import_verify()
    ledger = _write_ledger(tmp_path / "snapshots.parquet", [
        {"date": "2026-09-22", "underlying": "SPY", "skew": 0.05},
        {"date": "2026-09-22", "underlying": "AAPL", "skew": 0.06},
        {"date": "2026-09-22", "underlying": "MSFT", "skew": 0.07},
    ])
    code, info = mod.check(ledger, pre_rows=2)
    assert code == mod.EXIT_OK
    assert info["rows"] == 3
    assert info["pre_rows"] == 2
    assert "content" in info["reason"]


def test_check_returns_no_ledger_when_no_growth(tmp_path):
    """BLOCKER-2 RED-first regression: the W2-1b no-op accrue case.
    Pre-accrue row count equals post-accrue row count — the accrue
    contributed nothing new (chain=None, no rows, or dedup-only). The
    OLD "ledger has >= 1 row" check passed this through to publish; the
    NEW check refuses on no growth, so the launchd log cannot report a
    successful publish for a byte-equal ledger."""
    mod = _import_verify()
    # 12,375 rows in the bootstrap ledger → accrue is supposed to add
    # today's session. If snapshot() returns 0 (no-op), the row count
    # is unchanged and verify refuses.
    rows = [{"date": "2026-09-15", "underlying": f"SYM{i}",
             "skew": 0.01 * i} for i in range(12375)]
    ledger = _write_ledger(tmp_path / "snapshots.parquet", rows)
    code, info = mod.check(ledger, pre_rows=12375)
    assert code == mod.EXIT_NO_LEDGER
    assert info["rows"] == 12375
    assert info["pre_rows"] == 12375
    assert "did not grow" in info["reason"]
    assert "no-op snapshot" in info["reason"]


def test_check_returns_no_ledger_when_file_missing(tmp_path):
    """Accrue wrote nothing → no ledger file → exit 5."""
    mod = _import_verify()
    code, info = mod.check(tmp_path / "nope.parquet")
    assert code == mod.EXIT_NO_LEDGER
    assert "does not exist" in info["reason"]
    assert "accrue never wrote one" in info["reason"]


def test_check_returns_no_ledger_when_zero_rows(tmp_path):
    """The W2-1b zero-row case: ledger exists, is non-empty parquet, but
    has 0 rows (chain=None / no rows / dedup-only). Refuse to publish."""
    mod = _import_verify()
    ledger = _write_ledger(tmp_path / "snapshots.parquet", None)
    assert ledger.stat().st_size > 0  # parquet header bytes, not 0
    code, info = mod.check(ledger)
    assert code == mod.EXIT_NO_LEDGER
    assert info["rows"] == 0
    assert "0 rows" in info["reason"]


def test_check_returns_no_ledger_when_zero_bytes(tmp_path):
    """Empty file (0 bytes) → exit 5. The runner's zero-byte file would
    trigger the publish_r2 bytes floor anyway, but the verify gates the
    publish BEFORE that floor trips, so the operator sees a named reason."""
    mod = _import_verify()
    ledger = tmp_path / "snapshots.parquet"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_bytes(b"")
    code, info = mod.check(ledger)
    assert code == mod.EXIT_NO_LEDGER
    assert info["bytes"] == 0


# ── CLI subprocess surface ────────────────────────────────────────────────── #


def test_main_prints_status_word_on_stdout(tmp_path):
    """The runner reads stdout for the status word; verify the shape."""
    ledger = _write_ledger(tmp_path / "snapshots.parquet", [
        {"date": "2026-09-22", "underlying": "SPY", "skew": 0.05},
    ])
    rc = subprocess.run(
        [sys.executable, str(VERIFY), "--ledger", str(ledger)],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == 0
    first = next((l for l in rc.stdout.splitlines() if l.strip()), "")
    assert first == "OK"


def test_main_exit_code_when_ledger_missing(tmp_path):
    """The runner's verify step reads the exit code; pin it."""
    mod = _import_verify()
    rc = subprocess.run(
        [sys.executable, str(VERIFY),
         "--ledger", str(tmp_path / "nope.parquet")],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == mod.EXIT_NO_LEDGER
    first = next((l for l in rc.stdout.splitlines() if l.strip()), "")
    assert first == "NO_LEDGER"


def test_main_cli_pre_rows_blocks_no_op_accrue(tmp_path):
    """BLOCKER-2 RED-first end-to-end: --pre-rows blocks a no-op accrue
    via the subprocess CLI (the runner's actual call shape)."""
    mod = _import_verify()
    rows = [{"date": "2026-09-15", "underlying": f"SYM{i}",
             "skew": 0.01 * i} for i in range(5)]
    ledger = _write_ledger(tmp_path / "snapshots.parquet", rows)
    rc = subprocess.run(
        [sys.executable, str(VERIFY),
         "--ledger", str(ledger), "--pre-rows", "5"],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == mod.EXIT_NO_LEDGER
    assert "did not grow" in rc.stderr