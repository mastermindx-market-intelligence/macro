"""Offline materialization of Tiingo raw receipts to research-only Parquet.

This is a Data OS L1 candidate reader, not L2 enrollment or an alternate
identity/backtest/PIT authority. One input hash -> one immutable view artifact.
Every input is verified before use, no vendor requests, no API credential reads,
no internal SSD fallback. Unsupported product families remain RAW_ONLY.

Usage:
  python -m scripts.tiingo_materialize --dry-run --max-receipts 500
  python -m scripts.tiingo_materialize --max-receipts 500
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import os
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors.tiingo_archive import (
    DEFAULT_ARCHIVE, MIN_FREE_BYTES, TiingoArchiveError, _publish_once,
    require_external_root, require_space,
)
from lib.dataos.tiingo_views import SCHEMA_VERSION, research_rows

MAX_RAW_MATERIALIZE_BYTES = 64 * 1024 * 1024
MAX_OUTPUT_ROWS = 1_000_000


def verified_raw(archive_root: Path, receipt: dict[str, Any]) -> bytes:
    if receipt.get("vendor") != "tiingo":
        raise TiingoArchiveError("non-Tiingo receipt")
    rel = Path(receipt["raw_path"])
    if rel.is_absolute() or ".." in rel.parts:
        raise TiingoArchiveError("raw receipt escaped lake root")
    target = (archive_root / rel).resolve()
    if not target.is_relative_to(archive_root.resolve()):
        raise TiingoArchiveError("raw path escapes external drive")
    if target.stat().st_size > MAX_RAW_MATERIALIZE_BYTES:
        raise TiingoArchiveError("raw compressed partition exceeds research batch limit")
    # Decompress bounded to prevent a tiny gzip bomb from exhausting memory.
    with gzip.open(target, "rb") as fp:
        raw = fp.read(MAX_RAW_MATERIALIZE_BYTES + 1)
    if len(raw) > MAX_RAW_MATERIALIZE_BYTES:
        raise TiingoArchiveError("raw uncompressed partition exceeds research batch limit")
    if hashlib.sha256(raw).hexdigest() != receipt["raw_sha256"]:
        raise TiingoArchiveError("raw source digest mismatch")
    return raw


def materialize_one(root: Path, receipt: dict[str, Any], *,
                    free_floor: int = MIN_FREE_BYTES,
                    dry_run: bool = False) -> dict[str, Any]:
    require_space(root, floor=free_floor)
    raw = verified_raw(root, receipt)
    try:
        rows = research_rows(raw, receipt)
    except (TypeError, ValueError, KeyError, OverflowError) as err:
        raise TiingoArchiveError("source payload cannot be normalized") from err
    if rows is None:
        return {"status": "RAW_ONLY", "reason": "NO_REVIEWED_L1_PROJECTOR",
                "source": receipt.get("source")}
    if len(rows) > MAX_OUTPUT_ROWS:
        raise TiingoArchiveError("normalized row cap exceeded")
    if not rows:
        return {"status": "EMPTY_NORMALIZED", "rows": 0,
                "source": receipt.get("source")}
    day = (receipt.get("observed_at_utc")
           or receipt.get("first_received_at_utc") or "undated")[:10]
    source = receipt.get("source") or "boats-firehose"
    digest = receipt["raw_sha256"]
    dest = root / "normalized" / source / day / (digest + ".parquet")
    manifest_path = root / "manifests" / source / day / (digest + ".json")
    file_exists = dest.is_file()
    if file_exists and manifest_path.is_file():
        return {"status": "EXISTS", "rows": len(rows),
                "source": source, "path": dest.relative_to(root).as_posix()}
    if dry_run:
        return {"status": "WOULD_REPAIR" if file_exists else "WOULD_WRITE",
                "rows": len(rows), "source": source,
                "path": dest.relative_to(root).as_posix()}
    try:
        import pyarrow as pa  # type: ignore[import-not-found]
        import pyarrow.parquet as pq  # type: ignore[import-not-found]
    except ImportError as err:
        raise TiingoArchiveError("pyarrow is required for L1 Parquet") from err

    # Union columns across Q/T/B shapes; pyarrow from_pylist otherwise silently
    # drops fields present only in later rows (loss of sale-condition or quotes).
    keys = sorted({k for row in rows for k in row})
    table = pa.Table.from_pylist([{k: row.get(k) for k in keys} for row in rows])
    if file_exists:
        # A crash may leave a fully written Parquet without its manifest.
        # Repair only after comparing exact normalized source row content.
        if pq.read_table(dest).to_pylist() != table.to_pylist():
            raise TiingoArchiveError("orphaned Parquet disagrees with raw source")
        created = False
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".parquet-", dir=str(dest.parent))
        os.close(fd)
        try:
            pq.write_table(table, tmp, compression="zstd")
            with open(tmp, "rb") as fp:
                os.fsync(fp.fileno())
            try:
                os.link(tmp, dest)
                created = True
            except FileExistsError:
                created = False
        finally:
            Path(tmp).unlink(missing_ok=True)
        if not created and pq.read_table(dest).to_pylist() != table.to_pylist():
            raise TiingoArchiveError("concurrent Parquet disagrees with raw source")
    out = {"status": "WRITTEN" if created else "REPAIRED_MANIFEST",
           "source": source, "rows": len(rows),
           "path": dest.relative_to(root).as_posix()}
    if created or not manifest_path.is_file():
        manifest = {
            "schema": "mastermind.tiingo.materialized_receipt.v1",
            "source_sha256": digest,
            "source_receipt_schema": receipt["schema"],
            "source_vendor": "tiingo",
            "view_schema": SCHEMA_VERSION,
            "output_path": out["path"],
            "output_sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
            "rows": len(rows), "columns": keys,
            "dataos_identity_admitted": False,
            "pit_backtest_eligible": False,
            "redistribution_admitted": False,
            "source_observed_at_utc": receipt.get("observed_at_utc")
                                      or receipt.get("first_received_at_utc"),
        }
        _publish_once(
            manifest_path,
            (json.dumps(manifest, sort_keys=True) + "\n").encode("utf-8"))
    return out


def materialize_many(root: Path = DEFAULT_ARCHIVE, *,
                     max_receipts: int = 500,
                     source_filter: str | None = None,
                     dry_run: bool = True,
                     check_mount: bool = True,
                     free_floor: int = MIN_FREE_BYTES) -> dict[str, Any]:
    if max_receipts < 1 or max_receipts > 100_000:
        raise ValueError("invalid receipt budget")
    base = require_external_root(root, check_mount=check_mount)
    result: dict[str, Any] = {
        "seen": 0, "written": 0, "existing": 0, "raw_only": 0,
        "empty": 0, "would_write": 0, "refused": 0, "errors": [],
        "dry_run": dry_run, "raw_receipts_total": None,
        "scope": "RESEARCH_ONLY_NOT_CANONICAL",
    }
    if not (base / "receipts").exists():
        return result
    for file in sorted((base / "receipts").rglob("*.json")):
        if result["seen"] >= max_receipts:
            result["truncated"] = True
            break
        try:
            receipt = json.loads(file.read_text())
            if source_filter and receipt.get("source", "boats-firehose") != source_filter:
                continue
            result["seen"] += 1
            out = materialize_one(base, receipt, dry_run=dry_run,
                                  free_floor=free_floor)
            status = out["status"]
            bucket = {
                "WRITTEN": "written", "EXISTS": "existing", "RAW_ONLY": "raw_only",
                "EMPTY_NORMALIZED": "empty", "WOULD_WRITE": "would_write",
                "WOULD_REPAIR": "would_write", "REPAIRED_MANIFEST": "written",
            }[status]
            result[bucket] += 1
        except (OSError, ValueError, KeyError, TiingoArchiveError) as err:
            result["refused"] += 1
            if len(result["errors"]) < 20:
                result["errors"].append({
                    "receipt": file.relative_to(base).as_posix(),
                    "reason": type(err).__name__,
                })
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--max-receipts", type=int, default=500)
    p.add_argument("--source", help="materialize only one vendor product")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    try:
        outcome = materialize_many(max_receipts=args.max_receipts,
                                   source_filter=args.source,
                                   dry_run=args.dry_run)
    except (ValueError, TiingoArchiveError) as err:
        print(json.dumps({"status": "REFUSED", "reason": str(err)}))
        return 2
    print(json.dumps(outcome, indent=2))
    return 2 if outcome["refused"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
