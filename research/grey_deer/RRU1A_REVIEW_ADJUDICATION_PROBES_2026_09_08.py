"""Synthetic mathematical adjudication; no market data or prediction outcomes.
Checks the independent review's claims using the actual rolling-percentile function.
This is neither production implementation nor an independent rerun of that review.
"""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from engine.indicators import pct_rank_window


def main():
    rows = []
    rng = np.random.default_rng(20260908)
    values = pd.DataFrame(rng.uniform(0.05, 0.95, (1000, 4)))
    mask = pd.DataFrame(rng.uniform(size=values.shape) > 0.25)
    mask.iloc[:, 0] = True  # Positive denominator; no index-set change.
    observed = values.where(mask)
    den = observed.notna().sum(axis=1)
    old_raw = observed.fillna(0.5).sum(axis=1) / den
    new_raw = observed.fillna(0.0).sum(axis=1) / den
    expected_bias = 0.5 * (4 - den) / den
    np.testing.assert_allclose(old_raw - new_raw, expected_bias, atol=1e-12)
    rows.append({"claim": "raw_missingness_bias", "passed": True,
                 "meaning": "Old minus corrected equals 0.5 times missing/available group weight."})
    old_rank = pct_rank_window(old_raw, 504)
    new_rank = pct_rank_window(new_raw, 504)
    complete = observed.notna().all(axis=1) & old_rank.notna() & new_rank.notna()
    assert complete.any()
    assert (new_rank[complete] >= old_rank[complete] - 1e-12).all()
    rows.append({"claim": "complete_current_row_rank_cannot_decrease",
                 "passed": True, "tested_rows": int(complete.sum()),
                 "strict_increases": int((new_rank[complete] > old_rank[complete] + 1e-12).sum())})
    scaled = pct_rank_window(new_raw * 2.0, 504)
    pd.testing.assert_series_equal(new_rank, scaled, check_names=False)
    rows.append({"claim": "global_positive_rescale_is_rank_invariant", "passed": True,
                 "meaning": "A doubling mutant is not a valid discriminator for rank-level output."})
    quiet_available = (0.1 + 0.9) / 2.0
    assert 0.1 < quiet_available < 0.9
    rows.append({"claim": "missingness_can_raise_or_lower_vs_unobserved_full_blend",
                 "passed": True, "full_blend": quiet_available,
                 "only_low_leg": 0.1, "only_high_leg": 0.9,
                 "meaning": "Missing evidence is not necessarily quiet or necessarily loud versus truth."})
    x = np.linspace(-1.0, 1.0, 1001)
    full = (x + 10.0 * x) / 2.0
    ratio = float(np.var(x) / np.var(full))
    assert ratio < 1.0
    rows.append({"claim": "fewer_legs_need_not_strictly_increase_variance",
                 "passed": True, "partial_to_full_variance": ratio,
                 "meaning": "Heterogeneous correlated legs refute the review's universal variance claim."})
    tuner_path = ROOT / "engine/risk_radar_intl_tune.py"
    tuner = ast.parse(tuner_path.read_text())
    fn = next(n for n in tuner.body if isinstance(n, ast.FunctionDef) and n.name == "tune")
    calls = sorted({ast.unparse(n.func) for n in ast.walk(fn) if isinstance(n, ast.Call)})
    assert "A.realized_odds" in calls and "A._read" in calls
    assert not any("composite_series" in call for call in calls)
    rows.append({"claim": "tuner_reads_graded_history_not_constructor", "passed": True,
                 "meaning": "Review F5 conflates the offline calibration script with the online tuner.",
                 "calls": calls})
    print(json.dumps({"kind": "synthetic_review_adjudication_not_market_validation",
        "no_market_data_reads": True, "no_production_source_writes": True,
        "source_hashes": {
            "engine/indicators.py": hashlib.sha256((ROOT / "engine/indicators.py").read_bytes()).hexdigest(),
            "engine/risk_radar_intl_tune.py": hashlib.sha256(tuner_path.read_bytes()).hexdigest()},
        "checks": rows}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
