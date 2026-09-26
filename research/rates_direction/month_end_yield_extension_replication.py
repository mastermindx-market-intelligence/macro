"""Direct-yield source translation of the validated month-end bond extension effect.

This is an amendment to the existing d2_rates_calendar_flows TrialLedger family.
It is retrospective source-translation research only; no live authority is created.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from engine.trial_ledger import TrialLedger
from engine.validation import benjamini_hochberg, newey_west_tstat

FAMILY = "d2_rates_calendar_flows"
PRIOR_FAMILY_TRIALS = 13
PRIMARY_START = pd.Timestamp("2007-01-01")
PRIMARY_END = pd.Timestamp("2026-09-22")
ETF_HISTORY_START = pd.Timestamp("2002-07-30")
TENORS = {
    "DGS2": ("data/fred/DGS2.parquet", "us2y"),
    "DGS5": ("data/fred/DGS5.parquet", "us5y"),
    "DGS10": ("data/fred/DGS10.parquet", "us10y"),
    "DGS30": ("data/fred/DGS30.parquet", "us30y"),
}
METRICS = ("raw", "excess")
CONFIGS = tuple((tenor, metric) for tenor in TENORS for metric in METRICS)
PRIMARY = "DGS10"
SPEC = {
    "family": FAMILY,
    "prior_family_trials": PRIOR_FAMILY_TRIALS,
    "primary_start": PRIMARY_START.date().isoformat(),
    "primary_end": PRIMARY_END.date().isoformat(),
    "historical_context_end_exclusive": ETF_HISTORY_START.date().isoformat(),
    "tenors": {key: {"path": value[0], "column": value[1]} for key, value in TENORS.items()},
    "metrics": list(METRICS),
    "minimum_monthly_changes": 5,
    "expected_sign": "negative",
    "hac_lag_rule": "max(2,min(4,floor(sqrt(n))))",
    "bh_alpha": 0.10,
    "split_half_required": True,
    "headline": "DGS10:raw",
    "authority": False,
}
FROZEN_PATHS = (
    "research/rates_direction/month_end_yield_extension_replication.py",
    "research/rates_direction/MONTH_END_YIELD_EXTENSION_REPLICATION_V1.md",
    "tests/test_month_end_yield_extension_replication.py",
    "engine/validation.py",
)
FREEZE = ROOT / "research/rates_direction/month_end_yield_extension_replication_freeze_v1.json"


def file_hash(path: Path | str) -> str:
    p = Path(path)
    h = sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _nw_lags(n: int) -> int:
    if n <= 1:
        return 0
    return max(2, min(4, int(math.sqrt(n))))


def load_yield_series(path: Path, column: str) -> pd.Series:
    """Load one finite, strictly ordered FRED market-yield series."""
    df = pd.read_parquet(path)
    if column not in df.columns:
        raise ValueError(f"missing expected column {column} in {path}")
    s = pd.to_numeric(df[column], errors="coerce")
    s.index = pd.to_datetime(s.index)
    s = s[np.isfinite(s)].sort_index()
    if s.index.has_duplicates:
        raise ValueError(f"duplicate yield dates in {path}")
    if not s.index.is_monotonic_increasing:
        raise ValueError(f"unordered yield dates in {path}")
    return s.astype(float)


def month_end_events(
    series: pd.Series,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    minimum_monthly_changes: int = 5,
) -> pd.DataFrame:
    """One event per calendar month using only finite observed yield changes.

    The first daily change in a month may reference the last finite observation of
    the prior month. This mirrors an observable close-to-close yield change rather
    than inventing a month boundary reset.
    """
    s = pd.to_numeric(series, errors="coerce").astype(float)
    s.index = pd.to_datetime(s.index)
    s = s[np.isfinite(s)].sort_index()
    if s.index.has_duplicates:
        raise ValueError("duplicate dates are not allowed")
    changes = s.diff().mul(100.0).dropna().rename("change_bp")
    frame = changes.to_frame()
    frame["month"] = frame.index.to_period("M")

    rows: list[dict] = []
    start = pd.Timestamp(start).normalize()
    end = pd.Timestamp(end).normalize()
    for month, group in frame.groupby("month", sort=True):
        month_start = month.to_timestamp(how="start").normalize()
        month_end = month.to_timestamp(how="end").normalize()
        # Never relabel a source-cutoff partial month as a month-end event. The
        # requested interval must contain the whole calendar month. Daily source
        # observations may end earlier for weekends/holidays; that is fine once
        # the calendar month itself is complete at the declared cutoff.
        if month_start < start or month_end > end:
            continue
        in_window = group[(group.index >= start) & (group.index <= end)]
        # Filtering after change calculation keeps the prior close available for
        # the first close-to-close change of a fully admitted month.
        if in_window.empty:
            continue
        # Only admit a month when ALL finite changes for the included month that
        # fall inside the sample are present in the event construction.
        if len(in_window) < minimum_monthly_changes:
            continue
        last = in_window.iloc[-1]
        others = in_window.iloc[:-1]
        if len(others) < minimum_monthly_changes - 1:
            continue
        raw = float(last["change_bp"])
        other_mean = float(others["change_bp"].mean())
        rows.append(
            {
                "month": str(month),
                "event_date": in_window.index[-1],
                "n_changes": int(len(in_window)),
                "raw_bp": raw,
                "other_day_mean_bp": other_mean,
                "excess_bp": raw - other_mean,
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "month",
                "event_date",
                "n_changes",
                "raw_bp",
                "other_day_mean_bp",
                "excess_bp",
            ]
        ).set_index(pd.DatetimeIndex([], name="event_date"))
    out = pd.DataFrame(rows).set_index("event_date").sort_index()
    return out


def _split_half(series: pd.Series) -> dict:
    s = pd.to_numeric(series, errors="coerce").dropna().sort_index()
    n = len(s)
    if n < 2:
        return {
            "n": n,
            "n_first": n,
            "n_second": 0,
            "first_mean_bp": None,
            "second_mean_bp": None,
            "both_negative": False,
        }
    cut = n // 2
    first = s.iloc[:cut]
    second = s.iloc[cut:]
    m1 = float(first.mean())
    m2 = float(second.mean())
    return {
        "n": n,
        "n_first": len(first),
        "n_second": len(second),
        "first_mean_bp": m1,
        "second_mean_bp": m2,
        "both_negative": bool(m1 < 0 and m2 < 0),
    }


def _cell(series: pd.Series) -> dict:
    s = pd.to_numeric(series, errors="coerce").dropna().sort_index()
    n = len(s)
    requested = _nw_lags(n)
    nw = newey_west_tstat(s.to_numpy(float), lags=requested)
    return {
        "n": n,
        "mean_bp": nw.get("mean"),
        "se_bp": nw.get("se"),
        "t_hac": nw.get("t"),
        "p_hac": nw.get("p"),
        "hac_lags": nw.get("lags"),
        "hac_lags_requested": nw.get("lags_requested"),
        "split_half": _split_half(s),
    }


def evaluate_primary(series_by_tenor: dict[str, pd.Series]) -> dict:
    events: dict[str, pd.DataFrame] = {}
    cells: dict[str, dict] = {}
    pvals: dict[str, float] = {}

    for tenor, series in series_by_tenor.items():
        ev = month_end_events(
            series,
            start=PRIMARY_START,
            end=PRIMARY_END,
            minimum_monthly_changes=SPEC["minimum_monthly_changes"],
        )
        events[tenor] = ev
        for metric, col in (("raw", "raw_bp"), ("excess", "excess_bp")):
            key = f"{tenor}:{metric}"
            item = _cell(ev[col] if col in ev.columns else pd.Series(dtype=float))
            cells[key] = item
            if item["p_hac"] is not None and np.isfinite(item["p_hac"]):
                pvals[key] = float(item["p_hac"])

    bh = benjamini_hochberg(pvals, alpha=SPEC["bh_alpha"])
    for key, item in cells.items():
        b = bh.get(key)
        item["bh_q"] = b.get("q") if b else None
        item["bh_reject"] = b.get("reject") if b else False
        item["sign_negative"] = bool(
            item["mean_bp"] is not None and item["mean_bp"] < 0
        )
        item["t_gate"] = bool(
            item["t_hac"] is not None and item["t_hac"] <= -2.0
        )
        item["split_gate"] = bool(item["split_half"]["both_negative"])
        item["cell_gate"] = bool(
            item["sign_negative"]
            and item["t_gate"]
            and item["bh_reject"]
            and item["split_gate"]
        )

    tenor_verdicts = {
        tenor: bool(
            cells[f"{tenor}:raw"]["cell_gate"]
            and cells[f"{tenor}:excess"]["cell_gate"]
        )
        for tenor in TENORS
    }
    event_ranges = {}
    for tenor, ev in events.items():
        event_ranges[tenor] = {
            "n_months": int(len(ev)),
            "first_event": ev.index.min().date().isoformat() if len(ev) else None,
            "last_event": ev.index.max().date().isoformat() if len(ev) else None,
        }

    return {
        "cells": cells,
        "tenor_confirmed": tenor_verdicts,
        "primary_pass": bool(tenor_verdicts[PRIMARY]),
        "event_ranges": event_ranges,
    }


def evaluate_historical_context(dgs10: pd.Series) -> dict:
    start = pd.Timestamp(dgs10.index.min())
    end = ETF_HISTORY_START - pd.Timedelta(days=1)
    ev = month_end_events(
        dgs10,
        start=start,
        end=end,
        minimum_monthly_changes=SPEC["minimum_monthly_changes"],
    )
    return {
        "window": [start.date().isoformat(), end.date().isoformat()],
        "n_months": int(len(ev)),
        "raw": _cell(ev["raw_bp"] if "raw_bp" in ev else pd.Series(dtype=float)),
        "excess": _cell(ev["excess_bp"] if "excess_bp" in ev else pd.Series(dtype=float)),
        "promotion_eligible": False,
    }


def verify_freeze(receipt: dict) -> None:
    if receipt.get("spec") != SPEC:
        raise ValueError("frozen spec mismatch")
    if set(receipt.get("files", {})) != set(FROZEN_PATHS):
        raise ValueError("frozen file set mismatch")
    for name, digest in receipt["files"].items():
        if file_hash(ROOT / name) != digest:
            raise ValueError("post-freeze source change: " + name)
    if set(receipt.get("data", {})) != set(TENORS):
        raise ValueError("frozen data set mismatch")
    for tenor, meta in receipt["data"].items():
        rel, col = TENORS[tenor]
        if meta.get("path") != rel or meta.get("column") != col:
            raise ValueError("frozen data binding mismatch: " + tenor)
        if file_hash(ROOT / rel) != meta.get("sha256"):
            raise ValueError("post-freeze data change: " + tenor)


def freeze() -> None:
    if FREEZE.exists():
        raise FileExistsError("freeze receipt already exists")
    ledger_path = ROOT / "data/trial_ledger.jsonl"
    ledger = TrialLedger(path=ledger_path, family=FAMILY)
    if ledger.literal_n() != PRIOR_FAMILY_TRIALS:
        raise ValueError(
            f"existing family width changed: expected {PRIOR_FAMILY_TRIALS}, "
            f"got {ledger.literal_n()}"
        )
    data = {}
    for tenor, (rel, col) in TENORS.items():
        data[tenor] = {
            "path": rel,
            "column": col,
            "sha256": file_hash(ROOT / rel),
        }
    receipt = {
        "schema": "ric.month_end_yield_extension_replication.freeze.v1",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "outcomes_opened_for_this_construction": False,
        "known_prior_evidence": (
            "d2_rates_calendar_flows V3 TLT/IEF and D4 LQD month-end "
            "price-return extension already scored before this translation study"
        ),
        "spec": SPEC,
        "files": {name: file_hash(ROOT / name) for name in FROZEN_PATHS},
        "data": data,
        "trial_ledger_before_sha256": file_hash(ledger_path),
        "prior_family_trials": PRIOR_FAMILY_TRIALS,
        "new_configs": len(CONFIGS),
        "authority": False,
    }
    FREEZE.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


def run(output: Path) -> None:
    receipt = json.loads(FREEZE.read_text(encoding="utf-8"))
    verify_freeze(receipt)
    ledger_path = ROOT / "data/trial_ledger.jsonl"
    if file_hash(ledger_path) != receipt["trial_ledger_before_sha256"]:
        raise ValueError("trial ledger changed after freeze; reconcile")
    ledger = TrialLedger(path=ledger_path, family=FAMILY)
    if ledger.literal_n() != PRIOR_FAMILY_TRIALS:
        raise ValueError("family state changed after freeze; reconcile")
    output.mkdir(parents=True, exist_ok=False)

    freeze_sha = file_hash(FREEZE)
    configs = [
        {
            "amendment": "direct_yield_month_end_extension_v1",
            "tenor": tenor,
            "metric": metric,
            "spec": SPEC,
            "freeze_sha256": freeze_sha,
            "data_sha256": receipt["data"][tenor]["sha256"],
        }
        for tenor, metric in CONFIGS
    ]
    added = ledger.log_grid(
        configs,
        info_cutoff=receipt["frozen_at"],
        source="d2_rates_calendar_flows_direct_yield_translation",
        note=(
            "Known TLT/IEF/LQD month-end effect translated directly to DGS yields; "
            "retrospective confirmatory source translation; no authority."
        ),
    )
    registration = {
        "schema": "ric.month_end_yield_extension_replication.registration.v1",
        "family": FAMILY,
        "prior_literal_n": PRIOR_FAMILY_TRIALS,
        "registered": added,
        "literal_n": ledger.literal_n(),
        "freeze_sha256": freeze_sha,
        "ledger_before_sha256": receipt["trial_ledger_before_sha256"],
        "ledger_after_sha256": file_hash(ledger_path),
        "authority": False,
    }
    (output / "registration.json").write_text(
        json.dumps(registration, indent=2) + "\n", encoding="utf-8"
    )
    if added != len(CONFIGS) or ledger.literal_n() != PRIOR_FAMILY_TRIALS + len(CONFIGS):
        raise ValueError("partial family registration; reconcile")

    series_by_tenor = {
        tenor: load_yield_series(ROOT / rel, col)
        for tenor, (rel, col) in TENORS.items()
    }
    result = evaluate_primary(series_by_tenor)
    historical = evaluate_historical_context(series_by_tenor["DGS10"])

    payload = {
        "schema": "ric.month_end_yield_extension_replication.result.v1",
        "spec": SPEC,
        "registration": registration,
        "data": receipt["data"],
        "primary": result,
        "historical_context_dgs10_pre_etf": historical,
        "source_translation_not_independent_discovery": True,
        "prospective_validation": False,
        "authority": False,
    }
    (output / "summary.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "primary_pass": result["primary_pass"],
                "tenor_confirmed": result["tenor_confirmed"],
                "cells": {
                    key: {
                        k: item.get(k)
                        for k in (
                            "n",
                            "mean_bp",
                            "t_hac",
                            "p_hac",
                            "bh_q",
                            "bh_reject",
                            "split_gate",
                            "cell_gate",
                        )
                    }
                    for key, item in result["cells"].items()
                },
                "historical_context_dgs10": {
                    "n_months": historical["n_months"],
                    "raw_mean_bp": historical["raw"]["mean_bp"],
                    "raw_t_hac": historical["raw"]["t_hac"],
                    "excess_mean_bp": historical["excess"]["mean_bp"],
                    "excess_t_hac": historical["excess"]["t_hac"],
                },
                "output": str(output),
            },
            indent=2,
        )
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["freeze", "run"])
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    if args.action == "freeze":
        freeze()
        return
    if args.output is None:
        ap.error("run requires --output")
    run(args.output)


if __name__ == "__main__":
    main()
