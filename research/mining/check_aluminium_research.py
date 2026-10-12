"""Pass07 reproducible research arithmetic and compatibility illustrations.

Run beside both reports: python check_aluminium_research.py
Standard library only. No network, product imports or trading output.
These pedagogical examples are not production accounting/contract validation.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
REPORT = 'MINING_ALUMINIUM_ENERGY_ECONOMICS_2026-09-23.md'
COVERAGE = 'MINING_COVERAGE_AND_DESIGN_FRONTIER_2026-09-23.md'
text = (ROOT / REPORT).read_text(encoding='utf-8')
coverage = (ROOT / COVERAGE).read_text(encoding='utf-8')
checks: list[dict] = []

def check(name: str, condition: bool, evidence: object) -> None:
    checks.append({'check': name, 'passed': bool(condition), 'evidence': evidence})

def rounded(value: D, places: str = '.0001') -> D:
    return value.quantize(D(places))

def pct(current: str, prior: str) -> D:
    return (D(current) / D(prior) - 1) * 100

def expect_refusal(name: str, fn) -> None:
    try:
        fn()
    except ValueError as exc:
        check(name, True, str(exc))
    else:
        check(name, False, 'No required refusal')

# Document checks do not independently authenticate or fact-check sources.
cases = re.findall(r'^### (AL-C\d{2}) ', text, re.M)
hypotheticals = re.findall(r'^### (AL-H\d{2}) ', text, re.M)
personas = re.findall(r'^### (AL-P\d{2}) ', text, re.M)
sources = re.findall(r'^- \*\*(AL-S\d{2})\.', text, re.M)
requirements = re.findall(r'^\| (ME-\d{2}) \|', text, re.M)
check('twelve_dossiers', cases == [f'AL-C{i:02}' for i in range(1,13)], cases)
check('six_hypotheticals', hypotheticals == [f'AL-H{i:02}' for i in range(1,7)], hypotheticals)
check('four_personas', personas == [f'AL-P{i:02}' for i in range(1,5)], personas)
check('nineteen_source_records', sources == [f'AL-S{i:02}' for i in range(1,20)], sources)
check('twenty_eight_requirements', requirements == [f'ME-{i:02}' for i in range(1,29)], requirements)
check('references_resolve', set(re.findall(r'AL-S\d{2}', text)) == set(sources), 'No unknown source identifier')
check('research_and_handoff_held', '**Mission complete:** false.' in text and '**Final Fable implementation handoff:** not created.' in text, 'Explicit incomplete scope')
check('mirror_limits_preserved', 'Screenshot route failed' in text and 'no table-derived arithmetic' in text, 'Chalco visual verification not invented')
check('seven_canonical_passes', re.findall(r'^\| (P\d{2}) \|', coverage, re.M) == [f'P{i:02}' for i in range(1,8)], 'Existing coverage updated')
check('corpus_table_contiguous', 'supplier value capture |\n| P07' in coverage, 'Single Markdown table')
check('canonical_P05_preserved', '42c90b4634b4b408c014b7ccb335744adb79bf48' in coverage and 'DO_NOT_PUBLISH_DUPLICATE' in coverage, 'Parallel P05 excluded')
check('remaining_battery_gap', 'nickel/cobalt and graphite/anode' in coverage, 'Next regime not declared complete')
check('current_procedure_pin', 'a7d2b3049e5cdc523e91e61a6e9d70a1cb911157' in text and 'a7d2b3049e5cdc523e91e61a6e9d70a1cb911157' in coverage, 'Same protected SHA')

# Sourced selected arithmetic; source classifications are retained in the report.
check('Hydro_stage_directions', D('522') < D('1521') and D('6421') > D('2423') and D('499') < D('1069'), 'AL-S01; unlike stages, not a causal model')
check('Hydro_energy_flow_table', 2009 + 2915 - 4701 - 221 == 2, 'GWh, Q2 2026, AL-S02; table arithmetic not physical audit')
fcf = 9031 - 2469 - 22 + 396 + 1566 - 4539
check('Hydro_FCF_bridge', fcf == 3963, 'NOK millions, Q2 2026, AL-S02')
check('Hydro_simple_cash_not_adjusted_FCF', 9031 + 396 != fcf, {'operating_plus_investing':9427, 'adjusted_FCF':fcf})
check('Eviny_total_energy', D('.5') * D('10') == D('5'), 'TWh, 2031-2040; AL-S03')
check('Eviny_annual_MWh', D('.5') * D('1000000') == D('500000'), 'Annual energy, not MW capacity')
check('Slovalco_tranches', 75000 + 100000 == 175000, 'Capacity tranches, not annual actual output; AL-S05')
check('EGA_restored_cell_fraction', rounded(D(315)/D(1262)*100) == D('24.9604'), 'AL-S16; not saleable-output fraction')
check('Novelis_adjusted_FCF', -455 - 676 - 3 == -1134, 'USD millions, quarter ended June30; AL-S08')
check('Novelis_earnings_cash_opposite', D(516)>D(416) and D(-455)<D(105), 'AL-S08; causes require source, not this arithmetic')
check('Constellium_Q2_matched', 439-129 == 310 and 146-(-19) == 165, 'USD millions; AL-S09')
check('Constellium_H1_matched', 798-226 == 572, 'USD millions; AL-S09')
check('Constellium_H2_guidance_remainder', (980+1020)//2-(798-226) == 428, 'Guidance arithmetic, not a forecast')
check('Constellium_wrong_remainder_detected', 1000-798 == 202 and 202 != 428, 'Inclusion mismatch must not silently pass')
check('Constellium_growth_definitions', rounded(pct('310','165')) == D('87.8788') and rounded(pct('439','146')) == D('200.6849'), 'Matched vs headline, AL-S09')
actual_coupon = D('1500')*D('.06625')+D('1100')*D('.06875')
assumed_coupon = D('1300')*D('.07')+D('1300')*D('.0675')
check('Alcoa_actual_nominal_coupon', actual_coupon == D('175'), 'USD million/year, actual terms, AL-S12')
check('Alcoa_assumed_nominal_coupon', assumed_coupon == D('178.75'), 'Earlier pro forma assumptions, AL-S11')
check('Alcoa_coupon_delta', assumed_coupon-actual_coupon == D('3.75'), 'Not complete accounting-interest change')
check('Nexans_arithmetic_average', D(85000)/5 == D(17000), 'AL-S13; not an annual delivery schedule')

# Explicitly invented cases, not issuer parameter estimates.
check('H01_fixed_energy', 3300-600-1400 == 1300, 'Invented product/energy costs')
check('H01_partial_index', D(600)+D(600)*D('.5')*D('.1') == D(630) and 3300-630-1400 == 1270, 'No actual Century coefficient')
check('H01_full_index', 3300-660-1400 == 1240, 'Hypothetical comparison')
check('H02_area_basis', 100000*110 - 100000*(90-50) == 7000000, 'Invented physical/hedge prices')
check('H02_remaining_cost_increase', 7000000 - 100000*60 == 1000000, 'Location mismatch not eliminated')
check('H03_net_external_seller', 100*10-80*10 == 20*10 == 200, 'Invented matched boundaries')
check('H03_net_external_buyer', (60-80)*10 == -200, 'Integrated label does not fix sign')
funding = D(100000)*D(30)/D(365)*D(500)
check('H04_inventory_funding', rounded(funding/D(1000000),'.001') == D('4.110'), 'Inventory only; hypothetical')
check('H04_carrying_cost', rounded(funding*D('.08')/D(1000000),'.001') == D('.329'), 'Annual financing, not current inventory purchase')
check('H04_contribution_unchanged', 100000*200 == 20000000, 'Assumed constant retained contribution')
check('H05_base_recycling', D(2600)-D(1500)/D('.75')-D(300) == D(300), 'Input vs output tonnes')
check('H05_yield_improvement', D(2600)-D(1500)/D('.8')-D(300) == D(425), 'Hypothetical grade/yield held otherwise constant')
check('H05_feed_cost_pressure', rounded(D(2600)-D(1700)/D('.75')-D(300)) == D('33.3333'), 'Hypothetical inputs')
check('H06_two_sided_premium', 120-100 == 20 and 100-90 == 10 and 70<90, 'Buyer and producer feasibility, not a carbon quote')

# Small compatibility demonstrations; these are not product implementations.
@dataclass(frozen=True)
class Observation:
    amount: D
    unit: str
    period: str
    basis: str

def difference(a: Observation, b: Observation) -> D:
    if (a.unit,a.period,a.basis) != (b.unit,b.period,b.basis):
        raise ValueError('Incompatible unit, period or basis')
    return a.amount-b.amount

base = Observation(D(1000),'USD_million','FY2026','EBITDA_excluding_lag')
check('compatible_observation_example', difference(base,replace(base,amount=D(572))) == D(428), 'Pedagogical same-basis example only')
expect_refusal('refuse_unmatched_lag', lambda:difference(base,replace(base,amount=D(798),basis='EBITDA_including_lag')))
expect_refusal('refuse_unmatched_currency', lambda:difference(base,replace(base,unit='EUR_million')))
expect_refusal('refuse_unmatched_period', lambda:difference(base,replace(base,period='FY2025')))
expect_refusal('refuse_NPV_as_annual', lambda:difference(base,replace(base,unit='USD_million_NPV',basis='discounted_value')))

def energy_for_year(amount:D, unit:str, start:int, end:int, year:int) -> D:
    if unit != 'TWh_per_year' or not start<=year<=end:
        raise ValueError('Energy unit or effective year unsupported')
    return amount*D(1000000)

check('future_contract_eligible_year', energy_for_year(D('.5'),'TWh_per_year',2031,2040,2035)==D(500000), 'Only hypothetical parser compatibility')
expect_refusal('refuse_future_contract_for_2026', lambda:energy_for_year(D('.5'),'TWh_per_year',2031,2040,2026))
expect_refusal('refuse_MW_as_annual_energy', lambda:energy_for_year(D(545),'MW',2031,2040,2035))

# No completeness percentage, market price or trade is calculated.
def digest(path:Path) -> dict:
    raw=path.read_bytes()
    return {'bytes':len(raw),'words':len(raw.decode('utf-8').split()),
            'sha256':hashlib.sha256(raw).hexdigest(),
            'git_blob_sha1':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}

receipt={
    'operation':'gmi-mining-principal-research-20260923-sol-001',
    'classification':'LOCAL_RESEARCH_ARITHMETIC_DOCUMENT_AND_PEDAGOGICAL_EXAMPLES_ONLY',
    'run_utc':datetime.now(timezone.utc).isoformat(), 'research_cutoff':'2026-09-23',
    'command':'python check_aluminium_research.py',
    'documents':{name:digest(ROOT/name) for name in [REPORT,COVERAGE]},
    'script_git_blob_sha1':digest(Path(__file__))['git_blob_sha1'],
    'total':len(checks),'passed':sum(c['passed'] for c in checks),
    'failed':sum(not c['passed'] for c in checks),'checks':checks,
    'not_claimed':['application tests','independent research review','accounting audit','actual contract settlement','native source retention','source-rights acceptance','canonical Agent OS validator','CI','browser proof','investment validation'],
    'notes':['Historical research suites not rerun.','Chalco narrative admitted with mirror provenance; table-derived arithmetic excluded after screenshot failure.','Only original report/coverage/check files are packaged.']
}
output=ROOT/'MINING_ALUMINIUM_RESEARCH_CHECKS_2026-09-23.json'
output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:receipt[k] for k in ['total','passed','failed','documents','script_git_blob_sha1']},indent=2))
if receipt['failed']:
    print(json.dumps([c for c in checks if not c['passed']],indent=2))
    raise SystemExit(1)
