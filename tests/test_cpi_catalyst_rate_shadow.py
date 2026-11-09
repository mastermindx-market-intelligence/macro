from __future__ import annotations

import copy
from datetime import date
import json

import pandas as pd
import pytest

from research.rates_direction import cpi_catalyst_rate_shadow as c


def _coherent(release: str, *, asof="2026-10-13", rdate="2026-10-14", point=0.3):
    return {
        "schema": 2,
        "row_type": "shadow_projection",
        "model": "coherent_ridge_v1",
        "model_epoch": "coherent_ridge_v1",
        "target_epoch": "alfred_same_release_vintage_proxy_v1",
        "display_only": True,
        "authority": False,
        "asof_night": asof,
        "release": release,
        "period": "2026-09",
        "release_date": rdate,
        "projection_point": point,
        "prediction_id": f"{release}:coherent",
        "inputs_hash": f"hash-{release}",
    }


def _champion(release: str, *, asof="2026-10-13", rdate="2026-10-14", med=0.2, point=-99.0):
    return {
        "schema": 2,
        "row_type": "projection",
        "model": None,
        "asof_night": asof,
        "release": release,
        "period": "2026-09",
        "release_date": rdate,
        "projection_point": point,
        "expectation_read": {
            "expectation_median": med,
            "sources": ["cleveland_nowcast"],
        },
    }


def test_component_threshold_is_fixed_and_symmetric():
    assert c.component_state(0.051) == 1
    assert c.component_state(0.05) == 1
    assert c.component_state(0.0499) == 0
    assert c.component_state(-0.0499) == 0
    assert c.component_state(-0.05) == -1


def test_combine_states_conflict_abstains_and_inline_allows_single_direction():
    assert c.combine_states(1, 1) == 1
    assert c.combine_states(1, 0) == 1
    assert c.combine_states(0, -1) == -1
    assert c.combine_states(1, -1) == 0
    assert c.combine_states(0, 0) == 0


def test_build_event_uses_coherent_point_but_only_expectation_context_from_champion():
    rows = [
        _coherent("cpi_headline", point=0.31),
        _coherent("cpi_core", point=0.27),
        _champion("cpi_headline", med=0.20, point=-50),
        _champion("cpi_core", med=0.24, point=50),
    ]
    events = c.build_events(rows)
    assert len(events) == 1
    e = events[0]
    assert e["prospective_eligible"] is True
    assert e["signal"] == 1
    assert e["headline"]["gap_pp"] == pytest.approx(0.11)
    assert e["core"]["gap_pp"] == pytest.approx(0.03)
    assert e["headline"]["expectation_sources"] == ["cleveland_nowcast"]


def test_build_event_refuses_non_tminus1_and_requires_both_components():
    rows = [
        _coherent("cpi_headline", asof="2026-10-12"),
        _champion("cpi_headline", asof="2026-10-12"),
        _coherent("cpi_core"),
        _champion("cpi_core"),
    ]
    assert c.build_events(rows) == []


def test_build_event_marks_prefreeze_history_excluded():
    rows = [
        _coherent("cpi_headline", asof="2026-09-10", rdate="2026-09-11"),
        _coherent("cpi_core", asof="2026-09-10", rdate="2026-09-11"),
        _champion("cpi_headline", asof="2026-09-10", rdate="2026-09-11"),
        _champion("cpi_core", asof="2026-09-10", rdate="2026-09-11"),
    ]
    events = c.build_events(rows)
    assert len(events) == 1
    assert events[0]["prospective_eligible"] is False


def test_duplicate_coherent_identity_fails_closed():
    row = _coherent("cpi_headline")
    with pytest.raises(ValueError, match="duplicate coherent"):
        c.build_events([
            row,
            copy.deepcopy(row),
            _coherent("cpi_core"),
            _champion("cpi_headline"),
            _champion("cpi_core"),
        ])


def test_attach_outcome_uses_prior_and_future_observations_without_fill():
    idx = pd.to_datetime([
        "2026-10-06",
        "2026-10-07",
        "2026-10-08",
        "2026-10-09",
        "2026-10-12",
        "2026-10-13",
        "2026-10-14",
        "2026-10-15",
        "2026-10-16",
        "2026-10-19",
        "2026-10-20",
        "2026-10-21",
    ])
    values = [4.80, 4.81, 4.82, 4.83, 4.84, 4.85, 4.89, 4.90, 4.91, 4.92, 4.93, 4.94]
    s = pd.Series(values, index=idx)
    event = {
        "release_date": "2026-10-14",
        "prospective_eligible": True,
        "signal": 1,
    }
    out = c.attach_outcome(event, s)["outcome"]
    assert out["prior_close"] == pytest.approx(4.85)
    assert out["baseline_5obs_bp"] == pytest.approx(5.0)
    assert out["baseline_state"] == 1
    assert out["h0_bp"] == pytest.approx(4.0)
    assert out["h0_state"] == 1
    assert out["h1_bp"] == pytest.approx(5.0)
    assert out["h5_bp"] == pytest.approx(9.0)


def test_move_class_keeps_small_moves_inline():
    assert c.move_class(1.99) == 0
    assert c.move_class(-1.99) == 0
    assert c.move_class(2.0) == 1
    assert c.move_class(-2.0) == -1
    assert c.move_class(None) is None


def test_summary_counts_one_release_once_and_prefreeze_never_scores():
    pre = {
        "release_date": "2026-09-11",
        "prospective_eligible": False,
        "signal": 1,
        "outcome": {"h0_state": 1, "h1_state": 1, "h5_state": 1, "baseline_state": -1},
    }
    live = {
        "release_date": "2026-10-14",
        "prospective_eligible": True,
        "signal": 1,
        "outcome": {"h0_state": 1, "h1_state": 0, "h5_state": -1, "baseline_state": -1},
    }
    abstain = {
        "release_date": "2026-11-12",
        "prospective_eligible": True,
        "signal": 0,
        "outcome": {"h0_state": 1, "h1_state": 1, "h5_state": 1, "baseline_state": 1},
    }
    out = c.summarize([pre, live, abstain])
    assert out["pre_freeze_excluded"] == 1
    assert out["prospective_events"] == 2
    assert out["prospective_active"] == 1
    assert out["prospective_abstained"] == 1
    assert out["h0"]["n_active_matured"] == 1
    assert out["h0"]["catalyst_hits"] == 1
    assert out["h0"]["baseline_hits"] == 0
    assert out["descriptive_floor_met"] is False
