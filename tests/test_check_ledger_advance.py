"""Tests for CSP-W6 forward-ledger heartbeat — scripts/check_ledger_advance.py.

Guards:
1. Advance is silent: when a ledger's asof advances and render happened, no
   stall is returned and no alert fires.
2. Stall + render = one ledger_stall alert: stalled list is non-empty and
   _dispatch_stall_alert fires push_ops_alert with type_=ledger_stall.
3. Stall without render = no stall row (no escalation without republish).
4. Weekend = skip: a non-trading day returns empty, no state mutation.
5. Double-run = no dup: same-calendar-day re-run does NOT produce a stall
   (idempotent per last_check_date guard).
6. Missing ledger file is silently skipped (no stall for absent files).
7. State is persisted and the next-run prev_asof reflects current-run curr_asof.
8. Multiple stalls in one run: all stalled ledgers returned; one combined alert.
9. Corrupt state file → fail-open, treated as empty.
10. push_ops_alert failure → fail-open, no crash.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts import check_ledger_advance as M

# ── shared datetimes ────────────────────────────────────────────────────────
# Use Thursdays/Fridays (guaranteed trading days; not near US holidays).
_D1 = datetime(2026, 7, 16, 22, 0, 0, tzinfo=timezone.utc)  # Thu, first run
_D2 = datetime(2026, 7, 17, 22, 0, 0, tzinfo=timezone.utc)  # Fri, second run

# Saturday (non-trading day)
_SAT = datetime(2026, 7, 19, 22, 0, 0, tzinfo=timezone.utc)


# ── helpers ────────────────────────────────────────────────────────────────

def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _write_state(state_path: Path, ledgers: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps({
            "schema": "ledger_heartbeat_state.v1",
            "updated_utc": None,
            "last_check_date": None,
            "ledgers": ledgers,
        }),
        encoding="utf-8",
    )


def _load_state(state_path: Path) -> dict:
    return json.loads(state_path.read_text(encoding="utf-8"))


class _Dispatch:
    """Records push_ops_alert calls."""
    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, *, source, type_, message, severity, lane, root):
        self.calls.append(dict(source=source, type_=type_, message=message,
                               severity=severity, lane=lane))


# ── Test 1: advance is silent ──────────────────────────────────────────────

def test_advance_silent(tmp_path):
    """When ledger advances and render happened, no stall and no alert."""
    ledger = tmp_path / "data" / "risk_radar" / "forward_log.jsonl"
    _write_jsonl(ledger, [
        {"asof": "2026-07-15", "state": "caution"},
        {"asof": "2026-07-16", "state": "caution"},
    ])
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    _write_state(state_path, {
        "data/risk_radar/forward_log.jsonl": {
            "asof": "2026-07-15",
            "last_check_date": "2026-07-16",
            "stalled_since": None,
        },
    })

    manifest = [{"path": "data/risk_radar/forward_log.jsonl", "label": "risk_radar"}]
    dispatch = _Dispatch()
    with (
        patch.object(M, "_LEDGER_MANIFEST", manifest),
        patch("engine.alert_triage.push_ops_alert", dispatch),
    ):
        stalled = M.run_check(
            root=tmp_path,
            state_path=state_path,
            render_happened=True,
            _now=_D2,
        )
        # Also verify the dispatch function doesn't fire
        M._dispatch_stall_alert(stalled, tmp_path)

    assert stalled == []
    assert dispatch.calls == []
    # State updated to new asof
    saved = _load_state(state_path)
    assert saved["ledgers"]["data/risk_radar/forward_log.jsonl"]["asof"] == "2026-07-16"


# ── Test 2: stall + render = alert fires ─────────────────────────────────

def test_stall_with_render(tmp_path):
    """Stall + render_happened=True → stall dict returned, push_ops_alert fires."""
    ledger = tmp_path / "data" / "risk_radar" / "forward_log.jsonl"
    _write_jsonl(ledger, [{"asof": "2026-07-15", "state": "caution"}])
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    _write_state(state_path, {
        "data/risk_radar/forward_log.jsonl": {
            "asof": "2026-07-15",
            "last_check_date": "2026-07-16",  # yesterday
            "stalled_since": None,
        },
    })

    manifest = [{"path": "data/risk_radar/forward_log.jsonl", "label": "risk_radar"}]
    dispatch = _Dispatch()
    with (
        patch.object(M, "_LEDGER_MANIFEST", manifest),
        patch("engine.alert_triage.push_ops_alert", dispatch),
    ):
        stalled = M.run_check(
            root=tmp_path,
            state_path=state_path,
            render_happened=True,
            _now=_D2,
        )
        M._dispatch_stall_alert(stalled, tmp_path)

    assert len(stalled) == 1
    s = stalled[0]
    assert s["label"] == "risk_radar"
    assert s["prev_asof"] == "2026-07-15"
    assert s["curr_asof"] == "2026-07-15"
    assert len(dispatch.calls) == 1
    assert dispatch.calls[0]["type_"] == "ledger_stall"
    assert dispatch.calls[0]["source"] == "ledger_heartbeat"


# ── Test 3: stall without render = no stall row ──────────────────────────

def test_stall_without_render(tmp_path):
    """Stall + render_happened=False → empty (no escalation without republish)."""
    ledger = tmp_path / "data" / "risk_radar" / "forward_log.jsonl"
    _write_jsonl(ledger, [{"asof": "2026-07-15", "state": "caution"}])
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    _write_state(state_path, {
        "data/risk_radar/forward_log.jsonl": {
            "asof": "2026-07-15",
            "last_check_date": "2026-07-16",
            "stalled_since": None,
        },
    })

    manifest = [{"path": "data/risk_radar/forward_log.jsonl", "label": "risk_radar"}]
    dispatch = _Dispatch()
    with (
        patch.object(M, "_LEDGER_MANIFEST", manifest),
        patch("engine.alert_triage.push_ops_alert", dispatch),
    ):
        stalled = M.run_check(
            root=tmp_path,
            state_path=state_path,
            render_happened=False,   # <-- no render
            _now=_D2,
        )
        M._dispatch_stall_alert(stalled, tmp_path)

    assert stalled == []
    assert dispatch.calls == []


# ── Test 4: weekend = skip ────────────────────────────────────────────────

def test_weekend_skip(tmp_path):
    """Non-trading day (Saturday) → empty, no state mutation."""
    ledger = tmp_path / "data" / "risk_radar" / "forward_log.jsonl"
    _write_jsonl(ledger, [{"asof": "2026-07-15", "state": "caution"}])
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    initial_ledgers = {
        "data/risk_radar/forward_log.jsonl": {
            "asof": "2026-07-15",
            "last_check_date": "2026-07-17",
            "stalled_since": None,
        },
    }
    _write_state(state_path, initial_ledgers)

    manifest = [{"path": "data/risk_radar/forward_log.jsonl", "label": "risk_radar"}]
    dispatch = _Dispatch()
    with (
        patch.object(M, "_LEDGER_MANIFEST", manifest),
        patch("engine.alert_triage.push_ops_alert", dispatch),
    ):
        stalled = M.run_check(
            root=tmp_path,
            state_path=state_path,
            render_happened=True,
            _now=_SAT,  # Saturday
        )

    assert stalled == []
    assert dispatch.calls == []
    # State file not mutated on non-trading day
    saved = _load_state(state_path)
    assert saved["ledgers"]["data/risk_radar/forward_log.jsonl"]["last_check_date"] == "2026-07-17"


# ── Test 5: double-run = no dup ──────────────────────────────────────────

def test_double_run_idempotent(tmp_path):
    """Same-day re-run does not produce a second stall (idempotent)."""
    ledger = tmp_path / "data" / "risk_radar" / "forward_log.jsonl"
    _write_jsonl(ledger, [{"asof": "2026-07-16", "state": "caution"}])
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    # Simulate state AFTER a first run today already recorded last_check_date=today
    _write_state(state_path, {
        "data/risk_radar/forward_log.jsonl": {
            "asof": "2026-07-16",
            "last_check_date": "2026-07-17",  # already ran today (_D2)
            "stalled_since": None,
        },
    })

    manifest = [{"path": "data/risk_radar/forward_log.jsonl", "label": "risk_radar"}]
    dispatch = _Dispatch()
    with (
        patch.object(M, "_LEDGER_MANIFEST", manifest),
        patch("engine.alert_triage.push_ops_alert", dispatch),
    ):
        stalled = M.run_check(
            root=tmp_path,
            state_path=state_path,
            render_happened=True,
            _now=_D2,  # 2026-07-17 — same day as last_check_date
        )
        M._dispatch_stall_alert(stalled, tmp_path)

    assert stalled == []
    assert dispatch.calls == []


# ── Test 6: missing ledger file is silently skipped ──────────────────────

def test_missing_ledger_skipped(tmp_path):
    """A ledger file that doesn't exist yet is silently skipped."""
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    _write_state(state_path, {})

    manifest = [{"path": "data/leadership_crack/forward_log.jsonl", "label": "leadership_crack"}]
    dispatch = _Dispatch()
    with (
        patch.object(M, "_LEDGER_MANIFEST", manifest),
        patch("engine.alert_triage.push_ops_alert", dispatch),
    ):
        stalled = M.run_check(
            root=tmp_path,
            state_path=state_path,
            render_happened=True,
            _now=_D2,
        )
        M._dispatch_stall_alert(stalled, tmp_path)

    assert stalled == []
    assert dispatch.calls == []
    # State updated but curr_asof is None (file absent)
    saved = _load_state(state_path)
    entry = saved["ledgers"].get("data/leadership_crack/forward_log.jsonl", {})
    assert entry.get("asof") is None


# ── Test 7: state persists for next run ──────────────────────────────────

def test_state_persists(tmp_path):
    """After a run, the saved state carries the current asof as the new prev_asof."""
    ledger = tmp_path / "data" / "market_state" / "forward_log.jsonl"
    _write_jsonl(ledger, [
        {"asof": "2026-07-14"},
        {"asof": "2026-07-15"},
        {"asof": "2026-07-16"},
    ])
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    _write_state(state_path, {})  # no prior state

    manifest = [{"path": "data/market_state/forward_log.jsonl", "label": "market_state"}]
    with patch.object(M, "_LEDGER_MANIFEST", manifest):
        M.run_check(
            root=tmp_path,
            state_path=state_path,
            render_happened=True,
            _now=_D1,
        )

    saved = _load_state(state_path)
    assert saved["ledgers"]["data/market_state/forward_log.jsonl"]["asof"] == "2026-07-16"
    assert saved["ledgers"]["data/market_state/forward_log.jsonl"]["last_check_date"] == "2026-07-16"


# ── Test 8: multiple stalls in one run ───────────────────────────────────

def test_multiple_stalls(tmp_path):
    """All stalled ledgers in one run are reported; dispatch_stall_alert fires once."""
    l1 = tmp_path / "data" / "risk_radar" / "forward_log.jsonl"
    l2 = tmp_path / "data" / "market_state" / "forward_log.jsonl"
    _write_jsonl(l1, [{"asof": "2026-07-15"}])
    _write_jsonl(l2, [{"asof": "2026-07-14"}])

    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    _write_state(state_path, {
        "data/risk_radar/forward_log.jsonl": {
            "asof": "2026-07-15",
            "last_check_date": "2026-07-16",
            "stalled_since": None,
        },
        "data/market_state/forward_log.jsonl": {
            "asof": "2026-07-14",
            "last_check_date": "2026-07-16",
            "stalled_since": None,
        },
    })

    manifest = [
        {"path": "data/risk_radar/forward_log.jsonl", "label": "risk_radar"},
        {"path": "data/market_state/forward_log.jsonl", "label": "market_state"},
    ]
    dispatch = _Dispatch()
    with (
        patch.object(M, "_LEDGER_MANIFEST", manifest),
        patch("engine.alert_triage.push_ops_alert", dispatch),
    ):
        stalled = M.run_check(
            root=tmp_path,
            state_path=state_path,
            render_happened=True,
            _now=_D2,
        )
        # Dispatch is called once with the combined stall list (mimics main())
        M._dispatch_stall_alert(stalled, tmp_path)

    assert len(stalled) == 2
    labels = {s["label"] for s in stalled}
    assert labels == {"risk_radar", "market_state"}
    # One combined alert dispatched
    assert len(dispatch.calls) == 1
    assert dispatch.calls[0]["type_"] == "ledger_stall"


# ── Test 9: corrupt state file → fail-open ──────────────────────────────

def test_corrupt_state_fail_open(tmp_path):
    """Corrupt state JSON → fail-open, treated as empty state."""
    ledger = tmp_path / "data" / "risk_radar" / "forward_log.jsonl"
    _write_jsonl(ledger, [{"asof": "2026-07-16"}])
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("{INVALID JSON{{")

    manifest = [{"path": "data/risk_radar/forward_log.jsonl", "label": "risk_radar"}]
    with patch.object(M, "_LEDGER_MANIFEST", manifest):
        stalled = M.run_check(
            root=tmp_path,
            state_path=state_path,
            render_happened=True,
            _now=_D2,
        )
    # No previous state → no stall (prev_asof is None → no comparison possible)
    assert stalled == []


# ── Test 10: push_ops_alert failure → fail-open ──────────────────────────

def test_push_ops_alert_failure_fail_open(tmp_path):
    """push_ops_alert raising an exception → script still exits 0 (fail-open)."""
    ledger = tmp_path / "data" / "risk_radar" / "forward_log.jsonl"
    _write_jsonl(ledger, [{"asof": "2026-07-15"}])
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    _write_state(state_path, {
        "data/risk_radar/forward_log.jsonl": {
            "asof": "2026-07-15",
            "last_check_date": "2026-07-16",
            "stalled_since": None,
        },
    })

    manifest = [{"path": "data/risk_radar/forward_log.jsonl", "label": "risk_radar"}]
    with (
        patch.object(M, "_LEDGER_MANIFEST", manifest),
        patch("engine.alert_triage.push_ops_alert", side_effect=RuntimeError("boom")),
    ):
        stalled = M.run_check(
            root=tmp_path,
            state_path=state_path,
            render_happened=True,
            _now=_D2,
        )
        # Should not raise
        M._dispatch_stall_alert(stalled, tmp_path)

    # Stall was detected even though alert dispatch failed
    assert len(stalled) == 1


# ── Test: stalled_since is preserved across consecutive stall days ────────

def test_stalled_since_preserved(tmp_path):
    """stalled_since is set on first stall and preserved on subsequent stall days."""
    ledger = tmp_path / "data" / "risk_radar" / "forward_log.jsonl"
    _write_jsonl(ledger, [{"asof": "2026-07-15"}])
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    _write_state(state_path, {
        "data/risk_radar/forward_log.jsonl": {
            "asof": "2026-07-15",
            "last_check_date": "2026-07-16",
            "stalled_since": "2026-07-16",  # was already stalled yesterday
        },
    })

    manifest = [{"path": "data/risk_radar/forward_log.jsonl", "label": "risk_radar"}]
    dispatch = _Dispatch()
    with (
        patch.object(M, "_LEDGER_MANIFEST", manifest),
        patch("engine.alert_triage.push_ops_alert", dispatch),
    ):
        stalled = M.run_check(
            root=tmp_path,
            state_path=state_path,
            render_happened=True,
            _now=_D2,
        )

    assert len(stalled) == 1
    assert stalled[0]["stalled_since"] == "2026-07-16"  # preserved, not overwritten

    saved = _load_state(state_path)
    assert saved["ledgers"]["data/risk_radar/forward_log.jsonl"]["stalled_since"] == "2026-07-16"


# ── Test: main() CLI always returns 0 ────────────────────────────────────

def test_main_always_exits_zero(tmp_path):
    """main() always returns 0 regardless of outcome (fail-open, CSP-R1)."""
    rc = M.main(["--root", str(tmp_path)])
    assert rc == 0


def test_main_with_render_happened(tmp_path):
    """--render-happened flag + stall condition triggers alert via main()."""
    ledger = tmp_path / "data" / "risk_radar" / "forward_log.jsonl"
    _write_jsonl(ledger, [{"asof": "2026-07-15"}])
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    _write_state(state_path, {
        "data/risk_radar/forward_log.jsonl": {
            "asof": "2026-07-15",
            "last_check_date": "2026-07-16",
            "stalled_since": None,
        },
    })

    manifest = [{"path": "data/risk_radar/forward_log.jsonl", "label": "risk_radar"}]
    dispatch = _Dispatch()
    with (
        patch.object(M, "_LEDGER_MANIFEST", manifest),
        patch("engine.alert_triage.push_ops_alert", dispatch),
        # Ensure the test date is treated as a trading day
        patch.object(M, "_is_trading_day", return_value=True),
    ):
        rc = M.main([
            "--root", str(tmp_path),
            "--state-file", str(state_path),
            "--render-happened",
        ])
    assert rc == 0
    # Alert should have fired for the stall
    assert len(dispatch.calls) == 1
    assert dispatch.calls[0]["type_"] == "ledger_stall"


# ── Test: _latest_asof supports 'date' field fallback ────────────────────

def test_latest_asof_date_field(tmp_path):
    """_latest_asof reads 'date' field when 'asof' is absent (mag7_regime schema)."""
    ledger = tmp_path / "ledger.jsonl"
    _write_jsonl(ledger, [
        {"date": "2026-07-15", "trend_state": "turning_up"},
        {"date": "2026-07-16", "trend_state": "running_narrow"},
    ])
    result = M._latest_asof(ledger)
    assert result == "2026-07-16"


def test_latest_asof_asof_field(tmp_path):
    """_latest_asof reads 'asof' field for risk_radar/market_state schema."""
    ledger = tmp_path / "forward_log.jsonl"
    _write_jsonl(ledger, [
        {"asof": "2026-07-14", "state": "caution"},
        {"asof": "2026-07-16", "state": "caution"},
        {"asof": "2026-07-15", "state": "caution"},  # out-of-order, but tail-scan handles it
    ])
    result = M._latest_asof(ledger)
    # Tail scan of last 20 rows; picks max within that window
    # All 3 rows are in the window; max is "2026-07-16"
    assert result == "2026-07-16"


def test_latest_asof_missing_file(tmp_path):
    """_latest_asof returns None when file does not exist."""
    result = M._latest_asof(tmp_path / "nonexistent.jsonl")
    assert result is None


# ── Stall-marker integrity (Grey Deer O7/T03, 2026-10-11) ────────────────
# Production replay: on 2026-10-08 the 15:05Z run recorded risk_radar and
# leadership_crack as stalled since 2026-10-07 (asof 2026-10-06), and the
# 16:17Z same-day rerun wrote stalled_since=None with the asof unchanged
# (state-file commits e65335239332^ -> e65335239332). A non-stall branch is
# not an advance: only a strictly newer asof may clear an open stall.

_RR = "data/risk_radar/forward_log.jsonl"
_RR_MANIFEST = [{"path": _RR, "label": "risk_radar"}]
_MON = datetime(2026, 7, 20, 22, 0, 0, tzinfo=timezone.utc)  # next session after _D2


def _run(tmp_path, state_path, *, now, render_happened=True):
    dispatch = _Dispatch()
    with (
        patch.object(M, "_LEDGER_MANIFEST", _RR_MANIFEST),
        patch("engine.alert_triage.push_ops_alert", dispatch),
    ):
        stalled = M.run_check(
            root=tmp_path,
            state_path=state_path,
            render_happened=render_happened,
            _now=now,
        )
        M._dispatch_stall_alert(stalled, tmp_path)
    return stalled, dispatch


def test_same_day_rerun_preserves_open_stall(tmp_path):
    """A same-day rerun with an unchanged ledger keeps the open stall marker."""
    _write_jsonl(tmp_path / _RR, [{"asof": "2026-07-15"}])
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    # State as written by today's first run: stall already open since yesterday.
    _write_state(state_path, {
        _RR: {"asof": "2026-07-15", "last_check_date": "2026-07-17",
              "stalled_since": "2026-07-16"},
    })

    stalled, dispatch = _run(tmp_path, state_path, now=_D2)

    assert stalled == []          # idempotent: no second alert today
    assert dispatch.calls == []
    entry = _load_state(state_path)["ledgers"][_RR]
    assert entry["asof"] == "2026-07-15"
    assert entry["stalled_since"] == "2026-07-16"   # not erased by the rerun

    # Next session, still unchanged: the stall keeps its original start date.
    stalled, _ = _run(tmp_path, state_path, now=_MON)
    assert len(stalled) == 1
    assert stalled[0]["stalled_since"] == "2026-07-16"


def test_same_day_rerun_with_changed_ledger_clears_stall(tmp_path):
    """Changed issuer data clears the stall, even on a same-day rerun."""
    _write_jsonl(tmp_path / _RR, [{"asof": "2026-07-15"}, {"asof": "2026-07-17"}])
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    _write_state(state_path, {
        _RR: {"asof": "2026-07-15", "last_check_date": "2026-07-17",
              "stalled_since": "2026-07-16"},
    })

    stalled, _ = _run(tmp_path, state_path, now=_D2)

    assert stalled == []
    entry = _load_state(state_path)["ledgers"][_RR]
    assert entry["asof"] == "2026-07-17"
    assert entry["stalled_since"] is None


def test_no_render_night_preserves_open_stall(tmp_path):
    """A night without a republish neither alerts nor clears an open stall."""
    _write_jsonl(tmp_path / _RR, [{"asof": "2026-07-15"}])
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    _write_state(state_path, {
        _RR: {"asof": "2026-07-15", "last_check_date": "2026-07-16",
              "stalled_since": "2026-07-16"},
    })

    stalled, _ = _run(tmp_path, state_path, now=_D2, render_happened=False)

    assert stalled == []
    assert _load_state(state_path)["ledgers"][_RR]["stalled_since"] == "2026-07-16"


def test_unreadable_ledger_keeps_snapshot_and_open_stall(tmp_path):
    """An unreadable ledger is not an advance: snapshot and stall marker survive."""
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    _write_state(state_path, {
        _RR: {"asof": "2026-07-15", "last_check_date": "2026-07-16",
              "stalled_since": "2026-07-16"},
    })
    # Ledger absent (the reader returns None, same as an unparseable file).
    stalled, _ = _run(tmp_path, state_path, now=_D2)

    assert stalled == []
    entry = _load_state(state_path)["ledgers"][_RR]
    assert entry["asof"] == "2026-07-15"
    assert entry["stalled_since"] == "2026-07-16"

    # The ledger reappears unchanged: the stall is still reported from its start.
    _write_jsonl(tmp_path / _RR, [{"asof": "2026-07-15"}])
    stalled, _ = _run(tmp_path, state_path, now=_MON)
    assert len(stalled) == 1
    assert stalled[0]["prev_asof"] == "2026-07-15"
    assert stalled[0]["stalled_since"] == "2026-07-16"


def test_regressed_asof_is_a_stall_and_rerun_keeps_marker(tmp_path):
    """An out-of-order (older) newest asof is a stall, never an advance.

    It alerts once, a same-day rerun does not alert again, and the open
    marker keeps its original start date through both runs.
    """
    _write_jsonl(tmp_path / _RR, [{"asof": "2026-07-15"}])
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    _write_state(state_path, {
        _RR: {"asof": "2026-07-16", "last_check_date": "2026-07-16",
              "stalled_since": "2026-07-16"},
    })

    stalled, dispatch = _run(tmp_path, state_path, now=_D2)
    assert len(stalled) == 1
    assert stalled[0]["curr_asof"] == "2026-07-15"
    assert stalled[0]["stalled_since"] == "2026-07-16"
    assert len(dispatch.calls) == 1
    assert _load_state(state_path)["ledgers"][_RR]["stalled_since"] == "2026-07-16"

    stalled, dispatch = _run(tmp_path, state_path, now=_D2)
    assert stalled == []
    assert dispatch.calls == []
    assert _load_state(state_path)["ledgers"][_RR]["stalled_since"] == "2026-07-16"


# ── Session lag against the expected NYSE session (Grey Deer W4 G-HB) ────
# Staleness for an opted-in ledger is the number of NYSE sessions in
# (ledger asof, last session on or before yesterday]. Synthetic rows and
# injected dates only. Ledgers without max_sessions_behind are untouched.

_LAG_REL = "data/risk_radar/forward_log.jsonl"


def _at(day: date, hour: int = 12) -> datetime:
    """Fixed UTC timestamp on `day` (12:00Z is morning in ET). No wall clock."""
    return datetime(day.year, day.month, day.day, hour, 0, tzinfo=timezone.utc)


def _run_manifest(tmp_path, state_path, manifest, *, now, render_happened=True):
    dispatch = _Dispatch()
    with (
        patch.object(M, "_LEDGER_MANIFEST", manifest),
        patch("engine.alert_triage.push_ops_alert", dispatch),
    ):
        stalled = M.run_check(
            root=tmp_path,
            state_path=state_path,
            render_happened=render_happened,
            _now=now,
        )
        M._dispatch_stall_alert(stalled, tmp_path)
    return stalled, dispatch


def test_friday_asof_is_current_on_weekend_and_monday_morning(tmp_path):
    """A Friday asof is 0 sessions behind on Sat, Sun, and Monday morning."""
    friday = date(2026, 7, 17)
    saturday = date(2026, 7, 18)
    sunday = date(2026, 7, 19)
    monday = date(2026, 7, 20)
    for today in (saturday, sunday, monday):
        assert M._expected_session(today) == friday
        assert M._sessions_behind(friday, today) == 0

    manifest = [{"path": _LAG_REL, "label": "risk_radar", "max_sessions_behind": 0}]
    _write_jsonl(tmp_path / _LAG_REL, [{"asof": "2026-07-17"}])
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    # Thursday snapshot: the Friday row is an advance, so no_advance stays quiet.
    _write_state(state_path, {
        _LAG_REL: {"asof": "2026-07-16", "last_check_date": "2026-07-17",
                   "stalled_since": None},
    })
    before = state_path.read_text(encoding="utf-8")

    for day in (saturday, sunday):
        stalled, dispatch = _run_manifest(
            tmp_path, state_path, manifest, now=_at(day),
        )
        assert stalled == []
        assert dispatch.calls == []
        assert state_path.read_text(encoding="utf-8") == before

    stalled, dispatch = _run_manifest(
        tmp_path, state_path, manifest, now=_at(monday),
    )
    assert stalled == []
    assert dispatch.calls == []
    entry = _load_state(state_path)["ledgers"][_LAG_REL]
    assert entry["asof"] == "2026-07-17"
    assert entry["sessions_behind"] == 0
    assert entry["expected_session"] == "2026-07-17"
    assert entry["lag_stalled_since"] is None


def test_expected_session_is_yesterday_even_after_the_close(tmp_path):
    """The ceiling is last session on or before yesterday, including after the close.

    Friday 22:00Z is 18:00 ET, after the cash close. A Thursday asof is still
    current: today's own session is not yet required.
    """
    friday = date(2026, 7, 17)
    assert M._expected_session(friday) == date(2026, 7, 16)
    assert M._sessions_behind(date(2026, 7, 16), friday) == 0

    manifest = [{"path": _LAG_REL, "label": "risk_radar", "max_sessions_behind": 0}]
    _write_jsonl(tmp_path / _LAG_REL, [{"asof": "2026-07-16"}])
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    _write_state(state_path, {
        _LAG_REL: {"asof": "2026-07-15", "last_check_date": "2026-07-16",
                   "stalled_since": None},
    })
    stalled, dispatch = _run_manifest(
        tmp_path, state_path, manifest,
        now=datetime(2026, 7, 17, 22, 0, tzinfo=timezone.utc),
    )
    assert stalled == []
    assert dispatch.calls == []
    entry = _load_state(state_path)["ledgers"][_LAG_REL]
    assert entry["expected_session"] == "2026-07-16"
    assert entry["sessions_behind"] == 0
    assert entry["lag_stalled_since"] is None


def test_labor_day_monday_is_not_counted(tmp_path):
    """2026-09-07 Labor Day is not an NYSE session and does not add lag.

    Thursday 2026-09-03 checked on Tuesday 2026-09-08 is one session behind
    (Friday 09-04 only). Counting the holiday Monday would make it two.
    A Friday 09-04 asof is current across that weekend.
    """
    assert M._expected_session(date(2026, 9, 8)) == date(2026, 9, 4)
    assert M._sessions_behind(date(2026, 9, 3), date(2026, 9, 8)) == 1
    assert M._sessions_behind(date(2026, 9, 4), date(2026, 9, 8)) == 0

    manifest = [{"path": _LAG_REL, "label": "risk_radar", "max_sessions_behind": 0}]
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    tuesday = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)

    _write_jsonl(tmp_path / _LAG_REL, [{"asof": "2026-09-03"}])
    _write_state(state_path, {
        _LAG_REL: {"asof": "2026-09-02", "last_check_date": "2026-09-04",
                   "stalled_since": None},
    })
    stalled, dispatch = _run_manifest(
        tmp_path, state_path, manifest, now=tuesday,
    )
    assert len(stalled) == 1
    assert stalled[0]["stall_reason"] == "session_lag"
    assert stalled[0]["stall_reasons"] == ["session_lag"]
    assert stalled[0]["sessions_behind"] == 1
    assert stalled[0]["expected_session"] == "2026-09-04"
    assert len(dispatch.calls) == 1

    _write_jsonl(tmp_path / _LAG_REL, [{"asof": "2026-09-04"}])
    _write_state(state_path, {
        _LAG_REL: {"asof": "2026-09-03", "last_check_date": "2026-09-04",
                   "stalled_since": None},
    })
    stalled, dispatch = _run_manifest(
        tmp_path, state_path, manifest, now=tuesday,
    )
    assert stalled == []
    assert dispatch.calls == []
    entry = _load_state(state_path)["ledgers"][_LAG_REL]
    assert entry["sessions_behind"] == 0
    assert entry["expected_session"] == "2026-09-04"
    assert entry["lag_stalled_since"] is None


def test_three_sessions_behind_max_two_is_session_lag(tmp_path):
    """An asof that advanced once and is still 3 sessions behind a max of 2 lags.

    Checked Friday 2026-07-17, Monday 2026-07-13 is short of Thursday 2026-07-16
    by Tue/Wed/Thu. A later one-session advance that is still over the ceiling
    keeps the original lag_stalled_since.
    """
    assert M._sessions_behind(date(2026, 7, 13), date(2026, 7, 17)) == 3
    manifest = [{"path": _LAG_REL, "label": "risk_radar", "max_sessions_behind": 2}]
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    _write_jsonl(tmp_path / _LAG_REL, [{"asof": "2026-07-13"}])
    _write_state(state_path, {
        _LAG_REL: {"asof": "2026-07-10", "last_check_date": "2026-07-16",
                   "stalled_since": None},
    })
    friday = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)
    stalled, dispatch = _run_manifest(
        tmp_path, state_path, manifest, now=friday,
    )
    assert len(stalled) == 1
    assert stalled[0]["stall_reason"] == "session_lag"
    assert stalled[0]["stall_reasons"] == ["session_lag"]
    assert stalled[0]["sessions_behind"] == 3
    assert stalled[0]["expected_session"] == "2026-07-16"
    assert stalled[0]["lag_stalled_since"] == "2026-07-17"
    assert stalled[0]["stalled_since"] is None
    assert len(dispatch.calls) == 1
    assert dispatch.calls[0]["type_"] == "ledger_stall"
    assert "session_lag" in dispatch.calls[0]["message"]
    entry = _load_state(state_path)["ledgers"][_LAG_REL]
    assert entry["lag_stalled_since"] == "2026-07-17"
    assert entry["sessions_behind"] == 3

    # One session newer, still 3 behind on Monday morning. Same lag episode.
    _write_jsonl(tmp_path / _LAG_REL, [{"asof": "2026-07-14"}])
    assert M._sessions_behind(date(2026, 7, 14), date(2026, 7, 20)) == 3
    stalled, dispatch = _run_manifest(
        tmp_path, state_path, manifest, now=_at(date(2026, 7, 20)),
    )
    assert len(stalled) == 1
    assert stalled[0]["stall_reasons"] == ["session_lag"]
    assert stalled[0]["sessions_behind"] == 3
    assert stalled[0]["lag_stalled_since"] == "2026-07-17"
    assert _load_state(state_path)["ledgers"][_LAG_REL]["lag_stalled_since"] == "2026-07-17"
    assert len(dispatch.calls) == 1


def test_sessions_behind_equal_to_the_ceiling_is_not_a_lag(tmp_path):
    """sessions_behind must be strictly greater than max_sessions_behind."""
    assert M._sessions_behind(date(2026, 7, 14), date(2026, 7, 17)) == 2
    manifest = [{"path": _LAG_REL, "label": "risk_radar", "max_sessions_behind": 2}]
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    _write_jsonl(tmp_path / _LAG_REL, [{"asof": "2026-07-14"}])
    _write_state(state_path, {
        _LAG_REL: {"asof": "2026-07-13", "last_check_date": "2026-07-16",
                   "stalled_since": None},
    })
    stalled, dispatch = _run_manifest(
        tmp_path, state_path, manifest,
        now=datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc),
    )
    assert stalled == []
    assert dispatch.calls == []
    entry = _load_state(state_path)["ledgers"][_LAG_REL]
    assert entry["sessions_behind"] == 2
    assert entry["lag_stalled_since"] is None


def test_lag_stalled_since_clears_only_on_strictly_newer_asof(tmp_path):
    """An open lag marker clears only when a strictly newer asof is within the ceiling.

    Same-day rerun, a no-render night, an unreadable ledger, and an asof that
    has not moved all keep the marker — including when the calendar lag has
    already fallen to zero. A strictly newer asof inside the ceiling clears it.
    """
    manifest = [{"path": _LAG_REL, "label": "risk_radar", "max_sessions_behind": 2}]
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    _write_jsonl(tmp_path / _LAG_REL, [{"asof": "2026-07-17"}])
    _write_state(state_path, {
        _LAG_REL: {
            "asof": "2026-07-17",
            "last_check_date": "2026-07-17",
            "stalled_since": None,
            "lag_stalled_since": "2026-07-10",
        },
    })
    monday = _at(date(2026, 7, 20))

    stalled, _dispatch = _run_manifest(
        tmp_path, state_path, manifest, now=monday,
    )
    # 0 sessions behind, so this is not a session_lag. The asof did not move,
    # so the open lag marker stays. The unchanged asof is still a no_advance.
    assert M._sessions_behind(date(2026, 7, 17), date(2026, 7, 20)) == 0
    assert len(stalled) == 1
    assert stalled[0]["stall_reasons"] == ["no_advance"]
    assert _load_state(state_path)["ledgers"][_LAG_REL]["lag_stalled_since"] == "2026-07-10"

    stalled, dispatch = _run_manifest(
        tmp_path, state_path, manifest, now=monday,
    )
    assert stalled == []
    assert dispatch.calls == []
    assert _load_state(state_path)["ledgers"][_LAG_REL]["lag_stalled_since"] == "2026-07-10"

    stalled, dispatch = _run_manifest(
        tmp_path, state_path, manifest, now=_at(date(2026, 7, 21)),
        render_happened=False,
    )
    assert stalled == []
    assert dispatch.calls == []
    assert _load_state(state_path)["ledgers"][_LAG_REL]["lag_stalled_since"] == "2026-07-10"
    assert _load_state(state_path)["ledgers"][_LAG_REL]["asof"] == "2026-07-17"

    # Friday 07-24 would be 4 sessions behind the Friday 07-17 snapshot.
    # The file is unreadable, so that must not open a session_lag alert
    # and must not clear the marker or the last good asof.
    (tmp_path / _LAG_REL).unlink()
    assert M._sessions_behind(date(2026, 7, 17), date(2026, 7, 24)) == 4
    stalled, dispatch = _run_manifest(
        tmp_path, state_path, manifest, now=_at(date(2026, 7, 24)),
    )
    assert stalled == []
    assert dispatch.calls == []
    entry = _load_state(state_path)["ledgers"][_LAG_REL]
    assert entry["asof"] == "2026-07-17"
    assert entry["lag_stalled_since"] == "2026-07-10"

    _write_jsonl(tmp_path / _LAG_REL, [{"asof": "2026-07-23"}])
    assert M._sessions_behind(date(2026, 7, 23), date(2026, 7, 27)) == 1
    stalled, dispatch = _run_manifest(
        tmp_path, state_path, manifest, now=_at(date(2026, 7, 27)),
    )
    assert stalled == []
    assert dispatch.calls == []
    entry = _load_state(state_path)["ledgers"][_LAG_REL]
    assert entry["asof"] == "2026-07-23"
    assert entry["sessions_behind"] == 1
    assert entry["lag_stalled_since"] is None


def test_legacy_ledger_without_max_sessions_behind_is_unchanged(tmp_path):
    """No max_sessions_behind key: same decisions and the same state keys as before.

    Three sessions behind but advanced once stays silent. An unchanged asof is
    still a single no_advance stall, with no session_lag field and no lag marker.
    """
    rel = "data/market_state/forward_log.jsonl"
    manifest = [{"path": rel, "label": "market_state"}]
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    friday = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)
    _write_jsonl(tmp_path / rel, [{"asof": "2026-07-13"}])

    _write_state(state_path, {
        rel: {"asof": "2026-07-10", "last_check_date": "2026-07-16",
              "stalled_since": None},
    })
    stalled, dispatch = _run_manifest(
        tmp_path, state_path, manifest, now=friday,
    )
    assert stalled == []
    assert dispatch.calls == []
    entry = _load_state(state_path)["ledgers"][rel]
    assert set(entry) == {"asof", "last_check_date", "stalled_since"}
    assert entry["asof"] == "2026-07-13"
    assert entry["stalled_since"] is None

    _write_state(state_path, {
        rel: {"asof": "2026-07-13", "last_check_date": "2026-07-16",
              "stalled_since": None},
    })
    stalled, dispatch = _run_manifest(
        tmp_path, state_path, manifest, now=friday,
    )
    assert len(stalled) == 1
    assert stalled[0]["stall_reason"] == "no_advance"
    assert stalled[0]["stall_reasons"] == ["no_advance"]
    assert "session_lag" not in stalled[0]["stall_reasons"]
    assert "sessions_behind" not in stalled[0]
    assert "lag_stalled_since" not in stalled[0]
    assert len(dispatch.calls) == 1
    assert "session_lag" not in dispatch.calls[0]["message"]
    entry = _load_state(state_path)["ledgers"][rel]
    assert set(entry) == {"asof", "last_check_date", "stalled_since"}
    assert entry["stalled_since"] == "2026-07-16"


def test_no_advance_and_session_lag_are_one_alert(tmp_path, capsys):
    """Both reasons for one ledger are one stall row and one ops alert per day."""
    manifest = [{"path": _LAG_REL, "label": "risk_radar", "max_sessions_behind": 2}]
    state_path = tmp_path / "data" / "ci" / "ledger_heartbeat_state.json"
    _write_jsonl(tmp_path / _LAG_REL, [{"asof": "2026-07-13"}])
    _write_state(state_path, {
        _LAG_REL: {"asof": "2026-07-13", "last_check_date": "2026-07-16",
                   "stalled_since": None},
    })
    friday = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)
    stalled, dispatch = _run_manifest(
        tmp_path, state_path, manifest, now=friday,
    )
    assert len(stalled) == 1
    assert stalled[0]["stall_reasons"] == ["no_advance", "session_lag"]
    assert stalled[0]["stall_reason"] == "no_advance,session_lag"
    assert stalled[0]["sessions_behind"] == 3
    assert stalled[0]["stalled_since"] == "2026-07-16"
    assert stalled[0]["lag_stalled_since"] == "2026-07-17"
    assert len(dispatch.calls) == 1
    message = dispatch.calls[0]["message"]
    assert message.count("stall_reason=") == 1
    assert "no_advance" in message and "session_lag" in message
    assert dispatch.calls[0]["type_"] == "ledger_stall"

    M._emit_warning_annotation(stalled)
    notes = capsys.readouterr().out
    assert notes.count("::warning ") == 1
    assert "no_advance" in notes and "session_lag" in notes

    entry = _load_state(state_path)["ledgers"][_LAG_REL]
    assert entry["stalled_since"] == "2026-07-16"
    assert entry["lag_stalled_since"] == "2026-07-17"

    stalled, dispatch = _run_manifest(
        tmp_path, state_path, manifest, now=friday,
    )
    assert stalled == []
    assert dispatch.calls == []
    assert _load_state(state_path)["ledgers"][_LAG_REL]["lag_stalled_since"] == "2026-07-17"


def test_risk_radar_and_leadership_crack_opt_in_at_two_sessions():
    """risk_radar and leadership_crack use a 2-session ceiling; nothing else does."""
    by_label = {entry["label"]: entry for entry in M._LEDGER_MANIFEST}
    assert by_label["risk_radar"]["max_sessions_behind"] == 2
    assert by_label["leadership_crack"]["max_sessions_behind"] == 2
    for entry in M._LEDGER_MANIFEST:
        if entry["label"] not in ("risk_radar", "leadership_crack"):
            assert "max_sessions_behind" not in entry
