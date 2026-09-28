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


BRIEFING_SCHEMA = "mastermind.risk_warning_briefing/v1"
_BRIEF_STANCE = {
    "calm": ("Observe", "观察"),
    "watch": ("Get ready", "做好准备"),
    "caution": ("Reduce concentration", "降低集中度"),
    "elevated": ("Protect gains / reduce gross", "保护收益／降低总敞口"),
    "risk-off": ("Stand aside / protect capital", "暂避风险／保护资本"),
}


def _safe_num(value: Any, *, lower: float = -1_000_000.0,
              upper: float = 1_000_000.0) -> float | int | None:
    return value if _finite_number(value, lower, upper) else None


def _owner_sources(risk_envelope: Any) -> list[Mapping]:
    if not isinstance(risk_envelope, Mapping):
        return []
    provenance = risk_envelope.get("provenance")
    sources = provenance.get("sources") if isinstance(provenance, Mapping) else None
    return [source for source in sources if isinstance(source, Mapping)] if isinstance(sources, list) else []


def _briefing_drivers(radar: Any, risk_envelope: Any) -> list[dict]:
    out: list[dict] = []
    remaining_scares: list[Mapping] = []
    if isinstance(radar, Mapping):
        scares = radar.get("scares")
        if isinstance(scares, list):
            candidates = [s for s in scares if isinstance(s, Mapping)]
            candidates.sort(key=lambda s: -float(_safe_num(s.get("score"), lower=0, upper=100) or -1))
            dominant = radar.get("dominant_scare")
            ordered = ([s for s in candidates if s.get("scare") == dominant] +
                       [s for s in candidates if s.get("scare") != dominant])
            remaining_scares = ordered
            if ordered:
                scare = ordered.pop(0)
                key, label = scare.get("scare"), scare.get("label_en")
                if isinstance(key, str) and isinstance(label, str) and label.strip():
                    out.append({
                        "key": f"radar:{key}", "kind": "risk_radar",
                        "label_en": label.strip()[:160],
                        "label_zh": (scare.get("label_zh") if isinstance(scare.get("label_zh"), str) else label)[:160],
                        "state": scare.get("band") if isinstance(scare.get("band"), str) else None,
                        "score": _safe_num(scare.get("score"), lower=0, upper=100),
                    })
    known = {d["key"] for d in out}
    owner_rows = []
    for source in _owner_sources(risk_envelope):
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or source_id in ("risk-radar-us",) or source_id in known:
            continue
        label = source.get("label_en")
        if not isinstance(label, str) or not label.strip():
            continue
        owner_rows.append({
            "key": source_id, "kind": str(source.get("role") or "owner_evidence"),
            "label_en": label.strip()[:160],
            "label_zh": (source.get("label_zh") if isinstance(source.get("label_zh"), str) else label)[:160],
            "state": source.get("state") if isinstance(source.get("state"), str) else None,
            "score": None,
            "coverage": source.get("coverage") if isinstance(source.get("coverage"), str) else None,
        })
    owner_rows.sort(key=lambda row: (0 if row.get("state") in ("BROKEN", "RISK_OFF", "elevated", "risk-off") else 1, row["key"]))
    out.extend(owner_rows[:2])
    for scare in remaining_scares:
        if len(out) >= 5:
            break
        key, label = scare.get("scare"), scare.get("label_en")
        if not isinstance(key, str) or not isinstance(label, str) or not label.strip():
            continue
        out.append({
            "key": f"radar:{key}", "kind": "risk_radar",
            "label_en": label.strip()[:160],
            "label_zh": (scare.get("label_zh") if isinstance(scare.get("label_zh"), str) else label)[:160],
            "state": scare.get("band") if isinstance(scare.get("band"), str) else None,
            "score": _safe_num(scare.get("score"), lower=0, upper=100),
        })
    return out


def _downside_view(warning: Mapping, radar: Any) -> dict:
    blank = {
        "target": None, "h5": None, "h10": None, "h21": None,
        "base_h21": None, "lift_h21": None, "above_base": None,
        "calibration_status": "unavailable", "precision_grade": False,
        "interpretation": "unavailable", "limitations": [],
    }
    if warning.get("status") != "current" or not isinstance(radar, Mapping):
        return blank
    market = warning.get("market")
    dp = radar.get("drawdown_prob")
    if not isinstance(dp, Mapping):
        return blank
    if market != "us":
        blank["calibration_status"] = "directional_only"
        blank["interpretation"] = "directional_only"
        return blank
    evidence = dp.get("calibration_evidence")
    if not isinstance(evidence, Mapping):
        return blank
    target = evidence.get("target") if isinstance(evidence.get("target"), Mapping) else {}
    depth = _safe_num(target.get("depth"), lower=0, upper=1)
    horizons = target.get("horizons") if isinstance(target.get("horizons"), list) else []
    path = target.get("price_path") if isinstance(target.get("price_path"), str) else None
    target_text = None
    if depth is not None and horizons:
        target_text = f">={round(depth * 100)}% SPY pullback / {max(horizons)} sessions"
        if path:
            target_text += f" ({path})"
    h5 = _safe_num(dp.get("h5"), lower=0, upper=1)
    h10 = _safe_num(dp.get("h10"), lower=0, upper=1)
    h21 = _safe_num(dp.get("h21"), lower=0, upper=1)
    base = _safe_num(dp.get("base_h21"), lower=0, upper=1)
    lift = _safe_num(dp.get("lift_h21"), lower=0, upper=100)
    above = dp.get("state_above_base") if type(dp.get("state_above_base")) is bool else (
        bool(h21 > base) if h21 is not None and base is not None else None)
    limitations = evidence.get("limitations")
    if not isinstance(limitations, list):
        limitations = []
    return {
        "target": target_text, "h5": h5, "h10": h10, "h21": h21,
        "base_h21": base, "lift_h21": lift, "above_base": above,
        "calibration_status": str(evidence.get("evidence_class") or "available"),
        "precision_grade": bool(evidence.get("precision_grade") is True),
        "interpretation": "above_base" if above is True else ("early_flag_not_edge" if above is False else "unavailable"),
        "limitations": [str(item)[:240] for item in limitations if isinstance(item, str)][:4],
    }


def _backdrop_view(regime: Any, market_state: Any, material_risk: bool) -> dict:
    rg = regime if isinstance(regime, Mapping) else {}
    ms = market_state if isinstance(market_state, Mapping) else {}
    name = rg.get("quad_name") if isinstance(rg.get("quad_name"), str) else None
    verdict = ms.get("verdict") if isinstance(ms.get("verdict"), str) else None
    components = ms.get("components")
    component_rows = []
    if isinstance(components, Mapping):
        iterable = [(key, value) for key, value in components.items()]
    elif isinstance(components, list):
        iterable = [(value.get("key"), value) for value in components if isinstance(value, Mapping)]
    else:
        iterable = []
    for key, value in iterable:
        if not isinstance(key, str) or not isinstance(value, Mapping):
            continue
        score = _safe_num(value.get("score"), lower=0, upper=100)
        if score is None:
            continue
        row = {"key": key, "score": score}
        if isinstance(value.get("label_en"), str):
            row["label_en"] = value["label_en"][:160]
        if isinstance(value.get("read_en"), str):
            row["read_en"] = value["read_en"][:240]
        component_rows.append(row)
    separation = None
    if material_risk and name == "Reflation":
        separation = "Reflation does not mean the tape is safe. The economic backdrop and market damage are different reads."
    elif material_risk and name:
        separation = f"{name} is economic backdrop, not a safety signal. Market damage is a separate read."
    return {
        "regime": name,
        "quad": rg.get("quad") if isinstance(rg.get("quad"), str) else None,
        "transition": rg.get("transition_state") if isinstance(rg.get("transition_state"), str) else None,
        "growth_score": _safe_num(rg.get("growth_score")),
        "inflation_score": _safe_num(rg.get("inflation_score")),
        "market_state_score": _safe_num(ms.get("score"), lower=0, upper=100),
        "market_state_verdict": verdict,
        "components": component_rows,
        "separation_note_en": separation,
    }


def _recovery_view(recovery: Any) -> dict:
    base = {"state": "UNESTABLISHED", "reentry_authorized": False,
            "headline_en": None, "phase": None, "channels": {"liquidity": None, "market": None, "veto": None}}
    if not isinstance(recovery, Mapping) or recovery.get("present") is not True:
        return base
    channels = recovery.get("channels") if isinstance(recovery.get("channels"), Mapping) else {}
    normalized = {key: (channels.get(key) if type(channels.get(key)) is bool else None)
                  for key in ("liquidity", "market", "veto")}
    if recovery.get("suppressed") is True:
        state = "FAILED_REPAIR"
    elif recovery.get("turn_confirmed_full") is True:
        state = "CONFIRMED_REPAIR"
    elif recovery.get("turn_confirmed") is True:
        state = "EARLY_REPAIR"
    elif recovery.get("receding") is True or recovery.get("peaking") is True:
        state = "STABILIZING"
    else:
        state = "UNESTABLISHED"
    return {
        "state": state, "reentry_authorized": False,
        "headline_en": recovery.get("headline_en") if isinstance(recovery.get("headline_en"), str) else None,
        "phase": recovery.get("phase") if isinstance(recovery.get("phase"), str) else None,
        "channels": normalized,
    }


def _pathways(radar: Any, risk_envelope: Any, recovery_view: Mapping) -> tuple[list[dict], list[dict]]:
    scares = {}
    if isinstance(radar, Mapping) and isinstance(radar.get("scares"), list):
        for scare in radar["scares"]:
            if isinstance(scare, Mapping) and isinstance(scare.get("scare"), str):
                scares[scare["scare"]] = scare
    dominant = radar.get("dominant_scare") if isinstance(radar, Mapping) else None
    rate_observed = dominant in ("rates", "rate_shock") or any(
        key in str(dominant or "") for key in ("rate", "inflation"))
    leadership = next((s for s in _owner_sources(risk_envelope)
                       if s.get("source_id") == "leadership-crack-latest"), None)
    leadership_observed = isinstance(leadership, Mapping) and leadership.get("state") == "BROKEN"
    credit = scares.get("credit")
    credit_hot = isinstance(credit, Mapping) and credit.get("band") in ("caution", "elevated", "risk-off")
    deterioration = [
        {"key": "rates_pressure", "status": "observed" if rate_observed else "not_active",
         "label_en": "Rates / inflation pressure"},
        {"key": "leadership_damage", "status": "observed" if leadership_observed else "unavailable" if leadership is None else "not_active",
         "label_en": "Leadership damage"},
        {"key": "credit_broadening", "status": "observed" if credit_hot else "watch",
         "label_en": "Credit / bank stress broadens"},
    ]
    channels = recovery_view.get("channels") if isinstance(recovery_view.get("channels"), Mapping) else {}
    liquidity = channels.get("liquidity")
    market = channels.get("market")
    veto = channels.get("veto")
    full_state = recovery_view.get("state")
    resolution = [
        {"key": "liquidity_turn", "status": "observed" if liquidity is True else "missing" if liquidity is False else "unavailable",
         "label_en": "Market-local liquidity turns supportive"},
        {"key": "market_internals", "status": "observed" if market is True else "missing" if market is False else "unavailable",
         "label_en": "Breadth / internals confirm repair"},
        {"key": "volatility_veto", "status": "blocked" if veto is True else "observed" if veto is False else "unavailable",
         "label_en": "Volatility veto clears"},
        {"key": "full_repair", "status": "observed" if full_state == "CONFIRMED_REPAIR" else "near" if full_state == "EARLY_REPAIR" else "not_active",
         "label_en": "Recovery owner confirms durable repair"},
    ]
    return deterioration, resolution


def compose_capital_protection_briefing(
    warning: Mapping, *, radar: Any = None, regime: Any = None,
    market_state: Any = None, risk_envelope: Any = None,
    recovery: Any = None,
) -> dict:
    """Compose the answer-first Capital Protection Briefing display model.

    All financial state comes from the supplied canonical owners. This function
    only chooses deterministic presentation language and preserves a display-only
    authority ceiling. It never writes, ranks, sizes, gates, trades or upgrades
    a recovery into re-entry permission.
    """
    if not isinstance(warning, Mapping) or warning.get("schema") != SCHEMA:
        raise ValueError("warning must be mastermind.risk_warning/v1")
    market = _market_key(warning.get("market"))
    status = warning.get("status") if isinstance(warning.get("status"), str) else "unavailable"
    state = warning.get("state") if isinstance(warning.get("state"), str) and warning.get("state") in _STATE_ATTENTION else None
    attention = warning.get("attention") if isinstance(warning.get("attention"), str) else "unavailable"
    if status == "current" and state is not None:
        label_en, label_zh = _BRIEF_STANCE[state]
        stance_note = ("State-derived display guidance only. No exact exposure target is validated; "
                       "this is not an automatic all-cash instruction or execution command.")
    elif status == "unverified" and attention in ("high", "critical"):
        label_en, label_zh = "Keep defensive posture pending verification", "核实前维持防御"
        stance_note = ("The prior severe warning has not been cleared by current evidence. "
                       "No exact exposure target is validated; this is not an automatic all-cash instruction.")
    else:
        label_en, label_zh = "Verification unavailable", "当前状态待核实"
        stance_note = "Missing evidence is not an all-clear and carries no execution authority."
    severity = {
        "state": state, "attention": attention,
        "ungated_state": warning.get("state_ungated") if isinstance(warning.get("state_ungated"), str) else None,
        "confirmation": warning.get("confirmation") if isinstance(warning.get("confirmation"), str) else "unknown",
        "intensity": _safe_num(warning.get("score"), lower=0, upper=100),
    }
    material = attention in ("warning", "high", "critical")
    rec_view = _recovery_view(recovery)
    deterioration, resolution = _pathways(radar, risk_envelope, rec_view)
    drivers = _briefing_drivers(radar, risk_envelope)
    primary = drivers[0]["label_en"] if drivers else (warning.get("driver_en") or "Current risk")
    summary_headline = {
        "calm": "No active warning", "watch": "Early risk watch",
        "caution": "Risk is building", "elevated": "High market risk",
        "risk-off": "Critical risk-off conditions",
    }.get(state, "Current risk cannot be verified" if status != "unverified" else "Last verified severe risk remains unresolved")
    why = f"{primary} is the leading risk read."
    if any(d.get("key") == "leadership-crack-latest" and d.get("state") == "BROKEN" for d in drivers):
        why += " Leadership damage remains broken."
    if warning.get("confirmation") == "pending":
        why += " Confirmation is incomplete."
    freshness = {
        "status": status,
        "source_session": _session(warning.get("source_session")),
        "expected_session": _session(warning.get("expected_session")),
        "artifact_freshness": warning.get("artifact_freshness") if isinstance(warning.get("artifact_freshness"), str) else "unavailable",
        "underlying_input_status": warning.get("underlying_input_status") if isinstance(warning.get("underlying_input_status"), str) else "unknown",
    }
    return {
        "schema": BRIEFING_SCHEMA, "market": market,
        "severity": severity,
        "stance": {
            "label_en": label_en, "label_zh": label_zh,
            "authority": "display_guidance", "exact_exposure_target": None,
            "authority_note_en": stance_note,
        },
        "summary": {"headline_en": summary_headline, "why_now_en": why},
        "downside": _downside_view(warning, radar),
        "backdrop": _backdrop_view(regime, market_state, material),
        "drivers": drivers,
        "deterioration_path": deterioration,
        "resolution_path": resolution,
        "recovery": rec_view,
        "freshness": freshness,
        "changed_since_prior": [],
        "authority": _authority(),
    }
