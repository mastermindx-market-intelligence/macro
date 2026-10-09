"""Lossless qbus.v1 -> qbus news-store migration utility.

Default mode is read-only validation. Passing --write imports the exact legacy
rows into the production-inert qbus-owned SQLite store and verifies that the
store can reproduce the same ordered qbus.v1 row projection. It never rewrites,
deletes, renames, or replaces the source parquet and never changes qbus's active
writer selector.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Sequence

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import pandas as pd

from engine import qbus
from engine.qbus_news_store import NewsStore, validate_legacy_rows

MIGRATION_SOURCE_KEY = "qbus-v1-migration"


class MigrationError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_rows(rows: Sequence[dict]) -> str:
    return json.dumps(
        list(rows),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=True,
    )


def _read_source(source: Path) -> tuple[dict, ...]:
    if not source.exists() or not source.is_file():
        raise MigrationError("source_missing")
    try:
        frame = pd.read_parquet(source)
    except Exception as exc:  # noqa: BLE001
        raise MigrationError("source_unreadable") from exc

    expected = tuple(qbus.COLUMNS)
    actual = tuple(str(x) for x in frame.columns)
    if actual != expected:
        raise MigrationError("source_schema_mismatch")

    try:
        rows = validate_legacy_rows(frame.to_dict(orient="records"))
    except Exception as exc:  # preserve store's reason as causal evidence
        raise MigrationError("source_row_invalid") from exc

    seen: set[str] = set()
    for row in rows:
        item_id = str(row["item_id"])
        if item_id in seen:
            raise MigrationError("source_duplicate_item_id")
        seen.add(item_id)
    return rows


def migrate(
    *,
    source: Path | str,
    database: Path | str,
    write: bool = False,
) -> dict:
    source_path = Path(source)
    database_path = Path(database)

    source_sha = _sha256(source_path) if source_path.exists() else ""
    rows = _read_source(source_path)
    source_sha_after_read = _sha256(source_path)
    if source_sha_after_read != source_sha:
        raise MigrationError("source_changed_during_read")

    base = {
        "schema": "qbus.news_migration.v1",
        "mode": "write" if write else "check_only",
        "source_rows": len(rows),
        "source_sha256": source_sha,
        "database": str(database_path),
        "imported_rows": 0,
        "duplicate_rows": 0,
        "projection_equal": None,
    }
    if not write:
        return base

    database_path.parent.mkdir(parents=True, exist_ok=True)
    with NewsStore(database_path, source_key=MIGRATION_SOURCE_KEY) as store:
        receipt = store.import_legacy_rows(rows)
        projection = store.legacy_rows()

    projection_equal = _canonical_rows(projection) == _canonical_rows(rows)
    source_sha_after_write = _sha256(source_path)
    if source_sha_after_write != source_sha:
        raise MigrationError("source_mutated")
    if not projection_equal:
        raise MigrationError("projection_mismatch")

    return {
        **base,
        "imported_rows": receipt.imported_rows,
        "duplicate_rows": receipt.duplicate_rows,
        "projection_equal": True,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate or import qbus.v1 into the production-inert news store."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/qbus/items.parquet"),
        help="existing qbus.v1 parquet; never modified",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/qbus/qbus.sqlite3"),
        help="target qbus-owned SQLite store",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="perform the import; omitted means validation only",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = migrate(
            source=args.source,
            database=args.database,
            write=bool(args.write),
        )
    except MigrationError as exc:
        print(
            json.dumps(
                {
                    "schema": "qbus.news_migration.v1",
                    "ok": False,
                    "error": str(exc),
                },
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps({**report, "ok": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())