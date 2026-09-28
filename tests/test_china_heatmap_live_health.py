from __future__ import annotations

import copy
from datetime import datetime, timezone

from scripts.check_vps_live_health import evaluate


ACTIVE_NOW = datetime(2026, 9, 28, 2, 15, 40, tzinfo=timezone.utc)


def _base_status() -> dict:
    return {
        "status": "ok",
        "checks": {
            "quotes": {"age_min": 1, "requested": 25, "resolved": 20},
            "release_publications": {"age_min": 1},
            "orchestrator": {
                "age_min": 1,
                "lanes": {
                    "fast": {"ok": True, "age_min": 1},
                    "snapshot": {"ok": True, "age_min": 4},
                },
            },
            "basket_pulse": {"age_min": 4},
            "china_risk_state": {"age_min": 2},
            "china_heatmap_live": _healthy_check(),
        },
    }


def _healthy_check() -> dict:
    requested = 1702
    resolved = 1690
    adv, dec, flat = 1000, 650, 40
    return {
        "schema": "china_heatmap_live.v1",
        "age_min": 0.1,
        "market": "china",
        "map_type": "stocks",
        "artifact_status": "live",
        "generated_at": "2026-09-28T02:15:30+00:00",
        "heartbeat_age_sec": 10.0,
        "baseline_asof": "2026-09-24",
        "served_baseline_asof": "2026-09-24",
        "baseline_ok": True,
        "session_date": "2026-09-28",
        "phase": "morning",
        "expected_phase": "morning",
        "phase_ok": True,
        "source": "tushare-rt-k",
        "source_observed_at": "2026-09-28T02:15:30+00:00",
        "source_lag_sec": 10.0,
        "requested": requested,
        "resolved": resolved,
        "quotes_count": resolved,
        "coverage": resolved / requested,
        "usable": True,
        "fallback": False,
        "breadth_n": resolved,
        "breadth_adv": adv,
        "breadth_dec": dec,
        "breadth_flat": flat,
        "breadth_pct_up": 100 * adv / resolved,
    }


def _failures(check: dict, *, now: datetime = ACTIVE_NOW) -> list[str]:
    payload = _base_status()
    payload["checks"]["china_heatmap_live"] = check
    return evaluate(payload, now=now)


def test_active_session_healthy_overlay_passes() -> None:
    assert _failures(_healthy_check()) == []


def test_active_session_missing_overlay_fails_visible() -> None:
    check = {"status": "missing", "expected_phase": "morning"}
    failures = _failures(check)
    assert any("china_heatmap_live: artifact missing during morning" in f for f in failures)


def test_active_session_stale_heartbeat_fails() -> None:
    check = _healthy_check()
    check["heartbeat_age_sec"] = 121.0
    failures = _failures(check)
    assert any("producer heartbeat stale" in f for f in failures)


def test_active_session_low_coverage_and_unusable_fail() -> None:
    check = _healthy_check()
    check.update(resolved=1531, quotes_count=1531, coverage=1531 / 1702, usable=False)
    check.update(breadth_n=1531, breadth_adv=900, breadth_dec=600, breadth_flat=31,
                 breadth_pct_up=100 * 900 / 1531)
    failures = _failures(check)
    assert any("coverage low" in f for f in failures)
    assert any("not usable during morning" in f for f in failures)


def test_active_session_source_clock_lag_fails() -> None:
    check = _healthy_check()
    check["source_lag_sec"] = 46.0
    failures = _failures(check)
    assert any("source clock lag" in f for f in failures)


def test_wrong_daily_baseline_fails() -> None:
    check = _healthy_check()
    check.update(baseline_asof="2026-09-23", baseline_ok=False)
    failures = _failures(check)
    assert any("daily baseline mismatch" in f for f in failures)


def test_lunch_break_accepts_fresh_heartbeat_and_fixed_1130_source() -> None:
    check = _healthy_check()
    check.update(
        artifact_status="break",
        generated_at="2026-09-28T04:00:00+00:00",
        heartbeat_age_sec=0.0,
        phase="session_break",
        expected_phase="session_break",
        source_observed_at="2026-09-28T03:29:50+00:00",
        source_lag_sec=10.0,
    )
    now = datetime(2026, 9, 28, 4, 0, tzinfo=timezone.utc)
    assert _failures(check, now=now) == []


def test_closed_phase_accepts_final_source_clock() -> None:
    check = _healthy_check()
    check.update(
        artifact_status="closed",
        generated_at="2026-09-28T08:00:00+00:00",
        heartbeat_age_sec=0.0,
        phase="closed",
        expected_phase="closed",
        source_observed_at="2026-09-28T07:00:00+00:00",
        source_lag_sec=0.0,
    )
    now = datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc)
    assert _failures(check, now=now) == []


def test_missing_artifact_outside_session_is_ok() -> None:
    payload = _base_status()
    payload["checks"]["china_heatmap_live"] = {
        "status": "missing", "expected_phase": "weekend",
    }
    now = datetime(2026, 10, 3, 2, 15, tzinfo=timezone.utc)
    assert evaluate(payload, now=now) == []


def test_malformed_present_artifact_fails_even_outside_session() -> None:
    payload = _base_status()
    payload["checks"]["china_heatmap_live"] = {
        "error": "unavailable", "expected_phase": "weekend", "age_min": 1,
    }
    now = datetime(2026, 10, 3, 2, 15, tzinfo=timezone.utc)
    failures = evaluate(payload, now=now)
    assert any("artifact unreadable" in f for f in failures)


def test_phase_mismatch_fails() -> None:
    check = _healthy_check()
    check.update(phase="session_break", phase_ok=False)
    failures = _failures(check)
    assert any("phase mismatch" in f for f in failures)


def test_accounting_mismatch_fails_closed() -> None:
    check = copy.deepcopy(_healthy_check())
    check["quotes_count"] -= 1
    check["breadth_adv"] += 1
    failures = _failures(check)
    assert any("quote accounting mismatch" in f for f in failures)
    assert any("breadth accounting mismatch" in f for f in failures)


def test_live_heatmap_suites_have_one_executable_ci_owner() -> None:
    from pathlib import Path
    import yaml
    manifest = Path(__file__).resolve().parents[1] / ".github/ci/legacy-jobs.yml"
    jobs = yaml.safe_load(manifest.read_text())["jobs"]
    suites = (
        "tests/test_china_heatmap_live.py",
        "tests/test_china_heatmap_live_producer.py",
        "tests/test_china_heatmap_live_deploy.py",
        "tests/test_china_heatmap_live_health.py",
        "tests/test_china_heatmap_live_refresh.cjs",
        "tests/test_china_heatmap_live_render.cjs",
    )
    for suite in suites:
        owners = [name for name, job in jobs.items()
                  if any(suite in step.get("run", "") for step in job.get("steps", []))]
        assert owners == ["china-board-breadth"], (suite, owners)
    job = jobs["china-board-breadth"]
    assert job["gate"] == "code"
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    assert "node --test" in commands
    assert "HEATMAP_SOURCE=site/heatmap.js" in commands
    assert "REFRESH_SOURCE=site/heatmap.js" in commands


def test_status_projection_is_testable_without_importing_the_api() -> None:
    from app.china_heatmap_status import status_projection
    assert callable(status_projection)


def test_china_heatmap_status_projection_is_phase_aware_and_private_safe(monkeypatch):
    import json as _json
    from app.china_heatmap_status import status_projection
    from engine.prophet_live import cn_clock

    now = datetime(2026, 9, 28, 2, 15, 40, tzinfo=timezone.utc)
    expected = datetime(2026, 9, 28, 2, 15, 40, tzinfo=timezone.utc)
    monkeypatch.setattr(cn_clock, "phase", lambda value=None: "morning")
    monkeypatch.setattr(cn_clock, "expected_latest_quote_time", lambda value=None: expected)
    ts = int(datetime(2026, 9, 28, 2, 15, 30, tzinfo=timezone.utc).timestamp() * 1000)
    payload = {
        "schema": "china_heatmap_live.v1", "market": "china", "map_type": "stocks",
        "baseline_asof": "2026-09-24", "session_date": "2026-09-28",
        "phase": "morning", "status": "live", "source": "tushare-rt-k",
        "generated_at": "2026-09-28T02:15:30+00:00",
        "source_observed_at": "2026-09-28T02:15:30+00:00",
        "requested": 2, "resolved": 2, "coverage": 1.0,
        "usable": True, "fallback": False,
        "quotes": {
            "600519.SS": {"price": 1412.8, "prevClose": 1398.0, "changePct": 1.0, "ts": ts},
            "000001.SZ": {"price": 11.1, "prevClose": 11.2, "changePct": -0.9, "ts": ts - 1000},
        },
        "breadth": {"n": 2, "adv": 1, "dec": 1, "flat": 0, "pctUp": 50.0},
    }
    projected = status_projection(
        payload, now=now, age_min=0.1, served_baseline_asof="2026-09-24",
    )
    assert projected["expected_phase"] == projected["phase"] == "morning"
    assert projected["phase_ok"] is True
    assert projected["heartbeat_age_sec"] == 10.0
    assert projected["source_lag_sec"] == 10.0
    assert projected["baseline_ok"] is True
    assert projected["quotes_count"] == projected["resolved"] == 2
    assert projected["breadth_n"] == 2
    encoded = _json.dumps(projected)
    assert "600519.SS" not in encoded and "000001.SZ" not in encoded
    assert "quotes" not in projected


def test_china_heatmap_missing_status_still_projects_the_session_law(monkeypatch):
    from app.china_heatmap_status import status_projection
    from engine.prophet_live import cn_clock

    now = datetime(2026, 10, 3, 2, 15, tzinfo=timezone.utc)
    monkeypatch.setattr(cn_clock, "phase", lambda value=None: "weekend")
    projected = status_projection(
        None, now=now, age_min=None, served_baseline_asof="2026-09-24",
    )
    assert projected == {
        "status": "missing",
        "expected_phase": "weekend",
        "served_baseline_asof": "2026-09-24",
        "source_required": False,
    }


def test_served_browser_ci_uses_the_actual_harness_environment_keys() -> None:
    from pathlib import Path
    import yaml
    root = Path(__file__).resolve().parents[1]
    job = yaml.safe_load((root / ".github/ci/legacy-jobs.yml").read_text())["jobs"]["china-board-breadth"]
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    assert "LIVE_REFRESH_SOURCE=site/heatmap.js" in commands
    assert "LIVE_RENDER_SOURCE=site/heatmap.js" in commands




def _idle_unavailable(phase: str) -> dict:
    check = _healthy_check()
    check.update(phase=phase, expected_phase=phase, artifact_status="unavailable",
                 source=None, source_observed_at=None, source_lag_sec=None,
                 usable=False, resolved=0, quotes_count=0, coverage=0.0,
                 breadth_n=0, breadth_adv=0, breadth_dec=0, breadth_flat=0, breadth_pct_up=0.0,
                 source_required=False)
    return check


def test_weekend_unavailable_is_an_honest_idle_state_not_an_outage() -> None:
    assert _failures(_idle_unavailable("weekend"),
                     now=datetime(2026, 10, 3, 2, 15, tzinfo=timezone.utc)) == []


def test_closed_before_open_does_not_require_a_current_session_quote() -> None:
    assert _failures(_idle_unavailable("closed"),
                     now=datetime(2026, 9, 28, 0, 15, tzinfo=timezone.utc)) == []


def test_settled_daily_baseline_makes_closed_live_overlay_optional() -> None:
    check = _idle_unavailable("closed")
    check.update(baseline_asof="2026-09-28", served_baseline_asof="2026-09-28")
    assert _failures(check, now=datetime(2026, 9, 28, 10, 0, tzinfo=timezone.utc)) == []
