"""Qualified A6/A7 extension of the existing F07 earnings-multiple owner.

This module is deliberately pure: no IO, network, clock, event reader, identity
resolver, source loader, publication, ranking, or lifecycle effect. It consumes
one caller-supplied immutable qualified receipt and extends
engine.valuation_scenario without modifying that byte-pinned legacy owner.

The forward operation order is the F07 owner relation:

    adjusted_income = N * (1 + g/100) * (1 + (d/100) / (N/R))
    per_share = adjusted_income * k / S

The conditional inverse solves only for k with g and d visibly locked. It is
research/display context, never fair value, market-belief probability, ranking,
sizing, or trading authority.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
import re

from engine import valuation_scenario as _v1_owner


QUALIFIED_INPUT_SCHEMA = "valuation_scenario_qualified_input.v1"
QUALIFIED_FORWARD_SCHEMA = "valuation_scenario_forward.v2"
QUALIFIED_INVERSE_SCHEMA = "valuation_scenario_inverse.v1"
QUALIFIED_INTERVAL_SCHEMA = "valuation_scenario_compatible_interval.v1"
QUALIFIED_MODEL_FAMILY = "f07_earnings_multiple"
QUALIFIED_MODEL_VERSION = "a6_a7.v1"
QUALIFIED_OWNER_MODULE = "engine.valuation_scenario"
QUALIFIED_OWNER_PRESETS = _v1_owner.SCENARIOS

# These are the accepted existing F07 control bounds. They are duplicated here
# only as an admission contract so this pure module does not import
# valuation_assumptions, whose module graph includes moving event readers.
# Tests bind these values back to the owner controls.
QUALIFIED_ASSUMPTION_BOUNDS = {
    "sales_growth_pct": (-10.0, 20.0),
    "margin_delta_pp": (-3.0, 3.0),
    "earnings_multiple": (8.0, 35.0),
}
_QUALIFIED_TICKERS = frozenset({"AAPL"})
_QUALIFIED_SHARE_IDENTITIES = frozenset({"outstanding"})
_QUALIFIED_MARGIN_BASE_FLOOR = 0.01


def _number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _text(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def _utc(value):
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _base_result(schema, receipt):
    receipt = receipt if isinstance(receipt, dict) else {}
    return {
        "schema": schema,
        "model_family": QUALIFIED_MODEL_FAMILY,
        "model_version": QUALIFIED_MODEL_VERSION,
        "owner_module": QUALIFIED_OWNER_MODULE,
        "authority": "research_display_only",
        "tier": "research_display_only",
        "valid": False,
        "refusal_reasons": [],
        "ticker": receipt.get("ticker"),
        "security_ref": receipt.get("security_ref"),
        "input_receipt_id": receipt.get("receipt_id"),
        "financial_receipt_id": receipt.get("financial_receipt_id"),
        "price_receipt_id": receipt.get("price_receipt_id"),
        "currency": receipt.get("financial_currency"),
        "share_identity": receipt.get("share_identity"),
        "accounting_basis": receipt.get("accounting_basis"),
        "fiscal_period": receipt.get("fiscal_period"),
        "decision_cutoff": receipt.get("decision_cutoff"),
    }


def _qualify_receipt(receipt):
    reasons = []
    if not isinstance(receipt, dict) or receipt.get("schema") != QUALIFIED_INPUT_SCHEMA:
        reasons.append("invalid_schema")
        return {}, reasons

    for key, reason in (
        ("receipt_id", "receipt_unqualified"),
        ("financial_receipt_id", "financial_receipt_unqualified"),
        ("price_receipt_id", "price_receipt_unqualified"),
        ("security_ref", "identity_unqualified"),
        ("accounting_basis", "accounting_basis_unqualified"),
        ("fiscal_period", "fiscal_period_unqualified"),
        ("price_basis", "price_basis_unqualified"),
    ):
        if _text(receipt.get(key)) is None:
            reasons.append(reason)

    ticker = _text(receipt.get("ticker"))
    if ticker not in _QUALIFIED_TICKERS:
        reasons.append("unsupported_ticker")

    security_ref = _text(receipt.get("security_ref"))
    price_security_ref = _text(receipt.get("price_security_ref"))
    if price_security_ref is None or price_security_ref != security_ref:
        reasons.append("price_identity_mismatch")

    accounting_basis = _text(receipt.get("accounting_basis"))
    if accounting_basis is not None and accounting_basis != "US_GAAP":
        reasons.append("unsupported_accounting_basis")

    fiscal_period = _text(receipt.get("fiscal_period"))
    if fiscal_period is not None and re.fullmatch(r"FY\d{4}", fiscal_period) is None:
        reasons.append("unsupported_fiscal_period")

    share_identity = _text(receipt.get("share_identity"))
    if share_identity not in _QUALIFIED_SHARE_IDENTITIES:
        reasons.append("unsupported_share_identity")

    financial_currency = _text(receipt.get("financial_currency"))
    price_currency = _text(receipt.get("price_currency"))
    if financial_currency is None or price_currency is None or financial_currency != price_currency:
        reasons.append("currency_mismatch")

    if (
        receipt.get("research_use_permitted") is not True
        or receipt.get("derived_use_permitted") is not True
    ):
        reasons.append("rights_not_permitted")

    cutoff = _utc(receipt.get("decision_cutoff"))
    financial_available = _utc(receipt.get("financial_available_at"))
    price_available = _utc(receipt.get("price_available_at"))
    if cutoff is None or financial_available is None or price_available is None:
        reasons.append("cutoff_unqualified")
    elif financial_available > cutoff or price_available > cutoff:
        reasons.append("cutoff_violation")

    values = {}
    for key in ("net_income", "revenue", "shares", "price", "price_tolerance"):
        values[key] = _number(receipt.get(key))
        if values[key] is None:
            reasons.append("nonfinite_or_boolean_input")

    if values.get("net_income") is not None and values["net_income"] <= 0:
        reasons.append("nonpositive_net_income")
    if values.get("revenue") is not None and values["revenue"] <= 0:
        reasons.append("nonpositive_revenue")
    if values.get("shares") is not None and values["shares"] <= 0:
        reasons.append("nonpositive_shares")
    if values.get("price") is not None and values["price"] <= 0:
        reasons.append("price_nonpositive")
    if values.get("price_tolerance") is not None and values["price_tolerance"] < 0:
        reasons.append("price_tolerance_invalid")

    values.update(
        {
            "ticker": ticker,
            "security_ref": security_ref,
            "price_security_ref": price_security_ref,
            "financial_currency": financial_currency,
            "share_identity": share_identity,
            "accounting_basis": accounting_basis,
            "fiscal_period": fiscal_period,
            "cutoff": cutoff,
        }
    )
    return values, list(dict.fromkeys(reasons))


def _qualify_assumptions(*, sales_growth_pct, margin_delta_pp, earnings_multiple=None):
    reasons = []
    values = {}
    for key, raw in (
        ("sales_growth_pct", sales_growth_pct),
        ("margin_delta_pp", margin_delta_pp),
    ):
        value = _number(raw)
        values[key] = value
        if value is None:
            reasons.append("nonfinite_or_boolean_assumption")

    if earnings_multiple is not None:
        multiple = _number(earnings_multiple)
        values["earnings_multiple"] = multiple
        if multiple is None:
            reasons.append("nonfinite_or_boolean_assumption")
    else:
        values["earnings_multiple"] = None

    g = values["sales_growth_pct"]
    d = values["margin_delta_pp"]
    k = values["earnings_multiple"]
    if g is not None:
        lo, hi = QUALIFIED_ASSUMPTION_BOUNDS["sales_growth_pct"]
        if not lo <= g <= hi:
            reasons.append("growth_out_of_bounds")
    if d is not None:
        lo, hi = QUALIFIED_ASSUMPTION_BOUNDS["margin_delta_pp"]
        if not lo <= d <= hi:
            reasons.append("margin_out_of_bounds")
    if earnings_multiple is not None and k is not None:
        lo, hi = QUALIFIED_ASSUMPTION_BOUNDS["earnings_multiple"]
        if not lo <= k <= hi:
            reasons.append("multiple_out_of_bounds")
    return values, list(dict.fromkeys(reasons))


def _components(receipt, *, sales_growth_pct, margin_delta_pp, earnings_multiple=None):
    inputs, reasons = _qualify_receipt(receipt)
    assumptions, assumption_reasons = _qualify_assumptions(
        sales_growth_pct=sales_growth_pct,
        margin_delta_pp=margin_delta_pp,
        earnings_multiple=earnings_multiple,
    )
    reasons.extend(assumption_reasons)

    ni = inputs.get("net_income")
    revenue = inputs.get("revenue")
    shares = inputs.get("shares")
    g = assumptions.get("sales_growth_pct")
    d = assumptions.get("margin_delta_pp")

    net_margin_base = None
    growth_factor = None
    margin_factor = None
    scale = None
    if ni is not None and revenue is not None and ni > 0 and revenue > 0:
        net_margin_base = ni / revenue
        if not math.isfinite(net_margin_base) or abs(net_margin_base) < _QUALIFIED_MARGIN_BASE_FLOOR:
            reasons.append("margin_base_too_thin")
        if g is not None:
            growth_factor = 1.0 + g / 100.0
        if d is not None and math.isfinite(net_margin_base) and net_margin_base != 0:
            if (net_margin_base + d / 100.0) <= 0:
                reasons.append("adjusted_margin_nonpositive")
            margin_factor = 1.0 + (d / 100.0) / net_margin_base

    if (
        ni is not None
        and shares is not None
        and ni > 0
        and shares > 0
        and growth_factor is not None
        and margin_factor is not None
        and growth_factor > 0
        and margin_factor > 0
    ):
        scale = ni * growth_factor * margin_factor / shares
        if not math.isfinite(scale) or scale <= 0:
            reasons.append("zero_or_nonfinite_scale")

    return {
        "inputs": inputs,
        "assumptions": assumptions,
        "net_margin_base": net_margin_base,
        "growth_factor": growth_factor,
        "margin_factor": margin_factor,
        "scale": scale,
        "reasons": list(dict.fromkeys(reasons)),
    }


def evaluate_qualified_scenario(
    receipt,
    *,
    sales_growth_pct,
    margin_delta_pp,
    earnings_multiple,
):
    """Pure A6 forward evaluation over an already-qualified immutable receipt."""
    out = _base_result(QUALIFIED_FORWARD_SCHEMA, receipt)
    state = _components(
        receipt,
        sales_growth_pct=sales_growth_pct,
        margin_delta_pp=margin_delta_pp,
        earnings_multiple=earnings_multiple,
    )
    reasons = list(state["reasons"])
    inputs = state["inputs"]
    assumptions = state["assumptions"]
    raw = None

    if not reasons:
        ni = inputs["net_income"]
        revenue = inputs["revenue"]
        shares = inputs["shares"]
        g = assumptions["sales_growth_pct"]
        d = assumptions["margin_delta_pp"]
        k = assumptions["earnings_multiple"]
        net_margin_base = ni / revenue

        # Preserve the exact F07 operation sequence. Do not replace this with
        # the algebraic scale factor used only for inverse derivation below.
        adjusted_income = ni * (1 + g / 100.0) * (1 + (d / 100.0) / net_margin_base)
        if not math.isfinite(adjusted_income) or adjusted_income <= 0:
            reasons.append("numerical_nonfinite")
        else:
            raw = (adjusted_income * k) / shares
            if not math.isfinite(raw) or raw <= 0:
                raw = None
                reasons.append("numerical_nonfinite")

    out.update(
        {
            "refusal_reasons": list(dict.fromkeys(reasons)),
            "assumptions": {
                "sales_growth_pct": assumptions.get("sales_growth_pct"),
                "margin_delta_pp": assumptions.get("margin_delta_pp"),
                "earnings_multiple": assumptions.get("earnings_multiple"),
            },
            "unrounded_per_share": raw,
            "display_per_share": round(raw, 2) if raw is not None else None,
            "price_object": (
                {
                    "value": inputs.get("price"),
                    "currency": inputs.get("financial_currency"),
                    "basis": receipt.get("price_basis") if isinstance(receipt, dict) else None,
                    "receipt_id": receipt.get("price_receipt_id") if isinstance(receipt, dict) else None,
                }
                if isinstance(receipt, dict)
                else None
            ),
        }
    )
    out["valid"] = not out["refusal_reasons"] and raw is not None
    return out


def required_earnings_multiple(
    receipt,
    *,
    sales_growth_pct,
    margin_delta_pp,
):
    """Return the bounded conditional A7 inverse with forward-substitution proof."""
    out = _base_result(QUALIFIED_INVERSE_SCHEMA, receipt)
    state = _components(
        receipt,
        sales_growth_pct=sales_growth_pct,
        margin_delta_pp=margin_delta_pp,
        earnings_multiple=None,
    )
    reasons = list(state["reasons"])
    inputs = state["inputs"]
    assumptions = state["assumptions"]
    scale = state["scale"]
    price = inputs.get("price")
    tolerance = inputs.get("price_tolerance")
    k = None
    forward = None
    residual = None
    within_tolerance = False
    jacobian = None
    null_directions = []

    if not reasons and scale is not None and price is not None:
        candidate_k = price / scale
        if not math.isfinite(candidate_k):
            reasons.append("zero_or_nonfinite_scale")
        else:
            lo, hi = QUALIFIED_ASSUMPTION_BOUNDS["earnings_multiple"]
            if not lo <= candidate_k <= hi:
                reasons.append("inverse_out_of_bounds")
            else:
                k = candidate_k

    if not reasons and k is not None:
        forward_result = evaluate_qualified_scenario(
            receipt,
            sales_growth_pct=assumptions["sales_growth_pct"],
            margin_delta_pp=assumptions["margin_delta_pp"],
            earnings_multiple=k,
        )
        if not forward_result["valid"]:
            reasons.extend(forward_result["refusal_reasons"])
        else:
            forward = forward_result["unrounded_per_share"]
            residual = forward - price
            if not math.isfinite(residual):
                reasons.append("numerical_nonfinite")
            else:
                within_tolerance = abs(residual) <= tolerance
                if not within_tolerance:
                    reasons.append("inverse_forward_substitution_mismatch")

    if not reasons and k is not None and forward is not None:
        mu = state["net_margin_base"]
        u = state["growth_factor"]
        v = state["margin_factor"]
        dg = forward / (100.0 * u)
        dd = forward / (100.0 * mu * v)
        dk = forward / k
        n_g = (1.0, 0.0, -k / (100.0 * u))
        n_d = (0.0, 1.0, -k / (100.0 * mu * v))
        numeric = (dg, dd, dk, *n_g, *n_d)
        if not all(math.isfinite(value) for value in numeric):
            reasons.append("numerical_nonfinite")
        else:
            jacobian = {
                "parameter_order": ["sales_growth_pct", "margin_delta_pp", "earnings_multiple"],
                "row": [dg, dd, dk],
                "rank": 1,
                "nullspace_dimension": 2,
            }
            null_directions = [list(n_g), list(n_d)]

    out.update(
        {
            "refusal_reasons": list(dict.fromkeys(reasons)),
            "conditional_on": {
                "sales_growth_pct": assumptions.get("sales_growth_pct"),
                "margin_delta_pp": assumptions.get("margin_delta_pp"),
            },
            "required_earnings_multiple": k,
            "price": price,
            "price_tolerance": tolerance,
            "forward_unrounded_per_share": forward,
            "forward_residual": residual,
            "within_tolerance": within_tolerance,
            "jacobian": jacobian,
            "null_directions": null_directions,
            "compatibility_mass": None,
            "compatibility_mass_status": "independent_joint_reference_not_qualified",
        }
    )
    out["valid"] = not out["refusal_reasons"] and forward is not None and within_tolerance
    return out


def compatible_multiple_interval(
    receipt,
    *,
    sales_growth_pct,
    margin_delta_pp,
    price_lower,
    price_upper,
):
    """Return the bounded multiple interval compatible with a declared price band.

    This is a feasible-set projection only. It intentionally emits no
    compatibility percentage because no independent joint reference measure is
    qualified by this owner.
    """
    out = _base_result(QUALIFIED_INTERVAL_SCHEMA, receipt)
    state = _components(
        receipt,
        sales_growth_pct=sales_growth_pct,
        margin_delta_pp=margin_delta_pp,
        earnings_multiple=None,
    )
    reasons = list(state["reasons"])
    lower = _number(price_lower)
    upper = _number(price_upper)
    if lower is None or upper is None:
        reasons.append("nonfinite_or_boolean_price_band")
    elif lower <= 0 or upper <= 0 or lower > upper:
        reasons.append("invalid_price_band")

    interval = None
    scale = state["scale"]
    if not reasons and scale is not None:
        k_lower = lower / scale
        k_upper = upper / scale
        if not math.isfinite(k_lower) or not math.isfinite(k_upper):
            reasons.append("zero_or_nonfinite_scale")
        else:
            bound_lower, bound_upper = QUALIFIED_ASSUMPTION_BOUNDS["earnings_multiple"]
            feasible_lower = max(bound_lower, k_lower)
            feasible_upper = min(bound_upper, k_upper)
            if feasible_lower > feasible_upper:
                reasons.append("empty_feasible_set")
            else:
                interval = [feasible_lower, feasible_upper]

    out.update(
        {
            "refusal_reasons": list(dict.fromkeys(reasons)),
            "conditional_on": {
                "sales_growth_pct": state["assumptions"].get("sales_growth_pct"),
                "margin_delta_pp": state["assumptions"].get("margin_delta_pp"),
            },
            "price_band": [lower, upper],
            "earnings_multiple_interval": interval,
            "compatibility_mass": None,
            "compatibility_mass_status": "independent_joint_reference_not_qualified",
        }
    )
    out["valid"] = not out["refusal_reasons"] and interval is not None
    return out
