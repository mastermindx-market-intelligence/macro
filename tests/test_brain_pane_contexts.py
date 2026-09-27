"""Deferred combined-pass regressions for read-only mounted-pane chart context.

Authored during feature construction; execution remains deferred by current Chairman ordering.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.neuralweb import brain_gateway as gw

NATIVE = "chart.native_live_observations.v1"
PRICE = "chart.price_window.v1"
PRESENTATION = "chart.presentation.v1"
PANES = "chart.pane_contexts.v1"


def unavailable_native(reason: str = "fixture_native_unavailable") -> dict:
    return {"schema": NATIVE, "status": "unavailable", "reason": reason}


def price_packet(symbol: str, tf: str, when: float, visible: dict | None = None) -> dict:
    return {
        "schema": PRICE,
        "status": "observed",
        "symbol": symbol,
        "tf": tf,
        "source_bar_count": 1,
        "selection": {
            "scope": "visible_tail" if visible else "loaded_tail",
            "visible_range": visible,
            "eligible_bars": 1,
            "returned_bars": 1,
            "omitted_older_bars": 0,
            "max_bars": 12,
            "order": "oldest_to_newest",
        },
        "basis": {"data_status": "loaded_chart_cache_not_live_attestation"},
        "bars": [{
            "source_index": 0, "time": when,
            "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0,
            "volume": 1000.0, "age_bars_from_loaded_end": 0,
        }],
    }


def presentation_packet(symbol: str, tf: str, pane_id: int, chart_type: str) -> dict:
    return {
        "schema": PRESENTATION,
        "status": "observed",
        "symbol": symbol,
        "tf": tf,
        "pane_id": pane_id,
        "chart_type": chart_type,
        "price_scale": {"mode": "normal", "inverted": False, "side": "right", "auto": True},
        "session": {
            "replay": False,
            "day_trade_mode": False,
            "extended_hours": {"requested": False, "eligible": False, "effective": False},
        },
        "display": {
            "price_line": True, "last_value": True, "grid_h": True, "grid_v": True,
            "ohlc": True, "volume": False, "indicator_titles": True, "watermark": True,
            "candle_body": True, "candle_borders": True, "candle_wicks": True,
            "extended_price_line": True, "precision": "auto",
        },
        "visual_intelligence": {
            "context": True, "regime": False, "volume": False, "levels": False, "events": False,
        },
        "comparisons": [],
    }


def pane_state() -> dict:
    active_native = unavailable_native()
    return {
        "connected": True,
        "origin_id": "pane-origin",
        "context_revision": 9,
        "session": {
            "symbol": "NVDA",
            "tf": "D",
            "pane_id": 0,
            "indicators": [],
            "capabilities": {},
            "price_window": price_packet(
                "NVDA", "D", 1_500.0, {"from": 1_000.0, "to": 2_000.0},
            ),
            "presentation": presentation_packet("NVDA", "D", 0, "candles"),
            "native_observations": active_native,
            "pane_contexts": {
                "schema": PANES,
                "status": "observed",
                "active_pane_id": 0,
                "pane_count": 2,
                "control_authority": "active_pane_only",
                "panes": [
                    {
                        "pane_id": 0,
                        "symbol": "NVDA",
                        "tf": "D",
                        "visible_range": {"from": 1_000.0, "to": 2_000.0},
                        "price_window_ref": "session.price_window",
                        "presentation_ref": "session.presentation",
                        "native_observations_ref": "session.native_observations",
                    },
                    {
                        "pane_id": 1,
                        "symbol": "NVDA",
                        "tf": "W",
                        "visible_range": {"from": 3_000.0, "to": 4_000.0},
                        "price_window": price_packet(
                            "NVDA", "W", 3_500.0, {"from": 3_000.0, "to": 4_000.0},
                        ),
                        "presentation": presentation_packet("NVDA", "W", 1, "line"),
                        "native_observations": unavailable_native("weekly_fixture_unavailable"),
                    },
                ],
            },
        },
        "acks": [],
    }


def test_pane_contexts_preserve_separate_read_only_bases_without_mutating_input():
    state = pane_state()
    before = copy.deepcopy(state)
    out = gw._qualified_chart_pane_contexts(state)

    assert out["status"] == "partial"
    assert out["control_authority"] == "active_pane_only"
    assert out["active_pane_id"] == 0
    assert out["pane_count"] == 2
    assert out["basis"]["read_only"] is True
    assert out["basis"]["context_revision"] == "read_does_not_increment"
    assert out["panes"][0]["native_observations_ref"] == "session.native_observations"
    assert out["panes"][0]["price_window_ref"] == "session.price_window"
    assert out["panes"][0]["presentation_ref"] == "session.presentation"
    assert "native_observations" not in out["panes"][0]
    assert "price_window" not in out["panes"][0]
    assert "presentation" not in out["panes"][0]
    assert out["panes"][1]["native_observations"]["reason"] == "weekly_fixture_unavailable"
    assert out["panes"][1]["price_window"]["status"] == "observed"
    assert out["panes"][1]["presentation"]["chart_type"] == "line"
    assert out["panes"][1]["price_window"]["selection"]["scope"] == "visible_tail"
    assert state == before


def test_pre_presentation_client_degrades_pane_context_to_partial_not_invalid():
    state = pane_state()
    state["session"].pop("presentation")
    state["session"]["pane_contexts"]["panes"][0].pop("presentation_ref")
    state["session"]["pane_contexts"]["panes"][1].pop("presentation")
    out = gw._qualified_chart_pane_contexts(state)
    assert out["status"] == "partial"
    assert out["panes"][0]["presentation_ref"] == "session.presentation"
    assert out["panes"][1]["presentation"]["status"] == "unavailable"
    assert out["panes"][1]["presentation"]["reason"] == "presentation_not_supplied"


def test_active_pane_identity_must_match_root_chart():
    state = pane_state()
    state["session"]["pane_contexts"]["panes"][0]["symbol"] = "AAPL"
    out = gw._qualified_chart_pane_contexts(state)
    assert out["status"] == "unavailable"
    assert out["reason"] == "active_pane_context_mismatch"


def test_active_pane_must_reference_root_presentation_price_and_native_packets_without_duplicates():
    state = pane_state()
    state["session"]["pane_contexts"]["panes"][0]["price_window_ref"] = "wrong"
    out = gw._qualified_chart_pane_contexts(state)
    assert out["status"] == "unavailable"
    assert out["reason"] == "active_pane_reference_invalid"

    state = pane_state()
    state["session"]["pane_contexts"]["panes"][0]["price_window"] = copy.deepcopy(
        state["session"]["price_window"]
    )
    out = gw._qualified_chart_pane_contexts(state)
    assert out["status"] == "unavailable"
    assert out["reason"] == "active_pane_reference_invalid"

    state = pane_state()
    state["session"]["pane_contexts"]["panes"][0]["presentation_ref"] = "wrong"
    out = gw._qualified_chart_pane_contexts(state)
    assert out["status"] == "unavailable"
    assert out["reason"] == "active_pane_reference_invalid"

    state = pane_state()
    state["session"]["pane_contexts"]["panes"][0]["presentation"] = copy.deepcopy(
        state["session"]["presentation"]
    )
    out = gw._qualified_chart_pane_contexts(state)
    assert out["status"] == "unavailable"
    assert out["reason"] == "active_pane_reference_invalid"


def test_inactive_pane_cannot_reference_active_root_packets():
    state = pane_state()
    state["session"]["pane_contexts"]["panes"][1].pop("price_window")
    state["session"]["pane_contexts"]["panes"][1]["price_window_ref"] = "session.price_window"
    out = gw._qualified_chart_pane_contexts(state)
    assert out["status"] == "unavailable"
    assert out["reason"] == "inactive_pane_reference_invalid"

    state = pane_state()
    state["session"]["pane_contexts"]["panes"][1].pop("presentation")
    state["session"]["pane_contexts"]["panes"][1]["presentation_ref"] = "session.presentation"
    out = gw._qualified_chart_pane_contexts(state)
    assert out["status"] == "unavailable"
    assert out["reason"] == "inactive_pane_reference_invalid"


def test_duplicate_or_out_of_range_pane_ids_fail_closed():
    for ids in ((0, 0), (0, 4)):
        state = pane_state()
        for row, pane_id in zip(state["session"]["pane_contexts"]["panes"], ids):
            row["pane_id"] = pane_id
        out = gw._qualified_chart_pane_contexts(state)
        assert out["status"] == "unavailable"
        assert out["reason"] == "pane_context_identity_invalid"


def test_pane_presentation_replay_must_match_pane_price_context():
    state = pane_state()
    state["session"]["pane_contexts"]["panes"][1]["presentation"]["session"]["replay"] = True
    out = gw._qualified_chart_pane_contexts(state)
    assert out["status"] == "unavailable"
    assert out["reason"] == "pane_presentation_price_context_mismatch"


def test_pane_price_window_must_match_the_same_panesync_viewport():
    state = pane_state()
    state["session"]["pane_contexts"]["panes"][1]["price_window"]["selection"]["visible_range"] = {
        "from": 3_100.0, "to": 4_000.0,
    }
    out = gw._qualified_chart_pane_contexts(state)
    assert out["status"] == "unavailable"
    assert out["reason"] == "pane_price_window_viewport_mismatch"


def test_nonfinite_or_reversed_viewports_fail_closed():
    bad_ranges = (
        {"from": float("inf"), "to": 4_000.0},
        {"from": 4_000.0, "to": 3_000.0},
        "not-a-range",
    )
    for visible in bad_ranges:
        state = pane_state()
        state["session"]["pane_contexts"]["panes"][1]["visible_range"] = visible
        out = gw._qualified_chart_pane_contexts(state)
        assert out["status"] == "unavailable"
        assert out["reason"] == "pane_context_visible_range_invalid"


def test_mirror_coverage_accepts_explicit_pane_context_budget_omission():
    session = {
        "drawings": [],
        "mirror_coverage": {
            "schema": "chart.state_coverage.v1",
            "partial": True,
            "omitted_fields": ["pane_contexts"],
            "drawings": None,
            "acks_in_batch": 0,
            "acks_pending": 0,
            "basis": "transport_projection_not_chart_deletion",
        },
    }
    out = gw._qualified_chart_mirror_coverage(session)
    assert out is not None
    assert out["status"] == "reported"
    assert out["partial"] is True
    assert out["omitted_fields"] == ["pane_contexts"]


def test_read_chart_state_exposes_qualified_pane_contexts(monkeypatch):
    state = pane_state()
    record = {
        "session": state["session"],
        "context_revision": state["context_revision"],
        "acks": [],
    }
    monkeypatch.setattr(gw, "get_chart_state_record", lambda *_args, **_kwargs: record)
    out = gw._tool_read_chart_state(
        "pane-user", "terminal",
        origin_id=state["origin_id"], context_revision=state["context_revision"],
    )
    assert out["connected"] is True
    assert out["session"]["pane_contexts"]["pane_count"] == 2
    assert out["session"]["pane_contexts"]["control_authority"] == "active_pane_only"
    assert out["session"]["pane_contexts"]["panes"][0]["price_window_ref"] == "session.price_window"
    assert out["session"]["pane_contexts"]["panes"][0]["presentation_ref"] == "session.presentation"
    assert out["session"]["pane_contexts"]["panes"][1]["price_window"]["status"] == "observed"
    assert out["session"]["pane_contexts"]["panes"][1]["presentation"]["chart_type"] == "line"
