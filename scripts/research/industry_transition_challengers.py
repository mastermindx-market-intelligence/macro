#!/usr/bin/env python3
"""Adaptive second experiment, specified before its own results.

Prior race is already seen. This is development, NOT independent confirmation.
Fixed HGBT settings; same pre-2003 inputs/folds. Compare both ranking replacement
and a risk overlay on the unchanged raw-momentum top quintile. Overlay retention
is fixed at 50% and 75%; equally selective momentum and low-vol controls included.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from engine.industry_transition_research import ConditionalModel, CONTEXT_FEATURES, feature_panel, label_panel
from engine.validation import brier_reliability, platt_fit
from scripts.research.industry_transition_discovery import FOLDS, load_inputs, month_mean, select, block_difference

TREE_SETTINGS = dict(max_leaf_nodes=7, max_depth=3, max_iter=100, learning_rate=.05,
                     min_samples_leaf=200, l2_regularization=10., early_stopping=False,
                     random_state=20261114)


def weights(frame):
    count = frame.as_of.value_counts()
    w = frame.as_of.map(1 / count).to_numpy(float, copy=True)
    return w / w.mean()


def calibrated(p, calibration):
    p = np.clip(np.asarray(p), 1e-4, 1 - 1e-4)
    z = calibration["a"] * np.log(p / (1 - p)) + calibration["b"]
    return 1 / (1 + np.exp(-np.clip(z, -700, 700)))


def run(output: Path):
    r, market, source = load_inputs("2002-12-31")
    features = feature_panel(r, market)
    labelled = label_panel(features, r, market)
    parts, fold_records = [], []
    for first, last in FOLDS:
        start, cal_start = pd.Timestamp(first, 1, 1), pd.Timestamp(first - 5, 1, 1)
        train = labelled[labelled.label_end < start].copy()
        fit = train[train.label_end < cal_start].copy()
        calibration = train[train.as_of >= cal_start].copy()
        test = labelled[(labelled.as_of.dt.year >= first) & (labelled.as_of.dt.year <= last)].copy()
        if min(fit.as_of.nunique(), calibration.as_of.nunique()) < 24:
            raise ValueError("insufficient chronological fit/calibration history")
        names = list(CONTEXT_FEATURES)
        # Return ranking sees all pre-test matured labels. Risk calibration uses
        # a strictly earlier fit segment and a separate final five-year segment.
        regression = HistGradientBoostingRegressor(**TREE_SETTINGS).fit(
            train[names], train.excess63, sample_weight=weights(train))
        tail = HistGradientBoostingClassifier(**TREE_SETTINGS).fit(
            fit[names], fit.bad10.astype(int), sample_weight=weights(fit))
        if list(tail.classes_) != [0, 1]:
            raise ValueError("missing risk class")
        cal = platt_fit(tail.predict_proba(calibration[names])[:, 1], calibration.bad10)
        if not cal:
            raise ValueError("calibration unavailable")
        prior = ConditionalModel(tuple(CONTEXT_FEATURES)).fit(train, prediction_start=start)
        old = prior.predict(test)
        test["tree_expected_excess"] = regression.predict(test[names])
        test["tree_tail_raw"] = tail.predict_proba(test[names])[:, 1]
        test["tree_tail_calibrated"] = calibrated(test.tree_tail_raw, cal)
        test["linear_tail"] = old.p_bad10.to_numpy()
        test["momentum_score"] = test.rel252 - test.rel21
        test["negative_volatility"] = -test.sigma63
        test["negative_tree_tail"] = -test.tree_tail_calibrated
        test["negative_linear_tail"] = -test.linear_tail
        parts.append(test)
        fold_records.append({"test": [first, last], "return_train_rows": len(train),
                             "risk_fit_rows": len(fit), "risk_calibration_rows": len(calibration),
                             "risk_fit_last_label": str(fit.label_end.max().date()),
                             "calibration_first_decision": str(calibration.as_of.min().date()),
                             "calibration_last_label": str(calibration.label_end.max().date()),
                             "first_test_decision": str(test.as_of.min().date()), "platt": cal})
        print("CHALLENGER_FIT", first, len(fit), len(calibration), len(test), flush=True)
    oos = pd.concat(parts, ignore_index=True)
    primary = select(oos, "momentum_score")
    tree_selected = select(oos, "tree_expected_excess")
    report = {"status": "ADAPTIVE_HISTORICAL_DISCOVERY_NO_PROMOTION", "source": source,
              "tree_settings": TREE_SETTINGS, "folds": fold_records,
              "oos_events": len(oos), "oos_months": int(oos.as_of.nunique()),
              "prior_model_tracks_seen": 3, "new_model_families": 1,
              "overlay_retention_variants": [.5, .75], "hyperparameter_search": False,
              "full_selection": {"raw_momentum": month_mean(primary), "tree": month_mean(tree_selected)},
              "tree_minus_momentum": block_difference(tree_selected, primary),
              "tail_diagnostics": {"raw_tree": brier_reliability(oos.tree_tail_raw, oos.bad10),
                                   "chronologically_calibrated_tree": brier_reliability(oos.tree_tail_calibrated, oos.bad10),
                                   "linear": brier_reliability(oos.linear_tail, oos.bad10)},
              "overlays": {}, "financial_influence": False,
              "limitations": ["Adaptive after first-race outcomes; all intervals exploratory and unadjusted.",
                              "Calibration is a past-fitted transformation, not proof of future calibration.",
                              "Risk overlays shrink coverage; compare only with equally selective controls.",
                              "Event averages are not implementable portfolio returns; no ranking authority changes."]}
    for fraction in (.5, .75):
        policies = {"stronger_momentum": select(primary, "momentum_score", fraction),
                    "lower_volatility": select(primary, "negative_volatility", fraction),
                    "linear_risk": select(primary, "negative_linear_tail", fraction),
                    "tree_risk": select(primary, "negative_tree_tail", fraction)}
        item = {"coverage": fraction, "policies": {key: month_mean(value) for key, value in policies.items()},
                "tree_minus_low_vol": block_difference(policies["tree_risk"], policies["lower_volatility"]),
                "tree_minus_stronger_momentum": block_difference(policies["tree_risk"], policies["stronger_momentum"]),
                "linear_minus_low_vol": block_difference(policies["linear_risk"], policies["lower_volatility"]),
                "rejected_opportunities": {}}
        for name, frame in policies.items():
            keys = pd.MultiIndex.from_frame(frame[["as_of", "industry"]])
            rejected = primary[~pd.MultiIndex.from_frame(primary[["as_of", "industry"]]).isin(keys)]
            item["rejected_opportunities"][name] = month_mean(rejected)
        report["overlays"][str(fraction)] = item
    output.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(report, indent=2, allow_nan=False) + "\n"
    target = output / "industry_challengers_results.json"
    target.write_text(raw)
    print("CHALLENGER_RESULT", json.dumps({"selection": report["full_selection"],
            "tail_diagnostics": report["tail_diagnostics"],
            "overlays": {k: v["policies"] for k, v in report["overlays"].items()},
            "sha256": hashlib.sha256(raw.encode()).hexdigest()}), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
