"""Throwaway adversarial probes (Opus final review, PR #7905 @ c8db6a81cc). Not repo code."""
from __future__ import annotations
import copy
from datetime import date
import pytest
from engine.company_intelligence.economic_observations import EconomicObservationError, validate_selected_facts
from engine.company_intelligence.pg_profile import parse_pg_literal
from tests.test_pg_economic_observations_probes import (
    Case, Q4_FY2026, Q1_FY2027, _literal_workspace, _pg_rows, _present, _validate,
)

HEAD = '<html><head><title>x</title></head><body>\n<p>Synthetic, no relationship to any real filing.</p>\n'
TAIL = '</body></html>'
EPS_TABLE = ('<table>\n<tr><td></td><td>{c}</td><td>{p}</td></tr>\n'
             '<tr><td>Diluted Net Earnings per Common Share</td><td>$3.07</td><td>$2.93</td></tr>\n'
             '<tr><td>Core EPS</td><td>$3.11</td><td>$2.97</td></tr>\n</table>\n')
DRIVERS_HDR = ('<tr><td></td><td>Volume with Acquisitions &amp; Divestitures</td><td>Volume Excluding Acquisitions &amp; Divestitures</td>'
               '<td>Foreign Exchange</td><td>Price</td><td>Mix</td><td>Other</td><td>Net Sales Growth</td></tr>\n')

def _eps(ws):
    return {m: r.get("value") for m, r in _pg_rows(ws).items() if m in {"pg_diluted_eps","pg_prior_diluted_eps","pg_core_eps","pg_prior_core_eps"}}

GOOD = {"pg_diluted_eps": 3.07, "pg_prior_diluted_eps": 2.93, "pg_core_eps": 3.11, "pg_prior_core_eps": 2.97}

# ---- R7: derived heading forms the ruling names explicitly ----
@pytest.mark.parametrize("heading", ["Fourth Quarter 2026", "Fiscal Year 2026 Fourth Quarter"])
def test_r7_ruling_named_heading_forms_bind(heading):
    body = HEAD + f"<h1>{heading}</h1>\n" + EPS_TABLE.format(c="2026", p="2025") + TAIL
    ws, texts = _literal_workspace(body, Q4_FY2026, "r7h")
    assert _eps(ws) == GOOD

# ---- R7/R14: "Three Months Ended" as COLUMN header form ----
def test_r7_three_months_ended_column_headers_bind():
    body = HEAD + "<h1>Fourth Quarter Fiscal Year 2026</h1>\n" + EPS_TABLE.format(
        c="Three Months Ended June 30, 2026", p="Three Months Ended June 30, 2025") + TAIL
    ws, texts = _literal_workspace(body, Q4_FY2026, "r7c")
    assert _eps(ws) == GOOD

# ---- R7: annual forms refused even when the annual heading follows the quarterly heading ----
def test_r7_annual_table_after_quarter_heading_never_binds():
    body = (HEAD + "<h1>Fourth Quarter Fiscal Year 2026</h1>\n<h2>Twelve Months Ended June 30, 2026</h2>\n"
            '<table>\n<tr><td></td><td>2026</td><td>2025</td></tr>\n'
            '<tr><td>Diluted Net Earnings per Common Share</td><td>$12.07</td><td>$11.93</td></tr>\n'
            '<tr><td>Core EPS</td><td>$12.11</td><td>$11.97</td></tr>\n</table>\n' + TAIL)
    ws, texts = _literal_workspace(body, Q4_FY2026, "r7a")
    assert all(v is None for v in _eps(ws).values()), _eps(ws)

# ---- R7: reconciliation located by keyword heading + metric name, not by a sentence ----
def test_r7_reconciliation_by_keyword_heading_and_metric_name():
    body = (HEAD + "<h2>Reconciliation of Non-GAAP Measures</h2>\n"
            "<p>Core EPS excludes restructuring costs of 0.10 per share.</p>\n" + TAIL)
    ws, texts = _literal_workspace(body, Q4_FY2026, "r7r")
    assert "value" in _pg_rows(ws)["pg_core_reconciliation_context"], _pg_rows(ws)["pg_core_reconciliation_context"]

# ---- R7: segment block located by definition keyword {"segment"} ----
def test_r7_segment_table_by_keyword():
    body = (HEAD + "<h2>Segment Results</h2>\n<table>\n<tr><td>Segment</td><td>2026</td><td>2025</td></tr>\n"
            "<tr><td>Beauty</td><td>1%</td><td>0%</td></tr>\n</table>\n" + TAIL)
    ws, texts = _literal_workspace(body, Q4_FY2026, "r7s")
    assert _pg_rows(ws)["pg_beauty_organic_sales_growth_pct"].get("value") == 1.0

# ---- R8: extractor-accepted "Q4 FY2026" column must replay (extractor/validator vocabulary parity) ----
def test_r8_q_fy_column_form_replays():
    body = HEAD + "<h1>Fourth Quarter Fiscal Year 2026</h1>\n" + EPS_TABLE.format(c="Q4 FY2026", p="Q4 FY2025") + TAIL
    ws, texts = _literal_workspace(body, Q4_FY2026, "r8q")
    assert _eps(ws) == GOOD
    _validate(ws, texts, Q4_FY2026.scope)

# ---- R8: two-row header (spanning label row + year row) must replay ----
def test_r8_two_row_header_replays():
    body = (HEAD + "<h1>Fourth Quarter Fiscal Year 2026</h1>\n<table>\n"
            "<tr><td></td><td>Three Months Ended June 30</td><td></td></tr>\n"
            "<tr><td></td><td>2026</td><td>2025</td></tr>\n"
            "<tr><td>Diluted Net Earnings per Common Share</td><td>$3.07</td><td>$2.93</td></tr>\n"
            "<tr><td>Core EPS</td><td>$3.11</td><td>$2.97</td></tr>\n</table>\n" + TAIL)
    ws, texts = _literal_workspace(body, Q4_FY2026, "r8t")
    assert _eps(ws) == GOOD
    _validate(ws, texts, Q4_FY2026.scope)

# ---- R8: dash convention stated AFTER the table (same document) ----
def test_r8_dash_convention_after_table_is_consistent():
    body = (HEAD + "<h2>Net Sales Change Drivers 2026 vs. 2025</h2>\n<table>\n" + DRIVERS_HDR +
            "<tr><td>Total P&amp;G</td><td>1%</td><td>—</td><td>(1)%</td><td>1%</td><td>0%</td><td>0%</td><td>1%</td></tr>\n</table>\n"
            "<p>A dash means zero in the table above.</p>\n" + TAIL)
    ws, texts = _literal_workspace(body, Q4_FY2026, "r8d")
    row = _pg_rows(ws)["pg_organic_volume_growth_pct"]
    if "value" in row:  # extractor accepted the dash as zero -> validator must accept its own output
        _validate(ws, texts, Q4_FY2026.scope)

# ---- R9: fiscal-year identity is not checked (quarter only) ----
def test_r9_wrong_fiscal_year_refused():
    body = HEAD + "<h1>Fourth Quarter Fiscal Year 2026</h1>\n" + EPS_TABLE.format(c="2026", p="2025") + TAIL
    wrong_year = Case(Q4_FY2026.scope, 2019, 4, Q4_FY2026.period_end, Q4_FY2026.filing_date,
                      Q4_FY2026.acceptance, Q4_FY2026.observed_at, Q4_FY2026.accession)
    ws, texts = _literal_workspace(body, wrong_year, "r9y")
    print("event_id", ws["event_id"])
    with pytest.raises(EconomicObservationError):
        _validate(ws, texts, Q4_FY2026.scope)

# ---- R9: a Q2 scope (Oct-Dec) binds fiscal Q2 of the NEXT fiscal year ----
def test_r9_q2_scope_binds():
    q2 = Case(("2026-10-01", "2026-12-31", "2025-10-01", "2025-12-31"), 2027, 2, date(2026, 12, 31),
              "2027-01-22", "2027-01-22T11:00:00Z", "2027-01-22T11:05:00Z", "0000080424-27-000109")
    body = HEAD + "<h1>Second Quarter Fiscal Year 2027</h1>\n" + EPS_TABLE.format(c="2026", p="2025") + TAIL
    ws, texts = _literal_workspace(body, q2, "r9q2")
    assert _eps(ws) == GOOD
    _validate(ws, texts, q2.scope)
    ws3, t3 = _literal_workspace(body, q2, "r9q2b", quarter=4)
    with pytest.raises(EconomicObservationError):
        _validate(ws3, t3, q2.scope)

# ---- R10: absence fact_id must follow the identity function too ----
def test_r10_absence_fact_id_is_bound():
    body = HEAD + "<h1>Fourth Quarter Fiscal Year 2026</h1>\n" + EPS_TABLE.format(c="2026", p="2025") + TAIL
    ws, texts = _literal_workspace(body, Q4_FY2026, "r10")
    _validate(copy.deepcopy(ws), texts, Q4_FY2026.scope)
    for row in ws["facts"]:
        if row.get("metric") == "pg_reported_sales_growth_pct":
            assert "typed_absence" in row
            row["fact_id"] = "fact_attacker_chosen"
    with pytest.raises(EconomicObservationError):
        _validate(ws, texts, Q4_FY2026.scope)

# ---- R11: unbalanced / malformed parentheses beyond the probe literals ----
@pytest.mark.parametrize("lit,unit", [("1.25%)", "percent"), ("((1.25)%", "percent"), ("(1.25))%", "percent"),
                                      ("$(1.25", "usd_per_share"), ("(($1.25)", "usd_per_share"), ("(1.25)%)", "percentage_points")])
def test_r11_malformed_parentheses_refused(lit, unit):
    assert parse_pg_literal(lit, unit=unit) is None

def test_r11_percent_in_driver_cell_for_eps_is_unit_mismatch():
    body = (HEAD + "<h1>Fourth Quarter Fiscal Year 2026</h1>\n<table>\n<tr><td></td><td>2026</td><td>2025</td></tr>\n"
            "<tr><td>Diluted Net Earnings per Common Share</td><td>3.07%</td><td>$2.93</td></tr>\n"
            "<tr><td>Core EPS</td><td>$3.11</td><td>$2.97</td></tr>\n</table>\n"
            "<h2>Net Sales Change Drivers 2026 vs. 2025</h2>\n<table>\n" + DRIVERS_HDR +
            "<tr><td>Total P&amp;G</td><td>$1</td><td>1%</td><td>(1)%</td><td>1%</td><td>0%</td><td>0%</td><td>1%</td></tr>\n</table>\n" + TAIL)
    ws, texts = _literal_workspace(body, Q4_FY2026, "r11")
    rows = _pg_rows(ws)
    assert rows["pg_diluted_eps"]["typed_absence"]["reason"] == "unit_mismatch"
    assert rows["pg_total_volume_growth_pct"]["typed_absence"]["reason"] == "unit_mismatch"
    _validate(ws, texts, Q4_FY2026.scope)

# ---- R13: volume in a second table disagrees with the drivers table ----
def test_r13_second_table_volume_disagreement_is_typed_absence():
    body = (HEAD + "<h2>Net Sales Change Drivers 2026 vs. 2025</h2>\n<table>\n" + DRIVERS_HDR +
            "<tr><td>Total P&amp;G</td><td>1%</td><td>1%</td><td>(1)%</td><td>1%</td><td>0%</td><td>0%</td><td>1%</td></tr>\n</table>\n"
            "<h2>Three Months Ended June 30, 2026</h2>\n<table>\n<tr><td></td><td>Volume</td></tr>\n"
            "<tr><td>Total P&amp;G</td><td>4%</td></tr>\n</table>\n" + TAIL)
    ws, texts = _literal_workspace(body, Q4_FY2026, "r13")
    assert "typed_absence" in _pg_rows(ws)["pg_total_volume_growth_pct"], _pg_rows(ws)["pg_total_volume_growth_pct"]

# ---- R15/R9: a 'combined volume/mix' subject must not be claimed when no combined line exists ----
def test_r15_no_combined_claim_without_combined_line():
    body = HEAD + "<h1>Fourth Quarter Fiscal Year 2026</h1>\n" + EPS_TABLE.format(c="2026", p="2025") + TAIL
    ws, texts = _literal_workspace(body, Q4_FY2026, "r15")
    ab = _pg_rows(ws)["pg_total_volume_growth_pct"]["typed_absence"]
    assert "combined" not in (ab["subject"] + ab["detail"]).casefold(), ab
