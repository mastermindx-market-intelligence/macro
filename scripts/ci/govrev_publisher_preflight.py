#!/usr/bin/env python3
"""Read the existing publisher's retained GitHub Actions evidence before effects.

This is a bounded preflight of three existing workflow families, not a scheduler.
The protected baseline retires only individually reconciled legacy operations.
A passed checkpoint carries previous coverage; its own later push is checked anew.
"""
from __future__ import annotations
import argparse
import base64
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

import govrev_candidate_proof as proof
import govrev_source_binding as source_binding

REPOSITORY = 'mastermindx-market-intelligence/macro'
FAMILIES = {'government-revenue-live.yml': 'refresh',
            'daily.yml': 'government_revenue_projection / refresh',
            'fms-acquire.yml': 'publish / refresh'}
STEP_NAME = 'reconcile retained GovRev publication outcomes'
BASELINE = 'research/defense_intelligence/e2e_20261011/PUBLISHER_RECOVERY_BASELINE.json'
CASE = 'govrev-candidate-proof.run-case.json'
CHECKPOINT = 'govrev-candidate-proof.preflight.json'
SOURCE_PATHS = ('scripts/ci/govrev_publisher_preflight.py', 'scripts/ci/govrev_candidate_proof.py',
                'scripts/ci/govrev_source_binding.py',
                'scripts/ci/fms_persist.py',
                '.github/workflows/government-revenue-live.yml', '.github/workflows/daily.yml',
                '.github/workflows/fms-acquire.yml')

class Refused(ValueError):
    pass


def stamp():
    return datetime.now(timezone.utc).isoformat()


def parse_time(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise Refused('unqualified_clock')
    return result


def digest(body):
    return hashlib.sha256(body).hexdigest()


def source_closure(root):
    return {p: digest((root / p).read_bytes()) for p in SOURCE_PATHS}


def read_baseline(root):
    value = json.loads((root / BASELINE).read_text())
    if (value.get('contract') != 'government_revenue.publisher_recovery_baseline.v1'
            or value.get('repository') != REPOSITORY or value.get('families') != FAMILIES
            or value.get('source_closure') != source_closure(root)):
        raise Refused('baseline_source_or_owner_not_qualified')
    parse_time(value['scan_created_after'])
    if (value.get('legacy_census_complete') is not True
            or not re.fullmatch('[0-9a-f]{64}', value.get('legacy_census_evidence_sha256', ''))
            or not isinstance(value.get('legacy_effects_reconciled_at'), str)):
        raise Refused('legacy_census_not_qualified')
    parse_time(value['legacy_effects_reconciled_at'])
    entries = value['reconciled_legacy_operations']
    if not isinstance(entries, list) or not entries:
        raise Refused('legacy_census_missing')
    for entry in entries:
        if (not isinstance(entry.get('run_id'), int) or not isinstance(entry.get('run_attempt'), int)
                or entry.get('operation_scope') != 'govrev_publisher'
                or not isinstance(entry.get('publisher_job_id'), int)
                or entry.get('workflow_path') not in {'.github/workflows/' + name for name in FAMILIES}
                or not isinstance(entry.get('publisher_job_name'), str)
                or entry.get('disposition') not in ('no_publication_effect', 'original_effect_confirmed', 'explicitly_retired')
                or not re.fullmatch('[0-9a-f]{64}', entry.get('evidence_sha256', ''))):
            raise Refused('unqualified_legacy_disposition')
    if len({(e['run_id'], e['run_attempt']) for e in entries}) != len(entries):
        raise Refused('legacy_case_not_unique')
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHub:
    def __init__(self, token):
        if not token:
            raise Refused('actions_read_credential_missing')
        self.token = token
        self.deadline = time.monotonic() + 180

    def read(self, url, *, authenticated=True, redirect=False, limit=16777216):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise Refused('bounded_preflight_budget_exhausted')
        headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
        if authenticated:
            headers['Authorization'] = 'Bearer ' + self.token
        req = urllib.request.Request(url, headers=headers)
        try:
            opener = urllib.request.build_opener(NoRedirect)
            with opener.open(req, timeout=min(10, remaining)) as response:
                body = response.read(limit + 1)
                if len(body) > limit:
                    raise Refused('retained_evidence_budget_exceeded')
                return body
        except urllib.error.HTTPError as exc:
            if redirect and exc.code in (301, 302, 303, 307, 308):
                location = exc.headers.get('Location', '')
                parsed = urllib.parse.urlparse(location)
                if parsed.scheme != 'https' or not (parsed.hostname or '').endswith(('.githubusercontent.com', '.blob.core.windows.net', '.actions.githubusercontent.com')):
                    raise Refused('artifact_redirect_not_qualified')
                # Never forward the GitHub token to the signed artifact host.
                return self.read(location, authenticated=False, limit=limit)
            raise Refused('github_evidence_read_refused') from None
        except (OSError, urllib.error.URLError):
            raise Refused('github_evidence_read_failed') from None

    def json(self, path):
        return json.loads(self.read('https://api.github.com/repos/' + REPOSITORY + '/' + path))

    def source_file(self, relative, commit):
        if not re.fullmatch('[0-9a-f]{40}', commit):
            raise Refused('legacy_workflow_commit_not_qualified')
        value = self.json('contents/' + urllib.parse.quote(relative, safe='/') + '?ref=' + commit)
        if value.get('type') != 'file' or value.get('path') != relative or value.get('encoding') != 'base64':
            raise Refused('legacy_source_object_not_qualified')
        body = base64.b64decode(''.join(value['content'].split()), validate=True)
        blob = hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()
        if blob != value.get('sha') or len(body) != value.get('size'):
            raise Refused('legacy_source_object_identity_mismatch')
        return body, {"git_blob_sha": blob, "sha256": digest(body), "bytes": len(body)}

    def archive(self, run_id, attempt):
        name = f'govrev-candidate-proof-diagnostics-{run_id}-{attempt}'
        found = []
        for page in range(1, 5):
            value = self.json(f'actions/runs/{run_id}/artifacts?per_page=100&page={page}')
            items = value['artifacts']
            found.extend(a for a in items if a['name'] == name)
            if len(items) < 100:
                break
        else:
            raise Refused('artifact_census_incomplete')
        if len(found) != 1 or found[0].get('expired') or found[0].get('workflow_run', {}).get('id') != run_id:
            raise Refused('required_retained_artifact_missing_or_expired')
        item = found[0]
        body = self.read(f'https://api.github.com/repos/{REPOSITORY}/actions/artifacts/{item["id"]}/zip', redirect=True)
        return unpack(body), {'artifact_id': item['id'], 'archive_sha256': digest(body)}


def unpack(body):
    files = {}
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        total = 0
        for item in archive.infolist():
            if item.is_dir():
                continue
            name = Path(item.filename).name
            if name in files or item.filename != name or (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise Refused('artifact_path_or_duplicate_refused')
            total += item.file_size
            if item.file_size > 8388608 or total > 33554432:
                raise Refused('retained_evidence_budget_exceeded')
            files[name] = archive.read(item)
    return files


def load_case(files, record):
    case = json.loads(files[CASE])
    if (case.get('contract') != 'government_revenue.publisher_run_case.v1'
            or case.get('repository') != REPOSITORY
            or case.get('run_id') != record['run_id'] or case.get('run_attempt') != record['run_attempt']
            or case.get('job_id') != record['job_id'] or case.get('workflow_path') != record['workflow_path']
            or case.get('phase') not in ('created_before_effect', 'preflight_passed_before_effect', 'preflight_refused_before_effect')
            or case.get('source_closure') != record.get('expected_source_closure')
            or not re.fullmatch('[0-9a-f]{40}', case.get('checkout_commit', ''))):
        raise Refused('retained_case_owner_or_attempt_mismatch')
    return case


def qualified_records(api, created_after, current_key):
    records, pending = {}, []
    for family, job_name in FAMILIES.items():
        runs = {}
        # Active callers can have been created before the rolling scan floor.
        # Inspect only their GovRev target, not unrelated daily/FMS jobs.
        for selector in ({"created": ">=" + created_after}, {"status": "queued"}, {"status": "in_progress"}):
            for page in range(1, 5):
                query = urllib.parse.urlencode({"per_page": 100, "page": page, **selector})
                items = api.json(f'actions/workflows/{family}/runs?{query}')['workflow_runs']
                for run in items:
                    if run.get('path') != '.github/workflows/' + family:
                        raise Refused('workflow_family_mismatch')
                    runs[run['id']] = run
                if len(items) < 100:
                    break
            else:
                raise Refused('bounded_workflow_census_incomplete')
        for run in runs.values():
            for attempt in range(1, run['run_attempt'] + 1):
                key = (run['id'], attempt)
                if key == current_key:
                    continue
                jobs = api.json(f'actions/runs/{run["id"]}/attempts/{attempt}/jobs?per_page=100')
                if jobs.get('total_count', 0) > 100:
                    raise Refused('job_census_incomplete')
                targets = []
                for job in jobs['jobs']:
                    skipped = (job.get('status') == 'completed' and job.get('conclusion') == 'skipped'
                               and not job.get('steps'))
                    parent_name = job_name.split(' / ')[0]
                    if job['name'] == job_name or (job['name'] == parent_name and skipped):
                        targets.append((job, skipped))
                if not targets and run['status'] != 'completed':
                    pending.append(run['created_at'])
                for job, skipped in targets:
                    if not job.get('started_at') and not skipped:
                        pending.append(run['created_at'])
                        continue
                    if job['status'] != 'completed':
                        raise Refused('another_publisher_job_still_active')
                    record = {'run_id': run['id'], 'run_attempt': attempt, 'job_id': job['id'],
                              'workflow_path': run['path'], 'started_at': job.get('started_at') or run['created_at'],
                              'created_at': run['created_at'], 'steps': job.get('steps', []),
                              'publisher_never_started': skipped, 'publisher_job_name': job['name'],
                              'workflow_head_sha': run.get('head_sha'), 'publisher_job_status': job['status']}
                    if key in records:
                        raise Refused('publisher_case_not_unique')
                    records[key] = record
    return list(records.values()), pending


def _caller_job_block(body, job_name):
    text = body.decode('utf-8')
    starts = list(re.finditer(r'^  ' + re.escape(job_name) + r':\s*$', text, re.M))
    if len(starts) != 1:
        raise Refused('legacy_caller_job_not_unique')
    start = starts[0].start()
    tail = text[start:]
    following = re.search(r'\n  [A-Za-z_][A-Za-z0-9_-]*:', tail[1:])
    end = start + 1 + following.start() + 1 if following else len(text)
    return text[start:end].encode()


def _legacy_checkout_commit(log):
    # Checkout's actual command/result, not the workflow run's definition SHA.
    lines = log.decode('utf-8', errors='replace').splitlines()
    candidates = []
    for index, line in enumerate(lines[:-1]):
        if '[command]' in line and re.search(r'\bgit log -1 --format=[\"\']?%H', line):
            next_line = lines[index + 1]
            match = re.fullmatch(r'(?:[0-9]{4}-[0-9T:.-]+Z\s+)?([0-9a-f]{40})', next_line.strip())
            if match:
                candidates.append(match.group(1))
    if len(candidates) != 1:
        raise Refused('legacy_runtime_checkout_not_qualified')
    return candidates[0]


def classify_legacy_never_published(api, record, baseline):
    allowed = baseline.get('legacy_never_started_workflow_whitelist', [])
    if not allowed:
        raise Refused('legacy_effect_not_in_reviewed_census')
    if record.get('publisher_job_status') != 'completed':
        raise Refused('legacy_publisher_not_terminal')
    head = record.get('workflow_head_sha')
    body, identity = api.source_file('.github/workflows/government-revenue-live.yml', head)
    matches = [entry for entry in allowed if entry.get('workflow') == {
        'workflow_path': '.github/workflows/government-revenue-live.yml', **identity}]
    if len(matches) != 1:
        raise Refused('legacy_workflow_not_independently_whitelisted')
    entry = matches[0]
    if (not re.fullmatch('[0-9a-f]{64}', entry.get('audit_evidence_sha256', ''))
            or entry.get('publisher_job_id') != 'refresh'
            or entry.get('timestamp_policy') != 'authenticated_completed_skipped_is_nonexecution'):
        raise Refused('legacy_semantic_audit_not_qualified')
    family = Path(record['workflow_path']).name
    caller_identity = None
    if family != 'government-revenue-live.yml':
        caller = entry.get('callers', {}).get(family)
        if not caller or caller.get('exact_uses') != './.github/workflows/government-revenue-live.yml':
            raise Refused('legacy_same_commit_caller_not_whitelisted')
        caller_body, caller_identity = api.source_file(record['workflow_path'], head)
        block = _caller_job_block(caller_body, caller['caller_job_id'])
        if (digest(block) != caller.get('caller_job_block_sha256')
                or len(re.findall(rb'^    uses: \./\.github/workflows/government-revenue-live\.yml\s*$', block, re.M)) != 1
                or record['publisher_job_name'] != caller['caller_job_id'] + ' / refresh'):
            raise Refused('legacy_same_commit_caller_link_drift')
    elif record['publisher_job_name'] != 'refresh':
        raise Refused('legacy_publisher_job_identity_mismatch')
    step_name = entry.get('sole_repository_publication_step_name')
    steps = [step for step in record['steps'] if step.get('name') == step_name]
    if (not isinstance(step_name, str) or len(steps) != 1 or steps[0].get('status') != 'completed'
            or steps[0].get('conclusion') != 'skipped'):
        raise Refused('legacy_publication_step_begun_missing_or_unqualified')
    # ref:main in the audited legacy YAML can resolve newer runtime source.
    # Authenticate the checkout and exactly the independently inspected entrypoints.
    deps = entry.get('dependency_source_identities')
    required = {'scripts/build_government_revenue.py', 'scripts/collect.py', 'scripts/ci/push_retry.sh',
                'collectors/sam_gov.py', 'collectors/base.py'}
    if not isinstance(deps, dict) or set(deps) != required:
        raise Refused('legacy_runtime_inspection_closure_incomplete')
    log = api.read(f'https://api.github.com/repos/{REPOSITORY}/actions/jobs/{record["job_id"]}/logs', redirect=True)
    checkout = _legacy_checkout_commit(log)
    actual_deps = {}
    for relative in sorted(required):
        _, actual = api.source_file(relative, checkout)
        if actual != deps[relative]:
            raise Refused('legacy_runtime_entrypoint_drift')
        actual_deps[relative] = actual
    return {'run_id': record['run_id'], 'run_attempt': record['run_attempt'], 'job_id': record['job_id'],
            'operation_scope': 'govrev_publisher', 'disposition': 'authenticated_audited_publication_step_skipped',
            'workflow_head_sha': head, 'workflow_identity': identity, 'caller_identity': caller_identity,
            'audit_evidence_sha256': entry['audit_evidence_sha256'], 'runtime_checkout_commit': checkout,
            'runtime_entrypoint_identities': actual_deps, 'job_log_sha256': digest(log),
            'publication_step': {'name': step_name, 'status': steps[0]['status'], 'conclusion': steps[0]['conclusion'],
                                 'scheduler_started_at': steps[0].get('started_at'),
                                 'scheduler_completed_at': steps[0].get('completed_at')},
            'scheduler_clocks_are_execution_evidence': False, 'issuance_authority': False,
            'unrelated_parent_effects_retired': False,
            'runtime_scope': 'inspected entrypoints only; no arbitrary transitive source or unrelated effect claim'}


def check_proof_archive(files, identity):
    raw = files['govrev-candidate-proof.receipt.json']
    receipt = json.loads(raw)
    if (digest(raw) != identity['proof_receipt_sha256'] or proof._required_receipt_fields(receipt)
            or proof.receipt_identity(receipt) != receipt['identity'] or receipt['identity'] != identity['proof_identity']):
        raise Refused('prior_push_proof_not_sealed')
    for item in receipt['execution_evidence']['artifacts'].values():
        body = files[item['filename']]
        if digest(body) != item['sha256'] or len(body) != item['bytes']:
            raise Refused('prior_execution_evidence_not_sealed')
    return receipt


def reconcile_record(root, files, record, out_dir):
    case = load_case(files, record)
    identities = sorted(name for name in files if re.fullmatch(r'govrev-candidate-proof.push-\d+\.identity.json', name))
    if not identities:
        return {'run_id': record['run_id'], 'run_attempt': record['run_attempt'], 'disposition': 'no_push_identity_no_push_effect'}
    results = []
    for name in identities:
        identity = json.loads(files[name])
        claimed = identity.pop('identity')
        if (claimed != digest(proof._canonical(identity).encode())
                or str(identity['run_id']) != str(record['run_id']) or str(identity['run_attempt']) != str(record['run_attempt'])):
            raise Refused('original_push_identity_not_qualified')
        identity['identity'] = claimed
        outcome_raw = files.get(name.replace('.identity.json', '.outcome.json'))
        outcome = json.loads(outcome_raw)['outcome'] if outcome_raw else 'effect_unknown'
        if outcome == 'refused':
            raise Refused('prior_explicit_refusal_not_retired')
        if outcome == 'definite_contention_rejection':
            results.append({'push_identity': claimed, 'disposition': 'definite_no_write_rejection'})
            continue
        if outcome not in ('successful', 'effect_unknown'):
            raise Refused('unqualified_prior_outcome')
        receipt = check_proof_archive(files, identity)
        # Historical observation uses the original identity, never a replacement push.
        identity_path = out_dir / f'govrev-candidate-proof.prior-{record["run_id"]}-{record["run_attempt"]}-{identity["push_attempt"]}.identity.json'
        identity_path.write_bytes(files[name])
        observation = identity_path.with_suffix('.observation.json')
        result = subprocess.run([sys.executable, str(Path(proof.__file__)), 'observe-push', '--root', str(root),
                                 '--identity', str(identity_path), '--out', str(observation), '--historical'],
                                capture_output=True, timeout=50)
        if result.returncode:
            raise Refused('prior_original_commit_effect_still_unknown')
        # Bind the sealed public candidate generation to the observed commit's actual blobs.
        commit = identity['expected_commit']
        fetched = subprocess.run(['git', '-C', str(root), 'fetch', '--filter=blob:none', '--no-tags', '--no-write-fetch-head', 'origin', commit],
                                 capture_output=True, timeout=20)
        if fetched.returncode:
            raise Refused('prior_committed_generation_unavailable')
        tree = subprocess.run(['git', '-C', str(root), 'ls-tree', '-r', '-z', commit, '--', 'data/government_revenue', 'site'], capture_output=True, text=True, check=True, timeout=5)
        relatives = set(proof.DEFAULT_CANDIDATE_PATHS) | {proof.DEFAULT_PUBLIC_TWIN}
        for row in tree.stdout.split('\0'):
            if not row:
                continue
            metadata, relative = row.split('\t', 1)
            static = (relative.startswith('site/government-revenue-') or relative.startswith('site/government_revenue')) and Path(relative).suffix in ('.js', '.css', '.html')
            if relative.startswith(('data/government_revenue/', 'site/government-revenue-data/')) or static:
                if metadata.split()[0] == '120000':
                    raise Refused('prior_committed_symlink_not_sealed_generation')
                relatives.add(relative)
        for relative in relatives:
            blob = subprocess.run(['git', '-C', str(root), 'show', f'{commit}:{relative}'], capture_output=True, timeout=5)
            if blob.returncode or digest(blob.stdout) != receipt['outputs'].get(relative):
                raise Refused('prior_candidate_commit_not_sealed_generation')
        results.append({'push_identity': claimed, 'expected_commit': commit,
                        'observation_sha256': digest(observation.read_bytes()), 'disposition': 'original_effect_confirmed'})
    return {'run_id': record['run_id'], 'run_attempt': record['run_attempt'], 'pushes': results}


def preflight(root, out_dir, api, baseline, current):
    if max(parse_time(baseline['scan_created_after']), parse_time(baseline['legacy_effects_reconciled_at'])) > parse_time(current['started_at']):
        raise Refused('baseline_cutover_is_in_future')
    # Discovery is bounded to retained evidence; absence cannot reset an older epoch.
    recent_floor = max(parse_time(baseline['scan_created_after']), parse_time(current['started_at']) - timedelta(days=7)).isoformat()
    retired = {(e['run_id'], e['run_attempt']): e for e in baseline['reconciled_legacy_operations']}
    recent, _ = qualified_records(api, recent_floor, (current['run_id'], current['run_attempt']))
    archives = {}
    checkpoints = []
    for record in sorted(recent, key=lambda r: (r['started_at'], r['job_id']), reverse=True):
        if (record['run_id'], record['run_attempt']) in retired or record.get('publisher_never_started'):
            continue
        if not any(s['name'] == STEP_NAME for s in record['steps']):
            continue
        record['expected_source_closure'] = baseline['source_closure']
        files, artifact = api.archive(record['run_id'], record['run_attempt'])
        load_case(files, record)
        archives[(record['run_id'], record['run_attempt'])] = (files, artifact)
        if CHECKPOINT in files:
            cp = json.loads(files[CHECKPOINT])
            if (cp.get('contract') != 'government_revenue.publisher_preflight.v1' or cp.get('conclusion') != 'passed'
                    or cp.get('baseline_sha256') != digest(proof._canonical(baseline).encode())
                    or cp.get('repository') != REPOSITORY or cp.get('run_id') != record['run_id']
                    or cp.get('run_attempt') != record['run_attempt']
                    or cp.get('covered_before_started_at') != record['started_at']
                    or parse_time(cp['next_created_scan_floor']) > parse_time(record['created_at'])):
                raise Refused('prior_checkpoint_not_qualified')
            checkpoints.append((record, cp, artifact))
            break
    previous = checkpoints[0] if checkpoints else None
    floor = previous[1]['next_created_scan_floor'] if previous else baseline['scan_created_after']
    records, pending = qualified_records(api, floor, (current['run_id'], current['run_attempt']))
    if previous and (previous[0]['run_id'], previous[0]['run_attempt']) not in {(r['run_id'], r['run_attempt']) for r in records}:
        records.append(previous[0])
    checked = []
    covered_before = previous[1]['covered_before_started_at'] if previous else baseline['scan_created_after']
    for record in records:
        if time.monotonic() >= api.deadline:
            raise Refused('bounded_preflight_budget_exhausted')
        key = (record['run_id'], record['run_attempt'])
        if parse_time(record['started_at']) < parse_time(covered_before) and (not previous or key != (previous[0]['run_id'], previous[0]['run_attempt'])):
            continue
        if record.get('publisher_never_started'):
            checked.append({'run_id': key[0], 'run_attempt': key[1], 'job_id': record['job_id'], 'disposition': 'authenticated_publisher_job_skipped_without_steps'})
            continue
        if key in retired:
            if (retired[key]['publisher_job_id'] != record['job_id']
                    or retired[key]['workflow_path'] != record['workflow_path']
                    or retired[key]['publisher_job_name'] != record['publisher_job_name']):
                raise Refused('reviewed_legacy_target_mismatch')
            checked.append({'run_id': key[0], 'run_attempt': key[1], 'explicit_reviewed_disposition': retired[key]})
            continue
        if not any(s['name'] == STEP_NAME for s in record['steps']):
            checked.append(classify_legacy_never_published(api, record, baseline))
            continue
        record['expected_source_closure'] = baseline['source_closure']
        files, artifact = archives.get(key) or api.archive(*key)
        checked.append({**reconcile_record(root, files, record, out_dir), **artifact})
    if time.monotonic() >= api.deadline:
        raise Refused('bounded_preflight_budget_exhausted')
    checkpoint = {'contract': 'government_revenue.publisher_preflight.v1', 'conclusion': 'passed',
                  'repository': REPOSITORY, 'run_id': current['run_id'], 'run_attempt': current['run_attempt'],
                  'baseline_sha256': digest(proof._canonical(baseline).encode()),
                  'covered_before_started_at': current['started_at'],
                  'next_created_scan_floor': min([current['created_at'], *pending]),
                  'previous_checkpoint': previous[2] if previous else None, 'checked_operations': checked,
                  'issuance_authority': False}
    proof._atomic_write(out_dir / CHECKPOINT, proof._canonical(checkpoint) + '\n')
    return checkpoint


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--out-dir', required=True)
    args = parser.parse_args(argv)
    root, out_dir = Path(args.root).resolve(), Path(args.out_dir).resolve()
    if out_dir.is_relative_to(root):
        return 75
    out_dir.mkdir(parents=True, exist_ok=True)
    case = {'contract': 'government_revenue.publisher_run_case.v1', 'repository': os.environ.get('GITHUB_REPOSITORY'),
            'run_id': int(os.environ.get('GITHUB_RUN_ID', '0')), 'run_attempt': int(os.environ.get('GITHUB_RUN_ATTEMPT', '0')),
            'case_written_at': stamp(), 'phase': 'created_before_effect', 'issuance_authority': False}
    proof._atomic_write(out_dir / CASE, proof._canonical(case) + '\n')
    try:
        if case['repository'] != REPOSITORY or not case['run_id'] or case['run_attempt'] != 1:
            raise Refused('current_native_actions_identity_missing')
        case.update({'checkout_commit': proof._head_commit(root), 'source_closure': source_closure(root)})
        case['execution_source_binding'] = source_binding.check_checkout(os.environ, case['checkout_commit'])
        proof._atomic_write(out_dir / CASE, proof._canonical(case) + '\n')
        api = GitHub(os.environ.get('GITHUB_TOKEN'))
        baseline = read_baseline(root)
        run = api.json(f'actions/runs/{case["run_id"]}')
        if (run.get('id') != case['run_id'] or run.get('run_attempt') != case['run_attempt']
                or run['path'] not in {'.github/workflows/' + p for p in FAMILIES}):
            raise Refused('current_workflow_family_not_admitted')
        jobs = api.json(f'actions/runs/{case["run_id"]}/attempts/{case["run_attempt"]}/jobs?per_page=100')['jobs']
        family = Path(run['path']).name
        current = [j for j in jobs if j['name'] == FAMILIES[family] and j['status'] == 'in_progress']
        if len(current) != 1:
            raise Refused('current_publisher_job_not_unique')
        case.update({'job_id': current[0]['id'], 'workflow_path': run['path'], 'started_at': current[0]['started_at'],
                     'created_at': run['created_at'], 'checkout_commit': proof._head_commit(root), 'source_closure': source_closure(root)})
        proof._atomic_write(out_dir / CASE, proof._canonical(case) + '\n')
        preflight(root, out_dir, api, baseline, case)
        case['phase'] = 'preflight_passed_before_effect'
        proof._atomic_write(out_dir / CASE, proof._canonical(case) + '\n')
        print('GovRev prior publisher effects reconciled; no new build/write began in preflight')
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        case['reason'] = str(exc) if isinstance(exc, (Refused, source_binding.BindingRefused)) else 'required_evidence_unavailable_or_unqualified'
        case['phase'] = 'preflight_refused_before_effect'
        proof._atomic_write(out_dir / CASE, proof._canonical(case) + '\n')
        print('::error title=GovRev publication preflight::publication frozen: ' + case['reason'])
        return 75

if __name__ == '__main__':
    sys.exit(main())
