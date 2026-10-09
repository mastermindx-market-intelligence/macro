"""Read the canonical risk/rotation explanation; never infer a new risk verdict.

This is a consumer of Risk Envelope, not another composer or evidence owner.
Callers supply the observation clock and enforce their existing entitlement before
calling ``read_context``. No cache, ledger, network call, score or policy lives here.
"""
from __future__ import annotations

import copy
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

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

    World State/Brain are settled consumers here. The existing live Risk Envelope
    owner and Terminal bridge retain live selection/dwell; this reader does not
    create a competing live-precedence or cache rule.
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
    measured = context.get("measured_state") or {}
    rotation = context.get("rotation_context") or {}
    hazard = context.get("hazard_summary") or {}
    transition = context.get("market_transition") or {}
    audit = context.get("confluence") or {}
    # The producer owns these fields; consumers never derive a rotation from pairs.
    rotation_state = rotation.get("state") if rotation.get("usable") is True else None
    if rotation.get("usable") is True and rotation_state is None and isinstance(rotation.get("early_context"), dict):
        rotation_state = rotation["early_context"].get("state")
    backdrop = _MARKET.get(measured.get("verdict") if measured.get("usable") is True else None, ("Unavailable", "暂无读数"))[idx]
    leadership = _ROTATION.get(rotation_state, ("Rotation coverage unavailable", "轮动数据不全"))[idx]
    head = (f"[风险与轮动 · {context.get('source_session')}]" if zh else
            f"[RISK AND ROTATION · source session {context.get('source_session')}]")
    lines = [head,
             (f"市场背景：{backdrop}。相对强弱：{leadership}。" if zh else
              f"Market backdrop: {backdrop}. Relative leadership: {leadership}."),
             ("两者互为背景；重复的价格或广度读数不能增加信号权重。资金限制另有独立依据。" if zh else
              "These are complementary descriptions. Shared price/breadth inputs are not extra votes. Capital policy is separate."),
             ("相对跑赢不等于资金净流入、机构换手、成分股广度改善或未来抛售预测。" if zh else
              "Relative outperformance does not establish net inflows, institutional ownership transfers, constituent breadth, or a predicted selloff.")]
    # Bound the native projection before encoding. A large provenance object must
    # not crowd out the last actual recorded change or the missing-lineage caveat.
    change = transition.get("latest_recorded_change")
    change = change if isinstance(change, dict) else {}
    detail = {"hazard_stage": hazard.get("stage"), "coverage": context.get("data_state"),
              "rotation_as_of": rotation.get("as_of"),
              "last_recorded_change": {k: change.get(k) for k in ("before", "after", "verdict_changed", "cause")} if change else None,
              "current_matches_latest_record": transition.get("current_matches_latest_record"),
              "lineage_status": audit.get("lineage_status"),
              "unknown_lineage_sources": audit.get("unknown_lineage_sources"),
              "independence_established": False}
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
