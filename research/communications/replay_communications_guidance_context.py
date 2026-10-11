"""Fixed research counterexamples; not a disclosure parser or product selector.

All statement annotations below are AUTHOR-SUPPLIED. Their correctness is not
proved by this experiment. No original transcript text, native owner, network,
model, identity, source retention, or private-data interface is read. Only an
explicit --output destination is written. Source IDs refer to the accompanying
COMMUNICATIONS_GUIDANCE_REVISION_QUALIFICATION_2026-09-24.md study.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal as D
import json
from pathlib import Path

# Case IDs are research labels, never native event or security identities.
STATEMENTS = (
    {"case": "GC01", "source": "S15", "issued": "2026-01-26",
     "outer_speaker": "issuer", "origin": "issuer", "act": "reaffirm",
     "target": "Q4_2025", "measure": "revenue", "bound": "floor",
     "amount": "840", "unit": "USD_million", "expected_outlook": True},
    {"case": "GC02", "source": "S11", "issued": "2026-06-04",
     "outer_speaker": "customer", "origin": "customer", "act": "testimonial",
     "target": None, "measure": None, "bound": None,
     "amount": None, "unit": None, "expected_outlook": False},
    {"case": "GC03", "source": "S17", "issued": "2026-08-26",
     "outer_speaker": "issuer", "origin": "quoted_analyst", "act": "question",
     "target": "Q4_2026", "measure": "revenue", "bound": None,
     "amount": None, "unit": None, "expected_outlook": False},
    {"case": "GC04", "source": "S17", "issued": "2026-08-26",
     "outer_speaker": "issuer", "origin": "issuer", "act": "reaffirm",
     "target": "Q3_2026", "measure": "revenue", "bound": None,
     "amount": None, "unit": None, "expected_outlook": True},
    {"case": "GC05", "source": "S16", "issued": "2026-08-26",
     "outer_speaker": "issuer", "origin": "issuer", "act": "new_component",
     "target": "Q3_2026", "measure": "additional_legal_expense", "bound": "approximate",
     "amount": "10000", "unit": "USD_million", "expected_outlook": True},
    {"case": "GC06", "source": "S17", "issued": "2026-08-26",
     "outer_speaker": "issuer", "origin": "issuer", "act": "not_provided",
     "target": "BEYOND_Q3_2026", "measure": "revenue", "bound": None,
     "amount": None, "unit": None, "expected_outlook": False},
    {"case": "GC07", "source": "S12", "issued": "2026-04-29",
     "outer_speaker": "issuer", "origin": "issuer", "act": "included_assumption",
     "target": "Q2_2026", "measure": "revenue", "bound": None,
     "amount": None, "unit": None, "expected_outlook": False},
    {"case": "GC08", "source": "S08", "issued": "2026-07-28",
     "outer_speaker": "issuer", "origin": "issuer", "act": "project_announcement",
     "target": "FUTURE_INFRASTRUCTURE", "measure": "project_commitment",
     "bound": None, "amount": None, "unit": None, "expected_outlook": False},
)

CONFERENCES = (
    ("Needham", "2026-05-13", "2026-05-13", 90),
    ("B. Riley", "2026-05-20", "2026-05-21", None),
    ("RBCCM", "2026-05-27", "2026-05-27", None),
    ("Craig-Hallum", "2026-05-28", "2026-05-28", None),
    ("Bank of America", "2026-06-02", "2026-06-02", None),
    ("Rothschild & Co Redburn", "2026-06-03", "2026-06-03", None),
    ("Evercore", "2026-06-03", "2026-06-03", 90),
    ("Roth AdTech Summit", "2026-06-15", "2026-06-15", None),
)


def run_reference() -> dict:
    checks: list[str] = []

    def check(name: str, condition: bool) -> None:
        if not condition:
            raise AssertionError(name)
        if name in checks:
            raise AssertionError("duplicate_check_name: " + name)
        checks.append(name)

    # Deliberately simple semantics over manually annotated records, NOT text.
    recognized_acts = {"issue", "reaffirm", "new_component"}
    observed = {}
    for row in STATEMENTS:
        got = row["origin"] == "issuer" and row["act"] in recognized_acts
        observed[row["case"]] = got
        check(row["case"] + "_annotation_interpretation", got == row["expected_outlook"])
    check("one_research_id_per_statement", len({r['case'] for r in STATEMENTS}) == 8)

    # The CFO reads the analyst's premise; outer speaker alone yields a false hit.
    nested = STATEMENTS[2]
    check("outer_speaker_alone_false_positive", nested["outer_speaker"] == "issuer" and not observed['GC03'])
    check("correct_reply_targets_Q3", STATEMENTS[3]["target"] == "Q3_2026")
    check("no_admitted_Q4_reaffirmation", not any(
        observed[r['case']] and r['target'] == 'Q4_2026' for r in STATEMENTS))
    # The annotation-only example CANNOT detect a falsely rewritten annotation.
    changed = dict(nested, origin="issuer", act="reaffirm")
    annotation_fools_toy = changed['origin'] == 'issuer' and changed['act'] in recognized_acts
    check("annotation_blind_spot_is_exposed", annotation_fools_toy)

    # An actual reaffirmation in a corporate notice has the wrong financial target.
    check("corporate_notice_has_outlook", observed['GC01'])
    check("calendar_year_is_not_target_year", STATEMENTS[0]['issued'].startswith('2026') and
          STATEMENTS[0]['target'] == 'Q4_2025')
    check("no_Q2_numeric_replacement_from_selected_context_cases", not any(
        observed[r['case']] and r['target'] == 'Q2_2026' for r in STATEMENTS))

    # This is selection within a FIXED PARTIAL sample, never a no-change proof.
    coverage = {name: {'original_located': name != 'Alphabet', 'history_complete': False}
                for name in ('Meta', 'Alphabet', 'The Trade Desk', 'Magnite')}
    check("four_company_denominator_retained", len(coverage) == 4)
    check("three_original_guides_not_four", sum(r['original_located'] for r in coverage.values()) == 3)
    check("zero_final_pre_result_certifications", not any(r['history_complete'] for r in coverage.values()))
    check("no_change_not_inferred_from_empty_sample", not any(
        r['history_complete'] and not observed['GC02'] for r in coverage.values()))

    # Statement issue date and event date are different discovery dimensions.
    start, end = date(2026, 5, 6), date(2026, 8, 5)
    notice = date(2026, 4, 30)
    check("notice_precedes_investigation_window", notice < start)
    for name, first, last, _days in CONFERENCES:
        check("in_window_event_" + name, start <= date.fromisoformat(first) <=
              date.fromisoformat(last) < end)
    replay_windows = {name: (date.fromisoformat(last) + timedelta(days=days)).isoformat()
                      for name, _first, last, days in CONFERENCES if days is not None}
    check("only_two_advertised_90_day_replays", len(replay_windows) == 2)
    check("Needham_nominal_window_end", replay_windows['Needham'] == '2026-08-11')
    check("Evercore_nominal_window_end", replay_windows['Evercore'] == '2026-09-01')
    research_day = date(2026, 9, 24)
    check("advertised_windows_elapsed", all(date.fromisoformat(x) < research_day for x in replay_windows.values()))
    # Actual remote availability was not measured by calendar arithmetic.
    replay_deleted = {name: None for name in replay_windows}
    check("deletion_stays_unknown", all(v is None for v in replay_deleted.values()))

    # Same-day date strings cannot establish pre-result ordering.
    result_day = date(2026, 7, 29)
    dates = (('2026-07-28', 'before_day'), ('2026-07-29', 'same_day_unknown'),
             ('2026-07-30', 'after_day'))
    for raw, expected in dates:
        d = date.fromisoformat(raw)
        status = 'before_day' if d < result_day else 'after_day' if d > result_day else 'same_day_unknown'
        check('day_grain_' + raw, status == expected)
    check("index_and_source_dates_not_forced_equal", date(2026, 8, 25) != date(2026, 8, 26))

    # A scoped financial update need not overwrite every other guided measure.
    baseline = {'Q3_revenue': {'source': 'S02', 'status': 'original_range'},
                'annual_expense': {'source': 'S02', 'status': 'original_range'}}
    revised = deepcopy(baseline)
    revised['Q3_revenue']['status'] = 'reaffirmed_by_S17'
    revised['additional_Q3_expense'] = {'source': 'S16', 'status': 'approximate_component'}
    revised['annual_expense']['status'] = 'original_range_excludes_new_component'
    check("baseline_not_overwritten", baseline['annual_expense']['status'] == 'original_range')
    check("revenue_reaffirmation_not_expense_reaffirmation", revised['Q3_revenue']['status'] != revised['annual_expense']['status'])
    check("no_invented_annual_range_endpoints", all('value' not in r for r in revised.values()))
    check("approximate_expense_not_cash_paid", STATEMENTS[4]['bound'] == 'approximate' and
          STATEMENTS[4]['measure'] == 'additional_legal_expense')

    # Synthetic counterfactual: adjust the changed assumption, not the full old risk.
    unaffected, included, new_risk = D('110'), D('5'), D('8')
    baseline_value = unaffected - included
    scenario_value = baseline_value - (new_risk - included)
    check("synthetic_included_baseline", baseline_value == D('105'))
    check("synthetic_double_deduction_is_wrong", baseline_value - included != baseline_value)
    check("synthetic_incremental_adjustment", scenario_value == D('102'))
    check("synthetic_counterfactual_equivalence", scenario_value == unaffected - new_risk)
    # Two invented PV/prior-accrual pairs give the same incremental accrual.
    check("net_accrual_does_not_identify_total_PV", D('12')-D('2') == D('11')-D('1') == D('10'))
    check("different_PV_still_possible", D('12') != D('11'))

    return {'research_only': True, 'reference_checks_passed': len(checks),
            'case_ids': [r['case'] for r in STATEMENTS], 'checks': checks,
            'conference_count': len(CONFERENCES), 'nominal_replay_window_ends': replay_windows,
            'final_pre_result_certified': [], 'source_history_complete': False,
            'annotation_blind_spot_demonstrated': annotation_fools_toy,
            'product_tests_run': 0, 'native_reads': 0, 'network_requests': 0,
            'limitations': ['manual annotations are inputs, not validated extraction',
                            'fixed sample does not certify complete disclosure history',
                            'no original source or native clock/identity/rights proof',
                            'synthetic arithmetic is not an issuer forecast']}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='optional local JSON result file')
    args = parser.parse_args()
    receipt = run_reference()
    body = json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body, encoding='utf-8')
    print(f"{receipt['reference_checks_passed']} reference checks passed; 0 product tests; history incomplete")


if __name__ == '__main__':
    main()
