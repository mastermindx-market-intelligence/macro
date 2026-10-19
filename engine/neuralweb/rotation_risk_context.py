"""Read the canonical risk/rotation explanation; never infer a new risk verdict.

This is a consumer of Risk Envelope, not another composer or evidence owner.
Callers supply the observation clock and enforce their existing entitlement before
calling ``read_context``. No cache, ledger, network call, score or policy lives here.
"""
from __future__ import annotations

import copy
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from engine.risk_envelope import (
    LIVE_MARKET_FUTURE_TOLERANCE_S, STAGE_VOCABULARY, live_market_freshness,
)
from lib import nyse_calendar

SCHEMA = "mastermind.risk_envelope/v1"
_MARKET = {"RISK_ON": ("Risk-on", "风险偏好"), "MIXED": ("Mixed", "混合"),
           "RISK_OFF": ("Risk-off", "避险")}
_ROTATION = {
    "DEFENSIVE_RELATIVE_STRENGTH": ("Defensive groups gaining relative strength", "防御板块相对转强"),
    "BROADENING": ("Broader-market proxies gaining relative strength", "更广市场代理相对转强"),
    "MIXED_ROTATION": ("Defensive groups and broader-market proxies gaining relative strength", "防御板块与更广市场代理相对转强"),
    "NO_EARLY_SHIFT": ("No short-term relative shift measured", "未测得短期相对强弱变化"),
}
_CONTEXT_FIELDS = (
    "schema", "definition_id", "market", "revision", "source_session", "as_of",
    "observed_at", "produced_at", "stale_after", "bundle_id", "measured_state",
    "hazard_summary", "policy_summary", "data_state", "coverage", "freshness",
    "rotation_context", "confluence", "market_transition", "authority",
)


def _instant(value: Any) -> datetime | None:
    if not isinstance(value, str) or "T" not in value:
        return None
    try:
        out = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return out.astimezone(timezone.utc) if out.tzinfo else None
    except (ValueError, OverflowError):
        return None


def _session(value: Any) -> date | None:
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        parsed = date.fromisoformat(value)
        return parsed if parsed.isoformat() == value else None
    except ValueError:
        return None


def _unavailable(reason: str, payload: dict | None = None) -> dict:
    native = payload or {}
    return {"schema": SCHEMA, "usable": False, "reason": reason,
            "source_session": native.get("source_session"),
            "as_of": native.get("as_of"), "bundle_id": native.get("bundle_id"),
            "display_only": True, "derived_from": "risk-envelope-settled"}


def compact_context(payload: Any, *, now: datetime,
                    expected_session: str | None = None) -> dict:
    """Qualify source clocks and carry native fields without recomputing them.

    A fresh consumer build cannot refresh an old source. ``usable`` means the
    artifact is readable for its stated session, not that its coverage is complete
    or that it has predictive, ranking, sizing or execution authority.
    """
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        return _unavailable("missing_or_invalid_envelope")
    if now.tzinfo is None:
        return _unavailable("observation_clock_unqualified", payload)
    now = now.astimezone(timezone.utc)
    day = _session(payload.get("source_session"))
    if day is None or _session(payload.get("as_of")) != day:
        return _unavailable("source_session_unqualified", payload)
    if day > now.astimezone(ZoneInfo("America/New_York")).date():
        return _unavailable("future_source_session", payload)
    if expected_session is not None and payload.get("source_session") != expected_session:
        return _unavailable("source_session_mismatch", payload)
    clocks = {}
    for name in ("observed_at", "produced_at"):
        instant = _instant(payload.get(name))
        if instant is None or instant > now:
            return _unavailable("unqualified_" + name, payload)
        clocks[name] = instant
    if clocks["observed_at"] > clocks["produced_at"]:
        return _unavailable("source_clock_order_invalid", payload)
    expires = payload.get("stale_after")
    if expires is not None:
        expiry = _instant(expires)
        if expiry is None or expiry <= now:
            return _unavailable("expired_or_invalid_source_clock", payload)
    if payload.get("data_state") == "STALE":
        return _unavailable("stale_source_coverage", payload)
    authority = payload.get("authority")
    flags = ("envelope_may_rank", "envelope_may_gate", "envelope_may_size",
             "envelope_may_execute")
    if not isinstance(authority, dict) or any(authority.get(k) is not False for k in flags):
        return _unavailable("authority_contract_unqualified", payload)
    for name in ("measured_state", "hazard_summary", "policy_summary"):
        if not isinstance(payload.get(name), dict):
            return _unavailable("invalid_" + name, payload)
    for name in ("rotation_context", "confluence", "market_transition"):
        if payload.get(name) is not None and not isinstance(payload[name], dict):
            return _unavailable("invalid_" + name, payload)
    measured = payload["measured_state"]
    if measured.get("usable") is True and measured.get("as_of") != payload["source_session"]:
        return _unavailable("measured_source_session_mismatch", payload)
    rotation = payload.get("rotation_context") or {}
    if rotation.get("usable") is True and rotation.get("as_of") != payload["source_session"]:
        return _unavailable("rotation_source_session_mismatch", payload)
    out = {key: copy.deepcopy(payload.get(key)) for key in _CONTEXT_FIELDS}
    out.update(usable=True, reason=None, display_only=True,
               derived_from="risk-envelope-settled",
               evidence_note="Repeated source context; no additional evidence vote or authority.")
    return out


def read_context(root: Path, *, now: datetime,
                 expected_session: str | None = None) -> dict:
    """Read one canonical settled artifact after caller authorization. No fallback.

    World State and callers of this API remain settled consumers. The explicit
    per-turn read_preferred_context API qualifies the existing live owner's
    wrapper; neither reader advances dwell or creates a cache.
    """
    path = Path(root) / "data" / "risk_envelope" / "latest.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return _unavailable("missing_or_invalid_envelope")
    if expected_session is None:
        # Source qualification uses the existing settled Market State session;
        # the read time never substitutes for its economic date.
        try:
            market = json.loads((Path(root) / "data" / "market_state" / "latest.json").read_text(encoding="utf-8"))
            expected_session = market.get("asof") if isinstance(market, dict) else None
        except (OSError, ValueError, TypeError):
            pass
    return compact_context(payload, now=now, expected_session=expected_session)


def _source_instant(value: Any, *, generated: bool = False) -> datetime | None:
    instant = _instant(value)
    if instant is not None or not generated or not isinstance(value, str):
        return instant
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)
        return parsed if parsed.strftime("%Y-%m-%d %H:%M UTC") == value else None
    except (ValueError, OverflowError):
        return None


def _receipt_clock_status(receipt: Any, *, now: datetime) -> dict:
    """Check every original alias; production is never original availability."""
    out = {"reason": None, "availability": "UNKNOWN", "expiry": "UNKNOWN"}
    if receipt is None:
        return out
    if not isinstance(receipt, dict):
        return dict(out, reason="malformed_source_clock_receipt")
    availability = receipt.get("availability")
    if availability is not None and not isinstance(availability, dict):
        return dict(out, reason="malformed_availability")
    aliases = [(key, receipt.get(key)) for key in
               ("produced_at", "generated_utc", "available_at")]
    if isinstance(availability, dict):
        aliases.append(("available_at", availability.get("available_at")))
    for key, value in aliases:
        if value is None:
            continue
        stamp = _source_instant(value, generated=key == "generated_utc")
        if stamp is None:
            return dict(out, reason="malformed_source_clock")
        if stamp > now:
            return dict(out, reason=("source_not_available" if key == "available_at"
                                     else "future_production_clock"))
        if key == "available_at":
            out["availability"] = "RECORDED"
    if isinstance(availability, dict) and availability.get("status") == "UNKNOWN":
        out["availability"] = "UNKNOWN"
    expiry = receipt.get("stale_after")
    if expiry is not None:
        stamp = _instant(expiry)
        if stamp is None:
            return dict(out, reason="malformed_source_expiry")
        if stamp <= now:
            return dict(out, reason="source_expired", expiry="EXPIRED")
        out["expiry"] = "UNEXPIRED"
    fresh = receipt.get("freshness")
    if fresh is not None:
        if not isinstance(fresh, dict) or ("stale" in fresh and type(fresh["stale"]) is not bool):
            return dict(out, reason="malformed_freshness")
        if fresh.get("stale") is True:
            return dict(out, reason="source_stale")
    return out


def _rotation_turn_status(rotation: dict | None, *, session: str, now: datetime) -> dict:
    """Reader-only qualification; native state and confluence are not rewritten."""
    out = {"current_at_turn": False, "reason": "rotation_unavailable",
           "availability": "UNKNOWN", "expiry": "UNKNOWN",
           "independent_evidence_vote": False}
    if not isinstance(rotation, dict) or rotation.get("usable") is not True:
        return out
    early = rotation.get("early_context")
    if (rotation.get("as_of") != session or not isinstance(early, dict)
            or early.get("schema") != "rotation_early_context/v1"
            or early.get("as_of") != session):
        return dict(out, reason="rotation_source_session_unqualified")
    parent = _receipt_clock_status(rotation.get("source_clock_receipt"), now=now)
    child = _receipt_clock_status(early, now=now)
    out.update(availability=child["availability"],
               expiry="EXPIRED" if parent["expiry"] == "EXPIRED" else child["expiry"])
    if parent["reason"] or child["reason"]:
        return dict(out, reason=parent["reason"] or child["reason"])
    if child["availability"] == "UNKNOWN":
        return dict(out, reason="original_availability_unknown")
    if child["expiry"] == "UNKNOWN":
        return dict(out, reason="source_expiry_unknown")
    return dict(out, current_at_turn=True, reason=None)


def _live_unavailable(reason: str, payload: dict | None = None) -> dict:
    out = _unavailable(reason, payload)
    out["derived_from"] = "risk-envelope-live"
    return out


def qualify_live_context(payload: Any, *, settled: dict, now: datetime) -> dict:
    """Qualify the existing live owner's projection against its real settled anchor.

    No state is composed, no dwell advances, and source IDs/clocks are not changed.
    The returned selection/rotation_at_turn fields are reader qualifications only.
    """
    if not isinstance(now, datetime) or now.tzinfo is None:
        return _live_unavailable("observation_clock_unqualified")
    try:
        now = now.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return _live_unavailable("observation_clock_unqualified")
    anchor = compact_context(settled, now=now)
    if (not anchor.get("usable") or anchor.get("revision") not in ("settled", "corrected")
            or not isinstance(anchor.get("bundle_id"), str) or not anchor["bundle_id"]):
        return _live_unavailable("settled_anchor_unqualified")
    out = compact_context(payload, now=now)
    if not out.get("usable"):
        return _live_unavailable(out["reason"], payload if isinstance(payload, dict) else None)
    if payload.get("revision") != "live_provisional":
        return _live_unavailable("live_revision_unqualified", payload)
    if payload.get("live_active") is not True or payload.get("precedence") != "live":
        return _live_unavailable("live_owner_not_active", payload)
    session = payload["source_session"]
    overlay = payload.get("overlays")
    if (not isinstance(overlay, dict)
            or overlay.get("settled_source_session") != anchor["source_session"]
            or overlay.get("settled_bundle_id") != anchor["bundle_id"]):
        return _live_unavailable("settled_anchor_mismatch", payload)
    if session <= anchor["source_session"]:
        return _live_unavailable("live_not_ahead_of_settled", payload)
    clocks = payload.get("clocks")
    if not isinstance(clocks, dict):
        return _live_unavailable("live_clocks_unqualified", payload)
    if any(_instant(clocks.get(key)) != _instant(payload.get(key))
           for key in ("observed_at", "produced_at")):
        return _live_unavailable("live_clock_alias_mismatch", payload)
    # Check every supplied original-availability alias before compacting. An
    # earlier first availability may legitimately precede re-publication; neither
    # a production clock nor this turn supplies a missing availability.
    for receipt in (payload, clocks):
        if receipt.get("available_at") is not None:
            available = _instant(receipt["available_at"])
            if available is None or available > now:
                return _live_unavailable("live_availability_unqualified", payload)
    built_dt = _instant(clocks.get("upstream_built"))
    ttl = payload.get("stale_after_min")
    if built_dt is None:
        return _live_unavailable("upstream_clock_unqualified", payload)
    try:
        if (type(ttl) not in (int, float) or not math.isfinite(ttl) or ttl <= 0
                or not math.isfinite(ttl * 60.0)):
            return _live_unavailable("live_ttl_unqualified", payload)
        fresh_through = built_dt + timedelta(minutes=ttl)
        fresh = live_market_freshness(live_active=True, built_dt=built_dt,
                                      stale_after_min=ttl, now=now)
    except (ValueError, OverflowError):
        return _live_unavailable("live_ttl_unqualified", payload)
    if not fresh["usable"]:
        return _live_unavailable("upstream_clock_future" if fresh["future_artifact"]
                                 else "upstream_clock_expired", payload)
    try:
        today_et = now.astimezone(ZoneInfo("America/New_York")).date()
        if (not nyse_calendar.is_session(today_et)
                or session != nyse_calendar.session_date(now).isoformat()
                or session != nyse_calendar.session_date(built_dt).isoformat()):
            return _live_unavailable("live_session_unqualified", payload)
    except (ValueError, OverflowError):
        return _live_unavailable("live_session_unqualified", payload)
    event_time = clocks.get("event_time")
    if event_time is not None:
        event = _instant(event_time)
        # Only carrying-built coordinates receive the original skew tolerance.
        # The source event may have finer precision than the whole-second built
        # stamp; do not invent a cross-clock ordering against that coarse stamp.
        if event is None or event > now:
            return _live_unavailable("source_event_clock_unqualified", payload)
    transition = payload.get("live_transition")
    if not isinstance(transition, dict) or transition.get("session") != session:
        return _live_unavailable("live_transition_unqualified", payload)
    for key in ("stable_stage", "candidate_stage"):
        if key not in transition or (transition[key] is not None and
                (not isinstance(transition[key], str) or transition[key] not in STAGE_VOCABULARY)):
            return _live_unavailable("live_transition_unqualified", payload)
    if transition["candidate_stage"] != payload["hazard_summary"].get("stage"):
        return _live_unavailable("live_candidate_mismatch", payload)
    pending = transition.get("pending")
    if pending is not None:
        if (not isinstance(pending, dict) or not isinstance(pending.get("stage"), str)
                or pending["stage"] not in STAGE_VOCABULARY
                or type(pending.get("ticks")) is not int or type(pending.get("needs")) is not int
                or not 0 < pending["ticks"] < pending["needs"]):
            return _live_unavailable("live_pending_unqualified", payload)
    observed_built = transition.get("last_observed_built")
    if observed_built is not None:
        try:
            stamp = datetime.strptime(observed_built, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
            if (stamp - now).total_seconds() > LIVE_MARKET_FUTURE_TOLERANCE_S:
                return _live_unavailable("live_observation_unqualified", payload)
        except (TypeError, ValueError, OverflowError):
            return _live_unavailable("live_observation_unqualified", payload)
    for key in ("live_active", "precedence", "stale_after_min", "overlays", "live_transition", "clocks"):
        out[key] = copy.deepcopy(payload[key])
    if "available_at" in payload:
        out["available_at"] = copy.deepcopy(payload["available_at"])
    out.update(derived_from="risk-envelope-live", selection={
        "plane": "live", "reason": None,
        "fresh_through": fresh_through.isoformat(), "ttl_boundary": "inclusive",
        "explicit_stale_after": payload.get("stale_after"),
        "settled_source_session": anchor["source_session"],
        "settled_bundle_id": anchor["bundle_id"],
    }, rotation_at_turn=_rotation_turn_status(payload.get("rotation_context"),
                                              session=session, now=now))
    return out


def read_preferred_context(root: Path, *, now: datetime) -> dict:
    """Per-turn live preference after caller entitlement; settled default is separate.

    Read existing explicit artifacts once. The live owner must name the exact
    settled generation read here; mismatches fall back, without a retry or cache.
    """
    settled = read_context(root, now=now)
    try:
        payload = json.loads((Path(root) / "site" / "live" / "risk_envelope.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        live = _live_unavailable("missing_or_invalid_live_envelope")
    else:
        live = qualify_live_context(payload, settled=settled, now=now)
    if live.get("usable"):
        return live
    out = copy.deepcopy(settled)
    out["selection"] = {"plane": "settled" if out.get("usable") else "unavailable",
                        "live_reason": live["reason"]}
    return out


def redact_new_context(payload: Any) -> Any:
    """Remove only this feature's additions at an unentitled chat boundary.

    Cortex retains the stored blackboard. This also handles read_artifact's
    content wrapper; a second tool spelling cannot expose protected additions.
    Never mutates a shared cached object.
    """
    if isinstance(payload, list):
        return [redact_new_context(value) for value in payload]
    if not isinstance(payload, dict):
        return payload
    envelope = payload.get("schema") == SCHEMA
    out = {}
    for key, value in payload.items():
        if key == "risk_envelope":
            continue
        if key == "early_context" and isinstance(value, dict) and value.get("schema") == "rotation_early_context/v1":
            continue
        if envelope and key in ("rotation_context", "confluence", "market_transition"):
            continue
        out[key] = redact_new_context(value)
    return out


def render_context(context: dict, *, lang: str = "en", char_budget: int = 1800) -> str:
    """Bounded source-attributed model grounding, with no probability or new stance."""
    zh = lang == "zh"
    idx = int(zh)
    if not context.get("usable"):
        return ("[风险与轮动] 当前关联读数不可用；不可据此推断市场平静。" if zh else
                "[RISK AND ROTATION] Current joint context unavailable; absence is not evidence of calm.")
    live = context.get("derived_from") == "risk-envelope-live"
    measured = context.get("measured_state") or {}
    rotation = context.get("rotation_context") or {}
    hazard = context.get("hazard_summary") or {}
    transition = context.get("market_transition") or {}
    audit = context.get("confluence") or {}
    # The producer owns these fields; consumers never derive a rotation from pairs.
    rotation_usable = (rotation.get("usable") is True and
                       (not live or (context.get("rotation_at_turn") or {}).get("current_at_turn") is True))
    rotation_state = rotation.get("state") if rotation_usable else None
    if rotation_usable and rotation_state is None and isinstance(rotation.get("early_context"), dict):
        rotation_state = rotation["early_context"].get("state")
    backdrop = _MARKET.get(measured.get("verdict") if measured.get("usable") is True else None, ("Unavailable", "暂无读数"))[idx]
    leadership = _ROTATION.get(rotation_state, ("Rotation coverage unavailable", "轮动数据不全"))[idx]
    head = (f"[风险与轮动 · {context.get('source_session')}]" if zh else
            f"[RISK AND ROTATION · source session {context.get('source_session')}]")
    if live:
        anchor = (context.get("overlays") or {}).get("settled_source_session")
        head += (f" 实时暂定；已结算锚点 {anchor}" if zh else
                 f" Live provisional; settled anchor {anchor}")
    lines = [head,
             (f"市场背景：{backdrop}。相对强弱：{leadership}。" if zh else
              f"Market backdrop: {backdrop}. Relative leadership: {leadership}."),
             ("两者互为背景；重复的价格或广度读数不能增加信号权重。资金限制另有独立依据。" if zh else
              "These are complementary descriptions. Shared price/breadth inputs are not extra votes. Capital policy is separate."),
             ("相对跑赢不等于资金净流入、机构换手、成分股广度改善或未来抛售预测。" if zh else
              "Relative outperformance does not establish net inflows, institutional ownership transfers, constituent breadth, or a predicted selloff.")]
    if live:
        dwell = context.get("live_transition") or {}
        pending = dwell.get("pending")
        pending_text = (f"{pending['stage']} {pending['ticks']}/{pending['needs']}"
                        if isinstance(pending, dict) else ("无" if zh else "none"))
        stable = dwell.get("stable_stage")
        candidate = dwell.get("candidate_stage")
        unknown = "暂无读数" if zh else "unavailable"
        lines.insert(2, (f"风险阶段：已接受 {stable if stable is not None else unknown}；"
                         f"候选 {candidate if candidate is not None else unknown}；待确认 {pending_text}。" if zh else
                         f"Hazard stage: accepted {stable if stable is not None else unknown}; "
                         f"candidate {candidate if candidate is not None else unknown}; pending {pending_text}."))
        timing = context.get("rotation_at_turn") or {}
        availability = timing.get("availability", "UNKNOWN")
        expiry = timing.get("expiry", "UNKNOWN")
        lines.append((f"轮动原始可用时间：{availability}；到期状态：{expiry}。" if zh else
                      f"Rotation original availability: {availability}; expiry: {expiry}."))
        if timing.get("current_at_turn") is not True:
            lines.append("该轮动子读数未获当前时点的证据资格。" if zh else
                         "This rotation child is not qualified as current evidence.")
    # Bound the native projection before encoding. A large provenance object must
    # not crowd out the last actual recorded change or the missing-lineage caveat.
    change = transition.get("latest_recorded_change")
    change = change if isinstance(change, dict) else {}
    detail = {"hazard_stage": (context["live_transition"].get("stable_stage") if live else hazard.get("stage")), "coverage": context.get("data_state"),
              "rotation_as_of": rotation.get("as_of"),
              "last_recorded_change": {k: change.get(k) for k in ("before", "after", "verdict_changed", "cause")} if change else None,
              "current_matches_latest_record": transition.get("current_matches_latest_record"),
              "lineage_status": audit.get("lineage_status"),
              "unknown_lineage_sources": audit.get("unknown_lineage_sources"),
              "independence_established": False}
    if live:
        detail["candidate_stage"] = context["live_transition"].get("candidate_stage")
        detail["pending"] = context["live_transition"].get("pending")
    text = "\n".join(lines)
    remaining = max(0, int(char_budget) - len(text) - 1)
    if remaining > 200:
        encoded = json.dumps(detail, ensure_ascii=False, separators=(",", ":"))
        if len(encoded) <= remaining:
            text += "\n" + encoded
        else:
            text += "\n" + ("详细依据超出本段预算；不能将省略项视为已确认。" if zh else
                            "Detailed receipts exceed this context budget; omitted evidence is not confirmation.")
    return text[:max(0, int(char_budget))]
