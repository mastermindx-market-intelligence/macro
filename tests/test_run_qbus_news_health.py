"""Runtime health publication and activation-gate tests for qbus news runner."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys

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


def _frame(item_id=1):
    return json.dumps(
        {
            "id": f"msg-{item_id}",
            "kind": "news",
            "data": {
                "action": "created",
                "id": item_id,
                "timestamp": "2026-10-05T15:00:02Z",
                "content": {
                    "id": item_id,
                    "created": "Mon, 05 Oct 2026 11:00:00 -0400",
                    "updated": "Mon, 05 Oct 2026 11:00:01 -0400",
                    "title": f"Story {item_id}",
                    "url": f"https://www.benzinga.com/news/{item_id}",
                    "stocks": [{"name": "NVDA"}],
                    "channels": [{"name": "News"}],
                    "tags": [],
                },
            },
        }
    )


class Client:
    def __init__(self, *, gap=False, fail=False):
        self.gap = gap
        self.fail = fail

    def fetch_delta(self, *, cursor_epoch, observed_at):
        if self.fail:
            raise benzinga_news.BenzingaTransportError("http_503")
        return benzinga_news.DeltaBatch(
            revisions=(),
            query_since_epoch=0,
            next_cursor_epoch=int(observed_at.timestamp()),
            gap_unresolved=self.gap,
            hold_reasons=("page_budget",) if self.gap else (),
            news_pages=1,
            removed_pages=1,
        )


class WS:
    def __init__(self, actions):
        self.actions = list(actions)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def recv(self, timeout=None):
        if not self.actions:
            raise ConnectionError("closed")
        value = self.actions.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value


class Connect:
    def __init__(self, ws):
        self.ws = ws

    def __call__(self, url, **kwargs):
        return self.ws


class Clock:
    def __init__(self):
        self.now = T0
        self.mono = 0.0

    def utcnow(self):
        return self.now

    def monotonic(self):
        return self.mono


def test_runner_publishes_catchup_stream_disconnect_and_exit_health(monkeypatch, tmp_path):
    published = []
    monkeypatch.setattr(
        run_qbus_news,
        "write_health_receipt",
        lambda path, payload: published.append(dict(payload)),
    )
    clock = Clock()

    with store_mod.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        runner = run_qbus_news.NewsIngestRunner(
            token="TOKEN",
            store=store,
            universe_provider=_universe,
            direct_client=Client(),
            connect=Connect(WS([_frame(1), ConnectionError("drop")])),
            clock=clock.utcnow,
            monotonic=clock.monotonic,
            wait=lambda _: None,
            health_path=tmp_path / "health.json",
        )
        stats = runner.run(max_connections=1)

    assert stats.stream_events == 1
    states = [row["state"] for row in published]
    assert states[0] == "catching_up"
    assert "live" in states
    assert "degraded" in states
    assert states[-1] == "unavailable"

    live = [row for row in published if row["state"] == "live"]
    assert any(row["last_successful_catchup"] is not None for row in live)
    assert any(row["last_stream_event_at"] is not None for row in live)
    assert all("TOKEN" not in json.dumps(row) for row in published)


def test_gap_health_is_degraded_and_never_claims_successful_catchup(monkeypatch, tmp_path):
    published = []
    monkeypatch.setattr(
        run_qbus_news,
        "write_health_receipt",
        lambda path, payload: published.append(dict(payload)),
    )

    with store_mod.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        runner = run_qbus_news.NewsIngestRunner(
            token="TOKEN",
            store=store,
            universe_provider=_universe,
            direct_client=Client(gap=True),
            connect=Connect(WS([ConnectionError("drop")])),
            clock=lambda: T0,
            monotonic=lambda: 0.0,
            wait=lambda _: None,
            health_path=tmp_path / "health.json",
        )
        runner.run(max_connections=1)

    degraded = [row for row in published if row["state"] == "degraded"]
    assert degraded
    assert any(row["gap_unresolved"] is True for row in degraded)
    assert all(row["last_successful_catchup"] is None for row in degraded if row["gap_unresolved"])


def test_stream_event_after_failed_catchup_does_not_publish_live(monkeypatch, tmp_path):
    published = []
    monkeypatch.setattr(
        run_qbus_news,
        "write_health_receipt",
        lambda path, payload: published.append(dict(payload)),
    )

    with store_mod.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        runner = run_qbus_news.NewsIngestRunner(
            token="TOKEN",
            store=store,
            universe_provider=_universe,
            direct_client=Client(fail=True),
            connect=Connect(WS([_frame(2), ConnectionError("drop")])),
            clock=lambda: T0,
            monotonic=lambda: 0.0,
            wait=lambda _: None,
            health_path=tmp_path / "health.json",
        )
        runner.run(max_connections=1)

    event_rows = [row for row in published if row["last_stream_event_at"] is not None]
    assert event_rows
    assert all(row["state"] != "live" for row in event_rows)
    assert all(row["last_successful_catchup"] is None for row in event_rows)


def test_health_write_failure_never_kills_ingest_and_is_counted(monkeypatch, tmp_path):
    def fail_write(path, payload):
        raise OSError("disk unavailable")

    monkeypatch.setattr(run_qbus_news, "write_health_receipt", fail_write)

    with store_mod.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        runner = run_qbus_news.NewsIngestRunner(
            token="TOKEN",
            store=store,
            universe_provider=_universe,
            direct_client=Client(),
            connect=Connect(WS([_frame(3), ConnectionError("drop")])),
            clock=lambda: T0,
            monotonic=lambda: 0.0,
            wait=lambda _: None,
            health_path=tmp_path / "health.json",
        )
        stats = runner.run(max_connections=1)

    assert stats.stream_events == 1
    assert stats.health_write_failures >= 1


def test_cli_run_requires_rights_receipt_and_health_path(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("BENZINGA_API_KEY", "DO-NOT-PRINT")
    universe = tmp_path / "universe.json"
    universe.write_text("{}", encoding="utf-8")

    rc = run_qbus_news.main(
        ["--run", "--universe-snapshot", str(universe)]
    )
    out = capsys.readouterr().out

    assert rc == 2
    payload = json.loads(out)
    assert payload["error"] == "activation_prerequisite_missing"
    assert payload["rights_receipt_present"] is False
    assert payload["health_path_present"] is False
    assert "DO-NOT-PRINT" not in out


def test_cli_run_rejects_present_but_unqualified_rights_receipt(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("BENZINGA_API_KEY", "DO-NOT-PRINT")
    universe = tmp_path / "universe.json"
    universe.write_text("{}", encoding="utf-8")
    rights = tmp_path / "rights.json"
    rights.write_text(
        json.dumps({"schema": "qbus.news_rights_receipt.v1", "status": "denied"}),
        encoding="utf-8",
    )

    rc = run_qbus_news.main(
        [
            "--run",
            "--universe-snapshot",
            str(universe),
            "--rights-receipt",
            str(rights),
            "--health-path",
            str(tmp_path / "health.json"),
        ]
    )
    out = capsys.readouterr().out

    assert rc == 2
    payload = json.loads(out)
    assert payload["error"] == "activation_rights_unqualified"
    assert "DO-NOT-PRINT" not in out

def test_runner_direct_script_check_only_is_executable_from_repo_root(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    for name in (
        "BENZINGA_API_KEY",
        "MM_TICKER_NEWS_RIGHTS",
        "MM_TICKER_NEWS_HEALTH",
        "MM_TICKER_NEWS_UNIVERSE",
        "MM_TICKER_NEWS_DB",
    ):
        monkeypatch.delenv(name, raising=False)

    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "run_qbus_news.py")],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema"] == "qbus.news_runner_preflight.v1"
    assert payload["run_requested"] is False
    assert payload["token_present"] is False
    assert "BENZINGA" not in proc.stderr

def test_runner_stops_ingestion_when_admission_guard_revokes(monkeypatch, tmp_path):
    published = []
    monkeypatch.setattr(
        run_qbus_news,
        "write_health_receipt",
        lambda path, payload: published.append(dict(payload)),
    )
    allowed = {"value": True}

    with store_mod.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        original_commit = store.commit_observations

        def commit_then_revoke(revisions):
            receipt = original_commit(revisions)
            allowed["value"] = False
            return receipt

        monkeypatch.setattr(store, "commit_observations", commit_then_revoke)
        runner = run_qbus_news.NewsIngestRunner(
            token="TOKEN",
            store=store,
            universe_provider=_universe,
            direct_client=Client(),
            connect=Connect(WS([_frame(10), _frame(11)])),
            clock=lambda: T0,
            monotonic=lambda: 0.0,
            wait=lambda _: None,
            health_path=tmp_path / "health.json",
            admission_guard=lambda: allowed["value"],
        )
        stats = runner.run(max_connections=1)
        counts = store.counts()

    assert stats.stream_events == 1
    assert counts["revisions"] == 1
    assert counts["states"] == 1
    assert published[-1]["state"] == "unavailable"


def test_runner_treats_admission_guard_error_as_denial(monkeypatch, tmp_path):
    published = []
    monkeypatch.setattr(
        run_qbus_news,
        "write_health_receipt",
        lambda path, payload: published.append(dict(payload)),
    )

    def broken_guard():
        raise OSError("rights store unavailable")

    with store_mod.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        runner = run_qbus_news.NewsIngestRunner(
            token="TOKEN",
            store=store,
            universe_provider=_universe,
            direct_client=Client(),
            connect=Connect(WS([_frame(12)])),
            clock=lambda: T0,
            monotonic=lambda: 0.0,
            wait=lambda _: None,
            health_path=tmp_path / "health.json",
            admission_guard=broken_guard,
        )
        stats = runner.run(max_connections=1)
        counts = store.counts()

    assert stats.connect_attempts == 0
    assert stats.stream_events == 0
    assert counts["revisions"] == 0
    assert published[-1]["state"] == "unavailable"
