"""Opus round-12 red-team probes for PR #7905 (rulings R71–R75), frozen by the seat as the eleventh suite (R80). Original synthetic data only. No case struck.
Each test asserts the CORRECT behaviour: a failing w* test is a wrong bind, a failing f* test is a fail-closed refusal,
v* tests pair a wrong bind with the validator (they skip once the extractor no longer binds the wrong value), c* are controls."""
from __future__ import annotations

import pytest

import engine.company_intelligence.pg_profile as pgp
from engine.company_intelligence.economic_observations import EconomicObservationError, validate_selected_facts
from tests.test_pg_economic_observations_probes import Q1_FY2027, Q4_FY2026
from tests.test_pg_economic_observations_probes_r4 import Q3_FY2026, TITLE, DRV, SUB, row, table, _forge_absent
from tests.test_pg_economic_observations_probes_r5 import ws, TV, DIL
from tests.test_pg_economic_observations_probes_r7 import PRIOR, CORE, DILL, YEARS, SEG_T, BEAUTY, _val
from tests.test_pg_economic_observations_probes_r10 import T1, T3, GUIDE_T, _spanned

REC = "pg_core_reconciliation_context"
REC_TEXT = "Core EPS excludes a synthetic restructuring item of 0.10."
EPS_T = "<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + "</table>\n"


def _refuses(w, t, c):
    try:
        validate_selected_facts(w, source_texts=t, fiscal_scope=c.scope)
    except EconomicObservationError:
        return True
    return False


def _v(body, metric, wrong, case=Q4_FY2026):
    w, t, r, c = ws(body, case=case, slug="r12")
    got = _val(r, metric)
    if got != wrong:
        pytest.skip(f"extractor did not bind the wrong value (got {got!r})")
    assert _refuses(w, t, c), f"VALIDATOR ACCEPTS wrong value {wrong!r} for {metric}"


# ===== W-A: a bare PRIOR year is neutral in headings/labels (R72 "prior ... neutral in a heading") =====
PRIOR_DRV_HEADING = TITLE + "<h2>Net Sales Change Drivers 2025</h2>\n" + table()
PRIOR_LABEL = TITLE + "<h2>Net Sales Change Drivers</h2>\n<p>2025</p>\n" + table()
PRIOR_ANCESTOR_DRV = TITLE + "<h2>2025 Results</h2>\n<h3>Net Sales Change Drivers</h3>\n" + table()
PRIOR_ANCESTOR_REC = TITLE + "<h2>2025 Results</h2>\n<h3>Core EPS Reconciliation</h3>\n<p>" + REC_TEXT + "</p>\n"
PRIOR_DRV_Q3 = T3 + "<h2>Net Sales Change Drivers 2025</h2>\n" + table()


def test_w01_drivers_heading_naming_only_the_prior_year():
    w, t, r, c = ws(PRIOR_DRV_HEADING)
    assert "value" not in r[TV], ("'Net Sales Change Drivers 2025' table bound as Q4 FY2026", _val(r, TV))


def test_v01():
    _v(PRIOR_DRV_HEADING, TV, 1.0)


def test_w02_bare_prior_year_label_over_drivers_table():
    w, t, r, c = ws(PRIOR_LABEL)
    assert "value" not in r[TV], ("label '2025' ignored; drivers table bound as Q4 FY2026", _val(r, TV))


def test_v02():
    _v(PRIOR_LABEL, TV, 1.0)


def test_w03_prior_year_ancestor_section_drivers():
    w, t, r, c = ws(PRIOR_ANCESTOR_DRV)
    assert "value" not in r[TV], ("drivers table inside a '2025 Results' section bound", _val(r, TV))


def test_v03():
    _v(PRIOR_ANCESTOR_DRV, TV, 1.0)


def test_w04_prior_year_ancestor_section_reconciliation():
    w, t, r, c = ws(PRIOR_ANCESTOR_REC)
    assert "value" not in r[REC], ("reconciliation paragraph inside a '2025 Results' section bound", _val(r, REC))


def test_v04():
    _v(PRIOR_ANCESTOR_REC, REC, REC_TEXT)


def test_w05_prior_drivers_heading_q3():
    w, t, r, c = ws(PRIOR_DRV_Q3, case=Q3_FY2026, slug="r12q3")
    assert "value" not in r[TV], _val(r, TV)


def test_v05():
    _v(PRIOR_DRV_Q3, TV, 1.0, case=Q3_FY2026)


# ===== W-B: Q1 FY2027 -- the calendar year of the quarter end is a CURRENT form (R72 + plan current_forms) =====
Q1_DRV_2026 = T1 + "<h2>Net Sales Change Drivers 2026</h2>\n" + table()
Q1_FY_COLS_EPS = T1 + "<table>\n" + row(["", "2027", "2026"]) + row([DILL, "$3.20", "$3.07"]) + "</table>\n"
Q1_FY_COLS_SEG = T1 + "<h2>Segment Results</h2>\n<table>\n" + row(["", "2027", "2026"]) + row(["Beauty", "5.0%", "4.0%"]) + "</table>\n"


def test_c06_q1_drivers_2026_vs_2025_refused_control():
    w, t, r, c = ws(T1 + "<h2>Net Sales Change Drivers 2026 vs. 2025</h2>\n" + table(), case=Q1_FY2027, slug="r12q1")
    assert "value" not in r[TV], _val(r, TV)


def test_w06_q1_drivers_heading_2026_without_vs_admitted():
    w, t, r, c = ws(Q1_DRV_2026, case=Q1_FY2027, slug="r12q1")
    assert "value" not in r[TV], ("'2026 vs. 2025' is foreign but bare '2026' binds FY2026 drivers as Q1 FY2027", _val(r, TV))


def test_v06():
    _v(Q1_DRV_2026, TV, 1.0, case=Q1_FY2027)


def test_w07_q1_fiscal_year_columns_bind_prior_column_as_current_eps():
    w, t, r, c = ws(Q1_FY_COLS_EPS, case=Q1_FY2027, slug="r12q1")
    assert _val(r, DIL) != 3.07, ("'2027 | 2026' band: the 2026 (prior fiscal) column bound as current diluted EPS", r[DIL])


def test_v07():
    _v(Q1_FY_COLS_EPS, DIL, 3.07, case=Q1_FY2027)


def test_w08_q1_fiscal_year_columns_bind_prior_column_as_current_segment():
    w, t, r, c = ws(Q1_FY_COLS_SEG, case=Q1_FY2027, slug="r12q1")
    assert _val(r, BEAUTY) != 4.0, ("'2027 | 2026' band: prior column bound as Q1 FY2027 Beauty", r[BEAUTY])


def test_v08():
    _v(Q1_FY_COLS_SEG, BEAUTY, 4.0, case=Q1_FY2027)


# ===== W-C: R71 -- an EMPTY first thead/tfoot is still the first header/footer group (CSS 2.1 17.2) =====
EMPTY_THEAD = (TITLE + SUB + "<table>\n<thead></thead>\n<tbody>" + YEARS + row([DILL, "$3.07", "$2.93"]) + "</tbody>\n<tbody>"
               + row(["Twelve Months Ended June 30, 2026", "", ""]) + "</tbody>\n<thead>" + YEARS
               + row(["Core EPS", "$12.50", "$11.90"]) + "</thead></table>\n")
EMPTY_TFOOT = (TITLE + SUB + "<table>\n<tfoot></tfoot>\n<thead>" + YEARS + "</thead>\n<tbody>" + row([DILL, "$3.07", "$2.93"])
               + row(["Twelve Months Ended June 30, 2026", "", ""]) + "</tbody>\n<tfoot>" + row(["Core EPS", "$12.50", "$11.90"])
               + "</tfoot>\n<tbody>" + row(["Three Months Ended June 30, 2026", "", ""]) + row(["Net Sales", "$21,000", "$20,500"])
               + "</tbody></table>\n")


def test_w09_empty_first_thead_second_thead_hoisted():
    w, t, r, c = ws(EMPTY_THEAD)
    assert _val(r, CORE) is None, ("second thead hoisted because the first thead has no rows; annual Core EPS bound", _val(r, CORE))


def test_v09():
    _v(EMPTY_THEAD, CORE, 12.5)


def test_w10_empty_first_tfoot_second_tfoot_sunk_below_scope_label():
    w, t, r, c = ws(EMPTY_TFOOT)
    assert _val(r, CORE) is None, ("second tfoot sunk below 'Three Months Ended'; twelve-month Core EPS bound", _val(r, CORE))


def test_v10():
    _v(EMPTY_TFOOT, CORE, 12.5)


def test_c11_thead_after_tbody_hoisted_control():
    body = TITLE + SUB + "<table>\n<tbody>" + row([DILL, "$3.07", "$2.93"]) + "</tbody>\n<thead>" + YEARS + "</thead></table>\n"
    w, t, r, c = ws(body)
    assert (_val(r, DIL), _val(r, PRIOR)) == (3.07, 2.93), (r[DIL], r[PRIOR])


def test_c12_tfoot_first_then_thead_control():
    body = (TITLE + SUB + "<table>\n<tfoot>" + row(["Core EPS", "$2.95", "$2.80"]) + "</tfoot>\n<thead>" + YEARS + "</thead>\n<tbody>"
            + row([DILL, "$3.07", "$2.93"]) + "</tbody></table>\n")
    w, t, r, c = ws(body)
    assert (_val(r, DIL), _val(r, CORE)) == (3.07, 2.95), (r[DIL], r[CORE])


def test_c13_rowspan_in_thead_clipped_at_group_boundary_control():
    body = (TITLE + SUB + '<table>\n<thead><tr><td rowspan="3"></td><td>2026</td><td>2025</td></tr></thead>\n<tbody>'
            + row([DILL, "$3.07", "$2.93"]) + "</tbody></table>\n")
    w, t, r, c = ws(body)
    assert _val(r, DIL) == 3.07, r[DIL]


def test_c14_rowspan_zero_in_later_thead_drawn_in_place_control():
    body = (TITLE + SUB + "<table>\n<thead>" + YEARS + "</thead>\n<tbody>" + row([DILL, "$3.07", "$2.93"]) + "</tbody>\n<thead>"
            + '<tr><td>Core EPS</td><td rowspan="0">$2.95</td><td>$2.80</td></tr></thead></table>\n')
    w, t, r, c = ws(body)
    assert (_val(r, DIL), _val(r, CORE)) == (3.07, 2.95), (r[DIL], r[CORE])


# ===== W-D: R73 title exemption and ancestor gaps =====
FORWARD_TITLE = "<h1>Outlook</h1>\n<h2>Segment Organic Sales Growth</h2>\n" + GUIDE_T
AMBITIONS = T3 + "<h2>Ambitions</h2>\n<h3>Segment Organic Sales Growth</h3>\n" + GUIDE_T
CUMULATIVE = TITLE + "<h2>Cumulative Results</h2>\n<h3>Segment Results</h3>\n" + SEG_T


def test_w15_forward_word_title_is_exempt():
    w, t, r, c = ws(FORWARD_TITLE, case=Q3_FY2026, slug="r12q3")
    assert _val(r, BEAUTY) is None, ("first heading 'Outlook' exempt as title; fiscal-year goal bound as Q3 Beauty", _val(r, BEAUTY))


def test_v15():
    _v(FORWARD_TITLE, BEAUTY, 5.0, case=Q3_FY2026)


def test_w16_unlisted_forward_ancestor_declared_gap():
    w, t, r, c = ws(AMBITIONS, case=Q3_FY2026, slug="r12q3")
    assert _val(r, BEAUTY) is None, ("'Ambitions' ancestor neutral; goal column bound", _val(r, BEAUTY))


def test_v16():
    _v(AMBITIONS, BEAUTY, 5.0, case=Q3_FY2026)


def test_w17_cumulative_ancestor():
    w, t, r, c = ws(CUMULATIVE)
    assert _val(r, BEAUTY) is None, ("'Cumulative Results' ancestor neutral; cumulative 2026 column bound as Q4", _val(r, BEAUTY))


def test_v17():
    _v(CUMULATIVE, BEAUTY, 4.0)


def test_c18_nested_outlook_h2_not_released_by_scope_h4_control():
    body = TITLE + "<h2>Outlook</h2>\n<h3>Segment Results</h3>\n<h4>Fourth Quarter Segment Results</h4>\n" + SEG_T
    w, t, r, c = ws(body)
    assert _val(r, BEAUTY) is None, _val(r, BEAUTY)


def test_c19_outlook_released_by_sibling_h2_control():
    body = TITLE + "<h2>Outlook</h2>\n<h3>Guidance</h3>\n<h2>Segment Results</h2>\n" + SEG_T
    w, t, r, c = ws(body)
    assert _val(r, BEAUTY) == 4.0, r[BEAUTY]


# ===== W-E: R73 label-vs-sentence -- a label by shape that is a sentence by punctuation/literal =====
@pytest.mark.parametrize("label", ["Q3 2026.", "January to March 2026.", "Q3 2026 (in $000s)"], ids=["q3_dot", "jan_mar_dot", "q3_literal"])
def test_w20_unreadable_foreign_label_demoted_to_prose(label):
    w, t, r, c = ws(TITLE + DRV + f"<p>{label}</p>\n" + table())
    assert "value" not in r[TV], (label, _val(r, TV))


def test_v20():
    _v(TITLE + DRV + "<p>Q3 2026.</p>\n" + table(), TV, 1.0)


def test_c21_scope_label_with_dot_control():
    w, t, r, c = ws(TITLE + DRV + "<p>Three Months Ended June 30, 2026.</p>\n" + table())
    assert _val(r, TV) == 1.0, r[TV]


def test_c22_foreign_readable_label_with_dot_control():
    w, t, r, c = ws(TITLE + DRV + "<p>Three Months Ended March 31, 2026.</p>\n" + table())
    assert "value" not in r[TV], _val(r, TV)


# ===== W-F: basis -- a band word naming a non-GAAP basis over one column =====
PRO_FORMA = TITLE + SUB + "<table>\n" + row(["", "Pro Forma", ""]) + YEARS + row([DILL, "$3.40", "$2.93"]) + "</table>\n"


def test_w23_pro_forma_column_bound_as_gaap_diluted_eps():
    w, t, r, c = ws(PRO_FORMA)
    assert _val(r, DIL) is None, ("'Pro Forma' column bound as GAAP diluted EPS", r[DIL])


def test_v23():
    _v(PRO_FORMA, DIL, 3.4)


# ===== F: fail-closed refusals (correct value missed) =====
def test_f30_reconciliation_scope_label_turns_section_off():
    body = TITLE + "<h2>Reconciliation of Non-GAAP Measures</h2>\n<p>Three Months Ended June 30, 2026</p>\n<p>" + REC_TEXT + "</p>\n"
    w, t, r, c = ws(body)
    assert _val(r, REC) == REC_TEXT, r[REC]


def test_f31_fourth_quarter_2026_vs_2025_heading():
    w, t, r, c = ws(TITLE + "<h2>Fourth Quarter Segment Results 2026 vs. 2025</h2>\n" + SEG_T)
    assert _val(r, BEAUTY) == 4.0, r[BEAUTY]


@pytest.mark.parametrize("sub", [["", "US$", "", ""], ["", "(1a)", "", ""], ["", "(ii)", "", ""], ["", "†", "", ""]],
                         ids=["usd_prefix", "1a", "roman_ii", "dagger"])
def test_f32_plain_marks_outside_r74(sub):
    w, t, r, c = ws(_spanned(sub, [DILL, "", "$3.07", "$2.93"]))
    assert _val(r, DIL) == 3.07, (sub, r[DIL])


def test_f33_unreadable_other_period_volume_sentence_conflicts():
    body = TITLE + DRV + SUB + table() + "<p>Total P&amp;G volume increased 3% in Q3 2026.</p>\n"
    w, t, r, c = ws(body)
    assert _val(r, TV) == 1.0, r[TV]


def test_f34_non_gaap_without_hyphen():
    w, t, r, c = ws(TITLE + "<h2>Non GAAP Reconciliation</h2>\n<p>" + REC_TEXT + "</p>\n")
    assert _val(r, REC) == REC_TEXT, r[REC]


# ===== Validator surface (a): a forged absence hides a bound value =====
def test_x40_validator_accepts_forged_absence_over_bound_value():
    w, t, r, c = ws(TITLE + SUB + EPS_T)
    assert _val(r, DIL) == 3.07
    _forge_absent(w, DIL, DIL)
    assert _refuses(w, t, c), "validator ACCEPTS a forged typed absence over a uniquely addressable diluted EPS (round-6 disposition (a), still open)"
