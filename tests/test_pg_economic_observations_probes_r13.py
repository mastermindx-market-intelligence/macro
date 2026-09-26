"""Opus round-14 red-team probes for PR #7905 (rulings R81-R86), frozen by the seat as the thirteenth suite (R96). Original synthetic data only. The "last year" case of f11 struck by R94.
Each test asserts the CORRECT behaviour: failing w* = wrong bind; v* = the validator paired with a wrong bind
(skips if the wrong value is not bound; fails if the validator ACCEPTS it); f* = fail-closed refusal (a correct
value missed); x* = validator surface; c* = controls."""
from __future__ import annotations

import copy
from datetime import date

import pytest

import engine.company_intelligence.pg_profile as pgp
from engine.company_intelligence.economic_observations import EconomicObservationError, validate_selected_facts
from tests.test_pg_economic_observations_probes import Q1_FY2027, Q4_FY2026, Case
from tests.test_pg_economic_observations_probes_r4 import Q3_FY2026, TITLE, DRV, SUB, row, table, _forge_absent, HEAD, VALS
from tests.test_pg_economic_observations_probes_r5 import ws, TV, DIL, forge_present, at
from tests.test_pg_economic_observations_probes_r7 import PRIOR, CORE, DILL, YEARS, SEG_T, BEAUTY, _val
from tests.test_pg_economic_observations_probes_r10 import T1, T3, GUIDE_T

MIX = "pg_mix_contribution_pp"
Q2_FY2027 = Case(("2026-10-01", "2026-12-31", "2025-10-01", "2025-12-31"), 2027, 2, date(2026, 12, 31),
                 "2027-01-22", "2027-01-22T11:00:00Z", "2027-01-22T11:05:00Z", "0000080424-27-000104")
T2 = "<h1>Second Quarter Fiscal Year 2027 Results</h1>\n"
SUB2 = "<h3>Three Months Ended December 31, 2026</h3>\n"
SUB1 = "<h3>Three Months Ended September 30, 2026</h3>\n"
PF_T = "<table>\n" + YEARS + row([DILL, "$3.40", "$2.93"]) + "</table>\n"


def _refuses(w, t, c):
    try:
        validate_selected_facts(w, source_texts=t, fiscal_scope=c.scope)
    except EconomicObservationError:
        return True
    return False


def _v(body, metric, wrong, case=Q4_FY2026):
    w, t, r, c = ws(body, case=case, slug="r14")
    got = _val(r, metric)
    if got != wrong:
        pytest.skip(f"extractor did not bind the wrong value (got {got!r})")
    assert _refuses(w, t, c), f"VALIDATOR ACCEPTS wrong value {wrong!r} for {metric}"


# ===== W-A (R81): "versus" / "compared with" drivers pairs bypass _DRIVERS_YEARS (regex needs "vs.") =====
DRV_VERSUS_Q1 = T1 + "<h2>Net Sales Change Drivers 2027 versus 2025</h2>\n" + table()
DRV_COMPARED_Q1 = T1 + "<h2>Net Sales Change Drivers 2027 compared with 2025</h2>\n" + table()
DRV_VERSUS_Q2 = T2 + "<h2>Net Sales Change Drivers 2027 versus 2025</h2>\n" + table()


@pytest.mark.parametrize("body,case", [(DRV_VERSUS_Q1, Q1_FY2027), (DRV_COMPARED_Q1, Q1_FY2027), (DRV_VERSUS_Q2, Q2_FY2027)],
                         ids=["versus_q1", "compared_with_q1", "versus_q2"])
def test_w01_drivers_fiscal_year_versus_two_years_back(body, case):
    w, t, r, c = ws(body, case=case)
    assert "value" not in r[TV], ("'2027 versus 2025' drivers heading bound as the quarter", _val(r, TV))


@pytest.mark.parametrize("body,case", [(DRV_VERSUS_Q1, Q1_FY2027), (DRV_COMPARED_Q1, Q1_FY2027), (DRV_VERSUS_Q2, Q2_FY2027)],
                         ids=["versus_q1", "compared_with_q1", "versus_q2"])
def test_v01(body, case):
    _v(body, TV, 1.0, case=case)


@pytest.mark.parametrize("years", ["2027 versus 2026", "2027 vs. 2026", "2027 compared with 2026"])
def test_c01_drivers_q1_correct_pairs_bind(years):
    w, t, r, c = ws(T1 + f"<h2>Net Sales Change Drivers {years}</h2>\n" + table(), case=Q1_FY2027)
    assert _val(r, TV) == 1.0, (years, r[TV])


@pytest.mark.parametrize("years", ["2026 vs. 2025 vs. 2024", "2026 versus 2024", "(2026 vs. 2023)"])
def test_c01b_drivers_q4_other_pairs_refuse(years):
    w, t, r, c = ws(TITLE + f"<h2>Net Sales Change Drivers {years}</h2>\n" + table())
    assert "value" not in r[TV], (years, r[TV])


def test_f01_reversed_vs_pair_q4():
    w, t, r, c = ws(TITLE + "<h2>Net Sales Change Drivers 2025 vs. 2026</h2>\n" + table())
    assert _val(r, TV) == 1.0, r[TV]


# ===== W-B (R82): the units-note alternative of _DECORATION swallows ANY words up to ")" =====
UNITS_HEAD = TITLE + "<h3>Three Months Ended June 30, 2026 (in millions, except per share amounts; pro forma combined company)</h3>\n" + PF_T
UNITS_CAPTION = TITLE + SUB + "<table>\n<caption>(In millions, except per share amounts, pro forma combined company)</caption>\n" + YEARS + row([DILL, "$3.40", "$2.93"]) + "</table>\n"
UNITS_PARA = TITLE + SUB + "<p>(In millions, pro forma combined)</p>\n" + PF_T


@pytest.mark.parametrize("body", [UNITS_HEAD, UNITS_CAPTION, UNITS_PARA], ids=["heading", "caption", "label_paragraph"])
def test_w02_units_note_hides_basis(body):
    w, t, r, c = ws(body)
    assert _val(r, DIL) is None, ("basis words inside a units-note parenthetical are decoration", r[DIL])


@pytest.mark.parametrize("body", [UNITS_HEAD, UNITS_CAPTION, UNITS_PARA], ids=["heading", "caption", "label_paragraph"])
def test_v02(body):
    _v(body, DIL, 3.40)


def test_c02_plain_units_note_binds():
    w, t, r, c = ws(TITLE + SUB + "<table>\n<caption>(In millions, except per share amounts)</caption>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + "</table>\n")
    assert _val(r, DIL) == 3.07, r[DIL]


# ===== W-C (R83): only the LAST paragraph before a table is its label =====
TWO_LINE = TITLE + SUB + "<p>Pro Forma Combined</p>\n<p>(In millions, except per share amounts)</p>\n" + PF_T
TWO_LINE_B = TITLE + SUB + "<p>Pro Forma Combined</p>\n<p>(Unaudited)</p>\n" + PF_T


@pytest.mark.parametrize("body", [TWO_LINE, TWO_LINE_B], ids=["units_second", "unaudited_second"])
def test_w03_basis_label_then_units_line(body):
    w, t, r, c = ws(body)
    assert _val(r, DIL) is None, ("basis label one paragraph above the table is ignored", r[DIL])


@pytest.mark.parametrize("body", [TWO_LINE, TWO_LINE_B], ids=["units_second", "unaudited_second"])
def test_v03(body):
    _v(body, DIL, 3.40)


# ===== W-D (R83): a label of six or more words, or a long period+basis label, is "prose" =====
SIX_WORD = TITLE + SUB + "<p>Supplemental Unaudited Pro Forma Combined Company Information</p>\n" + PF_T
PERIOD_BASIS = TITLE + SUB + "<p>Pro Forma Combined Company Results for the Three Months Ended June 30, 2026</p>\n" + PF_T


@pytest.mark.parametrize("body", [SIX_WORD, PERIOD_BASIS], ids=["six_words", "period_plus_basis"])
def test_w04_long_basis_label(body):
    w, t, r, c = ws(body)
    assert _val(r, DIL) is None, ("a basis label longer than PG_TABLE_LABEL_WORDS binds its table", r[DIL])


@pytest.mark.parametrize("body", [SIX_WORD, PERIOD_BASIS], ids=["six_words", "period_plus_basis"])
def test_v04(body):
    _v(body, DIL, 3.40)


def test_c04_short_period_basis_label_refuses():
    w, t, r, c = ws(TITLE + SUB + "<p>Pro Forma Three Months Ended June 30, 2026</p>\n" + PF_T)
    assert _val(r, DIL) is None, r[DIL]


# ===== W-E (R83): the table-label vocabulary is the UNION of every route, so non-GAAP / core words pass =====
NONGAAP_CAPTION = TITLE + SUB + "<table>\n<caption>Non-GAAP Results</caption>\n" + YEARS + row([DILL, "$3.40", "$2.93"]) + "</table>\n"
CORE_LABEL = TITLE + SUB + "<p>Core Results</p>\n" + PF_T


@pytest.mark.parametrize("body", [NONGAAP_CAPTION, CORE_LABEL], ids=["nongaap_caption", "core_paragraph"])
def test_w05_non_gaap_table_label_binds_gaap_eps(body):
    w, t, r, c = ws(body)
    assert _val(r, DIL) is None, ("a non-GAAP/core-labelled table's diluted EPS bound as GAAP diluted EPS", r[DIL])


@pytest.mark.parametrize("body", [NONGAAP_CAPTION, CORE_LABEL], ids=["nongaap_caption", "core_paragraph"])
def test_v05(body):
    _v(body, DIL, 3.40)


# ===== W-F (R83): the OUTER table of a nested table loses the band text the inner table carried =====
def _inner(text):
    return "<td><table><tr><td>" + text + "</td></tr></table></td>"


OUTER = (TITLE + SUB + "<table>\n<tr><td></td>" + _inner("Three Months Ended March 31, 2026") + _inner("Three Months Ended March 31, 2025") + "</tr>\n"
         + YEARS + row([DILL, "$3.40", "$2.93"]) + "</table>\n")
OUTER_CAP = (TITLE + SUB + "<table>\n<tr><td>" + "<table><tr><td>Twelve Months Ended June 30, 2026</td></tr></table>" + "</td><td></td><td></td></tr>\n"
             + YEARS + row([DILL, "$12.00", "$11.00"]) + "</table>\n")


@pytest.mark.parametrize("body,wrong", [(OUTER, 3.40), (OUTER_CAP, 12.0)], ids=["foreign_band_in_inner", "annual_label_in_inner"])
def test_w06_outer_table_of_nested_table(body, wrong):
    w, t, r, c = ws(body)
    assert _val(r, DIL) is None, ("outer table whose band lived in a nested table bound", r[DIL])


@pytest.mark.parametrize("body,wrong", [(OUTER, 3.40), (OUTER_CAP, 12.0)], ids=["foreign_band_in_inner", "annual_label_in_inner"])
def test_v06(body, wrong):
    _v(body, DIL, wrong)


# ===== R81 Q2 identities and bare quarter numbers =====
def test_c07_q2_calendar_band():
    w, t, r, c = ws(T2 + SUB2 + "<table>\n" + row(["", "2026", "2025"]) + row([DILL, "$3.20", "$3.07"]) + "</table>\n", case=Q2_FY2027)
    assert (_val(r, DIL), _val(r, PRIOR)) == (3.20, 3.07), (r[DIL], r[PRIOR])


def test_c07b_q2_fiscal_band():
    w, t, r, c = ws(T2 + SUB2 + "<table>\n" + row(["", "2027", "2026"]) + row([DILL, "$3.20", "$3.07"]) + "</table>\n", case=Q2_FY2027)
    assert (_val(r, DIL), _val(r, PRIOR)) == (3.20, 3.07), (r[DIL], r[PRIOR])


def test_c07c_q2_date_band():
    w, t, r, c = ws(T2 + "<table>\n" + row(["", "December 31, 2026", "December 31, 2025"]) + row([DILL, "$3.20", "$3.07"]) + "</table>\n", case=Q2_FY2027)
    assert (_val(r, DIL), _val(r, PRIOR)) == (3.20, 3.07), (r[DIL], r[PRIOR])


@pytest.mark.parametrize("head", ["Second Quarter 2026 Results", "Six Months Ended December 31, 2026", "Q2 FY26 Results",
                                  "Three Months Ended December 31, 2025", "Q1 Highlights"])
def test_c07d_q2_foreign_headings_refuse(head):
    w, t, r, c = ws(T2 + f"<h2>{head}</h2>\n" + "<table>\n" + row(["", "2026", "2025"]) + row([DILL, "$3.20", "$3.07"]) + "</table>\n", case=Q2_FY2027)
    assert _val(r, DIL) is None, (head, r[DIL])


@pytest.mark.parametrize("head", ["Quarter 3 Highlights", "Q-3 Highlights", "Q 3 Highlights", "q3 highlights"])
def test_f08_bare_quarter_spellings_q3(head):
    w, t, r, c = ws(T3 + f"<h2>{head}</h2>\n<h3>Segment Results</h3>\n" + SEG_T, case=Q3_FY2026)
    assert _val(r, BEAUTY) == 4.0, (head, r[BEAUTY])


@pytest.mark.parametrize("head", ["Q3 Highlights", "Q4 Highlights", "Q3FY Highlights"])
def test_c08_bare_quarter_other_quarter_refuses_q4(head):
    w, t, r, c = ws(TITLE + f"<h2>{head}</h2>\n<h3>Segment Results</h3>\n" + SEG_T)
    assert (_val(r, BEAUTY) == 4.0) is (head == "Q4 Highlights"), (head, r[BEAUTY])


# ===== R81 pure-year band columns =====
@pytest.mark.parametrize("band", [["2027 (1)", "2026 (1)"], ["$ 2027", "$ 2026"]], ids=["footnote", "dollar"])
def test_c09_q1_fiscal_band_with_marks(band):
    w, t, r, c = ws(T1 + SUB1 + "<table>\n" + row(["", *band]) + row([DILL, "$3.20", "$3.07"]) + "</table>\n", case=Q1_FY2027)
    assert _val(r, PRIOR) != 3.20 and _val(r, DIL) != 3.07, (band, r[DIL], r[PRIOR])


def test_c09b_q1_star_marked_fiscal_band_never_crosses():
    w, t, r, c = ws(T1 + SUB1 + "<table>\n" + row(["", "2027", "2026"]) + row(["", "*", "*"]) + row([DILL, "$3.20", "$3.07"]) + "</table>\n", case=Q1_FY2027)
    assert _val(r, PRIOR) != 3.20 and _val(r, DIL) != 3.07, (r[DIL], r[PRIOR])


def test_c09c_q1_only_prior_pure_years():
    # Only prior years among the pure-year columns: never read the 2025 column as current.
    w, t, r, c = ws(T1 + SUB1 + "<table>\n" + row(["", "2025", "2024"]) + row([DILL, "$3.20", "$3.07"]) + "</table>\n", case=Q1_FY2027)
    assert _val(r, DIL) is None, r[DIL]


# ===== R84 matched-column stacks =====
def test_c10_prior_under_other_prior_quarter_refuses():
    body = (TITLE + SUB + "<table>\n" + row(["", "Three Months Ended June 30,", "Three Months Ended March 31,"])
            + YEARS + row([DILL, "$3.07", "$2.50"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert _val(r, PRIOR) != 2.50, r[PRIOR]


def test_c10b_single_column_scope_and_prior_stack():
    body = (TITLE + SUB + "<table>\n" + '<tr><td></td><td>Three Months Ended June 30, 2026 and 2025</td><td></td></tr>\n'
            + row(["", "2026", "2025"]) + row([DILL, "$3.07", "$2.93"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert _val(r, PRIOR) != 3.07 and _val(r, DIL) != 2.93, (r[DIL], r[PRIOR])


# ===== R84 volume sentences (refusal surface) =====
# f11's "last year" case STRUCK by seat ruling R94: without a comparison preposition "last year" may still be the
# comparison base ("... on top of 3% growth last year"), so a sentence naming it stays a same-period statement and
# refuses (fail closed); the fiscal-year phrases name a year-level period and bind.
@pytest.mark.parametrize("sentence", ["Total P&amp;G volume increased 4% this fiscal year.", "Total P&amp;G volume increased 4% for the fiscal year."],
                         ids=["this_fiscal_year", "for_the_fiscal_year"])
def test_f11_year_level_volume_sentence_is_not_the_quarter(sentence):
    w, t, r, c = ws(TITLE + DRV + SUB + table() + f"<p>{sentence}</p>\n")
    assert _val(r, TV) == 1.0, (sentence, r[TV])


@pytest.mark.parametrize("sentence", ["Total P&amp;G volume decreased 2% in Q4.", "Total P&amp;G volume decreased 2% in the fourth quarter."])
def test_g11_same_quarter_conflicting_sentence(sentence):
    w, t, r, c = ws(TITLE + DRV + SUB + table() + f"<p>{sentence}</p>\n")
    assert "value" not in r[TV], (sentence, r[TV])


# ===== x: validator surface =====
HONEST = [
    TITLE + SUB + "<table>\n" + YEARS + row([DILL, "<span>$3.07</span>", "$2.93"]) + "</table>\n",
    TITLE + SUB + "<table>\n" + YEARS + row([DILL, "$&nbsp;3.07", "$2.93"]) + "</table>\n",
    TITLE + SUB + "<table>\n" + YEARS + row([DILL, "$3.07&#160;", "$2.93"]) + "</table>\n",
    TITLE + SUB + "<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + row([DILL, "$3.08", "$2.94"]) + "</table>\n",
    TITLE + DRV + SUB + table() + "<p>Total P&amp;G volume decreased 2% in the quarter.</p>\n",
    TITLE + DRV + SUB + table(vals=["1.0", "1.0%", "(1.0)%", "0.5%", "0.5%", "1.0%", "3.0%", "1.0%"]),
    "<h1>Third Quarter Fiscal Year 2026 Results</h1>\n" + SUB + "<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + "</table>\n",
    OUTER, TWO_LINE, SIX_WORD, NONGAAP_CAPTION, UNITS_CAPTION,
    TITLE + "<h2>Core EPS Reconciliation</h2>\n<p>Core EPS excludes a synthetic <!-- c --> restructuring item of 0.10.</p>\n",
    TITLE + DRV + SUB + "<table>\n" + row(["", "Volume/Mix", *HEAD[2:]]) + row(["Total P&amp;G", "1.5%", *VALS[2:]]) + "</table>\n",
]


@pytest.mark.parametrize("body", HONEST, ids=["span_cell", "nbsp_split", "nbsp_charref", "duplicate_row", "conflict_sentence",
                                              "unit_mismatch", "out_of_scope", "outer_nested", "two_line", "six_word", "nongaap",
                                              "units_caption", "comment_paragraph", "combined_only"])
def test_x12_extractor_own_workspace_validates(body):
    w, t, r, c = ws(body)
    try:
        validate_selected_facts(w, source_texts=t, fiscal_scope=c.scope)
    except EconomicObservationError as exc:
        pytest.fail(f"validator REFUSES the extractor's own workspace: {exc}")


def test_x12b_q2_honest_workspace_validates():
    w, t, r, c = ws(T2 + SUB2 + "<table>\n" + row(["", "2027", "2026"]) + row([DILL, "$3.20", "$3.07"]) + "</table>\n", case=Q2_FY2027)
    validate_selected_facts(w, source_texts=t, fiscal_scope=c.scope)


FORGE_CASES = [
    (T1 + SUB1 + "<table>\n" + row(["", "2027", "2026"]) + row([DILL, "$3.20", "$3.07"]) + "</table>\n", PRIOR, Q1_FY2027),
    (T2 + SUB2 + "<table>\n" + row(["", "2026", "2025"]) + row([DILL, "$3.20", "$3.07"]) + "</table>\n", DIL, Q2_FY2027),
    (T3 + "<h2>Q3 Highlights</h2>\n<h3>Segment Results</h3>\n" + SEG_T, BEAUTY, Q3_FY2026),
    (TITLE + SUB + "<table>\n<caption>(In millions, except per share amounts)</caption>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + "</table>\n", DIL, Q4_FY2026),
    (TITLE + SUB + "<table>\n" + YEARS + row(["Three Months Ended June 30, 2026", "—", "—"]) + row([DILL, "$3.07", "$2.93"]) + "</table>\n", DIL, Q4_FY2026),
    (T1 + "<h2>Net Sales Change Drivers 2027 vs. 2026</h2>\n" + table(), TV, Q1_FY2027),
    (TITLE + SUB + "<table>\n" + YEARS + row([DILL, "<span>$3.07</span>", "$2.93"]) + "</table>\n", DIL, Q4_FY2026),
]


@pytest.mark.parametrize("body,metric,case", FORGE_CASES, ids=["q1_fiscal_prior", "q2_dil", "q_bare", "units_caption", "dash_label", "q1_drivers", "span"])
def test_x13_forged_plain_absence(body, metric, case):
    w, t, r, c = ws(body, case=case)
    assert "value" in r[metric], (metric, r[metric])
    _forge_absent(w, metric, metric)
    assert _refuses(w, t, c), f"validator ACCEPTS a forged plain absence over {metric}"


@pytest.mark.parametrize("metric", ["pg_total_volume_growth_pct", MIX])
def test_x14_forged_combined_absence_without_combined_column(metric):
    w, t, r, c = ws(TITLE + DRV + SUB + table())
    assert "value" in r[metric]
    _forge_absent(w, metric, f"{metric} combined volume/mix")
    assert _refuses(w, t, c)


def test_x15_forged_present_under_basis_label():
    body = TITLE + SUB + "<p>Pro Forma Combined</p>\n" + PF_T
    w, t, r, c = ws(body)
    assert _val(r, DIL) is None
    src = next(iter(t.values()))
    s, e = at(src, "$3.40")
    w2, t2 = forge_present(w, src, DIL, s, e, 3.40, "2026-06-30")
    assert _refuses(w2, t2, c), "validator ACCEPTS a forged present value the R83 label refused"


def test_x16_forged_prior_value_as_current():
    w, t, r, c = ws(T1 + SUB1 + "<table>\n" + row(["", "2027", "2026"]) + row([DILL, "$3.20", "$3.07"]) + "</table>\n", case=Q1_FY2027)
    src = next(iter(t.values()))
    s, e = at(src, "$3.07")
    w2, t2 = forge_present(w, src, DIL, s, e, 3.07, "2026-09-30")
    assert _refuses(w2, t2, c)


@pytest.mark.parametrize("mutation", ["value_str", "period_none", "span_missing", "subject_int", "absence_not_dict"])
def test_x17_malformed_rows_raise_only_economic_error(mutation):
    w, t, r, c = ws(TITLE + SUB + "<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + "</table>\n")
    w = copy.deepcopy(w)
    f = next(x for x in w["facts"] if isinstance(x, dict) and x.get("metric") == DIL)
    g = next(x for x in w["facts"] if isinstance(x, dict) and x.get("metric") == CORE)
    if mutation == "value_str":
        f["value"] = "3.07"
    elif mutation == "period_none":
        f["period"] = None
    elif mutation == "span_missing":
        f.pop("source_span")
    elif mutation == "subject_int":
        g["typed_absence"]["subject"] = 7
    else:
        g["typed_absence"] = "absent"
    try:
        validate_selected_facts(w, source_texts=t, fiscal_scope=c.scope)
    except EconomicObservationError:
        return
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"validator raised {type(exc).__name__}: {exc}")
    pytest.fail("validator accepted a malformed row")


# ===== R82 hierarchy controls =====
@pytest.mark.parametrize("head", ["<h1>Synthetic Co.</h1>\n<h1>Fiscal Year 2027 Outlook</h1>\n<h2>Segment Results</h2>\n",
                                  "<h2>Segment Results Outlook</h2>\n"],
                         ids=["second_h1_forward_governs", "h2_first_forward"])
def test_c18_forward_hierarchy(head):
    w, t, r, c = ws(head + GUIDE_T)
    assert _val(r, BEAUTY) is None, (head, r[BEAUTY])


def test_c18b_fiscal_year_highlights_over_annual_segment_table():
    w, t, r, c = ws(TITLE + "<h2>Fiscal Year 2026 Highlights</h2>\n<h3>Segment Results</h3>\n" + SEG_T)
    assert _val(r, BEAUTY) is None, r[BEAUTY]


def test_c18c_fiscal_year_highlights_then_scope_segment_heading():
    w, t, r, c = ws(TITLE + "<h2>Fiscal Year 2026 Highlights</h2>\n<h3>Three Months Ended June 30, 2026 Segment Results</h3>\n" + SEG_T)
    assert _val(r, BEAUTY) == 4.0, r[BEAUTY]


@pytest.mark.parametrize("head", ["Net Sales Change Drivers 2026 vs. 2025 - Q4 FY25", "Net Sales Change Drivers 2026 vs. 2025 - June 30, 2025",
                                  "Net Sales Change Drivers 2026 vs. 2025 - 4Q FY25", "Net Sales Change Drivers 2026 vs. 2025 - FY25 Q4"])
def test_c19_prior_quarter_beside_year_level_drivers_refuses(head):
    w, t, r, c = ws(TITLE + f"<h2>{head}</h2>\n" + table())
    assert "value" not in r[TV], (head, r[TV])


@pytest.mark.parametrize("cells", [["Twelve Months Ended June 30, 2026", "$", "$"], ["Twelve Months Ended June 30, 2026", "—", ""],
                                   ], ids=["dollar_marks", "dash_blank"])
def test_c20_section_label_rows_open_annual(cells):
    body = TITLE + SUB + "<table>\n" + YEARS + row(cells) + row([DILL, "$12.00", "$11.00"]) + "</table>\n"
    w, t, r, c = ws(body)
    assert _val(r, DIL) is None, (cells, r[DIL])


# ===== W-G (R84): a footnote mark in a label row's value column makes it a DATA row; the twelve-month label is lost =====
MARK_SECTION = TITLE + SUB + "<table>\n" + YEARS + row(["Twelve Months Ended June 30, 2026", "(1)", "\u2014"]) + row([DILL, "$12.00", "$11.00"]) + "</table>\n"


def test_w07_twelve_month_label_row_with_footnote_mark():
    w, t, r, c = ws(MARK_SECTION)
    assert _val(r, DIL) is None, ("row under 'Twelve Months Ended June 30, 2026 | (1) | -' bound as Q4", r[DIL])


def test_v07():
    _v(MARK_SECTION, DIL, 12.0)


# ===== W-H (R77/R82): a level-1 masthead that is an OUTLOOK for the admitted quarter is exempt =====
OUTLOOK_MAST = ["<h1>Q4 Outlook</h1>\n<h2>Segment Organic Sales Growth</h2>\n" + GUIDE_T,
                "<h1>Fourth Quarter Fiscal Year 2026 Outlook</h1>\n<h2>Segment Organic Sales Growth</h2>\n" + GUIDE_T]


@pytest.mark.parametrize("body", OUTLOOK_MAST, ids=["q_bare", "ordinal_fy"])
def test_w08_outlook_masthead_for_admitted_quarter(body):
    w, t, r, c = ws(body)
    assert _val(r, BEAUTY) is None, ("goal table under an outlook masthead bound", r[BEAUTY])


@pytest.mark.parametrize("body", OUTLOOK_MAST, ids=["q_bare", "ordinal_fy"])
def test_v08(body):
    _v(body, BEAUTY, 5.0)
