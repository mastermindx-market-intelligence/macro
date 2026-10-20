"""Bounded accession-scope reads over one verified institutional 13F catalog.

Full quarter verification in ``engine.institutional_census.catalog`` downloads
and decodes every artifact of a generation, including all 64 holding buckets.
The current exact catalog holds 2,544,831 holdings across 7,258 filings and
7,000 manager relationships, so loading the whole generation is an unsuitable
interactive read for one authenticated reported-holding request.

``load_catalog_accession_scope`` reuses the owner's native manifest, pointer,
bounded-store, digest, Parquet, and JSON verification helpers to verify and
download only the artifacts one accession can reference: ``filings_parquet``
(all filing rows, retained for effective-filing lineage), the single
``holdings_bucket_*_parquet`` role the accession hashes to,
``manager_relationships_parquet``, ``source_receipts_json``, and
``coverage_json``.  The matching generation manifest still commits the full
descriptor/count set (the manifest class enforces that at decode), but this
reader verifies only the selected artifacts.

The result is a frozen :class:`VerifiedCatalogAccessionScope`, deliberately a
different type from ``PublishedCatalogGeneration``, which never claims that the
other 63 holding buckets or any other unselected artifact were verified.

Every failure fails closed with native catalog errors: a missing, malformed,
or unbound pointer, a missing or digest-mismatched selected object, a
generation invisible at the decision cutoff, and an interactive bound overflow
never degrade to absence or a fallback, and a scope is only returned after
every selected verification passes.  No writer, registry, credential, HTTP, or
raw-source access lives here: the caller's wrapper bounds aggregate source
bytes/calls/time, and the existing ``project_reported_holding`` raw-source
``cross_check_raw_receipt`` still owns the raw receipt check.
"""
from __future__ import annotations

import io
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any

from engine.research_vault.r2_store import StrictBoundedReadStore

from .catalog import (
    HARD_MAX_CATALOG_MANIFEST_BYTES,
    HARD_MAX_CATALOG_POINTER_BYTES,
    Institutional13FCatalogError,
    _ROLE_BYTE_LIMITS,
    _decode_json_artifacts,
    _decode_parquet,
    _read_required,
    holding_bucket_role,
)
from .models import (
    CATALOG_ARTIFACT_ROLES,
    CatalogGenerationManifest,
    CatalogPointer,
    Institutional13FError,
    catalog_manifest_key,
    catalog_pointer_key,
    normalize_accession,
    normalize_report_period,
    utc_datetime,
)
from .storage import Institutional13FStorageError, read_verified_object

SCOPE_VALIDATION = "accession_bucket"

# Interactive bounds apply to the artifacts this scope actually selects; they
# never apply to the whole-generation ``manifest.counts.holding_rows`` total,
# which stays committed by the manifest but is not verified here.
SCOPE_MAX_SELECTED_ROW_COUNT = 100_000
SCOPE_MAX_SELECTED_ARTIFACT_BYTES = 64 * 1024 * 1024
SCOPE_MAX_SELECTED_PARQUET_ROW_GROUP_BYTES = 128 * 1024 * 1024


class CatalogScopeNotAvailableAtCutoff(Institutional13FCatalogError):
    """The verified catalog generation was published after the decision cutoff."""


@dataclass(frozen=True)
class VerifiedCatalogAccessionScope:
    """Frozen verified-catalog rows for exactly one accession.

    Deliberately distinct from ``PublishedCatalogGeneration``: no payloads are
    retained, whole-generation verification is never claimed, and
    ``validated_roles`` names the only artifacts (at most one holding bucket of
    the 64) this scope proved.  ``filings`` intentionally keeps every filing
    row of the generation so the existing effective-filing lineage helpers keep
    their semantics; ``holdings`` and ``manager_relationships`` are narrowed to
    the accession itself.
    """

    manifest: CatalogGenerationManifest
    accession: str
    filings: tuple[Mapping[str, Any], ...]
    holdings: tuple[Mapping[str, Any], ...]
    manager_relationships: tuple[Mapping[str, Any], ...]
    validated_roles: tuple[str, ...]
    current_generation_id: str | None = None
    pointer_read: bool = False
    superseded: bool = False
    validation_scope: str = SCOPE_VALIDATION

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, CatalogGenerationManifest):
            raise Institutional13FCatalogError("accession scope manifest is invalid")
        object.__setattr__(self, "accession", normalize_accession(self.accession))
        # A pinned generation proves no fact about the current pointer. Only
        # pointer mode may populate this field; absence stays explicit.
        if self.superseded or self.current_generation_id not in {None, self.manifest.generation_id}:
            raise Institutional13FCatalogError("accession scope successor state is invalid")
        if type(self.pointer_read) is not bool or self.pointer_read != (self.current_generation_id is not None):
            raise Institutional13FCatalogError("accession scope pointer evidence is invalid")
        if self.validation_scope != SCOPE_VALIDATION:
            raise Institutional13FCatalogError("accession scope validation scope is invalid")
        roles = tuple(self.validated_roles)
        manifest_roles = {item.role for item in self.manifest.artifacts}
        if (
            not roles
            or len(set(roles)) != len(roles)
            or any(
                not isinstance(role, str) or role not in CATALOG_ARTIFACT_ROLES
                for role in roles
            )
            or not set(roles) <= manifest_roles
        ):
            raise Institutional13FCatalogError("accession scope validated roles are invalid")
        object.__setattr__(self, "validated_roles", roles)
        for name in ("filings", "holdings", "manager_relationships"):
            rows = getattr(self, name)
            if not isinstance(rows, tuple) or any(
                not isinstance(row, Mapping) for row in rows
            ):
                raise Institutional13FCatalogError(f"accession scope {name} rows are invalid")

    @property
    def generation_id(self) -> str:
        return self.manifest.generation_id


def _selected_roles(bucket_role: str) -> tuple[str, ...]:
    """The roles this scope verifies, in manifest artifact order."""
    return (
        "filings_parquet",
        bucket_role,
        "manager_relationships_parquet",
        "source_receipts_json",
        "coverage_json",
    )


def _read_bound_manifest(
    store: StrictBoundedReadStore,
    *,
    report_period: str,
    generation_id: str,
    pointer: CatalogPointer | None = None,
) -> CatalogGenerationManifest:
    """Read one exact manifest and bind it to its identity, period, and pointer."""
    key = catalog_manifest_key(report_period, generation_id)
    manifest_payload = _read_required(
        store, key, maximum_bytes=HARD_MAX_CATALOG_MANIFEST_BYTES
    )
    if pointer is not None and (
        len(manifest_payload) != pointer.manifest_byte_length
        or sha256(manifest_payload).hexdigest() != pointer.manifest_sha256
    ):
        raise Institutional13FCatalogError(
            "catalog pointer manifest hash or length is invalid"
        )
    try:
        # ``from_json_bytes`` re-derives the content-bound generation identity,
        # so a decoded manifest can only ever bind its own bytes.
        manifest = CatalogGenerationManifest.from_json_bytes(manifest_payload)
    except Institutional13FError as exc:
        raise Institutional13FCatalogError(f"catalog manifest is invalid for {key}") from exc
    if manifest.generation_id != generation_id or manifest.manifest_key != key:
        raise Institutional13FCatalogError("catalog manifest does not bind requested generation")
    if manifest.clocks.report_period != report_period:
        raise Institutional13FCatalogError("catalog manifest belongs to another report period")
    if pointer is not None and manifest.clocks.published_at != pointer.published_at:
        raise Institutional13FCatalogError("catalog pointer clock does not bind its manifest")
    return manifest


def _selected_row_group_bytes(role: str, payload: bytes) -> int:
    """Sum one downloaded Parquet payload's uncompressed row-group byte sizes."""
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - requirements pins pyarrow.
        raise Institutional13FCatalogError("pyarrow is required for 13F catalogs") from exc
    try:
        reader = pq.ParquetFile(io.BytesIO(payload))
        metadata = reader.metadata
        if metadata is None:
            raise Institutional13FCatalogError(f"{role} parquet metadata is missing")
        return sum(
            int(metadata.row_group(index).total_byte_size)
            for index in range(metadata.num_row_groups)
        )
    except Institutional13FCatalogError:
        raise
    except Exception as exc:
        raise Institutional13FCatalogError(
            f"could not inspect {role} parquet row groups"
        ) from exc


def load_catalog_accession_scope(
    store: StrictBoundedReadStore,
    *,
    report_period: str,
    accession: str,
    generation_id: str | None = None,
    decision_cutoff: str | datetime,
) -> VerifiedCatalogAccessionScope:
    """Verify and download only the catalog artifacts one accession needs.

    Explicit ``generation_id`` reads exactly that manifest and never touches
    the quarter pointer; pointer mode decodes the exact pointer and proves its
    manifest length, digest, publication clock, period, and generation binding
    before any artifact read.  A generation published after the aware UTC
    ``decision_cutoff`` raises :class:`CatalogScopeNotAvailableAtCutoff` before
    any artifact download.  Selected artifacts are digest-verified through the
    owner's per-role ceilings, bounded interactively (per-artifact row counts,
    summed artifact bytes, summed Parquet row-group bytes), decoded with the
    owner's decoders, and cross-checked for bucket membership, filing lineage,
    and receipt provenance before any scope is returned.
    """
    if not isinstance(store, StrictBoundedReadStore):
        raise Institutional13FCatalogError(
            "catalog accession scope requires a StrictBoundedReadStore"
        )
    period = normalize_report_period(report_period)
    target = normalize_accession(accession)
    cutoff = utc_datetime(decision_cutoff, field="decision_cutoff")
    bucket_role = holding_bucket_role(target)
    roles = _selected_roles(bucket_role)

    pointer = None
    if generation_id is not None:
        manifest = _read_bound_manifest(
            store, report_period=period, generation_id=generation_id
        )
    else:
        pointer_payload = _read_required(
            store, catalog_pointer_key(period), maximum_bytes=HARD_MAX_CATALOG_POINTER_BYTES
        )
        pointer = CatalogPointer.from_json_bytes(pointer_payload)
        if pointer.report_period != period:
            raise Institutional13FCatalogError(
                "catalog pointer belongs to another report period"
            )
        manifest = _read_bound_manifest(
            store, report_period=period, generation_id=pointer.generation_id, pointer=pointer
        )

    published_at = utc_datetime(str(manifest.clocks.published_at), field="published_at")
    if published_at > cutoff:
        raise CatalogScopeNotAvailableAtCutoff(
            f"catalog generation {manifest.generation_id} published_at "
            f"{published_at.isoformat()} is after the decision cutoff {cutoff.isoformat()}"
        )

    descriptors = {item.role: item for item in manifest.artifacts}
    selected = tuple(descriptors[role] for role in roles)
    for descriptor in selected:
        if (
            descriptor.row_count is not None
            and descriptor.row_count > SCOPE_MAX_SELECTED_ROW_COUNT
        ):
            raise Institutional13FCatalogError(
                f"catalog accession scope artifact {descriptor.role} exceeds the "
                f"interactive row bound ({descriptor.row_count} > "
                f"{SCOPE_MAX_SELECTED_ROW_COUNT})"
            )
    selected_bytes = sum(descriptor.byte_length for descriptor in selected)
    if selected_bytes > SCOPE_MAX_SELECTED_ARTIFACT_BYTES:
        raise Institutional13FCatalogError(
            f"catalog accession scope selected artifacts exceed the interactive "
            f"byte bound ({selected_bytes} > {SCOPE_MAX_SELECTED_ARTIFACT_BYTES})"
        )

    payloads: dict[str, bytes] = {}
    for descriptor in selected:
        try:
            payloads[descriptor.role] = read_verified_object(
                store, descriptor, maximum_bytes=_ROLE_BYTE_LIMITS[descriptor.role]
            )
        except Institutional13FStorageError as exc:
            raise Institutional13FCatalogError(str(exc)) from exc

    # Inspect row-group metadata only (no column decode) and bound the total
    # uncompressed Parquet size before any selected Parquet is decoded.
    row_group_bytes = sum(
        _selected_row_group_bytes(role, payloads[role])
        for role in roles
        if role.endswith("_parquet")
    )
    if row_group_bytes > SCOPE_MAX_SELECTED_PARQUET_ROW_GROUP_BYTES:
        raise Institutional13FCatalogError(
            f"catalog accession scope selected parquet row groups exceed the "
            f"interactive row-group byte bound ({row_group_bytes} > "
            f"{SCOPE_MAX_SELECTED_PARQUET_ROW_GROUP_BYTES})"
        )

    filings = _decode_parquet(
        "filings_parquet",
        payloads["filings_parquet"],
        expected_rows=manifest.counts.filing_rows,
        report_period=period,
    )
    bucket_rows = _decode_parquet(
        bucket_role,
        payloads[bucket_role],
        expected_rows=descriptors[bucket_role].row_count or 0,
        report_period=period,
    )
    if any(holding_bucket_role(str(item["accession"])) != bucket_role for item in bucket_rows):
        raise Institutional13FCatalogError("holding row is stored in the wrong bucket")
    managers = _decode_parquet(
        "manager_relationships_parquet",
        payloads["manager_relationships_parquet"],
        expected_rows=manifest.counts.manager_relationship_rows,
        report_period=period,
    )
    receipts = _decode_json_artifacts(
        report_period=period,
        source_payload=payloads["source_receipts_json"],
        coverage_payload=payloads["coverage_json"],
        expected_receipts=manifest.counts.source_receipts,
    )
    if {str(item["source_receipt_id"]) for item in filings} != set(receipts):
        raise Institutional13FCatalogError("catalog filing provenance does not match receipts")
    filing_accessions = {str(item["accession"]) for item in filings}
    if any(str(item["accession"]) not in filing_accessions for item in bucket_rows):
        raise Institutional13FCatalogError("catalog holding row has no filing")
    if any(str(item["accession"]) not in filing_accessions for item in managers):
        raise Institutional13FCatalogError("catalog manager relationship row has no filing")

    return VerifiedCatalogAccessionScope(
        manifest=manifest,
        accession=target,
        filings=filings,
        holdings=tuple(item for item in bucket_rows if str(item["accession"]) == target),
        manager_relationships=tuple(
            item for item in managers if str(item["accession"]) == target
        ),
        validated_roles=roles,
        current_generation_id=pointer.generation_id if pointer is not None else None,
        pointer_read=pointer is not None,
        superseded=False,
    )
