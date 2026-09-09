"""A-F01-W4-1: Treasury curve-shape hero on the existing rates_curves route.

RED-first and fixture-driven. Every test builds a synthetic
``mastermind.macro_workspace_snapshot.v1`` snapshot (or a minimal series
fixture). No test touches ``data/fred/*.parquet`` or the network.

The twelve cases pin: the hero is rates_curves-only, ten nominal CMT tenors
in registry order, prior-close / prior-month arithmetic, honest nulls, the
context_only ceiling, two arithmetic spreads, EN+ZH copy, whole-panel null,
byte preservation of the bonds hub and the other thirteen suite pages, and
no import of the yield-curve engine.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
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
# Word-boundary / exact-token checks: a tenor id like "3m" is not "band".
CEILING_EN = (
    "prob", "odds", "score", "rank", "band", "signal", "forecast",
    "bull", "bear", "lean",
)
CEILING_ZH = ("概率", "评分", "预测", "看多", "看空")

SHAPE_NORMAL_EN = (
    "The curve is upward-sloping — longer maturities pay more than shorter ones."
)
SHAPE_NORMAL_ZH = "曲线呈正常形态 — 期限越长，收益率越高。"
SHAPE_INVERTED_EN = (
    "The curve is inverted — some shorter maturities pay more than longer ones."
)
SHAPE_INVERTED_ZH = "曲线出现倒挂 — 部分短期利率高于长期利率。"
NULL_PANEL_EN = "The curve panel needs tonight's Treasury data, which did not arrive."
NULL_PANEL_ZH = "曲线面板需要当晚的美债数据，但数据未能到达。"
NULL_TENOR_EN = "No reading for this maturity in tonight's data."
NULL_TENOR_ZH = "本次数据未覆盖该期限。"

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
    """today, prior_close, prior_month per tenor. Upward-sloping today."""
    # today values climb with maturity (normal curve)
    today = {
        "3m": 4.31, "6m": 4.28, "1y": 4.22, "2y": 4.10, "3y": 4.05,
        "5y": 4.08, "7y": 4.12, "10y": 4.18, "20y": 4.45, "30y": 4.55,
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
    lowered = text.lower()
    hits: list[str] = []
    for token in CEILING_EN:
        # Token as a whole word, so "3m" does not match "band" etc.
        if re.search(rf"(?<![a-z0-9_]){re.escape(token)}(?![a-z0-9_])", lowered):
            hits.append(token)
    for token in CEILING_ZH:
        if token in text:
            hits.append(token)
    return hits


def _git_show(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"origin/main:{path}"], cwd=ROOT)


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


# ---------------------------------------------------------------------------
# T7
# ---------------------------------------------------------------------------
def test_7_two_spreads_only_arithmetic_not_model_output() -> None:
    hero = _hero(_snapshot())
    spreads = hero["spreads"]
    assert [s["id"] for s in spreads] == ["10y3m", "2s10s"]
    by_tenor = {row["tenor"]: row for row in hero["tenors"]}
    ten_minus_three = by_tenor["10y"]["today"] - by_tenor["3m"]["today"]
    two_minus_ten = by_tenor["2y"]["today"] - by_tenor["10y"]["today"]
    by_id = {s["id"]: s for s in spreads}
    assert by_id["10y3m"]["today"] == pytest.approx(ten_minus_three)
    assert by_id["2s10s"]["today"] == pytest.approx(two_minus_ten)
    # Deltas are the same arithmetic on the comparison windows.
    close_10y3m = by_tenor["10y"]["prior_close"] - by_tenor["3m"]["prior_close"]
    assert by_id["10y3m"]["delta_close"] == pytest.approx(
        by_id["10y3m"]["today"] - close_10y3m
    )


# ---------------------------------------------------------------------------
# T8
# ---------------------------------------------------------------------------
def test_8_en_and_zh_both_render() -> None:
    html = _render_rates_page(_snapshot())
    assert SHAPE_NORMAL_EN in html or SHAPE_INVERTED_EN in html
    assert SHAPE_NORMAL_ZH in html or SHAPE_INVERTED_ZH in html
    assert "The Treasury curve" in html
    assert "美债收益率曲线" in html
    assert "today vs the prior close vs a month ago" in html
    assert "今日 vs 上一交易日收盘 vs 一个月前" in html
    assert "10-year minus 3-month" in html
    assert "10年期减3月期" in html
    assert "2-year minus 10-year" in html
    assert "2年期减10年期" in html
    assert "Today" in html and "今日" in html
    assert "Prior close" in html and "上一交易日收盘" in html
    assert "A month ago" in html and "一个月前" in html


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
    assert "<path" not in html or "mq-curve-null" in html


# ---------------------------------------------------------------------------
# T10
# ---------------------------------------------------------------------------
def test_10_bonds_hub_output_is_byte_identical() -> None:
    """Preservation at the render artifact, not only a source diff.

    ``scripts/build_bonds.py:main`` stamps ``datetime.now`` into the page and
    writes the live ``site/`` and ``data/bonds/`` trees, so two consecutive
    builder runs are never byte-identical even with no code change. This test
    therefore compares the committed bonds hub HTML and its three owner files
    to ``origin/main`` — the render-level proof that this packet did not
    rebuild or rewrite them.
    """
    for rel in (
        "templates/bonds.html.j2",
        "scripts/build_bonds.py",
        "engine/yield_curve.py",
        "site/bonds.html",
    ):
        current = (ROOT / rel).read_bytes()
        origin = _git_show(rel)
        assert current == origin, rel


# ---------------------------------------------------------------------------
# T11
# ---------------------------------------------------------------------------
def test_11_thirteen_other_suite_pages_byte_identical(tmp_path: Path) -> None:
    untouched = [
        p for p in builder.SUITE_PAGES if p.workspace_id != "rates_curves"
    ]
    assert len(untouched) == 13
    for page in untouched:
        rel = f"templates/{page.template}"
        assert (ROOT / rel).read_bytes() == _git_show(rel), rel
    for rel in (
        "templates/_macro_suite_shell.html.j2",
        "templates/_macro_suite_nav.html.j2",
        "templates/macro_monetary.html.j2",
        "templates/macro_suite.css",
        "templates/macro_suite.js",
        "templates/_navlinks.html.j2",
    ):
        assert (ROOT / rel).read_bytes() == _git_show(rel), rel

    # Render-level: the other thirteen pages do not carry the new hero.
    out = tmp_path / "site"
    pages = builder.render(
        ROOT, data_root=ROOT / "site" / "macrodata",
        out_dir=out, page_built_at=BUILT_AT,
    )
    by_name = {p.name: p.read_text(encoding="utf-8") for p in pages}
    for page in untouched:
        html = by_name[page.output]
        assert "mq-curve-hero" not in html, page.output
        assert "The Treasury curve" not in html, page.output
        assert "美债收益率曲线" not in html, page.output
    hub = by_name[builder.HUB_PAGE.output]
    assert "mq-curve-hero" not in hub


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
