"""Cluster policy version provenance per stored cluster. Hermetic: fixtures only."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import os
import shutil
import sqlite3
from pathlib import Path

from engine.qbus_news_cluster import CLUSTER_POLICY_VERSION
from engine.qbus_news_contract import normalize_news
from engine.qbus_news_store import NewsReadRights, NewsStore, RoutedRevision
from engine.qbus_news_velocity import compute_news_velocity

try:
    from engine.qbus_news_cluster import UNKNOWN_CLUSTER_POLICY_VERSION
except ImportError:  # pre-change base: the constant does not exist yet
    UNKNOWN_CLUSTER_POLICY_VERSION = "unknown (pre-column)"


UTC = timezone.utc
NOW = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
T0 = NOW - timedelta(minutes=30)
SEC = "SEC:US-XNAS-NVDA"

# The near-duplicate pair from tests/test_qbus_news_store_clusters.py:69,
# which the live policy mints as exactly one cluster row.
TITLE_A = "Nvidia launches new AI accelerator"
TITLE_B = "Nvidia launches its new AI accelerator"
UNRELATED_TITLE = "Eurobond deal priced in Paris"
OLD_VERSION = "qbus_news_cluster.v1"


def _rights() -> NewsReadRights:
    return NewsReadRights(allowed_sources=frozenset({"benzinga"}))


def _routed(item_id: int, title: str, minute: int = 0) -> RoutedRevision:
    t = T0 + timedelta(minutes=minute)
    revision = normalize_news(
        {
            "id": item_id,
            "created": (t - timedelta(seconds=1)).isoformat(),
            "updated": t.isoformat(),
            "title": title,
            "teaser": f"teaser:{title}",
            "url": f"https://www.benzinga.com/news/{item_id}",
            "stocks": [{"name": "NVDA"}],
            "channels": [{"name": "News"}],
            "tags": [],
        },
        transport="benzinga_rest",
        received_at=t + timedelta(seconds=2),
    )
    return RoutedRevision(
        revision=revision,
        security_ids=(SEC,),
        universe_revision="sp500-r1",
    )


def _checkpoint(db: Path) -> None:
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()


def _table_columns(conn: sqlite3.Connection) -> list[str]:
    return [str(row[1]) for row in conn.execute("PRAGMA table_info(news_clusters)")]


def _columns_on_disk(db: Path) -> list[str]:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return _table_columns(conn)
    finally:
        conn.close()


def _clustered_store(db: Path) -> None:
    """One store whose two near-duplicate reports mint exactly one cluster."""
    with NewsStore(db, source_key="benzinga-rest") as store:
        store.commit(
            [_routed(1, TITLE_A, minute=0), _routed(2, TITLE_B, minute=1)],
            expected_cursor=None,
            next_cursor="c1",
        )
    _checkpoint(db)


def _legacy_db(tmp_path: Path, name: str = "legacy.sqlite3") -> Path:
    """A store whose news_clusters table predates the policy column."""
    assert sqlite3.sqlite_version_info >= (3, 35)
    db = tmp_path / name
    _clustered_store(db)
    conn = sqlite3.connect(db)
    try:
        if "cluster_policy_version" in _table_columns(conn):
            conn.execute(
                "ALTER TABLE news_clusters DROP COLUMN cluster_policy_version"
            )
        conn.commit()
    finally:
        conn.close()
    _checkpoint(db)
    assert "cluster_policy_version" not in _columns_on_disk(db)
    return db


def _flow(db: Path, *, now: datetime = NOW) -> dict:
    with NewsStore.open_readonly(db, source_key="benzinga-rest") as store:
        return store.news_flow(SEC, now=now, rights=_rights())


def _velocity(db: Path, *, now: datetime = NOW) -> dict:
    _checkpoint(db)
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        return compute_news_velocity(
            conn,
            security_id=SEC,
            now=now,
            allowed_sources=frozenset({"benzinga"}),
        )
    finally:
        conn.close()


def _versions_24h(db: Path) -> object:
    return _velocity(db)["cluster_policy_versions_24h"]


def test_fresh_store_has_column_and_stamps_v2(tmp_path):
    db = tmp_path / "fresh.sqlite3"
    with NewsStore(db, source_key="benzinga-rest") as store:
        assert "cluster_policy_version" in _table_columns(store._conn)
        store.commit(
            [_routed(1, TITLE_A, minute=0), _routed(2, TITLE_B, minute=1)],
            expected_cursor=None,
            next_cursor="c1",
        )
        rows = store._conn.execute(
            "SELECT cluster_policy_version FROM news_clusters"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == CLUSTER_POLICY_VERSION


def test_legacy_store_readonly_open_does_not_migrate(tmp_path):
    db = _legacy_db(tmp_path)
    ro = tmp_path / "legacy-ro.sqlite3"
    shutil.copyfile(db, ro)
    conn = sqlite3.connect(ro)
    try:
        conn.execute("PRAGMA journal_mode=DELETE")
    finally:
        conn.close()
    os.chmod(ro, 0o444)
    try:
        before = hashlib.sha256(ro.read_bytes()).hexdigest()
        flow = _flow(ro)
        assert flow["stories_24h"] > 0
        assert (
            flow["provenance"]["cluster_policy_version"]
            == UNKNOWN_CLUSTER_POLICY_VERSION
        )
        assert hashlib.sha256(ro.read_bytes()).hexdigest() == before
        assert "cluster_policy_version" not in _columns_on_disk(ro)
    finally:
        os.chmod(ro, 0o644)


def test_writable_open_adds_column_idempotently(tmp_path):
    db = _legacy_db(tmp_path)
    with NewsStore(db, source_key="benzinga-rest") as store:
        assert _table_columns(store._conn).count("cluster_policy_version") == 1
    with NewsStore(db, source_key="benzinga-rest") as store:
        assert _table_columns(store._conn).count("cluster_policy_version") == 1
        values = store._conn.execute(
            "SELECT cluster_policy_version FROM news_clusters"
        ).fetchall()
    assert [row[0] for row in values] == [None]


def test_mixed_legacy_and_new_clusters_join_labels(tmp_path):
    db = _legacy_db(tmp_path)
    with NewsStore(db, source_key="benzinga-rest") as store:
        store.commit(
            [_routed(3, UNRELATED_TITLE, minute=2)],
            expected_cursor="c1",
            next_cursor="c2",
        )
    _checkpoint(db)
    flow = _flow(db)
    assert flow["stories_24h"] == 2
    assert flow["provenance"]["cluster_policy_version"] == (
        "qbus_news_cluster.v2 + unknown (pre-column)"
    )
    assert _versions_24h(db) == [
        "qbus_news_cluster.v2",
        "unknown (pre-column)",
    ]


def test_stored_older_version_is_reported_not_the_constant(tmp_path):
    db = tmp_path / "older.sqlite3"
    _clustered_store(db)
    conn = sqlite3.connect(db)
    try:
        # On the pre-change base the column does not exist and this UPDATE
        # is skipped, so the flow assertion below fails on the constant the
        # base always reports.
        if "cluster_policy_version" in _table_columns(conn):
            conn.execute(
                "UPDATE news_clusters SET cluster_policy_version=?",
                (OLD_VERSION,),
            )
        conn.commit()
    finally:
        conn.close()
    _checkpoint(db)
    flow = _flow(db)
    assert flow["stories_24h"] > 0
    assert flow["provenance"]["cluster_policy_version"] == OLD_VERSION
    assert _versions_24h(db) == [OLD_VERSION]


def test_no_clustered_story_in_window_names_the_policy_in_force(tmp_path):
    db = tmp_path / "unclustered.sqlite3"
    with NewsStore(db, source_key="benzinga-rest") as store:
        store.commit(
            [_routed(1, TITLE_A, minute=0)],
            expected_cursor=None,
            next_cursor="c1",
        )
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DELETE FROM news_cluster_members")
        conn.execute("DELETE FROM news_clusters")
        conn.commit()
    finally:
        conn.close()
    _checkpoint(db)
    flow = _flow(db)
    assert flow["stories_24h"] == 1
    assert (
        flow["provenance"]["cluster_policy_version"] == CLUSTER_POLICY_VERSION
    )
    assert _versions_24h(db) == []


def test_velocity_versions_key_is_sorted_list(tmp_path):
    db = _legacy_db(tmp_path)
    with NewsStore(db, source_key="benzinga-rest") as store:
        store.commit(
            [_routed(3, UNRELATED_TITLE, minute=2)],
            expected_cursor="c1",
            next_cursor="c2",
        )
    _checkpoint(db)
    versions = _versions_24h(db)
    assert isinstance(versions, list)
    assert versions == sorted(set(versions))
    assert set(versions) == {
        CLUSTER_POLICY_VERSION,
        UNKNOWN_CLUSTER_POLICY_VERSION,
    }


def test_velocity_versions_key_is_sorted_on_every_hash_seed(tmp_path):
    """The sorted-list contract fails deterministically, not by set-order luck.

    A two-element set iterates in the sorted order on some PYTHONHASHSEED
    values, so asserting sortedness over a fixed stamp pair can pass even
    when the code emits the raw set order. This test picks, at run time, a
    stamp pair whose set iteration is NOT sorted in either insertion order,
    so emitting the set order unsorted fails on every seed.
    """
    db = tmp_path / "sorted.sqlite3"
    with NewsStore(db, source_key="benzinga-rest") as store:
        store.commit(
            [_routed(1, TITLE_A, minute=0), _routed(2, UNRELATED_TITLE, minute=1)],
            expected_cursor=None,
            next_cursor="c1",
        )
    conn = sqlite3.connect(db)
    try:
        cluster_ids = [
            str(row[0])
            for row in conn.execute(
                "SELECT cluster_id FROM news_clusters ORDER BY cluster_id"
            )
        ]
        assert len(cluster_ids) == 2
        pair = None
        for i in range(64):
            for j in range(i + 1, 64):
                x, y = f"stamp-{i:02d}", f"stamp-{j:02d}"
                if x > y:
                    x, y = y, x
                if list({x, y}) != [x, y] and list({y, x}) != [x, y]:
                    pair = (x, y)
                    break
            if pair is not None:
                break
        assert pair is not None, "no unsorted-iteration stamp pair available"
        x, y = pair
        for cluster_id, stamp in zip(cluster_ids, (x, y)):
            conn.execute(
                "UPDATE news_clusters SET cluster_policy_version=? WHERE cluster_id=?",
                (stamp, cluster_id),
            )
        conn.commit()
    finally:
        conn.close()
    _checkpoint(db)
    versions = _versions_24h(db)
    assert versions == [x, y]
    assert versions == sorted(set(versions))
    assert _flow(db)["provenance"]["cluster_policy_version"] == f"{x} + {y}"


def test_schema_row_unchanged_after_migration(tmp_path):
    db = _legacy_db(tmp_path)
    with NewsStore(db, source_key="benzinga-rest"):
        pass
    conn = sqlite3.connect(db)
    try:
        row = conn.execute(
            "SELECT value FROM qbus_meta WHERE key='schema'"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row[0] == "qbus.news_store.v1"


def test_orphan_member_reads_unknown(tmp_path):
    db = tmp_path / "orphan.sqlite3"
    _clustered_store(db)
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DELETE FROM news_clusters")
        conn.commit()
    finally:
        conn.close()
    _checkpoint(db)
    flow = _flow(db)
    assert flow["stories_24h"] > 0
    assert (
        flow["provenance"]["cluster_policy_version"]
        == UNKNOWN_CLUSTER_POLICY_VERSION
    )
    assert _versions_24h(db) == [UNKNOWN_CLUSTER_POLICY_VERSION]
