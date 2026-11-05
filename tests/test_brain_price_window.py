"""Deferred combined-pass coverage for the active rendered OHLCV price window.

Authored during feature construction. Execution remains deferred by Chairman ordering.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.neuralweb import brain_gateway as gw

SCHEMA = "chart.price_window.v1"


def state(scope: str = "loaded_tail", replay: bool = False) -> dict:
    source_count = 20
    start = 8
    rows = [
        {
            "source_index": i,
            "time": f"2026-09-{i + 1:02d}",
            "open": 100.0 + i,
            "high": 102.0 + i,
            "low": 99.0 + i,
            "close": 101.0 + i,
            "volume": 1000.0 + i,
            "age_bars_from_loaded_end": 999,  # server must ignore/recompute
        }
        for i in range(start, source_count)
    ]
    visible = None
    eligible = source_count
    omitted = start
    if scope == "visible_tail":
        rows = rows[:6]
        visible = {
            "from": gw._price_window_time(rows[0]["time"]),
            "to": gw._price_window_time(rows[-1]["time"]),
        }
        eligible = len(rows)
        omitted = 0
    packet = {
        "schema": SCHEMA,
        "status": "observed",
        "symbol": "NVDA",
        "tf": "D",
        "source_bar_count": source_count,
        "selection": {
            "scope": scope,
            "visible_range": visible,
            "eligible_bars": eligible,
            "returned_bars": len(rows),
            "omitted_older_bars": omitted,
            "max_bars": 12,
            "order": "oldest_to_newest",
        },
        "basis": {
            "data_status": "replay_slice" if replay
            else "loaded_chart_cache_not_live_attestation",
        },
        "bars": rows,
    }
    return {
        "connected": True,
        "origin_id": "price-origin",
        "context_revision": 4,
        "session": {
            "symbol": "NVDA",
            "tf": "D",
            "pane_id": 0,
            "price_window": packet,
        },
    }


def qualify(value: dict) -> dict:
    return gw._qualified_chart_price_window(value)


def test_price_window_loaded_tail_is_server_qualified_and_age_is_recomputed():
    value = state()
    before = copy.deepcopy(value)
    out = qualify(value)
    assert out["status"] == "observed"
    assert out["source"] == "terminal_active_rendered_bars_structurally_qualified"
    assert out["selection"]["scope"] == "loaded_tail"
    assert out["selection"]["returned_bars"] == 12
    assert out["bars"][0]["source_index"] == 8
    assert out["bars"][0]["age_bars_from_loaded_end"] == 11
    assert out["bars"][-1]["source_index"] == 19
    assert out["bars"][-1]["age_bars_from_loaded_end"] == 0
    assert out["basis"]["last_bar_closed"] == "unknown"
    assert out["basis"]["predictive_validation"] is False
    assert value == before


def test_price_window_visible_tail_keeps_only_viewport_basis():
    out = qualify(state("visible_tail"))
    assert out["status"] == "observed"
    assert out["selection"]["scope"] == "visible_tail"
    assert out["selection"]["returned_bars"] == 6
    assert out["selection"]["visible_range"] is not None
    assert all(
        out["selection"]["visible_range"]["from"]
        <= gw._price_window_time(row["time"])
        <= out["selection"]["visible_range"]["to"]
        for row in out["bars"]
    )


def test_price_window_replay_status_survives_sanitization():
    out = qualify(state(replay=True))
    assert out["basis"]["data_status"] == "replay_slice"
    assert out["basis"]["freshness"] == "chart_loaded_data_not_independently_live_attested"


@pytest.mark.parametrize(("mutate", "reason"), [
    (lambda s: s["session"]["price_window"]["bars"].__setitem__(
        1, {**s["session"]["price_window"]["bars"][1], "source_index": 8}),
     "price_window_index_invalid"),
    (lambda s: s["session"]["price_window"]["bars"].__setitem__(
        1, {**s["session"]["price_window"]["bars"][1], "source_index": 10}),
     "price_window_index_gap"),
    (lambda s: s["session"]["price_window"]["bars"].__setitem__(
        1, {**s["session"]["price_window"]["bars"][1], "time": "2026-09-01"}),
     "price_window_time_order_invalid"),
    (lambda s: s["session"]["price_window"]["bars"][0].__setitem__("high", float("nan")),
     "price_window_ohlc_invalid"),
    (lambda s: s["session"]["price_window"]["bars"][0].__setitem__("volume", -1),
     "price_window_volume_invalid"),
])
def test_price_window_rejects_malformed_or_cherry_pickable_sequences(mutate, reason):
    value = state()
    mutate(value)
    assert qualify(value)["reason"] == reason


def test_visible_tail_rejects_bar_outside_declared_viewport():
    value = state("visible_tail")
    value["session"]["price_window"]["selection"]["visible_range"]["to"] = (
        gw._price_window_time(value["session"]["price_window"]["bars"][-2]["time"])
    )
    assert qualify(value)["reason"] == "price_window_bar_outside_viewport"


def test_loaded_tail_must_end_at_loaded_series_tail():
    value = state()
    value["session"]["price_window"]["bars"] = value["session"]["price_window"]["bars"][:-1]
    value["session"]["price_window"]["selection"]["returned_bars"] -= 1
    value["session"]["price_window"]["selection"]["omitted_older_bars"] += 1
    assert qualify(value)["reason"] == "price_window_loaded_tail_invalid"


def test_read_chart_state_replaces_client_price_packet_with_qualified_projection(monkeypatch):
    value = state("visible_tail")
    record = {
        "session": value["session"],
        "context_revision": value["context_revision"],
        "acks": [],
    }
    monkeypatch.setattr(gw, "get_chart_state_record", lambda *_args, **_kwargs: record)
    out = gw._tool_read_chart_state(
        "price-user", "terminal",
        origin_id=value["origin_id"], context_revision=value["context_revision"],
    )
    assert out["connected"] is True
    assert out["session"]["price_window"]["status"] == "observed"
    assert out["session"]["price_window"]["selection"]["scope"] == "visible_tail"
