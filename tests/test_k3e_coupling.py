from __future__ import annotations

from engine.k3e_coupling import compose_descriptive_coupling


def _expectation(*, period_continuity="SAME_NATIVE_PERIOD", baseline_status="UNESTIMABLE"):
    return {
        "semantic_payload": {
            "schema": "k3e.declared_capture_inspection.v1",
            "query_identity": "q" * 64,
            "query": {
                "provider": "yfinance",
                "ticker_compat": "AAPL",
                "metric": "EPS",
                "horizon_label_raw": "+1q",
                "as_of": "2026-10-01T12:00:00Z",
            },
            "latest_captured_snapshot": {
                "status": "AVAILABLE",
                "snapshot": {
                    "selected_observation": {
                        "observation_id": "obs-latest",
                        "value": 9.99,
                        "period_end": "2026-12-31",
                    },
                    "derived_capture_available_at": "2026-10-01T11:59:00Z",
                    "structurally_supported": True,
                    "evidence_use": "RAW_CAPTURE_INSPECTION_ONLY",
                },
            },
            "last_structurally_supported_snapshot": {
                "status": "AVAILABLE",
                "snapshot": {
                    "selected_observation": {
                        "observation_id": "obs-supported",
                        "value": 8.88,
                        "period_end": "2026-12-31",
                    },
                    "derived_capture_available_at": "2026-09-30T11:59:00Z",
                    "structurally_supported": True,
                    "evidence_use": "RAW_CAPTURE_INSPECTION_ONLY",
                },
            },
            "latest_attempt": {"status": "AVAILABLE", "snapshot": {"status": "success"}},
            "period_continuity": period_continuity,
            "normalized_baseline": {
                "value": None,
                "status": baseline_status,
                "rights_state": "UNKNOWN",
                "reasons": [
                    "NORMALIZED_CONSUMER_ADMISSION_NOT_GRANTED",
                    "SOURCE_USE_RIGHTS_UNKNOWN",
                ],
            },
        },
        "semantic_digest": "e" * 64,
    }


def _market(*, status="RAW_AND_RESIDUAL_CONTEXT"):
    raw_available = status in {"RAW_AND_RESIDUAL_CONTEXT", "RAW_ONLY"}
    residual_available = status in {"RAW_AND_RESIDUAL_CONTEXT", "RESIDUAL_ONLY"}
    return {
        "schema": "price_pressure.market_response_export.v1",
        "owner": "engine.price_pressure",
        "response_model": "lsr_p0",
        "tier": "display",
        "authority": "context_only",
        "financial_influence": False,
        "ticker": "AAPL",
        "window": {
            "start_session": "2026-09-29",
            "end_session": "2026-10-01",
            "owner_observation_steps": 2,
            "session_steps": None,
        },
        "status": status,
        "raw_response": {
            "state": "AVAILABLE_UNQUALIFIED" if raw_available else "UNAVAILABLE",
            "simple_return": 0.10 if raw_available else None,
            "log_return": 0.0953101798 if raw_available else None,
        },
        "residual_response": {
            "state": "AVAILABLE_UNQUALIFIED" if residual_available else "UNAVAILABLE",
            "log_residual": 0.05 if residual_available else None,
            "simple_equivalent": 0.051271096 if residual_available else None,
        },
        "qualification": {
            "state": "NOT_QUALIFIED",
            "k3e_admissible": False,
            "missing": [
                "canonical_security_identity_receipt",
                "currency_receipt",
                "price_basis_vintage_receipt",
                "availability_clock_receipt",
                "source_use_receipt",
                "calendar_session_receipt",
                "residual_baseline_receipt",
            ],
        },
    }


def test_components_only_never_turn_raw_capture_values_into_revision_or_incorporation():
    out = compose_descriptive_coupling(_expectation(), _market())

    assert out["schema"] == "k3e.descriptive_coupling.v1"
    assert out["authority"] == "descriptive_context_only"
    assert out["financial_influence"] is False
    assert out["k3e_admissible"] is False
    assert out["state"] == "COMPONENTS_ONLY"

    assert out["expectation"]["normalized_value"] is None
    assert out["expectation"]["raw_numeric_values_consumed"] is False
    assert out["market"]["raw_simple_return"] == 0.10
    assert out["market"]["residual_log_return"] == 0.05

    coupling = out["coupling"]
    assert coupling["revision_direction"] is None
    assert coupling["velocity"] is None
    assert coupling["acceleration"] is None
    assert coupling["disagreement_magnitude"] is None
    assert coupling["incorporation_fraction"] is None
    assert coupling["phase_probability"] is None
    assert coupling["status"] == "UNAVAILABLE_NORMALIZED_EXPECTATION"

    assert out["rival_explanation"]["code"] == "TIMING_OR_OMITTED_INFORMATION_REMAINS_PLAUSIBLE"
    assert out["next_observable"]["code"] == "OWNER_QUALIFIED_COMPARABLE_EXPECTATION_CHANGE"


def test_period_rollover_is_not_called_revision():
    out = compose_descriptive_coupling(
        _expectation(period_continuity="NATIVE_PERIOD_CHANGED_NO_REVISION_INFERENCE"),
        _market(),
    )

    assert out["expectation"]["period_continuity"] == "NATIVE_PERIOD_CHANGED_NO_REVISION_INFERENCE"
    assert out["coupling"]["status"] == "PERIOD_CHANGED_NOT_REVISION"
    assert out["coupling"]["revision_direction"] is None


def test_price_only_preserves_market_context_and_missing_expectation():
    out = compose_descriptive_coupling(None, _market(status="RAW_ONLY"))

    assert out["state"] == "PRICE_ONLY"
    assert out["expectation"]["state"] == "UNAVAILABLE"
    assert out["market"]["state"] == "RAW_ONLY"
    assert out["coupling"]["status"] == "EXPECTATION_COMPONENT_UNAVAILABLE"
    assert out["market"]["raw_simple_return"] == 0.10
    assert out["k3e_admissible"] is False


def test_expectation_only_preserves_capture_state_and_missing_market():
    out = compose_descriptive_coupling(_expectation(), None)

    assert out["state"] == "EXPECTATION_ONLY"
    assert out["expectation"]["state"] == "AVAILABLE_UNQUALIFIED"
    assert out["market"]["state"] == "UNAVAILABLE"
    assert out["coupling"]["status"] == "MARKET_COMPONENT_UNAVAILABLE"
    assert out["coupling"]["velocity"] is None


def test_wrong_component_schema_fails_closed():
    bad_expectation = _expectation()
    bad_expectation["semantic_payload"]["schema"] = "other.schema/v9"
    out = compose_descriptive_coupling(bad_expectation, _market())

    assert out["state"] == "REFUSED"
    assert "EXPECTATION_SCHEMA_UNSUPPORTED" in out["refusals"]
    assert out["k3e_admissible"] is False


def test_non_null_unqualified_baseline_does_not_unlock_math():
    expectation = _expectation(baseline_status="AVAILABLE")
    expectation["semantic_payload"]["normalized_baseline"]["value"] = 12.34

    out = compose_descriptive_coupling(expectation, _market())

    assert out["state"] == "REFUSED"
    assert "UNQUALIFIED_NORMALIZED_VALUE_PRESENT" in out["refusals"]
    assert out["coupling"]["incorporation_fraction"] is None
    assert out["financial_influence"] is False


def test_subject_mismatch_refuses_cross_security_composition():
    market = _market()
    market["ticker"] = "MSFT"
    out = compose_descriptive_coupling(_expectation(), market)

    assert out["state"] == "REFUSED"
    assert "SUBJECT_MISMATCH" in out["refusals"]
    assert out["coupling"]["incorporation_fraction"] is None


def test_output_is_strict_json_serializable():
    import json

    out = compose_descriptive_coupling(_expectation(), _market())
    encoded = json.dumps(out, allow_nan=False, sort_keys=True)
    assert "NaN" not in encoded
    assert "Infinity" not in encoded


def test_two_component_composition_refuses_missing_expectation_subject():
    expectation = _expectation()
    expectation["semantic_payload"]["query"]["ticker_compat"] = None

    out = compose_descriptive_coupling(expectation, _market())

    assert out["state"] == "REFUSED"
    assert "SUBJECT_IDENTITY_MISSING" in out["refusals"]
    assert out["coupling"]["status"] == "REFUSED"


def test_two_component_composition_refuses_missing_market_subject():
    market = _market()
    market["ticker"] = None

    out = compose_descriptive_coupling(_expectation(), market)

    assert out["state"] == "REFUSED"
    assert "SUBJECT_IDENTITY_MISSING" in out["refusals"]
    assert out["coupling"]["status"] == "REFUSED"


def test_market_projection_requires_exact_incumbent_owner_envelope():
    for field, value in [
        ("owner", "forged.owner"),
        ("tier", "production"),
        ("authority", "rank_and_trade"),
    ]:
        market = _market()
        market[field] = value

        out = compose_descriptive_coupling(_expectation(), market)

        assert out["state"] == "REFUSED"
        assert "MARKET_OWNER_ENVELOPE_UNSUPPORTED" in out["refusals"]
        assert out["market"]["raw_simple_return"] is None


def test_market_projection_refuses_nonfinite_or_boolean_numeric_values():
    import math

    mutations = [
        ("raw_response", "simple_return", float("nan")),
        ("raw_response", "log_return", float("inf")),
        ("residual_response", "log_residual", float("-inf")),
        ("residual_response", "simple_equivalent", True),
        ("window", "owner_observation_steps", True),
    ]
    for block, field, value in mutations:
        market = _market()
        market[block][field] = value

        out = compose_descriptive_coupling(_expectation(), market)

        assert out["state"] == "REFUSED"
        assert "MARKET_NUMERIC_INVALID" in out["refusals"]
        assert out["coupling"]["status"] == "REFUSED"
        assert out["market"]["raw_simple_return"] is None
        assert out["market"]["residual_log_return"] is None

        # Refused output itself remains strict JSON.
        encoded = __import__("json").dumps(out, allow_nan=False, sort_keys=True)
        assert "NaN" not in encoded
        assert "Infinity" not in encoded
