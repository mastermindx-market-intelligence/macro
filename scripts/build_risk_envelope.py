#!/usr/bin/env python3
"""scripts/build_risk_envelope.py — settled producer for `mastermind.risk_envelope/v1`.

    python -m scripts.build_risk_envelope           # writes both copies
    python -m scripts.build_risk_envelope --print   # compose + print, write nothing

This is the SETTLED lane only.  The live provisional lane (`site/live/risk_envelope.json`)
is GD-3 and is gated on this wave's production acceptance; it will call the SAME pure
composer with fresher observations and must never fork the state logic.

Division of labour
------------------
`engine/risk_envelope.py` is pure: states in, envelope out, no clock, no disk.  THIS
file owns everything impure — reading the settled artifacts, reading the clock, and the
atomic dual write.  The adapters below are the only place that knows how a given organ
spells its state, and each one carries that organ's read through VERBATIM.

Output paths (freeze §5.1 + the risk_radar_scorecard dual-write convention):
  * ``data/risk_envelope/latest.json``  — durable settled copy
  * ``site/riskdata/risk_envelope.json`` — public/cross-repository contract

Both are written with tmp+os.replace, so no reader ever sees a partial file.

Never fatal: a missing source becomes a MISSING coverage entry and (if required) nulls
the hazard stage.  That is the honest answer, and it is why the builder does not need
to guess.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping

# Repo-root pin, the house idiom (scripts/build_regime_prior.py:28-29).
# UNCONDITIONAL and top-level on purpose: a guarded `if str(_ROOT) not in sys.path`
# is not a strong pin — it is not guaranteed to run, and a root already sitting
# further down sys.path still loses to a foreign package ahead of it.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from engine.risk_envelope import (  # noqa: E402
    SourceRead,
    compose_envelope,
    canonical_json,
    ROTATION_SOURCE_ID,
    ROTATION_EARLY_STATES,
)
from lib.nyse_calendar import ET, is_session, sessions_between  # noqa: E402

log = logging.getLogger(__name__)

MARKET = "US"

# Freshness horizon for the settled lane: a settled artifact whose own clock predates
# the session we are baking is off-session, and a required off-session source cannot
# hold the hazard stage open.  Expressed in sessions (date strings), never wall-clock,
# because settled organs stamp dates.
_MEASURED_SOURCE = "market-state-latest"
_LEADERSHIP_SOURCE = "leadership-crack-latest"
_RADAR_SOURCE = "risk-radar-us"
_WARNING_STATES = frozenset(("caution", "elevated", "risk-off"))
_CONTEXT_NOT_PROVIDED = object()
_PAIR_RECEIPT_LIMIT = 12
_NATIVE_MARKET_FIELDS = (
    "raw_score", "score", "verdict", "capped", "score_source", "score_caps",
    "score_ceiling", "score_gap", "overrides", "components", "input_vintages",
    "stale_inputs", "degraded_components", "freshness", "lineage",
)


def _day(value: Any) -> date | None:
    try:
        parsed = date.fromisoformat(value) if isinstance(value, str) else None
        return parsed if parsed and parsed.isoformat() == value and is_session(parsed) else None
    except (TypeError, ValueError):
        return None


def _instant(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None
    except (ValueError, OverflowError):
        return None


def _clock_reason(doc: Mapping[str, Any], as_of: Any, session: Any,
                  now: datetime | None) -> str | None:
    """Source clocks qualify context; a new build cannot refresh an old observation."""
    source_day, session_day = _day(as_of), _day(session)
    if source_day is None or session_day is None:
        return "missing_or_malformed_session"
    if source_day > session_day:
        return "future_source_session"
    if source_day < session_day:
        return "off_session"
    if now is not None and source_day > now.astimezone(ET).date():
        return "future_source_session"
    clocks = [(key, doc.get(key)) for key in ("available_at", "produced_at", "generated_utc")]
    availability = doc.get("availability")
    if availability is not None and not isinstance(availability, Mapping):
        return "malformed_availability"
    if isinstance(availability, Mapping):
        clocks.append(("available_at", availability.get("available_at")))
    # Validate every supplied native clock, not just a preferred alias. A valid
    # backdated alias must not hide another explicit future availability clock.
    for key, value in clocks:
        if value is None:
            continue
        stamp = _instant(value)
        if stamp is None and key == "generated_utc":
            # Rotation Command writes this exact, explicitly UTC minute format.
            # Preserve the native clock rather than rejecting every real payload.
            try:
                stamp = datetime.strptime(value, "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)
                if stamp.strftime("%Y-%m-%d %H:%M UTC") != value:
                    stamp = None
            except (TypeError, ValueError):
                pass
        if stamp is None:
            return "malformed_source_clock"
        if now is not None and stamp > now.astimezone(timezone.utc):
            return "source_not_available" if key == "available_at" else "future_production_clock"
    fresh = doc.get("freshness")
    if fresh is not None and not isinstance(fresh, Mapping):
        return "malformed_freshness"
    if isinstance(fresh, Mapping):
        if "stale" in fresh and not isinstance(fresh["stale"], bool):
            return "malformed_freshness"
        if fresh.get("stale"):
            return "source_stale"
    return None


def _market_lineage(doc: Mapping[str, Any]) -> dict[str, Any]:
    native = doc.get("lineage")
    if isinstance(native, Mapping):
        return dict(native)
    # The actual component names establish conservative price overlap, but do not
    # identify all primitive observations. Do not mint roots from the latest file.
    components = doc.get("components")
    keys = {c.get("key") for c in components if isinstance(c, Mapping)} if isinstance(components, list) else set()
    return {
        "definition_id": "market-state-component-dependencies-v1",
        "status": "PARTIAL" if keys else "UNKNOWN", "roots": [],
        "dependency_groups": ["equity_price"] if keys & {"trend", "breadth", "risk"} else [],
        "derived_from": [],
    }


def _compact_early_context(early: Mapping[str, Any]) -> dict[str, Any]:
    """Bound product receipts; lineage lives once in source provenance."""
    fields = ("schema", "definition_id", "as_of", "produced_at", "available_at",
              "availability", "display_only", "state", "reason_codes", "coverage",
              "prior_loser_constituent_claim")
    out = {key: early[key] for key in fields if key in early}
    pairs = early.get("pairs")
    pairs = pairs if isinstance(pairs, list) else []
    out["pairs"] = [{k: v for k, v in pair.items() if k != "lineage"}
                    for pair in pairs[:_PAIR_RECEIPT_LIMIT] if isinstance(pair, Mapping)]
    out["source_pair_count"] = len(pairs)
    out["pairs_omitted"] = max(0, len(pairs) - _PAIR_RECEIPT_LIMIT)
    out["omitted_pair_ids"] = [p.get("pair_id") for p in pairs[_PAIR_RECEIPT_LIMIT:] if isinstance(p, Mapping)]
    out["lineage_source"] = ROTATION_SOURCE_ID
    return out


def _rotation_read(doc: Mapping[str, Any] | None, session: str | None, *,
                   now: datetime | None = None) -> SourceRead:
    if not isinstance(doc, Mapping) or not doc:
        return SourceRead(source_id=ROTATION_SOURCE_ID, role="context", present=False,
                          detail={"excluded_reason": "source_missing"})
    early = doc.get("early_context")
    early = early if isinstance(early, Mapping) else None
    confirmed_asof = doc.get("as_of", doc.get("asof"))
    as_of = early.get("as_of") if early else confirmed_asof
    # The legacy confirmed-event date may be older than the early observation.
    # Its parent artifact's publication/availability clocks still constrain both.
    reason = (_clock_reason(doc, as_of, session, now)
              or _clock_reason(early or doc, as_of, session, now))
    if not early or early.get("schema") != "rotation_early_context/v1":
        reason = "early_context_missing_or_malformed"
    elif (not isinstance(early.get("definition_id"), str) or not early.get("definition_id")
          or early.get("display_only") is not True or not isinstance(early.get("pairs"), list)
          or any(not isinstance(p, Mapping) for p in early["pairs"])
          or not isinstance(early.get("coverage"), Mapping)):
        reason = "early_context_missing_or_malformed"
    elif early.get("state") not in ROTATION_EARLY_STATES:
        reason = reason or "early_context_unavailable"
    active = doc.get("active")
    confirmed = None
    if isinstance(active, list) and all(isinstance(item, Mapping) for item in active):
        active_ids = sorted(str(item["id"]) for item in active if item.get("id") is not None)
        confirmed = {
            "active_count": len(active),
            "active_ids": active_ids[:20],
            "active_ids_omitted": max(0, len(active_ids) - 20),
            "as_of": confirmed_asof,
            "usable": _clock_reason(doc, confirmed_asof, session, now) is None,
        }
    return SourceRead(
        source_id=ROTATION_SOURCE_ID, role="context",
        state=early.get("state") if early else None,
        as_of=as_of, stale=reason is not None, required=False,
        label_en="Relative leadership", label_zh="相对领导变化",
        detail={
            "early_context": _compact_early_context(early) if early else None,
            "confirmed_events": confirmed,
            "lineage": dict(early["lineage"]) if early and isinstance(early.get("lineage"), Mapping) else {},
            "excluded_reason": reason,
            "availability_basis": "source_recorded" if early and early.get("available_at") else "original_availability_unknown",
        },
    )


# ── source adapters ────────────────────────────────────────────────────────────
# Each adapter answers exactly one question: "what did this organ publish, and what
# descriptive V0 stage does its OWN state vocabulary mean?".  Adapters never threshold
# a score into a stage and never look at another organ.

def _market_state_read(
    doc: Mapping[str, Any] | None, session: str | None, *,
    stale_override: bool | None = None,
    context_enabled: bool = False,
    transition_context: Mapping[str, Any] | None = None,
    now: datetime | None = None,
) -> SourceRead:
    """Market State — the slow confirmed trend.  Carried verbatim, never recomputed.

    `stale_override` (GD-3): when given, it REPLACES this adapter's own staleness
    expression rather than combining with it — the live lane (scripts/build_live_
    risk_envelope.py) computes freshness from the live plane's own clock and hands
    it straight through.  `None` (the default) is a no-op: the settled lane's
    behaviour is unchanged byte-for-byte."""
    if not isinstance(doc, Mapping) or not doc:
        return SourceRead(
            source_id=_MEASURED_SOURCE, role="measured_state",
            present=False, required=True,
            detail=({"market_transition": dict(transition_context) if transition_context else None,
                     "excluded_reason": "source_missing"} if context_enabled else {}),
        )
    fresh_raw = doc.get("freshness")
    fresh = fresh_raw if isinstance(fresh_raw, Mapping) else {}
    as_of = doc.get("asof")
    # Two independent staleness signals, both from the organ itself: its own
    # `freshness.stale` verdict, and whether its clock matches the session we bake.
    stale = stale_override if stale_override is not None else (
        bool(fresh.get("stale")) or (bool(session) and bool(as_of) and as_of != session)
    )
    context_detail: dict[str, Any] = {}
    if context_enabled:
        reason = _clock_reason(doc, as_of, session, now)
        if doc.get("verdict") not in ("RISK_ON", "MIXED", "RISK_OFF"):
            reason = reason or "market_state_unavailable"
        score = doc.get("score")
        if score is not None and (isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score)):
            reason = reason or "malformed_market_score"
        stale = bool(stale or reason)
        context_detail = {key: doc.get(key) for key in _NATIVE_MARKET_FIELDS}
        context_detail.update({
            "lineage": _market_lineage(doc),
            "market_transition": dict(transition_context) if transition_context else None,
            "excluded_reason": reason,
        })
    return SourceRead(
        source_id=_MEASURED_SOURCE,
        role="measured_state",
        state=doc.get("verdict"),
        score=doc.get("score"),
        as_of=as_of,
        stale=stale,
        required=True,
        # label_* names the SOURCE (what the drawer's "Source" column says).
        # The organ's own bilingual STATE label rides in detail, so the band can
        # print the state in the organ's own words without renaming the source.
        label_en="Market state",
        label_zh="市场状态",
        detail={
            "state_label_en": doc.get("label_en"),
            "state_label_zh": doc.get("label_zh"),
            "raw_score": doc.get("raw_score"),
            "capped": bool(doc.get("capped")),
            "score_source": doc.get("score_source"),
            "expected_asof": fresh.get("expected_asof"),
            "any_input_stale": bool(fresh.get("any_input_stale")),
            "worst_input_age_days": fresh.get("worst_input_age_days"),
            **context_detail,
        },
    )


# Leadership Crack's own state vocabulary -> the V0 descriptive stage.  This is a
# TRANSLATION of one organ's published vocabulary, not a judgement: BROKEN means the
# tracked leadership cohort has already taken measured damage, which is a present-tense
# observation (FRAGILE), never an anticipatory claim.
_LEADERSHIP_STAGE = {
    "INTACT": "NONE",
    "OK": "NONE",
    "REPAIRING": "NONE",
    "STRAINED": "FRAGILE",
    "CRACKED": "FRAGILE",
    "BROKEN": "FRAGILE",
}


def _leadership_crack_read(
    doc: Mapping[str, Any] | None, session: str | None, *,
    stale_override: bool | None = None,
) -> SourceRead:
    """Leadership Crack — has the leadership cohort taken damage this session?

    `stale_override` (GD-3): see `_market_state_read`.  `None` preserves the
    settled lane's original expression exactly."""
    if not doc:
        return SourceRead(
            source_id=_LEADERSHIP_SOURCE, role="hazard_evidence",
            present=False, required=True,
        )
    as_of = doc.get("asof")
    state = doc.get("state")
    stale = stale_override if stale_override is not None else (
        bool(session) and bool(as_of) and as_of != session
    )
    stage = _LEADERSHIP_STAGE.get(str(state).upper()) if state else None
    # GD-2R1 (Sol post-merge review): `dislocation` does NOT promote to TRANSMITTING.
    # Dislocation is precisely "the cohort is damaged while the INDEX still holds" —
    # evidence that damage has NOT spread. Reading it as transmission inverted the
    # signal's own meaning. It stays a FRAGILE observation and the flag itself is
    # carried in `detail` for the evidence drawer. This organ measures one cohort, so
    # it is not competent to assert transmission at all: the default FRAGILE ceiling
    # on SourceRead is what enforces that, whatever a future mapping claims.
    return SourceRead(
        source_id=_LEADERSHIP_SOURCE,
        role="hazard_evidence",
        state=state,
        score=None,
        as_of=as_of,
        stale=stale,
        required=True,
        hazard_stage=stage,
        label_en="Leadership cohort",
        label_zh="龙头股群体",
        detail={
            "state_since": doc.get("state_since"),
            "cohort_role": doc.get("cohort_role"),
            "n_fresh": doc.get("n_fresh"),
            "n_total": doc.get("n_total"),
            "dislocation": bool(doc.get("dislocation")),
            "high_window_sessions": doc.get("high_window_sessions"),
        },
    )


# Risk Radar's own state vocabulary -> the V0 descriptive stage.
_RADAR_STAGE = {
    "calm": "NONE",
    "watch": "NONE",
    "caution": "FRAGILE",
    "warning": "FRAGILE",
    "alert": "TRANSMITTING",
    "loud": "TRANSMITTING",
    "severe": "BREAKDOWN",
}


def _risk_radar_read(radar: Mapping[str, Any] | None, session: str | None,
                     ms_asof: str | None, *,
                     stale_override: bool | None = None,
                     issued_duration: Mapping[str, Any] | None = None) -> SourceRead:
    """US Risk Radar — the cross-asset scare monitor, source-native on Market State.

    Optional coverage: the radar corroborates but is not required for the stage to be
    knowable, so its absence degrades coverage rather than nulling the answer.

    `stale_override` (GD-3): see `_market_state_read`.  `None` preserves the
    settled lane's original expression exactly.
    """
    if not radar:
        return SourceRead(
            source_id=_RADAR_SOURCE, role="hazard_evidence",
            present=False, required=False,
        )
    state = radar.get("state")
    stale = stale_override if stale_override is not None else (
        bool(session) and bool(ms_asof) and ms_asof != session
    )
    return SourceRead(
        source_id=_RADAR_SOURCE,
        role="hazard_evidence",
        state=state,
        score=radar.get("top_score"),
        as_of=ms_asof,
        stale=stale,
        required=False,
        hazard_stage=_RADAR_STAGE.get(str(state).lower()) if state else None,
        label_en="Cross-asset scares",
        label_zh="跨资产风险扫描",
        detail={
            "is_warning": bool(radar.get("is_warning")),
            "is_loud": bool(radar.get("is_loud")),
            "label_en": radar.get("label_en"),
            "label_zh": radar.get("label_zh"),
            **(dict(issued_duration) if issued_duration else {}),
        },
    )


def build_sources(
    market_state: Mapping[str, Any] | None,
    leadership_crack: Mapping[str, Any] | None,
    session: str | None,
    *,
    radar_issued_duration: Mapping[str, Any] | None = None,
    rotation_events: Any = _CONTEXT_NOT_PROVIDED,
    market_transition: Mapping[str, Any] | None = None,
    now: datetime | None = None,
) -> list[SourceRead]:
    """Adapt the settled artifacts into source-native reads. Pure; no I/O."""
    market_state = market_state if isinstance(market_state, Mapping) else None
    leadership_crack = leadership_crack if isinstance(leadership_crack, Mapping) else None
    ms_asof = (market_state or {}).get("asof")
    context_enabled = rotation_events is not _CONTEXT_NOT_PROVIDED
    sources = [
        _market_state_read(market_state, session, context_enabled=context_enabled,
                           transition_context=market_transition, now=now),
        _leadership_crack_read(leadership_crack, session),
        _risk_radar_read(
            (market_state or {}).get("radar"), session, ms_asof,
            issued_duration=radar_issued_duration,
        ),
    ]
    if context_enabled:
        # The optional addition does not promote any source's competence. It does
        # enforce actual session clocks before carrying those sources into a joint
        # explanation; an undated required organ cannot masquerade as fresh.
        from dataclasses import replace
        for index in (1, 2):
            source = sources[index]
            doc = leadership_crack if index == 1 else (market_state or {}).get("radar")
            doc = doc if isinstance(doc, Mapping) else {}
            reason = _clock_reason(doc, source.as_of, session, now) if source.present else "source_missing"
            detail = dict(source.detail)
            detail["lineage"] = doc.get("lineage") if isinstance(doc.get("lineage"), Mapping) else {}
            detail["excluded_reason"] = reason
            sources[index] = replace(source, stale=bool(source.stale or reason), detail=detail)
        sources.append(_rotation_read(rotation_events, session, now=now))
    return sources


# ── I/O ────────────────────────────────────────────────────────────────────────


def _native_record(doc: Mapping[str, Any]) -> dict[str, Any]:
    fields = ("asof", "logged_at", "available_at", "produced_at", "availability",
              "definition_id", *_NATIVE_MARKET_FIELDS)
    return {key: doc[key] for key in fields if key in doc}


def _recorded_comparison(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    """Native differences only. These are not causal weights or signal votes."""
    def number(value: Any) -> float | int | None:
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None

    def components(doc: Mapping[str, Any]) -> dict[str, Any]:
        value = doc.get("components")
        if isinstance(value, Mapping):
            return dict(value)
        if isinstance(value, list):
            return {str(c["key"]): c for c in value if isinstance(c, Mapping) and c.get("key")}
        return {}

    a, b = components(before), components(after)
    movements = []
    for key in sorted(set(a) | set(b)):
        old = a.get(key) if isinstance(a.get(key), Mapping) else {}
        new = b.get(key) if isinstance(b.get(key), Mapping) else {}
        previous, current = number(old.get("score")), number(new.get("score"))
        if old != new:
            movements.append({"key": key, "previous": dict(old), "current": dict(new),
                              "score_delta": current - previous if current is not None and previous is not None else None})
    return {
        "before": _native_record(before), "after": _native_record(after),
        "verdict_changed": before.get("verdict") != after.get("verdict"),
        "adjacent_sessions": len(sessions_between(_day(before["asof"]), _day(after["asof"]))) == 2,
        "component_movements": movements,
        "changed_native_fields": [key for key in _NATIVE_MARKET_FIELDS if before.get(key) != after.get(key)],
        "cause": "not_inferred_from_snapshot_differences",
    }


def _recorded_market_transition(path: Path, session: str | None, *,
                                now: datetime, current: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Read actual first-writer receipts; no new ledger and no reconstructed onset."""
    current_reason = (_clock_reason(current, current.get("asof"), session, now)
                      if isinstance(current, Mapping) else "source_missing")
    qualified_current = current if current_reason is None else None
    out: dict[str, Any] = {
        "basis": "market_state_forward_log_first_writer",
        "status": "UNKNOWN", "source_session": session,
        "latest_recorded": None, "previous_recorded": None,
        "latest_comparison": None, "latest_recorded_change": None,
        "current_snapshot": _native_record(qualified_current) if qualified_current is not None else None,
        "current_snapshot_basis": "current_persisted_snapshot_not_a_first_writer_receipt",
        "current_snapshot_excluded_reason": current_reason,
        "current_matches_latest_record": None,
        "excluded_record_count": 0, "display_only": True,
    }
    if _day(session) is None:
        out["reason"] = "source_session_unknown"
        return out
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        out["reason"] = "forward_log_unavailable"
        return out
    eligible: list[Mapping[str, Any]] = []
    last_day: date | None = None
    last_receipt: datetime | None = None
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            out["reason"] = "malformed_forward_log"
            return out
        if not isinstance(row, Mapping):
            out["reason"] = "malformed_forward_log"
            return out
        if row.get("type") == "premise_repair":
            continue
        day = _day(row.get("asof"))
        if day is None:
            out["reason"] = "malformed_record_session"
            return out
        if day > _day(session) or day > now.astimezone(ET).date():
            out["excluded_record_count"] += 1
            continue
        if last_day is not None and day <= last_day:
            out["reason"] = "duplicate_or_unordered_first_writer_records"
            return out
        last_day = day
        receipt = _instant(row.get("logged_at"))
        if receipt is None or receipt > now.astimezone(timezone.utc):
            out["excluded_record_count"] += 1
            continue
        if last_receipt is not None and receipt <= last_receipt:
            out["reason"] = "unordered_record_receipts"
            return out
        last_receipt = receipt
        if row.get("verdict") not in ("RISK_ON", "MIXED", "RISK_OFF"):
            out["excluded_record_count"] += 1
            continue
        eligible.append(row)
    if not eligible:
        out["reason"] = "no_qualified_recorded_snapshot"
        return out
    latest = eligible[-1]
    out["status"] = "RECORDED" if latest["asof"] == session else "RECORDED_PRIOR_SESSION"
    out["latest_recorded"] = _native_record(latest)
    if qualified_current is not None and qualified_current.get("asof") == latest["asof"]:
        out["current_matches_latest_record"] = all(qualified_current.get(k) == latest.get(k) for k in ("verdict", "score", "raw_score"))
    if len(eligible) > 1:
        out["previous_recorded"] = _native_record(eligible[-2])
        out["latest_comparison"] = _recorded_comparison(eligible[-2], latest)
    for before, after in zip(eligible, eligible[1:]):
        comparison = _recorded_comparison(before, after)
        if comparison["verdict_changed"] and comparison["adjacent_sessions"]:
            out["latest_recorded_change"] = comparison
    return out


def _issued_warning_duration(
    path: Path,
    session: str | None,
    current_state: str | None,
) -> dict[str, Any] | None:
    """Issued caution+ streak ending on the settled session, or None.

    Product law is frozen by
    research/grey_deer/RISK_RADAR_CAUTION_PERSISTENCE_PREREG_2026-09-21.md:
    caution+ = caution/elevated/risk-off and five consecutive known sessions is
    presentation context only. This adapter deliberately uses the issued
    first-writer forward ledger rather than reconstructing historical states.

    Fail closed:
    - current settled session must have exactly one ledger row;
    - its state must match the settled Radar state;
    - duplicate/invalid rows do not earn a duration claim;
    - a missing expected NYSE session breaks the streak;
    - calm/watch return an honest zero-duration fact, never "persistent".
    """
    if not session or not current_state:
        return None
    try:
        session_day = date.fromisoformat(str(session))
        if session_day.isoformat() != str(session):
            return None
        raw = path.read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError, TypeError):
        return None

    rows_by_day: dict[date, Mapping[str, Any]] = {}
    for line in raw:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if not isinstance(row, dict):
                return None
            day_raw = row.get("asof")
            day = date.fromisoformat(day_raw) if isinstance(day_raw, str) else None
            if day is None or day.isoformat() != day_raw:
                return None
        except (json.JSONDecodeError, ValueError, TypeError):
            return None
        # The ledger contract is keep-FIRST / one row per as-of. A duplicate is
        # ambiguous here even when byte-identical: duration must not silently gain
        # evidence from a malformed ledger.
        if day in rows_by_day:
            return None
        rows_by_day[day] = row

    current = rows_by_day.get(session_day)
    if not current:
        return None
    state = str(current.get("state") or "").strip().lower()
    if state != str(current_state).strip().lower():
        return None

    # Non-warning states carry a zero fact so provenance remains explicit, while
    # the template displays nothing below the five-session research floor.
    if state not in _WARNING_STATES:
        return {
            "issued_warning_sessions": 0,
            "issued_warning_since": None,
            "issued_warning_persistent": False,
            "issued_warning_floor": 5,
            "issued_warning_basis": "risk_radar_forward_log_first_writer_sessions",
        }

    earliest = min(rows_by_day)
    expected = sessions_between(earliest, session_day)
    streak = 0
    since: date | None = None
    for day in reversed(expected):
        row = rows_by_day.get(day)
        if row is None:
            break
        row_state = str(row.get("state") or "").strip().lower()
        if row_state not in _WARNING_STATES:
            break
        streak += 1
        since = day

    return {
        "issued_warning_sessions": streak,
        "issued_warning_since": since.isoformat() if since else None,
        "issued_warning_persistent": bool(streak >= 5),
        "issued_warning_floor": 5,
        "issued_warning_basis": "risk_radar_forward_log_first_writer_sessions",
    }


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        if not path.exists():
            log.warning("risk_envelope: source missing %s", path)
            return None
        parsed = json.loads(path.read_text(encoding="utf-8"))
        return parsed if isinstance(parsed, dict) else None
    except Exception as e:  # noqa: BLE001 — a bad source becomes MISSING coverage
        log.warning("risk_envelope: source unreadable %s (%s)", path, e)
        return None


def _atomic_write(path: Path, payload: str) -> None:
    """Write atomically via tmp+rename. Never raises (mirrors risk_radar_scorecard)."""
    tmp = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            os.write(fd, payload.encode("utf-8"))
        finally:
            os.close(fd)
        os.replace(tmp, path)
        # mkstemp creates 0600; site/riskdata/ is publicly served, so a 0600 artifact
        # written by the nightly would 403 for the web user until the next git checkout
        # reset the mode. Never fatal.
        try:
            os.chmod(path, 0o644)
        except Exception:  # noqa: BLE001
            pass
    except Exception as e:  # noqa: BLE001
        log.warning("risk_envelope atomic write to %s failed: %s", path, e)
        if tmp:
            try:
                os.unlink(tmp)
            except Exception:  # noqa: BLE001
                pass


def data_path(root: Path | None = None) -> Path:
    return (root or _REPO_ROOT) / "data" / "risk_envelope" / "latest.json"


def site_path(root: Path | None = None) -> Path:
    return (root or _REPO_ROOT) / "site" / "riskdata" / "risk_envelope.json"


def build(root: Path | None = None, now: datetime | None = None) -> dict[str, Any]:
    """Read the settled artifacts and compose the envelope. Returns the envelope dict."""
    root = root or _REPO_ROOT
    now = now or datetime.now(timezone.utc)
    stamp = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    market_state = _read_json(root / "data" / "market_state" / "latest.json")
    leadership = _read_json(root / "data" / "leadership_crack" / "latest.json")
    rotation = _read_json(root / "site" / "marketdata" / "rotation_events.json")

    # The settled session is the market-state organ's own session: it is the artifact
    # that defines "this settled session" for the US market.  Every other source is
    # then measured AGAINST that session rather than against wall-clock time.
    session = (market_state or {}).get("asof")
    radar_state = (((market_state or {}).get("radar") or {}).get("state"))
    radar_issued_duration = _issued_warning_duration(
        root / "data" / "risk_radar" / "forward_log.jsonl",
        session,
        radar_state,
    )

    sources = build_sources(
        market_state, leadership, session,
        radar_issued_duration=radar_issued_duration,
        rotation_events=rotation,
        market_transition=_recorded_market_transition(
            root / "data" / "market_state" / "forward_log.jsonl", session,
            now=now, current=market_state,
        ),
        now=now,
    )
    return compose_envelope(
        sources=sources,
        market=MARKET,
        source_session=session,
        observed_at=stamp,
        produced_at=stamp,
        as_of=session,
        stale_after=None,
        revision="settled",
    )


def write(root: Path | None = None, now: datetime | None = None) -> dict[str, Any]:
    """Build and atomically write both copies. Never raises; returns the envelope."""
    try:
        env = build(root, now)
        payload = canonical_json(env) + "\n"
        _atomic_write(data_path(root), payload)
        _atomic_write(site_path(root), payload)
        log.info(
            "risk_envelope: session=%s measured=%s hazard=%s coherence=%s data=%s bundle=%s",
            env.get("source_session"),
            (env.get("measured_state") or {}).get("verdict"),
            (env.get("hazard_summary") or {}).get("stage"),
            (env.get("coherence") or {}).get("state"),
            env.get("data_state"),
            env.get("bundle_id"),
        )
        return env
    except Exception as e:  # noqa: BLE001 — additive artifact, never breaks the bake
        log.warning("risk_envelope build failed: %s", e)
        return {}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--print", action="store_true", dest="print_only",
                        help="compose and print to stdout; write nothing")
    parser.add_argument("--root", type=Path, default=None, help="repository root override")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if args.print_only:
        print(json.dumps(build(args.root), indent=2, ensure_ascii=False))
        return
    write(args.root)


if __name__ == "__main__":
    main()
