"""Captured artifacts exercise original calculation owners without file acquisition."""
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from engine import basket_score, basket_breadth_divergence, cycle_phase_age, us_act_now, sector_pulse
from scripts import build_stock_library
from tests.test_sector_auxiliary_capture import decoded, financial_frames, parquet


@pytest.fixture(autouse=True)
def no_ambient_reads(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Captured projection attempted ambient source acquisition")
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    from lib import config
    monkeypatch.setattr(config, "load", forbidden)
    monkeypatch.setattr(config, "data_dir", forbidden)
    monkeypatch.setattr(config, "site_dir", forbidden)


def test_one_calibration_document_supplies_existing_rollover_and_divergence_owners():
    result = decoded(baskets_calibration=b'{"rollover_fit":{"verdict":"ship_fitted_weights","wired_weights":[0.1,0.2,0.3,0.15,0.25]},"breadth_divergence_fit":{"verdict":"ship_sizing_leg","wired_weights":[0.6,0.25,0.15]}}')
    document = result.document("baskets_calibration")
    assert basket_score.rollover_weights_from_document(document) == (0.1, 0.2, 0.3, 0.15, 0.25)
    divergence = basket_breadth_divergence.calibration_from_document(document)
    assert basket_breadth_divergence._bd_weights(calibration=divergence) == (0.6, 0.25, 0.15)
    divergence["wired_weights"][0] = 999
    assert document["breadth_divergence_fit"]["wired_weights"][0] == 0.6


@pytest.mark.parametrize("value", [None, [], {}, {"rollover_fit": "bad"},
    {"rollover_fit": {"verdict": "ship_fitted_weights", "wired_weights": ["bad"] * 5}}])
def test_rollover_keeps_its_incumbent_optional_fallback(value):
    assert basket_score.rollover_weights_from_document(value) == basket_score._ROLLOVER_HAND


def test_one_forward_log_supplies_phase_history_and_latest_bottoming_rows():
    result = decoded(cycle_forward_log=parquet(financial_frames()["cycle_forward_log"]))
    frame = result.table("cycle_forward_log")
    history, status = cycle_phase_age.phase_history_from_inputs(
        frame, observation=result.observation("cycle_forward_log").decode_outcome)
    assert status == "ok"
    assert list(history.columns) == ["date", "id", "phase_v2", "basis"]
    assert history["basis"].tolist() == ["tr", "tr"]
    rows = us_act_now.cycle_rows_from_inputs(frame)
    assert [row["id"] for row in rows] == ["xlf"]
    assert rows[0]["date"] == "2026-11-05"
    assert rows[0]["timing_state"] == "late"
    assert rows[0]["pos"] == 55.0
    history.iloc[0, 0] = "changed"
    assert frame.iloc[0]["date"] == "2026-11-04"


def test_phase_observation_cannot_invent_absence():
    assert cycle_phase_age.phase_history_from_inputs(None, observation="absent") == (None, "absent")
    assert cycle_phase_age.phase_history_from_inputs(None, observation="unreadable") == (None, "read_error")
    assert cycle_phase_age.phase_history_from_inputs(None, observation="malformed") == (None, "read_error")
    with pytest.raises(ValueError):
        cycle_phase_age.phase_history_from_inputs(None, observation="unattempted")
    with pytest.raises(ValueError):
        cycle_phase_age.phase_history_from_inputs(pd.DataFrame(), observation="absent")
    assert us_act_now.cycle_rows_from_inputs(None) is None
    assert us_act_now.cycle_rows_from_inputs(pd.DataFrame()) == []


def test_pulse_keeps_original_archive_dates_order_and_heat_verdict():
    frame = pd.DataFrame({
        "asof": ["2026-11-05", "2026-11-04"],
        "snapshot_json": ['{"themes":[{"id":"semis","score":70}]}', '{"themes":[{"id":"semis","score":60}]}'],
    })
    result = decoded(basket_archive=parquet(frame),
        pulse_heat=b'{"verdict":{"broken":{"verdict":"measurable_edge","claim":"drawdown"}}}')
    rows = sector_pulse.archive_snapshots_from_inputs(result.table("basket_archive"))
    assert [row["asof"] for row in rows] == ["2026-11-04", "2026-11-05"]
    assert [row["themes"][0]["score"] for row in rows] == [60, 70]
    document = result.document("pulse_heat")
    selected = sector_pulse.heat_calibration_from_document(document)
    assert selected == {"broken": {"verdict": "measurable_edge", "claim": "drawdown"}}
    selected["broken"]["claim"] = "mutated"
    assert document["verdict"]["broken"]["claim"] == "drawdown"


def test_timing_context_uses_persisted_mrs_and_rank_composite_without_new_math():
    latest = {"liquidity_overlay": "contracting", "macro_risk": {"score": 0.75}, "date": "2026-10-30"}
    assert build_stock_library.liquidity_from_document(latest) == "contracting"
    assert build_stock_library.macro_drag_from_document(latest) == 0.75
    assert build_stock_library.liquidity_from_document({"liquidity_overlay": "unknown"}) is None
    assert build_stock_library.macro_drag_from_document({"macro_risk": {"score": "0.75"}}) is None
    factors = {"table": [
        {"ticker": "A", "composite_rank": 0, "composite": 99, "sue": 1.5, "value": 0.2, "sector": "Tech"},
        {"ticker": "B", "composite_rank": None, "composite": 0.4, "sue": 0},
        {"composite": 123},
    ]}
    context = build_stock_library.factor_context_from_document(factors)
    assert context["factor_z"] == {"A": 0, "B": 0.4}
    assert context["sue_z"] == {"A": 1.5, "B": 0}
    assert context["factor_legs"]["A"] == {"value": 0.2, "quality": None, "profitability": None}
    assert context["sectors"] == {"A": "Tech"}
    assert latest["date"] == "2026-10-30"


def test_incumbent_partial_factor_row_fallback_is_preserved():
    result = build_stock_library.factor_context_from_document(
        {"table": [{"ticker": "A", "composite": 1}, None, {"ticker": "B", "composite": 2}]})
    assert result["factor_z"] == {"A": 1}


def test_captured_optional_breadth_uses_existing_concentration_projection():
    frame = pd.DataFrame({"adv": [30.0] * 25, "dec": [10.0] * 25},
                         index=pd.date_range("2026-10-01", periods=25))
    result = decoded(breadth_tape=parquet(frame))
    assert basket_score.market_concentration_from_inputs(result.table("breadth_tape")) == basket_score.market_concentration_from_inputs(frame)
