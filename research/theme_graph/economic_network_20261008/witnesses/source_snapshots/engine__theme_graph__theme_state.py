"""Shadow-only, generation-bound ThemeState composition over qualified owner receipts.

This leaf owns no graph/PIT/identity/rights selection, store, writer, scheduler or
financial authority. Callers inject already-resolved owner queries. Hashes prove
document integrity, not source authentication or entitlement. Publication and
actual owner adapter qualification remain separate acceptance gates.

The sole filesystem read is the checked-in schema, following existing graph
document consumers. Composition and reads have no ambient clock or mutable I/O.
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

import jsonschema

from engine.theme_graph.identity import local_theme_node_id, theme_node_id

SCHEMA = "theme_state/v1"
READ_SCHEMA = "gmi.theme_state_read/v1"
AUTHORITY = {
    "is_context_only": True, "may_rank": False, "may_gate": False,
    "may_size": False, "may_escalate": False, "may_trade": False, "may_publish": False,
}
ROLES = ("ontology", "identity", "membership", "rights", "eligibility")
STATE_MAX_AGE_HOURS = 30
LIMITATIONS = [
    "Shadow source only: no publication, financial authority or production qualification.",
    "Injected receipt hashes prove document integrity, not source authentication or rights grants.",
    "Identity, membership, ontology, rights and measurement admission remain with their existing owners.",
    "Date-only knowledge cannot establish availability at a historical instant on the same UTC date.",
    "Legacy observations/history retain their original meaning and qualification; no retrospective relabeling.",
]
_CLOCK = re.compile(r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2}))?$")


def canonical_sha256(value: Any) -> str:
    """Canonical-content digest; distinct from an immutable file-byte receipt."""
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def _validator():
    path = Path(__file__).resolve().parents[2] / "contracts/theme_graph/theme_state.v1.schema.json"
    return jsonschema.Draft202012Validator(json.loads(path.read_text(encoding="utf-8")))


def _clock(value: str) -> tuple[dt.datetime, bool]:
    if not isinstance(value, str) or not _CLOCK.fullmatch(value):
        raise ValueError("invalid or unzoned clock")
    if len(value) == 10:
        date = dt.date.fromisoformat(value)
        return dt.datetime.combine(date, dt.time(), tzinfo=dt.timezone.utc), True
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(dt.timezone.utc), False


def _proven_by(value: str, cutoff: str) -> bool:
    """Date-only means an unknown instant during that day, never midnight certainty."""
    stamp, date_only = _clock(value)
    end, cutoff_date = _clock(cutoff)
    if date_only:
        return stamp.date() < end.date()
    if cutoff_date:
        # Inclusive date cutoff is only the beginning of its unknown interval.
        return stamp < end
    return stamp <= end


def _definitely_after(left: str, right: str) -> bool:
    """Reject impossible order, retaining uncertainty inside a date-only interval."""
    first, _ = _clock(left)
    last, last_date = _clock(right)
    return first >= last + dt.timedelta(days=1) if last_date else first > last


def _clock_reasons(receipt: Mapping[str, Any], effective_at: str, known_at: str) -> list[str]:
    source_effective, _ = _clock(receipt["effective_at"])
    requested_effective, effective_date = _clock(effective_at)
    # Effective dates denote owner-declared sessions. Compare calendar labels
    # without pretending they are measurement instants.
    if effective_date:
        future_effective = source_effective.date() > requested_effective.date()
    else:
        future_effective = source_effective > requested_effective
    reasons = ["SOURCE_EFFECTIVE_FUTURE"] if future_effective else []
    for name in ("known_at", "available_at", "recorded_at"):
        if not _proven_by(receipt[name], known_at):
            source, date_only = _clock(receipt[name])
            cutoff, _ = _clock(known_at)
            reasons.append("KNOWLEDGE_TIME_UNPROVEN" if date_only and source.date() == cutoff.date()
                           else "SOURCE_AFTER_CUTOFF")
    return sorted(set(reasons))


def _validate_receipt(receipt: Mapping[str, Any], *, subject_id: str | None = None,
                      graph_generation_id: str | None = None,
                      owner_generations: Mapping[str, str] | None = None,
                      query: Mapping[str, str] | None = None) -> None:
    validator = jsonschema.Draft202012Validator(_validator().schema["$defs"]["receipt"])
    try:
        validator.validate(receipt)
    except jsonschema.ValidationError as exc:
        raise ValueError("invalid owner receipt") from exc
    for name in ("effective_at", "known_at", "available_at", "recorded_at"):
        _clock(receipt[name])
    for name in ("effective_at", "known_at"):
        _clock(receipt["query"][name])
    if (_definitely_after(receipt["available_at"], receipt["known_at"]) or
            _definitely_after(receipt["known_at"], receipt["recorded_at"])):
        raise ValueError("owner availability/knowledge/recording chronology invalid")
    if canonical_sha256(receipt["payload"]) != receipt["sha256"]:
        raise ValueError("owner payload digest mismatch")
    if subject_id is not None and receipt["subject_id"] != subject_id:
        raise ValueError("owner subject identity mismatch")
    if graph_generation_id is not None and receipt["graph_generation_id"] != graph_generation_id:
        raise ValueError("owner graph generation mismatch")
    if owner_generations is not None and owner_generations.get(receipt["owner"]) != receipt["generation_id"]:
        raise ValueError("owner source generation mismatch")
    if query is not None and receipt["query"] != query:
        raise ValueError("owner query mismatch; latest is not an as-known query")
    if (receipt["availability"] == "UNAVAILABLE") != (receipt["payload"] is None):
        raise ValueError("owner unavailable status disagrees with payload")


def _eligibility(receipt: Mapping[str, Any] | None, reasons: Sequence[str]) -> dict:
    unqualified = {"status": "NOT_QUALIFIED", "policy_revision": None, "reason_codes": ["D2E_UNSEALED"]}
    if receipt is None or receipt["availability"] != "AVAILABLE":
        return unqualified
    payload = receipt["payload"]
    if not isinstance(payload, Mapping) or payload.get("status") not in {"QUALIFIED", "INELIGIBLE", "NOT_QUALIFIED"}:
        return unqualified
    status, policy = payload["status"], payload.get("policy_revision")
    supplied_reasons = payload.get("reason_codes", [])
    if not isinstance(supplied_reasons, list) or any(not isinstance(r, str) or not r for r in supplied_reasons):
        raise ValueError("invalid eligibility owner reasons")
    if status in {"QUALIFIED", "INELIGIBLE"} and (not isinstance(policy, str) or not policy):
        return unqualified
    if reasons:
        return {"status": "NOT_QUALIFIED", "policy_revision": policy,
                "reason_codes": sorted(set(supplied_reasons) | set(reasons))}
    return {"status": status, "policy_revision": policy,
            "reason_codes": sorted(set(supplied_reasons)) or (["D2E_UNSEALED"] if status == "NOT_QUALIFIED" else [])}


def _subject(raw: Mapping[str, Any], *, graph_generation_id: str,
             owner_generations: Mapping[str, str], query: Mapping[str, str]) -> dict:
    keys = {"node_id", "kind", "name_en", "name_zh", "source_family", "native_id",
            "owners", "observations", "canonical_aggregation"}
    if not isinstance(raw, Mapping) or set(raw) != keys:
        raise ValueError("closed subject input keys required")
    node = raw["node_id"]
    canonical = raw["kind"] == "canonical_theme"
    if canonical:
        if not isinstance(node, str) or (not node.startswith("theme:") or node != theme_node_id(node[6:])) or raw["source_family"] is not None or raw["native_id"] is not None:
            raise ValueError("canonical subject identity invalid")
    elif raw["kind"] == "local_theme":
        if not isinstance(node, str) or not isinstance(raw["source_family"], str) or not isinstance(raw["native_id"], str) or node != local_theme_node_id(raw["source_family"], raw["native_id"]) or node != "ltheme:" + raw["source_family"] + ":" + raw["native_id"]:
            raise ValueError("local subject identity invalid")
    else:
        raise ValueError("unsupported subject kind")
    owners = raw["owners"]
    if not isinstance(owners, Mapping) or set(owners) != set(ROLES):
        raise ValueError("closed owner roles required")
    reasons: list[str] = []
    for role in ROLES:
        receipt = owners[role]
        if receipt is None:
            if role != "eligibility":
                reasons.append(role.upper() + "_UNAVAILABLE")
            continue
        _validate_receipt(receipt, subject_id=node, graph_generation_id=graph_generation_id,
                          owner_generations=owner_generations, query=query)
        if role != "eligibility":
            if receipt["availability"] == "UNAVAILABLE":
                reasons.append(role.upper() + "_UNAVAILABLE")
            reasons.extend(_clock_reasons(receipt, **query))
    ontology = owners["ontology"]
    mapping = {"state": "SUBJECT_IS_CANONICAL" if canonical else "UNMAPPED", "theme_node_ids": []}
    if ontology is not None and ontology["availability"] != "UNAVAILABLE":
        payload = ontology["payload"]
        supplied = payload.get("canonical_mapping") if isinstance(payload, Mapping) else None
        if not isinstance(supplied, Mapping) or set(supplied) != {"state", "theme_node_ids"}:
            reasons.append("ONTOLOGY_INPUT_INVALID")
        else:
            mapping = copy.deepcopy(supplied)
    destinations = mapping["theme_node_ids"]
    if not isinstance(destinations, list) or any(not isinstance(n, str) or not n.startswith("theme:") or n != theme_node_id(n[6:]) for n in destinations) or len(destinations) != len(set(destinations)):
        raise ValueError("invalid canonical mapping destinations")
    if mapping["state"] == "MAPPED" and not destinations:
        raise ValueError("mapped subject requires canonical destinations")
    if mapping["state"] == "SUBJECT_IS_CANONICAL" and destinations:
        raise ValueError("canonical subject does not redirect its identity")
    if mapping["state"] == "SUBJECT_IS_CANONICAL" and not canonical:
        raise ValueError("local cannot overwrite canonical identity")
    if canonical and mapping["state"] != "SUBJECT_IS_CANONICAL":
        raise ValueError("canonical mapping status invalid")
    if mapping["state"] == "UNMAPPED" and mapping["theme_node_ids"]:
        raise ValueError("unmapped identity has canonical destinations")
    identity = owners["identity"]
    if identity is not None and (not isinstance(identity["payload"], Mapping) or identity["payload"].get("status") != "RESOLVED"):
        reasons.append("IDENTITY_NOT_RESOLVED")
    membership = owners["membership"]
    if membership is not None and membership["availability"] != "UNAVAILABLE":
        payload = membership["payload"]
        counts = [payload.get(k) for k in ("declared_count", "eligible_count", "observed_count")] if isinstance(payload, Mapping) else []
        if (not isinstance(payload, Mapping) or payload.get("status") != membership["availability"]
                or not isinstance(payload.get("members"), list)
                or len(counts) != 3 or any(type(c) is not int or c < 0 for c in counts)
                or not counts[0] >= counts[1] >= counts[2]):
            reasons.append("MEMBERSHIP_INPUT_INVALID")
        elif membership["availability"] == "VALID_EMPTY" and (payload["members"] or counts[1] or counts[2]):
            reasons.append("MEMBERSHIP_EMPTY_ADMISSION_CONFLICT")
        elif membership["availability"] == "AVAILABLE" and not payload["members"]:
            reasons.append("MEMBERSHIP_EMPTY_NOT_ADMITTED")
    rights = owners["rights"]
    if rights is None or not isinstance(rights["payload"], Mapping) or rights["payload"].get("allowed") is not True or rights["payload"].get("purpose") != "research_internal":
        reasons.append("RIGHTS_NOT_ADMITTED")
    observations = copy.deepcopy(raw["observations"])
    if not isinstance(observations, Mapping):
        raise ValueError("observations must be named object")
    for observation in observations.values():
        coverage = observation.get("coverage", {})
        if (type(coverage.get("declared")) is not int or type(coverage.get("observed")) is not int
                or not 0 <= coverage["observed"] <= coverage["declared"]):
            raise ValueError("observation coverage exceeds admitted declared population")
        for receipt in observation.get("source_receipts", []):
            _validate_receipt(receipt, subject_id=node, graph_generation_id=graph_generation_id,
                              owner_generations=owner_generations, query=query)
        if not observation.get("source_receipts"):
            raise ValueError("observation requires source receipt")
        if observation["presence"] == "VALID_EMPTY" and observation["null_reason"] is not None:
            raise ValueError("valid empty is an admitted value, not an unavailable null")
        if observation["presence"] == "POSITIVE" and observation["value"] is None:
            raise ValueError("null observation requires typed presence and reason")
        if observation["presence"] in {"UNAVAILABLE", "INVALID"} and observation["value"] is not None:
            raise ValueError("unavailable observation cannot carry asserted value")
        if observation["presence"] in {"UNAVAILABLE", "INVALID"} and not observation["null_reason"]:
            raise ValueError("unavailable observation requires typed null")
        observation["freshness"] = _freshness(observation["source_receipts"], query["known_at"],
                                              observation["freshness_policy"]["max_age_hours"])
        source_reasons = sorted(set(r for receipt in observation["source_receipts"]
                                    for r in _clock_reasons(receipt, **query)))
        if any(r["availability"] == "UNAVAILABLE" for r in observation["source_receipts"]):
            observation.update(presence="UNAVAILABLE", value=None, null_reason="OWNER_UNAVAILABLE")
        if source_reasons:
            observation["presence"], observation["freshness"], observation["value"] = "UNAVAILABLE", "FUTURE" if "SOURCE_EFFECTIVE_FUTURE" in source_reasons else "UNKNOWN", None
            observation["null_reason"] = source_reasons[0]
    aggregation = {"status": "NOT_APPLICABLE", "receipt": None, "reason_codes": []}
    aggregate = raw["canonical_aggregation"]
    if canonical:
        aggregation = {"status": "UNAVAILABLE", "receipt": None,
                       "reason_codes": ["CANONICAL_AGGREGATION_UNSUPPLIED"]}
        if aggregate is not None:
            _validate_receipt(aggregate, subject_id=node, graph_generation_id=graph_generation_id,
                              owner_generations=owner_generations, query=query)
            temporal = _clock_reasons(aggregate, **query)
            payload = aggregate["payload"]
            if aggregate["availability"] == "AVAILABLE" and isinstance(payload, Mapping) and payload.get("method") and not temporal:
                aggregation = {"status": "SUPPLIED", "receipt": copy.deepcopy(aggregate), "reason_codes": []}
            else:
                aggregation["receipt"] = copy.deepcopy(aggregate)
                aggregation["reason_codes"] = temporal or ["CANONICAL_AGGREGATION_UNAVAILABLE"]
    elif aggregate is not None:
        raise ValueError("local state cannot accept canonical aggregation")
    eligibility_receipt = owners["eligibility"]
    eligibility_reasons = list(reasons)
    if eligibility_receipt is not None:
        eligibility_reasons.extend(_clock_reasons(eligibility_receipt, **query))
    result = {key: copy.deepcopy(raw[key]) for key in
              ("node_id", "kind", "name_en", "name_zh", "source_family", "native_id")}
    result.update(mapping=mapping, availability="UNAVAILABLE" if reasons else "AVAILABLE",
                  reason_codes=sorted(set(reasons)), eligibility=_eligibility(eligibility_receipt, eligibility_reasons),
                  owner_receipts=copy.deepcopy(owners), observations=observations, aggregation=aggregation)
    return result


def _state_digest(artifact: Mapping[str, Any]) -> str:
    return canonical_sha256({k: v for k, v in artifact.items() if k not in {"generation_id", "state_sha256"}})


def validate_state(artifact: Mapping[str, Any]) -> None:
    """Validate closed wire, integrity, owner joins, typed missingness and authority."""
    try:
        _validator().validate(artifact)
        for field in ("effective_at", "known_at", "generated_at"):
            _clock(artifact[field])
        if _clock(artifact["generated_at"])[1]:
            raise ValueError("state generation clock must be precise")
        if not _proven_by(artifact["known_at"], artifact["generated_at"]):
            raise ValueError("state knowledge cutoff exceeds build instant")
        digest = _state_digest(artifact)
        if digest != artifact["state_sha256"] or digest[:32] != artifact["generation_id"]:
            raise ValueError("state generation digest mismatch")
        subjects = artifact["subjects"]
        identities = [s["node_id"] for s in subjects]
        if artifact["subject_count"] != len(subjects) or identities != sorted(set(identities)):
            raise ValueError("duplicate or unordered subject identities")
        query = {k: artifact[k] for k in ("effective_at", "known_at")}
        for result in subjects:
            raw = {k: copy.deepcopy(result[k]) for k in
                   ("node_id", "kind", "name_en", "name_zh", "source_family", "native_id", "observations")}
            raw["owners"] = result["owner_receipts"]
            raw["canonical_aggregation"] = result["aggregation"]["receipt"]
            rebuilt = _subject(raw, graph_generation_id=artifact["graph_generation_id"],
                               owner_generations=artifact["owner_generations"], query=query)
            if rebuilt != result:
                raise ValueError("state disagrees with owner receipt semantics")
            if result["eligibility"]["status"] == "QUALIFIED" and result["availability"] != "AVAILABLE":
                raise ValueError("unavailable subject cannot qualify")
        correction = artifact["correction"]
        if correction is not None:
            if (correction["generation_id"] != correction["state_sha256"][:32]
                    or _clock(correction["generated_at"])[1]
                    or not _proven_by(correction["known_at"], correction["generated_at"])
                    or not _proven_by(correction["generated_at"], artifact["generated_at"])):
                raise ValueError("correction identity or emission lineage invalid")
        if correction is not None and (correction["generation_id"] == artifact["generation_id"] or
                correction["effective_at"] != artifact["effective_at"] or
                not _proven_by(correction["known_at"], artifact["known_at"]) or
                _clock(correction["known_at"])[0] == _clock(artifact["known_at"])[0]):
            raise ValueError("correction must reference an earlier-known same-effective generation")
    except (jsonschema.ValidationError, KeyError, TypeError, OverflowError) as exc:
        raise ValueError("invalid theme_state/v1") from exc


def compose_state(subject_inputs: Sequence[Mapping[str, Any]], *, graph_generation_id: str,
                  owner_generations: Mapping[str, str], effective_at: str, known_at: str,
                  generated_at: str, previous: Mapping[str, Any] | None = None) -> dict:
    """Compose a deterministic shadow generation; selection/admission stays in owners."""
    query = {"effective_at": effective_at, "known_at": known_at}
    for value in (effective_at, known_at, generated_at):
        _clock(value)
    if _clock(generated_at)[1]:
        raise ValueError("state generation clock must be precise")
    subjects = [_subject(raw, graph_generation_id=graph_generation_id,
                         owner_generations=owner_generations, query=query) for raw in subject_inputs]
    identities = [s["node_id"] for s in subjects]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate subject identity")
    correction = None
    if previous is not None:
        validate_state(previous)
        if previous["effective_at"] != effective_at or not _proven_by(previous["known_at"], known_at) or _clock(previous["known_at"])[0] == _clock(known_at)[0]:
            raise ValueError("correction requires strictly later knowledge at same effective time")
        if not _proven_by(previous["generated_at"], generated_at):
            raise ValueError("previous emission is later than correction emission")
        correction = {k: previous[k] for k in ("generation_id", "state_sha256", "effective_at", "known_at", "generated_at")}
    artifact = {"schema": SCHEMA, "mode": "shadow", "graph_generation_id": graph_generation_id,
                "owner_generations": dict(sorted(owner_generations.items())), **query,
                "generated_at": generated_at, "authority": dict(AUTHORITY),
                "subject_count": len(subjects), "subjects": sorted(subjects, key=lambda s: s["node_id"]),
                "correction": correction, "limitations": list(LIMITATIONS)}
    digest = _state_digest(artifact)
    artifact.update(generation_id=digest[:32], state_sha256=digest)
    validate_state(artifact)
    return artifact


def _freshness(receipts: Sequence[Mapping[str, Any]], known_at: str, max_age_hours: float) -> str:
    cutoff, _ = _clock(known_at)
    states = []
    for receipt in receipts:
        stamp, date_only = _clock(receipt["effective_at"])
        oldest_age = (cutoff - stamp).total_seconds() / 3600
        youngest_age = oldest_age - (24 if date_only else 0)
        states.append("FUTURE" if oldest_age < 0 else
                      "STALE" if youngest_age > max_age_hours else
                      "UNKNOWN" if oldest_age > max_age_hours or youngest_age < 0 else "FRESH")
    return next((state for state in ("FUTURE", "STALE", "UNKNOWN") if state in states), "FRESH")


def adapt_recommended_overlap(narrative_receipt: Mapping[str, Any], membership_receipt: Mapping[str, Any],
                              *, basket_id: str, effective_at: str, known_at: str,
                              max_age_hours: float = STATE_MAX_AGE_HOURS,
                              owner_policy_revision: str = "state-default-30h") -> dict:
    """Read real numeric legs/recommended[] and owner-resolved members[].

    The membership receipt must already represent the owner's exact valid/known
    query. This adapter never selects added/removed rows, resolves aliases or
    derives whole-cluster membership from the top-five recommendation subset.
    """
    query = {"effective_at": effective_at, "known_at": known_at}
    receipts = [narrative_receipt, membership_receipt]
    for receipt in receipts:
        _validate_receipt(receipt, query=query)
    if not isinstance(max_age_hours, (int, float)) or isinstance(max_age_hours, bool) or not math.isfinite(max_age_hours) or max_age_hours <= 0:
        raise ValueError("owner freshness budget must be finite and positive")
    out = {"owner": narrative_receipt["owner"],
           "schema": "gmi.forming_narrative_recommended_ticker_overlap/v1",
           "presence": "UNAVAILABLE", "freshness": _freshness(receipts, known_at, max_age_hours),
           "value": None, "null_reason": None, "units": "boolean", "window": "source_snapshot",
           "coverage": {"declared": 0, "observed": 0, "basis": "top_5_entry_quality_subset"},
           "conflicts": [], "source_receipts": copy.deepcopy(receipts),
           "freshness_policy": {"max_age_hours": max_age_hours,
                                "owner_policy_revision": owner_policy_revision}}

    def refusal(presence, reason):
        out.update(presence=presence, null_reason=reason)
        return out

    if any(r["availability"] == "UNAVAILABLE" for r in receipts):
        return refusal("UNAVAILABLE", "OWNER_UNAVAILABLE")
    if out["freshness"] == "FUTURE":
        return refusal("UNAVAILABLE", "SOURCE_EFFECTIVE_FUTURE")
    clock_reasons = sorted(set(reason for r in receipts for reason in _clock_reasons(r, **query)))
    if clock_reasons:
        out["freshness"] = "UNKNOWN"
        return refusal("UNAVAILABLE", clock_reasons[0])
    ne, mb = narrative_receipt["payload"], membership_receipt["payload"]
    if not isinstance(mb, Mapping) or mb.get("basket_id") != basket_id or not isinstance(mb.get("members"), list):
        return refusal("INVALID", "MALFORMED_MEMBERSHIP")
    members = mb["members"]
    if not members and membership_receipt["availability"] != "VALID_EMPTY":
        return refusal("UNAVAILABLE", "MEMBERSHIP_EMPTY_NOT_ADMITTED")
    if members and membership_receipt["availability"] == "VALID_EMPTY":
        return refusal("INVALID", "EMPTY_ADMISSION_CONFLICT")
    if any(not isinstance(row, Mapping) or not isinstance(row.get("ticker"), str) or not row["ticker"] or "added" in row or "removed" in row for row in members):
        return refusal("INVALID", "MEMBERSHIP_REQUIRES_RESOLVED_OWNER_QUERY")
    member_ids = {row["ticker"] for row in members}
    if len(member_ids) != len(members):
        return refusal("INVALID", "DUPLICATE_OWNER_MEMBER")
    if not isinstance(ne, Mapping) or not isinstance(ne.get("narratives"), list):
        return refusal("INVALID", "MALFORMED_NARRATIVE")
    narratives = ne["narratives"]
    if narratives and narrative_receipt["availability"] == "VALID_EMPTY":
        return refusal("INVALID", "EMPTY_ADMISSION_CONFLICT")
    if not narratives and narrative_receipt["availability"] != "VALID_EMPTY":
        return refusal("UNAVAILABLE", "EMPTY_NOT_ADMITTED")
    matched, signatures, recommended = set(), set(), set()
    for row in narratives:
        if not isinstance(row, Mapping) or not isinstance(row.get("legs"), Mapping) or not isinstance(row.get("recommended"), list) or not isinstance(row.get("signature"), str):
            return refusal("INVALID", "MALFORMED_NARRATIVE")
        if not row["legs"] or any(type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1 for value in row["legs"].values()) or len(row["recommended"]) > 5:
            return refusal("INVALID", "MALFORMED_NARRATIVE")
        for entry in row["recommended"]:
            if not isinstance(entry, Mapping) or not isinstance(entry.get("ticker"), str) or not entry["ticker"]:
                return refusal("INVALID", "MALFORMED_NARRATIVE")
            ticker = entry["ticker"]
            recommended.add(ticker)
            if ticker in member_ids:
                matched.add(ticker)
                signatures.add(row["signature"])
    out["coverage"].update(declared=len(member_ids), observed=len(member_ids & recommended))
    out.update(presence="POSITIVE" if matched else "VALID_EMPTY", null_reason=None,
               value={"has_overlap": bool(matched), "matched_tickers": sorted(matched),
                      "narrative_signatures": sorted(signatures),
                      "coverage_basis": "top_5_entry_quality_subset"})
    return out


def read_theme_state(artifact: Mapping[str, Any], subject_id: str, *, effective_at: str,
                     known_at: str, expected_generation_id: str | None = None) -> dict:
    """Exact generation read; never resolve latest or substitute later-known state."""
    validate_state(artifact)
    _clock(effective_at)
    _clock(known_at)
    result = {"schema": READ_SCHEMA, "status": "UNAVAILABLE", "reason_codes": [],
              "subject_id": subject_id, "generation_id": artifact["generation_id"],
              "state_sha256": artifact["state_sha256"], "state_generated_at": artifact["generated_at"],
              "effective_at": effective_at,
              "known_at": known_at, "subject": None}
    reasons = []
    if expected_generation_id is not None and expected_generation_id != artifact["generation_id"]:
        reasons.append("GENERATION_MISMATCH")
    if effective_at != artifact["effective_at"]:
        reasons.append("EFFECTIVE_TIME_MISMATCH")
    if not _proven_by(artifact["known_at"], known_at):
        reasons.append("STATE_AFTER_CUTOFF")
    if not _proven_by(artifact["generated_at"], known_at):
        reasons.append("STATE_NOT_YET_EMITTED")
    known, _ = _clock(known_at)
    built, _ = _clock(artifact["generated_at"])
    if (known - built).total_seconds() > STATE_MAX_AGE_HOURS * 3600:
        reasons.append("STATE_STALE")
    subject = next((s for s in artifact["subjects"] if s["node_id"] == subject_id), None)
    if subject is None:
        reasons.append("SUBJECT_NOT_FOUND")
    elif subject["availability"] != "AVAILABLE":
        reasons.extend(subject["reason_codes"])
    if reasons:
        result["reason_codes"] = sorted(set(reasons))
        return result
    result["subject"] = copy.deepcopy(subject)
    result["status"] = "QUALIFIED" if subject["eligibility"]["status"] == "QUALIFIED" else "DESCRIPTIVE"
    return result


def legacy_projection(artifact: Mapping[str, Any]) -> dict:
    """In-memory canonical compatibility only; never relabel historical v1 rows."""
    validate_state(artifact)
    themes, stale, legacy_ids = [], [], set()
    for subject in artifact["subjects"]:
        if subject["kind"] != "canonical_theme":
            continue
        observation = subject["observations"].get("legacy_context")
        if observation is None or observation["presence"] not in {"POSITIVE", "VALID_EMPTY"} or not isinstance(observation["value"], Mapping):
            raise ValueError("canonical legacy_context unavailable: compatibility needs owner acceptance")
        value = observation["value"]
        if not isinstance(value.get("theme_id"), str) or not value["theme_id"]:
            raise ValueError("explicit legacy identity required; do not infer from graph label")
        if value["theme_id"] in legacy_ids:
            raise ValueError("duplicate legacy theme identity")
        if theme_node_id(value["theme_id"]) != subject["node_id"]:
            raise ValueError("legacy identity lacks exact incumbent crosswalk equivalence")
        legacy_ids.add(value["theme_id"])
        themes.append(copy.deepcopy(value))
        if observation["freshness"] != "FRESH" or subject["availability"] != "AVAILABLE":
            stale.append(subject["node_id"] + ": " + observation["freshness"])
    return {"schema": "neuralweb.theme_state.v1", "as_of": artifact["effective_at"][:10],
            "generated_at": artifact["generated_at"], "authority": dict(AUTHORITY),
            "n_themes": len(themes), "themes": themes, "stale_legs": stale,
            "lineage": {"source_schema": SCHEMA, "generation_id": artifact["generation_id"],
                        "state_sha256": artifact["state_sha256"], "mode": "shadow",
                        "historical_reclassification": False}}
