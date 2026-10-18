"""Pure PTSE NEW_ENTRY context compiler over existing B3/B4 owners.

No I/O, source collection, calendar calculation, persistence, route, publisher,
cache, lifecycle, eligibility, ranking, plan, alert, sizing, portfolio,
execution, or trade authority is created here.

This first compiler slice is intentionally narrow:
US / DAILY / REGULAR / H5 / NEW_ENTRY.

It consumes:
- one already-validated canonical B3 candidate-state projection;
- one already-validated B4 prophet.entry_availability/v1 object;
- passive owner facts supplied through ptse_owner_observation;
- explicit out-of-band receipts/clocks supplied by the existing owners.

B4's 2_15_SESSIONS/new_entry strategy horizon remains B4 strategy identity.
It is NOT silently substituted for PTSE's H5 forecast horizon or the
independent holding-horizon owner receipt.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Final

from engine.prophet_candidate_state import validate_candidate_state_projection
from engine.prophet_entry_availability import validate_entry_availability
from research.options_estate.ptse_contract import (
    AUTHORITY_KEYS,
    GRADES,
    ContextArtifact,
    EvidenceRef,
    build_context,
)
from research.options_estate.ptse_options_observation import (
    OptionsRootBinding,
    adapt_options_hub,
)
from research.options_estate.ptse_owner_observation import (
    OwnerArtifactBinding,
    PTSEOwnerAdapterError,
    compose_owner_facts,
)


MARKET: Final = "US"
CADENCE: Final = "DAILY"
SESSION_SCOPE: Final = "REGULAR"
ACTION: Final = "NEW_ENTRY"
FORECAST_HORIZON_SESSIONS: Final = 5


class PTSENewEntryContextError(ValueError):
    """Cross-owner binding failure; does not echo owner payload values."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise PTSENewEntryContextError(code)


@dataclass(frozen=True)
class NewEntryContextBinding:
    """Trusted owner metadata supplied outside the PTSE wire."""

    market_session: str
    decision_at: str
    issued_at: str
    valid_until: str
    forecast_end_session: str
    calendar_ref: EvidenceRef
    freshness_ref: EvidenceRef
    source_manifest_ref: EvidenceRef
    calculation_receipt_ref: EvidenceRef
    producer_revision: str
    feature_version: str
    observation_instrument_id: str
    cohort_ref: EvidenceRef
    eligibility_ref: EvidenceRef
    holding_horizon_ref: EvidenceRef
    target_version: str
    reconstructed_at: str | None = None


def _utc(value: Any) -> datetime:
    if not isinstance(value, str):
        _fail("TIMESTAMP_INVALID")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, OverflowError):
        _fail("TIMESTAMP_INVALID")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail("TIMESTAMP_INVALID")
    try:
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        _fail("TIMESTAMP_INVALID")


def _external_ref(ref: Mapping[str, Any], code: str) -> dict[str, str]:
    if (
        not isinstance(ref, Mapping)
        or set(ref) != {"owner_ref", "artifact_id", "sha256"}
        or not all(isinstance(ref.get(key), str) and ref.get(key) for key in ref)
    ):
        _fail(code)
    digest = ref.get("sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        _fail(code)
    return dict(ref)


def _owner_payload_sha256(payload: Mapping[str, Any]) -> str:
    """Hash owner JSON using the B3/B4 canonical JSON shape, not PTSE JSON."""
    try:
        wire = json.dumps(
            dict(payload),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise PTSENewEntryContextError("OWNER_CANONICALIZATION_FAILED") from exc
    return sha256(wire).hexdigest()


def _candidate_row(
    candidate_projection: Mapping[str, Any],
    episode_id: str,
) -> Mapping[str, Any]:
    rows = candidate_projection.get("rows")
    if not isinstance(rows, list):
        _fail("B3_ROWS_INVALID")
    matches = [
        row
        for row in rows
        if isinstance(row, Mapping) and row.get("episode_id") == episode_id
    ]
    if len(matches) != 1:
        _fail("B3_EPISODE_NOT_UNIQUE")
    return matches[0]


def _availability_applicability(state: str) -> tuple[str, str]:
    """Map B4 lane existence, not entry permission, into PTSE applicability.

    APPLICABLE means the canonical NEW_ENTRY lane exists for this episode and
    may carry read-only timing context. It does NOT mean B4 ENTRY_OPEN.
    """
    if state == "INVALIDATED":
        return "NOT_APPLICABLE", "B4_NEW_ENTRY_LANE_INVALIDATED"
    if state == "UNAVAILABLE_DATA":
        return "UNKNOWN", "B4_NEW_ENTRY_LANE_UNAVAILABLE"
    return "APPLICABLE", "B4_NEW_ENTRY_LANE_PRESENT_ENTRY_PERMISSION_UNCHANGED"


def _observation_grade(facts: list[Mapping[str, Any]]) -> str:
    grades = [fact.get("evidence_grade") for fact in facts]
    if not grades or any(grade not in GRADES for grade in grades):
        _fail("OWNER_FACT_GRADE_INVALID")
    return min(grades, key=lambda grade: GRADES[grade])


def build_new_entry_context(
    *,
    candidate_projection: Mapping[str, Any],
    entry_availability: Mapping[str, Any],
    binding: NewEntryContextBinding,
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
    """Compile one immutable, zero-authority NEW_ENTRY context artifact."""

    try:
        validate_candidate_state_projection(candidate_projection)
    except Exception as exc:  # existing owner validator is authoritative
        raise PTSENewEntryContextError("B3_CONTRACT_INVALID") from exc
    try:
        validate_entry_availability(entry_availability)
    except Exception as exc:  # existing owner validator is authoritative
        raise PTSENewEntryContextError("B4_CONTRACT_INVALID") from exc

    if (
        candidate_projection.get("market_session") != binding.market_session
        or entry_availability.get("market_session") != binding.market_session
    ):
        _fail("MARKET_SESSION_MISMATCH")
    if _utc(entry_availability.get("evaluated_at")) != _utc(binding.decision_at):
        _fail("DECISION_CLOCK_MISMATCH")

    episode_id = entry_availability.get("episode_id")
    if not isinstance(episode_id, str) or not episode_id:
        _fail("B4_IDENTITY_INVALID")
    row = _candidate_row(candidate_projection, episode_id)

    if entry_availability.get("candidate_state_projection_id") != candidate_projection.get(
        "projection_id"
    ):
        _fail("B3_B4_PROJECTION_MISMATCH")

    identity_pairs = (
        ("episode_id", episode_id, row.get("episode_id")),
        (
            "candidate_generation_id",
            entry_availability.get("candidate_generation_id"),
            candidate_projection.get("candidate_generation_id"),
        ),
        (
            "candidate_generation_id",
            entry_availability.get("candidate_generation_id"),
            row.get("candidate_generation_id"),
        ),
        ("security_id", entry_availability.get("security_id"), row.get("security_id")),
        ("identity_epoch", entry_availability.get("identity_epoch"), row.get("identity_epoch")),
    )
    if any(left != right for _, left, right in identity_pairs):
        _fail("B3_B4_IDENTITY_MISMATCH")

    company_id = row.get("company_id")
    if not isinstance(company_id, str) or not company_id:
        _fail("B3_COMPANY_ID_INVALID")

    if (
        entry_availability.get("horizon_role") != "new_entry"
        or entry_availability.get("horizon") != "2_15_SESSIONS"
    ):
        _fail("B4_STRATEGY_HORIZON_MISMATCH")

    cohort_ref = _external_ref(binding.cohort_ref, "COHORT_REF_INVALID")
    if (
        cohort_ref["artifact_id"] != candidate_projection.get("projection_id")
        or cohort_ref["sha256"] != _owner_payload_sha256(candidate_projection)
    ):
        _fail("COHORT_REF_MISMATCH")

    eligibility_ref = _external_ref(
        binding.eligibility_ref,
        "ELIGIBILITY_REF_INVALID",
    )
    if (
        eligibility_ref["artifact_id"] != entry_availability.get("availability_id")
        or eligibility_ref["sha256"] != _owner_payload_sha256(entry_availability)
    ):
        _fail("ELIGIBILITY_REF_MISMATCH")

    try:
        facts = compose_owner_facts(
            market_session=binding.market_session,
            decision_at=binding.decision_at,
            market_state=market_state,
            market_state_binding=market_state_binding,
            regime_vector=regime_vector,
            regime_vector_binding=regime_vector_binding,
        )
    except PTSEOwnerAdapterError as exc:
        raise PTSENewEntryContextError("OWNER_FACT_ADAPTER_INVALID") from exc
    if any(
        fact.get("source_scope", {}).get("instrument_id")
        != binding.observation_instrument_id
        for fact in facts
    ):
        _fail("OBSERVATION_INSTRUMENT_MISMATCH")
    if any(
        fact.get("source_scope", {}).get("session_scope") != SESSION_SCOPE
        for fact in facts
    ):
        _fail("OWNER_SESSION_SCOPE_MISMATCH")

    options_supplied = any(
        value is not None
        for value in (options_vol, options_vol_binding, options_gex, options_gex_binding)
    )
    if options_supplied:
        if options_root_binding is None:
            _fail("OPTIONS_ROOT_BINDING_REQUIRED")
        if options_root_binding.security_id != row.get("security_id"):
            _fail("OPTIONS_SECURITY_BINDING_MISMATCH")
        try:
            options_facts = adapt_options_hub(
                market_session=binding.market_session,
                decision_at=binding.decision_at,
                root_binding=options_root_binding,
                vol=options_vol,
                vol_binding=options_vol_binding,
                gex=options_gex,
                gex_binding=options_gex_binding,
            )
        except PTSEOwnerAdapterError as exc:
            raise PTSENewEntryContextError("OPTIONS_OWNER_FACT_INVALID") from exc
        if any(
            fact.get("source_scope", {}).get("instrument_id") != row.get("security_id")
            for fact in options_facts
        ):
            _fail("OPTIONS_SECURITY_BINDING_MISMATCH")
        if any(
            fact.get("source_scope", {}).get("session_scope") != SESSION_SCOPE
            for fact in options_facts
        ):
            _fail("OWNER_SESSION_SCOPE_MISMATCH")
        facts.extend(options_facts)

    grade = _observation_grade(facts)
    if grade in {"RETROSPECTIVE_PIT_UNPROVEN", "PIT_QUALIFIED_REPLAY"}:
        if binding.reconstructed_at is None:
            _fail("RECONSTRUCTION_REQUIRED")
    elif binding.reconstructed_at is not None:
        _fail("RECONSTRUCTION_FORBIDDEN")

    state = entry_availability.get("state")
    if not isinstance(state, str):
        _fail("B4_STATE_INVALID")
    applicability, applicability_reason = _availability_applicability(state)

    present_context = any(
        fact.get("status") in {"OBSERVED", "PARTIAL", "STALE"}
        for fact in facts
    )

    observation = {
        "market": MARKET,
        "instrument_id": binding.observation_instrument_id,
        "market_session": binding.market_session,
        "cadence": CADENCE,
        "session_scope": SESSION_SCOPE,
        "decision_at": binding.decision_at,
        "issued_at": binding.issued_at,
        "valid_until": binding.valid_until,
        "calendar_ref": _external_ref(binding.calendar_ref, "CALENDAR_REF_INVALID"),
        "freshness_ref": _external_ref(binding.freshness_ref, "FRESHNESS_REF_INVALID"),
        "source_manifest_ref": _external_ref(
            binding.source_manifest_ref,
            "SOURCE_MANIFEST_REF_INVALID",
        ),
        "calculation_receipt_ref": _external_ref(
            binding.calculation_receipt_ref,
            "CALCULATION_RECEIPT_REF_INVALID",
        ),
        "producer_revision": binding.producer_revision,
        "feature_version": binding.feature_version,
        "evidence_grade": grade,
        "reconstructed_at": binding.reconstructed_at,
        "supersedes_ref": None,
        "correction_reason": None,
        "facts": facts,
    }

    assessment = {
        "episode_id": episode_id,
        "security_id": row.get("security_id"),
        "company_id": company_id,
        "identity_epoch": row.get("identity_epoch"),
        "candidate_generation_id": row.get("candidate_generation_id"),
        "cohort_ref": cohort_ref,
        "strategy_id": entry_availability.get("strategy_id"),
        "strategy_version": entry_availability.get("strategy_version"),
        "holding_horizon_ref": _external_ref(
            binding.holding_horizon_ref,
            "HOLDING_HORIZON_REF_INVALID",
        ),
        "action": ACTION,
        "decision_at": binding.decision_at,
        "issued_at": binding.issued_at,
        "forecast_horizon_sessions": FORECAST_HORIZON_SESSIONS,
        "forecast_end_session": binding.forecast_end_session,
        "calendar_ref": _external_ref(binding.calendar_ref, "CALENDAR_REF_INVALID"),
        "target_version": binding.target_version,
        "applicability": applicability,
        "applicability_reason": applicability_reason,
        "eligibility_ref": eligibility_ref,
        "position_ref": None,
        "geometry_ref": None,
        "risk_budget_ref": None,
        "prior_exit_episode_ref": None,
        "evidence_status": (
            "OBSERVED_CONTEXT_ONLY" if present_context else "ABSTAINED"
        ),
        "estimate_status": "NOT_FITTED",
        "estimate": None,
        "drivers": [],
        "contradictions": [],
        "authority": {key: False for key in AUTHORITY_KEYS},
    }

    try:
        return build_context(observation, assessment)
    except Exception as exc:
        raise PTSENewEntryContextError("PTSE_CONTEXT_INVALID") from exc


__all__ = [
    "MARKET",
    "CADENCE",
    "SESSION_SCOPE",
    "ACTION",
    "FORECAST_HORIZON_SESSIONS",
    "PTSENewEntryContextError",
    "NewEntryContextBinding",
    "build_new_entry_context",
]