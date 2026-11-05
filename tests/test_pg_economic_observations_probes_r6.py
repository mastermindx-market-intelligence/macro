"""Opus round-7 red-team probes for PR #7905 (rulings R43–R48), frozen by the seat as the sixth suite (R54). Original synthetic data only."""
from __future__ import annotations

import copy

import pytest

from tests.test_pg_economic_observations_probes_r4 import Q3_FY2026, HEAD, VALS, TITLE, DRV, SUB, row, table
from tests.test_pg_economic_observations_probes_r5 import (
    ws, valid, refused, forge_present, at, _absent_row, TV, PRICE, MIX, REC, DIL, BASE, REC_OK,
)

ORG = "pg_organic_volume_growth_pct"
FX = "pg_fx_contribution_pp"
PRIOR = "pg_prior_diluted_eps"
CORE = "pg_core_eps"
Q3_TITLE = "<h1>Third Quarter Fiscal Year 2026 Results</h1>\n"
V8 = ["1.0%", "2.0%", "(3.0)%", "4.0%", "5.0%", "6.0%", "7.0%", "8.0%"]
SUBHEAD2 = row(["", "with Acquisitions &amp; Divestitures", "Excluding Acquisitions &amp; Divestitures", ""])


def _val(r, m):
    return r[m].get("value")


# ======================= R43 grid =======================
def test_r43a_data_colspan_attribute_is_not_a_colspan():
    hdr = ('<tr><td></td><td data-colspan="2">Volume with Acquisitions &amp; Divestitures</td>'
           + "".join(f"<td>{h}</td>" for h in HEAD[1:]) + "</tr>\n")
    w, t, r, c = ws(TITLE + DRV + SUB + "<table>\n" + hdr + row(["Total P&amp;G", *V8]) + "</table>\n")
    valid(w, t, c)
    assert _val(r, ORG) in (None, 2.0), ("organic volume bound from the FX column via data-colspan", _val(r, ORG))
    assert _val(r, PRICE) in (None, 4.0), ("price bound from the Mix column via data-colspan", _val(r, PRICE))


def test_r43b_colspan_with_leading_space_is_two_columns():
    hdr = '<tr><td></td><td colspan=" 2">Volume</td><td>Price</td></tr>\n'
    w, t, r, c = ws(TITLE + DRV + SUB + "<table>\n" + hdr + SUBHEAD2 + row(["Total P&amp;G", "3.0%", "2.0%", "0.5%"]) + "</table>\n")
    valid(w, t, c)
    assert _val(r, PRICE) in (None, 0.5), ("Price bound from the organic-volume column (colspan=' 2')", _val(r, PRICE))


def test_r43c_colspan_after_long_style_attribute():
    css = "text-align:center;" + "padding-left:1pt;" * 25
    hdr = f'<tr><td></td><td style="{css}" colspan="2">Volume</td><td>Price</td></tr>\n'
    w, t, r, c = ws(TITLE + DRV + SUB + "<table>\n" + hdr + SUBHEAD2 + row(["Total P&amp;G", "3.0%", "2.0%", "0.5%"]) + "</table>\n")
    valid(w, t, c)
    assert _val(r, PRICE) in (None, 0.5), ("Price bound from the organic-volume column (colspan past 400 chars)", _val(r, PRICE))


def test_r43d_rowspan_band_keeps_columns_aligned():
    hdr = ('<tr><td rowspan="2"></td><td colspan="2">Volume</td><td rowspan="2">Price</td></tr>\n'
           '<tr><td>Excluding Acquisitions &amp; Divestitures</td><td>with Acquisitions &amp; Divestitures</td></tr>\n')
    w, t, r, c = ws(TITLE + DRV + SUB + "<table>\n" + hdr + row(["Total P&amp;G", "3.0%", "1.0%", "0.5%"]) + "</table>\n")
    valid(w, t, c)
    assert _val(r, TV) in (None, 1.0), ("total volume bound from the organic column under a rowspan band", _val(r, TV))


def test_r43e_edgar_two_row_band_spanning_year_over_dollar_split():
    body = (TITLE + SUB + "<table>\n"
            '<tr><td></td><td colspan="4">Three Months Ended June 30,</td></tr>\n'
            '<tr><td></td><td colspan="2">2026</td><td colspan="2">2025</td></tr>\n'
            + row(["Diluted Net Earnings per Common Share", "$", "3.07", "$", "2.93"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert (_val(r, DIL), _val(r, PRIOR)) == (3.07, 2.93), ("R43 $/amount split not addressed under a two-row band", r[DIL], r[PRIOR])
    valid(w, t, c)


def test_r43f_spanning_header_split_negative_sign():
    body = (TITLE + SUB + "<table>\n"
            '<tr><td></td><td colspan="3">2026</td><td colspan="3">2025</td></tr>\n'
            + row(["Diluted Net Earnings per Common Share", "$ (", "3.07", ")", "$", "2.93", ""]) + "</table>\n")
    w, t, r, c = ws(body)
    valid(w, t, c)
    assert _val(r, DIL) in (None, -3.07), ("rendered $ (3.07) bound with a positive sign", _val(r, DIL))


def test_r43g_spanning_header_paren_in_amount_cell_is_absent():
    body = (TITLE + SUB + "<table>\n"
            '<tr><td></td><td colspan="3">2026</td><td colspan="3">2025</td></tr>\n'
            + row(["Diluted Net Earnings per Common Share", "$", "(3.07", ")", "$", "2.93", ""]) + "</table>\n")
    w, t, r, c = ws(body)
    assert _val(r, DIL) in (None, -3.07), _val(r, DIL)
    valid(w, t, c)


def test_r43h_mid_table_cumulative_section_row_not_bound_as_quarter():
    body = (Q3_TITLE + DRV + "<table>\n" + row(["", *HEAD]) + row(["Three Months Ended March 31, 2026"] + [""] * 8)
            + row(["Beauty", *VALS]) + row(["Nine Months Ended March 31, 2026"] + [""] * 8)
            + row(["Total P&amp;G", *V8]) + "</table>\n")
    w, t, r, c = ws(body, case=Q3_FY2026)
    assert "value" not in r[TV], ("Total P&G row of a nine-month section bound as the quarter", _val(r, TV))


# ======================= R44 vocabulary =======================
BANDS = [
    ("9_months_digits_q3", "9 Months Ended March 31, 2026", Q3_FY2026),
    ("12_months_digits_q4", "12 Months Ended June 30, 2026", None),
    ("3_months_digits_foreign_q4", "3 Months Ended March 31, 2026", None),
    ("three_months_ending_foreign_q4", "Three Months Ending March 31, 2026", None),
    ("quarter_ended_day_first_foreign_q4", "Quarter Ended 31 March 2026", None),
    ("quarter_ended_no_comma_foreign_q4", "Quarter Ended March 31 2026", None),
    ("three_month_period_foreign_q4", "Three-Month Period Ended March 31, 2026", None),
    ("first_nine_months_q3", "First Nine Months", Q3_FY2026),
    ("ytd_q3", "YTD", Q3_FY2026),
    ("fiscal_2026_q4", "Fiscal 2026", None),
    ("fy26_q4", "FY26", None),
]


@pytest.mark.parametrize("label,case", [(b[1], b[2]) for b in BANDS], ids=[b[0] for b in BANDS])
def test_r44a_band_label_refuses_the_table(label, case):
    pre = row(["", label] + [""] * 7)
    if case is None:
        w, t, r, c = ws(TITLE + DRV + table(pre=pre))
    else:
        w, t, r, c = ws(Q3_TITLE + DRV + table(pre=pre), case=case)
    assert "value" not in r[TV], (f"band {label!r} bound as the admitted quarter", _val(r, TV))


def test_r44b_three_month_period_subheading_is_a_pure_period_heading():
    w, t, r, c = ws(TITLE + DRV + "<h3>Three-Month Period Ended June 30, 2026</h3>\n" + table())
    assert _val(r, TV) == 1.0, ("R44 pure-period heading form replaced the drivers topic", r[TV])
    valid(w, t, c)


def test_r44c_caption_period_label_refuses_the_table():
    body = (Q3_TITLE + DRV + "<table>\n<caption>Nine Months Ended March 31, 2026</caption>\n"
            + row(["", *HEAD]) + row(["Total P&amp;G", *VALS]) + "</table>\n")
    w, t, r, c = ws(body, case=Q3_FY2026)
    assert "value" not in r[TV], ("nine-month table (caption) bound as the quarter", _val(r, TV))


def test_r44d_bold_paragraph_period_label_refuses_the_table():
    body = Q3_TITLE + DRV + "<p><b>Nine Months Ended March 31, 2026</b></p>\n" + table()
    w, t, r, c = ws(body, case=Q3_FY2026)
    assert "value" not in r[TV], ("nine-month table (bold paragraph label) bound as the quarter", _val(r, TV))


# ======================= R45/R46 replay =======================
def test_r46a_validator_refuses_present_volume_the_extractor_refused_as_conflict():
    w, t, r, c = ws(BASE + "<p>Total P&amp;G volume increased 4%.</p>\n")
    assert r[TV]["typed_absence"]["reason"] == "cross_check_conflict", r[TV]
    (src,) = t.values()
    s, e = at(src, "<td>Total P&amp;G</td><td>1.0%", inner="1.0%")
    w2, t2 = forge_present(w, src, TV, s, e, 1.0, "2026-06-30")
    refused(w2, t2, c)


def test_r46b_receipt_on_attribute_copy_of_visible_text_refused():
    data = ('<tr><td>Total P&amp;G</td><td data-note="1.0%">1.0%</td>'
            + "".join(f"<td>{v}</td>" for v in VALS[1:]) + "</tr>\n")
    w, t, r, c = ws(TITLE + DRV + SUB + "<table>\n" + row(["", *HEAD]) + data + "</table>\n")
    assert _val(r, TV) == 1.0, r[TV]
    (src,) = t.values()
    s, e = at(src, 'data-note="1.0%"', inner="1.0%")
    w2, t2 = forge_present(w, src, TV, s, e, 1.0, "2026-06-30")
    refused(w2, t2, c)


def test_r45a_parity_multibyte_entities_colspan_reconciliation():
    body = (TITLE + "<p>Synthetic note — café “quoted” ✓ ünïcode.</p>\n" + DRV + SUB + "<table>\n"
            + row(["", "Volume with Acquisitions &amp; Divestitures", "Volume Excluding Acquisitions &amp; Divestitures",
                   "Foreign&nbsp;Exchange", "Price&#160;", "Mix", "Other", "Net Sales Growth", "Organic Sales Growth"])
            + row(["Total P&amp;G", "1.0%", "1.0%", "(1.0)%", "&#160;0.5%", "0.5%", "1.0%", "3.0%", "1.0%"]) + "</table>\n"
            + "<h2>Three Months Ended June 30, 2026 — EPS</h2>\n<table>\n"
            + '<tr><td></td><td colspan="2">2026</td><td colspan="2">2025</td></tr>\n'
            + row(["Diluted Net Earnings per Common Share", "$", "3.07", "$", "2.93"])
            + row(["Core EPS", "$", "3.11", "$", "2.97"]) + "</table>\n"
            + "<p>Ünïcode ✓ padding — ñ.</p>\n" + REC_OK)
    w, t, r, c = ws(body)
    got = {m: _val(r, m) for m in (TV, FX, PRICE, DIL, PRIOR, CORE)}
    assert got == {TV: 1.0, FX: -1.0, PRICE: 0.5, DIL: 3.07, PRIOR: 2.93, CORE: 3.11}, got
    assert "value" in r[REC], r[REC]
    valid(w, t, c)


# ======================= R47 statements =======================
@pytest.mark.parametrize("sentence", [
    "Total P&amp;G volume declined by 4 percent.",
    "Total P&amp;G's volume increased 4%.",
    "Total P&amp;G volume was down 4%.",
    "Total P&amp;G volumes grew 4%.",
], ids=["declined_by_percent", "possessive", "was_down", "plural_volumes"])
def test_r47a_same_period_statement_conflicts(sentence):
    w, t, r, c = ws(BASE + f"<p>{sentence}</p>\n")
    assert "value" not in r[TV], (sentence, _val(r, TV))


def test_r47b_agreeing_percent_word_is_not_a_conflict():
    w, t, r, c = ws(BASE + "<p>Total P&amp;G volume increased 1 percent!</p>\n")
    assert _val(r, TV) == 1.0, r[TV]
    valid(w, t, c)


# ======================= R48 combined =======================
CH = ["Volume/Mix", "Foreign Exchange", "Other", "Net Sales Growth"]
CV = ["2.0%", "(1.0)%", "1.0%", "3.0%"]


def test_r48a_two_admitted_drivers_tables_one_combined_one_split():
    w, t, r, c = ws(TITLE + DRV + SUB + table(head=CH, vals=CV) + DRV + SUB + table())
    assert _val(r, TV) == 1.0 and _val(r, MIX) == 0.5, (r[TV], r[MIX])
    valid(w, t, c)
    w2 = copy.deepcopy(w)
    for i, f in enumerate(w2["facts"]):
        if isinstance(f, dict) and f.get("metric") == TV:
            w2["facts"][i] = _absent_row(w2, TV, subject=f"{TV} combined volume/mix")
    refused(w2, t, c)


def test_r48b_combined_table_under_out_of_scope_heading_ignored():
    body = (TITLE + DRV + "<h3>Twelve Months Ended June 30, 2026</h3>\n" + table(head=CH, vals=CV)
            + DRV + SUB + table())
    w, t, r, c = ws(body)
    assert _val(r, TV) == 1.0, r[TV]
    valid(w, t, c)
