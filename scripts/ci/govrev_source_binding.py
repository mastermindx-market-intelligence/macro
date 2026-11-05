"""Bind the existing publisher to its native event or settled caller commit.

This module selects immutable source only. It neither authorizes publication nor
observes, retries, or retires an original operation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess

REPOSITORY = "mastermindx-market-intelligence/macro"
PUBLISHER = "government-revenue-live.yml"
CALLERS = {"daily.yml", "fms-acquire.yml"}


class BindingRefused(ValueError):
    pass


def commit_sha(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise BindingRefused("immutable_source_commit_required")
    return value


def select_source(env):
    if env.get("GITHUB_REPOSITORY") != REPOSITORY or env.get("GITHUB_REF") != "refs/heads/main":
        raise BindingRefused("source_caller_repository_or_ref_not_admitted")
    event_sha = commit_sha(env.get("GITHUB_SHA"))
    prefix = REPOSITORY + "/.github/workflows/"
    workflow_ref = env.get("GITHUB_WORKFLOW_REF", "")
    admitted = {prefix + name + "@refs/heads/main": name for name in CALLERS | {PUBLISHER}}
    workflow = admitted.get(workflow_ref)
    if workflow is None:
        raise BindingRefused("source_caller_workflow_not_admitted")
    caller_source = env.get("GOVREV_CALL_SOURCE_SHA", "")
    if workflow == PUBLISHER:
        if caller_source:
            raise BindingRefused("direct_event_cannot_override_native_source")
        source_sha, kind = event_sha, "native_event"
    else:
        # github context belongs to the caller. Its initial SHA predates the
        # collection/persistence push and cannot stand in for this output.
        source_sha, kind = commit_sha(caller_source), "settled_caller_output"
    return {"source_sha": source_sha, "kind": kind, "event_sha": event_sha,
            "caller_workflow_ref": workflow_ref, "repository": REPOSITORY}


def check_checkout(env, actual_head):
    binding = select_source(env)
    if commit_sha(actual_head) != binding["source_sha"]:
        raise BindingRefused("execution_checkout_source_mismatch")
    return binding


def bind_checkout(root, env):
    """Bind an exact detached DATA source to this job's fresh local branch.

    GitHub's immutable SHA checkout is detached. Never rename/move an incumbent
    main or accept a dispatch branch merely to satisfy push_on_main_ok. The
    selected original source must be in the existing origin/main ancestry.
    This makes no remote write, publication intent or admission receipt.
    """
    run=env.get('GITHUB_RUN_ID','');attempt=env.get('GITHUB_RUN_ATTEMPT','')
    if not re.fullmatch('[1-9][0-9]{0,19}',run) or attempt!='1':
        raise BindingRefused('original_source_job_identity_required')
    from scripts.ci.native_queue_push import repository_for
    if repository_for(root)!=REPOSITORY:
        raise BindingRefused('source_origin_repository_changed')
    def git(*args,check=True):
        result=subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True,
            timeout=20,env={**os.environ,'GIT_NO_REPLACE_OBJECTS':'1','GIT_NO_LAZY_FETCH':'1','GIT_TERMINAL_PROMPT':'0'})
        if check and result.returncode:
            raise BindingRefused('selected_source_git_evidence_unqualified')
        return result
    selected=check_checkout(env,git('rev-parse','HEAD').stdout.strip())['source_sha']
    if git('status','--porcelain','--untracked-files=all').stdout.strip():
        raise BindingRefused('selected_source_checkout_not_clean')
    current=git('symbolic-ref','--short','-q','HEAD',check=False)
    if current.returncode==0 and current.stdout.strip()!='main':
        raise BindingRefused('selected_source_is_another_owned_branch')
    git('fetch','--no-tags','--no-write-fetch-head','origin',
        '+refs/heads/main:refs/remotes/origin/main')
    git('merge-base','--is-ancestor',selected,'refs/remotes/origin/main')
    if (git('rev-parse','HEAD').stdout.strip()!=selected
            or git('status','--porcelain','--untracked-files=all').stdout.strip()):
        raise BindingRefused('selected_source_checkout_changed')
    branch='_govrev_source_'+run+'_'+attempt
    # -c refuses any existing branch; no force, reset, adopted writer or replay.
    git('switch','-c',branch,selected)
    if git('symbolic-ref','--short','HEAD').stdout.strip()!=branch or git('rev-parse','HEAD').stdout.strip()!=selected:
        raise BindingRefused('selected_source_branch_readback_unqualified')
    return {'source_sha':selected,'source_branch':branch}


def settled_fms_source(receipt):
    if (not isinstance(receipt, dict) or receipt.get("contract") != "fms.acquisition_persistence.v1"
            or receipt.get("state") != "ORIGINAL_EFFECT_CONFIRMED"
            or receipt.get("target_ref") != "refs/heads/main"
            or not isinstance(receipt.get("attempts"), list) or not receipt["attempts"]):
        raise BindingRefused("fms_source_effect_not_confirmed")
    attempt = receipt["attempts"][-1]
    if isinstance(attempt,dict) and attempt.get('state')=='native_published':
        publication=receipt.get('native_publication')
        if (not isinstance(publication,dict)
                or publication.get('source_head')!=attempt.get('expected_commit')
                or publication.get('source_head')!=receipt.get('candidate')
                or type(publication.get('pr_number')) is not int or publication['pr_number']<=0
                or not isinstance(publication.get('projection_sha256'),str)
                or not re.fullmatch('[0-9a-f]{64}',publication['projection_sha256'])):
            raise BindingRefused('fms_native_publication_not_confirmed')
        commit_sha(attempt.get('observed_commit'))
        commit_sha(publication.get('observed_target_sha'))
        # Native SQUASH does not retain acquisition ancestry. The producer
        # validated the full original generation/source closure at this actual
        # protected merge, separately from a later target observation.
        return commit_sha(publication.get('merge_sha'))
    if not isinstance(attempt, dict) or attempt.get("state") not in {"acknowledged", "effect_unknown"}:
        raise BindingRefused("fms_source_effect_not_confirmed")
    commit_sha(attempt.get("observed_commit"))
    # The persistence helper already confirmed this exact candidate is an
    # ancestor of observed_commit. HEAD stays at the pre-rebase acquisition.
    return commit_sha(attempt.get("expected_commit"))


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument("--fms-receipt", type=Path)
    mode.add_argument("--bind-checkout", action="store_true")
    args = parser.parse_args()
    try:
        if args.bind_checkout:
            bound=bind_checkout(Path.cwd(),os.environ)
            with Path(os.environ['GITHUB_ENV']).open('a',encoding='utf-8') as envfile:
                envfile.write('PUSH_MAIN_BRANCHES='+bound['source_branch']+'\n')
            source=bound['source_sha']
        else:
            source = (settled_fms_source(json.loads(args.fms_receipt.read_text()))
                  if args.fms_receipt else select_source(os.environ)["source_sha"])
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
            output.write("source_sha=" + source + "\n")
        return 0
    except (OSError, ValueError, KeyError, TypeError,subprocess.SubprocessError):
        print("::error title=GovRev source binding::immutable source binding refused")
        return 75


if __name__ == "__main__":
    raise SystemExit(main())
