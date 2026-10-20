"""FIF V0-b: backup / restore / restart / effect-unknown recovery drill.

A READ-MOSTLY companion to the frozen production-dataset owner
(``engine/fundamental_forensics/production_datasets.py``). This module never
edits that owner and performs no network I/O; the only I/O it performs runs
through the strict conditional store object it is given. Its job is to prove,
against an in-memory double or a local-directory store, the two acceptance
cases of the recovery drill:

- **A47 (restart, lost publication, restore, rollback).** A reopened store
  object over the same local directory serves the same generation (restart is
  a store property, proven by the tests). ``backup_issuer`` /
  ``backup_bytes`` capture an admitted generation byte-exactly (pointer,
  manifest, every object the manifest references); ``restore_issuer``
  replays them CREATE-ONLY — identical bytes are left in place, different
  bytes stop the restore, nothing is ever overwritten — and re-points the
  target only when it has no pointer: an existing pointer, even one naming
  a different generation, is kept as ``kept_existing`` with both
  generation ids. ``audit_issuer`` classifies an issuer
  into exactly one recovery state. Rollback is a CORRECTION (a new
  superseding generation through ``publish_production_dataset``); the owner
  refuses pointer rewinds and this drill deliberately exposes no rewind
  function.
- **A18 (EFFECT_UNKNOWN on write loss).** After an ambiguous publish,
  ``reconcile_effect_unknown`` performs ZERO writes and returns one of
  ``landed`` / ``manifest_landed_pointer_not_advanced`` / ``not_landed`` /
  ``pointer_names_other_generation``. It never retries a publish and never
  fails over: the target stays EFFECT_UNKNOWN on its original carrier until
  reconciliation reads it, and no republish or failover may precede that
  read.

Manifest fields consumed by the backup (read through the public
``ProductionDatasetGeneration.manifest`` attribute, so no JSON is re-parsed
here): the ``objects`` role rows ``{"role", "object_key", "sha256",
"byte_length"}`` written by the owner at
production_datasets.py:933-945/966-967, and the ``accessions[].members``
rows ``{"name", "sha256", "byte_length"}`` written by
``_index_accessions_for_manifest`` at production_datasets.py:1010-1039
(member mapping at :1028-1033).

Typed gaps (never worked around):

- ``listing_unsupported``: a store without a usable ``list_prefix`` cannot be
  audited for lost publication (absent vs. pointer_absent_generation_present
  is indistinguishable without listing). ``audit_issuer`` returns this state
  instead of guessing.
- Repointing after a lost publication is a publisher act. The drill never
  writes a pointer outside ``restore_issuer``'s no-pointer rule; the lawful
  republish is ``publish_production_dataset`` with the same material.
- A pointer rewind to a prior generation is impossible through the public
  API (the owner's stale-pointer guard), by design: rollback is a
  superseding correction.
- ``restore_issuer`` keeps an existing pointer even when it names a
  different generation; replacing it is a publisher act, not a restore.

Recovery-path mapping notes for the closed ``reconcile_effect_unknown``
vocabulary: a pointer that exists but cannot be verified raises
``ProductionDatasetEffectUnknownError`` (A18 — an unverifiable pointer
proves nothing about landing, so the outcome is never reported
``not_landed``), and an unreadable manifest probe fails closed with
``ProductionDatasetError``. The drill never invents a fifth state and never
writes to resolve one.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Mapping

from .production_datasets import (
    ProductionDatasetEffectUnknownError,
    ProductionDatasetError,
    ProductionDatasetGeneration,
    load_generation,
    load_latest_generation,
    latest_generation_summary,
    production_latest_key,
    production_manifest_key,
    production_object_key,
)

__all__ = [
    "AUDIT_STATE_ABSENT",
    "AUDIT_STATE_ADMITTED",
    "AUDIT_STATE_LISTING_UNSUPPORTED",
    "AUDIT_STATE_POINTER_ABSENT_GENERATION_PRESENT",
    "AUDIT_STATE_POINTER_UNVERIFIABLE",
    "BackupEntry",
    "BackupManifest",
    "IssuerRecoveryState",
    "RECONCILE_LANDED",
    "RECONCILE_MANIFEST_LANDED_POINTER_NOT_ADVANCED",
    "RECONCILE_NOT_LANDED",
    "RECONCILE_POINTER_NAMES_OTHER_GENERATION",
    "RECOVERY_PUBLISHER_REPOINT_REQUIRED",
    "RestoreReceipt",
    "audit_issuer",
    "backup_bytes",
    "backup_issuer",
    "reconcile_effect_unknown",
    "restore_issuer",
]

# Drill-local defensive read caps (this module cannot import the owner's
# frozen bounds; these are generous ceilings for fixture-scale stores).
DRILL_MAX_POINTER_BYTES = 1 * 1024 * 1024
DRILL_MAX_MANIFEST_BYTES = 16 * 1024 * 1024
DRILL_MAX_OBJECT_BYTES = 256 * 1024 * 1024

BACKUP_ROLE_POINTER = "pointer"
BACKUP_ROLE_MANIFEST = "manifest"
BACKUP_ROLE_OBJECT = "object"
_BACKUP_ROLES = frozenset({BACKUP_ROLE_POINTER, BACKUP_ROLE_MANIFEST, BACKUP_ROLE_OBJECT})

_SHA256_RE = re.compile(r"\A[a-f0-9]{64}\Z")

RESTORE_POINTER_RESTORED = "restored"
RESTORE_POINTER_KEPT_EXISTING = "kept_existing"

# Immutable-entry (object/manifest) restore outcomes. ``restored`` is the
# drill's OWN write whose ambiguous signal (a raised or falsy conditional
# put) a read-back then confirmed with exact bytes; ``already_present`` is
# reserved for keys that held the exact bytes before any write was attempted.
RESTORE_ENTRY_WRITTEN = "written"
RESTORE_ENTRY_RESTORED = "restored"
RESTORE_ENTRY_ALREADY_PRESENT = "already_present"

AUDIT_STATE_ADMITTED = "admitted"
AUDIT_STATE_ABSENT = "absent"
AUDIT_STATE_POINTER_ABSENT_GENERATION_PRESENT = "pointer_absent_generation_present"
AUDIT_STATE_POINTER_UNVERIFIABLE = "pointer_unverifiable"
AUDIT_STATE_LISTING_UNSUPPORTED = "listing_unsupported"
RECOVERY_PUBLISHER_REPOINT_REQUIRED = "publisher_repoint_required"

RECONCILE_LANDED = "landed"
RECONCILE_MANIFEST_LANDED_POINTER_NOT_ADVANCED = "manifest_landed_pointer_not_advanced"
RECONCILE_NOT_LANDED = "not_landed"
RECONCILE_POINTER_NAMES_OTHER_GENERATION = "pointer_names_other_generation"


# ---------------------------------------------------------------------------
# Backup shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BackupEntry:
    """One backed-up store key with its digest, length, and layout role."""

    key: str
    sha256_hex: str
    byte_length: int
    role: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "sha256_hex": self.sha256_hex,
            "byte_length": self.byte_length,
            "role": self.role,
        }


@dataclass(frozen=True)
class BackupManifest:
    """The byte-exact inventory of one admitted generation."""

    issuer_id: str
    generation_id: str
    entries: tuple[BackupEntry, ...]

    def to_dict(self) -> dict[str, Any]:
        """Deterministic document: entries sorted by key."""
        return {
            "issuer_id": self.issuer_id,
            "generation_id": self.generation_id,
            "entries": [entry.to_dict() for entry in sorted(self.entries, key=lambda e: e.key)],
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "BackupManifest":
        if not isinstance(document, Mapping) or set(document) != {
            "issuer_id",
            "generation_id",
            "entries",
        }:
            raise ProductionDatasetError("recovery drill backup document is malformed")
        raw_entries = document["entries"]
        if not isinstance(raw_entries, list):
            raise ProductionDatasetError("recovery drill backup document is malformed")
        entries = []
        for row in raw_entries:
            if not isinstance(row, Mapping) or set(row) != {
                "key",
                "sha256_hex",
                "byte_length",
                "role",
            }:
                raise ProductionDatasetError("recovery drill backup entry is malformed")
            entries.append(
                BackupEntry(
                    key=row["key"],
                    sha256_hex=row["sha256_hex"],
                    byte_length=row["byte_length"],
                    role=row["role"],
                )
            )
        return _enforced_manifest(
            cls(
                issuer_id=document["issuer_id"],
                generation_id=document["generation_id"],
                entries=tuple(sorted(entries, key=lambda e: e.key)),
            )
        )


def _require_issuer_id(issuer_id: str) -> None:
    if not isinstance(issuer_id, str) or not issuer_id:
        raise ProductionDatasetError("recovery drill issuer id is malformed")


def _enforced_manifest(manifest: BackupManifest) -> BackupManifest:
    """Enforce the backup layout laws shared by construction and re-parse."""
    _require_issuer_id(manifest.issuer_id)
    if not isinstance(manifest.generation_id, str) or not manifest.generation_id:
        raise ProductionDatasetError("recovery drill backup generation id is malformed")
    if len(set(manifest.entries)) != len(manifest.entries):
        raise ProductionDatasetError("recovery drill backup has duplicate entries")
    roles: dict[str, list[BackupEntry]] = {}
    for entry in manifest.entries:
        if not isinstance(entry.key, str) or not entry.key:
            raise ProductionDatasetError("recovery drill backup entry is malformed")
        if entry.role not in _BACKUP_ROLES:
            raise ProductionDatasetError("recovery drill backup entry role is malformed")
        if not isinstance(entry.sha256_hex, str) or not _SHA256_RE.fullmatch(entry.sha256_hex):
            raise ProductionDatasetError("recovery drill backup digest is malformed")
        if (
            not isinstance(entry.byte_length, int)
            or isinstance(entry.byte_length, bool)
            or entry.byte_length < 0
        ):
            raise ProductionDatasetError("recovery drill backup length is malformed")
        roles.setdefault(entry.role, []).append(entry)
    if len(roles.get(BACKUP_ROLE_POINTER, ())) != 1:
        raise ProductionDatasetError("recovery drill backup requires exactly one pointer entry")
    if len(roles.get(BACKUP_ROLE_MANIFEST, ())) != 1:
        raise ProductionDatasetError("recovery drill backup requires exactly one manifest entry")
    if not roles.get(BACKUP_ROLE_OBJECT):
        raise ProductionDatasetError("recovery drill backup requires object entries")
    if roles[BACKUP_ROLE_POINTER][0].key != production_latest_key(manifest.issuer_id):
        raise ProductionDatasetError("recovery drill backup pointer key is malformed")
    if roles[BACKUP_ROLE_MANIFEST][0].key != production_manifest_key(
        manifest.issuer_id, manifest.generation_id
    ):
        raise ProductionDatasetError("recovery drill backup manifest key is malformed")
    for entry in roles[BACKUP_ROLE_OBJECT]:
        if entry.key != production_object_key(entry.sha256_hex):
            raise ProductionDatasetError("recovery drill backup object key is malformed")
    return manifest


# ---------------------------------------------------------------------------
# Strict bounded reads (drill-local)
# ---------------------------------------------------------------------------


def _read_strict(store: Any, key: str, maximum: int) -> bytes | None:
    """Bounded strict read; ``None`` is authoritative absence, failures raise."""
    try:
        payload = store.get_bytes_strict_bounded(key, maximum)
    except Exception as exc:  # noqa: BLE001
        raise ProductionDatasetError("recovery drill bounded read failed") from exc
    if payload is None:
        return None
    if not isinstance(payload, bytes) or not payload:
        raise ProductionDatasetError("recovery drill bounded read is malformed")
    return payload


def _try_read_strict(store: Any, key: str, maximum: int) -> bytes | None:
    """``_read_strict`` with every failure collapsed to absence (A18 probing)."""
    try:
        return _read_strict(store, key, maximum)
    except ProductionDatasetError:
        return None


def _read_required(store: Any, key: str, maximum: int) -> bytes:
    payload = _read_strict(store, key, maximum)
    if payload is None:
        raise ProductionDatasetError("recovery drill object is missing")
    return payload


def _digest(payload: bytes) -> str:
    return hashlib.sha256(bytes(payload)).hexdigest()


# ---------------------------------------------------------------------------
# 1. Backup
# ---------------------------------------------------------------------------


def backup_issuer(store: Any, issuer_id: str) -> BackupManifest:
    """Inventory the issuer's admitted latest generation, byte-exactly.

    Reads the latest pointer bytes, the manifest of the generation it names,
    and every object key that manifest references — the ``objects`` role rows
    plus the content-addressed statement-package member objects listed under
    ``accessions[].members``. Everything the manifest names must be present
    with matching digest and length; a generation whose pointer cannot be
    verified cannot be backed up from here (see module gaps).
    """
    _require_issuer_id(issuer_id)
    generation = load_latest_generation(store, issuer_id)
    if generation is None:
        raise ProductionDatasetError("recovery drill backup requires an admitted latest generation")
    pointer_key = production_latest_key(issuer_id)
    pointer_payload = _read_required(store, pointer_key, DRILL_MAX_POINTER_BYTES)
    entries: list[BackupEntry] = [
        BackupEntry(
            key=pointer_key,
            sha256_hex=_digest(pointer_payload),
            byte_length=len(pointer_payload),
            role=BACKUP_ROLE_POINTER,
        )
    ]
    manifest_key = production_manifest_key(issuer_id, generation.generation_id)
    manifest_payload = _read_required(store, manifest_key, DRILL_MAX_MANIFEST_BYTES)
    entries.append(
        BackupEntry(
            key=manifest_key,
            sha256_hex=_digest(manifest_payload),
            byte_length=len(manifest_payload),
            role=BACKUP_ROLE_MANIFEST,
        )
    )
    seen_keys: set[str] = set()
    # Role objects: the manifest's own ``objects`` rows (owner-written shape,
    # production_datasets.py:933-945/966-967). load_latest_generation has
    # already byte-verified these; re-read and re-check anyway.
    for row in generation.manifest.get("objects") or []:
        if not isinstance(row, Mapping) or not isinstance(row.get("object_key"), str):
            raise ProductionDatasetError("recovery drill manifest object row is malformed")
        key = row["object_key"]
        payload = _read_required(store, key, DRILL_MAX_OBJECT_BYTES)
        if _digest(payload) != row.get("sha256") or len(payload) != row.get("byte_length"):
            raise ProductionDatasetError("recovery drill backup object disagrees with manifest")
        if key not in seen_keys:
            seen_keys.add(key)
            entries.append(
                BackupEntry(
                    key=key, sha256_hex=_digest(payload), byte_length=len(payload),
                    role=BACKUP_ROLE_OBJECT,
                )
            )
    # Statement-package member objects: content-addressed by digest in
    # ``accessions[].members`` (owner-written shape,
    # production_datasets.py:1028-1033). Members without a digest are
    # referenced-only rows this store never fetched; they are skipped.
    for accession in generation.manifest.get("accessions") or []:
        if not isinstance(accession, Mapping):
            raise ProductionDatasetError("recovery drill manifest accession row is malformed")
        for member in accession.get("members") or []:
            if not isinstance(member, Mapping):
                raise ProductionDatasetError("recovery drill manifest member row is malformed")
            digest = member.get("sha256")
            length = member.get("byte_length")
            if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
                continue
            key = production_object_key(digest)
            if key in seen_keys:
                continue
            payload = _read_required(store, key, DRILL_MAX_OBJECT_BYTES)
            if _digest(payload) != digest or (
                isinstance(length, int) and not isinstance(length, bool) and len(payload) != length
            ):
                raise ProductionDatasetError("recovery drill backup member disagrees with manifest")
            seen_keys.add(key)
            entries.append(
                BackupEntry(
                    key=key, sha256_hex=_digest(payload), byte_length=len(payload),
                    role=BACKUP_ROLE_OBJECT,
                )
            )
    return _enforced_manifest(
        BackupManifest(
            issuer_id=issuer_id,
            generation_id=generation.generation_id,
            entries=tuple(sorted(entries, key=lambda e: e.key)),
        )
    )


def backup_bytes(store: Any, manifest: BackupManifest) -> dict[str, bytes]:
    """Re-read and re-verify every entry of a backup manifest.

    Raises ``ProductionDatasetError`` on any missing key, length mismatch, or
    sha256 mismatch while reading.
    """
    _enforced_manifest(manifest)
    payloads: dict[str, bytes] = {}
    for entry in sorted(manifest.entries, key=lambda e: e.key):
        maximum = (
            DRILL_MAX_POINTER_BYTES
            if entry.role == BACKUP_ROLE_POINTER
            else DRILL_MAX_MANIFEST_BYTES
            if entry.role == BACKUP_ROLE_MANIFEST
            else DRILL_MAX_OBJECT_BYTES
        )
        payload = _read_required(store, entry.key, maximum)
        if len(payload) != entry.byte_length:
            raise ProductionDatasetError("recovery drill backup byte length mismatch")
        if _digest(payload) != entry.sha256_hex:
            raise ProductionDatasetError("recovery drill backup digest mismatch")
        payloads[entry.key] = payload
    return payloads


# ---------------------------------------------------------------------------
# 2. Restore
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RestoreReceipt:
    """What one restore did: writes, idempotent hits, pointer rule, verdict.

    ``written`` holds keys the conditional put created cleanly (True
    returned); ``restored`` holds keys whose write signal was ambiguous
    (raised or falsy) but whose exact bytes a read-back then confirmed —
    the drill's own write, never counted as ``already_present``;
    ``already_present`` holds keys that were already there, byte-identical,
    before the drill attempted any write. ``pointer_generation_id`` is the
    generation this restore carried; ``kept_pointer_generation_id`` names
    the generation a kept existing pointer names (``kept_existing`` only;
    None when the drill itself pointed the pointer or the kept pointer
    cannot be proven).
    """

    written: tuple[str, ...]
    already_present: tuple[str, ...]
    restored: tuple[str, ...]
    pointer: str
    pointer_generation_id: str
    verified: bool
    kept_pointer_generation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "written": list(self.written),
            "already_present": list(self.already_present),
            "restored": list(self.restored),
            "pointer": self.pointer,
            "pointer_generation_id": self.pointer_generation_id,
            "verified": self.verified,
            "kept_pointer_generation_id": self.kept_pointer_generation_id,
        }


def _restore_create_only(
    target_store: Any, *, entry: BackupEntry, payload: bytes
) -> str:
    """Create one immutable entry at an absent key; classify the outcome.

    ``written`` (the conditional put returned True) | ``restored`` (the
    write signal was ambiguous — raised or falsy — but a read-back then
    confirmed the drill's exact bytes, and the key was verifiably absent
    before the write was attempted) | ``already_present`` (the key held the
    exact bytes before any write was attempted). Different bytes stop the
    restore; an unprovable write outcome preserves EFFECT_UNKNOWN on the
    original target (A18) instead of retrying or failing over.
    """
    current = _read_strict(target_store, entry.key, DRILL_MAX_OBJECT_BYTES)
    if current is not None:
        if current == payload:
            return RESTORE_ENTRY_ALREADY_PRESENT
        raise ProductionDatasetError("restore target holds different bytes")
    try:
        written = target_store.put_bytes_strict_conditional(
            entry.key,
            payload,
            expected_version=None,
            content_type="application/octet-stream",
        )
    except Exception as exc:  # noqa: BLE001 - the write may have committed
        echoed = _try_read_strict(target_store, entry.key, DRILL_MAX_OBJECT_BYTES)
        if echoed is not None:
            if echoed == payload:
                return RESTORE_ENTRY_RESTORED
            raise ProductionDatasetError("restore target holds different bytes") from exc
        raise ProductionDatasetEffectUnknownError(
            "restore conditional write outcome could not be reconciled"
        ) from exc
    if written is True:
        return RESTORE_ENTRY_WRITTEN
    echoed = _try_read_strict(target_store, entry.key, DRILL_MAX_OBJECT_BYTES)
    if echoed is None:
        raise ProductionDatasetEffectUnknownError(
            "restore conditional write outcome could not be reconciled"
        )
    if echoed == payload:
        return RESTORE_ENTRY_RESTORED
    raise ProductionDatasetError("restore target holds different bytes")


def _kept_pointer_generation_id(target_store: Any, issuer_id: str) -> str | None:
    """Generation id the target's live pointer names, when that is provable.

    The kept pointer belongs to another writer; when it cannot be decoded
    and verified through the owner's public summary the receipt says None
    rather than guessing.
    """
    try:
        summary = latest_generation_summary(target_store, issuer_id)
    except ProductionDatasetError:
        return None
    if not isinstance(summary, Mapping):
        return None
    generation_id = summary.get("dataset_generation_id")
    if not isinstance(generation_id, str) or not generation_id:
        return None
    return generation_id


def _restore_pointer(
    target_store: Any,
    *,
    entry: BackupEntry,
    payload: bytes,
    issuer_id: str,
    generation_id: str,
) -> tuple[str, str | None]:
    """Restore the pointer last, only when the target has none (A47).

    An existing pointer is always KEPT — even when it names a different
    generation (replacing it is a publisher act, not a restore) — and
    nothing is written to it. Returns ``(outcome, kept_generation_id)``:
    ``kept_generation_id`` is the generation a kept pointer names (the
    restore's own generation when the kept bytes are identical, the other
    writer's generation when they differ and can be proven, None when they
    cannot), None when the drill itself pointed the pointer. An unprovable
    write outcome preserves EFFECT_UNKNOWN on the original target (A18)
    instead of retrying or failing over.
    """
    current = _read_strict(target_store, entry.key, DRILL_MAX_POINTER_BYTES)
    if current is not None:
        if current == payload:
            return RESTORE_POINTER_KEPT_EXISTING, generation_id
        return (
            RESTORE_POINTER_KEPT_EXISTING,
            _kept_pointer_generation_id(target_store, issuer_id),
        )
    try:
        written = target_store.put_bytes_strict_conditional(
            entry.key,
            payload,
            expected_version=None,
            content_type="application/json",
        )
    except Exception as exc:  # noqa: BLE001 - the CAS may have committed
        echoed = _try_read_strict(target_store, entry.key, DRILL_MAX_POINTER_BYTES)
        if echoed is not None:
            if echoed == payload:
                # The drill's own write evidently committed.
                return RESTORE_POINTER_RESTORED, None
            # A concurrent writer pointed the pointer first: keep theirs.
            return (
                RESTORE_POINTER_KEPT_EXISTING,
                _kept_pointer_generation_id(target_store, issuer_id),
            )
        raise ProductionDatasetEffectUnknownError(
            "restore pointer write outcome could not be reconciled"
        ) from exc
    if written is True:
        return RESTORE_POINTER_RESTORED, None
    echoed = _try_read_strict(target_store, entry.key, DRILL_MAX_POINTER_BYTES)
    if echoed is None:
        raise ProductionDatasetEffectUnknownError(
            "restore pointer write outcome could not be reconciled"
        )
    if echoed == payload:
        # Verifiably absent before the write attempt, the drill's exact
        # bytes after it: the drill's own write.
        return RESTORE_POINTER_RESTORED, None
    return (
        RESTORE_POINTER_KEPT_EXISTING,
        _kept_pointer_generation_id(target_store, issuer_id),
    )


def restore_issuer(
    target_store: Any, manifest: BackupManifest, payloads: Mapping[str, bytes]
) -> RestoreReceipt:
    """Replay a backup onto a target store, create-only, never overwriting.

    Every ``object`` and ``manifest`` entry is written with the store's
    strict conditional put under an absent precondition. A key that already
    holds IDENTICAL bytes is recorded ``already_present`` and not written; a
    key whose ambiguous write signal (raised or falsy) a read-back then
    confirms with exact bytes is recorded ``restored`` — the drill's own
    write; a key that holds DIFFERENT bytes stops the restore with
    ``ProductionDatasetError("restore target holds different bytes")``. The
    pointer is restored last and only when the target has no pointer for
    the issuer — an existing pointer is KEPT even when it names a different
    generation (replacing it is a publisher act), the receipt reports
    ``kept_existing`` with both generation ids, and nothing is written to
    the pointer. The receipt's ``verified`` is True only when the restored
    generation loads and verifies afterwards — a False means the restore is
    not complete, not that it succeeded.
    """
    _enforced_manifest(manifest)
    if not isinstance(payloads, Mapping):
        raise ProductionDatasetError("recovery drill restore payloads are malformed")
    expected_keys = {entry.key for entry in manifest.entries}
    if set(payloads) != expected_keys:
        raise ProductionDatasetError("recovery drill restore payload keys are inexact")
    verified_payloads: dict[str, bytes] = {}
    for entry in manifest.entries:
        payload = payloads[entry.key]
        if not isinstance(payload, (bytes, bytearray)) or not payload:
            raise ProductionDatasetError("recovery drill restore payload is missing")
        payload = bytes(payload)
        if len(payload) != entry.byte_length or _digest(payload) != entry.sha256_hex:
            raise ProductionDatasetError("recovery drill restore payload digest mismatch")
        verified_payloads[entry.key] = payload

    written: list[str] = []
    restored: list[str] = []
    already_present: list[str] = []
    ordered = sorted(manifest.entries, key=lambda e: e.key)

    def _record(entry: BackupEntry, outcome: str) -> None:
        if outcome == RESTORE_ENTRY_WRITTEN:
            written.append(entry.key)
        elif outcome == RESTORE_ENTRY_RESTORED:
            restored.append(entry.key)
        else:
            already_present.append(entry.key)

    for entry in (e for e in ordered if e.role == BACKUP_ROLE_OBJECT):
        _record(
            entry,
            _restore_create_only(
                target_store, entry=entry, payload=verified_payloads[entry.key]
            ),
        )
    for entry in (e for e in ordered if e.role == BACKUP_ROLE_MANIFEST):
        _record(
            entry,
            _restore_create_only(
                target_store, entry=entry, payload=verified_payloads[entry.key]
            ),
        )
    pointer_entry = next(e for e in manifest.entries if e.role == BACKUP_ROLE_POINTER)
    pointer, kept_generation_id = _restore_pointer(
        target_store,
        entry=pointer_entry,
        payload=verified_payloads[pointer_entry.key],
        issuer_id=manifest.issuer_id,
        generation_id=manifest.generation_id,
    )

    try:
        load_generation(target_store, manifest.issuer_id, manifest.generation_id)
        complete = True
    except ProductionDatasetError:
        complete = False
    return RestoreReceipt(
        written=tuple(sorted(written)),
        already_present=tuple(sorted(already_present)),
        restored=tuple(sorted(restored)),
        pointer=pointer,
        pointer_generation_id=manifest.generation_id,
        verified=complete,
        kept_pointer_generation_id=kept_generation_id,
    )


# ---------------------------------------------------------------------------
# 3. Audit (read only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IssuerRecoveryState:
    """One issuer's recovery classification; carries no payloads."""

    issuer_id: str
    state: str
    recovery: str | None = None
    generation_id: str | None = None
    manifest_generation_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "issuer_id": self.issuer_id,
            "state": self.state,
            "recovery": self.recovery,
            "generation_id": self.generation_id,
            "manifest_generation_ids": list(self.manifest_generation_ids),
        }


def _generations_prefix(issuer_id: str) -> str:
    issuer_dir = production_latest_key(issuer_id).rsplit("/", 1)[0]
    return f"{issuer_dir}/generations/"


def _list_generation_ids(store: Any, issuer_id: str) -> tuple[str, ...] | None:
    """Sorted generation ids found under the issuer prefix, or None if the
    store cannot list (the typed gap)."""
    prefix = _generations_prefix(issuer_id)
    lister = getattr(store, "list_prefix", None)
    if not callable(lister):
        return None
    try:
        keys = lister(prefix)
    except Exception:  # noqa: BLE001 - cannot list is the typed gap, not a crash
        return None
    if not isinstance(keys, list):
        return None
    ids = []
    for key in keys:
        if not isinstance(key, str) or not key.startswith(prefix) or not key.endswith(".json"):
            continue
        stem = key[len(prefix):-len(".json")]
        if stem and "/" not in stem:
            ids.append(stem)
    return tuple(sorted(set(ids)))


def audit_issuer(store: Any, issuer_id: str) -> IssuerRecoveryState:
    """Classify one issuer's recovery state. Performs zero writes.

    ``admitted``: the pointer verifies via ``load_latest_generation``.
    ``absent``: no pointer and no manifest under the issuer prefix.
    ``pointer_absent_generation_present``: lost publication — a manifest
    exists but no pointer does; re-pointing is a publisher act, so the state
    carries ``recovery="publisher_repoint_required"`` and never writes a
    pointer here. ``pointer_unverifiable``: the pointer exists but the
    latest generation cannot be loaded/verified. ``listing_unsupported``:
    the store cannot list, a typed gap rather than a pass.
    """
    _require_issuer_id(issuer_id)
    try:
        generation: ProductionDatasetGeneration | None = load_latest_generation(store, issuer_id)
    except ProductionDatasetError:
        return IssuerRecoveryState(issuer_id=issuer_id, state=AUDIT_STATE_POINTER_UNVERIFIABLE)
    if generation is not None:
        return IssuerRecoveryState(
            issuer_id=issuer_id,
            state=AUDIT_STATE_ADMITTED,
            generation_id=generation.generation_id,
        )
    listed = _list_generation_ids(store, issuer_id)
    if listed is None:
        return IssuerRecoveryState(issuer_id=issuer_id, state=AUDIT_STATE_LISTING_UNSUPPORTED)
    if listed:
        return IssuerRecoveryState(
            issuer_id=issuer_id,
            state=AUDIT_STATE_POINTER_ABSENT_GENERATION_PRESENT,
            recovery=RECOVERY_PUBLISHER_REPOINT_REQUIRED,
            manifest_generation_ids=listed,
        )
    return IssuerRecoveryState(issuer_id=issuer_id, state=AUDIT_STATE_ABSENT)


# ---------------------------------------------------------------------------
# 4. Effect-unknown reconciliation (read only, zero writes)
# ---------------------------------------------------------------------------


def reconcile_effect_unknown(store: Any, issuer_id: str, expected_generation_id: str) -> str:
    """Reconcile an A18 ambiguous publish against the ORIGINAL target.

    Read-only: never retries a publish, never writes, never fails over.
    Returns exactly one of ``landed`` (the pointer names the expected
    generation and it verifies), ``manifest_landed_pointer_not_advanced``
    (no pointer, but the expected generation's manifest object is present),
    ``not_landed`` (a VERIFIED absence: no pointer and no manifest object
    for the expected generation), or ``pointer_names_other_generation`` (a
    different verified generation is live under ``latest``). A pointer that
    exists but cannot be verified — corrupt, unparseable, or naming a
    generation that fails verification — proves nothing about landing: the
    call raises ``ProductionDatasetEffectUnknownError`` so the target stays
    EFFECT_UNKNOWN (A18) instead of being reported ``not_landed``.
    """
    _require_issuer_id(issuer_id)
    if not isinstance(expected_generation_id, str) or not expected_generation_id:
        raise ProductionDatasetError("recovery drill expected generation id is malformed")
    try:
        generation = load_latest_generation(store, issuer_id)
    except ProductionDatasetEffectUnknownError:
        raise
    except ProductionDatasetError as exc:
        # A pointer that exists but cannot be verified proves nothing about
        # landing: the outcome on the original target stays EFFECT_UNKNOWN
        # (A18) — never "not landed" and never replayed.
        raise ProductionDatasetEffectUnknownError(
            "recovery drill reconciliation found an unverifiable pointer; "
            "landing on the original target is unknown"
        ) from exc
    if generation is not None:
        if generation.generation_id == expected_generation_id:
            return RECONCILE_LANDED
        return RECONCILE_POINTER_NAMES_OTHER_GENERATION
    if (
        _read_strict(
            store,
            production_manifest_key(issuer_id, expected_generation_id),
            DRILL_MAX_MANIFEST_BYTES,
        )
        is not None
    ):
        return RECONCILE_MANIFEST_LANDED_POINTER_NOT_ADVANCED
    return RECONCILE_NOT_LANDED
