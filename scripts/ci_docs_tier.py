#!/usr/bin/env python3
"""Trusted-base classifier for the planner's docs fast lane.

A pull request whose every changed path is an inert narrative record
(``*.md`` under ``docs/``, ``research/`` or ``agentos/``) cannot redden any
legacy CI job that does not read narrative files, yet the scoped planner
still launches two packs for it: one for the unscoped always-on jobs and one
for every job whose hand-written scope over-claims ``research/**/*.md``
(measured 2026-11-11, PR #10997: 7 jobs / 2 packs for a one-file markdown
edit).  ``build_plan`` therefore accepts a FAST LANE that selects zero
legacy jobs, leaving ``fences.yml``, ``ci-authority.yml``, ``contract-delta``
and ``ci-gate`` as the required proof of the head.

The decision to drop every legacy job is authority over CI execution, and a
candidate merge tree must not be its own judge: this classifier is executed
from a checkout of the repository's DEFAULT BRANCH (the same trusted-base
shape ``ci-authority.yml`` uses), never from the pull request's copy.  It
inspects only real git objects — the exact tested merge tree and its first
parent — and publishes a verdict the planner binds to its own independently
resolved changed-file list by digest.  Any doubt (unreadable manifest, odd
status letter, rename, delete, typechange, non-markdown path, a markdown
file some job declares as an individual literal path, or any internal
error) publishes ``docs_tier: false`` and exits 0: the fail-closed
direction is simply the incumbent scoped behaviour.

Verdict fields are bounded on purpose: a path count, a digest, and one
example path.  The full list already travels as the planner's
``ci-changed-files`` artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

SCHEMA = "ci.docs_tier.v1"
# Must stay byte-identical to scripts/run_ci_pack.py's changed_files_digest
# over the same git output.  Pinned jointly by tests/test_ci_docs_tier.py.

MANIFEST_PATH = ".github/ci/legacy-jobs.yml"

# Narrative roots whose markdown is inert unless a consumer names it.
NARRATIVE_ROOTS = ("docs/", "research/", "agentos/")

# Markdown files read as DATA by scripts the manifest only names as commands.
# Each entry must carry the consumer that reads it, and each addition is a
# review act: this list is the only hand-maintained fail-closed surface.
CONSUMED_MARKDOWN = {
    # scripts/check_house_law_registry.py --emit-docs verifies this registry
    # document against the registry table (house-law-registry{,-code}).
    "docs/HOUSE_LAW_CI_GUARD_SUITE.md",
    # scripts/check_append_only_assertions.py reads this registry directly.
    "docs/INTELLIGENCE_REGISTRY.md",
}

# Add/modify keep the tested tree's every prior byte intact.  Every other
# letter widens the blast radius: D removes an owner's subject, R/C move it,
# T retypes it, U is unresolved.  Renames are refused BEFORE the both-sides
# expansion so old and new paths cannot smuggle a half-narrative rename.
TIER_STATUSES = frozenset({"A", "M"})

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_GLOB_META = set("*?[]!")
_MD_LITERAL_RE = re.compile(r"(?:[A-Za-z0-9_.\-]+/)*[A-Za-z0-9_.\-]+\.md")
_REASON_LIMIT = 200


def _bounded(text: str) -> str:
    return text[:_REASON_LIMIT].replace("\n", " ")


def changed_paths_digest(paths: list[str]) -> str:
    """Byte-identical twin of run_ci_pack.changed_files_digest.

    The planner resolves its own list from the same git objects with the
    same flags, so equal digests prove the classifier judged exactly the
    list the planner scoped — never a stale, truncated or substituted one.
    """
    payload = json.dumps(paths, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _is_narrative_markdown(path: str) -> bool:
    return path.endswith(".md") and path.startswith(NARRATIVE_ROOTS)


def manifest_literal_markdown(document: object) -> set[str]:
    """Every literal ``*.md`` path any job declares in the base manifest.

    A hand-written individual markdown row in a job's scope is the one
    signal the manifest itself gives that some suite reads that exact file
    (wildcards like ``research/**/*.md`` are scope smear and ignored).  The
    classifier reads this from the BASE tree's manifest, which for an
    all-markdown diff is byte-identical to the merge tree's manifest the
    planner loads.
    """
    consumed: set[str] = set()
    if not isinstance(document, dict):
        return consumed
    jobs = document.get("jobs")
    if not isinstance(jobs, dict):
        return consumed
    for definition in jobs.values():
        if not isinstance(definition, dict):
            continue
        for key in ("paths", "scope"):
            rows = definition.get(key)
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, str):
                    continue
                candidate = row.strip()
                if (
                    candidate.endswith(".md")
                    and not (_GLOB_META & set(candidate))
                    and "/" in candidate
                    and not candidate.startswith("/")
                    and _MD_LITERAL_RE.fullmatch(candidate)
                ):
                    consumed.add(candidate)
    return consumed


def classify_entries(
    entries: list[tuple[str, str]],
    *,
    consumed: set[str] | None = None,
) -> tuple[bool, str]:
    """Pure classification of ``(status, path)`` git entries.

    ``consumed`` defaults to the hand-curated registry set; callers that
    have a manifest overlay it with :func:`manifest_literal_markdown`.
    Entries must arrive in git's own order — the digest is order-sensitive.
    """
    consumed = (CONSUMED_MARKDOWN if consumed is None else consumed) | set(
        CONSUMED_MARKDOWN
    )
    if not entries:
        return False, "classifier refuses an empty changed-file inventory"
    paths: list[str] = []
    for status, path in entries:
        if status not in TIER_STATUSES:
            return False, _bounded(
                f"status {status or '∅'} on {path} is not add/modify"
            )
        if not _is_narrative_markdown(path):
            return False, _bounded(f"{path} is not narrative markdown")
        if path in consumed:
            return False, _bounded(f"{path} is a consumed registry document")
        if path not in paths:
            paths.append(path)
    return True, f"{len(paths)} inert narrative path(s)"


def _git(workspace: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(workspace), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _diff_entries(workspace: Path, base: str, merge: str) -> list[tuple[str, str]]:
    """(status, path) entries from the exact revision spec the planner uses.

    Rename/copy rows carry two paths in git's -z stream; they are refused
    as a STATUS before any expansion, matching the planner's both-sides
    semantics for non-tier plans.
    """
    raw = _git(
        workspace,
        "diff",
        "--name-status",
        "-z",
        "--find-renames",
        "--find-copies",
        f"{base}...{merge}",
    )
    fields = raw.split("\0")
    if fields and fields[-1] == "":
        fields.pop()
    entries: list[tuple[str, str]] = []
    index = 0
    while index < len(fields):
        status = fields[index]
        index += 1
        if not status:
            raise ValueError("empty git diff status")
        if status[0] in {"R", "C"}:
            # Consume old+new so the stream stays parseable; classify_entries
            # refuses the R/C STATUS, so naming either path suffices.
            old = fields[index]
            index += 2
            entries.append((status, old))
            continue
        entries.append((status, fields[index]))
        index += 1
    return entries


def _dedup_planner_order(entries: list[tuple[str, str]]) -> list[str]:
    seen: dict[str, None] = {}
    for _status, path in entries:
        if path:
            seen.setdefault(path, None)
    return list(seen)


def classify_workspace(
    workspace: Path, *, base: str, merge: str
) -> dict[str, object]:
    """Full trusted-base verdict for one exact (base, merge) pair."""
    if not _SHA_RE.fullmatch(base) or not _SHA_RE.fullmatch(merge):
        return _verdict(False, "base/merge are not exact 40-hex SHAs")
    try:
        _git(workspace, "cat-file", "-e", f"{base}^{{commit}}")
        _git(workspace, "cat-file", "-e", f"{merge}^{{commit}}")
        manifest_raw = _git(workspace, "show", f"{base}:{MANIFEST_PATH}")
        entries = _diff_entries(workspace, base, merge)
    except (subprocess.CalledProcessError, OSError, ValueError) as exc:
        return _verdict(False, _bounded(f"classifier-error: {exc}"))
    consumed = set(CONSUMED_MARKDOWN)
    try:
        import yaml  # available in the ci-plan runner venv
    except ImportError as exc:
        # No YAML reader: the manifest-literal scan cannot run, so the tier
        # cannot be attested at all. Fail closed (the ci-plan runner installs
        # pyyaml, so this is a defensive arm, not an expected one).
        return _verdict(False, _bounded(f"classifier-error: no yaml reader ({exc})"))
    try:
        document = yaml.safe_load(manifest_raw)
    except yaml.YAMLError:
        return _verdict(False, "classifier-error: base manifest unreadable")
    consumed |= manifest_literal_markdown(document)
    eligible, reason = classify_entries(entries, consumed=consumed)
    paths = _dedup_planner_order(entries)
    verdict = _verdict(eligible, reason)
    verdict["base_sha"] = base
    verdict["merge_sha"] = merge
    verdict["paths_sha256"] = changed_paths_digest(paths)
    verdict["paths_count"] = len(paths)
    if paths:
        verdict["example_path"] = paths[0]
    return verdict


def _verdict(eligible: bool, reason: str) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "docs_tier": eligible,
        "reason": reason,
        "base_sha": "",
        "merge_sha": "",
        "paths_sha256": "",
        "paths_count": 0,
    }


def _run_selftest() -> int:
    """Pure classification proofs; no git, no manifest, no filesystem."""
    consumed = {"docs/HOUSE_LAW_CI_GUARD_SUITE.md"}
    cases = [
        ((("M", "docs/NOTE.md"),), True),
        ((("A", "research/plan_2026/ROOM.md"), ("M", "agentos/decisions/DEC-X.md")), True),
        ((("M", "README.md"),), False),  # not under a narrative root
        ((("M", "engine/note.md"),), False),  # markdown outside the roots
        ((("M", "docs/evidence.json"),), False),  # not markdown
        ((("D", "docs/NOTE.md"),), False),  # deletion
        ((("R100", "docs/A.md"),), False),  # rename
        ((("C100", "docs/A.md"),), False),  # copy
        ((("T", "docs/A.md"),), False),  # typechange
        ((("U", "docs/A.md"),), False),  # unresolved
        ((("M", "docs/HOUSE_LAW_CI_GUARD_SUITE.md"),), False),  # consumed
        ((), False),  # empty inventory
    ]
    for entries, expected in cases:
        got, _reason = classify_entries(list(entries), consumed=consumed)
        assert got is expected, f"{entries}: expected {expected}, got {got}"
    digest = changed_paths_digest(["docs/A.md", "docs/B.md"])
    assert len(digest) == 64 and digest != changed_paths_digest(["docs/B.md", "docs/A.md"])
    literal = manifest_literal_markdown(
        {
            "jobs": {
                "a": {"paths": ["research/**/*.md", "research/DO_NOT_REBUILD.md"]},
                "b": {"scope": ["docs/HOUSE_LAW_CI_GUARD_SUITE.md", "engine/x.py"]},
                "c": {"paths": ["*.md"]},
            }
        }
    )
    assert literal == {
        "research/DO_NOT_REBUILD.md",
        "docs/HOUSE_LAW_CI_GUARD_SUITE.md",
    }, literal
    print("ci_docs_tier selftest: ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--base", default="")
    parser.add_argument("--merge", default="")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return _run_selftest()
    if args.out is None:
        parser.error("--out is required unless --selftest")
    verdict = classify_workspace(args.workspace, base=args.base, merge=args.merge)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(verdict, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"::notice title=ci-docs-tier::{verdict['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
