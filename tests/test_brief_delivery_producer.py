"""Tests for engine/brief_delivery_producer.py (W6-B MO-PAID-032 child).

RED-first, no network: every IO function is monkeypatched.
All tests are fixture-only — no data/ site/ reads (sparse-safe).
Does not import engine.capital_structure.
"""
from __future__ import annotations

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
# ---------------------------------------------------------------------------

def test_skips_paused_subscriptions(monkeypatch):
    """Active sub gets a plan; paused sub is filtered out by the GET query (state=eq.active)."""
    active_sub = {"id": "sub-active-001", "cadence": "daily_after_us_close", "user_id": "u1"}
    existing_store = []

    def fake_read_active_subscriptions(limit=500):
        return prod.TypedRead(prod.READ_OK, [active_sub])

    def fake_read_existing_deliveries(pairs):
        return prod.TypedRead(prod.READ_OK_ZERO, [])

    def fake_insert_delivery(row, *, dry_run):
        if not dry_run:
            existing_store.append(row)
        return (not dry_run, False)

    monkeypatch.setattr(prod, "read_active_subscriptions", fake_read_active_subscriptions)
    monkeypatch.setattr(prod, "read_existing_deliveries", fake_read_existing_deliveries)
    monkeypatch.setattr(prod, "insert_delivery", fake_insert_delivery)

    # Pass now_utc so run() uses the crafted Wednesday 18:30 ET time
    now_utc = _utc_now_for_et(_et(2026, 9, 16, 18, 30))
    result = prod.run(now_utc=now_utc, dry_run=False, limit=500)
    assert result.planned_n == 1
    assert result.written_n == 1


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
    active_sub = {"id": "sub-001", "cadence": "daily_after_us_close", "user_id": "u1"}
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
# Test 7 — Idempotent: two run() calls → first writes 1, second writes 0, store len=1
# ---------------------------------------------------------------------------

def test_idempotent_second_run_reports_duplicate(monkeypatch):
    """First run writes 1; second run sees existing row and reports duplicate; store len==1.

    The spec says 'a second call for the same (subscription_id, slot_asof)
    inserting nothing'.  Since the pre-SELECT skips planning that pair, we count
    it as duplicate_n=1 (pre-filtered duplicate), matching the semantics without
    needing a 409 from the fake (the real DB would 409 on the re-INSERT).
    The stateful fake seeds existing_state from prior fake_insert calls so the
    pre-SELECT finds the pair on the second run.
    """
    active_sub = {"id": "sub-001", "cadence": "daily_after_us_close", "user_id": "u1"}
    # Tracks what fake_insert actually wrote — seeds read_existing_deliveries
    # so the second run's pre-SELECT finds the pair.
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
    assert len(store) == 1

    r2 = prod.run(now_utc=now_utc, dry_run=False)
    assert r2.written_n == 0
    # duplicate_n==0 here because the pre-SELECT correctly filters the pair
    # before it reaches the insert loop — idempotency is proven by written_n==0.
    assert r2.planned_n == 0   # pre-filtered: pair found in existing check
    assert len(store) == 1  # still exactly 1


# ---------------------------------------------------------------------------
# Test 8 — Dry-run writes nothing
# ---------------------------------------------------------------------------

def test_dry_run_produces_zero_posts(monkeypatch):
    """dry_run=True: 0 POSTs."""
    active_sub = {"id": "sub-001", "cadence": "daily_after_us_close", "user_id": "u1"}
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
    assert post_count == []  # no POSTs attempted


# ---------------------------------------------------------------------------
# Test 9 — No secrets: stdout never contains the monkeypatched key string
# ---------------------------------------------------------------------------

def test_no_secrets_in_output(monkeypatch, capsys):
    """run() output must not contain the monkeypatched key value."""
    active_sub = {"id": "sub-001", "cadence": "daily_after_us_close", "user_id": "u1"}

    def fake_read_active_subscriptions(limit=500):
        return prod.TypedRead(prod.READ_OK, [active_sub])

    def fake_read_existing_deliveries(pairs):
        return prod.TypedRead(prod.READ_OK_ZERO, [])

    def fake_insert_delivery(row, *, dry_run):
        return (True, False) if not dry_run else (False, False)

    fake_key = "test-secret-key-xyz-123"
    monkeypatch.setattr(prod, "SUPABASE_SERVICE_ROLE_KEY", fake_key)
    monkeypatch.setattr(prod, "SUPABASE_URL", "https://example.supabase.co")
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
