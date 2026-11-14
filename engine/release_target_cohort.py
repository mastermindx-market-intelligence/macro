"""Exact-byte reads of the incumbent Release Target collector cohort.

Shared by release-truth and descriptive workspace consumers. This module adds
no collector, cache, history store or target calculation. Decode the same bytes
that the manifest binds; refuse a changed manifest before returning the cohort.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from engine.release_target_truth import SOURCE_OUTPUT_TYPE, normalize_full_vintage_frame

COLLECTOR_MANIFEST_SCHEMA = "release_target_vintage_collection.v1"
COLLECTOR_INTEGRITY_PROFILE = "release_target_artifact_sha256_bytes.v1"
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_ARTIFACT_ROWS = 2_000_000
MAX_DECODED_BYTES = 128 * 1024 * 1024


class ReleaseTargetCohortError(ValueError):
    """A cohort is corrupt, unbound or changed while it was read."""


class ReleaseTargetCohortUnavailable(ReleaseTargetCohortError):
    """The collector has not completed the required source cohort."""


def logical_path(path: Path, logical_root: Path | None) -> str:
    if logical_root is not None:
        try:
            return path.resolve().relative_to(logical_root.resolve()).as_posix()
        except ValueError:
            pass
    return path.name


def _read_bounded(path: Path, limit: int, error_type: type[ValueError]) -> bytes:
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if not data or len(data) > limit:
        raise error_type(f"{path.name} is empty or exceeds its byte bound")
    return data


def _manifest_bytes(path: Path, logical_root: Path | None,
                    error_type: type[ValueError]) -> tuple[dict, dict, bytes]:
    data = _read_bounded(path, MAX_MANIFEST_BYTES, error_type)
    try:
        payload = json.loads(data)
    except (ValueError, UnicodeError) as exc:
        raise error_type("collector manifest is not valid JSON") from exc
    if not isinstance(payload, dict) or payload.get("schema") != COLLECTOR_MANIFEST_SCHEMA:
        raise error_type(f"collector manifest schema must be {COLLECTOR_MANIFEST_SCHEMA!r}")
    if payload.get("integrity_profile") != COLLECTOR_INTEGRITY_PROFILE:
        raise error_type("collector manifest lacks the required exact-byte integrity profile")
    if type(payload.get("source_output_type")) is not int or payload["source_output_type"] != SOURCE_OUTPUT_TYPE:
        raise error_type("collector manifest source_output_type must be 2")
    if payload.get("status") != "ok":
        failure = ReleaseTargetCohortUnavailable if error_type is ReleaseTargetCohortError else error_type
        raise failure(f"collector manifest status must be 'ok', got {payload.get('status')!r}")
    value = payload.get("completed_at")
    try:
        if not isinstance(value, str):
            raise ValueError("not a timestamp")
        completed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise error_type("collector manifest completed_at must be a timezone-aware ISO-8601 timestamp") from exc
    if completed.tzinfo is None or completed.utcoffset() is None:
        raise error_type("collector manifest completed_at must include an explicit timezone offset")
    collected_at = payload.get("collected_at")
    if collected_at is not None:
        try:
            collected = datetime.fromisoformat(collected_at.strip().replace("Z", "+00:00"))
            if collected.utcoffset() is None or collected > completed:
                raise ValueError("collection must precede completion and carry a timezone")
        except (AttributeError, TypeError, ValueError) as exc:
            raise error_type("collector manifest collected_at is invalid or after completion") from exc
    receipt = {
        "schema": payload["schema"], "integrity_profile": payload["integrity_profile"],
        "source_output_type": payload["source_output_type"],
        "collected_at": payload.get("collected_at"),
        "completed_at": completed.astimezone(timezone.utc).isoformat(),
        "path": logical_path(path, logical_root), "artifact_bytes": len(data),
        "artifact_sha256": hashlib.sha256(data).hexdigest(),
    }
    return payload, receipt, data


def manifest_series_entry(manifest: Mapping[str, Any], series_id: str, *,
                          error_type: type[ValueError] = ReleaseTargetCohortError) -> Mapping:
    series = manifest.get("series")
    failure = ReleaseTargetCohortUnavailable if error_type is ReleaseTargetCohortError else error_type
    if not isinstance(series, Mapping) or not isinstance(series.get(series_id), Mapping):
        raise failure(f"collector manifest has no bound entry for {series_id}")
    entry = series[series_id]
    if entry.get("status") not in {"written", "sealed"}:
        raise failure(f"collector manifest entry {series_id} is not durably written or sealed")
    return entry


def artifact_receipt(path: Path, entry: Mapping, manifest_receipt: Mapping, *,
                     logical_root: Path | None = None, data: bytes | None = None,
                     error_type: type[ValueError] = ReleaseTargetCohortError) -> dict:
    expected_sha, expected_bytes = entry.get("artifact_sha256"), entry.get("artifact_bytes")
    if not isinstance(expected_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
        raise error_type(f"manifest entry for {path.name} has no valid artifact_sha256")
    if type(expected_bytes) is not int or not 0 < expected_bytes <= MAX_ARTIFACT_BYTES:
        raise error_type(f"manifest entry for {path.name} has no valid bounded artifact_bytes")
    recorded_path = entry.get("path")
    if recorded_path and Path(str(recorded_path)).name != path.name:
        raise error_type(f"manifest basename mismatch for {path}: recorded={recorded_path!r}")
    body = data if data is not None else _read_bounded(path, MAX_ARTIFACT_BYTES, error_type)
    actual_sha = hashlib.sha256(body).hexdigest()
    if len(body) != expected_bytes:
        raise error_type(f"source parquet byte-count mismatch for {path.name}: manifest={expected_bytes} actual={len(body)}")
    if actual_sha != expected_sha:
        raise error_type(f"source parquet SHA-256 mismatch for {path.name}: manifest={expected_sha} actual={actual_sha}")
    return {
        "path": logical_path(path, logical_root), "artifact_bytes": len(body),
        "artifact_sha256": actual_sha,
        "manifest_artifact_sha256": manifest_receipt["artifact_sha256"],
        "manifest_bound": True, "manifest_entry_status": entry.get("status"),
        **{key: entry.get(key) for key in ("rows", "periods", "release_dates", "period_min", "period_max")},
    }


def validate_loaded_frame(frame: pd.DataFrame, entry: Mapping, series_id: str, *,
                          error_type: type[ValueError] = ReleaseTargetCohortError) -> None:
    if frame.empty:
        raise error_type(f"{series_id} full-vintage frame is empty")
    if set(frame["series"]) != {series_id}:
        raise error_type(f"{series_id} source contains another series")
    for field, actual, label in (
        ("rows", len(frame), "row"), ("periods", int(frame["period"].nunique()), "period"),
        ("release_dates", int(frame["realtime_start"].nunique()), "release-date"),
    ):
        expected = entry.get(field)
        if expected is not None and (type(expected) is not int or expected != actual):
            raise error_type(f"{series_id} {label}-count mismatch: manifest={expected} loaded={actual}")
    for field, value in (("period_min", frame["period"].min()), ("period_max", frame["period"].max())):
        if entry.get(field) is not None and entry[field] != value.date().isoformat():
            raise error_type(f"{series_id} {field} mismatch")
    if not frame["value"].map(lambda value: not isinstance(value, bool) and math.isfinite(float(value))).all():
        raise error_type(f"{series_id} has non-finite observations")
    if not all(end >= start.date() for start, end in zip(frame["realtime_start"], frame["realtime_end"])):
        raise error_type(f"{series_id} has an inverted vintage interval")


def _unchanged_manifest(path: Path, original: bytes, error_type: type[ValueError]) -> None:
    if _read_bounded(path, MAX_MANIFEST_BYTES, error_type) != original:
        raise error_type("collector manifest changed while reading the cohort")


def load_and_bind_manifest(path: Path, required_series: Mapping[str, Path], *,
                           logical_root: Path | None = None,
                           error_type: type[ValueError] = ReleaseTargetCohortError) -> tuple[dict, dict]:
    """Compatibility receipt helper; full consumers use read_release_target_cohort."""
    payload, receipt, original = _manifest_bytes(path, logical_root, error_type)
    for series_id, source_path in required_series.items():
        entry = manifest_series_entry(payload, series_id, error_type=error_type)
        artifact_receipt(Path(source_path), entry, receipt, logical_root=logical_root, error_type=error_type)
    _unchanged_manifest(path, original, error_type)
    return payload, receipt


def read_release_target_cohort(path: Path, required_series: Mapping[str, Path], *,
                               logical_root: Path | None = None,
                               error_type: type[ValueError] = ReleaseTargetCohortError) -> tuple[dict, dict, dict, dict]:
    """Return frames, manifest, manifest receipt and source receipts, bound once.

    The caller chooses the closed series set. The existing truth normalizer
    retains ownership of supported series and full-vintage semantics.
    """
    import pyarrow.parquet as parquet
    import pyarrow.types as types

    if not required_series:
        raise error_type("a cohort read must require at least one series")
    payload, receipt, original = _manifest_bytes(path, logical_root, error_type)
    frames, artifacts = {}, {}
    for series_id, source_path in required_series.items():
        source_path = Path(source_path)
        entry = manifest_series_entry(payload, series_id, error_type=error_type)
        data = _read_bounded(source_path, MAX_ARTIFACT_BYTES, error_type)
        artifacts[series_id] = artifact_receipt(
            source_path, entry, receipt, logical_root=logical_root, data=data, error_type=error_type)
        file = parquet.ParquetFile(io.BytesIO(data))
        if not 0 < file.metadata.num_rows <= MAX_ARTIFACT_ROWS or len(file.schema.names) > 32:
            raise error_type(f"{series_id} parquet exceeds the row or column bound")
        decoded_bytes = sum(file.metadata.row_group(i).total_byte_size for i in range(file.metadata.num_row_groups))
        if not 0 < decoded_bytes <= MAX_DECODED_BYTES:
            raise error_type(f"{series_id} parquet exceeds the decoded-byte bound")
        required = {"series", "period", "realtime_start", "realtime_end", "value", "source_output_type"}
        if not required.issubset(file.schema_arrow.names):
            raise error_type(f"{series_id} parquet is missing required full-vintage columns")
        for name in required:
            kind = file.schema_arrow.field(name).type
            numeric = types.is_integer(kind) or types.is_floating(kind)
            temporal = types.is_date(kind) or types.is_timestamp(kind)
            textual = types.is_string(kind) or types.is_large_string(kind)
            if not (numeric if name in {"value", "source_output_type"} else textual if name == "series" else textual or temporal):
                raise error_type(f"{series_id} parquet column {name} has an unsupported type")
        table = file.read(columns=sorted(required))
        if table.nbytes > MAX_DECODED_BYTES:
            raise error_type(f"{series_id} decoded table exceeds the byte bound")
        raw = table.to_pandas()
        if "source_output_type" not in raw.columns:
            raise error_type(f"{source_path} has no source_output_type marker; refusing ambiguous store")
        if "series" not in raw or set(raw["series"]) != {series_id}:
            raise error_type(f"{series_id} source contains another series or lacks its identity")
        if raw["value"].map(lambda value: isinstance(value, bool)).any():
            raise error_type(f"{series_id} has boolean observations")
        try:
            frame = normalize_full_vintage_frame(raw, series_id=series_id)
        except ValueError as exc:
            raise error_type(str(exc)) from exc
        if len(frame) != len(raw):
            raise error_type(f"{series_id} has invalid or duplicate rows")
        validate_loaded_frame(frame, entry, series_id, error_type=error_type)
        frames[series_id] = frame
    _unchanged_manifest(path, original, error_type)
    return frames, payload, receipt, artifacts
