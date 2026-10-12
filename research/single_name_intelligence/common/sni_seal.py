"""SNI-local DRAFT seal contract (sni_seal.v1).

stdlib-only (json, hashlib, dataclasses, datetime, types, pathlib). Authority
flags are hard-false: rank, gate, size, signal, escalation, and trade authority
are always False, and callers cannot set them true. This module consumes
owner-supplied identity facts (Data OS identity, Stock Identity, and related
owners) and never mints, derives, or guesses issuer or security ids.

This is not an implementation of Data OS identity, Company Event/Earnings, FIF,
Capital Structure, Stock Identity, Options, Research Vault, or qledger/
Evaluation. Those owners remain the source of identity, event, capital,
options, vault, and evaluation values; this library only records caller-supplied
opaque strings (or UNRESOLVED / null) plus input-manifest pins and a
canonical content digest. Nothing here feeds a ranker, gate, sizer, signal,
escalation, or trade path.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType

SCHEMA_VERSION = "sni_seal.v1"

AUTHORITY_FLAG_KEYS = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

_HEX64 = "0123456789abcdef"
_CELL_KEYS = frozenset({"protocol", "version", "split", "h"})
_FORBIDDEN_EXTRA = frozenset(AUTHORITY_FLAG_KEYS) | {"authority_flags"}
_HARD_FALSE_AUTHORITY = MappingProxyType({key: False for key in AUTHORITY_FLAG_KEYS})


@dataclass(frozen=True, order=True)
class _CellKey:
    protocol: object
    version: object
    split: object
    h: object


def canonical_json(obj) -> str:
    """Deterministic JSON: sorted keys, compact separators, UTF-8, trailing newline.

    Finite floats only; NaN and inf raise ValueError.
    """
    try:
        return json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n"
    except ValueError as exc:
        raise ValueError("canonical_json requires finite floats (no NaN or inf)") from exc


def sha256_bytes(b: bytes) -> str:
    if not isinstance(b, (bytes, bytearray, memoryview)):
        raise ValueError("sha256_bytes requires bytes")
    return hashlib.sha256(bytes(b)).hexdigest()


def sha256_text(s: str) -> str:
    if not isinstance(s, str):
        raise ValueError("sha256_text requires str")
    return sha256_bytes(s.encode("utf-8"))


def sha256_file(path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def _is_hex64(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in _HEX64 for c in value)


def _is_str_or_int(value) -> bool:
    return type(value) is str or type(value) is int


def _require_hex64(name: str, value) -> str:
    if not _is_hex64(value):
        raise ValueError(f"{name} must be a 64-char lowercase hex digest")
    return value


def _validate_sealed_at_utc(value) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("sealed_at_utc must be an ISO-8601 Z string")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("sealed_at_utc must be an ISO-8601 Z string") from exc
    return value


def _check_identity_id_values(obj, path: str = "identity_facts") -> None:
    """Owner-supplied *_id values must be str or None; this library never constructs them."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            here = f"{path}.{key}"
            if isinstance(key, str) and key.endswith("_id"):
                if value is not None and not isinstance(value, str):
                    raise ValueError(f"{here} must be a string or None")
            _check_identity_id_values(value, here)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            _check_identity_id_values(value, f"{path}[{index}]")


def _parse_cell(cell) -> _CellKey:
    if not isinstance(cell, dict) or set(cell.keys()) != _CELL_KEYS:
        raise ValueError("each cell must have exactly keys {protocol, version, split, h}")
    for field in ("protocol", "version", "split", "h"):
        if not _is_str_or_int(cell[field]):
            raise ValueError(f"cell.{field} must be a string or int")
    return _CellKey(cell["protocol"], cell["version"], cell["split"], cell["h"])


def _normalize_cells(cells) -> list[dict]:
    if not isinstance(cells, list):
        raise ValueError("cells must be a list")
    parsed = [_parse_cell(cell) for cell in cells]
    seen = set()
    for key in parsed:
        if key in seen:
            raise ValueError("duplicate cells")
        seen.add(key)
    try:
        parsed_sorted = sorted(parsed)
    except TypeError as exc:
        raise ValueError("cells are not comparable for sort") from exc
    return [
        {
            "protocol": item.protocol,
            "version": item.version,
            "split": item.split,
            "h": item.h,
        }
        for item in parsed_sorted
    ]


def _normalize_budgets(budgets) -> dict:
    if not isinstance(budgets, dict):
        raise ValueError("budgets must be a dict")
    out = {}
    for family, n in budgets.items():
        if not isinstance(family, str):
            raise ValueError("budget family keys must be strings")
        if type(n) is not int or n <= 0:
            raise ValueError(f"budget for {family} must be a positive int")
        out[family] = n
    return out


def _normalize_manifest(input_manifest) -> list[dict]:
    if not isinstance(input_manifest, list):
        raise ValueError("input_manifest must be a list")
    entries = []
    for item in input_manifest:
        if not isinstance(item, dict) or set(item.keys()) != {"path", "sha256"}:
            raise ValueError("input_manifest entries must have exactly keys {path, sha256}")
        path = item["path"]
        digest = item["sha256"]
        if not isinstance(path, str) or not path:
            raise ValueError("input_manifest path must be a non-empty string")
        _require_hex64("input_manifest.sha256", digest)
        entries.append({"path": path, "sha256": digest})
    return sorted(entries, key=lambda entry: entry["path"])


def _normalize_string_list(name: str, values) -> list[str]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{name} must be a list of strings")
    out = []
    for item in values:
        if not isinstance(item, str):
            raise ValueError(f"{name} must be a list of strings")
        out.append(item)
    return sorted(out)


def _authority_flags_hard_false(extra: dict) -> dict:
    overlap = _FORBIDDEN_EXTRA.intersection(extra)
    if overlap:
        raise ValueError(
            "extra must not contain authority_flags or any authority flag key; "
            f"refused: {sorted(overlap)}"
        )
    return {key: False for key in AUTHORITY_FLAG_KEYS}


def build_seal(
    *,
    lane: str,
    protocol_ids: list[str],
    cells: list[dict],
    budgets: dict[str, int],
    input_manifest: list[dict],
    prereg_digest: str,
    identity_facts: dict,
    sealed_at_utc: str,
    repo_ref: str,
    not_supported: list[str] = (),
    extra: dict | None = None,
) -> dict:
    """Build an sni_seal.v1 object with authority flags hard-false and a content digest."""
    if not isinstance(lane, str) or not lane:
        raise ValueError("lane must be a non-empty string")
    if not isinstance(repo_ref, str) or not repo_ref:
        raise ValueError("repo_ref must be a non-empty string")
    if extra is None:
        extra_out = {}
    elif not isinstance(extra, dict):
        raise ValueError("extra must be a dict")
    else:
        extra_out = dict(extra)
    if not isinstance(identity_facts, dict):
        raise ValueError("identity_facts must be a dict")
    identity_out = dict(identity_facts)
    _check_identity_id_values(identity_out)
    _require_hex64("prereg_digest", prereg_digest)
    _validate_sealed_at_utc(sealed_at_utc)

    seal = {
        "schema_version": SCHEMA_VERSION,
        "lane": lane,
        "protocol_ids": _normalize_string_list("protocol_ids", protocol_ids),
        "cells": _normalize_cells(cells),
        "budgets": _normalize_budgets(budgets),
        "input_manifest": _normalize_manifest(input_manifest),
        "prereg_digest": prereg_digest,
        "identity_facts": identity_out,
        "sealed_at_utc": sealed_at_utc,
        "repo_ref": repo_ref,
        "not_supported": _normalize_string_list("not_supported", not_supported),
        "authority_flags": _authority_flags_hard_false(extra_out),
        "outcome_free": True,
        "extra": extra_out,
    }
    seal["content_digest"] = sha256_text(canonical_json(seal))
    return seal


def verify_seal(seal: dict, *, file_bytes: dict[str, bytes] | None = None) -> list[str]:
    """Return violation strings; empty means the seal is valid."""
    violations: list[str] = []
    if not isinstance(seal, dict):
        return ["seal is not an object"]

    if seal.get("schema_version") != SCHEMA_VERSION:
        violations.append("schema_version mismatch")

    flags = seal.get("authority_flags")
    if not isinstance(flags, dict):
        for key in AUTHORITY_FLAG_KEYS:
            violations.append(f"authority_flags.{key} missing")
    else:
        for key in AUTHORITY_FLAG_KEYS:
            if key not in flags:
                violations.append(f"authority_flags.{key} missing")
            elif flags[key] is not False:
                violations.append(f"authority_flags.{key} is not false")

    if seal.get("outcome_free") is not True:
        violations.append("outcome_free is not true")

    cells = seal.get("cells")
    if not isinstance(cells, list):
        violations.append("cells not sorted")
    else:
        keys = []
        well_formed = True
        for cell in cells:
            try:
                keys.append(_parse_cell(cell))
            except ValueError:
                well_formed = False
                break
        if well_formed:
            if len(keys) != len(set(keys)):
                violations.append("duplicate cells")
            try:
                if keys != sorted(keys):
                    violations.append("cells not sorted")
            except TypeError:
                violations.append("cells not sorted")

    budgets = seal.get("budgets")
    if isinstance(budgets, dict):
        for family, n in budgets.items():
            if type(n) is not int or n <= 0:
                violations.append(f"non-positive budget for {family}")

    body = {key: value for key, value in seal.items() if key != "content_digest"}
    try:
        expected = sha256_text(canonical_json(body))
    except (TypeError, ValueError):
        violations.append("content_digest mismatch")
    else:
        if seal.get("content_digest") != expected:
            violations.append("content_digest mismatch")

    if file_bytes is not None:
        manifest = seal.get("input_manifest")
        manifest_paths = set()
        if isinstance(manifest, list):
            for entry in manifest:
                if not isinstance(entry, dict):
                    continue
                path = entry.get("path")
                digest = entry.get("sha256")
                if not isinstance(path, str):
                    continue
                manifest_paths.add(path)
                if path in file_bytes:
                    actual = sha256_bytes(file_bytes[path])
                    if actual != digest:
                        violations.append(
                            f"input_manifest sha256 mismatch for path {path}"
                        )
        for path in file_bytes:
            if path not in manifest_paths:
                violations.append(
                    f"path {path} in file_bytes missing from input_manifest"
                )

    return violations


def render_seal_md(seal) -> str:
    """Deterministic markdown for a seal; flags listed explicitly as false."""
    if not isinstance(seal, dict):
        raise ValueError("seal must be a dict")
    lines = [
        "# SNI seal",
        "",
        f"schema_version: {seal.get('schema_version', '')}",
        f"lane: {seal.get('lane', '')}",
        f"repo_ref: {seal.get('repo_ref', '')}",
        f"sealed_at_utc: {seal.get('sealed_at_utc', '')}",
        f"prereg_digest: {seal.get('prereg_digest', '')}",
        "",
        "authority_flags:",
    ]
    for key in AUTHORITY_FLAG_KEYS:
        lines.append(f"{key}: false")
    cells = seal.get("cells") if isinstance(seal.get("cells"), list) else []
    lines.extend(
        [
            "",
            "outcome_free: true",
            "",
            f"cells: {len(cells)}",
            "",
            "budgets:",
            "",
            "| family | n |",
            "|---|---|",
        ]
    )
    budgets = seal.get("budgets") if isinstance(seal.get("budgets"), dict) else {}
    for family in sorted(budgets):
        lines.append(f"| {family} | {budgets[family]} |")
    lines.extend(
        [
            "",
            "input_manifest:",
            "",
            "| path | sha256 |",
            "|---|---|",
        ]
    )
    manifest = seal.get("input_manifest") if isinstance(seal.get("input_manifest"), list) else []
    for entry in manifest:
        if not isinstance(entry, dict):
            continue
        lines.append(f"| {entry.get('path', '')} | {entry.get('sha256', '')} |")
    lines.extend(
        [
            "",
            f"content_digest: {seal.get('content_digest', '')}",
            "",
        ]
    )
    return "\n".join(lines)


def write_seal(seal, out_dir: Path) -> tuple[Path, Path]:
    """Write SEAL.json (canonical JSON) and SEAL.md under out_dir."""
    if not isinstance(seal, dict):
        raise ValueError("seal must be a dict")
    destination = Path(out_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "SEAL.json"
    md_path = destination / "SEAL.md"
    json_path.write_text(canonical_json(seal), encoding="utf-8")
    md_path.write_text(render_seal_md(seal), encoding="utf-8")
    return json_path, md_path
