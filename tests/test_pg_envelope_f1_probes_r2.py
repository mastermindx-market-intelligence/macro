"""CDV-1 T1 F1-Q envelope — frozen R2 witness (seat-frozen after the independent Opus re-audit R2 of 5add1e2eefc).

Every case edits one of the frozen gzipped originals in memory and asserts the outcome that the bytes and the seat
rulings R116-R121, R122-R131 and R132-R142 require.  The constructions are the auditor's; the seat reviewed each
expected outcome against the rulings and froze them unchanged, except the B11 case, which pins the ratified stricter
S0 check (R139) instead of a differential against a side-loaded base module.  The two R141 cases at the end are
seat-authored.

Rulings: research/consumer_defensive/cdv1_program/reviews/SEAT_RULING_T1_ENVELOPE_R2_2026-09-25.md.
Audit record: research/consumer_defensive/cdv1_program/reviews/OPUS_T1_ENVELOPE_AUDIT_R2_2026-09-25.md.
"""
from __future__ import annotations

import copy
import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_pg_envelope_f1 as t  # noqa: E402
import test_pg_envelope_f1_probes_r1 as r1  # noqa: E402
from engine.company_intelligence.economic_observations import EconomicObservationError, validate_selected_facts  # noqa

Q1, Q2, Q3 = t.FY26Q1, t.FY26Q2, t.FY26Q3
REL = {"Q1": Q1, "Q2": Q2, "Q3": Q3}
TAB = {"Q1": t.F1Q_TABLES["FY26Q1"], "Q2": t.F1Q_TABLES["FY26Q2"], "Q3": t.F1Q_TABLES["FY26Q3"]}
CUR = {"Q1": "July - September 2025", "Q2": "October - December 2025", "Q3": "January - March 2026"}
TITLE = {"Q1": "Three Months Ended September 30, 2025", "Q2": "Three Months Ended December 31, 2025",
         "Q3": "Three Months Ended March 31, 2026"}
EARN = {"Q1": "Three Months Ended September 30", "Q2": "Three Months Ended December 31", "Q3": "Three Months Ended March 31"}
TOTALS = [t.SALES, t.TV, t.OV, t.PRICE, t.MIX, t.FX, t.OTHER]
ORGREC = [t.ORG, *t.SEGMENTS]
EARNINGS = [t.DIL, t.PDIL, t.REPG]


def src(q):
    return t.original(REL[q])


def build(body, q="Q3"):
    return t.workspace(REL[q], body, REL[q])


def numeric(body, q="Q3"):
    ws, texts, _ = build(body, q)
    return r1.numeric(ws), ws, texts


def add_row_end(s, o, row):
    t0, t1 = t.tables(s)[o]
    seg = s[t0:t1]
    i = seg.lower().rfind("</table")
    return s[:t0] + seg[:i] + row + seg[i:] + s[t1:]


def not_bound(got, metrics):
    return {m: got[m] for m in metrics if isinstance(got[m], float)}


# ============================ SP / R124: a statement titled for another period never binds as the quarter
RANGE = {  # name -> (quarter, role, new title, metrics whose PRIMARY sits in that table)
    "Q3_segdrv_ytd_jul_mar": ("Q3", "segment_drivers", "July - March 2026", TOTALS),
    "Q3_segdrv_six_oct_mar": ("Q3", "segment_drivers", "October - March 2026", TOTALS),
    "Q3_segdrv_bogus_start": ("Q3", "segment_drivers", "Foo - March 2026", TOTALS),
    "Q3_orgrec_ytd_jul_mar": ("Q3", "organic_reconciliation", "July - March 2026", ORGREC),
    "Q2_segdrv_ytd_jul_dec": ("Q2", "segment_drivers", "July - December 2025", TOTALS),
    "Q2_orgrec_ytd_jul_dec": ("Q2", "organic_reconciliation", "July - December 2025", ORGREC),
    "Q1_segdrv_six_apr_sep": ("Q1", "segment_drivers", "April - September 2025", TOTALS),
}


@pytest.mark.parametrize("name", sorted(RANGE))
def test_sp_range_title_must_span_the_quarter(name):
    """expected: a pinned primary under a year-to-date / non-quarter range title is envelope_unlocated (R124, bar b)."""
    q, role, new, metrics = RANGE[name]
    got, _, _ = numeric(t.in_table(src(q), TAB[q][role], CUR[q], new), q)
    assert not_bound(got, metrics) == {}


DAY = {  # the month/day form: the day must be the period end's (R124)
    "Q3_corerec_mar30": ("Q3", "core_reconciliation", TITLE["Q3"], "Three Months Ended March 30, 2026", [t.CORE]),
    "Q3_corerec_mar1": ("Q3", "core_reconciliation", TITLE["Q3"], "Three Months Ended March 1, 2026", [t.CORE]),
    "Q2_corerec_dec1": ("Q2", "core_reconciliation", TITLE["Q2"], "Three Months Ended December 1, 2025", [t.CORE]),
    "Q1_priorcore_sep1": ("Q1", "prior_core_reconciliation", "Three Months Ended September 30, 2024",
                          "Three Months Ended September 1, 2024", [t.PCORE]),
}


@pytest.mark.parametrize("name", sorted(DAY))
def test_r124_month_day_title_day_must_match(name):
    """expected: the statement is not located, so the metric is envelope_unlocated (R124, bar b)."""
    q, role, old, new, metrics = DAY[name]
    got, _, _ = numeric(t.in_table(src(q), TAB[q][role], old, new), q)
    assert not_bound(got, metrics) == {}


@pytest.mark.parametrize("q", ["Q2", "Q3"])
def test_r124_nine_month_title_over_cell_with_moved_quarter_title(q):
    """expected: the earnings statement titled 'Nine Months Ended ...' never binds the quarter's EPS (bar b); a
    three-month title moved to a bottom row cannot re-govern cells a nine-month title sits over."""
    body = t.in_table(src(q), TAB[q]["earnings"], EARN[q], EARN[q].replace("Three", "Nine"))
    body = add_row_end(body, TAB[q]["earnings"], f"<tr><td>{EARN[q]}</td></tr>")
    got, _, _ = numeric(body, q)
    assert not_bound(got, EARNINGS) == {}


def test_r124_control_title_moved_alone_binds():
    """control (R124 fallback): the only title moved to a bottom row still governs; values unchanged."""
    body = add_row_end(t.in_table(src("Q3"), TAB["Q3"]["earnings"], ">" + EARN["Q3"] + "<", "><"), TAB["Q3"]["earnings"],
                       f"<tr><td>{EARN['Q3']}</td></tr>")
    got, _, _ = numeric(body)
    assert {m: got[m] for m in EARNINGS} == {m: t.expected_values(Q3)[m] for m in EARNINGS}


@pytest.mark.parametrize("new,q,role,code", [
    ("Twelve Months Ended March 31", "Q3", "earnings", "envelope_refused:unknown_table:t4"),
    ("Nine Months Ended March 31", "Q3", "earnings", "envelope_refused:unknown_table:t4"),
    ("Twelve Months Ended September 30, 2024", "Q1", "prior_core_reconciliation", "envelope_refused:unknown_table:t11"),
])
def test_r125_duration_word_survives_folding(new, q, role, code):
    """expected: a twelve/nine-month title never folds onto a three-month one (R125), so the table is unknown."""
    old = EARN[q] if role == "earnings" else "Three Months Ended September 30, 2024"
    ws, _, _ = build(t.in_table(src(q), TAB[q][role], old, new), q)
    assert r1.refusal_details(ws) == {code}


@pytest.mark.parametrize("new", ["Three Months Ended Marhc 31", "Three Months Ended February 30", "Three Months Ended Foo 1"])
def test_r122_r130_unparseable_title_is_not_an_exception(new):
    """expected: an unknown month / impossible date is 'not a title': no exception, earnings pins unlocated."""
    got, _, _ = numeric(t.in_table(src("Q3"), TAB["Q3"]["earnings"], EARN["Q3"], new))
    assert not_bound(got, EARNINGS) == {}


@pytest.mark.parametrize("new", ["three months ended march 31", "Three  Months Ended March 31", "Three&#160;Months Ended March 31",
                                 "Three Months<br/>Ended March 31", "THREE MONTHS ENDED MARCH 31"])
def test_r124_title_spelling_variants_never_misbind(new):
    """control (coverage): a spelling variant of the earnings title binds the frozen values or nothing."""
    got, _, _ = numeric(t.in_table(src("Q3"), TAB["Q3"]["earnings"], EARN["Q3"], new))
    base = t.expected_values(Q3)
    assert all(got[m] in (base[m], t.UNLOCATED) for m in EARNINGS)


def test_r124_two_titles_over_one_cell_unlocated():
    """control: a second title row over the core reconciliation's current columns -> CORE unlocated."""
    body = t.in_table(src("Q3"), TAB["Q3"]["core_reconciliation"], TITLE["Q3"],
                      TITLE["Q3"] + "</font></td></tr><tr><td colspan=\"30\"><font>" + "Three Months Ended March 31, 2025")
    got, _, _ = numeric(body)
    assert not_bound(got, [t.CORE]) == {}


@pytest.mark.parametrize("q", ["Q1", "Q2", "Q3"])
def test_r124_range_title_in_untitled_table_refuses_or_unlocates(q):
    """control: a range title injected into the highlights table (prints none) never binds a wrong value."""
    body = add_row_end(src(q), TAB[q]["highlights"], f"<tr><td>{CUR[q].replace('2025', '2024').replace('2026', '2025')}</td></tr>")
    ws, _, _ = build(body, q)
    got = r1.numeric(ws)
    base = t.expected_values(REL[q])
    assert all(got[m] == base[m] or not isinstance(got[m], float) for m in got)


# ============================ R123: the validator refuses every tampered field, including span width
def _respan(ws, texts, metric, d_start, d_end):
    ws = copy.deepcopy(ws)
    row = t.by_metric(ws)[metric]
    source = next(iter(texts.values())).encode("utf-8")
    span = row["source_span"]
    s, e = span["receipt"]["span_start_byte"] + d_start, span["receipt"]["span_end_byte"] + d_end
    text = source[s:e]
    digest = hashlib.sha256(text).hexdigest()
    for holder in (span["locator"], span["receipt"]):
        holder["span_start_byte"], holder["span_end_byte"] = s, e
    span["text_sha256"] = span["receipt"]["text_sha256"] = digest
    span["display_excerpt"] = text.decode("utf-8")
    return ws


SPAN_TAMPER = {  # name -> (quarter, metric, start delta, end delta)
    "Q3_core_wider_over_nbsp_entity": ("Q3", t.CORE, 0, 6),
    "Q3_dil_wider_over_nbsp_entity": ("Q3", t.DIL, 0, 6),
    "Q3_dil_wider_one_byte_left_into_tag": ("Q3", t.DIL, -1, 0),
    "Q3_sales_narrower_drops_percent": ("Q3", t.SALES, 0, -1),
    "Q2_dil_wider_over_nbsp_entity": ("Q2", t.DIL, 0, 6),
    "Q1_dil_wider_over_nbsp_entity": ("Q1", t.DIL, 0, 6),
    "Q1_sales_narrower_drops_percent": ("Q1", t.SALES, 0, -1),
}


@pytest.mark.parametrize("name", sorted(SPAN_TAMPER))
def test_r123_span_one_step_wider_or_narrower_is_refused(name):
    """expected: EconomicObservationError; the receipt span is exactly the printed literal (R123, bar c)."""
    q, metric, ds, de = SPAN_TAMPER[name]
    ws, texts, _ = t.case(REL[q].key)
    bad = _respan(ws, texts, metric, ds, de)
    assert not r1.validates(bad, texts, REL[q])


def _absent_row(ws):
    return next(r for r in t.pg_rows(ws) if "typed_absence" in r)


@pytest.mark.parametrize("case_name", ["FY26Q3", "FY26Q2", "FY26Q1"])
def test_r123_absence_subject_suffix_is_refused(case_name):
    """expected: a typed absence whose subject is not exactly its metric is refused (every typed-absence key)."""
    ws, texts, _ = t.case(case_name)
    ws = copy.deepcopy(ws)
    row = _absent_row(ws)
    row["typed_absence"]["subject"] = row["metric"] + " (forged)"
    assert not r1.validates(ws, texts, t.RELEASES[case_name])


def test_r123_refused_document_subject_suffix_is_refused():
    """expected: refused-document rows are held to every typed-absence key too (bar c)."""
    ws, texts, _ = t.case("refused:type_ex_99_2")
    ws = copy.deepcopy(ws)
    row = _absent_row(ws)
    row["typed_absence"]["subject"] = row["metric"] + "_x"
    assert not r1.validates(ws, texts, Q3)


def test_r123_fact_without_metric_is_refused_as_s0_refuses():
    """expected: S0 refuses a facts entry that names no metric ('workspace facts must each name a metric'); R123 says the
    wrapped branch keeps every S0 structural check."""
    ws, texts, _ = t.case("FY26Q3")
    ws = copy.deepcopy(ws)
    ws["facts"].append({"schema": "event_fact.v1", "value": 9.99})
    assert not r1.validates(ws, texts, Q3)


@pytest.mark.parametrize("q", ["Q1", "Q2"])
def test_r123_q1_q2_value_forgery_refused(q):
    """control (Q1/Q2 sweep, family 9): a present value changed by 0.01 is refused."""
    ws, texts, _ = t.case(REL[q].key)
    ws = copy.deepcopy(ws)
    t.by_metric(ws)[t.DIL]["value"] += 0.01
    assert not r1.validates(ws, texts, REL[q])


# ============================ R123: the receipt span is exactly the printed literal, and never an exception
def test_r123_entity_before_dash_literal_span_is_the_literal():
    """expected: with '&#160;' before FY26 Q2's highlights '&#8212;%', Core EPS growth binds 0.0 with display_excerpt
    exactly '&#8212;%', and the validator accepts the extractor's own output (bar a)."""
    s = src("Q2")
    c = t.one(s, t.pins(Q2)[t.COREG][0])
    body = s[:c.start] + s[c.start:c.end].replace("&#8212;%", "&#160;&#8212;%") + s[c.end:]
    ws, texts, _ = build(body, "Q2")
    row = t.by_metric(ws)[t.COREG]
    assert row.get("value") == 0.0 and row["source_span"]["display_excerpt"] == "&#8212;%"
    assert r1.validates(ws, texts, Q2)


@pytest.mark.parametrize("new", ["1.6<b></b>3&#160;", "1&#46;63&#160;"])
def test_r123_interrupted_or_entity_literal_never_raises(new):
    """expected: no exception.  Markup inside the literal -> envelope_unlocated (R123); an entity digit may bind only
    with a span over exactly the printed characters."""
    s = src("Q3")
    c = t.one(s, t.pins(Q3)[t.DIL][0])
    body = s[:c.start] + s[c.start:c.end].replace("1.63&#160;", new) + s[c.end:]
    ws, texts, _ = build(body)
    row = t.by_metric(ws)[t.DIL]
    if "<b>" in new:
        assert "value" not in row
    assert r1.validates(ws, texts, Q3)


# ============================ R122 wrapper
@pytest.mark.parametrize("prefix", ["\x0c", "\x0b", "﻿\x0c"])
def test_r122_other_whitespace_before_document_is_wrapped(prefix):
    """expected: whitespace other than space/tab/CR/LF before <DOCUMENT> is still the wrapper; every row is an envelope
    outcome, never a legacy detail (bar d)."""
    ws, _, _ = build(prefix + src("Q3"))
    assert r1.all_envelope(ws)


def test_r122_indented_second_type_line_refused():
    """expected: a second <TYPE> line in the header, indented, is still a second TYPE line -> not_ex_99_1."""
    ws, _, _ = build(t.once(src("Q3"), "<TYPE>EX-99.1\n", "<TYPE>EX-99.1\n <TYPE>EX-99.2\n"))
    assert r1.refusal_details(ws) == {"envelope_refused:not_ex_99_1"}


def test_r122_type_line_after_text_is_body():
    """control: a <TYPE> line after <TEXT> is body text, not the header."""
    ws, _, _ = build(t.once(src("Q3"), "<TEXT>\n", "<TEXT>\n<TYPE>EX-99.2\n"))
    assert r1.numeric(ws) == t.expected_values(Q3)


# ============================ R116/R126/R129 check order
NESTED = "<table><tr><td>x</td></tr></table>"


def _nest(s, o):
    t0, t1 = t.tables(s)[o]
    seg = s[t0:t1]
    i = seg.lower().find("<td")
    return s[:t0] + seg[:i] + "<td>" + NESTED + "</td>" + seg[i:] + s[t1:]


def test_r116_order_generator_before_nested_table():
    """expected: generator removed + a nested table -> generator_not_workiva (check 2 precedes check 4)."""
    body = _nest(t.once(src("Q3"), "<!-- Document created using Wdesk -->\n", ""), TAB["Q3"]["organic_reconciliation"])
    ws, _, _ = build(body)
    assert r1.refusal_details(ws) == {"envelope_refused:generator_not_workiva"}


def test_r116_order_issuer_before_nested_table():
    """expected: another issuer's masthead + a nested table -> issuer_not_pg (check 3 precedes check 4)."""
    body = t.in_table(src("Q3"), 0, "The Procter &#38; Gamble Company", "The Clorox Company")
    ws, _, _ = build(_nest(body, TAB["Q3"]["organic_reconciliation"]))
    assert r1.refusal_details(ws) == {"envelope_refused:issuer_not_pg"}


def test_r116_first_unknown_in_document_order_with_later_nested():
    """expected: an injected unknown table at t7 and a nested table later -> unknown_table:t7 (first in document order)."""
    body = t.after_table(src("Q3"), TAB["Q3"]["drivers"], t.INJECTED_TABLE)
    body = _nest(body, TAB["Q3"]["organic_reconciliation"] + 1)
    ws, _, _ = build(body)
    assert r1.refusal_details(ws) == {"envelope_refused:unknown_table:t7"}


@pytest.mark.parametrize("q", ["Q2", "Q3"])
def test_r126_unread_table_removed_or_repeated_admitted(q):
    """control (R126): the balance sheet removed / repeated keeps every frozen value."""
    base = t.expected_values(REL[q])
    for body in (t.drop_table(src(q), 8), t.repeat_table(src(q), 8)):
        assert numeric(body, q)[0] == base


def test_r127_q2_with_q1_prior_core_table_keeps_value():
    """control (R127): FY26 Q2 with FY26 Q1's prior-core table appended keeps the footnote route."""
    s1 = src("Q1")
    t0, t1 = t.tables(s1)[TAB["Q1"]["prior_core_reconciliation"]]
    body = t.after_table(src("Q2"), TAB["Q2"]["organic_reconciliation"], s1[t0:t1])
    assert numeric(body, "Q2")[0] == t.expected_values(Q2)


def test_r126_q1_without_prior_core_table_refused():
    """control (R126): FY26 Q1 without its prior-core table -> required_table_missing:prior_core_reconciliation."""
    ws, _, _ = build(t.drop_table(src("Q1"), TAB["Q1"]["prior_core_reconciliation"]), "Q1")
    assert r1.refusal_details(ws) == {"envelope_refused:required_table_missing:prior_core_reconciliation"}


# ============================ R130 EPS row / R128 literal
def test_r130_two_eps_rows_never_bind_an_unlabelled_cell():
    """expected: two diluted-EPS rows (markers (2),(3)) leave CORE/PCORE unlocated even if an unlabelled row prints a
    number under Core(Non-GAAP) (the empty eps_row must not match label-less cells)."""
    s = src("Q3")
    o = TAB["Q3"]["core_reconciliation"]
    body = r1.dup_row(s, o, "Diluted net earnings per common share (2)",
                      lambda row: row.replace("Diluted net earnings per common share (2)", "Diluted net earnings per common share (3)"))
    body = r1.dup_row(body, o, "Currency-neutral Core EPS",
                      lambda row: row.replace("Currency-neutral Core EPS", ""))
    got, _, _ = numeric(body)
    assert not_bound(got, [t.CORE, t.PCORE]) == {}


def test_r128_percent_marked_eps_never_binds_usd():
    """expected (bar a, unit): an EPS primary printed '1.63%' is not a usd_per_share figure -> not bound."""
    s = src("Q3")
    c = t.one(s, t.pins(Q3)[t.DIL][0])
    body = s[:c.start] + s[c.start:c.end].replace("1.63&#160;", "1.63%") + s[c.end:]
    got, _, _ = numeric(body)
    assert not isinstance(got[t.DIL], float)


# ============================ Q1/Q2 sweep: families 1-3 and 8
@pytest.mark.parametrize("q", ["Q1", "Q2"])
def test_sweep_cross_table_swap_conflicts(q):
    """expected: swapping ORG's primary with SALES's primary conflicts both (family 1)."""
    p = t.pins(REL[q])
    body = r1.swap_cells(src(q), p[t.ORG][0], p[t.SALES][0])
    got = numeric(body, q)[0]
    va, vb = t.literal(t.one(src(q), p[t.ORG][0]).text), t.literal(t.one(src(q), p[t.SALES][0]).text)
    assert got[t.ORG] == got[t.SALES] == (t.CONFLICT if va != vb else va)


@pytest.mark.parametrize("q", ["Q1", "Q2"])
def test_sweep_duplicate_label_unlocates(q):
    """expected: a repeated 'Total P&G' row in segment drivers unlocates the totals (family 2)."""
    body = r1.dup_row(src(q), TAB[q]["segment_drivers"], "Total P&G")
    assert not_bound(numeric(body, q)[0], TOTALS) == {}


@pytest.mark.parametrize("q", ["Q1", "Q2"])
def test_sweep_earnings_year_headers_swapped_follow_witness(q):
    """expected: earnings year headers swapped -> DIL/PDIL conflict, as the frozen witness reads (family 3)."""
    y = int(REL[q].fiscal[2][:4])
    body = t.mutate(src(q), [(TAB[q]["earnings"], str(y), str(y - 1))])
    got = numeric(body, q)[0]
    assert (got[t.DIL], got[t.PDIL]) == (t.CONFLICT, t.CONFLICT)


def test_sweep_q2_note_removed_unlocates_prior_core():
    """expected: FY26 Q2 without its no-adjustment footnote -> PCORE unlocated (family 8)."""
    body = t.once(src("Q2"), "no adjustments to or reconciling items", "adjustments to and reconciling items")
    assert numeric(body, "Q2")[0][t.PCORE] == t.UNLOCATED


# ============================ R139: the ratified stricter S0 missing_fields check stays (B11)
def test_r139_s0_typed_absence_missing_fields_tamper_refused():
    """expected: an unwrapped (S0) workspace whose pg_ typed absence carries missing_fields=['basis'] is refused.
    No engine emitter produces a non-empty missing_fields, so the stricter check refuses only tampered workspaces (R139)."""
    from tests.earnings_economic_fixtures import FISCAL_SCOPE, pg_source_texts, pg_workspace_case
    found = None
    for kind in ("annual_first", "blank", "dash"):
        ws = pg_workspace_case(kind)
        rows = [r for r in ws["facts"] if isinstance(r, dict) and "typed_absence" in r and str(r.get("metric", "")).startswith("pg_")]
        if rows:
            found = (kind, ws)
            break
    assert found is not None, "no S0 workspace with a pg_ typed absence among annual_first/blank/dash"
    kind, ws = found
    validate_selected_facts(ws, source_texts=pg_source_texts(kind), fiscal_scope=FISCAL_SCOPE)
    ws = copy.deepcopy(ws)
    next(r for r in ws["facts"] if isinstance(r, dict) and "typed_absence" in r and str(r.get("metric", "")).startswith("pg_"))["typed_absence"]["missing_fields"] = ["basis"]
    with pytest.raises(EconomicObservationError):
        validate_selected_facts(ws, source_texts=pg_source_texts(kind), fiscal_scope=FISCAL_SCOPE)


# ============================ R141: core and prior-core reconciliations are told apart by anchors alone (seat-authored)
def test_r141_prior_core_with_core_eps_currency_rows_is_unknown():
    """expected (seat): FY26 Q1's prior-core table printing the core table's EPS currency rows matches neither role —
    the core anchor is the census token 'currency impact to core gross margin' and the prior-core vocabulary carries no
    currency row — so the document is refused unknown_table:t11 (R125, R141), never recognised as a second core table."""
    body = add_row_end(src("Q1"), TAB["Q1"]["prior_core_reconciliation"],
                       "<tr><td>Currency impact to earnings</td></tr><tr><td>Currency-neutral EPS</td></tr>")
    ws, _, _ = build(body, "Q1")
    assert r1.refusal_details(ws) == {"envelope_refused:unknown_table:t11"}


def test_r141_prior_core_with_core_margin_currency_row_is_refused():
    """expected (seat): FY26 Q1's prior-core table printing 'Currency impact to core gross margin' can no longer match
    the prior-core role (its vocabulary is the census of prior-core tables, which print no currency row), so the
    document is refused whatever the code (R141)."""
    body = add_row_end(src("Q1"), TAB["Q1"]["prior_core_reconciliation"],
                       "<tr><td>Currency impact to core gross margin</td></tr>")
    ws, _, _ = build(body, "Q1")
    details = r1.refusal_details(ws)
    assert details and all(isinstance(d, str) and d.startswith("envelope_refused:") for d in details), details
