"""Catalyst status must fail closed when the incumbent live source is disconnected."""
from __future__ import annotations

from copy import deepcopy
import json


def view():
    row = {
        "ticker": "A",
        "legacy_alpha": 2.0,
        "current_context": {
            "episode": {
                "status": "AVAILABLE",
                "episode_id": "pe:SEC:US-XNAS-A:epoch_0:sa:abc:1",
                "company_id": "ISS:A",
            },
            "authority": {"rank": False, "entry": False, "size": False,
                          "execution": False, "trade": False},
        },
    }
    return {
        "schema": "mastermind.leadership_lab.recovery.v1",
        "rows": [deepcopy(row)],
        "shortlist": [deepcopy(row)],
        "current_context": {
            "authority": {"rank": False, "entry": False, "size": False,
                          "execution": False, "trade": False},
        },
        "authority": {"prophet_rank": False, "entry": False, "sizing": False,
                      "trade": False, "production_publish": False},
    }


def waiting():
    return {
        "schema": "entry_radar.w5_ledger_state/v1",
        "session": "2026-10-05",
        "state": "WAITING_FOR_LIVE_SOURCE",
        "spool_dir": None,
        "observed_spool_events": 0,
        "live_forward_rows": 0,
        "forward_rows_total": 0,
        "qledger": {"registered": 0, "rejected": 0, "failed": 0},
        "updated_at": "2026-10-05T10:08:52.994624+00:00",
    }


def attach(ledger=None):
    from engine.leadership_lab.catalyst import attach_catalyst_readiness
    return attach_catalyst_readiness(view(), waiting() if ledger is None else ledger)


def test_waiting_live_source_becomes_unavailable_not_no_catalyst():
    result = attach()
    global_state = result["current_context"]["catalyst"]
    row = result["rows"][0]["current_context"]["catalyst"]
    assert global_state["status"] == "UNAVAILABLE_LIVE_ENTRY_RADAR_SOURCE"
    assert global_state["owner_state"] == "WAITING_FOR_LIVE_SOURCE"
    assert global_state["absence_inference_allowed"] is False
    assert global_state["prophet_episode_substitution_allowed"] is False
    assert global_state["catalyst_probability"] is None
    assert row == {
        "status": "UNAVAILABLE",
        "reason": "LIVE_ENTRY_RADAR_LIVE_EPISODE_SOURCE_NOT_AVAILABLE",
        "catalyst_probability": None,
        "absence_inference_allowed": False,
        "authority": {"rank": False, "entry": False, "size": False,
                      "execution": False, "trade": False},
    }
    raw = json.dumps(result).lower()
    assert "no catalyst" not in raw
    assert "no event" not in raw


def test_owner_state_present_without_live_context_still_does_not_infer_probability():
    ledger = waiting()
    ledger.update(
        state="FORWARD_ACTIVE", spool_dir="/private/opaque", observed_spool_events=8,
        live_forward_rows=4, forward_rows_total=4)
    result = attach(ledger)
    assert result["current_context"]["catalyst"]["status"] == "OWNER_STATE_PRESENT_CONTEXT_NOT_CONNECTED"
    assert result["rows"][0]["current_context"]["catalyst"]["reason"] == "LIVE_CATALYST_CONTEXT_NOT_CONNECTED"
    assert result["rows"][0]["current_context"]["catalyst"]["catalyst_probability"] is None


def test_malformed_ledger_degrades_only_catalyst_lane():
    result = attach({"schema": "bad"})
    assert result["rows"][0]["legacy_alpha"] == 2.0
    assert result["current_context"]["catalyst"]["status"] == "UNAVAILABLE_OWNER_LEDGER"
    assert result["rows"][0]["current_context"]["catalyst"]["status"] == "UNAVAILABLE"


def test_catalyst_status_preserves_rows_order_and_authority():
    before = view()
    result = attach()
    assert before == view()
    assert [r["ticker"] for r in result["rows"]] == ["A"]
    assert result["authority"] == before["authority"]
    assert all(v is False for v in result["current_context"]["catalyst"]["authority"].values())


def test_output_is_strict_json():
    json.dumps(attach(), allow_nan=False)


def test_adapter_never_reads_prophet_expert_events_or_creates_event_owner():
    from pathlib import Path
    from engine.leadership_lab import catalyst as module
    source = Path(module.__file__).read_text()
    assert "expert_events" not in source
    assert "source_event_ids" not in source
    assert "assess_catalyst_context(" not in source
    assert "LiveEpisode(" not in source
