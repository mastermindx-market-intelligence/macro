"""Wave 1B — an Exhibit 99.1 body bound as an event document, with receipts.

The finding this suite closes: nothing in the estate ingested a release BODY.
Releases existed only as revision metadata, and all 140 committed span receipts
in the golden corpus point at transcripts — so no surface citing a release could
be verified at all.

Two properties carry the whole wave and both are pinned here:

1. **Replayability.** Every receipt re-opens the source, re-slices the exact
   UTF-8 bytes, re-hashes them, and re-derives the figure.  The tampered fixture
   differs from the clean one by ONE digit inside the bound diluted-EPS cell,
   and the replay raises on it.
2. **Typed absence.** A number without basis, units, period, and source is
   ABSENT.  Both directions are tested: a figure that has all four binds, and a
   figure missing any one of them lands as an absence that carries no value
   field at all — so it cannot be misread as zero.
"""
from __future__ import annotations

from dataclasses import fields as dataclass_fields
import hashlib
from pathlib import Path
import re
import socket

import pytest

from engine.earnings_release import binding, figures as fig, receipts as rcp
from engine.fundamental_forensics.disclosure_diff import normalize_filing


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "earnings_release"
CLEAN = FIXTURES / "ex99_1_release.htm"
TAMPERED = FIXTURES / "ex99_1_release_tampered.htm"

CIK = 1234567
ACCESSION = "0001234567-26-000012"
AMENDMENT = "0001234567-26-000031"
REPORT_DATE = "2026-01-28"


# ─────────────────────────────────────────────────────────────────────────────
# The suite may not reach the network.
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Refuse every outbound socket for the whole module.

    ``bind_release_document`` takes the body as an argument and never fetches
    it; this fence is what makes that checkable rather than asserted.
    """

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError(
            "release-binding tests must not touch the network; the body is "
            "supplied from tests/fixtures/earnings_release/."
        )

    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)


def test_the_network_fence_actually_bites() -> None:
    with pytest.raises(AssertionError, match="must not touch the network"):
        socket.create_connection(("www.sec.gov", 443))


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def clean_body() -> str:
    return CLEAN.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def tampered_body() -> str:
    return TAMPERED.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def bound(clean_body: str) -> binding.BoundRelease:
    return binding.bind_release_document(
        cik=CIK,
        accession=ACCESSION,
        form="8-K",
        filing_date="2026-01-29",
        acceptance_datetime="2026-01-29T21:07:14.000Z",
        report_date=REPORT_DATE,
        exhibit_url=f"https://www.sec.gov/Archives/edgar/data/{CIK}/nwi-20260128xex991.htm",
        body=clean_body,
    )


# ─────────────────────────────────────────────────────────────────────────────
# The fixture is an EX-99.1 in EDGAR's own shapes, not a toy table.
# ─────────────────────────────────────────────────────────────────────────────

def test_the_fixture_carries_the_edgar_shapes_the_extractor_must_survive(
    clean_body: str,
) -> None:
    """If a shape is removed from the fixture, the guard below stops guarding."""
    assert "<TYPE>EX-99.1" in clean_body, "SGML document wrapper"
    assert 'style="display:none"' in clean_body, "hidden spacer cells"
    assert "&#160;" in clean_body, "no-break space after every figure"
    assert "width:2.18%" in clean_body, "a column width sharing a literal with a figure"
    assert re.search(r">\s*\$\s*</font>|>\$</font>", clean_body), "currency in its own cell"
    assert "(311)" in clean_body, "accounting parentheses"
    assert "Shares used in computing earnings per share" in clean_body, "the EPS scope trap"
    assert clean_body.count("<font") > 100, "font-wrapped text, no semantic tags"


def test_the_tampered_fixture_differs_by_exactly_the_bound_figure(
    clean_body: str, tampered_body: str
) -> None:
    assert clean_body != tampered_body
    assert len(clean_body) == len(tampered_body)
    differing = [
        index for index, (a, b) in enumerate(zip(clean_body, tampered_body)) if a != b
    ]
    # One digit, appearing in the headline sentence and in the EPS cell.
    assert {clean_body[i] for i in differing} == {"1"}
    assert {tampered_body[i] for i in differing} == {"7"}


# ─────────────────────────────────────────────────────────────────────────────
# GATE 3 — a release figure bound to a byte-replayable receipt.
# ─────────────────────────────────────────────────────────────────────────────

def test_the_release_body_binds_to_its_filing(bound: binding.BoundRelease) -> None:
    revision = bound.revision
    assert revision.filing_key.key == f"{CIK:010d}:{ACCESSION}"
    assert revision.report_date == REPORT_DATE
    assert revision.acceptance_datetime == "2026-01-29T21:07:14Z"
    assert revision.source_sha256 == hashlib.sha256(
        CLEAN.read_bytes()
    ).hexdigest(), "the document hash is over the supplied bytes, unmodified"
    assert revision.is_amendment is False
    assert bound.authority == "context_only"


def test_every_bound_figure_replays_byte_for_byte(
    bound: binding.BoundRelease, clean_body: str
) -> None:
    assert bound.figures.figures, "no figure bound at all"
    for figure in bound.figures.figures:
        replayed = rcp.replay_receipt(figure.receipt, source=clean_body)
        assert replayed == figure.receipt.value_text
        # And the receipt's byte span really is the figure, not a neighbouring
        # cell that happens to hash the same.
        raw = clean_body.encode("utf-8")[
            figure.receipt.byte_start:figure.receipt.byte_end
        ].decode("utf-8")
        assert rcp.visible_text(raw) == figure.receipt.value_text


def test_the_reported_revenue_receipt_points_at_the_reported_revenue(
    bound: binding.BoundRelease, clean_body: str
) -> None:
    revenue = bound.figures.figure("revenue")
    assert revenue is not None
    assert revenue.value == 8412.0
    assert revenue.receipt.value_text == "8,412"
    assert clean_body[revenue.receipt.char_start:revenue.receipt.char_end] == "8,412"
    # The slice is inside a table cell, and the surrounding source says so.
    context = clean_body[revenue.receipt.char_start - 400:revenue.receipt.char_end]
    assert "Total net sales" in context


def test_a_tampered_body_makes_the_receipt_raise(
    bound: binding.BoundRelease, tampered_body: str
) -> None:
    """The whole point of a receipt: it must fail against altered bytes."""
    eps = bound.figures.figure("eps_diluted", basis="gaap")
    assert eps is not None and eps.value == 2.18

    with pytest.raises(rcp.ReceiptReplayError, match="source_sha256 does not match"):
        rcp.replay_receipt(eps.receipt, source=tampered_body)


def test_a_receipt_whose_span_moved_raises_even_with_a_matching_source_hash(
    bound: binding.BoundRelease, clean_body: str
) -> None:
    """Refute the weaker property: a whole-document hash alone is not a receipt."""
    eps = bound.figures.figure("eps_diluted", basis="gaap")
    payload = eps.receipt.to_dict()
    payload["char_start"] += 1
    payload["byte_start"] += 1
    with pytest.raises(rcp.ReceiptReplayError):
        rcp.replay_receipt(payload, source=clean_body)


def test_a_receipt_with_a_doctored_value_raises(
    bound: binding.BoundRelease, clean_body: str
) -> None:
    eps = bound.figures.figure("eps_diluted", basis="gaap")
    payload = eps.receipt.to_dict()
    payload["value_text"] = "9.99"
    with pytest.raises(rcp.ReceiptReplayError, match="does not match the receipt"):
        rcp.replay_receipt(payload, source=clean_body)


def test_a_receipt_missing_a_field_is_refused(bound: binding.BoundRelease) -> None:
    payload = bound.figures.figures[0].receipt.to_dict()
    payload.pop("span_sha256")
    with pytest.raises(rcp.ReceiptError, match="fields mismatch"):
        rcp.SpanReceipt.from_dict(payload)


def test_a_receipt_is_replayed_before_it_is_ever_returned(clean_body: str) -> None:
    """Non-vacuity: an unreplayable receipt cannot leave the receipts module."""
    sha = hashlib.sha256(clean_body.encode("utf-8")).hexdigest()
    with pytest.raises(rcp.ReceiptError, match="does not occur"):
        rcp.receipt_for_literal(
            source=clean_body, source_sha256=sha,
            search_start=0, search_end=500, literal="8,412",
        )


def test_a_literal_occurring_twice_in_the_window_is_refused(clean_body: str) -> None:
    sha = hashlib.sha256(clean_body.encode("utf-8")).hexdigest()
    with pytest.raises(rcp.ReceiptError, match="more than once"):
        rcp.receipt_for_literal(
            source=clean_body, source_sha256=sha,
            search_start=0, search_end=len(clean_body), literal="8,412",
        )


def test_the_receipt_search_ignores_markup(clean_body: str) -> None:
    """``width:2.18%`` must not be mistaken for diluted EPS of 2.18.

    The fixture deliberately carries that column width on every table, which is
    exactly what a real Workiva-generated exhibit does.  In the column-width row
    the ONLY occurrence of ``2.18`` is inside a tag, so a masked search must
    find nothing — while an unmasked ``str.find`` would have found the style.
    """
    sha = hashlib.sha256(clean_body.encode("utf-8")).hexdigest()
    # Skip the provenance comment, which names the shape it is documenting.
    style_at = clean_body.index("width:2.18%", clean_body.index("<table"))
    row_start = clean_body.rindex("<tr>", 0, style_at)
    row_end = clean_body.index("</tr>", style_at) + len("</tr>")
    window = clean_body[row_start:row_end]

    assert "2.18" in window, "the unmasked window really does contain the literal"
    assert "2.18" not in rcp.mask_markup(window), "masking must hide tag interiors"

    with pytest.raises(rcp.ReceiptError, match="does not occur"):
        rcp.receipt_for_literal(
            source=clean_body, source_sha256=sha,
            search_start=row_start, search_end=row_end, literal="2.18",
        )


# ─────────────────────────────────────────────────────────────────────────────
# GATE 4 — basis, units, period and source travel with every number.
# ─────────────────────────────────────────────────────────────────────────────

def test_every_bound_figure_carries_basis_units_period_and_source(
    bound: binding.BoundRelease,
) -> None:
    for figure in bound.figures.figures:
        assert figure.basis in {"gaap", "non_gaap"}, figure.concept
        assert figure.units, figure.concept
        assert figure.period_label, figure.concept
        assert figure.receipt.source_sha256 == bound.revision.source_sha256
        if figure.units.startswith("usd") or figure.units == "per_share":
            assert figure.currency == "USD", figure.concept
        if figure.units == "percent":
            assert figure.currency is None, figure.concept


def test_gaap_and_non_gaap_eps_are_separate_figures_not_one(
    bound: binding.BoundRelease,
) -> None:
    """The grading axis the corpus calls ``gaap_vs_non_gaap`` (16 cases)."""
    gaap = bound.figures.figure("eps_diluted", basis="gaap")
    non_gaap = bound.figures.figure("eps_diluted", basis="non_gaap")
    assert gaap is not None and non_gaap is not None
    assert gaap.value == 2.18
    assert non_gaap.value == 2.51
    assert gaap.value != non_gaap.value, "a GAAP print compared to an adjusted one"


def test_a_per_share_figure_does_not_inherit_the_tables_millions_scale(
    bound: binding.BoundRelease,
) -> None:
    """The corpus's ``units_currency`` axis (14 cases), in its sharpest form."""
    eps = bound.figures.figure("eps_diluted", basis="gaap")
    revenue = bound.figures.figure("revenue")
    assert eps.units == "per_share" and eps.scale_factor == 1.0
    assert revenue.units == "usd_millions" and revenue.scale_factor == 1e6


def test_the_share_count_row_is_not_read_as_earnings_per_share(
    bound: binding.BoundRelease,
) -> None:
    """``Basic``/``Diluted`` appear twice; the second pair are share counts."""
    for concept in ("eps_basic", "eps_diluted"):
        for figure in bound.figures.figures:
            if figure.concept == concept:
                assert abs(figure.value) < 100, (
                    f"{concept} read a share count ({figure.value}) as a per-share amount"
                )


def test_a_percentage_row_is_a_percentage_not_a_dollar_amount(
    bound: binding.BoundRelease,
) -> None:
    pct = bound.figures.figure("gross_margin_pct")
    profit = bound.figures.figure("gross_profit")
    assert pct is not None and pct.value == 56.9 and pct.units == "percent"
    assert profit is not None and profit.units == "usd_millions"


def test_accounting_parentheses_are_read_as_negative(bound: binding.BoundRelease) -> None:
    capex = bound.figures.figure("capital_expenditures")
    assert capex is not None and capex.value == -311.0


def test_a_footnote_marker_cell_does_not_become_the_label(
    bound: binding.BoundRelease,
) -> None:
    """``(1)`` sits in its own cell before ``Net sales by reportable segment:``."""
    segments = {
        figure.concept for figure in bound.figures.figures
        if figure.concept.startswith("segment_revenue:")
    }
    assert segments == {
        "segment_revenue:life_sciences",
        "segment_revenue:industrial_metrology",
        "segment_revenue:environmental_systems",
    }


def test_the_segment_total_is_not_double_counted(bound: binding.BoundRelease) -> None:
    revenues = [f for f in bound.figures.figures if f.concept == "revenue"]
    assert len(revenues) == 1


# ─────────────────────────────────────────────────────────────────────────────
# GATE 4, the other direction — a missing requirement lands as typed absence.
# ─────────────────────────────────────────────────────────────────────────────

def test_a_guidance_range_with_no_declared_basis_is_absent_not_guessed(
    bound: binding.BoundRelease,
) -> None:
    for concept in ("guidance_revenue_low", "guidance_revenue_high"):
        absence = bound.figures.absence(concept)
        assert absence is not None, f"{concept} was guessed rather than refused"
        assert absence.reason == fig.AbsenceReason.BASIS_UNDECLARED.value
        assert bound.figures.figure(concept) is None


def test_a_guidance_range_that_declares_everything_does_bind(
    bound: binding.BoundRelease,
) -> None:
    """Both directions, from the same document: refusal is not a blanket."""
    low = bound.figures.figure("guidance_eps_low")
    high = bound.figures.figure("guidance_eps_high")
    assert low is not None and low.value == 1.94 and low.basis == "non_gaap"
    assert high is not None and high.value == 2.11
    assert "quarter" in low.period_label


def test_a_typed_absence_carries_no_value_field_at_all() -> None:
    """It must be impossible for an absence to be read as zero."""
    names = {field.name for field in dataclass_fields(fig.TypedAbsence)}
    assert names == {"concept", "reason", "detail", "label"}
    assert "value" not in names
    absence = fig.TypedAbsence(concept="revenue", reason="x", detail="y")
    assert not hasattr(absence, "value")
    assert "value" not in absence.to_dict()


def test_a_table_with_no_units_caption_yields_absences_not_numbers() -> None:
    body = """<html><body>
      <div>SUPPLEMENTAL DATA (Unaudited)</div>
      <table>
        <tr><td></td><td>December 28, 2025</td></tr>
        <tr><td>Total net sales</td><td>8,412</td></tr>
      </table></body></html>"""
    document = normalize_filing(
        {"accession": ACCESSION, "entity_cik": str(CIK), "form": "8-K", "content": body}
    )
    result = fig.extract_release_figures(document)
    assert result.figure("revenue") is None
    absence = result.absence("revenue")
    assert absence is not None
    assert absence.reason in {
        fig.AbsenceReason.UNITS_UNDECLARED.value,
        fig.AbsenceReason.BASIS_UNDECLARED.value,
    }


def test_a_table_whose_header_names_no_period_yields_a_period_absence() -> None:
    body = """<html><body>
      <div>CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS (Unaudited)</div>
      <div>(In millions)</div>
      <table>
        <tr><td>Total net sales</td><td>$</td><td>8,412</td></tr>
      </table></body></html>"""
    document = normalize_filing(
        {"accession": ACCESSION, "entity_cik": str(CIK), "form": "8-K", "content": body}
    )
    result = fig.extract_release_figures(document)
    assert result.figure("revenue") is None
    assert result.absence("revenue").reason == fig.AbsenceReason.PERIOD_UNDECLARED.value


def test_a_column_with_no_currency_anywhere_yields_a_currency_absence() -> None:
    body = """<html><body>
      <div>CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS (Unaudited)</div>
      <div>(In millions)</div>
      <table>
        <tr><td></td><td>December 28, 2025</td></tr>
        <tr><td>Total net sales</td><td>8,412</td></tr>
      </table></body></html>"""
    document = normalize_filing(
        {"accession": ACCESSION, "entity_cik": str(CIK), "form": "8-K", "content": body}
    )
    result = fig.extract_release_figures(document)
    assert result.figure("revenue") is None
    assert result.absence("revenue").reason == fig.AbsenceReason.CURRENCY_UNDECLARED.value


def test_a_concept_the_release_never_reports_is_absent_by_name() -> None:
    body = """<html><body>
      <div>CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS (Unaudited)</div>
      <div>(In millions)</div>
      <table>
        <tr><td></td><td>December 28, 2025</td></tr>
        <tr><td>Total net sales</td><td>$</td><td>8,412</td></tr>
      </table></body></html>"""
    document = normalize_filing(
        {"accession": ACCESSION, "entity_cik": str(CIK), "form": "8-K", "content": body}
    )
    result = fig.extract_release_figures(document)
    assert result.figure("revenue").value == 8412.0
    for concept in ("eps_diluted", "capital_expenditures", "operating_cash_flow"):
        assert result.absence(concept).reason == (
            fig.AbsenceReason.CONCEPT_NOT_PRESENT.value
        )


def test_no_roster_concept_is_both_bound_and_absent(bound: binding.BoundRelease) -> None:
    bound_concepts = bound.figures.concepts()
    absent_concepts = {absence.concept for absence in bound.figures.absences}
    assert not (bound_concepts & absent_concepts)


def test_two_rows_disagreeing_on_one_concept_drop_both() -> None:
    """Keeping the first would make the answer depend on document order."""
    body = """<html><body>
      <div>CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS (Unaudited)</div>
      <div>(In millions)</div>
      <table>
        <tr><td></td><td>December 28, 2025</td></tr>
        <tr><td>Total net sales</td><td>$</td><td>8,412</td></tr>
        <tr><td>Total net sales</td><td>$</td><td>8,999</td></tr>
      </table></body></html>"""
    document = normalize_filing(
        {"accession": ACCESSION, "entity_cik": str(CIK), "form": "8-K", "content": body}
    )
    result = fig.extract_release_figures(document)
    assert result.figure("revenue") is None
    assert result.absence("revenue").reason == fig.AbsenceReason.VALUE_AMBIGUOUS.value


# ─────────────────────────────────────────────────────────────────────────────
# Layouts the 40-release census proved unreadable, one class at a time.
# research/MARKETING_X_CATALYST_BINDER_CENSUS_20261101.md names the real
# releases behind each class; every body here is synthetic.
# ─────────────────────────────────────────────────────────────────────────────

_GAAP_CAPTION = "<div>CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS (Unaudited)</div>"
_UNITS = "<div>(In millions, except per share amounts)</div>"
_DATED = '<tr><td></td><td colspan="2">December 28, 2025</td></tr>'


def _extract(body: str) -> fig.ReleaseFigureSet:
    document = normalize_filing(
        {"accession": ACCESSION, "entity_cik": str(CIK), "form": "8-K", "content": body}
    )
    return fig.extract_release_figures(document)


def _statement(rows: str, *, caption: str = _GAAP_CAPTION, units: str = _UNITS) -> str:
    return f"<html><body>{caption}{units}<table>{rows}</table></body></html>"


@pytest.mark.parametrize(
    "header",
    [
        # A year row under a "Three Months Ended September 30," caption row.
        '<tr><td></td><td colspan="4">Three Months Ended September 30,</td></tr>'
        '<tr><td></td><td colspan="2">2025</td><td colspan="2">2024</td></tr>',
        # The period and its whole date in one cell.
        '<tr><td></td><td colspan="2">Three Months Ended September 30, 2025</td>'
        '<td colspan="2">Three Months Ended September 30, 2024</td></tr>',
        # A numeric date.
        '<tr><td></td><td colspan="2">9/30/2025</td><td colspan="2">9/30/2024</td></tr>',
    ],
    ids=["year-row", "date-tail", "slash-date"],
)
def test_class_a_a_dated_header_in_any_census_shape_names_the_period(header: str) -> None:
    rows = header + (
        "<tr><td>Total net sales</td><td>$</td><td>8,412</td><td>$</td><td>7,900</td></tr>"
    )
    revenue = _extract(_statement(rows)).figure("revenue")
    assert revenue is not None
    assert (revenue.value, revenue.period_end) == (8412.0, "2025-09-30")


@pytest.mark.parametrize(
    ("caption", "units"),
    [
        ("(in $ millions)", "usd_millions"),
        ("($ in millions, except per share data)", "usd_millions"),
        ("($ billions, except EPS)", "usd_billions"),
    ],
)
def test_class_b_a_dollar_led_units_caption_declares_units_and_currency(
    caption: str, units: str
) -> None:
    """The no-currency fixture above stays an absence; a "$" caption is a declaration."""
    rows = "<tr><td></td><td>December 28, 2025</td></tr><tr><td>Total net sales</td><td>8,412</td></tr>"
    revenue = _extract(_statement(rows, units=f"<div>{caption}</div>")).figure("revenue")
    assert revenue is not None
    assert (revenue.value, revenue.units, revenue.currency) == (8412.0, units, "USD")


@pytest.mark.parametrize("cell", ["$8,412", "$ 8,412"])
def test_class_c_a_currency_symbol_inside_the_value_cell_is_a_currency(cell: str) -> None:
    rows = f"{_DATED}<tr><td>Total net sales</td><td colspan=\"2\">{cell}</td></tr>"
    revenue = _extract(_statement(rows)).figure("revenue")
    assert revenue is not None
    assert (revenue.value, revenue.currency) == (8412.0, "USD")


def test_class_c_a_negative_typeset_across_two_cells_reads_as_one_value() -> None:
    rows = (
        f"{_DATED}<tr><td>Net loss per share:</td></tr>"
        "<tr><td>Diluted</td><td>$</td><td>(0.12</td><td>)</td></tr>"
    )
    eps = _extract(_statement(rows)).figure("eps_diluted")
    assert eps is not None
    assert eps.value == -0.12


@pytest.mark.parametrize(
    ("label", "cell", "concept", "value"),
    [
        ("Net operating revenues", "8,412", "revenue", 8412.0),
        ("Sales to customers", "8,412", "revenue", 8412.0),
        ("Net revenues1", "8,412", "revenue", 8412.0),
        ("Diluted EPS", "1.23", "eps_diluted", 1.23),
        ("EPS (diluted)", "1.23", "eps_diluted", 1.23),
        ("EPS - basic", "1.25", "eps_basic", 1.25),
    ],
)
def test_class_d_census_label_variants_name_their_concept(
    label: str, cell: str, concept: str, value: float
) -> None:
    rows = f"{_DATED}<tr><td>{label}</td><td>$</td><td>{cell}</td></tr>"
    figure = _extract(_statement(rows)).figure(concept)
    assert figure is not None
    assert figure.value == value


@pytest.mark.parametrize(
    "caption",
    [
        "CONSOLIDATED STATEMENTS OF EARNINGS",
        "Consolidated Earnings Information",
        "INCOME STATEMENTS (Unaudited)",
    ],
)
def test_class_e_census_statement_titles_declare_gaap(caption: str) -> None:
    rows = f"{_DATED}<tr><td>Total net sales</td><td>$</td><td>8,412</td></tr>"
    revenue = _extract(_statement(rows, caption=f"<div>{caption}</div>")).figure("revenue")
    assert revenue is not None
    assert revenue.basis == fig.Basis.GAAP.value


def test_class_e_prose_mentioning_a_basis_closes_the_section_it_follows() -> None:
    """A footnote about non-GAAP measures is where a release turns to them."""
    prose = (
        "<p>Non-GAAP results exclude the impact of certain items, which are "
        "explained in the reconciliations that follow.</p>"
    )
    rows = f"{_DATED}<tr><td>Total net sales</td><td>$</td><td>8,412</td></tr>"
    result = _extract(_statement(rows, caption=_GAAP_CAPTION + prose))
    assert result.figure("revenue") is None
    assert result.absence("revenue").reason == fig.AbsenceReason.BASIS_UNDECLARED.value


def test_class_e_a_basis_declared_inside_a_table_speaks_for_that_table_only() -> None:
    body = f"""<html><body>{_GAAP_CAPTION}{_UNITS}
      <table>{_DATED}<tr><td>Total net sales</td><td>$</td><td>8,412</td></tr></table>
      {_UNITS}
      <table><tr><td>Reconciliation of non-GAAP measures</td></tr>{_DATED}
        <tr><td>Diluted EPS</td><td>$</td><td>1.30</td></tr></table>
      {_UNITS}
      <table>{_DATED}<tr><td>Operating income</td><td>$</td><td>2,100</td></tr></table>
    </body></html>"""
    result = _extract(body)
    assert result.figure("revenue").basis == fig.Basis.GAAP.value
    assert result.figure("eps_diluted").basis == fig.Basis.NON_GAAP.value
    # Untitled after a reconciliation: unknown, never reverted to GAAP.
    assert result.figure("operating_income") is None
    assert result.absence("operating_income").reason == (
        fig.AbsenceReason.BASIS_UNDECLARED.value
    )


def test_class_e_a_title_typeset_as_a_table_governs_like_a_caption() -> None:
    """Regression guard: the base already read a table-typeset title; class E must not break it."""
    title = (
        "<table><tr><td>CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS</td></tr></table>"
    )
    rows = f"{_DATED}<tr><td>Total net sales</td><td>$</td><td>8,412</td></tr>"
    revenue = _extract(_statement(rows, caption=title)).figure("revenue")
    assert revenue is not None
    assert revenue.basis == fig.Basis.GAAP.value


def test_class_g_a_reconciliation_split_of_one_period_is_refused() -> None:
    """As reported / impact / as adjusted: no position is THE value for the period."""
    rows = (
        '<tr><td></td><td colspan="3">Three Months Ended September 30, 2025</td></tr>'
        "<tr><td></td><td>As Reported</td><td>Impact</td><td>As Adjusted</td></tr>"
        "<tr><td>Diluted EPS</td><td>$1.10</td><td>$0.20</td><td>$1.30</td></tr>"
    )
    result = _extract(_statement(rows))
    assert result.figure("eps_diluted") is None
    assert result.absence("eps_diluted").reason == fig.AbsenceReason.VALUE_AMBIGUOUS.value


def test_class_g_an_amount_and_percent_split_narrows_to_the_amount() -> None:
    rows = (
        '<tr><td></td><td colspan="2">Three Months Ended September 30, 2025</td></tr>'
        "<tr><td></td><td>Amount</td><td>% of Net Sales</td></tr>"
        "<tr><td>Total net sales</td><td>$8,412</td><td>100.0%</td></tr>"
    )
    revenue = _extract(_statement(rows)).figure("revenue")
    assert revenue is not None
    assert (revenue.value, revenue.period_end) == (8412.0, "2025-09-30")


@pytest.mark.parametrize(
    ("body", "outcome"),
    [
        ("<html><body><p>Acme reports results for the quarter.</p></body></html>",
         fig.BindingOutcome.NO_TABLES),
        (_statement(f"{_DATED}<tr><td>Employees</td><td>1,200</td></tr>"),
         fig.BindingOutcome.NO_CANDIDATE_ROWS),
        (_statement("<tr><td>Total net sales</td><td>$</td><td>8,412</td></tr>"),
         fig.BindingOutcome.NO_PERIOD_COLUMNS),
        (_statement(f"{_DATED}<tr><td>Total net sales</td><td>$</td><td>8,412</td></tr>",
                    units=""),
         fig.BindingOutcome.ALL_REFUSED),
        (_statement(f"{_DATED}<tr><td>Total net sales</td><td>$</td><td>8,412</td></tr>"),
         fig.BindingOutcome.FIGURES_BOUND),
    ],
    ids=["prose", "no-roster-row", "undated", "refused", "bound"],
)
def test_class_f_an_empty_figure_list_names_why_it_is_empty(
    body: str, outcome: fig.BindingOutcome
) -> None:
    result = _extract(body)
    assert result.outcome == outcome.value
    assert bool(result.figures) is (outcome is fig.BindingOutcome.FIGURES_BOUND)
    serialized = result.to_dict()
    assert serialized["outcome"] == outcome.value
    assert serialized["table_count"] == (0 if outcome is fig.BindingOutcome.NO_TABLES else 1)


# A Q4 release heads its statement of operations with the quarter and its
# cash-flow statement with the year, on the same period end.
_CASH_FLOW_CAPTION = "<div>CONDENSED CONSOLIDATED STATEMENTS OF CASH FLOWS (Unaudited)</div>"


def _quarter_beside_cash_flow(operations_header: str, cash_flow_header: str) -> str:
    def table(caption: str, header: str, value: str) -> str:
        return (
            f'{caption}{_UNITS}<table><tr><td></td><td colspan="2">{header}</td></tr>'
            f"<tr><td>Net income</td><td>$</td><td>{value}</td></tr></table>"
        )

    return (
        "<html><body>"
        + table(_GAAP_CAPTION, operations_header, "6,002")
        + table(_CASH_FLOW_CAPTION, cash_flow_header, "23,504")
        + "</body></html>"
    )


@pytest.mark.parametrize(
    ("operations_header", "cash_flow_header"),
    [
        ("Three Months Ended December 28, 2025", "Twelve Months Ended December 28, 2025"),
        ("13 Weeks Ended December 28, 2025", "52 Weeks Ended December 28, 2025"),
        ("Three Months Ended December 28, 2025", "52 Weeks Ended December 28, 2025"),
    ],
    ids=["months", "weeks", "mixed"],
)
def test_the_quarter_wins_over_the_year_on_one_period_end(
    operations_header: str, cash_flow_header: str
) -> None:
    result = _extract(_quarter_beside_cash_flow(operations_header, cash_flow_header))
    net_income = result.figure("net_income")
    assert net_income is not None
    assert (net_income.value, net_income.period_end) == (6002.0, "2025-12-28")


@pytest.mark.parametrize(
    ("operations_header", "cash_flow_header"),
    [
        # Neither header says how long its period runs.
        ("December 28, 2025", "December 28, 2025"),
        # Only one does: the other could be the quarter.
        ("December 28, 2025", "Twelve Months Ended December 28, 2025"),
        # Two names for one span are one span, so the readings still disagree.
        ("13 Weeks Ended December 28, 2025", "Three Months Ended December 28, 2025"),
    ],
    ids=["undeclared", "one-declared", "same-span"],
)
def test_disagreeing_readings_without_a_shorter_declared_span_are_refused(
    operations_header: str, cash_flow_header: str
) -> None:
    result = _extract(_quarter_beside_cash_flow(operations_header, cash_flow_header))
    assert result.figure("net_income") is None
    assert result.absence("net_income").reason == fig.AbsenceReason.VALUE_AMBIGUOUS.value


def test_a_quarter_count_header_declares_its_span() -> None:
    """ "Two Quarters Ended" is six months, not one quarter, so the quarter still wins."""
    result = _extract(_quarter_beside_cash_flow(
        "Three Months Ended December 28, 2025", "Two Quarters Ended December 28, 2025"
    ))
    net_income = result.figure("net_income")
    assert net_income is not None
    assert net_income.value == 6002.0


@pytest.mark.parametrize(
    ("operations_header", "cash_flow_header"),
    [
        # Two spans in one header: the column could be either.
        ("Three and Twelve Months Ended December 28, 2025",
         "Three Months Ended December 28, 2025"),
        # A year-to-date column is cumulative, whatever quarter it names.
        ("Third Quarter Year to Date Ended December 28, 2025",
         "Six Months Ended December 28, 2025"),
    ],
    ids=["two-spans", "year-to-date"],
)
def test_a_header_that_declares_no_single_span_is_never_the_longer_period(
    operations_header: str, cash_flow_header: str
) -> None:
    result = _extract(_quarter_beside_cash_flow(operations_header, cash_flow_header))
    assert result.figure("net_income") is None
    assert result.absence("net_income").reason == fig.AbsenceReason.VALUE_AMBIGUOUS.value


# ─────────────────────────────────────────────────────────────────────────────
# Live gaps (AMZN, MA, MSFT, GOOGL, KO, V) and the first review's findings.
# Every body is synthetic; the census doc names the releases by hash and URL.
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "label",
    [
        "Diluted EPS excluding special items",
        "Diluted EPS growth",
        "Diluted earnings per share excluding acquisition costs",
    ],
)
def test_an_eps_label_naming_a_different_number_is_not_eps(label: str) -> None:
    result = _extract(_statement(f"{_DATED}<tr><td>{label}</td><td>$</td><td>1.23</td></tr>"))
    assert result.figure("eps_diluted") is None
    assert result.absence("eps_diluted").reason == fig.AbsenceReason.CONCEPT_NOT_PRESENT.value


def _opening(name: str) -> str:
    """A release's first line naming ``name`` as the reporter, by exchange ticker and verb."""
    return f"{name} (NYSE: XYZ) today reported results." if name else ""


def _eps_statement(label: str, issuer: str = "") -> str:
    """One diluted EPS row, under a caption that opens with ``issuer`` when given."""
    caption = (f"<div>{issuer}</div>" if issuer else "") + _GAAP_CAPTION
    return _statement(f"{_DATED}<tr><td>{label}</td><td>$</td><td>1.23</td></tr>", caption=caption)


@pytest.mark.parametrize(
    ("issuer", "label"),
    [
        ("Acme Corporation", "Diluted earnings per share attributable to Acme common shareholders"),
        ("", "Diluted EPS (GAAP)"),
    ],
)
def test_an_eps_label_with_an_attribution_or_basis_tag_is_still_eps(issuer: str, label: str) -> None:
    eps = _extract(_eps_statement(label, _opening(issuer))).figure("eps_diluted")
    assert eps is not None
    assert eps.value == 1.23


_TWO_PERIODS = (
    '<tr><td></td><td colspan="2">December 28, 2025</td>'
    '<td colspan="2">December 29, 2024</td></tr>'
)


def test_a_row_with_more_values_than_period_columns_is_refused() -> None:
    """An unheaded leading column ("4", a note number) must not read as the quarter."""
    units = "<div>($ in millions, except per share data)</div>"
    rows = _TWO_PERIODS + "<tr><td>Total net sales</td><td>4</td><td>8,412</td><td>7,900</td></tr>"
    result = _extract(_statement(rows, units=units))
    assert result.figure("revenue") is None
    assert result.absence("revenue").reason == fig.AbsenceReason.PERIOD_UNDECLARED.value

    rows = _TWO_PERIODS + "<tr><td>Total net sales</td><td>8,412</td><td>7,900</td></tr>"
    assert _extract(_statement(rows, units=units)).figure("revenue").value == 8412.0


@pytest.mark.parametrize(
    "caption",
    [
        "ADJUSTED CONSOLIDATED STATEMENTS OF EARNINGS",
        "Consolidated Statements of Earnings, Excluding Special Items",
        "CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS (As Adjusted)",
        "CONSOLIDATED STATEMENTS OF CASH FLOWS (excluding discontinued operations)",
        "Consolidated Statements of Operations - Pro Forma",
    ],
)
def test_a_statement_title_qualified_as_adjusted_declares_no_basis(caption: str) -> None:
    """Neither the GAAP statement nor a declared non-GAAP measure: unknown basis."""
    rows = f"{_DATED}<tr><td>Total net sales</td><td>$</td><td>8,412</td></tr>"
    result = _extract(_statement(rows, caption=f"<div>{caption}</div>"))
    assert result.figure("revenue") is None
    assert result.absence("revenue").reason == fig.AbsenceReason.BASIS_UNDECLARED.value


def test_a_units_qualifier_does_not_qualify_the_statement() -> None:
    caption = "<div>Consolidated Statements of Operations (excluding per share data)</div>"
    rows = f"{_DATED}<tr><td>Total net sales</td><td>$</td><td>8,412</td></tr>"
    revenue = _extract(_statement(rows, caption=caption)).figure("revenue")
    assert revenue is not None
    assert revenue.basis == fig.Basis.GAAP.value


def test_a_parenthesized_value_after_a_currency_cell_is_negative() -> None:
    rows = f"{_DATED}<tr><td>Operating income</td><td>$</td><td>(5)</td></tr>"
    assert _extract(_statement(rows)).figure("operating_income").value == -5.0
    # "(1)" with no currency before it is still a footnote marker.
    rows = f"{_DATED}<tr><td>Total net sales</td><td>(1)</td><td>$</td><td>8,412</td></tr>"
    assert _extract(_statement(rows)).figure("revenue").value == 8412.0


def test_a_placeholder_in_the_current_period_is_a_refused_roster_row() -> None:
    """The row was read and holds no value: all_refused, not no_candidate_rows."""
    rows = _TWO_PERIODS + "<tr><td>Diluted EPS</td><td>$</td><td>—</td><td>$</td><td>1.10</td></tr>"
    result = _extract(_statement(rows))
    assert result.figure("eps_diluted") is None
    assert result.absence("eps_diluted").reason == fig.AbsenceReason.CONCEPT_NOT_PRESENT.value
    assert result.outcome == fig.BindingOutcome.ALL_REFUSED.value


def test_prose_comparing_against_gaap_is_not_a_gaap_caption() -> None:
    body = f"""<html><body>
      <div>RECONCILIATION OF GAAP TO NON-GAAP MEASURES</div>
      <div>Compared with GAAP results</div>{_UNITS}
      <table>{_DATED}<tr><td>Diluted EPS</td><td>$</td><td>1.30</td></tr></table>
    </body></html>"""
    result = _extract(body)
    assert result.figure("eps_diluted") is None
    assert result.absence("eps_diluted").reason == fig.AbsenceReason.BASIS_UNDECLARED.value


def _segments(*lines: tuple[str, str]) -> str:
    return "".join(
        f"<tr><td>{segment}</td></tr><tr><td>Net sales</td><td>$</td><td>{value}</td></tr>"
        for segment, value in lines
    )


def test_a_segment_breakdown_binds_the_line_its_segments_sum_to() -> None:
    rows = _DATED + _segments(
        ("North America", "5,000"), ("International", "3,000"), ("Consolidated", "8,000")
    )
    revenue = _extract(_statement(rows)).figure("revenue")
    assert revenue is not None
    assert revenue.value == 8000.0


@pytest.mark.parametrize(
    "body",
    [
        # Does not foot.
        _statement(_DATED + _segments(
            ("North America", "5,000"), ("International", "3,000"), ("Consolidated", "9,000")
        )),
        # Two amounts are a restatement, not a breakdown.
        _statement(_DATED + _segments(("North America", "5,000"), ("Consolidated", "8,000"))),
        # A negative line is an elimination the rule cannot tell from a component.
        _statement(_DATED + _segments(
            ("North America", "5,000"), ("International", "4,000"),
            ("Eliminations", "(1,000)"), ("Consolidated", "8,000"),
        )),
        # Amounts in two scales do not add.
        "<html><body>" + _GAAP_CAPTION + _UNITS
        + f"<table>{_DATED}{_segments(('North America', '5,000'), ('International', '3,000'))}"
        + "</table><div>(In thousands)</div>"
        + f"<table>{_DATED}{_segments(('Consolidated', '8,000'))}</table></body></html>",
    ],
    ids=["no-footing", "two-amounts", "elimination", "mixed-scale"],
)
def test_a_breakdown_that_does_not_cleanly_foot_stays_ambiguous(body: str) -> None:
    result = _extract(body)
    assert result.figure("revenue") is None
    assert result.absence("revenue").reason == fig.AbsenceReason.VALUE_AMBIGUOUS.value


def _share_classes(headline: str | None, basic: tuple[str, str], diluted: tuple[str, str],
                   *, direct: str = "") -> str:
    head = f"<tr><td>Earnings per share</td><td>$</td><td>{headline}</td></tr>" if headline else ""
    block = "".join(
        f"<tr><td>{scope}</td></tr>"
        f"<tr><td>Class A common stock</td><td>$</td><td>{class_a}</td></tr>"
        f"<tr><td>Class B-1 common stock</td><td>$</td><td>{class_b}</td></tr>"
        for scope, (class_a, class_b) in (
            ("Basic earnings per share:", basic), ("Diluted earnings per share:", diluted)
        )
    )
    return _statement(_DATED + direct + head + block)


def test_the_headline_eps_names_which_share_class_is_the_release_eps() -> None:
    result = _extract(_share_classes("3.19", ("3.19", "4.98"), ("3.19", "4.97")))
    for concept in ("eps_basic", "eps_diluted"):
        eps = result.figure(concept)
        assert eps is not None
        assert (eps.value, eps.basis) == (3.19, fig.Basis.GAAP.value)
    assert not any(f.concept.startswith("_") for f in result.figures)
    assert not any(a.concept.startswith("_") for a in result.absences)


@pytest.mark.parametrize(
    ("headline", "basic", "diluted"),
    [
        (None, ("3.19", "4.98"), ("3.19", "4.97")),     # no headline names a class
        ("3.19", ("3.19", "3.19"), ("3.19", "3.19")),   # two classes equal it
        ("3.19", ("3.19", "4.98"), ("3.18", "3.19")),   # basic and diluted disagree
    ],
    ids=["no-headline", "two-classes-match", "classes-disagree"],
)
def test_share_class_eps_without_one_matching_class_is_refused(
    headline: str | None, basic: tuple[str, str], diluted: tuple[str, str]
) -> None:
    result = _extract(_share_classes(headline, basic, diluted))
    assert result.figure("eps_diluted") is None
    assert result.absence("eps_diluted").reason == fig.AbsenceReason.VALUE_AMBIGUOUS.value
    assert not any(a.concept.startswith("_") for a in result.absences)


def test_a_direct_eps_row_wins_over_share_class_rows() -> None:
    direct = "<tr><td>Diluted EPS</td><td>$</td><td>3.10</td></tr>"
    result = _extract(_share_classes("3.19", ("3.19", "4.98"), ("3.19", "4.97"), direct=direct))
    assert result.figure("eps_diluted").value == 3.10
    assert result.figure("eps_basic").value == 3.19


def test_a_headline_eps_alone_binds_neither_basic_nor_diluted() -> None:
    result = _extract(
        _statement(f"{_DATED}<tr><td>Earnings per share</td><td>$</td><td>3.19</td></tr>")
    )
    assert result.figures == ()
    assert result.absence("eps_diluted").reason == fig.AbsenceReason.CONCEPT_NOT_PRESENT.value
    assert not any(a.concept.startswith("_") for a in result.absences)


def test_a_bare_gaap_heading_opens_a_gaap_section() -> None:
    body = f"""<html><body>
      <div>GAAP</div>{_UNITS}
      <table>{_DATED}<tr><td>Diluted EPS</td><td>$</td><td>3.19</td></tr></table>
      <div>Non-GAAP</div>{_UNITS}
      <table>{_DATED}<tr><td>Diluted EPS</td><td>$</td><td>3.17</td></tr></table>
    </body></html>"""
    result = _extract(body)
    assert result.figure("eps_diluted", basis=fig.Basis.GAAP.value).value == 3.19
    assert result.figure("eps_diluted", basis=fig.Basis.NON_GAAP.value).value == 3.17


@pytest.mark.parametrize(
    ("amount", "change", "change_cell"),
    [("USD", "YoY Change", "12%"), ("Amount", "$ Change", "$512")],
)
def test_an_amount_and_change_split_narrows_to_the_amount(
    amount: str, change: str, change_cell: str
) -> None:
    rows = (
        '<tr><td></td><td colspan="2">Three Months Ended September 30, 2025</td></tr>'
        f"<tr><td></td><td>{amount}</td><td>{change}</td></tr>"
        f"<tr><td>Total net sales</td><td>$8,412</td><td>{change_cell}</td></tr>"
    )
    revenue = _extract(_statement(rows)).figure("revenue")
    assert revenue is not None
    assert revenue.value == 8412.0


@pytest.mark.parametrize(
    "eps_row",
    ["", "<tr><td>Diluted EPS</td><td>$</td><td>—</td></tr>"],
    ids=["no-eps-row", "eps-placeholder"],
)
def test_a_release_that_states_no_eps_fails_closed_on_eps(eps_row: str) -> None:
    """The live fixes must not invent a figure the release does not state."""
    rows = f"{_DATED}<tr><td>Total net sales</td><td>$</td><td>8,412</td></tr>{eps_row}"
    result = _extract(_statement(rows))
    assert result.figure("revenue").value == 8412.0
    for concept in ("eps_basic", "eps_diluted"):
        assert result.figure(concept) is None
        assert result.absence(concept).reason == fig.AbsenceReason.CONCEPT_NOT_PRESENT.value


# ─────────────────────────────────────────────────────────────────────────────
# The second review's findings (N1-N8).
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "label",
    [
        "Diluted EPS attributable to discontinued operations",
        "Diluted earnings per share attributable to continuing operations",
        "Diluted EPS attributable to the Tax Act",
        "Diluted EPS attributable to Acme - pro forma",
        "Diluted EPS attributable to restructuring charges",
        "Diluted EPS attributable to noncontrolling interests",
        "Diluted EPS attributable to items affecting comparability",
    ],
)
def test_an_eps_attributed_to_anything_but_the_parent_is_not_eps(label: str) -> None:
    result = _extract(_statement(f"{_DATED}<tr><td>{label}</td><td>$</td><td>0.12</td></tr>"))
    assert result.figure("eps_diluted") is None
    assert result.absence("eps_diluted").reason == fig.AbsenceReason.CONCEPT_NOT_PRESENT.value


@pytest.mark.parametrize(
    ("issuer", "label"),
    [
        ("Walmart Inc.", "Diluted earnings per share attributable to Walmart"),
        ("WALMART INC.", "Diluted earnings per share attributable to Walmart"),
        ("The Coca-Cola Company", "Diluted EPS attributable to The Coca-Cola Company"),
        ("The Procter &amp; Gamble Company",
         "Diluted earnings per share attributable to Procter &amp; Gamble"),
        ("Acme Holdings, Inc.", "Diluted EPS attributable to Acme Holdings common stockholders"),
        ("Acme Holdings, Inc.", "Diluted EPS attributable to common stockholders of Acme Holdings"),
        ("Acme, Inc.", "Diluted earnings per share attributable to common stockholders of Acme, Inc."),
        ("", "Diluted EPS attributable to common stockholders"),
        ("", "Diluted EPS attributable to the Company's common stockholders"),
        ("", "Diluted EPS attributable to the Company"),
        ("", "Diluted EPS attributable to the company"),
    ],
)
def test_an_eps_attributed_to_the_parent_or_its_holders_is_eps(issuer: str, label: str) -> None:
    eps = _extract(_eps_statement(label, _opening(issuer))).figure("eps_diluted")
    assert eps is not None
    assert eps.value == 1.23


@pytest.mark.parametrize(
    ("amount", "change"),
    [("Adjusted", "Change"), ("Constant Currency", "Reported Change"),
     ("As Adjusted", "% Change")],
)
def test_a_split_whose_remaining_column_is_another_measure_is_refused(
    amount: str, change: str
) -> None:
    rows = (
        '<tr><td></td><td colspan="2">Three Months Ended September 30, 2025</td></tr>'
        f"<tr><td></td><td>{amount}</td><td>{change}</td></tr>"
        "<tr><td>Total net sales</td><td>$8,412</td><td>12%</td></tr>"
    )
    result = _extract(_statement(rows))
    assert result.figure("revenue") is None
    assert result.absence("revenue").reason == fig.AbsenceReason.VALUE_AMBIGUOUS.value


def test_a_split_that_names_its_non_gaap_amount_narrows_to_a_non_gaap_figure() -> None:
    rows = (
        '<tr><td></td><td colspan="2">Three Months Ended September 30, 2025</td></tr>'
        "<tr><td></td><td>Non-GAAP</td><td>YoY Change</td></tr>"
        "<tr><td>Total net sales</td><td>$8,412</td><td>12%</td></tr>"
    )
    revenue = _extract(_statement(rows)).figure("revenue")
    assert revenue is not None
    assert (revenue.value, revenue.basis) == (8412.0, fig.Basis.NON_GAAP.value)


def test_footing_counts_every_reading_not_every_distinct_amount() -> None:
    """1,000 + 2,000 + 2,000 is 5,000: the 3,000 segment is not the total."""
    rows = _DATED + _segments(
        ("North America", "1,000"), ("Europe", "2,000"), ("Asia", "2,000"), ("Other", "3,000")
    )
    result = _extract(_statement(rows))
    assert result.figure("revenue") is None
    assert result.absence("revenue").reason == fig.AbsenceReason.VALUE_AMBIGUOUS.value


def test_a_total_stated_twice_still_foots() -> None:
    rows = _DATED + _segments(
        ("North America", "5,000"), ("International", "3,000"),
        ("Consolidated", "8,000"), ("Total", "8,000"),
    )
    revenue = _extract(_statement(rows)).figure("revenue")
    assert revenue is not None
    assert revenue.value == 8000.0


def test_a_placeholder_beside_a_change_column_is_a_refused_roster_row() -> None:
    """The percent beside the placeholder must not hide the revenue row."""
    rows = (
        '<tr><td></td><td colspan="2">Three Months Ended September 30, 2025</td></tr>'
        "<tr><td></td><td>Amount</td><td>% Change</td></tr>"
        "<tr><td>Total net sales</td><td>—</td><td>12%</td></tr>"
    )
    result = _extract(_statement(rows))
    assert result.figure("revenue") is None
    assert result.absence("revenue").reason == fig.AbsenceReason.CONCEPT_NOT_PRESENT.value
    assert result.outcome == fig.BindingOutcome.ALL_REFUSED.value


def test_an_unclosed_parenthesis_is_a_value_whose_sign_cannot_be_read() -> None:
    rows = _TWO_PERIODS + "<tr><td>Diluted EPS</td><td>$</td><td>(0.12</td><td>$</td><td>1.10</td></tr>"
    result = _extract(_statement(rows))
    assert result.figure("eps_diluted") is None
    absence = result.absence("eps_diluted")
    assert absence.reason == fig.AbsenceReason.VALUE_AMBIGUOUS.value
    assert "parenthesis" in absence.detail
    assert result.outcome == fig.BindingOutcome.ALL_REFUSED.value


@pytest.mark.parametrize(
    "caption",
    [
        "GAAP Results: Q3 2025 vs. Q3 2024",
        "CONSOLIDATED STATEMENTS OF OPERATIONS Q4 FY25 versus Q4 FY24",
        "CONSOLIDATED STATEMENTS OF OPERATIONS</div><div>Compared with GAAP results",
    ],
    ids=["periods-vs", "periods-versus", "gaap-compared-with-gaap"],
)
def test_a_comparison_of_periods_or_of_the_same_basis_keeps_the_section(caption: str) -> None:
    rows = f"{_DATED}<tr><td>Total net sales</td><td>$</td><td>8,412</td></tr>"
    revenue = _extract(_statement(rows, caption=f"<div>{caption}</div>")).figure("revenue")
    assert revenue is not None
    assert revenue.basis == fig.Basis.GAAP.value


@pytest.mark.parametrize(
    "header",
    [
        "Fourth Quarter and Fiscal Year Ended December 28, 2025",
        "Q4 and Full Year Ended December 28, 2025",
        "Twelve Weeks and Forty Weeks Ended December 28, 2025",
        "Twenty-Six Weeks Ended December 28, 2025",
    ],
    ids=["quarter-and-year", "q4-and-full-year", "unlisted-week-count", "hyphenated-count"],
)
def test_a_header_joining_two_periods_or_an_unread_count_declares_no_span(header: str) -> None:
    result = _extract(_quarter_beside_cash_flow(header, "Twelve Months Ended December 28, 2025"))
    assert result.figure("net_income") is None
    assert result.absence("net_income").reason == fig.AbsenceReason.VALUE_AMBIGUOUS.value


def test_the_shortest_span_wins_only_when_it_is_a_quarter() -> None:
    """Six months against twelve: two cumulative columns, neither is the quarter."""
    result = _extract(_quarter_beside_cash_flow(
        "Two Quarters Ended December 28, 2025", "Twelve Months Ended December 28, 2025"
    ))
    assert result.figure("net_income") is None
    assert result.absence("net_income").reason == fig.AbsenceReason.VALUE_AMBIGUOUS.value


# ─────────────────────────────────────────────────────────────────────────────
# The delta review's findings (NF1-NF4).
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "caption",
    [
        "Core Results Compared With GAAP Results",
        "Comparable Basis versus GAAP",
        "Comparable EPS versus GAAP EPS",
        "Pro Forma Results Compared With GAAP",
        "Results Excluding Special Items Compared with GAAP",
        "Underlying results compared to GAAP",
    ],
)
def test_a_comparison_that_names_another_measure_leaves_the_section(caption: str) -> None:
    """NF1: whatever the comparison sets against GAAP is not the GAAP statement."""
    rows = f"{_DATED}<tr><td>Total net sales</td><td>$</td><td>8,412</td></tr>"
    result = _extract(_statement(rows, caption=f"{_GAAP_CAPTION}<div>{caption}</div>"))
    assert result.figure("revenue") is None
    assert result.absence("revenue").reason == fig.AbsenceReason.BASIS_UNDECLARED.value


@pytest.mark.parametrize(
    "caption",
    ["Compared with GAAP results", "Fourth Quarter 2025 compared with GAAP", "Q3 FY25 vs. GAAP"],
)
def test_a_comparison_of_only_periods_and_the_same_basis_keeps_the_gaap_section(caption: str) -> None:
    rows = f"{_DATED}<tr><td>Total net sales</td><td>$</td><td>8,412</td></tr>"
    revenue = _extract(_statement(rows, caption=f"{_GAAP_CAPTION}<div>{caption}</div>")).figure("revenue")
    assert revenue is not None
    assert revenue.basis == fig.Basis.GAAP.value


@pytest.mark.parametrize(
    "target",
    [
        "Goodwill Impairment", "Acquisition-Related Charges", "Litigation Settlement",
        "Mark-to-Market Losses", "Participating Securities", "the Merger", "Spin-Off",
        "COVID-19", "Foreign Currency", "Share Repurchases", "Net Income", "TCJA", "Core",
        "Gain on Sale", "Q3 2025", "US Tax Reform", "Class A Common Stock", "Class A",
        "Acme", "Acme Holdings", "Acme Pro-Forma", "Proforma",
    ],
)
@pytest.mark.parametrize("issuer", ["", "Walmart Inc."], ids=["no-issuer", "other-issuer"])
def test_an_eps_attributed_to_a_name_the_release_gives_no_company_is_not_eps(
    target: str, issuer: str
) -> None:
    """NF2: a capitalized attribution is the parent only when the release names a company by it."""
    result = _extract(_eps_statement(f"Diluted EPS attributable to {target}", _opening(issuer)))
    assert result.figure("eps_diluted") is None
    assert result.absence("eps_diluted").reason == fig.AbsenceReason.CONCEPT_NOT_PRESENT.value


def test_an_eps_attributed_to_the_issuer_needs_the_release_to_name_the_issuer() -> None:
    label = "Diluted earnings per share attributable to Walmart"
    assert _extract(_eps_statement(label)).figure("eps_diluted") is None
    assert _extract(_eps_statement(label, _opening("Walmart Inc."))).figure("eps_diluted").value == 1.23
    # A corporate name with no ticker or reporting verb may be an advisor, so it names no issuer.
    assert _extract(_eps_statement(label, "Walmart Inc.")).figure("eps_diluted") is None
    # Only a trailing run of the corporate name is the issuer: "Acme" is not "Acme Holdings".
    shareholders = "Diluted earnings per share attributable to Acme common shareholders"
    opening = _opening("Acme Holdings, Inc.")
    assert _extract(_eps_statement(shareholders, opening)).figure("eps_diluted") is None


@pytest.mark.parametrize(
    "caption",
    [
        "Consolidated Statements of Operations - Pro-Forma",
        "Unaudited Pro-Forma Condensed Consolidated Statements of Operations",
        "Consolidated Statements of Earnings - Comparable Basis",
        "Consolidated Statements of Earnings - Core",
        "Consolidated Statements of Operations, As Recast",
        "Consolidated Statements of Earnings - Underlying",
        "Consolidated Statements of Operations - Pro–Forma",
        "Consolidated Statements of Operations - Pro‑Forma",
    ],
)
def test_a_statement_title_qualified_as_another_basis_declares_no_basis(caption: str) -> None:
    """NF4: pro-forma, comparable, core, underlying and recast statements are not GAAP."""
    rows = f"{_DATED}<tr><td>Total net sales</td><td>$</td><td>8,412</td></tr>"
    result = _extract(_statement(rows, caption=f"<div>{caption}</div>"))
    assert result.figure("revenue") is None
    assert result.absence("revenue").reason == fig.AbsenceReason.BASIS_UNDECLARED.value


@pytest.mark.parametrize(
    "header",
    [
        "Twenty–Six Weeks Ended December 28, 2025",
        "Twenty—Six Weeks Ended December 28, 2025",
        "Twenty Six Weeks Ended December 28, 2025",
        "Thirty Nine Weeks Ended December 28, 2025",
        "Fourth Quarter &amp; Fiscal Year Ended December 28, 2025",
        "Fourth Quarter / Full Year Ended December 28, 2025",
        "Quarter &amp; Year Ended December 28, 2025",
        "Quarter Ended December 28, 2025 and Year Ended December 28, 2025",
        "Three Months Ended, and Year Ended December 28, 2025",
        "Twenty‐Six Weeks Ended December 28, 2025",
        "Twenty‑Six Weeks Ended December 28, 2025",
        "Twenty­Six Weeks Ended December 28, 2025",
        "Twenty‒Six Weeks Ended December 28, 2025",
        "Twenty−Six Weeks Ended December 28, 2025",
        "Twenty - Six Weeks Ended December 28, 2025",
        "Twenty – Six Weeks Ended December 28, 2025",
        "Fourth Quarter / FY2025 Ended December 28, 2025",
        "Fourth Quarter &amp; FY25 Ended December 28, 2025",
        "Fourth Quarter and FY2025 Ended December 28, 2025",
        "Fourth Quarter – Fiscal Year Ended December 28, 2025",
        "Fourth Quarter; Fiscal Year Ended December 28, 2025",
        "Fourth Quarter | Full Year Ended December 28, 2025",
        "Fourth Quarter Plus Fiscal Year Ended December 28, 2025",
        "Twenty\u200bSix Weeks Ended December 28, 2025",
        "Twenty&#8203;Six Weeks Ended December 28, 2025",
        "Twenty\ufeffSix Weeks Ended December 28, 2025",
    ],
    ids=["en-dash-count", "em-dash-count", "spaced-count", "unlisted-spaced-count",
         "ampersand-join", "slash-join", "bare-ampersand-join", "two-ended-clauses",
         "comma-and-join", "hyphen-count", "non-breaking-hyphen-count", "soft-hyphen-count",
         "figure-dash-count", "minus-count", "spaced-hyphen-count", "spaced-en-dash-count",
         "slash-fy-join", "ampersand-fy-join", "and-fy-join", "en-dash-join", "semicolon-join",
         "pipe-join", "plus-join", "zero-width-space-count", "entity-zero-width-count",
         "byte-order-mark-count"],
)
def test_a_header_joining_periods_or_counting_in_an_unread_form_declares_no_span(header: str) -> None:
    """NF3: every spelling of a count or a join the span reader cannot resolve refuses."""
    result = _extract(_quarter_beside_cash_flow(header, "Twelve Months Ended December 28, 2025"))
    assert result.figure("net_income") is None
    assert result.absence("net_income").reason == fig.AbsenceReason.VALUE_AMBIGUOUS.value


@pytest.mark.parametrize(
    ("header", "months"),
    [
        ("Three Months Ended December 28, 2025 and December 29, 2024", 3),
        ("Fourth Quarter Ended December 28, 2025", 3),
        ("13 Weeks Ended December 28, 2025", 3),
        ("Twelve Weeks Ended December 28, 2025", 3),
        ("Sixteen Weeks Ended December 28, 2025", 4),
        ("Six Months Ended December 28, 2025", 6),
    ],
)
def test_a_single_period_header_still_declares_its_span(header: str, months: int) -> None:
    """NF3 control: two dates of one period are not two periods."""
    assert fig._declared_period_months(header) == months


# ─────────────────────────────────────────────────────────────────────────────
# The third delta review's findings: any dash is a hyphen, and the issuer is
# the company the release names first.
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "caption",
    ["Non‑GAAP Results", "Non–GAAP Results", "NON&#8209;GAAP RESULTS", "Non GAAP Results",
     "Non‐GAAP Results", "Non−GAAP Results", "Non\u200b-GAAP Results", "Non&#8203;-GAAP Results",
     "Non\ufeffGAAP Results", "Non\u2060GAAP Results"],
    ids=["non-breaking-hyphen", "en-dash", "entity-hyphen", "space", "hyphen", "minus",
         "zero-width-space", "entity-zero-width-space", "byte-order-mark", "word-joiner"],
)
@pytest.mark.parametrize("after_gaap", [False, True], ids=["alone", "after-gaap"])
def test_a_non_gaap_caption_spelled_with_any_dash_declares_non_gaap(caption: str, after_gaap: bool) -> None:
    """A Unicode hyphen does not turn a non-GAAP section into a GAAP one."""
    rows = f"{_DATED}<tr><td>Total net sales</td><td>$</td><td>8,412</td></tr>"
    lead = _GAAP_CAPTION if after_gaap else ""
    revenue = _extract(_statement(rows, caption=f"{lead}<div>{caption}</div>")).figure("revenue")
    assert revenue is not None
    assert (revenue.value, revenue.basis) == (8412.0, fig.Basis.NON_GAAP.value)


@pytest.mark.parametrize(
    "label",
    ["Diluted EPS attributable to Goodwill Impairment Co.",
     "Diluted EPS attributable to common stockholders of Goodwill Impairment Co."],
)
@pytest.mark.parametrize("issuer", ["", "Walmart Inc."], ids=["no-issuer", "other-issuer"])
def test_an_eps_line_cannot_name_its_own_issuer(label: str, issuer: str) -> None:
    """The name an attribution gives is what is checked, so it cannot also be the issuer."""
    result = _extract(_eps_statement(label, _opening(issuer)))
    assert result.figure("eps_diluted") is None
    assert result.absence("eps_diluted").reason == fig.AbsenceReason.CONCEPT_NOT_PRESENT.value


@pytest.mark.parametrize(
    ("opening", "target"),
    [
        ("Walmart Inc. reports results.</div><div>Flipkart Ltd. is a subsidiary of Walmart.", "Flipkart"),
        ("Acme Advisors LLC (NYSE: AAV) today announced a merger.</div><div>Walmart Inc. reports results.",
         "Walmart"),
        ("Walmart Inc. (NYSE: WMT) today reported results.</div><div>Flipkart Ltd. (NYSE: FLP) posted gains.",
         "Flipkart"),
    ],
    ids=["subsidiary-named-later", "other-company-reports-first", "subsidiary-reports-later"],
)
def test_only_the_first_company_the_release_names_is_the_issuer(opening: str, target: str) -> None:
    """Only the first company named as reporter is the issuer; another one first refuses (fail closed)."""
    result = _extract(_eps_statement(f"Diluted EPS attributable to {target}", opening))
    assert result.figure("eps_diluted") is None
    assert result.absence("eps_diluted").reason == fig.AbsenceReason.CONCEPT_NOT_PRESENT.value


@pytest.mark.parametrize(
    "opening",
    [
        "Acme Advisors LLC advised on the offering.</div><div>Walmart Inc. reports results.",
        "John Smith, Co-Founder of Acme, said.</div><div>Walmart Inc. (NYSE: WMT) today reported results.",
        "Acme, a Delaware corporation, merged.</div><div>Walmart Inc. reports results.",
    ],
    ids=["advisor-without-cue", "co-founder", "delaware-corporation"],
)
def test_a_company_named_without_a_ticker_or_reporting_verb_is_not_the_issuer(opening: str) -> None:
    """An advisor or merger partner is named without a cue; "Co-Founder" and "a Delaware corporation" name no one."""
    eps = _extract(_eps_statement("Diluted EPS attributable to Walmart", opening)).figure("eps_diluted")
    assert eps is not None
    assert (eps.value, eps.basis) == (1.23, fig.Basis.GAAP.value)
    result = _extract(_eps_statement("Diluted EPS attributable to Acme", opening))
    assert result.figure("eps_diluted") is None
    assert result.absence("eps_diluted").reason == fig.AbsenceReason.CONCEPT_NOT_PRESENT.value


@pytest.mark.parametrize(
    ("opening", "label"),
    [
        ("<table><tr><td>Walmart Inc. reports results.</td></tr></table>",
         "Diluted EPS attributable to Walmart"),
        ("The Company and Walmart Inc. report results.", "Diluted EPS attributable to Walmart"),
        ("JPMorgan Chase &amp; Co. reports results.",
         "Diluted earnings per share attributable to JPMorgan Chase"),
    ],
    ids=["layout-table", "self-reference-first", "ampersand-co"],
)
def test_the_issuer_is_named_in_a_layout_table_after_a_self_reference_or_with_ampersand_co(
    opening: str, label: str
) -> None:
    """Walmart sets its release in layout tables; "The Company" names no one; "& Co." is a suffix."""
    eps = _extract(_eps_statement(label, opening)).figure("eps_diluted")
    assert eps is not None
    assert (eps.value, eps.basis) == (1.23, fig.Basis.GAAP.value)


@pytest.mark.parametrize("hyphen", ["-", "‑"], ids=["hyphen", "non-breaking-hyphen"])
def test_an_issuer_named_pro_forma_still_refuses_a_pro_forma_attribution(hyphen: str) -> None:
    """The tail refuses any hyphenated pro forma, even when the release names a company by it."""
    name = f"Acme Pro{hyphen}Forma"
    result = _extract(_eps_statement(f"Diluted EPS attributable to {name}", _opening(f"{name} Inc.")))
    assert result.figure("eps_diluted") is None
    assert result.absence("eps_diluted").reason == fig.AbsenceReason.CONCEPT_NOT_PRESENT.value


# ─────────────────────────────────────────────────────────────────────────────
# The fourth delta review's findings: an attribution never vouches for its own
# issuer, a scope row's attribution is checked like a label's, and every fold
# site is pinned.
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "label",
    [
        "Diluted EPS Attributable To Goodwill Impairment Co.",
        "DILUTED EPS ATTRIBUTABLE TO GOODWILL IMPAIRMENT CO.",
        "Diluted Earnings Per Share Attributable To Acme Operating LLC",
        "Diluted EPS Attributable To Common Stockholders Of SpinCo Inc.",
    ],
)
@pytest.mark.parametrize("issuer", ["", "Walmart Inc."], ids=["no-issuer", "other-issuer"])
def test_an_eps_line_in_any_case_cannot_name_its_own_issuer(label: str, issuer: str) -> None:
    """M1: the attribution window reaches the name itself, so Title Case and capitals refuse too."""
    result = _extract(_eps_statement(label, _opening(issuer)))
    assert result.figure("eps_diluted") is None
    assert result.absence("eps_diluted").reason == fig.AbsenceReason.CONCEPT_NOT_PRESENT.value


def _scoped_eps_statement(scope: str, issuer: str = "") -> str:
    """A bare ``Diluted`` row under a label-only per-share scope row, after a data row."""
    rows = (
        f"{_DATED}<tr><td>Total net sales</td><td>$</td><td>8,412</td></tr>"
        f"<tr><td>{scope}</td></tr><tr><td>Diluted</td><td>$</td><td>1.23</td></tr>"
    )
    return _statement(rows, caption=(f"<div>{issuer}</div>" if issuer else "") + _GAAP_CAPTION)


@pytest.mark.parametrize(
    "scope",
    [
        "Earnings per share attributable to discontinued operations:",
        "Earnings per share attributable to noncontrolling interests:",
        "Earnings per share attributable to Acme Operating LLC:",
        "Earnings per share attributable to Goodwill Impairment:",
        "Earnings per share excluding special items:",
        "Earnings per share from continuing operations:",
        "Pro forma earnings per share:",
    ],
)
def test_a_bare_diluted_row_under_a_component_or_foreign_scope_is_not_eps(scope: str) -> None:
    """M2: a scope row naming a component or another company refuses as the same label would."""
    result = _extract(_scoped_eps_statement(scope, _opening("Walmart Inc.")))
    assert result.figure("eps_diluted") is None
    assert result.absence("eps_diluted").reason == fig.AbsenceReason.CONCEPT_NOT_PRESENT.value


@pytest.mark.parametrize(
    ("scope", "basis"),
    [
        ("Earnings per share:", fig.Basis.GAAP.value),
        ("Earnings (loss) per share:", fig.Basis.GAAP.value),
        ("Earnings per share (1):", fig.Basis.GAAP.value),
        ("Earnings per share attributable to common stockholders:", fig.Basis.GAAP.value),
        ("Net income per share attributable to Walmart:", fig.Basis.GAAP.value),
        ("Adjusted earnings per share:", fig.Basis.NON_GAAP.value),
    ],
)
def test_a_bare_diluted_row_under_the_issuers_eps_scope_is_eps(scope: str, basis: str) -> None:
    """M2 control: the issuer's own EPS scope still binds its bare Diluted row."""
    eps = _extract(_scoped_eps_statement(scope, _opening("Walmart Inc."))).figure("eps_diluted")
    assert eps is not None
    assert (eps.value, eps.basis) == (1.23, basis)


def test_a_scope_attributed_to_the_issuer_needs_the_release_to_name_the_issuer() -> None:
    result = _extract(_scoped_eps_statement("Net income per share attributable to Walmart:"))
    assert result.figure("eps_diluted") is None
    assert result.absence("eps_diluted").reason == fig.AbsenceReason.CONCEPT_NOT_PRESENT.value


@pytest.mark.parametrize("label", ["Diluted EPS (Non‑GAAP)", "Non‑GAAP diluted EPS"])
def test_a_non_gaap_eps_label_with_a_non_breaking_hyphen_is_non_gaap(label: str) -> None:
    """m3: the label is folded both to match its rule and to read its basis."""
    eps = _extract(_eps_statement(label)).figure("eps_diluted")
    assert eps is not None
    assert (eps.value, eps.basis) == (1.23, fig.Basis.NON_GAAP.value)


@pytest.mark.parametrize(
    ("issuer", "label"),
    [
        ("The Coca‑Cola Company", "Diluted EPS attributable to Coca-Cola"),
        ("The Coca-Cola Company", "Diluted EPS attributable to Coca‑Cola"),
    ],
    ids=["hyphen-in-issuer", "hyphen-in-label"],
)
def test_an_issuer_and_its_attribution_match_across_hyphen_spellings(issuer: str, label: str) -> None:
    """m3: the release text and the EPS label are folded before the issuer is compared."""
    eps = _extract(_eps_statement(label, _opening(issuer))).figure("eps_diluted")
    assert eps is not None
    assert (eps.value, eps.basis) == (1.23, fig.Basis.GAAP.value)


def test_a_year_valued_row_with_a_hyphenated_roster_label_is_data_not_a_header() -> None:
    """m3: a roster label says the row is data even when its values look like years."""
    result = _extract(_statement(f"{_DATED}<tr><td>Non‑GAAP diluted EPS</td><td>2025</td></tr>"))
    assert result.figure("eps_diluted") is None
    # Read as data, the row is refused for its missing currency, not passed over as a header.
    assert result.absence("eps_diluted").reason == fig.AbsenceReason.CURRENCY_UNDECLARED.value


@pytest.mark.parametrize("text", ["per\u200b share", "per&#8203; share"], ids=["zero-width", "entity"])
@pytest.mark.parametrize("where", ["label", "scope"])
def test_a_per_share_line_holding_a_zero_width_character_is_eps(text: str, where: str) -> None:
    """m3: the label and scope are folded to read the value as per-share and to match the rule."""
    html = (_eps_statement(f"Diluted earnings {text}") if where == "label"
            else _scoped_eps_statement(f"Earnings {text}:", _opening("Walmart Inc.")))
    eps = _extract(html).figure("eps_diluted")
    assert eps is not None
    assert (eps.value, eps.basis) == (1.23, fig.Basis.GAAP.value)


def test_a_non_gaap_scope_row_with_a_non_breaking_hyphen_is_non_gaap() -> None:
    """m3: a scope row punctuated as prose is no caption, so its basis is read from the folded scope."""
    scope = "Non‑GAAP earnings per share; diluted and basic:"
    eps = _extract(_scoped_eps_statement(scope, _opening("Walmart Inc."))).figure("eps_diluted")
    assert eps is not None
    assert (eps.value, eps.basis) == (1.23, fig.Basis.NON_GAAP.value)

@pytest.mark.parametrize(
    ("scope", "basis"),
    [("Canon GAAP basis:", fig.Basis.GAAP.value), ("Non GAAP basis:", fig.Basis.NON_GAAP.value)],
)
def test_the_non_of_a_word_ending_in_non_is_not_non_gaap(scope: str, basis: str) -> None:
    """m3: "Canon GAAP" holds "non GAAP" inside a word, which is no non-GAAP declaration."""
    rows = f"{_DATED}<tr><td>{scope}</td></tr><tr><td>Total net sales</td><td>$</td><td>8,412</td></tr>"
    revenue = _extract(_statement(rows)).figure("revenue")
    assert revenue is not None
    assert (revenue.value, revenue.basis) == (8412.0, basis)


@pytest.mark.parametrize(
    "header",
    ["Q4-FY26", "Q4 - Fiscal 2026", "Fourth Quarter - Fiscal 2026",
     "Fourth Quarter – FY2025 Ended December 28, 2025", "Q4‑FY2026 Ended December 28, 2025"],
    ids=["hyphen-fy", "spaced-hyphen-fiscal", "words-fiscal", "en-dash-fy", "non-breaking-hyphen-fy"],
)
def test_a_quarter_dashed_to_its_numbered_fiscal_year_is_one_quarter(header: str) -> None:
    """m2: a dash before "FY26" or "Fiscal 2026" says which year the quarter is in."""
    assert fig._declared_period_months(header) == 3


@pytest.mark.parametrize(
    "header",
    ["Q4 FY26 and FY25", "Q4 FY26 / FY25", "Q4-FY26/FY25", "Q4-FY26 and FY25",
     "Fourth Quarter - Fiscal 2026 and Fiscal Year Ended", "Fourth Quarter - Fiscal Year 2026"],
    ids=["and-fy", "slash-fy", "hyphen-then-slash-fy", "hyphen-then-and-fy",
         "qualified-then-joined", "unnumbered-fiscal-year"],
)
def test_a_quarter_dashed_to_a_second_period_still_names_two(header: str) -> None:
    """m2 control: only a numbered fiscal year qualifies; another period still joins."""
    assert fig._declared_period_months(header) is None


def test_a_quarter_dashed_to_its_fiscal_year_wins_over_the_year() -> None:
    """m2: the qualified quarter is the quarter beside a twelve-month cash flow."""
    result = _extract(_quarter_beside_cash_flow(
        "Fourth Quarter - Fiscal 2026 Ended December 28, 2025",
        "Twelve Months Ended December 28, 2025"))
    net_income = result.figure("net_income")
    assert net_income is not None
    assert (net_income.value, net_income.period_end) == (6002.0, "2025-12-28")


# ─────────────────────────────────────────────────────────────────────────────
# Determinism, and the authority ceiling.
# ─────────────────────────────────────────────────────────────────────────────

def test_extraction_is_deterministic_for_one_body(clean_body: str) -> None:
    """Zero new provider/model calls for an unchanged document hash."""
    runs = []
    for _ in range(2):
        document = normalize_filing({
            "accession": ACCESSION, "entity_cik": str(CIK), "form": "8-K",
            "content": clean_body,
        })
        runs.append(fig.extract_release_figures(document).to_dict())
    assert runs[0] == runs[1]


def test_the_extractor_calls_no_model_and_no_network() -> None:
    source = Path(fig.__file__).read_text(encoding="utf-8")
    for forbidden in ("requests", "urllib", "openai", "anthropic", "httpx", "llm", "prompt"):
        assert forbidden not in source.lower().replace("promptly", ""), forbidden


def test_the_output_claims_no_authority(bound: binding.BoundRelease) -> None:
    payload = bound.figures.to_dict()
    assert payload["authority"] == "context_only"
    assert fig.AUTHORITY == "context_only"
    for key in ("rank", "size", "gate", "escalation", "score"):
        assert key not in payload


# ─────────────────────────────────────────────────────────────────────────────
# The bound release is an event, and an amendment does not fork it.
# ─────────────────────────────────────────────────────────────────────────────

def test_an_amended_release_body_is_a_second_revision_of_one_event(
    clean_body: str, tampered_body: str
) -> None:
    original = binding.bind_release_document(
        cik=CIK, accession=ACCESSION, form="8-K", filing_date="2026-01-29",
        acceptance_datetime="2026-01-29T21:07:14Z", report_date=REPORT_DATE,
        body=clean_body,
    )
    amended = binding.bind_release_document(
        cik=CIK, accession=AMENDMENT, form="8-K/A", filing_date="2026-02-02",
        acceptance_datetime="2026-02-02T14:31:00Z", report_date=REPORT_DATE,
        body=tampered_body,
    )
    assert original.revision.source_sha256 != amended.revision.source_sha256

    result = binding.collapse_release_events([original, amended])
    assert len(result.events) == 1
    event = result.events[0]
    assert len(event.revisions) == 2
    assert event.current.filing_key.accession == AMENDMENT
    assert event.amended is True
    # And the corrected figure is what the current revision reports.
    assert amended.figures.figure("eps_diluted", basis="gaap").value == 2.78


def test_the_identical_body_filed_twice_collapses(clean_body: str) -> None:
    first = binding.bind_release_document(
        cik=CIK, accession=ACCESSION, form="8-K", filing_date="2026-01-29",
        acceptance_datetime="2026-01-29T21:07:14Z", report_date=REPORT_DATE,
        body=clean_body,
    )
    again = binding.bind_release_document(
        cik=CIK, accession="0001234567-26-000013", form="8-K", filing_date="2026-01-29",
        acceptance_datetime="2026-01-29T22:15:00Z", report_date=REPORT_DATE,
        body=clean_body,
    )
    result = binding.collapse_release_events([first, again])
    assert len(result.events) == 1
    assert len(result.events[0].revisions) == 1
    assert result.collapsed[0].reason == "identical_body_sha256"


def test_an_empty_body_is_refused() -> None:
    with pytest.raises(binding.BindingError, match="non-empty"):
        binding.bind_release_document(cik=CIK, accession=ACCESSION, body="   ")


def test_submissions_rows_transposes_edgars_parallel_arrays() -> None:
    payload = {"filings": {"recent": {
        "form": ["8-K", "8-K/A"],
        "accessionNumber": [ACCESSION, AMENDMENT],
        "filingDate": ["2026-01-29", "2026-02-02"],
        "acceptanceDateTime": ["2026-01-29T21:07:14.000Z", "2026-02-02T14:31:00.000Z"],
        "reportDate": [REPORT_DATE, REPORT_DATE],
        "items": ["2.02,9.01", "2.02"],
    }}}
    rows = binding.submissions_rows(payload)
    assert [row["accessionNumber"] for row in rows] == [ACCESSION, AMENDMENT]
    assert rows[1]["form"] == "8-K/A"
    # A short list must not raise or shift a value onto the wrong filing.
    payload["filings"]["recent"]["reportDate"] = [REPORT_DATE]
    assert binding.submissions_rows(payload)[1]["reportDate"] == ""


# Synthetic acquisition records exercise provenance replay, never a live grant.
def _synthetic_acquisition():
    import json
    return json.loads((FIXTURES / "sec_acquisition.synthetic.json").read_text())


def _validate_synthetic_acquisition(receipt, source_text=None):
    fixture = _synthetic_acquisition()
    return rcp.validate_sec_acquisition_receipt(
        receipt, cik="0000320193", accession="0000320193-26-000001",
        source_url=fixture["acquisition_receipt"]["requested_url"],
        source_text=fixture["decoded_text"] if source_text is None else source_text,
    )


def test_sec_acquisition_synthetic_entity_to_utf8_replays_without_minting():
    fixture = _synthetic_acquisition()
    receipt = fixture["acquisition_receipt"]
    assert fixture["fixture_kind"].startswith("SYNTHETIC_NOT_LIVE")
    assert receipt["entity_sha256"] != receipt["source_sha256"]
    validated = _validate_synthetic_acquisition(receipt)
    assert validated == receipt and validated is not receipt
    validated["filing_key"]["cik"] = "0000000001"
    assert receipt["filing_key"]["cik"] == "0000320193"
    assert rcp.validate_sec_acquisition_receipt(
        receipt, cik=320193, accession="0000320193-26-000001",
        source_url=receipt["requested_url"], source_text=fixture["decoded_text"],
        entity_body=bytes.fromhex(fixture["entity_bytes_hex"]),
    ) == receipt


@pytest.mark.parametrize("url", [
    "http://www.sec.gov/Archives/edgar/data/320193/000032019326000001/ex991.htm",
    "https://www.sec.gov.evil.test/Archives/edgar/data/320193/000032019326000001/ex991.htm",
    "https://evil.test/Archives/edgar/data/320193/000032019326000001/ex991.htm",
    "https://www.sec.gov:443/Archives/edgar/data/320193/000032019326000001/ex991.htm",
    "https://user@www.sec.gov/Archives/edgar/data/320193/000032019326000001/ex991.htm",
    "https://www.sec.gov/Archives/edgar/data/320194/000032019326000001/ex991.htm",
    "https://www.sec.gov/Archives/edgar/data/320193/000032019326000002/ex991.htm",
    "https://www.sec.gov/Archives/edgar/data/0320193/000032019326000001/ex991.htm",
    "https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/../ex991.htm",
    "https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/%65x991.htm",
    "https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/ex991.htm?",
    "https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/ex991.htm#",
    "https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/ex991.htm?token=x",
    "https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/ex991.htm#part",
    "https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/a\\ex991.htm",
    "https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/é.htm",
])
def test_sec_acquisition_url_refuses_noncanonical_or_different_filing(url):
    with pytest.raises(rcp.ReceiptError):
        rcp.validate_sec_acquisition_url(url, cik=320193, accession="0000320193-26-000001")


@pytest.mark.parametrize("field,value", [
    ("schema", "other"), ("http_status", True), ("http_status", 201),
    ("body_representation", "raw_wire"), ("redirect_policy", "follow_any"),
    ("entity_sha256", "0" * 64), ("source_sha256", "f" * 64),
    ("entity_length", True), ("source_utf8_length", -1),
    ("acquired_at", "2026-01-01"), ("acquired_at", "2026-02-30T00:00:00Z"),
    ("acquired_at", "2026-01-01T00:00:00+00:00"),
    ("decoder", "ascii"), ("decoder", []), ("decode_policy", []),
    ("decode_errors", "replace"), ("decode_policy", "utf8_strict"),
    ("declared_charset", "utf-8"), ("content_type", {"bad": True}),
    ("redirects", {}), ("filing_key", {"cik": "0000320194", "accession": "0000320193-26-000001"}),
])
def test_sec_acquisition_receipt_fails_closed_on_material_tampering(field, value):
    receipt = _synthetic_acquisition()["acquisition_receipt"]
    receipt[field] = value
    with pytest.raises(rcp.ReceiptError):
        _validate_synthetic_acquisition(receipt)


def test_sec_acquisition_refuses_unknown_missing_keys_body_and_unnecessary_fallback():
    receipt = _synthetic_acquisition()["acquisition_receipt"]
    with pytest.raises(rcp.ReceiptError):
        _validate_synthetic_acquisition({**receipt, "rights_granted": True})
    with pytest.raises(rcp.ReceiptError):
        _validate_synthetic_acquisition({k: v for k, v in receipt.items() if k != "acquired_at"})
    with pytest.raises(rcp.ReceiptError):
        _validate_synthetic_acquisition(receipt, "different body")
    for value in (None, [], "receipt"):
        with pytest.raises(rcp.ReceiptError):
            _validate_synthetic_acquisition(value)
    text = "ASCII body"
    receipt.update(entity_sha256=hashlib.sha256(text.encode()).hexdigest(),
                   source_sha256=hashlib.sha256(text.encode()).hexdigest(),
                   entity_length=len(text), source_utf8_length=len(text))
    with pytest.raises(rcp.ReceiptError, match="fallback was not required"):
        _validate_synthetic_acquisition(receipt, text)


def test_sec_acquisition_redirect_chain_requires_every_hop_same_filing():
    fixture = _synthetic_acquisition()
    receipt = fixture["acquisition_receipt"]
    first = receipt["requested_url"]
    final = first.replace("www.sec.gov", "sec.gov").replace("ex991.htm", "canonical.htm")
    receipt["redirects"] = [{"url": first, "status": 302, "location": final, "next_url": final}]
    receipt["final_url"] = final
    assert _validate_synthetic_acquisition(receipt) == receipt
    receipt["redirects"][0]["location"] = "https://evil.test/stolen.htm"
    with pytest.raises(rcp.ReceiptError):
        _validate_synthetic_acquisition(receipt)
    receipt["redirects"][0].update(location=first, next_url=first)
    receipt["final_url"] = first
    with pytest.raises(rcp.ReceiptError, match="cycle"):
        _validate_synthetic_acquisition(receipt)


def test_sec_acquisition_schema_and_runtime_agree_on_synthetic_example():
    import json
    from jsonschema import Draft202012Validator, FormatChecker
    schema = json.loads((Path(__file__).resolve().parents[1] / "contracts" / "earnings_release" / "sec_acquisition.v1.schema.json").read_text())
    receipt = _synthetic_acquisition()["acquisition_receipt"]
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(receipt)
    assert set(schema["required"]) == set(receipt)
    assert _validate_synthetic_acquisition(receipt) == receipt


@pytest.mark.parametrize("name", ["index.htm", "index.html", "index.txt", "index-headers.html", "filing-index.htm", "filing-index.html", "filing-index-headers.html", "filing-index-headers.txt", "INDEX-HEADERS.html"])
def test_sec_index_document_exclusion_in_urls_receipts_and_schema(name):
    import json
    from copy import deepcopy
    from jsonschema import Draft202012Validator
    schema = json.loads((Path(__file__).resolve().parents[1] / "contracts/earnings_release/sec_acquisition.v1.schema.json").read_text())
    original = _synthetic_acquisition()["acquisition_receipt"]
    excluded = original["requested_url"].rsplit("/", 1)[0] + "/" + name
    with pytest.raises(rcp.ReceiptError):
        rcp.validate_sec_acquisition_url(excluded, **original["filing_key"])
    for field in ("requested_url", "final_url"):
        receipt = deepcopy(original)
        receipt[field] = excluded
        assert not Draft202012Validator(schema).is_valid(receipt)
        with pytest.raises(rcp.ReceiptError):
            _validate_synthetic_acquisition(receipt)


@pytest.mark.parametrize("location", ["./canonical.htm", "a/../canonical.htm", "%63anonical.htm", "a\\canonical.htm", "canonical.htm?", "canonical.htm#", "https:canonical.htm", "https:/canonical.htm"])
def test_sec_stored_redirect_raw_location_cannot_be_normalized_into_admission(location):
    from urllib.parse import urljoin
    receipt = _synthetic_acquisition()["acquisition_receipt"]
    first = receipt["requested_url"]
    final = urljoin(first, location)
    receipt["redirects"] = [{"url": first, "status": 302, "location": location, "next_url": final}]
    receipt["final_url"] = final
    with pytest.raises(rcp.ReceiptError):
        _validate_synthetic_acquisition(receipt)


def test_sec_safe_relative_basename_redirect_remains_supported():
    receipt = _synthetic_acquisition()["acquisition_receipt"]
    first = receipt["requested_url"]
    final = first.rsplit("/", 1)[0] + "/canonical.htm"
    receipt["redirects"] = [{"url": first, "status": 302, "location": "canonical.htm", "next_url": final}]
    receipt["final_url"] = final
    assert _validate_synthetic_acquisition(receipt) == receipt
