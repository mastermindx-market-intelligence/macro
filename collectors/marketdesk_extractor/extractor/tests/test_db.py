"""Tests for db.py — init, upsert_discovered idempotency, status transitions."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from marketdesk_extractor import db
from marketdesk_extractor.schemas import ArticleMeta, Status


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _meta(
    blob_id: str = "blob-001",
    title: str = "Test Paper",
    institution: str | None = "JPM",
) -> ArticleMeta:
    return ArticleMeta(
        blob_id=blob_id,
        article_url=f"https://marketdesk.ai/library/browse?item={blob_id}",
        blob_url=f"https://marketdesk.ai/files/{blob_id}/blob",
        title=title,
        institution=institution,
        published_at=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
        published_unix=1751889600,
    )


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    c = db.connect(tmp_path / "test.sqlite")
    db.init_db(c)
    return c


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------

def test_init_db_creates_tables(conn: sqlite3.Connection) -> None:
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "papers" in tables
    assert "meta" in tables


def test_init_db_idempotent(conn: sqlite3.Connection) -> None:
    # calling init_db a second time must not raise
    db.init_db(conn)


# ---------------------------------------------------------------------------
# upsert_discovered — new row
# ---------------------------------------------------------------------------

def test_upsert_new_returns_id_and_true(conn: sqlite3.Connection) -> None:
    row_id, is_new = db.upsert_discovered(conn, _meta())
    assert isinstance(row_id, int)
    assert row_id >= 1
    assert is_new is True


def test_upsert_new_sets_discovered_status(conn: sqlite3.Connection) -> None:
    row_id, _ = db.upsert_discovered(conn, _meta())
    row = conn.execute("SELECT status FROM papers WHERE id=?", (row_id,)).fetchone()
    assert row["status"] == Status.DISCOVERED.value


# ---------------------------------------------------------------------------
# upsert_discovered — re-insert (idempotent)
# ---------------------------------------------------------------------------

def test_upsert_existing_returns_same_id_and_false(conn: sqlite3.Connection) -> None:
    row_id1, is_new1 = db.upsert_discovered(conn, _meta())
    row_id2, is_new2 = db.upsert_discovered(conn, _meta())
    assert row_id1 == row_id2
    assert is_new1 is True
    assert is_new2 is False


def test_upsert_does_not_regress_status(conn: sqlite3.Connection) -> None:
    """Re-discovering a paper that is already DOWNLOADED must keep DOWNLOADED."""
    row_id, _ = db.upsert_discovered(conn, _meta())
    db.set_status(conn, "blob-001", Status.DOWNLOADED)

    # re-upsert
    db.upsert_discovered(conn, _meta())

    row = conn.execute("SELECT status FROM papers WHERE id=?", (row_id,)).fetchone()
    assert row["status"] == Status.DOWNLOADED.value


def test_upsert_updates_title_on_re_insert(conn: sqlite3.Connection) -> None:
    db.upsert_discovered(conn, _meta(title="Original Title"))
    updated = ArticleMeta(
        blob_id="blob-001",
        article_url="https://marketdesk.ai/library/browse?item=blob-001",
        blob_url="https://marketdesk.ai/files/blob-001/blob",
        title="Updated Title",
        institution="JPM",
    )
    db.upsert_discovered(conn, updated)
    row = conn.execute(
        "SELECT title FROM papers WHERE blob_id='blob-001'"
    ).fetchone()
    assert row["title"] == "Updated Title"


# ---------------------------------------------------------------------------
# update_fields / set_status
# ---------------------------------------------------------------------------

def test_update_fields_changes_column(conn: sqlite3.Connection) -> None:
    db.upsert_discovered(conn, _meta())
    db.update_fields(conn, "blob-001", sha256="abc123", page_count=12)
    row = conn.execute(
        "SELECT sha256, page_count FROM papers WHERE blob_id='blob-001'"
    ).fetchone()
    assert row["sha256"] == "abc123"
    assert row["page_count"] == 12


def test_update_fields_ignores_unknown_columns(conn: sqlite3.Connection) -> None:
    db.upsert_discovered(conn, _meta())
    # should not raise
    db.update_fields(conn, "blob-001", nonexistent_col="value")


def test_set_status_advances_state(conn: sqlite3.Connection) -> None:
    db.upsert_discovered(conn, _meta())
    for target in (Status.DOWNLOADED, Status.PARSED, Status.COMPLETE):
        db.set_status(conn, "blob-001", target)
        row = conn.execute(
            "SELECT status FROM papers WHERE blob_id='blob-001'"
        ).fetchone()
        assert row["status"] == target.value


def test_set_status_accepts_string(conn: sqlite3.Connection) -> None:
    db.upsert_discovered(conn, _meta())
    db.set_status(conn, "blob-001", "FAILED")
    row = conn.execute(
        "SELECT status FROM papers WHERE blob_id='blob-001'"
    ).fetchone()
    assert row["status"] == "FAILED"


def test_set_status_records_error_message(conn: sqlite3.Connection) -> None:
    db.upsert_discovered(conn, _meta())
    db.set_status(conn, "blob-001", Status.FAILED, error_message="network timeout")
    row = conn.execute(
        "SELECT error_message FROM papers WHERE blob_id='blob-001'"
    ).fetchone()
    assert row["error_message"] == "network timeout"


# ---------------------------------------------------------------------------
# meta KV
# ---------------------------------------------------------------------------

def test_get_meta_missing_returns_default(conn: sqlite3.Connection) -> None:
    assert db.get_meta(conn, "no_key") is None
    assert db.get_meta(conn, "no_key", "fallback") == "fallback"


def test_set_and_get_meta_roundtrip(conn: sqlite3.Connection) -> None:
    db.set_meta(conn, "last_run", "2026-07-07T00:00:00Z")
    assert db.get_meta(conn, "last_run") == "2026-07-07T00:00:00Z"


def test_set_meta_overwrites(conn: sqlite3.Connection) -> None:
    db.set_meta(conn, "k", "v1")
    db.set_meta(conn, "k", "v2")
    assert db.get_meta(conn, "k") == "v2"


# ---------------------------------------------------------------------------
# counts_by_status
# ---------------------------------------------------------------------------

def test_counts_by_status(conn: sqlite3.Connection) -> None:
    for i in range(3):
        db.upsert_discovered(conn, _meta(blob_id=f"blob-{i}"))
    db.set_status(conn, "blob-0", Status.DOWNLOADED)
    counts = db.counts_by_status(conn)
    assert counts[Status.DISCOVERED.value] == 2
    assert counts[Status.DOWNLOADED.value] == 1
