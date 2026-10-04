from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from scripts.research import replay_event_microstructure as replay


def _ms(ts: str) -> int:
    raw = ts.replace("Z", "+00:00")
    return int(datetime.fromisoformat(raw).timestamp() * 1000)


def _vendor_row(close_known_at: str, close: float) -> dict:
    known = datetime.fromisoformat(close_known_at.replace("Z", "+00:00"))
    start = known.timestamp() - 60.0
    return {"t": int(start * 1000), "c": close}


def _event() -> dict:
    return {
        "event_id": "evt-test",
        "event_time": "2026-09-24T16:32:00Z",
        "available_at": "2026-09-24T16:32:00Z",
        "observed_at": "2026-09-25T08:00:00Z",
    }


def test_minute_close_is_stamped_at_bar_end_not_bar_start():
    rows = [{"t": _ms("2026-09-24T16:31:00Z"), "c": 100.0}]
    points = replay.minute_close_points(rows, session=date(2026, 9, 24))
    assert points == [{"ts": "2026-09-24T16:32:00Z", "price": 100.0}]


def test_fetch_session_uses_one_day_minute_endpoint_and_no_store():
    calls = []

    def transport(path, params):
        calls.append((path, dict(params)))
        return [_vendor_row("2026-09-24T16:32:00Z", 100.0)]

    out = replay.fetch_session(
        "BRK-B",
        date(2026, 9, 24),
        transport=transport,
    )
    assert calls == [
        (
            "/v2/aggs/ticker/BRK.B/range/1/minute/2026-09-24/2026-09-24",
            {"adjusted": "true", "sort": "asc", "limit": 50000},
        )
    ]
    assert out["row_count"] == 1
    assert out["first_close_known_at"] == "2026-09-24T16:32:00Z"


def test_replay_measures_uso_to_smh_sequence_with_xle_secondary():
    fixtures = {
        "USO": [
            _vendor_row("2026-09-24T16:32:00Z", 100.0),
            _vendor_row("2026-09-24T16:34:00Z", 99.6),
            _vendor_row("2026-09-24T16:49:00Z", 99.4),
            _vendor_row("2026-09-24T17:04:00Z", 99.3),
        ],
        "SMH": [
            _vendor_row("2026-09-24T16:32:00Z", 200.0),
            _vendor_row("2026-09-24T16:35:00Z", 200.2),
            _vendor_row("2026-09-24T16:38:00Z", 200.7),
            _vendor_row("2026-09-24T16:49:00Z", 201.2),
            _vendor_row("2026-09-24T17:04:00Z", 202.0),
        ],
        "QQQ": [
            _vendor_row("2026-09-24T16:34:00Z", 400.0),
            _vendor_row("2026-09-24T16:49:00Z", 400.8),
            _vendor_row("2026-09-24T17:04:00Z", 401.0),
        ],
        "XLE": [
            _vendor_row("2026-09-24T16:32:00Z", 90.0),
            _vendor_row("2026-09-24T16:36:00Z", 89.7),
        ],
    }

    def transport(path, params):
        symbol = path.split("/")[4]
        return fixtures[symbol]

    out = replay.replay(
        event=_event(),
        session=date(2026, 9, 24),
        causal_symbol="USO",
        secondary_causal_symbol="XLE",
        response_symbol="SMH",
        benchmark_symbol="QQQ",
        mode="public_reconstruction",
        causal_threshold_bps=25,
        response_threshold_bps=25,
        transport=transport,
    )
    assert out["causal_proxy"] == {
        "symbol": "USO",
        "role": "oil_price_proxy_not_direct_crude",
    }
    assert out["study_result"]["causal"]["crossed_at"] == "2026-09-24T16:34:00Z"
    assert out["study_result"]["response"]["crossed_at"] == "2026-09-24T16:38:00Z"
    assert out["study_result"]["ordered_propagation"] is True
    assert out["study_result"]["lag_seconds"] == 240.0
    assert out["secondary_causal"]["threshold_result"]["status"] == "crossed"
    assert out["persistence"] == "none_stdout_only"
    assert out["direct_crude_status"].startswith("not_used")


def test_replay_refuses_duplicate_roles():
    with pytest.raises(replay.ReplayContractError):
        replay.replay(
            event=_event(),
            session=date(2026, 9, 24),
            causal_symbol="USO",
            response_symbol="USO",
            benchmark_symbol="QQQ",
            transport=lambda path, params: [],
        )


def test_replay_refuses_unbounded_symbol_shape():
    with pytest.raises(replay.ReplayContractError):
        replay.replay(
            event=_event(),
            session=date(2026, 9, 24),
            causal_symbol="../../USO",
            response_symbol="SMH",
            benchmark_symbol="QQQ",
            transport=lambda path, params: [],
        )


def test_conflicting_vendor_bar_close_is_refused():
    rows = [
        _vendor_row("2026-09-24T16:32:00Z", 100.0),
        _vendor_row("2026-09-24T16:32:00Z", 101.0),
    ]
    with pytest.raises(replay.ReplayContractError):
        replay.minute_close_points(rows, session=date(2026, 9, 24))


def test_cli_operational_mode_requires_historical_observed_at():
    with pytest.raises(SystemExit, match="--observed-at"):
        replay.main(
            [
                "--event-id", "evt",
                "--session", "2026-09-24",
                "--event-time", "2026-09-24T16:17:00Z",
                "--available-at", "2026-09-24T16:17:00Z",
                "--mode", "operational_pit",
            ]
        )


# ---------------------------------------------------------------------------
# Prospective cross-session capture harness
# ---------------------------------------------------------------------------

from scripts.research import capture_cross_session_transfer as capture


def _capture_admission(available_at: str, *, source_state: str = "SOURCE_RESOLVED") -> dict:
    return capture.admit_source_event(
        event_id="evt-prospective",
        event_time=available_at,
        available_at=available_at,
        observed_at=available_at,
        event_class="ceasefire_deescalation_or_escalation",
        source_state=source_state,
        source_name="wire",
        source_ref="wire:evt-prospective",
        headline="Attributed material geopolitical development",
    )


def test_capture_admission_preserves_original_and_challenger_freeze_clocks():
    development = _capture_admission("2026-09-26T11:16:23Z")
    assert development["state"] == "DEVELOPMENT_ONLY"
    assert development["primary_v1_eligible"] is False
    assert development["challenger_v1_1_eligible"] is False

    primary_only = _capture_admission("2026-09-26T12:00:00Z")
    assert primary_only["state"] == "PROSPECTIVE_V1_ONLY"
    assert primary_only["primary_v1_eligible"] is True
    assert primary_only["challenger_v1_1_eligible"] is False

    both = _capture_admission("2026-09-26T21:41:02Z")
    assert both["state"] == "PROSPECTIVE_V1_1"
    assert both["primary_v1_eligible"] is True
    assert both["challenger_v1_1_eligible"] is True
    assert both["outcome_state"] == "NOT_READ"


def test_capture_confounded_source_is_not_clean_primary():
    out = _capture_admission(
        "2026-09-26T21:41:02Z",
        source_state="SOURCE_CONFOUNDED",
    )
    assert out["primary_v1_eligible"] is True
    assert out["clean_primary_eligible"] is False


def test_capture_measure_us_refuses_pre_v1_event_before_any_transport_call():
    admission = _capture_admission("2026-09-26T11:16:23Z")
    calls = []

    def transport(path, params):
        calls.append(path)
        return []

    with pytest.raises(capture.CaptureContractError, match="predates"):
        capture.measure_us_response(admission, transport=transport)
    assert calls == []


def test_capture_measure_us_uses_only_frozen_us_symbols_and_no_hk_outcome():
    admission = _capture_admission("2026-09-26T21:41:02Z")
    calls = []
    fixtures = {
        "SPY": [
            _vendor_row("2026-09-26T21:46:02Z", 100.0),
            _vendor_row("2026-09-26T22:16:02Z", 101.0),
        ],
        "QQQ": [
            _vendor_row("2026-09-26T21:46:02Z", 200.0),
            _vendor_row("2026-09-26T22:16:02Z", 204.0),
        ],
        "SMH": [
            _vendor_row("2026-09-26T21:46:02Z", 300.0),
            _vendor_row("2026-09-26T22:16:02Z", 309.0),
        ],
    }

    def transport(path, params):
        symbol = path.split("/")[4]
        calls.append(symbol)
        return fixtures[symbol]

    out = capture.measure_us_response(admission, transport=transport)
    assert calls == ["SPY", "QQQ", "SMH"]
    assert out["primary_v1"]["return_bps"] == pytest.approx(100.0)
    assert out["challenger_v1_1"]["return_bps"] == pytest.approx(100.0)
    assert out["nuisance_baselines_bps"]["SPY"] == pytest.approx(100.0)
    assert out["nuisance_baselines_bps"]["QQQ"] == pytest.approx(200.0)
    assert out["nuisance_baselines_bps"]["SMH"] == pytest.approx(300.0)
    assert out["hk_outcome_state"] == "NOT_READ_BY_THIS_HARNESS"
    assert out["matched_control_state"] == "NOT_SELECTED_BY_THIS_HARNESS"
    assert out["persistence"] == "none_stdout_only"
    assert out["authority"]["may_trade"] is False
    assert out["authority"]["may_write_qledger"] is False
    assert out["authority"]["may_write_chronicle"] is False


def test_capture_measure_us_omits_challenger_before_amendment_clock():
    admission = _capture_admission("2026-09-26T12:00:00Z")
    fixtures = {
        symbol: [
            _vendor_row("2026-09-26T12:05:00Z", 100.0),
            _vendor_row("2026-09-26T12:35:00Z", 101.0),
        ]
        for symbol in ("SPY", "QQQ", "SMH")
    }

    def transport(path, params):
        return fixtures[path.split("/")[4]]

    out = capture.measure_us_response(admission, transport=transport)
    assert out["primary_v1"]["eligible"] is True
    assert out["challenger_v1_1"]["eligible"] is False
    assert out["challenger_v1_1"]["return_bps"] is None

def test_capture_late_confirmation_cannot_manufacture_prospective_event():
    admission = _capture_admission(
        "2026-09-26T00:26:00Z",
        source_state="SOURCE_CONFOUNDED",
    )
    out = capture.amend_source_state(
        admission,
        source_available_at="2026-09-26T22:00:00Z",
        observed_at="2026-09-26T22:01:00Z",
        source_state="SOURCE_RESOLVED",
        source_name="official",
        source_ref="official:confirmation",
        headline="Later authoritative confirmation of the already-known claim",
    )
    assert out["schema"] == capture.SCHEMA_SOURCE_AMENDMENT
    assert out["event_id"] == admission["event_id"]
    assert out["available_at"] == "2026-09-26T00:26:00Z"
    assert out["measurement_anchor_at"] == "2026-09-26T00:26:00Z"
    assert out["source_state_before"] == "SOURCE_CONFOUNDED"
    assert out["source_state_after"] == "SOURCE_RESOLVED"
    assert out["source_resolution"]["source_available_at"] == "2026-09-26T22:00:00Z"
    assert out["independent_event"] is False
    assert out["primary_v1_eligible"] is False
    assert out["challenger_v1_1_eligible"] is False
    assert out["clean_primary_eligible"] is False
    assert out["outcome_state"] == "NOT_READ"


def test_capture_source_amendment_cannot_upgrade_clean_slice():
    admission = _capture_admission(
        "2026-09-26T21:41:02Z",
        source_state="SOURCE_CONFOUNDED",
    )
    out = capture.amend_source_state(
        admission,
        source_available_at="2026-09-26T21:50:00Z",
        observed_at="2026-09-26T21:51:00Z",
        source_state="SOURCE_RESOLVED",
        source_name="official",
        source_ref="official:resolution",
        headline="Later corroboration before any target outcome is read",
    )
    assert out["primary_v1_eligible"] is True
    assert out["challenger_v1_1_eligible"] is True
    assert out["clean_primary_eligible"] is False
    assert out["measurement_anchor_at"] == admission["available_at"]


def test_capture_source_amendment_refuses_after_outcome_read():
    admission = _capture_admission("2026-09-26T21:41:02Z")
    admission["outcome_state"] = "READ"
    with pytest.raises(capture.CaptureContractError, match="after outcome read"):
        capture.amend_source_state(
            admission,
            source_available_at="2026-09-26T21:50:00Z",
            observed_at="2026-09-26T21:51:00Z",
            source_state="SOURCE_RESOLVED",
            source_name="official",
            source_ref="official:resolution",
            headline="Late source receipt",
        )


def test_capture_source_amendment_refuses_resolution_before_first_disclosure():
    admission = _capture_admission("2026-09-26T21:41:02Z")
    with pytest.raises(capture.CaptureContractError, match="cannot predate"):
        capture.amend_source_state(
            admission,
            source_available_at="2026-09-26T21:40:00Z",
            observed_at="2026-09-26T21:40:30Z",
            source_state="SOURCE_RESOLVED",
            source_name="official",
            source_ref="official:resolution",
            headline="Impossible earlier resolution",
        )

def test_capture_freeze_controls_reuses_exact_clock_and_counts_excluded_sessions():
    admission = _capture_admission("2026-09-29T15:17:00Z")
    controls = capture.freeze_matched_controls(
        admission,
        observed_session_dates=[
            "2026-09-24",
            "2026-09-25",
            "2026-09-28",
            "2026-09-29",
            "2026-09-30",
            "2026-10-01",
            "2026-10-02",
            "2026-10-05",
        ],
        admitted_event_dates=[
            "2026-09-29",
            "2026-09-30",
            "2026-10-01",
        ],
        source_coverage_complete_through="2026-10-03T00:00:00Z",
    )
    assert controls["state"] == "COMPLETE"
    assert controls["prior"] == {
        "status": "SELECTED",
        "control_date": "2026-09-28",
        "session_distance": 1,
        "control_anchor_at": "2026-09-28T15:17:00Z",
    }
    assert controls["next"] == {
        "status": "SELECTED",
        "control_date": "2026-10-02",
        "session_distance": 3,
        "control_anchor_at": "2026-10-02T15:17:00Z",
    }
    assert controls["outcome_state"] == "NOT_READ"
    assert controls["selection_law"]["return_based_replacement_allowed"] is False


def test_capture_freeze_controls_keeps_next_pending_until_source_coverage_catches_up():
    admission = _capture_admission("2026-09-29T15:17:00Z")
    controls = capture.freeze_matched_controls(
        admission,
        observed_session_dates=[
            "2026-09-28",
            "2026-09-29",
            "2026-09-30",
            "2026-10-01",
        ],
        admitted_event_dates=["2026-09-29"],
        source_coverage_complete_through="2026-09-30T00:00:00Z",
    )
    assert controls["prior"]["status"] == "SELECTED"
    assert controls["next"]["status"] == "PENDING_OBSERVED_SESSION"
    assert controls["next"]["control_date"] is None
    assert controls["state"] == "PENDING"


def test_capture_freeze_controls_returns_data_gap_after_ten_excluded_next_sessions():
    admission = _capture_admission("2026-09-29T15:17:00Z")
    sessions = [
        "2026-09-28",
        "2026-09-29",
        "2026-09-30",
        "2026-10-01",
        "2026-10-02",
        "2026-10-05",
        "2026-10-06",
        "2026-10-07",
        "2026-10-08",
        "2026-10-09",
        "2026-10-12",
        "2026-10-13",
    ]
    excluded_next = sessions[2:12]
    controls = capture.freeze_matched_controls(
        admission,
        observed_session_dates=sessions,
        admitted_event_dates=["2026-09-29", *excluded_next],
        source_coverage_complete_through="2026-10-14T00:00:00Z",
    )
    assert controls["next"]["status"] == "DATA_GAP"
    assert controls["next"]["control_date"] is None


def test_capture_measure_control_us_uses_frozen_control_date_and_exact_clock_only():
    admission = _capture_admission("2026-09-29T15:17:00Z")
    controls = capture.freeze_matched_controls(
        admission,
        observed_session_dates=[
            "2026-09-28",
            "2026-09-29",
            "2026-09-30",
        ],
        admitted_event_dates=["2026-09-29"],
        source_coverage_complete_through="2026-10-01T00:00:00Z",
    )
    calls = []
    fixtures = {
        "SPY": [
            _vendor_row("2026-09-28T15:22:00Z", 100.0),
            _vendor_row("2026-09-28T15:52:00Z", 101.0),
        ],
        "QQQ": [
            _vendor_row("2026-09-28T15:22:00Z", 200.0),
            _vendor_row("2026-09-28T15:52:00Z", 204.0),
        ],
        "SMH": [
            _vendor_row("2026-09-28T15:22:00Z", 300.0),
            _vendor_row("2026-09-28T15:52:00Z", 309.0),
        ],
    }

    def transport(path, params):
        symbol = path.split("/")[4]
        calls.append((symbol, path))
        return fixtures[symbol]

    out = capture.measure_control_us_response(
        admission,
        controls,
        side="prior",
        transport=transport,
    )
    assert [symbol for symbol, _ in calls] == ["SPY", "QQQ", "SMH"]
    assert all("/2026-09-28/2026-09-28" in path for _, path in calls)
    assert out["control_anchor_at"] == "2026-09-28T15:17:00Z"
    assert out["primary_v1"]["return_bps"] == pytest.approx(100.0)
    assert out["challenger_v1_1"]["return_bps"] == pytest.approx(100.0)
    assert out["hk_outcome_state"] == "NOT_READ_BY_THIS_HARNESS"


def test_capture_measure_control_us_refuses_pending_side_before_transport():
    admission = _capture_admission("2026-09-29T15:17:00Z")
    controls = capture.freeze_matched_controls(
        admission,
        observed_session_dates=["2026-09-28", "2026-09-29"],
        admitted_event_dates=["2026-09-29"],
        source_coverage_complete_through="2026-09-30T00:00:00Z",
    )
    calls = []

    def transport(path, params):
        calls.append(path)
        return []

    with pytest.raises(capture.CaptureContractError, match="not frozen/selected"):
        capture.measure_control_us_response(
            admission,
            controls,
            side="next",
            transport=transport,
        )
    assert calls == []

def _minimal_event_us_measurement(admission):
    return {
        "schema": capture.SCHEMA_US,
        "event_id": admission["event_id"],
        "available_at": admission["available_at"],
        "hk_outcome_state": "NOT_READ_BY_THIS_HARNESS",
    }


def _minimal_control_us_measurement(admission, controls, side):
    selected = controls[side]
    return {
        "schema": capture.SCHEMA_CONTROL_US,
        "event_id": admission["event_id"],
        "control_side": side,
        "control_date": selected["control_date"],
        "control_anchor_at": selected["control_anchor_at"],
        "hk_outcome_state": "NOT_READ_BY_THIS_HARNESS",
    }


def test_capture_hk_gate_refuses_pending_next_control():
    admission = _capture_admission("2026-09-29T15:17:00Z")
    controls = capture.freeze_matched_controls(
        admission,
        observed_session_dates=["2026-09-28", "2026-09-29"],
        admitted_event_dates=["2026-09-29"],
        source_coverage_complete_through="2026-09-30T00:00:00Z",
    )
    with pytest.raises(capture.CaptureContractError, match="still pending"):
        capture.gate_hk_outcome_read(
            admission,
            controls,
            _minimal_event_us_measurement(admission),
            prior_control_measurement=_minimal_control_us_measurement(
                admission, controls, "prior"
            ),
        )


def test_capture_hk_gate_requires_every_selected_control_measurement():
    admission = _capture_admission("2026-09-29T15:17:00Z")
    controls = capture.freeze_matched_controls(
        admission,
        observed_session_dates=["2026-09-28", "2026-09-29", "2026-09-30"],
        admitted_event_dates=["2026-09-29"],
        source_coverage_complete_through="2026-10-01T00:00:00Z",
    )
    with pytest.raises(capture.CaptureContractError, match="next selected control measurement"):
        capture.gate_hk_outcome_read(
            admission,
            controls,
            _minimal_event_us_measurement(admission),
            prior_control_measurement=_minimal_control_us_measurement(
                admission, controls, "prior"
            ),
        )


def test_capture_hk_gate_accepts_complete_pre_outcome_receipts():
    admission = _capture_admission("2026-09-29T15:17:00Z")
    controls = capture.freeze_matched_controls(
        admission,
        observed_session_dates=["2026-09-28", "2026-09-29", "2026-09-30"],
        admitted_event_dates=["2026-09-29"],
        source_coverage_complete_through="2026-10-01T00:00:00Z",
    )
    out = capture.gate_hk_outcome_read(
        admission,
        controls,
        _minimal_event_us_measurement(admission),
        prior_control_measurement=_minimal_control_us_measurement(
            admission, controls, "prior"
        ),
        next_control_measurement=_minimal_control_us_measurement(
            admission, controls, "next"
        ),
    )
    assert out["schema"] == capture.SCHEMA_HK_GATE
    assert out["state"] == "READY_FOR_RESEARCH_HK_OUTCOME_READ"
    assert out["research_hk_outcome_read_ready"] is True
    assert out["hk_outcome_state"] == "NOT_READ"
    assert out["controls"]["prior"]["measurement_present"] is True
    assert out["controls"]["next"]["measurement_present"] is True


def test_capture_hk_gate_accepts_terminal_control_data_gap_without_fake_receipt():
    admission = _capture_admission("2026-09-29T15:17:00Z")
    sessions = [
        "2026-09-28",
        "2026-09-29",
        "2026-09-30",
        "2026-10-01",
        "2026-10-02",
        "2026-10-05",
        "2026-10-06",
        "2026-10-07",
        "2026-10-08",
        "2026-10-09",
        "2026-10-12",
        "2026-10-13",
    ]
    controls = capture.freeze_matched_controls(
        admission,
        observed_session_dates=sessions,
        admitted_event_dates=["2026-09-29", *sessions[2:12]],
        source_coverage_complete_through="2026-10-14T00:00:00Z",
    )
    out = capture.gate_hk_outcome_read(
        admission,
        controls,
        _minimal_event_us_measurement(admission),
        prior_control_measurement=_minimal_control_us_measurement(
            admission, controls, "prior"
        ),
    )
    assert out["controls"]["next"] == {
        "status": "DATA_GAP",
        "control_date": None,
        "measurement_present": False,
    }


def test_capture_hk_gate_rejects_wrong_control_clock():
    admission = _capture_admission("2026-09-29T15:17:00Z")
    controls = capture.freeze_matched_controls(
        admission,
        observed_session_dates=["2026-09-28", "2026-09-29", "2026-09-30"],
        admitted_event_dates=["2026-09-29"],
        source_coverage_complete_through="2026-10-01T00:00:00Z",
    )
    prior = _minimal_control_us_measurement(admission, controls, "prior")
    prior["control_anchor_at"] = "2026-09-28T15:18:00Z"
    with pytest.raises(capture.CaptureContractError, match="clock mismatch"):
        capture.gate_hk_outcome_read(
            admission,
            controls,
            _minimal_event_us_measurement(admission),
            prior_control_measurement=prior,
            next_control_measurement=_minimal_control_us_measurement(
                admission, controls, "next"
            ),
        )

def _full_measurement(event_id, available_at, primary, challenger, *, challenger_eligible=True):
    return {
        "schema": capture.SCHEMA_US,
        "event_id": event_id,
        "available_at": available_at,
        "primary_v1": {"return_bps": primary, "eligible": True},
        "challenger_v1_1": {
            "return_bps": challenger,
            "eligible": challenger_eligible,
        },
        "hk_outcome_state": "NOT_READ_BY_THIS_HARNESS",
    }


def _full_control_measurement(admission, controls, side, primary, challenger):
    selected = controls[side]
    return {
        "schema": capture.SCHEMA_CONTROL_US,
        "event_id": admission["event_id"],
        "control_side": side,
        "control_date": selected["control_date"],
        "control_anchor_at": selected["control_anchor_at"],
        "primary_v1": {"return_bps": primary, "eligible": True},
        "challenger_v1_1": {
            "return_bps": challenger,
            "eligible": admission["challenger_v1_1_eligible"],
        },
        "hk_outcome_state": "NOT_READ_BY_THIS_HARNESS",
    }


def test_capture_score_hsi_refuses_pending_before_transport_call():
    admission = _capture_admission("2026-09-29T15:17:00Z")
    controls = capture.freeze_matched_controls(
        admission,
        observed_session_dates=["2026-09-28", "2026-09-29"],
        admitted_event_dates=["2026-09-29"],
        source_coverage_complete_through="2026-09-30T00:00:00Z",
    )
    calls = []

    def transport(start, end):
        calls.append((start, end))
        return []

    with pytest.raises(capture.CaptureContractError, match="still pending"):
        capture.score_hsi_outcome(
            admission,
            controls,
            _full_measurement(
                admission["event_id"],
                admission["available_at"],
                100.0,
                50.0,
            ),
            prior_control_measurement=_full_control_measurement(
                admission, controls, "prior", -100.0, -50.0
            ),
            transport=transport,
        )
    assert calls == []


def test_capture_score_hsi_measures_event_and_selected_controls_after_gate():
    admission = _capture_admission("2026-09-29T15:17:00Z")
    controls = capture.freeze_matched_controls(
        admission,
        observed_session_dates=["2026-09-28", "2026-09-29", "2026-09-30"],
        admitted_event_dates=["2026-09-29"],
        source_coverage_complete_through="2026-10-01T00:00:00Z",
    )
    event_us = _full_measurement(
        admission["event_id"],
        admission["available_at"],
        -120.0,
        -60.0,
    )
    prior_us = _full_control_measurement(
        admission, controls, "prior", 80.0, -20.0
    )
    next_us = _full_control_measurement(
        admission, controls, "next", 40.0, 25.0
    )
    calls = []

    def transport(start, end):
        calls.append((start, end))
        return [
            {"date": "2026-09-28", "open": 995.0, "close": 1000.0},
            {"date": "2026-09-29", "open": 1010.0, "close": 1020.0},
            {"date": "2026-09-30", "open": 1000.0, "close": 980.0},
            {"date": "2026-10-01", "open": 990.0, "close": 992.0},
        ]

    out = capture.score_hsi_outcome(
        admission,
        controls,
        event_us,
        prior_control_measurement=prior_us,
        next_control_measurement=next_us,
        transport=transport,
    )
    assert len(calls) == 1
    assert out["schema"] == capture.SCHEMA_HK_SCORE
    assert out["event"]["hsi"]["gap_bps"] == pytest.approx(
        (1000.0 / 1020.0 - 1.0) * 10_000.0
    )
    assert out["event"]["primary_v1"]["sign_agreement"] is True
    assert out["event"]["challenger_v1_1"]["sign_agreement"] is True
    assert out["controls"]["prior"]["hsi"]["gap_bps"] == pytest.approx(100.0)
    assert out["controls"]["prior"]["primary_v1"]["sign_agreement"] is True
    assert out["controls"]["prior"]["challenger_v1_1"]["sign_agreement"] is False
    assert out["controls"]["next"]["hsi"]["gap_bps"] == pytest.approx(
        (990.0 / 980.0 - 1.0) * 10_000.0
    )
    assert out["pooled_claim_allowed"] is False
    assert out["product_or_trading_authority"] is False
    assert out["persistence"] == "none_stdout_only"


def test_capture_score_hsi_keeps_missing_anchor_as_data_gap():
    admission = _capture_admission("2026-09-29T15:17:00Z")
    controls = capture.freeze_matched_controls(
        admission,
        observed_session_dates=["2026-09-28", "2026-09-29", "2026-09-30"],
        admitted_event_dates=["2026-09-29"],
        source_coverage_complete_through="2026-10-01T00:00:00Z",
    )
    event_us = _full_measurement(
        admission["event_id"],
        admission["available_at"],
        100.0,
        50.0,
    )
    prior_us = _full_control_measurement(
        admission, controls, "prior", 80.0, 20.0
    )
    next_us = _full_control_measurement(
        admission, controls, "next", 40.0, 25.0
    )

    def transport(start, end):
        return [
            {"date": "2026-09-28", "open": 995.0, "close": 1000.0},
            {"date": "2026-09-30", "open": 1000.0, "close": 980.0},
            {"date": "2026-10-01", "open": 990.0, "close": 992.0},
        ]

    out = capture.score_hsi_outcome(
        admission,
        controls,
        event_us,
        prior_control_measurement=prior_us,
        next_control_measurement=next_us,
        transport=transport,
    )
    assert out["event"]["hsi"]["status"] == "DATA_GAP"
    assert out["event"]["hsi"]["reason"] == "missing_anchor_close"
    assert out["event"]["primary_v1"]["sign_agreement"] is None


def test_capture_score_hsi_rejects_conflicting_duplicate_ohlc():
    admission = _capture_admission("2026-09-29T15:17:00Z")
    controls = capture.freeze_matched_controls(
        admission,
        observed_session_dates=["2026-09-28", "2026-09-29", "2026-09-30"],
        admitted_event_dates=["2026-09-29"],
        source_coverage_complete_through="2026-10-01T00:00:00Z",
    )
    event_us = _full_measurement(
        admission["event_id"],
        admission["available_at"],
        100.0,
        50.0,
    )
    prior_us = _full_control_measurement(
        admission, controls, "prior", 80.0, 20.0
    )
    next_us = _full_control_measurement(
        admission, controls, "next", 40.0, 25.0
    )

    def transport(start, end):
        return [
            {"date": "2026-09-28", "open": 995.0, "close": 1000.0},
            {"date": "2026-09-28", "open": 996.0, "close": 1000.0},
        ]

    with pytest.raises(capture.CaptureContractError, match="conflicting HSI OHLC"):
        capture.score_hsi_outcome(
            admission,
            controls,
            event_us,
            prior_control_measurement=prior_us,
            next_control_measurement=next_us,
            transport=transport,
        )

def test_capture_freeze_controls_does_not_certify_partial_cutoff_day():
    admission = _capture_admission("2026-09-29T15:17:00Z")
    kwargs = {
        "admission": admission,
        "observed_session_dates": [
            "2026-09-28",
            "2026-09-29",
            "2026-09-30",
            "2026-10-01",
            "2026-10-02",
        ],
        "admitted_event_dates": [
            "2026-09-29",
            "2026-09-30",
            "2026-10-01",
        ],
    }
    partial = capture.freeze_matched_controls(
        **kwargs,
        source_coverage_complete_through="2026-10-02T18:00:00Z",
    )
    assert partial["source_coverage_complete_through"] == "2026-10-02T18:00:00Z"
    assert partial["source_coverage_certified_calendar_through"] == "2026-10-01"
    assert partial["next"]["status"] == "PENDING_OBSERVED_SESSION"
    assert partial["next"]["control_date"] is None

    complete = capture.freeze_matched_controls(
        **kwargs,
        source_coverage_complete_through="2026-10-03T00:00:00Z",
    )
    assert complete["source_coverage_certified_calendar_through"] == "2026-10-02"
    assert complete["next"]["status"] == "SELECTED"
    assert complete["next"]["control_date"] == "2026-10-02"


def test_capture_freeze_controls_requires_full_event_date_source_coverage():
    admission = _capture_admission("2026-09-29T15:17:00Z")
    with pytest.raises(capture.CaptureContractError, match="full admitted event date"):
        capture.freeze_matched_controls(
            admission,
            observed_session_dates=["2026-09-28", "2026-09-29"],
            admitted_event_dates=["2026-09-29"],
            source_coverage_complete_through="2026-09-29T23:59:59Z",
        )

