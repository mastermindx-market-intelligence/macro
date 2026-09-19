"""Tests for engine/brief_delivery_producer.py (W6-B MO-PAID-032 child).

RED-first, no network: every IO function is monkeypatched.
All tests are fixture-only — no data/ site/ reads (sparse-safe).
Does not import engine.capital_structure.
"""
from __future__ import annotations

import urllib.error

import pytest

from engine import brief_delivery_producer as prod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _et(year, month, day, hour, minute):
    """Naive datetime in ET zone (adds tzinfo for use with astimezone)."""
    import datetime
    from lib.nyse_calendar import ET
    naive = datetime.datetime(year, month, day, hour, minute)
    return naive.replace(tzinfo=ET)


def _utc_now_for_et(et_dt):
    """Return a UTC ISO8601 string for a given ET datetime for use as now_utc arg."""
    import datetime
    utc = et_dt.astimezone(datetime.timezone.utc)
    return utc.isoformat()


# ---------------------------------------------------------------------------
# Test 1 — Daily slot: Wednesday 18:30 ET is_session → compute_slot returns that Wednesday
# ---------------------------------------------------------------------------

def test_daily_slot_returns_wednesday_when_session_and_after_close(monkeypatch):
    """Wednesday 18:30 ET (2026-09-16) is a session day and close has passed."""
    now = _et(2026, 9, 16, 18, 30)  # Wednesday
    slot = prod.compute_slot("daily_after_us_close", now)
    assert slot is not None
    assert slot.year == 2026
    assert slot.month == 9
    assert slot.day == 16


def test_daily_slot_is_none_for_weekly_saturday_on_same_day(monkeypatch):
    """Same day (Saturday logic): compute_slot('weekly_saturday') must be None
    because the day is Wednesday (not Saturday)."""
    now = _et(2026, 9, 16, 18, 30)  # Wednesday
    slot = prod.compute_slot("weekly_saturday", now)
    assert slot is None


# ---------------------------------------------------------------------------
# Test 2 — Before close: Wednesday 15:00 ET → daily slot is None
# ---------------------------------------------------------------------------

def test_daily_slot_is_none_before_close(monkeypatch):
    """Wednesday 15:00 ET — close (17:00) has not yet passed."""
    now = _et(2026, 9, 16, 15, 0)  # Wednesday, before 17:00 ET
    slot = prod.compute_slot("daily_after_us_close", now)
    assert slot is None


# ---------------------------------------------------------------------------
# Test 3 — Weekly slot: Saturday 18:30 ET → weekly == that Saturday; daily is None
# ---------------------------------------------------------------------------

def test_weekly_slot_returns_saturday_when_after_close(monkeypatch):
    """Saturday 18:30 ET: weekly slot is that Saturday; daily is None (Saturday != session)."""
    now = _et(2026, 9, 19, 18, 30)  # Saturday
    weekly_slot = prod.compute_slot("weekly_saturday", now)
    assert weekly_slot is not None
    assert weekly_slot.weekday() == 5  # Saturday

    daily_slot = prod.compute_slot("daily_after_us_close", now)
    assert daily_slot is None  # Saturday is not a session


# ---------------------------------------------------------------------------
# Test 4 — Skip paused: one active + one paused sub → exactly one planned insert
# MAJOR 1: run() guards state=="active" itself; suite feeds both active+paused
# ---------------------------------------------------------------------------

def test_skips_paused_subscriptions(monkeypatch):
    """Active sub gets a plan; paused sub filtered by run()'s own state guard (MAJOR 1)."""
    active_sub = {"id": "sub-active-001", "state": "active", "cadence": "daily_after_us_close", "user_id": "u1"}
    paused_sub = {"id": "sub-paused-001", "state": "paused", "cadence": "daily_after_us_close", "user_id": "u2"}
    written_ids = []

    def fake_read_active_subscriptions(limit=500):
        # GET returns both active and paused — run() must filter by state itself
        return prod.TypedRead(prod.READ_OK, [active_sub, paused_sub])

    def fake_read_existing_deliveries(pairs):
        return prod.TypedRead(prod.READ_OK_ZERO, [])

    def fake_insert_delivery(row, *, dry_run):
        if not dry_run:
            written_ids.append(row["subscription_id"])
        return (not dry_run, False)

    monkeypatch.setattr(prod, "read_active_subscriptions", fake_read_active_subscriptions)
    monkeypatch.setattr(prod, "read_existing_deliveries", fake_read_existing_deliveries)
    monkeypatch.setattr(prod, "insert_delivery", fake_insert_delivery)

    now_utc = _utc_now_for_et(_et(2026, 9, 16, 18, 30))
    result = prod.run(now_utc=now_utc, dry_run=False, limit=500)
    assert result.planned_n == 1
    assert result.written_n == 1
    # Only the active sub was planned/written
    assert written_ids == ["sub-active-001"]


# ---------------------------------------------------------------------------
# Test 5 — No subscription → no write
# ---------------------------------------------------------------------------

def test_no_active_subscriptions_produces_zero_writes(monkeypatch):
    """Empty GET response: 0 planned, 0 written."""

    def fake_read_active_subscriptions(limit=500):
        return prod.TypedRead(prod.READ_OK_ZERO, [])

    monkeypatch.setattr(prod, "read_active_subscriptions", fake_read_active_subscriptions)

    result = prod.run(now_utc=_utc_now_for_et(_et(2026, 9, 16, 18, 30)), dry_run=False)
    assert result.planned_n == 0
    assert result.written_n == 0
    assert result.duplicate_n == 0


# ---------------------------------------------------------------------------
# Test 6 — Degraded first slice: planned row has correct degraded fields
# ---------------------------------------------------------------------------

def test_degraded_first_slice_fields(monkeypatch):
    """Planned row: state=='degraded', degraded_reason=='no_artifact',
    artifact_asof is None, body=={}."""
    active_sub = {"id": "sub-001", "state": "active", "cadence": "daily_after_us_close", "user_id": "u1"}
    planned_rows = []

    def fake_read_active_subscriptions(limit=500):
        return prod.TypedRead(prod.READ_OK, [active_sub])

    def fake_read_existing_deliveries(pairs):
        return prod.TypedRead(prod.READ_OK_ZERO, [])

    def fake_insert_delivery(row, *, dry_run):
        planned_rows.append(row)
        return (True, False) if not dry_run else (False, False)

    monkeypatch.setattr(prod, "read_active_subscriptions", fake_read_active_subscriptions)
    monkeypatch.setattr(prod, "read_existing_deliveries", fake_read_existing_deliveries)
    monkeypatch.setattr(prod, "insert_delivery", fake_insert_delivery)

    result = prod.run(now_utc=_utc_now_for_et(_et(2026, 9, 16, 18, 30)), dry_run=False)
    assert result.planned_n == 1
    assert len(planned_rows) == 1
    row = planned_rows[0]
    assert row["state"] == "degraded"
    assert row["degraded_reason"] == "no_artifact"
    assert row["artifact_asof"] is None
    assert row["body"] == {}


# ---------------------------------------------------------------------------
# Test 7 — Idempotent: two run() calls → first writes 1, second writes 0, dup=1
# MAJOR 2: pre-SELECT skip increments duplicate_n
# ---------------------------------------------------------------------------

def test_idempotent_second_run_reports_duplicate(monkeypatch):
    """First run writes 1; second run pre-SELECT finds the pair and counts duplicate_n=1
    (MAJOR 2 — mirrors thesis_condition_monitor.py:756)."""
    active_sub = {"id": "sub-001", "state": "active", "cadence": "daily_after_us_close", "user_id": "u1"}
    _written_pairs: set = set()
    store: list = []

    def fake_read_active_subscriptions(limit=500):
        return prod.TypedRead(prod.READ_OK, [active_sub])

    def fake_read_existing_deliveries(pairs):
        rows = [{"subscription_id": sid, "slot_asof": asof.isoformat()}
                for sid, asof in pairs if (sid, asof) in _written_pairs]
        return prod.TypedRead(prod.READ_OK if rows else prod.READ_OK_ZERO, rows)

    def fake_insert_delivery(row, *, dry_run):
        if not dry_run:
            store.append(row)
            slot_asof = row["slot_asof"]
            if isinstance(slot_asof, str):
                from datetime import date as date_class
                slot_asof = date_class.fromisoformat(slot_asof)
            _written_pairs.add((row["subscription_id"], slot_asof))
        return (not dry_run, False)

    monkeypatch.setattr(prod, "read_active_subscriptions", fake_read_active_subscriptions)
    monkeypatch.setattr(prod, "read_existing_deliveries", fake_read_existing_deliveries)
    monkeypatch.setattr(prod, "insert_delivery", fake_insert_delivery)

    now_utc = _utc_now_for_et(_et(2026, 9, 16, 18, 30))
    r1 = prod.run(now_utc=now_utc, dry_run=False)
    assert r1.written_n == 1
    assert r1.duplicate_n == 0
    assert r1.planned_n == 1
    assert r1.outcome == "ok"
    assert len(store) == 1

    r2 = prod.run(now_utc=now_utc, dry_run=False)
    assert r2.written_n == 0
    assert r2.duplicate_n == r2.planned_n  # before-dedup planned_n; skip is a duplicate
    assert r2.planned_n == 1
    assert r2.outcome == "ok"
    assert len(store) == 1         # still exactly 1 row in DB


# ---------------------------------------------------------------------------
# Test 8 — Dry-run writes nothing
# ---------------------------------------------------------------------------

def test_dry_run_produces_zero_posts(monkeypatch):
    """dry_run=True: 0 POSTs."""
    active_sub = {"id": "sub-001", "state": "active", "cadence": "daily_after_us_close", "user_id": "u1"}
    post_count = []

    def fake_read_active_subscriptions(limit=500):
        return prod.TypedRead(prod.READ_OK, [active_sub])

    def fake_read_existing_deliveries(pairs):
        return prod.TypedRead(prod.READ_OK_ZERO, [])

    def fake_insert_delivery(row, *, dry_run):
        if not dry_run:
            post_count.append(row)
        return (False, False)  # never written

    monkeypatch.setattr(prod, "read_active_subscriptions", fake_read_active_subscriptions)
    monkeypatch.setattr(prod, "read_existing_deliveries", fake_read_existing_deliveries)
    monkeypatch.setattr(prod, "insert_delivery", fake_insert_delivery)

    result = prod.run(now_utc=_utc_now_for_et(_et(2026, 9, 16, 18, 30)), dry_run=True)
    assert result.planned_n == 1
    assert result.written_n == 0
    assert result.duplicate_n == 0
    assert result.outcome == "ok"  # dry-run is not a failure (M1)
    assert post_count == []  # no POSTs attempted


# ---------------------------------------------------------------------------
# Test 9 — No secrets: stdout never contains the monkeypatched key string
# ---------------------------------------------------------------------------

def test_no_secrets_in_output(monkeypatch, capsys):
    """run() output must not contain the monkeypatched key value."""
    active_sub = {"id": "sub-001", "state": "active", "cadence": "daily_after_us_close", "user_id": "u1"}

    def fake_read_active_subscriptions(limit=500):
        return prod.TypedRead(prod.READ_OK, [active_sub])

    def fake_read_existing_deliveries(pairs):
        return prod.TypedRead(prod.READ_OK_ZERO, [])

    def fake_insert_delivery(row, *, dry_run):
        return (True, False) if not dry_run else (False, False)

    fake_key = "test-secret-key-xyz-123"
    # Monkeypatch _env directly since creds are now loaded per-call
    monkeypatch.setattr(prod, "_env", lambda name: fake_key if name == "SUPABASE_SERVICE_ROLE_KEY" else "https://example.supabase.co")
    monkeypatch.setattr(prod, "read_active_subscriptions", fake_read_active_subscriptions)
    monkeypatch.setattr(prod, "read_existing_deliveries", fake_read_existing_deliveries)
    monkeypatch.setattr(prod, "insert_delivery", fake_insert_delivery)

    prod.run(now_utc=_utc_now_for_et(_et(2026, 9, 16, 18, 30)), dry_run=False)
    out = capsys.readouterr().out
    assert fake_key not in out


# ---------------------------------------------------------------------------
# Test 10 — READ_UNAVAILABLE: always returns a result object, never raises
# ---------------------------------------------------------------------------

def test_read_unavailable_returns_result_object(monkeypatch):
    """Missing credentials / table absent: returns ProducerResult with READ_UNAVAILABLE."""

    def fake_read_active_subscriptions(limit=500):
        return prod.TypedRead(prod.READ_UNAVAILABLE, None, "no_credentials")

    monkeypatch.setattr(prod, "read_active_subscriptions", fake_read_active_subscriptions)

    result = prod.run(now_utc=_utc_now_for_et(_et(2026, 9, 16, 18, 30)), dry_run=False)
    assert result.read_state == prod.READ_UNAVAILABLE
    assert result.error_class == "no_credentials"
    assert result.written_n == 0
    assert isinstance(result, prod.ProducerResult)


# ---------------------------------------------------------------------------
# Test 11 — MAJOR 2: fake 409 / 23505 drives insert_delivery's real branch
# -> written=False, duplicate=True, duplicate_n incremented
# ---------------------------------------------------------------------------

def test_fake_409_counts_as_duplicate(monkeypatch):
    """HTTP 409 / 23505 from insert_delivery: written=False, duplicate=True, duplicate_n++.
    Mirrors thesis_condition_monitor.py:656-658. This drives the real branch in
    insert_delivery 409 branch through a fake transport."""
    active_sub = {"id": "sub-001", "state": "active", "cadence": "daily_after_us_close", "user_id": "u1"}

    def fake_read_active_subscriptions(limit=500):
        return prod.TypedRead(prod.READ_OK, [active_sub])

    def fake_read_existing_deliveries(pairs):
        return prod.TypedRead(prod.READ_OK_ZERO, [])

    # Fake a 409 response from the POST — drives insert_delivery's real branch
    class FakeHTTPError(urllib.error.HTTPError):
        def __init__(self):
            pass
        @property
        def code(self):
            return 409
        def read(self):
            return b"23505 duplicate key"

    original_pg = prod._pg

    def fake_pg(method, path, body=None, prefer=None, timeout=6):
        if method == "POST" and "brief_deliveries" in path:
            raise FakeHTTPError()
        return original_pg(method, path, body, prefer, timeout)

    monkeypatch.setattr(prod, "read_active_subscriptions", fake_read_active_subscriptions)
    monkeypatch.setattr(prod, "read_existing_deliveries", fake_read_existing_deliveries)
    monkeypatch.setattr(prod, "_pg", fake_pg)

    result = prod.run(now_utc=_utc_now_for_et(_et(2026, 9, 16, 18, 30)), dry_run=False)
    assert result.written_n == 0
    assert result.duplicate_n == 1
    assert result.planned_n == 1


# ---------------------------------------------------------------------------
# Test 12 — MINOR m4: non-409 POST failure -> outcome="partial" or "error", failed_n counted
# ---------------------------------------------------------------------------

def test_non_409_post_failure_reports_partial_outcome(monkeypatch):
    """Non-409 HTTP error: outcome is 'partial' (not 'ok'), row not written."""
    active_sub = {"id": "sub-001", "state": "active", "cadence": "daily_after_us_close", "user_id": "u1"}

    def fake_read_active_subscriptions(limit=500):
        return prod.TypedRead(prod.READ_OK, [active_sub])

    def fake_read_existing_deliveries(pairs):
        return prod.TypedRead(prod.READ_OK_ZERO, [])

    class FakeHTTPError(urllib.error.HTTPError):
        def __init__(self):
            pass
        @property
        def code(self):
            return 500

    original_pg = prod._pg

    def fake_pg(method, path, body=None, prefer=None, timeout=6):
        if method == "POST" and "brief_deliveries" in path:
            raise FakeHTTPError()
        return original_pg(method, path, body, prefer, timeout)

    monkeypatch.setattr(prod, "read_active_subscriptions", fake_read_active_subscriptions)
    monkeypatch.setattr(prod, "read_existing_deliveries", fake_read_existing_deliveries)
    monkeypatch.setattr(prod, "_pg", fake_pg)

    result = prod.run(now_utc=_utc_now_for_et(_et(2026, 9, 16, 18, 30)), dry_run=False)
    assert result.written_n == 0
    assert result.planned_n == 1
    assert result.outcome in ("partial", "error")  # m4: not "ok"


# ---------------------------------------------------------------------------
# Test 13 — BLOCKER 1(i): armed mode + real env + fake transport POSTs
# GET returns PRODUCTION-SHAPED rows (exactly the selected columns, no extra keys).
# ---------------------------------------------------------------------------

def _select_cols(path: str) -> list[str] | None:
    """Parse PostgREST `select=` from a `_pg` path (table?query)."""
    from urllib.parse import parse_qs

    if "?" not in path:
        return None
    raw = (parse_qs(path.split("?", 1)[1], keep_blank_values=True).get("select") or [None])[0]
    if not raw:
        return None
    return [c.strip() for c in raw.split(",") if c.strip()]


def _project_selected(row: dict, path: str) -> dict:
    """Return only the columns the producer actually selected (production shape)."""
    cols = _select_cols(path)
    if cols is None:
        return dict(row)
    return {k: row[k] for k in cols if k in row}


def test_armed_mode_posts_one_production_shaped_active_row(monkeypatch):
    """B1(i): ENABLE=1 + both Supabase env vars + fake transport.

    GET returns exactly the selected columns (no stuffed extra keys). One due
    active daily sub on a Wednesday after close → written_n == 1, error_class
    is None, exactly one POST. Fails at 4c9392ab because select omits `state`
    and run() then drops every row.
    """
    store_row = {
        "id": "sub-001",
        "state": "active",
        "cadence": "daily_after_us_close",
        "user_id": "u1",
        "subject_ref": "macro",
    }
    posts: list = []

    def fake_pg(method, path, body=None, prefer=None, timeout=6):
        if method == "GET" and path.startswith("brief_subscriptions"):
            return [_project_selected(store_row, path)]
        if method == "GET" and path.startswith("brief_deliveries"):
            return []
        if method == "POST" and "brief_deliveries" in path:
            posts.append(body)
            return None
        raise AssertionError("unexpected %s %s" % (method, path))

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
    monkeypatch.setenv("BRIEF_DELIVERIES_ENABLE", "1")
    monkeypatch.setattr(prod, "_pg", fake_pg)

    result = prod.run(
        now_utc=_utc_now_for_et(_et(2026, 9, 16, 18, 30)),
        dry_run=False,
    )
    assert result.written_n == 1
    assert result.error_class is None
    assert result.outcome == "ok"
    assert len(posts) == 1
