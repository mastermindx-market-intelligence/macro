"""Pure Bonds explanation projection.

This module is deliberately a *display* projection over existing canonical
contracts.  It does not own a score, probability, regime, signal, alert, data
source, or market-state transition.

Inputs are mappings already owned by:
- data/bonds/bond_health.json
- data/transmission/latest.json
- optionally data/regime/latest.json

The output makes competing mechanisms inspectable as Supports / Contradicts /
Missing evidence, preserves source dates and horizons, and fails closed when the
inputs cannot be joined safely.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any, Mapping


SCHEMA = "mastermind.bonds_explanation_view.v1"


def _pair(en: str, zh: str) -> dict[str, str]:
    return {"en": en, "zh": zh}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _number(value: Any) -> float | None:
    """Finite real number, but never bool (True must not become 1bp)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _boolean(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _date(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    # Contract dates may include a time suffix; mechanism joins use only the
    # calendar-date identity. Impossible dates fail closed rather than becoming
    # a distinct-looking but invalid source date.
    s = value.strip()
    if len(s) < 10 or s[4:5] != "-" or s[7:8] != "-":
        return None
    ymd = s[:10]
    try:
        return date.fromisoformat(ymd).isoformat()
    except ValueError:
        return None


def _direction(change: Any) -> str | None:
    value = _number(change)
    if value is None:
        return None
    if value > 0:
        return "steepening"
    if value < 0:
        return "flattening"
    return "unchanged"


def _evidence(
    family: str,
    status: str,
    claim_en: str,
    claim_zh: str,
    *,
    value: Any = None,
    unit: str | None = None,
    horizon: str | None = None,
    source: str | None = None,
    source_as_of: str | None = None,
    basis: str = "observed",
    observed: Mapping[str, Any] | None = None,
    limit_en: str | None = None,
    limit_zh: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "family": family,
        "status": status,
        "claim": _pair(claim_en, claim_zh),
        "value": value,
        "unit": unit,
        "horizon": horizon,
        "source": source,
        "source_as_of": source_as_of,
        "basis": basis,
    }
    if observed is not None:
        out["observed"] = dict(observed)
    if limit_en or limit_zh:
        out["limit"] = _pair(limit_en or "", limit_zh or "")
    return out


def _missing(
    family: str,
    claim_en: str,
    claim_zh: str,
    *,
    source: str | None = None,
    source_as_of: str | None = None,
) -> dict[str, Any]:
    return _evidence(
        family,
        "missing",
        claim_en,
        claim_zh,
        value=None,
        source=source,
        source_as_of=source_as_of,
        basis="missing",
    )


def _split(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        "supports": [x for x in items if x["status"] == "supports"],
        "contradicts": [x for x in items if x["status"] == "contradicts"],
        "missing": [x for x in items if x["status"] == "missing"],
    }


def _dates_align(*dates: str | None) -> bool:
    return bool(dates) and all(value is not None for value in dates) and len(set(dates)) == 1


def _withhold_row(row: dict[str, Any], reason: dict[str, str]) -> None:
    """Withhold only the joined conclusion; preserve its independently dated evidence."""
    row["state"] = "withheld"
    row["summary"] = reason
    row["withheld_reason"] = reason


def _source_status(
    bond: Mapping[str, Any],
    transmission: Mapping[str, Any],
    regime: Mapping[str, Any],
) -> dict[str, Any]:
    be = _mapping(transmission.get("breakeven_decomp"))
    systemic = _mapping(_mapping(regime.get("conditions")).get("systemic_stress"))
    dates = {
        "bond_health": _date(bond.get("as_of")),
        "transmission": _date(transmission.get("asof")),
        "breakevens": _date(be.get("as_of")),
        "systemic_stress": _date(regime.get("asof")) if systemic else None,
    }
    required_date_keys = ["bond_health", "transmission"]
    # Optional evidence families become date-required only when the family is
    # actually populated.  An absent optional family remains a local Missing
    # state; a populated-but-undated family may not borrow another owner's date.
    if be:
        required_date_keys.append("breakevens")
    if systemic:
        required_date_keys.append("systemic_stress")
    missing_dates = [key for key in required_date_keys if dates.get(key) is None]
    present = [dates[key] for key in required_date_keys if dates.get(key) is not None]
    if missing_dates:
        state = "insufficient"
    elif len(set(present)) > 1:
        state = "date_mismatch"
    else:
        state = "aligned"
    as_of = dates["bond_health"] if state == "aligned" else None
    return {"state": state, "dates": dates, "missing_dates": missing_dates, "as_of": as_of}


def _curve_horizons(transmission: Mapping[str, Any]) -> dict[str, Any]:
    as_of = _date(transmission.get("asof"))
    yc = _mapping(transmission.get("yield_curve"))
    regime = _mapping(yc.get("regime"))
    slopes = _mapping(yc.get("slopes"))
    s2 = _mapping(slopes.get("2s10s"))
    s3 = _mapping(slopes.get("3m10y"))

    current_change = _number(regime.get("slope_chg_bp"))
    current_window = _number(regime.get("window_d"))
    longer_change = _number(s2.get("chg_63d_bp"))
    recession_change = _number(s3.get("chg_63d_bp"))

    current = {
        "slope": "2s10s",
        "horizon": f"{int(current_window)}d" if current_window is not None else None,
        "change_bp": current_change,
        "direction": _direction(current_change),
        "source_as_of": as_of,
    }
    longer = {
        "slope": "2s10s",
        "horizon": "63d",
        "change_bp": longer_change,
        "direction": _direction(longer_change),
        "source_as_of": as_of,
    }
    context = [{
        "slope": "3m10y",
        "horizon": "63d",
        "change_bp": recession_change,
        "direction": _direction(recession_change),
        "source_as_of": as_of,
        "meaning": _pair(
            "recession slope; context only, not the same basis as 2s10s",
            "衰退斜率；仅作背景，不能与2s10s视为同一口径",
        ),
    }]

    if current["direction"] is None or longer["direction"] is None:
        state = "insufficient"
        explanation = _pair(
            "The same-slope windows cannot be compared because one change is unavailable.",
            "同一斜率的不同窗口无法比较，因为至少一个变动值缺失。",
        )
    elif current["direction"] == longer["direction"]:
        state = "aligned"
        current_days = int(current_window)
        explanation = _pair(
            f"The 2s10s directions align across the named {current_days}-day and 63-day windows.",
            f"2s10s在明确标注的{current_days}日与63日窗口中方向一致。",
        )
    else:
        state = "disagreement"
        explanation = _pair(
            "The same 2s10s slope points in different directions across different windows; keep both horizons visible.",
            "同一2s10s斜率在不同窗口中方向相反；应同时保留两个期限。",
        )
    return {
        "state": state,
        "current": current,
        "longer_same_slope": longer,
        "context": context,
        "explanation": explanation,
    }


def _policy_real_rate(
    bond: Mapping[str, Any],
    transmission: Mapping[str, Any],
) -> dict[str, Any]:
    as_of_t = _date(transmission.get("asof"))
    as_of_b = _date(bond.get("as_of"))
    yc = _mapping(transmission.get("yield_curve"))
    momentum = _mapping(yc.get("momentum"))
    fed = _mapping(bond.get("fed_path"))
    real = _number(momentum.get("real10y_speed_bp"))
    front = _number(momentum.get("front2y_speed_bp"))
    implied = _number(fed.get("implied_bp_12m"))
    window = _number(momentum.get("window_d"))
    horizon = f"{int(window)}d" if window is not None else None
    items: list[dict[str, Any]] = []

    if real is None:
        items.append(_missing("real_rates", "Real-rate speed is unavailable.", "实际利率速度不可用.", source="yield_curve.momentum.real10y_speed_bp", source_as_of=as_of_t))
    else:
        status = "supports" if real > 0 else "contradicts"
        items.append(_evidence(
            "real_rates", status,
            f"10y real yields changed {real:+.0f}bp over the selected window.",
            f"10年期实际收益率在所选窗口变动{real:+.0f}基点。",
            value=real, unit="bp", horizon=horizon,
            source="yield_curve.momentum.real10y_speed_bp", source_as_of=as_of_t,
        ))

    if front is None:
        items.append(_missing("front_end", "Front-end yield speed is unavailable.", "前端收益率速度不可用。", source="yield_curve.momentum.front2y_speed_bp", source_as_of=as_of_t))
    else:
        status = "supports" if front > 0 else "contradicts"
        items.append(_evidence(
            "front_end", status,
            f"2y yields changed {front:+.0f}bp over the selected window.",
            f"2年期收益率在所选窗口变动{front:+.0f}基点。",
            value=front, unit="bp", horizon=horizon,
            source="yield_curve.momentum.front2y_speed_bp", source_as_of=as_of_t,
        ))

    if implied is None:
        items.append(_missing("policy_path", "The futures-implied 12m policy change is unavailable.", "期货隐含的12个月政策利率变动不可用。", source="fed_path.implied_bp_12m", source_as_of=as_of_b))
    else:
        status = "supports" if implied > 0 else "contradicts"
        items.append(_evidence(
            "policy_path", status,
            f"Fed-funds futures price a {implied:+.0f}bp 12-month policy-rate change.",
            f"联邦基金期货定价未来12个月政策利率变动{implied:+.0f}基点。",
            value=implied, unit="bp", horizon="12m",
            source="fed_path.implied_bp_12m", source_as_of=as_of_b,
            basis="market_price",
            limit_en="A futures-implied path is a market price, not a forecast edge.",
            limit_zh="期货隐含路径是市场价格，不是预测优势。",
        ))

    parts = _split(items)
    decisive = {"real_rates", "front_end", "policy_path"}
    missing = {x["family"] for x in parts["missing"]}
    supports = {x["family"] for x in parts["supports"]}
    contradicts = {x["family"] for x in parts["contradicts"]}
    if decisive & missing:
        state = "insufficient"
    elif decisive <= supports:
        state = "supported"
    elif decisive <= contradicts:
        state = "contradicted"
    else:
        state = "mixed"
    summary = {
        "supported": _pair("Real-rate, front-end and priced policy-path evidence all point toward tighter rates pressure.", "实际利率、前端与市场定价的政策路径共同指向更紧的利率压力。"),
        "contradicted": _pair("Real-rate, front-end and priced policy-path evidence do not support a tightening mechanism.", "实际利率、前端与市场定价的政策路径不支持紧缩机制。"),
        "mixed": _pair("Rates and policy-path evidence disagree; do not force one tightening narrative.", "利率与政策路径证据不一致，不应强行归为单一紧缩叙事。"),
        "insufficient": _pair("Required rates or policy-path evidence is missing.", "必要的利率或政策路径证据缺失。"),
    }[state]
    return {"key": "policy_real_rate", "label": _pair("Policy / real-rate tightening", "政策 / 实际利率紧缩"), "state": state, "summary": summary, **parts}


def _growth_cuts(
    bond: Mapping[str, Any],
    transmission: Mapping[str, Any],
) -> dict[str, Any]:
    as_of_t = _date(transmission.get("asof"))
    as_of_b = _date(bond.get("as_of"))
    yc = _mapping(transmission.get("yield_curve"))
    recession = _mapping(yc.get("recession"))
    momentum = _mapping(yc.get("momentum"))
    credit = _mapping(_mapping(bond.get("pillars")).get("credit"))
    fed = _mapping(bond.get("fed_path"))
    items: list[dict[str, Any]] = []

    risk = recession.get("risk")
    n_flags = _number(recession.get("n_flags"))
    ntfs = _number(recession.get("ntfs"))
    if not isinstance(risk, str) or n_flags is None or ntfs is None:
        items.append(_missing("recession", "Recession-state evidence is incomplete.", "衰退状态证据不完整。", source="yield_curve.recession", source_as_of=as_of_t))
    else:
        risk_l = risk.lower()
        support = risk_l in {"high", "elevated"} or n_flags >= 2 or ntfs < 0
        contradict = risk_l == "low" and n_flags == 0 and ntfs >= 0
        status = "supports" if support else "contradicts" if contradict else "missing"
        if status == "missing":
            items.append(_missing("recession", "Recession evidence is present but does not map to a reviewed directional state.", "衰退证据存在，但无法映射到已审查的方向状态。", source="yield_curve.recession", source_as_of=as_of_t))
        else:
            items.append(_evidence(
                "recession", status,
                f"Recession risk is {risk_l}; flags={int(n_flags)}, NTFS={ntfs:+.2f}.",
                f"衰退风险为{risk_l}；标志={int(n_flags)}，NTFS={ntfs:+.2f}。",
                source="yield_curve.recession", source_as_of=as_of_t,
                observed={"risk": risk_l, "n_flags": int(n_flags), "ntfs": ntfs},
            ))

    front = _number(momentum.get("front2y_speed_bp"))
    window = _number(momentum.get("window_d"))
    horizon = f"{int(window)}d" if window is not None else None
    if front is None:
        items.append(_missing("front_end", "Front-end repricing is unavailable.", "前端重新定价不可用。", source="yield_curve.momentum.front2y_speed_bp", source_as_of=as_of_t))
    else:
        status = "supports" if front < 0 else "contradicts"
        items.append(_evidence("front_end", status, f"2y yield speed is {front:+.0f}bp.", f"2年期收益率速度为{front:+.0f}基点。", value=front, unit="bp", horizon=horizon, source="yield_curve.momentum.front2y_speed_bp", source_as_of=as_of_t))

    implied = _number(fed.get("implied_bp_12m"))
    if implied is None:
        items.append(_missing("policy_path", "The futures-implied policy path is unavailable.", "期货隐含政策路径不可用。", source="fed_path.implied_bp_12m", source_as_of=as_of_b))
    else:
        status = "supports" if implied < 0 else "contradicts"
        items.append(_evidence(
            "policy_path", status,
            f"Fed-funds futures price {implied:+.0f}bp over 12 months.",
            f"联邦基金期货定价未来12个月变动{implied:+.0f}基点。",
            value=implied, unit="bp", horizon="12m", source="fed_path.implied_bp_12m", source_as_of=as_of_b, basis="market_price",
            limit_en="Market pricing is reactive context, not a recession probability.",
            limit_zh="市场定价是反应性背景，不是衰退概率。",
        ))

    direction = credit.get("direction")
    band = credit.get("distress_band")
    if not isinstance(direction, str) or not isinstance(band, str):
        items.append(_missing("credit", "Credit-spread direction or band is unavailable.", "信用利差方向或区间不可用。", source="pillars.credit", source_as_of=as_of_b))
    else:
        widening = direction.lower() == "widening"
        status = "supports" if widening else "contradicts"
        items.append(_evidence(
            "credit", status,
            f"Credit is {direction.lower()} but remains in the {band.lower()} band.",
            f"信用利差{direction.lower()}，但仍处于{band.lower()}区间。",
            source="pillars.credit", source_as_of=as_of_b,
            observed={"direction": direction.lower(), "band": band.lower(), "hy_oas": _number(credit.get("hy_oas")), "ig_oas": _number(credit.get("ig_oas"))},
        ))

    parts = _split(items)
    smap = {x["family"]: x["status"] for x in items}
    required = ("recession", "front_end", "policy_path")
    if any(smap.get(k) == "missing" for k in required):
        state = "insufficient"
    elif smap.get("recession") == "supports" and any(smap.get(k) == "supports" for k in ("front_end", "policy_path", "credit")):
        state = "supported"
    elif all(smap.get(k) == "contradicts" for k in required):
        state = "contradicted"
    else:
        state = "mixed"
    summary = {
        "supported": _pair("Growth-break evidence is being confirmed by at least one policy, front-end or credit channel.", "增长下行证据至少得到政策、前端或信用渠道之一的确认。"),
        "contradicted": _pair("The recession, front-end and policy-path owners do not confirm a cut-driven growth break.", "衰退、前端与政策路径的权威证据均未确认由降息驱动的增长破裂。"),
        "mixed": _pair("Growth and financing evidence disagree; preserve the conflict instead of calling a growth break.", "增长与融资证据不一致，应保留冲突而不是直接判定增长破裂。"),
        "insufficient": _pair("Required recession, front-end or policy-path evidence is missing.", "必要的衰退、前端或政策路径证据缺失。"),
    }[state]
    return {"key": "growth_cuts", "label": _pair("Growth / cut repricing", "增长 / 降息重新定价"), "state": state, "summary": summary, **parts}


def _inflation_reflation(transmission: Mapping[str, Any]) -> dict[str, Any]:
    as_of_t = _date(transmission.get("asof"))
    be = _mapping(transmission.get("breakeven_decomp"))
    as_of_be = _date(be.get("as_of"))
    velocity = _mapping(be.get("velocity_bp"))
    be63 = _number(velocity.get("chg_63d_bp"))
    yc = _mapping(transmission.get("yield_curve"))
    momentum = _mapping(yc.get("momentum"))
    real = _number(momentum.get("real10y_speed_bp"))
    nominal = _number(momentum.get("nom10y_speed_bp"))
    items: list[dict[str, Any]] = []

    if be63 is None:
        items.append(_missing("breakevens", "63-day breakeven change is unavailable.", "63日盈亏平衡变动不可用。", source="breakeven_decomp.velocity_bp.chg_63d_bp", source_as_of=as_of_be))
    else:
        status = "supports" if be63 > 0 else "contradicts"
        items.append(_evidence(
            "breakevens", status,
            f"10y breakeven inflation changed {be63:+.0f}bp over 63 days.",
            f"10年期盈亏平衡通胀在63日内变动{be63:+.0f}基点。",
            value=be63, unit="bp", horizon="63d",
            source="breakeven_decomp.velocity_bp.chg_63d_bp", source_as_of=as_of_be,
            observed={"direction": be.get("direction"), "trend": be.get("trend"), "cause": _mapping(be.get("cause_badge")).get("cause")},
            limit_en="Breakeven movement is descriptive context, not a forward risk signal.",
            limit_zh="盈亏平衡变动是描述性背景，不是前瞻风险信号。",
        ))

    if real is None or nominal is None or be63 is None:
        items.append(_missing("decomposition", "Real-versus-inflation move decomposition is incomplete.", "实际利率与通胀补偿的变动分解不完整。", source="yield_curve.momentum + breakeven_decomp", source_as_of=as_of_t))
    elif as_of_t is None or as_of_be is None or as_of_t != as_of_be:
        items.append(_missing(
            "decomposition",
            "Real-yield and breakeven calculation dates do not match, so their move sizes are not joined.",
            "实际收益率与盈亏平衡的计算日期不一致，因此不合并比较其变动幅度。",
            source="yield_curve.momentum + breakeven_decomp",
            source_as_of=None,
        ))
    else:
        real_dominant = abs(real) > abs(be63)
        status = "contradicts" if real_dominant else "supports"
        claim_en = (
            f"Real-yield repricing ({real:+.0f}bp) is dominant versus breakevens ({be63:+.0f}bp); inflation is not the dominant current driver."
            if real_dominant else
            f"Breakeven repricing ({be63:+.0f}bp) is at least as large as the real-yield move ({real:+.0f}bp)."
        )
        claim_zh = (
            f"实际收益率重新定价（{real:+.0f}基点）大于盈亏平衡变动（{be63:+.0f}基点）；通胀不是当前主导驱动。"
            if real_dominant else
            f"盈亏平衡重新定价（{be63:+.0f}基点）不小于实际收益率变动（{real:+.0f}基点）。"
        )
        items.append(_evidence(
            "decomposition", status, claim_en, claim_zh,
            source="yield_curve.momentum + breakeven_decomp", source_as_of=as_of_t,
            observed={"real_yield_bp": real, "breakeven_bp": be63, "nominal_yield_bp": nominal},
        ))

    parts = _split(items)
    if parts["supports"] and parts["contradicts"]:
        state = "mixed"
    elif parts["supports"]:
        state = "supported"
    elif parts["contradicts"]:
        state = "contradicted"
    else:
        state = "insufficient"
    summary = {
        "supported": _pair("Inflation compensation is the cleaner observed rates contribution.", "通胀补偿是当前更清晰的利率贡献来源。"),
        "contradicted": _pair("Observed rates decomposition does not support inflation as the current driver.", "观察到的利率分解不支持通胀作为当前驱动。"),
        "mixed": _pair("Inflation compensation contributes, but real-rate repricing is larger; treat reflation as secondary, not the whole move.", "通胀补偿有所贡献，但实际利率重新定价更大；应将再通胀视为次要因素，而不是全部解释。"),
        "insufficient": _pair("Breakeven or decomposition evidence is missing.", "盈亏平衡或分解证据缺失。"),
    }[state]
    return {"key": "inflation_reflation", "label": _pair("Inflation / reflation", "通胀 / 再通胀"), "state": state, "summary": summary, **parts}


def _term_premium_supply(
    bond: Mapping[str, Any],
    transmission: Mapping[str, Any],
) -> dict[str, Any]:
    as_of_t = _date(transmission.get("asof"))
    as_of_b = _date(bond.get("as_of"))
    yc = _mapping(transmission.get("yield_curve"))
    yreg = _mapping(yc.get("regime"))
    ri = _mapping(_mapping(bond.get("pillars")).get("real_inflation"))
    direction = yreg.get("term_premium_dir")
    change = _number(yreg.get("term_premium_chg_bp"))
    window = _number(yreg.get("window_d"))
    level = _number(ri.get("term_premium"))
    items: list[dict[str, Any]] = []

    if not isinstance(direction, str) or change is None or level is None:
        items.append(_missing("term_premium_model", "Kim-Wright term-premium evidence is incomplete.", "Kim-Wright期限溢价模型证据不完整。", source="yield_curve.regime + pillars.real_inflation.term_premium", source_as_of=as_of_t))
    elif as_of_t is None or as_of_b is None or as_of_t != as_of_b:
        items.append(_missing(
            "term_premium_model",
            "Term-premium level and change come from different calculation dates, so they are not joined.",
            "期限溢价水平与变动来自不同计算日期，因此不合并解释。",
            source="yield_curve.regime + pillars.real_inflation.term_premium",
            source_as_of=None,
        ))
    else:
        d = direction.lower()
        status = "supports" if d == "rising" and change > 0 else "contradicts" if d == "falling" and change < 0 else "missing"
        if status == "missing":
            items.append(_missing("term_premium_model", "The model estimate is present but does not map to a reviewed directional state.", "模型估值存在，但无法映射到已审查的方向状态。", source="yield_curve.regime", source_as_of=as_of_t))
        else:
            items.append(_evidence(
                "term_premium_model", status,
                f"Kim-Wright term premium is {level:.2f}pp and changed {change:+.0f}bp over the regime window.",
                f"Kim-Wright期限溢价为{level:.2f}个百分点，在状态窗口内变动{change:+.0f}基点。",
                value=change, unit="bp",
                horizon=f"{int(window)}d" if window is not None else None,
                source="yield_curve.regime.term_premium_chg_bp", source_as_of=as_of_t,
                basis="model_estimate",
                observed={"model": "Kim-Wright", "level_pp": level, "direction": d},
                limit_en="Term premium is model-estimated, not observed fact.",
                limit_zh="期限溢价是模型估值，不是直接观察事实。",
            ))

    items.append(_missing(
        "second_term_premium_model",
        "A second independent term-premium model is not supplied, so no model band is available.",
        "未提供第二个独立期限溢价模型，因此无法形成模型区间。",
        source="not supplied by current Bonds contracts", source_as_of=as_of_b,
    ))
    items.append(_missing(
        "supply_auction",
        "Direct Treasury supply / auction confirmation is not supplied to this projection.",
        "本投影未提供直接的国债供给 / 拍卖确认。",
        source="not supplied by current Bonds contracts", source_as_of=as_of_b,
    ))

    parts = _split(items)
    if any(x["family"] == "term_premium_model" for x in parts["supports"]):
        state = "supported"
    elif any(x["family"] == "term_premium_model" for x in parts["contradicts"]):
        state = "contradicted"
    else:
        state = "insufficient"
    summary = {
        "supported": _pair("Term-premium model evidence supports duration repricing, while supply confirmation and a second model remain missing.", "期限溢价模型证据支持久期重新定价，但供给确认与第二模型仍缺失。"),
        "contradicted": _pair("The term-premium model does not support a rising duration-compensation mechanism.", "期限溢价模型不支持期限补偿上升机制。"),
        "insufficient": _pair("Term-premium model evidence is incomplete.", "期限溢价模型证据不完整。"),
    }[state]
    return {"key": "term_premium_supply", "label": _pair("Term premium / supply", "期限溢价 / 供给"), "state": state, "summary": summary, **parts}


def _funding_liquidity(
    bond: Mapping[str, Any],
    regime: Mapping[str, Any],
) -> dict[str, Any]:
    as_of_b = _date(bond.get("as_of"))
    as_of_g = _date(regime.get("asof"))
    stress = _mapping(_mapping(bond.get("pillars")).get("stress"))
    systemic = _mapping(_mapping(regime.get("conditions")).get("systemic_stress"))
    items: list[dict[str, Any]] = []

    band = stress.get("move_band")
    pct = _number(stress.get("move_pctile"))
    move = _number(stress.get("move"))
    if not isinstance(band, str):
        items.append(_missing("rates_vol", "MOVE absolute stress band is unavailable.", "MOVE绝对压力区间不可用。", source="pillars.stress", source_as_of=as_of_b))
    else:
        b = band.lower()
        support = b in {"elevated", "crisis", "stress", "stressed"}
        status = "supports" if support else "contradicts" if b in {"calm", "normal"} else "missing"
        if status == "missing":
            items.append(_missing("rates_vol", "MOVE band is present but outside the reviewed vocabulary.", "MOVE区间存在，但不在已审查词表中。", source="pillars.stress.move_band", source_as_of=as_of_b))
        else:
            if status == "contradicts" and pct is not None and pct >= 0.9:
                en = f"MOVE remains in the {b} absolute band despite a high percentile ({pct:.1%}); relative elevation alone does not confirm plumbing stress."
                zh = f"MOVE绝对区间仍为{b}，尽管分位数较高（{pct:.1%}）；相对偏高本身不能确认资金管道压力。"
            else:
                en = f"MOVE is in the {b} absolute band."
                zh = f"MOVE处于{b}绝对区间。"
            items.append(_evidence(
                "rates_vol", status, en, zh,
                value=move, source="pillars.stress.move_band", source_as_of=as_of_b,
                observed={"band": b, "percentile": pct, "move": move},
            ))

    repo = _boolean(stress.get("repo_stress"))
    scarcity = _boolean(stress.get("reserve_scarcity"))
    if repo is None or scarcity is None:
        items.append(_missing("repo", "Repo-stress or reserve-scarcity state is unavailable.", "回购压力或准备金稀缺状态不可用。", source="pillars.stress", source_as_of=as_of_b))
    else:
        support = repo or scarcity
        items.append(_evidence(
            "repo", "supports" if support else "contradicts",
            "Repo/reserve plumbing is flagging stress." if support else "Repo stress and reserve scarcity are both off.",
            "回购/准备金资金管道正在发出压力信号。" if support else "回购压力与准备金稀缺均未触发。",
            source="pillars.stress.repo_stress + reserve_scarcity", source_as_of=as_of_b,
            observed={"repo_stress": repo, "reserve_scarcity": scarcity, "sofr_iorb_bp": _number(stress.get("sofr_iorb_bp"))},
        ))

    state = systemic.get("state")
    if not isinstance(state, str):
        items.append(_missing("systemic_funding", "Systemic funding-stress state is unavailable.", "系统性资金压力状态不可用。", source="conditions.systemic_stress", source_as_of=as_of_g))
    else:
        s = state.lower()
        support = s in {"elevated", "stress", "stressed", "crisis"}
        contradict = s == "calm"
        if support or contradict:
            items.append(_evidence(
                "systemic_funding", "supports" if support else "contradicts",
                f"OFR systemic-stress state is {s}.",
                f"OFR系统性压力状态为{s}。",
                source="conditions.systemic_stress", source_as_of=as_of_g,
                observed={
                    "state": s,
                    "trend": systemic.get("trend"),
                    "ofr_fsi": _number(systemic.get("ofr_fsi")),
                    "funding_component": _number(_mapping(systemic.get("functional")).get("funding")),
                },
                limit_en="OFR FSI is a coincident stress gauge, not a lead signal.",
                limit_zh="OFR FSI是同步压力指标，不是领先信号。",
            ))
        else:
            items.append(_missing("systemic_funding", "Systemic-stress state is outside the reviewed vocabulary.", "系统性压力状态不在已审查词表中。", source="conditions.systemic_stress.state", source_as_of=as_of_g))

    items.append(_missing(
        "market_depth_collateral",
        "Market-depth, collateral and margin/liquidation evidence is not supplied to this projection.",
        "本投影未提供市场深度、抵押品以及保证金/清算证据。",
        source="not supplied by current Bonds contracts", source_as_of=as_of_b,
    ))

    parts = _split(items)
    decisive = {"rates_vol", "repo", "systemic_funding"}
    smap = {x["family"]: x["status"] for x in items}
    if all(smap.get(k) == "supports" for k in decisive):
        state_out = "supported"
    elif all(smap.get(k) == "contradicts" for k in decisive):
        state_out = "contradicted"
    elif any(smap.get(k) == "missing" for k in decisive):
        state_out = "insufficient"
    else:
        state_out = "mixed"
    summary = {
        "supported": _pair("Rates volatility, repo/reserve plumbing and systemic stress all confirm funding pressure.", "利率波动、回购/准备金管道与系统性压力共同确认资金压力。"),
        "contradicted": _pair("Available rates-vol and plumbing owners do not confirm acute funding stress.", "现有利率波动与资金管道权威证据未确认急性资金压力。"),
        "mixed": _pair("Funding-stress owners disagree; preserve the disagreement.", "资金压力权威证据不一致，应保留分歧。"),
        "insufficient": _pair("One or more required funding-stress owners are unavailable.", "一个或多个必要的资金压力权威来源不可用。"),
    }[state_out]
    return {"key": "funding_liquidity", "label": _pair("Funding / liquidity stress", "资金 / 流动性压力"), "state": state_out, "summary": summary, **parts}


def build_bonds_explanation_view(
    bond_health: Mapping[str, Any] | None,
    transmission: Mapping[str, Any] | None,
    regime: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project canonical Bonds evidence into competing explanation rows.

    The function is pure: no I/O, clock read, network, scoring, forecasting or
    mutation. Date admission is mechanism-local: a stale or undated optional
    family may withhold only the joined conclusion that consumes it, while
    independent mechanism rows and every dated evidence item remain usable.
    """
    bond = _mapping(bond_health)
    trans = _mapping(transmission)
    reg = _mapping(regime)
    status = _source_status(bond, trans, reg)
    mechanisms = [
        _policy_real_rate(bond, trans),
        _growth_cuts(bond, trans),
        _inflation_reflation(trans),
        _term_premium_supply(bond, trans),
        _funding_liquidity(bond, reg),
    ]
    rows = {row["key"]: row for row in mechanisms}
    dates = status["dates"]
    bond_date = dates["bond_health"]
    transmission_date = dates["transmission"]
    breakeven_date = dates["breakevens"]
    systemic_date = dates["systemic_stress"]
    breakevens_present = bool(_mapping(trans.get("breakeven_decomp")))
    systemic_present = bool(_mapping(_mapping(reg.get("conditions")).get("systemic_stress")))

    bond_trans_reason = _pair(
        "This mechanism joins Bonds and transmission evidence whose calculation dates are missing or different; inspect the dated evidence separately.",
        "该机制需要合并债券与传导证据，但其计算日期缺失或不一致；请分别查看带日期的证据。",
    )
    if not _dates_align(bond_date, transmission_date):
        for key in ("policy_real_rate", "growth_cuts", "term_premium_supply"):
            _withhold_row(rows[key], bond_trans_reason)

    if transmission_date is None or (
        breakevens_present and not _dates_align(transmission_date, breakeven_date)
    ):
        _withhold_row(
            rows["inflation_reflation"],
            _pair(
                "This inflation interpretation joins rates and breakeven evidence whose calculation dates are missing or different; keep the readings separate.",
                "该通胀解释需要合并利率与盈亏平衡证据，但其计算日期缺失或不一致；应分别保留这些读数。",
            ),
        )

    if bond_date is None or (
        systemic_present and not _dates_align(bond_date, systemic_date)
    ):
        _withhold_row(
            rows["funding_liquidity"],
            _pair(
                "This funding interpretation joins Bonds plumbing and systemic-stress evidence whose calculation dates are missing or different; keep the readings separate.",
                "该资金解释需要合并债券资金管道与系统性压力证据，但其计算日期缺失或不一致；应分别保留这些读数。",
            ),
        )

    withheld_rows = [row for row in mechanisms if row["state"] == "withheld"]
    withheld_reason = None
    if len(withheld_rows) == len(mechanisms):
        withheld_reason = _pair(
            "Every mechanism join is withheld because its required calculation dates are missing or incompatible; dated evidence remains visible.",
            "所有机制的联合结论均因必要计算日期缺失或不兼容而暂不输出；带日期的证据仍保留显示。",
        )

    return {
        "schema": SCHEMA,
        "as_of": status["as_of"],
        "source_status": status,
        "curve_horizons": _curve_horizons(trans),
        "mechanisms": mechanisms,
        "withheld_reason": withheld_reason,
    }
