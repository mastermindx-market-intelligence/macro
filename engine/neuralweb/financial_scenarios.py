"""Bounded financial arithmetic for supplied assumptions, never market/signal facts.

No reads, writes, retrieval, provider calls or inferred zero adjustments. The model
must establish a common currency/scale/accounting basis before calling this tool.
"""
from __future__ import annotations

import re
from decimal import (Context, Decimal, DecimalException, DivisionByZero, Inexact,
                     InvalidOperation, Overflow, ROUND_HALF_EVEN, Underflow, localcontext)

TOOL_NAME = "analyze_financial_scenario"
_FIELDS = (
    "revenue", "gross_margin_pct", "operating_expenses",
    "working_capital_increase", "other_operating_cash_adjustments", "capital_expenditure",
)
_UNITS = ("ones", "thousands", "millions", "billions")
_REQUIREMENTS = {
    "gross_profit": ("revenue", "gross_margin_pct"),
    "operating_profit": ("revenue", "gross_margin_pct", "operating_expenses"),
    "simplified_operating_cash": ("revenue", "gross_margin_pct", "operating_expenses",
                                  "other_operating_cash_adjustments", "working_capital_increase"),
    "simplified_cash_after_capex": _FIELDS,
}
_MAX_ABS = Decimal("1000000000000000")
_MARGIN_MIN_PCT = Decimal("-1000")
_MARGIN_MAX_PCT = Decimal("100")
_NONNEGATIVE_FIELDS = frozenset({"revenue", "operating_expenses", "capital_expenditure"})
_DECIMAL_PATTERN = r"[+-]?(?:[0-9]+(?:\.[0-9]{0,6})?|\.[0-9]{1,6})"
_DECIMAL_TEXT = re.compile(_DECIMAL_PATTERN)
_ERROR = "invalid_financial_scenario"
_ARITHMETIC_ERROR = "financial_scenario_arithmetic_unavailable"


def _bounds(name: str) -> tuple[Decimal, Decimal]:
    if name == "gross_margin_pct":
        return _MARGIN_MIN_PCT, _MARGIN_MAX_PCT
    if name in _NONNEGATIVE_FIELDS:
        return Decimal(0), _MAX_ABS
    return -_MAX_ABS, _MAX_ABS


def _number(value: object, name: str) -> Decimal | None:
    if value is None:
        return None
    if type(value) not in (int, float, str):
        raise ValueError(_ERROR)
    text = str(value)
    if len(text) > 40 or (isinstance(value, str) and not _DECIMAL_TEXT.fullmatch(text)):
        raise ValueError(_ERROR)
    number = Decimal(text)
    if not number.is_finite() or number.as_tuple().exponent < -6:
        raise ValueError(_ERROR)
    minimum, maximum = _bounds(name)
    if number < minimum or number > maximum:
        raise ValueError(_ERROR)
    return number


def _period(raw: object) -> dict[str, Decimal | None]:
    if type(raw) is not dict or set(raw) - set(_FIELDS):
        raise ValueError(_ERROR)
    return {name: _number(raw.get(name), name) for name in _FIELDS}


def _text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    if value == 0:
        return "0"
    rendered = format(value, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _calculate(values: dict, output: str) -> Decimal:
    gross = values["revenue"] * values["gross_margin_pct"] / Decimal(100)
    if output == "gross_profit":
        return gross
    operating = gross - values["operating_expenses"]
    if output == "operating_profit":
        return operating
    cash = operating + values["other_operating_cash_adjustments"] - values["working_capital_increase"]
    return cash if output == "simplified_operating_cash" else cash - values["capital_expenditure"]


def _projection(values: dict) -> dict:
    missing = {output: [name for name in deps if values[name] is None]
               for output, deps in _REQUIREMENTS.items()}
    return {
        **{output: None if missing[output] else _text(_calculate(values, output))
           for output in _REQUIREMENTS},
        "inputs": {name: _text(value) for name, value in values.items()},
        "missing_inputs": missing,
    }


def _bridge(prior: dict, current: dict) -> dict:
    needed = ("revenue", "gross_margin_pct", "operating_expenses")
    missing = [f"{period}.{name}" for period, values in (("prior", prior), ("current", current))
               for name in needed if values[name] is None]
    if missing:
        return {"status": "unavailable", "missing_inputs": missing, "is_causal_estimate": False}
    revenue = (current["revenue"] - prior["revenue"]) * prior["gross_margin_pct"] / Decimal(100)
    margin = current["revenue"] * (current["gross_margin_pct"] - prior["gross_margin_pct"]) / Decimal(100)
    expenses = prior["operating_expenses"] - current["operating_expenses"]
    return {
        "status": "available", "missing_inputs": [], "is_causal_estimate": False,
        "revenue_effect_at_prior_margin": _text(revenue),
        "margin_effect_at_current_revenue": _text(margin),
        "operating_expense_effect": _text(expenses),
        "operating_profit_change": _text(revenue + margin + expenses),
        "method": "Prior-margin revenue bridge, then current-revenue margin bridge; order-dependent arithmetic, not causal evidence.",
    }


def _invalid_result() -> dict:
    return {
        "error": _ERROR,
        "is_context_only": True,
        "note": (
            "Use the closed scenario fields, a common unit/currency and finite decimals "
            "(at most 6 fractional places; gross margin -1000% to 100%; other amounts "
            "within +/-10^15 and nonnegative where specified). Leave unknown inputs "
            "null; never fill them with invented zeroes."
        ),
    }


def _arithmetic_unavailable_result() -> dict:
    return {
        "error": _ARITHMETIC_ERROR,
        "is_context_only": True,
        "note": (
            "The supplied inputs passed validation, but exact scenario arithmetic could "
            "not be completed. Do not reinterpret this as a bad input, a zero, or a "
            "financial conclusion."
        ),
    }


def analyze(params: object) -> dict:
    """Return exact decimal strings or explicit missing values; invalid input is opaque."""
    try:
        if type(params) is not dict or set(params) != {"unit", "currency", "prior", "current"}:
            raise ValueError(_ERROR)
        if not isinstance(params["unit"], str) or params["unit"] not in _UNITS:
            raise ValueError(_ERROR)
        currency = params["currency"]
        if currency is not None and (
            not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency)
        ):
            raise ValueError(_ERROR)
    except (ValueError, TypeError, OverflowError):
        return _invalid_result()

    # Fully explicit per-call context: do not inherit exponent limits, traps
    # or a mutated DefaultContext from another request/library. The admitted
    # input envelope and fixed equations fit exactly inside 64 decimal digits.
    arithmetic = Context(
        prec=64,
        rounding=ROUND_HALF_EVEN,
        Emin=-999999,
        Emax=999999,
        capitals=1,
        clamp=0,
        flags=[],
        traps=[InvalidOperation, DivisionByZero, Overflow, Underflow, Inexact],
    )
    with localcontext(arithmetic):
        # Parsing/validation failures are caller-contract errors. Arithmetic
        # failures after that boundary are a different state and must never be
        # mislabeled as "invalid input".
        try:
            prior, current = _period(params["prior"]), _period(params["current"])
        except (ValueError, TypeError, DecimalException, OverflowError):
            return _invalid_result()
        try:
            periods = {"prior": _projection(prior), "current": _projection(current)}
            bridge = _bridge(prior, current)
        except (DecimalException, OverflowError):
            return _arithmetic_unavailable_result()

    partial = any(
        missing
        for period in periods.values()
        for missing in period["missing_inputs"].values()
    )
    return {
        "schema": "brain.financial_scenario.v1",
        "status": "partial" if partial else "available",
        "authority": "analysis_only",
        "is_context_only": True,
        "input_basis": "unverified_supplied_assumptions",
        "unit": params["unit"],
        "currency": currency,
        "periods": periods,
        "operating_profit_bridge": bridge,
        "equations": {
            "gross_profit": "revenue * gross_margin_pct / 100",
            "operating_profit": "gross_profit - operating_expenses",
            "simplified_operating_cash": (
                "operating_profit + other_operating_cash_adjustments "
                "- working_capital_increase"
            ),
            "simplified_cash_after_capex": (
                "simplified_operating_cash - capital_expenditure"
            ),
        },
        "limits": [
            "Inputs are not verified market facts; no source, period, currency or accounting-basis validation is implied.",
            "Amounts must already share one scale, currency and comparable accounting definitions. No FX or period conversion is performed.",
            "Cash adjustments must explicitly include applicable noncash addbacks, cash taxes, cash interest and other operating adjustments. Missing is not zero.",
            "Cash figures are simplified scenario arithmetic, not reported cash-flow statements or an audited free-cash-flow measure.",
            "Growth and this bridge alone do not establish valuation, cause, a house signal or a trade decision.",
        ],
    }


_NUMBER_TYPES = ("number", "string", "null")


def tool_schema() -> dict:
    """A fresh schema for the existing Brain registry; no provider-specific tools."""
    descriptions = {
        "revenue": "Nonnegative revenue in the common amount unit.",
        "gross_margin_pct": "Gross margin in percent, e.g. 25 not 0.25; bounded to [-1000, 100] as a safety envelope, not an accounting-law claim.",
        "operating_expenses": "Nonnegative expenses below gross profit, in the common amount unit.",
        "working_capital_increase": "Net working-capital increase (cash use); a decrease is negative. Not the ending balance.",
        "other_operating_cash_adjustments": "Signed net operating cash adjustments beyond profit and working capital: noncash addbacks minus cash taxes/interest plus other adjustments. Supply 0 only when explicitly justified.",
        "capital_expenditure": "Nonnegative cash capital spending, in the common amount unit.",
    }
    def period_schema() -> dict:
        properties: dict[str, dict] = {}
        for name, description in descriptions.items():
            minimum, maximum = _bounds(name)
            properties[name] = {
                "type": list(_NUMBER_TYPES),
                "description": description,
                # JSON Schema applies numeric bounds only to number instances and
                # pattern/length only to string instances. Runtime remains the
                # authoritative Decimal parser for either representation.
                "minimum": int(minimum),
                "maximum": int(maximum),
                "maxLength": 40,
                "pattern": f"^(?:{_DECIMAL_PATTERN})$",
            }
        return {"type": "object", "additionalProperties": False, "properties": properties}
    return {
        "name": TOOL_NAME,
        "description": "Reconcile a supplied financial scenario with exact profit/cash arithmetic and a revenue/margin/expense bridge. Establish common units, periods and accounting basis first. Use unknown/null, not invented zero adjustments. Outputs are unverified-input analysis, not live facts, causal proof, valuation or house signals.",
        "input_schema": {"type": "object", "additionalProperties": False,
                         "required": ["unit", "currency", "prior", "current"],
                         "properties": {"unit": {"type": "string", "enum": list(_UNITS)},
                                        "currency": {"type": ["string", "null"], "pattern": "^[A-Z]{3}$",
                                                     "description": "Common currency label if known; null if not supplied. Do not infer currency."},
                                        "prior": period_schema(), "current": period_schema()}},
    }
