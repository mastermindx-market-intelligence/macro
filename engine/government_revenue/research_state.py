"""Precomputed read-only GRV-FA1 research state; no issuance/evaluation activation.

This initial integration deliberately has no append API. Only the incumbent
serialized publisher may later activate issuance after owner admission and
durable-before-entry acknowledgement. A staging clock cannot supply that proof.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from engine.government_revenue.candidates import is_valid_candidate_queue
from engine.government_revenue.candidate_grader import (
    GRV_FA1, GraderError, _authority, admit, canonical_bytes, cohort_rows,
    load_family_declaration, parse_issuance_log,
)

CONTRACT = "government_revenue.research_state.v1"
MAX_STATE_BYTES = 128 * 1024
FIELDS = frozenset({"contract", "schema_version", "content_id", "authority", "generated_at",
    "as_of", "state", "is_running", "registration", "sources", "issuance", "input_admission",
    "outcomes", "required_next_steps", "limitations"})
SOURCE_PATHS = frozenset({"data/government_revenue/latest.json", "data/government_revenue/workspace.json",
    "data/government_revenue/recipient_entity_graph.json", "data/government_revenue/candidate_queue.json",
    "data/government_revenue/candidate_ledger.jsonl", "data/government_revenue/candidate_projection_state.json",
    "data/government_revenue/candidate_projection_status.json"})
REASON_CODES = frozenset({"owner_admitted_input_shape", "family_mismatch", "authority_not_display",
    "missing_known_at", "mapping_missing", "missing_source_event", "ceiling_change_out_of_family",
    "family_rail_mismatch", "deobligation", "direction_not_positive", "not_exact_linked", "late_discovery"})
NEXT_STEPS = ["Admit immutable source, rights, security and calendar inputs through their existing owner.",
    "Bind actual durable issuance before registered entry through the existing publisher.",
    "Register only genuinely fresh eligible actions; retain historical display/audit records.",
    "Accrue natural horizons and the unchanged registered coverage/independence gates."]
LIMITATIONS = ["Candidate display admission is not forecast issuance.",
    "A staging clock or local source/test proof is not durable issuance acknowledgement.",
    "No proposed DPV3 family is activated or evaluated by this state."]
REFUSALS = ("runtime_source_admission_missing", "durable_before_entry_acknowledgement_missing")


def _clock(value: str) -> datetime:
    if not isinstance(value, str) or len(value) > 64:
        raise GraderError("research state clock is invalid")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise GraderError("research state clock is invalid") from exc
    if result.tzinfo is None:
        raise GraderError("research state clock requires a timezone")
    return result.astimezone(timezone.utc)


def content_id(payload: Mapping[str, Any]) -> str:
    return "grrs1-" + sha256(canonical_bytes({k:v for k,v in payload.items() if k != "content_id"})).hexdigest()


def _report_as_of(queue: Mapping[str, Any], generated_at: str, generated: datetime) -> str:
    """Separate the incumbent daily analysis horizon from this report's cutoff.

    The verified candidate owner represents a date with inclusive UTC end-of-day.
    Only that exact horizon on the actual generation's UTC date may be bounded to
    the report clock. Precise future cutoffs and future UTC dates remain invalid.
    The original queue stays byte-exact and bound by its existing source digest.
    """
    horizon = _clock(queue["as_of"])
    if horizon <= generated:
        return queue["as_of"]
    if horizon.date() == generated.date() and horizon.time() == datetime.max.time():
        return generated_at
    raise GraderError("research state candidate as_of is future")


def _validate_source_clocks(value: Any, *, cutoff: datetime, generated: datetime) -> None:
    """No horizon adaptation may admit evidence unavailable at the report cutoff."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in {"known_at", "event_known_at", "graph_known_at"}:
                if _clock(item) > cutoff:
                    raise GraderError("research state cannot consume future candidate knowledge")
            elif key == "generated_at":
                if _clock(item) > generated:
                    raise GraderError("research state cannot consume future candidate generation")
            else:
                _validate_source_clocks(item, cutoff=cutoff, generated=generated)
    elif isinstance(value, list):
        for item in value:
            _validate_source_clocks(item, cutoff=cutoff, generated=generated)


def build_not_started_state(*, queue: Mapping[str, Any], prereg_path: Path,
    generated_at: str, source_digests: Mapping[str, str], prior_issuance_raw: bytes = b"") -> dict[str, Any]:
    """Project verified current input shapes; never mistake them for issuances.

    The serialized publisher verifies the candidate artifacts before this call.
    Sources are the exact hashes of that verified generation. No runtime source
    bundle/durable acknowledgement is currently admitted by this integration.
    """
    family, document_digest = load_family_declaration(prereg_path)
    generated = _clock(generated_at)
    if family != GRV_FA1 or family.version != "4.1.0":
        raise GraderError("research state cannot change incumbent GRV-FA1 terms")
    log = parse_issuance_log(prior_issuance_raw)
    if cohort_rows(log, family_id=family.family_id):
        raise GraderError("existing issuance requires its admitted owner report; refuse not_started projection")
    if not is_valid_candidate_queue(queue):
        raise GraderError("research state candidate input is invalid")
    report_as_of = _report_as_of(queue, generated_at, generated)
    _validate_source_clocks(queue, cutoff=_clock(report_as_of), generated=generated)
    if not source_digests or any(not isinstance(k,str) or not k or not isinstance(v,str)
        or len(v) != 64 or any(c not in "0123456789abcdef" for c in v) for k,v in source_digests.items()):
        raise GraderError("research state requires exact source SHA256 references")
    reasons = Counter()
    for candidate in queue["candidates"]:
        decision = admit(candidate, family=family)
        reasons["owner_admitted_input_shape" if decision.admitted else decision.reason] += 1
    payload = {"contract": CONTRACT, "schema_version": "1.0.0", "content_id": "",
        "authority": _authority(), "generated_at": generated_at, "as_of": report_as_of,
        "state": "not_started", "is_running": False,
        "registration": {"family": family.to_payload(), "document_sha256": document_digest},
        "sources": dict(source_digests),
        "issuance": {"sha256": log.sha256, "line_count": log.line_count, "issued_n": 0,
            "append_count_this_generation": 0, "activation_refusals": list(REFUSALS)},
        "input_admission": {"considered_n": len(queue["candidates"]), "counts": dict(sorted(reasons.items())),
            "is_prospective_cohort": False},
        "outcomes": {"state": "not_started", "evaluated_n": 0, "efficacy": None},
        "required_next_steps": list(NEXT_STEPS), "limitations": list(LIMITATIONS)}
    payload["content_id"] = content_id(payload)
    validate_research_state(payload)
    return payload


def _object(value: Any, fields: set[str] | frozenset[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise GraderError(f"research state {label} fields are invalid")
    return value


def _same_closed(value: Any, expected: Any) -> bool:
    if type(value) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(value) == set(expected) and all(_same_closed(value[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(value) == len(expected) and all(_same_closed(a, b) for a, b in zip(value, expected))
    return value == expected


def _digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _count(value: Any) -> bool:
    return type(value) is int and value >= 0


def validate_research_state(payload: Any) -> None:
    """Closed nested contract: every field is typed, bounded and non-sensitive."""
    _object(payload, FIELDS, "outer")
    if payload["contract"] != CONTRACT or payload["schema_version"] != "1.0.0":
        raise GraderError("research state contract is invalid")
    authority = _object(payload["authority"], set(_authority()), "authority")
    if not _same_closed(authority, _authority()):
        raise GraderError("research state authority is invalid")
    generated = _clock(payload["generated_at"])
    if _clock(payload["as_of"]) > generated:
        raise GraderError("research state as_of is future")
    if payload["state"] != "not_started" or payload["is_running"] is not False:
        raise GraderError("unactivated research cannot be running")
    registration = _object(payload["registration"], {"family", "document_sha256"}, "registration")
    if not _same_closed(registration["family"], GRV_FA1.to_payload()):
        raise GraderError("research state registered measurement differs")
    if not _digest(registration["document_sha256"]):
        raise GraderError("research registration digest is invalid")
    sources = _object(payload["sources"], SOURCE_PATHS, "sources")
    if not all(_digest(digest) for digest in sources.values()):
        raise GraderError("research source digest is invalid")
    issuance = _object(payload["issuance"], {"sha256", "line_count", "issued_n",
        "append_count_this_generation", "activation_refusals"}, "issuance")
    if not _digest(issuance["sha256"]) or not _count(issuance["line_count"]):
        raise GraderError("research issuance log reference is invalid")
    if type(issuance["issued_n"]) is not int or issuance["issued_n"] != 0 or type(issuance["append_count_this_generation"]) is not int or issuance["append_count_this_generation"] != 0 or issuance["activation_refusals"] != list(REFUSALS):
        raise GraderError("unactivated research cannot claim issuance")
    outcomes = _object(payload["outcomes"], {"state", "evaluated_n", "efficacy"}, "outcomes")
    if outcomes["state"] != "not_started" or type(outcomes["evaluated_n"]) is not int or outcomes["evaluated_n"] != 0 or outcomes["efficacy"] is not None:
        raise GraderError("unactivated research cannot claim outcomes")
    admission = _object(payload["input_admission"], {"considered_n", "counts", "is_prospective_cohort"}, "input admission")
    counts = admission["counts"]
    if admission["is_prospective_cohort"] is not False or not _count(admission["considered_n"]):
        raise GraderError("research input admission is invalid")
    if not isinstance(counts, dict) or not set(counts).issubset(REASON_CODES) or not all(_count(v) for v in counts.values()):
        raise GraderError("research admission reason counts are invalid")
    if sum(counts.values()) != admission["considered_n"]:
        raise GraderError("research input admission accounting differs")
    if payload["required_next_steps"] != NEXT_STEPS or payload["limitations"] != LIMITATIONS:
        raise GraderError("research state disclosure differs")
    if not isinstance(payload["content_id"], str) or payload["content_id"] != content_id(payload):
        raise GraderError("research state content digest differs")
    if len(canonical_bytes(payload)) > MAX_STATE_BYTES:
        raise GraderError("research state exceeds byte budget")


def load_research_state(paths: tuple[Path, Path]) -> dict[str, Any]:
    """Bounded twin read for the paid consumer; never calculate outcomes."""
    buffers = []
    for path in paths:
        with path.open("rb") as stream:
            raw = stream.read(MAX_STATE_BYTES + 1)
        if len(raw) > MAX_STATE_BYTES:
            raise GraderError("research state exceeds byte budget")
        buffers.append(raw)
    if buffers[0] != buffers[1]:
        raise GraderError("research state canonical/public twins differ")
    try:
        payload = json.loads(buffers[0])
    except (ValueError, RecursionError) as exc:
        raise GraderError("research state JSON is invalid") from exc
    validate_research_state(payload)
    return payload
