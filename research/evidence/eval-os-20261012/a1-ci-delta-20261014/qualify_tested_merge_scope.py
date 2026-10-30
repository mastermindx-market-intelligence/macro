"""Measure a five-input manifest proposal on the immutable actual tested merge.

Only the isolated analysis worktree's manifest changes. No carrier/base or ceiling
is changed, and a diagnostic exit does not claim a green binding check.
"""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import re
import subprocess
import sys
import time
import yaml

root = Path.cwd()
out = Path(__file__).parent
sys.path.insert(0, str(root))
from scripts import run_ci_pack as c
from scripts import ci_scope_dependencies as d
from scripts.check_contract_delta import packing_probe_spec

head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
assert head == '7c610b6d8a771cc66d8c2a43548a0328c817b79c', head
manifest = root / '.github/ci/legacy-jobs.yml'
original = manifest.read_text()
before = yaml.safe_load(original)
inputs = [
    'engine/rates_command_basis.py',
    'engine/neuralweb/market_memory_brain_citations.py',
    'engine/neuralweb/market_memory_retained_catalog.py',
    'engine/neuralweb/market_memory_retained_legacy_guard.py',
    'engine/neuralweb/market_memory_retained_saved.py',
]
assert all((root / item).is_file() for item in inputs)
job = before['jobs']['eval-os-a1']
assert all(item not in job['paths'] for item in inputs)
match = re.search(r'^  eval-os-a1:\n(.*?)(?=^  [A-Za-z0-9_-]+:|\Z)', original, re.M | re.S)
body = match.group(1)
assert body.count('    paths:\n') == 1
new_body = body.replace('    paths:\n', '    paths:\n' + ''.join('      - ' + item + '\n' for item in inputs), 1)
proposed = original[:match.start(1)] + new_body + original[match.end(1):]
after = yaml.safe_load(proposed)
normalized = copy.deepcopy(after)
normalized['jobs']['eval-os-a1']['paths'] = job['paths']
assert normalized == before
assert len(after['jobs']['eval-os-a1']['paths']) == len(job['paths']) + 5
manifest.write_text(proposed)
subprocess.run(['git', 'diff', '--check'], check=True)
(out / 'a1-five-inputs-tested-merge.patch').write_bytes(subprocess.check_output(['git', 'diff', '--', '.github/ci/legacy-jobs.yml']))
report = {
    'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'tested_merge': head,
    'isolated_worktree': str(root),
    'manifest_overlay_sha256': hashlib.sha256(proposed.encode()).hexdigest(),
    'exact_inputs_added': inputs,
    'all_job_execution_definitions_and_prior_paths_preserved': True,
    'ceilings_changed': False,
    'source_carrier_changed': False,
    'phase': 'inventory',
}
def save():
    (out / 'tested-merge-scope-measurements.json').write_text(json.dumps(report, indent=2) + '\n')
save()
inventory = out / 'tested-merge-7c-tracked.bin'
d.write_tracked_path_inventory(inventory, head, root=root)
report['inventory_sha256'] = hashlib.sha256(inventory.read_bytes()).hexdigest()
spec = packing_probe_spec(root / 'tests/test_ci_pack.py')
report['existing_probe_spec'] = spec
started = time.monotonic()
with d.planner_tracked_path_inventory(inventory, head, root=root):
    report['phase'] = 'canonical_curated_closure'
    save()
    print('Exact tested-merge inventory bound; measuring canonical closure.', flush=True)
    report['closure_misses'] = c.curated_exclusive_closure_findings(manifest)
    report['a1_closure_clear'] = 'eval-os-a1' not in report['closure_misses']
    report['phase'] = 'canonical_packing'
    save()
    print(json.dumps({'a1_closure_clear': report['a1_closure_clear'], 'closure_misses': report['closure_misses']}), flush=True)
    rows = c.packing_probe_measurements(manifest, [tuple(row) for row in spec['probes']], max_packs=spec['max_packs'])
    report['packing_rows'] = rows
    report['packing_breaches'] = c.packing_probe_breaches(rows)
report['elapsed_seconds'] = round(time.monotonic() - started, 2)
report['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
report['phase'] = 'diagnostic_complete'
report['binding_checks_green'] = report['a1_closure_clear'] and not report['packing_breaches']
save()
print(json.dumps({k: v for k, v in report.items() if k != 'packing_rows'}, indent=2), flush=True)
print(json.dumps([{k: v for k, v in row.items() if k not in {'selected_jobs', 'selected_job_ids'}} for row in report['packing_rows']], indent=2), flush=True)
