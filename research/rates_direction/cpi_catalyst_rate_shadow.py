"""Prospective CPI catalyst-to-rates shadow evaluator.

Consumes existing immutable Release Radar rows and incumbent DGS10 history only.
No producer, collector, scheduler, live signal, or trade authority is created.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from engine.trial_ledger import TrialLedger

FAMILY = "ric_cpi_catalyst_rate_shadow_v1"
FREEZE_DATE = date(2026, 9, 24)
GAP_THRESHOLD_PP = 0.05
MOVE_FLOOR_BP = 2.0
MIN_EVENTS = 12
MIN_ACTIVE = 8
PROMOTION_REVIEW_EVENTS = 24
TARGET_EPOCH = "alfred_same_release_vintage_proxy_v1"
MODEL_EPOCH = "coherent_ridge_v1"
LEDGER = ROOT / "data/release_forecast/forward_ledger.jsonl"
DGS10 = ROOT / "data/fred/DGS10.parquet"
FREEZE = ROOT / "research/rates_direction/cpi_catalyst_rate_shadow_freeze_v1.json"
SPEC = {
    "freeze_date": FREEZE_DATE.isoformat(),
    "gap_threshold_pp": GAP_THRESHOLD_PP,
    "move_floor_bp": MOVE_FLOOR_BP,
    "minimum_events": MIN_EVENTS,
    "minimum_active": MIN_ACTIVE,
    "promotion_review_events": PROMOTION_REVIEW_EVENTS,
    "model": MODEL_EPOCH,
    "target_epoch": TARGET_EPOCH,
    "primary_horizon": "h0",
    "secondary_horizons": ["h1", "h5"],
    "baseline": "prior_5_observation_dgs10_direction",
    "evidence_tier": "prospective_rule_existing_forward_inputs_research_only",
}
FROZEN_PATHS = (
    "research/rates_direction/cpi_catalyst_rate_shadow.py",
    "research/rates_direction/CPI_CATALYST_RATE_SHADOW_V1.md",
    "tests/test_cpi_catalyst_rate_shadow.py",
)


def file_hash(path: Path | str) -> str:
    h = sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _finite(value: object) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if np.isfinite(out) else None


def load_jsonl(path: Path = LEDGER) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception as exc:
            raise ValueError(f"invalid JSONL at line {line_no}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"non-object JSONL row at line {line_no}")
        rows.append(row)
    return rows


def _tminus1(asof_night: object, release_date: object) -> bool:
    try:
        a = date.fromisoformat(str(asof_night))
        r = date.fromisoformat(str(release_date))
    except ValueError:
        return False
    return a == r - timedelta(days=1)


def _coherent_rows(rows: list[dict]) -> dict[tuple[str, str, str, str], dict]:
    out: dict[tuple[str, str, str, str], dict] = {}
    for row in rows:
        if row.get("row_type") != "shadow_projection":
            continue
        if row.get("model") != MODEL_EPOCH:
            continue
        if row.get("release") not in ("cpi_headline", "cpi_core"):
            continue
        if row.get("model_epoch") != MODEL_EPOCH or row.get("target_epoch") != TARGET_EPOCH:
            continue
        if row.get("display_only") is not True or row.get("authority") is not False:
            continue
        if not _tminus1(row.get("asof_night"), row.get("release_date")):
            continue
        point = _finite(row.get("projection_point"))
        if point is None:
            continue
        key = (
            str(row.get("asof_night")),
            str(row.get("release")),
            str(row.get("period")),
            str(row.get("release_date")),
        )
        if key in out:
            raise ValueError(f"duplicate coherent T-1 projection: {key}")
        out[key] = row
    return out


def _expectation_rows(rows: list[dict]) -> dict[tuple[str, str, str, str], dict]:
    out: dict[tuple[str, str, str, str], dict] = {}
    for row in rows:
        if row.get("row_type") != "projection" or row.get("model") is not None:
            continue
        if row.get("release") not in ("cpi_headline", "cpi_core"):
            continue
        if not _tminus1(row.get("asof_night"), row.get("release_date")):
            continue
        read = row.get("expectation_read")
        if not isinstance(read, dict):
            continue
        median = _finite(read.get("expectation_median"))
        sources = read.get("sources")
        if median is None or not isinstance(sources, list) or not sources:
            continue
        if any(not isinstance(x, str) or not x for x in sources):
            continue
        key = (
            str(row.get("asof_night")),
            str(row.get("release")),
            str(row.get("period")),
            str(row.get("release_date")),
        )
        if key in out:
            raise ValueError(f"duplicate expectation T-1 projection: {key}")
        out[key] = row
    return out


def component_state(gap_pp: float) -> int:
    if gap_pp >= GAP_THRESHOLD_PP:
        return 1
    if gap_pp <= -GAP_THRESHOLD_PP:
        return -1
    return 0


def combine_states(headline: int, core: int) -> int:
    if headline == -1 and core == 1 or headline == 1 and core == -1:
        return 0
    if headline == 1 or core == 1:
        return 1
    if headline == -1 or core == -1:
        return -1
    return 0


def build_events(rows: list[dict]) -> list[dict]:
    coherent = _coherent_rows(rows)
    expectations = _expectation_rows(rows)
    by_date: dict[str, dict[str, dict]] = {}
    for key, crow in coherent.items():
        erow = expectations.get(key)
        if erow is None:
            continue
        asof_night, release, period, release_date = key
        point = float(crow["projection_point"])
        eread = erow["expectation_read"]
        expectation = float(eread["expectation_median"])
        gap = point - expectation
        component = {
            "release": release,
            "period": period,
            "asof_night": asof_night,
            "release_date": release_date,
            "coherent_prediction_id": crow.get("prediction_id"),
            "coherent_inputs_hash": crow.get("inputs_hash"),
            "coherent_point": point,
            "expectation_median": expectation,
            "expectation_sources": list(eread["sources"]),
            "gap_pp": round(gap, 6),
            "state": component_state(gap),
            "model_epoch": crow.get("model_epoch"),
            "target_epoch": crow.get("target_epoch"),
        }
        by_date.setdefault(release_date, {})[release] = component

    events: list[dict] = []
    for release_date, comps in sorted(by_date.items()):
        h = comps.get("cpi_headline")
        c = comps.get("cpi_core")
        if h is None or c is None:
            continue
        if h["asof_night"] != c["asof_night"]:
            raise ValueError(f"headline/core cutoff mismatch on {release_date}")
        if h["period"] != c["period"]:
            raise ValueError(f"headline/core period mismatch on {release_date}")
        rdate = date.fromisoformat(release_date)
        events.append(
            {
                "release_date": release_date,
                "period": h["period"],
                "asof_night": h["asof_night"],
                "prospective_eligible": rdate > FREEZE_DATE,
                "signal": combine_states(h["state"], c["state"]),
                "headline": h,
                "core": c,
                "authority": False,
            }
        )
    return events


def load_dgs10(path: Path = DGS10) -> pd.Series:
    df = pd.read_parquet(path)
    if df.shape[1] != 1:
        raise ValueError("DGS10 source must contain exactly one value column")
    s = pd.to_numeric(df.iloc[:, 0], errors="coerce").astype(float).dropna()
    s.index = pd.DatetimeIndex(s.index).tz_localize(None).normalize()
    if s.index.has_duplicates or not s.index.is_monotonic_increasing:
        raise ValueError("DGS10 index must be unique and increasing")
    return s


def move_class(bp: float | None) -> int | None:
    if bp is None or not np.isfinite(bp):
        return None
    if bp >= MOVE_FLOOR_BP:
        return 1
    if bp <= -MOVE_FLOOR_BP:
        return -1
    return 0


def attach_outcome(event: dict, dgs10: pd.Series) -> dict:
    out = dict(event)
    rd = pd.Timestamp(event["release_date"])
    prior = dgs10[dgs10.index < rd]
    release = dgs10[dgs10.index == rd]
    future = dgs10[dgs10.index > rd]
    if prior.empty:
        out["outcome"] = None
        return out
    prior_close = float(prior.iloc[-1])
    prior_index = prior.index
    baseline_bp = None
    if len(prior) >= 6:
        baseline_bp = float((prior.iloc[-1] - prior.iloc[-6]) * 100.0)
    outcome = {
        "prior_date": prior_index[-1].date().isoformat(),
        "prior_close": prior_close,
        "baseline_5obs_bp": baseline_bp,
        "baseline_state": move_class(baseline_bp),
        "h0_bp": None,
        "h0_state": None,
        "h1_bp": None,
        "h1_state": None,
        "h5_bp": None,
        "h5_state": None,
    }
    if not release.empty:
        h0 = float((release.iloc[0] - prior_close) * 100.0)
        outcome["h0_bp"] = h0
        outcome["h0_state"] = move_class(h0)
    if len(future) >= 1:
        h1 = float((future.iloc[0] - prior_close) * 100.0)
        outcome["h1_bp"] = h1
        outcome["h1_state"] = move_class(h1)
    if len(future) >= 5:
        h5 = float((future.iloc[4] - prior_close) * 100.0)
        outcome["h5_bp"] = h5
        outcome["h5_state"] = move_class(h5)
    out["outcome"] = outcome
    return out


def summarize(events: list[dict]) -> dict:
    prospective = [e for e in events if e.get("prospective_eligible")]
    active = [e for e in prospective if e.get("signal") in (-1, 1)]
    matured = [
        e for e in active
        if isinstance(e.get("outcome"), dict)
        and e["outcome"].get("h0_state") is not None
    ]
    def score(horizon: str) -> dict:
        key = f"{horizon}_state"
        rows = [e for e in active if isinstance(e.get("outcome"), dict) and e["outcome"].get(key) is not None]
        cat = sum(e["signal"] == e["outcome"][key] for e in rows)
        baseline_rows = [e for e in rows if e["outcome"].get("baseline_state") in (-1, 1)]
        base = sum(e["outcome"]["baseline_state"] == e["outcome"][key] for e in baseline_rows)
        paired = [
            int(e["signal"] == e["outcome"][key]) - int(e["outcome"]["baseline_state"] == e["outcome"][key])
            for e in rows if e["outcome"].get("baseline_state") in (-1, 1)
        ]
        return {
            "n_active_matured": len(rows),
            "catalyst_hits": cat,
            "catalyst_accuracy": cat / len(rows) if rows else None,
            "baseline_n": len(baseline_rows),
            "baseline_hits": base,
            "baseline_accuracy": base / len(baseline_rows) if baseline_rows else None,
            "paired_mean_success_difference": float(np.mean(paired)) if paired else None,
        }
    return {
        "schema": "ric.cpi_catalyst_rate_shadow.summary.v1",
        "freeze_date": FREEZE_DATE.isoformat(),
        "total_joined_events": len(events),
        "pre_freeze_excluded": sum(not e.get("prospective_eligible") for e in events),
        "prospective_events": len(prospective),
        "prospective_active": len(active),
        "prospective_abstained": len(prospective) - len(active),
        "matured_primary": len(matured),
        "signal_counts": dict(Counter(e.get("signal") for e in prospective)),
        "h0": score("h0"),
        "h1": score("h1"),
        "h5": score("h5"),
        "descriptive_floor_met": len(prospective) >= MIN_EVENTS and len(active) >= MIN_ACTIVE,
        "promotion_review_sample_met": len(prospective) >= PROMOTION_REVIEW_EVENTS,
        "authority": False,
    }


def freeze() -> None:
    if FREEZE.exists():
        raise FileExistsError("freeze receipt already exists")
    ledger = TrialLedger(path=ROOT / "data/trial_ledger.jsonl", family=FAMILY)
    if ledger.literal_n() != 0:
        raise ValueError("family already registered; reconcile")
    receipt = {
        "schema": "ric.cpi_catalyst_rate_shadow.freeze.v1",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "eligible_outcomes_opened": False,
        "freeze_date": FREEZE_DATE.isoformat(),
        "spec": SPEC,
        "files": {name: file_hash(ROOT / name) for name in FROZEN_PATHS},
        "release_ledger_sha256_at_freeze": file_hash(LEDGER),
        "dgs10_sha256_at_freeze": file_hash(DGS10),
        "trial_ledger_before_sha256": file_hash(ROOT / "data/trial_ledger.jsonl"),
        "prior_family_trials": 0,
        "new_configs": 1,
        "authority": False,
    }
    FREEZE.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


def verify_freeze(receipt: dict) -> None:
    if receipt.get("freeze_date") != FREEZE_DATE.isoformat() or receipt.get("spec") != SPEC:
        raise ValueError("frozen spec mismatch")
    if set(receipt.get("files", {})) != set(FROZEN_PATHS):
        raise ValueError("frozen file set mismatch")
    for name, digest in receipt["files"].items():
        if file_hash(ROOT / name) != digest:
            raise ValueError("post-freeze source change: " + name)


def register() -> None:
    receipt = json.loads(FREEZE.read_text(encoding="utf-8"))
    verify_freeze(receipt)
    ledger_path = ROOT / "data/trial_ledger.jsonl"
    if file_hash(ledger_path) != receipt["trial_ledger_before_sha256"]:
        raise ValueError("trial ledger changed after freeze; reconcile")
    ledger = TrialLedger(path=ledger_path, family=FAMILY)
    if ledger.literal_n() != 0:
        raise ValueError("family state changed; reconcile")
    config = [{
        "spec": SPEC,
        "freeze_sha256": file_hash(FREEZE),
        "release_ledger_sha256_at_freeze": receipt["release_ledger_sha256_at_freeze"],
        "dgs10_sha256_at_freeze": receipt["dgs10_sha256_at_freeze"],
    }]
    added = ledger.log_grid(
        config,
        info_cutoff=receipt["frozen_at"],
        source="prospective_cpi_catalyst_to_rates_shadow",
        note="Future post-freeze CPI only; existing Release Radar rows; no authority.",
    )
    if added != 1 or ledger.literal_n() != 1:
        raise ValueError("registration was not exactly one new configuration")
    print(json.dumps({"family": FAMILY, "registered": added, "literal_n": ledger.literal_n()}, indent=2))


def report(output: Path | None = None) -> dict:
    receipt = json.loads(FREEZE.read_text(encoding="utf-8"))
    verify_freeze(receipt)
    events = build_events(load_jsonl())
    dgs10 = load_dgs10()
    graded = [attach_outcome(e, dgs10) for e in events]
    payload = {
        "schema": "ric.cpi_catalyst_rate_shadow.report.v1",
        "spec": SPEC,
        "events": graded,
        "summary": summarize(graded),
        "authority": False,
    }
    if output is not None:
        output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
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
