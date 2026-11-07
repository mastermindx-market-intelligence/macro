#!/usr/bin/env python3
"""Offline reproduction of the pinned Prophet research audit. No network or trading."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd

BLOB = "b0ee089e86269854b699f4667b47dd10a469374c"
KEY = ["as_of", "lane", "ticker", "horizon"]
REQUIRED = set(KEY + ["rank_by", "tier_cascade", "news_burst", "entry_status", "ret", "excess_spy", "excess_sector", "sector"])


def verified_read(path: Path) -> pd.DataFrame:
    data = path.read_bytes()
    actual = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
    if actual != BLOB:
        raise ValueError(f"Input version mismatch: expected {BLOB}, got {actual}")
    return pd.read_parquet(path)


def stats(frame: pd.DataFrame) -> dict:
    result = {"n": len(frame), "issuers": int(frame.ticker.nunique()), "dates": int(frame.as_of.nunique())}
    for column in ["ret", "excess_spy", "excess_sector"]:
        values = pd.to_numeric(frame[column], errors="coerce").dropna()
        result[column] = {"observed": len(values), "positive": int(values.gt(0).sum()),
                          "mean": float(values.mean()) if len(values) else None}
    return result


def analyse(data: pd.DataFrame) -> dict:
    missing = REQUIRED - set(data.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if data.duplicated(KEY).any():
        raise ValueError("Duplicate economic observation keys; resolve before analysis")
    v = data[data.rank_by.eq("us_prophet_v3") & data.lane.eq("buy")].copy()
    out = {"status": "EXPLORATORY_NOT_A_FORECAST", "source_blob": BLOB,
           "cells": {}, "matched_controls": {}, "era_counts": {}}
    for horizon in (5, 10):
        h = v[v.horizon.eq(horizon)]
        for technical in (True, False):
            for news in (True, False):
                mask = h.tier_cascade.eq("T2").eq(technical) & h.news_burst.eq(news)
                out["cells"][f"H{horizon}_T2_{technical}_news_{news}"] = stats(h[mask])
        signal = h[h.tier_cascade.eq("T2") & h.news_burst.eq(True)].sort_values(["as_of", "ticker"])
        out["cells"][f"H{horizon}_first_per_issuer"] = stats(signal.drop_duplicates("ticker"))
        out["cells"][f"H{horizon}_action_open"] = stats(signal[signal.entry_status.isin(["buy_now", "partial"])])
        if horizon == 10:
            out["cells"]["H10_without_INTC"] = stats(signal[signal.ticker.ne("INTC")])
        for columns in (["as_of"], ["as_of", "sector"], ["as_of", "sector", "entry_status"]):
            differences = []
            for _, group in h[h.tier_cascade.eq("T2")].groupby(columns, dropna=False):
                treated = group[group.news_burst.eq(True)].excess_spy.dropna()
                controls = group[group.news_burst.eq(False)].excess_spy.dropna()
                if len(treated) and len(controls):
                    differences.extend((treated - controls.mean()).tolist())
            out["matched_controls"][f"H{horizon}_{','.join(columns)}"] = {
                "matched_signal_rows": len(differences),
                "mean_difference": sum(differences) / len(differences) if differences else None,
                "positive_differences": sum(value > 0 for value in differences)}
    for era, group in data[data.horizon.eq(5) & data.lane.eq("buy")].groupby("rank_by"):
        signature = group[group.tier_cascade.eq("T2") & group.news_burst.eq(True)]
        out["era_counts"][str(era)] = {"buy_rows": len(group), "news_nonnull": int(group.news_burst.notna().sum()),
            "news_true": int(group.news_burst.eq(True).sum()), "signature": stats(signature),
            "signature_issuers": sorted(signature.ticker.unique().tolist())}
    signal = v[v.tier_cascade.eq("T2") & v.news_burst.eq(True)]
    paired = signal[signal.horizon.eq(5)].merge(signal[signal.horizon.eq(10)], on=["as_of", "ticker"], suffixes=("_5", "_10"), validate="one_to_one")
    out["paired_horizons"] = {"n": len(paired), "h5_wins": int(paired.excess_spy_5.gt(0).sum()),
        "h10_wins": int(paired.excess_spy_10.gt(0).sum()),
        "h5_mean": float(paired.excess_spy_5.mean()) if len(paired) else None,
        "h10_mean": float(paired.excess_spy_10.mean()) if len(paired) else None}
    out["limits"] = ["No fitting, threshold search, causal or trading authority.",
        "First observation per issuer is a sensitivity analysis, not an approved episode definition.",
        "No-news False does not prove upstream coverage; source-vintage reconstruction is still required.",
        "Neither excess-return wins nor hypothetical entry bases establish profitable executable trades.",
        "All inspected observations are discovery data; no prospective holdout is claimed."]
    return out


def self_test() -> None:
    row = dict(as_of="2026-09-01", lane="buy", ticker="A", horizon=5, rank_by="us_prophet_v3", tier_cascade="T2", news_burst=True, entry_status="partial", ret=-.01, excess_spy=.01, excess_sector=None, sector="Technology")
    frame = pd.DataFrame([row, {**row, "ticker": "B", "news_burst": False, "ret": .02, "excess_spy": -.01}])
    a = analyse(frame)
    s = a["cells"]["H5_T2_True_news_True"]
    assert s["ret"]["positive"] == 0 and s["excess_spy"]["positive"] == 1
    assert s["excess_sector"]["observed"] == 0
    assert a["matched_controls"]["H5_as_of"]["matched_signal_rows"] == 1
    # A missing news observation must not silently become a measured negative.
    null = pd.DataFrame([{**row, "news_burst": None}])
    assert analyse(null)["cells"]["H5_T2_True_news_False"]["n"] == 0
    try:
        analyse(pd.concat([frame, frame], ignore_index=True))
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate guard failed")
    print("PASS: profit/excess separation; missing-data guard; matching; duplicate refusal")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.input is None or args.output is None:
        parser.error("Use --input frozen.parquet --output new_result.json, or --self-test")
    if args.output.exists():
        parser.error("Output already exists; choose a new file to preserve prior evidence")
    if args.output.resolve() == args.input.resolve():
        parser.error("Input cannot be overwritten")
    result = analyse(verified_read(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}; source hash verified; no production effects")


if __name__ == "__main__":
    main()
