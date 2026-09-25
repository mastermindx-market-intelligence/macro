"""CDV-1 T1 F1-Q envelope — frozen R4 witness (seat-frozen after the independent Opus re-audit R4 of 2a8d1eb1a9c).

Every case edits one of the frozen gzipped originals in memory and asserts the outcome that the bytes and the seat
rulings R116-R153 and R154-R161 require.  The constructions are the auditor's (P1-P4, M1-M3), widened by the seat to
both narrowing directions on every present row, to the spaced forms of the M1 relocations, to the unit cell on the
right of a per-share value and on the left of a percent value, and to the controls each ruling keeps.  Every case drives
the public path (build_event_workspace, validate_selected_facts) except the R155 seam cases, which patch the shared
receipts API that R143 names as the only place a wrapped receipt is minted, and the R160 census, which reads the
vocabularies themselves (R160 names both exceptions to R131).

Rulings: research/consumer_defensive/cdv1_program/reviews/SEAT_RULING_T1_ENVELOPE_R4_2026-09-25.md.
Audit record: research/consumer_defensive/cdv1_program/reviews/OPUS_T1_ENVELOPE_AUDIT_R4_2026-09-25.md.
"""
from __future__ import annotations

import functools
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_pg_envelope_f1 as t  # noqa: E402
import test_pg_envelope_f1_probes_r1 as r1  # noqa: E402
from engine.company_intelligence import pg_envelope as pe  # noqa: E402
from engine.earnings_release import receipts  # noqa: E402

Q1, Q2, Q3 = t.FY26Q1, t.FY26Q2, t.FY26Q3
REL = {"Q1": Q1, "Q2": Q2, "Q3": Q3}
TAB = {"Q1": t.F1Q_TABLES["FY26Q1"], "Q2": t.F1Q_TABLES["FY26Q2"], "Q3": t.F1Q_TABLES["FY26Q3"]}


def src(q):
    return t.original(REL[q])


def build(body, q="Q3"):
    return t.workspace(REL[q], body, REL[q])


def pin(q, metric, k=0):
    return t.pins(REL[q])[metric][k]


def excerpt(ws, metric):
    row = t.by_metric(ws)[metric]
    return row["source_span"]["display_excerpt"] if "value" in row else None


def edit_cell(body, q, metric, k, fn):
    cell = t.one(body, pin(q, metric, k))
    raw = body[cell.start:cell.end]
    new = fn(raw, cell.text)
    assert new != raw
    return body[:cell.start] + new + body[cell.end:]


def insert_row_after(body, ordinal, row_index, fragment):
    start, end = t.tables(body)[ordinal]
    at = list(t._ROW.finditer(body, start, end))[row_index].end()
    return body[:at] + fragment + body[at:]


@functools.lru_cache(maxsize=None)
def spans(q):
    """The char span of every present row of an original, read from its own untampered workspace."""
    body = src(q)
    ws, _, _ = build(body, q)
    raw = body.encode("utf-8")
    out = {}
    for metric, row in t.by_metric(ws).items():
        if "value" in row:
            receipt = row["source_span"]["receipt"]
            out[metric] = (
                len(raw[:receipt["span_start_byte"]].decode("utf-8")),
                len(raw[:receipt["span_end_byte"]].decode("utf-8")),
            )
    return out


def reseat(monkeypatch, body, old, new):
    """Through R143's seam, mint the one receipt the extractor asks for at `old` (a char span of `body`) at `new`."""
    minted = receipts.receipt_for_char_span

    def moved(*, source, source_sha256, char_start, char_end, **kw):
        if source == body and (char_start, char_end) == old:
            char_start, char_end = new
        return minted(source=source, source_sha256=source_sha256, char_start=char_start, char_end=char_end, **kw)

    monkeypatch.setattr(pe, "receipt_for_char_span", moved)
    monkeypatch.setattr(receipts, "receipt_for_char_span", moved)


# ============================ R154 (P1): a reference that runs into the literal leaves it unlocated
GLUED = [
    ("Q3", t.DIL, ">1.63", ">&nbsp1&#46;63"),
    ("Q3", t.DIL, ">1.63", ">&nbsp1&#x2e;63"),
    ("Q2", t.CORE, ">1.88", ">&nbsp1&#46;88"),
    ("Q1", t.SALES, ">3%", ">&nbsp3&#37;"),
]


@pytest.mark.parametrize("q,metric,old,new", GLUED)
def test_r154_a_reference_that_runs_into_the_literal_leaves_it_unlocated(q, metric, old, new):
    """R154 (enforces R143): '&nbsp1' is one unit under R143's grammar, and it decodes past the literal's start.  The
    primary statement's literal is unlocated, the metric is envelope_unlocated, and the workspace validates."""
    body = edit_cell(src(q), q, metric, 0, lambda raw, lit: raw.replace(old, new, 1))
    ws, texts, _ = build(body, q)
    assert r1.numeric(ws)[metric] == t.UNLOCATED
    assert r1.validates(ws, texts, REL[q])


@pytest.mark.parametrize("before", ["&nbsp;", "&nbsp"])
def test_r154_control_a_reference_that_ends_before_the_literal_is_layout(before):
    """R154 control: '&nbsp;' ends at its semicolon, and a bare '&nbsp' ends where '&' begins the literal's own
    reference.  Either is layout outside the span, and the literal binds."""
    body = edit_cell(src("Q3"), "Q3", t.DIL, 0, lambda raw, lit: raw.replace(">1.63", ">" + before + "&#49;.63", 1))
    ws, texts, _ = build(body)
    assert r1.numeric(ws)[t.DIL] == t.expected_values(Q3)[t.DIL]
    assert excerpt(ws, t.DIL) == "&#49;.63"
    assert r1.validates(ws, texts)


# ============================ R155 (P2, M1): the validator's independent check requires a whole literal
PRESENT = [(q, metric) for q in REL for metric, value in sorted(t.expected_values(REL[q]).items()) if isinstance(value, float)]


@pytest.mark.parametrize("side", ["left", "right"])
@pytest.mark.parametrize("q,metric", PRESENT)
def test_r155_a_narrowed_span_is_not_a_whole_literal(monkeypatch, q, metric, side):
    """R155 (P2): every present span narrowed by one character through R143's seam is refused.  Where the narrowed text
    still parses to the row's value ('7%' to '7', '(1)%' to '(1)'), a literal character is left beside the span."""
    body = src(q)
    start, end = spans(q)[metric]
    new = (start + 1, end) if side == "left" else (start, end - 1)
    if new[0] >= new[1]:
        pytest.skip("a one-character literal has no narrowing")
    reseat(monkeypatch, body, (start, end), new)
    ws, texts, _ = build(body, q)
    assert excerpt(ws, metric) == body[new[0]:new[1]], "wrapped receipts are minted via receipt_for_char_span"
    assert not r1.validates(ws, texts, REL[q])


RELOCATIONS = {
    "comment": "<!--1.63-->",
    "comment_spaced": "<!-- 1.63 -->",
    "attribute": '<p title="1.63"></p>',
    "attribute_spaced": '<p title=" 1.63 "></p>',
}


@pytest.mark.parametrize("form", sorted(RELOCATIONS))
def test_r155_a_relocation_into_markup_is_refused(monkeypatch, form):
    """R155 (M1): the Q3 diluted-EPS receipt relocated through R143's seam onto '1.63' inside a comment or an attribute
    value, glued or spaced, is refused: the text between the last '>' and the span is not whitespace."""
    body = src("Q3")
    end = body.lower().rindex("</text>")
    body = body[:end] + RELOCATIONS[form] + body[end:]
    at = body.index("1.63", end)
    reseat(monkeypatch, body, spans("Q3")[t.DIL], (at, at + len("1.63")))
    ws, texts, _ = build(body)
    assert r1.numeric(ws)[t.DIL] == t.expected_values(Q3)[t.DIL]
    assert excerpt(ws, t.DIL) == "1.63", "wrapped receipts are minted via receipt_for_char_span"
    assert not r1.validates(ws, texts)


# ============================ R156 (P3): the title's year joins the agreement set, and a year header needs its year alone
HIGHLIGHTS_2025_COLUMNS = (
    '<tr><td colspan="6"></td><td colspan="3">{y}</td><td colspan="12"></td><td colspan="3">{y}</td>'
    '<td colspan="3"></td></tr>'
)


def test_r156_a_year_row_contradicting_the_title_year_leaves_no_year():
    """R156 (P3): a row printing '2025' across the Q3 core reconciliation, under its 2026 title.  The title's year joins
    the header years, the set is {2025, 2026}, and CORE, whose pin needs a year, is unlocated."""
    body = insert_row_after(src("Q3"), TAB["Q3"]["core_reconciliation"], 2, '<tr><td colspan="30">2025</td></tr>')
    ws, texts, _ = build(body)
    assert r1.numeric(ws)[t.CORE] == t.UNLOCATED
    assert r1.validates(ws, texts)


def test_r156_a_year_header_needs_its_year_alone():
    """R156 (P3): a Q3 highlights row printing '2026' over the 2025 columns only.  PCORE's and PDIL's highlights cells
    then sit under {2025, 2026}, and both metrics are unlocated, although the highlights role requires no period
    title."""
    body = insert_row_after(src("Q3"), TAB["Q3"]["highlights"], 2, HIGHLIGHTS_2025_COLUMNS.format(y="2026"))
    ws, texts, _ = build(body)
    got = r1.numeric(ws)
    assert (got[t.PCORE], got[t.PDIL]) == (t.UNLOCATED, t.UNLOCATED)
    assert r1.validates(ws, texts)


def test_r156_control_an_agreeing_year_row_changes_nothing():
    """R156 control: the same highlights row printing '2025' over the 2025 columns leaves one year over every cell, and
    the document binds every frozen value."""
    body = insert_row_after(src("Q3"), TAB["Q3"]["highlights"], 2, HIGHLIGHTS_2025_COLUMNS.format(y="2025"))
    ws, texts, _ = build(body)
    assert r1.numeric(ws) == t.expected_values(Q3)
    assert r1.validates(ws, texts)


# ============================ R157 (P4): a literal parses only to a finite number
@pytest.mark.parametrize("statements", [(0,), (0, 1)])
def test_r157_a_literal_too_long_for_a_float_never_binds(statements):
    """R157 (P4): the Q3 diluted-EPS primary statement, alone or with the second, prints a 400-digit figure.  It does
    not parse to a finite number, so R145 makes the metric unlocated (never a conflict), and the workspace validates."""
    body = src("Q3")
    for k in statements:
        body = r1.set_cell(body, pin("Q3", t.DIL, k), "9" * 400)
    ws, texts, _ = build(body)
    assert r1.numeric(ws)[t.DIL] == t.UNLOCATED
    assert r1.validates(ws, texts)


# ============================ R158 (M2): a comment is not structure
def _earnings_rows(body):
    start, end = t.tables(body)[TAB["Q3"]["earnings"]]
    return start, end, list(t._ROW.finditer(body, start, end))


def test_r158_a_table_end_tag_inside_a_comment_closes_nothing():
    """R158 (M2): '<!-- </table> -->' in the Q3 earnings table, before a second Diluted row printing 9.99 and 9.98.
    The comment closes nothing, the table holds both Diluted rows, and R130 leaves DIL unlocated."""
    s = src("Q3")
    start, end, rows = _earnings_rows(s)
    diluted = next(row for row in rows if re.search(r">Diluted<", row.group(0)))
    extra = diluted.group(0).replace("1.63", "9.99").replace("1.54", "9.98")
    close = s.rindex("</table>", start, end + len("</table>"))
    body = s[:close] + "<!-- </table> -->" + extra + s[close:]
    ws, texts, _ = build(body)
    assert r1.numeric(ws)[t.DIL] == t.UNLOCATED
    assert r1.validates(ws, texts)


def test_r158_a_table_start_tag_inside_a_comment_opens_nothing():
    """R158 (M2): '<!-- <table> -->' between two rows of the Q3 earnings table opens nothing, so no table is nested, no
    ordinal moves, and the document binds every frozen value."""
    s = src("Q3")
    _, _, rows = _earnings_rows(s)
    at = rows[1].end()
    body = s[:at] + "<!-- <table> -->" + s[at:]
    ws, texts, _ = build(body)
    assert r1.numeric(ws) == t.expected_values(Q3)
    assert r1.validates(ws, texts)


def test_r158_a_cell_inside_a_comment_is_not_a_cell():
    """R158 (M2): both Q3 diluted-EPS statements hold a comment wrapping a copy of the pinned cell (printing 1.63),
    followed by the printed cell with 9.99.  The commented cell is not a cell, the columns are unchanged, and DIL binds
    the printed 9.99."""
    s = src("Q3")
    for k in (0, 1):
        cell = t.one(s, pin("Q3", t.DIL, k))
        td0 = s.rindex("<td", 0, cell.start)
        td1 = s.index("</td>", cell.end) + len("</td>")
        cell_html = s[td0:td1]
        s = s[:td0] + "<!-- " + cell_html + " -->" + cell_html.replace("1.63", "9.99") + s[td1:]
    ws, texts, _ = build(s)
    assert r1.numeric(ws)[t.DIL] == 9.99
    assert r1.validates(ws, texts)


# ============================ R159 (M3): the unit rule reads the unit cells beside a pinned value
def replace_neighbour(body, q, metric, k, side, new):
    """Replace the '$' cell printed next to a pinned cell, on its left or right, as the witness grid reads the row."""
    cell = t.one(body, pin(q, metric, k))
    row = next(r for r in t.grid(body, cell.table) if cell in r)
    if side == "left":
        unit = max((other for other in row if other.col1 <= cell.col0 and other.text), key=lambda other: other.col1)
    else:
        unit = min((other for other in row if other.col0 >= cell.col1 and other.text), key=lambda other: other.col0)
    assert unit.text == "$"
    return body[:unit.start] + body[unit.start:unit.end].replace("$", new, 1) + body[unit.end:]


def test_r159_a_percent_cell_left_of_a_per_share_value_leaves_it_unlocated():
    """R159 (M3): the Q3 earnings statement prints Diluted EPS as '% | 1.63' (its '$' cell replaced by '%').  The unit
    cell beside the value is one usd_per_share forbids, and DIL is unlocated."""
    body = replace_neighbour(src("Q3"), "Q3", t.DIL, 0, "left", "%")
    ws, texts, _ = build(body)
    assert r1.numeric(ws)[t.DIL] == t.UNLOCATED
    assert r1.validates(ws, texts)


def test_r159_a_percent_cell_right_of_a_per_share_value_leaves_it_unlocated():
    """R159 (M3): the '$' cell between the Q3 earnings statement's 1.63 and 1.54 is replaced by '%'.  It sits beside
    both per-share values, whichever it was printed for, and DIL and PDIL are unlocated."""
    body = replace_neighbour(src("Q3"), "Q3", t.DIL, 0, "right", "%")
    ws, texts, _ = build(body)
    got = r1.numeric(ws)
    assert (got[t.DIL], got[t.PDIL]) == (t.UNLOCATED, t.UNLOCATED)
    assert r1.validates(ws, texts)


def test_r159_a_dollar_cell_left_of_a_percent_value_leaves_it_unlocated():
    """R159 (M3): a '$' cell is printed between the Q3 core reconciliation's 'Core EPS' label and its growth figure.
    The unit cell beside the value is one percent forbids, and COREG is unlocated."""
    body = src("Q3")
    cell = t.one(body, pin("Q3", t.COREG, 1))
    td0 = body.rindex("<td", 0, cell.start)
    body = body[:td0] + "<td>$</td>" + body[td0:]
    ws, texts, _ = build(body)
    assert r1.numeric(ws)[t.COREG] == t.UNLOCATED
    assert r1.validates(ws, texts)


# ============================ R160: a vocabulary holds exactly the tokens the F1-Q originals produce
def test_r160_every_vocabulary_is_the_census_of_the_three_originals():
    """R160 (conforms to R148): each role's vocabulary is exactly the union of the label tokens of the tables the three
    F1-Q originals admit to that role.  A white-box check by necessity: the rule is about the vocabulary itself."""
    produced: dict[str, set[str]] = {}
    for q, rel in REL.items():
        body = src(q)
        admission = pe.wrapped_admit(body, rel.scope)
        document = pe._document(body)
        for role, ordinal in admission.roles.items():
            produced.setdefault(role, set()).update(pe._signature(document.tables[ordinal]))
    assert {role: set(vocabulary) for role, vocabulary in pe._VOCABULARIES.items()} == produced
