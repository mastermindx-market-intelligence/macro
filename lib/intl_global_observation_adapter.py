"""Adapter from the incumbent intl qualification output to the observation contract.

Maps engine.intl_inputs.qualify_return_records receipts (over a
build_return_records envelope built from the same frame) into
engine.intl_global_observation.build_observation records. The incumbent
qualifier stays the authority: this adapter can keep or withhold a value,
never upgrade one — an observation is qualified only when its incumbent
receipt is. The provider's real publication instant is not observed, so the
collector's checked_at bounds source_publication from above (upper_bound)
while the same instant is the exact ingestion clock. No input is mutated.
"""
from __future__ import annotations

import pandas as pd

from engine.intl_global_observation import (
    LEGACY_MARKET_TO_UNIVERSE_ID,
    ObservationError,
    build_observation,
    fx_return_from_closes,
)

_BASIS_LEG = {"local": "local", "usd_unhedged": "usd", "usd_hedged": "usd"}


def _text(value) -> str | None:
    return value if (type(value) is str and value.strip()) else None


def _window_of(record: dict, leg: str) -> dict | None:
    metric = record.get(leg)
    window = metric.get("window") if isinstance(metric, dict) else None
    return window if isinstance(window, dict) else None


def _fx_close(closes: pd.DataFrame, fx_id, timestamp_text) -> float | None:
    """Exact fx close at a window endpoint timestamp; None when unavailable."""
    if not _text(timestamp_text) or not isinstance(fx_id, str):
        return None
    if not isinstance(closes, pd.DataFrame) or fx_id not in closes.columns:
        return None
    try:
        moment = pd.Timestamp(timestamp_text)
        close = closes.at[moment, fx_id]
        if close is None or pd.isna(close):
            return None
        close = float(close)
    except (KeyError, IndexError, TypeError, ValueError, OverflowError):
        return None
    return close if close > 0 else None


def _fx_pct(closes, fx_id, orientation, window) -> float | None:
    """fx return in percent from the window's endpoint closes, or None."""
    endpoints = window.get("endpoint_observations") if isinstance(window, dict) else None
    endpoints = endpoints if isinstance(endpoints, dict) else {}
    try:
        start = _fx_close(closes, fx_id, endpoints.get("fx_start"))
        end = _fx_close(closes, fx_id, endpoints.get("fx_end"))
        if start is None or end is None:
            return None
        return 100.0 * fx_return_from_closes(start, end, orientation)
    except (ObservationError, ValueError):
        return None


def _evidence_ref(source_evidence, index_id, fx_id, leg) -> str | None:
    """Joined decision_refs of every required series witness, or None."""
    required = [index_id] if leg == "local" else [index_id, fx_id]
    references = []
    for series_id in required:
        if not isinstance(series_id, str):
            return None
        entry = next((item for item in source_evidence
                      if isinstance(item, dict) and item.get("series_id") == series_id),
                     None)
        reference = entry.get("decision_ref") if entry else None
        if not _text(reference):
            return None
        references.append(reference)
    return "|".join(references)


def _incumbent_receipt(qualification, market_id, horizon, currency_basis, leg):
    """The receipt bound to this exact market/horizon/basis/leg, else None.

    A hedged basis never borrows an usd_unhedged receipt: the binding's
    currency_basis must equal the requested basis exactly.
    """
    if not isinstance(qualification, dict):
        return None
    receipts = qualification.get("qualifications")
    if not isinstance(receipts, list):
        return None
    for receipt in receipts:
        if not isinstance(receipt, dict):
            continue
        binding = receipt.get("binding")
        if not isinstance(binding, dict):
            continue
        if (binding.get("market_id") == market_id
                and binding.get("horizon") == horizon
                and binding.get("currency_basis") == currency_basis
                and binding.get("leg") == leg):
            return receipt
    return None


def _rights_view(rights) -> dict | None:
    if not isinstance(rights, dict) or rights.get("status") != "confirmed":
        return None
    return {"decision_ref": rights.get("decision_ref"), "scope": rights.get("scope")}


def observations_from_qualification(records: dict, qualification: dict, *,
                                    closes: pd.DataFrame,
                                    source_evidence: list[dict],
                                    run_status_source: dict,
                                    evaluated_at: str,
                                    rights: dict,
                                    currency_basis: str) -> list[dict]:
    """One contract observation per (record market_id, horizon).

    `qualification` is the incumbent qualify_return_records output for the
    SAME currency_basis (for usd_hedged pass the usd_unhedged output or
    {"qualifications": []} — every observation then abstains
    basis_unsupported and no hedged observation borrows an unhedged
    incumbent). `closes` is the frame the records were built from;
    `source_evidence` the build_eod_inputs evidence list; `run_status_source`
    the run_status.json sources.intl_prices dict; `rights` the config.yml
    intl.eod_publication grant.
    """
    if not isinstance(records, dict):
        return []
    entries = records.get("records")
    if not isinstance(entries, list):
        return []
    leg = _BASIS_LEG.get(currency_basis, "usd")
    checked_at = None
    if isinstance(run_status_source, dict):
        checked_at = _text(run_status_source.get("checked_at"))
    observations = []
    for record in entries:
        if not isinstance(record, dict):
            continue
        market_id = record.get("market_id")
        horizon = record.get("horizon")
        index_id = record.get("index_id")
        fx_id = record.get("fx_id")
        receipt = _incumbent_receipt(qualification, market_id, horizon,
                                     currency_basis, leg)
        binding = receipt.get("binding") if receipt is not None else None
        incumbent = None
        if receipt is not None:
            incumbent = {
                "quality": receipt.get("quality"),
                "reason": receipt.get("reason"),
                "decision_ref": receipt.get("decision_ref"),
            }
        window = _window_of(record, leg)
        window_start = _text(window.get("start")) if window else None
        window_end = _text(window.get("end")) if window else None

        local_metric = record.get("local")
        usd_metric = record.get("usd")
        local_pct = local_metric.get("value") if isinstance(local_metric, dict) else None
        usd_pct = usd_metric.get("value") if isinstance(usd_metric, dict) else None
        fx_pct = _fx_pct(closes, fx_id, record.get("fx_quote_orientation"), window)

        clocks = {
            "observation": {"at": window_end, "precision": "session_date"},
            "source_publication": {"at": checked_at, "precision": "upper_bound"},
            "ingestion": {"at": checked_at, "precision": "exact"},
            "computation": {"at": _text(evaluated_at), "precision": "exact"},
        }
        identity = {
            "universe_id": LEGACY_MARKET_TO_UNIVERSE_ID.get(market_id),
            "market_id": market_id,
            "index_id": index_id,
            "fx_id": fx_id,
            "horizon": horizon,
            "currency_basis": currency_basis,
            "return_basis": record.get("return_basis"),
            "window_start": window_start,
            "window_end": window_end,
            "source_content_sha256": (binding.get("content_sha256")
                                      if isinstance(binding, dict) else None),
        }
        extra_reasons = []
        if isinstance(binding, dict) and (
                binding.get("index_id") != index_id
                or binding.get("fx_id") != fx_id):
            extra_reasons.append("identity_mismatch")
        if currency_basis == "usd_unhedged":
            local_window = _window_of(record, "local")
            usd_window = _window_of(record, "usd")
            if local_window and usd_window:
                starts = (_text(local_window.get("start")), _text(usd_window.get("start")))
                ends = (_text(local_window.get("end")), _text(usd_window.get("end")))
                if starts[0] != starts[1] or ends[0] != ends[1]:
                    if "identity_mismatch" not in extra_reasons:
                        extra_reasons.append("identity_mismatch")
        observations.append(build_observation(
            identity=identity, clocks=clocks,
            values={"local_pct": local_pct, "usd_pct": usd_pct, "fx_pct": fx_pct},
            rights=_rights_view(rights), incumbent=incumbent,
            evidence_ref=_evidence_ref(source_evidence, index_id, fx_id, leg),
            extra_reasons=tuple(extra_reasons),
        ))
    return observations
