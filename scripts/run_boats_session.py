"""One finite overnight BOATS session over bounded incumbent publisher segments.

SCOPE. This module orchestrates repeats of the existing
``scripts.build_ext_quotes.publish_boats_stream`` segment so that a single
calendar launch can cover one real overnight session (20:00 ET → 04:00 ET,
tied to the following US cash session by the incumbent
``boats_session_date``). It owns session bookkeeping only: budgets, window
arithmetic, single-writer exclusion, start receipts and terminal reasons.
All stream, archive, reduction and publication logic remains in the
incumbent publisher and is called unmodified.

LAUNCH CONTRACT. Two local calendar candidates (17:00 and 18:00 Vancouver)
cover both B.C.'s permanent UTC-7 from March 2026 and older host timezone data.
Only the candidate in the first 15 minutes after 20:00 New York is admitted
with --scheduled. The real NYSE session and immutable start receipt remain
mandatory. No OS timezone change, interval relaunch or retry is performed.

BOUNDS (all enforced before and during the run):
  * at most 8 wall-clock hours and at most 32 segments per session;
  * every segment is passed to the incumbent with
    ``max_seconds <= 3600`` and ``max_messages <= 10_000_000`` (the
    incumbent's own bounds) and the seconds re-clamped against the real
    time remaining until 04:00 ET before each segment. Socket cleanup and
    final archival may finish later; the incumbent emits only empty
    invalidations outside the overnight window, never an eligible trade;
  * the total message budget is an explicit required input (``--publish``)
    and is capped at 80,000,000. A returned segment's actual
    ``raw_messages`` count consumes the night budget;
  * sequential segments only — a segment starts only after the previous
    one has returned, so there is never overlap.

STOP RULES. The run stops after the caps, outside the overnight window, on
any exception, when ``publication_ok is not True`` (which includes a
structured storage access denial — a denial is never reopened), when the
segment reports ``transport_breaks > 0`` (a break invalidates display
state downstream; continuity is never inferred across one), or on clock
regression / overnight-session change. A failed or uncertain segment is
never retried and there is no automatic recovery or replay.

SINGLE WRITER. Before any stream effect the configured mounted archive is
required through the incumbent ``require_external_root`` with a >= 40 GiB
reserve, a valid symbols file is read through the existing ``load_symbols``
helper and validated by the incumbent coverage constructor, then a
non-blocking kernel lock plus an O_EXCL per-trading-session start receipt
are taken in the existing archive's ``run-receipts`` area. The start
receipt is permanent until lawful manual reconciliation: a crashed run
leaves it in place and therefore blocks any later same-session replay.

EFFECTS. The default mode is a bounded dry-run plan: no stream, no R2, no
lock and no run-start receipt. ``--publish`` requires the explicit budgets
and paths and still refuses to start outside the overnight window. The
30-second consumer expiry and per-segment ended invalidation belong to the
incumbent publisher and are preserved untouched. This module never adopts
or resumes the original finite run
``tiingo-boats-publish-20261012-01a12ab6``.
"""
from __future__ import annotations

import argparse
import errno
import fcntl
import json
import logging
import os
import shutil
import signal
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, time as dtime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Optional
from zoneinfo import ZoneInfo

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from lib.nyse_calendar import ET
from scripts.build_ext_quotes import boats_session_date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [boats_session] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("run_boats_session")

SCHEMA = "mastermind.boats_session_run.v1"

# Hard session bounds. PER_SEGMENT_* mirror the incumbent publisher's own
# argument validation so a clamped plan can never be rejected downstream.
MAX_SEGMENTS = 32
MAX_TOTAL_SECONDS = 8 * 3600
PER_SEGMENT_MAX_SECONDS = 3600
PER_SEGMENT_MAX_MESSAGES = 10_000_000
MAX_TOTAL_MESSAGES = 80_000_000
# Drive reserve required before any stream effect (design constant).
MIN_ARCHIVE_FREE_BYTES = 40 * 1024 ** 3
# Wall-clock tolerance before a backwards jump is called a clock regression.
CLOCK_REGRESSION_TOLERANCE_S = 2.0

SESSION_END_ET = dtime(4, 0)

# Original finite run this source must never adopt or resume.
FOREIGN_RUN_ID = "tiingo-boats-publish-20261012-01a12ab6"


class SessionRefused(RuntimeError):
    """A precondition failed before any stream effect; the run did not start."""


class StartReceiptBlocked(SessionRefused):
    """A same-session start receipt already exists (prior run or crash)."""


class HostTimezoneError(SessionRefused):
    """Host timezone does not match the configured Vancouver calendar carrier."""


class SessionInterrupted(RuntimeError):
    """A process termination request; cleanup must never start another segment."""


def _interrupt(signum: int, _frame: Any) -> None:
    raise SessionInterrupted(f"signal {signum}")


@dataclass(frozen=True)
class SessionConfig:
    """Everything a real run needs; every field is explicit for --publish."""

    publish: bool
    symbols_file: str
    archive_root: str
    total_max_messages: int = MAX_TOTAL_MESSAGES
    max_segments: int = MAX_SEGMENTS
    segment_max_seconds: int = PER_SEGMENT_MAX_SECONDS
    total_max_seconds: int = MAX_TOTAL_SECONDS
    scheduled: bool = False

    def __post_init__(self) -> None:
        if type(self.scheduled) is not bool:
            raise SessionRefused("scheduled must be a boolean")
        if type(self.total_max_messages) is not int or not 1 <= self.total_max_messages <= MAX_TOTAL_MESSAGES:
            raise SessionRefused(
                f"total message budget must be an integer in 1..{MAX_TOTAL_MESSAGES}")
        if type(self.max_segments) is not int or not 1 <= self.max_segments <= MAX_SEGMENTS:
            raise SessionRefused(f"segment cap must be an integer in 1..{MAX_SEGMENTS}")
        if type(self.segment_max_seconds) is not int or not 1 <= self.segment_max_seconds <= PER_SEGMENT_MAX_SECONDS:
            raise SessionRefused(
                f"per-segment seconds must be an integer in 1..{PER_SEGMENT_MAX_SECONDS}")
        if type(self.total_max_seconds) is not int or not 1 <= self.total_max_seconds <= MAX_TOTAL_SECONDS:
            raise SessionRefused(
                f"total seconds budget must be an integer in 1..{MAX_TOTAL_SECONDS}")
        if self.max_segments * self.segment_max_seconds < self.total_max_seconds:
            raise SessionRefused("segment plan cannot cover the configured time budget")
        if self.publish and not (self.symbols_file and self.archive_root):
            raise SessionRefused("publish requires explicit symbols file and archive root")


@dataclass
class _Clock:
    """Injectable clock so tests can drive midnight, 04:00 ET and DST."""

    base_utc: Optional[datetime] = None
    base_monotonic: Optional[float] = None

    def now_utc(self) -> datetime:
        return self.base_utc or datetime.now(timezone.utc)

    def monotonic(self) -> float:
        return time.monotonic() if self.base_monotonic is None else self.base_monotonic


# ---------------------------------------------------------------------------
# Timezone / window arithmetic
# ---------------------------------------------------------------------------

def _zone_name(tzinfo: Any) -> str:
    return getattr(tzinfo, "key", None) or getattr(tzinfo, "zone", None) or ""


def _host_zone_name() -> str:
    """Read the OS zone used by launchd, independently of process TZ overrides."""
    try:
        target = os.readlink("/etc/localtime")
    except OSError as exc:
        raise HostTimezoneError("OS timezone name cannot be verified") from exc
    if "zoneinfo/" not in target:
        raise HostTimezoneError("OS timezone is not a recognized zoneinfo link")
    return target.rsplit("zoneinfo/", 1)[1]


def validate_host_timezone(now_utc: datetime, local_tz: Any = None) -> dict[str, Any]:
    """Require the configured host zone and a supported Vancouver clock.

    B.C. keeps UTC-7 after March 2026; older host tzdata may still use UTC-8
    in winter. Finite calendar candidates cover either representation, while
    the New York entry gate decides whether this invocation may start.
    Never change the OS clock or infer the market window from a fixed delta.
    """
    if local_tz is None:
        zone = _host_zone_name()
        if zone != "America/Vancouver":
            raise HostTimezoneError(f"OS timezone {zone!r} does not match America/Vancouver")
        local_tz = ZoneInfo(zone)
    local = now_utc.astimezone(local_tz)
    et = now_utc.astimezone(ET)
    offset = local.utcoffset() - et.utcoffset()
    zone = _zone_name(local.tzinfo)
    checks = {"offset_ok": local.utcoffset() in {timedelta(hours=-7), timedelta(hours=-8)},
              "zone_ok": True if not zone else zone == "America/Vancouver"}
    result = {"host_zone": zone, "local_offset_vs_et_seconds": int(offset.total_seconds()),
              "supported_host_utc_offsets_seconds": [-28800, -25200],
              "host_timezone_ok": all(checks.values()), **checks,
              "now_local": local.isoformat(), "now_et": et.isoformat()}
    if not result["host_timezone_ok"]:
        raise HostTimezoneError(
            "host timezone does not match the deployment contract "
            f"(zone={zone or 'unknown'}, offset vs ET={int(offset.total_seconds())}s, "
            "expected America/Vancouver with a UTC-7 or UTC-8 host clock): refusing to start")
    return result


def scheduled_session_due(now_utc: datetime) -> bool:
    """One market-open admission window, independent of host clock changes."""
    local = now_utc.astimezone(ET)
    return local.hour == 20 and local.minute < 15 and boats_session_date(now_utc) is not None


def overnight_boundary_et(now_utc: datetime) -> datetime:
    """04:00 ET on the calendar date of the current overnight session.

    Mirrors the incumbent publisher's own boundary arithmetic (evening hours
    roll to the next morning; early hours stay on today)."""
    local = now_utc.astimezone(ET)
    day = local.date() + timedelta(days=1 if local.hour >= 20 else 0)
    return datetime.combine(day, SESSION_END_ET, tzinfo=ET)


def seconds_until_boundary(now_utc: datetime) -> int:
    return max(0, int((overnight_boundary_et(now_utc) - now_utc).total_seconds()))


def clamp_segment(*, seconds_remaining: int, seconds_to_boundary: int,
                  messages_remaining: int, segment_max_seconds: int) -> dict[str, int]:
    """Bounded next-segment plan; {} when nothing can legally run."""
    seg_seconds = min(segment_max_seconds, seconds_to_boundary, seconds_remaining,
                      PER_SEGMENT_MAX_SECONDS)
    seg_messages = min(messages_remaining, PER_SEGMENT_MAX_MESSAGES)
    if seg_seconds < 1 or seg_messages < 1:
        return {}
    return {"max_seconds": int(seg_seconds), "max_messages": int(seg_messages)}


# ---------------------------------------------------------------------------
# Archive / coverage preconditions
# ---------------------------------------------------------------------------

def prepare_archive(archive_root: str) -> dict[str, Any]:
    """Require the incumbent mounted archive and a >= 40 GiB reserve.

    Uses the existing ``require_external_root`` so the mount contract stays
    the incumbent's. Read-only: nothing is created outside the run-receipt
    area later, and no stream effect happens on failure."""
    from collectors.tiingo_archive import require_external_root
    base = require_external_root(Path(archive_root), check_mount=True)
    free = shutil.disk_usage(str(base)).free
    if free < MIN_ARCHIVE_FREE_BYTES:
        raise SessionRefused(
            f"archive reserve {free} bytes below required {MIN_ARCHIVE_FREE_BYTES}")
    return {"archive_root": str(base), "free_bytes": free,
            "required_free_bytes": MIN_ARCHIVE_FREE_BYTES}


def load_and_validate_symbols(symbols_file: str) -> list[str]:
    """Read coverage through the existing helper, validate via the incumbent."""
    from scripts.tiingo_ingest import load_symbols
    from scripts.build_ext_quotes import BoatsLastTrade, MAX_BOATS_SYMBOLS
    symbols = load_symbols("", symbols_file, limit=MAX_BOATS_SYMBOLS)
    if not symbols:
        raise SessionRefused("symbols file produced no coverage; refusing to default")
    # The incumbent constructor enforces bounded, unique, path-safe, uppercase
    # coverage. An empty file must never silently fall back to the watchlist.
    BoatsLastTrade(symbols, "coverage-validation")
    return symbols


# ---------------------------------------------------------------------------
# Single-writer exclusion: kernel lock + O_EXCL per-session start receipt
# ---------------------------------------------------------------------------

def receipt_dir(archive_root: str | Path) -> Path:
    """The existing archive's run-receipt area (created on first real run)."""
    return Path(archive_root) / "run-receipts"


def _fsync_dir(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def acquire_session_lock(archive_root: str | Path) -> int:
    """Non-blocking exclusive lock held for the whole run; -1 fd on refusal.

    The lock file itself is permanent (deleting it would race a concurrent
    acquirer onto a fresh inode)."""
    area = receipt_dir(archive_root)
    area.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(area / "session.lock"), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        os.close(fd)
        if exc.errno in (errno.EACCES, errno.EAGAIN):
            raise SessionRefused(
                "another overnight-session writer holds the kernel lock") from None
        raise
    return fd


def _write_receipt(path: Path, payload: dict[str, Any]) -> None:
    """O_EXCL + fsync + atomic rename so a receipt is never partially visible."""
    body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, body)
        os.fsync(fd)
    finally:
        os.close(fd)
    if path.exists():
        os.unlink(str(tmp))
        raise StartReceiptBlocked(f"start receipt appeared concurrently: {path}")
    os.replace(str(tmp), str(path))
    _fsync_dir(path.parent)


def write_start_receipt(archive_root: str | Path, session_date: str,
                        config: SessionConfig, started_at: datetime,
                        symbols_count: int, *, host_zone: str | None = None) -> Path:
    """Permanent per-trading-session start receipt (O_EXCL)."""
    area = receipt_dir(archive_root)
    area.mkdir(parents=True, exist_ok=True)
    path = area / f"run-start-{session_date}.json"
    payload = {
        "schema": SCHEMA,
        "kind": "run-start",
        "run_id": f"boats-session-{session_date}-{uuid.uuid4().hex[:12]}",
        "trading_session": session_date,
        "started_at_utc": started_at.isoformat(),
        "pid": os.getpid(),
        "host_zone": host_zone,
        "publish": config.publish,
        "total_max_messages": config.total_max_messages,
        "max_segments": config.max_segments,
        "segment_max_seconds": config.segment_max_seconds,
        "total_max_seconds": config.total_max_seconds,
        "symbols_file": config.symbols_file,
        "symbols_count": symbols_count,
        "archive_root": str(archive_root),
        "note": "permanent until lawful manual reconciliation; a crash here "
                "blocks later same-session replay",
    }
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise StartReceiptBlocked(
            f"session {session_date} already has a start receipt ({path}); "
            "same-session replay is blocked until lawful manual reconciliation") from None
    try:
        os.write(fd, json.dumps(payload, indent=2, sort_keys=True).encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_dir(area)
    return path


def write_final_receipt(archive_root: str | Path, session_date: str,
                        started_at: datetime, result: dict[str, Any]) -> Path:
    """Durable completed-run result: counts and explicit terminal reason."""
    area = receipt_dir(archive_root)
    area.mkdir(parents=True, exist_ok=True)
    stamp = started_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = area / f"run-final-{session_date}-{stamp}.json"
    _write_receipt(path, {"schema": SCHEMA, "kind": "run-final",
                          "trading_session": session_date,
                          "started_at_utc": started_at.isoformat(),
                          "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                          **result})
    return path


# ---------------------------------------------------------------------------
# Segment execution (the only call into the incumbent publisher)
# ---------------------------------------------------------------------------

def _run_segment(*, max_seconds: int, max_messages: int,
                 symbols: list[str], publish: bool, archive_root: str) -> dict[str, Any]:
    """One bounded incumbent segment. Indirection kept for deterministic tests."""
    from scripts.build_ext_quotes import publish_boats_stream
    from collectors.tiingo_archive import Archive
    archive = Archive(Path(archive_root), free_floor=MIN_ARCHIVE_FREE_BYTES)
    return publish_boats_stream(max_seconds=max_seconds, max_messages=max_messages,
                                symbols=symbols, publish=publish, archive=archive)


def run_session(config: SessionConfig, *, clock: Optional[_Clock] = None,
                segment_runner: Callable[..., dict[str, Any]] = _run_segment,
                archive_prep: Callable[[str], dict[str, Any]] = prepare_archive,
                local_tz: Any = None) -> dict[str, Any]:
    """One finite overnight session. Returns the durable terminal result."""
    clock = clock or _Clock()
    started_at = clock.now_utc()
    started_mono = clock.monotonic()
    result: dict[str, Any] = {
        "schema": SCHEMA, "run_mode": "publish" if config.publish else "dry-run",
        "session_date": None, "segments_run": 0, "raw_messages_total": 0,
        "bytes_total": 0, "messages_budget": config.total_max_messages,
        "max_segments": config.max_segments,
        "total_seconds_budget": config.total_max_seconds,
        "terminal_reason": None, "stopped_outside_window": False,
        "publication_ok_last": None, "start_receipt": None, "final_receipt": None,
        "capture_ids": [], "last_segment": None, "window_end_reached": False,
    }
    lock_fd: Optional[int] = None
    symbols: list[str] = []

    def finish(reason: str, *, outside: bool = False) -> dict[str, Any]:
        result["terminal_reason"] = reason
        result["stopped_outside_window"] = outside
        result["elapsed_seconds"] = round(clock.monotonic() - started_mono, 3)
        result["finished_at_utc"] = clock.now_utc().isoformat()
        if config.publish and result["start_receipt"]:
            try:
                result["final_receipt"] = str(write_final_receipt(
                    config.archive_root, result["session_date"], started_at, result))
            except OSError as exc:
                log.error("final receipt write failed (%s); start receipt remains", exc)
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(lock_fd)
            result["lock_released"] = True
        log.info("overnight session finished: %s", json.dumps(result))
        return result

    # 1. Host timezone contract (before any effect). A dry-run records the
    # finding in its plan instead of refusing; a real run refuses outright.
    try:
        tz = validate_host_timezone(started_at, local_tz=local_tz)
    except HostTimezoneError as exc:
        if not config.publish:
            result["host_timezone_ok"] = False
            result["host_timezone_error"] = str(exc)
            return finish("host_timezone_mismatch")
        raise
    result["host_timezone_ok"] = tz["host_timezone_ok"]
    result["host_zone"] = tz["host_zone"]

    if config.scheduled and not scheduled_session_due(started_at):
        return finish("scheduled_candidate_not_due", outside=True)

    # 2. Real overnight window (holidays/DST via the incumbent calendar).
    session = boats_session_date(started_at)
    result["session_date"] = session
    if session is None:
        return finish("outside_overnight_window", outside=True)

    # 3. Coverage: existing read helper + incumbent validation, before effects.
    from collectors.tiingo_archive import TiingoArchiveError
    try:
        symbols = load_and_validate_symbols(config.symbols_file)
    except (ValueError, OSError, TiingoArchiveError) as exc:
        raise SessionRefused(f"coverage precondition: {exc}") from exc
    result["symbols_count"] = len(symbols)

    if not config.publish:
        # Dry-run: bounded plan only. No stream, no R2, no lock, no start receipt.
        result["first_segment_plan"] = clamp_segment(
            seconds_remaining=config.total_max_seconds,
            seconds_to_boundary=seconds_until_boundary(started_at),
            messages_remaining=config.total_max_messages,
            segment_max_seconds=config.segment_max_seconds)
        result["seconds_to_boundary"] = seconds_until_boundary(started_at)
        return finish("dry_run_plan")

    # 4. Mounted archive + reserve.
    try:
        archive_info = archive_prep(config.archive_root)
    except (ValueError, OSError, TiingoArchiveError) as exc:
        raise SessionRefused(f"archive precondition: {exc}") from exc
    result.update(archive_info)

    # 5. Single writer: nonblocking kernel lock, then permanent start receipt.
    lock_fd = acquire_session_lock(config.archive_root)
    try:
        receipt = write_start_receipt(config.archive_root, session, config,
                                      started_at, len(symbols), host_zone=tz["host_zone"])
    except BaseException:
        os.close(lock_fd)
        raise
    result["start_receipt"] = str(receipt)

    # 6. Sequential bounded segments; budget consumed by actual returns.
    last_wall = started_at.timestamp()
    boundary = overnight_boundary_et(started_at).astimezone(timezone.utc)
    for _ in range(config.max_segments):
        now = clock.now_utc()
        wall = now.timestamp()
        if wall < last_wall - CLOCK_REGRESSION_TOLERANCE_S:
            return finish("clock_regression")
        if abs((wall - started_at.timestamp()) - (clock.monotonic() - started_mono)) > CLOCK_REGRESSION_TOLERANCE_S:
            return finish("clock_discontinuity")
        last_wall = wall
        if now >= boundary and now - boundary < timedelta(minutes=1):
            result["window_end_reached"] = True
            return finish("overnight_window_closed", outside=True)
        current_session = boats_session_date(now)
        if current_session is None:
            return finish("outside_overnight_window", outside=True)
        if current_session != session:
            return finish("clock_or_session_change")
        elapsed = clock.monotonic() - started_mono
        seconds_remaining = int(config.total_max_seconds - elapsed)
        messages_remaining = config.total_max_messages - result["raw_messages_total"]
        plan = clamp_segment(seconds_remaining=max(0, seconds_remaining),
                             seconds_to_boundary=seconds_until_boundary(now),
                             messages_remaining=messages_remaining,
                             segment_max_seconds=config.segment_max_seconds)
        if not plan:
            if messages_remaining < 1:
                return finish("message_budget_exhausted")
            if seconds_remaining < 1:
                return finish("time_budget_exhausted")
            return finish("overnight_window_closed", outside=True)
        try:
            seg = segment_runner(max_seconds=plan["max_seconds"],
                                 max_messages=plan["max_messages"],
                                 symbols=symbols, publish=config.publish,
                                 archive_root=config.archive_root)
            result["segments_run"] += 1
            if not isinstance(seg, dict):
                raise ValueError("segment result is not an object")
            raw = seg.get("raw_messages")
            size = seg.get("bytes")
            breaks = seg.get("transport_breaks")
            if type(raw) is not int or raw < 0 or raw > plan["max_messages"]:
                return finish("count_overflow")
            if type(size) is not int or size < 0 or type(breaks) is not int or breaks < 0:
                raise ValueError("segment byte/transport counts are invalid")
            retained_segment = {key: seg.get(key) for key in (
                "capture_id", "connections", "segments", "transport_breaks", "raw_messages",
                "bytes", "publication", "publication_ok")}
            # Validate retained metadata before either banking counts or writing receipts.
            json.dumps(retained_segment, allow_nan=False)
            result["last_segment"] = retained_segment
            if isinstance(seg.get("capture_id"), str):
                result["capture_ids"].append(seg["capture_id"])
            result["bytes_total"] += size
            result["raw_messages_total"] += raw
            result["publication_ok_last"] = seg.get("publication_ok")
            if breaks > 0:
                result["last_transport_breaks"] = breaks
                return finish("transport_break")
            if config.publish and seg.get("publication_ok") is not True:
                return finish("publication_not_ok")
        except Exception as exc:  # noqa: BLE001 — any exception stops the night
            log.error("segment raised %s: %s", type(exc).__name__, exc)
            result["exception"] = type(exc).__name__
            return finish(f"exception:{type(exc).__name__}")
        log.info("segment %d settled raw_messages=%d budget_left=%d",
                 result["segments_run"], raw,
                 config.total_max_messages - result["raw_messages_total"])
    now = clock.now_utc()
    if boundary <= now < boundary + timedelta(minutes=1):
        result["window_end_reached"] = True
        return finish("overnight_window_closed", outside=True)
    return finish("segment_cap_reached")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="One finite overnight BOATS session over bounded incumbent segments.")
    parser.add_argument("--publish", action="store_true",
                        help="Run the real bounded session (default is a dry-run plan).")
    parser.add_argument("--scheduled", action="store_true",
                        help="Admit a calendar candidate only just after 20:00 New York.")
    parser.add_argument("--symbols-file",
                        help="Bounded line-oriented BOATS coverage (required for --publish).")
    parser.add_argument("--archive-root",
                        help="Configured mounted archive root (required for --publish).")
    parser.add_argument("--total-max-messages", type=int,
                        help=f"Explicit night message budget, 1..{MAX_TOTAL_MESSAGES} "
                             "(required for --publish).")
    parser.add_argument("--total-max-seconds", type=int, default=MAX_TOTAL_SECONDS,
                        help=f"Session capture budget in seconds, 1..{MAX_TOTAL_SECONDS} "
                             f"(default {MAX_TOTAL_SECONDS}; cleanup may finish later).")
    parser.add_argument("--max-segments", type=int, default=MAX_SEGMENTS,
                        help=f"Segment cap, 1..{MAX_SEGMENTS} (default {MAX_SEGMENTS}).")
    parser.add_argument("--segment-max-seconds", type=int, default=PER_SEGMENT_MAX_SECONDS,
                        help=f"Per-segment seconds, 1..{PER_SEGMENT_MAX_SECONDS} "
                             f"(default {PER_SEGMENT_MAX_SECONDS}).")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        total = args.total_max_messages
        if args.publish:
            if total is None:
                raise SessionRefused("--publish requires an explicit --total-max-messages")
            if not args.symbols_file:
                raise SessionRefused("--publish requires an explicit --symbols-file")
            if not args.archive_root:
                raise SessionRefused("--publish requires an explicit --archive-root")
        elif total is None:
            # Dry-run plans against the documented ceiling without any effect.
            total = MAX_TOTAL_MESSAGES
        config = SessionConfig(
            publish=args.publish, symbols_file=args.symbols_file or "",
            archive_root=args.archive_root or "", total_max_messages=total,
            total_max_seconds=args.total_max_seconds, max_segments=args.max_segments,
            segment_max_seconds=args.segment_max_seconds, scheduled=args.scheduled)
    except SessionRefused as exc:
        log.error("refusing to start: %s", exc)
        return 2
    original_handlers = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        for sig in original_handlers:
            signal.signal(sig, _interrupt)
        result = run_session(config)
    except HostTimezoneError as exc:
        log.error("%s", exc)
        return 3
    except StartReceiptBlocked as exc:
        log.error("start refused: %s", exc)
        return 4
    except SessionRefused as exc:
        log.error("precondition failed before any stream effect: %s", exc)
        return 2
    except Exception as exc:  # noqa: BLE001 — precondition failures never loop
        log.error("session aborted before completion: %s: %s", type(exc).__name__, exc)
        return 1
    finally:
        for sig, handler in original_handlers.items():
            signal.signal(sig, handler)
    if args.publish:
        reason = result["terminal_reason"]
        if reason in {"segment_cap_reached", "message_budget_exhausted", "time_budget_exhausted"}:
            log.warning("bounded run ended before window completion: %s", reason)
            return 5
        if reason not in {"overnight_window_closed", "outside_overnight_window", "scheduled_candidate_not_due"}:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
