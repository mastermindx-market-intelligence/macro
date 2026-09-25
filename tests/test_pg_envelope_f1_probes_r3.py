"""CDV-1 T1 F1-Q envelope — frozen R3 witness (seat-frozen after the independent Opus re-audit R3 of 80bd14fce4a).

Every case edits one of the frozen gzipped originals in memory and asserts the outcome that the bytes and the seat
rulings R116-R121, R122-R131, R132-R142 and R143-R151 require.  The constructions are the auditor's (N1-N8), widened by
the seat to both sides of the literal, to every CR form and to the controls each ruling keeps; the R143 seam case and the
R144 locale cases are seat-authored.  Every case drives the public path (build_event_workspace, validate_selected_facts,
pg_envelope.admit) except the R143 seam case, which patches the shared receipts API that R143 names as the only place a
wrapped receipt is minted.

Rulings: research/consumer_defensive/cdv1_program/reviews/SEAT_RULING_T1_ENVELOPE_R3_2026-09-25.md.
Audit record: research/consumer_defensive/cdv1_program/reviews/OPUS_T1_ENVELOPE_AUDIT_R3_2026-09-25.md.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_pg_envelope_f1 as t  # noqa: E402
import test_pg_envelope_f1_probes_r1 as r1  # noqa: E402
from engine.company_intelligence import pg_envelope as pe  # noqa: E402
from engine.earnings_release import receipts  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
Q1, Q2, Q3 = t.FY26Q1, t.FY26Q2, t.FY26Q3
REL = {"Q1": Q1, "Q2": Q2, "Q3": Q3}
TAB = {"Q1": t.F1Q_TABLES["FY26Q1"], "Q2": t.F1Q_TABLES["FY26Q2"], "Q3": t.F1Q_TABLES["FY26Q3"]}
CUR = {"Q1": "July - September 2025", "Q2": "October - December 2025", "Q3": "January - March 2026"}
MARKER = "<!-- Document created using Wdesk -->\n"


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


def before(fragment):
    return lambda raw, lit: raw.replace(">" + lit, ">" + fragment + lit, 1)


def after(fragment):
    def fn(raw, lit):
        i = raw.index(">" + lit) + 1 + len(lit)
        return raw[:i] + fragment + raw[i:]
    return fn


# ============================ R143 (N1, N2): one tokenizer; the receipt is exactly the printed literal
LAYOUT = {
    "two_spaces": before("  "),
    "crlf": before("\r\n"),
    "newline_indent": before("\n    "),
    "tab_tab": before("\t\t"),
    "nbsp_space": before("\xa0 "),
    "entity_nbsp_space": before("&#160; "),
    "comment_bare_amp": before("<!-- >& -->"),
    "comment_two_char_entity": before("<!-- >&acE; -->"),
    "empty_span_spaces": before("<span>  </span>"),
    "trailing_two_spaces": after("  "),
    "trailing_crlf": after("\r\n"),
    "trailing_comment": after("<!-- x -->"),
}
TARGETS = [("Q3", t.DIL, 0), ("Q3", t.DIL, 1), ("Q2", t.CORE, 0), ("Q1", t.SALES, 0)]


@pytest.mark.parametrize("q,metric,k", TARGETS)
@pytest.mark.parametrize("edit", sorted(LAYOUT))
def test_r143_layout_around_the_literal_keeps_the_exact_span(edit, q, metric, k):
    """R143: whitespace, comments and empty markup around a printed literal (primary k=0 or second statement k=1) change
    nothing: no exception escapes, the metric binds its frozen value, its receipt is exactly the primary literal, and the
    workspace validates."""
    primary = t.one(src(q), pin(q, metric)).text
    body = edit_cell(src(q), q, metric, k, LAYOUT[edit])
    ws, texts, _ = build(body, q)
    assert r1.numeric(ws)[metric] == t.expected_values(REL[q])[metric]
    assert excerpt(ws, metric) == primary
    assert r1.validates(ws, texts, REL[q])


INSIDE = {"comment_inside": "<!-- x -->", "span_inside": "<span></span>"}


@pytest.mark.parametrize("q,metric", [("Q3", t.DIL), ("Q1", t.SALES)])
@pytest.mark.parametrize("edit", sorted(INSIDE))
def test_r143_markup_inside_the_literal_never_binds(edit, q, metric):
    """R143: a span holding markup is not a printed literal; the metric is envelope_unlocated and the workspace
    validates."""
    body = edit_cell(src(q), q, metric, 0, lambda raw, lit: raw.replace(">" + lit, ">" + lit[:1] + INSIDE[edit] + lit[1:], 1))
    ws, texts, _ = build(body, q)
    assert r1.numeric(ws)[metric] == t.UNLOCATED
    assert r1.validates(ws, texts, REL[q])


@pytest.mark.parametrize("entity", ["&#49;", "&#x31;"])
def test_r143_character_reference_inside_the_literal_is_part_of_it(entity):
    """R143 control: a character reference is one unit of the printed literal; the span covers it and decodes to the
    literal."""
    body = edit_cell(src("Q3"), "Q3", t.DIL, 0, lambda raw, lit: raw.replace(">1.63", ">" + entity + ".63", 1))
    ws, texts, _ = build(body)
    assert r1.numeric(ws)[t.DIL] == t.expected_values(Q3)[t.DIL]
    assert excerpt(ws, t.DIL) == entity + ".63"
    assert r1.validates(ws, texts)


SHIFTS = {"tag_before": (-1, 0), "entity_after": (0, len("&#160;")), "n1_form": (1, len("&#160;"))}


@pytest.mark.parametrize("shift", sorted(SHIFTS))
def test_r143_validator_checks_the_span_itself_not_the_extractor(monkeypatch, shift):
    """R143: the validator refuses a wrapped present fact whose span is not exactly a printed literal of its value, even
    when the extractor itself mints that span, so that the R136 replay agrees with it."""
    body = src("Q3")
    cell = t.one(body, pin("Q3", t.DIL))
    lit_start = body.index(">1.63&#160;", cell.start, cell.end) + 1
    lit_end = lit_start + len("1.63")
    left, right = SHIFTS[shift]
    minted = receipts.receipt_for_char_span

    def misaligned(*, source, source_sha256, char_start, char_end, **kw):
        if source == body and (char_start, char_end) == (lit_start, lit_end):
            char_start, char_end = lit_start + left, lit_end + right
        return minted(source=source, source_sha256=source_sha256, char_start=char_start, char_end=char_end, **kw)

    monkeypatch.setattr(pe, "receipt_for_char_span", misaligned)
    monkeypatch.setattr(receipts, "receipt_for_char_span", misaligned)
    ws, texts, _ = build(body)
    assert excerpt(ws, t.DIL) == body[lit_start + left:lit_end + right], "wrapped receipts are minted via receipt_for_char_span"
    assert not r1.validates(ws, texts)


# ============================ R144 (N3 + locale): the outcome is a function of the bytes, in every process
_ADMIT = r"""
import sys; sys.path.insert(0, "tests")
import test_pg_envelope_f1 as t
from engine.company_intelligence import pg_envelope as pe
S = t.original(t.FY26Q3); T = t.F1Q_TABLES["FY26Q3"]
print(pe.admit(t.drop_table(t.drop_table(S, T["drivers"]), T["earnings"]), t.FY26Q3.scope).code)
print(pe.admit(t.repeat_table(t.repeat_table(S, T["drivers"]), T["earnings"]), t.FY26Q3.scope).code)
"""


def test_r144_refusal_code_is_independent_of_pythonhashseed():
    """R144: roles are considered in _ROLES order in every process, so the first missing or repeated role (earnings
    before drivers) names the code whatever the hash seed."""
    outs = set()
    for seed in ("0", "1", "4", "7"):
        env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT)}
        outs.add(subprocess.run([sys.executable, "-c", _ADMIT], env=env, cwd=ROOT, capture_output=True, text=True,
                                check=True).stdout)
    assert outs == {"required_table_missing:earnings\nrequired_table_repeated:earnings\n"}


def test_r144_month_names_never_come_from_the_locale():
    """R144: month names come from a fixed English table; nothing in the envelope formats a date through strftime."""
    text = (ROOT / "engine" / "company_intelligence" / "pg_envelope.py").read_text(encoding="utf-8")
    assert "strftime" not in text and "%B" not in text and "%b" not in text


_LOCALE = r"""
import locale, sys; sys.path.insert(0, "tests")
try:
    locale.setlocale(locale.LC_ALL, sys.argv[1])
except locale.Error:
    print("UNAVAILABLE"); raise SystemExit(0)
import test_pg_envelope_f1 as t, test_pg_envelope_f1_probes_r1 as r1
ws, _, _ = t.workspace(t.FY26Q3, t.original(t.FY26Q3), t.FY26Q3)
print(r1.numeric(ws) == t.expected_values(t.FY26Q3))
"""


@pytest.mark.parametrize("name", ["de_DE.UTF-8", "fr_FR.UTF-8"])
def test_r144_outcome_is_independent_of_the_process_locale(name):
    """R144: under a non-English process locale the Q3 original binds its frozen values."""
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    out = subprocess.run([sys.executable, "-c", _LOCALE, name], env=env, cwd=ROOT, capture_output=True, text=True,
                         check=True).stdout.strip()
    if out == "UNAVAILABLE":
        pytest.skip(f"locale {name} is not installed on this host")
    assert out == "True"


# ============================ R145 (N4), as R152 amends it: the unit rule binds both cells of an agreeing pair
@pytest.mark.parametrize("q,metric,k,printed,other", [
    ("Q3", t.DIL, 1, "1.63%", None),
    ("Q2", t.CORE, 1, None, "%"),
    ("Q3", t.SALES, 1, "$7%", None),
    ("Q1", t.SALES, 1, None, "$"),
    ("Q3", t.DIL, 0, "1.63%", None),
])
def test_r145_unit_marker_on_either_statement_is_unlocated(q, metric, k, printed, other):
    """R145 as R152 amends it: when the two statements agree, a usd_per_share literal holding '%' or a percent literal
    holding '$', in EITHER statement, makes the metric envelope_unlocated, never present."""
    body = src(q)
    cell = t.one(body, pin(q, metric, k))
    if printed is None:
        printed = ("$" + cell.text) if other == "$" else (cell.text + "%")
        other = None
    body = r1.set_cell(body, pin(q, metric, k), printed)
    if other and other.startswith("second:"):
        body = r1.set_cell(body, pin(q, metric, 1), other.split(":", 1)[1])
    ws, _, _ = build(body, q)
    assert r1.numeric(ws)[metric] == t.UNLOCATED


@pytest.mark.parametrize("q,metric,marker", [("Q3", t.DIL, "%"), ("Q1", t.SALES, "$")])
def test_r152_a_disagreeing_pair_is_a_conflict_whatever_its_unit_markers(q, metric, marker):
    """R152: the two statements are compared as the frozen witness reads them, unit markers ignored.  A pair whose
    values differ is a conflict, exactly as t.witness_outcome says, even when one cell holds a marker R145 forbids."""
    body = src(q)
    primary = t.one(body, pin(q, metric, 0)).text
    body = r1.set_cell(body, pin(q, metric, 0), ("$" + primary) if marker == "$" else (primary + "%"))
    body = r1.set_cell(body, pin(q, metric, 1), "99")
    ws, _, _ = build(body, q)
    assert r1.numeric(ws)[metric] == t.CONFLICT == t.witness_outcome(body, REL[q])[metric]


# ============================ R146 (N5): carriage returns are tolerated
CR_FORMS = {
    "type_line_crlf": lambda s: t.once(s, "<TYPE>EX-99.1\n", "<TYPE>EX-99.1\r\n"),
    "marker_line_crlf": lambda s: t.once(s, MARKER, MARKER[:-1] + "\r\n"),
    "every_line_crlf": lambda s: s.replace("\r\n", "\n").replace("\n", "\r\n"),
}


@pytest.mark.parametrize("q", ["Q1", "Q2", "Q3"])
@pytest.mark.parametrize("form", sorted(CR_FORMS))
def test_r146_carriage_returns_are_the_same_document(form, q):
    """R146: CRLF on the TYPE line, on the generator marker line, or on every line is the same document: admitted, every
    frozen value bound, and the workspace validates."""
    ws, texts, _ = build(CR_FORMS[form](src(q)), q)
    assert r1.numeric(ws) == t.expected_values(REL[q])
    assert r1.validates(ws, texts, REL[q])


@pytest.mark.parametrize("edit,detail", [
    (lambda s: t.once(s, "<TYPE>EX-99.1\n", "<TYPE>EX-99.1 \n"), "envelope_refused:not_ex_99_1"),
    (lambda s: t.once(s, "<TYPE>EX-99.1\n", "<TYPE>EX-99.1\r\r\n"), "envelope_refused:not_ex_99_1"),
    (lambda s: t.once(s, "\n" + MARKER, "\nx" + MARKER), "envelope_refused:generator_not_workiva"),
    (lambda s: t.once(s, MARKER, MARKER[:-1] + " \n"), "envelope_refused:generator_not_workiva"),
], ids=["type_trailing_space", "type_two_crs", "marker_not_line_start", "marker_trailing_space"])
def test_r146_only_one_line_terminator_is_tolerated(edit, detail):
    """R146 control: exactly one trailing CR is tolerated; any other text on the TYPE or marker line is refused."""
    ws, _, _ = build(edit(src("Q3")))
    assert r1.refusal_details(ws) == {detail}


# ============================ R147 (N6): a header year is defined only by agreement
def _year_row(q, first, second):
    s = src(q)
    earnings = TAB[q]["earnings"]
    t0, t1 = t.tables(s)[earnings]
    rows = list(t._ROW.finditer(s, t0, t1))
    cal = int(REL[q].fiscal[2][:4])
    year_row = next(i for i, row in enumerate(t.grid(s, earnings)) if any(c.text == str(cal) and c.row == i for c in row))
    extra = (f'<tr><td colspan="3"></td><td colspan="3">{cal + first}</td><td colspan="3"></td>'
             f'<td colspan="3">{cal + second}</td><td colspan="6"></td></tr>')
    return s[:rows[year_row].start()] + extra + s[rows[year_row].start():]


@pytest.mark.parametrize("q", ["Q2", "Q3"])
def test_r147_contradictory_year_headers_leave_no_header_year(q):
    """R147: two year headers naming different years over one earnings cell leave it no header year; DIL and PDIL are
    envelope_unlocated even when the highlights table is edited to agree with the swapped reading (the auditor's N6)."""
    fy = REL[q].fiscal[0]
    body = t.swap(_year_row(q, -1, 0), TAB[q]["highlights"], str(fy), str(fy - 1))
    ws, texts, _ = build(body, q)
    got = r1.numeric(ws)
    assert (got[t.DIL], got[t.PDIL]) == (t.UNLOCATED, t.UNLOCATED)
    assert r1.validates(ws, texts, REL[q])


@pytest.mark.parametrize("q", ["Q2", "Q3"])
def test_r147_agreeing_year_headers_still_bind(q):
    """R147 control: a second year header naming the same years in the same columns changes nothing."""
    ws, texts, _ = build(_year_row(q, 0, -1), q)
    assert r1.numeric(ws) == t.expected_values(REL[q])
    assert r1.validates(ws, texts, REL[q])


# ============================ R148 (N7): a duration class never folds onto the quarter's
@pytest.mark.parametrize("label", ["FY 2026", "Fiscal Year 2026", "July - March 2026", "October - March 2026"])
def test_r148_orgrec_relabelled_for_another_duration_is_unknown(label):
    """R148: a fiscal-year label or a month range that is not three months keeps its own token, so the relabelled organic
    reconciliation is unknown_table:t11 and no fact is present."""
    ws, _, _ = build(t.in_table(src("Q3"), TAB["Q3"]["organic_reconciliation"], CUR["Q3"], label))
    assert r1.refusal_details(ws) == {"envelope_refused:unknown_table:t11"}


@pytest.mark.parametrize("key", ["FY25Q4", "FY26Q4"])
def test_r148_fiscal_year_orgrec_from_an_annual_release_is_unknown(key):
    """R148: the fiscal-year organic reconciliation of an F2-A release (its table 14) matches no F1-Q role; put in place
    of the Q3 organic reconciliation it is unknown_table:t11."""
    annual = t.original(t.RELEASES[key])
    a, b = t.tables(annual)[14]
    s = src("Q3")
    c0, c1 = t.tables(s)[TAB["Q3"]["organic_reconciliation"]]
    ws, _, _ = build(s[:c0] + annual[a:b] + s[c1:])
    assert r1.refusal_details(ws) == {"envelope_refused:unknown_table:t11"}


# ============================ R149 (N8): every '<table' start tag is a table
def test_r149_unclosed_table_after_the_last_table_is_unknown():
    """R149: an unclosed '<table' start tag runs to the end of the source and takes the next ordinal; the injected table
    is unknown_table:t16 and no fact is present."""
    s = src("Q3")
    last = t.tables(s)[-1][1]
    ws, _, _ = build(s[:last] + "<table><tr><td>Pro Forma Combined Company</td></tr>" + s[last:])
    assert r1.refusal_details(ws) == {"envelope_refused:unknown_table:t16"}


def test_r149_unclosed_table_that_swallows_later_tables_is_nested():
    """R149: an unclosed '<table' start before table 8 contains every later table, so t8 is nested: unknown_table:t8."""
    s = src("Q3")
    a = t.tables(s)[8][0]
    ws, _, _ = build(s[:a] + "<table>" + s[a:])
    assert r1.refusal_details(ws) == {"envelope_refused:unknown_table:t8"}


def test_r149_stray_table_close_is_ignored():
    """R149 control: a '</table>' with no open table is ignored, as a browser ignores it."""
    s = src("Q3")
    a = t.tables(s)[8][0]
    ws, texts, _ = build(s[:a] + "</table>" + s[a:])
    assert r1.numeric(ws) == t.expected_values(Q3)
    assert r1.validates(ws, texts)
