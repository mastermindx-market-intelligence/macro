"""Presenter property tests: the pullback popup's chart window and level gate.

Every close path below is synthetic (stdlib random, fixed seeds) and is observed
through the real ``lib.pullback_observation.observe()`` before the real
``lib.pullback_depth.present()`` read model is checked, so each property holds —
or is recorded as a counterexample — against shipped behaviour, not against a
mock. This file owns the PRESENTER and ``level_break`` only; observer
invariants live in tests/test_pullback_observation_invariants.py.

Three properties were originally recorded as ``xfail(strict=True)``
counterexamples; adjudication kept the product behaviour and moved the
wording, so each is now pinned positively against shipped code:

* P2 — ``uncovered`` is exactly the presenter's own coverage rule: it fires
  iff the retained peak has aged out of the capped drawn path, or the drawn
  window would contradict the measured episode low (``episode_window``'s
  coherence gate, unit-pinned by tests/test_pullback_depth_mutants.py).
* P4 — every drawn chart carries the shared renderer's standard SVG stretch
  attribute ``preserveAspectRatio="none"`` (lib/illus.py); the scan strips
  exactly that attribute and requires no leaked token to remain.
* P7 — the presenter draws pre-episode (monitoring/developing) windows from
  the reference high, and the rendered popup labels them by their own phase
  ("Pullback monitor" / "回撤观察"), never with an active-phase verdict.
"""
from __future__ import annotations

import json
import random
import re
from copy import deepcopy
from datetime import date, timedelta

import pytest

from lib.pullback_depth import (
    MIN_CHART_POINTS,
    OBSERVATION_SCHEMA,
    PATH_TOLERANCE_PP,
    level_break,
    present,
)
from lib.pullback_observation import PATH_MAX_CLOSES, observe

# Fixture-only market identity: present() compares this to the observation's
# own stamp, so any stable label qualifies; nothing here names a real market.
MARKET = "synthetic"
ARIA_EN = "Observed drawdown"
ARIA_ZH = "已观察回撤"

# The presenter defines exactly two withheld reasons (lib/pullback_depth.py,
# present(): "short" = a coherent window younger than MIN_CHART_POINTS closes,
# "uncovered" = no window that agrees with the measured figures).
WITHHELD_REASONS = frozenset({"short", "uncovered"})

# The shared illustration renderer emits this standard SVG attribute on every
# drawn chart (lib/illus.py); it is structural stretch markup, never a value.
SANCTIONED_NONE_ATTR = 'preserveAspectRatio="none"'
LEAKED_TOKENS = ("nan", "inf", "none", "undefined")

SWEEP_SEED = 872101
SWEEP_PATHS = 300
LEVEL_BREAK_SEED = 20261011
LEVEL_BREAK_PATHS = 300


# --------------------------------------------------------------------------- #
# synthetic close paths (weekday calendar is a fixture, as repo-wide)
# --------------------------------------------------------------------------- #
def session(day):
    return day.weekday() < 5


def rows_for(values, baseline=64):
    values = [100.0] * baseline + list(values)
    day = date(2025, 1, 2)
    rows = []
    for value in values:
        while not session(day):
            day += timedelta(days=1)
        rows.append((day.isoformat(), value))
        day += timedelta(days=1)
    return rows


def _walk(rng, count, start=100.0, vol=0.015):
    prices, price = [], start
    for _ in range(count):
        price *= 1.0 + rng.uniform(-vol, vol)
        prices.append(price)
    return prices


def _next_day(day):
    return day + timedelta(days=1)


def _next_session(day):
    day = _next_day(day)
    while not session(day):
        day = _next_day(day)
    return day


def _next_non_session(day):
    day = _next_day(day)
    while session(day):
        day = _next_day(day)
    return day


def _qualified(obs):
    return (
        obs.get("available") is True
        and obs.get("quality") == "current"
        and obs.get("clock") == "settled_close"
        and obs.get("market") == MARKET
        and obs.get("schema") == OBSERVATION_SCHEMA
    )


def _observe_case(rows, expected=None):
    """observe() one path, present() the read model, and record the facts the
    properties are stated against (closes since the peak, counted from the
    fixture's own rows — never from the code under test)."""
    expected = expected or date.fromisoformat(rows[-1][0])
    obs = observe(rows, expected_session=expected, is_session=session)
    obs = dict(obs, market=MARKET, clock="settled_close")
    view = present(obs, market=MARKET, aria_en=ARIA_EN, aria_zh=ARIA_ZH)
    peak = obs.get("peak_session")
    path_dates = (obs.get("price_path") or {}).get("dates") or []
    return {
        "rows": rows,
        "obs": obs,
        "view": view,
        "pristine": deepcopy(obs),
        "qualified": _qualified(obs),
        "peak_retained": bool(peak) and peak in path_dates,
        "n_since_peak": None if not peak else sum(1 for day, _ in rows if day >= peak),
    }


def _vetoed_case(sound, key, value):
    """One qualification veto at a time: the popup must go unavailable."""
    broken = dict(sound["obs"])
    broken[key] = value
    view = present(broken, market=MARKET, aria_en=ARIA_EN, aria_zh=ARIA_ZH)
    return {
        "rows": sound["rows"],
        "obs": broken,
        "view": view,
        "pristine": deepcopy(broken),
        "qualified": False,
        "peak_retained": False,
        "n_since_peak": None,
    }


def _episode_tail(rng):
    """Confirmed episodes that then stabilize, recover, or repair."""
    shape = rng.choice(("stabilizing", "recovering", "repaired"))
    if shape == "stabilizing":
        return [95.0, 90.0] + [90.0 + 0.5 * j + rng.uniform(-0.05, 0.05)
                               for j in range(3, 6)]
    if shape == "recovering":
        return ([95.0, 80.0]
                + [81.0 + 0.25 * j + rng.uniform(-0.05, 0.05) for j in range(1, 25)])
    return [95.0, 90.0, 100.0, 100.0 + rng.uniform(0.05, 0.4)]


def _unavailable_case(rng):
    roll = rng.random()
    if roll < 0.34:  # too few closes for a reference window
        return _observe_case(rows_for(
            [100.0 * (1 + rng.uniform(-0.01, 0.01)) for _ in range(rng.randint(5, 62))],
            baseline=0))
    rows = rows_for(_walk(rng, 80), baseline=0)
    if roll < 0.67:  # the expected session is not a session
        return _observe_case(rows, expected=_next_non_session(
            date.fromisoformat(rows[-1][0])))
    return _observe_case(rows, expected=_next_session(  # the close is stale
        date.fromisoformat(rows[-1][0])))


def _sweep_cases():
    """>= 300 seeded paths spanning every presenter branch, plus deterministic
    members that pin each phase and each recorded counterexample."""
    cases, rng = [], random.Random(SWEEP_SEED)
    for i in range(SWEEP_PATHS):
        kind = i % 10
        if kind in (0, 1, 2, 3):  # open-ended walk: monitoring/developing/episodes
            cases.append(_observe_case(rows_for(_walk(rng, rng.randint(200, 330)),
                                                baseline=0)))
        elif kind in (4, 5):  # spike, then an unfixed decline: possibly cap-aged
            n = rng.randint(200, PATH_MAX_CLOSES + 40)
            cases.append(_observe_case(
                rows_for([101.0] + [96.0 - 0.004 * j for j in range(n)])))
        elif kind == 6:  # failed deeper dip, then a shallower confirmation
            depth1 = rng.uniform(0.025, 0.045)
            depth2 = rng.uniform(0.021, depth1 - 0.003)
            cases.append(_observe_case(rows_for([
                101.0,
                101.0 * (1 - depth1),
                101.0 * (1 - rng.uniform(0.002, 0.015)),
                101.0 * (1 - depth2),
                101.0 * (1 - depth2),
            ])))
        elif kind == 7:  # a fresh high on the last closes: a valid but young window
            tail = [100.0 + 0.3 * j for j in range(rng.randint(1, 3))]
            cases.append(_observe_case(rows_for(tail, baseline=64 + rng.randint(0, 20))))
        elif kind == 8:  # an episode that then stabilizes, recovers, or repairs
            cases.append(_observe_case(rows_for(_episode_tail(rng))))
        else:  # young or mistimed history: the unavailable reads
            cases.append(_unavailable_case(rng))
    cases.extend(_deterministic_cases())
    return cases


def _deterministic_cases():
    cases = [
        _observe_case(rows_for([100.0] * 62 + [99.5])),   # monitoring (young window)
        _observe_case(rows_for([100.0] * 62 + [98.0])),   # developing (young window)
        _observe_case(rows_for([100.0] * 62 + [94.5])),   # single 5% shock: underway
        _observe_case(rows_for([95.0, 90.0, 91.0, 92.0, 93.0])),  # stabilizing
        _observe_case(rows_for([95.0, 80.0] + [81.0 + 0.25 * j for j in range(24)])),
        _observe_case(rows_for([95.0, 90.0, 100.0, 100.2])),  # repaired by reclaim
        # The recorded P2 counterexample: a deeper dip that failed confirmation,
        # then a shallower confirmed episode, inside the reference window.
        _observe_case(rows_for([101.0, 97.0, 99.5, 98.5, 98.2])),
        # The recorded P7 counterexample: an inactive monitoring read that the
        # presenter still charts (4 coherent closes from the reference high).
        _observe_case(rows_for([100.0] * 62 + [99.0, 98.0, 99.5])),
        # An episode older than the display cap: uncovered by age.
        _observe_case(rows_for(
            [101.0] + [96.0 - 0.01 * j for j in range(PATH_MAX_CLOSES + 20)])),
    ]
    sound = cases[2]
    for key, value in (("market", "other"), ("schema", "other.v1"),
                       ("available", False), ("quality", "delayed"),
                       ("clock", "intraday"), ("phase", "shock")):
        cases.append(_vetoed_case(sound, key, value))
    return cases


@pytest.fixture(scope="module")
def sweep():
    return _sweep_cases()


# --------------------------------------------------------------------------- #
# fixture sanity: no property below may pass against a vacuous sweep
# --------------------------------------------------------------------------- #
def test_sweep_exercises_every_presenter_branch(sweep):
    seen = {"drawn": 0, "short": 0, "uncovered": 0, "unavailable": 0}
    phases, charted_actives = set(), set()
    young_qualified = aged_qualified = 0
    for case in sweep:
        view = case["view"]
        if view["phase"] == "unavailable":
            seen["unavailable"] += 1
        elif view["detail_withheld"] is None:
            seen["drawn"] += 1
        else:
            seen[view["detail_withheld"]] += 1
        phases.add(view["phase"])
        if view["detail_path"] is not None:
            charted_actives.add(case["obs"].get("active"))
        if case["qualified"] and case["peak_retained"] \
                and case["n_since_peak"] < MIN_CHART_POINTS:
            young_qualified += 1
        if case["qualified"] and case["n_since_peak"] and \
                case["n_since_peak"] > PATH_MAX_CLOSES:
            aged_qualified += 1
    assert seen["drawn"] >= 10 and seen["short"] >= 5 and seen["uncovered"] >= 5
    assert seen["unavailable"] >= 5
    assert phases == {"monitoring", "developing", "underway", "stabilizing",
                      "recovering", "repaired", "unavailable"}
    assert charted_actives == {True, False}
    assert young_qualified >= 1 and aged_qualified >= 1


# --------------------------------------------------------------------------- #
# P1 — a drawn window contains the peak, the low, and the as-of session
# --------------------------------------------------------------------------- #
def test_p1_drawn_window_spans_peak_low_and_asof_session(sweep):
    for case in sweep:
        obs, view = case["obs"], case["view"]
        if view["detail_withheld"]:
            continue  # withheld charts are P2's subject
        if view["detail_path"] is None:
            # the only falsy-withheld shape without a window is an unavailable read
            assert view["phase"] == "unavailable"
            assert view["detail_chart_html"] in ("", None)
            continue
        path = view["detail_path"]
        dates, vals = path["dates"], path["vals"]
        assert obs["peak_session"] in dates
        if obs.get("low_session"):
            assert obs["low_session"] in dates
        assert dates[-1] == obs["asof"]
        assert all(later > earlier for earlier, later in zip(dates, dates[1:]))
        assert len(dates) == len(vals)
        assert MIN_CHART_POINTS <= len(dates) <= PATH_MAX_CLOSES
        assert view["detail_chart_html"]  # a drawn window always renders the figure


# --------------------------------------------------------------------------- #
# P2 — withheld charts name a presenter reason and stay empty
# --------------------------------------------------------------------------- #
def test_p2_withheld_chart_names_a_reason_and_draws_nothing(sweep):
    for case in sweep:
        view = case["view"]
        reason = view["detail_withheld"]
        if not reason:
            continue
        assert reason in WITHHELD_REASONS
        assert view["detail_chart_html"] in ("", None)
        assert view["detail_path"] is None
        retained, n = case["peak_retained"], case["n_since_peak"]
        if reason == "short":  # short exactly when too few closes exist
            assert retained and n < MIN_CHART_POINTS
        if case["qualified"]:
            if retained and n < MIN_CHART_POINTS:
                assert reason == "short"
            if n > PATH_MAX_CLOSES:  # an aged peak is always uncovered
                assert reason == "uncovered"


def _window_contradicts_measured_low(case):
    """Case (b) of the coverage rule, restated from the case's own facts.

    ``episode_window`` slices the owner's capped path at the retained peak and
    refuses the window when any drawn close sits below the measured episode
    low by more than the presenter's rounding tolerance — a deeper dip that
    failed confirmation must not be drawn under figures that exclude it.
    Reads the observation's own rounded ``price_path`` values, the same list
    the presenter slices, so the comparison has no re-derivation drift.
    """
    obs = case["obs"]
    low, low_session = obs.get("low_close"), obs.get("low_session")
    if not case["peak_retained"] or low is None or low_session is None:
        return False  # no drawn window, or no measured episode low to contradict
    dates = obs["price_path"]["dates"]
    drawn = obs["price_path"]["vals"][dates.index(obs["peak_session"]):]
    low_pct = 100.0 * (low / obs["peak_close"] - 1.0)
    return min(drawn) < low_pct - PATH_TOLERANCE_PP


def test_p2_uncovered_iff_the_peak_ages_out_or_the_window_hides_a_deeper_low(sweep):
    """The exact coverage rule, both directions, over every qualified case.

    ``uncovered`` fires iff (a) the retained peak is older than the drawn
    path's close cap, or (b) the drawn window would contradict the measured
    episode low. ``short`` remains the young-window verdict; a contradicted
    window is refused outright, never drawn short.
    """
    aged = contradicted = uncovered = 0
    for case in sweep:
        if not case["qualified"]:
            continue  # an unqualified read goes unavailable, never uncovered
        view = case["view"]
        by_age = case["n_since_peak"] > PATH_MAX_CLOSES  # (a): peak older than the cap
        by_contradiction = _window_contradicts_measured_low(case)  # (b): refused gate
        aged += by_age
        contradicted += by_contradiction
        assert (view["detail_withheld"] == "uncovered") is (by_age or by_contradiction)
        if by_age or by_contradiction:
            uncovered += 1
            assert view["detail_chart_html"] in ("", None)
            assert view["detail_path"] is None
    assert aged >= 1 and contradicted >= 1 and uncovered >= 1


def test_p2_the_recorded_counterexample_is_uncovered_by_a_contradicted_window():
    """The original counterexample, now stated as the rule it demonstrates.

    closes 101.0, 97.0, 99.5, 98.5, 98.2 after a flat 64-close run observe to
    an 'underway' episode whose retained peak is only 5 closes old. The deeper
    97.0 dip failed confirmation, so the measured episode low is 98.2 (-2.77%)
    while the owner's price path still draws the 97.0 close (-3.96%): the
    coherence gate refuses the window, so the chart is withheld as
    'uncovered' — figure contradiction, not cap age.
    """
    case = _observe_case(rows_for([101.0, 97.0, 99.5, 98.5, 98.2]))
    obs, view = case["obs"], case["view"]
    assert obs["phase"] == "underway" and case["peak_retained"]
    assert case["n_since_peak"] <= PATH_MAX_CLOSES  # NOT uncovered by age
    assert _window_contradicts_measured_low(case)
    assert view["detail_withheld"] == "uncovered"
    assert view["detail_chart_html"] in ("", None)
    assert view["detail_path"] is None


# --------------------------------------------------------------------------- #
# P3 — the plotted end value is the observation's own drawdown ratio
# --------------------------------------------------------------------------- #
def test_p3_last_plotted_value_is_the_observation_drawdown_ratio(sweep):
    for case in sweep:
        view = case["view"]
        if view["detail_path"] is None:
            continue
        obs = case["obs"]
        ratio = 100.0 * (obs["close"] / obs["peak_close"] - 1.0)
        last = view["detail_path"]["vals"][-1]
        # The chart end is the unclipped close/peak ratio at the owner's four
        # places. drawdown_pct stays clipped at 0 when the close has reclaimed
        # the frozen high.
        assert last == round(ratio, 4)
        if obs["close"] <= obs["peak_close"]:
            assert abs(last - obs["drawdown_pct"]) <= 5.0001e-5
        else:
            assert obs["drawdown_pct"] == 0.0
            assert last > 0


# --------------------------------------------------------------------------- #
# P4 — rendered HTML and the plotted path leak no computed garbage
# --------------------------------------------------------------------------- #
def _assert_no_leak(text):
    lowered = text.replace(SANCTIONED_NONE_ATTR, "").lower()
    for token in LEAKED_TOKENS:
        assert token not in lowered, token


def test_p4_rendered_html_and_path_leak_no_computed_garbage(sweep):
    for case in sweep:
        view = case["view"]
        chart = view["detail_chart_html"]
        _assert_no_leak("\n".join((
            view["phase"], chart or "",
            json.dumps(view["detail_path"], allow_nan=False),
        )))
        if chart:
            # The sanctioned SVG stretch attribute is the ONLY "none" allowed.
            assert chart.lower().count("none") == chart.count(SANCTIONED_NONE_ATTR)
            assert re.search(r'class="ilx-path[^"]*" d="([^"]+)"', chart)


def test_p4_the_sanctioned_svg_stretch_attribute_is_the_only_leak_match(sweep):
    """The whole-string scan, with the renderer's own markup allowed exactly.

    lib/illus.py stamps the standard SVG stretch attribute
    ``preserveAspectRatio="none"`` on every drawn figure, so the honest scan
    strips exactly that attribute — case-sensitively, in full — and then
    requires no leaked token to remain. Every chart must carry the attribute,
    so the allowance can never silently turn the scan into a no-op.
    """
    checked = 0
    for case in sweep:
        chart = case["view"]["detail_chart_html"]
        if not chart:
            continue
        checked += 1
        assert chart.count(SANCTIONED_NONE_ATTR) >= 1  # the strip is not vacuous
        _assert_no_leak(chart)
    assert checked >= 10


# --------------------------------------------------------------------------- #
# P5 — present() is deterministic and does not mutate its input
# --------------------------------------------------------------------------- #
def test_p5_present_is_deterministic_and_does_not_mutate_its_input(sweep):
    for case in sweep:
        obs, pristine = case["obs"], case["pristine"]
        first = present(obs, market=MARKET, aria_en=ARIA_EN, aria_zh=ARIA_ZH)
        second = present(obs, market=MARKET, aria_en=ARIA_EN, aria_zh=ARIA_ZH)
        assert first == second
        assert obs == pristine


# --------------------------------------------------------------------------- #
# P6 — level_break: scale invariance and the single-jump gate
# --------------------------------------------------------------------------- #
def test_p6_level_break_is_scale_invariant_and_gates_single_jumps():
    rng = random.Random(LEVEL_BREAK_SEED)
    scale_checked = 0
    for _ in range(LEVEL_BREAK_PATHS):
        rows = rows_for(_walk(rng, rng.randint(12, 40), start=50.0, vol=0.01),
                        baseline=0)
        base = level_break(rows)
        assert base is False  # +/-1% steps never leave [0.75, 1/0.75]
        for k in (0.01, 7.0, 1e4):
            assert level_break([(day, value * k) for day, value in rows]) == base
            scale_checked += 1
        # One injected jump per path: 2:1 and 1:2 are breaks, 0.80/1.20 are not.
        for factor, should_break in ((2.0, True), (0.5, True), (0.8, False),
                                     (1.2, False)):
            jumped = list(rows)
            j = rng.randrange(1, len(jumped))
            jumped[j] = (jumped[j][0], jumped[j - 1][1] * factor)
            assert level_break(jumped) is should_break
            for k in (0.01, 7.0, 1e4):
                assert level_break(
                    [(day, value * k) for day, value in jumped]) is should_break
    assert scale_checked >= LEVEL_BREAK_PATHS


# --------------------------------------------------------------------------- #
# P7 — the unavailable read never draws
# --------------------------------------------------------------------------- #
def test_p7_unavailable_observations_never_produce_a_chart_or_a_path(sweep):
    for case in sweep:
        view = case["view"]
        if view["phase"] != "unavailable":
            continue
        assert view["detail_chart_html"] in ("", None)
        assert not view["detail_path"]  # None, never a plotted window
        assert view["detail_withheld"] is None


def test_p7_pre_episode_windows_draw_from_the_reference_high_and_stay_monitoring():
    """Pre-episode reads are drawn and labelled by their own phase.

    The presenter never reads the observation's ``active`` field: a
    monitoring/developing window (no measured low yet) still draws from the
    reference high — pinned by tests/test_us_pullback_observation_adapter.py::
    test_pre_episode_observation_still_draws_from_the_reference_high. Rendering
    the real fragment for that inactive observation must show the monitoring
    verdict ("Pullback monitor" / "回撤观察"), never an active-phase one
    ("Pullback underway" / "回撤进行中").
    """
    case = _observe_case(rows_for([100.0] * 62 + [99.0, 98.0, 99.5]))
    obs, view = case["obs"], case["view"]
    assert obs["phase"] == "monitoring" and obs["active"] is False
    assert view["phase"] == "monitoring"
    assert len(view["detail_path"]["dates"]) == 4  # peak + the three tail closes
    assert view["detail_withheld"] is None

    # Render the real fragment. The fragment qualifies on the two adapter-only
    # fields the core observer does not mint (market label, valid_until); stamp
    # them on a copy the way lib.us_pullback_observation.snapshot does.
    from tests.test_risk_radar_pullback_depth_template import render
    stamped = dict(obs, market="us", valid_until="2026-10-13T21:00:00+00:00")
    html = render(present(stamped, market="us", aria_en=ARIA_EN, aria_zh=ARIA_ZH), "us")
    assert 'data-pb-phase="monitoring"' in html
    assert "Pullback monitor" in html and "回撤观察" in html
    assert "Pullback underway" not in html and "回撤进行中" not in html
    assert '<div class="rrp-chart"' in html  # the pre-episode window is drawn


def test_p3_a_close_above_the_high_tags_the_chart_end_with_a_plus():
    """The chart's end tag and the history table print one signed number.

    A recovering close above the frozen high is a positive ratio. Printed
    unsigned inside a drawdown chart it would read as a 1% drawdown.
    """
    case = _observe_case(rows_for([100.0] * 62 + [94.0, 97.0, 101.0]))
    obs, view = case["obs"], case["view"]
    assert obs["close"] > obs["peak_close"]
    assert view["detail_path"]["vals"][-1] == pytest.approx(1.0, abs=1e-9)
    tags = re.findall(r'<span class="ilx-tag">([^<]*)<', view["detail_chart_html"])
    assert tags == ["+1.0%"]


@pytest.mark.parametrize("tail, tag", [
    ([94.0, 96.0, 95.0], "\u22125.0%"),
    ([94.0, 97.0, 100.0], "0.0%"),
])
def test_p3_an_end_at_or_below_the_high_keeps_its_unsigned_or_minus_tag(tail, tag):
    case = _observe_case(rows_for([100.0] * 62 + tail))
    view = case["view"]
    if view["detail_path"] is None:
        pytest.skip("presenter withheld this path")
    tags = re.findall(r'<span class="ilx-tag">([^<]*)<', view["detail_chart_html"])
    assert tags == [tag]
