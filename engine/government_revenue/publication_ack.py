"""Read-only proposal for same-publisher GRV issuance acknowledgement.

No append, rollback, retraction, evaluation or publication API exists here. This
adapter is not an admitted source/calendar/rights owner. Phase two must reseal
its state projection before publication. Runtime installation remains pending.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from hashlib import sha1, sha256
import base64
import json
import os
import re
import subprocess
from typing import Callable, Mapping, Any

LEDGER_PATH = 'data/government_revenue/candidate_issuance_log.jsonl'
MAX_RESPONSE = 8 * 1024 * 1024
REPOSITORY = 'mastermindx-market-intelligence/macro'
WORKFLOW = '.github/workflows/government-revenue-live.yml'


class AcknowledgementError(ValueError):
    pass


def clock(value: str) -> datetime:
    try:
        if not isinstance(value, str) or len(value) > 64:
            raise ValueError()
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None:
            raise ValueError()
        return result.astimezone(timezone.utc)
    except ValueError as exc:
        raise AcknowledgementError('timezone-aware clock required') from exc


def _hex(value: Any, size: int) -> bool:
    return isinstance(value, str) and len(value) == size and all(c in '0123456789abcdef' for c in value)


def entry_boundary(entry_session: str) -> datetime:
    try:
        if not isinstance(entry_session, str) or len(entry_session) != 10:
            raise ValueError()
        d = date.fromisoformat(entry_session)
        if d.isoformat() != entry_session:
            raise ValueError()
        return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    except ValueError as exc:
        raise AcknowledgementError('registered entry session date required') from exc


def require_remaining_window(*, actual_now: str, entry_session: str,
    proof_budget_seconds: int, push_budget_seconds: int, acknowledgement_budget_seconds: int,
    safety_seconds: int) -> int:
    """Admission refusal before effects: entry UTC midnight is conservative."""
    budgets = (proof_budget_seconds, push_budget_seconds, acknowledgement_budget_seconds, safety_seconds)
    if any(type(v) is not int or v <= 0 for v in budgets):
        raise AcknowledgementError('positive bounded phase-one budgets required')
    remaining = (entry_boundary(entry_session) - clock(actual_now)).total_seconds()
    if remaining <= sum(budgets):
        raise AcknowledgementError('insufficient conservative publication window')
    return int(remaining)


@dataclass(frozen=True)
class OwnerObservation:
    """Bytes from the qualified authenticated owner transport, not caller JSON."""
    status: int
    headers: Mapping[str, str]
    body: bytes


class GitHubOwnerReader:
    """Pinned TLS host through incumbent authenticated gh; read requests only.

    /user must identify the existing qualified publication principal. Actions
    installation-token authentication is NOT silently substituted for this
    principal contract. That owner mode needs its own qualified admission.
    Response headers remain in memory; secrets and CLI error output are omitted.
    """
    def __call__(self, endpoint: str) -> OwnerObservation:
        if not endpoint.startswith('/') or not re.fullmatch(r'/[A-Za-z0-9_./?=&%-]+', endpoint):
            raise AcknowledgementError('invalid owner read endpoint')
        env = dict(os.environ)
        env.pop('GH_DEBUG', None)
        try:
            result = subprocess.run(['gh', 'api', '--hostname', 'github.com', '--method', 'GET',
                '--include', '-H', 'Accept: application/vnd.github+json',
                '-H', 'X-GitHub-Api-Version: 2022-11-28', '-H', 'Cache-Control: no-cache',
                '-H', 'Pragma: no-cache', endpoint],
                env=env, capture_output=True, timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AcknowledgementError('owner read unavailable; reconcile same carrier') from exc
        if result.returncode != 0 or len(result.stdout) > MAX_RESPONSE:
            raise AcknowledgementError('owner read refused or oversized; reconcile same carrier')
        raw = result.stdout.replace(b'\r\n', b'\n')
        header, separator, body = raw.partition(b'\n\n')
        if not separator:
            raise AcknowledgementError('owner response header absent')
        lines = header.decode('ascii', errors='strict').splitlines()
        status_match = re.fullmatch(r'HTTP/[0-9.]+ ([0-9]{3})(?: .*)?', lines[0])
        if not status_match:
            raise AcknowledgementError('owner HTTP status absent')
        headers = {}
        for line in lines[1:]:
            key, delimiter, value = line.partition(':')
            if not delimiter or key.lower() in headers:
                raise AcknowledgementError('owner response header malformed')
            headers[key.lower()] = value.strip()
        return OwnerObservation(int(status_match[1]), headers, body)


def acknowledge_published_prefix(*, read_owner: Callable[[str], OwnerObservation],
    principal_login: str, principal_id: int, repository_id: int, run_id: int,
    run_head_sha: str, published_commit_sha: str, expected_ledger_prefix: bytes,
    entry_session: str, actual_read_completed_at: Callable[[], str],
    source_generation_sha256: str, registration_sha256: str,
    server_clock_allowance_seconds: int = 30) -> dict:
    """Acknowledge an exact nonempty prefix already durable on the same carrier.

    The read caller is the existing serialized publisher. Its source admission,
    fresh issuance preparation and bounded remaining-window check precede this
    operation. This read does not make a local staged row an actual issuance.
    Remote bytes may extend the expected prefix but may never replace it.
    """
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', principal_login):
        raise AcknowledgementError('qualified publication principal required')
    if any(type(v) is not int or v <= 0 for v in (principal_id, repository_id, run_id)):
        raise AcknowledgementError('positive owner repository/run IDs required')
    if not all(_hex(v, 40) for v in (run_head_sha, published_commit_sha)) or not all(_hex(v, 64) for v in (source_generation_sha256, registration_sha256)):
        raise AcknowledgementError('exact source/registration/commit references required')
    if type(server_clock_allowance_seconds) is not int or not 1 <= server_clock_allowance_seconds <= 300:
        raise AcknowledgementError('bounded conservative server-clock allowance required')
    if not isinstance(expected_ledger_prefix, bytes) or not expected_ledger_prefix or not expected_ledger_prefix.endswith(b'\n') or len(expected_ledger_prefix) > MAX_RESPONSE // 2:
        raise AcknowledgementError('nonempty exact whole-line ledger prefix required')
    deadline = entry_boundary(entry_session)
    observations = []

    def observe(endpoint: str) -> dict:
        observation = read_owner(endpoint)
        if not isinstance(observation, OwnerObservation) or observation.status != 200 or len(observation.body) > MAX_RESPONSE:
            raise AcknowledgementError('authenticated owner observation failed')
        headers = {k.lower(): v for k, v in observation.headers.items()}
        try:
            if str(headers.get('age', '0')) != '0':
                raise ValueError()
            server_at = parsedate_to_datetime(headers['date'])
            if server_at.tzinfo is None:
                raise ValueError()
            server_at = server_at.astimezone(timezone.utc)
        except (KeyError, TypeError, ValueError) as exc:
            raise AcknowledgementError('uncached trusted server observation clock required') from exc
        completed = clock(actual_read_completed_at())
        allowance = timedelta(seconds=server_clock_allowance_seconds)
        # Local completion only refuses stale/late responses; server Date supplies
        # the authoritative observation. Both must clear the conservative boundary.
        if server_at + allowance >= deadline or completed + allowance >= deadline or abs(completed - server_at) > allowance:
            raise AcknowledgementError('durable before-entry acknowledgement unavailable')
        try:
            payload = json.loads(observation.body)
        except (ValueError, UnicodeDecodeError) as exc:
            raise AcknowledgementError('owner response is not JSON') from exc
        if not isinstance(payload, dict):
            raise AcknowledgementError('owner response object required')
        observations.append(server_at.isoformat().replace('+00:00', 'Z'))
        return payload

    principal = observe('/user')
    if principal.get('id') != principal_id or type(principal.get('id')) is not int or principal.get('login') != principal_login:
        raise AcknowledgementError('publication principal differs')
    repo = observe('/repos/' + REPOSITORY)
    if repo.get('full_name') != REPOSITORY or type(repo.get('id')) is not int or repo.get('id') != repository_id:
        raise AcknowledgementError('publication repository differs')
    run = observe(f'/repos/{REPOSITORY}/actions/runs/{run_id}')
    if run.get('id') != run_id or type(run.get('id')) is not int or run.get('head_sha') != run_head_sha or run.get('path') != WORKFLOW or (run.get('repository') if isinstance(run.get('repository'), dict) else {}).get('id') != repository_id or (run.get('repository') if isinstance(run.get('repository'), dict) else {}).get('full_name') != REPOSITORY:
        raise AcknowledgementError('publication workflow/run identity differs')
    # A successful phase-one push is while this same serialized run is executing.
    if run.get('status') != 'in_progress' or run.get('event') not in ('schedule', 'workflow_dispatch', 'push'):
        raise AcknowledgementError('current serialized publisher run required')
    commit = observe(f'/repos/{REPOSITORY}/git/commits/{published_commit_sha}')
    if commit.get('sha') != published_commit_sha or not _hex((commit.get('tree') if isinstance(commit.get('tree'), dict) else {}).get('sha'), 40):
        raise AcknowledgementError('published commit identity differs')
    tree_sha = commit['tree']['sha']
    tree = observe(f'/repos/{REPOSITORY}/git/trees/{tree_sha}?recursive=1')
    if tree.get('sha') != tree_sha or tree.get('truncated') is not False or not isinstance(tree.get('tree'), list):
        raise AcknowledgementError('complete published commit tree required')
    entries = [v for v in tree['tree'] if isinstance(v, dict) and v.get('path') == LEDGER_PATH]
    if len(entries) != 1 or entries[0].get('type') != 'blob' or entries[0].get('mode') != '100644' or not _hex(entries[0].get('sha'), 40):
        raise AcknowledgementError('canonical published ledger blob required')
    blob_sha = entries[0]['sha']
    blob = observe(f'/repos/{REPOSITORY}/git/blobs/{blob_sha}')
    if blob.get('sha') != blob_sha or blob.get('encoding') != 'base64' or not isinstance(blob.get('content'), str):
        raise AcknowledgementError('exact published ledger bytes required')
    try:
        raw = base64.b64decode(''.join(blob['content'].split()), validate=True)
    except (ValueError, TypeError) as exc:
        raise AcknowledgementError('published ledger encoding invalid') from exc
    actual_git_sha = sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
    if actual_git_sha != blob_sha or type(blob.get('size')) is not int or blob['size'] != len(raw) or not raw.startswith(expected_ledger_prefix):
        raise AcknowledgementError('published ledger prefix bytes differ')
    ref = observe(f'/repos/{REPOSITORY}/git/ref/heads/main')
    if ref.get('ref') != 'refs/heads/main' or (ref.get('object') if isinstance(ref.get('object'), dict) else {}).get('type') != 'commit' or (ref.get('object') if isinstance(ref.get('object'), dict) else {}).get('sha') != published_commit_sha:
        raise AcknowledgementError('ledger commit is not current canonical publication')
    # This binds exact bytes, not scientific eligibility. The incumbent parser,
    # source owner and issuance preparer supply those separate requirements.
    result = {'contract': 'government_revenue.publication_ack.v1',
        'repository': REPOSITORY, 'repository_id': repository_id,
        'principal': {'login': principal_login, 'id': principal_id},
        'run_id': run_id, 'run_head_sha': run_head_sha, 'workflow': WORKFLOW,
        'published_commit_sha': published_commit_sha, 'tree_sha': tree_sha,
        'ledger_path': LEDGER_PATH, 'ledger_blob_sha': blob_sha,
        'published_ledger_sha256': sha256(raw).hexdigest(),
        'ledger_prefix_sha256': sha256(expected_ledger_prefix).hexdigest(),
        'ledger_prefix_bytes': len(expected_ledger_prefix),
        'ledger_prefix_lines': expected_ledger_prefix.count(b'\n'),
        'source_generation_sha256': source_generation_sha256,
        'registration_sha256': registration_sha256,
        'entry_session': entry_session, 'server_observed_at': max(observations),
        'server_clock_allowance_seconds': server_clock_allowance_seconds,
        'append_count': 0, 'requires_new_final_generation_proof': True}
    result['content_id'] = 'grpa1-' + sha256(json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    return result
