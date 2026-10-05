"""Pure zero-authority PTSE shadow-enrollment contract for W7.

This module does not select a physical store, write a ledger, grade an outcome,
change candidate membership, or grant any decision authority. It binds one
incumbent candidate-row grain to the exact B1 relation and, when present, one
validated PTSE context artifact.

Missing optional PTSE context stays an explicit UNAVAILABLE row so the incumbent
candidate population is never silently shrunk.
"""
from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from typing import Any

from research.options_estate.ptse_candidate_relation import (
    CandidateEpisodeRelation,
    resolve_candidate_episode_relation,
)
from research.options_estate.ptse_contract import ContextArtifact, validate_context

SCHEMA = "ptse.shadow_enrollment/v1-research"
DEFINITION = "ptse_new_entry_shadow_v1"
AUTHORITY = {
    "rank": False,
    "admission": False,
    "entry_gating": False,
    "plan_mutation": False,
    "alert_escalation": False,
    "sizing": False,
    "portfolio": False,
    "execution": False,
    "trade": False,
}


class PTSEShadowEnrollmentError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise PTSEShadowEnrollmentError(code)


def _text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value or any(ord(ch) < 32 for ch in value):
        _fail(code)
    return value


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise PTSEShadowEnrollmentError("SHADOW_ROW_NOT_CANONICAL") from exc


def _status(context: ContextArtifact) -> tuple[str, str]:
    payload = context.to_dict()
    observation = payload["observation"]
    assessment = payload["assessment"]
    if assessment["evidence_status"] == "ABSTAINED" or assessment["estimate_status"] == "ABSTAINED":
        return "ABSTAINED", "ACTION_ABSTAINED"
    if assessment["applicability"] == "UNKNOWN":
        return "UNAVAILABLE", "APPLICABILITY_UNKNOWN"
    if assessment["applicability"] == "NOT_APPLICABLE":
        return "UNAVAILABLE", "APPLICABILITY_NOT_APPLICABLE"
    fact_statuses = {fact["status"] for fact in observation["facts"]}
    if any(status in {"PARTIAL", "STALE", "UNAVAILABLE", "CONFLICTED"} for status in fact_statuses):
        return "PARTIAL", "SOME_FACTS_NOT_OBSERVED"
    return "AVAILABLE", "OBSERVED_CONTEXT_ONLY"


def build_shadow_enrollment(
    *,
    candidate_row: Mapping[str, object],
    b1_snapshot: object,
    context: ContextArtifact | bytes | str | None,
) -> dict[str, Any]:
    """Build one deterministic shadow row without changing incumbent behavior."""
    relation: CandidateEpisodeRelation
    if context is None:
        relation = resolve_candidate_episode_relation(candidate_row, b1_snapshot)
        status, reason = "UNAVAILABLE", "CONTEXT_MISSING"
        artifact = None
        payload = None
    else:
        artifact = (
            context if isinstance(context, ContextArtifact)
            else validate_context(context)
        )
        # Re-validate even a ContextArtifact so caller-created wrapper objects
        # cannot bypass the wire contract.
        artifact = validate_context(artifact.canonical_bytes)
        payload = artifact.to_dict()
        assessment = payload["assessment"]
        relation = resolve_candidate_episode_relation(
            candidate_row,
            b1_snapshot,
            expected_episode_id=assessment["episode_id"],
        )
        if assessment["action"] != "NEW_ENTRY":
            _fail("SHADOW_ACTION_NOT_ADMITTED")
        if payload["observation"]["evidence_grade"] != "PROSPECTIVE_FIRST_SEEN":
            _fail("SHADOW_SOURCE_GRADE_NOT_ADMITTED")
        for field in ("security_id", "company_id", "identity_epoch", "candidate_generation_id"):
            expected = getattr(relation, field)
            if assessment[field] != expected:
                _fail("SHADOW_B1_IDENTITY_MISMATCH")
        if any(assessment["authority"].values()):
            _fail("SHADOW_AUTHORITY_FORBIDDEN")
        status, reason = _status(artifact)

    row: dict[str, Any] = {
        "schema": SCHEMA,
        "definition": DEFINITION,
        "stamp_date": _text(candidate_row.get("stamp_date"), "CANDIDATE_STAMP_REQUIRED"),
        "ticker": _text(candidate_row.get("ticker"), "CANDIDATE_TICKER_REQUIRED"),
        "board_definition": _text(
            candidate_row.get("board_definition"),
            "CANDIDATE_BOARD_DEFINITION_REQUIRED",
        ),
        "candidate_source_event_id": relation.source_event_id,
        "candidate_generation_id": relation.candidate_generation_id,
        "episode_id": relation.episode_id,
        "security_id": relation.security_id,
        "company_id": relation.company_id,
        "identity_epoch": relation.identity_epoch,
        "action": "NEW_ENTRY",
        "context_status": status,
        "context_reason": reason,
        "context_sha256": artifact.sha256 if artifact is not None else None,
        "observation_id": artifact.observation_id if artifact is not None else None,
        "assessment_id": artifact.assessment_id if artifact is not None else None,
        "evidence_grade": (
            payload["observation"]["evidence_grade"] if payload is not None else None
        ),
        "authority": dict(AUTHORITY),
    }
    semantic = dict(row)
    row["enrollment_id"] = "ptse-shadow:" + hashlib.sha256(
        _canonical_json(semantic)
    ).hexdigest()
    return row


def validate_shadow_enrollment(row: Mapping[str, Any]) -> None:
    if not isinstance(row, Mapping):
        _fail("SHADOW_ROW_REQUIRED")
    expected = {
        "schema", "definition", "stamp_date", "ticker", "board_definition",
        "candidate_source_event_id", "candidate_generation_id", "episode_id",
        "security_id", "company_id", "identity_epoch", "action",
        "context_status", "context_reason", "context_sha256", "observation_id",
        "assessment_id", "evidence_grade", "authority", "enrollment_id",
    }
    if set(row) != expected:
        _fail("SHADOW_FIELDS_NOT_CLOSED")
    if row["schema"] != SCHEMA or row["definition"] != DEFINITION or row["action"] != "NEW_ENTRY":
        _fail("SHADOW_SCHEMA_NOT_ADMITTED")
    if row["context_status"] not in {"AVAILABLE", "PARTIAL", "UNAVAILABLE", "ABSTAINED"}:
        _fail("SHADOW_STATUS_INVALID")
    if row["authority"] != AUTHORITY:
        _fail("SHADOW_AUTHORITY_FORBIDDEN")
    has_context = row["context_sha256"] is not None
    if has_context != (row["observation_id"] is not None) or has_context != (row["assessment_id"] is not None):
        _fail("SHADOW_CONTEXT_IDENTITY_INCOMPLETE")
    if not has_context and row["evidence_grade"] is not None:
        _fail("SHADOW_GRADE_WITHOUT_CONTEXT")
    if has_context and row["evidence_grade"] != "PROSPECTIVE_FIRST_SEEN":
        _fail("SHADOW_SOURCE_GRADE_NOT_ADMITTED")
    semantic = {k: v for k, v in row.items() if k != "enrollment_id"}
    expected_id = "ptse-shadow:" + hashlib.sha256(_canonical_json(semantic)).hexdigest()
    if row["enrollment_id"] != expected_id:
        _fail("SHADOW_IDENTITY_MISMATCH")


__all__ = [
    "AUTHORITY",
    "DEFINITION",
    "PTSEShadowEnrollmentError",
    "SCHEMA",
    "build_shadow_enrollment",
    "validate_shadow_enrollment",
]
