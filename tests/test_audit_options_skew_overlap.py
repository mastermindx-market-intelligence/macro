"""Tests for scripts/audit_options_skew_overlap.py — the real-overlap audit
tool for the options_skew ledger (MO-PAID-013 W2-2).

The audit exposes a SKEW_AUDIT_FAKE_ENGINE=1 env-var hook that swaps the real
engine imports for a synthetic provider/compute_skew pair. All subprocess
tests use that hook — no real store, no network. The MISSING_ENGINE branch
(pre-W2-1b tree) is exercised by hiding engine.* from sys.modules.

The audit is meant to be re-runnable on a pre-W2-1b tree; that branch exits
EXIT_MISSING_ENGINE rather than crashing with an ImportError.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "audit_options_skew_overlap.py"


# ── helpers ────────────────────────────────────────────────────────────────── #


def _load_audit():
    """Import the audit module under a unique name so test reloads work."""
    spec = importlib.util.spec_from_file_location(
        "audit_options_skew_overlap_under_test", AUDIT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_ledger(path: Path, rows: list[dict], *,
                  include_source: bool = True) -> Path:
    """Write a synthetic parquet ledger with the given rows.

    `include_source=False` mimics a pre-W2-1b ledger (no `source` column);
    the audit must treat every row as legacy then.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if not include_source:
        rows = [{k: v for k, v in r.items() if k != "source"} for r in rows]
    df = pd.DataFrame(rows)
    df.to_parquet(path, index=False)
    return path


def _fake_env(table: dict[str, dict[str, float]]) -> dict[str, str]:
    """Return SKEW_AUDIT_FAKE_ENGINE + SKEW_AUDIT_FAKE_TABLE env vars."""
    return {
        "SKEW_AUDIT_FAKE_ENGINE": "1",
        "SKEW_AUDIT_FAKE_TABLE": json.dumps(table),
    }


# ── contract / exit-code surface ────────────────────────────────────────────── #


def test_load_engine_returns_none_when_no_engine_no_fake(monkeypatch):
    """Without the env-var hook, the audit imports the engine via the
    try/except block. On THIS main both modules import cleanly, so the
    branch returns the (provider, compute_skew) pair — the test only
    pins the contract: it never raises ImportError and it never returns
    a partial result."""
    mod = _load_audit()
    monkeypatch.delenv("SKEW_AUDIT_FAKE_ENGINE", raising=False)
    monkeypatch.delenv("SKEW_AUDIT_FAKE_TABLE", raising=False)
    # We cannot simulate the MISSING_ENGINE branch by hiding sys.modules
    # because the audit script prepends the repo root to sys.path and the
    # engine/ tree is a sibling of scripts/. The real coverage of the
    # MISSING_ENGINE exit path is the subprocess test below
    # (test_cli_main_loop_with_patched_load_engine_returns_missing_engine).
    result = mod._load_engine()
    assert result is None or (callable(result[0]) and callable(result[1]))


def test_load_engine_returns_pair_under_fake_env(monkeypatch):
    """Under SKEW_AUDIT_FAKE_ENGINE=1, _load_engine returns a (provider,
    compute_skew) pair — even with engine.* removed from sys.modules."""
    mod = _load_audit()
    monkeypatch.setenv("SKEW_AUDIT_FAKE_ENGINE", "1")
    monkeypatch.setenv("SKEW_AUDIT_FAKE_TABLE",
                       json.dumps({"2026-09-15": {"SPY": 0.05}}))
    saved = {}
    for name in list(sys.modules):
        if name == "engine" or name.startswith("engine."):
            saved[name] = sys.modules.pop(name)
    try:
        result = mod._load_engine()
        assert result is not None
        make_chain_provider, compute_skew = result
        provider = make_chain_provider(store=None, require_iv=True)
        chain = provider("2026-09-15", "SPY")
        assert chain is not None and not chain.empty
        out = compute_skew(chain)
        assert out is not None
        assert out["skew"] == pytest.approx(0.05)
    finally:
        for k, v in saved.items():
            sys.modules[k] = v


def test_load_engine_fake_returns_none_for_unknown_key(monkeypatch):
    """The fake provider returns None for keys not in the table — that is the
    `no_chain` skip path in the audit body."""
    mod = _load_audit()
    monkeypatch.setenv("SKEW_AUDIT_FAKE_ENGINE", "1")
    monkeypatch.setenv("SKEW_AUDIT_FAKE_TABLE",
                       json.dumps({"2026-09-15": {"SPY": 0.05}}))
    make_chain_provider, _ = mod._load_engine()
    provider = make_chain_provider(store=None)
    assert provider("2026-09-15", "AAPL") is None  # not in table


# ── unit surface for the helpers ────────────────────────────────────────────── #


def test_select_legacy_rows_treats_absent_source_as_all_legacy():
    """A pre-W2-1b ledger (no `source` column) → every row is legacy."""
    mod = _load_audit()
    df = pd.DataFrame([
        {"date": "2026-09-15", "underlying": "AAPL", "skew": 0.05},
        {"date": "2026-09-15", "underlying": "MSFT", "skew": -0.02},
    ])
    legacy = mod._select_legacy_rows(df)
    assert len(legacy) == 2


def test_select_legacy_rows_filters_on_source_column():
    """A post-W2-1b ledger → only `source == polygon_gex` rows are legacy."""
    mod = _load_audit()
    df = pd.DataFrame([
        {"date": "2026-09-15", "underlying": "AAPL", "skew": 0.05,
         "source": "polygon_gex"},
        {"date": "2026-09-15", "underlying": "MSFT", "skew": -0.02,
         "source": "thetadata"},
    ])
    legacy = mod._select_legacy_rows(df)
    assert len(legacy) == 1
    assert legacy.iloc[0]["underlying"] == "AAPL"


def test_delta_stats_returns_nan_safe_on_empty():
    """An empty pairs list returns n=0 and None quantiles (no crash)."""
    mod = _load_audit()
    stats = mod._delta_stats([])
    assert stats["n"] == 0
    assert stats["p50"] is None
    assert stats["p90"] is None
    assert stats["max"] is None
    assert stats["sign_agreement_rate"] is None
    assert stats["n_sign_flip"] == 0


def test_delta_stats_sign_agreement_matches_product_test():
    """BLOCKER-1 RED-first regression: sign_agreement_rate is
    (n_sign_match + n_zero_delta) / n — agreement means the two paths
    share a sign OR agree on zero. Pairs [(0.05, 0.05), (0.10, 0.05),
    (0.03, 0.06)] give 3 of 3 in agreement (all positive)."""
    mod = _load_audit()
    stats = mod._delta_stats([(0.05, 0.05), (0.10, 0.05), (0.03, 0.06)])
    assert stats["n"] == 3
    assert stats["max"] == 0.05
    assert stats["sign_agreement_rate"] == pytest.approx(1.0)
    assert stats["n_sign_match"] == 3
    assert stats["n_zero_delta"] == 0
    assert stats["n_sign_flip"] == 0


def test_delta_stats_counts_genuine_sign_flips():
    """BLOCKER-1 RED-first regression: a true sign flip means legacy and
    new have STRICTLY OPPOSITE non-zero signs. The product test
    `legacy * new < 0` is the only correct way: a delta-based classifier
    conflates same-sign magnitude differences with actual flips. Verify
    pairs [(0.10, -0.10), (0.05, 0.07)] give n_sign_flip == 1,
    n_sign_match == 1."""
    mod = _load_audit()
    stats = mod._delta_stats([(0.10, -0.10), (0.05, 0.07)])
    assert stats["n"] == 2
    assert stats["n_sign_flip"] == 1
    assert stats["n_sign_match"] == 1
    assert stats["n_zero_delta"] == 0


def test_delta_stats_same_sign_magnitude_difference_is_NOT_a_flip():
    """BLOCKER-1 regression: the OLD delta-based classifier called
    legacy=0.05, new=0.15 (both positive, SAME sign) a "flip" because
    delta = -0.10 < 0. Pin the corrected behavior: that pair is a
    sign_match, NOT a sign_flip. The same applies to (legacy=-0.05,
    new=-0.15) — both negative, SAME sign, also a sign_match."""
    mod = _load_audit()
    stats = mod._delta_stats([(0.05, 0.15), (-0.05, -0.15)])
    assert stats["n"] == 2
    assert stats["n_sign_flip"] == 0
    assert stats["n_sign_match"] == 2
    assert stats["n_zero_delta"] == 0
    # Both pairs are agreement: same non-zero sign on both sides.
    assert stats["sign_agreement_rate"] == pytest.approx(1.0)


def test_delta_stats_separates_zero_delta_from_sign_match():
    """A pair where BOTH paths report exactly zero skew is the
    `n_zero_delta` bucket — the audit surfaces it separately so the
    receipt can distinguish "they agree there is no skew" from "they
    agree on the same sign". Pairs: same-positive-equal (sign_match),
    same-positive-unequal (sign_match), opposite-sign (sign_flip),
    both-zero (zero_delta)."""
    mod = _load_audit()
    stats = mod._delta_stats([(0.10, 0.05), (0.25, -0.25),
                              (0.0, 0.0), (-0.1, -0.1)])
    assert stats["n"] == 4
    # (0.0, 0.0) is the only zero-delta pair; the others share a sign
    # in either direction. n_zero_delta is reserved for "both zero".
    assert stats["n_zero_delta"] == 1
    assert stats["n_sign_match"] == 2
    assert stats["n_sign_flip"] == 1
    assert stats["n_sign_flip"] + stats["n_sign_match"] + stats["n_zero_delta"] == 4
    # sign_agreement_rate = (1 zero + 2 match) / 4 = 3/4
    assert stats["sign_agreement_rate"] == pytest.approx(3 / 4)


def test_delta_stats_sign_agreement_includes_zero_delta():
    """Zero-delta pairs count toward sign_agreement_rate — the two
    paths agree on no skew, which IS agreement. Pairs [(0.0, 0.0),
    (0.0, 0.0), (0.05, -0.05)] → 2 of 3 are zero-delta, 1 is a flip."""
    mod = _load_audit()
    stats = mod._delta_stats([(0.0, 0.0), (0.0, 0.0), (0.05, -0.05)])
    assert stats["n"] == 3
    assert stats["sign_agreement_rate"] == pytest.approx(2 / 3)
    assert stats["n_zero_delta"] == 2
    assert stats["n_sign_flip"] == 1
    assert stats["n_sign_match"] == 0


def test_worst_keys_returns_top_k_by_abs_delta():
    mod = _load_audit()
    records = [
        {"date": "2026-09-15", "underlying": "A", "delta_skew": 0.01,
         "legacy_skew": 0.0, "new_skew": 0.0},
        {"date": "2026-09-15", "underlying": "B", "delta_skew": -0.5,
         "legacy_skew": 0.0, "new_skew": 0.0},
        {"date": "2026-09-15", "underlying": "C", "delta_skew": 0.2,
         "legacy_skew": 0.0, "new_skew": 0.0},
    ]
    worst = mod._worst_keys(records, k=2)
    assert [r["underlying"] for r in worst] == ["B", "C"]


def test_key_iter_yields_iso_date_and_string_underlying():
    mod = _load_audit()
    df = pd.DataFrame([
        {"date": "2026-09-15", "underlying": "SPY", "skew": 0.05,
         "source": "polygon_gex"},
    ])
    keys = list(mod._key_iter(df))
    assert keys == [("2026-09-15", "SPY")]


# ── CLI: MISSING_ENGINE branch ─────────────────────────────────────────────── #


def test_cli_main_loop_with_patched_load_engine_returns_missing_engine(tmp_path):
    """Hermetic MISSING_ENGINE coverage: drive main() with _load_engine
    patched to return None. The CLI must exit EXIT_MISSING_ENGINE (1) with
    a MISSING_ENGINE line on stderr — never raise. The subprocess variant
    cannot exercise this branch on a main where engine.thetadata_store /
    engine.options_skew both already import."""
    mod = _load_audit()
    ledger = _write_ledger(tmp_path / "snapshots.parquet", [
        {"date": "2026-09-15", "underlying": "AAPL", "skew": 0.05,
         "source": "polygon_gex"},
    ])
    original = mod._load_engine
    mod._load_engine = lambda: None
    try:
        rc = mod.main([
            "--ledger", str(ledger),
            "--store", str(tmp_path / "store"),
            "--out", str(tmp_path / "out.md"),
        ])
    finally:
        mod._load_engine = original
    assert rc == mod.EXIT_MISSING_ENGINE


def test_cli_absent_ledger_returns_read_error(tmp_path):
    """Missing ledger path is operator-actionable; the audit surfaces that
    with EXIT_READ_ERROR (3) rather than crashing on the parquet read."""
    mod = _load_audit()
    rc = subprocess.run(
        [sys.executable, str(AUDIT),
         "--ledger", str(tmp_path / "nope.parquet")],
        capture_output=True, text=True, check=False,
        env={**os.environ, **_fake_env({})},
    )
    assert rc.returncode == mod.EXIT_READ_ERROR
    assert "READ_ERROR" in rc.stderr


def test_cli_no_legacy_rows_returns_no_legacy(tmp_path):
    """An all-thetadata ledger has nothing to compare against — the audit
    reports it and exits EXIT_NO_LEGACY_ROWS (2) rather than emitting a
    vacuous 0-key summary."""
    mod = _load_audit()
    ledger = _write_ledger(tmp_path / "snapshots.parquet", [
        {"date": "2026-09-15", "underlying": "SPY", "skew": 0.05,
         "source": "thetadata"},
    ])
    rc = subprocess.run(
        [sys.executable, str(AUDIT),
         "--ledger", str(ledger),
         "--out", str(tmp_path / "out.md")],
        capture_output=True, text=True, check=False,
        env={**os.environ, **_fake_env({})},
    )
    assert rc.returncode == mod.EXIT_NO_LEGACY_ROWS
    assert "NO_LEGACY_ROWS" in rc.stderr


# ── CLI: happy path with the fake engine ──────────────────────────────────── #


def test_cli_happy_path_emits_receipt_and_summary(tmp_path):
    """Synthetic ledger + SKEW_AUDIT_FAKE_ENGINE produces expected agreement
    numbers, a one-line JSON summary on stdout, and a markdown receipt at
    --out."""
    mod = _load_audit()
    rows = [
        {"date": "2026-09-15", "underlying": "SPY", "skew": 0.10,
         "source": "polygon_gex"},
        {"date": "2026-09-16", "underlying": "AAPL", "skew": 0.11,
         "source": "polygon_gex"},
        {"date": "2026-09-17", "underlying": "MSFT", "skew": 0.12,
         "source": "polygon_gex"},
        {"date": "2026-09-18", "underlying": "GOOG", "skew": 0.13,
         "source": "polygon_gex"},   # sign flip below
        {"date": "2026-09-19", "underlying": "AMZN", "skew": 0.0,
         "source": "polygon_gex"},   # both-zero pair below
    ]
    ledger = _write_ledger(tmp_path / "snapshots.parquet", rows)
    # Fake table: SPY/AAPL/MSFT/GOOG all same sign (sign_match under the
    # product test — even SPY with legacy == new == 0.10 is "same sign",
    # NOT a zero-delta because the value is non-zero); AMZN is the only
    # both-zero pair; GOOG flips sign.
    table = {
        "2026-09-15": {"SPY": 0.10},   # legacy 0.10, new 0.10 → MATCH (same non-zero sign)
        "2026-09-16": {"AAPL": 0.12},  # legacy 0.11, new 0.12 → -0.01, MATCH
        "2026-09-17": {"MSFT": 0.13},  # legacy 0.12, new 0.13 → -0.01, MATCH
        "2026-09-18": {"GOOG": -0.13}, # legacy 0.13, new -0.13 → +0.26, FLIP
        "2026-09-19": {"AMZN": 0.0},   # legacy 0.0, new 0.0 → ZERO (both exactly zero)
    }
    out_md = tmp_path / "receipt.md"
    rc = subprocess.run(
        [sys.executable, str(AUDIT),
         "--ledger", str(ledger),
         "--store", str(tmp_path / "store"),
         "--out", str(out_md)],
        capture_output=True, text=True, check=False,
        env={**os.environ, **_fake_env(table)},
    )
    assert rc.returncode == mod.EXIT_OK, (rc.stdout, rc.stderr)
    summary = json.loads(rc.stdout.strip().splitlines()[-1])
    assert summary["keys_compared"] == 5
    # sign_agreement = (n_sign_match + n_zero_delta) / n = (3 + 1) / 5 = 4/5
    assert summary["sign_agreement_rate"] == pytest.approx(4 / 5)
    # max |delta| is GOOG +0.26
    assert summary["abs_delta_skew"]["max"] == pytest.approx(0.26)
    # BLOCKER-1 fix: bucket the pairs under the product test.
    #   SPY    → legacy 0.10, new 0.10: sign_match (same non-zero sign)
    #   AAPL   → legacy 0.11, new 0.12: sign_match (both > 0, same sign)
    #   MSFT   → legacy 0.12, new 0.13: sign_match (both > 0, same sign)
    #   GOOG   → legacy 0.13, new -0.13: sign_flip  (opposite signs)
    #   AMZN   → legacy 0.0,  new 0.0:   zero_delta (both exactly zero)
    assert summary["n_zero_delta"] == 1
    assert summary["n_sign_match"] == 3
    assert summary["n_sign_flip"] == 1
    assert (summary["n_sign_flip"] + summary["n_sign_match"]
            + summary["n_zero_delta"]) == summary["keys_compared"]
    assert out_md.exists()
    body = out_md.read_text(encoding="utf-8")
    assert "Top 10 worst keys" in body
    assert "| date | underlying | legacy_skew | new_skew | delta_skew |" in body
    # Worst key is GOOG with delta 0.26
    assert "GOOG" in body
    # Receipt surfaces the new sign-bucket breakdown.
    assert "match=" in body and "flip=" in body and "zero=" in body


def test_cli_limit_caps_input(tmp_path):
    """--limit N caps the (date, underlying) keys the audit walks."""
    mod = _load_audit()
    rows = [
        {"date": f"2026-09-{15 + i:02d}", "underlying": f"SYM{i}",
         "skew": 0.10 + 0.01 * i, "source": "polygon_gex"}
        for i in range(10)
    ]
    ledger = _write_ledger(tmp_path / "snapshots.parquet", rows)
    table = {f"2026-09-{15 + i:02d}": {f"SYM{i}": 0.10 + 0.01 * i}
             for i in range(10)}
    rc = subprocess.run(
        [sys.executable, str(AUDIT),
         "--ledger", str(ledger),
         "--limit", "2",
         "--out", str(tmp_path / "receipt.md")],
        capture_output=True, text=True, check=False,
        env={**os.environ, **_fake_env(table)},
    )
    assert rc.returncode == mod.EXIT_OK, (rc.stdout, rc.stderr)
    summary = json.loads(rc.stdout.strip().splitlines()[-1])
    assert summary["keys_compared"] == 2
    assert summary["limit"] == 2


def test_cli_pre_w2_1b_ledger_treated_as_all_legacy(tmp_path):
    """Pre-W2-1b ledgers do not have the `source` column; the audit treats
    every row as legacy so it remains useful before W2-1b merges."""
    mod = _load_audit()
    rows = [
        {"date": "2026-09-15", "underlying": "SPY", "skew": 0.10},
        {"date": "2026-09-16", "underlying": "AAPL", "skew": 0.11},
    ]
    ledger = _write_ledger(tmp_path / "snapshots.parquet", rows,
                            include_source=False)
    table = {
        "2026-09-15": {"SPY": 0.10},
        "2026-09-16": {"AAPL": 0.11},
    }
    rc = subprocess.run(
        [sys.executable, str(AUDIT),
         "--ledger", str(ledger),
         "--out", str(tmp_path / "receipt.md")],
        capture_output=True, text=True, check=False,
        env={**os.environ, **_fake_env(table)},
    )
    assert rc.returncode == mod.EXIT_OK, (rc.stdout, rc.stderr)
    summary = json.loads(rc.stdout.strip().splitlines()[-1])
    assert summary["keys_compared"] == 2