#!/usr/bin/env python3
"""Verify the PB-A research package; optionally reproduce in a temporary directory.

No network calls, repository writes, production access or outcome recoding.
The reproduction forecast runs before an outcome directory exists in its workspace.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED_FORECAST_SHA256 = '2204fc89a45fa6cb3234762316ae63ffdd9f60daae631c799e2d0d5ac55e246a'
DESIGN_FILES = {'decisions': 'PB_A_DECISION_INPUTS.json', 'protocol': 'PB_A_PROTOCOL_FREEZE.json',
                'clarifications': 'PB_A_IMPLEMENTATION_CLARIFICATIONS.json', 'code': 'pb_a_analyze.py'}

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()

def parsed_time(text):
    return datetime.fromisoformat(text.replace('Z', '+00:00'))

def walk_keys(obj):
    if isinstance(obj, dict):
        for key, val in obj.items():
            yield key
            yield from walk_keys(val)
    elif isinstance(obj, list):
        for val in obj:
            yield from walk_keys(val)

def run(script, *args):
    done = subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(done.stderr or done.stdout)
    return done.stdout

def verify(reproduce=False):
    checked_manifest = 0
    manifest = ROOT / 'SHA256SUMS.txt'
    if manifest.exists():
        for line in manifest.read_text().splitlines():
            if not line.strip():
                continue
            wanted, name = line.split('  ', 1)
            path = ROOT / name
            assert path.resolve().is_relative_to(ROOT.resolve())
            assert sha(path) == wanted, 'Manifest mismatch: ' + name
            checked_manifest += 1
    frozen = read(ROOT / 'PB_A_FORECAST_FREEZE.json')
    assert sha(ROOT / 'PB_A_FORECAST_FREEZE.json') == EXPECTED_FORECAST_SHA256
    for key, name in DESIGN_FILES.items():
        assert sha(ROOT / name) == frozen['input_sha256'][key], key
    unsigned = {k: frozen[k] for k in ('input_sha256', 'forecast_payload')}
    assert hashlib.sha256(canonical(unsigned)).hexdigest() == frozen['freeze_content_sha256']
    book = read(ROOT / 'PB_A_CASEBOOK.json')
    sources = {s['source_id']: s for s in book['sources']}
    primary = [e for e in book['episodes'] if e['cohort'] == 'PRIMARY']
    challenge = [e for e in book['episodes'] if e['cohort'] == 'ADVERSARIAL_CHALLENGE']
    assert len(primary) == 24 and len(challenge) == 1
    assert len(set(e['episode_id'] for e in book['episodes'])) == 25
    for row in book['episodes']:
        assert row['pit_certified'] is True and 'documentary' in row['pit_certification_scope'].lower()
        assert list(row).index('decision_time') < list(row).index('outcomes')
        certificate = row['source_clock_certificate']
        for sid in certificate['admitted_source_ids']:
            s = sources[sid]
            assert s['canonical_clock']['public_time_upper_bound_utc'] is not None
            assert parsed_time(s['canonical_clock']['public_time_upper_bound_utc']) <= parsed_time(row['decision_cut_utc'])
            assert s['canonical_clock']['grade'] in ('DOCUMENTARY_MINUTE', 'DOCUMENTARY_DATE')
        decision = row['decision_time']
        forbidden = {'outcomes', 'later_outcomes', 'net_change_bps', 'drift_bps', 'truth', 'endpoint_range_pct'}
        assert not forbidden.intersection(walk_keys(decision)), row['episode_id']
        assert len(decision['competing_hypotheses']) >= 2
        assert all(h['falsifiers'] and h['new_observation_to_rerank'] for h in decision['competing_hypotheses'])
        for rhetoric in decision['rhetoric']:
            assert rhetoric['evidence_publication_clocks']
            assert 'explicit_horizon' in rhetoric and 'ambiguity_conditionality' in rhetoric
        assert not any(a.get('executed_flow_receipt') for a in decision['actions'])
    # A joint announcement keeps all origins, without turning them into independent observations.
    assert set(sources['joint20230312']['originator_families']) == {'FEDERAL_RESERVE_SYSTEM', 'US_TREASURY', 'FDIC'}
    buyback = next(e for e in primary if e['event_date'] == '2024-05-29')
    a = buyback['decision_time']['actions'][0]
    assert a['accepted_allocation_receipt_present'] and not a['completed_settlement_receipt_present']
    outputs = read(ROOT / 'PB_A_OUTCOMES.json')
    forecast_rows = {e['episode_id']: e for e in frozen['forecast_payload']['episodes']}
    outcome_rows = {e['episode_id']: e for e in outputs['episodes']}
    for e in book['episodes']:
        assert e['decision_time']['frozen_forecasts'] == forecast_rows[e['episode_id']]
        assert e['outcomes'] == outcome_rows[e['episode_id']]
    assert outputs['forecast_freeze_file_sha256'] == EXPECTED_FORECAST_SHA256
    for name, digest in outputs['outcome_source_sha256'].items():
        path = ROOT / 'outcome_inputs' / (name + ('.json' if name == 'policy_decision_changes' else '.csv'))
        assert sha(path) == digest
    reproduced = []
    if reproduce:
        with tempfile.TemporaryDirectory(prefix='pb_a_reproduce_') as tmp:
            dst = Path(tmp)
            for name in DESIGN_FILES.values():
                shutil.copyfile(ROOT / name, dst / name)
            assert not (dst / 'outcome_inputs').exists()
            run(dst / 'pb_a_analyze.py', 'forecast')
            assert sha(dst / 'PB_A_FORECAST_FREEZE.json') == EXPECTED_FORECAST_SHA256
            reproduced.append('Forecast bytes identical with no outcome directory present')
            shutil.copytree(ROOT / 'outcome_inputs', dst / 'outcome_inputs')
            run(dst / 'pb_a_analyze.py', 'score')
            for name in ('PB_A_OUTCOMES.json', 'PB_A_BASELINE_PILOT.json'):
                assert canonical(read(ROOT / name)) == canonical(read(dst / name)), name
                reproduced.append(name + ' JSON content reproduced exactly')
            # Published pilot may be compacted; use its exact bytes for the exploratory receipt's input hashes.
            shutil.copyfile(ROOT / 'PB_A_BASELINE_PILOT.json', dst / 'PB_A_BASELINE_PILOT.json')
            shutil.copyfile(ROOT / 'pb_a_endpoint_sensitivity.py', dst / 'pb_a_endpoint_sensitivity.py')
            run(dst / 'pb_a_endpoint_sensitivity.py')
            assert canonical(read(ROOT / 'PB_A_ENDPOINT_SENSITIVITY.json')) == canonical(read(dst / 'PB_A_ENDPOINT_SENSITIVITY.json'))
            reproduced.append('Post-score endpoint diagnostic reproduced exactly')
            shutil.copytree(ROOT / 'source_packets', dst / 'source_packets')
            shutil.copyfile(ROOT / 'pb_a_build_casebook.py', dst / 'pb_a_build_casebook.py')
            run(dst / 'pb_a_build_casebook.py', 'build')
            assert sha(dst / 'PB_A_DECISION_INPUTS.json') == frozen['input_sha256']['decisions']
            run(dst / 'pb_a_build_casebook.py', 'assemble')
            assert canonical(read(ROOT / 'PB_A_CASEBOOK.json')) == canonical(read(dst / 'PB_A_CASEBOOK.json'))
            reproduced.append('Casebook reconstruction and input identities reproduced exactly')
    return {'status': 'PASS', 'primary_episodes': len(primary), 'separate_challenges': len(challenge),
            'source_records': len(sources), 'first_public_clock_counts_primary': dict(Counter(e['event_time_precision'] for e in primary)),
            'immutable_forecast_sha256': EXPECTED_FORECAST_SHA256,
            'checks': ['Frozen design/code/forecast identities', 'Source admission bounds and scoped certificates', 'No realized outcome keys in decision block', 'Required rhetoric/hypothesis fields', 'Joint source lineage', 'Allocation versus completed-settlement semantics', 'Forecast/outcome joins and source digests'],
            'manifest_files_verified': checked_manifest, 'reproduction': reproduced,
            'limits': 'Verifies this research package, not historical served bytes, full M2, calibrated skill or production integration.'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reproduce', action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify(args.reproduce), indent=2))
