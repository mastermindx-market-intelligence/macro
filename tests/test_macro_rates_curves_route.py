"""A-F01-W4-1: Treasury curve-shape hero on the existing rates_curves route.

RED-first and fixture-driven. Every test builds a synthetic
``mastermind.macro_workspace_snapshot.v1`` snapshot (or a minimal series
fixture). No test touches ``data/fred/*.parquet`` or the network.

The cases pin: the hero is rates_curves-only, ten nominal CMT tenors
in registry order, prior-close / prior-month arithmetic, honest nulls, the
context_only ceiling, two arithmetic spreads, EN+ZH copy, whole-panel null,
region-level byte preservation of the thirteen sibling suite pages plus the
hub (T11), and no import of the yield-curve engine. T10 lives in
tests/test_macro_rates_curves_bonds_guard.py so this pandas-free module
never imports scripts.build_bonds.
"""
from __future__ import annotations

import ast
import json
import math
import re
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from lib import macro_suite_view
from scripts import build_macro_suite_pages as builder

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
BUILT_AT = "2026-09-09T12:00:00Z"

NOMINAL_TENORS = ("3m", "6m", "1y", "2y", "3y", "5y", "7y", "10y", "20y", "30y")
TENOR_TO_SERIES = {
    "3m": "us3m",
    "6m": "us6m",
    "1y": "us1y",
    "2y": "us2y",
    "3y": "us3y",
    "5y": "us5y",
    "7y": "us7y",
    "10y": "us10y",
    "20y": "us20y",
    "30y": "us30y",
}

# Ceiling tokens that must never appear in the hero JSON or the panel HTML.
# Plain substring matching per spec §10.5 — "probability" must fire on "prob".
CEILING_EN = (
    "prob", "odds", "score", "rank", "band", "signal", "forecast",
    "bull", "bear", "lean",
)
CEILING_ZH = ("概率", "评分", "预测", "看多", "看空", "偏多", "偏空")

SHAPE_NORMAL_EN = (
    "The curve is upward-sloping — longer maturities pay more than shorter ones."
)
SHAPE_NORMAL_ZH = "曲线呈正常形态——期限越长，收益率越高。"
SHAPE_NORMAL_DIP_EN = (
    "The curve is upward-sloping — longer maturities pay more than shorter ones, "
    "with a small dip at the very long end."
)
SHAPE_NORMAL_DIP_ZH = "曲线呈正常形态——期限越长，收益率越高，仅在最长端有小幅回落。"
SHAPE_FLAT_EN = "The curve is close to flat — long and short maturities pay about the same."
SHAPE_FLAT_ZH = "曲线接近平坦——长短期限的收益率大致相同。"
SHAPE_INVERTED_FRONT_EN = (
    "The curve is inverted at the front — three-month yields are at or above ten-year yields."
)
SHAPE_INVERTED_FRONT_ZH = "曲线在短端倒挂——三个月期收益率已不低于十年期。"
SHAPE_INVERTED_BELLY_EN = (
    "The curve is inverted between two and ten years — two-year yields are at or above ten-year yields."
)
SHAPE_INVERTED_BELLY_ZH = (
    "曲线在两年期与十年期之间倒挂——两年期收益率不低于十年期收益率。"
)
SHAPE_INVERTED_BOTH_EN = (
    "The curve is inverted at the front and between two and ten years — "
    "three-month and two-year yields are at or above ten-year yields."
)
SHAPE_INVERTED_BOTH_ZH = (
    "曲线在短端以及两年期与十年期之间均倒挂——三个月期与两年期收益率均不低于十年期收益率。"
)
SHAPE_UNSTATED_EN = (
    "The curve's shape is not stated today: a deciding maturity has no reading."
)
SHAPE_UNSTATED_ZH = "今日不判断曲线形态：关键期限缺少读数。"
NULL_PANEL_EN = "The curve panel needs the Treasury data from tonight, which did not arrive."
NULL_PANEL_ZH = "曲线面板需要当晚的美债数据，但数据未能到达。"
NULL_NOT_DRAWN_EN = "The curve is not drawn: not enough maturities have a reading."
NULL_NOT_DRAWN_ZH = "曲线未画出：有读数的期限不足。"
NULL_FIRST_NIGHTLY_EN = (
    "Today's curve is shown alone: no earlier curve is on file to compare it with."
)
NULL_FIRST_NIGHTLY_ZH = "今天的曲线单独显示：暂无更早的曲线可供对比。"
# The two honest-null legend lines, verbatim. EN and ZH must state the SAME
# reason: "a second day" is not "the next day", and 一个月前线 garden-paths on
# 前线 ("front line"), so the ZH names the line in quotation marks instead.
LEGEND_CLOSE_NULL_EN = (
    "Prior close is not drawn: that comparison needs two days of history."
)
LEGEND_CLOSE_NULL_ZH = "未画出上一交易日收盘线：该对比需要两个交易日的数据。"
LEGEND_MONTH_NULL_EN = (
    "A month ago is not drawn: that comparison needs a month of history."
)
LEGEND_MONTH_NULL_ZH = "未画出“一个月前”对比线：该对比需要一个月的历史数据。"
NULL_SEVEN_EN = "No reading for the 7-year maturity in tonight's data."
NULL_SEVEN_ZH = "本次数据未覆盖7年期。"
EMPTY_HISTORY_EN = "No history published for this series in tonight's data."
EMPTY_HISTORY_ZH = "本次数据未发布该序列的历史。"
CHANGE_CLOSE_EN = "Change since prior close"
CHANGE_CLOSE_ZH = "较上一交易日收盘变动"
CHANGE_MONTH_EN = "Change over a month"
CHANGE_MONTH_ZH = "较一个月前变动"
SPREAD_NOW_EN = "Spread now"
SPREAD_NOW_ZH = "当前利差"
SUBTITLE_EN = "today versus the prior close versus a month ago"
SUBTITLE_ZH = "今日、上一交易日收盘与一个月前对比"

# The page-build stamp the shell prints. T11 renders each sibling with that
# page's own stamp so the stamp sitting inside the macro-suite region does
# not itself become a mismatch; a shared-stamp precondition is forbidden.
_SUITE_BUILT_AT_RE = re.compile(
    r"Page built.*?<time>(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)</time>", re.S)

T11_SITE_PAGES = (
    "site/macro_liquidity_regime.html",
    "site/macro_growth_real_economy.html",
    "site/macro_business_activity.html",
    "site/macro_labor_markets.html",
    "site/macro_inflation_system.html",
    "site/macro_monetary_policy.html",
    "site/macro_financial_conditions.html",
    "site/macro_liquidity_central_banks.html",
    "site/macro_capital_structure.html",
    "site/macro_housing_real_estate.html",
    "site/macro_consumer_payments.html",
    "site/macro_national_debt_liabilities.html",
    "site/macro_trade_flows.html",
    "site/macro_monetary.html",
)

# The region of a rendered suite page that this packet's shared-surface edits
# (the hero slot in the shell's body macro, the Range cell, the `range` key in
# _series) can possibly reach. Everything outside it is site chrome rendered by
# partials this packet never touches.
_SUITE_REGION = ('<nav class="mq-suitenav"',
                 '<div class="mq-scrim" id="mq-scrim" hidden></div>')
_HUB_REGION = ('<main class="mq-shell mq-hub"', "</main>")

ARTIFACT = {
    "path": "macrodata/workspaces/rates_curves/US/latest.json",
    "sha256": "0" * 64,
    "bytes": 1,
    "manifest_path": "macrodata/workspaces/manifest.json",
    "min_client_contract": "mastermind.macro_workspace_snapshot.v1@1.0.0",
}


def _pair(en: str, zh: str) -> dict[str, str]:
    return {"en": en, "zh": zh}


def _points_for(today: float, prior_close: float, prior_month: float,
                as_of: date = date(2026, 9, 9)) -> list[dict[str, Any]]:
    """Three dated rows: month-ago, prior close, today. Extra earlier row so
    prior-close cannot be confused with an average of a longer window."""
    return [
        {"t": (as_of - timedelta(days=40)).isoformat(), "v": prior_month + 0.05},
        {"t": (as_of - timedelta(days=30)).isoformat(), "v": prior_month},
        {"t": (as_of - timedelta(days=2)).isoformat(), "v": prior_close + 0.02},
        {"t": (as_of - timedelta(days=1)).isoformat(), "v": prior_close},
        {"t": as_of.isoformat(), "v": today},
    ]


def _series_entry(tenor: str, points: list[dict[str, Any]] | None) -> dict[str, Any]:
    return {
        "series_id": TENOR_TO_SERIES[tenor],
        "label": _pair(f"{tenor} Treasury yield", f"{tenor}美债收益率"),
        "unit": "percent",
        "basis": "constant_maturity_investment_basis",
        "points": list(points or []),
        "source_ref": f"FRED:{tenor}",
        "freshness": "CURRENT" if points else "SOURCE_FAILED",
        "revision_behavior": "recomputed each owner cadence from prior-only owner reads",
    }


def _complete_levels() -> dict[str, tuple[float, float, float]]:
    """today, prior_close, prior_month per tenor. Upward-sloping today.

    Every adjacent pair climbs with maturity so the shape sentence is the
    normal one, matching this helper's name.
    """
    today = {
        "3m": 3.90, "6m": 3.95, "1y": 4.00, "2y": 4.08, "3y": 4.15,
        "5y": 4.22, "7y": 4.28, "10y": 4.35, "20y": 4.48, "30y": 4.55,
    }
    close = {k: round(v + 0.01, 4) for k, v in today.items()}
    month = {k: round(v + 0.07, 4) for k, v in today.items()}
    return {k: (today[k], close[k], month[k]) for k in NOMINAL_TENORS}


def _inverted_levels() -> dict[str, tuple[float, float, float]]:
    """today, prior_close, prior_month per tenor. Downward-sloping today.

    Both policy spreads are negative, so this fixture is the both-locations
    inverted branch. Prefer the front/belly helpers when a test needs one where.
    """
    today = {
        "3m": 4.55, "6m": 4.48, "1y": 4.40, "2y": 4.32, "3y": 4.25,
        "5y": 4.18, "7y": 4.12, "10y": 4.05, "20y": 3.95, "30y": 3.90,
    }
    close = {k: round(v + 0.01, 4) for k, v in today.items()}
    month = {k: round(v + 0.07, 4) for k, v in today.items()}
    return {k: (today[k], close[k], month[k]) for k in NOMINAL_TENORS}


def _flat_levels() -> dict[str, tuple[float, float, float]]:
    """10y−3m inside ±0.25 pp; no policy spread negative."""
    today = {
        "3m": 4.20, "6m": 4.22, "1y": 4.24, "2y": 4.26, "3y": 4.28,
        "5y": 4.30, "7y": 4.32, "10y": 4.34, "20y": 4.40, "30y": 4.45,
    }
    close = {k: round(v + 0.01, 4) for k, v in today.items()}
    month = {k: round(v + 0.07, 4) for k, v in today.items()}
    return {k: (today[k], close[k], month[k]) for k in NOMINAL_TENORS}


def _inverted_front_levels() -> dict[str, tuple[float, float, float]]:
    """10y−3m ≤ 0; 10y−2y still positive."""
    today = {
        "3m": 4.50, "6m": 4.40, "1y": 4.20, "2y": 4.00, "3y": 4.05,
        "5y": 4.10, "7y": 4.15, "10y": 4.20, "20y": 4.30, "30y": 4.35,
    }
    close = {k: round(v + 0.01, 4) for k, v in today.items()}
    month = {k: round(v + 0.07, 4) for k, v in today.items()}
    return {k: (today[k], close[k], month[k]) for k in NOMINAL_TENORS}


def _inverted_belly_levels() -> dict[str, tuple[float, float, float]]:
    """10y−2y ≤ 0; 10y−3m still positive."""
    today = {
        "3m": 3.80, "6m": 3.90, "1y": 4.10, "2y": 4.50, "3y": 4.40,
        "5y": 4.30, "7y": 4.25, "10y": 4.20, "20y": 4.28, "30y": 4.32,
    }
    close = {k: round(v + 0.01, 4) for k, v in today.items()}
    month = {k: round(v + 0.07, 4) for k, v in today.items()}
    return {k: (today[k], close[k], month[k]) for k in NOMINAL_TENORS}


def _snapshot_kink_levels() -> dict[str, tuple[float, float, float]]:
    """The committed snapshot's own ten CMT levels (20y 5.25, 30y 5.24).

    Both policy spreads are positive (10y−3m = 0.87, 10y−2y = 0.41). The
    1 bp 20y/30y dip is a long-end kink, not an inversion.
    """
    today = {
        "3m": 3.91, "6m": 3.98, "1y": 4.13, "2y": 4.37, "3y": 4.45,
        "5y": 4.54, "7y": 4.65, "10y": 4.78, "20y": 5.25, "30y": 5.24,
    }
    close = {k: round(v + 0.01, 4) for k, v in today.items()}
    month = {k: round(v + 0.07, 4) for k, v in today.items()}
    return {k: (today[k], close[k], month[k]) for k in NOMINAL_TENORS}


def _snapshot(*, workspace_id: str = "rates_curves",
              levels: dict[str, tuple[float, float, float]] | None = None,
              extra_points: dict[str, list[dict[str, Any]]] | None = None,
              skip_tenors: frozenset[str] = frozenset(),
              as_of: date = date(2026, 9, 9),
              availability: dict[str, Any] | None = None) -> dict[str, Any]:
    """A sparse snapshot: enough for build_view, plus a series block the hero reads."""
    items: list[dict[str, Any]] = []
    if levels is None and extra_points is None and workspace_id == "rates_curves":
        levels = _complete_levels()
    for tenor in NOMINAL_TENORS:
        if tenor in skip_tenors:
            items.append(_series_entry(tenor, []))
            continue
        if extra_points and tenor in extra_points:
            items.append(_series_entry(tenor, extra_points[tenor]))
            continue
        if levels and tenor in levels:
            today, close, month = levels[tenor]
            items.append(_series_entry(tenor, _points_for(today, close, month, as_of)))
            continue
        items.append(_series_entry(tenor, []))
    n_with = sum(1 for it in items if it["points"])
    if n_with == 0:
        series = {"items": [], "status": "ABSENT", "null_reason": "INSUFFICIENT_HISTORY"}
    elif n_with < len(NOMINAL_TENORS):
        series = {"items": items, "status": "PARTIAL", "null_reason": None}
    else:
        series = {"items": items, "status": "PRESENT", "null_reason": None}
    return {
        "workspace": {
            "id": workspace_id,
            "title": _pair("Rates & Curves", "利率与曲线"),
            "subtitle": _pair("The Treasury curve, node by node",
                              "国债收益率曲线，逐节点"),
        },
        "region": {"code": "US", "supported": True, "display_name": "United States"},
        "generation": {
            "generation_id": "test",
            "built_at": BUILT_AT,
            "calculation_as_of": as_of.isoformat(),
            "content_sha256": "0" * 64,
        },
        "availability": availability if availability is not None else {
            "state": "CURRENT", "required": [], "degraded": [],
            "coverage_ratio": 1.0, "worst_freshness": "CURRENT",
            "contradiction": {"present": False}, "reasons": [],
        },
        "headline": {"state_id": None, "status": "ABSENT",
                     "null_reason": "NOT_APPLICABLE",
                     "state_label": _pair("No named state", "无命名状态")},
        "axes": {"items": []},
        "metrics": {"items": []},
        "series": series,
        "drivers": {"rate_side": [], "balance_sheet": []},
        "changes": {"comparability": "NO_PRIOR", "deltas": [], "status": "ABSENT",
                    "null_reason": "WARMUP"},
        "implications": {"items": []},
        "learning": {"event_names": []},
    }


def _view(snapshot: dict[str, Any]) -> dict[str, Any]:
    return macro_suite_view.build_view(
        snapshot, page_built_at=BUILT_AT, artifact=ARTIFACT,
    )


def _hero(snapshot: dict[str, Any]) -> dict[str, Any]:
    view = _view(snapshot)
    assert "curve_hero" in view, "rates_curves view is missing curve_hero"
    return view["curve_hero"]


def _render_panel(curve: dict[str, Any]) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=True,
        undefined=StrictUndefined,
    )
    # The panel reads view.curve_hero (the include is passed the page context).
    tmpl = env.get_template("_curve_panel.html.j2")
    return tmpl.render(view={"curve_hero": curve, "ok": True})


def _render_rates_page(snapshot: dict[str, Any]) -> str:
    page = next(p for p in builder.SUITE_PAGES if p.workspace_id == "rates_curves")
    view = _view(snapshot)
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=True,
        undefined=StrictUndefined,
    )
    return builder.render_page(env, page, view)


def _ceiling_hits(text: str) -> list[str]:
    """Plain substring matching. Spec §10.5: 'probability' must fire on 'prob'."""
    lowered = text.lower()
    hits: list[str] = []
    for token in CEILING_EN:
        if token in lowered:
            hits.append(token)
    for token in CEILING_ZH:
        if token in text:
            hits.append(token)
    return hits


def _svg_inner(html: str) -> str:
    start = html.find("<svg")
    end = html.find("</svg>")
    assert start != -1 and end != -1, "panel is missing an svg"
    return html[start:end]


# ---------------------------------------------------------------------------
# T1
# ---------------------------------------------------------------------------
def test_1_curve_hero_present_on_rates_curves_view_only() -> None:
    rates = _view(_snapshot(workspace_id="rates_curves"))
    assert "curve_hero" in rates
    assert rates["curve_hero"]["ok"] is True

    other = _view(_snapshot(workspace_id="liquidity_regime"))
    assert "curve_hero" not in other

    for workspace_id in (
        "growth_real_economy", "business_activity", "labor_markets",
        "inflation_system", "monetary_policy", "financial_conditions",
        "liquidity_central_banks", "capital_structure", "housing_real_estate",
        "consumer_payments", "national_debt_liabilities", "trade_flows",
    ):
        view = _view(_snapshot(workspace_id=workspace_id))
        assert "curve_hero" not in view, workspace_id


# ---------------------------------------------------------------------------
# T2
# ---------------------------------------------------------------------------
def test_2_ten_nominal_tenors_in_registry_order() -> None:
    hero = _hero(_snapshot())
    tenors = hero["tenors"]
    assert [row["tenor"] for row in tenors] == list(NOMINAL_TENORS)
    for row in tenors:
        assert row["today"] is not None
        assert row["prior_close"] is not None
        assert row["prior_month"] is not None
        assert row["delta_close"] == pytest.approx(row["today"] - row["prior_close"])
        assert row["delta_month"] == pytest.approx(row["today"] - row["prior_month"])


# ---------------------------------------------------------------------------
# T3
# ---------------------------------------------------------------------------
def test_3_prior_close_is_the_immediately_preceding_row() -> None:
    as_of = date(2026, 9, 9)
    # Four rows; prior close must be the value one row before today, never the
    # mean of the window and never the month-ago print.
    points = [
        {"t": "2026-08-01", "v": 4.00},
        {"t": "2026-08-10", "v": 4.10},
        {"t": "2026-09-08", "v": 4.32},
        {"t": "2026-09-09", "v": 4.31},
    ]
    extra = {tenor: list(points) for tenor in NOMINAL_TENORS}
    hero = _hero(_snapshot(extra_points=extra, as_of=as_of))
    ten = {row["tenor"]: row for row in hero["tenors"]}
    assert ten["10y"]["today"] == pytest.approx(4.31)
    assert ten["10y"]["prior_close"] == pytest.approx(4.32)
    assert ten["10y"]["prior_close"] != pytest.approx((4.32 + 4.31) / 2)
    assert ten["10y"]["prior_close"] != pytest.approx(4.10)


# ---------------------------------------------------------------------------
# T4
# ---------------------------------------------------------------------------
def test_4_prior_month_is_nearest_row_30_days_back() -> None:
    as_of = date(2026, 9, 9)
    # 30 calendar days before as_of is 2026-08-10. The Aug-20 row is closer in
    # time but only 20 days back, so it must not win. The July-01 row is the
    # nearest that is still at least 30 days back.
    points = [
        {"t": "2026-07-01", "v": 4.00},
        {"t": "2026-08-20", "v": 4.10},
        {"t": "2026-09-08", "v": 4.20},
        {"t": "2026-09-09", "v": 4.30},
    ]
    extra = {tenor: list(points) for tenor in NOMINAL_TENORS}
    hero = _hero(_snapshot(extra_points=extra, as_of=as_of))
    ten = {row["tenor"]: row for row in hero["tenors"]}
    assert ten["10y"]["prior_month"] == pytest.approx(4.00)
    assert ten["10y"]["prior_month"] != pytest.approx(4.10)
    assert ten["10y"]["prior_month"] != pytest.approx(4.30)
    assert ten["10y"]["prior_month"] != pytest.approx(4.20)


# ---------------------------------------------------------------------------
# T5
# ---------------------------------------------------------------------------
def test_5_missing_tenor_is_an_honest_null_not_a_dropped_row() -> None:
    hero = _hero(_snapshot(skip_tenors=frozenset({"7y"})))
    tenors = hero["tenors"]
    assert [row["tenor"] for row in tenors] == list(NOMINAL_TENORS)
    seven = next(row for row in tenors if row["tenor"] == "7y")
    assert seven["today"] is None
    assert "7y" in hero["missing_tenors"]
    assert hero["ok"] is True  # nine of ten still draw the curve
    # The missing 7y must break the polyline, not interpolate across the hole.
    chart = hero["chart"]
    assert chart is not None
    xs = [tick["x"] for tick in chart["x_ticks"]]
    x5, x7, x10 = xs[5], xs[6], xs[7]
    segments = chart["today_segments"]
    assert len(segments) >= 2
    joined = " ".join(segments)
    assert f"{x7}," not in joined
    for seg in segments:
        has5 = f"{x5}," in seg
        has10 = f"{x10}," in seg
        assert not (has5 and has10), seg
    html = _render_panel(hero)
    # autoescape turns the apostrophe into &#39;; the words still have to land.
    assert "No reading for the 7-year maturity in tonight" in html
    assert NULL_SEVEN_ZH in html
    svg = _svg_inner(html)
    assert f"{x7}," not in svg
    polylines = re.findall(r'<polyline class="mq-curve-line-today" points="([^"]*)">', svg)
    assert len(polylines) >= 2
    for points in polylines:
        assert f"{x5}," not in points or f"{x10}," not in points, points


# ---------------------------------------------------------------------------
# T6
# ---------------------------------------------------------------------------
def test_6_no_forecast_or_probability_content() -> None:
    hero = _hero(_snapshot())
    dumped = json.dumps(hero, ensure_ascii=False)
    hits = _ceiling_hits(dumped)
    assert hits == [], hits
    html = _render_panel(hero)
    html_hits = _ceiling_hits(html)
    assert html_hits == [], html_hits
    assert "nyfed_prob" not in dumped
    assert "nyfed" not in dumped.lower()
    source = Path(macro_suite_view.__file__).read_text(encoding="utf-8")
    # The helper that builds the hero must never read the NY Fed probability.
    tree = ast.parse(source)
    hero_fn = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_curve_hero"
    )
    hero_src = ast.get_source_segment(source, hero_fn) or ""
    assert "nyfed_prob" not in hero_src
    assert "nyfed" not in hero_src.lower()


def test_6_ceiling_substring_fires_on_planted_surface_forms() -> None:
    """RED control: the natural surface forms spec §10.5 named must bite.

    The previous whole-word matcher let 'probability', 'bullish', 'forecasts'
    and 'ranking' through. This planted string is the transcript of that miss.
    """
    planted = "probability bullish forecasts ranking"
    hits = _ceiling_hits(planted)
    assert "prob" in hits
    assert "bull" in hits
    assert "forecast" in hits
    assert "rank" in hits
    planted_zh = "概率评分预测看多看空偏多偏空"
    zh_hits = _ceiling_hits(planted_zh)
    for token in CEILING_ZH:
        assert token in zh_hits, token


# ---------------------------------------------------------------------------
# T7
# ---------------------------------------------------------------------------
def test_7_two_spreads_only_arithmetic_not_model_output() -> None:
    hero = _hero(_snapshot())
    spreads = hero["spreads"]
    assert [s["id"] for s in spreads] == ["10y3m", "2s10s"]
    by_tenor = {row["tenor"]: row for row in hero["tenors"]}
    ten_minus_three = by_tenor["10y"]["today"] - by_tenor["3m"]["today"]
    ten_minus_two = by_tenor["10y"]["today"] - by_tenor["2y"]["today"]
    two_minus_ten = by_tenor["2y"]["today"] - by_tenor["10y"]["today"]
    by_id = {s["id"]: s for s in spreads}
    assert by_id["10y3m"]["today"] == pytest.approx(ten_minus_three)
    # Same long-minus-short convention as this route's published 2s10s
    # (rates_curves.py: curve_2s10s_level = 10y - 2y). Short-minus-long is
    # the opposite sign and is forbidden here.
    assert by_id["2s10s"]["today"] == pytest.approx(ten_minus_two)
    assert by_id["2s10s"]["today"] != pytest.approx(two_minus_ten)
    assert by_id["2s10s"]["label"]["en"] == "10-year minus 2-year"
    assert by_id["2s10s"]["label"]["zh"] == "10年期减2年期"
    # Deltas are the same arithmetic on the comparison windows.
    close_10y3m = by_tenor["10y"]["prior_close"] - by_tenor["3m"]["prior_close"]
    assert by_id["10y3m"]["delta_close"] == pytest.approx(
        by_id["10y3m"]["today"] - close_10y3m
    )
    close_2s10s = by_tenor["10y"]["prior_close"] - by_tenor["2y"]["prior_close"]
    assert by_id["2s10s"]["delta_close"] == pytest.approx(
        by_id["2s10s"]["today"] - close_2s10s
    )


def test_7_hero_2s10s_sign_equals_producer_formula_for_the_fixture() -> None:
    """Producer curve_2s10s_level is 10y − 2y. The hero must share that sign."""
    levels = _complete_levels()
    producer_2s10s = levels["10y"][0] - levels["2y"][0]
    hero = _hero(_snapshot(levels=levels))
    today = next(s["today"] for s in hero["spreads"] if s["id"] == "2s10s")
    assert math.copysign(1.0, today) == math.copysign(1.0, producer_2s10s)
    assert today == pytest.approx(producer_2s10s)
    inverted = _inverted_levels()
    producer_inv = inverted["10y"][0] - inverted["2y"][0]
    inv_today = next(
        s["today"] for s in _hero(_snapshot(levels=inverted))["spreads"]
        if s["id"] == "2s10s"
    )
    assert math.copysign(1.0, inv_today) == math.copysign(1.0, producer_inv)
    assert inv_today == pytest.approx(producer_inv)


# ---------------------------------------------------------------------------
# T8
# ---------------------------------------------------------------------------
def test_8_en_and_zh_both_render() -> None:
    html = _render_rates_page(_snapshot())
    assert "The Treasury curve" in html
    assert "美债收益率曲线" in html
    assert SUBTITLE_EN in html
    assert SUBTITLE_ZH in html
    assert "10-year minus 3-month" in html
    assert "10年期减3月期" in html
    assert "10-year minus 2-year" in html
    assert "10年期减2年期" in html
    assert "2-year minus 10-year" not in html
    assert "2年期减10年期" not in html
    assert "Today" in html and "今日" in html
    assert "Prior close" in html and "上一交易日收盘" in html
    assert "A month ago" in html and "一个月前" in html


def test_8_normal_fixture_renders_the_normal_shape_sentence_only() -> None:
    html = _render_panel(_hero(_snapshot(levels=_complete_levels())))
    assert SHAPE_NORMAL_EN in html
    assert SHAPE_NORMAL_ZH in html
    assert SHAPE_INVERTED_FRONT_EN not in html
    assert SHAPE_INVERTED_FRONT_ZH not in html
    assert SHAPE_INVERTED_BELLY_EN not in html
    assert "inverted" not in html.lower()
    assert "倒挂" not in html


def test_8_inverted_fixture_renders_the_inverted_shape_sentence_only() -> None:
    html = _render_panel(_hero(_snapshot(levels=_inverted_front_levels())))
    assert SHAPE_INVERTED_FRONT_EN in html
    assert SHAPE_INVERTED_FRONT_ZH in html
    assert SHAPE_NORMAL_EN not in html
    assert SHAPE_NORMAL_ZH not in html
    assert SHAPE_INVERTED_BELLY_EN not in html


# ---------------------------------------------------------------------------
# T9
# ---------------------------------------------------------------------------
def test_9_whole_panel_honest_null_when_snapshot_incomplete() -> None:
    empty = _snapshot(levels={}, extra_points={}, skip_tenors=frozenset(NOMINAL_TENORS))
    hero = _hero(empty)
    assert hero["ok"] is False
    html = _render_panel(hero)
    # Default fixture availability is CURRENT, but the panel is not drawn
    # (zero tenors). The copy must not claim today's curve is shown.
    assert NULL_NOT_DRAWN_EN in html
    assert NULL_NOT_DRAWN_ZH in html
    assert NULL_FIRST_NIGHTLY_EN not in html
    assert NULL_FIRST_NIGHTLY_ZH not in html
    assert "shown alone" not in html
    assert NULL_PANEL_EN not in html
    assert "<polyline" not in html
    assert "<path" not in html


# ---------------------------------------------------------------------------
# T11 — region byte identity of the thirteen siblings plus the hub
# ---------------------------------------------------------------------------
def _copy_site_assets(destination: Path) -> None:
    """lib.pages.write_page may hash sibling css/js next to the page."""
    site = ROOT / "site"
    if not site.is_dir():
        return
    for asset in sorted(site.glob("*.css")):
        shutil.copy2(asset, destination / asset.name)
    for asset in sorted(site.glob("*.js")):
        shutil.copy2(asset, destination / asset.name)


def _page_built_stamp(html: str) -> str | None:
    found = _SUITE_BUILT_AT_RE.search(html)
    return found.group(1) if found else None


def _region(html: str, name: str) -> str | None:
    start, end = _HUB_REGION if name == "macro_monetary.html" else _SUITE_REGION
    i = html.find(start)
    j = html.rfind(end)
    if i < 0 or j < i:
        return None
    return html[i:j + len(end)]


def _t11_collapse_main_prior_label(html: str) -> str:
    """Collapse origin/main #6984's missing-prior label rewrite.

    ``a49a705752`` retitled a missing prior from the generic Unknown pair
    to a plain-word sentence. Committed sibling pages on main were not
    rebaked, so a raw region compare against ``site/`` is that main-side
    drift, not this packet. Both forms collapse to the same bytes so T11
    still fails on any other shared-surface edit.
    """
    return html.replace(
        "No earlier reading available to compare yet.",
        "Unknown",
    ).replace(
        "暂无可比较的更早读数。",
        "未知",
    )


def test_11_thirteen_other_suite_pages_byte_identical(tmp_path) -> None:
    """Region-level byte identity of the macro-suite region (the slice
    enclosing <main>) on all fourteen T11 targets, unconditionally.

    A mismatched region is a FAIL, never a skip. Whole-page identity is
    reported per target as information (identical / drifted lists printed);
    ``assert len(identical)+len(drifted)==14`` is kept. Main-side chrome
    stamps make whole-page identity unattainable on committed siblings; the
    region is the whole of what this packet's shared-surface edits can reach.

    Each target is rendered with that committed page's own page-built stamp
    so a stamp sitting inside the region cannot itself become a mismatch, and
    so a sibling rebake that moves one stamp cannot disable this test.
    """
    assert (ROOT / "site" / "macrodata").is_dir(), (
        "site/ is not materialised — python3 scripts/worktree_sparse.py add site"
    )
    _copy_site_assets(tmp_path)
    env = builder._environment(ROOT)
    data = ROOT / "site" / "macrodata"
    entries: list[Any] = []
    for page in builder.SUITE_PAGES:
        committed_path = ROOT / "site" / page.output
        assert committed_path.exists(), page.output
        stamp = _page_built_stamp(committed_path.read_text(encoding="utf-8")) or BUILT_AT
        _path, _ok, entry = builder.build_page(
            ROOT, page, data_root=data, out_dir=tmp_path, env=env,
            page_built_at=stamp,
        )
        entries.append(entry)
    hub_committed = ROOT / "site" / "macro_monetary.html"
    assert hub_committed.exists()
    hub_stamp = _page_built_stamp(hub_committed.read_text(encoding="utf-8")) or BUILT_AT
    builder.build_hub(entries, out_dir=tmp_path, env=env, page_built_at=hub_stamp)

    targets = [page.output for page in builder.SUITE_PAGES
               if page.workspace_id != "rates_curves"] + ["macro_monetary.html"]
    assert len(targets) == 14
    assert [f"site/{name}" for name in targets] == list(T11_SITE_PAGES)

    identical: list[str] = []
    drifted: list[str] = []
    for name in targets:
        committed_path = ROOT / "site" / name
        rendered_path = tmp_path / name
        assert rendered_path.exists(), name
        if committed_path.read_bytes() == rendered_path.read_bytes():
            identical.append(name)
            continue
        before = _region(committed_path.read_text(encoding="utf-8"), name)
        after = _region(rendered_path.read_text(encoding="utf-8"), name)
        assert before is not None and after is not None, f"{name}: no macro-suite region"
        assert _t11_collapse_main_prior_label(before) == _t11_collapse_main_prior_label(after), (
            f"{name}: the macro-suite region is NOT byte-identical to the committed "
            "page. That is a regression introduced by this packet's shared-surface "
            "edits, not main-side drift."
        )
        drifted.append(name)
    print(f"T11 identical: {identical}")
    print(f"T11 drifted: {drifted}")
    print(f"T11: 14 targets — {len(identical)} whole-page identical, "
          f"{len(drifted)} region-identical with whole-page drift.")
    assert len(identical) + len(drifted) == 14


def test_11_stamp_mismatch_does_not_disable_the_region_assertion(tmp_path) -> None:
    """M4. Altering one sibling's page-built stamp in a tmp copy must not
    skip T11, and the region assertion still runs.
    """
    name = "macro_trade_flows.html"
    committed_path = ROOT / "site" / name
    assert committed_path.exists(), name
    original = committed_path.read_text(encoding="utf-8")
    stamp = _page_built_stamp(original)
    assert stamp is not None
    altered_stamp = "1999-01-01T00:00:00Z"
    altered = original.replace(stamp, altered_stamp)
    assert altered != original
    assert stamp not in altered
    copy = tmp_path / name
    copy.write_text(altered, encoding="utf-8")
    # The comparison still runs: region of the altered copy vs a re-render
    # that uses the altered stamp. A skip is impossible here — there is no
    # shared-stamp gate.
    env = builder._environment(ROOT)
    data = ROOT / "site" / "macrodata"
    page = next(p for p in builder.SUITE_PAGES if p.output == name)
    out = tmp_path / "rendered"
    out.mkdir()
    _copy_site_assets(out)
    builder.build_page(
        ROOT, page, data_root=data, out_dir=out, env=env,
        page_built_at=altered_stamp,
    )
    before = _region(altered, name)
    after = _region((out / name).read_text(encoding="utf-8"), name)
    assert before is not None and after is not None
    assert before == after
    assert altered_stamp in before
    assert stamp not in before


# ---------------------------------------------------------------------------
# T13 — extra guard (NOT T11): the include appears in exactly one template
# ---------------------------------------------------------------------------
def test_13_curve_panel_include_appears_in_exactly_one_template() -> None:
    """The include lives in the shell's hero slot, in the plain form (no
    ignore missing), and nowhere else. This is an extra guard with its own
    number; the spec's T11 is the byte-preservation test above.
    """
    needle = '{% include "_curve_panel.html.j2" %}'
    forbidden = '{% include "_curve_panel.html.j2" ignore missing %}'
    hits: list[str] = []
    for path in sorted((ROOT / "templates").rglob("*.j2")):
        text = path.read_text(encoding="utf-8")
        if forbidden in text:
            hits.append(f"{path.name}#ignore-missing")
        elif needle in text:
            hits.append(path.name)
        elif "_curve_panel.html.j2" in text and path.name != "_curve_panel.html.j2":
            hits.append(f"{path.name}#mention")
    assert hits == ["_macro_suite_shell.html.j2"]
    shell = (TEMPLATES / "_macro_suite_shell.html.j2").read_text(encoding="utf-8")
    assert "ignore missing" not in shell
    for path in (ROOT / "templates").glob("macro_*.html.j2"):
        text = path.read_text(encoding="utf-8")
        assert "mq-curve-hero" not in text, path.name
        assert "_curve_panel.html.j2" not in text, path.name


# ---------------------------------------------------------------------------
# T12
# ---------------------------------------------------------------------------
def test_12_no_import_of_yield_curve_engine() -> None:
    forbidden = (
        "engine.yield_curve",
        "engine.rates_inflation_command",
        "engine.yield_momentum",
        "from engine import yield_curve",
        "import yield_curve",
    )
    for rel in (
        "lib/macro_suite_view.py",
        "engine/market_os/macro_workspaces/rates_curves.py",
        "templates/_curve_panel.html.j2",
        "templates/macro_rates_curves.html.j2",
    ):
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{rel} imports {token}"
        assert "build_bonds" not in text, rel
    # sys.modules assertion: building the rates_curves view must not load those
    # engines. Clear the probes first so this measures the view builder, not
    # any earlier import in the process.
    probes = (
        "engine.yield_curve",
        "engine.rates_inflation_command",
        "engine.yield_momentum",
    )
    for mod in probes:
        sys.modules.pop(mod, None)
    _view(_snapshot())
    for mod in probes:
        assert mod not in sys.modules, mod


# ---------------------------------------------------------------------------
# R1 — SVG ticks are tspans, never HTML spans
# ---------------------------------------------------------------------------
def test_svg_tick_labels_are_tspans_not_html_spans() -> None:
    """Axis labels live outside the SVG (HTML overlay). SVG must not contain
    HTML <span> (the foreign-content breakout) or scaled <text> ticks.
    """
    hero = _hero(_snapshot())
    html = _render_panel(hero)
    svg = _svg_inner(html)
    assert "<span" not in svg
    assert "<text" not in svg
    ticks = hero["chart"]["x_ticks"]
    assert len(ticks) == 10
    overlay = html[html.find('class="mq-curve-xlabels"'):html.find('class="mq-curve-legend"')]
    for tick in ticks:
        assert f'<span class="l-en">{tick["label"]["en"]}</span>' in overlay
        assert f'<span class="l-zh">{tick["label"]["zh"]}</span>' in overlay
        assert f'<span class="l-en">{tick["short"]["en"]}</span>' in overlay
        assert f'<span class="l-zh">{tick["short"]["zh"]}</span>' in overlay
    assert "is-last" in overlay
    assert "mq-curve-xlabel-short" in overlay
    assert "mq-curve-xlabel-long" in overlay


# ---------------------------------------------------------------------------
# R5 — degraded_view carries the honest-null hero
# ---------------------------------------------------------------------------
def test_degraded_view_sets_honest_null_curve_hero() -> None:
    view = macro_suite_view.degraded_view(
        workspace_id="rates_curves",
        title=_pair("Rates & Curves", "利率与曲线"),
        subtitle=_pair("The Treasury curve, node by node", "国债收益率曲线，逐节点"),
        region_code="US",
        region_display_name="United States",
        page_built_at=BUILT_AT,
        artifact=ARTIFACT,
        failure_kind="SOURCE_FAILED",
        failure_detail="test",
    )
    assert view["ok"] is False
    hero = view["curve_hero"]
    assert hero["ok"] is False
    html = _render_panel(hero)
    assert NULL_PANEL_EN in html
    assert NULL_PANEL_ZH in html
    other = macro_suite_view.degraded_view(
        workspace_id="liquidity_regime",
        title=_pair("Liquidity Regime", "流动性体制"),
        subtitle=_pair("x", "x"),
        region_code="US",
        region_display_name="United States",
        page_built_at=BUILT_AT,
        artifact=ARTIFACT,
        failure_kind="SOURCE_FAILED",
        failure_detail="test",
    )
    assert "curve_hero" not in other


# ---------------------------------------------------------------------------
# R7 / R10 — units and change-row wording
# ---------------------------------------------------------------------------
def test_hero_numbers_carry_units_and_change_rows_are_not_legend_labels() -> None:
    html = _render_panel(_hero(_snapshot()))
    assert "percentage points" in html
    assert "个百分点" in html
    assert re.search(r"\d+\.\d{2}%", html), html
    assert CHANGE_CLOSE_EN in html
    assert CHANGE_CLOSE_ZH in html
    assert CHANGE_MONTH_EN in html
    assert CHANGE_MONTH_ZH in html
    assert SPREAD_NOW_EN in html
    assert SPREAD_NOW_ZH in html
    # Legend still names the plotted LEVELS; change rows must not reuse those
    # labels as the only words in front of a delta.
    legend_close = html.find("is-close")
    deltas = html.find("mq-curve-deltas")
    assert 0 <= legend_close < deltas
    delta_block = html[deltas:]
    assert CHANGE_CLOSE_EN in delta_block
    assert "Prior close +" not in delta_block
    assert "A month ago +" not in delta_block


# ---------------------------------------------------------------------------
# Round 3 R1 — three shape states with a where
# ---------------------------------------------------------------------------
def test_shape_normal_strictly_rising_has_no_where_clause() -> None:
    html = _render_panel(_hero(_snapshot(levels=_complete_levels())))
    assert SHAPE_NORMAL_EN in html
    assert SHAPE_NORMAL_ZH in html
    assert "inverted" not in html.lower()
    assert "倒挂" not in html
    assert "small dip" not in html
    assert SHAPE_FLAT_EN not in html


def test_shape_flat_when_10y3m_inside_quarter_point() -> None:
    levels = _flat_levels()
    assert abs(levels["10y"][0] - levels["3m"][0]) <= 0.25
    assert levels["10y"][0] - levels["2y"][0] > 0
    html = _render_panel(_hero(_snapshot(levels=levels)))
    assert SHAPE_FLAT_EN in html
    assert SHAPE_FLAT_ZH in html
    assert "inverted" not in html.lower()
    assert "倒挂" not in html


def test_shape_inverted_at_the_front() -> None:
    levels = _inverted_front_levels()
    assert levels["10y"][0] - levels["3m"][0] <= 0
    assert levels["10y"][0] - levels["2y"][0] > 0
    html = _render_panel(_hero(_snapshot(levels=levels)))
    assert SHAPE_INVERTED_FRONT_EN in html
    assert SHAPE_INVERTED_FRONT_ZH in html
    assert SHAPE_INVERTED_BELLY_EN not in html
    assert SHAPE_NORMAL_EN not in html


def test_shape_inverted_between_two_and_ten_years() -> None:
    levels = _inverted_belly_levels()
    assert levels["10y"][0] - levels["2y"][0] <= 0
    assert levels["10y"][0] - levels["3m"][0] > 0
    html = _render_panel(_hero(_snapshot(levels=levels)))
    assert SHAPE_INVERTED_BELLY_EN in html
    assert SHAPE_INVERTED_BELLY_ZH in html
    assert SHAPE_INVERTED_FRONT_EN not in html
    assert SHAPE_NORMAL_EN not in html


def test_shape_snapshot_kink_is_normal_not_inverted() -> None:
    """The committed snapshot's own ten levels: 20y 5.25 > 30y 5.24, spreads +."""
    levels = _snapshot_kink_levels()
    assert levels["10y"][0] - levels["3m"][0] == pytest.approx(0.87)
    assert levels["10y"][0] - levels["2y"][0] == pytest.approx(0.41)
    assert levels["20y"][0] > levels["30y"][0]
    html = _render_panel(_hero(_snapshot(levels=levels)))
    assert SHAPE_NORMAL_DIP_EN in html
    assert SHAPE_NORMAL_DIP_ZH in html
    assert "inverted" not in html.lower()
    assert "倒挂" not in html
    assert SHAPE_FLAT_EN not in html


# ---------------------------------------------------------------------------
# Round 3 R2 — two honest-null reasons
# ---------------------------------------------------------------------------
def test_null_not_drawn_when_availability_is_current_and_series_absent() -> None:
    empty = _snapshot(levels={}, extra_points={}, skip_tenors=frozenset(NOMINAL_TENORS))
    hero = _hero(empty)
    assert hero["ok"] is False
    html = _render_panel(hero)
    assert NULL_NOT_DRAWN_EN in html
    assert NULL_NOT_DRAWN_ZH in html
    assert NULL_FIRST_NIGHTLY_EN not in html
    assert NULL_FIRST_NIGHTLY_ZH not in html
    assert "shown alone" not in html
    assert NULL_PANEL_EN not in html
    assert NULL_PANEL_ZH not in html


def test_first_nightly_copy_only_when_todays_curve_is_shown() -> None:
    """M2. The ruled 'shown alone' pair is true only when the chart draws
    today's curve and no earlier curve. An empty CURRENT panel must not use it.
    """
    as_of = date(2026, 9, 9)
    extra = {
        tenor: [{"t": as_of.isoformat(), "v": 4.0 + i * 0.02}]
        for i, tenor in enumerate(NOMINAL_TENORS)
    }
    shown = _hero(_snapshot(extra_points=extra, as_of=as_of))
    assert shown["ok"] is True
    assert shown["chart"]["has_today"] is True
    assert shown["chart"]["has_prior_close"] is False
    assert shown["chart"]["has_prior_month"] is False
    shown_html = _render_panel(shown)
    # autoescape turns the apostrophe in Today's into &#39;
    assert "curve is shown alone" in shown_html
    assert "no earlier curve is on file" in shown_html
    assert NULL_FIRST_NIGHTLY_ZH in shown_html
    assert NULL_NOT_DRAWN_EN not in shown_html

    empty = _hero(_snapshot(levels={}, extra_points={}, skip_tenors=frozenset(NOMINAL_TENORS)))
    assert empty["ok"] is False
    empty_html = _render_panel(empty)
    assert NULL_FIRST_NIGHTLY_EN not in empty_html
    assert NULL_FIRST_NIGHTLY_ZH not in empty_html
    assert NULL_NOT_DRAWN_EN in empty_html
    assert NULL_NOT_DRAWN_ZH in empty_html

    complete = _hero(_snapshot())
    assert complete["ok"] is True
    assert complete["chart"]["has_prior_close"] is True
    complete_html = _render_panel(complete)
    assert NULL_FIRST_NIGHTLY_EN not in complete_html
    assert NULL_FIRST_NIGHTLY_ZH not in complete_html
    assert complete["first_nightly"] is None


def test_null_did_not_arrive_when_availability_is_not_current() -> None:
    empty = _snapshot(
        levels={}, extra_points={}, skip_tenors=frozenset(NOMINAL_TENORS),
        availability={
            "state": "SOURCE_FAILED", "required": [], "degraded": [],
            "coverage_ratio": 0.0, "worst_freshness": "SOURCE_FAILED",
            "contradiction": {"present": False}, "reasons": [],
        },
    )
    hero = _hero(empty)
    assert hero["ok"] is False
    html = _render_panel(hero)
    assert NULL_PANEL_EN in html
    assert NULL_PANEL_ZH in html
    assert NULL_FIRST_NIGHTLY_EN not in html
    assert NULL_FIRST_NIGHTLY_ZH not in html
    assert NULL_NOT_DRAWN_EN not in html
    assert NULL_NOT_DRAWN_ZH not in html


# ---------------------------------------------------------------------------
# Round 3 R4 / R5 — last tick fits; overlay labels are 10 CSS px
# ---------------------------------------------------------------------------
def test_tenor_labels_live_outside_the_viewbox_as_an_html_list() -> None:
    """Structural, not arithmetic. The clipping this closes was a render-time
    viewBox effect, so the guard is the STRUCTURE that makes it impossible: no
    tenor label <text> inside the <svg> at all, the labels in an
    <ol class="mq-curve-xlabels"> after </svg>, and the last <li> end-anchored
    with `is-last`. It fails the moment a label moves back into the viewBox.
    """
    hero = _hero(_snapshot())
    html = _render_panel(hero)
    svg = _svg_inner(html)
    assert "<text" not in svg
    assert "<tspan" not in svg
    for label in ("3-month", "30-year", "3月期", "30年期", "3 mo", "30 yr", "3个月"):
        assert label not in svg, label
    svg_end = html.find("</svg>")
    ol_at = html.find('<ol class="mq-curve-xlabels">')
    assert svg_end != -1 and ol_at > svg_end
    overlay = html[ol_at:html.find("</ol>", ol_at)]
    classes = re.findall(r'<li class="([^"]*)"', overlay)
    assert len(classes) == len(chart_ticks := hero["chart"]["x_ticks"]) == 10
    assert "is-last" in classes[-1]
    assert all("is-last" not in value for value in classes[:-1])
    assert chart_ticks[-1]["anchor"] == "end"
    assert all(tick["anchor"] == "middle" for tick in chart_ticks[:-1])
    assert "30-year" in overlay and "30年期" in overlay


def test_y_label_box_width_equals_pad_l_over_chart_width() -> None:
    """R1. The CSS width of `.mq-curve-ylabels li` IS pad_l/width, so the label
    box ends exactly at the plot's left edge — and there is no media-query
    override of that width, which is what put the lowest tick under the data.
    """
    css = (TEMPLATES / "_curve_panel.html.j2").read_text(encoding="utf-8")
    declared = re.findall(r"\.mq-curve-ylabels li \{[^}]*?width:\s*([0-9.]+)%", css, re.S)
    assert declared == ["11.25"], declared
    chart = _hero(_snapshot())["chart"]
    assert float(declared[0]) == pytest.approx(100.0 * chart["pad_l"] / chart["width"])
    # Measured: 31.7 px of ink for a "5.28%"-shaped label in Inter at 10 CSS px,
    # plus the 4 px gutter, against a 336 px plot at a 390 viewport.
    assert chart["pad_l"] >= 64
    assert chart["pad_l"] / chart["width"] * 336.0 - 4.0 >= 31.7
    media = css[css.find("@media"):]
    assert media, "the partial has no media query to check"
    assert re.search(r"\.mq-curve-ylabels li \{[^}]*width", media, re.S) is None, (
        "a media query overrides the y-label box width; it must equal pad_l/width "
        "at EVERY viewport"
    )


def test_mobile_x_labels_are_thinned_so_no_two_touch_at_390() -> None:
    """R7(a). Ten overlay labels cannot clear each other at a 390 CSS px
    viewport in either language. Five stay visible; the other five keep their
    <li> in the <ol> and are hidden by CSS alone.

    The gap is checked at the measured 390-viewport plot width (336 CSS px,
    from the pad_l y-label measurement in ``_chart_payload``) with CJK glyphs
    at the full 10 px em and ASCII at 0.6 em. The last-two EN shorts after
    R9.3 (``10 yr`` / ``30 yr``) must still clear by more than 4 CSS px.
    """
    hero = _hero(_snapshot())
    chart = hero["chart"]
    ticks = chart["x_ticks"]
    assert len(ticks) == 10
    shown = [tick for tick in ticks if tick["mobile"]]
    assert [tick["label"]["en"] for tick in shown] == [
        "3-month", "1-year", "5-year", "10-year", "30-year"]
    assert [tick["short"]["en"] for tick in shown] == [
        "3 mo", "1 yr", "5 yr", "10 yr", "30 yr"]
    html = _render_panel(hero)
    overlay = html[html.find('<ol class="mq-curve-xlabels">'):html.find("</ol>", html.find('<ol class="mq-curve-xlabels">'))]
    assert overlay.count("<li ") == 10
    assert overlay.count("is-mobile-hidden") == 5
    assert ".mq-curve-xlabels li.is-mobile-hidden { visibility: hidden; }" in html

    plot_px = 336.0  # measured plot width at a 390 CSS px viewport

    def _width(text: str) -> float:
        return sum(10.0 if ord(ch) > 0x2E80 else 6.0 for ch in text)

    gaps: dict[str, list[float]] = {}
    for lang in ("en", "zh"):
        boxes: list[tuple[float, float]] = []
        for tick in shown:
            centre = plot_px * tick["x_pct"] / 100.0
            width = _width(tick["short"][lang])
            if tick["anchor"] == "end":
                boxes.append((centre - width, centre))
            else:
                boxes.append((centre - width / 2.0, centre + width / 2.0))
        lang_gaps = []
        for (_, right), (left, _) in zip(boxes, boxes[1:]):
            gap = left - right
            lang_gaps.append(gap)
            assert gap >= 4.0, (lang, gap, boxes)
        gaps[lang] = lang_gaps
    # Last two visible EN shorts: 10 yr (center) and 30 yr (end-anchored).
    last_two_en = gaps["en"][-1]
    print(f"R9.2 last-two EN gap at 390/336px plot: {last_two_en:.2f} CSS px")
    assert last_two_en >= 4.0
    assert last_two_en == pytest.approx(20.33, abs=0.05)


def test_axis_overlay_labels_are_ten_css_px() -> None:
    html = _render_panel(_hero(_snapshot()))
    assert re.search(
        r"\.mq-curve-xlabels li,\s*\n\s*\.mq-curve-ylabels li \{[^}]*font-size:\s*10px",
        html,
        re.S,
    )
    assert "font-size: 10px; /* CSS px" in html


def test_svg_aria_labelledby_is_en_only_with_zh_on_data_a11y() -> None:
    html = _render_panel(_hero(_snapshot()))
    start = html.find("<svg")
    end = html.find(">", start) + 1
    opener = html[start:end]
    labelled = re.search(r'aria-labelledby="([^"]*)"', opener)
    assert labelled is not None
    assert labelled.group(1) == "mq-curve-hero-caption-en"
    assert 'data-a11y-zh="mq-curve-hero-caption-zh"' in opener
    assert 'data-a11y-en="mq-curve-hero-caption-en"' in opener


def test_as_of_caption_is_derived_from_the_plotted_rows() -> None:
    hero = _hero(_snapshot(as_of=date(2026, 9, 9)))
    assert hero["as_of"] == "2026-09-09"
    html = _render_panel(hero)
    assert "Levels as of 9 September 2026" in html
    assert "各期限水平截至2026年9月9日" in html


def test_a_tenor_a_day_behind_makes_the_caption_name_the_range() -> None:
    """R7(k). The caption is the oldest date the PLOTTED rows carry, never the
    page-wide generation.calculation_as_of — a stale tenor must not inherit a
    fresher one's date. When the plotted tenors span more than one day the
    caption names the range in both languages.
    """
    as_of = date(2026, 9, 9)
    levels = _complete_levels()
    today, close, month = levels["7y"]
    hero = _hero(_snapshot(
        levels=levels,
        as_of=as_of,
        extra_points={"7y": _points_for(today, close, month, as_of - timedelta(days=1))},
    ))
    rows = {row["tenor"]: row for row in hero["tenors"]}
    assert rows["7y"]["as_of_tenor"] == "2026-09-08"
    assert rows["10y"]["as_of_tenor"] == "2026-09-09"
    assert hero["as_of"] == "2026-09-08"
    html = _render_panel(hero)
    assert "Levels as of 8–9 September 2026" in html
    assert "各期限水平截至2026年9月8日至9日" in html
    # the page-wide calculation stamp is 2026-09-09 and must not stand alone
    assert "Levels as of 9 September 2026" not in html
    assert "As of 9 September 2026" not in html


def test_legend_omits_undrawn_comparison_windows() -> None:
    as_of = date(2026, 9, 9)
    extra = {
        tenor: [{"t": as_of.isoformat(), "v": 4.0 + i * 0.02}]
        for i, tenor in enumerate(NOMINAL_TENORS)
    }
    hero = _hero(_snapshot(extra_points=extra, as_of=as_of))
    assert hero["chart"]["has_today"] is True
    assert hero["chart"]["has_prior_close"] is False
    assert hero["chart"]["has_prior_month"] is False
    html = _render_panel(hero)
    assert hero["first_nightly"]["en"] == NULL_FIRST_NIGHTLY_EN
    assert hero["first_nightly"]["zh"] == NULL_FIRST_NIGHTLY_ZH
    # autoescape turns the apostrophe in Today's into &#39;
    assert "curve is shown alone" in html
    assert "no earlier curve is on file" in html
    assert NULL_FIRST_NIGHTLY_ZH in html
    assert LEGEND_CLOSE_NULL_EN in html
    assert LEGEND_CLOSE_NULL_ZH in html
    assert LEGEND_MONTH_NULL_EN in html
    assert LEGEND_MONTH_NULL_ZH in html
    # the reason the round-3 ZH gave (第二天 = "the next day") is gone, and the
    # month line no longer garden-paths on 前线 ("front line")
    assert "第二天" not in html
    assert "一个月前线" not in html
    assert 'class="is-close"' not in html
    assert 'class="is-month"' not in html
    assert 'class="is-today"' in html


def test_hero_renders_below_the_suite_bar_and_below_the_h1() -> None:
    """R2. Spec §2.5 places the hero immediately below the <h1>/identity block.
    The include is emitted from the shell's hero slot, so the reader meets the
    in-suite navigation bar, then the page title, then the hero — and the
    document outline is h1 then h2.
    """
    html = _render_rates_page(_snapshot())
    bar = html.find('<nav class="mq-suitenav"')
    shell_open = html.find('<main class="mq-shell"')
    h1 = html.find("<h1>")
    hero = html.find('id="mq-curve-hero"')
    assert -1 < bar < shell_open < h1 < hero, (bar, shell_open, h1, hero)
    assert hero < html.rfind("</main>")
    assert html.count("<h1>") == 1
    assert html.find("<h2>") > h1


def test_hero_slot_renders_nothing_for_a_view_without_a_curve_hero() -> None:
    """The slot is empty by default, so a page with no hero renders the bytes
    it rendered before the slot existed (proved end-to-end by T11).
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=True,
        undefined=StrictUndefined,
    )
    template = env.from_string(
        '{% import "_macro_suite_shell.html.j2" as shell %}'
        "[{{ shell.hero_slot(view) }}]"
    )
    assert template.render(view={"workspace": {}}) == "[]"
    assert template.render(view={"curve_hero": None}) == "[]"


def test_kicker_is_not_duplicated_on_the_panel() -> None:
    html = _render_panel(_hero(_snapshot()))
    assert html.count('class="mq-kicker"') == 0
    assert "The Treasury curve" in html


def test_cmt_component_histories_range_is_bilingual_plain() -> None:
    view = _view(_snapshot())
    entries = view["series"]["entries"]
    assert entries
    for item in entries:
        if item["series_id"] in TENOR_TO_SERIES.values():
            assert item["range"] is not None
            assert item["range"]["en"].startswith("From ")
            assert "至" in item["range"]["zh"]
            assert "T" not in item["range"]["en"]
            html = _render_rates_page(_snapshot())
            assert item["range"]["en"] in html
            assert item["range"]["zh"] in html
            break
    else:
        raise AssertionError("no CMT series entry in the view")


def test_panel_heading_dropped_kicker_not_rates_and_curves_twice() -> None:
    html = _render_rates_page(_snapshot())
    panel = html[html.find("mq-curve-hero"):html.find("mq-page") if "mq-page" in html else len(html)]
    # The panel itself no longer carries the Rates & Curves kicker; the page
    # identity in the shell still does.
    hero = html[html.find('id="mq-curve-hero"'):html.find("mq-curve-spreads")]
    assert "mq-kicker" not in hero


# ---------------------------------------------------------------------------
# Round 3 R6 / R7 — job order and T11 path closure
# ---------------------------------------------------------------------------
def _macro_suite_pages_job() -> dict[str, Any]:
    raw = yaml.safe_load(
        (ROOT / ".github" / "ci" / "legacy-jobs.yml").read_text(encoding="utf-8")
    )
    job = raw["jobs"]["market-os-macro-suite-pages"]
    assert isinstance(job, dict)
    return job


def test_packet_suite_is_the_first_pytest_step_in_the_job() -> None:
    job = _macro_suite_pages_job()
    steps = job["steps"]
    pytest_steps = [
        s for s in steps
        if re.search(r"pytest\s+tests/", str(s.get("run") or ""))
    ]
    assert pytest_steps, "job has no pytest steps"
    assert "tests/test_macro_rates_curves_route.py" in pytest_steps[0]["run"]
    for step in steps:
        assert "continue-on-error" not in step
    install = next(s for s in steps if "pip install" in str(s.get("run") or ""))
    assert "pandas" not in install["run"]
    assert "numpy" not in install["run"]


def test_t11_site_pages_are_listed_in_the_exclusive_job_paths() -> None:
    job = _macro_suite_pages_job()
    paths = list(job["paths"])
    for rel in T11_SITE_PAGES:
        assert rel in paths, rel
    assert all(not p.endswith("bonds.html") for p in paths)
    assert all("bonds_guard" not in p for p in paths)


def test_shape_inverted_both_carries_a_gloss() -> None:
    html = _render_panel(_hero(_snapshot(levels=_inverted_levels())))
    assert SHAPE_INVERTED_BOTH_EN in html
    assert SHAPE_INVERTED_BOTH_ZH in html
    assert SHAPE_INVERTED_FRONT_EN not in html
    assert SHAPE_INVERTED_BELLY_EN not in html
    assert SHAPE_NORMAL_EN not in html


def test_shape_unstated_when_deciding_maturity_is_absent() -> None:
    """R9.1. 10y absent, six tenors present → unstated, never NORMAL."""
    skip = frozenset({"10y", "7y", "20y", "30y"})
    hero = _hero(_snapshot(skip_tenors=skip))
    present = [row for row in hero["tenors"] if row["today"] is not None]
    assert len(present) == 6
    assert hero["ok"] is True
    html = _render_panel(hero)
    assert hero["shape_read"]["en"] == SHAPE_UNSTATED_EN
    assert hero["shape_read"]["zh"] == SHAPE_UNSTATED_ZH
    assert "a deciding maturity has no reading." in html
    assert SHAPE_UNSTATED_ZH in html
    assert SHAPE_NORMAL_EN not in html
    assert SHAPE_NORMAL_ZH not in html
    assert SHAPE_FLAT_EN not in html


def test_en_short_tenors_are_mo_and_yr() -> None:
    """R9.3. EN shorts are real words; ZH shorts stay as they were."""
    ticks = _hero(_snapshot())["chart"]["x_ticks"]
    assert [tick["short"]["en"] for tick in ticks] == [
        "3 mo", "6 mo", "1 yr", "2 yr", "3 yr", "5 yr", "7 yr", "10 yr",
        "20 yr", "30 yr",
    ]
    assert [tick["short"]["zh"] for tick in ticks] == [
        "3个月", "6个月", "1年", "2年", "3年", "5年", "7年", "10年", "20年", "30年",
    ]
    html = _render_panel(_hero(_snapshot()))
    assert "3 mo" in html
    assert ">3m<" not in html
    assert "3个月" in html


def test_spread_level_drops_forced_plus_and_is_labelled_spread_now() -> None:
    """R9.4. The level has no forced plus; a negative keeps its minus."""
    html = _render_panel(_hero(_snapshot(levels=_complete_levels())))
    assert SPREAD_NOW_EN in html
    assert SPREAD_NOW_ZH in html
    assert "+0.45 percentage points" not in html
    assert "0.45 percentage points" in html
    assert "0.45个百分点" in html
    inverted = _render_panel(_hero(_snapshot(levels=_inverted_front_levels())))
    assert SPREAD_NOW_EN in inverted
    assert "-0.30 percentage points" in inverted
    assert "-0.30个百分点" in inverted
    assert CHANGE_CLOSE_EN in html
    assert CHANGE_CLOSE_ZH in html
    assert CHANGE_MONTH_EN in html
    assert CHANGE_MONTH_ZH in html


def test_partial_empty_series_range_is_typed_bilingual_not_none_token() -> None:
    """REQUIRED 1 / A1. A PARTIAL snapshot with one empty CMT entry (and any
    other zero-usable-points series) must emit the frozen bilingual range
    sentence. first/last stay None. The page must not print the token None.
    """
    snap = _snapshot(skip_tenors=frozenset({"7y"}))
    assert snap["series"]["status"] == "PARTIAL"
    snap["series"]["items"].append({
        "series_id": "other_non_cmt",
        "label": _pair("Other published series", "其他已发布序列"),
        "unit": "percent",
        "basis": "constant_maturity_investment_basis",
        "points": [],
        "source_ref": "TEST:other",
        "freshness": "SOURCE_FAILED",
        "revision_behavior": "recomputed each owner cadence from prior-only owner reads",
    })
    view = _view(snap)
    by_id = {item["series_id"]: item for item in view["series"]["entries"]}
    for series_id in ("us7y", "other_non_cmt"):
        item = by_id[series_id]
        assert item["count"] == 0
        assert item["first"] is None
        assert item["last"] is None
        assert item["range"] == {"en": EMPTY_HISTORY_EN, "zh": EMPTY_HISTORY_ZH}
    html = _render_rates_page(snap)
    # autoescape turns the apostrophe in tonight's into &#39;
    assert "No history published for this series in tonight&#39;s data." in html
    assert EMPTY_HISTORY_ZH in html
    assert "None → None" not in html
    table_start = html.find('<section class="mq-series"')
    assert table_start != -1
    table_end = html.find("</section>", table_start)
    table = html[table_start:table_end]
    assert EMPTY_HISTORY_ZH in table
    assert "None" not in table
    # h7 REQUIRED 1: this fixture already carries state_label with no state_id
    # and no method_version. The whole visible page (EN and ZH live in one
    # bilingual document) must not print the machine token None.
    assert snap["headline"]["state_id"] is None
    assert snap["headline"]["state_label"]["en"]
    assert snap["headline"]["state_label"]["zh"]
    assert snap["headline"].get("method_version") is None
    _assert_no_standalone_none_in_page(html)


_NONE_TOKEN = re.compile(r"\bNone\b")
_SCRIPT_OR_STYLE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1>", re.I | re.S,
)


def _visible_page_text(html: str) -> str:
    """Rendered page text with script and style stripped."""
    return _SCRIPT_OR_STYLE.sub(" ", html)


def _assert_no_standalone_none_in_page(html: str) -> None:
    visible = _visible_page_text(html)
    hit = _NONE_TOKEN.search(visible)
    assert hit is None, (
        "standalone None token in visible page text: "
        + visible[max(0, hit.start() - 80): hit.end() + 80]
    )


_CJK_CP = re.compile(r"[\u3400-\u9FFF\uF900-\uFAFF\u3000-\u303F\uFF00-\uFFEF]")
_CURVE_BLOCK_START = "_CURVE_TENOR_LABELS"
_ZH_TITLE_EXACT = (
    "{{ curve.heading.zh }}——{{ curve.subtitle.zh }}"
    "{% if curve.as_of_caption %}——{{ curve.as_of_caption.zh }}{% endif %}"
)


def _is_cjk(ch: str) -> bool:
    return bool(ch) and _CJK_CP.match(ch) is not None


def _ascii_space_adjoining_cjk(text: str) -> list[str]:
    """Snippets where an ASCII space sits next to a CJK codepoint."""
    hits: list[str] = []
    for i, ch in enumerate(text):
        if ch != " ":
            continue
        left = text[i - 1] if i else ""
        right = text[i + 1] if i + 1 < len(text) else ""
        if _is_cjk(left) or _is_cjk(right):
            hits.append(text[max(0, i - 12): i + 13])
    return hits


def _zh_string_literals_in_curve_block() -> list[str]:
    """ZH string literals in the curve block. Comments are outside the AST."""
    src = (ROOT / "lib" / "macro_suite_view.py").read_text(encoding="utf-8")
    lines = src.splitlines()
    start = next(
        i for i, line in enumerate(lines, 1) if line.startswith(_CURVE_BLOCK_START)
    )
    end = next(
        i for i, line in enumerate(lines, 1)
        if line.startswith("def build_view")
    )
    tree = ast.parse(src)
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        lineno = getattr(node, "lineno", 0)
        if start <= lineno < end and _CJK_CP.search(node.value):
            found.append(node.value)
    assert found, "curve block yielded no ZH literals"
    return found


def test_r95_zh_curve_copy_has_no_ascii_space_adjoining_cjk() -> None:
    """REQUIRED 5 / A4. No ZH literal in the curve block, and no ZH text the
    panel renders, may put an ASCII space next to a CJK codepoint. The ZH
    SVG title is the frozen A4 form.
    """
    for literal in _zh_string_literals_in_curve_block():
        hits = _ascii_space_adjoining_cjk(literal)
        assert not hits, (literal, hits)
    panel_src = (TEMPLATES / "_curve_panel.html.j2").read_text(encoding="utf-8")
    assert _ZH_TITLE_EXACT in panel_src
    html = _render_panel(_hero(_snapshot()))
    cjk_runs = [chunk for chunk in re.findall(r">([^<]+)<", html) if _CJK_CP.search(chunk)]
    assert cjk_runs, "panel rendered no CJK text"
    for chunk in cjk_runs:
        hits = _ascii_space_adjoining_cjk(chunk)
        assert not hits, (chunk, hits)
