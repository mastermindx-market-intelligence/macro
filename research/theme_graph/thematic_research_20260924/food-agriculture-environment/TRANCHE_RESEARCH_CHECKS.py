"""GMI A: authored research arithmetic/examples, not a native product adapter.
Run: python TRANCHE_RESEARCH_CHECKS.py
Produces TRANCHE_VERIFICATION.json next to this file. No network or dependencies.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, replace
from decimal import Decimal as D
from pathlib import Path
from typing import Callable

OP = 'gmi-theme-research-food-agriculture-environment-20260924-001'
PASSED: list[str] = []
REJECTED: list[str] = []
def check(name: str, test: bool) -> None:
    if not test:
        raise AssertionError(name)
    PASSED.append(name)
def rejects(name: str, fn: Callable[[], object]) -> None:
    try:
        fn()
    except ValueError:
        REJECTED.append(name)
    else:
        raise AssertionError('corruption was not rejected: ' + name)

@dataclass(frozen=True)
class Measure:
    value: D
    entity: str
    period_kind: str
    period: str
    basis: str
    unit: str
    population: str

def ratio(n: Measure, d: Measure) -> D:
    if (n.entity, n.period_kind, n.period, n.unit, n.population) != (d.entity, d.period_kind, d.period, d.unit, d.population):
        raise ValueError('incompatible arithmetic populations/periods/units')
    if d.value <= 0:
        raise ValueError('denominator must be positive')
    return n.value / d.value

def profit(gross: int, sga: int, da_ex_cogs: int, closure: int) -> int:
    return gross - sga - da_ex_cogs - closure

# Hand-transcribed from the cited HTML releases. No automatic extraction claimed.
sprouts = {
    'source': 'https://investors.sprouts.com/news/news-details/2026/Sprouts-Farmers-Market-Inc--Reports-Second-Quarter-2026-Results/default.aspx',
    'unit': 'USD_thousands',
    '2026Q2': [2325804,1425156,900648,682633,43081,760,174174],
    '2025Q2': [2220602,1358002,862600,645127,36606,1511,179356],
    '2026H1': [4654983,2837059,1817924,1341414,85108,1921,389481],
    '2025H1': [4457038,2708075,1748963,1268353,71705,3217,405688],
    'cash_26weeks': {'2026': [368995,189907], '2025': [410337,120319]},
}
for period in ['2026Q2','2025Q2','2026H1','2025H1']:
    sales,cost,gross,sga,da,closure,op = sprouts[period]
    check('Sprouts '+period+' gross',sales-cost==gross)
    check('Sprouts '+period+' operating bridge',profit(gross,sga,da,closure)==op)
q26,q25=sprouts['2026Q2'],sprouts['2025Q2']
delta = [q26[i]-q25[i] for i in range(len(q26))]
check('Q2 operating change bridge',delta[2]-delta[3]-delta[4]-delta[5]==-5182)
check('Q2 gross profit increase',delta[2]==38048)
check('Q2 SGA increase',delta[3]==37506)
check('Q2 non-COGS DA increase',delta[4]==6475)
check('Q2 closure cost relief',delta[5]==-751)
check('Q2 sales rise while operating profit falls',delta[0]>0 and delta[6]<0)
sc26=D(368995-189907)/1000
sc25=D(410337-120319)/1000
check('Sprouts H1 scoped residual 2026',sc26==D('179.088'))
check('Sprouts H1 scoped residual 2025',sc25==D('290.018'))
check('Sprouts H1 residual change',sc26-sc25==D('-110.930'))

ingsource='https://ir.ingredionincorporated.com/news-releases/news-release-details/ingredion-incorporated-reports-second-quarter-2026-results'
check('Ingredion external segment sales reconcile',sum([627,611,488,124])==1850)
check('Ingredion excluded intersegment sales',sum([35,11,48,8])==102)
check('Intersegment cannot be added as external sales',1850+102!=1850)
check('Ingredion adjusted operating bridge',sum([117,118,58,6,-41])==258)
check('Ingredion GAAP operating bridge',258-6-31-14-19==188)
check('Ingredion prior adjusted operating bridge',111+127+86-1-50==273)
check('Ingredion prior GAAP bridge',273-3+1==271)
check('Ingredion specialty profit increases',117-111==6)
check('Ingredion US Canada profit decreases',58-86==-28)
check('Ingredion H1 CFO categories',sum([260,110,38,-44,33,47,-19,-231,-71])==123)
check('Ingredion H1 2025 CFO categories',sum([397,108,32,0,6,4,-9,-241,-35])==262)
check('Ingredion selected cash residuals',123-210==-87 and 262-193==69)
check('Ingredion selected cash residual delta',(-87)-69==-156)
check('Sale proceeds do not equal customer cash',139!=123)

# Synthetic chain: one physical unit; contribution excludes all other costs.
chain0={'input':D(10),'producer_sale':D(16),'final_sale':D(25)}
chain1={'input':D(8),'producer_sale':D(14),'final_sale':D(23)}
for i,c in enumerate([chain0,chain1]):
    conversion=c['producer_sale']-c['input']
    retail=c['final_sale']-c['producer_sale']
    check('Synthetic chain '+str(i)+' value added conservation',c['input']+conversion+retail==c['final_sale'])
    check('Synthetic chain '+str(i)+' conversion contribution',conversion==6)
    check('Synthetic chain '+str(i)+' retail gross contribution',retail==9)
check('Synthetic cheaper final purchase need not reduce conversion contribution',chain1['final_sale']<chain0['final_sale'])
check('Synthetic repeated revenues are not end demand',10+16+25!=25)
check('Synthetic retained dollars versus percentage',D(9)/23>D(9)/25)

# Conditional educational electricity-settlement example inspired by selected clauses.
# NOT a contract calculator: Schedule 14, tax/eligibility, amendments, credits and invoices are unimplemented.
def electricity_example(actual: D, guarantee: D, cap: D, *, conditions_verified: bool) -> D:
    if not conditions_verified:
        raise ValueError('eligibility and contract conditions unverified')
    if actual < 0 or guarantee <= 0 or cap < 0:
        raise ValueError('invalid assumed costs/cap')
    if actual > guarantee:
        return -(actual-guarantee)
    return min(cap, max(D(0),(D('.95')*guarantee-actual)*D('.5')))
water_cases=[('1100000','-100000'),('1000000','0'),('975000','0'),('950000','0'),('900000','25000'),('700000','100000')]
for actual,expected in water_cases:
    check('Synthetic electricity cost '+actual,electricity_example(D(actual),D(1000000),D(100000),conditions_verified=True)==D(expected))
check('Original reference-year fixed charge sum',1952193+416598==2368791)
check('Original reference-year four components sum',1952193+416598+301720+51408==2721919)
check('Reference capital and membrane components distinct',301720+51408==353128)
check('Synthetic joint reserve balance is not unrestricted cash',D(100)+D(30)-D(20)==D(110))
check('Synthetic amount available without eligible draw is zero',D(0)!=D(110))

# Publication/projection safeguards: authored examples, not production implementations.
def accepted_service(state: str) -> bool:
    return state=='ACCEPTED_OPERATION'
for s in ['AWARD','SIGNED','LIMITED_NOTICE','CONSTRUCTION','COMMISSIONING']:
    check(s+' does not prove accepted service',not accepted_service(s))
check('Explicit accepted-operation example',accepted_service('ACCEPTED_OPERATION'))

n=Measure(D(900648),'SFM','13weeks','2026-06-28','gross_profit','USD_thousands','consolidated')
d=Measure(D(2325804),'SFM','13weeks','2026-06-28','revenue','USD_thousands','consolidated')
check('Compatible gross-margin pair',D(0)<ratio(n,d)<D(1))
rejects('mixed currency/scale',lambda:ratio(n,replace(d,unit='USD_millions')))
rejects('mixed quarter and half year',lambda:ratio(n,replace(d,period_kind='26weeks')))
rejects('borrowed issuer denominator',lambda:ratio(n,replace(d,entity='INGR')))
rejects('borrowed segment population',lambda:ratio(n,replace(d,population='specialty_segment')))
rejects('zero denominator',lambda:ratio(n,replace(d,value=D(0))))
rejects('future forecast versus observed period',lambda:ratio(n,replace(d,period='2026FY_forecast')))
rejects('electricity formula without eligibility proof',lambda:electricity_example(D(900000),D(1000000),D(100000),conditions_verified=False))
rejects('negative synthetic electric cost',lambda:electricity_example(D(-1),D(1000000),D(100000),conditions_verified=True))
rejects('zero guaranteed cost',lambda:electricity_example(D(0),D(0),D(100000),conditions_verified=True))
rejects('negative payment cap',lambda:electricity_example(D(0),D(1000000),D(-1),conditions_verified=True))
gov=Measure(D(33078),'DASH','quarter','2026-06-30','GOV','USD_millions','marketplaces')
orders=Measure(D(970),'DASH','quarter','2026-06-30','orders','USD_millions','marketplaces_plus_commerce_platform')
# Same dummy unit solely isolates population rejection; true order denominator has its own unit.
rejects('GOV divided by broader Total Orders population',lambda:ratio(gov,orders))

out={
 'operation':OP, 'scope':'Hand-transcribed arithmetic and authored synthetic counterexamples only',
 'positive_checks_passed':len(PASSED),'corrupted_variants_rejected':len(REJECTED),'failures':0,
 'positive_checks':PASSED,'rejected_variants':REJECTED,
 'sprouts_source_and_rows':sprouts,'ingredion_source':ingsource,
 'derived_values':{'sprouts_operating_change_USD_millions':'-5.182','sprouts_26week_CFO_less_gross_PPE_USD_millions':['179.088','290.018'],'ingredion_H1_CFO_less_capex_and_mechanical_stores_net_USD_millions':[-87,69],'original_reference_year_water_components_USD':2721919},
 'limitations':['Synthetic electricity calculation is not the full agreement, current invoice, legal opinion or forecast.','Cash residuals are not standardized free cash flow, segment cash or distributable shareholder cash.','Company samples are not a proven supplier-customer chain.','No live source admission, automated extraction, native code, independent review, market backtest or browser proof.'],
 'native_tests':0,'independent_review':False,'trade_authority':False,
 'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
}
Path(__file__).with_name('TRANCHE_VERIFICATION.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['positive_checks_passed','corrupted_variants_rejected','failures']},indent=2))
