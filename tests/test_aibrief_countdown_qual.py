"""Regression for the AI Brief server-rendered forecast countdown.

The committed producer's days_to is intentionally stale; the published page
must recompute from the render date without touching model/asof data.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from scripts.build_aibrief import _gather_forward_panel

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def bounded_calendars(monkeypatch):
    from engine import event_calendar, rebalance_calendar

    monkeypatch.setattr(event_calendar, "high_impact_strip", lambda **kwargs: [])
    monkeypatch.setattr(rebalance_calendar, "tag", lambda today: {"td_to_quarter_end": 999})


@pytest.mark.parametrize(
    ("render_day", "expected_en", "expected_zh"),
    [
        (date(2026, 10, 25), "In 4 days", "距今 4 天"),
        (date(2026, 10, 29), "Today", "今天"),
        (date(2026, 10, 30), None, None),
    ],
)
def test_committed_pce_countdown_and_asof_unchanged(render_day, expected_en, expected_zh):
    source = ROOT / "data" / "release_forecast" / "latest.json"
    before = source.read_bytes()
    producer = json.loads(before)
    assert producer["asof"] == "2026-10-16T18:18:59Z"
    assert any(e.get("release") == "pce" and e.get("days_to") == 13 for e in producer["upcoming"])

    panel = _gather_forward_panel(ROOT / "data", today=render_day)
    pce = [e for e in panel["events"] if e.get("is_forecast")
           and e.get("label_en") == "PCE" and e["date"] == "2026-10-29"]
    if expected_en is None:
        assert not pce
    else:
        assert len(pce) == 1  # preserve headline/core deduplication
        assert expected_en in pce[0]["tip_en"]
        assert expected_zh in pce[0]["tip_zh"]
        assert "13 day" not in pce[0]["tip_en"]
        assert "13 天" not in pce[0]["tip_zh"]
    assert source.read_bytes() == before


def test_bad_missing_past_and_claims_rows_are_suppressed(tmp_path):
    rf = tmp_path / "release_forecast"
    rf.mkdir()
    rows = [
        None,
        {"release": "bad", "release_date": None, "days_to": 77},
        {"release": "bad", "release_date": ["2026-10-29"], "days_to": 77},
        {"release": "bad", "release_date": "not-a-date", "days_to": 77},
        {"release": "bad", "release_date": "2026-02-30", "days_to": 77},
        {"release": "bad", "release_date": "20261029", "days_to": 77},
        {"release": "bad", "days_to": 77},
        {"release": "claims", "release_date": "2026-10-30", "days_to": 1},
        {"release": "nfp", "release_date": "2026-10-28", "days_to": 99},
        {"release": "pce", "release_type": "headline", "release_date": "2026-10-29", "days_to": 13},
        {"release": "pce", "release_type": "core", "release_date": "2026-10-29", "days_to": 13},
        {"release": "cpi", "date": "2026-11-01", "days_to": 999},
    ]
    (rf / "latest.json").write_text(json.dumps({"asof": "2026-10-16T18:18:59Z", "upcoming": rows}))
    panel = _gather_forward_panel(tmp_path, today=date(2026, 10, 29))
    forecast = [e for e in panel["events"] if e.get("is_forecast")]
    assert [(e["label_en"], e["date"]) for e in forecast] == [
        ("PCE", "2026-10-29"), ("CPI", "2026-11-01")
    ]
    assert "Today" in forecast[0]["tip_en"]
    assert "今天" in forecast[0]["tip_zh"]
    assert "In 3 days" in forecast[1]["tip_en"]
    assert "距今 3 天" in forecast[1]["tip_zh"]


def test_unusable_dates_do_not_fabricate_timing_or_crash(tmp_path):
    rf = tmp_path / "release_forecast"
    rf.mkdir()
    (rf / "latest.json").write_text(json.dumps({
        "upcoming": [
            {"release": "pce", "release_date": ""},
            {"release": "cpi", "release_date": "2026-13-15", "days_to": 1},
            {"release": "nfp", "release_date": False, "days_to": 3},
        ]
    }))
    panel = _gather_forward_panel(tmp_path, today=date(2026, 10, 29))
    assert not [e for e in panel["events"] if e.get("is_forecast")]
    assert panel["absent"] is True
