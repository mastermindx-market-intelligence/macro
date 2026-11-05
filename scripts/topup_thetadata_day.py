#!/usr/bin/env python3
"""scripts/topup_thetadata_day.py — ThetaData T1 store top-up + daily maintainer.

WHY THIS EXISTS (R0.2, Options Superintelligence masterplan 2026-07-31)
─────────────────────────────────────────────────────────────────────────────
Historical observation: on 2026-07-31 20:42 ET, same-day greeks/oi/eod
returned zero rows. This is not a permanent provider availability rule. Current
EOD documentation names 17:15 ET report generation; actual availability remains
a separately retained observation. OI reports have their own overnight clock. The nightly backfill
refresh pass runs at ~16:10 ET and therefore only ever captures T-1. This
script started as a bounded pre-open top-up (N roots x 1 day) and is extended
here (AD-1T1, `research/AD1T1_INCREMENTAL_CADENCE_SPEC_2026-08-22.md`, R2) into
the canonical full-universe DAILY incremental maintainer of the T1 store, so a
normal market-day run keeps a lawful S/D source pair at >=90% AD-universe
coverage without the whole-year re-pull the old daily keepalive used.

THREE MODES
─────────────────────────────────────────────────────────────────────────────
    python -m scripts.topup_thetadata_day --roots SPY,QQQ [--date YYYY-MM-DD]
        Legacy bounded mode — byte-compatible behavior (§G). Pulls ONE session
        eod/oi/greeks for the named roots and merges into the store.

    python -m scripts.topup_thetadata_day --roots @universe --date YYYY-MM-DD
        Explicit catch-up (F10): same 3-tier one-day ensure as the legacy mode,
        but over the FULL resolved T1 universe. This is the runbook's tool for
        gaps of >=2 sessions — NOT the daily mode, which never sweeps history.

    python -m scripts.topup_thetadata_day --daily [--workers N] [--deadline-min M] [--force-run]
        Market-wide incremental daily mode (§A-§D). Gate-checked (F4), ensures
        exactly the S/D cells of §A4 for the full T1 universe, and writes a
        `daily_refresh` health receipt into the store's `_manifest.json`.

MERGE SEMANTICS
─────────────────────────────────────────────────────────────────────────────
The backfill's year-overwrite writer is DESTRUCTIVE for partial ranges, so this
script never calls it. Per root x tier it: reads the existing {YYYY}.parquet,
drops any rows already carrying the target date, appends the fresh day's rows,
sorts by date, and writes atomically (tmp -> os.replace). The next evening's
refresh pass re-pulls the whole year for these roots and overwrites — the
top-up rows are superseded by identical vendor data, so the store never forks.

WRITER EXCLUSION (§B)
─────────────────────────────────────────────────────────────────────────────
Every mutating writer of the T1 store (this script's legacy/@universe/daily
modes, and `scripts/backfill_thetadata_eod.py`) acquires a non-blocking
`fcntl.flock` on `{store}/_writer.lock` before its first parquet mutation. A
refusal mutates NOTHING (not even `_manifest.json`) and is announced with a
single JSON line (`{"event": "writer_locked", ...}`). The legacy/@universe
modes keep their existing exit-1 refusal shape; `--daily` exits 0 on refusal
(F14 — repeated nonzero exits would poison `launchctl print`'s LastExitStatus
as a daily false alarm).

Exit codes:
    Legacy / @universe modes: 0 = every requested root now has rows for the
        date (or already did); 2 = vendor has no data yet for ANY root;
        1 = partial, OR blocked (backfill running / lock refused).
    --daily mode: 0 = healthy receipt, no-op gate, OR lock refusal (F14);
        1 = partial/failed source receipt or failed downstream baseline refresh.

Usage:
    python -m scripts.topup_thetadata_day --roots SPY,QQQ --date 2026-07-30
    python -m scripts.topup_thetadata_day --roots SPY   # date defaults to the
                                                        # last weekday before today
    python -m scripts.topup_thetadata_day --roots @universe --date 2026-07-30
    python -m scripts.topup_thetadata_day --daily
"""
from __future__ import annotations

import argparse
import fcntl
import json
import logging
import math
import subprocess
import sys
import time as _time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, as_completed, wait
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date as _date, datetime, time as _time_of_day, timedelta, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.thetadata_store import resolve_thetadata_store  # noqa: E402
from lib import nyse_calendar  # noqa: E402

log = logging.getLogger("topup_thetadata_day")

TIERS = ("eod", "oi", "greeks")

# AD1T1-FROZEN-BY-FABLE: production --workers default for `--daily`, frozen
# from the 2026-08-23 quiet-window benchmark ladder (spec §F): zero errors at
# every W in 1/2/4/6, no concurrency knee through W=6, full-universe
# steady-state projection 25.8/12.6/6.0/4.6 min. W=4 is the ruling: ~10x
# headroom inside the 65-min deadline on a degraded-vendor day, and 4 of the
# Terminal's 8 request slots left free for any concurrent consumer. Every
# call site and every test reads this constant — never the literal.
_DAILY_WORKERS_DEFAULT = 4

_MAX_WORKERS = 6                 # hard vendor-safety cap (§A1) — Terminal ceiling is 8
# (RF7, R3) 65 min — the plist's four fire points are >=70 min apart (§E), so
# a run holding the lock for the full deadline still releases it before the
# NEXT fire; 100 min would let one held lock swallow a whole retry-ladder rung.
_DEFAULT_DEADLINE_MIN = 65       # §F2
_GATE_TIME_ET = _time_of_day(16, 10)
_REPROBE_FETCH_FAILED_FRACTION = 0.25   # F5
_S_SUSPECT_VENDOR_EMPTY_FRACTION = 0.50  # F12
# (N1, R3 verify-pass) minimum EOD[S]-attempted-roots floor before the
# s_suspect_non_session ratio means anything: max(5, ceil(5% of the T1
# universe)). Below this, eod_s_attempted is too small a sample either way.
_S_SUSPECT_MIN_ATTEMPT_FRACTION = 0.05

WRITER_LOCK_NAME = "_writer.lock"

_PRESENT_STATES = {"already_present", "complete"}


# ── legacy helpers (§G byte-compatibility — unchanged behavior) ─────────────
def _last_weekday_before(d: _date) -> _date:
    prev = d - timedelta(days=1)
    while prev.weekday() >= 5:
        prev -= timedelta(days=1)
    return prev


def _backfill_running() -> bool:
    try:
        rc = subprocess.run(["pgrep", "-f", "backfill_thetadata_eod"],
                            capture_output=True, check=False)
        return rc.returncode == 0
    except OSError:
        return False


def _tmp_path(dest: Path) -> Path:
    """(F9) `{YYYY}.parquet.tmp` — deliberately does NOT end in `.parquet`, so
    store readers' `*.parquet` glob (e.g. `engine/thetadata_store.py`) never
    matches a tmp file left behind by a SIGKILL between write and replace. The
    old `{YYYY}.tmp.parquet` shape (via `Path.with_suffix`) DID match that
    glob — a killed writer could double a root's rows on the next read."""
    return dest.with_name(dest.name + ".tmp")


def _write_atomic(df: pd.DataFrame, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp_path(dest)
    df.to_parquet(tmp, index=False)
    tmp.replace(dest)


def _merge_day(store: Path, tier: str, root: str, day: _date,
               fresh: pd.DataFrame) -> int:
    """Merge one day's rows into {store}/{tier}/{ROOT}/{YYYY}.parquet.

    Returns the number of rows now present for `day` in that parquet.
    """
    dest = store / tier / root.upper() / f"{day.year}.parquet"
    fresh = fresh.copy()
    fresh["date"] = pd.to_datetime(fresh["date"], errors="coerce")
    day_ts = pd.Timestamp(day)
    fresh = fresh[fresh["date"] == day_ts]
    if fresh.empty:
        return 0
    if dest.exists():
        existing = pd.read_parquet(dest)
        existing["date"] = pd.to_datetime(existing["date"], errors="coerce")
        kept = existing[existing["date"] != day_ts]
        merged = pd.concat([kept, fresh], ignore_index=True)
    else:
        merged = fresh
    merged = merged.sort_values("date").reset_index(drop=True)
    _write_atomic(merged, dest)
    return int(len(fresh))


def _has_day(store: Path, tier: str, root: str, day: _date) -> bool:
    dest = store / tier / root.upper() / f"{day.year}.parquet"
    if not dest.exists():
        return False
    try:
        col = pd.read_parquet(dest, columns=["date"])
    except Exception:  # noqa: BLE001 — unreadable parquet = treat as absent
        return False
    return bool((pd.to_datetime(col["date"], errors="coerce")
                 == pd.Timestamp(day)).any())


# ── writer exclusion (§B) ────────────────────────────────────────────────────
@contextmanager
def _writer_lock(store: Path):
    """Crash-safe advisory flock guarding ALL mutating writers of the T1 store.

    `fcntl.flock(LOCK_EX | LOCK_NB)` on `{store}/_writer.lock` (local APFS —
    flock is reliable there). The lock FILE persisting is harmless: the LOCK
    dies with the file descriptor, so process death (including SIGKILL)
    releases ownership and no stale file can wedge the source. Yields True if
    acquired, False if refused."""
    store.mkdir(parents=True, exist_ok=True)
    lock_path = store / WRITER_LOCK_NAME
    fh = open(lock_path, "a+")
    acquired = False
    try:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except OSError:
            acquired = False
        yield acquired
    finally:
        if acquired:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        fh.close()


def _emit_writer_locked(mode: str) -> None:
    """(§B) Machine-readable single-line refusal record to stdout."""
    print(json.dumps({"event": "writer_locked", "mode": mode}), flush=True)


def _sweep_stale_tmp(store: Path) -> int:
    """(F9, extended RF9/R3) Sweep stale tmp files under the flock at
    daily-mode startup.

    Sweeps BOTH the new `{YYYY}.parquet.tmp` shape this build writes and the
    legacy `{YYYY}.tmp.parquet` shape the pre-F9 writer used (a SIGKILL under
    the old naming could still be on disk from before this deploy — and the
    old shape is the one that actually corrupts reads, since it matches the
    store readers' `*.parquet` glob). (RF9) Also sweeps STORE-ROOT `*.tmp`
    files — a SIGKILL mid `_write_daily_receipt`/`_write_manifest` leaves
    `_manifest.json.tmp` sitting at the store root, not under a tier dir."""
    count = 0
    if not store.exists():
        return 0
    for tier in TIERS:
        tier_dir = store / tier
        if not tier_dir.exists():
            continue
        for pattern in ("*/*.parquet.tmp", "*/*.tmp.parquet"):
            for p in tier_dir.glob(pattern):
                try:
                    p.unlink()
                    count += 1
                except OSError:
                    pass
    for p in store.glob("*.tmp"):
        try:
            p.unlink()
            count += 1
        except OSError:
            pass
    return count


def _dated_greek_request_options(root: str) -> dict:
    """Compatibility entry point for the shared explicit writer policy."""
    from lib.options_source_receipts import dated_greek_request_options
    return dated_greek_request_options(root)


# ── legacy / @universe bounded 3-tier one-day ensure (§G) ───────────────────
def _run_bounded(store: Path, roots: list[str], day: _date) -> int:
    """3-tier one-day ensure for `roots` on `day` (legacy contract; §G).

    Returns the legacy exit-code triple: 0 = every root now has rows for the
    date (or already did); 2 = vendor has no data yet for ANY root; 1 = partial.
    """
    from collectors import thetadata as td

    if not td.reachable():
        log.error("topup: theta terminal unreachable — nothing pulled")
        return 2

    complete = 0
    empty = 0
    for root in roots:
        if all(_has_day(store, t, root, day) for t in TIERS):
            log.info("topup: %s %s already in store (all tiers) — skipping", root, day)
            complete += 1
            continue
        try:
            pulls = {
                "eod":    td.bulk_eod(root, 0, day, day),
                "oi":     td.bulk_open_interest(root, 0, day, day),
                "greeks": td.bulk_greeks(root, 0, day, day, order=3, **_dated_greek_request_options(root)),
            }
        except Exception as e:  # noqa: BLE001
            log.warning("topup: %s %s pull failed: %s", root, day, e)
            continue
        rows = {}
        got_all = True
        for tier in TIERS:
            df = pulls[tier]
            if df is None or df.empty:
                rows[tier] = 0
                got_all = False
                continue
            rows[tier] = _merge_day(store, tier, root, day, df)
            if rows[tier] == 0:
                got_all = False
        if sum(rows.values()) == 0:
            empty += 1
            log.info("topup: %s %s — vendor has no rows yet (eod/oi/greeks all empty)",
                     root, day)
        else:
            log.info("topup: %s %s merged rows eod=%d oi=%d greeks=%d",
                     root, day, rows["eod"], rows["oi"], rows["greeks"])
            if got_all:
                complete += 1

    log.info("topup: %s — %d/%d roots complete, %d vendor-empty",
             day, complete, len(roots), empty)
    if complete == len(roots):
        return 0
    if empty == len(roots):
        return 2
    return 1


# ── daily incremental mode (§A-§D) ───────────────────────────────────────────
@dataclass(frozen=True)
class RunContext:
    """Immutable daily-mode run context (F3) — S/D resolved EXACTLY ONCE,
    before the worker pool starts. No worker may consult the wall clock."""
    D: _date
    S: _date | None
    forced: bool


def _resolve_daily_context(now: datetime, *, forced: bool) -> RunContext | None:
    """(F4) Exact calendar/time derivation for the daily gate.

    `now` may be any aware datetime (naive is treated as UTC, matching this
    repo's other calendar helpers); it is converted to America/New_York here.
    `expected_last_session()` is FORBIDDEN on this path — its 17:00 ET settle
    buffer would return S when asked for D at the 16:15-window fire.

    Returns None for a lawful no-op (non-session day, or before 16:10 ET)
    unless `forced`. Returns a RunContext with `S=None` when the calendar
    cannot resolve the prior session (session_n_back failure) — the caller
    aborts that as a `failed` run.
    """
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now_et = now.astimezone(nyse_calendar.ET)
    today_et = now_et.date()

    gate_open = (nyse_calendar.is_session(today_et)
                and now_et.time() >= _GATE_TIME_ET)
    if not gate_open and not forced:
        return None

    D = today_et if nyse_calendar.is_session(today_et) \
        else nyse_calendar.last_session_on_or_before(today_et)
    S = nyse_calendar.session_n_back(D, 1)
    return RunContext(D=D, S=S, forced=forced)


@dataclass
class RootResult:
    root: str
    state: str
    cells: dict = field(default_factory=dict)
    failure_reason: str | None = None


def _ensure_one_cell(store: Path, tier: str, root: str, day: _date,
                     fetch_fn: Callable[[], pd.DataFrame | None]) -> str:
    """Ensure one (tier, root, day) cell (§A4). Returns the cell's terminal
    state: already_present | complete | vendor_empty | fetch_failed |
    date_unresolved."""
    if _has_day(store, tier, root, day):
        return "already_present"
    df = fetch_fn()
    if df is None:
        # (F5) the collector returns None indistinguishably for timeouts,
        # stream truncation, non-200s, and parse failures — fetch_failed is
        # a deliberate superset, not a cause classification.
        return "fetch_failed"
    if df.empty:
        return "vendor_empty"
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    day_ts = pd.Timestamp(day)
    rows_returned = len(d)
    rows_for_target_date = int((d["date"] == day_ts).sum())
    if rows_for_target_date == 0:
        # (F6) rows came back, but none carry the target date after
        # normalization — distinct from vendor_empty (an EMPTY frame).
        log.warning("topup daily: %s %s %s date_unresolved "
                   "(rows_returned=%d rows_for_target_date=0)",
                   root, tier, day, rows_returned)
        return "date_unresolved"
    _merge_day(store, tier, root, day, df)
    return "complete"


_SNAPSHOT_OI_COLUMNS = ["root", "expiration", "strike", "right", "date", "open_interest"]


_EOD_CATCHUP_ROOTS = ("GLD", "SLV", "TLT", "HYG")


def _eod_capture_scope(start, end, byte_cap, total_bytes, row_cap, total_rows):
    """A bounded repair scope, not provider permission or an automatic job."""
    if type(start) is not _date or type(end) is not _date:
        raise ValueError("EOD catch-up needs exact date objects")
    if not 0 <= (end - start).days <= 4 or start.year != end.year:
        raise ValueError("EOD catch-up supports at most5 days in one year")
    from zoneinfo import ZoneInfo
    if end >= datetime.now(timezone.utc).astimezone(ZoneInfo('America/New_York')).date():
        raise ValueError("EOD catch-up requires a completed historical date")
    for value, ceiling in ((byte_cap, 16*1024*1024), (total_bytes, 64*1024*1024),
                           (row_cap, 100000), (total_rows, 400000)):
        if type(value) is not int or not 0 < value <= ceiling:
            raise ValueError("EOD catch-up needs explicit positive byte/row bounds")
    days = [start + timedelta(days=i) for i in range((end-start).days+1)]
    if any(day.weekday() >= 5 for day in days):
        raise ValueError("EOD catch-up scope must name contiguous weekday sessions")
    return days


def _eod_sync_directory(path):
    import os
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _eod_retain(path, data):
    """Atomic bytes plus directory durability before their receipt is advanced."""
    import os
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    _eod_sync_directory(path.parent)


def _eod_sync_canonical(path, store):
    """Make canonical bytes and their directory entries durable before receipt."""
    import os
    with path.open('rb') as stream:
        os.fsync(stream.fileno())
    parent = path.parent
    while True:
        _eod_sync_directory(parent)
        if parent == store:
            break
        parent = parent.parent


def _validate_eod_capture_frame(frame, root, days):
    import numpy as np
    required = {'root', 'expiration', 'strike', 'right', 'date', 'close', 'volume'}
    if frame is None or frame.empty or not required <= set(frame):
        raise ValueError("Incomplete EOD capture schema/population")
    dates = pd.to_datetime(frame['date'], errors='coerce')
    if (not frame['root'].eq(root).all() or dates.isna().any() or dates.dt.tz is not None
            or set(dates.dt.date) != set(days)
            or not dates.eq(dates.dt.normalize()).all()
            or not frame['right'].isin(['C', 'P']).all()
            or pd.to_datetime(frame['expiration'], errors='coerce').isna().any()):
        raise ValueError("EOD response does not match exact root/session scope")
    for field in ('strike', 'close', 'volume'):
        values = pd.to_numeric(frame[field], errors='coerce')
        if not np.isfinite(values).all() or (values < 0).any() or (field == 'strike' and (values == 0).any()):
            raise ValueError("Invalid EOD source numbers")
    if frame.duplicated(['root', 'expiration', 'strike', 'right', 'date']).any():
        raise ValueError("Ambiguous EOD contract/day")


def capture_bounded_eod_catchup(store: Path, capture_dir: Path, *, start: _date, end: _date,
        original_root: str, assigning_parent: str, max_response_bytes: int,
        max_total_bytes: int, max_response_rows: int, max_total_rows: int) -> dict:
    """Retain one four-root EOD operation. No store data write, probe or retry.

    Callable only by a separately admitted operator; no CLI/scheduler invokes it.
    Identity labels record custody, never grant it. Existing claims are final:
    inspect their original state rather than replaying this function.
    """
    import hashlib
    import uuid
    from collectors import thetadata as td
    from lib.options_source_receipts import BoundedRequestBudget
    days = _eod_capture_scope(start, end, max_response_bytes, max_total_bytes,
                              max_response_rows, max_total_rows)
    for identity in (original_root, assigning_parent):
        if str(uuid.UUID(identity)) != identity:
            raise ValueError("Exact native custody identity required")
    if not store.is_dir() or not capture_dir.parent.is_dir():
        raise ValueError("Existing canonical store and capture parent required")
    record = dict(schema='options.bounded_eod_catchup/v1', original_root=original_root,
        assigning_parent=assigning_parent, roots=list(_EOD_CATCHUP_ROOTS),
        store_ref=str(store.resolve()),
        collector_sha256=hashlib.sha256(Path(td.__file__).read_bytes()).hexdigest(),
        start=start.isoformat(), end=end.isoformat(), state='PREPARED', max_gets=4,
        max_response_bytes=max_response_bytes, max_total_bytes=max_total_bytes,
        max_response_rows=max_response_rows, max_total_rows=max_total_rows,
        attempts=0, response_bytes=0, raw_rows=0, requests=[], store_writes=0,
        publication=False, started_at=datetime.now(timezone.utc).isoformat())
    def save():
        _eod_retain(capture_dir/'receipt.json', json.dumps(record, allow_nan=False, sort_keys=True).encode())
    with _writer_lock(store) as acquired:
        if not acquired:
            raise RuntimeError("Canonical store writer is occupied")
        if any(_tmp_path(store/'eod'/root/f'{start.year}.parquet').exists() for root in _EOD_CATCHUP_ROOTS):
            raise ValueError("Unreconciled canonical EOD temporary file")
        if any(_has_day(store, 'eod', root, day) for root in _EOD_CATCHUP_ROOTS for day in days):
            raise ValueError("Catch-up scope contains an already retained day")
        capture_dir.mkdir()  # exclusive operation claim; never exist_ok/replacement
        _eod_sync_directory(capture_dir.parent)
        save()
        class Budget(BoundedRequestBudget):
            def begin(self, session, url):
                super().begin(session, url)
                if url != td._base_url()+'/v3/option/history/eod':
                    raise ValueError("Unexpected EOD endpoint")
                record['attempts'] = self.attempts
                entry.update(state='REQUEST_STARTED', started_at=datetime.now(timezone.utc).isoformat())
                save()  # reserve actual attempt durably BEFORE requests.Session.get
        budget = Budget(4, profile='eod_catchup')
        try:
            for root in _EOD_CATCHUP_ROOTS:
                byte_bound = min(max_response_bytes, max_total_bytes-record['response_bytes'])
                row_bound = min(max_response_rows, max_total_rows-record['raw_rows'])
                if min(byte_bound, row_bound) <= 0:
                    raise ValueError("Aggregate EOD budget exhausted")
                params = dict(symbol=root, expiration='*', start_date=int(start.strftime('%Y%m%d')),
                              end_date=int(end.strftime('%Y%m%d')), format='csv')
                entry = dict(root=root, parameters=params, endpoint='/v3/option/history/eod',
                             origin=td._base_url(), state='RESERVED')
                record['requests'].append(entry)
                save()
                def response(status):
                    entry.update(http_status=status, state='RESPONSE_HEADERS' if status == 200 else 'REFUSED')
                    save()
                def retain(raw):
                    _eod_retain(capture_dir/(root+'.csv'), raw)
                    record['response_bytes'] += len(raw)
                    entry.update(state='RAW_CAPTURED', response_bytes=len(raw),
                        response_sha256=hashlib.sha256(raw).hexdigest(),
                        received_at=datetime.now(timezone.utc).isoformat())
                    save()
                frame = td.bulk_eod(root, 0, start, end, request_budget=budget,
                    max_bytes=byte_bound, max_rows=row_bound,
                    response_handler=response, raw_response_handler=retain)
                if frame is None or frame.empty:
                    raise ValueError("EOD acquisition returned no complete frame")
                raw_rows = frame.attrs.get('_bounded_raw_rows')
                if type(raw_rows) is not int or not 0 < raw_rows <= row_bound:
                    raise ValueError("Missing actual bounded source row count")
                record['raw_rows'] += raw_rows
                entry['raw_rows'] = raw_rows
                _validate_eod_capture_frame(frame, root, days)
                entry.update(state='CAPTURED', normalized_rows=len(frame))
                save()
            record['state'] = 'CAPTURED'
        except BaseException as exc:
            budget.stop()
            if record['requests'] and record['requests'][-1]['state'] in ('REQUEST_STARTED', 'RESPONSE_HEADERS'):
                record['requests'][-1]['state'] = 'EFFECT_UNKNOWN'
            record.update(state='EFFECT_UNKNOWN' if any(r['state']=='EFFECT_UNKNOWN' for r in record['requests'])
                          else 'STOPPED', error_type=type(exc).__name__)
            raise
        finally:
            record['completed_at'] = datetime.now(timezone.utc).isoformat()
            save()
    return record


def merge_bounded_eod_capture(store: Path, capture_dir: Path) -> dict:
    """Separate admitted store effect from a completed retained capture; no GET.

    A started/failed merge is never resumed automatically. Its receipt and the
    original canonical files must be reconciled by the admitted operator.
    """
    import hashlib
    import io
    from collectors import thetadata as td
    from lib.options_source_receipts import instant
    receipt = capture_dir/'receipt.json'
    if not store.is_dir() or capture_dir.is_symlink() or receipt.is_symlink() or receipt.stat().st_size > 65536:
        raise ValueError("Oversize EOD receipt")
    receipt_bytes = receipt.read_bytes()
    record = json.loads(receipt_bytes)
    if (record.get('schema') != 'options.bounded_eod_catchup/v1' or record.get('state') != 'CAPTURED'
            or record.get('roots') != list(_EOD_CATCHUP_ROOTS) or record.get('attempts') != 4
            or record.get('store_ref') != str(store.resolve())
            or record.get('collector_sha256') != hashlib.sha256(Path(td.__file__).read_bytes()).hexdigest()
            or record.get('store_writes') != 0 or len(record.get('requests', [])) != 4):
        raise ValueError("No complete, unmerged EOD capture")
    start, end = _date.fromisoformat(record['start']), _date.fromisoformat(record['end'])
    days = _eod_capture_scope(start, end, record['max_response_bytes'], record['max_total_bytes'],
                              record['max_response_rows'], record['max_total_rows'])
    frames = {}
    total_bytes = total_rows = 0
    started, completed = instant(record.get('started_at')), instant(record.get('completed_at'))
    if not started <= completed <= datetime.now(timezone.utc):
        raise ValueError("Invalid EOD operation clocks")
    for root, entry in zip(_EOD_CATCHUP_ROOTS, record['requests']):
        params = dict(symbol=root, expiration='*', start_date=int(start.strftime('%Y%m%d')),
                      end_date=int(end.strftime('%Y%m%d')), format='csv')
        raw_path = capture_dir/(root+'.csv')
        if raw_path.is_symlink() or raw_path.stat().st_size > record['max_response_bytes']:
            raise ValueError("EOD raw byte bound")
        raw = raw_path.read_bytes()
        if (entry.get('root') != root or entry.get('state') != 'CAPTURED'
                or entry.get('endpoint') != '/v3/option/history/eod' or entry.get('parameters') != params
                or entry.get('origin') != td._base_url()
                or not started <= instant(entry.get('started_at')) <= instant(entry.get('received_at')) <= completed
                or entry.get('http_status') != 200 or entry.get('response_bytes') != len(raw)
                or entry.get('response_sha256') != hashlib.sha256(raw).hexdigest()):
            raise ValueError("EOD retained response binding mismatch")
        frame = pd.read_csv(io.BytesIO(raw), keep_default_na=False, na_values=[''])
        if not 0 < len(frame) <= record['max_response_rows'] or len(frame) != entry['raw_rows']:
            raise ValueError("EOD retained row bound")
        total_bytes += len(raw)
        total_rows += len(frame)
        td._validate_bounded_eod_source(frame, start, end)
        frames[root] = td._normalize_eod_df(frame, root)
        _validate_eod_capture_frame(frames[root], root, days)
    if (total_bytes != record['response_bytes'] or total_rows != record['raw_rows']
            or total_bytes > record['max_total_bytes'] or total_rows > record['max_total_rows']):
        raise ValueError("EOD aggregate binding mismatch")
    def save():
        _eod_retain(receipt, json.dumps(record, allow_nan=False, sort_keys=True).encode())
    with _writer_lock(store) as acquired:
        if not acquired:
            raise RuntimeError("Canonical store writer is occupied")
        # A competing caller may have started an uncertain merge while these
        # frames were validated. Zero written days does not make that retryable.
        if receipt.is_symlink() or receipt.read_bytes() != receipt_bytes:
            raise ValueError("EOD receipt changed before writer lock")
        if any(_tmp_path(store/'eod'/root/f'{start.year}.parquet').exists() for root in frames):
            raise ValueError("Unreconciled canonical EOD temporary file")
        if any(_has_day(store, 'eod', root, day) for root in frames for day in days):
            raise ValueError("Canonical EOD scope changed after capture")
        record['state'] = 'MERGE_STARTED'
        save()
        # Any interrupted merge keeps MERGE_STARTED, never a retryable CAPTURED.
        for root, frame in frames.items():
            for day in days:
                written = _merge_day(store, 'eod', root, day, frame)
                if written != int(frame['date'].eq(pd.Timestamp(day)).sum()):
                    raise RuntimeError("Canonical EOD merge count differs from retained capture")
                _eod_sync_canonical(store/'eod'/root/f'{day.year}.parquet', store)
                record['store_writes'] += 1
                save()
        record['state'] = 'MERGED'
        save()
    return record


# Source preparation only: CLI, wrapper and environment do not enable this seam.
# The incumbent collector owner must supply/qualify a two-attempt transport that
# budgets EVERY physical request (including probes/retries/redirects), retains raw
# bytes before parsing and honors the shared deadline. Current transport is None.
@dataclass(frozen=True)
class _DSessionObservation:
    retention_parent: Path
    original_root: str
    assigning_parent: str
    transport: Callable | None = None
    session_day: _date | None = None  # one prospective operation, never a daily allowance
    capacity_preflight: Callable | None = None  # configured native lane only; no GET


def _d_session_coverage(eod, greeks, oi_d, oi_s, *, D, S, requested_version):
    """Complete observed membership only; never a market/model/PIT certificate."""
    import numpy as np
    frames = {'eod_D': eod, 'greeks_D': greeks, 'oi_D': oi_d, 'oi_S': oi_s}
    counts = {name: len(frame) if isinstance(frame, pd.DataFrame) else 0
              for name, frame in frames.items()}
    result = dict(ready=False, reason='missing_input', counts=counts,
                  D=D.isoformat(), S=S.isoformat(), observed_contracts=None,
                  population='reported_live_contracts_expiry_gte_D', excluded_before_D={})
    if requested_version != '1':
        return dict(result, reason='greek_version_unestablished')
    populations = []
    common = {'root', 'expiration', 'strike', 'right', 'date'}
    for name, frame in frames.items():
        required = common | ({'close', 'volume'} if name == 'eod_D' else
                    {'gamma', 'underlying_price'} if name == 'greeks_D' else {'open_interest'})
        if not isinstance(frame, pd.DataFrame) or frame.empty or not required <= set(frame):
            return result
        day = S if name == 'oi_S' else D
        dates = pd.to_datetime(frame['date'], errors='coerce')
        expiry = pd.to_datetime(frame['expiration'], errors='coerce')
        if (dates.isna().any() or dates.dt.tz is not None
                or not dates.eq(pd.Timestamp(day)).all() or expiry.isna().any()
                or expiry.dt.tz is not None or (expiry < pd.Timestamp(day)).any()
                or not expiry.eq(expiry.dt.normalize()).all()
                or not frame['root'].eq('SPY').all() or not frame['right'].isin(['C', 'P']).all()):
            return dict(result, reason='source_scope_or_date_mismatch')
        numeric = {'strike'} | (required - common)
        values = {}
        for col in numeric:
            value = pd.to_numeric(frame[col], errors='coerce')
            if (not np.isfinite(value).all()
                    or (col in {'strike', 'close', 'underlying_price'} and (value <= 0).any())
                    or (col in {'volume', 'open_interest'} and (value < 0).any())):
                return dict(result, reason='invalid_source_numbers')
            values[col] = value
        keys = list(zip(expiry, values['strike'], frame['right']))
        if len(set(keys)) != len(keys):
            return dict(result, reason='ambiguous_membership')
        live_keys = {key for key in keys if key[0] >= pd.Timestamp(D)}
        result['excluded_before_D'][name] = len(keys)-len(live_keys)
        populations.append(live_keys)
    union = set.union(*populations)
    result['observed_contracts'] = len(union)
    result['missing_by_input'] = {name: len(union-population)
        for name, population in zip(frames, populations)}
    result['matched_contracts'] = len(set.intersection(*populations))
    result['market_universe_complete'] = None
    if not union:
        return dict(result, reason='empty_live_observed_population')
    if any(population != union for population in populations):
        return dict(result, reason='incomplete_observed_membership')
    return dict(result, ready=True, reason='complete_observed_inputs')


def _d_session_local_oi(store, D, S):
    """Read exact retained reports under the caller's canonical writer lock."""
    import hashlib
    import numpy as np
    import pyarrow.parquet as pq
    required = {'root', 'expiration', 'strike', 'right', 'date', 'open_interest'}
    parts, references = [], []
    for year in sorted({D.year, S.year}):
        path = store / 'oi' / 'SPY' / f'{year}.parquet'
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 256*1024*1024:
            raise ValueError('local_oi_unavailable')
        parquet = pq.ParquetFile(path)
        columns = parquet.schema.names
        if len(columns) > 64 or not required <= set(columns):
            raise ValueError('local_oi_schema')
        indices = [parquet.schema.names.index(col) for col in columns]
        decoded = sum(parquet.metadata.row_group(i).column(j).total_uncompressed_size
                      for i in range(parquet.metadata.num_row_groups) for j in indices)
        if decoded > 256*1024*1024:
            raise ValueError('local_oi_decoded_bound')
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024*1024), b''):
                digest.update(chunk)
        frame = pd.read_parquet(path, columns=columns, filters=[
            [('date', '>=', pd.Timestamp(day)),
             ('date', '<', pd.Timestamp(day)+pd.Timedelta(days=1))] for day in [S, D]])
        if len(frame) > 200000:
            raise ValueError('local_oi_row_bound')
        parts.append(frame)
        references.append(dict(path=str(path), sha256=digest.hexdigest(),
            bytes=path.stat().st_size, read_at=datetime.now(timezone.utc).isoformat(),
            first_availability=None))
    frame = pd.concat(parts, ignore_index=True)
    dates = pd.to_datetime(frame['date'], errors='coerce')
    if (dates.isna().any() or dates.dt.tz is not None
            or not dates.isin([pd.Timestamp(D), pd.Timestamp(S)]).all()):
        raise ValueError('invalid_local_oi_report_dates')
    reports = [frame[dates.eq(pd.Timestamp(day))].copy() for day in [D, S]]
    if any(f.empty or len(f) > 100000 for f in reports):
        raise ValueError('missing_local_oi_or_baseline')
    live_populations = []
    for report, day in zip(reports, [D, S]):
        strike = pd.to_numeric(report['strike'], errors='coerce')
        interest = pd.to_numeric(report['open_interest'], errors='coerce')
        expiry = pd.to_datetime(report['expiration'], errors='coerce')
        if (not report['root'].eq('SPY').all() or not report['right'].isin(['C', 'P']).all()
                or expiry.isna().any() or expiry.dt.tz is not None
                or not expiry.eq(expiry.dt.normalize()).all() or (expiry < pd.Timestamp(day)).any()
                or not np.isfinite(strike).all() or (strike <= 0).any()
                or not np.isfinite(interest).all() or (interest < 0).any()
                or report.duplicated(['expiration', 'strike', 'right', 'date']).any()):
            raise ValueError('ambiguous_or_invalid_local_oi')
        live_populations.append({key for key in zip(expiry, strike, report['right'])
                                 if key[0] >= pd.Timestamp(D)})
    if not live_populations[0] or live_populations[0] != live_populations[1]:
        raise ValueError('incompatible_live_local_oi_baseline')
    return *reports, references


def _observe_spy_d_session(store, ctx, entered_at, deadline_at, config, *, request_options):
    """Inert until an incumbent bounded transport is supplied after qualification.

    The ordinary CLI binds only the exact separately approved Oct26 operation
    when its explicit configuration is present; absent configuration stays None.
    Its budget must wrap actual transport, not merely count bulk API calls.
    Pilot payloads never enter _ensure_one_cell/_merge_day/canonical parquet.
    """
    import hashlib
    import uuid
    from lib.options_source_receipts import BoundedRequestBudget
    outcome = dict(state='WITHHELD', reason='not_selected_natural_rung', attempts=0,
        root='SPY', D=ctx.D.isoformat(), S=ctx.S.isoformat(), canonical_writes=0,
        hub_promotion=False, instantaneous=False, historical_pit=False)
    entered_et = entered_at.astimezone(nyse_calendar.ET)
    if (ctx.forced or not nyse_calendar.is_session(ctx.D)
            or ctx.S != nyse_calendar.session_n_back(ctx.D, 1)
            or entered_et.date() != ctx.D
            or entered_et.time().replace(second=0, microsecond=0) != _time_of_day(17, 30)):
        return outcome
    if type(config.session_day) is not _date or config.session_day != ctx.D:
        return dict(outcome, reason='observation_session_not_bound')
    if request_options != {'version': '1'}:
        return dict(outcome, reason='greek_request_policy_unestablished')
    if _time.monotonic() >= deadline_at:
        return dict(outcome, reason='shared_deadline_exhausted')
    try:
        oi_d, oi_s, local_refs = _d_session_local_oi(store, ctx.D, ctx.S)
    except Exception as exc:
        return dict(outcome, reason='local_oi_or_baseline_unavailable', error_type=type(exc).__name__)
    if config.transport is None:
        return dict(outcome, reason='bounded_transport_not_bound', local_inputs=local_refs)
    for identity in [config.original_root, config.assigning_parent]:
        if str(uuid.UUID(identity)) != identity:
            raise ValueError('Exact source custody identities required')
    if config.capacity_preflight is not None:
        try:
            capable = config.capacity_preflight(deadline_at=deadline_at)
        except Exception:
            capable = False
        if capable is not True:
            return dict(outcome, reason='native_transport_capacity_unavailable')
    parent = config.retention_parent
    if (not parent.is_dir() or parent.is_symlink()
            or parent.resolve().is_relative_to(store.resolve())):
        return dict(outcome, reason='private_retention_parent_unqualified')
    directory = parent / f'spy-{ctx.D.isoformat()}-1730-observation-v1'
    try:
        directory.mkdir()  # exclusive, never reuse a refused/unknown/complete claim
    except FileExistsError:
        return dict(outcome, reason='existing_observation_claim')
    _eod_sync_directory(parent)
    record = dict(outcome, schema='options.d_session_observation/v1', state='PREPARED',
        operation_ref=directory.name, bound_session=config.session_day.isoformat(),
        reason=None, original_root=config.original_root, assigning_parent=config.assigning_parent,
        entered_at=entered_at.isoformat(), started_at=datetime.now(timezone.utc).isoformat(),
        first_availability=None, market_universe_complete=None, model_scope=None,
        requested_greek_version='1',
        local_inputs=local_refs, max_gets=2, requests=[], economic_expiry=None,
        model_details=None, topup_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    def save():
        _eod_retain(directory/'receipt.json', json.dumps(record, allow_nan=False, sort_keys=True).encode())
    save()
    # Full normalized local reports, before the declared expiry exclusion, stay
    # in this private observation evidence. These are not original vendor CSVs.
    record['local_report_copies'] = []
    for name, report in [('oi_D', oi_d), ('oi_S', oi_s)]:
        body = report.to_csv(index=False).encode()
        if len(body) > 32*1024*1024:
            raise ValueError('Private local-report copy byte bound')
        _eod_retain(directory/(name+'.csv'), body)
        expiry = pd.to_datetime(report['expiration'])
        record['local_report_copies'].append(dict(name=name, rows=len(report),
            bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
            excluded_expiry_before_D=int((expiry < pd.Timestamp(ctx.D)).sum()),
            representation='normalized_local_report_before_live_population_exclusion'))
    save()
    class Budget(BoundedRequestBudget):
        def begin(self, session, url):
            if entry['state'] != 'RESERVED' or url != entry['origin'] + entry['endpoint']:
                if entry['state'] == 'RESERVED':
                    entry.update(state='NOT_ATTEMPTED', reason='request_scope_refused')
                save()
                raise RuntimeError('Pilot retries/redirects/probes are not admitted')
            if _time.monotonic() >= deadline_at:
                entry.update(state='NOT_ATTEMPTED', reason='shared_deadline_exhausted')
                save()
                raise RuntimeError('Shared deadline exhausted before request')
            try:
                super().begin(session, url)
            except Exception:
                entry.update(state='NOT_ATTEMPTED', reason='request_budget_refused')
                save()
                raise
            record['attempts'] = self.attempts
            entry.update(state='REQUEST_STARTED', started_at=datetime.now(timezone.utc).isoformat())
            save()  # durability BEFORE the adapter may perform a physical GET
    budget = Budget(2)
    frames = {}
    try:
        for kind, endpoint in [('eod', '/v3/option/history/eod'), ('greeks', '/v3/option/history/greeks/eod')]:
            if budget.stopped or _time.monotonic() >= deadline_at:
                raise RuntimeError('Pilot stopped/shared deadline exhausted')
            entry = dict(kind=kind, state='RESERVED', origin=config.transport.origin,
                endpoint=endpoint, parameters=dict(symbol='SPY', expiration='*',
                start_date=int(ctx.D.strftime('%Y%m%d')), end_date=int(ctx.D.strftime('%Y%m%d')),
                format='csv', **({'version': '1', 'right': 'both'} if kind == 'greeks' else {})),
                requested_order=3 if kind == 'greeks' else None, raw_rows=None, normalized_rows=None)
            record['requests'].append(entry)
            save()
            def response(status):
                if entry['state'] != 'REQUEST_STARTED':
                    raise RuntimeError('Unreserved response')
                entry.update(state='HEADERS' if status == 200 else 'REFUSED', http_status=status,
                             response_at=datetime.now(timezone.utc).isoformat())
                save()
                if status != 200:
                    budget.stop()
                    raise ValueError('Pilot source refusal')
            def raw(body):
                if entry['state'] != 'HEADERS' or not isinstance(body, bytes) or len(body) > 16*1024*1024:
                    raise ValueError('Pilot raw-response contract/bound')
                _eod_retain(directory/(kind+'.csv'), body)
                entry.update(state='RAW_CAPTURED', bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
                             received_at=datetime.now(timezone.utc).isoformat())
                save()
                if not body.strip():
                    raise ValueError('Empty observed source response')
            entry['adapter_entered_at'] = datetime.now(timezone.utc).isoformat()
            save()
            frame = config.transport(kind, root='SPY', day=ctx.D, order=3 if kind=='greeks' else None,
                request_options={'version':'1'} if kind=='greeks' else {}, request_budget=budget,
                max_bytes=16*1024*1024, max_rows=100000, deadline_at=deadline_at,
                response_handler=response, raw_response_handler=raw)
            if entry['state'] != 'RAW_CAPTURED' or entry.get('http_status') != 200:
                raise ValueError('Missing actual acquisition receipt')
            if not isinstance(frame, pd.DataFrame) or frame.empty or len(frame) > 100000:
                raise ValueError('Missing/malformed/oversized pilot frame')
            raw_rows = frame.attrs.get('_bounded_raw_rows')
            if type(raw_rows) is not int or not 0 < raw_rows <= 100000:
                raise ValueError('Missing/out-of-bound actual raw row count')
            expected_binding = dict(origin=entry['origin'], endpoint=entry['endpoint'],
                parameters=entry['parameters'], raw_rows=raw_rows,
                payload_sha256=entry['sha256'], payload_bytes=entry['bytes'])
            if frame.attrs.get('_d_session_binding') != expected_binding:
                raise ValueError('Unbound/mismatched actual request and raw-to-parser evidence')
            if kind=='greeks':
                request_provenance = frame.attrs.get('requested_version')
                entry['frame_request_version_provenance'] = request_provenance
                entry['response_model_metadata'] = None
                if request_provenance is not None and request_provenance != '1':
                    raise ValueError('Conflicting Greek request-version provenance')
            entry.update(state='PARSED', parsed_at=datetime.now(timezone.utc).isoformat(),
                         raw_rows=raw_rows, normalized_rows=len(frame))
            returned_dates = pd.to_datetime(frame['date'], errors='coerce') if 'date' in frame else None
            entry['returned_frame_dates'] = None
            if returned_dates is not None and not returned_dates.isna().any():
                unique_dates = list(pd.unique(returned_dates))
                if len(unique_dates) <= 8:
                    entry['returned_frame_dates'] = sorted(pd.Timestamp(value).isoformat() for value in unique_dates)
            frames[kind] = frame
            save()
        if _time.monotonic() >= deadline_at:
            raise RuntimeError('Shared deadline exhausted during observation')
        coverage = _d_session_coverage(frames['eod'], frames['greeks'], oi_d, oi_s,
            D=ctx.D, S=ctx.S, requested_version='1')
        record.update(state='OBSERVED_COMPLETE' if coverage['ready'] else 'WITHHELD',
                      reason=coverage['reason'], coverage=coverage)
    except BaseException as exc:
        budget.stop()
        if (record['requests'] and record['requests'][-1]['state'] == 'RESERVED'
                and getattr(exc, 'request_started', None) is False):
            record['requests'][-1].update(state='NOT_ATTEMPTED', reason='source_pre_get_refusal')
        if record['requests'] and (record['requests'][-1]['state'] in ('REQUEST_STARTED', 'HEADERS')
                or (record['requests'][-1]['state'] == 'RESERVED'
                    and 'adapter_entered_at' in record['requests'][-1])):
            record['requests'][-1]['state'] = 'EFFECT_UNKNOWN'
        record.update(state='EFFECT_UNKNOWN' if any(r['state']=='EFFECT_UNKNOWN' for r in record['requests'])
                      else 'STOPPED', reason=type(exc).__name__)
        if not isinstance(exc, Exception):
            raise
    finally:
        record['completed_at'] = datetime.now(timezone.utc).isoformat()
        save()
    return dict(outcome, state=record['state'], reason=record['reason'], attempts=record['attempts'],
                receipt=str(directory/'receipt.json'), coverage=record.get('coverage'))


def _snapshot_oi_frame(td, root: str) -> pd.DataFrame | None:
    """(K2, Sol B1b) OI[D] frontier via `collectors.thetadata.snapshot_open_interest`
    — replaces the current-day-unavailable `bulk_open_interest(root, 0, D, D)`
    history call for `--daily` mode ONLY (`collectors/thetadata.py` itself is
    NOT modified).

    Fetch -> guard -> normalize; the result flows through the UNCHANGED
    `_ensure_one_cell` classification:
      - `None` (vendor unreachable/parse failure) -> stays `None` ->
        `fetch_failed`.
      - Empty frame -> stays empty -> `vendor_empty`.
      - Else: derive `date = snapshot_ts.dt.normalize()` — the SAME vendor
        `timestamp` clock `_normalize_oi_df` already uses for the store's
        history-path `date` column — drop `snapshot_ts`, and select exactly
        the store's OI schema (`root, expiration, strike, right, date,
        open_interest`).

    This wrapper does NOT itself filter rows by `date == D` (post-
    adjudication it never date-filters at all, hence no `D` parameter): doing
    so here would collapse a "vendor returned rows, but none for D" (stale
    snapshot, e.g. a midnight-crossing cache reset) into an indistinguishable-
    from-truly-empty frame, losing `_ensure_one_cell`'s existing
    `date_unresolved` classification (rows_returned>0, rows_for_target_date
    ==0). Instead every row's OWN derived date rides through unchanged, and
    the EXISTING machinery does the scoping: `_ensure_one_cell` classifies
    `date_unresolved` when zero rows carry `D`, and `_merge_day`'s existing
    exact-date replacement writer keeps ONLY the `D`-dated rows when it
    writes (`fresh["date"] == day_ts`) — so a stale/other-date row is still
    NEVER written under `D` (the source-timestamp guard: stale rows are
    absent from the store, never relabeled), it is only the classification
    boundary that reads the un-pre-filtered frame.

    (K6 NOTE-3) A vendor frame lacking `open_interest` after normalization
    (malformed response) returns `None` -> `fetch_failed` rather than ever
    classifying `complete` without the OI column — stricter than the history
    path's permissive column selection, deliberate for this new endpoint.

    (K6 MAJOR-2) `.drop_duplicates()` runs AFTER the final column selection
    — same ordering law as the collectors' `_normalize_oi_df`: dedup must
    cover exactly the columns actually written. `snapshot_ts` differs
    per-contract even when every OTHER column is identical, so deduping
    before dropping it would never collapse anything; deduping after it is
    dropped is what prevents `_merge_day` from writing duplicate rows and
    double-counting OI in the health-certifying cell.
    """
    df = td.snapshot_open_interest(root)
    if df is None:
        return None
    if df.empty:
        return df
    out = df.copy()
    out["date"] = pd.to_datetime(out["snapshot_ts"], errors="coerce").dt.normalize()
    out = out.drop(columns=["snapshot_ts"])
    if "open_interest" not in out.columns:
        log.warning("topup daily: %s snapshot_open_interest response missing "
                   "'open_interest' column after normalization — treating as "
                   "fetch_failed", root)
        return None
    available = [c for c in _SNAPSHOT_OI_COLUMNS if c in out.columns]
    return out[available].drop_duplicates().reset_index(drop=True)


def _ensure_daily_root(store: Path, root: str, S: _date, D: _date, td) -> RootResult:
    """Per-root ensure of the four §A4 cells, in the §A5 sequential order
    (eod[S] -> oi[S] -> oi[D] -> greeks[S]). (F11) ANY exception from vendor,
    parse, or parquet read/write is mapped to a root-level `failed` state —
    no exception may escape a worker into the pool."""
    cells: dict[str, str] = {}
    try:
        cells["eod_S"] = _ensure_one_cell(
            store, "eod", root, S, lambda: td.bulk_eod(root, 0, S, S))
        cells["oi_S"] = _ensure_one_cell(
            store, "oi", root, S, lambda: td.bulk_open_interest(root, 0, S, S))
        cells["oi_D"] = _ensure_one_cell(
            store, "oi", root, D, lambda: _snapshot_oi_frame(td, root))
        cells["greeks_S"] = _ensure_one_cell(
            store, "greeks", root, S, lambda: td.bulk_greeks(root, 0, S, S, order=3, **_dated_greek_request_options(root)))
    except Exception as e:  # noqa: BLE001 — F11 catch-all
        return RootResult(root=root, state="failed", cells=cells,
                          failure_reason=type(e).__name__)
    return RootResult(root=root, state=_classify_root_state(cells), cells=cells)


def _classify_root_state(cells: dict[str, str]) -> str:
    """Aggregate a root's four §A4 cell states into ONE per-root terminal
    state (Fable ruling, 2026-08-22 — restates the ladder against three
    binding constraints):

      1. `complete`       ONLY if all four cells are present (already_present
                          or complete) AFTER this run.
      2. `already_present` ONLY if all four cells were ALREADY present before
                          this run touched the vendor (zero vendor calls for
                          this root).
      3. ANY cell-level problem (fetch_failed / date_unresolved on a needed
         cell, or the whole root vendor_empty) means the root is NOT
         `complete` — full stop, no matter how many other cells landed.

    The aggregate is the WORST outstanding cell, worst-first:

        fetch_failed > date_unresolved > vendor_empty (ALL four) > partial
        > already_present > complete

    `partial` is the residual bucket: "some cells landed, some did not" —
    e.g. 3 cells complete + 1 vendor_empty is `partial`, NEVER `complete`.
    A root with 3 complete cells + 1 fetch_failed is `fetch_failed` (worse
    than partial) — also never `complete`. Only a uniform vendor_empty
    across ALL four cells earns the dedicated `vendor_empty` label (the
    "root has no options at all" shape); a partial vendor_empty mix falls
    through to `partial` like any other incomplete mix.
    """
    values = list(cells.values())
    if any(v == "fetch_failed" for v in values):
        return "fetch_failed"
    if any(v == "date_unresolved" for v in values):
        return "date_unresolved"
    if all(v == "vendor_empty" for v in values):
        return "vendor_empty"
    if all(v in _PRESENT_STATES for v in values):
        # All four present. already_present ONLY when EVERY cell was
        # already_present (zero vendor calls); any cell that had to be
        # fetched (state == "complete") demotes the whole root to "complete".
        if all(v == "already_present" for v in values):
            return "already_present"
        return "complete"
    return "partial"


def _panel_present(cells: dict, key: str) -> bool:
    return cells.get(key) in _PRESENT_STATES


def _s_panel_ok(r: RootResult) -> bool:
    return (_panel_present(r.cells, "eod_S") and _panel_present(r.cells, "oi_S")
            and _panel_present(r.cells, "greeks_S"))


def _ad_ready_ok(r: RootResult) -> bool:
    """(K1, Sol B1a) AD-ready = all FOUR §A4 cells present (the S-panel PLUS
    OI[D]) — the settlement print (`chain_next`) certifies an S/D panel, not
    the S-panel alone."""
    return _s_panel_ok(r) and _panel_present(r.cells, "oi_D")


def _run_daily_pool(store: Path, t1_universe: list[str], td, *,
                    workers: int, deadline_min: float, ctx: RunContext,
                    ) -> tuple[dict[str, RootResult], bool, bool]:
    """Dispatch the worker pool over `t1_universe` (§A5, §F2, §F5).

    Returns (results, deadline_exceeded, terminal_lost_mid_run). Stops
    DISPATCHING new roots once the deadline elapses (roots already in flight
    are drained, never abandoned) and, once fetch_failed exceeds 25% of
    processed roots, re-probes `td.reachable()` exactly once — a False
    re-probe aborts the run without dispatching further work (F5).
    """
    deadline_at = _time.monotonic() + max(0.0, deadline_min) * 60
    results: dict[str, RootResult] = {}
    deadline_exceeded = False
    terminal_lost_mid_run = False
    reprobed = False
    workers = max(1, workers)
    roots_iter = iter(t1_universe)
    in_flight: dict = {}

    def _record(fut, root) -> None:
        try:
            results[root] = fut.result()
        except Exception as e:  # noqa: BLE001 — belt-and-suspenders; workers
            # already catch everything internally (F11).
            results[root] = RootResult(root=root, state="failed",
                                       failure_reason=type(e).__name__)

    executor = ThreadPoolExecutor(max_workers=workers)
    try:
        for _ in range(workers):
            try:
                r = next(roots_iter)
            except StopIteration:
                break
            in_flight[executor.submit(_ensure_daily_root, store, r, ctx.S, ctx.D, td)] = r

        while in_flight and not terminal_lost_mid_run:
            done, _pending = wait(list(in_flight.keys()), timeout=1.0,
                                  return_when=FIRST_COMPLETED)
            if not done:
                if _time.monotonic() >= deadline_at:
                    deadline_exceeded = True
                    break
                continue
            for f in done:
                r = in_flight.pop(f)
                _record(f, r)

            fetch_failed_n = sum(1 for res in results.values()
                                 if res.state == "fetch_failed")
            if (not reprobed and results
                    and fetch_failed_n / len(results) > _REPROBE_FETCH_FAILED_FRACTION):
                reprobed = True
                if not td.reachable():
                    terminal_lost_mid_run = True
                    break

            if _time.monotonic() >= deadline_at:
                deadline_exceeded = True
                break

            while len(in_flight) < workers:
                try:
                    r = next(roots_iter)
                except StopIteration:
                    break
                in_flight[executor.submit(_ensure_daily_root, store, r, ctx.S, ctx.D, td)] = r
    finally:
        if in_flight:
            if terminal_lost_mid_run:
                # (RF12, R3) A future may have already finished in the gap
                # between the reprobe decision and this loop — gather ANY
                # already-completed result before cancelling the rest.
                # `cancel()` on an already-running/finished future is a
                # harmless no-op; discarding a landed result would make
                # completed work vanish from the receipt's counts.
                for f in list(in_flight):
                    if f.done():
                        _record(f, in_flight[f])
                    else:
                        f.cancel()
            else:
                for f in as_completed(list(in_flight)):
                    _record(f, in_flight[f])
        executor.shutdown(wait=True)

    if len(results) < len(t1_universe) and not terminal_lost_mid_run:
        deadline_exceeded = True
    return results, deadline_exceeded, terminal_lost_mid_run


def _source_coverage_gate() -> float:
    """Import, never a second literal (§D)."""
    from engine.options_intel_brief import CONFIG
    return CONFIG["SOURCE_COVERAGE_GATE"]


def _daily_universe() -> list[str]:
    from scripts.backfill_thetadata_eod import _resolve_universe
    return _resolve_universe()


def _ad_universe() -> list[str]:
    from engine.options_universe import gex_symbols
    return [s.upper() for s in gex_symbols()]


def _aggregate_daily(results: dict[str, RootResult], t1_universe: list[str],
                     ad_universe: list[str]) -> dict:
    ad_set = set(ad_universe)

    eod_S = sum(1 for r in results.values() if _panel_present(r.cells, "eod_S"))
    greeks_S = sum(1 for r in results.values() if _panel_present(r.cells, "greeks_S"))
    oi_S = sum(1 for r in results.values() if _panel_present(r.cells, "oi_S"))
    oi_D = sum(1 for r in results.values() if _panel_present(r.cells, "oi_D"))

    complete_t1_roots = sum(1 for r in results.values() if _s_panel_ok(r))
    # (K1, Sol B1a) Renamed from `complete_ad_roots` — observational S-panel
    # count within the AD universe. Computation UNCHANGED (EOD[S] ∧
    # Greeks[S] ∧ OI[S]); it is reported but no longer certifies `healthy`.
    s_panel_ad_roots = sum(1 for root, r in results.items()
                           if root in ad_set and _s_panel_ok(r))
    chain_next_ad_roots = sum(1 for root, r in results.items()
                              if root in ad_set and _panel_present(r.cells, "oi_D"))
    # (K1, Sol B1a) NEW — AD-ready roots: all FOUR §A4 cells present
    # (S-panel PLUS OI[D]). This is the gate `healthy` now certifies.
    ad_ready_roots = sum(1 for root, r in results.items()
                        if root in ad_set and _ad_ready_ok(r))

    ad_universe_count = len(ad_universe)
    s_panel_coverage_pct = (s_panel_ad_roots / ad_universe_count) if ad_universe_count else 0.0
    ad_ready_coverage_pct = (ad_ready_roots / ad_universe_count) if ad_universe_count else 0.0

    failure_counts: dict[str, int] = {}
    failure_examples: list[dict] = []
    for root, r in results.items():
        reason = r.failure_reason
        if reason is None and r.state in ("fetch_failed", "date_unresolved", "failed"):
            reason = r.state
        if reason:
            failure_counts[reason] = failure_counts.get(reason, 0) + 1
            if len(failure_examples) < 10:
                failure_examples.append({"root": root, "reason": reason})

    # (RF8, R3) Denominator = roots with an ACTUAL EOD[S] vendor attempt this
    # run — "already_present" roots never touched the vendor and must not
    # dilute the ratio (a steady-state ladder re-fire where most roots are
    # already_present would otherwise make a real closure invisible: e.g. 2
    # already_present + 2 fresh vendor_empty used to read as 2/4=50% — not
    # over the >50% bar — instead of the true 2/2=100% among roots actually
    # asked). A cell that never even reached "eod_S" (root failed earlier)
    # is likewise not an attempt. Zero attempts => flag False (never divide
    # by zero, never guess).
    #
    # (N1, R3 verify-pass) RF8's fix over-corrected the OTHER direction: a
    # TINY attempted set makes the ratio noisy the opposite way — falsified
    # live: 19 already_present roots + 1 genuinely option-less root gives
    # eod_s_attempted=1, eod_s_vendor_empty=1, ratio=1.0 (100%), a spurious
    # flag from a SINGLE root. A minimum-attempt floor guards both directions
    # at once: below the floor, the sample is too small to say anything about
    # "is today a session" and the flag is False regardless of the ratio.
    eod_s_attempted = sum(1 for r in results.values()
                         if r.cells.get("eod_S") not in (None, "already_present"))
    eod_s_vendor_empty = sum(1 for r in results.values()
                             if r.cells.get("eod_S") == "vendor_empty")
    min_attempts_floor = max(5, math.ceil(_S_SUSPECT_MIN_ATTEMPT_FRACTION * len(t1_universe)))
    s_suspect_non_session = (eod_s_attempted >= min_attempts_floor
                             and (eod_s_vendor_empty / eod_s_attempted
                                  > _S_SUSPECT_VENDOR_EMPTY_FRACTION))

    # (K6 NOTE-1) Stamp the auditable observation path only when at least one
    # root's oi_D cell had an actual VENDOR ATTEMPT this run — a cell state
    # not in {absent (never reached / missing from `cells`), already_present}
    # — so a run where every oi_D cell was already satisfied (no vendor call
    # made) is not falsely attributed to the snapshot endpoint.
    oi_d_vendor_attempted = any(
        r.cells.get("oi_D") not in (None, "already_present")
        for r in results.values())
    oi_D_source = "snapshot_open_interest" if oi_d_vendor_attempted else None

    return {
        "t1_universe_count": len(t1_universe),
        "ad_universe_count": ad_universe_count,
        "eod_S_roots": eod_S,
        "greeks_S_roots": greeks_S,
        "oi_S_roots": oi_S,
        "oi_D_roots": oi_D,
        "complete_t1_roots": complete_t1_roots,
        "s_panel_ad_roots": s_panel_ad_roots,
        "s_panel_coverage_pct": s_panel_coverage_pct,
        "ad_ready_roots": ad_ready_roots,
        "ad_ready_coverage_pct": ad_ready_coverage_pct,
        "chain_next_ad_roots": chain_next_ad_roots,
        "failure_counts_by_reason": failure_counts,
        "failure_examples": failure_examples,
        "s_suspect_non_session": s_suspect_non_session,
        # (K2, repaired K6 NOTE-1) auditable observation path — stamped only
        # when this run actually made a vendor attempt on ≥1 oi_D cell; else
        # `None` (no run ever falsely attributed to the endpoint it didn't
        # use).
        "oi_D_source": oi_D_source,
    }


def _write_daily_receipt(store: Path, receipt: dict) -> None:
    """(§D) Read-modify-write `_manifest.json`, preserving every OTHER
    top-level key (backfill's store/n_roots/per_root/updated_at, and any
    unknown key) — only `daily_refresh` is replaced. (F16) An unreadable
    manifest logs ONE warning and is treated as empty (fail-open); this
    writer never raises on a corrupt read."""
    p = store / "_manifest.json"
    preserved: dict = {}
    if p.exists():
        try:
            preserved = json.loads(p.read_text())
        except Exception as e:  # noqa: BLE001 — F16 fail-open
            log.warning("topup daily: unreadable manifest %s (%s: %s) — "
                       "regenerating fresh, preserving nothing", p,
                       type(e).__name__, e)
            preserved = {}
    doc = dict(preserved)
    doc["daily_refresh"] = receipt
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2, default=str, sort_keys=True))
    tmp.replace(p)


def _refresh_live_flow_baselines(runtime: Path, store: Path, source_session: _date) -> dict:
    """Refresh the existing consumer's artifact, without running its producer.

    Called only after a healthy natural source update, while its source-store
    lock still excludes parquet writers. The child uses the consumer's own
    environment, data directory and universe. Its strict build preserves the
    last artifact on missing/stale roots; this never starts a flow cycle.
    """
    wrapper = runtime / "ops/launchd/run_with_env.sh"
    env_file = runtime / ".env"
    if not runtime.is_absolute() or not wrapper.is_file() or not env_file.is_file():
        log.error("topup daily: baseline consumer runtime is not provisioned")
        return {"status": "failed", "reason": "consumer_runtime_unavailable"}
    try:
        result = subprocess.run(
            [str(wrapper), str(env_file), sys.executable, "-m",
             "scripts.build_live_flow_baselines", "--poll-universe", "--chunk-size", "1",
             "--require-source-session", source_session.isoformat(),
             "--expected-store", str(store.resolve())],
            cwd=runtime, timeout=600, check=False,
        )
    except subprocess.TimeoutExpired:
        log.error("topup daily: baseline refresh exceeded its separate 600s bound")
        return {"status": "failed", "reason": "timeout"}
    except OSError as exc:
        log.error("topup daily: baseline refresh could not launch: %s", type(exc).__name__)
        return {"status": "failed", "reason": "launch_failed"}
    return {"status": "complete" if result.returncode == 0 else "failed",
            "returncode": result.returncode, "source_session": source_session.isoformat()}


def _daily_main(*, workers: int, deadline_min: float, forced: bool,
                now_fn: Callable[[], datetime] | None = None,
                baseline_runtime: Path | None = None,
                d_session_observation: _DSessionObservation | None = None) -> int:
    now_fn = now_fn or (lambda: datetime.now(timezone.utc))
    started_at = datetime.now(timezone.utc)

    entered_at = now_fn()
    ctx = _resolve_daily_context(entered_at, forced=forced)
    if ctx is None:
        log.info("topup daily: gate closed (non-session day or before 16:10 ET) "
                 "— clean no-op, no receipt")
        return 0

    shared_deadline_at = (_time.monotonic() + max(0., deadline_min)*60
                          if d_session_observation is not None else None)

    try:
        store = Path(resolve_thetadata_store(
            required=True, purpose="daily incremental T1 maintainer"))
    except Exception as e:  # noqa: BLE001
        log.error("topup daily: no thetadata store: %s", e)
        return 1

    # (HARDENING, R3) A `with` statement would let an OSError from opening
    # the lock file (read-only store, ENOSPC) propagate as a bare traceback.
    # Acquire manually so that failure mode is a clean logged `failed`
    # outcome instead — the flock-refused (acquired=False) path is untouched.
    lock_cm = _writer_lock(store)
    try:
        acquired = lock_cm.__enter__()
    except OSError as e:
        log.error("topup daily: cannot open writer lock at %s (%s: %s) — "
                 "store may be read-only or full — aborting as failed, no receipt",
                 store / WRITER_LOCK_NAME, type(e).__name__, e)
        return 1

    try:
        if not acquired:
            _emit_writer_locked("daily")
            log.warning("topup daily: writer lock held by another process — "
                       "refusing (no mutation, no receipt)")
            return 0   # F14

        observation = None

        def _finish(status: str, **extra) -> dict:
            finished_at = datetime.now(timezone.utc)
            receipt = {
                "source": "thetadata",
                "mode": "incremental_daily",
                "S": ctx.S.isoformat() if ctx.S else None,
                "D": ctx.D.isoformat(),
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
                "elapsed_sec": (finished_at - started_at).total_seconds(),
                "worker_count": workers,
                "status": status,
                "forced": forced,
                "t1_universe_count": None,
                "ad_universe_count": None,
                "eod_S_roots": None,
                "greeks_S_roots": None,
                "oi_S_roots": None,
                "oi_D_roots": None,
                "complete_t1_roots": None,
                "s_panel_ad_roots": None,
                "s_panel_coverage_pct": None,
                "ad_ready_roots": None,
                "ad_ready_coverage_pct": None,
                "chain_next_ad_roots": None,
                "deadline_exceeded": False,
                "stale_tmp_swept": 0,
                "s_suspect_non_session": False,
                "failure_counts_by_reason": {},
                "failure_examples": [],
                "terminal_health": None,
                "oi_D_source": None,
            }
            if observation is not None:
                receipt['d_session_observation'] = observation
            receipt.update(extra)
            _write_daily_receipt(store, receipt)
            return receipt

        if ctx.S is None:
            _finish("failed",
                   failure_counts_by_reason={"session_resolution_failed": 1},
                   failure_examples=[{"root": None,
                                     "reason": "session_resolution_failed"}])
            log.error("topup daily: session_n_back(%s, 1) returned None — aborting", ctx.D)
            return 1

        if d_session_observation is not None:
            try:
                observation = _observe_spy_d_session(store, ctx, entered_at, shared_deadline_at,
                    d_session_observation, request_options=_dated_greek_request_options('SPY'))
            except Exception as exc:
                # A failed return/durability write cannot certify attempt absence.
                # Preserve the private claim and isolate the optional lane from
                # the existing four-cell maintenance and its health calculation.
                observation = dict(state='EFFECT_UNKNOWN', attempts=None,
                    reason='observation_return_unavailable', error_type=type(exc).__name__,
                    canonical_writes=0, hub_promotion=False)

        stale_tmp_swept = _sweep_stale_tmp(store)

        # (F7/RF5) pgrep breadcrumb — ADVISORY ONLY in --daily. The flock is
        # the sole refusal authority here; this never blocks, it only leaves
        # an operator-visible trail (an orphaned backfill child, or a
        # concurrent manual run, can leave a false-positive pgrep hit for as
        # long as the orphan lives — a refusal on that basis would be wrong).
        if _backfill_running():
            log.warning("topup daily: backfill_thetadata_eod appears to be "
                       "running (pgrep advisory only in --daily — continuing; "
                       "the flock already granted exclusive access)")

        from collectors import thetadata as td
        if not td.reachable():
            _finish("failed", terminal_health="unreachable",
                   stale_tmp_swept=stale_tmp_swept)
            log.error("topup daily: theta terminal unreachable — aborting before pulls")
            return 1

        try:
            t1_universe = _daily_universe()
            ad_universe = _ad_universe()
        except Exception as e:  # noqa: BLE001
            _finish("failed", terminal_health="reachable",
                   stale_tmp_swept=stale_tmp_swept,
                   failure_counts_by_reason={type(e).__name__: 1})
            log.error("topup daily: universe resolution failed: %s", e)
            return 1

        remaining_deadline_min = (deadline_min if shared_deadline_at is None else
                                 max(0., (shared_deadline_at-_time.monotonic())/60))
        results, deadline_exceeded, terminal_lost = _run_daily_pool(
            store, t1_universe, td, workers=workers,
            deadline_min=remaining_deadline_min, ctx=ctx)

        agg = _aggregate_daily(results, t1_universe, ad_universe)

        if terminal_lost:
            _finish("failed", terminal_health="lost_mid_run",
                   stale_tmp_swept=stale_tmp_swept,
                   deadline_exceeded=deadline_exceeded, **agg)
            log.error("topup daily: fetch_failed > 25%% of attempted roots and "
                     "the re-probe found the terminal unreachable — aborting "
                     "as failed (terminal_lost_mid_run)")
            return 1

        gate = _source_coverage_gate()
        # (K1, Sol B1a) `healthy` now certifies the AD-READY split (S-panel
        # PLUS OI[D]), not the S-panel alone. OI[D] absent everywhere ⇒
        # ad_ready_coverage_pct == 0.0 ⇒ NEVER healthy, no matter how
        # complete the observational S-panel is — the frozen AD source
        # contract requires the settlement print (`chain_next`) to certify
        # an S/D panel; `s_panel_coverage_pct` is reported but certifies
        # nothing.
        healthy = agg["ad_ready_coverage_pct"] >= gate
        # (RF2, R3) deadline_exceeded FORCES partial — a run that ran out of
        # wall-clock time is by definition unfinished, no matter how much
        # coverage the roots it DID reach happened to hit. Never let a
        # high-coverage partial pool read as `healthy`.
        status = "partial" if deadline_exceeded else ("healthy" if healthy else "partial")
        source_receipt = _finish(status, terminal_health="reachable",
                                 stale_tmp_swept=stale_tmp_swept,
                                 deadline_exceeded=deadline_exceeded, **agg)
        log.info("topup daily: S=%s D=%s ad_ready_coverage=%.1f%% status=%s "
                "deadline_exceeded=%s", ctx.S, ctx.D,
                agg["ad_ready_coverage_pct"] * 100, status, deadline_exceeded)
        if status == "healthy" and not forced and baseline_runtime is not None:
            baseline_started = datetime.now(timezone.utc).isoformat()
            baseline = _refresh_live_flow_baselines(baseline_runtime, store, ctx.S)
            # Source health and downstream refresh are separate facts. A child
            # failure must neither rewrite source health nor claim delivery.
            baseline.update(started_at=baseline_started,
                            finished_at=datetime.now(timezone.utc).isoformat())
            source_receipt["live_flow_baselines"] = baseline
            _write_daily_receipt(store, source_receipt)
            if baseline["status"] != "complete":
                return 1
        return 0 if status == "healthy" else 1
    finally:
        lock_cm.__exit__(None, None, None)


# One commissioned observation; this is not a daily/date/budget registry.
_SPY_20261026_OPERATION = 'spy-2026-10-26-1730-observation-v1'
_SPY_20261026_RETENTION_PARENT = Path('/Users/chriswong/optionshub-ops-wt/.git/options-source-captures')


def _configured_d_session_observation(*, daily, forced, deadline_min):
    """Bind the existing CLI/wrapper to one default-off, source-qualified pilot.

    The host owner must qualify/install this source and actual account/capacity
    before setting the exact operation token. Configuration is not evidence of
    entitlement, first availability, model semantics, or a new provider budget.
    No network, claim, directory creation or schedule change occurs here.
    """
    import os
    selected = os.environ.get('THETADATA_D_SESSION_OBSERVATION')
    if selected in (None, ''):
        return None
    if (selected != _SPY_20261026_OPERATION or not daily or forced
            or deadline_min != _DEFAULT_DEADLINE_MIN):
        raise ValueError('Observation supports only exact Oct26 natural daily operation with65min deadline')
    from collectors import thetadata as td
    transport = td.bounded_spy_d_session_transport(_date(2026,10,26))
    if transport.origin != 'http://127.0.0.1:25503' or not callable(getattr(transport, 'preflight', None)):
        raise ValueError('Observation native source/capacity contract is unqualified')
    return _DSessionObservation(
        _SPY_20261026_RETENTION_PARENT,
        '01a156f1-f450-7793-8951-bddadd4784c2',
        '01a15700-1ae2-7a73-9756-f1546da7ace8',
        transport, session_day=_date(2026,10,26), capacity_preflight=transport.preflight)


# ── CLI ───────────────────────────────────────────────────────────────────
def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="ThetaData T1 store top-up + daily incremental maintainer.")
    ap.add_argument("--roots", default=None,
                    help="comma-separated roots, or '@universe' for the "
                         "resolved T1 universe (explicit catch-up, F10)")
    ap.add_argument("--date", default=None,
                    help="session date YYYY-MM-DD (default: last weekday before today)")
    ap.add_argument("--daily", action="store_true",
                    help="market-wide incremental daily mode (mutually "
                         "exclusive with --roots/--date)")
    ap.add_argument("--workers", type=int, default=None,
                    help=f"--daily worker pool size (default {_DAILY_WORKERS_DEFAULT}; "
                         f"hard cap {_MAX_WORKERS})")
    ap.add_argument("--deadline-min", type=float, default=_DEFAULT_DEADLINE_MIN,
                    help="--daily hard wall-clock deadline in minutes (F2)")
    ap.add_argument("--force-run", action="store_true",
                    help="--daily: bypass the session/time gate for diagnostics "
                         "ONLY; stamps forced=true in the receipt")
    ap.add_argument("--baseline-runtime", type=Path,
                    help="--daily: refresh this provisioned live-flow runtime's baseline after healthy natural updates")
    return ap


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = _build_parser()
    args = ap.parse_args(argv)
    try:
        _dated_greek_request_options("")  # fail before any acquisition on bad config
    except ValueError as exc:
        ap.error(str(exc))

    if args.daily and (args.roots is not None or args.date is not None):
        ap.error("--daily is mutually exclusive with --roots/--date")
    if not args.daily and args.roots is None:
        ap.error("--roots is required unless --daily is given")
    if args.baseline_runtime is not None and not args.daily:
        ap.error("--baseline-runtime requires --daily")
    if args.workers is not None and args.workers > _MAX_WORKERS:
        ap.error(f"--workers must be <= {_MAX_WORKERS} (hard vendor-safety cap)")

    try:
        observation = _configured_d_session_observation(
            daily=args.daily, forced=args.force_run, deadline_min=args.deadline_min)
    except ValueError as exc:
        ap.error(str(exc))

    if args.daily:
        workers = args.workers if args.workers is not None else _DAILY_WORKERS_DEFAULT
        return _daily_main(workers=workers, deadline_min=args.deadline_min,
                           forced=args.force_run, baseline_runtime=args.baseline_runtime,
                           d_session_observation=observation)

    # ---- legacy / @universe bounded mode ----
    try:
        store = Path(resolve_thetadata_store(required=True, purpose="pre-open day top-up"))
    except Exception as e:  # noqa: BLE001
        log.error("topup: no thetadata store: %s", e)
        return 1

    if args.roots.strip() == "@universe":
        from scripts.backfill_thetadata_eod import _resolve_universe
        roots = _resolve_universe()
        log.info("topup: @universe resolved to %d roots", len(roots))
    else:
        roots = [r.strip().upper() for r in args.roots.split(",") if r.strip()]

    day = (_date.fromisoformat(args.date) if args.date
           else _last_weekday_before(_date.today()))

    if _backfill_running():
        log.warning("topup: backfill_thetadata_eod is running — skipping merge "
                    "entirely (never race the year-overwrite writer)")
        return 1

    try:
        with _writer_lock(store) as acquired:
            if not acquired:
                _emit_writer_locked("legacy")
                log.warning("topup: writer lock held by another process — refusing")
                return 1
            return _run_bounded(store, roots, day)
    except OSError as e:
        # (HARDENING, R3) — read-only store / ENOSPC opening the lock file:
        # a clean logged failure, never a bare traceback.
        log.error("topup: cannot open writer lock at %s (%s: %s) — store may be "
                 "read-only or full", store / WRITER_LOCK_NAME, type(e).__name__, e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
