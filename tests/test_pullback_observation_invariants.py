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
"""
from __future__ import annotations

from datetime import date, timedelta
from math import isfinite
import random

import pytest

from lib.pullback_observation import PATH_MAX_CLOSES, RULES, observe


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

# Shortest inputs that violate one stated invariant. Dates are the weekday
# calendar anchored at CALENDAR_START; do not shrink these further.
_I2_REASON = (
    "62 closes at 100, then 94, then 101 (64 weekdays from 2024-01-02, "
    "as-of 2024-03-29): active episode peak_basis frozen_at_onset but "
    "peak_close 100 < close 101 (peak_session 2024-03-27, onset 2024-03-28)"
)
_I3_REASON = (
    "62 closes at 100, then 97, then 98 (64 weekdays from 2024-01-02): "
    "low_close 97 on 2024-03-28 is before onset_session 2024-03-29, and the "
    "min close from onset to as-of is 98"
)
_I8_REASON = (
    "62 closes at 100, then 94-0.01*i for i in 0..252 (315 weekdays from "
    "2024-01-02): price_transitions[0] date 2024-03-28 phase underway is "
    "before price_path.dates[0] 2024-03-29 (314 closes still includes it)"
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


def i2_violations(rows, obs):
    if not obs["active"]:
        return []
    bad = []
    if obs["peak_basis"] != "frozen_at_onset":
        bad.append(f"peak_basis {obs['peak_basis']}")
    breached = [price for stamp, price in rows
                if obs["peak_session"] <= stamp <= obs["asof"] and price > obs["peak_close"]]
    if breached:
        bad.append(f"peak_close {obs['peak_close']} < {max(breached)}")
    return bad


def i3_violations(rows, obs):
    if obs["onset_session"] is None:
        return []
    window = [(stamp, price) for stamp, price in rows
              if obs["onset_session"] <= stamp <= obs["asof"]]
    if not window:
        return ["onset window empty"]
    lowest = min(price for _, price in window)
    first = next(stamp for stamp, price in window if price == lowest)
    bad = []
    if obs["low_close"] != lowest:
        bad.append(f"low_close {obs['low_close']} != {lowest}")
    if obs["low_session"] != first:
        bad.append(f"low_session {obs['low_session']} != {first}")
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
    if len(transitions) > 6:
        bad.append(f"{len(transitions)} transitions")
    stamps = [item["date"] for item in transitions]
    if stamps != sorted(stamps) or len(stamps) != len(set(stamps)):
        bad.append("transition dates are not strictly increasing")
    if path_dates:
        first, last = path_dates[0], path_dates[-1]
        outside = [item["date"] for item in transitions if not first <= item["date"] <= last]
        if outside:
            bad.append(f"transitions outside the path: {outside}")
    unknown = sorted({item["phase"] for item in transitions if item["phase"] not in TRANSITION_PHASES})
    if unknown:
        bad.append(f"phases outside vocabulary: {unknown}")
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


@pytest.mark.xfail(strict=True, reason=_I2_REASON)
def test_i2_active_peak_is_at_least_every_close_through_asof():
    _assert_holds(i2_violations)


@pytest.mark.xfail(strict=True, reason=_I3_REASON)
def test_i3_low_is_the_first_minimum_from_onset_through_asof():
    _assert_holds(i3_violations)


def test_i4_loss_recovered_matches_the_clamped_owner_formula():
    _assert_holds(i4_violations)


def test_i5_observed_closes_since_onset_counts_rows_through_asof():
    _assert_holds(i5_violations)


def test_i6_no_new_low_closes_counts_rows_after_the_low():
    _assert_holds(i6_violations)


def test_i7_price_path_is_capped_nonpositive_and_ends_at_asof():
    _assert_holds(i7_violations)


@pytest.mark.xfail(strict=True, reason=_I8_REASON)
def test_i8_transitions_stay_inside_the_path_and_the_phase_vocabulary():
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
