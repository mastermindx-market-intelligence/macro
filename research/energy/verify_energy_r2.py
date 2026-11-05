"""Local research-integrity and arithmetic checks, not application or investment validation."""
from __future__ import annotations
import hashlib
import json
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / 'ENERGY_R2_RESEARCH_MODEL_2026-09-23.json'
raw = MODEL.read_bytes()
m = json.loads(raw)
D = Decimal
checks = []

def check(name: str, ok: bool, detail: object) -> None:
    checks.append({'name': name, 'pass': bool(ok), 'detail': detail})

def calc(name: str, actual: Decimal, expected: str, note: str,
         places: str = '0.000001') -> None:
    target = D(expected)
    check(name, actual.quantize(D(places), rounding=ROUND_HALF_UP) == target.quantize(D(places), rounding=ROUND_HALF_UP),
          {'actual': str(actual), 'expected': expected, 'rounding': places, 'note': note})

sids = {s['id'] for s in m['sources']}
check('unique_primary_source_ids', len(sids) == len(m['sources']), len(sids))
check('unique_source_urls', len({s['url'] for s in m['sources']}) == len(sids), len(sids))
check('https_source_locators', all(urlparse(s['url']).scheme == 'https' for s in m['sources']), 'Locators only; not an HTTP-link test')
cutoff = date.fromisoformat(m['research_cutoff'])
check('no_future_publication_date', all(s['date'] is None or date.fromisoformat(s['date']) <= cutoff for s in m['sources']), m['research_cutoff'])
check('authority_all_false', all(v is False for v in m['authority'].values()), m['authority'])
check('no_application_tests_or_completion_claim', m['application_tests_run'] == 0 and m['mission_complete'] is False, 'Research only')
for group, isdict in [('business_roles', False), ('contracts', True), ('observations', False), ('drivers', False), ('acceptance_cases', False), ('gaps', True)]:
    ids = [r['id'] if isdict else r[0] for r in m[group]]
    check(f'{group}_unique_ids', len(ids) == len(set(ids)), len(ids))
check('role_source_references', all(set(r[4]) <= sids for r in m['business_roles']), 'Every research role cites registered sources')
check('contract_source_references', all(set(r['source_ids']) <= sids for r in m['contracts']), 'Every research contract cites registered sources')
check('observation_source_references', all(set(r[6]) <= sids for r in m['observations']), 'Every observation cites registered sources')
check('numeric_observation_values', all(D(v).is_finite() for r in m['observations'] for v in r[5].values()), 'Decimal-parsable values with row-level units')
c = {r['id']: r for r in m['contracts']}
check('future_contract_not_current_profit', c['C02']['start_year'] > cutoff.year and c['C02']['current_contract_profit'] is None, 'EOG 2027 start')
check('counterparty_option_preserved', c['C02']['option_holder'] == 'counterparty', c['C02']['options'])
check('announced_project_has_no_invented_earnings', c['C04']['target_completion_year'] > cutoff.year and c['C04']['forecast_incremental_profit'] is None and c['C04']['baseline_contributed_asset_profit'] is None, 'Western Gateway')
check('power_linked_contract_unknowns_preserved', all(c['C06'][k] is None for k in ['formula', 'start_date', 'current_deliveries', 'incremental_cashflow']), 'EQT/CPV')
check('no_claim_of_full_SLB_annual_read', 'excerpt' in next(s for s in m['sources'] if s['id'] == 'S14')['kind'], 'Full annual fetch limitation retained')
integrity_count = len(checks)
o = {r[0]: {k:D(v) for k,v in r[5].items()} for r in m['observations']}

calc('EOG_reported_FCF', o['O01']['adjusted_CFO']-o['O01']['defined_capex'], '2799', 'USD million; issuer definition')
calc('EOG_naive_FCF_label_gap', (o['O01']['CFO']-o['O01']['defined_capex'])-o['O01']['issuer_FCF'], '283', 'USD million; not a restated company measure')
calc('EOG_gas_revenue_bridge', o['O02']['prior_revenue']+o['O02']['volume_effect']+o['O02']['price_effect'], '812', 'USD million')
calc('EOG_BOE_rounding', o['O03']['oil_kbpd']+o['O03']['NGL_kbpd']+o['O03']['gas_MMcfpd']/o['O03']['Mcf_per_boe'], '1410.4', 'Quantity conversion only, not economic equivalence', '0.1')
calc('SLB_headline_growth_pct', (o['O04']['current']/o['O04']['prior']-1)*100, '4.984788205', 'Rounded reporting basis, not share-price return')
calc('SLB_acquisition_excluded_growth_pct', ((o['O04']['current']-o['O04']['acquired_current'])/o['O04']['prior']-1)*100, '-5.195413059', 'Not constant-currency or full pro forma growth')
calc('SLB_reported_FCF', o['O05']['CFO']-o['O05']['capex']-o['O05']['APS_investment']-o['O05']['capitalized_exploration_data'], '716', 'USD million')
calc('SLB_omitted_capital_investments', o['O05']['APS_investment']+o['O05']['capitalized_exploration_data'], '184', 'USD million; naive CFO-capex overstatement versus issuer measure')
calc('Cheniere_adjusted_parent_NI', sum(v for k,v in o['O06'].items() if k != 'adjusted_parent_NI'), '632', 'USD million; not cash flow')
calc('Cheniere_NPNS_reclassification', sum(v for k,v in o['O08'].items() if k != 'net'), '349', 'USD million; not cash generation')
calc('KMI_service_revenue_sum', o['O11']['firm']+o['O11']['fee_based'], '2097', 'USD million; no cash-flow-mix inference')
calc('EQT_consolidated_FCF', o['O12']['CFO']+o['O12']['working_capital_adjustment']+o['O12']['capex']+o['O12']['equity_method_contributions'], '453734', 'USD thousand; issuer capital definition')
calc('EQT_attributable_FCF', sum(v for k,v in o['O13'].items() if k != 'attributable_FCF'), '329666', 'USD thousand; includes NCI capital offsets')
calc('EQT_consolidated_vs_attributable_gap', o['O12']['FCF']-o['O13']['attributable_FCF'], '124068', 'USD thousand; not cash lost or an expense newly incurred')
calc('Valero_rounded_input_reconstruction', D(360)*1000/(D(130)*91), '30.431107354', 'Illustration from rounded aggregate inputs, not the reported 30.36 ratio')
check('Valero_published_ratio_not_overwritten', o['O10']['current'] == D('30.36') and D(360)*1000/(D(130)*91) != o['O10']['current'], 'Source ratio retained; rounding gap is explicit')

# Deliberately hypothetical examples. None is a company forecast or a calibrated model.
calc('hypothetical_partial_hedge_revenue_change', (D(10)*5+D(6)*(4-5))-(D(10)*3+D(6)*(4-3)), '8', 'USD million; 10 million units produced, six hedged at $4, spot $3 to $5; no basis/tax/cost change')
calc('hypothetical_LNG_lifting_contribution', D('5.25')-D('1.15')*3-1, '0.80', '$/MMBtu; unavoidable $2.50 fixed fee excluded from marginal lifting decision')
calc('hypothetical_LNG_full_cost_margin', D('5.25')-D('1.15')*3-1-D('2.50'), '-1.70', '$/MMBtu; include fixed fee for full-cycle margin; no other costs assumed')
calc('hypothetical_turnkey_profit_change_pct', ((100-D(80)*D('1.10'))/(100-80)-1)*100, '-40', 'Contract price 100, initial cost 80; cost +10%, no contractual recovery')
calc('hypothetical_five_year_cash_PV', sum(D(100)/(D('1.10')**year) for year in range(1,6)), '379.078676941', 'End-year cash 100 for five years, no terminal value, 10% discount; not reserve valuation')
calc('hypothetical_firm_fee', D(1000000)*D('0.4')*365/D(1000000), '146', 'USD million annually; availability and counterparty payment assumed')

model_check_count = len(checks)
DOC = ROOT / 'ENERGY_R2_HYDROCARBON_ECONOMICS_2026-09-23.md'
BRIDGE = ROOT / 'ENERGY_R2_RECONCILIATION_AND_POWER_BRIDGE_2026-09-23.md'
doc = DOC.read_text()
bridge = BRIDGE.read_text()
check('document_registered_sources', set(re.findall(r'\bS\d{2}\b', doc)) <= sids, 'Document source IDs resolve to model')
check('document_seven_dossiers', all(name in doc for name in ['2.1 EOG','2.2 Valero','2.3 Kinder Morgan','2.4 Cheniere','2.5 SLB','2.6 Halliburton','2.7 EQT']), 'Seven named issuer sections')
check('document_exact_source_rows', len(re.findall(r'^\| S\d{2} \|', doc, re.M)) == len(sids), 'Anchored locator-row grammar, not loose substring count')
check('document_no_placeholders', not re.search(r'\b(TODO|TBD|PLACEHOLDER)\b', doc), 'No placeholder marker')
check('bridge_explicit_hypothesis', 'no source establishes it for CPV or EQT' in bridge and 'This is not an estimate for Shay' in bridge, 'Synthetic pricing and timing examples are not company forecasts')
check('bridge_source_locator_rows', len(re.findall(r'^P0[1-5] —', bridge, re.M)) == 5, 'Four primary locators including a reused EOG filing; external error example is not ownership truth')
document_check_count = len(checks) - model_check_count
calc('bridge_gas_price_low', D('0.6')*50/7, '4.285714', 'Hypothetical $/MMBtu; not CPV terms')
calc('bridge_gas_price_high', D('0.6')*80/7, '6.857143', 'Hypothetical $/MMBtu; not CPV terms')
calc('bridge_generator_contribution_low', D(50)-D('0.6')*50, '20', 'Hypothetical $/MWh before all other costs')
calc('bridge_generator_contribution_high', D(80)-D('0.6')*80, '32', 'Hypothetical $/MWh before all other costs')
calc('bridge_gas_payment_delta', D('0.6')*(80-50), '18', 'Hypothetical $/MWh; payment not producer profit')
calc('bridge_generator_contribution_delta', (1-D('0.6'))*(80-50), '12', 'Hypothetical $/MWh; no double count')
pv = sum(D(100)/(D('1.1')**year) for year in range(1,6))
calc('bridge_delayed_cash_PV', pv/D('1.1'), '344.616979037', 'Hypothetical one-year delay at 10%; no company valuation')
calc('bridge_delay_value_change_pct', (1/D('1.1')-1)*100, '-9.090909', 'Hypothetical timing-only change')
bridge_check_count = len(checks) - model_check_count - document_check_count

failures = [r for r in checks if not r['pass']]
result = {
 'artifact_type':'local_research_integrity_and_arithmetic_receipt',
 'input_file':MODEL.name,
 'input_sha256':hashlib.sha256(raw).hexdigest(),
 'input_git_blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),
 'integrity_checks':integrity_count,
 'arithmetic_and_measurement_checks':model_check_count-integrity_count,
 'document_integrity_checks':document_check_count,
 'bridge_arithmetic_checks':bridge_check_count,
 'input_artifacts':[{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(p.read_bytes())).encode()+b'\0'+p.read_bytes()).hexdigest()} for p in [MODEL,DOC,BRIDGE]],
 'verifier_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'check_corrections':['Corrected a mistyped expected SLB growth constant using an independent exact fraction; no input or tolerance change.','Replaced a loose substring locator count with an anchored source-row grammar; no source or coverage requirement removed.'],
 'passed':len(checks)-len(failures), 'failed':len(failures),
 'application_tests_run':0,
 'claim_limit':'Does not establish source truth beyond cited reads, link availability, complete global coverage, predictive validity, accepted schema, native ingestion, browser proof or research acceptance.',
 'checks':checks,
}
(ROOT/'ENERGY_R2_VERIFICATION_2026-09-23.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
if failures:
    print(json.dumps(failures,indent=2))
    raise SystemExit(1)
