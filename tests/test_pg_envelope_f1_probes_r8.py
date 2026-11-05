"""CDV-1 T1 F1-Q envelope — frozen R8 witness (seat-frozen after the independent Opus re-audit R8 of e6f49ceccb85).

Every case edits a frozen gzipped FY26 Q1-Q3 original in memory, or tampers a workspace built from one, and asserts the
outcome that the bytes and the seat rulings R116-R186 and R187-R191 require.  G1 found a decimal character reference
longer than 4,300 digits raising out of the release parser, the envelope's admission and the validator (B1): Python
converts the digits whole and refuses past its limit.  G3 found a year glued to a letter or a mark ("2026M", "x2026",
"A-2026") still named as a year (B1).  G4 found the validator printing tampered fields with str(), which raises for an
integer past the digit limit and for a value nested deeper than the interpreter prints (B1).  G2 found text holding a
lone surrogate raising when the validator encodes it (B2), and a relocation glued to printed text through an end tag a
reader ignores accepted as a whole token (B1).  The seat found a release body holding a lone surrogate raising when the
binding hashes it (S-R8-1).

R187 reads a character reference's digits the way a reader does, without converting the run: leading zeros add
nothing, and more than seven significant digits is past U+10FFFF and prints U+FFFD.  The envelope and the validator
read references through that reader; the release parser reads no blocks from a document holding a decimal reference
longer than 640 digits, the least limit Python can be set to.  R188 reads a header value's years as words, in one pass:
a 20dd names a year only as a whole word, alone or beside a word that names a period, or joined to such a year; a
letter or a mark glued to it leaves it a figure.  "2025x" and "No. 2025" leave R179's table in the R7 suite for this
one.  R189 refuses, at the validator's entry, every value it could not print or encode (nested deeper than 32, more
than 100,000 values, an integer or fraction term of 641 digits or more, text holding a lone surrogate), and the binding
refuses a release body no bytes decode to.  R190 counts a tag as a separator only where a tree builder acts on it
whatever else is open: every start tag in the set, and of the end tags only </p> and </br>.  R191 freezes this file.

The constructions are the auditors' (G1-G4), widened by the seat to each rule's controls; S-R8-1's is the seat's,
and so is R187's witness through the validator's own reading.
Every case drives the public path (build_event_workspace, validate_selected_facts) except the grammar cases (R187's
reference reader, R188's year table, R190's separator set), which read the one function each rule changed, and the
relocations, which patch the shared receipts API that R143 names as the only place a wrapped receipt is minted.

Rulings: research/consumer_defensive/cdv1_program/reviews/SEAT_RULING_T1_ENVELOPE_R8_2026-09-29.md.
Audit record: research/consumer_defensive/cdv1_program/reviews/OPUS_T1_ENVELOPE_AUDIT_R8_2026-09-28.md.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_pg_envelope_f1 as t  # noqa: E402
import test_pg_envelope_f1_probes_r1 as r1  # noqa: E402
import test_pg_envelope_f1_probes_r4 as r4  # noqa: E402
import test_pg_envelope_f1_probes_r6 as r6  # noqa: E402
import test_pg_envelope_f1_probes_r7 as r7  # noqa: E402
from engine.company_intelligence import economic_observations as eo  # noqa: E402
from engine.company_intelligence import pg_envelope as pe  # noqa: E402
from engine.company_intelligence.economic_observations import EconomicObservationError  # noqa: E402
from engine.earnings_release import receipts  # noqa: E402
from engine.earnings_release.binding import BindingError  # noqa: E402

REL = r4.REL
QUARTERS = sorted(REL)
built, refused, present_row, nested, relocated = r7.built, r7.refused, r7.present_row, r7.nested, r6.relocated
UNPRINTABLE = "workspace holds a value it cannot print"


def after_body(body):
    return body.index(">", body.index("<body")) + 1


def present(ws):
    return {metric: value for metric, value in r1.numeric(ws).items() if isinstance(value, float)}


# ============================ R187 (G1-R8-B1): a character reference's digits are read as a reader reads them
LONG = "&#" + "0" * 4300 + "49;"  # 4,302 digits; a reader prints "1"
WHERE = {
    "text": lambda body, q: body[:after_body(body)] + "<p>" + LONG + "</p>" + body[after_body(body):],
    "comment": lambda body, q: body[:after_body(body)] + "<!-- " + LONG + " -->" + body[after_body(body):],
    "script": lambda body, q: body[:after_body(body)] + "<script>" + LONG + "</script>" + body[after_body(body):],
    "attribute": lambda body, q: body[:after_body(body)] + '<p title="' + LONG + '">x</p>' + body[after_body(body):],
    "pinned_cell": lambda body, q: (lambda cell: body[:cell.start] + LONG + body[cell.start:])(
        r6.pinned(body, q, t.SALES if q == "Q1" else t.DIL)
    ),
}


@pytest.mark.parametrize("where", sorted(WHERE))
@pytest.mark.parametrize("q", QUARTERS)
def test_r187_a_long_decimal_reference_is_read_as_a_reader_reads_it(q, where):
    """R187 (G1-R8-B1): a 4,302-digit decimal reference to '1' in text, a comment, a script, an attribute, or at the
    start of the pinned cell.  ValueError escaped build_event_workspace at e6f49ceccb85.  The document is admitted and
    every value binds as before, except the pinned cell's, which now prints '1' glued to its literal and is refused;
    the workspace validates."""
    before = present(built(q)[0])
    body = WHERE[where](r4.src(q), q)
    assert pe.admit(body, REL[q].scope).code == "F1-Q"
    ws, texts, _ = r4.build(body, q)
    lost = {t.SALES if q == "Q1" else t.DIL} if where == "pinned_cell" else set()
    assert present(ws) == {metric: value for metric, value in before.items() if metric not in lost}
    assert r1.validates(ws, texts, REL[q])


@pytest.mark.parametrize("q", QUARTERS)
def test_r187_the_validator_refuses_a_source_holding_a_long_reference_never_raises(q):
    """R187 (G1-R8-B1): the extractor's own workspace, validated against a source that also carries the reference in
    a comment.  ValueError escaped the validator at e6f49ceccb85; the source is not the one the receipts were minted
    against, and the workspace is refused."""
    ws, texts = built(q)
    body = r4.src(q)
    texts = {key: (WHERE["comment"](body, q) if value == body else value) for key, value in texts.items()}
    refused(ws, texts, q)


SPELLED = {
    "spelled_digit": lambda body, start, end: (
        body[:start] + "&#" + "0" * 4300 + str(ord(body[start])) + ";" + body[start + 1:]
    ),
    "space_before": lambda body, start, end: body[:start] + "&#" + "0" * 4300 + "32;" + body[start:],
    "space_after": lambda body, start, end: body[:end] + "&#" + "0" * 4300 + "32;" + body[end:],
}


@pytest.mark.parametrize("form", sorted(SPELLED))
@pytest.mark.parametrize("metric", [t.SALES, t.DIL], ids=["sales", "diluted_eps"])
@pytest.mark.parametrize("q", QUARTERS)
def test_r187_a_literal_spelled_or_set_off_by_a_long_reference_binds_and_validates(q, metric, form):
    """R187 (G1-R8-B1), the validator's own reading: a 4,302-digit reference spelling the literal's first digit, or
    printing a space before or after the literal.  ValueError escaped build_event_workspace at e6f49ceccb85, and with
    only the envelope's reading repaired it escaped the validator, whose span check reads the receipt's own units.
    Every value binds as before, and the workspace validates."""
    before = present(built(q)[0])
    start, end = r4.spans(q)[metric]
    ws, texts, _ = r4.build(SPELLED[form](r4.src(q), start, end), q)
    assert present(ws) == before and r1.validates(ws, texts, REL[q])


READER = {
    "leading_zeros": ("&#" + "0" * 5000 + "49;", "1"),
    "leading_zeros_no_semicolon": ("&#" + "0" * 5000 + "49 x", "1 x"),
    "past_the_last_code_point": ("&#" + "9" * 5000 + ";", "�"),
    "eight_significant_digits": ("&#11141120;", "�"),
    "hex_past_the_last_code_point": ("&#x" + "f" * 5000 + ";", "�"),
}


@pytest.mark.parametrize("name", sorted(READER))
def test_r187_the_reader_reads_a_long_reference_without_converting_its_digits(name):
    """R187: the engine's reference reader.  html.unescape raises past 4,300 decimal digits; the reader prints what a
    browser's tokenizer prints."""
    text, printed = READER[name]
    assert receipts.unescape(text) == printed


CONVERTIBLE = ["&#49;", "&#0049;", "&#1114111;", "&#1114112;", "&#x31;", "&amp;", "&amp", "&copy1", "&#65&#66;",
               "a&#;b", "&#" + "0" * 4290 + "49;", "&#55296;", "&#0;", "&#128;"]


@pytest.mark.parametrize("text", CONVERTIBLE, ids=[str(index) for index in range(len(CONVERTIBLE))])
def test_r187_the_reader_agrees_with_html_unescape_wherever_it_converts(text):
    """R187: wherever html.unescape converts, the reader prints the same characters."""
    assert receipts.unescape(text) == html.unescape(text)


# ============================ R188 (G3-R8-B1, G1-R8-n1): a header value's years are read as words, in one pass
GLUED_YEARS = ["2026M", "2026m", "2026k", "2026K", "2026B", "2026x", "x2026", "A-2026", "2026-A", "2025x", "No. 2025"]


@pytest.mark.parametrize("value", GLUED_YEARS)
def test_r188_a_year_glued_to_a_letter_or_a_mark_names_no_year(value):
    """R188 (G3-R8-B1): a 20dd glued to a letter ('2026M', 'x2026') or beside a word or a mark that names no period
    ('A-2026', 'No. 2025') is an amount or an identifier to a reader, not a year.  Each was named at e6f49ceccb85, so a
    pin whose title lost its year bound to it.  The words that name a period, and years joined to them, stay named:
    R179's table in the R7 suite."""
    assert pe._named_years(value)[0] == []


GLUED_BANNERS = ["{y}M", "{y}m", "{y}k", "{y}K", "{y}B", "{y}x", "x{y}", "A-{y}", "{y}-A"]


@pytest.mark.parametrize("form", GLUED_BANNERS)
@pytest.mark.parametrize("metric", [t.CORE, t.PCORE], ids=["core", "prior_core"])
@pytest.mark.parametrize("q", QUARTERS)
def test_r188_a_banner_printing_the_year_glued_to_a_letter_or_a_mark_leaves_its_eps_unlocated(q, metric, form):
    """R188 (G3-R8-B1), through the public path: R179's construction, with the title's year removed and a banner across
    the table printing the year glued to a letter or beside a mark that names no period.  The engine named the year and
    bound CORE and PCORE at e6f49ceccb85, on Q1-Q3; a reader reads no year over the core EPS, and it is unlocated.  The
    control, the same banner printing the plain year, binds (R179's, in the R7 suite)."""
    body, role, year = r7.without_title_year(q, metric)
    assert r7.unlocated(r6.banner(q, body, role, form.format(y=year)), q, metric)


# ============================ R189 (G4-R8-B1, G2-R8-B2, S-R8-1): a value the validator cannot print is refused
@pytest.mark.parametrize("q", QUARTERS)
def test_r189_a_present_row_whose_period_has_too_many_digits_to_print_is_refused_not_raised(q):
    """R189 (G4-R8-B1): a present row's period is 10**5000.  ValueError (the digit limit) escaped _fact_id at
    e6f49ceccb85."""
    ws, texts = built(q)
    present_row(ws)["period"] = 10**5000
    refused(ws, texts, q, UNPRINTABLE)


@pytest.mark.parametrize("value", [10**5000, "nested"], ids=["digits", "nested"])
@pytest.mark.parametrize("field", ["quarter", "year"])
def test_r189_a_fiscal_period_field_the_validator_cannot_print_is_refused_not_raised(field, value):
    """R189 (G4-R8-B1): the workspace's fiscal quarter or year is 10**5000 or a list nested 100000 deep.  ValueError
    or RecursionError escaped str() at e6f49ceccb85, before any handler."""
    ws, texts = built("Q3")
    ws["fiscal_period"][field] = nested(100000) if value == "nested" else value
    refused(ws, texts, "Q3", UNPRINTABLE)


@pytest.mark.parametrize("q", ["Q1", "Q3"])
def test_r189_an_absence_subject_nested_too_deep_to_print_is_refused_not_raised(q):
    """R189 (G4-R8-B1): a typed absence's subject is a list nested 100000 deep.  RecursionError escaped str() at
    e6f49ceccb85."""
    ws, texts = built(q)
    next(row for row in t.pg_rows(ws) if "typed_absence" in row)["typed_absence"]["subject"] = nested(100000)
    refused(ws, texts, q, UNPRINTABLE)


SURROGATE = json.loads('"\\ud800"')  # a JSON document carries it; no bytes decode to it


@pytest.mark.parametrize("where", ["event_id", "period"])
@pytest.mark.parametrize("q", QUARTERS)
def test_r189_text_holding_a_lone_surrogate_is_refused_not_raised(q, where):
    """R189 (G2-R8-B2): the workspace's event identity, or a present row's period, is a lone surrogate.
    UnicodeEncodeError escaped the replay's identity or _fact_id at e6f49ceccb85."""
    ws, texts = built(q)
    if where == "event_id":
        ws["event_id"] = SURROGATE
    else:
        present_row(ws)["period"] = SURROGATE
    refused(ws, texts, q, UNPRINTABLE)


@pytest.mark.parametrize("q", QUARTERS)
def test_r189_a_source_text_holding_a_lone_surrogate_is_refused_not_raised(q):
    """R189: the source text handed to the validator holds a lone surrogate in a comment.  It is not text any bytes
    decode to, and it is refused as source_texts that are not text."""
    ws, texts = built(q)
    body = r4.src(q)
    bad = body[:after_body(body)] + "<!-- " + SURROGATE + " -->" + body[after_body(body):]
    texts = {key: (bad if value == body else value) for key, value in texts.items()}
    refused(ws, texts, q, "source_texts must map document ids to text")


def build_unbound(q, body):
    """build_event_workspace on `body` as given (t.workspace binds it first)."""
    rel = REL[q]
    filing = {"cik": rel.cik, "accession": rel.accession, "form": "8-K", "filing_date": rel.filed,
              "acceptance_datetime": rel.accepted, "report_date": rel.filed, "exhibit_url": t.exhibit_url(rel)}
    year, quarter, end = rel.fiscal
    return t.build_event_workspace(
        registry=t.pgp.pg_private_registry(), ticker="PG", asof=t.date.fromisoformat(rel.filed),
        fiscal_period=t.FiscalPeriod(year=year, quarter=quarter, calendar_end=t.date.fromisoformat(end)),
        exhibit_body=body, filing=filing, transcript=None, observed_at=rel.accepted,
        source_available_at=rel.accepted, profile=t.pgp.pg_profile(fiscal_scope=rel.scope),
    )


@pytest.mark.parametrize("where", ["comment", "text"])
@pytest.mark.parametrize("q", QUARTERS)
def test_r189_a_release_body_no_bytes_decode_to_is_refused_not_raised(q, where):
    """R189 (S-R8-1): the release body holds a lone surrogate in a comment or a paragraph.  UnicodeEncodeError escaped
    build_event_workspace at e6f49ceccb85 (the binding hashes the body's UTF-8); the body is refused as not text."""
    body = r4.src(q)
    insert = "<!-- " + SURROGATE + " -->" if where == "comment" else "<p>" + SURROGATE + "</p>"
    with pytest.raises(BindingError, match="release body must be non-empty text"):
        build_unbound(q, body[:after_body(body)] + insert + body[after_body(body):])


@pytest.fixture
def least_digit_limit():
    """Python's integer-to-text limit set to 640 digits, the least it can be set to, for one test."""
    limit = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(640)
    yield
    sys.set_int_max_str_digits(limit)


@pytest.mark.parametrize("q", QUARTERS)
def test_r189_a_number_past_the_least_digit_limit_is_refused_at_the_entry(q, least_digit_limit):
    """R189: a present row's period is 10**640 (641 digits) and the interpreter's limit is the least it can be set
    to.  ValueError escaped _fact_id at e6f49ceccb85; the entry refuses it under any limit."""
    ws, texts = built(q)
    present_row(ws)["period"] = 10**640
    refused(ws, texts, q, UNPRINTABLE)


@pytest.mark.parametrize("q", QUARTERS)
def test_r189_control_a_number_that_prints_under_the_least_limit_is_left_to_the_row_checks(q, least_digit_limit):
    """R189 control: 10**639 (640 digits) prints under every limit Python can be set to, so the entry passes it and
    the row checks refuse it."""
    ws, texts = built(q)
    present_row(ws)["period"] = 10**639
    with pytest.raises(EconomicObservationError) as caught:
        eo.validate_selected_facts(ws, source_texts=texts, fiscal_scope=REL[q].scope)
    assert UNPRINTABLE not in str(caught.value)


@pytest.mark.parametrize("q", QUARTERS)
def test_r189_control_a_character_past_the_basic_plane_is_text(q):
    """R189 control: a character past U+FFFF (a whole code point, not a surrogate) is text.  U+1D400 is one Unicode
    3.2 assigns (R178's admission refuses one it leaves unassigned, such as U+1F600).  In a comment of
    the release body, raw or through a reference, every value binds as before and validates; as the event identity
    it is refused by the replay, not by the entry."""
    ws, texts = built(q)
    before = present(ws)
    body = r4.src(q)
    for comment in ("<!-- \U0001d400 -->", "<!-- &#119808; -->"):
        wide, wide_texts, _ = r4.build(body[:after_body(body)] + comment + body[after_body(body):], q)
        assert present(wide) == before and r1.validates(wide, wide_texts, REL[q])
    ws["event_id"] = ws["event_id"] + "\U0001d400"
    with pytest.raises(EconomicObservationError) as caught:
        eo.validate_selected_facts(ws, source_texts=texts, fiscal_scope=REL[q].scope)
    assert UNPRINTABLE not in str(caught.value)


# ============================ R190 (G2-R8-B1): only a tag a builder acts on whatever is open sets a token off
STRAY = {
    "end_div_after_letter": "<p>Zq</div>1.63</p>", "end_div_after_minus": "<p>-</div>1.63</p>",
    "end_td_after_minus": "<p>-</td>1.63</p>", "end_th_after_letter": "<p>Zq</th>1.63</p>",
    "end_tr_after_letter": "<p>Zq</tr>1.63</p>", "end_table_after_minus": "<p>-</table>1.63</p>",
    "end_div_before_letter": "<p>1.63</div>Zq</p>", "end_div_upper_space": "<p>-</DIV >1.63</p>",
}


@pytest.mark.parametrize("form", sorted(STRAY))
def test_r190_a_relocation_glued_through_an_end_tag_a_reader_ignores_is_refused(monkeypatch, form):
    """R190 (G2-R8-B1): the Q3 diluted-EPS receipt relocated through R143's seam onto '1.63' where an end tag with no
    element open stands between it and a printed character.  A tree builder ignores the tag, so a reader prints one
    token ('-1.63', 'Zq1.63').  Each was accepted at e6f49ceccb85."""
    body = relocated(monkeypatch, STRAY[form])
    assert pe._unreadable_markup(body) is None
    ws, texts, _ = r4.build(body)
    assert r4.excerpt(ws, t.DIL) == "1.63"
    assert not r1.validates(ws, texts)


BOUNDARY = {
    "p_then_p": "<p>Zq</p><p>1.63</p>", "br": "<p>Zq<br>1.63</p>", "end_br": "<p>Zq</br>1.63</p>",
    "end_p_with_none_open": "<p>Zq</p>1.63", "end_div_then_line_feed": "<div>Zq</div>\n1.63",
}


@pytest.mark.parametrize("form", sorted(BOUNDARY))
def test_r190_control_a_relocation_set_off_by_a_boundary_a_builder_makes_is_accepted(monkeypatch, form):
    """R190 control (inside R176's rule): a paragraph, a line break (</br> is read as <br>), an empty paragraph from
    </p> with none open, or layout after a closing div sets the literal off.  The relocation is accepted."""
    body = relocated(monkeypatch, BOUNDARY[form])
    ws, texts, _ = r4.build(body)
    assert r4.excerpt(ws, t.DIL) == "1.63"
    assert r1.validates(ws, texts)


def test_r190_the_separators_are_the_start_tags_and_two_end_tags():
    """R190: the span check's reading of each tag."""
    tags = [b"<td>", b"<th>", b"<tr>", b"<table>", b"<p>", b"<div>", b"<br>", b"<br/>", b"</p>", b"</br>", b"</P >",
            b"</td>", b"</th>", b"</tr>", b"</table>", b"</div>", b"<b>", b"</b>"]
    units, _ = eo._printed_units(b"".join(tags))
    assert [kind for _start, _end, kind in units] == ["separator"] * 11 + ["markup"] * 7
