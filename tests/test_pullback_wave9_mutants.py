"""Killers for the wave-9 mutants the standing suites let survive.

A mutation survey of the "Pullback underway" chart wave — 28 single-edit
mutants across the fragment's chart block and signed-zero rule and the
presenter's chart-name assignment and window guards, each run against the
eight standing pullback suites (-x -q --tb=no) — killed 19 and classed one
equivalent; each test here kills at least one of the nine true survivors and
passes on the restored sources.

id | site | change | verdict | killer
---|------|--------|---------|-------
A01 | _risk_radar_pullback_depth.html.j2:197 | drop ``_chart_en is string`` | SURVIVED | test_the_chart_name_refuses_a_non_string_label
A02 | _risk_radar_pullback_depth.html.j2:197 | drop ``_chart_zh is string`` | SURVIVED | test_the_chart_name_refuses_a_non_string_label
A03 | _risk_radar_pullback_depth.html.j2:197 | drop ``_chart_en`` truthiness | SURVIVED | test_the_chart_name_refuses_an_empty_label
A04 | _risk_radar_pullback_depth.html.j2:197 | drop ``_chart_zh`` truthiness | SURVIVED | test_the_chart_name_refuses_an_empty_label
A05 | _risk_radar_pullback_depth.html.j2:197 | ``and`` -> ``or`` across the guard | SURVIVED | test_the_chart_name_needs_both_labels_not_either
A06 | _risk_radar_pullback_depth.html.j2:200 | span id no longer matches aria-labelledby | KILLED (chart accessible-name suite)
A07 | _risk_radar_pullback_depth.html.j2:201 | drop ``aria-hidden="true"`` | KILLED (chart accessible-name suite)
A08 | _risk_radar_pullback_depth.html.j2:200 | swap the .l-en/.l-zh classes | KILLED (chart accessible-name suite)
A09 | _risk_radar_pullback_depth.html.j2:199 | drop ``role="img"`` | KILLED (chart accessible-name suite)
A10 | _risk_radar_pullback_depth.html.j2:203 | ``{%- else %}`` -> ``{% else %}`` | KILLED (byte-identity pin)
A11 | _risk_radar_pullback_depth.html.j2:197 | ``{%- set %}`` -> ``{% set %}`` | EQUIVALENT — pair-redundant: the preceding set's ``-%}`` already trims the shared whitespace; the kill set (including the sha256 byte-identity pin) passes and a three-state render gallery is byte-identical
A12 | _risk_radar_pullback_depth.html.j2:205 | ``{%- endif %}`` -> ``{% endif %}`` | KILLED (byte-identity pin)
A13 | _risk_radar_pullback_depth.html.j2:146 | metric ``+`` prefix unconditional | SURVIVED | test_a_reclaim_that_rounds_to_zero_prints_the_unsigned_metric
A14 | _risk_radar_pullback_depth.html.j2:146 | ``!=`` -> ``==`` | KILLED (reclaim +1.0% pins; also killed by the A13 killer)
A15 | _risk_radar_pullback_depth.html.j2:197 | negate the whole guard | KILLED (unnamed-branch pin)
B01 | lib/pullback_depth.py:271 | swap the chart_label_en/zh assignment | KILLED (SPY / Shanghai Composite asserts)
B02 | lib/pullback_depth.py:269 | drop ``if chart else None`` | SURVIVED | test_a_chart_that_was_not_drawn_carries_no_name_pair
B03 | lib/pullback_depth.py:254 | ``> 0`` -> ``>= 0`` on the rounded end | KILLED (standing suites; the boundary is now pinned explicitly by test_an_end_of_exactly_zero_prints_an_unsigned_chart_tag)
B04 | lib/pullback_depth.py:254 | drop the ``round(..., 1)`` | SURVIVED | test_an_end_that_rounds_to_zero_prints_an_unsigned_chart_tag
B05 | lib/pullback_depth.py:254 | ``{:z.1f}%`` -> ``{:.1f}%`` | KILLED (fake-renderer value_fmt pin)
B06 | lib/pullback_depth.py:257 | ``minus="−"`` -> ``minus="-"`` | KILLED (U+2212 glyph inside the byte-identity pin)
C01 | lib/pullback_depth.py:239 | ``>=`` -> ``>`` on the chart minimum | KILLED (four-point minimum)
C02 | lib/pullback_depth.py:20 | ``MIN_CHART_POINTS = 4`` -> ``5`` | KILLED (four-point minimum)
C03 | lib/pullback_depth.py:239 | drop the length term | KILLED (short-withheld states)
C04 | lib/pullback_depth.py:241 | swap ``short``/``uncovered`` | KILLED (withheld copy pins)
C05 | lib/pullback_depth.py:172 | drop the peak-membership refusal | KILLED (pre-episode refusal)
C06 | lib/pullback_depth.py:174 | ``start = dates.index(peak)`` -> ``0`` | KILLED (window starts at the retained high)
C07 | lib/pullback_depth.py:176 | allow a stale end | SURVIVED | test_a_window_that_ends_before_asof_is_not_drawn
C08 | lib/pullback_depth.py:201 | ``vals[:-1] + [end]`` -> ``list(vals)`` | KILLED (drawn end from the metric's own ratio)
C09 | lib/pullback_depth.py:176 | ``!=`` -> ``<`` on the as-of end | SURVIVED | test_a_window_that_ends_after_asof_is_not_drawn
A16 | _risk_radar_pullback_depth.html.j2:202 | drop ``|e`` on both chart-name spans | SURVIVED | test_the_chart_name_escapes_metacharacters_without_autoescape

Every input is synthetic; no forecast, probability or odds is produced or
asserted anywhere in this module.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from tests.test_pullback_depth_a11y import EVIDENCE, _observation
from tests.test_risk_radar_pullback_depth_template import native_view, render

# The chart figure's own end tag is the only place the sign of a rounding-to-
# zero reclaim is printed; the metric and the history table already print it.
_ILX_TAG = re.compile(r'class="ilx-tag">([^<]*)</span>')


def _soup(view, market="us"):
    return BeautifulSoup(render(view, market), "html.parser")


def _name_root(soup):
    return soup.select_one('[role="img"][aria-labelledby]')


def test_the_chart_name_refuses_a_non_string_label():
    """A presenter regression that leaks a number must not name the chart."""
    for field, bad, other in (
            ("chart_label_en", 123, "已观测回撤"),
            ("chart_label_zh", 123, "Observed drawdown")):
        view = native_view("us")
        view[field] = bad
        view["chart_label_zh" if field == "chart_label_en" else "chart_label_en"] = other
        soup = _soup(view)
        assert _name_root(soup) is None
        assert soup.select_one('.rrp-chart[aria-hidden="true"]') is not None


def test_the_chart_name_refuses_an_empty_label():
    """An empty label is absent, not blank: the chart stays unnamed."""
    for field, other in (
            ("chart_label_en", "已观测回撤"),
            ("chart_label_zh", "Observed drawdown")):
        view = native_view("us")
        view[field] = ""
        view["chart_label_zh" if field == "chart_label_en" else "chart_label_en"] = other
        soup = _soup(view)
        assert _name_root(soup) is None
        assert soup.select_one('.rrp-chart[aria-hidden="true"]') is not None


def test_the_chart_name_needs_both_labels_not_either():
    """One language alone names nothing; the fragment must not invent the other."""
    for fields in ({"chart_label_en": "Observed drawdown"},
                   {"chart_label_zh": "已观测回撤"}):
        view = native_view("us")
        view.update(fields)
        soup = _soup(view)
        assert _name_root(soup) is None
        assert "None" not in (soup.get_text() or "")


def test_a_reclaim_that_rounds_to_zero_prints_the_unsigned_metric():
    """close 100.04 against a 100.0 high: +0.04% rounds to 0.0, unsigned."""
    view = native_view("us")
    view["phase"] = "recovering"
    view["observation"]["phase"] = "recovering"
    view["observation"]["close"] = 100.04
    view["observation"]["peak_close"] = 100.0
    soup = _soup(view)
    metric = soup.select_one('[data-metric="current"]')
    assert metric is not None
    assert metric.get_text(strip=True) == "0.0%"


def test_a_chart_that_was_not_drawn_carries_no_name_pair():
    """A young window withholds the chart; the view must not grow a name."""
    view = _observation(
        "us", "underway",
        path={"dates": ["2026-09-14", "2026-09-21", "2026-09-30"],
              "vals": [0.0, -7.4, -6.8]},
        close=93.2, peak_close=100.0, low_close=92.6, **dict(EVIDENCE))
    assert view["detail_chart_html"] == ""
    assert view["detail_withheld"] == "short"
    assert "chart_label_en" not in view
    assert "chart_label_zh" not in view


def test_an_end_that_rounds_to_zero_prints_an_unsigned_chart_tag():
    """end = +0.04 rounds to one tenth of zero: the tag prints 0.0%, no '+'."""
    view = _observation(
        "us", "recovering",
        path={"dates": ["2026-09-14", "2026-09-21", "2026-09-24", "2026-09-30"],
              "vals": [0.0, -7.4, -3.1, 0.04]},
        close=100.04, peak_close=100.0, low_close=92.6, **dict(EVIDENCE))
    tags = _ILX_TAG.findall(view["detail_chart_html"])
    assert tags and tags[-1] == "0.0%"
    assert "+0.0%" not in view["detail_chart_html"]


def test_an_end_of_exactly_zero_prints_an_unsigned_chart_tag():
    """A close back at the high ends at exactly 0.0: unsigned, never '+0.0%'."""
    view = _observation(
        "us", "recovering",
        path={"dates": ["2026-09-14", "2026-09-21", "2026-09-24", "2026-09-30"],
              "vals": [0.0, -7.4, -3.1, 0.0]},
        close=100.0, peak_close=100.0, low_close=92.6, **dict(EVIDENCE))
    tags = _ILX_TAG.findall(view["detail_chart_html"])
    assert tags and tags[-1] == "0.0%"
    assert "+0.0%" not in view["detail_chart_html"]


def test_a_window_that_ends_before_asof_is_not_drawn():
    """A path whose last session is older than asof supports no window."""
    view = _observation(
        "us", "underway",
        path={"dates": ["2026-09-14", "2026-09-21", "2026-09-24", "2026-09-30"],
              "vals": [0.0, -7.4, -5.2, -6.8]},
        asof="2026-10-01", close=93.2, peak_close=100.0, low_close=92.6,
        **dict(EVIDENCE))
    assert view["detail_chart_html"] == ""
    assert view["detail_withheld"] == "uncovered"
    assert "chart_label_en" not in view
    assert "chart_label_zh" not in view


def test_a_window_that_ends_after_asof_is_not_drawn():
    """A path whose last session is newer than asof supports no window either."""
    view = _observation(
        "us", "underway",
        path={"dates": ["2026-09-14", "2026-09-21", "2026-09-24", "2026-10-02"],
              "vals": [0.0, -7.4, -5.2, -6.8]},
        asof="2026-09-30", close=93.2, peak_close=100.0, low_close=92.6,
        **dict(EVIDENCE))
    assert view["detail_chart_html"] == ""
    assert view["detail_withheld"] == "uncovered"


def test_the_chart_name_escapes_metacharacters_without_autoescape():
    """The China page renders without autoescape, so the spans escape for it."""
    view = native_view("cn")
    view["chart_label_en"] = "A & B <drawdown>"
    view["chart_label_zh"] = "已观测回撤"
    html = render(view, "cn")
    assert "A &amp; B &lt;drawdown&gt;" in html
    assert "A & B" not in html and "<drawdown>" not in html
