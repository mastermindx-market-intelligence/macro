#!/usr/bin/env python3
"""Draft a WS-* append and a handoff skeleton from seat PR JSON.

Knowledge plane only (invariant I1). This command never gates execution, never
starts or stops work, and does not import a control plane. It reads one local
JSON file the seat already built (schema agentos.record_draft.v1) and writes a
draft to stdout or --out. It never writes agentos/. scripts/agentos.py validate
remains the gate, and only for malformed records.

The seat supplies the pull-request number, title, head sha, files, and
merged_at, and names the workstream. Optional kinds draft-decision and
draft-discovery add those skeletons to the same JSON. A discovery skeleton
keeps falsifier and so_what unfilled, so check_discovery rejects it until a
human replaces both. Facts this process cannot check from the local git object
store are copied and marked UNVERIFIED. Nothing here calls GitHub or EDGAR.
Rank, gate, suffix, and priority keys are refused: a handoff stem is
<KEY>-<YYYY-MM-DD> and this draft does not rank work. --repo selects the git
repository used for cat-file and diff-tree; it does not move the store.

Usage::

    python3 scripts/agentos_records_draft.py --pr-json pr.json
    python3 scripts/agentos_records_draft.py --pr-json pr.json --out /tmp/draft.json
    python3 scripts/agentos_records_draft.py --pr-json pr.json --repo /path/to/repo
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shlex
import subprocess
import sys
import unicodedata
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from scripts.agentos import (  # noqa: E402  — pin above is the import contract
    FRONTMATTER_RE,
    HANDOFF_ENDED,
    HANDOFF_MODEL,
    check_decision,
    check_discovery,
    check_handoff,
)
import yaml  # noqa: E402

INPUT_SCHEMA = "agentos.record_draft.v1"
OUTPUT_SCHEMA = "agentos.record_draft_output.v1"
REFUSED_KEYS = frozenset({"rank", "gate", "suffix", "priority"})
_TOP_KEYS = frozenset({
    "schema", "workstream", "pr", "session", "model", "ended_because", "kinds",
})
_KINDS = frozenset({"draft-decision", "draft-discovery"})
# check_discovery rejects this token: it has no command, file:line, or #PR.
DISCOVERY_FALSIFIER_PLACEHOLDER = "UNFILLED"
# An empty so_what is the unfilled placeholder. A non-empty stub would pass
# check_discovery, so the skeleton stays empty until a human writes it.
DISCOVERY_SO_WHAT_PLACEHOLDER = ""
_PR_KEYS = frozenset({"number", "title", "head_sha", "files", "merged_at"})
_WS_RE = re.compile(r"^WS:([A-Z0-9]+(?:-[A-Z0-9]+)*)$")
# ``re.ASCII``, not ``[0-9]``: local to this pattern, retroactively covering
# every ``\d`` here -- present and future -- while ``\d{2}`` stays readable.
# Without it ``\d`` matches every Unicode Nd; measured pre-fix, only the
# hour/minute/second ONES coerced -- 3 of the 6 time positions x 670
# non-ASCII Nd = 2010 (``2026-10-13T1٠:34:56Z``): ``_strptime``'s TimeRE
# pins the tens as ASCII literals and ``fromisoformat`` refused the date,
# so the regex class was the only door that could refuse the whole family.
_MERGED_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:T\d{2}:\d{2}:\d{2}Z)?$", re.ASCII)
_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
# This checkout can be a partial clone. A missing object must not promisor-fetch,
# and a miss can walk a multi-gigabyte pack index, so the lookup is bounded.
_GIT_TIMEOUT_SECONDS = 5
# One argv hardening list for BOTH the git the drafter runs and the git it
# RECORDS. A recorded command is a reproduction artifact a human pastes into a
# shell; if the two prefixes drift, the copy-paste loses the ``-c`` overrides.
# ``core.fsmonitor`` is the PROVEN vector, and it is proven for the subcommands
# ``_git`` admits and for nothing wider: ``_git`` accepts only ``cat-file`` and
# ``diff-tree``, and a target repository's ``.git/config`` can name a
# ``core.fsmonitor`` executable that a plain, unhardened ``git diff-tree`` runs.
# ``test_diff_tree_does_not_invoke_repo_fsmonitor`` and
# ``test_pasting_a_recorded_git_command_does_not_run_repo_fsmonitor`` each assert
# that power check first -- an UNHARDENED argv really does touch the marker on
# this git build -- so the flag is not defending a hypothetical.
# ``-c core.hooksPath=`` is defense-in-depth, not a second proven vector:
# hooks fire for commands that move refs or the index (commit, push,
# receive-pack, checkout), not for read-only plumbing, so no command this
# drafter can record reaches ``core.hooksPath`` today -- measured on git
# 2.43.0 in a throwaway repository whose ``core.hooksPath`` was seeded with
# all 28 hook names documented in ``githooks(5)``: plain ``cat-file`` and
# ``diff-tree`` fire NOTHING, and ``git commit`` fires SIX of them
# (pre-commit, prepare-commit-msg, commit-msg, post-commit,
# reference-transaction, post-index-change). An earlier revision here claimed
# five; that count is seed-dependent -- it only reproduces from a seed that
# omits post-index-change. No test here proves a hook ran, because none can;
# what IS pinned is that the flag stays in both prefixes
# (``test_recorded_git_commands_carry_the_hardening_flags``). It is carried in
# the same list on purpose: if the ``_git`` subcommand set is ever widened,
# the widening starts hardened instead of becoming the day the copy-paste
# gained a second execution vector.
_GIT_HARDENING = ("-c", "core.fsmonitor=", "-c", "core.hooksPath=")
# Unicode general categories the ``pr.files`` guard refuses ON TOP of the
# ``splitlines()`` clause, and the two reasons differ:
# (i) characters that DO break ``str.splitlines`` inside an entry, so one seat
#     string becomes two rendered lines, and that the pre-#9310 ``"\n" in entry
#     or "\r" in entry`` test missed: U+0085 NEL, U+000B VT, U+000C FF (Cc),
#     U+2028 LINE SEPARATOR (Zl) and U+2029 PARAGRAPH SEPARATOR (Zp). U+000A and
#     U+000D break lines the same way and were already caught. Scope note: the
#     count clause only sees a separator that is FOLLOWED by text -- a trailing
#     one collapses to a single element (``"lib/x.py\n".splitlines() ==
#     ["lib/x.py"]``), so this category set, not the count, is what refuses a
#     trailing break of any kind.
# (ii) characters that break NO line, so no line count can see them, and that
#     must not reach a rendered record either way: U+0009 TAB, U+0000 NUL and
#     U+001B ESC (Cc), and the zero-advance invisibles U+200B ZWSP, the bidi
#     controls U+202A LRE / U+202B RLE / U+202C PDF / U+202D LRO / U+202E RLO
#     and U+FEFF BOM (Cf). The rendered path is copy-pasted back into a shell,
#     where ESC is an escape sequence and a bidi override is not decoration.
# Both parts bind through the same door: ``pr.files`` entries are interpolated
# RAW into the handoff body and the WS append, so the field guard is the only
# place they can be refused -- ``_q`` protects the quoted fields, not those two
# f-strings. (i) is pinned by ``test_file_path_line_separators_are_refused``,
# (ii) by ``test_invisible_non_line_breakers_are_refused``.
_UNSAFE_LINE_CATEGORIES = frozenset({"Cc", "Cf", "Zl", "Zp"})
_GIT_ENV = dict(os.environ)
_GIT_ENV["GIT_TERMINAL_PROMPT"] = "0"
_GIT_ENV["GIT_NO_LAZY_FETCH"] = "1"


class DraftError(Exception):
    """The seat JSON cannot be drafted. Exit 2. This is not an execution gate."""


class DraftSchemaError(Exception):
    """The renderer built a handoff the record gate rejects. Exit 1."""


def _q(value: str) -> str:
    """YAML double-quoted scalar. Newlines stay inside the scalar.

    Python's ``json`` module with ``ensure_ascii=False`` leaves U+2028, U+2029
    and U+0085 as raw characters, which YAML double-quoted scalars treat as
    line breaks and which Python's ``str.splitlines`` splits on. Escape them
    so the rendered scalar stays on one physical line.
    """
    encoded = json.dumps(value, ensure_ascii=False)
    encoded = encoded.replace("\u2028", "\\u2028")
    encoded = encoded.replace("\u2029", "\\u2029")
    encoded = encoded.replace("\u0085", "\\u0085")
    return encoded


def _walk_refused(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in REFUSED_KEYS:
                raise DraftError(f"refused key {key!r}")
            _walk_refused(item)
    elif isinstance(value, list):
        for item in value:
            _walk_refused(item)


def _git(
    subcommand: str, *git_args: str, repo: Path | None = None
) -> subprocess.CompletedProcess[str] | None:
    if subcommand not in {"cat-file", "diff-tree"}:
        raise RuntimeError(f"refusing git subcommand {subcommand}")
    root = _ROOT if repo is None else repo
    try:
        return subprocess.run(
            [
                "git",
                *_GIT_HARDENING,
                "-C",
                str(root),
                subcommand,
                *git_args,
            ],
            capture_output=True,
            text=True,
            check=False,
            env=_GIT_ENV,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _git_tool(repo: Path | None) -> str:
    """Command prefix recorded in the draft, hardened like the drafter's own argv.

    ``_git`` runs ``git`` with ``-c core.fsmonitor= -c core.hooksPath=`` before
    ``-C``. The recorded prefix is quoted out of the handoff by a human, so it
    carries the same ``-c`` overrides in the same order; a plain ``git -C``
    prefix would run the target repository's ``core.fsmonitor`` for the copier.
    An omitted ``--repo`` keeps the flags and drops ``-C``.
    """
    argv = ["git", *_GIT_HARDENING]
    if repo is not None:
        argv += ["-C", str(repo)]
    return " ".join(shlex.quote(part) for part in argv)


def _load_document(path: Path) -> dict:
    if not path.is_file():
        raise DraftError(f"pr json not found: {path}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DraftError(f"pr json is not valid JSON: {exc.__class__.__name__}") from exc
    if not isinstance(document, dict):
        raise DraftError("pr json must be an object")
    _walk_refused(document)
    unknown = sorted(set(document) - _TOP_KEYS)
    if unknown:
        raise DraftError(f"unknown key {unknown[0]!r}")
    if document.get("schema") != INPUT_SCHEMA:
        raise DraftError(f"schema must be {INPUT_SCHEMA}")
    return document


def _workstream_key(document: dict) -> str:
    citation = document.get("workstream")
    if not isinstance(citation, str):
        raise DraftError("workstream must be a WS:KEY citation")
    match = _WS_RE.fullmatch(citation)
    if match is None:
        raise DraftError(f"workstream must be a WS:KEY citation, got {citation!r}")
    key = match.group(1)
    relative = f"agentos/workstreams/WS-{key}.md"
    if not (_ROOT / relative).is_file():
        raise DraftError(f"workstream file absent: {relative}")
    return key


def _pr_fields(document: dict) -> dict:
    pr = document.get("pr")
    if not isinstance(pr, dict):
        raise DraftError("pr must be an object")
    unknown = sorted(set(pr) - _PR_KEYS)
    if unknown:
        raise DraftError(f"unknown pr key {unknown[0]!r}")
    number = pr.get("number")
    if type(number) is not int or number < 1:
        raise DraftError("pr.number must be a positive integer")
    title = pr.get("title")
    if not isinstance(title, str) or not title.strip():
        raise DraftError("pr.title must be a non-empty string")
    head_sha = pr.get("head_sha")
    if not isinstance(head_sha, str) or not head_sha.strip():
        raise DraftError("pr.head_sha must be a non-empty string")
    files = pr.get("files")
    if not isinstance(files, list) or not files:
        raise DraftError("pr.files must be a non-empty list")
    checked: list[str] = []
    for entry in files:
        if not isinstance(entry, str) or not entry.strip():
            raise DraftError("pr.files entries must be non-empty strings")
        if (
            len(entry.splitlines()) != 1
            or any(
                unicodedata.category(ch) in _UNSAFE_LINE_CATEGORIES for ch in entry
            )
            or entry.startswith(("/", "\\"))
        ):
            raise DraftError("pr.files entries must be single-line repo-relative paths")
        if any(part == ".." for part in entry.split("/")):
            raise DraftError("pr.files entries must not contain ..")
        checked.append(entry)
    merged_at = pr.get("merged_at")
    match = _MERGED_RE.fullmatch(merged_at) if isinstance(merged_at, str) else None
    if match is None:
        raise DraftError("pr.merged_at must be YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ")
    try:
        _dt.date.fromisoformat(match.group(1))
    except ValueError:
        raise DraftError(
            "pr.merged_at must be YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ"
        ) from None
    # The regex permits any digit pairs in the time component; reject impossible
    # wall-clock times like 2026-10-13T99:99:99Z when the ``T...Z`` part is
    # present. ``fullmatch`` on _MERGED_RE admits exactly two shapes: the fixed
    # 10-character date group, or that group plus the fixed 10-character
    # ``(?:T\d{2}:\d{2}:\d{2}Z)`` group. So an accepted string is 10 or 20
    # characters long and ``len(merged_at) > 10`` already means index 10 is the
    # literal ``T``; the second test was implied.
    if len(merged_at) > 10:
        try:
            _dt.datetime.strptime(merged_at, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            raise DraftError(
                "pr.merged_at must be YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ"
            ) from None
    return {
        "number": number,
        "title": title,
        "head_sha": head_sha,
        "files": checked,
        "merged_at": merged_at,
        "day": match.group(1),
    }


def _optional_enum(document: dict, field: str, allowed: set[str], default: str) -> tuple[str, bool]:
    if field not in document:
        return default, True
    value = document[field]
    if value not in allowed:
        raise DraftError(f"{field} must be one of {', '.join(sorted(allowed))}")
    return str(value), False


def _session(document: dict) -> tuple[str, bool]:
    if "session" not in document:
        return "UNVERIFIED", True
    value = document["session"]
    if not isinstance(value, str) or not value.strip():
        raise DraftError("session must be a non-empty string")
    return value, False


def _kinds(document: dict) -> list[str]:
    if "kinds" not in document:
        return []
    value = document["kinds"]
    if not isinstance(value, list):
        raise DraftError("kinds must be a list")
    found: list[str] = []
    for item in value:
        if not isinstance(item, str) or item not in _KINDS:
            raise DraftError(
                "kinds entry must be draft-decision or draft-discovery, "
                f"got {item!r}"
            )
        if item in found:
            raise DraftError(f"duplicate kinds entry {item!r}")
        found.append(item)
    return found


def _observe(head_sha: str, repo: Path | None = None) -> tuple[str | None, list[str] | None]:
    """Local object type, and the commit name list when diff-tree returns one.

    A missing object, a non-hex seat sha, or an empty name list stays None.
    Empty output is not treated as proof that every path is absent: merge
    commits can print nothing. The seat sha is never rewritten.
    """
    if not _SHA_RE.fullmatch(head_sha):
        return None, None
    typed = _git("cat-file", "-t", head_sha, repo=repo)
    if typed is None or typed.returncode != 0:
        return None, None
    object_type = typed.stdout.strip() or None
    if object_type != "commit":
        return object_type, None
    listed = _git("diff-tree", "--no-commit-id", "--name-only", "-r", head_sha, repo=repo)
    if listed is None or listed.returncode != 0:
        return object_type, None
    names = [line for line in listed.stdout.splitlines() if line]
    if not names:
        return object_type, None
    return object_type, names


def _file_rows(files: list[str], names: list[str] | None) -> list[dict]:
    name_set = set(names) if names is not None else None
    rows: list[dict] = []
    for path in files:
        if name_set is None:
            rows.append({"path": path, "status": "UNVERIFIED", "in_local_commit": None})
        elif path in name_set:
            rows.append({"path": path, "status": "observed", "in_local_commit": True})
        else:
            rows.append({"path": path, "status": "UNVERIFIED", "in_local_commit": False})
    return rows


def _what(row: dict, number: int, head_sha: str, repo: Path | None = None) -> str:
    path_clause = f"Seat JSON lists this path for PR #{number}."
    tool = _git_tool(repo)
    if row["in_local_commit"] is True:
        return (
            f"{path_clause} GIT_NO_LAZY_FETCH=1 {tool} diff-tree --no-commit-id "
            f"--name-only -r {head_sha} names this path. What the diff changes is UNVERIFIED."
        )
    if row["in_local_commit"] is False:
        return (
            f"{path_clause} GIT_NO_LAZY_FETCH=1 {tool} diff-tree --no-commit-id "
            f"--name-only -r {head_sha} does not name this path. Whether the pull "
            "request touches it is UNVERIFIED."
        )
    return f"{path_clause} Presence in the local commit is UNVERIFIED."


def _unverified_rows(
    *,
    object_type: str | None,
    model_defaulted: bool,
    ended_defaulted: bool,
    session_defaulted: bool,
) -> list[dict[str, str]]:
    rows = [
        {
            "field": "pr.number",
            "status": "UNVERIFIED",
            "reason": "no GitHub call; the seat value is copied",
        },
        {
            "field": "pr.title",
            "status": "UNVERIFIED",
            "reason": "no GitHub call; the seat value is copied",
        },
        {
            "field": "pr.merged_at",
            "status": "UNVERIFIED",
            "reason": "no GitHub call; the seat value is copied",
        },
        {
            "field": "pr.head_sha_is_github_head",
            "status": "UNVERIFIED",
            "reason": "a local git object is not evidence that this sha is the pull-request head",
        },
        {
            "field": "pr.file_meanings",
            "status": "UNVERIFIED",
            "reason": "a path list does not say what a diff changed",
        },
    ]
    if object_type is None:
        rows.append({
            "field": "pr.head_sha_local_object",
            "status": "UNVERIFIED",
            "reason": "git cat-file did not report a local object for the seat sha",
        })
    if model_defaulted:
        rows.append({
            "field": "model",
            "status": "UNVERIFIED",
            "reason": "the seat JSON omitted model; the skeleton records local",
        })
    if ended_defaulted:
        rows.append({
            "field": "ended_because",
            "status": "UNVERIFIED",
            "reason": "the seat JSON omitted ended_because; the skeleton records ci_handoff",
        })
    if session_defaulted:
        rows.append({
            "field": "session",
            "status": "UNVERIFIED",
            "reason": "the seat JSON omitted session; the skeleton records UNVERIFIED",
        })
    return rows


def _render_handoff(
    *,
    key: str,
    session: str,
    model: str,
    ended: str,
    pr: dict,
    file_rows: list[dict],
    verified: list[dict[str, str]],
    object_type: str | None,
    repo: Path | None = None,
) -> str:
    number = pr["number"]
    title = pr["title"]
    head_sha = pr["head_sha"]
    mission = (
        f"Draft a knowledge-plane handoff and workstream append for seat-supplied "
        f"PR #{number} ({title}). This draft records the supplied metadata and local "
        f"git observations. It does not gate execution."
    )
    state_before = (
        f"UNVERIFIED. The seat JSON did not include the workstream state before "
        f"PR #{number}. Seat head sha: {head_sha}."
    )
    lines = [
        "---",
        f"workstream: {_q('WS:' + key)}",
        f"session: {_q(session)}",
        f"model: {_q(model)}",
        f"ended_because: {_q(ended)}",
        f"mission: {_q(mission)}",
        f"state_before: {_q(state_before)}",
        "changed:",
    ]
    for row in file_rows:
        lines.append(f"  - path: {_q(row['path'])}")
        lines.append(f"    what: {_q(_what(row, number, head_sha, repo))}")
    lines.append("prs:")
    lines.append(f"  - {number}")
    lines.append("verified:")
    for item in verified:
        lines.append(f"  - claim: {_q(item['claim'])}")
        lines.append(f"    command: {_q(item['command'])}")
        lines.append(f"    result: {_q(item['result'])}")
    lines.extend([
        "unverified:",
        f"  - claim: {_q(f'PR number {number} is the GitHub number of a merged pull request.')}",
        "    what_would_verify: "
        + _q("A seat GitHub read of the pull request. This drafter does not call GitHub."),
        f"  - claim: {_q('The seat title is the GitHub pull-request title.')}",
        "    what_would_verify: "
        + _q("A seat GitHub read of the pull request. This drafter does not call GitHub."),
        f"  - claim: {_q(f'{pr["merged_at"]} is the GitHub merge time of PR #{number}.')}",
        "    what_would_verify: "
        + _q("A seat GitHub read of the merge time. This drafter does not call GitHub."),
        f"  - claim: {_q(f'{head_sha} is the GitHub head of PR #{number}.')}",
        "    what_would_verify: "
        + _q("A seat GitHub read of the pull-request head. This drafter does not call GitHub."),
        "unresolved:",
        f"  - {_q('The seat has not accepted this draft into agentos/.')}",
        f"  - {_q('PR number, title, and merged_at are UNVERIFIED against GitHub.')}",
        "next_actions:",
        "  - "
        + _q(
            "Review this skeleton and, if it is accepted, write the handoff and the "
            "workstream append in a records change. This command does not write agentos/."
        ),
        "do_not_redo:",
        "  - " + _q("Do not call GitHub or EDGAR from this drafter."),
        "  - "
        + _q(
            f"Do not suffix the handoff stem. The canonical name is {key}-{pr['day']}.md."
        ),
        "danger_areas:",
        "  - "
        + _q(
            "This draft is not an execution gate. scripts/agentos.py validate checks "
            "record shape only."
        ),
        "  - "
        + _q(
            "A handoff stem that does not end in -YYYY-MM-DD is dropped by "
            "compile-context (HANDOFF_DATE_RE in scripts/agentos.py)."
        ),
        "---",
        "",
        "## What this draft is",
        "",
        "This is a knowledge-plane skeleton drafted from a seat JSON file. "
        "It does not gate execution, start work, or write agentos/.",
        "",
        "## Seat-supplied pull request",
        "",
        f"- number: {number} - UNVERIFIED (this command does not call GitHub)",
        f"- title: {_q(title)} - UNVERIFIED (this command does not call GitHub)",
        f"- merged_at: {pr['merged_at']} - UNVERIFIED (this command does not call GitHub)",
        f"- head_sha: {_q(head_sha)} - {_sha_note(object_type)}",
        f"- session: {_q(session)}",
        "- files:",
    ])
    for row in file_rows:
        lines.append(f"  - {row['path']} - {_file_note(row)}")
    lines.extend([
        "",
        f"Append target: agentos/workstreams/WS-{key}.md",
        f"Handoff target: agentos/handoffs/{key}-{pr['day']}.md",
        "",
    ])
    return "\n".join(lines)


def _sha_note(object_type: str | None) -> str:
    if object_type is None:
        return "UNVERIFIED local git object"
    return f"local git object: {object_type}"


def _file_note(row: dict) -> str:
    if row["in_local_commit"] is True:
        return "named in the local commit diff-tree; what changed is UNVERIFIED"
    if row["in_local_commit"] is False:
        return "not named in the local commit diff-tree; pull-request membership is UNVERIFIED"
    return "UNVERIFIED"


def _render_append(
    *,
    key: str,
    pr: dict,
    file_rows: list[dict],
    object_type: str | None,
    session: str,
) -> str:
    number = pr["number"]
    lines = [
        f"## Record draft append - PR #{number}",
        "",
        "Seat-supplied pull-request metadata. Facts this drafter could not check "
        "locally are marked UNVERIFIED. This section does not change workstream "
        "status, waves, claims, or execution. It does not gate execution.",
        "",
        f"- workstream: WS:{key}",
        f"- number: {number} (UNVERIFIED against GitHub)",
        f"- title: {_q(pr['title'])} (UNVERIFIED against GitHub)",
        f"- merged_at: {pr['merged_at']} (UNVERIFIED against GitHub)",
        f"- head_sha: {_q(pr['head_sha'])} ({_sha_note(object_type)})",
        f"- session: {_q(session)}",
        "- files:",
    ]
    for row in file_rows:
        lines.append(f"  - {row['path']} ({_file_note(row)})")
    lines.append("")
    return "\n".join(lines)


def _verified_items(
    pr_json: Path,
    head_sha: str,
    files: list[str],
    object_type: str | None,
    names: list[str] | None,
    repo: Path | None = None,
) -> list[dict[str, str]]:
    command = "python3 scripts/agentos_records_draft.py --pr-json " + shlex.quote(str(pr_json))
    tool = _git_tool(repo)
    items = [{
        "claim": "The seat JSON parsed and contained the required pull-request fields.",
        "command": command,
        "result": "parsed; number, title, head_sha, files, merged_at present; agentos/ not written by this command",
    }]
    if object_type is not None:
        items.append({
            "claim": f"Local git object type of the seat head sha {head_sha}.",
            "command": f"GIT_NO_LAZY_FETCH=1 {tool} cat-file -t {head_sha}",
            "result": object_type,
        })
    if names is not None:
        name_set = set(names)
        present = [path for path in files if path in name_set]
        absent = [path for path in files if path not in name_set]
        items.append({
            "claim": f"Which seat paths are names in the local commit {head_sha}.",
            "command": f"GIT_NO_LAZY_FETCH=1 {tool} diff-tree --no-commit-id --name-only -r {head_sha}",
            "result": (
                f"name list has {len(names)} paths; "
                f"seat paths named: {', '.join(present) or '(none)'}; "
                f"seat paths absent: {', '.join(absent) or '(none)'}"
            ),
        })
    return items


def _draft_record_key(ws_key: str, number: int) -> str:
    key = f"{ws_key}-PR-{number}"
    if _WS_RE.fullmatch("WS:" + key) is None:
        raise DraftSchemaError(f"draft record key {key!r} is not UPPER-KEBAB")
    return key


def _seat_command(pr_json: Path) -> str:
    return "python3 scripts/agentos_records_draft.py --pr-json " + shlex.quote(str(pr_json))


def _render_decision(*, ws_key: str, pr: dict, pr_json: Path) -> tuple[str, str]:
    number = pr["number"]
    record_key = _draft_record_key(ws_key, number)
    relative = f"agentos/decisions/DEC-{record_key}.md"
    question = f"What should the knowledge plane record about seat-supplied PR #{number}?"
    answer = (
        f"UNVERIFIED skeleton for PR #{number} ({pr['title']}). "
        "This draft copies seat metadata. It does not decide execution."
    )
    rationale = (
        "The drafter copies seat-supplied pull-request metadata and local git "
        "observations. It does not call GitHub or EDGAR, and it does not gate execution. "
        "A human accepts or replaces this skeleton before it is a decision the "
        "organization relies on."
    )
    why_not = (
        "The seat JSON did not name alternatives. This skeleton records that "
        "absence; a human replaces it before relying on the decision."
    )
    lines = [
        "---",
        f"key: {_q(record_key)}",
        f"question: {_q(question)}",
        f"answer: {_q(answer)}",
        f"rationale: {_q(rationale)}",
        "alternatives:",
        "  - option: " + _q("(none considered)"),
        "    why_not: " + _q(why_not),
        "evidence:",
        "  - " + _q(_seat_command(pr_json)),
        "affects:",
        "  - " + _q("WS:" + ws_key),
        "confidence: low",
        "reversibility: easy",
        "decided_by: " + _q("UNVERIFIED"),
        f"decided_at: {_q(pr['day'])}",
        "---",
        "",
        "## What this draft is",
        "",
        "This is a knowledge-plane decision skeleton. It does not gate execution "
        "and this command does not write agentos/.",
        "",
    ]
    return relative, "\n".join(lines)


def _render_discovery(*, ws_key: str, pr: dict, pr_json: Path) -> tuple[str, str]:
    number = pr["number"]
    record_key = _draft_record_key(ws_key, number)
    relative = f"agentos/discoveries/DSC-{record_key}.md"
    claim = (
        f"UNFILLED discovery skeleton for seat-supplied PR #{number} ({pr['title']}). "
        "This is not a finding."
    )
    lines = [
        "---",
        f"key: {_q(record_key)}",
        f"claim: {_q(claim)}",
        f"falsifier: {_q(DISCOVERY_FALSIFIER_PLACEHOLDER)}",
        f"so_what: {_q(DISCOVERY_SO_WHAT_PLACEHOLDER)}",
        "kind: constraint",
        f"verified_at: {_q(pr['day'])}",
        f"verified_by: {_q(_seat_command(pr_json))}",
        "scope:",
        "  - " + _q("WS:" + ws_key),
        "confidence: suspected",
        "---",
        "",
        "## Unfilled admission gates",
        "",
        "falsifier is the token UNFILLED. It names no command, file:line, or #PR, "
        "so check_discovery rejects it (unfalsifiable-claim) until a human replaces it.",
        "",
        "so_what is the empty string. check_discovery rejects a missing or empty "
        "so_what (required-field). A non-empty stub would pass that checker, so this "
        "unfilled draft keeps so_what empty until a human writes what a future session "
        "does differently.",
        "",
        "This draft does not gate execution and this command does not write agentos/.",
        "",
    ]
    return relative, "\n".join(lines)


def _assert_handoff_parses(markdown: str, relative: str) -> None:
    match = FRONTMATTER_RE.match(markdown)
    if not match:
        raise DraftSchemaError("generated handoff has no frontmatter")
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise DraftSchemaError(f"generated handoff YAML did not parse: {exc}") from exc
    if not isinstance(data, dict):
        raise DraftSchemaError("generated handoff frontmatter is not a mapping")
    data["_body"] = match.group(2)
    hard = [item for item in check_handoff(data, Path(relative)) if item.hard]
    if hard:
        detail = "; ".join(item.message for item in hard)
        raise DraftSchemaError(detail)


def _load_generated(markdown: str, label: str) -> dict:
    match = FRONTMATTER_RE.match(markdown)
    if not match:
        raise DraftSchemaError(f"generated {label} has no frontmatter")
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise DraftSchemaError(f"generated {label} YAML did not parse: {exc}") from exc
    if not isinstance(data, dict):
        raise DraftSchemaError(f"generated {label} frontmatter is not a mapping")
    data["_body"] = match.group(2)
    return data


def _assert_decision_parses(markdown: str, relative: str) -> None:
    data = _load_generated(markdown, "decision")
    hard = [item for item in check_decision(data, Path(relative)) if item.hard]
    if hard:
        raise DraftSchemaError("; ".join(item.message for item in hard))


def _assert_discovery_stays_unfilled(markdown: str, relative: str) -> None:
    """Emit the skeleton only when falsifier and so_what are the hard failures.

    Any other hard error is a renderer bug. A valid discovery would mean the
    unfilled placeholders no longer block a commit, which is also a bug.
    """
    data = _load_generated(markdown, "discovery")
    hard = [item for item in check_discovery(data, Path(relative)) if item.hard]
    falsifier = [item for item in hard if "falsifier" in item.message]
    so_what = [item for item in hard if "so_what" in item.message]
    others = [item for item in hard if item not in falsifier and item not in so_what]
    if not falsifier or not so_what or others:
        detail = "; ".join(item.message for item in hard) or "discovery draft was valid"
        raise DraftSchemaError(
            "discovery draft must fail validation only on unfilled falsifier and so_what: "
            + detail
        )


def build_draft(pr_json: Path, repo: Path | None = None) -> dict:
    if repo is not None and not repo.is_dir():
        raise DraftError(f"--repo is not a directory: {repo}")
    document = _load_document(pr_json)
    kinds = _kinds(document)
    key = _workstream_key(document)
    pr = _pr_fields(document)
    model, model_defaulted = _optional_enum(document, "model", HANDOFF_MODEL, "local")
    ended, ended_defaulted = _optional_enum(document, "ended_because", HANDOFF_ENDED, "ci_handoff")
    session, session_defaulted = _session(document)
    object_type, names = _observe(pr["head_sha"], repo)
    file_rows = _file_rows(pr["files"], names)
    verified = _verified_items(pr_json, pr["head_sha"], pr["files"], object_type, names, repo)
    handoff_name = f"{key}-{pr['day']}.md"
    handoff_rel = f"agentos/handoffs/{handoff_name}"
    markdown = _render_handoff(
        key=key,
        session=session,
        model=model,
        ended=ended,
        pr=pr,
        file_rows=file_rows,
        verified=verified,
        object_type=object_type,
        repo=repo,
    )
    _assert_handoff_parses(markdown, handoff_rel)
    tool = _git_tool(repo)
    observations = []
    if object_type is not None:
        observations.append({
            "field": "pr.head_sha",
            "object_type": object_type,
            "command": f"GIT_NO_LAZY_FETCH=1 {tool} cat-file -t {pr['head_sha']}",
            "result": object_type,
        })
    drafted = {
        "schema": OUTPUT_SCHEMA,
        "input_schema": INPUT_SCHEMA,
        "ws_append": {
            "mode": "append",
            "path": f"agentos/workstreams/WS-{key}.md",
            "markdown": _render_append(
                key=key,
                pr=pr,
                file_rows=file_rows,
                object_type=object_type,
                session=session,
            ),
        },
        "handoff": {"path": handoff_rel, "markdown": markdown},
        "handoff_target_exists": (_ROOT / handoff_rel).is_file(),
        "unverified": _unverified_rows(
            object_type=object_type,
            model_defaulted=model_defaulted,
            ended_defaulted=ended_defaulted,
            session_defaulted=session_defaulted,
        ),
        "files": file_rows,
        "observations": observations,
        "handoff_verified_commands": verified,
    }
    if "draft-decision" in kinds:
        relative, body = _render_decision(ws_key=key, pr=pr, pr_json=pr_json)
        _assert_decision_parses(body, relative)
        drafted["decision"] = {
            "path": relative,
            "markdown": body,
            "target_exists": (_ROOT / relative).is_file(),
        }
    if "draft-discovery" in kinds:
        relative, body = _render_discovery(ws_key=key, pr=pr, pr_json=pr_json)
        _assert_discovery_stays_unfilled(body, relative)
        drafted["discovery"] = {
            "path": relative,
            "markdown": body,
            "target_exists": (_ROOT / relative).is_file(),
        }
    return drafted


def _is_inside_store(path: Path) -> bool:
    store = (_ROOT / "agentos").resolve()
    try:
        path.resolve(strict=False).relative_to(store)
    except ValueError:
        return False
    return True


def _write_out(path: Path, text: str) -> None:
    if _is_inside_store(path):
        raise DraftError("refusing to write into agentos/")
    if path.exists() and path.is_dir():
        raise DraftError("--out is a directory; pass a file path")
    parent = path.parent
    if not parent.is_dir():
        raise DraftError("--out parent directory does not exist")
    if _is_inside_store(parent):
        raise DraftError("refusing to write into agentos/")
    temporary = parent / f".agentos-records-draft-{os.getpid()}.tmp"
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentos_records_draft",
        description="Draft a WS append and a handoff skeleton from seat PR JSON.",
    )
    parser.add_argument("--pr-json", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--repo",
        type=Path,
        help="Git repository for cat-file and diff-tree. Default: this checkout.",
    )
    args = parser.parse_args(argv)
    try:
        text = json.dumps(
            build_draft(args.pr_json, repo=args.repo),
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        ) + "\n"
        if args.out is None:
            sys.stdout.write(text)
        else:
            _write_out(args.out, text)
    except DraftError as exc:
        print(f"agentos-records-draft: {exc}", file=sys.stderr)
        return 2
    except DraftSchemaError as exc:
        print(f"agentos-records-draft: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
