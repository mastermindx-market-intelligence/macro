"""Current metadata-purpose policy for the retained SPY price-source CLI.

This module composes the accepted retained-source metadata reader
(``read_retained_source_bar_metadata``/``disclose_retained_source_bar_metadata``
on the private technical actual-output store) with the current administrator
policy that the assigning owner requires for exactly that metadata purpose.

Trust origin, stated precisely: the approved source deployed by the incumbent
release path plus the existing authenticated OS administrator invocation.  An
euid/path/hash match is consistency evidence, not an independent authentication
of owner authority, and this module is not a security boundary against a
malicious administrator.  Python imports run inside the trusted administrator
process; nothing here claims to sandbox a compromised root host.

The policy owns two duties and no more.  First, it binds one exact immutable
identity quadruple (generation and source-observation IDs plus digests) and
denies unknown actions, extra fields, or any resource drift.  Second, before
any authorization it re-verifies the installed source closure - this policy
module, the CLI entry point, the accepted technical store/observation modules,
the PIT kernel, and the reviewed canary/calendar/license/price-basis bytes -
against the exact deployed Git HEAD captured at qualification.  Grant or basis
drift after a read therefore denies the final disclosure.  These are adopted
existing grant and basis records, not new grants and not proof that any
caller-supplied JSON is genuine.

This is a private one-shot administrator composition path.  It creates no
access ledger, reservation, study installation, scheduler, service, registry,
network call, or runtime write, and it never substitutes a house Yahoo/FRED
policy for the bound Massive entitlement record.
"""

from __future__ import annotations

import copy
import hashlib
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Any, Callable

from engine.neuralweb import market_memory_technical_store as store

POLICY_ID = "market_memory.price_metadata_use.installed_admin.v1"
INSTALLED_REPOSITORY_ROOT = Path("/opt/macro")

_ACTIONS = (
    "read_retained_source_bar_metadata",
    "disclose_retained_source_bar_metadata",
)
_RESOURCE_FIELDS = (
    "profile",
    "store_id",
    "generation_id",
    "generation_sha256",
    "source_observation_id",
)
_EXPECTED_PROFILE = store.STORE_PROFILE

_STORE_ID = re.compile(r"mmactualstore_[a-f0-9]{64}\Z")
_GENERATION_ID = re.compile(r"mmactualgeneration_[a-f0-9]{64}\Z")
_SHA256 = re.compile(r"[a-f0-9]{64}\Z")
_SOURCE_ID = re.compile(r"mmtechsrc_[a-f0-9]{64}\Z")
_GIT_OID = re.compile(r"[a-f0-9]{40}(?:[a-f0-9]{24})?\Z")

# Reviewed installed Git sources.  The expected digests are read from the
# accepted technical store's pin set at verification time so this policy and
# the store can never disagree about the reviewed license/basis identities.
_CLOSURE_GIT_SOURCE_PATHS = {
    "canary_identity_config": "config/market_memory_canary.v1.json",
    "xnys_calendar_module": "lib/nyse_calendar.py",
    "massive_entitlement_record": "research/licenses/MASSIVE_ENTITLEMENT_RECORD.md",
    "technical_price_basis_contract": (
        "config/market_memory_technical_price_basis.v1.json"
    ),
}
_CLOSURE_CODE_MODULE_PATHS = {
    "price_metadata_use_policy": "engine/neuralweb/market_memory_price_metadata_use.py",
    "price_metadata_cli": "scripts/inspect_market_memory_price_coverage.py",
    "technical_store": "engine/neuralweb/market_memory_technical_store.py",
    "technical_observation": "engine/neuralweb/market_memory_technical_observation.py",
    "technical_pit_kernel": "engine/neuralweb/market_memory_pit.py",
}
_CLOSURE_BYTE_LIMITS = {
    "price_metadata_use_policy": 128 * 1024,
    "price_metadata_cli": 64 * 1024,
    "technical_store": 256 * 1024,
    "technical_observation": 256 * 1024,
    "technical_pit_kernel": 256 * 1024,
    "canary_identity_config": 32 * 1024,
    "xnys_calendar_module": 256 * 1024,
    "massive_entitlement_record": 64 * 1024,
    "technical_price_basis_contract": 32 * 1024,
}
_GIT_TIMEOUT_SECONDS = 10
_GIT_OUTPUT_LIMIT = 64 * 1024

ClosureVerifier = Callable[..., dict[str, Any]]


class MarketMemoryPriceMetadataPolicyError(Exception):
    """The installed price-metadata policy could not be qualified or enforced."""


def _git_bounded(root: Path, *args: str) -> str:
    """Run one bounded read-only Git query against the installed checkout."""
    # -C does not override GIT_DIR, GIT_WORK_TREE, object-store overrides or
    # injected config. Qualify this checkout, never a caller-selected Git view.
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith("GIT_")}
    environment.update({
        "GIT_NO_LAZY_FETCH": "1", "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0", "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_ALLOW_PROTOCOL": "",
    })
    try:
        result = subprocess.run(
            ["/usr/bin/git", "-c", "protocol.allow=never", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            env=environment,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise MarketMemoryPriceMetadataPolicyError(
            "installed source closure cannot be bound to Git"
        ) from exc
    output = result.stdout
    if type(output) is not str or not output or len(output) > _GIT_OUTPUT_LIMIT:
        raise MarketMemoryPriceMetadataPolicyError(
            "installed source closure Git output is malformed"
        )
    return output


def _git_blob_oid(body: bytes) -> str:
    framed = f"blob {len(body)}\0".encode("ascii") + body
    return hashlib.sha1(framed).hexdigest()


def _stable_bounded_read(path: Path, *, limit: int, label: str) -> bytes:
    """Read one regular non-symlink installed file inside a stable byte bound."""
    try:
        before = path.lstat()
    except OSError as exc:
        raise MarketMemoryPriceMetadataPolicyError(
            f"installed {label} is unavailable"
        ) from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise MarketMemoryPriceMetadataPolicyError(
            f"installed {label} must be a regular non-symlink"
        )
    if not 1 <= before.st_size <= limit:
        raise MarketMemoryPriceMetadataPolicyError(
            f"installed {label} exceeds its byte bound"
        )
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise MarketMemoryPriceMetadataPolicyError(
            f"installed {label} could not be opened safely"
        ) from exc
    try:
        opened = os.fstat(descriptor)
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(descriptor)
        closed = path.lstat()
    except OSError as exc:
        raise MarketMemoryPriceMetadataPolicyError(
            f"installed {label} changed during its stable read"
        ) from exc
    finally:
        os.close(descriptor)
    identities = {
        (
            item.st_dev,
            item.st_ino,
            item.st_size,
            item.st_mtime_ns,
            item.st_ctime_ns,
            stat.S_IFMT(item.st_mode),
        )
        for item in (before, opened, after, closed)
    }
    body = b"".join(chunks)
    if (
        len(identities) != 1
        or not stat.S_ISREG(after.st_mode)
        or len(body) != after.st_size
        or len(body) > limit
    ):
        raise MarketMemoryPriceMetadataPolicyError(
            f"installed {label} changed during its stable read"
        )
    return body


def _require_installed_regular_file(root: Path, repo_path: str) -> Path:
    """Reject symlinked or nonregular components inside the installed root."""
    parts = [part for part in Path(repo_path).parts]
    if not parts or any(
        part in {"", ".", ".."} or "/" in part or "\\" in part or "\0" in part
        for part in parts
    ):
        raise MarketMemoryPriceMetadataPolicyError(
            "installed closure path is not a safe repository-relative path"
        )
    resolved_root = Path(os.path.realpath(root))
    if Path(os.path.abspath(root)) != resolved_root:
        raise MarketMemoryPriceMetadataPolicyError(
            "installed repository root must not be a symlink"
        )
    cursor = resolved_root
    for part in parts[:-1]:
        cursor = cursor / part
        try:
            metadata = cursor.lstat()
        except OSError as exc:
            raise MarketMemoryPriceMetadataPolicyError(
                "installed closure directory is unavailable"
            ) from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise MarketMemoryPriceMetadataPolicyError(
                "installed closure directory must be a real directory"
            )
    return resolved_root / Path(*parts)


def verify_installed_price_metadata_closure(
    repository_root: str | Path, *, expected_head: str
) -> dict[str, Any]:
    """Authenticate the installed closure against the exact deployed HEAD.

    Every closure file must be a bounded regular non-symlink inside the
    installed root, its bytes must match the blob published at
    ``expected_head``, and the reviewed license/basis/config/calendar digests
    must equal the accepted store's reviewed pin set.  Bounded Git queries and
    bounded file reads only; source changes are never attempted.
    """
    if type(expected_head) is not str or not _GIT_OID.fullmatch(expected_head):
        raise MarketMemoryPriceMetadataPolicyError(
            "expected deployed HEAD is not a full Git object ID"
        )
    root = Path(os.path.abspath(os.fspath(Path(repository_root))))
    if not root.is_dir():
        raise MarketMemoryPriceMetadataPolicyError(
            "installed repository root is unavailable"
        )
    head = _git_bounded(root, "rev-parse", "--verify", "HEAD^{commit}").strip()
    if head != expected_head:
        raise MarketMemoryPriceMetadataPolicyError(
            "installed checkout is not the exact deployed source HEAD"
        )

    sections: dict[str, dict[str, dict[str, Any]]] = {}
    plans: list[tuple[str, str, str]] = [
        *(
            ("modules", role, path)
            for role, path in _CLOSURE_CODE_MODULE_PATHS.items()
        ),
        *(
            ("git_sources", role, path)
            for role, path in _CLOSURE_GIT_SOURCE_PATHS.items()
        ),
    ]
    for section, role, repo_path in plans:
        path = _require_installed_regular_file(root, repo_path)
        body = _stable_bounded_read(
            path, limit=_CLOSURE_BYTE_LIMITS[role], label=role
        )
        digest = hashlib.sha256(body).hexdigest()
        blob_oid = _git_bounded(root, "rev-parse", f"{expected_head}:{repo_path}").strip()
        if not _GIT_OID.fullmatch(blob_oid) or blob_oid != _git_blob_oid(body):
            raise MarketMemoryPriceMetadataPolicyError(
                f"installed {role} bytes differ from the deployed HEAD blob"
            )
        if section == "git_sources":
            reviewed = store._GIT_SOURCE_SHA256[role]
            if digest != reviewed:
                raise MarketMemoryPriceMetadataPolicyError(
                    f"installed {role} differs from its reviewed v1 SHA-256"
                )
        sections.setdefault(section, {})[role] = {
            "path": repo_path,
            "sha256": digest,
            "bytes": len(body),
            "git_blob_oid": blob_oid,
        }
    if _git_bounded(root, "rev-parse", "--verify", "HEAD^{commit}").strip() != head:
        raise MarketMemoryPriceMetadataPolicyError(
            "installed HEAD changed during closure verification"
        )
    return {
        "deployed_head": head,
        "modules": sections["modules"],
        "git_sources": sections["git_sources"],
    }


def _validate_identity(field: str, value: object, pattern: re.Pattern[str]) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise MarketMemoryPriceMetadataPolicyError(
            f"metadata {field} does not match its immutable grammar"
        )
    return value


class RetainedSourceBarMetadataUsePolicy:
    """Owner policy admitting exactly the two retained-metadata actions.

    Construction qualifies the current installed closure once; every
    enforcement re-verifies it against the deployed HEAD captured here, so a
    grant, basis, license, calendar, or module change after a read denies the
    corresponding disclosure.  The resource quadruple is bound at construction
    and may never widen.
    """

    policy_id = POLICY_ID

    def __init__(
        self,
        *,
        repository_root: str | Path,
        store_id: str,
        generation_id: str,
        generation_sha256: str,
        source_observation_id: str,
        expected_head: str | None = None,
        closure_verifier: ClosureVerifier | None = None,
    ):
        _validate_identity("store_id", store_id, _STORE_ID)
        _validate_identity("generation_id", generation_id, _GENERATION_ID)
        _validate_identity("generation_sha256", generation_sha256, _SHA256)
        _validate_identity(
            "source_observation_id", source_observation_id, _SOURCE_ID
        )
        self._resource = {
            "profile": _EXPECTED_PROFILE,
            "store_id": store_id,
            "generation_id": generation_id,
            "generation_sha256": generation_sha256,
            "source_observation_id": source_observation_id,
        }
        self._repository_root = Path(repository_root)
        # Bind the current approved deployment once, never a source-code constant
        # that predates this command. This is source qualification, not private
        # generation discovery; the four caller-supplied data pins stay exact.
        self._expected_head = expected_head if expected_head is not None else (
            _git_bounded(self._repository_root, "rev-parse", "--verify", "HEAD^{commit}").strip()
        )
        self._verifier: ClosureVerifier = (
            verify_installed_price_metadata_closure
            if closure_verifier is None
            else closure_verifier
        )
        self._qualified_closure = self._verifier(
            self._repository_root, expected_head=self._expected_head
        )

    @property
    def resource(self) -> dict[str, str]:
        return copy.deepcopy(self._resource)

    @property
    def qualified_closure(self) -> dict[str, Any]:
        return copy.deepcopy(self._qualified_closure)

    def check(self, action: object, resource: object) -> bool:
        if type(action) is not str or action not in _ACTIONS:
            raise PermissionError("unknown retained technical metadata action")
        if (
            type(resource) is not dict
            or frozenset(resource) != frozenset(_RESOURCE_FIELDS)
            or any(
                type(resource[field]) is not str
                or resource[field] != self._resource[field]
                for field in _RESOURCE_FIELDS
            )
        ):
            raise PermissionError("retained technical metadata resource drift")
        try:
            current = self._verifier(
                self._repository_root, expected_head=self._expected_head
            )
        except Exception as exc:
            raise PermissionError(
                "current installed source closure drifted or is unverifiable"
            ) from exc
        if current != self._qualified_closure:
            raise PermissionError(
                "current installed source closure differs from the qualified one"
            )
        return True


__all__ = [
    "INSTALLED_REPOSITORY_ROOT",
    "MarketMemoryPriceMetadataPolicyError",
    "POLICY_ID",
    "RetainedSourceBarMetadataUsePolicy",
    "verify_installed_price_metadata_closure",
]
