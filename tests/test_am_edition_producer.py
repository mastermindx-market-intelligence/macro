"""Contract tests for scripts/build_am_edition.py (packet A-MO-W2-3).

All tests drive build_payload() against tmp_path fixture trees with a frozen
`now` — none touch the network, none require the real data/ or site/ trees,
so this file is safe in a sparse worktree and needs no needs_full_checkout
marker.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from lib import nyse_calendar
from scripts.build_am_edition import (
    STATES,
    CLASSIFICATIONS,
    build_payload,
    _humanize_age,
    _is_session_open_now,
    _session_phase,
)

FORBIDDEN_KEYS = {
    "score", "rank", "signal", "gate", "size", "sizing", "ENTRY_OPEN",
    "prophet", "conviction", "buy", "sell", "target",
    "projection", "confidence", "surprise_skew", "surprise_distribution",
    "reaction_sensitivity", "market_implied", "inputs_hash", "model_epoch",
}


def _write(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj), encoding="utf-8")


def _fresh_tree(tmp_path: Path, *, tape_asof: str, session_date: str) -> tuple[Path, Path]:
    site = tmp_path / "site"
    data = tmp_path / "data"
    _write(site / "live" / "quotes.json", {
        "ts": 1, "asof": tape_asof, "source": "yahoo",
        "quotes": {
            "SPY": {"price": 740.0, "prevClose": 739.0, "changePct": 0.14, "basis": "regular"},
        },
        "meta": {},
    })
    _write(data / "market_state" / "latest.json", {
        "asof": session_date, "label_en": "Risk-on", "label_zh": "风险偏好",
        "posture_en": "Constructive", "posture_zh": "积极", "headline_en": "x", "headline_zh": "x",
    })
    _write(data / "regime" / "latest.json", {
        "asof": session_date, "quad_name": "Reflation", "label": "Q2",
    })
    _write(data / "neuralweb" / "market_plane.json", {
        "asof": session_date,
        "verdict": {
            "verdict": "RISK_ON", "score": 75, "label_en": "Risk-on", "label_zh": "风险偏好",
        },
        "contradiction_count": 0,
        "stale": False,
        "gaps": ["options_structure: no usable options_hub/gex payload for SPX/SPY/QQQ"],
    })
    _write(data / "release_forecast" / "latest.json", {
        "asof": f"{session_date}T10:00:00Z",
        "upcoming": [{
            "release": "cpi",
            "release_type": "cpi_headline",
            "release_date": session_date,
            "target": "mom_sa_pct",
            "projection": {
                "point": 0.2018, "p10": -0.5103, "p25": -0.0278,
                "p50": 0.2994, "p75": 0.6296, "p90": 0.8925,
            },
            "confidence": 0.42,
            "confidence_v2": 0.41,
            "surprise_skew": {"sigma": 0.4895, "tag": "hotter"},
            "surprise_distribution": {"p10": -0.5, "p90": 0.9},
            "reaction_sensitivity": {"spy": 0.3},
            "revision_risk": 0.1,
            "market_implied": {"source": "polymarket", "implied": "0.2%"},
            "model_epoch": "v3",
            "inputs_hash": "deadbeef",
            "code_receipt": "engine/release_forecast.py:1",
        }],
    })
    _write(site / "master_brief.json", {
        "generated_at": f"{session_date}T10:00:00Z", "state_asof": session_date, "lens": "macro",
    })
    return site, data


def _empty_tree(tmp_path: Path) -> tuple[Path, Path]:
    site = tmp_path / "site"
    data = tmp_path / "data"
    site.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    return site, data


def test_generated_at_may_not_launder_a_stale_source(tmp_path):
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)  # Tuesday, after open
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-05T10:00:00Z", session_date="2026-09-08")
    payload = build_payload(site, data, now=now)
    tape = next(b for b in payload["blocks"] if b["key"] == "tape_since_prior_close")
    assert tape["state"] != "CURRENT"
    assert tape["age_minutes"] > tape["max_age_minutes"]
    for b in payload["blocks"]:
        if b["state"] == "CURRENT" and b["key"] != "session_clock":
            assert 0 <= b["age_minutes"] <= b["max_age_minutes"]

    # Future-stamped source (negative age) must never be CURRENT.
    site2, data2 = _fresh_tree(tmp_path, tape_asof="2026-09-09T10:00:00Z", session_date="2026-09-08")
    payload2 = build_payload(site2, data2, now=now)
    tape2 = next(b for b in payload2["blocks"] if b["key"] == "tape_since_prior_close")
    assert tape2["state"] != "CURRENT"


def test_every_block_carries_its_own_source_clock(tmp_path):
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-08T13:00:00Z", session_date="2026-09-08")
    payload = build_payload(site, data, now=now)
    gen_at = payload["generated_at"]
    for b in payload["blocks"]:
        if b["state"] in ("CURRENT", "STALE_WITH_LAST_KNOWN"):
            assert b["source_as_of"] is not None
            if b["key"] != "session_clock":
                # session_clock is a self-computed calendar fact: its "source"
                # IS the current instant, so equality is not laundering.
                assert b["source_as_of"] != gen_at
        else:
            assert b["source_as_of"] is None


def test_state_vocabulary_includes_closed(tmp_path):
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-08T13:00:00Z", session_date="2026-09-08")
    payload = build_payload(site, data, now=now)
    for b in payload["blocks"]:
        assert b["state"] in STATES
    for s in (
        "CURRENT", "STALE_WITH_LAST_KNOWN", "UNAVAILABLE",
        "NOT_COVERED", "NOT_YET_OPEN", "CLOSED",
    ):
        assert s in STATES
    assert len(STATES) == 6


def test_missing_source_prints_a_null_it_does_not_drop_the_block(tmp_path):
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _empty_tree(tmp_path)
    payload = build_payload(site, data, now=now)
    keys = {b["key"] for b in payload["blocks"]}
    expected = {
        "session_clock", "tape_since_prior_close", "market_state", "regime",
        "cross_asset_plane", "todays_calendar", "prior_close_brief_ref",
    }
    assert keys == expected
    observed_null = 0
    for b in payload["blocks"]:
        if b["key"] == "session_clock":
            continue
        assert b["state"] in ("UNAVAILABLE", "NOT_COVERED")
        assert b["state_reason_en"]
        assert b["state_reason_zh"]
        observed_null += 1
    # session_clock is CURRENT during the cash session, so it is not a null.
    clock = next(b for b in payload["blocks"] if b["key"] == "session_clock")
    assert clock["state"] == "CURRENT"
    assert payload["null_count"] == observed_null


def test_feasibility_is_computed_not_assumed(tmp_path):
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)

    site_a, data_a = _fresh_tree(tmp_path / "a", tape_asof="2026-09-08T13:00:00Z", session_date="2026-09-08")
    payload_a = build_payload(site_a, data_a, now=now)
    assert payload_a["morning_source_feasibility"] == "AVAILABLE"

    site_b, data_b = _fresh_tree(tmp_path / "b", tape_asof="2026-07-27T22:32:09Z", session_date="2026-09-08")
    payload_b = build_payload(site_b, data_b, now=now)
    assert payload_b["morning_source_feasibility"] == "DEGRADED"
    assert payload_b["morning_source_feasibility_cause_en"]
    assert payload_b["morning_source_feasibility_cause_zh"]
    assert "site/live/quotes.json" not in payload_b["morning_source_feasibility_cause_en"]
    for b in payload_b["blocks"]:
        for row in b.get("rows") or []:
            if isinstance(row, dict) and "last" in row:
                assert b["state"] != "CURRENT"

    site_c, data_c = _empty_tree(tmp_path / "c")
    payload_c = build_payload(site_c, data_c, now=now)
    assert payload_c["morning_source_feasibility"] == "BLOCKED"
    assert payload_c["morning_source_feasibility_cause_en"]
    assert payload_c["morning_source_feasibility_cause_zh"]


def test_no_authority_fields_are_emitted(tmp_path):
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-08T13:00:00Z", session_date="2026-09-08")
    payload = build_payload(site, data, now=now)
    raw = json.dumps(payload)

    def _walk_keys(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield k
                yield from _walk_keys(v)
        elif isinstance(obj, list):
            for item in obj:
                yield from _walk_keys(item)

    keys = set(_walk_keys(payload))
    assert not (keys & FORBIDDEN_KEYS), keys & FORBIDDEN_KEYS
    assert payload["authority"] == "display_only"
    assert payload["display_only"] is True


def test_every_field_is_classified(tmp_path):
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-08T13:00:00Z", session_date="2026-09-08")
    payload = build_payload(site, data, now=now)
    for b in payload["blocks"]:
        assert b["classification"] in CLASSIFICATIONS


def test_weekend_and_before_open_states(tmp_path):
    saturday = datetime(2026, 9, 5, 15, 0, tzinfo=timezone.utc)  # Saturday
    site, data = _fresh_tree(tmp_path / "sat", tape_asof="2026-09-04T20:00:00Z", session_date="2026-09-05")
    payload = build_payload(site, data, now=saturday)
    assert payload["session_state"] == "NOT_YET_OPEN"
    tape = next(b for b in payload["blocks"] if b["key"] == "tape_since_prior_close")
    assert tape["state"] != "CURRENT"

    weekday_before_open = datetime(2026, 9, 8, 11, 0, tzinfo=timezone.utc)  # Tuesday 11:00 UTC
    site2, data2 = _fresh_tree(tmp_path / "wk", tape_asof="2026-09-08T10:59:00Z", session_date="2026-09-08")
    payload2 = build_payload(site2, data2, now=weekday_before_open)
    assert payload2["session_state"] == "NOT_YET_OPEN"
    tape2 = next(b for b in payload2["blocks"] if b["key"] == "tape_since_prior_close")
    # A 1-minute-old premarket reading IS current — session_open alone must
    # never force a fresh reading to STALE (that was the bug).
    assert tape2["state"] == "CURRENT"
    assert "Premarket" in (tape2["state_reason_en"] or "")

    # A genuinely stale premarket reading (well past the 240min budget) must
    # still read STALE_WITH_LAST_KNOWN with a bilingual disclosure.
    site3, data3 = _fresh_tree(tmp_path / "wk2", tape_asof="2026-09-08T05:00:00Z", session_date="2026-09-08")
    payload3 = build_payload(site3, data3, now=weekday_before_open)
    tape3 = next(b for b in payload3["blocks"] if b["key"] == "tape_since_prior_close")
    assert tape3["state"] == "STALE_WITH_LAST_KNOWN"
    assert tape3["state_reason_en"] and tape3["state_reason_zh"]


def test_output_is_deterministic(tmp_path):
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-08T13:00:00Z", session_date="2026-09-08")
    p1 = build_payload(site, data, now=now)
    p2 = build_payload(site, data, now=now)
    assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True)


def test_producer_never_breaks_the_render(tmp_path):
    from scripts import build_am_edition as mod

    site = tmp_path / "site"
    data = tmp_path / "data"
    site.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    # Poisoned 0-byte source.
    (site / "live").mkdir(parents=True, exist_ok=True)
    (site / "live" / "quotes.json").write_bytes(b"")

    class _FakeCfg(dict):
        pass

    orig_load = mod.config.load
    orig_root = mod.config.ROOT
    try:
        mod.config.load = lambda: {"storage": {"site_dir": str(site)}}
        mod.config.ROOT = str(tmp_path)
        rc = mod.main()
        assert rc == 0
        out = site / "am_edition.json"
        assert out.exists()
        payload = json.loads(out.read_text())
        assert payload["schema"] == "am_edition.v1"
    finally:
        mod.config.load = orig_load
        mod.config.ROOT = orig_root


def test_prior_close_date_walks_back_to_a_trading_day(tmp_path):
    # Monday 2026-09-07 11:00 UTC, premarket. Calendar walk-back would land
    # on Sunday 2026-09-06, a date on which no close exists.
    monday_premarket = datetime(2026, 9, 7, 11, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-04T20:00:00Z", session_date="2026-09-07")
    payload = build_payload(site, data, now=monday_premarket)
    assert payload["prior_close_date"] == "2026-09-04"  # Friday, not Sunday


def test_nested_verdict_objects_never_leak_authority_fields(tmp_path):
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-08T13:00:00Z", session_date="2026-09-08")
    payload = build_payload(site, data, now=now)
    plane = next(b for b in payload["blocks"] if b["key"] == "cross_asset_plane")
    verdict = plane["rows"][0]["verdict"]
    assert set(verdict) == {"verdict", "label_en", "label_zh"}
    assert "score" not in json.dumps(plane)
    assert "gaps" not in plane["rows"][0]
    assert "contradiction_count" not in plane["rows"][0]
    assert "stale" not in plane["rows"][0]
    assert plane["rows"][0]["contradictions_en"] == "No disagreements across the plane."
    assert plane["rows"][0]["contradictions_zh"] == "各资产读数一致，无分歧。"
    assert plane["rows"][0]["freshness_en"] == "This plane reading is current."
    assert plane["rows"][0]["freshness_zh"] == "该全景读数是最新的。"


def test_regime_row_carries_no_raw_quad_slug(tmp_path):
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-08T13:00:00Z", session_date="2026-09-08")
    payload = build_payload(site, data, now=now)
    regime = next(b for b in payload["blocks"] if b["key"] == "regime")
    raw = json.dumps(regime)
    assert '"Q2"' not in raw
    assert regime["rows"][0]["quad_name_en"] == "Reflation"
    assert regime["rows"][0]["quad_name_zh"] == "再通胀"


def test_stale_block_never_ships_a_null_reason(tmp_path):
    stale_now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-08T13:00:00Z", session_date="2026-08-01")
    payload = build_payload(site, data, now=stale_now)
    for b in payload["blocks"]:
        if b["state"] == "STALE_WITH_LAST_KNOWN":
            assert b["state_reason_en"], b["key"]
            assert b["state_reason_zh"], b["key"]
            assert "(s)" not in b["state_reason_en"]
            assert "hour(s)" not in b["state_reason_en"]
            assert "minute(s)" not in b["state_reason_en"]


def test_dst_does_not_shift_the_open_by_an_hour(tmp_path):
    # 2026-01-15 (EST, UTC-5): 09:30 ET == 14:30 UTC. Under the old fixed
    # 13:30 UTC constant the session would falsely read OPEN a full hour
    # early; the EDT-tuned 13:30 UTC (09:30 ET summertime) must NOT open here.
    winter_at_old_edt_open = datetime(2026, 1, 15, 13, 30, tzinfo=timezone.utc)
    assert _is_session_open_now(winter_at_old_edt_open) is False
    winter_at_true_est_open = datetime(2026, 1, 15, 14, 30, tzinfo=timezone.utc)
    assert _is_session_open_now(winter_at_true_est_open) is True
    # 16:00 ET EST == 21:00 UTC; 15:59 ET must still read open.
    winter_just_before_close = datetime(2026, 1, 15, 20, 59, tzinfo=timezone.utc)
    assert _is_session_open_now(winter_just_before_close) is True
    winter_at_close = datetime(2026, 1, 15, 21, 0, tzinfo=timezone.utc)
    assert _is_session_open_now(winter_at_close) is False
    assert _session_phase(winter_at_close) == "closed"


def test_calendar_filters_on_release_date_and_whitelists_plain_titles(tmp_path):
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-08T13:00:00Z", session_date="2026-09-08")
    payload = build_payload(site, data, now=now)
    cal = next(b for b in payload["blocks"] if b["key"] == "todays_calendar")
    assert cal["rows"] == [{
        "release_date": "2026-09-08",
        "title_en": "Headline CPI (consumer prices)",
        "title_zh": "CPI 总体（消费者物价）",
    }]
    raw = json.dumps(cal)
    for leak in (
        "projection", "confidence", "surprise_skew", "hotter", "mom_sa_pct",
        "ppi_finaldemand", "inputs_hash", "model_epoch", "deadbeef",
    ):
        assert leak not in raw
    assert payload["null_count"] == 0


def test_empty_calendar_is_a_printed_null_not_a_resolved_block(tmp_path):
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-08T13:00:00Z", session_date="2026-09-08")
    # Production shape: release_date, never `date`. Nothing lands on session_date.
    _write(data / "release_forecast" / "latest.json", {
        "asof": "2026-09-08T10:00:00Z",
        "upcoming": [{
            "release": "ppi",
            "release_type": "ppi_finaldemand",
            "release_date": "2026-09-10",
            "date": "2026-09-08T13:30:00Z",  # invented field must NOT match
            "projection": {"point": 0.2},
            "confidence": 0.5,
            "surprise_skew": {"tag": "hotter"},
        }],
    })
    payload = build_payload(site, data, now=now)
    cal = next(b for b in payload["blocks"] if b["key"] == "todays_calendar")
    assert cal["rows"] == []
    assert cal["state_reason_en"] == "No scheduled US releases today."
    assert cal["state_reason_zh"] == "今日无美国经济数据发布。"
    assert payload["null_count"] >= 1
    # Counting rule: empty calendar increments null_count.
    others = [b for b in payload["blocks"] if b["key"] != "todays_calendar"]
    expected = 1 + sum(
        1 for b in others if b["state"] in ("UNAVAILABLE", "NOT_COVERED", "NOT_YET_OPEN", "CLOSED")
    )
    assert payload["null_count"] == expected


def test_invented_date_key_never_matches_todays_calendar(tmp_path):
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-08T13:00:00Z", session_date="2026-09-08")
    _write(data / "release_forecast" / "latest.json", {
        "asof": "2026-09-08T10:00:00Z",
        "upcoming": [{"date": "2026-09-08T13:30:00Z", "name": "CPI"}],
    })
    payload = build_payload(site, data, now=now)
    cal = next(b for b in payload["blocks"] if b["key"] == "todays_calendar")
    assert cal["rows"] == []
    assert cal["state_reason_en"] == "No scheduled US releases today."


def test_post_close_session_is_closed_not_open(tmp_path):
    # Tuesday 21:00 ET (EDT, UTC-4) = 2026-09-09 01:00 UTC — five hours after the close.
    postclose = datetime(2026, 9, 9, 1, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-08T19:30:00Z", session_date="2026-09-08")
    payload = build_payload(site, data, now=postclose)
    assert payload["session_state"] == "CLOSED"
    clock = next(b for b in payload["blocks"] if b["key"] == "session_clock")
    assert clock["state"] == "CLOSED"
    assert clock["state_reason_en"] == "US markets have closed for the day."
    assert clock["state_reason_zh"] == "美股今日已收盘。"
    assert payload["null_count"] >= 1


def test_stale_quote_baseline_is_not_labelled_yesterdays_close(tmp_path):
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-07-27T22:32:09.883727Z", session_date="2026-09-08")
    payload = build_payload(site, data, now=now)
    # 2026-09-07 is Labor Day; the weekday-only walk used to name the holiday.
    assert payload["prior_close_date"] == "2026-09-04"
    tape = next(b for b in payload["blocks"] if b["key"] == "tape_since_prior_close")
    row = tape["rows"][0]
    assert row["change_pct"] is None
    assert row["prior_close"] == 739.0
    assert row["last"] == 740.0
    assert "basis" not in row
    assert "24 Jul" in tape["state_reason_en"]
    assert "Compared with the close of 24 Jul" in tape["state_reason_en"]
    assert "7月24日" in tape["state_reason_zh"]


def test_same_session_quote_keeps_change_pct_against_prior_close(tmp_path):
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-08T13:00:00Z", session_date="2026-09-08")
    payload = build_payload(site, data, now=now)
    tape = next(b for b in payload["blocks"] if b["key"] == "tape_since_prior_close")
    assert payload["prior_close_date"] == "2026-09-04"
    assert tape["rows"][0]["change_pct"] == 0.14
    assert "Compared with the close of" not in (tape["state_reason_en"] or "")


def test_stale_reason_uses_weeks_not_machine_hours(tmp_path):
    # 1020 hours = 42.5 days = 6 weeks. The old copy printed "1020 hour(s)".
    assert _humanize_age(1020 * 60) == ("6 weeks", "6周")
    assert _humanize_age(107 * 60) == ("4 days", "4天")
    assert _humanize_age(1) == ("1 minute", "1分钟")
    assert _humanize_age(60) == ("1 hour", "1小时")
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-07-27T22:32:09Z", session_date="2026-09-08")
    payload = build_payload(site, data, now=now)
    tape = next(b for b in payload["blocks"] if b["key"] == "tape_since_prior_close")
    assert tape["state"] == "STALE_WITH_LAST_KNOWN"
    assert "week" in tape["state_reason_en"]
    assert "(s)" not in tape["state_reason_en"]
    assert "1020" not in tape["state_reason_en"]
    assert "周" in tape["state_reason_zh"]


def test_unknown_quad_code_does_not_copy_english_into_zh(tmp_path):
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-08T13:00:00Z", session_date="2026-09-08")
    _write(data / "regime" / "latest.json", {
        "asof": "2026-09-08", "quad_name": "Reflation", "label": "QX",
    })
    payload = build_payload(site, data, now=now)
    regime = next(b for b in payload["blocks"] if b["key"] == "regime")
    assert regime["rows"][0]["quad_name_en"] == "Reflation"
    assert regime["rows"][0]["quad_name_zh"] is None
    assert "Reflation" not in (regime["state_reason_zh"] or "")
    assert "英文名未写入中文栏" in regime["state_reason_zh"]


def test_prior_brief_drops_raw_lens_and_state_asof(tmp_path):
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-08T13:00:00Z", session_date="2026-09-08")
    payload = build_payload(site, data, now=now)
    brief = next(b for b in payload["blocks"] if b["key"] == "prior_close_brief_ref")
    assert set(brief["rows"][0]) == {"generated_at", "link"}
    assert brief["rows"][0]["link"] == "/aibrief.html"
    raw = json.dumps(brief)
    assert "state_asof" not in raw
    assert '"lens"' not in raw


def test_not_yet_open_counts_toward_null_count(tmp_path):
    weekday_before_open = datetime(2026, 9, 8, 11, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-08T10:59:00Z", session_date="2026-09-08")
    payload = build_payload(site, data, now=weekday_before_open)
    assert payload["session_state"] == "NOT_YET_OPEN"
    clock = next(b for b in payload["blocks"] if b["key"] == "session_clock")
    assert clock["state"] == "NOT_YET_OPEN"
    assert payload["null_count"] >= 1


def test_nyse_holiday_session_is_closed_with_prior_session_close(tmp_path):
    # 2026-07-03 is the observed Independence Day (Friday; July 4 is Saturday).
    holiday = date(2026, 7, 3)
    assert not nyse_calendar.is_session(holiday)
    prior_session = nyse_calendar.last_session_on_or_before(holiday - timedelta(days=1))
    assert prior_session == date(2026, 7, 2)
    # Midday ET on the holiday (11:00 ET = 15:00 UTC, DST) — the old weekday
    # wall-clock would have published OPEN / CURRENT here.
    now = datetime(2026, 7, 3, 15, 0, tzinfo=timezone.utc)
    assert _session_phase(now) == "holiday"
    site, data = _fresh_tree(tmp_path, tape_asof="2026-07-02T20:00:00Z", session_date="2026-07-03")
    payload = build_payload(site, data, now=now)
    assert payload["session_state"] == "CLOSED"
    assert payload["prior_close_date"] == "2026-07-02"
    clock = next(b for b in payload["blocks"] if b["key"] == "session_clock")
    assert clock["state"] == "CLOSED"
    assert clock["state_reason_en"] == "Market holiday"
    assert clock["state_reason_zh"] == "休市日"
    # The weekday-only walk-back would name Friday 2026-07-03 (the holiday)
    # as prior_close_date on the following Monday.
    monday_after = datetime(2026, 7, 6, 15, 0, tzinfo=timezone.utc)
    site2, data2 = _fresh_tree(tmp_path / "mon", tape_asof="2026-07-02T20:00:00Z", session_date="2026-07-06")
    payload2 = build_payload(site2, data2, now=monday_after)
    assert payload2["prior_close_date"] == "2026-07-02"


def test_weekday_session_clock_unchanged_on_a_normal_session_day(tmp_path):
    # Wednesday 2026-09-16 11:00 ET (15:00 UTC) — a regular session with no
    # adjacent holiday, so prior_close_date is the previous weekday.
    now = datetime(2026, 9, 16, 15, 0, tzinfo=timezone.utc)
    assert nyse_calendar.is_session(date(2026, 9, 16))
    assert _session_phase(now) == "open"
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-16T13:00:00Z", session_date="2026-09-16")
    payload = build_payload(site, data, now=now)
    assert payload["session_state"] == "OPEN"
    assert payload["prior_close_date"] == "2026-09-15"
    clock = next(b for b in payload["blocks"] if b["key"] == "session_clock")
    assert clock["state"] == "CURRENT"
    assert clock["state_reason_en"] is None
