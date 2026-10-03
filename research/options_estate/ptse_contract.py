"""PTSE owner-evidence contract and optional-consumer guard, research v1.

Pure functions only: no collection, clock reads, filesystem, network, calendar
calculation, model fitting, persistence, scheduling or decision mutation. Source
and publication admission remain with their existing owners. A valid record is
software conformance, NOT evidence that a source or strategy has been qualified.

The namespace is a candidate for owner review under Macro #7925 / #8325. This
initial revision admits observations and NOT_FITTED/abstained assessments, not
numerical forecasts. All six actions are typed; the first live consumer slice is
US / regular-session / H5 / NEW_ENTRY. Other actions are not entry vetoes: their
optional context simply remains unavailable until independently admitted.

ConsumerBinding is trusted, out-of-band input from the incumbent request and
accepted publication/source receipts. Never construct it from the untrusted
context payload or accept the payload's own hash as external admission evidence.
The future production integration must bind it at the existing API/consumer.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
import copy
import hashlib
import json
import math
import re
from typing import Any, Final, Literal, TypedDict

SCHEMA: Final = "prophet.timing_context/v1-research"
CANONICALIZATION: Final = "ptse-json/v1"
ACTIONS: Final = ("NEW_ENTRY", "CONTINUATION", "PULLBACK_BUY", "ADD", "REENTRY", "DERISK")
AUTHORITY_KEYS: Final = ("rank", "admission", "entry_gating", "plan_mutation", "alert_escalation",
                         "sizing", "portfolio", "execution", "trade")
STATUSES: Final = ("OBSERVED", "PARTIAL", "STALE", "UNAVAILABLE", "CONFLICTED", "NOT_APPLICABLE")
GRADES: Final = {"SYNTHETIC": 0, "RETROSPECTIVE_PIT_UNPROVEN": 1,
                "PIT_QUALIFIED_REPLAY": 2, "PROSPECTIVE_FIRST_SEEN": 3}
UNITS: Final = frozenset({"DIMENSIONLESS", "FRACTION", "PERCENT", "BASIS_POINTS", "LOG_RETURN",
                         "POINTS", "USD", "SHARES", "CONTRACTS", "COUNT", "SESSIONS",
                         "ANNUALIZED_VOLATILITY", "ANNUALIZED_VARIANCE", "BOOLEAN", "STATE", "TEXT",
                         "TIMESTAMP", "USD_PER_ONE_PERCENT_MOVE", "USD_PER_VOLATILITY_POINT"})
MAX_WIRE_BYTES: Final = 1_048_576  # Transport bound, not a statistical/support threshold.
MAX_SAFE_INTEGER: Final = 9_007_199_254_740_991
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_REV = re.compile(r"[0-9a-f]{40}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+#=%|~-]*\Z")

Action = Literal["NEW_ENTRY", "CONTINUATION", "PULLBACK_BUY", "ADD", "REENTRY", "DERISK"]
FactStatus = Literal["OBSERVED", "PARTIAL", "STALE", "UNAVAILABLE", "CONFLICTED", "NOT_APPLICABLE"]
EvidenceGrade = Literal["SYNTHETIC", "RETROSPECTIVE_PIT_UNPROVEN", "PIT_QUALIFIED_REPLAY", "PROSPECTIVE_FIRST_SEEN"]


class EvidenceRef(TypedDict):
    owner_ref: str
    artifact_id: str
    sha256: str


class KnownAt(TypedDict):
    earliest: str
    latest: str
    precision: Literal["EXACT", "INTERVAL", "DATE_ONLY"]
    evidence_ref: EvidenceRef


class Coverage(TypedDict):
    numerator: int
    denominator: int | None
    missing_count: int | None
    population_ref: EvidenceRef


class SourceScope(TypedDict):
    instrument_id: str
    session_scope: Literal["REGULAR", "EXTENDED", "ALL", "OWNER_DEFINED"]
    population_ref: EvidenceRef
    position_scope: Literal["NOT_APPLICABLE", "WINDOWED", "FULL_BOOK"]
    side_semantics: Literal["NOT_APPLICABLE", "UNSIGNED_GROSS", "ASSUMED_DEALER_SCENARIO", "MEASURED_TRADE_SIDE"]


class OwnerFact(TypedDict):
    feature_id: str
    owner_ref: str
    source_artifact_ref: EvidenceRef
    economic_time: str
    economic_time_role: Literal["OBSERVATION", "SCHEDULED_EVENT"]
    known_at: KnownAt | None
    valid_until: str
    value: int | float | bool | str | None
    unit: str
    status: FactStatus
    method_kind: Literal["OBSERVATION", "DETERMINISTIC_COMPUTATION", "STATISTICAL_ESTIMATE", "GROUNDED_SYNTHESIS"]
    calculation_version: str
    evidence_grade: EvidenceGrade
    coverage: Coverage
    source_scope: SourceScope
    limitations: list[str]
    null_reason: str | None


class Observation(TypedDict):
    observation_id: str
    market: str
    instrument_id: str
    market_session: str
    cadence: Literal["DAILY", "INTRADAY"]
    session_scope: Literal["REGULAR", "EXTENDED", "ALL", "OWNER_DEFINED"]
    decision_at: str
    issued_at: str
    valid_until: str
    calendar_ref: EvidenceRef
    freshness_ref: EvidenceRef
    source_manifest_ref: EvidenceRef
    calculation_receipt_ref: EvidenceRef
    producer_revision: str
    feature_version: str
    evidence_grade: EvidenceGrade
    reconstructed_at: str | None
    supersedes_ref: str | None
    correction_reason: str | None
    facts: list[OwnerFact]


class ActionAssessment(TypedDict):
    assessment_id: str
    observation_id: str
    episode_id: str
    security_id: str
    company_id: str
    identity_epoch: str
    candidate_generation_id: str
    cohort_ref: EvidenceRef
    strategy_id: str
    strategy_version: str
    holding_horizon_ref: EvidenceRef
    action: Action
    decision_at: str
    issued_at: str
    forecast_horizon_sessions: int
    forecast_end_session: str
    calendar_ref: EvidenceRef
    target_version: str
    applicability: Literal["APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"]
    applicability_reason: str
    eligibility_ref: EvidenceRef | None
    position_ref: EvidenceRef | None
    geometry_ref: EvidenceRef | None
    risk_budget_ref: EvidenceRef | None
    prior_exit_episode_ref: EvidenceRef | None
    evidence_status: Literal["OBSERVED_CONTEXT_ONLY", "ABSTAINED"]
    estimate_status: Literal["NOT_FITTED", "ABSTAINED"]
    estimate: None
    drivers: list[str]
    contradictions: list[str]
    authority: dict[str, bool]


class ContractViolation(ValueError):
    """Closed reason code plus a field path; never echoes untrusted payloads."""
    def __init__(self, code: str, path: str = "$") -> None:
        self.code, self.path = code, path
        super().__init__(f"{code}: {path}")


def _fail(code: str, path: str) -> None:
    raise ContractViolation(code, path)


def _keys(value: Any, required: set[str], path: str, optional: set[str] | None = None) -> dict:
    if not isinstance(value, dict) or any(not isinstance(k, str) for k in value):
        _fail("OBJECT_REQUIRED", path)
    if set(value) - required - (optional or set()) or required - set(value):
        _fail("FIELD_SET", path)
    return value


def _text(value: Any, path: str, *, identifier: bool = False) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > 4096:
        _fail("TEXT_REQUIRED", path)
    if any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        _fail("TEXT_INVALID", path)
    if identifier and not _ID.fullmatch(value):
        _fail("IDENTIFIER_REQUIRED", path)
    return value


def _choice(value: Any, choices: Any, path: str, code: str = "ENUM_UNKNOWN") -> str:
    if not isinstance(value, str) or value not in choices:
        _fail(code, path)
    return value


def _integer(value: Any, path: str, *, minimum: int = 0) -> int:
    if type(value) is not int or not minimum <= value <= MAX_SAFE_INTEGER:
        _fail("INTEGER_REQUIRED", path)
    return value


def _hash(value: Any, path: str) -> str:
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        _fail("DIGEST_REQUIRED", path)
    return value


def _ref(value: Any, path: str) -> dict:
    _keys(value, {"owner_ref", "artifact_id", "sha256"}, path)
    _text(value["owner_ref"], path + ".owner_ref", identifier=True)
    _text(value["artifact_id"], path + ".artifact_id", identifier=True)
    _hash(value["sha256"], path + ".sha256")
    return value


def _time(value: Any, path: str) -> datetime:
    if not isinstance(value, str) or not re.match(r"^\d{4}-\d{2}-\d{2}T", value):
        _fail("TIMESTAMP_REQUIRED", path)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _fail("TIMESTAMP_INVALID", path)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail("TIMEZONE_REQUIRED", path)
    return parsed.astimezone(timezone.utc)


def _stamp(record: dict, key: str, path: str) -> datetime:
    parsed = _time(record[key], path + "." + key)
    record[key] = parsed.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return parsed


def _session(value: Any, path: str) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        _fail("SESSION_REQUIRED", path)
    try:
        return date.fromisoformat(value)
    except ValueError:
        _fail("SESSION_INVALID", path)


def _json_tree(value: Any) -> Any:
    """Deterministic Python JSON v1; integer-valued floats and -0 normalize."""
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        if abs(value) > MAX_SAFE_INTEGER:
            _fail("UNSAFE_JSON_INTEGER", "$")
        return value
    if type(value) is float:
        if not math.isfinite(value) or abs(value) > MAX_SAFE_INTEGER:
            _fail("NONFINITE_OR_UNSAFE_NUMBER", "$")
        return int(value) if value.is_integer() else value
    if isinstance(value, str):
        if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            _fail("TEXT_INVALID", "$")
        return value
    if isinstance(value, list):
        return [_json_tree(x) for x in value]
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        return {k: _json_tree(v) for k, v in value.items()}
    _fail("NON_JSON_TYPE", "$")


def canonical_json(value: Any) -> bytes:
    """Versioned UTF-8/sorted-key JSON, not a claim of RFC-8785 compatibility."""
    try:
        return json.dumps(_json_tree(value), sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, ContractViolation):
            raise
        raise ContractViolation("CANONICALIZATION_FAILED") from exc


def _pairs(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for k, v in pairs:
        if k in result:
            _fail("DUPLICATE_JSON_KEY", "$")
        result[k] = v
    return result


def _constant(_: str) -> None:
    _fail("NONFINITE_OR_UNSAFE_NUMBER", "$")


def _parse(raw: bytes | str) -> dict:
    if not isinstance(raw, (bytes, str)):
        _fail("WIRE_TYPE", "$")
    try:
        wire = raw.encode("utf-8") if isinstance(raw, str) else raw
        if len(wire) > MAX_WIRE_BYTES:
            _fail("PAYLOAD_TOO_LARGE", "$")
        if wire.startswith(b"\xef\xbb\xbf"):
            _fail("BOM_FORBIDDEN", "$")
        value = json.loads(wire.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
        if not isinstance(value, dict):
            _fail("OBJECT_REQUIRED", "$")
        return _json_tree(value)
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, ContractViolation):
            raise
        raise ContractViolation("INVALID_JSON") from exc


def _fact(f: dict, decision: datetime, path: str) -> dict:
    required = set(OwnerFact.__required_keys__)
    _keys(f, required, path)
    for key in ["feature_id", "owner_ref", "calculation_version"]:
        _text(f[key], path + "." + key, identifier=True)
    _ref(f["source_artifact_ref"], path + ".source_artifact_ref")
    if f["owner_ref"] != f["source_artifact_ref"]["owner_ref"]:
        _fail("OWNER_MISMATCH", path)
    economic = _stamp(f, "economic_time", path)
    expiry = _stamp(f, "valid_until", path)
    role = _choice(f["economic_time_role"], {"OBSERVATION", "SCHEDULED_EVENT"}, path + ".economic_time_role")
    status = _choice(f["status"], STATUSES, path + ".status")
    grade = _choice(f["evidence_grade"], GRADES, path + ".evidence_grade")
    unit = _choice(f["unit"], UNITS, path + ".unit", "UNIT_UNKNOWN")
    method = _choice(f["method_kind"], {"OBSERVATION", "DETERMINISTIC_COMPUTATION", "STATISTICAL_ESTIMATE", "GROUNDED_SYNTHESIS"}, path + ".method_kind")
    if role == "OBSERVATION" and economic > decision:
        _fail("FUTURE_ECONOMIC_OBSERVATION", path)
    if role == "SCHEDULED_EVENT" and unit not in {"TIMESTAMP", "STATE"}:
        _fail("SCHEDULE_IS_NOT_RELEASE_OUTCOME", path)
    if not isinstance(f["limitations"], list) or not f["limitations"]:
        _fail("LIMITATIONS_REQUIRED", path)
    for value in f["limitations"]:
        _text(value, path + ".limitations")
    if f["null_reason"] is not None:
        _text(f["null_reason"], path + ".null_reason")
    nullable = status in {"UNAVAILABLE", "CONFLICTED", "NOT_APPLICABLE"}
    if nullable:
        if f["value"] is not None or f["null_reason"] is None:
            _fail("NULL_CONTRACT", path)
    elif f["value"] is None:
        _fail("NULL_CONTRACT", path)
    elif status == "STALE":
        if f["null_reason"] is None or expiry > decision:
            _fail("FRESHNESS_STATUS_MISMATCH", path)
    elif expiry <= decision or f["null_reason"] is not None:
        _fail("FRESHNESS_STATUS_MISMATCH", path)

    k = f["known_at"]
    if k is None:
        if not nullable and not (grade == "RETROSPECTIVE_PIT_UNPROVEN" and status == "PARTIAL"):
            _fail("AVAILABILITY_REQUIRED", path)
    else:
        _keys(k, set(KnownAt.__required_keys__), path + ".known_at")
        earliest = _stamp(k, "earliest", path + ".known_at")
        latest = _stamp(k, "latest", path + ".known_at")
        precision = _choice(k["precision"], {"EXACT", "INTERVAL", "DATE_ONLY"}, path + ".known_at.precision")
        _ref(k["evidence_ref"], path + ".known_at.evidence_ref")
        if earliest > latest or (precision == "EXACT" and earliest != latest) or (precision == "DATE_ONLY" and earliest == latest):
            _fail("AVAILABILITY_PRECISION_MISMATCH", path)
        if not nullable and latest > decision:
            _fail("NOT_KNOWN_AT_DECISION", path)
        if not nullable and role == "OBSERVATION" and economic > latest:
            _fail("AVAILABILITY_PRECEDES_OBSERVATION", path)

    c = _keys(f["coverage"], set(Coverage.__required_keys__), path + ".coverage")
    n = _integer(c["numerator"], path + ".coverage.numerator")
    _ref(c["population_ref"], path + ".coverage.population_ref")
    if c["denominator"] is None:
        if c["missing_count"] is not None or status not in {"PARTIAL", "UNAVAILABLE", "CONFLICTED"}:
            _fail("COVERAGE_MISMATCH", path)
    else:
        d = _integer(c["denominator"], path + ".coverage.denominator")
        m = _integer(c["missing_count"], path + ".coverage.missing_count")
        if n + m != d:
            _fail("COVERAGE_MISMATCH", path)
        if status == "OBSERVED" and (d == 0 or n != d):
            _fail("COVERAGE_STATUS_MISMATCH", path)
        if status == "PARTIAL" and (n == 0 or n == d):
            _fail("COVERAGE_STATUS_MISMATCH", path)
    if nullable and n != 0:
        _fail("COVERAGE_STATUS_MISMATCH", path)

    s = _keys(f["source_scope"], set(SourceScope.__required_keys__), path + ".source_scope")
    _text(s["instrument_id"], path + ".source_scope.instrument_id", identifier=True)
    _choice(s["session_scope"], {"REGULAR", "EXTENDED", "ALL", "OWNER_DEFINED"}, path + ".source_scope.session_scope")
    _choice(s["position_scope"], {"NOT_APPLICABLE", "WINDOWED", "FULL_BOOK"}, path + ".source_scope.position_scope")
    _choice(s["side_semantics"], {"NOT_APPLICABLE", "UNSIGNED_GROSS", "ASSUMED_DEALER_SCENARIO", "MEASURED_TRADE_SIDE"}, path + ".source_scope.side_semantics")
    _ref(s["population_ref"], path + ".source_scope.population_ref")
    if s["population_ref"] != c["population_ref"]:
        _fail("POPULATION_MISMATCH", path)

    v = f["value"]
    if v is not None:
        if method == "GROUNDED_SYNTHESIS" and (unit != "TEXT" or not isinstance(v, str)):
            _fail("NUMERIC_SYNTHESIS_FORBIDDEN", path)
        if unit == "BOOLEAN":
            if type(v) is not bool:
                _fail("BOOLEAN_REQUIRED", path)
        elif unit in {"STATE", "TEXT", "TIMESTAMP"}:
            _text(v, path + ".value")
            if unit == "TIMESTAMP":
                f["value"] = _time(v, path + ".value").isoformat(timespec="microseconds").replace("+00:00", "Z")
        else:
            if type(v) not in (int, float) or not math.isfinite(v) or abs(v) > MAX_SAFE_INTEGER:
                _fail("NUMERIC_VALUE_REQUIRED", path)
            if unit in {"COUNT", "SESSIONS", "CONTRACTS", "SHARES"}:
                _integer(v, path + ".value")
            if unit == "FRACTION" and not 0 <= v <= 1:
                _fail("UNIT_RANGE", path)
            if unit in {"ANNUALIZED_VARIANCE", "ANNUALIZED_VOLATILITY"} and v < 0:
                _fail("UNIT_RANGE", path)
    return f


def _observation_identity(o: dict) -> str:
    economic = {k: v for k, v in o.items() if k not in {"observation_id", "issued_at", "reconstructed_at", "correction_reason"}}
    return "obs:" + hashlib.sha256(canonical_json(economic)).hexdigest()


def _observation(o: dict, *, sealed: bool) -> dict:
    p = "$.observation"
    required = set(Observation.__required_keys__) - {"observation_id"}
    _keys(o, required | ({"observation_id"} if sealed else set()), p, {"observation_id"})
    for key in ["market", "instrument_id", "feature_version"]:
        _text(o[key], p + "." + key, identifier=True)
    _session(o["market_session"], p + ".market_session")
    _choice(o["cadence"], {"DAILY", "INTRADAY"}, p + ".cadence")
    _choice(o["session_scope"], {"REGULAR", "EXTENDED", "ALL", "OWNER_DEFINED"}, p + ".session_scope")
    decision = _stamp(o, "decision_at", p); issued = _stamp(o, "issued_at", p)
    expiry = _stamp(o, "valid_until", p)
    if issued < decision or expiry <= decision:
        _fail("CLOCK_ORDER", p)
    for key in ["calendar_ref", "freshness_ref", "source_manifest_ref", "calculation_receipt_ref"]:
        _ref(o[key], p + "." + key)
    if not isinstance(o["producer_revision"], str) or not _REV.fullmatch(o["producer_revision"]):
        _fail("REVISION_REQUIRED", p)
    grade = _choice(o["evidence_grade"], GRADES, p + ".evidence_grade")
    reconstruction = None
    if o["reconstructed_at"] is not None:
        reconstruction = _stamp(o, "reconstructed_at", p)
        if not decision <= reconstruction <= issued:
            _fail("CLOCK_ORDER", p + ".reconstructed_at")
    if grade in {"RETROSPECTIVE_PIT_UNPROVEN", "PIT_QUALIFIED_REPLAY"} and reconstruction is None:
        _fail("RECONSTRUCTION_REQUIRED", p)
    if grade == "PROSPECTIVE_FIRST_SEEN" and reconstruction is not None:
        _fail("PROSPECTIVE_RECONSTRUCTION_FORBIDDEN", p)
    if not isinstance(o["facts"], list) or not o["facts"]:
        _fail("FACTS_REQUIRED", p)
    seen = set()
    for i, f in enumerate(o["facts"]):
        _fact(f, decision, p + f".facts[{i}]")
        if f["feature_id"] in seen:
            _fail("DUPLICATE_FEATURE", p)
        seen.add(f["feature_id"])
        # A missing optional family carries its own null/grade, not a global veto.
        # Present values still cannot inherit stronger PIT provenance than their source.
        if f["value"] is not None and GRADES[grade] > GRADES[f["evidence_grade"]]:
            _fail("GRADE_UPGRADE_FORBIDDEN", p)
    o["facts"].sort(key=lambda f: f["feature_id"])
    if (o["supersedes_ref"] is None) != (o["correction_reason"] is None):
        _fail("CORRECTION_PAIR_REQUIRED", p)
    if o["supersedes_ref"] is not None:
        if not isinstance(o["supersedes_ref"], str) or not re.fullmatch(r"obs:[0-9a-f]{64}", o["supersedes_ref"]):
            _fail("OBSERVATION_REFERENCE_REQUIRED", p)
        _text(o["correction_reason"], p + ".correction_reason")
    oid = _observation_identity(o)
    if "observation_id" in o and o["observation_id"] != oid:
        _fail("IDENTITY_MISMATCH", p)
    if oid == o["supersedes_ref"]:
        _fail("SELF_SUPERSESSION", p)
    o["observation_id"] = oid
    return o


def _assessment(a: dict, o: dict, *, sealed: bool) -> dict:
    p = "$.assessment"
    ids = {"assessment_id", "observation_id"}
    required = set(ActionAssessment.__required_keys__) - ids
    _keys(a, required | (ids if sealed else set()), p, ids)
    for key in ["episode_id", "security_id", "company_id", "identity_epoch", "candidate_generation_id", "strategy_id", "strategy_version", "target_version"]:
        _text(a[key], p + "." + key, identifier=True)
    for key in ["cohort_ref", "holding_horizon_ref", "calendar_ref"]:
        _ref(a[key], p + "." + key)
    decision = _stamp(a, "decision_at", p); issued = _stamp(a, "issued_at", p)
    if decision != _time(o["decision_at"], p) or issued < _time(o["issued_at"], p):
        _fail("CLOCK_ORDER", p)
    _integer(a["forecast_horizon_sessions"], p + ".forecast_horizon_sessions", minimum=1)
    end = _session(a["forecast_end_session"], p + ".forecast_end_session")
    if end <= _session(o["market_session"], p):
        _fail("HORIZON_ORDER", p)
    if a["calendar_ref"] != o["calendar_ref"]:
        _fail("CALENDAR_MISMATCH", p)
    # No weekday arithmetic: the incumbent calendar supplies/accepts the exact end session.
    action = _choice(a["action"], ACTIONS, p + ".action")
    applicability = _choice(a["applicability"], {"APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"}, p + ".applicability")
    _text(a["applicability_reason"], p + ".applicability_reason")
    refs = {"eligibility_ref", "position_ref", "geometry_ref", "risk_budget_ref", "prior_exit_episode_ref"}
    for key in refs:
        if a[key] is not None:
            _ref(a[key], p + "." + key)
    if applicability != "UNKNOWN" and a["eligibility_ref"] is None:
        _fail("ACTION_BINDING_REQUIRED", p + ".eligibility_ref")
    required_refs = {
        "NEW_ENTRY": set(), "CONTINUATION": {"position_ref"}, "PULLBACK_BUY": {"geometry_ref"},
        "ADD": {"position_ref", "geometry_ref", "risk_budget_ref"}, "REENTRY": {"prior_exit_episode_ref"},
        "DERISK": {"position_ref"},
    }[action]
    if applicability == "APPLICABLE":
        for key in required_refs:
            if a[key] is None:
                _fail("ACTION_BINDING_REQUIRED", p + "." + key)
    # Prevent an assessment for a different position action from being renamed NEW_ENTRY.
    if action == "NEW_ENTRY" and any(a[k] is not None for k in refs - {"eligibility_ref", "geometry_ref"}):
        _fail("ACTION_BINDING_FORBIDDEN", p)
    _choice(a["estimate_status"], {"NOT_FITTED", "ABSTAINED"}, p + ".estimate_status", "ESTIMATE_NOT_ADMITTED")
    _choice(a["evidence_status"], {"OBSERVED_CONTEXT_ONLY", "ABSTAINED"}, p + ".evidence_status", "ESTIMATE_NOT_ADMITTED")
    if a["estimate"] is not None:
        _fail("ESTIMATE_NOT_ADMITTED", p)
    auth = _keys(a["authority"], set(AUTHORITY_KEYS), p + ".authority")
    if any(auth[key] is not False for key in AUTHORITY_KEYS):
        _fail("AUTHORITY_FORBIDDEN", p + ".authority")
    facts = {f["feature_id"] for f in o["facts"]}
    for key in ["drivers", "contradictions"]:
        if not isinstance(a[key], list):
            _fail("ARRAY_REQUIRED", p + "." + key)
        seen = set()
        for feature in a[key]:
            _text(feature, p + "." + key, identifier=True)
            if feature in seen:
                _fail("DUPLICATE_REFERENCE", p + "." + key)
            if feature not in facts:
                _fail("UNKNOWN_FACT_REFERENCE", p + "." + key)
            seen.add(feature)
    if "observation_id" in a and a["observation_id"] != o["observation_id"]:
        _fail("IDENTITY_MISMATCH", p)
    a["observation_id"] = o["observation_id"]
    semantic = {k: v for k, v in a.items() if k not in {"assessment_id", "issued_at"}}
    aid = "assessment:" + hashlib.sha256(canonical_json(semantic)).hexdigest()
    if "assessment_id" in a and a["assessment_id"] != aid:
        _fail("IDENTITY_MISMATCH", p)
    a["assessment_id"] = aid
    return a


@dataclass(frozen=True)
class ContextArtifact:
    """Immutable bytes returned by validated factories; each decoded copy is detached."""
    canonical_bytes: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()

    def to_dict(self) -> dict:
        return _parse(self.canonical_bytes)

    @property
    def observation_id(self) -> str:
        return self.to_dict()["observation"]["observation_id"]

    @property
    def assessment_id(self) -> str:
        return self.to_dict()["assessment"]["assessment_id"]


def build_context(observation: Mapping[str, Any], assessment: Mapping[str, Any]) -> ContextArtifact:
    """Seal caller-supplied owner facts; never invent data, timestamps, expiry or admission."""
    o = _observation(copy.deepcopy(dict(observation)), sealed=False)
    a = _assessment(copy.deepcopy(dict(assessment)), o, sealed=False)
    return ContextArtifact(canonical_json({"schema_version": SCHEMA, "canonicalization": CANONICALIZATION,
                                           "observation": o, "assessment": a}))


def validate_context(raw: bytes | str) -> ContextArtifact:
    p = _parse(raw)
    _keys(p, {"schema_version", "canonicalization", "observation", "assessment"}, "$")
    if p["schema_version"] != SCHEMA or p["canonicalization"] != CANONICALIZATION:
        _fail("SCHEMA_NOT_ADMITTED", "$")
    o = _observation(p["observation"], sealed=True)
    _assessment(p["assessment"], o, sealed=True)
    return ContextArtifact(canonical_json(p))


def reconcile_observation(previous: ContextArtifact, candidate: ContextArtifact) -> str:
    """Pure append/CAS precondition for the EXISTING owner, not a store or lock.

    The owner must still compare its actual prior revision atomically. This does
    not authorize replacing an artifact, reclaiming a writer or replaying an effect.
    """
    old = validate_context(previous.canonical_bytes).to_dict()["observation"]
    new = validate_context(candidate.canonical_bytes).to_dict()["observation"]
    if old["observation_id"] == new["observation_id"]:
        if old != new:
            _fail("IDEMPOTENCY_CONFLICT", "$.observation")
        return "IDEMPOTENT"
    if new["supersedes_ref"] != old["observation_id"]:
        _fail("CORRECTION_REQUIRED", "$.observation")
    anchor = ("market", "instrument_id", "market_session", "cadence", "session_scope", "decision_at")
    if any(old[k] != new[k] for k in anchor):
        _fail("CORRECTION_ANCHOR_MISMATCH", "$.observation")
    if _time(new["issued_at"], "$") < _time(old["issued_at"], "$"):
        _fail("CLOCK_ORDER", "$.observation.issued_at")
    ignored = {"observation_id", "issued_at", "reconstructed_at", "supersedes_ref", "correction_reason"}
    if {k: v for k, v in old.items() if k not in ignored} == {k: v for k, v in new.items() if k not in ignored}:
        _fail("CORRECTION_WITHOUT_CHANGE", "$.observation")
    return "CORRECTION"


@dataclass(frozen=True)
class ConsumerBinding:
    """Trusted incumbent request + owner-admitted canonical digest, never wire input."""
    artifact_sha256: str
    producer_revision: str
    source_manifest_sha256: str
    market: str
    cadence: str
    session_scope: str
    observation_instrument_id: str
    episode_id: str
    security_id: str
    company_id: str
    identity_epoch: str
    candidate_generation_id: str
    cohort_sha256: str
    strategy_id: str
    strategy_version: str
    holding_horizon_sha256: str
    action: str
    decision_at: str
    forecast_horizon_sessions: int
    forecast_end_session: str
    calendar_sha256: str
    target_version: str
    accepted_grades: frozenset[str]
    lane: Literal["READ_ONLY_LIVE", "TEST"] = "READ_ONLY_LIVE"


@dataclass(frozen=True)
class ConsumerResult:
    incumbent: Mapping[str, Any]
    status: Literal["AVAILABLE", "PARTIAL", "UNAVAILABLE", "IGNORED"]
    reason: str
    update: Literal["REPLACE_CONTEXT", "CLEAR_CONTEXT", "KEEP_CURRENT"]
    context: ContextArtifact | None = None
    effective_fact_statuses: tuple[tuple[str, str], ...] = ()


def read_optional_context(
    incumbent: Mapping[str, Any], raw: bytes | str | None, binding: ConsumerBinding, *,
    now: str, response_request_id: str, active_request_id: str, enabled: bool = True,
) -> ConsumerResult:
    """Validate untrusted optional context without changing one incumbent decision field.

    KEEP_CURRENT is intentional: a superseded response (including a late failure)
    must not clear the newer request's context. CLEAR_CONTEXT only clears this
    optional attachment. It never removes a candidate, rank, plan, alert or holding.
    """
    def unavailable(reason: str) -> ConsumerResult:
        return ConsumerResult(incumbent, "UNAVAILABLE", reason, "CLEAR_CONTEXT")

    if enabled is not True:
        return unavailable("DISABLED" if enabled is False else "INVALID_ENABLE_FLAG")
    if not isinstance(response_request_id, str) or not response_request_id or not isinstance(active_request_id, str) or not active_request_id:
        return unavailable("REQUEST_BINDING_REQUIRED")
    if response_request_id != active_request_id:
        return ConsumerResult(incumbent, "IGNORED", "SUPERSEDED_REQUEST", "KEEP_CURRENT")
    if raw is None or raw == b"" or raw == "":
        return unavailable("CONTEXT_MISSING")
    try:
        art = validate_context(raw)
        _hash(binding.artifact_sha256, "binding.artifact_sha256")
        if art.sha256 != binding.artifact_sha256:
            return unavailable("ARTIFACT_DIGEST_MISMATCH")
        p = art.to_dict(); o, a = p["observation"], p["assessment"]
        equalities = (
            (o["producer_revision"], binding.producer_revision),
            (o["source_manifest_ref"]["sha256"], binding.source_manifest_sha256),
            (o["market"], binding.market), (o["cadence"], binding.cadence),
            (o["session_scope"], binding.session_scope), (o["instrument_id"], binding.observation_instrument_id),
            (a["episode_id"], binding.episode_id),
            (a["security_id"], binding.security_id),
            (a["company_id"], binding.company_id), (a["identity_epoch"], binding.identity_epoch),
            (a["candidate_generation_id"], binding.candidate_generation_id),
            (a["cohort_ref"]["sha256"], binding.cohort_sha256),
            (a["strategy_id"], binding.strategy_id), (a["strategy_version"], binding.strategy_version),
            (a["holding_horizon_ref"]["sha256"], binding.holding_horizon_sha256),
            (a["action"], binding.action), (a["target_version"], binding.target_version),
            (a["forecast_horizon_sessions"], binding.forecast_horizon_sessions),
            (a["forecast_end_session"], binding.forecast_end_session),
            (a["calendar_ref"]["sha256"], binding.calendar_sha256),
        )
        if any(x != y or type(x) is not type(y) for x, y in equalities) or _time(a["decision_at"], "$") != _time(binding.decision_at, "binding.decision_at"):
            return unavailable("BINDING_MISMATCH")
        # These are the incumbent B1/B3 fields, not a new episode/lifecycle identity.
        for key in ("episode_id", "security_id", "company_id", "identity_epoch", "candidate_generation_id"):
            if type(incumbent.get(key)) is not str or incumbent.get(key) != getattr(binding, key):
                return unavailable("INCUMBENT_EPISODE_BINDING_MISMATCH")
        if binding.lane not in {"READ_ONLY_LIVE", "TEST"}:
            return unavailable("LANE_NOT_ADMITTED")
        if type(binding.accepted_grades) is not frozenset or not binding.accepted_grades <= GRADES.keys():
            return unavailable("CONSUMER_BINDING_INVALID")
        if o["evidence_grade"] not in binding.accepted_grades:
            return unavailable("SOURCE_GRADE_NOT_ADMITTED")
        if binding.lane == "READ_ONLY_LIVE":
            if o["evidence_grade"] not in {"PIT_QUALIFIED_REPLAY", "PROSPECTIVE_FIRST_SEEN"}:
                return unavailable("SOURCE_GRADE_NOT_ADMITTED")
            if (binding.market, binding.cadence, binding.session_scope, binding.forecast_horizon_sessions, binding.action) != ("US", "DAILY", "REGULAR", 5, "NEW_ENTRY"):
                return unavailable("LANE_NOT_ADMITTED")
        instant = _time(now, "consumer.now")
        if instant < _time(a["issued_at"], "$"):
            return unavailable("NOT_YET_ISSUED")
        if instant >= _time(o["valid_until"], "$"):
            return unavailable("EXPIRED")
        if a["applicability"] != "APPLICABLE":
            return unavailable("APPLICABILITY_" + a["applicability"])
        if a["evidence_status"] == "ABSTAINED" or a["estimate_status"] == "ABSTAINED":
            return unavailable("ACTION_ABSTAINED")
        states = tuple((f["feature_id"], "STALE" if f["status"] in {"OBSERVED", "PARTIAL"} and instant >= _time(f["valid_until"], "$") else f["status"]) for f in o["facts"])
        partial = any(status != "OBSERVED" for _, status in states)
        return ConsumerResult(incumbent, "PARTIAL" if partial else "AVAILABLE",
                              "SOME_FACTS_UNAVAILABLE_OR_STALE" if partial else "OBSERVED_CONTEXT_ONLY",
                              "REPLACE_CONTEXT", art, states)
    except (ContractViolation, TypeError, AttributeError, KeyError, RecursionError) as exc:
        return unavailable(exc.code if isinstance(exc, ContractViolation) else "CONSUMER_BINDING_INVALID")
