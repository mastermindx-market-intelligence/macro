"""Prospective inflation-catalyst -> Treasury response shadow.

Reads only incumbent Release Radar forward evidence and DGS10. It never writes the
Release Radar ledger, creates a scheduler, or grants signal/trade authority.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np

from engine.trial_ledger import TrialLedger
from research.rates_direction import cpi_catalyst_rate_shadow as cpi

FAMILY = "ric_inflation_catalyst_rate_response_v1"
FREEZE_DATE = date(2026, 9, 24)
Z_THRESHOLD = 0.35
MOVE_FLOOR_BP = 2.0
MIN_EVENTS = 12
MIN_ACTIVE = 8
PROMOTION_REVIEW_EVENTS = 24
NY = ZoneInfo("America/New_York")
LEDGER = ROOT / "data/release_forecast/forward_ledger.jsonl"
DGS10 = ROOT / "data/fred/DGS10.parquet"
FREEZE = ROOT / "research/rates_direction/inflation_catalyst_rate_response_shadow_freeze_v1.json"
FAMILIES = {
    "cpi": ("cpi_headline", "cpi_core"),
    "pce": ("pce_headline", "pce_core"),
}
COMPONENTS = frozenset(x for pair in FAMILIES.values() for x in pair)
SPEC = {
    "freeze_date": FREEZE_DATE.isoformat(),
    "z_threshold": Z_THRESHOLD,
    "move_floor_bp": MOVE_FLOOR_BP,
    "minimum_events": MIN_EVENTS,
    "minimum_active": MIN_ACTIVE,
    "promotion_review_events": PROMOTION_REVIEW_EVENTS,
    "families": {k: list(v) for k, v in FAMILIES.items()},
    "expectation_cutoff": "exact_release_date_minus_1_calendar_day",
    "actual_basis": "official_published_metric",
    "actual_source": "official_release_document",
    "actual_availability_cutoff": "16:00 America/New_York release day",
    "primary_horizon": "h0",
    "secondary_horizons": ["h1", "h5"],
    "baseline": "prior_5_observation_dgs10_direction",
    "evidence_tier": "prospective_actual_catalyst_to_rates_research_only",
}
FROZEN_PATHS = (
    "research/rates_direction/inflation_catalyst_rate_response_shadow.py",
    "research/rates_direction/INFLATION_CATALYST_RATE_RESPONSE_SHADOW_V1.md",
    "tests/test_inflation_catalyst_rate_response_shadow.py",
    "research/rates_direction/cpi_catalyst_rate_shadow.py",
)


def file_hash(path: Path | str) -> str:
    return cpi.file_hash(path)


def _finite(value: object) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if np.isfinite(out) else None


def _parse_ts(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    token = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        out = datetime.fromisoformat(token)
    except ValueError:
        return None
    if out.tzinfo is None or out.utcoffset() is None:
        return None
    return out.astimezone(timezone.utc)


def _tminus1(asof_night: object, release_date: object) -> bool:
    try:
        a = date.fromisoformat(str(asof_night))
        r = date.fromisoformat(str(release_date))
    except ValueError:
        return False
    return a == r - timedelta(days=1)


def _expectation_rows(rows: list[dict]) -> dict[tuple[str, str, str], dict]:
    """Exact T-1 champion expectation evidence, one row per component/event."""
    out: dict[tuple[str, str, str], dict] = {}
    for row in rows:
        if row.get("row_type") != "projection" or row.get("model") is not None:
            continue
        release = row.get("release")
        if release not in COMPONENTS:
            continue
        if not _tminus1(row.get("asof_night"), row.get("release_date")):
            continue
        read = row.get("expectation_read")
        if not isinstance(read, dict):
            continue
        median = _finite(read.get("expectation_median"))
        sigma = _finite(row.get("sigma_scale_pp"))
        sources = read.get("sources")
        if median is None or sigma is None or sigma <= 0:
            continue
        if not isinstance(sources, list) or not sources:
            continue
        if any(not isinstance(x, str) or not x for x in sources):
            continue
        period = str(row.get("period") or "")
        release_date = str(row.get("release_date") or "")
        if not period or not release_date:
            continue
        key = (str(release), period, release_date)
        if key in out:
            raise ValueError(f"duplicate exact T-1 expectation row: {key}")
        out[key] = {
            "release": release,
            "period": period,
            "release_date": release_date,
            "asof_night": str(row.get("asof_night")),
            "expectation_median": median,
            "expectation_sources": list(sources),
            "sigma_scale_pp": sigma,
            "prediction_id": row.get("prediction_id"),
            "inputs_hash": row.get("inputs_hash"),
            "model_epoch": row.get("model_epoch"),
            "target_epoch": row.get("target_epoch"),
        }
    return out


def _official_actual_rows(rows: list[dict]) -> dict[tuple[str, str, str], dict]:
    """Earliest same-day official receipt, deduping copies carried by model rows."""
    by_key: dict[tuple[str, str, str], dict[str, dict]] = {}
    for row in rows:
        if row.get("row_type") != "scored":
            continue
        release = row.get("release")
        if release not in COMPONENTS:
            continue
        if row.get("actual_basis") != "official_published_metric":
            continue
        if row.get("actual_source") != "official_release_document":
            continue
        receipt = row.get("actual_receipt_id")
        observed = _parse_ts(row.get("actual_observed_at"))
        actual = _finite(
            row.get("actual_first")
            if row.get("actual_first") is not None
            else row.get("actual")
        )
        period = str(row.get("period") or "")
        release_date_s = str(row.get("release_date") or "")
        if not receipt or observed is None or actual is None or not period or not release_date_s:
            continue
        try:
            release_day = date.fromisoformat(release_date_s)
        except ValueError:
            continue
        observed_ny = observed.astimezone(NY)
        close_ny = datetime.combine(release_day, time(16, 0), tzinfo=NY)
        if observed_ny.date() != release_day or observed_ny > close_ny:
            continue
        key = (str(release), period, release_date_s)
        rec = {
            "actual": actual,
            "actual_receipt_id": str(receipt),
            "actual_observed_at": observed.isoformat(),
            "actual_source_url": row.get("actual_source_url"),
            "actual_source_sha256": row.get("actual_source_sha256"),
        }
        prior = by_key.setdefault(key, {}).get(str(receipt))
        if prior is not None and (
            prior["actual"] != rec["actual"]
            or prior["actual_observed_at"] != rec["actual_observed_at"]
        ):
            raise ValueError(f"conflicting rows for official receipt: {receipt}")
        by_key[key][str(receipt)] = rec

    out: dict[tuple[str, str, str], dict] = {}
    for key, receipts in by_key.items():
        out[key] = min(
            receipts.values(),
            key=lambda item: _parse_ts(item["actual_observed_at"]) or datetime.max.replace(tzinfo=timezone.utc),
        )
    return out


def component_state(z_actual: float) -> int:
    if z_actual >= Z_THRESHOLD:
        return 1
    if z_actual <= -Z_THRESHOLD:
        return -1
    return 0


def combine_states(a: int, b: int) -> int:
    if (a, b) in ((1, -1), (-1, 1)):
        return 0
    if a == 1 or b == 1:
        return 1
    if a == -1 or b == -1:
        return -1
    return 0


def build_events(rows: list[dict]) -> list[dict]:
    expectations = _expectation_rows(rows)
    actuals = _official_actual_rows(rows)
    events: list[dict] = []

    for family, pair in FAMILIES.items():
        first, second = pair
        first_keys = {
            (period, release_date)
            for release, period, release_date in expectations
            if release == first
        }
        second_keys = {
            (period, release_date)
            for release, period, release_date in expectations
            if release == second
        }
        for period, release_date_s in sorted(first_keys & second_keys):
            e1 = expectations[(first, period, release_date_s)]
            e2 = expectations[(second, period, release_date_s)]
            if e1["asof_night"] != e2["asof_night"]:
                raise ValueError(f"component T-1 mismatch: {family}/{period}")
            rdate = date.fromisoformat(release_date_s)
            a1 = actuals.get((first, period, release_date_s))
            a2 = actuals.get((second, period, release_date_s))
            components = []
            missing = []
            for exp, act in ((e1, a1), (e2, a2)):
                if act is None:
                    missing.append(exp["release"])
                    components.append({**exp, "actual": None, "z_actual": None, "state": None})
                    continue
                z = (act["actual"] - exp["expectation_median"]) / exp["sigma_scale_pp"]
                components.append(
                    {
                        **exp,
                        **act,
                        "z_actual": round(float(z), 6),
                        "state": component_state(float(z)),
                    }
                )
            signal = None
            latest_observed = None
            if not missing:
                signal = combine_states(int(components[0]["state"]), int(components[1]["state"]))
                latest_observed = max(
                    str(components[0]["actual_observed_at"]),
                    str(components[1]["actual_observed_at"]),
                )
            events.append(
                {
                    "family": family,
                    "period": period,
                    "release_date": release_date_s,
                    "asof_night": e1["asof_night"],
                    "prospective_eligible": rdate > FREEZE_DATE,
                    "signal": signal,
                    "signal_observed_at": latest_observed,
                    "availability": "observable" if not missing else "waiting_official_actual",
                    "missing_components": missing,
                    "components": components,
                    "authority": False,
                }
            )
    return events


def attach_outcomes(events: list[dict]):
    dgs10 = cpi.load_dgs10(DGS10)
    return [cpi.attach_outcome(event, dgs10) for event in events]


def _score_group(events: list[dict], horizon: str) -> dict:
    key = f"{horizon}_state"
    active = [e for e in events if e.get("signal") in (-1, 1)]
    rows = [
        e
        for e in active
        if isinstance(e.get("outcome"), dict)
        and e["outcome"].get(key) is not None
    ]
    catalyst_hits = sum(e["signal"] == e["outcome"][key] for e in rows)
    baseline_rows = [
        e for e in rows if e["outcome"].get("baseline_state") in (-1, 1)
    ]
    baseline_hits = sum(
        e["outcome"]["baseline_state"] == e["outcome"][key]
        for e in baseline_rows
    )
    paired = [
        int(e["signal"] == e["outcome"][key])
        - int(e["outcome"]["baseline_state"] == e["outcome"][key])
        for e in baseline_rows
    ]
    return {
        "n_active_matured": len(rows),
        "catalyst_hits": catalyst_hits,
        "catalyst_accuracy": catalyst_hits / len(rows) if rows else None,
        "baseline_n": len(baseline_rows),
        "baseline_hits": baseline_hits,
        "baseline_accuracy": baseline_hits / len(baseline_rows) if baseline_rows else None,
        "paired_mean_success_difference": float(np.mean(paired)) if paired else None,
    }


def _summary_slice(events: list[dict]) -> dict:
    observable = [e for e in events if e.get("signal") in (-1, 0, 1)]
    active = [e for e in observable if e.get("signal") in (-1, 1)]
    return {
        "events": len(events),
        "signal_observable": len(observable),
        "active": len(active),
        "abstained": sum(e.get("signal") == 0 for e in observable),
        "waiting_official_actual": sum(e.get("signal") is None for e in events),
        "signal_counts": dict(Counter(e.get("signal") for e in observable)),
        "h0": _score_group(events, "h0"),
        "h1": _score_group(events, "h1"),
        "h5": _score_group(events, "h5"),
    }


def summarize(events: list[dict]) -> dict:
    prospective = [e for e in events if e.get("prospective_eligible")]
    total = _summary_slice(prospective)
    by_family = {
        family: _summary_slice([e for e in prospective if e.get("family") == family])
        for family in FAMILIES
    }
    return {
        "schema": "ric.inflation_catalyst_rate_response.summary.v1",
        "freeze_date": FREEZE_DATE.isoformat(),
        "pre_freeze_excluded": sum(not e.get("prospective_eligible") for e in events),
        **total,
        "by_family": by_family,
        "descriptive_floor_met": (
            total["signal_observable"] >= MIN_EVENTS and total["active"] >= MIN_ACTIVE
        ),
        "promotion_review_sample_met": (
            total["signal_observable"] >= PROMOTION_REVIEW_EVENTS
        ),
        "authority": False,
    }


def freeze() -> None:
    if FREEZE.exists():
        raise FileExistsError("freeze receipt already exists")
    ledger = TrialLedger(path=ROOT / "data/trial_ledger.jsonl", family=FAMILY)
    if ledger.literal_n() != 0:
        raise ValueError("family already registered; reconcile")
    receipt = {
        "schema": "ric.inflation_catalyst_rate_response.freeze.v1",
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
        source="prospective_official_inflation_catalyst_to_rates_response",
        note="Future post-freeze CPI/PCE only; incumbent Release Radar + DGS10; no authority.",
    )
    if added != 1 or ledger.literal_n() != 1:
        raise ValueError("registration was not exactly one new configuration")
    print(json.dumps({"family": FAMILY, "registered": added, "literal_n": ledger.literal_n()}, indent=2))


def report(output: Path | None = None) -> dict:
    receipt = json.loads(FREEZE.read_text(encoding="utf-8"))
    verify_freeze(receipt)
    events = attach_outcomes(build_events(cpi.load_jsonl(LEDGER)))
    payload = {
        "schema": "ric.inflation_catalyst_rate_response.report.v1",
        "spec": SPEC,
        "events": events,
        "summary": summarize(events),
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
