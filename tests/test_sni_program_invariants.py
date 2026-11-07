"""Tree-wide SNI program-law tripwire (commission 8659).

SNI-local DRAFT invariant scanner. It consumes owner-supplied identity
values from Data OS / Stock Identity (`data/reference/security_master.parquet`)
and never mints, derives, or guesses issuer or security ids. It does not
re-implement Data OS identity, Company Event/Earnings, FIF, Capital Structure,
Stock Identity, Options, Research Vault, or qledger/Evaluation. Nothing here
feeds a ranker, gate, sizer, signal, escalation, or trade path. Every
authority flag is required to be literal false; a caller that tries to set
one true is a test failure.

Scans research/single_name_intelligence/** and
contracts/single_name_intelligence/** (*.json, *.yml, *.yaml, *.py).
Python is read with ast only (never imported). JSON/YAML parse failure is
a test failure naming the file.
"""
from __future__ import annotations

import ast
import io
import json
import re
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Iterator

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover - host has PyYAML; keep the import gated
    yaml = None

REPO_ROOT = Path(__file__).resolve().parents[1]

SCAN_ROOTS = (
    "research/single_name_intelligence",
    "contracts/single_name_intelligence",
)
SCAN_EXTS = {".json": "json", ".yml": "yml", ".yaml": "yaml", ".py": "py"}

# path (posix, relative to the scanned root) -> reason. Empty on this tree:
# no scanned file exceeds 20 MB. A test asserts every listed path exists.
SKIPPED: dict[str, str] = {}

ALLOWED_SPLIT_DEVIATIONS: dict[str, str] = {}
ALLOWED_HORIZON_DEVIATIONS: dict[str, str] = {}

AUTHORITY_FLAG_KEYS = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)
AUTHORITY_FLAG_FOLDED = {k.casefold() for k in AUTHORITY_FLAG_KEYS}
AUTHORITY_SHORT_FOLDED = {
    "rank", "gate", "size", "signal", "escalation", "trade",
}
AUTHORITY_MAP_KEYS = {"authority", "authority_flags"}

IDENTITY_ID_KEYS = (
    "canonical_issuer_id",
    "issuer_id",
    "security_id",
    "canonical_security_id",
    "instrument_id",
    "listing_id",
    "cik",
    "figi",
    "isin",
    "cusip",
    "permid",
    "perm_id",
    "lei",
    "sedol",
)
IDENTITY_ID_FOLDED = {k.casefold() for k in IDENTITY_ID_KEYS}

IDENTITY_KEY_TO_COLUMNS = {
    "security_id": ("security_id",),
    "canonical_security_id": ("security_id", "canonical_security_id"),
    "issuer_id": ("issuer_id",),
    "canonical_issuer_id": ("issuer_id", "canonical_issuer_id"),
    "cik": ("issuer_cik", "cik"),
    "listing_id": ("listing_id", "listing_key"),
    "instrument_id": ("instrument_id",),
    "figi": ("figi",),
    "isin": ("isin",),
    "cusip": ("cusip",),
    "permid": ("permid", "perm_id"),
    "perm_id": ("perm_id", "permid"),
    "lei": ("lei",),
    "sedol": ("sedol",),
}

UNKNOWN_IDENTITY = {None, "UNRESOLVED"}

TUNE_START = date(2024, 1, 1)
QUARANTINE_START = date(2026, 10, 1)
REQUIRED_HORIZONS = (5, 21, 63)

ID_SHAPE = re.compile(r"\b(SEC|ISS):[A-Z]{2}-[A-Z]{4}-[A-Z0-9.]+\b")
ISO_DATE = re.compile(r"(20\d{2}-\d{2}-\d{2})")
WINDOW_TUNE = re.compile(
    r"(20\d{2}-\d{2}-\d{2})\s*<=\s*s\s*<\s*(20\d{2}-\d{2}-\d{2})"
)
TRAIN_LT = re.compile(r"\bs\s*<\s*(20\d{2}-\d{2}-\d{2})")
QUAR_GE = re.compile(r"\bs\s*>=\s*(20\d{2}-\d{2}-\d{2})")
PURGE_TRAIN = re.compile(
    r"(?:coverage_date|last session(?: of W_h)?)\s*"
    r"(?:>=|on or after)\s*(20\d{2}-\d{2}-\d{2}).*PURGED_TRAIN",
    re.I | re.S,
)
PURGE_TUNE = re.compile(
    r"(?:coverage_date|last session(?: of W_h)?)\s*"
    r"(?:>=|on or after)\s*(20\d{2}-\d{2}-\d{2}).*PURGED_TUNE",
    re.I | re.S,
)
SECRET_NEEDLES = (
    "BEGIN RSA",
    "BEGIN OPENSSH",
    "ghp_",
    "github_pat_",
    "xoxb-",
    "sk-ant-",
    "AKIA",
)
SCHEMA_KEYS = {
    "$ref", "$defs", "$schema", "$id", "type", "properties", "required",
    "additionalProperties", "oneOf", "anyOf", "allOf", "items", "const",
    "description", "pattern", "title", "definitions", "minLength",
    "minProperties", "propertyNames", "enum", "not",
}
HORIZON_KEY_FOLDED = {"grade_horizons", "horizons"}
SPLIT_BOUNDARY_NAME = re.compile(
    r"(TRAIN|TUNE|QUARANTINE).*(START|END|BEGIN)|"
    r"SPLIT_.*(START|END)|"
    r"^SPLIT_TUNEE_START$",
    re.I,
)
SPLIT_LEAF_FOLDED = {
    "train", "tune", "quarantine",
    "train_end", "tune_end", "tune_start", "quarantine_start", "train_start",
}
def _is_authority_map_name(name: str) -> bool:
    """True for AUTHORITY_FLAGS (any decoration) or the exact name AUTHORITY."""
    folded = name.upper()
    if "AUTHORITY_FLAGS" in folded:
        return True
    return name.strip("_").upper() == "AUTHORITY"
MAX_FILE_BYTES = 20 * 1024 * 1024
OWNER_PARQUET_REL = "data/reference/security_master.parquet"


@dataclass(frozen=True)
class Violation:
    path: str
    key: str
    invariant: str
    detail: str


@dataclass(frozen=True)
class Declaration:
    path: str
    key: str
    kind: str
    role: str
    value: str


@dataclass
class OwnerIds:
    by_column: dict[str, set[str]]
    union: set[str]
    skip_reason: str | None = None


@dataclass
class ScanReport:
    root: str
    file_counts: dict[str, int] = field(default_factory=dict)
    files_read: list[str] = field(default_factory=list)
    parse_errors: list[Violation] = field(default_factory=list)
    authority_checked: int = 0
    identity_checked: int = 0
    secret_hits: int = 0
    violations: list[Violation] = field(default_factory=list)
    split_declarations: list[Declaration] = field(default_factory=list)
    horizon_declarations: list[Declaration] = field(default_factory=list)
    owner_skip_reason: str | None = None


def _posix(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _is_skipped(rel: str) -> bool:
    for listed in SKIPPED:
        if rel == listed or rel.startswith(listed.rstrip("/") + "/"):
            return True
    return False


def iter_scan_files(root: Path) -> list[Path]:
    """Return every JSON/YAML/Python file under the SNI scan roots."""
    root = Path(root)
    out: list[Path] = []
    for rel in SCAN_ROOTS:
        base = root / rel
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in SCAN_EXTS:
                continue
            rel_path = _posix(root, path)
            if _is_skipped(rel_path):
                continue
            out.append(path)
    return out


def _load_yaml(text: str) -> Any:
    if yaml is None:
        raise RuntimeError("PyYAML is not installed")
    return yaml.safe_load(text)


def parse_structured(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    suf = path.suffix.lower()
    if suf == ".json":
        return json.loads(text)
    if suf in {".yml", ".yaml"}:
        return _load_yaml(text)
    raise ValueError(f"not a structured file: {path}")


def _is_schema_node(value: Any) -> bool:
    return isinstance(value, dict) and bool(SCHEMA_KEYS.intersection(value.keys()))


def _is_schema_false_constraint(value: Any) -> bool:
    if not isinstance(value, dict) or "const" not in value:
        return False
    return value["const"] is False


def _walk(obj: Any, path: tuple[str, ...]) -> Iterator[tuple[tuple[str, ...], str, Any]]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            ks = str(key)
            here = path + (ks,)
            yield here, ks, value
            yield from _walk(value, here)
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            yield from _walk(value, path + (f"[{i}]",))


def _dotted(parts: Iterable[str]) -> str:
    return ".".join(parts)


def load_owner_ids(repo_root: Path) -> OwnerIds:
    """Load owner-supplied identity strings from security_master.parquet.

    Never constructs an id. If pandas/pyarrow are missing or the file is not
    on disk, try `git show HEAD:data/reference/security_master.parquet` once
    and read the blob from memory (no shared temp file, so concurrent jobs on
    one runner cannot race). If it still cannot be read, skip_reason is set.
    """
    parquet_path = Path(repo_root) / OWNER_PARQUET_REL
    tried_git = False
    blob_bytes: bytes | None = None
    if not parquet_path.is_file():
        tried_git = True
        try:
            blob = subprocess.run(
                ["git", "show", f"HEAD:{OWNER_PARQUET_REL}"],
                cwd=str(repo_root),
                check=False,
                capture_output=True,
            )
            if blob.returncode == 0 and blob.stdout:
                blob_bytes = blob.stdout
            else:
                return OwnerIds(
                    {}, set(),
                    f"security_master.parquet not on disk and git show failed "
                    f"(rc={blob.returncode})",
                )
        except OSError as exc:
            return OwnerIds({}, set(), f"git show failed: {exc}")

    def _source() -> Any:
        # A fresh stream per reader, so the pandas fallback re-reads from 0.
        return io.BytesIO(blob_bytes) if blob_bytes is not None else str(parquet_path)

    try:
        import pyarrow.parquet as pq
    except ImportError:
        pq = None
    try:
        import pandas as pd
    except ImportError:
        pd = None

    columns: list[str]
    table_cols: dict[str, list[Any]] = {}
    if pq is not None:
        try:
            table = pq.read_table(_source())
            columns = list(table.column_names)
            for name in columns:
                table_cols[name] = table.column(name).to_pylist()
        except Exception as exc:  # noqa: BLE001 - skip this sub-check
            if pd is None:
                return OwnerIds(
                    {}, set(),
                    f"pyarrow failed to read {parquet_path}: {exc}; pandas missing",
                )
            try:
                frame = pd.read_parquet(_source())
            except Exception as exc2:  # noqa: BLE001
                return OwnerIds(
                    {}, set(),
                    f"could not read security_master.parquet "
                    f"(pyarrow {exc}; pandas {exc2})",
                )
            columns = list(frame.columns)
            for name in columns:
                table_cols[name] = list(frame[name].tolist())
    elif pd is not None:
        try:
            frame = pd.read_parquet(_source())
        except Exception as exc:  # noqa: BLE001
            return OwnerIds(
                {}, set(),
                f"pandas failed to read {parquet_path}: {exc}",
            )
        columns = list(frame.columns)
        for name in columns:
            table_cols[name] = list(frame[name].tolist())
    else:
        where = "git-exported blob" if tried_git else str(parquet_path)
        return OwnerIds(
            {}, set(),
            f"pandas and pyarrow missing; cannot read {where}",
        )

    by_column: dict[str, set[str]] = {}
    union: set[str] = set()
    for name, values in table_cols.items():
        bucket: set[str] = set()
        for raw in values:
            if raw is None:
                continue
            text = str(raw).strip()
            if not text or text.lower() in {"nan", "none", "nat", "<na>"}:
                continue
            bucket.add(text)
        by_column[name] = bucket
        union.update(bucket)
    return OwnerIds(by_column, union, None)


def _owner_holds(owner: OwnerIds, key: str, value: str) -> bool:
    cols = IDENTITY_KEY_TO_COLUMNS.get(key.casefold(), (key,))
    present = [c for c in cols if c in owner.by_column]
    if present:
        return any(value in owner.by_column[c] for c in present)
    return value in owner.union


def _ast_const(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    return ast.unparse(node) if hasattr(ast, "unparse") else None


def _assigned_names(node: ast.AST) -> list[str]:
    names: list[str] = []
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                names.append(target.id)
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        names.append(node.target.id)
    return names


def _dict_like(node: ast.AST | None) -> ast.AST | None:
    if node is None:
        return None
    if isinstance(node, (ast.Dict, ast.DictComp)):
        return node
    if isinstance(node, ast.Call):
        for arg in list(node.args) + [kw.value for kw in node.keywords if kw.value]:
            found = _dict_like(arg)
            if found is not None:
                return found
    return None


def _date_from_call(node: ast.AST) -> date | None:
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    is_date = (
        (isinstance(func, ast.Name) and func.id == "date")
        or (isinstance(func, ast.Attribute) and func.attr == "date")
    )
    if not is_date:
        return None
    nums: list[int] = []
    for arg in node.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
            nums.append(arg.value)
        else:
            return None
    if len(nums) >= 3:
        try:
            return date(nums[0], nums[1], nums[2])
        except ValueError:
            return None
    kwargs = {}
    for kw in node.keywords:
        if kw.arg in {"year", "month", "day"} and isinstance(kw.value, ast.Constant):
            if isinstance(kw.value.value, int):
                kwargs[kw.arg] = kw.value.value
    if {"year", "month", "day"} <= set(kwargs):
        try:
            return date(kwargs["year"], kwargs["month"], kwargs["day"])
        except ValueError:
            return None
    return None


def _horizon_seq(value: Any) -> tuple[int, ...] | None:
    if isinstance(value, (list, tuple)) and value and all(
        type(x) is int for x in value
    ):
        return tuple(value)
    return None


def _ast_horizon_seq(node: ast.AST) -> tuple[int, ...] | None:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    nums: list[int] = []
    for elt in node.elts:
        if isinstance(elt, ast.Constant) and type(elt.value) is int:
            nums.append(elt.value)
        else:
            return None
    if not nums:
        return None
    return tuple(nums)


def _extract_split_dates(key: str, value: Any) -> list[tuple[str, date, str]]:
    """Narrow extractor: TUNE start / QUARANTINE start from a declaration."""
    folded = key.casefold()
    found: list[tuple[str, date, str]] = []

    def add(role: str, iso: str, raw: str) -> None:
        try:
            found.append((role, date.fromisoformat(iso), raw))
        except ValueError:
            return

    if isinstance(value, date):
        if "quarantine" in folded or (folded.endswith("_end") and "tune" in folded):
            found.append(("quarantine_start", value, value.isoformat()))
        elif "tune" in folded or (folded.endswith("_end") and "train" in folded):
            found.append(("tune_start", value, value.isoformat()))
        elif "train" in folded and "start" in folded:
            pass
        return found

    if not isinstance(value, str):
        return found
    raw = value
    m = WINDOW_TUNE.search(raw)
    if m:
        add("tune_start", m.group(1), raw)
        add("quarantine_start", m.group(2), raw)
        return found
    if folded in {"train"} or folded.endswith("train"):
        m = TRAIN_LT.search(raw)
        if m:
            add("tune_start", m.group(1), raw)
        m = PURGE_TRAIN.search(raw)
        if m:
            add("tune_start", m.group(1), raw)
        return found
    if folded in {"tune"} or (folded.endswith("tune") and "quarantine" not in folded):
        m = WINDOW_TUNE.search(raw)
        if m:
            add("tune_start", m.group(1), raw)
            add("quarantine_start", m.group(2), raw)
        m = PURGE_TUNE.search(raw)
        if m:
            add("quarantine_start", m.group(1), raw)
        return found
    if "quarantine" in folded:
        m = QUAR_GE.search(raw)
        if m:
            add("quarantine_start", m.group(1), raw)
        return found
    m = PURGE_TRAIN.search(raw)
    if m:
        add("tune_start", m.group(1), raw)
    m = PURGE_TUNE.search(raw)
    if m:
        add("quarantine_start", m.group(1), raw)
    m = WINDOW_TUNE.search(raw)
    if m:
        add("tune_start", m.group(1), raw)
        add("quarantine_start", m.group(2), raw)
    elif "quarantine" in folded:
        m = QUAR_GE.search(raw)
        if m:
            add("quarantine_start", m.group(1), raw)
    return found


def _is_split_boundary_key(key: str) -> bool:
    folded = key.casefold()
    if folded in SPLIT_LEAF_FOLDED:
        return True
    if SPLIT_BOUNDARY_NAME.search(key):
        return True
    return False


def _check_authority_map(rel: str, key_path: str, mapping: dict, report: ScanReport) -> None:
    if _is_schema_node(mapping):
        props = mapping.get("properties")
        if isinstance(props, dict):
            for pk, pv in props.items():
                if pk.casefold() in AUTHORITY_FLAG_FOLDED:
                    report.authority_checked += 1
                    if not _is_schema_false_constraint(pv) and pv is not False:
                        report.violations.append(Violation(
                            rel, f"{key_path}.{pk}", "authority",
                            f"schema constraint is {pv!r}, required const false",
                        ))
        extra = mapping.get("additionalProperties")
        if extra is True:
            report.authority_checked += 1
            report.violations.append(Violation(
                rel, f"{key_path}.additionalProperties", "authority",
                "additionalProperties is true on an authority map",
            ))
        return
    for mk, mv in mapping.items():
        report.authority_checked += 1
        if isinstance(mv, dict):
            _check_authority_map(rel, f"{key_path}.{mk}", mv, report)
            continue
        if mv is not False:
            report.violations.append(Violation(
                rel, f"{key_path}.{mk}", "authority",
                f"value {mv!r} is not literal false",
            ))


def _scan_structured(rel: str, obj: Any, report: ScanReport, owner: OwnerIds) -> None:
    for parts, key, value in _walk(obj, ()):
        folded = key.casefold()
        dotted = _dotted(parts)

        if folded in AUTHORITY_FLAG_FOLDED:
            report.authority_checked += 1
            if value is not False and not _is_schema_false_constraint(value):
                report.violations.append(Violation(
                    rel, dotted, "authority",
                    f"value {value!r} is not literal false",
                ))

        if folded in AUTHORITY_MAP_KEYS and isinstance(value, dict):
            _check_authority_map(rel, dotted, value, report)

        if folded in IDENTITY_ID_FOLDED:
            report.identity_checked += 1
            if _is_schema_node(value):
                pass
            elif value in UNKNOWN_IDENTITY:
                pass
            elif isinstance(value, str):
                if owner.skip_reason:
                    pass
                elif not _owner_holds(owner, key, value):
                    report.violations.append(Violation(
                        rel, dotted, "identity",
                        f"value {value!r} is not null/UNRESOLVED and not in "
                        "data/reference/security_master.parquet",
                    ))
            else:
                report.violations.append(Violation(
                    rel, dotted, "identity",
                    f"value {value!r} is not null/UNRESOLVED and not owner-supplied",
                ))

        if folded in HORIZON_KEY_FOLDED:
            seq = _horizon_seq(value)
            if seq is not None:
                shown = repr(list(seq))
                report.horizon_declarations.append(Declaration(
                    rel, dotted, "horizon", "horizons", shown,
                ))
                if seq != REQUIRED_HORIZONS and rel not in ALLOWED_HORIZON_DEVIATIONS:
                    report.violations.append(Violation(
                        rel, dotted, "horizons",
                        f"{shown} != [5, 21, 63]",
                    ))

        if _is_split_boundary_key(key):
            if isinstance(value, str) or isinstance(value, date):
                report.split_declarations.append(Declaration(
                    rel, dotted, "split", "declaration",
                    value if isinstance(value, str) else value.isoformat(),
                ))
            for role, bound, raw in _extract_split_dates(key, value):
                if rel in ALLOWED_SPLIT_DEVIATIONS:
                    continue
                expected = TUNE_START if role == "tune_start" else QUARANTINE_START
                if bound != expected:
                    report.violations.append(Violation(
                        rel, dotted, "split",
                        f"{role} {bound.isoformat()} != {expected.isoformat()} ({raw!r})",
                    ))


def _scan_python(rel: str, tree: ast.AST, report: ScanReport, owner: OwnerIds) -> None:
    class Visitor(ast.NodeVisitor):
        def visit_Assign(self, node: ast.Assign) -> None:
            self._check_assign(node)
            self.generic_visit(node)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            self._check_assign(node)
            self.generic_visit(node)

        def visit_Dict(self, node: ast.Dict) -> None:
            self._inspect_dict(node)
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            for kw in node.keywords:
                if not kw.arg:
                    continue
                if kw.arg.casefold() in AUTHORITY_FLAG_FOLDED:
                    report.authority_checked += 1
                    const = kw.value
                    if not (isinstance(const, ast.Constant) and const.value is False):
                        report.violations.append(Violation(
                            rel, kw.arg, "authority",
                            f"keyword argument {kw.arg}={ast.dump(kw.value)} "
                            "is not literal False",
                        ))
            self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._defaults(node)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._defaults(node)
            self.generic_visit(node)

        def _defaults(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            pos = node.args.args
            pos_defs = node.args.defaults
            if pos_defs:
                for name_node, default in zip(pos[-len(pos_defs):], pos_defs):
                    self._flag_default(name_node.arg, default)
            for name_node, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
                if default is not None:
                    self._flag_default(name_node.arg, default)

        def _flag_default(self, name: str, default: ast.AST) -> None:
            if name.casefold() not in AUTHORITY_FLAG_FOLDED:
                return
            report.authority_checked += 1
            if not (isinstance(default, ast.Constant) and default.value is False):
                report.violations.append(Violation(
                    rel, name, "authority",
                    f"default {name}={ast.dump(default)} is not literal False",
                ))

        def _check_assign(self, node: ast.Assign | ast.AnnAssign) -> None:
            names = _assigned_names(node)
            value = node.value
            for name in names:
                if name.casefold() in HORIZON_KEY_FOLDED and value is not None:
                    seq = _ast_horizon_seq(value)
                    if seq is not None:
                        shown = repr(list(seq))
                        report.horizon_declarations.append(Declaration(
                            rel, name, "horizon", "horizons", shown,
                        ))
                        if seq != REQUIRED_HORIZONS and rel not in ALLOWED_HORIZON_DEVIATIONS:
                            report.violations.append(Violation(
                                rel, name, "horizons",
                                f"{shown} != [5, 21, 63]",
                            ))
                if SPLIT_BOUNDARY_NAME.search(name) or name.casefold() in SPLIT_LEAF_FOLDED:
                    bound = _date_from_call(value) if value is not None else None
                    if bound is not None:
                        report.split_declarations.append(Declaration(
                            rel, name, "split", "declaration", bound.isoformat(),
                        ))
                        if rel not in ALLOWED_SPLIT_DEVIATIONS:
                            folded = name.casefold()
                            if "quarantine" in folded or (
                                folded.endswith("_end") and "tune" in folded
                            ):
                                if bound != QUARANTINE_START:
                                    report.violations.append(Violation(
                                        rel, name, "split",
                                        f"quarantine start {bound.isoformat()} "
                                        f"!= {QUARANTINE_START.isoformat()}",
                                    ))
                            elif "tune" in folded or (
                                folded.endswith("_end") and "train" in folded
                            ) or "tunee" in folded:
                                if bound != TUNE_START:
                                    report.violations.append(Violation(
                                        rel, name, "split",
                                        f"tune start {bound.isoformat()} "
                                        f"!= {TUNE_START.isoformat()}",
                                    ))
                if _is_authority_map_name(name) and value is not None:
                    dict_node = _dict_like(value)
                    if isinstance(dict_node, ast.Dict):
                        self._check_authority_dict(name, dict_node)
                    elif isinstance(dict_node, ast.DictComp):
                        report.authority_checked += 1
                        val = dict_node.value
                        if not (isinstance(val, ast.Constant) and val.value is False):
                            report.violations.append(Violation(
                                rel, name, "authority",
                                "dict comprehension value is not literal False",
                            ))

        def _check_authority_dict(self, name: str, node: ast.Dict) -> None:
            for k_node, v_node in zip(node.keys, node.values):
                if k_node is None:
                    continue
                report.authority_checked += 1
                if not (isinstance(v_node, ast.Constant) and v_node.value is False):
                    key_shown = _ast_const(k_node)
                    report.violations.append(Violation(
                        rel, f"{name}.{key_shown}", "authority",
                        f"dict literal value {_ast_const(v_node)!r} is not "
                        "literal False",
                    ))

        def _inspect_dict(self, node: ast.Dict) -> None:
            for k_node, v_node in zip(node.keys, node.values):
                if k_node is None or not isinstance(k_node, ast.Constant):
                    continue
                if not isinstance(k_node.value, str):
                    continue
                folded = k_node.value.casefold()
                if folded in HORIZON_KEY_FOLDED:
                    seq = _ast_horizon_seq(v_node)
                    if seq is not None:
                        shown = repr(list(seq))
                        report.horizon_declarations.append(Declaration(
                            rel, k_node.value, "horizon", "horizons", shown,
                        ))
                        if (
                            seq != REQUIRED_HORIZONS
                            and rel not in ALLOWED_HORIZON_DEVIATIONS
                        ):
                            report.violations.append(Violation(
                                rel, k_node.value, "horizons",
                                f"{shown} != [5, 21, 63]",
                            ))
                if folded in IDENTITY_ID_FOLDED:
                    report.identity_checked += 1
                    if isinstance(v_node, ast.Constant):
                        val = v_node.value
                        if val in UNKNOWN_IDENTITY:
                            pass
                        elif isinstance(val, str):
                            if owner.skip_reason:
                                pass
                            elif not _owner_holds(owner, k_node.value, val):
                                report.violations.append(Violation(
                                    rel, k_node.value, "identity",
                                    f"value {val!r} is not null/UNRESOLVED "
                                    "and not in security_master.parquet",
                                ))
                        elif val is not None:
                            report.violations.append(Violation(
                                rel, k_node.value, "identity",
                                f"value {val!r} is not null/UNRESOLVED",
                            ))
                if _is_split_boundary_key(k_node.value) and isinstance(
                    v_node, ast.Constant
                ) and isinstance(v_node.value, str):
                    raw = v_node.value
                    report.split_declarations.append(Declaration(
                        rel, k_node.value, "split", "declaration", raw,
                    ))
                    if rel not in ALLOWED_SPLIT_DEVIATIONS:
                        for role, bound, shown in _extract_split_dates(
                            k_node.value, raw
                        ):
                            expected = (
                                TUNE_START if role == "tune_start"
                                else QUARANTINE_START
                            )
                            if bound != expected:
                                report.violations.append(Violation(
                                    rel, k_node.value, "split",
                                    f"{role} {bound.isoformat()} != "
                                    f"{expected.isoformat()} ({shown!r})",
                                ))

    Visitor().visit(tree)


def _scan_regex_ids(rel: str, text: str, report: ScanReport, owner: OwnerIds) -> None:
    if owner.skip_reason:
        return
    seen: set[str] = set()
    for match in ID_SHAPE.finditer(text):
        token = match.group(0)
        if token in seen:
            continue
        seen.add(token)
        report.identity_checked += 1
        if token not in owner.union:
            report.violations.append(Violation(
                rel, token, "identity",
                f"shaped id {token} is not present in "
                "data/reference/security_master.parquet",
            ))


def _scan_secrets(rel: str, text: str, report: ScanReport) -> None:
    for needle in SECRET_NEEDLES:
        count = text.count(needle)
        if count:
            report.secret_hits += count
            report.violations.append(Violation(
                rel, needle, "secrets",
                f"substring {needle!r} occurs {count} time(s)",
            ))


def scan_tree(root: Path, owner_ids: OwnerIds | None = None) -> ScanReport:
    """Scan SNI artifacts under ``root``. Owner ids default to ``root`` then REPO_ROOT."""
    root = Path(root)
    report = ScanReport(root=str(root))
    if owner_ids is None:
        owner_ids = load_owner_ids(root)
        if owner_ids.skip_reason and root.resolve() != REPO_ROOT.resolve():
            fallback = load_owner_ids(REPO_ROOT)
            if fallback.skip_reason is None:
                owner_ids = fallback
    report.owner_skip_reason = owner_ids.skip_reason
    counts: Counter[str] = Counter()
    for path in iter_scan_files(root):
        rel = _posix(root, path)
        suf = path.suffix.lower()
        counts[SCAN_EXTS[suf]] += 1
        report.files_read.append(rel)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            report.parse_errors.append(Violation(
                rel, "", "parse", f"could not read: {exc}",
            ))
            continue
        _scan_secrets(rel, text, report)
        if suf == ".py":
            try:
                tree = ast.parse(text, filename=rel)
            except SyntaxError as exc:
                report.parse_errors.append(Violation(
                    rel, "", "parse", f"ast parse failed: {exc}",
                ))
                continue
            _scan_python(rel, tree, report, owner_ids)
            _scan_regex_ids(rel, text, report, owner_ids)
            continue
        try:
            obj = parse_structured(path)
        except Exception as exc:  # noqa: BLE001 - parse failure is a test failure
            report.parse_errors.append(Violation(
                rel, "", "parse", f"{type(exc).__name__}: {exc}",
            ))
            continue
        if obj is not None:
            _scan_structured(rel, obj, report, owner_ids)
        _scan_regex_ids(rel, text, report, owner_ids)
    report.file_counts = dict(sorted(counts.items()))
    return report


def find_authority_violations(root: Path) -> list[Violation]:
    report = scan_tree(root)
    return [v for v in report.violations if v.invariant == "authority"] + report.parse_errors


def find_identity_violations(
    root: Path, owner_ids: OwnerIds | None = None
) -> list[Violation]:
    report = scan_tree(root, owner_ids=owner_ids)
    return [v for v in report.violations if v.invariant == "identity"] + report.parse_errors


def find_split_violations(root: Path) -> list[Violation]:
    report = scan_tree(root)
    return [v for v in report.violations if v.invariant == "split"] + report.parse_errors


def find_horizon_violations(root: Path) -> list[Violation]:
    report = scan_tree(root)
    return [v for v in report.violations if v.invariant == "horizons"] + report.parse_errors


def find_secret_violations(root: Path) -> list[Violation]:
    report = scan_tree(root)
    return [v for v in report.violations if v.invariant == "secrets"] + report.parse_errors


@pytest.fixture(scope="module")
def repo_report() -> ScanReport:
    return scan_tree(REPO_ROOT)


def test_inv_00_skipped_paths_exist() -> None:
    for rel, reason in SKIPPED.items():
        assert isinstance(reason, str) and reason.strip(), f"SKIPPED[{rel!r}] has no reason"
        target = REPO_ROOT / rel
        assert target.exists(), f"SKIPPED path does not exist: {rel}"
    for path in iter_scan_files(REPO_ROOT):
        if path.stat().st_size > MAX_FILE_BYTES:
            rel = _posix(REPO_ROOT, path)
            assert rel in SKIPPED, (
                f"{rel} is > 20 MB and must be listed in SKIPPED with a reason"
            )


def test_inv_01_authority_flags_false(repo_report: ScanReport) -> None:
    assert repo_report.parse_errors == [], (
        "parse failures:\n" + "\n".join(
            f"{v.path}: {v.detail}" for v in repo_report.parse_errors
        )
    )
    bad = [v for v in repo_report.violations if v.invariant == "authority"]
    assert repo_report.authority_checked > 0
    assert bad == [], (
        "authority flags not literal false:\n"
        + "\n".join(f"{v.path} {v.key}: {v.detail}" for v in bad)
    )


def test_inv_02_identity_ids_owner_supplied(repo_report: ScanReport) -> None:
    assert repo_report.parse_errors == []
    if repo_report.owner_skip_reason:
        pytest.skip(repo_report.owner_skip_reason)
    bad = [v for v in repo_report.violations if v.invariant == "identity"]
    assert repo_report.identity_checked > 0
    assert bad == [], (
        "identity ids not owner-supplied:\n"
        + "\n".join(f"{v.path} {v.key}: {v.detail}" for v in bad)
    )


def test_inv_03_split_law_boundaries(repo_report: ScanReport) -> None:
    assert repo_report.parse_errors == []
    bad = [v for v in repo_report.violations if v.invariant == "split"]
    assert repo_report.split_declarations, "no split-boundary declarations found"
    assert bad == [], (
        "split boundaries disagree with S0 register §2 "
        "(TUNE start 2024-01-01, QUARANTINE start 2026-10-01):\n"
        + "\n".join(f"{v.path} {v.key}: {v.detail}" for v in bad)
    )


def test_inv_04_horizons_5_21_63(repo_report: ScanReport) -> None:
    assert repo_report.parse_errors == []
    bad = [v for v in repo_report.violations if v.invariant == "horizons"]
    assert repo_report.horizon_declarations, "no GRADE_HORIZONS/HORIZONS declarations found"
    assert bad == [], (
        "horizons != [5, 21, 63]:\n"
        + "\n".join(f"{v.path} {v.key}: {v.detail}" for v in bad)
    )


def test_inv_05_no_private_material(repo_report: ScanReport) -> None:
    assert repo_report.parse_errors == []
    bad = [v for v in repo_report.violations if v.invariant == "secrets"]
    assert repo_report.secret_hits == 0
    assert bad == [], (
        "secret-shape substrings:\n"
        + "\n".join(f"{v.path} {v.key}: {v.detail}" for v in bad)
    )


def test_inv_06_positive_control_poisons(tmp_path: Path) -> None:
    sni = tmp_path / "research" / "single_name_intelligence"
    sni.mkdir(parents=True)
    (sni / "poison_authority.yml").write_text(
        "trade_authority: true\n", encoding="utf-8",
    )
    (sni / "poison_identity.json").write_text(
        json.dumps({"security_id": "SEC:US-XNAS-FAKE"}) + "\n",
        encoding="utf-8",
    )
    (sni / "poison_flags.py").write_text(
        "AUTHORITY_FLAGS = {\"rank\": True}\n", encoding="utf-8",
    )
    (sni / "poison_split.json").write_text(
        json.dumps({"splits": {"QUARANTINE": "s >= 2026-09-01"}}) + "\n",
        encoding="utf-8",
    )
    (sni / "poison_horizons.json").write_text(
        json.dumps({"GRADE_HORIZONS": [5, 20, 63]}) + "\n",
        encoding="utf-8",
    )

    owner = load_owner_ids(REPO_ROOT)
    report = scan_tree(tmp_path, owner_ids=owner)

    def has(invariant: str, token: str) -> bool:
        blob = " ".join(
            f"{v.path}|{v.key}|{v.detail}"
            for v in report.violations if v.invariant == invariant
        )
        return token in blob

    assert has("authority", "trade_authority"), report.violations
    assert has("identity", "SEC:US-XNAS-FAKE"), report.violations
    assert has("authority", "AUTHORITY_FLAGS"), report.violations
    assert has("split", "2026-09-01"), report.violations
    assert has("horizons", "5, 20, 63") or has("horizons", "[5, 20, 63]"), (
        report.violations
    )
    assert report.parse_errors == []
