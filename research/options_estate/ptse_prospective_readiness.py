"""Prospective-readiness validator for PTSE observation contexts.

This module does not publish, persist, schedule, backfill, replay, or mint source
timestamps. It only determines whether an already-built PTSE context is eligible
to be handed to the existing publication owner as a genuine first-seen
observation-only artifact.

A READY result is not an issuance receipt, a production acceptance, a forecast,
or decision authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping

from research.options_estate.ptse_contract import (
    AUTHORITY_KEYS,
    ContextArtifact,
    ContractViolation,
    canonical_json,
    validate_context,
    _time,
)


class PTSEProspectiveReadinessError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise PTSEProspectiveReadinessError(code)


@dataclass(frozen=True)
class ProspectiveReadiness:
    observation_id: str
    assessment_id: str
    artifact_sha256: str
    action: str
    decision_at: str
    issued_at: str
    market_session: str
    evidence_grade: str
    status: str
    publication_authority: bool
    decision_authority: bool


def qualify_prospective_observation(
    artifact: ContextArtifact | bytes | str,
) -> ProspectiveReadiness:
    """Validate first-seen observation readiness without any external effect."""

    try:
        validated = (
            validate_context(artifact.canonical_bytes)
            if isinstance(artifact, ContextArtifact)
            else validate_context(artifact)
        )
    except ContractViolation as exc:
        raise PTSEProspectiveReadinessError("CONTEXT_INVALID") from exc

    payload = validated.to_dict()
    observation = payload["observation"]
    assessment = payload["assessment"]

    if observation.get("evidence_grade") != "PROSPECTIVE_FIRST_SEEN":
        _fail("OBSERVATION_NOT_PROSPECTIVE")
    if observation.get("reconstructed_at") is not None:
        _fail("PROSPECTIVE_RECONSTRUCTION_FORBIDDEN")
    if assessment.get("estimate_status") != "NOT_FITTED" or assessment.get("estimate") is not None:
        _fail("ESTIMATE_NOT_ADMITTED")
    authority = assessment.get("authority")
    if (
        not isinstance(authority, Mapping)
        or set(authority) != set(AUTHORITY_KEYS)
        or any(authority.get(key) is not False for key in AUTHORITY_KEYS)
    ):
        _fail("AUTHORITY_FORBIDDEN")

    decision_at = _time(observation.get("decision_at"), "prospective.decision_at")
    issued_at = _time(observation.get("issued_at"), "prospective.issued_at")
    assessment_issued_at = _time(assessment.get("issued_at"), "prospective.assessment.issued_at")
    valid_until = _time(observation.get("valid_until"), "prospective.valid_until")
    if issued_at < decision_at:
        _fail("ISSUED_BEFORE_DECISION")
    # The consumer expires context at now >= valid_until and cannot use it
    # before assessment issuance. Both clocks must leave a nonempty interval.
    if max(issued_at, assessment_issued_at) >= valid_until:
        _fail("ISSUED_AFTER_EXPIRY")

    facts = observation.get("facts")
    if not isinstance(facts, list) or not facts:
        _fail("FACTS_REQUIRED")

    for fact in facts:
        if not isinstance(fact, Mapping):
            _fail("FACT_INVALID")
        if fact.get("evidence_grade") != "PROSPECTIVE_FIRST_SEEN":
            _fail("FACT_NOT_PROSPECTIVE")
        status = fact.get("status")
        known_at = fact.get("known_at")
        if status in {"OBSERVED", "PARTIAL", "STALE"}:
            if not isinstance(known_at, Mapping):
                _fail("KNOWN_AT_REQUIRED")
            latest = _time(
                known_at.get("latest"),
                "prospective.fact.known_at.latest",
            )
            if latest > decision_at:
                _fail("FACT_KNOWN_AFTER_DECISION")
        elif status in {"UNAVAILABLE", "NOT_APPLICABLE"}:
            if known_at is not None:
                _fail("MISSING_FACT_KNOWN_AT_FORBIDDEN")
        elif status == "CONFLICTED":
            if known_at is not None:
                latest = _time(
                    known_at.get("latest"),
                    "prospective.fact.known_at.latest",
                )
                if latest > decision_at:
                    _fail("FACT_KNOWN_AFTER_DECISION")

    wire = validated.canonical_bytes
    return ProspectiveReadiness(
        observation_id=observation["observation_id"],
        assessment_id=assessment["assessment_id"],
        artifact_sha256=sha256(wire).hexdigest(),
        action=assessment["action"],
        decision_at=observation["decision_at"],
        issued_at=observation["issued_at"],
        market_session=observation["market_session"],
        evidence_grade=observation["evidence_grade"],
        status="READY_FOR_EXISTING_PUBLICATION_OWNER",
        publication_authority=False,
        decision_authority=False,
    )


__all__ = [
    "PTSEProspectiveReadinessError",
    "ProspectiveReadiness",
    "qualify_prospective_observation",
]
