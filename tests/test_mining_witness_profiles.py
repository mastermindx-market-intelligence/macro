"""Mining T02 witness profiles — synthetic filings only.

Real Freeport and MP operating figures are not fixtures. The real CIKs live
only as constants on ``mining_issuer_profiles``; this file never spells them.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from engine.company_intelligence.documents import ABSENCE_REASONS
from engine.company_intelligence.event_workspace import production_registry
from engine.company_intelligence.identity import company_id_for_cik
from engine.company_intelligence.issuer_profiles import profile_for_ticker
from engine.company_intelligence.mining_issuer_profiles import (
    ATTRIBUTION_BASES,
    FCX_CIK,
    FCX_METRICS,
    FLOW_KIND_BY_METRIC,
    FLOW_KINDS,
    MINING_PRIVATE_RIGHTS_PROFILE,
    MINING_TICKERS,
    MP_CIK,
    MP_METRICS,
    WitnessMetric,
    bind_witness_release,
    fact_is_borrowed,
    fcx_issuer,
    fcx_profile,
    fcx_sourced_identity,
    fcx_unsourced_identity,
    mining_private_registry,
    mining_profile_for_ticker,
    mp_issuer,
    mp_profile,
    mp_sourced_identity,
    mp_unsourced_identity,
    parse_mining_literal,
)
from engine.company_intelligence.qa_exchange import RIGHTS_PROFILE, RIGHTS_PROFILES
from engine.earnings_release.filing_key import FilingKey
from engine.earnings_release.receipts import ReceiptError, receipt_for_literal


PERIOD_END = "2026-06-30"
SCOPE = ("2026-04-01", PERIOD_END, "2025-04-01", "2025-06-30")
FCX_FIXTURE_CIK = "0000999991"
MP_FIXTURE_CIK = "0000999992"
FCX_ACCESSION = "0000999991-26-000001"
MP_ACCESSION = "0000999992-26-000001"
_MODULE = (
    Path(__file__).resolve().parents[1]
    / "engine"
    / "company_intelligence"
    / "mining_issuer_profiles.py"
)

# Quarter literal, half-year literal, attribution basis word. Half-year is a
# different column and must not be added to the quarter.
_FCX_CELLS = {
    "consolidated_copper_sales": ("111", "999", "consolidated"),
    "copper_unit_net_cash_cost": ("222", "223", "payable"),
    "idle_and_restoration_costs_excluded_from_unit_cost": ("10", "25", "gross"),
    "copper_production_consolidated": ("710", "710", "gross"),
    "morenci_copper_production": ("55", "56", "attributable"),
    "management_issued_copper_sales_estimate": ("400", "401", "consolidated"),
    "management_issued_copper_unit_net_cash_cost_estimate": ("500", "501", "consolidated"),
}
_MP_CELLS = {
    "materials_revenue_including_intersegment_sales": ("600", "601", "consolidated"),
    "magnetics_precursor_revenue": ("610", "611", "saleable"),
    "revenue_elimination": ("(4,200)", "(4,201)", "consolidated"),
    "consolidated_revenue": ("700", "701", "consolidated"),
    "price_protection_income": ("77", "78", "payable"),
    "gaap_net_loss": ("(20,296)", "(20,297)", "consolidated"),
    "adjusted_ebitda": ("20,296", "20,297", "consolidated"),
    "ndpr_production": ("12", "13", "gross"),
    "ndpr_sales": ("9", "8", "saleable"),
}
_FCX_EXPECTED = {
    "consolidated_copper_sales": 111.0,
    "copper_unit_net_cash_cost": 222.0,
    "idle_and_restoration_costs_excluded_from_unit_cost": 10.0,
    "copper_production_consolidated": 710.0,
    "morenci_copper_production": 55.0,
    "management_issued_copper_sales_estimate": 400.0,
    "management_issued_copper_unit_net_cash_cost_estimate": 500.0,
}
_MP_EXPECTED = {
    "materials_revenue_including_intersegment_sales": 600.0,
    "magnetics_precursor_revenue": 610.0,
    "revenue_elimination": -4200.0,
    "consolidated_revenue": 700.0,
    "price_protection_income": 77.0,
    "gaap_net_loss": -20296.0,
    "adjusted_ebitda": 20296.0,
    "ndpr_production": 12.0,
    "ndpr_sales": 9.0,
}


def _table(
    metric: WitnessMetric,
    quarter: str,
    half: str | None,
    basis: str,
    *,
    swap_headers: bool = False,
    drop_period: bool = False,
    basis_text: str | None = None,
    unit_text: str | None = None,
    extra_header: str | None = None,
    extra_cell: str | None = None,
) -> str:
    quarter_header = f"Quarter ended {PERIOD_END}"
    half_header = f"Six months ended {PERIOD_END}"
    if swap_headers:
        quarter_header, half_header = half_header, quarter_header
    shown_basis = metric and (basis if basis_text is None else basis_text)
    shown_unit = unit_text if unit_text is not None else metric.unit
    if drop_period:
        period_header = "Amount"
    else:
        period_header = quarter_header
    half_h = "" if half is None or drop_period else f"<th>{half_header}</th>"
    half_c = "" if half is None or drop_period else f"<td>{half}</td>"
    extra_h = f"<th>{extra_header}</th>" if extra_header else ""
    extra_c = f"<td>{extra_cell}</td>" if extra_cell else ""
    return (
        f"<h2>{metric.selection_label}</h2>"
        "<table><tr>"
        f"<th>Label</th><th>Basis</th><th>Unit</th><th>{period_header}</th>{half_h}{extra_h}"
        "</tr><tr>"
        f"<td>{metric.row_label}</td><td>{shown_basis}</td><td>{shown_unit}</td>"
        f"<td>{quarter}</td>{half_c}{extra_c}"
        "</tr></table>"
    )


def _html(
    metrics: tuple[WitnessMetric, ...],
    cells: dict[str, tuple[str, str, str]],
    **overrides: dict,
) -> str:
    parts = ["<html><body>"]
    for metric in metrics:
        quarter, half, basis = cells[metric.metric]
        options = dict(overrides.get(metric.metric, {}))
        quarter = options.pop("quarter", quarter)
        half = options.pop("half", half)
        basis = options.pop("basis", basis)
        if metric.metric == "morenci_copper_production" and "extra_cell" not in options:
            options = {
                **options,
                "extra_header": "Interest note",
                "extra_cell": "60 percent interest",
            }
        parts.append(_table(metric, quarter, half, basis, **options))
    parts.append("</body></html>")
    return "".join(parts)


def _bind(body: str, *, cik: str, accession: str, ticker: str):
    exhibit_url = f"https://example.invalid/synthetic/{ticker.lower()}-witness"
    if "example.invalid" not in exhibit_url or "sec.gov" in exhibit_url:
        raise AssertionError("fixture host must be example.invalid")
    return bind_witness_release(
        cik=cik,
        accession=accession,
        body=body,
        form="8-K",
        filing_date="2026-07-23",
        acceptance_datetime="2026-07-23T13:00:00Z",
        report_date=PERIOD_END,
        exhibit_url=exhibit_url,
        content_type="text/html",
    )


def _rows(profile, bound, event_id: str) -> list[dict]:
    return profile.extract_release_facts(
        bound=bound,
        document_id=f"doc-{event_id}",
        event_id=event_id,
    )


def _reasons(rows: list[dict]) -> list[str]:
    """Sorted absence-reason set. Equality, never a subset."""
    return sorted({
        row["typed_absence"]["reason"] for row in rows if "typed_absence" in row
    })


def _present(rows: list[dict]) -> dict[str, dict]:
    return {row["metric"]: row for row in rows if "value" in row}


def _load(which: str, *, synthetic: bool = True, **overrides: dict):
    if synthetic is not True:
        raise ValueError("mining witness fixtures are synthetic-only")
    if which == "fcx":
        body = _html(FCX_METRICS, _FCX_CELLS, **overrides)
        bound = _bind(body, cik=FCX_FIXTURE_CIK, accession=FCX_ACCESSION, ticker="fcx")
        profile = fcx_profile(fiscal_scope=SCOPE)
        expected = _FCX_EXPECTED
    else:
        body = _html(MP_METRICS, _MP_CELLS, **overrides)
        bound = _bind(body, cik=MP_FIXTURE_CIK, accession=MP_ACCESSION, ticker="mp")
        profile = mp_profile(fiscal_scope=SCOPE)
        expected = _MP_EXPECTED
    assert "example.invalid" in (bound.revision.exhibit_url or "")
    assert "sec.gov" not in (bound.revision.exhibit_url or "")
    return profile, bound, expected


def test_synthetic_flag_is_required_and_the_false_state_is_refused() -> None:
    profile, _bound, _expected = _load("fcx", synthetic=True)
    assert profile.ticker == "FCX"
    with pytest.raises(ValueError, match="synthetic-only"):
        _load("fcx", synthetic=False)


def test_bind_rejects_a_misbound_exhibit_before_the_binder_runs() -> None:
    """The guard must read the exhibit_url passed to bind_witness_release.

    Substituting a URL that contains sec.gov for that argument raises inside
    ``_bind`` before the binder runs. A different literal does not count.
    """
    bad = (
        "https://example.invalid/synthetic/fcx-witness"
        "?ref=https://www.sec.gov/Archives/edgar/data/999991/wrong-exhibit.htm"
    )
    text = Path(__file__).read_text(encoding="utf-8")
    start = text.index("def _bind(")
    source = text[start:text.index("\n\ndef ", start)]
    passed = 'f"https://example.invalid/synthetic/{ticker.lower()}-witness"'
    assert source.count(passed) == 1
    calls: list[str] = []
    real = bind_witness_release

    def spy(**kwargs):
        calls.append(kwargs.get("exhibit_url"))
        return real(**kwargs)

    namespace = dict(_bind.__globals__)
    namespace["bind_witness_release"] = spy
    exec(source.replace(passed, repr(bad), 1), namespace)
    bound = None
    raised = None
    try:
        bound = namespace["_bind"](
            "<html><body>synthetic</body></html>",
            cik=FCX_FIXTURE_CIK,
            accession=FCX_ACCESSION,
            ticker="fcx",
        )
    except AssertionError as exc:
        raised = str(exc)
    receipt_url = None if bound is None else bound.revision.exhibit_url
    assert raised == "fixture host must be example.invalid", receipt_url
    assert calls == []


def test_identity_constants_are_ten_digit_and_not_repeated_in_this_file() -> None:
    assert MINING_TICKERS == ("FCX", "MP")
    assert len(FCX_CIK) == 10 and FCX_CIK.isdigit()
    assert len(MP_CIK) == 10 and MP_CIK.isdigit()
    assert FCX_CIK != MP_CIK
    assert FCX_CIK != FCX_FIXTURE_CIK
    assert MP_CIK != MP_FIXTURE_CIK
    text = Path(__file__).read_text(encoding="utf-8")
    assert FCX_CIK not in text
    assert MP_CIK not in text
    fcx = fcx_sourced_identity()
    mp = mp_sourced_identity()
    assert fcx.cik == FCX_CIK and fcx.ticker == "FCX"
    assert fcx.display_name == "Freeport-McMoRan"
    assert fcx.reporting_currency == "USD"
    assert fcx.company_id == company_id_for_cik(FCX_CIK)
    assert mp.cik == MP_CIK and mp.ticker == "MP"
    assert mp.display_name == "MP Materials"
    assert mp.reporting_currency == "USD"
    assert mp.company_id == company_id_for_cik(MP_CIK)


def test_unsourced_identity_fields_are_typed_absences() -> None:
    """Fiscal year-end and listing MIC have no admitted submissions receipt."""
    assert fcx_issuer() is None
    assert mp_issuer() is None
    for issuer, absences in (
        ("FCX", fcx_unsourced_identity()),
        ("MP", mp_unsourced_identity()),
    ):
        assert [item.reason for item in absences] == ["missing_source", "missing_source"]
        assert {item.subject for item in absences} == {
            f"{issuer}.fiscal_year_end_month",
            f"{issuer}.listing_mic",
        }
        for item in absences:
            assert item.reason in ABSENCE_REASONS
    source = _MODULE.read_text(encoding="utf-8")
    assert "fiscal_year_end_month=" not in source
    assert 'mic="XNYS"' not in source
    assert "mic='XNYS'" not in source
    assert len(mining_private_registry()) == 0
    assert mining_private_registry().resolve_ticker("FCX", asof=date(2026, 6, 30)) is None
    assert mining_private_registry().resolve_ticker("MP", asof=date(2026, 6, 30)) is None


def test_empty_unsourced_tuple_does_not_yield_the_identity_class(monkeypatch) -> None:
    """The else branch returned the IssuerIdentity class. An empty tuple must not."""
    import engine.company_intelligence.mining_issuer_profiles as mining

    monkeypatch.setattr(mining, "fcx_unsourced_identity", lambda: ())
    monkeypatch.setattr(mining, "mp_unsourced_identity", lambda: ())
    assert fcx_issuer() is None
    assert mp_issuer() is None
    source = _MODULE.read_text(encoding="utf-8")
    assert "type: ignore" not in source
    assert "_IDENTITY_TYPES" not in source


def test_public_discovery_does_not_enroll_mining() -> None:
    """Mutant (c): a public ``profile_for_ticker`` branch for FCX must fail here."""
    registry = production_registry()
    assert registry.resolve_ticker("FCX", asof=date(2026, 6, 30)) is None
    assert registry.resolve_ticker("MP", asof=date(2026, 6, 30)) is None
    assert profile_for_ticker("FCX") is None
    assert profile_for_ticker("MP") is None
    assert profile_for_ticker("FCX", publication="private", fiscal_scope=SCOPE) is None
    assert profile_for_ticker("MP", publication="public") is None
    assert "production_registry" not in _MODULE.read_text(encoding="utf-8")
    assert mining_profile_for_ticker("FCX", publication="public", fiscal_scope=SCOPE) is None
    assert mining_profile_for_ticker("ZZZZ", publication="private", fiscal_scope=SCOPE) is None
    with pytest.raises(ValueError, match="private mining profile requires fiscal_scope"):
        mining_profile_for_ticker("FCX", publication="private")
    with pytest.raises(ValueError, match="publication must be"):
        mining_profile_for_ticker("FCX", publication="secret", fiscal_scope=SCOPE)
    enrolled = mining_profile_for_ticker("MP", publication="private", fiscal_scope=SCOPE)
    assert enrolled is not None and enrolled.ticker == "MP"


def test_profile_requires_a_quarter_scope() -> None:
    with pytest.raises(TypeError):
        fcx_profile()
    with pytest.raises(ValueError, match="four dates"):
        mp_profile(fiscal_scope=("2026-06-30",))
    with pytest.raises(ValueError, match="quarters"):
        fcx_profile(fiscal_scope=("2026-01-01", "2026-06-30", "2025-01-01", "2025-06-30"))


def test_closed_attribution_and_flow_vocabulary() -> None:
    """MGD-13 first clause and MGD-14 kind vocabulary, as exact sets."""
    assert ATTRIBUTION_BASES == frozenset(
        {"gross", "consolidated", "attributable", "payable", "saleable"}
    )
    assert FLOW_KINDS == frozenset(
        {"production", "purchases", "inventory", "internal_transfer", "external_delivery"}
    )
    assert set(FLOW_KIND_BY_METRIC) >= {
        "consolidated_copper_sales",
        "copper_production_consolidated",
        "morenci_copper_production",
        "ndpr_production",
        "ndpr_sales",
        "revenue_elimination",
    }
    for kind in FLOW_KIND_BY_METRIC.values():
        assert kind in FLOW_KINDS
    assert FLOW_KIND_BY_METRIC["copper_production_consolidated"] == "production"
    assert FLOW_KIND_BY_METRIC["consolidated_copper_sales"] == "external_delivery"
    assert FLOW_KIND_BY_METRIC["ndpr_production"] != FLOW_KIND_BY_METRIC["ndpr_sales"]


def test_fcx_nominal_rows_match_the_oracle() -> None:
    profile, bound, expected = _load("fcx")
    rows = _rows(profile, bound, "evt-fcx")
    assert _reasons(rows) == []
    assert len(rows) == 7
    present = _present(rows)
    assert set(present) == set(expected)
    for metric, value in expected.items():
        row = present[metric]
        assert type(row["value"]) is float
        assert type(row["value"]) is not bool
        assert row["value"] == value
        assert row["value"] == row["value"]
        assert row["unit"]
        assert row["basis"] in ATTRIBUTION_BASES
        assert row["period"] == f"Quarter ended {PERIOD_END}"
        assert row["event_id"] == "evt-fcx"
        assert row["schema"] == "event_fact.v1"
        assert set(row) == {
            "schema", "fact_id", "event_id", "metric", "value", "unit", "period", "basis", "source_span",
        }
        assert row["fact_id"] != f"fact_{metric}"
        assert fact_is_borrowed(row, event_id="evt-fcx") is False
        assert fact_is_borrowed(row, event_id="evt-other") is True


def test_mp_nominal_rows_match_the_oracle() -> None:
    profile, bound, expected = _load("mp")
    rows = _rows(profile, bound, "evt-mp")
    assert _reasons(rows) == []
    assert len(rows) == 9
    present = _present(rows)
    assert set(present) == set(expected)
    for metric, value in expected.items():
        row = present[metric]
        assert type(row["value"]) is float
        assert row["value"] == value
        assert row["basis"] in ATTRIBUTION_BASES
        assert "typed_absence" not in row


def test_nominal_bases_cover_the_attribution_vocabulary() -> None:
    fcx_rows = _rows(*_load("fcx")[:2], "evt-fcx")
    mp_rows = _rows(*_load("mp")[:2], "evt-mp")
    bases = {row["basis"] for row in fcx_rows + mp_rows}
    assert bases == ATTRIBUTION_BASES


def test_attribution_not_applied_twice() -> None:
    """MGD-13: an attributable Morenci literal is not scaled by the interest note."""
    _profile, bound, _expected = _load("fcx")
    rows = _present(_rows(fcx_profile(fiscal_scope=SCOPE), bound, "evt-fcx"))
    row = rows["morenci_copper_production"]
    assert row["basis"] == "attributable"
    assert row["value"] == 55.0
    assert "ownership" not in row
    assert row["value"] != 33.0
    assert "60 percent interest" in bound.source
    assert sum(1 for item in rows.values() if item["metric"] == "morenci_copper_production") == 1


def test_production_is_not_delivery() -> None:
    """MGD-14 first clause: production and sales stay different metrics and values."""
    fcx = _present(_rows(*_load("fcx")[:2], "evt-fcx"))
    mp = _present(_rows(*_load("mp")[:2], "evt-mp"))
    assert fcx["copper_production_consolidated"]["value"] == 710.0
    assert fcx["consolidated_copper_sales"]["value"] == 111.0
    assert fcx["copper_production_consolidated"]["metric"] != fcx["consolidated_copper_sales"]["metric"]
    produced = fcx["copper_production_consolidated"]["value"]
    for metric, kind in FLOW_KIND_BY_METRIC.items():
        if kind == "external_delivery" and metric in fcx:
            assert fcx[metric]["value"] != produced
    assert mp["ndpr_production"]["value"] == 12.0
    assert mp["ndpr_sales"]["value"] == 9.0
    assert mp["ndpr_production"]["value"] != mp["ndpr_sales"]["value"]


def test_quarter_is_not_added_to_the_half_year_column() -> None:
    rows = _present(_rows(*_load("fcx")[:2], "evt-fcx"))
    assert rows["idle_and_restoration_costs_excluded_from_unit_cost"]["value"] == 10.0
    assert rows["idle_and_restoration_costs_excluded_from_unit_cost"]["value"] != 35.0


def test_price_protection_is_not_renamed_to_revenue() -> None:
    rows = _present(_rows(*_load("mp")[:2], "evt-mp"))
    assert rows["price_protection_income"]["value"] == 77.0
    assert rows["consolidated_revenue"]["value"] == 700.0
    assert rows["materials_revenue_including_intersegment_sales"]["value"] != 77.0
    assert rows["magnetics_precursor_revenue"]["value"] != 77.0


def test_parenthesized_loss_stays_negative_and_the_plain_literal_does_not() -> None:
    rows = _present(_rows(*_load("mp")[:2], "evt-mp"))
    assert rows["gaap_net_loss"]["value"] == -20296.0
    assert rows["adjusted_ebitda"]["value"] == 20296.0
    assert rows["gaap_net_loss"]["value"] == -rows["adjusted_ebitda"]["value"]
    assert rows["revenue_elimination"]["value"] == -4200.0
    assert parse_mining_literal("(20,296)", unit="usd_thousands") == -20296.0
    assert parse_mining_literal("20,296", unit="usd_thousands") == 20296.0
    assert parse_mining_literal("-8", unit="count") == -8.0
    assert parse_mining_literal("8", unit="count") == 8.0


def test_parse_rejects_bools_and_non_finite_values() -> None:
    assert parse_mining_literal(True, unit="count") is None
    assert parse_mining_literal(False, unit="count") is None
    assert parse_mining_literal("nan", unit="count") is None
    assert parse_mining_literal("inf", unit="count") is None
    assert parse_mining_literal("-inf", unit="count") is None
    assert parse_mining_literal("1e309", unit="count") is None
    assert parse_mining_literal("12", unit="") is None
    assert parse_mining_literal(12, unit="count") is None


def test_document_wide_window_refuses_and_the_cell_window_mints() -> None:
    """Mutant (a) and the cell-scoped mint. 710 is in the Q2 cell and the H1 cell."""
    _profile, bound, _expected = _load("fcx")
    with pytest.raises(ReceiptError, match="more than once"):
        receipt_for_literal(
            source=bound.source,
            source_sha256=bound.revision.source_sha256,
            search_start=0,
            search_end=len(bound.source),
            literal="710",
        )
    rows = _present(_rows(fcx_profile(fiscal_scope=SCOPE), bound, "evt-fcx"))
    row = rows["copper_production_consolidated"]
    assert row["value"] == 710.0
    cell = _quarter_cell(bound, "Consolidated copper production")
    receipt = row["source_span"]["receipt"]
    span = cell.source_span
    assert span.byte_start <= receipt["span_start_byte"] < receipt["span_end_byte"] <= span.byte_end
    replayed = bound.source.encode("utf-8")[receipt["span_start_byte"]:receipt["span_end_byte"]]
    assert b"710" in replayed


def test_swapping_the_quarter_and_half_headers_changes_the_value() -> None:
    """Mutant (b): the profile follows the header, not the column index."""
    nominal = _present(_rows(*_load("fcx")[:2], "evt-fcx"))
    swapped_profile, swapped_bound, _expected = _load("fcx", **{
        metric.metric: {"swap_headers": True} for metric in FCX_METRICS
    })
    swapped = _present(_rows(swapped_profile, swapped_bound, "evt-fcx"))
    assert nominal["consolidated_copper_sales"]["value"] == 111.0
    assert swapped["consolidated_copper_sales"]["value"] == 999.0
    assert swapped["consolidated_copper_sales"]["period"].lower().startswith("quarter ended")


def test_missing_period_column_absents_only_that_row() -> None:
    target = "copper_unit_net_cash_cost"
    profile, bound, expected = _load("fcx", **{target: {"drop_period": True}})
    rows = _rows(profile, bound, "evt-fcx")
    assert _reasons(rows) == ["missing_period"]
    present = _present(rows)
    assert target not in present
    assert len(present) == len(expected) - 1
    assert present["consolidated_copper_sales"]["value"] == 111.0


def test_absent_basis_and_a_word_outside_the_vocabulary() -> None:
    target = "consolidated_copper_sales"
    profile, bound, expected = _load("fcx", **{target: {"basis_text": ""}})
    rows = _rows(profile, bound, "evt-fcx")
    assert _reasons(rows) == ["missing_basis"]
    assert target not in _present(rows)
    assert len(_present(rows)) == len(expected) - 1
    outside, outside_bound, _expected = _load("fcx", **{target: {"basis_text": "reported"}})
    outside_rows = _rows(outside, outside_bound, "evt-fcx")
    assert _reasons(outside_rows) == ["missing_basis"]
    assert "reported" not in {row.get("basis") for row in outside_rows}


def test_unit_mismatch_is_missing_units() -> None:
    target = "ndpr_sales"
    profile, bound, expected = _load("mp", **{target: {"unit_text": "troy_ounce"}})
    rows = _rows(profile, bound, "evt-mp")
    assert _reasons(rows) == ["missing_units"]
    assert target not in _present(rows)
    assert len(_present(rows)) == len(expected) - 1
    assert "value" not in next(row for row in rows if row["metric"] == target)


def test_duplicate_cell_literal_is_an_absence_not_the_first_match() -> None:
    """Mutant (h): a repeated literal becomes an absence, not the first copy."""
    target = "consolidated_revenue"
    profile, bound, expected = _load("mp", **{target: {"quarter": "700 700"}})
    rows = _rows(profile, bound, "evt-mp")
    assert _reasons(rows) == ["no_span_addressable_evidence"]
    absent = next(row for row in rows if row["metric"] == target)
    assert "value" not in absent
    assert len(_present(rows)) == len(expected) - 1


def test_body_not_held_absents_every_row() -> None:
    profile = fcx_profile(fiscal_scope=SCOPE)
    rows = profile.extract_release_facts(bound=None, document_id="doc-none", event_id="evt-none")
    assert _reasons(rows) == ["document_bytes_not_held"]
    assert _present(rows) == {}
    assert len(rows) == len(FCX_METRICS)
    assert all("value" not in row for row in rows)


def test_unjoinable_accession_absents_every_row() -> None:
    """Filing identity is the pair (CIK, accession). Either half missing absents."""
    profile, bound, _expected = _load("mp")
    assert bound.document.accession == bound.revision.filing_key.accession
    mismatched = replace(
        bound,
        revision=replace(
            bound.revision,
            filing_key=FilingKey(cik=42, accession=bound.revision.filing_key.accession),
        ),
    )
    rows = _rows(profile, mismatched, "evt-mp")
    assert _reasons(rows) == ["unjoinable_filing_identity"]
    assert _present(rows) == {}
    assert all("value" not in row for row in rows)
    swapped_accession = replace(
        bound,
        revision=replace(
            bound.revision,
            filing_key=FilingKey(
                cik=bound.revision.filing_key.cik,
                accession="0000999992-26-000099",
            ),
        ),
    )
    assert swapped_accession.revision.filing_key.accession != bound.document.accession
    accession_rows = _rows(profile, swapped_accession, "evt-mp")
    assert _reasons(accession_rows) == ["unjoinable_filing_identity"]
    assert _present(accession_rows) == {}
    assert all("value" not in row for row in accession_rows)


def test_two_events_do_not_share_a_fact_id() -> None:
    """Mutant (d): ``fact_{metric}`` collides across events and must not."""
    profile, bound, _expected = _load("fcx")
    first = _present(_rows(profile, bound, "evt-a"))
    second = _present(_rows(profile, bound, "evt-b"))
    assert first["consolidated_copper_sales"]["value"] == second["consolidated_copper_sales"]["value"]
    assert first["consolidated_copper_sales"]["fact_id"] != second["consolidated_copper_sales"]["fact_id"]
    borrowed = dict(first["consolidated_copper_sales"])
    assert fact_is_borrowed(borrowed, event_id="evt-b") is True
    assert fact_is_borrowed(borrowed, event_id="evt-a") is False


def test_rights_token_is_the_registry_entry_and_not_redeclared() -> None:
    assert MINING_PRIVATE_RIGHTS_PROFILE in RIGHTS_PROFILES
    assert MINING_PRIVATE_RIGHTS_PROFILE != RIGHTS_PROFILE
    source = _MODULE.read_text(encoding="utf-8")
    assert f'"{MINING_PRIVATE_RIGHTS_PROFILE}"' not in source
    assert f"'{MINING_PRIVATE_RIGHTS_PROFILE}'" not in source
    _profile, bound, _expected = _load("fcx")
    row = _present(_rows(fcx_profile(fiscal_scope=SCOPE), bound, "evt-fcx"))["consolidated_copper_sales"]
    assert row["source_span"]["rights_profile"] == MINING_PRIVATE_RIGHTS_PROFILE


def test_limitation_words_are_not_absence_reasons() -> None:
    for word in (
        "missing_derivation",
        "interpretation_stale",
        "stream_threshold_unknown",
        "definition_unqualified",
    ):
        assert word not in ABSENCE_REASONS
    rows = _rows(*_load("fcx")[:2], "evt-fcx") + _rows(*_load("mp")[:2], "evt-mp")
    blob = repr(rows)
    assert "missing_derivation" not in blob
    assert "definition_unqualified" not in blob
    assert "beat" not in blob
    assert "miss" not in blob


def test_module_has_no_unreceipted_decimal_literal() -> None:
    text = _MODULE.read_text(encoding="utf-8")
    assert not __import__("re").search(r"\b\d+\.\d+\b", text)


def test_transcript_and_guidance_callables_return_nothing() -> None:
    profile = mp_profile(fiscal_scope=SCOPE)
    assert profile.extract_transcript_claims(segments=(), document_id="d", body_sha256="ab", event_id="e") == []
    assert profile.extract_guidance(segments=(), document_id="d", body_sha256="ab", event_id="e") == []


def _quarter_cell(bound, row_label: str):
    for block in bound.document.blocks:
        table = block.table
        if table is None or not table.rows:
            continue
        header = table.rows[0]
        quarter_at = [
            index for index, cell in enumerate(header)
            if f"Quarter ended {PERIOD_END}".casefold() in cell.text.casefold()
            and "six months" not in cell.text.casefold()
        ]
        if len(quarter_at) != 1:
            continue
        column = quarter_at[0]
        for row in table.rows[1:]:
            if any(cell.text.casefold() == row_label.casefold() for cell in row):
                return row[column]
    raise AssertionError(f"no quarter cell for {row_label}")
