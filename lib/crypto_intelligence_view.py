"""Display-only R4 projections of existing crypto contracts.

No strategy, portfolio, probability, source capture or alert-delivery authority.
The dated close-range conditions are research context, never model invalidations.
"""
from __future__ import annotations

from datetime import date, timedelta
import math
import re
from typing import Any


def finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def iso_day(value: Any) -> date | None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def validated(source: Any, schema: str) -> dict:
    return source if isinstance(source, dict) and source.get("schema") == schema else {}


def price_history(chart: dict, as_of: str) -> dict:
    """Return only the latest contiguous daily segment; never bridge missing bars."""
    cutoff = iso_day(as_of)
    dates, prices = chart.get("dates"), chart.get("price")
    empty = {"dates": [], "vals": [], "state": "unavailable", "gaps": False}
    if chart.get("valid") is not True or not cutoff:
        return empty
    if not isinstance(dates, list) or not isinstance(prices, list) or len(dates) != len(prices):
        return empty
    previous = None
    segment: list[tuple[str, float]] = []
    gaps = False
    for stamp, raw in zip(dates, prices):
        day, value = iso_day(stamp), finite(raw)
        if not day or day > cutoff or (previous is not None and day <= previous):
            return empty
        if previous is not None and (day - previous).days != 1:
            segment = []
            gaps = True
        previous = day
        if value is None or value <= 0:
            segment = []
            gaps = True
            continue
        segment.append((str(day), value))
    if not segment:
        return {**empty, "gaps": gaps}
    if segment[-1][0] != str(cutoff):
        return {**empty, "state": "stale", "gaps": gaps, "last_observed": segment[-1][0]}
    return {
        "dates": [item[0] for item in segment],
        "vals": [item[1] for item in segment],
        "state": "ready" if len(segment) >= 4 else "insufficient",
        "gaps": gaps,
    }


def prior_close_range(history: dict, days: int) -> dict:
    values = history.get("vals") or []
    dates = history.get("dates") or []
    if len(values) < days + 1 or len(values) != len(dates):
        return {"available": False, "lookback_days": days, "basis": "prior_daily_closes", "high": None, "low": None, "start": None, "end": None, "current_date": None, "current": None, "position": None}
    prior = values[-days - 1:-1]
    return {
        "available": True, "lookback_days": days, "basis": "prior_daily_closes",
        "start": dates[-days - 1], "end": dates[-2], "current_date": dates[-1],
        "high": max(prior), "low": min(prior), "current": values[-1],
        "position": "above" if values[-1] > max(prior) else "below" if values[-1] < min(prior) else "inside",
    }


FAMILY_NAMES = {
    "trend_momentum": ("Price structure", "价格结构"),
    "liquidity_flows": ("Demand & capital", "需求与资金"),
    "leverage_derivatives": ("Leverage", "杠杆"),
    "network_miners": ("Holders & network", "持有者与网络"),
    "macro_backdrop": ("Macro conditions", "宏观环境"),
    "participation": ("Participation", "市场参与"),
}

FAMILY_NOTES = {
    "trend_momentum": (
        "Momentum and structure are related readings. A strong trend does not confirm new spot demand.",
        "动量与结构并非独立证据。趋势走强，不等于新增现货需求已获确认。"),
    "liquidity_flows": (
        "ETF subscriptions, stablecoin issuance and spot participation measure different things. Missing updates cannot confirm demand.",
        "ETF申购、稳定币发行与现货参与各有含义。缺少更新时，不能确认需求增强。"),
    "leverage_derivatives": (
        "The pressure reading is observed context. Missing funding is not zero funding or proof of low crowding.",
        "压力读数仅反映已观测情况。缺少资金费率，不代表费率为零或拥挤风险低。"),
    "network_miners": (
        "Network activity, holders and miner economics are slower context; they do not time the next price move.",
        "网络活动、持有者与矿工经济属于较慢背景，不能据此确定下一次价格变动。"),
    "macro_backdrop": (
        "Rates, the dollar and liquidity can affect risk appetite. Their influence changes with the regime and forecast horizon.",
        "利率、美元与流动性会影响风险偏好，但作用随市场阶段和观察周期变化。"),
    "participation": (
        "Broad market participation is withheld until the existing history and eligibility floor is met.",
        "达到既有历史与样本门槛后，才展示全市场参与度判断。"),
}


def families(cockpit: dict, class_state: dict) -> list[dict]:
    axes = {a.get("id"): a for a in cockpit.get("axes", []) if isinstance(a, dict)}
    out = []
    for key, labels in FAMILY_NAMES.items():
        axis = axes.get(key, {})
        primary = axis.get("primary") or {}
        state = primary.get("state_en") or "Unavailable"
        state_zh = primary.get("state_zh") or "暂无"
        source_date = primary.get("as_of") if iso_day(primary.get("as_of")) else None
        non_observed = state.lower() in {"unavailable", "data pending", "insufficient history", "not confirmed", "not yet confirmed"}
        quality = "missing" if non_observed else ("observed" if source_date else "snapshot_only")
        members = axis.get("receipt_members") or []
        if key == "liquidity_flows":
            flow_kinds = class_state.get("flow_kinds") or {}
            if not class_state:
                state, state_zh, quality = "Freshness unknown", "数据时效未知", "missing"
            if any((flow_kinds.get(k) or {}).get("observation") == "stale" for k in ("etf", "stablecoins")):
                state, state_zh, quality = "Updates pending", "等待数据更新", "stale"
                source_date = None
        if key == "participation":
            breadth = (class_state.get("universe_coverage") or {}).get("breadth") or {}
            ready = breadth.get("available") is True and finite(breadth.get("value")) is not None
            state = breadth.get("state") if ready else "Not yet confirmed"
            state_zh = breadth.get("state_zh") if ready else "尚未确认"
            quality = "observed" if ready else "insufficient"
            source_date = breadth.get("as_of") if iso_day(breadth.get("as_of")) else None
            primary = {"source": "crypto.class_state/v1.universe_coverage.breadth"}
            eligible, required = finite(breadth.get("eligible")), finite(breadth.get("required"))
            members = [{
                "label_en": "Eligible histories", "label_zh": "合格历史样本",
                "state_en": f"{eligible:g} of {required:g} required" if eligible is not None and required is not None else "Coverage not supplied",
                "state_zh": f"现有{eligible:g}个，要求{required:g}个" if eligible is not None and required is not None else "未提供覆盖数据",
            }]
        out.append({
            "id": key, "label_en": labels[0], "label_zh": labels[1],
            "state_en": state, "state_zh": state_zh, "quality": quality,
            "tone": primary.get("tone", "neutral") if quality == "observed" else "neutral",
            "as_of": source_date, "snapshot_as_of": class_state.get("as_of") if key == "participation" else cockpit.get("as_of"),
            "source": primary.get("source") or "Not supplied",
            "note_en": FAMILY_NOTES[key][0], "note_zh": FAMILY_NOTES[key][1],
            "members": members,
        })
    return out


def scenario_set(history: dict, as_of: str, horizon: int) -> list[dict]:
    lookback = 20 if horizon == 7 else 60
    levels = prior_close_range(history, lookback)
    day = iso_day(as_of)
    if not day or not levels.get("available"):
        return []
    expires = str(day + timedelta(days=horizon))
    high = "$" + format(levels["high"], ",.0f") if levels.get("available") else "the prior range high"
    low = "$" + format(levels["low"], ",.0f") if levels.get("available") else "the prior range low"
    high_zh = high if levels.get("available") else "前期区间高位"
    low_zh = low if levels.get("available") else "前期区间低位"
    definitions = [
        ("continuation", "Breaks higher", "向上突破",
         f"A daily close above {high}, followed by stronger spot demand.",
         f"日收盘突破{high_zh}，随后现货需求增强。",
         "Price holds above the old range as participation broadens.",
         "价格守住原区间上方，市场参与扩大。",
         "A return inside the range weakens the breakout; losing its low invalidates this path.",
         "重回区间会削弱突破；跌破区间低位则推翻此路径。",
         "Price condition", "价格条件", "This path needs current demand evidence.", "此路径需要最新需求证据。"),
        ("range", "Range persists", "区间延续",
         f"Daily closes remain between {low} and {high}.",
         f"日收盘维持在{low_zh}至{high_zh}之间。",
         "Mixed demand keeps the market inside its recent range.",
         "需求分化，价格维持近期区间。",
         "A sustained range break with demand or selling pressure ends this path.",
         "持续突破区间，并伴随需求或卖压变化，结束此路径。",
         "Mixed evidence", "证据分化", "A sudden catalyst can end the range.", "突发催化可能打破区间。"),
        ("failure", "Breaks lower", "向下突破",
         f"A daily close below {low}, followed by weaker demand.",
         f"日收盘跌破{low_zh}，随后需求转弱。",
         "Lost price structure and weaker demand reinforce selling pressure.",
         "价格结构失守，需求转弱，加大卖压。",
         "Reclaiming the range with improving demand weakens this downside path.",
         "重回区间且需求改善，会削弱下行路径。",
         "Price condition", "价格条件", "Demand and leverage evidence must be checked before inferring forced selling.", "推断被动卖出前，需检查需求与杠杆证据。"),
    ]
    return [{
        "id": key, "title_en": en, "title_zh": zh,
        "asset": "BTC", "horizon_days": horizon, "as_of": as_of, "expires": expires,
        "state": "conditional" if levels.get("available") else "insufficient",
        "condition_en": ce, "condition_zh": cz, "sequence_en": se, "sequence_zh": sz,
        "invalidation_en": ie, "invalidation_zh": iz,
        "support_en": pe, "support_zh": pz, "counter_en": ne, "counter_zh": nz,
        "levels": levels, "probability": None,
        "evidence_strength_en": "Evidence incomplete", "evidence_strength_zh": "证据不完整",
        "revision": f"r4-display:{as_of}:{horizon}:{key}",
        "authority": "conditional_research_only",
    } for key, en, zh, ce, cz, se, sz, ie, iz, pe, pz, ne, nz in definitions]


def build_view(cockpit: dict, class_state: dict, asset_states: dict, chart: dict) -> dict:
    raw_contracts = {"cockpit": (cockpit, "crypto.cockpit/v1"), "class_state": (class_state, "crypto.class_state/v1"), "asset_states": (asset_states, "crypto.asset_states/v1"), "chart": (chart, "mastermind.vector_risk_strategy.v2")}
    contract_status = {key: ("accepted" if isinstance(value, dict) and value.get("schema") == schema else "missing_or_schema_mismatch") for key, (value, schema) in raw_contracts.items()}
    cockpit = validated(cockpit, "crypto.cockpit/v1")
    class_state = validated(class_state, "crypto.class_state/v1")
    asset_states = validated(asset_states, "crypto.asset_states/v1")
    chart = validated(chart, "mastermind.vector_risk_strategy.v2")
    as_of = cockpit.get("as_of") if iso_day(cockpit.get("as_of")) else None
    history = price_history(chart, as_of or "")
    hero = cockpit.get("hero") or {}
    price = finite(hero.get("price"))
    price_conflict = bool(history["vals"] and (price is None or abs(history["vals"][-1] - price) > max(0.02, price * 0.00001)))
    if hero.get("asset") != "BTC-USD":
        history = {"dates": [], "vals": [], "state": "asset_unverified", "gaps": False}
    display_price = history["vals"][-1] if history["vals"] else None
    change = (100 * (history["vals"][-1] / history["vals"][-2] - 1)) if len(history["vals"]) >= 2 else None
    decision = cockpit.get("decision") or {}
    exposure = finite(decision.get("final_exposure_pct"))
    model_ok = (
        decision.get("schema") == "btc.decision/v1"
        and decision.get("status") == "ok" and decision.get("integrity_ok") is True
        and exposure is not None and 0 <= exposure <= 100
        and iso_day(decision.get("as_of")) is not None
        and decision.get("authority_source") == "btc.decision/v1.final.exposure_pct"
    )
    assets = []
    for symbol, item in (asset_states.get("assets") or {}).items():
        if not isinstance(item, dict):
            continue
        coverage = item.get("coverage") or {}
        covered = coverage.get("available") is True and iso_day(item.get("as_of")) is not None
        if covered and as_of and item["as_of"] > as_of:
            covered = False
        assets.append({
            "symbol": symbol, "name": {"ETH": "Ethereum", "SOL": "Solana"}.get(symbol, symbol),
            "as_of": item.get("as_of"), "price": finite(item.get("price")),
            "change_30d_pct": finite(item.get("change_30d_pct")) if covered else None,
            "relative_90d_pct": finite((item.get("relative") or {}).get("change_90d_pct")) if covered else None,
            "trend_en": ((item.get("trend") or {}).get("state") or "Unavailable") if covered else "Unavailable",
            "trend_zh": ((item.get("trend") or {}).get("state_zh") or "暂无") if covered else "暂无",
            "risk_en": ((item.get("risk") or {}).get("state") or "Unavailable") if covered else "Unavailable",
            "risk_zh": ((item.get("risk") or {}).get("state_zh") or "暂无") if covered else "暂无",
            "relative_en": ((item.get("relative") or {}).get("state") or "Unavailable") if covered else "Unavailable",
            "relative_zh": ((item.get("relative") or {}).get("state_zh") or "暂无") if covered else "暂无",
            "coverage_en": coverage.get("note_en") or "Price history unavailable.",
            "coverage_zh": coverage.get("note_zh") or "暂无价格历史。",
            "available": covered,
        })
    market = class_state.get("market") or {}
    market_copy = {
        "Rising": ("Recovery needs breadth", "修复有待扩散", "The latest snapshot rose; broad participation remains unconfirmed.", "最新快照显示市值回升，参与是否扩大仍待确认。"),
        "Falling": ("Market value is falling", "市场总值回落", "The latest snapshot fell; watch demand and price structure.", "最新快照显示市值回落，关注需求与价格结构。"),
        "Steady": ("Market value is steady", "市场总值平稳", "The latest snapshot is steady; inspect demand for the next change.", "最新快照显示市值平稳，关注需求的下一步变化。"),
    }
    breadth = (class_state.get("universe_coverage") or {}).get("breadth") or {}
    broad_ready = breadth.get("available") is True and finite(breadth.get("value")) is not None
    copy = market_copy.get(market.get("total_state"), ("Market evidence incomplete", "市场证据不完整", "A broad market read is unavailable from this snapshot.", "该快照暂不能提供全市场判断。"))
    if market.get("total_state") == "Rising" and broad_ready:
        copy = ("Market value is rising", "市场总值回升", "The latest snapshot rose; compare price with observed participation.", "最新快照显示市值回升，对照价格与参与度。")
    levels = prior_close_range(history, 20)
    return {
        "schema": "crypto.intelligence_view/v1", "display_only": True, "contracts": contract_status,
        "as_of": as_of, "market_as_of": class_state.get("as_of"),
        "price": display_price, "snapshot_price": price,
        "change_24h_pct": change,
        "headline_en": copy[0], "headline_zh": copy[1], "summary_en": copy[2], "summary_zh": copy[3],
        "btc_headline_en": "Watch the range" if levels["available"] else "Price evidence incomplete",
        "btc_headline_zh": "关注区间突破" if levels["available"] else "价格证据不完整",
        "families": families(cockpit, class_state),
        "history": history, "levels": levels,
        "scenarios": {str(h): scenario_set(history, as_of or "", h) for h in (7, 30)},
        "assets": assets, "asset_as_of": asset_states.get("as_of"),
        "model": {
            "available": model_ok, "exposure_pct": exposure if model_ok else None,
            "as_of": decision.get("as_of"), "source": decision.get("authority_source"),
            "scope": "Bitcoin model", "schema": "btc.decision/v1", "matches_cockpit_date": model_ok and decision.get("as_of") == as_of,
        },
        "limitations": {
            "price_basis_divergence": price_conflict,
            "history_state": history["state"],
            "broad_participation": not broad_ready,
            "forecast_probabilities": "not_qualified", "historical_evaluation": "not_qualified",
            "remote_alert_delivery": "not_connected",
            "source_dates_differ": len({x for x in (as_of, class_state.get("as_of"), asset_states.get("as_of")) if x}) > 1,
        },
    }
