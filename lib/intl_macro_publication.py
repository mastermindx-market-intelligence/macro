"""Exact acquisition of the materialized ECB deposit-rate artifact pair."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from io import BytesIO
from pathlib import Path

import pandas as pd


_ARTIFACT_PATH = Path("intl_macro") / "ez_depo_rate.parquet"
_PROVENANCE_PATH = Path("intl_macro") / "provenance.json"
_ARTIFACT_MAX_BYTES = 16 * 1024 * 1024
_PROVENANCE_MAX_BYTES = 8 * 1024 * 1024
_READ_CHUNK_BYTES = 64 * 1024


def _read_bounded(fd: int, limit: int) -> bytes:
    chunks: list[bytes] = []
    remaining = limit
    while remaining:
        chunk = os.read(fd, min(_READ_CHUNK_BYTES, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_stable_once(path: Path, limit: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("source is not a regular file")
        if before.st_size > limit:
            raise ValueError("source exceeds its byte limit")
        payload = _read_bounded(fd, limit)
        after = os.fstat(fd)
        stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        before_identity = tuple(getattr(before, field) for field in stable_fields)
        after_identity = tuple(getattr(after, field) for field in stable_fields)
        if before_identity != after_identity:
            raise ValueError("source changed while being consumed")
        if len(payload) != min(before.st_size, limit):
            raise ValueError("bounded source read was incomplete")
    finally:
        os.close(fd)

    final = os.lstat(path)
    if (final.st_dev, final.st_ino) != (before.st_dev, before.st_ino):
        raise ValueError("source path was replaced")
    if final.st_mode != before.st_mode:
        raise ValueError("source path mode changed")
    return payload


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_nonstandard_constant(value: str) -> None:
    raise ValueError(f"nonstandard JSON constant: {value}")


def _missing_result() -> dict[str, object]:
    return {
        "status": "missing",
        "series": None,
        "provenance": None,
        "materialized_identity": None,
    }


def _failed_result() -> dict[str, object]:
    return {
        "status": "failed",
        "series": None,
        "provenance": None,
        "materialized_identity": None,
    }


def read_ecb_deposit_materialization(*, data_root: Path | str) -> dict[str, object]:
    """Read one exact ECB Parquet/provenance pair without granting disclosure.

    The two snapshots are consumed independently. Matching identities bind the
    bytes consumed by this reader, but the read is not an atomic pair snapshot.
    """
    root = Path(data_root)
    try:
        artifact_bytes = _read_stable_once(root / _ARTIFACT_PATH, _ARTIFACT_MAX_BYTES)
        provenance_bytes = _read_stable_once(
            root / _PROVENANCE_PATH, _PROVENANCE_MAX_BYTES
        )

        artifact_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
        provenance_sha256 = hashlib.sha256(provenance_bytes).hexdigest()

        frame = pd.read_parquet(BytesIO(artifact_bytes))
        if not isinstance(frame, pd.DataFrame):
            raise ValueError("Parquet source did not decode to a DataFrame")
        if frame.columns.tolist() != ["ez_depo_rate"]:
            raise ValueError("Parquet source has an invalid column layout")
        if frame.columns.duplicated().any():
            raise ValueError("Parquet source has duplicate columns")

        document = json.loads(
            provenance_bytes,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonstandard_constant,
        )
        if type(document) is not dict:
            raise ValueError("provenance root is not an object")
        if "series" not in document:
            return _missing_result()
        series_provenance = document["series"]
        if type(series_provenance) is not dict:
            raise ValueError("provenance series root is not an object")
        if "ez_depo_rate" not in series_provenance:
            return _missing_result()
        provenance = series_provenance["ez_depo_rate"]
        if type(provenance) is not dict:
            raise ValueError("ECB provenance is not an object")

        series = frame.iloc[:, 0]
        return {
            "status": "ready",
            "series": series,
            "provenance": provenance,
            "materialized_identity": {
                "artifact_sha256": artifact_sha256,
                "provenance_sha256": provenance_sha256,
                "column": "ez_depo_rate",
            },
        }
    except FileNotFoundError:
        return _missing_result()
    except Exception:
        return _failed_result()
