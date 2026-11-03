"""Commodity Decision Workspace: a pure, display-only consumer of existing owners.

No collectors, forecasts, scores, correlation estimation, alert writes, or clock reads.
Snapshot dates are publisher labels, NOT proof of point-in-time availability.
The builder supplies accepted artifacts; newer/undated context is explicitly fenced.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import math
from numbers import Integral, Real
from typing import Any

SCHEMA = "mmx.commodities.workspace.v1"
CONDITION_SCHEMA = "mmx.commodities.research_condition.v1"
PROJECTION_REVISION = 6
HYPOTHESIS_REVISION = "commodity-mechanisms-20261018-r3"

LABELS = {
    "oil": ("WTI crude", "WTI原油"), "natgas": ("Natural gas", "天然气"),
    "gasoline": ("Gasoline", "汽油"), "heating_oil": ("Heating oil", "取暖油"),
    "gold": ("Gold", "黄金"), "silver": ("Silver", "白银"),
    "platinum": ("Platinum", "铂金"), "palladium": ("Palladium", "钯金"),
    "copper": ("Copper", "铜"), "corn": ("Corn", "玉米"),
    "wheat": ("Wheat", "小麦"), "soybeans": ("Soybeans", "大豆"),
    "coffee": ("Coffee", "咖啡"), "cocoa": ("Cocoa", "可可"),
    "sugar": ("Sugar", "糖"), "cotton": ("Cotton", "棉花"),
    "live_cattle": ("Live cattle", "活牛"),
}
FAMILIES = {
    "energy": ("Energy", "能源"), "precious": ("Precious metals", "贵金属"),
    "industrial": ("Industrial metals", "工业金属"), "grain": ("Grains", "谷物"),
    "soft": ("Soft commodities", "软商品"), "livestock": ("Livestock", "畜牧"),
}
FAMILY_ORDER = tuple(FAMILIES)
FOCUS = ("oil", "gold", "copper")
CHAIN_IDS = {
    "oil": ("oil_inflation_duration_derate", "oil_slide_disinflation_duration_rerate"),
    "gold": ("real_rate_peak_gold_rerate",),
    "copper": (),
}
SOURCE_PATHS = {
    "commodities": "data/commodity/complex_latest.json",
    "rates": "data/transmission/latest.json",
    "fx": "data/forex/latest.json",
    "chains": "data/transmission/chain_state.json",
    "ratios": "data/commodity/latest.json",
}
NODE_LABELS = {
    "oil_shock": ("Oil advance", "油价上涨"),
    "breakeven_rise": ("Inflation expectations rise", "通胀预期上升"),
    "yield_rise": ("Yields rise", "收益率上升"),
    "duration_derate": ("Growth equities lag", "成长股落后"),
    "oil_slide": ("Oil retreat", "油价回落"),
    "breakeven_fall": ("Inflation expectations ease", "通胀预期回落"),
    "real_yield_fall": ("Real yields fall", "实际收益率下降"),
    "duration_rerate": ("Growth equities recover", "成长股修复"),
    "real_rate_extreme": ("High real yields", "实际收益率处于高位"),
    "real_rate_rolldown": ("Real yields turn lower", "实际收益率转跌"),
    "gold_bid": ("Gold confirms", "金价确认"),
}
HYPOTHESES = {
    "oil": [
        {"id": "unresolved", "label": ("Cause unresolved", "原因未明"),
         "mechanism": ("A price move alone cannot identify a supply or demand shock.", "仅凭油价变化，无法辨别供给或需求冲击。"),
         "confirm": ("Compare dated inventories, production, refinery activity and the futures curve.", "核对有日期的库存、产量、炼厂活动与期货曲线。"),
         "invalidate": ("Conflicting physical evidence keeps the explanation unresolved.", "实物市场证据冲突时，继续保留不确定性。")},
        {"id": "supply", "label": ("Supply disruption", "供应受扰"),
         "mechanism": ("If lost supply drives oil higher, input costs can rise while demand weakens.", "若供给减少推高油价，投入成本可能上升，需求却可能转弱。"),
         "confirm": ("Look for corroborating supply losses, seasonal inventory tightness and nearby spreads.", "寻找供应损失、季节性库存偏紧与近月价差的相互印证。"),
         "invalidate": ("Restored supply and easing physical tightness would weaken this explanation.", "供应恢复、实物市场紧张缓解，会削弱这一解释。")},
        {"id": "demand", "label": ("Demand expansion", "需求扩张"),
         "mechanism": ("If demand drives oil higher, broader industrial activity should corroborate the move.", "若需求扩张推高油价，更广泛的工业活动应提供印证。"),
         "confirm": ("Check refinery throughput, four-week product demand, industrial metals and activity.", "核对炼厂加工量、四周产品需求、工业金属与经济活动。"),
         "invalidate": ("Weakening activity and product demand would challenge the demand explanation.", "经济活动与成品油需求走弱，会挑战需求扩张的解释。")},
        {"id": "supply_recovery", "label": ("Supply recovery", "供应恢复"),
         "mechanism": ("If restored supply lowers oil, cheaper inputs can support consumers without implying weaker demand.", "若供应恢复压低油价，投入成本下降可能利好消费端，而不意味着需求转弱。"),
         "confirm": ("Look for restored production, easing nearby spreads and stable product consumption.", "寻找产量恢复、近月价差缓和与产品消费稳定的证据。"),
         "invalidate": ("Falling activity and consumption would challenge a supply-only explanation.", "经济活动与消费下降，会挑战单纯的供应解释。")},
        {"id": "demand_contraction", "label": ("Demand contraction", "需求收缩"),
         "mechanism": ("If weaker demand lowers oil, cheaper inputs may coincide with weaker sales and credit conditions.", "若需求转弱压低油价，投入成本下降可能伴随销售及信贷状况走弱。"),
         "confirm": ("Seek weakening product consumption and activity alongside inventory accumulation.", "寻找产品消费及经济活动走弱，同时库存增加的证据。"),
         "invalidate": ("Resilient consumption with a documented supply recovery would weaken this explanation.", "消费保持韧性且供应明确恢复，会削弱这一解释。")},
    ],
    "gold": [
        {"id": "unresolved", "label": ("Cause unresolved", "原因未明"),
         "mechanism": ("Gold's currency, real-rate and defensive-demand relationships can pull in different directions.", "汇率、实际利率与避险需求对黄金的影响可能方向相反。"),
         "confirm": ("Check real yields, the dollar and gold-specific physical or fund-flow evidence.", "核对实际收益率、美元及黄金实物或资金流证据。"),
         "invalidate": ("A narrative without corroborating gold evidence remains a hypothesis.", "缺乏黄金自身证据的叙事仍属于假设。")},
        {"id": "rates", "label": ("Real-rate relief", "实际利率压力缓解"),
         "mechanism": ("Falling real yields may ease gold's opportunity-cost pressure; price confirmation is separate.", "实际收益率下降可能减轻持有黄金的机会成本压力；价格确认需单独检验。"),
         "confirm": ("Inspect the existing real-rate-to-gold sequence and its unconfirmed steps.", "检查现有实际利率至黄金的传导序列及未确认环节。"),
         "invalidate": ("Persistently rising real yields would weaken this explanation.", "实际收益率持续上升，会削弱这一解释。")},
    ],
    "copper": [
        {"id": "unresolved", "label": ("Cause unresolved", "原因未明"),
         "mechanism": ("Copper can reflect industrial demand, supply constraints and currency effects simultaneously.", "铜价可能同时反映工业需求、供应约束与汇率影响。"),
         "confirm": ("Check exchange inventories, physical premiums, China activity and the dollar.", "核对交易所库存、实物升水、中国经济活动与美元。"),
         "invalidate": ("Price strength without physical or activity corroboration does not establish stronger demand.", "缺乏实物市场或经济活动印证的涨价，不能证明需求增强。")},
        {"id": "demand", "label": ("Industrial demand", "工业需求"),
         "mechanism": ("A demand explanation needs evidence beyond copper's price trend.", "需求解释需要铜价趋势之外的证据。"),
         "confirm": ("Seek agreement between manufacturing activity, inventory use and physical premiums.", "寻找制造业活动、库存消耗与实物升水之间的一致性。"),
         "invalidate": ("Inventory accumulation alongside weak activity challenges a demand-led recovery.", "库存累积且经济活动疲弱，会挑战需求驱动复苏的解释。")},
    ],
}


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def number(value: Any) -> float | int | None:
    """Keep genuine zero and negative observations; never coerce text/bool to data."""
    if not isinstance(value, Real) or isinstance(value, bool) or not math.isfinite(value):
        return None
    return int(value) if isinstance(value, Integral) else float(value)


def iso_date(value: Any) -> str | None:
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        return value if date.fromisoformat(value).isoformat() == value else None
    except ValueError:
        return None


def bil(en: str, zh: str) -> dict[str, str]:
    return {"en": en, "zh": zh}


def _safe_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_json(v) for v in value]
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, Real):
        return number(value)
    return None


def fingerprint(value: Any) -> str:
    return sha256(json.dumps(_safe_json(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def source_receipt(key: str, doc: Any, cutoff: str | None) -> dict:
    d = _dict(doc)
    stamp = iso_date(d.get("asof"))
    state = "available"
    if not d:
        state = "missing"
    elif stamp is None:
        state = "undated"
    elif cutoff is None:
        state = "cutoff_unavailable"
    elif stamp > cutoff:
        state = "newer_than_snapshot"
    elif stamp < cutoff:
        state = "earlier_context"
    return {"id": key, "path": SOURCE_PATHS.get(key, "data/eia/"), "as_of": stamp,
            "state": state, "available_at": None, "point_in_time_verified": False,
            "immutable_source": None, "same_research_date": state == "available",
            "fingerprint": fingerprint(d) if d else None}


def _receipt_value(receipt: dict) -> dict:
    """Preserve the owner's metric/window/operator; never translate yield into return."""
    out = {k: deepcopy(receipt.get(k)) for k in ("series", "path", "metric", "window", "vs", "op", "threshold", "value", "passed") if k in receipt}
    if "value" in out and not isinstance(out["value"], str):
        out["value"] = number(out["value"])
    if "threshold" in out and not isinstance(out["threshold"], str):
        out["threshold"] = number(out["threshold"])
    if "passed" in out and not isinstance(out["passed"], bool):
        out["passed"] = None
    unit = {"ret_bp": "bp", "ret_pct": "%", "rs_pp": "pp"}.get(out.get("metric"))
    out["unit"] = unit
    out["observation_at"] = None
    return out


def _project_chain(chain: dict, receipt: dict, rates: dict) -> dict:
    raw_nodes = chain.get("nodes") if isinstance(chain.get("nodes"), list) else []
    raw_hops = chain.get("hops") if isinstance(chain.get("hops"), list) else []
    nodes, conflicts = [], []
    for raw in raw_nodes:
        n = _dict(raw)
        raw_checks = n.get("receipts") if isinstance(n.get("receipts"), list) else []
        checks = [_receipt_value(r) for r in raw_checks if isinstance(r, dict)]
        node_id = str(n.get("id", ""))
        nodes.append({"id": node_id, "label": bil(*NODE_LABELS.get(node_id, ("Evidence step", "证据环节"))),
                      "resolved": n.get("resolved") is True, "confirmed": n.get("confirmed") is True,
                      "receipts": checks})
        for check in checks:
            if check.get("series") == "DFII10" and check.get("metric") == "ret_bp" and check.get("window") == 22:
                counterpart = number(rates.get("real_10y_chg_22d_bp"))
                own = number(check.get("value"))
                if counterpart is not None and own is not None and abs(counterpart - own) > 0.5:
                    conflicts.append({"metric": "DFII10.ret_bp.22", "unit": "bp",
                                      "chain_value": own, "rates_value": counterpart})
    all_resolved = bool(nodes) and all(n["resolved"] for n in nodes)
    all_current = all_resolved and all(n["confirmed"] for n in nodes)
    hops = [{"id": h.get("id"), "from": h.get("from"), "to": h.get("to"),
             "lag_days": _safe_json(h.get("lag_d")), "confirmed": h.get("confirmed") is True,
             "confirmed_at": iso_date(h.get("asof"))} for h in raw_hops if isinstance(h, dict)]
    dated_hops = [h["confirmed_at"] for h in hops if h["confirmed"]]
    recorded_complete = (bool(hops) and all(h["confirmed"] for h in hops)
                         and all(dated_hops) and receipt["as_of"] is not None
                         and all(d <= receipt["as_of"] for d in dated_hops)
                         and dated_hops == sorted(dated_hops)
                         and bool(chain.get("episode_id")))
    applicability = "unassessed"
    if receipt["state"] != "available" or not all_resolved:
        applicability = "unavailable"
    elif chain.get("falsifier_fired") is not None:
        applicability = "contradicted"
    elif all_current and not conflicts:
        applicability = "current_checks_met"
    elif any(n["confirmed"] for n in nodes) or conflicts:
        applicability = "mixed"
    cohorts = []
    for key, value in _dict(chain.get("blast")).items():
        item = _dict(value)
        # Existing cohort membership is not a verified business-exposure or stock signal.
        cohorts.append({"id": key, "label": deepcopy(item.get("label")),
                        "note": deepcopy(item.get("note")), "count": number(item.get("n")),
                        "unevaluable": number(item.get("unevaluable")), "ranked": False})
    return {"id": chain.get("chain"), "revision": chain.get("rev"),
            "title": deepcopy(chain.get("title")), "source_id": "chains", "as_of": receipt["as_of"],
            "claim_type": "conditional", "applicability": applicability,
            "source_state": receipt["state"], "current_checks_met": sum(n["confirmed"] and n["resolved"] for n in nodes),
            "current_checks_total": len(nodes),
            "recorded_sequence_status": "dated_episode_record" if recorded_complete else "incomplete_or_undated",
            "causal_timing_verified": False,
            "owner_state": chain.get("state"), "episode_id": chain.get("episode_id"),
            "nodes": nodes, "hops": hops,
            "conflicts": conflicts, "cohorts": cohorts,
            "forecast": False, "tradable_signal": False}


def _interpret_asset(asset: dict, chains: list, rates: dict, sources: dict) -> dict:
    """Plain readings of published observations; no estimated cause or recommendation."""
    change, trend = asset["change_1m_pct"], asset["trend"]
    headline = bil("Read the available evidence", "查看现有证据")
    detail = bil("A dated price move is an observation. Its explanation needs separate evidence.", "有日期的价格变化属于观察，其原因需要独立证据。")
    if not asset["as_of"] or change is None:
        return {"headline": headline, "detail": detail, "source_ids": ["commodities"], "assessment": "unavailable"}
    if change < 0 and trend == "up":
        headline = bil("A pullback within an uptrend.", "上涨趋势中的回落。")
        detail = bil("The one-month move is negative; the published long-term trend remains up. A reversal is not established by this combination alone.", "一个月变化为负，已发布的长期趋势仍向上；仅凭这一组合，不能确认趋势反转。")
    elif change > 0 and trend == "down":
        headline = bil("A rebound within a downtrend.", "下跌趋势中的反弹。")
        detail = bil("The one-month move is positive; the published long-term trend remains down. A recovery needs further confirmation.", "一个月变化为正，已发布的长期趋势仍向下；复苏需要进一步确认。")
    elif change > 0 and trend == "up":
        headline = bil("Price and trend point higher.", "价格与趋势同向上行。")
        detail = bil("The one-month advance agrees with the published long-term trend. This alignment does not identify the cause or establish a future return.", "一个月涨幅与已发布的长期趋势一致；这种一致性不能识别原因，也不能确定未来回报。")
    elif change < 0 and trend == "down":
        headline = bil("Price and trend point lower.", "价格与趋势同向下行。")
        detail = bil("The one-month decline agrees with the published long-term trend. Supply, demand and positioning still need separate investigation.", "一个月跌幅与已发布的长期趋势一致，仍需分别研究供应、需求与持仓。")
    source_ids = ["commodities"]
    oil_chain = next((c for c in chains if c["id"] == "oil_inflation_duration_derate"), {})
    inflation = next((n for n in oil_chain.get("nodes", []) if n["id"] == "breakeven_rise"), {})
    if (asset["id"] == "oil" and change > 0 and sources["chains"]["state"] == "available"
        and inflation.get("resolved") and not inflation.get("confirmed")):
        headline = bil("Strong oil. Inflation link unconfirmed.", "油价偏强，通胀传导未确认。")
        detail = bil("Oil is higher over one month, but the existing inflation-expectation check is not met. Other market moves cannot establish this missing link.", "油价一个月上涨，但现有通胀预期条件未满足。其他市场变化不能补足这一缺失的传导环节。")
        source_ids += ["chains"]
    if (asset["id"] == "gold" and change < 0 and sources["rates"]["state"] == "available"
        and number(rates.get("real_10y_chg_22d_bp")) is not None and rates["real_10y_chg_22d_bp"] > 0):
        headline = bil("Weaker gold. Higher real yields.", "黄金走弱，实际收益率走高。")
        detail = bil("Gold is falling alongside higher real-yield readings. This is consistent with rate pressure, but does not establish it as the cause.", "黄金下跌与实际收益率读数上升同时出现；这与利率压力的解释相符，但不能证明因果关系。")
        source_ids += ["rates"]
    if (asset["id"] == "gold" and change < 0
        and sources["rates"]["state"] == "available" and sources["chains"]["state"] == "available"
        and any(c["conflicts"] for c in chains)):
        headline = bil("Weaker gold. Rate readings differ.", "黄金走弱，利率读数有分歧。")
        detail = bil("Gold is lower over one month. Published real-yield changes differ; compare their observation windows and revisions before linking the move to rates.", "黄金一个月下跌，已发布的实际收益率变化存在分歧；将走势归因于利率前，需核对观察窗口与修订版本。")
        source_ids = ["commodities", "rates", "chains"]
    return {"headline": headline, "detail": detail, "source_ids": source_ids, "assessment": "descriptive"}



def _physical_view(context: dict, cutoff: str | None, chains: list, change: float | None) -> dict:
    """Interpret the existing display owner; never infer a cause or release vintage."""
    out = {
        "state": "missing", "classification": "unavailable", "as_of": None,
        "age_days": None, "hypothesis_confirmation_eligible": False,
        "headline": bil("US petroleum balance unavailable", "美国石油供需数据不可用"),
        "detail": bil("The price and transmission readings remain available. Dated physical evidence is needed to distinguish oil-market explanations.",
                      "仍可查看价格及传导读数；区分油价解释需要有日期的实物证据。"),
        "clock": bil("Physical observation date unavailable.", "实物观察日期不可用。"),
        "causal_limit": bil("Inventory changes alone do not distinguish supply, demand, refinery operations or trade.",
                           "库存变化本身无法区分供应、需求、炼厂运作或贸易因素。"),
        "stocks": [], "flows": [], "evidence": {}, "source_id": "physical",
        "downstream": bil("The inflation link needs its own dated evidence.", "通胀传导需要独立的有日期证据。"),
        "business_read": bil("Check realised prices and hedges for producers, product spreads for refiners, and fuel pass-through for consumers.",
                             "生产商需核对实现价格与套保，炼油商需核对产品价差，消费端需核对燃料成本转嫁。"),
        "owner_method_revision": context.get("method_revision"), "method": deepcopy(_dict(context.get("method"))),
        "source_dependencies": deepcopy(context.get("sources", {})),
        "release_at": None, "point_in_time_verified": False,
    }
    if (context.get("schema") != "mmx.commodities.petroleum_balance.v1"
        or not cutoff or not iso_date(context.get("analysis_cutoff"))
        or context["analysis_cutoff"] > cutoff or context.get("display_only") is not True):
        return out
    receipts = _dict(context.get("evidence"))

    def observation(key):
        r = {"value": None, "unit": None, "observation_at": None, "window_start": None,
             "window_end": None, "reference": None, "source_ids": [], "release_at": None,
             "point_in_time_verified": False, **deepcopy(_dict(receipts.get(key)))}
        value, stamp = number(r.get("value")), iso_date(r.get("observation_at"))
        released = r.get("release_at")
        release_date = iso_date(released[:10]) if isinstance(released, str) else None
        if value is None or stamp is None or stamp > cutoff or (release_date and release_date > cutoff):
            r["value"] = None
            r["state"] = "unqualified_for_snapshot"
        else:
            r["value"] = value
        return r

    labels = {"crude": ("Commercial crude", "商业原油"), "gasoline": ("Gasoline", "汽油"),
              "distillate": ("Distillate", "馏分油")}
    balance_labels = {
        "tight": bil("Below seasonal norm", "低于季节常态"),
        "ample": bil("Above seasonal norm", "高于季节常态"),
        "balanced": bil("Near seasonal norm", "接近季节常态"),
        "unavailable": bil("Seasonal comparison unavailable", "季节比较不可用"),
    }
    for stem, label in labels.items():
        level, anomaly, delta = [observation(stem + suffix) for suffix in ("_stocks_mb", "_z", "_chg_4w_mb")]
        z = number(anomaly.get("value"))
        if (number(level.get("value")) is None or level.get("unit") != "million_barrels"
            or anomaly.get("observation_at") != level.get("observation_at")
            or anomaly.get("unit") != "seasonal_z"
            or (number(_dict(anomaly.get("reference")).get("observations")) or 0) < 104):
            z = None
            anomaly["value"] = None
        category = "unavailable" if z is None else "tight" if z <= -.5 else "ample" if z >= .5 else "balanced"
        cover_key = {"crude": "days_supply", "gasoline": "gasoline_days", "distillate": "distillate_days"}[stem]
        cover = observation(cover_key)
        if cover.get("observation_at") != level.get("observation_at"):
            cover["value"] = None
        out["stocks"].append({
            "id": stem, "label": bil(*label), "balance": category, "balance_label": balance_labels[category],
            "level": level, "anomaly": anomaly, "change_4w": delta, "days_cover": cover,
        })
        for key, r in ((stem + "_stocks_mb", level), (stem + "_z", anomaly),
                       (stem + "_chg_4w_mb", delta), (cover_key, cover)):
            out["evidence"][key] = r

    flow_labels = (
        ("refinery_inputs_avg", ("Refinery inputs · average", "炼厂投入 · 均值")),
        ("gasoline_supplied_avg", ("Gasoline supplied · average", "汽油供应量 · 均值")),
        ("distillate_supplied_avg", ("Distillate supplied · average", "馏分油供应量 · 均值")),
        ("production_mbd", ("US crude production", "美国原油产量")),
        ("production_chg_4w", ("Production change · 4 weeks", "产量变化 · 四周")),
        ("refinery_util", ("Refinery utilisation", "炼厂利用率")),
        ("spr_chg_4w_mb", ("SPR stock change · 4 weeks", "战略储备库存变化 · 四周")),
        ("cushing_stocks_mb", ("Cushing crude stocks", "库欣原油库存")),
    )
    for key, label in flow_labels:
        r = observation(key)
        out["evidence"][key] = r
        out["flows"].append({"id": key, "label": bil(*label), **r})
    dates = [iso_date(row["anomaly"].get("observation_at")) for row in out["stocks"]]
    states = [row["balance"] for row in out["stocks"]]
    common = len(set(dates)) == 1 and all(dates) and "unavailable" not in states
    if not any(number(row["level"].get("value")) is not None for row in out["stocks"]):
        return out
    out["state"] = "dated_context"
    out["as_of"] = dates[0] if common else None
    if common:
        out["age_days"] = (date.fromisoformat(cutoff) - date.fromisoformat(dates[0])).days
        out["clock"] = bil(
            f"Week ending {dates[0]} · {out['age_days']} days before the price snapshot · release vintage unavailable.",
            f"截至{dates[0]}的一周 · 早于价格快照{out['age_days']}天 · 发布版本不可核实。")
    else:
        out["clock"] = bil("Observation weeks differ or seasonal coverage is incomplete; read each source date.",
                           "观察周不同或季节覆盖不完整，请分别查看来源日期。")
    classification = "partial"
    headline = bil("A partial physical picture", "实物证据仍不完整")
    detail = bil("The available stock observations remain useful, but missing or differently dated seasonal comparisons prevent a broad balance conclusion.",
                 "现有库存观察仍有参考价值，但季节比较缺失或日期不同，无法形成整体供需判断。")
    if common:
        if states == ["tight"] * 3:
            classification = "broad_tightness"
            headline = bil("Crude and product stocks below seasonal norms", "原油与成品油库存均低于季节常态")
            detail = bil("All three stock categories were below their own seasonal norms in this observation week. This shows a tight US inventory buffer; it does not identify the cause or establish a global supply loss.",
                         "该观察周的三类库存均低于各自季节常态，说明美国库存缓冲偏紧；尚不能识别原因或确认全球供应损失。")
        elif states == ["ample"] * 3:
            classification = "ample"
            headline = bil("Crude and product stocks above seasonal norms", "原油与成品油库存均高于季节常态")
            detail = bil("The available US inventory buffer was ample across crude and products. A weak-demand explanation still needs consumption and activity evidence; extra supply can also raise stocks.",
                         "美国原油及成品油库存缓冲均较充裕。需求疲弱的解释仍需消费与活动证据，额外供应也可能推高库存。")
        elif states[0] != "tight" and states[1:] == ["tight", "tight"]:
            classification = "product_tightness"
            headline = bil("Product stocks tight; crude less constrained", "成品油库存偏紧，原油约束较轻")
            detail = bil("Gasoline and distillate stocks were below seasonal norms while crude was not. The contrast focuses attention on product supply, refinery operations and trade; it does not establish a crude supply shock.",
                         "汽油与馏分油库存低于季节常态，原油则未出现同样偏紧。应重点核查成品油供应、炼厂运作与贸易，而不能据此确认原油供应冲击。")
            out["business_read"] = bil(
                "Product tightness makes refining margins and fuel pass-through worth checking. Refiners need product prices to outpace crude and operating costs; fuel users need evidence on hedges and pricing power.",
                "成品油偏紧值得进一步检查炼油利润与燃料成本转嫁。炼油商需确认产品价格能否跑赢原油及运营成本，燃料使用方需检查套保与定价能力。")
        elif states[0] == "tight" and "tight" not in states[1:]:
            classification = "crude_tightness"
            headline = bil("Crude stocks tight; products do not confirm", "原油库存偏紧，成品油未同步印证")
            detail = bil("Crude was below its seasonal norm while product stocks were not. Refinery runs, imports, exports and domestic production can help distinguish a crude-specific constraint from stronger final demand.",
                         "原油低于季节常态，但成品油库存未同步偏紧。炼厂加工、进出口与国内产量有助于区分原油供应约束与终端需求增强。")
        elif states == ["balanced"] * 3:
            classification = "near_seasonal"
            headline = bil("Stocks close to seasonal norms", "库存接近季节常态")
            detail = bil("The three stock categories were near their seasonal norms. These inventory levels alone offer little basis for choosing a supply or demand explanation for the price move.",
                         "三类库存均接近季节常态；仅凭这些库存水平，难以选择供应或需求来解释价格变化。")
        else:
            classification = "mixed"
            headline = bil("Crude and products tell different stories", "原油与成品油证据有分歧")
            detail = bil("Inventory conditions differed across crude, gasoline and distillate. Preserve that disagreement: one broad tightness label would hide where the pressure actually sits.",
                         "原油、汽油与馏分油的库存状况不同，应保留这种分歧；单一的整体松紧标签会掩盖压力所在。")
    out.update(classification=classification, headline=headline, detail=detail)
    chain_id, node_id = ("oil_slide_disinflation_duration_rerate", "breakeven_fall") if change is not None and change < 0 else ("oil_inflation_duration_derate", "breakeven_rise")
    chain = next((c for c in chains if c["id"] == chain_id), {}) if change is not None and change != 0 else {}
    node = next((n for n in chain.get("nodes", []) if n["id"] == node_id), {})
    if chain.get("source_state") == "available" and node.get("resolved"):
        if node.get("confirmed"):
            out["downstream"] = bil("The separate inflation-expectation check is met. Yields, timing and equity responses still need their own checks; physical tightness does not confirm the whole sequence.",
                                    "独立的通胀预期条件已满足。收益率、时序与股票反应仍需分别检查；实物市场偏紧不能确认整条传导。")
        else:
            out["downstream"] = bil("The separate inflation-expectation check is not met. This physical reading cannot fill that gap, so a rates or duration conclusion remains incomplete.",
                                    "独立的通胀预期条件尚未满足。实物读数不能补足这一缺口，因此利率或久期结论仍不完整。")
    return out


def _gold_physical_view(publication: dict, cutoff: str | None, parent: dict) -> dict:
    """Read the existing China-premium publication without recalculating its spread."""
    raw = _dict(_dict(publication.get("gold_context")).get("china_physical_premium"))
    stamp, display_clock = None, None
    source_asof = raw.get("source_asof")
    if iso_date(source_asof):
        stamp = source_asof
        display_clock = source_asof
    elif isinstance(source_asof, str):
        try:
            parsed = datetime.fromisoformat(source_asof.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc)
                stamp = parsed.date().isoformat()
                display_clock = parsed.strftime("%Y-%m-%d %H:%M UTC")
        except (ValueError, TypeError):
            pass
    receipt = {
        "id": "gold_physical", "path": SOURCE_PATHS["ratios"],
        "field": "gold_context.china_physical_premium", "as_of": stamp,
        "source_timestamp": source_asof, "publisher_as_of": parent.get("as_of"),
        "available_at": None, "point_in_time_verified": False,
        "immutable_source": deepcopy(parent.get("immutable_source")),
        "fingerprint": fingerprint(raw) if raw else None, "same_research_date": False,
    }
    method = raw.get("method") if isinstance(raw.get("method"), str) else None
    labels = {
        "close_proxy": bil("China premium · close-based proxy", "中国溢价 · 收盘代理指标"),
        "canonical": bil("China premium · official benchmark comparison", "中国溢价 · 官方基准比较"),
        "intraday": bil("China premium · indicative intraday proxy", "中国溢价 · 日内参考代理"),
    }
    out = {
        "state": "unavailable", "source_receipt": receipt, "method": method,
        "label": labels.get(method, bil("China physical pricing", "中国实物定价")),
        "headline": bil("Regional pricing context unavailable", "区域定价背景不可用"),
        "detail": bil("A qualified, dated China-premium reading is not attached to this snapshot. Gold price and rate evidence remain available.",
                      "此快照未接入合格且有日期的中国溢价读数，仍可查看黄金价格与利率证据。"),
        "implication": bil("Regional relative pricing does not resolve the separate rate readings or identify the cause of gold's price move.",
                           "区域相对定价不能解决独立利率读数的分歧，也不能确定金价变化的原因。"),
        "premium_pct": None, "avg_5_pct": None, "range_30_pct": None,
        "clock": display_clock, "source_fresh_at_publication": raw.get("source_fresh") is True,
        "official_canonical_available": raw.get("official_canonical_available") is True,
        "context_only": True, "hypothesis_confirmation_eligible": False,
        "point_in_time_verified": False, "source_id": "gold_physical",
        "basis": bil("The comparison method is not qualified for this view.", "本视图尚未确认比较方法。"),
        "statistics_basis": bil("Published history of the same comparison method.", "同一比较方法的已发布历史。"),
    }
    value = number(raw.get("premium_pct"))
    expected_currency = "CNY" if method == "close_proxy" else "USD"
    if not raw:
        receipt["state"] = "missing"
    elif not stamp:
        receipt["state"] = "undated"
    elif not cutoff or parent.get("state") not in ("available", "earlier_context"):
        receipt["state"] = "publisher_unqualified"
    elif stamp > cutoff or stamp > parent["as_of"]:
        receipt["state"] = "newer_than_snapshot"
    elif (raw.get("available") is not True or raw.get("context_only") is not True or value is None or value <= -100):
        receipt["state"] = "unavailable"
    elif (method not in labels or raw.get("price_currency") != expected_currency
          or (method == "canonical" and raw.get("official_canonical_available") is not True)):
        receipt["state"] = "method_unqualified"
    elif raw.get("source_fresh") is not True:
        receipt["state"] = "stale_or_unqualified_freshness"
        out["detail"] = bil("The publisher does not mark this regional observation fresh. Open its source history before using it alongside this price snapshot.",
                            "发布来源未将此区域观察标为新鲜；与本次价格快照结合前，请查看来源历史。")
    else:
        receipt["state"] = "available" if stamp == cutoff else "earlier_context"
        receipt["same_research_date"] = stamp == cutoff
        out["state"] = receipt["state"]
        out["premium_pct"] = value
        out["headline"] = bil(
            "Shanghai priced above the reference" if value > 0 else "Shanghai priced below the reference" if value < 0 else "Shanghai and the reference at parity",
            "上海价格高于参考市场" if value > 0 else "上海价格低于参考市场" if value < 0 else "上海与参考市场价格持平")
        out["detail"] = bil(
            "This regional relative price can coexist with a rising or falling global gold price. Demand, import constraints, supply and market structure can all influence the gap; its sign alone does not measure global physical demand.",
            "这一区域相对价格可以与全球金价上涨或下跌并存。需求、进口约束、供应与市场结构均会影响价差，其正负本身不能衡量全球实物需求。")
        if method != "intraday":
            out["avg_5_pct"] = number(raw.get("avg_5_pct"))
            bounds = raw.get("range_30_pct")
            if isinstance(bounds, list) and len(bounds) == 2:
                low, high = map(number, bounds)
                if low is not None and high is not None and low <= high:
                    out["range_30_pct"] = [low, high]
        out["basis"] = bil(
            "Shanghai Au99.99 in CNY per gram is converted to CNY per troy ounce and compared with aligned global XAU/CNY at the Shanghai close. This is an indicative proxy, not the official Shanghai/London benchmark.",
            "上海Au99.99人民币/克价格换算为人民币/金衡盎司后，与上海收盘时钟对齐的全球XAU/CNY比较。这是参考代理指标，并非官方上海/伦敦基准。"
        ) if method == "close_proxy" else bil(
            "Shanghai and London prices are compared after currency conversion. The benchmark and intraday proxy remain separate methods; an intraday reading does not inherit the benchmark's history.",
            "上海与伦敦价格经汇率换算后比较。基准与日内代理属于不同方法，日内读数不继承基准历史。")
    if receipt.get("state") == "newer_than_snapshot":
        out["detail"] = bil("The regional observation is newer than the price snapshot or its parent publication. It is excluded from this investigation.",
                            "区域观察晚于价格快照或其所属发布日期，已从本次研究中排除。")
    return out

def build_workspace(snapshot: Any, *, transmission: Any = None, fx: Any = None,
                    chain_state: Any = None, commodity_latest: Any = None, source_identities: Any = None,
                    physical_context: Any = None) -> dict:
    """Project immutable publisher artifacts. Missing context degrades only its own panel."""
    snapshot, transmission, fx, chain_state = map(_dict, (snapshot, transmission, fx, chain_state))
    commodity_latest = _dict(commodity_latest)
    physical_context = _dict(physical_context)
    cutoff = iso_date(snapshot.get("asof"))
    sources = {k: source_receipt(k, d, cutoff) for k, d in
               (("commodities", snapshot), ("rates", transmission), ("fx", fx), ("chains", chain_state), ("ratios", commodity_latest), ("physical", physical_context))}
    for key, identity in _dict(source_identities).items():
        if key in sources and isinstance(identity, dict):
            sources[key]["immutable_source"] = _safe_json(identity)
    rates_raw = _dict(_dict(transmission.get("state")).get("rates"))
    # Never compare disagreeing metric values from different publisher dates.
    same_date_rates = rates_raw if sources["rates"]["as_of"] == sources["chains"]["as_of"] else {}
    raw_members = snapshot.get("members") if isinstance(snapshot.get("members"), list) else []
    assets, seen = [], set()
    for member in raw_members:
        m = _dict(member)
        key, family = m.get("name"), m.get("class")
        if key not in LABELS or family not in FAMILIES or key in seen:
            continue
        seen.add(key)
        velocity = _dict(m.get("velocity"))
        assets.append({"id": key, "label": bil(*LABELS[key]), "family": family,
                       "change_1m_pct": number(m.get("chg_1m_pct")),
                       "returns": {str(w): number(velocity.get(f"r{w}")) for w in (5, 20, 60, 252)},
                       "trend": m.get("ts_trend") if m.get("ts_trend") in ("up", "down", "flat") else None,
                       "momentum": m.get("momentum_state") if m.get("momentum_state") in ("bull", "bear", "neutral") else None,
                       "as_of": cutoff, "source_id": "commodities",
                       "identity_basis": "existing_commodity_name", "contract": None,
                       "return_basis": "publisher_price_series", "deep_coverage": key in FOCUS})
    by_id = {a["id"]: a for a in assets}
    families = [{"id": k, "label": bil(*FAMILIES[k]), "assets": [a for a in assets if a["family"] == k]}
                for k in FAMILY_ORDER if any(a["family"] == k for a in assets)]
    index = _dict(snapshot.get("index"))
    breadth = _dict(snapshot.get("breadth"))
    n_members, n_up = number(breadth.get("n_members")), number(breadth.get("n_up_trend"))
    breadth_valid = (isinstance(n_members, int) and isinstance(n_up, int) and
                     0 <= n_up <= n_members and n_members == len(assets))
    headline = bil("Read each commodity", "逐品种判断")
    oil = by_id.get("oil", {}).get("change_1m_pct")
    metal_ids = ("gold", "silver", "platinum", "palladium", "copper")
    metals = [by_id.get(k, {}).get("change_1m_pct") for k in metal_ids]
    if cutoff and oil is not None and oil > 0 and all(x is not None and x < 0 for x in metals):
        headline = bil("Oil holds. Metals retreat.", "油价坚挺，金属回落。")
    chains = []
    for raw in chain_state.get("chains", []) if isinstance(chain_state.get("chains"), list) else []:
        c = _dict(raw)
        if any(c.get("chain") in ids for ids in CHAIN_IDS.values()):
            chains.append(_project_chain(c, sources["chains"], same_date_rates))
    rates = {key: number(rates_raw.get(key)) for key in
             ("real_10y", "nominal_10y", "real_10y_chg_22d_bp", "real_10y_chg_63d_bp", "curve_2s10s")}
    rates["direction"] = rates_raw.get("direction") if rates_raw.get("direction") in ("rising", "falling", "flat") else None
    for asset in assets:
        asset["read"] = _interpret_asset(asset, chains, rates, sources)
    physical = _physical_view(physical_context, cutoff, chains, by_id.get("oil", {}).get("change_1m_pct"))
    gold_physical = _gold_physical_view(commodity_latest, cutoff, sources["ratios"])
    sources["gold_physical"] = gold_physical["source_receipt"]
    ratios = []
    for key, label in (("gold_silver", ("Gold / silver", "黄金 / 白银")), ("copper_gold", ("Copper / gold", "铜 / 黄金"))):
        raw = _dict(_dict(commodity_latest.get("ratios")).get(key))
        value = number(raw.get("chg_20d_pct"))
        if value is not None:
            ratios.append({"id": key, "label": bil(*label), "change_pct": value, "window_sessions": 20,
                           "source_id": "ratios", "as_of": sources["ratios"]["as_of"],
                           "source_state": sources["ratios"]["state"], "claim_type": "descriptive", "forecast": False})
    # An aggregate publisher date must not silently replace an absent correlation clock.
    fx_tx = _dict(fx.get("transmission"))
    metric_date = iso_date(fx_tx.get("as_of"))
    method = _dict(fx_tx.get("method"))
    direction = fx_tx.get("usd_dir") if fx_tx.get("usd_dir") in ("strengthening", "weakening", "flat") else None
    direction_state = sources["fx"]["state"]
    # The current owner omits a per-direction clock. Preserve that parent-dated
    # description, but never replace an explicitly supplied invalid/future clock.
    direction_clock = "transmission_observation" if "as_of" in fx_tx else "publisher_date_only"
    if "as_of" in fx_tx:
        if (metric_date is None or not sources["fx"]["as_of"] or not cutoff
                or metric_date > sources["fx"]["as_of"] or metric_date > cutoff):
            direction, direction_state = None, "date_unqualified"
        elif direction_state == "available" and metric_date < cutoff:
            direction_state = "earlier_context"
    # Do not infer estimator windows, pair orientation or coverage from field names.
    fx_statistics_qualified = (sources["fx"]["state"] == "available" and metric_date is not None
        and metric_date <= sources["fx"]["as_of"] and metric_date <= cutoff
        and method.get("estimator") == "pearson_return_correlation"
        and method.get("sampling") == "aligned_daily_returns" and method.get("pair_orientation") == "usd_strength_vs_asset"
        and type(method.get("window_fast")) is int and type(method.get("window_slow")) is int
        and 2 <= method["window_fast"] < method["window_slow"]
        and isinstance(method.get("revision"), str) and bool(method["revision"]))
    fx_rows = []
    for symbol, raw in _dict(fx_tx.get("assets")).items():
        item = _dict(raw)
        fast, slow = number(item.get("corr_fast")), number(item.get("corr_slow"))
        coverage = _dict(item.get("coverage"))
        if (not fx_statistics_qualified or fast is None or slow is None or not (-1 <= fast <= 1 and -1 <= slow <= 1)
            or type(coverage.get("fast")) is not int or type(coverage.get("slow")) is not int
            or coverage["fast"] != method["window_fast"] or coverage["slow"] != method["window_slow"]):
            continue
        fx_rows.append({"series": symbol, "corr_fast": fast, "corr_slow": slow,
                        "as_of": metric_date, "method": deepcopy(method), "coverage": deepcopy(coverage),
                        "window_fast": method["window_fast"], "window_slow": method["window_slow"],
                        "claim_type": "statistical", "causal": False})
    return {"schema": SCHEMA, "as_of": cutoff, "display_only": True, "live": False,
            "headline": headline, "assets": assets, "families": families,
            "attention": [key for key in FOCUS if key in by_id],
            "attention_basis": bil("Three fixed research lenses; no opportunity ranking.", "三个固定研究视角，不构成机会排名。"),
            "breadth": {"n": n_members if breadth_valid else None, "up": n_up if breadth_valid else None,
                        "state": "available" if breadth_valid else "inconsistent_or_missing"},
            "index_change_1m_pct": number(index.get("chg_1m_pct")), "sources": sources,
            "rates": rates, "fx": {"direction": direction, "direction_state": direction_state,
                                  "direction_as_of": metric_date, "direction_clock": direction_clock, "rows": fx_rows,
                                  "statistics_state": "available" if fx_rows else "date_or_method_unqualified"},
            "chains": chains, "ratios": ratios, "physical": physical, "gold_physical": gold_physical, "hypotheses": {k: [{**h, "label": bil(*h["label"]),
                "mechanism": bil(*h["mechanism"]), "confirm": bil(*h["confirm"]),
                "invalidate": bil(*h["invalidate"]), "applicability": "unassessed",
                "claim_type": "conditional", "revision": HYPOTHESIS_REVISION} for h in v] for k, v in HYPOTHESES.items()},
            "research": {"effect": "export_only", "monitoring_active": False, "schema": CONDITION_SCHEMA},
            "projection_revision": PROJECTION_REVISION,
            "fingerprint": fingerprint({"snapshot": snapshot, "transmission": transmission, "fx": fx, "chains": chain_state,
                                        "ratios": commodity_latest, "physical": physical_context, "projection_revision": PROJECTION_REVISION, "hypotheses": HYPOTHESES})}


def condition_semantics(workspace: dict, asset: str, window: int, hypothesis: str) -> dict:
    """Exact owner field plus an as-saved appendix; unresolved contract identity stays unresolved."""
    selected = next((a for a in workspace.get("assets", []) if a["id"] == asset), None)
    explanation = next((h for h in workspace.get("hypotheses", {}).get(asset, []) if h["id"] == hypothesis), None)
    related = [c for c in workspace.get("chains", []) if c["id"] in CHAIN_IDS.get(asset, ())]
    return {"as_of": workspace.get("as_of"), "basis": "publisher_price_series", "contract": None,
            "expiry_timezone": "UTC", "effect": "export_only", "monitoring_active": False,
            "source_dependencies": deepcopy(workspace.get("sources", {})),
            "requires_monitor_owner_qualification": True,
            "metric_contract": {"source_id": "commodities", "owner_path": SOURCE_PATHS["commodities"],
                "member_key": {"name": asset}, "field": f"velocity.r{window}", "unit": "%",
                "window_sessions": window, "series_identity": None, "contract_roll_method": None,
                "method_reference": "engine/commodity_index.py", "evaluation_qualified": False},
            "as_saved_evidence": {"schema": "mmx.commodities.as_saved_evidence.v1",
                "workspace_fingerprint": workspace.get("fingerprint"), "projection_revision": workspace.get("projection_revision"),
                "asset": deepcopy(selected), "hypothesis": deepcopy(explanation), "chains": deepcopy(related),
                "physical": deepcopy(workspace.get("physical")) if asset == "oil" else None,
                "gold_physical": deepcopy(workspace.get("gold_physical")) if asset == "gold" else None,
                "rates": deepcopy(workspace.get("rates")), "fx": deepcopy(workspace.get("fx")), "ratios": deepcopy(workspace.get("ratios", [])),
                "source_receipts": deepcopy(workspace.get("sources", {})), "live": False}}


def validate_condition(draft: Any, workspace: dict) -> tuple[dict | None, list[str]]:
    """Validate a portable research draft; this does not save, arm, or evaluate a monitor."""
    d = _dict(draft)
    errors = []
    valid_assets = {a["id"] for a in workspace.get("assets", [])}
    asset = d.get("asset")
    if d.get("schema") != CONDITION_SCHEMA:
        errors.append("schema")
    if asset not in valid_assets:
        errors.append("asset")
    if d.get("metric") != "return_pct" or d.get("unit") != "%":
        errors.append("metric_unit")
    if type(d.get("window_sessions")) is not int or d["window_sessions"] not in (5, 20, 60, 252):
        errors.append("window_sessions")
    if d.get("operator") not in ("gt", "gte", "lt", "lte"):
        errors.append("operator")
    if number(d.get("threshold")) is None:
        errors.append("threshold")
    expiry = iso_date(d.get("expires_on"))
    if expiry is None or not workspace.get("as_of") or expiry < workspace["as_of"]:
        errors.append("expires_on")
    if d.get("snapshot_fingerprint") != workspace.get("fingerprint"):
        errors.append("snapshot_fingerprint")
    hypotheses = {h["id"] for h in workspace.get("hypotheses", {}).get(asset, [])} | {"unresolved"}
    if d.get("hypothesis") not in hypotheses:
        errors.append("hypothesis")
    if errors:
        return None, errors
    semantics = condition_semantics(workspace, asset, d["window_sessions"], d["hypothesis"])
    # An imported semantic field cannot be silently replaced with the current one.
    for key, expected in semantics.items():
        if key in d and _safe_json(d[key]) != _safe_json(expected):
            errors.append(key)
    if errors:
        return None, errors
    out = {k: deepcopy(d[k]) for k in ("schema", "asset", "metric", "unit", "window_sessions",
                                      "operator", "threshold", "expires_on", "snapshot_fingerprint", "hypothesis")}
    out.update(semantics)
    return out, []
