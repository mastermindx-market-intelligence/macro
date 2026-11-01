"""Lane C synthetic CAT annual heading recovery after discarded factless TOC."""
from __future__ import annotations

import pytest

from engine.fundamental_forensics.statement_graph import (
    StatementGraphError,
    parse_displayed_primary_table,
)

TITLE = "Consolidated Financial Position at December 31"


def toc() -> str:
    return "<table><tr><td>Consolidated Financial Position at December 31</td></tr></table>"


def statement(title_row: str) -> str:
    return f"""
    <table>
    <tr>{title_row}</tr>
    <tr><td>Line</td><td>December 31, 2025</td><td>December 31, 2024</td></tr>
    <tr>
      <td>Assets</td>
      <td><ix:nonFraction name="us-gaap:Assets" contextRef="c2025" id="cat-syn-a25" unitRef="usd" decimals="-6" scale="6">200</ix:nonFraction></td>
      <td><ix:nonFraction name="us-gaap:Assets" contextRef="c2024" id="cat-syn-a24" unitRef="usd" decimals="-6" scale="6">180</ix:nonFraction></td>
    </tr>
    </table>
    """


def test_lane_c_comma_terminated_single_cell_title_after_toc_rearms() -> None:
    # CAT 2023–25 10-K real heading ends in a comma; manifest title does not.
    html = toc() + statement(f"<td>{TITLE},</td>")
    parsed = parse_displayed_primary_table(html, title=TITLE)
    assert parsed["columns_iso"] == ["2025-12-31", "2024-12-31"]
    assert [row["label"] for row in parsed["rows"]] == ["Assets"]
    assert [fact["fact_id"] for fact in parsed["rows"][0]["value_facts"]] == [
        "cat-syn-a25", "cat-syn-a24",
    ]


@pytest.mark.parametrize("unsafe", [
    f"<td>{TITLE},</td><td>Note 12, to financial position and ratios</td>",
    f"<td>See {TITLE}, for further discussion</td>",
    f"<td>{TITLE}.</td>",
    f"<td>{TITLE}, extra annotation</td>",
])
def test_lane_c_comma_rearm_does_not_accept_note_or_other_punctuation(unsafe: str) -> None:
    # None of these are a *complete single title*, so no post-TOC re-arm.
    html = toc() + statement(unsafe)
    with pytest.raises(
        StatementGraphError,
        match=r"^displayed statement table is absent: Consolidated Financial Position at December 31$",
    ):
        parse_displayed_primary_table(html, title=TITLE)


def test_lane_c_comma_title_with_empty_neighbor_still_rearms() -> None:
    # EDGAR chrome can print empty spacer cells alongside the title.
    html = toc() + statement(f"<td>{TITLE},</td><td>  </td>")
    parsed = parse_displayed_primary_table(html, title=TITLE)
    assert parsed["columns_iso"] == ["2025-12-31", "2024-12-31"]


def test_lane_c_comma_title_with_fact_is_not_a_heading() -> None:
    heading = (f"<td>{TITLE},"
               '<ix:nonFraction name="us-gaap:Assets" contextRef="c2025" '
               'id="bad-title-fact" unitRef="usd">30</ix:nonFraction></td>')
    with pytest.raises(StatementGraphError, match=r"^displayed statement table is absent"):
        parse_displayed_primary_table(toc() + statement(heading), title=TITLE)


def test_lane_c_no_toc_title_before_discard_remains_unchanged() -> None:
    html = statement(f"<td>{TITLE},</td>")
    parsed = parse_displayed_primary_table(html, title=TITLE)
    assert parsed["columns_iso"] == ["2025-12-31", "2024-12-31"]


def _cat_year_header(*, units: str = "(Dollars in millions)", years: str = "<td>2025</td><td>2024</td>") -> str:
    return f"""
    <table>
      <tr><td colspan="3">{TITLE},</td></tr>
      <tr><td colspan="3">{units}</td></tr>
      <tr><td> </td>{years}</tr>
      <tr>
        <td>Assets</td>
        <td><ix:nonFraction name="us-gaap:Assets" contextRef="c2025" id="cat-2025" unitRef="usd">200</ix:nonFraction></td>
        <td><ix:nonFraction name="us-gaap:Assets" contextRef="c2024" id="cat-2024" unitRef="usd">180</ix:nonFraction></td>
      </tr>
    </table>
    """


def test_lane_c_cat_10k_unit_band_between_banner_and_years_reconstructs() -> None:
    parsed = parse_displayed_primary_table(toc() + _cat_year_header(), title=TITLE)
    assert parsed["columns_iso"] == ["2025-12-31", "2024-12-31"]
    assert parsed["columns_source"] == "composed_title_year_row"
    assert [row["label"] for row in parsed["rows"]] == ["Assets"]
    assert [fact["fact_id"] for fact in parsed["rows"][0]["value_facts"]] == ["cat-2025", "cat-2024"]


@pytest.mark.parametrize("unit_band,year_cells", [
    ("See accompanying notes", "<td>2025</td><td>2024</td>"),
    ("(Dollars in thousands)", "<td>2025</td><td>2024</td>"),
    ("(Dollars in millions) extra", "<td>2025</td><td>2024</td>"),
    ("(Dollars in millions)", "<td>2025</td><td>Q4</td>"),
    ("(Dollars in millions)", "<td>2025</td><td> </td>"),
])
def test_lane_c_only_whitelisted_unit_band_and_pure_years_are_composed(
    unit_band: str, year_cells: str
) -> None:
    # A notes footer ends a factless capture before the column phase. Either
    # typed absence remains a refusal rather than inventing a statement row.
    refusal = (r"^displayed statement table is absent" if unit_band == "See accompanying notes"
               else r"^displayed statement columns are absent")
    with pytest.raises(StatementGraphError, match=refusal):
        parse_displayed_primary_table(
            toc() + _cat_year_header(units=unit_band, years=year_cells),
            title=TITLE,
        )


@pytest.mark.parametrize("annual_kind,unit", [
    ("Consolidated Results of Operations for the Years Ended December 31",
     "(Dollars in millions except per share data)"),
    ("Consolidated Statement of Cash Flow for the Years Ended December 31",
     "(Millions of dollars)"),
])
def test_lane_c_cat_annual_income_cashflow_unit_variants(annual_kind: str, unit: str) -> None:
    # The real CAT 10-Ks place three comparative years after exactly this
    # one nonnumeric unit band; their period groups must not be inferred from
    # arbitrary prose.
    html = f"""
    <table><tr><td>{annual_kind}</td></tr></table>
    <table>
      <tr><td colspan="4">{annual_kind},</td></tr>
      <tr><td colspan="4">{unit}</td></tr>
      <tr><td> </td><td>2025</td><td>2024</td><td>2023</td></tr>
      <tr>
        <td>Operating result</td>
        <td><ix:nonFraction name="us-gaap:NetIncomeLoss" contextRef="d2025" id="cat-annual-25" unitRef="usd">12</ix:nonFraction></td>
        <td><ix:nonFraction name="us-gaap:NetIncomeLoss" contextRef="d2024" id="cat-annual-24" unitRef="usd">11</ix:nonFraction></td>
        <td><ix:nonFraction name="us-gaap:NetIncomeLoss" contextRef="d2023" id="cat-annual-23" unitRef="usd">10</ix:nonFraction></td>
      </tr>
    </table>
    """
    parsed = parse_displayed_primary_table(html, title=annual_kind)
    assert parsed["columns_iso"] == ["2025-12-31", "2024-12-31", "2023-12-31"]
    assert parsed["columns_source"] == "composed_title_year_row"
    assert [f["fact_id"] for f in parsed["rows"][0]["value_facts"]] == [
        "cat-annual-25", "cat-annual-24", "cat-annual-23"
    ]


def test_lane_c_comma_title_beside_an_empty_display_fact_is_not_a_heading() -> None:
    # The fact's display text is empty, so the title cell is the row's only
    # nonblank text; the row still carries a numeric fact and cannot re-arm.
    heading = (f"<td>{TITLE},</td>"
               '<td><ix:nonFraction name="us-gaap:Assets" contextRef="c2025" '
               'id="bad-empty-fact" unitRef="usd"></ix:nonFraction></td>')
    with pytest.raises(StatementGraphError, match=r"^displayed statement table is absent"):
        parse_displayed_primary_table(toc() + statement(heading), title=TITLE)


def test_lane_c_double_comma_title_does_not_rearm() -> None:
    # Exactly one terminal comma is the observed CAT variant; stripping every
    # trailing comma would admit other punctuation runs.
    with pytest.raises(StatementGraphError, match=r"^displayed statement table is absent"):
        parse_displayed_primary_table(toc() + statement(f"<td>{TITLE},,</td>"), title=TITLE)


def test_lane_c_two_consecutive_unit_bands_refuse() -> None:
    # Only one exact unit band may sit between the title banner and the years.
    html = toc() + f"""
    <table>
      <tr><td colspan="3">{TITLE},</td></tr>
      <tr><td colspan="3">(Dollars in millions)</td></tr>
      <tr><td colspan="3">(Dollars in millions)</td></tr>
      <tr><td> </td><td>2025</td><td>2024</td></tr>
      <tr>
        <td>Assets</td>
        <td><ix:nonFraction name="us-gaap:Assets" contextRef="c2025" id="cat-2b-25" unitRef="usd">200</ix:nonFraction></td>
        <td><ix:nonFraction name="us-gaap:Assets" contextRef="c2024" id="cat-2b-24" unitRef="usd">180</ix:nonFraction></td>
      </tr>
    </table>
    """
    with pytest.raises(StatementGraphError, match=r"^displayed statement columns are absent"):
        parse_displayed_primary_table(html, title=TITLE)


@pytest.mark.parametrize("unit_band", ["(In millions)", "(Dollars in millions, except ratios)", "(dollars in millions)"])
def test_lane_c_unit_band_is_an_exact_list_not_a_millions_substring(unit_band: str) -> None:
    with pytest.raises(StatementGraphError, match=r"^displayed statement columns are absent"):
        parse_displayed_primary_table(toc() + _cat_year_header(units=unit_band), title=TITLE)


def test_lane_c_snow_banner_without_unit_band_keeps_year_row_source() -> None:
    # The unit-band skip is what marks the CAT title-banner composition; a
    # banner directly over the years keeps the existing SNOW source label.
    html = toc() + f"""
    <table>
      <tr><td colspan="3">{TITLE},</td></tr>
      <tr><td> </td><td>2025</td><td>2024</td></tr>
      <tr>
        <td>Assets</td>
        <td><ix:nonFraction name="us-gaap:Assets" contextRef="c2025" id="cat-nb-25" unitRef="usd">200</ix:nonFraction></td>
        <td><ix:nonFraction name="us-gaap:Assets" contextRef="c2024" id="cat-nb-24" unitRef="usd">180</ix:nonFraction></td>
      </tr>
    </table>
    """
    parsed = parse_displayed_primary_table(html, title=TITLE)
    assert parsed["columns_iso"] == ["2025-12-31", "2024-12-31"]
    assert parsed["columns_source"] == "composed_year_row"
