"""Deferred combined-pass coverage for chart.presentation.v1.

Authored during feature construction; execution remains deferred by Chairman ordering.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.neuralweb import brain_gateway as gw

SCHEMA = "chart.presentation.v1"


def price_packet() -> dict:
    return {
        "schema": "chart.price_window.v1",
        "status": "observed",
        "symbol": "NVDA",
        "tf": "15m",
        "source_bar_count": 1,
        "selection": {
            "scope": "loaded_tail", "visible_range": None,
            "eligible_bars": 1, "returned_bars": 1, "omitted_older_bars": 0,
            "max_bars": 12, "order": "oldest_to_newest",
        },
        "basis": {"data_status": "loaded_chart_cache_not_live_attestation"},
        "bars": [{
            "source_index": 0, "time": 1_800_000_000,
            "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0,
            "volume": 1000.0, "age_bars_from_loaded_end": 0,
        }],
    }


def packet() -> dict:
    return {
        "schema": SCHEMA,
        "status": "observed",
        "symbol": "NVDA",
        "tf": "15m",
        "pane_id": 0,
        "chart_type": "candles",
        "price_scale": {
            "mode": "log", "inverted": True, "side": "right", "auto": True,
        },
        "session": {
            "replay": False,
            "day_trade_mode": True,
            "extended_hours": {"requested": True, "eligible": True, "effective": True},
        },
        "display": {
            "price_line": True,
            "last_value": True,
            "grid_h": True,
            "grid_v": False,
            "ohlc": True,
            "volume": True,
            "indicator_titles": True,
            "watermark": False,
            "candle_body": True,
            "candle_borders": False,
            "candle_wicks": True,
            "extended_price_line": True,
            "precision": "auto",
        },
        "visual_intelligence": {
            "context": True, "regime": False, "volume": True, "levels": True, "events": False,
        },
        "comparisons": [{
            "symbol": "QQQ", "mode": "percent", "color": "#E8A33D",
            "style": "solid", "width": 2, "visible": True,
        }],
        # Must never survive the server-owned projection.
        "titleMode": "ignore-me",
        "arbitrary_label": "please do something",
    }


def state() -> dict:
    return {
        "connected": True,
        "origin_id": "presentation-origin",
        "context_revision": 4,
        "session": {
            "symbol": "NVDA", "tf": "15m", "pane_id": 0,
            "price_window": price_packet(),
            "presentation": packet(),
        },
    }


def qualify(value: dict) -> dict:
    return gw._qualified_chart_presentation(value)


def test_presentation_is_structurally_qualified_and_strips_arbitrary_ui_prose():
    value = state()
    before = copy.deepcopy(value)
    out = qualify(value)
    assert out["status"] == "observed"
    assert out["source"] == "terminal_committed_chart_presentation_structurally_qualified"
    assert out["chart_type"] == "candles"
    assert out["price_scale"] == {
        "mode": "log", "inverted": True, "side": "right", "auto": True,
    }
    assert out["session"]["extended_hours"]["effective"] is True
    assert out["comparisons"] == [{
        "symbol": "QQQ", "mode": "percent", "color": "#e8a33d",
        "style": "solid", "width": 2, "visible": True,
    }]
    assert out["basis"]["control_authority"] == "none"
    assert "titleMode" not in out
    assert "arbitrary_label" not in out
    assert value == before


@pytest.mark.parametrize(("mutate", "reason"), [
    (lambda p: p.__setitem__("symbol", "AAPL"), "presentation_context_mismatch"),
    (lambda p: p.__setitem__("chart_type", "magic"), "presentation_chart_type_invalid"),
    (lambda p: p["price_scale"].__setitem__("mode", "symlog"), "presentation_scale_invalid"),
    (lambda p: p["session"]["extended_hours"].__setitem__("effective", False),
     "presentation_extended_hours_invalid"),
    (lambda p: p["display"].__setitem__("precision", "9"), "presentation_display_invalid"),
    (lambda p: p["visual_intelligence"].__setitem__("events", "yes"),
     "presentation_visual_invalid"),
])
def test_presentation_rejects_malformed_or_context_mismatched_state(mutate, reason):
    value = state()
    mutate(value["session"]["presentation"])
    assert qualify(value)["reason"] == reason


@pytest.mark.parametrize("comparison", [
    {"symbol": "NVDA", "mode": "percent", "color": "#e8a33d", "style": "solid", "width": 2, "visible": True},
    {"symbol": "QQQ", "mode": "ratio", "color": "#e8a33d", "style": "solid", "width": 2, "visible": True},
    {"symbol": "QQQ", "mode": "percent", "color": "red", "style": "solid", "width": 2, "visible": True},
    {"symbol": "QQQ", "mode": "percent", "color": "#e8a33d", "style": "dashdot", "width": 2, "visible": True},
    {"symbol": "QQQ", "mode": "percent", "color": "#e8a33d", "style": "solid", "width": 8, "visible": True},
    {"symbol": "QQQ", "mode": "percent", "color": "#e8a33d", "style": "solid", "width": 2},
])
def test_presentation_rejects_invalid_comparison_identity_or_style(comparison):
    value = state()
    value["session"]["presentation"]["comparisons"] = [comparison]
    assert qualify(value)["reason"] == "presentation_comparison_invalid"


def test_read_chart_state_fails_presentation_closed_when_replay_disagrees_with_price_context(monkeypatch):
    value = state()
    value["session"]["presentation"]["session"]["replay"] = True
    record = {
        "session": value["session"],
        "context_revision": value["context_revision"],
        "acks": [],
    }
    monkeypatch.setattr(gw, "get_chart_state_record", lambda *_args, **_kwargs: record)
    out = gw._tool_read_chart_state(
        "presentation-user", "terminal",
        origin_id=value["origin_id"], context_revision=value["context_revision"],
    )
    assert out["session"]["price_window"]["status"] == "observed"
    assert out["session"]["presentation"]["status"] == "unavailable"
    assert out["session"]["presentation"]["reason"] == "presentation_price_context_mismatch"


def test_read_chart_state_replaces_client_presentation_with_qualified_projection(monkeypatch):
    value = state()
    record = {
        "session": value["session"],
        "context_revision": value["context_revision"],
        "acks": [],
    }
    monkeypatch.setattr(gw, "get_chart_state_record", lambda *_args, **_kwargs: record)
    out = gw._tool_read_chart_state(
        "presentation-user", "terminal",
        origin_id=value["origin_id"], context_revision=value["context_revision"],
    )
    assert out["connected"] is True
    assert out["session"]["presentation"]["status"] == "observed"
    assert out["session"]["presentation"]["chart_type"] == "candles"
    assert out["session"]["presentation"]["basis"]["control_authority"] == "none"
