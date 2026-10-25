"""Tests for SHA-256 dedup logic — find_sha256_owner, SKIPPED_SEEN transitions."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from marketdesk_extractor import db
from marketdesk_extractor.schemas import ArticleMeta, Status


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _meta(blob_id: str, title: str = "Some Paper") -> ArticleMeta:
    return ArticleMeta(
        blob_id=blob_id,
        article_url=f"https://marketdesk.ai/library/browse?item={blob_id}",
        blob_url=f"https://marketdesk.ai/files/{blob_id}/blob",
        title=title,
        institution="Goldman",
    )


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    c = db.connect(tmp_path / "dedupe.sqlite")
    db.init_db(c)
    return c


# ---------------------------------------------------------------------------
# find_sha256_owner
# ---------------------------------------------------------------------------

def test_find_sha256_owner_returns_none_when_absent(conn: sqlite3.Connection) -> None:
    result = db.find_sha256_owner(conn, "deadbeef" * 8)
    assert result is None


def test_find_sha256_owner_finds_row(conn: sqlite3.Connection) -> None:
    db.upsert_discovered(conn, _meta("A"))
    db.update_fields(conn, "A", sha256="abc" * 21 + "d")  # 64 hex chars
    row = db.find_sha256_owner(conn, "abc" * 21 + "d")
    assert row is not None
    assert row["blob_id"] == "A"


def test_find_sha256_owner_exclude_blob_id(conn: sqlite3.Connection) -> None:
    """Excluding the owning blob_id returns None (used for self-check on re-download)."""
    db.upsert_discovered(conn, _meta("A"))
    sha = "cafe" * 16
    db.update_fields(conn, "A", sha256=sha)

    # excluding the owner → no other row
    result = db.find_sha256_owner(conn, sha, exclude_blob_id="A")
    assert result is None


def test_find_sha256_owner_two_rows_second_is_duplicate(conn: sqlite3.Connection) -> None:
    """Two rows share a sha256 (same PDF, different blob_ids on MarketDesk).
    find_sha256_owner on the second blob_id's sha should return the first row."""
    sha = "1234" * 16

    # first paper is downloaded and sha set
    db.upsert_discovered(conn, _meta("first"))
    db.update_fields(conn, "first", sha256=sha, status=Status.COMPLETE.value)

    # second paper arrives with the same content
    db.upsert_discovered(conn, _meta("second"))
    # pipeline tries to set sha; finds a conflict — check find_sha256_owner
    owner = db.find_sha256_owner(conn, sha, exclude_blob_id="second")
    assert owner is not None
    assert owner["blob_id"] == "first"


def test_duplicate_paper_marked_skipped_seen(conn: sqlite3.Connection) -> None:
    """Simulate the pipeline marking the duplicate as SKIPPED_SEEN."""
    sha = "abcd" * 16
    db.upsert_discovered(conn, _meta("original"))
    db.update_fields(conn, "original", sha256=sha, status=Status.COMPLETE.value)

    db.upsert_discovered(conn, _meta("dup"))
    # pipeline detects duplicate via find_sha256_owner
    owner = db.find_sha256_owner(conn, sha, exclude_blob_id="dup")
    assert owner is not None

    # pipeline sets dup to SKIPPED_SEEN
    db.set_status(conn, "dup", Status.SKIPPED_SEEN)

    row = conn.execute(
        "SELECT status FROM papers WHERE blob_id='dup'"
    ).fetchone()
    assert row["status"] == Status.SKIPPED_SEEN.value


def test_skipped_seen_does_not_regress_to_discovered_on_re_upsert(
    conn: sqlite3.Connection,
) -> None:
    """Re-upserting a paper already SKIPPED_SEEN keeps SKIPPED_SEEN."""
    db.upsert_discovered(conn, _meta("dup"))
    db.set_status(conn, "dup", Status.SKIPPED_SEEN)

    # pipeline re-discovers the same article
    db.upsert_discovered(conn, _meta("dup"))

    row = conn.execute(
        "SELECT status FROM papers WHERE blob_id='dup'"
    ).fetchone()
    assert row["status"] == Status.SKIPPED_SEEN.value


def test_get_by_status_returns_only_matching(conn: sqlite3.Connection) -> None:
    db.upsert_discovered(conn, _meta("p1"))
    db.upsert_discovered(conn, _meta("p2"))
    db.set_status(conn, "p2", Status.SKIPPED_SEEN)

    skipped = db.get_by_status(conn, [Status.SKIPPED_SEEN])
    discovered = db.get_by_status(conn, [Status.DISCOVERED])
    assert len(skipped) == 1
    assert skipped[0]["blob_id"] == "p2"
    assert len(discovered) == 1
    assert discovered[0]["blob_id"] == "p1"
