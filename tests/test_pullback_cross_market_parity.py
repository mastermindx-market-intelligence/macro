"""Cross-market pullback parity: one close series, one set of reader numbers.

The US risk-radar popup and the China risk dialog both read the same episode
owner (``lib.pullback_observation.observe``) and render the same shared
fragment (``templates/_risk_radar_pullback_depth.html.j2``); only the
adapters, calendars, and benchmark identity differ. So the same close-VALUE
sequence must surface the same numbers to a reader in both markets: the same
read model (every date-valued and identity field removed) and the same visible
numeric text in the rendered panel (dates and the per-market clock stamp
removed). Dates legitimately differ — each market sits on its own session
calendar — so they are projected out, never compared.

Each series is placed on the US calendar with the US fuzz suite's ``_days``
and on the China calendar with the China suite's ``_days``, both ending on the
same Friday both calendars are open. Each market is driven through its own
adapter (``snapshot`` then ``present``) and rendered through the same Jinja
fragment the fuzz suites use.

All fixtures are synthetic levels and are not index quotes.
"""
from __future__ import annotations

import random
import re

from bs4 import BeautifulSoup

from tests import test_pullback_episode_fuzz as us_fuzz
from tests import test_pullback_episode_fuzz_cn as cn_fuzz

# Identity and provenance: names, clocks, and digests the two markets are
# SUPPOSED to disagree on. Everything else must match once dates are removed.
_IDENTITY = frozenset({
    "market", "benchmark", "benchmark_en", "benchmark_zh",
    "source", "price_basis", "produced_at", "valid_until",
    "source_digest", "chart_label_en", "chart_label_zh", "detail_chart_html",
})
_ISO_DATE = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")
# The panel's stamp and history table print dates and a settle clock; the
# per-market clock text ("17:00 UTC-04:00" vs "15:00 UTC+08:00") differs by
# design, so date/time stamps come out before numbers are read.
_STAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?(?:\s*UTC(?:[+-]\d{2}:\d{2})?)?")
_NUMBER = re.compile("[−+-]?\\d+(?:\\.\\d+)?%?")

_LEAD_PHASES = ("underway", "stabilizing", "recovering")


def _projection(value):
    """The read model a reader sees, with dates and identity removed."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key in _IDENTITY:
                continue
            if isinstance(item, str) and _ISO_DATE.match(item):
                continue
            if (isinstance(item, list) and item
                    and all(isinstance(v, str) and _ISO_DATE.match(v) for v in item)):
                continue
            out[key] = _projection(item)
        return out
    if isinstance(value, list):
        return [_projection(item) for item in value]
    return value


def _panel_numbers(html):
    """Visible numeric text of the pullback panel, dates and stamps removed.

    The chart SVG carries paths only and never <text>, so ``get_text`` reads
    the panel's visible copy. The stamp is dropped whole (the US benchmark
    name itself carries digits), then any residual date/time stamp.
    """
    soup = BeautifulSoup(html, "html.parser")
    panel = soup.select_one("section.rrp")
    stamp = panel.select_one(".rrp-stamp")
    if stamp is not None:
        stamp.decompose()
    text = _STAMP.sub(" ", panel.get_text(" ", strip=True))
    return _NUMBER.findall(text)


def _first_difference(us, cn, path="view"):
    """A readable name for the first key that differs, "" when none does."""
    if isinstance(us, dict) and isinstance(cn, dict):
        for key in sorted(set(us) | set(cn)):
            if key not in us or key not in cn:
                return f"{path}.{key}: present on only one market"
            found = _first_difference(us[key], cn[key], f"{path}.{key}")
            if found:
                return found
        return ""
    if isinstance(us, list) and isinstance(cn, list):
        if len(us) != len(cn):
            return f"{path}: list length {len(us)} != {len(cn)}"
        for index, (one, two) in enumerate(zip(us, cn)):
            found = _first_difference(one, two, f"{path}[{index}]")
            if found:
                return found
        return ""
    if us != cn:
        return f"{path}: {us!r} != {cn!r}"
    return ""


def _drive_both(values):
    """The same close values through each market's own adapter and render."""
    us_rows = us_fuzz._zip(values)
    cn_rows = [(day.isoformat(), float(price))
               for day, price in zip(cn_fuzz._days(len(values)), values)]
    us_obs, _window, us_view, _qualified, us_html = us_fuzz._feed(us_rows)
    cn_obs, cn_view = cn_fuzz._drive(cn_rows)
    cn_html = cn_fuzz._DETAIL_TPL.render(mkt="cn", v=cn_view)
    return us_obs, us_view, us_html, cn_obs, cn_view, cn_html


def _assert_parity(name, values, expect_numbers=True):
    """Both markets must agree on every projected field and visible number."""
    us_obs, us_view, us_html, cn_obs, cn_view, cn_html = _drive_both(values)

    problems = []
    us_projected, cn_projected = _projection(us_view), _projection(cn_view)
    if us_projected != cn_projected:
        problems.append(
            "read model differs: "
            + (_first_difference(us_projected, cn_projected) or "views differ"))
    us_numbers, cn_numbers = _panel_numbers(us_html), _panel_numbers(cn_html)
    if us_numbers != cn_numbers:
        index = next((i for i, (a, b) in enumerate(zip(us_numbers, cn_numbers))
                      if a != b), min(len(us_numbers), len(cn_numbers)))
        problems.append(
            f"panel numbers differ at [{index}]: us={us_numbers!r} cn={cn_numbers!r}")
    if expect_numbers and not us_numbers:
        problems.append("panel rendered no numbers; parity would be vacuous")
    if problems:
        raise AssertionError(
            f"[{name}] cross-market pullback parity failed\n"
            f"sequence ({len(values)} closes): {values!r}\n"
            + "\n".join(problems)
        )
    return us_obs.get("phase"), us_numbers


# --- named families -------------------------------------------------------

# Calm tape: never admits an episode, but the panel still renders.
def test_flat_tape_shows_the_same_monitoring_numbers():
    _assert_parity("flat_monitor", [100.0] * 70 + [99.5, 98.8, 99.2])


# A shallow dip below the owner's onset threshold never admits.
def test_shallow_dip_that_never_admits_shows_the_same_numbers():
    _assert_parity("never_admits", [100.0] * 70 + [99.3, 98.7, 99.1, 98.9])


# (a) a 6% slide admits an episode.
def test_six_percent_slide_shows_the_same_episode_numbers():
    phase, numbers = _assert_parity(
        "slide_6", [100.0] * 70 + [97.0, 95.5, 94.0])
    assert phase in _LEAD_PHASES, f"expected a live episode, saw {phase!r}"


# (b) a 12% slide.
def test_twelve_percent_slide_shows_the_same_episode_numbers():
    phase, numbers = _assert_parity(
        "slide_12", [100.0] * 70 + [94.0, 90.0, 88.0])
    assert phase in _LEAD_PHASES, f"expected a live episode, saw {phase!r}"


# (c) slide then a partial rebound: stabilizing.
def test_slide_with_partial_rebound_shows_the_same_stabilizing_numbers():
    phase, numbers = _assert_parity(
        "stabilizing", [100.0] * 70 + [94.0, 90.0, 91.5, 92.0, 92.5])
    assert phase == "stabilizing", f"expected stabilizing, saw {phase!r}"


# (d) slide, rebound, then a new low after the rebound.
def test_rebound_into_a_new_low_shows_the_same_numbers():
    phase, numbers = _assert_parity(
        "rebound_new_low",
        [100.0] * 70 + [94.0, 91.0, 92.0, 92.5, 90.0, 89.0])
    assert phase in _LEAD_PHASES, f"expected a live episode, saw {phase!r}"


# (e) an exact-half ratio: low 89.75 under a 100 high.
def test_exact_half_low_shows_the_same_numbers():
    phase, numbers = _assert_parity(
        "exact_half", [100.0] * 70 + [94.0, 89.75, 91.33])
    assert "−8.7%" in numbers, f"exact-half drawdown missing: {numbers!r}"


# Reclaim above the reference high repairs the episode.
def test_repair_above_the_high_shows_the_same_numbers():
    _assert_parity("repaired", [100.0] * 70 + [94.0, 90.0, 100.0, 100.4])


def test_recovering_above_the_high_shows_the_same_numbers():
    phase, numbers = _assert_parity(
        "recovering_above", [100.0] * 70 + [94.0, 89.0, 100.4])
    assert phase == "recovering", f"expected recovering, saw {phase!r}"


def test_young_new_high_shows_the_same_monitoring_numbers():
    _assert_parity("young_high", [100.0] * 70 + [100.5])


# Too little history: the unavailable copy, with no numbers at all.
def test_short_history_shows_the_same_unavailable_copy():
    phase, numbers = _assert_parity(
        "short_history", [100.0] * 30, expect_numbers=False)
    assert phase == "unavailable", f"expected unavailable, saw {phase!r}"


# (g) longer than PATH_MAX_CLOSES: the uncovered path is withheld.
def test_series_past_the_path_cap_shows_the_same_numbers():
    values = [120.0]
    price = 110.0
    values.append(price)
    for _ in range(260):
        price = round(price * 0.998, 4)
        values.append(price)
    phase, numbers = _assert_parity("past_path_cap", values)
    assert phase in _LEAD_PHASES, f"expected a live episode, saw {phase!r}"


# --- seeded random --------------------------------------------------------

def _walk(seed, count=90, start=100.0):
    """A deterministic cents-rounded random walk; every close stays positive."""
    rng = random.Random(seed)
    values = [start]
    price = start
    for _ in range(count - 1):
        price = round(price * (1.0 + rng.uniform(-0.03, 0.015)), 4)
        values.append(price)
    assert all(price > 0 for price in values)
    return values


def test_seeded_random_walks_show_the_same_numbers_in_both_markets():
    """Four fixed-seed walks. At least one must reach a live episode so the
    parity claim cannot quietly degrade into comparing two empty panels."""
    episodes = 0
    for seed in (7, 29, 101, 2026):
        phase, _numbers = _assert_parity(f"random_seed_{seed}", _walk(seed))
        if phase in _LEAD_PHASES:
            episodes += 1
    assert episodes >= 1, "no seeded walk reached a live episode"
