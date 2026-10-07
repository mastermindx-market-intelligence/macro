"""Lifecycle tests for the single-writer qbus live-news service."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

from collectors import benzinga_news
from engine import qbus_news_store as store_mod
from engine.qbus_news_universe import qualify_universe
from scripts import run_qbus_news


UTC = timezone.utc
T0 = datetime(2026, 10, 5, 15, 0, tzinfo=UTC)


def _universe():
    return qualify_universe(
        {
            "owner": "security_reference.sp500",
            "revision": "sp500-r1",
            "complete": True,
            "truncated": False,
            "effective_at": T0 - timedelta(days=1),
            "known_at": T0 - timedelta(hours=1),
            "fresh_until": T0 + timedelta(days=1),
            "securities": [
                {
                    "security_id": "sec-NVDA",
                    "ticker": "NVDA",
                    "aliases": ["NVDA"],
                    "valid_from": T0 - timedelta(days=100),
                    "valid_to": None,
                    "known_at": T0 - timedelta(days=100),
                }
            ],
        },
        asof=T0,
    )


def _frame(item_id=1, action="created"):
    content = {
        "id": item_id,
        "created": "Mon, 05 Oct 2026 10:00:00 -0400",
        "updated": "Mon, 05 Oct 2026 10:00:01 -0400",
        "title": f"Story {item_id}",
        "url": f"https://www.benzinga.com/news/{item_id}",
        "stocks": [{"name": "NVDA"}],
        "channels": [{"name": "News"}],
        "tags": [],
    }
    return json.dumps(
        {
            "id": f"msg-{item_id}",
            "api_version": "websocket/v1",
            "kind": "news",
            "data": {
                "action": action,
                "id": item_id,
                "timestamp": "2026-10-05T14:00:02Z",
                "content": content,
            },
        }
    )


class FakeCatchupClient:
    def __init__(self):
        self.calls = 0

    def fetch_delta(self, *, cursor_epoch, observed_at):
        self.calls += 1
        return benzinga_news.DeltaBatch(
            revisions=(),
            query_since_epoch=0,
            next_cursor_epoch=int(observed_at.timestamp()),
            gap_unresolved=False,
            hold_reasons=(),
            news_pages=1,
            removed_pages=1,
        )


class FakeWS:
    def __init__(self, actions):
        self.actions = list(actions)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def recv(self, timeout=None):
        if not self.actions:
            raise ConnectionError("closed")
        action = self.actions.pop(0)
        if isinstance(action, BaseException):
            raise action
        return action


class FakeConnect:
    def __init__(self, connections):
        self.connections = list(connections)
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if not self.connections:
            raise ConnectionError("no more fake connections")
        return self.connections.pop(0)


class Clock:
    def __init__(self):
        self.now = T0
        self.mono = 0.0

    def utcnow(self):
        return self.now

    def monotonic(self):
        return self.mono

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)
        self.mono += seconds


def test_stream_url_uses_query_token_but_redacted_label_never_contains_token():
    url = run_qbus_news.stream_url("SECRET TOKEN")
    assert url.startswith(benzinga_news.STREAM_URL + "?")
    assert "token=SECRET+TOKEN" in url
    assert "SECRET" not in run_qbus_news.STREAM_LOG_LABEL


def test_startup_catchup_precedes_connect_and_stream_commit_preserves_cursor(tmp_path):
    clock = Clock()
    connect = FakeConnect([FakeWS([_frame(1), ConnectionError("drop")])])
    client = FakeCatchupClient()
    db = tmp_path / "qbus.sqlite3"

    with store_mod.NewsStore(db, source_key="benzinga-rest") as store:
        runner = run_qbus_news.NewsIngestRunner(
            token="TOKEN",
            store=store,
            universe_provider=_universe,
            direct_client=client,
            connect=connect,
            clock=clock.utcnow,
            monotonic=clock.monotonic,
            wait=lambda _: None,
            catchup_interval_seconds=30,
        )
        stats = runner.run(max_connections=1)

        assert client.calls == 1
        assert len(connect.calls) == 1
        assert stats.stream_events == 1
        assert store.current_cursor() == str(int(T0.timestamp()))
        assert store.snapshot(
            "sec-NVDA",
            limit=10,
            cursor=None,
            rights=store_mod.NewsReadRights.all_internal(),
        ).rows[0].source_item_id == "1"


def test_disconnect_reconnects_with_bounded_backoff_and_catchup_before_each_connection(tmp_path):
    clock = Clock()
    waits = []

    def wait(seconds):
        waits.append(seconds)
        clock.advance(seconds)

    connect = FakeConnect(
        [
            FakeWS([ConnectionError("first drop")]),
            FakeWS([_frame(2), ConnectionError("second drop")]),
        ]
    )
    client = FakeCatchupClient()
    with store_mod.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        runner = run_qbus_news.NewsIngestRunner(
            token="TOKEN",
            store=store,
            universe_provider=_universe,
            direct_client=client,
            connect=connect,
            clock=clock.utcnow,
            monotonic=clock.monotonic,
            wait=wait,
            reconnect_base_seconds=1,
            reconnect_max_seconds=8,
        )
        stats = runner.run(max_connections=2)

    assert client.calls == 2
    assert len(connect.calls) == 2
    assert waits == [1]
    assert stats.disconnects == 2
    assert stats.stream_events == 1


def test_timeout_tick_runs_periodic_catchup_without_opening_another_upstream_connection(tmp_path):
    clock = Clock()

    class TimeoutWS(FakeWS):
        def recv(self, timeout=None):
            if not self.actions:
                raise ConnectionError("end")
            action = self.actions.pop(0)
            if action == "timeout":
                clock.advance(31)
                raise TimeoutError
            return action

    connect = FakeConnect([TimeoutWS(["timeout", _frame(3), ConnectionError("end")])])
    client = FakeCatchupClient()

    with store_mod.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        runner = run_qbus_news.NewsIngestRunner(
            token="TOKEN",
            store=store,
            universe_provider=_universe,
            direct_client=client,
            connect=connect,
            clock=clock.utcnow,
            monotonic=clock.monotonic,
            wait=lambda _: None,
            catchup_interval_seconds=30,
            recv_timeout_seconds=1,
        )
        stats = runner.run(max_connections=1)

    assert client.calls == 2
    assert len(connect.calls) == 1
    assert stats.stream_events == 1
    assert stats.catchups_ok == 2


def test_malformed_or_oversized_frames_are_counted_and_do_not_kill_following_good_frame(tmp_path):
    clock = Clock()
    connect = FakeConnect(
        [
            FakeWS(
                [
                    "{bad-json",
                    "x" * 1025,
                    _frame(4),
                    ConnectionError("end"),
                ]
            )
        ]
    )
    client = FakeCatchupClient()

    with store_mod.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        runner = run_qbus_news.NewsIngestRunner(
            token="TOKEN",
            store=store,
            universe_provider=_universe,
            direct_client=client,
            connect=connect,
            clock=clock.utcnow,
            monotonic=clock.monotonic,
            wait=lambda _: None,
            max_frame_bytes=1024,
        )
        stats = runner.run(max_connections=1)

    assert stats.stream_errors == 2
    assert stats.stream_events == 1


def test_non_news_frames_are_ignored_not_errors(tmp_path):
    connect = FakeConnect(
        [FakeWS([json.dumps({"kind": "heartbeat"}), ConnectionError("end")])]
    )
    client = FakeCatchupClient()
    clock = Clock()

    with store_mod.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        runner = run_qbus_news.NewsIngestRunner(
            token="TOKEN",
            store=store,
            universe_provider=_universe,
            direct_client=client,
            connect=connect,
            clock=clock.utcnow,
            monotonic=clock.monotonic,
            wait=lambda _: None,
        )
        stats = runner.run(max_connections=1)

    assert stats.stream_ignored == 1
    assert stats.stream_errors == 0


def test_failed_catchup_does_not_prevent_fresh_stream_ingest_and_cursor_stays_put(tmp_path):
    class FailingClient:
        calls = 0

        def fetch_delta(self, *, cursor_epoch, observed_at):
            self.calls += 1
            raise benzinga_news.BenzingaTransportError("http_503")

    connect = FakeConnect([FakeWS([_frame(5), ConnectionError("end")])])
    client = FailingClient()
    clock = Clock()

    with store_mod.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        runner = run_qbus_news.NewsIngestRunner(
            token="TOKEN",
            store=store,
            universe_provider=_universe,
            direct_client=client,
            connect=connect,
            clock=clock.utcnow,
            monotonic=clock.monotonic,
            wait=lambda _: None,
        )
        stats = runner.run(max_connections=1)
        assert store.current_cursor() is None
        assert store.snapshot(
            "sec-NVDA",
            limit=10,
            cursor=None,
            rights=store_mod.NewsReadRights.all_internal(),
        ).rows[0].source_item_id == "5"

    assert stats.catchups_failed == 1
    assert stats.stream_events == 1


def test_stop_before_run_opens_no_connection(tmp_path):
    clock = Clock()
    stop = run_qbus_news.StopFlag()
    stop.set()
    connect = FakeConnect([])
    client = FakeCatchupClient()

    with store_mod.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        runner = run_qbus_news.NewsIngestRunner(
            token="TOKEN",
            store=store,
            universe_provider=_universe,
            direct_client=client,
            connect=connect,
            clock=clock.utcnow,
            monotonic=clock.monotonic,
            wait=lambda _: None,
            stop=stop,
        )
        stats = runner.run(max_connections=1)

    assert connect.calls == []
    assert client.calls == 0
    assert stats.connect_attempts == 0


def test_cli_preflight_reports_presence_not_token_value(monkeypatch, capsys):
    monkeypatch.setenv("BENZINGA_API_KEY", "DO-NOT-PRINT-ME")
    rc = run_qbus_news.main([])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["run_requested"] is False
    assert payload["token_present"] is True
    assert "DO-NOT-PRINT-ME" not in out
    assert payload["stream"] == run_qbus_news.STREAM_LOG_LABEL


def test_cli_run_fails_closed_without_universe_snapshot(monkeypatch, capsys):
    monkeypatch.setenv("BENZINGA_API_KEY", "DO-NOT-PRINT-ME")
    rc = run_qbus_news.main(["--run"])
    out = capsys.readouterr().out
    assert rc == 2
    assert json.loads(out)["error"] == "activation_prerequisite_missing"
    assert "DO-NOT-PRINT-ME" not in out


def test_exit_receipt_serializes_slotted_runner_stats():
    stats = run_qbus_news.RunnerStats(
        connect_attempts=2,
        stream_events=3,
        catchups_ok=4,
    )
    payload = run_qbus_news.exit_receipt(stats)
    assert payload["schema"] == "qbus.news_runner_exit.v1"
    assert payload["connect_attempts"] == 2
    assert payload["stream_events"] == 3
    assert payload["catchups_ok"] == 4