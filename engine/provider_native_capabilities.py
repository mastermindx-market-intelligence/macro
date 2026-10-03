"""Secret-free native provider-capability registration owner.

This module owns only deterministic Shared AI Provider Control registration
facts for native Claude subscription capacity. It does not read credentials,
probe providers, enroll host realms, persist mutable account state, dispatch
work, or implement Executive placement.

Current state is checked-in source. Transition validity is evaluated against
the immediately preceding first-parent source state. Registration documents
are emitted only from exact committed bytes.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


REGISTRY_SCHEMA = "mastermind.provider_native_capability_registry/v1"
REGISTRATION_SCHEMA = "mastermind.provider_native_capability_registration/v1"
OWNER_PROGRAM = "shared-ai-provider-control"
REGISTRY_PATH = "config/provider_native_capabilities.v1.json"
MATERIAL_SOURCE_PATHS = (
    REGISTRY_PATH,
    "engine/provider_native_capabilities.py",
)

_CAPABILITY_ID_RE = re.compile(r"^ncap_[0-9a-f]{32}$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")

_ROW_FIELDS = {
    "capacity_capability_id",
    "capability_generation",
    "provider",
    "billing_mode",
    "credential_kind",
    "execution_surface",
    "registration_state",
}
_REGISTRATION_FIELDS = {
    "schema",
    *_ROW_FIELDS,
    "material_source_digest",
    "registration_receipt_digest",
}


class ProviderNativeCapabilityError(ValueError):
    """Bounded refusal from source/transition validation."""


@dataclass(frozen=True)
class MaterialSourceReceipt:
    material_source_digest: str
    repository_commit: str
    material_sources_match_commit: bool


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProviderNativeCapabilityError("NON_CANONICAL_JSON") from exc


def canonical_json(value: Any, *, pretty: bool = False) -> str:
    try:
        if pretty:
            return json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            ) + "\n"
        return _canonical_bytes(value).decode("utf-8") + "\n"
    except ProviderNativeCapabilityError:
        raise
    except (TypeError, ValueError) as exc:
        raise ProviderNativeCapabilityError("NON_CANONICAL_JSON") from exc


def _closed(value: Mapping[str, Any], expected: set[str], code: str) -> None:
    if set(value) != expected:
        raise ProviderNativeCapabilityError(code)


def _validate_row(row: Any) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        raise ProviderNativeCapabilityError("CAPABILITY_ROW_INVALID")
    _closed(row, _ROW_FIELDS, "CAPABILITY_ROW_SCHEMA_INVALID")

    capability_id = row["capacity_capability_id"]
    generation = row["capability_generation"]
    if not isinstance(capability_id, str) or not _CAPABILITY_ID_RE.fullmatch(capability_id):
        raise ProviderNativeCapabilityError("CAPABILITY_ID_INVALID")
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 1:
        raise ProviderNativeCapabilityError("CAPABILITY_GENERATION_INVALID")
    if row["provider"] != "claude":
        raise ProviderNativeCapabilityError("PROVIDER_INVALID")
    if row["billing_mode"] != "subscription":
        raise ProviderNativeCapabilityError("BILLING_MODE_INVALID")
    if row["credential_kind"] != "attached_login":
        raise ProviderNativeCapabilityError("CREDENTIAL_KIND_INVALID")
    if row["execution_surface"] != "native_cli":
        raise ProviderNativeCapabilityError("EXECUTION_SURFACE_INVALID")
    if row["registration_state"] not in {"registered", "revoked"}:
        raise ProviderNativeCapabilityError("REGISTRATION_STATE_INVALID")
    return dict(row)


def validate_registry(document: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(document, Mapping):
        raise ProviderNativeCapabilityError("REGISTRY_SCHEMA_INVALID")
    _closed(document, {"schema", "owner_program", "capabilities"}, "REGISTRY_SCHEMA_INVALID")
    if document["schema"] != REGISTRY_SCHEMA:
        raise ProviderNativeCapabilityError("REGISTRY_SCHEMA_INVALID")
    if document["owner_program"] != OWNER_PROGRAM:
        raise ProviderNativeCapabilityError("OWNER_PROGRAM_INVALID")
    rows = document["capabilities"]
    if not isinstance(rows, list):
        raise ProviderNativeCapabilityError("CAPABILITIES_INVALID")

    normalized = tuple(_validate_row(row) for row in rows)
    identities = [row["capacity_capability_id"] for row in normalized]
    if len(identities) != len(set(identities)):
        raise ProviderNativeCapabilityError("DUPLICATE_CAPABILITY_ID")
    if identities != sorted(identities):
        raise ProviderNativeCapabilityError("CAPABILITY_ORDER_INVALID")
    return normalized


def validate_transition(previous: Any | None, current: Any) -> None:
    current_rows = validate_registry(current)
    current_by_id = {row["capacity_capability_id"]: row for row in current_rows}

    if previous is None:
        for row in current_rows:
            if row["registration_state"] != "registered":
                raise ProviderNativeCapabilityError("INITIAL_STATE_INVALID")
        return

    previous_rows = validate_registry(previous)
    previous_by_id = {row["capacity_capability_id"]: row for row in previous_rows}
    removed = set(previous_by_id) - set(current_by_id)
    if removed:
        raise ProviderNativeCapabilityError("REGISTERED_ID_REMOVED")

    for capability_id, current_row in current_by_id.items():
        previous_row = previous_by_id.get(capability_id)
        if previous_row is None:
            if current_row["registration_state"] != "registered":
                raise ProviderNativeCapabilityError("INITIAL_STATE_INVALID")
            continue

        previous_generation = previous_row["capability_generation"]
        current_generation = current_row["capability_generation"]
        previous_state = previous_row["registration_state"]
        current_state = current_row["registration_state"]

        if current_generation < previous_generation:
            raise ProviderNativeCapabilityError("GENERATION_DECREMENT")

        if previous_state == "registered":
            if current_generation != previous_generation:
                raise ProviderNativeCapabilityError("GENERATION_TRANSITION_INVALID")
            # registered(g) -> registered(g) or revoked(g)
            continue

        # revoked(g) is a tombstone. It may stay revoked at exactly g, or be
        # re-enrolled only as registered(g2) where g2 > g.
        if current_state == "revoked":
            if current_generation != previous_generation:
                raise ProviderNativeCapabilityError("GENERATION_TRANSITION_INVALID")
            continue
        if current_generation == previous_generation:
            raise ProviderNativeCapabilityError("GENERATION_REUSE")
        # current_generation > previous_generation and state == registered
        # is the sole legal re-enrollment transition.


def _registration_facts(
    document: Any,
    *,
    material_source_digest: str,
) -> tuple[dict[str, Any], ...]:
    if not isinstance(material_source_digest, str) or not _DIGEST_RE.fullmatch(material_source_digest):
        raise ProviderNativeCapabilityError("MATERIAL_SOURCE_DIGEST_INVALID")
    rows = validate_registry(document)
    facts: list[dict[str, Any]] = []
    for row in rows:
        unsigned: dict[str, Any] = {
            "schema": REGISTRATION_SCHEMA,
            **row,
            "material_source_digest": material_source_digest,
        }
        receipt_digest = hashlib.sha256(_canonical_bytes(unsigned)).hexdigest()
        fact = {**unsigned, "registration_receipt_digest": receipt_digest}
        _closed(fact, _REGISTRATION_FIELDS, "REGISTRATION_SCHEMA_INVALID")
        facts.append(fact)
    return tuple(facts)


def _git(repo_root: Path, *args: str, allow_failure: bool = False) -> subprocess.CompletedProcess[bytes]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ProviderNativeCapabilityError("REPOSITORY_IDENTITY_UNAVAILABLE") from exc
    if proc.returncode and not allow_failure:
        raise ProviderNativeCapabilityError("REPOSITORY_IDENTITY_UNAVAILABLE")
    return proc


def _material_rows(
    repo_root: Path,
    paths: Sequence[str],
) -> tuple[list[dict[str, str]], dict[str, str]]:
    if not paths or len(paths) != len(set(paths)) or tuple(paths) != tuple(sorted(paths)):
        raise ProviderNativeCapabilityError("MATERIAL_SOURCE_ALLOWLIST_INVALID")
    root = repo_root.resolve(strict=True)
    rows: list[dict[str, str]] = []
    blob_oids: dict[str, str] = {}
    for raw_path in paths:
        relative = Path(raw_path)
        if relative.is_absolute() or ".." in relative.parts or str(relative) != raw_path:
            raise ProviderNativeCapabilityError("MATERIAL_SOURCE_PATH_ESCAPE")
        candidate = root / relative
        if candidate.is_symlink():
            raise ProviderNativeCapabilityError("MATERIAL_SOURCE_SYMLINK")
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ProviderNativeCapabilityError("MATERIAL_SOURCE_MISSING") from exc
        if root not in resolved.parents or not resolved.is_file():
            raise ProviderNativeCapabilityError("MATERIAL_SOURCE_NON_REGULAR")
        try:
            data = resolved.read_bytes()
        except OSError as exc:
            raise ProviderNativeCapabilityError("MATERIAL_SOURCE_UNREADABLE") from exc
        rows.append({"path": raw_path, "sha256": hashlib.sha256(data).hexdigest()})
        blob_header = f"blob {len(data)}\0".encode("ascii")
        blob_oids[raw_path] = hashlib.sha1(blob_header + data).hexdigest()
    return rows, blob_oids


def _committed_material_oids(
    repo_root: Path,
    commit: str,
    paths: Sequence[str],
) -> dict[str, str]:
    raw = _git(
        repo_root,
        "ls-tree",
        "-rz",
        "--full-tree",
        commit,
        "--",
        *paths,
    ).stdout
    result: dict[str, str] = {}
    try:
        for record in raw.split(b"\0"):
            if not record:
                continue
            metadata, separator, raw_path = record.partition(b"\t")
            mode, object_type, object_id = metadata.split(b" ")
            path = raw_path.decode("utf-8", "strict")
            if (
                not separator
                or object_type != b"blob"
                or mode == b"120000"
                or path not in paths
                or path in result
                or not re.fullmatch(rb"[0-9a-f]{40}", object_id)
            ):
                return {}
            result[path] = object_id.decode("ascii")
    except (UnicodeDecodeError, ValueError):
        return {}
    return result


def material_source_receipt(repo_root: Path | None = None) -> MaterialSourceReceipt:
    root = (repo_root or _repo_root()).resolve(strict=True)
    rows, local_blob_oids = _material_rows(root, MATERIAL_SOURCE_PATHS)
    digest = hashlib.sha256(_canonical_bytes(rows)).hexdigest()
    commit = _git(root, "rev-parse", "HEAD").stdout.decode("ascii", "strict").strip()
    if not _SHA_RE.fullmatch(commit):
        raise ProviderNativeCapabilityError("REPOSITORY_IDENTITY_UNAVAILABLE")
    committed = _committed_material_oids(root, commit, MATERIAL_SOURCE_PATHS)
    matches = set(committed) == set(MATERIAL_SOURCE_PATHS) and committed == local_blob_oids
    return MaterialSourceReceipt(digest, commit, matches)


def _load_registry_bytes(raw: bytes, *, code: str) -> dict[str, Any]:
    try:
        document = json.loads(raw.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderNativeCapabilityError(code) from exc
    try:
        validate_registry(document)
    except ProviderNativeCapabilityError as exc:
        raise ProviderNativeCapabilityError(code) from exc
    return document


def _registry_at_commit(repo_root: Path, commit: str) -> dict[str, Any]:
    """Load the exact registry blob from one already-grounded repository commit."""

    if not _SHA_RE.fullmatch(commit):
        raise ProviderNativeCapabilityError("REPOSITORY_IDENTITY_UNAVAILABLE")
    proc = _git(
        repo_root,
        "show",
        f"{commit}:{REGISTRY_PATH}",
        allow_failure=True,
    )
    if proc.returncode:
        raise ProviderNativeCapabilityError("REGISTRY_SOURCE_INVALID")
    return _load_registry_bytes(proc.stdout, code="REGISTRY_SOURCE_INVALID")


def _previous_registry(repo_root: Path, current_commit: str) -> dict[str, Any] | None:
    parent_proc = _git(repo_root, "rev-parse", f"{current_commit}^", allow_failure=True)
    if parent_proc.returncode:
        raise ProviderNativeCapabilityError("PREVIOUS_SOURCE_UNAVAILABLE")
    parent = parent_proc.stdout.decode("ascii", "strict").strip()
    if not _SHA_RE.fullmatch(parent):
        raise ProviderNativeCapabilityError("PREVIOUS_SOURCE_UNAVAILABLE")

    listing = _git(
        repo_root,
        "ls-tree",
        "-z",
        "--name-only",
        parent,
        "--",
        REGISTRY_PATH,
    ).stdout
    paths = [item.decode("utf-8", "strict") for item in listing.split(b"\0") if item]
    if not paths:
        return None
    if paths != [REGISTRY_PATH]:
        raise ProviderNativeCapabilityError("PREVIOUS_SOURCE_INVALID")

    raw = _git(repo_root, "show", f"{parent}:{REGISTRY_PATH}").stdout
    return _load_registry_bytes(raw, code="PREVIOUS_SOURCE_INVALID")


def current_registration_facts(
    *,
    repo_root: Path | None = None,
) -> tuple[dict[str, Any], ...]:
    """Return exact current registration facts from committed Provider Control source."""
    root = (repo_root or _repo_root()).resolve(strict=True)
    receipt = material_source_receipt(root)
    if not receipt.material_sources_match_commit:
        raise ProviderNativeCapabilityError("MATERIAL_SOURCE_UNGROUNDED")
    current = _registry_at_commit(root, receipt.repository_commit)
    previous = _previous_registry(root, receipt.repository_commit)
    validate_transition(previous, current)
    return _registration_facts(current, material_source_digest=receipt.material_source_digest)
