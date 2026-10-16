"""Accessible static Jinja component for admitted, gap-aware IM02 charts."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from html.parser import HTMLParser

import pytest
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from tests.test_intl_chart_publication import inputs, _case, _project
from lib.intl_chart_geometry import build_chart_geometry


def _render(model, *, identity="im-test", labels=None):
    folder = Path(__file__).resolve().parents[1] / "templates"
    env = Environment(loader=FileSystemLoader(folder),
                      autoescape=select_autoescape(["j2"]),
                      undefined=StrictUndefined)
    macro = env.get_template("intl_workspace/chart_cohorts.html.j2").module
    return str(macro.render_source_charts(model, identity, labels or {
        "JP": {"en": "Japan", "zh": "日本"},
        "GB": {"en": "United Kingdom", "zh": "英国"},
    }))


def _model(inputs):
    view, raw, evidence = _case(inputs)
    return build_chart_geometry(_project(view, raw, evidence))


def test_two_market_accessible_svg_and_named_table_are_bilingual(inputs):
    html = _render(_model(inputs))
    assert html.count('data-im-chart-cohort="c0"') == 1
    assert 'viewBox="0 0 640 220"' in html and 'width="100%"' in html
    assert 'role="img"' in html and 'aria-labelledby=' in html
    assert '<summary id="im-test-chart-c0-title">' in html
    assert '<figcaption id="im-test-chart-c0-desc">' in html
    assert 'aria-labelledby="im-test-chart-heading im-test-chart-c0-title"' in html
    assert 'aria-describedby="im-test-chart-intro im-test-chart-c0-desc"' in html
    assert 'Same starting point. Different paths.' in html
    assert '相同起点，不同走势。' in html
    assert 'data-im-chart-series="JP"' in html
    assert 'data-im-chart-series="GB"' in html
    assert 'data-im-chart-data-table' in html
    assert 'data-im-chart-table-market="JP"' in html
    assert 'data-im-chart-table-market="GB"' in html
    assert 'no missing price or FX value was filled' in html
    assert 'Line and point styles identify markets. Unobserved dates break the series' in html
    assert '线型和点形用于区分市场。未观测日期中断曲线' in html
    assert 'data-im-chart-benchmark-unavailable' in html
    assert 'data-im-chart-selection-unavailable hidden' in html
    assert 'data-im-chart-baseline-label' in html
    assert 'Horizontal dashed reference line: 100.' in html
    assert '水平虚线基准：100。' in html
    assert '<text x="4" y="' not in html
    assert '<line x1="0" y1="6" x2="31" y2="6"' in html
    assert '>2025-12-18</time>' in html


def test_partial_source_chart_shows_actual_gap_and_not_fake_interpolation(inputs):
    _, original = inputs
    frame = original.copy()
    frame.loc[frame.index[12], "USDJPY=X"] = float("nan")
    view, raw, evidence = _case(inputs, data=frame)
    geometry = build_chart_geometry(_project(view, raw, evidence))
    japan = next(line for line in geometry["cohorts"][0]["paths"] if line["market_id"] == "JP")
    assert japan["gaps"] >= 1
    assert len(japan["segments"]) >= 2
    html = _render(geometry)
    assert html.count('data-im-chart-series="JP"') == len(japan["segments"])
    assert f"<td>{japan['gaps']}</td>" in html
    assert 'not available: its source and comparison window' in html


def test_unqualified_no_same_window_keeps_existing_compare_fallback(inputs):
    view, raw, evidence = _case(inputs, drop_fx=True)
    geo = build_chart_geometry(_project(view, raw, evidence))
    assert geo["status"] == "unavailable"
    assert _render(geo) == ""


def test_owner_market_labels_are_escaped_and_ids_are_unique(inputs):
    geo = _model(inputs)
    duplicated = deepcopy(geo)
    duplicated["cohorts"].append(deepcopy(geo["cohorts"][0]))
    duplicated["cohorts"][1]["id"] = "c1"
    html = _render(duplicated, identity="safe-prefix",
                   labels={"JP":{"en":"<script>alert(1)</script>","zh":"日本"},
                           "GB":{"en":"United Kingdom","zh":"英国"}})
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html
    assert html.count('id="safe-prefix-chart-c0-title"') == 1
    assert html.count('id="safe-prefix-chart-c1-title"') == 1
    assert html.count('data-im-chart-data-table') == 2



def test_discontinuous_isolated_observation_is_drawn_as_a_point(inputs):
    model = _model(inputs)
    from lib.intl_chart_geometry import build_chart_geometry
    from tests.test_intl_chart_publication import _case, _project
    view, raw, evidence = _case(inputs)
    admitted = _project(view, raw, evidence)
    jp = next(line for line in admitted["series"] if line["market_id"] == "JP")
    # Introduce two separate source-null intervals, isolating the observed
    # point between them. The geometry may not join across either gap.
    for index in (8, 10):
        jp["points"][index]["rebased"] = None
        jp["points"][index]["reason"] = "missing_fx"
    jp["gaps"] = 2
    jp["status"] = "source_bound_partial"
    geom = build_chart_geometry(admitted)
    japan = next(p for p in geom["cohorts"][0]["paths"] if p["market_id"] == "JP")
    assert any(part["count"] == 1 for part in japan["segments"])
    html = _render(geom)
    assert '<g data-im-chart-series="JP" data-im-chart-point' in html
    assert 'data-im-chart-point-key' in html

def test_chart_responsive_intrinsic_aspect_has_no_mobile_letterbox(inputs):
    """The same viewBox must retain geometry without a forced 220px phone box."""
    html = _render(_model(inputs))
    assert 'viewBox="0 0 640 220"' in html
    assert '<svg role="img"' in html
    assert 'height="220"' not in html
    assert 'style=' not in html
    assert 'preserveAspectRatio="xMidYMid meet"' in html
