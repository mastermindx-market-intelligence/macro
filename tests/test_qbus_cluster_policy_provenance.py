"""Cluster policy version provenance per stored cluster. Hermetic: fixtures only."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import os
import shutil
import sqlite3
from pathlib import Path

import pytest

from engine.qbus_news_cluster import CLUSTER_POLICY_VERSION
from engine.qbus_news_cluster import ClusterPolicy
from engine.qbus_news_cluster import cluster_policy_version
from engine.qbus_news_contract import normalize_news
from engine.qbus_news_store import NewsReadRights, NewsStore, RoutedRevision
from engine.qbus_news_velocity import compute_news_velocity

try:
    from engine.qbus_news_cluster import UNKNOWN_CLUSTER_POLICY_VERSION
except ImportError:  # pre-change base: the constant does not exist yet
    UNKNOWN_CLUSTER_POLICY_VERSION = "unknown (pre-column)"

try:
    from engine.qbus_news_store import _META_CLUSTER_POLICY_KEY
except ImportError:  # pre-change base: the meta key constant does not exist yet
    _META_CLUSTER_POLICY_KEY = "cluster_policy_version"


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
        "qbus_news_cluster.v3 + unknown (pre-column)"
    )
    assert _versions_24h(db) == [
        "qbus_news_cluster.v3",
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


def test_no_clustered_story_in_window_names_custom_policy_in_force(tmp_path):
    db = tmp_path / "custom-policy-unclustered.sqlite3"
    label = (
        "qbus_news_cluster.v3 (title_threshold=0.9, "
        "window_seconds=21600, max_candidates=128)"
    )
    with NewsStore(
        db,
        source_key="benzinga-rest",
        cluster_policy=ClusterPolicy(title_threshold=0.9),
    ) as store:
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
    with NewsStore.open_readonly(
        db,
        source_key="benzinga-rest",
        cluster_policy=ClusterPolicy(title_threshold=0.9),
    ) as store:
        flow = store.news_flow(SEC, now=NOW, rights=_rights())
    assert flow["stories_24h"] == 1
    assert flow["provenance"]["cluster_policy_version"] == label
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


def test_members_without_clusters_table_read_unknown(tmp_path):
    db = tmp_path / "members-only-flow.sqlite3"
    _clustered_store(db)
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DROP TABLE news_clusters")
        conn.commit()
    finally:
        conn.close()
    _checkpoint(db)
    flow = _flow(db)
    assert flow["stories_24h"] == 1
    assert (
        flow["provenance"]["cluster_policy_version"]
        == UNKNOWN_CLUSTER_POLICY_VERSION
    )
    assert _versions_24h(db) == [UNKNOWN_CLUSTER_POLICY_VERSION]


def test_concurrent_writable_open_tolerates_duplicate_column(
    tmp_path, monkeypatch
):
    db = _legacy_db(tmp_path)
    real_connect = sqlite3.connect
    fired = []

    class _StalePragmaRows:
        """fetchall() replays the column list captured before the racing ALTER."""

        def __init__(self, rows):
            self._rows = rows

        def fetchall(self):
            return self._rows

    class _RacingConnection(sqlite3.Connection):
        def execute(self, sql, params=()):
            if not fired and sql.strip() == "PRAGMA table_info(news_clusters)":
                fired.append(True)
                rows = super().execute(sql).fetchall()
                # A second concurrent writable open of the same legacy
                # store adds the column after this PRAGMA read its rows.
                other = real_connect(str(db), timeout=5.0, isolation_level=None)
                try:
                    other.execute(
                        "ALTER TABLE news_clusters"
                        " ADD COLUMN cluster_policy_version TEXT"
                    )
                finally:
                    other.close()
                return _StalePragmaRows(rows)
            return super().execute(sql, params)

    def _connect(*args, **kwargs):
        kwargs["factory"] = _RacingConnection
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", _connect)
    with NewsStore(db, source_key="benzinga-rest") as store:
        assert _table_columns(store._conn).count("cluster_policy_version") == 1
        # A swallowed race must leave the store writable: commit one report
        # (a fresh cluster, stamped by the policy in force) and read it back.
        store.commit(
            [_routed(3, UNRELATED_TITLE, minute=2)],
            expected_cursor="c1",
            next_cursor="c2",
        )
    assert fired == [True]
    assert _columns_on_disk(db).count("cluster_policy_version") == 1
    flow = _flow(db)
    assert flow["stories_24h"] == 2
    assert flow["provenance"]["cluster_policy_version"] == (
        f"{CLUSTER_POLICY_VERSION} + {UNKNOWN_CLUSTER_POLICY_VERSION}"
    )


def test_alter_non_duplicate_error_still_raises(tmp_path, monkeypatch):
    db = _legacy_db(tmp_path)
    real_connect = sqlite3.connect

    class _LockedAlterConnection(sqlite3.Connection):
        def execute(self, sql, params=()):
            if sql.strip() == (
                "ALTER TABLE news_clusters"
                " ADD COLUMN cluster_policy_version TEXT"
            ):
                raise sqlite3.OperationalError("database is locked")
            return super().execute(sql, params)

    def _connect(*args, **kwargs):
        kwargs["factory"] = _LockedAlterConnection
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", _connect)
    with pytest.raises(sqlite3.OperationalError, match="database is locked"):
        NewsStore(db, source_key="benzinga-rest")


def test_alter_duplicate_error_without_column_still_raises(
    tmp_path, monkeypatch
):
    db = _legacy_db(tmp_path)
    real_connect = sqlite3.connect

    class _DuplicateAlterConnection(sqlite3.Connection):
        def execute(self, sql, params=()):
            if sql.strip() == (
                "ALTER TABLE news_clusters"
                " ADD COLUMN cluster_policy_version TEXT"
            ):
                raise sqlite3.OperationalError(
                    "duplicate column name: cluster_policy_version"
                )
            return super().execute(sql, params)

    def _connect(*args, **kwargs):
        kwargs["factory"] = _DuplicateAlterConnection
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", _connect)
    with pytest.raises(
        sqlite3.OperationalError, match="duplicate column name"
    ):
        NewsStore(db, source_key="benzinga-rest")
    assert "cluster_policy_version" not in _columns_on_disk(db)


def test_custom_policy_is_stamped_not_the_constant(tmp_path):
    db = tmp_path / "custom-policy.sqlite3"
    label = (
        "qbus_news_cluster.v3 (title_threshold=0.9, "
        "window_seconds=21600, max_candidates=128)"
    )
    with NewsStore(
        db,
        source_key="benzinga-rest",
        cluster_policy=ClusterPolicy(title_threshold=0.9),
    ) as store:
        store.commit(
            [_routed(1, TITLE_A, minute=0), _routed(2, TITLE_B, minute=1)],
            expected_cursor=None,
            next_cursor="c1",
        )
        rows = store._conn.execute(
            "SELECT cluster_policy_version FROM news_clusters"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == label
    _checkpoint(db)
    assert _flow(db)["provenance"]["cluster_policy_version"] == label


def test_default_policy_stamps_exactly_v3(tmp_path):
    db = tmp_path / "default-policy.sqlite3"
    with NewsStore(db, source_key="benzinga-rest") as store:
        store.commit(
            [_routed(1, TITLE_A, minute=0), _routed(2, TITLE_B, minute=1)],
            expected_cursor=None,
            next_cursor="c1",
        )
        rows = store._conn.execute(
            "SELECT cluster_policy_version FROM news_clusters"
        ).fetchall()
    assert [row[0] for row in rows] == ["qbus_news_cluster.v3"]
    from engine.qbus_news_cluster import cluster_policy_version

    assert cluster_policy_version(ClusterPolicy()) == "qbus_news_cluster.v3"
    assert " + " not in cluster_policy_version(
        ClusterPolicy(title_threshold=0.9)
    )


def test_velocity_with_members_only_reads_unknown_policy(tmp_path):
    db = tmp_path / "members-only.sqlite3"
    _clustered_store(db)
    pristine = tmp_path / "pristine.sqlite3"
    shutil.copyfile(db, pristine)
    expected = _velocity(pristine)
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DROP TABLE news_clusters")
        conn.commit()
    finally:
        conn.close()
    _checkpoint(db)
    got = _velocity(db)
    assert set(got) == set(expected)
    assert got["stories_24h"] == 1
    assert got["cluster_policy_versions_24h"] == [
        UNKNOWN_CLUSTER_POLICY_VERSION
    ]


def test_velocity_without_any_cluster_tables_returns_empty_versions(tmp_path):
    db = tmp_path / "no-cluster-tables.sqlite3"
    _clustered_store(db)
    pristine = tmp_path / "pristine-both.sqlite3"
    shutil.copyfile(db, pristine)
    expected = _velocity(pristine)
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DROP TABLE news_cluster_members")
        conn.execute("DROP TABLE news_clusters")
        conn.commit()
    finally:
        conn.close()
    _checkpoint(db)
    got = _velocity(db)
    assert set(got) == set(expected)
    assert got["cluster_policy_versions_24h"] == []
    assert got["stories_24h"] == got["count_24h"]


def test_velocity_without_members_table_returns_empty_versions(tmp_path):
    db = tmp_path / "no-members-table.sqlite3"
    _clustered_store(db)
    pristine = tmp_path / "pristine-members.sqlite3"
    shutil.copyfile(db, pristine)
    expected = _velocity(pristine)
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DROP TABLE news_cluster_members")
        conn.commit()
    finally:
        conn.close()
    _checkpoint(db)
    got = _velocity(db)
    assert set(got) == set(expected)
    assert got["cluster_policy_versions_24h"] == []
    assert got["stories_24h"] == got["count_24h"]


def _delete_meta_policy_key(db: Path) -> None:
    """Drop the recorded policy key: a store written before it existed."""
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute(
            "DELETE FROM qbus_meta WHERE key=?", (_META_CLUSTER_POLICY_KEY,)
        )
        conn.commit()
    finally:
        conn.close()
    _checkpoint(db)


def test_empty_window_readonly_reads_recorded_writer_policy(tmp_path):
    """No policy passed: the flow names the version the writer recorded."""
    db = tmp_path / "recorded-custom.sqlite3"
    custom = ClusterPolicy(title_threshold=0.9)
    with NewsStore(
        db, source_key="benzinga-rest", cluster_policy=custom
    ) as store:
        store.commit([], expected_cursor=None, next_cursor="c0")
    _checkpoint(db)
    flow = _flow(db)
    assert flow["stories_24h"] == 0
    assert _versions_24h(db) == []
    assert (
        flow["provenance"]["cluster_policy_version"]
        == cluster_policy_version(custom)
    )


def test_empty_window_without_recorded_policy_reads_unknown(tmp_path):
    """A pre-change store (no recorded key) reports unknown, never v2."""
    db = tmp_path / "pre-key.sqlite3"
    with NewsStore(db, source_key="benzinga-rest") as store:
        store.commit([], expected_cursor=None, next_cursor="c0")
    _delete_meta_policy_key(db)
    flow = _flow(db)
    assert flow["stories_24h"] == 0
    assert _versions_24h(db) == []
    assert (
        flow["provenance"]["cluster_policy_version"]
        == UNKNOWN_CLUSTER_POLICY_VERSION
    )


def test_empty_window_default_writer_reads_v2(tmp_path):
    """Every production writer uses the default policy, so v2 is recorded."""
    db = tmp_path / "recorded-default.sqlite3"
    with NewsStore(db, source_key="benzinga-rest") as store:
        store.commit([], expected_cursor=None, next_cursor="c0")
    _checkpoint(db)
    flow = _flow(db)
    assert flow["stories_24h"] == 0
    assert _versions_24h(db) == []
    assert flow["provenance"]["cluster_policy_version"] == CLUSTER_POLICY_VERSION


def test_long_lived_readonly_handle_sees_key_recorded_later(tmp_path):
    """The key is read at call time, not cached at open."""
    db = tmp_path / "late-key.sqlite3"
    with NewsStore(db, source_key="benzinga-rest") as store:
        store.commit([], expected_cursor=None, next_cursor="c0")
    _delete_meta_policy_key(db)
    ro = NewsStore.open_readonly(db, source_key="benzinga-rest")
    try:
        with NewsStore(
            db,
            source_key="benzinga-rest",
            cluster_policy=ClusterPolicy(title_threshold=0.9),
        ) as store:
            store.commit([], expected_cursor="c0", next_cursor="c1")
        flow = ro.news_flow(SEC, now=NOW, rights=_rights())
    finally:
        ro.close()
    assert flow["stories_24h"] == 0
    assert (
        flow["provenance"]["cluster_policy_version"]
        == cluster_policy_version(ClusterPolicy(title_threshold=0.9))
    )


def test_writer_records_policy_idempotently(tmp_path):
    """Two default writer opens leave one row and rewrite nothing."""
    db = tmp_path / "meta-idempotent.sqlite3"
    first = NewsStore(db, source_key="benzinga-rest")
    first.close()
    _checkpoint(db)
    second = NewsStore(db, source_key="benzinga-rest")
    try:
        unchanged_value_changes = second._conn.total_changes
    finally:
        second.close()
    assert unchanged_value_changes == 0
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT value FROM qbus_meta WHERE key=?", (_META_CLUSTER_POLICY_KEY,)
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 1
    assert str(rows[0][0]) == CLUSTER_POLICY_VERSION
