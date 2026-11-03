"""Fixed upload boundaries of the incumbent merge-on-green job.

This is its protected-process adapter, not a second scheduler. All source and
credentials remain on the default-branch controller. GitHub artifacts are the
immutable receipts; local files are only same-job handoff between upload steps.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import merge_on_green as mog
contract = mog.proof_admission


def write_once(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, sort_keys=True, separators=(',', ':')).encode()
    with path.open('xb') as out:
        out.write(payload)
    return hashlib.sha256(payload).hexdigest()


class Stages:
    def __init__(self, repo, read_token, write_token, checks_token, context, directory):
        self.repo, self.read, self.write, self.checks = repo, read_token, write_token, checks_token
        self.context = context
        self.directory = Path(directory)

    def authority(self):
        if not mog._shared_controller_authority(self.repo, self.read, **self.context):
            raise ValueError('not exact protected serialized original controller')

    def save(self, name, data):
        return write_once(self.directory / (name + '.json'), data)

    def load(self, name):
        return json.loads((self.directory / (name + '.json')).read_text(),
                          object_pairs_hook=contract._unique_object)

    def receipt(self, kind, value, suffix):
        schema = {'admission': 'mastermind.ci-proof-admission.v1',
                  'demands': 'mastermind.ci-proof-demands.v1',
                  'checkpoint': 'mastermind.ci-proof-checkpoint.v1'}[kind]
        data = dict(schema=schema, repository_id=self.context['repository_id'],
                    controller_run_id=int(self.context['current_run_id']),
                    controller_run_attempt=self.context['current_run_attempt'])
        data[kind] = value
        digest = write_once(self.directory / suffix / 'ci-proof-admission.json', data)
        self.save(suffix + '-digest', digest)

    def reference(self, suffix, artifact_id):
        if type(artifact_id) is not int or artifact_id <= 0:
            raise ValueError('no original upload artifact identity')
        return dict(artifact_id=artifact_id,
                    controller_run_id=int(self.context['current_run_id']),
                    controller_attempt=self.context['current_run_attempt'],
                    controller_sha=self.context['protected_controller_sha'],
                    payload_sha256=self.load(suffix + '-digest'))

    def initialize_empty_register(self):
        """Only a positively idle legacy register with no owners may migrate."""
        root = f'{mog.GITHUB_API}/repos/{self.repo}'
        url = root + '/labels/' + urllib.parse.quote(mog.REFRESH_LEASE_LABEL, safe='')
        status, label = mog._request('GET', url, self.read)
        if status == 200 and isinstance(label, dict) and str(label.get('description', '')).startswith('a2 '):
            return
        if status != 200 or not isinstance(label, dict) or label.get('description') != mog.REFRESH_LEASE_DESCRIPTION:
            raise ValueError('legacy register missing, occupied or unknown; no migration')
        # Complete state=all associations, not just the open queue. An old m1
        # association is never interpreted as empty because its PR closed.
        query = urllib.parse.urlencode(dict(state='all', labels=mog.REFRESH_LEASE_LABEL, per_page=100))
        code, rows = mog._request('GET', root + '/issues?' + query, self.read)
        if code != 200 or rows != []:
            raise ValueError('legacy owner association remains; no migration')
        code, _ = mog._request('PATCH', url, self.write, {'description': 'a2 idle'})
        if code != 200:
            raise RuntimeError('UNKNOWN original register migration')
        code, observed = mog._request('GET', url, self.read)
        if code != 200 or not isinstance(observed, dict) or observed.get('description') != 'a2 idle':
            raise RuntimeError('UNKNOWN original register migration readback')

    def history(self, pull):
        comments = mog.fetch_issue_comments(self.repo, pull['number'], self.read, strict=True)
        if comments is None:
            raise ValueError('incomplete original PR comments')
        prefixes = (mog.ADMISSION_COMMENT_PREFIX, mog.DEMAND_COMMENT_PREFIX, mog.CHECKPOINT_COMMENT_PREFIX)
        if not any(str(c.get('body', '')).startswith(prefixes) for c in comments):
            if mog.REFRESH_LEASE_LABEL in mog.label_names(pull):
                raise ValueError('associated PR lacks original receipt')
            return [], []
        return mog.pr_admission_history(self.repo, self.read, pull['number'], comments,
            repository_id=self.context['repository_id'],
            protected_controller_sha=self.context['protected_controller_sha'],
            allow_empty=mog.REFRESH_LEASE_LABEL not in mog.label_names(pull))

    def candidate_native_entrypoint(self, pull):
        import base64
        import yaml
        merge = pull.get('merge_commit_sha')
        if not isinstance(merge, str) or not re.fullmatch('[0-9a-f]{40}', merge):
            return None
        root = f'{mog.GITHUB_API}/repos/{self.repo}'
        code, commit = mog._request('GET', root + f'/git/commits/{merge}', self.read)
        if (code != 200 or not isinstance(commit, dict) or commit.get('sha') != merge
                or [p.get('sha') for p in commit.get('parents', [])] !=
                   [(pull.get('base') or {}).get('sha'), (pull.get('head') or {}).get('sha')]):
            return None
        code, data = mog._request('GET', root + '/contents/.github/workflows/ci.yml?ref=' + merge, self.read)
        if (code != 200 or not isinstance(data, dict) or data.get('type') != 'file'
                or data.get('encoding') != 'base64' or type(data.get('size')) is not int
                or not 0 < data['size'] <= 1048576):
            raise ValueError('candidate CI entrypoint unavailable')
        raw = base64.b64decode(''.join(data['content'].split()), validate=True)
        if len(raw) != data['size']:
            raise ValueError('candidate CI entrypoint truncated')
        workflow = yaml.safe_load(raw)
        if not isinstance(workflow, dict):
            raise ValueError('candidate CI entrypoint malformed')
        events = workflow.get('on', workflow.get(True))
        if isinstance(events, str):
            return events == 'pull_request'
        if isinstance(events, (dict, list)):
            return 'pull_request' in events
        raise ValueError('candidate CI entrypoints unknown')

    def demand_kind(self, pull, runs, freshness, native_pr_enabled):
        anchors = mog.proof_anchor_runs(runs)
        ci = [v for k, v in anchors.items() if k in {'ci-plan', 'contract-delta', 'ci-gate'} or k.startswith('ci-pack')]
        if any(r.get('status') != 'completed' for r in ci):
            return None
        if not ci:
            # During foundation installation the original native PR event owns
            # first proof. No race with its indexing gap or duplicate launch.
            return None if native_pr_enabled else 'authored'
        if not mog.is_sweep_candidate(pull):
            return None
        # Refresh only an affirmative current-input invalidator. Red alone,
        # missing evidence and unchanged source do not authorize a rerun.
        stale, _reason = freshness.stale_for(pull, runs)
        return 'refresh' if stale is True else None

    def prepare(self, *, native_pr_enabled, freshness):
        self.authority()
        self.initialize_empty_register()
        workload = mog.shared_proof_workload(self.repo, self.read,
            repository_id=self.context['repository_id'],
            protected_controller_sha=self.context['protected_controller_sha'])
        if not workload.complete:
            raise ValueError('incomplete shared workload')
        budget = mog.SweepBudget(self.read)
        if not budget.preflight()[0]:
            raise ValueError('insufficient original budget for complete demand census')
        pulls = mog.open_pulls(self.repo, self.read)
        demands, changed = [], []
        now = datetime.now(timezone.utc).isoformat()
        for index, pull in enumerate(pulls):
            if not budget.may_continue(index)[0]:
                raise ValueError('incomplete demand census at budget boundary; no selection')
            if (pull.get('state') != 'open' or (pull.get('base') or {}).get('ref') != 'main'):
                continue
            head = (pull.get('head') or {}).get('sha')
            if not isinstance(head, str) or not re.fullmatch('[0-9a-f]{40}', head):
                raise ValueError('incomplete open PR identity')
            own = [a for a in workload.admissions if a.pr_number == pull['number']]
            if any(not a.settled for a in own):
                continue
            records, prior = self.history(pull)
            runs = mog.head_check_runs(self.repo, head, self.read)
            # The candidate owns the pull_request entrypoint. During the
            # staged cutover, protected main may still have native PR events
            # while this exact candidate has removed them (or the reverse).
            candidate_native = self.candidate_native_entrypoint(pull)
            if candidate_native is None:
                continue  # no exact merge object: not currently eligible
            kind = self.demand_kind(pull, runs, freshness, candidate_native)
            if kind is None:
                continue
            if any(a.head_sha == head and a.base_sha == self.context['protected_controller_sha']
                   for a in own):
                continue  # terminal UNKNOWN/red is served, never a replay request
            if kind == 'authored' and any(a.head_sha == head for a in own):
                continue  # missing completion cannot mint another source attempt
            pending = contract.pending_demand_for_pr(prior, records, pull['number'], head)
            demand = pending or contract.Demand(pull['number'], head, kind, now, secrets.token_hex(6))
            demands.append(demand)
            if demand not in prior:
                changed.append(demand)
        # Selection cannot happen from a truncated or partially indexed census.
        contract.ordered_demands(demands)
        self.save('census', dict(context=self.context, pulls=pulls, demands=[asdict(d) for d in demands]))
        if changed:
            self.receipt('demands', [asdict(d) for d in changed], 'demands')
        return dict(changed=bool(changed), count=len(demands))

    def index(self, number, prefix, reference):
        body = prefix + json.dumps(reference, sort_keys=True, separators=(',', ':'))
        root = f'{mog.GITHUB_API}/repos/{self.repo}'
        code, result = mog._request('POST', root + f'/issues/{number}/comments', self.read, {'body': body})
        if code != 201 or not isinstance(result, dict) or type(result.get('id')) is not int or result.get('body') != body:
            raise RuntimeError('UNKNOWN original receipt index')
        code, observed = mog._request('GET', root + f"/issues/comments/{result['id']}", self.read)
        if code != 200 or observed.get('id') != result['id'] or observed.get('body') != body:
            raise RuntimeError('UNKNOWN original receipt index readback')
        code, _ = mog._request('POST', root + f'/issues/{number}/labels', self.write, {'labels': [mog.REFRESH_LEASE_LABEL]})
        if code != 200:
            raise RuntimeError('UNKNOWN original receipt association')
        code, observed = mog._request('GET', root + f'/issues/{number}/labels', self.read)
        if code != 200 or not isinstance(observed, list) or mog.REFRESH_LEASE_LABEL not in {x.get('name') for x in observed if isinstance(x, dict)}:
            raise RuntimeError('UNKNOWN original receipt association readback')

    def reserve(self, demand_artifact_id=None):
        self.authority()
        census = self.load('census')
        if census['context'] != self.context:
            raise ValueError('foreign controller census')
        if (self.directory / 'demands-digest.json').exists():
            ref = self.reference('demands', demand_artifact_id)
            changed = mog.authenticated_demands_from_ref(self.repo, self.read, ref,
                repository_id=self.context['repository_id'], protected_controller_sha=self.context['protected_controller_sha'])
            for d in changed:
                self.index(d.pr_number, mog.DEMAND_COMMENT_PREFIX, ref)
        demands = contract.ordered_demands(contract.Demand(**d) for d in census['demands'])
        for demand in demands:
            result = mog.reserve_shared_admission(self.repo, self.read, self.write, demand, **self.context)
            if result.disposition == 'ineligible':
                continue  # ineligible/conflicted demand owns no reserved slot
            if result.disposition == 'held':
                return dict(prepared=False, disposition='held', detail=result.detail)
            self.save('reservation', dict(disposition=result.disposition, detail=result.detail))
            if result.disposition != 'prepared':
                raise RuntimeError('UNKNOWN original reservation; no next candidate')
            self.receipt('admission', asdict(result.admission), 'prepared')
            # Same original complete-history producer seals compaction before
            # dispatch. Its index lands only after immutable artifact readback.
            checkpoint = mog.prepare_shared_checkpoint(self.repo, self.read, demand.pr_number, **self.context)
            self.receipt('checkpoint', asdict(checkpoint), 'checkpoint')
            return dict(prepared=True, generation=result.admission.generation, pr_number=demand.pr_number)
        return dict(prepared=False)

    def dispatch(self, prepared_artifact_id, checkpoint_artifact_id):
        self.authority()
        checkpoint_ref = self.reference('checkpoint', checkpoint_artifact_id)
        checkpoint = mog.authenticated_checkpoint_from_ref(self.repo, self.read, checkpoint_ref,
            repository_id=self.context['repository_id'], protected_controller_sha=self.context['protected_controller_sha'])
        self.index(checkpoint.pr_number, mog.CHECKPOINT_COMMENT_PREFIX, checkpoint_ref)
        ref = self.reference('prepared', prepared_artifact_id)
        result = mog.publish_prepared_shared_admission(self.repo, self.read, self.write, ref, **self.context)
        if result.disposition != 'indexed':
            raise RuntimeError('original preparation did not settle: ' + result.disposition)
        result = mog.dispatch_admitted_pr_proof(self.repo, self.read, self.write, ref, **self.context)
        self.save('dispatch', dict(disposition=result.disposition, detail=result.detail))
        if result.disposition != 'bound':
            raise RuntimeError('original dispatch did not bind: ' + result.disposition)
        self.receipt('admission', asdict(result.admission), 'bound')
        return dict(bound=True, generation=result.admission.generation)

    def finalize(self, bound_artifact_id):
        self.authority()
        ref = self.reference('bound', bound_artifact_id)
        result = mog.finalize_shared_admission(self.repo, self.read, self.write, ref, **self.context)
        self.save('finalized', dict(disposition=result.disposition, detail=result.detail))
        if result.disposition != 'finalized':
            raise RuntimeError('original finalization did not settle: ' + result.disposition)
        return dict(finalized=True)

    def complete(self, run_id=None, attempt=None):
        """Reconcile current original terminal records, including coalesced wakes.

        The incumbent singleton pointer is retained THROUGH check publication.
        After a missing/ambiguous check response, the next invocation may only
        read the exact triplet; it cannot fill missing members or re-POST.
        """
        self.authority()
        inventory = mog.shared_admission_inventory(self.repo, self.read)
        if not inventory.complete or inventory.mode != 'shared':
            return dict(disposition='not_shared')
        root = f'{mog.GITHUB_API}/repos/{self.repo}'
        register_url = root + '/labels/' + urllib.parse.quote(mog.REFRESH_LEASE_LABEL, safe='')
        outcomes = []
        for issue in inventory.issues:
            if issue.get('state') != 'open':
                continue
            comments = mog.fetch_issue_comments(self.repo, issue['number'], self.read, strict=True)
            if comments is None:
                raise ValueError('incomplete completion inventory')
            catalog = {}
            records, _ = mog.pr_admission_history(self.repo, self.read, issue['number'], comments,
                repository_id=self.context['repository_id'],
                protected_controller_sha=self.context['protected_controller_sha'], reference_catalog=catalog)
            code, pull = mog._request('GET', root + f"/pulls/{issue['number']}", self.read)
            if code != 200 or not isinstance(pull, dict):
                raise ValueError('current completion subject unavailable')
            for a in records:
                if a.run_id is None or a.head_sha != (pull.get('head') or {}).get('sha'):
                    continue
                ref = catalog.get((a.generation, a.run_id))
                if ref is None:
                    continue  # covered settled history is never reopened
                marker = mog.admitted_subject_external_id(ref)
                checks = mog._admitted_check_inventory(mog._admitted_reads(self.repo, self.read)[0], a.head_sha)
                matching = [c for c in checks if c.get('external_id') == marker]
                if {c.get('name') for c in matching} == set(mog.ADMITTED_SUBJECT_CHECK_NAMES):
                    # Authenticate before clearing a prior UNKNOWN pointer; for
                    # already completed publication this is a read, no new POST.
                    if inventory.launch != (a.pr_number, a.generation):
                        continue
                if matching and {c.get('name') for c in matching} != set(mog.ADMITTED_SUBJECT_CHECK_NAMES):
                    return dict(disposition='unknown', detail='partial original publication; no retry')
                # Never acquire a global completion pointer for an obsolete
                # original generation. Validate every advertised later binding
                # before deciding; check text/order alone grants no credit.
                original_binding = None
                others = {c.get('external_id') for c in checks if c.get('name') in mog.ADMITTED_SUBJECT_CHECK_NAMES
                          and isinstance(c.get('external_id'), str)
                          and c['external_id'].startswith(mog.ADMITTED_SUBJECT_CHECK_PREFIX)
                          and c['external_id'] != marker}
                superseded = False
                for other in others:
                    if original_binding is None:
                        original_binding = mog._admitted_completion_binding(self.repo, self.read, ref,
                            expected_run_id=a.run_id, expected_run_attempt=a.run_attempt,
                            protected_controller_sha=self.context['protected_controller_sha'])
                    later = mog._admitted_completion_binding(self.repo, self.read,
                        mog._admitted_subject_reference(other), expected_subject_head=a.head_sha,
                        protected_controller_sha=self.context['protected_controller_sha'])
                    superseded |= mog._admitted_run_order(later) > mog._admitted_run_order(original_binding)
                if superseded:
                    continue
                observed = mog._read_admitted_run(self.repo, self.read, a, self.context['repository_id'])
                if observed.status != 'completed':
                    continue
                description = f'a2 p={a.pr_number} g={a.generation} s=completing'
                code, register = mog._request('GET', register_url, self.read)
                if code != 200 or not isinstance(register, dict):
                    raise ValueError('completion custody unavailable')
                continuing = register.get('description') == description
                if register.get('description') not in {'a2 idle', description}:
                    return dict(disposition='held', detail='original launch or completion owns pointer')
                if continuing:
                    try:
                        loaded = mog.admitted_semantic_evidence_for_head(self.repo, a.head_sha, self.read, check_runs=matching)
                        if loaded.evidence.get('run_id') != a.run_id:
                            raise ValueError('different generation')
                    except Exception:
                        return dict(disposition='unknown', detail='original completion unsettled; no retry')
                    result = dict(disposition='already_published')
                else:
                    # Preflight full original evidence BEFORE acquiring custody.
                    try:
                        mog.admitted_completion_proof(self.repo, self.read, ref,
                            expected_run_id=a.run_id, expected_run_attempt=a.run_attempt,
                            protected_controller_sha=self.context['protected_controller_sha'])
                    except Exception:
                        outcomes.append('held')  # no intent/effect: independent originals may proceed
                        continue
                    code, _ = mog._request('PATCH', register_url, self.write, {'description': description})
                    if code != 200:
                        return dict(disposition='unknown', detail='completion intent write unsettled')
                    code, register = mog._request('GET', register_url, self.read)
                    if code != 200 or register.get('description') != description:
                        return dict(disposition='unknown', detail='completion intent readback unsettled')
                    result = mog.publish_admitted_subject_checks(self.repo, self.read, self.checks, ref,
                        expected_run_id=a.run_id, expected_run_attempt=a.run_attempt,
                        protected_controller_sha=self.context['protected_controller_sha'])
                if result['disposition'] not in {'published', 'already_published'}:
                    return result  # pointer deliberately retained, no compensating clear
                code, register = mog._request('GET', register_url, self.read)
                if code != 200 or register.get('description') != description:
                    return dict(disposition='unknown', detail='completion custody changed')
                code, _ = mog._request('PATCH', register_url, self.write, {'description': 'a2 idle'})
                if code != 200:
                    return dict(disposition='unknown', detail='completion finalization unsettled')
                code, register = mog._request('GET', register_url, self.read)
                if code != 200 or register.get('description') != 'a2 idle':
                    return dict(disposition='unknown', detail='completion finalization readback unsettled')
                outcomes.append(result['disposition'])
        return dict(disposition='reconciled', count=sum(x != 'held' for x in outcomes), held=outcomes.count('held'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['prepare', 'reserve', 'dispatch', 'finalize', 'complete'])
    args = parser.parse_args()
    context = dict(repository_id=int(os.environ['GITHUB_REPOSITORY_ID']),
                   protected_controller_sha=os.environ['GITHUB_SHA'],
                   current_run_id=os.environ['GITHUB_RUN_ID'],
                   current_run_attempt=int(os.environ['GITHUB_RUN_ATTEMPT']))
    stages = Stages(os.environ['GH_REPO'], os.environ['READ_TOKEN'], os.environ['MERGE_TOKEN'],
                    os.environ.get('CHECKS_TOKEN', ''), context, os.environ['CI_ADMISSION_STAGE_DIR'])
    if args.stage == 'prepare':
        import yaml
        workflow = yaml.safe_load((Path(__file__).resolve().parents[1] / '.github/workflows/ci.yml').read_text())
        triggers = workflow.get('on', workflow.get(True, {}))
        result = stages.prepare(native_pr_enabled='pull_request' in triggers,
            freshness=mog.ProofFreshness.build(stages.repo, stages.read))
    elif args.stage == 'reserve':
        result = stages.reserve(int(os.environ['ARTIFACT_ID']) if os.environ.get('ARTIFACT_ID') else None)
    elif args.stage == 'dispatch':
        result = stages.dispatch(int(os.environ['ARTIFACT_ID']), int(os.environ['CHECKPOINT_ARTIFACT_ID']))
    elif args.stage == 'finalize':
        result = stages.finalize(int(os.environ['ARTIFACT_ID']))
    else:
        result = stages.complete()
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            for key, value in result.items():
                if isinstance(value, (bool, int, str)) and '\n' not in str(value):
                    output.write(f'{key}={str(value).lower() if isinstance(value, bool) else value}\n')
    print(json.dumps(result, default=str, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
