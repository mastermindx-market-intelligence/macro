"""Pinned current-vintage arithmetic diagnostic; no forecasts or production writes."""
from __future__ import annotations
import ast
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import warnings
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PIN = "eb9e91961ddc4f3043d0dad358602525e66eccda"
EXPECTED = "1596e1da4794bf97d49f6f0ae42eaabff7226fa812fb0a96bfb0a6242faf7cd7"
sys.path.insert(0, str(ROOT))
from engine import risk_radar_intl as radar

CACHE = {}
INPUTS = {}
TOTAL_BYTES = 0

def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          check=True, timeout=45).stdout

def read_blob(group, name):
    global TOTAL_BYTES
    safe = name.replace("^", "_").replace("=", "_").replace("/", "_").replace(" ", "_")
    path = f"data/{group}/{safe}.parquet"
    if path in CACHE:
        return CACHE[path]
    sha = git("ls-tree", "--format=%(objectname)", PIN, "--", path).decode().strip()
    if not sha:
        INPUTS[path] = {"state": "missing_at_pin"}
        CACHE[path] = None
        return None
    size = int(git("cat-file", "-s", sha))
    if size > 20_000_000 or TOTAL_BYTES + size > 150_000_000:
        raise RuntimeError("Research input budget exceeded")
    raw = git("cat-file", "blob", sha)
    if hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() != sha:
        raise RuntimeError("Git object integrity mismatch")
    TOTAL_BYTES += len(raw)
    frame = pd.read_parquet(io.BytesIO(raw))
    frame.index = pd.to_datetime(frame.index)
    frame = frame.sort_index()
    INPUTS[path] = {"state": "read", "blob": sha,
        "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
        "rows": len(frame), "first": str(frame.index.min()),
        "last": str(frame.index.max()), "columns": list(frame.columns)}
    CACHE[path] = frame
    return frame

def candidate_function():
    raw = (ROOT / "engine/risk_radar_intl.py").read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise RuntimeError("Source differs from the frozen diagnostic")
    patch = Path(__file__).with_name("RRU1A_MISSINGNESS_CANDIDATE.patch").read_text()
    removed = [s[1:] for s in patch.splitlines() if s.startswith("-") and not s.startswith("---")]
    added = [s[1:] for s in patch.splitlines() if s.startswith("+") and not s.startswith("+++")]
    if len(removed) != 1 or len(added) != 1 or raw.decode().count(removed[0]) != 1:
        raise RuntimeError("Candidate is not a unique one-line replacement")
    revised = raw.decode().replace(removed[0], added[0])
    node = next(n for n in ast.parse(revised).body
                if isinstance(n, ast.FunctionDef) and n.name == "composite_series")
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    env = dict(radar.__dict__)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, node], type_ignores=[])),
                 "candidate_composite_series", "exec"), env)
    return env["composite_series"], hashlib.sha256(revised.encode()).hexdigest()

def states_for(series, gate, profile):
    states = series.map(lambda x: radar._band(float(x) * 100, profile.bands))
    allowed = gate.reindex(series.index).fillna(False)
    return states.where(allowed | ~states.isin(["elevated", "risk-off"]), "caution")

def numeric(value):
    return float(value) if value is not None and np.isfinite(value) else None

def profile_impact(profile, candidate):
    benchmark, sub, old, gate = radar.composite_series(profile)
    if benchmark is None or old is None or old.empty:
        return {"market": profile.key, "status": "insufficient_inputs"}
    benchmark2, sub2, new, gate2 = candidate(profile)
    if new is None or new.empty:
        return {"market": profile.key, "status": "candidate_unavailable"}
    pd.testing.assert_series_equal(benchmark, benchmark2)
    pd.testing.assert_series_equal(gate, gate2)
    common = old.dropna().index.intersection(new.dropna().index)
    delta = (old.reindex(common) - new.reindex(common)).abs() * 100
    before = states_for(old.reindex(common), gate, profile)
    after = states_for(new.reindex(common), gate, profile)
    changed = delta > 1e-9
    coverage_parts = {}
    for key, codes, weight in profile.comp_legs:
        members = [sub[c] for c in codes if c in sub]
        coverage_parts[key] = pd.concat(members, axis=1).mean(axis=1).reindex(benchmark.index) if members else pd.Series(np.nan, index=benchmark.index)
    coverage = pd.DataFrame(coverage_parts).notna()
    final = common[-1] if len(common) else None
    return {"market": profile.key, "status": "complete", "bench": list(profile.bench),
        "paired_dates": len(common), "changed_percentiles": int(changed.sum()),
        "max_score_point_difference": numeric(delta.max()),
        "changed_gated_states": int((before != after).sum()),
        "historical_incomplete_group_dates": int((~coverage.all(axis=1)).sum()),
        "latest_group_availability": coverage.iloc[-1].to_dict(),
        "latest": None if final is None else {"date": str(final),
            "baseline_score": numeric(old.loc[final] * 100), "candidate_score": numeric(new.loc[final] * 100),
            "baseline_state": before.loc[final], "candidate_state": after.loc[final]},
        "last_changed_date": str(common[changed.to_numpy()][-1]) if changed.any() else None}

def main():
    candidate, candidate_sha = candidate_function()
    original_reader = radar.store.read
    rows = []
    radar.store.read = read_blob
    try:
        with warnings.catch_warnings(record=True) as notices:
            warnings.simplefilter("always")
            for key, profile in radar.PROFILES.items():
                try:
                    rows.append(profile_impact(profile, candidate))
                except Exception as exc:
                    rows.append({"market": key, "status": "failed",
                                 "error_type": type(exc).__name__, "error": str(exc)[:300]})
                print("PROFILE_FINISHED", key, rows[-1]["status"], file=sys.stderr, flush=True)
            warning_text = sorted({str(item.message) for item in notices})
    finally:
        radar.store.read = original_reader
    unchanged = hashlib.sha256((ROOT / "engine/risk_radar_intl.py").read_bytes()).hexdigest() == EXPECTED
    result = {"source_data_pin": PIN, "source_sha256": EXPECTED,
        "candidate_sha256": candidate_sha, "source_unchanged": unchanged,
        "kind": "current_vintage_arithmetic_sensitivity_NOT_PIT_forecast_validation",
        "outcomes_inspected": False, "production_mutations": 0,
        "input_bytes": TOTAL_BYTES, "inputs": INPUTS, "profiles": rows,
        "warnings": warning_text, "all_profiles_complete": len(rows) == 10 and all(r["status"] == "complete" for r in rows)}
    print(json.dumps(result, indent=2, allow_nan=False))
    if not unchanged or not result["all_profiles_complete"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
