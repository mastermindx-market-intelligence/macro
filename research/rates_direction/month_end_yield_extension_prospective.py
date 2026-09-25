"""Forward-only month-end DGS10 shadow for the existing calendar-flow family."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from engine.rebalance_calendar import month_end_sessions
from engine.trial_ledger import TrialLedger
from engine.validation import newey_west_tstat

FAMILY = "d2_rates_calendar_flows"
PRIOR_FAMILY_TRIALS = 21
FREEZE_DATE = date(2026, 9, 24)
SCHEDULE_EVENTS = 24
DGS10 = ROOT / "data/fred/DGS10.parquet"
DGS10_COLUMN = "us10y"
DESCRIPTIVE_FLOOR = 12
PROMOTION_REVIEW_FLOOR = 24
SPEC = {
    "family": FAMILY,
    "prior_family_trials": PRIOR_FAMILY_TRIALS,
    "freeze_date": FREEZE_DATE.isoformat(),
    "scheduled_events": SCHEDULE_EVENTS,
    "tenor": "DGS10",
    "source": "data/fred/DGS10.parquet",
    "source_column": DGS10_COLUMN,
    "signal": "DOWN",
    "zero_is_success": False,
    "descriptive_floor": DESCRIPTIVE_FLOOR,
    "promotion_review_floor": PROMOTION_REVIEW_FLOOR,
    "hac_lag_rule": "max(2,min(4,floor(sqrt(n))))",
    "quarter_end_is_diagnostic_only": True,
    "authority": False,
}
FREEZE = ROOT / "research/rates_direction/month_end_yield_extension_prospective_freeze_v1.json"
FROZEN_PATHS = (
    "research/rates_direction/month_end_yield_extension_prospective.py",
    "research/rates_direction/MONTH_END_YIELD_EXTENSION_PROSPECTIVE_V1.md",
    "tests/test_month_end_yield_extension_prospective.py",
    "engine/rebalance_calendar.py",
    "engine/validation.py",
)


def file_hash(path: Path | str) -> str:
    h = sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_dgs10(path: Path = DGS10) -> pd.Series:
    df = pd.read_parquet(path)
    if DGS10_COLUMN not in df.columns:
        raise ValueError("DGS10 source column absent")
    s = pd.to_numeric(df[DGS10_COLUMN], errors="coerce")
    s.index = pd.to_datetime(s.index).normalize()
    s = s[np.isfinite(s)].sort_index()
    if s.index.has_duplicates or not s.index.is_monotonic_increasing:
        raise ValueError("DGS10 dates must be unique and sorted")
    return s.astype(float)


def series_prefix_digest(series: pd.Series, through: date | pd.Timestamp) -> str:
    """Canonical date/value digest, independent of Parquet byte layout."""
    end = pd.Timestamp(through).normalize()
    s = series[series.index <= end]
    rows = [[ts.date().isoformat(), format(float(value), ".12g")] for ts, value in s.items()]
    body = json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode()
    return sha256(body).hexdigest()


def frozen_schedule() -> list[str]:
    """Next exact 24 incumbent calendar month-end sessions after freeze."""
    dates = month_end_sessions(FREEZE_DATE.year, FREEZE_DATE.year + 4)
    future = [d for d in dates if d > FREEZE_DATE]
    if len(future) < SCHEDULE_EVENTS:
        raise ValueError("calendar owner did not provide enough future month-ends")
    return [d.isoformat() for d in future[:SCHEDULE_EVENTS]]


def _nw_lags(n: int) -> int:
    if n <= 1:
        return 0
    return max(2, min(4, int(math.sqrt(n))))


def _split_half(values: list[float]) -> dict:
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    n = len(a)
    if n < 2:
        return {
            "n": n,
            "first_mean_bp": None,
            "second_mean_bp": None,
            "both_negative": False,
        }
    cut = n // 2
    first = float(a[:cut].mean())
    second = float(a[cut:].mean())
    return {
        "n": n,
        "first_mean_bp": first,
        "second_mean_bp": second,
        "both_negative": bool(first < 0 and second < 0),
    }


def _metric(values: list[float]) -> dict:
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    nw = newey_west_tstat(a, lags=_nw_lags(len(a)))
    return {
        "n": len(a),
        "mean_bp": nw.get("mean"),
        "se_bp": nw.get("se"),
        "t_hac": nw.get("t"),
        "p_hac": nw.get("p"),
        "hac_lags": nw.get("lags"),
        "hac_lags_requested": nw.get("lags_requested"),
        "split_half": _split_half(a.tolist()),
    }


def evaluate_event(series: pd.Series, event_date: date) -> dict:
    stamp = pd.Timestamp(event_date).normalize()
    quarter_end = stamp.month in (3, 6, 9, 12)
    base = {
        "event_date": event_date.isoformat(),
        "quarter_end_month": quarter_end,
        "signal": "DOWN",
        "authority": False,
    }
    if stamp > series.index.max():
        return {**base, "status": "PENDING_SOURCE", "raw_bp": None, "excess_bp": None}
    if stamp not in series.index:
        return {
            **base,
            "status": "MISSING_FROZEN_EVENT_OBSERVATION",
            "raw_bp": None,
            "excess_bp": None,
        }

    prior = series[series.index < stamp]
    if prior.empty:
        return {**base, "status": "MISSING_PRIOR_CLOSE", "raw_bp": None, "excess_bp": None}
    prior_stamp = prior.index[-1]
    prior_close = float(prior.iloc[-1])
    event_close = float(series.loc[stamp])
    raw_bp = (event_close - prior_close) * 100.0

    changes = series.diff().mul(100.0).dropna()
    same_month_before = changes[
        (changes.index.to_period("M") == stamp.to_period("M"))
        & (changes.index < stamp)
    ]
    if same_month_before.empty:
        return {
            **base,
            "status": "MISSING_MONTH_BASELINE",
            "prior_date": prior_stamp.date().isoformat(),
            "raw_bp": raw_bp,
            "excess_bp": None,
        }
    other_mean = float(same_month_before.mean())
    return {
        **base,
        "status": "MATURED",
        "prior_date": prior_stamp.date().isoformat(),
        "prior_close": prior_close,
        "event_close": event_close,
        "raw_bp": raw_bp,
        "other_month_mean_bp": other_mean,
        "excess_bp": raw_bp - other_mean,
        "directional_success": bool(raw_bp < 0),
    }


def summarize(events: list[dict], *, historical_prefix_changed: bool) -> dict:
    matured = [e for e in events if e.get("status") == "MATURED"]
    raw = [float(e["raw_bp"]) for e in matured]
    excess = [float(e["excess_bp"]) for e in matured]
    raw_metric = _metric(raw)
    excess_metric = _metric(excess)
    q = [e for e in matured if e["quarter_end_month"]]
    nq = [e for e in matured if not e["quarter_end_month"]]

    def _slice(rows: list[dict]) -> dict:
        vals = [float(e["raw_bp"]) for e in rows]
        return {
            "n": len(rows),
            "mean_raw_bp": float(np.mean(vals)) if vals else None,
            "negative_fraction": float(np.mean([v < 0 for v in vals])) if vals else None,
        }

    n = len(matured)
    promotion_gate = bool(
        n >= PROMOTION_REVIEW_FLOOR
        and not historical_prefix_changed
        and raw_metric["mean_bp"] is not None
        and raw_metric["mean_bp"] < 0
        and raw_metric["t_hac"] is not None
        and raw_metric["t_hac"] <= -2.0
        and raw_metric["split_half"]["both_negative"]
        and excess_metric["mean_bp"] is not None
        and excess_metric["mean_bp"] < 0
        and excess_metric["t_hac"] is not None
        and excess_metric["t_hac"] <= -2.0
        and excess_metric["split_half"]["both_negative"]
    )
    return {
        "scheduled": len(events),
        "matured": n,
        "pending": sum(e.get("status") == "PENDING_SOURCE" for e in events),
        "missing_frozen_event_observation": sum(
            e.get("status") == "MISSING_FROZEN_EVENT_OBSERVATION" for e in events
        ),
        "directional_successes": sum(bool(e.get("directional_success")) for e in matured),
        "directional_hit_fraction": (
            float(np.mean([bool(e["directional_success"]) for e in matured]))
            if matured
            else None
        ),
        "raw": raw_metric,
        "excess": excess_metric,
        "quarter_end_diagnostic": _slice(q),
        "non_quarter_end_diagnostic": _slice(nq),
        "historical_prefix_changed": historical_prefix_changed,
        "descriptive_floor_met": n >= DESCRIPTIVE_FLOOR,
        "promotion_review_sample_met": n >= PROMOTION_REVIEW_FLOOR,
        "promotion_gate_met": promotion_gate,
        "authority": False,
    }


def verify_freeze(receipt: dict) -> None:
    if receipt.get("spec") != SPEC:
        raise ValueError("frozen spec mismatch")
    if receipt.get("schedule") != frozen_schedule():
        raise ValueError("frozen schedule no longer matches pinned calendar owner")
    if set(receipt.get("files", {})) != set(FROZEN_PATHS):
        raise ValueError("frozen file set mismatch")
    for name, digest in receipt["files"].items():
        if file_hash(ROOT / name) != digest:
            raise ValueError("post-freeze source change: " + name)


def freeze() -> None:
    if FREEZE.exists():
        raise FileExistsError("freeze receipt already exists")
    ledger_path = ROOT / "data/trial_ledger.jsonl"
    ledger = TrialLedger(path=ledger_path, family=FAMILY)
    if ledger.literal_n() != PRIOR_FAMILY_TRIALS:
        raise ValueError(
            f"family width changed: expected {PRIOR_FAMILY_TRIALS}, got {ledger.literal_n()}"
        )
    series = load_dgs10()
    latest = series.index.max().date()
    if latest >= FREEZE_DATE:
        # An event after/at the declared freeze boundary would require checking
        # whether eligible outcomes had already become observable. Freeze only
        # while the source remains strictly pre-boundary as preregistered.
        raise ValueError(
            f"DGS10 latest {latest} is not strictly before freeze date {FREEZE_DATE}"
        )
    receipt = {
        "schema": "ric.month_end_yield_extension.prospective_freeze.v1",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "eligible_outcomes_opened": False,
        "spec": SPEC,
        "schedule": frozen_schedule(),
        "files": {name: file_hash(ROOT / name) for name in FROZEN_PATHS},
        "dgs10_latest_at_freeze": latest.isoformat(),
        "dgs10_prefix_digest": series_prefix_digest(series, latest),
        "trial_ledger_before_sha256": file_hash(ledger_path),
        "prior_family_trials": PRIOR_FAMILY_TRIALS,
        "new_configs": 1,
        "authority": False,
    }
    FREEZE.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


def register() -> None:
    receipt = json.loads(FREEZE.read_text(encoding="utf-8"))
    verify_freeze(receipt)
    ledger_path = ROOT / "data/trial_ledger.jsonl"
    if file_hash(ledger_path) != receipt["trial_ledger_before_sha256"]:
        raise ValueError("trial ledger changed after freeze; reconcile")
    ledger = TrialLedger(path=ledger_path, family=FAMILY)
    if ledger.literal_n() != PRIOR_FAMILY_TRIALS:
        raise ValueError("family width changed after freeze; reconcile")
    added = ledger.log_grid(
        [
            {
                "amendment": "prospective_month_end_dgs10_v1",
                "spec": SPEC,
                "freeze_sha256": file_hash(FREEZE),
                "schedule": receipt["schedule"],
                "dgs10_prefix_digest": receipt["dgs10_prefix_digest"],
            }
        ],
        info_cutoff=receipt["frozen_at"],
        source="d2_rates_calendar_flows_prospective_month_end_dgs10",
        note=(
            "Generic DOWN sign frozen before any post-2026-09-24 month-end; "
            "quarter-end diagnostic only; no authority."
        ),
    )
    if added != 1 or ledger.literal_n() != PRIOR_FAMILY_TRIALS + 1:
        raise ValueError("prospective registration was not exactly one config")
    result = {
        "schema": "ric.month_end_yield_extension.prospective_registration.v1",
        "family": FAMILY,
        "registered": added,
        "literal_n": ledger.literal_n(),
        "config_hash": json.loads(ledger_path.read_text().splitlines()[-1])["config_hash"],
        "freeze_sha256": file_hash(FREEZE),
        "ledger_after_sha256": file_hash(ledger_path),
        "authority": False,
    }
    out = ROOT / "research/rates_direction/month_end_yield_extension_prospective_registration_v1.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


def report(output: Path | None = None) -> dict:
    receipt = json.loads(FREEZE.read_text(encoding="utf-8"))
    verify_freeze(receipt)
    series = load_dgs10()
    freeze_latest = date.fromisoformat(receipt["dgs10_latest_at_freeze"])
    changed = (
        series_prefix_digest(series, freeze_latest)
        != receipt["dgs10_prefix_digest"]
    )
    events = [
        evaluate_event(series, date.fromisoformat(token))
        for token in receipt["schedule"]
    ]
    payload = {
        "schema": "ric.month_end_yield_extension.prospective_report.v1",
        "spec": SPEC,
        "freeze_sha256": file_hash(FREEZE),
        "source_latest": series.index.max().date().isoformat(),
        "events": events,
        "summary": summarize(events, historical_prefix_changed=changed),
        "authority": False,
    }
    if output is not None:
        output.write_text(
            json.dumps(payload, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(payload["summary"], indent=2))
    return payload


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["freeze", "register", "report"])
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    if args.action == "freeze":
        freeze()
    elif args.action == "register":
        register()
    else:
        report(args.output)


if __name__ == "__main__":
    main()
