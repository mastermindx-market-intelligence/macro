#!/usr/bin/env python3
"""Read-only admission gate, run from the protected control bundle BEFORE checkout.

CI_PR_ADMISSION_INPUTS is JSON, never shell-expanded candidate input. A prepared
receipt is only an anchor: execution also requires the immutable bound receipt
for this original run/attempt. Binding publication may race runner pickup. One
resolver invocation permits at most 12 comment readbacks, 128 GETs and a single
120-second monotonic deadline (5 seconds between readbacks). HTTP timeouts are
clamped to the remaining deadline, at most 10 seconds. No error/UNKNOWN is retried;
only affirmative absence of a bound record permits another same-attempt read.
The workflow must additionally retain its finite job timeout (at least 3 minutes).
No dispatch, checkout, settlement, check publication or candidate import occurs.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import sys
import time

# The script and its dependencies must be copied from the protected control SHA.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts import merge_on_green as mog
from scripts import ci_proof_admission as admission

DEADLINE_SECONDS = 120
MAX_READBACKS = 12
MAX_REQUESTS = 128
READBACK_INTERVAL = 5
REPOSITORY = "mastermindx-market-intelligence/macro"


class ResolutionError(RuntimeError):
    """Incomplete proof; never a request to retry a workload effect."""


def _positive(value):
    return type(value) is int and value > 0


def _sha(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None


def _integer(value):
    if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]*", value):
        raise ResolutionError("invalid positive identifier")
    return int(value)


def _object(value):
    return value if isinstance(value, dict) else {}


@contextmanager
def _bounded_reads(repo, token, clock, deadline):
    """Scope incumbent HTTP helpers to fixed repository GETs and one deadline.

    This resolver is a standalone, single-threaded process. Restoring globals also
    makes in-process tests safe; no controller execution is run concurrently here.
    """
    request, download, timeout = mog._request, mog._download_semantic_artifact, mog.REQUEST_TIMEOUT_SECONDS
    count = 0
    prefix = f"{mog.GITHUB_API}/repos/{repo}/"

    def call(original, url, supplied_token, *args):
        nonlocal count
        remaining = deadline - clock()
        if (remaining <= 0 or count >= MAX_REQUESTS or supplied_token != token
                or not isinstance(url, str) or not url.startswith(prefix)):
            raise ResolutionError("original resolver deadline/read budget exceeded or unsafe path")
        count += 1
        mog.REQUEST_TIMEOUT_SECONDS = min(10, remaining)
        result = original(*args, url, supplied_token)
        if clock() >= deadline:
            raise ResolutionError("original resolver deadline expired")
        return result

    def get(method, url, supplied_token, *args, **kwargs):
        if method != "GET" or args or kwargs:
            raise ResolutionError("resolver permits read-only fixed-path GETs")
        return call(request, url, supplied_token, method)

    def artifact_download(url, supplied_token):
        return call(download, url, supplied_token)

    mog._request, mog._download_semantic_artifact = get, artifact_download
    try:
        yield
    finally:
        mog._request, mog._download_semantic_artifact = request, download
        mog.REQUEST_TIMEOUT_SECONDS = timeout


def resolve(inputs, *, repository, repository_id, run_id, run_attempt,
            workflow_sha, event_sha, event_name, ref, token,
            clock=time.monotonic, sleep=time.sleep):
    """Return safe checkout outputs after authenticating the original execution.

    Framework identity arguments come from GitHub's workflow context, not inputs.
    A fork is accepted only as a hosted subject: same_repository=false must NEVER
    be used to authorize the persistent trusted-ci executor.
    """
    deadline = clock() + DEADLINE_SECONDS
    required = {"proof_role", "admission_generation", "admission_artifact_id",
                "admission_payload_sha256", "pr_number", "subject_head_sha",
                "tested_base_sha", "tested_merge_sha", "expected_workflow_definition_sha"}
    if (not isinstance(inputs, dict) or set(inputs) - required - {"expected_sha"}
            or not required <= set(inputs) or inputs.get("expected_sha", "") != ""
            or inputs["proof_role"] != "pr_head"
            or not isinstance(inputs["admission_generation"], str)
            or not re.fullmatch(r"[0-9a-f]{12}", inputs["admission_generation"])
            or not isinstance(inputs["admission_payload_sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", inputs["admission_payload_sha256"])
            or any(not _sha(inputs[k]) for k in (
                "subject_head_sha", "tested_base_sha", "tested_merge_sha", "expected_workflow_definition_sha"))
            or repository != REPOSITORY or not all(_positive(x) for x in (repository_id, run_id, run_attempt))
            or not _sha(workflow_sha) or event_sha != workflow_sha
            or inputs["expected_workflow_definition_sha"] != workflow_sha
            or event_name != "workflow_dispatch" or ref != "refs/heads/main"):
        raise ResolutionError("invalid trusted PR dispatch context")
    number = _integer(inputs["pr_number"])
    prepared_id = _integer(inputs["admission_artifact_id"])
    generation = inputs["admission_generation"]
    root = f"{mog.GITHUB_API}/repos/{repository}"
    controls = {workflow_sha}
    cached = {}

    def get(path):
        status, result = mog._request("GET", root + path, token)
        if status != 200 or not isinstance(result, dict):
            raise ResolutionError("required original identity read unavailable")
        return result

    def current_run():
        observed = get(f"/actions/runs/{run_id}")
        if (type(observed.get("id")) is not int or observed["id"] != run_id
                or type(observed.get("run_attempt")) is not int or observed["run_attempt"] != run_attempt
                or observed.get("status") != "in_progress"
                or observed.get("event") != "workflow_dispatch"
                or observed.get("head_branch") != "main" or observed.get("head_sha") != workflow_sha
                or observed.get("path") not in {".github/workflows/ci.yml", ".github/workflows/ci.yml@main",
                    ".github/workflows/ci.yml@refs/heads/main", ".github/workflows/ci.yml@" + workflow_sha}
                or type(_object(observed.get("repository")).get("id")) is not int
                or observed["repository"]["id"] != repository_id):
            raise ResolutionError("current run is not the original active protected PR dispatch")

    def protected(control):
        if not _sha(control):
            raise ResolutionError("invalid controller source")
        if control not in controls:
            compared = get(f"/compare/{control}...{workflow_sha}?per_page=1")
            if (compared.get("status") not in {"identical", "ahead"}
                    or _object(compared.get("base_commit")).get("sha") != control
                    or _object(compared.get("merge_base_commit")).get("sha") != control):
                raise ResolutionError("controller source is not protected workflow ancestry")
            controls.add(control)

    def load(reference):
        if not isinstance(reference, dict):
            raise ResolutionError("malformed admission index reference")
        key = json.dumps(reference, sort_keys=True)
        if key not in cached:
            protected(reference.get("controller_sha"))
            cached[key] = mog.authenticated_admission_from_ref(
                repository, token, reference, repository_id=repository_id,
                protected_controller_sha=reference["controller_sha"])
        return cached[key]

    try:
        with _bounded_reads(repository, token, clock, deadline):
            current_run()
            artifact = get(f"/actions/artifacts/{prepared_id}")
            match = re.fullmatch(r"ci-proof-admission-([1-9][0-9]*)-([1-9][0-9]*)-([0-9a-f]{12})-(?:source-)?prepared",
                                 str(artifact.get("name", "")))
            if match is None or match[3] != generation:
                raise ResolutionError("dispatch lacks exact prepared artifact anchor")
            prepared_ref = {"artifact_id": prepared_id, "controller_run_id": int(match[1]),
                            "controller_attempt": int(match[2]),
                            "controller_sha": _object(artifact.get("workflow_run")).get("head_sha"),
                            "payload_sha256": inputs["admission_payload_sha256"]}
            prepared = load(prepared_ref)
            if (prepared.pr_number != number or prepared.generation != generation
                    or prepared.run_id is not None or prepared.settled):
                raise ResolutionError("prepared admission identity is not unbound original generation")
            admission.validate_execution(prepared, subject_head=inputs["subject_head_sha"],
                base=inputs["tested_base_sha"], merge=inputs["tested_merge_sha"],
                parents=[inputs["tested_base_sha"], inputs["subject_head_sha"]], workflow=workflow_sha)
            bound = None
            for readback in range(MAX_READBACKS):
                current_run()
                comments = mog.fetch_issue_comments(repository, number, token, strict=True)
                if comments is None:
                    raise ResolutionError("admission index unreadable; binding UNKNOWN")
                records = [prepared]
                for comment in comments:
                    body = comment.get("body")
                    if not isinstance(body, str) or not body.startswith(mog.ADMISSION_COMMENT_PREFIX):
                        continue
                    if not mog.admission_index_writer(comment):
                        continue
                    if len(body) > 4096:
                        raise ResolutionError("oversized admission index")
                    reference = json.loads(body[len(mog.ADMISSION_COMMENT_PREFIX):], object_pairs_hook=admission._unique_object)
                    if not isinstance(reference, dict) or not _positive(reference.get("artifact_id")):
                        raise ResolutionError("malformed admission index")
                    indexed = get(f"/actions/artifacts/{reference['artifact_id']}")
                    name = str(indexed.get("name", ""))
                    # Server metadata permits skipping other generations without
                    # treating a comment's generation claim as authenticated.
                    if not re.fullmatch(r"ci-proof-admission-[1-9][0-9]*-[1-9][0-9]*-" + generation + r"-(?:source-)?(prepared|bound)", name):
                        continue
                    if any(reference.get(field) != prepared_ref[field] for field in (
                            "controller_run_id", "controller_attempt", "controller_sha")):
                        raise ResolutionError("generation binding changed its original controller attempt")
                    record = load(reference)
                    if record.generation != generation or record.pr_number != number:
                        raise ResolutionError("admission index disagrees with authenticated identity")
                    records.append(record)
                merged = admission.merge_records(records)
                if len(merged) != 1:
                    raise ResolutionError("ambiguous admitted generation")
                candidate = merged[0]
                if candidate.run_id is not None:
                    if candidate.settled or candidate.run_id != run_id or candidate.run_attempt != run_attempt:
                        raise ResolutionError("bound receipt authorizes another or settled execution")
                    bound = candidate
                    break
                if readback + 1 == MAX_READBACKS or clock() + READBACK_INTERVAL >= deadline:
                    raise ResolutionError("bound receipt incomplete within original resolver deadline")
                sleep(READBACK_INTERVAL)
            if bound is None:
                raise ResolutionError("bound receipt unavailable")
            pull = get(f"/pulls/{number}")
            head, base = _object(pull.get("head")), _object(pull.get("base"))
            head_repo, base_repo = _object(head.get("repo")), _object(base.get("repo"))
            head_id = head_repo.get("id")
            head_name = head_repo.get("full_name")
            if (type(pull.get("number")) is not int or pull["number"] != number or pull.get("state") != "open"
                    or head.get("sha") != bound.head_sha or base.get("ref") != getattr(bound,"target_ref","main")
                    or type(base_repo.get("id")) is not int or base_repo["id"] != repository_id
                    or base_repo.get("full_name") != repository or not _positive(head_id)
                    or not isinstance(head_name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", head_name)
                    or (head_id == repository_id) != (head_name == repository)):
                raise ResolutionError("live PR subject or repository boundary changed")
            commit = get(f"/git/commits/{bound.merge_sha}")
            parents = commit.get("parents")
            if commit.get("sha") != bound.merge_sha or not isinstance(parents, list):
                raise ResolutionError("exact admitted merge object unavailable")
            admission.validate_execution(bound, subject_head=head["sha"], base=bound.base_sha,
                merge=commit["sha"], parents=[_object(p).get("sha") for p in parents], workflow=workflow_sha)
            current_run()
            return {"tested_commit": bound.merge_sha, "subject_head": bound.head_sha,
                    "base": bound.base_sha, "pr_number": str(number),
                    "head_repository_id": str(head_id), "same_repository": str(head_id == repository_id).lower(),
                    "admission_generation": generation, "semantic_role": "pr_head"}
    except ResolutionError:
        raise
    except Exception as exc:
        # Never relay HTTP bodies, URLs, token-bearing exceptions or input JSON.
        raise ResolutionError("admission evidence unreadable or inconsistent; proof incomplete") from exc



def _native_policy_read_url(url):
    """Only the incumbent canonical protected policy source, on the same API.

    The policy adapter revalidates actual branch/blob provenance. This allowlist
    grants no alternate origin, caller-selected source or Administration read.
    All reads still spend the original resolver deadline and request allowance.
    """
    if not isinstance(url, str):
        return False
    prefix = mog.GITHUB_API + '/repos/mastermindx-market-intelligence/Mastermind/'
    if url == prefix + 'branches/master':
        return True
    return re.fullmatch(re.escape(prefix) +
        r'contents/control_plane/github_review_risk_(?:policy|source|dispatch)\.py\?ref=[0-9a-f]{40}', url) is not None


def resolve_native(payload, *, repository, repository_id, run_id, run_attempt,
                   workflow_sha, workflow_ref, event_sha, event_name, ref, token,
                   clock=time.monotonic, sleep=time.sleep, membership_only=False, workflow_file="ci.yml", include_source_branch=False, final_evidence=None):
    """Read only one pre-reserved native original from the incumbent PR ledger.

    Called by the pinned required CI workflow, before any candidate checkout or
    import. Ordinary candidate-sourced merge_group YAML cannot satisfy the
    framework source ref binding. Admission still originates in the incumbent
    protected serialized controller, never in this group runner.
    """
    from scripts import ci_authority as authority
    deadline = clock() + DEADLINE_SECONDS
    if workflow_file not in {'ci.yml', 'fences.yml', 'ci-authority.yml'} or type(membership_only) is not bool:
        raise ResolutionError('unsupported native workflow reader')
    if workflow_file != 'ci.yml' and not membership_only:
        raise ResolutionError('only CI may resolve an execution receipt')
    source_path = '.github/workflows/' + workflow_file
    source_prefix = repository + '/' + source_path + '@'
    source_ref = workflow_ref.removeprefix(source_prefix) if isinstance(workflow_ref,str) and workflow_ref.startswith(source_prefix) else ''
    if (repository != REPOSITORY or event_name != 'merge_group' or not _sha(workflow_sha)
            or not all(_positive(v) for v in (repository_id,run_id,run_attempt))
            or run_attempt != 1 or source_ref not in {'refs/heads/main','refs/heads/'+authority.NATIVE_QUEUE_TARGET}):
        raise ResolutionError('native workflow source is not an installed protected source')
    raw_target=_object(payload.get('merge_group')).get('base_ref') if isinstance(payload,dict) else None
    selected_target=raw_target.removeprefix('refs/heads/') if isinstance(raw_target,str) and raw_target.startswith('refs/heads/') else ''
    if selected_target not in authority.NATIVE_QUEUE_TARGETS:raise ResolutionError('native target is not allowlisted')
    root = f'{mog.GITHUB_API}/repos/{repository}'
    request, download, timeout = mog._request, mog._download_semantic_artifact, mog.REQUEST_TIMEOUT_SECONDS
    calls = 0

    def bounded(method,url,supplied_token,body=None):
        nonlocal calls
        graphql = method=='POST' and url==mog.GITHUB_API+'/graphql' and isinstance(body,dict) and body.get('query') in {authority.NATIVE_QUEUE_QUERY,authority.NATIVE_PR_RELEASE_QUERY}
        policy_read = final_evidence is not None and _native_policy_read_url(url)
        if (supplied_token!=token or not (graphql or method=='GET'
                and (url.startswith(root+'/') or policy_read) and body is None)
                or clock()>=deadline or calls>=MAX_REQUESTS):
            raise ResolutionError('native original resolver budget, deadline or path refused')
        calls += 1
        mog.REQUEST_TIMEOUT_SECONDS=min(10,deadline-clock())
        result=request(method,url,token,body) if body is not None else request(method,url,token)
        if clock()>=deadline:raise ResolutionError('native original resolver expired during read')
        return result

    def bounded_archive(url,supplied_token):
        nonlocal calls
        if supplied_token!=token or not url.startswith(root+'/actions/artifacts/') or calls>=MAX_REQUESTS or clock()>=deadline:
            raise ResolutionError('native original archive boundary refused')
        calls+=1;mog.REQUEST_TIMEOUT_SECONDS=min(10,deadline-clock())
        result=download(url,token)
        if clock()>=deadline:raise ResolutionError('native original archive read expired')
        return result

    def get(path):
        code,result=bounded('GET',root+path,token)
        if code!=200:raise ResolutionError('native original evidence unavailable')
        return result

    source_branch = None
    def membership():
        nonlocal source_branch
        owner,name=repository.split('/')
        code,body=bounded('POST',mog.GITHUB_API+'/graphql',token,dict(query=authority.NATIVE_QUEUE_QUERY,
            variables=dict(owner=owner,name=name,target=selected_target,
                qualifiedRef='refs/heads/'+selected_target)))
        if code!=200 or not isinstance(body,dict) or body.get('errors') or not isinstance(body.get('data'),dict):
            raise ResolutionError('native membership unavailable')
        group = authority.validate_native_queue_snapshot(body['data'],payload,repository,
            execution_sha=event_sha,execution_ref=ref)
        rows=body['data']['repository']['mergeQueue']['entries']['nodes']
        branch=next(row['pullRequest']['headRefName'] for row in rows if row['id']==group['queue_entry_id'])
        if source_branch is not None and branch!=source_branch:
            raise ResolutionError('native source branch changed during original read')
        source_branch=branch
        return group

    def original_run():
        run=get(f'/actions/runs/{run_id}')
        if (not isinstance(run,dict) or type(run.get('id')) is not int or run['id']!=run_id
                or type(run.get('run_attempt')) is not int or run['run_attempt']!=run_attempt
                or run.get('status')!='in_progress' or run.get('event')!='merge_group'
                or run.get('head_sha')!=event_sha or run.get('head_branch')!=ref.removeprefix('refs/heads/')
                or _object(run.get('repository')).get('id')!=repository_id
                or run.get('path') not in {source_path,source_path+'@'+source_ref,source_path+'@'+workflow_sha}):
            raise ResolutionError('native original run identity changed')

    mog._request,mog._download_semantic_artifact=bounded,bounded_archive
    try:
        original_run()
        # Complete effective rule pagination, with the same original 128-read
        # budget; short page only certifies this rules endpoint, not PR census.
        from urllib.parse import quote
        rules=[]
        for page in range(1,11):
            rows=get('/rules/branches/'+quote(selected_target,safe='')+f'?per_page=100&page={page}')
            if not isinstance(rows,list) or len(rows)>100 or any(not isinstance(x,dict) for x in rows):
                raise ResolutionError('native protection read incomplete')
            rules.extend(rows)
            if len(rows)<100:break
        else:raise ResolutionError('native protection inventory bound reached')
        protection=authority.native_protection_contract(rules,repository_id=repository_id,
            protected_source_sha=workflow_sha,protected_source_ref=source_ref,selected_target=selected_target)
        main=get('/branches/main')
        protected_tip=_object(main.get('commit')).get('sha') if isinstance(main,dict) else None
        if not _sha(protected_tip) or (protected_tip!=workflow_sha
                and not mog._github_is_ancestor(repository,token,workflow_sha,protected_tip)):
            raise ResolutionError('native required source has no protected ancestry')
        group=membership()
        if membership_only:
            original_run()
            if membership()!=group:
                raise ResolutionError('native membership changed during original read')
            return dict(group=group,source_branch=source_branch) if include_source_branch else group
        number=group['pr_number']; bound=None
        for readback in range(MAX_READBACKS):
            comments=mog.fetch_issue_comments(repository,number,token,strict=True)
            if comments is None:raise ResolutionError('native admission comments incomplete')
            records,_=mog.pr_admission_history(repository,token,number,comments,
                repository_id=repository_id,protected_controller_sha=protected_tip)
            candidates=[a for a in records if isinstance(a,admission.NativeAdmission)
                and (a.pr_number,a.head_sha,a.base_sha,a.tree_sha,a.workflow_sha)==(
                    number,group['source_head_sha'],group['base_sha'],group['tree_sha'],workflow_sha)
                and not a.settled]
            if len(candidates)!=1:
                raise ResolutionError('native event has no unique original pre-enqueue reservation')
            candidate=candidates[0]
            if candidate.queue_entry_id not in {None,group['queue_entry_id']}:
                raise ResolutionError('native queue entry changed')
            if candidate.run_id is not None:
                if (candidate.run_id,candidate.run_attempt)!=(run_id,run_attempt) or admission.native_execution_identity(candidate)!=group:
                    raise ResolutionError('native receipt belongs to a different original')
                bound=candidate;break
            if readback+1==MAX_READBACKS or clock()+READBACK_INTERVAL>=deadline:
                raise ResolutionError('native bound receipt incomplete within original resolver deadline')
            sleep(READBACK_INTERVAL)
        if bound is None:raise ResolutionError('native original receipt missing')
        if final_evidence is not None:
            from scripts.ci_semantic_proof import load_semantic_evidence
            loaded=load_semantic_evidence(final_evidence,advertised=True,
                expected_run_id=run_id,expected_event='merge_group',expected_role='merge_group',
                expected_workflow='ci',expected_native_group=group,expected_admission_generation=bound.generation)
            authority.native_final_evidence(loaded,admission_record=bound,run_id=run_id,attempt=run_attempt)
            mog.native_current_release(repository,token,group,protection=protection)
        if membership()!=group:raise ResolutionError('native original membership changed')
        original_run()
        return dict(tested_commit=group['group_head_sha'],subject_head=group['source_head_sha'],base=group['base_sha'],
            pr_number=str(number),head_repository_id=str(repository_id),same_repository='true',
            admission_generation=bound.generation,semantic_role='merge_group',
            native_group_json=json.dumps(group,sort_keys=True,separators=(',',':')))
    except ResolutionError:raise
    except Exception as exc:
        raise ResolutionError('native original proof is incomplete') from exc
    finally:
        mog._request,mog._download_semantic_artifact,mog.REQUEST_TIMEOUT_SECONDS=request,download,timeout

def main():
    try:
        context = dict(repository=os.environ.get("GITHUB_REPOSITORY", ""),
            repository_id=_integer(os.environ.get("GITHUB_REPOSITORY_ID", "")),
            run_id=_integer(os.environ.get("GITHUB_RUN_ID", "")),
            run_attempt=_integer(os.environ.get("GITHUB_RUN_ATTEMPT", "")),
            workflow_sha=os.environ.get("GITHUB_WORKFLOW_SHA", ""), event_sha=os.environ.get("GITHUB_SHA", ""),
            event_name=os.environ.get("GITHUB_EVENT_NAME", ""), ref=os.environ.get("GITHUB_REF", ""),
            token=os.environ.get("GITHUB_TOKEN", ""))
        if context["event_name"] == "merge_group":
            event_path = Path(os.environ.get("GITHUB_EVENT_PATH", ""))
            with event_path.open("rb") as stream:
                raw = stream.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ResolutionError("oversized native event")
            payload = json.loads(raw, object_pairs_hook=admission._unique_object)
            outputs = resolve_native(payload, workflow_ref=os.environ.get("GITHUB_WORKFLOW_REF", ""), **context)
        else:
            raw = os.environ.get("CI_PR_ADMISSION_INPUTS", "")
            if len(raw) > 4096:
                raise ResolutionError("oversized dispatch input")
            inputs = json.loads(raw, object_pairs_hook=admission._unique_object)
            outputs = resolve(inputs, **context)
        destination = os.environ.get("GITHUB_OUTPUT")
        if not destination:
            raise ResolutionError("missing workflow output destination")
        with open(destination, "a", encoding="utf-8") as stream:
            for key, value in outputs.items():
                stream.write(f"{key}={value}\n")
        return 0
    except Exception:
        print("::error title=ci-pr-admission::Original admitted PR proof could not be verified; incomplete.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
