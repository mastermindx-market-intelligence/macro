"""Compose two payload-free Save assets with the completed native c077 build."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--workspace', type=Path, required=True)
p.add_argument('--base-receipt', type=Path, required=True)
p.add_argument('--source-head', required=True)
p.add_argument('--log', type=Path, required=True)
p.add_argument('--receipt', type=Path, required=True)
a = p.parse_args()
root = a.workspace.resolve()
def git(*args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def record(paths):
    return {rel: {'sha256': digest(root / rel), 'bytes': (root / rel).stat().st_size}
            for rel in paths}

assert not a.receipt.exists() and not a.log.exists(), 'Reconcile this operation; do not repeat it.'
base = json.loads(a.base_receipt.read_text())
assert base.get('completed_at') and len(base['modules']) == 4
assert all(step['exit'] == 0 for step in base['modules'])
assert Path(base['workspace']).resolve() == root
assert git('rev-parse', 'HEAD') == base['head']
for rel, value in base['artifacts'].items():
    assert digest(root / rel) == value['sha256'], rel
allowed = {
    'templates/prophet_save.js', 'templates/prophet_save.css',
    'tests/test_prophet_save_composition.py', 'config/site_access.yml',
    'app/deploy/Caddyfile', 'tests/test_paywall.py', 'tests/test_regwall_json_gate.py',
}
delta = git('diff', '--name-only', base['head'], a.source_head).splitlines()
assert set(delta) == allowed, delta
assert not git('diff', '--name-only', '--', *sorted(allowed))
subprocess.run(['git', 'merge-base', '--is-ancestor', base['head'], a.source_head], cwd=root, check=True)
outputs = (
    'site/us_stocks.html', 'site/premiumdata/us_stocks.json',
    'site/factordata/us_standouts.json', 'site/prophet_save.js',
    'site/prophet_save.css', 'site/theme.js', 'site/theme.css',
    'templates/chat.html', 'site/chat.html',
)
before = record(outputs)
rec = {
    'base_build_head': base['head'], 'source_head': a.source_head,
    'workspace': str(root), 'base_receipt_sha256': digest(a.base_receipt),
    'tool_sha256': digest(Path(__file__)), 'source_delta': delta,
    'before': before, 'started_at': time.time(), 'steps': [],
    'scope': 'Completed four-module native build plus canonical emission of two Save assets. '
             'Policy, CI enrollment and tests have separate source evidence. '
             'This is not a new market-data build, deployed serving policy or browser acceptance.',
}
def save():
    a.receipt.write_text(json.dumps(rec, indent=2) + '\n')
save()
with a.log.open('x') as log:
    cmd = ['git', 'merge', '--ff-only', a.source_head]
    result = subprocess.run(cmd, cwd=root, stdout=log, stderr=subprocess.STDOUT)
    rec['steps'].append({'command': cmd, 'exit': result.returncode}); save()
    if result.returncode:
        raise SystemExit(result.returncode)
    sys.path.insert(0, str(root))
    from lib.site_assets import copy_asset
    for asset in ('prophet_save.js', 'prophet_save.css'):
        copy_asset(asset, root / 'templates' / asset, root / 'site')
        assert (root / 'templates' / asset).read_bytes() == (root / 'site' / asset).read_bytes()
    cmd = [sys.executable, '-m', 'scripts.optimize_assets']
    started = time.time()
    result = subprocess.run(cmd, cwd=root, stdout=log, stderr=subprocess.STDOUT)
    rec['steps'].append({'command': cmd, 'exit': result.returncode,
                         'seconds': round(time.time() - started, 2)}); save()
    if result.returncode:
        raise SystemExit(result.returncode)
rec['artifacts'] = record(outputs)
for rel in ('site/premiumdata/us_stocks.json', 'site/factordata/us_standouts.json',
            'site/theme.js', 'site/theme.css'):
    assert before[rel]['sha256'] == rec['artifacts'][rel]['sha256'], rel
for asset in ('prophet_save.js', 'prophet_save.css'):
    assert (root / 'templates' / asset).read_bytes() == (root / 'site' / asset).read_bytes()
assert (root / 'templates/chat.html').read_bytes() == (root / 'site/chat.html').read_bytes()
assert git('rev-parse', 'HEAD') == a.source_head
rec['protected_payload_and_market_source_unchanged'] = True
rec['completed_at'] = time.time(); save()
print(json.dumps({'source_head': a.source_head, 'steps': rec['steps'],
                  'receipt': str(a.receipt)}, indent=2))
