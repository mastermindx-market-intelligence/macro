"""Third-pass title-block carry: a factless heading table hands the displayed
statement title to the untitled fact table after it
(DEC:FIF-DISPLAYED-TITLE-BLOCK-CARRY-20261103)."""
from __future__ import annotations

import pytest

from engine.fundamental_forensics import statement_graph
from engine.fundamental_forensics.statement_graph import (
    StatementGraphError,
    parse_displayed_primary_table,
)

_TITLE = "Consolidated Statements of Operations"
_COMPANY = "Corning Incorporated and Subsidiary Companies"


def _title_block(*rows: str) -> str:
    """A factless heading table, one ``<td>`` row per argument."""
    body = "".join(f"<tr><td>{row}</td></tr>\n" for row in rows)
    return f"<table>\n{body}</table>\n"


def _fact_table(
    *,
    label: str = "Net income",
    ids: tuple[str, str] = ("tbc-ni-2025", "tbc-ni-2024"),
    lead_row: str = "",
) -> str:
    """An untitled statement body parse_displayed_primary_table accepts."""
    return f"""<table>
    {lead_row}
    <tr><td>Line</td><td>September 27, 2025</td><td>September 28, 2024</td></tr>
    <tr>
      <td>{label}</td>
      <td><ix:nonFraction name="us-gaap:NetIncomeLoss" contextRef="d2025" id="{ids[0]}" unitRef="usd" decimals="-6" scale="6">100</ix:nonFraction></td>
      <td><ix:nonFraction name="us-gaap:NetIncomeLoss" contextRef="d2024" id="{ids[1]}" unitRef="usd" decimals="-6" scale="6">90</ix:nonFraction></td>
    </tr>
    </table>
"""


def _rows(parsed: dict) -> list[dict]:
    return [
        {
            "label": row["label"],
            "facts": [str(item.get("fact_id") or "") for item in row["value_facts"]],
        }
        for row in parsed["rows"]
    ]


def _absent(html: str, title: str | list[str] = _TITLE) -> None:
    with pytest.raises(StatementGraphError) as caught:
        parse_displayed_primary_table(html, title=title)
    assert caught.value.refusal_code == "displayed_table_absent"


_SERVED = [{"label": "Net income", "facts": ["tbc-ni-2025", "tbc-ni-2024"]}]


# --- the carry serves ----------------------------------------------------


def test_tbc1_title_block_then_untitled_fact_table_serves() -> None:
    html = _title_block(_COMPANY, _TITLE) + _fact_table()
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert parsed["columns_iso"] == ["2025-09-27", "2024-09-28"]
    assert _rows(parsed) == _SERVED
    assert parsed["table_source"] == "carried_title_block"


def test_tbc1_title_block_with_caption_rows_serves() -> None:
    html = (
        _title_block(_COMPANY, _TITLE, "")
        + _fact_table()
    )
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert _rows(parsed) == _SERVED
    assert parsed["table_source"] == "carried_title_block"


def test_tbc1_heading_rows_after_the_title_stay_out_of_the_statement() -> None:
    html = (
        _title_block(_TITLE, "(In millions, except per share amounts)", "Years ended")
        + _fact_table()
    )
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert _rows(parsed) == _SERVED
    assert parsed["table_source"] == "carried_title_block"


def test_tbc1_contents_table_before_the_title_block_is_still_discarded() -> None:
    contents = (
        "<table>\n"
        f"<tr><td>{_TITLE}</td><td>45</td></tr>\n"
        "<tr><td>Consolidated Balance Sheets</td><td>47</td></tr>\n"
        "</table>\n"
    )
    html = contents + _title_block(_COMPANY, _TITLE) + _fact_table()
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert _rows(parsed) == _SERVED
    assert parsed["table_source"] == "carried_title_block"


def test_tbc1_two_title_blocks_in_a_row_carry_once_more() -> None:
    html = _title_block(_COMPANY, _TITLE) + _title_block(_COMPANY, _TITLE) + _fact_table()
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert _rows(parsed) == _SERVED


def test_tbc1_fold_pass_carries_a_case_differing_title_block() -> None:
    html = _title_block(_COMPANY, _TITLE.upper()) + _fact_table()
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert _rows(parsed) == _SERVED
    assert parsed["table_source"] == "carried_title_block"


def test_tbc1_fold_pass_carries_an_allowlisted_qualifier() -> None:
    html = _title_block(_COMPANY, f"{_TITLE} (Unaudited)") + _fact_table()
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert _rows(parsed) == _SERVED


def test_tbc1_list_title_carries_on_normalized_equality() -> None:
    html = _title_block(_COMPANY, _TITLE) + _fact_table()
    parsed = parse_displayed_primary_table(html, title=[_TITLE, "Statements of Income"])
    assert _rows(parsed) == _SERVED
    assert parsed["table_source"] == "carried_title_block"


def test_tbc1_single_line_document_serves() -> None:
    html = (_title_block(_COMPANY, _TITLE) + _fact_table()).replace("\n", "")
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert _rows(parsed) == _SERVED


def test_tbc1_six_row_title_block_still_carries() -> None:
    html = _title_block("Corning", _TITLE, "", "", "", "") + _fact_table()
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert _rows(parsed) == _SERVED


def test_tbc1_next_statement_after_the_capture_is_not_a_split() -> None:
    html = (
        _title_block(_COMPANY, _TITLE)
        + _fact_table()
        + _title_block("Consolidated Balance Sheets")
        + _fact_table(ids=("bs-0", "bs-1"))
    )
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert _rows(parsed) == _SERVED


def test_tbc1_longer_statement_title_after_the_capture_is_not_a_split() -> None:
    html = (
        _title_block(_COMPANY, _TITLE.upper())
        + _fact_table()
        + _title_block(f"{_TITLE} and Comprehensive Income")
        + _fact_table(ids=("ci-0", "ci-1"))
    )
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert _rows(parsed) == _SERVED
    assert parsed["table_source"] == "carried_title_block"


def test_tbc1_carry_pass_returns_only_a_carried_capture() -> None:
    # The carry pass repeats the exact search; a table that search serves on
    # its own is never handed back as carried.
    html = _fact_table(lead_row=f"<tr><td>{_TITLE}</td></tr>")
    assert statement_graph._carried_title_block_parse(html, _TITLE, None) is None


def test_tbc1_title_after_the_next_fact_table_is_not_scanned() -> None:
    html = (
        _title_block(_COMPANY, _TITLE)
        + _fact_table()
        + _fact_table(ids=("other-0", "other-1"))
        + f"<p>{_TITLE}</p>\n"
    )
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert _rows(parsed) == _SERVED


def test_tbc1_hidden_title_after_the_capture_is_ignored() -> None:
    html = (
        _title_block(_COMPANY, _TITLE)
        + _fact_table()
        + f"<ix:hidden><p>{_TITLE}</p></ix:hidden>\n"
    )
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert _rows(parsed) == _SERVED


# --- the carry keeps the refusal ------------------------------------------


def test_tbc1_contents_table_with_page_reference_does_not_carry() -> None:
    contents = (
        f"<table>\n<tr><td>{_COMPANY}</td></tr>\n"
        f"<tr><td>{_TITLE}</td><td>45</td></tr>\n</table>\n"
    )
    _absent(contents + _fact_table())


def test_tbc1_lettered_page_reference_does_not_carry() -> None:
    contents = (
        f"<table>\n<tr><td>{_COMPANY}</td></tr>\n"
        f"<tr><td>{_TITLE}</td><td>F-4</td></tr>\n</table>\n"
    )
    _absent(contents + _fact_table())


def test_tbc1_page_reference_in_its_own_row_does_not_carry() -> None:
    _absent(_title_block(_COMPANY, _TITLE, "F-4") + _fact_table())


def test_tbc1_heading_table_holding_a_fact_does_not_carry() -> None:
    block = (
        "<table>\n"
        '<tr><td>Shares outstanding</td><td><ix:nonFraction name="dei:EntityCommonStockSharesOutstanding"'
        ' contextRef="i2025" id="tbc-sh" unitRef="shares" decimals="0">1,250</ix:nonFraction></td></tr>\n'
        f"<tr><td>{_TITLE}</td></tr>\n"
        "</table>\n"
    )
    _absent(block + _fact_table())


def test_tbc1_title_sharing_its_row_with_other_text_does_not_carry() -> None:
    block = (
        f"<table>\n<tr><td>{_COMPANY}</td></tr>\n"
        f"<tr><td>{_TITLE}</td><td>Years ended</td></tr>\n</table>\n"
    )
    _absent(block + _fact_table())


def test_tbc1_title_with_trailing_words_does_not_carry() -> None:
    _absent(_title_block(_COMPANY, f"{_TITLE} and Comprehensive Income Data") + _fact_table())


def test_tbc1_seven_row_title_block_does_not_carry() -> None:
    _absent(_title_block("Corning", _TITLE, "", "", "", "", "") + _fact_table())


def test_tbc1_caption_table_between_title_block_and_facts_breaks_the_carry() -> None:
    html = _title_block(_COMPANY, _TITLE) + _title_block("(In millions)") + _fact_table()
    _absent(html)


def test_tbc1_title_repeated_after_the_capture_is_a_split() -> None:
    html = _title_block(_COMPANY, _TITLE) + _fact_table() + _title_block(_COMPANY, _TITLE) + _fact_table(
        ids=("p2-0", "p2-1")
    )
    _absent(html)


def test_tbc1_title_paragraph_after_the_capture_is_a_split() -> None:
    _absent(_title_block(_COMPANY, _TITLE) + _fact_table() + f"<p>{_TITLE}</p>\n")


def test_tbc1_exact_pass_still_wins_on_a_titled_later_table() -> None:
    # A title paragraph arms the exact pass on the table after it, exactly as
    # before this pass existed; the carry never runs once the exact pass serves.
    html = _title_block(_COMPANY, _TITLE) + _fact_table() + f"<p>{_TITLE}</p>\n" + _fact_table(
        ids=("p2-0", "p2-1")
    )
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert _rows(parsed) == [{"label": "Net income", "facts": ["p2-0", "p2-1"]}]
    assert "table_source" not in parsed


def test_tbc1_continuation_marker_after_the_capture_is_a_split() -> None:
    html = (
        _title_block(_COMPANY, _TITLE)
        + _fact_table()
        + "<p>(Continued)</p>\n"
        + _fact_table(ids=("p2-0", "p2-1"))
    )
    _absent(html)


def test_tbc1_titled_continuation_cell_after_the_capture_is_a_split() -> None:
    html = (
        _title_block(_COMPANY, _TITLE)
        + _fact_table()
        + _title_block(f"{_TITLE} - Continued")
        + _fact_table(ids=("p2-0", "p2-1"))
    )
    _absent(html)


def test_tbc1_notes_footer_inside_a_heading_table_does_not_carry() -> None:
    # "See accompanying notes" closes a capture while its table is still open;
    # only the end of an outermost table may carry a title block.
    _absent(_title_block(_TITLE, "See accompanying notes.") + _fact_table())


def test_tbc1_layout_wrapper_around_the_title_carries_like_its_rows() -> None:
    # The parser reads nested rows as rows of the outermost table, so a layout
    # wrapper holding only a title block is a factless title block like any other.
    block = (
        "<table><tr><td><table>"
        f"<tr><td>{_COMPANY}</td></tr><tr><td>{_TITLE}</td></tr>"
        "</table></td></tr></table>\n"
    )
    parsed = parse_displayed_primary_table(block + _fact_table(), title=_TITLE)
    assert _rows(parsed) == _SERVED
    assert parsed["table_source"] == "carried_title_block"


def test_tbc1_contents_table_without_page_references_does_not_carry() -> None:
    # A heading table naming another statement is a contents table even when
    # it prints no page numbers; its title row never carries.
    contents = _title_block(
        _COMPANY, "Consolidated Balance Sheets", _TITLE, "Consolidated Statements of Cash Flows"
    )
    _absent(contents + _fact_table())
    _absent(_title_block(_TITLE, "Notes to Consolidated Financial Statements") + _fact_table())


@pytest.mark.parametrize(
    "entity", ["Parent Company Only", "GUARANTOR SUBSIDIARIES", "(Registrant)", "Parent<br>Company"]
)
def test_tbc1_title_block_naming_another_entity_does_not_carry(entity: str) -> None:
    _absent(_title_block(entity, _TITLE) + _fact_table())


def test_tbc1_title_line_broken_across_a_br_is_no_other_statement() -> None:
    # A line naming the declared title, however its words are broken, is not
    # another statement's heading.
    html = _title_block(_COMPANY, _TITLE, "Consolidated Statements of<br>Operations data")
    parsed = parse_displayed_primary_table(html + _fact_table(), title=_TITLE)
    assert _rows(parsed) == _SERVED
    assert parsed["table_source"] == "carried_title_block"


def test_tbc1_other_statement_match_ignores_whitespace() -> None:
    names_other = statement_graph._StatementTableParser._names_other_table
    assert names_other("CONSOLIDATED STATEMENTS OFCOMPREHENSIVE INCOME", False)
    assert names_other("Consolidated BalanceSheets", False)
    assert names_other("ParentCompany Only", True)
    assert not names_other(_TITLE, True)
    assert not names_other(_COMPANY, False)
    assert not names_other("Table of Contents", False)


@pytest.mark.parametrize(
    "between",
    [
        "<p>Consolidated Statements of Comprehensive Income</p>\n",
        "<p>(In millions)</p>\n",
        "<div><span>Years ended September</span></div>\n",
    ],
)
def test_tbc1_text_between_the_title_block_and_the_table_declines_the_carry(
    between: str,
) -> None:
    # Text printed after the block belongs to the table after it, which is
    # then no longer the block's untitled body.
    _absent(_title_block(_COMPANY, _TITLE) + between + _fact_table())


@pytest.mark.parametrize("between", ["<p>&nbsp;</p>\n", "<div>​</div>\n", "<p> </p>\n"])
def test_tbc1_blank_text_between_the_title_block_and_the_table_still_carries(
    between: str,
) -> None:
    parsed = parse_displayed_primary_table(
        _title_block(_COMPANY, _TITLE) + between + _fact_table(), title=_TITLE
    )
    assert _rows(parsed) == _SERVED
    assert parsed["table_source"] == "carried_title_block"


_ENTITY_CONTEXTS = {
    "d2025": frozenset({("dei:LegalEntityAxis", "x:ParentCompanyMember")}),
    "d2024": frozenset({("dei:LegalEntityAxis", "x:ParentCompanyMember")}),
}


@pytest.mark.parametrize("title", [_TITLE, [_TITLE, "Statements of Income"]])
def test_tbc1_carried_table_in_entity_contexts_does_not_carry(title: str | list[str]) -> None:
    # With contexts supplied, a carried table whose facts sit on an entity
    # axis is another entity's statement, on the exact attempt (the only one
    # a list title runs) as on the fold attempt.
    html = _title_block(_COMPANY, _TITLE) + _fact_table()
    with pytest.raises(StatementGraphError) as caught:
        parse_displayed_primary_table(html, title=title, context_dimensions=_ENTITY_CONTEXTS)
    assert caught.value.refusal_code == "displayed_table_absent"
    plain = {"d2025": frozenset(), "d2024": frozenset()}
    parsed = parse_displayed_primary_table(html, title=title, context_dimensions=plain)
    assert _rows(parsed) == _SERVED
    assert parsed["table_source"] == "carried_title_block"


@pytest.mark.parametrize(
    "repeat",
    [
        f"{_TITLE} (Unaudited)",
        f"{_TITLE} (In millions)",
        _TITLE.upper(),
        f"{_COMPANY} {_TITLE}",
        "Consolidated Statements of<br>Operations",
    ],
)
def test_tbc1_qualified_repeat_of_the_title_after_the_capture_is_a_split(repeat: str) -> None:
    html = (
        _title_block(_COMPANY, _TITLE)
        + _fact_table()
        + _title_block(_COMPANY, repeat)
        + _fact_table(ids=("p2-0", "p2-1"))
    )
    _absent(html)


def test_tbc1_title_heading_a_longer_ampersand_title_is_not_a_split() -> None:
    html = (
        _title_block(_COMPANY, _TITLE)
        + _fact_table()
        + _title_block(f"{_TITLE} &amp; Comprehensive Income")
        + _fact_table(ids=("ci-0", "ci-1"))
    )
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert _rows(parsed) == _SERVED


def test_tbc1_rest_of_a_table_closed_mid_table_is_skipped() -> None:
    # "See accompanying notes" closes the carried capture inside its table;
    # the follower skips the rest of that table before looking for a split.
    footer = (
        "<tr><td>See accompanying notes.</td></tr>\n"
        f"<tr><td>{_COMPANY} {_TITLE}</td></tr>\n    </table>"
    )
    html = _title_block(_COMPANY, _TITLE) + _fact_table().replace("</table>", footer)
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert _rows(parsed) == _SERVED
    assert parsed["table_source"] == "carried_title_block"
    _absent(html + _title_block(_COMPANY, _TITLE) + _fact_table(ids=("p2-0", "p2-1")))


# --- a title block prints a companion line --------------------------------


def test_tbc1_bare_title_table_does_not_carry() -> None:
    # A table printing the title and nothing else reads like a contents entry
    # or a bare heading; it stays a discarded factless capture (P5B R3).
    _absent(_title_block(_TITLE) + _fact_table())
    _absent(_title_block("", _TITLE, "") + _fact_table())
    _absent(_title_block(_TITLE.upper()) + _fact_table())


def test_tbc1_a_row_naming_the_title_is_no_companion() -> None:
    named = f"Selected {_TITLE} data"
    _absent(_title_block(_TITLE, named) + _fact_table())
    parsed = parse_displayed_primary_table(
        _title_block(_COMPANY, _TITLE, named) + _fact_table(), title=_TITLE
    )
    assert _rows(parsed) == _SERVED
    assert parsed["table_source"] == "carried_title_block"


@pytest.mark.parametrize(
    "companion",
    [_COMPANY, "(In millions, except per share amounts)", "(Unaudited)", "Table of Contents"],
)
def test_tbc1_any_line_not_naming_the_title_is_a_companion(companion: str) -> None:
    parsed = parse_displayed_primary_table(
        _title_block(_TITLE, companion) + _fact_table(), title=_TITLE
    )
    assert _rows(parsed) == _SERVED
    assert parsed["table_source"] == "carried_title_block"


# --- a carried table printing its own heading keeps its refusal -----------


@pytest.mark.parametrize(
    "lead",
    [
        f"<td>{_TITLE}, extra annotation</td>",
        f"<td>See {_TITLE}, for further discussion</td>",
        f"<td>{_TITLE},</td><td>Note 12, to financial position and ratios</td>",
        f"<td>{_TITLE}.</td>",
        f"<td>{_TITLE.upper()} (CONTINUED FROM ABOVE)</td>",
        (
            f"<td>{_TITLE},"
            '<ix:nonFraction name="us-gaap:Revenues" contextRef="d2025" '
            'id="tbc-title-fact" unitRef="usd" decimals="-6" scale="6">30</ix:nonFraction></td>'
        ),
    ],
)
def test_tbc1_carried_table_naming_the_title_before_its_facts_does_not_carry(
    lead: str,
) -> None:
    # The exact and fold passes and their re-arm rules govern a table that
    # prints its own heading (lane C); the carry never serves it instead.
    _absent(_title_block(_COMPANY, _TITLE) + _fact_table(lead_row=f"<tr>{lead}</tr>"))


def test_tbc1_title_named_after_the_first_fact_still_carries() -> None:
    footer = f"<tr><td>Totals agree to the {_TITLE}</td><td></td><td></td></tr>\n    </table>"
    html = _title_block(_COMPANY, _TITLE) + _fact_table().replace("</table>", footer)
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert parsed["rows"][0]["label"] == "Net income"
    assert parsed["table_source"] == "carried_title_block"


@pytest.mark.parametrize(
    "lead",
    [
        "<td>CONSOLIDATED STATEMENTS OF COMPREHENSIVE INCOME</td>",
        "<td>CONSOLIDATED STATEMENTS OF<br>COMPREHENSIVE INCOME</td>",
        "<td>Statements of<br>Cash Flows</td>",
        "<td>Consolidated Balance Sheets</td>",
        "<td>Parent Company Only</td>",
    ],
)
def test_tbc1_carried_table_naming_another_heading_before_its_facts_does_not_carry(
    lead: str,
) -> None:
    # A table printing another statement's or entity's heading before its
    # first fact has a heading of its own; the block's title is not its title.
    _absent(_title_block(_COMPANY, _TITLE) + _fact_table(lead_row=f"<tr>{lead}</tr>"))


def test_tbc1_other_statement_named_after_the_first_fact_still_carries() -> None:
    footer = "<tr><td>Reconciled to the Consolidated Balance Sheets</td><td></td><td></td></tr>\n    </table>"
    html = _title_block(_COMPANY, _TITLE) + _fact_table().replace("</table>", footer)
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert parsed["rows"][0]["label"] == "Net income"
    assert parsed["table_source"] == "carried_title_block"


# --- the carry builds a grid only for a capture it keeps -------------------

_RAGGED = (
    '<tr><td>Revenue</td><td><ix:nonFraction name="us-gaap:Revenues" contextRef="d2025" '
    'id="tbc-ragged" unitRef="usd" decimals="-6" scale="6">5</ix:nonFraction></td></tr>'
)


def test_tbc1_declined_carry_never_reaches_the_grid() -> None:
    # A split declines the carry before any grid is built, so a ragged
    # carried table keeps the exact pass's absent refusal.
    html = _title_block(_COMPANY, _TITLE) + _fact_table(lead_row=_RAGGED) + f"<p>{_TITLE}</p>\n"
    _absent(html)


def test_tbc1_kept_carry_refuses_an_unsupported_layout() -> None:
    # A kept carried table is the statement; its layout is judged like any
    # captured table's.
    with pytest.raises(StatementGraphError) as caught:
        parse_displayed_primary_table(
            _title_block(_COMPANY, _TITLE) + _fact_table(lead_row=_RAGGED), title=_TITLE
        )
    assert caught.value.refusal_code == "displayed_layout_unsupported"


# --- the exact and fold passes are unchanged -------------------------------


def test_tbc1_titled_fact_table_never_runs_the_carry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("carry pass ran")

    monkeypatch.setattr(statement_graph, "_carried_title_block_parse", refuse)
    html = _fact_table(lead_row=f"<tr><td>{_TITLE}</td></tr>")
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert _rows(parsed) == _SERVED
    assert "table_source" not in parsed


def test_tbc1_exact_and_fold_parsers_never_note_title_block_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("noted a title-block row outside the carry pass")

    monkeypatch.setattr(statement_graph._StatementTableParser, "_note_title_block_row", refuse)
    monkeypatch.setattr(
        statement_graph, "_carried_title_block_parse", lambda *_args, **_kwargs: None
    )
    _absent(_title_block(_COMPANY, _TITLE) + _fact_table())
    html = _fact_table(lead_row=f"<tr><td>{_TITLE.upper()}</td></tr>")
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert _rows(parsed) == _SERVED


def test_tbc1_no_title_anywhere_keeps_the_refusal() -> None:
    _absent(_title_block(_COMPANY, "Consolidated Balance Sheets") + _fact_table())


def test_tbc1_title_block_without_a_following_fact_table_keeps_the_refusal() -> None:
    _absent(_title_block(_COMPANY, _TITLE) + "<p>No statement follows.</p>")


# --- guards the mutation pass found unexercised ------------------------------


def test_tbc1_comma_variant_title_after_a_discard_arms_no_carry() -> None:
    # After a discarded bare heading (P5B R3) a row hits on its text with a
    # trailing comma dropped, but only the title alone arms the carry:
    # "Title," is a title plus a suffix the fold does not accept.
    _absent(
        _title_block(_TITLE) + _title_block(_COMPANY, f"{_TITLE},") + _fact_table()
    )


def test_tbc1_title_repeated_after_a_longer_title_in_one_cell_is_a_split() -> None:
    # The first occurrence heads a longer title; the second, in the same text,
    # repeats the title itself, so the block after the capture is a split.
    html = (
        _title_block(_COMPANY, _TITLE)
        + _fact_table()
        + _title_block(f"{_TITLE} and Comprehensive Income; {_TITLE} (Unaudited)")
        + _fact_table(ids=("p2-0", "p2-1"))
    )
    _absent(html)


def test_tbc1_caption_inside_the_carried_table_still_carries() -> None:
    # Text inside the carried table itself is that table's own content, not a
    # heading printed between the block and the table.
    html = _title_block(_COMPANY, _TITLE) + _fact_table(
        lead_row="<caption>(In millions)</caption>"
    )
    parsed = parse_displayed_primary_table(html, title=_TITLE)
    assert _rows(parsed) == _SERVED
    assert parsed["table_source"] == "carried_title_block"
