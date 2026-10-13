"""Read-only ticker-news inventory. Hermetic: store commit APIs and tmp files only."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import os
import re
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

import pytest

from engine.qbus_news_contract import normalize_news
from engine.qbus_news_receipts import load_health_receipt
from engine.qbus_news_store import NewsStore, RoutedRevision
from scripts import ticker_news_inventory as inventory
from scripts.qbus_news_cluster_audit import audit_store


UTC = timezone.utc
T0 = datetime(2026, 10, 5, 2, 0, tzinfo=UTC)
NOW = datetime(2026, 10, 5, 22, 0, tzinfo=UTC)
TITLE = "ZXQ-TITLE-sentinel-9f3c"
TEASER = "ZXQ-TEASER-sentinel-9f3c"
URL = "https://example.invalid/zxq-url-sentinel-9f3c"
BODY = "ZXQ-BODY-sentinel-9f3c"
REPO_ROOT = Path(__file__).resolve().parents[1]

_CONTENT_KEYS = frozenset({
    "title",
    "teaser",
    "url",
    "body",
    "delivery_json",
    "anchor_title",
    "state_json",
    "revision_json",
    "row_json",
})


def _stamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _rest_payload(*, item_id: int, updated: datetime, tickers: tuple[str, ...] = ("NVDA",)) -> dict:
    published = updated - timedelta(seconds=1)
    return {
        "id": item_id,
        "created": _stamp(published),
        "updated": _stamp(updated),
        "title": TITLE,
        "teaser": TEASER,
        "body": BODY,
        "url": URL,
        "channels": [{"name": "News"}],
        "stocks": [{"name": ticker} for ticker in tickers],
        "tags": [{"name": "breaking"}],
    }


def _ws_payload(*, item_id: int, message_id: str, event: datetime) -> dict:
    return {
        "id": message_id,
        "api_version": "websocket/v1",
        "kind": "news",
        "data": {
            "action": "Deleted",
            "id": item_id,
            "timestamp": _stamp(event),
        },
    }


def _alpaca_payload(*, item_id: int, updated: datetime) -> dict:
    return {
        "id": item_id,
        "headline": TITLE,
        "author": "Desk",
        "created_at": _stamp(updated - timedelta(seconds=1)),
        "updated_at": _stamp(updated),
        "summary": TEASER,
        "content": BODY,
        "url": URL,
        "symbols": ["AAPL"],
        "source": "benzinga",
    }


def _massive_payload(*, item_id: int, updated: datetime) -> dict:
    return {
        "benzinga_id": item_id,
        "published": _stamp(updated - timedelta(seconds=1)),
        "last_updated": _stamp(updated),
        "title": TITLE,
        "teaser": TEASER,
        "body": BODY,
        "url": URL,
        "channels": ["News"],
        "tickers": ["NVDA"],
        "tags": ["breaking"],
    }


def _routed(revision, security_ids: tuple[str, ...]) -> RoutedRevision:
    return RoutedRevision(
        revision=revision,
        security_ids=security_ids,
        universe_revision="sp500-r1",
    )


def _commit(store: NewsStore, routed: RoutedRevision, *, expected: str | None, nxt: str | None):
    return store.commit((routed,), expected_cursor=expected, next_cursor=nxt)


def _empty_store(tmp_path: Path) -> Path:
    db = tmp_path / "qbus.sqlite3"
    with NewsStore(db, source_key="benzinga-rest"):
        pass
    return db


def _mixed_store(tmp_path: Path) -> tuple[Path, datetime, datetime, datetime, datetime]:
    """Two REST deliveries, one WS withdrawal, one Alpaca REST delivery.

    Item 1 is routed to two securities so ``news_change_targets`` outnumbers
    ``news_changes``. Item 1 is later withdrawn. Alpaca uses another cursor
    namespace on the same file.
    """

    db = tmp_path / "qbus.sqlite3"
    rest_early = T0 + timedelta(seconds=5)
    rest_late = T0 + timedelta(minutes=10, seconds=5)
    withdrawn_at = T0 + timedelta(minutes=20)
    alpaca_at = T0 + timedelta(minutes=30, seconds=5)
    with NewsStore(db, source_key="benzinga-rest") as store:
        _commit(
            store,
            _routed(
                normalize_news(
                    _rest_payload(item_id=101, updated=T0),
                    transport="benzinga_rest",
                    received_at=rest_early,
                ),
                ("sec-NVDA", "sec-AMD"),
            ),
            expected=None,
            nxt="cursor-rest-1",
        )
        _commit(
            store,
            _routed(
                normalize_news(
                    _rest_payload(item_id=202, updated=T0 + timedelta(minutes=10), tickers=("MSFT",)),
                    transport="benzinga_rest",
                    received_at=rest_late,
                ),
                ("sec-MSFT",),
            ),
            expected="cursor-rest-1",
            nxt="cursor-rest-2",
        )
        _commit(
            store,
            _routed(
                normalize_news(
                    _ws_payload(item_id=101, message_id="msg-delete-101", event=withdrawn_at),
                    transport="benzinga_ws",
                    received_at=withdrawn_at + timedelta(seconds=1),
                ),
                (),
            ),
            expected="cursor-rest-2",
            nxt="cursor-rest-2",
        )
    with NewsStore(db, source_key="alpaca-rest") as store:
        _commit(
            store,
            _routed(
                normalize_news(
                    _alpaca_payload(item_id=303, updated=T0 + timedelta(minutes=30)),
                    transport="alpaca_rest",
                    received_at=alpaca_at,
                ),
                ("sec-AAPL",),
            ),
            expected=None,
            nxt="cursor-alpaca-1",
        )
    return db, rest_early, rest_late, withdrawn_at + timedelta(seconds=1), alpaca_at


def _invoke(capsys, database: Path | str, *extra: str) -> tuple[int, str]:
    rc = inventory.main(["--database", str(database), "--now", NOW.isoformat(), *extra])
    captured = capsys.readouterr()
    assert captured.err == ""
    return rc, captured.out


def _keys(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _keys(child)


def _snapshot(path: Path) -> tuple[bytes, int, int]:
    stat = path.stat()
    return path.read_bytes(), stat.st_mtime_ns, stat.st_mode


def test_missing_database_is_not_created(tmp_path, capsys):
    missing = tmp_path / "nested" / "absent.sqlite3"

    rc, out = _invoke(capsys, missing)

    assert rc == 2
    assert out == '{"error":"database_missing"}\n'
    assert not missing.exists()
    assert not missing.parent.exists()


def test_non_sqlite_file_is_left_unchanged(tmp_path, capsys):
    db = tmp_path / "not-a-store.sqlite3"
    db.write_bytes(b"not a database")
    before = _snapshot(db)

    rc, out = _invoke(capsys, db)

    assert rc == 2
    assert json.loads(out) == {"error": "database_unreadable"}
    assert _snapshot(db) == before


def test_schema_mismatch_does_not_rewrite_the_file(tmp_path, capsys):
    db = _empty_store(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE qbus_meta SET value='other' WHERE key='schema'")
    before = _snapshot(db)

    rc, out = _invoke(capsys, db)

    assert rc == 2
    assert json.loads(out) == {"error": "schema_mismatch"}
    assert _snapshot(db) == before


def test_read_only_run_preserves_database_bytes_and_mtime(tmp_path, capsys):
    db, *_times = _mixed_store(tmp_path)
    before = _snapshot(db)

    rc, out = _invoke(capsys, db, "--json")

    assert rc == 0
    assert json.loads(out)["schema"] == inventory.SCHEMA
    assert _snapshot(db) == before


def test_read_only_run_leaves_live_wal_files_unchanged(tmp_path, capsys):
    """A live writer keeps commits in the WAL. immutable=1 would miss them."""

    db = tmp_path / "qbus.sqlite3"
    store = NewsStore(db, source_key="benzinga-rest")
    try:
        revision = normalize_news(
            _rest_payload(item_id=55, updated=T0),
            transport="benzinga_rest",
            received_at=T0 + timedelta(seconds=5),
        )
        _commit(store, _routed(revision, ("sec-NVDA",)), expected=None, nxt="c1")
        before = {path: _snapshot(path) for path in tmp_path.iterdir()}
        assert (db.parent / (db.name + "-wal")) in before

        rc, out = _invoke(capsys, db)
        report = json.loads(out)

        assert rc == 0
        assert report["rest_catchup_proven"] is True
        assert report["transports"][0]["deliveries"] == 1
        assert {path: _snapshot(path) for path in before} == before
    finally:
        store.close()


def test_empty_store_reports_zeros_and_no_rest_catchup(tmp_path, capsys):
    db = _empty_store(tmp_path)

    rc, out = _invoke(capsys, db)
    report = json.loads(out)

    assert rc == 0
    assert report == {
        "schema": "ticker_news.inventory.v1",
        "generated_at": NOW.isoformat(),
        "database": {"path": "qbus.sqlite3", "bytes": db.stat().st_size},
        "transports": [],
        "totals": {
            "revisions": 0,
            "states": 0,
            "open_states": 0,
            "withdrawn_states": 0,
            "clusters": 0,
            "changes": 0,
        },
        "cursors": [],
        "health": {"state": "unavailable", "reason": "health_path_unset"},
        "universe": {
            "state": "unavailable",
            "reason": "universe_path_unset",
            "known_at": "2026-10-05T22:00:00Z",
        },
        "cluster_summary": {
            "stories": 0,
            "clusters": 0,
            "multi_member_clusters": 0,
            "size_histogram": {},
            "audit": {
                "state": "ran",
                "near_misses_listed": 0,
                "near_miss_list_limit": 50,
                "number_mismatch_pairs": 0,
                "number_mismatch_clusters": 0,
            },
            "known_at": "2026-10-05T22:00:00Z",
        },
        "flow_read_latency": {
            "state": "unavailable",
            "reason": "universe_path_unset",
            "known_at": "2026-10-05T22:00:00Z",
        },
        "rest_catchup_proven": False,
    }


def test_mixed_store_totals_cursors_and_freshness(tmp_path, capsys):
    db, rest_early, rest_late, ws_at, alpaca_at = _mixed_store(tmp_path)

    rc, out = _invoke(capsys, db)
    report = json.loads(out)

    assert rc == 0
    assert report["database"]["path"] == "qbus.sqlite3"
    assert str(tmp_path) not in out
    assert report["generated_at"] == NOW.isoformat()
    assert report["transports"] == [
        {
            "transport": "alpaca_rest",
            "deliveries": 1,
            "first_received_at": alpaca_at.isoformat(),
            "last_received_at": alpaca_at.isoformat(),
        },
        {
            "transport": "benzinga_rest",
            "deliveries": 2,
            "first_received_at": rest_early.isoformat(),
            "last_received_at": rest_late.isoformat(),
        },
        {
            "transport": "benzinga_ws",
            "deliveries": 1,
            "first_received_at": ws_at.isoformat(),
            "last_received_at": ws_at.isoformat(),
        },
    ]
    # 4 revisions (2 rest, 1 withdrawal, 1 alpaca). Item 101 withdrawn, two
    # others still active. Distinct subjects stay in three clusters. One
    # change row per applied commit, including the withdrawal.
    assert report["totals"] == {
        "revisions": 4,
        "states": 3,
        "open_states": 2,
        "withdrawn_states": 1,
        "clusters": 3,
        "changes": 4,
    }
    assert report["cursors"] == [
        {"source_key": "alpaca-rest", "cursor": "cursor-alpaca-1"},
        {"source_key": "benzinga-rest", "cursor": "cursor-rest-2"},
    ]
    assert report["rest_catchup_proven"] is True


def test_output_omits_content_fields(tmp_path, capsys):
    db, *_times = _mixed_store(tmp_path)

    rc, out = _invoke(capsys, db, "--text")
    text_rc, text = rc, out
    json_rc, raw = _invoke(capsys, db)
    report = json.loads(raw)

    assert text_rc == 0
    assert json_rc == 0
    blob = raw + text
    for sentinel in (TITLE, TEASER, URL, BODY):
        assert sentinel not in blob
    assert _CONTENT_KEYS.isdisjoint(_keys(report))
    assert "delivery_json" not in blob
    assert "validated" not in blob.lower()


def test_delivery_count_is_rows_not_distinct_revisions(tmp_path, capsys):
    db = tmp_path / "qbus.sqlite3"
    early = T0 + timedelta(seconds=5)
    late = T0 + timedelta(minutes=3)
    with NewsStore(db, source_key="benzinga-rest") as store:
        revision = normalize_news(
            _rest_payload(item_id=7, updated=T0),
            transport="benzinga_rest",
            received_at=early,
        )
        first = _commit(
            store,
            _routed(revision, ("sec-NVDA",)),
            expected=None,
            nxt="c1",
        )
        second = _commit(
            store,
            _routed(replace(revision, received_at=late), ("sec-NVDA",)),
            expected="c1",
            nxt="c1",
        )

    assert first.inserted_revisions == 1
    assert second.inserted_revisions == 0
    rc, out = _invoke(capsys, db)
    report = json.loads(out)

    assert rc == 0
    assert report["totals"]["revisions"] == 1
    assert report["transports"] == [
        {
            "transport": "benzinga_rest",
            "deliveries": 2,
            "first_received_at": early.isoformat(),
            "last_received_at": late.isoformat(),
        }
    ]


def test_transport_names_stay_literal_and_rest_match_is_case_sensitive(tmp_path, capsys):
    db = tmp_path / "qbus.sqlite3"
    received = T0 + timedelta(seconds=5)
    with NewsStore(db, source_key="benzinga-rest") as store:
        revision = normalize_news(
            _rest_payload(item_id=8, updated=T0),
            transport="benzinga_rest",
            received_at=received,
        )
        _commit(
            store,
            _routed(replace(revision, transport="Benzinga_REST"), ("sec-NVDA",)),
            expected=None,
            nxt="c1",
        )

    rc, out = _invoke(capsys, db)
    report = json.loads(out)

    assert rc == 0
    assert report["transports"] == [
        {
            "transport": "Benzinga_REST",
            "deliveries": 1,
            "first_received_at": received.isoformat(),
            "last_received_at": received.isoformat(),
        }
    ]
    assert report["rest_catchup_proven"] is False


def test_rest_substring_counts_alpaca_and_ignores_ws_and_massive(tmp_path, capsys):
    cases = {
        "benzinga_ws": False,
        "massive_benzinga_v2": False,
        "alpaca_rest": True,
        "benzinga_rest": True,
    }
    for transport, proven in cases.items():
        db = tmp_path / f"{transport}.sqlite3"
        received = T0 + timedelta(seconds=5)
        if transport == "benzinga_ws":
            payload = {
                "id": "msg-created-1",
                "api_version": "websocket/v1",
                "kind": "news",
                "data": {
                    "action": "created",
                    "id": 11,
                    "timestamp": _stamp(T0),
                    "content": {
                        "id": 11,
                        "created": _stamp(T0 - timedelta(seconds=1)),
                        "updated": _stamp(T0),
                        "title": TITLE,
                        "teaser": TEASER,
                        "body": BODY,
                        "url": URL,
                        "channels": [{"name": "News"}],
                        "stocks": [{"name": "NVDA"}],
                        "tags": [],
                    },
                },
            }
        elif transport == "massive_benzinga_v2":
            payload = _massive_payload(item_id=11, updated=T0)
        elif transport == "alpaca_rest":
            payload = _alpaca_payload(item_id=11, updated=T0)
        else:
            payload = _rest_payload(item_id=11, updated=T0)
        with NewsStore(db, source_key="benzinga-rest") as store:
            _commit(
                store,
                _routed(
                    normalize_news(payload, transport=transport, received_at=received),
                    ("sec-NVDA",),
                ),
                expected=None,
                nxt="c1",
            )
        rc, out = _invoke(capsys, db)
        report = json.loads(out)
        assert rc == 0
        assert report["transports"][0]["transport"] == transport
        assert report["rest_catchup_proven"] is proven


def test_cluster_total_counts_cluster_rows_not_members(tmp_path, capsys):
    db = tmp_path / "qbus.sqlite3"
    with NewsStore(db, source_key="benzinga-rest") as store:
        for item_id, minute in ((31, 0), (32, 1)):
            updated = T0 + timedelta(minutes=minute)
            _commit(
                store,
                _routed(
                    normalize_news(
                        _rest_payload(item_id=item_id, updated=updated),
                        transport="benzinga_rest",
                        received_at=updated + timedelta(seconds=5),
                    ),
                    ("sec-NVDA",),
                ),
                expected=None if item_id == 31 else "c1",
                nxt="c1" if item_id == 31 else "c2",
            )

    rc, out = _invoke(capsys, db)
    report = json.loads(out)

    assert rc == 0
    assert report["totals"]["states"] == 2
    assert report["totals"]["clusters"] == 1
    assert report["totals"]["changes"] == 2


def test_changes_count_change_rows_not_security_targets(tmp_path, capsys):
    db = tmp_path / "qbus.sqlite3"
    with NewsStore(db, source_key="benzinga-rest") as store:
        receipt = _commit(
            store,
            _routed(
                normalize_news(
                    _rest_payload(item_id=41, updated=T0),
                    transport="benzinga_rest",
                    received_at=T0 + timedelta(seconds=5),
                ),
                ("sec-AAA", "sec-BBB"),
            ),
            expected=None,
            nxt="c1",
        )

    assert receipt.first_sequence == receipt.last_sequence == 1
    rc, out = _invoke(capsys, db)
    report = json.loads(out)

    assert rc == 0
    assert report["totals"]["changes"] == 1
    assert report["rest_catchup_proven"] is True


def test_health_unset_differs_from_projection_of_a_stale_receipt(tmp_path, capsys):
    db = _empty_store(tmp_path)
    health = tmp_path / "health.json"
    stale = {
        "schema": "qbus.news_health.v1",
        "source": "benzinga",
        "state": "live",
        "observed_at": (NOW - timedelta(minutes=10)).isoformat(),
        "last_successful_catchup": (NOW - timedelta(minutes=10)).isoformat(),
        "last_stream_event_at": None,
        "gap_unresolved": False,
        "connect_attempts": 2,
        "disconnects": 1,
        "catchups_failed": 0,
    }
    health.write_text(json.dumps(stale), encoding="utf-8")
    health_before = health.read_bytes()

    unset_rc, unset_out = _invoke(capsys, db)
    stale_rc, stale_out = _invoke(capsys, db, "--health", str(health))
    unset = json.loads(unset_out)
    projected = json.loads(stale_out)

    assert unset_rc == 0 and stale_rc == 0
    assert unset["health"] == {"state": "unavailable", "reason": "health_path_unset"}
    assert projected["health"] == load_health_receipt(health, now=NOW)
    assert projected["health"]["state"] == "unavailable"
    assert projected["health"]["reason"] == "receipt_stale"
    assert projected["health"]["state"] != stale["state"]
    assert health.read_bytes() == health_before
    assert str(health) not in stale_out


def test_fresh_health_projection_and_zulu_now_are_canonical(tmp_path, capsys):
    db = _empty_store(tmp_path)
    health = tmp_path / "health.json"
    payload = {
        "schema": "qbus.news_health.v1",
        "source": "benzinga",
        "state": "live",
        "observed_at": "2026-10-05T21:59:55+00:00",
        "last_successful_catchup": "2026-10-05T21:59:50+00:00",
        "last_stream_event_at": None,
        "gap_unresolved": False,
        "connect_attempts": 2,
        "disconnects": 1,
        "catchups_failed": 0,
    }
    health.write_text(json.dumps(payload), encoding="utf-8")

    rc = inventory.main([
        "--database", str(db),
        "--health", str(health),
        "--now", "2026-10-05T22:00:00Z",
    ])
    out = capsys.readouterr().out
    report = json.loads(out)

    assert rc == 0
    assert report["generated_at"] == "2026-10-05T22:00:00+00:00"
    assert report["health"] == load_health_receipt(health, now=NOW)
    assert report["health"]["state"] == "live"
    assert report["health"]["reason"] == "fresh"


def test_text_summary_is_bilingual_and_omits_content(tmp_path, capsys):
    db, *_times = _mixed_store(tmp_path)

    rc, out = _invoke(capsys, db, "--text")

    assert rc == 0
    assert "Ticker news inventory / 个股新闻库存" in out
    assert "transports / 传输:" in out
    assert "benzinga_rest: deliveries / 送达数=2" in out
    assert "alpaca-rest: cursor-alpaca-1" in out
    assert "open_states / 在册状态=2" in out
    assert "withdrawn_states / 撤回状态=1" in out
    assert "health / 运行健康: unavailable (health_path_unset)" in out
    assert "rest_catchup_proven / REST补齐已送达: yes / 是" in out
    for sentinel in (TITLE, TEASER, URL, BODY):
        assert sentinel not in out
    assert "validated" not in out.lower()
    assert "<" not in out


def test_invalid_now_does_not_touch_the_database(tmp_path, capsys):
    db = _empty_store(tmp_path)
    before = _snapshot(db)
    missing = tmp_path / "absent.sqlite3"

    rc = inventory.main(["--database", str(db), "--now", "yesterday"])
    out = capsys.readouterr().out
    missing_rc = inventory.main(["--database", str(missing), "--now", "2026-10-05T22:00:00"])
    missing_out = capsys.readouterr().out

    assert rc == 2
    assert json.loads(out) == {"error": "invalid_now"}
    assert _snapshot(db) == before
    assert missing_rc == 2
    assert json.loads(missing_out) == {"error": "invalid_now"}
    assert not missing.exists()


def test_directory_database_is_unreadable_and_not_replaced(tmp_path, capsys):
    db = tmp_path / "qbus.sqlite3"
    db.mkdir()

    rc, out = _invoke(capsys, db)

    assert rc == 2
    assert json.loads(out) == {"error": "database_unreadable"}
    assert db.is_dir()
    assert list(db.iterdir()) == []


def test_direct_script_invocation_reports_missing_database(tmp_path):
    missing = tmp_path / "absent.sqlite3"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/ticker_news_inventory.py",
            "--database",
            str(missing),
            "--now",
            NOW.isoformat(),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        timeout=30,
        check=False,
    )

    assert proc.returncode == 2, proc.stderr
    assert json.loads(proc.stdout.decode("utf-8")) == {"error": "database_missing"}
    assert not missing.exists()


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory modes")
def test_untraversable_store_directory_fails_closed(tmp_path, capsys):
    """A root-owned 0700 state dir must refuse, never traceback (D1)."""

    store = tmp_path / "s"
    store.mkdir()
    db = _empty_store(store)
    before = _snapshot(db)

    store.chmod(0o000)
    try:
        rc, out = _invoke(capsys, db)
    finally:
        store.chmod(0o700)

    assert rc == 2
    assert out == '{"error":"database_unreadable"}\n'
    assert _snapshot(db) == before


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory modes")
def test_untraversable_store_directory_exits_2_without_traceback(tmp_path):
    store = tmp_path / "s"
    store.mkdir()
    db = _empty_store(store)

    store.chmod(0o000)
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/ticker_news_inventory.py",
                "--database",
                str(db),
                "--now",
                NOW.isoformat(),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=30,
            check=False,
        )
    finally:
        store.chmod(0o700)

    assert proc.returncode == 2, proc.stderr
    assert proc.stdout.decode("utf-8") == '{"error":"database_unreadable"}\n'
    assert proc.stderr == b""


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory modes")
def test_health_in_untraversable_directory_still_prints_report(tmp_path, capsys):
    """Pins engine.qbus_news_receipts: an unreadable health dir is not fatal."""

    db = _empty_store(tmp_path)
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    health = receipts / "health.json"

    receipts.chmod(0o000)
    try:
        rc, out = _invoke(capsys, db, "--health", str(health))
    finally:
        receipts.chmod(0o700)

    assert rc == 0
    report = json.loads(out)
    assert report["health"]["state"] == "unavailable"
    assert report["health"]["reason"] == "receipt_missing"
    assert not health.exists()


def test_docs_inventory_section_describes_the_command():
    text = (REPO_ROOT / "docs" / "ops" / "ticker-news.md").read_text(encoding="utf-8")
    section = text.split("## Inventory / 库存", 1)
    assert len(section) == 2
    body = section[1]
    paragraphs = body.split("\n\n")
    cjk = re.compile(r"[一-鿿]")
    assert "scripts/ticker_news_inventory.py" in body
    # mode=ro must be described in English and in Chinese, independently.
    assert any("mode=ro" in p and not cjk.search(p) for p in paragraphs)
    assert any("mode=ro" in p and cjk.search(p) for p in paragraphs)
    assert "rest_catchup_proven" in body
    assert "health_path_unset" in body
    assert "delivery_json" in body
    assert "--store <path>" in body
    en_universe = any(
        not cjk.search(p)
        and "reason_codes" in p
        and "distinct" in p
        and "snapshot-level" in p
        and "not a per-security count" in p
        for p in paragraphs
    )
    zh_universe = any(
        cjk.search(p)
        and "reason_codes" in p
        and "去重" in p
        and "快照级" in p
        and "不是逐证券计数" in p
        for p in paragraphs
    )
    assert en_universe and zh_universe
    label = "in-process, not HTTP / 进程内读取，非 HTTP"
    assert sum(1 for p in paragraphs if label in p) >= 2
    assert "validated" not in body.lower()
    assert "title=" not in body


def test_docs_inventory_section_describes_sidecars_and_root_privilege():
    text = (REPO_ROOT / "docs" / "ops" / "ticker-news.md").read_text(encoding="utf-8")
    section = text.split("## Inventory / 库存", 1)
    assert len(section) == 2
    body = section[1]
    assert "may create empty ones" not in body
    assert "-shm" in body
    assert "32 KiB" in body
    assert "sudo" in body
    assert "database_unreadable" in body
    # The ZH mirror carries the same measured facts.
    assert "32 KiB 的" in body
    assert "仅 root" in body


# --- W11-05: store-API open pin and the universe / cluster / flow sections ---

RIGHTS_FILE = REPO_ROOT / "config" / "ticker_news_rights_alpaca_benzinga.json"
FLOW_NOW = datetime(2026, 10, 12, 15, 0, tzinfo=UTC)
EXPIRED_NOW = datetime(2027, 10, 12, 15, 0, tzinfo=UTC)
KNOWN_AT = "2026-10-12T15:00:00Z"
RANKING_WORDS = (
    "top",
    "most",
    "rank",
    "ranked",
    "best",
    "worst",
    "hot",
    "leader",
    "热门",
    "最多",
    "排名",
    "领先",
)


def _usec(
    sid,
    ticker,
    *,
    aliases=(),
    valid_from=None,
    valid_to=None,
    known_at=None,
    base=FLOW_NOW,
):
    return {
        "security_id": sid,
        "ticker": ticker,
        "aliases": list(aliases) or [ticker],
        "valid_from": _stamp(valid_from or (base - timedelta(days=100))),
        "valid_to": None if valid_to is None else _stamp(valid_to),
        "known_at": _stamp(known_at or (base - timedelta(days=10))),
    }


def _usnap(securities, *, base=FLOW_NOW, **kw):
    payload = {
        "owner": "security_reference.sp500",
        "revision": "sp500-2026-10-12-r1",
        "complete": True,
        "truncated": False,
        "effective_at": _stamp(base - timedelta(days=1)),
        "known_at": _stamp(base - timedelta(hours=2)),
        "fresh_until": _stamp(base + timedelta(days=2)),
        "securities": list(securities),
    }
    payload.update(kw)
    return payload


def _write_universe(tmp_path, securities, *, name="universe.json", base=FLOW_NOW, **kw):
    path = tmp_path / name
    path.write_text(json.dumps(_usnap(securities, base=base, **kw)), encoding="utf-8")
    return path


def _titled_payload(*, item_id, updated, title, ticker):
    payload = _rest_payload(item_id=item_id, updated=updated, tickers=(ticker,))
    payload["title"] = title
    return payload


def _commit_routed(db, routed, *, source_key="benzinga-rest"):
    with NewsStore(db, source_key=source_key) as store:
        return store.commit(routed, expected_cursor=None, next_cursor="c1")


def _flow_store(tmp_path):
    """Six active stories in the 7 days before FLOW_NOW: ZZZ 3, MMM 2, AAA 1."""

    db = tmp_path / "flow.sqlite3"
    plan = (
        ("sec-901", "ZZZ", (9100001, 9100002, 9100003)),
        ("sec-902", "MMM", (9100011, 9100012)),
        ("sec-903", "AAA", (9100021,)),
    )
    routed = []
    for slot, (sid, ticker, item_ids) in enumerate(plan):
        for offset, item_id in enumerate(item_ids):
            updated = FLOW_NOW - timedelta(hours=24 + 6 * slot + offset)
            routed.append(
                RoutedRevision(
                    revision=normalize_news(
                        _rest_payload(item_id=item_id, updated=updated, tickers=(ticker,)),
                        transport="benzinga_rest",
                        received_at=updated + timedelta(seconds=5),
                    ),
                    security_ids=(sid,),
                    universe_revision="sp500-r1",
                )
            )
    _commit_routed(db, routed)
    return db


def _flow_universe(tmp_path, *, name="universe.json", base=FLOW_NOW):
    return _write_universe(
        tmp_path,
        [
            _usec("sec-901", "ZZZ", base=base),
            _usec("sec-902", "MMM", base=base),
            _usec("sec-903", "AAA", base=base),
        ],
        name=name,
        base=base,
    )


def _invoke_flow(capsys, database, universe, rights, *extra, now=FLOW_NOW):
    args = ["--database", str(database), "--now", now.isoformat()]
    if universe is not None:
        args += ["--universe", str(universe)]
    if rights is not None:
        args += ["--rights", str(rights)]
    rc = inventory.main(args + list(extra))
    captured = capsys.readouterr()
    assert captured.err == ""
    return rc, captured.out


def test_inventory_opens_store_through_open_readonly(tmp_path, capsys, monkeypatch):
    db = _flow_store(tmp_path)
    calls = []
    real = NewsStore.open_readonly.__func__

    def spy(cls, *args, **kwargs):
        calls.append((args, kwargs))
        return real(cls, *args, **kwargs)

    monkeypatch.setattr(NewsStore, "open_readonly", classmethod(spy))
    rc, out = _invoke_flow(capsys, db, _flow_universe(tmp_path), RIGHTS_FILE)

    assert rc == 0
    assert json.loads(out)["schema"] == inventory.SCHEMA
    assert len(calls) == 1
    assert calls[0][1].get("source_key") == "ticker-news-inventory"


def test_every_sqlite_connect_is_uri_read_only(tmp_path, capsys, monkeypatch):
    db = _flow_store(tmp_path)
    seen = []
    real = sqlite3.connect

    def wrapped(*args, **kwargs):
        target = str(args[0]) if args else str(kwargs.get("database"))
        assert kwargs.get("uri") is True, (target, kwargs)
        assert "mode=ro" in target, target
        seen.append(target)
        return real(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", wrapped)
    rc, out = _invoke_flow(capsys, db, _flow_universe(tmp_path), RIGHTS_FILE)

    assert rc == 0
    # store open + cluster audit + flow reads
    assert len(seen) >= 3


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores file modes")
def test_report_runs_against_a_0444_copy(tmp_path, capsys):
    db = _flow_store(tmp_path)
    universe = _flow_universe(tmp_path)
    copy = tmp_path / "locked.sqlite3"
    shutil.copyfile(db, copy)
    conn = sqlite3.connect(copy)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("PRAGMA journal_mode=DELETE")
    finally:
        conn.close()
    before = _snapshot(copy)
    copy.chmod(0o444)
    tmp_path.chmod(0o555)
    try:
        rc, out = _invoke_flow(capsys, copy, universe, RIGHTS_FILE)
        after = _snapshot(copy)
        wal = (tmp_path / "locked.sqlite3-wal").exists()
        shm = (tmp_path / "locked.sqlite3-shm").exists()
    finally:
        tmp_path.chmod(0o755)
        copy.chmod(0o644)

    assert rc == 0
    assert json.loads(out)["schema"] == inventory.SCHEMA
    assert after[0] == before[0]
    assert after[1] == before[1]
    assert not wal and not shm


def test_new_sections_omit_titles_ids_and_content(tmp_path, capsys):
    db = _flow_store(tmp_path)
    universe = _flow_universe(tmp_path)
    receipt_id = json.loads(RIGHTS_FILE.read_text(encoding="utf-8"))["receipt_id"]

    json_rc, raw = _invoke_flow(capsys, db, universe, RIGHTS_FILE)
    text_rc, text = _invoke_flow(capsys, db, universe, RIGHTS_FILE, "--text")
    report = json.loads(raw)

    assert json_rc == 0 and text_rc == 0
    blob = raw + text
    for sentinel in (TITLE, TEASER, URL, BODY):
        assert sentinel not in blob
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        story_ids = [
            str(row[0])
            for row in conn.execute("SELECT story_id FROM news_cluster_members")
        ]
        item_ids = [
            str(row[0])
            for row in conn.execute("SELECT source_item_id FROM news_cluster_members")
        ]
        cluster_ids = [
            str(row[0]) for row in conn.execute("SELECT cluster_id FROM news_clusters")
        ]
    finally:
        conn.close()
    for leaked in (*story_ids, *item_ids, *cluster_ids, receipt_id):
        assert leaked not in blob, leaked
    assert _CONTENT_KEYS.isdisjoint(_keys(report))


def test_new_section_text_labels_are_bilingual(tmp_path, capsys):
    db = _flow_store(tmp_path)
    universe = _flow_universe(tmp_path)

    rc, text = _invoke_flow(capsys, db, universe, RIGHTS_FILE, "--text")
    assert rc == 0
    blobs = [text]

    skipped = inventory.build_inventory(
        database=db,
        health=None,
        now=FLOW_NOW,
        universe=universe,
        rights=RIGHTS_FILE,
        audit_cap=1,
    )
    blobs.append(inventory.format_text(skipped))

    broken = tmp_path / "broken.sqlite3"
    shutil.copyfile(db, broken)
    conn = sqlite3.connect(broken)
    try:
        conn.execute("UPDATE news_clusters SET subject_ids_json='not-json'")
        conn.commit()
    finally:
        conn.close()
    failed = inventory.build_inventory(
        database=broken,
        health=None,
        now=FLOW_NOW,
        universe=universe,
        rights=RIGHTS_FILE,
    )
    blobs.append(inventory.format_text(failed))

    unset = inventory.build_inventory(database=db, health=None, now=FLOW_NOW)
    blobs.append(inventory.format_text(unset))

    blob = "\n".join(blobs)
    for label in (
        "universe / 股票池:",
        "qualified/合格",
        "excluded/排除",
        "ambiguous/歧义",
        "revision/版本",
        "asof/截至",
        "unavailable/不可用",
        "clusters / 聚类:",
        "multi-member/多成员",
        "stories/条目",
        "cluster audit / 聚类审计:",
        "near misses/近似未合并",
        "number mismatches/数字不符",
        "pairs/对",
        "clusters/聚类",
        "cluster audit skipped / 聚类审计已跳过:",
        "cap/上限",
        "run/手动运行",
        "cluster audit failed / 聚类审计失败:",
        "flow reads / 流量读取:",
        "over/共",
        "reads/次",
        "tickers / 抽样代码",
        "in-process, not HTTP / 进程内读取，非 HTTP",
    ):
        assert label in blob, label


def test_universe_section_counts_and_reasons(tmp_path, capsys):
    db = _flow_store(tmp_path)

    unset_rc, unset_out = _invoke_flow(capsys, db, None, None)
    assert unset_rc == 0
    assert json.loads(unset_out)["universe"] == {
        "state": "unavailable",
        "reason": "universe_path_unset",
        "known_at": KNOWN_AT,
    }

    garbage = tmp_path / "garbage.json"
    garbage.write_text("not-json{", encoding="utf-8")
    bad_rc, bad_out = _invoke_flow(capsys, db, garbage, None)
    assert bad_rc == 0
    assert json.loads(bad_out)["universe"] == {
        "state": "unavailable",
        "reason": "universe_unreadable",
        "known_at": KNOWN_AT,
    }

    universe = _write_universe(
        tmp_path,
        [
            _usec("sec-901", "ZZZ", aliases=("ZZZ", "DUPX")),
            _usec("sec-902", "MMM", aliases=("MMM", "DUPX")),
            _usec("sec-903", "AAA", valid_to=FLOW_NOW - timedelta(days=1)),
        ],
        name="counts.json",
    )
    rc, out = _invoke_flow(capsys, db, universe, RIGHTS_FILE)

    assert rc == 0
    assert json.loads(out)["universe"] == {
        "state": "held",
        "revision": "sp500-2026-10-12-r1",
        "asof": KNOWN_AT,
        "qualified": 2,
        "excluded": 1,
        "ambiguous_aliases": 1,
        "reason_codes": ["ambiguous_alias"],
        "known_at": KNOWN_AT,
    }


def test_cluster_summary_equals_audit_store(tmp_path, capsys):
    db = tmp_path / "shapes.sqlite3"
    base = FLOW_NOW - timedelta(hours=3)
    rows = (
        (9200001, base, "Zed Corp opens new regional plant", "sec-921"),
        (9200002, base + timedelta(minutes=10), "Zed Corp opens new regional plant", "sec-921"),
        (9200003, base + timedelta(minutes=30), "Yon Ltd wins tender 7 for campus work", "sec-922"),
    )
    routed = [
        RoutedRevision(
            revision=normalize_news(
                _titled_payload(
                    item_id=item_id,
                    updated=updated,
                    title=title,
                    ticker=title.split()[0].upper(),
                ),
                transport="benzinga_rest",
                received_at=updated + timedelta(seconds=5),
            ),
            security_ids=(sid,),
            universe_revision="sp500-r1",
        )
        for item_id, updated, title, sid in rows
    ]
    _commit_routed(db, routed)
    conn = sqlite3.connect(db)
    try:
        conn.execute(
            "INSERT INTO news_clusters(cluster_id, anchor_story_id, anchor_title,"
            " anchor_observed_at, subject_ids_json, event_family)"
            " VALUES('ev2_zero_member_fixture_0000','benzinga:0','unused',?,?,'')",
            (_stamp(base), '["sec-921"]'),
        )
        conn.execute(
            "INSERT INTO news_cluster_members(source, source_item_id, cluster_id, story_id)"
            " VALUES('benzinga','9200099','ev2_orphan_member_fixture_9999','benzinga:9200099')"
        )
        conn.commit()
    finally:
        conn.close()

    universe = _write_universe(
        tmp_path, [_usec("sec-921", "ZED"), _usec("sec-922", "YON")]
    )
    rc, out = _invoke_flow(capsys, db, universe, RIGHTS_FILE)
    report = json.loads(out)

    assert rc == 0
    expected = audit_store(db)
    summary = report["cluster_summary"]
    assert summary["clusters"] == expected["clusters"] == 4
    assert summary["multi_member_clusters"] == expected["multi_member_clusters"] == 1
    assert summary["size_histogram"] == expected["size_histogram"] == {
        "0": 1,
        "1": 2,
        "2": 1,
    }
    assert summary["stories"] == 4
    # Gap observation: totals.clusters counts news_clusters rows only, so the
    # orphan member id widens cluster_summary.clusters by one.
    assert report["totals"]["clusters"] == 3


def test_cluster_audit_skips_over_cap_with_hand_run_line(tmp_path):
    hostile = tmp_path / 'w12 store ?#%41 "q é数据'
    hostile.mkdir()
    db = _flow_store(hostile)

    report = inventory.build_inventory(
        database=db,
        health=None,
        now=FLOW_NOW,
        audit_cap=1,
    )

    assert report["cluster_summary"]["audit"] == {
        "state": "skipped",
        "reason": "story_count_over_cap",
        "stories": 6,
        "cap": 1,
        "hand_run": "python3 scripts/qbus_news_cluster_audit.py --store <path>",
    }
    assert inventory.AUDIT_HAND_RUN == (
        "python3 scripts/qbus_news_cluster_audit.py --store <path>"
    )
    text = inventory.format_text(report)
    assert (
        "cluster audit skipped / 聚类审计已跳过: stories/条目 6 > cap/上限 1; "
        "run/手动运行: python3 scripts/qbus_news_cluster_audit.py --store <path>"
    ) in text
    blob = json.dumps(report, ensure_ascii=False) + text
    assert str(db) not in blob
    assert str(db.parent) not in blob
    assert str(tmp_path) not in blob


def test_cli_over_cap_never_echoes_the_store_path(tmp_path, capsys, monkeypatch):
    hostile = tmp_path / 'w12 store ?#%41 "q é数据'
    hostile.mkdir()
    db = _flow_store(hostile)
    real_build = inventory.build_inventory

    def force_cap(**kwargs):
        kwargs["audit_cap"] = 1
        return real_build(**kwargs)

    # No CLI flag sets the audit cap, and main() binds AUDIT_STORY_CAP as a
    # def-time default of build_inventory, so the cap is forced through the
    # build_inventory global while main(), argparse, --json and --text all
    # stay the genuine CLI path.
    monkeypatch.setattr(inventory, "build_inventory", force_cap)

    json_rc, json_out = _invoke(capsys, db, "--json")
    text_rc, text_out = _invoke(capsys, db, "--text")

    assert json_rc == 0
    assert text_rc == 0
    assert json.loads(json_out)["cluster_summary"]["audit"]["state"] == "skipped"
    assert "cluster audit skipped / 聚类审计已跳过" in text_out
    for out in (json_out, text_out):
        assert str(db) not in out
        assert str(db.parent) not in out
        assert str(tmp_path) not in out


# Each name is opened read-only as given: without percent-encoding the URI,
# q?bus/q#bus would truncate at ? or # (opening or creating a file "q") and
# %41copy would percent-decode to Acopy.
HOSTILE_STORE_NAMES = (
    "sp ace.sqlite3",
    "q?bus.sqlite3",
    "q#bus.sqlite3",
    "%41copy.sqlite3",
    "100%.sqlite3",
    'quo"te\'.sqlite3',
    "naïve-数据.sqlite3",
    'dir ?#%41 "q\' é/qbus.sqlite3',
)


@pytest.mark.parametrize("name", HOSTILE_STORE_NAMES)
def test_hostile_store_paths_open_the_named_file_and_create_nothing(
    tmp_path, capsys, name
):
    reference_dir = tmp_path / "reference"
    reference_dir.mkdir()
    reference = _flow_store(reference_dir)
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    hostile = case_dir / name
    if hostile.parent != case_dir:
        hostile.parent.mkdir()
    shutil.copyfile(reference, hostile)
    copy_dir = tmp_path / "plaincopy"
    copy_dir.mkdir()
    plain_copy = copy_dir / "plain_copy.sqlite3"
    shutil.copyfile(reference, plain_copy)

    decoy = None
    if name == "%41copy.sqlite3":
        mixed_dir = tmp_path / "mixedsrc"
        mixed_dir.mkdir()
        mixed_db, *_times = _mixed_store(mixed_dir)
        decoy = case_dir / "Acopy.sqlite3"
        shutil.copyfile(mixed_db, decoy)
    if name in ("q?bus.sqlite3", "q#bus.sqlite3"):
        assert not (case_dir / "q").exists()

    before = set(tmp_path.rglob("*"))
    hostile_before = _snapshot(hostile)
    decoy_before = None if decoy is None else _snapshot(decoy)

    hostile_rc, hostile_out = _invoke(capsys, hostile, "--json")
    plain_rc, plain_out = _invoke(capsys, plain_copy, "--json")

    assert hostile_rc == 0
    assert plain_rc == 0
    # generated_at is pinned by --now and database.path carries the file
    # basename; no other field holds the file name, so both are dropped.
    hostile_report = json.loads(hostile_out)
    plain_report = json.loads(plain_out)
    for report in (hostile_report, plain_report):
        del report["generated_at"]
        del report["database"]["path"]
    assert hostile_report == plain_report
    assert hostile_report["cluster_summary"]["audit"]["state"] == "ran"

    assert _snapshot(hostile) == hostile_before
    if decoy is not None:
        assert _snapshot(decoy) == decoy_before
    allowed = {
        hostile.parent / f"{hostile.name}-wal",
        hostile.parent / f"{hostile.name}-shm",
        plain_copy.parent / f"{plain_copy.name}-wal",
        plain_copy.parent / f"{plain_copy.name}-shm",
    }
    assert set(tmp_path.rglob("*")) - before <= allowed


@pytest.mark.parametrize("name", HOSTILE_STORE_NAMES)
def test_missing_hostile_store_path_is_not_created(tmp_path, capsys, name):
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    missing = fresh / name
    before = set(tmp_path.rglob("*"))

    rc, out = _invoke(capsys, missing)

    assert rc == 2
    assert out == '{"error":"database_missing"}\n'
    assert set(tmp_path.rglob("*")) == before


def test_cluster_audit_under_cap_projects_counts_only(tmp_path, capsys):
    db = tmp_path / "mismatch.sqlite3"
    # Two subject groups, 28 hours apart, so no cross-subject pair falls
    # inside the 6-hour window: the audit lists exactly one near miss.
    base = FLOW_NOW - timedelta(hours=30)
    ace_base = FLOW_NOW - timedelta(hours=2)
    rows = (
        (9300001, base, "Zed Corp wins contract worth 3 million", "sec-931"),
        (9300002, base + timedelta(minutes=5), "Zed Corp wins contract worth 4 million", "sec-931"),
        (9300003, ace_base, "Ace Ltd lifts target to 20 dollars", "sec-932"),
        (9300004, ace_base + timedelta(minutes=5), "Ace Ltd lifts target to 30 dollars", "sec-932"),
    )
    routed = [
        RoutedRevision(
            revision=normalize_news(
                _titled_payload(
                    item_id=item_id,
                    updated=updated,
                    title=title,
                    ticker=title.split()[0].upper(),
                ),
                transport="benzinga_rest",
                received_at=updated + timedelta(seconds=5),
            ),
            security_ids=(sid,),
            universe_revision="sp500-r1",
        )
        for item_id, updated, title, sid in rows
    ]
    _commit_routed(db, routed)
    conn = sqlite3.connect(db)
    try:
        ace_cluster = conn.execute(
            "SELECT cluster_id FROM news_cluster_members WHERE source_item_id='9300003'"
        ).fetchone()[0]
        conn.execute(
            "UPDATE news_cluster_members SET cluster_id=? WHERE source_item_id='9300004'",
            (ace_cluster,),
        )
        conn.commit()
    finally:
        conn.close()

    universe = _write_universe(
        tmp_path, [_usec("sec-931", "ZED"), _usec("sec-932", "ACE")]
    )
    rc, out = _invoke_flow(capsys, db, universe, RIGHTS_FILE)
    report = json.loads(out)

    assert rc == 0
    assert report["cluster_summary"]["audit"] == {
        "state": "ran",
        "near_misses_listed": 1,
        "near_miss_list_limit": 50,
        "number_mismatch_pairs": 1,
        "number_mismatch_clusters": 1,
    }
    assert set(report["cluster_summary"]["audit"]) == {
        "state",
        "near_misses_listed",
        "near_miss_list_limit",
        "number_mismatch_pairs",
        "number_mismatch_clusters",
    }
    for row_key in ("a_story", "b_story", "a_numbers", "b_numbers", "similarity"):
        assert row_key not in out


def test_flow_latency_with_injected_timer(tmp_path):
    db = _flow_store(tmp_path)
    universe = _flow_universe(tmp_path)
    ticks = []

    def timer():
        call = len(ticks)
        ticks.append(call)
        slot, after = divmod(call, 2)
        return (slot * (slot + 1) // 2 + after * (slot + 1)) * 0.001

    report = inventory.build_inventory(
        database=db,
        health=None,
        now=FLOW_NOW,
        universe=universe,
        rights=RIGHTS_FILE,
        flow_tickers=2,
        flow_reads=20,
        timer=timer,
    )

    # The timer is used only for flow reads: exactly two calls per read.
    assert len(ticks) == 40
    assert report["flow_read_latency"] == {
        "state": "measured",
        "reads": 20,
        "tickers": ["MMM", "ZZZ"],
        "reports_7d": {"MMM": 2, "ZZZ": 3},
        "p50_ms": 10.0,
        "p95_ms": 19.0,
        "max_ms": 20.0,
        "method": "in-process store.news_flow reads; not HTTP; nearest-rank percentiles",
        "known_at": KNOWN_AT,
    }


def test_flow_text_line_is_labelled_in_process_not_http(tmp_path):
    db = _flow_store(tmp_path)
    universe = _flow_universe(tmp_path)
    ticks = []

    def timer():
        call = len(ticks)
        ticks.append(call)
        slot, after = divmod(call, 2)
        return (slot * (slot + 1) // 2 + after * (slot + 1)) * 0.001

    report = inventory.build_inventory(
        database=db,
        health=None,
        now=FLOW_NOW,
        universe=universe,
        rights=RIGHTS_FILE,
        flow_tickers=2,
        flow_reads=20,
        timer=timer,
    )

    assert (
        "flow reads / 流量读取: p50 10.0 ms p95 19.0 ms max 20.0 ms "
        "over/共 20 reads/次; tickers / 抽样代码: MMM, ZZZ; "
        "in-process, not HTTP / 进程内读取，非 HTTP"
    ) in inventory.format_text(report)

    unset = inventory.build_inventory(database=db, health=None, now=FLOW_NOW)
    unset_text = inventory.format_text(unset)
    assert "flow reads / 流量读取: unavailable (universe_path_unset)" in unset_text
    assert "in-process, not HTTP" not in unset_text


def test_flow_latency_unavailable_reasons(tmp_path, capsys):
    db = _flow_store(tmp_path)
    universe = _flow_universe(tmp_path)
    held = _write_universe(
        tmp_path, [_usec("sec-901", "ZZZ")], name="held.json", complete=False
    )

    def flow(out):
        return json.loads(out)["flow_read_latency"]

    rc, out = _invoke_flow(capsys, db, None, None)
    assert rc == 0
    assert flow(out) == {
        "state": "unavailable",
        "reason": "universe_path_unset",
        "known_at": KNOWN_AT,
    }
    rc, out = _invoke_flow(capsys, db, tmp_path / "absent.json", None)
    assert rc == 0
    assert flow(out) == {
        "state": "unavailable",
        "reason": "universe_unreadable",
        "known_at": KNOWN_AT,
    }
    rc, out = _invoke_flow(capsys, db, held, RIGHTS_FILE)
    assert rc == 0
    assert flow(out) == {
        "state": "unavailable",
        "reason": "universe_unqualified",
        "known_at": KNOWN_AT,
    }
    rc, out = _invoke_flow(capsys, db, universe, None)
    assert rc == 0
    assert flow(out) == {
        "state": "unavailable",
        "reason": "rights_path_unset",
        "known_at": KNOWN_AT,
    }

    expired_universe = _flow_universe(tmp_path, name="expired.json", base=EXPIRED_NOW)
    rc, out = _invoke_flow(capsys, db, expired_universe, RIGHTS_FILE, now=EXPIRED_NOW)
    assert rc == 0
    assert flow(out) == {
        "state": "unavailable",
        "reason": "rights_unavailable",
        "known_at": "2027-10-12T15:00:00Z",
    }

    mixed_db, *_times = _mixed_store(tmp_path)
    mixed_universe = _write_universe(
        tmp_path,
        [
            _usec("sec-NVDA", "NVDA"),
            _usec("sec-AMD", "AMD"),
            _usec("sec-MSFT", "MSFT"),
            _usec("sec-AAPL", "AAPL"),
        ],
        name="mixed.json",
    )
    rc, out = _invoke_flow(capsys, mixed_db, mixed_universe, RIGHTS_FILE)
    assert rc == 0
    assert flow(out) == {"state": "no_reports_7d", "reads": 0, "known_at": KNOWN_AT}


def test_new_sections_use_no_ranking_words(tmp_path_factory, capsys):
    # A neutrally-named directory: the report prints only the store basename
    # (the audit hand-run line carries a <path> placeholder), and pytest
    # embeds the test name in tmp_path.
    tmp_path = tmp_path_factory.mktemp("w12clean")
    db = _flow_store(tmp_path)
    universe = _flow_universe(tmp_path)
    held = _write_universe(
        tmp_path, [_usec("sec-901", "ZZZ")], name="held.json", complete=False
    )
    outputs = []

    for universe_arg, rights_arg, now, extra in (
        (None, None, FLOW_NOW, "--json"),
        (None, None, FLOW_NOW, "--text"),
        (universe, RIGHTS_FILE, FLOW_NOW, "--json"),
        (universe, RIGHTS_FILE, FLOW_NOW, "--text"),
        (tmp_path / "absent.json", None, FLOW_NOW, "--json"),
        (held, RIGHTS_FILE, FLOW_NOW, "--text"),
        (universe, None, FLOW_NOW, "--text"),
    ):
        rc, out = _invoke_flow(capsys, db, universe_arg, rights_arg, extra, now=now)
        assert rc == 0
        outputs.append(out)

    expired_universe = _flow_universe(tmp_path, name="expired.json", base=EXPIRED_NOW)
    rc, out = _invoke_flow(capsys, db, expired_universe, RIGHTS_FILE, "--text", now=EXPIRED_NOW)
    assert rc == 0
    outputs.append(out)

    skipped = inventory.build_inventory(
        database=db, health=None, now=FLOW_NOW, universe=universe, rights=RIGHTS_FILE, audit_cap=1
    )
    outputs.append(inventory.format_text(skipped))

    broken = tmp_path / "broken.sqlite3"
    shutil.copyfile(db, broken)
    conn = sqlite3.connect(broken)
    try:
        conn.execute("UPDATE news_clusters SET subject_ids_json='not-json'")
        conn.commit()
    finally:
        conn.close()
    failed = inventory.build_inventory(
        database=broken, health=None, now=FLOW_NOW, universe=universe, rights=RIGHTS_FILE
    )
    outputs.append(inventory.format_text(failed))

    mixed_db, *_times = _mixed_store(tmp_path)
    mixed_universe = _write_universe(
        tmp_path,
        [
            _usec("sec-NVDA", "NVDA"),
            _usec("sec-AMD", "AMD"),
            _usec("sec-MSFT", "MSFT"),
            _usec("sec-AAPL", "AAPL"),
        ],
        name="mixed.json",
    )
    rc, out = _invoke_flow(capsys, mixed_db, mixed_universe, RIGHTS_FILE, "--text")
    assert rc == 0
    outputs.append(out)

    for out in outputs:
        # The mandated statistical term "nearest-rank" is a method name, not
        # ranking language; the banned words are checked around it.
        low = out.lower().replace("nearest-rank", "")
        for word in RANKING_WORDS:
            assert word not in low, (word, out)
