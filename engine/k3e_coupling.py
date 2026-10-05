"""K3E A9 descriptive coupling over existing owner outputs.

This is a pure composer, not a price engine, expectation normalizer, phase
classifier, evaluator, ranker, or authority plane.  It consumes the existing
EXP-1 declared-capture inspection and MKT-1 market-response projection only at
their explicitly supported descriptive boundary.

Until an owner-qualified economically comparable expectation value exists,
revision direction, velocity, acceleration, disagreement magnitude and any
"incorporation" statistic remain unavailable.  Raw captured estimate values are
not consumed here.
"""
from __future__ import annotations

EXPECTATION_SCHEMA = "k3e.declared_capture_inspection.v1"
MARKET_SCHEMA = "price_pressure.market_response_export.v1"
SCHEMA = "k3e.descriptive_coupling.v1"


def _base() -> dict:
    return {
        "schema": SCHEMA,
        "authority": "descriptive_context_only",
        "financial_influence": False,
        "k3e_admissible": False,
        "state": "UNAVAILABLE",
        "refusals": [],
        "expectation": {
            "state": "UNAVAILABLE",
            "schema": None,
            "query_identity": None,
            "ticker": None,
            "metric": None,
            "horizon": None,
            "as_of": None,
            "period_continuity": None,
            "latest_capture_status": None,
            "last_supported_status": None,
            "latest_attempt_status": None,
            "normalized_value": None,
            "normalized_status": None,
            "normalized_rights_state": None,
            "raw_numeric_values_consumed": False,
        },
        "market": {
            "state": "UNAVAILABLE",
            "schema": None,
            "ticker": None,
            "response_model": None,
            "raw_state": "UNAVAILABLE",
            "raw_simple_return": None,
            "raw_log_return": None,
            "residual_state": "UNAVAILABLE",
            "residual_log_return": None,
            "residual_simple_equivalent": None,
            "owner_observation_steps": None,
            "session_steps": None,
            "qualification_state": None,
            "qualification_missing": [],
        },
        "coupling": {
            "status": "UNAVAILABLE",
            "revision_direction": None,
            "velocity": None,
            "acceleration": None,
            "disagreement_magnitude": None,
            "incorporation_fraction": None,
            "phase_probability": None,
        },
        "rival_explanation": {
            "code": "INSUFFICIENT_COMPONENT_EVIDENCE",
            "text": (
                "The available components do not identify a causal information-to-price "
                "mechanism."
            ),
        },
        "next_observable": {
            "code": "OWNER_QUALIFIED_COMPARABLE_EXPECTATION_CHANGE",
            "text": (
                "Obtain an owner-qualified economically comparable expectation change "
                "before computing coupling direction or speed."
            ),
        },
    }


def _expectation_projection(result: object) -> tuple[dict | None, list[str]]:
    if result is None:
        return None, []
    if not isinstance(result, dict):
        return None, ["EXPECTATION_INPUT_INVALID"]
    payload = result.get("semantic_payload")
    if not isinstance(payload, dict) or payload.get("schema") != EXPECTATION_SCHEMA:
        return None, ["EXPECTATION_SCHEMA_UNSUPPORTED"]

    baseline = payload.get("normalized_baseline")
    if not isinstance(baseline, dict):
        return None, ["EXPECTATION_BASELINE_STATE_INVALID"]
    if baseline.get("value") is not None:
        # Current accepted EXP-1 intentionally withholds normalized economics.
        # A later owner-qualified positive path must be versioned deliberately
        # rather than silently changing this composer's semantics.
        return None, ["UNQUALIFIED_NORMALIZED_VALUE_PRESENT"]

    query = payload.get("query") if isinstance(payload.get("query"), dict) else {}
    latest = (
        payload.get("latest_captured_snapshot")
        if isinstance(payload.get("latest_captured_snapshot"), dict)
        else {}
    )
    supported = (
        payload.get("last_structurally_supported_snapshot")
        if isinstance(payload.get("last_structurally_supported_snapshot"), dict)
        else {}
    )
    attempt = (
        payload.get("latest_attempt")
        if isinstance(payload.get("latest_attempt"), dict)
        else {}
    )
    state = (
        "AVAILABLE_UNQUALIFIED"
        if latest.get("status") in {"AVAILABLE", "UNESTIMABLE"}
        or supported.get("status") == "AVAILABLE"
        else "UNAVAILABLE"
    )
    return {
        "state": state,
        "schema": EXPECTATION_SCHEMA,
        "query_identity": payload.get("query_identity"),
        "ticker": query.get("ticker_compat"),
        "metric": query.get("metric"),
        "horizon": query.get("horizon_label_raw"),
        "as_of": query.get("as_of"),
        "period_continuity": payload.get("period_continuity"),
        "latest_capture_status": latest.get("status"),
        "last_supported_status": supported.get("status"),
        "latest_attempt_status": attempt.get("status"),
        "normalized_value": None,
        "normalized_status": baseline.get("status"),
        "normalized_rights_state": baseline.get("rights_state"),
        "raw_numeric_values_consumed": False,
    }, []


def _market_projection(result: object) -> tuple[dict | None, list[str]]:
    if result is None:
        return None, []
    if not isinstance(result, dict) or result.get("schema") != MARKET_SCHEMA:
        return None, ["MARKET_SCHEMA_UNSUPPORTED"]
    if (
        result.get("owner") != "engine.price_pressure"
        or result.get("tier") != "display"
        or result.get("authority") != "context_only"
    ):
        return None, ["MARKET_OWNER_ENVELOPE_UNSUPPORTED"]
    if result.get("financial_influence") is not False:
        return None, ["MARKET_AUTHORITY_UNSUPPORTED"]

    qualification = (
        result.get("qualification")
        if isinstance(result.get("qualification"), dict)
        else {}
    )
    if qualification.get("k3e_admissible") is not False:
        # This v1 composer is deliberately the current fail-closed descriptive
        # boundary.  Future qualified market receipts require an explicit schema
        # amendment and semantic review.
        return None, ["MARKET_QUALIFICATION_UNSUPPORTED"]

    raw = result.get("raw_response") if isinstance(result.get("raw_response"), dict) else {}
    residual = (
        result.get("residual_response")
        if isinstance(result.get("residual_response"), dict)
        else {}
    )
    window = result.get("window") if isinstance(result.get("window"), dict) else {}

    import math

    def valid_optional_number(value: object) -> bool:
        return value is None or (
            not isinstance(value, bool)
            and isinstance(value, (int, float))
            and math.isfinite(value)
        )

    copied_numbers = (
        raw.get("simple_return"),
        raw.get("log_return"),
        residual.get("log_residual"),
        residual.get("simple_equivalent"),
        window.get("owner_observation_steps"),
        window.get("session_steps"),
    )
    if not all(valid_optional_number(value) for value in copied_numbers):
        return None, ["MARKET_NUMERIC_INVALID"]

    return {
        "state": result.get("status") or "UNAVAILABLE",
        "schema": MARKET_SCHEMA,
        "ticker": result.get("ticker"),
        "response_model": result.get("response_model"),
        "raw_state": raw.get("state") or "UNAVAILABLE",
        "raw_simple_return": raw.get("simple_return"),
        "raw_log_return": raw.get("log_return"),
        "residual_state": residual.get("state") or "UNAVAILABLE",
        "residual_log_return": residual.get("log_residual"),
        "residual_simple_equivalent": residual.get("simple_equivalent"),
        "owner_observation_steps": window.get("owner_observation_steps"),
        "session_steps": window.get("session_steps"),
        "qualification_state": qualification.get("state"),
        "qualification_missing": list(qualification.get("missing") or []),
    }, []


def compose_descriptive_coupling(
    expectation_result: object,
    market_response: object,
) -> dict:
    """Compose owner outputs without creating missing economic semantics."""
    out = _base()
    expectation, e_refusals = _expectation_projection(expectation_result)
    market, m_refusals = _market_projection(market_response)
    out["refusals"].extend(e_refusals)
    out["refusals"].extend(m_refusals)

    if out["refusals"]:
        out["state"] = "REFUSED"
        out["coupling"]["status"] = "REFUSED"
        return out

    if expectation is not None:
        out["expectation"].update(expectation)
    if market is not None:
        out["market"].update(market)

    if expectation is None and market is None:
        return out
    if expectation is None:
        out["state"] = "PRICE_ONLY"
        out["coupling"]["status"] = "EXPECTATION_COMPONENT_UNAVAILABLE"
        out["rival_explanation"]["code"] = "EXPECTATION_COMPONENT_UNAVAILABLE"
        return out
    if market is None:
        out["state"] = "EXPECTATION_ONLY"
        out["coupling"]["status"] = "MARKET_COMPONENT_UNAVAILABLE"
        out["rival_explanation"]["code"] = "MARKET_COMPONENT_UNAVAILABLE"
        return out

    expectation_ticker = expectation.get("ticker")
    market_ticker = market.get("ticker")
    if (
        not isinstance(expectation_ticker, str)
        or not expectation_ticker.strip()
        or not isinstance(market_ticker, str)
        or not market_ticker.strip()
    ):
        out["state"] = "REFUSED"
        out["refusals"].append("SUBJECT_IDENTITY_MISSING")
        out["coupling"]["status"] = "REFUSED"
        return out
    if expectation_ticker != market_ticker:
        out["state"] = "REFUSED"
        out["refusals"].append("SUBJECT_MISMATCH")
        out["coupling"]["status"] = "REFUSED"
        return out

    out["state"] = "COMPONENTS_ONLY"
    continuity = expectation.get("period_continuity")
    if continuity == "NATIVE_PERIOD_CHANGED_NO_REVISION_INFERENCE":
        out["coupling"]["status"] = "PERIOD_CHANGED_NOT_REVISION"
    else:
        out["coupling"]["status"] = "UNAVAILABLE_NORMALIZED_EXPECTATION"

    out["rival_explanation"] = {
        "code": "TIMING_OR_OMITTED_INFORMATION_REMAINS_PLAUSIBLE",
        "text": (
            "Observed market movement may reflect information outside the captured "
            "expectation source, source-timing differences, or unrelated market forces."
        ),
    }
    return out
