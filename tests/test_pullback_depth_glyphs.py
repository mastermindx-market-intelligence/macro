"""Glyph + label contract for the pullback popup's chart and its presenters.

One close's drawdown must print ONE minus glyph across the panel: the headline
metric and the history table print U+2212 (the fragment renders the magnitude
with a '−' prefix), so the chart's own end tag must print the same glyph —
lib/illus.py formats visible numbers with str.format, which always emits ASCII
"-". The fix is an opt-in option: every other illus.illus caller in the repo
must stay byte-identical, so this file pins their output to the BASE renderer.

Every close path below is synthetic and is observed through the real
``lib.pullback_observation.observe()`` and presented by the real presenter,
the way tests/test_pullback_depth_presenter_properties.py does (helpers
imported, never copied).
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup

from lib.pullback_depth import present
from tests.test_pullback_depth_presenter_properties import (
    ARIA_EN,
    ARIA_ZH,
    _observe_case,
    rows_for,
)
from tests.test_risk_radar_pullback_depth_template import render

ROOT = Path(__file__).resolve().parents[1]
# The commit this contract is written against: the byte-identity pin below
# loads lib/illus.py exactly as it exists there.
BASE_COMMIT = "ee05fd772e89ecc2cdefadfc793c8f0c732a0f5c"

MINUS = "−"  # U+2212, the glyph the metric and the history table print


# --------------------------------------------------------------------------- #
# real-presenter fixtures
# --------------------------------------------------------------------------- #
def _presented(values):
    """Observe a synthetic path, present it, and render the shipped fragment.

    Returns (chart_html, fragment_html). The observation is stamped the way
    lib.us_pullback_observation.snapshot does, so the fragment qualifies it."""
    case = _observe_case(rows_for(values))
    chart = case["view"]["detail_chart_html"]
    assert chart, "the synthetic window was not drawn"
    stamped = dict(case["obs"], market="us",
                   valid_until="2026-10-13T21:00:00+00:00")
    html = render(present(stamped, market="us", aria_en=ARIA_EN, aria_zh=ARIA_ZH), "us")
    return chart, html


def _end_tag_text(chart):
    tag = BeautifulSoup(chart, "html.parser").select_one("span.ilx-tag")
    assert tag is not None, "the chart renders no end-value tag"
    return tag.get_text()


def _metric_text(html):
    metric = BeautifulSoup(html, "html.parser").select_one('[data-metric="current"]')
    assert metric is not None
    return metric.get_text(strip=True)


# --------------------------------------------------------------------------- #
# 1 — the chart's end tag prints the metric's minus glyph
# --------------------------------------------------------------------------- #
def test_chart_end_tag_prints_the_metric_minus_glyph():
    chart, html = _presented([100.0] * 62 + [94.5, 94.4, 94.6, 94.5])  # a -5.5% pullback
    tag = _end_tag_text(chart)
    assert MINUS in tag
    assert not re.search(r"-\d", tag), tag
    metric = _metric_text(html)
    assert metric == f"{MINUS}5.5%"
    assert tag == metric  # same number, same glyph, same 1-dp rounding


def test_chart_ref_label_and_corners_print_no_ascii_minus_before_a_digit():
    """Every other visible number the chart renders agrees with the glyph too.

    The only other visible-number site on this chart is the reference-level
    label (reference 0, unsigned); the corner captions are ISO dates, whose
    hyphens are punctuation, so the whole-figure scan strips dates first."""
    chart, _html = _presented([100.0] * 62 + [94.5, 94.4, 94.6, 94.5])
    soup = BeautifulSoup(chart, "html.parser")
    ref = soup.select_one(".ilx-reflab")
    assert ref is not None and ref.get_text(strip=True) == "0"
    for node in soup.select(".ilx-d"):
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", node.get_text(strip=True))
    without_dates = re.sub(r"\d{4}-\d{2}-\d{2}", "", soup.get_text())
    assert not re.search(r"-\d", without_dates), without_dates


# --------------------------------------------------------------------------- #
# 2 — a value that rounds to zero prints unsigned, in the chart and the metric
# --------------------------------------------------------------------------- #
def test_value_that_rounds_to_zero_prints_unsigned_in_chart_and_metric():
    chart, html = _presented([100.0] * 62 + [99.97, 99.96, 99.97, 99.98])
    tag = _end_tag_text(chart)
    assert tag == "0.0%"
    assert MINUS not in tag and "-" not in tag
    assert _metric_text(html) == "0.0%"


# --------------------------------------------------------------------------- #
# 3 — byte-identity: no other caller's output moves
# --------------------------------------------------------------------------- #
def _load_base_illus(tmp_path):
    """The BASE copy of lib/illus.py, imported as a standalone module."""
    shown = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{BASE_COMMIT}:lib/illus.py"],
        check=True, capture_output=True, text=True).stdout
    path = tmp_path / "base_illus.py"
    path.write_text(shown)
    spec = importlib.util.spec_from_file_location("base_illus_glyphs", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_DATES = ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04",
          "2026-09-05", "2026-09-08"]


def _shape(name, series, **kwargs):
    return (name, series, kwargs)


# Call shapes lifted from real illus.illus call sites elsewhere in the repo
# (scripts/build_*.py), each with negative values so a stray default sign
# change could not hide. One shape per distinct kind / value_fmt family.
OTHER_CALLER_SHAPES = [
    _shape("canada-price-line",
           {"dates": _DATES, "vals": [1.61, 1.62, -1.59, 1.64, -1.55, 1.6]},
           kind="line", accent="var(--teal)", height=92,
           value_fmt="{:,.2f}", aria_en="WTI price history"),
    _shape("canada-multi-signed",
           [{"label_en": "growth", "label_zh": "增长", "color": "var(--up)",
             "dates": _DATES, "vals": [0.4, -0.2, 0.9, -1.1, 0.3, 0.7]},
            {"label_en": "inflation", "label_zh": "通胀", "color": "var(--down)",
             "dates": _DATES, "vals": [2.1, 2.4, -0.5, 2.2, 1.8, 2.0]}],
           kind="multi", height=200, value_fmt="{:+.2f}", baseline=0,
           aria_en="Canada growth and inflation regime scores over time"),
    _shape("altdata-baseline-signed",
           {"dates": _DATES, "vals": [-0.4, 1.2, -1.8, 0.6, -0.2, 0.9]},
           kind="baseline", baseline=0.0, accent="var(--info)", height=58,
           value_fmt="{:+.1f}", aria_en="Trading intensity vs 20-day normal",
           aria_zh="成交强度相对20日常态"),
    _shape("china-property-drawdown",
           {"dates": _DATES, "vals": [0.0, -1.4, -2.8, -2.2, -3.1, -2.6]},
           kind="drawdown", accent="var(--down)", height=170, unit_en="%",
           value_fmt="{:,.2f}", aria_en="Property ETF drawdown chart"),
    _shape("hk-drawdown-default-fmt",
           {"dates": _DATES, "vals": [0.0, -3.0, -6.5, -5.0, -7.2, -6.1]},
           kind="drawdown", accent="var(--down)", height=150,
           aria_en="Drawdown from high"),
    _shape("crypto-spark-3g",
           {"dates": _DATES, "vals": [-0.52, 1.7, -12.4, 0.03, -0.9, 2.5]},
           kind="line", accent="var(--tone)", height=42, max_points=50,
           value_fmt="{:,.3g}", aria_en="token available price history"),
    _shape("bonds-gauge-reference-bands",
           {"dates": _DATES, "vals": [-12.0, 3.0, -25.0, 8.0, -4.0, 1.0]},
           kind="line", height=180, reference=0, value_fmt="{:,.0f}",
           bands=[{"hi": 0, "lo": None, "tint": "var(--muted)",
                   "label_en": "calm", "label_zh": "平静", "pos": "bottom"}],
           aria_en="MOVE rates volatility index"),
    _shape("bars-with-units",
           {"dates": _DATES, "vals": [-2.0, 1.5, -0.5, 3.0, -1.0, 0.5]},
           kind="bars", baseline=0, unit_en="%", unit_zh="%",
           value_fmt="{:+.1f}", aria_en="monthly change"),
]


def test_other_callers_render_byte_identical_to_base(tmp_path):
    from lib import illus

    base = _load_base_illus(tmp_path)
    checked = 0
    for name, series, kwargs in OTHER_CALLER_SHAPES:
        assert illus.illus(series, **kwargs) == base.illus(series, **kwargs), name
        checked += 1
    assert checked >= 5


def test_minus_option_changes_only_the_sign_glyph(tmp_path):
    """The option itself swaps exactly the sign, never the digits or rounding."""
    from lib import illus

    base = _load_base_illus(tmp_path)
    series = {"dates": _DATES, "vals": [0.0, -3.0, -6.5, -5.0, -7.2, -6.1]}
    kwargs = dict(kind="drawdown", accent="var(--down)", height=150,
                  aria_en="Drawdown from high")
    swapped = illus.illus(series, **kwargs, minus=MINUS)
    plain = base.illus(series, **kwargs)
    # Byte-level, the end tag's sign glyph is the ONLY difference (the corner
    # dates keep their ISO hyphens; nothing else in the figure carries a sign;
    # this shape passes no unit, so the tag is the bare number).
    assert swapped == plain.replace(">-6.1<", f">{MINUS}6.1<")
    tag = BeautifulSoup(swapped, "html.parser").select_one("span.ilx-tag")
    assert tag is not None and tag.get_text() == f"{MINUS}6.1"
