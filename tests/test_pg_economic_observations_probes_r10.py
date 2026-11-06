"""Opus round-11 red-team probes for PR #7905 (rulings R66–R70), frozen by the seat as the tenth suite (R75). Original synthetic data only. s07 struck by R71, s25 struck by R73."""
from __future__ import annotations

import pytest

import engine.company_intelligence.pg_profile as pgp
from engine.company_intelligence.economic_observations import EconomicObservationError, validate_selected_facts
from tests.test_pg_economic_observations_probes import Q1_FY2027, Q4_FY2026
from tests.test_pg_economic_observations_probes_r4 import Q3_FY2026, HEAD, VALS, TITLE, DRV, SUB, row, table, wrap
from tests.test_pg_economic_observations_probes_r5 import ws, TV, DIL, BASE
from tests.test_pg_economic_observations_probes_r7 import PRIOR, CORE, DILL, YEARS, SEG_T, BEAUTY, _val, _cells

T1 = "<h1>First Quarter Fiscal Year 2027 Results</h1>\n"
T3 = "<h1>Third Quarter Fiscal Year 2026 Results</h1>\n"
GUIDE_T = "<table>\n" + row(["", "2026"]) + row(["Beauty", "5.0%"]) + "</table>\n"


def _refuses(w, t, c):
    try:
        validate_selected_facts(w, source_texts=t, fiscal_scope=c.scope)
    except EconomicObservationError:
        return True
    return False


def _v(body, metric, wrong, case=Q4_FY2026):
    w, t, r, c = ws(body, case=case, slug="r11")
    got = _val(r, metric)
    if got != wrong:
        pytest.skip(f"extractor did not bind the wrong value (got {got!r})")
    assert _refuses(w, t, c), f"VALIDATOR ACCEPTS wrong value {wrong!r} for {metric}"


# ================= R66 =================
SECOND_THEAD = (TITLE + SUB + "<table>\n<thead>" + YEARS + "</thead>\n<tbody>" + row([DILL, "$3.07", "$2.93"]) + "</tbody>\n<tbody>"
                + row(["Twelve Months Ended June 30, 2026", "", ""]) + "</tbody>\n<thead>" + row(["Core EPS", "$12.50", "$11.90"])
                + "</thead></table>\n")


def test_s01_second_thead_is_drawn_in_place_not_hoisted():
    # CSS 2.1 17.2: only the FIRST table-header-group is a header; later theads render as row groups in source order.
    w, t, r, c = ws(SECOND_THEAD)
    assert _val(r, CORE) is None, ("second <thead> hoisted above the twelve-month section; annual Core EPS bound as quarterly", _val(r, CORE))


def test_s01v_validator_on_second_thead():
    _v(SECOND_THEAD, CORE, 12.5)


SECOND_TFOOT = (TITLE + SUB + "<table>\n<thead>" + YEARS + "</thead>\n<tbody>" + row([DILL, "$3.07", "$2.93"]) + "</tbody>\n<tfoot>"
                + row(["Synthetic footer note", "", ""]) + "</tfoot>\n<tfoot>" + row(["Core EPS", "$2.95", "$2.80"]) + "</tfoot>\n<tbody>"
                + row(["Twelve Months Ended June 30, 2026", "", ""]) + "</tbody></table>\n")


def test_s02_second_tfoot_drawn_in_place_binds_quarter_core_eps():
    w, t, r, c = ws(SECOND_TFOOT)
    assert _val(r, CORE) == 2.95, ("second <tfoot> (a row group in place, above the twelve-month label) sunk below it", r[CORE])


def test_s03_rowspan_zero_in_thead_does_not_swallow_body_control():
    body = TITLE + SUB + '<table>\n<thead><tr><td rowspan="0"></td><td>2026</td><td>2025</td></tr></thead>\n<tbody>' + row([DILL, "$3.07", "$2.93"]) + "</tbody></table>\n"
    w, t, r, c = ws(body)
    assert (_val(r, DIL), _val(r, PRIOR)) == (3.07, 2.93), (r[DIL], r[PRIOR])


def test_s04_td_directly_in_thead_without_tr_control():
    body = TITLE + SUB + "<table>\n<thead><td></td><td>2026</td><td>2025</td></thead>\n<tbody>" + row([DILL, "$3.07", "$2.93"]) + "</tbody></table>\n"
    w, t, r, c = ws(body)
    assert _val(r, DIL) == 3.07, r[DIL]


def test_s05_nested_tbody_clips_rowspan_control():
    body = (TITLE + SUB + "<table>\n" + YEARS + f'<tbody><tr><td>{DILL}</td><td rowspan="2">$3.07</td><td>$2.93</td></tr>\n'
            + "<tbody>" + row(["Core EPS", "$2.95"]) + "</tbody></tbody></table>\n")
    w, t, r, c = ws(body)
    assert _val(r, CORE) in (None, 2.95) and _val(r, DIL) == 3.07, (r[CORE], r[DIL])


def test_s06_colspan_overflow_with_valid_rowspan_refuses_table_control():
    body = TITLE + SUB + "<table>\n" + YEARS + f'<tr><td>{DILL}</td><td colspan="99" rowspan="2">$3.07</td><td>$2.93</td></tr>\n' + "</table>\n"
    w, t, r, c = ws(body)
    assert _val(r, DIL) is None and _val(r, PRIOR) is None, (r[DIL], r[PRIOR])


# s07 (rowspan="-0" reads 0) STRUCK by seat ruling R71: the HTML rules for parsing non-negative integers accept an
# optional "+" only, so a leading "-" is a parse error and the attribute takes its default of 1 -- the same reading
# the frozen p04 case pins for rowspan="-2".


# ================= R67 lexicon gaps (SEG_T under a period heading the lexicon does not read) =================
GAPS = ["H2 2026 Segment Results", "1H26 Segment Results", "TTM Segment Results", "LTM Segment Results", "CY2026 Segment Results",
        "Calendar 2026 Segment Results", "52 Weeks Segment Results", "2026-03-31 Segment Results", "03/31/2026 Segment Results",
        "31.03.2026 Segment Results", "Q-3 Segment Results", "Q 3 2026 Segment Results", "Fourth Quarter &#8217;25 Segment Results",
        "Fourth Quarter '25 Segment Results"]


@pytest.mark.parametrize("heading", GAPS)
def test_s10_unlisted_period_forms_fail_closed(heading):
    w, t, r, c = ws(TITLE + f"<h2>{heading}</h2>\n" + SEG_T)
    assert _val(r, BEAUTY) is None, (heading, _val(r, BEAUTY))


@pytest.mark.parametrize("heading", ["TTM Segment Results", "2026-03-31 Segment Results", "Q-3 Segment Results", "Fourth Quarter '25 Segment Results", "H2 2026 Segment Results"])
def test_s10v_validator_on_lexicon_gaps(heading):
    _v(TITLE + f"<h2>{heading}</h2>\n" + SEG_T, BEAUTY, 4.0)


def test_s11_q1_ordinal_with_calendar_year_is_not_the_admitted_quarter():
    # Q1 FY2027 = Jul-Sep 2026. "First Quarter 2026" is fiscal Q1 FY2026 (Jul-Sep 2025) or calendar Q1 2026 (Jan-Mar): never the admitted quarter.
    w, t, r, c = ws(T1 + "<h2>First Quarter 2026 Segment Results</h2>\n" + SEG_T, case=Q1_FY2027, slug="r11q1")
    assert _val(r, BEAUTY) is None, _val(r, BEAUTY)


def test_s11v_validator_on_q1_calendar_year():
    _v(T1 + "<h2>First Quarter 2026 Segment Results</h2>\n" + SEG_T, BEAUTY, 4.0, case=Q1_FY2027)


def test_s12_drivers_heading_with_apostrophe_foreign_quarter():
    w, t, r, c = ws(TITLE + "<h2>Net Sales Change Drivers 2026 vs. 2025 &#8212; Fourth Quarter &#8217;25</h2>\n" + table())
    assert "value" not in r[TV], _val(r, TV)


def test_s13_fy_then_q_order_binds_claim_every_spelling():
    w, t, r, c = ws(TITLE + "<h2>FY26 Q4 Segment Results</h2>\n" + SEG_T)
    assert _val(r, BEAUTY) == 4.0, r[BEAUTY]


def test_s14_scope_vs_bare_prior_year_comparison_heading_control():
    w, t, r, c = ws(TITLE + "<h2>Fourth Quarter Fiscal Year 2026 vs 2025 Segment Results</h2>\n" + SEG_T)
    assert _val(r, BEAUTY) == 4.0, r[BEAUTY]


def _label(n):
    tail = " for the Three Months Ended March 31, 2026"
    base = "Restated segment amounts shown "
    text = base + "z" * (n - len(base) - len(tail)) + tail
    assert len(pgp._period_label_text(text)) == n
    return f"<p>{text}</p>\n"


def test_s15_label_of_121_chars_naming_a_foreign_quarter():
    w, t, r, c = ws(TITLE + DRV + _label(121) + table())
    assert "value" not in r[TV], ("a 121-char foreign period label is ignored; drivers table binds", _val(r, TV))


def test_s15b_label_of_120_chars_control():
    w, t, r, c = ws(TITLE + DRV + _label(120) + table())
    assert "value" not in r[TV], _val(r, TV)


def test_s16_prose_sentence_becomes_label_and_refuses_drivers_table():
    w, t, r, c = ws(TITLE + DRV + SUB + "<p>Net sales grew 4% in fiscal 2026 on strong volume.</p>\n" + table())
    assert _val(r, TV) == 1.0, ("prose sentence read as an annual period label; current drivers table refused", r[TV])


def test_s17_prose_quarter_sentence_refuses_eps_table():
    body = TITLE + SUB + "<p>Diluted EPS was $3.07 for the quarter.</p>\n<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + "</table>\n"
    w, t, r, c = ws(body)
    assert _val(r, DIL) == 3.07, ("prose read as an unknown period label", r[DIL])


PROSE_OVERRIDE = (TITLE + "<h2>Third Quarter Fiscal Year 2026 Segment Results</h2>\n"
                  "<p>Segment amounts are presented on the Fourth Quarter Fiscal Year 2026 basis.</p>\n" + SEG_T)


def test_s18_prose_label_overrides_foreign_heading():
    w, t, r, c = ws(PROSE_OVERRIDE)
    assert _val(r, BEAUTY) is None, ("a prose 'label' naming Q4 re-opened scope under a Third Quarter heading", _val(r, BEAUTY))


def test_s18v_validator_on_prose_override():
    _v(PROSE_OVERRIDE, BEAUTY, 4.0)


@pytest.mark.parametrize("label", ["<ul><li><b>Third-Quarter 2026</b></li></ul>\n", "<ul><li><p><b>Third-Quarter 2026</b></p></li></ul>\n",
                                   "<div><p><b>Third-Quarter 2026</b></p></div>\n"], ids=["li", "li_p", "div_p"])
def test_s19_foreign_label_in_list_or_div(label):
    w, t, r, c = ws(TITLE + DRV + label + table())
    assert "value" not in r[TV], (label, _val(r, TV))


# ================= R68 =================
@pytest.mark.parametrize("heading", ["Looking Ahead: Segment Organic Sales", "Segment Organic Sales Goals", "Segment Sales Plan"])
def test_s20_unlisted_forward_cue_with_results_word_q3(heading):
    w, t, r, c = ws(T3 + f"<h2>{heading}</h2>\n" + GUIDE_T, case=Q3_FY2026, slug="r11q3")
    assert _val(r, BEAUTY) is None, ("fiscal-year goal column bound as Q3 segment growth", heading, _val(r, BEAUTY))


def test_s20v_validator_on_looking_ahead():
    _v(T3 + "<h2>Looking Ahead: Segment Organic Sales</h2>\n" + GUIDE_T, BEAUTY, 5.0, case=Q3_FY2026)


def test_s21_scope_heading_erases_next_quarter_guidance():
    w, t, r, c = ws(T3 + "<h2>Third Quarter Fiscal Year 2026: Next Quarter Segment Guidance</h2>\n" + GUIDE_T, case=Q3_FY2026, slug="r11q3")
    assert _val(r, BEAUTY) is None, _val(r, BEAUTY)


def test_s22_masthead_h1_refuses_whole_release():
    body = "<h1>The Procter &amp; Gamble Company</h1>\n<h2>Fourth Quarter Fiscal Year 2026 Results</h2>\n<h3>Segment Results</h3>\n" + SEG_T
    w, t, r, c = ws(body)
    assert _val(r, BEAUTY) == 4.0, ("company-name masthead h1 opens a non-results section no h2..h6 can release", r[BEAUTY])


def test_s23_overview_h2_governs_segment_results_h3():
    w, t, r, c = ws(TITLE + "<h2>Overview</h2>\n<h3>Segment Results</h3>\n" + SEG_T)
    assert _val(r, BEAUTY) == 4.0, r[BEAUTY]


def test_s24_outlook_for_net_sales_control():
    w, t, r, c = ws(TITLE + "<h2>Outlook for Net Sales</h2>\n<h3>Segment Results</h3>\n" + SEG_T)
    assert _val(r, BEAUTY) is None, _val(r, BEAUTY)


# s25 ("... Guidance Recap Segment Results" binds) STRUCK by seat ruling R73: a governing heading admits only by
# route vocabulary, and a forward word in it refuses whatever period it also names -- the same reading the frozen
# r25 case pins for "Segment Results vs. Expected".  Refusing is fail-closed, never a wrong bind.


def test_s26_h6_outlook_released_by_h6_results_control():
    w, t, r, c = ws(TITLE + "<h6>Outlook</h6>\n<h6>Segment Results</h6>\n" + SEG_T)
    assert _val(r, BEAUTY) == 4.0, r[BEAUTY]


# ================= R69 =================
def _spanned(sub, data):
    return (TITLE + SUB + "<table>\n" + '<tr><td></td><td colspan="2">Three Months Ended June 30, 2026</td><td>Three Months Ended June 30, 2025</td></tr>\n'
            + row(sub) + row(data) + "</table>\n")


@pytest.mark.parametrize("sub", [["", "", "(Unaudited)", ""], ["", "(A)", "(B)", ""], ["", "(1)(2)", "", ""], ["", "**", "", ""]],
                         ids=["Unaudited_capital", "A_B_upper", "double_mark", "stars_bare"])
def test_s30_plain_marks_outside_allow_list_spelling(sub):
    w, t, r, c = ws(_spanned(sub, [DILL, "", "$3.07", "$2.93"]))
    assert _val(r, DIL) == 3.07, (sub, r[DIL])


@pytest.mark.parametrize("sub", [["", "(cy)", "(py)", ""], ["", "(rp)", "(cc)", ""]], ids=["cy_py", "rp_cc"])
def test_s31_two_letter_marks_tell_columns_apart(sub):
    w, t, r, c = ws(_spanned(sub, [DILL, "", "$2.88", "$2.93"]))
    assert _val(r, DIL) is None, ("two-letter parenthetical treated as a footnote mark", sub, _val(r, DIL))


def test_s31v_validator_on_py():
    _v(_spanned(["", "(cy)", "(py)", ""], [DILL, "", "$2.88", "$2.93"]), DIL, 2.88)


def test_s32_lowercase_restated_control():
    w, t, r, c = ws(_spanned(["", "(reported)", "(restated)", ""], [DILL, "", "$3.19", "$2.93"]))
    assert _val(r, DIL) is None, _val(r, DIL)
