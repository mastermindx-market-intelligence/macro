"""Read-only Market Navigator composition; no regime, signal or lifecycle owner.

Consume incumbent market_state and source-qualified observations. Evaluate explicit
research conditions at one cutoff, never invent probabilities or authorize trades.
This module performs no I/O and stores no history. Source authenticity and consumer
freshness policy remain with the upstream owner; syntactic validity is not authenticity.
Public projection is a closed numeric/enum allowlist, not a raw source passthrough.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from hashlib import sha256
import json
import math
import operator
import re
from typing import Any, Mapping
from types import MappingProxyType

SCHEMA = "market_navigator.context/v1"
HORIZONS = frozenset({"intraday", "swing", "position"})
FAMILIES = frozenset({"price", "breadth", "volatility", "positioning", "macro", "event", "liquidity"})
QUALITIES = frozenset({"observed", "estimated", "user_claim", "synthetic"})
OPS = {"gt": operator.gt, "gte": operator.ge, "lt": operator.lt, "lte": operator.le}
# Immutable process-wide no-trade invariant: runtime consumers may copy it,
# but an in-process component cannot silently mutate the trusted baseline.
AUTHORITY = MappingProxyType({k: False for k in (
    "signal", "probability", "ranking", "sizing", "trading", "auto_exit", "alert_escalation",
)})
_ID = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
_UNITS = frozenset({"USD", "percent", "ratio", "vol_points", "basis_points", "contracts", "index_points"})
_VERDICTS = frozenset({"RISK_ON", "MIXED", "RISK_OFF"})


class ContractError(ValueError):
    """Malformed source or scenario contract, never a neutral market observation."""


def _id(value: str) -> None:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ContractError("identifier must be a bounded lowercase slug")


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError("value must be a native finite number, not bool/string")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ContractError("non-finite value") from exc
    if not math.isfinite(number):
        raise ContractError("non-finite value")
    return number


def _clock(value: str) -> datetime:
    if not isinstance(value, str):
        raise ContractError("clock must be timezone-aware ISO text")
    try:
        clock = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("invalid clock") from exc
    if clock.tzinfo is None or clock.utcoffset() is None:
        raise ContractError("naive or date-only clock")
    return clock.astimezone(timezone.utc)


def _ref(value: str) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise ContractError("bounded upstream reference required")


@dataclass(frozen=True)
class Receipt:
    source_ref: str
    revision: str
    observed_at: str
    received_at: str
    available_at: str
    valid_until: str

    def __post_init__(self) -> None:
        _ref(self.source_ref)
        _ref(self.revision)
        observed, received, available, expires = map(
            _clock, (self.observed_at, self.received_at, self.available_at, self.valid_until))
        if not observed <= received <= available or expires <= observed:
            raise ContractError("receipt violates clock ordering")

    def disposition(self, cutoff: datetime) -> str:
        if _clock(self.available_at) > cutoff:
            return "not_yet_available"
        if cutoff >= _clock(self.valid_until):
            return "stale"
        return "current"


@dataclass(frozen=True)
class Observation:
    key: str
    subject: str
    family: str
    value: float | None
    unit: str
    horizons: tuple[str, ...]
    receipt: Receipt
    quality: str = "observed"

    def __post_init__(self) -> None:
        _id(self.key)
        _ref(self.subject)
        if self.family not in FAMILIES or self.quality not in QUALITIES or self.unit not in _UNITS:
            raise ContractError("unknown family, quality or unit")
        if not isinstance(self.horizons, tuple) or not self.horizons or not set(self.horizons) <= HORIZONS:
            raise ContractError("explicit supported horizons required")
        if not isinstance(self.receipt, Receipt):
            raise ContractError("receipt required")
        if self.value is not None:
            _number(self.value)


@dataclass(frozen=True)
class Condition:
    observation: str
    op: str
    threshold: float
    unit: str

    def __post_init__(self) -> None:
        _id(self.observation)
        if self.op not in OPS or self.unit not in _UNITS:
            raise ContractError("unknown condition operator or unit")
        _number(self.threshold)


@dataclass(frozen=True)
class Scenario:
    key: str
    subject: str
    horizon: str
    definition_available_at: str
    definition_ref: str
    deadline: str
    triggers: tuple[Condition, ...]
    invalidations: tuple[Condition, ...]
    support: tuple[str, ...] = ()
    counterevidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _id(self.key)
        _ref(self.subject)
        _ref(self.definition_ref)
        if _clock(self.definition_available_at) >= _clock(self.deadline):
            raise ContractError("scenario must be defined before its deadline")
        if self.horizon not in HORIZONS:
            raise ContractError("unknown scenario horizon")
        if not isinstance(self.triggers, tuple) or not self.triggers or not isinstance(self.invalidations, tuple) or not self.invalidations:
            raise ContractError("explicit nonempty trigger and invalidation tuples required")
        if not all(isinstance(c, Condition) for c in self.triggers + self.invalidations):
            raise ContractError("conditions must be typed; executable expressions are not accepted")
        if len(self.triggers) > 16 or len(self.invalidations) > 16:
            raise ContractError("bounded condition count exceeded")
        if not isinstance(self.support, tuple) or not isinstance(self.counterevidence, tuple):
            raise ContractError("evidence references must be tuples")
        for key in self.support + self.counterevidence:
            _id(key)


def _condition(condition: Condition, rows: Mapping[str, dict]) -> dict:
    row = rows.get(condition.observation)
    reason = "missing" if row is None else row["status"]
    if row is not None and row["unit"] != condition.unit:
        reason = "unit_mismatch"
    known = row is not None and reason == "current"
    result = OPS[condition.op](row["value"], condition.threshold) if known else None
    return {"observation": condition.observation, "op": condition.op,
            "threshold": condition.threshold, "unit": condition.unit,
            "met": result, "reason": reason}


def _all(results: list[dict]) -> bool | None:
    values = [r["met"] for r in results]
    return False if False in values else None if None in values else True


def compose(*, subject: str, horizon: str, as_of: str,
            observations: tuple[Observation, ...], scenarios: tuple[Scenario, ...],
            market_state: Mapping[str, Any] | None = None,
            market_state_receipt: Receipt | None = None,
            expected_market_session: str | None = None,
            canonical_session_complete: bool | None = None) -> dict:
    """Point-in-time condition inspection, NOT confirmation of forecast/trade validity.

    Triggers are AND; invalidations are OR. Unknown invalidation keeps a true
    trigger unresolved. The deadline is exclusive. No state is retained between
    calls and no historical crossing/hold is inferred from a single observation.
    Scenario definitions must themselves be known by the cutoff and bound to the
    subject; clean historical inputs cannot justify a future-written rule.
    Canonical market posture is separate broad-market context, never a condition.
    """
    _ref(subject)
    if horizon not in HORIZONS:
        raise ContractError("unknown horizon")
    cutoff = _clock(as_of)
    if len(observations) > 128 or len(scenarios) > 12:
        raise ContractError("bounded input exceeded")
    rows: dict[str, dict] = {}
    for obs in observations:
        if obs.key in rows:
            raise ContractError("duplicate observation identity")
        status = obs.receipt.disposition(cutoff)
        if obs.subject != subject:
            status = "subject_mismatch"
        elif horizon not in obs.horizons:
            status = "horizon_mismatch"
        elif obs.value is None:
            status = "missing"
        elif obs.quality in {"user_claim", "synthetic"}:
            status = "unqualified"
        rows[obs.key] = {"key": obs.key, "family": obs.family, "status": status,
                         "value": obs.value if status == "current" else None,
                         "unit": obs.unit, "quality": obs.quality,
                         "observed_at": obs.receipt.observed_at,
                         "available_at": obs.receipt.available_at,
                         "valid_until": obs.receipt.valid_until,
                         "source_ref": obs.receipt.source_ref, "revision": obs.receipt.revision}
    results, ids = [], set()
    for scenario in scenarios:
        if scenario.key in ids:
            raise ContractError("duplicate scenario identity")
        ids.add(scenario.key)
        if _clock(scenario.definition_available_at) > cutoff:
            raise ContractError("scenario definition was unavailable at the decision cutoff")
        in_scope = scenario.subject == subject and scenario.horizon == horizon
        trigger = [_condition(c, rows) for c in scenario.triggers] if in_scope else []
        invalid = [_condition(c, rows) for c in scenario.invalidations] if in_scope else []
        if scenario.subject != subject:
            state = "subject_mismatch"
        elif scenario.horizon != horizon:
            state = "horizon_mismatch"
        elif cutoff >= _clock(scenario.deadline):
            state = "expired"
        elif any(r["met"] is True for r in invalid):
            state = "invalidated"
        elif _all(trigger) is None or any(r["met"] is None for r in invalid):
            state = "unresolved"
        else:
            state = "conditions_met" if _all(trigger) else "waiting"
        evidence = lambda keys: [{"key": k, "status": rows.get(k, {}).get("status", "missing")} for k in keys]
        results.append({"key": scenario.key, "horizon": scenario.horizon,
                        "definition_available_at": scenario.definition_available_at,
                        "definition_ref": scenario.definition_ref,
                        "deadline": scenario.deadline, "status": state,
                        "triggers": trigger, "invalidations": invalid,
                        "support": evidence(scenario.support),
                        "counterevidence": evidence(scenario.counterevidence), "probability": None})
    canonical = {"status": "missing", "verdict": None}
    if market_state is not None:
        if market_state.get("schema") != "market_state.v1" or market_state.get("is_display_only") is not True:
            raise ContractError("incumbent display-only market_state.v1 required")
        if market_state.get("market") != "us":
            raise ContractError("v1 canonical market context is US-only")
        if not isinstance(market_state_receipt, Receipt):
            raise ContractError("canonical state availability receipt required")
        canonical["status"] = market_state_receipt.disposition(cutoff)
        verdict = market_state.get("verdict")
        if verdict not in _VERDICTS:
            canonical["status"] = "unsupported_verdict"
        try:
            session = date.fromisoformat(market_state.get("asof", ""))
        except (TypeError, ValueError) as exc:
            raise ContractError("canonical state session date required") from exc
        if session != _clock(market_state_receipt.observed_at).astimezone(ZoneInfo("America/New_York")).date():
            canonical["status"] = "asof_mismatch"
        fresh = market_state.get("freshness") or {}
        vintages = market_state.get("input_vintages") or {}
        if not isinstance(fresh, Mapping) or not isinstance(vintages, Mapping):
            raise ContractError("canonical freshness and vintages must be mappings")
        if canonical["status"] == "current":
            if expected_market_session is None:
                canonical["status"] = "session_unverified"
            else:
                try:
                    expected = date.fromisoformat(expected_market_session)
                except (TypeError, ValueError) as exc:
                    raise ContractError("expected market session must come from the calendar owner") from exc
                if session < expected or fresh.get("stale") is True:
                    canonical["status"] = "stale"
                elif session > expected and canonical_session_complete is not True:
                    canonical["status"] = "session_completion_unverified"
                elif (market_state.get("stale_inputs") or market_state.get("degraded_components")
                      or fresh.get("any_input_stale") or fresh.get("stale_inputs")
                      or any(isinstance(v, Mapping) and v.get("stale") is True for v in vintages.values())):
                    canonical["status"] = "degraded"

        if canonical["status"] == "current":
            canonical["verdict"] = verdict
        canonical["asof"] = session.isoformat()
        canonical["observed_at"] = market_state_receipt.observed_at
        canonical["available_at"] = market_state_receipt.available_at
        canonical["valid_until"] = market_state_receipt.valid_until
        canonical["source_ref"] = market_state_receipt.source_ref
        canonical["revision"] = market_state_receipt.revision
    packet = {"schema": SCHEMA, "subject": subject, "horizon": horizon,
              "as_of": cutoff.isoformat(), "canonical_market": canonical,
              "observations": sorted(rows.values(), key=lambda r: r["key"]),
              "scenarios": sorted(results, key=lambda r: r["key"]),
              "coincident_conditions": sum(r["status"] == "conditions_met" for r in results) > 1,
              "readiness": "research_only", "authority": dict(AUTHORITY)}
    packet["context_digest"] = sha256(json.dumps(packet, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return packet


def public_projection(packet: Mapping[str, Any]) -> dict:
    """Closed display fields from this compositor only; no internals or arbitrary prose.

    Not an authorization boundary: authenticated routes must bind visibility and
    data rights before calling. Do not expose internal sources via this projection.
    """
    if packet.get("schema") != SCHEMA or packet.get("authority") != AUTHORITY:
        raise ContractError("unrecognized or authority-bearing packet")
    body = {k: v for k, v in packet.items() if k != "context_digest"}
    actual = sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    if actual != packet.get("context_digest"):
        raise ContractError("packet changed after composition")
    cutoff = _clock(packet["as_of"])
    public_rows = []
    for row in packet["observations"]:
        public_row = {k: row[k] for k in ("key", "family", "status", "value", "unit", "quality")}
        known = _clock(row["available_at"]) <= cutoff
        public_row.update({k: row[k] if known else None
                           for k in ("observed_at", "available_at", "valid_until")})
        public_rows.append(public_row)
    public_scenarios = []
    for row in packet["scenarios"]:
        public_row = {k: row[k] for k in ("key", "horizon", "definition_available_at", "deadline", "status", "probability")}
        for field in ("triggers", "invalidations"):
            public_row[field] = [{k: item[k] for k in ("observation", "op", "threshold", "unit", "met", "reason")}
                                 for item in row[field]]
        for field in ("support", "counterevidence"):
            public_row[field] = [{k: item[k] for k in ("key", "status")} for item in row[field]]
        public_scenarios.append(public_row)
    canonical = packet["canonical_market"]
    public_market = {k: canonical[k] for k in ("status", "verdict")}
    known = canonical.get("available_at") is not None and _clock(canonical["available_at"]) <= cutoff
    public_market.update({k: canonical.get(k) if known else None
                          for k in ("asof", "observed_at", "available_at", "valid_until")})
    return {"schema": SCHEMA, "horizon": packet["horizon"], "as_of": packet["as_of"],
            "canonical_market": public_market, "observations": public_rows,
            "scenarios": public_scenarios,
            "coincident_conditions": packet["coincident_conditions"],
            "readiness": "research_only", "authority": dict(AUTHORITY)}
