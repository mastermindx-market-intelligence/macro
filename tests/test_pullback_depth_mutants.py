"""Mutation-survey kills for lib/pullback_depth.py (lane M4).

Each test pins one observed behaviour that a surviving single-edit mutant of
the presenter core broke; the ``M##`` tags match the survey table in the lane
report. Everything here is synthetic: no network, no market data, no fixtures
beyond hand-built dicts, and no forecast is computed or asserted anywhere.
"""
from __future__ import annotations

import datetime

import pytest

from lib import pullback_depth as core
from lib.pullback_depth import LicensedCloses, SourceRefused

AS = datetime.date(2026, 3, 10)
PEAK, CLOSE, LOW = 100.0, 93.2, 92.6
DATES = ["2026-09-14", "2026-09-16", "2026-09-21", "2026-09-24", "2026-09-30"]
CLOSES = [100.0, 97.0, 92.6, 93.8, 93.2]
# A valid but young window: it still starts at the peak and ends at as-of.
SHORT_DATES = ["2026-09-14", "2026-09-21", "2026-09-30"]
SHORT_CLOSES = [100.0, 92.6, 93.2]


def _vals(closes, peak=PEAK):
    """The owner's rounding: each close against the peak, 4 dp, unclipped."""
    return [round(100.0 * (p / peak - 1.0), 4) for p in closes]


def _path(dates, closes, peak=PEAK):
    return {"dates": list(dates), "vals": _vals(closes, peak)}


def _obs(path=None, **over):
    obs = {
        "schema": core.OBSERVATION_SCHEMA, "market": "cn", "available": True,
        "quality": "current", "clock": "settled_close", "phase": "underway",
        "active": True, "asof": DATES[-1], "peak_session": DATES[0],
        "peak_close": PEAK, "close": CLOSE, "low_close": LOW,
        "low_session": "2026-09-21", "drawdown_pct": -6.8,
        "price_path": path or _path(DATES, CLOSES),
    }
    obs.update(over)
    return obs


def _present(obs, market="cn"):
    return core.present(obs, market=market, aria_en="Drawdown", aria_zh="回撤")


# ── unavailable() shape ───────────────────────────────────────────────────────

def test_unavailable_reports_the_unavailable_phase_and_no_asof():
    # M03 (phase constant) / M04 (asof minted from the expected date): a view
    # the owner could not produce must not carry a phase or an as-of stamp.
    out = core.unavailable(AS, "delayed")
    assert out["phase"] == "unavailable"
    assert out["asof"] is None
    assert out["available"] is False
    assert out["quality"] == "delayed"
    assert out["expected_session"] == "2026-03-10"


# ── price_rows() label and pair contracts ─────────────────────────────────────

def test_price_rows_preserves_intraday_and_aware_labels_without_laundering():
    # M05 (or -> and): a midnight tz-aware stamp and a naive intraday stamp are
    # deliberately preserved; only a naive midnight collapses to a day label.
    frame = {"close": {
        datetime.datetime(2026, 1, 5, 9, 30): 5.0,
        datetime.datetime(2026, 1, 6, tzinfo=datetime.timezone.utc): 6.0,
        datetime.datetime(2026, 1, 7): 7.0,
        datetime.date(2026, 1, 8): 8.0,
        20260109: 9.0,
    }}
    assert core.price_rows(frame) == [
        ("2026-01-05T09:30:00", 5.0),
        ("2026-01-06T00:00:00+00:00", 6.0),
        ("2026-01-07", 7.0),
        ("2026-01-08", 8.0),
        ("20260109", 9.0),
    ]


def test_price_rows_pairs_are_label_then_value_from_the_named_column():
    # M06 (swapped pair order) plus the column admission: the rows feed the
    # owner as (session label, close); a second column is never read by default.
    frame = {"close": {datetime.date(2026, 1, 6): 6.0},
             "open": {datetime.date(2026, 1, 6): 5.5}}
    assert core.price_rows(frame) == [("2026-01-06", 6.0)]
    assert core.price_rows(frame, column="open") == [("2026-01-06", 5.5)]


# ── session_day() / positive() admission ──────────────────────────────────────

def test_session_day_admits_only_ten_char_iso_day_labels():
    # The 10-length gate is what keeps CPython's other accepted forms out:
    # date.fromisoformat also parses basic "20260105" and week "2026-W01-1",
    # and only the length check stops a compact stamp from being read as a
    # session day. (M07, `!= 10` -> `< 10`, survives every suite: it widens
    # the gate to lengths >= 10, and no such string parses — see the lane
    # report; the test pins the contract, the mutant is argued EQUIVALENT.)
    assert core.session_day("2026-01-05") == datetime.date(2026, 1, 5)
    assert core.session_day("2026-01-05T00:00:00") is None
    assert core.session_day("20260105") is None
    assert core.session_day("2026-1-5") is None
    assert core.session_day("not-a-date") is None


@pytest.mark.parametrize("bad", [True, False, "3", None, 0.0, -1.0,
                                 float("inf"), float("nan")])
def test_positive_admits_only_finite_positive_reals(bad):
    # M09 (bool exclusion dropped) / M10 (> 0 -> >= 0) / M11 (isfinite dropped):
    # a boolean close, a zero or negative price, and non-finite prices are all
    # unusable; the window must never be built from any of them.
    assert core.positive(bad) is None
    assert core.positive(1.0) == 1.0


def test_a_boolean_close_never_draws_a_self_consistent_window():
    # M09 again, at the behaviour level: with True coerced to 1.0 the crafted
    # path below is internally consistent, and the popup must still refuse it.
    obs = _obs(close=True,
               path={"dates": list(DATES), "vals": [0.0, -3.0, -7.4, -6.2, -99.0]})
    assert _present(obs)["detail_withheld"] == "uncovered"


# ── level_break() split detection ─────────────────────────────────────────────

def test_level_break_tolerates_the_band_and_flags_outside_it():
    # M02 (0.75 -> 0.8): a -24.9% single-session move stays inside the band.
    assert core.level_break([("2026-01-05", 100.0), ("2026-01-06", 75.1)]) is False
    assert core.level_break([("2026-01-05", 100.0), ("2026-01-06", 74.9)]) is True
    # M12 (guard `not` dropped): a calm series is never a break.
    assert core.level_break([("2026-01-05", 100.0), ("2026-01-06", 100.0)]) is False
    assert core.level_break([("2026-01-05", 100.0), ("2026-01-06", 134.0)]) is True


def test_level_break_reads_adjacent_sessions_only():
    # M14 (dated[1:] -> dated[2:]): the break between the first two sessions
    # must not be skipped just because the remaining pair is calm.
    rows = [("2026-01-05", 100.0), ("2026-01-06", 74.9), ("2026-01-07", 100.0)]
    assert core.level_break(rows) is True


# ── observe_closes() admission and schema gate ────────────────────────────────

def _always(day):
    return True


def _one_row_read(_expected):
    return LicensedCloses(rows=[("2026-03-10", 5.0)])


def _stub_observer(rows, *, expected_session, is_session):
    return core.unavailable(expected_session, "stub_clock_only")


def _run(read=None, observer=None):
    return core.observe_closes(AS, read=read, observer=observer, is_session=_always)


def test_empty_or_mistyped_source_results_stay_source_unavailable():
    # M17 (`or not got.rows` dropped): an admitted but empty series must not
    # reach the observer and inherit whatever quality it returns.
    # M60 (quality constant on the mistyped branch): a read result that is not
    # a LicensedCloses is a source failure, not an observer failure.
    out, tip = _run(read=lambda e: LicensedCloses(rows=[]), observer=_stub_observer)
    assert out["quality"] == "source_unavailable"
    assert tip == {"appended": [], "hold": None}
    out, _ = _run(read=lambda e: {"rows": []}, observer=_stub_observer)
    assert out["quality"] == "source_unavailable"


def test_the_owner_schema_string_is_admitted_not_a_private_drifted_one():
    # M57 (OBSERVATION_SCHEMA bumped to .v2): the gate must keep admitting the
    # owner's published schema, and present() must keep qualifying it.
    def owner_shaped(rows, *, expected_session, is_session):
        return {"schema": "pullback_observation.v1", "available": True,
                "quality": "current", "expected_session": "2026-03-10",
                "asof": "2026-03-10", "phase": "monitoring"}

    out, _ = _run(read=_one_row_read, observer=owner_shaped)
    assert out["quality"] == "current"
    assert _present(_obs(schema="pullback_observation.v1"))["phase"] == "underway"


def _owner_like(rows, *, expected_session, is_session):
    return {"schema": "pullback_observation.v1", "available": True,
            "quality": "current", "expected_session": "2026-03-10",
            "asof": "2026-03-10", "phase": "monitoring"}


def test_a_current_stamp_with_delayed_quality_is_inconsistent():
    # M20 (!= "current" -> ==): the gate must reject an available observation
    # whose own quality claim contradicts currency even when the dates agree.
    def delayed(rows, *, expected_session, is_session):
        out = _owner_like(rows, expected_session=expected_session,
                          is_session=is_session)
        out["quality"] = "delayed"
        return out

    out, _ = _run(read=_one_row_read, observer=delayed)
    assert out["quality"] == "observation_inconsistent"


def test_source_refusal_keeps_the_owner_quality_and_exceptions_degrade():
    # M21 (exc.quality replaced): a refused basis names its own quality.
    # M22 (KeyError narrowed out of the except): an observer crash degrades to
    # source_unavailable instead of taking the popup down.
    def refused(rows, *, expected_session, is_session):
        raise SourceRefused("stale_basis")

    def keyerror(rows, *, expected_session, is_session):
        raise KeyError("boom")

    assert _run(read=_one_row_read, observer=refused)[0]["quality"] == "stale_basis"
    assert _run(read=_one_row_read, observer=keyerror)[0]["quality"] == "source_unavailable"


def test_the_session_tip_carries_the_appended_rows_and_the_hold():
    # M23 (hold dropped): the expiry/hold surface the adapters surface must
    # survive observe_closes untouched.
    read = lambda e: LicensedCloses(rows=[("2026-03-10", 5.0)],
                                    appended=("2026-03-10",), hold="halt")
    out, tip = _run(read=read, observer=_stub_observer)
    assert tip == {"appended": ["2026-03-10"], "hold": "halt"}
    assert out["quality"] == "stub_clock_only"


# ── episode_window() ──────────────────────────────────────────────────────────

def test_a_consistent_episode_window_draws_whole_with_the_metric_end():
    # M25 (start index + 1) / M26 (!= -> == at the as-of end) / M28 (self-zip)
    # / M29 (0.0 boundary excluded) / M36 (low indexed at 0) / M45 (window
    # inversion) / M48 (withheld `or` -> `and`): the canonical window starts at
    # the peak, holds the low, ends at as-of, and is drawn.
    view = _present(_obs())
    assert view["phase"] == "underway"
    assert view["detail_withheld"] is None
    assert view["detail_path"]["dates"] == DATES
    assert view["detail_path"]["vals"][0] == 0.0
    assert view["detail_path"]["vals"][-1] == 100.0 * (CLOSE / PEAK - 1.0)


def test_the_drawn_end_point_is_the_metrics_own_ratio_not_the_path_tail():
    # M38 (end point no longer re-drawn): the owner rounds its path to 4 dp, so
    # its last value can sit half a tenth from the metric; the chart ends on
    # the metric's own ratio.
    obs = _obs(path={"dates": list(DATES), "vals": [0.0, -3.0, -7.4, -6.2, -6.8005]})
    assert _present(obs)["detail_path"]["vals"][-1] == 100.0 * (CLOSE / PEAK - 1.0)


def test_a_peak_outside_the_retained_path_is_refused_without_raising():
    # M24 (membership early return removed): index() would raise on a peak the
    # cap already aged out; the popup must withhold instead.
    obs = _obs(path={"dates": DATES[1:], "vals": _vals(CLOSES)[1:]})
    view = _present(obs)
    assert view["detail_withheld"] == "uncovered"
    assert view["detail_path"] is None


def test_a_window_that_does_not_end_at_asof_is_refused():
    # M26 at the refusal side: consistent numbers on a stale end date are
    # still not the episode the metrics describe.
    obs = _obs(path={"dates": [DATES[0], DATES[2], DATES[3], DATES[4], "2026-09-29"],
                     "vals": [0.0, -7.4, -6.2, -6.8, -6.8]})
    assert core.episode_window(obs) is None


def test_window_dates_must_be_strictly_increasing_and_in_range():
    # M27 (<= -> <): a duplicated session label is not a measured path.
    # M29 at the refusal side: a point above the 0% line is not a drawdown.
    dup = _obs(path={"dates": [DATES[0], DATES[0], DATES[2], DATES[3], DATES[4]],
                     "vals": [0.0, 0.0, -7.4, -6.2, -6.8]})
    assert core.episode_window(dup) is None
    above = _obs(path={"dates": list(DATES), "vals": [0.0, -3.0, -7.4, -6.2, 0.5]})
    assert core.episode_window(above) is None


def test_the_first_point_must_sit_at_the_reference_high():
    # M31 (tolerance 0.01 -> 1.0): a window starting half a point below the
    # high contradicts the peak the metrics name.
    obs = _obs(path={"dates": list(DATES), "vals": [-0.5, -3.0, -7.4, -6.2, -6.8]})
    assert core.episode_window(obs) is None


def test_a_reclaimed_close_draws_above_the_reference_high():
    # A close above the frozen high is drawn at its own ratio, not flattened to 0.
    end = 100.0 * (100.5 / PEAK - 1.0)
    obs = _obs(phase="repaired", active=False, close=100.5,
               path={"dates": list(DATES), "vals": [0.0, -3.0, -7.4, -6.2, round(end, 4)]})
    view = _present(obs)
    assert view["detail_path"] is not None
    assert view["detail_path"]["vals"][-1] == end
    assert end > 0


def test_the_window_must_hold_the_episode_low():
    # M32 (low checks inverted) / M35 (`not in` inverted): the drawn window
    # contains the measured low, and only windows that do are accepted.
    missing = _obs(path={"dates": [DATES[0], DATES[1], DATES[3], "2026-09-27", DATES[4]],
                         "vals": [0.0, -3.0, -6.2, -6.5, -6.8]})
    assert core.episode_window(missing) is None


def test_the_low_point_must_agree_with_the_measured_low_close():
    # M36 at the refusal side: the value at the low session, not the window's
    # first point, is what must match low_close against the peak.
    obs = _obs(path={"dates": list(DATES), "vals": [0.0, -3.0, -3.4, -6.2, -6.8]})
    assert core.episode_window(obs) is None


def test_no_path_point_may_dive_below_the_measured_low():
    # M37 (< -> >): the owner's low is the episode minimum; a path that dips
    # past it contradicts the worst figure printed beside the chart.
    obs = _obs(path={"dates": list(DATES), "vals": [0.0, -3.0, -7.4, -8.4, -6.8]})
    assert core.episode_window(obs) is None


def test_a_pre_episode_window_without_a_low_still_counts_as_short():
    # M32 (inversion also breaks this side) / M33 (developing dropped from the
    # no-episode phases) / M47 (`and` -> `or` at the chart gate): a young but
    # valid monitoring/developing window is "short", never "uncovered", and is
    # never drawn below MIN_CHART_POINTS.
    for phase in ("monitoring", "developing"):
        obs = _obs(path=_path(SHORT_DATES, SHORT_CLOSES), phase=phase, active=False,
                   low_close=None, low_session=None)
        view = _present(obs)
        assert view["detail_withheld"] == "short", phase
        assert view["detail_chart_html"] == ""


def test_monitoring_with_a_low_close_is_not_treated_as_pre_episode():
    # M34 (`and` -> `or`): a low_close without a low session is not an episode
    # the presenter may skip checking.
    obs = _obs(path=_path(SHORT_DATES, SHORT_CLOSES), phase="monitoring",
               active=False, low_close=LOW, low_session=None)
    assert _present(obs)["detail_withheld"] == "uncovered"


# ── present() qualification and the read model ────────────────────────────────

def test_four_points_meet_the_chart_minimum():
    # M01 (MIN_CHART_POINTS 4 -> 5) / M46 (>= -> >): four points is the shared
    # renderer's floor, and a four-point window draws.
    obs = _obs(path=_path(DATES[:3] + [DATES[4]], [100.0, 97.0, 92.6, 93.2]))
    view = _present(obs)
    assert view["detail_withheld"] is None
    assert len(view["detail_path"]["dates"]) == 4


def test_a_non_mapping_observation_is_unavailable_not_a_crash():
    # M39 (guard removed): the adapters may hand over junk; present() answers.
    for junk in (None, [1, 2], "underway"):
        view = _present(junk)
        assert view["phase"] == "unavailable"
        # An unavailable phase withholds nothing: no chart promise to explain.
        assert view["detail_withheld"] is None
        assert view["detail_chart_html"] == ""


def test_every_qualification_clause_binds():
    # M42 (a clause loosened with `or`): a wrong-schema observation that looks
    # current everywhere else stays unavailable.
    # M43 (`in PHASES` inverted): an unknown phase never renders, and a real
    # one is not discarded.
    wrong_schema = _obs(schema="nope.v9")
    assert _present(wrong_schema)["phase"] == "unavailable"
    bogus = _present(_obs(phase="bogus"))
    assert bogus["phase"] == "unavailable"
    assert bogus["detail_withheld"] is None
    assert _present(_obs(phase="repaired"))["phase"] == "repaired"


def test_repaired_is_a_phase_of_its_own():
    # M56 ("repaired" dropped from PHASES): a repaired observation renders as
    # repaired, not as an outage.
    assert "repaired" in core.PHASES
    assert _present(_obs(phase="repaired"))["phase"] == "repaired"


def test_an_observation_without_a_path_withholds_as_uncovered():
    # M49 (short/uncovered inverted): no window at all is "uncovered"; "short"
    # is reserved for a window the chart floor refused.
    obs = _obs()
    del obs["price_path"]
    view = _present(obs)
    assert view["detail_withheld"] == "uncovered"
    assert view["detail_path"] is None


def test_the_chart_is_drawn_by_the_shared_renderer_under_its_own_contracts():
    # M50-M55 (kind/height/accent/reference/format/max_points): the popup
    # draws a drawdown of the shown window with the down accent, a zero-trim
    # percent format, and every close the owner kept.
    import lib.illus as illus_module
    from lib.pullback_observation import PATH_MAX_CLOSES

    seen = {}

    def fake_illus(series, **kwargs):
        seen["series"] = series
        seen.update(kwargs)
        return "<figure class=\"ilx\"></figure>"

    pytest_monkey = pytest.MonkeyPatch()
    try:
        pytest_monkey.setattr(illus_module, "illus", fake_illus)
        view = _present(_obs())
    finally:
        pytest_monkey.undo()
    assert view["detail_chart_html"] == "<figure class=\"ilx\"></figure>"
    assert seen["series"] is view["detail_path"]
    assert seen["kind"] == "drawdown"
    assert seen["height"] == 188
    assert seen["accent"] == "var(--down)"
    assert seen["reference"] == 0
    assert seen["value_fmt"] == "{:z.1f}%"
    assert seen["max_points"] == PATH_MAX_CLOSES
    assert seen["aria_en"] == "Drawdown" and seen["aria_zh"] == "回撤"
