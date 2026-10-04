"""Versioned read-only market-response export for K3E/MKT-1.

This module belongs to the existing price-pressure owner. It does not build a
new price panel or residual model. It projects the already-produced LSR/DRL
owner state into a small machine contract.

Subject response comes from the owner's close frame. Residual response comes
from the owner's cumulative log1p-residual frame. Exact endpoints are required;
there is no nearest-date or widened-window fallback. Missing qualification
evidence remains explicit and K3E admission stays false.

Identity, currency, source-use rights, price-basis vintage, availability clocks,
calendar receipts and residual-fit receipts are intentionally not caller
parameters here. Until their existing owners can attest them, this export is
descriptive owner context only and must not be promoted to a qualified K3E leg.
"""
from __future__ import annotations

import math

import pandas as pd

from engine.price_pressure import ENGINE_VERSION


SCHEMA = "price_pressure.market_response_export.v1"
RESPONSE_MODEL = "lsr_p0"
QUALIFICATION_MISSING = (
    "canonical_security_identity_receipt",
    "currency_receipt",
    "price_basis_vintage_receipt",
    "availability_clock_receipt",
    "source_use_receipt",
    "calendar_session_receipt",
    "residual_baseline_receipt",
)


def _as_frame(owner_state: object, key: str):
    if not isinstance(owner_state, dict):
        return None
    if key == "close":
        features = owner_state.get("f")
        if not isinstance(features, dict):
            return None
        value = features.get("close")
    else:
        value = owner_state.get(key)
    return value if isinstance(value, pd.DataFrame) else None


def _base(ticker: object, start_session: object, end_session: object) -> dict:
    return {
        "schema": SCHEMA,
        "owner": "engine.price_pressure",
        "owner_engine_version": ENGINE_VERSION,
        "response_model": RESPONSE_MODEL,
        "tier": "display",
        "authority": "context_only",
        "financial_influence": False,
        "ticker": ticker,
        "window": {
            "start_session": str(start_session),
            "end_session": str(end_session),
            "observed_session_steps": None,
        },
        "status": "UNAVAILABLE",
        "refusals": [],
        "raw_response": {
            "state": "UNAVAILABLE",
            "simple_return": None,
            "log_return": None,
            "start_close": None,
            "end_close": None,
            "price_basis": "LSR_SPLIT_REPAIRED_PANEL_NOT_A4_QUALIFIED",
            "reasons": [],
        },
        "residual_response": {
            "state": "UNAVAILABLE",
            "log_residual": None,
            "simple_equivalent": None,
            "construction": "LSR_P0_CUM_LOG1P_RESIDUAL_DELTA",
            "reasons": [],
        },
        "qualification": {
            "state": "NOT_QUALIFIED",
            "k3e_admissible": False,
            "missing": list(QUALIFICATION_MISSING),
            "canonical_security_id": None,
            "currency": None,
            "availability_clock": None,
            "source_use": "UNKNOWN",
            "adjustment_vintage": None,
        },
    }


def _finite_positive(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number <= 0:
        return None
    return number


def _finite(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _position(index: pd.Index, label: pd.Timestamp) -> int | None:
    if not index.is_unique:
        return None
    try:
        loc = index.get_loc(label)
    except KeyError:
        return None
    return int(loc) if isinstance(loc, int) else None


def export_market_response(
    owner_state: object,
    *,
    ticker: object,
    start_session: object,
    end_session: object,
) -> dict:
    """Project one exact owner window without manufacturing qualification."""
    out = _base(ticker, start_session, end_session)
    close = _as_frame(owner_state, "close")
    cum = _as_frame(owner_state, "cum")
    if close is None:
        out["refusals"].append("OWNER_STATE_INVALID")
        out["raw_response"]["reasons"].append("OWNER_CLOSE_FRAME_UNAVAILABLE")
        out["residual_response"]["reasons"].append("OWNER_RESIDUAL_FRAME_UNAVAILABLE")
        return out

    if not isinstance(ticker, str) or not ticker or ticker not in close.columns:
        out["refusals"].append("TICKER_NOT_IN_OWNER_STATE")
        out["raw_response"]["reasons"].append("TICKER_NOT_IN_OWNER_STATE")
        out["residual_response"]["reasons"].append("TICKER_NOT_IN_OWNER_STATE")
        return out

    try:
        start = pd.Timestamp(start_session)
        end = pd.Timestamp(end_session)
    except (TypeError, ValueError):
        out["refusals"].append("INVALID_WINDOW")
        return out

    start_pos = _position(close.index, start)
    end_pos = _position(close.index, end)
    if start_pos is None or end_pos is None:
        out["refusals"].append("EXACT_ENDPOINT_MISSING")
        out["raw_response"]["reasons"].append("EXACT_ENDPOINT_MISSING")
        out["residual_response"]["reasons"].append("EXACT_ENDPOINT_MISSING")
        return out
    if end_pos <= start_pos:
        out["refusals"].append("INVALID_WINDOW")
        out["raw_response"]["reasons"].append("INVALID_WINDOW")
        out["residual_response"]["reasons"].append("INVALID_WINDOW")
        return out

    out["window"] = {
        "start_session": str(start.date()),
        "end_session": str(end.date()),
        "observed_session_steps": end_pos - start_pos,
    }

    start_close = _finite_positive(close.at[start, ticker])
    end_close = _finite_positive(close.at[end, ticker])
    if start_close is None or end_close is None:
        out["raw_response"]["reasons"].append("RAW_ENDPOINT_UNAVAILABLE")
    else:
        ratio = end_close / start_close
        if math.isfinite(ratio) and ratio > 0:
            out["raw_response"].update(
                {
                    "state": "AVAILABLE_UNQUALIFIED",
                    "simple_return": ratio - 1.0,
                    "log_return": math.log(ratio),
                    "start_close": start_close,
                    "end_close": end_close,
                }
            )
        else:
            out["raw_response"]["reasons"].append("RAW_ENDPOINT_UNAVAILABLE")

    if cum is None or ticker not in cum.columns:
        out["residual_response"]["reasons"].append("OWNER_RESIDUAL_FRAME_UNAVAILABLE")
    else:
        residual_start_pos = _position(cum.index, start)
        residual_end_pos = _position(cum.index, end)
        if residual_start_pos is None or residual_end_pos is None:
            out["residual_response"]["reasons"].append("RESIDUAL_ENDPOINT_UNAVAILABLE")
        else:
            start_cum = _finite(cum.at[start, ticker])
            end_cum = _finite(cum.at[end, ticker])
            if start_cum is None or end_cum is None:
                out["residual_response"]["reasons"].append("RESIDUAL_ENDPOINT_UNAVAILABLE")
            else:
                delta = end_cum - start_cum
                simple_equivalent = math.expm1(delta)
                if math.isfinite(delta) and math.isfinite(simple_equivalent):
                    out["residual_response"].update(
                        {
                            "state": "AVAILABLE_UNQUALIFIED",
                            "log_residual": delta,
                            "simple_equivalent": simple_equivalent,
                        }
                    )
                else:
                    out["residual_response"]["reasons"].append(
                        "RESIDUAL_ENDPOINT_UNAVAILABLE"
                    )

    raw_available = out["raw_response"]["state"] == "AVAILABLE_UNQUALIFIED"
    residual_available = out["residual_response"]["state"] == "AVAILABLE_UNQUALIFIED"
    if raw_available and residual_available:
        out["status"] = "RAW_AND_RESIDUAL_CONTEXT"
    elif raw_available:
        out["status"] = "RAW_ONLY"
    elif residual_available:
        out["status"] = "RESIDUAL_ONLY"
    return out
