"""A20C structural authority scan.

The A20B extension's line-level regex (see tests/test_sni_injection_safety_ext.py
``_AUTHORITY_TRUE_RE``) only flags a non-False authority value when the key and
``true`` lie on the same physical line. A non-False value split across lines,
nested inside a list, written as a YAML flow mapping, encoded as an int or as
the string ``"false"``, or hidden by a duplicate key a parser resolves to the
later value passes through the regex unseen. This module ADDS a STRUCTURAL
scan that parses every JSON / JSONL / YAML file under
``research/single_name_intelligence/``, walks the parsed objects, and flags
every such value regardless of how it was spelled.

Tests in this file:
  * ``test_a20c_no_structural_authority_hits`` -- a full scan returns no hits;
  * ``test_a20c_scan_floors`` -- the scan proved it saw the corpus;
  * ``test_a20c_positive_controls`` -- synthetic strings that must trip the scan;
  * ``test_a20c_negative_controls`` -- synthetic strings that must not;
  * ``test_a20c_regex_gap_witness`` -- the line regex misses several of those
    positives; the structural scan must catch them;
  * ``test_a20c_deterministic`` -- two scans return identical hit lists.

Tests read files only. They never import the existing A20B extension, never
spawn subprocesses, never write anywhere, and never mutate ``sys.modules``.
"""
from __future__ import annotations

import ast
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Callable

import pytest

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover -- environment guarantees PyYAML
    _yaml = None  # type: ignore[assignment]


ROOT: Path = Path(__file__).resolve().parents[1]
SNI_ROOT: Path = ROOT / "research" / "single_name_intelligence"

DATA_SUFFIXES: tuple[str, ...] = (".json", ".jsonl", ".yml", ".yaml")
CANONICAL_AUTHORITY: tuple[str, ...] = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)


# ---------------------------------------------------------------------------
# YAML loader that records duplicate keys during construction
# ---------------------------------------------------------------------------


class _DupYAMLLoader(_yaml.SafeLoader):
    """SafeLoader subclass that records duplicate keys during construction.

    PyYAML's default ``construct_mapping`` silently overwrites earlier key
    occurrences with the later value; we keep that resolved-dict behaviour so
    callers see what Python would see, but ALSO emit a duplicate-key record
    for every collision we observed.
    """

    def __init__(self, stream: object) -> None:
        super().__init__(stream)  # type: ignore[arg-type]
        self._dup_records: list[object] = []

    def construct_mapping(self, node: object, deep: bool = False) -> dict:
        MappingNode = _yaml.MappingNode  # type: ignore[attr-defined]
        if not isinstance(node, MappingNode):
            raise _yaml.ConstructorError(  # type: ignore[attr-defined]
                None,
                None,
                f"expected a mapping node, but found {node.id}",
                node.start_mark,
            )
        self.flatten_mapping(node)
        result: dict = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            value = self.construct_object(value_node, deep=deep)
            try:
                hash(key)
            except TypeError:
                continue
            if key in result:
                self._dup_records.append(key)
            result[key] = value
        return result


# ---------------------------------------------------------------------------
# JSON object_pairs_hook helper
# ---------------------------------------------------------------------------


def _json_pairs_hook_factory(
    recorder: list[tuple[str, object]],
) -> Callable[[list[tuple[object, object]]], dict]:
    """Return an ``object_pairs_hook`` that records duplicate keys into ``recorder``."""

    def _hook(pairs: list[tuple[object, object]]) -> dict:
        seen: set = set()
        for key, _ in pairs:
            try:
                hash(key)
            except TypeError:
                continue
            if key in seen:
                recorder.append(("", key))
            else:
                seen.add(key)
        return dict(pairs)

    return _hook


# ---------------------------------------------------------------------------
# Walker -- accumulates hits and counters
# ---------------------------------------------------------------------------


def _json_pointer(path: tuple) -> str:
    """RFC-6901-style JSON pointer built from a tuple of (str|int) parts.

    A path of (``"authority_flags"``, ``"rank_authority"``) renders as
    ``"/authority_flags/rank_authority"``; a list-index part is rendered
    numerically (``0``, ``1``, ...). Empty tuple returns the empty string.
    """
    if not path:
        return ""
    parts: list[str] = []
    for part in path:
        if isinstance(part, int):
            parts.append(str(part))
        else:
            parts.append(str(part).replace("~", "~0").replace("/", "~1"))
    return "/" + "/".join(parts)


def _walk(
    obj: Any,
    *,
    relpath: str,
    path: tuple = (),
    hits: list[tuple[str, str, str]],
    counters: dict,
    rules: str = "all",
) -> None:
    """Walk ``obj`` recursively, appending structural hits and updating counters.

    ``rules`` selects which rule set to apply:
      * ``"all"``      -- rules (a)+(b)+(c) (corpus and controls).
      * ``"a_only"``   -- rule (a) only (the A20B regex analogue).
    """
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            sub: tuple = path + (key,)
            klow = key.lower() if isinstance(key, str) else None
            if rules in ("all", "a_only") and klow is not None and klow.endswith("_authority"):
                # Rule (a): every key whose lower-cased form ends with _authority
                # whose value is not False is a hit.
                counters["authority_leaves"] = (
                    counters.get("authority_leaves", 0) + 1
                )
                if klow in CANONICAL_AUTHORITY:
                    counters[klow] = counters.get(klow, 0) + 1
                if value is not False:
                    hits.append((relpath, _json_pointer(sub), repr(value)[:80]))
                if rules == "a_only":
                    # a_only still recurses (the walk is structurally
                    # general), but stop emitting other rules.
                    _walk(
                        value,
                        relpath=relpath,
                        path=sub,
                        hits=hits,
                        counters=counters,
                        rules="a_only",
                    )
                    continue
            elif klow == "authority_flags":
                # Rule (b): authority_flags value is not a dict => hit; if it
                # IS a dict, count it as a mapping AND check each child for
                # any value that is not False.
                counters["authority_flags_keys"] = (
                    counters.get("authority_flags_keys", 0) + 1
                )
                if not isinstance(value, Mapping):
                    hits.append((relpath, _json_pointer(sub), repr(value)[:80]))
                else:
                    counters["authority_flags_mappings"] = (
                        counters.get("authority_flags_mappings", 0) + 1
                    )
                    for ik, iv in value.items():
                        if iv is not False:
                            hits.append(
                                (
                                    relpath,
                                    _json_pointer(sub + (ik,)),
                                    repr(iv)[:80],
                                )
                            )
            elif rules == "all" and klow == "authority":
                # Rule (c): value is a dict holding a bool that is not False.
                if isinstance(value, Mapping):
                    for ik, iv in value.items():
                        if isinstance(iv, bool) and iv is not False:
                            hits.append(
                                (
                                    relpath,
                                    _json_pointer(sub + (ik,)),
                                    repr(iv)[:80],
                                )
                            )
            if rules == "all":
                _walk(
                    value,
                    relpath=relpath,
                    path=sub,
                    hits=hits,
                    counters=counters,
                    rules="all",
                )
            else:
                # a_only when the key wasn't a *_authority key, drop to no-rules
                # so we still descend but stop emitting rule (a) on descendants.
                # In practice this only matters for control multi-doc scans.
                _walk(
                    value,
                    relpath=relpath,
                    path=sub,
                    hits=hits,
                    counters=counters,
                    rules="a_only",
                )
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk(
                v,
                relpath=relpath,
                path=path + (i,),
                hits=hits,
                counters=counters,
                rules=rules,
            )


# ---------------------------------------------------------------------------
# Public scan entry
# ---------------------------------------------------------------------------


def _discover_files() -> list[Path]:
    paths: list[Path] = []
    for path in sorted(SNI_ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(SNI_ROOT)
        if "__pycache__" in rel.parts:
            continue
        if path.suffix.lower() not in DATA_SUFFIXES:
            continue
        paths.append(path)
    return paths


def _parse_yaml_text(
    text: str,
) -> tuple[list, list[object]]:
    loader = _DupYAMLLoader(text)
    documents: list = []
    try:
        while loader.check_data():
            documents.append(loader.get_data())
    finally:
        loader.dispose()
    return documents, loader._dup_records


def _scan_file_text(
    suffix: str,
    text: str,
    relpath: str,
    *,
    out_hits: list,
    counters: dict,
) -> None:
    """Scan an in-memory file ``text`` (suffix-aware). Mutations go to out_hits."""
    counters["files_scanned"] = counters.get("files_scanned", 0) + 1
    counters[f"suffix:{suffix.lower()}"] = (
        counters.get(f"suffix:{suffix.lower()}", 0) + 1
    )
    if suffix == ".json":
        recorder: list[tuple[str, object]] = []
        try:
            obj = json.loads(
                text,
                object_pairs_hook=_json_pairs_hook_factory(recorder),
            )
        except json.JSONDecodeError as exc:
            out_hits.append(
                (relpath, "", f"PARSE_ERROR {type(exc).__name__}")
            )
            return
        for _, key in recorder:
            out_hits.append((relpath, f"/{key!r}", repr(key)[:80]))
        _walk(obj, relpath=relpath, hits=out_hits, counters=counters, rules="all")
    elif suffix == ".jsonl":
        for line_no, raw in enumerate(text.splitlines(), 1):
            if raw == "" or raw.isspace():
                continue
            recorder = []
            try:
                obj = json.loads(
                    raw,
                    object_pairs_hook=_json_pairs_hook_factory(recorder),
                )
            except json.JSONDecodeError as exc:
                out_hits.append(
                    (
                        relpath,
                        f":L{line_no}",
                        f"PARSE_ERROR {type(exc).__name__}",
                    )
                )
                continue
            for _, key in recorder:
                out_hits.append(
                    (
                        relpath,
                        f":L{line_no}/{key!r}",
                        repr(key)[:80],
                    )
                )
            _walk(
                obj,
                relpath=relpath,
                hits=out_hits,
                counters=counters,
                rules="all",
            )
    elif suffix in (".yml", ".yaml"):
        try:
            documents, dup_records = _parse_yaml_text(text)
        except _yaml.YAMLError as exc:  # type: ignore[attr-defined]
            out_hits.append(
                (relpath, "", f"PARSE_ERROR {type(exc).__name__}")
            )
            return
        for key in dup_records:
            out_hits.append((relpath, f"/{key!r}", repr(key)[:80]))
        for doc in documents:
            _walk(
                doc,
                relpath=relpath,
                hits=out_hits,
                counters=counters,
                rules="all",
            )


def _scan_one(path: Path, out_hits: list, counters: dict) -> None:
    rel = path.relative_to(SNI_ROOT).as_posix()
    suffix = path.suffix.lower()
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        out_hits.append((rel, "", f"PARSE_ERROR {type(exc).__name__}"))
        return
    _scan_file_text(suffix, text, rel, out_hits=out_hits, counters=counters)


def _full_scan() -> tuple[list, dict]:
    hits: list = []
    counters: dict = {}
    for path in _discover_files():
        _scan_one(path, hits, counters)
    return hits, counters


# ---------------------------------------------------------------------------
# 1. test_a20c_no_structural_authority_hits
# ---------------------------------------------------------------------------


def test_a20c_no_structural_authority_hits() -> None:
    """A structural scan of the entire SNI corpus returns no non-False authority.

    This is the primary guarantee: every authority value, regardless of how it
    was spelled in the source, is literal False.
    """
    hits, counters = _full_scan()
    if hits:
        msg_lines = [f"{rel}:{ptr} -> {val}" for rel, ptr, val in hits]
        raise AssertionError(
            f"A20C structural scan found {len(hits)} non-False authority values "
            f"across {counters.get('files_scanned', 0)} files:\n"
            + "\n".join(msg_lines)
        )
    assert hits == []


# ---------------------------------------------------------------------------
# 2. test_a20c_scan_floors
# ---------------------------------------------------------------------------


SCAN_FLOORS: dict[str, int] = {
    "files_scanned": 120,
    "suffix:.json": 60,
    "suffix:.jsonl": 40,
    "suffix:.yml": 3,  # adjust if .yaml count + .yml count >= 5; we floor per-ext.
    "suffix:.yaml": 0,
    "authority_leaves": 250,
    "authority_flags_mappings": 20,
    "rank_authority": 40,
    "gate_authority": 40,
    "size_authority": 40,
    "signal_authority": 40,
    "escalation_authority": 40,
    "trade_authority": 40,
}


def test_a20c_scan_floors() -> None:
    """The scan saw enough of the corpus to be meaningful.

    Floors pin a silent empty scan: a test that ran against zero files would
    also ``assert hits == []``. Each floor is the observed census value on the
    pin day; if real data shrinks, drop ONLY to the observed value, never below.
    """
    _hits, counters = _full_scan()
    suffix_yaml_total = (
        counters.get("suffix:.yml", 0) + counters.get("suffix:.yaml", 0)
    )
    actual_summary = {
        "files_scanned": counters.get("files_scanned", 0),
        "suffix:.json": counters.get("suffix:.json", 0),
        "suffix:.jsonl": counters.get("suffix:.jsonl", 0),
        "suffix:.yml+.yaml": suffix_yaml_total,
        "authority_leaves": counters.get("authority_leaves", 0),
        "authority_flags_mappings": counters.get(
            "authority_flags_mappings", 0
        ),
        "rank_authority": counters.get("rank_authority", 0),
        "gate_authority": counters.get("gate_authority", 0),
        "size_authority": counters.get("size_authority", 0),
        "signal_authority": counters.get("signal_authority", 0),
        "escalation_authority": counters.get("escalation_authority", 0),
        "trade_authority": counters.get("trade_authority", 0),
    }
    failures: list[str] = []
    for key, floor in SCAN_FLOORS.items():
        if key in {"suffix:.yml", "suffix:.yaml"}:
            continue  # handled by the combined suffix:.yml+.yaml floor
        actual = counters.get(key, 0)
        if actual < floor:
            failures.append(f"  {key}: actual={actual} < floor={floor}")
    if suffix_yaml_total < 5:
        failures.append(
            f"  suffix:.yml+.yaml: actual={suffix_yaml_total} < floor=5"
        )
    assert not failures, (
        "A20C scan-floor failures:\n"
        + "\n".join(failures)
        + "\n\nObserved counts:\n"
        + "\n".join(f"  {k} = {v}" for k, v in actual_summary.items())
    )


# ---------------------------------------------------------------------------
# 3. test_a20c_positive_controls (parametrized)
# ---------------------------------------------------------------------------


POSITIVE_CONTROLS: tuple[tuple[str, str], ...] = (
    # (id, text) -- the structural scan must yield exactly one hit per row.
    (
        "json_multi_line",
        '{"x": {\n "rank_authority":\n true}}',
    ),
    ("json_nested_list", '{"a": [{"gate_authority": true}]}'),
    ("json_int_one", '{"size_authority": 1}'),
    ("json_string_false", '{"signal_authority": "false"}'),
    ("json_duplicate_k", '{"k": 1, "k": 2}'),
    ("jsonl_trade_null", '{"a": 1}\n{"trade_authority": null}\n'),
    ("yaml_flow_yes", "gate_authority: yes"),
    ("yaml_multi_line_true", "escalation_authority:\n  true"),
    ("yaml_on_truthy", "trade_authority: on"),
    ("yaml_authority_flags_list", "authority_flags: [false]"),
    ("yaml_authority_dict_bool", "authority:\n  x: true"),
    ("yaml_duplicate", "a: 1\na: 2\n"),
    ("json_rank_authority_case", '{"Rank_Authority": true}'),
)


@pytest.mark.parametrize("cid,text", POSITIVE_CONTROLS)
def test_a20c_positive_controls(cid: str, text: str) -> None:
    """Every positive control parses to exactly one structural hit."""
    hits: list = []
    counters: dict = {}
    # Each control is treated as a separate "file" so the parse+walk functions
    # see exactly what the corpus scan would feed them.
    fmt = _control_format(cid)
    _scan_file_text(fmt, text, cid, out_hits=hits, counters=counters)
    assert len(hits) == 1, (
        f"positive control {cid!r} yielded {len(hits)} hits, expected 1. "
        f"Hits: {hits}"
    )


def _control_format(cid: str) -> str:
    if cid.startswith("json"):
        return ".json"
    if cid.startswith("jsonl"):
        return ".jsonl"
    if cid.startswith("yaml") or cid.startswith("yml"):
        return ".yml"
    raise KeyError(cid)


# ---------------------------------------------------------------------------
# 4. test_a20c_negative_controls (parametrized)
# ---------------------------------------------------------------------------


NEGATIVE_CONTROLS: tuple[tuple[str, str], ...] = (
    ("json_rank_false", '{"rank_authority": false}'),
    ("yaml_authority_string", 'authority: "prose about rank authority"'),
    ("json_authorityx", '{"authorityx": true}'),
    (
        "json_note_mentions_authority",
        '{"note": "rank_authority: true"}',
    ),
    (
        "yaml_authority_flags_all_false",
        "authority_flags:\n  rank_authority: false\n  gate_authority: false\n",
    ),
)


@pytest.mark.parametrize("cid,text", NEGATIVE_CONTROLS)
def test_a20c_negative_controls(cid: str, text: str) -> None:
    """Every negative control yields zero hits."""
    hits: list = []
    counters: dict = {}
    fmt = _control_format(cid)
    _scan_file_text(fmt, text, cid, out_hits=hits, counters=counters)
    assert hits == [], (
        f"negative control {cid!r} should yield zero hits, got {hits}"
    )


# ---------------------------------------------------------------------------
# 5. test_a20c_regex_gap_witness
# ---------------------------------------------------------------------------


def _resolve_authority_pattern() -> re.Pattern:
    """Read tests/test_sni_injection_safety_ext.py and compile its regex.

    Extracts the literal pattern + flags from the assignment to
    ``_AUTHORITY_TRUE_RE`` WITHOUT importing that module. The pattern is
    expected to be either a string assigned to ``re.compile(...)`` or a
    ``re.compile(...)`` Call whose arguments are literal-evaluable.
    """
    src_path = ROOT / "tests" / "test_sni_injection_safety_ext.py"
    tree = ast.parse(src_path.read_text(encoding="utf-8"))
    found_pattern: str | None = None
    found_flags: int = 0
    found_value: Any = None
    found_node: ast.Assign | None = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Name)
                and target.id == "_AUTHORITY_TRUE_RE"
            ):
                found_value = node.value
                found_node = node
                break
        if found_value is not None:
            break
    if found_value is None or found_node is None:
        raise AssertionError(
            "_AUTHORITY_TRUE_RE assignment not found in tests/"
            "test_sni_injection_safety_ext.py; cannot compile the witness."
        )
    # Two accepted shapes:
    #   _AUTHORITY_TRUE_RE = "<pattern>"
    #   _AUTHORITY_TRUE_RE = re.compile("<pattern>", re.IGNORECASE)
    if isinstance(found_value, ast.Constant) and isinstance(found_value.value, str):
        found_pattern = found_value.value
    elif (
        isinstance(found_value, ast.Call)
        and isinstance(found_value.func, ast.Attribute)
        and found_value.func.attr == "compile"
        and isinstance(found_value.func.value, ast.Name)
        and found_value.func.value.id == "re"
    ):
        if not found_value.args:
            raise AssertionError(
                "_AUTHORITY_TRUE_RE = re.compile() called with no args"
            )
        first = found_value.args[0]
        if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
            raise AssertionError(
                "_AUTHORITY_TRUE_RE pattern is not a literal string"
            )
        found_pattern = first.value
        for kw in found_value.keywords:
            if kw.arg != "flags":
                continue
            v = kw.value
            if isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name) and v.value.id == "re":
                found_flags = int(getattr(re, v.attr))
            elif isinstance(v, ast.Constant) and isinstance(v.value, int):
                found_flags = v.value
            elif isinstance(v, ast.BinOp):
                # e.g. re.I | re.M
                left = v.left
                right = v.right
                lv = _resolve_flag_operand(left)
                rv = _resolve_flag_operand(right)
                if lv is None or rv is None:
                    raise AssertionError(
                        "_AUTHORITY_TRUE_RE flags BinOp operand not resolvable"
                    )
                found_flags = int(lv) | int(rv)
            else:
                raise AssertionError(
                    f"_AUTHORITY_TRUE_RE flags keyword not resolvable: {ast.dump(v)}"
                )
        # positional 2nd arg equivalent
        if len(found_value.args) >= 2:
            v = found_value.args[1]
            if isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name) and v.value.id == "re":
                found_flags = int(getattr(re, v.attr))
            elif isinstance(v, ast.Constant) and isinstance(v.value, int):
                found_flags = v.value
            else:
                raise AssertionError(
                    "_AUTHORITY_TRUE_RE positional flags not resolvable"
                )
    else:
        raise AssertionError(
            f"_AUTHORITY_TRUE_RE is not a string or re.compile() call: "
            f"{ast.dump(found_value)}"
        )
    assert found_pattern is not None
    return re.compile(found_pattern, found_flags)


def _resolve_flag_operand(node: ast.AST) -> int | None:
    """Resolve a single flag operand (``re.I``, ``re.M``, an int literal)."""
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "re":
        try:
            return int(getattr(re, node.attr))
        except AttributeError:
            return None
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    return None


def test_a20c_regex_gap_witness() -> None:
    """The line regex must miss at least 5 of the structural positives.

    For each positive control the structural scan catches, the line regex must
    NOT match any single line of the same text. We do not import the existing
    A20B extension; we read its source and recompile its regex directly.
    """
    pattern = _resolve_authority_pattern()
    gaps: list[tuple[str, str]] = []
    misses: list[tuple[str, str]] = []
    for cid, text in POSITIVE_CONTROLS:
        # Structural scan must catch it.
        hits: list = []
        counters: dict = {}
        fmt = _control_format(cid)
        _scan_file_text(fmt, text, cid, out_hits=hits, counters=counters)
        if not hits:
            raise AssertionError(
                f"positive control {cid!r} is not caught by the structural scan; "
                f"cannot be a regex gap"
            )
        # Line regex must miss every line of the control text.
        matched_any = any(pattern.search(line) for line in text.splitlines())
        if not matched_any:
            gaps.append((cid, text))
        else:
            misses.append((cid, text))
    assert len(gaps) >= 5, (
        f"regex-gap witness needs >= 5 controls the line regex misses; "
        f"observed {len(gaps)} gaps. Full gap list:\n"
        + "\n".join(f"  {cid}: {text!r}" for cid, text in gaps)
        + "\n\nControls the regex DID match (excluded from the gap set):\n"
        + "\n".join(f"  {cid}: {text!r}" for cid, text in misses)
    )


# ---------------------------------------------------------------------------
# 6. test_a20c_deterministic
# ---------------------------------------------------------------------------


def test_a20c_deterministic() -> None:
    """Two full scans return identical hit lists AND identical counters."""
    first_hits, first_counters = _full_scan()
    second_hits, second_counters = _full_scan()
    assert first_hits == second_hits, (
        f"A20C hits changed between scans:\n"
        f"first  = {first_hits[:5]}...\n"
        f"second = {second_hits[:5]}..."
    )
    assert first_counters == second_counters, (
        f"A20C counters changed between scans:\n"
        f"first  = {first_counters}\nsecond = {second_counters}"
    )
