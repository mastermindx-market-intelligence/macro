"""Cluster audit store opens must survive paths containing ?, # and %.

SQLite URI filenames split the path at the first ``?`` (query) and ``#``
(fragment) and percent-decode the rest, so the audit script's unquoted
``file:{path}?mode=ro`` misparses any store path carrying those bytes: with
``?`` or ``#`` in a directory name the ``mode=ro`` parameter is lost and a
truncated path is opened read-write-create, planting a stray database beside
the real one; ``%41`` in a directory name is decoded to ``A`` and the wrong
file is addressed. These tests pin the seeded-cluster read, the stray-file
refusal and the ``--store`` CLI on such paths (control case: ``plain``).
Seeding reuses the committed-RoutedRevision idiom of
tests/test_qbus_news_cluster_audit.py.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import sqlite3
from pathlib import Path

import pytest

from engine.qbus_news_contract import normalize_news
from engine.qbus_news_store import NewsStore, RoutedRevision
import scripts.qbus_news_cluster_audit as audit

UTC = timezone.utc
T0 = datetime(2026, 10, 5, 15, 0, tzinfo=UTC)

DIR_NAMES = ("plain", "q?mark", "hash#tag", "pct%41x")


def _routed(item_id: int, title: str, minute: int = 0) -> RoutedRevision:
    updated = T0 + timedelta(minutes=minute)
    revision = normalize_news(
        {
            "id": item_id,
            "created": (updated - timedelta(seconds=1)).isoformat(),
            "updated": updated.isoformat(),
            "title": title,
            "url": f"https://www.benzinga.com/news/{item_id}",
            "stocks": [{"name": "NVDA"}],
            "channels": [{"name": "News"}],
            "tags": [],
        },
        transport="benzinga_rest",
        received_at=updated + timedelta(seconds=2),
    )
    return RoutedRevision(
        revision=revision,
        security_ids=("sec-NVDA",),
        universe_revision="sp500-r1",
    )


def _checkpoint(db: Path) -> None:
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()


def _seeded_db(tmp_path: Path, dir_name: str) -> Path:
    """A store at <dir_name>/news.db holding a two-story cluster plus a loner."""
    db = tmp_path / dir_name / "news.db"
    with NewsStore(db, source_key="benzinga-rest") as store:
        store.commit(
            [
                _routed(1, "Nvidia launches new AI accelerator"),
                _routed(2, "Nvidia launches its new AI accelerator", 1),
                _routed(3, "Nvidia CFO resigns", 2),
            ],
            expected_cursor=None,
            next_cursor="c1",
        )
    _checkpoint(db)
    return db


@pytest.mark.parametrize("dir_name", DIR_NAMES)
def test_audit_store_reads_seeded_clusters_on_special_paths(tmp_path, dir_name):
    db = _seeded_db(tmp_path, dir_name)
    report = audit.audit_store(db)
    assert report["schema"] == "qbus.news_cluster_audit.v1"
    # Two routed stories cluster together; the third stays a loner.
    assert report["clusters"] == 2
    assert report["multi_member_clusters"] == 1
    assert report["size_histogram"] == {"1": 1, "2": 1}


@pytest.mark.parametrize("dir_name", DIR_NAMES)
def test_audit_store_creates_no_stray_file(tmp_path, dir_name):
    db = _seeded_db(tmp_path, dir_name)
    names_before = {entry.name for entry in db.parent.iterdir()}
    audit.audit_store(db)
    # A misparsed URI would create tmp_path/"q", tmp_path/"hash" or address
    # a decoded tmp_path/"pctAx" directory beside the real one.
    assert {entry for entry in tmp_path.iterdir()} == {tmp_path / dir_name}
    names_after = {entry.name for entry in db.parent.iterdir()}
    assert names_before <= names_after
    assert names_after - names_before <= {"news.db-wal", "news.db-shm"}


def test_audit_open_ro_connection_is_read_only_on_special_paths(tmp_path):
    db = _seeded_db(tmp_path, "q?mark")
    connection = audit._open_ro(db)
    insert = "INSERT INTO news_clusters (cluster_id) VALUES ('pin-uri')"
    try:
        # The right file was addressed: an unquoted URI would land on an
        # empty wrong database where this SELECT raises "no such table".
        assert connection.execute("SELECT COUNT(*) FROM news_clusters").fetchone()[0] == 2
        with pytest.raises(sqlite3.OperationalError):
            connection.execute(insert)
        # query_only=ON refuses writes on its own; clear it so the refusal
        # below proves the file itself was opened mode=ro, not merely guarded.
        connection.execute("PRAGMA query_only=OFF")
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute(insert)
    finally:
        connection.close()


@pytest.mark.parametrize("dir_name", DIR_NAMES)
def test_audit_cli_store_mode_on_special_paths(tmp_path, dir_name, capsys):
    db = _seeded_db(tmp_path, dir_name)
    assert audit.main(["--store", str(db)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["clusters"] == 2
    assert report["multi_member_clusters"] == 1
    assert report["size_histogram"] == {"1": 1, "2": 1}
