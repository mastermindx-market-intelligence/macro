"""Futures tape Data OS primitives.

This module defines the durable, provider-neutral contract for raw and normalized
futures tape partitions. It does not fetch data and it does not create a scheduler.

Provider roles are intentionally explicit:
- LSE vendor-continuous symbols are secondary/deep-history research inputs.
- Massive/CME exact contracts are exchange-contract truth when entitlement exists.
- Mastermind continuous series are derived artifacts built from exact contracts.

The physical root is selected by MMX_FUTURES_TAPE_ROOT. Falling back to
data/futures_tape keeps tests and developer smoke runs hermetic; production hosts
should point the variable at the external SSD.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable

SCHEMA = "futures_tape_partition.v1"
DEFAULT_ROOT = Path("data/futures_tape")
ROOT_ENV = "MMX_FUTURES_TAPE_ROOT"

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


class FuturesTapeError(ValueError):
    """Invalid futures-tape metadata or an unsafe storage request."""


class SourceRole(Enum):
    """Epistemic role of a source, not a vendor-quality score."""

    VENDOR_CONTINUOUS = "vendor_continuous"
    EXCHANGE_CONTRACT = "exchange_contract"
    MMX_DERIVED_CONTINUOUS = "mmx_derived_continuous"


class PartitionState(Enum):
    PROVISIONAL = "provisional"
    FINAL = "final"


def storage_root(explicit: str | Path | None = None) -> Path:
    if explicit is not None:
        return Path(explicit).expanduser()
    env = (os.environ.get(ROOT_ENV) or "").strip()
    return Path(env).expanduser() if env else DEFAULT_ROOT


def safe_component(value: str) -> str:
    raw = str(value).strip()
    if not raw:
        raise FuturesTapeError("empty storage component")
    out = _SAFE.sub("_", raw)
    if out in {".", ".."} or "/" in out or "\\" in out:
        raise FuturesTapeError(f"unsafe storage component {value!r}")
    return out


@dataclass(frozen=True)
class StorageCapacity:
    path: str
    total_bytes: int
    used_bytes: int
    free_bytes: int

    @property
    def free_gib(self) -> float:
        return self.free_bytes / (1024 ** 3)


def capacity(path: str | Path) -> StorageCapacity:
    p = Path(path).expanduser()
    # disk_usage requires an existing ancestor; walk upward for a not-yet-created root.
    probe = p
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    total, used, free = shutil.disk_usage(probe)
    return StorageCapacity(str(p), int(total), int(used), int(free))


def require_capacity(path: str | Path, min_free_gib: float) -> StorageCapacity:
    if min_free_gib < 0:
        raise FuturesTapeError("min_free_gib must be non-negative")
    c = capacity(path)
    if c.free_gib < min_free_gib:
        raise FuturesTapeError(
            f"{path}: only {c.free_gib:.1f} GiB free; "
            f"{min_free_gib:.1f} GiB reserve required"
        )
    return c


def sha256_file(path: str | Path, chunk_bytes: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        while True:
            chunk = fh.read(chunk_bytes)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class PartitionManifest:
    source: str
    source_role: str
    source_symbol: str
    state: str
    relative_path: str
    row_count: int
    byte_count: int
    sha256: str
    retrieved_at_utc: str
    min_timestamp_utc: str | None = None
    max_timestamp_utc: str | None = None
    schema: str = SCHEMA

    def validate(self) -> None:
        if self.schema != SCHEMA:
            raise FuturesTapeError(f"unsupported manifest schema {self.schema!r}")
        try:
            SourceRole(self.source_role)
            PartitionState(self.state)
        except ValueError as exc:
            raise FuturesTapeError(str(exc)) from exc
        if self.row_count < 0 or self.byte_count < 0:
            raise FuturesTapeError("row_count/byte_count must be non-negative")
        if not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise FuturesTapeError("sha256 must be 64 lowercase hex chars")
        p = Path(self.relative_path)
        if p.is_absolute() or ".." in p.parts:
            raise FuturesTapeError("relative_path must stay beneath the tape root")

    def to_json(self) -> str:
        self.validate()
        return json.dumps(asdict(self), indent=2, sort_keys=True) + "\n"

    @classmethod
    def from_json(cls, text: str) -> "PartitionManifest":
        obj = cls(**json.loads(text))
        obj.validate()
        return obj


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def raw_export_path(
    root: str | Path,
    source: str,
    symbol: str,
    window_start: str,
    window_end: str,
) -> Path:
    return (
        Path(root)
        / "raw"
        / f"source={safe_component(source)}"
        / f"symbol={safe_component(symbol)}"
        / f"window={safe_component(window_start)}_{safe_component(window_end)}"
        / "export.parquet"
    )


def normalized_day_path(
    root: str | Path,
    source: str,
    identity: str,
    day: str,
) -> Path:
    return (
        Path(root)
        / "normalized"
        / "ticks"
        / f"source={safe_component(source)}"
        / f"instrument={safe_component(identity)}"
        / f"date={safe_component(day)}"
        / "part-000.parquet"
    )


def derived_bar_path(
    root: str | Path,
    instrument: str,
    frequency: str,
    day: str,
) -> Path:
    return (
        Path(root)
        / "derived"
        / "bars"
        / f"instrument={safe_component(instrument)}"
        / f"freq={safe_component(frequency)}"
        / f"date={safe_component(day)}"
        / "part-000.parquet"
    )


def manifest_path(data_path: str | Path) -> Path:
    return Path(str(data_path) + ".manifest.json")


def write_manifest_atomic(data_path: str | Path, manifest: PartitionManifest) -> Path:
    target = manifest_path(data_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".partial")
    tmp.write_text(manifest.to_json(), encoding="utf-8")
    os.replace(tmp, target)
    return target


def verify_manifest(root: str | Path, manifest_file: str | Path) -> list[str]:
    """Return violations; never mutates the store."""
    mf = Path(manifest_file)
    try:
        manifest = PartitionManifest.from_json(mf.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{mf}: unreadable manifest: {exc}"]

    data = Path(root) / manifest.relative_path
    problems: list[str] = []
    if not data.is_file():
        return [f"{mf}: missing data file {data}"]
    size = data.stat().st_size
    if size != manifest.byte_count:
        problems.append(f"{data}: byte_count {size} != manifest {manifest.byte_count}")
    digest = sha256_file(data)
    if digest != manifest.sha256:
        problems.append(f"{data}: sha256 {digest} != manifest {manifest.sha256}")
    return problems


def audit_manifests(root: str | Path) -> list[str]:
    p = Path(root)
    if not p.exists():
        return [f"{p}: futures tape root does not exist"]
    out: list[str] = []
    for mf in sorted(p.rglob("*.manifest.json")):
        out.extend(verify_manifest(p, mf))
    return out


def coverage_windows(manifests: Iterable[PartitionManifest]) -> list[tuple[str, str]]:
    """Sorted unique raw-export windows, useful for resumable planners."""
    return sorted({(m.source, m.relative_path) for m in manifests})
