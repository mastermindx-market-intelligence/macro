"""Fail-closed post-entry PTSE action contexts while owner identity is unresolved.

Supported actions: CONTINUATION, ADD, DERISK, REENTRY.

Current architecture has no canonical B1-episode ↔ Prophet-plan ↔ Terminal-position
relation owner. This module therefore emits only UNKNOWN action applicability
without fabricating plan/position/geometry/risk/exit bindings.

It does not join on ticker, create a relation table, alter plans/positions, or
grant rank, admission, entry, alert, sizing, portfolio, execution or trade
authority. When the incumbent owner later publishes an accepted relation and
action-eligibility receipt, this adapter may be extended under that owner's
contract; this file deliberately does not pre-authorize that future shape.
"""

from __future__ import annotations

from typing import Final

from research.options_estate.ptse_contract import (
    AUTHORITY_KEYS,
    ContextArtifact,
    build_context,
    validate_context,
)


POST_ENTRY_ACTIONS: Final = frozenset(
    {"CONTINUATION", "ADD", "DERISK", "REENTRY"}
)


class PTSEPostEntryContextError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise PTSEPostEntryContextError(code)


def build_unresolved_post_entry_context(
    *,
    base_context: ContextArtifact | bytes | str,
    action: str,
    reason: str = "CANONICAL_EPISODE_PLAN_POSITION_RELATION_UNAVAILABLE",
) -> ContextArtifact:
    """Project one honest UNKNOWN action assessment over an unchanged observation."""

    if action not in POST_ENTRY_ACTIONS:
        _fail("POST_ENTRY_ACTION_INVALID")
    if (
        not isinstance(reason, str)
        or not reason
        or reason != reason.strip()
    ):
        _fail("APPLICABILITY_REASON_REQUIRED")

    try:
        base = (
            validate_context(base_context.canonical_bytes)
            if isinstance(base_context, ContextArtifact)
            else validate_context(base_context)
        )
    except Exception as exc:
        raise PTSEPostEntryContextError("BASE_CONTEXT_INVALID") from exc

    payload = base.to_dict()
    observation = payload["observation"]
    prior = payload["assessment"]

    # Reusing the already-sealed observation is intentional: unresolved
    # post-entry action applicability adds no new market/source fact.
    observation.pop("observation_id", None)

    assessment = {
        "episode_id": prior["episode_id"],
        "security_id": prior["security_id"],
        "company_id": prior["company_id"],
        "identity_epoch": prior["identity_epoch"],
        "candidate_generation_id": prior["candidate_generation_id"],
        "cohort_ref": prior["cohort_ref"],
        "strategy_id": prior["strategy_id"],
        "strategy_version": prior["strategy_version"],
        "holding_horizon_ref": prior["holding_horizon_ref"],
        "action": action,
        "decision_at": prior["decision_at"],
        "issued_at": prior["issued_at"],
        "forecast_horizon_sessions": prior["forecast_horizon_sessions"],
        "forecast_end_session": prior["forecast_end_session"],
        "calendar_ref": prior["calendar_ref"],
        "target_version": prior["target_version"],
        "applicability": "UNKNOWN",
        "applicability_reason": reason,
        "eligibility_ref": None,
        "position_ref": None,
        "geometry_ref": None,
        "risk_budget_ref": None,
        "prior_exit_episode_ref": None,
        "evidence_status": prior["evidence_status"],
        "estimate_status": "NOT_FITTED",
        "estimate": None,
        "drivers": [],
        "contradictions": [],
        "authority": {key: False for key in AUTHORITY_KEYS},
    }

    try:
        return build_context(observation, assessment)
    except Exception as exc:
        raise PTSEPostEntryContextError(
            "POST_ENTRY_CONTEXT_INVALID"
        ) from exc


__all__ = [
    "POST_ENTRY_ACTIONS",
    "PTSEPostEntryContextError",
    "build_unresolved_post_entry_context",
]