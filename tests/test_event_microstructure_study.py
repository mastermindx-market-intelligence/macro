from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_MODULE = Path(__file__).resolve().parents[1] / "research" / "event_microstructure_study.py"
_SPEC = importlib.util.spec_from_file_location("event_microstructure_study", _MODULE)
assert _SPEC is not None and _SPEC.loader is not None
s = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(s)


def _event(**overrides):
    base = {
        "event_id": "evt-1",
        "event_time": "2026-09-24T16:28:00Z",
        "available_at": "2026-09-24T16:30:00Z",
        "observed_at": "2026-09-24T16:32:00Z",
        "source_class": "wire",
    }
    base.update(overrides)
    return base


def _points(rows):
    return [{"ts": ts, "price": price} for ts, price in rows]


def test_operational_clock_uses_observed_at_not_publication_time():
    assert (
        s.knowledge_time(_event(), mode="operational_pit").isoformat()
        == "2026-09-24T16:32:00+00:00"
    )
    assert (
        s.knowledge_time(_event(), mode="public_reconstruction").isoformat()
        == "2026-09-24T16:30:00+00:00"
    )


def test_refuses_impossible_clock_order():
    with pytest.raises(s.StudyContractError):
        s.knowledge_time(
            _event(
                available_at="2026-09-24T16:29:00Z",
                event_time="2026-09-24T16:30:00Z",
            ),
            mode="public_reconstruction",
        )


def test_causal_asset_crosses_before_response_and_lag_is_measured():
    causal = _points(
        [
            ("2026-09-24T16:31:00Z", 100.0),
            ("2026-09-24T16:32:00Z", 100.0),
            ("2026-09-24T16:34:00Z", 99.60),
            ("2026-09-24T17:02:00Z", 99.40),
        ]
    )
    response = _points(
        [
            ("2026-09-24T16:31:00Z", 200.0),
            ("2026-09-24T16:32:00Z", 200.0),
            ("2026-09-24T16:35:00Z", 200.2),
            ("2026-09-24T16:38:00Z", 200.7),
            ("2026-09-24T16:49:00Z", 201.2),
            ("2026-09-24T17:04:00Z", 202.0),
        ]
    )
    benchmark = _points(
        [
            ("2026-09-24T16:34:00Z", 400.0),
            ("2026-09-24T16:49:00Z", 400.8),
            ("2026-09-24T17:04:00Z", 401.0),
        ]
    )
    out = s.analyze_event(
        event=_event(),
        causal_points=causal,
        response_points=response,
        benchmark_points=benchmark,
        mode="operational_pit",
        causal_direction=-1,
        response_direction=1,
        causal_threshold_bps=30,
        response_threshold_bps=25,
    )
    assert out["causal_confirmed"] is True
    assert out["ordered_propagation"] is True
    assert out["causal"]["crossed_at"] == "2026-09-24T16:34:00Z"
    assert out["response"]["crossed_at"] == "2026-09-24T16:38:00Z"
    assert out["lag_seconds"] == 240.0
    assert (
        out["forward_from_causal_confirmation"]["30m"]["residual_return_bps"]
        is not None
    )


def test_response_that_moves_first_is_not_ordered_propagation():
    causal = _points(
        [
            ("2026-09-24T16:32:00Z", 100.0),
            ("2026-09-24T16:39:00Z", 99.6),
        ]
    )
    response = _points(
        [
            ("2026-09-24T16:32:00Z", 200.0),
            ("2026-09-24T16:34:00Z", 200.8),
        ]
    )
    out = s.analyze_event(
        event=_event(),
        causal_points=causal,
        response_points=response,
        mode="operational_pit",
        causal_direction=-1,
        response_direction=1,
        causal_threshold_bps=30,
        response_threshold_bps=25,
    )
    assert out["lag_seconds"] < 0
    assert out["ordered_propagation"] is False


def test_stale_baseline_is_data_gap_not_zero_move():
    out = s.first_threshold_cross(
        _points(
            [
                ("2026-09-24T16:00:00Z", 100.0),
                ("2026-09-24T16:35:00Z", 99.0),
            ]
        ),
        anchor="2026-09-24T16:32:00Z",
        direction=-1,
        threshold_bps=25,
        horizon_minutes=10,
        max_baseline_age_minutes=5,
    )
    assert out["status"] == "data_gap"
    assert out["crossed_at"] is None


def test_forward_return_refuses_missing_end_bar():
    value = s.forward_return_bps(
        _points(
            [
                ("2026-09-24T16:34:00Z", 100.0),
                ("2026-09-24T16:40:00Z", 101.0),
            ]
        ),
        anchor="2026-09-24T16:34:00Z",
        horizon_minutes=30,
    )
    assert value is None


def test_social_lead_is_timing_context_not_authority_upgrade():
    ladder = s.publication_ladder(
        [
            _event(
                claim_id="social",
                source_class="social",
                event_time="2026-09-24T16:20:00Z",
                available_at="2026-09-24T16:20:00Z",
                observed_at="2026-09-24T16:21:00Z",
            ),
            _event(
                claim_id="wire",
                source_class="wire",
                event_time="2026-09-24T16:28:00Z",
                available_at="2026-09-24T16:30:00Z",
                observed_at="2026-09-24T16:32:00Z",
            ),
        ],
        mode="public_reconstruction",
    )
    assert ladder["social_led_authoritative"] is True
    assert ladder["social_lead_seconds"] == 600.0
    assert ladder["first_authoritative"]["source_class"] == "wire"


def test_conflicting_duplicate_price_timestamp_is_refused():
    with pytest.raises(s.StudyContractError):
        s.first_threshold_cross(
            _points(
                [
                    ("2026-09-24T16:32:00Z", 100.0),
                    ("2026-09-24T16:32:00Z", 100.5),
                ]
            ),
            anchor="2026-09-24T16:32:00Z",
            direction=1,
            threshold_bps=25,
            horizon_minutes=5,
        )


def test_event_vs_control_summary_keeps_missingness_visible():
    out = s.compare_to_controls([30.0, 10.0, None], [5.0, -5.0, None])
    assert out["events"]["n"] == 2
    assert out["events"]["missing"] == 1
    assert out["controls"]["n"] == 2
    assert out["delta_mean"] == 20.0
    assert out["inference"].startswith("descriptive_only")


def test_v2_first_pass_measures_pre_state_impulse_and_plus5_residual():
    out = s.repricing_first_pass(
        known_at="2026-09-24T16:15:00Z",
        causal_direction=-1,
        causal_points=_points(
            [
                ("2026-09-24T12:15:00Z", 120.0),
                ("2026-09-24T15:15:00Z", 110.0),
                ("2026-09-24T16:15:00Z", 100.0),
                ("2026-09-24T16:20:00Z", 98.0),
            ]
        ),
        response_points=_points(
            [
                ("2026-09-24T16:15:00Z", 198.0),
                ("2026-09-24T16:20:00Z", 200.0),
                ("2026-09-24T16:35:00Z", 202.0),
                ("2026-09-24T16:50:00Z", 206.0),
                ("2026-09-24T17:20:00Z", 208.0),
            ]
        ),
        benchmark_points=_points(
            [
                ("2026-09-24T16:15:00Z", 399.0),
                ("2026-09-24T16:20:00Z", 400.0),
                ("2026-09-24T16:35:00Z", 401.0),
                ("2026-09-24T16:50:00Z", 402.0),
                ("2026-09-24T17:20:00Z", 403.0),
            ]
        ),
    )
    assert out["status"] == "measured"
    assert out["causal_impulse"]["raw_return_bps"] == -200.0
    assert out["causal_impulse"]["signed_expected_direction_bps"] == 200.0
    assert out["first_impulse"]["response_return_bps"] > 0
    assert out["first_impulse"]["residual_return_bps"] > 0
    assert out["pre_event_causal"]["60m"]["raw_return_bps"] == -909.090909
    assert (
        out["response_from_impulse_end"]["30m"]["residual_return_bps"]
        == 250.0
    )


def test_v2_first_pass_pre_event_window_never_uses_future_bar():
    out = s.repricing_first_pass(
        known_at="2026-09-24T16:15:00Z",
        causal_direction=-1,
        causal_points=_points(
            [
                ("2026-09-24T15:14:00Z", 110.0),
                ("2026-09-24T15:16:00Z", 90.0),
                ("2026-09-24T16:15:00Z", 100.0),
                ("2026-09-24T16:20:00Z", 99.0),
            ]
        ),
        response_points=_points(
            [
                ("2026-09-24T16:20:00Z", 200.0),
                ("2026-09-24T16:50:00Z", 201.0),
            ]
        ),
        benchmark_points=_points(
            [
                ("2026-09-24T16:20:00Z", 400.0),
                ("2026-09-24T16:50:00Z", 401.0),
            ]
        ),
    )
    assert out["pre_event_causal"]["60m"]["start_known_at"] == (
        "2026-09-24T15:14:00Z"
    )
    assert out["pre_event_causal"]["60m"]["raw_return_bps"] == -909.090909


def test_v2_first_pass_missing_plus5_response_stays_data_gap():
    out = s.repricing_first_pass(
        known_at="2026-09-24T16:15:00Z",
        causal_direction=-1,
        causal_points=_points(
            [
                ("2026-09-24T16:15:00Z", 100.0),
                ("2026-09-24T16:20:00Z", 99.0),
            ]
        ),
        response_points=_points(
            [
                ("2026-09-24T16:30:00Z", 200.0),
                ("2026-09-24T16:50:00Z", 201.0),
            ]
        ),
        benchmark_points=_points(
            [
                ("2026-09-24T16:20:00Z", 400.0),
                ("2026-09-24T16:50:00Z", 401.0),
            ]
        ),
    )
    assert out["status"] == "data_gap"
    assert (
        out["response_from_impulse_end"]["30m"]["residual_return_bps"]
        is None
    )


def test_evidence_state_rejects_later_equity_move_without_causal_confirmation():
    out = s.classify_evidence_state(
        source_quality_resolved=True,
        causal_confirmed=False,
        cross_session_assimilated=True,
    )
    assert out["state"] == "CAUSAL_REJECTED"
    assert out["flags"]["cross_session_assimilated"] is True
    assert out["authority"]["may_trade"] is False


def test_evidence_state_conflict_dominates_positive_progression():
    out = s.classify_evidence_state(
        source_quality_resolved=True,
        causal_confirmed=True,
        first_impulse_observed=True,
        continuation_observed=True,
        source_confounded=True,
    )
    assert out["state"] == "CONFLICTED"


def test_evidence_state_keeps_data_gap_distinct_from_no_continuation():
    gap = s.classify_evidence_state(
        source_quality_resolved=True,
        causal_confirmed=True,
        data_gap=True,
    )
    no_continuation = s.classify_evidence_state(
        source_quality_resolved=True,
        causal_confirmed=True,
        first_impulse_observed=True,
        continuation_observed=False,
    )
    assert gap["state"] == "DATA_GAP"
    assert no_continuation["state"] == "NO_CONTINUATION"


def test_evidence_state_requires_causal_confirmation_before_first_impulse():
    with pytest.raises(s.StudyContractError):
        s.classify_evidence_state(
            source_quality_resolved=True,
            causal_confirmed=False,
            first_impulse_observed=True,
        )


def test_evidence_state_does_not_promote_cross_session_before_causal_resolution():
    out = s.classify_evidence_state(
        source_quality_resolved=True,
        causal_confirmed=None,
        cross_session_assimilated=True,
    )
    assert out["state"] == "SOURCE_QUALITY_RESOLVED"
    assert out["flags"]["cross_session_assimilated"] is True


def test_evidence_state_can_record_regional_no_assimilation_after_confirmation():
    out = s.classify_evidence_state(
        source_quality_resolved=True,
        causal_confirmed=True,
        cross_session_assimilated=False,
    )
    assert out["state"] == "CROSS_SESSION_NO_ASSIMILATION"
