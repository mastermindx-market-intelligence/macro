"""CDV-1 T1 F1-Q envelope — frozen R6 witness (seat-frozen after the independent Opus re-audit R6 of 135a67a3e12).

Every case edits a frozen gzipped FY26 Q1-Q3 original in memory and asserts the outcome that the bytes and the seat
rulings R116-R167 and R168-R178 require.  G3 found a value bound under one of two year columns it spans (B1), a unit
cell read past an invisible format character (B2), and a header value naming a second year in a form other than 20dd
(B3).  G1 found end tags a reader reads as closing a cell (B1, '</tbody>'), references `html.unescape` drops that a
reader prints (B2), an element html5lib expands into printed text (B3, '<isindex>'), and the prior-year note read from
raw text a reader does not print (M1).  G4 found a relocation onto a literal glued to printed text through markup
accepted (B1) and twelve R163 branches without an isolating witness (m2).  G2 found the span check's limit wider than
R166's list (B1), a tampered row raising where it must refuse (B2), and replay equality blind to a JSON type change
(m1).  The seat found the engine decoding printed text twice (S1), and characters Python 3.12 and 3.14 read
differently because their Unicode versions differ (S2).

R168 reads the pin at every grid position a value occupies: every column it spans sits under the pin's header, year and
period, and every row it spans carries the pin's label.  R169 reads a unit cell by what a reader sees of it.  R170
reads every year a header value names, in any form, and names none where a numeral it cannot read as a year remains.
R171 refuses a table-section or '<isindex>' tag.  R172 refuses a cell printing a character html.unescape drops or a
control or odd space.  R173 reads the prior-year note only from printed text.  R174 accepts a span only where it is a
whole printed token.  R175 decodes printed text once.  R176 restates R155/R166's limit as a rule, refuses every
tampered row without raising, and compares canonical JSON text.  R177 freezes this file and witnesses each R163 branch
that had no isolating witness.  R178 refuses a document holding a character Unicode 3.2 does not assign, before any
admission check that reads printed text, and reads every character Unicode 3.2 files as an other letter as a possible
figure.

The constructions are the auditors' (G1-G4), widened by the seat to each rule's controls; R178's are the seat's.  Every
case drives the public path (build_event_workspace, validate_selected_facts) except the relocations, which patch the
shared receipts API that R143 names as the only place a wrapped receipt is minted.

Rulings: research/consumer_defensive/cdv1_program/reviews/SEAT_RULING_T1_ENVELOPE_R6_2026-09-25.md.
Audit record: research/consumer_defensive/cdv1_program/reviews/OPUS_T1_ENVELOPE_AUDIT_R6_2026-09-25.md.
"""
from __future__ import annotations

import copy
import re
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_pg_envelope_f1 as t  # noqa: E402
import test_pg_envelope_f1_probes_r1 as r1  # noqa: E402
import test_pg_envelope_f1_probes_r4 as r4  # noqa: E402
import test_pg_envelope_f1_probes_r5 as r5  # noqa: E402
from engine.company_intelligence import pg_envelope as pe  # noqa: E402
from engine.company_intelligence.economic_observations import (  # noqa: E402
    EconomicObservationError,
    validate_selected_facts,
)

REL = r4.REL
QUARTERS = sorted(REL)


def binds_everything(body, q="Q3"):
    ws, texts, _ = r4.build(body, q)
    return r1.numeric(ws) == t.expected_values(REL[q]) and r1.validates(ws, texts, REL[q])


def unlocated(body, q, *metrics):
    """Each metric is unlocated, and the workspace validates."""
    ws, texts, _ = r4.build(body, q)
    got = r1.numeric(ws)
    return [got[metric] for metric in metrics] == [t.UNLOCATED] * len(metrics) and r1.validates(ws, texts, REL[q])


def binds(body, q, metric):
    """The metric binds its frozen value, and the workspace validates."""
    ws, texts, _ = r4.build(body, q)
    return r1.numeric(ws)[metric] == t.expected_values(REL[q])[metric] and r1.validates(ws, texts, REL[q])


def refusal(body, q="Q3"):
    ws, texts, _ = r4.build(body, q)
    return r1.refusal_details(ws), r1.validates(ws, texts, REL[q])


def pinned(body, q, metric, k=0):
    return t.one(body, r4.pin(q, metric, k))


def element(body, c):
    """The <td> or <th> element that holds cell `c`: its start, the end of its opening tag, and its end."""
    start = max(body.rfind("<td", 0, c.start), body.rfind("<th", 0, c.start))
    tag_end = body.index(">", start) + 1
    assert tag_end == c.start, (start, tag_end, c.start)
    return start, tag_end, body.index(">", c.end) + 1


def right_of(body, c):
    """The cell that starts where `c` ends, in `c`'s own row."""
    return next(other for other in t.grid(body, c.table)[c.row] if other.row == c.row and other.col0 == c.col1)


def relocated(monkeypatch, fragment, literal="1.63"):
    """`fragment` inserted before the Q3 '</TEXT>', and the Q3 diluted-EPS receipt relocated through R143's seam onto
    the `literal` in it."""
    body = r5.before_text_end(r5.src(), fragment)
    at = r5.text_end(r5.src()) + fragment.index(literal)
    r4.reseat(monkeypatch, body, r4.spans("Q3")[t.DIL], (at, at + len(literal)))
    return body


# ============================ R168 (G3-B1): the pin is read alike at every grid position a value occupies
def widen_over_next_year(q, body, metric, k):
    """The pinned cell's colspan grows to also cover the next year's column, and the cells it now covers are removed."""
    loc = r4.pin(q, metric, k)
    c, g = t.one(body, loc), t.grid(body, loc[0])
    year = min(
        (x for row in g[:c.row] for x in row
         if re.fullmatch(r"20\d\d", x.text) and x.text != loc[2] and x.col0 >= c.col1),
        key=lambda x: x.col0,
    )
    covered = [x for x in g[c.row] if x.row == c.row and x.col0 >= c.col1 and x.col1 <= year.col1]
    start, tag_end, _ = element(body, c)
    tag = body[start:tag_end]
    width = f'colspan="{year.col1 - c.col0}"'
    wide = re.sub(r'colspan="\d+"', width, tag) if "colspan" in tag else tag[:-1] + f" {width}>"
    return r5.splice(body, (start, tag_end, wide), *((element(body, x)[0], element(body, x)[2], "") for x in covered))


@pytest.mark.parametrize("q,metric,k", [
    ("Q3", t.DIL, 1), ("Q3", t.CORE, 1), ("Q3", t.DIL, 0), ("Q1", t.DIL, 0), ("Q2", t.CORE, 1),
])
def test_r168_a_value_spanning_two_year_columns_is_unlocated(q, metric, k):
    """R168 (G3-B1, enforces R147/R156): the pinned cell spans its own year's column and the next year's.  A reader
    reads it under both years; the engine read the year over its first column alone and bound it at 135a67a3e12."""
    assert unlocated(widen_over_next_year(q, r4.src(q), metric, k), q, metric)


def test_r168_control_a_value_spanning_two_columns_of_its_own_year_binds():
    """R168 control: the Q3 1.63 cell spans its own column and the empty column after it, both under its year, header
    and period.  Every column it occupies reads the pin alike, and the document binds every frozen value."""
    body = r5.src()
    value = r5.dil(body)
    after = right_of(body, value)
    assert after.text == ""
    start, tag_end, _ = element(body, value)
    after_start, _, after_end = element(body, after)
    wide = body[start:tag_end][:-1] + ' colspan="2">'
    assert binds_everything(r5.splice(body, (start, tag_end, wide), (after_start, after_end, "")))


def spanning_the_blank_row(label):
    """The Q3 1.63 cell spans the Diluted row and the blank row after it.  The blank row prints `label` in its first
    cell and keeps the table's eighteen columns around the column the value covers."""
    body = r5.src()
    blank = r5.row(body, 1)
    return r5.splice(
        body,
        r5.open_tag(body, r5.dil(body), "<td", '<td rowspan="2"'),
        (blank.start(), blank.end(), f'<tr><td colspan="3">{label}</td><td></td><td colspan="13"></td></tr>'),
    )


@pytest.mark.parametrize("label", ["Basic", ""])
def test_r168_a_value_spanning_a_row_with_another_label_or_none_is_unlocated(label):
    """R168: the second row the 1.63 cell spans prints `label` ('' prints none).  A reader reads the value beside that
    row as well; the engine read the label of the value's first row alone and bound DIL at 135a67a3e12."""
    assert unlocated(spanning_the_blank_row(label), "Q3", t.DIL)


def test_r168_control_a_value_spanning_two_rows_that_print_its_label_binds():
    """R168 control: both rows the 1.63 cell spans print 'Diluted'.  Every row it occupies carries the pin's label,
    and the document binds every frozen value."""
    assert binds_everything(spanning_the_blank_row("Diluted"))


# ============================ R169 (G3-B2): a unit cell is read by what a reader sees of it
INVISIBLE = ["$&#8203;", "&#8203;$", "$&#65279;", "$&#173;"]


@pytest.mark.parametrize("form", INVISIBLE)
@pytest.mark.parametrize("q", QUARTERS)
def test_r169_a_dollar_cell_with_an_invisible_character_beside_a_percent_value_leaves_it_unlocated(q, form):
    """R169 (G3-B2, enforces R159/R164): the cell right of the reported-sales-growth value prints `form`, which a
    reader sees as '$'.  The engine compared the raw text with {'$', '%'} and bound the percent at 135a67a3e12."""
    body = r4.src(q)
    right = right_of(body, pinned(body, q, t.SALES))
    assert unlocated(r5.splice(body, (right.start, right.end, form)), q, t.SALES)


@pytest.mark.parametrize("q", QUARTERS)
def test_r169_a_zero_width_cell_does_not_shield_the_unit_beyond_it(q):
    """R169 (G3-B2): the cell right of the reported-sales-growth value prints only a zero-width space and the next
    prints '$'.  A reader sees no printed cell between the value and '$'; the engine took the empty-looking cell as
    the nearest neighbour."""
    body = r4.src(q)
    first = right_of(body, pinned(body, q, t.SALES))
    second = right_of(body, first)
    edited = r5.splice(body, (first.start, first.end, "&#8203;"), (second.start, second.end, "$"))
    assert unlocated(edited, q, t.SALES)


@pytest.mark.parametrize("form", ["%&#8203;", "&#8203;%", "%&#65279;", "%&#173;"])
@pytest.mark.parametrize("q", QUARTERS)
def test_r169_control_a_percent_cell_with_an_invisible_character_beside_a_percent_value_binds(q, form):
    """R169 control: the cell right of the reported-sales-growth value prints `form`, which a reader sees as '%'.  The
    percent unit admits it, and the value binds.  (A '$&#8203;' cell beside a per-share value is no control: `_locate`
    reads its raw text as a second candidate under the value's label, at 135a67a3e12 and after R169 alike, and the
    value stays unlocated.)"""
    body = r4.src(q)
    right = right_of(body, pinned(body, q, t.SALES))
    assert binds(r5.splice(body, (right.start, right.end, form)), q, t.SALES)


# ============================ R170 (G3-B3): every year a header value names, in any form
def banner(q, body, role, value):
    """A first row across the whole `role` table printing `value`."""
    ordinal = r4.TAB[q][role]
    start = t.tables(body)[ordinal][0]
    width = max(x.col1 for row in t.grid(body, ordinal) for x in row)
    at = body.index("<tr", start)
    return body[:at] + f'<tr><td colspan="{width}">{value}</td></tr>' + body[at:]


TWO_YEAR_BANNERS = [
    "2025/26", "2025-26", "2025&#8211;26", "20252026",
    "&#1634;&#1632;&#1634;&#1638;", "&#65298;&#65296;&#65298;&#65302;", "'26",
]


@pytest.mark.parametrize("value", TWO_YEAR_BANNERS)
@pytest.mark.parametrize("q", QUARTERS)
def test_r170_a_banner_naming_a_second_year_in_another_form_leaves_the_prior_year_pins_unlocated(q, value):
    """R170 (G3-B3, enforces R156/R165): a banner across the highlights table names FY26 in a form other than a bare
    ASCII 20dd.  The prior-year pins sit under it and under their own 2025 header; the engine read no year from the
    banner and bound both at 135a67a3e12."""
    assert unlocated(banner(q, r4.src(q), "highlights", value), q, t.PDIL, t.PCORE)


@pytest.mark.parametrize("y", ["2025 (1)", "2025(1)", "(1) 2025"])
def test_r170_control_a_year_header_with_a_footnote_marker_names_its_year(y):
    """R170 control: R156's highlights row printing `y` over the Q3 2025 columns.  A footnote marker is neither a year
    nor an unread numeral; the header names 2025 alone, and the document binds every frozen value."""
    body = r4.insert_row_after(r4.src("Q3"), r4.TAB["Q3"]["highlights"], 2, r4.HIGHLIGHTS_2025_COLUMNS.format(y=y))
    assert binds_everything(body)


# ============================ R171 (G1-B1, G1-B3): a table-section or '<isindex>' tag refuses the document
def label_of(body, c):
    return next(other for other in t.grid(body, c.table)[c.row] if other.row == c.row and other.col0 == 0)


TBODY = [
    ("Q3", t.DIL, "label", "</tbody>"), ("Q3", t.DIL, "value", "</tbody>"), ("Q3", t.DIL, "label", "</TBODY >"),
    ("Q1", t.SALES, "label", "</tbody>"), ("Q2", t.CORE, "label", "</tbody>"), ("Q3", t.BEAUTY, "label", "</tbody>"),
    ("Q2", t.PDIL, "value", "</tbody>"), ("Q1", t.ORG, "label", "</tbody>"),
]


@pytest.mark.parametrize("q,metric,where,tag", TBODY)
def test_r171_a_table_section_end_tag_in_a_cell_refuses_the_document(q, metric, where, tag):
    """R171 (G1-B1): `tag` at the end of the pinned cell or of its label cell.  A reader closes the cell, the row and
    the implied body there and lays the rest of the row out as a new row; the engine ignored the end tag in a cell
    and bound every value at 135a67a3e12."""
    body = r4.src(q)
    c = pinned(body, q, metric)
    at = (label_of(body, c) if where == "label" else c).end
    assert refusal(body[:at] + tag + body[at:], q) == r5.unreadable("table")


@pytest.mark.parametrize("q,metric", [("Q3", t.DIL), ("Q1", t.SALES), ("Q2", t.CORE)])
def test_r171_isindex_in_a_pinned_cell_refuses_the_document(q, metric):
    """R171 (G1-B3): '<isindex>' after the pinned literal.  html5lib 1.1 expands it into a form with printed text in
    the cell; the engine read it as a void tag and bound every value at 135a67a3e12."""
    body = r4.src(q)
    _, end = r4.spans(q)[metric]
    assert refusal(body[:end] + "<isindex>" + body[end:], q) == r5.unreadable("element")


# ============================ R172 (G1-B2, G1-m2): a cell printing a dropped reference or an odd character
DROPPED = [
    ("Q3", t.DIL, "&#xFFFF;", "before"), ("Q3", t.DIL, "&#127;", "after"), ("Q2", t.CORE, "&#1;", "before"),
    ("Q1", t.BEAUTY, "&#xFDD0;", "before"), ("Q3", t.SALES, "&#x8;", "after"), ("Q3", t.DIL, "&#11;", "before"),
]


@pytest.mark.parametrize("q,metric,reference,side", DROPPED)
def test_r172_a_reference_the_engine_drops_beside_a_pinned_literal_refuses_the_document(q, metric, reference, side):
    """R172 (G1-B2, G1-m2): `reference` beside the pinned literal.  A reader prints U+FFFF, U+007F, U+0001, U+FDD0,
    U+0008 or U+000B glued to the literal; `html.unescape` dropped it and the engine bound the bare literal at
    135a67a3e12."""
    body = r4.src(q)
    start, end = r4.spans(q)[metric]
    at = start if side == "before" else end
    assert refusal(body[:at] + reference + body[at:], q) == r5.unreadable("character")


@pytest.mark.parametrize("prefix", ["&#160;", "\xa0", "&#32;\t"])
def test_r172_control_a_space_a_reader_prints_as_layout_before_a_pinned_literal_binds(prefix):
    """R172 control: `prefix` before the Q3 diluted-EPS literal is layout to a reader.  The document binds every frozen
    value."""
    body = r5.src()
    start, _ = r4.spans("Q3")[t.DIL]
    assert binds_everything(body[:start] + prefix + body[start:])


# ============================ R173 (G1-M1): the prior-year note is read only from printed text
def moved_note(wrap):
    """The Q3 'no adjustments' note after the core reconciliation, replaced by its plain sentence inside `wrap`."""
    body = r5.src()
    i = body.index("no adjustments to or reconciling items")
    start, end = body.rindex("(1)", 0, i), body.index("EPS.", i) + len("EPS.")
    return body[:start] + wrap.format(t.NO_ADJUSTMENT_NOTE["FY26Q3"]) + body[end:]


@pytest.mark.parametrize("wrap", ["<script>{}</script>", "<style>{}</style>", "<title>{}</title>"])
def test_r173_the_prior_year_note_inside_raw_text_leaves_prior_core_eps_unlocated(wrap):
    """R173 (G1-M1, enforces R157): the note sits in script, style or title text between the core reconciliation and
    the next table.  A reader prints none of it; `_prior_note_present` read it through `_text` and bound PCORE at
    135a67a3e12."""
    assert unlocated(moved_note(wrap), "Q3", t.PCORE)


def test_r173_control_the_prior_year_note_in_a_paragraph_binds():
    """R173 control: the same sentence in a paragraph is printed, and the document binds every frozen value."""
    assert binds_everything(moved_note("<p>{}</p>"))


# ============================ R174 (G4-B1): a span is a whole printed token
GLUED_BY_MARKUP = {
    "digit_then_empty_inline_element": "<p>9<b></b>1.63</p>",  # a reader prints '91.63'
    "minus_then_empty_inline_element": "<p>-<b></b>1.63</p>",  # '-1.63'
    "digit_then_comment": "<p>9<!-- c -->1.63</p>",  # '91.63'
    "literal_then_inline_digit": "<p>1.63<b>9</b></p>",  # '1.639'
    "digit_then_empty_italic": "<p>2<i></i>1.63</p>",  # '21.63'
}


@pytest.mark.parametrize("form", sorted(GLUED_BY_MARKUP))
def test_r174_a_relocation_onto_a_literal_glued_by_markup_is_refused(monkeypatch, form):
    """R174 (G4-B1): the Q3 diluted-EPS receipt relocated through R143's seam onto '1.63' where a reader prints it as
    part of a longer token.  R163 admits the markup; the span check read the bytes between the literal and its
    neighbour, not what a reader prints, and accepted it at 135a67a3e12."""
    body = relocated(monkeypatch, GLUED_BY_MARKUP[form])
    assert pe._unreadable_markup(body) is None
    ws, texts, _ = r4.build(body)
    assert r4.excerpt(ws, t.DIL) == "1.63", "wrapped receipts are minted via receipt_for_char_span"
    assert not r1.validates(ws, texts)


SEPARATED_BY_MARKUP = {
    "own_paragraph": "<p>1.63</p>",
    "paragraph_after_text": "<p>9</p><p>1.63</p>",
    "line_break_after_text": "<p>9<br>1.63</p>",
    "space_after_an_inline_element": "<p><b>9</b> 1.63</p>",
}


@pytest.mark.parametrize("form", sorted(SEPARATED_BY_MARKUP))
def test_r174_control_a_relocation_onto_a_literal_a_reader_prints_alone_is_accepted(monkeypatch, form):
    """R174 control (inside R176's restated limit): the literal is a whole printed token, set off by a paragraph, a
    line break or a space.  The relocation is accepted."""
    body = relocated(monkeypatch, SEPARATED_BY_MARKUP[form])
    ws, texts, _ = r4.build(body)
    assert r4.excerpt(ws, t.DIL) == "1.63"
    assert r1.validates(ws, texts)


# ============================ R175 (seat S1): printed text is decoded once
EARNINGS_TABLE_UNKNOWN = ({"envelope_refused:unknown_table:t4"}, True)


def diluted_label(reference):
    """The Q3 Diluted label's source with `reference` appended to its text."""
    body = r5.src()
    label = r5.label(body)
    raw = body[label.start:label.end]
    assert raw.count(">Diluted<") == 1
    return r5.splice(body, (label.start, label.end, raw.replace(">Diluted<", f">Diluted{reference}<")))


def earnings_title(space):
    """The Q3 earnings title with `space` in place of the space in 'March 31'."""
    body = r5.src()
    start, end = t.tables(body)[r5.TAB["earnings"]]
    at = body.index("Three Months Ended March 31", start, end) + len("Three Months Ended March")
    return body[:at] + space + body[at + 1:]


def test_r175_a_label_printing_a_reference_as_text_leaves_the_earnings_table_unknown():
    """R175 (S1): the Q3 Diluted label's source is 'Diluted&amp;#160;', which a reader prints as 'Diluted&#160;'.
    `_norm` decoded the printed text a second time, read 'Diluted', and bound DIL at 135a67a3e12.  Read once, the table
    no longer reads as the earnings table, and the document is refused."""
    assert refusal(diluted_label("&amp;#160;")) == EARNINGS_TABLE_UNKNOWN


def test_r175_a_period_title_printing_a_reference_as_text_leaves_the_earnings_table_unknown():
    """R175 (S1): the Q3 earnings title's source is 'March&amp;#160;31', which a reader prints as 'March&#160;31'.
    `_parse_period_title` replaced the printed '&#160;' and read a period at 135a67a3e12.  Read once, the title names
    no period, the table no longer reads as the earnings table, and the document is refused."""
    assert refusal(earnings_title("&amp;#160;")) == EARNINGS_TABLE_UNKNOWN


def test_r175_control_a_reference_the_source_holds_is_decoded_once():
    """R175 control: the label's source is 'Diluted&#160;' and the title's 'March&#160;31', which a reader prints with
    a no-break space.  One decode reads both, and the document binds every frozen value either way."""
    assert binds_everything(diluted_label("&#160;"))
    assert binds_everything(earnings_title("&#160;"))


# ============================ R176 (G2-B1, G2-B2, G2-m1): the limit as a rule, refusal without raising, JSON text
def relocated_into(monkeypatch, where, make):
    """G2's relocations: the Q3 diluted-EPS receipt relocated through R143's seam onto a '1.63' at `where`."""
    body = r4.src("Q3")
    old = r4.spans("Q3")[t.DIL]
    literal = body[old[0]:old[1]]
    assert literal == "1.63"
    if where == "description":
        i = body.index("<DESCRIPTION>") + len("<DESCRIPTION>")
        edited = body[:i] + literal + body[body.index("\n", i):]
        new = (i, i + len(literal))
    else:
        at = r5.text_end(body) if where == "text_end" else body.lower().rindex("</html>") + len("</html>")
        fragment = make(literal)
        edited = body[:at] + fragment + body[at:]
        new = (at + fragment.index(literal), at + fragment.index(literal) + len(literal))
    r4.reseat(monkeypatch, edited, old, new)
    return edited


INSIDE_THE_RULE = {
    "wrapper_description_header": ("description", None),
    "prose_paragraph": ("text_end", lambda x: f"<p>{x}</p>"),
    "bare_text_before_text_end": ("text_end", lambda x: f"\n{x}\n"),
    "text_after_html_end": ("after_html", lambda x: f"<p>{x}</p>"),
    "title_outside_tables": ("text_end", lambda x: f"<title>{x}</title>"),
    "textarea_outside_tables": ("text_end", lambda x: f"<textarea>{x}</textarea>"),
    "xmp_outside_tables": ("text_end", lambda x: f"<xmp>{x}</xmp>"),
    "iframe_outside_tables": ("text_end", lambda x: f"<iframe>{x}</iframe>"),
    "noscript_outside_tables": ("text_end", lambda x: f"<noscript>{x}</noscript>"),
    "noembed_outside_tables": ("text_end", lambda x: f"<noembed>{x}</noembed>"),
    "noframes_outside_tables": ("text_end", lambda x: f"<noframes>{x}</noframes>"),
}


@pytest.mark.parametrize("case", sorted(INSIDE_THE_RULE))
def test_r176_a_relocation_onto_a_whole_printed_token_outside_the_tables_is_accepted(monkeypatch, case):
    """R176 (G2-B1, restates R155/R166's limit as a rule): the span check proves only that the span is a whole token of
    the text the engine reads (R174's units) that parses to the value.  It proves neither that a reader shows that
    text nor where it sits; placement is replay's job (R143).  Through the seam, which replaces replay's receipt, a
    relocation onto such a token in the wrapper header, in prose, after '</html>' or in raw text outside the tables is
    accepted, before and after R168-R176."""
    where, make = INSIDE_THE_RULE[case]
    body = relocated_into(monkeypatch, where, make)
    assert pe.admit(body, REL["Q3"].scope).code == "F1-Q"
    ws, texts, _ = r4.build(body)
    assert r4.excerpt(ws, t.DIL) == "1.63"
    assert r1.validates(ws, texts)


def tamper(ws, present, path, value):
    ws = copy.deepcopy(ws)
    row = next(r for r in t.pg_rows(ws) if ("value" in r) == present)
    target = row
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return ws


@pytest.mark.parametrize("which,path,value", [
    ("refused", ("typed_absence", "missing_fields"), 5),
    ("refused", ("typed_absence", "reason"), {}),
    ("refused", ("typed_absence", "detail"), Decimal("1")),
    ("present", ("source_span", "rights_profile"), {1}),
])
def test_r176_a_row_holding_a_value_json_cannot_carry_is_refused_not_raised(which, path, value):
    """R176 (G2-B2, enforces R134): a selected row whose field holds 5, {}, Decimal('1') or {1} where the replay holds
    JSON data.  The validator raised TypeError at 135a67a3e12; it refuses with EconomicObservationError."""
    body = r5.comment_in_dil(r5.src(), "<!-->") if which == "refused" else r5.src()
    ws, texts, _ = r4.build(body)
    with pytest.raises(EconomicObservationError):
        validate_selected_facts(tamper(ws, which == "present", path, value), source_texts=texts,
                                fiscal_scope=REL["Q3"].scope)


@pytest.mark.parametrize("path,convert", [
    (("value",), int),
    (("source_span", "receipt", "segment_bytes"), float),
    (("source_span", "locator", "span_start_byte"), float),
])
def test_r176_a_field_whose_json_type_changes_is_refused(path, convert):
    """R176 (G2-m1, enforces R136): a present Q1 row whose field serialises differently from the replay ('5' against
    '5.0').  Python equality accepted it at 135a67a3e12; the canonical JSON text differs."""
    ws, texts, _ = r4.build(r4.src("Q1"), "Q1")
    ws = copy.deepcopy(ws)
    row = next(r for r in t.pg_rows(ws) if "value" in r and float(r["value"]).is_integer())
    target = row
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = convert(target[path[-1]])
    assert not r1.validates(ws, texts, REL["Q1"])


def test_r176_control_a_list_held_as_a_tuple_validates():
    """R176 control (R136): a refused row's missing_fields held as a tuple serialises as the list it replays to, and
    the workspace validates."""
    ws, texts, _ = r4.build(r5.comment_in_dil(r5.src(), "<!-->"))
    row = next(r for r in t.pg_rows(ws) if "value" not in r)
    held = tamper(ws, False, ("typed_absence", "missing_fields"), tuple(row["typed_absence"]["missing_fields"]))
    assert r1.validates(held, texts)


# ============================ R177 (G4-m2): a witness for each R163 branch no earlier case isolates
def table_unclosed_at_the_end(body):
    """The source ends inside the last table, after its last row: its '</table>' and everything after are gone."""
    return body[:body.lower().rindex("</table>")]


def before_row_end(body, fragment):
    """`fragment` inserted just before the Q3 Diluted row's own '</tr>'."""
    found = r5.row(body, 0)
    at = body.lower().rindex("</tr", found.start(), found.end())
    return body[:at] + fragment + body[at:]


def before_earnings_close(body, fragment):
    """`fragment` inserted just before the Q3 earnings table's '</table>', after its last row."""
    at = r5.earnings_close(body)
    return body[:at] + fragment + body[at:]


SPAN, ROWSPAN_OVER = 'colspan="3"', '<td rowspan="65535"'
ISOLATED = {
    "raw_text_unclosed": ("element", lambda s: r5.before_text_end(s, "<script>var a = 1;")),
    "start_tag_between_rows": ("table", lambda s: r5.after_row(s, "<br></tr>")),
    "start_tag_in_a_row": ("table", lambda s: r5.after_open_tr(s, "<p></p>")),
    "end_tag_between_rows": ("table", lambda s: before_earnings_close(s, "</b>")),
    "end_tag_in_a_row": ("table", lambda s: before_row_end(s, "</b><tr>")),
    "row_end_inside_a_cell": ("table", lambda s: r5.dil_content(s, "1.63</tr>")),
    "table_unclosed_at_the_end": ("table", table_unclosed_at_the_end),
    "rowspan_over_the_limit": ("span", lambda s: r5.splice(s, r5.open_tag(s, r5.cell(s, -1, 3), "<td", ROWSPAN_OVER))),
    "span_repeated_alike": ("span", lambda s: r5.splice(s, r5.open_tag(s, r5.label(s), SPAN, SPAN + " " + SPAN))),
    "span_the_engine_reads_from_another_attribute": (
        "span", lambda s: r5.splice(s, r5.open_tag(s, r5.label(s), SPAN, 'title="colspan=4" ' + SPAN))),
}


@pytest.mark.parametrize("case", sorted(ISOLATED))
def test_r177_each_r163_branch_has_a_witness_of_its_own(case):
    """R177 (G4-m2): each construct reaches one R163 branch that no R5 case reaches alone: raw text never closed, a
    start or end tag other than a row's between rows or a cell's in a row, a row end inside a cell, a table the source
    never closes, a rowspan over HTML's limit, a span given twice alike, and a span the engine reads from another
    attribute.  The document is refused with that branch's kind before and after R168-R176.  Each tag construct is
    built so that, read as the tag its branch expects ('<br>' as a row, '<p>' as a cell, '</b>' as the table's or the
    row's end), the rest of the source is well formed: with that branch removed and every other branch kept, the
    document is admitted."""
    kind, make = ISOLATED[case]
    assert refusal(make(r5.src())) == r5.unreadable(kind)


EARLIER_CHECKS = ["type_ex_99_2", "generator_removed", "masthead_other_issuer", "table_injected", "drivers_removed",
                  "drivers_repeated", "q3_under_q2_scope"]


def refused_with(case, addition):
    """The frozen FY26 Q3 refusal case `case`, with `addition` placed after the tables, built and validated under the
    case's own period: its refusal details, and whether the workspace validates."""
    release, rewrite, period, _ = t.REFUSED[case]
    assert release is t.FY26Q3
    body = r5.before_text_end(r5.src(), addition)
    ws, texts, _ = t.workspace(release, rewrite(body) if rewrite else body, period)
    return r1.refusal_details(ws), r1.validates(ws, texts, period)


@pytest.mark.parametrize("case", EARLIER_CHECKS)
def test_r177_r163_runs_after_every_earlier_admission_check(case):
    """R177 (G4-m2, breadth of R163's order witness): the frozen refusal case with a text '>' added after the tables
    keeps its own code, so R163 runs after every earlier admission check: the filing type, the generator, the issuer,
    the table signatures, the required roles and the reported quarter."""
    assert refused_with(case, "<p>9>1.63</p>") == ({t.REFUSED[case][3]}, True)


# ============================ R178 (seat S2): the envelope reads its characters alike on Python 3.12 and 3.14
LATER_DIGITS = ["&#x11BF2;&#x11BF0;&#x11BF2;&#x11BF6;", "&#x1CCF2;&#x1CCF0;&#x1CCF2;&#x1CCF6;"]
HIGHLIGHTS_EPS = (t.DIL, t.PDIL, t.REPG, t.CORE, t.PCORE, t.COREG)
HEAVY_DOLLAR = "<p>&#x1F4B2;</p>"


def exactly_unlocated(body, q, *metrics):
    """Exactly `metrics` are unlocated, every other frozen value binds, and the workspace validates."""
    ws, texts, _ = r4.build(body, q)
    expected = {**t.expected_values(REL[q]), **dict.fromkeys(metrics, t.UNLOCATED)}
    return r1.numeric(ws) == expected and r1.validates(ws, texts, REL[q])


@pytest.mark.parametrize("q", QUARTERS)
def test_r178_a_cell_printing_a_character_unicode_3_2_does_not_assign_refuses_the_document(q):
    """R178 (seat S2): the cell right of the reported-sales-growth value prints only U+1CCF0 OUTLINED DIGIT ZERO, which
    Unicode 16.0 assigns, and the next prints '$'.  After R169 the value was unlocated on Python 3.12 (Unicode 15.0) and
    bound on Python 3.14 (Unicode 16.0).  The document is refused on both."""
    body = r4.src(q)
    first = right_of(body, pinned(body, q, t.SALES))
    second = right_of(body, first)
    edited = r5.splice(body, (first.start, first.end, "&#x1CCF0;"), (second.start, second.end, "$"))
    assert refusal(edited, q) == r5.unreadable("character")


@pytest.mark.parametrize("value", LATER_DIGITS)
@pytest.mark.parametrize("q", QUARTERS)
def test_r178_a_banner_printing_digits_unicode_3_2_does_not_assign_refuses_the_document(q, value):
    """R178 (seat S2): a banner across the highlights table prints 2026 in Sunuwar or outlined digits, which Unicode
    16.0 assigns.  After R170 the prior-year pins under it bound on Python 3.12 and were unlocated on Python 3.14.  The
    document is refused on both."""
    assert refusal(banner(q, r4.src(q), "highlights", value), q) == r5.unreadable("character")


@pytest.mark.parametrize("form", ["&#x1F4B2;", "\U0001F4B2"])
def test_r178_a_character_unicode_3_2_does_not_assign_outside_the_tables_refuses_the_document(form):
    """R178 (seat S2): a paragraph after the Q3 tables prints U+1F4B2 HEAVY DOLLAR SIGN (Unicode 6.0), as a reference or
    as the character.  No table holds it, and the document bound every frozen value at 135a67a3e12 and after R168-R176.
    The envelope reads text outside the tables too, so R178 refuses such a character wherever it stands."""
    assert refusal(r5.before_text_end(r5.src(), f"<p>{form}</p>")) == r5.unreadable("character")


@pytest.mark.parametrize("value", ["&#x4E24;", "&#x4EAC;", "&#x8CA1;"])
@pytest.mark.parametrize("q", QUARTERS)
def test_r178_a_banner_printing_an_other_letter_leaves_the_highlights_pins_unlocated(q, value):
    """R178 (seat S2, amends R170's figure test): a banner across the highlights table prints 两, 京 or 財, which
    Unicode 3.2 files as other letters (Lo).  Python 3.14 (Unicode 16.0) calls 两 and 京 numeric and Python 3.12 does
    not, so after R170 the six earnings-per-share pins under the banner were unlocated on 3.14 and bound on 3.12.  R178
    reads every such letter as a possible figure, 財 included, so on both interpreters the banner holds a numeral the
    envelope cannot read as a year, the six pins are unlocated, and every other value binds."""
    assert exactly_unlocated(banner(q, r4.src(q), "highlights", value), q, *HIGHLIGHTS_EPS)


def test_r178_control_characters_unicode_3_2_assigns_outside_the_tables_bind():
    """R178 control: a paragraph after the Q3 tables prints the euro sign and the trade mark sign, as references and as
    characters.  Unicode 3.2 assigns both, and the document binds every frozen value."""
    assert binds_everything(r5.before_text_end(r5.src(), "<p>&#8364; &#8482; € ™</p>"))


@pytest.mark.parametrize("value", ["&#233;", "&#8212;"])
def test_r178_control_a_banner_printing_a_cased_letter_or_a_dash_binds(value):
    """R178 control: a banner across the Q3 highlights table prints 'é' or an em dash.  Neither is a figure or an other
    letter, so the banner names no year and holds no numeral, and the document binds every frozen value."""
    assert binds_everything(banner("Q3", r4.src("Q3"), "highlights", value))


@pytest.mark.parametrize("case", EARLIER_CHECKS[:2])
def test_r178_control_the_type_and_generator_checks_run_before_it(case):
    """R178 control (order): the frozen refusal case with a paragraph printing U+1F4B2 added keeps its own code.  R178
    runs after the two checks that match an ASCII literal in the filing header and the generator comment, which no
    other character can change."""
    assert refused_with(case, HEAVY_DOLLAR) == ({t.REFUSED[case][3]}, True)


@pytest.mark.parametrize("case", EARLIER_CHECKS[2:] + ["text_gt"])
def test_r178_runs_before_every_admission_check_that_reads_printed_text(case):
    """R178 (order, amends R116's order): the frozen refusal case, or a paragraph printing a text '>' that R163
    refuses, with a paragraph printing U+1F4B2 added, is refused 'character'.  R178 runs before the issuer, table,
    role, quarter and R163 checks, each of which reads printed text."""
    if case == "text_gt":
        assert refusal(r5.before_text_end(r5.src(), "<p>9>1.63</p>" + HEAVY_DOLLAR)) == r5.unreadable("character")
    else:
        assert refused_with(case, HEAVY_DOLLAR) == r5.unreadable("character")
