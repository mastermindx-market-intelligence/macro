"""Research-notebook integrity and arithmetic, not product or investment validation.

Run beside ENERGY_R4_EVIDENCE_MODEL_2026-09-23.json using Python 3.10+.
No network access or third-party packages are used. Negative controls alter copies.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / 'ENERGY_R4_EVIDENCE_MODEL_2026-09-23.json'
OUTPUT = ROOT / 'ENERGY_R4_VERIFICATION_2026-09-23.json'
D = Decimal


def blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def invariant_failures(m: dict) -> list[str]:
    """Selected authored scope invariants; this does not authenticate sources."""
    errors = []
    sids = {s['id'] for s in m['sources']}
    if not m['authority'] or any(v is not False for v in m['authority'].values()):
        errors.append('authority')
    if any(not set(o[6]) <= sids for o in m['observations']):
        errors.append('source_reference')
    try:
        if any(not D(v).is_finite() for o in m['observations'] for v in o[5].values()):
            errors.append('finite_values')
    except (InvalidOperation, TypeError, ValueError):
        errors.append('finite_values')
    g = m['scope_guards']
    expected = {
        'definitive_means_unconditional': False,
        'all_smr_requires_haleu': False,
        'nuscale_product_fuel': 'conventional_LWR',
        'fuel_flexible_means_hydrogen_consumed': False,
        'vestas_eps_horizon': 'LTM',
        'ormat_electricity_comparator': 'prior_year_quarter',
        'orsted_consensus_panel_acquired': False,
        'point_in_time_expectations_ready': False,
        'source_truth_certified_by_arithmetic': False,
    }
    for key, value in expected.items():
        if g.get(key) != value:
            errors.append(key)
    e = {x['id']: x for x in m['events']}
    for eid, key in [('E01', 'future_warrant_cash_as_current'),
                     ('E03', 'included_in_q2_revenue'),
                     ('E04', 'site_operating_license'),
                     ('E05', 'proves_aurora_grid_operation'),
                     ('E06', 'definitive_ppa_established_by_source')]:
        if e[eid].get(key) is not False:
            errors.append(key)
    if any(e['E02'].get(k) is not None for k in
           ['quantity', 'price', 'delivered_volume', 'exact_first_delivery_date']):
        errors.append('undisclosed_contract_terms')
    o = {x[0]: x for x in m['observations']}
    if o['O18'][2] != 'reported_LTM':
        errors.append('eps_basis')
    if o['O21'][2] != 'guidance':
        errors.append('forecast_basis')
    if o['O26'][2] != 'model_assumption':
        errors.append('cost_model_basis')
    return errors


def main() -> int:
    raw = MODEL.read_bytes()
    m = json.loads(raw)
    checks = []

    def check(category: str, name: str, ok: bool, detail: object) -> None:
        checks.append({'category': category, 'name': name, 'pass': bool(ok), 'detail': detail})

    def calc(category: str, name: str, actual: Decimal, target: str | Fraction,
             note: str, tolerance: str = '0.000001') -> None:
        expected = (D(target.numerator) / D(target.denominator)
                    if isinstance(target, Fraction) else D(target))
        check(category, name, actual.is_finite() and abs(actual - expected) <= D(tolerance),
              {'actual': str(actual), 'expected': str(expected),
               'absolute_tolerance': tolerance, 'scope': note})

    sids = {s['id'] for s in m['sources']}
    cutoff = date.fromisoformat(m['research_cutoff'])
    check('integrity', 'source_ids_and_urls_unique',
          len(sids) == len(m['sources']) == len({s['url'] for s in m['sources']}),
          len(m['sources']))
    check('integrity', 'https_locators',
          all(urlparse(s['url']).scheme == 'https' for s in m['sources']),
          'Locator syntax only; not an HTTP test')
    check('integrity', 'known_publication_dates_not_after_cutoff',
          all(s['date'] is None or date.fromisoformat(s['date']) <= cutoff for s in m['sources']),
          m['research_cutoff'])
    for group, first_column in [('observations', True), ('company_cases', True),
                                ('requirements', True), ('events', False)]:
        ids = [r[0] if first_column else r['id'] for r in m[group]]
        check('integrity', group + '_unique_ids', len(ids) == len(set(ids)), len(ids))
    check('integrity', 'observation_row_shape', all(len(o) == 8 for o in m['observations']),
          'Named eight-column research rows')
    check('integrity', 'company_and_event_sources_resolve',
          all(set(c[3]) <= sids for c in m['company_cases']) and
          all(set(e['sources']) <= sids for e in m['events']), 'No invented source reference')
    check('integrity', 'unresolved_identities_and_weights_preserved',
          all(c[4] is None and c[5] is None for c in m['company_cases']),
          'Research descriptions are not admitted securities or measured weights')
    check('integrity', 'no_product_or_prediction_completion',
          m['application_tests_run'] == 0 and m['predictive_backtests_run'] == 0 and
          m['mission_complete'] is False, 'Research scope only')
    check('integrity', 'requirements_have_unique_coverage',
          {r[0] for r in m['requirements']} == {f'A{i:02}' for i in range(1, 51)},
          '50 proposals, not 50 executed application tests')
    check('integrity', 'selected_scope_invariants', not invariant_failures(m), invariant_failures(m))
    e = {x['id']: x for x in m['events']}
    check('integrity', 'closing_evidence_clock_preserved',
          date.fromisoformat(e['E01']['event_date']) < date.fromisoformat(e['E01']['knowledge_date']),
          'Participant confirmation was published after closing')
    check('integrity', 'cashless_warrant_terms_retained',
          'cashless' in next(s for s in m['sources'] if s['id'] == 'S05')['scope'].lower(),
          'No unconditional future exercise-cash assumption')
    check('integrity', 'source_truth_is_not_arithmetic_proof',
          m['scope_guards']['source_truth_certified_by_arithmetic'] is False,
          'Numbers and scope checks cannot certify issuer claims')

    o = {r[0]: {k: D(v) for k, v in r[5].items()} for r in m['observations']}
    cat = 'source_arithmetic'
    calc(cat, 'cameco_current_unit_spread', o['O01']['price']-o['O01']['cost'], '8.61',
         'CAD/kgU blended measure including depreciation, not EBITDA/unit')
    calc(cat, 'cameco_prior_unit_spread', o['O01']['prior_price']-o['O01']['prior_cost'], '9.47',
         'Prior-year comparison, not a spot conversion quote')
    calc(cat, 'cameco_unit_spread_change_percent',
         ((o['O01']['price']-o['O01']['cost'])/(o['O01']['prior_price']-o['O01']['prior_cost'])-1)*100,
         Fraction(-8600, 947), 'Derived from rounded reported unit metrics')
    calc(cat, 'cameco_uranium_sales_categories', o['O03']['uranium_fixed']+o['O03']['uranium_market'],
         '658721', 'CAD thousand revenue, not volume exposure')
    calc(cat, 'cameco_fuel_sales_categories', o['O03']['fuel_fixed']+o['O03']['fuel_market'],
         '151940', 'CAD thousand revenue, not price delta')
    calc(cat, 'cameco_consolidated_sales', o['O03']['uranium_total']+o['O03']['fuel_total']+o['O03']['other'],
         '813772', 'CAD thousand, do not add equity-method investee sales')
    calc(cat, 'westinghouse_sales_elimination', sum(o['O04'].values()), '0',
         'Displayed investee sales eliminated in presentation')
    calc(cat, 'centrus_backlog_segment_sum', o['O05']['leu']+o['O05']['technical'], '4.5',
         'USD billion; no claim total is funded')
    check(cat, 'centrus_nested_contingencies',
          o['O05']['definitive_within_contingent'] <= o['O05']['contingent_within_leu'] <= o['O05']['leu'],
          'Definitive subset is inside contingent subset; not additive')
    calc(cat, 'centrus_common_and_prefunded_underlying', o['O06']['common']+o['O06']['prefunded'],
         '2505513', 'Underlying share count diagnostic; distinct instruments retained')
    calc(cat, 'bwxt_segment_sum_gap', o['O08']['government']+o['O08']['commercial']-o['O08']['consolidated'],
         '2.2', 'USD million; no forced equality or inferred organic growth')
    calc(cat, 'bwxt_government_operating_income_delta', o['O09']['current']-o['O09']['prior'],
         '-3.7', 'USD million, not a revenue-growth proxy')
    calc(cat, 'first_solar_historical_transfer_discount', o['O10']['face']-o['O10']['proceeds'],
         '33.8', 'USD million, historical transaction')
    calc(cat, 'first_solar_historical_transfer_discount_percent',
         (1-o['O10']['proceeds']/o['O10']['face'])*100, Fraction(33800, 7019),
         'Not a current transfer-market quote')
    calc(cat, 'first_solar_single_benefit_diagnostic', o['O11']['gross_profit']-o['O11']['refund_effect'],
         '516.404', 'USD million; not a full normalized earnings counterfactual')
    calc(cat, 'enphase_timing_excluded_current', o['O12']['revenue']-o['O12']['safe_harbor'], '207.6',
         'Rounded USD million; not sell-through')
    calc(cat, 'enphase_timing_excluded_prior', o['O12']['prior_revenue']-o['O12']['prior_safe_harbor'], '248.4',
         'Rounded USD million; not official organic revenue')
    calc(cat, 'enphase_timing_excluded_change_percent',
         ((o['O12']['revenue']-o['O12']['safe_harbor'])/(o['O12']['prior_revenue']-o['O12']['prior_safe_harbor'])-1)*100,
         Fraction(-3400, 207), 'Diagnostic only')
    calc(cat, 'enphase_refund_recognition_allocation',
         o['O13']['gross_profit']+o['O13']['interest_income']+o['O13']['inventory'], '52',
         'USD million; multiple financial-statement effects')
    calc(cat, 'enphase_refund_cash_timing', o['O13']['q2_received']+o['O13']['later_received'], '52',
         'USD million; two different receipt periods')
    calc(cat, 'enphase_reported_cash_bridge', o['O14']['cfo']-o['O14']['capex'], '25.9',
         'USD million including timing effects')
    calc(cat, 'vestas_backlog_sum', o['O15']['turbine']+o['O15']['service'], '76.9',
         'EUR billion, not annual profit')
    calc(cat, 'vestas_warranty_rollforward', o['O17']['opening']+o['O17']['provision']-o['O17']['consumed'],
         '1821', 'EUR million; consumption is not automatically cash or earnings release')
    calc(cat, 'vestas_warranty_income_charge', o['O17']['provision']+o['O17']['supplier_adjustment'],
         '260', 'EUR million, separate from closing liability')
    calc(cat, 'orsted_reported_cash_bridge', o['O19']['cfo']-o['O19']['gross_investment']+o['O19']['divestments'],
         '364', 'DKK million including divestments')
    calc(cat, 'orsted_no_disposal_diagnostic', o['O19']['cfo']-o['O19']['gross_investment'],
         '-9137', 'DKK million; not alternative issuer-defined FCF')
    calc(cat, 'fluence_revenue_guidance_delta_percent',
         (o['O21']['new_revenue']/o['O21']['old_revenue']-1)*100, '-20', 'Management estimate revision')
    calc(cat, 'fluence_loss_guidance_absolute_delta', o['O21']['new_adjusted_ebitda']-o['O21']['old_adjusted_ebitda'],
         '-190', 'USD million; do not label percentage earnings growth across negative bases')
    calc(cat, 'ormat_storage_gross_profit', o['O22']['revenue']-o['O22']['cost'], '24044',
         'USD thousand; mix and capacity changed')
    calc(cat, 'ormat_product_gross_profit', o['O24']['revenue']-o['O24']['cost'], '4522',
         'USD thousand; not storage-owner economics')
    calc(cat, 'plug_rounded_fuel_gross_contribution', o['O25']['fuel_revenue']*o['O25']['fuel_margin'],
         '-18.72', 'Approximate USD million; rounded-input product only')
    calc(cat, 'plug_rounded_service_gross_contribution', o['O25']['service_revenue']*o['O25']['service_margin'],
         '8.10', 'Approximate USD million; not total corporate profit')

    h = {k: {x: D(v) for x, v in row.items()} for k, row in m['hypothetical_inputs'].items()}
    b, f, d, t, liq = [h[k] for k in ['battery', 'fair_price_financing', 'developer', 'duration', 'liquidity']]
    cat = 'hypothetical_arithmetic'
    energy_in = b['usable_mwh']/b['efficiency']
    annual = (b['usable_mwh']*b['sell_price']-energy_in*b['charge_price'])*b['cycles']
    compressed = (b['usable_mwh']*b['compressed_sell']-energy_in*b['compressed_charge'])*b['cycles']
    calc(cat, 'battery_duration', b['usable_mwh']/b['mw'], '4', 'Hours; usable energy assumption')
    calc(cat, 'battery_charge_input', energy_in, Fraction(4000, 9), 'MWh per cycle, loss-aware')
    calc(cat, 'battery_base_annual_contribution', annual, '6800000', 'USD before all other costs, not a market forecast')
    calc(cat, 'battery_compressed_annual_contribution', compressed, Fraction(7600000, 3),
         'Same hardware, hypothetical compressed spreads')
    calc(cat, 'battery_contribution_change_percent', (compressed/annual-1)*100, Fraction(-3200, 51),
         'No assertion of feasible market dispatch')
    hy = h['hydrogen']
    calc(cat, 'hydrogen_low_power_cost', hy['kwh_per_kg']*hy['electricity_low_usd_mwh']/1000, '2.2',
         'USD/kg electricity only, not a named plant')
    calc(cat, 'hydrogen_high_power_cost', hy['kwh_per_kg']*hy['electricity_high_usd_mwh']/1000, '4.4',
         'Excludes capex, utilization, delivery and credits')
    pre_price = f['pre_money']/f['old_shares']
    issued = f['raise']/pre_price
    calc(cat, 'fair_price_financing_shares_issued', issued, '25', 'Hypothetical common-stock raise, no warrants or fees')
    calc(cat, 'fair_price_financing_post_price', (f['pre_money']+f['raise'])/(f['old_shares']+issued),
         '2', 'Fair-value issue alone does not mechanically reduce per-share value')
    calc(cat, 'fair_price_financing_old_fraction', f['old_shares']/(f['old_shares']+issued), '.8',
         'Ownership percentage, not automatic loss in wealth')
    calc(cat, 'lower_cost_project_cash_on_cost_percent', d['annual_cash']/d['lower_capital']*100,
         Fraction(200, 17), 'Simple cash-on-cost, not IRR')
    calc(cat, 'competitive_project_cash_on_cost_percent', d['competitive_cash']/d['lower_capital']*100,
         Fraction(160, 17), 'Capital savings may be competed away; hypothetical')
    pv = sum(t['annual_cash']/(1+t['discount'])**y for y in range(1, int(t['years'])+1))
    delayed = pv/(1+t['discount'])**int(t['delay_years'])
    calc(cat, 'ten_year_cash_present_value', pv, '614.456710570468', 'No terminal value, hypothetical units')
    calc(cat, 'two_year_delayed_cash_present_value', delayed, '507.815463281379', 'Timing only; no project forecast')
    calc(cat, 'delay_value_change_percent', (delayed/pv-1)*100, Fraction(-2100, 121),
         'Costs and risk held constant solely for illustration')
    available = liq['cash']-liq['restricted']-liq['committed_before_revenue']
    calc(cat, 'liquidity_after_stated_commitments', available, '70', 'Hypothetical funding budget')
    calc(cat, 'funding_budget_quarters', available/liq['quarterly_operating_burn'], Fraction(14, 3),
         'Static illustrative coverage, not company runway')

    mutations = [
        ('trade_authority', lambda x: x['authority'].__setitem__('trade', True), 'authority'),
        ('invalid_source', lambda x: x['observations'][0].__setitem__(6, ['MISSING']), 'source_reference'),
        ('nonfinite_value', lambda x: x['observations'][0][5].__setitem__('price', 'NaN'), 'finite_values'),
        ('conditional_backlog', lambda x: x['scope_guards'].__setitem__('definitive_means_unconditional', True), 'definitive_means_unconditional'),
        ('universal_haleu', lambda x: x['scope_guards'].__setitem__('all_smr_requires_haleu', True), 'all_smr_requires_haleu'),
        ('fuel_capability_as_demand', lambda x: x['scope_guards'].__setitem__('fuel_flexible_means_hydrogen_consumed', True), 'fuel_flexible_means_hydrogen_consumed'),
        ('eps_horizon', lambda x: x['scope_guards'].__setitem__('vestas_eps_horizon', 'quarter'), 'vestas_eps_horizon'),
        ('unacquired_consensus', lambda x: x['scope_guards'].__setitem__('point_in_time_expectations_ready', True), 'point_in_time_expectations_ready'),
        ('future_warrant_cash', lambda x: x['events'][0].__setitem__('future_warrant_cash_as_current', True), 'future_warrant_cash_as_current'),
        ('postquarter_acquisition', lambda x: x['events'][2].__setitem__('included_in_q2_revenue', True), 'included_in_q2_revenue'),
        ('design_as_operating_license', lambda x: x['events'][3].__setitem__('site_operating_license', True), 'site_operating_license'),
        ('wrong_reactor_proof', lambda x: x['events'][4].__setitem__('proves_aurora_grid_operation', True), 'proves_aurora_grid_operation'),
        ('guidance_as_actual', lambda x: x['observations'][20].__setitem__(2, 'actual'), 'forecast_basis'),
        ('cost_model_as_observed', lambda x: x['observations'][25].__setitem__(2, 'reported'), 'cost_model_basis'),
    ]
    for name, change, expected_error in mutations:
        bad = copy.deepcopy(m)
        change(bad)
        errors = invariant_failures(bad)
        check('negative_control', name, expected_error in errors,
              {'expected_rejection': expected_error, 'observed_rejections': errors})

    failures = [c for c in checks if not c['pass']]
    script = Path(__file__).read_bytes()
    result = {
        'artifact_type': 'research_integrity_and_arithmetic_receipt',
        'model_file': MODEL.name, 'model_sha256': hashlib.sha256(raw).hexdigest(),
        'model_git_blob': blob(raw), 'verifier_file': Path(__file__).name,
        'verifier_sha256': hashlib.sha256(script).hexdigest(), 'verifier_git_blob': blob(script),
        'counts': dict(Counter(c['category'] for c in checks)),
        'passed': len(checks)-len(failures), 'failed': len(failures),
        'application_tests_run': 0, 'predictive_backtests_run': 0,
        'full_source_link_test': False,
        'claim_limit': 'Selected notebook invariants and arithmetic only. Not source-truth certification, complete legal/contract review, production behavior, rights admission, causal validation or investment merit.',
        'checks': checks,
    }
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'checks'}, indent=2))
    if failures:
        print(json.dumps(failures, indent=2))
    return int(bool(failures))


if __name__ == '__main__':
    with localcontext() as context:
        context.prec = 36
        raise SystemExit(main())
