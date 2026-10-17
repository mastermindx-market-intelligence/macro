"""Local research arithmetic/semantic checks; NOT application tests or backtests.

Run from any directory with: python verify_wave2_research.py
Only the adjacent, original research files are read; no network or production writes.
"""
from __future__ import annotations
from decimal import Decimal as D
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
FP = ROOT / 'INDUSTRIALS_WAVE2_RESEARCH_FIXTURES_2026-09-23.json'
fixture = json.loads(FP.read_text(encoding='utf-8'))
checks: list[dict[str, str]] = []
outputs: dict[str, str] = {}

def check(name: str, condition: bool) -> None:
    checks.append({'name': name, 'result': 'PASS' if condition else 'FAIL'})

def close(actual: D, expected: str, tolerance: str = '0.0001') -> bool:
    return abs(actual-D(expected)) <= D(tolerance)

def ratio(a: str, b: str) -> D:
    if D(b) == 0:
        raise ValueError('Zero denominator')
    return D(a)/D(b)*100

def stable_value(g: D, r: D, ret: D) -> D:
    if not (D(0) <= g < r and ret > 0 and g <= ret):
        raise ValueError('Unsupported stable-state assumptions')
    return (1-g/ret)/(r-g)

def reject_invalid_case(case: dict) -> None:
    """Tiny illustrative checks on these fixtures, not a general data-admission API."""
    kind = case['kind']
    if kind == 'compare':
        if case['left'] != case['right']:
            raise ValueError('Comparison definitions differ')
    elif kind in {'denominator', 'measure', 'statement'}:
        if case['actual'] != case['requested']:
            raise ValueError('Unsupported meaning substitution')
    elif kind == 'stable_value':
        stable_value(D(case['growth']), D(case['cost_of_capital']), D(case['incremental_return']))
    elif kind == 'aggregation':
        ids = {item['id'] for item in case['items']}
        if any(item.get('parent') in ids for item in case['items']):
            raise ValueError('Overlapping purchase boundaries')
    else:
        raise KeyError(f'Unexpected local fixture kind: {kind}')

E = fixture['examples']
e = E['eaton_margin']
value=(D(e['current'])-D(e['prior_year']))*100
outputs['eaton_yoy_margin_bp']=str(value)
check('EA annual and sequential changes differ in sign', value == -200 and D(e['reported_sequential_change_bp']) > 0)
s=E['siemens_scoped_shares']
for key,num,den,expected in [('siemens_DI_software_percent','di_software','di_revenue','36.2936'),('siemens_SI_service_percent','si_service','si_revenue','19.6649')]:
    value=ratio(s[num],s[den]);outputs[key]=str(value);check(key,close(value,expected))
s=E['siemens_profit_bridge'];check('Siemens Profit less purchased amortization equals EBIT',D(s['di_profit'])-D(s['purchased_intangible_amortization'])==D(s['di_ebit']))
s=E['rockwell_scoped_share'];value=ratio(s['software_control_sales'],s['group_sales']);outputs['rockwell_composite_segment_share_percent']=str(value);check('Rockwell composite segment share',close(value,'32.4687'))
s=E['nvent_reconciliation'];value=ratio(s['systems_sales'],s['group_sales']);outputs['nvent_systems_segment_share_percent']=str(value);check('nVent segment share',close(value,'72.8675'))
check('nVent segment sum minus enterprise cost equals group profit',D(s['systems_adjusted_operating_income'])+D(s['connections_adjusted_operating_income'])-D(s['enterprise_cost'])==D(s['group_adjusted_operating_income']))
s=E['abb_cash']
for scope,target in [('consolidated','8.5930'),('continuing','34.1916')]:
    value=ratio(s[f'{scope}_current'],s[f'{scope}_prior'])-100;outputs[f'abb_{scope}_cash_growth_percent']=str(value);check(f'ABB {scope} cash growth',close(value,target))
s=E['vertiv_cash'];wc=sum(D(v) for v in s['working_capital'].values());check('Vertiv all working-capital components reconcile',wc==D(s['reported_wc_total']))
fcf=D(s['cfo'])-D(s['capex'])-D(s['capitalized_software']);outputs['vertiv_fcf_usdm']=str(fcf);check('Vertiv reported adjusted FCF arithmetic',fcf==D(s['reported_adjusted_fcf']))
outputs['vertiv_CFO_less_all_WC_decomposition_not_normalized']=str(D(s['cfo'])-wc)
s=E['keyence_period'];value=ratio(s['operating_income_current'],s['sales_current']);outputs['keyence_operating_margin_percent']=str(value);check('Keyence margin arithmetic',close(value,'53.9713'))
check('Keyence sign and actual fiscal ending retained',D(s['prior_europe_others_local_growth_percent']) < 0 and s['period_end']=='2026-06-20')
s=E['smc_bridge'];check('SMC rounded sales bridge within stated tolerance',abs(sum(D(s[k]) for k in ['volume','price','currency'])-D(s['reported_growth']))<=D(s['rounding_tolerance_pp']))
b=s['profit_bridge_jpy_100m'];check('SMC displayed operating-profit bridge reconciles',sum(D(v) for k,v in b.items() if k!='ending_profit')==D(b['ending_profit']))
s=fixture['hypothetical_scenarios']['profit_bridge'];rev=D(s['base_revenue'])*(1+D(s['volume_growth']))*(1+D(s['price_growth']));vc=D(s['base_variable_cost'])*(1+D(s['volume_growth']))*(1+D(s['unit_variable_cost_growth']));profit=rev-vc-D(s['next_fixed_cost']);outputs['hypothetical_next_revenue']=str(rev);outputs['hypothetical_next_operating_profit']=str(profit)
check('Hypothetical price-volume-cost scenario',rev==D('112.2') and profit==D('21.555'))
s=fixture['hypothetical_scenarios']['reinvestment'];nopat=D(s['next_revenue'])*D(s['operating_margin'])*(1-D(s['tax_rate']));growth=D(s['next_revenue'])-D(s['base_revenue']);a=nopat-growth/D(s['incremental_sales_to_capital_a']);b=nopat-growth/D(s['incremental_sales_to_capital_b']);outputs['hypothetical_growth_cash_a']=str(a);outputs['hypothetical_growth_cash_b']=str(b)
check('Hypothetical reinvestment economics differ despite same profit',a==13 and b==-2)
s=fixture['hypothetical_scenarios']['stable_value'];g=D(s['growth']);r=D(s['cost_of_capital_base']);a=stable_value(g,r,D(s['incremental_return_a']));b=stable_value(g,r,D(s['incremental_return_b']));c=stable_value(g,D(s['cost_of_capital_higher']),D(s['incremental_return_b']));outputs.update({'hypothetical_EV_NOPAT_A':str(a),'hypothetical_EV_NOPAT_B':str(b),'hypothetical_EV_NOPAT_C':str(c)})
check('Stable value A',a==D('12.5'));check('Stable value B',close(b,'14.583333'));check('Stable value C',close(c,'11.666667'))
for case in fixture['semantic_negative_cases']:
    try:
        reject_invalid_case(case)
    except ValueError:
        check(case['id']+': '+case['reason'],True)
    else:
        check(case['id']+': '+case['reason'],False)
# Positive control: identical labels should not be rejected by this narrow checker.
try:
    reject_invalid_case({'kind':'compare','left':{'scope':'x'},'right':{'scope':'x'}})
except ValueError:
    check('Identical local comparison is accepted',False)
else:
    check('Identical local comparison is accepted',True)
text=(ROOT/'INDUSTRIALS_WAVE2_EVIDENCE_2026-09-23.md').read_text()
ids=re.findall(r'^## (W2-S\d+)',text,re.M)
check('26 unique sequential source IDs',ids==[f'W2-S{i:02d}' for i in range(1,27)])
model=(ROOT/'INDUSTRIALS_WAVE2_ECONOMIC_MODEL_2026-09-23.md').read_text()
check('28 unique proposed research slices',set(re.findall(r'\| (AE-\d\d) ',model))=={f'AE-{i:02d}' for i in range(1,29)})
check('24 unique proposed application acceptance cases',set(re.findall(r'\| (AE-T\d\d) ',model))=={f'AE-T{i:02d}' for i in range(1,25)})
check('Fixture source references exist',set(re.findall(r'W2-S\d+',FP.read_text()))<=set(ids))
check('Hypothetical and production limitations are explicit','Hypothetical' in model and 'No empirical backtest' in model and 'not an enrolled production contract' in fixture['purpose'])
check('No drafting placeholders',not re.search(r'\b(TODO|TBD|FIXME)\b',text+model))
artifacts={}
for p in sorted(ROOT.glob('*')):
    if p.is_file() and p.suffix in {'.md','.json','.py'} and p.name not in {'verification_report.json','extend_evidence.py'}:
        raw=p.read_bytes();artifacts[p.name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'git_blob_sha1':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}
report={'scope':'Local research document, arithmetic and fixture guard checks only. Not independent source review, application tests, backtests, forecast validation or browser acceptance.','passed':sum(c['result']=='PASS' for c in checks),'failed':sum(c['result']=='FAIL' for c in checks),'checks':checks,'derived_values':outputs,'artifacts':artifacts}
(ROOT/'verification_report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['scope','passed','failed']},indent=2))
for c in checks:
    if c['result']=='FAIL': print(c)
if report['failed']:
    raise SystemExit(1)
