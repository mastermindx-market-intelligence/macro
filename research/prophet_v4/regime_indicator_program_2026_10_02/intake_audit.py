"""Offline diagnostic adapter for Prophet research intake; no execution authority.

Consumes already-corrected rows and declared owner evidence. It is not a ledger,
calendar, regime classifier, backtester, trial registry or promotion gate. Upstream
contracts remain authoritative. A passing check means internally consistent input,
not verified provenance or predictive value.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from hashlib import sha256
import json
import math
from statistics import mean, median
from typing import Any, Iterable, Mapping

SCHEMA = "prophet.regime_indicator_intake_audit/v1"
AUTHORITY = {key: False for key in ("rank", "entry", "size", "trade", "promotion")}


def digest(value: Any) -> str:
    """Hash strict JSON: non-finite values must never masquerade as observations."""
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode()).hexdigest()


def _number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("return must be a finite number or explicit null")
    if not math.isfinite(value):
        raise ValueError("non-finite return")
    return float(value)


def _entry_month(row: Mapping[str, Any]) -> str:
    value = row.get("entry_date")
    if value is None:
        return "unknown"
    if not isinstance(value, str):
        raise ValueError("entry_date must be an ISO date or null")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("entry_date must use YYYY-MM-DD")
    return value[:7]


def _stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [_number(row.get("stock_result_pct")) for row in rows]
    values = [x for x in values if x is not None]
    winners, losers = [x for x in values if x > 0], [x for x in values if x < 0]
    return {
        "closed_rows": len(rows), "return_observed": len(values),
        "return_missing": len(rows) - len(values),
        "positive": len(winners), "negative": len(losers),
        "flat": sum(x == 0 for x in values),
        "positive_fraction": len(winners) / len(values) if values else None,
        "mean_stock_return_pct": mean(values) if values else None,
        "median_stock_return_pct": median(values) if values else None,
        "mean_positive_pct": mean(winners) if winners else None,
        "mean_negative_pct": mean(losers) if losers else None,
        "outcomes": dict(sorted(Counter(str(r.get("outcome")) for r in rows).items())),
    }


def summarize_effective_ledger(
    effective_rows: Iterable[Mapping[str, Any]],
    quarantined_ids: Iterable[str],
    reconstructed_ids: Iterable[str],
    *, source_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Describe the existing owner's corrected projection, never change it.

    Caller obtains reconstructed_ids through prophet_integrity.is_reconstructed.
    Lack of that marker is NOT proof of live delivery. No corrections or return
    calculations are implemented here, and the source ledger is never written.
    """
    rows = [dict(row) for row in effective_rows]
    ids = [r.get("id") for r in rows]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("unique, nonempty canonical plan ids required")
    quarantine, reconstructed = set(quarantined_ids), set(reconstructed_ids)
    if not quarantine.issubset(ids) or not reconstructed.issubset(ids):
        raise ValueError("disposition references a plan absent from the projection")
    allowed = {"NO_ENTRY", "T1_HIT", "T2_HIT", "INVALIDATED", "EXPIRED", "CLOSED_EARLY"}
    if any(row.get("outcome") not in allowed for row in rows):
        raise ValueError("unrecognized terminal outcome; review owner schema")
    kept = [r for r in rows if r["id"] not in quarantine]
    no_entry = [r for r in kept if r["outcome"] == "NO_ENTRY"]
    entered = [r for r in kept if r["outcome"] != "NO_ENTRY"]
    reconstructed_rows = [r for r in entered if r["id"] in reconstructed]
    unmarked = [r for r in entered if r["id"] not in reconstructed]
    cohorts: dict[str, list[dict[str, Any]]] = {}
    for row in unmarked:
        cohorts.setdefault(_entry_month(row), []).append(row)
    return {
        "schema": SCHEMA, "authority": dict(AUTHORITY),
        "source_identity": dict(source_identity),
        "counts": {"raw_projection": len(rows), "quarantined": len(quarantine),
                   "effective": len(kept), "no_entry": len(no_entry), "entered": len(entered)},
        "entered": _stats(entered), "reconstructed_entered": _stats(reconstructed_rows),
        "not_marked_reconstructed_entered": _stats(unmarked),
        "entry_month_closed_only": {k: _stats(v) for k, v in sorted(cohorts.items())},
        "limitations": [
            "Closed-plan diagnostic, not a portfolio return or verified delivered-pick track record.",
            "Recent entry cohorts are right-censored; early failures can close before later winners.",
            "Missing reconstruction marker does not prove contemporaneous publication or delivery.",
            "No benchmark, cost, strategy-era, equal-horizon or open-plan adjustment is inferred.",
            "T1_HIT/T2_HIT use the owner first-trigger rule, not eventual maximum favorable excursion.",
        ],
    }


def _instant(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timezone-aware timestamp required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("date-only or timezone-naive availability cannot certify a decision cut")
    return parsed


def audit_information_cut(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Check declared owner timing without inventing intraday publication times.

    known_at is the later of source publication and ingestion/recording. Window
    qualification belongs to the source owner; this adapter never infers it from
    a label or from today's revised historical values.
    """
    checks = []
    seen: set[str] = set()
    for row in rows:
        rid = row.get("id")
        if not isinstance(rid, str) or not rid or rid in seen:
            raise ValueError("unique evidence id required")
        seen.add(rid)
        reasons = []
        try:
            decision, published, captured = (_instant(row.get(k)) for k in
                                             ("decision_at", "published_at", "captured_at"))
            known = max(published, captured)
            if known > decision:
                reasons.append("future_information")
        except (ValueError, TypeError):
            known = None
            reasons.append("unresolved_information_clock")
        if row.get("vintage_qualification") != "owner_verified":
            reasons.append("vintage_not_qualified")
        if row.get("lookback_qualification") != "owner_verified":
            reasons.append("lookback_not_qualified")
        checks.append({"id": rid, "declared_known_at": known.isoformat() if known else None,
                       "consistent": not reasons, "reasons": reasons})
    return {"schema": SCHEMA, "authority": dict(AUTHORITY), "checks": checks,
            "consistent": bool(checks) and all(c["consistent"] for c in checks),
            "note": "Declared-contract check only; owner receipts still require independent verification."}


# G/A/K/D and label/evaluation identity are compared separately, not rolled into a score.
IDENTITY = ("population_digest", "decision_cut_digest", "target_definition",
            "target_horizon", "target_horizon_unit", "cost_definition",
            "evaluation_partition", "information_vintage_policy")
CLOCK = ("instrument_plane", "feed", "session", "timezone", "anchor", "adjustment")


def _bar_policy(item: Mapping[str, Any]) -> str | None:
    # Preserve the original complete-only manifest. A live provisional view must
    # instead declare an independently qualified, decision-cut-bound snapshot.
    explicit = item.get("bar_observation_policy")
    if explicit is not None:
        return explicit
    return "completed_only" if item.get("completed_bars_only") is True else None


def audit_comparison(left: Mapping[str, Any], right: Mapping[str, Any], *,
                     contrast: str) -> dict[str, Any]:
    """Audit paired-owner manifests. It neither reads outcomes nor selects a winner.

    `grain_memory_matched` means a grain-only comparison. `policy_bundle` allows
    differing clocks/kernels but cannot be reported as a pure timeframe effect.
    For a pure grain comparison the caller supplies an exact declared memory-law
    identity, not a rounded nominal period count. Complete-only histories and
    qualified as-of provisional snapshots are distinct valid observation policies;
    a finalized full-history stream never substitutes for the latter.
    """
    if contrast not in {"grain_memory_matched", "kernel", "session", "policy_bundle"}:
        raise ValueError("unknown contrast")
    reasons = []
    for side, item in (("left", left), ("right", right)):
        for key in (*IDENTITY, *CLOCK, "grain", "kernel_memory_law", "species_id", "selection_scope"):
            if key not in item or item[key] is None or item[key] == "":
                reasons.append(f"{side}:missing:{key}")
        if item.get("selection_scope") == "per_security_outcome_argmax":
            reasons.append(f"{side}:forbidden_outcome_audition")
        elif item.get("selection_scope") not in {"frozen_family", "frozen_policy"}:
            reasons.append(f"{side}:unqualified_selection_scope")
        horizon = item.get("target_horizon")
        if type(horizon) is not int or horizon <= 0:
            reasons.append(f"{side}:invalid_target_horizon")
        if item.get("target_horizon_unit") not in {"exchange_sessions", "clock_hours", "calendar_days"}:
            reasons.append(f"{side}:unqualified_horizon_unit")
        policy = _bar_policy(item)
        if policy == "completed_only":
            if item.get("completed_bars_only") is not True:
                reasons.append(f"{side}:unqualified_bar_completion")
        elif policy == "asof_snapshot":
            if type(item.get("completed_bars_only")) is not bool:
                reasons.append(f"{side}:unqualified_bar_completion")
            if item.get("asof_snapshot_qualified") is not True:
                reasons.append(f"{side}:unqualified_asof_snapshot")
            if item.get("snapshot_cut_digest") != item.get("decision_cut_digest"):
                reasons.append(f"{side}:asof_snapshot_cut_mismatch")
            receipt = item.get("asof_snapshot_receipt")
            if not isinstance(receipt, str) or not receipt.strip():
                reasons.append(f"{side}:missing_asof_snapshot_receipt")
        else:
            reasons.append(f"{side}:unqualified_bar_observation_policy")
        if item.get("warmup_qualified") is not True:
            reasons.append(f"{side}:unqualified_warmup")
    for key in IDENTITY:
        if left.get(key) != right.get(key):
            reasons.append(f"unpaired:{key}")
    if contrast != "policy_bundle":
        if _bar_policy(left) != _bar_policy(right):
            reasons.append("confounded:bar_observation_policy")
        same = [k for k in CLOCK if contrast != "session" or k not in {"session", "anchor"}]
        if contrast != "kernel":
            same.append("kernel_memory_law")
        if contrast != "grain_memory_matched":
            same.append("grain")
        same.append("species_id")
        for key in same:
            if left.get(key) != right.get(key):
                reasons.append(f"confounded:{key}")
    changed_axis = {"grain_memory_matched": ("grain",),
                    "kernel": ("kernel_memory_law",),
                    "session": ("session", "anchor"),
                    "policy_bundle": (*CLOCK, "grain", "kernel_memory_law", "species_id")}
    changed = any(left.get(k) != right.get(k) for k in changed_axis[contrast])
    if contrast == "policy_bundle":
        changed = changed or _bar_policy(left) != _bar_policy(right)
    if not changed:
        reasons.append("no_declared_treatment_difference")
    if left == right:
        reasons.append("self_comparison")
    return {"schema": SCHEMA, "authority": dict(AUTHORITY), "contrast": contrast,
            "consistent": not reasons, "reasons": reasons,
            "left_digest": digest(dict(left)), "right_digest": digest(dict(right)),
            "note": "Input consistency only; not estimability, statistical significance, parity or promotion."}
