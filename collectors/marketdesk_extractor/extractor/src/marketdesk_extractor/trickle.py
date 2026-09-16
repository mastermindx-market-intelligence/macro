"""The trickle runner — a long-running, demand-aware, multi-account download loop.

Ties the pure allocator (``allocator.py``) and the per-account rolling ledger
(``db.py``) to real Playwright sessions. Each account gets one persistent
``BrowserSession`` opened once and reused across ticks (relaunching Chromium
every tick would be both slow and rude). Every tick:

  1. periodically refresh the new-post queue via the UNCAPPED discovery API
     (one authed session is enough — discovery is shared across accounts). Most
     refreshes are NARROW (new window + 24h); once a day (and always on the first
     refresh after start) the refresh is WIDE — a 14-day re-walk that heals
     late-arriving AI summaries + truncated titles outside the narrow window and
     re-queues cap-FAILED papers;
  2. for each account with spare rolling-24h quota and not in cooldown, compute
     the backfill reserve from the demand profile, decide new-vs-backfill, pick a
     candidate, download it through THAT account, then run the offline
     upload -> publish-vault -> prune-local chain so it lands in R2 and the local
     PDF is reclaimed;
  3. if a download bounces on the cap (the HTML app-shell), put that account into
     a self-calibrating cooldown until its oldest in-window download ages out;
  4. if an account's downloads keep dying on the Playwright driver ("Connection
     closed while reading from the driver"), recycle THAT account's session, and
     if the re-open keeps failing, exit(1) so launchd restarts us clean.

The loop is cooperative and bounded: at most ``downloads_per_account_per_tick``
downloads per account per tick, then sleep ``TRICKLE_INTERVAL_SEC``. ``--once``
runs a single tick; ``--dry-run`` computes and prints the per-account plan and
downloads NOTHING.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import allocator, db
from .auth import BrowserSession
from .cleanup import prune_local
from .config import Config, Profile
from .download import download_one
from .marketdesk import (
    DownloadCapExhausted,
    MarketDeskClient,
    MarketDeskError,
    SessionExpired,
)
from .pipeline import publish_vault_pending, upload_pending
from .schemas import Status
from .storage import StorageGuardError
from .utils import get_logger, utc_now

log = get_logger("trickle")

# Backstop only: the token-bucket pace in run_tick is the real rate governor;
# this just caps a single tick's drain so nothing runs away.
DOWNLOADS_PER_ACCOUNT_PER_TICK = 15

RESEARCH_INGEST_REPOSITORY = "mastermindx-market-intelligence/macro"
RESEARCH_INGEST_WORKFLOW = "research-ingest.yml"
RESEARCH_INGEST_TIMEOUT_SECONDS = 20.0

# ---------------------------------------------------------------------------
# Dead-driver watchdog
# ---------------------------------------------------------------------------
# Observed production wedge: after "APIRequestContext.get: Connection closed while
# reading from the driver" the Playwright session was dead but ``state.authed``
# stayed True, so the loop kept ticking — burning CPU, downloading nothing — for
# 17+ hours. Nothing in the loop could notice, because every tick looked like a
# normal per-paper failure. These markers identify that class of error (the
# transport is gone, the paper is fine) so the loop can recycle the session.
_DRIVER_DEAD_MARKERS: tuple[str, ...] = (
    "connection closed",
    "target closed",
    "has been closed",
    "target page, context or browser has been closed",
)

# Consecutive ticks in which EVERY download attempt for an account died on the
# driver before we recycle that account's session.
DRIVER_DEAD_TICKS_BEFORE_REOPEN = 3
# Consecutive failed re-opens before we give up and let the supervisor restart us.
REOPEN_FAILURES_BEFORE_EXIT = 2


def _is_driver_dead(exc: BaseException) -> bool:
    """Is this exception the transport dying rather than a bad paper? (pure)"""
    msg = str(exc).lower()
    return any(marker in msg for marker in _DRIVER_DEAD_MARKERS)


def _refill_tokens(
    tokens: float, last_refill: datetime | None, now: datetime,
    *, burst: float, refill_per_sec: float,
) -> float:
    """Token-bucket pacing (pure). Spreads the daily rolling-cap budget across the
    day instead of bursting it all at once — bursting would exhaust the 24h window
    in minutes and then starve every new post that arrives later (e.g. the 17-19
    ET US-close bump). Capacity ``burst`` allows a small catch-up spike for a fresh
    burst of new posts; steady refill = cap/24h keeps the sustained rate under the
    cap. A fresh account starts with a full bucket."""
    if last_refill is None:
        return float(burst)
    elapsed = (now - last_refill).total_seconds()
    if elapsed <= 0:
        return tokens
    return min(float(burst), tokens + elapsed * refill_per_sec)


# ---------------------------------------------------------------------------
# Per-account runtime state
# ---------------------------------------------------------------------------
@dataclass
class AccountState:
    profile: Profile
    session: BrowserSession | None = None
    client: MarketDeskClient | None = None
    authed: bool = False
    cooldown_until: datetime | None = None  # cap-bounce backoff
    tokens: float = 0.0                      # pacing token bucket (see _refill_tokens)
    last_refill: datetime | None = None
    # dead-driver watchdog: consecutive ticks whose every download attempt died on
    # the driver, and consecutive failed session re-opens.
    driver_dead_ticks: int = 0
    reopen_failures: int = 0

    @property
    def name(self) -> str:
        return self.profile.name

    def in_cooldown(self, now: datetime) -> bool:
        return self.cooldown_until is not None and now < self.cooldown_until


@dataclass
class AccountPlan:
    """What one account would do this tick (also the dry-run print payload)."""

    account: str
    authed: bool
    available_quota: int
    trailing_24h: int
    reserve: float
    allow_backfill: bool
    next_blob_id: str | None
    next_kind: str  # "new" | "backfill" | "none"
    new_pending: int
    backfill_pending: int
    cooldown_until: datetime | None = None

    def describe(self) -> str:
        if not self.authed:
            return f"[{self.account}] NOT AUTHENTICATED — skipped"
        cd = ""
        if self.cooldown_until is not None:
            cd = f" cooldown_until={self.cooldown_until.isoformat()}"
        nxt = self.next_blob_id or "(none eligible)"
        return (
            f"[{self.account}] quota={self.available_quota} "
            f"(used_24h={self.trailing_24h}) reserve={self.reserve:.1f} "
            f"allow_backfill={self.allow_backfill} next={self.next_kind}:{nxt} "
            f"queue(new={self.new_pending},backfill={self.backfill_pending}){cd}"
        )


@dataclass
class TickResult:
    plans: list[AccountPlan] = field(default_factory=list)
    downloaded_new: int = 0
    downloaded_backfill: int = 0
    cap_bounces: int = 0
    unsupported: int = 0
    errors: int = 0
    driver_dead: int = 0  # attempts that died on the Playwright transport
    session_expired: int = 0  # accounts parked this tick on a lapsed login

    def summary(self) -> str:
        return (
            f"downloaded new={self.downloaded_new} backfill={self.downloaded_backfill} "
            f"cap_bounces={self.cap_bounces} unsupported={self.unsupported} "
            f"errors={self.errors} driver_dead={self.driver_dead} "
            f"session_expired={self.session_expired}"
        )


# ---------------------------------------------------------------------------
# Planning (pure-ish: reads DB + clock, no downloads) — used by dry-run too
# ---------------------------------------------------------------------------
def plan_account(
    cfg: Config, conn, state: AccountState, now: datetime,
    *, profile: allocator.HourlyProfile | None = None,
) -> AccountPlan:
    prof = profile or allocator.DEFAULT_PROFILE
    used = db.trailing_24h_count(conn, state.name, now)
    quota = max(0, cfg.download_cap_per_account_24h - used)
    reserve = allocator.expected_new_next_hours(now, cfg.backfill_reserve_hours, prof)
    allow_backfill = quota > reserve
    new_pending, backfill_pending = allocator.queue_depths(
        conn, now, new_window_hours=cfg.new_window_hours
    )
    blob_id = None
    kind = "none"
    if quota > 0 and state.authed and not state.in_cooldown(now):
        blob_id = allocator.next_candidate(
            conn, now, new_window_hours=cfg.new_window_hours,
            reserve=reserve, allow_backfill=allow_backfill,
        )
        if blob_id is not None:
            kind = _classify(conn, blob_id, now, cfg.new_window_hours)
    return AccountPlan(
        account=state.name,
        authed=state.authed,
        available_quota=quota,
        trailing_24h=used,
        reserve=reserve,
        allow_backfill=allow_backfill,
        next_blob_id=blob_id,
        next_kind=kind,
        new_pending=new_pending,
        backfill_pending=backfill_pending,
        cooldown_until=state.cooldown_until,
    )


def _classify(conn, blob_id: str, now: datetime, new_window_hours: int) -> str:
    row = conn.execute(
        "SELECT published_at FROM papers WHERE blob_id=?", (blob_id,)
    ).fetchone()
    pub = row["published_at"] if row is not None else None
    return "new" if allocator.is_new(pub, now, new_window_hours) else "backfill"


# ---------------------------------------------------------------------------
# Research Vault ingest bridge — owned by the already-running collector
# ---------------------------------------------------------------------------
def _default_watermark_path() -> Path:
    return Path.home() / "mastermind-research" / ".feed_vault_watermark"


def _write_watermark_atomic(path: Path, value: str) -> None:
    """Advance the legacy feed cursor without exposing a partial write."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(value.rstrip() + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _dispatch_research_ingest(
    *,
    latest_vaulted_at: str,
    published_count: int,
    watermark_path: Path | None = None,
    runner: Callable[..., object] | None = None,
) -> bool:
    """Dispatch the canonical ingest after a successful vault publication.

    The collector already owns the external-volume SQLite connection that recorded
    ``vaulted_at``. Dispatching here avoids a second launchd process reopening that
    removable-volume database. Failure is fail-soft because the hourly GitHub
    workflow remains the correction backstop; the collector must never die because
    the transport is briefly unavailable.
    """
    latest = str(latest_vaulted_at or "").strip()
    if published_count <= 0 or not latest:
        return False

    command = [
        "gh",
        "workflow",
        "run",
        RESEARCH_INGEST_WORKFLOW,
        "-R",
        RESEARCH_INGEST_REPOSITORY,
    ]
    run = runner or subprocess.run
    try:
        result = run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=RESEARCH_INGEST_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning(
            "research ingest dispatch unavailable after %d vault publication(s): %s; "
            "hourly workflow remains the backstop",
            published_count,
            exc,
        )
        return False

    returncode = int(getattr(result, "returncode", 1))
    if returncode != 0:
        detail = str(getattr(result, "stderr", "") or "").strip()[-500:]
        log.warning(
            "research ingest dispatch failed rc=%d after %d vault publication(s)%s; "
            "hourly workflow remains the backstop",
            returncode,
            published_count,
            f": {detail}" if detail else "",
        )
        return False

    cursor = Path(watermark_path) if watermark_path is not None else _default_watermark_path()
    try:
        _write_watermark_atomic(cursor, latest)
    except OSError as exc:
        # The workflow has already been accepted. Do not retry blindly; preserve the
        # old cursor and let the next natural publication or hourly run reconcile.
        log.warning(
            "research ingest dispatched for %d vault publication(s), but watermark "
            "advance to %s failed: %s",
            published_count,
            latest,
            exc,
        )
        return True

    log.info(
        "research ingest dispatched after %d vault publication(s); watermark -> %s",
        published_count,
        latest,
    )
    return True


# ---------------------------------------------------------------------------
# Offline drain (upload -> vault -> prune) for a freshly downloaded paper
# ---------------------------------------------------------------------------
def _drain_offline(cfg: Config, conn) -> None:
    """Push freshly DOWNLOADED papers off-box and reclaim local disk.

    Parsing is deliberately skipped in the trickle loop (heavy ML deps, off the
    latency path): ``upload_pending`` marks papers COMPLETE local-only when no
    upload target is configured, and the vault path publishes the PDF as-is.
    Cleanup requires a durable copy (vault when the main R2 archive is off) so a
    prune never races ahead of the archive.
    """
    try:
        upload_pending(cfg, conn)
    except Exception as e:  # noqa: BLE001 - never let a drain error kill the loop
        log.warning("trickle drain: upload_pending failed: %s", e)
    if cfg.vault_enabled:
        vault_summary = None
        try:
            vault_summary = publish_vault_pending(cfg, conn)
        except Exception as e:  # noqa: BLE001
            log.warning("trickle drain: publish_vault_pending failed: %s", e)
        if vault_summary is not None and vault_summary.published > 0:
            _dispatch_research_ingest(
                latest_vaulted_at=vault_summary.latest_vaulted_at,
                published_count=vault_summary.published,
            )
        try:
            prune_local(cfg, conn, older_than_days=0, require_vault=True)
        except Exception as e:  # noqa: BLE001
            log.warning("trickle drain: prune_local failed: %s", e)


# ---------------------------------------------------------------------------
# One tick
# ---------------------------------------------------------------------------
def run_tick(
    cfg: Config, conn, states: list[AccountState], now: datetime,
    *, dry_run: bool, profile: allocator.HourlyProfile | None = None,
    per_tick_cap: int = DOWNLOADS_PER_ACCOUNT_PER_TICK,
) -> TickResult:
    # Re-check every tick. If the volume was unplugged or crossed the safety
    # floor, abort before selecting a paper or spending a provider attempt.
    cfg.assert_storage_ready()
    res = TickResult()
    for state in states:
        plan = plan_account(cfg, conn, state, now, profile=profile)
        res.plans.append(plan)
        if dry_run or not state.authed or state.in_cooldown(now):
            continue
        if plan.available_quota <= 0 or plan.next_blob_id is None:
            continue

        # pacing: refill this account's token bucket, then spend tokens so the
        # daily budget spreads across the day rather than bursting all at once.
        refill_per_sec = cfg.download_cap_per_account_24h / 86400.0
        state.tokens = _refill_tokens(
            state.tokens, state.last_refill, now,
            burst=cfg.trickle_burst, refill_per_sec=refill_per_sec,
        )
        state.last_refill = now

        pulled = 0
        attempts = 0        # download attempts made for this account this tick
        driver_dead = 0     # ...of which died on the Playwright transport
        while state.tokens >= 1.0 and pulled < per_tick_cap:
            # re-evaluate quota + candidate each pull (DB moved under us)
            used = db.trailing_24h_count(conn, state.name, now)
            quota = max(0, cfg.download_cap_per_account_24h - used)
            if quota <= 0:
                break
            reserve = allocator.expected_new_next_hours(
                now, cfg.backfill_reserve_hours, profile or allocator.DEFAULT_PROFILE
            )
            allow_backfill = quota > reserve
            blob_id = allocator.next_candidate(
                conn, now, new_window_hours=cfg.new_window_hours,
                reserve=reserve, allow_backfill=allow_backfill,
            )
            if blob_id is None:
                break
            kind = _classify(conn, blob_id, now, cfg.new_window_hours)
            row = db.get_by_blob_id(conn, blob_id)
            if row is None:
                break
            state.tokens -= 1.0  # spend a pacing token on this fetch attempt
            attempts += 1
            try:
                status = download_one(
                    cfg, conn, state.client, row, account=state.name
                )
                if status == Status.DOWNLOADED:
                    if kind == "new":
                        res.downloaded_new += 1
                    else:
                        res.downloaded_backfill += 1
                    _drain_offline(cfg, conn)
                pulled += 1
            except StorageGuardError:
                # Storage pressure is infrastructure, not a paper failure. Undo
                # the pacing bookkeeping and let launchd retry after recovery.
                state.tokens += 1.0
                attempts -= 1
                raise
            except SessionExpired as e:
                # NOT a cap: the login itself is gone, so every later attempt on
                # this account would bounce identically. Park the account (its
                # plan line then reads "NOT AUTHENTICATED — skipped" every tick,
                # which is the loud, true thing) instead of scheduling a cooldown
                # that quietly re-arms forever. The paper goes back to DISCOVERED:
                # it never got a fair try. Recovery is human — the profile is
                # single-writer, so `marketdesk auth` needs the daemon stopped;
                # a KeepAlive restart alone re-opens the same dead session.
                res.session_expired += 1
                state.authed = False
                db.set_status(conn, blob_id, Status.DISCOVERED, error_message=None)
                log.error(
                    "[%s] SESSION EXPIRED on %s: %s", state.name, blob_id, e,
                )
                break
            except DownloadCapExhausted as e:
                # The account really is capped (even if our configured cap said
                # otherwise). Cool it down until its oldest in-window download
                # ages out — self-calibrating.
                res.cap_bounces += 1
                free_at = db.next_free_at(conn, state.name, now)
                state.cooldown_until = free_at
                db.set_status(conn, blob_id, Status.DISCOVERED, error_message=None)
                log.warning(
                    "[%s] cap bounce on %s: %s — cooldown until %s",
                    state.name, blob_id, e,
                    free_at.isoformat() if free_at else "next tick",
                )
                break
            except MarketDeskError as e:
                # A non-cap blob that isn't a PDF (ZIP/XLSX/data attachment). The
                # vault is PDF-only, so this is terminal: mark SKIPPED_UNSUPPORTED
                # so next_candidate never re-selects it (retrying only wastes quota).
                res.unsupported += 1
                db.set_status(conn, blob_id, Status.SKIPPED_UNSUPPORTED,
                              error_message=str(e)[:500])
                log.info("[%s] unsupported blob %s (not a PDF) — skipping: %s",
                         state.name, blob_id, e)
                pulled += 1
            except Exception as e:  # noqa: BLE001 - bad paper, keep going
                res.errors += 1
                if _is_driver_dead(e):
                    # The TRANSPORT died, not the paper: put the paper straight
                    # back in the queue (never FAILED — it never got a fair try)
                    # and end this account's tick. Continuing would spin through
                    # the whole queue marking good papers FAILED, which is exactly
                    # what the 17h wedge did.
                    res.driver_dead += 1
                    driver_dead += 1
                    db.set_status(conn, blob_id, Status.DISCOVERED, error_message=None)
                    log.error(
                        "[%s] driver/transport failure on %s: %s — ending this "
                        "account's tick", state.name, blob_id, e,
                    )
                    break
                db.set_status(conn, blob_id, Status.FAILED, error_message=str(e)[:500])
                log.error("[%s] download failed for %s: %s", state.name, blob_id, e)
                pulled += 1

        # dead-driver watchdog: a tick counts against the account only when it
        # actually TRIED something and every attempt died on the driver. A tick
        # with no attempts (no quota, no candidate, cooled down) is not evidence
        # either way and leaves the counter alone.
        if attempts > 0:
            if driver_dead == attempts:
                state.driver_dead_ticks += 1
                log.warning(
                    "[%s] tick had %d/%d attempts die on the driver "
                    "(consecutive dead ticks: %d/%d)",
                    state.name, driver_dead, attempts, state.driver_dead_ticks,
                    DRIVER_DEAD_TICKS_BEFORE_REOPEN,
                )
            else:
                state.driver_dead_ticks = 0
    return res


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------
def _open_session(cfg: Config, state: AccountState) -> bool:
    """Open + auth-probe ONE account's persistent session. Returns whether the
    account came up authenticated. Non-fatal on failure: a broken/unauthenticated
    profile is logged, marked not-authed, and skipped by the loop."""
    acct_cfg = _profile_cfg(cfg, state.profile)
    try:
        sess = BrowserSession(acct_cfg)
        sess.__enter__()
        state.session = sess
        state.authed = sess.is_authenticated()
        if state.authed:
            state.client = MarketDeskClient(sess.context, acct_cfg)
            log.info("[%s] session ready (%s)", state.name, state.profile.path)
        else:
            log.warning(
                "[%s] NOT authenticated (%s) — skipping this account. "
                "Run `MARKETDESK_PROFILE_DIR=%s marketdesk auth` to log in.",
                state.name, state.profile.path, state.profile.path,
            )
    except Exception as e:  # noqa: BLE001
        log.error("[%s] failed to open session: %s", state.name, e)
        state.session = None
        state.client = None
        state.authed = False
    return state.authed


def _open_sessions(cfg: Config, states: list[AccountState]) -> None:
    """Open one persistent session per profile (see :func:`_open_session`)."""
    for state in states:
        _open_session(cfg, state)


def _close_session(state: AccountState) -> None:
    """Tear down ONE account's session. Never raises — a dead driver usually
    fails its own close, and that must not stop us re-opening."""
    if state.session is not None:
        try:
            state.session.__exit__(None, None, None)
        except Exception as e:  # noqa: BLE001
            log.warning("[%s] session close failed: %s", state.name, e)
    state.session = None
    state.client = None


def _close_sessions(states: list[AccountState]) -> None:
    for state in states:
        _close_session(state)


def _recycle_dead_sessions(cfg: Config, states: list[AccountState]) -> None:
    """Recycle any account whose driver has been dead for N consecutive ticks.

    The failure this exists for is silent: the Playwright transport dies, every
    download raises "Connection closed while reading from the driver", but
    ``state.authed`` stays True, so the loop keeps ticking forever and downloads
    nothing (observed: 17+ hours). Closing and re-opening THAT account's session
    is the fix; when even the re-open keeps failing, the process is unrecoverable
    in-place, so we ``sys.exit(1)`` and let launchd's ``KeepAlive`` give us a
    clean process. Other accounts are untouched — one dead driver is not a reason
    to recycle a healthy sibling.
    """
    for state in states:
        if state.driver_dead_ticks < DRIVER_DEAD_TICKS_BEFORE_REOPEN:
            continue
        log.warning(
            "[%s] driver dead for %d consecutive ticks — recycling session",
            state.name, state.driver_dead_ticks,
        )
        _close_session(state)
        state.driver_dead_ticks = 0
        if _open_session(cfg, state):
            state.reopen_failures = 0
            log.info("[%s] session recycled successfully", state.name)
            continue
        state.reopen_failures += 1
        log.error(
            "[%s] session re-open FAILED (%d consecutive)",
            state.name, state.reopen_failures,
        )
        if state.reopen_failures >= REOPEN_FAILURES_BEFORE_EXIT:
            log.error(
                "[%s] session re-open failed %d times — exiting(1) so the "
                "supervisor (launchd KeepAlive) restarts the process cleanly",
                state.name, state.reopen_failures,
            )
            _close_sessions(states)
            sys.exit(1)


def _profile_cfg(cfg: Config, profile: Profile) -> Config:
    """A shallow per-account copy of cfg with ``profile_dir`` swapped so the
    session opens THIS account's persistent Chromium profile. All other paths
    (DB, R2, vault) are shared."""
    import copy

    acct = copy.copy(cfg)
    acct.profile_dir = profile.path
    return acct


def _refresh_queue(
    cfg: Config, conn, states: list[AccountState],
    *, since_hours: int | None = None, heal_limit: int | None = None,
    limit: int | None = None,
) -> None:
    """Refresh the new-post queue via the UNCAPPED discovery API on ONE authed
    session (discovery results are shared across all accounts).

    ``since_hours`` defaults to the NARROW window (new window + 24h) and
    ``heal_limit`` / ``limit`` to ``discover``'s own defaults; the daily WIDE pass
    overrides all three (see :func:`run_trickle`). ``limit`` matters there:
    ``walk_papers`` caps SCANNED items with it, and the default
    (``MAX_ARTICLES_PER_RUN`` = 300) covers only ~1.5 days of posting volume —
    a truncated wide pass silently re-examines nothing older (observed on the
    first production wide pass: exactly ``scanned=300``). Discovery is uncapped,
    so a wide pass costs API calls and wall-clock, never download quota.
    """
    from .discover import discover

    authed = next((s for s in states if s.authed and s.client is not None), None)
    if authed is None:
        log.warning("trickle discover: no authenticated account; skipping refresh")
        return
    if since_hours is None:
        since_hours = cfg.new_window_hours + 24  # a little older than the new window
    kwargs = {} if heal_limit is None else {"heal_limit": heal_limit}
    if limit is not None:
        kwargs["limit"] = limit
    try:
        res = discover(cfg, conn, authed.client, since_hours=since_hours, **kwargs)
        log.info(
            "trickle discover (via %s, since=%dh): %s",
            authed.name, since_hours, res.summary(),
        )
    except SessionExpired as e:
        # Park the account rather than logging a soft warning: a logged-out
        # discovery returns a clean-looking scanned=0, which is indistinguishable
        # from a quiet news day and is precisely what hid the 2026-08-07 lapse.
        authed.authed = False
        log.error("[%s] SESSION EXPIRED during discovery: %s", authed.name, e)
    except Exception as e:  # noqa: BLE001
        log.warning("trickle discover failed: %s", e)


def _reset_failed(conn) -> int:
    """FAILED papers failed on the cap (not bad content) — reset to DISCOVERED so
    they re-enter the candidate pool. Run at loop start AND on every wide pass, so
    a long-lived daemon re-tries them daily rather than only on restart."""
    rows = db.get_by_status(conn, [Status.FAILED])
    for r in rows:
        db.set_status(conn, r["blob_id"], Status.DISCOVERED, error_message=None)
    return len(rows)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def run_trickle(
    cfg: Config,
    *,
    once: bool = False,
    dry_run: bool = False,
    max_iterations: int | None = None,
    profile: allocator.HourlyProfile | None = None,
    per_tick_cap: int = DOWNLOADS_PER_ACCOUNT_PER_TICK,
    now_fn: Callable[[], datetime] = utc_now,
    sleep_fn: Callable[[float], None] = time.sleep,
    monotonic_fn: Callable[[], float] = time.monotonic,
) -> list[TickResult]:
    """Run the trickle loop. Returns the per-tick results (handy for tests).

    ``now_fn`` / ``sleep_fn`` / ``monotonic_fn`` are injectable so a test can drive
    ticks with a fixed clock and no real sleeping. ``dry_run`` prints the plan and
    downloads nothing (sessions are still opened to report real auth + quota
    state).

    Discovery cadence: every ``DISCOVER_EVERY_SEC`` the queue is refreshed over
    the NARROW window. Every ``TRICKLE_WIDE_DISCOVER_EVERY_SEC`` — and always on
    the FIRST refresh after start, so a restart heals immediately — that refresh
    is instead WIDE (``TRICKLE_WIDE_DISCOVER_HOURS`` back,
    ``TRICKLE_WIDE_HEAL_LIMIT`` heals) and also resets FAILED rows to DISCOVERED.
    The narrow refresh only re-examines papers inside its own window, so
    late-arriving AI summaries and truncated titles on OLDER papers can only ever
    be healed by this pass — it replaces the manual wide `marketdesk discover`."""
    cfg.ensure_dirs()
    conn = db.connect(cfg.database_url)
    db.init_db(conn)

    states = [AccountState(profile=p) for p in cfg.profiles]
    log.info(
        "trickle starting: %d profile(s)=%s cap=%d/24h new_window=%dh "
        "reserve=%dh interval=%ds discover_every=%ds wide_every=%ds/%dh%s",
        len(states), [s.name for s in states], cfg.download_cap_per_account_24h,
        cfg.new_window_hours, cfg.backfill_reserve_hours, cfg.trickle_interval_sec,
        cfg.discover_every_sec, cfg.trickle_wide_discover_every_sec,
        cfg.trickle_wide_discover_hours, " [DRY-RUN]" if dry_run else "",
    )

    if not dry_run:
        n = _reset_failed(conn)
        if n:
            log.info("reset %d FAILED papers to DISCOVERED (cap-failures, retryable)", n)

    results: list[TickResult] = []
    _open_sessions(cfg, states)
    # ``None`` = "never happened yet" (a monotonic clock can legitimately read
    # 0.0, so 0.0 is not usable as the sentinel).
    last_discover: float | None = None
    last_wide_discover: float | None = None
    try:
        iteration = 0
        while True:
            cfg.assert_storage_ready()
            now = now_fn()
            # refresh the new-post queue on a cadence (skip in dry-run: read-only)
            mono = monotonic_fn()
            if not dry_run and (last_discover is None
                                or mono - last_discover >= cfg.discover_every_sec):
                wide = (last_wide_discover is None
                        or mono - last_wide_discover
                        >= cfg.trickle_wide_discover_every_sec)
                if wide:
                    # cap-FAILED papers re-enter the pool DAILY, not just at start
                    n = _reset_failed(conn)
                    log.info(
                        "wide discover pass: since=%dh heal_limit=%d "
                        "(reset %d FAILED -> DISCOVERED)",
                        cfg.trickle_wide_discover_hours, cfg.trickle_wide_heal_limit, n,
                    )
                    _refresh_queue(
                        cfg, conn, states,
                        since_hours=cfg.trickle_wide_discover_hours,
                        heal_limit=cfg.trickle_wide_heal_limit,
                        limit=cfg.trickle_wide_discover_limit,
                    )
                    last_wide_discover = mono
                else:
                    _refresh_queue(cfg, conn, states)
                last_discover = mono

            tick = run_tick(cfg, conn, states, now, dry_run=dry_run,
                            profile=profile, per_tick_cap=per_tick_cap)
            results.append(tick)
            if not dry_run:
                # may sys.exit(1) when an account's session cannot be re-opened
                _recycle_dead_sessions(cfg, states)

            # per-tick log line + dry-run plan print
            for plan in tick.plans:
                if dry_run:
                    print(plan.describe())
                log.info("tick plan %s", plan.describe())
            if not dry_run:
                log.info("tick done: %s", tick.summary())

            iteration += 1
            if once or (max_iterations is not None and iteration >= max_iterations):
                break
            sleep_fn(cfg.trickle_interval_sec)
    finally:
        _close_sessions(states)
        conn.close()
    return results
