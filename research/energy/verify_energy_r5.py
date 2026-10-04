"""Research-notebook checks only; no network, product tests or return backtest.

Run beside the R5 model and dossier with Python 3.10+. Negative controls mutate
copies. A rejected bad notebook is not a validated investment signal.
"""
from __future__ import annotations
import copy
import hashlib
import json
import re
from datetime import date
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from statistics import median
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / 'ENERGY_R5_EXPECTATIONS_GLOBAL_MODEL_2026-09-23.json'
DOC = ROOT / 'ENERGY_R5_EXPECTATIONS_GLOBAL_RESEARCH_2026-09-23.md'
OUT = ROOT / 'ENERGY_R5_VERIFICATION_2026-09-23.json'
D = Decimal

def digest(path: Path) -> dict:
    raw = path.read_bytes()
    return {'file':path.name, 'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest(),
            'git_blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}

def audit(m: dict) -> list[str]:
    errors = []
    def require(ok: bool, label: str) -> None:
        if not ok: errors.append(label)
    require(all(v is False for v in m['authority'].values()), 'authority')
    require(m['application_tests_run'] == 0 and m['predictive_backtests_run'] == 0
            and m['mission_complete'] is False, 'scope')
    sources = m['sources']; sids = {s['id'] for s in sources}
    require(len(sids) == len(sources), 'source_id')
    require(len({s['url'] for s in sources}) == len(sources), 'source_url')
    require(all(urlparse(s['url']).scheme == 'https' for s in sources), 'https')
    cutoff = date.fromisoformat(m['research_cutoff'])
    require(all(s['date'] is None or date.fromisoformat(s['date']) <= cutoff for s in sources), 'source_date')
    require(all('input_date' not in s or date.fromisoformat(s['input_date']) <= cutoff for s in sources), 'input_date')
    for key in ['observations','cases','requirements','gaps']:
        require(len({r[0] for r in m[key]}) == len(m[key]), key+'_id')
    require(all(set(r[6]) <= sids for r in m['observations']), 'observation_source')
    require(all(set(r[3]) <= sids for r in m['cases']), 'case_source')
    require(all(D(v).is_finite() for r in m['observations'] for v in r[5].values()), 'finite_values')
    require(all(r[2] and r[3] and r[4] for r in m['observations']), 'observation_scope')
    v = m['valuation_case']; e = m['expectations_status']
    require(e['selected_values_acquired'] is True and e['independent_historical_vintages'] is False
            and e['native_admission'] is False and e['matched_fixed_horizon_backtest'] is False
            and e['priced_in_verdict'] is None, 'historical_admission')
    require(v['mode'] == 'MIXED_CLOCK_REFERENCE_NOT_CURRENT_OR_PIT', 'quote_mode')
    require(v['estimate_first_publication'] is None, 'invented_publication')
    require(v['quote_asof'] == '2026-09-15T12:12:00+02:00' and v['balance_asof'] == '2026-06-30', 'clock')
    require(v['quote_share_basis'] == 'issued_count_reference', 'share_basis')
    require(v['NCI_and_hybrid_basis'] == 'book_values_for_sensitivity_only', 'claim_basis')
    require(v['claims_complete'] is False and v['forecast_metric_mapping_complete'] is False
            and all(v[k] is None for k in ['EV_market_value','EV_EBITDA','fair_value']), 'incomplete_valuation')
    o = {r[0]:r for r in m['observations']}
    require('post-Q2' in o['O09'][3], 'post_result')
    require('crore' in o['O18'][4] and o['O18'][5]['rupees_per_crore'] == '10000000', 'crore')
    require(o['O16'][5]['ordinary_per_ADS'] == '4', 'ADS')
    require(o['O07'][5]['lease_already_in_debt'] == '10273', 'lease')
    require('other_interest_bearing_debt_addback' in o['O08'][5]
            and 'other_interest_bearing_receivables_addback' in o['O08'][5]
            and 'gas_inventory' not in o['O08'][5], 'debt_note_labels')
    require(o['O21'][5]['actual_operating_aftertax_rounded'] == '3440'
            and o['O21'][5]['actual_adjusted_net_income_rounded'] == '3220', 'operating_vs_net')
    require('London South East' in next(s for s in sources if s['id']=='S15')['publisher'], 'publisher_identity')
    return errors

def main() -> None:
    m = json.loads(MODEL.read_text(encoding='utf-8')); checks = []
    def check(name: str, ok: bool, category: str, detail: object) -> None:
        checks.append({'name':name,'pass':bool(ok),'category':category,'detail':detail})
    def calc(name: str, actual: Decimal, numerator: int, denominator: int = 1,
             category: str = 'source_arithmetic', note: str = '') -> None:
        f = Fraction(numerator, denominator)
        with localcontext() as ctx:
            ctx.prec = 45
            expected = D(f.numerator) / D(f.denominator)
            ok = abs(actual - expected) <= D('0.00000001')
        check(name, ok, category, {'actual':str(actual),'independent_fraction':str(f),'note':note})
    errors = audit(m)
    check('model_invariants', not errors, 'integrity', errors)
    check('expected_coverage', [len(m[k]) for k in ['sources','observations','cases','requirements','gaps']]
          == [20,22,11,45,6], 'integrity', 'Research coverage only')
    doc = DOC.read_text(encoding='utf-8')
    check('dossier_source_refs', set(re.findall(r'\bS\d{2}\b',doc)) <= {s['id'] for s in m['sources']},
          'integrity','Local source references resolve; not an HTTP-link check')
    check('dossier_case_names', all(r[1] in doc for r in m['cases']), 'integrity','All named cases present')
    check('dossier_no_placeholder', not re.search(r'\b(TODO|TBD|PLACEHOLDER)\b',doc), 'integrity','No placeholder marker')
    check('rights_preserved', 'not a copied full analyst panel' in m['rights'], 'integrity','No native data license inferred')
    check('method_differences', all(t in doc for t in ['trimmed mean','independently','post-Q2']), 'integrity','Methods remain distinct')
    o = {r[0]:{k:D(v) for k,v in r[5].items()} for r in m['observations']}
    growth = lambda new,old: (new/old-1)*100
    calc('Orsted_EBITDA_labelled_variance',growth(o['O04']['EBITDA_reported'],o['O01']['EBITDA_reported']),32000,5103,note='Not qualified PIT surprise')
    calc('Orsted_PAT_labelled_variance',growth(o['O04']['group_PAT'],o['O01']['PAT']),-67700,1364,note='Group PAT, not owner PAT')
    calc('Orsted_PAT_ownership',o['O04']['owners_PAT']+o['O04']['NCI_PAT'],687)
    calc('Orsted_nonadditive_median_gap',o['O02']['EBITDA_total']-o['O02']['partnerships']-o['O02']['EBITDA_ex_partnerships'],148,note='Preserve; not a source accounting error')
    calc('Orsted_quote_capitalization',o['O05']['price']*o['O05']['issued_shares'],169972081532,note='DKK, not millions of the displayed full number')
    calc('Orsted_capital_increase',o['O06']['old']+o['O06']['new'],1321197680)
    calc('Orsted_reported_net_debt',o['O07']['debt']-o['O07']['interest_bearing_assets'],21960)
    calc('Orsted_adjusted_net_debt',sum(v for k,v in o['O08'].items() if k!='adjusted_net_debt'),33931,note='Issuer convention, not EV')
    calc('Orsted_book_claim_sum',o['O07']['hybrid_book']+o['O07']['NCI_book'],29287,note='Book sensitivity only; not market valuation')
    calc('Orsted_incomplete_equity_plus_netdebt',o['O05']['displayed_marketcap']/D(1000000)+o['O07']['reported_net_debt'],191932081532,1000000,note='Mixed-clock partial bridge, not enterprise value')
    calc('Vestas_ratio_of_means',o['O09']['EBIT_before_special']/o['O09']['revenue']*100,181300,21417,note='Not mean analyst margin')
    calc('VERBUND_realized_price_change',growth(o['O10']['realized_current'],o['O10']['realized_prior']),-31000,1172)
    calc('VERBUND_hydro_coefficient_change',growth(o['O10']['hydro_current'],o['O10']['hydro_prior']),-800,76)
    calc('VERBUND_equity_capital_change',growth(o['O12']['marketcap_current'],o['O12']['marketcap_prior']),-3317800,226341,note='Not a shareholder total return')
    calc('VERBUND_partial_claim_change',growth(o['O12']['marketcap_current']+o['O12']['netdebt_current'],o['O12']['marketcap_prior']+o['O12']['netdebt_prior']),-196830,25102,note='Marketcap plus reported net debt, not full EV')
    calc('VERBUND_H1_EBITDA_change',growth(o['O12']['EBITDA_H1_current'],o['O12']['EBITDA_H1_prior']),-35150,1413)
    calc('Neste_comparable_EBITDA_change',growth(o['O13']['EBITDA_current'],o['O13']['EBITDA_prior']),86200,341)
    calc('Neste_cash_before_financing_change',growth(o['O13']['cash_before_financing_current'],o['O13']['cash_before_financing_prior']),-6200,226)
    calc('Veolia_energy_growth_basis_difference',o['O14']['energy_growth_ex_price']-o['O14']['energy_organic_growth'],21,10,note='Percentage points, not EBITDA effect')
    calc('Jinko_margin_change_pp',o['O15']['gross_margin_current']-o['O15']['gross_margin_prior'],-41,10)
    calc('Jinko_parent_loss_magnitude_change',growth(o['O15']['parent_loss_current'],o['O15']['parent_loss_prior']),233800,4635,note='Increasing loss magnitude, not positive earnings growth')
    calc('Jinko_disposal_interests',o['O16']['US_interest_sold']+o['O16']['retained_equity_method'],100)
    calc('Jinko_ADS_rounding_gap',o['O16']['loss_per_ordinary']*o['O16']['ordinary_per_ADS']-o['O16']['loss_per_ADS'],1,100,note='Rounded values; not an accounting error')
    calc('Kaz_revenue_change',growth(o['O17']['revenue_current'],o['O17']['revenue_prior']),5766700,660167)
    calc('Kaz_adjusted_EBITDA_change',growth(o['O17']['adjusted_EBITDA_current'],o['O17']['adjusted_EBITDA_prior']),814100,363111)
    calc('Kaz_attributable_EBITDA_change',growth(o['O17']['attributable_EBITDA_current'],o['O17']['attributable_EBITDA_prior']),-3756800,302408)
    calc('Kaz_owner_profit_change',growth(o['O17']['owners_profit_current'],o['O17']['owners_profit_prior']),-4551300,202068)
    calc('Kaz_operating_cash_change',growth(o['O17']['CFO_current'],o['O17']['CFO_prior']),-29328000,532870)
    calc('NTPC_standalone_growth',growth(o['O18']['standalone_PAT_current'],o['O18']['standalone_PAT_prior']),56700,4775)
    calc('NTPC_group_growth',growth(o['O18']['group_PAT_current'],o['O18']['group_PAT_prior']),78800,6108)
    calc('NTPC_crore_scale',o['O18']['standalone_PAT_current']*o['O18']['rupees_per_crore'],53420000000)
    calc('CNQ_total_capital_revision',o['O19']['total_current']-o['O19']['total_prior'],761)
    calc('CNQ_direct_cash_distribution',o['O20']['dividends']+o['O20']['buybacks'],12,5,note='CAD billion; debt reduction not included')
    calc('CNQ_inclusive_label_gap',o['O20']['issuer_inclusive_returns']-o['O20']['dividends']-o['O20']['buybacks'],8,5,note='Debt reduction, not additional cash distribution')
    calc('Equinor_constructed_aftertax',o['O21']['consensus_operating_pretax']-o['O21']['consensus_tax'],3380)
    calc('Equinor_operating_aftertax_variance',growth(o['O21']['actual_operating_aftertax_rounded'],o['O21']['consensus_operating_aftertax']),6000,3380,note='Rounded actual, not exact historical surprise')
    calc('Equinor_EPS_variance',growth(o['O21']['actual_EPS'],o['O21']['consensus_EPS']),-100,134)
    calc('Repsol_nonadditive_consensus_gap',sum(v for k,v in o['O22'].items() if k!='group_adjusted_net')-o['O22']['group_adjusted_net'],2,note='Source explains different samples')

    s = m['synthetics']; old={k:D(v) for k,v in s['panel_old'].items()}; new={k:D(v) for k,v in s['panel_new'].items()}
    calc('synthetic_panel_raw_change',growth(sum(new.values())/len(new),sum(old.values())/len(old)),2000,110,'hypothetical_arithmetic')
    calc('synthetic_matched_contributor_change',growth(new['A'],old['A']),0,1,'hypothetical_arithmetic')
    calc('synthetic_median_nonadditivity',D(median([0,100,101])-median([0,99,0])-median([0,1,101])),99,1,'hypothetical_arithmetic')
    r={k:D(v) for k,v in s['rights'].items()}; capital=r['new_shares']*r['subscription_price']; ex=(r['old_shares']*r['old_price']+capital)/(r['old_shares']+r['new_shares'])
    calc('synthetic_rights_subscription',capital,200,1,'hypothetical_arithmetic')
    calc('synthetic_theoretical_ex_rights_price',ex,8,1,'hypothetical_arithmetic')
    entitlement=r['new_shares']/r['old_shares']*(ex-r['subscription_price'])
    calc('synthetic_entitlement_per_old_share',entitlement,2,1,'hypothetical_arithmetic')
    calc('synthetic_non_subscriber_wealth_with_rights',r['old_shares']*(ex+entitlement),1000,1,'hypothetical_arithmetic')
    b={k:D(v) for k,v in s['equity_bridge'].items()}; ev0=b['EBITDA_old']*b['multiple_old']; ev1=b['EBITDA_new']*b['multiple_new']; eq0=ev0-b['net_claims_old']; eq1=ev1-b['net_claims_new']
    calc('synthetic_EV_change',growth(ev1,ev0),5,1,'hypothetical_arithmetic')
    calc('synthetic_equity_change',growth(eq1,eq0),45,2,'hypothetical_arithmetic')
    calc('synthetic_multiple_change',growth(b['multiple_new'],b['multiple_old']),-25,2,'hypothetical_arithmetic')
    calc('synthetic_per_share_after',eq1/b['shares'],49,10,'hypothetical_arithmetic')
    calc('synthetic_currency_return',((1+D(s['FX']['local_return']))*(1+D(s['FX']['currency_return']))-1)*100,-1,1,'hypothetical_arithmetic')
    calc('synthetic_horizon_roll_without_revision',growth(D(s['fixed_horizon']['FY2027']),D(s['fixed_horizon']['FY2026'])),50,1,'hypothetical_arithmetic')
    calc('synthetic_same_horizon_unchanged',growth(D(s['fixed_horizon']['FY2027']),D(s['fixed_horizon']['FY2027'])),0,1,'hypothetical_arithmetic')

    def bad(name, mutate, expected):
        x=copy.deepcopy(m); mutate(x); detected=audit(x)
        check(name, expected in detected, 'negative_control', {'expected':expected,'errors':detected})
    bad('reject_trade_authority',lambda x:x['authority'].update(trade=True),'authority')
    bad('reject_false_backtest',lambda x:x.update(predictive_backtests_run=1),'scope')
    bad('reject_duplicate_source',lambda x:x['sources'].append(copy.deepcopy(x['sources'][0])),'source_id')
    bad('reject_unknown_source',lambda x:x['observations'][0][6].append('S99'),'observation_source')
    bad('reject_infinite_numeric',lambda x:x['observations'][0][5].update(PAT='Infinity'),'finite_values')
    bad('reject_current_quote_label',lambda x:x['valuation_case'].update(mode='CURRENT'),'quote_mode')
    bad('reject_fabricated_first_publication',lambda x:x['valuation_case'].update(estimate_first_publication='2026-07-29T00:00:00Z'),'invented_publication')
    bad('reject_archive_inference',lambda x:x['expectations_status'].update(independent_historical_vintages=True),'historical_admission')
    bad('reject_incomplete_fairvalue',lambda x:x['valuation_case'].update(fair_value='200'),'incomplete_valuation')
    bad('reject_issued_as_float',lambda x:x['valuation_case'].update(quote_share_basis='free_float'),'share_basis')
    bad('reject_book_as_market_claim',lambda x:x['valuation_case'].update(NCI_and_hybrid_basis='market_value'),'claim_basis')
    bad('reject_pre_result_relabel',lambda x:x['observations'][8].__setitem__(3,'pre-Q2'),'post_result')
    bad('reject_crore_million',lambda x:x['observations'][17][5].update(rupees_per_crore='1000000'),'crore')
    bad('reject_wrong_ADS_ratio',lambda x:x['observations'][15][5].update(ordinary_per_ADS='1'),'ADS')
    bad('reject_operating_net_swap',lambda x:x['observations'][20][5].update(actual_operating_aftertax_rounded='3220'),'operating_vs_net')
    bad('reject_debt_component_mislabel',lambda x:x['observations'][7][5].update(gas_inventory='4058'),'debt_note_labels')
    from collections import Counter
    failures=[c for c in checks if not c['pass']]
    result={'artifact_type':'research_integrity_and_arithmetic_receipt','input_artifacts':[digest(p) for p in [MODEL,DOC,Path(__file__)]],
            'counts':dict(Counter(c['category'] for c in checks)), 'passed':len(checks)-len(failures),'failed':len(failures),
            'application_tests_run':0,'predictive_backtests_run':0,'full_source_link_test':False,
            'scope_correction':'Before publication, two Orsted adjusted-debt component labels were corrected to the visually inspected note; source numbers unchanged.',
            'claim_limit':'Selected notebook checks only; not source-truth, license, complete contract/valuation, production behavior, PIT admission or investment merit.', 'checks':checks}
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['checks','input_artifacts']},indent=2))
    if failures:
        print(json.dumps(failures,indent=2)); raise SystemExit(1)

if __name__ == '__main__':
    main()
