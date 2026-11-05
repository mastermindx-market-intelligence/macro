"""Lossless legacy-qbus migration tests for the production-inert news store."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from engine import qbus
from engine import qbus_news_store as store_mod


def _legacy_row(
    *,
    item_id: str,
    crawled: str,
    title: str,
    source: str = "reuters",
    entities=("NVDA",),
) -> dict:
    return qbus.normalize_row(
        {
            "item_id": item_id,
            "event_key": f"ev_{item_id}",
            "desk": "financial_news",
            "source": source,
            "source_tier": 1,
            "lang": "en",
            "url": f"https://example.test/{item_id}",
            "title": title,
            "body_sha256": hashlib.sha256(title.encode()).hexdigest(),
            "seendate": "2026-10-04T19:59:00+00:00",
            "_crawled_at": crawled,
            "timestamp_quality": "PUBLISHER_STATED",
            "entities": list(entities),
            "themes": ["semiconductors"],
            "importance_raw": 0.75,
        }
    )


def _rows() -> list[dict]:
    return [
        _legacy_row(
            item_id="legacy-a",
            crawled="2026-10-04T20:00:00+00:00",
            title="Nvidia launches accelerator",
        ),
        _legacy_row(
            item_id="legacy-b",
            crawled="2026-10-04T20:01:00+00:00",
            title="AMD announces chip update",
            entities=("AMD",),
        ),
    ]


def _parquet(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=list(qbus.COLUMNS)).to_parquet(path, index=False)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_store_import_preserves_every_legacy_column_id_clock_and_order(tmp_path):
    db = tmp_path / "qbus.sqlite3"
    rows = _rows()
    with store_mod.NewsStore(db, source_key="benzinga-live") as store:
        receipt = store.import_legacy_rows(rows)
        assert receipt.imported_rows == 2
        assert receipt.duplicate_rows == 0
        assert receipt.total_rows == 2
        assert store.legacy_rows() == tuple(rows)
        assert store.counts()["legacy_items"] == 2
        assert store.counts()["revisions"] == 0
        assert store.legacy_rows()[0]["item_id"] == "legacy-a"
        assert store.legacy_rows()[0]["seendate"] == "2026-10-04T19:59:00+00:00"
        assert store.legacy_rows()[0]["_crawled_at"] == "2026-10-04T20:00:00+00:00"


def test_exact_legacy_reimport_is_idempotent(tmp_path):
    db = tmp_path / "qbus.sqlite3"
    rows = _rows()
    with store_mod.NewsStore(db, source_key="benzinga-live") as store:
        store.import_legacy_rows(rows)
        second = store.import_legacy_rows(rows)
        assert second.imported_rows == 0
        assert second.duplicate_rows == 2
        assert second.total_rows == 2
        assert store.legacy_rows() == tuple(rows)


def test_partial_import_can_resume_without_rewriting_verified_prefix(tmp_path):
    db = tmp_path / "qbus.sqlite3"
    rows = _rows()
    with store_mod.NewsStore(db, source_key="benzinga-live") as store:
        first = store.import_legacy_rows(rows[:1])
        resumed = store.import_legacy_rows(rows)
        assert first.imported_rows == 1
        assert resumed.imported_rows == 1
        assert resumed.duplicate_rows == 1
        assert store.legacy_rows() == tuple(rows)


def test_conflicting_same_legacy_item_id_rolls_back_entire_batch(tmp_path):
    db = tmp_path / "qbus.sqlite3"
    rows = _rows()
    with store_mod.NewsStore(db, source_key="benzinga-live") as store:
        store.import_legacy_rows(rows[:1])
        before = store.legacy_rows()
        conflict = dict(rows[0], title="different bytes")
        with pytest.raises(store_mod.LegacyCollision):
            store.import_legacy_rows(
                [
                    _legacy_row(
                        item_id="legacy-c",
                        crawled="2026-10-04T20:02:00+00:00",
                        title="new row must roll back too",
                    ),
                    conflict,
                ]
            )
        assert store.legacy_rows() == before
        assert store.counts()["legacy_items"] == 1


def test_legacy_import_refuses_missing_or_extra_schema_fields(tmp_path):
    db = tmp_path / "qbus.sqlite3"
    row = _rows()[0]
    missing = dict(row)
    missing.pop("timestamp_quality")
    extra = dict(row, surprise_field="not-owned-by-qbus-v1")
    with store_mod.NewsStore(db, source_key="benzinga-live") as store:
        with pytest.raises(store_mod.LegacySchemaError):
            store.import_legacy_rows([missing])
        with pytest.raises(store_mod.LegacySchemaError):
            store.import_legacy_rows([extra])
        assert store.counts()["legacy_items"] == 0


def test_migration_check_only_validates_without_creating_database(tmp_path):
    from scripts import migrate_qbus_news as migration

    source = tmp_path / "items.parquet"
    db = tmp_path / "qbus.sqlite3"
    _parquet(source, _rows())
    source_sha = _sha(source)

    report = migration.migrate(source=source, database=db, write=False)

    assert report["mode"] == "check_only"
    assert report["source_rows"] == 2
    assert report["source_sha256"] == source_sha
    assert report["projection_equal"] is None
    assert not db.exists()
    assert _sha(source) == source_sha


def test_migration_write_round_trips_exact_projection_without_touching_source(tmp_path):
    from scripts import migrate_qbus_news as migration

    source = tmp_path / "items.parquet"
    db = tmp_path / "qbus.sqlite3"
    rows = _rows()
    _parquet(source, rows)
    source_sha = _sha(source)

    report = migration.migrate(source=source, database=db, write=True)

    assert report["mode"] == "write"
    assert report["source_rows"] == 2
    assert report["imported_rows"] == 2
    assert report["projection_equal"] is True
    assert report["source_sha256"] == source_sha
    assert _sha(source) == source_sha
    with store_mod.NewsStore(db, source_key=migration.MIGRATION_SOURCE_KEY) as store:
        assert store.legacy_rows() == tuple(rows)
        assert store.counts()["revisions"] == 0


def test_migration_is_restartable_after_prior_verified_prefix(tmp_path):
    from scripts import migrate_qbus_news as migration

    source = tmp_path / "items.parquet"
    db = tmp_path / "qbus.sqlite3"
    rows = _rows()
    with store_mod.NewsStore(db, source_key=migration.MIGRATION_SOURCE_KEY) as store:
        store.import_legacy_rows(rows[:1])
    _parquet(source, rows)

    report = migration.migrate(source=source, database=db, write=True)

    assert report["imported_rows"] == 1
    assert report["duplicate_rows"] == 1
    assert report["projection_equal"] is True


def test_migration_refuses_source_schema_drift_before_database_write(tmp_path):
    from scripts import migrate_qbus_news as migration

    source = tmp_path / "items.parquet"
    db = tmp_path / "qbus.sqlite3"
    df = pd.DataFrame(_rows(), columns=list(qbus.COLUMNS))
    df["unexpected"] = "x"
    df.to_parquet(source, index=False)

    with pytest.raises(migration.MigrationError, match="source_schema_mismatch"):
        migration.migrate(source=source, database=db, write=True)

    assert not db.exists()