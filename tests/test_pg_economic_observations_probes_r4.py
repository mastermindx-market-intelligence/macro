"""Opus R5 throwaway probes for PR #7905 rulings R27-R33 (never committed). Synthetic data only."""
from __future__ import annotations

import copy
import hashlib
import importlib
from datetime import date

import pytest

from engine.company_intelligence.documents import TypedAbsence
from engine.company_intelligence.economic_observations import EconomicObservationError, validate_selected_facts
from engine.company_intelligence.events import FiscalPeriod
import engine.company_intelligence.pg_profile as pgp
from engine.company_intelligence import qa_exchange
from tests.earnings_economic_fixtures import pg_source_texts, pg_workspace_case, FISCAL_PERIOD, FISCAL_SCOPE
from tests.test_pg_economic_observations_probes import Case, Q4_FY2026, _literal_workspace, _pg_rows

Q3_FY2026 = Case(("2026-01-01", "2026-03-31", "2025-01-01", "2025-03-31"), 2026, 3, date(2026, 3, 31),
                 "2026-04-20", "2026-04-20T11:00:00Z", "2026-04-20T11:05:00Z", "0000080424-26-000301")

HEAD = ["Volume with Acquisitions &amp; Divestitures", "Volume Excluding Acquisitions &amp; Divestitures",
        "Foreign Exchange", "Price", "Mix", "Other", "Net Sales Growth", "Organic Sales Growth"]
VALS = ["1.0%", "1.0%", "(1.0)%", "0.5%", "0.5%", "1.0%", "3.0%", "1.0%"]
TITLE = "<h1>Fourth Quarter Fiscal Year 2026 Results</h1>\n"
DRV = "<h2>Net Sales Change Drivers 2026 vs. 2025</h2>\n"
SUB = "<h3>Three Months Ended June 30, 2026</h3>\n"


def row(cells, tag="td"):
    return "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>\n"


def table(head=HEAD, vals=VALS, pre="", tag="td", thead=False, label="Total P&amp;G"):
    h = row(["", *head], tag)
    if thead:
        h = "<thead>" + h + "</thead><tbody>"
    return "<table>\n" + pre + h + row([label, *vals]) + ("</tbody>" if thead else "") + "</table>\n"


def wrap(body):
    return ("<html><head><title>Synthetic probe</title></head><body>\n"
            "<p>Synthetic probe; no relationship to any filing.</p>\n" + body + "</body></html>")


def ws(body, case=Q4_FY2026, slug="r5", quarter=None, year=None):
    if year is not None:
        case = Case(case.scope, year, case.fiscal_quarter, case.period_end, case.filing_date,
                    case.acceptance, case.observed_at, case.accession)
    w, t = _literal_workspace(wrap(body), case, slug, quarter=quarter)
    return w, t, _pg_rows(w), case


def ok(w, t, case):
    validate_selected_facts(w, source_texts=t, fiscal_scope=case.scope)


def refused(w, t, case):
    with pytest.raises(EconomicObservationError):
        validate_selected_facts(w, source_texts=t, fiscal_scope=case.scope)


TV = "pg_total_volume_growth_pct"
BASE = TITLE + DRV + SUB + table()

# ---------------- R27 ----------------
def test_r27_control_topic_then_period_subheading_binds():
    w, t, r, c = ws(BASE)
    assert r[TV].get("value") == 1.0
    ok(w, t, c)


def test_r27a_mixed_title_with_twelve_month_subheading_refuses():
    body = "<h1>P&amp;G Announces Fourth Quarter and Fiscal Year 2026 Results</h1>\n" + DRV + \
        "<h3>Twelve Months Ended June 30, 2026</h3>\n" + table()
    w, t, r, c = ws(body)
    assert "value" not in r[TV]


def test_r27b_fiscal_year_qualifier_in_table_header_row_refuses():
    pre = '<tr><td></td><td colspan="8">Fiscal Year 2026</td></tr>\n'
    w, t, r, c = ws(TITLE + DRV + table(pre=pre))
    assert "value" not in r[TV], r[TV]


def test_r27c_foreign_quarter_title_refuses():
    w, t, r, c = ws("<h1>Third Quarter Fiscal Year 2026 Results</h1>\n" + DRV + table())
    assert "value" not in r[TV]


# test_r27d_year_level_heading_alone_is_not_a_quarterly_form_q3_scope: adjudicated OUT by the seat (R35: a document with no period signal binds by the admitted scope).

def test_r27e_q3_scope_over_june_quarter_header_row_refuses():
    pre = '<tr><td></td><td colspan="8">Three Months Ended June 30, 2026</td></tr>\n'
    w, t, r, c = ws(DRV + table(pre=pre), case=Q3_FY2026)
    assert "value" not in r[TV], ("June-quarter table emitted as", r[TV].get("period"))


def _swap(w, t, old, new):
    (doc_id, src), = t.items()
    assert src.count(old) == 1 and len(old.encode()) == len(new.encode())
    new_src = src.replace(old, new)
    digest = hashlib.sha256(new_src.encode()).hexdigest()
    for f in w["facts"]:
        if isinstance(f, dict) and "value" in f and str(f.get("metric", "")).startswith("pg_"):
            f["source_span"]["receipt"]["source_sha256"] = digest
            f["source_span"]["receipt"]["segment_sha256"] = digest
    return {doc_id: new_src}


def test_r27f_validator_refuses_row_under_allcaps_twelve_month_label():
    w, t, r, c = ws(BASE)
    assert r[TV].get("value") == 1.0
    t2 = _swap(w, t, "<h3>Three Months Ended June 30, 2026</h3>", "<p> TWELVE MONTHS ENDED JUNE 30, 2026</p>")
    refused(w, t2, c)


# test_r27g_validator_refuses_row_whose_quarter_label_is_removed: adjudicated OUT by the seat (R35: a document with no period signal binds by the admitted scope).

def test_r27h_validator_refuses_foreign_quarter_label():
    w, t, r, c = ws(BASE)
    t2 = _swap(w, t, "<h3>Three Months Ended June 30, 2026</h3>", "<h3>Three Months Ended Sept 30, 2026</h3>")
    refused(w, t2, c)


def test_r27i_q3_scope_over_fixture_q4_document_is_refused_all_absent():
    scope = ("2026-01-01", "2026-03-31", "2025-01-01", "2025-03-31")
    period = FiscalPeriod(year=2026, quarter=3, calendar_end=date(2026, 3, 31))
    # Seat adaptation under R41: the fixture now follows the workspace period, so the Q4 document the probe
    # names is requested explicitly (document_period); the scenario -- Q3 scope over a Q4 document -- is unchanged.
    w = pg_workspace_case("annual_first", fiscal_scope=scope, fiscal_period=period, document_period=FISCAL_PERIOD)
    present = [m for m, x in _pg_rows(w).items() if "value" in x]
    assert present == [], present

# ---------------- R28 ----------------
def test_r28a_lowercase_nbsp_double_space_headers_roundtrip():
    head = [h.lower().replace(" with ", " with&nbsp;").replace(" &amp; ", " &amp;  ") for h in HEAD]
    w, t, r, c = ws(TITLE + DRV + SUB + table(head=head))
    assert r[TV].get("value") == 1.0, r[TV]
    ok(w, t, c)


def test_r28b_thead_th_headers_roundtrip():
    w, t, r, c = ws(TITLE + DRV + SUB + table(tag="th", thead=True))
    assert r[TV].get("value") == 1.0, r[TV]
    ok(w, t, c)


def test_r28c_th_headers_without_thead_roundtrip():
    w, t, r, c = ws(TITLE + DRV + SUB + table(tag="th"))
    assert r[TV].get("value") == 1.0, r[TV]
    ok(w, t, c)


def test_r28d_br_inside_header_cell_roundtrip():
    head = [HEAD[0].replace("with ", "with<br>")] + HEAD[1:]
    w, t, r, c = ws(TITLE + DRV + SUB + table(head=head))
    assert r[TV].get("value") == 1.0, r[TV]
    ok(w, t, c)


def test_r28e_numeric_nbsp_entity_in_row_label():
    w, t, r, c = ws(TITLE + DRV + SUB + table(label="Total&#160;P&amp;G"))
    assert r[TV].get("value") == 1.0, r[TV]
    ok(w, t, c)


def test_r28f_extractor_and_validator_share_the_locator():
    import inspect
    from engine.company_intelligence import economic_observations as eo
    assert "replay_table_layout(" in inspect.getsource(pgp._row_fact)
    assert "replay_table_layout(" in inspect.getsource(eo._verify_pg_replay)

# ---------------- R29 ----------------
DASH_VALS = ["—", *VALS[1:]]


def _dash(extra):
    return TITLE + extra + DRV + SUB + table(vals=DASH_VALS)


def test_r29_control_visible_convention_binds_zero():
    w, t, r, c = ws(_dash("<p>In these tables dashes represent zero.</p>\n"))
    assert r[TV].get("value") == 0.0
    ok(w, t, c)


def test_r29a_nested_hidden_element():
    w, t, r, c = ws(_dash("<div hidden><div>note</div><p>In these tables dashes represent zero.</p></div>\n"))
    assert "value" not in r[TV], r[TV]


def test_r29b_attribute_value_with_gt():
    w, t, r, c = ws(_dash('<p><img alt="a > In these tables dashes represent zero."></p>\n'))
    assert "value" not in r[TV], r[TV]


def test_r29c_template_element():
    w, t, r, c = ws(_dash("<template><p>In these tables dashes represent zero.</p></template>\n"))
    assert "value" not in r[TV], r[TV]


def test_r29d_head_title_is_not_body_text():
    body = _dash("")
    w, t, r, c = ws(body.replace("", "", 0))
    src = wrap(body).replace("<title>Synthetic probe</title>", "<title>Dashes represent zero</title>")
    w, t = _literal_workspace(src, Q4_FY2026, "r29d")
    assert "value" not in _pg_rows(w)[TV], _pg_rows(w)[TV]


def test_r29e_display_none_style():
    w, t, r, c = ws(_dash('<p style="DISPLAY : none">In these tables dashes represent zero.</p>\n'))
    assert "value" not in r[TV]

# ---------------- R30 ----------------
def test_r30a_wrong_workspace_year_extractor_all_absent():
    w, t, r, c = ws(BASE, year=2025)
    assert [m for m, x in r.items() if "value" in x] == []


def test_r30b_wrong_workspace_quarter_extractor_all_absent():
    w, t, r, c = ws(BASE, quarter=3)
    assert [m for m, x in r.items() if "value" in x] == []


def test_r30c_fixture_builds_a_non_june_quarter_document():
    period = FiscalPeriod(year=2027, quarter=1, calendar_end=date(2026, 9, 30))
    (src,) = pg_source_texts("annual_first", fiscal_period=period).values()
    assert "September 30" in src and "June 30" not in src and "Fourth Quarter" not in src, src[:600]

# ---------------- R31 ----------------
def test_r31a_private_profile_is_a_distinct_registry_member():
    assert pgp.PG_PRIVATE_RIGHTS_PROFILE in qa_exchange.RIGHTS_PROFILES
    assert pgp.PG_PRIVATE_RIGHTS_PROFILE != qa_exchange.RIGHTS_PROFILE


def test_r31b_second_private_profile_is_an_import_error(monkeypatch):
    monkeypatch.setattr(qa_exchange, "RIGHTS_PROFILES", qa_exchange.RIGHTS_PROFILES | {"rp_other_private_v9"})
    try:
        with pytest.raises(ImportError):
            importlib.reload(pgp)
    finally:
        monkeypatch.undo()
        importlib.reload(pgp)

# ---------------- R32 ----------------
SEG = "".join(row([s, "9.0%", "9.0%"]) for s in ("Beauty", "Grooming"))


def test_r32a_disagreeing_second_table_with_segment_rows_above_total():
    second = "<h2>Segment Results</h2>\n<table>\n" + row(["", "Volume Growth", "Net Sales Growth"]) + SEG + \
        row(["Total P&amp;G", "4.0%", "3.0%"]) + "</table>\n"
    w, t, r, c = ws(BASE + second)
    assert r[TV]["typed_absence"]["reason"] == "cross_check_conflict", r[TV]


def test_r32b_disagreeing_second_table_header_split_in_two_rows():
    second = "<h2>Segment Results</h2>\n<table>\n" + row(["", "Volume", "Net Sales"]) + \
        row(["", "with Acquisitions &amp; Divestitures", "Growth"]) + row(["Total P&amp;G", "4.0%", "3.0%"]) + "</table>\n"
    w, t, r, c = ws(BASE + second)
    assert "value" not in r[TV] and r[TV]["typed_absence"]["reason"] == "cross_check_conflict", r[TV]


def test_r32c_organic_volume_sentence_is_not_a_conflict():
    w, t, r, c = ws(BASE + "<p>Total P&amp;G organic volume increased 3%.</p>\n")
    assert r[TV].get("value") == 1.0, r[TV]


def test_r32d_volume_excluding_sentence_is_not_a_conflict():
    w, t, r, c = ws(BASE + "<p>Total P&amp;G volume excluding acquisitions and divestitures increased 3%.</p>\n")
    assert r[TV].get("value") == 1.0, r[TV]


def test_r32e_disagreeing_sentence_volume_before_subject():
    w, t, r, c = ws(BASE + "<p>Unit volume for Total P&amp;G increased 4%.</p>\n")
    assert "value" not in r[TV], r[TV]


def test_r32f_agreeing_second_table_total_last():
    second = "<h2>Segment Results</h2>\n<table>\n" + row(["", "Total Volume"]) + \
        "".join(row([s, "9.0%"]) for s in ("Beauty",)) + row(["Total P&amp;G", "1.0%"]) + "</table>\n"
    w, t, r, c = ws(BASE + second)
    assert r[TV].get("value") == 1.0, r[TV]
    ok(w, t, c)


def test_r32g_prior_year_labelled_second_table_is_not_a_conflict():
    second = "<h2>Segment Results</h2>\n<table>\n" + row(["", "Three Months Ended June 30, 2025"]) + \
        row(["", "Total Volume"]) + row(["Total P&amp;G", "7.0%"]) + "</table>\n"
    w, t, r, c = ws(BASE + second)
    assert r[TV].get("value") == 1.0, r[TV]


def test_r32h_prior_year_sentence_is_not_a_conflict():
    w, t, r, c = ws(BASE + "<p>In the prior-year quarter, Total P&amp;G volume increased 7%.</p>\n")
    assert r[TV].get("value") == 1.0, r[TV]


def test_r32i_mix_and_organic_columns_do_not_count():
    second = "<h2>Segment Results</h2>\n<table>\n" + row(["", "Volume/Mix", "Organic Volume", "Volume Excluding Acquisitions"]) + \
        row(["Total P&amp;G", "9.0%", "9.0%", "9.0%"]) + "</table>\n"
    w, t, r, c = ws(BASE + second)
    assert r[TV].get("value") == 1.0, r[TV]


def test_r32j_dash_in_second_table_is_not_a_conflict():
    second = "<h2>Segment Results</h2>\n<table>\n" + row(["", "Total Volume"]) + row(["Total P&amp;G", "—"]) + "</table>\n"
    w, t, r, c = ws(BASE + second)
    assert r[TV].get("value") == 1.0, r[TV]

# ---------------- R33 ----------------
def _forge_absent(w, metric, subject):
    doc = next(s["document_id"] for s in w["sources"] if s.get("kind") == "issuer_release")
    ev = w["event_id"]
    d = next(x for x in pgp.PG_DEFINITIONS if x.metric == metric)
    target = next(f for f in w["facts"] if isinstance(f, dict) and f.get("metric") == metric)
    ident = "|".join((ev, metric, metric, d.basis))
    target.clear()
    target.update({"schema": "event_fact.v1", "fact_id": "fact_" + hashlib.sha256(ident.encode()).hexdigest()[:16],
                   "event_id": ev, "metric": metric,
                   "typed_absence": TypedAbsence(reason="no_span_addressable_evidence", subject=subject, detail="forged",
                                                 event_id=ev, document_id=doc).to_payload()})


def test_r33a_combined_absence_refused_when_drivers_table_has_separate_mix_column():
    w, t, r, c = ws(BASE + "<p>Earlier releases used a volume/mix presentation.</p>\n")
    assert r["pg_mix_contribution_pp"].get("value") == 0.5
    _forge_absent(w, "pg_mix_contribution_pp", "pg_mix_contribution_pp combined volume/mix")
    refused(w, t, c)


def test_r33b_combined_absence_refused_for_a_metric_that_is_never_combined():
    w = copy.deepcopy(pg_workspace_case("combined_volume_only"))
    t = pg_source_texts("combined_volume_only")
    validate_selected_facts(copy.deepcopy(w), source_texts=t, fiscal_scope=FISCAL_SCOPE)
    _forge_absent(w, "pg_price_contribution_pp", "pg_price_contribution_pp combined volume/mix")
    with pytest.raises(EconomicObservationError):
        validate_selected_facts(w, source_texts=t, fiscal_scope=FISCAL_SCOPE)


def test_r33c_free_form_subject_suffix_refused():
    w, t, r, c = ws(BASE)
    _forge_absent(w, TV, TV + " volume/mix not separately disclosed")
    refused(w, t, c)


def test_r33d_bare_combined_refused():
    w, t, r, c = ws(BASE + "<p>volume/mix</p>\n")
    _forge_absent(w, TV, TV + " combined")
    refused(w, t, c)
