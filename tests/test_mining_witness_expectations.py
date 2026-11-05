"""Wave 10 build W10-2: publish the copper estimate-vs-actual row through the
composer's existing mev path (engine/market_ontology/mining_theme_research.py:906-955)
from synthetic witness facts.

A two-row synthetic FCX exhibit holding both
``management_issued_copper_sales_estimate`` (earlier point estimate) and
``consolidated_copper_sales`` (later actual) is mapped to a single
``kind: management_estimate_vs_actual`` / ``pair: "sales"`` packet by
``tests.mining_casebook.expectations_packets_from_event_facts`` and submitted to
the composer. The first row of ``expectations`` carries
``comparison_kind == "earlier_point_estimate_vs_later_actual"`` and
``comparison == "above_estimate"`` / ``"below_estimate"`` (or withheld on equal
values). No ``omitted:expectations`` is minted on the polarised rows.

The mapper is structural only: it does not police value polarity, value
equality, missing definition fields or per-pair domain rules. The composer is
responsible for the equal-values withhold, the ``definition_unqualified:*``
mints, the unit / perimeter / basis presence check and the comparable-fields
check. This build does not edit ``engine/``; the comparator at
``mining_theme_research.py:868-873`` is the existing composer rule.
"""

from __future__ import annotations

from dataclasses import replace as _replace

import pytest

from engine.market_ontology import mining_theme_research as composition
from tests.mining_casebook import (
    expectations_packets_from_event_facts,
    synthetic_case,
)


_PERIOD = "Quarter ended 2026-06-30"
_UNIT = "million_recoverable_pounds"
_BASIS = "consolidated"
_PERIMETER = "consolidated"
_SUBJECT = "0000000421"


def _estimate_fact_row(*, value: float) -> dict:
    """A synthetic ``event_fact.v1`` row for the management sales estimate."""
    return {
        "schema": "event_fact.v1",
        "fact_id": "fact-w10-2-estimate-%d" % int(value * 100),
        "event_id": "evt-w10-2",
        "metric": "management_issued_copper_sales_estimate",
        "value": value,
        "unit": _UNIT,
        "period": _PERIOD,
        "basis": _BASIS,
    }


def _actual_fact_row(*, value: float) -> dict:
    """A synthetic ``event_fact.v1`` row for the consolidated actual sales."""
    return {
        "schema": "event_fact.v1",
        "fact_id": "fact-w10-2-actual-%d" % int(value * 100),
        "event_id": "evt-w10-2",
        "metric": "consolidated_copper_sales",
        "value": value,
        "unit": _UNIT,
        "period": _PERIOD,
        "basis": _BASIS,
    }


def _compose_with_rows(rows):
    """Bind a copper query + bundle whose only ``financial_packets`` are the
    mev packets derived from ``rows`` by the new mapper.
    """
    packets = expectations_packets_from_event_facts(
        rows, stable_subject_id=_SUBJECT, perimeter=_PERIMETER
    )
    case = synthetic_case("copper_complete")
    bundle = _replace(case.bundle, financial_packets=packets)
    return composition.compose_mining_research(case.query, bundle), packets


def test_sales_actual_above_estimate_publishes_the_row():
    """A two-row synthetic exhibit (estimate=100, actual=111, same
    unit / basis / period as T04b) maps to one mev packet and composes to a
    one-row ``expectations`` list with ``comparison == "above_estimate"`` and
    both leg values preserved. ``omitted:expectations`` is absent.
    """
    rows = [_estimate_fact_row(value=100), _actual_fact_row(value=111)]
    result, packets = _compose_with_rows(rows)
    assert len(packets) == 1
    assert packets[0]["kind"] == "management_estimate_vs_actual"
    assert packets[0]["pair"] == "sales"
    assert len(result["expectations"]) == 1, result["expectations"]
    row = result["expectations"][0]
    assert row["comparison_kind"] == "earlier_point_estimate_vs_later_actual"
    assert row["comparison"] == "above_estimate"
    assert row["earlier_point_estimate"]["value"] == 100
    assert row["later_actual"]["value"] == 111
    assert "omitted:expectations" not in result["limitations"]
    composition.validate_mining_research(result)


def test_sales_actual_below_estimate_publishes_the_row():
    """Reversed values (estimate=100, actual=89): the same mapper produces one
    packet; the composer publishes ``comparison == "below_estimate"``.
    """
    rows = [_estimate_fact_row(value=100), _actual_fact_row(value=89)]
    result, _ = _compose_with_rows(rows)
    assert len(result["expectations"]) == 1
    row = result["expectations"][0]
    assert row["comparison_kind"] == "earlier_point_estimate_vs_later_actual"
    assert row["comparison"] == "below_estimate"
    assert row["earlier_point_estimate"]["value"] == 100
    assert row["later_actual"]["value"] == 89
    assert "omitted:expectations" not in result["limitations"]
    composition.validate_mining_research(result)


def test_equal_estimate_and_actual_withholds():
    """Equal values: the mapper still emits one packet; the composer's
    equal-values withhold (mining_theme_research.py:868-873) suppresses the
    row and mints ``omitted:expectations``. This is the existing composer
    rule, not a new vocabulary word.
    """
    rows = [_estimate_fact_row(value=100), _actual_fact_row(value=100)]
    result, packets = _compose_with_rows(rows)
    assert len(packets) == 1  # the mapper does not police polarity
    assert result["expectations"] == []
    assert "omitted:expectations" in result["limitations"]
    composition.validate_mining_research(result)


def test_mismatched_periods_withhold():
    """W15-B mC pin: the mapper carries each leg's OWN row period, so a
    mismatched pair reaches the composer's COMPARABILITY_FIELDS check and the
    row withholds with ``omitted:expectations``. Mutant mC forced the estimate
    leg's period to the actual's, silencing that check and publishing a
    fabricated cross-period comparison.
    """
    rows = [
        {**_estimate_fact_row(value=100), "period": "Quarter ended 2026-03-31"},
        _actual_fact_row(value=111),
    ]
    result, packets = _compose_with_rows(rows)
    assert len(packets) == 1
    assert (
        packets[0]["earlier_point_estimate"]["period"] == "Quarter ended 2026-03-31"
    )
    assert result["expectations"] == []
    assert "omitted:expectations" in result["limitations"]
    composition.validate_mining_research(result)


@pytest.mark.parametrize("perimeter", ["", "   "])
def test_empty_or_whitespace_perimeter_raises(perimeter):
    """W15-B mD pin: an empty or whitespace-only caller perimeter raises
    ValueError at the mapper gate before any packet is built. Mutant mD
    deleted that gate, letting an unqualified perimeter flow into both legs.
    """
    rows = [_estimate_fact_row(value=100), _actual_fact_row(value=111)]
    with pytest.raises(ValueError, match="perimeter is required"):
        expectations_packets_from_event_facts(
            rows, stable_subject_id=_SUBJECT, perimeter=perimeter
        )


def test_typed_absence_row_with_value_is_skipped():
    """W15-B mE pin: a row carrying ``typed_absence`` is skipped even when it
    also carries a ``value`` -- the estimate leg never pairs, the mapper
    returns zero packets, and the composer withholds with
    ``omitted:expectations``. Mutant mE dropped the typed-absence half of the
    gate and let the disqualified row emit a packet.
    """
    rows = [
        {**_estimate_fact_row(value=100), "typed_absence": "not_disclosed"},
        _actual_fact_row(value=111),
    ]
    packets = expectations_packets_from_event_facts(
        rows, stable_subject_id=_SUBJECT, perimeter=_PERIMETER
    )
    assert packets == ()
    result, _ = _compose_with_rows(rows)
    assert result["expectations"] == []
    assert "omitted:expectations" in result["limitations"]


def test_missing_period_raises_in_mapper():
    """W15-B item 4 (fail-open guard): at HEAD a pair of rows without
    ``period`` mapped to blank-period legs and the composer still published
    ``above_estimate`` with no limitation. The guard mirrors the sibling
    mapper's gate: a paired row whose period is not a non-blank string
    raises before any packet exists.
    """
    rows = [
        {k: v for k, v in _estimate_fact_row(value=100).items() if k != "period"},
        {k: v for k, v in _actual_fact_row(value=111).items() if k != "period"},
    ]
    with pytest.raises(ValueError, match="event_fact.v1 period must be carried"):
        expectations_packets_from_event_facts(
            rows, stable_subject_id=_SUBJECT, perimeter=_PERIMETER
        )
