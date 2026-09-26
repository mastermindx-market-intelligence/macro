"""Opus round-13 red-team probes for PR #7905 (rulings R76–R80), frozen by the seat as the twelfth suite (R86). Original synthetic data only. f11, f12 and the "Q3'26" case of f15 struck by R81; x25 adapted by R86.
Each test asserts the CORRECT behaviour: failing w* = wrong bind; failing f* = fail-closed refusal; failing g* = a
gate that let a conflict through; v* pair a wrong bind with the validator (skip if the wrong value is not bound);
x* = validator surface; c* = controls."""
from __future__ import annotations

import copy
import pytest

import engine.company_intelligence.pg_profile as pgp
from engine.company_intelligence.economic_observations import EconomicObservationError, validate_selected_facts
from tests.test_pg_economic_observations_probes import Q1_FY2027, Q4_FY2026
from tests.test_pg_economic_observations_probes_r4 import Q3_FY2026, TITLE, DRV, SUB, row, table, _forge_absent, HEAD, VALS
from tests.test_pg_economic_observations_probes_r5 import ws, TV, DIL, forge_present, at
from tests.test_pg_economic_observations_probes_r7 import PRIOR, CORE, DILL, YEARS, SEG_T, BEAUTY, _val
from tests.test_pg_economic_observations_probes_r10 import T1, T3, GUIDE_T, _spanned

REC = "pg_core_reconciliation_context"
REC_TEXT = "Core EPS excludes a synthetic restructuring item of 0.10."
NSG = "pg_reported_sales_growth_pct"
MIX = "pg_mix_contribution_pp"
EPS_T = "<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + "</table>\n"
SUB1 = "<h3>Three Months Ended September 30, 2026</h3>\n"


def _refuses(w, t, c):
    try:
        validate_selected_facts(w, source_texts=t, fiscal_scope=c.scope)
    except EconomicObservationError:
        return True
    return False


def _v(body, metric, wrong, case=Q4_FY2026):
    w, t, r, c = ws(body, case=case, slug="r13")
    got = _val(r, metric)
    if got != wrong:
        pytest.skip(f"extractor did not bind the wrong value (got {got!r})")
    assert _refuses(w, t, c), f"VALIDATOR ACCEPTS wrong value {wrong!r} for {metric}"


# ===== W-A (R76): the drivers-heading regex judges only its FIRST year =====
DRV_3Y = TITLE + "<h2>Net Sales Change Drivers 2026 vs. 2023</h2>\n" + table()
DRV_2Y_Q1 = T1 + "<h2>Net Sales Change Drivers 2027 vs. 2025</h2>\n" + table()


def test_w01_drivers_heading_fiscal_year_vs_non_prior_year_q4():
    w, t, r, c = ws(DRV_3Y)
    assert "value" not in r[TV], ("'Net Sales Change Drivers 2026 vs. 2023' (three-year stack) bound as the quarter", _val(r, TV))


def test_v01():
    _v(DRV_3Y, TV, 1.0)


def test_w01b_drivers_heading_fiscal_year_vs_non_prior_year_q1():
    w, t, r, c = ws(DRV_2Y_Q1, case=Q1_FY2027)
    assert "value" not in r[TV], ("'Net Sales Change Drivers 2027 vs. 2025' bound in Q1 FY2027", _val(r, TV))


def test_v01b():
    _v(DRV_2Y_Q1, TV, 1.0, case=Q1_FY2027)


# ===== W-B (R79): a column-label metric's own column period is never judged =====
_D7 = ["Volume with Acquisitions &amp; Divestitures", "Volume Excluding Acquisitions &amp; Divestitures", "Foreign Exchange",
       "Price", "Mix", "Other", "Organic Sales Growth"]
PRIOR_NSG_COL = (TITLE + DRV + "<table>\n"
                 + '<tr><td></td><td colspan="7">Three Months Ended June 30, 2026</td><td>Three Months Ended June 30, 2025</td></tr>\n'
                 + row(["", *_D7, "Net Sales Growth"])
                 + row(["Total P&amp;G", "1.0%", "1.0%", "(1.0)%", "0.5%", "0.5%", "1.0%", "1.0%", "9.9%"]) + "</table>\n")


def test_w02_prior_year_net_sales_growth_column_bound_as_current():
    w, t, r, c = ws(PRIOR_NSG_COL)
    assert _val(r, NSG) != 9.9, ("Net Sales Growth stacked under 'Three Months Ended June 30, 2025' bound as Q4 FY2026", r[NSG])


def test_v02():
    _v(PRIOR_NSG_COL, NSG, 9.9)


def test_c02_same_table_current_drivers_still_bind():
    w, t, r, c = ws(PRIOR_NSG_COL)
    assert _val(r, TV) == 1.0, r[TV]


# ===== W-C (R76 band reading): a non-matching column carrying the fiscal year flips the whole band to fiscal =====
GUIDE_COL_Q1 = T1 + SUB1 + "<table>\n" + row(["", "2026", "2025", "2027 Guidance"]) + row([DILL, "$3.20", "$3.07", "$13.00"]) + "</table>\n"


def test_w03_calendar_band_with_fiscal_guidance_column_prior_eps():
    w, t, r, c = ws(GUIDE_COL_Q1, case=Q1_FY2027)
    assert _val(r, PRIOR) != 3.20, ("calendar '2026' (current quarter) column bound as PRIOR diluted EPS", r[PRIOR])


def test_v03():
    _v(GUIDE_COL_Q1, PRIOR, 3.20, case=Q1_FY2027)


def test_f03_calendar_band_with_fiscal_guidance_column_current_eps():
    w, t, r, c = ws(GUIDE_COL_Q1, case=Q1_FY2027)
    assert _val(r, DIL) == 3.20, r[DIL]


# ===== W-D (R77): parentheticals are stripped before positive admission, so a topic/forward word in parentheses is invisible =====
@pytest.mark.parametrize("paren", ["Outlook", "Guidance", "Long-Term Ambitions", "Targets", "Illustrative"])
def test_w04_parenthetical_topic_in_admitted_heading(paren):
    w, t, r, c = ws(TITLE + f"<h2>Segment Organic Sales Growth ({paren})</h2>\n" + GUIDE_T)
    assert "value" not in r[BEAUTY], (f"'Segment Organic Sales Growth ({paren})' goal table bound", _val(r, BEAUTY))


def test_v04():
    _v(TITLE + "<h2>Segment Organic Sales Growth (Outlook)</h2>\n" + GUIDE_T, BEAUTY, 5.0)


def test_c04_same_words_unparenthesised_refuse():
    w, t, r, c = ws(TITLE + "<h2>Segment Organic Sales Growth Outlook</h2>\n" + GUIDE_T)
    assert "value" not in r[BEAUTY]


PAREN_ANCESTOR = TITLE + "<h2>Highlights (Pro Forma Combined Company)</h2>\n" + SUB + EPS_T


def test_w05_neutral_ancestor_with_parenthetical_basis():
    w, t, r, c = ws(PAREN_ANCESTOR)
    assert _val(r, DIL) is None, ("pro forma EPS under 'Highlights (Pro Forma Combined Company)' bound as GAAP diluted", r[DIL])


def test_v05():
    _v(PAREN_ANCESTOR, DIL, 3.07)


def test_c05_unparenthesised_ancestor_refuses():
    w, t, r, c = ws(TITLE + "<h2>Pro Forma Combined Company Highlights</h2>\n" + SUB + EPS_T)
    assert _val(r, DIL) is None


# ===== W-E: a basis named at TABLE level (caption / label paragraph) is not read (R79 reads it only over one column) =====
CAPTION_BASIS = TITLE + SUB + "<table>\n<caption>Pro Forma Combined</caption>\n" + YEARS + row([DILL, "$3.40", "$2.93"]) + "</table>\n"
PARA_BASIS = TITLE + SUB + "<p>Pro Forma (Unaudited)</p>\n" + "<table>\n" + YEARS + row([DILL, "$3.40", "$2.93"]) + "</table>\n"


def test_w06_pro_forma_caption():
    w, t, r, c = ws(CAPTION_BASIS)
    assert _val(r, DIL) is None, ("table captioned 'Pro Forma Combined' bound as GAAP diluted EPS", r[DIL])


def test_v06():
    _v(CAPTION_BASIS, DIL, 3.40)


def test_w06b_pro_forma_paragraph_label():
    w, t, r, c = ws(PARA_BASIS)
    assert _val(r, DIL) is None, ("table under '<p>Pro Forma (Unaudited)</p>' bound as GAAP diluted EPS", r[DIL])


def test_v06b():
    _v(PARA_BASIS, DIL, 3.40)


# ===== W-F (R77 title rule): the exemption attaches to whatever heading comes first, not to a masthead =====
NO_MASTHEAD = "<p>Synthetic Co. reported results today.</p>\n<h2>Supplemental Pro Forma Information</h2>\n" + SUB + "<table>\n" + YEARS + row([DILL, "$3.40", "$2.93"]) + "</table>\n"


def test_w07_first_heading_topic_exempt_without_masthead():
    w, t, r, c = ws(NO_MASTHEAD)
    assert _val(r, DIL) is None, ("'Supplemental Pro Forma Information' (first heading) exempt; pro forma EPS bound", r[DIL])


def test_v07():
    _v(NO_MASTHEAD, DIL, 3.40)


def test_c07_same_heading_after_masthead_refuses():
    w, t, r, c = ws(TITLE + "<h2>Supplemental Pro Forma Information</h2>\n" + SUB + "<table>\n" + YEARS + row([DILL, "$3.40", "$2.93"]) + "</table>\n")
    assert _val(r, DIL) is None


# ===== W-G (declared-open 2): a caption inside an unclosed td is folded into the cell =====
CAP_IN_TD = (TITLE + "<table>\n" + YEARS + "<tr><td>" + DILL + "</td><td>$12.00</td><td>$11.00</td><td>"
             "<caption>Twelve Months Ended June 30, 2026</caption></tr>\n</table>\n")


def test_w08_caption_inside_unclosed_td():
    w, t, r, c = ws(CAP_IN_TD)
    assert _val(r, DIL) is None, ("twelve-month caption swallowed by an unclosed td; annual EPS bound as Q4", r[DIL], r[PRIOR])


def test_v08():
    _v(CAP_IN_TD, DIL, 12.0)


def test_c08_caption_in_place_refuses():
    w, t, r, c = ws(TITLE + "<table>\n<caption>Twelve Months Ended June 30, 2026</caption>\n" + YEARS + row([DILL, "$12.00", "$11.00"]) + "</table>\n")
    assert _val(r, DIL) is None


# ===== W-H (declared-open 1): a table nested inside the thead of an annual-captioned table =====
NESTED = (TITLE + "<table>\n<caption>Twelve Months Ended June 30, 2026</caption>\n<thead><tr><td>"
          + "<table>\n" + YEARS + row([DILL, "$12.00", "$11.00"]) + "</table>" + "</td></tr></thead>\n</table>\n")


def test_w09_nested_table_in_annual_thead():
    w, t, r, c = ws(NESTED)
    assert _val(r, DIL) is None, ("table nested in an annual-captioned thead bound as Q4", r[DIL])


def test_v09():
    _v(NESTED, DIL, 12.0)


# ===== W-I (R78): a section label row carrying a dash literal is a DATA row and never opens a section =====
DASH_SECTION = (TITLE + "<table>\n" + YEARS + row(["Twelve Months Ended June 30, 2026", "—", "—"])
                + row([DILL, "$12.00", "$11.00"]) + "</table>\n")


def test_w10_twelve_month_section_row_with_dashes():
    w, t, r, c = ws(DASH_SECTION)
    assert _val(r, DIL) is None, ("row under 'Twelve Months Ended June 30, 2026 | - | -' bound as Q4", r[DIL])


def test_v10():
    _v(DASH_SECTION, DIL, 12.0)


# ===== Refusals / R76-R79 edges =====
# f11 ("FY2027 | FY2026" band binds) STRUCK by seat ruling R81: a bare fiscal-year label in a table's own band names a
# fiscal YEAR column (R67), and a quarterly table so labelled cannot be told from a full-year one; refusing is fail-closed.
# f12 ("First Quarter Segment Results 2026 vs. 2025" binds in Q1 FY2027) STRUCK by R81: the calendar spelling of an
# ordinal quarter in a Q1/Q2 release is ambiguous with the prior fiscal quarter -- the frozen s11 case pins "First
# Quarter 2026" as NOT the admitted quarter under Q1 FY2027 -- so it stays foreign.


def test_f13_fiscal_year_highlights_ancestor_q4():
    w, t, r, c = ws(TITLE + "<h2>Fiscal Year 2026 Highlights</h2>\n" + SUB + EPS_T)
    assert _val(r, DIL) == 3.07, r[DIL]


def test_f14_q3_highlights_ancestor():
    w, t, r, c = ws(T3 + "<h2>Q3 Highlights</h2>\n<h3>Segment Results</h3>\n" + SEG_T, case=Q3_FY2026)
    assert _val(r, BEAUTY) == 4.0, r[BEAUTY]


# f15's "Q3'26" case STRUCK by R81: an apostrophe year with no fiscal marker is a calendar spelling and stays unreadable;
# the fiscal spellings "3Q FY26" and "Q3 FY26" bind.
@pytest.mark.parametrize("label", ["3Q FY26", "Q3 FY26"])
def test_f15_readable_q3_label_spellings(label):
    w, t, r, c = ws(T3 + "<h2>Segment Results</h2>\n" + f"<p>{label}</p>\n" + SEG_T, case=Q3_FY2026)
    assert _val(r, BEAUTY) == 4.0, (label, r[BEAUTY])


@pytest.mark.parametrize("sub", [["", "(iv)", "", ""], ["", "(ix)", "", ""], ["", "(x)", "", ""], ["", "(vi)", "", ""],
                                 ["", "(10a)", "", ""], ["", "(1b)", "", ""], ["", "US $", "", ""]],
                         ids=["iv", "ix", "x", "vi", "10a", "1b", "US_space_dollar"])
def test_f16_plain_marks(sub):
    w, t, r, c = ws(_spanned(sub, [DILL, "", "$3.07", "$2.93"]))
    assert _val(r, DIL) == 3.07, (sub, r[DIL])


@pytest.mark.parametrize("sub", [["", "(cy)", "", ""], ["", "(ci)", "", ""]], ids=["cy", "ci"])
def test_c16_two_letter_codes_refuse(sub):
    w, t, r, c = ws(_spanned(sub, [DILL, "", "$3.07", "$2.93"]))
    assert _val(r, DIL) is None, (sub, r[DIL])


def test_f17_calendar_current_beside_fiscal_prior_form_q1():
    w, t, r, c = ws(T1 + SUB1 + "<table>\n" + row(["", "2026", "Q1 FY2026"]) + row([DILL, "$3.20", "$3.07"]) + "</table>\n", case=Q1_FY2027)
    assert (_val(r, DIL), _val(r, PRIOR)) == (3.20, 3.07), (r[DIL], r[PRIOR])


@pytest.mark.parametrize("band,cur,pri", [(["2026", "2027"], "$3.07", "$3.20"), (["2027", "2026", "2025"], "$3.20", "$3.07")],
                         ids=["reversed", "three_col"])
def test_c18_q1_fiscal_band_orders(band, cur, pri):
    vals = [cur, pri] if len(band) == 2 else [cur, pri, "$2.80"]
    w, t, r, c = ws(T1 + SUB1 + "<table>\n" + row(["", *band]) + row([DILL, *vals]) + "</table>\n", case=Q1_FY2027)
    assert (_val(r, DIL), _val(r, PRIOR)) == (3.20, 3.07), (r[DIL], r[PRIOR])


@pytest.mark.parametrize("years,binds", [("2027 vs. 2026", True), ("2027", True), ("2026", False), ("2026 vs. 2025", False)])
def test_c19_q1_drivers_heading_years(years, binds):
    w, t, r, c = ws(T1 + f"<h2>Net Sales Change Drivers {years}</h2>\n" + table(), case=Q1_FY2027)
    assert (_val(r, TV) == 1.0) is binds, (years, r[TV])


# ===== g: the R32 cross-check vs R79's "the quarter counts" =====
@pytest.mark.parametrize("sentence", ["Total P&amp;G volume decreased 2% in the quarter.", "Total P&amp;G volume decreased 2% this quarter."])
def test_g20_same_quarter_conflicting_volume_sentence(sentence):
    w, t, r, c = ws(TITLE + DRV + SUB + table() + f"<p>{sentence}</p>\n")
    assert "value" not in r[TV], ("conflicting same-quarter volume sentence skipped; cross-check passed", sentence, _val(r, TV))


# ===== R78 grid controls =====
@pytest.mark.parametrize("markup", [
    "<table>\n<thead></thead><thead></thead><tbody>" + YEARS + row([DILL, "$3.07", "$2.93"]) + "</tbody></table>\n",
    "<table>\n</thead><thead></thead><tbody>" + YEARS + row([DILL, "$3.07", "$2.93"]) + "</tbody></table>\n",
    "<table>\n<thead>" + YEARS + "</thead><tbody></tbody><tbody>" + row([DILL, "$3.07", "$2.93"]) + "</tbody></table>\n",
    "<table>\n<tfoot></tfoot><thead></thead><thead>" + YEARS + "</thead><tbody>" + row([DILL, "$3.07", "$2.93"]) + "</tbody></table>\n",
], ids=["two_empty_theads", "stray_end_then_empty", "empty_tbody_between", "empty_tfoot_empty_thead_second_thead"])
def test_c21_grid_groups(markup):
    w, t, r, c = ws(TITLE + SUB + markup)
    assert _val(r, DIL) == 3.07, r[DIL]


# ===== x: validator surface =====
COMBINED_AND_MIX = (TITLE + DRV + SUB + "<table>\n" + row(["", "Volume/Mix", *HEAD]) + row(["Total P&amp;G", "1.5%", *VALS]) + "</table>\n")


def test_x22_combined_absence_forged_over_separately_bound_mix():
    w, t, r, c = ws(COMBINED_AND_MIX)
    assert _val(r, MIX) == 0.5, r[MIX]
    _forge_absent(w, MIX, f"{MIX} combined volume/mix")
    assert _refuses(w, t, c), "validator ACCEPTS a combined-subject absence over a separately bound Mix value"


CORE_T = "<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + row(["Core EPS", "$3.11", "$2.97"]) + "</table>\n"
NZ_T = TITLE + DRV + SUB + table(vals=["1.0%", "1.0%", "(1.0)%", "0.5%", "—", "1.0%", "3.0%", "1.0%"]) + "<p>A dash means zero.</p>\n"


@pytest.mark.parametrize("body,metric", [
    (TITLE + SUB + CORE_T, DIL), (TITLE + SUB + CORE_T, PRIOR), (TITLE + SUB + CORE_T, CORE), (TITLE + SUB + CORE_T, "pg_prior_core_eps"),
    (TITLE + DRV + SUB + table(), TV), (TITLE + DRV + SUB + table(), "pg_fx_contribution_pp"),
    (TITLE + "<h2>Segment Results</h2>\n" + SEG_T, BEAUTY),
    (TITLE + "<h2>Core EPS Reconciliation</h2>\n<p>" + REC_TEXT + "</p>\n", REC),
    (NZ_T, MIX),
    (TITLE + DRV + SUB + table() + "<p>Total P&amp;G volume increased 1% in the quarter.</p>\n", TV),
], ids=["dil", "prior", "core", "prior_core", "tv", "fx", "beauty", "rec", "dash_neutral_zero", "tv_agreeing_sentence"])
def test_x23_forged_plain_absence_every_class(body, metric):
    w, t, r, c = ws(body)
    assert "value" in r[metric], (metric, r[metric])
    _forge_absent(w, metric, metric)
    assert _refuses(w, t, c), f"validator ACCEPTS a forged plain absence over {metric}"


def test_c23_dash_without_convention_honest_absence_accepted():
    w, t, r, c = ws(TITLE + DRV + SUB + table(vals=["1.0%", "1.0%", "(1.0)%", "0.5%", "—", "1.0%", "3.0%", "1.0%"]))
    assert "value" not in r[MIX]
    _forge_absent(w, MIX, MIX)
    assert not _refuses(w, t, c)


@pytest.mark.parametrize("body", [
    TITLE + "<h2>Core EPS Reconciliation</h2>\n<p>Core EPS excludes a synthetic restructuring &amp; impairment item of 0.10.</p>\n",
    TITLE + SUB + "<table>\n" + YEARS + row([DILL, "&#36;3.07", "$2.93"]) + "</table>\n",
    TITLE + SUB + "<table>\n" + YEARS + row([DILL, "$3.<!-- x -->07", "$2.93"]) + "</table>\n",
], ids=["entity_paragraph", "entity_cell", "comment_in_cell"])
def test_x24_extractor_own_workspace_validates(body):
    w, t, r, c = ws(body)
    try:
        validate_selected_facts(w, source_texts=t, fiscal_scope=c.scope)
    except EconomicObservationError as exc:
        pytest.fail(f"validator REFUSES the extractor's own workspace: {exc} | rows={ {k: r[k] for k in (DIL, REC)} }")


def test_x25_forged_present_where_extractor_refused():
    # ADAPTED at freeze by R86: the original body (GUIDE_COL_Q1) now binds 3.20 under R81's pure-year band reading, so
    # the forged-present surface is probed on the "FY2027 | FY2026" band, which the extractor refuses as annual.
    body = T1 + SUB1 + "<table>\n" + row(["", "FY2027", "FY2026"]) + row([DILL, "$3.20", "$3.07"]) + "</table>\n"
    w, t, r, c = ws(body, case=Q1_FY2027)
    assert _val(r, DIL) is None
    src = next(iter(t.values()))
    s, e = at(src, "$3.20")
    w2, t2 = forge_present(w, src, DIL, s, e, 3.20, "2026-09-30")
    assert _refuses(w2, t2, c), "validator ACCEPTS a forged present current EPS the extractor refused"


def test_x26_forged_period_on_prior():
    w, t, r, c = ws(TITLE + SUB + EPS_T)
    row_ = next(f for f in w["facts"] if isinstance(f, dict) and f.get("metric") == PRIOR)
    row_["period"] = "2026-06-30"
    assert _refuses(w, t, c)
