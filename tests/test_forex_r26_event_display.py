"""Display qualification preserves the incumbent technical-event owner."""
from copy import deepcopy

import pandas as pd
import pytest

from engine import forex_alerts
from scripts import build_forex as builder


@pytest.mark.parametrize("pair,assessed,inverted", [
    ("USDJPY", "JPY", True), ("EURUSD", "EUR", False),
    ("USDCNH", "CNH", True),
])
@pytest.mark.parametrize("method", ["adjusted", "raw_fallback", "zero_filled", "unavailable", None])
def test_actual_event_producer_keeps_identity_and_qualifies_assessed_series(pair, assessed, inverted, method):
    index = pd.date_range("2026-10-15", periods=3)
    frame = pd.DataFrame({
        "close": [1.0, 1.1, 1.2],
        "momentum_state": ["bear", "bull", "bull"],
        "structure_state": ["broken", "constructive", "constructive"],
        "ts_trend": ["short", "long", "long"],
        "shock_state": ["normal", "exogenous_bid", "exogenous_bid"],
        "shock_z": [0.0, 3.2, 3.2],
        "residual_method": [method] * 3,
    }, index=index)
    meta = {"label": pair[:3] + "/" + pair[3:], "base": assessed, "invert": inverted}
    original = forex_alerts._pair_events(pair, frame, meta)
    before = deepcopy(original)
    before_frame = frame.copy(deep=True)
    projected = builder._project_event_display(original, {pair: frame}, {"assets": {pair: meta}})
    assert {event["type"] for event in projected} == {"momentum", "structure", "trend_flip", "residual_shock"}
    assert original == before
    pd.testing.assert_frame_equal(frame, before_frame)
    for source, display in zip(original, projected):
        assert {key: display[key] for key in source} == source
        assert display["display_assessed_currency"] == assessed
        assert display["display_basis"] == "assessed_currency_residual_pipeline"
        assert display["display_residual_method"] == method
        assert display["display_headline_en"].startswith(assessed)
        assert display["display_headline_zh"].startswith(assessed)
        assert "residual technical series" in display["display_basis_en"]
        assert "残差技术序列" in display["display_basis_zh"]
        assert not display["display_headline_en"].startswith(meta["label"])
    groups = builder._group_timeline(projected)
    shown = {event["id"]: event for group in groups for event in group["events"]}
    for event in projected:
        assert shown[event["id"]]["headline"] == event["display_headline_en"]
        assert shown[event["id"]]["headline_zh"] == event["display_headline_zh"]
        assert shown[event["id"]]["ts"] == event["ts"]
    projected[0]["context"]["display_mutation"] = True
    assert original == before, "projection must not alias ledger context"


def test_missing_convention_and_unrelated_events_pass_through_without_relabeling():
    event = {"id": "unchanged", "asset": "USDJPY", "type": "risk_regime",
             "ts": "2026-10-16T16:00:00Z", "headline": "USD/JPY risk changed",
             "headline_zh": "美元日元风险变化", "context": {"risk_index": 42}}
    for kind, cfg in [("risk_regime", {"assets": {"USDJPY": {"base": "JPY"}}}),
                      ("momentum", {"assets": {}})]:
        candidate = {**event, "type": kind}
        out = builder._project_event_display([candidate], {}, cfg)
        assert out == [candidate]
        assert out[0] is not candidate


def test_event_day_basis_never_borrows_a_newer_rows_adjustment():
    frame = pd.DataFrame({"residual_method": ["raw_fallback", "adjusted"]},
                         index=pd.to_datetime(["2026-10-16", "2026-10-19"]))
    event = {"id": "old", "asset": "USDJPY", "type": "momentum",
             "ts": "2026-10-16T16:00:00Z", "headline": "USD/JPY: Trend turned up",
             "headline_zh": "USD/JPY：趋势转强"}
    out = builder._project_event_display([event], {"USDJPY": frame},
                                         {"assets": {"USDJPY": {"base": "JPY"}}})[0]
    assert out["display_residual_method"] == "raw_fallback"
    assert "raw-price fallback" in out["display_basis_en"]
    assert out["display_headline_en"] == "JPY: Trend turned up"
    assert "down" not in out["display_headline_en"], "residual direction must not be naively inverted"


@pytest.mark.parametrize("method", [["malformed"], {"malformed": True}, pd.NA])
def test_unknown_event_day_method_is_disclosed(method):
    frame = pd.DataFrame({"residual_method": [method]}, index=pd.to_datetime(["2026-10-16"]))
    event = {"id": "unknown", "asset": "USDJPY", "type": "structure",
             "ts": "2026-10-16", "headline": "USD/JPY: Chart shape broke down"}
    out = builder._project_event_display([event], {"USDJPY": frame},
                                         {"assets": {"USDJPY": {"base": "JPY"}}})[0]
    assert out["display_residual_method"] is None
    assert "not supplied" in out["display_basis_en"]



def test_residual_shock_direction_is_not_presented_as_the_opposite_literal_quote_move():
    frame = pd.DataFrame({
        "close": [1 / 150, 1 / 149],
        "shock_state": ["normal", "exogenous_bid"],
        "shock_z": [0.0, 3.2],
        "residual_method": ["adjusted", "adjusted"],
    }, index=pd.to_datetime(["2026-10-15", "2026-10-16"]))
    meta = {"label": "USD/JPY", "base": "JPY", "invert": True}
    source = forex_alerts._pair_events("USDJPY", frame, meta)[0]
    shown = builder._project_event_display([source], {"USDJPY": frame},
                                           {"assets": {"USDJPY": meta}})[0]
    assert source["type"] == "residual_shock"
    assert source["headline"].startswith("USD/JPY:") and "(up)" in source["headline"]
    assert "USD/JPY 149.0000" in source["detail"]
    assert shown["display_headline_en"].startswith("JPY:") and "(up)" in shown["display_headline_en"]
    assert shown["display_headline_zh"].startswith("JPY：") and "异常上行" in shown["display_headline_zh"]
    assert "Assessed JPY residual technical series" in shown["display_basis_en"]
    assert {key: shown[key] for key in source} == source
