"""Read-only store opens must survive paths containing ?, # and %.

SQLite URI filenames split the path at the first ``?`` (query) and ``#``
(fragment) and percent-decode the rest, so an unquoted ``file:{db}?mode=ro``
misparses any store path carrying those bytes. These tests pin that both
read-only open paths percent-quote the directory (control case: ``plain``).
Seeding reuses the committed-RoutedRevision idiom of
tests/test_qbus_news_flow_store.py.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3
from pathlib import Path

import pytest

from engine.qbus_news_contract import normalize_news
from engine.qbus_news_store import NewsReadRights, NewsStore, RoutedRevision

UTC = timezone.utc
NOW = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
T0 = NOW - timedelta(minutes=30)

DIR_NAMES = ("plain", "q?mark", "hash#tag", "pct%41x")
SECURITY_ID = "SEC:US-XNAS-NVDA"
TITLE = "Nvidia launches accelerator"


def _routed(item_id: int = 1) -> RoutedRevision:
    revision = normalize_news(
        {
            "id": item_id,
            "created": (T0 - timedelta(seconds=1)).isoformat(),
            "updated": T0.isoformat(),
            "title": TITLE,
            "teaser": f"teaser:{TITLE}",
            "url": f"https://www.benzinga.com/news/{item_id}",
            "stocks": [{"name": "NVDA"}],
            "channels": [{"name": "News"}],
            "tags": [],
        },
        transport="benzinga_rest",
        received_at=T0 + timedelta(seconds=2),
    )
    return RoutedRevision(
        revision=revision,
        security_ids=(SECURITY_ID,),
        universe_revision="sp500-r1",
    )


def _checkpoint(db: Path) -> None:
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()


def _seeded_db(tmp_path: Path, dir_name: str) -> Path:
    """A store at <dir_name>/news.db holding one committed routed story."""
    db = tmp_path / dir_name / "news.db"
    with NewsStore(db, source_key="benzinga-rest") as store:
        store.commit(
            [_routed(item_id=1)],
            expected_cursor=None,
            next_cursor="c1",
        )
    _checkpoint(db)
    return db


@pytest.mark.parametrize("dir_name", DIR_NAMES)
def test_open_readonly_reads_seeded_rows_on_special_paths(tmp_path, dir_name):
    db = _seeded_db(tmp_path, dir_name)
    rights = NewsReadRights(allowed_sources=frozenset({"benzinga"}))
    with NewsStore.open_readonly(db, source_key="benzinga-rest") as ro:
        rows = ro.snapshot(SECURITY_ID, limit=50, cursor=None, rights=rights).rows
        assert len(rows) == 1
        assert rows[0].item_count == 1
        assert rows[0].source_count == 1
        assert rows[0].title == TITLE
        # The file itself was opened read-only: a direct write is refused, and
        # still refused with query_only cleared, so mode=ro was not dropped.
        with pytest.raises(sqlite3.OperationalError):
            ro._conn.execute(
                "INSERT INTO qbus_meta(key,value) VALUES('pin-uri','1')"
            )
        ro._conn.execute("PRAGMA query_only=OFF")
        try:
            with pytest.raises(sqlite3.OperationalError):
                ro._conn.execute(
                    "INSERT INTO qbus_meta(key,value) VALUES('pin-uri','1')"
                )
        finally:
            ro._conn.execute("PRAGMA query_only=ON")
    if dir_name == "pct%41x":
        # %41 must reach SQLite as %41, never decoded to A: no stray store.
        assert not (tmp_path / "pctAx").exists()


@pytest.mark.parametrize("dir_name", DIR_NAMES)
def test_news_flow_reads_through_special_paths(tmp_path, dir_name):
    db = _seeded_db(tmp_path, dir_name)
    store = NewsStore(db, source_key="benzinga-rest")
    try:
        flow = store.news_flow(
            SECURITY_ID,
            now=NOW,
            rights=NewsReadRights(allowed_sources=frozenset({"benzinga"})),
        )
    finally:
        store.close()
    assert flow["schema"] == "ticker_news.flow.v1"
    assert flow["state"] in ("ok", "thin_history")
    assert flow["reason"] is None
    assert flow["reports_24h"] == 1
    assert flow["stories_24h"] == 1
