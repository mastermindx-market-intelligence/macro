"""Mutation-survey kills for the four-place tenth rule on the pullback surfaces.

Every displayed tenth of a pullback ratio is ``'%.1f'`` of the owner's
four-place value (the history row's precision), never of the raw binary
ratio: an exact half such as 10.25% sits a hair ABOVE 10.25 in binary64, so
formatting the raw double gives ``10.3`` where the four-place value gives
``10.2``. The rule lives in the four ``|round(4)`` filters of
``templates/_risk_radar_pullback_depth.html.j2`` (current, drawdown, worst,
rebound) and in ``round(end, 4)`` of ``lib/pullback_depth.py``
``episode_window``, whose drawn end tag must agree with them.

The sweep that produced the table below ran outside pytest against the
existing kill set (``tests/test_pullback_episode_fuzz.py``,
``tests/test_pullback_episode_fuzz_cn.py``,
``tests/test_pullback_depth_template_mutants.py``,
``tests/test_pullback_depth_mutants.py``,
``tests/test_pullback_depth_presenter_properties.py``,
``tests/test_pullback_observation_invariants.py``,
``tests/test_risk_radar_pullback_depth_template.py`` and
``tests/test_pullback_wave9_mutants.py``), one single-edit mutant at a time.
Each test here pins a behaviour a surviving mutant broke. Figures are
synthetic. Neither mutable source is modified.

EQUIVALENT rows need no killer and get none: the suites' fixtures quantize
every close to two decimals under a 100.0 peak, and over that whole input
space ``round(raw, 3)`` and ``round(raw, 5)`` return the IDENTICAL double to
``round(raw, 4)`` (measured: 8,001 drop closes 20.00-100.00, 3,000 reclaim
closes 100.01-130.00, 8,001 worst-site lows - zero tenth disagreements, max
``|round(raw, 3) - round(raw, 5)| = 0.0``). The raw double's noise (~1e-13)
is orders below the 5e-4 that could move the tenth.

Mutant table (id, file:line, change, verdict, killer):

T01 | templates/_risk_radar_pullback_depth.html.j2:148 | drop ``|round(4)`` at the up site | SURVIVED | test_us_close_above_high_half_prints_one_tenth
T02 | templates/_risk_radar_pullback_depth.html.j2:148 | ``round(4)`` -> ``round(1)`` at the up site | SURVIVED | test_us_close_above_high_half_prints_one_tenth
T03 | templates/_risk_radar_pullback_depth.html.j2:148 | ``round(4)`` -> ``round(3)`` at the up site | EQUIVALENT | 2-decimal sweep proof (module docstring)
T04 | templates/_risk_radar_pullback_depth.html.j2:148 | ``round(4)`` -> ``round(5)`` at the up site | EQUIVALENT | 2-decimal sweep proof (module docstring)
T05 | templates/_risk_radar_pullback_depth.html.j2:149 | drop ``|round(4)`` at the dd site | KILLED | test_i8_one_low_prints_one_tenth_on_an_exact_half
T06 | templates/_risk_radar_pullback_depth.html.j2:149 | ``round(4)`` -> ``round(1)`` at the dd site | KILLED | test_i8_one_low_prints_one_tenth_on_an_exact_half
T07 | templates/_risk_radar_pullback_depth.html.j2:149 | ``round(4)`` -> ``round(3)`` at the dd site | EQUIVALENT | 2-decimal sweep proof (module docstring)
T08 | templates/_risk_radar_pullback_depth.html.j2:149 | ``round(4)`` -> ``round(5)`` at the dd site | EQUIVALENT | 2-decimal sweep proof (module docstring)
T09 | templates/_risk_radar_pullback_depth.html.j2:153 | drop ``|round(4)`` at the worst site | KILLED | test_i8_one_low_prints_one_tenth_on_an_exact_half
T10 | templates/_risk_radar_pullback_depth.html.j2:153 | ``round(4)`` -> ``round(1)`` at the worst site | KILLED | test_i8_one_low_prints_one_tenth_on_an_exact_half
T11 | templates/_risk_radar_pullback_depth.html.j2:153 | ``round(4)`` -> ``round(3)`` at the worst site | EQUIVALENT | 2-decimal sweep proof (module docstring)
T12 | templates/_risk_radar_pullback_depth.html.j2:153 | ``round(4)`` -> ``round(5)`` at the worst site | EQUIVALENT | 2-decimal sweep proof (module docstring)
T13 | templates/_risk_radar_pullback_depth.html.j2:157 | drop ``|round(4)`` at the rebound site | SURVIVED | test_us_rebound_exact_half_prints_the_four_place_tenth
T14 | templates/_risk_radar_pullback_depth.html.j2:157 | ``round(4)`` -> ``round(1)`` at the rebound site | SURVIVED | test_us_rebound_exact_half_prints_the_four_place_tenth
T15 | templates/_risk_radar_pullback_depth.html.j2:157 | ``round(4)`` -> ``round(3)`` at the rebound site | SURVIVED | test_us_rebound_three_places_disagree_prints_the_four_place_tenth
T16 | templates/_risk_radar_pullback_depth.html.j2:157 | ``round(4)`` -> ``round(5)`` at the rebound site | SURVIVED | test_us_rebound_five_places_disagree_prints_the_four_place_tenth
T17 | templates/_risk_radar_pullback_depth.html.j2:148 | ``up_s != '0.0'`` -> ``!= '0'`` | KILLED | test_seeded_episode_fuzz_across_owner_presenter_and_fragment
T18 | templates/_risk_radar_pullback_depth.html.j2:149 | ``dd_s != '0.0'`` -> ``!= '0'`` | KILLED | test_seeded_episode_fuzz_across_owner_presenter_and_fragment
T19 | templates/_risk_radar_pullback_depth.html.j2:153 | ``worst_s != '0.0'`` -> ``!= '0'`` | KILLED | test_m_low_equal_to_the_peak_still_measures_the_drawdown
T20 | templates/_risk_radar_pullback_depth.html.j2:157 | ``rebound_s != '0.0'`` -> ``!= '0'`` | KILLED | test_seeded_episode_fuzz_across_owner_presenter_and_fragment
L01 | lib/pullback_depth.py:202 | ``round(end, 4)`` -> ``end`` | KILLED | test_i8_one_low_prints_one_tenth_on_an_exact_half
L02 | lib/pullback_depth.py:202 | ``round(end, 4)`` -> ``round(end, 1)`` | KILLED | test_i8_one_low_prints_one_tenth_on_an_exact_half
L03 | lib/pullback_depth.py:202 | ``round(end, 4)`` -> ``round(end, 3)`` | KILLED | test_p3_last_plotted_value_is_the_observation_drawdown_ratio
L04 | lib/pullback_depth.py:202 | ``round(end, 4)`` -> ``round(end, 5)`` | KILLED | test_p3_last_plotted_value_is_the_observation_drawdown_ratio

The two tests below re-pin the whole I8 invariant (one close, one tenth
across the current metric, the worst metric, the history rows and the drawn
end tag) on the exact-half series, for the US panel and for the China dialog
that renders the same shared fragment, so the rule cannot regress on either
surface without a test naming it.
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from tests.test_pullback_episode_fuzz import _MINUS, _feed, _zip, assert_i8
from tests.test_pullback_episode_fuzz_cn import _days, _drive, _render

# Seventy flat sessions at the retained high, then the episode tail: every
# close in this module is a two-decimal synthetic figure.
_BASE = [100.0] * 70


def _text(soup, selector):
    node = soup.select_one(selector)
    assert node is not None, selector
    return node.get_text(strip=True)


def test_us_half_drop_last_prints_one_tenth_on_current_worst_and_end_tag():
    """An exact 10.25% half (close 89.75 under a 100.0 high) with the low on
    the last close: the current metric, the worst metric, the low history row
    and the drawn end tag must all print the four-place tenth -10.2% - never
    the raw double's -10.3% - and the flat rebound stays an unsigned 0.0%."""
    rows = _zip(_BASE + [94.0, 91.5, 89.75])
    obs, _window, view, _qualified, html = _feed(rows)
    soup = BeautifulSoup(html, "html.parser")
    assert view.get("detail_path")
    assert_i8(soup, obs, view, k=0, kind="low last", rows=rows)
    assert _text(soup, '[data-metric="current"]') == f"{_MINUS}10.2%"
    assert _text(soup, '[data-metric="worst"]') == f"{_MINUS}10.2%"
    assert _text(soup, ".ilx-tag") == f"{_MINUS}10.2%"
    assert _text(soup, '[data-metric="rebound"]') == "0.0%"


def test_cn_dialog_prints_the_same_one_tenth_texts():
    """The China dialog renders the same shared fragment: the same exact-half
    series must print -10.2% on the current metric, the worst metric and the
    drawn end tag, with the flat rebound an unsigned 0.0%."""
    values = _BASE + [94.0, 91.5, 89.75]
    rows = [(day.isoformat(), float(v)) for day, v in zip(_days(len(values)), values)]
    obs, view = _drive(rows)
    soup = BeautifulSoup(_render("cn", view), "html.parser")
    section = soup.select_one("section.rrp")
    assert section is not None and section.get("data-pb-phase") == obs.get("phase")
    assert _text(soup, '[data-metric="current"]') == f"{_MINUS}10.2%"
    assert _text(soup, '[data-metric="worst"]') == f"{_MINUS}10.2%"
    assert _text(soup, ".ilx-tag") == f"{_MINUS}10.2%"
    assert _text(soup, '[data-metric="rebound"]') == "0.0%"


def test_us_rebound_exact_half_prints_the_four_place_tenth():
    """A rebound of exactly +1.15% (close 79.16 off the 78.26 low) is an
    exact half at four places: the raw ratio is a hair above the half, so
    dropping the round - or coarsening it to one place - prints +1.2% where
    the owner's four-place value prints +1.1%."""
    rows = _zip(_BASE + [92.0, 85.0, 78.26, 79.16])
    _obs, _window, _view, _qualified, html = _feed(rows)
    soup = BeautifulSoup(html, "html.parser")
    assert _text(soup, '[data-metric="rebound"]') == "+1.1%"
    assert _text(soup, '[data-metric="current"]') == f"{_MINUS}20.8%"
    assert _text(soup, '[data-metric="worst"]') == f"{_MINUS}21.7%"
    assert _text(soup, ".ilx-tag") == f"{_MINUS}20.8%"


def test_us_rebound_three_places_disagree_prints_the_four_place_tenth():
    """A rebound of 100*(83.12/78.01-1) = 6.550442...: the four-place value
    6.5504 sits above the 6.55 half and prints +6.6%, while the three-place
    value lands on double(6.55), which sits BELOW the half and prints +6.5%.
    Only the four-place round prints the owner's tenth."""
    rows = _zip(_BASE + [92.0, 85.0, 78.01, 83.12])
    _obs, _window, _view, _qualified, html = _feed(rows)
    soup = BeautifulSoup(html, "html.parser")
    assert _text(soup, '[data-metric="rebound"]') == "+6.6%"


def test_us_rebound_five_places_disagree_prints_the_four_place_tenth():
    """A rebound of 100*(85.85/78.01-1) = 10.049993...: the four-place value
    is 10.05, which sits above the 10.05 half in binary64 and prints +10.1%,
    while at five places the value is still 10.04999, below the half, and
    prints +10.0%. Only the four-place round prints the owner's tenth."""
    rows = _zip(_BASE + [92.0, 85.0, 78.01, 85.85])
    _obs, _window, _view, _qualified, html = _feed(rows)
    soup = BeautifulSoup(html, "html.parser")
    assert _text(soup, '[data-metric="rebound"]') == "+10.1%"


def test_us_close_above_high_half_prints_one_tenth():
    """A reclaim closing at 100.05 over the 100.0 high: the raw ratio
    0.04999999999999449 is a hair BELOW the 0.05 half, so formatting it raw -
    or rounded to one place - prints 0.0% with the plus suppressed, while the
    four-place value 0.05 prints +0.1% on the current metric and the drawn
    end tag."""
    rows = _zip(_BASE + [94.0, 89.75, 96.0, 100.05])
    obs, _window, _view, _qualified, html = _feed(rows)
    soup = BeautifulSoup(html, "html.parser")
    assert obs.get("phase") == "recovering"
    assert _text(soup, '[data-metric="current"]') == "+0.1%"
    assert _text(soup, ".ilx-tag") == "+0.1%"
    assert _text(soup, '[data-metric="worst"]') == f"{_MINUS}10.2%"
    assert _text(soup, '[data-metric="rebound"]') == "+11.5%"


def test_us_close_above_high_under_half_prints_unsigned_zero():
    """A reclaim closing at 100.04: the four-place value 0.04 formats to
    0.0% and the sign test must suppress the plus - comparing against '0'
    instead of '0.0' prints +0.0% on the current metric and the drawn end
    tag."""
    rows = _zip(_BASE + [94.0, 91.0, 96.0, 100.04])
    obs, _window, _view, _qualified, html = _feed(rows)
    soup = BeautifulSoup(html, "html.parser")
    assert obs.get("phase") == "recovering"
    current = _text(soup, '[data-metric="current"]')
    assert current == "0.0%"
    assert "+" not in current and _MINUS not in current
    assert _text(soup, ".ilx-tag") == "0.0%"
