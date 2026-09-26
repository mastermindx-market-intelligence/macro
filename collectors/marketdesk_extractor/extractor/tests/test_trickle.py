"""Tests for the trickle runner (trickle.py) with a fake client + fake session.

NO network, NO auth, NO Playwright. We monkeypatch ``BrowserSession`` /
``MarketDeskClient`` / ``discover`` inside the ``trickle`` module so the loop
exercises its real orchestration (planning, per-account quota, newest-first,
cap-bounce cooldown, offline drain) against a seeded temp DB.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from marketdesk_extractor import db, trickle
from marketdesk_extractor.config import Config
from marketdesk_extractor.marketdesk import DownloadCapExhausted
from marketdesk_extractor.schemas import Status

NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)  # Monday 08:00 ET


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------
class FakeSession:
    """Stand-in for BrowserSession: authed, no browser, context is a sentinel."""

    def __init__(self, cfg, headless=None):
        self.cfg = cfg
        self.context = object()
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *exc):
        self.exited = True

    def is_authenticated(self):
        return True


class FakeClient:
    """Serves valid PDFs; records which blob_ids it was asked to download."""

    def __init__(self, context, cfg):
        self.cfg = cfg
        self.downloaded: list[str] = []

    def download_blob(self, blob_id: str) -> bytes:
        self.downloaded.append(blob_id)
        return b"%PDF-1.4\n" + blob_id.encode() + b"\n%%EOF\n"


class CappedClient(FakeClient):
    """Bounces every download with the over-cap HTML app-shell signal."""

    def download_blob(self, blob_id: str) -> bytes:
        self.downloaded.append(blob_id)
        raise DownloadCapExhausted(f"blob {blob_id}: HTML app-shell — cap reached")


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _cfg(tmp_path, monkeypatch, *, profiles: str = "") -> Config:
    env = {
        "DATABASE_URL": str(tmp_path / "db" / "t.sqlite"),
        "OUTPUT_DIR": str(tmp_path / "data"),
        "RAW_PDF_DIR": str(tmp_path / "data" / "raw_pdfs"),
        "MARKDOWN_DIR": str(tmp_path / "data" / "markdown"),
        "METADATA_DIR": str(tmp_path / "data" / "metadata"),
        "MANIFEST_DIR": str(tmp_path / "data" / "manifests"),
        "LOG_DIR": str(tmp_path / "logs"),
        "MARKETDESK_PROFILE_DIR": str(tmp_path / "prof"),
        "R2_ENABLED": "false",
        "DROPBOX_ENABLED": "false",
        "VAULT_ENABLED": "false",
        "PARSER_BACKEND": "none",
        "DOWNLOAD_CAP_PER_ACCOUNT_24H": "70",
        "NEW_WINDOW_HOURS": "48",
        "MARKETDESK_PROFILES": profiles,
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    cfg = Config.from_env()
    cfg.ensure_dirs()
    return cfg


def _seed(conn, blob_id, *, published_at, status=Status.DISCOVERED):
    conn.execute(
        "INSERT INTO papers (blob_id, article_url, blob_url, title, institution, "
        "published_at, status) VALUES (?,?,?,?,?,?,?)",
        (
            blob_id,
            f"https://marketdesk.ai/library/browse?item={blob_id}",
            f"https://marketdesk.ai/files/{blob_id}/blob",
            f"Title {blob_id}", "JPM",
            _iso(published_at), status.value,
        ),
    )
    conn.commit()


def _patch_sessions(monkeypatch, client_cls=FakeClient, session_cls=FakeSession):
    monkeypatch.setattr(trickle, "BrowserSession", session_cls)
    monkeypatch.setattr(trickle, "MarketDeskClient", client_cls)
    # never hit the network for discovery in these tests
    monkeypatch.setattr(trickle, "_refresh_queue", lambda *a, **k: None)


# ---------------------------------------------------------------------------
# dry-run smoke: prints a plan, downloads NOTHING
# ---------------------------------------------------------------------------
def test_dry_run_once_prints_plan_and_downloads_nothing(tmp_path, monkeypatch, capsys):
    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    _seed(conn, "fresh1", published_at=NOW - timedelta(hours=1))
    _seed(conn, "fresh2", published_at=NOW - timedelta(hours=3))
    conn.close()

    _patch_sessions(monkeypatch)
    results = trickle.run_trickle(
        cfg, once=True, dry_run=True, now_fn=lambda: NOW,
        sleep_fn=lambda _s: None,
    )
    out = capsys.readouterr().out
    assert "quota=70" in out          # a real per-account plan line was printed
    assert "next=new:fresh1" in out   # newest-first candidate identified
    assert len(results) == 1

    # NOTHING downloaded: no paper advanced past DISCOVERED, no PDF on disk
    conn = db.connect(cfg.database_url)
    counts = db.counts_by_status(conn)
    conn.close()
    assert counts.get(Status.DOWNLOADED.value, 0) == 0
    assert counts.get(Status.COMPLETE.value, 0) == 0
    assert not any(Path(cfg.raw_pdf_dir).glob("*.pdf"))


# ---------------------------------------------------------------------------
# real tick: downloads newest-first, records account, completes local-only
# ---------------------------------------------------------------------------
def test_tick_downloads_newest_first_and_records_account(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    _seed(conn, "older_new", published_at=NOW - timedelta(hours=10))
    _seed(conn, "newest_new", published_at=NOW - timedelta(hours=1))
    conn.close()

    _patch_sessions(monkeypatch)
    # single tick, cap the per-tick burst to 1 so we can assert the FIRST pick
    results = trickle.run_trickle(
        cfg, once=True, dry_run=False, per_tick_cap=1,
        now_fn=lambda: NOW, sleep_fn=lambda _s: None,
    )
    assert results[0].downloaded_new == 1

    conn = db.connect(cfg.database_url)
    newest = db.get_by_blob_id(conn, "newest_new")
    older = db.get_by_blob_id(conn, "older_new")
    acct_name = cfg.profiles[0].name
    conn.close()

    # newest was pulled first, marked COMPLETE (R2/vault off -> local-only),
    # and stamped with the account + downloaded_at
    assert newest["status"] == Status.COMPLETE.value
    assert newest["account"] == acct_name
    assert newest["downloaded_at"]
    assert newest["sha256"]
    # the older new paper was NOT touched this single-pull tick
    assert older["status"] == Status.DISCOVERED.value


def test_tick_records_ledger_and_quota_decrements(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    for i in range(3):
        _seed(conn, f"p{i}", published_at=NOW - timedelta(hours=i + 1))
    conn.close()

    _patch_sessions(monkeypatch)
    trickle.run_trickle(
        cfg, once=True, dry_run=False, now_fn=lambda: NOW, sleep_fn=lambda _s: None,
    )
    conn = db.connect(cfg.database_url)
    acct = cfg.profiles[0].name
    used = db.trailing_24h_count(conn, acct, NOW)
    conn.close()
    # default per-tick burst is 3 -> all three drained in one tick
    assert used == 3


# ---------------------------------------------------------------------------
# cap bounce -> account cooldown + paper reset (self-calibrating)
# ---------------------------------------------------------------------------
def test_cap_bounce_sets_cooldown_and_resets_paper(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    # a prior in-window download establishes the "oldest ages out" cooldown target
    conn.execute(
        "INSERT INTO papers (blob_id, article_url, blob_url, title, published_at, "
        "status, downloaded_at, account) VALUES (?,?,?,?,?,?,?,?)",
        ("prior", "u", "b", "prior", _iso(NOW - timedelta(days=3)),
         Status.COMPLETE.value, _iso(NOW - timedelta(hours=20)),
         (tmp_path / "prof").name),
    )
    conn.commit()
    _seed(conn, "wants_download", published_at=NOW - timedelta(hours=1))
    conn.close()

    _patch_sessions(monkeypatch, client_cls=CappedClient)
    states = [trickle.AccountState(profile=p) for p in cfg.profiles]
    conn = db.connect(cfg.database_url); db.init_db(conn)
    trickle._open_sessions(cfg, states)
    tick = trickle.run_tick(cfg, conn, states, NOW, dry_run=False)

    # the bounce was recorded, the paper was put BACK to DISCOVERED (not FAILED),
    # and the account is cooled down until its oldest in-window download ages out
    assert tick.cap_bounces == 1
    row = db.get_by_blob_id(conn, "wants_download")
    assert row["status"] == Status.DISCOVERED.value
    assert states[0].cooldown_until is not None
    expected_free = (NOW - timedelta(hours=20)) + timedelta(hours=24)
    assert abs((states[0].cooldown_until - expected_free).total_seconds()) < 1
    # and while cooled down, a later plan reports no candidate for that account
    later = NOW + timedelta(minutes=1)
    plan = trickle.plan_account(cfg, conn, states[0], later)
    assert plan.next_blob_id is None
    trickle._close_sessions(states)
    conn.close()


# ---------------------------------------------------------------------------
# unauthenticated profile is skipped, not crashed
# ---------------------------------------------------------------------------
def test_unauthenticated_account_is_skipped(tmp_path, monkeypatch, capsys):
    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    _seed(conn, "fresh", published_at=NOW - timedelta(hours=1))
    conn.close()

    class Unauthed(FakeSession):
        def is_authenticated(self):
            return False

    _patch_sessions(monkeypatch, session_cls=Unauthed)
    results = trickle.run_trickle(
        cfg, once=True, dry_run=True, now_fn=lambda: NOW, sleep_fn=lambda _s: None,
    )
    out = capsys.readouterr().out
    assert "NOT AUTHENTICATED" in out
    # nothing pulled
    assert results[0].downloaded_new == 0


# ---------------------------------------------------------------------------
# FAILED papers are reset to DISCOVERED at loop start (cap-failures, retryable)
# ---------------------------------------------------------------------------
def test_reset_failed_requeues_cap_failures(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    _seed(conn, "was_failed", published_at=NOW - timedelta(hours=2),
          status=Status.FAILED)
    n = trickle._reset_failed(conn)
    assert n == 1
    assert db.get_by_blob_id(conn, "was_failed")["status"] == Status.DISCOVERED.value
    conn.close()


# ---------------------------------------------------------------------------
# reserve gating: when quota <= expected near-term new arrivals, no backfill
# ---------------------------------------------------------------------------
def test_reserve_holds_back_backfill_when_quota_scarce(tmp_path, monkeypatch):
    # cap=1 so quota is tiny; only backfill candidates exist. At Monday 08:00 ET
    # the next-4h demand is large, so reserve > quota => allow_backfill False =>
    # the loop pulls nothing (holds the last slot for the expected new arrivals).
    cfg = _cfg(tmp_path, monkeypatch)
    monkeypatch.setenv("DOWNLOAD_CAP_PER_ACCOUNT_24H", "1")
    cfg = Config.from_env(); cfg.ensure_dirs()
    conn = db.connect(cfg.database_url); db.init_db(conn)
    _seed(conn, "backfill_only", published_at=NOW - timedelta(hours=100))
    conn.close()

    _patch_sessions(monkeypatch)
    results = trickle.run_trickle(
        cfg, once=True, dry_run=False, now_fn=lambda: NOW, sleep_fn=lambda _s: None,
    )
    assert results[0].downloaded_new == 0
    assert results[0].downloaded_backfill == 0
    conn = db.connect(cfg.database_url)
    assert db.get_by_blob_id(conn, "backfill_only")["status"] == Status.DISCOVERED.value
    conn.close()


# ---------------------------------------------------------------------------
# WIDE discover pass: heals papers OLDER than the narrow refresh window
# ---------------------------------------------------------------------------
class _RefreshRecorder:
    """Stands in for _refresh_queue; records the (since_hours, heal_limit, limit)
    of every refresh so a test can tell a WIDE pass from a narrow one."""

    def __init__(self):
        self.calls: list[tuple[int | None, int | None, int | None]] = []

    def __call__(self, cfg, conn, states, *, since_hours=None, heal_limit=None,
                 limit=None):
        self.calls.append((since_hours, heal_limit, limit))


class _FakeMonotonic:
    """Injectable monotonic clock: advances a fixed step per read."""

    def __init__(self, step: float, start: float = 0.0):
        self.t = start
        self.step = step
        self.reads = 0

    def __call__(self) -> float:
        self.reads += 1
        v = self.t
        self.t += self.step
        return v


def test_wide_discover_runs_on_first_refresh_then_only_after_the_interval(
    tmp_path, monkeypatch
):
    """A restart must heal IMMEDIATELY (first refresh is wide), then daily. The
    narrow refresh only re-examines its own window, so anything older can be
    healed by nothing else."""
    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    conn.close()

    _patch_sessions(monkeypatch)
    rec = _RefreshRecorder()
    monkeypatch.setattr(trickle, "_refresh_queue", rec)
    # each tick advances the monotonic clock by one discover interval, so EVERY
    # tick refreshes; only the wide cadence should gate wide-vs-narrow.
    mono = _FakeMonotonic(step=cfg.discover_every_sec)

    trickle.run_trickle(
        cfg, max_iterations=4, dry_run=False, now_fn=lambda: NOW,
        sleep_fn=lambda _s: None, monotonic_fn=mono,
    )

    assert len(rec.calls) == 4, "every tick crossed the narrow discover interval"
    # tick 1: WIDE (first refresh after start). The scan budget must be the WIDE
    # limit: walk_papers caps SCANNED items, and the narrow default (300) covers
    # ~1.5 days — a wide pass truncated by it heals nothing older.
    assert rec.calls[0] == (
        cfg.trickle_wide_discover_hours, cfg.trickle_wide_heal_limit,
        cfg.trickle_wide_discover_limit,
    )
    # ticks 2-4: NARROW (the 24h wide interval has not elapsed)
    assert rec.calls[1:] == [(None, None, None)] * 3


def test_wide_discover_repeats_once_the_wide_interval_elapses(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    conn.close()

    _patch_sessions(monkeypatch)
    rec = _RefreshRecorder()
    monkeypatch.setattr(trickle, "_refresh_queue", rec)
    # a full wide interval per tick -> every refresh is due to be wide again
    mono = _FakeMonotonic(step=cfg.trickle_wide_discover_every_sec)

    trickle.run_trickle(
        cfg, max_iterations=3, dry_run=False, now_fn=lambda: NOW,
        sleep_fn=lambda _s: None, monotonic_fn=mono,
    )
    wide = (cfg.trickle_wide_discover_hours, cfg.trickle_wide_heal_limit,
            cfg.trickle_wide_discover_limit)
    assert rec.calls == [wide, wide, wide]


def test_wide_pass_resets_failed_rows_daily(tmp_path, monkeypatch):
    """Cap-FAILED papers must re-enter the pool on every wide pass, not only at
    process start — a daemon that runs for weeks otherwise strands them."""
    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    _seed(conn, "ok", published_at=NOW - timedelta(hours=2))
    conn.close()

    _patch_sessions(monkeypatch)
    rec = _RefreshRecorder()
    monkeypatch.setattr(trickle, "_refresh_queue", rec)

    # A row that goes FAILED *after* the loop-start reset: only the wide pass can
    # rescue it. Mark it between tick 1 and tick 2 via the injected clock hook.
    marked: list[bool] = []

    def mono_fn(_c=_FakeMonotonic(step=cfg.trickle_wide_discover_every_sec)):
        if not marked:
            marked.append(True)
        else:
            c = db.connect(cfg.database_url)
            db.set_status(c, "ok", Status.FAILED, error_message="cap")
            c.close()
        return _c()

    trickle.run_trickle(
        cfg, max_iterations=2, dry_run=False, per_tick_cap=0,
        now_fn=lambda: NOW, sleep_fn=lambda _s: None, monotonic_fn=mono_fn,
    )

    conn = db.connect(cfg.database_url)
    assert db.get_by_blob_id(conn, "ok")["status"] == Status.DISCOVERED.value
    conn.close()
    assert len(rec.calls) == 2 and all(c[0] == cfg.trickle_wide_discover_hours
                                       for c in rec.calls)


# ---------------------------------------------------------------------------
# dead-driver watchdog: recycle the session, then exit(1) for the supervisor
# ---------------------------------------------------------------------------
DRIVER_DEAD_MSG = (
    "APIRequestContext.get: Connection closed while reading from the driver"
)


class DeadDriverClient(FakeClient):
    """Every download dies on the Playwright transport (the observed wedge)."""

    def download_blob(self, blob_id: str) -> bytes:
        self.downloaded.append(blob_id)
        raise Exception(DRIVER_DEAD_MSG)


def test_is_driver_dead_recognises_transport_failures():
    assert trickle._is_driver_dead(Exception(DRIVER_DEAD_MSG))
    assert trickle._is_driver_dead(Exception("Target closed"))
    assert trickle._is_driver_dead(
        Exception("Target page, context or browser has been closed")
    )
    # a normal bad-paper failure is NOT a transport failure
    assert not trickle._is_driver_dead(Exception("blob abc -> 404"))
    assert not trickle._is_driver_dead(ValueError("not a pdf"))


def test_driver_dead_requeues_the_paper_and_ends_the_account_tick(tmp_path, monkeypatch):
    """The transport died, not the paper: it must go back to DISCOVERED (never
    FAILED) and the account must stop pulling this tick — spinning the whole
    queue into FAILED is exactly what the 17h wedge did."""
    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    for i in range(3):
        _seed(conn, f"p{i}", published_at=NOW - timedelta(hours=i + 1))
    conn.close()

    _patch_sessions(monkeypatch, client_cls=DeadDriverClient)
    states = [trickle.AccountState(profile=p) for p in cfg.profiles]
    conn = db.connect(cfg.database_url); db.init_db(conn)
    trickle._open_sessions(cfg, states)
    tick = trickle.run_tick(cfg, conn, states, NOW, dry_run=False)

    assert tick.driver_dead == 1, "exactly ONE attempt, then the tick ended"
    assert states[0].client.downloaded == ["p0"]
    assert db.get_by_blob_id(conn, "p0")["status"] == Status.DISCOVERED.value
    assert states[0].driver_dead_ticks == 1
    trickle._close_sessions(states)
    conn.close()


def test_session_is_recycled_after_three_consecutive_dead_ticks(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    _seed(conn, "p", published_at=NOW - timedelta(hours=1))
    conn.close()

    opened: list[int] = []

    class CountingSession(FakeSession):
        def __enter__(self):
            opened.append(1)
            return super().__enter__()

    _patch_sessions(monkeypatch, client_cls=DeadDriverClient,
                    session_cls=CountingSession)

    results = trickle.run_trickle(
        cfg, max_iterations=3, dry_run=False, now_fn=lambda: NOW,
        sleep_fn=lambda _s: None, monotonic_fn=lambda: 0.0,
    )
    # 3 dead ticks -> one recycle (the initial open + exactly one re-open)
    assert [r.driver_dead for r in results] == [1, 1, 1]
    assert len(opened) == 2, "session opened once at start, re-opened once"


def test_healthy_tick_resets_the_dead_driver_counter(tmp_path, monkeypatch):
    """Only CONSECUTIVE all-dead ticks count — an intermittent blip must not
    accumulate into a needless session recycle."""
    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    _seed(conn, "a", published_at=NOW - timedelta(hours=1))
    _seed(conn, "b", published_at=NOW - timedelta(hours=2))
    conn.close()

    class FlakyClient(FakeClient):
        calls = 0

        def download_blob(self, blob_id: str) -> bytes:
            FlakyClient.calls += 1
            if FlakyClient.calls == 1:
                raise Exception(DRIVER_DEAD_MSG)
            return super().download_blob(blob_id)

    _patch_sessions(monkeypatch, client_cls=FlakyClient)
    states = [trickle.AccountState(profile=p) for p in cfg.profiles]
    conn = db.connect(cfg.database_url); db.init_db(conn)
    trickle._open_sessions(cfg, states)

    trickle.run_tick(cfg, conn, states, NOW, dry_run=False, per_tick_cap=1)
    assert states[0].driver_dead_ticks == 1
    trickle.run_tick(cfg, conn, states, NOW, dry_run=False, per_tick_cap=1)
    assert states[0].driver_dead_ticks == 0, "a successful tick clears the streak"
    trickle._close_sessions(states)
    conn.close()


def test_two_failed_reopens_exit_1_for_the_supervisor(tmp_path, monkeypatch):
    """When even the re-open fails, the process is unrecoverable in place: exit(1)
    so launchd's KeepAlive gives us a clean one."""
    cfg = _cfg(tmp_path, monkeypatch)
    states = [trickle.AccountState(profile=p) for p in cfg.profiles]
    states[0].driver_dead_ticks = trickle.DRIVER_DEAD_TICKS_BEFORE_REOPEN
    states[0].reopen_failures = trickle.REOPEN_FAILURES_BEFORE_EXIT - 1

    def boom(_cfg, _state):
        _state.authed = False
        return False

    monkeypatch.setattr(trickle, "_open_session", boom)
    with pytest.raises(SystemExit) as ei:
        trickle._recycle_dead_sessions(cfg, states)
    assert ei.value.code == 1


def test_successful_reopen_clears_the_failure_streak(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    states = [trickle.AccountState(profile=p) for p in cfg.profiles]
    states[0].driver_dead_ticks = trickle.DRIVER_DEAD_TICKS_BEFORE_REOPEN
    states[0].reopen_failures = 1

    def ok(_cfg, _state):
        _state.authed = True
        return True

    monkeypatch.setattr(trickle, "_open_session", ok)
    trickle._recycle_dead_sessions(cfg, states)
    assert states[0].reopen_failures == 0
    assert states[0].driver_dead_ticks == 0


def test_a_healthy_account_is_never_recycled(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    states = [trickle.AccountState(profile=p) for p in cfg.profiles]
    states[0].driver_dead_ticks = trickle.DRIVER_DEAD_TICKS_BEFORE_REOPEN - 1
    calls: list[str] = []
    monkeypatch.setattr(
        trickle, "_open_session", lambda c, s: calls.append(s.name) or True
    )
    trickle._recycle_dead_sessions(cfg, states)
    assert calls == []

# ---------------------------------------------------------------------------
# Collector-owned Research Vault ingest dispatch
# ---------------------------------------------------------------------------
def test_dispatch_research_ingest_advances_watermark_after_success(tmp_path):
    watermark = tmp_path / ".feed_vault_watermark"
    watermark.write_text("2026-09-16T10:00:00+00:00\n")
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="workflow queued\n", stderr="")

    ok = trickle._dispatch_research_ingest(
        latest_vaulted_at="2026-09-16T20:34:05.176549+00:00",
        published_count=3,
        watermark_path=watermark,
        runner=run,
    )

    assert ok is True
    assert calls == [
        (
            [
                "gh",
                "workflow",
                "run",
                "research-ingest.yml",
                "-R",
                "mastermindx-market-intelligence/macro",
            ],
            {
                "capture_output": True,
                "text": True,
                "check": False,
                "timeout": 20.0,
            },
        )
    ]
    assert watermark.read_text().strip() == "2026-09-16T20:34:05.176549+00:00"


def test_dispatch_research_ingest_failure_is_fail_soft_and_preserves_watermark(tmp_path):
    watermark = tmp_path / ".feed_vault_watermark"
    watermark.write_text("2026-09-16T10:00:00+00:00\n")

    def run(_command, **_kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="dispatch denied")

    ok = trickle._dispatch_research_ingest(
        latest_vaulted_at="2026-09-16T20:34:05.176549+00:00",
        published_count=1,
        watermark_path=watermark,
        runner=run,
    )

    assert ok is False
    assert watermark.read_text().strip() == "2026-09-16T10:00:00+00:00"


def test_offline_drain_dispatches_once_after_vault_publication(tmp_path, monkeypatch):
    events = []
    summary = SimpleNamespace(
        published=2,
        skipped=0,
        latest_vaulted_at="2026-09-16T20:34:05.176549+00:00",
    )
    cfg = SimpleNamespace(vault_enabled=True)
    conn = object()

    monkeypatch.setattr(trickle, "upload_pending", lambda *_a, **_k: events.append("upload"))
    monkeypatch.setattr(trickle, "publish_vault_pending", lambda *_a, **_k: summary)
    monkeypatch.setattr(trickle, "prune_local", lambda *_a, **_k: events.append("prune"))
    monkeypatch.setattr(
        trickle,
        "_dispatch_research_ingest",
        lambda *, latest_vaulted_at, published_count, **_k: events.append(
            ("dispatch", latest_vaulted_at, published_count)
        ) or True,
    )

    trickle._drain_offline(cfg, conn)

    assert events == [
        "upload",
        (
            "dispatch",
            "2026-09-16T20:34:05.176549+00:00",
            2,
        ),
        "prune",
    ]


def test_offline_drain_does_not_dispatch_without_new_vault_publication(monkeypatch):
    cfg = SimpleNamespace(vault_enabled=True)
    summary = SimpleNamespace(published=0, skipped=0, latest_vaulted_at="")
    monkeypatch.setattr(trickle, "upload_pending", lambda *_a, **_k: None)
    monkeypatch.setattr(trickle, "publish_vault_pending", lambda *_a, **_k: summary)
    monkeypatch.setattr(trickle, "prune_local", lambda *_a, **_k: None)
    monkeypatch.setattr(
        trickle,
        "_dispatch_research_ingest",
        lambda **_k: (_ for _ in ()).throw(AssertionError("dispatch must not run")),
    )

    trickle._drain_offline(cfg, object())
