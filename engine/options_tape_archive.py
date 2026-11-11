"""Immutable cold-archive codec for ThetaData option trade + attached-NBBO rows.

This module is storage only.  It does not fetch market data, choose a universe,
schedule work, sign flow, or create a second options truth plane.  The incumbent
ThetaData/T2a collector supplies normalized source rows; this codec preserves them
as an immutable root-session Parquet plus a content-bound receipt.

Layout::

    {archive_root}/session=YYYY-MM-DD/root=ROOT/trade_nbbo.parquet
    {archive_root}/session=YYYY-MM-DD/root=ROOT/receipt.json

The first complete capture wins.  A later invocation verifies the existing bytes
and returns ``already_present``; it never silently rewrites history.  A missing,
malformed, or hash-mismatched half of the pair fails closed for explicit repair.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

SCHEMA = "options.raw_trade_nbbo/v1"
SOURCE = "thetadata"
SOURCE_ENDPOINT = "/v3/option/history/trade_quote"
PARQUET_NAME = "trade_nbbo.parquet"
RECEIPT_NAME = "receipt.json"
_ROOT_RE = re.compile(r"^[A-Z0-9._-]+$")

# Source fields whose presence makes the archive useful as a replay substrate.
# Additive collector fields are retained automatically and listed in the receipt.
REQUIRED_COLUMNS = frozenset(
    {
        "date",
        "trade_timestamp",
        "quote_timestamp",
        "sequence",
        "expiration",
        "strike",
        "right",
        "price",
        "size",
        "exchange",
        "bid",
        "ask",
        "condition",
        "bid_size",
        "ask_size",
        "root",
    }
)


class TapeArchiveError(RuntimeError):
    """Base class for archive failures."""


class TapeArchiveIntegrityError(TapeArchiveError):
    """Existing archive bytes/receipt disagree or are incomplete."""


class TapeArchiveSchemaError(TapeArchiveError):
    """Collector rows do not satisfy the frozen minimum replay schema."""


def _utc_iso(value: datetime | None = None) -> str:
    ts = value or datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def resolve_archive_root(override: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the raw archive root without inventing a second config owner.

    Production should set ``THETADATA_TAPE_ARCHIVE`` to an explicit staging/cold
    mount.  The fallback stays under the existing tape_flow data owner so local
    tests and bounded manual runs remain self-contained.
    """
    if override is not None:
        return Path(override).expanduser()
    env = os.environ.get("THETADATA_TAPE_ARCHIVE", "").strip()
    if env:
        return Path(env).expanduser()
    from lib import config

    return config.data_dir() / "tape_flow" / "raw" / "partitions"


def archive_paths(
    root: str,
    trade_date: date | str,
    *,
    archive_root: str | os.PathLike[str] | None = None,
) -> tuple[Path, Path]:
    r = str(root).strip().upper()
    if not _ROOT_RE.fullmatch(r):
        raise ValueError(f"unsafe option root: {root!r}")
    d = date.fromisoformat(str(trade_date)[:10])
    base = resolve_archive_root(archive_root) / f"session={d.isoformat()}" / f"root={r}"
    return base / PARQUET_NAME, base / RECEIPT_NAME


def _validate_frame(df: pd.DataFrame, *, expected_root: str, label: str) -> None:
    missing = sorted(REQUIRED_COLUMNS.difference(df.columns))
    if missing:
        raise TapeArchiveSchemaError(f"{label} frame missing required columns: {missing}")
    if df.empty:
        return
    roots = set(df["root"].dropna().astype(str).str.upper().unique())
    if roots != {expected_root}:
        raise TapeArchiveSchemaError(
            f"{label} frame root identity mismatch: expected={expected_root} observed={sorted(roots)}"
        )


def _validate_existing(parquet_path: Path, receipt_path: Path) -> dict[str, Any] | None:
    p_exists = parquet_path.exists()
    r_exists = receipt_path.exists()
    if not p_exists and not r_exists:
        return None
    if p_exists != r_exists:
        raise TapeArchiveIntegrityError(
            f"incomplete immutable archive pair: parquet={p_exists} receipt={r_exists} path={parquet_path.parent}"
        )
    try:
        receipt = json.loads(receipt_path.read_text())
    except Exception as exc:  # noqa: BLE001
        raise TapeArchiveIntegrityError(f"unreadable tape receipt: {receipt_path}: {exc}") from exc
    receipt_schema = receipt.get("schema")
    if receipt_schema != SCHEMA:
        raise TapeArchiveIntegrityError(
            f"unexpected tape receipt schema at {receipt_path}: {receipt_schema!r}"
        )
    observed_size = parquet_path.stat().st_size
    expected_size = receipt.get("compressed_bytes", -1)
    if int(expected_size) != observed_size:
        raise TapeArchiveIntegrityError(
            f"tape archive size mismatch at {parquet_path}: receipt={expected_size} actual={observed_size}"
        )
    observed_sha = _sha256(parquet_path)
    expected_sha = receipt.get("sha256")
    if expected_sha != observed_sha:
        raise TapeArchiveIntegrityError(
            f"tape archive sha256 mismatch at {parquet_path}: receipt={expected_sha} actual={observed_sha}"
        )
    return receipt


def _write_parquet_streaming(path: Path, frames: list[pd.DataFrame]) -> None:
    """Write multiple source frames without materializing one giant concat frame."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    os.close(fd)
    tmp = Path(tmp_name)
    writer: pq.ParquetWriter | None = None
    try:
        # Freeze a stable union column order.  Current call/put frames share a
        # schema; the union guard also preserves future additive collector fields.
        columns: list[str] = []
        for frame in frames:
            for c in frame.columns:
                if c not in columns:
                    columns.append(c)
        normalized = [frame.reindex(columns=columns) for frame in frames]
        schemas = [
            pa.Table.from_pandas(
                frame.iloc[: min(len(frame), 1024)] if not frame.empty else frame,
                preserve_index=False,
            ).schema
            for frame in normalized
        ]
        schema = pa.unify_schemas(schemas, promote_options="permissive")
        writer = pq.ParquetWriter(
            tmp,
            schema,
            compression="zstd",
            compression_level=3,
            use_dictionary=True,
            write_statistics=True,
        )
        wrote = False
        for frame in normalized:
            if frame.empty:
                continue
            table = pa.Table.from_pandas(frame, preserve_index=False)
            if table.schema != schema:
                try:
                    table = table.cast(schema, safe=False)
                except Exception as exc:  # noqa: BLE001
                    raise TapeArchiveSchemaError(
                        f"call/put archive schemas diverged: expected={schema} observed={table.schema}"
                    ) from exc
            writer.write_table(table, row_group_size=250_000)
            wrote = True
        if not wrote:
            # A legitimate no-trade observation still gets a durable empty file.
            writer.write_table(pa.Table.from_pandas(normalized[0], preserve_index=False))
        writer.close()
        writer = None
        os.replace(tmp, path)
    except BaseException:
        if writer is not None:
            writer.close()
        tmp.unlink(missing_ok=True)
        raise


def load_trade_nbbo(
    root: str,
    trade_date: date | str,
    *,
    archive_root: str | os.PathLike[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]] | None:
    """Load and verify an archived root-session for deterministic replay."""
    r = str(root).strip().upper()
    d = date.fromisoformat(str(trade_date)[:10])
    parquet_path, receipt_path = archive_paths(r, d, archive_root=archive_root)
    receipt = _validate_existing(parquet_path, receipt_path)
    if receipt is None:
        return None
    try:
        frame = pd.read_parquet(parquet_path)
    except Exception as exc:
        raise TapeArchiveIntegrityError(
            f"unreadable tape parquet after receipt verification: {parquet_path}: {exc}"
        ) from exc
    if len(frame) != int(receipt.get("rows", -1)):
        raise TapeArchiveIntegrityError(
            f"tape row-count mismatch at {parquet_path}: receipt={receipt.get('rows')} actual={len(frame)}"
        )
    _validate_frame(frame, expected_root=r, label="archive")
    replay_receipt = dict(receipt)
    replay_receipt["archive_status"] = "replayed"
    return frame, replay_receipt


def archive_trade_nbbo(
    *,
    root: str,
    trade_date: date | str,
    calls: pd.DataFrame,
    puts: pd.DataFrame,
    archive_root: str | os.PathLike[str] | None = None,
    capture_started_at: datetime | None = None,
    capture_completed_at: datetime | None = None,
) -> dict[str, Any]:
    """Persist one immutable root-session raw trade+attached-NBBO capture.

    Returns a compact receipt with ``archive_status`` equal to ``written`` or
    ``already_present``.  Existing bytes are content-verified before reuse.
    """
    r = str(root).strip().upper()
    d = date.fromisoformat(str(trade_date)[:10])
    _validate_frame(calls, expected_root=r, label="call")
    _validate_frame(puts, expected_root=r, label="put")

    parquet_path, receipt_path = archive_paths(r, d, archive_root=archive_root)
    existing = _validate_existing(parquet_path, receipt_path)
    if existing is not None:
        out = dict(existing)
        out["archive_status"] = "already_present"
        return out

    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    _write_parquet_streaming(parquet_path, [calls, puts])
    parquet_sha = _sha256(parquet_path)
    columns: list[str] = []
    for frame in (calls, puts):
        for c in frame.columns:
            if c not in columns:
                columns.append(c)
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "source": SOURCE,
        "source_endpoint": SOURCE_ENDPOINT,
        "root": r,
        "session": d.isoformat(),
        "rows": int(len(calls) + len(puts)),
        "call_rows": int(len(calls)),
        "put_rows": int(len(puts)),
        "columns": columns,
        "compressed_bytes": int(parquet_path.stat().st_size),
        "sha256": parquet_sha,
        "capture_started_at": _utc_iso(capture_started_at) if capture_started_at else None,
        "capture_completed_at": _utc_iso(capture_completed_at) if capture_completed_at else None,
        "mastermind_persisted_at": _utc_iso(),
        "source_clock_fields": ["trade_timestamp", "quote_timestamp"],
        "vendor_available_at": None,
        "clock_disclosure": (
            "trade_timestamp and quote_timestamp retain ThetaData field semantics; "
            "neither is relabeled as exchange/SIP/receipt time"
        ),
        "immutability": "first_complete_capture_wins",
    }
    _atomic_json(receipt_path, receipt)
    # Final self-check means a successful return is a readable content-bound pair.
    verified = _validate_existing(parquet_path, receipt_path)
    assert verified is not None
    out = dict(verified)
    out["archive_status"] = "written"
    return out
