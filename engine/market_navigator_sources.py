"""Read-only adapter to the incumbent market-state loader/calendar.

No second store, clock reconstruction or source authenticator. Deployment must supply
an existing owner-issued receipt verifier; absence is a visible capability gap. The
verifier is application-owned wiring, never a request-provided callable. This module
does not prove a production binding simply because a test provides a verifier.
"""
from __future__ import annotations

from typing import Callable, Mapping

from engine.market_navigator import Observation, Receipt, Scenario, compose, _clock
from lib.nyse_calendar import expected_last_session


def snapshot(*, subject: str, horizon: str, as_of: str,
             observations: tuple[Observation, ...] = (),
             scenarios: tuple[Scenario, ...] = (),
             state_receipt: Receipt | None = None,
             verify_state_receipt: Callable[[Mapping, Receipt], bool] | None = None,
             canonical_session_complete: bool | None = None,
             load_state: Callable[[], dict | None] | None = None) -> dict:
    """Load once, validate once, compose once. Never use file mtime as available_at."""
    cutoff = _clock(as_of)
    expected = expected_last_session(cutoff).isoformat()
    if subject != "SPY:ARCX":
        return {"schema": "market_navigator.source_adapter/v1",
                "source_admission": "unsupported_subject", "reported_state_date": None,
                "expected_daily_session_floor": expected,
                "context": compose(subject=subject, horizon=horizon, as_of=as_of,
                                   observations=observations, scenarios=scenarios),
                "production_binding_proven": False}
    if load_state is None:
        from engine.market_state import load_persisted
        load_state = load_persisted
    source_status = "unavailable"
    state = None
    try:
        state = load_state()
    except (OSError, ValueError, TypeError):
        source_status = "read_failed"
    reported_date = state.get("asof") if isinstance(state, Mapping) else None
    trusted_state = None
    if state is not None:
        if not isinstance(state, Mapping):
            source_status = "malformed"
        elif state_receipt is None:
            source_status = "receipt_missing"
        elif verify_state_receipt is None:
            source_status = "receipt_verifier_unbound"
        else:
            try:
                verified = verify_state_receipt(state, state_receipt)
            except (ValueError, TypeError, OSError):
                verified = False
            if verified is True:
                trusted_state = state
                source_status = "verified_by_bound_owner"
            else:
                source_status = "receipt_not_verified"
    context = compose(subject=subject, horizon=horizon, as_of=as_of,
        observations=observations, scenarios=scenarios, market_state=trusted_state,
        market_state_receipt=state_receipt if trusted_state is not None else None,
        expected_market_session=expected, canonical_session_complete=canonical_session_complete)
    return {"schema": "market_navigator.source_adapter/v1",
        "source_admission": source_status, "reported_state_date": reported_date,
        "expected_daily_session_floor": expected,
        "context": context, "production_binding_proven": False}
