"""Verify retained fiscal evidence without reacquiring sources or rerunning admissions."""
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

def sha(data):
    return hashlib.sha256(data).hexdigest()

def bind(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(W)), 'sha256': sha(data), 'bytes': len(data)}

def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')

before = json.loads(gzip.decompress((F / 'baseline_before.json.gz').read_bytes()))
after = json.loads((W / 'config/intl_country_baseline.json').read_text())
admission = json.loads((F / 'admission.json').read_text())
old_records = {r['record_id']: r for r in before['forecast_archive']}
records = {r['record_id']: r for r in after['forecast_archive']}
preserved_fields = {k: before[k] == after.get(k) for k in before if k not in ['forecast_archive', 'retrieved_at']}
superseded_ids = {x['supersedes'] for x in admission['metadata_corrections']}
original_record_checks = []
for key, value in old_records.items():
    expected = dict(value)
    if key in superseded_ids:
        expected['superseded_at'] = admission['recorded_at']
    original_record_checks.append({
        'record_id': key, 'original_content_and_expected_lifecycle_match': records.get(key) == expected,
        'new_lifecycle_marker': 'superseded_at' if key in superseded_ids else None,
    })
original_records_preserved = all(x['original_content_and_expected_lifecycle_match'] for x in original_record_checks)
corrections = []
for item in admission['metadata_corrections']:
    corrected = records[item['record_id']]
    old = old_records[item['supersedes']]
    unchanged = ['values', 'periods', 'source_url', 'dataset_url', 'source_sha256',
                 'source_row_sha256', 'retrieved_at', 'published', 'provider', 'family',
                 'edition', 'series_id', 'period_basis', 'definition_id']
    corrections.append({
        'record_id': corrected['record_id'],
        'original_id': old['record_id'],
        'data_and_source_preserved': all(corrected.get(k) == old.get(k) for k in unchanged),
        'cutoff': corrected['information_cutoff'],
        'sequence': corrected['correction_sequence'],
        'custody_is_actual_admission': corrected['first_observed_at'] == corrected['admitted_at'] == admission['recorded_at'],
    })
raw_checks = []
for row in json.loads((F / 'source_acquisition.json').read_text()):
    raw = gzip.decompress((F / 'raw_api' / (row['series'] + '.json.gz')).read_bytes())
    raw_checks.append({'series': row['series'], 'hash_match': sha(raw) == row['sha256'], 'bytes_match': len(raw) == row['bytes'], 'http_status': row['status']})
browser = json.loads((F / 'browser_verification.json').read_text())
canonical_path = W / browser['canonical_manifest']
canonical = json.loads(canonical_path.read_text())
capture_checks = []
for page in canonical['pages']:
    for state in page['states']:
        path = canonical_path.parent / state['file']
        data = path.read_bytes()
        capture_checks.append({'file': str(path.relative_to(W)), 'hash_match': sha(data) == state['sha256'], 'bytes_match': len(data) == state['bytes'], 'captured': state['captured']})
screenshot_checks = [{'path': x['path'], 'hash_match': sha((W / x['path']).read_bytes()) == x['sha256']} for x in browser['screenshots']]
manifest = json.loads((F / 'preview/manifest.json').read_text())
archive_checks = []
for name, record in manifest['html_archives'].items():
    path = W / record['path']
    raw = gzip.decompress(path.read_bytes())
    archive_checks.append({'html': name, 'archive_hash_match': sha(path.read_bytes()) == record['sha256'], 'raw_hash_match': sha(raw) == record['decompressed_sha256'] == manifest['html_sha256'][name]})
paper = json.loads((F / 'paper_fiscal_coverage_receipt.json').read_text())
paper_bindings = paper['parents'] + paper['effects'] + paper['artifacts']
paper_bindings += [paper['verification']['readback'], paper['verification']['capture_materialization']]
paper_artifacts_match = all(sha((W / x['path']).read_bytes()) == x['sha256'] for x in paper_bindings)
gates = json.loads((F / 'gates/verification.json').read_text())

# Losslessly archived integrated HTML carries inherited whitespace. Remove only those two
# transient text copies after verifying their archives; the exact browser-tested bytes remain.
removed_text_copies = []
for name in ['intl_integrated_preview.html', 'intl_stocks_integrated_preview.html']:
    path = F / 'preview' / name
    if path.exists():
        assert sha(path.read_bytes()) == manifest['html_sha256'][name]
        path.unlink()
        removed_text_copies.append(str(path.relative_to(W)))

new_text_paths = [
    W / 'agentos/workstreams/WS-PAPER-INTERNATIONAL-WAVES.md',
    W / 'tests/fixtures/intl_weo_october_2026_fiscal_api.json',
    canonical_path.parent / 'EVIDENCE.yml',
]
new_text_paths += [p for p in F.rglob('*') if p.is_file() and p.suffix in {'.md', '.py', '.jsx', '.json', '.yml', '.yaml'} and p.name not in {'FISCAL_COVERAGE_20261020.json'}]
whitespace = []
for path in sorted(set(new_text_paths)):
    for index, line in enumerate(path.read_text().splitlines(), 1):
        if line != line.rstrip(' \t'):
            whitespace.append({'path': str(path.relative_to(W)), 'line': index})
tracked = subprocess.run(['git', 'diff', '--check'], cwd=W, capture_output=True, text=True)
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=W, text=True).strip()
result = {
    'schema': 'mastermind.intl_fiscal_integrity.v1',
    'checked_at': datetime.now(timezone.utc).isoformat(),
    'baseline_sha256': sha((W / 'config/intl_country_baseline.json').read_bytes()),
    'baseline_matches_admission': sha((W / 'config/intl_country_baseline.json').read_bytes()) == admission['baseline_after_sha256'],
    'archive_count': len(records), 'prior_archive_count': len(old_records),
    'preserved_baseline_fields': preserved_fields,
    'all_original_record_content_preserved': original_records_preserved,
    'original_record_lifecycle_checks': original_record_checks,
    'new_fiscal_count': len(admission['new_fiscal_records']),
    'new_fiscal_ids_present': all(r['record_id'] in records for r in admission['new_fiscal_records']),
    'cutoff_corrections': corrections,
    'source_raw_checks': raw_checks,
    'canonical_manifest_matches_browser': sha(canonical_path.read_bytes()) == browser['canonical_manifest_sha256'],
    'canonical_capture_checks': capture_checks,
    'focused_screenshot_checks': screenshot_checks,
    'html_archive_checks': archive_checks,
    'paper_artifact_hashes_match': paper_artifacts_match,
    'paper_manifest_binding_matches': sha((F / 'paper_fiscal_coverage_receipt.json').read_bytes()) == manifest['paper_design']['receipt_sha256'],
    'asset_repair_hashes_match': all(x['match'] and sha((W / x['path']).read_bytes()) == x['sha256'] for x in gates['inherited_asset_repair']),
    'removed_archived_integrated_text_copies': removed_text_copies,
    'new_text_whitespace_findings': whitespace,
    'tracked_diff_check_exit': tracked.returncode,
    'head': head,
    'head_preserved': head == '11c83bb5dfb0c8199a0fb0cb2c6e70452c724984',
}
checks = [
    result['baseline_matches_admission'], len(records) == 73, len(old_records) == 37,
    all(preserved_fields.values()), original_records_preserved,
    result['new_fiscal_count'] == 8, result['new_fiscal_ids_present'], len(corrections) == 28,
    all(x['data_and_source_preserved'] and x['cutoff'] == '2026-09-30' and x['sequence'] == 1 and x['custody_is_actual_admission'] for x in corrections),
    all(x['hash_match'] and x['bytes_match'] and x['http_status'] == 200 for x in raw_checks),
    result['canonical_manifest_matches_browser'], len(capture_checks) == 12,
    all(x['hash_match'] and x['bytes_match'] and x['captured'] for x in capture_checks),
    all(x['hash_match'] for x in screenshot_checks),
    all(x['archive_hash_match'] and x['raw_hash_match'] for x in archive_checks),
    paper_artifacts_match, result['paper_manifest_binding_matches'],
    result['asset_repair_hashes_match'], not whitespace, tracked.returncode == 0, result['head_preserved'],
]
result['passed'] = all(checks)
write_json(F / 'gates/integrity.json', result)
print(json.dumps({'passed': result['passed'], 'archive_count': len(records), 'prior_records_preserved': original_records_preserved, 'cutoff_corrections': len(corrections), 'canonical_captures': len(capture_checks), 'paper_artifact_hashes_match': paper_artifacts_match, 'whitespace_findings': whitespace[:12], 'head_preserved': result['head_preserved']}))
sys.exit(0 if result['passed'] else 1)
