"""Hermetic entrypoint regressions for #10090's computation-failure boundary.

Run with stdlib unittest or pytest. MACRO_BUILDER_TEST_SOURCE can point at an
unaltered baseline copy to witness the expected RED. No Parquet engine is needed:
only pd.read_parquet is replaced with deterministic synthetic DataFrames. Healthy
names use the real analyzer and append-only marker merge. No production data,
publisher, network, or global source edits are involved.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings

SOURCE = Path(os.environ.get("MACRO_BUILDER_TEST_SOURCE", Path(__file__).resolve().parents[1])).resolve()
SYMBOLS = ("SYN00", "SYN01", "SYN02")


def _artifacts(root):
    paths = [*sorted((root / "site/signals").glob("*.json"))]
    leaf = root / "data/signal_archive/mtf_signals_latest.json"
    if leaf.exists():
        paths.append(leaf)
    return {str(p.relative_to(root)): p.read_bytes() for p in paths}


def _child(case, root):
    def no_network(event, args):
        if event.startswith("socket."):
            raise RuntimeError("network forbidden by synthetic fixture")

    sys.addaudithook(no_network)
    sys.path.insert(0, str(SOURCE))
    import numpy as np
    import pandas as pd
    from datetime import datetime, timezone
    from scripts import build_signal_quality as builder

    idx = pd.bdate_range("2019-01-01", periods=900)
    t = np.arange(len(idx), dtype=float)
    close = pd.Series(100 + 18 * np.sin(t / 33) + .015 * t + 4 * np.sin(t / 6), index=idx)
    healthy = pd.DataFrame({"close": close})
    short = healthy.iloc[:3].copy()
    actual_analyze = builder.analyze
    actual_merge = builder.marker_integrity.merge_payload
    source_dir = root / "data/stocks"
    source_dir.mkdir(parents=True)
    for symbol in SYMBOLS:
        (source_dir / f"{symbol}.parquet").write_text("synthetic token, not Parquet or market data")

    if case != "fresh_late_error":
        prior_rows = []
        for symbol in (*SYMBOLS, "EXTRA"):
            prior = actual_analyze(symbol, healthy["close"].iloc[:860])
            prior = actual_merge(None, prior, run_stamp="2026-10-21")
            path = root / "site/signals" / f"{symbol}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(prior, separators=(",", ":")))
            if symbol in SYMBOLS:
                prior_rows.append({k: prior[k] for k in ("ticker", "asof", "state", "above200", "weekly_bull", "trail_breach", "trail_stop", "early_now")})
                prior_rows[-1]["last"] = prior["markers"][-1] if prior["markers"] else None
        leaf = root / "data/signal_archive/mtf_signals_latest.json"
        leaf.parent.mkdir(parents=True, exist_ok=True)
        leaf.write_text(json.dumps({"asof": prior_rows[-1]["asof"], "tf": "3D", "universe": "us_deep", "source": "daily_adjusted", "note": "synthetic prior leaf", "signals": prior_rows}, indent=1) + "\n")
    before = _artifacts(root)
    # Save actual bytes, not just hashes, so the parent can assert exact preservation.
    (root / "before.json").write_text(json.dumps({k: v.decode() for k, v in before.items()}))
    fail_symbol = SYMBOLS[0] if case.startswith("early_") else SYMBOLS[-1]
    intraday = "intraday" in case

    def synthetic_read(path, *args, **kwargs):
        p = Path(path).resolve()
        assert p.parent == source_dir.resolve() and p.stem in SYMBOLS, p
        if p.stem == fail_symbol and case in {"early_read_error", "late_read_error", "late_intraday_read_error"}:
            raise OSError("synthetic_read_failure")
        if p.stem == fail_symbol and case == "late_missing_close":
            return healthy.rename(columns={"close": "not_close"}).copy()
        if case == "all_insufficient" or (case == "insufficient" and p.stem == SYMBOLS[1]):
            return short.copy()
        return healthy.copy()

    def analyze(symbol, *args, **kwargs):
        if symbol == fail_symbol and case in {"early_analyze_error", "late_analyze_error", "fresh_late_error"}:
            raise RuntimeError("synthetic_analyze_failure")
        value = actual_analyze(symbol, *args, **kwargs)
        if symbol == fail_symbol and case == "late_serialize_error":
            value["non_json_fixture"] = {1, 2}
        return value

    def merge(previous, result, **kwargs):
        if result["ticker"] == fail_symbol and case == "late_merge_error":
            raise RuntimeError("synthetic_merge_failure")
        return actual_merge(previous, result, **kwargs)

    def intraday_close(symbol, **kwargs):
        if symbol == fail_symbol and case == "late_intraday_derive_error":
            raise OSError("synthetic_intraday_failure")
        return None  # Exercises the real intraday -> adjusted-store fallback.

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 22, 18, 0, tzinfo=timezone.utc)

    argv = ["build_signal_quality.py"] + (["--intraday"] if intraday else [])
    with warnings.catch_warnings(), patch.object(builder, "ROOT", root), patch.object(builder, "datetime", FrozenDatetime), patch.object(builder.pd, "read_parquet", synthetic_read), patch.object(builder, "analyze", analyze), patch.object(builder.marker_integrity, "merge_payload", merge), patch.object(builder, "daily_close_for", intraday_close), patch.object(sys, "argv", argv):
        warnings.simplefilter("ignore", FutureWarning)
        builder.main()


class TestBuildSignalQualityFailClosed(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="signal_build_test_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def run_case(self, case):
        env = dict(os.environ, MACRO_BUILDER_TEST_SOURCE=str(SOURCE), PYTHONDONTWRITEBYTECODE="1", PYTHONWARNINGS="ignore::FutureWarning")
        p = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--builder-child", case, str(self.root)], env=env, text=True, capture_output=True, timeout=60)
        before = {k: v.encode() for k, v in json.loads((self.root / "before.json").read_text()).items()}
        after = _artifacts(self.root)
        return p, before, after

    def assert_failed_without_publication(self, case, message=None):
        p, before, after = self.run_case(case)
        # Both properties matter: raising after writing early symbols is not safe.
        self.assertNotEqual(p.returncode, 0, (case, p.stdout, p.stderr))
        self.assertEqual(before, after, "failed computation modified the accepted artifact set")
        self.assertNotIn("wrote ", p.stdout)
        if case not in {"late_merge_error", "late_serialize_error"}:
            self.assertIn("SignalBuildError", p.stderr)
        if message:
            self.assertIn(message, p.stderr)

    def test_early_read_error_preserves_both_shapes(self):
        self.assert_failed_without_publication("early_read_error", "SYN00")

    def test_late_read_error_preserves_both_shapes(self):
        self.assert_failed_without_publication("late_read_error", "SYN02")

    def test_early_analyzer_error_preserves_both_shapes(self):
        self.assert_failed_without_publication("early_analyze_error", "SYN00")

    def test_late_analyzer_error_preserves_both_shapes(self):
        self.assert_failed_without_publication("late_analyze_error", "SYN02")

    def test_missing_close_preserves_both_shapes(self):
        self.assert_failed_without_publication("late_missing_close", "KeyError")

    def test_intraday_fallback_read_error_preserves_both_shapes(self):
        self.assert_failed_without_publication("late_intraday_read_error", "SYN02")

    def test_intraday_derivation_error_preserves_both_shapes(self):
        self.assert_failed_without_publication("late_intraday_derive_error", "SYN02")

    def test_fresh_failed_build_creates_no_signal_artifacts(self):
        self.assert_failed_without_publication("fresh_late_error", "SYN02")

    def test_late_merge_error_preserves_both_shapes(self):
        self.assert_failed_without_publication("late_merge_error", "synthetic_merge_failure")

    def test_late_serialization_error_preserves_both_shapes(self):
        self.assert_failed_without_publication("late_serialize_error", "TypeError")

    def assert_success(self, case, expected):
        p, before, after = self.run_case(case)
        self.assertEqual(p.returncode, 0, (p.stdout, p.stderr))
        leaf = json.loads(after["data/signal_archive/mtf_signals_latest.json"])
        self.assertEqual([s["ticker"] for s in leaf["signals"]], expected)
        self.assertEqual(before["site/signals/EXTRA.json"], after["site/signals/EXTRA.json"])
        self.assertEqual(leaf["asof"], leaf["signals"][-1]["asof"] if expected else None)
        self.assertEqual(leaf["source"], "intraday_delayed" if "intraday" in case else "daily_adjusted")
        for symbol in expected:
            path = f"site/signals/{symbol}.json"
            self.assertNotEqual(before[path], after[path])
            previous = json.loads(before[path])
            current = json.loads(after[path])
            old_by_key = {(m["date"], m["type"]): m for m in previous["markers"]}
            current_by_key = {(m["date"], m["type"]): m for m in current["markers"]}
            for key, marker in old_by_key.items():
                self.assertIn(key, current_by_key)
                self.assertIn("recorded_at", marker)
                self.assertEqual(marker["recorded_at"], current_by_key[key]["recorded_at"])
        validation = subprocess.run([sys.executable, str(SOURCE / "scripts/validate_signals.py"), "--signals-dir", str(self.root / "site/signals"), "--leaf", str(self.root / "data/signal_archive/mtf_signals_latest.json"), "--audit", str(self.root / "audit.json"), "--schema", str(SOURCE / "research/signal_engine/SCHEMA.json")], text=True, capture_output=True, timeout=60)
        self.assertEqual(validation.returncode, 0 if expected else 1, (validation.stdout, validation.stderr))
        return before, after

    def test_complete_history_still_builds_with_sticky_markers(self):
        self.assert_success("complete", list(SYMBOLS))

    def test_genuine_insufficiency_remains_nonfatal(self):
        before, after = self.assert_success("insufficient", [SYMBOLS[0], SYMBOLS[2]])
        self.assertEqual(before[f"site/signals/{SYMBOLS[1]}.json"], after[f"site/signals/{SYMBOLS[1]}.json"])

    def test_all_insufficient_retains_existing_empty_leaf_behavior(self):
        # Not a coverage fix: legacy all-None behavior still returns 0/asof=null.
        self.assert_success("all_insufficient", [])

    def test_intraday_fallback_still_builds(self):
        self.assert_success("complete_intraday", list(SYMBOLS))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--builder-child":
        _child(sys.argv[2], Path(sys.argv[3]))
    else:
        unittest.main()
