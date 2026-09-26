"""CDV-1 T1 F1-Q envelope — frozen R5 witness (seat-frozen after the independent Opus re-audit R5 of a1220205b09).

Every case edits the frozen gzipped Q3 original in memory and asserts the outcome that the bytes and the seat rulings
R116-R162 and R163-R167 require.  B1 and B3 found that the envelope reads markup by a grammar an HTML reader does not
share: a comment the reader closes early or never closes, a text '<' or '>', a tag the reader does not read as one,
and a table the reader builds another way (an implied row, a span it reads differently, a grid with a hole or an
overlap) each let the engine bind a literal the reader never prints.  R163 refuses such a document at admission,
after every earlier check, naming the first construct it cannot read; the validator replays admission, so a workspace
built past the gate is refused as well.  R164 (B2) reads the unit cells beside a value in every grid row the value
occupies, carried cells included, and R165 (m3) reads every year a header value names.  R166 keeps what stays inside
R155's restated limit, and each of its cases passes before and after the repair.

The constructions are the auditor's (B1-B3), widened by the seat to every kind R163 names, to two replay witnesses (a
comment and a grid) and three relocations built past the gate, and to the controls each ruling keeps.  Every case
drives the public path (build_event_workspace, validate_selected_facts) with two exceptions, both named by R163 as
exceptions to R131: the replay witnesses and the relocations build past the gate by replacing `_unreadable_markup` for
the build only, and the relocations and the R166 cases patch the shared receipts API that R143 names as the only place
a wrapped receipt is minted.

Rulings: research/consumer_defensive/cdv1_program/reviews/SEAT_RULING_T1_ENVELOPE_R5_2026-09-25.md.
Audit record: research/consumer_defensive/cdv1_program/reviews/OPUS_T1_ENVELOPE_AUDIT_R5_2026-09-25.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_pg_envelope_f1 as t  # noqa: E402
import test_pg_envelope_f1_probes_r1 as r1  # noqa: E402
import test_pg_envelope_f1_probes_r4 as r4  # noqa: E402
from engine.company_intelligence import pg_envelope as pe  # noqa: E402

Q2, Q3 = t.FY26Q2, t.FY26Q3
TAB = t.F1Q_TABLES["FY26Q3"]


def src():
    return t.original(Q3)


def refusal(body, scope=Q3):
    ws, texts, _ = t.workspace(Q3, body, scope)
    return r1.refusal_details(ws), r1.validates(ws, texts, scope)


def unreadable(kind):
    return {f"envelope_refused:markup_unreadable:{kind}"}, True


def splice(body, *edits):
    """Apply (start, end, new) replacements, each located in the unedited body, from the last to the first."""
    for start, end, new in sorted(edits, reverse=True):
        body = body[:start] + new + body[end:]
    return body


def dil(body):
    return t.one(body, t.pins(Q3)[t.DIL][0])


def rows(body):
    start, end = t.tables(body)[TAB["earnings"]]
    return list(t._ROW.finditer(body, start, end))


def row(body, dy):
    """The Q3 earnings row `dy` rows below the Diluted row (the Basic row is -1, the blank row after it is 1)."""
    return rows(body)[dil(body).row + dy]


def cell(body, dy, col0):
    y = dil(body).row + dy
    return next(c for c in t.grid(body, TAB["earnings"])[y] if c.row == y and c.col0 == col0)


def label(body):
    found = cell(body, 0, 0)
    assert found.text == "Diluted"
    return found


def td(body, c):
    """The <td> element that holds cell `c`: its start, the end of its opening tag, and its end."""
    start = body.rindex("<td", 0, c.start)
    return start, body.index(">", start) + 1, body.index("</td>", c.end) + len("</td>")


def open_tag(body, c, old, new):
    start, tag_end, _ = td(body, c)
    tag = body[start:tag_end]
    assert tag.count(old) == 1, (old, tag)
    return start, tag_end, tag.replace(old, new)


def set_td(body, c, element):
    start, _, end = td(body, c)
    return start, end, element


def in_dil(body, old, new):
    c = dil(body)
    raw = body[c.start:c.end]
    assert raw.count(old) == 1, (old, raw)
    return c.start, c.end, raw.replace(old, new)


def dil_content(body, new):
    """The Q3 diluted-EPS primary cell prints `new` where it printed '1.63'."""
    return splice(body, in_dil(body, ">1.63", ">" + new))


def dil_end(body, new):
    _, _, end = td(body, dil(body))
    return end - len("</td>"), end, new


def row_end(body, new):
    match = row(body, 0)
    assert body[match.end() - len("</tr>"):match.end()] == "</tr>"
    return match.end() - len("</tr>"), match.end(), new


def after_open_tr(body, fragment):
    at = body.index(">", row(body, 0).start()) + 1
    return body[:at] + fragment + body[at:]


def before_row(body, fragment):
    at = row(body, 0).start()
    return body[:at] + fragment + body[at:]


def after_row(body, fragment):
    at = row(body, 0).end()
    return body[:at] + fragment + body[at:]


def text_end(body):
    return body.lower().rindex("</text>")


def before_text_end(body, fragment):
    at = text_end(body)
    return body[:at] + fragment + body[at:]


def earnings_close(body):
    start, end = t.tables(body)[TAB["earnings"]]
    return body.rindex("</table>", start, end)


def second_diluted_row(body, *, before="", after="", open_row=True):
    """A second Diluted row printing 9.99 and 9.98 at the end of the Q3 earnings table, optionally without its '<tr>'."""
    extra = row(body, 0).group(0).replace("1.63", "9.99").replace("1.54", "9.98")
    if not open_row:
        extra = extra[extra.index(">") + 1:]
    at = earnings_close(body)
    return body[:at] + before + extra + after + body[at:]


def tfoot_first_row(body):
    first = rows(body)[0]
    return body[:first.start()] + "<tfoot>" + first.group(0) + "</tfoot>" + body[first.end():]


def grid_hole(body):
    """The Basic row's empty cell over columns 6-8 becomes '%' spanning two rows, and the Diluted row ends after 1.63:
    a reader prints '%' beside 1.63 across the empty column 5, which the engine's grid never reached."""
    return splice(
        body,
        set_td(body, cell(body, -1, 6), '<td colspan="3" rowspan="2">%</td>'),
        (td(body, cell(body, 0, 5))[0], td(body, cell(body, 0, 15))[2], ""),
    )


def grid_overlap(body):
    """The Basic row's empty column-5 cell becomes '%' spanning two rows, and the Diluted row's 1.63 cell spans
    columns 4-5 in place of its own column-5 cell: a reader lays the two cells over one slot."""
    return splice(
        body,
        set_td(body, cell(body, -1, 5), '<td rowspan="2">%</td>'),
        open_tag(body, dil(body), "<td", '<td colspan="2"'),
        set_td(body, cell(body, 0, 5), ""),
    )


def ungated(monkeypatch, body):
    """Build past R163's gate: `_unreadable_markup` answers None for the build only, as the engine read at a1220205b09."""
    with monkeypatch.context() as patch:
        patch.setattr(pe, "_unreadable_markup", lambda source: None)
        return r4.build(body)


# ============================ R163 (B1): a comment the reader closes early or never closes refuses the document
HTML5_CLOSERS = ["<!-->", "<!--->", "<!-- a --!>"]


def comment_in_dil(body, opener):
    return dil_content(body, opener + "9.99<!-- z -->1.63")


@pytest.mark.parametrize("opener", HTML5_CLOSERS)
def test_r163_a_comment_the_reader_closes_early_in_the_pinned_cell_refuses_the_document(opener):
    """R163 (B1): the Q3 diluted-EPS primary cell prints `<opener>9.99<!-- z -->1.63`.  A reader closes the comment
    at the opener and prints '9.991.63'; the engine's `<!--.*?-->` hid '9.99' and bound 1.63 at a1220205b09."""
    assert refusal(comment_in_dil(src(), opener)) == unreadable("comment")


@pytest.mark.parametrize("opener", HTML5_CLOSERS)
def test_r163_a_comment_the_reader_closes_early_around_a_second_row_refuses_the_document(opener):
    """R163 (B1): a second Diluted row (9.99 / 9.98) between `<opener>` and `<!-- z -->` at the end of the Q3 earnings
    table.  A reader prints both rows, which R130 leaves unlocated; the engine hid the row and bound 1.63."""
    assert refusal(second_diluted_row(src(), before=opener, after="<!-- z -->")) == unreadable("comment")


def test_r163_an_unclosed_comment_refuses_the_document():
    """R163 (B1): '<!--' with no later '-->' after the Q3 earnings table.  A reader renders nothing after it; the engine
    ignored it and bound SALES and CORE from tables the reader cannot see."""
    body = src()
    _, end = t.tables(body)[TAB["earnings"]]
    assert refusal(body[:end] + "<!--" + body[end:]) == unreadable("comment")


# ============================ R163 (B3 and the grammar it implies): markup the reader reads another way refuses it
UNREADABLE = {
    # gt: a text '>' (the audit's relocation target, which a reader prints as '9>1.63')
    "gt_text": ("gt", lambda s: before_text_end(s, "<p>9>1.63</p>")),
    # lt: a '<' that opens no tag, which a reader prints
    "lt_text": ("lt", lambda s: before_text_end(s, "<p>1.63< x</p>")),
    "lt_in_the_pinned_cell": ("lt", lambda s: dil_content(s, "1.63<9.99")),  # the engine read '<9.99…</font>' as a tag
    # tag: '<!', '<?', '</' or '<' and a letter that no strict tag reading accepts
    "tag_cdata": ("tag", lambda s: before_text_end(s, "<![CDATA[>1.63<]]>")),
    "tag_bracket_in_an_attribute": ("tag", lambda s: before_text_end(s, '<p title=">1.63<"></p>')),
    "tag_bracket_in_an_attribute_in_the_pinned_cell": ("tag", lambda s: dil_content(s, '<img alt="9.99>1.63<">')),
    "tag_attribute_on_an_end_tag": ("tag", lambda s: splice(s, row_end(s, "</tr x>"))),
    "tag_no_break_space_before_an_attribute": (
        "tag", lambda s: splice(s, open_tag(s, label(s), "<td colspan", "<td\xa0colspan"))),
    # element: raw text in a table, raw text holding a bracket, or an element whose content a reader hides or moves
    "element_script_in_the_pinned_cell": ("element", lambda s: dil_content(s, "<script>1.63</script>")),
    "element_template_in_the_pinned_cell": ("element", lambda s: dil_content(s, "<template>1.63</template>")),
    "element_plaintext": ("element", lambda s: before_text_end(s, "<plaintext>")),
    "element_script_holding_lt": ("element", lambda s: before_text_end(s, "<script>if (a < b) {}</script>")),
    "element_style_holding_gt": ("element", lambda s: before_text_end(s, "<style>p > b {}</style>")),
    "element_tfoot": ("element", tfoot_first_row),
    # table: table > tr > td|th only, no text in a table or row outside a cell, every element closed by its own end tag
    "table_text_in_a_row": ("table", lambda s: after_open_tr(s, "9.99")),
    "table_implied_row": ("table", lambda s: second_diluted_row(s, open_row=False)),
    "table_cell_end_missing": ("table", lambda s: splice(s, dil_end(s, ""))),
    "table_cell_closed_by_th": ("table", lambda s: splice(s, dil_end(s, "</th>"))),
    "table_cell_outside_a_table": ("table", lambda s: before_text_end(s, "<td>1.63</td>")),
    "table_row_end_missing": ("table", lambda s: splice(s, row_end(s, ""))),
    "table_div_between_rows": ("table", lambda s: after_row(s, "<div>9.99</div>")),
    # span: colspan and rowspan at most once each, a plain positive integer within HTML's limits, read alike
    "span_rowspan_zero": ("span", lambda s: splice(s, open_tag(s, cell(s, -1, 3), "<td", '<td rowspan="0"'))),
    "span_signed": ("span", lambda s: splice(s, open_tag(s, label(s), 'colspan="3"', 'colspan="+3"'))),
    "span_named_in_another_attribute": ("span", lambda s: splice(s, open_tag(s, dil(s), "<td", '<td alt="colspan=2"'))),
    "span_suffix_of_another_name": ("span", lambda s: splice(s, open_tag(s, dil(s), "<td", '<td data-colspan="2"'))),
    "span_over_the_limit": ("span", lambda s: splice(s, open_tag(s, label(s), 'colspan="3"', 'colspan="1001"'))),
    "span_repeated": ("span", lambda s: splice(s, open_tag(s, label(s), 'colspan="3"', 'colspan="x" colspan="3"'))),
    # grid: no cell over a slot a rowspan already fills, and no empty slot before a filled one
    "grid_hole": ("grid", grid_hole),
    "grid_overlap": ("grid", grid_overlap),
}


@pytest.mark.parametrize("case", sorted(UNREADABLE))
def test_r163_markup_the_reader_reads_another_way_refuses_the_document(case):
    """R163: each construct is one the engine's regular reading and an HTML reader read differently.  The document is
    refused at admission with markup_unreadable:<kind>, every row carries that refusal, and the workspace validates."""
    kind, make = UNREADABLE[case]
    assert refusal(make(src())) == unreadable(kind)


@pytest.mark.parametrize("scope,edit,code", [
    ("Q2", lambda s: comment_in_dil(s, "<!-->"), "quarter_mismatch"),
    ("Q3", lambda s: before_text_end(t.after_table(s, t._Q3["drivers"], t.INJECTED_TABLE), "<p>9>1.63</p>"),
     "unknown_table:t7"),
])
def test_r163_runs_after_every_earlier_admission_check(scope, edit, code):
    """R163 is admission's last check, so an earlier refusal keeps its own code: the B1 body under the Q2 scope is a
    quarter mismatch, and a text '>' after an injected table is still the unknown table."""
    assert refusal(edit(src()), {"Q2": Q2, "Q3": Q3}[scope]) == ({f"envelope_refused:{code}"}, True)


REPLAYED = {"comment": lambda s: comment_in_dil(s, "<!-->"), "grid": grid_hole}


@pytest.mark.parametrize("kind", sorted(REPLAYED))
def test_r163_the_validator_replays_the_gate(monkeypatch, kind):
    """R163: built past the gate, the engine binds DIL 1.63 as it did at a1220205b09, and the validator, which replays
    admission, refuses the workspace."""
    ws, texts, _ = ungated(monkeypatch, REPLAYED[kind](src()))
    assert r1.numeric(ws)[t.DIL] == t.expected_values(Q3)[t.DIL]
    assert not r1.validates(ws, texts)


RELOCATED = {"gt": "<p>9>1.63</p>", "lt": "<p>1.63< x</p>", "tag": "<![CDATA[>1.63<]]>"}


@pytest.mark.parametrize("kind", sorted(RELOCATED))
def test_r163_a_relocation_onto_a_literal_beside_a_text_bracket_is_refused(monkeypatch, kind):
    """R163 (B3): the Q3 diluted-EPS receipt relocated through R143's seam onto '1.63' in a fragment where a reader
    prints a bracket beside it, in a workspace built past the gate.  R155's gap check alone accepted it at
    a1220205b09; the validator's replay of admission refuses it."""
    fragment = RELOCATED[kind]
    body = before_text_end(src(), fragment)
    at = text_end(src()) + fragment.index("1.63")
    r4.reseat(monkeypatch, body, r4.spans("Q3")[t.DIL], (at, at + len("1.63")))
    ws, texts, _ = ungated(monkeypatch, body)
    assert r4.excerpt(ws, t.DIL) == "1.63", "wrapped receipts are minted via receipt_for_char_span"
    assert not r1.validates(ws, texts)


def upper_case_label(body):
    start, tag_end, end = td(body, label(body))
    assert body[start:tag_end].startswith('<td colspan="3"')
    return splice(body, (start, start + len('<td colspan="3"'), '<TD COLSPAN="3"'), (end - len("</td>"), end, "</TD>"))


KEPT = {
    "comment_holding_brackets": lambda s: dil_content(s, "<!-- a>b<c -->1.63"),
    "comment_between_rows": lambda s: before_row(s, "<!-- note -->"),
    "upper_case_markup": upper_case_label,
    "stray_end_tags_outside_tables": lambda s: before_text_end(s, "</tr></td>"),
    "space_between_row_and_cell": lambda s: after_open_tr(s, "\n  "),
    "single_quoted_span": lambda s: splice(s, open_tag(s, label(s), 'colspan="3"', "colspan='3'")),
    "unquoted_span": lambda s: splice(s, open_tag(s, label(s), 'colspan="3"', "colspan=3")),
    "script_outside_tables": lambda s: before_text_end(s, "<script>var a = 1;</script>"),
}


@pytest.mark.parametrize("case", sorted(KEPT))
def test_r163_control_markup_the_reader_reads_the_same_way_binds(case):
    """R163 control: a comment holding brackets, a comment between rows, upper-case names, stray end tags outside a
    table (R149), layout space between a row and its cell, single-quoted and unquoted spans, and script text outside
    a table are read alike, and the document binds every frozen value."""
    ws, texts, _ = r4.build(KEPT[case](src()))
    assert r1.numeric(ws) == t.expected_values(Q3)
    assert r1.validates(ws, texts)


# ============================ R164 (B2): the unit cells beside a value are read in every grid row it occupies
def carried_unit(body, unit):
    """The Basic row's '$' cell prints `unit` and spans two rows, and the Diluted row's own '$' cell is removed, so a
    reader sees `unit` beside 1.63."""
    basic, diluted = cell(body, -1, 3), cell(body, 0, 3)
    assert (basic.text, diluted.text) == ("$", "$")
    start, tag_end, end = td(body, basic)
    carried = body[start:tag_end].replace("<td", '<td rowspan="2"', 1) + unit + "</td>"
    return splice(body, (start, end, carried), set_td(body, diluted, ""))


def spanning_value(body):
    """The 1.63 cell spans the Diluted row and the blank row after it, which prints '%' right beside it."""
    blank = row(body, 1)
    assert not any(c.text for c in t.grid(body, TAB["earnings"])[dil(body).row + 1])
    return splice(
        body,
        open_tag(body, dil(body), "<td", '<td rowspan="2"'),
        (blank.start(), blank.end(), '<tr><td colspan="3"></td><td></td><td>%</td></tr>'),
    )


@pytest.mark.parametrize("make", [lambda s: carried_unit(s, "%"), spanning_value], ids=["carried_cell", "spanning_value"])
def test_r164_a_percent_cell_beside_a_per_share_value_in_any_row_it_occupies_leaves_it_unlocated(make):
    """R164 (B2, enforces R159): a '%' carried into the value's row by rowspan, or printed beside the lower row of a
    value that spans two rows, is beside the value to a reader.  DIL is unlocated and the workspace validates;
    `_neighbours_admit` read only the value's own row and its own cells at a1220205b09."""
    ws, texts, _ = r4.build(make(src()))
    assert r1.numeric(ws)[t.DIL] == t.UNLOCATED
    assert r1.validates(ws, texts)


def test_r164_control_a_dollar_cell_carried_beside_a_per_share_value_binds():
    """R164 control: the same carried cell printing '$' admits the per-share unit, and the document binds every frozen
    value."""
    ws, texts, _ = r4.build(carried_unit(src(), "$"))
    assert r1.numeric(ws) == t.expected_values(Q3)
    assert r1.validates(ws, texts)


# ============================ R165 (m3): a header value naming two years names both
def test_r165_a_header_value_naming_two_years_under_a_one_year_title_leaves_no_year():
    """R165 (m3, enforces R156): a row printing '2026/2025' across the Q3 core reconciliation.  Its years are {2025,
    2026}, not the first one alone, and CORE, whose period needs one year, is unlocated."""
    body = r4.insert_row_after(src(), TAB["core_reconciliation"], 2, '<tr><td colspan="30">2026/2025</td></tr>')
    ws, texts, _ = r4.build(body)
    assert r1.numeric(ws)[t.CORE] == t.UNLOCATED
    assert r1.validates(ws, texts)


def test_r165_a_year_header_value_naming_two_years_needs_its_year_alone():
    """R165 (m3, enforces R156): a Q3 highlights row printing '2025/2026' over the 2025 columns.  PCORE's and PDIL's
    highlights cells sit under {2025, 2026}, and both metrics are unlocated."""
    body = r4.insert_row_after(src(), TAB["highlights"], 2, r4.HIGHLIGHTS_2025_COLUMNS.format(y="2025/2026"))
    ws, texts, _ = r4.build(body)
    got = r1.numeric(ws)
    assert (got[t.PCORE], got[t.PDIL]) == (t.UNLOCATED, t.UNLOCATED)
    assert r1.validates(ws, texts)


def test_r165_control_a_header_value_naming_one_year_twice_changes_nothing():
    """R165 control: the same highlights row printing '2025/2025' over the 2025 columns names one year, and the
    document binds every frozen value."""
    body = r4.insert_row_after(src(), TAB["highlights"], 2, r4.HIGHLIGHTS_2025_COLUMNS.format(y="2025/2025"))
    ws, texts, _ = r4.build(body)
    assert r1.numeric(ws) == t.expected_values(Q3)
    assert r1.validates(ws, texts)


# ============================ R166: what stays inside R155's restated limit
INSIDE_LIMIT = {
    "script_text_outside_tables": "<script>1.63</script>",
    "comment_interior_between_brackets": "<!-- x>1.63<y -->",
    "bare_legacy_reference": "<p>&nbsp1.63</p>",
    "code_point_unescape_drops": "<p>&#1;1.63</p>",
}


@pytest.mark.parametrize("form", sorted(INSIDE_LIMIT))
def test_r166_a_relocation_inside_the_restated_limit_is_accepted(monkeypatch, form):
    """R166 (records R155's restated limit): the Q3 diluted-EPS receipt relocated through R143's seam onto '1.63' in
    script text outside a table, in a comment between a '>' and a '<', after a bare legacy reference, or after a
    reference html.unescape drops.  The markup is admitted and the relocation is accepted, before and after R163."""
    fragment = INSIDE_LIMIT[form]
    body = before_text_end(src(), fragment)
    at = text_end(src()) + fragment.index("1.63")
    r4.reseat(monkeypatch, body, r4.spans("Q3")[t.DIL], (at, at + len("1.63")))
    ws, texts, _ = r4.build(body)
    assert r4.excerpt(ws, t.DIL) == "1.63", "wrapped receipts are minted via receipt_for_char_span"
    assert r1.validates(ws, texts)
