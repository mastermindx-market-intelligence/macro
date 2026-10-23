"""Read-only Navigator consumer of incumbent Market Memory evidence.

No receipt-clock translation, snapshot resolution, nearest lookup, persistence or
new source authenticator. Keep the canonical packet intact internally; the public
view exposes bounded descriptors, not source paths or snapshot references. Reader
construction/entitlement belongs to application composition, never HTTP arguments.
Recorded historical context is not a claim that its values are current or tradable.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from engine.market_navigator import AUTHORITY, HORIZONS, ContractError, _clock
from engine.neuralweb import market_memory as owner

SCHEMA = "market_navigator.memory_evidence/v1"
CHANGE_SCHEMA = "market_navigator.memory_changes/v1"


def _validated(packet: Mapping[str, Any]) -> dict:
    try:
        return deepcopy(owner.validate_as_known_at_context(packet))
    except (ValueError, TypeError, KeyError) as exc:
        raise ContractError("invalid incumbent Market Memory context") from exc


def _feature_view(row: Mapping[str, Any], sources: Mapping[str, dict]) -> dict:
    dependencies = [sources[ref] for ref in row["source_receipt_ids"]]
    # These clocks KEEP the owner's meaning, including availability <= capture.
    clocks = [{key: source[key] for key in
               ("measurement_end", "available_at", "observed_at", "age_at_cutoff_seconds")}
              for source in dependencies]
    scalar = row["unit"] != "snapshot_ref"
    return {"feature_id": row["feature_id"], "domain": row["domain"],
            "status": row["status"], "unit": row["unit"],
            "value": row["value"] if scalar else None,
            "representation": "scalar" if scalar else "retained_reference_not_resolved",
            "feature_observed_at": row["observed_at"], "source_clocks": clocks,
            "pit_basis": row["pit_basis"], "quality": deepcopy(row["quality"]),
            "missing_reason": row["missing_reason"]}


def evidence_view(packet: Mapping[str, Any], *, horizon: str) -> dict:
    """Describe an exact recorded context, without interpreting it as an entry signal.

    This function validates semantics, not source authenticity. Production calls
    must come from read_evidence with the existing trusted application reader.
    No registry entry or scalar is promoted into Navigator condition eligibility.
    """
    if horizon not in HORIZONS:
        raise ContractError("unsupported Navigator horizon")
    clean = _validated(packet)
    sources = {row["receipt_id"]: row for row in clean["source_receipts"]}
    return {"schema": SCHEMA, "status": "recorded_context", "horizon": horizon,
            "context_id": clean["context_id"], "mode": clean["mode"],
            "clocks": deepcopy(clean["clocks"]),
            "domain_coverage": deepcopy(clean["domain_coverage"]),
            "features": [_feature_view(row, sources) for row in clean["feature_receipts"]],
            "condition_eligibility": "not_evaluated",
            "readiness": "research_only", "authority": dict(AUTHORITY)}


def read_evidence(reader: owner.AsKnownAtReader, *, subject: Mapping[str, str],
                  event_time: str, as_known_at: str, horizon: str) -> dict:
    """One exact read; no retries, fabricated availability or nearby-history fallback.

    Reader is an application-supplied capability, not a user-supplied function/path.
    Absence is distinct from unreadable/corrupt/denied data. The unchanged canonical
    packet is retained in this INTERNAL result; only `view` is for rendering after
    the incumbent route has enforced the user's rights and audience.
    """
    from engine.neuralweb import market_memory_pit as pit
    if horizon not in HORIZONS:
        raise ContractError("unsupported Navigator horizon")
    event, cutoff = _clock(event_time), _clock(as_known_at)
    if event > cutoff:
        raise ContractError("event cannot follow the knowledge cutoff")
    if not isinstance(subject, Mapping) or set(subject) != {"subject_id", "instrument_id"}:
        raise ContractError("exact owner subject binding required")
    query_subject = dict(subject)
    if not isinstance(reader, owner.AsKnownAtReader):
        raise ContractError("incumbent AsKnownAtReader required")
    try:
        with pit.bounded_owner_reads(maximum_bytes=8 * 1024 * 1024):
            raw = reader.read_as_known_at(subject=deepcopy(query_subject),
                event_time=event.isoformat().replace("+00:00", "Z"),
                as_known_at=cutoff.isoformat().replace("+00:00", "Z"))
    except pit.MarketMemoryQueryError as exc:
        raise ContractError("invalid incumbent Market Memory query") from exc
    except pit.MarketMemoryContextNotFound:
        reason = "exact_context_absent"
    except PermissionError:
        reason = "source_access_denied"
    except (pit.MarketMemoryPITError, OSError):
        reason = "source_unavailable"
    else:
        clean = _validated(raw)
        if (clean["subject"] != query_subject or
                _clock(clean["clocks"]["event_time"]) != event or
                _clock(clean["clocks"]["as_known_at"]) != cutoff):
            raise ContractError("owner response does not match the exact request")
        if clean["mode"] != "operational_pit":
            raise ContractError("operational read cannot substitute a reconstruction")
        return {"schema": SCHEMA, "source_status": "exact_owner_read",
                "source_context": clean, "view": evidence_view(clean, horizon=horizon),
                "authority": dict(AUTHORITY)}
    return {"schema": SCHEMA, "source_status": reason, "source_context": None,
            "view": {"schema": SCHEMA, "status": reason, "horizon": horizon,
                     "context_id": None, "features": [], "domain_coverage": [],
                     "condition_eligibility": "unavailable",
                     "readiness": "research_only", "authority": dict(AUTHORITY)},
            "authority": dict(AUTHORITY)}


def compare_evidence(before: Mapping[str, Any], after: Mapping[str, Any], *, horizon: str) -> dict:
    """Typed change review of two immutable owner contexts, not a forecast revision.

    No outcome lookup, confidence upgrade, order, save, watcher or history store.
    Reference changes are stated as such: their opaque contents are not interpreted.
    A transform change suppresses numeric comparisons; an exact-query conflict is
    refused rather than accepted as a helpful source update.
    """
    if horizon not in HORIZONS:
        raise ContractError("unsupported Navigator horizon")
    old, new = _validated(before), _validated(after)
    if old["subject"] != new["subject"] or old["mode"] != new["mode"]:
        raise ContractError("comparison requires the same subject and evidence mode")
    oe, ne = (_clock(p["clocks"]["event_time"]) for p in (old, new))
    oc, nc = (_clock(p["clocks"]["as_known_at"]) for p in (old, new))
    if ne < oe or nc < oc:
        raise ContractError("comparison cannot regress the event or knowledge clock")
    if oe == ne and oc == nc and old["context_id"] != new["context_id"]:
        raise ContractError("conflicting evidence for one exact operational query")
    left = {r["feature_id"]: r for r in old["feature_receipts"]}
    right = {r["feature_id"]: r for r in new["feature_receipts"]}
    old_sources = {r["receipt_id"]: r for r in old["source_receipts"]}
    new_sources = {r["receipt_id"]: r for r in new["source_receipts"]}
    changes = []
    for key in sorted(set(left) | set(right)):
        a, b = left.get(key), right.get(key)
        kinds = []
        if a is None or b is None:
            kinds.append("feature_coverage_changed")
        elif a["status"] != b["status"]:
            kinds.append("became_available" if b["status"] == "observed" else "became_unavailable")
        elif a["status"] == "observed":
            if (a["transform_version"], a["unit"]) != (b["transform_version"], b["unit"]):
                kinds.append("method_changed")
            elif a["value"] != b["value"]:
                kinds.append("reference_changed" if b["unit"] == "snapshot_ref" else "recorded_value_changed")
            if a["source_receipt_ids"] != b["source_receipt_ids"]:
                kinds.append("source_evidence_changed")
        if a is not None and b is not None:
            if a["quality"] != b["quality"] or a["pit_basis"] != b["pit_basis"]:
                kinds.append("quality_changed")
            if a["missing_reason"] != b["missing_reason"]:
                kinds.append("missing_reason_changed")
        if kinds:
            changes.append({"feature_id": key, "kinds": kinds,
                "before": _feature_view(a, old_sources) if a is not None else None,
                "after": _feature_view(b, new_sources) if b is not None else None,
                "numeric_comparison_permitted": "method_changed" not in kinds and
                    a is not None and b is not None and a["status"] == b["status"] == "observed" and
                    a["unit"] == b["unit"] != "snapshot_ref"})
    return {"schema": CHANGE_SCHEMA, "horizon": horizon,
            "before_context_id": old["context_id"], "after_context_id": new["context_id"],
            "before_clocks": deepcopy(old["clocks"]), "after_clocks": deepcopy(new["clocks"]),
            "changes": changes, "original_preserved": True,
            "readiness": "research_only", "authority": dict(AUTHORITY)}
