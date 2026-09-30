"""Inactive, bounded primitives for the Options Context Audit v2.

This module is intentionally a preparation layer.  It scans immutable JSONL
sources, builds deterministic sort runs, and validates a source manifest.  It
does not resolve Market Memory, write a trusted context, publish a receipt, or
wire itself into the v1 engine, auditor, service, or timer.

The scanner hashes the bytes it actually read and compares file identity and
size before and after the read.  A source changing during a scan therefore
fails closed instead of producing a plausible partial audit.  The run helpers
keep only a bounded batch in memory and merge canonical JSONL runs in key
order.
"""

from __future__ import annotations

import hashlib
import heapq
import json
import os
import tempfile
import string
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


SCHEMA = "options.market_memory_context_audit/v2"
DEFAULT_KEY_FIELDS = ("schema", "id")
_SHA256_LENGTH = 64


class RefusalCode(str, Enum):
    """Machine-readable reasons an audit preparation must refuse."""

    SOURCE_MANIFEST_INCOMPLETE = "SOURCE_MANIFEST_INCOMPLETE"
    SOURCE_SNAPSHOT_UNSTABLE = "SOURCE_SNAPSHOT_UNSTABLE"
    SOURCE_MUTATED = "SOURCE_MUTATED"
    MALFORMED_ROW = "MALFORMED_ROW"
    PREFIX_MISMATCH = "PREFIX_MISMATCH"
    CHECKPOINT_STALE = "CHECKPOINT_STALE"
    CAMPAIGN_OUTPUT_STALE = "CAMPAIGN_OUTPUT_STALE"
    DERIVATION_PENDING = "DERIVATION_PENDING"
    CAMPAIGN_REPLAY_MISMATCH = "CAMPAIGN_REPLAY_MISMATCH"
    OWNER_MISSING = "OWNER_MISSING"
    DUPLICATE_OWNER_CONFLICT = "DUPLICATE_OWNER_CONFLICT"
    CORRECTION_LINEAGE_MISSING = "CORRECTION_LINEAGE_MISSING"
    DEPENDENCY_MISMATCH = "DEPENDENCY_MISMATCH"
    BOUNDARY_INVALID = "BOUNDARY_INVALID"
    NONDETERMINISTIC_OUTPUT = "NONDETERMINISTIC_OUTPUT"
    REPLAY_MISMATCH = "REPLAY_MISMATCH"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    RECEIPT_OVERFLOW = "RECEIPT_OVERFLOW"
    AUTHORITY_VIOLATION = "AUTHORITY_VIOLATION"


@dataclass(frozen=True)
class Refusal:
    """Typed, serializable refusal payload returned by bounded operations."""

    code: RefusalCode
    message: str
    path: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "path": self.path,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class FileIdentity:
    """The stable file attributes checked around one read."""

    device: int
    inode: int
    size: int
    mtime_ns: int

    @classmethod
    def from_stat(cls, stat: os.stat_result) -> "FileIdentity":
        return cls(stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


@dataclass(frozen=True)
class SourceSpec:
    """A declared source or explicit exclusion in the audit manifest."""

    path: Path | str
    role: str
    consumed: bool = True
    exclusion_reason: str | None = None
    expected_sha256: str | None = None
    expected_bytes: int | None = None
    expected_rows: int | None = None
    key_fields: tuple[str, ...] = DEFAULT_KEY_FIELDS

    def __post_init__(self) -> None:
        path = Path(self.path)
        if not self.role.strip():
            raise ValueError("source role must be non-empty")
        if self.consumed and self.exclusion_reason is not None:
            raise ValueError("consumed source cannot have an exclusion reason")
        if not self.consumed and not (self.exclusion_reason or "").strip():
            raise ValueError("excluded source requires an exclusion reason")
        if not self.key_fields:
            raise ValueError("source key_fields must be non-empty")
        if self.expected_sha256 is not None and (
            len(self.expected_sha256) != _SHA256_LENGTH
            or any(char not in string.hexdigits for char in self.expected_sha256)
        ):
            raise ValueError("expected_sha256 must be a 64-character hexadecimal digest")
        object.__setattr__(self, "path", path)


@dataclass(frozen=True)
class SourceManifest:
    """Explicit consumed and excluded source declarations.

    Excluded paths are carried in the manifest even though they are not read;
    this makes adjacent ledgers visible to a reviewer and prevents accidental
    omission from being mistaken for an empty source.
    """

    consumed: tuple[SourceSpec, ...]
    excluded: tuple[SourceSpec, ...] = ()

    def __post_init__(self) -> None:
        consumed = tuple(self.consumed)
        excluded = tuple(self.excluded)
        if not consumed:
            raise ValueError("manifest must declare at least one consumed source")
        seen: dict[Path, bool] = {}
        for spec in (*consumed, *excluded):
            if spec.consumed is not (spec in consumed):
                raise ValueError("source consumed flag disagrees with manifest section")
            if spec.path in seen:
                raise ValueError(f"source appears more than once: {spec.path}")
            seen[spec.path] = True
        object.__setattr__(self, "consumed", consumed)
        object.__setattr__(self, "excluded", excluded)


@dataclass(frozen=True)
class SourceSnapshot:
    """Observed immutable source facts from one complete scan."""

    path: Path
    role: str
    sha256: str
    bytes: int
    rows: int
    identity_before: FileIdentity
    identity_after: FileIdentity

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path.as_posix(),
            "role": self.role,
            "sha256": self.sha256,
            "bytes": self.bytes,
            "rows": self.rows,
            "identity_before": self.identity_before.__dict__,
            "identity_after": self.identity_after.__dict__,
        }


@dataclass(frozen=True)
class ScanOutcome:
    snapshot: SourceSnapshot | None = None
    refusal: Refusal | None = None

    @property
    def accepted(self) -> bool:
        return self.snapshot is not None and self.refusal is None


@dataclass(frozen=True)
class AuditPlan:
    """Deterministic preparation output; it has no trusted-context authority."""

    schema: str
    snapshots: tuple[SourceSnapshot, ...]
    excluded: tuple[dict[str, str], ...]
    run_paths: tuple[Path, ...]
    row_count: int
    stream_sha256: str
    trusted_context: bool = False
    published: bool = False


def _canonical_bytes(row: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            row,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("row is not canonical JSON") from exc


def _row_key(row: Mapping[str, Any], key_fields: Sequence[str]) -> tuple[str, ...]:
    values: list[str] = []
    for field_name in key_fields:
        value = row.get(field_name)
        if not isinstance(value, (str, int, float, bool)) or value is None:
            raise KeyError(field_name)
        values.append(str(value))
    return tuple(values)


def canonical_stream_hash(rows: Iterable[Mapping[str, Any]]) -> tuple[str, int, int]:
    """Hash canonical JSONL rows without materializing the stream."""

    digest = hashlib.sha256()
    count = 0
    size = 0
    for row in rows:
        body = _canonical_bytes(row) + b"\n"
        digest.update(body)
        count += 1
        size += len(body)
    return digest.hexdigest(), count, size


def scan_jsonl(
    spec: SourceSpec,
    on_row: Callable[[Mapping[str, Any]], None] | None = None,
) -> ScanOutcome:
    """Stream one JSONL source and fail closed if it changes while read."""

    path = Path(spec.path)
    try:
        before = FileIdentity.from_stat(path.stat())
    except OSError as exc:
        return ScanOutcome(refusal=Refusal(RefusalCode.SOURCE_SNAPSHOT_UNSTABLE, str(exc), path.as_posix()))
    digest = hashlib.sha256()
    rows = 0
    try:
        with path.open("rb") as source:
            for line_number, line in enumerate(source, 1):
                digest.update(line)
                if not line.strip():
                    continue
                try:
                    row = json.loads(line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    return ScanOutcome(refusal=Refusal(RefusalCode.MALFORMED_ROW, f"invalid JSONL row: {exc}", path.as_posix(), {"line": line_number}))
                if not isinstance(row, Mapping):
                    return ScanOutcome(refusal=Refusal(RefusalCode.MALFORMED_ROW, "JSONL row must be an object", path.as_posix(), {"line": line_number}))
                try:
                    _canonical_bytes(row)
                except ValueError as exc:
                    return ScanOutcome(refusal=Refusal(RefusalCode.MALFORMED_ROW, str(exc), path.as_posix(), {"line": line_number}))
                rows += 1
                if on_row is not None:
                    on_row(row)
        after = FileIdentity.from_stat(path.stat())
    except OSError as exc:
        return ScanOutcome(refusal=Refusal(RefusalCode.SOURCE_SNAPSHOT_UNSTABLE, str(exc), path.as_posix()))
    if before != after or after.size != before.size:
        return ScanOutcome(refusal=Refusal(RefusalCode.SOURCE_MUTATED, "source identity changed during scan", path.as_posix(), {"before": before.__dict__, "after": after.__dict__}))
    sha256 = digest.hexdigest()
    if spec.expected_sha256 is not None and sha256 != spec.expected_sha256:
        return ScanOutcome(refusal=Refusal(RefusalCode.PREFIX_MISMATCH, "source digest differs from manifest", path.as_posix(), {"expected": spec.expected_sha256, "actual": sha256}))
    if spec.expected_bytes is not None and after.size != spec.expected_bytes:
        return ScanOutcome(refusal=Refusal(RefusalCode.PREFIX_MISMATCH, "source byte count differs from manifest", path.as_posix(), {"expected": spec.expected_bytes, "actual": after.size}))
    if spec.expected_rows is not None and rows != spec.expected_rows:
        return ScanOutcome(refusal=Refusal(RefusalCode.PREFIX_MISMATCH, "source row count differs from manifest", path.as_posix(), {"expected": spec.expected_rows, "actual": rows}))
    return ScanOutcome(snapshot=SourceSnapshot(path, spec.role, sha256, after.size, rows, before, after))


def write_sorted_runs(
    rows: Iterable[Mapping[str, Any]],
    directory: Path,
    *,
    key_fields: Sequence[str] = DEFAULT_KEY_FIELDS,
    max_rows: int = 1024,
) -> tuple[Path, ...]:
    """Write bounded canonical JSONL runs sorted by identity then row bytes."""

    if max_rows < 1:
        raise ValueError("max_rows must be positive")
    directory.mkdir(parents=True, exist_ok=True)
    runs: list[Path] = []
    batch: list[tuple[tuple[str, ...], bytes]] = []

    def flush() -> None:
        if not batch:
            return
        batch.sort(key=lambda item: (item[0], item[1]))
        path = directory / f"run-{len(runs):08d}.jsonl"
        with path.open("wb") as output:
            for _, body in batch:
                output.write(body)
                output.write(b"\n")
        runs.append(path)
        batch.clear()

    for row in rows:
        try:
            key = _row_key(row, key_fields)
            body = _canonical_bytes(row)
        except (KeyError, ValueError) as exc:
            raise ValueError(f"row missing canonical key or is malformed: {exc}") from exc
        batch.append((key, body))
        if len(batch) >= max_rows:
            flush()
    flush()
    return tuple(runs)


class _RunAccumulator:
    """Small bounded buffer used by the source scanner."""

    def __init__(self, directory: Path, *, prefix: str, key_fields: Sequence[str], max_rows: int) -> None:
        self.directory = directory
        self.prefix = prefix
        self.key_fields = tuple(key_fields)
        self.max_rows = max_rows
        self.batch: list[tuple[tuple[str, ...], bytes]] = []
        self.paths: list[Path] = []

    def add(self, row: Mapping[str, Any]) -> None:
        self.batch.append((_row_key(row, self.key_fields), _canonical_bytes(row)))
        if len(self.batch) >= self.max_rows:
            self.flush()

    def flush(self) -> None:
        if not self.batch:
            return
        self.batch.sort(key=lambda item: (item[0], item[1]))
        path = self.directory / f"{self.prefix}-{len(self.paths):08d}.jsonl"
        with path.open("wb") as output:
            for _, body in self.batch:
                output.write(body)
                output.write(b"\n")
        self.paths.append(path)
        self.batch.clear()

    def finish(self) -> tuple[Path, ...]:
        self.flush()
        return tuple(self.paths)


def merge_sorted_runs(
    paths: Sequence[Path],
    *,
    key_fields: Sequence[str] = DEFAULT_KEY_FIELDS,
) -> Iterator[Mapping[str, Any]]:
    """Yield rows from canonical runs in deterministic key/byte order."""

    streams: list[Any] = []
    heap: list[tuple[tuple[str, ...], bytes, int, Mapping[str, Any]]] = []
    try:
        for index, path in enumerate(paths):
            stream = Path(path).open("rb")
            streams.append(stream)
            line = stream.readline()
            if line:
                row = json.loads(line)
                body = _canonical_bytes(row)
                heapq.heappush(heap, (_row_key(row, key_fields), body, index, row))
        while heap:
            _, _, index, row = heapq.heappop(heap)
            yield row
            line = streams[index].readline()
            if line:
                next_row = json.loads(line)
                body = _canonical_bytes(next_row)
                heapq.heappush(heap, (_row_key(next_row, key_fields), body, index, next_row))
    finally:
        for stream in streams:
            stream.close()


def build_audit_plan(
    manifest: SourceManifest,
    run_directory: Path | None = None,
    *,
    max_rows_per_run: int = 1024,
) -> AuditPlan | Refusal:
    """Prepare deterministic bounded runs and reject duplicate owner identities.

    The scanner feeds a bounded accumulator directly; it never materializes a
    complete source ledger. Runs created by a refused operation are removed,
    while an explicitly supplied directory retains only files that existed
    before this call. The returned plan is inert and cannot publish context.
    """

    if max_rows_per_run < 1:
        return Refusal(RefusalCode.RESOURCE_LIMIT, "max_rows_per_run must be positive")
    owned_directory = run_directory is None
    directory = (
        Path(tempfile.mkdtemp(prefix="options-context-v2-"))
        if owned_directory
        else Path(run_directory)
    )
    directory.mkdir(parents=True, exist_ok=True)
    initial_runs = set(directory.glob("source-*.jsonl"))
    snapshots: list[SourceSnapshot] = []
    runs: list[Path] = []
    result: AuditPlan | Refusal | None = None
    try:
        for source_index, spec in enumerate(manifest.consumed):
            writer = _RunAccumulator(
                directory,
                prefix=f"source-{source_index:08d}",
                key_fields=spec.key_fields,
                max_rows=max_rows_per_run,
            )

            def consume(
                row: Mapping[str, Any], *, spec: SourceSpec = spec
            ) -> None:
                try:
                    _row_key(row, spec.key_fields)
                    writer.add(row)
                except (KeyError, ValueError) as exc:
                    raise ValueError(f"malformed owner row: {exc}") from exc

            try:
                outcome = scan_jsonl(spec, consume)
            except ValueError as exc:
                result = Refusal(
                    RefusalCode.MALFORMED_ROW, str(exc), spec.path.as_posix()
                )
                break
            if outcome.refusal is not None:
                result = outcome.refusal
                break
            assert outcome.snapshot is not None
            snapshots.append(outcome.snapshot)
            runs.extend(writer.finish())
        else:
            merged = merge_sorted_runs(runs)
            digest = hashlib.sha256()
            row_count = 0
            previous_key: tuple[str, ...] | None = None
            for row in merged:
                try:
                    key = _row_key(row, DEFAULT_KEY_FIELDS)
                except KeyError as exc:
                    result = Refusal(
                        RefusalCode.MALFORMED_ROW,
                        f"missing owner key {exc.args[0]}",
                    )
                    break
                if key == previous_key:
                    result = Refusal(
                        RefusalCode.DUPLICATE_OWNER_CONFLICT,
                        "duplicate owner identity",
                        details={"key": list(key)},
                    )
                    break
                previous_key = key
                body = _canonical_bytes(row) + b"\n"
                digest.update(body)
                row_count += 1
            else:
                result = AuditPlan(
                    SCHEMA,
                    tuple(snapshots),
                    tuple(
                        {
                            "path": spec.path.as_posix(),
                            "role": spec.role,
                            "reason": spec.exclusion_reason or "",
                        }
                        for spec in manifest.excluded
                    ),
                    tuple(runs),
                    row_count,
                    digest.hexdigest(),
                )
    finally:
        if result is None or isinstance(result, Refusal):
            for path in set(directory.glob("source-*.jsonl")) - initial_runs:
                path.unlink(missing_ok=True)
        if owned_directory:
            for path in directory.iterdir():
                if path.is_file():
                    path.unlink(missing_ok=True)
            directory.rmdir()
    assert result is not None
    return result


def validate_audit_plan(plan: AuditPlan) -> Refusal | None:
    """Validate the inert plan without granting context or publication authority."""

    if plan.schema != SCHEMA:
        return Refusal(RefusalCode.BOUNDARY_INVALID, "unsupported audit plan schema")
    if plan.trusted_context or plan.published:
        return Refusal(RefusalCode.AUTHORITY_VIOLATION, "v2 preparation cannot publish trusted context")
    if len(plan.stream_sha256) != _SHA256_LENGTH:
        return Refusal(RefusalCode.NONDETERMINISTIC_OUTPUT, "stream digest is not sha256")
    return None


__all__ = [
    "AuditPlan",
    "DEFAULT_KEY_FIELDS",
    "FileIdentity",
    "Refusal",
    "RefusalCode",
    "ScanOutcome",
    "SourceManifest",
    "SourceSnapshot",
    "SourceSpec",
    "build_audit_plan",
    "canonical_stream_hash",
    "merge_sorted_runs",
    "scan_jsonl",
    "validate_audit_plan",
    "write_sorted_runs",
]
