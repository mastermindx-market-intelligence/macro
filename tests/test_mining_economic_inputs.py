"""T03 economic fact rows from the mining witness profiles.

Company-owner ``event_fact.v1`` rows only. This suite does not import
``engine.market_ontology``. Figures are synthetic.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from engine.company_intelligence.issuer_profiles import _no_guidance
from engine.company_intelligence.mining_issuer_profiles import (
    FCX_METRICS,
    fact_id_for,
    fact_is_borrowed,
    parse_mining_literal,
)
from engine.earnings_release.filing_key import FilingKey
from tests.test_mining_witness_profiles import _load, _present, _reasons, _rows

_CELL_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "mining_economic_inputs"
    / "parenthesized_cell.json"
)


def test_parenthesized_literal_is_a_negative_float() -> None:
    fixture = json.loads(_CELL_FIXTURE.read_text(encoding="utf-8"))
    assert fixture["cell"] == "(20,296)"
    assert fixture["unit"] == "usd_thousands"
    assert parse_mining_literal("(20,296)", unit="usd_thousands") == -20296.0
    assert parse_mining_literal(fixture["cell"], unit=fixture["unit"]) == -20296.0
    assert parse_mining_literal("20,296", unit="usd_thousands") == 20296.0
    profile, bound, _expected = _load("mp")
    row = _present(_rows(profile, bound, "evt-mp"))["gaap_net_loss"]
    assert row["value"] == -20296.0
    assert type(row["value"]) is float
    assert row["value"] != "(20,296)"


def test_missing_period_column_drops_one_row_with_exact_absence() -> None:
    target = "copper_unit_net_cash_cost"
    profile, bound, _expected = _load("fcx", **{target: {"drop_period": True}})
    rows = _rows(profile, bound, "evt-fcx")
    present = _present(rows)
    assert len(present) == len(FCX_METRICS) - 1
    assert target not in present
    assert _reasons(rows) == ["missing_period"]
    assert present["consolidated_copper_sales"]["value"] == 111.0


def test_unjoinable_accession_absence_is_unjoinable_filing_identity() -> None:
    profile, bound, _expected = _load("mp")
    swapped = replace(
        bound,
        revision=replace(
            bound.revision,
            filing_key=FilingKey(
                cik=bound.revision.filing_key.cik,
                accession="0000999992-26-000099",
            ),
        ),
    )
    rows = _rows(profile, swapped, "evt-mp")
    assert [row for row in rows if "value" in row] == []
    assert _reasons(rows) == ["unjoinable_filing_identity"]


def test_no_forward_figure_keeps_extract_guidance_unbound() -> None:
    from engine.company_intelligence.mining_issuer_profiles import witness_guidance_refusal

    profile, bound, _expected = _load("fcx")
    rows = _rows(profile, bound, "evt-fcx")
    present = _present(rows)
    assert present["management_issued_copper_sales_estimate"]["value"] == 400.0
    assert present["consolidated_copper_sales"]["value"] == 111.0
    assert profile.extract_guidance is _no_guidance
    assert profile.extract_guidance(segments=(), document_id="d", body_sha256="ab", event_id="e") == []
    refusal = witness_guidance_refusal(bound, rows)
    assert refusal == {"status": "unavailable", "reason": "projector_unbound"}
    rendered = repr(refusal)
    assert "midpoint" not in rendered
    assert "badge" not in rendered
    assert "beat" not in rendered
    assert "range" not in rendered

    marked_profile, marked_bound, _marked_expected = _load("fcx", **{
        "consolidated_copper_sales": {
            "extra_header": "Note",
            "extra_cell": "subsequent-quarter outlook",
        },
    })
    marked_rows = _rows(marked_profile, marked_bound, "evt-fcx")
    marked_present = _present(marked_rows)
    assert marked_present["management_issued_copper_sales_estimate"]["value"] == 400.0
    assert marked_present["consolidated_copper_sales"]["value"] == 111.0
    assert marked_profile.extract_guidance is _no_guidance
    assert witness_guidance_refusal(marked_bound, marked_rows) is None
    assert witness_guidance_refusal(bound, []) is None


def test_borrowed_fact_id_is_refused() -> None:
    profile, bound, _expected = _load("fcx")
    first = _present(_rows(profile, bound, "evt-a"))
    second = _present(_rows(profile, bound, "evt-b"))
    left = first["consolidated_copper_sales"]
    right = second["consolidated_copper_sales"]
    assert left["value"] == right["value"] == 111.0
    assert left["fact_id"] != right["fact_id"]
    assert left["fact_id"] == fact_id_for(
        event_id="evt-a",
        metric=left["metric"],
        period=left["period"],
        basis=left["basis"],
    )
    assert right["fact_id"] == fact_id_for(
        event_id="evt-b",
        metric=right["metric"],
        period=right["period"],
        basis=right["basis"],
    )
    borrowed = dict(left)
    assert fact_is_borrowed(borrowed, event_id="evt-b") is True
    assert fact_is_borrowed(borrowed, event_id="evt-a") is False
