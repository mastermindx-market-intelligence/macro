"""Read-only Bonds projection of the existing CCW dislocation artifact.

No collection, classifier fitting, alert activation or source mutation on render.
The reader recomputes freshness against the render cutoff instead of trusting a
formerly fresh status saved in an old file.
"""
from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any

from engine.credit_dislocation import AUTHORITY, MAX_AGE_SESSIONS, SCHEMA
from engine.corp_credit import (
    CMT_TOLERANCE, INSTRUMENT_HISTORY_BASIS, INSTRUMENT_HISTORY_MAX_OBSERVATIONS,
    INSTRUMENT_HISTORY_POPULATION, INSTRUMENT_HISTORY_SCHEMA,
)
from lib.nyse_calendar import sessions_between

MAX_SNAPSHOT_BYTES = 4_000_000
STATE_COPY = {
    "credit_widening_equity_steadier": ("Credit widening; equity steadier", "信用利差扩大，股价相对平稳", "question"),
    "joint_deterioration": ("Credit and equity weakening", "信用与股价同时走弱", "question"),
    "credit_improving_equity_weaker": ("Credit improving; equity weaker", "信用利差收窄，股价仍弱", "neutral"),
    "joint_improvement": ("Credit and equity improving", "信用与股价同时改善", "neutral"),
    "relative_gap_only": ("Relative gap; direction unconfirmed", "存在相对差异，绝对方向未确认", "neutral"),
    "no_large_relative_change": ("No large relative move", "相对变化未达研究阈值", "neutral"),
    "insufficient_evidence": ("Comparison incomplete", "比较数据不足", "neutral"),
    "historical_only": ("Historical observation", "历史观察", "neutral"),
}
THEME_COPY = {
    "hyperscaler_credit": ("Hyperscalers", "大型云平台"),
    "neocloud_credit": ("AI compute", "AI算力"),
    "memory_credit": ("Memory & storage", "存储"),
    "ai_power_credit": ("AI power", "AI电力"),
    "dc_reit_credit": ("Data centers", "数据中心"),
    "ai_hardware_credit": ("AI hardware", "AI硬件"),
    "telecom_legacy": ("Telecom controls", "电信对照组"),
}
REASON_COPY = {
    "history_unavailable": ("Retained instrument history unavailable", "缺少债券历史观察"),
    "history_invalid": ("Instrument history is invalid", "债券历史记录无效"),
    "history_binding_unqualified": ("History does not have a matching validation binding", "历史记录缺少匹配的验证绑定"),
    "history_identifier_unresolved": ("Instrument identity unresolved", "债券身份待核验"),
    "history_terms_conflict": ("Observed bond terms conflict", "债券条款观察存在冲突"),
    "history_terms_changed": ("Coupon or maturity changed within the window", "窗口内票息或到期日发生变化"),
    "history_terms_missing": ("Coupon or maturity observations missing", "缺少票息或到期日观察"),
    "history_currency_conflict": ("Source currencies conflict", "来源币种存在冲突"),
    "history_currency_unknown": ("Source currency unavailable", "来源币种缺失"),
    "history_currency_unsupported": ("Currency is unsupported for this Treasury comparison", "该币种不支持此美国国债比较"),
    "pricing_unqualified": ("Pricing validation is missing, failed, or bound to different data", "\u5b9a\u4ef7\u9a8c\u8bc1\u7f3a\u5931\u3001\u672a\u901a\u8fc7\u6216\u4e0e\u6570\u636e\u4e0d\u5339\u914d"),
    "equity_unavailable": ("Equity observations unavailable", "缺少股价观察"),
    "missing_equity_sessions": ("Equity sessions missing", "股价交易日数据缺失"),
    "conflicting_equity_dates": ("Conflicting equity observations", "股价日期存在冲突"),
    "corporate_action_or_extreme_move_needs_review": ("Equity adjustment needs review", "股价调整或极端波动待核验"),
    "missing_session_or_matched_change": ("Credit window has missing observations", "信用观察窗口存在缺口"),
    "no_matched_instruments": ("No matched bonds for this window", "窗口内缺少可匹配债券"),
    "insufficient_history": ("History still accumulating", "历史数据积累中"),
    "issuer_not_observed_at_common_cutoff": ("Issuer is missing at the common cutoff", "共同截止日缺少该发行人数据"),
    "insufficient_coarse_peers_or_issuer_history": ("Too few comparable issuers or observations", "可比发行人或观察值不足"),
}


def _finite(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def _metric(value: Any, suffix: str, *, signed: bool = True, decimals: int = 1) -> str:
    n = _finite(value)
    if n is None:
        return "—"
    if abs(n) < 0.5 * 10 ** -decimals:
        n = 0.0
    pattern = f"{{:{'+' if signed else ''}.{decimals}f}}"
    return pattern.format(n) + suffix


def _empty(reason: str) -> dict:
    return {"available": False, "status": "unavailable", "reason": reason,
            "title_en": "Credit comparison unavailable", "title_zh": "信用比较暂不可用",
            "subtitle_en": "Missing observations are not evidence of low risk.",
            "subtitle_zh": "缺少观察数据并不代表风险较低。",
            "source_as_of": None, "age_sessions": None, "issuers": [],
            "paired_count": 0, "bond_count": 0, "authority": dict(AUTHORITY)}



def _instrument_history_view(bond: dict, pricing: dict, pricing_ok: bool, source_day: date) -> dict:
    history = bond.get("instrument_history")
    present = isinstance(history, dict)
    history = history if present else {}
    count = history.get("observations")
    valid = bool(
        present and history.get("schema") == INSTRUMENT_HISTORY_SCHEMA
        and history.get("population") == INSTRUMENT_HISTORY_POPULATION
        and history.get("valuation_basis") == INSTRUMENT_HISTORY_BASIS
        and history.get("historical_publication_qualified") is False
        and history.get("independent_historical_pricing_qualified") is False
        and type(count) is int and 0 <= count <= INSTRUMENT_HISTORY_MAX_OBSERVATIONS
        and history.get("status") in {"available", "partial", "unavailable"}
    )
    if valid and count:
        try:
            first_seen = date.fromisoformat(history["first_seen"])
            first = date.fromisoformat(history["observed_from"])
            last = date.fromisoformat(history["observed_through"])
            valid = first_seen <= first <= last == source_day
            if history.get("cmt_as_of") is not None:
                curve_day = date.fromisoformat(history["cmt_as_of"])
                valid = valid and 0 <= (source_day - curve_day).days <= CMT_TOLERANCE.days
        except (KeyError, ValueError, TypeError):
            valid = False
    short = history.get("change_5") if isinstance(history.get("change_5"), dict) else {}
    long = history.get("change_21") if isinstance(history.get("change_21"), dict) else {}
    if valid:
        for horizon, window in [(5, short), (21, long)]:
            if _finite(window.get("value_bp")) is not None:
                valid = bool(valid and count >= horizon + 1
                             and history.get("currency") == "USD" and history.get("cmt_as_of"))
    qualified = valid and pricing_ok and pricing.get("instrument_history_verified") is True
    reason = history.get("reason") or short.get("reason") or long.get("reason")
    if not present:
        reason = "history_unavailable"
    elif not valid:
        reason = "history_invalid"
    elif not pricing_ok and count:
        reason = "pricing_unqualified"
    elif not qualified and count:
        reason = "history_binding_unqualified"
    en, zh = REASON_COPY.get(reason, ("", "") if not reason else REASON_COPY["history_unavailable"])
    if valid and count:
        coverage_en = f'{count} observed dates · {history["observed_from"]}–{history["observed_through"]}'
        coverage_zh = f'{count}个观察日 · {history["observed_from"]}–{history["observed_through"]}'
    else:
        coverage_en, coverage_zh = REASON_COPY["history_unavailable"]
    currency = history.get("currency")
    curve_day = history.get("cmt_as_of")
    return {
        "history5": _metric(short.get("value_bp") if qualified else None, " bp"),
        "history21": _metric(long.get("value_bp") if qualified else None, " bp"),
        "history_coverage_en": coverage_en, "history_coverage_zh": coverage_zh,
        "history_reason_en": en, "history_reason_zh": zh,
        "history_currency": currency if valid and isinstance(currency, str) and len(currency) <= 16 else "—",
        "history_curve_as_of": curve_day if valid and isinstance(curve_day, str) and len(curve_day) == 10 else "—",
    }


def build_view(snapshot: dict | None, *, as_of: date) -> dict:
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SCHEMA:
        return _empty("source_unavailable_or_incompatible")
    authority = snapshot.get("authority")
    if (not isinstance(authority, dict) or set(authority) != set(AUTHORITY)
            or any(value is not False for value in authority.values())
            or snapshot.get("display_only") is not True):
        return _empty("incompatible_authority_contract")
    if snapshot.get("status") not in {"partial", "stale"}:
        return _empty("no_usable_source_observations")
    try:
        source_day = date.fromisoformat(snapshot["source_as_of"])
        generation_day = date.fromisoformat(snapshot["as_of"])
    except (KeyError, ValueError, TypeError):
        return _empty("missing_source_date")
    if source_day > generation_day or generation_day > as_of:
        return _empty("future_source_or_generation")
    try:
        age = len([d for d in sessions_between(source_day, as_of) if d > source_day])
    except (ValueError, TypeError, OverflowError):
        return _empty("calendar_unavailable")
    stale = age > MAX_AGE_SESSIONS or snapshot.get("status") == "stale"
    raw_rows = snapshot.get("issuers")
    if not isinstance(raw_rows, list) or len(raw_rows) > 200:
        return _empty("invalid_issuer_population")
    result = _empty("")
    result.update(available=True, status="stale" if stale else "partial",
                  source_as_of=source_day.isoformat(), age_sessions=age,
                  observation_id=snapshot.get("observation_id"),
                  title_en="Historical credit comparison" if stale else "Stocks and their bonds",
                  title_zh="历史信用比较" if stale else "股票与其债券",
                  subtitle_en=("These dated observations cannot establish today's credit condition." if stale
                               else "Compare the move. Inspect the borrower. Test the countercase."),
                  subtitle_zh=("这些历史观察不能证明当前信用状况。" if stale
                               else "比较变化，核查借款人，并检验相反解释。"))
    pricing = snapshot.get("pricing_validation")
    pricing = pricing if isinstance(pricing, dict) else {}
    pricing_ok = (pricing.get("status") == "passed"
                  and pricing.get("source_binding_verified") is True
                  and pricing.get("observation_as_of") == source_day.isoformat())
    result.update(pricing_qualified=pricing_ok, pricing_validation=pricing,
                  pricing_en=("Pricing checked against same-day LQD holdings; source hashes verified."
                              if pricing_ok else "Pricing unqualified: derived credit values are withheld."),
                  pricing_zh=("\u5b9a\u4ef7\u5df2\u4e0e\u540c\u65e5LQD\u6301\u4ed3\u6838\u9a8c\uff0c\u6570\u636e\u54c8\u5e0c\u5339\u914d\u3002"
                              if pricing_ok else "\u5b9a\u4ef7\u672a\u901a\u8fc7\u6838\u9a8c\uff1a\u6682\u4e0d\u5c55\u793a\u884d\u751f\u4fe1\u7528\u6570\u503c\u3002"))
    seen = set()
    for row in raw_rows:
        if not isinstance(row, dict) or not isinstance(row.get("issuer"), str) or row["issuer"] in seen:
            return _empty("invalid_or_duplicate_issuer")
        seen.add(row["issuer"])
        if not pricing_ok:
            row = dict(row, state="insufficient_evidence", reason="pricing_unqualified",
                       change_5={}, change_21={}, relative_change_5_bp=None,
                       peer_change_5_bp=None, acceleration_bp_per_session=None)
        change = row.get("change_5") if isinstance(row.get("change_5"), dict) else {}
        equity = row.get("equity_5") if isinstance(row.get("equity_5"), dict) else {}
        long = row.get("change_21") if isinstance(row.get("change_21"), dict) else {}
        state = "historical_only" if stale else row.get("state", "insufficient_evidence")
        if not stale and any(_finite(value) is None for value in
                             (change.get("value_bp"), row.get("relative_change_5_bp"), equity.get("value_pct"))):
            state = "insufficient_evidence"
        en, zh, tone = STATE_COPY.get(state, STATE_COPY["insufficient_evidence"])
        reasons = [row.get("reason"), change.get("reason"), equity.get("reason"), row.get("peer_reason")]
        notes = [REASON_COPY[r] for r in dict.fromkeys(r for r in reasons if isinstance(r, str)) if r in REASON_COPY]
        for metric, label_en, label_zh in [(change, "Missing credit dates", "\u7f3a\u5c11\u4fe1\u7528\u65e5\u671f"),
                                            (equity, "Missing equity dates", "\u7f3a\u5c11\u80a1\u4ef7\u65e5\u671f")]:
            missing = metric.get("missing_sessions")
            if isinstance(missing, list) and missing:
                dates = ", ".join(str(day)[:10] for day in missing[:22])
                notes.append((f"{label_en}: {dates}", f"{label_zh}: {dates}"))
        theme_en, theme_zh = THEME_COPY.get(row.get("theme"), ("Other tracked issuers", "其他跟踪发行人"))
        raw_bonds = row.get("bonds") or []
        if not isinstance(raw_bonds, list) or len(raw_bonds) > 1000:
            return _empty("invalid_bond_population")
        securities = []
        for bond in raw_bonds:
            if not isinstance(bond, dict) or not isinstance(bond.get("identifier"), dict):
                return _empty("invalid_bond_record")
            native = bond["identifier"]
            securities.append({
                "name": str(bond.get("name") or "Unnamed security"),
                "identifier": str(native.get("value") or "—"),
                "identifier_type": str(native.get("kind") or "unknown").upper(),
                "identifier_valid": native.get("checksum_valid") is True,
                "maturity": str(bond.get("maturity") or "—")[:10],
                "coupon": _metric(bond.get("coupon_pct"), "%", signed=False, decimals=2),
                "price": _metric(bond.get("price_clean") if pricing_ok else None, "", signed=False, decimals=2),
                "spread": _metric(bond.get("g_spread_bp") if pricing_ok else None, " bp", signed=False),
                "call_review": bond.get("near_par_call_flag") is not False,
                **_instrument_history_view(bond, pricing, pricing_ok, source_day),
            })
        relative = _finite(row.get("relative_change_5_bp"))
        paired = relative is not None and _finite(equity.get("value_pct")) is not None
        peers = row.get("peer_issuers") if isinstance(row.get("peer_issuers"), list) else []
        result["issuers"].append({
            "issuer": row["issuer"], "ticker": str(row.get("equity_ticker") or ""),
            "theme_en": theme_en, "theme_zh": theme_zh, "theme": row.get("theme") or "other",
            "tier": row.get("tier") if row.get("tier") in {"IG", "HY"} else "—",
            "state": state, "state_en": en, "state_zh": zh, "tone": tone,
            "change": _metric(change.get("value_bp"), " bp"),
            "relative": _metric(relative, " bp"), "equity": _metric(equity.get("value_pct"), "%"),
            "change21": _metric(long.get("value_bp"), " bp"),
            "acceleration": _metric(row.get("acceleration_bp_per_session"), " bp/session"),
            "credit_direction": "wider" if (_finite(change.get("value_bp")) or 0) > 0 else "other",
            "peer_count": len(peers), "peers": ", ".join(str(p) for p in peers),
            "peer_change": _metric(row.get("peer_change_5_bp"), " bp"),
            "bonds": securities, "notes": notes, "paired": paired,
            "search_text": " ".join([row["issuer"], str(row.get("equity_ticker") or ""), theme_en, theme_zh]
                                      + [b["identifier"] for b in securities]).lower(),
        })
    result["paired_count"] = sum(r["paired"] for r in result["issuers"])
    result["bond_count"] = sum(len(r["bonds"]) for r in result["issuers"])
    if not stale and result["paired_count"] == 0:
        result["subtitle_en"] = "No eligible five-session comparisons yet. Missing observations are not evidence of low risk."
        result["subtitle_zh"] = "\u6682\u65e0\u5408\u683c\u7684\u4e94\u4e2a\u4ea4\u6613\u65e5\u914d\u5bf9\u6bd4\u8f83\u3002\u7f3a\u5c11\u89c2\u5bdf\u6570\u636e\u5e76\u4e0d\u4ee3\u8868\u98ce\u9669\u8f83\u4f4e\u3002"
    return result


def load_view(root: Path, *, as_of: date) -> dict:
    path = root / "corp_bonds/credit_dislocation.json"
    try:
        if path.stat().st_size > MAX_SNAPSHOT_BYTES:
            return _empty("snapshot_exceeds_size_limit")
        def reject_constant(value):
            raise ValueError(f"invalid JSON constant: {value}")
        snapshot = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)
        return build_view(snapshot, as_of=as_of)
    except (OSError, ValueError, TypeError):
        return _empty("source_unreadable")


def compact_context(view: dict) -> dict:
    """Small attributed context for bond_health; no implied new Radar authority."""
    available = view.get("available") is True
    return {
        "schema": "corp_credit.dislocation_context.v1",
        "source_schema": SCHEMA,
        "source_as_of": view.get("source_as_of"),
        "status": view.get("status", "unavailable"),
        "authority": dict(AUTHORITY),
        "display_only": True,
        "prediction_validated": False,
        "cds_available": False,
        "pricing_qualified": view.get("pricing_qualified") is True,
        "pricing_validation": view.get("pricing_validation", {}),
        "paired_issuer_count": view.get("paired_count") if available else None,
        "mapped_bond_count": view.get("bond_count") if available else None,
        "observation_id": view.get("observation_id"),
        "href": "bonds.html#credit-dislocation",
        "issuer_observations": [{"issuer": row["issuer"], "state": row["state"],
                                 "paired": row["paired"]} for row in view.get("issuers", [])],
        "limitations": ["economic_parent_mapping", "coarse_peers", "holdings_not_total_debt",
                        "historical_publication_unqualified", "not_an_equity_loss_forecast"],
    }
