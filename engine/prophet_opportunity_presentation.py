"""Display an already-selected, already-entitled US board row.

This module does not select candidates, assign a strategy, refresh an assessment,
join plans, request quotes, or grant entry permission. Its output is a presentation
value, never a native receipt. Integrators retain the existing selection and access
owners and must supply an occurrence id and the real originating view's links.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from math import isfinite
import re
from xml.etree import ElementTree
from urllib.parse import urlencode


_ENTRY = {
    "buy_now": ("buy", "Buy", "买入"),
    "partial": ("buy", "Buy · partial", "买入 · 部分"),
    "buy_soon": ("near", "Near", "临近"),
    "await_confluence": ("near", "Awaiting confirmation", "等待确认"),
    "hold": ("hold", "Hold", "持有"),
    "topping": ("hold", "Topping", "顶部形成中"),
    "exit": ("avoid", "Exit", "退出"),
    "avoid": ("avoid", "Avoid", "回避"),
    "extended": ("wait", "Wait · extended", "等待 · 已延伸"),
    "blocked": ("wait", "Wait · blocked", "等待 · 受阻"),
    "wait": ("wait", "Wait", "等待"),
    "watch": ("wait", "Watch", "观察"),
    "wait_pullback": ("wait", "Wait · pullback", "等待 · 回调"),
    "bounce_wait": ("wait", "Wait · countertrend", "等待 · 逆势反弹"),
}
_LANE = {"bottoming": 0, "recovery": 1, "continuation": 2, "trend": 3}
_STAGES = (("Bottoming", "筑底"), ("Turning", "转折"),
           ("Ready", "就绪"), ("Trend", "趋势"))
_FAMILY_LABELS = {
    "F1_TECHNICAL_CONFLUENCE": ("Technical agreement", "技术共振"),
    "F2_MOMENTUM_EXTENSION": ("Momentum & extension", "动量与延伸"),
    "F3_THEME_STRUCTURE": ("Theme structure", "主题结构"),
    "F4_CATALYST_EVENT": ("Catalysts & events", "催化与事件"),
    "F5_FLOW_POSITIONING": ("Flows & positioning", "资金流与仓位"),
    "F6_MACRO_REGIME": ("Macro conditions", "宏观环境"),
    "F7_QUALITY_FUNDAMENTAL": ("Business quality", "基本面质量"),
    "F8_ATTENTION_CROWDING": ("Attention & crowding", "关注度与拥挤度"),
}


def _mapping(value):
    return value if isinstance(value, Mapping) else {}


def _text(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def _number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    try:
        return value if isfinite(value) else None
    except OverflowError:
        return None


def _session_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def _words(en, zh=None):
    en = _text(en)
    return {"en": en, "zh": _text(zh) or en} if en else None


def _money(value):
    value = _number(value)
    return f"${value:,.2f}" if value is not None else None


def _href(value):
    value = _text(value)
    if not value or any(ord(c) < 32 or c == "\\" for c in value):
        return None
    return value if value.startswith("#") or (value.startswith("/") and not value.startswith("//")) else None


def _theme_context(row):
    """Use the producer's existing membership and the native theme-id resolver."""
    theme = _mapping(row.get("theme"))
    theme_id, name = _text(theme.get("id")), _text(theme.get("name"))
    if not name or not theme_id or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", theme_id):
        return {}
    return {"href": f"/baskets.html#theme-{theme_id}",
            "en": f"{name} · Explore context",
            "zh": f"{_text(theme.get('name_zh')) or name} · 探索背景"}


def _memory_href(ticker):
    """Open the existing symbol tool, without claiming a retained-episode match."""
    if not ticker or not re.fullmatch(r"[A-Z0-9^][A-Z0-9.^=_-]{0,19}", ticker):
        return None
    # Explicit issuer intent prevents the receiver's cached/default AAPL fallback.
    # No candidate, generation, assessment, or private evidence is transferred.
    return "/market_memory.html?" + urlencode({"mm_issuer_input": ticker})


def _evidence_profile(prophet):
    """Show the incumbent v3 producer's contributions without recomputing a score."""
    fusion = _mapping(prophet.get("fusion"))
    if prophet.get("version") != "us_prophet_v3" or fusion.get("definition") != "us_prophet_v3":
        return None
    active, absent = fusion.get("families_active"), fusion.get("families_abstaining")
    scores = _mapping(fusion.get("family_contribution"))
    if (not isinstance(active, list) or not isinstance(absent, list)
            or any(not isinstance(k, str) or k not in _FAMILY_LABELS for k in active + absent)
            or len(set(active)) != len(active) or set(active) & set(absent)
            or set(scores) != set(active) or not active
            or any(_number(v) is None or not 0 <= v <= 100 for v in scores.values())):
        return None
    return {"scores": [{"key": k, "label": _words(*_FAMILY_LABELS[k]), "value": scores[k]}
                       for k in active],
            "abstaining": [_words(*_FAMILY_LABELS[k]) for k in absent]}


def _chart_geometry(svg):
    """Extract only numeric geometry from the existing owned spark renderer.

    No source markup is returned or trusted. A malformed drawing is unavailable;
    we never substitute a flat chart or infer a quote/assessment clock from it.
    """
    empty = {"points": [], "zone_edges": [], "zone_fill": None, "direction": "neutral"}
    if not isinstance(svg, str) or len(svg) > 65536 or "<!" in svg:
        return empty
    try:
        root = ElementTree.fromstring(svg)
        if root.tag != "svg" or root.get("class") != "nch":
            return empty
        if any(e.tag not in {"svg", "polyline", "line", "rect", "circle"}
               or any(k.lower().startswith("on") or k in {"href", "style"} for k in e.attrib)
               for e in root.iter()):
            return empty
        box = [float(n) for n in (root.get("viewBox") or "").split()]
        if len(box) != 4 or box[:2] != [0, 0] or not all(isfinite(n) for n in box) or min(box[2:]) <= 0:
            return empty
        lines = [e for e in root if e.tag == "polyline" and e.get("fill") == "none"]
        if len(lines) != 1:
            return empty
        pairs = [p.split(",") for p in (lines[0].get("points") or "").split()]
        if not 2 <= len(pairs) <= 512 or any(len(p) != 2 for p in pairs):
            return empty
        points = [{"x": float(p[0]) / box[2] * 100, "y": float(p[1]) / box[3] * 100} for p in pairs]
        if any(not isfinite(v) or not 0 <= v <= 100 for p in points for v in p.values()):
            return empty
        if any(a["x"] >= b["x"] for a, b in zip(points, points[1:])):
            return empty
        # Preserve the publisher's plotted zone, including an off-chart absence.
        # Recomputing it from the current quote would move the historical drawing.
        edges, fill = [], None
        for element in root:
            if element.tag == "line":
                edge = {k: float(element.get(k)) / box[2 if k[0] == "x" else 3] * 100
                        for k in ("x1", "x2", "y1", "y2")}
                if (any(not isfinite(v) or not 0 <= v <= 100 for v in edge.values())
                        or edge["x1"] > edge["x2"] or edge["y1"] != edge["y2"]):
                    return empty
                edges.append(edge)
            elif element.tag == "rect":
                if fill is not None:
                    return empty
                fill = {k: float(element.get(k)) / box[2 if k in ("x", "width") else 3] * 100
                        for k in ("x", "y", "width", "height")}
                if (any(not isfinite(v) or not 0 <= v <= 100 for v in fill.values())
                        or fill["x"] + fill["width"] > 100.01 or fill["y"] + fill["height"] > 100.01):
                    return empty
        if len(edges) not in (0, 2):
            return empty
        direction = {"var(--up)": "up", "var(--down)": "down"}.get(lines[0].get("stroke"), "neutral")
        return {"points": points, "zone_edges": edges, "zone_fill": fill, "direction": direction}
    except (ElementTree.ParseError, TypeError, ValueError, OverflowError):
        return empty


def present_us_candidate(row, *, occurrence_id, board_asof=None, setup_href=None,
                         compare_enabled=False, folded_cautions=(), marks=(), context=None):
    """Return detached display values for ONE row, in the caller's original order.

    ``folded_cautions`` and ``marks`` are the existing board presenter's resolved
    disclosures, not a second computation of those rules. ``board_asof`` labels
    the current zone snapshot; signal_asof and price_as_of stay independent.
    Missing strategy, horizon, quote change and exact plan relation remain absent.
    """
    if not isinstance(row, Mapping):
        raise TypeError("one source row is required")
    if not isinstance(occurrence_id, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,95}", occurrence_id):
        raise ValueError("a unique, caller-owned occurrence id is required")
    es, conviction = _mapping(row.get("entry_signal")), _mapping(row.get("conviction"))
    status = _text(es.get("status"))
    stance, label, label_zh = _ENTRY.get(status, ("unknown", "Assessment unavailable", "暂无评估"))
    prophet = _mapping(row.get("prophet"))
    score = _number(prophet.get("score"))
    priority_label = _words("Priority", "优先级")
    priority_path = "prophet.score"
    if score is None:
        score = _number(conviction.get("score_edge"))
        priority_label = _words("Edge", "强度")
        priority_path = "conviction.score_edge"
    priority = None if score is None else {
        "value": f"{score:.0f}", "label": priority_label,
        "meaning": _words("Relative evidence-family strength, not entry permission, a return forecast or a win probability.", "证据类别的相对强度，并非入场许可、回报预测或胜率。") if priority_path == "prophet.score" and prophet.get("version") == "us_prophet_v3" else
                   _words("Relative setup readiness, not a win probability.", "相对形态就绪程度，并非胜率。") if priority_path == "prophet.score" else
                   _words("Relative stock selection, entry and quality, not a win probability.", "相对选股、入场与质量强度，并非胜率。"),
    }
    caution_rows = []
    for item in folded_cautions:
        if isinstance(item, Mapping):
            words = _words(item.get("en"), item.get("zh"))
        elif isinstance(item, (tuple, list)) and len(item) == 2:
            words = _words(*item)
        else:
            words = _words(item)
        if words:
            caution_rows.append(words)
    stage = _LANE.get(_text(row.get("lane")))
    stages = [{"label": _words(*words), "active": i == stage} for i, words in enumerate(_STAGES)] if stage is not None else []
    zone = _mapping(es.get("buy_zone"))
    lo, hi = _number(zone.get("low")), _number(zone.get("high"))
    valid_zone = lo is not None and hi is not None and 0 < lo <= hi
    terms = {
        "label": _words("Entry zone", "入场区间"),
        "value": f"{_money(lo)}–{_money(hi)}" if valid_zone else None,
        "asof": _text(board_asof) if valid_zone else None,
        "currency": "USD" if valid_zone else None,
    }
    context = _theme_context(row) if context is None else _mapping(context)
    link = _href(context.get("href"))
    supplied_marks = []
    for mark in marks:
        if isinstance(mark, Mapping):
            words = _words(mark.get("en"), mark.get("zh"))
            if words:
                words["explanation"] = None if mark.get("k") in {"feat", "new"} else _words(mark.get("tip_en"), mark.get("tip_zh"))
                supplied_marks.append(words)
    chart = _chart_geometry(row.get("spark_svg"))
    ticker = _text(row.get("ticker"))
    return {
        "id": occurrence_id, "stance": stance, "stance_label": _words(label, label_zh),
        "assessment_asof": None,
        "signal_asof": _text(row.get("signal_asof")),
        "assessment_missing_reason": _text(row.get("entry_signal_null_reason")) if stance == "unknown" else None,
        "strategy": None, "horizon": None,
        "quote": {"price": _money(row.get("price")), "change": None, "direction": "neutral",
                  "asof": _text(row.get("price_as_of")), "currency": "USD"},
        "chart": {**chart, "label": _words("Daily closes", "每日收盘"),
                  "asof": _text(row.get("spark_as_of")) if chart["points"] else None},
        "identity": {"ticker": ticker, "name": _words(row.get("name"), row.get("name_zh")),
                     "industry": _words(row.get("industry"), row.get("industry_zh")),
                     "sector": _words(row.get("sector"), row.get("sector_zh"))},
        "priority": priority, "observation": _words(es.get("headline"), es.get("headline_zh")),
        "assessment_detail": _words(es.get("action"), es.get("action_zh")),
        "evidence_profile": _evidence_profile(prophet),
        "cautions": caution_rows, "stages": stages,
        "marks": supplied_marks, "added_date": _session_date(row.get("added_date")),
        "context": {"href": link, "label": _words(context.get("en"), context.get("zh"))} if link else None,
        "terms": terms, "setup_href": _href(setup_href),
        "memory_href": _memory_href(ticker),
        "compare_enabled": compare_enabled is True and bool(ticker),
        "source_fields": {"stance": "entry_signal.status", "assessment_asof": None, "signal_asof": "signal_asof",
                          "quote.price": "price", "quote.asof": "price_as_of", "chart.points": "spark_svg numeric geometry",
                          "chart.asof": "spark_as_of" if chart["points"] and _text(row.get("spark_as_of")) else None,
                          "priority": priority_path if priority else None,
                          "terms.value": "entry_signal.buy_zone" if valid_zone else None,
                          "terms.asof": "board envelope as_of" if valid_zone and _text(board_asof) else None,
                          "observation": "entry_signal.headline", "assessment_detail": "entry_signal.action",
                          "evidence_profile": "prophet.fusion", "strategy": None, "horizon": None},
    }
