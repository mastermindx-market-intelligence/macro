"""Tests for the knowledge-time (point-in-time eligibility) law.

All dates below are synthetic calendar constructions, not market data.
Every clock is supplied by the caller; the module under test never reads
the system clock, so each test pins its own wall clock.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

import engine.global_liquidity_knowledge_time as kt
from engine.global_liquidity_knowledge_time import (
    Observation,
    anchor_month_end,
    availability_start_utc,
    cutoff_utc,
    earliest_possible_utc,
    eligible_as_of,
    latest_by_series,
    observation_from_wrapper,
)

UTC = timezone.utc
WALL = datetime(2026, 9, 1, tzinfo=UTC)  # fixed synthetic wall clock for every test


def _aware(y, m, d, hh=0, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=UTC)


def test_boj_month_start_label_is_refused():
    with pytest.raises(kt.KnowledgeTimeError, match="C09"):
        Observation(
            series_id="BOJ_MONETARY_BASE",
            observation_id="boj-bad-label",
            economic_period_end=date(2026, 7, 1),
            published_at=_aware(2026, 8, 4),
            evidence_available_at=_aware(2026, 8, 4),
            vintage_id="v1",
            value=1.0,
            period_anchor="month_end",
            availability_tz="Asia/Tokyo",
        )
    assert anchor_month_end(date(2026, 7, 1)) == date(2026, 7, 31)
    assert anchor_month_end(date(2026, 1, 31)) == date(2026, 1, 31)
    assert anchor_month_end(date(2024, 2, 5)) == date(2024, 2, 29)
    with pytest.raises(kt.KnowledgeTimeError, match="datetime"):
        anchor_month_end(datetime(2026, 7, 1))


def test_boj_month_end_value_not_disclosed_early():
    obs = Observation(
        series_id="BOJ_MONETARY_BASE",
        observation_id="boj-2026-07",
        economic_period_end=date(2026, 7, 31),
        published_at=date(2026, 8, 4),
        evidence_available_at=date(2026, 8, 4),
        vintage_id="v1",
        value=Decimal("42"),
        period_anchor="month_end",
        availability_tz="Asia/Tokyo",
    )
    for as_of in (date(2026, 7, 31), date(2026, 8, 1), date(2026, 8, 4)):
        res = eligible_as_of([obs], as_of, wall_clock=WALL, decision_tz="Asia/Tokyo")
        assert res.rows == (), f"unexpectedly eligible as_of {as_of}"
    res = eligible_as_of([obs], date(2026, 8, 5), wall_clock=WALL, decision_tz="Asia/Tokyo")
    assert len(res.rows) == 1
    assert res.rows[0].value == Decimal("42")
    assert res.rows[0].observation_id == "boj-2026-07"


def test_month_end_publication_on_or_before_period_end_is_refused():
    with pytest.raises(kt.KnowledgeTimeError, match="strictly after"):
        Observation(
            series_id="BOJ_MONETARY_BASE",
            observation_id="boj-early-pub",
            economic_period_end=date(2026, 7, 31),
            published_at=date(2026, 7, 31),
            evidence_available_at=date(2026, 8, 1),
            vintage_id="v1",
            value=1.0,
            period_anchor="month_end",
            availability_tz="Asia/Tokyo",
        )


def test_date_only_bound_becomes_available_after_local_date_elapses():
    # EDT = UTC-4: local midnight of 2026-08-05 is 04:00Z.
    assert availability_start_utc(date(2026, 8, 4), "America/New_York") == _aware(2026, 8, 5, 4)
    assert earliest_possible_utc(date(2026, 8, 4), "America/New_York") == _aware(2026, 8, 4, 4)
    obs = Observation(
        series_id="NY_SERIES",
        observation_id="ny-1",
        economic_period_end=date(2026, 7, 31),
        published_at=date(2026, 8, 4),
        evidence_available_at=date(2026, 8, 4),
        vintage_id="v1",
        value=7.5,
        availability_tz="America/New_York",
    )
    res = eligible_as_of([obs], _aware(2026, 8, 5, 3, 59), wall_clock=WALL)
    assert res.rows == ()
    res = eligible_as_of([obs], _aware(2026, 8, 5, 4, 0), wall_clock=WALL)
    assert len(res.rows) == 1
    assert res.rows[0].value == 7.5


def test_datetime_bound_is_inclusive():
    obs = Observation(
        series_id="DT_SERIES",
        observation_id="dt-1",
        economic_period_end=date(2026, 7, 31),
        published_at=_aware(2026, 8, 6, 13, 30),
        evidence_available_at=_aware(2026, 8, 6, 13, 30),
        vintage_id="v1",
        value=2.0,
    )
    res = eligible_as_of([obs], _aware(2026, 8, 6, 13, 29), wall_clock=WALL)
    assert res.rows == ()
    res = eligible_as_of([obs], _aware(2026, 8, 6, 13, 30), wall_clock=WALL)
    assert len(res.rows) == 1


def test_delayed_holiday_publication_uses_actual_publication():
    # Scheduled release 2026-08-03 falls on a holiday; the source actually
    # publishes on 2026-08-05. Only the actual publication/evidence dates exist.
    obs = Observation(
        series_id="HOL_SERIES",
        observation_id="hol-1",
        economic_period_end=date(2026, 6, 30),
        published_at=date(2026, 8, 5),
        evidence_available_at=date(2026, 8, 5),
        vintage_id="v1",
        value=11.0,
        availability_tz="UTC",
    )
    for as_of in (date(2026, 8, 3), date(2026, 8, 4), date(2026, 8, 5)):
        res = eligible_as_of([obs], as_of, wall_clock=WALL, decision_tz="UTC")
        assert res.rows == (), f"unexpectedly eligible as_of {as_of}"
    res = eligible_as_of([obs], date(2026, 8, 6), wall_clock=WALL, decision_tz="UTC")
    assert len(res.rows) == 1
    assert res.rows[0].value == 11.0


def test_same_cutoff_revision_keeps_first_known_value_and_records_amendment():
    o_m1 = Observation(
        series_id="S",
        observation_id="o-m1",
        economic_period_end=date(2026, 5, 31),
        published_at=_aware(2026, 6, 5, 12),
        evidence_available_at=_aware(2026, 6, 5, 12),
        vintage_id="v1",
        value=100.0,
    )
    o_m = Observation(
        series_id="S",
        observation_id="o-m",
        economic_period_end=date(2026, 6, 30),
        published_at=_aware(2026, 7, 5, 12),
        evidence_available_at=_aware(2026, 7, 5, 12),
        vintage_id="v2",
        value=200.0,
    )
    c_m1 = Observation(
        series_id="S",
        observation_id="c-m1",
        economic_period_end=date(2026, 5, 31),
        published_at=_aware(2026, 7, 5, 12),
        evidence_available_at=_aware(2026, 7, 5, 12),
        vintage_id="v2",
        value=101.0,
        is_correction=True,
        supersedes="o-m1",
    )
    records = [o_m1, o_m, c_m1]

    # Between the two releases: m-1 keeps its first-known value, m is absent.
    res = eligible_as_of(records, _aware(2026, 6, 20), wall_clock=WALL)
    assert len(res.rows) == 1
    row_m1 = res.rows[0]
    assert row_m1.economic_period_end == date(2026, 5, 31)
    assert row_m1.value == 100.0
    assert row_m1.amendments == ()

    # At/after the second release: value is still the first-known original...
    res = eligible_as_of(records, _aware(2026, 7, 5, 12), wall_clock=WALL)
    assert {(r.economic_period_end, r.value) for r in res.rows} == {
        (date(2026, 5, 31), 100.0),
        (date(2026, 6, 30), 200.0),
    }
    row_m1 = next(r for r in res.rows if r.economic_period_end == date(2026, 5, 31))
    # ...and the revision is recorded as an amendment, never a replacement.
    assert len(row_m1.amendments) == 1
    amd = row_m1.amendments[0]
    assert amd.observation_id == "c-m1"
    assert amd.value == 101.0
    assert amd.supersedes == "o-m1"


def test_correction_known_at_same_instant_as_original_is_refused():
    o = Observation(
        series_id="S",
        observation_id="o-1",
        economic_period_end=date(2026, 6, 30),
        published_at=_aware(2026, 7, 5, 12),
        evidence_available_at=_aware(2026, 7, 5, 12),
        vintage_id="v1",
        value=1.0,
    )
    c = Observation(
        series_id="S",
        observation_id="c-1",
        economic_period_end=date(2026, 6, 30),
        published_at=_aware(2026, 7, 5, 12),
        evidence_available_at=_aware(2026, 7, 5, 12),
        vintage_id="v2",
        value=1.5,
        is_correction=True,
        supersedes="o-1",
    )
    with pytest.raises(kt.KnowledgeTimeError, match="strictly after"):
        eligible_as_of([o, c], _aware(2026, 8, 1), wall_clock=WALL)


def test_correction_chain_walks_to_root_original():
    o = Observation(
        series_id="CH",
        observation_id="o",
        economic_period_end=date(2026, 6, 30),
        published_at=_aware(2026, 7, 5, 12),
        evidence_available_at=_aware(2026, 7, 5, 12),
        vintage_id="v1",
        value=1.0,
    )
    c1 = Observation(
        series_id="CH",
        observation_id="c1",
        economic_period_end=date(2026, 6, 30),
        published_at=_aware(2026, 7, 10, 12),
        evidence_available_at=_aware(2026, 7, 10, 12),
        vintage_id="v2",
        value=2.0,
        is_correction=True,
        supersedes="o",
    )
    c2 = Observation(
        series_id="CH",
        observation_id="c2",
        economic_period_end=date(2026, 6, 30),
        published_at=_aware(2026, 7, 15, 12),
        evidence_available_at=_aware(2026, 7, 15, 12),
        vintage_id="v3",
        value=3.0,
        is_correction=True,
        supersedes="c1",
    )
    res = eligible_as_of([o, c1, c2], _aware(2026, 8, 1), wall_clock=WALL)
    assert len(res.rows) == 1
    row = res.rows[0]
    assert row.observation_id == "o"
    assert row.value == 1.0
    assert [a.observation_id for a in row.amendments] == ["c1", "c2"]
    assert [a.value for a in row.amendments] == [2.0, 3.0]


def test_dangling_supersedes_and_cross_series_correction_are_refused():
    o = Observation(
        series_id="A",
        observation_id="a-1",
        economic_period_end=date(2026, 6, 30),
        published_at=_aware(2026, 7, 5, 12),
        evidence_available_at=_aware(2026, 7, 5, 12),
        vintage_id="v1",
        value=1.0,
    )
    dangling = Observation(
        series_id="A",
        observation_id="a-c-dangling",
        economic_period_end=date(2026, 6, 30),
        published_at=_aware(2026, 7, 10, 12),
        evidence_available_at=_aware(2026, 7, 10, 12),
        vintage_id="v2",
        value=1.1,
        is_correction=True,
        supersedes="nope",
    )
    with pytest.raises(kt.KnowledgeTimeError, match="dangling supersedes"):
        eligible_as_of([o, dangling], _aware(2026, 8, 1), wall_clock=WALL)

    cross_series = Observation(
        series_id="B",
        observation_id="b-c-cross",
        economic_period_end=date(2026, 6, 30),
        published_at=_aware(2026, 7, 10, 12),
        evidence_available_at=_aware(2026, 7, 10, 12),
        vintage_id="v2",
        value=9.0,
        is_correction=True,
        supersedes="a-1",
    )
    with pytest.raises(kt.KnowledgeTimeError, match="series_id or economic_period_end"):
        eligible_as_of([o, cross_series], _aware(2026, 8, 1), wall_clock=WALL)

    cross_period = Observation(
        series_id="A",
        observation_id="a-c-period",
        economic_period_end=date(2026, 5, 31),
        published_at=_aware(2026, 7, 10, 12),
        evidence_available_at=_aware(2026, 7, 10, 12),
        vintage_id="v2",
        value=1.2,
        is_correction=True,
        supersedes="a-1",
    )
    with pytest.raises(kt.KnowledgeTimeError, match="series_id or economic_period_end"):
        eligible_as_of([o, cross_period], _aware(2026, 8, 1), wall_clock=WALL)


def test_duplicate_originals_are_refused():
    o1 = Observation(
        series_id="A",
        observation_id="a-1",
        economic_period_end=date(2026, 6, 30),
        published_at=_aware(2026, 7, 5, 12),
        evidence_available_at=_aware(2026, 7, 5, 12),
        vintage_id="v1",
        value=1.0,
    )
    o2 = Observation(
        series_id="A",
        observation_id="a-1-dup",
        economic_period_end=date(2026, 6, 30),
        published_at=_aware(2026, 7, 6, 12),
        evidence_available_at=_aware(2026, 7, 6, 12),
        vintage_id="v2",
        value=2.0,
    )
    with pytest.raises(kt.KnowledgeTimeError, match="duplicate originals"):
        eligible_as_of([o1, o2], _aware(2026, 8, 1), wall_clock=WALL)
    # A different period for the same series is fine.
    o3 = Observation(
        series_id="A",
        observation_id="a-2",
        economic_period_end=date(2026, 5, 31),
        published_at=_aware(2026, 6, 5, 12),
        evidence_available_at=_aware(2026, 6, 5, 12),
        vintage_id="v1",
        value=0.5,
    )
    res = eligible_as_of([o1, o3], _aware(2026, 8, 1), wall_clock=WALL)
    assert len(res.rows) == 2


def test_latest_vintage_cannot_be_first_known():
    kwargs = dict(
        series_id="LX",
        observation_id="lx-1",
        economic_period_end=date(2026, 6, 30),
        published_at=_aware(2026, 7, 5, 12),
        evidence_available_at=_aware(2026, 7, 5, 12),
        vintage_id="latest",
        value=9.0,
    )
    with pytest.raises(kt.KnowledgeTimeError, match="latest vintage"):
        Observation(**kwargs)

    obs = Observation(**kwargs, availability_basis="release_lag_aligned_reconstruction")
    # Excluded under the default allowed_bases, counted, never relabelled.
    res = eligible_as_of([obs], _aware(2026, 8, 1), wall_clock=WALL)
    assert res.rows == ()
    assert res.excluded_basis_count == 1

    res = eligible_as_of(
        [obs],
        _aware(2026, 8, 1),
        wall_clock=WALL,
        allowed_bases=("first_system_known", "release_lag_aligned_reconstruction"),
    )
    assert len(res.rows) == 1
    assert res.rows[0].availability_basis == "release_lag_aligned_reconstruction"
    assert res.rows[0].vintage_id == "latest"


def test_wrapper_generated_at_cannot_backdate_availability():
    base = dict(
        series_id="W",
        observation_id="w-1",
        economic_period_end=date(2026, 7, 31),
        published_at=_aware(2026, 8, 4, 9),
        vintage_id="v1",
        value=5.0,
    )
    with pytest.raises(kt.KnowledgeTimeError, match="cannot backdate availability"):
        observation_from_wrapper(
            **base,
            wrapper_generated_at=_aware(2026, 8, 4, 20),
            row_first_known_at=_aware(2026, 8, 4, 10),
            claimed_available_at=_aware(2026, 8, 1, 12),
        )
    with pytest.raises(kt.KnowledgeTimeError, match="wrapper_generated_at"):
        observation_from_wrapper(
            **base,
            wrapper_generated_at=_aware(2026, 8, 4, 20),
            row_first_known_at=_aware(2026, 8, 4, 21),
        )
    # A later claimed_available_at is honoured as the evidence time.
    obs = observation_from_wrapper(
        **base,
        wrapper_generated_at=_aware(2026, 8, 4, 20),
        row_first_known_at=_aware(2026, 8, 4, 10),
        claimed_available_at=_aware(2026, 8, 6, 9),
    )
    assert obs.evidence_available_at == _aware(2026, 8, 6, 9)
    assert obs.availability_basis == "first_system_known"
    res = eligible_as_of([obs], _aware(2026, 8, 6, 8, 59), wall_clock=WALL)
    assert res.rows == ()
    res = eligible_as_of([obs], _aware(2026, 8, 6, 9), wall_clock=WALL)
    assert len(res.rows) == 1


def test_evidence_before_publication_is_refused():
    with pytest.raises(kt.KnowledgeTimeError, match="backdating refused"):
        Observation(
            series_id="E",
            observation_id="e-1",
            economic_period_end=date(2026, 6, 30),
            published_at=_aware(2026, 7, 10, 12),
            evidence_available_at=_aware(2026, 7, 5, 12),
            vintage_id="v1",
            value=1.0,
        )


def test_naive_datetime_and_missing_tz_are_refused():
    base = dict(
        series_id="N",
        observation_id="n-1",
        economic_period_end=date(2026, 6, 30),
        vintage_id="v1",
        value=1.0,
    )
    with pytest.raises(kt.KnowledgeTimeError, match="naive datetime"):
        Observation(
            **base,
            published_at=datetime(2026, 7, 5, 12),
            evidence_available_at=_aware(2026, 7, 5, 12),
        )
    with pytest.raises(kt.KnowledgeTimeError, match="naive datetime"):
        Observation(
            **base,
            published_at=_aware(2026, 7, 5, 12),
            evidence_available_at=datetime(2026, 7, 5, 12),
        )
    with pytest.raises(kt.KnowledgeTimeError, match="availability_tz"):
        Observation(
            **base,
            published_at=date(2026, 7, 5),
            evidence_available_at=date(2026, 7, 5),
        )
    with pytest.raises(kt.KnowledgeTimeError, match="decision_tz"):
        eligible_as_of(
            [
                Observation(
                    **base,
                    published_at=_aware(2026, 7, 5, 12),
                    evidence_available_at=_aware(2026, 7, 5, 12),
                )
            ],
            date(2026, 8, 1),
            wall_clock=WALL,
        )
    with pytest.raises(kt.KnowledgeTimeError, match="economic_period_end"):
        Observation(
            **{**base, "economic_period_end": datetime(2026, 6, 30, tzinfo=UTC)},
            published_at=_aware(2026, 7, 5, 12),
            evidence_available_at=_aware(2026, 7, 5, 12),
        )


def test_future_clock_rejected():
    o = Observation(
        series_id="F",
        observation_id="fut-1",
        economic_period_end=date(2026, 6, 30),
        published_at=_aware(2026, 7, 5, 12),
        evidence_available_at=_aware(2026, 7, 5, 12),
        vintage_id="v1",
        value=1.0,
    )
    with pytest.raises(kt.KnowledgeTimeError, match="after the supplied wall clock"):
        eligible_as_of([o], _aware(2026, 9, 2), wall_clock=WALL)
    with pytest.raises(kt.KnowledgeTimeError, match="fut-1"):
        eligible_as_of(
            [o],
            _aware(2026, 7, 1),
            wall_clock=_aware(2026, 7, 1),  # before the record's own evidence
        )
    with pytest.raises(kt.KnowledgeTimeError, match="wall_clock must be an aware datetime"):
        eligible_as_of([o], _aware(2026, 6, 1), wall_clock=datetime(2026, 9, 1))


def test_partial_coverage_reports_missing_required_never_zero():
    a = Observation(
        series_id="A",
        observation_id="a-1",
        economic_period_end=date(2026, 6, 30),
        published_at=_aware(2026, 7, 5, 12),
        evidence_available_at=_aware(2026, 7, 5, 12),
        vintage_id="v1",
        value=3.0,
    )
    res = eligible_as_of(
        [a], _aware(2026, 8, 1), wall_clock=WALL, required_series=("A", "B", "C")
    )
    assert res.missing_required == ("B", "C")
    assert res.null_value_required == ()
    assert res.coverage_complete is False
    assert [r.series_id for r in res.rows] == ["A"]  # no invented rows for B/C


def test_missing_required_component_value_is_null_not_zero():
    a = Observation(
        series_id="A",
        observation_id="a-null",
        economic_period_end=date(2026, 6, 30),
        published_at=_aware(2026, 7, 5, 12),
        evidence_available_at=_aware(2026, 7, 5, 12),
        vintage_id="v1",
        value=None,
    )
    res = eligible_as_of([a], _aware(2026, 8, 1), wall_clock=WALL, required_series=("A",))
    assert res.missing_required == ()
    assert res.null_value_required == ("A",)
    assert res.coverage_complete is False
    assert res.rows[0].value is None  # never zero-filled


def test_latest_by_series_picks_max_period():
    a_may = Observation(
        series_id="A",
        observation_id="a-may",
        economic_period_end=date(2026, 5, 31),
        published_at=_aware(2026, 6, 5, 12),
        evidence_available_at=_aware(2026, 6, 5, 12),
        vintage_id="v1",
        value=1.0,
    )
    a_jun = Observation(
        series_id="A",
        observation_id="a-jun",
        economic_period_end=date(2026, 6, 30),
        published_at=_aware(2026, 7, 5, 12),
        evidence_available_at=_aware(2026, 7, 5, 12),
        vintage_id="v2",
        value=2.0,
    )
    b_jun = Observation(
        series_id="B",
        observation_id="b-jun",
        economic_period_end=date(2026, 6, 30),
        published_at=_aware(2026, 7, 5, 12),
        evidence_available_at=_aware(2026, 7, 5, 12),
        vintage_id="v1",
        value=7.0,
    )
    res = eligible_as_of([a_may, a_jun, b_jun], _aware(2026, 8, 1), wall_clock=WALL)
    latest = latest_by_series(res)
    assert set(latest) == {"A", "B"}
    assert latest["A"].observation_id == "a-jun"
    assert latest["A"].economic_period_end == date(2026, 6, 30)
    assert latest["B"].observation_id == "b-jun"


def test_module_never_reads_the_system_clock():
    source = Path(kt.__file__).read_text()
    for banned in ("now(", "utcnow", "today(", "time.time"):
        assert banned not in source, f"banned clock access pattern found: {banned!r}"
    assert kt.VALIDATED is False
    assert kt.CLAIM_LEVEL == "knowledge_time_law_display_tier"
    # cutoff_utc is a pure function of its arguments.
    assert cutoff_utc(date(2026, 8, 5), "Asia/Tokyo") == _aware(2026, 8, 4, 15)


@pytest.mark.parametrize(
    "bad",
    [float("nan"), float("inf"), float("-inf"), Decimal("NaN"), Decimal("Infinity")],
)
def test_non_finite_required_component_value_is_null_not_present(bad):
    # Seat finding S7: a NaN/inf component is null coverage, never "present".
    a = Observation(
        series_id="A",
        observation_id="a-nonfinite",
        economic_period_end=date(2026, 6, 30),
        published_at=_aware(2026, 7, 5, 12),
        evidence_available_at=_aware(2026, 7, 5, 12),
        vintage_id="v1",
        value=bad,
    )
    res = eligible_as_of([a], _aware(2026, 8, 1), wall_clock=WALL, required_series=("A",))
    assert res.missing_required == ()
    assert res.null_value_required == ("A",)
    assert res.coverage_complete is False
