"""User-adjustable valuation assumptions (B-F07-2).

No network and no clock. Reads a valuation_scenario.v1 blob and the local
issuer event spines through their existing readers, then emits
valuation_scenario_controls.v1 for the sandbox panel. The three V1 server
cards stay the authority; this module only names the three free parameters
and evaluates the same closed-form per-share identity at caller-supplied
points.

Range derivation (frozen spec section 2.3, verbatim): each range is the V1
frozen triple's own span, widened to a round number that still contains
every V1 preset with headroom. V1 spans growth [-2, 7] -> [-10, 20];
margin [-1.5, 1.5] -> [-3.0, 3.0]; multiple [14, 22] -> [8, 35]. Defaults
are exactly V1's base case, read from CONTROLS (never re-typed as literals
next to the derived per_share), so the panel's first paint is numerically
identical to the Base card under the same round2 rule.

Rounding: do not use Python round() (banker's rounding; JS has no equivalent).
round2(v) = floor(v * 100 + 0.5) / 100 for v > 0. The panel never paints
v <= 0. server_default.per_share is computed through the same rule.

SCENARIOS and MISSING_LABELS are imported read-only from
engine.valuation_scenario so presets cannot drift from V1's frozen triples
and a future null path can reuse V1 diction without re-typing.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
from datetime import datetime

from engine.valuation_scenario import MISSING_LABELS, SCENARIOS

log = logging.getLogger(__name__)

# Each range is the V1 frozen triple's own span, widened to a round number
# that still contains every V1 preset with headroom. V1 spans growth
# [-2, 7] -> [-10, 20]; margin [-1.5, 1.5] -> [-3.0, 3.0]; multiple
# [14, 22] -> [8, 35]. Defaults are exactly V1's base case.
CONTROLS = (
    {"key": "sales_growth_pct", "min": -10, "max": 20, "step": 0.5, "default": 3},
    {"key": "margin_delta_pp", "min": -3.0, "max": 3.0, "step": 0.1, "default": 0},
    {"key": "earnings_multiple", "min": 8, "max": 35, "step": 1, "default": 18},
)

_MARGIN_BASE_FLOOR = 0.01

# Imported read-only; kept bound so a future null path can reuse V1 diction
# without re-typing. The sandbox panel's too-thin sentence is the B-F07-2
# verbatim copy, not MISSING_LABELS["margin_too_thin"].
_V1_MISSING_LABELS = MISSING_LABELS

QUALIFIED_INPUT_SCHEMA = "valuation_scenario_qualified_input.v1"
FORWARD_EVALUATION_SCHEMA = "valuation_scenario_forward_evaluation.v1"
REQUIRED_MULTIPLE_SCHEMA = "valuation_scenario_required_multiple.v1"
OWNER_QUALIFICATION_UNAVAILABLE = "OWNER_QUALIFICATION_UNAVAILABLE"
_FORWARD_MODEL_FAMILY = "earnings_multiple"
_FORWARD_MODEL_VERSION = "B-F07-A6.v1"
_REQUIRED_MULTIPLE_VERSION = "K3E-A7.v1"
_DISPLAY_POLICY = "python_round_half_even_2dp"
_SUPPORTED_TICKER = "AAPL"
_SUPPORTED_CURRENCY = "USD"
_SUPPORTED_ACCOUNTING_BASIS = "reported_gaap"
_SUPPORTED_SHARE_IDENTITY = "outstanding"
_SUPPORTED_CORPORATE_ACTION_BASIS = "split_adjusted_v1"
_SUPPORTED_VALUATION_OBJECT = "equity_per_share"
_SUPPORTED_USE = "research_display"


def _refusal(code: str, field: str | None = None) -> dict:
    row = {"code": code}
    if field is not None:
        row["field"] = field
    return row


def _canonical_digest(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _parse_aware_timestamp(value: object, field: str, refusals: list[dict]):
    if not isinstance(value, str) or not value.strip():
        refusals.append(_refusal("MISSING_RECEIPT_FIELD", field))
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        refusals.append(_refusal("INVALID_TIMESTAMP", field))
        return None
    if parsed.tzinfo is None:
        refusals.append(_refusal("INVALID_TIMESTAMP", field))
        return None
    return parsed


def _required_text(container: dict, key: str, prefix: str, refusals: list[dict]):
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        refusals.append(_refusal("MISSING_RECEIPT_FIELD", f"{prefix}.{key}"))
        return None
    return value.strip()


def _strict_number(value: object, field: str, refusals: list[dict]):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        refusals.append(_refusal("INVALID_NUMERIC_INPUT", field))
        return None
    number = float(value)
    if not math.isfinite(number):
        refusals.append(_refusal("INVALID_NUMERIC_INPUT", field))
        return None
    return number


def _control_bound(key: str) -> tuple[float, float]:
    for row in CONTROLS:
        if row["key"] == key:
            return float(row["min"]), float(row["max"])
    raise KeyError(key)


def _validate_parameter(
    key: str,
    value: object,
    refusals: list[dict],
) -> float | None:
    number = _strict_number(value, f"assumptions.{key}", refusals)
    if number is None:
        return None
    low, high = _control_bound(key)
    if number < low or number > high:
        refusals.append(_refusal("PARAMETER_OUT_OF_BOUNDS", f"assumptions.{key}"))
        return number
    return number


def _qualified_invalid(schema: str, refusals: list[dict], **extra) -> dict:
    blob = {
        "schema": schema,
        "valid": False,
        "refusals": refusals,
        "tier": "research_display_only",
        "authority": "descriptive_context_only",
        "financial_influence": False,
    }
    blob.update(extra)
    return blob


def _validate_qualified_input(receipt: object) -> tuple[dict | None, list[dict]]:
    refusals: list[dict] = []
    if not isinstance(receipt, dict):
        return None, [_refusal("INVALID_RECEIPT", "receipt")]
    if receipt.get("schema") != QUALIFIED_INPUT_SCHEMA:
        refusals.append(_refusal("INVALID_RECEIPT_SCHEMA", "schema"))

    ticker = receipt.get("ticker")
    if ticker != _SUPPORTED_TICKER:
        refusals.append(_refusal("UNSUPPORTED_TICKER", "ticker"))

    requested_use = _required_text(receipt, "requested_use", "receipt", refusals)
    if requested_use is not None and requested_use != _SUPPORTED_USE:
        refusals.append(_refusal("UNSUPPORTED_USE", "receipt.requested_use"))

    financial = receipt.get("financial")
    price = receipt.get("price")
    if not isinstance(financial, dict):
        refusals.append(_refusal("MISSING_RECEIPT_FIELD", "financial"))
        financial = {}
    if not isinstance(price, dict):
        refusals.append(_refusal("MISSING_RECEIPT_FIELD", "price"))
        price = {}

    fin_receipt = _required_text(financial, "receipt_id", "financial", refusals)
    px_receipt = _required_text(price, "receipt_id", "price", refusals)
    issuer_ref = _required_text(financial, "issuer_ref", "financial", refusals)
    fin_security = _required_text(financial, "security_ref", "financial", refusals)
    px_security = _required_text(price, "security_ref", "price", refusals)
    fin_currency = _required_text(financial, "currency", "financial", refusals)
    px_currency = _required_text(price, "currency", "price", refusals)
    accounting_basis = _required_text(financial, "accounting_basis", "financial", refusals)
    fiscal_period = _required_text(financial, "fiscal_period", "financial", refusals)
    period_end = _required_text(financial, "period_end", "financial", refusals)
    fin_share_identity = _required_text(financial, "share_identity", "financial", refusals)
    px_share_identity = _required_text(price, "share_identity", "price", refusals)
    fin_action_basis = _required_text(financial, "corporate_action_basis", "financial", refusals)
    px_action_basis = _required_text(price, "corporate_action_basis", "price", refusals)
    valuation_object = _required_text(price, "valuation_object", "price", refusals)
    price_session = _required_text(price, "session", "price", refusals)

    if fin_security is not None and px_security is not None and fin_security != px_security:
        refusals.append(_refusal("IDENTITY_MISMATCH", "price.security_ref"))
    if fin_currency is not None and px_currency is not None and fin_currency != px_currency:
        refusals.append(_refusal("CURRENCY_MISMATCH", "price.currency"))
    elif fin_currency is not None and fin_currency != _SUPPORTED_CURRENCY:
        refusals.append(_refusal("UNSUPPORTED_CURRENCY", "financial.currency"))
    if (
        fin_share_identity is not None
        and px_share_identity is not None
        and fin_share_identity != px_share_identity
    ):
        refusals.append(_refusal("SHARE_IDENTITY_MISMATCH", "price.share_identity"))
    elif fin_share_identity is not None and fin_share_identity != _SUPPORTED_SHARE_IDENTITY:
        refusals.append(_refusal("UNSUPPORTED_SHARE_IDENTITY", "financial.share_identity"))
    if (
        fin_action_basis is not None
        and px_action_basis is not None
        and fin_action_basis != px_action_basis
    ):
        refusals.append(
            _refusal("CORPORATE_ACTION_BASIS_MISMATCH", "price.corporate_action_basis")
        )
    elif fin_action_basis is not None and fin_action_basis != _SUPPORTED_CORPORATE_ACTION_BASIS:
        refusals.append(
            _refusal("UNSUPPORTED_CORPORATE_ACTION_BASIS", "financial.corporate_action_basis")
        )
    if accounting_basis is not None and accounting_basis != _SUPPORTED_ACCOUNTING_BASIS:
        refusals.append(_refusal("UNSUPPORTED_ACCOUNTING_BASIS", "financial.accounting_basis"))
    if valuation_object is not None and valuation_object != _SUPPORTED_VALUATION_OBJECT:
        refusals.append(_refusal("UNSUPPORTED_VALUATION_OBJECT", "price.valuation_object"))

    for prefix, leg in (("financial", financial), ("price", price)):
        uses = leg.get("permitted_uses")
        if (
            not isinstance(uses, list)
            or requested_use is None
            or requested_use not in uses
        ):
            refusals.append(_refusal("RIGHTS_BLOCKED", f"{prefix}.permitted_uses"))

    cutoff = _parse_aware_timestamp(
        receipt.get("decision_cutoff"),
        "receipt.decision_cutoff",
        refusals,
    )
    fin_available = _parse_aware_timestamp(
        financial.get("available_at"),
        "financial.available_at",
        refusals,
    )
    px_observed = _parse_aware_timestamp(
        price.get("observed_at"),
        "price.observed_at",
        refusals,
    )
    if cutoff is not None:
        if fin_available is not None and fin_available > cutoff:
            refusals.append(_refusal("CUTOFF_VIOLATION", "financial.available_at"))
        if px_observed is not None and px_observed > cutoff:
            refusals.append(_refusal("CUTOFF_VIOLATION", "price.observed_at"))

    net_income = _strict_number(financial.get("net_income"), "financial.net_income", refusals)
    revenue = _strict_number(financial.get("revenue"), "financial.revenue", refusals)
    shares = _strict_number(financial.get("shares"), "financial.shares", refusals)
    price_value = _strict_number(price.get("value"), "price.value", refusals)
    for field, number in (
        ("financial.net_income", net_income),
        ("financial.revenue", revenue),
        ("financial.shares", shares),
        ("price.value", price_value),
    ):
        if number is not None and number <= 0:
            refusals.append(_refusal("NONPOSITIVE_INPUT", field))

    if refusals:
        return None, refusals

    state = {
        "ticker": ticker,
        "requested_use": requested_use,
        "decision_cutoff": receipt["decision_cutoff"],
        "financial_receipt_id": fin_receipt,
        "price_receipt_id": px_receipt,
        "issuer_ref": issuer_ref,
        "security_ref": fin_security,
        "currency": fin_currency,
        "accounting_basis": accounting_basis,
        "fiscal_period": fiscal_period,
        "period_end": period_end,
        "share_identity": fin_share_identity,
        "corporate_action_basis": fin_action_basis,
        "valuation_object": valuation_object,
        "price_session": price_session,
        "net_income": net_income,
        "revenue": revenue,
        "shares": shares,
        "price": price_value,
        "receipt_digest": _canonical_digest(receipt),
    }
    return state, []


def _forward_scale(
    state: dict,
    sales_growth_pct: float,
    margin_delta_pp: float,
) -> tuple[dict | None, list[dict]]:
    refusals: list[dict] = []
    ni = state["net_income"]
    revenue = state["revenue"]
    shares = state["shares"]
    net_margin_base = ni / revenue
    if not math.isfinite(net_margin_base):
        return None, [_refusal("ZERO_OR_NONFINITE_SCALE", "financial.net_margin_base")]
    if abs(net_margin_base) < _MARGIN_BASE_FLOOR:
        return None, [_refusal("MARGIN_BASE_TOO_THIN", "financial.net_margin_base")]
    adjusted_margin = net_margin_base + (margin_delta_pp / 100.0)
    if adjusted_margin <= 0:
        return None, [_refusal("ADJUSTED_MARGIN_NONPOSITIVE", "assumptions.margin_delta_pp")]

    growth_factor = 1.0 + sales_growth_pct / 100.0
    margin_factor = 1.0 + (margin_delta_pp / 100.0) / net_margin_base
    first = ni * growth_factor
    second = first * margin_factor
    for field, value in (
        ("net_margin_base", net_margin_base),
        ("growth_factor", growth_factor),
        ("margin_factor", margin_factor),
        ("income_after_growth", first),
        ("income_after_margin", second),
    ):
        if not math.isfinite(value):
            refusals.append(_refusal("NONFINITE_FORWARD_INTERMEDIATE", field))
    if refusals:
        return None, refusals
    scale = second / shares
    if not math.isfinite(scale) or scale <= 0:
        return None, [_refusal("ZERO_OR_NONFINITE_SCALE", "per_share_scale")]
    return {
        "net_margin_base": net_margin_base,
        "growth_factor": growth_factor,
        "margin_factor": margin_factor,
        "income_after_growth": first,
        "income_after_margin": second,
        "per_share_scale": scale,
    }, []


def _forward_unrounded(
    state: dict,
    sales_growth_pct: float,
    margin_delta_pp: float,
    earnings_multiple: float,
) -> tuple[float | None, dict | None, list[dict]]:
    scale_state, refusals = _forward_scale(state, sales_growth_pct, margin_delta_pp)
    if refusals:
        return None, scale_state, refusals
    third = scale_state["income_after_margin"] * earnings_multiple
    if not math.isfinite(third):
        return None, scale_state, [_refusal("NONFINITE_FORWARD_INTERMEDIATE", "equity_value")]
    raw = third / state["shares"]
    if not math.isfinite(raw):
        return None, scale_state, [_refusal("NONFINITE_FORWARD_INTERMEDIATE", "per_share_value")]
    if raw <= 0:
        return None, scale_state, [_refusal("NONPOSITIVE_FORWARD_VALUE", "per_share_value")]
    scale_state = dict(scale_state)
    scale_state["equity_value"] = third
    scale_state["per_share_value"] = raw
    return raw, scale_state, []


def _forward_common_fields(state: dict) -> dict:
    return {
        "model_family": _FORWARD_MODEL_FAMILY,
        "model_version": _FORWARD_MODEL_VERSION,
        "ticker": state["ticker"],
        "issuer_ref": state["issuer_ref"],
        "security_ref": state["security_ref"],
        "valuation_object": state["valuation_object"],
        "currency": state["currency"],
        "accounting_basis": state["accounting_basis"],
        "fiscal_period": state["fiscal_period"],
        "period_end": state["period_end"],
        "share_identity": state["share_identity"],
        "corporate_action_basis": state["corporate_action_basis"],
        "decision_cutoff": state["decision_cutoff"],
        "requested_use": state["requested_use"],
        "input_refs": {
            "financial_receipt_id": state["financial_receipt_id"],
            "price_receipt_id": state["price_receipt_id"],
        },
        "receipt_digest": state["receipt_digest"],
        "accounting": {
            "debt_bridge": "NOT_APPLICABLE",
            "terminal_growth": "NOT_APPLICABLE",
            "terminal_value_share": "NOT_APPLICABLE",
        },
    }


def _owner_qualification_unavailable(schema: str, **extra) -> dict:
    return _qualified_invalid(
        schema,
        [_refusal(OWNER_QUALIFICATION_UNAVAILABLE)],
        **extra,
    )


def _evaluate_qualified_assumptions_internal(
    state: dict,
    *,
    sales_growth_pct: object,
    margin_delta_pp: object,
    earnings_multiple: object,
) -> dict:
    """Fixture/testing-only forward math over an already-validated owner-shaped state.

    Not a production qualification path. Callers must not treat a passing receipt
    validation as attested owner qualification.
    """
    params_refusals: list[dict] = []
    g = _validate_parameter("sales_growth_pct", sales_growth_pct, params_refusals)
    d = _validate_parameter("margin_delta_pp", margin_delta_pp, params_refusals)
    k = _validate_parameter("earnings_multiple", earnings_multiple, params_refusals)
    if params_refusals:
        return _qualified_invalid(
            FORWARD_EVALUATION_SCHEMA,
            params_refusals,
            **_forward_common_fields(state),
        )
    assert g is not None and d is not None and k is not None
    raw, steps, forward_refusals = _forward_unrounded(state, g, d, k)
    if forward_refusals:
        return _qualified_invalid(
            FORWARD_EVALUATION_SCHEMA,
            forward_refusals,
            **_forward_common_fields(state),
        )
    return {
        "schema": FORWARD_EVALUATION_SCHEMA,
        "valid": True,
        "refusals": [],
        "tier": "research_display_only",
        "authority": "descriptive_context_only",
        "financial_influence": False,
        "evidence_tier": "fixture_testing_only_not_attested",
        **_forward_common_fields(state),
        "assumptions": {
            "sales_growth_pct": sales_growth_pct,
            "margin_delta_pp": margin_delta_pp,
            "earnings_multiple": earnings_multiple,
        },
        "unrounded_per_share": raw,
        "display_per_share": round(raw, 2),
        "display_policy": _DISPLAY_POLICY,
        "forward_steps": steps,
    }


def evaluate_qualified_assumptions(
    receipt: object,
    *,
    sales_growth_pct: object,
    margin_delta_pp: object,
    earnings_multiple: object,
) -> dict:
    """Public A6 owner-qualified path.

    Fail closed until incumbent owners supply a complete positive qualification
    bundle (Data OS binding, attested FIF facts, owner price/session receipt,
    permitted-use decision, cutoff compatibility). Caller-authored qualified-input
    bundles are never accepted at this seam.
    """
    del receipt, sales_growth_pct, margin_delta_pp, earnings_multiple
    return _owner_qualification_unavailable(
        FORWARD_EVALUATION_SCHEMA,
        model_family=_FORWARD_MODEL_FAMILY,
        model_version=_FORWARD_MODEL_VERSION,
    )


def _required_earnings_multiple_internal(
    state: dict,
    *,
    sales_growth_pct: object,
    margin_delta_pp: object,
    price_tolerance: object,
) -> dict:
    """Fixture/testing-only A7 inverse over an already-validated owner-shaped state."""
    params_refusals: list[dict] = []
    g = _validate_parameter("sales_growth_pct", sales_growth_pct, params_refusals)
    d = _validate_parameter("margin_delta_pp", margin_delta_pp, params_refusals)
    tol = _strict_number(price_tolerance, "price_tolerance", params_refusals)
    if tol is not None and tol < 0:
        params_refusals.append(_refusal("INVALID_TOLERANCE", "price_tolerance"))
    inverse_common = _forward_common_fields(state)
    inverse_common["model_version"] = _REQUIRED_MULTIPLE_VERSION
    if params_refusals:
        return _qualified_invalid(REQUIRED_MULTIPLE_SCHEMA, params_refusals, **inverse_common)
    assert g is not None and d is not None and tol is not None
    if state["price"] - tol <= 0:
        return _qualified_invalid(
            REQUIRED_MULTIPLE_SCHEMA,
            [_refusal("INVALID_TOLERANCE", "price_tolerance")],
            **inverse_common,
        )

    scale_state, scale_refusals = _forward_scale(state, g, d)
    if scale_refusals:
        # A7 names a collapsed scale explicitly because it makes the inverse
        # undefined, even when the forward path would merely have no value.
        codes = {item["code"] for item in scale_refusals}
        if "ZERO_OR_NONFINITE_SCALE" not in codes and any(
            item["code"] == "NONFINITE_FORWARD_INTERMEDIATE" for item in scale_refusals
        ):
            scale_refusals.append(_refusal("ZERO_OR_NONFINITE_SCALE", "per_share_scale"))
        return _qualified_invalid(
            REQUIRED_MULTIPLE_SCHEMA,
            scale_refusals,
            **inverse_common,
        )

    scale = scale_state["per_share_scale"]
    if not math.isfinite(scale) or scale <= 0:
        return _qualified_invalid(
            REQUIRED_MULTIPLE_SCHEMA,
            [_refusal("ZERO_OR_NONFINITE_SCALE", "per_share_scale")],
            **inverse_common,
        )

    required = state["price"] / scale
    if not math.isfinite(required) or required <= 0:
        return _qualified_invalid(
            REQUIRED_MULTIPLE_SCHEMA,
            [_refusal("ZERO_OR_NONFINITE_SCALE", "required_multiple")],
            **inverse_common,
        )
    multiple_min, multiple_max = _control_bound("earnings_multiple")
    exact_in_bounds = multiple_min <= required <= multiple_max

    lower_price = state["price"] - tol
    upper_price = state["price"] + tol
    interval_lower = max(multiple_min, lower_price / scale)
    interval_upper = min(multiple_max, upper_price / scale)
    interval_nonempty = (
        math.isfinite(interval_lower)
        and math.isfinite(interval_upper)
        and interval_lower <= interval_upper
    )

    # Forward-substitute through the exact owner operation order. Do not call
    # the public A6 wrapper here because the exact inverse must remain visible
    # even when it lands outside declared parameter bounds.
    forward_raw, _, forward_refusals = _forward_unrounded(state, g, d, required)
    residual = None if forward_raw is None else forward_raw - state["price"]
    inverse_refusals: list[dict] = list(forward_refusals)
    if not exact_in_bounds:
        inverse_refusals.append(
            _refusal("REQUIRED_MULTIPLE_OUT_OF_BOUNDS", "required_multiple")
        )
    if residual is None or not math.isfinite(residual) or abs(residual) > tol:
        inverse_refusals.append(
            _refusal("FORWARD_RESIDUAL_EXCEEDS_TOLERANCE", "forward_check.residual")
        )

    mu = scale_state["net_margin_base"]
    u = scale_state["growth_factor"]
    v = scale_state["margin_factor"]
    f_value = forward_raw if forward_raw is not None else state["price"]
    jacobian = [
        f_value / (100.0 * u),
        f_value / (100.0 * mu * v),
        f_value / required,
    ]
    nullspace = [
        [1.0, 0.0, -required / (100.0 * u)],
        [0.0, 1.0, -required / (100.0 * mu * v)],
    ]
    if not all(math.isfinite(x) for x in jacobian + nullspace[0] + nullspace[1]):
        inverse_refusals.append(_refusal("NONFINITE_JACOBIAN", "identification"))

    return {
        "schema": REQUIRED_MULTIPLE_SCHEMA,
        "valid": not inverse_refusals,
        "refusals": inverse_refusals,
        "tier": "research_display_only",
        "authority": "descriptive_context_only",
        "financial_influence": False,
        "evidence_tier": "fixture_testing_only_not_attested",
        **_forward_common_fields(state),
        "model_version": _REQUIRED_MULTIPLE_VERSION,
        "locked_assumptions": {
            "sales_growth_pct": g,
            "margin_delta_pp": d,
        },
        "price_target": state["price"],
        "price_tolerance": tol,
        "required_multiple": required,
        "multiple_bounds": {"min": multiple_min, "max": multiple_max},
        "forward_check": {
            "unrounded_per_share": forward_raw,
            "residual": residual,
            "within_tolerance": residual is not None and abs(residual) <= tol,
        },
        "feasible_multiple_interval": {
            "lower": interval_lower,
            "upper": interval_upper,
            "nonempty": interval_nonempty,
            "definition": "declared_price_band_intersection_not_exact_inverse_clamping",
        },
        "identification": {
            "parameter_dimension": 3,
            "independent_price_observations": 1,
            "jacobian_rank": 1,
            "nullspace_dimension": 2,
            "conditional_root_count": 1,
            "full_parameter_set_identified": False,
            "conditioning": {
                "locked": ["sales_growth_pct", "margin_delta_pp"],
                "solved": ["earnings_multiple"],
            },
            "jacobian": jacobian,
            "nullspace_basis": nullspace,
        },
        "prior": {"status": "NOT_USED"},
        "compatibility_mass": {
            "status": "UNAVAILABLE",
            "value": None,
            "reason": "INDEPENDENT_JOINT_REFERENCE_NOT_QUALIFIED",
        },
    }


def required_earnings_multiple(
    receipt: object,
    *,
    sales_growth_pct: object,
    margin_delta_pp: object,
    price_tolerance: object,
) -> dict:
    """Public A7 owner-qualified path.

    Fail closed until incumbent owners supply a complete positive qualification
    bundle. Caller-authored qualified-input bundles are never accepted.
    """
    del receipt, sales_growth_pct, margin_delta_pp, price_tolerance
    return _owner_qualification_unavailable(
        REQUIRED_MULTIPLE_SCHEMA,
        model_family=_FORWARD_MODEL_FAMILY,
        model_version=_REQUIRED_MULTIPLE_VERSION,
    )


def _bridge_for_issuer(event_class: object):
    from engine import valuation_event_bridge as _veb

    return _veb.bridge_for_issuer(event_class)


def latest_issuer_spine_event_class(ticker: object) -> str | None:
    """Read the latest non-null issuer class from the local event spines.

    Chronicle JSONL and the capital-structure parquet ledger are read through
    their engine-owned readers. Collector modules are not imported.
    """
    if not isinstance(ticker, str) or not ticker.strip():
        return None
    wanted = ticker.strip().upper()
    try:
        return _select_latest_classified_event_class(wanted)
    except Exception as exc:
        log.warning("valuation: issuer event lookup failed: %s", exc)
        return None


def _select_latest_classified_event_class(wanted: str) -> str | None:
    from engine.chronicle import spine as chronicle_spine
    from engine.capital_structure.event_versions_io import iter_classified_spine_events
    from engine.capital_structure.spine_paths import chronicle_events_path

    events = list(chronicle_spine.load_events_jsonl(chronicle_events_path()))
    for event in iter_classified_spine_events(wanted):
        events.append({
            "id": event["event_id"],
            "tickers": [event["issuer"]["ticker"]],
            "kind": event["event"]["subtype"],
            "ts": event["point_in_time"]["available_at"],
        })
    latest_key = None
    latest_event = None
    for event in events:
        if not isinstance(event, dict):
            continue
        tickers = event.get("tickers")
        if not isinstance(tickers, list) or wanted not in {
            str(item).strip().upper() for item in tickers
        }:
            continue
        event_class = str(event.get("kind") or "").strip()
        if not event_class or _bridge_for_issuer(event_class) is None:
            continue
        available = event.get("ts") or event.get("date")
        if not available:
            continue
        key = (str(available), str(event.get("id") or ""))
        if latest_key is None or key > latest_key:
            latest_key = key
            latest_event = event
    if latest_event is None:
        return None
    return str(latest_event["kind"]).strip()


def _issuer_event_class(v1_blob: dict) -> str | None:
    return latest_issuer_spine_event_class(v1_blob.get("ticker"))


def latest_issuer_event_record(ticker: object) -> tuple[dict | None, bool]:
    """(latest event record, reader_ok).

    ``reader_ok`` is False only when the readers themselves failed. A healthy
    reader that simply has no events for this issuer returns ``(None, True)``,
    so "we could not look" and "there is nothing" stay distinguishable —
    collapsing them is what makes a silent degradation read as a confident
    "nothing on file".
    """
    if not isinstance(ticker, str) or not ticker.strip():
        return None, True
    wanted = ticker.strip().upper()
    try:
        from engine.chronicle import spine as chronicle_spine
        from engine.capital_structure.event_versions_io import iter_classified_spine_events
        from engine.capital_structure.spine_paths import chronicle_events_path

        events = [
            e for e in chronicle_spine.load_events_jsonl(chronicle_events_path())
            if isinstance(e, dict) and wanted in {
                str(x).strip().upper() for x in (e.get("tickers") or [])
            }
        ]
        for event in iter_classified_spine_events(wanted):
            events.append({
                "id": event["event_id"],
                "tickers": [event["issuer"]["ticker"]],
                "kind": event["event"]["subtype"],
                "ts": event["point_in_time"]["available_at"],
            })
    except Exception as exc:
        log.warning("valuation: issuer event record lookup failed: %s", exc)
        return None, False
    dated = [e for e in events if (e.get("ts") or e.get("date"))]
    if not dated:
        return None, True
    return max(dated, key=lambda e: str(e.get("ts") or e.get("date"))), True


def issuer_guidance_hits(ticker: object) -> list[dict]:
    """SEC 8-K directional guidance hits for one issuer.

    Delegates to engine.guidance_gap, which already owns that parquet. No new
    collector, no second store, and no direct file access from this module.
    """
    try:
        from engine.guidance_gap import hits_for_ticker

        return hits_for_ticker(ticker)
    except Exception as exc:  # noqa: BLE001 — additive, never fatal
        log.warning("valuation: guidance hits unreadable: %s", exc)
        return []


def _attach_event_proposal(blob: dict, as_of: object = None) -> dict:
    """Attach the typed AssumptionChange proposal and its shadow evaluation.

    Additive and never fatal: a failure here leaves the rest of the panel
    exactly as it was.
    """
    try:
        from engine import valuation_event_proposal as _vep

        ticker = blob.get("ticker")
        record, reader_ok = latest_issuer_event_record(ticker)
        if not reader_ok:
            proposal = _vep.proposal_reader_unavailable(blob)
        else:
            proposal = _vep.best_proposal(
                blob,
                chronicle_events=[record] if record else (),
                guidance_hits=issuer_guidance_hits(ticker),
                as_of=as_of,
            )
        blob["event_assumption_proposal"] = proposal
        blob["event_assumption_scenario"] = (
            _vep.evaluate_proposal(blob, proposal) if proposal else None
        )
    except Exception as exc:  # noqa: BLE001 — additive, never fatal
        log.warning("valuation: event assumption proposal failed: %s", exc)
        blob.setdefault("event_assumption_proposal", None)
        blob.setdefault("event_assumption_scenario", None)
    return blob


def round2(v):
    """Half-up to two decimals for v > 0. Matches JS Math.floor(v*100+0.5)/100."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f <= 0 or f == float("inf"):
        return None
    return math.floor(f * 100 + 0.5) / 100


def per_share_at(ni, revenue, shares, g, m_pp, mult):
    """Closed-form per-share value, or None when the setting is not paintable.

    Frozen identity (same four operations as V1, different rounding):
      per_share = ni * (1 + g/100) * (1 + (m_pp/100) / net_margin_base)
                  * mult / shares
    then round2. Returns None when any input is missing, shares is zero,
    |net_margin_base| is under the 1% floor, the per-setting margin gate
    fails (net_margin_base + m_pp/100 <= 0), or the result is not a
    positive finite number. No negative dollar figure is ever returned.
    """
    try:
        ni_f = float(ni)
        rev_f = float(revenue)
        sh_f = float(shares)
        g_f = float(g)
        m_f = float(m_pp)
        mult_f = float(mult)
    except (TypeError, ValueError):
        return None
    for x in (ni_f, rev_f, sh_f, g_f, m_f, mult_f):
        if x != x or x == float("inf") or x == float("-inf"):
            return None
    if ni_f <= 0 or rev_f == 0 or sh_f == 0:
        return None
    net_margin_base = ni_f / rev_f
    if abs(net_margin_base) < _MARGIN_BASE_FLOOR:
        return None
    if (net_margin_base + (m_f / 100.0)) <= 0:
        return None
    raw = ni_f * (1 + g_f / 100.0) * (1 + (m_f / 100.0) / net_margin_base) * mult_f / sh_f
    if raw != raw or raw <= 0 or raw == float("inf"):
        return None
    out = round2(raw)
    # round2 collapses a positive sub-half-cent raw to 0.0, and 0.00 is not a
    # paintable per-share value. Return None, which is what the JS twin returns
    # at the same point, so the two languages cannot disagree there.
    if out is None or out <= 0:
        return None
    return out


def _num(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:
        return None
    return f


def _control_defaults():
    return {c["key"]: c["default"] for c in CONTROLS}


def controls_blob(v1_blob, as_of=None):
    """Build valuation_scenario_controls.v1 from a V1 compute() blob, or None.

    Returns None when the V1 blob is missing, when net income is missing or
    not positive, when revenue is missing, when shares are missing or zero,
    or when V1's base scenario is not computable. When |net_margin_base| is
    under the 1% floor, returns a blob with too_thin_base True and no
    controls (the panel then renders only the single-line copy). Every key
    in the frozen contract is present on the interactive blob, or the whole
    blob is None. No key is ever 0 standing in for missing.
    """
    if not v1_blob or not isinstance(v1_blob, dict):
        return None
    base = v1_blob.get("base") or {}
    ni = _num((base.get("net_income") or {}).get("value"))
    revenue = _num((base.get("revenue") or {}).get("value"))
    shares = _num((base.get("share_count") or {}).get("value"))
    if ni is None or ni <= 0:
        return None
    if revenue is None:
        return None
    if shares is None or shares == 0:
        return None
    if revenue == 0:
        return None
    net_margin_base = ni / revenue

    ticker = v1_blob.get("ticker") or ""
    fy = v1_blob.get("fy")
    period_end = v1_blob.get("period_end")
    if fy is None or not period_end:
        return None

    latest_event_class = _issuer_event_class(v1_blob)
    if abs(net_margin_base) < _MARGIN_BASE_FLOOR:
        return _attach_event_proposal(as_of=as_of, blob={
            "schema": "valuation_scenario_controls.v1",
            "ticker": ticker,
            "tier": "research_display_only",
            "fy": fy,
            "period_end": period_end,
            "source": "SEC filings",
            "too_thin_base": True,
            "inputs": {
                "net_income": ni,
                "revenue": revenue,
                "shares": shares,
                "net_margin_base": net_margin_base,
            },
            "margin_base_floor": _MARGIN_BASE_FLOOR,
            "latest_event_bridge": _bridge_for_issuer(latest_event_class),
        })

    scenarios = v1_blob.get("scenarios") or []
    by_key = {s.get("key"): s for s in scenarios if isinstance(s, dict)}
    base_sc = by_key.get("base")
    if not base_sc:
        return None
    base_ps = base_sc.get("per_share")
    if not base_sc.get("computable") or base_ps is None or base_ps <= 0:
        return None

    defaults = _control_defaults()
    g = defaults["sales_growth_pct"]
    m_pp = defaults["margin_delta_pp"]
    mult = defaults["earnings_multiple"]
    default_ps = per_share_at(ni, revenue, shares, g, m_pp, mult)
    if default_ps is None:
        return None
    # Section 2.6 makes this an equality, not a coincidence: the sandbox's first
    # paint IS V1's Base card, so the two figures can never disagree on screen.
    # The rules can disagree in principle -- round2 here is half-up, V1's
    # round() is half-to-even, so an exact half-cent splits them -- and when
    # they do, the panel is not shown at all rather than contradicting the
    # authority directly above it. The null shape is the same one every other
    # unusable-V1 branch returns.
    if default_ps != base_ps:
        log.warning(
            "valuation_assumptions equality guard: issuer=%s sandbox_per_share=%s v1_base_per_share=%s",
            ticker,
            default_ps,
            base_ps,
        )
        return None

    presets = {}
    for key, g_s, m_s, mult_s in SCENARIOS:
        presets[key] = {
            "sales_growth_pct": g_s,
            "margin_delta_pp": m_s,
            "earnings_multiple": mult_s,
        }

    # The durable capital-structure spine is read directly; no new collector
    # and no network access are introduced.
    _latest_event_bridge = _bridge_for_issuer(latest_event_class)

    return _attach_event_proposal(as_of=as_of, blob={
        "schema": "valuation_scenario_controls.v1",
        "ticker": ticker,
        "tier": "research_display_only",
        "fy": fy,
        "period_end": period_end,
        "source": "SEC filings",
        "inputs": {
            "net_income": ni,
            "revenue": revenue,
            "shares": shares,
            "net_margin_base": net_margin_base,
        },
        "margin_base_floor": _MARGIN_BASE_FLOOR,
        "controls": [dict(c) for c in CONTROLS],
        "presets": presets,
        "server_default": {
            "sales_growth_pct": g,
            "margin_delta_pp": m_pp,
            "earnings_multiple": mult,
            "per_share": default_ps,
        },
        "latest_event_bridge": _latest_event_bridge,
    })
