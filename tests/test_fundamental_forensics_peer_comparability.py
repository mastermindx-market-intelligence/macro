"""FIF C1 (A35): peer-cohort comparability controls and exact denominators.

Synthetic CohortMember/MetricObservation values only, reusing the helper
style of ``test_fundamental_forensics_peer_cohort.py``.  Covers the four
comparability exclusions (K1/U1/D1/V1), the ``anchor_unavailable`` emission
state, the per-metric denominator invariant, and the ``to_dict`` snapshot
keys — plus the builder's projection of period start/unit from the
precomputed statement trees.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
import json

import pytest

import scripts.build_fundamental_forensics as bff
from engine.fundamental_forensics.peer_cohort import (
    CohortDefinition,
    CohortMember,
    MetricObservation,
    build_cohort_table,
)
from engine.fundamental_forensics.production_datasets import ProductionDatasetError


AAPL = "ISS:US-XNAS-AAPL"
MSFT = "ISS:US-XNAS-MSFT"
NVDA = "ISS:US-XNAS-NVDA"
CAT = "ISS:US-XNAS-CAT"
SNOW = "ISS:US-XNAS-SNOW"

FY_END = date(2025, 12, 31)
METRIC = "revenue"


def _member(
    issuer_id: str,
    cik: str,
    ticker: str,
    *,
    issuer_class: str = "industrial",
    sic: str = "7370",
) -> CohortMember:
    return CohortMember(
        issuer_id=issuer_id,
        cik=cik,
        tickers=(ticker,),
        issuer_class=issuer_class,
        sic=sic,
    )


def _obs(
    value: Decimal | str | int | None,
    period_end: date | None = FY_END,
    *,
    applicable: bool = True,
    period_basis: str = "annual",
    period_start: date | None = None,
    unit: str | None = None,
    metric_version: str | None = None,
) -> MetricObservation:
    decimal_value: Decimal | None
    if value is None:
        decimal_value = None
    elif isinstance(value, Decimal):
        decimal_value = value
    else:
        decimal_value = Decimal(str(value))
    return MetricObservation(
        value=decimal_value,
        period_end=period_end,
        period_basis=period_basis,
        applicable=applicable,
        period_start=period_start,
        unit=unit,
        metric_version=metric_version,
    )


def _definition(
    members: tuple[CohortMember, ...],
    *,
    metric_ids: tuple[str, ...] = (METRIC,),
    anchor_issuer_id: str | None = None,
    alignment_mode: str = "exclude",
    period_tolerance_days: int = 45,
    min_n: int = 3,
) -> CohortDefinition:
    anchor = anchor_issuer_id if anchor_issuer_id is not None else members[0].issuer_id
    return CohortDefinition(
        cohort_id="cohort-test",
        anchor_issuer_id=anchor,
        members=members,
        metric_ids=metric_ids,
        alignment_mode=alignment_mode,
        period_tolerance_days=period_tolerance_days,
        min_n=min_n,
    )


def _assert_exact_denominator(emission) -> None:
    """A35 item 4: considered == eligible + removed, on every emission state."""
    assert emission.members_considered == emission.eligible_n + sum(
        emission.exclusion_counts.values()
    )


# ── (a) A35-D1: duration length comparability ─────────────────────────────


def test_a35_d1_excludes_mismatched_duration_and_keeps_close_period() -> None:
    members = (
        _member(CAT, "0000018230", "CAT"),
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(NVDA, "0001045810", "NVDA"),
    )
    observations = {
        # anchor: a full leap-year duration (2024-01-01 .. 2024-12-31, 365d)
        CAT: {METRIC: _obs("40", date(2024, 12, 31), period_basis="duration", period_start=date(2024, 1, 1))},
        # a fiscal quarter wearing the same end date (91d) — not comparable
        AAPL: {METRIC: _obs("100", date(2024, 12, 31), period_basis="duration", period_start=date(2024, 10, 1))},
        # one day shorter than the anchor (364d) — within the 20-day tolerance
        MSFT: {METRIC: _obs("90", date(2024, 12, 31), period_basis="duration", period_start=date(2024, 1, 2))},
        NVDA: {METRIC: _obs("80", date(2024, 12, 31), period_basis="duration", period_start=date(2024, 1, 1))},
    }
    table = build_cohort_table(
        _definition(members, anchor_issuer_id=CAT),
        observations,
    )
    d1 = [item for item in table.exclusions if item.code == "A35-D1"]
    assert len(d1) == 1
    assert d1[0].issuer_id == AAPL
    assert d1[0].metric_id == METRIC
    assert d1[0].reason == "duration_incompatible"
    emission = table.emissions[0]
    assert emission.emission_state == "ranked"
    assert {row.issuer_id for row in emission.rows} == {CAT, MSFT, NVDA}


def test_a35_d1_excludes_peer_without_period_start() -> None:
    members = (
        _member(CAT, "0000018230", "CAT"),
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(NVDA, "0001045810", "NVDA"),
    )
    observations = {
        CAT: {METRIC: _obs("40", FY_END, period_basis="duration", period_start=date(2025, 1, 1))},
        # same end, same basis, but no period_start on the member side
        AAPL: {METRIC: _obs("100", FY_END, period_basis="duration")},
        MSFT: {METRIC: _obs("90", FY_END, period_basis="duration", period_start=date(2025, 1, 1))},
        NVDA: {METRIC: _obs("80", FY_END, period_basis="duration", period_start=date(2025, 1, 2))},
    }
    table = build_cohort_table(_definition(members, anchor_issuer_id=CAT), observations)
    d1 = [item for item in table.exclusions if item.code == "A35-D1"]
    assert [item.issuer_id for item in d1] == [AAPL]
    assert d1[0].reason == "duration_incompatible"
    assert {row.issuer_id for row in table.emissions[0].rows} == {CAT, MSFT, NVDA}


def test_a35_d1_skipped_when_anchor_has_no_period_start() -> None:
    members = (
        _member(CAT, "0000018230", "CAT"),
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
    )
    observations = {
        # anchor duration without a start: D1 is skipped (legacy shape)
        CAT: {METRIC: _obs("40", FY_END, period_basis="duration")},
        AAPL: {METRIC: _obs("100", FY_END, period_basis="duration", period_start=date(2025, 10, 1))},
        MSFT: {METRIC: _obs("90", FY_END, period_basis="duration")},
    }
    table = build_cohort_table(_definition(members, anchor_issuer_id=CAT, min_n=3), observations)
    assert not [item for item in table.exclusions if item.code == "A35-D1"]
    assert table.emissions[0].emission_state == "ranked"


# ── (b) A35-K1: period basis comparability ────────────────────────────────


def test_a35_k1_excludes_instant_peer_against_duration_anchor() -> None:
    members = (
        _member(CAT, "0000018230", "CAT"),
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(NVDA, "0001045810", "NVDA"),
    )
    observations = {
        CAT: {METRIC: _obs("40", FY_END, period_basis="duration")},
        AAPL: {METRIC: _obs("100", FY_END, period_basis="instant")},
        MSFT: {METRIC: _obs("90", FY_END, period_basis="duration")},
        NVDA: {METRIC: _obs("80", FY_END, period_basis="duration")},
    }
    table = build_cohort_table(_definition(members, anchor_issuer_id=CAT), observations)
    k1 = [item for item in table.exclusions if item.code == "A35-K1"]
    assert len(k1) == 1
    assert k1[0].issuer_id == AAPL
    assert k1[0].metric_id == METRIC
    assert k1[0].reason == "period_basis_incompatible"
    assert {row.issuer_id for row in table.emissions[0].rows} == {CAT, MSFT, NVDA}


def test_a35_k1_skipped_when_anchor_basis_is_empty() -> None:
    members = (
        _member(CAT, "0000018230", "CAT"),
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
    )
    observations = {
        CAT: {METRIC: _obs("40", FY_END, period_basis="")},
        AAPL: {METRIC: _obs("100", FY_END, period_basis="duration")},
        MSFT: {METRIC: _obs("90", FY_END, period_basis="")},
    }
    table = build_cohort_table(_definition(members, anchor_issuer_id=CAT), observations)
    assert not [item for item in table.exclusions if item.code == "A35-K1"]
    assert table.emissions[0].emission_state == "ranked"


# ── (c) A35-U1: unit comparability ────────────────────────────────────────


def test_a35_u1_excludes_unit_mismatch_and_missing_member_unit() -> None:
    members = (
        _member(CAT, "0000018230", "CAT"),
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(NVDA, "0001045810", "NVDA"),
    )
    observations = {
        CAT: {METRIC: _obs("40", FY_END, unit="USD")},
        AAPL: {METRIC: _obs("100", FY_END, unit="USD/shares")},
        MSFT: {METRIC: _obs("90", FY_END)},
        NVDA: {METRIC: _obs("80", FY_END, unit="USD")},
    }
    table = build_cohort_table(_definition(members, anchor_issuer_id=CAT), observations)
    u1 = sorted(
        (item for item in table.exclusions if item.code == "A35-U1"),
        key=lambda item: item.issuer_id,
    )
    assert [item.issuer_id for item in u1] == [AAPL, MSFT]
    assert all(item.reason == "unit_incompatible" for item in u1)
    assert {row.issuer_id for row in table.emissions[0].rows} == {CAT, NVDA}


def test_a35_u1_skipped_when_anchor_unit_is_none_legacy() -> None:
    members = (
        _member(CAT, "0000018230", "CAT"),
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(NVDA, "0001045810", "NVDA"),
    )
    observations = {
        CAT: {METRIC: _obs("40", FY_END)},
        AAPL: {METRIC: _obs("100", FY_END, unit="USD/shares")},
        MSFT: {METRIC: _obs("90", FY_END, unit="USD")},
        NVDA: {METRIC: _obs("80", FY_END)},
    }
    table = build_cohort_table(_definition(members, anchor_issuer_id=CAT), observations)
    assert not [item for item in table.exclusions if item.code == "A35-U1"]
    emission = table.emissions[0]
    assert emission.emission_state == "ranked"
    assert emission.eligible_n == 4


# ── (d) A35-V1: metric version comparability ──────────────────────────────


def test_a35_v1_excludes_metric_version_mismatch() -> None:
    members = (
        _member(CAT, "0000018230", "CAT"),
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(NVDA, "0001045810", "NVDA"),
    )
    observations = {
        CAT: {METRIC: _obs("40", FY_END, metric_version="1.0.0")},
        AAPL: {METRIC: _obs("100", FY_END, metric_version="2.0.0")},
        MSFT: {METRIC: _obs("90", FY_END)},
        NVDA: {METRIC: _obs("80", FY_END, metric_version="1.0.0")},
    }
    table = build_cohort_table(_definition(members, anchor_issuer_id=CAT), observations)
    v1 = sorted(
        (item for item in table.exclusions if item.code == "A35-V1"),
        key=lambda item: item.issuer_id,
    )
    assert [item.issuer_id for item in v1] == [AAPL, MSFT]
    assert all(item.reason == "metric_version_incompatible" for item in v1)
    assert {row.issuer_id for row in table.emissions[0].rows} == {CAT, NVDA}


# ── (e) anchor_unavailable: no ranks without a usable anchor reference ────


def _good(value: str) -> MetricObservation:
    return _obs(value, FY_END, period_basis="duration", period_start=date(2025, 1, 1))


@pytest.mark.parametrize(
    "anchor_observation,anchor_code",
    [
        pytest.param(None, "A35-X1", id="observation-missing"),
        pytest.param(
            _obs("40", FY_END, applicable=False, period_basis="duration"),
            "A35-B1",
            id="not-applicable",
        ),
        pytest.param(_obs(None, FY_END, period_basis="duration"), "A35-X1", id="value-none"),
    ],
)
def test_anchor_unavailable_emits_no_ranks_and_r1_for_peers(
    anchor_observation: MetricObservation | None, anchor_code: str
) -> None:
    members = (
        _member(CAT, "0000018230", "CAT"),
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(NVDA, "0001045810", "NVDA"),
    )
    observations = {
        AAPL: {METRIC: _good("100")},
        MSFT: {METRIC: _good("90")},
        NVDA: {METRIC: _good("80")},
    }
    if anchor_observation is not None:
        observations[CAT] = {METRIC: anchor_observation}
    table = build_cohort_table(
        _definition(members, anchor_issuer_id=CAT, min_n=3),
        observations,
    )
    emission = table.emissions[0]
    assert emission.emission_state == "anchor_unavailable"
    assert emission.eligible_n == 0
    assert emission.rows == ()
    assert emission.ranks is None
    assert emission.percentiles is None
    assert emission.mean is None
    # the anchor keeps the exclusion it always had for its own observation
    anchor_exclusions = [
        item for item in table.exclusions if item.issuer_id == CAT
    ]
    assert [item.code for item in anchor_exclusions] == [anchor_code]
    # every other kept member is typed against the missing reference
    r1 = sorted(
        (item for item in table.exclusions if item.code == "A35-R1"),
        key=lambda item: item.issuer_id,
    )
    assert [item.issuer_id for item in r1] == sorted([AAPL, MSFT, NVDA])
    assert all(
        item.reason == "anchor_reference_unavailable" and item.metric_id == METRIC
        for item in r1
    )
    # denominators stay exact, and the snapshot keys stay sorted
    assert emission.members_considered == 4
    assert dict(emission.exclusion_counts) == {anchor_code: 1, "A35-R1": 3}
    assert list(emission.exclusion_counts) == sorted(emission.exclusion_counts)
    _assert_exact_denominator(emission)


# ── (f) exact denominators on every emission state ────────────────────────


def test_denominator_invariant_holds_for_ranked_below_min_n_and_unavailable() -> None:
    members = (
        _member(CAT, "0000018230", "CAT"),
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(NVDA, "0001045810", "NVDA"),
    )

    # ranked: nobody removed
    table = build_cohort_table(
        _definition(members, anchor_issuer_id=CAT),
        {
            CAT: {METRIC: _obs("40")},
            AAPL: {METRIC: _obs("100")},
            MSFT: {METRIC: _obs("90")},
            NVDA: {METRIC: _obs("80")},
        },
    )
    ranked = table.emissions[0]
    assert ranked.emission_state == "ranked"
    assert ranked.members_considered == 4
    assert dict(ranked.exclusion_counts) == {}
    assert ranked.shifted_n == 0
    _assert_exact_denominator(ranked)

    # below_min_n: one member removed for a None value
    table = build_cohort_table(
        _definition(members, anchor_issuer_id=CAT, min_n=4),
        {
            CAT: {METRIC: _obs("40")},
            AAPL: {METRIC: _obs("100")},
            MSFT: {METRIC: _obs("90")},
            NVDA: {METRIC: _obs(None)},
        },
    )
    below = table.emissions[0]
    assert below.emission_state == "below_min_n"
    assert below.members_considered == 4
    assert dict(below.exclusion_counts) == {"A35-X1": 1}
    _assert_exact_denominator(below)

    # anchor_unavailable: the anchor removal plus one R1 per remaining member
    table = build_cohort_table(
        _definition(members, anchor_issuer_id=CAT),
        {
            AAPL: {METRIC: _obs("100")},
            MSFT: {METRIC: _obs("90")},
            NVDA: {METRIC: _obs("80")},
        },
    )
    unavailable = table.emissions[0]
    assert unavailable.emission_state == "anchor_unavailable"
    assert unavailable.members_considered == 4
    assert dict(unavailable.exclusion_counts) == {"A35-X1": 1, "A35-R1": 3}
    assert unavailable.shifted_n == 0
    _assert_exact_denominator(unavailable)


def test_denominator_invariant_and_shifted_n_in_shift_labeled_mode() -> None:
    members = (
        _member(CAT, "0000018230", "CAT"),
        _member(SNOW, "0001640147", "SNOW"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(NVDA, "0001045810", "NVDA"),
    )
    snow_end = date(2025, 1, 31)
    table = build_cohort_table(
        _definition(members, anchor_issuer_id=CAT, alignment_mode="shift_labeled"),
        {
            CAT: {METRIC: _obs("40", FY_END)},
            SNOW: {METRIC: _obs("25", snow_end)},
            MSFT: {METRIC: _obs("90", FY_END)},
            NVDA: {METRIC: _obs("80", FY_END)},
        },
    )
    emission = table.emissions[0]
    assert emission.emission_state == "ranked"
    assert emission.eligible_n == 4
    # A35-P2 is a note on a kept row, never a removal: it is not counted
    assert dict(emission.exclusion_counts) == {}
    assert emission.shifted_n == 1
    assert emission.members_considered == 4
    _assert_exact_denominator(emission)
    assert any(item.code == "A35-P2" for item in table.exclusions)
    shifted_row = next(
        row for row in emission.rows if row.issuer_id == SNOW
    )
    assert shifted_row.shifted is True


# ── (g) to_dict: new denominator keys, legacy bytes unchanged ─────────────


def test_to_dict_carries_denominator_keys_and_legacy_bytes_unchanged() -> None:
    members = (
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(NVDA, "0001045810", "NVDA"),
        _member(CAT, "0000018230", "CAT"),
    )
    # all-legacy observations: only the four original constructor fields
    observations = {
        AAPL: {METRIC: MetricObservation(Decimal("100"), FY_END, "annual", True)},
        MSFT: {METRIC: MetricObservation(Decimal("90"), FY_END, "annual", True)},
        NVDA: {METRIC: MetricObservation(Decimal("80"), FY_END, "annual", True)},
        CAT: {METRIC: MetricObservation(None, FY_END, "annual", True)},
    }
    table = build_cohort_table(_definition(members, min_n=3), observations)
    emission = table.to_dict()["emissions"][0]
    assert set(emission) == {
        "metric_id",
        "emission_state",
        "eligible_n",
        "rows",
        "ranks",
        "percentiles",
        "mean",
        "members_considered",
        "exclusion_counts",
        "shifted_n",
    }
    assert emission["members_considered"] == 4
    assert emission["exclusion_counts"] == {"A35-X1": 1}
    assert emission["shifted_n"] == 0
    expected = {
        "metric_id": METRIC,
        "emission_state": "ranked",
        "eligible_n": 3,
        "rows": [
            {
                "issuer_id": AAPL,
                "metric_id": METRIC,
                "value": "100",
                "period_end": "2025-12-31",
                "period_label": "2025-12-31",
                "shifted": False,
            },
            {
                "issuer_id": MSFT,
                "metric_id": METRIC,
                "value": "90",
                "period_end": "2025-12-31",
                "period_label": "2025-12-31",
                "shifted": False,
            },
            {
                "issuer_id": NVDA,
                "metric_id": METRIC,
                "value": "80",
                "period_end": "2025-12-31",
                "period_label": "2025-12-31",
                "shifted": False,
            },
        ],
        "ranks": {AAPL: 1, MSFT: 2, NVDA: 3},
        "percentiles": {AAPL: "0.6667", MSFT: "0.3333", NVDA: "0.0000"},
        "mean": "90",
    }
    carried = {key: emission[key] for key in expected}
    assert json.dumps(carried, sort_keys=True) == json.dumps(expected, sort_keys=True)


# ── (5) builder wiring: _tree_metric_observations ─────────────────────────


class _FakeGeneration:
    """Only the one API the projection reads: statement_trees(accession)."""

    def __init__(self, trees: dict[str, dict]) -> None:
        self._trees = trees

    def statement_trees(self, accession: str) -> dict:
        try:
            return self._trees[accession]
        except KeyError:
            raise ProductionDatasetError("synthetic: accession absent") from None


def _cell(
    value: str,
    *,
    kind: str = "duration",
    start: str | None = "2026-04-01",
    end: str = "2026-06-30",
    unit: str | None = "USD",
) -> dict:
    period: dict = {"kind": kind, "end": end, "label": end}
    if start is not None:
        period["start"] = start
    cell: dict = {"period": period, "value": value, "scale": 0, "decimals": 0}
    if unit is not None:
        cell["unit"] = unit
    return cell


def _tree(rows: list[dict]) -> dict:
    return {"statements": [{"statement_type": "income_statement", "rows": rows}]}


def _row(metric_id: str, cells: list[dict]) -> dict:
    return {
        "order": 0,
        "depth": 0,
        "abstract": False,
        "standardized_metric_id": metric_id,
        "cells": cells,
    }


def test_tree_metric_observations_carries_start_unit_and_keeps_latest_end() -> None:
    metric_ids = ("revenue", "noinfo", "badstart", "nounit", "emptyunit", "nokind")
    generation = _FakeGeneration({
        "acc-1": _tree([
            _row("revenue", [_cell("101")]),
            _row("noinfo", [_cell("55", start=None)]),
            _row("badstart", [_cell("66", start="not-a-date")]),
            _row("nounit", [_cell("56", unit=None)]),
            _row("emptyunit", [_cell("77", unit="")]),
            _row("nokind", [_cell("78", kind="")]),
        ]),
        # a later period_end wins the latest-selection exactly as before
        "acc-2": _tree([
            _row("revenue", [_cell("202", start="2026-07-01", end="2026-09-30")]),
        ]),
    })
    latest = bff._tree_metric_observations(
        generation, ["acc-1", "acc-2"], metric_ids, {}, "TST"
    )
    assert latest is not None
    assert latest["revenue"].value == Decimal("202")
    assert latest["revenue"].period_end == date(2026, 9, 30)
    assert latest["revenue"].period_start == date(2026, 7, 1)
    assert latest["revenue"].unit == "USD"
    assert latest["revenue"].period_basis == "duration"
    # metric_version is never invented: without the member registry's
    # versions (``metric_versions``) every observation carries None
    assert all(obs.metric_version is None for obs in latest.values())
    # a start that is not text contributes nothing (None, never a guess)
    assert latest["noinfo"].period_start is None
    # an unparsable start skips the cell, exactly like an unparsable end
    assert "badstart" not in latest
    # A35: a cell of unknown unit or period kind is not comparable, so it
    # contributes nothing rather than slipping past the anchor's controls
    assert "nounit" not in latest
    assert "emptyunit" not in latest
    assert "nokind" not in latest
    stamped = bff._tree_metric_observations(
        generation, ["acc-1", "acc-2"], metric_ids, {}, "TST",
        metric_versions={"revenue": "1.0.0"},
    )
    assert stamped is not None
    assert stamped["revenue"].metric_version == "1.0.0"
    assert stamped["noinfo"].metric_version is None


# ── (6) same-end ties: deterministic pick, then alignment to the anchor ──────

_QUARTER = {"start": "2026-07-01", "end": "2026-09-30"}  # 91 days
_YEAR_TO_DATE = {"start": "2026-01-01", "end": "2026-09-30"}  # 272 days


@pytest.mark.parametrize("quarter_first", [True, False], ids=["quarter-first", "ytd-first"])
def test_same_end_cells_resolve_to_the_shortest_duration_in_either_order(
    quarter_first: bool,
) -> None:
    cells = [_cell("300", **_QUARTER), _cell("900", **_YEAR_TO_DATE)]
    if not quarter_first:
        cells.reverse()
    generation = _FakeGeneration({"acc-1": _tree([_row("revenue", cells)])})
    same_end: dict = {}
    latest = bff._tree_metric_observations(
        generation, ["acc-1"], ("revenue",), frozenset(), {}, same_end=same_end
    )
    assert latest is not None
    assert latest["revenue"].value == Decimal("300")
    assert latest["revenue"].period_start == date(2026, 7, 1)
    assert sorted(obs.value for obs in same_end["revenue"]) == [Decimal("300"), Decimal("900")]


def test_a_dated_cell_outranks_an_undated_one_on_the_same_end() -> None:
    generation = _FakeGeneration({
        "acc-1": _tree([_row("revenue", [_cell("1", start=None, end="2026-09-30"), _cell("2", **_QUARTER)])]),
    })
    latest = bff._tree_metric_observations(generation, ["acc-1"], ("revenue",), frozenset(), {})
    assert latest is not None
    assert latest["revenue"].value == Decimal("2")


def test_same_end_pool_is_only_recorded_for_ties_at_the_latest_end() -> None:
    generation = _FakeGeneration({
        "acc-1": _tree([
            # a tie at an earlier end is superseded by the later single cell
            _row("revenue", [
                _cell("10", start="2026-04-01", end="2026-06-30"),
                _cell("20", start="2026-01-01", end="2026-06-30"),
                _cell("30", **_QUARTER),
            ]),
            _row("cost", [_cell("5", **_QUARTER)]),
        ]),
    })
    same_end: dict = {}
    latest = bff._tree_metric_observations(
        generation, ["acc-1"], ("revenue", "cost"), frozenset(), {}, same_end=same_end
    )
    assert latest is not None
    assert latest["revenue"].value == Decimal("30")
    assert same_end == {}


def test_a_withheld_metric_carries_no_same_end_pool() -> None:
    generation = _FakeGeneration({
        "acc-1": _tree([_row("revenue", [_cell("300", **_QUARTER), _cell("900", **_YEAR_TO_DATE)])]),
        # a later income-statement refusal withholds the older cells
        "acc-2": {"statements": [{"statement_type": "income_statement", "refusal": {"code": "R"}, "rows": []}]},
    })
    same_end: dict = {}
    latest = bff._tree_metric_observations(
        generation, ["acc-1", "acc-2"], ("revenue",), frozenset(),
        {"acc-2": "2026-12-31"}, same_end=same_end,
    )
    assert latest is not None
    assert latest["revenue"].withheld is True
    assert same_end == {}


def _peer(issuer_id: str, observations: dict, same_end: dict | None = None):
    return bff._AdmittedPeer(
        member={"ticker": issuer_id, "cik10": "0000000001"},
        issuer_id=issuer_id,
        # admitted-shape invariant (A14): the owner binding agrees with the
        # contract row; the alignment helper under test never reads them.
        binding_cik="0000000001",
        binding_ticker=issuer_id,
        sic="7370",
        issuer_class="industrial",
        observations=observations,
        same_end=same_end or {},
    )


_END = date(2026, 9, 30)
_Q = _obs("300", _END, period_basis="duration", period_start=date(2026, 7, 1))
_YTD = _obs("900", _END, period_basis="duration", period_start=date(2026, 1, 1))


@pytest.mark.parametrize(
    "anchor_obs, expected",
    [
        pytest.param(_obs("1", _END, period_basis="duration", period_start=date(2026, 1, 2)), "900", id="ytd-anchor"),
        pytest.param(_obs("1", _END, period_basis="duration", period_start=date(2026, 7, 2)), "300", id="quarter-anchor"),
        pytest.param(_obs("1", _END, period_basis="duration"), "300", id="undated-anchor-keeps-default"),
    ],
)
def test_aligned_to_anchor_picks_the_closest_duration_on_the_same_end(anchor_obs, expected: str) -> None:
    peer = _peer(MSFT, {METRIC: _Q}, {METRIC: (_Q, _YTD)})
    aligned = bff._aligned_to_anchor(peer, {METRIC: anchor_obs})
    assert aligned[METRIC].value == Decimal(expected)
    # the peer's own default never changes in place
    assert peer.observations[METRIC] is _Q


def test_aligned_to_anchor_leaves_metrics_without_a_tie_or_an_anchor_cell() -> None:
    other = _obs("7", _END, period_basis="duration", period_start=date(2026, 7, 1))
    peer = _peer(MSFT, {METRIC: _Q, "cost": other}, {METRIC: (_Q, _YTD)})
    aligned = bff._aligned_to_anchor(peer, {"cost": _YTD})
    assert aligned == {METRIC: _Q, "cost": other}


def _ytd(value: str) -> MetricObservation:
    return _obs(value, _END, period_basis="duration", period_start=date(2026, 1, 1))


def test_alignment_keeps_a_year_to_date_anchor_from_excluding_a_tied_peer() -> None:
    members = (
        _member(CAT, "0000018230", "CAT"),
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(NVDA, "0001045810", "NVDA"),
    )
    anchor = _peer(CAT, {METRIC: _ytd("40")})
    tied = _peer(AAPL, {METRIC: _Q}, {METRIC: (_Q, _YTD)})
    observations = {
        CAT: anchor.observations,
        AAPL: bff._aligned_to_anchor(tied, anchor.observations),
        MSFT: {METRIC: _ytd("90")},
        NVDA: {METRIC: _ytd("80")},
    }
    table = build_cohort_table(_definition(members, anchor_issuer_id=CAT), observations)
    assert not [item for item in table.exclusions if item.code == "A35-D1"]
    rows = {row.issuer_id: row.value for row in table.emissions[0].rows}
    assert rows[AAPL] == Decimal("900")
    # without alignment the same peer's default quarter is D1-excluded
    unaligned = build_cohort_table(
        _definition(members, anchor_issuer_id=CAT), {**observations, AAPL: tied.observations}
    )
    assert [item.issuer_id for item in unaligned.exclusions if item.code == "A35-D1"] == [AAPL]
