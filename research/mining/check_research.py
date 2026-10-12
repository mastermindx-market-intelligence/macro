"""Check the research document and selected arithmetic, not product behavior."""
from __future__ import annotations
from decimal import Decimal as D
from pathlib import Path
import hashlib
import json
import re

root = Path(__file__).resolve().parent
p = root / 'MINING_PRINCIPAL_RESEARCH_FOUNDATION_2026-09-23.md'
raw = p.read_bytes()
text = raw.decode('utf-8')
checks: list[dict[str, object]] = []
def check(name: str, passed: bool, evidence: object) -> None:
    checks.append({'check': name, 'passed': bool(passed), 'evidence': evidence})

cases = re.findall(r'^### (C\d{2}) ', text, re.M)
sources = re.findall(r'^- \*\*(S\d{2}) — ', text, re.M)
requirements = re.findall(r'^\| (MN-\d{2}) \|', text, re.M)
hypotheses = re.findall(r'^- \*\*(H\d{2}) ', text, re.M)
check('ten_unique_cases', cases == [f'C{i:02d}' for i in range(1, 11)], cases)
check('nineteen_unique_primary_sources', sources == [f'S{i:02d}' for i in range(1, 20)], sources)
check('thirty_prospective_requirements', requirements == [f'MN-{i:02d}' for i in range(1, 31)], requirements)
check('four_hypothetical_cases', hypotheses == [f'H{i:02d}' for i in range(1, 5)], hypotheses)
refs = set(re.findall(r'\bS\d{2}\b', text))
check('source_references_resolve', refs == set(sources), sorted(refs))
urls = re.findall(r'https://\S+', text.split('## 12. Primary-source register', 1)[1])
check('one_unique_url_per_primary_source', len(urls) == len(set(urls)) == 19, len(urls))
check('mission_and_handoff_held', 'Mission complete: false.' in text and 'Final Fable CEO implementation handoff: not created.' in text, 'explicit research-only boundary')
check('procedural_pin_present', 'bf764f494b9cd0ecede6234bb472c3344c8e77cc' in text, 'Mastermind exact SHA')
check('implementation_baseline_present', 'c4da107fe729e46b4d4036b3e0e290390315d0fd' in text, 'Macro exact SHA')
check('scope_correction_preserves_original_carrier', 'da87d480adf6666583a61bb0912d6daeaeec984c' in text and '#7787' in text, 'Healthcare evidence not transferred')

payable = D('1000000') * D('0.01') * D('0.90') * D('0.96')
check('H01_payable_tonnes', payable == D('8640'), str(payable))
check('H01_attributable_tonnes', payable * D('0.60') == D('5184'), str(payable * D('0.60')))
old_value = D('1000000000') / D('100000000')
new_value = D('1200000000') / D('130000000')
check('H02_equity_dilution_counterexample', old_value == D('10') and new_value.quantize(D('.01')) == D('9.23') and ((new_value / old_value - 1) * 100).quantize(D('.01')) == D('-7.69'), {'before': str(old_value), 'after': str(new_value)})
check('H03_earnings_multiple_counterexample', D('2') * D('15') == D('3') * D('10') == D('30'), 'EPS +50%; hypothetical price unchanged, dividends excluded')
growth_old = (D('110') / D('100') - 1) * 100
growth_new = (D('110') / D('105') - 1) * 100
check('H04_vintage_counterexample', growth_old == D('10') and growth_new.quantize(D('.01')) == D('4.76'), {'first': str(growth_old), 'revised': str(growth_new)})
check('C05_MP_revenue_eliminations', D('95629') + D('16524') - D('3663') == D('108490'), 'USD thousands; S06')
check('C09_gold_source_version_difference', D('947.7') - D('908.6') == D('39.1'), 'tonnes; S13/S14; not an archived PIT receipt')
recycling_change = (D('326.1') / D('346.7') - 1) * 100
check('C09_gold_recycling_table_implies_minus_six', recycling_change.quantize(D('1')) == D('-6'), {'derived_percent': str(recycling_change), 'source': 'S14'})
fcx_price_change = (D('6.17') / D('4.54') - 1) * 100
check('C01_FCX_price_arithmetic', fcx_price_change.quantize(D('.1')) == D('35.9'), {'percent': str(fcx_price_change), 'source': 'S01', 'not_a_return_forecast': True})
check('unverified_contract_lag_disclosed', 'Exact pricing-lag parameters were not verified' in text, 'No inferred lag used')

receipt = {
    'operation': 'gmi-mining-principal-research-20260923-sol-001',
    'run_date': '2026-09-23',
    'command': 'python /mnt/data/mining_research/check_research.py',
    'classification': 'LOCAL_RESEARCH_INTEGRITY_AND_ARITHMETIC_ONLY',
    'document': p.name,
    'document_bytes': len(raw),
    'document_words': len(text.split()),
    'document_sha256': hashlib.sha256(raw).hexdigest(),
    'document_git_blob_sha1': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest(),
    'total_checks': len(checks),
    'passed': sum(bool(c['passed']) for c in checks),
    'failed': sum(not bool(c['passed']) for c in checks),
    'checks': checks,
    'not_claimed': ['application tests', 'CI', 'independent review', 'canonical Agent OS validator', 'browser proof', 'native source ingestion', 'investment validation', 'Fable dispatch', 'implementation acceptance'],
}
(root / 'MINING_RESEARCH_CHECKS_2026-09-23.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: receipt[k] for k in ['document_bytes','document_words','document_sha256','document_git_blob_sha1','total_checks','passed','failed']}, indent=2))
if receipt['failed']:
    raise SystemExit(1)
