"""Display-only warnings derived from existing, market-bound Risk Radar states.

This is a transport/presentation adapter, NOT a risk model, probability
calibration, capital policy, recovery detector or event store. The caller must
supply each market's independently established expected settled session. Never
use the snapshot's date as its own freshness reference. No clock is fabricated.

Supported native contracts: risk_radar.v2 (US), risk_radar_intl.v1 (country-bound).
Input-quality receipts remain distinct from artifact/session freshness. An
unverifiable refresh can retain a clearly labelled last-known severe warning;
it cannot turn unavailable data into a current market assertion.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import date
import math
import re
from typing import Any

SCHEMA = "mastermind.risk_warning/v1"
SET_SCHEMA = "mastermind.risk_warning_set/v1"
_STATE_ATTENTION = {
    "calm": "none", "watch": "watch", "caution": "warning",
    "elevated": "high", "risk-off": "critical",
}
_STATE_ORDER = {name: position for position, name in enumerate(_STATE_ATTENTION)}
_PRIORITY = {"none": 0, "watch": 1, "unavailable": 2, "warning": 3,
             "high": 4, "critical": 5}
_COPY = {
    "none": ("Radar is calm", "风险雷达平静",
             "No current Radar warning. This is not a recovery or re-entry signal.",
             "当前无雷达警告；这不代表底部确认或重新入场信号。"),
    "watch": ("Risk watch", "风险观察",
              "Monitor emerging risks and the next confirmed update.",
              "关注新出现的风险及下一次经确认的更新。"),
    "warning": ("Risk building", "风险正在累积",
                "Review exposure and a capital-protection plan; confirmation may still be incomplete.",
                "审视风险敞口及资本保护计划；确认条件可能尚未齐备。"),
    "high": ("Elevated market risk", "市场风险升高",
             "Prioritize exposure review and capital protection. A recovery is not established.",
             "优先审视风险敞口并保护资本；尚未确认复苏。"),
    "critical": ("Severe risk-off conditions", "严重风险规避状态",
                 "Capital protection deserves priority. Review leverage and liquidity; recovery is not established.",
                 "应优先保护资本，审视杠杆与流动性；尚未确认复苏。"),
    "unavailable": ("Risk verification unavailable", "风险状态无法核实",
                    "Current risk cannot be established. Missing data is not a safety signal.",
                    "无法确定当前风险；数据缺失不代表安全。"),
}


def _market_key(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{1,15}", value):
        raise ValueError("market must be a canonical short market key")
    return value.lower()


def _session(value: Any) -> str | None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _finite_number(value: Any, lower: float, upper: float) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and lower <= value <= upper and math.isfinite(value))


def _authority() -> dict:
    return {"display_only": True, "may_execute": False, "may_size": False,
            "may_gate": False, "may_rank": False}


def _copy_into(value: dict, attention: str) -> None:
    en, zh, detail_en, detail_zh = _COPY[attention]
    value.update(headline_en=en, headline_zh=zh,
                 detail_en=detail_en, detail_zh=detail_zh)


def _base(market: str, expected: str | None) -> dict:
    value = {
        "schema": SCHEMA, "market": market,
        "id": f"rw-{market}-{expected or 'unknown'}-unavailable",
        "status": "unavailable", "attention": "unavailable", "state": None,
        "state_ungated": None, "confirmation": "unknown",
        "source_schema": None, "source_session": None, "expected_session": expected,
        "artifact_freshness": "unavailable",
        "source_clock_basis": "source_asof_vs_owner_expected_session",
        "score": None, "score_semantics": "intensity_not_probability",
        "underlying_input_status": "unknown", "underlying_input_details": {},
        "reason_codes": [], "driver_en": None, "driver_zh": None,
        "authority": _authority(),
        "recovery": {"assessed": False, "reentry_authorized": False},
    }
    _copy_into(value, "unavailable")
    return value


def project_radar_warning(snapshot: Any, *, market: str, expected_session: Any,
                          input_quality: Any = None) -> dict:
    """Project one native Radar snapshot without changing its signal or authority.

    A caller/configuration error in `market` raises ValueError. Invalid source
    data returns an explicit unavailable record. `input_quality`, when provided,
    uses the existing any_input_stale / worst_input_age_days receipt fields;
    absence never becomes an assertion that all underlying inputs are fresh.
    """
    market = _market_key(market)
    expected = _session(expected_session)
    value = _base(market, expected)
    if expected is None:
        value["reason_codes"].append("expected_session_unavailable")
        return value
    if not isinstance(snapshot, Mapping):
        value["reason_codes"].append("snapshot_unavailable")
        return value
    schema = snapshot.get("schema")
    if schema not in ("risk_radar.v2", "risk_radar_intl.v1"):
        value["reason_codes"].append("unsupported_source_schema")
        return value
    value["source_schema"] = schema
    source_market = snapshot.get("market")
    if ((schema == "risk_radar.v2" and market != "us")
            or (schema == "risk_radar_intl.v1" and market == "us")
            or (schema == "risk_radar_intl.v1" and source_market is None)
            or (source_market is not None
                and (not isinstance(source_market, str) or source_market.lower() != market))):
        value["reason_codes"].append("source_market_mismatch")
        return value
    observed = _session(snapshot.get("asof"))
    value["source_session"] = observed
    if observed is None:
        value["reason_codes"].append("invalid_source_session")
        return value
    if observed != expected:
        value["reason_codes"].append("stale_source_session" if observed < expected
                                     else "future_source_session")
        value["artifact_freshness"] = "stale" if observed < expected else "future"
        return value
    state = snapshot.get("state")
    if not isinstance(state, str) or state not in _STATE_ATTENTION:
        value["reason_codes"].append("invalid_state")
        return value
    ungated = snapshot.get("state_ungated")
    if ungated is not None and (not isinstance(ungated, str) or ungated not in _STATE_ATTENTION):
        value["reason_codes"].append("invalid_ungated_state")
        return value
    score = snapshot.get("top_score")
    if score is not None and not _finite_number(score, 0, 100):
        value["reason_codes"].append("invalid_score")
        return value
    attention = _STATE_ATTENTION[state]
    value.update(
        id=f"rw-{market}-{observed}-{state}", status="current", attention=attention,
        state=state, state_ungated=ungated, score=score, artifact_freshness="current",
        confirmation=("pending" if ungated is not None
                      and _STATE_ORDER[ungated] > _STATE_ORDER[state] else "engine_state_only"),
    )
    _copy_into(value, attention)
    for field, source_key in (("driver_en", "dominant_label_en"),
                              ("driver_zh", "dominant_label_zh")):
        label = snapshot.get(source_key)
        if isinstance(label, str) and label.strip():
            value[field] = label.strip()[:240]  # render via textContent, never HTML
    if input_quality is not None:
        if not isinstance(input_quality, Mapping) or type(input_quality.get("any_input_stale")) is not bool:
            value["reason_codes"].append("invalid_input_quality")
        else:
            stale = input_quality["any_input_stale"]
            value["underlying_input_status"] = "degraded" if stale else "reported_current"
            if stale:
                value["reason_codes"].append("underlying_inputs_stale")
            age = input_quality.get("worst_input_age_days")
            if age is not None:
                if _finite_number(age, 0, 365000):
                    value["underlying_input_details"]["worst_input_age_days"] = age
                else:
                    value["underlying_input_status"] = "unknown" if not stale else "degraded"
                    value["reason_codes"].append("invalid_input_age")
    degraded_reason = snapshot.get("degraded_reason")
    if degraded_reason:
        value["underlying_input_status"] = "degraded"
        value["reason_codes"].append("source_reports_degradation")
    return value


def _prior_severe(previous: Any, market: str) -> dict | None:
    if not isinstance(previous, Mapping) or previous.get("market") != market:
        return None
    candidate = previous.get("last_known") if previous.get("status") == "unverified" else previous
    if not isinstance(candidate, Mapping):
        return None
    state = candidate.get("state")
    session = _session(candidate.get("source_session"))
    source_schema = "risk_radar.v2" if market == "us" else "risk_radar_intl.v1"
    if (candidate.get("schema") != SCHEMA or candidate.get("market") != market
            or candidate.get("status") != "current"
            or not isinstance(state, str) or state not in ("elevated", "risk-off")
            or candidate.get("attention") != _STATE_ATTENTION[state]
            or session is None or candidate.get("expected_session") != session
            or candidate.get("source_schema") != source_schema
            or candidate.get("id") != f"rw-{market}-{session}-{state}"):
        return None
    # A cached projection is a receipt, not an extensible authority object.
    # Rebuild only owned, bounded fields through the same pure constructor;
    # never retain arbitrary extensions, nested authority or malformed numbers.
    score = candidate.get("score")
    ungated = candidate.get("state_ungated")
    source = {
        "schema": source_schema, "market": market, "asof": session,
        "state": state, "top_score": score if _finite_number(score, 0, 100) else None,
        "state_ungated": (ungated if isinstance(ungated, str)
                          and ungated in _STATE_ATTENTION else None),
        "dominant_label_en": candidate.get("driver_en"),
        "dominant_label_zh": candidate.get("driver_zh"),
    }
    value = project_radar_warning(source, market=market, expected_session=session)
    quality = candidate.get("underlying_input_status")
    if quality in ("unknown", "reported_current", "degraded"):
        value["underlying_input_status"] = quality
    details = candidate.get("underlying_input_details")
    age = details.get("worst_input_age_days") if isinstance(details, Mapping) else None
    if _finite_number(age, 0, 365000):
        value["underlying_input_details"]["worst_input_age_days"] = age
    known_reasons = ("underlying_inputs_stale", "invalid_input_quality",
                     "invalid_input_age", "source_reports_degradation")
    reasons = candidate.get("reason_codes")
    if isinstance(reasons, list):
        value["reason_codes"] = [reason for reason in known_reasons if reason in reasons]
    return value


def retain_unresolved_warning(current: dict, previous: Any) -> dict:
    """Preserve a last-known severe warning when current verification fails.

    No ledger, capital authority or fabricated current state is created. A
    current lower state can replace the warning but is never a bottom call.
    The caller retains only this bounded view in its existing delivery state.
    """
    value = deepcopy(current)
    prior = _prior_severe(previous, value.get("market"))
    if prior is None:
        return value
    if value.get("status") == "current":
        if value["source_session"] >= prior["source_session"]:
            return value
        value["reason_codes"].append("out_of_order_delivery")
    elif value.get("status") not in ("unavailable", "unverified"):
        return value
    value.update(
        status="unverified", attention=prior["attention"], state=None,
        state_ungated=None, score=None, confirmation="unknown",
        artifact_freshness="unavailable", id=prior["id"] + "-unverified",
    )
    # One bounded original projection, not an accumulating recursive history.
    value["last_known"] = {key: deepcopy(item) for key, item in prior.items() if key != "last_known"}
    value["headline_en"] = "Verification unavailable — last known severe risk"
    value["headline_zh"] = "无法核实当前状态——上次为严重风险"
    value["detail_en"] = "The previous severe warning has not been cleared by current evidence."
    value["detail_zh"] = "当前证据尚未解除此前的严重风险警告。"
    return value


def project_warning_set(snapshots: Any, expected_sessions: Any, *, previous: Any = None,
                        input_qualities: Any = None) -> dict:
    """Project the explicitly expected market set; never average risk scores.

    Calendars and universe remain with existing owners. A missing requested
    market gets an unavailable row instead of disappearing from the denominator.
    """
    if not isinstance(expected_sessions, Mapping) or not expected_sessions:
        raise ValueError("a nonempty expected-session market manifest is required")
    expected = {}
    for key, session in expected_sessions.items():
        market = _market_key(key)
        if market in expected:
            raise ValueError("duplicate normalized market key")
        expected[market] = session
    sources = {}
    if isinstance(snapshots, Mapping):
        for key, value in snapshots.items():
            market = _market_key(key)
            if market in sources:
                raise ValueError("duplicate normalized snapshot key")
            sources[market] = value
    def normalized_optional(source):
        out = {}
        if isinstance(source, Mapping):
            for key, item in source.items():
                normalized = _market_key(key)
                if normalized in out:
                    raise ValueError("duplicate normalized optional-receipt key")
                out[normalized] = item
        return out

    previous = normalized_optional(previous)
    qualities = normalized_optional(input_qualities)
    rows = [retain_unresolved_warning(
        project_radar_warning(sources.get(market), market=market,
                              expected_session=session, input_quality=qualities.get(market)),
        previous.get(market),
    ) for market, session in expected.items()]
    rows.sort(key=lambda row: (-_PRIORITY[row["attention"]], row["market"]))
    counts = {name: 0 for name in _STATE_ATTENTION.values()}
    for row in rows:
        if row["status"] == "current":
            counts[row["attention"]] += 1
    return {
        "schema": SET_SCHEMA, "rows": rows, "authority": _authority(),
        "current_attention_counts": counts,
        "coverage": {
            "expected": len(expected),
            "current": sum(row["status"] == "current" for row in rows),
            "unavailable_markets": sorted(row["market"] for row in rows if row["status"] != "current"),
            "unrequested_markets": sorted(set(sources) - set(expected)),
        },
        "last_known_severe_markets": sorted(row["market"] for row in rows if row["status"] == "unverified"),
    }
