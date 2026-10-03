"""Opus round-16 red-team probes for PR #7905 at 6a59d80bf261 (rulings R97-R105), frozen by the seat as the fifteenth suite (R115). Original synthetic data only. Struck at freeze (R113): three f07 honest-document refusals (nongaap_footnote_after, forward_statements_after, masthead_label) and the two c01 fiscal-label drivers pairs (fy_pair_q1, fiscal_pair_q2), each a fail-closed refusal at the reviewed head, recorded as T1b findings; the f07 control unaudited_paren, which binds at the reviewed head, is kept.
w* = wrong bind; v* = validator paired with the wrong bind (skip when not bound); f* = fail-closed refusal;
x* = validator surface; c* = controls; l* = lexicon (non-blocking under R105)."""
from __future__ import annotations

import copy

import pytest

from engine.company_intelligence.economic_observations import EconomicObservationError, validate_selected_facts
from tests.test_pg_economic_observations_probes import Q1_FY2027, Q4_FY2026
from tests.test_pg_economic_observations_probes_r4 import Q3_FY2026, TITLE, DRV, SUB, row, table, _forge_absent
from tests.test_pg_economic_observations_probes_r5 import ws, TV, DIL, forge_present, at
from tests.test_pg_economic_observations_probes_r7 import DILL, YEARS, BEAUTY, _val
from tests.test_pg_economic_observations_probes_r10 import T1, GUIDE_T
from tests.test_pg_economic_observations_probes_r14 import Q2_FY2027, T2, PF_T, SEGH


def _refuses(w, t, c):
    try:
        validate_selected_facts(w, source_texts=t, fiscal_scope=c.scope)
    except EconomicObservationError:
        return True
    return False


def _v(body, metric, wrong, case=Q4_FY2026):
    w, t, r, c = ws(body, case=case, slug="r16")
    got = _val(r, metric)
    if got != wrong:
        pytest.skip(f"extractor did not bind the wrong value (got {got!r})")
    assert _refuses(w, t, c), f"VALIDATOR ACCEPTS wrong value {wrong!r} for {metric}"


# ===== A (R97): drivers years =====
DRV3 = [
    (T1 + "<h2>Net Sales Change Drivers FY27 vs. FY26 vs. FY25</h2>\n" + table(), Q1_FY2027),
    (T1 + "<h2>Net Sales Change Drivers Fiscal 2027 vs. 2026 vs. 2025</h2>\n" + table(), Q1_FY2027),
    (T2 + "<h2>Net Sales Change Drivers Fiscal 2027 vs. 2026 vs. 2025</h2>\n" + table(), Q2_FY2027),
    (T1 + "<h2>Net Sales Change Drivers &#8217;27 vs. &#8217;26 vs. &#8217;25</h2>\n" + table(), Q1_FY2027),
    (T2 + "<h2>Net Sales Change Drivers FY 2027 vs. FY 2026 vs. FY 2025</h2>\n" + table(), Q2_FY2027),
    (T1 + "<h2>Net Sales Change Drivers 2026 vs. 2025 (Fiscal 2027)</h2>\n" + table(), Q1_FY2027),
    (T2 + "<h2>Net Sales Change Drivers 2026 vs. 2025</h2>\n" + table(), Q2_FY2027),
    ("<h1>Third Quarter Fiscal Year 2026 Results</h1>\n<h2>Net Sales Change Drivers 2027 vs. 2026 vs. 2025</h2>\n" + table(), Q3_FY2026),
]
DRV3_IDS = ["fy_labels_q1", "fiscal_word_q1", "fiscal_word_q2", "apostrophe_q1", "fy_space_q2", "pair_prior_fiscal_named_q1", "pair_prior_q2", "future_year_q3"]


@pytest.mark.parametrize("body,case", DRV3, ids=DRV3_IDS)
def test_w01_three_year_or_prior_pair_drivers(body, case):
    w, t, r, c = ws(body, case=case, slug="r16")
    assert "value" not in r[TV], _val(r, TV)


@pytest.mark.parametrize("body,case", DRV3, ids=DRV3_IDS)
def test_v01(body, case):
    _v(body, TV, 1.0, case=case)


@pytest.mark.parametrize("head,case", [
    ("<h2>Net Sales Change Drivers 2027 vs. 2026</h2>", Q1_FY2027),
], ids=["pair_q1"])
def test_c01_current_pair_binds(head, case):
    w, t, r, c = ws((T1 if case is Q1_FY2027 else T2) + head + "\n" + table(), case=case, slug="r16")
    assert _val(r, TV) == 1.0, r[TV]


# ===== B (R98): titles =====
TITLES = [
    "Fourth Quarter Fiscal Year 2026 Results; Q4 Outlook",
    "Fourth Quarter Fiscal Year 2026 Results; Fourth-Quarter Outlook",
    "Fourth Quarter Fiscal Year 2026 Results; Outlook for the Quarter Ended June 30, 2026",
    "Fourth Quarter Fiscal Year 2026 Results; Q4 FY26 Guidance",
    "Fourth Quarter Fiscal Year 2026 Results; April&#8211;June 2026 Outlook",
    "Fourth Quarter Fiscal Year 2026 Results; Q4 FY 2026 Outlook",
    "Fourth Quarter Fiscal Year 2026 Results and Fourth Fiscal Quarter 2026 Outlook",
    "P&amp;G Announces Fourth Quarter Fiscal Year 2026 Earnings Date and Outlook",
]
TITLE_IDS = ["q4_bare", "fourth_hyphen", "quarter_ended", "q4_fy26", "month_range", "fy_space", "fourth_fiscal_quarter", "announces_date"]


@pytest.mark.parametrize("title", TITLES, ids=TITLE_IDS)
def test_w02_forward_clause_names_quarter_in_other_spelling(title):
    w, t, r, c = ws(f"<h1>{title}</h1>\n" + SEGH + GUIDE_T, slug="r16")
    assert _val(r, BEAUTY) is None, (title, r[BEAUTY])


@pytest.mark.parametrize("title", TITLES, ids=TITLE_IDS)
def test_v02(title):
    _v(f"<h1>{title}</h1>\n" + SEGH + GUIDE_T, BEAUTY, 5.0)


def test_l02_preview_is_not_a_forward_word():
    w, t, r, c = ws("<h1>Fourth Quarter Fiscal Year 2026 Earnings Preview</h1>\n" + SEGH + GUIDE_T, slug="r16")
    assert _val(r, BEAUTY) is None, r[BEAUTY]


def test_c02_results_and_fy_outlook_binds():
    w, t, r, c = ws("<h1>Fourth Quarter Fiscal Year 2026 Results and Fiscal Year 2027 Outlook</h1>\n" + SEGH + GUIDE_T, slug="r16")
    assert _val(r, BEAUTY) == 5.0, r[BEAUTY]


# ===== C (R99): variants of LISTED terms (blocking under R105) =====
VARIANTS = [
    "The results below are re-stated for the merger.",
    "The results below are re-cast for the merger.",
    "Amounts below are before non recurring items.",
    "Amounts below are before nonrecurring items.",
    "Amounts below are before one time items.",
    "The table below is presented on a pro&#8209;forma basis.",
    "The table below is presented on a pro&#8211;forma basis.",
    "The following table presents non&#8209;GAAP results.",
    "The following table presents non&#8211;GAAP results.",
    "Amounts below are on a constant&#8209;currency basis.",
    "The results below are as&#8209;adjusted for the merger.",
    "The results below give\neffect to the merger.",
    "Amounts below are shown before special items.",
    "The results are presented for the combined&#8209;company.",
    "The table below presents combined-company results.",
    "The results below reflect the Successor period.",
]
VAR_IDS = ["re_stated", "re_cast", "non_recurring_space", "nonrecurring", "one_time_space", "proforma_nbhyphen", "proforma_endash",
           "nongaap_nbhyphen", "nongaap_endash", "constant_nbhyphen", "as_adjusted_nbhyphen", "give_newline_effect",
           "before_special_items", "combined_nbhyphen_company", "combined_company_hyphen", "successor"]


@pytest.mark.parametrize("sentence", VARIANTS, ids=VAR_IDS)
def test_w03_listed_term_variant(sentence):
    w, t, r, c = ws(TITLE + SUB + f"<p>{sentence}</p>\n" + PF_T, slug="r16")
    assert _val(r, DIL) is None, (sentence, r[DIL])


@pytest.mark.parametrize("sentence", VARIANTS, ids=VAR_IDS)
def test_v03(sentence):
    _v(TITLE + SUB + f"<p>{sentence}</p>\n" + PF_T, DIL, 3.40)


# ===== D (R99): the figure test, own-name exception, structural cells =====
STRUCT = [
    # figure-bearing "label": prose, so no vocabulary check; basis not in either lexicon -> lexicon only
    ("l_figure_unlisted", TITLE + SUB + "<p>Post-Acquisition Entity Results 5%</p>\n" + PF_T),
    # own-name: prose declares the table's basis using its own row name
    ("own_row_core_eps", TITLE + SUB + "<p>All per-share amounts in the table below are presented as Core EPS.</p>\n"
     + "<table>\n" + YEARS + row([DILL, "$3.40", "$2.93"]) + row(["Core EPS", "$3.40", "$2.93"]) + "</table>\n"),
    # own-name: a footer row repeats the basis, prose repeats the footer row
    ("own_footer_row", TITLE + SUB + "<p>Amounts exclude the acquired business</p>\n".replace("</p>", ".</p>")
     + "<table>\n" + YEARS + row([DILL, "$3.40", "$2.93"]) + '<tr><td colspan="3">Amounts exclude the acquired business</td></tr>\n' + "</table>\n"),
    # footer / section row cells carrying the basis
    ("footer_row_proforma", TITLE + SUB + "<table>\n" + YEARS + row([DILL, "$3.40", "$2.93"]) + '<tr><td colspan="3">Pro forma combined company</td></tr>\n</table>\n'),
    ("footer_row_nongaap", TITLE + SUB + "<table>\n" + YEARS + row([DILL, "$3.40", "$2.93"]) + '<tr><td colspan="3">Non-GAAP</td></tr>\n</table>\n'),
    ("section_row_adjusted", TITLE + SUB + "<table>\n" + YEARS + row(["As Adjusted:", "", ""]) + row([DILL, "$3.40", "$2.93"]) + "</table>\n"),
    ("band_adjusted", TITLE + SUB + "<table>\n" + row(["", "2026 As Adjusted", "2025 As Adjusted"]) + row([DILL, "$3.40", "$2.93"]) + "</table>\n"),
    ("band_nongaap", TITLE + SUB + "<table>\n" + row(["", "Non-GAAP", "Non-GAAP"]) + YEARS + row([DILL, "$3.40", "$2.93"]) + "</table>\n"),
    ("band_excluding", TITLE + SUB + "<table>\n" + row(["", "2026 Excluding Charges", "2025 Excluding Charges"]) + row([DILL, "$3.40", "$2.93"]) + "</table>\n"),
    ("caption_adjusted", TITLE + SUB + "<table><caption>As Adjusted</caption>\n" + YEARS + row([DILL, "$3.40", "$2.93"]) + "</table>\n"),
    ("stub_header_proforma", TITLE + SUB + "<table>\n" + row(["Pro Forma Combined", "2026", "2025"]) + row([DILL, "$3.40", "$2.93"]) + "</table>\n"),
    ("stub_header_nongaap", TITLE + SUB + "<table>\n" + row(["Non-GAAP", "2026", "2025"]) + row([DILL, "$3.40", "$2.93"]) + "</table>\n"),
]


@pytest.mark.parametrize("body", [b for _i, b in STRUCT], ids=[i for i, _b in STRUCT])
def test_w04_structural_basis(body):
    w, t, r, c = ws(body, slug="r16")
    assert _val(r, DIL) is None, r[DIL]


@pytest.mark.parametrize("body", [b for _i, b in STRUCT], ids=[i for i, _b in STRUCT])
def test_v04(body):
    _v(body, DIL, 3.40)


# ===== E (R99/R101): stretch boundaries =====
BOUND = [
    ("para_before_topic", TITLE + "<p>All amounts in this release are pro forma combined company results.</p>\n<h2>Financial Highlights</h2>\n" + SUB + PF_T),
    ("section_prose_then_subtopic", TITLE + "<h2>Financial Highlights</h2>\n<p>Amounts in this section are presented on a pro forma combined basis.</p>\n"
     "<h3>Diluted Net Earnings per Common Share</h3>\n" + SUB + PF_T),
    ("note_after_second_table", TITLE + SUB + PF_T + "<table>\n" + YEARS + row(["Net Sales", "$21,000", "$20,000"]) + "</table>\n"
     "<p>The tables above present pro forma combined company results.</p>\n"),
    ("note_before_first_table", TITLE + SUB + "<p>The tables below present pro forma combined company results.</p>\n"
     + "<table>\n" + YEARS + row(["Net Sales", "$21,000", "$20,000"]) + "</table>\n" + PF_T),
    ("after_period_heading", TITLE + SUB + PF_T + "<h3>Three Months Ended June 30, 2025</h3>\n<p>The table above presents pro forma combined company results.</p>\n"),
    ("label_after_period_heading", TITLE + SUB + PF_T + "<h4>Three Months Ended June 30, 2026</h4>\n<p>Pro Forma Combined</p>\n"),
]


@pytest.mark.parametrize("body", [b for _i, b in BOUND], ids=[i for i, _b in BOUND])
def test_w05_stretch_boundary(body):
    w, t, r, c = ws(body, slug="r16")
    assert _val(r, DIL) is None, r[DIL]


@pytest.mark.parametrize("body", [b for _i, b in BOUND], ids=[i for i, _b in BOUND])
def test_v05(body):
    _v(body, DIL, 3.40)


# ===== F (R100): unread / visible markup =====
UNREAD = [
    ("svg_text", TITLE + SUB + '<svg width="300" height="20"><text x="0" y="15">Pro Forma Combined</text></svg>\n' + PF_T),
    ("aria_hidden_visible", TITLE + SUB + '<p aria-hidden="true">Pro Forma Combined</p>\n' + PF_T),
    ("ix_exclude", TITLE + SUB + "<p>Diluted EPS <ix:exclude>Pro Forma Combined</ix:exclude></p>\n" + PF_T),
    ("nested_div_text", TITLE + SUB + "<div><div>Pro Forma Combined<div>" + PF_T + "</div></div></div>\n"),
    ("inline_b", TITLE + SUB + "<b>Pro Forma Combined</b>\n" + PF_T),
    ("br_text_div", TITLE + SUB + "<div>Pro Forma<br>Combined" + PF_T + "</div>\n"),
    ("row_gap_text", TITLE + SUB + "<table>\n" + YEARS + "Pro Forma Combined\n" + row([DILL, "$3.40", "$2.93"]) + "</table>\n"),
    ("text_after_table_in_div", TITLE + SUB + "<div>" + PF_T + "Pro Forma Combined</div>\n"),
    ("section_text", TITLE + SUB + "<section>Pro Forma Combined" + PF_T + "</section>\n"),
    ("details_summary", TITLE + SUB + "<details open><summary>Pro Forma Combined</summary></details>\n" + PF_T),
    ("dl_dt", TITLE + SUB + "<dl><dt>Pro Forma Combined</dt></dl>\n" + PF_T),
    ("font_tag", TITLE + SUB + "<font>Pro Forma Combined</font>" + PF_T),
    ("th_colspan_last", TITLE + SUB + "<table>\n" + YEARS + row([DILL, "$3.40", "$2.93"]) + '<tr><th colspan="3">Pro Forma</th></tr>\n</table>\n'),
    ("td_empty_row_text", TITLE + SUB + "<table>\n" + YEARS + row([DILL, "$3.40", "$2.93"]) + "<tr>Pro Forma Combined</tr>\n</table>\n"),
]


@pytest.mark.parametrize("body", [b for _i, b in UNREAD], ids=[i for i, _b in UNREAD])
def test_w06_markup(body):
    w, t, r, c = ws(body, slug="r16")
    assert _val(r, DIL) is None, r[DIL]


@pytest.mark.parametrize("body", [b for _i, b in UNREAD], ids=[i for i, _b in UNREAD])
def test_v06(body):
    _v(body, DIL, 3.40)


def test_c06_hidden_style_is_not_visible():
    w, t, r, c = ws(TITLE + SUB + '<p style="display:none">Pro Forma Combined</p>\n' + PF_T.replace("$3.40", "$3.07"), slug="r16")
    assert _val(r, DIL) == 3.07, r[DIL]


# ===== G: honest documents (fail-closed findings, non-blocking) =====
HONEST = [
    ("unaudited_paren", TITLE + SUB + "<p>(Amounts in millions except per share amounts; Unaudited)</p>\n" + PF_T.replace("$3.40", "$3.07")),
]


@pytest.mark.parametrize("body", [b for _i, b in HONEST], ids=[i for i, _b in HONEST])
def test_f07_honest(body):
    w, t, r, c = ws(body, slug="r16")
    assert _val(r, DIL) == 3.07, r[DIL]


# ===== X: validator surface =====
@pytest.mark.parametrize("body,needle", [
    (TITLE + SUB + PF_T + "<p>The table above presents pro forma combined company results.</p>\n", "$3.40"),
    (TITLE + SUB + "<center>Pro Forma Combined</center>\n" + PF_T, "$3.40"),
    (TITLE + SUB + "<p>The following table presents non-GAAP results.</p>\n" + PF_T, "$3.40"),
    (TITLE + SUB + "<table>\n" + YEARS + "Pro Forma Combined\n" + row([DILL, "$3.40", "$2.93"]) + "</table>\n", "$3.40"),
    (TITLE + SUB + "<div>" + PF_T + "Pro Forma Combined</div>\n", "$3.40"),
], ids=["note_after", "center", "nongaap_prose", "row_gap", "div_after"])
def test_x08_forged_present_over_refused_table(body, needle):
    w, t, r, c = ws(body, slug="r16")
    if _val(r, DIL) is not None:
        pytest.skip("table not refused")
    src = next(iter(t.values()))
    s, e = at(src, needle)
    w2, t2 = forge_present(w, src, DIL, s, e, float(needle.strip("$")), "2026-06-30")
    try:
        ok = not _refuses(w2, t2, c)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"validator raised {type(exc).__name__}: {exc}")
    assert not ok, "validator ACCEPTS a forged present value over a refused table"


@pytest.mark.parametrize("body,metric,case", [
    (TITLE + SUB + "<p>Core EPS increased 5%.</p>\n" + "<table>\n" + YEARS + row([DILL, "$3.07", "$2.93"]) + row(["Core EPS", "$3.10", "$2.95"]) + "</table>\n", DIL, Q4_FY2026),
    (T1 + "<h2>Net Sales Change Drivers FY27 vs. FY26</h2>\n" + table(), TV, Q1_FY2027),
], ids=["own_name_core", "fy_pair"])
def test_x09_forged_absence_and_honest(body, metric, case):
    w, t, r, c = ws(body, case=case, slug="r16")
    if "value" not in r[metric]:
        pytest.skip("not bound")
    try:
        validate_selected_facts(w, source_texts=t, fiscal_scope=c.scope)
    except EconomicObservationError as exc:
        pytest.fail(f"validator REFUSES the extractor's own workspace: {exc}")
    _forge_absent(w, metric, metric)
    assert _refuses(w, t, c), "validator ACCEPTS a forged absence"


@pytest.mark.parametrize("mutate", ["workspace_list", "facts_none", "fact_metric_int", "source_bytes", "source_none", "scope_none",
                                    "fact_value_str", "sources_missing", "fact_empty_dict", "scope_tuple_short"])
def test_x10_malformed_inputs_raise_only_economic_error(mutate):
    w, t, r, c = ws(TITLE + SUB + PF_T.replace("$3.40", "$3.07"), slug="r16")
    w = copy.deepcopy(w)
    scope = c.scope
    if mutate == "workspace_list":
        w = [w]
    elif mutate == "facts_none":
        w["facts"] = None
    elif mutate == "fact_metric_int":
        w["facts"][0]["metric"] = 7
    elif mutate == "source_bytes":
        t = {k: v.encode() for k, v in t.items()}
    elif mutate == "source_none":
        t = {k: None for k in t}
    elif mutate == "scope_none":
        scope = None
    elif mutate == "fact_value_str":
        for f in w["facts"]:
            if f.get("metric") == DIL:
                f["value"] = "3.07"
    elif mutate == "sources_missing":
        w.pop("sources", None)
    elif mutate == "fact_empty_dict":
        w["facts"] = [*w["facts"], {}]
    else:
        scope = tuple(scope)[:2]
    try:
        validate_selected_facts(w, source_texts=t, fiscal_scope=scope)
    except EconomicObservationError:
        return
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"validator raised {type(exc).__name__}: {exc}")
    pytest.fail("validator accepted a malformed workspace")
