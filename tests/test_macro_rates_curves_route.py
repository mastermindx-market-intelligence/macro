"""A-F01-W4-1: Treasury curve-shape hero on the existing rates_curves route.

RED-first and fixture-driven. Every test builds a synthetic
``mastermind.macro_workspace_snapshot.v1`` snapshot (or a minimal series
fixture). No test touches ``data/fred/*.parquet`` or the network.

The cases pin: the hero is rates_curves-only, ten nominal CMT tenors
in registry order, prior-close / prior-month arithmetic, honest nulls, the
context_only ceiling, two arithmetic spreads, EN+ZH copy, whole-panel null,
byte preservation of the bonds hub sources, the include appearing in exactly
one template, and no import of the yield-curve engine.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
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
SHAPE_NORMAL_ZH = "曲线呈正常形态 — 期限越长，收益率越高。"
SHAPE_INVERTED_EN = (
    "The curve is inverted — some shorter maturities pay more than longer ones."
)
SHAPE_INVERTED_ZH = "曲线出现倒挂 — 部分短期利率高于长期利率。"
NULL_PANEL_EN = "The curve panel needs the Treasury data from tonight, which did not arrive."
NULL_PANEL_ZH = "曲线面板需要当晚的美债数据，但数据未能到达。"
NULL_SEVEN_EN = "No reading for the 7-year in tonight's data."
NULL_SEVEN_ZH = "本次数据未覆盖7年期。"
CHANGE_CLOSE_EN = "Change since prior close"
CHANGE_CLOSE_ZH = "较上一交易日收盘变动"
CHANGE_MONTH_EN = "Change over a month"
CHANGE_MONTH_ZH = "较一个月前变动"
SUBTITLE_EN = "today versus the prior close versus a month ago"
SUBTITLE_ZH = "今日、上一交易日收盘与一个月前对比"

# Pinned 2026-09-09 against the three source files the spec names. These are
# sha256 of the working-tree bytes this packet must not rewrite. site/bonds.html
# is a nightly build artefact and is not pinned. Recompute the constants only
# when a later merge of this exclusive job is itself a bonds-hub change.
# Seat R3 allowed a manifest; this packet pins the three sources as constants.
_BONDS_SOURCE_SHA256 = {
    "templates/bonds.html.j2": (
        "9fe1cc0b49ffa4da6b0f6c4ba55658a712dbc32702542806c3bc23346431bef3"
    ),
    "scripts/build_bonds.py": (
        "18d44adffc8889b66be9afe48b7a9d8a9ab1246f6bdd4af5dc67d1335b97748a"
    ),
    "engine/yield_curve.py": (
        "51931aec691f724c99b206257797ed162118986dbb7bcba10a2a2bf75dd60bc1"
    ),
}

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
    """today, prior_close, prior_month per tenor. Downward-sloping today."""
    today = {
        "3m": 4.55, "6m": 4.48, "1y": 4.40, "2y": 4.32, "3y": 4.25,
        "5y": 4.18, "7y": 4.12, "10y": 4.05, "20y": 3.95, "30y": 3.90,
    }
    close = {k: round(v + 0.01, 4) for k, v in today.items()}
    month = {k: round(v + 0.07, 4) for k, v in today.items()}
    return {k: (today[k], close[k], month[k]) for k in NOMINAL_TENORS}


def _snapshot(*, workspace_id: str = "rates_curves",
              levels: dict[str, tuple[float, float, float]] | None = None,
              extra_points: dict[str, list[dict[str, Any]]] | None = None,
              skip_tenors: frozenset[str] = frozenset(),
              as_of: date = date(2026, 9, 9)) -> dict[str, Any]:
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
        "availability": {"state": "CURRENT", "required": [], "degraded": [],
                         "coverage_ratio": 1.0, "worst_freshness": "CURRENT",
                         "contradiction": {"present": False}, "reasons": []},
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
    assert "No reading for the 7-year" in html
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
    assert SHAPE_INVERTED_EN not in html
    assert SHAPE_INVERTED_ZH not in html


def test_8_inverted_fixture_renders_the_inverted_shape_sentence_only() -> None:
    html = _render_panel(_hero(_snapshot(levels=_inverted_levels())))
    assert SHAPE_INVERTED_EN in html
    assert SHAPE_INVERTED_ZH in html
    assert SHAPE_NORMAL_EN not in html
    assert SHAPE_NORMAL_ZH not in html


# ---------------------------------------------------------------------------
# T9
# ---------------------------------------------------------------------------
def test_9_whole_panel_honest_null_when_snapshot_incomplete() -> None:
    empty = _snapshot(levels={}, extra_points={}, skip_tenors=frozenset(NOMINAL_TENORS))
    hero = _hero(empty)
    assert hero["ok"] is False
    html = _render_panel(hero)
    assert NULL_PANEL_EN in html
    assert NULL_PANEL_ZH in html
    assert "<polyline" not in html
    assert "<path" not in html


# ---------------------------------------------------------------------------
# T10
# ---------------------------------------------------------------------------
def test_10_bonds_hub_sources_match_the_pinned_sha256() -> None:
    """Preservation of the three source files the spec names.

    site/bonds.html is a nightly build artefact and is not pinned. This test
    never shells to git and never compares against a moving ref.
    """
    for rel, expected in _BONDS_SOURCE_SHA256.items():
        digest = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        assert digest == expected, rel


# ---------------------------------------------------------------------------
# T11
# ---------------------------------------------------------------------------
def test_11_curve_panel_include_appears_in_exactly_one_template() -> None:
    """Seat R3 allowed a manifest; this packet greps templates/ for the include.

    The include must be the plain form (no ignore missing). Sibling suite
    templates must not grow a second copy.
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
    assert hits == ["macro_rates_curves.html.j2"]
    rates = (TEMPLATES / "macro_rates_curves.html.j2").read_text(encoding="utf-8")
    assert "ignore missing" not in rates
    for path in (ROOT / "templates").glob("macro_*.html.j2"):
        if path.name == "macro_rates_curves.html.j2":
            continue
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
        "scripts.build_bonds",
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
    # sys.modules assertion: building the rates_curves view must not load those engines.
    _view(_snapshot())
    for mod in (
        "engine.yield_curve",
        "engine.rates_inflation_command",
        "engine.yield_momentum",
        "scripts.build_bonds",
    ):
        assert mod not in sys.modules, mod


# ---------------------------------------------------------------------------
# R1 — SVG ticks are tspans, never HTML spans
# ---------------------------------------------------------------------------
def test_svg_tick_labels_are_tspans_not_html_spans() -> None:
    hero = _hero(_snapshot())
    html = _render_panel(hero)
    svg = _svg_inner(html)
    assert "<span" not in svg
    ticks = hero["chart"]["x_ticks"]
    assert len(ticks) == 10
    for tick in ticks:
        x = tick["x"]
        assert f'<text class="mq-curve-tick" x="{x}"' in svg
        assert f'<tspan class="l-en">{tick["label"]["en"]}</tspan>' in svg
        assert f'<tspan class="l-zh">{tick["label"]["zh"]}</tspan>' in svg


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
    # Legend still names the plotted LEVELS; change rows must not reuse those
    # labels as the only words in front of a delta.
    legend_close = html.find("is-close")
    deltas = html.find("mq-curve-deltas")
    assert 0 <= legend_close < deltas
    delta_block = html[deltas:]
    assert CHANGE_CLOSE_EN in delta_block
    assert "Prior close +" not in delta_block
    assert "A month ago +" not in delta_block
