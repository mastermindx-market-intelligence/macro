"""SNI-local DRAFT literal copy guard for acceptance rows A14 and A30.

This module extends the existing A14/A30 markdown copy guard
(research/single_name_intelligence/acceptance/sni_copy_guard.py, NOT edited
here) to JSON string values and Python string constants under the SNI tree.
It reuses that guard's rule callables by import; it does not copy or fork
the rule tables. Markdown stays with sni_copy_guard; product UI and the
rendered site remain out of scope (gated on a ruling this lane does not hold).

It CONSUMES owner-supplied file text under research/single_name_intelligence/.
It does not mint, derive, or guess canonical HK/US issuer or security
identifiers from a ticker, name, code, or CIK; unknown identity stays
UNRESOLVED / null. Identity ids are caller-supplied opaque strings owned by
Stock Identity / Data OS. It does not re-implement Data OS identity, Company
Event/Earnings, FIF, Capital Structure, Stock Identity, Options, Research
Vault, or qledger/Evaluation.

This is a lexical, descriptive check of copy that could reach a page. It is
never a forecast, never causal, never a claim of news impact (A24), and an
unestimable family is outside this module (no default 50/50, A25). Nothing
here feeds or is described as feeding a ranker, gate, sizer, signal,
escalation, or trade path. Every authority flag is literal false; a caller
that tries to set any of them true is refused (raise). The AUTHORITY_FLAGS
MappingProxyType + refuse_nonfalse_authority idiom is copied from
research/single_name_intelligence/common/sni_join_guard.py.

Stdlib + the existing sni_copy_guard import only: no network, no writes, no
wall clock. scan_tree is the only function that reads files; it reads only
under the caller-given root and skips SKIPPED_DIR_PARTS trees (sealed or
deliberately adversarial bytes). Files that fail to decode or parse are
skipped, not findings.
"""
from __future__ import annotations

import ast
import fnmatch
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping, Sequence

_MODULE_DIR = Path(__file__).resolve().parent
if str(_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR))

from sni_copy_guard import (  # noqa: E402
    rule_a14_flow_intent,
    rule_a30_forecast_success,
)

AUTHORITY_FLAGS: Mapping[str, bool] = MappingProxyType(
    {
        "rank_authority": False,
        "gate_authority": False,
        "size_authority": False,
        "signal_authority": False,
        "escalation_authority": False,
        "trade_authority": False,
    }
)


def refuse_nonfalse_authority(flags: Mapping[str, object] | None = None) -> None:
    """Refuse any authority flag that is not literal False.

    Idiom copied from research/single_name_intelligence/common/sni_join_guard.py
    (which copied it from event_response/s2_seal.py); this module does not
    import those owners.
    """
    for key, value in AUTHORITY_FLAGS.items():
        if value is not False:
            raise ValueError(
                f"AUTHORITY_FLAGS[{key!r}] is {value!r}; every authority flag "
                "must be literal False"
            )
    if flags is None:
        return
    if not isinstance(flags, Mapping):
        raise ValueError("authority flags is not a mapping")
    for key, value in flags.items():
        if value is not False:
            raise ValueError(
                f"authority_flags[{key!r}] is {value!r}; "
                "every authority flag must be literal False"
            )


RULE_A14 = "A14"
RULE_A30 = "A30"
EXCERPT_LIMIT = 80

# The reused rule callables, in the same A14-then-A30 order check_text uses.
DEFAULT_RULES: Mapping[str, object] = MappingProxyType(
    {
        RULE_A14: rule_a14_flow_intent,
        RULE_A30: rule_a30_forecast_success,
    }
)

# Directories whose files scan_tree never reads: sealed run outputs and
# deliberately adversarial test fixtures.
SKIPPED_DIR_PARTS: tuple[tuple[str, ...], ...] = (
    ("runs",),
    ("tests", "fixtures"),
)

DEFAULT_INCLUDE: tuple[str, ...] = ("*.json", "*.py")

_SIMPLE_KEY_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
)


@dataclass(frozen=True)
class Finding:
    """One lexical copy finding at a literal location."""

    location: str
    rule_id: str
    excerpt: str


def _json_key_suffix(key: str) -> str:
    """Dot form for simple keys, bracket form otherwise (JSONPath-like)."""
    if key and not key[0].isdigit() and set(key) <= _SIMPLE_KEY_CHARS:
        return f".{key}"
    escaped = key.replace("\\", "\\\\").replace("'", "\\'")
    return f"['{escaped}']"


def json_strings(
    obj: object, path: str = "$"
) -> tuple[tuple[str, str], ...]:
    """Every string VALUE in a decoded JSON object, with its location.

    Dicts walk keys in sorted order (str keys first, then non-str keys;
    within each group by str representation); lists walk in index order.
    Keys are never returned as text. Non-str dict keys do not raise: their
    values are still walked with a path that uses the key's repr. Cyclic
    input is handled by tracking the `id()` of every dict/list/tuple on
    the current recursion path; a container already on the path is
    skipped. Deterministic for equal input.
    """
    out: list[tuple[str, str]] = []
    _walk_json(obj, path, frozenset(), out)
    return tuple(out)


def _walk_json(
    obj: object, path: str, path_ids: frozenset[int], out: list[tuple[str, str]]
) -> None:
    if isinstance(obj, str):
        out.append((path, obj))
        return
    if not isinstance(obj, (dict, list, tuple)):
        return
    if id(obj) in path_ids:
        return
    new_ids = path_ids | {id(obj)}
    if isinstance(obj, dict):
        keys = sorted(
            obj,
            key=lambda k: (
                not isinstance(k, str),
                str(k) if not isinstance(k, str) else k,
            ),
        )
        for key in keys:
            if isinstance(key, str):
                child_path = path + _json_key_suffix(key)
            else:
                child_path = f"{path}[{key!r}]"
            _walk_json(obj[key], child_path, new_ids, out)
        return
    for index, item in enumerate(obj):
        _walk_json(item, f"{path}[{index}]", new_ids, out)


def _docstring_constant(stmts: Sequence[ast.stmt]) -> ast.Constant | None:
    """The Constant str of a leading docstring expression, else None."""
    if not stmts:
        return None
    first = stmts[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return first.value
    return None


def _is_name_main_guard(node: ast.If) -> bool:
    """True for `if __name__ == "__main__":` (either operand order)."""
    test = node.test
    if (
        not isinstance(test, ast.Compare)
        or len(test.ops) != 1
        or not isinstance(test.ops[0], ast.Eq)
        or len(test.comparators) != 1
    ):
        return False
    left = test.left
    right = test.comparators[0]
    for a, b in ((left, right), (right, left)):
        if (
            isinstance(a, ast.Name)
            and a.id == "__name__"
            and isinstance(b, ast.Constant)
            and b.value == "__main__"
        ):
            return True
    return False


def python_strings(source: str) -> tuple[tuple[int, str], ...]:
    """Every string Constant in Python source, minus docstrings and __main__.

    Module, class, and function docstrings are excluded. String constants
    inside `if __name__ == "__main__":` blocks are excluded. F-string literal
    parts appear as their constant segments (formatted holes carry no
    constant). Result is sorted by (lineno, col_offset); deterministic.
    """
    tree = ast.parse(source)
    excluded: set[int] = set()
    found: list[tuple[int, int, str]] = []

    def visit(node: ast.AST) -> None:
        if isinstance(node, ast.If) and _is_name_main_guard(node):
            return
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str) and id(node) not in excluded:
                found.append((node.lineno, node.col_offset, node.value))
            return
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            doc = _docstring_constant(node.body)
            if doc is not None:
                excluded.add(id(doc))
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(tree)
    return tuple((lineno, text) for lineno, _col, text in sorted(found))


def _excerpt(text: str) -> str:
    return " ".join(text.split())[:EXCERPT_LIMIT]


def scan_text_items(
    items: Iterable[tuple[str, str]], *, rules: Mapping[str, object]
) -> tuple[Finding, ...]:
    """Apply each rule callable to each (location, text) item.

    A rule fires when it returns a truthy match (the reused guard rules
    return a term pair or None). Findings keep item order, then rule
    insertion order (A14 before A30 in DEFAULT_RULES).
    """
    refuse_nonfalse_authority()
    findings: list[Finding] = []
    for location, text in items:
        for rule_id, rule in rules.items():
            if rule(text):
                findings.append(
                    Finding(
                        location=location,
                        rule_id=rule_id,
                        excerpt=_excerpt(text),
                    )
                )
    return tuple(findings)


def _skipped(rel_parts: Sequence[str]) -> bool:
    for skip in SKIPPED_DIR_PARTS:
        span = len(skip)
        for i in range(len(rel_parts) - span + 1):
            if tuple(rel_parts[i : i + span]) == skip:
                return True
    return False


def scan_tree(
    root: pathlib.Path, *, include: tuple[str, ...] = DEFAULT_INCLUDE
) -> tuple[Finding, ...]:
    """Scan JSON and Python files under root with the reused A14/A30 rules.

    The only function here that reads files. Reads only under root, never
    writes, and visits matching files in sorted relative-path order.
    Symlinks are skipped: symlinked files are not read, symlinked
    directories are not descended into, and a file reached through a
    symlinked directory is not reported. Each real file is scanned at
    most once (dedup on `os.path.realpath`). Files under SKIPPED_DIR_PARTS
    directories are skipped without being read. JSON locations are
    `path#$.json.path`; Python locations are `path:lineno`.
    """
    refuse_nonfalse_authority()
    resolved = Path(root).resolve()
    chosen: list[str] = []
    seen_realpaths: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(resolved, followlinks=False):
        dirpath_path = Path(dirpath)
        rel_dir = dirpath_path.relative_to(resolved)
        kept_dirs = [
            d for d in dirnames
            if not (dirpath_path / d).is_symlink()
            and not _skipped(rel_dir.parts + (d,))
        ]
        dirnames[:] = kept_dirs
        for name in filenames:
            candidate = dirpath_path / name
            if candidate.is_symlink():
                continue
            if not candidate.is_file():
                continue
            rel = candidate.relative_to(resolved)
            if _skipped(rel.parts):
                continue
            if not any(fnmatch.fnmatch(candidate.name, pattern) for pattern in include):
                continue
            realpath = str(candidate.resolve())
            if realpath in seen_realpaths:
                continue
            seen_realpaths.add(realpath)
            chosen.append(rel.as_posix())
    findings: list[Finding] = []
    for rel in sorted(chosen):
        absolute = resolved / rel
        try:
            text = absolute.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if fnmatch.fnmatch(rel, "*.json"):
            try:
                obj = json.loads(text)
            except (json.JSONDecodeError, ValueError):
                continue
            items = (
                (f"{rel}#{json_path}", value)
                for json_path, value in json_strings(obj)
            )
        else:
            try:
                items = tuple(
                    (f"{rel}:{lineno}", value)
                    for lineno, value in python_strings(text)
                )
            except SyntaxError:
                continue
        findings.extend(scan_text_items(items, rules=DEFAULT_RULES))
    return tuple(findings)
