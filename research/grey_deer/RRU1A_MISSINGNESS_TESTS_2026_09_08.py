"""Synthetic arithmetic regression over all actual international profile definitions.
Optional --patch applies one textual delta IN MEMORY ONLY. No source file is edited.
The identity percentile exposes the pre-rank aggregation, not a live radar score.
"""
from __future__ import annotations
import argparse
import ast
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
import RISK_RADAR_INTEGRITY_PROBES_2026_09_08 as probes

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "engine/risk_radar_intl.py"
RAW = SOURCE.read_bytes()
CANDIDATE = RAW

def profiles():
    env = dict(dataclass=dataclass, field=field)
    wanted = {"_BANDS", "_DISCLAIMER", "_INTL_7_DISCLAIMER"}
    selected = []
    for node in ast.parse(RAW.decode()).body:
        if isinstance(node, ast.ClassDef) and node.name == "RadarProfile":
            selected.append(node)
        elif isinstance(node, ast.Assign):
            names = {t.id for t in node.targets if isinstance(t, ast.Name)}
            if names & wanted or any(name.endswith("_PROFILE") for name in names):
                selected.append(node)
    env["__name__"] = __name__
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, *selected], type_ignores=[])), str(SOURCE), "exec"), env)
    result = sorted((value for name, value in env.items() if name.endswith("_PROFILE")), key=lambda p: p.key)
    assert {p.key for p in result} == {"cn", "hk", "ca", "kr", "jp", "tw", "in", "au", "gb", "ez"}
    return result

PROFILES = profiles()
INDEX = pd.bdate_range("2023-01-02", periods=601)

def output(profile, series, candidate=CANDIDATE):
    bench = pd.Series(np.linspace(100.0, 140.0, len(INDEX)), index=INDEX)
    env = dict(pd=pd, np=np, _PCT_WIN=504, _read=lambda *args: bench,
               _sub_legs=lambda *args: series,
               pct_rank_window=lambda s, window: s,
               _gate_series=lambda *args: pd.Series(False, index=INDEX))
    read_bytes = Path.read_bytes
    def isolated_read(path):
        return candidate if path == SOURCE else read_bytes(path)
    with patch.object(Path, "read_bytes", isolated_read):
        probes.load(ROOT, "engine/risk_radar_intl.py", ["composite_series"], env)
    return env["composite_series"](profile)[2]

def sample(profile, partial=False):
    codes = sorted({code for _, group, _ in profile.comp_legs for code in group})
    rng = np.random.default_rng(20260908)
    result = {}
    for code in codes:
        values = rng.uniform(0.05, 0.95, len(INDEX))
        if partial:
            missing = rng.random(len(INDEX)) < 0.20
            missing[:100] = False
            values[missing] = np.nan
        result[code] = pd.Series(values, index=INDEX)
    return result

def reference(profile, series):
    values = []
    for position in range(len(INDEX)):
        weighted = []
        for _, codes, weight in profile.comp_legs:
            available = [float(series[c].iloc[position]) for c in codes
                         if c in series and pd.notna(series[c].iloc[position])]
            if available:
                weighted.append((sum(available) / len(available), weight))
        value = sum(x * w for x, w in weighted) / sum(w for _, w in weighted) if weighted else np.nan
        values.append(value)
    return pd.Series(values, index=INDEX).dropna()

class MissingnessRegression(unittest.TestCase):
    pass

def make_test(profile, case):
    def test(self):
        series = sample(profile, partial=(case == "partial"))
        first_group = profile.comp_legs[0][1]
        if case == "missing_group":
            for code in first_group:
                series[code].iloc[-50:] = np.nan
        elif case == "all_missing":
            for value in series.values():
                value.iloc[-10:] = np.nan
        actual = output(profile, series, candidate=CANDIDATE)
        expected = reference(profile, series)
        self.assertEqual(list(actual.index), list(expected.index))
        np.testing.assert_allclose(actual.to_numpy(), expected.to_numpy(), rtol=1e-12, atol=1e-12)
        self.assertTrue(((actual >= 0.0) & (actual <= 1.0)).all())
        if case == "complete":
            original = output(profile, series, candidate=RAW)
            np.testing.assert_array_equal(actual.to_numpy(), original.to_numpy())
    return test

for profile in PROFILES:
    for case in ("complete", "partial", "missing_group", "all_missing"):
        setattr(MissingnessRegression, f"test_{profile.key}_{case}", make_test(profile, case))

def main():
    global CANDIDATE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patch", type=Path, help="One-line unified patch, applied only in memory")
    args = parser.parse_args()
    expected = "1596e1da4794bf97d49f6f0ae42eaabff7226fa812fb0a96bfb0a6242faf7cd7"
    if hashlib.sha256(RAW).hexdigest() != expected:
        raise SystemExit("Source pin changed: re-review before transferring this receipt.")
    if args.patch:
        lines = args.patch.read_text().splitlines()
        removed = [s[1:] for s in lines if s.startswith("-") and not s.startswith("---")]
        added = [s[1:] for s in lines if s.startswith("+") and not s.startswith("+++")]
        if len(removed) != 1 or len(added) != 1 or RAW.decode().count(removed[0]) != 1:
            raise SystemExit("Candidate must contain exactly one unique source-line replacement.")
        CANDIDATE = RAW.decode().replace(removed[0], added[0]).encode()
    print("SOURCE_SHA256", hashlib.sha256(RAW).hexdigest(), flush=True)
    print("CANDIDATE_SHA256", hashlib.sha256(CANDIDATE).hexdigest(), flush=True)
    print("PROFILE_KEYS", ",".join(p.key for p in PROFILES), flush=True)
    print("SCOPE synthetic arithmetic only; no engine file, ledger, or production mutation", flush=True)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(MissingnessRegression)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)

if __name__ == "__main__":
    main()
