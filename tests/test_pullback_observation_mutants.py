"""Killers for the manual mutation survey of lib/pullback_observation.py.

Every test pins a decision boundary the pre-existing suites left uncovered;
every input is synthetic and no test reads or writes a data file.
Each docstring names the mutant id from the survey table.
"""
from __future__ import annotations

from datetime import date, timedelta

from lib.pullback_observation import observe


def session(day):
    return day.weekday() < 5


def rows_for(tail, baseline=64):
    values = [100.0] * baseline + list(tail)
    day = date(2025, 1, 2)
    rows = []
    for value in values:
        while not session(day):
            day += timedelta(days=1)
        rows.append((day.isoformat(), value))
        day += timedelta(days=1)
    return rows


def result(rows):
    return observe(rows, expected_session=date.fromisoformat(rows[-1][0]),
                   is_session=session)


def test_equal_lows_inside_a_pending_attempt_keep_the_first_low():
    # M08: the attempt-low min() tie-break keeps the FIRST equal low, so the
    # confirming close is one observed session without a new low.
    rows = rows_for([97.5, 97.5])
    read = result(rows)
    assert read["phase"] == "underway" and read["active"] is True
    assert read["low_session"] == rows[-2][0]
    assert read["no_new_low_closes"] == 1


def test_a_pending_high_alive_on_its_exact_window_boundary_still_confirms():
    # M10: the aged-out check is strict (<); a pending high sitting on the
    # window's first close is still inside the window and may confirm today.
    rows = rows_for([100.0] * 63 + [105.0] + [104.0] * 60 + [102.0, 102.0],
                    baseline=0)
    read = result(rows)
    assert read["active"] is True and read["phase"] == "underway"
    assert read["peak_close"] == 105.0 and read["low_close"] == 102.0


def test_the_onset_gate_tolerates_float_noise_at_the_two_percent_boundary():
    # M54: 1 - 98.00000000000001/100 is 0.019999999999999907, a hair under the
    # 2% gate; the deliberate 1e-12 slack must still open a pending attempt.
    read = result(rows_for([98.00000000000001]))
    assert read["phase"] == "developing" and read["active"] is False
    assert read["onset_session"] is None


def test_an_equal_low_is_not_a_new_low_and_does_not_reset_the_clock():
    # M16: a close equal to the episode low neither moves the trough off its
    # first date nor resets the no-new-low count.
    rows = rows_for([95.0, 90.0, 91.0, 90.0, 91.0])
    read = result(rows)
    assert read["low_session"] == rows[-4][0]
    assert read["no_new_low_closes"] == 3


def test_a_missing_session_inside_an_episode_resets_the_no_new_low_clock():
    # M18: the no-new-low counter advances only across a joined session.
    rows = rows_for([95.0, 90.0, 91.0, 92.0, 92.5])
    rows.pop(-3)  # the 91.0 close becomes a missing expected session
    read = result(rows)
    assert read["history_gap_count"] == 1
    assert read["no_new_low_closes"] == 1


def test_stabilization_arrives_at_exactly_five_contiguous_closes_after_a_gap():
    # M19: the stabilization gate is >= 5 contiguous closes, not > 5.
    rows = rows_for([94.9, 100.0, 90.0, 91.0, 92.0, 93.0, 94.0])
    rows.pop(-6)  # the filler close becomes a missing expected session
    read = result(rows)
    assert read["contiguous_closes"] == 5
    assert read["phase"] == "stabilizing" and read["active"] is True


def test_the_twenty_close_average_is_a_full_twenty_close_window():
    # M21: on a short ramp onto a plateau, a 19-close average sits above the
    # close and kills the above-average streak; the full window keeps it.
    rows = rows_for([95.0, 80.0] + [80.0 + 0.1 * t for t in range(1, 9)]
                    + [80.8] * 18)
    read = result(rows)
    assert read["phase"] == "recovering" and read["active"] is True


def test_recovering_needs_exactly_twenty_five_contiguous_closes_after_a_gap():
    # M23: the recovering gate is >= 25 contiguous closes, not > 25.
    rows = rows_for([95.0, 80.0] + [81.0 + 0.25 * i for i in range(26)])
    rows.pop(66)  # the first ramp close becomes a missing expected session
    read = result(rows)
    assert read["contiguous_closes"] == 25
    assert read["phase"] == "recovering" and read["active"] is True


def test_rising_twenty_compares_against_the_mean_five_sessions_ago():
    # M24: rising20 compares ma20 with the mean of closes i-24..i-4 (five
    # sessions ago); widening that slice to six ago delays the verdict.
    rows = rows_for([95.0, 80.0] + [81.0 + 0.25 * i for i in range(23)])
    read = result(rows)
    assert read["phase"] == "recovering" and read["active"] is True


def test_the_phase_trail_keeps_the_last_six_transitions():
    # M30: oscillating reclaim/relinquish appends more than six transitions;
    # the exposed trail keeps the last SIX, so the first kept is a reclaim.
    rows = rows_for([95.0, 90.0, 91.0, 92.0] + [100.5, 93.0] * 4)
    read = result(rows)
    assert len(read["price_transitions"]) == 6
    assert read["price_transitions"][0]["phase"] == "recovering"


def test_the_price_path_rounds_to_four_decimals():
    # M34: 97.1357 under the 100 peak is -2.8643%; three decimals lose a digit.
    read = result(rows_for([97.1357]))
    assert read["price_path"]["vals"][-1] == -2.8643


def test_below_the_twenty_close_average_uses_the_last_twenty_closes():
    # M37: the planted 50.0 is exactly 20 closes back; a 19-close window would
    # hide it and call 93.5 below the average.
    read = result(rows_for([50.0] + [95.0] * 18 + [93.5]))
    assert read["below_20_close_average"] is False


def test_last_calendar_disagreement_is_the_latest_one():
    # M42: two archived disagreements must report the LATEST date.
    rows = rows_for([100.0] * 70)
    closed = {rows[1][0], rows[3][0]}
    read = observe(rows, expected_session=date.fromisoformat(rows[-1][0]),
                   is_session=lambda day: session(day)
                   and day.isoformat() not in closed)
    assert read["available"] is True and read["phase"] == "monitoring"
    assert read["calendar_disagreement_count"] == 2
    assert read["last_calendar_disagreement"] == rows[3][0]


def test_the_timeline_is_sorted_oldest_first_with_the_latest_close_last():
    # M47: timeline rows run in ascending date order and the latest close last.
    read = result(rows_for([95.0, 90.0, 92.0]))
    dates = [row["date"] for row in read["timeline"]]
    assert dates == sorted(dates)
    assert read["timeline"][-1]["kind"] == "latest"


def test_history_gap_count_counts_one_per_gap():
    # M49: one missing expected session adds exactly one gap.
    rows = rows_for([97.0, 96.5, 96.0])
    rows.pop(-2)
    read = result(rows)
    assert read["history_gap_count"] == 1
    assert read["contiguous_closes"] == 1


def test_an_unexpected_row_shape_fails_closed_not_loud():
    # M53: iterating malformed rows can raise TypeError; the except clause
    # must catch it and return an explicit invalid_observation.
    read = observe([None], expected_session=date(2025, 1, 2), is_session=session)
    assert read["quality"] == "invalid_observation"
    assert read["available"] is False and read["phase"] == "unavailable"


def test_recovering_arrives_at_exactly_five_closes_above_the_average():
    # A13: the above-the-20-close-average gate is >= 5. The flat shelf holds
    # the streak at zero (a 91.0 shelf sits a hair under its own 20-close
    # average because the 95/90 dip outweighs two shelf closes), so the
    # streak is exactly five on the fifth rise close.
    rows = rows_for([95.0, 90.0] + [91.0] * 24 + [91.5, 92.0, 92.5, 93.0, 93.5])
    read = result(rows)
    assert read["phase"] == "recovering" and read["active"] is True


def test_recovering_arrives_at_exactly_ten_closes_without_a_new_low():
    # A14: the no-new-low gate is >= 10. A fresh low under the episode trough
    # resets the clock, and the tenth rise close is the first that qualifies.
    rows = rows_for([95.0, 90.0] + [91.0] * 24 + [89.9]
                    + [91.5, 92.0, 92.5, 93.0, 93.5,
                       94.0, 94.5, 95.0, 95.5, 96.0])
    read = result(rows)
    assert read["no_new_low_closes"] == 10
    assert read["phase"] == "recovering" and read["active"] is True


def test_a_close_exactly_at_the_twenty_close_average_is_not_below_it():
    # A39: "below the 20-close average" is strict; a close sitting exactly on
    # the average of the last twenty closes is not below it.
    read = result(rows_for([100.0]))
    assert read["phase"] == "monitoring" and read["active"] is False
    assert read["below_20_close_average"] is False
