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
candidate merge tree should not be its own judge: ``ci-plan`` executes the
DEFAULT BRANCH's copy of this file, extracted as a git object
(``git show FETCH_HEAD:scripts/ci_docs_tier.py``), never the pull request's
copy.  On ``pull_request`` the workflow and planner themselves come from the
candidate head, so this guards against honest mistakes, not a hostile PR;
``ci-authority.yml``/``fences.yml`` remain the security boundary.  It
inspects only real git objects — the exact tested merge tree, its first
parent, and the BASE tree's manifest and code — and publishes a verdict the
planner binds to its own independently resolved changed-file list by digest.
Any doubt (unreadable manifest, odd status letter, rename, delete,
typechange, non-markdown path, markdown that base-tree code reads, a failed
consumer scan, or any internal error) publishes ``docs_tier: false`` and
exits 0: the fail-closed direction is simply the incumbent scoped behaviour.

Verdict fields are bounded on purpose: a path count, a digest, and one
example path.  The full list already travels as the planner's
``ci-changed-files`` artifact.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path

SCHEMA = "ci.docs_tier.v1"
# Must stay byte-identical to scripts/run_ci_pack.py's changed_files_digest
# over the same git output.  Pinned jointly by tests/test_ci_docs_tier.py.

MANIFEST_PATH = ".github/ci/legacy-jobs.yml"

# Narrative roots whose markdown is inert unless a consumer names it.
NARRATIVE_ROOTS = ("docs/", "research/", "agentos/")

# Markdown read as DATA through a path the code-derived scan below cannot see.
# Ordinary readers need no entry: derive_consumed_markdown finds literal
# paths, basenames and enumerated directories in the BASE tree's code.
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


# ─── code-derived consumers (B2) ────────────────────────────────────────────
#
# A curated list cannot keep up with ~10k first-party Python files, so the
# classifier DERIVES the consumed set at classify time from the BASE tree's
# own Python (read as git objects — never the candidate's files, never the
# working tree).  It is deliberately conservative: an over-claim only costs a
# docs PR its fast lane, an under-claim lets a suite go unrun.
#
# Claimed, per first-party ``*.py`` blob in the base tree:
#   * literal paths   — any ``<root>/...md`` text anywhere in the module
#     (strings, comments, docstrings), any string constant, or ``a / "docs" / "X.md"`` /
#     ``Path(..., "docs", "X.md")`` / ``os.path.join`` chain, that resolves to
#     ``<root>/...md`` (the anchor left of the first root segment is ignored,
#     so ``ROOT / "docs" / "X.md"`` and ``tmp / "docs" / "X.md"`` both claim);
#   * basenames       — every ``*.md`` file name mentioned in any string
#     constant: ``DOCS / "RUNBOOK.md"`` claims RUNBOOK.md even when DOCS is
#     not statically resolvable;
#   * listed dirs     — the directory a ``glob``/``rglob``/``iterdir``/
#     ``os.walk``/``os.listdir``/``os.scandir``/``glob.glob`` call enumerates,
#     when it resolves under a root and its pattern can yield ``.md``; and the
#     directory of a dynamic ``<dir> / f"{x}.md"`` join;
#   * module homes    — every Python file that itself lives under a narrative
#     root claims its own directory subtree (packets that verify themselves
#     with ``Path(__file__).parent.rglob("*.md")``);
#   * other code      — literal ``<root>/...md`` paths in shell, JS/TS, the
#     Makefile and every ``.github/`` file (workflow steps, the legacy
#     manifest's commands), by plain regex.
# Any unparseable module that could name a root fails the WHOLE scan closed.

_ROOT_NAMES = tuple(root.rstrip("/") for root in NARRATIVE_ROOTS)
_ROOT_MENTION_RE = re.compile(r"""['"/\\](?:docs|research|agentos)['"/\\]""")
_MD_NAME_RE = re.compile(r"[A-Za-z0-9_.\-]+\.md(?![A-Za-z0-9_])")
_OTHER_CODE_SUFFIXES = (".sh", ".bash", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx")
_OTHER_LITERAL_RE = re.compile(
    r"(?<![A-Za-z0-9_.\-/])(?:docs|research|agentos)/[A-Za-z0-9_./\-]*?\.md(?![A-Za-z0-9_])"
)


_ATTR_TRAVERSALS = frozenset({"glob", "rglob", "iterdir"})
_FUNC_TRAVERSALS = frozenset({"glob", "iglob", "listdir", "scandir", "walk"})
_PATH_CTORS = frozenset({"Path", "PurePath", "PurePosixPath", "PosixPath"})
_PATTERN_SUFFIX_RE = re.compile(r"\.([A-Za-z0-9_]{1,8})$")
_ENV_FANOUT = 8
_RESOLVE_DEPTH = 6
SCAN_BLOB_BYTES_LIMIT = 512 * 1024 * 1024


@dataclass
class ConsumedMarkdown:
    """The base tree's code-derived markdown consumers."""

    literals: set[str] = field(default_factory=set)
    basenames: set[str] = field(default_factory=set)
    directories: set[str] = field(default_factory=set)
    provenance: dict[str, str] = field(default_factory=dict)

    def claims(self, path: str) -> str | None:
        """Why ``path`` is consumed, or ``None`` when no code reads it."""
        if path in self.literals:
            return f"named literally by {self.provenance.get(path, 'first-party code')}"
        name = path.rsplit("/", 1)[-1]
        if name in self.basenames:
            return f"basename {name} is named by {self.provenance.get('basename:' + name, 'first-party code')}"
        parts = path.split("/")
        for depth in range(1, len(parts)):
            prefix = "/".join(parts[:depth])
            if prefix in self.directories:
                return (
                    f"under {prefix}/, which "
                    f"{self.provenance.get('dir:' + prefix, 'first-party code')} enumerates"
                )
        return None

    def merge(self, other: "ConsumedMarkdown", source: str) -> None:
        for rel in other.literals:
            self.literals.add(rel)
            self.provenance.setdefault(rel, source)
        for name in other.basenames:
            self.basenames.add(name)
            self.provenance.setdefault("basename:" + name, source)
        for rel in other.directories:
            self.directories.add(rel)
            self.provenance.setdefault("dir:" + rel, source)


def _str_const(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _join(left: str, right: str) -> str:
    if not left:
        return right
    return left.rstrip("/") + "/" + right.lstrip("/")


def _resolve(
    node: ast.AST, env: dict[str, list[ast.AST]], depth: int = 0
) -> list[tuple[str, bool]]:
    """Candidate ``(path, complete)`` strings a path expression can denote.

    ``complete`` is False when an unresolvable piece truncated the path; an
    unresolvable LEFT anchor (``ROOT``, ``Path(__file__).parent``) resolves
    to the empty string so the narrative tail still surfaces.
    """
    if depth > _RESOLVE_DEPTH:
        return [("", False)]
    text = _str_const(node)
    if text is not None:
        return [(text, True)]
    if isinstance(node, ast.JoinedStr):
        prefix = ""
        for value in node.values:
            piece = _str_const(value)
            if piece is None:
                return [(prefix, False)]
            prefix += piece
        return [(prefix, True)]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        out: list[tuple[str, bool]] = []
        for left, left_complete in _resolve(node.left, env, depth + 1):
            if left and not left_complete:
                out.append((left, False))
                continue
            for right, right_complete in _resolve(node.right, env, depth + 1):
                out.append((_join(left, right), right_complete))
        return out
    if isinstance(node, ast.Call):
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        is_join = name == "join" and isinstance(func, ast.Attribute) and (
            ast.unparse(func.value) in {"os.path", "path", "posixpath"}
        )
        if (name in _PATH_CTORS or is_join) and node.args:
            acc: list[tuple[str, bool]] = [("", True)]
            for arg in node.args:
                nxt: list[tuple[str, bool]] = []
                for prefix, complete in acc:
                    if prefix and not complete:
                        nxt.append((prefix, False))
                        continue
                    for piece, piece_complete in _resolve(arg, env, depth + 1):
                        nxt.append((_join(prefix, piece), piece_complete))
                acc = nxt[: _ENV_FANOUT * _ENV_FANOUT]
            return acc
        if name in {"resolve", "absolute", "expanduser"} and isinstance(func, ast.Attribute):
            return _resolve(func.value, env, depth + 1)
    if isinstance(node, ast.Name) and node.id in env:
        out = []
        for value in env[node.id][:_ENV_FANOUT]:
            out.extend(_resolve(value, env, depth + 1))
        return out or [("", False)]
    if isinstance(node, ast.Attribute) and node.attr in env and node.attr != "parent":
        out = []
        for value in env[node.attr][:_ENV_FANOUT]:
            out.extend(_resolve(value, env, depth + 1))
        return out or [("", False)]
    return [("", False)]


def _narrative_tail(path: str) -> str | None:
    """``path`` from its first narrative-root segment, if it has one there.

    Only the FIRST non-empty segment may be the root: ``engine/docs/x.md`` is
    not narrative, but an anchor-less ``docs/x.md`` (or ``./docs/x.md``) is.
    """
    parts = [part for part in path.replace("\\", "/").split("/") if part not in ("", ".")]
    if parts and parts[0] in _ROOT_NAMES:
        return "/".join(parts)
    return None


def _static_prefix(path: str) -> str:
    kept: list[str] = []
    for part in path.split("/"):
        if any(ch in part for ch in "*?[{"):
            break
        kept.append(part)
    return "/".join(kept)


def _pattern_can_yield_markdown(pattern: str | None) -> bool:
    if pattern is None:
        return True
    if ".md" in pattern:
        return True
    tail = pattern.rsplit("/", 1)[-1]
    match = _PATTERN_SUFFIX_RE.search(tail)
    if match is None:
        return True
    # A brace/set suffix ("*.{md,txt}", "*.m?") is not a literal suffix.
    return any(ch in match.group(0) for ch in "*?[{")


def _bindings(tree: ast.Module) -> dict[str, list[ast.AST]]:
    env: dict[str, list[ast.AST]] = {}
    for node in ast.walk(tree):
        targets: list[ast.AST] = []
        value: ast.AST | None = None
        if isinstance(node, ast.Assign):
            targets, value = list(node.targets), node.value
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and node.value is not None:
            targets, value = [node.target], node.value
        elif isinstance(node, ast.NamedExpr):
            targets, value = [node.target], node.value
        elif isinstance(node, (ast.For, ast.comprehension)):
            iterable = node.iter
            values = (
                list(iterable.elts)
                if isinstance(iterable, (ast.List, ast.Tuple, ast.Set))
                else [iterable]
            )
            if isinstance(node.target, ast.Name):
                env.setdefault(node.target.id, []).extend(values)
            continue
        if value is None:
            continue
        for target in targets:
            for leaf in target.elts if isinstance(target, (ast.Tuple, ast.List)) else [target]:
                key = (
                    leaf.id
                    if isinstance(leaf, ast.Name)
                    else leaf.attr if isinstance(leaf, ast.Attribute) else None
                )
                if key:
                    env.setdefault(key, []).append(value)
    return env


def _traversal(node: ast.Call, env: dict[str, list[ast.AST]]) -> tuple[ast.AST | None, str | None] | None:
    """``(receiver, pattern)`` for a directory-enumerating call, else None."""
    func = node.func
    if isinstance(func, ast.Attribute):
        owner = func.value
        module = owner.id if isinstance(owner, ast.Name) else ast.unparse(owner)
        if func.attr in _FUNC_TRAVERSALS and module in {"glob", "os"}:
            return _func_traversal(func.attr, node, env)
        if func.attr in _ATTR_TRAVERSALS:
            pattern = None
            if func.attr != "iterdir" and node.args:
                candidates = _resolve(node.args[0], env)
                if len(candidates) == 1 and candidates[0][1]:
                    pattern = candidates[0][0]
            return owner, pattern
        return None
    if isinstance(func, ast.Name) and func.id in _FUNC_TRAVERSALS:
        return _func_traversal(func.id, node, env)
    return None


def _func_traversal(label: str, node: ast.Call, env) -> tuple[ast.AST | None, str | None]:
    receiver = node.args[0] if node.args else None
    if label in {"glob", "iglob"} and receiver is not None:
        candidates = _resolve(receiver, env)
        pattern = candidates[0][0] if len(candidates) == 1 and candidates[0][1] else None
        return receiver, pattern
    return receiver, None


def _dynamic_markdown_join(node: ast.AST) -> bool:
    """``<dir> / f"{x}.md"`` or ``<dir> / (x + ".md")``: a computed md name."""
    if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)):
        return False
    right = node.right
    if isinstance(right, ast.JoinedStr) and len(right.values) > 1:
        tail = _str_const(right.values[-1])
        return tail is not None and tail.endswith(".md")
    if isinstance(right, ast.BinOp) and isinstance(right.op, ast.Add):
        tail = _str_const(right.right)
        return tail is not None and tail.endswith(".md")
    return False


def scan_python_source(text: str, module_path: str = "") -> ConsumedMarkdown:
    """Narrative markdown one first-party module can read.

    Raises ``SyntaxError`` for an unparseable module that could name a root;
    callers fail the whole scan closed on it.
    """
    found = ConsumedMarkdown()
    home = _narrative_tail(module_path.rsplit("/", 1)[0]) if "/" in module_path else None
    if home:
        found.directories.add(home)
    rooted = bool(_ROOT_MENTION_RE.search(text))
    if not rooted and ".md" not in text:
        return found
    # Any literal narrative path anywhere in the text — strings, comments,
    # docstrings — is claimed.  Comment citations over-claim on purpose: the
    # cost is a lost fast lane, never an unrun suite.
    for match in _OTHER_LITERAL_RE.finditer(text):
        found.literals.add(match.group(0))
    tree = ast.parse(text)
    env = _bindings(tree) if rooted else {}
    for node in ast.walk(tree):
        text_value = _str_const(node)
        if text_value is not None and ".md" in text_value:
            found.basenames.update(_MD_NAME_RE.findall(text_value))
            for token in text_value.split():
                tail = _narrative_tail(token.strip("'\"`()[],;:"))
                if tail and tail.endswith(".md") and not any(ch in tail for ch in "*?[{"):
                    found.literals.add(tail)
            continue
        if not rooted:
            continue
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) or (
            isinstance(node, ast.Call)
            and (getattr(node.func, "id", None) in _PATH_CTORS or getattr(node.func, "attr", None) == "join")
        ):
            for candidate, complete in _resolve(node, env):
                tail = _narrative_tail(candidate)
                if tail and complete and tail.endswith(".md") and not any(ch in tail for ch in "*?[{"):
                    found.literals.add(tail)
            if _dynamic_markdown_join(node):
                for candidate, _complete in _resolve(node.left, env):  # type: ignore[attr-defined]
                    tail = _narrative_tail(candidate)
                    if tail:
                        found.directories.add(_static_prefix(tail).rstrip("/"))
        if isinstance(node, ast.Call):
            traversal = _traversal(node, env)
            if traversal is None:
                continue
            receiver, pattern = traversal
            if not _pattern_can_yield_markdown(pattern):
                continue
            if pattern:
                tail = _narrative_tail(pattern)
                if tail:
                    found.directories.add(_static_prefix(tail).rstrip("/"))
            if receiver is None:
                continue
            for candidate, _complete in _resolve(receiver, env):
                tail = _narrative_tail(candidate)
                if tail:
                    found.directories.add(_static_prefix(tail).rstrip("/"))
    found.directories.discard("")
    return found


def _is_other_code(path: str) -> bool:
    return (
        path.endswith(_OTHER_CODE_SUFFIXES)
        or path.startswith(".github/")
        or path == "Makefile"
    )


def scan_other_source(text: str) -> ConsumedMarkdown:
    found = ConsumedMarkdown()
    for match in _OTHER_LITERAL_RE.finditer(text):
        found.literals.add(match.group(0))
    return found


def _tree_python_blobs(workspace: Path, tree: str) -> list[tuple[str, str]]:
    raw = _git(workspace, "ls-tree", "-r", "-z", "--full-tree", tree)
    blobs: list[tuple[str, str]] = []
    for record in raw.split("\0"):
        if not record:
            continue
        meta, _tab, path = record.partition("\t")
        fields = meta.split()
        if len(fields) == 3 and fields[1] == "blob" and (
            path.endswith(".py") or _is_other_code(path)
        ):
            blobs.append((fields[2], path))
    return blobs


def _prefetch_missing(workspace: Path, oids: list[str]) -> None:
    """Best-effort ONE-request fetch of blobs a blob:none clone lacks.

    ``git cat-file --batch`` would lazily fetch each missing blob in its own
    round trip.  Failure here is harmless: the batch read below still fetches
    lazily, and any blob it cannot read fails the scan closed.
    """
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1")
    check = subprocess.run(
        ["git", "-C", str(workspace), "cat-file", "--batch-check=%(objectname) %(objecttype)"],
        input="".join(oid + "\n" for oid in oids),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    missing = [line.split()[0] for line in check.stdout.splitlines() if line.endswith(" missing")]
    if not missing:
        return
    subprocess.run(
        ["git", "-C", str(workspace), "fetch", "--quiet", "--no-tags",
         "--no-write-fetch-head", "--recurse-submodules=no",
         "--filter=blob:none", "origin", "--stdin"],
        input="".join(oid + "\n" for oid in missing),
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )


def derive_consumed_markdown(workspace: Path, tree: str) -> ConsumedMarkdown:
    """Scan every first-party ``*.py`` blob of ``tree`` (the BASE commit).

    Raises on any git or parse trouble; :func:`classify_workspace` turns that
    into a negative verdict.
    """
    blobs = _tree_python_blobs(workspace, tree)
    if not any(path.endswith(".py") for _oid, path in blobs):
        raise ValueError("base tree carries no Python to scan")
    _prefetch_missing(workspace, [oid for oid, _ in blobs])
    batch = subprocess.run(
        ["git", "-C", str(workspace), "cat-file", "--batch"],
        input=b"".join(oid.encode() + b"\n" for oid, _ in blobs),
        capture_output=True,
        check=True,
    ).stdout
    if len(batch) > SCAN_BLOB_BYTES_LIMIT:
        raise ValueError("base Python estate exceeds the scan byte limit")
    consumed = ConsumedMarkdown()
    offset = 0
    for oid, path in blobs:
        header_end = batch.index(b"\n", offset)
        header = batch[offset:header_end].split()
        if len(header) != 3 or header[0].decode() != oid or header[1] != b"blob":
            raise ValueError(f"unreadable base blob for {path}")
        size = int(header[2])
        body = batch[header_end + 1 : header_end + 1 + size]
        offset = header_end + 1 + size + 1
        text = body.decode("utf-8", errors="replace").replace("\x00", "")
        if not path.endswith(".py"):
            consumed.merge(scan_other_source(text), path)
            continue
        try:
            consumed.merge(scan_python_source(text, path), path)
        except SyntaxError as exc:
            raise ValueError(f"unparseable base module {path}: {exc.msg}") from exc
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
    if eligible:
        # Only a diff that already passed every cheap check pays for the
        # base-tree consumer scan; any scan trouble refuses the tier.
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                derived = derive_consumed_markdown(workspace, base)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, ValueError) as exc:
            eligible, reason = False, _bounded(f"classifier-error: consumer scan failed ({exc})")
        else:
            for path in paths:
                why = derived.claims(path)
                if why is not None:
                    eligible, reason = False, _bounded(f"{path} is read by code: {why}")
                    break
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
