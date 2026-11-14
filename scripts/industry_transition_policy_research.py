#!/usr/bin/env python3
"""Evaluate the fixed adaptive policies on existing chronological predictions."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from engine.industry_transition import summarize
from engine.industry_transition_policy import (
    POLICIES, calendar_paired_interval, combine_predictions, momentum_protected, reversal_half,
)

ORIGINAL_RESULT_SHA = "72eea568180075f75276af078a831af51331be8d69853ea8188a0e56468d5f92"
METRICS = ("terminal_net", "excess_net", "bad_loss", "adverse_excursion")


def descriptive(frame):
    result = summarize(frame)
    return {k: result[k] for k in ("events", "months", "win", "bad_loss", "terminal_net", "excess_net",
                                    "adverse_excursion", "upside_first", "downside_first", "timeout") if k in result}


def comparison(a, b):
    return {metric: calendar_paired_interval(a, b, metric) for metric in METRICS}


def evaluate_policies(predictions):
    joined = combine_predictions(predictions)
    all_policies = {p: momentum_protected(joined, p) for p in POLICIES}
    counts = all_policies["momentum"].groupby("decision_date").size()
    for p, frame in all_policies.items():
        pd.testing.assert_series_equal(frame.groupby("decision_date").size(), counts)
    results = {p: descriptive(f) | {"coverage": len(f) / len(joined)} for p, f in all_policies.items()}
    pairs = {"context_risk_minus_momentum": comparison(all_policies["context_risk"], all_policies["momentum"]),
             "context_risk_minus_price_risk": comparison(all_policies["context_risk"], all_policies["price_risk"]),
             "context_risk_minus_low_volatility": comparison(all_policies["context_risk"], all_policies["low_volatility"]),
             "expected_excess_minus_momentum": comparison(all_policies["expected_excess"], all_policies["momentum"])}
    composition = {p: {str(s): int(n) for s, n in f.groupby("state").size().items()} for p, f in all_policies.items()}
    folds = {p: {str(y): descriptive(g) for y, g in f.groupby("fold")} for p, f in all_policies.items()}
    reversal_policies = {p: reversal_half(joined, p) for p in
                        ("momentum_half", "context_risk_half", "price_risk_half", "expected_excess_half")}
    dates = reversal_policies["momentum_half"].decision_date.unique()
    reversal_all = joined[(joined.state == "reversal_attempt") & joined.decision_date.isin(dates)]
    rc = reversal_policies["momentum_half"].groupby("decision_date").size()
    for frame in reversal_policies.values():
        pd.testing.assert_series_equal(frame.groupby("decision_date").size(), rc)
    reversal = {"all_candidates": descriptive(reversal_all),
                "policies": {p: descriptive(f) | {"coverage": len(f) / len(reversal_all)} for p, f in reversal_policies.items()},
                "paired_against_momentum_half": {p: comparison(f, reversal_policies["momentum_half"])
                                                for p, f in reversal_policies.items() if p != "momentum_half"},
                "coverage_warning": "All-candidates comparator has different coverage; half policies have identical coverage."}
    return {"schema": "prophet.industry_adaptive_policy_evaluation.v1",
            "status": "ADAPTIVE_EXPLORATORY_NOT_CONFIRMATION", "new_models_fit": 0,
            "fixed_full_universe_policies": 5, "fixed_reversal_half_policies": 4,
            "full_universe_policy_results": results, "paired_comparisons": pairs,
            "state_composition_counts": composition, "fold_results": folds,
            "reversal_secondary": reversal,
            "limitations": ["The same historical period was previously examined; these are adaptive hypotheses.",
                            "Prediction rows are complete-case outcome observations, not a prospective tradable universe.",
                            "Equal-month event means with overlapping horizons are not portfolio returns.",
                            "Close-based barriers do not model intraday stops or gap execution.",
                            "No date later than2002 is used; no K3E fundamental payoff is tested here.",
                            "All intervals are descriptive and unadjusted for multiple comparisons."]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists(): raise FileExistsError("preserve prior result; use an explicit new revision")
    original = args.source_dir / "RESULTS.json"
    if sha256(original.read_bytes()).hexdigest() != ORIGINAL_RESULT_SHA:
        raise ValueError("original experiment binding mismatch")
    path = args.source_dir / "LOCAL_PREDICTIONS_DO_NOT_COMMIT.csv"
    raw = path.read_bytes()
    predictions = pd.read_csv(path, parse_dates=["decision_date", "entry_date", "label_end"])
    if predictions.label_end.max() > pd.Timestamp("2002-12-31"):
        raise ValueError("reserved-date outcome fence")
    if len(predictions) != 119444: raise ValueError("unexpected original prediction population")
    result = evaluate_policies(predictions)
    result["source_predictions_sha256"] = sha256(raw).hexdigest()
    result["original_results_sha256"] = ORIGINAL_RESULT_SHA
    result["code_sha256"] = sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print("RESULT_SHA256", sha256(args.output.read_bytes()).hexdigest())
    print("POLICIES", json.dumps(result["full_universe_policy_results"]))
    print("PAIRED", json.dumps(result["paired_comparisons"]))
    print("REVERSAL", json.dumps(result["reversal_secondary"]))


if __name__ == "__main__": main()
