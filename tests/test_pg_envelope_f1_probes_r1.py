"""Frozen R1 probe suite for the CDV-1 T1 F1-Q envelope (seat ruling R122-R130).

Adapted by the seat from the independent Opus audit's probes of the envelope build at c6bebf3a9d53 (R116-R121; report
research/consumer_defensive/cdv1_program/reviews/OPUS_T1_ENVELOPE_AUDIT_R1_2026-09-25.md).  Each case states the outcome
the bytes and the rulings require (SEAT_RULING_T1_ENVELOPE_R1_2026-09-25.md): the seat corrected the audit's four probe
artefacts, dropped its one white-box control, and added the cases the rulings name.  Byte-identical from the freeze; a
repair never edits it.
"""
from __future__ import annotations

import copy
import dataclasses
import functools
import html
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_pg_envelope_f1 as t  # noqa: E402  (frozen suite helpers; engine-free reader)
from engine.company_intelligence.economic_observations import (  # noqa: E402
    EconomicObservationError, validate_selected_facts)

Q1, Q2, Q3 = t.FY26Q1, t.FY26Q2, t.FY26Q3
T = t.F1Q_TABLES["FY26Q3"]
P = t.pins(Q3)
S = t.original(Q3)
ORIG = t.expected_values(Q3)
GROOM = "pg_grooming_organic_sales_growth_pct"
TOTALS = [t.SALES, t.TV, t.OV, t.PRICE, t.MIX, t.FX, t.OTHER]


# ---------------------------------------------------------------- helpers
@functools.lru_cache(maxsize=None)
def built(body: str, rel_key: str = "FY26Q3", period=None):
    rel = t.RELEASES[rel_key]
    return t.workspace(rel, body, period or rel)


def outcome(ws) -> dict:
    out = {}
    for m, r in t.by_metric(ws).items():
        if "value" in r:
            out[m] = r["value"]
            continue
        d = r["typed_absence"]["detail"]
        for pre, name in (("envelope_conflict", t.CONFLICT), ("envelope_unlocated", t.UNLOCATED),
                          ("envelope_excluded", t.EXCLUDED)):
            if d.startswith(pre):
                out[m] = name
                break
        else:
            out[m] = d
    return out


def numeric(ws) -> dict:
    o = outcome(ws)
    return {m: o[m] for m in t.NUMERIC}


def present(ws) -> dict:
    return {m: r["value"] for m, r in t.by_metric(ws).items() if "value" in r}


def validates(ws, texts, rel=Q3) -> bool:
    try:
        validate_selected_facts(ws, source_texts=texts, fiscal_scope=rel.scope)
        return True
    except EconomicObservationError:
        return False


def cell(source, pin):
    return t.one(source, pin)


def set_cell(source, pin, new):
    c = cell(source, pin)
    return source[:c.start] + new + source[c.end:]


def swap_cells(source, pa, pb):
    x, y = sorted((cell(source, pa), cell(source, pb)), key=lambda c: c.start)
    return source[:x.start] + source[y.start:y.end] + source[x.end:y.start] + source[x.start:x.end] + source[y.end:]


def row_span(source, ordinal, label):
    t0, t1 = t.tables(source)[ordinal]
    rows = t.grid(source, ordinal)
    idx = [r for r, row in enumerate(rows) if any(c.row == r and t.norm(c.text) == t.norm(label) for c in row)]
    assert len(idx) == 1, (label, idx)
    m = list(t._ROW.finditer(source, t0, t1))[idx[0]]
    return m.start(), m.end()


def dup_row(source, ordinal, label, rewrite=None):
    a, b = row_span(source, ordinal, label)
    copy_ = source[a:b] if rewrite is None else rewrite(source[a:b])
    return source[:b] + copy_ + source[b:]


def in_table_all(source, ordinal, mapping):
    t0, t1 = t.tables(source)[ordinal]
    seg = source[t0:t1]
    for old, new in mapping:
        seg = seg.replace(old, new)
    return source[:t0] + seg + source[t1:]


def refusal_details(ws) -> set:
    return {(r.get("typed_absence") or {}).get("detail") for r in t.pg_rows(ws)}


def all_envelope(ws) -> bool:
    return all(str((r.get("typed_absence") or {}).get("detail", "envelope_")).startswith("envelope_") or "value" in r
               for r in t.pg_rows(ws))


# ================================================================ F1 cross-table swaps that keep labels
F1 = {  # name -> (pin a, pin b, metrics that must conflict)
    "sales_vs_org": (P[t.ORG][0], P[t.SALES][0], [t.ORG, t.SALES]),
    "highlights_core_vs_gaap": (P[t.DIL][1], P[t.CORE][1], [t.DIL, t.CORE]),
    "earnings_vs_core_rec": (P[t.DIL][0], P[t.CORE][0], [t.DIL, t.CORE]),
    "drivers_price_vs_segdrivers_mix": (P[t.PRICE][1], P[t.MIX][0], [t.PRICE, t.MIX]),
    "orgrec_beauty_vs_segdrivers_grooming": (P[t.BEAUTY][0], P[GROOM][1], [t.BEAUTY, GROOM]),
}


@pytest.mark.parametrize("name", sorted(F1))
def test_f1_cross_table_swap_conflicts_never_binds(name):
    """expected: the swapped metrics are cross_check_conflict; every other metric keeps its oracle value."""
    a, b, metrics = F1[name]
    body = swap_cells(S, a, b)
    ws, texts, _ = built(body)
    got = numeric(ws)
    assert got == t.witness_outcome(body, Q3)
    for m in metrics:
        assert got[m] == t.CONFLICT, (m, got[m])
    assert validates(ws, texts)


# ================================================================ F2 duplicate labels
F2 = {  # name -> (role, row label, metrics that must be unlocated)
    "orgrec_total_company": ("organic_reconciliation", "Total Company", [t.ORG]),
    "segdrivers_total_pg": ("segment_drivers", "Total P&G", TOTALS + [t.ORG]),
    "drivers_total_company": ("drivers", "Total Company", TOTALS),
    "earnings_diluted": ("earnings", "Diluted", [t.DIL, t.PDIL, t.REPG]),
    "cvya_core_eps": ("change_versus_year_ago", "Core EPS", [t.COREG]),
    "highlights_diluted_eps": ("highlights", "Diluted EPS", [t.DIL, t.PDIL, t.REPG]),
    "orgrec_beauty": ("organic_reconciliation", "Beauty", [t.BEAUTY]),
}


@pytest.mark.parametrize("name", sorted(F2))
def test_f2_duplicate_label_is_unlocated_never_first_match(name):
    """expected: a repeated row label in a pinned table leaves every metric it addresses unlocated."""
    role, label, metrics = F2[name]
    body = dup_row(S, T[role], label)
    ws, texts, _ = built(body)
    got = numeric(ws)
    for m in metrics:
        assert got[m] == t.UNLOCATED, (m, got[m])
    assert set(present(ws).items()) <= set(ORIG.items())
    assert validates(ws, texts)


def test_f2_second_total_company_by_renaming_beauty():
    """expected: renaming org-rec 'Beauty' to 'Total Company' makes ORG and Beauty unlocated."""
    a, b = row_span(S, T["organic_reconciliation"], "Beauty")
    body = S[:a] + S[a:b].replace(">Beauty<", ">Total Company<", 1) + S[b:]
    assert body != S
    ws, _, _ = built(body)
    got = numeric(ws)
    assert got[t.ORG] == t.UNLOCATED and got[t.BEAUTY] == t.UNLOCATED, (got[t.ORG], got[t.BEAUTY])


# ================================================================ F3 header geometry (one statement edited)
def _header_cell_td(source, ordinal, text):
    t0, t1 = t.tables(source)[ordinal]
    rows = t.grid(source, ordinal)
    hits = [c for r, row in enumerate(rows) for c in row if c.row == r and c.text == text]
    assert hits, text
    c = hits[0]
    open_ = source.rfind("<td", t0, c.start)
    return open_, c


def _colspan_plus_one(source, ordinal, text):
    open_, c = _header_cell_td(source, ordinal, text)
    tag = source[open_:c.start]
    m = re.search(r'colspan="(\d+)"', tag)
    new = tag[:m.start()] + f'colspan="{int(m.group(1)) + 1}"' + tag[m.end():] if m else tag.replace("<td", '<td colspan="2"', 1)
    return source[:open_] + new + source[c.start:]


F3 = {
    "earnings_2026_colspan_plus1": lambda s: _colspan_plus_one(s, T["earnings"], "2026"),
    "earnings_empty_cell_before_2026": lambda s: (lambda o: s[:o[0]] + "<td></td>" + s[o[0]:])(_header_cell_td(s, T["earnings"], "2026")),
    "highlights_2026_colspan_plus1": lambda s: _colspan_plus_one(s, T["highlights"], "2026"),
    "segdrivers_price_colspan_plus1": lambda s: _colspan_plus_one(s, T["segment_drivers"], "Price"),
    "drivers_total_company_rowspan2": lambda s: (lambda o: s[:o[0]] + s[o[0]:o[1].start].replace("<td", '<td rowspan="2"', 1) + s[o[1].start:])(_header_cell_td(s, T["drivers"], "Total Company")),
    "orgrec_osg_header_moved_one_col": lambda s: (lambda o: s[:o[0]] + "<td></td>" + s[o[0]:])(_header_cell_td(s, T["organic_reconciliation"], "Organic Sales Growth")),
}


@pytest.mark.parametrize("name", sorted(F3))
def test_f3_header_geometry_edit_in_one_statement_never_binds_another_value(name):
    """expected: after a one-statement geometry edit, every present fact still equals its oracle value (else absent)."""
    body = F3[name](S)
    assert body != S
    ws, texts, _ = built(body)
    got = present(ws)
    assert set(got.items()) <= set(ORIG.items()), {m: (v, ORIG[m]) for m, v in got.items() if v != ORIG[m]}
    assert numeric(ws) == t.witness_outcome(body, Q3)
    assert validates(ws, texts)


# ================================================================ F4 literal-parse variants (both statements set alike)
NOT_NUMBERS = ["n/a", "nm", "NM", "bps", "1.63*", "−1%", "(1.2)x", "2.0 pts", "$(0.05)", "1%%", "1.6.3", "1,63",
               "–", "-", "— per share"]


@pytest.mark.parametrize("printed", NOT_NUMBERS)
def test_f4_non_number_in_both_eps_statements_is_never_a_number(printed):
    """expected (R128): a cell R118 does not name is never parsed as a number.  pg_diluted_eps is unlocated and every
    other metric keeps its value; or, where the text reads as a label ("2.0 pts"), the highlights table is unknown (R116
    check 4) and every row is refused."""
    body = set_cell(set_cell(S, P[t.DIL][0], printed), P[t.DIL][1], printed)
    ws, _, _ = built(body)
    if refusal_details(ws) == {"envelope_refused:unknown_table:t2"}:
        return
    assert numeric(ws) == {**ORIG, t.DIL: t.UNLOCATED}, numeric(ws)


def test_f4_bare_em_dash_in_both_eps_cells_is_not_zero():
    """expected: R118 makes '—' zero only as '—%' or beside a '%' unit cell; a bare '—' EPS ($ cell beside) is unlocated."""
    body = set_cell(set_cell(S, P[t.DIL][0], "—"), P[t.DIL][1], "—")
    ws, _, _ = built(body)
    assert numeric(ws)[t.DIL] == t.UNLOCATED, numeric(ws)[t.DIL]


def test_f4_bare_em_dash_primary_with_zero_second_is_not_bound():
    """expected: a primary EPS cell printing a bare '—' ($ beside, no %) is not a number, so DIL is unlocated."""
    body = set_cell(set_cell(S, P[t.DIL][0], "—"), P[t.DIL][1], "0.00")
    ws, _, _ = built(body)
    assert numeric(ws)[t.DIL] == t.UNLOCATED, numeric(ws)[t.DIL]


def test_f4_bare_em_dash_in_single_percent_cell_is_not_zero():
    """expected: '—' alone in a one-cell percent slot (no '%' unit cell beside) is not named by R118: REPG unlocated."""
    body = set_cell(set_cell(S, P[t.REPG][0], "—"), P[t.REPG][1], "—")
    ws, _, _ = built(body)
    assert numeric(ws)[t.REPG] == t.UNLOCATED, numeric(ws)[t.REPG]


@pytest.mark.parametrize("printed, value", [("(0)%", 0.0), ("+2%", 2.0), ("$1.63", 1.63)])
def test_f4_control_numeric_literals_bind(printed, value):
    """control: grammar literals bind their value when both statements print them."""
    pin = t.DIL if "." in printed else t.REPG
    body = set_cell(set_cell(S, P[pin][0], printed), P[pin][1], printed)
    ws, texts, _ = built(body)
    assert numeric(ws)[pin] == pytest.approx(value)
    assert validates(ws, texts)


@pytest.mark.parametrize("printed", ["+ 2%", "1 63", "１.６３", "3 %", "— %"])
def test_f4_spaced_or_non_ascii_digit_cell_is_not_a_literal(printed):
    """expected (R128): after trimming, a figure holds no whitespace and only ASCII digits, so the metric is unlocated and
    every other metric keeps its value.  The frozen literal() is looser; no frozen case exercises the difference."""
    pin = t.REPG if "%" in printed else t.DIL
    body = set_cell(set_cell(S, P[pin][0], printed), P[pin][1], printed)
    ws, _, _ = built(body)
    assert numeric(ws) == {**ORIG, pin: t.UNLOCATED}, numeric(ws)


# ================================================================ F5 wrapper and markup
def _refused_everywhere(ws, detail_re):
    rows = t.pg_rows(ws)
    assert not present(ws), present(ws)
    details = refusal_details(ws)
    assert len(details) == 1 and re.fullmatch(detail_re, next(iter(details))), details


F5_REFUSE = {  # name -> (rewrite, expected refusal detail regex)
    "type_line_in_body_only": (lambda s: t.once(s, "<TYPE>EX-99.1\n", "<TYPE>EX-99.2\n").replace("<TEXT>\n", "<TEXT>\n<TYPE>EX-99.1\n", 1),
                               r"envelope_refused:not_ex_99_1"),
    "two_type_lines": (lambda s: t.once(s, "<TYPE>EX-99.1\n", "<TYPE>EX-99.1\n<TYPE>EX-99.2\n"), r"envelope_refused:not_ex_99_1"),
    "crlf_whole_body": (lambda s: s.replace("\n", "\r\n"), r"envelope_refused:.+|F1Q"),
    "crlf_after_document_tag": (lambda s: "<DOCUMENT>\r\n" + s[len("<DOCUMENT>\n"):], r"envelope_refused:.+|F1Q"),
    "lowercase_type_tag": (lambda s: t.once(s, "<TYPE>EX-99.1\n", "<type>EX-99.1\n"), r"envelope_refused:not_ex_99_1"),
    "no_type_line": (lambda s: t.once(s, "<TYPE>EX-99.1\n", ""), r"envelope_refused:not_ex_99_1"),
    "no_text_tag": (lambda s: t.once(s, "<TEXT>\n", ""), r"envelope_refused:not_ex_99_1"),
    "bom_before_document": (lambda s: "﻿" + s, r"envelope_refused:.+|F1Q"),
    "nested_table_in_orgrec": (lambda s: t.in_table(s, T["organic_reconciliation"], ">Beauty<", "><table><tr><td>x</td></tr></table>Beauty<"),
                               r"envelope_refused:unknown_table:t11"),
    "lowercase_document_tag": (lambda s: "<document>" + s[len("<DOCUMENT>"):], r"envelope_refused:.+|F1Q"),
    "blank_line_before_document": (lambda s: "\n" + s, r"envelope_refused:.+|F1Q"),
}


@pytest.mark.parametrize("name", sorted(F5_REFUSE))
def test_f5_wrapper_and_markup(name):
    """expected (R122, R129): a body that begins with the EDGAR <DOCUMENT> wrapper (optional BOM and leading whitespace,
    any case) is admitted to F1-Q or refused with the R116 code; it never reaches the legacy reader."""
    rewrite, detail_re = F5_REFUSE[name]
    body = rewrite(S)
    assert body != S
    ws, texts, _ = built(body)
    assert all_envelope(ws), sorted({(r.get("typed_absence") or {}).get("detail", "")[:50] for r in t.pg_rows(ws)})[:3]
    if "F1Q" in detail_re and present(ws):
        assert set(present(ws).items()) <= set(ORIG.items())
        return
    _refused_everywhere(ws, detail_re.replace("|F1Q", ""))


def test_f5_control_uppercase_tags_still_bind():
    """control: upper-case TABLE/TR/TD tags bind the same oracle values."""
    body = S
    for a, b in (("<table", "<TABLE"), ("</table>", "</TABLE>"), ("<tr", "<TR"), ("</tr>", "</TR>"), ("<td", "<TD"), ("</td>", "</TD>")):
        body = body.replace(a, b)
    ws, texts, _ = built(body)
    assert numeric(ws) == ORIG
    assert validates(ws, texts)


def test_f5_control_comment_in_primary_cell():
    """control: an HTML comment carrying a number inside the primary cell does not change the bound value."""
    body = set_cell(S, P[t.DIL][0], "<!-- 9.99 -->1.63")
    ws, _, _ = built(body)
    assert numeric(ws)[t.DIL] == pytest.approx(1.63)


# ================================================================ F6 issuer
F6 = {
    "short_name_in_masthead": lambda s: t.in_table(s, 0, "The Procter &#38; Gamble Company", "Procter &#38; Gamble"),
    "masthead_after_headline": lambda s: (lambda a, b: s[:a[0]] + s[b[0]:b[1]] + s[a[1]:b[0]] + s[a[0]:a[1]] + s[b[1]:])(*t.tables(s)[:2]),
    "masthead_removed": lambda s: t.drop_table(s, 0),
}


@pytest.mark.parametrize("name", sorted(F6))
def test_f6_issuer(name):
    """expected: envelope_refused:issuer_not_pg on every row."""
    ws, texts, _ = built(F6[name](S))
    _refused_everywhere(ws, r"envelope_refused:issuer_not_pg")
    assert validates(ws, texts)


# ================================================================ F7 quarter
Q3_FY27 = dataclasses.replace(Q3, key="FY27Q3x", fiscal=(2027, 3, "2027-03-31"),
                              scope=("2027-01-01", "2027-03-31", "2026-01-01", "2026-03-31"))
TITLES = {  # the period titles the originals print (seat census, R124): range title, its year-ago, month/day title, years
    "FY26Q1": ("July - September 2025", "July - September 2024", "Three Months Ended September 30", "2025", "2024"),
    "FY26Q2": ("October - December 2025", "October - December 2024", "Three Months Ended December 31", "2025", "2024"),
    "FY26Q3": ("January - March 2026", "January - March 2025", "Three Months Ended March 31", "2026", "2025"),
}
OTHER_QUARTER_END = {"FY26Q1": "Three Months Ended December 31", "FY26Q2": "Three Months Ended March 31",
                     "FY26Q3": "Three Months Ended December 31"}


@pytest.mark.parametrize("key", ["FY26Q1", "FY26Q2", "FY26Q3"])
def test_f7_drivers_title_year_ago(key):
    """expected: envelope_refused:quarter_mismatch (R116 check 6 reads the drivers title)."""
    rel, (_, _, month_day, now, ago) = t.RELEASES[key], TITLES[key]
    body = t.in_table(t.original(rel), t.F1Q_TABLES[key]["drivers"], f"{month_day}, {now}", f"{month_day}, {ago}")
    ws, _, _ = built(body, key)
    _refused_everywhere(ws, r"envelope_refused:quarter_mismatch")


def test_f7_drivers_title_date_removed():
    """expected: refused.  A title without its year no longer reads as a period title, so the table is unknown (check 4
    precedes check 6); a reader that still folds it reaches quarter_mismatch."""
    ws, _, _ = built(t.in_table(S, T["drivers"], "2026", ""))
    _refused_everywhere(ws, r"envelope_refused:(unknown_table:t6|quarter_mismatch)")


def test_f7_scope_fiscal_year_changed():
    """expected: envelope_refused:quarter_mismatch."""
    ws, _, _ = built(S, "FY26Q3", Q3_FY27)
    _refused_everywhere(ws, r"envelope_refused:quarter_mismatch")


def _in_role(rel, role) -> set[str]:
    """The metrics with any pinned statement in ``role`` (the frozen pins)."""
    ordinal = t.F1Q_TABLES[rel.key][role]
    return {m for m, pair in t.pins(rel).items() if any(p[0] == ordinal for p in pair)}


def _retitled(rel, case: str) -> tuple[str, str]:
    """(the release's bytes with one pinned table titled for another period, that table's role)."""
    s, tab = t.original(rel), t.F1Q_TABLES[rel.key]
    range_now, range_ago, month_day, now, ago = TITLES[rel.key]
    if case == "segment_drivers_titled_year_ago":
        return t.in_table(s, tab["segment_drivers"], range_now, range_ago), "segment_drivers"
    if case == "organic_reconciliation_titled_year_ago":
        return t.in_table(s, tab["organic_reconciliation"], range_now, range_ago), "organic_reconciliation"
    if case == "earnings_titled_another_quarter_end":
        return t.in_table(s, tab["earnings"], month_day, OTHER_QUARTER_END[rel.key]), "earnings"
    if case == "core_reconciliation_years_swapped":
        return in_table_all(s, tab["core_reconciliation"], [(now, "@@"), (ago, now), ("@@", ago)]), "core_reconciliation"
    raise KeyError(case)


F7_TITLE_CASES = ("segment_drivers_titled_year_ago", "organic_reconciliation_titled_year_ago",
                  "earnings_titled_another_quarter_end", "core_reconciliation_years_swapped")


@pytest.mark.parametrize("key", ["FY26Q1", "FY26Q2", "FY26Q3"])
@pytest.mark.parametrize("case", F7_TITLE_CASES)
def test_f7_statement_titled_for_another_period_is_unlocated(case, key):
    """expected (R124, R125): the document stays admitted; every metric with a pinned statement in the retitled table is
    unlocated, never bound with the scope period; every other metric keeps its oracle value; the validator agrees."""
    rel = t.RELEASES[key]
    body, role = _retitled(rel, case)
    ws, texts, _ = built(body, key)
    hit = _in_role(rel, role)
    want = {m: (t.UNLOCATED if m in hit else v) for m, v in t.expected_values(rel).items()}
    assert numeric(ws) == want, ({m: numeric(ws)[m] for m in hit}, refusal_details(ws))
    assert validates(ws, texts, rel)


def test_f7_segment_drivers_title_removed_is_never_bound():
    """expected (R124): a pinned table that prints no period title locates nothing; its metrics are unlocated with every
    other value kept, or, if the lane anchors the role on its title, the table is unknown and every row is refused."""
    ws, _, _ = built(t.in_table(S, T["segment_drivers"], TITLES["FY26Q3"][0], ""))
    if refusal_details(ws) == {"envelope_refused:unknown_table:t3"}:
        return
    hit = _in_role(Q3, "segment_drivers")
    assert numeric(ws) == {m: (t.UNLOCATED if m in hit else v) for m, v in ORIG.items()}, numeric(ws)


# ================================================================ F8 the footnote rule
def _between(s, ordinal):
    return t.tables(s)[ordinal][1], t.tables(s)[ordinal + 1][0]


def _note_moved(s):
    a, b = _between(s, T["core_reconciliation"])
    note = s[a:b]
    s2 = s[:a] + s[b:]
    c = t.tables(s2)[T["change_versus_year_ago"]][1]
    return s2[:c] + note + s2[c:]


def _note_other_date(s):
    a, b = _between(s, T["core_reconciliation"])
    seg = s[a:b]
    assert seg.count("2025") == 1
    return s[:a] + seg.replace("2025", "2024") + s[b:]


@functools.lru_cache(maxsize=None)
def _q1_prior_table() -> str:
    q1 = t.original(Q1)
    a, b = t.tables(q1)[t.F1Q_TABLES["FY26Q1"]["prior_core_reconciliation"]]
    return q1[a:b]


def _inject_prior_table(s, value=None):
    table = _q1_prior_table()
    if value is not None:
        cell_ = t.one(table, (0, "Diluted net earnings per common share (1)", "Core(Non-GAAP)"))
        table = table[:cell_.start] + value + table[cell_.end:]
    end = t.tables(s)[-1][1]
    return s[:end] + table + s[end:]


F8 = {  # name -> (rewrite, expected PCORE outcome)
    "note_moved_after_cvya": (_note_moved, t.UNLOCATED),
    "note_other_date": (_note_other_date, t.UNLOCATED),
    "note_present_gaap_disagrees": (lambda s: set_cell(s, P[t.PCORE][1], "1.55"), t.CONFLICT),
    "q3_note_removed_plus_injected_q1_prior_core_table": (
        lambda s: _inject_prior_table(t.once(s, "no adjustments to or reconciling items", "adjustments to and reconciling items"), "1.54"),
        t.UNLOCATED),
    "q3_injected_q1_prior_core_table_note_present": (lambda s: _inject_prior_table(s), ORIG[t.PCORE]),
}


@pytest.mark.parametrize("name", sorted(F8))
def test_f8_footnote_rule_follows_the_frozen_pins(name):
    """expected (R127): PCORE follows the frozen Q3 pins (core-rec GAAP (1) column + the footnote), never an injected table."""
    rewrite, want = F8[name]
    ws, texts, _ = built(rewrite(S))
    got = numeric(ws)[t.PCORE]
    assert got == want, (got, want)


# ================================================================ F9 validator
def _q3():
    ws, texts, bound = t.case("FY26Q3")
    return copy.deepcopy(ws), texts, bound


def _row(ws, m):
    return next(f for f in ws["facts"] if isinstance(f, dict) and f.get("metric") == m)


def _v_authority(ws, b):
    _row(ws, t.REC)["typed_absence"]["authority"] = "authoritative"


def _v_subject(ws, b):
    _row(ws, t.REC)["typed_absence"]["subject"] = t.CORE


def _v_absence_schema(ws, b):
    _row(ws, t.REC)["typed_absence"]["schema"] = "forged.v0"


def _v_missing_fields(ws, b):
    _row(ws, t.REC)["typed_absence"]["missing_fields"] = ["value"]


def _v_row_schema(ws, b):
    _row(ws, t.DIL)["schema"] = "event_fact.v0"


def _v_present_plus_absence(ws, b):
    _row(ws, t.DIL)["typed_absence"] = copy.deepcopy(_row(ws, t.REC)["typed_absence"])


def _v_extra_key(ws, b):
    _row(ws, t.DIL)["status"] = "verified_by_hand"


def _v_display_excerpt(ws, b):
    _row(ws, t.DIL)["source_span"]["display_excerpt"] = "9.99"


def _v_text_sha(ws, b):
    _row(ws, t.DIL)["source_span"]["receipt"]["text_sha256"] = "0" * 64


def _v_segment_bytes(ws, b):
    _row(ws, t.DIL)["source_span"]["receipt"]["segment_bytes"] = 1


def _v_segment_sha(ws, b):
    _row(ws, t.DIL)["source_span"]["receipt"]["segment_sha256"] = "0" * 64


def _v_locator(ws, b):
    _row(ws, t.DIL)["source_span"]["locator"]["span_start_byte"] = 0


def _v_bool_value(ws, b):
    assert _row(ws, t.PRICE)["value"] == 1.0
    _row(ws, t.PRICE)["value"] = True


def _v_nonmapping_fact(ws, b):
    ws["facts"].append("junk")


def _v_unknown_pg_metric(ws, b):
    extra = copy.deepcopy(_row(ws, t.DIL)); extra["metric"] = "pg_forged_metric"; ws["facts"].append(extra)


def _v_prior_year_column(ws, b):
    c = t.one(b.source, P[t.PDIL][0])
    ws["facts"][ws["facts"].index(_row(ws, t.DIL))] = t._forged_present(ws, b, t.DIL, c, "1.54", 1.54, Q3.scope[1])


def _v_period(ws, b):
    _row(ws, t.DIL)["period"] = Q3.scope[3]


def _v_unit(ws, b):
    _row(ws, t.DIL)["unit"] = "percent"


def _v_basis(ws, b):
    _row(ws, t.DIL)["basis"] = "core_non_gaap"


def _v_sha(ws, b):
    _row(ws, t.DIL)["source_span"]["receipt"]["source_sha256"] = "0" * 64


def _v_missing_row(ws, b):
    ws["facts"].remove(_row(ws, t.DIL))


def _v_duplicate_row(ws, b):
    ws["facts"].append(copy.deepcopy(_row(ws, t.DIL)))


V_REFUSE = {k[3:]: v for k, v in globals().items() if k.startswith("_v_")}


@pytest.mark.parametrize("name", sorted(V_REFUSE))
def test_f9_validator_refuses_a_tampered_admitted_workspace(name):
    """expected: EconomicObservationError (the S0 validator refuses every one of these shapes)."""
    ws, texts, b = _q3()
    V_REFUSE[name](ws, b)
    with pytest.raises(EconomicObservationError):
        validate_selected_facts(ws, source_texts=texts, fiscal_scope=Q3.scope)


def test_f9_control_rows_reordered_accepted():
    """control: row order is not identity; the validator accepts reordered facts."""
    ws, texts, _ = _q3()
    ws["facts"].reverse()
    validate_selected_facts(ws, source_texts=texts, fiscal_scope=Q3.scope)


def test_f9_conflict_presented_as_present():
    """expected: in mutation period_single, a DIL present at the 1.63 cell (now under 2025) is refused."""
    ws, texts, b = t.case("mutation:period_single")
    ws = copy.deepcopy(ws)
    c = next(x for x in t.locate(b.source, (T["earnings"], "Diluted", "2025")))
    ws["facts"][ws["facts"].index(_row(ws, t.DIL))] = t._forged_present(ws, b, t.DIL, c, "1.63", 1.63, Q3.scope[1])
    with pytest.raises(EconomicObservationError):
        validate_selected_facts(ws, source_texts=texts, fiscal_scope=Q3.scope)


def test_f9_unlocated_dressed_as_conflict():
    """expected: in note_removed, PCORE re-labelled cross_check_conflict is refused."""
    ws, texts, _ = t.case("mutation:note_removed")
    ws = copy.deepcopy(ws)
    ab = _row(ws, t.PCORE)["typed_absence"]; ab["reason"] = "cross_check_conflict"; ab["detail"] = f"envelope_conflict:{t.PCORE}"
    with pytest.raises(EconomicObservationError):
        validate_selected_facts(ws, source_texts=texts, fiscal_scope=Q3.scope)


@pytest.mark.parametrize("field, value", [("authority", "authoritative"), ("subject", "pg_core_eps"), ("reason", "cross_check_conflict")])
def test_f9_refused_document_row_tampered(field, value):
    """expected: on a refused document, a row whose typed absence is tampered is refused."""
    ws, texts, _ = t.case("refused:type_ex_99_2")
    ws = copy.deepcopy(ws)
    t.pg_rows(ws)[0]["typed_absence"][field] = value
    with pytest.raises(EconomicObservationError):
        validate_selected_facts(ws, source_texts=texts, fiscal_scope=Q3.scope)


# ================================================================ F10 code review: positional/value admission, order
def test_f10_headline_value_edit_keeps_admission():
    """expected (R116: values never enter a signature): editing the unpinned headline figure keeps F1-Q and the 19 values."""
    ws, _, _ = built(t.in_table(S, 1, "1.63", "1.64"))
    assert numeric(ws) == ORIG, refusal_details(ws)


def test_f10_guidance_range_edit_keeps_admission():
    """expected (R116): editing an unpinned guidance range keeps F1-Q and the 19 values."""
    ws, _, _ = built(t.in_table(S, 13, "+6%", "+7%"))
    assert numeric(ws) == ORIG, refusal_details(ws)


def test_f10_check_order_unknown_before_repeated():
    """expected (R116 order 4 then 5): drivers repeated AND an unknown table later -> unknown_table:t17, not required_table_repeated."""
    body = t.repeat_table(S, T["drivers"])
    end = t.tables(body)[-1][1]
    body = body[:end] + t.INJECTED_TABLE + body[end:]
    ws, _, _ = built(body)
    _refused_everywhere(ws, r"envelope_refused:unknown_table:t17")


def test_f10_label_free_table_is_unknown():
    """expected: an injected table with no label cells is unknown_table:t7 (closed vocabulary), not a headline repeat."""
    ws, _, _ = built(t.after_table(S, T["drivers"], "<table><tr><td>5%</td></tr></table>"))
    _refused_everywhere(ws, r"envelope_refused:unknown_table:t7")


def test_f10_second_eps_row_with_another_marker_is_unlocated_not_a_crash():
    """expected (R130): a core reconciliation carrying two diluted-EPS rows ("... share (1)" beside "... share (2)")
    leaves Core EPS and year-ago Core EPS unlocated; never an exception; every other value kept; the validator agrees."""
    body = dup_row(S, T["core_reconciliation"], "Diluted net earnings per common share (2)",
                   rewrite=lambda r: r.replace("share (2)", "share (1)"))
    ws, texts, _ = built(body)
    assert numeric(ws) == {**ORIG, t.CORE: t.UNLOCATED, t.PCORE: t.UNLOCATED}, (numeric(ws), refusal_details(ws))
    assert validates(ws, texts)


def test_f10_duplicated_eps_row_is_unlocated_not_a_crash():
    """expected (R130, R117): two rows with the pinned EPS label leave Core EPS and year-ago Core EPS unlocated; never an
    exception; every other value kept."""
    ws, texts, _ = built(dup_row(S, T["core_reconciliation"], "Diluted net earnings per common share (2)"))
    assert numeric(ws) == {**ORIG, t.CORE: t.UNLOCATED, t.PCORE: t.UNLOCATED}, numeric(ws)
    assert validates(ws, texts)


def test_f10_control_role_order_is_not_positional():
    """control: moving the organic reconciliation table before the highlights keeps F1-Q and every value."""
    a, b = t.tables(S)[T["organic_reconciliation"]]
    h = t.tables(S)[T["highlights"]][0]
    body = S[:h] + S[a:b] + S[h:a] + S[b:]
    ws, texts, _ = built(body)
    assert numeric(ws) == ORIG
    assert validates(ws, texts)


# ================================================================ R126 check order and multiplicity
def test_r126_unread_table_removed_stays_admitted():
    """expected (R126): the balance sheet (t8) binds nothing; without it the document stays admitted with every value."""
    ws, texts, _ = built(t.drop_table(S, 8))
    assert numeric(ws) == ORIG, refusal_details(ws)
    assert validates(ws, texts)


def test_r126_unread_table_repeated_stays_admitted():
    """expected (R126): a repeated unread table is known and binds nothing; check 5 counts required roles only."""
    ws, texts, _ = built(t.repeat_table(S, 8))
    assert numeric(ws) == ORIG, refusal_details(ws)
    assert validates(ws, texts)


def test_r126_unknown_table_outranks_a_missing_required_table():
    """expected (R116 order, R126): drivers removed and an unknown table appended -> unknown_table:t15."""
    body = t.drop_table(S, T["drivers"])
    end = t.tables(body)[-1][1]
    ws, _, _ = built(body[:end] + t.INJECTED_TABLE + body[end:])
    _refused_everywhere(ws, r"envelope_refused:unknown_table:t15")


# ================================================================ R123 the receipt is the printed literal
@pytest.mark.parametrize("key", ["FY26Q1", "FY26Q2", "FY26Q3"])
def test_r123_receipt_span_is_the_printed_literal(key):
    """expected (R123): each present fact's receipt spans exactly the printed literal inside its primary cell, so the
    replayed bytes carry no markup and read as the cell's printed text; the display excerpt carries no markup."""
    rel = t.RELEASES[key]
    ws, _, bound = t.case(key)
    primary = {m: a for m, (a, _) in t.pins(rel).items()}
    raw = bound.source.encode("utf-8")
    rows = {m: r for m, r in t.by_metric(ws).items() if "value" in r}
    assert rows, key
    for m, row in rows.items():
        receipt = row["source_span"]["receipt"]
        span = raw[receipt["span_start_byte"]:receipt["span_end_byte"]].decode("utf-8")
        assert "<" not in span and ">" not in span, (m, span)
        assert html.unescape(span).strip() == t.one(bound.source, primary[m]).text, (m, span)
        assert "<" not in str(row["source_span"].get("display_excerpt", "")), (m, row["source_span"].get("display_excerpt"))
