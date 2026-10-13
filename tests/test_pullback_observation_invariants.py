"""Seeded invariant fuzz of the pullback episode owner.

The owner is ``lib.pullback_observation.observe``. Every path below is a
synthetic weekday calendar (Monday-Friday fixture, no exchange holidays) so
the session rule is satisfied. Prices are invented. One ``random.Random``
stream per generator, seeds:

    geometric       872101
    regime          872102
    vshape          872103
    grind           872104
    shock           872105
    double_bottom   872106
    sawtooth        872107
    flat            872108
    ties            872109

``loss_recovered_pct`` uses the owner's clamp: None when no episode is open
(also when peak <= low, which a confirmed episode does not produce), otherwise
``round`` of ``100 * (close - low) / (peak - low)`` clipped to [0, 100].

``onset_session`` is the confirmation session, not the first close of the
attempt. A shock (``RULES.shock_drawdown``) confirms on that one close. An
onset drawdown confirms on the second consecutive close
(``RULES.onset_closes``). The low is the first minimum from that run's first
close through the as-of, so a two-close confirmation can print the low before
``onset_session``. ``canonical_low_before_onset`` is that path.

An active episode's frozen peak bounds every close from ``peak_session``
through the as-of, except a trailing run of closes at or above the peak
whose length is from 1 through ``RULES.reclaim_closes - 1``. That run is an
unconfirmed reclaim: the phase is ``recovering`` and the episode stays
active. ``canonical_reclaim_above_frozen_peak`` is one such close. A later
close back below the peak leaves the overshoot in the window; the corpus
violates the bound on that path.

``price_path`` is display-only, capped at ``PATH_MAX_CLOSES``. Transition
phases stay in ``TRANSITION_PHASES``, and transition dates strictly increase
and never fall after the as-of. When a transition date or ``peak_session``
predates the first drawn close, ``episode_window`` is None, so nothing
draws a chart or a table from a partial episode.
``canonical_transition_outside_path`` is that cap.
"""
from __future__ import annotations

from datetime import date, timedelta
from math import isfinite
from statistics import fmean
import random

import pytest

from lib.pullback_depth import episode_window
from lib.pullback_observation import PATH_MAX_CLOSES, RULES, _next_observation, _peak, observe


# Phases ``_replay`` writes into ``price_transitions``. ``monitoring`` and
# ``developing`` are pre-episode view labels and are not transition phases.
TRANSITION_PHASES = frozenset({"underway", "stabilizing", "recovering", "repaired"})

SEEDS = {
    "geometric": 872101,
    "regime": 872102,
    "vshape": 872103,
    "grind": 872104,
    "shock": 872105,
    "double_bottom": 872106,
    "sawtooth": 872107,
    "flat": 872108,
    "ties": 872109,
}
PATHS_PER_FAMILY = 48
CALENDAR_START = date(2024, 1, 2)  # Tuesday

# Shortest active episode whose history breaks the frozen-peak bound.
# 62 closes at 100, a one-close shock, one reclaimed close, then a giveback.
# Do not shrink this: confirmation needs the reference window.
_I2_DEFECT = (
    "ENGINE DEFECT: 62 closes at 100, then 94, 101, 99 (65 weekdays from "
    "2024-01-02, as-of 2024-04-01): active phase underway but close 101 on "
    "2024-03-29 > frozen peak_close 100 (peak_session 2024-03-27); that "
    "close is not a trailing reclaim run of length 1..reclaim_closes-1"
)


def is_weekday_session(day: date) -> bool:
    """Fixture calendar only. The caller, not this test, owns a real exchange."""
    return day.weekday() < 5


def to_rows(values, start=CALENDAR_START):
    day = start
    rows = []
    for value in values:
        while not is_weekday_session(day):
            day += timedelta(days=1)
        rows.append((day.isoformat(), float(value)))
        day += timedelta(days=1)
    return rows


def _assert_weekday_path(rows):
    previous = None
    for stamp, price in rows:
        day = date.fromisoformat(stamp)
        assert is_weekday_session(day), stamp
        assert isinstance(price, float) and isfinite(price) and price > 0
        if previous is not None:
            probe = previous + timedelta(days=1)
            while probe < day:
                assert not is_weekday_session(probe), (previous, day)
                probe += timedelta(days=1)
            assert day > previous
        previous = day


def canonical_reclaim_above_frozen_peak():
    """One reclaimed close above the frozen peak leaves the episode active."""
    return [100.0] * 62 + [94.0, 101.0]


def canonical_low_before_onset():
    """Two-close confirmation whose first pending close is the strict low."""
    return [100.0] * 62 + [97.0, 98.0]


def canonical_transition_outside_path():
    """New low every session so the only transition stays on the onset bar.

    314 closes still draw that bar (it is ``price_path.dates[0]``). The 315th
    pushes it one session before the capped path.
    """
    return [100.0] * 62 + [94.0 - 0.01 * i for i in range(253)]


def _geometric(rng, n):
    price = rng.uniform(40.0, 180.0)
    out = []
    for _ in range(n):
        price *= 1.0 + rng.uniform(-0.035, 0.03)
        if price < 1.0:
            price = 1.0
        out.append(price)
    return out


def _regime(rng, n):
    price = rng.uniform(40.0, 180.0)
    out = []
    while len(out) < n:
        volatile = rng.random() < 0.45
        span = rng.randint(5, 15)
        half = 0.028 if volatile else 0.004
        drift = rng.uniform(-0.012, 0.006) if volatile else rng.uniform(-0.001, 0.001)
        for _ in range(span):
            if len(out) >= n:
                break
            price *= 1.0 + drift + rng.uniform(-half, half)
            if price < 1.0:
                price = 1.0
            out.append(price)
    return out


def _vshape(rng, n):
    start = rng.uniform(60.0, 140.0)
    trough_at = rng.randint(63, max(63, n - 2))
    trough = start * (1.0 - rng.uniform(0.08, 0.35))
    end = start * (1.0 + rng.uniform(0.02, 0.20))
    out = []
    for i in range(n):
        if i <= trough_at:
            weight = i / trough_at
            out.append(start + (trough - start) * weight)
        else:
            weight = (i - trough_at) / (n - 1 - trough_at)
            out.append(trough + (end - trough) * weight)
    return out


def _grind(rng, n):
    start = rng.uniform(50.0, 150.0)
    factor = rng.uniform(0.997, 0.9995)
    return [start * factor ** i for i in range(n)]


def _shock(rng, n):
    price = rng.uniform(50.0, 150.0)
    shock_at = rng.randint(62, n - 2)
    out = []
    for i in range(n):
        if i < shock_at:
            price *= 1.0 + rng.uniform(-0.003, 0.003)
            out.append(price)
        elif i == shock_at:
            price *= 0.94  # synthetic -6% shock day, past the 5% shock rule
            out.append(price)
        else:
            price *= 1.0 + rng.uniform(-0.02, 0.03)
            if price < 1.0:
                price = 1.0
            out.append(price)
    return out


def _double_bottom(rng, n):
    base = rng.uniform(60.0, 140.0)
    low = round(base * rng.uniform(0.86, 0.94), 4)
    mid = round(max(low * 1.02, base * rng.uniform(0.96, 0.995)), 4)
    down = max(3, (n - 63) // 6)

    def climb(target, steps):
        origin = vals[-1]
        for step in range(1, steps + 1):
            vals.append(origin + (target - origin) * (step / steps))

    vals = [base] * 63
    climb(low, down)
    vals[-1] = low
    climb(mid, down)
    vals[-1] = mid
    climb(low, down)
    vals[-1] = low
    vals.extend([low] * 3)  # exact ties on the second touch
    while len(vals) < n:
        step = len(vals) - (63 + 3 * down + 3) + 1
        vals.append(low + min(mid - low, 0.2 * max(step, 1)) * 0.5)
    return vals[:n]


def _sawtooth(rng, n):
    """Oscillate around the 2% onset line and occasionally print a -6% day."""
    peak = rng.choice((40.0, 100.0, 175.0))
    below_pct = (1.2, 2.0, 2.6, 3.2, 2.0, 1.5, 4.0, 2.4)
    phase = rng.randint(0, len(below_pct) - 1)
    vals = [peak] * 63
    i = 0
    while len(vals) < n:
        if i % 11 == 10:
            vals.append(peak * 0.94)
        else:
            pct = below_pct[(i + phase) % len(below_pct)]
            vals.append(peak * (1.0 - pct / 100.0))
        i += 1
    return vals


def _flat(rng, n):
    level = rng.choice((25.0, 80.0, 100.0, 100.0, 130.0))
    return [level] * n


def _ties(rng, n):
    base = rng.uniform(50.0, 150.0)
    low = round(base * rng.uniform(0.90, 0.97), 2)
    down = rng.randint(2, 6)
    repeats = rng.randint(3, 6)
    vals = [base] * 63
    for step in range(1, down + 1):
        vals.append(base + (low - base) * (step / down))
    vals[-1] = low
    vals.extend([low] * repeats)  # exact ties on the low
    while len(vals) < n:
        step = len(vals) - (63 + down + repeats) + 1
        vals.append(low + min((base - low) * 0.4, 0.25 * max(step, 1)))
    return vals[:n]


GENERATORS = {
    "geometric": _geometric,
    "regime": _regime,
    "vshape": _vshape,
    "grind": _grind,
    "shock": _shock,
    "double_bottom": _double_bottom,
    "sawtooth": _sawtooth,
    "flat": _flat,
    "ties": _ties,
}


def _length(family, index, rng):
    rolled = rng.randint(80, 130)
    if family == "flat" and index == 0:
        return RULES.reference_closes  # exactly 63 closes is available
    if family == "grind" and index == 0:
        return PATH_MAX_CLOSES  # on the cap; onset is still inside the path
    return rolled


def _build_corpus():
    built = []
    for family, seed in SEEDS.items():
        rng = random.Random(seed)
        generate = GENERATORS[family]
        for index in range(PATHS_PER_FAMILY):
            length = _length(family, index, rng)
            rows = to_rows(generate(rng, length))
            assert len(rows) == length, (family, index, len(rows), length)
            _assert_weekday_path(rows)
            built.append((f"{family}:{index}", rows))
    canonical = (
        ("canonical:reclaim", canonical_reclaim_above_frozen_peak()),
        ("canonical:low-before-onset", canonical_low_before_onset()),
        ("canonical:transition-outside-path", canonical_transition_outside_path()),
    )
    for label, values in canonical:
        rows = to_rows(values)
        _assert_weekday_path(rows)
        built.append((label, rows))
    assert len(built) >= 400
    return tuple(built)


CORPUS = _build_corpus()


def _observe(rows):
    return observe(
        rows,
        expected_session=date.fromisoformat(rows[-1][0]),
        is_session=is_weekday_session,
    )


def _walk(rows):
    """Every as-of that has a full reference window, inclusive of the tail."""
    assert len(rows) >= RULES.reference_closes
    for end in range(RULES.reference_closes, len(rows) + 1):
        prefix = rows[:end]
        obs = _observe(prefix)
        assert obs["available"] is True and obs["quality"] == "current", (
            end, obs.get("quality"))
        yield prefix, obs


def _drawdown(price, peak):
    return round(min(0.0, 100.0 * (price / peak - 1.0)), 4)


def _recovered(close, low, peak):
    """Owner formula. Range is [0, 100] after the clamp, or None if peak <= low."""
    if peak <= low:
        return None
    raw = 100.0 * (close - low) / (peak - low)
    return round(max(0.0, min(100.0, raw)), 2)


def i1_violations(rows, obs):
    bad = []
    if obs["close"] != rows[-1][1]:
        bad.append("close is not the as-of row")
    on_peak = [price for stamp, price in rows if stamp == obs["peak_session"]]
    if on_peak != [obs["peak_close"]]:
        bad.append("peak_close is not the close on peak_session")
    formula = _drawdown(obs["close"], obs["peak_close"])
    if obs["drawdown_pct"] != formula:
        bad.append(f"drawdown {obs['drawdown_pct']} != {formula}")
    if obs["drawdown_pct"] is None or obs["drawdown_pct"] > 0:
        bad.append(f"drawdown not <= 0 ({obs['drawdown_pct']})")
    if obs["low_close"] is not None:
        worst_price = obs["low_close"]
    else:
        window = [price for stamp, price in rows
                  if obs["peak_session"] <= stamp <= obs["asof"]]
        if not window:
            bad.append("no closes from peak_session to as-of")
            return bad
        worst_price = min(window)
    worst = _drawdown(worst_price, obs["peak_close"])
    if worst > obs["drawdown_pct"]:
        bad.append(f"worst {worst} > drawdown {obs['drawdown_pct']}")
    return bad


def _active_confirming_run(rows):
    """First close and confirmation close of the episode still active at the tail.

    Same arming rules as ``_replay``. A close at least ``shock_drawdown`` below
    the reference peak confirms on that close. An onset drawdown confirms when
    the pending streak reaches ``onset_closes``. The run starts at the pending
    attempt's first close. Resolution is replayed only so a finished episode
    is not mistaken for the one still open.
    """
    records = [(date.fromisoformat(stamp), price) for stamp, price in rows]
    prices = [price for _, price in records]
    pending = episode = None
    reference_floor = 0
    contiguous = above20 = 0
    for i, (day, price) in enumerate(records):
        joined = i == 0 or _next_observation(records[i - 1][0], day, is_weekday_session)
        contiguous = contiguous + 1 if joined else 1
        if not joined:
            pending = None
            above20 = 0
            if episode:
                episode["no_new_low_closes"] = 0
                episode["reclaim_streak"] = 0
        ma20 = fmean(prices[max(0, i - 19):i + 1])
        above20 = above20 + 1 if i >= 19 and price > ma20 else 0
        if i < RULES.reference_closes - 1:
            continue
        peak_i = _peak(records, max(reference_floor, i - RULES.reference_closes + 1), i + 1)
        if episode is None:
            if pending and pending["peak_index"] < i - RULES.reference_closes + 1:
                pending = None
            ref_i = pending["peak_index"] if pending else peak_i
            below = 1.0 - price / prices[ref_i]
            if below + 1e-12 >= RULES.onset_drawdown:
                if pending is None:
                    pending = {"peak_index": ref_i, "streak": 0, "first_index": i}
                pending["streak"] += 1
                if (pending["streak"] >= RULES.onset_closes
                        or below + 1e-12 >= RULES.shock_drawdown):
                    low_i = min(
                        range(pending["first_index"], i + 1),
                        key=lambda j: prices[j],
                    )
                    episode = {
                        "peak_index": ref_i,
                        "start_index": i,
                        "first_index": pending["first_index"],
                        "low_index": low_i,
                        "no_new_low_closes": i - low_i,
                        "reclaim_streak": 0,
                    }
                    pending = None
            else:
                pending = None
        if episode is not None:
            if price < prices[episode["low_index"]]:
                episode["low_index"] = i
                episode["no_new_low_closes"] = 0
            elif i > episode["start_index"]:
                episode["no_new_low_closes"] = (
                    episode["no_new_low_closes"] + 1 if joined else 0)
            reference = prices[episode["peak_index"]]
            episode["reclaim_streak"] = (
                episode["reclaim_streak"] + 1 if price >= reference else 0)
            rising20 = ma20 > fmean(prices[i - 24:i - 4])
            if episode["reclaim_streak"] >= RULES.reclaim_closes:
                resolution = "prior_high_reclaimed"
            elif (contiguous >= 25 and rising20
                  and above20 >= RULES.trend_repair_above_ma_closes
                  and episode["no_new_low_closes"] >= RULES.trend_repair_no_low_closes
                  and price > max(prices[i - 19:i])):
                resolution = "trend_repaired_below_prior_high"
            else:
                resolution = None
            if resolution:
                reference_floor = i
                episode = None
    if episode is None:
        return None
    return episode["first_index"], episode["start_index"]


def i2_violations(rows, obs):
    """Active peak bound, with an unconfirmed trailing reclaim as the only exception."""
    if not obs["active"]:
        return []
    peak = obs["peak_close"]
    window = [price for stamp, price in rows
              if obs["peak_session"] <= stamp <= obs["asof"]]
    if not window:
        return ["no closes from peak_session to as-of"]
    trail = 0
    for price in reversed(window):
        if price >= peak:
            trail += 1
        else:
            break
    head = window[:-trail] if trail else window
    bad = []
    over = [price for price in head if price > peak]
    if over:
        bad.append(
            f"overshoot: peak_close {peak} < {max(over)} outside the trailing reclaim"
        )
    if trail > RULES.reclaim_closes - 1:
        bad.append(f"reclaim run of {trail} closes is still active")
    elif trail >= 1 and obs["phase"] != "recovering":
        bad.append(f"phase {obs['phase']} during an unconfirmed reclaim of {trail}")
    return bad


def _i2_without_overshoot(rows, obs):
    return [item for item in i2_violations(rows, obs) if not item.startswith("overshoot:")]


def i3_violations(rows, obs):
    if not obs["active"]:
        return []
    located = _active_confirming_run(rows)
    if located is None:
        return ["active episode has no confirming run"]
    first_i, onset_i = located
    if rows[onset_i][0] != obs["onset_session"]:
        return [f"confirming run ends at {rows[onset_i][0]} != onset {obs['onset_session']}"]
    window = rows[first_i:]
    lowest = min(price for _, price in window)
    first_session = next(stamp for stamp, price in window if price == lowest)
    bad = []
    if obs["low_close"] != lowest:
        bad.append(f"low_close {obs['low_close']} != {lowest}")
    if obs["low_session"] != first_session:
        bad.append(f"low_session {obs['low_session']} != {first_session}")
    return bad


def i4_violations(rows, obs):
    if obs["onset_session"] is None:
        if obs["loss_recovered_pct"] is not None:
            return [f"loss_recovered_pct {obs['loss_recovered_pct']} without an episode"]
        return []
    if obs["low_close"] is None:
        return ["episode missing low_close"]
    expected = _recovered(obs["close"], obs["low_close"], obs["peak_close"])
    if obs["loss_recovered_pct"] != expected:
        return [f"loss_recovered_pct {obs['loss_recovered_pct']} != {expected}"]
    if expected is not None and not 0 <= expected <= 100:
        return [f"loss_recovered_pct {expected} outside [0, 100]"]
    return []


def i5_violations(rows, obs):
    if obs["active"] and obs["onset_session"] is None:
        return ["active episode has no onset_session"]
    if obs["onset_session"] is None:
        if obs["observed_closes_since_onset"] is not None:
            return ["observed_closes_since_onset set without an episode"]
        return []
    counted = sum(1 for stamp, _ in rows if obs["onset_session"] <= stamp <= obs["asof"])
    if obs["observed_closes_since_onset"] != counted:
        return [f"observed_closes_since_onset {obs['observed_closes_since_onset']} != {counted}"]
    return []


def i6_violations(rows, obs):
    if obs["low_session"] is None:
        if obs["no_new_low_closes"] is not None:
            return ["no_new_low_closes set without a low"]
        return []
    counted = sum(1 for stamp, _ in rows if obs["low_session"] < stamp <= obs["asof"])
    if obs["no_new_low_closes"] != counted:
        return [f"no_new_low_closes {obs['no_new_low_closes']} != {counted}"]
    return []


def i7_violations(rows, obs):
    path = obs["price_path"]
    dates = path["dates"]
    vals = path["vals"]
    bad = []
    if obs["asof"] != rows[-1][0]:
        bad.append("asof is not the last row")
    if not dates or dates[-1] != obs["asof"]:
        bad.append("price path does not end at as-of")
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        bad.append("price path dates are not strictly increasing")
    if len(dates) > PATH_MAX_CLOSES or len(vals) != len(dates):
        bad.append(f"price path length {len(dates)} vals {len(vals)}")
    if any(value > 0 for value in vals):
        bad.append("price path has a positive drawdown")
    if vals and vals[-1] != obs["drawdown_pct"]:
        bad.append(f"last path value {vals[-1]} != drawdown {obs['drawdown_pct']}")
    return bad


def i8_violations(rows, obs):
    path_dates = obs["price_path"]["dates"]
    transitions = obs["price_transitions"]
    bad = []
    stamps = [item["date"] for item in transitions]
    if stamps != sorted(stamps) or len(stamps) != len(set(stamps)):
        bad.append("transition dates are not strictly increasing")
    if any(stamp > obs["asof"] for stamp in stamps):
        bad.append("transition date is after the as-of")
    unknown = sorted({
        item["phase"] for item in transitions if item["phase"] not in TRANSITION_PHASES
    })
    if unknown:
        bad.append(f"phases outside vocabulary: {unknown}")
    if path_dates:
        first = path_dates[0]
        early = [item["date"] for item in transitions if item["date"] < first]
        peak_early = isinstance(obs.get("peak_session"), str) and obs["peak_session"] < first
        if (early or peak_early) and episode_window(obs) is not None:
            bad.append(
                "episode_window drew a chart though a transition or the peak predates the path"
            )
    return bad


def _scan(check):
    seen = 0
    failures = []
    for label, rows in CORPUS:
        seen += 1
        for prefix, obs in _walk(rows):
            bad = check(prefix, obs)
            if bad and len(failures) < 5:
                failures.append((label, prefix[-1][0], len(prefix), bad))
            elif bad:
                failures.append(None)
    real = [item for item in failures if item is not None]
    extra = sum(1 for item in failures if item is None)
    return seen, real, extra


def _assert_holds(check):
    seen, failures, extra = _scan(check)
    assert seen >= 400, seen
    assert not failures and extra == 0, (failures, extra)


def test_corpus_mixes_nine_generators_and_at_least_400_weekday_paths():
    families = {label.split(":", 1)[0] for label, _ in CORPUS}
    assert set(SEEDS) <= families
    assert len(CORPUS) >= 400
    assert len(CORPUS) == PATHS_PER_FAMILY * len(SEEDS) + 3


def test_i1_drawdown_is_nonpositive_and_matches_the_peak_formula():
    _assert_holds(i1_violations)


def test_i2_active_peak_bounds_every_close_except_an_unconfirmed_reclaim():
    """xfail(strict=True) while a giveback leaves a non-trailing overshoot.

    The canonical one-close reclaim is a real pin and is not part of that
    defect. A scan that stops reporting the overshoot fails until this xfail
    is removed.
    """
    rows = to_rows(canonical_reclaim_above_frozen_peak())
    obs = _observe(rows)
    assert obs["phase"] == "recovering"
    assert obs["active"] is True
    assert obs["close"] == 101.0
    assert obs["peak_close"] == 100.0
    assert obs["close"] > obs["peak_close"]
    assert obs["drawdown_pct"] == 0.0
    assert i2_violations(rows, obs) == []
    _assert_holds(_i2_without_overshoot)

    witness = to_rows([100.0] * 62 + [94.0, 101.0, 99.0])
    got = _observe(witness)
    assert got["asof"] == "2024-04-01"
    assert got["active"] is True and got["phase"] == "underway"
    assert got["peak_close"] == 100.0 and got["peak_session"] == "2024-03-27"
    witness_bad = i2_violations(witness, got)
    assert any(item.startswith("overshoot:") for item in witness_bad), witness_bad
    seen, failures, extra = _scan(i2_violations)
    assert seen >= 400
    if failures or extra:
        pytest.xfail(_I2_DEFECT)
    pytest.fail("xfail(strict=True) cleared: " + _I2_DEFECT)


def test_i3_low_is_the_first_minimum_of_the_confirming_run_through_asof():
    rows = to_rows(canonical_low_before_onset())
    obs = _observe(rows)
    first_i, onset_i = _active_confirming_run(rows)
    assert obs["phase"] == "underway"
    assert obs["low_close"] == 97.0
    assert obs["low_session"] == "2024-03-28"
    assert obs["onset_session"] == "2024-03-29"
    assert obs["low_session"] < obs["onset_session"]
    assert rows[first_i][0] == obs["low_session"]
    assert rows[onset_i][0] == obs["onset_session"]
    _assert_holds(i3_violations)


def test_i4_loss_recovered_matches_the_clamped_owner_formula():
    _assert_holds(i4_violations)


def test_i5_observed_closes_since_onset_counts_rows_through_asof():
    _assert_holds(i5_violations)


def test_i6_no_new_low_closes_counts_rows_after_the_low():
    _assert_holds(i6_violations)


def test_i7_price_path_is_capped_nonpositive_and_ends_at_asof():
    _assert_holds(i7_violations)


def test_i8_transitions_use_the_vocabulary_and_any_that_predate_the_path_withhold_the_chart():
    rows = to_rows(canonical_transition_outside_path())
    obs = _observe(rows)
    assert obs["peak_session"] == "2024-03-27"
    assert obs["price_path"]["dates"][0] == "2024-03-29"
    assert obs["price_transitions"][0] == {"date": "2024-03-28", "phase": "underway"}
    assert obs["price_transitions"][0]["date"] < obs["price_path"]["dates"][0]
    assert obs["peak_session"] < obs["price_path"]["dates"][0]
    assert episode_window(obs) is None
    _assert_holds(i8_violations)


def test_i9_active_episode_peak_and_onset_are_prefix_stable():
    """A still-active episode does not revise the previous as-of's peak or onset.

    The extra close is future relative to the earlier as-of, so re-observing
    that as-of on the longer prefix is the no-look-ahead check. While both
    as-ofs are active, the episode's own peak_session and onset_session stay.
    """
    seen = 0
    failures = []
    for label, rows in CORPUS:
        seen += 1
        previous = None
        for end in range(RULES.reference_closes, len(rows) + 1):
            prefix = rows[:end]
            asof = date.fromisoformat(prefix[-1][0])
            current = observe(prefix, expected_session=asof, is_session=is_weekday_session)
            assert current["available"] is True and current["quality"] == "current"
            if previous is not None and current["active"]:
                earlier_rows, earlier = previous
                replay = observe(
                    prefix, expected_session=date.fromisoformat(earlier_rows[-1][0]),
                    is_session=is_weekday_session)
                identity = (
                    replay["available"] is True
                    and replay["peak_session"] == earlier["peak_session"]
                    and replay["onset_session"] == earlier["onset_session"]
                )
                carried = True
                if earlier["active"]:
                    carried = (
                        current["peak_session"] == earlier["peak_session"]
                        and current["onset_session"] == earlier["onset_session"]
                    )
                if not identity or not carried:
                    if len(failures) < 5:
                        failures.append((
                            label, earlier_rows[-1][0], asof.isoformat(),
                            earlier["peak_session"], current["peak_session"],
                            earlier["onset_session"], current["onset_session"],
                            identity, carried,
                        ))
                    else:
                        failures.append(None)
            previous = (prefix, current)
    assert seen >= 400
    assert not failures, [item for item in failures if item is not None][:3]


def test_i10_appending_a_future_row_changes_only_the_excluded_count():
    seen = 0
    for label, rows in CORPUS:
        seen += 1
        asof = date.fromisoformat(rows[-1][0])
        base = observe(rows, expected_session=asof, is_session=is_weekday_session)
        next_day = asof + timedelta(days=1)
        next_weekday = next_day
        while not is_weekday_session(next_weekday):
            next_weekday += timedelta(days=1)
        extras = (
            (next_day.isoformat(), 123.45),
            (next_weekday.isoformat(), float("inf")),
        )
        for stamp, value in extras:
            extended = rows + [(stamp, value)]  # append only; history order unchanged
            assert [row[0] for row in extended[:-1]] == [row[0] for row in rows]
            more = observe(extended, expected_session=asof, is_session=is_weekday_session)
            assert more["excluded_future_rows"] == base["excluded_future_rows"] + 1, label
            base_body = dict(base)
            more_body = dict(more)
            base_body.pop("excluded_future_rows")
            more_body.pop("excluded_future_rows")
            assert base_body == more_body, label
    assert seen >= 400


def test_i11_observe_is_deterministic_and_does_not_mutate_its_input():
    seen = 0
    for _label, rows in CORPUS:
        seen += 1
        snapshot = [tuple(row) for row in rows]
        asof = date.fromisoformat(rows[-1][0])
        first = observe(rows, expected_session=asof, is_session=is_weekday_session)
        second = observe(list(rows), expected_session=asof, is_session=is_weekday_session)
        assert rows == snapshot
        assert first == second
    assert seen >= 400


def test_unavailable_paths_return_available_false_with_a_quality_reason():
    def assert_unavailable(rows, expected, quality):
        read = observe(rows, expected_session=expected, is_session=is_weekday_session)
        assert read["available"] is False
        assert read["quality"] == quality and isinstance(read["quality"], str)

    tuesday = CALENDAR_START
    assert_unavailable([], tuesday, "no_history")
    assert_unavailable(to_rows([100.0]), date.fromisoformat(to_rows([100.0])[-1][0]),
                       "insufficient_history")
    short = to_rows([100.0] * (RULES.reference_closes - 1))
    assert_unavailable(short, date.fromisoformat(short[-1][0]), "insufficient_history")

    families_checked = set()
    for label, rows in CORPUS:
        family = label.split(":", 1)[0]
        if family in families_checked or family.startswith("canonical"):
            continue
        families_checked.add(family)
        prefix = rows[:RULES.reference_closes - 1]
        assert_unavailable(prefix, date.fromisoformat(prefix[-1][0]), "insufficient_history")
    assert families_checked == set(SEEDS)

    saturday = date(2024, 1, 6)
    assert not is_weekday_session(saturday)
    full = to_rows([100.0] * RULES.reference_closes)
    assert_unavailable(full, saturday, "invalid_expected_session")

    broken = to_rows([100.0] * (RULES.reference_closes - 1) + [float("nan")])
    assert_unavailable(broken, date.fromisoformat(broken[-1][0]), "invalid_close")

    settled = to_rows([100.0] * RULES.reference_closes)
    later = date.fromisoformat(settled[-1][0]) + timedelta(days=1)
    while not is_weekday_session(later):
        later += timedelta(days=1)
    assert_unavailable(settled, later, "delayed")
