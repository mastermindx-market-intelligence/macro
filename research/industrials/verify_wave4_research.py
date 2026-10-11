"""Authored research checks only: not independent factual review or application proof."""
from __future__ import annotations
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import json
import math
import re
import sys
from calculate_wave4 import (Maintenance, maintenance, shop_wip, cohort_npv,
                            cost_to_cost_revenue, comparable, available_as_of, calculate)

ROOT=Path(__file__).parent
results=[]
def check(name, condition):
    results.append({'name':name,'passed':bool(condition)})
def near(name, got, expected, tol=1e-7):
    check(name, math.isclose(got,expected,rel_tol=tol,abs_tol=tol))
def rejects(name, fn):
    try: fn()
    except (ValueError, TypeError): check(name,True)
    else: check(name,False)

x=calculate(); m=x['maintenance_hypothetical']; q=x['shop_hypothetical']; c=x['cohort_hypothetical']; s=x['source_calculations']
near('baseline billable engine hours',m['baseline']['hours'],3_000_000)
near('baseline renewal equivalents',m['baseline']['renewal_visit_equivalent'],500)
near('baseline hourly contribution',m['baseline']['hourly_contract_contribution'],180_000_000)
near('longer interval hourly contribution',m['longer_interval']['hourly_contract_contribution'],380_000_000)
near('shorter interval hourly contribution',m['shorter_interval']['hourly_contract_contribution'],-120_000_000)
near('baseline event contribution',m['baseline']['event_provider_contribution'],150_000_000)
near('longer interval event contribution',m['longer_interval']['event_provider_contribution'],100_000_000)
near('shorter interval event contribution',m['shorter_interval']['event_provider_contribution'],225_000_000)
check('same fixed-hours billings in all three sensitivities',len({v['hourly_billings'] for v in m.values()})==1)
near('baseline break-even hourly fee',m['baseline']['breakeven_fee_per_hour'],240)
near('zero activity does not create renewal cost',maintenance(Maintenance(annual_hours_per_engine=0))['renewal_cost'],0)
near('WIP at 90 days',q['wip_90_days'],float(Decimal(18000)/Decimal(365)))
near('extra WIP is flow times added time',q['extra_wip'],float(Decimal(12000)/Decimal(365)))
near('WIP asset proxy capital',q['additional_capital_at_2m_per_unit'],65_753_424.657534246)
near('capacity backlog accumulation',q['backlog_growth_if_750_admitted_600_completed'],150)
near('finite cohort baseline',c['base_100_cost_25_cash_years_3_to_12'],26.953865820344618)
near('two-year delay loses present value',c['delay_to_years_5_to_14'],4.92055026474759)
near('lower net cash reduces cohort value',c['cash_lower_to_20'],1.5630926562756855)
near('extra initial cost is not amortized away',c['higher_upfront_cost_130'],-3.0461341796553825)
near('five-year license fails illustrative hurdle',c['license_cost_40_cash_10_years_1_to_5'],-1.1034873664828382)
r=x['recognition_hypothetical']
near('recognition prior revenue',r['old_revenue'],500)
near('favorable cost estimate catchup',r['new_revenue_lower_cost']-r['old_revenue'],float(Decimal(500)/Decimal(7)))
near('unfavorable cost estimate catchup',r['new_revenue_higher_cost']-r['old_revenue'],-float(Decimal(500)/Decimal(9)))
near('no assumed new cash from recognition example',r['cash_change_assumed'],0)
p=x['pass_through_hypothetical']
near('pass-through profit before equals after',p['before_revenue']-p['before_cost'],p['after_revenue']-p['after_cost'])
near('pass-through margin before',p['before_margin'],(p['before_revenue']-p['before_cost'])/p['before_revenue'])
near('pass-through margin after',p['after_margin'],(p['after_revenue']-p['after_cost'])/p['after_revenue'])
near('RR component reconciliation',s['W4-S02']['net_contract_benefit'],s['W4-S02']['component_sum'])
near('RR explicit profit denominator',s['W4-S02']['share_of_civil_underlying_profit_pct'],float(Decimal(497)/Decimal(1567)*100))
near('GE nested net estimate component',s['W4-S05']['other_net_estimate_changes_implied'],-160)
near('GE service RPO denominator',s['W4-S05']['total_rpo'],210790)
near('MTU half-year sales growth',s['W4-S08']['maintenance_revenue_growth_pct'],21.150410861021783)
near('MTU half-year profit growth',s['W4-S08']['maintenance_profit_growth_pct'],12.448132780082988)
check('MTU profit margin differs from growth rates',s['W4-S08']['current_margin_pct']<s['W4-S08']['prior_margin_pct'])
near('HEICO revenue after eliminations',s['W4-S15']['revenues_after_elimination'],1413.05)
near('HEICO group profit after corporate',s['W4-S15']['profit_after_corporate'],355.197)
near('HEICO shareholder rather than consolidated net income',s['W4-S15']['parent_net_income'],235.439)
near('HEICO partial cash bridge after acquisitions',s['W4-S15']['then_less_acquisitions_only'],-256.362)
near('StandardAero corporate subtraction',s['W4-S25']['group_adjusted_ebitda'],229.877)
near('StandardAero H1 minus Q2 yields Q1 only',s['W4-S25']['q1_cfo_derived'],-119.555)

rejects('zero maintenance interval',lambda:maintenance(Maintenance(hours_between_visits=0)))
rejects('negative maintenance fee',lambda:maintenance(Maintenance(fee_per_hour=-1)))
rejects('nonfinite visit cost',lambda:maintenance(Maintenance(cost_per_visit=float('inf'))))
rejects('negative throughput',lambda:shop_wip(-1,90))
rejects('zero days per year',lambda:shop_wip(1,90,0))
rejects('invalid first service year',lambda:cohort_npv(100,25,0,10,.1))
rejects('invalid service duration',lambda:cohort_npv(100,25,1,0,.1))
rejects('zero recognition denominator',lambda:cost_to_cost_revenue(1000,400,0))
rejects('cost exceeds expected total',lambda:cost_to_cost_revenue(1000,400,300))

base={'business':'engine_contract_A','period':'H1-2026','measure':'billable_engine_hours','unit':'hours','currency':'N/A','basis':'reported','contract':'hourly-risk-bearing','vintage':'2026-07-30'}
for name,key,value in [
('different physical fleet','business','aircraft_fleet_A'),
('quarter versus half year','period','Q2-2026'),
('RPK is not hours','measure','passenger_kilometers'),
('hours versus cycles','unit','cycles'),
('currency basis','currency','USD'),
('estimate versus observed','basis','forecast'),
('time-and-material versus hourly contract','contract','event-paid'),
('revised versus original vintage','vintage','2026-08-30'),
('missing contract does not default','contract',None),
('adjusted versus consolidated','basis','adjusted'),
('admissions are not completions','measure','shop_admissions'),
('accrual usage is not cash','measure','compensation_accrual_used'),
('approval is not adoption','measure','PMA_eligibility'),
('JV program share is not company share','measure','program_share'),
]:
    b={**base,key:value}; check('reject incompatible fixture: '+name,not comparable(base,b))
check('positive identical comparison control',comparable(base,dict(base)))
check('positive available publication control',available_as_of('2026-07-30','2026-09-23'))
check('post-cutoff AAR release is unavailable',not available_as_of('2026-09-29','2026-09-23'))
check('unknown publication does not become current',not available_as_of(None,'2026-09-23'))

model=(ROOT/'INDUSTRIALS_WAVE4_ECONOMIC_MODEL_2026-09-23.md').read_text()
idx=json.loads((ROOT/'WAVE4_SOURCE_INDEX.json').read_text())
check('26 indexed primary-source records',len(idx['sources'])==26)
check('unique source URLs',len(set(idx['sources'].values()))==26)
check('24 distinct research slices',len(set(re.findall(r'W4-R\d{2}',model)))==24)
check('12 distinct hypotheses',len(set(re.findall(r'W4-H\d{2}',model)))==12)
check('32 distinct application requirements',len(set(re.findall(r'W4-T\d{2}',model)))==32)
check('all explicit source citations resolve',set(re.findall(r'W4-S\d{2}',model))<=set(idx['sources']))
check('mission remains incomplete','MISSION_COMPLETE: false' in model)
check('Fable handoff explicitly withheld','final Fable CEO handoff remains withheld' in model)
check('empirical validation not claimed','No such empirical evaluation has been completed' in model)
check('hypothetical scope stated','not an actual one-year visit forecast' in model)

report={'passed':sum(r['passed'] for r in results),'failed':sum(not r['passed'] for r in results),'checks':results,
        'limits':'Authored research arithmetic/meaning fixtures and document checks only; no application, factual-review, predictive or production proof.'}
(ROOT/'WAVE4_CHECK_REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
print(f"{report['passed']} PASS, {report['failed']} FAIL")
for item in results:
    if not item['passed']: print('FAIL',item['name'])
sys.exit(bool(report['failed']))
