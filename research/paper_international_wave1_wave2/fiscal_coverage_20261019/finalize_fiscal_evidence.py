"""Bind the completed fiscal design and run the existing local UI gates."""
from __future__ import annotations
import gzip
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

W = Path('/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018')
F = W / 'research/paper_international_wave1_wave2/fiscal_coverage_20261019'
PYTHON = '/tmp/intl-country-cockpit-testenv-20261018/bin/python'
FROZEN_HEAD = '11c83bb5dfb0c8199a0fb0cb2c6e70452c724984'

def now():
    return datetime.now(timezone.utc).isoformat()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def bind(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(W)), 'sha256': sha(data), 'bytes': len(data)}

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=W, text=True).strip()
assert head == FROZEN_HEAD, head
readback = json.loads((F / 'paper_final_readback_verification.json').read_text())
assert readback['text_passed'] == readback['text_count'] == 56
assert readback['style_passed'] == readback['style_count'] == 16
assert readback['old_cutoff_absent']
finish = json.loads((F / 'paper_effect_07_finish.json').read_text())
assert finish['state'] == 'APPLIED_RESPONSE_OBSERVED'
effects = [
    'paper_effect_01.json', 'paper_effect_02.json', 'paper_effect_03.json',
    'paper_effect_04.json', 'paper_effect_05_recovered.json',
    'paper_effect_06.json', 'paper_effect_07_finish.json',
]
parent = W / 'research/paper_international_wave1_wave2/paper_r12_receipt.json'
policy_parent = W / 'research/paper_international_wave1_wave2/policy_coverage_20261019/paper_policy_coverage_receipt.json'
assert bind(policy_parent)['sha256'] == 'c9aad285a3ee80e54b0b125274f0251122f68d3b1a7862f0b1620227e69f6a24'
capture = json.loads((F / 'paper_capture_materialization.json').read_text())
paper = {
    'schema': 'mastermind.intl_fiscal_paper_coverage_receipt.v1',
    'recorded_at': now(),
    'file_id': '01M3P1TW5Y3XWQC37ADDS8K5AG',
    'page_id': 'p-G-0',
    'url': 'https://app.paper.design/file/01M3P1TW5Y3XWQC37ADDS8K5AG/p-G-0',
    'boards': ['DMX-0', 'DW7-0', 'E4D-0', 'EC2-0', 'ER4-0', 'ER5-0'],
    'parents': [bind(parent), bind(policy_parent)],
    'scope': 'Additional fiscal rows, forecast units, September30 information cutoff, and Taiwan light-theme correction on the existing R12 references.',
    'effects': [bind(F / name) for name in effects],
    'effect_count_including_finish': 7,
    'original_response_retained_count': 6,
    'recovered_effect': {
        'operation_id': 'intl-country-cockpit-20261018-fiscal-paper-layer-names-20261020',
        'original_state_observed': 'APPLIED_RESPONSE_OBSERVED',
        'original_response_retained': False,
        'readback': 'paper_effect_05_recovered.json',
        'limitation': 'The store copy was lost across an app-context refresh. Twelve layer names were independently read back; the mutation was not replayed.',
    },
    'verification': {
        'text_nodes': 56, 'text_passed': 56, 'style_properties': 16,
        'style_passed': 16, 'boards_finished': 6,
        'readback': bind(F / 'paper_final_readback_verification.json'),
        'capture_materialization': bind(F / 'paper_capture_materialization.json'),
    },
    'artifacts': capture['artifacts'],
    'visual_review': {
        'scope': 'Six boards reviewed; Taiwan was recaptured after correcting light-theme text and divider tokens.',
        'repairs': [
            'The cloned Taiwan fiscal card now uses the light-theme text, muted text and divider tokens.',
            'The working HTML country grid item has min-width:0; expanded source disclosure now fits 320px.',
        ],
        'reference_date': 'Paper header remains 19 October 2026; the browser fixture was rendered on 20 October UTC.',
        'market_replay_date': '2026-10-15',
    },
    'limitations': [
        'Paper source labels remain static design references. Real URLs and disclosure interactions are proved separately in Chrome.',
        'Native screenshots retain their original returned bytes. Tall overview boards are downscaled by Paper; JSX and focused browser captures provide readable detail.',
        'This is design and local implementation proof, not production or authenticated acceptance.',
        'The target is explicit R12 page p-G-0; the file title and unrelated active page still reference R10.',
    ],
}
paper_path = F / 'paper_fiscal_coverage_receipt.json'
write_json(paper_path, paper)
manifest_path = F / 'preview/manifest.json'
manifest = json.loads(manifest_path.read_text())
original = F / 'preview/manifest.render-original.json'
if not original.exists():
    original.write_bytes(manifest_path.read_bytes())
manifest['paper_design'].update({
    'receipt': '../paper_fiscal_coverage_receipt.json',
    'receipt_sha256': sha(paper_path.read_bytes()),
    'applied': True,
    'scope': 'R12 and policy parents plus the fiscal increment bound by the named receipt; functional HTML behavior is separately browser-tested.',
})
archives = {}
for name, expected in manifest['html_sha256'].items():
    path = F / 'preview' / name
    data = path.read_bytes()
    assert sha(data) == expected, name
    archive = path.with_suffix(path.suffix + '.gz')
    archive.write_bytes(gzip.compress(data, mtime=0))
    assert gzip.decompress(archive.read_bytes()) == data
    archives[name] = {**bind(archive), 'decompressed_sha256': sha(data)}
manifest['html_archives'] = archives
write_json(manifest_path, manifest)

gates = F / 'gates'
gates.mkdir(exist_ok=True)
diff = subprocess.check_output([
    'git', 'diff', FROZEN_HEAD, '--',
    'templates/intl_country_cockpit.css', 'templates/intl_country_cockpit.html.j2',
], cwd=W)
diff_path = gates / 'final_ui_delta.diff'
diff_path.write_bytes(diff)
diff_archive = gates / 'final_ui_delta.diff.gz'
diff_archive.write_bytes(gzip.compress(diff, mtime=0))
runs = []
for name, command in [
    ('design', [PYTHON, 'scripts/check_design_system.py', '--mode', 'enforce-added', '--diff-file', str(diff_path)]),
    ('visual', [PYTHON, 'scripts/check_ui_visual_evidence.py', '--diff-file', str(diff_path)]),
    ('tracked_whitespace', ['git', 'diff', '--check']),
]:
    started = now()
    result = subprocess.run(command, cwd=W, capture_output=True)
    log = gates / (name + '.log')
    log.write_bytes(result.stdout + result.stderr)
    record = {
        'name': name, 'command': command, 'started_at': started,
        'finished_at': now(), 'exit_code': result.returncode, 'log': bind(log),
    }
    runs.append(record)
    print(json.dumps({'gate': name, 'exit_code': result.returncode, 'log': str(log.relative_to(W))}), flush=True)
assets = {
    'app/deploy/Caddyfile': 'eb0abf17c03d1ef5ab2c6378ac67d6dfb71b58b5353810af64a08c4629780190',
    'config/site_access.yml': '127dd1de71c979910601a8df89132244e95c0d1991c194408281072ace6384c9',
    'tests/test_site_access_boundary.py': '220d3790b2a0135b7ea1b8c75a1d0a68192d9e3082a72168c39b8850da5372cf',
}
asset_checks = [{**bind(W / name), 'expected_sha256': expected, 'match': sha((W / name).read_bytes()) == expected} for name, expected in assets.items()]
result = {
    'schema': 'mastermind.intl_fiscal_local_gates.v1', 'recorded_at': now(),
    'head': head, 'scope': 'Working-tree UI delta relative to frozen local HEAD; hosted and formal release gates remain outstanding.',
    'runs': runs,
    'diff': {'base': head, 'raw_sha256': sha(diff), 'raw_bytes': len(diff), 'archive': bind(diff_archive)},
    'inherited_asset_repair': asset_checks,
    'paper_receipt': bind(paper_path), 'preview_manifest': bind(manifest_path),
}
write_json(gates / 'verification.json', result)
diff_path.unlink()
print(json.dumps({'paper_receipt': bind(paper_path), 'archives': len(archives), 'asset_hashes_preserved': all(x['match'] for x in asset_checks)}))
sys.exit(0 if all(x['exit_code'] == 0 for x in runs) and all(x['match'] for x in asset_checks) else 1)
