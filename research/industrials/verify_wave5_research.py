"""Narrow authored research checks; not factual review or application acceptance."""
from __future__ import annotations
from collections import Counter
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from math import isclose
import json
import re
from calculate_wave5 import (results, ffp, fpi, cpff, cash_schedule, growth, midpoint,
                             cumulative_buckets, Observation, comparable, available)

P=Path(__file__).parent
checks=[]

def check(name, ok, group='arithmetic'):
    checks.append({'name':name,'pass':bool(ok),'group':group})


def close(name, actual, expected, group='arithmetic'):
    check(name, isclose(actual, float(expected), rel_tol=1e-10, abs_tol=1e-9), group)


def refuses(name, call):
    try:
        call()
    except (ValueError, TypeError):
        check(name, True, 'invalid_input')
    else:
        check(name, False, 'invalid_input')

x=results()
for c, p in [(90,30),(100,20),(115,5),(120,0),(145,-25)]:
    close(f'fixed_price_profit_cost_{c}', ffp(120,c)['profit'], p)
for c, p in [(90,22),(100,20),(115,17),(120,12),(145,-13)]:
    close(f'incentive_profit_cost_{c}', fpi(c)['profit'], p)
close('ceiling_cost_threshold',fpi(100)['ceiling_cost_threshold'],115)
close('ceiling_binds',fpi(145)['price'],132)
close('fee_remains_fixed',cpff(145,10,150)['profit'],10)
check('fee_margin_can_fall',cpff(145,10,150)['margin']<cpff(90,10,150)['margin'])
for key, funding in [('early',0),('late',40),('later',60)]:
    close(f'{key}_lifetime_cash',x['cash_timing'][key]['lifetime_net_cash'],20)
    close(f'{key}_peak_period_end_funding',x['cash_timing'][key]['peak_net_funding'],funding)
r=Fraction(11,10)
close('early_discounted_value',x['cash_timing']['early']['npv'],10+Fraction(10)/r**3)
close('late_discounted_value',x['cash_timing']['late']['npv'],-20-Fraction(20)/r+Fraction(60)/r**3)
close('later_discounted_value',x['cash_timing']['later']['npv'],-20-Fraction(20)/r-Fraction(20)/r**3+Fraction(80)/r**4)
close('fixed_price_productivity_capture',x['service_productivity']['fixed_price_profit'],6)
close('hourly_productivity_capture',x['service_productivity']['time_materials_profit'],3)
close('remaining_loss_reconciles',x['remaining_loss_cash']['cash_to_date']+x['remaining_loss_cash']['future_net_cash'],-15)
check('known_loss_not_counted_twice',x['remaining_loss_cash']['double_counted_future_cash_wrong'] != x['remaining_loss_cash']['future_net_cash'])
for k,v in [('firm_now',136498),('firm_change',5658),('potential_change',-7197),('total_change',-1539)]:
    close(f'gd_{k}',x['gd'][k],v)
for n,v in enumerate([.35,.20,.45]): close(f'cumulative_bucket_{n}',x['northrop']['recognition_buckets'][n],v)
close('northrop_segment_guide_unchanged',x['northrop']['segment_guidance_change'],0)
close('northrop_eps_guide_change',x['northrop']['eps_guidance_change'],1.2)
close('lmt_cfo_midpoint_unchanged',x['lmt']['operating_cash_now']-x['lmt']['operating_cash_prior'],0)
close('lmt_fcf_change',x['lmt']['fcf_now']-x['lmt']['fcf_prior'],450)
close('lmt_capex_change',x['lmt']['capex_prior']-x['lmt']['capex_now'],450)
close('lmt_sales_change',x['lmt']['sales_delta'],2000)
close('lmt_segment_profit_change',x['lmt']['segment_profit_delta'],50)
close('hii_net_asset_change',x['hii']['net_contract_asset_change'],926)
close('hii_grant_inclusive_fcf',x['hii']['h1_fcf'],-611)
close('caci_cash_bridge',x['caci']['fcf_now'],232883)
close('caci_gaap_growth',x['caci']['cfo_growth_pct'],(Fraction(378266,155982)-1)*100)
close('caci_adjusted_growth',x['caci']['adjusted_cfo_growth_pct'],(Fraction(279660,167073)-1)*100)
close('saab_concentration',x['saab']['named_award_share_pct'],Fraction(47000,68393)*100)
close('saab_remaining_not_organic',x['saab']['remaining_orders'],21393)
close('fincantieri_total',x['fincantieri']['total_backlog'],73916)
close('fincantieri_equity_bridge',x['fincantieri']['equity_effect']+x['fincantieri']['reduction_ex_equity'],555)
close('fincantieri_sensitive_scope',x['fincantieri']['liquidity_sensitivity_debt_plus_supplier_finance'],1647)
close('rheinmetall_values_growth',x['rheinmetall']['computed_growth_pct'],(Fraction(20646,14829)-1)*100)
check('rheinmetall_source_conflict_retained',x['rheinmetall']['unresolved_conflict'] and abs(x['rheinmetall']['computed_growth_pct']-80)>40)
close('issuer_attributed_expectation_shortfall',x['rheinmetall']['q1_issuer_attributed_expectation_gap'],-362)

for name, call in [
 ('negative_cost',lambda:ffp(120,-1)),
 ('nonfinite_price',lambda:ffp(float('nan'),2)),
 ('unapproved_cost',lambda:cpff(100,10,150,allowable_and_authorized=False)),
 ('cost_above_limit',lambda:cpff(151,10,150)),
 ('share_outside_model',lambda:fpi(110,contractor_share=1)),
 ('ceiling_below_target',lambda:fpi(110,price_ceiling=100)),
 ('cash_period_mismatch',lambda:cash_schedule([10],[1,2])),
 ('negative_receipt',lambda:cash_schedule([-1],[2])),
 ('unordered_cumulative',lambda:cumulative_buckets(.6,.5)),
 ('cumulative_above_one',lambda:cumulative_buckets(.3,1.2)),
 ('negative_growth_denominator',lambda:growth(2,-1)),
 ('reverse_range',lambda:midpoint((3,1)))]: refuses(name,call)

a=Observation()
changes={'subject':'another_business','metric':'bookings','definition':'includes_expected_options',
         'unit':'EUR_million','period_kind':'quarter_flow','duration_months':12,
         'consolidation':'proportionate_APM','perimeter':'acquired_unrecast',
         'adjustment':'constant_currency','clock_family':'rule_effective',
         'statement':'management_forecast','method_revision':'comparison_basis_2'}
for field,value in changes.items():
    check(f'reject_comparison_{field}',not comparable(a,replace(a,**{field:value})),'comparison')
check('matching_comparison_control',comparable(a,replace(a)),'availability_control')
check('available_on_cutoff_day',available(a,'2026-07-01'),'availability_control')
check('future_publication_unavailable',not available(a,'2026-06-30'),'availability_control')
check('unknown_publication_unavailable',not available(replace(a,published=None),'2026-09-23'),'availability_control')
check('effective_date_not_publication',not available(replace(a,clock_family='rule_effective'),'2026-09-23'),'availability_control')

model=(P/'INDUSTRIALS_WAVE5_ECONOMIC_MODEL_2026-09-23.md').read_text()
evidence=(P/'INDUSTRIALS_WAVE5_EVIDENCE_2026-09-23.md').read_text()
sources=json.loads((P/'WAVE5_SOURCE_INDEX.json').read_text())
ids=[s['id'] for s in sources['sources']]
check('unique_sources_27',len(ids)==len(set(ids))==27,'integrity')
check('evidence_source_ids_match',set(re.findall(r'## (W5-S\d{2})',evidence))==set(ids),'integrity')
check('research_slices_24',len(set(re.findall(r'W5-R\d{2}',model)))==24,'integrity')
check('hypotheses_12',len(set(re.findall(r'W5-H\d{2}',model)))==12,'integrity')
check('acceptance_specs_36',len(set(re.findall(r'W5-T\d{2}',model)))==36,'integrity')
check('explicit_source_corrections','Corrections to the initial evidence register' in model and 'source_corrections' in sources,'integrity')
check('effective_clock_is_not_published',all(s['published_at']=='unknown' for s in sources['sources'] if 'effective_at' in s),'integrity')
check('precise_gd_endpoint_not_in_index','June 28' not in sources['sources'][0]['period'] and 'exact fiscal endpoint not asserted' in sources['sources'][0]['period'],'integrity')
check('contract_model_hypothetical','These are chosen parameters, not estimates of any real program.' in model,'integrity')
check('fable_handoff_withheld','The final Fable handoff remains withheld' in model,'integrity')
check('no_validation_claim','no empirical backtest' in model,'integrity')
check('no_raw_corpus','No raw PDF corpus' in evidence,'integrity')

out={'research_only':True,'passed':sum(c['pass'] for c in checks),
     'failed':sum(not c['pass'] for c in checks),'groups':dict(Counter(c['group'] for c in checks)),
     'checks':checks,'limitations':'Authored fixtures and document arithmetic only; no factual, application or predictive acceptance.'}
(P/'WAVE5_CHECK_RESULTS.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='checks'},indent=2))
for c in checks:
    if not c['pass']: print('FAIL:',c['name'])
raise SystemExit(0 if out['failed']==0 else 1)
