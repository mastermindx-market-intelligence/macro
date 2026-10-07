"""Pure owner-observation adapters for PTSE research v1.

This module performs no I/O and owns no source, clock, calendar, persistence,
publication, lifecycle, ranking, policy, model, or decision effect.

It translates already-admitted owner artifacts into the OwnerFact vocabulary
defined by ptse_contract. The caller must supply exact artifact identity,
availability, expiry, population and session metadata out-of-band.

Artifact SHA256 binds the entire supplied Mapping serialized as UTF-8 JSON with
sorted keys, compact separators, ensure_ascii=False and allow_nan=False, matching
the event/breadth adapter convention. It is parsed JSON content identity, not
raw source-file byte identity: this API receives no file bytes. Verifying that
content digest does not authenticate the external owner or admit its receipt.

Important boundary:
- market_state.v1 is consumed as display-only owner context.
- regime_vector is consumed as a thin owner-fact aggregation.
- directive-like fields such as favor_entries / cap_leadership are deliberately
  NOT adapted. PTSE cannot turn an incumbent directive into timing authority.
- missing optional fields become typed UNAVAILABLE facts rather than zeros.
"""

from __future__ import annotations

from dataclasses import dataclass
import copy
import hashlib
import json
import math
from typing import Any, Final, Mapping

from research.options_estate.ptse_contract import (
    EvidenceGrade,
    EvidenceRef,
    GRADES,
    OwnerFact,
    _time,
)


class PTSEOwnerAdapterError(ValueError):
    """Closed adapter failure code; never echoes source payload values."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise PTSEOwnerAdapterError(code)


@dataclass(frozen=True)
class OwnerArtifactBinding:
    owner_ref: str
    artifact_ref: EvidenceRef
    known_at_earliest: str
    known_at_latest: str
    known_at_precision: str
    known_at_evidence_ref: EvidenceRef
    economic_time: str
    valid_until: str
    evidence_grade: EvidenceGrade
    population_ref: EvidenceRef
    instrument_id: str
    session_scope: str
    calculation_version: str
    limitations: tuple[str, ...]


_MARKET_STATE_FIELDS: Final = (
    ("market_state.verdict", ("verdict",), "STATE", "DETERMINISTIC_COMPUTATION"),
    ("market_state.raw_score", ("raw_score",), "POINTS", "DETERMINISTIC_COMPUTATION"),
    ("market_state.score_source", ("score_source",), "STATE", "DETERMINISTIC_COMPUTATION"),
    ("market_state.capped", ("capped",), "BOOLEAN", "DETERMINISTIC_COMPUTATION"),
    ("market_state.radar_state", ("radar", "state"), "STATE", "DETERMINISTIC_COMPUTATION"),
    (
        "market_state.participation_state",
        ("participation_scope", "state"),
        "STATE",
        "DETERMINISTIC_COMPUTATION",
    ),
    (
        "market_state.participation_strength",
        ("participation_scope", "participation"),
        "STATE",
        "DETERMINISTIC_COMPUTATION",
    ),
    (
        "market_state.any_input_stale",
        ("freshness", "any_input_stale"),
        "BOOLEAN",
        "DETERMINISTIC_COMPUTATION",
    ),
)

_REGIME_VECTOR_FIELDS: Final = (
    (
        "regime_vector.quad_hard_label",
        ("quad_hard_label",),
        "STATE",
        "STATISTICAL_ESTIMATE",
    ),
    (
        "regime_vector.rate_pressure",
        ("rate_pressure",),
        "STATE",
        "DETERMINISTIC_COMPUTATION",
    ),
    (
        "regime_vector.risk_radar_state",
        ("risk_radar_state",),
        "STATE",
        "DETERMINISTIC_COMPUTATION",
    ),
    (
        "regime_vector.vol_regime",
        ("vol_regime",),
        "STATE",
        "DETERMINISTIC_COMPUTATION",
    ),
    (
        "regime_vector.liquidity_quality_label",
        ("liquidity_quality_label",),
        "STATE",
        "DETERMINISTIC_COMPUTATION",
    ),
    (
        "regime_vector.deescalation_eligible",
        ("deescalation_eligible",),
        "BOOLEAN",
        "DETERMINISTIC_COMPUTATION",
    ),
    (
        "regime_vector.deescalation_phase",
        ("deescalation_trajectory", "phase"),
        "STATE",
        "DETERMINISTIC_COMPUTATION",
    ),
    (
        "regime_vector.deescalation_intensity",
        ("deescalation_trajectory", "intensity"),
        "POINTS",
        "DETERMINISTIC_COMPUTATION",
    ),
    (
        "regime_vector.dislocation_verdict",
        ("dislocation_verdict",),
        "STATE",
        "DETERMINISTIC_COMPUTATION",
    ),
    (
        "regime_vector.dislocation_active",
        ("dislocation_active",),
        "BOOLEAN",
        "DETERMINISTIC_COMPUTATION",
    ),
    (
        "regime_vector.breadth_pct_above_50",
        ("breadth_pct_above_50",),
        "PERCENT",
        "DETERMINISTIC_COMPUTATION",
    ),
    (
        "regime_vector.breadth_pct_above_200",
        ("breadth_pct_above_200",),
        "PERCENT",
        "DETERMINISTIC_COMPUTATION",
    ),
    (
        "regime_vector.degraded",
        ("regime_vector_degraded",),
        "BOOLEAN",
        "DETERMINISTIC_COMPUTATION",
    ),
)

# These are owner directives/controls, not passive PTSE facts.
_FORBIDDEN_REGIME_VECTOR_FIELDS: Final = frozenset(
    {
        "favor_entries",
        "cap_leadership",
        "fused_risk_gross",
    }
)


def _ref_shape(ref: Mapping[str, Any]) -> dict[str, str]:
    if (
        not isinstance(ref, Mapping)
        or set(ref) != {"owner_ref", "artifact_id", "sha256"}
        or not all(isinstance(ref.get(k), str) and ref.get(k) for k in ref)
    ):
        _fail("EVIDENCE_REF_INVALID")
    return dict(ref)


def _validate_payload_binding(payload: Mapping[str, Any], binding: OwnerArtifactBinding) -> None:
    """Bind the complete parsed payload, including fields not projected to facts."""
    try:
        wire = json.dumps(
            dict(payload), sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise PTSEOwnerAdapterError("OWNER_PAYLOAD_NOT_CANONICAL") from exc
    if binding.artifact_ref["sha256"] != hashlib.sha256(wire).hexdigest():
        _fail("OWNER_ARTIFACT_REF_MISMATCH")


def _validate_binding(binding: OwnerArtifactBinding, *, decision_at: str) -> bool:
    if (
        not isinstance(binding.owner_ref, str)
        or not binding.owner_ref
        or binding.owner_ref != binding.artifact_ref.get("owner_ref")
    ):
        _fail("OWNER_BINDING_INVALID")

    _ref_shape(binding.artifact_ref)
    _ref_shape(binding.known_at_evidence_ref)
    _ref_shape(binding.population_ref)

    if binding.known_at_precision not in {"EXACT", "INTERVAL", "DATE_ONLY"}:
        _fail("KNOWN_AT_PRECISION_INVALID")
    if binding.session_scope not in {"REGULAR", "EXTENDED", "ALL", "OWNER_DEFINED"}:
        _fail("SESSION_SCOPE_INVALID")
    if binding.evidence_grade not in GRADES:
        _fail("EVIDENCE_GRADE_INVALID")
    if (
        not isinstance(binding.instrument_id, str)
        or not binding.instrument_id
        or not isinstance(binding.calculation_version, str)
        or not binding.calculation_version
    ):
        _fail("IDENTITY_INVALID")
    if not binding.limitations or any(
        not isinstance(x, str) or not x for x in binding.limitations
    ):
        _fail("LIMITATIONS_REQUIRED")
    earliest = _time(binding.known_at_earliest, "adapter.known_at_earliest")
    latest = _time(binding.known_at_latest, "adapter.known_at_latest")
    economic = _time(binding.economic_time, "adapter.economic_time")
    decision = _time(decision_at, "adapter.decision_at")
    expiry = _time(binding.valid_until, "adapter.valid_until")

    if earliest > latest:
        _fail("KNOWN_AT_ORDER_INVALID")
    if binding.known_at_precision == "EXACT" and earliest != latest:
        _fail("KNOWN_AT_PRECISION_INVALID")
    if binding.known_at_precision == "DATE_ONLY" and earliest == latest:
        _fail("KNOWN_AT_PRECISION_INVALID")
    if economic > latest:
        _fail("AVAILABILITY_PRECEDES_OBSERVATION")
    if latest > decision:
        _fail("NOT_KNOWN_AT_DECISION")
    return expiry <= decision


def _path(payload: Mapping[str, Any], keys: tuple[str, ...]) -> tuple[bool, Any]:
    node: Any = payload
    for key in keys:
        if not isinstance(node, Mapping) or key not in node:
            return False, None
        node = node[key]
    return True, node


def _validate_value(value: Any, unit: str) -> None:
    if unit == "BOOLEAN":
        if type(value) is not bool:
            _fail("OWNER_VALUE_TYPE_INVALID")
        return
    if unit == "STATE":
        if not isinstance(value, str) or not value or value != value.strip():
            _fail("OWNER_VALUE_TYPE_INVALID")
        return
    if unit == "POINTS":
        if (
            type(value) not in (int, float)
            or not math.isfinite(float(value))
            or not 0 <= float(value) <= 100
        ):
            _fail("OWNER_VALUE_RANGE_INVALID")
        return
    if unit == "PERCENT":
        if (
            type(value) not in (int, float)
            or not math.isfinite(float(value))
            or not 0 <= float(value) <= 100
        ):
            _fail("OWNER_VALUE_RANGE_INVALID")
        return
    _fail("OWNER_UNIT_INVALID")


def _fact(
    *,
    feature_id: str,
    value_present: bool,
    value: Any,
    unit: str,
    method_kind: str,
    binding: OwnerArtifactBinding,
    null_reason: str,
    stale_at_decision: bool,
    adapter_limitations: tuple[str, ...],
) -> OwnerFact:
    limitations = list(binding.limitations) + list(adapter_limitations)
    if value_present:
        _validate_value(value, unit)
        status = "STALE" if stale_at_decision else "OBSERVED"
        coverage = {
            "numerator": 1,
            "denominator": 1,
            "missing_count": 0,
            "population_ref": _ref_shape(binding.population_ref),
        }
        known_at = {
            "earliest": binding.known_at_earliest,
            "latest": binding.known_at_latest,
            "precision": binding.known_at_precision,
            "evidence_ref": _ref_shape(binding.known_at_evidence_ref),
        }
        fact_value = value
        reason = "SOURCE_EXPIRED_AT_DECISION" if stale_at_decision else None
    else:
        status = "UNAVAILABLE"
        coverage = {
            "numerator": 0,
            "denominator": 1,
            "missing_count": 1,
            "population_ref": _ref_shape(binding.population_ref),
        }
        known_at = None
        fact_value = None
        reason = null_reason

    return {
        "feature_id": feature_id,
        "owner_ref": binding.owner_ref,
        "source_artifact_ref": _ref_shape(binding.artifact_ref),
        "economic_time": binding.economic_time,
        "economic_time_role": "OBSERVATION",
        "known_at": known_at,
        "valid_until": binding.valid_until,
        "value": fact_value,
        "unit": unit,
        "status": status,
        "method_kind": method_kind,
        "calculation_version": binding.calculation_version,
        "evidence_grade": binding.evidence_grade,
        "coverage": coverage,
        "source_scope": {
            "instrument_id": binding.instrument_id,
            "session_scope": binding.session_scope,
            "population_ref": _ref_shape(binding.population_ref),
            "position_scope": "NOT_APPLICABLE",
            "side_semantics": "NOT_APPLICABLE",
        },
        "limitations": limitations,
        "null_reason": reason,
    }


def adapt_market_state(
    payload: Mapping[str, Any],
    binding: OwnerArtifactBinding,
    *,
    market_session: str,
    decision_at: str,
) -> list[OwnerFact]:
    """Adapt selected display-only market_state.v1 fields into owner facts."""
    stale_at_decision = _validate_binding(binding, decision_at=decision_at)
    if not isinstance(payload, Mapping):
        _fail("MARKET_STATE_OBJECT_REQUIRED")
    if payload.get("schema") != "market_state.v1":
        _fail("MARKET_STATE_SCHEMA_INVALID")
    if payload.get("market") != "us" or payload.get("is_display_only") is not True:
        _fail("MARKET_STATE_AUTHORITY_INVALID")
    if payload.get("asof") != market_session:
        _fail("MARKET_STATE_SESSION_MISMATCH")
    _validate_payload_binding(payload, binding)

    facts: list[OwnerFact] = []
    adapter_limitations = (
        "market_state.v1 declares is_display_only=true; adapted facts remain context only.",
        "market_state.raw_score is a 0-100 owner blend, not a probability or PTSE forecast.",
        "PTSE does not consume market_state through Prophet management scoring in this adapter.",
    )
    for feature_id, keys, unit, method_kind in _MARKET_STATE_FIELDS:
        present, value = _path(payload, keys)
        present = bool(present and value is not None)
        facts.append(
            _fact(
                feature_id=feature_id,
                value_present=present,
                value=value,
                unit=unit,
                method_kind=method_kind,
                binding=binding,
                null_reason="OWNER_FIELD_UNAVAILABLE",
                stale_at_decision=stale_at_decision,
                adapter_limitations=adapter_limitations,
            )
        )
    return facts


def adapt_regime_vector(
    payload: Mapping[str, Any],
    binding: OwnerArtifactBinding,
    *,
    market_session: str,
    decision_at: str,
) -> list[OwnerFact]:
    """Adapt passive regime owner fields; never carry directive-like controls."""
    stale_at_decision = _validate_binding(binding, decision_at=decision_at)
    if not isinstance(payload, Mapping):
        _fail("REGIME_VECTOR_OBJECT_REQUIRED")
    if payload.get("schema_version") != 1:
        _fail("REGIME_VECTOR_SCHEMA_INVALID")
    if payload.get("asof") != market_session:
        _fail("REGIME_VECTOR_SESSION_MISMATCH")
    _validate_payload_binding(payload, binding)

    # Refuse a future accidental extension that tries to include incumbent
    # directives in the passive mapping table.
    adapted_roots = {keys[0] for _, keys, _, _ in _REGIME_VECTOR_FIELDS}
    if adapted_roots & _FORBIDDEN_REGIME_VECTOR_FIELDS:
        _fail("DIRECTIVE_FIELD_FORBIDDEN")

    facts: list[OwnerFact] = []
    adapter_limitations = (
        "regime_vector is consumed as owner context; PTSE does not re-derive its axes.",
        "Directive-like owner fields are intentionally excluded from the PTSE fact mapping.",
        "A regime label or score does not grant PTSE rank, gate, sizing, or trade authority.",
    )
    for feature_id, keys, unit, method_kind in _REGIME_VECTOR_FIELDS:
        present, value = _path(payload, keys)
        present = bool(present and value is not None)
        facts.append(
            _fact(
                feature_id=feature_id,
                value_present=present,
                value=value,
                unit=unit,
                method_kind=method_kind,
                binding=binding,
                null_reason="OWNER_FIELD_UNAVAILABLE",
                stale_at_decision=stale_at_decision,
                adapter_limitations=adapter_limitations,
            )
        )
    return facts


def compose_owner_facts(
    *,
    market_session: str,
    decision_at: str,
    market_state: Mapping[str, Any] | None = None,
    market_state_binding: OwnerArtifactBinding | None = None,
    regime_vector: Mapping[str, Any] | None = None,
    regime_vector_binding: OwnerArtifactBinding | None = None,
) -> list[OwnerFact]:
    """Compose one deterministic fact set from zero-I/O owner payloads.

    A payload and its binding are an inseparable pair. At least one source must
    be supplied. The weaker evidence grade remains attached per fact; this
    function never upgrades provenance.
    """
    if (market_state is None) != (market_state_binding is None):
        _fail("MARKET_STATE_BINDING_REQUIRED")
    if (regime_vector is None) != (regime_vector_binding is None):
        _fail("REGIME_VECTOR_BINDING_REQUIRED")
    if market_state is None and regime_vector is None:
        _fail("OWNER_SOURCE_REQUIRED")

    facts: list[OwnerFact] = []
    if market_state is not None:
        facts.extend(
            adapt_market_state(
                copy.deepcopy(dict(market_state)),
                market_state_binding,
                market_session=market_session,
                decision_at=decision_at,
            )
        )
    if regime_vector is not None:
        facts.extend(
            adapt_regime_vector(
                copy.deepcopy(dict(regime_vector)),
                regime_vector_binding,
                market_session=market_session,
                decision_at=decision_at,
            )
        )

    facts.sort(key=lambda fact: fact["feature_id"])
    if len({fact["feature_id"] for fact in facts}) != len(facts):
        _fail("DUPLICATE_FEATURE")
    return facts


__all__ = [
    "PTSEOwnerAdapterError",
    "OwnerArtifactBinding",
    "adapt_market_state",
    "adapt_regime_vector",
    "compose_owner_facts",
]
