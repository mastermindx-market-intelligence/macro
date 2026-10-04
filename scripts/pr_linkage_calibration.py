#!/usr/bin/env python3
"""Replay frozen, independently labeled MAS-28 observations. Report-only; no network."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib import pr_linkage_validator as core


def bind_labels(cases: list[dict], ledger: list[dict]) -> list[dict]:
    """Join the pre-evaluation ledger only after verifying exact observation identity."""
    def index(rows):
        result = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('id'), str):
                raise ValueError('case identity must be a string')
            if row['id'] in result:
                raise ValueError('duplicate case identity')
            result[row['id']] = row
        return result
    observations, labels = index(cases), index(ledger)
    if observations.keys() != labels.keys():
        raise ValueError('label ledger identity set differs from corpus')
    bound = []
    for ident, case in sorted(observations.items()):
        label = labels[ident]
        if core.digest(case['observation']) != label['observation_digest']:
            raise ValueError(f'{ident}: observation digest differs from frozen labels')
        if 'labels' in case and case['labels'] != label['labels']:
            raise ValueError(f'{ident}: embedded labels differ from frozen ledger')
        bound.append({**case, 'labels': label['labels']})
    return bound


def _strings(value, name):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        raise ValueError(f'{name} must be a list of nonempty strings')
    if len(set(value)) != len(value):
        raise ValueError(f'{name} must not contain duplicates')
    return value


def calibrate(cases: list[dict], manifest: dict) -> dict:
    """Measure explicitly judged rule/case pairs; separate incomplete observations."""
    rules = {row['rule_id'] for row in manifest['rules']}
    seen: set[str] = set()
    rows, cohorts = [], {}
    for case in sorted(cases, key=lambda row: row['id']):
        ident, cohort, labels = case['id'], case['cohort'], case['labels']
        if not isinstance(ident, str) or not ident or not isinstance(cohort, str) or not cohort:
            raise ValueError('case id and cohort must be nonempty strings')
        if ident in seen:
            raise ValueError(f'duplicate case id: {ident}')
        seen.add(ident)
        expected = set(_strings(labels['expected_rules'], 'expected_rules'))
        judged = set(_strings(labels['judged_rules'], 'judged_rules'))
        unresolved = _strings(labels['unresolved'], 'unresolved')
        if not isinstance(labels['scope'], str) or not labels['scope']:
            raise ValueError('label scope must be a nonempty string')
        if not expected <= judged or not judged <= rules:
            raise ValueError(f'{ident}: positive labels must be judged manifest rules')
        agg = cohorts.setdefault(cohort, {'observations': 0, 'complete': 0,
                                         'incomplete': 0, 'execution_invalid': 0, 'rules': {}})
        agg['observations'] += 1
        try:
            report = core.analyze(case['observation'], manifest)
            repeat = core.analyze(case['observation'], manifest)
        except core.ValidationError as exc:
            agg['execution_invalid'] += 1
            rows.append({'id': ident, 'cohort': cohort, 'label_scope': labels['scope'],
                         'execution_error': str(exc), 'incomplete': True,
                         'unresolved': unresolved, 'judged_rules': sorted(judged),
                         'expected_rules': sorted(expected), 'observed_rules': None,
                         'false_positive_rules': None, 'false_negative_rules': None})
            continue
        if core.canonical_json(report) != core.canonical_json(repeat):
            raise ValueError(f'{ident}: nondeterministic report')
        semantic = report['semantic']
        observed = {f['rule_id'] for f in semantic['findings']}
        incomplete = bool(unresolved) or semantic['completeness'] != 'COMPLETE'
        partition = 'incomplete' if incomplete else 'complete'
        agg[partition] += 1
        for rule in sorted(judged | observed):
            counts = agg['rules'].setdefault(rule, {
                'complete': dict(tp=0, fp=0, fn=0, tn=0),
                'incomplete': dict(tp=0, fp=0, fn=0, tn=0),
                'unjudged_observed': 0})
            if rule not in judged:
                counts['unjudged_observed'] += 1
                continue
            bucket = ('tp' if rule in observed else 'fn') if rule in expected else ('fp' if rule in observed else 'tn')
            counts[partition][bucket] += 1
        rows.append({'id': ident, 'cohort': cohort, 'label_scope': labels['scope'],
                     'verdict': semantic['verdict'], 'completeness': semantic['completeness'],
                     'incomplete': incomplete, 'unresolved': unresolved,
                     'validator_unresolved': semantic['unresolved_observation_classes'],
                     'judged_rules': sorted(judged), 'expected_rules': sorted(expected),
                     'observed_rules': sorted(observed),
                     'false_positive_rules': sorted((observed - expected) & judged),
                     'false_negative_rules': sorted(expected - observed),
                     'unjudged_observed_rules': sorted(observed - judged),
                     'semantic_hash': report['semantic_hash']})
    for cohort in cohorts.values():
        for counts in cohort['rules'].values():
            c = counts['complete']
            counts['judged_complete'] = sum(c.values())
            counts['judged_incomplete'] = sum(counts['incomplete'].values())
            counts['complete_fpr'] = c['fp'] / (c['fp'] + c['tn']) if c['fp'] + c['tn'] else None
            counts['complete_fnr'] = c['fn'] / (c['fn'] + c['tp']) if c['fn'] + c['tp'] else None
    observations = [{'id': c['id'], 'cohort': c['cohort'], 'observation': c['observation']}
                    for c in sorted(cases, key=lambda row: row['id'])]
    ledger = [{'id': c['id'], 'observation_digest': core.digest(c['observation']), 'labels': c['labels']}
              for c in sorted(cases, key=lambda row: row['id'])]
    return {'schema': 'mastermind.pr_linkage_calibration.v1', 'enforcement': 'REPORT_ONLY',
            'status': 'PARTIAL_EXECUTION' if any(c['execution_invalid'] for c in cohorts.values()) else 'EVALUATED',
            'ruleset_digest': core.digest(manifest),
            'corpus_observation_digest': core.digest(observations),
            'label_ledger_digest': core.digest(ledger), 'cohorts': cohorts, 'cases': rows,
            'interpretation': 'Counts apply only to frozen judged rule/case pairs. '
                              'Incomplete counts are scoped judgments, not full-validator error rates. '
                              'Synthetic rates are regression measurements, not estate estimates.'}


def verify_source(source_sha: str) -> dict:
    """Check evaluator bytes against an immutable local Git commit, without fetching."""
    if not re.fullmatch('[0-9a-f]{40}', source_sha):
        raise ValueError('source SHA must be a full lowercase Git commit')
    hashes = {}
    for relative in ('lib/pr_linkage_validator.py', 'config/pr_linkage_rules.v1.json'):
        result = subprocess.run(['git', 'show', f'{source_sha}:{relative}'], cwd=ROOT,
                                capture_output=True, timeout=30, check=True)
        current = (ROOT / relative).read_bytes()
        if result.stdout != current:
            raise ValueError(f'source SHA does not identify current {relative}')
        hashes[relative] = hashlib.sha256(current).hexdigest()
    return {'commit': source_sha, 'files': hashes}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corpus', type=Path)
    parser.add_argument('--labels', required=True, type=Path)
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        source = verify_source(args.source_sha)
        cases = core.loads_strict(args.corpus.read_bytes())
        ledger = core.loads_strict(args.labels.read_bytes())
        manifest = core.loads_strict((ROOT / 'config/pr_linkage_rules.v1.json').read_bytes())
        report = calibrate(bind_labels(cases, ledger), manifest)
        report['validator_source'] = source
        report['runner_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        payload = core.canonical_json(report) + b'\n'
        if args.output:
            # Explicit operator-owned evidence file only; failed runs preserve older output.
            name = None
            try:
                with tempfile.NamedTemporaryFile(dir=args.output.parent, delete=False) as handle:
                    name = handle.name
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(name, args.output)
            finally:
                if name and os.path.exists(name):
                    os.unlink(name)
        else:
            sys.stdout.buffer.write(payload)
        return 2 if report['status'] == 'PARTIAL_EXECUTION' else 0
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as exc:
        print(f'calibration invalid: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
