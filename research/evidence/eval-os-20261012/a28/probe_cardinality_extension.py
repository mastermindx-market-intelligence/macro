#!/usr/bin/env python3
"""One root-authorized cardinality extension; original corpus/probe preserved.

Reuse the exact original child runner and both existing corpora via hardlinks.
Generate only synthetic Synapse metadata, empty producer sources and tiny outputs.
No production artifact values, source contents or outcomes are copied.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

import yaml

HERE = Path(__file__).resolve().parent
ORIGINAL_SHA = '6a0a24f9c7fe79ee073add6fc5c107aa516021791f2661f03c7979d226a3759e'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--tree', type=Path, default=Path('/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/eval-os-a1-preflight-20260922-f75c61cdabe6f12c'))
    parser.add_argument('--python', default=sys.executable)
    args = parser.parse_args()
    if not args.execute:
        parser.error('Explicit --execute required; authoring did not execute this extension')
    original_path = HERE / 'probe_composed_scale.py'
    spec = importlib.util.spec_from_file_location('a28_original_probe', original_path)
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    assert probe.sha(original_path) == ORIGINAL_SHA
    original = HERE / 'synthetic-estate'
    initial_report = json.loads((HERE / 'composed-scale-report.json').read_text())
    assert initial_report['ok']
    source_synapse = args.tree / 'config/synapse.yml'
    document = yaml.safe_load(source_synapse.read_text())
    source_rows = [v for v in document['artifacts'].values() if isinstance(v, dict)]
    counts = {'artifacts': len(source_rows),
              'producers': len({str(v['producer']) for v in source_rows if v.get('producer')}),
              'owners': len({str(v['owner_program']) for v in source_rows if v.get('owner_program')})}
    assert counts == {'artifacts': 647, 'producers': 369, 'owners': 102}, 'Source cardinality changed; adjudicate before extending'
    output = HERE / 'cardinality-extension'
    root = output / 'synthetic-estate'
    output.mkdir(exist_ok=True)
    root.mkdir(exist_ok=True)
    # Copy only prior small synthetic fixture files. Never call fixture(), which
    # generates the corpus; do not copy the 181MB ledger files or production data.
    excluded = {'data/qledger/claims.jsonl', 'data/qledger/grades.jsonl'}
    for path in original.rglob('*'):
        if not path.is_file() or path.relative_to(original).as_posix() in excluded:
            continue
        assert path.stat().st_size < 2 * 1024 * 1024
        target = root / path.relative_to(original)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    corpus_identities = {}
    for rel, key in [('data/qledger/claims.jsonl', 'claims'), ('data/qledger/grades.jsonl', 'grades')]:
        source = original / rel
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        assert probe.sha(source) == initial_report['inputs'][key]['sha256']
        if not target.exists():
            os.link(source, target)
        assert os.path.samefile(source, target), 'Refuse duplicated or foreign corpus'
        corpus_identities[key] = {'bytes': source.stat().st_size,
                                 'sha256': initial_report['inputs'][key]['sha256'],
                                 'reuse': 'same_inode_hardlink_no_content_copy'}
    synapse_path = root / 'config/synapse.yml'
    fixture_doc = yaml.safe_load(synapse_path.read_text())
    first = next(iter(fixture_doc['artifacts'].values()))
    for i in range(counts['artifacts'] - 1):
        producer = f'engine/synthetic/p_{i % (counts["producers"] - 1):03d}.py'
        owner = f'synthetic-program-{i % (counts["owners"] - 1):03d}'
        rel = f'data/synthetic/observations_{i:04d}.json'
        row = {**first, 'path': rel, 'format': 'json', 'producer': producer,
               'owner_program': owner, 'tier': 'display', 'notes': 'Synthetic cardinality only; no price/outcome meaning.'}
        fixture_doc['artifacts'][f'synthetic-{i:04d}'] = row
        source_file = root / producer
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text('')
        probe.write_json(root / rel, {'asof': 'unknown', 'scope': 'synthetic_cardinality_only'})
    raw = yaml.safe_dump(fixture_doc, sort_keys=True)
    target_bytes = source_synapse.stat().st_size
    # Disclosed comments match source transport size; they are not claimed to
    # reproduce production nested object shape, graph edges or producer ASTs.
    if len(raw.encode()) < target_bytes:
        raw += '\n#' + 'x' * max(0, target_bytes - len(raw.encode()) - 3) + '\n'
    synapse_path.write_text(raw)
    source_paths = list(initial_report['source_sha256'])
    source_hashes = {p: probe.sha(args.tree / p) for p in source_paths}
    assert source_hashes == initial_report['source_sha256'], 'Application source changed since accepted first probe'
    before = {p.relative_to(root).as_posix(): probe.sha(p) for p in root.rglob('*') if p.is_file()}
    runs = []
    for lane in ['baseline', 'A1']:
        run = probe.watched(args.python, original_path, args.tree, root, lane, output / (lane + '-result.json'))
        runs.append(run)
        if not run['ok']:
            break
    after = {p.relative_to(root).as_posix(): probe.sha(p) for p in root.rglob('*') if p.is_file()}
    stable = source_hashes == {p: probe.sha(args.tree / p) for p in source_paths}
    cardinality_ok = len(runs) == 2 and all(r['result'] and r['result']['assessed_artifacts'] == counts['artifacts'] for r in runs)
    report = {'schema': 'eval_os.a28.synthetic_cardinality_extension.v1',
              'original_probe_sha256': ORIGINAL_SHA,
              'original_report_sha256': probe.sha(HERE / 'composed-scale-report.json'),
              'source_synapse': {'sha256': probe.sha(source_synapse), 'bytes': target_bytes, **counts},
              'synthetic_synapse_bytes': synapse_path.stat().st_size,
              'reused_corpora': corpus_identities, 'source_sha256': source_hashes,
              'source_stable': stable, 'fixture_unchanged': before == after,
              'cardinality_exercised': cardinality_ok, 'runs': runs,
              'ok': cardinality_ok and stable and before == after and all(r['ok'] for r in runs),
              'limits': ['Mac CPU/disk/cache cannot predict VPS/client latency.',
                         '647 artifacts/369 producer files/102 owners are actual source cardinalities; artifact values, edges and producer AST complexity remain synthetic.',
                         'YAML comment padding matches transport bytes, not production metadata object distribution.',
                         'Original 1GiB watchdog/60s per child, guards and cumulative ru_maxrss definitions retained.',
                         'Historical unversioned owner snapshot; no empirical/current-source qualification.']}
    if len(runs) == 2 and all(r['result'] for r in runs):
        report['A1_minus_baseline_peak_rss_bytes'] = runs[1]['result']['peak_rss_bytes'] - runs[0]['result']['peak_rss_bytes']
        report['A1_cold_minus_baseline_wall_seconds'] = runs[1]['result']['samples'][0]['wall_seconds'] - runs[0]['result']['samples'][0]['wall_seconds']
    probe.write_json(output / 'cardinality-report.json', report)
    print(json.dumps({'ok': report['ok'], 'report': str(output / 'cardinality-report.json')}))
    if not report['ok']:
        sys.exit(1)


if __name__ == '__main__':
    main()
