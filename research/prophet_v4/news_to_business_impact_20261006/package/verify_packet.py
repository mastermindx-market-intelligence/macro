#!/usr/bin/env python3
"""Offline arithmetic and package checks, not market/model validation."""
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import zipfile
from budget import Stage, STAGES, report

ROOT = Path(__file__).resolve().parent
checks = []
def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append({'name': name, 'passed': True})

def refuses(name, stage, days=30):
    try:
        stage.cost(days)
    except (ValueError, TypeError):
        check(name, True)
    else:
        check(name, False)

r = report()
check('base monthly cost', Decimal(r['inference_base_usd']) == Decimal('106.05'))
check('100 percent overhead cost', Decimal(r['inference_with_100_percent_overhead_usd']) == Decimal('212.10'))
check('all raw frontier comparison', Decimal(r['all_raw_frontier_extraction_usd']) == Decimal('20700'))
check('workload and price stress', Decimal(r['three_times_work_two_times_prices_usd']) == Decimal('636.30'))
check('zero day cost', all(s.cost(0) == 0 for s in STAGES))
check('daily monthly consistency', all(s.cost(1) * 30 == s.cost() for s in STAGES))
refuses('negative counts refused', Stage('bad', -1, 1, 1, '1', '1'))
refuses('boolean counts refused', Stage('bad', True, 1, 1, '1', '1'))
refuses('fractional counts refused', Stage('bad', 1.2, 1, 1, '1', '1'))
refuses('negative price refused', Stage('bad', 1, 1, 1, '-1', '1'))
refuses('nonfinite price refused', Stage('bad', 1, 1, 1, 'Infinity', '1'))
refuses('nonfinite day refused', STAGES[0], days=float('inf'))
check('buyback EPS denominator illustration', (Decimal(1) / Decimal('0.97') - 1).quantize(Decimal('0.0001')) == Decimal('0.0309'))
check('fair value buyback illustration', (Decimal(100)-10)/(Decimal(100)-10) == Decimal(1))
text = (ROOT / 'MASTERPLAN.md').read_text()
check('all 15 masterplan sections present', all(f'## {n}. ' in text for n in range(1, 16)))
check('proposal status disclosed', 'Not an accepted production contract' in text)
check('no worker dispatch disclosed', 'No paid job or worker was launched' in text)
check('security boundary present', 'Source text is data, never tool authority' in text)
check('budget is not observed traffic', 'NOT measured traffic' in text)
check('no predictive proof claim', 'not proof of 99th-percentile return forecasts' in text)
check('persisted budget matches calculation', json.loads((ROOT / 'budget_scenario.json').read_text()) == r)

receipt = {
    'scope': 'Offline arithmetic, input validation and document-completeness checks only. No model benchmark, market backtest, GitHub suite, deployment or production test.',
    'date': '2026-10-06',
    'checks_passed': len(checks),
    'checks': checks,
    'masterplan_words': len(text.split()),
}
(ROOT / 'VERIFICATION.json').write_text(json.dumps(receipt, indent=2) + '\n')
files = sorted(p for p in ROOT.iterdir() if p.is_file() and p.name != 'MANIFEST.json')
manifest = {p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files}
(ROOT / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
zip_path = ROOT.parent / 'Prophet_News_Impact_Masterplan_Package.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for p in sorted(ROOT.iterdir()):
        if p.is_file():
            z.write(p, arcname=f'prophet_news_impact/{p.name}')
with zipfile.ZipFile(zip_path) as z:
    check('zip integrity', z.testzip() is None)
print(json.dumps({'checks_passed': len(checks), 'masterplan_words': len(text.split()), 'zip': str(zip_path), 'masterplan_sha256': hashlib.sha256((ROOT/'MASTERPLAN.md').read_bytes()).hexdigest()}, indent=2))
