"""Pure PTSE adapter for the incumbent current-tip breadth snapshot.

The owner is engine.neuralweb.market_memory_breadth_observation. This adapter
performs no I/O, membership reconstruction, history backfill, scoring, model
fit, publication, ranking, gating, sizing, or trade effect.

Only market_memory.breadth_factors_snapshot.v1 is accepted. Its current
membership / survivor-bias limitations remain explicit. Earlier recomputed
breadth rows are never promoted to point-in-time history. The owner snapshot is
clock-free, so caller-supplied first-durable-write availability is mandatory
before a prospective evidence grade can be meaningful.

The Market Memory mmsecurity instrument identity is preserved. This module does
not invent a mapping to Data OS SEC identity.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timezone
import hashlib
import json
import math
import re
from typing import Any, Final
from zoneinfo import ZoneInfo

from research.options_estate.ptse_contract import (
    EvidenceGrade,
    EvidenceRef,
    GRADES,
    OwnerFact,
    _time,
)


SCHEMA: Final = "market_memory.breadth_factors_snapshot.v1"
TRANSFORM: Final = "market_memory.breadth_factors_transform.v1"
_ET: Final = ZoneInfo("America/New_York")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_SNAPSHOT = re.compile(r"mmsnap_[0-9a-f]{64}\Z")
_SOURCE = re.compile(r"mmbreadthsrc_[0-9a-f]{64}\Z")

_STATE_FIELDS: Final = (
    ("breadth.advancers", "advancers", "COUNT"),
    ("breadth.constituent_count", "constituent_count", "COUNT"),
    ("breadth.decliners", "decliners", "COUNT"),
    ("breadth.new_highs", "new_highs", "COUNT"),
    ("breadth.new_lows", "new_lows", "COUNT"),
    ("breadth.pct_above_200", "pct_above_200", "PERCENT"),
    ("breadth.pct_above_50", "pct_above_50", "PERCENT"),
    ("breadth.priced_member_coverage", "priced_member_coverage", "FRACTION"),
    ("breadth.priced_members", "n_members", "COUNT"),
)


class PTSEBreadthAdapterError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise PTSEBreadthAdapterError(code)


@dataclass(frozen=True)
class BreadthSnapshotBinding:
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
    calculation_version: str
    limitations: tuple[str, ...]


def _ref(value: Mapping[str, Any]) -> dict[str, str]:
    if (
        not isinstance(value, Mapping)
        or set(value) != {"owner_ref", "artifact_id", "sha256"}
        or not all(isinstance(value.get(k), str) and value.get(k) for k in value)
    ):
        _fail("EVIDENCE_REF_INVALID")
    digest = value.get("sha256")
    if not isinstance(digest, str) or _HASH.fullmatch(digest) is None:
        _fail("EVIDENCE_REF_INVALID")
    return dict(value)


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    try:
        wire = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise PTSEBreadthAdapterError("BREADTH_PAYLOAD_INVALID") from exc
    return hashlib.sha256(wire).hexdigest()


def _binding(binding: BreadthSnapshotBinding, *, decision_at: str) -> bool:
    artifact = _ref(binding.artifact_ref)
    _ref(binding.known_at_evidence_ref)
    _ref(binding.population_ref)
    if (
        not isinstance(binding.owner_ref, str)
        or not binding.owner_ref
        or artifact["owner_ref"] != binding.owner_ref
    ):
        _fail("OWNER_BINDING_INVALID")
    if binding.known_at_precision not in {"EXACT", "INTERVAL", "DATE_ONLY"}:
        _fail("KNOWN_AT_PRECISION_INVALID")
    if binding.evidence_grade not in GRADES:
        _fail("EVIDENCE_GRADE_INVALID")
    if (
        not isinstance(binding.calculation_version, str)
        or not binding.calculation_version
        or not binding.limitations
        or any(not isinstance(x, str) or not x for x in binding.limitations)
    ):
        _fail("BINDING_INVALID")
    earliest = _time(binding.known_at_earliest, "breadth.known_at_earliest")
    latest = _time(binding.known_at_latest, "breadth.known_at_latest")
    economic = _time(binding.economic_time, "breadth.economic_time")
    decision = _time(decision_at, "breadth.decision_at")
    expiry = _time(binding.valid_until, "breadth.valid_until")
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


def _require_mapping(value: Any, keys: set[str], code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        _fail(code)
    return value


def _validate_authority(value: Any) -> None:
    if not isinstance(value, Mapping):
        _fail("BREADTH_AUTHORITY_INVALID")
    if (
        value.get("tier") != "display"
        or value.get("horizon_role") != "context"
        or value.get("context_only") is not True
        or value.get("proposal_weight") != 0
    ):
        _fail("BREADTH_AUTHORITY_INVALID")
    for key, item in value.items():
        if key.startswith("may_") and item is not False:
            _fail("BREADTH_AUTHORITY_INVALID")


def _validate_snapshot(
    payload: Mapping[str, Any],
    binding: BreadthSnapshotBinding,
    *,
    market_session: str,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    top = {
        "schema", "snapshot_id", "source_observation_id", "session",
        "transform_version", "subject", "state", "quality", "limitations",
        "authority",
    }
    _require_mapping(payload, top, "BREADTH_SCHEMA_INVALID")
    if payload.get("schema") != SCHEMA or payload.get("transform_version") != TRANSFORM:
        _fail("BREADTH_SCHEMA_INVALID")
    if payload.get("session") != market_session:
        _fail("BREADTH_SESSION_MISMATCH")
    if not isinstance(payload.get("snapshot_id"), str) or _SNAPSHOT.fullmatch(payload["snapshot_id"]) is None:
        _fail("BREADTH_IDENTITY_INVALID")
    if not isinstance(payload.get("source_observation_id"), str) or _SOURCE.fullmatch(payload["source_observation_id"]) is None:
        _fail("BREADTH_IDENTITY_INVALID")

    artifact = _ref(binding.artifact_ref)
    if (
        artifact["artifact_id"] != payload["snapshot_id"]
        or artifact["sha256"] != _canonical_sha256(payload)
    ):
        _fail("BREADTH_ARTIFACT_REF_MISMATCH")

    subject = _require_mapping(
        payload["subject"],
        {
            "symbol", "subject_id", "instrument_id", "identity_version", "mic",
            "currency", "universe_id", "calendar_id", "market_session",
        },
        "BREADTH_SUBJECT_INVALID",
    )
    if (
        subject.get("symbol") != "SPY"
        or subject.get("mic") != "ARCX"
        or subject.get("currency") != "USD"
        or subject.get("market_session") != "XNYS_REGULAR"
        or not all(
            isinstance(subject.get(k), str) and subject.get(k)
            for k in ("subject_id", "instrument_id", "identity_version", "universe_id", "calendar_id")
        )
    ):
        _fail("BREADTH_SUBJECT_INVALID")
    if _ref(binding.population_ref)["artifact_id"] != subject["universe_id"]:
        _fail("BREADTH_POPULATION_REF_MISMATCH")

    quality = _require_mapping(
        payload["quality"],
        {
            "status", "flags", "actual_output_source", "current_tip_only",
            "imputed", "training_eligible", "promotion_eligible",
        },
        "BREADTH_QUALITY_INVALID",
    )
    if (
        quality.get("status") != "degraded"
        or quality.get("actual_output_source") is not True
        or quality.get("current_tip_only") is not True
        or quality.get("imputed") is not False
        or quality.get("training_eligible") is not False
        or quality.get("promotion_eligible") is not False
        or quality.get("flags") != ["partial_coverage"]
    ):
        _fail("BREADTH_QUALITY_INVALID")

    limits = _require_mapping(
        payload["limitations"],
        {
            "current_membership_only", "current_membership_survivor_bias",
            "historical_constituent_point_in_time", "calendar_coverage",
            "calendar_partial_coverage", "ad_line_excluded",
        },
        "BREADTH_LIMITATIONS_INVALID",
    )
    if (
        limits.get("current_membership_only") is not True
        or limits.get("current_membership_survivor_bias") is not True
        or limits.get("historical_constituent_point_in_time") is not False
        or limits.get("calendar_coverage") != "full_day_closures_only"
        or limits.get("calendar_partial_coverage") is not True
        or limits.get("ad_line_excluded") is not True
    ):
        _fail("BREADTH_LIMITATIONS_INVALID")
    _validate_authority(payload["authority"])

    state = _require_mapping(
        payload["state"],
        {
            "n_members", "constituent_count", "priced_member_coverage",
            "pct_above_50", "pct_above_200", "new_highs", "new_lows",
            "advancers", "decliners",
        },
        "BREADTH_STATE_INVALID",
    )
    count = state.get("constituent_count")
    members = state.get("n_members")
    if (
        type(count) is not int
        or type(members) is not int
        or count <= 0
        or not 0 <= members <= count
    ):
        _fail("BREADTH_STATE_INVALID")
    for key in ("new_highs", "new_lows", "advancers", "decliners"):
        value = state.get(key)
        if type(value) is not int or not 0 <= value <= members:
            _fail("BREADTH_STATE_INVALID")
    if state["advancers"] + state["decliners"] > members:
        _fail("BREADTH_STATE_INVALID")
    for key in ("pct_above_50", "pct_above_200"):
        value = state.get(key)
        if type(value) not in (int, float) or not math.isfinite(float(value)) or not 0 <= float(value) <= 100:
            _fail("BREADTH_STATE_INVALID")
    coverage = state.get("priced_member_coverage")
    if (
        type(coverage) not in (int, float)
        or not math.isfinite(float(coverage))
        or not 0 <= float(coverage) <= 1
        or not math.isclose(float(coverage), members / count, rel_tol=1e-12, abs_tol=1e-12)
    ):
        _fail("BREADTH_COVERAGE_INVALID")
    return subject, state


def _fact(
    *,
    feature_id: str,
    value: int | float,
    unit: str,
    subject: Mapping[str, Any],
    state: Mapping[str, Any],
    binding: BreadthSnapshotBinding,
    stale: bool,
) -> OwnerFact:
    count = state["constituent_count"]
    members = state["n_members"]
    missing = count - members
    status = "STALE" if stale else ("PARTIAL" if missing else "OBSERVED")
    limitations = list(binding.limitations) + [
        "Current-tip breadth uses current constituent membership and is not historical PIT breadth.",
        "Current-membership survivor bias is explicit; historical_constituent_point_in_time is false.",
        "Owner quality is degraded/partial-coverage, training_eligible=false and promotion_eligible=false.",
        "ad_line is deliberately excluded by the incumbent breadth owner.",
        "Market Memory mmsecurity source identity is preserved; PTSE does not mint a Data OS SEC mapping.",
    ]
    return {
        "feature_id": feature_id,
        "owner_ref": binding.owner_ref,
        "source_artifact_ref": _ref(binding.artifact_ref),
        "economic_time": binding.economic_time,
        "economic_time_role": "OBSERVATION",
        "known_at": {
            "earliest": binding.known_at_earliest,
            "latest": binding.known_at_latest,
            "precision": binding.known_at_precision,
            "evidence_ref": _ref(binding.known_at_evidence_ref),
        },
        "valid_until": binding.valid_until,
        "value": value,
        "unit": unit,
        "status": status,
        "method_kind": "DETERMINISTIC_COMPUTATION",
        "calculation_version": binding.calculation_version,
        "evidence_grade": binding.evidence_grade,
        "coverage": {
            "numerator": members,
            "denominator": count,
            "missing_count": missing,
            "population_ref": _ref(binding.population_ref),
        },
        "source_scope": {
            "instrument_id": subject["instrument_id"],
            "session_scope": "REGULAR",
            "population_ref": _ref(binding.population_ref),
            "position_scope": "NOT_APPLICABLE",
            "side_semantics": "NOT_APPLICABLE",
        },
        "limitations": limitations,
        "null_reason": "SOURCE_EXPIRED_AT_DECISION" if stale else None,
    }


def adapt_breadth_snapshot(
    payload: Mapping[str, Any],
    binding: BreadthSnapshotBinding,
    *,
    market_session: str,
    decision_at: str,
) -> list[OwnerFact]:
    """Translate the owner current-tip snapshot into denominator-aware facts."""

    stale = _binding(binding, decision_at=decision_at)
    if not isinstance(payload, Mapping):
        _fail("BREADTH_OBJECT_REQUIRED")
    subject, state = _validate_snapshot(
        payload, binding, market_session=market_session
    )
    economic = _time(binding.economic_time, "breadth.economic_time")
    if economic.astimezone(_ET).date().isoformat() != market_session:
        _fail("BREADTH_ECONOMIC_SESSION_MISMATCH")

    facts = [
        _fact(
            feature_id=feature_id,
            value=state[key],
            unit=unit,
            subject=subject,
            state=state,
            binding=binding,
            stale=stale,
        )
        for feature_id, key, unit in _STATE_FIELDS
    ]
    facts.sort(key=lambda fact: fact["feature_id"])
    return facts


__all__ = [
    "PTSEBreadthAdapterError",
    "BreadthSnapshotBinding",
    "adapt_breadth_snapshot",
]