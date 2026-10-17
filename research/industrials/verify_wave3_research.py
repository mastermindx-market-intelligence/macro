"""Narrow research-fixture checks; not a product gate or independent factual review."""
from __future__ import annotations
import contextlib
import io
import json
import math
import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()):
    env = runpy.run_path(str(ROOT / 'calculate_wave3.py'))
data = env['out']
r = data['reported_calculations']
h = data['hypothetical']
checks: list[dict] = []

def check(name: str, condition: bool, kind: str = 'arithmetic') -> None:
    checks.append(dict(name=name, kind=kind, passed=bool(condition)))

def near(name: str, actual: float, expected: float, tol: float = 1e-6) -> None:
    check(name, math.isfinite(actual) and abs(actual - expected) <= tol)

def raises_value_error(name: str, function, *args) -> None:
    try:
        function(*args)
    except ValueError:
        check(name, True, 'invalid_input')
    else:
        check(name, False, 'invalid_input')

near('Deere two-year sales', r['deere_ppa']['sales_change_2024_2026_pct'], -21.5924691116)
near('Deere two-year profit', r['deere_ppa']['profit_change_2024_2026_pct'], -54.6471600688)
near('CNH sales', r['cnh_construction']['sales_growth_pct'], 12.0310478655)
near('CNH EBIT', r['cnh_construction']['ebit_growth_pct'], -57.1428571429)
check('AGCO recast changes apparent rate', r['agco_scope']['valid_recast_growth_pct'] > r['agco_scope']['invalid_mixed_scope_apparent_growth_pct'])
near('URI additive growth bridge', r['uri']['bridge_sum_pct'], 12.7)
near('URI cash reconciliation', r['uri']['fcf'], 1149)
near('URI investment versus payment gap', r['uri']['capex_minus_cash_payments'], 211)
check('URI cash-flow directions differ', r['uri']['cfo_growth_pct'] > 0 > r['uri']['fcf_growth_pct'])
check('Herc EBITDA and EPS directions differ', r['herc']['ebitda_growth_pct'] > 0 > r['herc']['adjusted_eps_growth_pct'])
near('Grainger FCF bridge', r['grainger']['cfo_contribution'] + r['grainger']['lower_capex_contribution'], 131)
check('Wesco reporting-window directions differ', r['wesco']['quarter_growth_pct'] < 0 < r['wesco']['half_growth_pct'])
near('Broker revenue-denominator margin', r['chrw']['revenue_margin_pct'], 5.183176337397433)
near('Broker AGP-denominator margin', r['chrw']['agp_margin_pct'], 34.655119612556676)
near('ODFL component product', r['odfl_august']['components_implied_tons_change_pct'], -.7408)
near('ODFL unexplained residual', r['odfl_august']['reported_minus_components_pp'], -.1592)
check('Channel shipment sequence', [x['shipments'] for x in h['channel']] == [400,500,600])
check('Channel profit sequence', [x['operating_profit'] for x in h['channel']] == [500,800,1100])
check('Channel retail remains flat', len({x['retail'] for x in h['channel']}) == 1)
near('Downside shipments', h['channel_retail_downside']['shipments'], 360)
near('Downside profit', h['channel_retail_downside']['operating_profit'], 380)
near('Months supply increases despite fewer units', h['months_supply']['later_months'], 10.125)
near('Replacement baseline EAC', h['replacement_baseline']['replace_eac'], 46.7502, .0001)
check('Baseline marginally favors replacing', h['replacement_baseline']['replace_eac'] < h['replacement_baseline']['keep_eac'])
check('Lower current trade value reverses choice', h['replacement_lower_trade_value']['keep_eac'] < h['replacement_lower_trade_value']['replace_eac'])
near('Trade gap rises', h['replacement_lower_trade_value']['trade_in_cash_gap'] - h['replacement_baseline']['trade_in_cash_gap'], 20)
near('Rental baseline NPV', h['rental_base']['npv'], 3.79028, .0001)
near('Rental higher purchase cost NPV', h['rental_higher_purchase_price']['npv'], -6.20972, .0001)
near('Rental lower residual NPV', h['rental_lower_residual']['npv'], -5.95869, .0001)
near('Rental lower cash NPV', h['rental_lower_use']['npv'], -11.76832, .0001)
near('Fuel pass-through ratio', h['fuel_pass_through']['after_operating_ratio_pct'], 83.3333333333)
check('Fuel pass-through profit unchanged', h['fuel_pass_through']['after_profit'] == h['fuel_pass_through']['before_profit'])
raises_value_error('Zero growth denominator refused', env['pct'], 1, 0)
raises_value_error('Negative channel shipments refused', env['channel'], 100, 10, 10)
raises_value_error('Invalid discount rate refused', env['pv_annuity'], -1, 5)
raises_value_error('Invalid horizon refused', env['pv_annuity'], .1, 0)
raises_value_error('Negative asset residual refused', env['asset_case'], 100, 20, -1)

# Deliberately small comparator, only for authored fixtures; not deployed validation.
REQUIRED = ('business_scope','metric','denominator','window','unit','method','population','vintage_mode')
def comparable(a: dict, b: dict, decision_at: str) -> bool:
    if a.get('conflict') or b.get('conflict'):
        return False
    if any(a.get(k) is None or b.get(k) is None or a[k] != b[k] for k in REQUIRED):
        return False
    return all(x.get('published_at') and x['published_at'] <= decision_at for x in (a,b))

base = dict(business_scope='business_A_recast', metric='rental_yield', denominator='average_OEC',
            window='trailing_12_month', unit='percent', method='reported_ancillary_included',
            population='eligible_fleet_v1', vintage_mode='as_known', published_at='2026-08-01', conflict=False)
check('Matching comparison positive control', comparable(base, dict(base), '2026-09-23'), 'positive_control')
for label, patch in [
    ('Unrecast business geography', {'business_scope':'old_business'}),
    ('Different metric', {'metric':'time_utilization'}),
    ('Ending versus average OEC', {'denominator':'ending_OEC'}),
    ('Monthly versus trailing window', {'window':'month'}),
    ('Different units', {'unit':'currency'}),
    ('Different ancillary coverage', {'method':'ancillary_excluded'}),
    ('Changed telemetry/lender population', {'population':'eligible_fleet_v2'}),
    ('Latest-restated versus as-known', {'vintage_mode':'latest_restated'}),
    ('Future publication lookahead', {'published_at':'2026-10-01'}),
    ('Unknown publication time', {'published_at':None}),
    ('Conflicting source definition', {'conflict':True}),
    ('Missing denominator not zero', {'denominator':None}),
    ('Estimated versus transacted method', {'method':'estimated_value'}),
    ('Aged share versus sale count', {'metric':'count_of_sales'})
]:
    check(label+' refused', not comparable(base, dict(base, **patch), '2026-09-23'), 'negative_comparison')

model = (ROOT / 'INDUSTRIALS_WAVE3_ECONOMIC_MODEL_2026-09-23.md').read_text()
extra = (ROOT / 'INDUSTRIALS_WAVE3_ASSET_MARKET_EVIDENCE_2026-09-23.md').read_text()
ids = set(re.findall(r'W3-S\d{2}', model))
allowed = {f'W3-S{i:02}' for i in range(1,32)}
check('Model citations inside 31-record bibliography', ids <= allowed, 'integrity')
check('Additional source headings exact', set(re.findall(r'^## (W3-S\d{2})',extra,re.M)) == {f'W3-S{i:02}' for i in range(28,32)}, 'integrity')
check('34 unique acceptance case rows', len(re.findall(r'^\| W3-T\d{2} \|',model,re.M)) == 34, 'integrity')
check('24 unique slice rows', len(re.findall(r'^\| (?:MR|RF|DS|TR)-\d{2} ',model,re.M)) == 24, 'integrity')
check('Mission explicitly incomplete', 'MISSION_COMPLETE: false' in model, 'integrity')
check('Scenarios not current fair value', data['research_only'] and not data['current_fair_value_or_forecast'], 'integrity')
check('Source conflict preserved', 'source conflict' in model and 'ending OEC' in model and 'average OEC' in model, 'integrity')
check('Unexplained residual preserved', 'explanation is not established' in model and 'automatically' in model, 'integrity')
check('New observations not claimed full transaction panel', 'not a recovered full transaction panel' in model, 'integrity')
check('No placeholder TODO markers', not re.search(r'\b(TODO|TBD|FIXME)\b',model+'\n'+extra), 'integrity')
report = dict(scope='Research arithmetic, authored negative comparisons and document integrity only',
              independent_factual_review=False, application_tests=False, backtest=False,
              passed=sum(c['passed'] for c in checks), failed=sum(not c['passed'] for c in checks),
              checks=checks)
(ROOT / 'INDUSTRIALS_WAVE3_LOCAL_CHECKS_2026-09-23.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('scope','passed','failed')},indent=2))
for c in checks:
    if not c['passed']:
        print('FAIL:', c['name'])
raise SystemExit(1 if report['failed'] else 0)
