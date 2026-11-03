"""SNI-local DRAFT AST scanner for ticker/company strategy branches (A36).

This module is an SNI-local DRAFT contract. It CONSUMES owner-supplied
profile facts (ticker, listing, sector_etf) from coverage/stress YAML
written by the research program. It does not re-implement Data OS identity,
Company Event/Earnings, FIF, Capital Structure, Stock Identity, Options,
Research Vault, or qledger/Evaluation. Identity ids are caller-supplied
opaque strings owned by Stock Identity / Data OS; this scanner never
mints, derives, or guesses canonical HK/US issuer or security identifiers
from a ticker, name, code, or CIK. Unknown identity stays UNRESOLVED / null.

Nothing here feeds a ranker, gate, sizer, signal, escalation, or trade path.
Every authority flag is literal false. A caller that tries to set any of
them true is refused (raise). Residuals and stress statistics mentioned in
scanned code stay descriptive; this scanner makes no causal or news-impact
claim (A24). An unreadable profile ABSTAINS from contributing literals
(named reason in PROFILE_LOAD_GAPS) and never invents a default 50/50 (A25).

Stdlib ``ast`` only for Python. Scanned SNI modules are never imported.
Profiles are read as text and parsed with PyYAML when importable, else the
same indent-based subset as ``us_stress.stress_set._minimal_yaml_load``.
The scanner is not that owner: it copies the subset so this file stays
pure (files are only read; no subprocess, socket, or scanned-module import).

Rules (a finding is a ticker/company string in a DECISION position)
------------------------------------------------------------------
* ``compare``: an ``ast.Compare`` with a ticker string constant on either
  side. This includes ``in`` / ``not in`` against a tuple, list, or set of
  constants (or ``set``/``frozenset``/``tuple``/``list`` constructed from
  one). One finding per ticker literal involved.
* ``match``: a ``match`` case pattern constant (``MatchValue`` and nested
  ``MatchOr`` / ``MatchAs`` / sequence / mapping / class patterns).
* ``dispatch``: a dict literal whose keys include a ticker constant, when
  that dict is subscripted or ``.get()``-ed in the same module (a dispatch
  table). Assigned names and inline ``{...}[k]`` / ``{...}.get(k)`` count.
  One finding per ticker key.
* ``call_branch``: ``str.startswith`` / ``endswith`` / ``upper()==``
  compositions against a ticker constant (receiver or argument).
  ``upper()==`` is classified as ``call_branch``, not ``compare``.

Not findings
------------
Docstrings, comments, f-strings used only for messages or paths, and
module-level constants that are never compared. A path string such as
``data/yahoo/BABA.parquet`` is not a ticker literal. Iteration over a
tuple of names without ``in``/compare is not a finding. A branch on a
value read from data (``if row["symbol"] == profile_field``) is out of
scope for this static scan.

Allowlist
---------
``ALLOWLIST`` is a tuple of ``(path, kind, literal, justification)``.
Path is repo-relative posix, kind is line-independent, literal is
case-insensitive. It is only for findings that are genuinely not strategy
branches (for example a fixture builder). An entry that matches nothing
is itself an error (``StaleAllowlistError``). S1/S2 reference-study
Alibaba/Tencent branches are not allowlisted; tests pin them as expected.
"""
from __future__ import annotations

import ast
import fnmatch
from collections import defaultdict
from pathlib import Path
from typing import Iterable, NamedTuple

AUTHORITY_FLAGS = {
    "rank_authority": False,
    "gate_authority": False,
    "size_authority": False,
    "signal_authority": False,
    "escalation_authority": False,
    "trade_authority": False,
}

_AUTHORITY_CANONICAL = {name.casefold(): name for name in AUTHORITY_FLAGS}


def refuse_authority_override(**kwargs):
    """Return the all-false flag map. Refuse any flag not literal False."""
    for key, value in kwargs.items():
        folded = key.strip().casefold() if isinstance(key, str) else None
        if folded in _AUTHORITY_CANONICAL:
            if key != _AUTHORITY_CANONICAL[folded] or value is not False:
                raise ValueError("authority flag %s must be literal False" % key)
        elif key not in AUTHORITY_FLAGS:
            raise ValueError("unknown authority flag: %s" % key)
        elif value is not False:
            raise ValueError("authority flag %s must be literal False" % key)
    return dict(AUTHORITY_FLAGS)


KINDS = frozenset({"compare", "match", "dispatch", "call_branch"})

# Hand-typed Mag-7 + HK reference-product tokens. Case-insensitive in use.
_HAND_TYPED = (
    "AAPL",
    "MSFT",
    "GOOGL",
    "GOOG",
    "AMZN",
    "META",
    "NVDA",
    "TSLA",
    "BABA",
    "9988",
    "9988.HK",
    "0700",
    "700",
    "0700.HK",
    "TCEHY",
    "TME",
    "KWEB",
    "ALIBABA",
    "TENCENT",
    "APPLE",
    "MICROSOFT",
    "ALPHABET",
    "AMAZON",
    "NVIDIA",
    "TESLA",
)

_PROFILE_VALUE_FIELDS = frozenset({"ticker", "listing", "sector_etf"})

_PROFILE_LOCATIONS = (
    "research/single_name_intelligence/us_stress/profiles",
    "config/single_name_intelligence/coverage_profiles",
)

DEFAULT_SCOPE_GLOBS = ("research/single_name_intelligence/**/*.py",)

# (path, kind, literal, justification). Empty: no non-strategy branch needs it.
ALLOWLIST: tuple[tuple[str, str, str, str], ...] = ()

SNI_ROOT_REL = "research/single_name_intelligence"


class Finding(NamedTuple):
    path: str
    line: int
    kind: str
    literal: str
    snippet: str


class StaleAllowlistError(ValueError):
    """An ALLOWLIST entry matched no finding."""


def _repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[3]


def _posix(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _strip_inline_comment(line: str) -> str:
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i].rstrip()
    return line.rstrip()


def _parse_scalar(raw: str):
    s = raw.strip()
    if s == "" or s == "~" or s == "null":
        return None
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        return s[1:-1]
    if s[0] in "0123456789.+-" and not s.startswith(".-") and s not in ("+", "-", "."):
        try:
            if any(c in s for c in ".eE"):
                return float(s)
            return int(s)
        except ValueError:
            pass
    return s


def _split_key_value(content: str):
    in_single = False
    in_double = False
    for i, ch in enumerate(content):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == ":" and not in_single and not in_double:
            return content[:i].strip(), content[i + 1 :].strip()
    return None, content


def _minimal_yaml_load(text: str):
    """Indent-based subset parser copied from stress_set._minimal_yaml_load.

    Limitation: no anchors, aliases, merge keys, flow {}/[], multiline
    scalars (|/>), tags, or '---' documents. Used only when PyYAML is
    missing so this scanner never imports a scanned SNI module.
    """
    lines = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        line = _strip_inline_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        lines.append((indent, line.strip()))
    n = len(lines)

    def parse_list(i, list_indent):
        result = []
        while i < n and lines[i][0] == list_indent and lines[i][1].startswith("- "):
            item = lines[i][1][2:].strip()
            if item == "":
                if i + 1 < n and lines[i + 1][0] > list_indent:
                    nxt_indent, nxt = lines[i + 1]
                    if nxt.startswith("- "):
                        child, i = parse_list(i + 1, nxt_indent)
                        result.append(child)
                    else:
                        child, i = parse_map(i + 1, nxt_indent)
                        result.append(child)
                else:
                    result.append(None)
                    i += 1
            else:
                key, rest = _split_key_value(item)
                if key is not None:
                    child = {}
                    if rest != "":
                        child[key] = _parse_scalar(rest)
                    else:
                        child[key] = None
                    i += 1
                    if i < n and lines[i][0] > list_indent and not lines[i][1].startswith("- "):
                        more, i = parse_map(i, lines[i][0])
                        child.update(more)
                    result.append(child)
                else:
                    result.append(_parse_scalar(item))
                    i += 1
        return result, i

    def parse_map(i, map_indent):
        result = {}
        while i < n and lines[i][0] == map_indent and not lines[i][1].startswith("- "):
            key, rest = _split_key_value(lines[i][1])
            if key is None:
                raise ValueError("unparsable yaml line: %s" % lines[i][1])
            if rest != "":
                result[key] = _parse_scalar(rest)
                i += 1
            elif i + 1 < n and lines[i + 1][0] > map_indent:
                nxt_indent, nxt = lines[i + 1]
                if nxt.startswith("- "):
                    child, i = parse_list(i + 1, nxt_indent)
                    result[key] = child
                else:
                    child, i = parse_map(i + 1, nxt_indent)
                    result[key] = child
            else:
                result[key] = None
                i += 1
        return result, i

    if n == 0:
        return {}
    obj, _ = parse_map(0, lines[0][0])
    return obj


def _load_yaml_text(text: str):
    try:
        import yaml
    except ImportError:
        yaml = None
    if yaml is not None:
        try:
            return yaml.safe_load(text)
        except Exception:
            pass
    return _minimal_yaml_load(text)


def _collect_profile_fields(obj, out: set) -> None:
    if isinstance(obj, dict):
        field = obj.get("field")
        if isinstance(field, str) and field.strip() in _PROFILE_VALUE_FIELDS:
            value = obj.get("value")
            if isinstance(value, str) and value.strip():
                out.add(value.strip())
        for key, value in obj.items():
            if key in _PROFILE_VALUE_FIELDS and isinstance(value, str) and value.strip():
                out.add(value.strip())
            _collect_profile_fields(value, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_profile_fields(item, out)


def _profile_yaml_paths(repo_root: Path) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for rel in _PROFILE_LOCATIONS:
        base = repo_root / rel
        if not base.is_dir():
            continue
        try:
            children = sorted(base.iterdir())
        except OSError:
            continue
        for path in children:
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".yml", ".yaml"}:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            paths.append(path)
    return paths


PROFILE_LOAD_GAPS: list[str] = []


def load_profile_ticker_literals(repo_root: Path | None = None) -> frozenset[str]:
    """Read ticker/listing/sector_etf values from the A36 profile YAMLs.

    Never raises on a single unreadable profile: the path is recorded in
    PROFILE_LOAD_GAPS and scanning continues with the literals already found.
    """
    root = Path(repo_root) if repo_root is not None else _repo_root_from_here()
    found: set[str] = set()
    paths = _profile_yaml_paths(root)
    if not paths:
        PROFILE_LOAD_GAPS.append("no profile YAML files on disk under %s" % root)
        return frozenset()
    for path in paths:
        rel = _posix(root, path)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            PROFILE_LOAD_GAPS.append("%s: could not read (%s)" % (rel, exc))
            continue
        try:
            obj = _load_yaml_text(text)
        except Exception as exc:  # noqa: BLE001 - profile load must not crash the scan
            PROFILE_LOAD_GAPS.append("%s: yaml load failed (%s)" % (rel, exc))
            continue
        if obj is None:
            continue
        _collect_profile_fields(obj, found)
    return frozenset(found)


def _build_ticker_literals(repo_root: Path | None = None) -> frozenset[str]:
    found = set(_HAND_TYPED)
    found.update(load_profile_ticker_literals(repo_root))
    return frozenset(found)


TICKER_LITERALS: frozenset[str] = _build_ticker_literals()
PROFILE_TICKER_LITERALS: frozenset[str] = load_profile_ticker_literals()


def _folded_set(tokens: Iterable[str]) -> frozenset[str]:
    return frozenset(token.casefold() for token in tokens if isinstance(token, str) and token)


_TICKER_FOLDED = _folded_set(TICKER_LITERALS)


def refresh_ticker_literals(repo_root: Path | None = None) -> frozenset[str]:
    """Rebuild TICKER_LITERALS (used by tests that point at a tmp repo)."""
    global TICKER_LITERALS, PROFILE_TICKER_LITERALS, _TICKER_FOLDED
    PROFILE_TICKER_LITERALS = load_profile_ticker_literals(repo_root)
    TICKER_LITERALS = frozenset(set(_HAND_TYPED) | set(PROFILE_TICKER_LITERALS))
    _TICKER_FOLDED = _folded_set(TICKER_LITERALS)
    return TICKER_LITERALS


def is_ticker_literal(value: object, literals: Iterable[str] | None = None) -> bool:
    if not isinstance(value, str) or not value:
        return False
    folded = _folded_set(literals) if literals is not None else _TICKER_FOLDED
    return value.casefold() in folded


def _const_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _sequence_str_constants(node: ast.AST | None) -> list[str]:
    if node is None:
        return []
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        out = []
        for elt in node.elts:
            value = _const_str(elt)
            if value is not None:
                out.append(value)
        return out
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id in {"set", "frozenset", "tuple", "list"} and node.args:
            return _sequence_str_constants(node.args[0])
    return []


def _dict_literal(node: ast.AST | None) -> ast.Dict | None:
    if node is None:
        return None
    if isinstance(node, ast.Dict):
        return node
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict":
        for arg in node.args:
            found = _dict_literal(arg)
            if found is not None:
                return found
    return None


def _target_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        names: list[str] = []
        for elt in node.elts:
            names.extend(_target_names(elt))
        return names
    return []


def _snippet(text: str, lineno: int, limit: int = 160) -> str:
    lines = text.splitlines()
    if lineno < 1 or lineno > len(lines):
        return ""
    return lines[lineno - 1].strip()[:limit]


def _has_attr_call(node: ast.AST, attr: str) -> bool:
    cur: ast.AST | None = node
    while isinstance(cur, ast.Call) and isinstance(cur.func, ast.Attribute):
        if cur.func.attr == attr:
            return True
        cur = cur.func.value
    return False


def _match_pattern_constants(pattern: ast.AST) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    if isinstance(pattern, ast.MatchValue):
        value = _const_str(pattern.value)
        if value is not None:
            found.append((pattern.lineno, value))
    elif isinstance(pattern, ast.MatchOr):
        for part in pattern.patterns:
            found.extend(_match_pattern_constants(part))
    elif isinstance(pattern, ast.MatchAs) and pattern.pattern is not None:
        found.extend(_match_pattern_constants(pattern.pattern))
    elif isinstance(pattern, ast.MatchSequence):
        for part in pattern.patterns:
            found.extend(_match_pattern_constants(part))
    elif isinstance(pattern, ast.MatchMapping):
        for key in pattern.keys:
            value = _const_str(key)
            if value is not None:
                found.append((key.lineno, value))
        for part in pattern.patterns:
            found.extend(_match_pattern_constants(part))
        rest = getattr(pattern, "rest", None)
        if rest is not None and not isinstance(rest, str):
            found.extend(_match_pattern_constants(rest))
    elif isinstance(pattern, ast.MatchClass):
        for part in pattern.patterns:
            found.extend(_match_pattern_constants(part))
        for part in pattern.kwd_patterns:
            found.extend(_match_pattern_constants(part))
    elif isinstance(pattern, ast.MatchStar) and getattr(pattern, "name", None) is None:
        pass
    return found


def scan_source(
    path: str,
    text: str,
    *,
    literals: Iterable[str] | None = None,
) -> list[Finding]:
    """Scan one Python source string. Never imports the module."""
    try:
        tree = ast.parse(text, filename=path)
    except SyntaxError:
        return []
    ticker_set = frozenset(literals) if literals is not None else TICKER_LITERALS

    def tick(value: object) -> bool:
        return is_ticker_literal(value, ticker_set)

    findings: list[Finding] = []
    seen: set[tuple[int, str, str]] = set()

    def emit(line: int, kind: str, literal: str) -> None:
        key = (line, kind, literal)
        if key in seen:
            return
        seen.add(key)
        findings.append(
            Finding(path=path, line=line, kind=kind, literal=literal, snippet=_snippet(text, line))
        )

    assigned_dicts: dict[str, list[ast.Dict]] = defaultdict(list)
    lookup_names: set[str] = set()
    inline_dicts: list[ast.Dict] = []
    upper_eq_nodes: set[int] = set()

    class Collector(ast.NodeVisitor):
        def visit_Assign(self, node: ast.Assign) -> None:
            d = _dict_literal(node.value)
            if d is not None:
                for target in node.targets:
                    for name in _target_names(target):
                        assigned_dicts[name].append(d)
            self.generic_visit(node)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            if node.value is not None:
                d = _dict_literal(node.value)
                if d is not None:
                    for name in _target_names(node.target):
                        assigned_dicts[name].append(d)
            self.generic_visit(node)

        def visit_Subscript(self, node: ast.Subscript) -> None:
            if isinstance(node.value, ast.Name):
                lookup_names.add(node.value.id)
            else:
                d = _dict_literal(node.value)
                if d is not None:
                    inline_dicts.append(d)
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "get":
                if isinstance(func.value, ast.Name):
                    lookup_names.add(func.value.id)
                else:
                    d = _dict_literal(func.value)
                    if d is not None:
                        inline_dicts.append(d)
            if isinstance(func, ast.Attribute) and func.attr in {"startswith", "endswith"}:
                recv = _const_str(func.value)
                if recv is not None and tick(recv):
                    emit(node.lineno, "call_branch", recv)
                for arg in node.args:
                    value = _const_str(arg)
                    if value is not None and tick(value):
                        emit(node.lineno, "call_branch", value)
            self.generic_visit(node)

        def visit_Compare(self, node: ast.Compare) -> None:
            chain = [node.left, *node.comparators]
            call_branch = False
            for i, op in enumerate(node.ops):
                a, b = chain[i], chain[i + 1]
                if isinstance(op, (ast.Eq, ast.NotEq)):
                    for left, right in ((a, b), (b, a)):
                        if _has_attr_call(left, "upper"):
                            value = _const_str(right)
                            if value is not None and tick(value):
                                emit(node.lineno, "call_branch", value)
                                call_branch = True
                                upper_eq_nodes.add(id(node))
            if call_branch:
                self.generic_visit(node)
                return
            for i, op in enumerate(node.ops):
                a, b = chain[i], chain[i + 1]
                for side in (a, b):
                    value = _const_str(side)
                    if value is not None and tick(value):
                        emit(node.lineno, "compare", value)
                if isinstance(op, (ast.In, ast.NotIn)):
                    for seq in (a, b):
                        for item in _sequence_str_constants(seq):
                            if tick(item):
                                emit(node.lineno, "compare", item)
            self.generic_visit(node)

        def visit_Match(self, node: ast.Match) -> None:
            for case in node.cases:
                for lineno, value in _match_pattern_constants(case.pattern):
                    if tick(value):
                        emit(lineno, "match", value)
            self.generic_visit(node)

    Collector().visit(tree)

    dispatch_dicts: list[ast.Dict] = []
    dispatch_dicts.extend(inline_dicts)
    for name, dicts in assigned_dicts.items():
        if name in lookup_names:
            dispatch_dicts.extend(dicts)
    for d in dispatch_dicts:
        for key_node in d.keys:
            value = _const_str(key_node)
            if value is not None and tick(value):
                emit(key_node.lineno, "dispatch", value)

    findings.sort(key=lambda f: (f.path, f.line, f.kind, f.literal))
    return findings


def _is_test_path(rel: str) -> bool:
    parts = rel.split("/")
    if "tests" in parts:
        return True
    name = parts[-1]
    if name.startswith("test_") and name.endswith(".py"):
        return True
    if name.endswith("_test.py"):
        return True
    return False


def _rel_matches(rel: str, globs: Iterable[str]) -> bool:
    for raw in globs:
        g = raw.replace("\\", "/")
        if fnmatch.fnmatch(rel, g):
            return True
        if "/**/" in g and fnmatch.fnmatch(rel, g.replace("/**/", "/")):
            return True
        if "**" in g:
            prefix = g.split("**", 1)[0].rstrip("/")
            if prefix and rel.startswith(prefix + "/") and rel.endswith(".py"):
                return True
            if prefix and rel == prefix:
                return True
        if g.endswith("/") and (rel.startswith(g) or rel == g[:-1]):
            if rel.endswith(".py"):
                return True
    return False


def iter_sni_python_files(repo_root: Path, scope_globs: Iterable[str] | None = None) -> list[Path]:
    """Return SNI Python files under *repo_root*, tests excluded.

    File-walking idiom matches tests/test_sni_program_invariants.py:
    ``sorted(base.rglob(...))`` over the SNI tree, skip non-files.
    """
    root = Path(repo_root)
    base = root / SNI_ROOT_REL
    out: list[Path] = []
    if not base.exists():
        return out
    globs = tuple(scope_globs) if scope_globs is not None else DEFAULT_SCOPE_GLOBS
    for path in sorted(base.rglob("*.py")):
        if not path.is_file():
            continue
        rel = _posix(root, path)
        if "__pycache__" in rel.split("/"):
            continue
        if _is_test_path(rel):
            continue
        if not _rel_matches(rel, globs):
            continue
        out.append(path)
    return out


def scan_tree(
    repo_root,
    scope_globs: Iterable[str] | None = None,
    *,
    literals: Iterable[str] | None = None,
) -> list[Finding]:
    """Scan ``*.py`` under the SNI tree (tests excluded). Files are only read."""
    root = Path(repo_root)
    globs = tuple(scope_globs) if scope_globs is not None else DEFAULT_SCOPE_GLOBS
    findings: list[Finding] = []
    for path in iter_sni_python_files(root, globs):
        rel = _posix(root, path)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        findings.extend(scan_source(rel, text, literals=literals))
    findings.sort(key=lambda f: (f.path, f.line, f.kind, f.literal))
    return findings


def allowlist_matches(finding: Finding, entry: tuple[str, str, str, str]) -> bool:
    path, kind, literal, _justification = entry
    if finding.path != path:
        return False
    if finding.kind != kind:
        return False
    return finding.literal.casefold() == literal.casefold()


def partition_allowlist(
    findings: Iterable[Finding],
    allowlist: Iterable[tuple[str, str, str, str]] | None = None,
) -> tuple[list[Finding], list[Finding], list[tuple[str, str, str, str]]]:
    """Return (kept, allowlisted, stale_entries)."""
    table = tuple(ALLOWLIST if allowlist is None else allowlist)
    kept: list[Finding] = []
    allowed: list[Finding] = []
    used = [False] * len(table)
    for finding in findings:
        hit = False
        for i, entry in enumerate(table):
            if allowlist_matches(finding, entry):
                used[i] = True
                hit = True
        if hit:
            allowed.append(finding)
        else:
            kept.append(finding)
    stale = [entry for i, entry in enumerate(table) if not used[i]]
    return kept, allowed, stale


def check_allowlist(
    findings: Iterable[Finding],
    allowlist: Iterable[tuple[str, str, str, str]] | None = None,
) -> list[Finding]:
    """Return non-allowlisted findings. Raise if an allowlist entry is stale."""
    kept, _allowed, stale = partition_allowlist(findings, allowlist)
    if stale:
        shown = ", ".join(
            "%s %s %s" % (path, kind, literal) for path, kind, literal, _j in stale
        )
        raise StaleAllowlistError("stale allowlist entries match nothing: %s" % shown)
    return kept
