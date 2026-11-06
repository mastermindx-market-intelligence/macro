"""Opus R4 throwaway probes for PR #7905 @635877f3df (rulings R17-R23). Not repo code."""
from __future__ import annotations
import copy
from datetime import date
import pytest
from engine.company_intelligence.economic_observations import EconomicObservationError, validate_selected_facts
from tests.test_pg_economic_observations_probes import Case, Q4_FY2026, Q1_FY2027, _literal_workspace, _pg_rows, _present

Q2_FY2026 = Case(("2025-10-01", "2025-12-31", "2024-10-01", "2024-12-31"), 2026, 2, date(2025, 12, 31),
                 "2026-01-23", "2026-01-23T11:00:00Z", "2026-01-23T11:05:00Z", "0000080424-26-000201")
Q3_FY2026 = Case(("2026-01-01", "2026-03-31", "2025-01-01", "2025-03-31"), 2026, 3, date(2026, 3, 31),
                 "2026-04-24", "2026-04-24T11:00:00Z", "2026-04-24T11:05:00Z", "0000080424-26-000202")

H = '<html><head><title>t</title></head><body>\n<p>Synthetic probe; no relationship to any filing.</p>\n'
T = '</body></html>'
EPS_M = {"pg_diluted_eps", "pg_prior_diluted_eps", "pg_core_eps", "pg_prior_core_eps"}
DRV_M = {"pg_reported_sales_growth_pct", "pg_organic_sales_growth_pct", "pg_total_volume_growth_pct",
         "pg_organic_volume_growth_pct", "pg_price_contribution_pp", "pg_mix_contribution_pp",
         "pg_fx_contribution_pp", "pg_other_contribution_pp"}
GOOD = {"pg_diluted_eps": 3.07, "pg_prior_diluted_eps": 2.93, "pg_core_eps": 3.11, "pg_prior_core_eps": 2.97}


def eps(c, p, *, header_rows=None):
    hdr = header_rows if header_rows is not None else f'<tr><td></td><td>{c}</td><td>{p}</td></tr>\n'
    return ('<table>\n' + hdr +
            '<tr><td>Diluted Net Earnings per Common Share</td><td>$3.07</td><td>$2.93</td></tr>\n'
            '<tr><td>Core EPS</td><td>$3.11</td><td>$2.97</td></tr>\n</table>\n')


def drivers(vals=("1.0%", "1.0%", "(1.0)%", "0.5%", "0.5%", "1.0%", "3.0%", "1.0%"), *, reverse=False, lower=False):
    hdrs = ["Volume with Acquisitions &amp; Divestitures", "Volume Excluding Acquisitions &amp; Divestitures",
            "Foreign Exchange", "Price", "Mix", "Other", "Net Sales Growth", "Organic Sales Growth"]
    if lower:
        hdrs = [h.lower() for h in hdrs]
    pairs = list(zip(hdrs, vals))
    if reverse:
        pairs.reverse()
    return ('<table>\n<tr><td></td>' + ''.join(f'<td>{h}</td>' for h, _ in pairs) + '</tr>\n'
            '<tr><td>Total P&amp;G</td>' + ''.join(f'<td>{v}</td>' for _, v in pairs) + '</tr>\n</table>\n')


def ws(body, case, slug, **kw):
    return _literal_workspace(H + body + T, case, slug, **kw)


def val(w, texts, case):
    return validate_selected_facts(w, source_texts=texts, fiscal_scope=case.scope)


def vals(w, metrics):
    rows = _pg_rows(w)
    return {m: rows[m].get("value") for m in metrics}

# ---------------- R17 ----------------
def test_r17a_annual_only_drivers_table_is_never_bound_as_quarter():
    body = ('<h2>Fourth Quarter Fiscal Year 2026</h2>\n' + eps("2026", "2025") +
            '<h2>Twelve Months Ended June 30, 2026</h2>\n' + drivers(("9.0%",) * 8))
    w, _t = ws(body, Q4_FY2026, "r17a")
    assert all(v is None for v in vals(w, DRV_M).values()), vals(w, DRV_M)


def test_r17b_twelve_month_drivers_first_does_not_win():
    body = ('<h2>Net Sales Change Drivers 2026 vs. 2025 (Twelve Months Ended June 30, 2026)</h2>\n' + drivers(("9.0%",) * 8) +
            '<h2>Net Sales Change Drivers 2026 vs. 2025 (Three Months Ended June 30, 2026)</h2>\n' + drivers())
    w, _t = ws(body, Q4_FY2026, "r17b")
    got = vals(w, {"pg_reported_sales_growth_pct"})["pg_reported_sales_growth_pct"]
    assert got != 9.0, "annual drivers table bound as Q4"


def test_r17c_q3_scope_never_binds_a_q4_drivers_table():
    body = ('<h2>Fourth Quarter Fiscal Year 2026</h2>\n<h2>Net Sales Change Drivers 2026 vs. 2025</h2>\n'
            '<h2>Three Months Ended June 30, 2026</h2>\n' + drivers())
    w, _t = ws(body, Q3_FY2026, "r17c")
    assert all(v is None for v in vals(w, DRV_M).values()), vals(w, DRV_M)


def test_r17d_q2_scope_q_form_heading_and_columns_bind():
    body = '<h2>Q2 FY2026</h2>\n' + eps("Q2 FY2026", "Q2 FY2025")
    w, texts = ws(body, Q2_FY2026, "r17d")
    assert vals(w, EPS_M) == GOOD
    val(w, texts, Q2_FY2026)


def test_r17e_q3_ordinal_quarter_fy_heading_three_months_columns_reordered_prior_first():
    body = ('<h2>Third Quarter 2026</h2>\n' +
            '<table>\n<tr><td></td><td>Three Months Ended March 31, 2025</td><td>Three Months Ended March 31, 2026</td></tr>\n'
            '<tr><td>Diluted Net Earnings per Common Share</td><td>$2.93</td><td>$3.07</td></tr>\n'
            '<tr><td>Core EPS</td><td>$2.97</td><td>$3.11</td></tr>\n</table>\n')
    w, texts = ws(body, Q3_FY2026, "r17e")
    assert vals(w, EPS_M) == GOOD
    val(w, texts, Q3_FY2026)


def test_r17f_q1_fiscal_heading_then_fiscal_year_heading_table_absent():
    body = ('<h2>Fiscal Year 2027 First Quarter</h2>\n<p>Commentary.</p>\n<h3>Fiscal Year 2026</h3>\n' + eps("2026", "2025"))
    w, _t = ws(body, Q1_FY2027, "r17f")
    assert all(v is None for v in vals(w, EPS_M).values())


def test_r17g_q1_first_quarter_fiscal_form_binds():
    body = '<h2>First Quarter Fiscal 2027</h2>\n' + eps("September 30, 2026", "September 30, 2025")
    w, texts = ws(body, Q1_FY2027, "r17g")
    assert vals(w, EPS_M) == GOOD
    val(w, texts, Q1_FY2027)

# ---------------- R18 ----------------
def test_r18a_segment_under_unseen_heading_and_reconciliation_under_unseen_heading():
    body = ('<h2>Fourth Quarter 2026</h2>\n' + eps("2026", "2025") +
            '<h2>Reconciliation of Core EPS to Diluted EPS</h2>\n<p>Core EPS excludes restructuring costs of 0.10 per share.</p>\n'
            '<h2>Organic Growth by Reportable Segment</h2>\n<table>\n<tr><td>Segment</td><td>2025</td><td>2026</td></tr>\n'
            '<tr><td>Beauty</td><td>0.5%</td><td>1.0%</td></tr>\n<tr><td>Grooming</td><td>1.5%</td><td>2.0%</td></tr>\n</table>\n')
    w, texts = ws(body, Q4_FY2026, "r18a")
    p = _present(w)
    assert p["pg_beauty_organic_sales_growth_pct"]["value"] == 1.0
    assert p["pg_grooming_organic_sales_growth_pct"]["value"] == 2.0
    assert "restructuring" in p["pg_core_reconciliation_context"]["value"]
    val(w, texts, Q4_FY2026)

# ---------------- R19 ----------------
@pytest.mark.parametrize("c,p", [
    ("three months ended june 30, 2026", "three months ended june 30, 2025"),
    ("June&nbsp;30, 2026", "June&nbsp;30, 2025"),
    ("Three Months Ended  June 30, 2026", "Three Months Ended  June 30, 2025"),
])
def test_r19a_validator_accepts_what_extractor_emits_header_spelling(c, p):
    body = '<h2>Fourth Quarter 2026</h2>\n' + eps(c, p)
    w, texts = ws(body, Q4_FY2026, "r19a")
    emitted = vals(w, EPS_M)
    if emitted == GOOD:
        val(w, texts, Q4_FY2026)  # round trip must hold
    else:
        assert all(v is None for v in emitted.values())


def test_r19b_lowercase_driver_header_round_trips():
    body = '<h2>Net Sales Change Drivers 2026 vs. 2025</h2>\n' + drivers(lower=True)
    w, texts = ws(body, Q4_FY2026, "r19b")
    if vals(w, {"pg_price_contribution_pp"})["pg_price_contribution_pp"] is not None:
        val(w, texts, Q4_FY2026)


def test_r19c_three_header_rows_round_trip():
    hdr = ('<tr><td></td><td>Quarter</td><td></td></tr>\n<tr><td></td><td>Three Months Ended June 30</td><td></td></tr>\n'
           '<tr><td></td><td>2026</td><td>2025</td></tr>\n')
    body = '<h2>Fiscal Year 2026 Fourth Quarter</h2>\n' + eps(None, None, header_rows=hdr)
    w, texts = ws(body, Q4_FY2026, "r19c")
    assert vals(w, EPS_M) == GOOD
    val(w, texts, Q4_FY2026)


def test_r19d_dash_convention_after_table_round_trips():
    v = ("1.0%", "—", "(1.0)%", "0.5%", "0.5%", "1.0%", "3.0%", "1.0%")
    body = '<h2>Net Sales Change Drivers 2026 vs. 2025</h2>\n' + drivers(v) + '<p>Note: dashes represent zero.</p>\n'
    w, texts = ws(body, Q4_FY2026, "r19d")
    assert vals(w, {"pg_organic_volume_growth_pct"})["pg_organic_volume_growth_pct"] == 0.0
    val(w, texts, Q4_FY2026)


def test_r19e_dash_convention_hidden_in_html_comment_is_not_a_convention():
    v = ("1.0%", "—", "(1.0)%", "0.5%", "0.5%", "1.0%", "3.0%", "1.0%")
    body = '<!-- a dash means zero -->\n<h2>Net Sales Change Drivers 2026 vs. 2025</h2>\n' + drivers(v)
    w, _t = ws(body, Q4_FY2026, "r19e")
    assert vals(w, {"pg_organic_volume_growth_pct"})["pg_organic_volume_growth_pct"] is None

# ---------------- R20 ----------------
@pytest.mark.parametrize("case,year,quarter,ok", [
    (Q2_FY2026, 2026, 2, True), (Q2_FY2026, 2025, 2, False), (Q3_FY2026, 2025, 3, False),
    (Q1_FY2027, 2027, 1, True), (Q1_FY2027, 2026, 1, False), (Q1_FY2027, 2027, 3, False),
])
def test_r20_fiscal_year_quarter_from_scope(case, year, quarter, ok):
    body = '<h2>Q{} FY{}</h2>\n'.format(case.fiscal_quarter, case.fiscal_year) + eps(
        f"Q{case.fiscal_quarter} FY{case.fiscal_year}", f"Q{case.fiscal_quarter} FY{case.fiscal_year - 1}")
    bad = Case(case.scope, year, quarter, case.period_end, case.filing_date, case.acceptance, case.observed_at, case.accession)
    w, texts = ws(body, bad, "r20")
    if ok:
        val(w, texts, case)
    else:
        with pytest.raises(EconomicObservationError):
            val(w, texts, case)


def test_r20b_extractor_itself_refuses_wrong_fiscal_year():
    body = '<h2>Q2 FY2026</h2>\n' + eps("Q2 FY2026", "Q2 FY2025")
    bad = Case(Q2_FY2026.scope, 2025, 2, Q2_FY2026.period_end, Q2_FY2026.filing_date, Q2_FY2026.acceptance, Q2_FY2026.observed_at, Q2_FY2026.accession)
    w, _t = ws(body, bad, "r20b")
    assert all(v is None for v in vals(w, EPS_M).values()), (w["event_id"], vals(w, EPS_M))

# ---------------- R21 ----------------
def test_r21a_absence_fact_id_with_plausible_period_formula_refused():
    import hashlib
    body = '<h2>Fourth Quarter 2026</h2>\n' + eps("2026", "2025")
    w, texts = ws(body, Q4_FY2026, "r21a")
    val(copy.deepcopy(w), texts, Q4_FY2026)
    row = next(r for r in w["facts"] if r.get("metric") == "pg_mix_contribution_pp")
    ident = "|".join((w["event_id"], "pg_mix_contribution_pp", "2026-06-30", "reported_growth_bridge"))
    row["fact_id"] = "fact_" + hashlib.sha256(ident.encode()).hexdigest()[:16]
    with pytest.raises(EconomicObservationError):
        val(w, texts, Q4_FY2026)


def test_r21b_release_selected_by_role_not_position():
    body = '<h2>Fourth Quarter 2026</h2>\n' + eps("2026", "2025")
    w, texts = ws(body, Q4_FY2026, "r21b")
    w["sources"] = [{"kind": "transcript", "document_id": "doc_other", "receipt_state": "byte_replayed"}, *w["sources"]]
    val(w, texts, Q4_FY2026)

# ---------------- R22 ----------------
SEG_VOL = ('<h2>Segment Results</h2>\n<table>\n<tr><td></td><td>{h}</td><td>Organic Sales Growth</td></tr>\n'
           '<tr><td>Total P&amp;G</td><td>{v}</td><td>1.0%</td></tr>\n</table>\n')


@pytest.mark.parametrize("h", ["Volume", "Volume Growth", "Total Volume"])
def test_r22a_second_table_disagreement_is_cross_check_conflict(h):
    body = '<h2>Net Sales Change Drivers 2026 vs. 2025</h2>\n' + drivers() + SEG_VOL.format(h=h, v="4.0%")
    w, texts = ws(body, Q4_FY2026, "r22a")
    row = _pg_rows(w)["pg_total_volume_growth_pct"]
    assert "value" not in row and row["typed_absence"]["reason"] == "cross_check_conflict", row
    val(w, texts, Q4_FY2026)


def test_r22b_summary_line_disagreement_is_cross_check_conflict():
    body = ('<h2>Net Sales Change Drivers 2026 vs. 2025</h2>\n' + drivers() +
            '<p>Total P&amp;G volume increased 4% versus the prior year period.</p>\n')
    w, _t = ws(body, Q4_FY2026, "r22b")
    row = _pg_rows(w)["pg_total_volume_growth_pct"]
    assert "value" not in row and row["typed_absence"]["reason"] == "cross_check_conflict", row


def test_r22c_three_row_header_second_table_disagreement():
    body = ('<h2>Net Sales Change Drivers 2026 vs. 2025</h2>\n' + drivers() +
            '<h2>Segment Results</h2>\n<table>\n<tr><td></td><td>Three Months Ended</td></tr>\n<tr><td></td><td>June 30, 2026</td></tr>\n'
            '<tr><td></td><td>Volume</td></tr>\n<tr><td>Total P&amp;G</td><td>4.0%</td></tr>\n</table>\n')
    w, _t = ws(body, Q4_FY2026, "r22c")
    row = _pg_rows(w)["pg_total_volume_growth_pct"]
    assert "value" not in row and row["typed_absence"]["reason"] == "cross_check_conflict", row


def test_r22d_agreeing_second_statement_keeps_value():
    body = '<h2>Net Sales Change Drivers 2026 vs. 2025</h2>\n' + drivers() + SEG_VOL.format(h="Volume", v="1.0%")
    w, texts = ws(body, Q4_FY2026, "r22d")
    assert _pg_rows(w)["pg_total_volume_growth_pct"].get("value") == 1.0
    val(w, texts, Q4_FY2026)


def test_r22e_prior_year_volume_in_second_table_is_not_a_conflict():
    body = ('<h2>Net Sales Change Drivers 2026 vs. 2025</h2>\n' + drivers() +
            '<h2>Net Sales Change Drivers 2025 vs. 2024</h2>\n' + drivers(("7.0%",) * 8))
    w, _t = ws(body, Q4_FY2026, "r22e")
    assert _pg_rows(w)["pg_total_volume_growth_pct"].get("value") == 1.0, _pg_rows(w)["pg_total_volume_growth_pct"]

# ---------------- R23 ----------------
def test_r23a_no_drivers_table_plain_subject():
    body = '<h2>Fourth Quarter 2026</h2>\n' + eps("2026", "2025")
    w, texts = ws(body, Q4_FY2026, "r23a")
    for m in ("pg_total_volume_growth_pct", "pg_mix_contribution_pp"):
        a = _pg_rows(w)[m]["typed_absence"]
        assert a["subject"] == m and "combined" not in a["detail"].casefold()
    val(w, texts, Q4_FY2026)


def test_r23b_forged_combined_subject_naming_one_component_refused():
    body = ('<h2>Net Sales Change Drivers 2026 vs. 2025</h2>\n<table>\n<tr><td></td><td>Net Sales Growth</td><td>Volume/Mix</td></tr>\n'
            '<tr><td>Total P&amp;G</td><td>3.0%</td><td>2.0%</td></tr>\n</table>\n')
    w, texts = ws(body, Q4_FY2026, "r23b")
    a = _pg_rows(w)["pg_total_volume_growth_pct"]["typed_absence"]
    assert "volume/mix" in a["subject"]
    val(copy.deepcopy(w), texts, Q4_FY2026)
    a["subject"] = "pg_total_volume_growth_pct combined"  # subject names neither 'mix' nor the combined line
    with pytest.raises(EconomicObservationError):
        val(w, texts, Q4_FY2026)
