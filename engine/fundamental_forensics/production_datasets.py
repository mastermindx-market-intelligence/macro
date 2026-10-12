"""FIF D3: immutable production issuer-dataset store (content-addressed generations).

Private-store layout, mirroring the sealed-snapshot conventions
(``attested_query_snapshots.py`` / ``query_snapshots.py``)::

    fundamental_forensics/production-datasets/v1/
      objects/sha256/<xx>/<digest>.bin                     # content-addressed payloads
      issuers/<issuer_id>/generations/<generation_id>.json  # immutable manifest (create-only)
      issuers/<issuer_id>/latest.json                       # CAS pointer (advances last)

Laws implemented here (WS:FINANCIAL-INTELLIGENCE-FABRIC, program
``fundamental-forensics``):

- **A17 (digest-bound immutable generations).** The generation id is
  ``stable_id("ffprods", issuer_id, sha256(canonical manifest core))``, so the
  manifest key is derived from its own content core and any byte change
  anywhere is a *different* generation id. A generation is published only when
  every required role object exists with exact byte_length and a matching
  sha256; a create-only collision at the same id is proof of drift and a hard
  error, never an overwrite.
- **A18 (EFFECT_UNKNOWN on write loss).** Immutable objects and the manifest
  are created with ``put_bytes_strict_conditional(expected_version=None)``. An
  exceptional or ``False`` outcome is reconciled by a bounded read-back on the
  SAME carrier — exact bytes prove idempotent completion — and never falls
  through to an unconditional ``put_bytes``. The ``latest`` pointer advances by
  compare-and-swap on the opaque version; a newer concurrent winner is
  preserved, never overwritten or rewound. A failed publish leaves ``latest``
  at the prior complete generation.

Publication contract: ``single_writer_operator_only`` (the operator/acquisition
lane materializes datasets off the request path, at the D1 seam). This module
performs no SEC fetch, no iXBRL extraction, and no model call, and mints no
wall clock: every timestamp is caller-supplied.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .financial_intelligence_packet import (
    EntityInput,
    PacketEvidenceDigests,
    digest_builder_source,
)
from .query_service import CanonicalEntityBinding
from .raw_ledger import RawFactLedger, canonical_json, parse_utc, stable_id, utc_text

PRODUCTION_DATASET_SCHEMA = "fundamental_forensics.production_issuer_dataset/v1"
PRODUCTION_DATASET_POINTER_SCHEMA = "fundamental_forensics.production_issuer_dataset_pointer/v1"
PRODUCTION_DATASET_FILING_METADATA_SCHEMA = (
    "fundamental_forensics.production_dataset_filing_metadata/v1"
)
PRODUCTION_DATASET_ENTITY_SCHEMA = (
    "fundamental_forensics.production_dataset_entity/v1"
)
PRODUCTION_DATASET_STATEMENT_INDEX_SCHEMA = (
    "fundamental_forensics.production_dataset_statement_index/v1"
)
PRODUCTION_DATASET_PREFIX = "fundamental_forensics/production-datasets/v1"
PRODUCTION_DATASET_GENERATION_ID_PREFIX = "ffprods"
PRODUCTION_DATASET_PUBLICATION_CONTRACT = "single_writer_operator_only"

# Role objects are JSON payloads, mirroring the query_snapshots v1 roles.
PRODUCTION_DATASET_ROLES: tuple[str, ...] = (
    "ledger_json",
    "filing_metadata_json",
    "registry_json",
    "entity_json",
    "statement_packages_index_json",
    "lineage_evidence_json",
)
_ROLE_SET = frozenset(PRODUCTION_DATASET_ROLES)

GENERATION_ID_RE = re.compile(r"\Affprods_[a-f0-9]{64}\Z")
_SHA256_RE = re.compile(r"\A[a-f0-9]{64}\Z")
_ACCESSION_RE = re.compile(r"\A[0-9]{10}-[0-9]{2}-[0-9]{6}\Z")

HARD_MAX_PRODUCTION_MANIFEST_BYTES = 4 * 1024 * 1024
HARD_MAX_PRODUCTION_ROLE_BYTES = 256 * 1024 * 1024
HARD_MAX_PRODUCTION_MEMBER_BYTES = 64 * 1024 * 1024
HARD_MAX_PRODUCTION_POINTER_BYTES = 16 * 1024
HARD_MAX_PRODUCTION_ROLE_JSON_NODES = 2_000_000

# The delivery law lives with the query adapter; repeated here only as the
# capture-basis vocabulary the manifest admits. attested=true requires a D2
# attestation admission reference, which does not exist yet.
LAWFUL_CAPTURE_BASES = frozenset({"reconstruction"})


class ProductionDatasetError(RuntimeError):
    """A production dataset generation is malformed, incomplete, or untrustworthy."""


class ProductionDatasetEffectUnknownError(ProductionDatasetError):
    """A18: an ambiguous write whose effect on its ORIGINAL target is unknown.

    Reconciliation on the same carrier could not prove idempotent completion.
    The remedy is a re-run of ``publish_production_dataset`` with the same
    inputs (every key is content-addressed or create-only, so the retry is
    idempotent) — never a write through a different key, bucket, or carrier.
    """


class ProductionDatasetModeError(RuntimeError):
    """FIF_FINANCIAL_DATASET_MODE holds an unsupported value (names-only log)."""


# ---------------------------------------------------------------------------
# Keys
# ---------------------------------------------------------------------------


def production_object_key(digest: str) -> str:
    return f"{PRODUCTION_DATASET_PREFIX}/objects/sha256/{digest[:2]}/{digest}.bin"


def production_manifest_key(issuer_id: str, generation_id: str) -> str:
    return f"{PRODUCTION_DATASET_PREFIX}/issuers/{issuer_id}/generations/{generation_id}.json"


def production_latest_key(issuer_id: str) -> str:
    return f"{PRODUCTION_DATASET_PREFIX}/issuers/{issuer_id}/latest.json"


# ---------------------------------------------------------------------------
# Store construction (no undocumented fallback: None means no store)
# ---------------------------------------------------------------------------


def build_production_dataset_store(local_dir: str | Path | None = None):
    """Build the private production-dataset store, or None when unconfigured.

    Precedence mirrors ``research_vault.r2_store.build_store``: an explicit
    local dir, then ``FIF_PRODUCTION_DATASET_LOCAL_STORE``, then the dedicated
    private research-store family. Generic ``R2_*`` values are never a
    fallback. Both keys are documented alongside ``FIF_FINANCIAL_DATASET_MODE``
    in ``research/financial_intelligence_fabric/FIF_3A3_REUSE_MAP.md``.
    """
    if local_dir:
        from engine.research_vault.r2_store import LocalStore  # noqa: PLC0415

        return LocalStore(Path(local_dir))
    env_local = os.environ.get("FIF_PRODUCTION_DATASET_LOCAL_STORE")
    if env_local:
        from engine.research_vault.r2_store import LocalStore  # noqa: PLC0415

        return LocalStore(Path(env_local))
    from engine.research_vault.r2_store import build_store  # noqa: PLC0415

    return build_store()


# ---------------------------------------------------------------------------
# Publication material
# ---------------------------------------------------------------------------


def snapshot_core_registry_payload(repo_root: str | Path) -> dict[str, Any]:
    """Snapshot the repository's governed v1 core registry as role payload.

    The acquisition/test lane calls this at dataset build time so the served
    registry is a property of the dataset (A12), never of the live repo.
    """
    from .metric_registry import _load_yaml, load_core_metric_registry  # noqa: PLC0415

    root = Path(repo_root)
    metric_root = root / "config" / "fundamental_forensics" / "metrics" / "v1"
    catalog = _load_yaml(metric_root / "metric_catalog.yaml", label="catalog")
    mappings = _load_yaml(metric_root / "mappings" / "core.yaml", label="mappings")
    formulas = _load_yaml(metric_root / "formulas" / "core.yaml", label="formulas")
    # Validate the snapshot exactly as the loader would, so a publication can
    # never pin a registry that cannot be rebuilt on the request path.
    load_core_metric_registry(root)
    return {"catalog": catalog, "mappings": mappings, "formulas": formulas}


def registry_from_payload(payload: Mapping[str, Any]):
    """Rebuild the pinned MetricRegistry from its snapshot payload."""
    from .metric_registry import metric_registry_from_dicts  # noqa: PLC0415

    if not isinstance(payload, Mapping):
        raise ProductionDatasetError("registry payload is malformed")
    keys = {"catalog", "mappings", "formulas"}
    if set(payload) != keys:
        raise ProductionDatasetError("registry payload is malformed")
    try:
        return metric_registry_from_dicts(
            payload["catalog"], payload["mappings"], payload["formulas"]
        )
    except Exception as exc:  # noqa: BLE001 - any rebuild failure is unavailability
        raise ProductionDatasetError("registry payload cannot be rebuilt") from exc


@dataclass(frozen=True)
class ProductionDatasetMaterial:
    """Everything one generation binds, supplied by the acquisition lane.

    ``admitted_at`` is the dataset's own admission clock (when the generation
    became servable) and doubles as the pointer's monotonic publication clock;
    it is caller-supplied and never ``now()``.
    """

    binding: CanonicalEntityBinding
    entity: EntityInput
    ledger: Any
    filing_metadata: Mapping[str, Any]
    registry_payload: Mapping[str, Any]
    admitted_at: datetime
    source_recorded_at_floor: datetime | None = None
    packages: tuple[Any, ...] = ()
    lineage_evidence: tuple[Any, ...] = ()
    input_digests: PacketEvidenceDigests | None = None
    security_id: str | None = None
    listing_key: str | None = None
    supersedes_generation: str | None = None
    packet_builder_digest: str | None = None


@dataclass(frozen=True)
class ProductionDatasetPublication:
    generation_id: str
    manifest_key: str
    admitted_at: str


# ---------------------------------------------------------------------------
# Role payload serialization
# ---------------------------------------------------------------------------


def _ledger_role_payload(ledger: Any) -> bytes:
    if not isinstance(ledger, RawFactLedger):
        raise ProductionDatasetError("production dataset ledger is malformed")
    try:
        return canonical_json(ledger.to_dict()).encode("utf-8")
    except Exception as exc:  # noqa: BLE001
        raise ProductionDatasetError("production dataset ledger cannot be serialized") from exc


def _filing_metadata_role_payload(filing_metadata: Mapping[str, Any]) -> bytes:
    if not isinstance(filing_metadata, Mapping):
        raise ProductionDatasetError("production dataset filing metadata is malformed")
    entries = []
    for accession in sorted(filing_metadata):
        value = filing_metadata[accession]
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            entries.append({"accession": accession, "typed": True, "value": to_dict()})
        elif isinstance(value, Mapping):
            entries.append({"accession": accession, "typed": False, "value": dict(value)})
        else:
            raise ProductionDatasetError("production dataset filing metadata is malformed")
    payload = {
        "schema": PRODUCTION_DATASET_FILING_METADATA_SCHEMA,
        "entries": entries,
    }
    return canonical_json(payload).encode("utf-8")


def filing_metadata_from_role_payload(payload: bytes) -> dict[str, Any]:
    """Rebuild filing metadata preserving each entry's typed/raw shape."""
    document = _decode_json_object(payload, field="filing metadata role")
    if (
        document.get("schema") != PRODUCTION_DATASET_FILING_METADATA_SCHEMA
        or not isinstance(document.get("entries"), list)
    ):
        raise ProductionDatasetError("filing metadata role is malformed")
    from .query import FilingMetadata  # noqa: PLC0415

    out: dict[str, Any] = {}
    for entry in document["entries"]:
        if not isinstance(entry, dict) or set(entry) != {"accession", "typed", "value"}:
            raise ProductionDatasetError("filing metadata role is malformed")
        accession = entry["accession"]
        if not isinstance(accession, str) or accession in out:
            raise ProductionDatasetError("filing metadata role is malformed")
        value = entry["value"]
        if entry["typed"] is True:
            try:
                out[accession] = FilingMetadata(**dict(value))
            except Exception as exc:  # noqa: BLE001
                raise ProductionDatasetError("filing metadata role is malformed") from exc
        else:
            if not isinstance(value, dict):
                raise ProductionDatasetError("filing metadata role is malformed")
            out[accession] = dict(value)
    if not out:
        raise ProductionDatasetError("filing metadata role is empty")
    return out


def _entity_role_payload(material: ProductionDatasetMaterial) -> bytes:
    digests = material.input_digests or PacketEvidenceDigests()
    payload = {
        "schema": PRODUCTION_DATASET_ENTITY_SCHEMA,
        "binding": {
            "entity_id": material.binding.entity_id,
            "cik": material.binding.cik,
            "ticker": material.binding.ticker,
            "source_entity_id": material.binding.source_entity_id,
        },
        "entity": {
            "entity_id": material.entity.entity_id,
            "cik": material.entity.cik,
            "ticker": material.entity.ticker,
            "name": material.entity.name,
            "identity_basis": material.entity.identity_basis,
            "source_entity_id": material.entity.source_entity_id,
        },
        "security_id": material.security_id,
        "listing_key": material.listing_key,
        "evidence_digests": digests.to_dict(),
    }
    return canonical_json(payload).encode("utf-8")


def _statement_index_role_payload(packages: tuple[Any, ...]) -> tuple[bytes, dict[str, bytes]]:
    """Serialize the per-accession package index plus its member bytes.

    Returns the role payload and the content-addressed member objects the
    publication must write (name -> bytes). Member rows carry the same fields
    the statement envelope already trusts.
    """
    accessions: list[dict[str, Any]] = []
    member_objects: dict[str, bytes] = {}
    seen_accessions: set[str] = set()
    for package in packages:
        manifest = getattr(package, "manifest", None)
        members = getattr(package, "members", None)
        if not isinstance(manifest, Mapping) or not isinstance(members, Mapping):
            raise ProductionDatasetError("production statement package is malformed")
        accession = manifest.get("accession")
        if not isinstance(accession, str) or not _ACCESSION_RE.fullmatch(accession):
            raise ProductionDatasetError("production statement package is malformed")
        if accession in seen_accessions:
            raise ProductionDatasetError("production statement package is duplicated")
        seen_accessions.add(accession)
        index_sha256 = manifest.get("index_sha256")
        if not isinstance(index_sha256, str) or not _SHA256_RE.fullmatch(index_sha256):
            raise ProductionDatasetError("production statement package index digest is malformed")
        rows: list[dict[str, Any]] = []
        manifest_members = manifest.get("members")
        if not isinstance(manifest_members, list):
            raise ProductionDatasetError("production statement package inventory is malformed")
        for item in manifest_members:
            if not isinstance(item, dict):
                raise ProductionDatasetError("production statement package inventory is malformed")
            name = item.get("name")
            if not isinstance(name, str) or not name:
                raise ProductionDatasetError("production statement package inventory is malformed")
            state = item.get("state")
            row = {"name": name, "state": state, "role": item.get("role")}
            if state == "stored":
                payload = members.get(name)
                if not isinstance(payload, (bytes, bytearray)):
                    raise ProductionDatasetError("production statement member is missing")
                digest = hashlib.sha256(payload).hexdigest()
                row["content_sha256"] = digest
                row["byte_length"] = len(payload)
                member_objects[f"{accession}\x1f{name}"] = bytes(payload)
            else:
                row["content_sha256"] = item.get("content_sha256")
                row["byte_length"] = item.get("byte_length")
            rows.append(row)
        accessions.append(
            {
                "accession": accession,
                "index_sha256": index_sha256,
                "manifest": _package_manifest_payload(manifest),
                "members": rows,
            }
        )
    payload = {
        "schema": PRODUCTION_DATASET_STATEMENT_INDEX_SCHEMA,
        "accessions": accessions,
    }
    return canonical_json(payload).encode("utf-8"), member_objects


_PACKAGE_MANIFEST_PASSTHROUGH_FIELDS = (
    "entity_id",
    "cik",
    "accession",
    "form",
    "primary_document",
    "period_of_report",
    "filing_date",
    "source_accepted_at",
    "fixture_recorded_at",
    "archive_index_url",
    "index_sha256",
    "index_byte_length",
    "member_count",
    "retained_count",
    "statement_roles",
    "related_event_ref",
)


def _package_manifest_payload(manifest: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name in _PACKAGE_MANIFEST_PASSTHROUGH_FIELDS:
        if name in manifest:
            out[name] = manifest[name]
    return out


def _lineage_role_payload(lineage_evidence: tuple[Any, ...]) -> bytes:
    receipts = []
    for item in lineage_evidence:
        to_dict = getattr(item, "to_dict", None)
        if not callable(to_dict):
            raise ProductionDatasetError("production lineage evidence is malformed")
        receipts.append(to_dict())
    return canonical_json({"schema": "fundamental_forensics.production_dataset_lineage/v1", "receipts": receipts}).encode("utf-8")


def lineage_from_role_payload(payload: bytes) -> tuple[Any, ...]:
    from .lineage_evidence import LineageEvidenceReceipt  # noqa: PLC0415

    document = _decode_json_object(payload, field="lineage evidence role")
    if document.get("schema") != "fundamental_forensics.production_dataset_lineage/v1":
        raise ProductionDatasetError("lineage evidence role is malformed")
    receipts_raw = document.get("receipts")
    if not isinstance(receipts_raw, list):
        raise ProductionDatasetError("lineage evidence role is malformed")
    receipts = []
    for raw in receipts_raw:
        if not isinstance(raw, dict):
            raise ProductionDatasetError("lineage evidence role is malformed")
        values = dict(raw)
        try:
            values["source_known_at"] = parse_utc(
                values.get("source_known_at"), field_name="source_known_at"
            )
            values["system_available_at"] = parse_utc(
                values.get("system_available_at"), field_name="system_available_at"
            )
            receipts.append(LineageEvidenceReceipt(**values))
        except ProductionDatasetError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ProductionDatasetError("lineage evidence role is malformed") from exc
    return tuple(receipts)


# ---------------------------------------------------------------------------
# Manifest construction and verification
# ---------------------------------------------------------------------------


def _manifest_core(
    *,
    issuer_block: Mapping[str, Any],
    accessions: list[dict[str, Any]],
    role_rows: list[dict[str, Any]],
    packet_builder_digest: str,
    admitted_at: datetime | str,
    source_recorded_at_floor: datetime | str | None,
    supersedes_generation: str | None,
) -> dict[str, Any]:
    admitted_dt = _as_utc_or_text(admitted_at, field_name="clocks.admitted_at")
    floor_dt = (
        _as_utc_or_text(source_recorded_at_floor, field_name="clocks.source_recorded_at_floor")
        if source_recorded_at_floor is not None
        else None
    )
    roles = {row["role"]: row for row in role_rows}
    if set(roles) != _ROLE_SET:
        raise ProductionDatasetError("production dataset role set is inexact")
    return {
        "schema": PRODUCTION_DATASET_SCHEMA,
        "issuer": dict(issuer_block),
        "accessions": accessions,
        "roles": [
            {"role": role, "sha256": roles[role]["sha256"], "byte_length": roles[role]["byte_length"]}
            for role in PRODUCTION_DATASET_ROLES
        ],
        "registry_content_sha256": roles["registry_json"]["sha256"],
        "packet_builder_digest": packet_builder_digest,
        "clocks": {
            "admitted_at": utc_text(admitted_dt),
            "source_recorded_at_floor": utc_text(floor_dt) if floor_dt is not None else None,
        },
        "supersedes": supersedes_generation,
    }


def _as_utc_or_text(value: datetime | str, *, field_name: str) -> datetime:
    """Normalize an aware datetime or its canonical text to an aware UTC datetime."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ProductionDatasetError(f"{field_name} requires an aware UTC clock")
        return value.astimezone(timezone.utc)
    parsed = parse_utc(value if isinstance(value, str) else None, field_name=field_name)
    if parsed is None:
        raise ProductionDatasetError(f"{field_name} is malformed")
    return parsed


def _generation_id_from_core(issuer_id: str, core: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(canonical_json(core).encode("utf-8")).hexdigest()
    return stable_id(PRODUCTION_DATASET_GENERATION_ID_PREFIX, issuer_id, digest)


def _decode_json_object(payload: bytes, *, field: str) -> dict[str, Any]:
    if not isinstance(payload, (bytes, bytearray)):
        raise ProductionDatasetError(f"{field} is malformed")
    try:
        document = json.loads(bytes(payload).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProductionDatasetError(f"{field} is malformed") from exc
    if not isinstance(document, dict):
        raise ProductionDatasetError(f"{field} is malformed")
    return document


def _read_bounded_optional(store: Any, key: str, *, maximum: int) -> bytes | None:
    """Strict bounded read; ``None`` is authoritative absence, failures raise."""
    try:
        payload = store.get_bytes_strict_bounded(key, maximum)
    except Exception as exc:  # noqa: BLE001
        raise ProductionDatasetError("production dataset bounded read failed") from exc
    if payload is None:
        return None
    if not isinstance(payload, bytes) or not payload:
        raise ProductionDatasetError("production dataset bounded read is malformed")
    return payload


def _read_versioned_pointer(store: Any, issuer_id: str):
    from engine.research_vault.r2_store import VersionedBytes  # noqa: PLC0415

    try:
        observed = store.get_bytes_strict_bounded_versioned(
            production_latest_key(issuer_id), HARD_MAX_PRODUCTION_POINTER_BYTES
        )
    except Exception as exc:  # noqa: BLE001
        raise ProductionDatasetError("production dataset pointer read failed") from exc
    if type(observed) is not VersionedBytes:
        raise ProductionDatasetError("production dataset pointer read is malformed")
    if observed.data is None and observed.version is not None:
        raise ProductionDatasetError("production dataset pointer read is malformed")
    if observed.data is not None and (
        type(observed.data) is not bytes
        or not isinstance(observed.version, str)
        or not observed.version
    ):
        raise ProductionDatasetError("production dataset pointer read is malformed")
    return observed


# ---------------------------------------------------------------------------
# A18 write law
# ---------------------------------------------------------------------------


def _create_immutable(store: Any, *, key: str, payload: bytes, maximum: int) -> None:
    """Create one immutable object at an absent key, then prove its bytes.

    A ``False`` or exceptional outcome receives bounded read-back
    reconciliation only; it never falls through to an unconditional put. Exact
    bytes prove idempotent completion; anything else preserves EFFECT_UNKNOWN
    on the original target as a hard error.
    """
    try:
        written = store.put_bytes_strict_conditional(
            key,
            payload,
            expected_version=None,
            content_type="application/octet-stream",
        )
    except Exception as exc:  # noqa: BLE001 - the commit may have succeeded
        reconcile = _try_read_back(store, key, payload, maximum=maximum)
        if reconcile is None:
            raise ProductionDatasetEffectUnknownError(
                "production dataset immutable write outcome could not be reconciled"
            ) from exc
        if reconcile is False:
            raise ProductionDatasetError(
                "production dataset immutable object collision"
            ) from exc
        return
    if written is True:
        echoed = _try_read_back(store, key, payload, maximum=maximum)
        if echoed is not True:
            raise ProductionDatasetError(
                "production dataset immutable object read-back mismatch"
            )
        return
    if written is False:
        reconcile = _try_read_back(store, key, payload, maximum=maximum)
        if reconcile is True:
            return
        if reconcile is False:
            raise ProductionDatasetError("production dataset immutable object collision")
        raise ProductionDatasetEffectUnknownError(
            "production dataset immutable write outcome could not be reconciled"
        )
    raise ProductionDatasetError("production dataset immutable write failed")


def _try_read_back(store: Any, key: str, payload: bytes, *, maximum: int) -> bool | None:
    """True = exact bytes; False = different bytes present; None = unreadable/absent."""
    try:
        echoed = _read_bounded_optional(store, key, maximum=maximum)
    except ProductionDatasetError:
        return None
    if echoed is None:
        return None
    return echoed == payload


def _pointer_after_failed_cas(
    store: Any,
    *,
    issuer_id: str,
    payload: bytes,
    pointer: Mapping[str, Any],
    cause: BaseException | None,
) -> None:
    """Reconcile a conflict or an ambiguous pointer CAS.

    Exact bytes prove idempotent completion. A newer concurrent winner is
    preserved rather than overwritten or rewound; every other state is a hard
    failure.
    """
    observed = _read_versioned_pointer(store, issuer_id)
    if observed.data == payload:
        return
    if observed.data is not None:
        current = _decode_pointer(observed.data, issuer_id=issuer_id)
        if current.get("generation_id") == pointer.get("generation_id"):
            raise ProductionDatasetError(
                "production dataset latest pointer disagrees with immutable generation"
            ) from cause
        if _pointer_clock(pointer) <= _pointer_clock(current):
            raise ProductionDatasetError(
                "stale production dataset cannot rewind independent latest pointer"
            ) from cause
    if cause is not None:
        raise ProductionDatasetEffectUnknownError(
            "production dataset latest pointer conditional write outcome could not be reconciled"
        ) from cause
    raise ProductionDatasetError("production dataset latest pointer compare-and-swap conflict")


def _pointer_clock(pointer: Mapping[str, Any]) -> datetime:
    value = parse_utc(pointer.get("published_at"), field_name="published_at")
    if value is None:
        raise ProductionDatasetError("production dataset pointer clock is malformed")
    return value


def _pointer_payload(issuer_id: str, generation_id: str, manifest_key: str, admitted_at: datetime) -> bytes:
    payload = {
        "schema": PRODUCTION_DATASET_POINTER_SCHEMA,
        "issuer_id": issuer_id,
        "generation_id": generation_id,
        "manifest_key": manifest_key,
        "admitted_at": utc_text(admitted_at),
        "published_at": utc_text(admitted_at),
    }
    return canonical_json(payload).encode("utf-8")


_POINTER_KEYS = frozenset(
    {"schema", "issuer_id", "generation_id", "manifest_key", "admitted_at", "published_at"}
)


def _decode_pointer(payload: bytes, *, issuer_id: str) -> dict[str, Any]:
    document = _decode_json_object(payload, field="production dataset pointer")
    if set(document) != _POINTER_KEYS:
        raise ProductionDatasetError("production dataset pointer is malformed")
    if document.get("schema") != PRODUCTION_DATASET_POINTER_SCHEMA:
        raise ProductionDatasetError("production dataset pointer is malformed")
    if document.get("issuer_id") != issuer_id:
        raise ProductionDatasetError("production dataset pointer is malformed")
    generation_id = document.get("generation_id")
    if not isinstance(generation_id, str) or not GENERATION_ID_RE.fullmatch(generation_id):
        raise ProductionDatasetError("production dataset pointer is malformed")
    if document.get("manifest_key") != production_manifest_key(issuer_id, generation_id):
        raise ProductionDatasetError("production dataset pointer is malformed")
    for clock in ("admitted_at", "published_at"):
        if parse_utc(document.get(clock), field_name=clock) is None:
            raise ProductionDatasetError("production dataset pointer is malformed")
    return document


def _publish_pointer(store: Any, *, issuer_id: str, generation_id: str, admitted_at: datetime) -> None:
    manifest_key = production_manifest_key(issuer_id, generation_id)
    payload = _pointer_payload(issuer_id, generation_id, manifest_key, admitted_at)
    pointer = _decode_pointer(payload, issuer_id=issuer_id)
    prior = _read_versioned_pointer(store, issuer_id)
    if prior.data is not None:
        old = _decode_pointer(prior.data, issuer_id=issuer_id)
        if old.get("generation_id") == generation_id:
            if prior.data != payload:
                raise ProductionDatasetError(
                    "production dataset latest pointer disagrees with immutable generation"
                )
            return
        if _pointer_clock(pointer) <= _pointer_clock(old):
            raise ProductionDatasetError(
                "stale production dataset cannot rewind independent latest pointer"
            )
    try:
        written = store.put_bytes_strict_conditional(
            production_latest_key(issuer_id),
            payload,
            expected_version=prior.version,
            content_type="application/json",
        )
    except Exception as exc:  # noqa: BLE001 - the CAS may have committed
        _pointer_after_failed_cas(
            store, issuer_id=issuer_id, payload=payload, pointer=pointer, cause=exc
        )
        return
    if written is not True:
        _pointer_after_failed_cas(
            store, issuer_id=issuer_id, payload=payload, pointer=pointer, cause=None
        )
        return
    echoed = _read_versioned_pointer(store, issuer_id)
    if echoed.data == payload:
        return
    # A successful CAS is the linearization point: another compliant writer may
    # have advanced from our version before the read-back. Accept only a
    # canonical strictly newer successor; never roll back over it.
    if echoed.data is not None:
        successor = _decode_pointer(echoed.data, issuer_id=issuer_id)
        if _pointer_clock(successor) > _pointer_clock(pointer):
            return
    raise ProductionDatasetError("production dataset latest pointer read-back mismatch")


# ---------------------------------------------------------------------------
# Publication
# ---------------------------------------------------------------------------


def _require_conditional_store(store: Any) -> None:
    from engine.research_vault.r2_store import StrictConditionalWriteStore  # noqa: PLC0415

    if not isinstance(store, StrictConditionalWriteStore):
        raise ProductionDatasetError(
            "production dataset publication requires a StrictConditionalWriteStore"
        )
    try:
        store.validate_strict_conditional_write_capability()
    except Exception as exc:  # noqa: BLE001
        raise ProductionDatasetError(
            "production dataset publication requires a StrictConditionalWriteStore"
        ) from exc


def _packet_builder_digest(material: ProductionDatasetMaterial) -> str:
    digest = material.packet_builder_digest
    if digest is not None:
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise ProductionDatasetError("production dataset builder digest is malformed")
        return digest
    builder_path = Path(__file__).resolve().parents[2] / "engine" / "fundamental_forensics" / "financial_intelligence_packet.py"
    return digest_builder_source(builder_path.read_bytes())


def publish_production_dataset(
    store: Any,
    material: ProductionDatasetMaterial,
    *,
    skip_pointer: bool = False,
) -> ProductionDatasetPublication:
    """Materialize one immutable generation, then advance the latest pointer.

    Order (A17/A18): validate inputs and the store BEFORE any write; write
    every content-addressed role and member object create-only with byte-exact
    read-back; write the immutable manifest create-only; only then advance the
    per-issuer ``latest`` pointer by CAS. ``skip_pointer`` exists for the
    acquisition lane's staged publishes and for tests that must leave ``latest``
    untouched; the request path never calls this function.
    """
    _require_conditional_store(store)
    binding = material.binding
    if not isinstance(binding, CanonicalEntityBinding):
        raise ProductionDatasetError("production dataset binding is malformed")
    entity = material.entity
    if not isinstance(entity, EntityInput):
        raise ProductionDatasetError("production dataset entity is malformed")
    if (
        entity.entity_id != binding.entity_id
        or entity.cik != binding.cik
        or entity.ticker != binding.ticker
        or entity.source_entity_id != binding.source_entity_id
    ):
        raise ProductionDatasetError("production dataset entity disagrees with binding")
    if binding.cik != binding.source_entity_id:
        raise ProductionDatasetError("production dataset binding is malformed")
    admitted_at = material.admitted_at
    if not isinstance(admitted_at, datetime) or admitted_at.tzinfo is None:
        raise ProductionDatasetError("production dataset admitted_at requires an aware UTC clock")
    admitted_at = admitted_at.astimezone(timezone.utc)
    floor = material.source_recorded_at_floor
    if floor is not None:
        if not isinstance(floor, datetime) or floor.tzinfo is None:
            raise ProductionDatasetError(
                "production dataset source_recorded_at_floor requires an aware UTC clock"
            )
        floor = floor.astimezone(timezone.utc)
    if floor is not None and floor > admitted_at:
        raise ProductionDatasetError("production dataset recorded floor exceeds admission clock")
    if material.supersedes_generation is not None and not GENERATION_ID_RE.fullmatch(
        material.supersedes_generation
    ):
        raise ProductionDatasetError("production dataset supersession reference is malformed")

    # The registry snapshot must rebuild exactly (A12: dataset-pinned registry).
    registry_from_payload(material.registry_payload)

    role_payloads: dict[str, bytes] = {
        "ledger_json": _ledger_role_payload(material.ledger),
        "filing_metadata_json": _filing_metadata_role_payload(material.filing_metadata),
        "registry_json": canonical_json(dict(material.registry_payload)).encode("utf-8"),
        "entity_json": _entity_role_payload(material),
        "statement_packages_index_json": None,  # filled below
        "lineage_evidence_json": _lineage_role_payload(tuple(material.lineage_evidence)),
    }
    index_payload, member_objects = _statement_index_role_payload(tuple(material.packages))
    role_payloads["statement_packages_index_json"] = index_payload

    for role, payload in role_payloads.items():
        if not isinstance(payload, bytes) or not payload:
            raise ProductionDatasetError("production dataset role payload is malformed")
        if len(payload) > HARD_MAX_PRODUCTION_ROLE_BYTES:
            raise ProductionDatasetError("production dataset role payload exceeds bound")
    for name, payload in member_objects.items():
        if len(payload) > HARD_MAX_PRODUCTION_MEMBER_BYTES:
            raise ProductionDatasetError("production dataset member exceeds bound")

    role_rows = [
        {
            "role": role,
            "object_key": production_object_key(hashlib.sha256(role_payloads[role]).hexdigest()),
            "sha256": hashlib.sha256(role_payloads[role]).hexdigest(),
            "byte_length": len(role_payloads[role]),
        }
        for role in PRODUCTION_DATASET_ROLES
    ]
    accessions = _index_accessions_for_manifest(index_payload)
    issuer_block = {
        "entity_id": binding.entity_id,
        "cik": binding.cik,
        "ticker": binding.ticker,
        "source_entity_id": binding.source_entity_id,
        "security_id": material.security_id,
        "listing_key": material.listing_key,
    }
    core = _manifest_core(
        issuer_block=issuer_block,
        accessions=accessions,
        role_rows=role_rows,
        packet_builder_digest=_packet_builder_digest(material),
        admitted_at=admitted_at,
        source_recorded_at_floor=floor,
        supersedes_generation=material.supersedes_generation,
    )
    generation_id = _generation_id_from_core(binding.entity_id, core)
    manifest = dict(core)
    manifest["generation_id"] = generation_id
    manifest["objects"] = role_rows
    manifest_payload = canonical_json(manifest).encode("utf-8")
    if len(manifest_payload) > HARD_MAX_PRODUCTION_MANIFEST_BYTES:
        raise ProductionDatasetError("production dataset manifest exceeds bound")
    manifest_key = production_manifest_key(binding.entity_id, generation_id)

    # A17: every immutable artifact is written create-only and read back
    # byte-for-byte BEFORE the pointer may advance.
    for row in role_rows:
        _create_immutable(
            store,
            key=row["object_key"],
            payload=role_payloads[row["role"]],
            maximum=HARD_MAX_PRODUCTION_ROLE_BYTES,
        )
    for key, payload in member_objects.items():
        digest = hashlib.sha256(payload).hexdigest()
        _create_immutable(
            store,
            key=production_object_key(digest),
            payload=payload,
            maximum=HARD_MAX_PRODUCTION_MEMBER_BYTES,
        )
    _create_immutable(
        store,
        key=manifest_key,
        payload=manifest_payload,
        maximum=HARD_MAX_PRODUCTION_MANIFEST_BYTES,
    )
    if not skip_pointer:
        _publish_pointer(
            store,
            issuer_id=binding.entity_id,
            generation_id=generation_id,
            admitted_at=admitted_at,
        )
    return ProductionDatasetPublication(
        generation_id=generation_id,
        manifest_key=manifest_key,
        admitted_at=utc_text(admitted_at),
    )


def _index_accessions_for_manifest(index_payload: bytes) -> list[dict[str, Any]]:
    document = _decode_json_object(index_payload, field="statement index role")
    if document.get("schema") != PRODUCTION_DATASET_STATEMENT_INDEX_SCHEMA:
        raise ProductionDatasetError("statement index role is malformed")
    accessions_raw = document.get("accessions")
    if not isinstance(accessions_raw, list):
        raise ProductionDatasetError("statement index role is malformed")
    out: list[dict[str, Any]] = []
    for item in accessions_raw:
        if not isinstance(item, dict):
            raise ProductionDatasetError("statement index role is malformed")
        members = item.get("members")
        if not isinstance(members, list):
            raise ProductionDatasetError("statement index role is malformed")
        out.append(
            {
                "accession": item.get("accession"),
                "index_sha256": item.get("index_sha256"),
                "members": [
                    {
                        "name": row.get("name"),
                        "sha256": row.get("content_sha256"),
                        "byte_length": row.get("byte_length"),
                    }
                    for row in members
                    if isinstance(row, dict)
                ],
            }
        )
    return out


# ---------------------------------------------------------------------------
# Loading and verification (request path)
# ---------------------------------------------------------------------------


_MANIFEST_KEYS = frozenset(
    {
        "schema",
        "generation_id",
        "issuer",
        "accessions",
        "roles",
        "registry_content_sha256",
        "packet_builder_digest",
        "clocks",
        "supersedes",
        "objects",
    }
)
_ISSUER_KEYS = frozenset(
    {"entity_id", "cik", "ticker", "source_entity_id", "security_id", "listing_key"}
)


@dataclass(frozen=True)
class ProductionDatasetGeneration:
    """One verified, immutable generation opened in memory.

    Carries the decoded manifest plus the verified role payloads. Statement
    member bytes are read and digest-verified lazily, per accession, bounded by
    the lengths the manifest binds.
    """

    manifest: dict[str, Any]
    role_payloads: dict[str, bytes] = field(repr=False, default_factory=dict)
    store: Any = field(repr=False, default=None)

    @property
    def generation_id(self) -> str:
        gid = self.manifest.get("generation_id")
        if not isinstance(gid, str):
            raise ProductionDatasetError("production dataset manifest is malformed")
        return gid

    @property
    def binding(self) -> CanonicalEntityBinding:
        issuer = self.manifest.get("issuer")
        if not isinstance(issuer, dict) or set(issuer) != _ISSUER_KEYS:
            raise ProductionDatasetError("production dataset manifest is malformed")
        return CanonicalEntityBinding(
            entity_id=issuer["entity_id"],
            cik=issuer["cik"],
            ticker=issuer["ticker"],
            source_entity_id=issuer["source_entity_id"],
        )

    @property
    def admitted_at(self) -> datetime:
        clocks = self.manifest.get("clocks")
        if not isinstance(clocks, dict):
            raise ProductionDatasetError("production dataset manifest is malformed")
        value = parse_utc(clocks.get("admitted_at"), field_name="admitted_at")
        if value is None:
            raise ProductionDatasetError("production dataset manifest is malformed")
        return value

    def delivery(self) -> dict[str, Any]:
        """The exact production delivery object this generation may mint.

        A13: a corpus fetched today, without historic capture evidence, is a
        reconstruction. ``attested`` becomes true only through a D2 attestation
        admission reference in the manifest, which does not exist yet, so this
        method refuses to mint an attested delivery until one does.
        """
        admission = self.manifest.get("attestation_admission")
        if admission is not None:
            # D2 owns this vocabulary; no lawful reference exists today.
            raise ProductionDatasetError(
                "production dataset attestation admission is not supported"
            )
        return {
            "kind": "production_issuer_dataset",
            "attested": False,
            "production_issuer_service": True,
            "dataset_generation_id": self.generation_id,
            "capture_basis": "reconstruction",
        }

    def statement_package(self, accession: str) -> tuple[dict[str, Any], dict[str, bytes]]:
        """Rebuild one statement package manifest + verified member bytes."""
        index = _decode_json_object(
            self.role_payloads["statement_packages_index_json"],
            field="statement index role",
        )
        for item in index.get("accessions") or []:
            if not isinstance(item, dict) or item.get("accession") != accession:
                continue
            members: dict[str, bytes] = {}
            for row in item.get("members") or []:
                if not isinstance(row, dict):
                    raise ProductionDatasetError("statement index role is malformed")
                if row.get("state") != "stored":
                    continue
                digest = row.get("content_sha256")
                length = row.get("byte_length")
                if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
                    raise ProductionDatasetError("statement index role is malformed")
                if not isinstance(length, int) or isinstance(length, bool) or length < 0:
                    raise ProductionDatasetError("statement index role is malformed")
                payload = _read_bounded_optional(
                    self.store, production_object_key(digest), maximum=HARD_MAX_PRODUCTION_MEMBER_BYTES
                )
                if payload is None:
                    raise ProductionDatasetError("production dataset member is missing")
                if len(payload) != length or hashlib.sha256(payload).hexdigest() != digest:
                    raise ProductionDatasetError("production dataset member digest mismatch")
                members[row["name"]] = payload
            manifest = dict(item.get("manifest") or {})
            manifest["accession"] = item.get("accession")
            manifest["index_sha256"] = item.get("index_sha256")
            manifest["members"] = [
                {
                    "name": row.get("name"),
                    "state": row.get("state"),
                    "role": row.get("role"),
                    "content_sha256": row.get("content_sha256"),
                    "byte_length": row.get("byte_length"),
                }
                for row in item.get("members") or []
                if isinstance(row, dict)
            ]
            return manifest, members
        raise KeyError(accession)

    def statement_accessions(self) -> tuple[str, ...]:
        index = _decode_json_object(
            self.role_payloads["statement_packages_index_json"],
            field="statement index role",
        )
        return tuple(
            item.get("accession")
            for item in index.get("accessions") or []
            if isinstance(item, dict)
        )


def load_generation(store: Any, issuer_id: str, generation_id: str) -> ProductionDatasetGeneration:
    """Load and verify one generation against its own digest binding.

    Fail-closed for every damage class: truncated JSON, a manifest that does
    not re-derive its own generation id, an inexact role set, a missing role
    object, or any byte_length/sha256 mismatch. The caller maps all of these
    to one indistinguishable unavailability; nothing here distinguishes them
    on the wire.
    """
    if not isinstance(generation_id, str) or not GENERATION_ID_RE.fullmatch(generation_id):
        raise ProductionDatasetError("production dataset generation id is malformed")
    manifest_payload = _read_bounded_optional(
        store,
        production_manifest_key(issuer_id, generation_id),
        maximum=HARD_MAX_PRODUCTION_MANIFEST_BYTES,
    )
    if manifest_payload is None:
        raise ProductionDatasetError("production dataset manifest is missing")
    manifest = _decode_json_object(manifest_payload, field="production dataset manifest")
    if set(manifest) != _MANIFEST_KEYS:
        raise ProductionDatasetError("production dataset manifest is malformed")
    if manifest.get("schema") != PRODUCTION_DATASET_SCHEMA:
        raise ProductionDatasetError("production dataset manifest is malformed")
    if manifest.get("generation_id") != generation_id:
        raise ProductionDatasetError("production dataset generation id mismatch")
    issuer = manifest.get("issuer")
    if not isinstance(issuer, dict) or set(issuer) != _ISSUER_KEYS:
        raise ProductionDatasetError("production dataset manifest is malformed")
    if issuer.get("entity_id") != issuer_id:
        raise ProductionDatasetError("production dataset manifest is malformed")
    objects = manifest.get("objects")
    roles = manifest.get("roles")
    if not isinstance(objects, list) or not isinstance(roles, list):
        raise ProductionDatasetError("production dataset manifest is malformed")
    if len(objects) != len(PRODUCTION_DATASET_ROLES):
        raise ProductionDatasetError("production dataset manifest is malformed")
    objects_by_role: dict[str, dict[str, Any]] = {}
    for row in objects:
        if not isinstance(row, dict) or set(row) != {"role", "object_key", "sha256", "byte_length"}:
            raise ProductionDatasetError("production dataset manifest is malformed")
        role = row.get("role")
        if role in objects_by_role:
            raise ProductionDatasetError("production dataset manifest is malformed")
        if not isinstance(row.get("sha256"), str) or not _SHA256_RE.fullmatch(row["sha256"]):
            raise ProductionDatasetError("production dataset manifest is malformed")
        if row.get("object_key") != production_object_key(row["sha256"]):
            raise ProductionDatasetError("production dataset manifest is malformed")
        length = row.get("byte_length")
        if not isinstance(length, int) or isinstance(length, bool) or length < 0:
            raise ProductionDatasetError("production dataset manifest is malformed")
        if length > HARD_MAX_PRODUCTION_ROLE_BYTES:
            raise ProductionDatasetError("production dataset manifest is malformed")
        objects_by_role[role] = row
    if set(objects_by_role) != _ROLE_SET:
        raise ProductionDatasetError("production dataset manifest is malformed")
    # The manifest must re-derive its own generation id from its content core.
    clocks = manifest.get("clocks")
    if not isinstance(clocks, dict):
        raise ProductionDatasetError("production dataset manifest is malformed")
    core_rows = [
        {"role": row["role"], "sha256": row["sha256"], "byte_length": row["byte_length"]}
        for row in objects
    ]
    stored_core = {
        key: manifest[key]
        for key in (
            "schema",
            "issuer",
            "accessions",
            "roles",
            "registry_content_sha256",
            "packet_builder_digest",
            "clocks",
            "supersedes",
        )
    }
    try:
        core = _manifest_core(
            issuer_block=stored_core["issuer"],
            accessions=stored_core["accessions"],
            role_rows=core_rows,
            packet_builder_digest=stored_core["packet_builder_digest"],
            admitted_at=clocks.get("admitted_at"),
            source_recorded_at_floor=clocks.get("source_recorded_at_floor"),
            supersedes_generation=stored_core["supersedes"],
        )
    except ProductionDatasetError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ProductionDatasetError("production dataset manifest is malformed") from exc
    if canonical_json(core) != canonical_json(stored_core):
        raise ProductionDatasetError("production dataset manifest core mismatch")
    if _generation_id_from_core(issuer_id, core) != generation_id:
        raise ProductionDatasetError("production dataset generation id mismatch")
    if manifest.get("registry_content_sha256") != objects_by_role["registry_json"]["sha256"]:
        raise ProductionDatasetError("production dataset registry digest mismatch")
    # A17: every required role object must exist with exact bytes.
    role_payloads: dict[str, bytes] = {}
    for role in PRODUCTION_DATASET_ROLES:
        row = objects_by_role[role]
        payload = _read_bounded_optional(
            store, row["object_key"], maximum=HARD_MAX_PRODUCTION_ROLE_BYTES
        )
        if payload is None:
            raise ProductionDatasetError("production dataset role object is missing")
        if len(payload) != row["byte_length"]:
            raise ProductionDatasetError("production dataset role object length mismatch")
        if hashlib.sha256(payload).hexdigest() != row["sha256"]:
            raise ProductionDatasetError("production dataset role object digest mismatch")
        role_payloads[role] = payload
    return ProductionDatasetGeneration(manifest=manifest, role_payloads=role_payloads, store=store)


def load_latest_generation(store: Any, issuer_id: str) -> ProductionDatasetGeneration | None:
    """Load the issuer's latest verified generation, or None when none exists.

    ``None`` means exactly "this available store carries no admitted
    generation for the issuer" (the 400 ``unknown entity`` case). A pointer
    that exists but cannot be verified is a hard error, never a miss.
    """
    if not isinstance(issuer_id, str) or not issuer_id:
        raise ProductionDatasetError("production dataset issuer id is malformed")
    observed = _read_versioned_pointer(store, issuer_id)
    if observed.data is None:
        return None
    pointer = _decode_pointer(observed.data, issuer_id=issuer_id)
    return load_generation(store, issuer_id, pointer["generation_id"])


def latest_generation_summary(store: Any, issuer_id: str) -> dict[str, Any] | None:
    """Names/ids only, for the health surface. Never a payload or a key."""
    observed = _read_versioned_pointer(store, issuer_id)
    if observed.data is None:
        return None
    pointer = _decode_pointer(observed.data, issuer_id=issuer_id)
    return {
        "dataset_generation_id": pointer["generation_id"],
        "admitted_at": pointer["admitted_at"],
    }


def load_query_dataset_payloads(generation: ProductionDatasetGeneration) -> dict[str, Any]:
    """Rebuild every query-servable payload from verified role bytes.

    No SEC fetch, no iXBRL parse/convert, no model call, no wall clock: the
    ledger, filing metadata, and registry are rebuilt from the generation's
    own immutable bytes.
    """
    ledger = RawFactLedger.from_dict(
        _decode_json_object(generation.role_payloads["ledger_json"], field="ledger role")
    )
    filing_metadata = filing_metadata_from_role_payload(
        generation.role_payloads["filing_metadata_json"]
    )
    registry_payload = _decode_json_object(
        generation.role_payloads["registry_json"], field="registry role"
    )
    registry = registry_from_payload(registry_payload)
    entity_document = _decode_json_object(
        generation.role_payloads["entity_json"], field="entity role"
    )
    if entity_document.get("schema") != PRODUCTION_DATASET_ENTITY_SCHEMA:
        raise ProductionDatasetError("entity role is malformed")
    entity_raw = entity_document.get("entity")
    binding_raw = entity_document.get("binding")
    digests_raw = entity_document.get("evidence_digests")
    if not isinstance(entity_raw, dict) or not isinstance(binding_raw, dict) or not isinstance(digests_raw, dict):
        raise ProductionDatasetError("entity role is malformed")
    try:
        entity = EntityInput(
            entity_id=entity_raw["entity_id"],
            cik=entity_raw["cik"],
            ticker=entity_raw["ticker"],
            name=entity_raw["name"],
            identity_basis=entity_raw["identity_basis"],
            source_entity_id=entity_raw.get("source_entity_id"),
        )
        input_digests = PacketEvidenceDigests(
            filing_package_fixture_sha256=digests_raw.get("filing_package_fixture_sha256"),
            companyfacts_witness_sha256=digests_raw.get("companyfacts_witness_sha256"),
            submissions_witness_sha256=digests_raw.get("submissions_witness_sha256"),
        )
    except Exception as exc:  # noqa: BLE001
        raise ProductionDatasetError("entity role is malformed") from exc
    lineage = lineage_from_role_payload(generation.role_payloads["lineage_evidence_json"])
    return {
        "ledger": ledger,
        "filing_metadata": filing_metadata,
        "registry": registry,
        "entity": entity,
        "binding_document": binding_raw,
        "security_id": entity_document.get("security_id"),
        "listing_key": entity_document.get("listing_key"),
        "input_digests": input_digests,
        "lineage_evidence": lineage,
    }


# ---------------------------------------------------------------------------
# In-memory strict conditional store double (tests and local verification)
# ---------------------------------------------------------------------------


class InMemoryStrictConditionalStore:
    """A ``StrictConditionalWriteStore`` double with fault-injection hooks.

    Versions are opaque monotonically increasing tokens. ``put_bytes`` (the
    unconditional legacy write) is deliberately refused so any accidental
    fallback from the conditional-write law fails loudly in tests.
    """

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}
        self._versions: dict[str, int] = {}
        self._counter = 0
        self.conditional_writes: list[tuple[str, str | None]] = []
        self.unconditional_writes: list[str] = []
        # Fault hooks: set before the call you want to affect.
        self.raise_on_conditional_after_commit = False
        self.drop_after_commit = False
        self.false_on_conditional = False
        self.corrupt_keys: set[str] = set()

    # -- strict read protocol ------------------------------------------------
    def get_bytes(self, key: str) -> bytes | None:
        payload = self._objects.get(key)
        if payload is None:
            return None
        if key in self.corrupt_keys:
            return payload[:-1] if payload else b"\x00"
        return payload

    def get_bytes_strict(self, key: str) -> bytes | None:
        return self.get_bytes(key)

    def get_bytes_strict_bounded(self, key: str, maximum_bytes: int) -> bytes | None:
        payload = self.get_bytes(key)
        if payload is None:
            return None
        if len(payload) > maximum_bytes:
            raise RuntimeError("bounded read exceeded")
        return payload

    def get_bytes_strict_bounded_versioned(self, key: str, maximum_bytes: int):
        from engine.research_vault.r2_store import VersionedBytes  # noqa: PLC0415

        payload = self.get_bytes_strict_bounded(key, maximum_bytes)
        if payload is None:
            return VersionedBytes(data=None, version=None)
        return VersionedBytes(data=payload, version=f"v{self._versions[key]}")

    # -- conditional write protocol -------------------------------------------
    def validate_strict_conditional_write_capability(self) -> None:
        return None

    def put_bytes_strict_conditional(
        self,
        key: str,
        data: bytes,
        *,
        expected_version: str | None,
        content_type: str = "application/octet-stream",
    ) -> bool:
        del content_type
        self.conditional_writes.append((key, expected_version))
        current = self._versions.get(key)
        if expected_version is None:
            if current is not None:
                if self.false_on_conditional:
                    self.false_on_conditional = False
                    return False
                return False
        else:
            if current is None or f"v{current}" != expected_version:
                if self.false_on_conditional:
                    self.false_on_conditional = False
                    return False
                return False
        committed = self._commit(key, data)
        if self.raise_on_conditional_after_commit:
            self.raise_on_conditional_after_commit = False
            if self.drop_after_commit:
                self.drop(key)
            raise RuntimeError("transport failed after commit")
        return committed

    def _commit(self, key: str, data: bytes) -> bool:
        self._counter += 1
        self._objects[key] = bytes(data)
        self._versions[key] = self._counter
        return True

    # -- legacy store surface (refused for writes) ----------------------------
    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
        del data, content_type
        self.unconditional_writes.append(key)
        raise ProductionDatasetError(
            "in-memory production store refuses unconditional writes"
        )

    def list_prefix(self, prefix: str) -> list[str]:
        return sorted(key for key in self._objects if key.startswith(prefix))

    def exists(self, key: str) -> bool:
        return key in self._objects

    def upload_time(self, key: str) -> str | None:
        del key
        return None

    # -- test helpers ----------------------------------------------------------
    def raw_put(self, key: str, data: bytes) -> None:
        """Bypass the conditional protocol (hostile/legacy seeding for tests)."""
        self._counter += 1
        self._objects[key] = bytes(data)
        self._versions[key] = self._counter

    def drop(self, key: str) -> None:
        self._objects.pop(key, None)
        self._versions.pop(key, None)


__all__ = [
    "GENERATION_ID_RE",
    "InMemoryStrictConditionalStore",
    "LAWFUL_CAPTURE_BASES",
    "PRODUCTION_DATASET_ENTITY_SCHEMA",
    "PRODUCTION_DATASET_FILING_METADATA_SCHEMA",
    "PRODUCTION_DATASET_GENERATION_ID_PREFIX",
    "PRODUCTION_DATASET_POINTER_SCHEMA",
    "PRODUCTION_DATASET_PREFIX",
    "PRODUCTION_DATASET_PUBLICATION_CONTRACT",
    "PRODUCTION_DATASET_ROLES",
    "PRODUCTION_DATASET_SCHEMA",
    "PRODUCTION_DATASET_STATEMENT_INDEX_SCHEMA",
    "ProductionDatasetEffectUnknownError",
    "ProductionDatasetError",
    "ProductionDatasetGeneration",
    "ProductionDatasetMaterial",
    "ProductionDatasetModeError",
    "ProductionDatasetPublication",
    "build_production_dataset_store",
    "filing_metadata_from_role_payload",
    "latest_generation_summary",
    "lineage_from_role_payload",
    "load_generation",
    "load_latest_generation",
    "load_query_dataset_payloads",
    "production_latest_key",
    "production_manifest_key",
    "production_object_key",
    "publish_production_dataset",
    "registry_from_payload",
    "snapshot_core_registry_payload",
]
