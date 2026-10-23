"""Offline, aggregate-only audit of existing app observations; never a ranker.

The incumbent altdata_models function remains the sole legacy rule owner.
This tool reads frozen inputs, measures losses and refuses false comparisons.
It neither collects data nor writes product artifacts, graphs, or outcome ledgers.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import inspect
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
from unittest.mock import patch

import numpy as np
import pandas as pd

REQUIRED = {"Ticker", "App", "Publisher", "Time", "Count", "Rating", "_first_seen"}
KEY = ["_ticker", "_app", "_publisher", "_date"]


def _legacy(frame: pd.DataFrame, display_limit: int) -> dict:
    from engine import altdata_models
    function = altdata_models.app_ratings_momentum
    fingerprint = hashlib.sha256(inspect.getsource(function).encode()).hexdigest()
    if frame.empty:
        rows = []
    else:
        try:
            with patch.object(altdata_models, "_read", return_value=frame.copy()):
                rows = function(top=max(1, len(frame)))
        except (ValueError, TypeError, OverflowError, KeyError) as error:
            return {"state": "BASELINE_ERROR", "error_type": type(error).__name__,
                    "function_sha256": fingerprint}
    displayed = rows[:display_limit]
    strong = sum(r.get("lean") == "strong" for r in rows)
    visible_strong = sum(r.get("lean") == "strong" for r in displayed)
    return {"state": "REPRODUCED", "function_sha256": fingerprint,
            "eligible_ticker_keys": len(rows), "display_limit": display_limit,
            "display_count": len(displayed), "strong_all": strong,
            "strong_displayed": visible_strong,
            "strong_hidden_by_cap": strong - visible_strong}


def audit_frame(frame: pd.DataFrame, *, observed_by: str,
                display_limit: int = 15) -> dict:
    """Return aggregate research diagnostics at an explicit knowledge cutoff."""
    if isinstance(display_limit, bool) or not isinstance(display_limit, int) or display_limit < 1:
        raise ValueError("display_limit must be a positive integer")
    cutoff = pd.Timestamp(observed_by)
    if pd.isna(cutoff) or cutoff.tzinfo is None:
        raise ValueError("observed_by requires an explicit timezone")
    cutoff = cutoff.tz_convert("UTC")
    if missing := REQUIRED - set(frame.columns):
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
    clock_text = frame["_first_seen"].astype("string")
    explicit_clock = clock_text.str.contains(
        r"[T ]\d{2}:\d{2}.*(?:Z|[+-]\d{2}:\d{2})$", na=False)
    seen = pd.to_datetime(clock_text.where(explicit_clock), utc=True,
                          errors="coerce", format="mixed")
    dates = pd.to_datetime(frame["Time"].astype("string"), utc=True,
                           errors="coerce", format="mixed").dt.normalize()
    known = seen.notna() & (seen <= cutoff)
    temporal = dates.notna() & (dates <= cutoff.normalize())
    available = frame.loc[known & temporal].copy()
    available["_date"] = dates.loc[available.index]
    report = {
        "schema": "intelligence_network.demand_audit.v1",
        "use": "internal_research_only", "state": "OBSERVATIONS_AVAILABLE",
        "identity_basis": "provider ticker/app/publisher labels; not resolved issuer/app IDs",
        "availability": {"observed_by": cutoff.isoformat(), "input_rows": len(frame),
            "excluded_unknown_clock": int(seen.isna().sum()),
            "excluded_after_cutoff": int((seen.notna() & (seen > cutoff)).sum()),
            "excluded_bad_or_future_snapshot": int((known & ~temporal).sum()),
            "available_rows": len(available)},
        "snapshot_dates": {"latest": None, "prior": None},
        "legacy": _legacy(available, display_limit), "quality": {}, "comparisons": {},
        "limitations": ["Not a source-health or commercial-rights attestation",
                        "Review counters are not users, downloads, sales, or stock returns",
                        "No scoring, ranking, sizing, or trade authority"]}
    if available.empty:
        report["state"] = "NO_AVAILABLE_OBSERVATIONS"
        return report
    for source, target in [("Ticker", "_ticker"), ("App", "_app"),
                           ("Publisher", "_publisher")]:
        available[target] = available[source].astype("string").str.strip().fillna("")
    for source, target in [("Count", "_count"), ("Rating", "_rating")]:
        text = available[source].astype("string").str.replace(",", "", regex=False)
        available[target] = pd.to_numeric(text, errors="coerce").astype(float)
    count, rating = available["_count"], available["_rating"]
    valid_measure = (np.isfinite(count) & (count >= 0) & (count % 1 == 0)
                     & np.isfinite(rating) & rating.between(0, 5))
    valid_identity = available[KEY[:3]].ne("").all(axis=1)
    values = ["_count", "_rating"]
    duplicate = available.duplicated(KEY + values)
    variation = available.groupby(KEY, dropna=False)[values].nunique(dropna=False)
    conflicts = variation.gt(1).any(axis=1)
    conflict_keys = set(variation.index[conflicts])
    conflict_rows = pd.Series([tuple(v) in conflict_keys for v in
                              available[KEY].itertuples(index=False, name=None)],
                             index=available.index)
    bad = ~valid_measure | ~valid_identity | conflict_rows
    report["quality"] = {"duplicate_rows": int(duplicate.sum()),
        "conflicting_snapshot_keys": int(conflicts.sum()),
        "invalid_measurement_rows": int((~valid_measure).sum()),
        "missing_identity_rows": int((~valid_identity).sum()),
        "unrated_rows": int((rating == 0).sum())}
    ordered_dates = sorted(available["_date"].unique())
    latest = ordered_dates[-1]
    previous = ordered_dates[-2] if len(ordered_dates) > 1 else None
    report["snapshot_dates"] = {"latest": latest.date().isoformat(),
        "prior": previous.date().isoformat() if previous is not None else None}
    paired_dates = [latest] if previous is None else [previous, latest]
    paired = available[available["_date"].isin(paired_dates)]
    blocked = set(available.loc[bad & available["_date"].isin(paired_dates), "_ticker"])
    clean = available.loc[~bad & ~duplicate]
    states = Counter()
    for ticker in sorted(set(paired["_ticker"]) - {""}):
        if ticker in blocked:
            states["INVALID_OR_CONFLICTING_INPUT"] += 1
            continue
        if previous is None:
            states["NO_PRIOR_SNAPSHOT"] += 1
            continue
        company = clean[clean["_ticker"] == ticker]
        current = company[company["_date"] == latest].set_index(KEY[1:3])["_count"]
        prior = company[company["_date"] == previous].set_index(KEY[1:3])["_count"]
        if current.empty:
            state = "PRIOR_ONLY"
        elif prior.empty:
            state = "CURRENT_ONLY"
        elif set(current.index) != set(prior.index):
            state = "COHORT_CHANGED"
        else:
            change = current - prior.reindex(current.index)
            state = ("COUNTER_DECREASE" if (change < 0).any() else
                     "COMPARABLE_INCREASE" if (change > 0).any() else
                     "COMPARABLE_UNCHANGED")
        states[state] += 1
    report["comparisons"] = dict(sorted(states.items()))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git-repo", type=Path, required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--dataset", default="data/quiver/appratings.parquet")
    parser.add_argument("--observed-by", required=True)
    parser.add_argument("--display-limit", type=int, default=15)
    args = parser.parse_args(argv)
    dataset = PurePosixPath(args.dataset)
    if dataset.is_absolute() or ".." in dataset.parts or ":" in args.dataset:
        parser.error("dataset must be a repository-relative path")
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

    def git(*values: str) -> bytes:
        return subprocess.check_output(["git", "-C", str(args.git_repo), *values],
                                       stderr=subprocess.PIPE, timeout=60)
    try:
        commit = git("rev-parse", "--verify", "--end-of-options",
                     args.source_ref + "^{commit}").decode().strip()
        blob = git("rev-parse", f"{commit}:{dataset}").decode().strip()
        raw = git("cat-file", "blob", blob)
        report = audit_frame(pd.read_parquet(io.BytesIO(raw)),
                             observed_by=args.observed_by,
                             display_limit=args.display_limit)
        report["provenance"] = {"source_commit": commit, "dataset": str(dataset),
            "blob_sha": blob, "bytes": len(raw),
            "data_sha256": hashlib.sha256(raw).hexdigest(),
            "auditor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "pandas_version": pd.__version__, "python_version": sys.version.split()[0]}
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({"state": "AUDIT_FAILED", "error_type": type(error).__name__,
                          "detail": str(error)[:300]}), file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
