"""Provider selection tests for the qbus news runner and its setup script.

Hermetic: no network, no service start, obvious fake credentials only. The
setup-script cases execute the real dispatcher functions sliced out of
app/deploy/ticker-news-setup.sh against a tmp 0600 env file.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess

import pytest

from collectors import alpaca_news, benzinga_news
from engine import qbus_news_store as store_mod
from engine.qbus_news_universe import qualify_universe
from scripts import run_qbus_news


UTC = timezone.utc
T0 = datetime(2026, 10, 11, 15, 0, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "app" / "deploy" / "ticker-news-setup.sh"
KEY_ID = "KEYID-FAKE"
SECRET_KEY = "SECRET-FAKE"
BENZINGA_TOKEN = "TOKEN-FAKE"


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
                },
            ],
        },
        asof=T0,
    )


def _clear_provider_env(monkeypatch):
    for var in (
        "BENZINGA_API_KEY",
        "QBUS_NEWS_PROVIDER",
        "ALPACA_API_KEY_ID",
        "ALPACA_API_SECRET_KEY",
        "MM_TICKER_NEWS_RIGHTS",
        "MM_TICKER_NEWS_HEALTH",
    ):
        monkeypatch.delenv(var, raising=False)


def _item(item_id: int) -> dict:
    return {
        "T": "n",
        "id": item_id,
        "headline": f"Story {item_id}",
        "created_at": "2026-10-11T14:59:00Z",
        "updated_at": "2026-10-11T14:59:01Z",
        "summary": f"teaser {item_id}",
        "url": f"https://www.benzinga.com/news/{item_id}",
        "symbols": ["NVDA"],
        "source": "benzinga",
    }


# ── CLI provider selection ───────────────────────────────────────────────────


def test_alpaca_flag_with_missing_env_fails_closed(monkeypatch, capsys, tmp_path):
    _clear_provider_env(monkeypatch)

    rc = run_qbus_news.main(
        [
            "--provider",
            "alpaca",
            "--run",
            "--database",
            str(tmp_path / "q.sqlite3"),
            "--universe-snapshot",
            str(tmp_path / "uni.json"),
        ]
    )

    out = capsys.readouterr().out
    assert rc == 2
    payload = json.loads(out)
    assert payload["error"] == "activation_prerequisite_missing"
    assert payload["provider"] == "alpaca"
    assert payload["token_present"] is False
    assert payload["stream"] == run_qbus_news.ALPACA_STREAM_LOG_LABEL
    assert "alpaca" in payload["stream"]
    assert "KEYID" not in out and "SECRET" not in out


def test_alpaca_env_keys_report_presence_without_values(monkeypatch, capsys, tmp_path):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("ALPACA_API_KEY_ID", KEY_ID)
    monkeypatch.setenv("ALPACA_API_SECRET_KEY", SECRET_KEY)

    rc = run_qbus_news.main(
        [
            "--provider",
            "alpaca",
            "--run",
            "--database",
            str(tmp_path / "q.sqlite3"),
            "--universe-snapshot",
            str(tmp_path / "uni.json"),
        ]
    )

    out = capsys.readouterr().out
    assert rc == 2  # universe/rights still missing
    payload = json.loads(out)
    assert payload["error"] == "activation_prerequisite_missing"
    assert payload["token_present"] is True
    assert KEY_ID not in out
    assert SECRET_KEY not in out


def test_bogus_provider_env_fails_closed_with_typed_error(monkeypatch, capsys):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("QBUS_NEWS_PROVIDER", "bogus")

    rc = run_qbus_news.main([])

    out = capsys.readouterr().out
    assert rc == 2
    payload = json.loads(out)
    assert payload["error"] == "activation_provider_invalid"
    assert payload["activation_qualified"] is False
    assert payload["provider"] == "bogus"


def test_bogus_provider_flag_fails_closed_too(monkeypatch, capsys):
    _clear_provider_env(monkeypatch)

    rc = run_qbus_news.main(["--provider", "wat"])

    out = capsys.readouterr().out
    assert rc == 2
    assert json.loads(out)["error"] == "activation_provider_invalid"


def test_env_selects_alpaca_without_flag(monkeypatch, capsys):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("QBUS_NEWS_PROVIDER", "alpaca")

    rc = run_qbus_news.main([])

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["provider"] == "alpaca"
    assert payload["stream"] == run_qbus_news.ALPACA_STREAM_LOG_LABEL


def test_default_report_is_today_s_report_plus_provider(monkeypatch, capsys, tmp_path):
    _clear_provider_env(monkeypatch)
    database = tmp_path / "q.sqlite3"
    universe = tmp_path / "uni.json"

    rc = run_qbus_news.main(
        [
            "--database",
            str(database),
            "--universe-snapshot",
            str(universe),
        ]
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert json.loads(out) == {
        "schema": "qbus.news_runner_preflight.v1",
        "run_requested": False,
        "check_requested": False,
        "token_present": False,
        "universe_present": False,
        "rights_receipt_present": False,
        "health_path_present": False,
        "database": str(database),
        "stream": run_qbus_news.STREAM_LOG_LABEL,
        "provider": "benzinga",
    }


def test_benzinga_report_with_token_still_works(monkeypatch, capsys, tmp_path):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("BENZINGA_API_KEY", BENZINGA_TOKEN)

    rc = run_qbus_news.main([])

    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["provider"] == "benzinga"
    assert payload["token_present"] is True
    assert payload["stream"] == run_qbus_news.STREAM_LOG_LABEL
    assert BENZINGA_TOKEN not in out


# ── runner: stream_target + handshake + frame_normalizer ─────────────────────


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
            removed_pages=0,
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


def test_alpaca_runner_routes_two_item_frame_with_one_commit(tmp_path):
    clock = Clock()
    frame = json.dumps([_item(1), _item(2)])
    connect = FakeConnect([FakeWS([frame, ConnectionError("drop")])])
    handshakes = []

    def handshake(ws):
        handshakes.append(ws)

    client = FakeCatchupClient()
    db = tmp_path / "qbus.sqlite3"
    health = tmp_path / "health.json"

    with store_mod.NewsStore(db, source_key="alpaca-rest") as store:
        commits = []
        original_commit = store.commit_observations

        def counting_commit(revisions):
            commits.append(list(revisions))
            return original_commit(revisions)

        store.commit_observations = counting_commit

        runner = run_qbus_news.NewsIngestRunner(
            token="",
            store=store,
            universe_provider=_universe,
            direct_client=client,
            connect=connect,
            clock=clock.utcnow,
            monotonic=clock.monotonic,
            wait=lambda _: None,
            catchup_interval_seconds=30,
            health_path=health,
            provider="alpaca",
            stream_target=alpaca_news.STREAM_URL,
            stream_handshake=handshake,
            frame_normalizer=alpaca_news.normalize_stream_frames,
        )
        stats = runner.run(max_connections=1)

        assert len(commits) == 1
        assert len(commits[0]) == 2
        assert [r.revision.source_item_id for r in commits[0]] == ["1", "2"]
        assert stats.stream_events == 2
        assert stats.stream_ignored == 0
        rows = store.snapshot(
            "sec-NVDA",
            limit=10,
            cursor=None,
            rights=store_mod.NewsReadRights.all_internal(),
        ).rows
        assert {row.source_item_id for row in rows} == {"1", "2"}

    assert len(connect.calls) == 1
    assert connect.calls[0][0] == alpaca_news.STREAM_URL
    assert "key" not in connect.calls[0][0]
    assert len(handshakes) == 1

    health_payload = json.loads(health.read_text(encoding="utf-8"))
    assert health_payload["provider"] == "alpaca"
    assert health_payload["source"] == "benzinga"
    assert KEY_ID not in health.read_text(encoding="utf-8")
    assert SECRET_KEY not in health.read_text(encoding="utf-8")


def test_alpaca_runner_handshake_error_follows_disconnect_backoff(tmp_path):
    clock = Clock()
    handshakes = []

    def failing_handshake(ws):
        handshakes.append(ws)
        raise alpaca_news.AlpacaStreamError("stream_handshake_timeout")

    # Connection 2 carries a good frame, but the handshake failure must divert
    # to the existing disconnect/backoff path BEFORE the recv loop consumes it.
    connect = FakeConnect(
        [FakeWS([]), FakeWS([json.dumps([_item(3)]), ConnectionError("end")])]
    )
    client = FakeCatchupClient()

    with store_mod.NewsStore(tmp_path / "q.sqlite3", source_key="alpaca-rest") as store:
        runner = run_qbus_news.NewsIngestRunner(
            token="",
            store=store,
            universe_provider=_universe,
            direct_client=client,
            connect=connect,
            clock=clock.utcnow,
            monotonic=clock.monotonic,
            wait=lambda _: None,
            provider="alpaca",
            stream_target=alpaca_news.STREAM_URL,
            stream_handshake=failing_handshake,
            frame_normalizer=alpaca_news.normalize_stream_frames,
        )
        stats = runner.run(max_connections=2)

    assert len(handshakes) == 2
    assert len(connect.calls) == 2  # the loop backed off and retried, no crash
    assert stats.disconnects == 2  # one per connection, via the shared handler
    assert stats.stream_events == 0  # the queued frame was never reached


def test_benzinga_runner_still_requires_a_token(tmp_path):
    with store_mod.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        with pytest.raises(ValueError, match="qbus_news:missing_stream_token"):
            run_qbus_news.NewsIngestRunner(
                token="",
                store=store,
                universe_provider=_universe,
                direct_client=FakeCatchupClient(),
            )


def test_empty_token_is_allowed_only_with_stream_target(tmp_path):
    with store_mod.NewsStore(tmp_path / "q.sqlite3", source_key="alpaca-rest") as store:
        runner = run_qbus_news.NewsIngestRunner(
            token="",
            store=store,
            universe_provider=_universe,
            direct_client=FakeCatchupClient(),
            connect=FakeConnect([]),
            clock=lambda: T0,
            monotonic=lambda: 0.0,
            wait=lambda _: None,
            provider="alpaca",
            stream_target=alpaca_news.STREAM_URL,
        )
        assert runner.provider == "alpaca"


def test_benzinga_runner_health_carries_provider_key(tmp_path):
    clock = Clock()
    connect = FakeConnect([FakeWS([ConnectionError("drop")])])
    health = tmp_path / "health.json"

    with store_mod.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        runner = run_qbus_news.NewsIngestRunner(
            token="TOKEN",
            store=store,
            universe_provider=_universe,
            direct_client=FakeCatchupClient(),
            connect=connect,
            clock=clock.utcnow,
            monotonic=clock.monotonic,
            wait=lambda _: None,
            health_path=health,
        )
        stats = runner.run(max_connections=1)

    assert stats.connect_attempts == 1
    payload = json.loads(health.read_text(encoding="utf-8"))
    assert payload["provider"] == "benzinga"
    assert payload["source"] == "benzinga"


# ── setup.sh dispatcher ──────────────────────────────────────────────────────


def _one_liner(text: str, prefix: str) -> str:
    for line in text.splitlines():
        if line.startswith(prefix):
            return line + "\n"
    raise AssertionError(f"function not found: {prefix}")


def _dispatcher_script() -> str:
    text = SETUP.read_text(encoding="utf-8")
    # Only the log/fail one-liners are carried over: everything else between
    # them and require_private_file() in the real script is top-level guard
    # code (root check, VPS paths, the macro-update flock) that must not run
    # under pytest.
    header = _one_liner(text, "log() {") + _one_liner(text, "fail() {")
    body = text[text.index("load_provider_token() {"):text.index("check_activation() {")]
    # The real require_private_file demands a root-owned file, which cannot
    # hold under a non-root pytest user; this stand-in keeps the mode check.
    # The root-owned half stays pinned textually by
    # tests/test_ticker_news_secret_delivery.py.
    stub = (
        "require_private_file() {\n"
        "  local mode\n"
        '  [ -f "$1" ] && [ ! -L "$1" ] || fail "required regular file missing: $1"\n'
        '  mode=$(stat -c "%a" "$1" 2>/dev/null || stat -f "%Lp" "$1")\n'
        '  case "$mode" in 600|400) ;; *) fail "file must be mode 600 or 400: $1" ;; esac\n'
        "}\n\n"
    )
    tail = (
        "load_provider_credentials\n"
        'if [ "${QBUS_NEWS_PROVIDER:-}" = alpaca ]; then\n'
        '  printf \'provider=%s key_len=%d secret_len=%d\\n\' '
        '"$QBUS_NEWS_PROVIDER" "${#ALPACA_API_KEY_ID}" "${#ALPACA_API_SECRET_KEY}"\n'
        "else\n"
        "  printf 'provider=%s token_len=%d\\n' "
        '"$QBUS_NEWS_PROVIDER" "${#BENZINGA_API_KEY}"\n'
        "fi\n"
    )
    return "set -euo pipefail\n" + header + "\n" + stub + body + tail


def _run_dispatcher(env_file: Path, tmp_path: Path) -> subprocess.CompletedProcess:
    script = tmp_path / "dispatch.sh"
    script.write_text(_dispatcher_script(), encoding="utf-8")
    return subprocess.run(
        ["bash", str(script)],
        env={**os.environ, "ENV_FILE": str(env_file)},
        capture_output=True,
        text=True,
        timeout=30,
    )


def _env_file(tmp_path: Path, lines: list[str]) -> Path:
    env_file = tmp_path / "macro-ticker-news.env"
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(env_file, 0o600)
    return env_file


def test_setup_dispatcher_alpaca_exports_without_echoing_values(tmp_path):
    env_file = _env_file(
        tmp_path,
        [
            "QBUS_NEWS_PROVIDER=alpaca",
            f"ALPACA_API_KEY_ID={KEY_ID}",
            f"ALPACA_API_SECRET_KEY={SECRET_KEY}",
        ],
    )

    proc = _run_dispatcher(env_file, tmp_path)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "provider=alpaca key_len=10 secret_len=11"
    combined = proc.stdout + proc.stderr
    assert KEY_ID not in combined
    assert SECRET_KEY not in combined


def test_setup_dispatcher_defaults_to_benzinga_without_provider_line(tmp_path):
    env_file = _env_file(tmp_path, [f"BENZINGA_API_KEY={BENZINGA_TOKEN}"])

    proc = _run_dispatcher(env_file, tmp_path)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "provider=benzinga token_len=10"
    combined = proc.stdout + proc.stderr
    assert BENZINGA_TOKEN not in combined


def test_setup_dispatcher_rejects_duplicate_provider_lines(tmp_path):
    env_file = _env_file(
        tmp_path,
        [
            "QBUS_NEWS_PROVIDER=alpaca",
            "QBUS_NEWS_PROVIDER=benzinga",
            f"ALPACA_API_KEY_ID={KEY_ID}",
            f"ALPACA_API_SECRET_KEY={SECRET_KEY}",
        ],
    )

    proc = _run_dispatcher(env_file, tmp_path)

    assert proc.returncode == 2
    assert "at most one QBUS_NEWS_PROVIDER" in proc.stderr
    combined = proc.stdout + proc.stderr
    assert KEY_ID not in combined
    assert SECRET_KEY not in combined


def test_setup_dispatcher_rejects_bogus_provider_value(tmp_path):
    env_file = _env_file(
        tmp_path,
        [
            "QBUS_NEWS_PROVIDER=bogus",
            f"BENZINGA_API_KEY={BENZINGA_TOKEN}",
        ],
    )

    proc = _run_dispatcher(env_file, tmp_path)

    assert proc.returncode == 2
    assert "must be benzinga or alpaca" in proc.stderr
    combined = proc.stdout + proc.stderr
    assert BENZINGA_TOKEN not in combined


def test_setup_dispatcher_rejects_wrong_mode_env_file(tmp_path):
    env_file = _env_file(tmp_path, [f"BENZINGA_API_KEY={BENZINGA_TOKEN}"])
    os.chmod(env_file, 0o644)

    proc = _run_dispatcher(env_file, tmp_path)

    assert proc.returncode == 2
    assert "mode 600 or 400" in proc.stderr


def test_setup_script_check_activation_uses_the_dispatcher(tmp_path):
    text = SETUP.read_text(encoding="utf-8")

    block = text[text.index("check_activation() {"):text.index("install_unit() {")]
    assert "load_provider_credentials" in block
    assert "\n  load_provider_token\n" not in block
    # load_provider_token itself stays textually intact.
    token_block = text[
        text.index("load_provider_token() {"):text.index("load_alpaca_credentials() {")
    ]
    assert 'grep -c -E "^BENZINGA_API_KEY="' in token_block
    assert "export BENZINGA_API_KEY" in token_block
