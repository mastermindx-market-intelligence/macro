"""Read an existing identity generation without inventing publication or clocks.

This is the Entry Radar file/Parquet adapter to ``lib.dataos.identity``. Identity
selection and generation validation remain with that owner. Nothing here writes
files, acquires source data, starts a collector, or authorizes a trading signal.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import stat
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from lib.dataos.identity import (
    IdentityError,
    ReferenceReadReceipt,
    ReferenceSnapshot,
    VendorAliasTable,
    _ob_load,
    validate_reference_snapshot,
)

REFERENCE_ARTIFACTS = (
    "security_master.parquet", "vendor_aliases.parquet", "issuer_master.parquet",
    "issuer_migrations.parquet", "security_migrations.parquet",
)
_MIB = 1024 * 1024
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_DAY_NS = 86_400 * 1_000_000_000


@dataclass(frozen=True, slots=True)
class IdentitySnapshotRead:
    """Actual read evidence; hashes are consistency seals, not authentication."""

    snapshot: ReferenceSnapshot
    receipt: ReferenceReadReceipt

    def alias_table(self) -> VendorAliasTable:
        """Use the native selector; its query still requires an explicit receipt."""
        context = json.loads(self.snapshot.receipt_bytes)
        return VendorAliasTable.from_records(
            json.loads(self.snapshot.alias_json),
            observation_history=context["identity_observations"],
            original_reference=context["prospective_reference"],
            snapshot_contexts=(self.snapshot,),
        )


@dataclass(frozen=True, slots=True)
class LegacyReferenceRead:
    """Complete captured LEGACY bytes; no native proof or availability clock."""

    receipt_bytes: bytes
    artifact_bytes: tuple[tuple[str, bytes], ...]
    mode: str = "LEGACY"

    def records(self, name: str) -> list[dict[str, Any]]:
        """Decode only immutable captured bytes, never reopen a latest path."""
        if name not in REFERENCE_ARTIFACTS:
            raise IdentityError("identity snapshot: unknown reference member")
        return _parquet_records(dict(self.artifact_bytes)[name], name)


def _clock(value: int) -> int:
    if type(value) is not int or not 0 < value <= 2**63 - 1:
        raise IdentityError("identity snapshot: invalid actual read clock")
    return value


def _stat_identity(value: os.stat_result) -> tuple[int, ...]:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _read_file(directory_fd: int, name: str, limit: int) -> bytes:
    """Read one regular, bounded file relative to the already-open directory."""
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(name, flags, dir_fd=directory_fd)
    except OSError as exc:
        raise IdentityError(f"identity snapshot file unavailable: {name}") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise IdentityError(f"identity snapshot requires a regular file: {name}")
        if not 0 < before.st_size <= limit:
            raise IdentityError(f"identity snapshot file byte bound: {name}")
        chunks, size = [], 0
        while size <= limit:
            chunk = os.read(fd, min(128 * 1024, limit + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            chunks.append(chunk)
        after = os.fstat(fd)
        if size > limit:
            raise IdentityError(f"identity snapshot file byte bound: {name}")
        if _stat_identity(before) != _stat_identity(after) or size != before.st_size:
            raise IdentityError(f"identity snapshot file changed during read: {name}")
        return b"".join(chunks)
    except OSError as exc:
        raise IdentityError(f"identity snapshot file unavailable: {name}") from exc
    finally:
        os.close(fd)


def _timestamp(scalar: Any, column: str) -> str:
    """Keep integer nanoseconds; do not depend on pandas-backed ``as_py``."""
    unit = scalar.type.unit
    scale = {"s": 1_000_000_000, "ms": 1_000_000, "us": 1_000, "ns": 1}.get(unit)
    if scale is None:
        raise IdentityError("identity snapshot: unsupported timestamp unit")
    ns = scalar.value * scale
    zone = scalar.type.tz
    if column in {"valid_from", "valid_to"}:
        if zone not in (None, "UTC", "Etc/UTC") or ns % _DAY_NS:
            raise IdentityError("identity snapshot: validity requires date-only midnight storage")
        try:
            return (_EPOCH + timedelta(days=ns // _DAY_NS)).date().isoformat()
        except (OverflowError, ValueError) as exc:
            raise IdentityError("identity snapshot: date-only storage out of range") from exc
    if column == "known_at" and zone is None:
        raise IdentityError("identity snapshot: known_at timestamp requires a timezone")
    seconds, remainder = divmod(ns, 1_000_000_000)
    try:
        wall = _EPOCH + timedelta(seconds=seconds)
    except (OverflowError, ValueError) as exc:
        raise IdentityError("identity snapshot: timestamp out of range") from exc
    suffix = "Z" if zone is not None else ""
    return wall.strftime("%Y-%m-%dT%H:%M:%S") + f".{remainder:09d}" + suffix


def _scalar(scalar: Any, column: str, arrow: Any) -> Any:
    if not scalar.is_valid:
        return None
    if arrow.types.is_timestamp(scalar.type):
        return _timestamp(scalar, column)
    if arrow.types.is_date(scalar.type):
        return scalar.as_py().isoformat()
    value = scalar.as_py()
    if type(value) not in (str, int, float, bool):
        raise IdentityError(f"identity snapshot: unsupported Parquet scalar in {column}")
    if isinstance(value, float) and not math.isfinite(value):
        raise IdentityError(f"identity snapshot: nonfinite Parquet value in {column}")
    if type(value) is str and len(value.encode("utf-8")) > 262_144:
        raise IdentityError(f"identity snapshot: Parquet string bound in {column}")
    return value


def _parquet_records(raw: bytes, name: str) -> list[dict[str, Any]]:
    # Lazy import keeps the identity owner and unrelated thin test lanes pure.
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise IdentityError("identity snapshot: Parquet dependency unavailable") from exc
    try:
        with pq.ParquetFile(
            pa.BufferReader(raw), pre_buffer=False,
            thrift_string_size_limit=8 * _MIB, thrift_container_size_limit=100_000,
        ) as source:
            metadata, schema = source.metadata, source.schema_arrow
            names = schema.names
            if len(names) > 128 or len(set(names)) != len(names) or any(not n for n in names):
                raise IdentityError(f"identity snapshot: invalid Parquet columns in {name}")
            if metadata.num_rows > 100_000:
                raise IdentityError(f"identity snapshot: Parquet row bound in {name}")
            uncompressed = sum(metadata.row_group(i).total_byte_size for i in range(metadata.num_row_groups))
            if uncompressed > 64 * _MIB:
                raise IdentityError(f"identity snapshot: Parquet decoded byte bound in {name}")
            for field in schema:
                typ = field.type
                if not (pa.types.is_string(typ) or pa.types.is_large_string(typ)
                        or pa.types.is_integer(typ) or pa.types.is_floating(typ)
                        or pa.types.is_boolean(typ) or pa.types.is_null(typ)
                        or pa.types.is_timestamp(typ) or pa.types.is_date(typ)):
                    raise IdentityError(f"identity snapshot: unsupported Parquet column {field.name}")
            rows, encoded_size, decoded_size = [], 2, 0
            for batch in source.iter_batches(batch_size=1024, use_threads=False, use_pandas_metadata=False):
                decoded_size += batch.nbytes
                if decoded_size > 64 * _MIB:
                    raise IdentityError(f"identity snapshot: Parquet decoded byte bound in {name}")
                for i in range(batch.num_rows):
                    row = {column: _scalar(batch.column(j)[i], column, pa)
                           for j, column in enumerate(names)}
                    wire = json.dumps(row, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=True, allow_nan=False).encode()
                    if len(wire) > 8 * _MIB:
                        raise IdentityError(f"identity snapshot: Parquet record byte bound in {name}")
                    encoded_size += len(wire) + (1 if rows else 0)
                    if len(rows) >= 100_000 or encoded_size > 64 * _MIB:
                        raise IdentityError(f"identity snapshot: Parquet record-set bound in {name}")
                    rows.append(row)
            if len(rows) != metadata.num_rows:
                raise IdentityError(f"identity snapshot: Parquet row count mismatch in {name}")
            return rows
    except IdentityError:
        raise
    except (pa.ArrowException, OSError, ValueError, TypeError, OverflowError) as exc:
        raise IdentityError(f"identity snapshot: unreadable Parquet {name}") from exc


def _read_reference_bytes(directory: str | Path, *, legacy: bool = False):
    """Capture existing bytes; only the LEGACY seam adds cooperative root SH.

    Native acquisition preserves its incumbent behavior, including writer-owned
    EX readback. LEGACY assumes local POSIX flock and cooperating participants;
    it does not fence old/noncooperating writers, other hosts or Git publication.
    """
    if not isinstance(directory, (str, Path)):
        raise IdentityError("identity snapshot: an absolute local directory is required")
    root = Path(directory)
    if not root.is_absolute() or ".." in root.parts:
        raise IdentityError("identity snapshot: an absolute local directory is required")
    if legacy:
        try:
            import fcntl
        except ImportError as exc:
            raise IdentityError("identity snapshot locking unsupported on this host") from exc
    try:
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                     | getattr(os, "O_CLOEXEC", 0))
    except OSError as exc:
        raise IdentityError("identity snapshot directory unavailable") from exc
    try:
        if legacy:
            try:
                fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise IdentityError("identity snapshot writer busy") from exc
        held = os.fstat(fd)
        def check_target():
            now = os.stat(root, follow_symlinks=False)
            if not stat.S_ISDIR(now.st_mode) or (now.st_dev, now.st_ino) != (held.st_dev, held.st_ino):
                raise IdentityError("identity snapshot directory changed during read")
        check_target()
        if legacy:
            try:
                os.stat(".identity", dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise IdentityError("identity snapshot native layout requires native acquisition")
        receipt_before = _read_file(fd, "_receipt.json", 9 * _MIB)
        artifacts = {name: _read_file(fd, name, 64 * _MIB) for name in REFERENCE_ARTIFACTS}
        receipt_after = _read_file(fd, "_receipt.json", 9 * _MIB)
        check_target()
        if receipt_before != receipt_after:
            raise IdentityError("identity observations: receipt changed during read")
    except OSError as exc:
        raise IdentityError("identity snapshot directory/locking unavailable") from exc
    finally:
        os.close(fd)
    return receipt_before, artifacts


def read_reference_generation(directory: str | Path) -> LegacyReferenceRead:
    """Capture the complete legacy root under SH; native mode has no fallback.

    Trusted local configuration only. A prospective legacy probe alone grants
    no native identity proof. Native publication/history or layout requires the
    separately qualified native reader; this API never creates a read receipt.
    """
    receipt, artifacts = _read_reference_bytes(directory, legacy=True)
    context = _ob_load(receipt, 9 * _MIB)
    if type(context) is not dict:
        raise IdentityError("identity snapshot: legacy receipt object required")
    if {"publication", "identity_observations"} & context.keys():
        raise IdentityError("identity snapshot native context requires native acquisition")
    return LegacyReferenceRead(receipt, tuple((name, artifacts[name]) for name in REFERENCE_ARTIFACTS))


def read_identity_snapshot(directory: str | Path) -> IdentitySnapshotRead:
    """Read one existing generation at the actual completion clock, without I/O writes.

    ``directory`` is a trusted local configuration, not a customer-controlled path.
    No supplied cutoff or filesystem timestamp can become a read-availability clock.
    A native validation error creates no read receipt and no legacy fallback.
    """
    started = _clock(time.time_ns())
    receipt_before, artifacts = _read_reference_bytes(directory)
    aliases = _parquet_records(artifacts["vendor_aliases.parquet"], "vendor_aliases.parquet")
    master = _parquet_records(artifacts["security_master.parquet"], "security_master.parquet")
    snapshot = validate_reference_snapshot(receipt_before, artifacts, receipt_before,
                                          alias_records=aliases, master_records=master)
    completed = _clock(time.time_ns())
    if started > completed:
        raise IdentityError("identity snapshot: actual read clock moved backwards")
    context = json.loads(snapshot.receipt_bytes)
    history, publication = context["identity_observations"], context["publication"]
    last = history["attempts"][-1] if history["attempts"] else history["anchor"]
    if completed < int(last["owner_read_completed_at_utc_ns"]):
        raise IdentityError("identity snapshot: consumer read precedes owner observation")
    receipt = ReferenceReadReceipt.from_record({
        "schema": "mastermind.identity_read_receipt.v1",
        "receipt_sha256": hashlib.sha256(snapshot.receipt_bytes).hexdigest(),
        "generation_id": publication["generation_id"],
        "artifact_sha256": {name: publication["artifacts"][name]["sha256"]
                            for name in REFERENCE_ARTIFACTS},
        "history_prefix_sha256": publication["history_sha256"],
        "read_started_at_utc_ns": str(started),
        "read_completed_at_utc_ns": str(completed),
    })
    return IdentitySnapshotRead(snapshot, receipt)
