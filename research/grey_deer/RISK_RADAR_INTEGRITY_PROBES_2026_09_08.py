"""Read-only, source-bound research probes; not a production engine or grader.
Run from the repo: python3 research/grey_deer/RISK_RADAR_INTEGRITY_PROBES_2026_09_08.py
Functions are extracted unchanged from the named files; dependencies are isolated.
Synthetic observations demonstrate mechanisms, never historical production impact.
"""
from __future__ import annotations
import argparse
import ast
from datetime import date, datetime, timedelta
import hashlib
import json
import logging
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd

PIN = "eb9e91961ddc4f3043d0dad358602525e66eccda"
SOURCE_HASHES = {}
RESULTS = []

def load(root, relative, names, env):
    raw = (root / relative).read_bytes()
    SOURCE_HASHES[relative] = hashlib.sha256(raw).hexdigest()
    nodes = ast.parse(raw.decode()).body
    selected = [n for n in nodes if isinstance(n, ast.FunctionDef) and n.name in names]
    if {n.name for n in selected} != set(names):
        raise RuntimeError(f"Source function missing: {relative}: {names}")
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, *selected], type_ignores=[])), relative, "exec"), env)

def record(key, observed, expected, mechanism, kind="contract_violation"):
    RESULTS.append(dict(key=key, observed=observed, expected=expected,
                        reproduced=observed != expected, kind=kind, mechanism=mechanism))

class FrozenDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 9, 8)

def freshness_probe(root):
    env = dict(date=FrozenDate, datetime=datetime)
    load(root, "engine/risk_radar_recovery.py", ["_recent"], env)
    recent = env["_recent"]
    assert recent("2026-09-08") is True
    assert recent("2026-07-10") is True
    assert recent("2026-07-09") is False
    record("future_catalyst_is_recent", recent("2026-09-09"), False,
           "The age check has an upper bound but no nonnegative lower bound.")

def composite_probe(root):
    idx = pd.bdate_range("2025-01-01", periods=301)
    bench = pd.Series(np.linspace(100, 130, len(idx)), index=idx)
    a = pd.Series(0.9, index=idx)
    b = a.copy()
    b.iloc[-1] = np.nan
    profile = SimpleNamespace(bench=("fixture", "index"), comp_legs=(
        ("a", ("a",), 1.0), ("b", ("b",), 1.0)))
    env = dict(pd=pd, np=np, _PCT_WIN=504, _read=lambda *args: bench)
    env.update(_sub_legs=lambda *args: {"a": a, "b": b},
               pct_rank_window=lambda series, window: series,
               _gate_series=lambda *args: pd.Series(False, index=idx))
    load(root, "engine/risk_radar_intl.py", ["composite_series"], env)
    result = env["composite_series"](profile)[2]
    assert np.isclose(result.iloc[-2], 0.9)
    record("missing_component_raw_blend", float(result.iloc[-1]), 0.9,
           "Identity percentile isolates the blend: missing weight remains in numerator, not denominator.")

def null_snapshot_probe(root):
    idx = pd.bdate_range("2025-01-01", periods=301)
    bench = pd.Series(np.linspace(100, 130, len(idx)), index=idx)
    score = pd.Series(np.nan, index=idx)
    states = ["calm", "watch", "caution", "elevated", "risk-off"]
    bands = dict(watch=58.0, caution=72.0, elevated=83.0, risk_off=91.0)
    base = dict(h5=0.05, h10=0.10, h21=0.20)
    cal = dict(bands=bands, prob_base=base,
               prob_cal={h: {s: value for s in states} for h, value in base.items()})
    profile = SimpleNamespace(key="cn", disclaimer=None, scares=(), comp_legs=(),
                              gate_mode="below_200dma", ext_sources=(),
                              caveat_en="fixture", caveat_zh="fixture")
    env = dict(pd=pd, np=np, _STATE_ORDER=states, _DISCLAIMER="fixture",
               _GROSS={s: 1.0 for s in states}, _calib=lambda *args: cal,
               _trajectory=lambda *args, **kwargs: None)
    env["composite_series"] = lambda *args: (
        bench, {}, score, pd.Series(True, index=idx))
    load(root, "engine/risk_radar_intl.py", ["_last", "_band", "_probs", "compute"], env)
    out = env["compute"](profile)
    record("all_null_composite_emits_calm", out.get("state"), None,
           "Public compute reaches _band(None) and emits baseline probabilities without a score.")
    score.iloc[:-1] = 0.9
    out = env["compute"](profile)
    current_without_coverage = bool(out.get("asof") == str(idx[-1].date())
        and out.get("state") is not None and not out.get("degraded_reason"))
    record("stale_score_relabelled_current", current_without_coverage, False,
           "_last drops the missing final observation; compute labels the old score with the benchmark's new date.")

def morphology_probe(root):
    env = {}
    load(root, "engine/risk_radar_market_catalysts.py", ["_morphology"], env)
    out = env["_morphology"]([])
    record("no_chips_is_grinding_recovery", out["shape"], "unknown",
           "Absence of V/retest evidence is not positive evidence of a grinding recovery.",
           kind="presentation_semantics")

def failed_reclaim_probe(root):
    prices = [100.0] * 150 + [90.0, 96.0, 98.0, 100.0, 101.0, 102.0, 96.0, 94.0, 92.0]
    idx = pd.bdate_range(end="2026-09-08", periods=len(prices))
    frame = pd.DataFrame({"close": prices}, index=idx)
    env = dict(pd=pd, np=np, store=SimpleNamespace(read=lambda *args: frame),
               log=logging.getLogger("risk_integrity_probe"),
               _iso=lambda ts: str(pd.Timestamp(ts).date()) if ts is not None else None,
               _is_fresh=lambda ts: True,
               _absent_chip=lambda *args: {"fired": False, "error": str(args)})
    load(root, "engine/risk_radar_market_catalysts.py", ["_c12_fast_reclaim", "_morphology"], env)
    chip = env["_c12_fast_reclaim"]()
    out = env["_morphology"]([chip])
    last_below_ma = bool(frame.close.iloc[-1] < frame.close.rolling(20).mean().iloc[-1])
    record("v_shape_survives_post_reclaim_relapse", bool(chip.get("fired") and last_below_ma and out["shape"] == "v_shape"), False,
           "Historical fired remains true after renewed weakness. Keep that event, but do not infer current recovery health from it.", kind="presentation_semantics")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    root = args.source_root.resolve()
    for probe in (freshness_probe, composite_probe, null_snapshot_probe,
                  morphology_probe, failed_reclaim_probe):
        probe(root)
    expected_hashes = {
        "engine/risk_radar_intl.py": "1596e1da4794bf97d49f6f0ae42eaabff7226fa812fb0a96bfb0a6242faf7cd7",
        "engine/risk_radar_recovery.py": "321545a3cace15f20d23b564e1b43595ccd0804fab3de362eceb5a580695c593",
        "engine/risk_radar_market_catalysts.py": "28442483c418491f71f1e6c1fb11bbecd5cac3d5237662c361d8b44199ee28c5",
    }
    exact_source = SOURCE_HASHES == expected_hashes
    result = dict(source_pin=PIN, source_hashes=SOURCE_HASHES, exact_source=exact_source,
                  synthetic_only=True, production_mutations=0, probes=RESULTS,
                  all_baseline_mechanisms_reproduced=all(r["reproduced"] for r in RESULTS))
    print(json.dumps(result, indent=2, allow_nan=False))
    if not exact_source:
        raise SystemExit("Source changed: re-pin and review; do not transfer this baseline receipt.")
    if not result["all_baseline_mechanisms_reproduced"]:
        raise SystemExit("A baseline mechanism was not reproduced; inspect the actual result.")

if __name__ == "__main__":
    main()
