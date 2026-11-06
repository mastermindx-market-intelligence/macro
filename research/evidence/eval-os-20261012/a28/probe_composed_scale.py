#!/usr/bin/env python3
"""Isolated synthetic A28 differential; never read production corpus or grade.

Root-authorized probe, not a performance service. Run explicitly with --execute.
Each child uses the real builder/_derive. Instrumentation only counts transports
and refuses forbidden readiness/grades reads; it supplies no replacement results.
"""
from __future__ import annotations

import argparse
import builtins
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

DEFAULT_TREE = Path('/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/eval-os-a1-preflight-20260922-f75c61cdabe6f12c')
CLAIMS_BYTES = 104577272
GRADES_BYTES = 76734696
READINESS_BYTES = 279736
FINDINGS_BYTES = 739954
RSS_CEILING = 1024**3
SECONDS_CEILING = 60


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, sort_keys=True, ensure_ascii=True) + '\n')


def corpus(path, target, row):
    """Stream complete ASCII JSON rows; no corpus-sized construction allocation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    total = count = 0
    with path.open('wb') as handle:
        while total < target:
            item = dict(row)
            item['claim_id'] = 'SYNTHETIC-' + str(count if count % 17 else max(0, count - 1))
            if 'desk' in item:
                item['horizon_d'] = 126 if count % 2 else 20
                item['direction'] = -1 if count % 3 else 1
            raw = (json.dumps(item, sort_keys=True, separators=(',', ':')) + '\n').encode('ascii')
            handle.write(raw)
            total += len(raw)
            count += 1
    return {'bytes': total, 'rows': count, 'target_bytes': target, 'sha256': sha(path)}


def pad_document(document, target):
    # Explicit transport-byte padding, not a claim about production object shape.
    size = len((json.dumps(document, sort_keys=True) + '\n').encode('ascii'))
    document['synthetic_transport_padding'] = 'x' * max(0, target - size - 40)
    return document


def fixture(output):
    root = output / 'synthetic-estate'
    root.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    artifact = {'path': 'data/stock_desk/theses.jsonl', 'format': 'jsonl',
                'producer': 'engine/stock_desk.py', 'owner_program': 'qualitative-intelligence',
                'cadence': 'daily-engine', 'storage': 'git', 'asof_field': 'asof',
                'freshness_sla_hours': 24, 'schema': 'none', 'tier': 'shadow',
                'horizon_role': 'context', 'weights': 'none', 'consumers': []}
    write_json(root / 'config/synapse.yml', {'meta': {'schema_version': 1,
               'description': 'SYNTHETIC A28', 'tier_vocabulary': {}, 'article2_surfaces': []},
               'artifacts': {'stock-ledger': artifact}})
    write_json(root / 'config/intelligence_registry_overlay.yml', {'engines': {
               'engine/stock_desk.py::qualitative-intelligence': {'output_class': {
               'value': 'predictive', 'rationale': 'Synthetic fixture only'}}}})
    (root / 'engine').mkdir(exist_ok=True)
    (root / 'engine/stock_desk.py').write_text('')
    write_json(root / 'data/stock_desk/theses.jsonl', {'asof': now})
    (root / 'config/qual_ladder.yml').write_text('families:\n  - claim_family: stock_desk\n')
    c = corpus(root / 'data/qledger/claims.jsonl', CLAIMS_BYTES,
               {'desk': 'stock_desk', 'claim_family': 'stock_desk', 'asof': '2026-08-19',
                'scope': {'type': 'entity', 'key': 'SYNTHETIC_ONLY'}, 'direction': 1,
                'horizon_d': 20, 'horizon_unit': 'trading_days', 'clock_market': 'US',
                'timestamp_quality': 'CRAWL_BOUNDED', 'bench': 'SYNTHETIC_BENCH'})
    g = corpus(root / 'data/qledger/grades.jsonl', GRADES_BYTES,
               {'horizon_d': 21, 'check_by': '2026-10-12', 'direction': -1,
                'excess': None, 'hit': None, 'clock_basis': 'synthetic_only'})
    row = {'n_dates': 0, 'needed': 25, 'ready': None, 'approaching': None,
           'wilson_ci_low': None, 'hit_rate': None, 'excess_mean': None,
           'benchmark_baseline_hit_rate': 0.0, 'n_cohort_rows': 0,
           'control_coverage': None, 'cohort_rowless': {}, 'clock_basis': None}
    readiness = {'stock_desk': {str(h): dict(row) for h in (5, 21, 63)}}
    report = pad_document({'promotion_readiness': readiness,
                          'promotion_readiness_at': now, 'by_family': {},
                          'placebo_magnitude': {}}, READINESS_BYTES)
    write_json(root / 'site/qledger/track_record.json', report)
    findings = pad_document({'schema': 'neuralweb.confluence_graph.v1',
                'artifact_id': 'confluence-graph', 'asof': 'unknown', 'produced_at': now,
                'produced_by': 'engine/neuralweb/confluence.py', 'tier': 'display',
                'is_context_only': True, 'display_only': True,
                'contradiction_records': [], 'gaps': ['SYNTHETIC source not supplied']}, FINDINGS_BYTES)
    write_json(root / 'data/neuralweb/confluence_graph.json', findings)
    return root, {'claims': c, 'grades': g, 'artifact_count': 1,
                  'readiness_bytes': (root / 'site/qledger/track_record.json').stat().st_size,
                  'findings_bytes': (root / 'data/neuralweb/confluence_graph.json').stat().st_size,
                  'fixture_limits': ['One real synthetic T4 artifact; not the entire production estate.',
                                     'Owner reports use disclosed byte padding, not production object distributions.',
                                     'Synthetic grades carry no observed outcomes and must never be read.']}


def peak_rss():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == 'darwin' else value * 1024)


def child(tree, root, lane, destination):
    sys.path.insert(0, str(tree))
    started = time.perf_counter()
    from admin import intelligence_os as ios
    from engine import qledger as q, qledger_store as store
    from scripts import build_output_health as health, grade_qledger as grader
    imported = time.perf_counter() - started
    calls = {'claim_text': [], 'grade_read_attempts': 0, 'readiness_compute_attempts': 0}
    original = store.read_tracked_claims_text
    def tracked(*args, **kwargs):
        text, source = original(*args, **kwargs)
        # Synthetic fixture ASCII: character length == raw UTF-8 bytes, no encoding copy.
        calls['claim_text'].append({'bytes': len(text) if text is not None else None,
                                    'source': str(source)})
        return text, source
    store.read_tracked_claims_text = tracked
    def no_compute(*args, **kwargs):
        calls['readiness_compute_attempts'] += 1
        raise AssertionError('Request-time readiness computation prohibited')
    grader.compute_promotion_readiness = no_compute
    def no_grades(*args, **kwargs):
        calls['grade_read_attempts'] += 1
        raise AssertionError('Grade parsing prohibited in recorded reader')
    q.load_grades = no_grades
    grade_path = (root / 'data/qledger/grades.jsonl').resolve()
    def guarded_open(original_open):
        def opened(path, mode='r', *args, **kwargs):
            if isinstance(path, (str, bytes, os.PathLike)) and Path(os.fsdecode(path)).resolve() == grade_path and 'r' in str(mode):
                return no_grades()
            return original_open(path, mode, *args, **kwargs)
        return opened
    builtins.open = guarded_open(builtins.open)
    io.open = guarded_open(io.open)
    os_open = os.open
    def guarded_os_open(path, flags, *args, **kwargs):
        if isinstance(path, (str, bytes, os.PathLike)) and Path(os.fsdecode(path)).resolve() == grade_path and flags & os.O_ACCMODE == os.O_RDONLY:
            return no_grades()
        return os_open(path, flags, *args, **kwargs)
    os.open = guarded_os_open
    ios._CACHE.clear()
    now = datetime.now(timezone.utc)
    samples = []
    def sample(name, fn):
        n = len(calls['claim_text']); begin = time.perf_counter(); cpu = time.process_time()
        result = fn()
        entry = {'name': name, 'wall_seconds': time.perf_counter() - begin,
                 'cpu_seconds': time.process_time() - cpu, 'peak_rss_bytes': peak_rss(),
                 'claim_transports': calls['claim_text'][n:]}
        samples.append(entry)
        return result
    if lane == 'baseline':
        def baseline():
            with store.ClaimsReadScope(root):
                return health.build_with_registry(root, now=now, trust_mtime=False)
        view, registry = sample('unchanged_T1_T4_cold', baseline)
    else:
        cold = sample('A1_cold_force', lambda: ios._derive(root, force=True))
        assert cold[4] == 'miss'
        hit = sample('A1_cache_hit', lambda: ios._derive(root, force=False))
        assert hit[4] == 'hit'
        forced = sample('A1_force', lambda: ios._derive(root, force=True))
        assert forced[4] == 'miss'
        def pair():
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: ios._derive(root, force=True), range(2)))
            assert all(result[4] == 'miss' for result in results)
            return results[-1]
        last = sample('A1_two_serialized_force_callers', pair)
        view, registry = last[:2]
        assert view['typed_findings']['status'] == 'recorded'
        provider = next(iter(last[2].values()))
        assert provider['read_status'] == 'partial'
        assert provider['recorded_snapshot']['current_source_qualification'] == 'unavailable'
        assert provider['readiness']['63']['ready'] is None
        assert provider['readiness']['63']['benchmark_baseline_hit_rate'] == 0.0
    assert calls['claim_text'] and calls['claim_text'][0]['bytes'] >= CLAIMS_BYTES
    assert calls['grade_read_attempts'] == calls['readiness_compute_attempts'] == 0
    report = {'lane': lane, 'ok': True, 'samples': samples, 'calls': calls,
              'peak_rss_bytes': peak_rss(), 'module_import_wall_seconds': imported,
              'whole_child_wall_seconds': time.perf_counter() - started,
              'canonical_engines': len(registry.get('engines', [])),
              'assessed_artifacts': len(view.get('outputs', [])),
              'python': sys.version, 'platform': platform.platform(),
              'fixture_root': str(root.resolve()), 'source_root': str(tree.resolve()),
              'measurement_limits': ['ru_maxrss is process lifetime maximum, including imports; per-sample peaks are cumulative.',
                                     'Claim transport byte count is not total physical I/O or disk-cache misses.',
                                     'All lanes import the same current modules to control interpreter/import baseline.']}
    write_json(destination, report)


def watched(python, script, tree, root, lane, destination):
    log = destination.with_suffix('.log')
    started = time.monotonic(); max_sampled = 0; reason = None
    with log.open('wb') as handle:
        process = subprocess.Popen([python, str(script), '--child', lane, '--tree', str(tree),
                                    '--root', str(root), '--result', str(destination)], stdout=handle, stderr=handle)
        while process.poll() is None:
            if time.monotonic() - started > SECONDS_CEILING:
                reason = '60_second_sample_deadline'; break
            observation = subprocess.run(['ps', '-o', 'rss=', '-p', str(process.pid)], capture_output=True, text=True)
            try: rss = int(observation.stdout.strip()) * 1024
            except ValueError: rss = 0
            max_sampled = max(max_sampled, rss)
            if rss > RSS_CEILING:
                reason = '1GiB_sampled_RSS_ceiling'; break
            time.sleep(0.05)
        if reason:
            process.terminate()
            try: process.wait(timeout=2)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
        rc = process.wait()
    data = json.loads(destination.read_text()) if destination.exists() else None
    if data and data['peak_rss_bytes'] > RSS_CEILING:
        reason = reason or '1GiB_final_peak_RSS_ceiling'
    return {'lane': lane, 'returncode': rc, 'watchdog_reason': reason,
            'sampled_peak_rss_bytes': max_sampled, 'elapsed_seconds': time.monotonic() - started,
            'result': data, 'log': str(log), 'ok': rc == 0 and reason is None and bool(data and data['ok'])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--tree', type=Path, default=DEFAULT_TREE)
    parser.add_argument('--output', type=Path, default=Path(__file__).parent)
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--child', choices=['baseline', 'A1'])
    parser.add_argument('--root', type=Path)
    parser.add_argument('--result', type=Path)
    args = parser.parse_args()
    if args.child:
        child(args.tree, args.root, args.child, args.result); return
    if not args.execute:
        parser.error('Explicit --execute is required; authoring did not run this probe')
    args.output.mkdir(parents=True, exist_ok=True)
    root, inputs = fixture(args.output)
    before = {str(p.relative_to(root)): sha(p) for p in root.rglob('*') if p.is_file()}
    sources = {p: sha(args.tree / p) for p in ['admin/intelligence_os.py','admin/evidence_status.py',
               'admin/evidence_findings.py','scripts/build_intelligence_registry.py',
               'scripts/build_output_health.py','engine/qledger_store.py','scripts/grade_qledger.py']}
    runs = []
    for lane in ['baseline', 'A1']:
        run = watched(args.python, Path(__file__).resolve(), args.tree, root, lane, args.output / (lane + '-result.json'))
        runs.append(run)
        if not run['ok']: break
    after = {str(p.relative_to(root)): sha(p) for p in root.rglob('*') if p.is_file()}
    final_sources = {p: sha(args.tree / p) for p in sources}
    report = {'schema': 'eval_os.a28.synthetic_differential.v1', 'inputs': inputs,
              'source_sha256': sources, 'source_stable': sources == final_sources,
              'fixture_unchanged': before == after, 'runs': runs,
              'rss_watchdog_ceiling_bytes': RSS_CEILING, 'per_child_deadline_seconds': SECONDS_CEILING,
              'watchdog_limit': '50ms sampled process RSS; final ru_maxrss also checks transient overshoot. No hard address-space limit.',
              'ok': len(runs) == 2 and all(r['ok'] for r in runs) and before == after and sources == final_sources,
              'acceptance_scope': 'Synthetic ledger-size differential only; not production full-estate concurrency, client latency or market/data proof.'}
    if len(runs) == 2 and all(r['result'] for r in runs):
        report['A1_minus_baseline_peak_rss_bytes'] = runs[1]['result']['peak_rss_bytes'] - runs[0]['result']['peak_rss_bytes']
        report['A1_cold_minus_baseline_wall_seconds'] = runs[1]['result']['samples'][0]['wall_seconds'] - runs[0]['result']['samples'][0]['wall_seconds']
    write_json(args.output / 'composed-scale-report.json', report)
    print(json.dumps({'ok': report['ok'], 'report': str(args.output / 'composed-scale-report.json')}))
    if not report['ok']: sys.exit(1)


if __name__ == '__main__':
    main()
