#!/usr/bin/env python3
"""Resolve a trusted-main or same-repository PR candidate for CI canaries.

Three candidate kinds, every one an exact SHA that cannot move:

* ``trusted-main`` — ``--pr-number 0``: the dispatched main commit itself.
* ``same-repository-pr-merge`` — an OPEN same-repository PR targeting main:
  GitHub's synthetic ``refs/pull/N/merge`` commit, frozen against the API's
  ``merge_commit_sha`` and the PR head.
* ``same-repository-pr-merged`` — a same-repository PR targeting main that was
  MERGED after its ci.yml run began (2026-09-16, PR #7203 run 35073695150):
  the real merge commit on main.  ci.yml fences merged-close events into their
  own concurrency group so a proof run survives a fast merge; refusing the
  closed PR here made that fencing pointless — the hosted plan died, every
  pack was skipped, ``ci-gate`` reported "semantic proof is blocking", and the
  merged head carried a red that ``gh run rerun --failed`` reproduced forever.
  The merge commit is the exact tree that landed, so it is a better candidate
  than the synthetic merge, not a weaker one.

Closed-unmerged, cross-repository, and non-main-targeting PRs are refused in
every state.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.request
from pathlib import Path

GITHUB_API = "https://api.github.com"


class ResolutionError(RuntimeError):
    pass


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], text=True, capture_output=True, check=False)
    if result.returncode:
        raise ResolutionError(
            f"git {' '.join(args)} failed ({result.returncode}): "
            f"{(result.stderr or result.stdout).strip()}"
        )
    return result.stdout.strip()


def _api_json(path: str, token: str) -> dict[str, object]:
    request = urllib.request.Request(
        f"{GITHUB_API}/{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "mastermind-ci-canary-resolver",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        return json.load(response)


def pull_request(repository: str, number: int, token: str) -> dict[str, object]:
    return _api_json(f"repos/{repository}/pulls/{number}", token)


def compare_commits(repository: str, base: str, head: str, token: str) -> dict[str, object]:
    """GitHub's ``base...head`` relation.

    ``status`` is ``identical`` or ``ahead`` (and ``behind_by`` is 0) exactly
    when ``base`` is reachable from ``head``.  ``per_page=1`` keeps the commit
    and file listings — irrelevant to the relation — from bloating the reply.
    """
    return _api_json(f"repos/{repository}/compare/{base}...{head}?per_page=1", token)


def write_outputs(path: Path, values: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def _merged_candidate(
    repository: str,
    pr_number: int,
    data: dict[str, object],
    head_sha: str,
    token: str,
) -> tuple[str, str]:
    """Return ``(tested_sha, base_sha)`` for a merged same-repository PR.

    ``tested_sha`` is the API's ``merge_commit_sha``, proven reachable on main
    through the compare endpoint BEFORE anything is fetched, then fetched by
    exact SHA and re-read from the object store.  ``base_sha`` is the main
    commit the PR landed on, derived from the merge commit's own parents so it
    is sound for every merge strategy the repository allows:

    * two parents (merge commit): first parent, with the second parent bound to
      the frozen PR head — a criss-cross or reversed merge is refused;
    * one parent (squash, or rebase): ``tested~commits`` where ``commits`` is
      the PR's frozen commit count.  A rebase lands exactly that many commits,
      so the walk ends on the pre-merge main tip; a squash lands one, so the
      walk over-reaches by ``commits - 1`` main commits — wider, never
      narrower, than the PR's own change set.  Squash cannot be told from
      rebase through the API, and an under-inclusive base would let a merged
      head skip the packs its earlier commits touched.
    """
    merge_sha = str(data.get("merge_commit_sha") or "")
    if len(merge_sha) != 40:
        raise ResolutionError(
            f"merged pull request #{pr_number} carries no 40-character merge commit SHA"
        )
    relation = compare_commits(repository, merge_sha, "main", token)
    status = str(relation.get("status") or "")
    behind_by = relation.get("behind_by")
    if status not in {"identical", "ahead"} or behind_by != 0:
        raise ResolutionError(
            f"pull request #{pr_number} merge commit {merge_sha} is not reachable on "
            f"main (compare status={status or 'unknown'}, behind_by={behind_by!r})"
        )
    commits = data.get("commits")
    if isinstance(commits, bool) or not isinstance(commits, int) or commits < 1:
        raise ResolutionError(
            f"GitHub returned an invalid commit count for merged pull request #{pr_number}"
        )
    local_ref = f"refs/ci-canary/pull/{pr_number}/merged"
    fetch = ["fetch", "--no-tags"]
    if git("rev-parse", "--is-shallow-repository") == "true":
        # The hosted control checkout is shallow; deepen just far enough for the
        # first-parent walk below without unshallowing a full clone elsewhere.
        fetch.append(f"--depth={commits + 1}")
    git(*fetch, "origin", f"+{merge_sha}:{local_ref}")
    tested_sha = git("rev-parse", f"{local_ref}^{{commit}}")
    if tested_sha != merge_sha:
        raise ResolutionError(
            "fetched merge commit does not match the API merge commit: "
            f"fetched={tested_sha}, API={merge_sha}"
        )
    parents = git("rev-list", "--parents", "-n", "1", tested_sha).split()[1:]
    if len(parents) == 2:
        if parents[1] != head_sha:
            raise ResolutionError(
                "merge commit second parent does not match the frozen PR head: "
                f"parent={parents[1]}, API={head_sha}"
            )
        base_sha = parents[0]
    elif len(parents) == 1:
        base_sha = parents[0] if commits == 1 else git("rev-parse", f"{tested_sha}~{commits}")
    else:
        raise ResolutionError(
            f"merge commit {tested_sha} has {len(parents)} parents; expected 1 or 2"
        )
    if len(base_sha) != 40:
        raise ResolutionError(f"merged pull request #{pr_number} base resolved to {base_sha!r}")
    return tested_sha, base_sha


def resolve(repository: str, github_sha: str, pr_number: int, token: str) -> dict[str, str]:
    if pr_number == 0:
        tested_sha = git("rev-parse", f"{github_sha}^{{commit}}")
        parent = git("rev-parse", f"{tested_sha}^")
        return {
            "source_kind": "trusted-main",
            "tested_ref": tested_sha,
            "tested_sha": tested_sha,
            "base_sha": parent,
            "head_sha": tested_sha,
            "head_ref": "main",
            "contamination_sha": parent,
        }

    if not token:
        raise ResolutionError("GITHUB_TOKEN is required to resolve a pull request")
    data = pull_request(repository, pr_number, token)
    state = str(data.get("state") or "")
    merged = state == "closed" and bool(data.get("merged_at"))
    if state != "open" and not merged:
        raise ResolutionError(
            f"pull request #{pr_number} is not open (state={state or 'unknown'}, not merged)"
        )
    head = data.get("head") or {}
    base = data.get("base") or {}
    head_repo = (head.get("repo") or {}).get("full_name")
    if str(head_repo).lower() != repository.lower():
        raise ResolutionError(
            f"pull request #{pr_number} head is {head_repo!r}, not same-repository"
        )
    if base.get("ref") != "main":
        raise ResolutionError(f"pull request #{pr_number} does not target main")
    api_base_sha = str(base.get("sha") or "")
    head_sha = str(head.get("sha") or "")
    head_ref = str(head.get("ref") or "")
    if len(api_base_sha) != 40 or len(head_sha) != 40:
        raise ResolutionError("GitHub returned an invalid base/head SHA")
    if not head_ref:
        raise ResolutionError("GitHub returned an empty PR head ref")
    git("check-ref-format", "--branch", head_ref)

    if merged:
        tested_sha, base_sha = _merged_candidate(repository, pr_number, data, head_sha, token)
        return {
            "source_kind": "same-repository-pr-merged",
            "tested_ref": tested_sha,
            "tested_sha": tested_sha,
            "base_sha": base_sha,
            "head_sha": head_sha,
            "head_ref": head_ref,
            "contamination_sha": base_sha,
        }

    tested_ref = f"refs/pull/{pr_number}/merge"
    local_ref = f"refs/ci-canary/pull/{pr_number}/merge"
    git("fetch", "--no-tags", "origin", f"+{tested_ref}:{local_ref}")
    tested_sha = git("rev-parse", f"{local_ref}^{{commit}}")
    api_merge = data.get("merge_commit_sha")
    if api_merge and api_merge != tested_sha:
        raise ResolutionError(
            f"merge ref moved during resolution: API={api_merge}, fetched={tested_sha}"
        )
    base_sha = git("rev-parse", f"{tested_sha}^1")
    fetched_head = git("rev-parse", f"{tested_sha}^2")
    if fetched_head != head_sha:
        raise ResolutionError(
            "fetched merge head does not match the frozen API head: "
            f"fetched={fetched_head}, API={head_sha}"
        )
    return {
        "source_kind": "same-repository-pr-merge",
        "tested_ref": tested_ref,
        "tested_sha": tested_sha,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "head_ref": head_ref,
        "contamination_sha": base_sha,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--github-sha", required=True)
    parser.add_argument("--pr-number", type=int, default=0)
    parser.add_argument("--github-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        values = resolve(
            args.repository,
            args.github_sha,
            args.pr_number,
            os.environ.get("GITHUB_TOKEN", ""),
        )
    except ResolutionError as exc:
        print(f"::error title=ci-canary-ref::{exc}", flush=True)
        return 2
    write_outputs(args.github_output, values)
    print(
        "CI_CANARY_REF="
        + json.dumps({"repository": args.repository, **values}, sort_keys=True),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
