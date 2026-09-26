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
