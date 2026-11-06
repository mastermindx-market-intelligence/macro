"""FIF P5B r1: right-edge grid padding, glued month tokens, factless-capture discard."""
from __future__ import annotations

import pytest

from engine.fundamental_forensics.statement_graph import (
    StatementGraphError,
    _DATE_RE,
    _MONTH_DAY_RE,
    _expand_displayed_statement_grid,
    _iso_dates_from_text,
    parse_displayed_primary_table,
)

TITLE = "SYNTHETIC STATEMENT OF OPERATIONS"


def _cell(text: str = "", *, colspan: int = 1, rowspan: int = 1) -> dict:
    """A parser-shaped source cell for direct ``_expand_displayed_statement_grid`` calls."""
    return {
        "text": text,
        "facts": [],
        "colspan": colspan,
        "rowspan": rowspan,
        "span_overflow": False,
        "rowspan_carry": False,
        "colspan_carry": False,
    }


# --- R1: right-edge padding in _expand_displayed_statement_grid ---


def test_r1_right_edge_hole_is_padded_fact_free() -> None:
    grid = _expand_displayed_statement_grid(
        [
            [_cell("SYNTHETIC STATEMENT OF OPERATIONS")],
            [_cell("Revenue"), _cell("10"), _cell("9")],
        ]
    )
    assert [len(row) for row in grid] == [3, 3]
    assert grid[0][0]["text"] == "SYNTHETIC STATEMENT OF OPERATIONS"
    assert "edge_pad" not in grid[0][0]
    for slot in grid[0][1:]:
        assert slot["text"] == ""
        assert slot["facts"] == []
        assert slot["edge_pad"] is True
        assert slot["colspan"] == 1
        assert slot["rowspan"] == 1
        assert slot["rowspan_carry"] is False
        assert slot["colspan_carry"] is True
    assert all("edge_pad" not in slot for slot in grid[1])


def test_r1_padding_applies_per_row_anywhere_in_the_grid() -> None:
    grid = _expand_displayed_statement_grid(
        [
            [_cell("Line"), _cell("March 31, 2025"), _cell("March 31, 2024")],
            [_cell("Total")],
            [_cell("Revenue"), _cell("10"), _cell("9")],
        ]
    )
    assert [len(row) for row in grid] == [3, 3, 3]
    assert [slot.get("edge_pad") for slot in grid[1]] == [None, True, True]
    assert [slot.get("edge_pad") for row in grid for slot in row].count(True) == 2


def test_r1_interior_hole_still_refuses() -> None:
    # Row 1 holds only carries in columns 1-3 (the colspan=3 group rowspans
    # down), so column 0 is a hole BELOW k, not a right-edge gap.
    with pytest.raises(StatementGraphError, match=r"ragged grid at row 1 column 0"):
        _expand_displayed_statement_grid(
            [
                [_cell("label"), _cell("group", colspan=3, rowspan=2)],
                [],
            ]
        )


def test_r1_row_with_zero_occupied_slots_still_refuses() -> None:
    with pytest.raises(StatementGraphError, match=r"ragged grid at row 0 column 0"):
        _expand_displayed_statement_grid(
            [
                [],
                [_cell("a"), _cell("b"), _cell("c")],
            ]
        )


def test_r1_rectangular_grid_has_no_edge_pad_anywhere() -> None:
    grid = _expand_displayed_statement_grid(
        [
            [_cell("Line"), _cell("March 31, 2025"), _cell("March 31, 2024")],
            [_cell("Revenue"), _cell("10"), _cell("9")],
        ]
    )
    assert [len(row) for row in grid] == [3, 3]
    assert all("edge_pad" not in slot for row in grid for slot in row)
    assert [slot["text"] for slot in grid[0]] == ["Line", "March 31, 2025", "March 31, 2024"]


def test_r1_narrow_banner_row_expands_to_dated_columns() -> None:
    # The banner row spans only 2 of the body's 3 columns (the ragged-banner
    # income shape): at baseline this refuses with a ragged grid.
    html = """
    <html><body>
    <table>
    <tr><td colspan="2">SYNTHETIC STATEMENT OF OPERATIONS</td></tr>
    <tr>
      <td>Line</td>
      <td>March 31, 2025</td>
      <td>March 31, 2024</td>
    </tr>
    <tr>
      <td>Revenue</td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2025" id="syn-p5b-r1-2025" unitRef="usd" decimals="-6" scale="6">10</ix:nonFraction></td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2024" id="syn-p5b-r1-2024" unitRef="usd" decimals="-6" scale="6">9</ix:nonFraction></td>
    </tr>
    </table>
    </body></html>
    """
    parsed = parse_displayed_primary_table(html, title=TITLE)
    assert parsed["columns_iso"] == ["2025-03-31", "2024-03-31"]
    assert [row["label"] for row in parsed["rows"]] == ["Revenue"]
    assert [item["fact_id"] for item in parsed["rows"][0]["value_facts"]] == [
        "syn-p5b-r1-2025",
        "syn-p5b-r1-2024",
    ]


# --- R2: glued month tokens in _DATE_RE / _MONTH_DAY_RE ---


def test_r2_glued_month_date_yields_iso_date() -> None:
    match = _DATE_RE.search("As ofMarch 31, 2025")
    assert match is not None
    assert match.group(1, 2, 3) == ("March", "31", "2025")
    assert _iso_dates_from_text("As ofMarch 31, 2025") == ["2025-03-31"]


def test_r2_glued_month_day_phrase_matches() -> None:
    match = _MONTH_DAY_RE.search("Fiscal Year EndedJanuary 31,")
    assert match is not None
    assert match.group(1, 2) == ("January", "31")


def test_r2_glued_full_date_is_a_date_not_a_month_day_phrase() -> None:
    # The negative lookahead still rejects the day when a year follows it.
    assert _MONTH_DAY_RE.search("EndedMarch 31, 2025") is None
    assert _iso_dates_from_text("EndedMarch 31, 2025") == ["2025-03-31"]


def test_r2_lookalikes_and_all_caps_glue_stay_unmatched() -> None:
    # Pinned from the pre-R2 pattern: "Decor." is not December, and the seam in
    # "ASOFMARCH" is uppercase-to-uppercase, so no boundary fires there.
    assert _DATE_RE.search("Decor. 31, 2025") is None
    assert _DATE_RE.search("ASOFMARCH 31, 2025") is None
    assert _iso_dates_from_text("Decor. 31, 2025") == []
    assert _iso_dates_from_text("ASOFMARCH 31, 2025") == []


def test_r2_lowercase_to_lowercase_seam_stays_unmatched() -> None:
    # "xsmarch": the seam is lowercase followed by lowercase, so the glued-token
    # lookaround must not fire (it is scoped case-sensitive).
    assert _DATE_RE.search("xsmarch 31, 2025") is None
    assert _iso_dates_from_text("xsmarch 31, 2025") == []


def test_r2_glued_as_of_header_composes_columns() -> None:
    # The balance-sheet header shape with no space after "As of": at baseline
    # no column date is found and the statement refuses with absent columns.
    html = """
    <html><body>
    <table>
    <tr><td colspan="3">SYNTHETIC STATEMENT OF OPERATIONS</td></tr>
    <tr>
      <td>Line</td>
      <td>As ofMarch 31, 2025</td>
      <td>As ofMarch 31, 2024</td>
    </tr>
    <tr>
      <td>Cash</td>
      <td><ix:nonFraction name="us-gaap:CashAndCashEquivalentsAtCarryingValue" contextRef="c2025" id="syn-p5b-r2-2025" unitRef="usd" decimals="-6" scale="6">100</ix:nonFraction></td>
      <td><ix:nonFraction name="us-gaap:CashAndCashEquivalentsAtCarryingValue" contextRef="c2024" id="syn-p5b-r2-2024" unitRef="usd" decimals="-6" scale="6">90</ix:nonFraction></td>
    </tr>
    </table>
    </body></html>
    """
    parsed = parse_displayed_primary_table(html, title=TITLE)
    assert parsed["columns_iso"] == ["2025-03-31", "2024-03-31"]
    assert [row["label"] for row in parsed["rows"]] == ["Cash"]
    assert [item["fact_id"] for item in parsed["rows"][0]["value_facts"]] == [
        "syn-p5b-r2-2025",
        "syn-p5b-r2-2024",
    ]


# --- R3: factless captures are discarded, not ended ---


def test_r3_factless_toc_table_is_discarded_for_the_real_table() -> None:
    html = """
    <html><body>
    <table>
    <tr><td>SYNTHETIC STATEMENT OF OPERATIONS</td></tr>
    </table>
    <table>
    <tr><td colspan="3">SYNTHETIC STATEMENT OF OPERATIONS</td></tr>
    <tr>
      <td>Line</td>
      <td>March 31, 2025</td>
      <td>March 31, 2024</td>
    </tr>
    <tr>
      <td>Revenue</td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2025" id="syn-p5b-r3-2025" unitRef="usd" decimals="-6" scale="6">10</ix:nonFraction></td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2024" id="syn-p5b-r3-2024" unitRef="usd" decimals="-6" scale="6">9</ix:nonFraction></td>
    </tr>
    </table>
    </body></html>
    """
    parsed = parse_displayed_primary_table(html, title=TITLE)
    assert parsed["columns_iso"] == ["2025-03-31", "2024-03-31"]
    assert [row["label"] for row in parsed["rows"]] == ["Revenue"]
    assert [item["fact_id"] for item in parsed["rows"][0]["value_facts"]] == [
        "syn-p5b-r3-2025",
        "syn-p5b-r3-2024",
    ]


def test_r3_only_factless_title_table_keeps_table_absent_refusal() -> None:
    table_ended = """
    <html><body>
    <table>
    <tr><td>SYNTHETIC STATEMENT OF OPERATIONS</td></tr>
    </table>
    </body></html>
    """
    notes_ended = """
    <html><body>
    <table>
    <tr><td>SYNTHETIC STATEMENT OF OPERATIONS</td></tr>
    <tr><td>see accompanying notes</td></tr>
    </table>
    </body></html>
    """
    for html in (table_ended, notes_ended):
        with pytest.raises(
            StatementGraphError,
            match=r"^displayed statement table is absent: SYNTHETIC STATEMENT OF OPERATIONS$",
        ):
            parse_displayed_primary_table(html, title=TITLE)


def test_r3_factless_capture_ended_by_notes_row_is_discarded() -> None:
    html = """
    <html><body>
    <table>
    <tr><td>SYNTHETIC STATEMENT OF OPERATIONS</td></tr>
    <tr><td>see accompanying notes</td></tr>
    </table>
    <table>
    <tr><td colspan="3">SYNTHETIC STATEMENT OF OPERATIONS</td></tr>
    <tr>
      <td>Line</td>
      <td>March 31, 2025</td>
      <td>March 31, 2024</td>
    </tr>
    <tr>
      <td>Revenue</td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2025" id="syn-p5b-r3n-2025" unitRef="usd" decimals="-6" scale="6">10</ix:nonFraction></td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2024" id="syn-p5b-r3n-2024" unitRef="usd" decimals="-6" scale="6">9</ix:nonFraction></td>
    </tr>
    </table>
    </body></html>
    """
    parsed = parse_displayed_primary_table(html, title=TITLE)
    assert parsed["columns_iso"] == ["2025-03-31", "2024-03-31"]
    assert [row["label"] for row in parsed["rows"]] == ["Revenue"]
    assert [item["fact_id"] for item in parsed["rows"][0]["value_facts"]] == [
        "syn-p5b-r3n-2025",
        "syn-p5b-r3n-2024",
    ]


def test_r3_reset_requires_a_new_title_hit() -> None:
    # After the factless capture is discarded, a following table WITHOUT the
    # title must not be captured on the discarded capture's title signal.
    html = """
    <html><body>
    <table>
    <tr><td>SYNTHETIC STATEMENT OF OPERATIONS</td></tr>
    </table>
    <table>
    <tr>
      <td>Line</td>
      <td>March 31, 2025</td>
      <td>March 31, 2024</td>
    </tr>
    <tr>
      <td>Revenue</td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2025" id="syn-p5b-r3c-2025" unitRef="usd" decimals="-6" scale="6">10</ix:nonFraction></td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2024" id="syn-p5b-r3c-2024" unitRef="usd" decimals="-6" scale="6">9</ix:nonFraction></td>
    </tr>
    </table>
    </body></html>
    """
    with pytest.raises(
        StatementGraphError,
        match=r"^displayed statement table is absent: SYNTHETIC STATEMENT OF OPERATIONS$",
    ):
        parse_displayed_primary_table(html, title=TITLE)


def test_r3_fact_bearing_capture_still_ends_at_notes_row() -> None:
    html = """
    <html><body>
    <table>
    <tr><td colspan="3">SYNTHETIC STATEMENT OF OPERATIONS</td></tr>
    <tr>
      <td>Line</td>
      <td>March 31, 2025</td>
      <td>March 31, 2024</td>
    </tr>
    <tr>
      <td>Revenue</td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2025" id="syn-p5b-r3e-2025" unitRef="usd" decimals="-6" scale="6">10</ix:nonFraction></td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2024" id="syn-p5b-r3e-2024" unitRef="usd" decimals="-6" scale="6">9</ix:nonFraction></td>
    </tr>
    <tr><td>see accompanying notes</td></tr>
    </table>
    <table>
    <tr>
      <td>Other</td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2025" id="syn-p5b-r3e-stray" unitRef="usd" decimals="-6" scale="6">7</ix:nonFraction></td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2024" id="syn-p5b-r3e-stray2" unitRef="usd" decimals="-6" scale="6">6</ix:nonFraction></td>
    </tr>
    </table>
    </body></html>
    """
    parsed = parse_displayed_primary_table(html, title=TITLE)
    assert [row["label"] for row in parsed["rows"]] == ["Revenue"]
    assert [item["fact_id"] for item in parsed["rows"][0]["value_facts"]] == [
        "syn-p5b-r3e-2025",
        "syn-p5b-r3e-2024",
    ]


def test_r6_values_beyond_dated_columns_refuse_on_a_rectangular_grid() -> None:
    # Rectangular grid (no edge pad): the banner prints an undated fourth column, so a
    # third value has no date to bind to and must refuse rather than be dropped.
    html = """
    <html><body>
    <div>SYNTHETIC STATEMENT OF OPERATIONS</div>
    <table>
    <tr>
      <td>Line</td>
      <td>March 31, 2025</td>
      <td>March 31, 2024</td>
      <td>Change</td>
    </tr>
    <tr>
      <td>Revenue</td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2025" id="syn-p5b-r6-2025" unitRef="usd" decimals="-6" scale="6">10</ix:nonFraction></td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2024" id="syn-p5b-r6-2024" unitRef="usd" decimals="-6" scale="6">9</ix:nonFraction></td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2023" id="syn-p5b-r6-2023" unitRef="usd" decimals="-6" scale="6">1</ix:nonFraction></td>
    </tr>
    </table>
    </body></html>
    """
    with pytest.raises(
        StatementGraphError,
        match=r"^displayed statement layout unsupported: row 0 carries 3 values for 2 dated columns$",
    ):
        parse_displayed_primary_table(html, title=TITLE)


def test_r6_row_with_values_equal_to_dated_columns_still_parses() -> None:
    html = """
    <html><body>
    <div>SYNTHETIC STATEMENT OF OPERATIONS</div>
    <table>
    <tr>
      <td>Line</td>
      <td>March 31, 2025</td>
      <td>March 31, 2024</td>
      <td>Change</td>
    </tr>
    <tr>
      <td>Revenue</td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2025" id="syn-p5b-r6e-2025" unitRef="usd" decimals="-6" scale="6">10</ix:nonFraction></td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2024" id="syn-p5b-r6e-2024" unitRef="usd" decimals="-6" scale="6">9</ix:nonFraction></td>
      <td>11%</td>
    </tr>
    </table>
    </body></html>
    """
    parsed = parse_displayed_primary_table(html, title=TITLE)
    assert parsed["columns_iso"] == ["2025-03-31", "2024-03-31"]
    assert [item["fact_id"] for item in parsed["rows"][0]["value_facts"]] == [
        "syn-p5b-r6e-2025",
        "syn-p5b-r6e-2024",
    ]


# --- R1 repair: only a fact-free row is padded ---


def _ix(context: str, fact_id: str, value: str = "5") -> str:
    return (
        f'<ix:nonFraction name="us-gaap:Revenues" contextRef="{context}" id="{fact_id}" '
        f'unitRef="usd" decimals="-6" scale="6">{value}</ix:nonFraction>'
    )


def test_r1_short_fact_row_after_colspan_dash_is_refused() -> None:
    # The FY2024 fact sits in the 2024 column group but would land on the 2025
    # column if the short row were padded on its right edge.
    html = f"""
    <html><body>
    <div>SYNTHETIC STATEMENT OF OPERATIONS</div>
    <table>
    <tr><td>Line</td><td></td><td>December 31, 2025</td><td></td><td>December 31, 2024</td></tr>
    <tr><td>Revenue</td><td>$</td><td>{_ix("c2025", "syn-p5b-r1d-2025", "10")}</td><td>$</td><td>{_ix("c2024", "syn-p5b-r1d-2024", "9")}</td></tr>
    <tr><td>Legacy charge</td><td colspan="2">—</td><td>{_ix("c2024", "syn-p5b-r1d-legacy")}</td></tr>
    </table>
    </body></html>
    """
    with pytest.raises(
        StatementGraphError,
        match=r"^displayed statement layout unsupported: ragged grid at row 2 column 4$",
    ):
        parse_displayed_primary_table(html, title=TITLE)


def test_r1_short_prior_only_fact_row_is_refused() -> None:
    html = f"""
    <html><body>
    <div>SYNTHETIC STATEMENT OF OPERATIONS</div>
    <table>
    <tr><td>Line</td><td>December 31, 2025</td><td>December 31, 2024</td></tr>
    <tr><td>Revenue</td><td>{_ix("c2025", "syn-p5b-r1p-2025", "10")}</td><td>{_ix("c2024", "syn-p5b-r1p-2024", "9")}</td></tr>
    <tr><td>Legacy charge</td><td>{_ix("c2024", "syn-p5b-r1p-legacy")}</td></tr>
    </table>
    </body></html>
    """
    with pytest.raises(
        StatementGraphError,
        match=r"^displayed statement layout unsupported: ragged grid at row 2 column 2$",
    ):
        parse_displayed_primary_table(html, title=TITLE)


def test_r1_fact_bearing_short_row_is_refused_by_the_grid() -> None:
    narrow = dict(_cell("10"), facts=[{"fact_id": "syn-p5b-r1g"}])
    with pytest.raises(
        StatementGraphError,
        match=r"^displayed statement layout unsupported: ragged grid at row 1 column 2$",
    ):
        _expand_displayed_statement_grid(
            [
                [_cell("Line"), _cell("March 31, 2025"), _cell("March 31, 2024")],
                [_cell("Revenue"), narrow],
            ]
        )


def test_r1_trailing_text_cell_beyond_dated_columns_binds_nothing() -> None:
    # The original stray-cell shape: the narrow row is the fact-free date
    # header, so it is padded; the stray text carries no fact and both values
    # stay on their own dates.
    html = f"""
    <html><body>
    <div>SYNTHETIC STATEMENT OF OPERATIONS</div>
    <table>
    <tr><td>Line</td><td>March 31, 2025</td><td>March 31, 2024</td></tr>
    <tr><td>Revenue</td><td>{_ix("c2025", "syn-p5b-r1s-2025", "10")}</td><td>{_ix("c2024", "syn-p5b-r1s-2024", "9")}</td><td>stray extra cell</td></tr>
    </table>
    </body></html>
    """
    parsed = parse_displayed_primary_table(html, title=TITLE)
    assert parsed["columns_iso"] == ["2025-03-31", "2024-03-31"]
    assert [item["fact_id"] for item in parsed["rows"][0]["value_facts"]] == [
        "syn-p5b-r1s-2025",
        "syn-p5b-r1s-2024",
    ]


# --- R3 repair: after a discard only the title itself re-arms the capture ---

_R3_REAL_TABLE = f"""
    <table>
    <tr><td>Line</td><td>December 31, 2025</td><td>December 31, 2024</td></tr>
    <tr><td>Revenue</td><td>{_ix("c2025", "syn-p5b-r3x-2025", "10")}</td><td>{_ix("c2024", "syn-p5b-r3x-2024", "9")}</td></tr>
    </table>
"""

_R3_NOTE_TABLE = f"""
    <p>Note 7. Lease cost is included in the SYNTHETIC STATEMENT OF OPERATIONS as follows:</p>
    <table>
    <tr><td></td><td>December 31, 2025</td><td>December 31, 2024</td></tr>
    <tr><td>Lease cost</td><td>{_ix("c2025", "syn-p5b-r3x-lease-2025", "3")}</td><td>{_ix("c2024", "syn-p5b-r3x-lease-2024", "2")}</td></tr>
    </table>
"""


def test_r3_span_split_title_after_discard_does_not_fall_to_a_note_table() -> None:
    html = f"""
    <html><body>
    <table><tr><td>SYNTHETIC STATEMENT OF OPERATIONS</td><td>45</td></tr></table>
    <p><span>SYNTHETIC STATEMENT</span> <span>OF OPERATIONS</span></p>
    {_R3_REAL_TABLE}
    {_R3_NOTE_TABLE}
    </body></html>
    """
    with pytest.raises(
        StatementGraphError,
        match=r"^displayed statement table is absent: SYNTHETIC STATEMENT OF OPERATIONS$",
    ):
        parse_displayed_primary_table(html, title=TITLE)


def test_r3_split_header_table_after_discard_does_not_fall_to_a_note_table() -> None:
    html = f"""
    <html><body>
    <table><tr><td>SYNTHETIC STATEMENT OF OPERATIONS</td><td>45</td></tr></table>
    <p>SYNTHETIC STATEMENT OF OPERATIONS</p>
    <table><tr><td>Line</td><td>December 31, 2025</td><td>December 31, 2024</td></tr></table>
    <table>
    <tr><td>Revenue</td><td>{_ix("c2025", "syn-p5b-r3h-2025", "10")}</td><td>{_ix("c2024", "syn-p5b-r3h-2024", "9")}</td></tr>
    </table>
    {_R3_NOTE_TABLE}
    </body></html>
    """
    with pytest.raises(
        StatementGraphError,
        match=r"^displayed statement table is absent: SYNTHETIC STATEMENT OF OPERATIONS$",
    ):
        parse_displayed_primary_table(html, title=TITLE)


def test_r3_whole_title_paragraph_after_discard_captures_the_real_table() -> None:
    html = f"""
    <html><body>
    <table><tr><td>SYNTHETIC STATEMENT OF OPERATIONS</td><td>45</td></tr></table>
    <p>SYNTHETIC STATEMENT OF OPERATIONS</p>
    {_R3_REAL_TABLE}
    {_R3_NOTE_TABLE}
    </body></html>
    """
    parsed = parse_displayed_primary_table(html, title=TITLE)
    assert [row["label"] for row in parsed["rows"]] == ["Revenue"]
    assert [item["fact_id"] for item in parsed["rows"][0]["value_facts"]] == [
        "syn-p5b-r3x-2025",
        "syn-p5b-r3x-2024",
    ]


def test_r3_list_title_after_discard_needs_the_whole_chunk() -> None:
    html = f"""
    <html><body>
    <table><tr><td>Synthetic Statement of Operations</td><td>45</td></tr></table>
    <p>The synthetic statement of operations is presented below.</p>
    {_R3_REAL_TABLE}
    </body></html>
    """
    with pytest.raises(StatementGraphError, match=r"^displayed statement table is absent"):
        parse_displayed_primary_table(html, title=["synthetic statement of operations"])
    whole = html.replace(
        "<p>The synthetic statement of operations is presented below.</p>",
        "<p>  SYNTHETIC   Statement of Operations </p>",
    )
    parsed = parse_displayed_primary_table(whole, title=["synthetic statement of operations"])
    assert [row["label"] for row in parsed["rows"]] == ["Revenue"]


def test_r3_single_exact_title_cell_beside_units_rearms_after_discards() -> None:
    # After a discard only a cell whose whole text is the title re-arms; the
    # joined row ("title (in millions)") is not an exact title and must not be
    # the sole route back into capture.
    html = """
    <html><body>
    <table><tr><td>SYNTHETIC STATEMENT OF OPERATIONS</td><td>45</td></tr></table>
    <table><tr><td>SYNTHETIC STATEMENT OF OPERATIONS</td><td>45</td></tr></table>
    <table>
    <tr><td>SYNTHETIC STATEMENT OF OPERATIONS</td><td>(in millions)</td><td></td></tr>
    <tr><td>Line</td><td>March 31, 2025</td><td>March 31, 2024</td></tr>
    <tr>
      <td>Revenue</td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2025" id="syn-p5b-r3c-2025" unitRef="usd" decimals="-6" scale="6">10</ix:nonFraction></td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2024" id="syn-p5b-r3c-2024" unitRef="usd" decimals="-6" scale="6">9</ix:nonFraction></td>
    </tr>
    </table>
    </body></html>
    """
    parsed = parse_displayed_primary_table(html, title=TITLE)
    assert parsed["columns_iso"] == ["2025-03-31", "2024-03-31"]
    assert [row["label"] for row in parsed["rows"]] == ["Revenue"]
    assert [item["fact_id"] for item in parsed["rows"][0]["value_facts"]] == [
        "syn-p5b-r3c-2025",
        "syn-p5b-r3c-2024",
    ]
