"""Opus round-9 red-team probes for PR #7905 (rulings R55–R60), frozen by the seat as the eighth suite (R65). Original synthetic data only. q06 adapted order-insensitively by R65."""
from __future__ import annotations

import pytest

import engine.company_intelligence.pg_profile as pgp
from tests.test_pg_economic_observations_probes_r4 import HEAD, VALS, TITLE, DRV, SUB, row, table, wrap
from tests.test_pg_economic_observations_probes_r5 import ws, valid, refused, forge_present, at, TV, PRICE, REC, DIL, BASE, REC_OK
from tests.test_pg_economic_observations_probes_r7 import PRIOR, CORE, DILL, YEARS, SEG_T, BEAUTY, _val, _cells


def _ords(html):
    out = []
    for b in pgp.parse_release_blocks(wrap(html)):
        if getattr(b, "table", None) is not None:
            out.append([[c.row_ordinal for c in r] for r in b.table.rows])
    return out


def _wrong_is_refused(w, t, c, got, wrong):
    if got != wrong:
        pytest.skip(f"extractor did not bind the wrong value (got {got!r})")
    refused(w, t, c)


# ================= R55 =================
Q01 = (TITLE + SUB + "<table>\n<thead><tr><td></td><td rowspan=\"2\">2026</td><td>2025</td></tr></thead>\n<tbody>"
       + row([DILL, "$3.07", "$2.93"]) + "</tbody></table>\n")


def test_q01_rowspan_is_clipped_at_thead_row_group():
    w, t, r, c = ws(Q01)
    assert _val(r, PRIOR) in (None, 2.93) and _val(r, DIL) in (None, 3.07), ("thead rowspan carried into tbody", r[DIL], r[PRIOR])


def test_q01v_validator_on_q01():
    w, t, r, c = ws(Q01)
    _wrong_is_refused(w, t, c, _val(r, PRIOR), 3.07)


Q02 = (TITLE + SUB + "<table>\n" + '<tr><td></td><td colspan="2.0">2026</td><td>2025</td></tr>\n'
       + row([DILL, "$", "3.07", "$2.93"]) + "</table>\n")


def test_q02_colspan_decimal_html_is_two():
    w, t, r, c = ws(Q02)
    assert _val(r, PRIOR) in (None, 2.93) and _val(r, DIL) in (None, 3.07), ("colspan=2.0 read as 1 shifts headers", r[DIL], r[PRIOR])


def test_q02v_validator_on_q02():
    w, t, r, c = ws(Q02)
    _wrong_is_refused(w, t, c, _val(r, PRIOR), 3.07)


def test_q03_span_parse_parity_with_html_integer_rules():
    got = _cells('<table><tr><td colspan="2_0">a</td><td colspan="+2">b</td><td colspan="3px">c</td></tr></table>')
    assert got == [(2, 1), (2, 1), (3, 1)], ("HTML parses a leading digit run; parser returns", got)


def test_q04_leading_zero_whitespace_uppercase_th():
    got = _cells('<table><tr><th COLSPAN="007">a</th><td colspan=" 2 \n">b</td><td ROWSPAN="3">c</td></tr></table>')
    assert got == [(7, 1), (2, 1), (1, 3)], got


def test_q05_bare_td_before_first_tr_is_its_own_row():
    assert _ords("<table><td>a</td><tr><td>b</td></tr><td>c</td></table>") == [[[0], [1], [2]]]


def test_q06_nested_table_ordinals_independent():
    got = _ords("<table><tr><td>x</td></tr><tr><td>w<table><tr><td>i1</td></tr><tr></tr><tr><td>i2</td></tr></table></td></tr><tr><td>y</td></tr></table>")
    # Adapted by seat ruling R65: order-insensitive -- the reviewer's own report records that this assertion
    # expected the two tables in the wrong emission order while the ordinals themselves were correct.
    assert sorted([[[0], [2]], [[0], [1], [2]]]) == sorted(got), got


def test_q07_rowspan_overrunning_table_end_binds():
    body = TITLE + SUB + "<table>\n" + YEARS + f'<tr><td>{DILL}</td><td>$3.07</td><td rowspan="5">$2.93</td></tr>\n</table>\n'
    w, t, r, c = ws(body)
    assert (_val(r, DIL), _val(r, PRIOR)) == (3.07, 2.93), (r[DIL], r[PRIOR])
    valid(w, t, c)


def test_q08_rowspan_label_covering_later_data_row_is_ambiguous():
    body = (TITLE + SUB + "<table>\n" + YEARS + f'<tr><td rowspan="2">{DILL}</td><td>$3.07</td><td>$2.93</td></tr>\n'
            + "<tr><td>$3.10</td><td>$2.95</td></tr>\n</table>\n")
    w, t, r, c = ws(body)
    assert _val(r, DIL) is None, r[DIL]


def test_q09_caption_after_rows_still_governs():
    body = (TITLE + "<h2>Segment Results</h2>\n<table>\n" + YEARS + row(["Beauty", "4.0%", "3.0%"])
            + "<caption>Three Months Ended March 31, 2026</caption></table>\n")
    w, t, r, c = ws(body)
    assert _val(r, BEAUTY) is None, _val(r, BEAUTY)


# ================= R56 =================
DECOR = ["Three Months Ended March 31, 2026 (Unaudited) (In millions)", "Three Months Ended March 31, 2026: (Unaudited)",
         "Three Months Ended March 31, 2026 and 2025", "Three Months Ended March 31, 2026 — Unaudited",
         "Unaudited: Three Months Ended March 31, 2026"]


@pytest.mark.parametrize("label", DECOR, ids=["two_parens", "colon_then_paren", "and_prior_year", "emdash", "prefix"])
def test_q10_decorated_foreign_period_label_paragraph_refuses(label):
    w, t, r, c = ws(TITLE + DRV + f"<p><b>{label}</b></p>\n" + table())
    assert "value" not in r[TV], (label, _val(r, TV))


def test_q10v_validator_on_decorated_label():
    w, t, r, c = ws(TITLE + DRV + f"<p><b>{DECOR[2]}</b></p>\n" + table())
    _wrong_is_refused(w, t, c, _val(r, TV), 1.0)


def test_q11_period_label_inside_div_with_other_text():
    w, t, r, c = ws(TITLE + DRV + "<div>Segment data. <b>Three Months Ended March 31, 2026</b></div>\n" + table())
    assert "value" not in r[TV], _val(r, TV)


FOREIGN_FY = ["Fourth Quarter Fiscal '25 Segment Results", "Fourth Quarter FY-25 Segment Results", "Fourth Quarter FY’25 Segment Results",
              "Fourth Quarter FY 2025 Segment Results", "Fourth Quarter FY2025 Segment Results", "Fourth Quarter Fiscal Year 2025 Segment Results",
              "Fourth Quarter and Fiscal 2025 Segment Results", "Fourth Quarter Segment Results, Fiscal 25"]


@pytest.mark.parametrize("heading", FOREIGN_FY)
def test_q12_fiscal_year_forms_naming_another_year_refuse(heading):
    w, t, r, c = ws(TITLE + f"<h2>{heading}</h2>\n" + SEG_T)
    assert _val(r, BEAUTY) is None, (heading, _val(r, BEAUTY))


def test_q12v_validator_on_fy_dash():
    w, t, r, c = ws(TITLE + f"<h2>{FOREIGN_FY[1]}</h2>\n" + SEG_T)
    _wrong_is_refused(w, t, c, _val(r, BEAUTY), 4.0)


@pytest.mark.parametrize("heading", ["Fourth Quarter FY 2026 Segment Results", "Fourth Quarter FY26 Segment Results"])
def test_q13_fiscal_year_scope_controls_bind(heading):
    w, t, r, c = ws(TITLE + f"<h2>{heading}</h2>\n" + SEG_T)
    assert _val(r, BEAUTY) == 4.0, (heading, r[BEAUTY])


def test_q14_caption_scope_plus_unreadable_marker_refuses():
    body = (TITLE + "<h2>Segment Results</h2>\n<table><caption>Three Months Ended June 30, 2026 and Three Months Ended March 31st, 2026</caption>\n"
            + YEARS + row(["Beauty", "4.0%", "3.0%"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert _val(r, BEAUTY) is None, _val(r, BEAUTY)


def test_q15_heading_scope_plus_unreadable_second_date_refuses():
    w, t, r, c = ws(TITLE + "<h2>Segment Results: Three Months Ended June 30, 2026 vs. Quarter Ended 31/03/2026</h2>\n" + SEG_T)
    assert _val(r, BEAUTY) is None, _val(r, BEAUTY)


def test_q16_reconciliation_under_foreign_fy_dash_heading_refused():
    w, t, r, c = ws(BASE + "<h2>Fourth Quarter FY-25 Core EPS Reconciliation</h2>\n<p>Core EPS excludes a synthetic restructuring item of 0.10.</p>\n")
    assert "value" not in r[REC], r[REC]


# ================= R57 =================
def _sectioned(section_rows):
    return (TITLE + SUB + "<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + section_rows
            + row(["Core EPS", "$12.50", "$11.90"]) + "</table>\n")


Q17 = _sectioned(row(["Twelve Months Ended June 30, 2026", "2026", "2025"]))


def test_q17_mid_table_band_row_opens_annual_section():
    w, t, r, c = ws(Q17)
    assert _val(r, CORE) is None, ("mid-table period band row ignored; twelve-month Core EPS bound", _val(r, CORE))


def test_q17v_validator_on_q17():
    w, t, r, c = ws(Q17)
    _wrong_is_refused(w, t, c, _val(r, CORE), 12.5)


def test_q18_section_label_with_second_text_cell():
    w, t, r, c = ws(_sectioned(row(["Twelve Months Ended June 30, 2026", "", "(unaudited)"])))
    assert _val(r, CORE) is None, _val(r, CORE)


def test_q19_colspan_section_label_beside_carried_text_label():
    body = (TITLE + SUB + "<table>\n" + YEARS + '<tr><td rowspan="2">Net Sales</td><td>$20,000</td><td>$19,000</td></tr>\n'
            + '<tr><td colspan="2">Twelve Months Ended June 30, 2026</td></tr>\n' + row(["Core EPS", "$12.50", "$11.90"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert _val(r, CORE) is None, _val(r, CORE)


def test_q20_colspan_section_label_beside_carried_empty_cell_control():
    body = (TITLE + SUB + "<table>\n" + YEARS + f'<tr><td>{DILL}</td><td>$3.07</td><td rowspan="2"></td></tr>\n'
            + '<tr><td colspan="2">Twelve Months Ended June 30, 2026</td></tr>\n' + row(["Core EPS", "$12.50", "$11.90"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert _val(r, CORE) is None, _val(r, CORE)


def test_q21_dollar_only_row_does_not_reset_section():
    w, t, r, c = ws(_sectioned(row(["Twelve Months Ended June 30, 2026", "", ""]) + row(["", "$", ""])))
    assert _val(r, CORE) is None, _val(r, CORE)


# ================= R58 =================
Q22 = (TITLE + SUB + "<table>\n" + '<tr><td></td><td colspan="2">Three Months Ended June 30, 2026</td><td>Three Months Ended June 30, 2025</td></tr>\n'
       + row(["", "As Reported", "Restated", ""]) + row([DILL, "", "$3.19", "$2.93"]) + "</table>\n")


def test_q22_spanning_top_over_two_text_subcells_does_not_share_key():
    w, t, r, c = ws(Q22)
    assert _val(r, DIL) is None, ("restated sub-column bound as reported diluted EPS", _val(r, DIL))


def test_q22v_validator_on_q22():
    w, t, r, c = ws(Q22)
    _wrong_is_refused(w, t, c, _val(r, DIL), 3.19)


def test_q23_restated_year_subcell_control():
    body = (TITLE + SUB + "<table>\n" + '<tr><td></td><td colspan="3">Three Months Ended June 30,</td></tr>\n'
            + row(["", "2026", "2026 Restated", "2025"]) + row([DILL, "", "$3.19", "$2.93"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert _val(r, DIL) is None, _val(r, DIL)


def test_q24_forged_receipt_on_spanning_literal_refused():
    body = TITLE + SUB + "<table>\n" + YEARS + f'<tr><td>{DILL}</td><td colspan="2">$3.07</td></tr>\n</table>\n'
    w, t, r, c = ws(body)
    assert _val(r, DIL) is None
    (src,) = t.values()
    s, e = at(src, '<td colspan="2">$3.07', inner="$3.07")
    w2, t2 = forge_present(w, src, DIL, s, e, 3.07, "2026-06-30")
    refused(w2, t2, c)


def test_q25_identical_origin_spanning_literal_extractor_validator_agree():
    body = (TITLE + SUB + "<table>\n" + '<tr><td></td><td colspan="2">2026</td><td>2025</td></tr>\n'
            + f'<tr><td>{DILL}</td><td colspan="2">$3.07</td><td>$2.93</td></tr>\n</table>\n')
    w, t, r, c = ws(body)
    if _val(r, DIL) == 3.07:
        valid(w, t, c)
        return
    assert _val(r, DIL) is None
    (src,) = t.values()
    s, e = at(src, '<td colspan="2">$3.07', inner="$3.07")
    w2, t2 = forge_present(w, src, DIL, s, e, 3.07, "2026-06-30")
    refused(w2, t2, c)


# ================= R59 =================
def test_q26_outlook_section_with_non_forward_subtopic():
    w, t, r, c = ws(TITLE + "<h2>Outlook</h2>\n<h3>Segment Results</h3>\n" + SEG_T)
    assert _val(r, BEAUTY) is None, ("table under Outlook > Segment Results bound", _val(r, BEAUTY))


def test_q27_forward_looking_caption():
    body = TITLE + "<h2>Segment Results</h2>\n<table><caption>Segment Outlook</caption>\n" + YEARS + row(["Beauty", "4.0%", "3.0%"]) + "</table>\n"
    w, t, r, c = ws(body)
    assert _val(r, BEAUTY) is None, _val(r, BEAUTY)


@pytest.mark.parametrize("heading", ["Targeting Segment Results", "Projecting Segment Results", "Anticipated Segment Results", "Projected Segment Results"])
def test_q28_forward_looking_inflections_beyond_list(heading):
    w, t, r, c = ws(TITLE + f"<h2>{heading}</h2>\n" + SEG_T)
    assert _val(r, BEAUTY) is None, (heading, _val(r, BEAUTY))


def test_q29_title_only_forward_term_availability():
    body = "<h1>Fourth Quarter Fiscal Year 2026 Results and Outlook</h1>\n" + SUB + "<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + "</table>\n"
    w, t, r, c = ws(body)
    assert _val(r, DIL) == 3.07, ("title-only forward term refuses an actual-results table", r[DIL])


def test_q30_outlook_reconciliation_paragraph():
    w, t, r, c = ws(BASE + "<h2>Core EPS Outlook Reconciliation</h2>\n<p>Core EPS excludes a synthetic restructuring item of 0.10.</p>\n")
    assert "value" not in r[REC], r[REC]


def test_q31_expectations_paragraph_is_not_a_heading_control():
    w, t, r, c = ws(TITLE + "<h2>Segment Results</h2>\n<p>Expectations are discussed below.</p>\n" + SEG_T)
    assert _val(r, BEAUTY) == 4.0, r[BEAUTY]
