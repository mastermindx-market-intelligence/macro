"""Research artifact and illustrative arithmetic checks. No network or product effects.

This is not application validation, source-truth certification, a return backtest,
or a calculator licensed to decide tariff bills or securities valuations.
"""
from __future__ import annotations
import copy
import hashlib
import json
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parent
MODEL=ROOT/'ENERGY_R3_RESEARCH_MODEL_2026-09-23.json'
DOC=ROOT/'ENERGY_R3_POWER_DEMAND_EQUITY_DOSSIERS_2026-09-23.md'
RECEIPT=ROOT/'ENERGY_R3_VERIFICATION_2026-09-23.json'
D=Decimal
m=json.loads(MODEL.read_text(encoding='utf-8'))
doc=DOC.read_text(encoding='utf-8')
checks=[]
def check(name: str, ok: bool, detail: object) -> None:
    checks.append({'name':name,'passed':bool(ok),'detail':detail})
def calc(name: str, actual: Decimal, expected: str, note: str,
         quantum: str='0.000001') -> None:
    target=D(expected)
    check(name,actual.quantize(D(quantum),rounding=ROUND_HALF_UP)==target.quantize(D(quantum),rounding=ROUND_HALF_UP),
          {'actual':str(actual),'expected':str(target),'quantum':quantum,'scope':note})
def validations(x: dict) -> list[str]:
    errors=[]
    sids=[r['id'] for r in x['sources']]
    sidset=set(sids)
    if len(sids)!=len(sidset): errors.append('duplicate_source_id')
    if any(v is not False for v in x['authority'].values()): errors.append('authority_escalation')
    if x['mission_complete'] is not False or x['application_tests_run']!=0 or x['predictive_backtests_run']!=0:
        errors.append('unsupported_completion')
    for group in ['observations','companies','evidence_scope_cases']:
        if any(not set(r['source_ids'])<=sidset for r in x[group]): errors.append('unresolved_source')
    for o in x['observations']:
        if set(o['values'])!=set(o['value_units']): errors.append('incomplete_units')
    for c in x['companies']:
        if any(c[k] is not None for k in ['canonical_issuer_id','canonical_security_id','exposure_weight','company_forecast']):
            errors.append('invented_canonical_exposure')
    e={r['id']:r for r in x['evidence_scope_cases']}
    if e['E01']['measure_kind']!='management_opportunity_not_guidance' or e['E01']['is_consensus']:
        errors.append('opportunity_promoted')
    if e['E02']['automatic_reopening_date'] is not None: errors.append('deadline_as_reopening')
    if e['E05']['Anderson_CWIP_treatment_from_Buck'] is not None: errors.append('cross_project_scope')
    if e['E06']['minimum_billing_demand_is_energy_consumption']: errors.append('demand_energy_confusion')
    if e['E07']['backlog_plus_RPO_valid']: errors.append('backlog_double_count')
    if e['E08']['Americas_order_growth_is_quarterly']: errors.append('rolling_period_confusion')
    if e['E09']['all_contracted_MW_are_new_supply']: errors.append('existing_capacity_as_new')
    return errors

check('research_model_invariants',not validations(m),validations(m))
check('unique_source_urls',len({s['url'] for s in m['sources']})==len(m['sources']),len(m['sources']))
check('https_source_locators',all(urlparse(s['url']).scheme=='https' for s in m['sources']),'Syntax only, not a network-link test')
check('no_future_publication',all(s['publication_date'] is None or date.fromisoformat(s['publication_date'])<=date.fromisoformat(m['research_cutoff']) for s in m['sources']),m['research_cutoff'])
check('unknown_publication_precision',all((s['publication_date'] is None)==(s['publication_precision']=='unknown') for s in m['sources']),'No invented midnight publication timestamps')
check('source_ingestion_unadmitted',all(s['redistribution_or_native_ingestion_admitted'] is False for s in m['sources']),'Public locator is not ingestion permission')
for group in ['observations','drivers','acceptance_cases','research_conflicts','evidence_scope_cases']:
    ids=[r['id'] for r in m[group]]
    check(f'{group}_unique_ids',len(ids)==len(set(ids)),len(ids))
check('finite_observation_values',all(D(v).is_finite() for o in m['observations'] for v in o['values'].values()),'Decimal-valued strings')
check('all_acceptance_cases_proposed',all(r['status']=='PROPOSED_NOT_APPLICATION_TESTED' for r in m['acceptance_cases']),len(m['acceptance_cases']))
check('all_source_ids_in_document_resolve',set(re.findall(r'\bP\d{2}\b',doc))<=set(s['id'] for s in m['sources']),'Includes locator register')
check('complete_locator_register',len(re.findall(r'^\*\*P\d{2} —',doc,re.M))==len(m['sources']),len(m['sources']))
check('no_unfinished_markers',not re.search(r'\b(TODO|TBD|PLACEHOLDER)\b',doc),'No placeholder markers; declared gaps remain')
check('five_core_dossiers',all(t in doc for t in ['## 4. Merchant generation','## 5. Regulated investment','## 6. Contracted generation','## 7. Equipment and service','## 8. Engineering and construction']),'Five required business models')
check('no_full_duke_read_claim','indexed' in next(s['review_scope'] for s in m['sources'] if s['id']=='P14'),'Full-file limitation explicit')
check('pdf_review_scope_recorded',all('screenshot' in s['review_scope'] for s in m['sources'] if s['id'] in ['P22','P23']),'Evidence of review method, not image validation by this script')
check('research_not_product_scope',m['artifact_type']=='research_notebook_not_production_schema' and 'not 55 executed application tests' in doc,'Proposed requirements do not equal tested product behavior')
integrity_count=len(checks)
O={r['id']:{k:D(v) for k,v in r['values'].items()} for r in m['observations']}
old_days=(date(2028,6,1)-date(2027,6,1)).days
new_days=(date(2029,6,1)-date(2028,6,1)).days
calc('capacity_old_delivery_days',D(old_days),'366','Delivery dates, not calendar-year assumption')
calc('capacity_new_delivery_days',D(new_days),'365','Delivery dates')
old=O['O03']['cleared_capacity']*O['O03']['price']*old_days
new=O['O04']['cleared_capacity']*O['O04']['price']*new_days
calc('Talen_old_gross_capacity_revenue_USD',old,'1067231404.80','Disclosed inputs; gross future capacity revenue, not net income')
calc('Talen_new_gross_capacity_revenue_USD',new,'1207602500','Disclosed inputs; changed portfolio')
calc('Talen_capacity_revenue_change_pct',(new/old-1)*100,'13.1528265162','Not stock performance or organic profit growth')
calc('Talen_cleared_MW_change_pct',(O['O04']['cleared_capacity']/O['O03']['cleared_capacity']-1)*100,'16.4093767867','Portfolio/performance attribution unresolved')
calc('Talen_capacity_price_change_pct',(O['O04']['price']/O['O03']['price']-1)*100,'-2.53119001919','Lower observed auction rate')
check('capacity_direction_counterexample',new>old and O['O04']['price']<O['O03']['price'],'Revenue up with rate down')
calc('Vistra_existing_plus_uprate',O['O06']['existing']+O['O06']['uprates'],str(O['O06']['total']),'Contract MW, not all new supply')
calc('Duke_proposed_interest_sum',sum(v for k,v in O['O07'].items() if k!='gross_capacity'),str(O['O07']['gross_capacity']),'Proposed capacity allocations, not final cash rights')
calc('GEV_RPO_sum',O['O09']['equipment']+O['O09']['services'],str(O['O09']['total']),'USD million, contractual revenue measure')
calc('GEV_rounded_liability_difference',O['O10']['closing']-O['O10']['opening'],'14087','USD million, stock difference from rounded values')
check('GEV_reported_rounding_preserved',O['O10']['source_reported_increase']==D('14088') and O['O10']['closing']-O['O10']['opening']!=O['O10']['source_reported_increase'],'Known precision difference is preserved, not an equality claimed PASS')
calc('GEV_H1_issuer_FCF',O['O24']['CFO']-O['O24']['gross_capex'],str(O['O24']['issuer_FCF']),'USD million; six-month period; not discretionary cash after every obligation')
check('GEV_cash_flow_contribution_not_balance_delta',O['O24']['contract_liabilities_cashflow_contribution']!=O['O10']['source_reported_increase'],'Flow and stock are different measures')
calc('Quanta_backlog_outside_RPO',O['O12']['backlog']-O['O12']['RPO'],'19886.341','USD million; does not estimate probability of conversion')
calc('Quanta_contract_revenue_sum',sum(v for k,v in O['O13'].items() if k!='total'),str(O['O13']['total']),'Revenue categories, USD million')
calc('Quanta_fixed_price_revenue_pct',O['O13']['fixed_price']/O['O13']['total']*100,'63.6545454602528','Revenue mix, not profit margin')
calc('Clearway_old_CAFD_midpoint',(O['O16']['old_low']+O['O16']['old_high'])/2,'490','USD million; historical guidance')
calc('Clearway_new_CAFD_midpoint',(O['O16']['new_low']+O['O16']['new_high'])/2,'450','USD million; revised management guidance')
calc('Clearway_guidance_midpoint_change_pct',(D(450)/490-1)*100,'-8.1632653061','Not a realized loss or market-surprise measure')
calc('Clearway_Q2_CAFD_bridge',sum(v for k,v in O['O17'].items() if k!='CAFD'),str(O['O17']['CAFD']),'USD million; issuer-defined CAFD')
calc('Clearway_guidance_CAFD_bridge',sum(v for k,v in O['O18'].items() if k!='CAFD'),str(O['O18']['CAFD']),'USD million; forecast reconciliation')
calc('Clearway_ownership_weighted_MW',O['O21']['gross']*O['O21']['ownership_percent']/100,str(O['O21']['net']),'Capacity only, not distribution waterfall')
calc('Clearway_public_disclosure_interval_days',D((date(2026,8,5)-date(2026,7,16)).days),'20','Not 20 days of exclusive information or proven alpha')
calc('Eaton_reported_sales_growth_components',O['O22']['organic_sales_growth']+O['O22']['acquisition_contribution'],str(O['O22']['reported_sales_growth']),'Reported percentage-point decomposition')
calc('Eaton_Global_sales_growth_components',O['O23']['Global_organic_growth']+O['O23']['Global_acquisition_contribution']+O['O23']['Global_FX'],str(O['O23']['Global_reported_sales_growth']),'Quarterly sales, not rolling orders')
calc('PJM_prior_vintage_peak',O['O01']['revised']-O['O01']['change_from_prior'],'164186','Derived previous forecast, not metered peak')
source_arithmetic_count=len(checks)-integrity_count

# Every calculation below is deliberately hypothetical, not a named issuer forecast.
calc('facility_1GW_90pct_TWh',D(1000)*8760*D('0.9')/D(1000000),'7.884','Facility-load scenario, non-leap year')
calc('IT_1GW_PUE1_2_TWh',D(1000)*D('1.2')*8760*D('0.9')/D(1000000),'9.4608','Different IT-load scenario, not additional demand')
calc('leap_year_facility_TWh',D(1000)*8784*D('0.9')/D(1000000),'7.9056','2028 calendar')
calc('hypothetical_spark_margin_delta',(D(70)-7*D(4))-(D(50)-7*D(3)),'13','USD/MWh before all other costs')
calc('hypothetical_unhedged_revenue_delta_USDm',(D(10)-8)*20,'40','TWh times USD/MWh -> USD million; simplified same-index hedge')
calc('hypothetical_outage_replacement_cost_USDm',D(1000)*4*(1000-50)/1000000,'3.8','Incremental replacement price only')
calc('hypothetical_allowed_equity_earnings_USDm',(D(1000)-200)*D('0.53')*D('0.10'),'42.4','Assumed eligible investment/equity/return; not company permission')
calc('hypothetical_half_year_allowed_earnings_USDm',D('42.4')/2,'21.2','Simplified half-year exposure')
calc('hypothetical_100bp_allowed_return_delta_USDm',D(800)*D('0.53')*D('0.01'),'4.24','Not observed jurisdictional ROE change')
calc('AEP_size_branch_100MW_MW',min(D('57.5')+(100-75),D('0.85')*100),'82.5','Tariff-summary size branch only; excludes ratchet, ramp, actual demand')
calc('AEP_size_branch_150MW_MW',min(D('57.5')+(150-75),D('0.85')*150),'127.5','Applies stated cap to size branch, not entire bill')
base_rev=D(100)*8760*D('0.25')*50/1000000
low_rev=base_rev*D('0.95')
calc('hypothetical_solar_revenue_USDm',base_rev,'10.95','100 MW, 25% capacity factor, USD50/MWh; no taxes/curtailment')
calc('hypothetical_solar_low_output_revenue_USDm',low_rev,'10.4025','5% less output, unchanged unit price')
calc('hypothetical_residual_cash_change_pct',((low_rev-7)/(base_rev-7)-1)*100,'-13.8607594937','Assumed fixed cash costs/debt of USD7m; not Clearway forecast')
calc('hypothetical_deposit_period_net_cash',D(30)-20,'10','Advance 30, early cost 20; not recognition of profit')
calc('hypothetical_equipment_whole_contract_cash',(D(30)-20)+(70-60),'20','Contract price100, cost80; no discount/tax effects')
calc('hypothetical_fixed_price_profit_change_pct',((D(100)-90*D('1.05'))/(100-90)-1)*100,'-45','5% cost increase; no customer recovery assumed')
scenario_count=len(checks)-integrity_count-source_arithmetic_count

# Small falsification checks of this notebook validator, NOT application mutation testing.
mutations=[
 ('reject_trade_authority',lambda x:x['authority'].__setitem__('trade',True),'authority_escalation'),
 ('reject_invented_theme_weight',lambda x:x['companies'][0].__setitem__('exposure_weight','0.5'),'invented_canonical_exposure'),
 ('reject_missing_unit',lambda x:x['observations'][2]['value_units'].pop('price'),'incomplete_units'),
 ('reject_opportunity_as_consensus',lambda x:x['evidence_scope_cases'][0].__setitem__('is_consensus',True),'opportunity_promoted'),
 ('reject_deadline_as_restart',lambda x:x['evidence_scope_cases'][1].__setitem__('automatic_reopening_date','2026-10-19'),'deadline_as_reopening'),
 ('reject_Duke_cross_heading_rule',lambda x:x['evidence_scope_cases'][4].__setitem__('Anderson_CWIP_treatment_from_Buck',False),'cross_project_scope'),
 ('reject_tariff_as_consumption',lambda x:x['evidence_scope_cases'][5].__setitem__('minimum_billing_demand_is_energy_consumption',True),'demand_energy_confusion'),
 ('reject_RPO_backlog_sum',lambda x:x['evidence_scope_cases'][6].__setitem__('backlog_plus_RPO_valid',True),'backlog_double_count'),
 ('reject_rolling_as_quarterly',lambda x:x['evidence_scope_cases'][7].__setitem__('Americas_order_growth_is_quarterly',True),'rolling_period_confusion'),
 ('reject_all_PPA_as_new_MW',lambda x:x['evidence_scope_cases'][8].__setitem__('all_contracted_MW_are_new_supply',True),'existing_capacity_as_new'),
]
for name,mutate,expected_error in mutations:
    candidate=copy.deepcopy(m)
    mutate(candidate)
    got=validations(candidate)
    check(name,expected_error in got,{'expected_rejection':expected_error,'observed':got})

def file_record(p: Path) -> dict:
    raw=p.read_bytes()
    return {'path':p.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
            'git_blob_sha1':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}
failed=[c for c in checks if not c['passed']]
result=dict(artifact_type='local_research_integrity_arithmetic_receipt',status='PASS' if not failed else 'FAIL',
            inputs=[file_record(p) for p in [MODEL,DOC]],verifier=file_record(Path(__file__)),
            passed=len(checks)-len(failed),failed=len(failed),counts=dict(integrity=integrity_count,source_arithmetic=source_arithmetic_count,hypothetical_scenarios=scenario_count,notebook_negative_controls=len(mutations)),
            application_tests_run=0,predictive_backtests_run=0,full_source_link_test_run=False,
            check_corrections=['Corrected the mistyped expected Quanta percentage using an independent exact integer fraction; source inputs and tolerance unchanged.'],
            claim_limit='Checks notebook structure, known scope guards and stated arithmetic only. Does not validate source truth, full contracts, issuer forecasts, product behavior, investment merit, deployment or publication.',checks=checks)
RECEIPT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
if failed:
    print(json.dumps(failed,indent=2))
    raise SystemExit(1)
