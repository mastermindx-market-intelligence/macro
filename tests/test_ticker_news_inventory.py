"""Read-only ticker-news inventory. Hermetic: store commit APIs and tmp files only."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

from engine.qbus_news_contract import normalize_news
from engine.qbus_news_receipts import load_health_receipt
from engine.qbus_news_store import NewsStore, RoutedRevision
from scripts import ticker_news_inventory as inventory


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


def test_docs_inventory_section_describes_the_command():
    text = (REPO_ROOT / "docs" / "ops" / "ticker-news.md").read_text(encoding="utf-8")
    section = text.split("## Inventory / 库存", 1)
    assert len(section) == 2
    body = section[1]
    assert "scripts/ticker_news_inventory.py" in body
    assert "mode=ro" in body
    assert "rest_catchup_proven" in body
    assert "health_path_unset" in body
    assert "delivery_json" in body
    assert "validated" not in body.lower()
    assert "title=" not in body
