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
            match = re.fullmatch(r"ci-proof-admission-([1-9][0-9]*)-([1-9][0-9]*)-([0-9a-f]{12})-prepared",
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
                    if len(body) > 4096:
                        raise ResolutionError("oversized admission index")
                    reference = json.loads(body[len(mog.ADMISSION_COMMENT_PREFIX):], object_pairs_hook=admission._unique_object)
                    if not isinstance(reference, dict) or not _positive(reference.get("artifact_id")):
                        raise ResolutionError("malformed admission index")
                    indexed = get(f"/actions/artifacts/{reference['artifact_id']}")
                    name = str(indexed.get("name", ""))
                    # Server metadata permits skipping other generations without
                    # treating a comment's generation claim as authenticated.
                    if not re.fullmatch(r"ci-proof-admission-[1-9][0-9]*-[1-9][0-9]*-" + generation + r"-(prepared|bound)", name):
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
                    or head.get("sha") != bound.head_sha or base.get("ref") != "main"
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


def main():
    try:
        raw = os.environ.get("CI_PR_ADMISSION_INPUTS", "")
        if len(raw) > 4096:
            raise ResolutionError("oversized dispatch input")
        inputs = json.loads(raw, object_pairs_hook=admission._unique_object)
        outputs = resolve(inputs, repository=os.environ.get("GITHUB_REPOSITORY", ""),
            repository_id=_integer(os.environ.get("GITHUB_REPOSITORY_ID", "")),
            run_id=_integer(os.environ.get("GITHUB_RUN_ID", "")),
            run_attempt=_integer(os.environ.get("GITHUB_RUN_ATTEMPT", "")),
            workflow_sha=os.environ.get("GITHUB_WORKFLOW_SHA", ""), event_sha=os.environ.get("GITHUB_SHA", ""),
            event_name=os.environ.get("GITHUB_EVENT_NAME", ""), ref=os.environ.get("GITHUB_REF", ""),
            token=os.environ.get("GITHUB_TOKEN", ""))
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
