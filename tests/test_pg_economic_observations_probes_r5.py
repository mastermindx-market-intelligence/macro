"""Opus round-6 red-team probes for PR #7905 (rulings R27–R42), frozen by the seat as the fifth suite (R48). Original synthetic data only."""
from __future__ import annotations

import copy
import hashlib

import pytest

from engine.company_intelligence.documents import TypedAbsence
from engine.company_intelligence.economic_observations import EconomicObservationError, validate_selected_facts
import engine.company_intelligence.pg_profile as pgp
from engine.earnings_release.binding import bind_release_document
from engine.earnings_release.receipts import receipt_for_char_span
from tests.earnings_economic_fixtures import FISCAL_SCOPE, pg_source_texts, pg_workspace_case
from tests.test_pg_economic_observations_probes import CIK, Q4_FY2026, _literal_workspace, _pg_rows
from tests.test_pg_economic_observations_probes_r4 import Q3_FY2026, HEAD, VALS, TITLE, DRV, SUB, row, table, wrap

TV = "pg_total_volume_growth_pct"
PRICE = "pg_price_contribution_pp"
MIX = "pg_mix_contribution_pp"
REC = "pg_core_reconciliation_context"
DIL = "pg_diluted_eps"
BASE = TITLE + DRV + SUB + table()
REC_OK = "<h2>Core EPS Reconciliation</h2>\n<p>Core EPS excludes a synthetic restructuring item of 0.10.</p>\n"


def ws(body, case=Q4_FY2026, slug="r6"):
    w, t = _literal_workspace(wrap(body), case, slug)
    return w, t, _pg_rows(w), case


def valid(w, t, case):
    validate_selected_facts(w, source_texts=t, fiscal_scope=case.scope)


def refused(w, t, case):
    with pytest.raises(EconomicObservationError):
        validate_selected_facts(w, source_texts=t, fiscal_scope=case.scope)


def _doc(w):
    return next(s["document_id"] for s in w["sources"] if s.get("kind") == "issuer_release")


def _absent_row(w, metric, subject=None):
    ev, d = w["event_id"], next(x for x in pgp.PG_DEFINITIONS if x.metric == metric)
    ident = "|".join((ev, metric, metric, d.basis))
    return {"schema": "event_fact.v1", "fact_id": "fact_" + hashlib.sha256(ident.encode()).hexdigest()[:16],
            "event_id": ev, "metric": metric,
            "typed_absence": TypedAbsence(reason="no_span_addressable_evidence", subject=subject or metric,
                                          detail="forged", event_id=ev, document_id=_doc(w)).to_payload()}


def forge_present(w, src, metric, char_start, char_end, value, period):
    """Every PG row becomes a plain absence except ``metric``, which is re-minted against ``src``."""
    w = copy.deepcopy(w)
    doc = _doc(w)
    bound = bind_release_document(cik=CIK, accession=Q4_FY2026.accession, body=src, form="8-K",
                                  filing_date="2026-07-29", report_date="2026-07-29", content_type="text/html")
    rec = receipt_for_char_span(source=src, source_sha256=bound.revision.source_sha256,
                                char_start=char_start, char_end=char_end)
    d = next(x for x in pgp.PG_DEFINITIONS if x.metric == metric)
    ident = "|".join((w["event_id"], metric, period, d.basis))
    for i, f in enumerate(w["facts"]):
        if isinstance(f, dict) and str(f.get("metric", "")).startswith("pg_"):
            if f["metric"] == metric:
                w["facts"][i] = {"schema": "event_fact.v1", "fact_id": "fact_" + hashlib.sha256(ident.encode()).hexdigest()[:16],
                                 "event_id": w["event_id"], "metric": metric, "value": value, "unit": d.unit,
                                 "period": period, "basis": d.basis, "source_span": pgp._span(doc, bound, rec)}
            else:
                w["facts"][i] = _absent_row(w, f["metric"])
    return w, {doc: src}


def at(src, needle, occurrence=0, inner=None):
    idx = -1
    for _ in range(occurrence + 1):
        idx = src.index(needle, idx + 1)
    if inner:
        idx += needle.index(inner)
        return idx, idx + len(inner)
    return idx, idx + len(needle)


# ======================= R35 document identity =======================
def test_r35a_only_band_signals_foreign_quarter_refused():
    pre = row(["", "Three Months Ended March 31, 2026"] + [""] * 7)
    w, t, r, c = ws("<h2>Net Sales Change Drivers</h2>\n" + table(pre=pre))
    assert "value" not in r[TV]


def test_r35b_matching_drivers_heading_plus_foreign_quarter_title_refused():
    w, t, r, c = ws("<h1>Third Quarter Fiscal Year 2026 Results</h1>\n" + DRV + table())
    assert "value" not in r[TV], r[TV]


def test_r35c_foreign_heading_after_tables_does_not_widen():
    w, t, r, c = ws(BASE + "<h2>Third Quarter Fiscal Year 2026 Recap</h2>\n<p>Synthetic recap.</p>\n")
    assert r[TV].get("value") == 1.0
    valid(w, t, c)


def test_r35d_reconciliation_under_twelve_month_heading_binds():
    body = BASE + "<h2>Twelve Months Ended June 30, 2026</h2>\n" + REC_OK
    w, t, r, c = ws(body)
    assert "value" in r[REC], r[REC]
    valid(w, t, c)


def test_r35e_reconciliation_under_foreign_quarter_heading_absent():
    body = BASE + "<h2>Third Quarter Fiscal Year 2026</h2>\n" + REC_OK
    w, t, r, c = ws(body)
    assert "value" not in r[REC]


def test_r35f_validator_refuses_forged_reconciliation_under_foreign_quarter_heading():
    body = BASE + "<h2>Third Quarter Fiscal Year 2026</h2>\n" + REC_OK
    w, t, r, c = ws(body)
    (src,) = t.values()
    text = "Core EPS excludes a synthetic restructuring item of 0.10."
    s, e = at(src, text)
    w2, t2 = forge_present(w, src, REC, s, e, text, "2026-06-30")
    refused(w2, t2, c)


def test_r35g_validator_refuses_forged_reconciliation_from_hidden_element():
    hidden = '<div hidden><p>Core EPS in this hidden note is a forged 9.99 statement.</p></div>\n'
    w, t, r, c = ws(BASE + hidden)
    (src,) = t.values()
    text = "Core EPS in this hidden note is a forged 9.99 statement."
    s, e = at(src, text)
    w2, t2 = forge_present(w, src, REC, s, e, text, "2026-06-30")
    refused(w2, t2, c)


def test_r35h_validator_accepts_extractor_reconciliation_after_multibyte_text():
    cjk = "<p>" + "全球品牌" * 80 + "</p>\n"
    w, t, r, c = ws(cjk + BASE + REC_OK)
    assert "value" in r[REC], r[REC]
    valid(w, t, c)


def test_r35i_validator_accepts_extractor_reconciliation_longer_than_240():
    long = "<h2>Core EPS Reconciliation</h2>\n<p>Core EPS excludes " + ", ".join(f"synthetic item {i}" for i in range(30)) + ".</p>\n"
    w, t, r, c = ws(BASE + long)
    if "value" in r[REC]:
        valid(w, t, c)


def test_r35j_document_verdict_parity_extractor_vs_validator_blocks():
    src = wrap("<h1>Third Quarter Fiscal Year 2026 Results</h1>\r\n<p>&amp; café &#8212;</p>" + BASE)
    bound = bind_release_document(cik=CIK, accession=Q4_FY2026.accession, body=src, content_type="text/html")
    ident = (2026, 4, Q4_FY2026.period_end)
    assert pgp.document_period_verdict(bound.document.blocks, ident) == pgp.document_period_verdict(pgp.parse_release_blocks(src), ident)
    key = lambda bs: [(b.kind.value, b.text, b.source_span.char_start, b.source_span.char_end) for b in bs]
    assert key(bound.document.blocks) == key(pgp.parse_release_blocks(src))


def test_r35k_year_to_date_band_is_not_the_admitted_quarter_q3_scope():
    pre = row(["", "Nine Months Ended March 31, 2026"] + [""] * 7)
    body = "<h1>Third Quarter Fiscal Year 2026 Results</h1>\n" + DRV + table(pre=pre)
    w, t, r, c = ws(body, case=Q3_FY2026)
    assert "value" not in r[TV], ("nine-month drivers bound as the quarter", r[TV].get("value"))


def test_r35l_quarter_ended_foreign_date_band_refused_q4_scope():
    pre = row(["", "Quarter Ended March 31, 2026"] + [""] * 7)
    w, t, r, c = ws(TITLE + DRV + table(pre=pre))
    assert "value" not in r[TV], ("March quarter drivers bound as June quarter", r[TV].get("value"))


# ======================= R37 header band =======================
def test_r37a_blank_row_before_first_literal_row():
    pre_rows = row(["", *HEAD]) + row(["Beauty"] + [""] * 8)
    body = TITLE + DRV + SUB + "<table>\n" + pre_rows + row(["Total P&amp;G", *VALS]) + "</table>\n"
    w, t, r, c = ws(body)
    assert r[TV].get("value") == 1.0, r[TV]
    valid(w, t, c)


def test_r37b_dash_row_before_total_is_data_not_band():
    body = TITLE + DRV + SUB + "<table>\n" + row(["", *HEAD]) + row(["Beauty"] + ["—"] * 8) + row(["Total P&amp;G", *VALS]) + "</table>\n"
    w, t, r, c = ws(body)
    assert r[TV].get("value") == 1.0, r[TV]


def test_r37c_year_like_band_row_then_metric_headers():
    pre = row(["", "2026"] + [""] * 7)
    w, t, r, c = ws(TITLE + DRV + SUB + table(pre=pre))
    assert r[TV].get("value") == 1.0, r[TV]
    valid(w, t, c)


def test_r37d_band_naming_quarter_and_twelve_months_refused_whole():
    pre = row(["", "Three Months Ended June 30, 2026", "Twelve Months Ended June 30, 2026"] + [""] * 6)
    w, t, r, c = ws(TITLE + DRV + table(pre=pre))
    assert "value" not in r[TV]


def test_r37e_split_fiscal_year_label_in_two_band_rows_refused():
    pre = row(["", "Fiscal Year"] + [""] * 7) + row(["", "2026"] + [""] * 7)
    w, t, r, c = ws(TITLE + DRV + SUB + table(pre=pre))
    assert "value" not in r[TV], ("annual band split over two rows binds", r[TV].get("value"))


def test_r37f_split_foreign_three_month_label_in_two_band_rows_refused():
    pre = row(["", "Three Months Ended"] + [""] * 7) + row(["", "March 31, 2026"] + [""] * 7)
    w, t, r, c = ws(TITLE + DRV + table(pre=pre))
    assert "value" not in r[TV], ("March-quarter band split over two rows binds", r[TV].get("value"))


def test_r37g_eps_split_foreign_date_with_bare_year_row():
    body = (TITLE + "<table>\n" + row(["", "Three Months Ended", "Three Months Ended"]) +
            row(["", "March 31, 2026", "March 31, 2025"]) + row(["", "2026", "2025"]) +
            row(["Diluted Net Earnings per Common Share", "$2.11", "$2.01"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert "value" not in r[DIL], ("March-quarter EPS bound as June quarter", r[DIL].get("value"))


def test_r37h_colspan_group_header_does_not_shift_columns():
    body = (TITLE + DRV + SUB + "<table>\n" +
            '<tr><td></td><td colspan="2">Volume</td><td>Price</td></tr>\n' +
            row(["", "with Acquisitions &amp; Divestitures", "Excluding Acquisitions &amp; Divestitures", ""]) +
            row(["Total P&amp;G", "3.0%", "2.0%", "0.5%"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert r[PRICE].get("value") != 2.0, "Price bound from the organic-volume column"


def test_r37i_colspan_year_headers_over_currency_cells():
    body = (TITLE + SUB + "<table>\n" + '<tr><td></td><td colspan="2">2026</td><td colspan="2">2025</td></tr>\n' +
            row(["Diluted Net Earnings per Common Share", "$", "3.07", "$", "2.93"]) + "</table>\n")
    w, t, r, c = ws(body)
    assert _pg_rows(w)["pg_prior_diluted_eps"].get("value") != 3.07, "current EPS bound as prior-year EPS"


# ======================= R42 uniqueness =======================
def test_r42a_second_addressable_table_is_ambiguity():
    w, t, r, c = ws(BASE + DRV + SUB + table(vals=["2.0%", *VALS[1:]]))
    assert "value" not in r[TV]


def test_r42b_identical_heading_text_twice_is_ambiguity():
    w, t, r, c = ws(BASE + DRV + SUB + table())
    assert "value" not in r[TV]


def test_r42c_duplicate_row_in_one_table_does_not_fall_through_to_another():
    dup = "<table>\n" + row(["", *HEAD]) + row(["Total P&amp;G", "9.0%", *VALS[1:]]) + row(["Total P&amp;G", "8.0%", *VALS[1:]]) + "</table>\n"
    w, t, r, c = ws(TITLE + DRV + SUB + dup + DRV + SUB + table())
    assert "value" not in r[TV], ("first table ambiguous, second bound", r[TV].get("value"))


def test_r42d_validator_refuses_forged_row_into_one_of_two_addressable_tables():
    body = BASE + DRV + SUB + table(vals=["2.0%", *VALS[1:]])
    w, t, r, c = ws(body)
    assert "value" not in r[TV]
    (src,) = t.values()
    s, e = at(src, "<td>2.0%</td>", inner="2.0%")
    w2, t2 = forge_present(w, src, TV, s, e, 2.0, "2026-06-30")
    refused(w2, t2, c)


def test_r42e_validator_refuses_forged_row_under_non_matching_heading():
    body = TITLE + "<h2>Supplemental Synthetic Data</h2>\n" + table(vals=["6.0%", *VALS[1:]])
    w, t, r, c = ws(body)
    assert "value" not in r[TV]
    (src,) = t.values()
    s, e = at(src, "<td>6.0%</td>", inner="6.0%")
    w2, t2 = forge_present(w, src, TV, s, e, 6.0, "2026-06-30")
    refused(w2, t2, c)


def test_r42f_validator_refuses_value_read_from_comment_inside_the_cell():
    body = TITLE + DRV + SUB + table(vals=["1.0%<!-- 4.0% -->", *VALS[1:]])
    w, t, r, c = ws(body)
    assert r[TV].get("value") == 1.0
    (src,) = t.values()
    s, e = at(src, "<!-- 4.0% -->", inner="4.0%")
    w2, t2 = forge_present(w, src, TV, s, e, 4.0, "2026-06-30")
    refused(w2, t2, c)


# ======================= R39 combined subject =======================
@pytest.mark.parametrize("metric", pgp.PG_METRIC_KEYS)
def test_r39a_forged_combined_absence_on_split_fixture_refused(metric):
    w = copy.deepcopy(pg_workspace_case("annual_first"))
    t = pg_source_texts("annual_first")
    i = next(i for i, f in enumerate(w["facts"]) if isinstance(f, dict) and f.get("metric") == metric)
    w["facts"][i] = _absent_row(w, metric, f"{metric} combined volume/mix")
    with pytest.raises(EconomicObservationError):
        validate_selected_facts(w, source_texts=t, fiscal_scope=FISCAL_SCOPE)


@pytest.mark.parametrize("metric", pgp.PG_METRIC_KEYS)
def test_r39b_forged_combined_absence_on_combined_fixture_only_for_the_three(metric):
    w = copy.deepcopy(pg_workspace_case("combined_volume_only"))
    t = pg_source_texts("combined_volume_only")
    i = next(i for i, f in enumerate(w["facts"]) if isinstance(f, dict) and f.get("metric") == metric)
    w["facts"][i] = _absent_row(w, metric, f"{metric} combined volume/mix")
    if metric in pgp.PG_COMBINED_VOLUME_MIX_METRICS:
        validate_selected_facts(w, source_texts=t, fiscal_scope=FISCAL_SCOPE)
    else:
        with pytest.raises(EconomicObservationError):
            validate_selected_facts(w, source_texts=t, fiscal_scope=FISCAL_SCOPE)


def _combined_table():
    return table(head=["Net Sales Growth", "Volume/Mix", "Price"], vals=["3.0%", "2.0%", "1.0%"])


def test_r39c_one_combined_one_split_drivers_table_pair_agrees():
    w, t, r, c = ws(TITLE + DRV + SUB + _combined_table() + DRV + SUB + table())
    valid(w, t, c)


def test_r39d_two_combined_drivers_tables_pair_agrees():
    w, t, r, c = ws(TITLE + DRV + SUB + _combined_table() + DRV + SUB + _combined_table())
    valid(w, t, c)


# ======================= R40 statements =======================
def test_r40a_qualifier_after_verb_is_a_conflict():
    w, t, r, c = ws(BASE + "<p>Total P&amp;G volume increased 4% versus the prior year period.</p>\n")
    assert r[TV]["typed_absence"]["reason"] == "cross_check_conflict", r[TV]


def test_r40b_qualifier_before_verb_is_not_a_conflict():
    w, t, r, c = ws(BASE + "<p>In the prior-year quarter, Total P&amp;G volume increased 7%.</p>\n")
    assert r[TV].get("value") == 1.0


def test_r40c_previously_announced_is_not_a_prior_period_qualifier():
    w, t, r, c = ws(BASE + "<p>As previously announced, Total P&amp;G volume increased 4%.</p>\n")
    assert "value" not in r[TV], ("'previously' suppressed a same-period conflict", r[TV].get("value"))


def test_r40d_priorities_is_not_a_prior_period_qualifier():
    w, t, r, c = ws(BASE + "<p>Consistent with our priorities, Total P&amp;G volume increased 4%.</p>\n")
    assert "value" not in r[TV], ("'priorities' suppressed a same-period conflict", r[TV].get("value"))


def test_r40e_subject_after_volume_and_verb():
    w, t, r, c = ws(BASE + "<p>Volume increased 4% for Total P&amp;G.</p>\n")
    assert "value" not in r[TV], ("subject-after sentence missed", r[TV].get("value"))


def test_r40f_multi_sentence_paragraph_second_sentence_conflicts():
    w, t, r, c = ws(BASE + "<p>Net sales grew. Total P&amp;G volume increased 1.5%.</p>\n")
    assert "value" not in r[TV]


def test_r40g_out_of_scope_sentence_inside_in_scope_paragraph_skipped():
    w, t, r, c = ws(BASE + "<p>Total P&amp;G volume increased 1%. In the third quarter of fiscal 2026, Total P&amp;G volume increased 6%.</p>\n")
    assert r[TV].get("value") == 1.0, r[TV]


def test_r40h_unit_volume_subject_after():
    w, t, r, c = ws(BASE + "<p>Unit volume for Total P&amp;G decreased 2%.</p>\n")
    assert "value" not in r[TV]


def test_r40i_percent_spelled_out_is_a_percentage():
    w, t, r, c = ws(BASE + "<p>Total P&amp;G volume increased 4 percent.</p>\n")
    assert "value" not in r[TV], ("'4 percent' missed", r[TV].get("value"))
