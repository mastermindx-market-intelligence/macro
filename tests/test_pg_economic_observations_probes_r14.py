"""Opus round-15 red-team probes for PR #7905 at 4e9706aa070d (rulings R87-R96), frozen by the seat as the fourteenth suite (R104). Original synthetic data only. No case struck.
w* = wrong bind (fails when the wrong value binds); v* = validator paired with the wrong bind (skip when not bound,
fail when the validator ACCEPTS); f* = fail-closed refusal; x* = validator surface; c* = controls."""
from __future__ import annotations

from datetime import date

import pytest

from engine.company_intelligence.economic_observations import EconomicObservationError, validate_selected_facts
from tests.test_pg_economic_observations_probes import Q1_FY2027, Q4_FY2026, Case
from tests.test_pg_economic_observations_probes_r4 import Q3_FY2026, TITLE, DRV, SUB, row, table, _forge_absent, HEAD, VALS
from tests.test_pg_economic_observations_probes_r5 import ws, TV, DIL, forge_present, at
from tests.test_pg_economic_observations_probes_r7 import PRIOR, CORE, DILL, YEARS, SEG_T, BEAUTY, _val
from tests.test_pg_economic_observations_probes_r10 import T1, T3, GUIDE_T

Q2_FY2027 = Case(("2026-10-01", "2026-12-31", "2025-10-01", "2025-12-31"), 2027, 2, date(2026, 12, 31),
                 "2027-01-22", "2027-01-22T11:00:00Z", "2027-01-22T11:05:00Z", "0000080424-27-000104")
T2 = "<h1>Second Quarter Fiscal Year 2027 Results</h1>\n"
SUB1 = "<h3>Three Months Ended September 30, 2026</h3>\n"
SUB2 = "<h3>Three Months Ended December 31, 2026</h3>\n"
PF_T = "<table>\n" + YEARS + row([DILL, "$3.40", "$2.93"]) + "</table>\n"
SEGH = "<h2>Segment Organic Sales Growth</h2>\n"


def _refuses(w, t, c):
    try:
        validate_selected_facts(w, source_texts=t, fiscal_scope=c.scope)
    except EconomicObservationError:
        return True
    return False


def _v(body, metric, wrong, case=Q4_FY2026):
    w, t, r, c = ws(body, case=case, slug="r15")
    got = _val(r, metric)
    if got != wrong:
        pytest.skip(f"extractor did not bind the wrong value (got {got!r})")
    assert _refuses(w, t, c), f"VALIDATOR ACCEPTS wrong value {wrong!r} for {metric}"


# ===== A (R87): a drivers heading whose pair is not directly after "net sales change drivers" misses the pair form
# and falls to the bare-year calendar reading: in Q1/Q2 the pair {2026, 2025} = {FY-1, FY-2} is admitted =====
DRV_MISS = [
    (T1 + "<h2>Net Sales Change Drivers for 2026 vs. 2025</h2>\n" + table(), Q1_FY2027),
    (T1 + "<h2>Net Sales Change Drivers: 2026 vs. 2025</h2>\n" + table(), Q1_FY2027),
    (T1 + "<h2>Net Sales Change Drivers, 2026 versus 2025</h2>\n" + table(), Q1_FY2027),
    (T1 + "<h2>Net Sales Change Drivers — 2026 vs. 2025</h2>\n" + table(), Q1_FY2027),
    (T2 + "<h2>Net Sales Change Drivers for 2026 vs. 2025</h2>\n" + table(), Q2_FY2027),
    (T1 + "<h2>Net Sales Change Drivers 2026/2025</h2>\n" + table(), Q1_FY2027),
]
DRV_IDS = ["for_q1", "colon_q1", "comma_versus_q1", "emdash_q1", "for_q2", "slash_q1"]


@pytest.mark.parametrize("body,case", DRV_MISS, ids=DRV_IDS)
def test_w01_drivers_pair_behind_a_separator(body, case):
    w, t, r, c = ws(body, case=case, slug="r15")
    assert "value" not in r[TV], ("{2026, 2025} drivers pair bound in FY2027", _val(r, TV))


@pytest.mark.parametrize("body,case", DRV_MISS, ids=DRV_IDS)
def test_v01(body, case):
    _v(body, TV, 1.0, case=case)


def test_c01_pair_form_2026_vs_2025_refuses_in_q1():
    w, t, r, c = ws(T1 + "<h2>Net Sales Change Drivers 2026 vs. 2025</h2>\n" + table(), case=Q1_FY2027, slug="r15")
    assert "value" not in r[TV], r[TV]


def test_w01b_three_year_drivers_q1():
    # "2027 vs. 2026" is taken by the pair form; the trailing 2025 is then read "prior" because 2027 left the residual.
    w, t, r, c = ws(T1 + "<h2>Net Sales Change Drivers 2027 vs. 2026 vs. 2025</h2>\n" + table(), case=Q1_FY2027, slug="r15")
    assert "value" not in r[TV], r[TV]


# ===== B (R93): the title clause split lets an OUTLOOK title head the quarter =====
OUTLOOK_TITLES = [
    "Fourth Quarter and Fiscal Year 2026 Outlook",
    "Fourth Quarter Fiscal Year 2026 — Outlook",
    "Fourth Quarter Fiscal Year 2026 &amp; Guidance",
    "Q4 Outlook: Fourth Quarter Fiscal Year 2026",
    "Fourth Quarter Fiscal Year 2026 | Outlook",
    "Q4 and Fiscal Year 2026 Guidance",
]


@pytest.mark.parametrize("title", OUTLOOK_TITLES)
def test_w02_outlook_title_split_into_a_scope_clause(title):
    w, t, r, c = ws(f"<h1>{title}</h1>\n" + SEGH + GUIDE_T, slug="r15")
    assert _val(r, BEAUTY) is None, (title, r[BEAUTY])


@pytest.mark.parametrize("title", OUTLOOK_TITLES)
def test_v02(title):
    _v(f"<h1>{title}</h1>\n" + SEGH + GUIDE_T, BEAUTY, 5.0)


def test_c02_results_and_outlook_title_binds_actuals():
    w, t, r, c = ws("<h1>Fourth Quarter Fiscal Year 2026 Results and Fiscal Year 2027 Outlook</h1>\n" + SEGH + GUIDE_T, slug="r15")
    assert _val(r, BEAUTY) == 5.0, r[BEAUTY]


# ===== C (R89): prose naming a presentation basis the negative list misses =====
PROSE = [
    "Proforma combined results are presented below.",
    "The following table presents non-GAAP results.",
    "Combined results are presented below.",
    "The results below give effect to the merger as though it closed at the start of the period.",
    "Amounts below exclude restructuring charges.",
    "The following results are shown on a core basis.",
]
PROSE_IDS = ["proforma_one_word", "non_gaap", "combined", "as_though", "exclude", "core_basis"]


@pytest.mark.parametrize("sentence", PROSE, ids=PROSE_IDS)
def test_w03_prose_basis_outside_negative_list(sentence):
    w, t, r, c = ws(TITLE + SUB + f"<p>{sentence}</p>\n" + PF_T, slug="r15")
    assert _val(r, DIL) is None, (sentence, r[DIL])


@pytest.mark.parametrize("sentence", PROSE, ids=PROSE_IDS)
def test_v03(sentence):
    _v(TITLE + SUB + f"<p>{sentence}</p>\n" + PF_T, DIL, 3.40)


# ===== D (R89): a basis named AFTER the table, inside it, or in markup the parser does not block =====
AROUND = [
    TITLE + SUB + PF_T + "<p>The table above presents pro forma combined company results.</p>\n",
    TITLE + SUB + "<table>\n" + '<tr><td colspan="3">Pro Forma Combined Company</td></tr>\n' + YEARS + row([DILL, "$3.40", "$2.93"]) + "</table>\n",
    TITLE + SUB + "<table>\n" + row(["", "2026 Pro Forma", "2025 Pro Forma"]) + row([DILL, "$3.40", "$2.93"]) + "</table>\n",
    TITLE + SUB + "<table>\n" + YEARS + row(["Pro Forma " + DILL, "$3.40", "$2.93"]) + "</table>\n",
    TITLE + SUB + "<center>Pro Forma Combined</center>\n" + PF_T,
    TITLE + SUB + "<figure><figcaption>Pro Forma Combined</figcaption>\n" + PF_T + "</figure>\n",
    TITLE + SUB + "<span>Pro Forma Combined</span>\n" + PF_T,
    TITLE + "<p>Pro Forma Combined</p>\n" + SUB + PF_T,
]
AROUND_IDS = ["note_after", "title_row", "band_basis", "row_prefix", "center", "figcaption", "bare_span", "label_above_heading"]


@pytest.mark.parametrize("body", AROUND, ids=AROUND_IDS)
def test_w04_basis_outside_the_label_run(body):
    w, t, r, c = ws(body, slug="r15")
    assert _val(r, DIL) is None, r[DIL]


@pytest.mark.parametrize("body", AROUND, ids=AROUND_IDS)
def test_v04(body):
    _v(body, DIL, 3.40)


# ===== E (R94): "Quarter N" beside a cumulative or year word =====
QN = ["Quarter 3 Year-to-Date Highlights", "Quarter 3 YTD Highlights", "Quarter 3 Highlights 2025", "Quarter 3 Nine Months Highlights",
      "Quarter 3 Fiscal Year Highlights"]


@pytest.mark.parametrize("head", QN)
def test_w05_quarter_n_beside_other_period(head):
    w, t, r, c = ws(T3 + f"<h2>{head}</h2>\n<h3>Segment Results</h3>\n" + SEG_T, case=Q3_FY2026, slug="r15")
    assert _val(r, BEAUTY) is None, (head, r[BEAUTY])


@pytest.mark.parametrize("head", QN)
def test_v05(head):
    _v(T3 + f"<h2>{head}</h2>\n<h3>Segment Results</h3>\n" + SEG_T, BEAUTY, 4.0, case=Q3_FY2026)


# ===== F (R92): footnote-mark label rows =====
def test_w06_mark_row_names_prior_quarter():
    body = TITLE + SUB + "<table>\n" + YEARS + row(["Three Months Ended March 31, 2026", "(a)", "(b)"]) + row([DILL, "$2.50", "$2.40"]) + "</table>\n"
    w, t, r, c = ws(body, slug="r15")
    assert _val(r, DIL) != 2.50, r[DIL]


def test_w06b_units_note_row_under_annual_label():
    body = TITLE + SUB + "<table>\n" + YEARS + row(["Twelve Months Ended June 30, 2026", "(in millions)", "(%)"]) + row([DILL, "$12.00", "$11.00"]) + "</table>\n"
    w, t, r, c = ws(body, slug="r15")
    assert _val(r, DIL) is None, r[DIL]


def test_c06_mark_row_scope_binds():
    body = TITLE + "<table>\n" + YEARS + row(["Three Months Ended June 30, 2026", "(1)", "(1)"]) + row([DILL, "$3.07", "$2.93"]) + "</table>\n"
    w, t, r, c = ws(body, slug="r15")
    assert _val(r, DIL) == 3.07, r[DIL]


# ===== G (R88): units-note grammar =====
@pytest.mark.parametrize("note", ["(in millions, except per share amounts and pro forma data)", "(in millions except per share combined)",
                                  "(dollars in millions, restated)", "(in millions; unaudited; as adjusted)"])
def test_w07_units_note_with_extra_words(note):
    w, t, r, c = ws(TITLE + SUB + f"<table>\n<caption>{note}</caption>\n" + YEARS + row([DILL, "$3.40", "$2.93"]) + "</table>\n", slug="r15")
    assert _val(r, DIL) is None, (note, r[DIL])


@pytest.mark.parametrize("note", ["(In millions of U.S. dollars, except per share data and percentages; unaudited)", "(Amounts in billions, except ratios)"])
def test_c07_units_note_closed_forms_bind(note):
    w, t, r, c = ws(TITLE + SUB + f"<table>\n<caption>{note}</caption>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + "</table>\n", slug="r15")
    assert _val(r, DIL) == 3.07, (note, r[DIL])


# ===== H (R90): per-plan label vocabulary =====
@pytest.mark.parametrize("label", ["Reconciliation of Non-GAAP Measures", "GAAP to Core EPS", "Core Diluted Net Earnings per Common Share"])
def test_w08_core_labels_refuse_gaap_eps(label):
    w, t, r, c = ws(TITLE + SUB + f"<p>{label}</p>\n" + PF_T, slug="r15")
    assert _val(r, DIL) is None, (label, r[DIL])


# ===== I (R91): nested tables =====
def test_w09_nested_table_in_a_later_row():
    body = (TITLE + SUB + "<table>\n" + YEARS + row([DILL, "$3.40", "$2.93"])
            + "<tr><td><table><tr><td>Pro Forma Combined</td></tr></table></td><td></td><td></td></tr>\n" + "</table>\n")
    w, t, r, c = ws(body, slug="r15")
    assert _val(r, DIL) is None, r[DIL]


# ===== J: Q1/Q2 segment route (left open by the ruling) =====
@pytest.mark.parametrize("band,case,head", [
    (["", "2025", "2024"], Q2_FY2027, T2 + SUB2),
    (["", "Six Months Ended December 31, 2026", "Six Months Ended December 31, 2025"], Q2_FY2027, T2),
    (["", "2026", "2025"], Q2_FY2027, T2 + "<h3>Six Months Ended December 31, 2026</h3>\n"),
    (["", "2026", "2025"], Q1_FY2027, T1 + "<h2>Fiscal Year 2026 Highlights</h2>\n"),
    (["", "September 30, 2025", "September 30, 2024"], Q1_FY2027, T1),
], ids=["q2_prior_years", "q2_six_month_band", "q2_six_month_heading", "q1_prior_fy_highlights", "q1_prior_dates"])
def test_w10_q1_q2_segment_other_periods(band, case, head):
    body = head + "<h3>Segment Results</h3>\n<table>\n" + row(band) + row(["Beauty", "4.0%", "3.0%"]) + "</table>\n"
    w, t, r, c = ws(body, case=case, slug="r15")
    assert _val(r, BEAUTY) is None, r[BEAUTY]


@pytest.mark.parametrize("band,case,head", [(["", "2026", "2025"], Q2_FY2027, T2 + SUB2), (["", "2027", "2026"], Q1_FY2027, T1 + SUB1)],
                         ids=["q2_calendar", "q1_fiscal"])
def test_c10_q1_q2_segment_binds(band, case, head):
    body = head + "<h3>Segment Results</h3>\n<table>\n" + row(band) + row(["Beauty", "4.0%", "3.0%"]) + "</table>\n"
    w, t, r, c = ws(body, case=case, slug="r15")
    assert _val(r, BEAUTY) == 4.0, r[BEAUTY]


# ===== K (R94): volume sentence year-level skip =====
@pytest.mark.parametrize("sentence", ["Total P&amp;G volume decreased 2% in the final three months of this fiscal year.",
                                      "Total P&amp;G volume decreased 2% for the fiscal year's fourth quarter."])
def test_g11_quarter_inside_year_phrase_conflicts(sentence):
    w, t, r, c = ws(TITLE + DRV + SUB + table() + f"<p>{sentence}</p>\n", slug="r15")
    assert "value" not in r[TV], (sentence, r[TV])


# ===== x: validator surface =====
HONEST = [
    (T1 + "<h2>Net Sales Change Drivers 2027 versus 2026</h2>\n" + table(), Q1_FY2027),
    (TITLE + "<table>\n" + YEARS + row(["Three Months Ended June 30, 2026", "(1)", "(1)"]) + row([DILL, "$3.07", "$2.93"]) + "</table>\n", Q4_FY2026),
    ("<h1>Fourth Quarter Fiscal Year 2026 Results and Fiscal Year 2027 Outlook</h1>\n" + SEGH + GUIDE_T, Q4_FY2026),
    (T3 + "<h2>Quarter 3 Highlights</h2>\n<h3>Segment Results</h3>\n" + SEG_T, Q3_FY2026),
    (TITLE + SUB + "<p>Pro Forma Combined</p>\n<p>(Unaudited)</p>\n" + PF_T, Q4_FY2026),
    (TITLE + SUB + "<p>Core Results</p>\n" + PF_T, Q4_FY2026),
    (TITLE + DRV + SUB + table() + "<p>Total P&amp;G volume increased 4% this fiscal year.</p>\n", Q4_FY2026),
    (T2 + SUB2 + "<h3>Segment Results</h3>\n<table>\n" + row(["", "2026", "2025"]) + row(["Beauty", "4.0%", "3.0%"]) + "</table>\n", Q2_FY2027),
]


@pytest.mark.parametrize("body,case", HONEST, ids=["q1_versus", "mark_row", "results_outlook_title", "quarter_n", "two_line_refused",
                                                    "core_label_refused", "year_level_sentence", "q2_segment"])
def test_x11_honest_workspace_validates(body, case):
    w, t, r, c = ws(body, case=case, slug="r15")
    try:
        validate_selected_facts(w, source_texts=t, fiscal_scope=c.scope)
    except EconomicObservationError as exc:
        pytest.fail(f"validator REFUSES the extractor's own workspace: {exc}")


FORGE = [
    (T1 + "<h2>Net Sales Change Drivers 2027 versus 2026</h2>\n" + table(), TV, Q1_FY2027),
    (TITLE + "<table>\n" + YEARS + row(["Three Months Ended June 30, 2026", "(1)", "(1)"]) + row([DILL, "$3.07", "$2.93"]) + "</table>\n", DIL, Q4_FY2026),
    (T3 + "<h2>Quarter 3 Highlights</h2>\n<h3>Segment Results</h3>\n" + SEG_T, BEAUTY, Q3_FY2026),
    (TITLE + DRV + SUB + table() + "<p>Total P&amp;G volume increased 4% this fiscal year.</p>\n", TV, Q4_FY2026),
]


@pytest.mark.parametrize("body,metric,case", FORGE, ids=["q1_versus", "mark_row", "quarter_n", "year_level_sentence"])
def test_x12_forged_absence(body, metric, case):
    w, t, r, c = ws(body, case=case, slug="r15")
    assert "value" in r[metric], r[metric]
    _forge_absent(w, metric, metric)
    assert _refuses(w, t, c), "validator ACCEPTS a forged absence"


@pytest.mark.parametrize("body,needle,metric", [
    (TITLE + SUB + "<p>Pro Forma Combined</p>\n<p>(Unaudited)</p>\n" + PF_T, "$3.40", DIL),
    (TITLE + SUB + "<p>Core Results</p>\n" + PF_T, "$3.40", DIL),
    (TITLE + SUB + "<table>\n<tr><td></td><td><table><tr><td>2026</td></tr></table></td><td>2025</td></tr>\n" + row([DILL, "$3.40", "$2.93"]) + "</table>\n", "$3.40", DIL),
    ("<h1>Q4 Outlook</h1>\n" + SEGH + GUIDE_T, "5.0%", BEAUTY),
], ids=["two_line", "core_label", "contains_nested", "outlook_title"])
def test_x13_forged_present_over_refused_table(body, needle, metric):
    w, t, r, c = ws(body, slug="r15")
    assert _val(r, metric) is None, r[metric]
    src = next(iter(t.values()))
    s, e = at(src, needle)
    value = float(needle.strip("$%"))
    w2, t2 = forge_present(w, src, metric, s, e, value, "2026-06-30")
    try:
        ok = not _refuses(w2, t2, c)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"validator raised {type(exc).__name__}: {exc}")
    assert not ok, "validator ACCEPTS a forged present value over a refused table"


# ===== round-2 breadth =====
THREE_YEAR = [
    (T1 + "<h2>Net Sales Change Drivers 2027 vs. 2026 and 2026 vs. 2025</h2>\n" + table(), Q1_FY2027),
    (T2 + "<h2>Net Sales Change Drivers 2027 vs. 2026 vs. 2025</h2>\n" + table(), Q2_FY2027),
    (T1 + "<h2>Net Sales Change Drivers 2027 versus 2026 (2025 Basis)</h2>\n" + table(), Q1_FY2027),
]


@pytest.mark.parametrize("body,case", THREE_YEAR, ids=["two_pairs_q1", "three_year_q2", "basis_year_q1"])
def test_w01c_fy_minus_two_beside_the_pair(body, case):
    w, t, r, c = ws(body, case=case, slug="r15")
    assert "value" not in r[TV], r[TV]


@pytest.mark.parametrize("body,case", [(T1 + "<h2>Net Sales Change Drivers 2027 vs. 2026 vs. 2025</h2>\n" + table(), Q1_FY2027), *THREE_YEAR],
                         ids=["three_year_q1", "two_pairs_q1", "three_year_q2", "basis_year_q1"])
def test_v01c(body, case):
    _v(body, TV, 1.0, case=case)


OUTLOOK_ROUTES = [
    ("<h1>Fourth Quarter and Fiscal Year 2026 Guidance</h1>\n" + SUB + PF_T, DIL, 3.40, Q4_FY2026),
    ("<h1>Fourth Quarter Fiscal Year 2026 — Outlook</h1>\n" + DRV + table(), TV, 1.0, Q4_FY2026),
    ("<h1>First Quarter and Fiscal Year 2027 Outlook</h1>\n" + SEGH + "<table>\n" + row(["", "2027"]) + row(["Beauty", "5.0%"]) + "</table>\n", BEAUTY, 5.0, Q1_FY2027),
    ("<h1>Second Quarter Fiscal Year 2027: Outlook</h1>\n" + SUB2 + "<table>\n" + row(["", "2027", "2026"]) + row([DILL, "$3.40", "$3.07"]) + "</table>\n", DIL, 3.40, Q2_FY2027),
]


@pytest.mark.parametrize("body,metric,wrong,case", OUTLOOK_ROUTES, ids=["q4_dil_guidance", "q4_drivers_dash", "q1_segment_and", "q2_dil_colon"])
def test_w02b_outlook_title_other_routes(body, metric, wrong, case):
    w, t, r, c = ws(body, case=case, slug="r15")
    assert _val(r, metric) != wrong, r[metric]


@pytest.mark.parametrize("body,metric,wrong,case", OUTLOOK_ROUTES, ids=["q4_dil_guidance", "q4_drivers_dash", "q1_segment_and", "q2_dil_colon"])
def test_v02b(body, metric, wrong, case):
    _v(body, metric, wrong, case=case)


BASIS_ROUTES = [
    (TITLE + "<h3>Segment Results</h3>\n<p>Segment results below are shown on a proforma basis.</p>\n" + SEG_T, BEAUTY, 4.0, Q4_FY2026),
    (TITLE + "<h3>Segment Results</h3>\n" + SEG_T + "<p>The segment results above are presented on a pro forma combined company basis.</p>\n", BEAUTY, 4.0, Q4_FY2026),
    (TITLE + DRV + "<p>The drivers below are presented on a combined basis with the acquired business.</p>\n" + table(), TV, 1.0, Q4_FY2026),
    (T1 + SUB1 + "<p>The following table presents non-GAAP results.</p>\n<table>\n" + row(["", "2027", "2026"]) + row([DILL, "$3.40", "$3.07"]) + "</table>\n", DIL, 3.40, Q1_FY2027),
]


@pytest.mark.parametrize("body,metric,wrong,case", BASIS_ROUTES, ids=["segment_proforma", "segment_note_after", "drivers_combined", "q1_non_gaap"])
def test_w03b_basis_prose_other_routes(body, metric, wrong, case):
    w, t, r, c = ws(body, case=case, slug="r15")
    assert _val(r, metric) != wrong, r[metric]


@pytest.mark.parametrize("body,metric,wrong,case", BASIS_ROUTES, ids=["segment_proforma", "segment_note_after", "drivers_combined", "q1_non_gaap"])
def test_v03b(body, metric, wrong, case):
    _v(body, metric, wrong, case=case)


HONEST_LABELS = [
    TITLE + SUB + "<ul><li>Diluted EPS of $3.07, up 5% versus the prior year</li></ul>\n" + "<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + "</table>\n",
    TITLE + SUB + "<p>The results for the quarter were as follows:</p>\n" + "<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + "</table>\n",
    TITLE + SUB + "<p>Amounts may not add due to rounding</p>\n" + "<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + "</table>\n",
    TITLE + SUB + "<p>Adjusted for the reclassification of prior-period amounts, results were in line with plan.</p>\n" + "<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + "</table>\n",
]


@pytest.mark.parametrize("body", HONEST_LABELS, ids=["bullet_no_period", "colon_lead_in", "rounding_note", "adjusted_word_in_prose"])
def test_f04_honest_paragraphs_over_table(body):
    w, t, r, c = ws(body, slug="r15")
    assert _val(r, DIL) == 3.07, r[DIL]


@pytest.mark.parametrize("mutate", ["empty_sources", "facts_not_list", "fact_not_dict", "scope_str"])
def test_x14_malformed_inputs_raise_only_economic_error(mutate):
    import copy
    w, t, r, c = ws(TITLE + SUB + PF_T.replace("$3.40", "$3.07"), slug="r15")
    w = copy.deepcopy(w)
    scope = c.scope
    if mutate == "empty_sources":
        t = {}
    elif mutate == "facts_not_list":
        w["facts"] = {"a": 1}
    elif mutate == "fact_not_dict":
        w["facts"] = [*w["facts"], "junk"]
    else:
        scope = "2026-Q4"
    try:
        validate_selected_facts(w, source_texts=t, fiscal_scope=scope)
    except EconomicObservationError:
        return
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"validator raised {type(exc).__name__}: {exc}")
    pytest.fail("validator accepted a malformed workspace")
