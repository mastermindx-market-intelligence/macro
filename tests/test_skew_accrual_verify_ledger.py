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
    """A ledger with at least one row → exit 0."""
    mod = _import_verify()
    ledger = _write_ledger(tmp_path / "snapshots.parquet", [
        {"date": "2026-09-22", "underlying": "SPY", "skew": 0.05},
    ])
    code, info = mod.check(ledger)
    assert code == mod.EXIT_OK
    assert info["rows"] == 1
    assert info["bytes"] > 0
    assert "content" in info["reason"]


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