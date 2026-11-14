#!/usr/bin/env python3
"""Execute the frozen industry-first experiment; never touch held confirmation.

Usage: python scripts/industry_transition_research.py --output /owned/path
Raw files and event predictions stay outside Git. Aggregate reports and an
explicitly historical research snapshot are safe to inspect as research outputs.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import sys
import zipfile

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from engine.industry_transition import (CLASSES, CONTEXT_FEATURES, Config, ResearchModel,
    forecast_record, make_events, make_features, selected, summarize, walk_forward)
from engine.industry_expectations import compose_with_k3e
from engine.prophet_lab.industry_transition_context import validate_snapshot, read_industry_context

CUTOFF = "2002-12-31"
URLS = {
    "industries": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/49_Industry_Portfolios_daily_CSV.zip",
    "factors": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_daily_CSV.zip",
}


def parse_archive(raw: bytes, cutoff: str = CUTOFF) -> tuple[pd.DataFrame, dict]:
    if cutoff > CUTOFF: raise ValueError("this experiment does not release reserved dates")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1: raise ValueError("ambiguous vendor archive")
        text = archive.read(names[0]).decode("utf-8-sig")
    lines = text.splitlines(); kept = []; header = None; started = False
    boundary = cutoff.replace("-", "")
    for i, line in enumerate(lines):
        first = line.split(",", 1)[0].strip()
        if re.fullmatch(r"\d{8}", first):
            if not started: header = lines[i - 1]; started = True
            # Compare date text BEFORE converting any return value.
            if first <= boundary: kept.append(line)
        elif started:
            break
    if not kept or header is None: raise ValueError("daily section absent")
    csv = header + "\n" + "\n".join(kept)
    frame = pd.read_csv(io.StringIO(csv), index_col=0)
    frame.columns = frame.columns.str.strip()
    frame.index = pd.to_datetime(frame.index.astype(str), format="%Y%m%d")
    frame = frame.replace([-99.99, -999.0], np.nan).astype(float) / 100
    if frame.index[-1] > pd.Timestamp(cutoff): raise AssertionError("cutoff leak")
    return frame, {"archive_sha256": sha256(raw).hexdigest(), "parsed_sha256": sha256(csv.encode()).hexdigest(),
                   "vendor_header": lines[0], "first": str(frame.index[0].date()),
                   "last": str(frame.index[-1].date()), "rows": len(frame)}


def load_data() -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, dict]:
    frames, sources = {}, {}
    for key, url in URLS.items():
        response = requests.get(url, timeout=(10, 30))
        response.raise_for_status()
        frames[key], sources[key] = parse_archive(response.content)
        sources[key]["url"] = url
    r, factors = frames["industries"], frames["factors"]
    if not r.index.equals(factors.index): raise ValueError("vendor calendars differ")
    market = factors["Mkt-RF"] + factors["RF"]
    return r, market, factors, sources


def paired_interval(a: pd.DataFrame, b: pd.DataFrame, metric: str, replicates: int = 1000) -> dict:
    aa, bb = a.groupby("decision_date")[metric].mean(), b.groupby("decision_date")[metric].mean()
    dates = aa.index.intersection(bb.index)
    d = (aa.loc[dates] - bb.loc[dates]).to_numpy(float)
    rng = np.random.default_rng(20261114); block = 12; n = len(d)
    if n < block: return {"difference": float(d.mean()) if n else None, "ci95": None, "months": n}
    starts = rng.integers(0, n - block + 1, size=(replicates, int(np.ceil(n / block))))
    idx = (starts[:, :, None] + np.arange(block)).reshape(replicates, -1)[:, :n]
    vals = d[idx].mean(axis=1)
    return {"difference": float(d.mean()), "ci95": np.quantile(vals, [.025, .975]).tolist(), "months": n}


def evaluate(predictions: pd.DataFrame, config: Config) -> dict:
    full, chosen, state, calibration, eras = {}, {}, {}, {}, {}
    selections = {}
    for name, p in predictions.groupby("model", sort=True):
        full[name] = summarize(p)
        state[name] = {s: summarize(g) for s, g in p.groupby("state")}
        eras[name] = {str(yr): summarize(g) for yr, g in p.groupby("fold")}
        if name != "base_rate":
            take = selected(p, config.selection_fraction); selections[name] = take
            chosen[name] = summarize(take)
            chosen[name]["coverage"] = len(take) / len(p)
        if name != "momentum126":
            bins = pd.cut(p.p_upside_first, [0, .2, .4, .6, .8, 1.], include_lowest=True)
            calibration[name] = [{"bin": str(k), "events": len(g), "months": int(g.decision_date.nunique()),
                                  "predicted": float(g.p_upside_first.mean()),
                                  "observed": float((g.outcome == 0).mean())}
                                 for k, g in p.groupby(bins, observed=True)]
    deltas = {}
    for comparator in ("price", "momentum126"):
        deltas["context_minus_" + comparator] = {
            metric: paired_interval(selections["context"], selections[comparator], metric)
            for metric in ("terminal_net", "excess_net", "bad_loss", "adverse_excursion")}
    costs = {}
    for name, p in selections.items():
        costs[name] = {str(bp): float(p.groupby("decision_date").terminal_gross.mean().mean() - bp / 10000)
                       for bp in (0, 20, 50)}
    return {"all_events": full, "top20_percent": chosen, "state_partitions_all_events": state,
            "folds_all_events": eras, "upside_calibration_event_weighted_bins": calibration,
            "top20_paired_intervals": deltas, "terminal_return_cost_sensitivity_bp": costs}


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args(); output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    config = Config()
    r, market, factors, source = load_data()
    print("INPUTS", json.dumps(source), flush=True)
    features = make_features(r, market, factors)
    # Actual prefix checks on data, independent of future labels.
    checks = []
    for date in ("1960-12-30", "1982-12-31", "2001-12-31"):
        stop = r.index[r.index <= date][-1]
        short = make_features(r.loc[:stop], market.loc[:stop], factors.loc[:stop])
        left = features[features.decision_date == stop].set_index("industry")[list(CONTEXT_FEATURES)]
        right = short[short.decision_date == stop].set_index("industry")[list(CONTEXT_FEATURES)]
        np.testing.assert_allclose(left.to_numpy(), right.to_numpy(), equal_nan=True, atol=1e-12)
        checks.append(str(stop.date()))
    events = make_events(r, market, features, config)
    print("EVENTS", len(events), int(events.decision_date.nunique()), flush=True)
    predictions, folds = walk_forward(events, config)
    print("FOLDS", len(folds), "PREDICTIONS", len(predictions), flush=True)
    report = {"schema": "prophet.industry_research_evaluation.v1",
              "status": "EXPLORATORY_RECONSTRUCTED_HISTORY_NOT_LIVE_VALIDATION",
              "config": asdict(config), "sources": source, "features": list(CONTEXT_FEATURES),
              "trial_count": 3, "fixed_comparator": "momentum126", "prefix_checks": checks,
              "event_count": len(events), "decision_months": int(events.decision_date.nunique()),
              "model_fold_receipts": folds, **evaluate(predictions, config),
              "limitations": ["Current-vintage reconstructed data; past eras have already been investigated.",
                "Intervals are exploratory, not multiplicity-adjusted or causal.",
                "Industry portfolios are not directly tradable; closing barriers are not intraday fills.",
                "Overlapping event means are not portfolio returns, Sharpe ratios or independent episodes.",
                "K3E expectation changes are not in this price/factor experiment without a historical input panel.",
                "No reserved post-2002 outcome was parsed; no stock timer or live trading validation."]}
    result_file = output / "RESULTS.json"
    result_file.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    predictions.to_csv(output / "LOCAL_PREDICTIONS_DO_NOT_COMMIT.csv", index=False)
    # Real historical artifact produced for the Prophet consumer, not a fixture.
    asof = r.index[-1]; cut = asof - pd.DateOffset(months=config.calibration_months)
    eligible = events[np.isfinite(events[list(CONTEXT_FEATURES)].to_numpy(float)).all(axis=1)]
    fit = eligible[eligible.label_end < cut]
    cal = eligible[(eligible.decision_date >= cut) & (eligible.label_end < asof)]
    model = ResearchModel(CONTEXT_FEATURES, config).fit(fit, cal, asof)
    latest = features[features.decision_date == asof]
    latest = latest[np.isfinite(latest[list(CONTEXT_FEATURES)].to_numpy(float)).all(axis=1)]
    rows = [compose_with_k3e(forecast_record(model, latest.iloc[[i]], source["industries"]["parsed_sha256"],
                            "RECONSTRUCTED_DISCOVERY")) for i in range(len(latest))]
    snapshot = {"schema": "prophet.industry_research_snapshot.v1", "as_of": asof.isoformat() + "+00:00",
                "generated_at": datetime.now(timezone.utc).isoformat(), "authority": "research_only",
                "financial_influence": False, "evidence_mode": "RECONSTRUCTED_DISCOVERY",
                "source_refs": [v["parsed_sha256"] for v in source.values()], "forecasts": rows}
    validate_snapshot(snapshot)
    snapshot_file = output / "historical_snapshot.json"
    snapshot_file.write_text(json.dumps(snapshot, indent=2, sort_keys=True, allow_nan=False) + "\n")
    proof = read_industry_context(snapshot_file)
    assert proof["state"] == "HISTORICAL_RESEARCH" and proof["live_signal"] is False
    print("RESULTS_SHA256", sha256(result_file.read_bytes()).hexdigest(), flush=True)
    print("CONSUMER", proof["state"], "industries", len(rows), "snapshot_sha256", proof["content_sha256"], flush=True)
    print("SUMMARY", json.dumps(report["top20_percent"]), flush=True)
    print("PAIRED", json.dumps(report["top20_paired_intervals"]), flush=True)


if __name__ == "__main__": main()
