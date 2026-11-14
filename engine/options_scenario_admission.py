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

from engine.intraday_greeks import KERNEL_CONVENTIONS, bs_greeks_vec, implied_vol_vec, kernel_applicability
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


def _quote_kernel_identity():
    """Local executed Python implementation identity, not source authentication.

    Code paths/line tables are excluded so worktree placement cannot change the
    identity. Actual kernel functions, constants, executed aliases and dependency
    versions are included. No file/current-clock/network read or caller version.
    """
    import hashlib
    import json
    import marshal
    import sys
    import types
    from engine import intraday_greeks as kernel
    try:
        import scipy
        scipy_version = scipy.__version__
    except ImportError:
        scipy_version = None

    def normalized(code):
        return code.replace(co_filename="", co_firstlineno=1, co_linetable=b"",
            co_consts=tuple(normalized(value) if isinstance(value, types.CodeType) else value
                            for value in code.co_consts))

    functions = {name: value for name, value in vars(kernel).items()
                 if isinstance(value, types.FunctionType) and value.__module__ == kernel.__name__}
    functions.update(executed_iv=implied_vol_vec, executed_greeks=bs_greeks_vec,
                     executed_applicability=kernel_applicability)
    implementation = {"kind": "local_python_implementation_fingerprint/v1",
        "module": kernel.__name__,
        "versions": {"python": sys.version, "numpy": np.__version__, "scipy": scipy_version},
        "functions": {name: {
            "code_sha256": hashlib.sha256(marshal.dumps(normalized(function.__code__))).hexdigest(),
            "defaults": function.__defaults__, "kwdefaults": function.__kwdefaults__}
            for name, function in sorted(functions.items())},
        "constants": {name: value.item() if isinstance(value, np.generic) else value
            for name, value in vars(kernel).items() if name.isupper()
            and isinstance(value, (str, int, float, bool, dict, tuple, list, type(None), np.generic))}}
    encoded = json.dumps(implementation, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return {**json.loads(encoded), "sha256": hashlib.sha256(encoded).hexdigest()}


def _quote_capsule_ref(capsule):
    import hashlib
    import json
    try:
        encoded = json.dumps(capsule, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("Invalid quote provenance encoding") from exc
    if len(encoded) > 262144:
        raise ValueError("Quote provenance exceeds selected-expiry byte bound")
    return "quote-valuation:sha256:" + hashlib.sha256(encoded).hexdigest()


def _validated_quote_capsule(context, greeks_df, oi_df, asof, root):
    """Bounded integrity/semantics check; never a provider/PIT/rights grant."""
    capsule = context.get("quote_valuation")
    if not isinstance(capsule, dict):
        raise ValueError("Missing quote provenance")
    identity = _quote_kernel_identity()
    iv = (context.get("greek_provenance") or {}).get("iv")
    original = deepcopy({key: value for key, value in context.items()
                if key not in {"quote_valuation", "source_snapshot_ref", "input_sha256", "greek_provenance"}})
    supplied = deepcopy(capsule.get("supplied_context"))
    if not isinstance(supplied, dict) or not isinstance(supplied.get("clocks"), dict):
        raise ValueError("Missing supplied quote context")
    # The incumbent OI receipt composer normalizes equivalent Z/+00:00 text.
    # Compare instants without changing any retained capsule/event strings.
    for field in ("option_observed_at", "underlying_observed_at", "greeks_available_at", "oi_available_at", "available_at"):
        before, after = _time(supplied["clocks"].get(field)), _time(original["clocks"].get(field))
        if before is None or after is None or before != after:
            raise ValueError("Quote context clock mismatch")
        supplied["clocks"][field] = original["clocks"][field] = after.isoformat()
    if (capsule.get("schema") != "options.quote_valuation/v1"
            or capsule.get("kind") != "conditional_asof_reconstruction"
            or capsule.get("historical_first_availability_established") is not False
            or capsule.get("pit_qualified") is not False
            or capsule.get("implementation") != identity
            or capsule.get("derived_input_sha256") != exposure_input_digest(greeks_df, oi_df, asof, root)
            or supplied != original
            or _quote_capsule_ref(capsule) != context.get("source_snapshot_ref")
            or not isinstance(iv, dict) or iv.get("implementation_sha256") != identity["sha256"]
            or iv.get("model_ref") != KERNEL_CONVENTIONS["model"]
               + "|engine.intraday_greeks.implied_vol_vec|local-implementation-sha256:" + identity["sha256"]):
        raise ValueError("Quote provenance/source/model mismatch")
    return deepcopy(capsule)


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
    if context["source_snapshot_ref"].startswith("quote-valuation:") or "quote_valuation" in context:
        try:
            out["source"]["quote_valuation"] = _validated_quote_capsule(context, greeks_df, oi_df, asof, root)
        except (ValueError, TypeError, AttributeError, KeyError, OverflowError):
            return refuse("quote_valuation_provenance_unqualified")
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


def compose_quote_valuation_inputs(option_captures, underlying_capture, oi_df, asof, root, *,
                                   source_context, valuation_at, evaluated_at,
                                   max_quote_age_seconds, quote_policy, r, q):
    """Opt-in local conditional reconstruction; no acquisition or authority grant.

    Capture objects contain ``raw`` CSV bytes and an original ``receipt`` string.
    Explicit equal context observation clocks describe model valuation at T; raw
    quote events remain separate, unchanged fields. Later capture availability is
    never backdated to T. The existing strict scenario admission remains separate.
    """
    from lib.options_source_receipts import quote_capture_at, native_acquisitions
    from engine.options_nbbo_cohort import FIRM_OPRA_QUOTE_CONDITIONS, KNOWN_THETA_EXCHANGES

    target, evaluated = _time(valuation_at), _time(evaluated_at)
    if (root not in {"SPY", "QQQ"} or target is None or evaluated is None or evaluated < target
            or target.tz_convert("America/New_York").date().isoformat() != asof
            or _native_number(r) is None or r < 0 or _native_number(q) != 0
            or not isinstance(source_context, dict) or source_context.get("kind") != "modeled_exposure"
            or source_context.get("root") != root or not _text(source_context.get("security_id"))):
        raise ValueError("Explicit qualified valuation domain required")
    if any(field in source_context for field in ("input_sha256", "source_snapshot_ref", "greek_provenance", "quote_valuation")):
        raise ValueError("Existing source identity cannot be relabelled as quote valuation")
    context = deepcopy(source_context)
    clocks = context.get("clocks")
    if (not isinstance(clocks, dict) or clocks.get("source_session") != asof
            or clocks.get("oi_report_date") != asof
            or any(_time(clocks.get(field)) != target for field in ("option_observed_at", "underlying_observed_at"))
            or _time(clocks.get("available_at")) != evaluated
            or _time(clocks.get("greeks_available_at")) != evaluated):
        raise ValueError("Explicit valuation/computation clocks required; none are rewritten")
    policy_fields = {"option_conditions", "stock_conditions", "option_exchanges", "stock_exchanges", "stock_condition_basis"}
    if (not isinstance(quote_policy, dict) or set(quote_policy) != policy_fields
            or not _text(quote_policy["stock_condition_basis"])
            or any(not isinstance(quote_policy[field], list) or not quote_policy[field]
                   or any(type(value) is not int or value < 0 for value in quote_policy[field])
                   for field in policy_fields - {"stock_condition_basis"})
            or not set(quote_policy["option_conditions"]) <= FIRM_OPRA_QUOTE_CONDITIONS
            or not set(quote_policy["option_exchanges"]) <= KNOWN_THETA_EXCHANGES):
        raise ValueError("Explicit feed-specific mark policy required")
    if (not isinstance(option_captures, list) or not option_captures or len(option_captures) > 100
            or not isinstance(underlying_capture, dict) or set(underlying_capture) != {"raw", "receipt"}):
        raise ValueError("Bounded exact supplied captures required")

    def capture(value, kind):
        if not isinstance(value, dict) or set(value) != {"raw", "receipt"}:
            raise ValueError("Invalid quote capture shape")
        result = quote_capture_at(**value, kind=kind, root=root, session=asof,
            valuation_at=valuation_at, max_age_seconds=max_quote_age_seconds,
            allowed_conditions=quote_policy[kind + "_conditions"],
            allowed_exchanges=quote_policy[kind + "_exchanges"])
        if _time(result["receipt"]["received_at"]) > evaluated:
            raise ValueError("Quote unavailable at actual evaluation cutoff")
        return result

    underlying = capture(underlying_capture, "stock")
    options = [capture(value, "option") for value in option_captures]
    expected_rows, term_rows = context.get("expected_contracts"), context.get("contract_terms")
    if (not isinstance(expected_rows, list) or not expected_rows or not isinstance(term_rows, list)
            or not isinstance(oi_df, pd.DataFrame)):
        raise ValueError("Explicit expected population/OI/terms required")
    if any(not isinstance(row, dict) for row in expected_rows + term_rows):
        raise ValueError("Invalid expected/terms row shape")
    expected, bad_e = _index(expected_rows, root)
    terms, bad_t = _index(term_rows, root)
    oi, bad_o = _index(oi_df.to_dict("records"), root)
    if (bad_e or bad_t or bad_o or any(len(rows) != 1 for table in (expected, terms, oi) for rows in table.values())
            or set(expected) != set(terms) or set(expected) != set(oi)):
        raise ValueError("Duplicate/missing/extra supplied member")
    oi_receipts = native_acquisitions(oi_df, root, asof, "oi", now=evaluated_at)
    oi_available = _time(clocks.get("oi_available_at"))
    if (not oi_receipts or oi_available is None or oi_available > evaluated
            or any(_time(receipt["received_at"]) > oi_available for receipt in oi_receipts)):
        raise ValueError("Actual OI availability unqualified")
    rows, seen = [], set()
    spot = underlying["mid"]
    for option in options:
        params = option["receipt"]["parameters"]
        key = (params["expiration"], float(params["strike"]), "C")
        if key in seen or key not in expected:
            raise ValueError("Duplicate/extra captured member")
        seen.add(key)
        term = terms[key][0]
        expiry, known = _time(term.get("economic_expiry_at")), _time(term.get("available_at"))
        if (expiry is None or known is None or known > evaluated
                or expiry.tz_convert("America/New_York").date().isoformat() != key[0]
                or term.get("exercise_style") != "american"
                or term.get("discrete_dividend_before_expiry") is not False
                or term.get("security_id") != context["security_id"]
                or term.get("currency") != "USD" or term.get("multiplier") != 100
                or term.get("deliverable") != "100_underlying_shares"
                or ("shares_per_contract" in term and _number(term["shares_per_contract"]) != 100)
                or ("additional_underlyings" in term and term["additional_underlyings"] != [])
                or any(not _text(term.get(field)) for field in ("series_id", "terms_ref", "deliverable_ref"))):
            raise ValueError("Explicit economic terms/dividend facts unqualified")
        seconds = (expiry - target).total_seconds()
        if kernel_applicability(exercise_style="american", right="C",
                seconds_to_economic_expiry=seconds, discrete_dividend_before_expiry=False)["status"] != "supported":
            raise ValueError("Kernel applicability refused")
        interest = _number(oi[key][0].get("open_interest"))
        if interest is None or interest < 0 or not interest.is_integer():
            raise ValueError("Unknown/invalid OI")
        sigma = float(implied_vol_vec(np.array([option["mid"]]), spot,
            np.array([key[1]]), np.array([seconds / (365 * 86400)]), np.array([True]), r=r, q=q)[0])
        if not np.isfinite(sigma) or sigma <= 0:
            raise ValueError("IV unsolved; supplied cohort withheld")
        rows.append(dict(root=root, date=asof, expiration=key[0], strike=key[1], right="C",
            implied_vol=sigma, underlying_price=spot, timestamp=option["raw_event_at"],
            underlying_timestamp=underlying["raw_event_at"], _theta_acquisition=option["receipt_text"]))
    if seen != set(expected):
        raise ValueError("Missing supplied quote member")
    greeks = pd.DataFrame(rows)
    input_digest = exposure_input_digest(greeks, oi_df, asof, root)
    implementation = _quote_kernel_identity()
    evidence = {"schema": "options.quote_valuation/v1", "kind": "conditional_asof_reconstruction",
        "valuation_at": valuation_at, "evaluated_at": evaluated_at,
        "historical_first_availability_established": False, "pit_qualified": False,
        "max_quote_age_seconds": max_quote_age_seconds, "policy": deepcopy(quote_policy),
        "r": r, "q": q, "derivation": "engine.intraday_greeks.implied_vol_vec",
        "implementation": implementation,
        "derived_input_sha256": input_digest,
        "option_quotes": options, "underlying_quote": underlying,
        "oi_receipts": oi_receipts, "supplied_context": deepcopy(context)}
    source_ref = _quote_capsule_ref(evidence)
    context["source_snapshot_ref"] = source_ref
    context["quote_valuation"] = evidence
    context["greek_provenance"] = {"iv": {"source_ref": source_ref,
        "model_ref": KERNEL_CONVENTIONS["model"] + "|engine.intraday_greeks.implied_vol_vec|local-implementation-sha256:" + implementation["sha256"],
        "implementation_sha256": implementation["sha256"],
        "method": "engine.intraday_greeks", "unit": "decimal_annualized",
        "tenor_policy": "economic_expiry_no_floor"}}
    context["input_sha256"] = input_digest
    return greeks, oi_df.copy(deep=True), context
