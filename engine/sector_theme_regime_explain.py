"""Deterministic EN/ZH regime explanations from source-held quantitative views.

No market tape, LLM, classifier, publication, prediction, rank or trading calls.
Explainers verify the underlying numeric predicate rather than trusting a tag
alone. All outputs are RESEARCH_PREVIEW_ONLY until owner source-use admission.
"""
from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

SCHEMA = "sector_theme_regime_explanation/v1"
INPUT_SCHEMA = "sector_theme_regime_fingerprint/v1"


def _num(raw: object) -> float | None:
    if not isinstance(raw, Mapping) or raw.get("status") != "measured":
        return None
    val = raw.get("value")
    if type(val) not in (int, float):
        return None
    try:
        n = float(val)
    except (TypeError, ValueError, OverflowError):
        return None
    return n if math.isfinite(n) else None


def _bounds(raw: object) -> tuple[float, float] | None:
    if not isinstance(raw, Mapping) or (
        raw.get("bounds_kind") != "identification_bounds_not_confidence_interval"
    ):
        return None
    b = raw.get("identification_bounds")
    if not isinstance(b, (list, tuple)) or len(b) != 2:
        return None
    try:
        if any(type(n) not in (int, float) for n in b):
            return None
        lo, hi = (float(n) for n in b)
    except (OverflowError, TypeError, ValueError):
        return None
    return (lo, hi) if math.isfinite(lo) and math.isfinite(hi) and 0 <= lo <= hi <= 1 else None


def _pct(value: float) -> str:
    return f"{value * 100:+.2f}%"


def _pp(value: float) -> str:
    return f"{value * 100:+.1f} pp"


def _hold(reason: str) -> dict:
    return {
        "schema": SCHEMA, "status": "HELD", "reason": reason,
        "group_cards": [], "single_name_cards": [],
        "source_unmeasured_axes": [],
        "eligible_for_customer_publication": False,
        "predictive_or_trading_authority": False,
    }


def _card(subject: str, tag: str, horizon: str, en: str, zh: str,
          metrics: dict, source_fields: list[str]) -> dict:
    return {
        "subject_id": subject,
        "tag": tag, "horizon": horizon,
        "en": en, "zh": zh,
        "metrics": metrics, "evidence_fields": source_fields,
        "source_status": "unqualified_descriptive_preview",
        "forecast_probability": None,
        "trade_recommendation": None,
    }


def _group_card(tag: str, h: str, row: Mapping) -> dict | None:
    rs = _num(row.get("rs_parent"))
    market_rs = _num(row.get("rs_market"))
    returns = _num((row.get("absolute_trend") or {}).get("group_return"))
    chg = (row.get("breadth_velocity_acceleration") or {})
    delta = _num(chg.get("same_member_uptrend_first_difference"))
    breadth = row.get("participation") or {}
    pos = _bounds(breadth.get("positive_return_breadth"))
    if tag == "positive_parent_rs_narrowing_same_member_breadth":
        if rs is None or delta is None or not (rs > 0 and delta < 0):
            return None
        return _card("group", tag, h,
            f"{h}: relative performance versus parent {_pct(rs)}; same-member uptrend breadth {_pp(delta)}. Participation is narrowing, not a forecast of a top.",
            f"{h}：相对母组表现 {_pct(rs)}；相同成分股的上升趋势广度变动 {_pp(delta)}。参与度收窄，不代表预测见顶。",
            {"rs_parent_frac": rs, "uptrend_breadth_delta_frac": delta},
            ["rs_parent", "breadth_velocity_acceleration.same_member_uptrend_first_difference"])
    if tag == "negative_parent_rs_internal_repair":
        if rs is None or delta is None or not (rs < 0 and delta > 0):
            return None
        return _card("group", tag, h,
            f"{h}: parent-relative performance {_pct(rs)}, while same-member uptrend breadth improved {_pp(delta)}. Internal repair is observed but relative leadership is still negative.",
            f"{h}：相对母组表现 {_pct(rs)}，但相同成分股的上升趋势广度改善 {_pp(delta)}。内部修复已出现，相对表现仍偏弱。",
            {"rs_parent_frac": rs, "uptrend_breadth_delta_frac": delta},
            ["rs_parent", "breadth_velocity_acceleration.same_member_uptrend_first_difference"])
    if tag == "positive_market_rs_with_negative_absolute_return":
        if returns is None or market_rs is None or not (returns < 0 and market_rs > 0):
            return None
        return _card("group", tag, h,
            f"{h}: full-cohort equal-weight return {_pct(returns)}, despite broad-market-relative performance {_pct(market_rs)}. Outperformance is not a positive absolute return.",
            f"{h}：完整成分组等权回报 {_pct(returns)}，但相对大盘表现 {_pct(market_rs)}。跑赢大盘并不等于绝对上涨。",
            {"absolute_return_frac": returns, "rs_market_frac": market_rs},
            ["absolute_trend.group_return", "rs_market"])
    if tag == "majority_positive_participation_proven_by_bounds":
        if pos is None or not pos[0] > .5:
            return None
        return _card("group", tag, h,
            f"{h}: at least {pos[0]*100:.1f}% of eligible members had a positive return; missing quotes cannot reverse the majority.",
            f"{h}：至少 {pos[0]*100:.1f}% 的合资格成分股上涨；即使考虑缺失报价，仍可确认多数上涨。",
            {"positive_return_breadth_lower_bound": pos[0]},
            ["participation.positive_return_breadth.identification_bounds"])
    if tag == "majority_nonpositive_participation_proven_by_bounds":
        if pos is None or not pos[1] < .5:
            return None
        return _card("group", tag, h,
            f"{h}: at most {pos[1]*100:.1f}% of eligible members had positive returns. A majority were flat or negative; the count of strictly declining members is not identified.",
            f"{h}：最多 {pos[1]*100:.1f}% 的合资格成分股上涨；大多数持平或下跌，不一定全是下跌股票。",
            {"positive_return_breadth_upper_bound": pos[1]},
            ["participation.positive_return_breadth.identification_bounds"])
    if tag == "positive_group_return_but_majority_nonpositive":
        if pos is None or returns is None or not (pos[1] < .5 and returns > 0):
            return None
        return _card("group", tag, h,
            f"{h}: full-cohort equal-weight return {_pct(returns)}, yet at most {pos[1]*100:.1f}% of members were positive. Performance is uneven; this alone does not prove concentration by issuer weight.",
            f"{h}：完整成分组等权回报 {_pct(returns)}，但最多 {pos[1]*100:.1f}% 的成分股上涨。表现分化，但不足以证明市值权重集中。",
            {"equal_weight_return_frac": returns, "positive_breadth_upper_bound": pos[1]},
            ["absolute_trend.group_return", "participation.positive_return_breadth"])
    if tag == "apparent_broadening_from_composition_only":
        if chg.get("composition_only") is not True:
            return None
        return _card("group", tag, h,
            f"{h}: headline uptrend breadth improved without a verified newly-uptrending common member. Coverage or cohort composition may explain the increase.",
            f"{h}：总体上升趋势广度上升，但未确认相同成分股新增上升趋势。覆盖率或成分变化可能解释差异。",
            {}, ["breadth_velocity_acceleration.composition_only"])
    return None


def _name_card(mid: str, tag: str, h: str, row: Mapping,
               group_row: Mapping) -> dict | None:
    rs = _num(row.get("rs_parent"))
    ret = _num(row.get("return"))
    grp_rs = _num(group_row.get("rs_market"))
    if tag == "name_outperforming_parent_while_group_lags_market":
        if rs is None or grp_rs is None or not (rs > 0 and grp_rs < 0):
            return None
        return _card(mid, tag, h,
            f"{mid}, {h}: outperformed its parent {_pct(rs)} while the group lagged the broad market {_pct(grp_rs)}. This is a relative divergence, not an entry signal.",
            f"{mid}（{h}）：相对母组跑赢 {_pct(rs)}，但母组相对大盘表现 {_pct(grp_rs)}。这是相对强弱分化，不是买入信号。",
            {"name_rs_parent_frac": rs, "group_rs_market_frac": grp_rs},
            ["single_names.rs_parent", "group.rs_market"])
    if tag == "name_relative_leadership_despite_absolute_decline":
        if rs is None or ret is None or not (rs > 0 and ret < 0):
            return None
        return _card(mid, tag, h,
            f"{mid}, {h}: absolute return {_pct(ret)} and parent-relative performance {_pct(rs)}. Falling less than the parent is not an uptrend.",
            f"{mid}（{h}）：绝对回报 {_pct(ret)}，相对母组表现 {_pct(rs)}。跌幅较小不代表处于上涨趋势。",
            {"name_return_frac": ret, "name_rs_parent_frac": rs},
            ["single_names.return", "single_names.rs_parent"])
    if tag == "name_above_ma50_while_group_majority_not_above":
        b = _bounds((group_row.get("participation") or {}).get("above_ma50_breadth"))
        if row.get("above_ma50") is not True or b is None or not b[1] < .5:
            return None
        basis = group_row.get("moving_average_basis")
        basis_labels = {
            "daily_sessions": ("daily-session bars", "日线"),
            "1m_bars": ("one-minute bars", "1分钟K线"),
            "5m_bars": ("five-minute bars", "5分钟K线"),
            "15m_bars": ("15-minute bars", "15分钟K线"),
            "60m_bars": ("60-minute bars", "60分钟K线"),
            "rth_bars": ("regular-session bars", "常规交易时段K线"),
        }
        if basis not in basis_labels or row.get("ma_basis") != basis:
            return None
        basis_en, basis_zh = basis_labels[basis]
        return _card(mid, tag, h,
            f"{mid}, {h}: above its 50-period moving average ({basis_en}) while at most {b[1]*100:.1f}% of eligible group members were above theirs. Others may be on, not below, the average.",
            f"{mid}（{h}）：股价高于自身50期均线（{basis_zh}），但组内最多 {b[1]*100:.1f}% 的合资格成分股高于各自均线；其余股票可能恰好位于均线上。",
            {"positive_ma50_upper_bound": b[1], "ma_basis": basis},
            ["single_names.above_ma50", "group.participation.above_ma50_breadth"])
    return None


def explain_regime_preview(fingerprint: object) -> dict:
    """Numerically recheck tags and render source-held bilingual evidence cards.

    Unsupported/malformed/forged tags abstain; never copy unverified facet
    prose, assign regime odds or invent reasons/observations from nulls.
    """
    if not isinstance(fingerprint, Mapping) or fingerprint.get("schema") != INPUT_SCHEMA:
        return _hold("invalid_fingerprint")
    authority = fingerprint.get("authority")
    if not isinstance(authority, Mapping) or any(
        authority.get(key) is not False for key in (
            "eligible_for_customer_publication", "predictive_promoted",
            "ranking_authority", "entry_or_sizing_authority", "alert_authority"
        )
    ):
        return _hold("unqualified_publication_or_trading_authority")
    horizons, names = fingerprint.get("horizons"), fingerprint.get("single_names")
    axes, facets = fingerprint.get("axes"), fingerprint.get("facets")
    if (not isinstance(horizons, Mapping) or not isinstance(names, Mapping)
            or not isinstance(axes, Mapping) or not isinstance(facets, list)):
        return _hold("invalid_fingerprint_structure")
    group_cards, single_cards, withheld = [], [], []
    for facet in facets:
        if not isinstance(facet, Mapping) or not isinstance(facet.get("id"), str):
            withheld.append("malformed_group_facet")
            continue
        tag, h = facet["id"], facet.get("horizon")
        if tag == "cross_horizon_parent_rs_sign_conflict":
            signs = {x: _num(row.get("rs_parent")) for x, row in horizons.items()
                     if isinstance(row, Mapping)}
            pos = sorted(x for x, val in signs.items() if val is not None and val > 0)
            neg = sorted(x for x, val in signs.items() if val is not None and val < 0)
            if pos and neg:
                group_cards.append(_card("group", tag, "multi",
                    f"Parent-relative return signs conflict across horizons: positive in {', '.join(pos)}; negative in {', '.join(neg)}. Period returns are not averaged.",
                    f"不同周期相对母组表现方向冲突：{', '.join(pos)} 为正，{', '.join(neg)} 为负。不同周期回报没有混合平均。",
                    {"positive_horizons": pos, "negative_horizons": neg}, ["rs_parent"]))
            else:
                withheld.append(tag)
            continue
        row = horizons.get(h)
        if not isinstance(row, Mapping):
            withheld.append(tag)
            continue
        card = _group_card(tag, h, row)
        if card is None:
            withheld.append(tag)
        else:
            group_cards.append(card)
    for member_id, item in sorted(names.items()):
        if not isinstance(item, Mapping):
            continue
        readings, nfacets = item.get("horizons"), item.get("facets")
        if not isinstance(readings, Mapping) or not isinstance(nfacets, list):
            continue
        for facet in nfacets:
            if not isinstance(facet, Mapping) or not isinstance(facet.get("id"), str):
                withheld.append("malformed_name_facet")
                continue
            tag, h = facet["id"], facet.get("horizon")
            if tag == "name_parent_rs_sign_conflict_across_horizons":
                signs = {x: _num(row.get("rs_parent")) for x, row in readings.items()
                         if isinstance(row, Mapping)}
                pos = sorted(x for x, value in signs.items() if value is not None and value > 0)
                neg = sorted(x for x, value in signs.items() if value is not None and value < 0)
                if pos and neg:
                    single_cards.append(_card(member_id, tag, "multi",
                        f"{member_id}: parent-relative strength changes sign across timeframes ({', '.join(pos)} positive; {', '.join(neg)} negative).",
                        f"{member_id}：相对母组强弱在不同周期改变符号（{', '.join(pos)} 为正；{', '.join(neg)} 为负）。",
                        {"positive_horizons": pos, "negative_horizons": neg},
                        ["single_names.rs_parent"]))
                else:
                    withheld.append(tag)
                continue
            row = readings.get(h)
            group_row = horizons.get(h)
            if not isinstance(row, Mapping) or not isinstance(group_row, Mapping):
                withheld.append(tag)
                continue
            card = _name_card(member_id, tag, h, row, group_row)
            if card is None:
                withheld.append(tag)
            else:
                single_cards.append(card)
    missing = sorted(k for k, value in axes.items()
                     if isinstance(value, Mapping) and value.get("status") != "measured")
    return {
        "schema": SCHEMA, "status": "RESEARCH_PREVIEW_ONLY",
        "group_cards": group_cards, "single_name_cards": single_cards,
        "source_unmeasured_axes": missing,
        "withheld_unverified_facets": sorted(set(withheld)),
        "message_en": "Observed descriptions only; source rights and future-event probabilities are not qualified.",
        "message_zh": "仅为已观察的描述；数据使用权限与未来事件概率尚未通过验证。",
        "eligible_for_customer_publication": False,
        "predictive_or_trading_authority": False,
    }
