"""Golden phase trails for twelve synthetic pullback shapes.

Weekday sessions are an injected fixture, as in tests/test_pullback_observation.py.
Every close is hand-built around an index level of 100. Replaying
``observe(rows[:k])`` for k from 63 through the end freezes the phase trail.
The popup must keep the remaining decline as "Estimate unavailable".
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

from lib.pullback_depth import PHASES, present
from lib.pullback_observation import RULES, observe


# Titles from templates/_risk_radar_pullback_depth.html.j2 (the h2 pair).
TITLES = {
    "monitoring": "Pullback monitor",
    "developing": "Pullback developing",
    "underway": "Pullback underway",
    "stabilizing": "Stabilization watch",
    "recovering": "Watching price repair",
    "repaired": "Pullback repaired",
}

_DETAIL = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parents[1] / "templates"),
    autoescape=False,
).from_string(
    '{% import "_risk_radar_pullback_depth.html.j2" as p %}'
    "{{ p.detail(market, v) }}"
)


def session(day):
    return day.weekday() < 5


def weekday_closes(values):
    """Map a price list onto weekdays starting Thursday 2025-01-02."""
    day = date(2025, 1, 2)
    rows = []
    for value in values:
        while not session(day):
            day += timedelta(days=1)
        rows.append((day.isoformat(), float(value)))
        day += timedelta(days=1)
    return rows


def run_length(reads):
    trail = []
    for read in reads:
        phase = read["phase"]
        if trail and trail[-1][0] == phase:
            trail[-1] = (phase, trail[-1][1] + 1)
        else:
            trail.append((phase, 1))
    return trail


def replay(rows):
    """Causal prefixes. k = 63 is the first close `reference_closes` can classify."""
    reads = []
    for k in range(63, len(rows) + 1):
        prefix = rows[:k]
        read = observe(
            prefix,
            expected_session=date.fromisoformat(prefix[-1][0]),
            is_session=session,
        )
        assert read["available"] is True and read["quality"] == "current", read["quality"]
        assert read["phase"] in PHASES
        for banned in ("probability", "forecast", "quantile", "odds", "q25", "q75"):
            assert banned not in read
        reads.append(read)
    return reads


def assert_sections(reads):
    """present() plus the fragment: the title matches the phase, and the
    downside block never grows a number."""
    assert set(TITLES) == set(PHASES)
    for read in reads:
        # observe() does not stamp market, clock, or valid_until. The fragment's
        # assess() withholds the phase title without those adapter fields.
        stamped = dict(
            read,
            market="us",
            clock="settled_close",
            valid_until="2026-12-31T21:00:00+00:00",
        )
        view = present(
            stamped, market="us", aria_en="Observed drawdown", aria_zh="已观察回撤",
        )
        assert view["phase"] == read["phase"]
        html = _DETAIL.render(market="us", v=view)
        soup = BeautifulSoup(html, "html.parser")
        heading = soup.select_one("h2").get_text(" ", strip=True)
        assert TITLES[read["phase"]] in heading, (read["asof"], read["phase"], heading)
        assert f'data-pb-phase="{read["phase"]}"' in html
        forecast = soup.select_one(".rrp-forecast")
        text = forecast.get_text(" ", strip=True)
        assert forecast.get("data-forecast-status") == "unavailable"
        assert "Estimate unavailable" in text
        assert not any(ch.isdigit() for ch in text)
        assert [node.get_text(strip=True) for node in forecast.select(".rrp-forecast-row strong")] == [
            "—", "—",
        ]


def expect(rows, trail):
    reads = replay(rows)
    got = run_length(reads)
    assert got == trail, got
    assert sum(n for _, n in trail) == len(reads)
    assert_sections(reads)
    return reads


def test_frozen_trails_use_the_published_rule_constants():
    assert RULES.version == "close_path.v1"
    assert RULES.reference_closes == 63
    assert RULES.onset_drawdown == 0.02
    assert RULES.onset_closes == 2
    assert RULES.shock_drawdown == 0.05
    assert RULES.stabilization_closes == 3
    assert RULES.recovery_above_ma_closes == 5
    assert RULES.recovery_no_low_closes == 10
    assert RULES.trend_repair_above_ma_closes == 20
    assert RULES.trend_repair_no_low_closes == 21
    assert RULES.reclaim_closes == 2


def test_steady_uptrend_never_leaves_monitoring():
    # Each close is a new high inside reference_closes, so the drawdown is 0.
    # It never reaches onset_drawdown, and shock_drawdown does not apply.
    # There is no transition: the trail stays monitoring.
    rows = weekday_closes([100.0 + i * 0.0625 for i in range(132)])
    reads = expect(rows, [("monitoring", 70)])
    assert all(
        read["phase"] == "monitoring" and read["drawdown_pct"] == 0 and read["active"] is False
        for read in reads
    )


def test_slow_four_percent_dip_never_confirms():
    # The path drifts toward the high, then pokes under it on isolated closes.
    # A poke of at least onset_drawdown but under shock_drawdown opens one
    # developing close. The next close is back inside onset_drawdown, so the
    # pending streak is cleared before it can reach onset_closes. The deepest
    # poke is -4%, still short of shock_drawdown, so nothing is confirmed.
    rows = weekday_closes([100.0] * 63 + [
        99.5, 99.0, 98.5,
        97.5,
        99.0, 98.5, 99.0,
        97.0,
        99.0, 98.5,
        96.0,
        98.5, 99.0, 99.5, 100.0,
    ])
    reads = expect(rows, [
        ("monitoring", 4),
        ("developing", 1),
        ("monitoring", 3),
        ("developing", 1),
        ("monitoring", 2),
        ("developing", 1),
        ("monitoring", 4),
    ])
    assert min(read["drawdown_pct"] for read in reads) == -4.0
    assert all(read["active"] is False for read in reads)
    assert not any(
        read["phase"] in {"underway", "stabilizing", "recovering", "repaired"}
        for read in reads
    )


def test_shock_then_v_recovery():
    # Flat, then one close at -6%. That single print meets shock_drawdown, so
    # the episode opens underway with no developing close.
    # The next two closes are not new lows, but no_new_low_closes is 1 then 2,
    # still below stabilization_closes, so they stay underway.
    # The following close is the third without a new low and is above its
    # 5-close average, so stabilization_closes fires and the phase is stabilizing.
    # The next close is back at the high: reclaim_streak is 1, which is below
    # reclaim_closes, so the phase is forced to recovering and there is no resolution.
    # The second close at the high reaches reclaim_closes: prior_high_reclaimed,
    # phase repaired.
    rows = weekday_closes([100.0] * 63 + [94.0, 96.0, 97.5, 99.0, 100.0, 100.0])
    reads = expect(rows, [
        ("monitoring", 1),
        ("underway", 3),
        ("stabilizing", 1),
        ("recovering", 1),
        ("repaired", 1),
    ])
    assert any(read["drawdown_pct"] == -6.0 and read["phase"] == "underway" for read in reads)
    assert reads[-2]["phase"] == "recovering" and reads[-2]["resolution"] is None
    assert reads[-1]["resolution"] == "prior_high_reclaimed"
    assert reads[-1]["active"] is False


def test_grind_down_fifteen_percent_over_sixty_closes():
    # Sixty closes step down by 0.25, from 99.75 to 85 (-15%).
    # The opening flat close and the first seven grind closes are less than
    # onset_drawdown under the high: monitoring.
    # 98.0 is exactly onset_drawdown for one close: developing. It is not yet
    # shock_drawdown.
    # The next close is still at least onset_drawdown down, so the pending
    # streak reaches onset_closes and the episode confirms underway.
    # Every later close is a new low, so no_new_low_closes stays 0, below
    # stabilization_closes. The phase cannot leave underway. The -5% level is
    # crossed only after confirmation, inside the same episode.
    grind = [100.0 - 0.25 * (i + 1) for i in range(60)]
    rows = weekday_closes([100.0] * 63 + grind)
    reads = expect(rows, [
        ("monitoring", 8),
        ("developing", 1),
        ("underway", 52),
    ])
    assert reads[-1]["close"] == 85.0
    assert reads[-1]["drawdown_pct"] == -15.0
    assert all(read["no_new_low_closes"] in (None, 0) for read in reads)


def test_double_bottom_retest_holds():
    # 99 is inside onset_drawdown (monitoring, with the flat close before it).
    # 97.5 reaches onset_drawdown once: developing, short of shock_drawdown and
    # short of onset_closes.
    # 95.5 is the second such close: onset_closes confirms, underway.
    # The decline to 90 keeps making new lows, so no_new_low_closes stays below
    # stabilization_closes (still underway). The bounce then posts three closes
    # without a new low above the 5-close average: stabilization_closes fires.
    # The retest (down to 90.5, which is still above the 90 low) is not strictly
    # above its 5-close average, so the stabilizing conjunction fails and the
    # phase returns to underway. no_new_low_closes keeps climbing because the
    # low is not undercut, and stabilization_closes remains satisfied.
    # The turn back up clears the 5-close average again: stabilizing returns.
    # recovery_above_ma_closes does not fire; the close is still under the
    # 20-close average. reclaim_closes never starts.
    rows = weekday_closes([100.0] * 63 + [
        99.0, 97.5, 95.5, 93.0, 91.0, 90.0,
        91.5, 93.0, 94.5, 96.0, 96.5,
        95.0, 93.0, 91.5, 90.5,
        91.5, 93.0, 94.5, 95.5,
    ])
    reads = expect(rows, [
        ("monitoring", 2),
        ("developing", 1),
        ("underway", 6),
        ("stabilizing", 3),
        ("underway", 5),
        ("stabilizing", 3),
    ])
    assert min(price for _, price in rows) == 90.0
    assert 90.5 in {price for _, price in rows}
    assert reads[-1]["low_close"] == 90.0
    assert reads[-1]["active"] is True


def test_double_bottom_breaks_lower():
    # Same opening as the hold: onset_drawdown, then onset_closes, then
    # stabilization_closes on the bounce. The walk back toward the low leaves
    # stabilizing for the same reason (the close is not above its 5-close
    # average) while the low is still 90 and no_new_low_closes is still at
    # least stabilization_closes.
    # 89 then undercuts that low. no_new_low_closes resets to 0, below
    # stabilization_closes, and the two closes after it are new lows too.
    # The phase stays underway. reclaim_closes never starts.
    rows = weekday_closes([100.0] * 63 + [
        99.0, 97.5, 95.5, 93.0, 91.0, 90.0,
        91.5, 93.0, 94.5, 96.0, 96.5,
        95.0, 93.0, 91.5, 89.0,
        88.5, 88.0,
    ])
    reads = expect(rows, [
        ("monitoring", 2),
        ("developing", 1),
        ("underway", 6),
        ("stabilizing", 3),
        ("underway", 6),
    ])
    assert any(read["low_close"] == 90.0 for read in reads)
    assert reads[-1]["low_close"] == 88.0
    assert reads[-1]["no_new_low_closes"] == 0
    assert all(read["resolution"] is None for read in reads)


def test_failed_rally_reclaims_once_then_makes_a_new_low():
    # 98.5 is inside onset_drawdown (monitoring). 97 reaches it once
    # (developing): below shock_drawdown, and the streak is still under
    # onset_closes. 96 is the second close: onset_closes confirms, underway,
    # and that close is the low. The next 97 is only the first close without
    # a new low, below stabilization_closes, so it stays underway.
    # 100 is one reclaimed close. reclaim_streak is nonzero but still below
    # reclaim_closes, so the phase is forced to recovering and resolution
    # stays empty. One reclaimed close is not a repair.
    # 95 undercuts the episode low, so no_new_low_closes resets below
    # stabilization_closes, and the close is back under the high so the
    # reclaim streak drops below reclaim_closes. The phase returns to underway.
    rows = weekday_closes([100.0] * 63 + [98.5, 97.0, 96.0, 97.0, 100.0, 95.0])
    reads = expect(rows, [
        ("monitoring", 2),
        ("developing", 1),
        ("underway", 2),
        ("recovering", 1),
        ("underway", 1),
    ])
    reclaimed = next(read for read in reads if read["phase"] == "recovering")
    assert reclaimed["resolution"] is None and reclaimed["close"] >= reclaimed["peak_close"]
    assert reads[-1]["low_close"] < reclaimed["low_close"]
    assert all(read["phase"] != "repaired" for read in reads)


def test_sideways_chop_between_three_and_five_percent():
    # 98.5 stays inside onset_drawdown. 97 reaches it for one close (developing).
    # 95.5 is the second close: onset_closes confirms. It is -4.5%, short of
    # shock_drawdown. 95 is a new low inside the episode, so the phase stays
    # underway; shock_drawdown does not open a second episode.
    # Once three closes have passed without a lower low, up closes (97 and
    # 96.5) are above the 5-close average and stabilization_closes fires.
    # Down closes (95.5 and 95) are not above that average, so the conjunction
    # fails and the phase returns to underway. They do not undercut 95, so
    # no_new_low_closes is not reset.
    # The same pair repeats. Dips sit on the 20-close average often enough
    # that above20 never reaches recovery_above_ma_closes or
    # trend_repair_above_ma_closes. reclaim_closes never starts.
    rows = weekday_closes([100.0] * 63 + [
        98.5, 97.0, 95.5, 95.0,
        96.5, 95.0, 97.0, 95.5, 96.5, 95.0, 97.0, 95.5, 96.5, 95.0,
    ])
    reads = expect(rows, [
        ("monitoring", 2),
        ("developing", 1),
        ("underway", 4),
        ("stabilizing", 1), ("underway", 1),
        ("stabilizing", 1), ("underway", 1),
        ("stabilizing", 1), ("underway", 1),
        ("stabilizing", 1), ("underway", 1),
    ])
    for read in reads:
        if read["phase"] in {"underway", "stabilizing"}:
            assert -5.0 <= read["drawdown_pct"] <= -3.0
    assert reads[-1]["low_close"] == 95.0
    assert all(read["phase"] not in {"recovering", "repaired"} for read in reads)


def test_confirmed_dip_then_full_repair():
    # No shock_drawdown print. 99 is inside onset_drawdown. 97.5 crosses it
    # for one close (developing). 96 is the second close: onset_closes
    # confirms, and that close is the low (underway).
    # Two further closes keep no_new_low_closes below stabilization_closes.
    # The next one reaches stabilization_closes and is above its 5-close
    # average: stabilizing. It is still under the high, so reclaim_closes
    # has not started.
    # The first close back at 100 forces recovering (reclaim streak 1, below
    # reclaim_closes, no resolution). The second reaches reclaim_closes:
    # prior_high_reclaimed, phase repaired.
    rows = weekday_closes([100.0] * 63 + [
        99.0, 97.5, 96.0, 97.0, 98.0, 99.0, 100.0, 100.0,
    ])
    reads = expect(rows, [
        ("monitoring", 2),
        ("developing", 1),
        ("underway", 3),
        ("stabilizing", 1),
        ("recovering", 1),
        ("repaired", 1),
    ])
    assert not any(read["drawdown_pct"] <= -5.0 for read in reads)
    assert reads[-2]["phase"] == "recovering" and reads[-2]["resolution"] is None
    assert reads[-1]["resolution"] == "prior_high_reclaimed"
    assert reads[-1]["drawdown_pct"] == 0
    assert reads[-1]["active"] is False


def test_repair_then_a_fresh_pullback_uses_a_new_reference():
    # The first episode matches the full repair: onset_drawdown, onset_closes,
    # stabilization_closes, one close under reclaim_closes (recovering), then
    # reclaim_closes (repaired, prior_high_reclaimed). Repair sets the
    # reference floor to that close and clears the episode, so the next close
    # is classified again. 101, 103, and 105 are new highs, inside
    # onset_drawdown, with peak_basis post_repair_high: monitoring.
    # 102 is at least onset_drawdown under 105 for one close: developing.
    # 98 is at least shock_drawdown under that same post-repair high, so the
    # fresh episode confirms underway on this close. The pending streak also
    # reaches onset_closes. The new peak is 105, not the repaired episode's 100,
    # and the old trough is not reused.
    rows = weekday_closes([100.0] * 63 + [
        99.0, 97.5, 96.0, 97.0, 98.0, 99.0, 100.0, 100.0,
        101.0, 103.0, 105.0, 102.0, 98.0,
    ])
    reads = expect(rows, [
        ("monitoring", 2),
        ("developing", 1),
        ("underway", 3),
        ("stabilizing", 1),
        ("recovering", 1),
        ("repaired", 1),
        ("monitoring", 3),
        ("developing", 1),
        ("underway", 1),
    ])
    repaired_at = next(i for i, read in enumerate(reads) if read["phase"] == "repaired")
    repaired = reads[repaired_at]
    assert repaired["resolution"] == "prior_high_reclaimed"
    assert repaired["peak_close"] == 100.0
    restarted = reads[repaired_at + 1]
    assert restarted["phase"] == "monitoring"
    assert restarted["peak_basis"] == "post_repair_high"
    assert restarted["reference_reset_session"] == repaired["asof"]
    assert reads[-1]["phase"] == "underway" and reads[-1]["active"] is True
    assert reads[-1]["peak_close"] == 105.0
    assert reads[-1]["low_close"] == 98.0
    assert reads[-1]["peak_session"] > repaired["asof"]
    assert reads[-1]["reference_reset_session"] == repaired["asof"]


def test_two_close_holiday_gap_inside_an_episode():
    # Onset matches a non-shock dip: onset_drawdown once (developing), then
    # onset_closes (underway). The low is 96. Two rising closes leave
    # no_new_low_closes below stabilization_closes. The next rising close
    # reaches it and is above its 5-close average: stabilizing.
    # Friday 2025-04-11 and Monday 2025-04-14 are then omitted. The weekday
    # fixture still counts both as sessions, so the following close is not the
    # next observation. That resets no_new_low_closes below stabilization_closes
    # and restarts the contiguous count, so the phase falls to underway.
    # stabilization_closes is met again only on the fifth contiguous close
    # after the hole (no_new_low_closes is 4, and the close is above its
    # 5-close average). recovery_no_low_closes is not met, and the reset also
    # cleared the above-average streak, so recovery_above_ma_closes does not fire.
    # reclaim_closes never starts; the close stays under the high.
    full = weekday_closes([100.0] * 63 + [
        99.0, 97.5, 96.5, 96.0,
        96.5, 97.0, 97.5, 98.0, 98.5, 99.0,
        99.25, 99.5, 99.75, 99.875, 99.9375,
    ])
    omitted = [row for row in full if row[0] in {"2025-04-11", "2025-04-14"}]
    assert omitted == [("2025-04-11", 98.5), ("2025-04-14", 99.0)]
    assert all(session(date.fromisoformat(day)) for day, _ in omitted)
    rows = [row for row in full if row[0] not in {"2025-04-11", "2025-04-14"}]
    reads = expect(rows, [
        ("monitoring", 2),
        ("developing", 1),
        ("underway", 4),
        ("stabilizing", 2),
        ("underway", 4),
        ("stabilizing", 1),
    ])
    gap_at = next(i for i, read in enumerate(reads) if read["history_gap_count"])
    assert reads[gap_at - 1]["phase"] == "stabilizing"
    assert reads[gap_at - 1]["history_gap_count"] == 0
    assert reads[gap_at]["asof"] == "2025-04-15"
    assert reads[gap_at]["phase"] == "underway"
    assert reads[gap_at]["contiguous_closes"] == 1
    assert reads[gap_at]["no_new_low_closes"] == 0
    assert reads[-1]["history_gap_count"] == 1
    assert reads[-1]["phase"] == "stabilizing"
    assert reads[-1]["contiguous_closes"] == 5
    assert reads[-1]["no_new_low_closes"] == 4
    assert reads[-1]["low_close"] == 96.0


def test_pending_onset_ages_out_without_confirmation():
    # Seventy closes at 99, a one-close spike to 100, sixty-one closes back at
    # 99, a single 98, then twelve closes at 99.
    # Replay starts on the 63rd close, still in the opening 99s. Through the
    # day before 98 the spike is inside reference_closes, but 99 is only 1%
    # under it, short of onset_drawdown: monitoring.
    # 98 is exactly onset_drawdown under the spike, on the last session whose
    # reference_closes window still contains that spike. The streak is 1, below
    # onset_closes, and the print is short of shock_drawdown: developing.
    # On the next session the spike falls outside reference_closes. The pending
    # high is dropped before it can confirm. The new high is the latest 99
    # (equal highs keep the most recent close) and the close is 99, so the
    # drawdown is 0. The onset never confirms, and the phase returns to monitoring.
    rows = weekday_closes(
        [99.0] * 70 + [100.0] + [99.0] * 61 + [98.0] + [99.0] * 12
    )
    reads = expect(rows, [
        ("monitoring", 70),
        ("developing", 1),
        ("monitoring", 12),
    ])
    pending_at = next(i for i, read in enumerate(reads) if read["phase"] == "developing")
    assert reads[pending_at]["peak_close"] == 100.0
    assert reads[pending_at]["drawdown_pct"] == -2.0
    assert reads[pending_at]["active"] is False
    assert reads[pending_at + 1]["phase"] == "monitoring"
    assert reads[pending_at + 1]["peak_close"] == 99.0
    assert reads[-1]["peak_close"] == 99.0
    assert all(read["active"] is False for read in reads)
    assert max(price for _, price in rows) == 100.0
