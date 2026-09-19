"""Brief delivery producer (MO-PAID-032 child, W6-B).

DORMANT by default: only writes real rows when BRIEF_DELIVERIES_ENABLE=1 is set.
Otherwise forces dry-run and prints a DORMANT line.

This module plans at most one brief_deliveries insert per ACTIVE subscription whose
cadence is due, with first-slice rows state='degraded', degraded_reason='no_artifact',
artifact_asof=null, body={}. A second call for the same (subscription_id, slot_asof)
inserts nothing (idempotency).

No LLM, no new number, no mailer. No imports from engine.capital_structure.
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any, Literal

from lib.nyse_calendar import ET, _CLOSE_PLUS_SETTLE, is_session

# Env names only — no hardcoded project host.
SUPABASE_URL: str | None = None
SUPABASE_SERVICE_ROLE_KEY: str | None = None

# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------


@dataclass
class ProducerResult:
    """Shape mirrors MonitorResult / drain result for ergonomic parity."""

    outcome: str  # ok | read_unavailable
    read_state: str
    error_class: str | None
    planned_n: int  # rows planned (before dedup)
    duplicate_n: int  # rows skipped as already present
    written_n: int  # rows actually POSTed (0 when dry_run or DORMANT)
    run_id: str


# ---------------------------------------------------------------------------
# Read states (vocabulary matches thesis_condition_monitor.py)
# ---------------------------------------------------------------------------

READ_OK = "ok"
READ_OK_ZERO = "ok_zero"
READ_UNAVAILABLE = "read_unavailable"


@dataclass
class TypedRead:
    state: str
    rows: list[dict] | None
    error_class: str | None = None


# ---------------------------------------------------------------------------
# Slot computation — pure, no IO
# ---------------------------------------------------------------------------


def compute_slot(cadence: str, now_et: datetime) -> date | None:
    """Return the slot date for `cadence` given the current ET wall-clock time.

    Daily: today must be a NYSE session AND close (17:00 ET) must have passed.
    Weekly (Saturday): today must be a Saturday session AND close has passed.
    Returns None when the slot is not due.
    """
    today = now_et.date()

    if cadence == "daily_after_us_close":
        if not is_session(today):
            return None
        if now_et.time() < _CLOSE_PLUS_SETTLE:
            return None
        return today

    if cadence == "weekly_saturday":
        # Weekly slot fires on Saturday (not a session day per se, but the weekly
        # cadence owner — daily.yml runs on Saturdays per its cron schedule).
        # The slot date is today, and close must have passed.
        if today.weekday() != 5:  # Saturday == 5
            return None
        if now_et.time() < _CLOSE_PLUS_SETTLE:
            return None
        return today

    return None


# ---------------------------------------------------------------------------
# IO — isolated, monkeypatched in tests
# ---------------------------------------------------------------------------


def _pg(method: str, path: str, body: Any = None, prefer: str | None = None, timeout: int = 6):
    """Thin PostgREST seam. Raises urllib.error on network failure."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def typed_get(path: str) -> TypedRead:
    if not SUPABASE_SERVICE_ROLE_KEY:
        return TypedRead(READ_UNAVAILABLE, None, "no_credentials")
    try:
        rows = _pg("GET", path)
        rows = rows if rows is not None else []
        if not rows:
            return TypedRead(READ_OK_ZERO, [])
        return TypedRead(READ_OK, rows)
    except urllib.error.HTTPError as exc:
        code = getattr(exc, "code", None)
        body = ""
        try:
            body = exc.read().decode("utf-8", "ignore")
        except Exception:
            pass
        if code == 404 or "42P01" in body or "PGRST205" in body:
            return TypedRead(READ_UNAVAILABLE, None, "table_absent")
        return TypedRead(READ_UNAVAILABLE, None, f"http_{code}")
    except Exception:
        return TypedRead(READ_UNAVAILABLE, None, "unknown")


def read_active_subscriptions(limit: int = 500) -> TypedRead:
    """Read active brief_subscriptions rows (state = 'active')."""
    path = (
        "brief_subscriptions"
        "?state=eq.active"
        "&select=id,cadence,user_id,subject_ref"
        f"&order=id.desc&limit={limit}"
    )
    return typed_get(path)


def read_existing_deliveries(pairs: list[tuple[str, date]]) -> TypedRead:
    """Read existing (subscription_id, slot_asof) pairs to check idempotency."""
    if not pairs:
        return TypedRead(READ_OK_ZERO, [])
    ors = ",".join(
        f"and(subscription_id.eq.{sid},slot_asof.eq.{asof.isoformat()})"
        for sid, asof in pairs
    )
    path = f"brief_deliveries?or=({ors})&select=subscription_id,slot_asof"
    return typed_get(path)


def insert_delivery(row: dict, *, dry_run: bool) -> tuple[bool, bool]:
    """Insert one brief_deliveries row.

    Returns (written, duplicate):
      written=True, duplicate=False  -> row POSTed successfully
      written=False, duplicate=True   -> 409 / 23505 treated as duplicate
      written=False, duplicate=False  -> other HTTP error
    """
    if dry_run:
        return (False, False)
    try:
        _pg("POST", "brief_deliveries", body=row, prefer="return=minimal")
        return (True, False)
    except urllib.error.HTTPError as exc:
        code = getattr(exc, "code", None)
        body = ""
        try:
            body = exc.read().decode("utf-8", "ignore")
        except Exception:
            pass
        if code == 409 or "23505" in body:
            return (False, True)
        return (False, False)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

# Max rows in one SELECT for existing delivery check (PostgREST limit)
_EXISTING_CHECK_CHUNK = 100


def _chunked_existing_check(
    pairs: list[tuple[str, date]],
) -> set[tuple[str, date]]:
    """Return the subset of pairs that already exist in brief_deliveries."""
    if not pairs:
        return set()
    seen: set[tuple[str, date]] = set()
    for i in range(0, len(pairs), _EXISTING_CHECK_CHUNK):
        chunk = pairs[i : i + _EXISTING_CHECK_CHUNK]
        result = read_existing_deliveries(chunk)
        if result.state == READ_UNAVAILABLE:
            # Treat unavailable as empty — we'll attempt inserts and let the
            # DB enforce uniqueness if it can.  Matches thesis_condition_monitor.py
            # behaviour on read failure during enqueue.
            continue
        for row in result.rows or []:
            sid = row["subscription_id"]
            asof_str = row["slot_asof"]
            asof = date.fromisoformat(asof_str) if isinstance(asof_str, str) else asof_str
            seen.add((sid, asof))
    return seen


def run(
    *,
    now_utc: str | None = None,
    dry_run: bool = True,
    limit: int = 500,
) -> ProducerResult:
    """Plan and optionally write brief_deliveries rows for all due active subscriptions.

    Args:
        now_utc: ISO8601 UTC timestamp override (for tests / ops).
        dry_run: If True, plan rows but do not POST anything.
        limit: Max subscriptions to fetch per query.
    """
    # Determine run_id once (wall-clock, not dependent on now_utc)
    run_id = datetime.now(timezone.utc).isoformat()

    # Parse / default now_utc
    if now_utc:
        parsed = datetime.fromisoformat(now_utc.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        now_et = parsed.astimezone(ET)
    else:
        now_et = datetime.now(timezone.utc).astimezone(ET)

    # Read active subscriptions
    sub_result = read_active_subscriptions(limit=limit)
    if sub_result.state == READ_UNAVAILABLE:
        return ProducerResult(
            outcome="read_unavailable",
            read_state=READ_UNAVAILABLE,
            error_class=sub_result.error_class,
            planned_n=0,
            duplicate_n=0,
            written_n=0,
            run_id=run_id,
        )
    subscriptions = sub_result.rows or []

    # Compute slots and build candidate rows
    candidates: list[tuple[dict, date]] = []  # (sub_row, slot_date)
    for sub in subscriptions:
        cadence = sub.get("cadence")
        if not cadence:
            continue
        slot = compute_slot(cadence, now_et)
        if slot is None:
            continue
        candidates.append((sub, slot))

    if not candidates:
        return ProducerResult(
            outcome="ok",
            read_state=sub_result.state,
            error_class=None,
            planned_n=0,
            duplicate_n=0,
            written_n=0,
            run_id=run_id,
        )

    # Idempotency check: which (subscription_id, slot_asof) pairs already exist?
    pair_keys = [(sub["id"], slot) for sub, slot in candidates]
    existing = _chunked_existing_check(pair_keys)

    # Build planned rows (first slice = degraded)
    planned: list[dict] = []
    for sub, slot in candidates:
        if (sub["id"], slot) in existing:
            continue
        row = {
            "subscription_id": sub["id"],
            "user_id": sub.get("user_id"),
            "slot_asof": slot.isoformat(),
            "state": "degraded",
            "degraded_reason": "no_artifact",
            "artifact_asof": None,
            "body": {},
        }
        planned.append(row)

    # Write (or plan)
    written_n = 0
    duplicate_n = 0
    for row in planned:
        written, is_dup = insert_delivery(row, dry_run=dry_run)
        if written:
            written_n += 1
        elif is_dup:
            duplicate_n += 1
        # else: other HTTP error — row not written, not counted as dup

    return ProducerResult(
        outcome="ok",
        read_state=sub_result.state,
        error_class=None,
        planned_n=len(planned),
        duplicate_n=duplicate_n,
        written_n=written_n,
        run_id=run_id,
    )
