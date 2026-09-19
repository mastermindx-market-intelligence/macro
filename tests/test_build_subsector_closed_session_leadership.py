"""Builder wiring for Lane C closed-session leadership observations."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import build_subsector_rotation as build


def _bars(returns: list[float], *, start: str = "2026-06-01") -> pd.DataFrame:
    idx = pd.bdate_range(start, periods=len(returns) + 1)
    close = 100.0 * np.cumprod(np.array([1.0, *[1.0 + r for r in returns]]))
    return pd.DataFrame({"close": close, "volume": 100.0}, index=idx)


def test_completed_session_cutoff_excludes_same_day_before_close():
    market = _bars([0.0] * 5)
    latest = market.index[-1]
    before_close_utc = datetime(latest.year, latest.month, latest.day, 19, 30, tzinfo=timezone.utc)
    after_close_utc = datetime(latest.year, latest.month, latest.day, 20, 20, tzinfo=timezone.utc)

    before = build._completed_session_asof(market, str(latest.date()), now_utc=before_close_utc)
    after = build._completed_session_asof(market, str(latest.date()), now_utc=after_close_utc)

    assert before == str(market.index[-2].date())
    assert after == str(latest.date())


def test_bounded_owner_loader_skips_unrelated_parent_and_attaches_to_real_payload():
    market = _bars([0.0] * 70)
    member = _bars([0.001] * 70)
    calls: list[str] = []

    def loader(ticker: str):
        calls.append(ticker)
        return market if ticker == "SPY" else member

    tree = [
        {"theme": "Semiconductors", "subsectors": [
            {"key": "semiscompute", "name": "Compute", "members": ["NVDA", "AMD", "ARM"]},
        ]},
        {"theme": "Agriculture", "subsectors": [
            {"key": "agfert", "name": "Fertilizer", "members": ["NTR", "MOS", "CF"]},
        ]},
    ]
    observation = build._build_closed_session_leadership(
        tree,
        requested_asof=str(market.index[-1].date()),
        now_utc=datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc),
        loader=loader,
    )

    assert set(calls) == {"SPY", "NVDA", "AMD", "ARM"}
    assert set(observation["themes"]) == {"Semiconductors"}

    build._stamp_closed_session_metadata(
        observation, input_snapshot_asof=str(market.index[-1].date()),
        computed_utc="2026-09-19 16:00",
    )
    payload = {"themes": [{"theme": "Semiconductors"}, {"theme": "Agriculture"}]}
    build._attach_closed_session_leadership(payload, observation)
    assert payload["themes"][0]["leadership_observation"]["schema"].endswith(".v1")
    assert "leadership_observation" not in payload["themes"][1]
    assert payload["closed_session_leadership"]["covered_themes"] == ["Semiconductors"]
    assert payload["closed_session_leadership"]["permissions"]["may_rank"] is False
    receipt = payload["themes"][0]["leadership_observation"]["measurement_receipt"]
    assert receipt["basis"]["membership_is_point_in_time"] is False
    assert receipt["permissions"]["may_rank"] is False
    assert receipt["clocks"]["observation_session"] == str(market.index[-1].date())


def test_failure_receipt_is_visible_and_carries_local_clocks():
    fallback = build._unavailable_closed_session_leadership(
        requested_asof="2026-09-18", reason="OWNER_INPUT_LOAD_FAILED"
    )
    build._stamp_closed_session_metadata(
        fallback, input_snapshot_asof="2026-09-18",
        computed_utc="2026-09-19 16:00",
    )
    payload = {"themes": []}
    build._attach_closed_session_leadership(payload, fallback)

    meta = payload["closed_session_leadership"]
    assert meta["status"] == "UNAVAILABLE"
    assert meta["bar_status"] == "UNCONFIRMED"
    assert meta["reason_codes"] == ["OWNER_INPUT_LOAD_FAILED"]
    assert meta["asof"] is None
    assert meta["requested_asof"] == "2026-09-18"
    assert meta["clocks"] == {
        "observation_session": None,
        "input_snapshot_asof": "2026-09-18",
        "computation_utc": "2026-09-19 16:00",
    }
    assert "engine.basket_index._load_member_ohlcv" in meta["source_records"]


def test_build_writes_leadership_observation_through_actual_publisher(monkeypatch, tmp_path):
    data = tmp_path / "data" / "themes_heatmap"
    data.mkdir(parents=True)
    (data / "themes_tree.json").write_text(json.dumps([
        {"theme": "Semiconductors", "subsectors": []}
    ]))
    (data / "perf_snapshot.json").write_text(json.dumps({
        "asof": "2026-09-18", "subsector_perf": {}, "member_perf": {}
    }))
    (tmp_path / "data" / "subsector_rotation").mkdir(parents=True)

    payload = {
        "asof": "2026-09-18", "themes": [{"theme": "Semiconductors"}],
        "subsectors": [], "turn": {}, "n_subsectors": 0, "n_themes": 1,
        "highlights": {"emerging": []},
    }
    observation = {
        "schema": "subsector_rotation.closed_session_leadership.v1",
        "status": "MEASURED", "asof": "2026-09-18", "bar_status": "CLOSED",
        "permissions": {"may_rank": False},
        "themes": {"Semiconductors": {
            "schema": "subsector_rotation.closed_session_leadership.v1",
            "status": "MEASURED", "asof": "2026-09-18",
            "parent": {"key": "Semiconductors"}, "subthemes": [],
        }},
        "reason_codes": ["DESCRIPTIVE_SHADOW_ONLY"],
    }
    calls = []
    monkeypatch.setattr(build, "_data", lambda *parts: tmp_path / "data" / Path(*parts))
    monkeypatch.setattr(build, "_inject_megacap_node", lambda *_: None)
    monkeypatch.setattr(build, "_load_history", lambda: [])
    monkeypatch.setattr(build.sr, "compute_rotation", lambda *a, **k: payload.copy())
    monkeypatch.setattr(build, "_build_closed_session_leadership",
                        lambda *a, **k: calls.append("leadership") or observation.copy())
    monkeypatch.setattr(build.sr, "compute_sector_etf_perf", lambda *_: {})
    monkeypatch.setattr(build, "_write_turn_artifacts", lambda *_: None)
    from engine import subsector_rotation_alerts, subsector_track_record
    monkeypatch.setattr(subsector_rotation_alerts, "rebuild", lambda *_: [])
    monkeypatch.setattr(subsector_track_record, "snapshot", lambda *a, **k: 0)
    monkeypatch.setattr(subsector_track_record, "compute",
                        lambda *a, **k: {"verdict": "accruing"})
    monkeypatch.setattr(subsector_track_record, "withdraw_unbacked_note", lambda *_: None)

    site = tmp_path / "site"
    result = build.build(site=site, generated_utc="2026-09-19 16:00")

    assert calls == ["leadership"]
    assert result["themes"][0]["leadership_observation"]["asof"] == "2026-09-18"
    written = json.loads((site / "marketdata" / "subsector_rotation.json").read_text())
    assert written["themes"][0]["leadership_observation"]["status"] == "MEASURED"
    assert (
        written["closed_session_leadership"]["clocks"]["computation_utc"]
        == "2026-09-19 16:00"
    )


def test_no_completed_market_session_fails_closed_instead_of_using_partial_bar():
    same_day = pd.DataFrame(
        {"close": [100.0], "volume": [1.0]},
        index=pd.DatetimeIndex(["2026-09-18"]),
    )

    result = build._build_closed_session_leadership(
        [{"theme": "Semiconductors", "subsectors": []}],
        requested_asof="2026-09-18",
        now_utc=datetime(2026, 9, 18, 19, 30, tzinfo=timezone.utc),
        loader=lambda ticker: same_day if ticker == "SPY" else None,
        parent_keys={"Semiconductors"},
    )

    assert result["status"] == "UNAVAILABLE"
    assert result["asof"] is None
    assert result["requested_asof"] == "2026-09-18"
    assert result["bar_status"] == "UNCONFIRMED"
    assert result["reason_codes"] == ["NO_COMPLETED_SESSION"]
