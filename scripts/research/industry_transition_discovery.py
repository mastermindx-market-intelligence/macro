#!/usr/bin/env python3
"""Execute the fixed historical industry experiment; writes aggregate research only.

Raw inputs remain in memory. Downloaded archives may contain later dates; strings
past --cutoff are excluded before numeric parsing. No reserved-period label read.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import zipfile

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from engine.industry_transition_research import (
    ConditionalModel, MODEL_FEATURES, feature_panel, label_panel,
)

URLS = {
    "industry": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/49_Industry_Portfolios_daily_CSV.zip",
    "market": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_daily_CSV.zip",
}
METRICS = ("net63", "excess63", "win", "bad10", "mae63", "upside_first", "downside_first", "unresolved")
FOLDS = ((1963, 1972), (1973, 1982), (1983, 1992), (1993, 2002))


def parse_french(raw: bytes, *, cutoff: str, kind: str) -> tuple[pd.DataFrame, dict]:
    cutoff_key = pd.Timestamp(cutoff).strftime("%Y%m%d")
    if pd.Timestamp(cutoff) > pd.Timestamp("2002-12-31"):
        raise ValueError("this experiment preserves post-2002 reserves")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        if len(names) != 1:
            raise ValueError("unexpected archive members")
        text = archive.read(names[0]).decode("utf-8-sig")
    lines = text.splitlines()
    if kind == "industry":
        start = next(k for k, line in enumerate(lines) if "Average Value Weighted Returns -- Daily" in line) + 1
    elif kind == "market":
        start = next(k for k, line in enumerate(lines) if line.strip().startswith(",Mkt-RF"))
    else:
        raise ValueError("unknown dataset")
    while not lines[start].strip():
        start += 1
    header = lines[start]
    selected = []
    for line in lines[start + 1:]:
        key = line.split(",", 1)[0].strip()
        if not (len(key) == 8 and key.isdigit()):
            if selected:
                break
            continue
        if key <= cutoff_key:
            selected.append(line)
    kept = header + "\n" + "\n".join(selected)
    frame = pd.read_csv(io.StringIO(kept), index_col=0)
    frame.columns = frame.columns.str.strip()
    frame.index = pd.to_datetime(frame.index.astype(str), format="%Y%m%d")
    frame = frame.replace({-99.99: np.nan, -999.0: np.nan}) / 100
    return frame, {"archive_sha256": hashlib.sha256(raw).hexdigest(), "archive_bytes": len(raw),
                   "parsed_sha256": hashlib.sha256(kept.encode()).hexdigest(),
                   "first": str(frame.index.min().date()), "last": str(frame.index.max().date()),
                   "rows": len(frame), "vintage": lines[0], "basis": "reconstructed_price_history"}


def load_inputs(cutoff: str) -> tuple[pd.DataFrame, pd.Series, dict]:
    data, sources = {}, {}
    for key, url in URLS.items():
        response = requests.get(url, timeout=40)
        response.raise_for_status()
        data[key], sources[key] = parse_french(response.content, cutoff=cutoff, kind=key)
        sources[key]["url"] = url
    if not data["industry"].index.equals(data["market"].index):
        raise ValueError("source session grids disagree")
    return data["industry"], data["market"]["Mkt-RF"] + data["market"]["RF"], sources


def month_mean(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {"events": 0, "months": 0, "equal_month_mean": None}
    grouped = frame.groupby("as_of")[list(METRICS)].mean()
    return {"events": len(frame), "months": len(grouped),
            "equal_month_mean": {key: float(value) for key, value in grouped.mean().items()}}


def select(frame: pd.DataFrame, score: str, fraction: float = .2) -> pd.DataFrame:
    rows = []
    for _, group in frame.groupby("as_of", sort=True):
        k = max(1, int(math.ceil(fraction * len(group))))
        rows.append(group.sort_values([score, "industry"], ascending=[False, True]).head(k))
    return pd.concat(rows, ignore_index=True) if rows else frame.iloc[:0]


def block_difference(a: pd.DataFrame, b: pd.DataFrame, *, reps: int = 2000) -> dict:
    aa, bb = a.groupby("as_of")[list(METRICS)].mean(), b.groupby("as_of")[list(METRICS)].mean()
    shared = aa.index.intersection(bb.index)
    if len(shared) < 24:
        return {"status": "INSUFFICIENT_SHARED_MONTHS", "months": len(shared)}
    delta = (aa.loc[shared] - bb.loc[shared])
    calendar = pd.period_range(shared.min().to_period("M"), shared.max().to_period("M"), freq="M")
    delta.index = delta.index.to_period("M")
    values = delta.reindex(calendar).to_numpy()
    rng = np.random.default_rng(20261114)
    boot = np.empty((reps, len(METRICS)))
    for k in range(reps):
        starts = rng.integers(0, max(1, len(values) - 12 + 1), math.ceil(len(values) / 12))
        sample = np.concatenate([np.arange(s, min(s + 12, len(values))) for s in starts])[:len(values)]
        boot[k] = np.nanmean(values[sample], axis=0)
    lo, hi = np.nanquantile(boot, [.025, .975], axis=0)
    return {"status": "EXPLORATORY_UNADJUSTED", "months": len(shared),
            "difference": {name: {"estimate": float(delta[name].mean()), "ci95": [float(lo[j]), float(hi[j])]}
                           for j, name in enumerate(METRICS)}}


def probability_diagnostics(frame: pd.DataFrame) -> dict:
    names = ["p_upside_first", "p_downside_first", "p_unresolved"]
    probabilities = frame[names].to_numpy()
    y = frame.outcome.to_numpy(dtype=int)
    onehot = np.eye(3)[y]
    work = frame[["as_of"]].copy()
    work["brier3"] = np.square(probabilities - onehot).sum(axis=1)
    work["logloss"] = -np.log(np.maximum(1e-12, probabilities[np.arange(len(y)), y]))
    work["tail_brier"] = np.square(frame.p_bad10 - frame.bad10)
    bins = []
    p = frame.p_upside_first
    for low in np.arange(0, 1, .1):
        group = frame[(p >= low) & (p < low + .1)]
        if len(group):
            bins.append({"range": [round(float(low), 1), round(float(low + .1), 1)],
                         "events": len(group), "months": int(group.as_of.nunique()),
                         "mean_predicted": float(group.p_upside_first.mean()),
                         "observed": float(group.upside_first.mean())})
    return {"equal_month_scores": work.groupby("as_of").mean().mean().to_dict(),
            "upside_reliability_bins_event_weighted": bins,
            "extrapolation_row_share": float((frame.extrapolation_features > 0).mean()),
            "status": "RELIABILITY_MEASURED_NOT_PROMOTED"}


def run(cutoff: str, output: Path) -> dict:
    r, market, sources = load_inputs(cutoff)
    features = feature_panel(r, market)
    labelled = label_panel(features, r, market)
    if labelled.duplicated(["as_of", "industry"]).any():
        raise AssertionError("duplicate industry decisions")
    # Causal prefix check on actual data, before fitting any outcome model.
    checks = []
    for year in (1950, 1982, 2001):
        chosen = features.loc[features.as_of.dt.year == year, "as_of"].max()
        prefix = feature_panel(r.loc[:chosen], market.loc[:chosen], decision_dates=pd.DatetimeIndex([chosen]))
        original = features.loc[features.as_of == chosen].reset_index(drop=True)
        pd.testing.assert_frame_equal(prefix, original, check_exact=False, atol=1e-12, rtol=1e-12)
        checks.append(str(chosen.date()))
    predictions = {name: [] for name in MODEL_FEATURES}
    fold_metadata, models = [], {}
    for first, last in FOLDS:
        test_start = pd.Timestamp(first, 1, 1)
        train = labelled[pd.to_datetime(labelled.label_end) < test_start].copy()
        test = labelled[(labelled.as_of.dt.year >= first) & (labelled.as_of.dt.year <= last)].copy()
        if test.empty:
            continue
        meta = {"test_years": [first, last], "train_rows": len(train),
                "train_months": int(train.as_of.nunique()), "test_rows": len(test),
                "test_months": int(test.as_of.nunique()), "last_train_label": str(train.label_end.max().date()),
                "first_test_decision": str(test.as_of.min().date())}
        for name, names in MODEL_FEATURES.items():
            fitted = ConditionalModel(tuple(names)).fit(train, prediction_start=test_start)
            pred = fitted.predict(test)
            joined = test.merge(pred.drop(columns=["state", "basis"]), on=["as_of", "industry"], validate="one_to_one")
            joined["fold"] = first
            predictions[name].append(joined)
            models[name] = fitted.to_dict()
            print("FIT", first, name, len(train), len(test), flush=True)
        fold_metadata.append(meta)
    outputs = {key: pd.concat(value, ignore_index=True) for key, value in predictions.items()}
    reference = outputs["momentum_information"]
    raw_momentum = reference.assign(momentum_score=reference.rel252 - reference.rel21)
    selections = {"raw_momentum": select(raw_momentum, "momentum_score")}
    selections.update({key: select(value, "expected_excess63") for key, value in outputs.items()})
    result = {"status": "RECONSTRUCTED_HISTORICAL_DISCOVERY_NOT_TRADING_VALIDATION",
              "source": sources, "cutoff": cutoff, "features": len(features), "labelled": len(labelled),
              "excluded_forward": len(features) - len(labelled), "basis": "reconstructed_price_history",
              "protocol": "IMPLEMENTATION_PLAN.md", "configured_model_tracks": 3, "model_fits": len(fold_metadata) * 3,
              "inference": "12-calendar-month moving blocks; 2000 replicates; exploratory unadjusted intervals",
              "feature_prefix_checks": checks, "folds": fold_metadata,
              "all_oos": month_mean(reference),
              "top_quintile": {key: month_mean(value) for key, value in selections.items()},
              "diagnostics": {key: probability_diagnostics(value) for key, value in outputs.items()},
              "comparisons": {}, "state_slices": {}, "era_slices": {},
              "financial_influence": False,
              "limitations": ["Current-vintage industry indices, not original vintages or tradable ETF fills.",
                              "Price-only historical fit; K3E context is composed separately, not fabricated backward.",
                              "Overlapping 63-session event results are not portfolio returns or Sharpe ratios.",
                              "Closing barriers do not establish intraday stop fills; all model probabilities are research estimates."]}
    for name in ("additive_context", "conditional_interactions"):
        result["comparisons"][name + "_minus_raw_momentum"] = block_difference(selections[name], selections["raw_momentum"])
    result["comparisons"]["interactions_minus_additive"] = block_difference(selections["conditional_interactions"], selections["additive_context"])
    for state in ("leading", "weakening", "improving", "lagging"):
        result["state_slices"][state] = {}
        for name, frame in outputs.items():
            within = frame[frame.state == state]
            within = within.groupby("as_of").filter(lambda x: len(x) >= 5)
            result["state_slices"][state][name] = month_mean(select(within, "expected_excess63"))
        raw = raw_momentum[raw_momentum.state == state].groupby("as_of").filter(lambda x: len(x) >= 5)
        result["state_slices"][state]["raw_momentum"] = month_mean(select(raw, "momentum_score"))
    for first, last in FOLDS:
        result["era_slices"][str(first)] = {key: month_mean(value[(value.as_of.dt.year >= first) & (value.as_of.dt.year <= last)])
                                          for key, value in selections.items()}
    output.mkdir(parents=True, exist_ok=True)
    (output / "industry_discovery_results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (output / "industry_research_models.json").write_text(json.dumps(models, indent=2, allow_nan=False) + "\n")
    print("RESULT", json.dumps({"events": len(reference), "months": int(reference.as_of.nunique()),
                                "top_quintile": result["top_quintile"], "comparisons": result["comparisons"]}), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cutoff", default="2002-12-31")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.cutoff, args.output)
