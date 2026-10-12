"""Peer-cohort lab: eligibility, A35 codes, and rank emission."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
import json

import pytest

from engine.fundamental_forensics.peer_cohort import (
    CohortDefinition,
    CohortMember,
    HARD_MAX_TICKERS,
    MetricObservation,
    build_cohort_table,
)
from engine.fundamental_forensics.query import HARD_MAX_TICKERS as QUERY_HARD_MAX_TICKERS


AAPL = "ISS:US-XNAS-AAPL"
MSFT = "ISS:US-XNAS-MSFT"
NVDA = "ISS:US-XNAS-NVDA"
CAT = "ISS:US-XNAS-CAT"
BAC = "ISS:US-XNAS-BAC"
GOOG = "ISS:US-XNAS-GOOG"
GOOGL = "ISS:US-XNAS-GOOGL"
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


def test_hard_max_tickers_is_imported_from_query() -> None:
    assert HARD_MAX_TICKERS is QUERY_HARD_MAX_TICKERS
    assert HARD_MAX_TICKERS == 50


def test_duplicate_issuer_id_raises_entity_ids_must_be_unique() -> None:
    members = (
        _member(AAPL, "0000320193", "AAPL"),
        _member(AAPL, "0000320193", "AAPL"),
    )
    with pytest.raises(ValueError, match="^entity_ids must be unique$"):
        build_cohort_table(_definition(members), {})


def test_member_count_above_hard_max_tickers_raises() -> None:
    members = tuple(
        _member(
            f"ISS:US-XNAS-T{index:02d}",
            f"{index:010d}",
            f"T{index:02d}",
        )
        for index in range(HARD_MAX_TICKERS + 1)
    )
    with pytest.raises(ValueError, match=f"HARD_MAX_TICKERS={HARD_MAX_TICKERS}"):
        build_cohort_table(_definition(members), {})


def test_goog_googl_collapse_one_member_and_a35_i1() -> None:
    goog = CohortMember(
        issuer_id=GOOG,
        cik="0001652044",
        tickers=("GOOG",),
        issuer_class="industrial",
        sic="7370",
    )
    googl = CohortMember(
        issuer_id=GOOGL,
        cik="0001652044",
        tickers=("GOOGL",),
        issuer_class="industrial",
        sic="7370",
    )
    # GOOGL listed first; collapse still keeps the lexicographically first issuer_id.
    table = build_cohort_table(
        _definition((googl, goog), min_n=1),
        {GOOG: {METRIC: _obs("100")}},
    )
    assert table.members_n == 1
    assert table.members[0].issuer_id == GOOG
    assert table.members[0].cik == "0001652044"
    assert table.members[0].tickers == ("GOOG", "GOOGL")
    i1 = [item for item in table.exclusions if item.code == "A35-I1"]
    assert len(i1) == 1
    assert i1[0].issuer_id == GOOGL
    assert i1[0].reason == "duplicate_share_class"
    assert table.emissions[0].eligible_n == 1
    assert table.emissions[0].rows[0].issuer_id == GOOG


def test_inapplicable_metric_emits_a35_b1() -> None:
    members = (
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(BAC, "0000070858", "BAC", issuer_class="bank", sic="6021"),
    )
    observations = {
        AAPL: {"gross_margin": _obs("40")},
        MSFT: {"gross_margin": _obs("50")},
        BAC: {"gross_margin": _obs("30", applicable=False)},
    }
    table = build_cohort_table(
        _definition(members, metric_ids=("gross_margin",), min_n=2),
        observations,
    )
    b1 = [item for item in table.exclusions if item.code == "A35-B1"]
    assert len(b1) == 1
    assert b1[0].issuer_id == BAC
    assert b1[0].metric_id == "gross_margin"
    assert b1[0].reason == "metric_not_applicable"
    eligible_ids = {row.issuer_id for row in table.emissions[0].rows}
    assert BAC not in eligible_ids
    assert table.emissions[0].eligible_n == 2


def test_missing_observation_emits_a35_x1() -> None:
    members = (
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(NVDA, "0001045810", "NVDA"),
    )
    observations = {
        AAPL: {METRIC: _obs("100")},
        MSFT: {METRIC: _obs("90")},
    }
    table = build_cohort_table(_definition(members, min_n=2), observations)
    x1 = [item for item in table.exclusions if item.code == "A35-X1"]
    assert len(x1) == 1
    assert x1[0].issuer_id == NVDA
    assert x1[0].reason == "missing_peer_observation"
    assert {row.issuer_id for row in table.emissions[0].rows} == {AAPL, MSFT}


def test_none_value_emits_a35_x1() -> None:
    members = (
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(NVDA, "0001045810", "NVDA"),
    )
    observations = {
        AAPL: {METRIC: _obs("100")},
        MSFT: {METRIC: _obs("90")},
        NVDA: {METRIC: _obs(None)},
    }
    table = build_cohort_table(_definition(members, min_n=2), observations)
    x1 = [item for item in table.exclusions if item.code == "A35-X1"]
    assert len(x1) == 1
    assert x1[0].issuer_id == NVDA
    assert x1[0].reason == "missing_peer_observation"
    assert table.emissions[0].eligible_n == 2


def test_period_misaligned_exclude_mode_emits_a35_p1() -> None:
    members = (
        _member(CAT, "0000018230", "CAT"),
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(NVDA, "0001045810", "NVDA"),
    )
    snow_end = date(2025, 1, 31)
    observations = {
        CAT: {METRIC: _obs("40", FY_END)},
        AAPL: {METRIC: _obs("100", snow_end)},
        MSFT: {METRIC: _obs("90", FY_END)},
        NVDA: {METRIC: _obs("80", FY_END)},
    }
    table = build_cohort_table(
        _definition(members, anchor_issuer_id=CAT, alignment_mode="exclude"),
        observations,
    )
    p1 = [item for item in table.exclusions if item.code == "A35-P1"]
    assert len(p1) == 1
    assert p1[0].issuer_id == AAPL
    assert p1[0].reason == "period_misaligned"
    assert {row.issuer_id for row in table.emissions[0].rows} == {CAT, MSFT, NVDA}
    assert all(not row.shifted for row in table.emissions[0].rows)


def test_shift_labeled_emits_shifted_label_and_a35_p2() -> None:
    members = (
        _member(CAT, "0000018230", "CAT"),
        _member(SNOW, "0001640147", "SNOW"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(NVDA, "0001045810", "NVDA"),
    )
    snow_end = date(2025, 1, 31)
    delta = (snow_end - FY_END).days
    observations = {
        CAT: {METRIC: _obs("40", FY_END)},
        SNOW: {METRIC: _obs("25", snow_end)},
        MSFT: {METRIC: _obs("90", FY_END)},
        NVDA: {METRIC: _obs("80", FY_END)},
    }
    table = build_cohort_table(
        _definition(
            members,
            anchor_issuer_id=CAT,
            alignment_mode="shift_labeled",
        ),
        observations,
    )
    p2 = [item for item in table.exclusions if item.code == "A35-P2"]
    assert len(p2) == 1
    assert p2[0].issuer_id == SNOW
    assert p2[0].reason == "period_shifted-and-labeled"
    snow_row = next(row for row in table.emissions[0].rows if row.issuer_id == SNOW)
    assert snow_row.shifted is True
    assert snow_row.period_label == f"shifted:{delta}d"
    assert snow_row.period_label == "shifted:-334d"
    assert table.emissions[0].eligible_n == 4
    assert table.emissions[0].emission_state == "ranked"


def test_below_min_n_emits_none_rank_percentile_mean() -> None:
    members = (
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(NVDA, "0001045810", "NVDA"),
    )
    observations = {
        AAPL: {METRIC: _obs("100")},
        MSFT: {METRIC: _obs("90")},
        NVDA: {METRIC: _obs(None)},
    }
    table = build_cohort_table(_definition(members, min_n=3), observations)
    emission = table.emissions[0]
    assert emission.emission_state == "below_min_n"
    assert emission.eligible_n == 2
    assert emission.rows  # remaining members still tabulated
    assert emission.ranks is None
    assert emission.percentiles is None
    assert emission.mean is None
    assert any(item.code == "A35-X1" for item in table.exclusions)


def test_ranked_dense_ties() -> None:
    members = (
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(NVDA, "0001045810", "NVDA"),
        _member(CAT, "0000018230", "CAT"),
    )
    observations = {
        AAPL: {METRIC: _obs("100")},
        MSFT: {METRIC: _obs("90")},
        NVDA: {METRIC: _obs("90")},
        CAT: {METRIC: _obs("80")},
    }
    table = build_cohort_table(_definition(members), observations)
    emission = table.emissions[0]
    assert emission.emission_state == "ranked"
    assert emission.ranks is not None
    assert emission.ranks[AAPL] == 1
    assert emission.ranks[MSFT] == 2
    assert emission.ranks[NVDA] == 2
    assert emission.ranks[CAT] == 3


def test_percentile_strictly_below_over_eligible_n() -> None:
    members = (
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(NVDA, "0001045810", "NVDA"),
        _member(CAT, "0000018230", "CAT"),
    )
    observations = {
        AAPL: {METRIC: _obs("40")},
        MSFT: {METRIC: _obs("30")},
        NVDA: {METRIC: _obs("20")},
        CAT: {METRIC: _obs("10")},
    }
    table = build_cohort_table(_definition(members), observations)
    percentiles = table.emissions[0].percentiles
    assert percentiles is not None
    assert percentiles[CAT] == Decimal("0.0000")
    assert percentiles[NVDA] == Decimal("0.2500")
    assert percentiles[MSFT] == Decimal("0.5000")
    assert percentiles[AAPL] == Decimal("0.7500")


def test_mean_quantized_to_max_input_scale() -> None:
    members = (
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(NVDA, "0001045810", "NVDA"),
    )
    observations = {
        AAPL: {METRIC: _obs(Decimal("1.00"))},
        MSFT: {METRIC: _obs(Decimal("2.0"))},
        NVDA: {METRIC: _obs(Decimal("3.000"))},
    }
    table = build_cohort_table(_definition(members), observations)
    assert table.emissions[0].mean == Decimal("2.000")
    assert str(table.emissions[0].mean) == "2.000"


def test_to_dict_is_deterministic_json_serializable_and_sorted() -> None:
    members = (
        _member(NVDA, "0001045810", "NVDA"),
        _member(AAPL, "0000320193", "AAPL"),
        _member(MSFT, "0000789019", "MSFT"),
        _member(CAT, "0000018230", "CAT"),
    )
    observations = {
        NVDA: {"m2": _obs("8"), "m1": _obs("80")},
        AAPL: {"m2": _obs("10"), "m1": _obs("100")},
        MSFT: {"m2": _obs("9"), "m1": _obs("90")},
        CAT: {"m2": _obs("7", applicable=False), "m1": _obs(None)},
    }
    table = build_cohort_table(
        _definition(members, metric_ids=("m2", "m1"), min_n=3),
        observations,
    )
    first = table.to_dict()
    second = table.to_dict()
    assert first == second
    json.dumps(first)
    member_ids = [item["issuer_id"] for item in first["members"]]
    assert member_ids == sorted(member_ids)
    exclusion_keys = [
        (item["metric_id"], item["issuer_id"]) for item in first["exclusions"]
    ]
    assert exclusion_keys == sorted(exclusion_keys)
    emission_ids = [item["metric_id"] for item in first["emissions"]]
    assert emission_ids == sorted(emission_ids)
    for emission in first["emissions"]:
        row_keys = [
            (item["metric_id"], item["issuer_id"]) for item in emission["rows"]
        ]
        assert row_keys == sorted(row_keys)
    assert first["authority"] == {"class": "context_only", "display_only": True}
    assert first["authority"]["display_only"] is True
