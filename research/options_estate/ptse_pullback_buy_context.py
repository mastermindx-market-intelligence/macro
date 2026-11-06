"""Pure PTSE PULLBACK_BUY context compiler over the accepted B3/B4 owners.

This is a read-only action-context projection. It does not alter B4 availability,
entry geometry, plan state, ranking, sizing, portfolio, execution, or trading.

PULLBACK_BUY applicability here means "the action context is relevant to inspect",
not "the user may buy". B4 remains the deterministic NEW_ENTRY availability owner.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from research.options_estate.ptse_contract import (
    AUTHORITY_KEYS,
    ContextArtifact,
    EvidenceRef,
    build_context,
)
from research.options_estate.ptse_new_entry_context import (
    NewEntryContextBinding,
    PTSENewEntryContextError,
    build_new_entry_context,
)
from research.options_estate.ptse_options_observation import OptionsRootBinding
from research.options_estate.ptse_owner_observation import OwnerArtifactBinding


class PTSEPullbackContextError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise PTSEPullbackContextError(code)


def _ref(value: Mapping[str, Any] | None) -> dict[str, str]:
    if (
        not isinstance(value, Mapping)
        or set(value) != {"owner_ref", "artifact_id", "sha256"}
        or not all(isinstance(value.get(k), str) and value.get(k) for k in value)
    ):
        _fail("GEOMETRY_REF_INVALID")
    digest = value.get("sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(ch not in "0123456789abcdef" for ch in digest)
    ):
        _fail("GEOMETRY_REF_INVALID")
    return dict(value)


def _applicability(state: str) -> tuple[str, str]:
    if state in {"WAIT_PULLBACK", "RAN_DONT_CHASE"}:
        return "APPLICABLE", f"B4_{state}_PULLBACK_CONTEXT_ONLY"
    if state == "INVALIDATED":
        return "NOT_APPLICABLE", "B4_NEW_ENTRY_LANE_INVALIDATED"
    if state == "UNAVAILABLE_DATA":
        return "UNKNOWN", "B4_NEW_ENTRY_LANE_UNAVAILABLE"
    return "NOT_APPLICABLE", f"B4_{state}_DOES_NOT_REQUIRE_PULLBACK_ACTION"


def build_pullback_buy_context(
    *,
    candidate_projection: Mapping[str, Any],
    entry_availability: Mapping[str, Any],
    binding: NewEntryContextBinding,
    geometry_ref: EvidenceRef | None,
    market_state: Mapping[str, Any] | None = None,
    market_state_binding: OwnerArtifactBinding | None = None,
    regime_vector: Mapping[str, Any] | None = None,
    regime_vector_binding: OwnerArtifactBinding | None = None,
    options_root_binding: OptionsRootBinding | None = None,
    options_vol: Mapping[str, Any] | None = None,
    options_vol_binding: OwnerArtifactBinding | None = None,
    options_gex: Mapping[str, Any] | None = None,
    options_gex_binding: OwnerArtifactBinding | None = None,
) -> ContextArtifact:
    """Compile one zero-authority PULLBACK_BUY context from the NEW_ENTRY spine."""

    try:
        base = build_new_entry_context(
            candidate_projection=candidate_projection,
            entry_availability=entry_availability,
            binding=binding,
            market_state=market_state,
            market_state_binding=market_state_binding,
            regime_vector=regime_vector,
            regime_vector_binding=regime_vector_binding,
            options_root_binding=options_root_binding,
            options_vol=options_vol,
            options_vol_binding=options_vol_binding,
            options_gex=options_gex,
            options_gex_binding=options_gex_binding,
        )
    except PTSENewEntryContextError as exc:
        raise PTSEPullbackContextError("NEW_ENTRY_SPINE_INVALID") from exc

    state = entry_availability.get("state")
    if not isinstance(state, str):
        _fail("B4_STATE_INVALID")
    applicability, reason = _applicability(state)

    owner_geometry_ref = None
    if geometry_ref is not None:
        owner_geometry_ref = _ref(geometry_ref)
        receipts = entry_availability.get("source_receipts")
        if not isinstance(receipts, list):
            _fail("B4_SOURCE_RECEIPTS_INVALID")
        if owner_geometry_ref["artifact_id"] not in receipts:
            _fail("GEOMETRY_REF_NOT_IN_B4_RECEIPTS")
        # Digest-form B4 receipt IDs already commit to their exact bytes. Opaque
        # owner IDs remain externally admitted references; do not invent a new
        # content-address requirement for the owner's other valid receipt forms.
        artifact_id = owner_geometry_ref["artifact_id"]
        if artifact_id.startswith("sha256:") and artifact_id != "sha256:" + owner_geometry_ref["sha256"]:
            _fail("GEOMETRY_REF_DIGEST_MISMATCH")

    if applicability == "APPLICABLE" and owner_geometry_ref is None:
        _fail("GEOMETRY_REF_REQUIRED")

    payload = base.to_dict()
    observation = payload["observation"]
    prior = payload["assessment"]

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
        "action": "PULLBACK_BUY",
        "decision_at": prior["decision_at"],
        "issued_at": prior["issued_at"],
        "forecast_horizon_sessions": prior["forecast_horizon_sessions"],
        "forecast_end_session": prior["forecast_end_session"],
        "calendar_ref": prior["calendar_ref"],
        "target_version": prior["target_version"],
        "applicability": applicability,
        "applicability_reason": reason,
        "eligibility_ref": prior["eligibility_ref"],
        "position_ref": None,
        "geometry_ref": owner_geometry_ref,
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
        raise PTSEPullbackContextError("PTSE_PULLBACK_CONTEXT_INVALID") from exc


__all__ = [
    "PTSEPullbackContextError",
    "build_pullback_buy_context",
]
