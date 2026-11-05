"""Bind the existing publisher to its native event or settled caller commit.

This module selects immutable source only. It neither authorizes publication nor
observes, retries, or retires an original operation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re

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


def settled_fms_source(receipt):
    if (not isinstance(receipt, dict) or receipt.get("contract") != "fms.acquisition_persistence.v1"
            or receipt.get("state") != "ORIGINAL_EFFECT_CONFIRMED"
            or receipt.get("target_ref") != "refs/heads/main"
            or not isinstance(receipt.get("attempts"), list) or not receipt["attempts"]):
        raise BindingRefused("fms_source_effect_not_confirmed")
    attempt = receipt["attempts"][-1]
    if not isinstance(attempt, dict) or attempt.get("state") not in {"acknowledged", "effect_unknown"}:
        raise BindingRefused("fms_source_effect_not_confirmed")
    commit_sha(attempt.get("observed_commit"))
    # The persistence helper already confirmed this exact candidate is an
    # ancestor of observed_commit. HEAD stays at the pre-rebase acquisition.
    return commit_sha(attempt.get("expected_commit"))


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fms-receipt", type=Path)
    args = parser.parse_args()
    try:
        source = (settled_fms_source(json.loads(args.fms_receipt.read_text()))
                  if args.fms_receipt else select_source(os.environ)["source_sha"])
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
            output.write("source_sha=" + source + "\n")
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        print("::error title=GovRev source binding::immutable source binding refused")
        return 75


if __name__ == "__main__":
    raise SystemExit(main())
