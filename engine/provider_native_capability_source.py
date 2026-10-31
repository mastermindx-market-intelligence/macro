"""Fixed native registration acquisition under Shared AI Provider Control.

This projector derives source identity; it does not authenticate an accepted
release. The incumbent Capacity source owner must bind the returned commit to
its admitted, immutable release. Only for that qualified single-parent release
does its parent identify the preceding accepted source. A local branch or a
content digest cannot supply that qualification.

No input selects a registry, predecessor, digest, generation or state. There is
no realm enrollment, credential access, availability assertion or dispatch here.
The V1 implementation and its material census are reused without modification.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

from engine import provider_capacity as capacity
from engine.provider_native_capabilities import (
    NativeCapabilityError, registration_export, validate_registry_transition,
)

REGISTRY_PATH = "config/provider_native_capabilities.v1.json"
MATERIAL_SOURCE_PATHS = tuple(sorted((*capacity.MATERIAL_SOURCE_PATHS,
    REGISTRY_PATH,
    "engine/provider_native_capabilities.py",
    "engine/provider_native_capability_source.py",
    "scripts/build_provider_native_capability_registration.py",
)))
MAX_REGISTRY_BYTES = 131072
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")


class NativeSourceError(ValueError):
    """A bounded refusal; input contents never appear in the message."""


@dataclass(frozen=True)
class RegistrationSource:
    repository_commit: str
    previous_repository_commit: str
    material_source_digest: str
    registrations: tuple[dict, ...]


def _git(root: Path, *args: str) -> bytes:
    try:
        return capacity._git_bytes(root, *args)
    except capacity.ProviderCapacityError:
        raise NativeSourceError("SOURCE_IDENTITY_UNAVAILABLE") from None


def _commits(root: Path) -> tuple[str, str]:
    try:
        fields = _git(root, "rev-list", "--parents", "-n", "1", "HEAD").decode("ascii").split()
    except UnicodeDecodeError:
        raise NativeSourceError("SOURCE_IDENTITY_UNAVAILABLE") from None
    # Never guess which parent was accepted, or infer an empty registry from
    # missing/shallow history. Protected release qualification stays upstream.
    if len(fields) != 2 or any(not _COMMIT.fullmatch(x) for x in fields):
        raise NativeSourceError("SINGLE_PARENT_SOURCE_REQUIRED")
    return fields[0], fields[1]


def _identity(root: Path, commit: str) -> str:
    try:
        rows, local = capacity._material_rows(root, MATERIAL_SOURCE_PATHS)
        committed = capacity._committed_material_oids(root, commit, MATERIAL_SOURCE_PATHS)
    except (OSError, RuntimeError, capacity.ProviderCapacityError):
        raise NativeSourceError("MATERIAL_SOURCE_UNAVAILABLE") from None
    if local != committed or set(committed) != set(MATERIAL_SOURCE_PATHS):
        raise NativeSourceError("MATERIAL_SOURCE_UNGROUNDED")
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise NativeSourceError("REGISTRY_SOURCE_INVALID")
        result[key] = value
    return result


def _registry(root: Path, commit: str) -> dict:
    # Tree mode checking refuses symlinks, directories and absent predecessors.
    # Read only this fixed blob, never an arbitrary path supplied by a caller.
    try:
        oids = capacity._committed_material_oids(root, commit, (REGISTRY_PATH,))
    except capacity.ProviderCapacityError:
        raise NativeSourceError("REGISTRY_SOURCE_UNAVAILABLE") from None
    if set(oids) != {REGISTRY_PATH}:
        raise NativeSourceError("REGISTRY_SOURCE_UNAVAILABLE")
    oid = oids[REGISTRY_PATH]
    size = _git(root, "cat-file", "-s", oid).strip()
    if not size.isdigit() or not 0 < int(size) <= MAX_REGISTRY_BYTES:
        raise NativeSourceError("REGISTRY_SOURCE_INVALID")
    raw = _git(root, "cat-file", "blob", oid)
    if len(raw) != int(size):
        raise NativeSourceError("REGISTRY_SOURCE_INVALID")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                          parse_constant=lambda _: _invalid_json())
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        raise NativeSourceError("REGISTRY_SOURCE_INVALID") from None


def _invalid_json():
    raise NativeSourceError("REGISTRY_SOURCE_INVALID")


def _read_source(root: Path) -> RegistrationSource:
    """Internal filesystem seam for owner tests; not a public input surface."""
    root = root.resolve(strict=True)
    commit, previous = _commits(root)
    digest = _identity(root, commit)
    current_registry = _registry(root, commit)
    previous_registry = _registry(root, previous)
    try:
        registry = validate_registry_transition(previous_registry, current_registry)
        exports = tuple(registration_export(registry, row["capacity_capability_id"],
                         material_source_digest=digest) for row in registry["capabilities"])
    except NativeCapabilityError as exc:
        raise NativeSourceError(exc.code) from None
    # Re-read both refs and actual material after collection. No bytes can be
    # exported under an identity that changed while these facts were acquired.
    if _commits(root) != (commit, previous) or _identity(root, commit) != digest:
        raise NativeSourceError("SOURCE_CHANGED_DURING_ACQUISITION")
    return RegistrationSource(commit, previous, digest, exports)


def current_registration_source() -> RegistrationSource:
    """Collect exact current source facts; no caller-supplied source overrides."""
    return _read_source(Path(__file__).resolve().parent.parent)
