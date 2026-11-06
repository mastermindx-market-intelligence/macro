"""Store-level ticker_news.flow.v1 contract tests. Hermetic: fixtures only."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
import re
import sqlite3
from pathlib import Path

import pytest

from engine.qbus_news_cluster import CLUSTER_POLICY_VERSION
from engine.qbus_news_contract import normalize_news
from engine.qbus_news_store import (
    NewsReadRights,
    NewsStore,
    RoutedRevision,
    StoreValidationError,
)
from engine.qbus_news_velocity import METHOD, SCHEMA as VELOCITY_SCHEMA


UTC = timezone.utc
NOW = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
T0 = NOW - timedelta(minutes=30)

FLOW_SCHEMA = "ticker_news.flow.v1"
FLOW_KEYS = (
    "schema",
    "state",
    "reason",
    "coverage",
    "as_of",
    "reports_24h",
    "reports_7d",
    "stories_24h",
    "median_daily_28d",
    "daily_counts_28d",
    "history_days_observed",
    "comparison",
    "provenance",
)
FLOW_NO_ACCESS = {
    "schema": FLOW_SCHEMA,
    "state": "unavailable",
    "reason": "no_accessible_sources",
    "coverage": "complete",
    "as_of": None,
    "reports_24h": None,
    "reports_7d": None,
    "stories_24h": None,
    "median_daily_28d": None,
    "daily_counts_28d": None,
    "history_days_observed": None,
    "comparison": None,
    "provenance": None,
}


def _new_db(tmp_path: Path) -> Path:
    db = tmp_path / "news.sqlite3"
    with NewsStore(db, source_key="benzinga-live"):
        pass
    _checkpoint(db)
    return db


def _checkpoint(db: Path) -> None:
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()


def _writer(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _insert(
    conn: sqlite3.Connection,
    *,
    security_id: str,
    item_id: str,
    published: datetime | None,
    received: datetime,
    status: str = "active",
    source: str = "benzinga",
) -> None:
    source_item_id = str(item_id)
    revision_id = f"rev-{source}-{source_item_id}-{status}"
    published_text = None if published is None else published.astimezone(UTC).isoformat()
    received_text = received.astimezone(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO news_revisions(
            revision_id, source, source_item_id, identity_json, revision_json
        ) VALUES(?,?,?,?,?)
        """,
        (revision_id, source, source_item_id, "{}", "{}"),
    )
    conn.execute(
        """
        INSERT INTO news_states(
            source, source_item_id, current_revision_id, status,
            state_json, last_sequence, universe_revision
        ) VALUES(?,?,?,?,?,?,?)
        """,
        (source, source_item_id, revision_id, status, "{}", 1, "u1"),
    )
    conn.execute(
        """
        INSERT INTO news_state_projection(
            source, source_item_id, title, url, teaser,
            published_at, updated_at, received_at
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            source,
            source_item_id,
            f"title {source_item_id}",
            f"https://example.invalid/{source_item_id}",
            "",
            published_text,
            published_text,
            received_text,
        ),
    )
    conn.execute(
        """
        INSERT INTO news_security_index(security_id, source, source_item_id)
        VALUES(?,?,?)
        """,
        (security_id, source, source_item_id),
    )


def _close_writer(conn: sqlite3.Connection, db: Path) -> None:
    conn.commit()
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()
    _checkpoint(db)


def _cluster(
    conn: sqlite3.Connection,
    cluster_id: str,
    members: tuple[tuple[str, str], ...],
) -> None:
    """One news_clusters row plus one member row per (source, source_item_id)."""
    conn.execute(
        """
        INSERT INTO news_clusters(
            cluster_id, anchor_story_id, anchor_title,
            anchor_observed_at, subject_ids_json, event_family
        ) VALUES(?,?,?,?,?,?)
        """,
        (
            cluster_id,
            f"{cluster_id}:anchor",
            f"title {cluster_id}",
            "2026-10-12T00:00:00+00:00",
            "[]",
            "news",
        ),
    )
    for source, source_item_id in members:
        conn.execute(
            """
            INSERT INTO news_cluster_members(
                source, source_item_id, cluster_id, story_id
            ) VALUES(?,?,?,?)
            """,
            (source, source_item_id, cluster_id, cluster_id),
        )


def _routed(item_id=1, title="Nvidia launches accelerator", minute=0):
    """RoutedRevision commit idiom copied from tests/test_ticker_news_api.py."""
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
        security_ids=("SEC:US-XNAS-NVDA",),
        universe_revision="sp500-r1",
    )


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _strings_all_non_empty(node: object) -> bool:
    if isinstance(node, str):
        return bool(node)
    if isinstance(node, dict):
        return all(_strings_all_non_empty(v) for v in node.values())
    if isinstance(node, list):
        return all(_strings_all_non_empty(v) for v in node)
    return True


def _has_no_label_key(node: object) -> bool:
    if isinstance(node, dict):
        if "label" in node:
            return False
        return all(_has_no_label_key(v) for v in node.values())
    if isinstance(node, list):
        return all(_has_no_label_key(v) for v in node)
    return True


def _valid_flow(flow: object) -> bool:
    """Contract section 4, rule by rule. Never raises."""
    if not isinstance(flow, dict):
        return False
    if list(flow) != list(FLOW_KEYS):
        return False
    if flow["schema"] != FLOW_SCHEMA:
        return False
    if flow["state"] not in ("ok", "thin_history", "unavailable"):
        return False
    if flow["reason"] not in (None, "no_accessible_sources", "calculation_failed"):
        return False
    if flow["coverage"] not in ("complete", "partial"):
        return False

    if flow["state"] == "unavailable":
        if flow["reason"] is None:
            return False
        if flow["coverage"] != "complete":
            return False
        for key in FLOW_KEYS:
            if key in ("schema", "state", "reason", "coverage"):
                continue
            if flow[key] is not None:
                return False
        return True

    if flow["reason"] is not None:
        return False
    if not isinstance(flow["as_of"], str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", flow["as_of"]
    ):
        return False
    for key in ("reports_24h", "reports_7d", "stories_24h"):
        if not _is_int(flow[key]) or flow[key] < 0:
            return False
    daily = flow["daily_counts_28d"]
    if not isinstance(daily, list) or len(daily) != 28:
        return False
    if not all(_is_int(v) and v >= 0 for v in daily):
        return False
    if (
        not _is_int(flow["history_days_observed"])
        or not 0 <= flow["history_days_observed"] <= 28
    ):
        return False
    if flow["stories_24h"] > flow["reports_24h"]:
        return False
    if flow["reports_24h"] > flow["reports_7d"]:
        return False

    provenance = flow["provenance"]
    if not isinstance(provenance, dict):
        return False
    if set(provenance) != {
        "velocity_schema",
        "sources_counted",
        "status_counted",
        "distinct_by",
        "story_grouping",
        "cluster_policy_version",
        "windows",
        "calculation",
        "time_basis_counts_24h",
    }:
        return False
    if not _strings_all_non_empty(provenance):
        return False
    sources = provenance["sources_counted"]
    if not isinstance(sources, list) or not sources:
        return False
    if not all(isinstance(s, str) and s for s in sources):
        return False
    windows = provenance["windows"]
    if not isinstance(windows, dict):
        return False
    if set(windows) != {"reports_24h", "reports_7d", "daily_28d"}:
        return False
    daily_window = windows["daily_28d"]
    if not isinstance(daily_window, dict) or set(daily_window) != {
        "start_date",
        "end_date",
        "unit",
        "excludes",
        "order",
    }:
        return False
    calculation = provenance["calculation"]
    if not isinstance(calculation, dict) or set(calculation) != {
        "method",
        "comparison_rule",
    }:
        return False
    basis = provenance["time_basis_counts_24h"]
    if not isinstance(basis, dict) or set(basis) != {"published_at", "received_at"}:
        return False
    if basis["published_at"] + basis["received_at"] != flow["reports_24h"]:
        return False

    if flow["state"] == "ok":
        if flow["history_days_observed"] < 20:
            return False
        median = flow["median_daily_28d"]
        if isinstance(median, bool) or not isinstance(median, (int, float)):
            return False
        if not math.isfinite(median) or median < 0:
            return False
        if flow["coverage"] == "complete" and flow["comparison"] not in (
            "busier",
            "typical",
            "quieter",
        ):
            return False
        if flow["coverage"] == "partial" and flow["comparison"] is not None:
            return False
    else:
        if flow["history_days_observed"] > 19:
            return False
        if flow["median_daily_28d"] is not None:
            return False
        if flow["coverage"] == "complete" and flow["comparison"] != (
            "insufficient_history"
        ):
            return False
        if flow["coverage"] == "partial" and flow["comparison"] is not None:
            return False
    return True


def test_news_flow_runs_on_query_only_connection(tmp_path, monkeypatch):
    db = _new_db(tmp_path)
    conn = _writer(db)
    recent = NOW - timedelta(hours=1)
    _insert(
        conn,
        security_id="SEC:US-XNAS-NVDA",
        item_id="f1",
        published=recent,
        received=recent,
    )
    _close_writer(conn, db)

    store = NewsStore(db, source_key="benzinga-rest")
    try:
        before = store._conn.total_changes
        recorded = []
        original = NewsStore._open_flow_connection

        def spy(self):
            flow_conn = original(self)
            recorded.append(flow_conn)
            assert flow_conn.execute("PRAGMA query_only").fetchone()[0] == 1
            with pytest.raises(sqlite3.OperationalError):
                flow_conn.execute(
                    "INSERT INTO qbus_meta(key,value) VALUES('spy','1')"
                )
            return flow_conn

        monkeypatch.setattr(NewsStore, "_open_flow_connection", spy)
        flow = store.news_flow(
            "SEC:US-XNAS-NVDA",
            now=NOW,
            rights=NewsReadRights(allowed_sources=frozenset({"benzinga"})),
        )
        assert flow["state"] in ("ok", "thin_history")
        assert len(recorded) == 1
        assert recorded[0] is not store._conn
        with pytest.raises(sqlite3.ProgrammingError):
            recorded[0].execute("SELECT 1").fetchall()
        assert store._conn.total_changes == before
    finally:
        store.close()


def test_snapshot_source_count_respects_rights(tmp_path):
    """PIN: snapshot source_count/item_count count only rights-visible members."""
    db = tmp_path / "pin.sqlite3"
    with NewsStore(db, source_key="benzinga-rest") as store:
        store.commit(
            [_routed(item_id=1, title="Acme wins large bridge contract", minute=0)],
            expected_cursor=None,
            next_cursor="c1",
        )

    # normalize_news can only mint source 'benzinga'
    # (engine/qbus_news_contract.py hard-codes it), so the restricted member
    # row is added by direct SQL into the benzinga cluster: the packet's
    # sanctioned UPDATE-fallback shape, as an INSERT of that one member row.
    conn = _writer(db)
    rows = conn.execute(
        """
        SELECT m.cluster_id, m.story_id
        FROM news_cluster_members m
        WHERE m.source='benzinga'
        """
    ).fetchall()
    assert len(rows) == 1
    cluster_id = str(rows[0][0])
    story_id = str(rows[0][1])
    recent = NOW - timedelta(minutes=20)
    _insert(
        conn,
        security_id="SEC:US-XNAS-NVDA",
        item_id="w1",
        published=recent,
        received=recent,
        source="restricted_wire",
    )
    conn.execute(
        """
        INSERT INTO news_cluster_members(
            source, source_item_id, cluster_id, story_id
        ) VALUES(?,?,?,?)
        """,
        ("restricted_wire", "w1", cluster_id, story_id),
    )
    conn.commit()
    total = conn.execute(
        "SELECT count(*) FROM news_cluster_members WHERE cluster_id=?",
        (cluster_id,),
    ).fetchone()[0]
    distinct_sources = conn.execute(
        "SELECT count(DISTINCT source) FROM news_cluster_members WHERE cluster_id=?",
        (cluster_id,),
    ).fetchone()[0]
    assert total == 2
    assert distinct_sources == 2
    _close_writer(conn, db)

    store = NewsStore(db, source_key="benzinga-rest")
    try:
        benzinga_rows = store.snapshot(
            "SEC:US-XNAS-NVDA",
            limit=50,
            cursor=None,
            rights=NewsReadRights(allowed_sources=frozenset({"benzinga"})),
        ).rows
        assert len(benzinga_rows) == 1
        assert benzinga_rows[0].item_count == 1
        assert benzinga_rows[0].source_count == 1

        both_rows = store.snapshot(
            "SEC:US-XNAS-NVDA",
            limit=50,
            cursor=None,
            rights=NewsReadRights(
                allowed_sources=frozenset({"benzinga", "restricted_wire"})
            ),
        ).rows
        assert len(both_rows) == 1
        assert both_rows[0].item_count == 2
        assert both_rows[0].source_count == 2
    finally:
        store.close()


def test_news_flow_shape_matches_contract(tmp_path):
    from engine.qbus_news_velocity import compare_to_typical

    day = NOW.date()
    first_day = day - timedelta(days=28)
    db = _new_db(tmp_path / "full")
    conn = _writer(db)
    item = 0
    for offset in range(28):
        d = first_day + timedelta(days=offset)
        when = datetime(d.year, d.month, d.day, 9, 0, tzinfo=UTC)
        copies = 2 if offset < 14 else 3
        for copy in range(copies):
            item += 1
            _insert(
                conn,
                security_id="SEC:US-XNAS-NVDA",
                item_id=f"d{item}",
                published=when,
                received=when,
            )
    _close_writer(conn, db)

    rights = NewsReadRights(allowed_sources=frozenset({"benzinga"}))
    store = NewsStore(db, source_key="benzinga-rest")
    try:
        flow = store.news_flow("SEC:US-XNAS-NVDA", now=NOW, rights=rights)
    finally:
        store.close()

    assert list(flow) == list(FLOW_KEYS)
    assert flow["schema"] == FLOW_SCHEMA
    assert flow["state"] == "ok"
    assert flow["reason"] is None
    assert flow["coverage"] == "complete"
    assert flow["history_days_observed"] == 28
    assert flow["median_daily_28d"] == 2.5
    assert flow["daily_counts_28d"] == [2] * 14 + [3] * 14
    assert flow["reports_24h"] == 0
    assert flow["reports_7d"] == sum(flow["daily_counts_28d"][22:])
    assert flow["stories_24h"] == 0
    assert flow["comparison"] == compare_to_typical(
        flow["reports_24h"], 2.5, True, "complete"
    )
    expected_provenance = {
        "velocity_schema": VELOCITY_SCHEMA,
        "sources_counted": ["benzinga"],
        "status_counted": "active",
        "distinct_by": "source + source_item_id",
        "story_grouping": (
            "news_cluster_members.cluster_id; "
            "a report in no cluster is its own story"
        ),
        "cluster_policy_version": CLUSTER_POLICY_VERSION,
        "windows": {
            "reports_24h": "rolling, closed at both ends: [as_of - 24h, as_of]",
            "reports_7d": "rolling, closed at both ends: [as_of - 7d, as_of]",
            "daily_28d": {
                "start_date": (day - timedelta(days=28)).isoformat(),
                "end_date": (day - timedelta(days=1)).isoformat(),
                "unit": "UTC calendar day",
                "excludes": "the current UTC day",
                "order": "oldest first",
            },
        },
        "calculation": {"method": METHOD, "comparison_rule": "flow_compare.v1"},
        "time_basis_counts_24h": {
            "published_at": flow["reports_24h"],
            "received_at": 0,
        },
    }
    assert flow["provenance"] == expected_provenance
    assert _has_no_label_key(flow)
    assert _valid_flow(flow)

    thin = _new_db(tmp_path / "thin")
    conn = _writer(thin)
    first = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)
    _insert(
        conn,
        security_id="SEC:US-XNAS-NVDA",
        item_id="t1",
        published=first,
        received=first,
    )
    _close_writer(conn, thin)

    store = NewsStore(thin, source_key="benzinga-rest")
    try:
        thin_flow = store.news_flow("SEC:US-XNAS-NVDA", now=NOW, rights=rights)
    finally:
        store.close()
    assert thin_flow["state"] == "thin_history"
    assert thin_flow["history_days_observed"] == 6
    assert thin_flow["median_daily_28d"] is None
    assert thin_flow["comparison"] == "insufficient_history"
    assert _valid_flow(thin_flow)


def test_news_flow_no_access_returns_unavailable_without_connection(
    tmp_path, monkeypatch
):
    db = _new_db(tmp_path)
    store = NewsStore(db, source_key="benzinga-rest")
    try:
        calls = []
        monkeypatch.setattr(
            NewsStore,
            "_open_flow_connection",
            lambda self: calls.append(True),
            raising=False,
        )
        flow = store.news_flow(
            "SEC:US-XNAS-NVDA",
            now=NOW,
            rights=NewsReadRights(allowed_sources=frozenset()),
        )
        assert flow == FLOW_NO_ACCESS
        assert calls == []
    finally:
        store.close()


def test_news_flow_rejects_bad_inputs(tmp_path):
    db = _new_db(tmp_path)
    store = NewsStore(db, source_key="benzinga-rest")
    try:
        rights = NewsReadRights(allowed_sources=frozenset({"benzinga"}))
        with pytest.raises(StoreValidationError) as excinfo:
            store.news_flow(
                "SEC:US-XNAS-NVDA",
                now=NOW,
                rights=frozenset({"benzinga"}),
            )
        assert str(excinfo.value) == "qbus_news_store:invalid_rights"
        with pytest.raises(ValueError):
            store.news_flow(
                "SEC:US-XNAS-NVDA",
                now=datetime(2026, 10, 12, 12, 0),
                rights=rights,
            )
        with pytest.raises(StoreValidationError):
            store.news_flow("", now=NOW, rights=rights)
    finally:
        store.close()


def test_news_flow_as_of_truncated_to_seconds(tmp_path, monkeypatch):
    from engine import qbus_news_store as store_mod

    db = _new_db(tmp_path)
    conn = _writer(db)
    recent = NOW - timedelta(hours=1)
    _insert(
        conn,
        security_id="SEC:US-XNAS-NVDA",
        item_id="f1",
        published=recent,
        received=recent,
    )
    _close_writer(conn, db)

    store = NewsStore(db, source_key="benzinga-rest")
    try:
        recorded = {}
        original = store_mod.compute_news_velocity

        def wrapper(conn, *, security_id, now, allowed_sources, curated=False, allowed_url_sources=(), **reader_options):
            recorded["now"] = now
            return original(
                conn,
                security_id=security_id,
                now=now,
                allowed_sources=allowed_sources,
                curated=curated,
                allowed_url_sources=allowed_url_sources,
                **reader_options,
            )

        monkeypatch.setattr(store_mod, "compute_news_velocity", wrapper)
        flow = store.news_flow(
            "SEC:US-XNAS-NVDA",
            now=NOW.replace(microsecond=654321),
            rights=NewsReadRights(allowed_sources=frozenset({"benzinga"})),
        )
    finally:
        store.close()

    assert recorded["now"].microsecond == 0
    assert recorded["now"].tzinfo is not None
    served = datetime.strptime(flow["as_of"], "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=UTC
    )
    assert served == recorded["now"]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", flow["as_of"])


def test_news_flow_matches_snapshot_rows_under_rights(tmp_path):
    """G1 parity at the store level: flow counts match the visible rows."""
    db = tmp_path / "parity.sqlite3"
    titles = (
        "Nvidia launches accelerator",
        "TSMC beats monthly sales estimates",
        "Eurobond deal priced in Paris",
    )
    with NewsStore(db, source_key="benzinga-rest") as store:
        cursor = None
        for index, title in enumerate(titles):
            next_cursor = f"c{index + 1}"
            store.commit(
                [_routed(item_id=index + 1, title=title, minute=index * 10)],
                expected_cursor=cursor,
                next_cursor=next_cursor,
            )
            cursor = next_cursor

    conn = _writer(db)
    recent = T0 + timedelta(minutes=15)
    _insert(
        conn,
        security_id="SEC:US-XNAS-NVDA",
        item_id="w1",
        published=recent,
        received=recent,
        source="restricted_wire",
    )
    conn.commit()
    indexed = conn.execute(
        """
        SELECT count(*) FROM news_security_index
        WHERE security_id='SEC:US-XNAS-NVDA' AND source='restricted_wire'
        """
    ).fetchone()[0]
    assert indexed == 1
    _close_writer(conn, db)

    store = NewsStore(db, source_key="benzinga-rest")
    try:
        rights = NewsReadRights(allowed_sources=frozenset({"benzinga"}))
        snap = store.snapshot(
            "SEC:US-XNAS-NVDA", limit=50, cursor=None, rights=rights
        )
        rows = snap.rows
        assert len(rows) == 3
        assert all(row.item_count == 1 for row in rows)
        flow = store.news_flow("SEC:US-XNAS-NVDA", now=NOW, rights=rights)
        assert flow["reports_24h"] == sum(row.item_count for row in rows) == 3
        assert flow["stories_24h"] == len(rows)
        assert flow["provenance"]["sources_counted"] == ["benzinga"]
    finally:
        store.close()
