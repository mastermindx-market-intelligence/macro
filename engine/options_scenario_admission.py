"""Pure strict composition of native Options receipts and the existing scenario math.

This is research/conditional calculation, never source, model or publication authority.
The legacy surface remains unchanged. Its skip-missing semantics are unsuitable for
complete supplied-book claims; this entry point checks every selected member first.
Only the existing standard SPY/QQQ equity terms domain is supported here. SPX risk
units and its separately reviewed known-IV endpoint policy remain with their owner.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date

import numpy as np
import pandas as pd

from engine.intraday_greeks import KERNEL_CONVENTIONS, bs_greeks_vec, kernel_applicability
from engine.options_exposure_projection import (
    _index, _number, _session_date, _time,
    compose_native_exposure_context, exposure_input_digest,
)
from engine.options_scenario_surface import MINUTES_PER_YEAR, build_scenario_surface

_AUTHORITY = {key: False for key in (
    "can_publish", "actual_dealer_inventory", "calibrated_probability", "executed_flow",
    "trading", "ranking", "portfolio", "sizing", "auto_exit",
)}
_REQUEST_FIELDS = {"price_grid", "horizons_minutes", "expiry_scope", "max_dte_days",
                   "r", "q", "mult", "pm", "spot", "iv_source", "vol_map", "model"}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _native_number(value):
    return _number(value) if isinstance(value, (int, float, np.integer, np.floating)) else None


def _strict_iv_provenance(context):
    provenance = context.get("greek_provenance")
    iv = provenance.get("iv") if isinstance(provenance, dict) else None
    return (isinstance(iv, dict)
        and iv.get("source_ref") == context.get("source_snapshot_ref")
        and _text(iv.get("model_ref"))
        and iv.get("method") in {"provider_observed", "engine.intraday_greeks"}
        and iv.get("unit") == "decimal_annualized"
        and iv.get("tenor_policy") == "economic_expiry_no_floor")


def _finite_kernel_members(contracts, prices, horizons, *, r, q):
    """Reuse the kernel; do not let the legacy finite-member mask shrink a total."""
    strike = np.asarray([c["strike"] for c in contracts], dtype=float)
    tenor = np.asarray([c["exp_years"] for c in contracts], dtype=float)
    iv = np.asarray([c["iv"] for c in contracts], dtype=float)
    calls = np.asarray([c["right"] == "C" for c in contracts], dtype=bool)
    for horizon in horizons:
        remaining = tenor - horizon / MINUTES_PER_YEAR
        for price in prices:
            with np.errstate(over="ignore", invalid="ignore", divide="ignore", under="ignore"):
                values = bs_greeks_vec(price, strike, remaining, iv, calls, r=r, q=q)
            if any(not np.isfinite(value).all() for value in values):
                return False
    return True


def build_admitted_scenario_surface(greeks_df, oi_df, asof, root, *, request, source_context):
    """Validate a supplied native snapshot, then call the incumbent IV-driven model.

    ``source_context`` uses the existing exposure-context keys and an ``iv`` entry
    in its existing ``greek_provenance`` map: source_ref/model_ref/method/unit/
    tenor_policy. IV must be decimal annualized on an economic-expiry/no-floor
    basis. Reported Gamma/Vanna/Charm are not required: this calculation derives
    them from the admitted IV using the incumbent kernel, not from feed Greeks.
    Rates and continuous dividend yield are explicit *scenario assumptions*;
    the admitted American-call equivalence requires r >= 0 and q == 0.
    Missing source/terms/availability or a refused capability never becomes zero.
    A structurally valid caller receipt does not authenticate it or grant rights.
    """
    out = {"schema": "options.admitted_scenario_surface/v1", "status": "unavailable",
        "product_kind": "conditional_price_time_scenario", "authority_tier": "research",
        "evidence_class": "SCENARIO", "authority": dict(_AUTHORITY),
        "source": None, "coverage": {"expected": None, "received": 0, "selected": 0,
            "qualified": 0, "missing": None, "zero_weight": 0, "unqualified_selected": None},
        "unavailable_reasons": [], "surface": None}

    def refuse(reason):
        out["unavailable_reasons"] = [reason]
        return out

    if root not in {"SPY", "QQQ"}:
        return refuse("unsupported_root")
    if not isinstance(asof, str):
        return refuse("invalid_source_session")
    try:
        if date.fromisoformat(asof).isoformat() != asof:
            return refuse("invalid_source_session")
    except ValueError:
        return refuse("invalid_source_session")
    if not isinstance(request, dict) or set(request) - _REQUEST_FIELDS:
        return refuse("invalid_request")
    numbers = {key: _native_number(request.get(key)) for key in ("r", "q", "mult", "pm")}
    if any(value is None for value in numbers.values()):
        return refuse("explicit_conventions_required")
    if numbers["mult"] != 100:
        return refuse("unsupported_multiplier")
    # The legacy kernel uses pm for Vanna too, but labels it per one vol point.
    if numbers["pm"] != .01:
        return refuse("unsupported_pct_move")
    # For the standard American-call domain below, no discrete dividend is
    # insufficient on its own: positive yield or negative rates can introduce
    # exercise value absent from the incumbent European kernel.
    if numbers["q"] != 0 or numbers["r"] < 0:
        return refuse("unsupported_american_call_carry")
    if (request.get("iv_source", "provided_iv") != "provided_iv"
            or request.get("vol_map", "sticky_strike") != "sticky_strike"
            or request.get("model", KERNEL_CONVENTIONS["model"]) != KERNEL_CONVENTIONS["model"]):
        return refuse("unsupported_pricing_convention")
    prices, horizons = request.get("price_grid"), request.get("horizons_minutes")
    if (not isinstance(prices, list) or len(prices) < 2
            or any(_native_number(x) is None or x <= 0 for x in prices)
            or len(set(prices)) < 2):
        return refuse("invalid_price_grid")
    if (not isinstance(horizons, list) or not horizons
            or any(isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, np.integer))
                   or _native_number(x * 60) is None or x < 0
                   for x in horizons)):
        return refuse("invalid_horizons")
    prices, horizons = sorted(set(prices)), sorted(set(horizons))
    scope, max_dte = request.get("expiry_scope"), request.get("max_dte_days")
    if scope is not None:
        if not isinstance(scope, list) or not scope or any(not isinstance(x, str) for x in scope):
            return refuse("invalid_expiry_scope")
        try:
            if any(date.fromisoformat(x).isoformat() != x for x in scope) or len(set(scope)) != len(scope):
                return refuse("invalid_expiry_scope")
        except ValueError:
            return refuse("invalid_expiry_scope")
    if max_dte is not None and (_native_number(max_dte) is None or max_dte <= 0):
        return refuse("invalid_max_dte")
    if (not isinstance(source_context, dict) or source_context.get("kind") != "modeled_exposure"
            or source_context.get("root", root) != root):
        return refuse("unsupported_source_context")
    capabilities = source_context.get("capabilities")
    if capabilities is not None and (not isinstance(capabilities, dict)
            or any(k in capabilities and capabilities[k] is not True for k in ("joint_scenario", "repricing"))):
        return refuse("source_capability_refused")
    for field in ("contract_terms", "expected_contracts", "contract_reference_populations", "contract_reference_observations"):
        records = source_context.get(field)
        if records is not None and (not isinstance(records, list) or any(not isinstance(row, dict) for row in records)):
            return refuse("invalid_source_context_shape")
    if not isinstance(source_context.get("clocks"), dict):
        return refuse("source_availability_unknown")
    if not isinstance(greeks_df, pd.DataFrame) or not isinstance(oi_df, pd.DataFrame):
        return refuse("invalid_native_frames")
    gs, os = greeks_df.to_dict("records"), oi_df.to_dict("records")
    if (any(_session_date(row.get("date")) != asof for row in gs)
            or any("date" in row and _session_date(row["date"]) != asof for row in os)):
        return refuse("source_session_mismatch")
    try:
        context = compose_native_exposure_context(greeks_df, oi_df, asof, root,
                                                   context=deepcopy(source_context))
    except (ValueError, TypeError, KeyError):
        return refuse("source_context_composition_failed")
    # The composer deliberately leaves mismatched digests untouched: validate it.
    if context.get("input_sha256") != exposure_input_digest(greeks_df, oi_df, asof, root):
        return refuse("source_inputs_do_not_match_receipt")
    if not _text(context.get("security_id")) or not _text(context.get("source_snapshot_ref")):
        return refuse("source_identity_unknown")
    clocks = context.get("clocks")
    if not isinstance(clocks, dict) or any(clocks.get(k) != asof for k in ("source_session", "oi_report_date")):
        return refuse("source_session_mismatch")
    stamps = {key: _time(clocks.get(key)) for key in (
        "option_observed_at", "underlying_observed_at", "greeks_available_at", "oi_available_at", "available_at")}
    if any(value is None for value in stamps.values()):
        return refuse("source_availability_unknown")
    observed, cutoff = stamps["option_observed_at"], stamps["available_at"]
    if stamps["underlying_observed_at"] != observed:
        return refuse("underlying_observation_mismatch")
    if (any(value > cutoff for value in stamps.values())
            or stamps["greeks_available_at"] < observed):
        return refuse("source_availability_order")
    if any(stamps[k].tz_convert("America/New_York").date().isoformat() != asof
           for k in ("option_observed_at", "underlying_observed_at")):
        return refuse("source_session_mismatch")
    out["source"] = {"root": root, "security_id": context["security_id"],
        "source_snapshot_ref": context["source_snapshot_ref"], "input_sha256": context["input_sha256"],
        "clocks": deepcopy(clocks), "rights_decision_ref": context.get("rights_decision_ref")}
    expected_rows, term_rows = context.get("expected_contracts"), context.get("contract_terms")
    if not isinstance(expected_rows, list) or not expected_rows or not isinstance(term_rows, list):
        return refuse("expected_population_or_terms_unknown")
    if any(not isinstance(row, dict) for row in expected_rows + term_rows):
        return refuse("invalid_contract_identity")
    greek, bad_g = _index(gs, root)
    oi, bad_o = _index(os, root)
    expected, bad_e = _index(expected_rows, root)
    terms, bad_t = _index(term_rows, root)
    received = set(greek) | set(oi)
    out["coverage"].update(expected=len(expected_rows), received=len(received), missing=len(set(expected) - received))
    if bad_g or bad_o or bad_e or bad_t or any(len(v) != 1 for table in (greek, oi, expected, terms) for v in table.values()):
        return refuse("invalid_or_duplicate_contract_identity")
    if received != set(expected) or set(terms) != set(expected):
        return refuse("supplied_population_mismatch")
    series_ids = set()
    validated, positives, spots = [], [], []
    for key in sorted(expected):
        term = terms[key][0]
        if (not all(_text(term.get(k)) for k in ("series_id", "terms_ref", "deliverable_ref"))
                or term["series_id"] in series_ids or term.get("security_id") != context["security_id"]
                or term.get("currency") != "USD" or term.get("deliverable") != "100_underlying_shares"
                or _number(term.get("multiplier")) != numbers["mult"]
                or ("shares_per_contract" in term and _number(term["shares_per_contract"]) != 100)
                or ("additional_underlyings" in term and term["additional_underlyings"] != [])
                or term.get("exercise_style") != "american"):
            return refuse("exact_series_terms_unqualified")
        series_ids.add(term["series_id"])
        known, expiry = _time(term.get("available_at")), _time(term.get("economic_expiry_at"))
        if known is None or known > cutoff or expiry is None or expiry.tz_convert("America/New_York").date().isoformat() != key[0]:
            return refuse("series_terms_clock_unqualified")
        oi_value = _number(oi.get(key, [{}])[0].get("open_interest"))
        if oi_value is None or oi_value < 0 or not oi_value.is_integer():
            return refuse("oi_unknown_or_invalid")
        validated.append((key, term, oi_value, (expiry - observed).total_seconds()))
    selected = [(key, term, oi_value, seconds) for key, term, oi_value, seconds in validated
        if (scope is None or key[0] in scope) and (max_dte is None or seconds / 86400 <= max_dte)]
    out["coverage"].update(expiry_scope=deepcopy(scope), max_dte_days=max_dte)
    out["coverage"]["selected"] = len(selected)
    out["coverage"]["unqualified_selected"] = len(selected)
    out["coverage"]["selected_contract_keys"] = [list(row[0]) for row in selected]
    out["coverage"]["basis"] = "input_and_applicability"
    if not selected or (scope is not None and set(scope) - {row[0][0] for row in selected}):
        return refuse("empty_expiry_scope")
    positive_members = []
    for key, term, oi_value, seconds in selected:
        for horizon in sorted({0, *horizons}):
            app = kernel_applicability(exercise_style=term["exercise_style"], right=key[2],
                seconds_to_economic_expiry=seconds - horizon * 60,
                discrete_dividend_before_expiry=term.get("discrete_dividend_before_expiry"))
            if app["status"] != "supported" and not (oi_value == 0 and app["reason"] in {
                "american_put_early_exercise", "american_call_dividend_before_expiry", "unknown_dividend_schedule"}):
                return refuse(app["reason"])
        if oi_value == 0:
            out["coverage"]["zero_weight"] += 1
            out["coverage"]["qualified"] += 1
            out["coverage"]["unqualified_selected"] -= 1
            continue
        positive_members.append((key, oi_value, seconds))
    for key, oi_value, seconds in positive_members:
        g = greek.get(key, [{}])[0]
        iv, spot = _number(g.get("implied_vol")), _number(g.get("underlying_price"))
        if iv is None or iv <= 0 or spot is None or spot <= 0:
            return refuse("iv_or_spot_unknown_or_invalid")
        spots.append(spot)
        positives.append({"strike": key[1], "right": key[2], "expiry": key[0],
            "exp_years": seconds / (365 * 86400), "oi": oi_value, "iv": iv})
        out["coverage"]["qualified"] += 1
        out["coverage"]["unqualified_selected"] -= 1
    if not positives:
        return refuse("no_positive_weight_contracts")
    if not _strict_iv_provenance(context):
        return refuse("iv_provenance_unqualified")
    if len(set(spots)) != 1 or ("spot" in request and _native_number(request["spot"]) != spots[0]):
        return refuse("underlying_population_mismatch")
    if not _finite_kernel_members(positives, prices, horizons, r=numbers["r"], q=numbers["q"]):
        return refuse("nonfinite_kernel_member")
    surface = build_scenario_surface(positives, root=root, observed_at=observed.isoformat(),
        spot=spots[0], price_grid=prices, horizons_minutes=horizons,
        expiry_scope=scope, iv_observed_at=observed.isoformat(),
        iv_source="provided_iv", vol_map="sticky_strike",
        r=numbers["r"], q=numbers["q"], mult=numbers["mult"], pm=numbers["pm"])
    if any(value is None or not np.isfinite(value)
           for grid in surface["grids"].values() for row in grid for value in row):
        return refuse("nonfinite_scenario_result")
    out.update(status="complete_for_supplied_universe", surface=surface)
    out["pricing"] = {**KERNEL_CONVENTIONS, "r": numbers["r"], "q": numbers["q"],
        "r_source": "explicit_scenario_assumption", "q_source": "explicit_scenario_assumption",
        "iv_provenance": deepcopy(context["greek_provenance"]["iv"])}
    return out
