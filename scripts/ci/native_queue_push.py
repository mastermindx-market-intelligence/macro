"""Canonical producer adapter: PR intent, original origin, actual landing.

This is a publisher, not a queue controller. Only the incumbent MOG may admit,
reserve or enqueue. The only HTTP writes here create a same-repository PR and
explicitly request its label. No request can merge, update or enqueue a PR.
Stage success is distinct from publication; ordinary publish returns zero only
after protected landing and complete original projection readback.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from scripts.ci.native_publication import (
    ABSENT, ExpectedOutput, ExpectedPublication, ObservedOutput,
    ObservedPublication, PublicationOutcome, PublicationValidationError, validate_publication,
)
from scripts.ci.native_publication_origin import (
    MAX_DOCUMENT_BYTES, decode_origin, encode_origin, producer_origin_artifact_name,
    producer_origin_pointer,
)

LEGACY, PENDING, UNKNOWN, REFUSED = 80, 77, 75, 76
REPOSITORY = 'mastermindx-market-intelligence/macro'
LABEL = 'merge-on-green'
GUARD_PATHS = (
    'scripts/ci_authority.py', 'scripts/ci_authority_paths.py', 'scripts/ci_admission_stages.py',
    'scripts/ci_native_review_policy.py', 'scripts/ci_proof_admission.py',
    'scripts/merge_on_green.py', '.github/workflows/ci.yml',
    '.github/workflows/fences.yml', '.github/workflows/ci-authority.yml',
    '.github/workflows/trusted-ci-executor.yml', '.github/workflows/merge-on-green.yml',
    'scripts/ci/qledger_publication.py', 'engine/__init__.py',
    'engine/qledger_store.py', 'engine/qledger_store_protocol.py', 'engine/qledger_store_sources.py',
)


class PublicationHeld(ValueError):
    """A named refusal, never a Git/HTTP error containing credentials."""


class EffectUnknown(PublicationHeld):
    pass


class AuthorizationRefused(PublicationHeld):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def sha(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{40}', value):
        raise PublicationHeld('immutable_git_identity_missing')
    return value


def positive(value):
    if type(value) is not int or value <= 0:
        raise PublicationHeld('positive_server_identity_missing')
    return value


def git(root, *args):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                            timeout=30, env={**os.environ, 'GIT_TERMINAL_PROMPT': '0',
                                'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_NO_LAZY_FETCH': '1'})
    if result.returncode:
        raise PublicationHeld('bounded_git_operation_failed')
    return result.stdout


def repository_for(root):
    fetch = git(root, 'remote', 'get-url', '--all', 'origin').decode().splitlines()
    push = git(root, 'remote', 'get-url', '--push', '--all', 'origin').decode().splitlines()
    if len(fetch) != 1 or fetch != push:
        raise PublicationHeld('single_unchanged_origin_required')
    match = re.fullmatch(r'(?:https://github\.com/|git@github\.com:)([^/]+/[^/]+?)(?:\.git)?', fetch[0])
    if not match or match[1] != REPOSITORY:
        raise PublicationHeld('publisher_origin_not_admitted')
    return match[1]


def github_origin(root):
    rows = git(root, 'remote', 'get-url', '--push', '--all', 'origin').decode().splitlines()
    if len(rows) != 1:
        raise PublicationHeld('single_push_origin_required')
    return rows[0].startswith('git@github.com:') or urllib.parse.urlsplit(rows[0]).hostname == 'github.com'


def destination(root, arguments):
    """Resolve one ordinary refspec; nonmain routes never acquire API authority."""
    args = list(arguments)
    forced = any(x.startswith('+') or x in ('--force', '-f') for x in args)
    args = [x for x in args if x not in ('--porcelain', '--force', '-f')]
    if len(args) == 3 and args[:2] == ['origin', '--delete']:
        if args[2].removeprefix('refs/heads/') not in ('main', 'codex/merge-queue-pilot'):
            return None
        raise PublicationHeld('protected_target_deletion_not_publication')
    if any(x.startswith('-') for x in args) or len(args) > 2:
        raise PublicationHeld('push_arguments_ambiguous')
    if len(args) == 2:
        if args[0] != 'origin' or args[1].count(':') != 1:
            raise PublicationHeld('single_origin_refspec_required')
        source, target = args[1].removeprefix('+').split(':')
    elif not args or args == ['origin']:
        branch = git(root, 'symbolic-ref', '--short', 'HEAD').decode().strip()
        remote = git(root, 'config', '--get', 'branch.' + branch + '.remote').decode().strip()
        target = git(root, 'config', '--get', 'branch.' + branch + '.merge').decode().strip()
        if remote != 'origin':
            raise PublicationHeld('tracking_origin_ambiguous')
        source = 'HEAD'
    else:
        raise PublicationHeld('push_arguments_ambiguous')
    target = target.removeprefix('refs/heads/')
    if target not in ('main', 'codex/merge-queue-pilot'):
        return None
    if forced:
        raise PublicationHeld('forced_protected_push_not_supported')
    if not source:
        raise PublicationHeld('target_deletion_not_publication')
    return target, sha(git(root, 'rev-parse', source + '^{commit}').decode().strip())


class GitHub:
    """Allowlisted original credential transport; errors never retain bodies."""
    def __init__(self, root, deadline=0):
        self.repo = repository_for(root)
        self.deadline = deadline
        if os.environ.get('NATIVE_PUBLICATION_TOKEN_ORIGIN') == 'GITHUB_TOKEN':
            # An explicit protected publishing-step reference to the SAME
            # checkout GITHUB_TOKEN, not a fallback from the render credential.
            token = os.environ.get('GITHUB_TOKEN')
            if not token:
                raise PublicationHeld('configured_app_rest_token_missing')
            self.authorization = 'Bearer ' + token
            return
        result = subprocess.run(['git', '-C', str(root), 'config', '--get',
                                 'http.https://github.com/.extraheader'], capture_output=True)
        header = result.stdout.decode().strip() if result.returncode == 0 else ''
        if header:
            key, separator, value = header.partition(':')
            if key.lower() != 'authorization' or not separator or '\n' in header or '\r' in header:
                raise PublicationHeld('configured_authorization_header_invalid')
            self.authorization = value.strip()
        elif os.environ.get('NATIVE_PUBLICATION_TOKEN_ORIGIN') == 'ADMIN_GH_TOKEN':
            raise PublicationHeld('configured_render_authorization_header_missing')
        elif os.environ.get('GITHUB_TOKEN'):
            self.authorization = 'Bearer ' + os.environ['GITHUB_TOKEN']
        else:
            raise PublicationHeld('configured_publication_credential_missing')

    def request(self, method, path, body=None):
        if not path.startswith('/') or path.startswith('//'):
            raise PublicationHeld('endpoint_not_admitted')
        allowed = method == 'GET' and path == '/'
        allowed = allowed or (method == 'GET' and re.fullmatch(
            r'/(?:rules/branches/[^?]+|git/(?:commits|trees|ref/heads)/[^?]+|'
            r'commits/[^?]+|compare/[^?]+|pulls(?:/\d+)?|issues/\d+/labels)(?:\?.*)?', path))
        allowed = allowed or (method == 'POST' and (path == '/pulls' or re.fullmatch(r'/issues/\d+/labels', path)))
        if not allowed:
            raise PublicationHeld('endpoint_not_admitted')
        if self.deadline and time.time() >= self.deadline:
            raise PublicationHeld('original_publication_budget_expired')
        request = urllib.request.Request('https://api.github.com/repos/' + self.repo + ('' if path == '/' else path),
            data=None if body is None else canonical(body), method=method,
            headers={'Authorization': self.authorization, 'Accept': 'application/vnd.github+json',
                     'Content-Type': 'application/json', 'X-GitHub-Api-Version': '2022-11-28'})
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                raise PublicationHeld('unexpected_api_redirect')
        try:
            timeout = min(20, self.deadline - time.time()) if self.deadline else 20
            if timeout <= 0:
                raise PublicationHeld('original_publication_budget_expired')
            with urllib.request.build_opener(NoRedirect).open(request, timeout=timeout) as response:
                raw = response.read(8 * 1024 * 1024 + 1)
                if len(raw) > 8 * 1024 * 1024:
                    raise PublicationHeld('bounded_api_response_exceeded')
                return json.loads(raw)
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                raise AuthorizationRefused(f'http_{error.code}_{method}_' + path.partition('?')[0]) from None
            if method == 'POST':
                raise EffectUnknown('original_write_not_confirmed') from None
            if error.code == 404 and path.startswith('/git/ref/heads/'):
                return None
            raise PublicationHeld(f'api_read_http_{error.code}_' + path.partition('?')[0]) from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            if method == 'POST':
                raise EffectUnknown('original_write_not_confirmed') from None
            raise PublicationHeld('required_api_read_unavailable') from None


def tree(api, commit, paths):
    """Resolve only requested paths through complete, nonrecursive tree rows.

    A large unrelated data/site subtree cannot truncate controller or output
    identity. Immutable tree objects are cached only within this original client.
    Blob payloads are never downloaded.
    """
    row = api.request('GET', '/git/commits/' + sha(commit))
    if row.get('sha') != commit:
        raise PublicationHeld('server_commit_identity_changed')
    tree_sha = sha((row.get('tree') or {}).get('sha'))
    if not hasattr(api, '_publication_tree_cache'):
        api._publication_tree_cache = {}
    cache = api._publication_tree_cache
    def children(identity):
        if identity not in cache:
            result = api.request('GET', '/git/trees/' + sha(identity))
            entries = result.get('tree')
            if (result.get('sha') != identity or result.get('truncated') is not False
                    or not isinstance(entries, list) or len(entries) > 100000
                    or any(not isinstance(x, dict) for x in entries)):
                raise PublicationHeld('complete_bounded_tree_readback_required')
            names = [x.get('path') for x in entries]
            if (any(not isinstance(p, str) or '/' in p or not p or p in ('.', '..') for p in names)
                    or len(set(names)) != len(names)):
                raise PublicationHeld('tree_paths_ambiguous')
            modes = {'blob': {'100644', '100755', '120000'},
                     'tree': {'040000'}, 'commit': {'160000'}}
            for entry in entries:
                if entry.get('mode') not in modes.get(entry.get('type'), set()):
                    raise PublicationHeld('tree_entry_type_mode_unqualified')
                sha(entry.get('sha'))
            cache[identity] = {x['path']: x for x in entries}
        return cache[identity]
    found = {}
    for path in paths:
        pieces = path.split('/')
        current = tree_sha
        for index, piece in enumerate(pieces):
            entry = children(current).get(piece)
            if entry is None:
                break  # Complete parent listing proves this path absent.
            if index == len(pieces) - 1:
                found[path] = {**entry, 'path': path}
            elif entry.get('type') == 'tree':
                current = sha(entry.get('sha'))
            else:
                break
    return found, tree_sha


def protection(api, root, repository_id, target, *, code_root=None):
    code_root = Path(code_root) if code_root is not None else Path(__file__).resolve().parents[2]
    rows = []
    for page in range(1, 11):
        part = api.request('GET', '/rules/branches/' + urllib.parse.quote(target, safe='') + f'?per_page=100&page={page}')
        if not isinstance(part, list) or len(part) > 100 or any(not isinstance(x, dict) for x in part):
            raise PublicationHeld('complete_effective_rules_required')
        rows.extend(part)
        if len(part) < 100:
            break
    else:
        raise PublicationHeld('effective_rules_bound_exceeded')
    if not any(x.get('type') == 'merge_queue' for x in rows):
        return None
    required = {'.github/workflows/' + x + '.yml' for x in ('ci', 'fences', 'ci-authority')}
    bindings = [x for rule in rows if rule.get('type') == 'workflows'
                for x in (rule.get('parameters') or {}).get('workflows', [])
                if isinstance(x, dict) and x.get('path') in required]
    sources = {x.get('sha') for x in bindings}
    if len(sources) != 1:
        raise PublicationHeld('required_workflow_source_ambiguous')
    source = sha(next(iter(sources)))
    main = sha(api.request('GET', '/commits/main').get('sha'))
    if source != main:
        comparison = api.request('GET', '/compare/' + source + '...' + main)
        if comparison.get('status') not in ('ahead', 'identical'):
            raise PublicationHeld('required_source_not_protected_ancestry')
    trusted, _ = tree(api, source, GUARD_PATHS)
    installed, _ = tree(api, main, GUARD_PATHS)
    for path in GUARD_PATHS:
        expected = trusted.get(path)
        if not expected or expected.get('type') != 'blob' or installed.get(path) != expected:
            raise PublicationHeld('installed_controller_source_not_bound')
        local = code_root / path
        if (local.is_symlink() or not local.is_file() or expected.get('mode') not in ('100644', '100755')
                or bool(local.stat().st_mode & 0o111) != (expected['mode'] == '100755')):
            raise PublicationHeld('local_controller_file_mode_not_bound')
        content = local.read_bytes()
        oid = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
        if expected.get('sha') != oid:
            raise PublicationHeld('local_controller_contract_not_bound')
    # Qualify immutable local/protected bytes BEFORE importing/calling the
    # supplier, and reject an unrelated cached module/PYTHONPATH shadow.
    from scripts import ci_authority as authority
    if Path(authority.__file__).resolve() != (code_root / 'scripts/ci_authority.py').resolve():
        raise PublicationHeld('loaded_authority_source_not_bound')
    contract = authority.native_protection_contract(rows, repository_id=repository_id,
        protected_source_sha=source, selected_target=target)
    if (not isinstance(contract, dict) or contract.get('target_ref') != target
            or contract.get('protected_source_sha') != source
            or contract.get('protected_source_ref') != 'refs/heads/main'
            or contract.get('required_workflows') != sorted(required)):
        raise PublicationHeld('normalized_target_source_contract_mismatch')
    return contract


def projection(root, head):
    parents = git(root, 'rev-list', '--parents', '-n', '1', sha(head)).decode().split()
    if len(parents) != 2:
        raise PublicationHeld('single_generated_commit_parent_required')
    raw = git(root, 'diff-tree', '--no-commit-id', '-r', '--raw', '-z', '--no-renames', parents[1], head)
    fields = raw.split(b'\0')
    outputs = []
    for index in range(0, len(fields) - 1, 2):
        metadata, path = fields[index].decode().split(), os.fsdecode(fields[index + 1])
        if len(metadata) != 5:
            raise PublicationHeld('projection_diff_unavailable')
        mode, oid = metadata[1], metadata[3]
        outputs.append(ExpectedOutput(path, ABSENT if mode == '000000' else mode,
                                      ABSENT if mode == '000000' else oid))
    if not outputs:
        raise PublicationHeld('empty_candidate_projection')
    return tuple(sorted(outputs, key=lambda x: x.path))


def projection_digest(outputs):
    return hashlib.sha256(canonical([{'path': x.path, 'mode': 'ABSENT' if x.mode is ABSENT else x.mode,
        'blob_sha': 'ABSENT' if x.blob_sha is ABSENT else x.blob_sha} for x in outputs])).hexdigest()


def exact_pull(pull, *, repository_id, head, target, number=None):
    if (not isinstance(pull, dict) or (number is not None and pull.get('number') != number)
            or (pull.get('head') or {}).get('sha') != head
            or (pull.get('base') or {}).get('ref') != target
            or any(type(((pull.get(k) or {}).get('repo') or {}).get('id')) is not int
                   or pull[k]['repo']['id'] != repository_id
                   or pull[k]['repo'].get('full_name') != REPOSITORY for k in ('head', 'base'))):
        raise PublicationHeld('original_pr_head_target_repository_changed')
    positive(pull.get('number'))
    return pull


def request_and_verify_intent(api, pull, *, repository_id, head, target):
    """Explicit adoption even when already labelled, then exact server readback."""
    number = positive(pull.get('number'))
    exact_pull(pull, repository_id=repository_id, head=head, target=target, number=number)
    if pull.get('state') != 'open' or pull.get('draft') is not False or pull.get('merged') is True:
        raise PublicationHeld('open_non_draft_original_required')
    api.request('POST', f'/issues/{number}/labels', {'labels': [LABEL]})
    current = api.request('GET', f'/pulls/{number}')
    exact_pull(current, repository_id=repository_id, head=head, target=target, number=number)
    if (current.get('state') != 'open' or current.get('draft') is not False
            or current.get('merged') is True or LABEL not in {
                x.get('name') for x in current.get('labels', []) if isinstance(x, dict)}):
        raise EffectUnknown('original_queue_intent_readback_not_confirmed')
    if current.get('user') != pull.get('user') or current.get('body') != pull.get('body'):
        raise EffectUnknown('original_queue_intent_subject_changed')
    return current


def publication(api, root, origin):
    """Read-only original settlement; no repair, rebase, label or second intent."""
    head, target = sha(origin['published_source_head']), origin['selected_target']
    repository_id = positive(origin['_repository_id'])
    original_protection = protection(api, root, repository_id, target)
    if original_protection is None:
        raise PublicationHeld('native_protection_no_longer_present')
    pull = exact_pull(api.request('GET', f"/pulls/{origin['pr_number']}"),
        repository_id=repository_id, head=head, target=target, number=origin['pr_number'])
    locator = dict(run_id=origin['producer_run_id'], run_attempt=origin['producer_run_attempt'],
        job=origin['publishing_job'], step=origin['publishing_step'], generation=origin['original_generation'])
    body = pull.get('body')
    marker = intent_pointer(origin['credential_origin'],locator)
    prefix = '<!-- mastermind-native-publication-' + ('origin' if origin['credential_origin']=='GITHUB_TOKEN' else 'intent') + ':v1 '
    if not isinstance(body, str) or body.count(marker) != 1 or body.count(prefix) != 1:
        raise PublicationHeld('original_intent_pointer_changed')
    if pull.get('user') != {'id': origin['pr_creation_user_id'], 'login': origin['pr_creation_login']}:
        user = pull.get('user') or {}
        if user.get('id') != origin['pr_creation_user_id'] or user.get('login') != origin['pr_creation_login']:
            raise PublicationHeld('original_pr_creator_changed')
    if pull.get('merged') is not True:
        if pull.get('state') != 'open':
            raise PublicationHeld('original_pr_closed_unmerged')
        return PENDING, None
    merge = sha(pull.get('merge_commit_sha'))
    observed = sha((api.request('GET', '/git/ref/heads/' + urllib.parse.quote(target, safe='')).get('object') or {}).get('sha'))
    ancestry = merge == observed
    if not ancestry:
        ancestry = api.request('GET', '/compare/' + merge + '...' + observed).get('status') in ('ahead', 'identical')
    expected = projection(root, head)
    if projection_digest(expected) != origin['projection_sha256']:
        raise PublicationHeld('original_projection_identity_changed')
    target_tree, _ = tree(api, observed, [item.path for item in expected])
    readback = []
    for item in expected:
        row = target_tree.get(item.path)
        if row is None:
            readback.append(ObservedOutput(item.path, ABSENT, ABSENT))
        elif row.get('type') == 'blob':
            readback.append(ObservedOutput(item.path, row.get('mode'), row.get('sha')))
        else:
            raise PublicationHeld('publication_path_not_a_blob')
    owner, name = REPOSITORY.split('/')
    receipt = validate_publication(ExpectedPublication(owner, name, 'refs/heads/' + target,
        origin['pr_number'], head, expected), ObservedPublication(owner, name, 'refs/heads/' + target,
        origin['pr_number'], head, 'closed', True, merge, observed, ancestry, tuple(readback), True))
    if receipt.outcome is not PublicationOutcome.PUBLISHED:
        raise PublicationHeld('original_publication_superseded')
    if protection(api, root, repository_id, target) != original_protection:
        raise PublicationHeld('native_protection_changed_during_readback')
    return 0, {'source_head': head, 'merge_sha': merge, 'observed_target_sha': observed,
               'projection_sha256': origin['projection_sha256'], 'pr_number': origin['pr_number']}


def producer_identity(head, digest, *, require_staging_step=True,publishing_step=None):
    """Closed producer source tuples; each also needs the trusted core join."""
    credential=os.environ.get('NATIVE_PUBLICATION_TOKEN_ORIGIN')
    if credential=='GITHUB_TOKEN':
        producers = {'shock': '.github/workflows/commodity-sentinel.yml',
                     'acquire': '.github/workflows/fms-acquire.yml',
                     'render': '.github/workflows/public-render.yml',
                     'cortex': '.github/workflows/daily.yml',
                     'collect': '.github/workflows/daily.yml',
                     'causal': '.github/workflows/daily.yml',
                     'capital_structure': '.github/workflows/daily.yml',
                     'collect_tail': '.github/workflows/daily.yml',
                     'factor_series': '.github/workflows/daily.yml',
                     'factor_panel': '.github/workflows/daily.yml',
                     'oracle_offrender': '.github/workflows/daily.yml',
                     'tech_lab_offrender': '.github/workflows/daily.yml',
                     'standout_audit_us': '.github/workflows/daily.yml',
                     'us_scan_tier': '.github/workflows/daily.yml',
                     'us_prophet_ledgers': '.github/workflows/daily.yml',
                     'stock_briefs': '.github/workflows/daily.yml',
                     'active_build_map': '.github/workflows/daily.yml',
                     'ledger_heartbeat': '.github/workflows/daily.yml',
                     'engine-render': '.github/workflows/engine-render.yml'}
        step='native_publication_stage'
    elif credential=='ADMIN_GH_TOKEN':
        producers={'render':'.github/workflows/render.yml'}
        step='native_publication'
    else:raise PublicationHeld('producer_original_credential_not_bound')
    job = os.environ.get('GITHUB_JOB')
    workflow = producers.get(job)
    allowed_steps={step}
    if credential=='GITHUB_TOKEN' and job=='collect':
        allowed_steps={'native_publication_stage','native_publication_salvage_stage'}
    if credential=='GITHUB_TOKEN' and job=='engine':
        allowed_steps={'native_publication_stage','native_publication_leader_stage',
            'native_publication_prophet_stage','native_publication_shadow_stage',
            'native_publication_core_stage','native_publication_chronicle_stage'}
    if credential=='GITHUB_TOKEN' and job=='causal':
        allowed_steps={'native_publication_stage','native_publication_foundry_stage'}
    if credential=='GITHUB_TOKEN' and job=='asia':
        allowed_steps={'native_publication_stage','native_publication_engine_stage'}
    step=os.environ.get('NATIVE_PUBLICATION_PUBLISHING_STEP') if require_staging_step else (publishing_step or step)
    if (os.environ.get('GITHUB_REPOSITORY') != REPOSITORY
            or os.environ.get('GITHUB_REF') != 'refs/heads/main'
            or workflow is None
            or step not in allowed_steps
            or os.environ.get('GITHUB_WORKFLOW_REF') != REPOSITORY + '/' + workflow + '@refs/heads/main'):
        raise PublicationHeld('producer_original_source_not_allowlisted')
    run = positive(int(os.environ.get('GITHUB_RUN_ID', '0')))
    attempt = positive(int(os.environ.get('GITHUB_RUN_ATTEMPT', '0')))
    workflow_sha = sha(os.environ.get('GITHUB_WORKFLOW_SHA'))
    generation = hashlib.sha256(canonical([REPOSITORY, run, attempt, job, step, head, digest])).hexdigest()[:12]
    locator = dict(run_id=run, run_attempt=attempt, job=job,
                   step=step, generation=generation)
    return locator, workflow, workflow_sha


def intent_pointer(credential,locator):
    if credential=='GITHUB_TOKEN':return producer_origin_pointer(**locator)
    if credential!='ADMIN_GH_TOKEN':raise PublicationHeld('producer_original_credential_not_bound')
    # Lookup only. This local settlement marker is NOT producer-origin evidence,
    # first-proof admission, an App event or a protected release authorization.
    return '<!-- mastermind-native-publication-intent:v1 '+canonical(locator).decode()+' -->'


def stage(api, root, target, head, repository_id, *, source_ref=None):
    """Create/reconcile ONE source-bound PR and verify explicit original intent."""
    outputs = projection(root, head)
    digest = projection_digest(outputs)
    locator, workflow, workflow_sha = producer_identity(head, digest)
    credential=os.environ.get('NATIVE_PUBLICATION_TOKEN_ORIGIN')
    marker = intent_pointer(credential,locator)
    # Exclusive original local namespace precedes every candidate/intent write.
    # Retain it on any uncertain return; no automatic second stage may adopt it.
    directory = Path(os.environ['RUNNER_TEMP']) / ('native-publication-' + locator['generation'])
    directory.mkdir(mode=0o700)
    branch = 'native-publication/' + target.replace('/', '-') + '/' + head
    query = urllib.parse.urlencode({'state': 'all', 'head': REPOSITORY.split('/')[0] + ':' + branch,
                                  'base': target, 'per_page': 100})
    candidates = api.request('GET', '/pulls?' + query)
    if not isinstance(candidates, list) or len(candidates) >= 100:
        raise PublicationHeld('complete_original_pr_lookup_required')
    if len(candidates) > 1:
        raise EffectUnknown('original_pr_identity_ambiguous')
    if candidates:
        pull = exact_pull(candidates[0], repository_id=repository_id, head=head, target=target)
        if not isinstance(pull.get('body'), str) or pull['body'].count(marker) != 1:
            raise PublicationHeld('existing_intent_belongs_to_another_original')
    else:
        ref = api.request('GET', '/git/ref/heads/' + urllib.parse.quote(branch, safe=''))
        if ref is not None:
            if (ref.get('object') or {}).get('sha') != head:
                raise PublicationHeld('existing_staging_source_changed')
        else:
            # This is a staging-branch push ONLY. No force or main fallback.
            try:
                remaining = getattr(api, 'deadline', 0)
                remaining = min(45, remaining - time.time()) if remaining else 45
                if remaining <= 0:
                    raise PublicationHeld('original_publication_budget_expired')
                source_ref=source_ref or head
                if git(root,'rev-parse',source_ref+'^{commit}').decode().strip()!=head:
                    raise PublicationHeld('original_staging_source_changed')
                result = subprocess.run(['git', '-C', str(root), 'push', '--porcelain', 'origin',
                                         source_ref + ':refs/heads/' + branch], capture_output=True, timeout=remaining)
            except (OSError, subprocess.TimeoutExpired):
                raise EffectUnknown('original_staging_push_unconfirmed') from None
            if result.returncode:
                if re.search(rb'GH00[16]:|GH013:|permission denied|permission to .* denied',
                             result.stdout + result.stderr, re.I):
                    raise PublicationHeld('original_staging_push_refused')
                raise EffectUnknown('original_staging_push_unconfirmed')
            readback=api.request('GET','/git/ref/heads/'+urllib.parse.quote(branch,safe=''))
            if ((readback or {}).get('object') or {}).get('sha')!=head:
                raise EffectUnknown('original_staging_push_readback_unconfirmed')
            if git(root,'rev-parse',source_ref+'^{commit}').decode().strip()!=head:
                raise EffectUnknown('original_staging_source_changed_after_push')
        pull = api.request('POST', '/pulls', {'title': 'Publish ' + locator['job'] + ' generation ' + locator['generation'],
            'head': branch, 'base': target, 'body': marker + '\n\nOriginal generated source: ' + head +
            '\nPending publication; only the protected incumbent controller may admit and release.'})
        pull = exact_pull(pull, repository_id=repository_id, head=head, target=target)
    current = request_and_verify_intent(api, pull, repository_id=repository_id, head=head, target=target)
    server_commit = api.request('GET', '/git/commits/' + head)
    candidate_tree = sha((server_commit.get('tree') or {}).get('sha'))
    if server_commit.get('sha') != head or candidate_tree != git(root, 'rev-parse', head + '^{tree}').decode().strip():
        raise EffectUnknown('original_published_candidate_tree_not_confirmed')
    user = current.get('user') or {}
    origin = dict(producer_run_id=locator['run_id'], producer_run_attempt=locator['run_attempt'],
        workflow_path=workflow, workflow_ref=REPOSITORY + '/' + workflow + '@refs/heads/main',
        workflow_sha=workflow_sha, publishing_job=locator['job'], publishing_step=locator['step'],
        credential_origin=credential, pr_number=positive(current['number']), published_source_head=head,
        selected_target=target, original_generation=locator['generation'], candidate_tree=candidate_tree,
        projection_sha256=digest, pr_creation_user_id=positive(user.get('id')), pr_creation_login=user.get('login'))
    envelope = dict(schema='mastermind.ci-proof-producer-origin.v1', repository_id=repository_id,
                    producer_origin=origin)
    # Codec validation is not authority. Only the successful exact request/readback
    # above precedes this official-upload input; no Admission is produced here.
    if credential=='GITHUB_TOKEN':
        raw = encode_origin(envelope, repository_id=repository_id, repository_full_name=REPOSITORY)
        path = directory / 'ci-proof-admission.json'
    else:
        # SAME original private namespace, no upload/registry. Validate all
        # existing codec shapes using a temporary syntax-only credential value;
        # never export this as GITHUB_TOKEN origin or authenticated admission.
        syntax=dict(envelope,producer_origin=dict(origin,credential_origin='GITHUB_TOKEN'))
        encode_origin(syntax,repository_id=repository_id,repository_full_name=REPOSITORY)
        envelope['schema']='mastermind.native-publication-local.v1'
        raw=canonical(envelope)
        path=directory/'publication.json'
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
        if credential=='GITHUB_TOKEN':
            output.write('native_origin_name=' + producer_origin_artifact_name(**locator) + '\n')
            output.write('native_origin_path=' + str(path) + '\n')
        output.write('native_code_root=' + str(Path(__file__).resolve().parents[2]) + '\n')
    return path


def settle(api, root, path, deadline, *, clock=time.time, sleep=time.sleep, on_published=None):
    if clock() >= deadline:
        return PENDING
    path = Path(path)
    namespace = path.parent
    if (path.name not in ('ci-proof-admission.json','publication.json') or namespace.is_symlink()
            or not re.fullmatch('native-publication-[0-9a-f]{12}', namespace.name)
            or namespace.parent.resolve() != Path(os.environ['RUNNER_TEMP']).resolve()):
        raise PublicationHeld('original_private_record_required')
    directory = namespace.stat()
    if directory.st_uid != os.getuid() or stat.S_IMODE(directory.st_mode) != 0o700:
        raise PublicationHeld('original_record_namespace_changed')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as stream:
        metadata = os.fstat(stream.fileno())
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode)!=0o600
                or metadata.st_nlink != 1 or metadata.st_size > MAX_DOCUMENT_BYTES):
            raise PublicationHeld('original_record_identity_invalid')
        raw = stream.read(MAX_DOCUMENT_BYTES + 1)
    repository = api.request('GET', '/')
    repository_id = positive(repository.get('id'))
    if repository.get('full_name') != REPOSITORY:
        raise PublicationHeld('original_repository_changed')
    if path.name=='ci-proof-admission.json':
        envelope = decode_origin(raw, repository_id=repository_id, repository_full_name=REPOSITORY)
    else:
        def pairs(rows):
            result={}
            for key,value in rows:
                if key in result:raise PublicationHeld('duplicate_local_publication_field')
                result[key]=value
            return result
        envelope=json.loads(raw,object_pairs_hook=pairs)
        if (envelope.get('schema')!='mastermind.native-publication-local.v1'
                or envelope.get('producer_origin',{}).get('credential_origin')!='ADMIN_GH_TOKEN'):
            raise PublicationHeld('original_render_local_record_required')
        syntax=dict(envelope,schema='mastermind.ci-proof-producer-origin.v1',
            producer_origin=dict(envelope['producer_origin'],credential_origin='GITHUB_TOKEN'))
        decode_origin(canonical(syntax),repository_id=repository_id,repository_full_name=REPOSITORY)
    origin = dict(envelope['producer_origin'], _repository_id=repository_id)
    if (str(origin['producer_run_id']) != os.environ.get('GITHUB_RUN_ID')
            or str(origin['producer_run_attempt']) != os.environ.get('GITHUB_RUN_ATTEMPT')):
        raise PublicationHeld('settlement_original_run_attempt_changed')
    locator, workflow, workflow_sha = producer_identity(origin['published_source_head'], origin['projection_sha256'],
        require_staging_step=False,publishing_step=origin['publishing_step'])
    if (origin['original_generation'] != locator['generation']
            or origin['workflow_path'] != workflow or origin['workflow_sha'] != workflow_sha
            or origin['publishing_job'] != locator['job'] or origin['publishing_step'] != locator['step']
            or origin['credential_origin'] != os.environ.get('NATIVE_PUBLICATION_TOKEN_ORIGIN')
            or namespace.name != 'native-publication-' + locator['generation']):
        raise PublicationHeld('settlement_original_source_generation_changed')
    while True:
        if clock() >= deadline:
            return PENDING
        status, result = publication(api, root, origin)
        if status == 0:
            if on_published is not None:
                on_published(result)
            print(json.dumps(result, sort_keys=True))
            return 0
        if clock() >= deadline:
            return PENDING
        sleep(min(15, max(0, deadline - clock())))


def prepare_publication(root, arguments, deadline):
    """Select one native stage or affirmative legacy route; no fallback on error."""
    if not github_origin(root):
        return LEGACY, None
    resolved = destination(root, arguments)
    if resolved is None:
        return LEGACY, None
    target, head = resolved
    api = GitHub(root, deadline)
    repo = api.request('GET', '/')
    if repo.get('full_name') != REPOSITORY:
        raise PublicationHeld('repository_identity_mismatch')
    repository_id = positive(repo.get('id'))
    if protection(api, root, repository_id, target) is None:
        return LEGACY, None
    if type(deadline) not in (int,float) or not math.isfinite(deadline) or deadline<=time.time():
        raise PublicationHeld('original_publication_budget_expired')
    if os.environ.get('NATIVE_PUBLICATION_EXPECT_OFF')=='1':
        raise PublicationHeld('native_mode_changed_after_legacy_selection')
    arguments=list(arguments)
    source_ref=arguments[-1].split(':')[0] if len(arguments)==2 and ':' in arguments[-1] else 'HEAD'
    return PENDING, stage(api, root, target, head, repository_id,source_ref=source_ref)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('publish', 'settle'))
    parser.add_argument('--root', default='.')
    parser.add_argument('--push-arg', action='append', default=[])
    parser.add_argument('--record')
    parser.add_argument('--deadline', type=float, default=0)
    parser.add_argument('--write-output',action='store_true',
        help='emit actual protected merge source only AFTER original settlement')
    args = parser.parse_args(argv)
    try:
        root = Path(args.root).resolve()
        if args.command == 'publish':
            status, record = prepare_publication(root, args.push_arg, args.deadline)
            if status==PENDING and os.environ.get('NATIVE_PUBLICATION_TOKEN_ORIGIN')=='ADMIN_GH_TOKEN':
                return settle(GitHub(root,args.deadline),root,record,args.deadline)
            return status
        if not args.record or args.deadline <= 0:
            raise PublicationHeld('original_record_and_budget_required')
        def published_outputs(receipt):
            with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
                output.write('source_sha='+sha(receipt['merge_sha'])+'\npublished=true\n')
        return settle(GitHub(root, args.deadline), root, args.record, args.deadline,
                      on_published=published_outputs if args.write_output else None)
    except EffectUnknown as error:
        print('::error::original native publication effect remains unknown: ' + str(error), file=sys.stderr)
        return UNKNOWN
    except PublicationHeld as error:
        print('::error::native publication held: ' + str(error), file=sys.stderr)
        return REFUSED
    except (PublicationHeld, PublicationValidationError, OSError, ValueError, ImportError,
            KeyError, TypeError, AttributeError, subprocess.SubprocessError):
        print('::error::native publication held; no direct fallback or second intent', file=sys.stderr)
        return REFUSED


if __name__ == '__main__':
    raise SystemExit(main())
