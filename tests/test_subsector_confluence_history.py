from __future__ import annotations

import json
from pathlib import Path

from engine import subsector_confluence_history as H


def _group(key: str, cls: str, state: str, *, side: str = "neutral", tier: str | None = None):
    return {
        "key": key,
        "label": key.title(),
        "sector": "Technology",
        "class": cls,
        "n_members": 3,
        "n_priced": 3,
        "reliability": "high",
        "entry": {
            "tier": tier,
            "weight": 0.9 if tier else 0.0,
            "ticks": 1 if tier else None,
            "fresh_bars": 1 if tier else None,
            "buyable": bool(tier),
            "reason": "test",
        },
        "regime": {
            "state": state,
            "side": side,
            "action": "test action",
            "rs_60d": 12.0,
        },
        "members": [{"ticker": "AAA"}, {"ticker": "BBB"}, {"ticker": "CCC"}],
    }


def _payload():
    return {
        "ok": True,
        "universe": "sp500_subsectors",
        "as_of": "2026-09-18",
        "subsectors": [
            _group("semiconductors", "entry_now", "EXTENDED", side="avoid", tier="T1"),
            _group("software", "neutral", "NEUTRAL"),
        ],
    }


def test_snapshot_is_first_seen_immutable_and_idempotent(tmp_path: Path):
    p = _payload()
    assert H.snapshot(p, "subsectors", root=tmp_path) == 2

    # A same-session recompute is not allowed to rewrite what users originally saw.
    p["subsectors"][0]["label"] = "REWRITTEN"
    p["subsectors"][0]["regime"]["state"] = "BUY"
    assert H.snapshot(p, "subsectors", root=tmp_path) == 0

    rows = [
        json.loads(line)
        for line in (tmp_path / "data/subsector_rotation/confluence_snapshots.jsonl")
        .read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 2
    semi = next(row for row in rows if row["key"] == "semiconductors")
    assert semi["label"] == "Semiconductors"
    assert semi["regime_state"] == "EXTENDED"
    assert semi["entry_condition"] == "stretched"
    assert semi["members"] == ["AAA", "BBB", "CCC"]


def test_public_projection_reconstructs_daily_recommendations_without_members(tmp_path: Path, monkeypatch):
    _clock(monkeypatch, "2026-09-18T22:30:00Z")
    assert H.snapshot(_payload(), "subsectors", root=tmp_path) == 2
    out = H.public_projection(today="2026-09-18", root=tmp_path)

    assert out["schema"] == H.PROJECTION_SCHEMA
    assert out["history_start"] == "2026-09-18"
    assert out["pit_only_since"] == "2026-09-18"
    assert out["accuracy"]["status"] == "accruing"

    day = out["days"][0]
    desk = day["desks"]["subsectors"]
    assert desk["counts"]["entry_now"] == 1
    assert desk["counts"]["neutral"] == 1
    rec = desk["recommendations"][0]
    assert rec["key"] == "semiconductors"
    assert rec["entry_tier"] == "T1"
    assert rec["entry_condition"] == "stretched"
    assert "members" not in rec


def test_accuracy_summary_separates_extended_from_other_fresh_entries():
    rows = [
        {"fwd_rel": 0.10, "entry_condition": "stretched"},
        {"fwd_rel": -0.04, "entry_condition": "stretched"},
        {"fwd_rel": 0.03, "entry_condition": "clean"},
    ]
    assert H._summary(rows)["n"] == 3
    ext = H._summary([r for r in rows if r["entry_condition"] == "stretched"])
    clean = H._summary([r for r in rows if r["entry_condition"] != "stretched"])
    assert ext == {"n": 2, "mean_fwd_rel": 0.03, "hit_rate": 0.5}
    assert clean == {"n": 1, "mean_fwd_rel": 0.03, "hit_rate": 1.0}


def test_unknown_or_degraded_desk_never_appends(tmp_path: Path):
    assert H.snapshot({"ok": False}, "subsectors", root=tmp_path) == 0
    assert H.snapshot(_payload(), "unknown", root=tmp_path) == 0
    assert not (tmp_path / "data/subsector_rotation/confluence_snapshots.jsonl").exists()


# Source recovery: publication availability and finite, coverage-qualified outcomes.
from datetime import datetime, timezone
import math

import pytest


def _clock(monkeypatch, stamp: str):
    value = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    monkeypatch.setattr(H, "_utc_now", lambda: value, raising=False)


def _prices(monkeypatch, *, missing=()):
    monkeypatch.setattr(H, "_covers", lambda *_: True)
    monkeypatch.setattr(H, "_level_asof", lambda ticker, *_: None if ticker in missing else 100.0)
    monkeypatch.setattr(H, "_close_at", lambda ticker, *_: None if ticker in missing else (105.0 if ticker == "SPY" else 110.0))


def test_repair_records_actual_observation_separately_from_source_date(tmp_path, monkeypatch):
    _clock(monkeypatch, "2026-09-25T22:30:00Z")
    payload = _payload()
    payload["generated_utc"] = "2026-09-25 22:29 UTC"
    assert H.snapshot(payload, "subsectors", root=tmp_path) == 2
    row = H._load(tmp_path)[0]
    assert row["date"] == "2026-09-18"
    assert row.get("observed_at") == "2026-09-25T22:30:00Z"
    assert row.get("source_generated_utc") == payload["generated_utc"]
    _clock(monkeypatch, "2026-09-26T22:30:00Z")
    assert H.snapshot(payload, "subsectors", root=tmp_path) == 0
    assert H._load(tmp_path)[0] == row


@pytest.mark.parametrize("observed,eligible", [
    ("2026-09-18T22:30:00Z", True),
    ("2026-09-19T12:00:00Z", True),  # Saturday maps to the same Friday data session.
    ("2026-09-25T22:30:00Z", False),
])
def test_repair_late_capture_stays_history_only(tmp_path, monkeypatch, observed, eligible):
    _clock(monkeypatch, observed)
    _prices(monkeypatch)
    assert H.snapshot(_payload(), "subsectors", root=tmp_path) == 2
    result = H.accuracy(today="2026-09-25", root=tmp_path, horizons=(5,))
    assert result["horizons"]["5"]["all"]["n"] == int(eligible)
    assert result["status"] == ("measuring" if eligible else "accruing")
    assert H.public_projection(today="2026-09-25", root=tmp_path)["days"][0]["date"] == "2026-09-18"


@pytest.mark.parametrize("observation", [None, "", "2026-09-18T22:30:00", "bad-date"])
def test_repair_unknown_or_naive_observation_cannot_score(tmp_path, monkeypatch, observation):
    _clock(monkeypatch, "2026-09-18T22:30:00Z")
    _prices(monkeypatch)
    assert H.snapshot(_payload(), "subsectors", root=tmp_path) == 2
    rows = H._load(tmp_path)
    for row in rows:
        if observation is None:
            row.pop("observed_at", None)
        else:
            row["observed_at"] = observation
    ledger = tmp_path / "data/subsector_rotation/confluence_snapshots.jsonl"
    ledger.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    before = ledger.read_bytes()
    assert H.accuracy(today="2026-09-25", root=tmp_path, horizons=(5,))["horizons"]["5"]["all"]["n"] == 0
    assert ledger.read_bytes() == before


@pytest.mark.parametrize("asof", [None, "", "not-a-date"])
def test_repair_missing_or_invalid_source_date_never_mints_a_session(tmp_path, monkeypatch, asof):
    _clock(monkeypatch, "2026-09-18T22:30:00Z")
    payload = _payload()
    payload["as_of"] = asof
    assert H.snapshot(payload, "subsectors", root=tmp_path) == 0
    assert not (tmp_path / "data/subsector_rotation/confluence_snapshots.jsonl").exists()


@pytest.mark.parametrize("p0,p1", [
    (float("nan"), 110.0), (float("inf"), 110.0), (-100.0, 110.0),
    (0.0, 110.0), (100.0, float("nan")), (100.0, float("inf")),
    (100.0, float("-inf")), (100.0, -1.0),
])
def test_repair_invalid_member_endpoints_are_unscored(tmp_path, monkeypatch, p0, p1):
    monkeypatch.setattr(H, "_level_asof", lambda *_: p0)
    monkeypatch.setattr(H, "_close_at", lambda *_: p1)
    assert H._member_ret("AAA", tmp_path, "2026-09-18", "2026-09-23") is None


def test_repair_zero_terminal_value_retains_total_loss(tmp_path, monkeypatch):
    monkeypatch.setattr(H, "_level_asof", lambda *_: 100.0)
    monkeypatch.setattr(H, "_close_at", lambda *_: 0.0)
    assert H._member_ret("AAA", tmp_path, "2026-09-18", "2026-09-23") == -1.0


@pytest.mark.parametrize("b0,b1", [
    (float("nan"), 105.0), (float("inf"), 105.0), (-100.0, 105.0),
    (0.0, 105.0), (100.0, float("nan")), (100.0, float("inf")), (100.0, -1.0),
])
def test_repair_invalid_benchmark_never_makes_a_measuring_row(tmp_path, monkeypatch, b0, b1):
    _clock(monkeypatch, "2026-09-18T22:30:00Z")
    monkeypatch.setattr(H, "_covers", lambda *_: True)
    monkeypatch.setattr(H, "_level_asof", lambda ticker, *_: b0 if ticker == "SPY" else 100.0)
    monkeypatch.setattr(H, "_close_at", lambda ticker, *_: b1 if ticker == "SPY" else 110.0)
    assert H.snapshot(_payload(), "subsectors", root=tmp_path) == 2
    result = H.accuracy(today="2026-09-25", root=tmp_path, horizons=(5,))
    assert result["horizons"]["5"]["all"]["n"] == 0
    assert result["status"] == "accruing"
    json.dumps(result, allow_nan=False)


def test_repair_priced_subset_keeps_minimum_and_reports_missing_members(tmp_path, monkeypatch):
    _clock(monkeypatch, "2026-09-18T22:30:00Z")
    _prices(monkeypatch, missing=("DDD",))
    payload = _payload()
    payload["subsectors"][0]["members"].append({"ticker": "DDD"})
    assert H.snapshot(payload, "subsectors", root=tmp_path) == 2
    result = H.accuracy(today="2026-09-25", root=tmp_path, horizons=(5,))
    horizon = result["horizons"]["5"]
    assert horizon["all"] == {"n": 1, "mean_fwd_rel": 0.05, "hit_rate": 1.0}
    assert horizon.get("coverage") == {
        "priced_member_observations": 3, "frozen_member_observations": 4, "partial_rows": 1,
    }
    assert "priced subset" in result["note"].lower()
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("state,side,expected", [
    ("", "", "unavailable"), ("MYSTERY", "buy", "unavailable"),
    ("SELL", "", "caution"), ("NEUTRAL", "neutral", "clean"),
])
def test_repair_absent_regime_never_becomes_a_positive_condition(state, side, expected):
    assert H._entry_condition({"regime_state": state, "regime_side": side}) == expected


def test_repair_nightly_hook_is_isolated_and_render_lane_does_not_append(tmp_path, monkeypatch):
    from scripts import build_subsector_confluence as builder
    _clock(monkeypatch, "2026-09-18T22:30:00Z")
    monkeypatch.setattr(H.config, "ROOT", tmp_path)
    monkeypatch.setenv("COLLECT_LANE", "render")
    assert builder._record_history(tmp_path / "site", ("subsectors", _payload())) == 0
    assert H._load(tmp_path) == []
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    assert builder._record_history(tmp_path / "site", ("subsectors", _payload())) == 2
    projected = json.loads((tmp_path / "site" / builder.HISTORY_JSON).read_text())
    assert projected["days"][0]["desks"]["subsectors"]["recommendations"][0]["key"] == "semiconductors"


def test_repair_archival_start_does_not_invent_a_prospective_start(tmp_path):
    source = Path(__file__).resolve().parent.parent / "data/subsector_rotation/confluence_snapshots.jsonl"
    raw = source.read_bytes()
    ledger = tmp_path / "data/subsector_rotation/confluence_snapshots.jsonl"
    ledger.parent.mkdir(parents=True)
    ledger.write_bytes(raw)
    out = H.public_projection(today="2026-11-06", root=tmp_path)
    assert out["history_start"] == "2026-09-18"
    assert out["pit_only_since"] is None
    assert out["accuracy"]["status"] == "accruing"
    assert ledger.read_bytes() == raw
    assert all("observed_at" not in row for row in H._load(tmp_path))


def test_repair_finite_endpoints_cannot_overflow_into_a_return(tmp_path, monkeypatch):
    monkeypatch.setattr(H, "_level_asof", lambda *_: 1e-308)
    monkeypatch.setattr(H, "_close_at", lambda *_: 1e308)
    assert H._member_ret("AAA", tmp_path, "2026-09-18", "2026-09-23") is None
