"""Exact held reader compatibility against changed Macro source projection.

Read-only compositional proof. No consumer checkout edits, HTTP authentication,
rendered UI, deployment or independent reviewer acceptance are implied.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from engine import treasury_auction_lifecycle as lifecycle

HERE = Path(__file__).resolve().parent
PROGRAM = ROOT / 'research/sovereign_auction_pressure'
AT = '2026-10-09T02:22:00Z'


def run():
    manifest = json.loads((HERE / 'SOURCE_MANIFEST.json').read_text())
    for item in manifest:
        raw = (ROOT / item['snapshot_path']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('exact consumer source snapshot changed')
    spec = importlib.util.spec_from_file_location('held_mastermind_auction_reader', HERE / 'source_snapshots/mastermind_reader.py')
    mm = importlib.util.module_from_spec(spec); spec.loader.exec_module(mm)
    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only',
        'fdc4239a67125fdbd96ddb889b3c60033f720272', 'data/treasury_auctions/observations'], cwd=ROOT, text=True).splitlines()
    originals = [json.loads(subprocess.check_output(['git', 'show', 'fdc4239a67125fdbd96ddb889b3c60033f720272:' + path], cwd=ROOT)) for path in paths]
    captured = [json.loads(p.read_text()) for p in sorted((PROGRAM / 'verification/local_codex_20261008/attended_capture/treasury_auctions/observations').glob('*.json'))]
    cases = {'original_four_receipts': lifecycle.build_context(originals, AT),
        'new_attended_notices': lifecycle.build_context(captured, AT),
        'combined_original_and_notices': lifecycle.build_context(originals + captured, AT),
        'stale_original_sources': lifecycle.build_context(originals, '2026-10-11T02:22:00Z'),
        'missing_sources': lifecycle.build_context([], AT)}
    # A future probability must still be denied; the consumer allowlist must not
    # be widened merely to accept additional receipt/age evidence.
    hostile = copy.deepcopy(cases['combined_original_and_notices']); hostile['probabilities'] = {'crash': 0.9}
    cases['hostile_prediction'] = hostile
    outputs = []
    for name, context in cases.items():
        expect = name != 'hostile_prediction'
        try:
            result = mm.validate_context(context, now=context['as_of'])
            mm_ok = True
            mm_count = len(result['events'])
        except mm.InvalidContext:
            mm_ok, mm_count = False, None
        request = {'context': context, 'now': context['as_of']}
        js = "import fs from 'node:fs'; const m=await import(process.argv[1]); const r=JSON.parse(fs.readFileSync(0,'utf8')); const out=m.validateSovereignAuctionContext(r.context,Date.parse(r.now)); console.log(JSON.stringify({ok:out.ok,event_count:out.ok?out.context.events.length:null}));"
        completed = subprocess.run(['node', '--input-type=module', '-e', js,
            (HERE / 'source_snapshots/terminal_reader.ts').as_uri()], input=json.dumps(request),
            check=True, text=True, capture_output=True)
        terminal = json.loads(completed.stdout)
        if mm_ok != expect or terminal['ok'] != expect:
            raise ValueError(f'consumer acceptance mismatch: {name}: Mastermind={mm_ok}, Terminal={terminal}')
        if expect and (mm_count != len(context['events']) or terminal['event_count'] != len(context['events'])):
            raise ValueError('consumer dropped events')
        outputs.append({'case': name, 'producer_status': context['status'],
            'producer_events': len(context['events']), 'mastermind_accepted': mm_ok,
            'terminal_accepted': terminal['ok'], 'expected_acceptance': expect})
    return {'schema': 'sovereign_auction_exact_reader_compatibility.v1', 'source_manifest': manifest,
        'cases': outputs, 'passed': True, 'source_only': True,
        'production_http_verified': False, 'browser_rendering_verified': False,
        'consumer_repositories_modified': False, 'independent_review': False}


if __name__ == '__main__':
    receipt = run()
    (HERE / 'COMPATIBILITY_RECEIPT.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'passed': receipt['passed'], 'cases': receipt['cases']}))
