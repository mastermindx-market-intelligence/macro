#!/usr/bin/env python3
"""Fixed adaptive macro-state interaction experiment; no original-vintage claim."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from engine.industry_transition_research import CONTEXT_FEATURES, ConditionalModel, feature_panel, label_panel
from engine.industry_macro_research import SERIES, MACRO_STATES, EXPOSURES, MACRO_INTERACTIONS, add_macro_context
from scripts.research.industry_transition_discovery import load_inputs, month_mean, select, block_difference, probability_diagnostics

FOLDS = ((1973, 1982), (1983, 1992), (1993, 2002))
TRACKS = {"price_same_population": CONTEXT_FEATURES,
          "macro_additive": CONTEXT_FEATURES + MACRO_STATES + EXPOSURES,
          "macro_interactions": CONTEXT_FEATURES + MACRO_STATES + EXPOSURES + MACRO_INTERACTIONS}


def parse_macro_csv(raw: bytes, cutoff: str = "2002-12-31") -> tuple[pd.DataFrame, dict]:
    if pd.Timestamp(cutoff) > pd.Timestamp("2002-12-31"):
        raise ValueError("preserve this experiment's reserve boundary")
    contents = [raw]
    if raw[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            contents = [archive.read(name) for name in archive.namelist() if name.lower().endswith(".csv")]
    frames, hashes = [], []
    for item in contents:
        lines = item.decode("utf-8-sig").splitlines()
        if not lines:
            continue
        # Cut dates as strings before numeric data is parsed.
        selected = [line for line in lines[1:] if line.split(",", 1)[0] <= cutoff and len(line.split(",", 1)[0]) == 10]
        kept = lines[0] + "\n" + "\n".join(selected)
        frame = pd.read_csv(io.StringIO(kept), index_col=0, na_values=["."])
        frame.index = pd.to_datetime(frame.index).to_period("M")
        if not frame.index.is_unique:
            raise ValueError("expected monthly observations, not intramonth duplicates")
        frames.append(frame)
        hashes.append(hashlib.sha256(kept.encode()).hexdigest())
    result = pd.concat(frames, axis=1).sort_index()
    if not result.columns.is_unique or not set(SERIES).issubset(result):
        raise ValueError("missing or duplicate FRED series")
    result = result[list(SERIES)].apply(pd.to_numeric, errors="raise")
    return result, {"download_sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                    "parsed_sha256": hashes, "rows": len(result), "first": str(result.index.min()),
                    "last": str(result.index.max()), "series": list(SERIES),
                    "basis": "CURRENT_VINTAGE_RECONSTRUCTION_WITH_ASSUMED_TWO_MONTH_LAG"}


def load_macro() -> tuple[pd.DataFrame, dict]:
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    response = requests.get(url, params={"id": ",".join(SERIES)}, timeout=45)
    response.raise_for_status()
    frame, source = parse_macro_csv(response.content)
    source["url"] = response.url
    return frame, source


def run(output: Path) -> dict:
    r, market, sources = load_inputs("2002-12-31")
    macro, macro_source = load_macro()
    base = feature_panel(r, market)
    features = add_macro_context(base, r, market, macro)
    if features.empty:
        raise ValueError("no complete industry/macro history")
    checks = []
    for year in (1970, 1982, 2001):
        cut = features.loc[features.as_of.dt.year == year, "as_of"].max()
        f = base[base.as_of <= cut]
        prefix = add_macro_context(f, r.loc[:cut], market.loc[:cut], macro.loc[:cut.to_period("M")])
        expected = features[features.as_of <= cut].reset_index(drop=True)
        pd.testing.assert_frame_equal(prefix, expected, check_exact=False, atol=1e-11, rtol=1e-11)
        checks.append(str(cut.date()))
    labelled = label_panel(features, r, market)
    predictions = {key: [] for key in TRACKS}
    folds = []
    for first, last in FOLDS:
        start = pd.Timestamp(first, 1, 1)
        train = labelled[labelled.label_end < start].copy()
        test = labelled[(labelled.as_of.dt.year >= first) & (labelled.as_of.dt.year <= last)].copy()
        folds.append({"test_years": [first, last], "train_events": len(train),
                      "train_months": int(train.as_of.nunique()), "test_events": len(test),
                      "test_months": int(test.as_of.nunique()), "last_train_label": str(train.label_end.max().date())})
        for name, names in TRACKS.items():
            model = ConditionalModel(tuple(names)).fit(train, prediction_start=start)
            forecasts = model.predict(test).drop(columns=["state", "basis"])
            joined = test.merge(forecasts, on=["as_of", "industry"], validate="one_to_one")
            predictions[name].append(joined)
            print("MACRO_FIT", first, name, len(train), len(test), flush=True)
    predictions = {key: pd.concat(value, ignore_index=True) for key, value in predictions.items()}
    reference = predictions["price_same_population"]
    raw = reference.assign(momentum_score=reference.rel252 - reference.rel21)
    selections = {"raw_momentum": select(raw, "momentum_score")}
    selections.update({key: select(value, "expected_excess63") for key, value in predictions.items()})
    report = {"status": "ADAPTIVE_RECONSTRUCTED_MACRO_DISCOVERY_NOT_PIT_OR_TRADING_PROOF",
              "price_sources": sources, "macro_source": macro_source,
              "configured_additional_tracks": 3, "hyperparameter_search": False,
              "lag_months": 2, "exposure_window_months": 60, "exposure_ridge": 6,
              "feature_rows": len(features), "labelled_rows": len(labelled),
              "oos_events": len(reference), "oos_months": int(reference.as_of.nunique()),
              "prefix_checks": checks, "folds": folds,
              "selection": {key: month_mean(value) for key, value in selections.items()},
              "diagnostics": {key: probability_diagnostics(value) for key, value in predictions.items()},
              "comparisons": {}, "state_slices": {}, "money_state_coverage": {},
              "era_slices": {}, "financial_influence": False,
              "limitations": ["Revised macro values with a fixed assumed lag; not historical first-release observations.",
                              "Exposure coefficients are associations, not policy-shock causal effects.",
                              "The ex-post real-rate proxy is not a complete monetary-stance measure.",
                              "Same-month event means are not portfolio returns; intervals are exploratory and unadjusted.",
                              "Industry state snapshots are not proprietary dot events."]}
    for name in ("macro_additive", "macro_interactions"):
        report["comparisons"][name + "_minus_raw_momentum"] = block_difference(selections[name], selections["raw_momentum"])
        report["comparisons"][name + "_minus_price_same_population"] = block_difference(selections[name], selections["price_same_population"])
    report["comparisons"]["interactions_minus_macro_additive"] = block_difference(selections["macro_interactions"], selections["macro_additive"])
    for state in ("leading", "improving", "weakening", "lagging"):
        report["state_slices"][state] = {}
        for name, frame in predictions.items():
            sample = frame[frame.state == state].groupby("as_of").filter(lambda x: len(x) >= 5)
            report["state_slices"][state][name] = month_mean(select(sample, "expected_excess63"))
        sample = raw[raw.state == state].groupby("as_of").filter(lambda x: len(x) >= 5)
        report["state_slices"][state]["raw_momentum"] = month_mean(select(sample, "momentum_score"))
    dates = reference.drop_duplicates("as_of").sort_values("as_of").copy()
    dates["money_state"] = np.where(dates.policy_delta12 > 0, "rising", np.where(dates.policy_delta12 < 0, "falling", "flat"))
    dates["money_state"] += np.where(dates.real_short_proxy < 0, "_negative_real", "_nonnegative_real")
    # Each run of a state is a calendar spell, not an independent crisis.
    previous = dates.money_state.shift()
    for state, group in dates.groupby("money_state"):
        report["money_state_coverage"][state] = {"months": len(group),
            "calendar_spells": int(((dates.money_state == state) & (previous != state)).sum())}
    for first, last in FOLDS:
        report["era_slices"][str(first)] = {key: month_mean(value[(value.as_of.dt.year >= first) & (value.as_of.dt.year <= last)]) for key, value in selections.items()}
    output.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    path = output / "industry_macro_results.json"
    path.write_text(text)
    print("MACRO_RESULT", json.dumps({"selection": report["selection"], "comparisons": report["comparisons"],
              "money_state_coverage": report["money_state_coverage"], "sha256": hashlib.sha256(text.encode()).hexdigest()}), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
