"""CDV-1 T1 F1-Q envelope — frozen R7 witness (seat-frozen after the independent Opus re-audit R7 of b6808dfcc16).

Every case edits a frozen gzipped FY26 Q1-Q3 original in memory, or tampers a workspace built from one, and asserts the
outcome that the bytes and the seat rulings R116-R178 and R179-R186 require.  G3 found a pin bound to a year printed
only as a figure (B1) and title years read in digits other than ASCII (m1).  G1 found the prior-year note read around
raw text a reader prints (B1) and around references the engine drops (B2), and a span expanded to its full width before
admission refuses it (m1).  G2 found tampered workspaces that raise where they must be refused (B3 a value too large for
a float, B4 an event identity that is not a string, B5 sources that are not a list, m2 nesting deeper than the
interpreter reads), and relocations into the tables accepted through the seam (B1).  G4 found the whole-token check
reading characters Python calls space as a reader's layout (B1).  The seat found a present row whose period is a list or
a mapping raising where it must be refused (S-R7-1), the span check reading a character reference as Python decodes it
where a reader prints another character, or the reference as written (S-R7-2), and the release parser converting a
span's digits whole, which raises past Python's 4,300-digit limit (S-R7-3).

R179 names a year only where a reader reads one: a 20dd set off by the start, a letter or digit, an abbreviation's
point, a comma, a slash or a range dash, and followed by the end, a letter or digit or such a separator; never beside a
figure's sign, bracket or percent.  A period title's day and year are ASCII digits.  R180 reads the prior-year note only
where every character of it prints as the sentence: raw text other than script and style, a reference the engine drops,
or an odd character in the region leaves the note absent.  R181 reads a span at its limit before it is converted or the
grid is expanded, in the release parser as in the envelope.
R182 rules G2-B1 inside R176: through the seam placement is not the span check's job, and without the seam replay
refuses the relocation.  R183 refuses, never raises, the four G2 tampers and the seat's.  R184 reads a whole token's
edge, and R155's gap, as layout only where a reader lays it out: space, tab, line feed, carriage return, form feed and
no-break space.  R185 reads a character reference as a reader prints it: the span begins and ends where printed
characters do, and a reference the engine drops is a printed character at the literal's edge, in R155's gap and inside
the literal; the round-5 case R166 accepted after such a reference is refused, and leaves the R5 suite.  Inside printed
raw text, where a reader may print a reference as written, the literal is set off both as decoded and as written.
R186 freezes this file.

The constructions are the auditors' (G1-G4), widened by the seat to each rule's controls; S-R7-1's to S-R7-3's, and
one isolating witness for each of R184's two checks and R185's five, are the seat's.  Every case drives the public path
(build_event_workspace, validate_selected_facts) except the grammar cases (R179's year table, R181's grid, R184's
token), which read the one function each rule changed, and the relocations, which patch the shared receipts API that
R143 names as the only place a wrapped receipt is minted.

Rulings: research/consumer_defensive/cdv1_program/reviews/SEAT_RULING_T1_ENVELOPE_R7_2026-09-28.md.
Audit record: research/consumer_defensive/cdv1_program/reviews/OPUS_T1_ENVELOPE_AUDIT_R7_2026-09-25.md.
"""
from __future__ import annotations

import copy
import html
import sys
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_pg_envelope_f1 as t  # noqa: E402
import test_pg_envelope_f1_probes_r1 as r1  # noqa: E402
import test_pg_envelope_f1_probes_r4 as r4  # noqa: E402
import test_pg_envelope_f1_probes_r5 as r5  # noqa: E402
import test_pg_envelope_f1_probes_r6 as r6  # noqa: E402
from engine.company_intelligence import economic_observations as eo  # noqa: E402
from engine.company_intelligence import pg_envelope as pe  # noqa: E402
from engine.company_intelligence.economic_observations import (  # noqa: E402
    EconomicObservationError,
    validate_selected_facts,
)

REL = r4.REL
QUARTERS = sorted(REL)
binds_everything, unlocated, binds, relocated = r6.binds_everything, r6.unlocated, r6.binds, r6.relocated


# ============================ R179 (G3-R7-B1, G3-R7-m1): a year is named only where a reader reads one
NAMED = [
    ("2025", [2025]), ("2025 (1)", [2025]), ("(1) 2025", [2025]), ("Fiscal 2025", [2025]), ("FY2025", [2025]),
    ("CY2025", [2025]), ("2025E", [2025]), ("Sept. 2025", [2025]),
    # R188: "2025x" and "No. 2025" moved to test_pg_envelope_f1_probes_r8.py (G3-R8-B1)
    ("2025 and 2026", [2025, 2026]), ("2025, 2026", [2025, 2026]), ("2025/2026", [2025, 2026]),
    ("2025-2026", [2025, 2026]), ("2025 - 2026", [2025, 2026]),
]


@pytest.mark.parametrize("value,years", NAMED)
def test_r179_a_year_a_reader_reads_as_a_year_is_named(value, years):
    """R179: a 20dd set off as a word, after a footnote marker, an abbreviation or a separator, is a year, and nothing
    else in the value is a figure."""
    named, rest = pe._named_years(value)
    assert named == years
    assert not any(pe._figure_character(character) for character in rest)


FIGURES = ["$2025", "2025%", "(2025)", "$(2025)", "+2025", "-2025", "#2025", "$ 2025", "2025.", "2025.5", "2,025"]


@pytest.mark.parametrize("value", FIGURES)
def test_r179_a_year_printed_as_a_figure_is_not_named(value):
    """R179 (G3-R7-B1): a 20dd a reader reads as money, a percentage, a signed or bracketed number or a decimal names no
    year; its digits stay in the value, so the header names none (R170)."""
    named, rest = pe._named_years(value)
    assert named == []
    assert any(pe._figure_character(character) for character in rest)


@pytest.mark.parametrize("value", ["2025 (a)", "2025*"])
def test_r179_a_year_beside_a_marker_outside_the_grammar_is_not_named(value):
    """R179's recorded coverage cost: a letter footnote marker or an asterisk after the year is outside the grammar.
    The value names no year and its digits stay in it, so the header's years are unreadable and the pins under it are
    unlocated (fail-closed; both named their year at b6808dfcc16).  Widening the grammar to them is a ruling, not a
    fix."""
    named, rest = pe._named_years(value)
    assert named == []
    assert any(pe._figure_character(character) for character in rest)


def without_title_year(q, metric):
    """The reconciliation table governing `metric` (CORE: the quarter's; PCORE: the year-ago one, a table of its own in
    Q1) with its period title's year removed.  Returns the edited body, the table's role and the year removed."""
    body = r4.src(q)
    year = str(int(REL[q].fiscal[2][:4]) - (metric == t.PCORE))
    role = "prior_core_reconciliation" if metric == t.PCORE and "prior_core_reconciliation" in r4.TAB[q] else \
        "core_reconciliation"
    start, end = t.tables(body)[r4.TAB[q][role]]
    segment = body[start:end]
    assert segment.count(f", {year}") == 1
    return body[:start] + segment.replace(f", {year}", "", 1) + body[end:], role, year


@pytest.mark.parametrize("metric", [t.CORE, t.PCORE], ids=["core", "prior_core"])
@pytest.mark.parametrize("q", QUARTERS)
def test_r179_precondition_a_title_without_its_year_leaves_its_eps_unlocated(q, metric):
    """R179 precondition (R147): with its title's year removed, nothing over the core EPS names a year."""
    body, _, _ = without_title_year(q, metric)
    assert unlocated(body, q, metric)


FIGURE_BANNERS = ["${y}", "{y}%", "({y})", "$({y})", "+{y}", "-{y}", "#{y}", "{y}."]


@pytest.mark.parametrize("form", FIGURE_BANNERS)
@pytest.mark.parametrize("metric", [t.CORE, t.PCORE], ids=["core", "prior_core"])
@pytest.mark.parametrize("q", QUARTERS)
def test_r179_a_banner_printing_the_year_only_as_a_figure_leaves_its_eps_unlocated(q, metric, form):
    """R179 (G3-R7-B1, enforces R147/R170): the title has lost its year and a banner across its table prints it only as
    a figure.  A reader reads no year over the core EPS; the engine read the digits as the year and bound it at
    b6808dfcc16 (G3's sweep: 16 bad judgements in each quarter, the eight forms over CORE and PCORE)."""
    body, role, year = without_title_year(q, metric)
    assert unlocated(r6.banner(q, body, role, form.format(y=year)), q, metric)


@pytest.mark.parametrize("metric", [t.CORE, t.PCORE], ids=["core", "prior_core"])
@pytest.mark.parametrize("q", QUARTERS)
def test_r179_control_a_banner_printing_the_year_as_a_year_binds_its_eps(q, metric):
    """R179 control: the same banner printing the plain year names it, and the core EPS binds its frozen value."""
    body, role, year = without_title_year(q, metric)
    assert binds(r6.banner(q, body, role, year), q, metric)


TITLE_DIGITS = ["&#1634;&#1632;&#1634;&#{arabic};", "2&#1632;2{ascii}", "&#65298;&#65296;&#65298;&#{wide};"]


@pytest.mark.parametrize("digits", TITLE_DIGITS)
@pytest.mark.parametrize("q", QUARTERS)
def test_r179_a_title_year_in_other_digits_leaves_the_core_reconciliation_unread(q, digits):
    """R179 (G3-R7-m1): the core reconciliation's title prints its year in Arabic-Indic, mixed or full-width digits.
    The table's signature reads a title's year only in ASCII digits, so the table is unknown and the document is
    refused, at b6808dfcc16 and with the repair.  G3's Q1 and Q2 binds ran on an unedited title: its probe took the
    fiscal year, 2026, where those titles print 2025.  R179 makes _parse_period_title read ASCII digits too, as
    defence in depth; these cases pin the refusal and pass with and without it."""
    body = r4.src(q)
    year = REL[q].fiscal[2][:4]
    last = int(year[-1])
    form = digits.format(arabic=1632 + last, ascii=last, wide=65296 + last)
    start, end = t.tables(body)[r4.TAB[q]["core_reconciliation"]]
    body = body[:start] + body[start:end].replace(f", {year}", f", {form}", 1) + body[end:]
    ordinal = r4.TAB[q]["core_reconciliation"]
    assert r6.refusal(body, q) == ({f"envelope_refused:unknown_table:t{ordinal}"}, True)


# ============================ R180 (G1-R7-B1, G1-R7-B2): the prior-year note is read only where all of it prints
def note_edit(fragment, where):
    """The Q3 'no adjustments' note after the core reconciliation, with `fragment` inserted before its closing period,
    after 'no' or after 'were'."""
    body = r4.src("Q3")
    i = body.index("no adjustments to or reconciling items")
    at = {"before_period": body.index("EPS.", i) + len("EPS"), "after_no": i + len("no"),
          "after_were": body.rindex("were", 0, i) + len("were")}[where]
    return body[:at] + fragment + body[at:]


EXCEPT = " except a $0.12 restructuring charge"
PRINTED_RAW = {
    "textarea_material": ("<textarea> material</textarea>", "after_no"),
    "textarea_except": (f"<textarea>{EXCEPT}</textarea>", "before_period"),
    "xmp_not": ("<xmp> not</xmp>", "after_were"),
    "xmp_except": (f"<xmp>{EXCEPT}</xmp>", "before_period"),
    **{f"{name}_except": (f"<{name}>{EXCEPT}</{name}>", "before_period")
       for name in ("noscript", "noembed", "noframes", "iframe", "title")},
}


@pytest.mark.parametrize("form", sorted(PRINTED_RAW))
def test_r180_raw_text_other_than_script_and_style_inside_the_note_leaves_prior_core_eps_unlocated(form):
    """R180 (G1-R7-B1, enforces R157/R173): raw text inside the note qualifies it for a reader who prints it.  The
    engine blanked every raw-text element and bound PCORE at b6808dfcc16.  R180 reads raw text as R174 does: only
    script and style are never printed, so any other raw-text element in the region leaves the note absent.  Textarea
    and xmp are printed by every reader; noscript, noembed, noframes and iframe content by a reader without scripting,
    embedding, frames or iframes; the title by a text reader (G1 counted the last five as reader artefacts; the seat
    reads them fail-closed)."""
    fragment, where = PRINTED_RAW[form]
    assert unlocated(note_edit(fragment, where), "Q3", t.PCORE)


@pytest.mark.parametrize("reference", ["&#1;", "&#127;", "&#xFDD0;", "&#xFFFE;", "&#xFFFF;", "&#x10FFFF;"])
def test_r180_a_reference_the_engine_drops_inside_the_note_leaves_prior_core_eps_unlocated(reference):
    """R180 (G1-R7-B2, enforces R172's class): a reference html.unescape drops, which a reader prints as a character,
    sits inside the note.  The note's reader decoded through _units, dropped it, and bound PCORE at b6808dfcc16."""
    assert unlocated(note_edit(reference, "after_no"), "Q3", t.PCORE)


@pytest.mark.parametrize("character", ["\x0b", "\x1c", "\x1f", "\x85", "\u2028", "\u3000"])
def test_r180_an_odd_character_inside_the_note_leaves_prior_core_eps_unlocated(character):
    """R180 (seat widening of G1-R7-B2): a control or an odd space inside the note, printed as itself, leaves it
    absent."""
    assert unlocated(note_edit(character, "after_no"), "Q3", t.PCORE)


@pytest.mark.parametrize("name", ["script", "style"])
def test_r180_control_script_or_style_inside_the_note_is_never_printed_and_binds(name):
    """R180 control: script and style are never printed; the note a reader reads is the sentence, and the document
    binds every frozen value."""
    assert binds_everything(note_edit(f"<{name}>{EXCEPT}</{name}>", "before_period"))


@pytest.mark.parametrize("space", ["&#160;", "&nbsp;", "\xa0"])
def test_r180_control_a_no_break_space_inside_the_note_is_layout_and_binds(space):
    """R180 control: the space after 'no' printed as a no-break space reads as the same sentence, and the document binds
    every frozen value."""
    body = r4.src("Q3")
    i = body.index("no adjustments to or reconciling items") + len("no")
    assert body[i] == " "
    assert binds_everything(body[:i] + space + body[i + 1:])


# ============================ R181 (G1-R7-m1, S-R7-3): a span is read at its limit before it is converted or expanded
def oversized(digits):
    """The Q3 diluted-EPS cell with colspan `digits` and rowspan 2, and the start of its content."""
    body = r4.src("Q3")
    c = r6.pinned(body, "Q3", t.DIL)
    _, tag_end, _ = r6.element(body, c)
    attribute = f' colspan="{digits}" rowspan="2"'
    return body[:tag_end - 1] + attribute + body[tag_end - 1:], c.start + len(attribute)


@pytest.mark.parametrize("digits", ["1000000000", "9" * 7000], ids=["ten_digits", "seven_thousand_digits"])
def test_r181_a_span_beyond_its_limit_is_read_at_the_limit(digits):
    """R181 (G1-R7-m1): the engine expanded the grid to the span's full width before R163 refused it, at a cost
    linear in the span's value (G1: 0.30 s at 10^3, 7.94 s at 10^7, at b6808dfcc16); the seven-thousand-digit form
    raised ValueError in the engine's own grid there.  The span is read at its limit, 1000 (the HTML table model's,
    which R163 enforces), and admission refuses the document."""
    body, start = oversized(digits)
    widths = {x.col1 - x.col0 for table in pe._document(body).tables for row in table for x in row if x.start == start}
    assert widths == {1000}
    assert pe.admit(body, REL["Q3"].scope).code == "markup_unreadable:span"


@pytest.mark.parametrize("digits", ["1000000000", "9" * 7000], ids=["ten_digits", "seven_thousand_digits"])
def test_r181_an_oversized_span_refuses_the_document(digits):
    """R181 (S-R7-3): the same spans through the public path refuse the document as markup_unreadable:span.  At
    b6808dfcc16 the release parser raised ValueError on the seven-thousand-digit form before the envelope ran: it
    converted the span's digits whole, past Python's 4,300-digit limit.  A value past six significant digits now
    reads as 10**6 without being converted, and the parser flags the span absurd as before."""
    body, _ = oversized(digits)
    assert r5.refusal(body) == r5.unreadable("span")


# ============================ R182 (G2-R7-B1): a relocation into the tables, ruled inside R176
IN_TABLE = {
    "comment_in_the_pinned_cell": ("<!-- x>{}<y -->", "pinned_cell"),
    "comment_in_the_pinned_row": ("<!-- x>{}<y -->", "pinned_row"),
    "comment_between_rows_of_the_last_table": ("<!-- x>{}<y -->", "last_table_between_rows"),
    "new_row_in_the_last_table": ("<tr><td>{}</td></tr>", "last_table_between_rows"),
}


def relocated_into_a_table(monkeypatch, q, fragment, where):
    """G2's relocations: the first pinned metric's receipt relocated through R143's seam onto its literal inside a
    table.  Returns the edited body, the metric and the literal."""
    body = r4.src(q)
    spans = r4.spans(q)
    metric = sorted(spans)[0]
    start, end = spans[metric]
    literal = html.unescape(body[start:end])
    fragment = fragment.format(literal)
    low = body.lower()
    if where == "pinned_cell":
        at = low.index("</td>", end)
    elif where == "pinned_row":
        at = low.index("</tr>", end)
    else:
        table_start, table_end = t.tables(body)[-1]
        at = low.rindex("</tr>", table_start, table_end) + len("</tr>")
    edited = body[:at] + fragment + body[at:]
    k = at + fragment.index(literal)
    r4.reseat(monkeypatch, edited, (start, end), (k, k + len(literal)))
    return edited, metric, literal


def replay_refuses(monkeypatch, ws, texts, q):
    """Without the seam, the validator's replay mints the receipt from the source bytes."""
    monkeypatch.undo()
    with pytest.raises(EconomicObservationError, match="does not replay from source bytes"):
        validate_selected_facts(ws, source_texts=texts, fiscal_scope=REL[q].scope)


@pytest.mark.parametrize("case", sorted(IN_TABLE))
@pytest.mark.parametrize("q", QUARTERS)
def test_r182_a_relocation_into_a_table_passes_the_span_check_and_replay_refuses_it(monkeypatch, q, case):
    """R182 (G2-R7-B1, within R176): through the seam, which replaces replay's receipt, a relocation onto the same
    literal in a comment inside a table or in a new row is accepted, as R176 records.  The span check proves the span
    is a whole token that parses to the value; where it sits is replay's job (R143), and without the seam replay refuses
    it."""
    body, metric, literal = relocated_into_a_table(monkeypatch, q, *IN_TABLE[case])
    assert pe.admit(body, REL[q].scope).code == "F1-Q"
    ws, texts, _ = r4.build(body, q)
    assert r4.excerpt(ws, metric) == literal
    assert r1.validates(ws, texts, REL[q])
    replay_refuses(monkeypatch, ws, texts, q)


def another_cell(q, n):
    """G2's relocation onto another cell printing the same literal: the n-th (metric, old span, new span)."""
    body = r4.src(q)
    pairs = []
    for metric, (start, end) in sorted(r4.spans(q).items()):
        literal = body[start:end]
        for table in pe._document(body).tables:
            for row in table:
                for cell in row:
                    if cell.text == html.unescape(literal) and not cell.start <= start < cell.end:
                        k = body[cell.start:cell.end].find(literal)
                        if k >= 0:
                            pairs.append((metric, (start, end), (cell.start + k, cell.start + k + len(literal))))
    return pairs[n]


@pytest.mark.parametrize("n", [0, 7])
@pytest.mark.parametrize("q", QUARTERS)
def test_r182_a_relocation_onto_another_cell_passes_the_span_check_and_replay_refuses_it(monkeypatch, q, n):
    """R182 (G2-R7-B1, within R176): the receipt relocated through the seam onto another cell printing the same literal
    is accepted, as R176 records; without the seam replay refuses it."""
    metric, old, new = another_cell(q, n)
    body = r4.src(q)
    r4.reseat(monkeypatch, body, old, new)
    ws, texts, _ = r4.build(body, q)
    receipt = t.by_metric(ws)[metric]["source_span"]["receipt"]
    assert body.encode("utf-8")[:receipt["span_start_byte"]].decode("utf-8") == body[:new[0]]
    assert r1.validates(ws, texts, REL[q])
    replay_refuses(monkeypatch, ws, texts, q)


# ============================ R183 (G2-R7-B3, B4, B5, m2; seat S-R7-1): a tampered workspace is refused, never raised
def built(q):
    ws, texts, _ = r4.build(r4.src(q), q)
    return copy.deepcopy(ws), texts


def present_row(ws):
    return next(row for row in t.pg_rows(ws) if "value" in row)


def refused(ws, texts, q, message=None):
    with pytest.raises(EconomicObservationError, match=message):
        validate_selected_facts(ws, source_texts=texts, fiscal_scope=REL[q].scope)


HUGE = {"int": 10**400, "negative_int": -(10**400), "fraction": Fraction(10**400, 1)}


@pytest.mark.parametrize("kind", sorted(HUGE))
@pytest.mark.parametrize("q", QUARTERS)
def test_r183_a_value_too_large_for_a_float_is_refused_not_raised(q, kind):
    """R183 (G2-R7-B3, enforces R134/R176): a present row's value is a number float() cannot hold.  The finiteness
    check raised OverflowError at b6808dfcc16; the value is not finite, and the row is refused."""
    ws, texts = built(q)
    present_row(ws)["value"] = HUGE[kind]
    refused(ws, texts, q, "numeric observation must be finite")


@pytest.mark.parametrize("event_id", [7, None, ["e"]], ids=["int", "null", "list"])
@pytest.mark.parametrize("q", QUARTERS)
def test_r183_a_workspace_event_identity_that_is_not_a_string_is_refused_not_raised(q, event_id):
    """R183 (G2-R7-B4): the workspace's event_id is a number, null or a list.  The replay raised TypeError at
    b6808dfcc16; the identity is not a string, and the workspace is refused."""
    ws, texts = built(q)
    ws["event_id"] = event_id
    refused(ws, texts, q, "workspace event identity is not a string")


@pytest.mark.parametrize("sources", [None, 5, True], ids=["null", "int", "bool"])
def test_r183_workspace_sources_that_are_not_a_list_are_refused_not_raised(sources):
    """R183 (G2-R7-B5): the workspace's sources field is null, a number or a boolean.  Iterating it raised TypeError at
    b6808dfcc16; the workspace is refused."""
    ws, texts = built("Q3")
    ws["sources"] = sources
    refused(ws, texts, "Q3", "workspace sources must be a list")


def nested(depth):
    value: list = []
    for _ in range(depth):
        value = [value]
    return value


@pytest.mark.parametrize("field", ["period", "unit", "rights_profile", "absence_detail"])
def test_r183_a_value_nested_deeper_than_the_interpreter_reads_is_refused_not_raised(field):
    """R183 (G2-R7-m2): a present Q1 row's period or unit, its receipt's rights profile, or the Q1 typed absence's
    detail, is a list nested 100000 deep.  RecursionError escaped at b6808dfcc16 (period on 3.12 and 3.14; unit,
    rights profile and detail on 3.12); the row is refused on both."""
    ws, texts = built("Q1")
    if field == "absence_detail":
        next(row for row in t.pg_rows(ws) if "typed_absence" in row)["typed_absence"]["detail"] = nested(100000)
    elif field == "rights_profile":
        present_row(ws)["source_span"]["rights_profile"] = nested(100000)
    else:
        present_row(ws)[field] = nested(100000)
    refused(ws, texts, "Q1")


@pytest.mark.parametrize("period", [["FY26Q3"], {"quarter": 3}], ids=["list", "mapping"])
def test_r183_a_present_row_whose_period_is_not_a_scalar_is_refused_not_raised(period):
    """R183 (seat S-R7-1): a present row's period is a list or a mapping and its fact_id is recomputed to follow it.
    Hashing the row's scope key raised TypeError at b6808dfcc16; the row is refused."""
    ws, texts = built("Q3")
    row = present_row(ws)
    row["period"] = period
    row["fact_id"] = eo._fact_id(ws["event_id"], row["metric"], period, eo._definition(row["metric"]).basis)
    refused(ws, texts, "Q3", "selected row period is not a scalar")


# ============================ R184 (G4-R7-B1): a token's edge is layout only where a reader lays it out
PYTHON_ONLY_SPACE = {"x0b": "\x0b", "x1c": "\x1c", "x1d": "\x1d", "x1e": "\x1e", "x1f": "\x1f", "x85": "\x85"}


@pytest.mark.parametrize("name", sorted(PYTHON_ONLY_SPACE))
def test_r184_a_character_python_calls_space_is_not_a_token_edge(name):
    """R184 (G4-R7-B1, enforces R174): str.isspace() accepts these characters; HTML lays out only space, tab, line
    feed, carriage return and form feed, and a reader prints them as characters, so '-X1.63' is one token."""
    fragment = f"<p>-{PYTHON_ONLY_SPACE[name]}1.63</p>".encode()
    start = fragment.index(b"1.63")
    assert not eo._whole_printed_token(fragment, start, start + 4)


@pytest.mark.parametrize("space", [" ", "\t", "\n", "\r", "\f", "\xa0", "&#160;", "&nbsp;", "&#32;"])
def test_r184_control_a_character_a_reader_lays_out_is_a_token_edge(space):
    """R184 control: HTML's layout space and the no-break space set the literal off."""
    fragment = f"<p>-{space}1.63</p>".encode()
    start = fragment.index(b"1.63")
    assert eo._whole_printed_token(fragment, start, start + 4)


GLUED = {
    **{f"letter_then_{name}": f"<p>x{character}1.63</p>" for name, character in PYTHON_ONLY_SPACE.items()},
    **{f"minus_markup_then_{name}": f"<p>-<b></b>{character}1.63</p>" for name, character in PYTHON_ONLY_SPACE.items()},
    "letter_markup_then_x0b": "<p>Q<i></i>\x0b1.63</p>",
    "letter_markup_then_x1c": "<p>Q<i></i>\x1c1.63</p>",
    "x0b_alone": "<p>\x0b1.63</p>",
}


@pytest.mark.parametrize("form", sorted(GLUED))
def test_r184_a_relocation_onto_a_literal_glued_by_a_character_python_calls_space_is_refused(monkeypatch, form):
    """R184 (G4-R7-B1): the Q3 diluted-EPS receipt relocated through R143's seam onto '1.63' where a reader prints it as
    part of a longer token.  At b6808dfcc16 the nine forms with markup or nothing between the character and the
    literal were accepted: R155's gap check and R174's token check both read the character as space.  The six forms
    with a letter in the gap were already refused there by R155's gap check; they pin that refusal."""
    body = relocated(monkeypatch, GLUED[form])
    assert pe._unreadable_markup(body) is None
    ws, texts, _ = r4.build(body)
    assert r4.excerpt(ws, t.DIL) == "1.63"
    assert not r1.validates(ws, texts)


ALONE = {
    **{f"gap_then_space_{name}": f"<p>{character} 1.63</p>" for name, character in PYTHON_ONLY_SPACE.items()},
    **{f"edge_across_markup_{name}": f"<p>-{character}<b></b>1.63</p>"
       for name, character in PYTHON_ONLY_SPACE.items()},
}


@pytest.mark.parametrize("form", sorted(ALONE))
def test_r184_each_check_alone_refuses_the_relocation_only_it_reads(monkeypatch, form):
    """R184 (G4-R7-B1), one witness per check; both forms were accepted at b6808dfcc16.  'gap_then_space': the
    character sits in R155's gap and a space sets the literal off, so R174's token check reads a space as its edge and
    only the gap check refuses: the element prints a character besides the literal.  'edge_across_markup': the gap is
    empty and the character is the printed neighbour across markup, so only R174's token check refuses."""
    body = relocated(monkeypatch, ALONE[form])
    assert pe._unreadable_markup(body) is None
    ws, texts, _ = r4.build(body)
    assert r4.excerpt(ws, t.DIL) == "1.63"
    assert not r1.validates(ws, texts)


SET_OFF = {
    "markup_then_space": "<p>-<b></b> 1.63</p>",
    "markup_then_no_break_space": "<p>-<b></b>&#160;1.63</p>",
    "no_break_space_alone": "<p>\xa01.63</p>",
}


@pytest.mark.parametrize("form", sorted(SET_OFF))
def test_r184_control_a_relocation_onto_a_literal_set_off_by_layout_is_accepted(monkeypatch, form):
    """R184 control (inside R176's rule): the literal is set off by a space or a no-break space.  The relocation is
    accepted."""
    body = relocated(monkeypatch, SET_OFF[form])
    ws, texts, _ = r4.build(body)
    assert r4.excerpt(ws, t.DIL) == "1.63"
    assert r1.validates(ws, texts)


# ============================ R185 (S-R7-2): the span check reads a character reference as a reader prints it
DROPPED = {"x01": "&#1;", "x7f": "&#127;", "xfdd0": "&#xFDD0;", "xfffe": "&#xFFFE;", "xffff": "&#xFFFF;",
           "x10ffff": "&#x10FFFF;"}
GLUED_BY_A_REFERENCE = {
    **{f"before_{name}": (f"<p>{reference}1.63</p>", "1.63") for name, reference in DROPPED.items()},
    **{f"after_{name}": (f"<p>1.63{reference}</p>", "1.63") for name, reference in DROPPED.items()},
}


@pytest.mark.parametrize("form", sorted(GLUED_BY_A_REFERENCE))
def test_r185_a_relocation_onto_a_literal_glued_by_a_reference_the_engine_drops_is_refused(monkeypatch, form):
    """R185 (S-R7-2): html.unescape returns nothing for a reference to a control or a noncharacter, where a reader
    prints the code point: '<p>&#1;1.63</p>' prints '\\x011.63', one token.  At b6808dfcc16, and with R179-R184, the
    relocation was accepted: R155's gap check and R174's token check both read the reference as nothing.  R166 had
    frozen 'before_x01' as accepted (the R5 suite's code_point_unescape_drops); R185 refuses it."""
    fragment, literal = GLUED_BY_A_REFERENCE[form]
    body = relocated(monkeypatch, fragment, literal)
    assert pe._unreadable_markup(body) is None
    ws, texts, _ = r4.build(body)
    assert r4.excerpt(ws, t.DIL) == literal
    assert not r1.validates(ws, texts)


CUT = {"x09": "<p>&#91.63</p>", "x0a_hex": "<p>&#x0a1.63</p>", "x0a": "<p>&#101.63</p>", "x20": "<p>&#321.63</p>",
       "x0d": "<p>&#131.63</p>", "xa0": "<p>&#1601.63</p>"}
ONE_CHECK = {
    **{f"cut_{name}": (fragment, "1.63") for name, fragment in CUT.items()},
    **{f"edge_{name}": (f"<p>{reference}<b></b>1.63</p>", "1.63") for name, reference in DROPPED.items()},
    **{f"gap_{name}": (f"<p>{reference} 1.63</p>", "1.63") for name, reference in DROPPED.items()},
    **{f"inside_{name}": (f"<p>1{reference}.63</p>", f"1{reference}.63") for name, reference in DROPPED.items()},
}


@pytest.mark.parametrize("form", sorted(ONE_CHECK))
def test_r185_each_check_alone_refuses_the_relocation_only_it_reads(monkeypatch, form):
    """R185 (S-R7-2), one witness per check; every form was accepted at b6808dfcc16 and with R179-R184.  'cut': the span
    starts inside a reference, which a reader prints as the one character it names ('&#91.63' prints '[.63', and
    '1.63' is not printed at all); the bytes before the span decode to layout, so only the check that the span begins
    where a printed character begins refuses.  'edge': the printed neighbour across markup is a dropped reference, so
    only R174's token check refuses.  'gap': a space sets the literal off and the dropped reference sits in R155's gap,
    so only the gap check refuses.  'inside': the dropped reference sits inside the literal ('1&#1;.63' prints
    '1\\x01.63'), so only the raw-literal check refuses."""
    fragment, literal = ONE_CHECK[form]
    body = relocated(monkeypatch, fragment, literal)
    assert pe._unreadable_markup(body) is None
    ws, texts, _ = r4.build(body)
    assert r4.excerpt(ws, t.DIL) == literal
    assert not r1.validates(ws, texts)


PRINTED_AS_DECODED = {
    "space_reference": ("<p>&#32;1.63</p>", "1.63"),
    "no_break_space_without_semicolon": ("<p>&nbsp1.63</p>", "1.63"),
    "full_stop_reference_inside": ("<p>1&#46;63</p>", "1&#46;63"),
    "digit_reference_first": ("<p>&#49;.63</p>", "&#49;.63"),
}


@pytest.mark.parametrize("form", sorted(PRINTED_AS_DECODED))
def test_r185_control_a_reference_a_reader_prints_as_the_engine_decodes_it_is_accepted(monkeypatch, form):
    """R185 control (inside R176's rule): each reference prints what the engine decodes.  A space sets the literal off;
    'nbsp' without its semicolon ends where a reader and the engine alike end it, so the span begins where a printed
    character begins; a reference inside or at the start of the span prints the full stop or the digit it names.  The
    relocation is accepted."""
    fragment, literal = PRINTED_AS_DECODED[form]
    body = relocated(monkeypatch, fragment, literal)
    ws, texts, _ = r4.build(body)
    assert r4.excerpt(ws, t.DIL) == literal
    assert r1.validates(ws, texts)


RAW_TEXT_AS_WRITTEN = ["iframe", "noembed", "noframes", "xmp"]
RAW_TEXT_DECODED = ["noscript", "textarea", "title"]


@pytest.mark.parametrize("name", RAW_TEXT_AS_WRITTEN)
def test_r185_a_relocation_onto_a_literal_raw_text_prints_glued_to_a_reference_is_refused(monkeypatch, name):
    """R185 (S-R7-2), the fifth check: inside iframe, noembed, noframes and xmp a reader prints a reference as its own
    characters, so '<xmp>&nbsp1.63</xmp>' prints '&nbsp1.63', one token.  The literal shares its raw-text unit with the
    reference, and the engine read that unit as html.unescape decodes it: a no-break space, then '1.63'.  The relocation
    was accepted at b6808dfcc16, with R179-R184 and with R185's other four checks; only the check that the literal is
    set off as its characters stand refuses it."""
    body = relocated(monkeypatch, f"<{name}>&nbsp1.63</{name}>")
    assert pe._unreadable_markup(body) is None
    ws, texts, _ = r4.build(body)
    assert r4.excerpt(ws, t.DIL) == "1.63"
    assert not r1.validates(ws, texts)


@pytest.mark.parametrize("name", RAW_TEXT_DECODED)
def test_r185_the_same_relocation_where_a_reader_decodes_the_reference_is_refused_too(monkeypatch, name):
    """R185 coverage pin: a reader decodes the reference in textarea and title, and in noscript read as markup, and
    prints '\\xa01.63'.  The engine does not ask which raw-text elements a reader decodes: inside printed raw text the
    literal must be set off both as decoded and as written, so these relocations are refused too.  The cost is coverage
    alone; each was accepted at b6808dfcc16 and with R179-R184."""
    body = relocated(monkeypatch, f"<{name}>&nbsp1.63</{name}>")
    assert pe._unreadable_markup(body) is None
    ws, texts, _ = r4.build(body)
    assert r4.excerpt(ws, t.DIL) == "1.63"
    assert not r1.validates(ws, texts)


SET_OFF_BOTH_WAYS = {
    **{f"{name}_space": f"<{name}>&nbsp 1.63</{name}>" for name in RAW_TEXT_AS_WRITTEN + RAW_TEXT_DECODED},
    "xmp_carriage_return": "<xmp>&nbsp\r1.63</xmp>",
}


@pytest.mark.parametrize("form", sorted(SET_OFF_BOTH_WAYS))
def test_r185_control_a_literal_raw_text_sets_off_both_as_decoded_and_as_written_is_accepted(monkeypatch, form):
    """R185 control (inside R176's rule): a space, or a carriage return a reader prints as a line break, sets the
    literal off both as decoded and as written.  The relocation is accepted."""
    body = relocated(monkeypatch, SET_OFF_BOTH_WAYS[form])
    ws, texts, _ = r4.build(body)
    assert r4.excerpt(ws, t.DIL) == "1.63"
    assert r1.validates(ws, texts)
