#!/usr/bin/env python3
"""Run one reviewed, read-only host proof after exact positive ancestry checks.

Only local /private/tmp evidence files are written. No fetch, deployment,
restart, acquisition, repository mutation or retry is performed.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

REPO = Path('/Users/chriswong/Documents/GitHub/macro/.claude/worktrees/rs-pullback-reference-admission-20261007')
SCRIPT = Path('/private/tmp/rs-pullback-installed-native-conformance-33040ed34fa4.py')
SCRIPT_SHA256 = '33040ed34fa4e413d7de754a0bd9b41558fad6007b66036cd3386d121d9133b5'
CANDIDATE = '6d14f398564dce1d0f68daf956315cf7e9d19520'
RELEASE = '7a1f9ad0a28973cdc9b261e80bfdf61f4eae9575'

def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()

def digest(value):
    return hashlib.sha256(value).hexdigest()

def write_once(path, data):
    with path.open('xb') as stream:
        stream.write(data)

def git(*args):
    result = subprocess.run(['git', '--no-optional-locks', '-c', 'core.fsmonitor=false', '-c', 'protocol.allow=never', '-C', str(REPO), *args], capture_output=True, timeout=30,
        env={'PATH': os.defpath, 'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0', 'GIT_NO_LAZY_FETCH': '1', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'})
    if result.returncode:
        raise RuntimeError('FULL_REPOSITORY_READ_FAILED:' + args[0])
    return result.stdout

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--expected-process-commit', required=True)
    args = parser.parse_args()
    for value in (args.expected_head, args.expected_process_commit):
        if not re.fullmatch('[0-9a-f]{40}', value):
            parser.error('Both commit pins must be exact full lowercase SHA-1 IDs')
    start = time.time_ns()
    stem = Path('/private/tmp/rs-pullback-installed-native-' + str(start))
    script = SCRIPT.read_bytes()
    if digest(script) != SCRIPT_SHA256:
        raise RuntimeError('REVIEWED_SCRIPT_DIGEST_MISMATCH')
    expected = {}
    for node in ast.parse(script).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ('SOURCES', 'ARTIFACTS'):
            expected.update(ast.literal_eval(node.value))
    shallow = git('rev-parse', '--is-shallow-repository').strip()
    if len(expected) != 13 or shallow not in (b'true', b'false'):
        raise RuntimeError('REPOSITORY_OR_PROTECTED_PATH_CENSUS_UNAVAILABLE')
    baseline = {}
    for path, sha in expected.items():
        blob = git('rev-parse', CANDIDATE + ':' + path).decode().strip()
        data = git('cat-file', 'blob', blob)
        if len(data) > 64 * 1024 * 1024 or digest(data) != sha:
            raise RuntimeError('ACCEPTED_BYTES_MISMATCH:' + path)
        baseline[path] = blob
    extra_baseline = {path: git('rev-parse', CANDIDATE + ':' + path).decode().strip() for path in ('lib/dataos', 'app/main.py')}
    verified = {}
    for label, ref in (('checkout', args.expected_head), ('process_build', args.expected_process_commit)):
        git('merge-base', '--is-ancestor', RELEASE, ref)
        entries = {path: git('rev-parse', ref + ':' + path).decode().strip() for path in baseline}
        closure = {path: git('rev-parse', ref + ':' + path).decode().strip() for path in extra_baseline}
        if entries != baseline or closure != extra_baseline:
            raise RuntimeError('APPROVED_REF_SOURCE_OR_ARTIFACT_DRIFT:' + label)
        verified[label] = {'commit': ref, 'release_is_ancestor': True, 'protected_blobs': entries, 'additional_import_and_health_bindings': closure}
    lineage = {'schema': 'mastermind.rs_pullback_launch.installed_native_release_lineage.v1', 'repository': str(REPO), 'nonshallow': shallow == b'false',
        'ancestry_method': 'Both exact git merge-base --is-ancestor commands must exit zero; unavailable or negative ancestry aborts. A positive ancestry result uses present history even if an unrelated older boundary is shallow.',
        'accepted_candidate': CANDIDATE, 'merged_release': RELEASE, 'proof_script_sha256': SCRIPT_SHA256,
        'started_at_utc_ns': str(start), 'completed_at_utc_ns': str(time.time_ns()), 'protected_sha256': expected, 'verified_refs': verified}
    lineage_bytes = encoded(lineage)
    lineage_path = Path(str(stem) + '-lineage.json')
    write_once(lineage_path, lineage_bytes)
    ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-i', '/Users/chriswong/.ssh/macro_dashboard_deploy_v2',
        'root@146.190.142.17', '/opt/macro-api/.venv/bin/python', '-B', '-', '--expected-head', args.expected_head,
        '--expected-process-commit', args.expected_process_commit]
    try:
        result = subprocess.run(ssh, input=script, capture_output=True, timeout=120)
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, code = exc.stdout or b'', exc.stderr or b'', 124
    proof_path = Path(str(stem) + '-proof.json')
    write_once(proof_path, stdout)
    if stderr:
        write_once(Path(str(stem) + '-stderr.txt'), stderr)
    accepted = False
    status = 'REMOTE_OUTPUT_UNAVAILABLE'
    try:
        proof = json.loads(stdout)
        status = proof.get('status')
        installation = proof['installation']
        health = proof['api_health']
        accepted = (code == 0 and status == 'PASS_SCOPED_INSTALLED_PROOF'
            and installation['actual_head'] == args.expected_head
            and installation['expected_process_commit'] == args.expected_process_commit
            and installation['merged_release_commit'] == RELEASE
            and health['expected_process_commit'] == args.expected_process_commit
            and health['expected_checkout_commit'] == args.expected_head
            and proof['protected_bytes_unchanged_after'] is True)
    except (ValueError, KeyError, TypeError):
        pass
    receipt = {'schema': 'mastermind.rs_pullback_launch.installed_native_delivery_receipt.v1', 'result': 'PASS' if accepted else 'FAIL_OR_UNAVAILABLE',
        'completed_at_utc_ns': str(time.time_ns()), 'proof_script_sha256': SCRIPT_SHA256,
        'expected_checkout': args.expected_head, 'expected_process_build': args.expected_process_commit,
        'lineage_path': str(lineage_path), 'lineage_bytes': len(lineage_bytes), 'lineage_sha256': digest(lineage_bytes),
        'proof_path': str(proof_path), 'proof_bytes': len(stdout), 'proof_sha256': digest(stdout), 'ssh_exit_code': code, 'remote_status': status}
    receipt_path = Path(str(stem) + '-delivery.json')
    write_once(receipt_path, encoded(receipt))
    if accepted:
        write_once(Path('/private/tmp/rs-pullback-installed-native-conformance-20261007.json'), stdout)
    print(json.dumps({'receipt_path': str(receipt_path), **receipt}, sort_keys=True))
    return 0 if accepted else 1

if __name__ == '__main__':
    raise SystemExit(main())
