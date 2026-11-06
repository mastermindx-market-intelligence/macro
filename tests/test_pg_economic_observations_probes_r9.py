"""Opus round-10 red-team probes for PR #7905 (rulings R61–R65), frozen by the seat as the ninth suite (R70). Original synthetic data only. r03 struck by R66."""
from __future__ import annotations

import pytest

import engine.company_intelligence.pg_profile as pgp
from engine.company_intelligence.economic_observations import EconomicObservationError, validate_selected_facts
from tests.test_pg_economic_observations_probes_r4 import HEAD, VALS, TITLE, DRV, SUB, row, table, wrap
from tests.test_pg_economic_observations_probes_r5 import ws, valid, refused, TV, REC, DIL, BASE
from tests.test_pg_economic_observations_probes_r7 import PRIOR, CORE, DILL, YEARS, SEG_T, BEAUTY, _val, _cells

REC_P = "<p>Core EPS excludes a synthetic restructuring item of 0.10.</p>\n"


def _validator_refuses(w, t, c):
    try:
        validate_selected_facts(w, source_texts=t, fiscal_scope=c.scope)
    except EconomicObservationError:
        return True
    return False


def _v(body, metric, wrong):
    w, t, r, c = ws(body)
    got = _val(r, metric)
    if got != wrong:
        pytest.skip(f"extractor did not bind the wrong value (got {got!r})")
    assert _validator_refuses(w, t, c), f"VALIDATOR ACCEPTS wrong value {wrong!r} for {metric}"


# ================= R61 parser =================
@pytest.mark.parametrize("attr,expect", [
    ('colspan="2 3"', (2, 1)), ('colspan="&#50;"', (2, 1)), ('COLSPAN="2"', (2, 1)),
    ('colspan=" 2"', (1, 1)), ('colspan="۲"', (1, 1)), ('colspan="　2"', (1, 1)),
], ids=["space_sep", "entity", "upper_th", "nbsp_lead", "persian_digit", "ideographic_space"])
def test_r01_span_attribute_html_parity(attr, expect):
    got = _cells(f'<table><tr><th {attr}>a</th><td>b</td></tr></table>')
    assert got[0] == expect, (attr, got)


def test_r02_rowspan_zero_is_end_of_group_in_html():
    got = _cells('<table><tr><td rowspan="0">a</td><td>b</td></tr><tr><td>c</td></tr></table>')
    assert got[0][1] != 1, ("HTML rowspan=0 spans to the end of the row group; parser reads", got)


# r03 (colspan="65" must read 65) STRUCK by seat ruling R66: the frozen p04 case pins "65 reads 1"; an absurd span is
# flagged (TableCell.span_overflow) and the whole table is refused rather than clamped or misaligned.


STRAY = (TITLE + SUB + "<table>\n" + YEARS + f'<tr><td>{DILL}</td><td rowspan="2">$3.07</td><td>$2.93</td></tr>\n'
         + "</thead>" + row(["Core EPS", "$2.95"]) + "</table>\n")


def test_r04_stray_thead_end_tag_does_not_clip_rowspan():
    w, t, r, c = ws(STRAY)
    assert _val(r, CORE) in (None, 3.07), ("stray </thead> (ignored by HTML) clipped a rowspan; prior-year cell bound as current Core EPS", _val(r, CORE))


def test_r04v_validator_on_stray_thead():
    _v(STRAY, CORE, 2.95)


STRAY_TF = STRAY.replace("</thead>", "</tfoot>")


def test_r05_stray_tfoot_end_tag_does_not_clip_rowspan():
    w, t, r, c = ws(STRAY_TF)
    assert _val(r, CORE) in (None, 3.07), _val(r, CORE)


TFOOT_FIRST = (TITLE + SUB + "<table>\n<thead>" + YEARS + "</thead>\n<tfoot>" + row(["Core EPS", "$12.50", "$11.90"])
               + "</tfoot>\n<tbody>" + row([DILL, "$3.07", "$2.93"]) + row(["Twelve Months Ended June 30, 2026", "", ""])
               + "</tbody></table>\n")


def test_r06_tfoot_before_tbody_renders_last():
    w, t, r, c = ws(TFOOT_FIRST)
    assert _val(r, CORE) is None, ("HTML4-order tfoot renders below the twelve-month section; bound as quarter Core EPS", _val(r, CORE))


def test_r06v_validator_on_tfoot_first():
    _v(TFOOT_FIRST, CORE, 12.5)


def test_r07_rowspan_across_implied_tbody_start_clipped_control():
    body = (TITLE + SUB + "<table>\n" + YEARS + f'<tr><td>{DILL}</td><td rowspan="2">$3.07</td><td>$2.93</td></tr>\n'
            + "<tbody>" + row(["Core EPS", "$2.95"]) + "</tbody></table>\n")
    w, t, r, c = ws(body)
    assert _val(r, CORE) in (None, 2.95) and _val(r, DIL) == 3.07, (r[CORE], r[DIL])


def test_r08_uppercase_h2_outlook_governs_h3():
    w, t, r, c = ws(TITLE + "<H2>Outlook</H2>\n<h3>Segment Results</h3>\n" + SEG_T)
    assert _val(r, BEAUTY) is None, _val(r, BEAUTY)


# ================= R62 =================
FOREIGN_NO_MARKER = ["Third-Quarter Segment Results", "Third-Quarter 2026 Segment Results", "Quarter 3 Segment Results",
                     "Prior Quarter Segment Results", "Q3 2026 Segment Results", "3Q26 Segment Results",
                     "2026 Q3 Segment Results", "Third Qtr. Segment Results", "January to March 2026 Segment Results"]


@pytest.mark.parametrize("heading", FOREIGN_NO_MARKER)
def test_r10_foreign_quarter_forms_fail_closed(heading):
    w, t, r, c = ws(TITLE + f"<h2>{heading}</h2>\n" + SEG_T)
    assert _val(r, BEAUTY) is None, (heading, _val(r, BEAUTY))


def test_r10v_validator_on_third_quarter_hyphen():
    _v(TITLE + f"<h2>{FOREIGN_NO_MARKER[0]}</h2>\n" + SEG_T, BEAUTY, 4.0)


def test_r10w_marked_context_quarter_word_lost():
    ident = (2026, 4, __import__("datetime").date(2026, 6, 30))
    assert pgp._marked_context("Prior Quarter Segment Results", ident) == "unknown", pgp._marked_context("Prior Quarter Segment Results", ident)


@pytest.mark.parametrize("heading", ["Q4 FY'26 Segment Results", "Q4 FY-26 Segment Results", "Q4 FY ’26 Segment Results",
                                     "Fourth Quarter Fiscal-Year 2026 Segment Results", "Fourth Quarter FY '26 Segment Results"])
def test_r11_admitted_year_fy_spellings_bind(heading):
    w, t, r, c = ws(TITLE + f"<h2>{heading}</h2>\n" + SEG_T)
    assert _val(r, BEAUTY) == 4.0, (heading, r[BEAUTY])


@pytest.mark.parametrize("heading", ["Q4 FY'25 Segment Results", "Fourth Quarter Fiscal-Year 2025 Segment Results",
                                     "Fourth Quarter FY '25 Segment Results", "Fourth Quarter Fiscal Yr. 2025 Segment Results"])
def test_r12_foreign_fy_spellings_refuse(heading):
    w, t, r, c = ws(TITLE + f"<h2>{heading}</h2>\n" + SEG_T)
    assert _val(r, BEAUTY) is None, (heading, _val(r, BEAUTY))


LONG_PREFIX = "<p>Comparison of segment results and operating performance for the Three Months Ended March 31, 2026</p>\n"


@pytest.mark.parametrize("label", [LONG_PREFIX, "<p><b>Three Months Ended March 31st, 2026</b></p>\n",
                                   "<p><b>Quarter Ended 31/03/2026</b></p>\n", "<p><b>Third-Quarter 2026</b></p>\n",
                                   "<p><b>Three months to March 31, 2026</b></p>\n"],
                         ids=["prefix_64", "ordinal_date", "numeric_date", "hyphen_quarter", "months_to"])
def test_r13_foreign_label_paragraph_forms(label):
    w, t, r, c = ws(TITLE + DRV + label + table())
    assert "value" not in r[TV], (label, _val(r, TV))


def test_r13v_validator_on_long_prefix_label():
    _v(TITLE + DRV + LONG_PREFIX + table(), TV, 1.0)


def test_r14_ordinary_word_marker_in_scope_heading_refuses_drivers_table_per_ruling():
    w, t, r, c = ws(TITLE + DRV + "<h3>Three Months Ended June 30, 2026 &#8212; Fiscal Discipline</h3>\n" + table())
    assert "value" not in r[TV], ("R62(a) mandates refusal of the one drivers table", _val(r, TV))


def test_r15_metric_label_only_row_opens_no_section_control():
    body = (TITLE + SUB + "<table>\n" + YEARS + row(["Twelve Months Ended June 30, 2026", "", ""]) + row([DILL, "", ""])
            + row(["Core EPS", "$12.50", "$11.90"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert _val(r, CORE) is None, _val(r, CORE)


def test_r16_split_section_label_across_cells():
    body = (TITLE + SUB + "<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + row(["Twelve", "Months Ended", "June 30, 2026"])
            + row(["Core EPS", "$12.50", "$11.90"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert _val(r, CORE) is None, _val(r, CORE)


# ================= R63 =================
DEEP = TITLE + "<h2>Outlook</h2>\n<h4>Guidance Assumptions</h4>\n<p>Synthetic assumptions.</p>\n<h3>Segment Results</h3>\n" + SEG_T


def test_r20_deeper_forward_heading_does_not_rebase_the_section():
    w, t, r, c = ws(DEEP)
    assert _val(r, BEAUTY) is None, ("Outlook(h2) > Guidance(h4) > Segment Results(h3): h3 released the h2 section", _val(r, BEAUTY))


def test_r20v_validator_on_deep():
    _v(DEEP, BEAUTY, 4.0)


def test_r21_deeper_forward_rebase_on_reconciliation_path():
    body = BASE + "<h2>Outlook</h2>\n<h4>Guidance</h4>\n<h3>Core EPS Reconciliation</h3>\n" + REC_P
    w, t, r, c = ws(body)
    assert "value" not in r[REC], r[REC]


def test_r22_promoted_allcaps_outlook_governs_real_h3():
    w, t, r, c = ws(TITLE + "<p><b>OUTLOOK</b></p>\n<h3>Segment Results</h3>\n" + SEG_T)
    assert _val(r, BEAUTY) is None, ("promoted OUTLOOK (level 2) not governing a real h3", _val(r, BEAUTY))


def test_r22b_promoted_allcaps_outlook_released_by_h2_control():
    w, t, r, c = ws(TITLE + "<p><b>OUTLOOK</b></p>\n<h2>Segment Results</h2>\n" + SEG_T)
    assert _val(r, BEAUTY) == 4.0, r[BEAUTY]


@pytest.mark.parametrize("title", ["<h1>Fourth Quarter Fiscal Year 2026 Results and Fiscal Year 2027 Outlook</h1>\n",
                                   "<h1>Fourth Quarter Fiscal Year 2026 Results; Fiscal 2027 Guidance</h1>\n"])
def test_r23_results_title_that_also_names_next_year_outlook(title):
    body = title + SUB + "<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + "</table>\n"
    w, t, r, c = ws(body)
    assert _val(r, DIL) == 3.07, ("R63: a heading naming the admitted quarter's results is never forward-looking", r[DIL])


def test_r24_h1_outlook_governs_every_later_h2_per_ruling():
    w, t, r, c = ws(TITLE + "<h1>Outlook</h1>\n<h2>Segment Results</h2>\n" + SEG_T)
    assert _val(r, BEAUTY) is None, _val(r, BEAUTY)


def test_r25_expected_as_past_adjective_refuses_per_ruling():
    w, t, r, c = ws(TITLE + "<h2>Segment Results vs. Expected</h2>\n" + SEG_T)
    assert _val(r, BEAUTY) is None, _val(r, BEAUTY)


def test_r26_forward_state_on_volume_path_deep_rebase():
    body = (TITLE + "<h2>Outlook</h2>\n<h4>Guidance</h4>\n<h3>Volume</h3>\n"
            "<p>Total P&amp;G unit volume increased 7% in the quarter.</p>\n")
    w, t, r, c = ws(body)
    assert "value" not in r[TV], r[TV]


# ================= R64 =================
def _spanned(sub, data):
    return (TITLE + SUB + "<table>\n" + '<tr><td></td><td colspan="2">Three Months Ended June 30, 2026</td><td>Three Months Ended June 30, 2025</td></tr>\n'
            + row(sub) + row(data) + "</table>\n")


PAREN_RESTATED = _spanned(["", "(As Reported)", "(Restated)", ""], [DILL, "", "$3.19", "$2.93"])


def test_r30_parenthesised_restated_subcells_tell_columns_apart():
    w, t, r, c = ws(PAREN_RESTATED)
    assert _val(r, DIL) is None, ("'(Restated)' treated as plain: restated sub-column bound as reported diluted EPS", _val(r, DIL))


def test_r30v_validator_on_paren_restated():
    _v(PAREN_RESTATED, DIL, 3.19)


GREEDY = _spanned(["", "(Unaudited) As Reported (Note 2)", "(Unaudited) Restated (Note 2)", ""], [DILL, "", "$3.19", "$2.93"])


def test_r31_greedy_parenthetical_swallows_words():
    w, t, r, c = ws(GREEDY)
    assert _val(r, DIL) is None, ("'(..) Restated (..)' matched \\(.*\\) as one parenthetical", _val(r, DIL))


def test_r32_three_spanned_with_empty_a_b_subcells_binds():
    body = (TITLE + SUB + "<table>\n" + '<tr><td></td><td colspan="3">Three Months Ended June 30, 2026</td><td>Three Months Ended June 30, 2025</td></tr>\n'
            + row(["", "", "(a)", "(b)", ""]) + row([DILL, "$", "3.07", "", "$2.93"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert _val(r, DIL) == 3.07, r[DIL]


def test_r33_dollar_and_literal_subcells_control():
    body = _spanned(["", "$", "(unaudited)", ""], [DILL, "", "$3.07", "$2.93"])
    w, t, r, c = ws(body)
    assert _val(r, DIL) == 3.07, r[DIL]


def test_r34_promotion_fact():
    blocks = pgp.parse_release_blocks(wrap("<p><b>OUTLOOK</b></p>\n<H2>Seg</H2>\n"))
    kinds = [(b.kind.value, getattr(b, "heading_level", None), b.text) for b in blocks if getattr(b, "table", None) is None]
    assert ("heading", 0, "OUTLOOK") in kinds and ("heading", 2, "Seg") in kinds, kinds
