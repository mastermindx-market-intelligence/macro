"""Opus round-8 red-team probes for PR #7905 (rulings R49–R54), frozen by the seat as the seventh suite (R60). Original synthetic data only. p34 struck by R60."""
from __future__ import annotations

import pytest

import engine.company_intelligence.pg_profile as pgp
from tests.test_pg_economic_observations_probes_r4 import HEAD, VALS, TITLE, DRV, SUB, row, table, wrap
from tests.test_pg_economic_observations_probes_r5 import ws, valid, refused, forge_present, at, TV, PRICE, REC, DIL, BASE, REC_OK

PRIOR = "pg_prior_diluted_eps"
CORE = "pg_core_eps"
ORG = "pg_organic_volume_growth_pct"
FX = "pg_fx_contribution_pp"
BEAUTY = "pg_beauty_organic_sales_growth_pct"
V8 = ["1.0%", "2.0%", "(3.0)%", "4.0%", "5.0%", "6.0%", "7.0%", "8.0%"]
DILL = "Diluted Net Earnings per Common Share"
YEARS = row(["", "2026", "2025"])
SEG_T = "<table>\n" + YEARS + row(["Beauty", "4.0%", "3.0%"]) + "</table>\n"


def _val(r, m):
    return r[m].get("value")


def _cells(html):
    blocks = pgp.parse_release_blocks(wrap(html))
    t = next(b for b in blocks if getattr(b, "table", None) is not None)
    return [(c.colspan, c.rowspan) for c in t.table.rows[0]]


# ============ R49 grid ============
def test_p01_empty_tr_consumed_by_rowspan_shifts_prior_eps():
    body = (TITLE + SUB + "<table>\n" + row(["", "Three Months Ended June 30, 2026", "Three Months Ended June 30, 2025"])
            + '<tr><td>Net Earnings</td><td rowspan="2">$5,000</td><td>$4,800</td></tr>\n<tr></tr>\n'
            + row([DILL, "$3.07", "$2.93"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert _val(r, PRIOR) in (None, 2.93), ("prior EPS bound to the current-quarter literal after an empty <tr>", r[PRIOR])
    assert _val(r, DIL) in (None, 3.07), r[DIL]


def test_p02_duplicate_colspan_attribute_first_wins():
    hdr = ('<tr><td></td><td colspan="1" colspan="2">' + HEAD[0] + "</td>" + "".join(f"<td>{h}</td>" for h in HEAD[1:]) + "</tr>\n")
    w, t, r, c = ws(TITLE + DRV + SUB + "<table>\n" + hdr + row(["Total P&amp;G", *V8]) + "</table>\n")
    assert _val(r, ORG) in (None, 2.0), ("organic volume read under the last duplicate colspan", _val(r, ORG))


def test_p03_non_ascii_or_underscore_colspan_is_garbage():
    got = _cells('<table><tr><td colspan="２">a</td><td colspan="1_0">b</td><td>c</td></tr></table>')
    assert got == [(1, 1), (1, 1), (1, 1)], got


def test_p04_colspan_bounds():
    got = _cells('<table><tr><td colspan="64">a</td><td colspan="65">b</td><td colspan="0">c</td><td rowspan="-2">d</td></tr></table>')
    assert got == [(64, 1), (1, 1), (1, 1), (1, 1)], got


def test_p05_stacked_header_only_top_row_spans_dollar_split():
    body = (TITLE + SUB + "<table>\n"
            '<tr><td></td><td colspan="2">Three Months Ended June 30, 2026</td><td colspan="2">Three Months Ended June 30, 2025</td></tr>\n'
            + row(["", "", "(unaudited)", "", "(unaudited)"]) + row([DILL, "$", "3.07", "$", "2.93"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert (_val(r, DIL), _val(r, PRIOR)) == (3.07, 2.93), ("single-literal rule not applied to a partly spanning stack", r[DIL], r[PRIOR])


def test_p06_colspan_plus_rowspan_same_band_cell():
    hdr0 = ('<tr><td></td>' + "".join(f'<td rowspan="2">{h}</td>' for h in HEAD[:2])
            + '<td colspan="2" rowspan="2">Foreign Exchange</td>' + "".join(f'<td rowspan="2">{h}</td>' for h in HEAD[3:]) + "</tr>\n")
    body = TITLE + DRV + SUB + "<table>\n" + hdr0 + "<tr><td></td></tr>\n" + row(["Total P&amp;G", "1.0%", "1.0%", "", "(1.0)%", "0.5%", "0.5%", "1.0%", "3.0%", "1.0%"]) + "</table>\n"
    w, t, r, c = ws(body)
    assert (_val(r, TV), _val(r, FX), _val(r, PRICE)) == (1.0, -1.0, 0.5), (r[TV], r[FX], r[PRICE])
    valid(w, t, c)


def test_p06b_fully_covered_band_row_is_an_empty_tr():
    hdr0 = ('<tr><td rowspan="2"></td>' + "".join(f'<td rowspan="2">{h}</td>' for h in HEAD) + "</tr>\n<tr></tr>\n")
    w, t, r, c = ws(TITLE + DRV + SUB + "<table>\n" + hdr0 + row(["Total P&amp;G", *VALS]) + "</table>\n")
    assert _val(r, TV) == 1.0, ("HTML-aligned drivers table unread after a fully covered band row", r[TV])


def test_p07_rowspan_header_crossing_into_data_row():
    body = (TITLE + SUB + "<table>\n" + '<tr><td></td><td>Three Months Ended June 30, 2026</td><td rowspan="2">Three Months Ended June 30, 2025</td></tr>\n'
            + f"<tr><td>{DILL}</td><td>$3.07</td></tr>\n</table>\n")
    w, t, r, c = ws(body)
    assert _val(r, DIL) == 3.07 and _val(r, PRIOR) is None, (r[DIL], r[PRIOR])
    valid(w, t, c)


def test_p08_rowspan_into_label_column():
    body = (TITLE + SUB + "<table>\n" + f'<tr><td rowspan="2">{DILL}</td><td>2026</td><td>2025</td></tr>\n'
            + "<tr><td>$3.07</td><td>$2.93</td></tr>\n</table>\n")
    w, t, r, c = ws(body)
    assert (_val(r, DIL), _val(r, PRIOR)) == (3.07, 2.93), (r[DIL], r[PRIOR])
    valid(w, t, c)


def test_p09_gap_one_literal_spanning_current_and_prior_columns():
    body = TITLE + SUB + "<table>\n" + YEARS + f'<tr><td>{DILL}</td><td colspan="2">$3.07</td></tr>\n</table>\n'
    w, t, r, c = ws(body)
    assert _val(r, DIL) is None, ("one literal spanning both period columns bound as the current quarter", r[DIL])


def test_p10_sign_fragment_in_spanned_cell_absent():
    body = (TITLE + SUB + "<table>\n" + '<tr><td></td><td colspan="2">2026</td><td colspan="2">2025</td></tr>\n'
            + row([DILL, "(", "$3.07", "", "$2.93"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert _val(r, DIL) is None, r[DIL]


def test_p11_bare_integer_plus_literal_under_one_spanning_header_absent():
    body = (TITLE + SUB + "<table>\n" + '<tr><td></td><td colspan="2">2026</td><td colspan="2">2025</td></tr>\n'
            + row([DILL, "2026", "$3.07", "", "$2.93"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert _val(r, DIL) is None, r[DIL]


def test_p11b_nested_table_parity_document_only():
    body = (TITLE + SUB + "<table>\n" + YEARS + f"<tr><td>{DILL}</td><td><table><tr><td>$3.07</td></tr></table></td><td>$2.93</td></tr>\n</table>\n")
    w, t, r, c = ws(body)
    valid(w, t, c)


# ============ R50 vocabulary / fail-closed ============
def test_p12_caption_with_unresolved_period_marker_is_not_fail_closed():
    body = TITLE + "<h2>Segment Results</h2>\n<table><caption>Three Months Ended March 31st, 2026</caption>\n" + YEARS + row(["Beauty", "4.0%", "3.0%"]) + "</table>\n"
    w, t, r, c = ws(body)
    assert _val(r, BEAUTY) is None, ("caption naming an unreadable quarter did not refuse the table", _val(r, BEAUTY))


def test_p12c_same_label_as_value_column_band_is_refused_control():
    body = (TITLE + "<h2>Segment Results</h2>\n<table>\n" + '<tr><td></td><td colspan="2">Three Months Ended March 31st, 2026</td></tr>\n'
            + YEARS + row(["Beauty", "4.0%", "3.0%"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert _val(r, BEAUTY) is None, _val(r, BEAUTY)


def test_p13_label_column_band_cell_with_unresolved_marker():
    body = TITLE + "<h2>Segment Results</h2>\n<table>\n" + row(["Quarter ended 31/03/2026", "2026", "2025"]) + row(["Beauty", "4.0%", "3.0%"]) + "</table>\n"
    w, t, r, c = ws(body)
    assert _val(r, BEAUTY) is None, ("label-column band cell naming an unreadable quarter did not refuse", _val(r, BEAUTY))


def test_p14_gap_heading_with_unresolved_period_marker():
    body = TITLE + "<h2>Segment Results for the Three Months Ended March 31st, 2026</h2>\n" + SEG_T
    w, t, r, c = ws(body)
    assert _val(r, BEAUTY) is None, ("keyword heading naming an unreadable quarter admitted the table", _val(r, BEAUTY))


def test_p15_value_column_ordinal_date_is_unknown():
    body = TITLE + SUB + "<table>\n" + row(["", "Three Months Ended June 30th, 2026", "Three Months Ended June 30th, 2025"]) + row([DILL, "$3.07", "$2.93"]) + "</table>\n"
    w, t, r, c = ws(body)
    assert _val(r, DIL) is None, r[DIL]


def test_p16_digit_months_abbrev_month_with_period_spanning_years():
    body = (TITLE + SUB + "<table>\n" + '<tr><td></td><td colspan="2">3 Months Ended Jun. 30,</td></tr>\n' + YEARS + row([DILL, "$3.07", "$2.93"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert (_val(r, DIL), _val(r, PRIOR)) == (3.07, 2.93), (r[DIL], r[PRIOR])
    valid(w, t, c)


def test_p17_reverse_order_ending_pure_paragraph_positive():
    body = TITLE + "<p><b>Three Months Ending 30 June 2026</b></p>\n<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + "</table>\n"
    w, t, r, c = ws(body)
    assert _val(r, DIL) == 3.07, r[DIL]
    valid(w, t, c)


@pytest.mark.parametrize("label", ["Three Months Ended March 31, 2026 (Unaudited)", "Three Months Ended March 31, 2026:",
                                   "For the Three Months Ended March 31, 2026"], ids=["unaudited", "colon", "for_the"])
def test_p18_gap_period_label_paragraph_with_decoration(label):
    w, t, r, c = ws(TITLE + DRV + f"<p><b>{label}</b></p>\n" + table())
    assert "value" not in r[TV], (label, _val(r, TV))


def test_p19_unknown_month_in_value_column_is_foreign():
    body = TITLE + SUB + "<table>\n" + row(["", "Three Months Ended Juin 30, 2026", "Three Months Ended Juin 30, 2025"]) + row([DILL, "$3.07", "$2.93"]) + "</table>\n"
    w, t, r, c = ws(body)
    assert _val(r, DIL) is None, r[DIL]


def test_p20_scope_caption_with_annual_column_refuses():
    body = (TITLE + SUB + "<table><caption>Three Months Ended June 30, 2026</caption>\n" + row(["", "2026", "Twelve Months Ended June 30, 2026"])
            + row([DILL, "$3.07", "$12.10"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert _val(r, DIL) is None, r[DIL]


# ============ R51 row sections ============
def _sectioned(section_row):
    return (TITLE + SUB + "<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + section_row
            + row(["Core EPS", "$12.50", "$11.90"]) + "</table>\n")


def test_p21_colspan_section_label_opens_annual_section():
    w, t, r, c = ws(_sectioned('<tr><td colspan="3">Twelve Months Ended June 30, 2026</td></tr>\n'))
    assert _val(r, CORE) is None, ("twelve-month Core EPS bound under a colspan section label", _val(r, CORE))


def test_p21c_label_only_section_control():
    w, t, r, c = ws(_sectioned(row(["Twelve Months Ended June 30, 2026", "", ""])))
    assert _val(r, CORE) is None, _val(r, CORE)
    assert _val(r, DIL) == 3.07, r[DIL]


def test_p22_gap_section_label_in_second_column():
    w, t, r, c = ws(_sectioned(row(["", "Twelve Months Ended June 30, 2026", ""])))
    assert _val(r, CORE) is None, ("twelve-month Core EPS bound under a second-column section label", _val(r, CORE))


def test_p23_scope_section_after_annual_section():
    body = (TITLE + SUB + "<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + row(["Twelve Months Ended June 30, 2026", "", ""])
            + row([DILL, "$12.10", "$11.50"]) + row(["Three Months Ended June 30, 2026", "", ""]) + row(["Core EPS", "$3.11", "$2.97"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert (_val(r, DIL), _val(r, CORE)) == (3.07, 3.11), (r[DIL], r[CORE])
    valid(w, t, c)


# ============ R52 validator ============
def test_p24_forged_receipt_on_excluded_section_cell_refused():
    body = (TITLE + DRV + SUB + "<table>\n" + row(["", *HEAD]) + row(["Beauty", *VALS]) + row(["Twelve Months Ended June 30, 2026"] + [""] * 8)
            + row(["Total P&amp;G", *V8]) + "</table>\n")
    w, t, r, c = ws(body)
    assert "value" not in r[TV], r[TV]
    (src,) = t.values()
    s, e = at(src, "<td>Total P&amp;G</td><td>1.0%", inner="1.0%")
    w2, t2 = forge_present(w, src, TV, s, e, 1.0, "2026-06-30")
    refused(w2, t2, c)


def test_p25_forged_receipt_on_comment_copy_inside_cell_refused():
    data = "<tr><td>Total P&amp;G</td><td><!-- 1.0% -->1.0%</td>" + "".join(f"<td>{v}</td>" for v in VALS[1:]) + "</tr>\n"
    w, t, r, c = ws(TITLE + DRV + SUB + "<table>\n" + row(["", *HEAD]) + data + "</table>\n")
    (src,) = t.values()
    s, e = at(src, "<!-- 1.0% -->", inner="1.0%")
    w2, t2 = forge_present(w, src, TV, s, e, 1.0, "2026-06-30")
    refused(w2, t2, c)


PARA = "Core EPS excludes a synthetic restructuring item of 0.10."


def test_p26_forged_paragraph_receipt_on_comment_copy_refused():
    body = BASE + f"<h2>Core EPS Reconciliation</h2>\n<p><!-- {PARA} -->{PARA}</p>\n"
    w, t, r, c = ws(body)
    (src,) = t.values()
    s, e = at(src, f"<!-- {PARA}", inner=PARA)
    w2, t2 = forge_present(w, src, REC, s, e, PARA, "2026-06-30")
    refused(w2, t2, c)


def test_p27_multibyte_entities_before_paragraph_parity():
    body = BASE + "<p>Préambule — &eacute;&#8212;&nbsp;✓ \U0001F600 synthetic.</p>\n" + REC_OK
    w, t, r, c = ws(body)
    assert "value" in r[REC], r[REC]
    valid(w, t, c)


def test_p28_total_volume_agrees_one_statement_conflicts_another():
    w, t, r, c = ws(BASE + "<p>Total P&amp;G volume increased 1%.</p>\n<p>Total P&amp;G volume increased 4%.</p>\n")
    assert "value" not in r[TV], r[TV]
    (src,) = t.values()
    s, e = at(src, "<td>Total P&amp;G</td><td>1.0%", inner="1.0%")
    w2, t2 = forge_present(w, src, TV, s, e, 1.0, "2026-06-30")
    refused(w2, t2, c)


# ============ R53 statements ============
@pytest.mark.parametrize("sentence", ["Total P&amp;G volumes decreased 4%.", "Total P&amp;G unit volumes were down 4 percent."])
def test_p29_plural_volumes_conflict(sentence):
    w, t, r, c = ws(BASE + f"<p>{sentence}</p>\n")
    assert "value" not in r[TV], (sentence, _val(r, TV))


# ============ R54 ============
def test_p30_overlong_duplicate_reconciliation_paragraph_absent():
    long = "Core EPS " + "is a synthetic long disclosure clause " * 10 + "."
    w, t, r, c = ws(BASE + REC_OK + f"<p>{long}</p>\n")
    assert "value" not in r[REC], r[REC]


def test_p31_outlook_topic_with_pure_period_sublabel_admits_table():
    body = TITLE + "<h2>Outlook</h2>\n<p>Three Months Ended June 30, 2026</p>\n<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + "</table>\n"
    w, t, r, c = ws(body)
    assert _val(r, DIL) is None, ("an Outlook-governed table admitted through its period sub-label", r[DIL])


@pytest.mark.parametrize("heading", ["Segment Outlooks", "Estimated Segment Results", "Forecasted Segment Results", "Targeted Segment Results"])
def test_p32_forward_looking_inflections(heading):
    w, t, r, c = ws(TITLE + f"<h2>{heading}</h2>\n" + SEG_T)
    assert _val(r, BEAUTY) is None, (heading, _val(r, BEAUTY))


def test_p33_outlook_subheading_between_topic_and_table_refuses():
    w, t, r, c = ws(TITLE + "<h2>Segment Results</h2>\n<h3>Outlook</h3>\n" + SEG_T)
    assert _val(r, BEAUTY) is None, _val(r, BEAUTY)


# p34 (gap g5: "Target" as a proper noun) STRUCK by seat ruling R60 -- the forward-looking exclusion is kept
# over-broad on purpose; its cost is a missed bind, never a wrong one.


def test_p35_segment_control_binds():
    w, t, r, c = ws(TITLE + "<h2>Segment Results</h2>\n" + SEG_T)
    assert _val(r, BEAUTY) == 4.0, r[BEAUTY]
    valid(w, t, c)
