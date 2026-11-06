#!/usr/bin/env python3
"""Research-only B1/B2 numerical references and executable adversarial fixtures.

Python standard library only. No network, production imports, services, or writes
except an explicitly requested new results file. European Black-Scholes at r=q=0
is a deliberately limited reference model, not a production pricing engine.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
from pathlib import Path
import platform
from typing import Callable


class ContractError(ValueError):
    """Invalid API-level research contract; missing row data uses result states."""


def finite(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def positive(value):
    return finite(value) and value > 0


def checked_sum(values):
    try:
        result = math.fsum(values)
    except (OverflowError, ValueError) as exc:
        raise ContractError("aggregate_outside_finite_reference_range") from exc
    if not finite(result):
        raise ContractError("aggregate_outside_finite_reference_range")
    return result


def checked_scale(value, divisor):
    if value is None:
        return None
    result = value / divisor
    if not finite(result):
        raise ContractError("scaled_amount_outside_finite_reference_range")
    return result


@dataclass(frozen=True)
class Position:
    position_id: str
    underlying: str | None
    currency: str | None
    strike: float | None
    remaining_years: float | None
    iv: float | None
    signed_contracts: float | None
    multiplier: float | None
    kind: str | None
    exercise_style: str = "european"


@dataclass(frozen=True)
class Book:
    underlying: str
    currency: str
    positions: tuple[Position, ...] | None
    population_complete: bool


@dataclass(frozen=True)
class GammaUnit:
    currency: str = "USD"
    # A value of 1e6 means reported amounts are in millions of this currency.
    currency_units_per_output_unit: float = 1.0

    def metadata(self):
        if (not isinstance(self.currency, str) or len(self.currency) != 3
                or not self.currency.isascii() or not self.currency.isalpha() or not self.currency.isupper()):
            raise ContractError("invalid_gamma_currency")
        if not positive(self.currency_units_per_output_unit):
            raise ContractError("invalid_gamma_amount_scale")
        return {"quantity": "gamma_driven_delta_change_notional", "currency": self.currency,
                "currency_units_per_output_unit": self.currency_units_per_output_unit,
                "spot_shock_fraction": 0.01, "interpretation": "Gamma-driven delta change converted to notional per +1% local spot move",
                "excludes": "Delta*dS term in change of S*Delta; not full market-value change of hedge holdings"}


@dataclass(frozen=True)
class GammaValue:
    net: float | None
    gross_absolute: float | None
    unit: GammaUnit
    status: str = "qualified"
    reason: str | None = None


@dataclass(frozen=True)
class GammaTolerance:
    # Absolute component is in the SAME output units as GammaValue, not spot units.
    absolute: float = 1e-8
    relative: float = 1e-10

    def threshold(self, gross_absolute):
        if not finite(self.absolute) or self.absolute < 0 or not finite(self.relative) or self.relative < 0:
            raise ContractError("invalid_gamma_tolerance")
        result = self.absolute + self.relative * gross_absolute
        if not finite(result):
            raise ContractError("gamma_tolerance_overflow")
        return result


def european_greeks(spot, strike, remaining_years, iv, kind):
    """Per-underlying-unit long-option Greeks; r=q=0; no limiting expiry cases."""
    if not all(positive(x) for x in (spot, strike, remaining_years, iv)):
        raise ContractError("reference_model_requires_positive_spot_strike_time_iv")
    if kind not in ("call", "put"):
        raise ContractError("unknown_option_kind")
    total_vol = iv * math.sqrt(remaining_years)
    if not positive(total_vol):
        raise ContractError("invalid_total_volatility")
    # log(S)-log(K) avoids overflow of S/K for otherwise finite positive inputs.
    d1 = (math.log(spot) - math.log(strike)) / total_vol + 0.5 * total_vol
    if not finite(d1):
        raise ContractError("nonfinite_reference_d1")
    call_delta = 0.5 * math.erfc(-d1 / math.sqrt(2.0))
    delta = call_delta if kind == "call" else -0.5 * math.erfc(d1 / math.sqrt(2.0))
    gamma = math.exp(-0.5 * d1 * d1) / math.sqrt(2.0 * math.pi) / spot / total_vol
    if not finite(delta) or not finite(gamma):
        raise ContractError("nonfinite_reference_greek")
    return {"delta": delta, "gamma": gamma,
            "numerical_tail_saturation": gamma == 0.0 or abs(delta) in (0.0, 1.0)}


def scope_check(book):
    if not isinstance(book.population_complete, bool):
        raise ContractError("population_completeness_must_be_explicit_boolean")
    GammaUnit(book.currency).metadata()
    if not isinstance(book.underlying, str) or not book.underlying:
        raise ContractError("declared_underlying_required")
    if book.positions is None:
        return [], ["positions_unavailable"]
    if not all(isinstance(p, Position) for p in book.positions):
        raise ContractError("positions_must_use_reference_position_type")
    ids = [p.position_id for p in book.positions]
    reasons = []
    if any(not isinstance(x, str) or not x for x in ids):
        reasons.append("position_identity_unavailable")
    elif len(set(ids)) != len(ids):
        reasons.append("duplicate_position_identity")
    # Scope is checked BEFORE pricing eligibility; an invalid row cannot hide FX.
    if any(p.currency is None for p in book.positions):
        reasons.append("position_currency_unavailable")
    if any(p.currency is not None and p.currency != book.currency for p in book.positions):
        reasons.append("mixed_or_mismatched_currency")
    if any(p.underlying is None for p in book.positions):
        reasons.append("position_underlying_unavailable")
    if any(p.underlying is not None and p.underlying != book.underlying for p in book.positions):
        reasons.append("mixed_or_mismatched_underlying")
    return sorted(book.positions, key=lambda p: str(p.position_id)), reasons


def row_reasons(p):
    reasons = []
    for field in ("strike", "remaining_years", "iv", "multiplier"):
        value = getattr(p, field)
        if value is None:
            reasons.append(field + "_unavailable")
        elif not positive(value):
            reasons.append(field + "_must_be_positive_finite")
    if p.signed_contracts is None:
        reasons.append("signed_contracts_unavailable")
    elif not finite(p.signed_contracts):
        reasons.append("signed_contracts_must_be_finite")
    if p.kind not in ("call", "put"):
        reasons.append("option_kind_unavailable_or_unsupported")
    if p.exercise_style != "european":
        reasons.append("unsupported_exercise_style")
    return reasons


def evaluate_rows(book, spot, *, target_spot=None, elapsed_years=0.0, target_ivs=None):
    """Return deterministic, scoped eligible rows and explicit ineligible rows."""
    if not positive(spot) or (target_spot is not None and not positive(target_spot)):
        raise ContractError("spot_must_be_positive_finite")
    if not finite(elapsed_years) or elapsed_years < 0:
        raise ContractError("elapsed_years_must_be_nonnegative_finite")
    positions, scope_reasons = scope_check(book)
    overrides = {} if target_ivs is None else dict(target_ivs)
    if not scope_reasons and set(overrides) - {p.position_id for p in positions}:
        raise ContractError("unknown_position_in_target_iv_overrides")
    common = {"scope": {"underlying": book.underlying, "declared_currency": book.currency,
                         "population_complete": book.population_complete,
                         "scope_meaning": "caller-specified hypothetical book, not market/dealer coverage"},
              "input_row_count": None if book.positions is None else len(book.positions),
              "scope_reasons": scope_reasons, "rows": []}
    if scope_reasons:
        common.update(status="no_data" if book.positions is None else "rejected_scope", complete=False,
                      evaluated_row_count=0, eligible_row_count=0, unavailable_row_count=None,
                      unevaluated_due_to_scope_count=common["input_row_count"])
        return common
    for p in positions:
        reasons = row_reasons(p)
        row = {"position_id": p.position_id, "strike": p.strike if positive(p.strike) else None,
               "reasons": reasons, "eligible": False}
        if target_spot is not None:
            remaining = p.remaining_years - elapsed_years if finite(p.remaining_years) else None
            target_iv = overrides.get(p.position_id, p.iv)
            if not positive(remaining):
                reasons.append("target_expired_or_time_unavailable")
            if not positive(target_iv):
                reasons.append("target_iv_unavailable_or_invalid")
        if not reasons:
            try:
                g0 = european_greeks(spot, p.strike, p.remaining_years, p.iv, p.kind)
                shares = p.signed_contracts * p.multiplier
                row.update(portfolio_delta_units=shares * g0["delta"],
                           portfolio_gamma_units_per_spot=shares * g0["gamma"],
                           portfolio_gamma_notional_per_1pct=shares * g0["gamma"] * spot * (spot * 0.01),
                           initial_delta=g0["delta"], initial_gamma=g0["gamma"],
                           numerical_tail_saturation=g0["numerical_tail_saturation"])
                if target_spot is not None:
                    g1 = european_greeks(target_spot, p.strike, remaining, target_iv, p.kind)
                    # Direct difference of option deltas; never change in hedge market value.
                    dq = -shares * (g1["delta"] - g0["delta"])
                    row.update(target_delta=g1["delta"], target_iv=target_iv,
                               target_remaining_years=remaining,
                               initial_hedge_units=-shares * g0["delta"],
                               target_hedge_units=-shares * g1["delta"], hedge_trade_units=dq,
                               endpoint_hedge_trade_notional=target_spot * dq,
                               numerical_tail_saturation=g0["numerical_tail_saturation"] or g1["numerical_tail_saturation"])
                numeric_keys = [k for k, v in row.items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
                if not all(finite(row[k]) for k in numeric_keys):
                    raise ContractError("nonfinite_scaled_sensitivity")
                row["eligible"] = True
            except (ArithmeticError, ValueError) as exc:
                row = {"position_id": p.position_id, "strike": p.strike,
                       "eligible": False, "reasons": ["reference_model_failure:" + type(exc).__name__]}
        common["rows"].append(row)
    count = sum(r["eligible"] for r in common["rows"])
    complete = book.population_complete and count == len(positions)
    common.update(status="qualified" if complete else "partial", complete=complete,
                  evaluated_row_count=len(positions), eligible_row_count=count,
                  unavailable_row_count=len(positions) - count, unevaluated_due_to_scope_count=0)
    return common


def eligible_sum(rows, key, *, known_empty=False):
    terms = [r[key] for r in rows if r["eligible"]]
    return checked_sum(terms) if terms or known_empty else None


def negate(value):
    return None if value is None else -value


def strike_sensitivity_distribution(book, spot, *, amount_scale=1.0):
    """Sensitivity distribution by contract strike; never a target-spot path."""
    unit = GammaUnit(book.currency, amount_scale)
    metadata = unit.metadata()
    evaluated = evaluate_rows(book, spot)
    rows = evaluated["rows"]
    qualified_rows = [r for r in rows if r["eligible"]]
    known_empty = evaluated["complete"] and evaluated["input_row_count"] == 0
    partial = eligible_sum(rows, "portfolio_gamma_notional_per_1pct", known_empty=known_empty)
    partial = checked_scale(partial, amount_scale)
    full = partial if evaluated["complete"] else None
    unbucketed = [r["position_id"] for r in rows if r["strike"] is None]
    grouped = {}
    for row in rows:
        if row["strike"] is not None:
            grouped.setdefault(row["strike"], []).append(row)
    distribution = []
    prefix = []
    prefix_complete = book.population_complete and not unbucketed and not evaluated["scope_reasons"]
    for strike, group in sorted(grouped.items()):
        prefix.extend(group)
        bucket_complete = book.population_complete and not unbucketed and all(r["eligible"] for r in group)
        prefix_complete = prefix_complete and all(r["eligible"] for r in group)
        gp = eligible_sum(group, "portfolio_gamma_notional_per_1pct")
        cp = eligible_sum(prefix, "portfolio_gamma_notional_per_1pct")
        gp = checked_scale(gp, amount_scale)
        cp = checked_scale(cp, amount_scale)
        distribution.append({"contract_strike": strike, "position_ids": [r["position_id"] for r in group],
            "input_count": len(group), "eligible_count": sum(r["eligible"] for r in group),
            "complete": bucket_complete,
            "portfolio_sensitivity": gp if bucket_complete else None,
            "hedge_sensitivity": negate(gp) if bucket_complete else None,
            "eligible_partial_portfolio_sensitivity": gp, "eligible_partial_hedge_sensitivity": negate(gp),
            "cumulative_from_lowest_strike_complete": prefix_complete,
            "cumulative_portfolio_sensitivity": cp if prefix_complete else None,
            "cumulative_hedge_sensitivity": negate(cp) if prefix_complete else None,
            "eligible_partial_cumulative_portfolio_sensitivity": cp,
            "eligible_partial_cumulative_hedge_sensitivity": negate(cp)})
    gross = checked_sum(abs(r["portfolio_gamma_notional_per_1pct"]) for r in qualified_rows) if qualified_rows or known_empty else None
    return {"reference": "B2_strike_distribution_v1", "axis": "contract_strike", "base_spot": spot,
            "unit": metadata, "interpretation": "signed portfolio sensitivity; hedge sensitivity is its negative",
            "not_interpretations": ["endpoint_hedge_trade", "spot_path_integral", "full_hedge_holdings_market_value_change", "dealer_inventory", "market_impact"],
            "coverage": evaluated, "unbucketed_position_ids": unbucketed, "distribution": distribution,
            "portfolio_sensitivity": full, "hedge_sensitivity": negate(full),
            "eligible_partial_portfolio_sensitivity": partial, "eligible_partial_hedge_sensitivity": negate(partial),
            "gross_absolute_portfolio_sensitivity": checked_scale(gross, amount_scale) if evaluated["complete"] else None}


def endpoint_rehedge(book, initial_spot, target_spot, *, elapsed_years=0.0, target_ivs=None):
    if not positive(target_spot):
        raise ContractError("target_spot_must_be_positive_finite")
    evaluated = evaluate_rows(book, initial_spot, target_spot=target_spot,
                              elapsed_years=elapsed_years, target_ivs=target_ivs)
    rows = evaluated["rows"]
    known_empty = evaluated["complete"] and evaluated["input_row_count"] == 0
    keys = ("initial_hedge_units", "target_hedge_units", "hedge_trade_units", "endpoint_hedge_trade_notional")
    partial = {k: eligible_sum(rows, k, known_empty=known_empty) for k in keys}
    partial["endpoint_trade_cash_change"] = negate(partial["endpoint_hedge_trade_notional"])
    totals = {k: v if evaluated["complete"] else None for k, v in partial.items()}
    return {"reference": "B2_endpoint_rehedge_v1", "model": "European_Black_Scholes_r0_q0_reference_only",
            "initial_spot": initial_spot, "target_spot": target_spot,
            "elapsed_years": elapsed_years, "target_iv_rule": "per-position explicit override, otherwise fixed IV",
            "units": {"hedge_units": "units of " + book.underlying, "notional_and_cash": book.currency},
            "convention": "B=-sum(n*m*Delta); H=S_target*(B_target-B_initial); H>0 buys; cash=-H",
            "exclusions": ["path_cash", "turnover", "funding", "prior_rebalancing", "fill_or_impact", "observed_dealer_positions"],
            "coverage": evaluated, "totals": totals, "eligible_partial_totals": partial}


def book_gamma_evaluator(book, unit=None):
    selected_unit = GammaUnit(book.currency) if unit is None else unit
    selected_unit.metadata()
    if selected_unit.currency != book.currency:
        raise ContractError("book_gamma_currency_mismatch")

    def evaluate(spot):
        result = strike_sensitivity_distribution(book, spot, amount_scale=selected_unit.currency_units_per_output_unit)
        return GammaValue(result["portfolio_sensitivity"], result["gross_absolute_portfolio_sensitivity"],
                          selected_unit, result["coverage"]["status"],
                          None if result["coverage"]["complete"] else "full_hypothetical_book_not_qualified")
    return evaluate


def analyze_gamma_curve(evaluate: Callable[[float], GammaValue], sample_spots, current_spot, *,
                        unit=GammaUnit(), tolerance=GammaTolerance(), evaluation_domain=None):
    """B1 direct local regime plus finite-grid root FEATURES, not a root theorem.

    Grid domain only bounds the root search. A current spot outside that grid is
    evaluated directly if the model permits it. An explicit model domain blocks
    evaluations outside it and yields unknown; no curve is extrapolated.
    """
    unit_metadata = unit.metadata()
    tolerance.threshold(0.0)
    if not positive(current_spot):
        raise ContractError("current_spot_must_be_positive_finite")
    sample_spots = [] if sample_spots is None else list(sample_spots)
    if any(not positive(s) for s in sample_spots):
        raise ContractError("grid_spots_must_be_positive_finite")
    spots = sorted(set(sample_spots))
    if evaluation_domain is not None:
        if len(evaluation_domain) != 2 or not all(positive(x) for x in evaluation_domain) or evaluation_domain[0] > evaluation_domain[1]:
            raise ContractError("invalid_evaluation_domain")
    cache = {}

    def observe(spot):
        if spot in cache:
            return cache[spot]
        result = {"spot": spot, "status": "unknown", "net_gamma": None, "gross_absolute_gamma": None,
                  "zero_tolerance": None, "sign": None, "reason": None}
        if evaluation_domain is not None and not evaluation_domain[0] <= spot <= evaluation_domain[1]:
            result.update(status="out_of_model_domain", reason="evaluation_not_performed")
        else:
            try:
                value = evaluate(spot)
                if not isinstance(value, GammaValue):
                    result.update(status="no_data", reason="gamma_value_unavailable")
                elif value.unit != unit:
                    result.update(status="invalid_unit", reason="gamma_unit_mismatch")
                elif value.status != "qualified":
                    result.update(status=value.status, reason=value.reason or "unqualified_gamma_value")
                elif not finite(value.net) or not finite(value.gross_absolute) or value.gross_absolute < 0:
                    result.update(status="invalid_model_output", reason="nonfinite_or_missing_gamma")
                elif value.gross_absolute < abs(value.net) and not math.isclose(value.gross_absolute, abs(value.net), rel_tol=1e-14):
                    result.update(status="invalid_model_output", reason="gross_absolute_smaller_than_net")
                else:
                    epsilon = tolerance.threshold(value.gross_absolute)
                    sign = 0 if abs(value.net) <= epsilon else 1 if value.net > 0 else -1
                    result.update(status="qualified", net_gamma=value.net, gross_absolute_gamma=value.gross_absolute,
                                  zero_tolerance=epsilon, sign=sign)
            except Exception as exc:
                result.update(status="model_failure", reason=type(exc).__name__)
        cache[spot] = result
        return result

    current = observe(current_spot)  # Independent of nearest root or grid interpolation.
    sampled = [observe(s) for s in spots]
    root_features = []
    i = 0
    while i < len(sampled):
        p = sampled[i]
        if p["sign"] is None:
            i += 1
            continue
        if p["sign"] == 0:
            end = i
            while end + 1 < len(sampled) and sampled[end + 1]["sign"] == 0:
                end += 1
            left = sampled[i - 1] if i > 0 and sampled[i - 1]["sign"] in (-1, 1) else None
            right = sampled[end + 1] if end + 1 < len(sampled) and sampled[end + 1]["sign"] in (-1, 1) else None
            exact = all(s["net_gamma"] == 0.0 for s in sampled[i:end + 1])
            observed_exact_zero_spots = [s["spot"] for s in sampled[i:end + 1] if s["net_gamma"] == 0.0]
            both = left is not None and right is not None
            crossing = both and left["sign"] != right["sign"]
            orientation = ("negative_to_positive" if left["sign"] < right["sign"] else "positive_to_negative") if crossing else ("same_sign_flanks" if both else "undetermined")
            if not exact:
                kind = "near_zero_band"
            elif end > i:
                kind = "sampled_zero_plateau"
            elif not both:
                kind = "boundary_or_gap_zero"
            elif crossing:
                kind = "sampled_zero_crossing"
            else:
                kind = "sampled_touch_candidate"
            root_features.append({"kind": kind, "orientation": orientation,
                "sampled_interval": [p["spot"], sampled[end]["spot"]],
                "flank_interval": [left["spot"] if left else None, right["spot"] if right else None],
                "location_estimate": p["spot"] if exact and end == i else None,
                "all_samples_exact_zero": exact, "observed_exact_zero_spots": observed_exact_zero_spots,
                "flank_sign_change": crossing if both else None,
                "root_claim": "observed_zero_sample_or_samples" if exact else "observed_zero_samples_within_tolerance_band" if observed_exact_zero_spots else "within_tolerance_not_proof_of_zero"})
            i = end + 1
            continue
        if i + 1 < len(sampled):
            q = sampled[i + 1]
            if q["sign"] in (-1, 1) and p["sign"] != q["sign"]:
                # Stable linear interpolation of opposite signs, not a model solve.
                scale = max(abs(p["net_gamma"]), abs(q["net_gamma"]))
                a, b = abs(p["net_gamma"]) / scale, abs(q["net_gamma"]) / scale
                estimate = p["spot"] + (q["spot"] - p["spot"]) * (a / (a + b))
                root_features.append({"kind": "sign_change_bracket",
                    "orientation": "negative_to_positive" if p["sign"] < q["sign"] else "positive_to_negative",
                    "sampled_interval": [p["spot"], q["spot"]], "flank_interval": [p["spot"], q["spot"]],
                    "location_estimate": estimate, "all_samples_exact_zero": False,
                    "observed_exact_zero_spots": [], "flank_sign_change": True,
                    "root_claim": "linear_interpolation_estimate_conditional_on_continuity"})
        i += 1
    # Do not choose a unique flip when nearest candidates/bands tie.
    distances = []
    for feature in root_features:
        lo, hi = feature["sampled_interval"]
        if feature["location_estimate"] is not None:
            distances.append(abs(current_spot - feature["location_estimate"]))
        else:
            distances.append(max(lo - current_spot, 0.0, current_spot - hi))
    nearest = [] if not distances else [j for j, distance in enumerate(distances)
                                         if math.isclose(distance, min(distances), rel_tol=1e-12, abs_tol=1e-12)]
    domain = [spots[0], spots[-1]] if spots else None
    domain_state = "no_sample_grid" if not spots else "inside_sample_grid" if spots[0] <= current_spot <= spots[-1] else "outside_sample_grid"
    qualified_count = sum(p["status"] == "qualified" for p in sampled)
    grid_status = "no_data" if not spots else "insufficient_grid" if len(spots) < 2 else "qualified" if qualified_count == len(spots) else "partial" if qualified_count else "no_data"
    regime = {1: "positive", -1: "negative", 0: "near_zero"}.get(current["sign"], "unknown")
    return {"reference": "B1_gamma_regime_and_sampled_roots_v1", "unit": unit_metadata,
            "tolerance": {"absolute_in_output_units": tolerance.absolute, "relative_to_gross_absolute": tolerance.relative,
                          "formula": "absolute + relative * gross_absolute_at_the_same_spot", "scope": "numerical, not market materiality"},
            "current": current, "current_regime": regime, "current_grid_domain_state": domain_state,
            "current_evaluation_method": "not_performed_outside_model_domain" if current["status"] == "out_of_model_domain" else "direct_model_attempt",
            "sample_grid_domain": domain, "evaluation_domain": evaluation_domain, "grid_status": grid_status,
            "sampled_values": sampled, "root_features": root_features, "nearest_feature_indices": nearest,
            "continuous_root_completeness": "not_certified_by_a_finite_grid",
            "limitations": ["unsampled_tangencies_or_multiple_crossings_may_be_missed",
                            "zero_samples_do_not_establish_a_continuous_zero_plateau",
                            "missing_intervals_are_not_bridged", "regime_describes_assumed_book_not_observed_dealers"]}


def run_fixtures():
    """Assertions exercise claims/failure modes; outputs are reproducible evidence."""
    checks = []
    details = {}

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)

    def close(a, b, *, rel=1e-10, absolute=1e-8):
        return math.isclose(a, b, rel_tol=rel, abs_tol=absolute)

    def rejected(name, function):
        try:
            function()
        except ContractError:
            check(name, True)
        else:
            check(name, False)

    U = GammaUnit()

    def synthetic(fn, *, unit=U, gross=None):
        def evaluate(s):
            value = fn(s)
            if value is None:
                return GammaValue(None, None, unit, "no_data", "fixture_gap")
            raw_gross = max(abs(value), 1.0) if gross is None else gross(s)
            return GammaValue(value, raw_gross, unit)
        return evaluate

    # B1 adversarial topology fixtures use explicit synthetic functions, not markets.
    ascending = analyze_gamma_curve(synthetic(lambda s: s - 100), [95, 105], 101)
    descending = analyze_gamma_curve(synthetic(lambda s: 100 - s), [95, 105], 101)
    check("B1 ascending regime and orientation", ascending["current_regime"] == "positive" and ascending["root_features"][0]["orientation"] == "negative_to_positive")
    check("B1 descending current regime independent of being above root", descending["current_regime"] == "negative" and descending["root_features"][0]["orientation"] == "positive_to_negative")
    below = analyze_gamma_curve(synthetic(lambda s: 100 - s), [95, 105], 98)
    check("B1 descending below root is positive", below["current_regime"] == "positive")
    exact = analyze_gamma_curve(synthetic(lambda s: s - 100), [95, 100, 105], 100)
    check("B1 one exact zero crossing not doubled", len(exact["root_features"]) == 1 and exact["root_features"][0]["kind"] == "sampled_zero_crossing" and exact["current_regime"] == "near_zero")
    multiple = analyze_gamma_curve(synthetic(lambda s: (s - 95) * (s - 105)), [90, 100, 110], 100)
    check("B1 two roots preserve both orientations and nearest tie", [f["orientation"] for f in multiple["root_features"]] == ["positive_to_negative", "negative_to_positive"] and multiple["nearest_feature_indices"] == [0, 1] and multiple["current_regime"] == "negative")
    touch = analyze_gamma_curve(synthetic(lambda s: (s - 100) ** 2), [95, 100, 105], 100)
    check("B1 sampled tangent is a touch candidate without sign crossing", touch["root_features"][0]["kind"] == "sampled_touch_candidate" and touch["root_features"][0]["flank_sign_change"] is False)
    missed_touch = analyze_gamma_curve(synthetic(lambda s: (s - 100) ** 2), [95, 105], 100)
    check("B1 unsampled tangent may be absent while direct regime is near zero", not missed_touch["root_features"] and missed_touch["current_regime"] == "near_zero")

    def plateau_value(s):
        return -1.0 if s < 99 else 1.0 if s > 101 else 0.0

    plateau = analyze_gamma_curve(synthetic(plateau_value), [95, 99, 100, 101, 105], 100)
    check("B1 plateau represented once without unique flip", len(plateau["root_features"]) == 1 and plateau["root_features"][0]["kind"] == "sampled_zero_plateau" and plateau["root_features"][0]["location_estimate"] is None and plateau["root_features"][0]["orientation"] == "negative_to_positive")
    same_plateau = analyze_gamma_curve(synthetic(lambda s: 0.0 if 99 <= s <= 101 else 1.0), [95, 99, 101, 105], 100)
    check("B1 same-sign plateau does not become crossing", same_plateau["root_features"][0]["flank_sign_change"] is False)
    near = analyze_gamma_curve(synthetic(lambda s: 1e-9), [95, 100, 105], 100)
    check("B1 near-zero band is not an exact root", near["current_regime"] == "near_zero" and near["root_features"][0]["kind"] == "near_zero_band" and near["root_features"][0]["all_samples_exact_zero"] is False)
    mixed_zero_values = {95: 1.0, 99: 1e-9, 100: 0.0, 101: -1e-9, 105: -1.0}
    mixed_zero = analyze_gamma_curve(synthetic(lambda s: mixed_zero_values[s]), [95, 99, 100, 101, 105], 100)
    check("B1 mixed tolerance band preserves exact-zero sample evidence", mixed_zero["root_features"][0]["kind"] == "near_zero_band" and mixed_zero["root_features"][0]["all_samples_exact_zero"] is False and mixed_zero["root_features"][0]["observed_exact_zero_spots"] == [100])
    zeros = analyze_gamma_curve(synthetic(lambda s: 0.0), [95, 100, 105], 100)
    check("B1 all-zero samples have no unique level or orientation", zeros["root_features"][0]["location_estimate"] is None and zeros["root_features"][0]["orientation"] == "undetermined")
    boundary = analyze_gamma_curve(synthetic(lambda s: s - 95), [95, 100, 105], 100)
    check("B1 boundary zero orientation undetermined", boundary["root_features"][0]["kind"] == "boundary_or_gap_zero" and boundary["root_features"][0]["orientation"] == "undetermined")
    gap = analyze_gamma_curve(synthetic(lambda s: None if s == 100 else s - 100), [95, 100, 105], 100)
    check("B1 no crossing invented across missing middle", gap["grid_status"] == "partial" and not gap["root_features"] and gap["current_regime"] == "unknown")
    no_data = analyze_gamma_curve(synthetic(lambda s: None), [], 100)
    check("B1 no data stays unknown", no_data["grid_status"] == "no_data" and no_data["current_regime"] == "unknown")
    no_grid = analyze_gamma_curve(synthetic(lambda s: 1.0), [], 100)
    check("B1 no root grid does not erase valid direct current evaluation", no_grid["current_regime"] == "positive" and no_grid["grid_status"] == "no_data")
    single = analyze_gamma_curve(synthetic(lambda s: s - 100), [100], 100)
    check("B1 one grid point explicitly insufficient", single["grid_status"] == "insufficient_grid")
    no_crossing = analyze_gamma_curve(synthetic(lambda s: 1.0), [95, 100, 105], 100)
    check("B1 qualified no-crossing curve has positive regime without flip", no_crossing["grid_status"] == "qualified" and no_crossing["current_regime"] == "positive" and not no_crossing["root_features"])
    outside = analyze_gamma_curve(synthetic(lambda s: s - 100), [95, 105], 120)
    check("B1 outside grid uses direct model with explicit state", outside["current_regime"] == "positive" and outside["current_grid_domain_state"] == "outside_sample_grid" and outside["current_evaluation_method"] == "direct_model_attempt")
    model_outside = analyze_gamma_curve(synthetic(lambda s: s - 100), [95, 105], 120, evaluation_domain=(90, 110))
    check("B1 outside allowed model domain stays unknown", model_outside["current_regime"] == "unknown" and model_outside["current"]["status"] == "out_of_model_domain")
    check("B1 grid-domain label never claims a blocked model evaluation occurred", model_outside["current_grid_domain_state"] == "outside_sample_grid" and model_outside["current_evaluation_method"] == "not_performed_outside_model_domain")
    permuted = analyze_gamma_curve(synthetic(lambda s: (s - 95) * (s - 105)), [110, 90, 100, 90], 100)
    check("B1 grid permutation and duplicate spots invariant", permuted == multiple)
    generated_grid = analyze_gamma_curve(synthetic(lambda s: (s - 95) * (s - 105)), (s for s in [90, 100, 110]), 100)
    check("B1 generator grid is materialized once", generated_grid == multiple)
    extended_grid = analyze_gamma_curve(synthetic(lambda s: (s - 95) * (s - 105)), [1, 90, 100, 110, 1e6], 100)
    check("B1 unrelated grid extremes cannot change direct regime or tolerance", extended_grid["current"] == multiple["current"])
    nan_value = analyze_gamma_curve(synthetic(lambda s: float("nan")), [95, 105], 100)
    check("B1 NaN is unknown, never near-zero", nan_value["current_regime"] == "unknown")
    failed = analyze_gamma_curve(lambda s: 1 / 0, [95, 105], 100)
    check("B1 model failure is explicit", failed["current"]["status"] == "model_failure")
    bad_unit = analyze_gamma_curve(synthetic(lambda s: 1, unit=GammaUnit("EUR")), [95, 105], 100)
    check("B1 unit mismatch rejects classification", bad_unit["current"]["status"] == "invalid_unit")
    rejected("B1 invalid grid value rejected", lambda: analyze_gamma_curve(synthetic(lambda s: 1), [95, float("inf")], 100))
    rejected("B1 negative tolerance rejected", lambda: analyze_gamma_curve(synthetic(lambda s: 1), [95, 105], 100, tolerance=GammaTolerance(-1, 0)))
    million = GammaUnit("USD", 1e6)
    scaled = analyze_gamma_curve(synthetic(lambda s: (100 - s) / 1e6, unit=million, gross=lambda s: max(abs(100 - s), 1) / 1e6), [95, 105], 101, unit=million, tolerance=GammaTolerance(1e-14, 1e-10))
    check("B1 dollar-to-million scaling preserves regime and root location", scaled["current_regime"] == descending["current_regime"] and scaled["root_features"] == descending["root_features"])
    cancellation = analyze_gamma_curve(synthetic(lambda s: 1e-3, gross=lambda s: 1e8), [95, 105], 100)
    check("B1 cancellation scale uses gross exposure", cancellation["current_regime"] == "near_zero" and cancellation["current"]["zero_tolerance"] > 1e-3)
    details["B1_topology"] = {"ascending": ascending, "descending": descending, "multiple": multiple,
        "touch": touch, "missed_touch": missed_touch, "plateau": plateau, "same_sign_plateau": same_plateau,
        "near_zero": near, "mixed_zero_band": mixed_zero, "all_zero": zeros, "boundary": boundary, "missing_gap": gap,
        "no_data": no_data, "no_grid": no_grid, "no_crossing": no_crossing, "single_point": single, "outside_grid": outside,
        "outside_model_domain": model_outside, "scaled_millions": scaled, "cancellation": cancellation}

    # B2 reference books use explicit synthetic signed positions, never inferred OI.
    T = 30 / 365
    anchor_strike = 100 * math.exp(0.5 * 0.2**2 * 0.25)
    anchor_call = european_greeks(100, anchor_strike, 0.25, 0.2, "call")
    anchor_put = european_greeks(100, anchor_strike, 0.25, 0.2, "put")
    anchor_gamma = 1 / (math.sqrt(2 * math.pi) * 100 * 0.2 * math.sqrt(0.25))
    check("reference analytic d1-zero anchor fixes delta and Gamma scales", close(anchor_call["delta"], 0.5, absolute=1e-12) and close(anchor_put["delta"], -0.5, absolute=1e-12) and close(anchor_call["gamma"], anchor_gamma, absolute=1e-12) and close(anchor_put["gamma"], anchor_gamma, absolute=1e-12))

    def p(identifier, strike=100.0, n=1000.0, *, time=T, iv=0.2, multiplier=100.0, kind="call", currency="USD"):
        return Position(identifier, "SYNTH", currency, strike, time, iv, n, multiplier, kind)

    def book(*positions, complete=True):
        return Book("SYNTH", "USD", tuple(positions), complete)

    base = book(p("low", 95), p("high", 105))
    zero = endpoint_rehedge(base, 100, 100)
    up = endpoint_rehedge(base, 100, 105)
    down = endpoint_rehedge(base, 100, 95)
    check("B2 qualified unchanged state has zero rehedge", zero["totals"]["endpoint_hedge_trade_notional"] == 0)
    check("B2 long options up sells and down buys", up["totals"]["endpoint_hedge_trade_notional"] < 0 < down["totals"]["endpoint_hedge_trade_notional"])
    check("B2 endpoint cash sign is opposite", up["totals"]["endpoint_trade_cash_change"] == -up["totals"]["endpoint_hedge_trade_notional"])
    short = endpoint_rehedge(replace(base, positions=tuple(replace(x, signed_contracts=-x.signed_contracts) for x in base.positions)), 100, 105)
    check("B2 inventory reversal reverses hedge trade", close(short["totals"]["endpoint_hedge_trade_notional"], -up["totals"]["endpoint_hedge_trade_notional"]))
    put_up = endpoint_rehedge(book(p("put", kind="put")), 100, 105)
    check("B2 long put starts with positive underlying hedge but sells on rise", put_up["totals"]["initial_hedge_units"] > 0 and put_up["totals"]["endpoint_hedge_trade_notional"] < 0)
    check("B2 both strike sides contribute to same upward rehedge", all(r["endpoint_hedge_trade_notional"] < 0 for r in up["coverage"]["rows"]))
    more_low = endpoint_rehedge(book(p("low", 95, 3000), p("high", 105)), 100, 105)
    check("B2 lower-strike inventory affects upper endpoint", more_low["totals"]["endpoint_hedge_trade_notional"] < up["totals"]["endpoint_hedge_trade_notional"])
    synthetic_forward = endpoint_rehedge(book(p("call", n=1), p("put", n=-1, kind="put")), 100, 110)
    check("B2 synthetic-forward hedge notional value change is not hedge trading", close(synthetic_forward["totals"]["initial_hedge_units"], -100) and close(synthetic_forward["totals"]["target_hedge_units"], -100) and close(synthetic_forward["totals"]["endpoint_hedge_trade_notional"], 0))
    distribution = strike_sensitivity_distribution(base, 100)
    check("B2 signed portfolio and hedge sensitivities are separate opposites", distribution["portfolio_sensitivity"] > 0 and distribution["hedge_sensitivity"] == -distribution["portfolio_sensitivity"])
    check("B2 distribution axis and unit explicitly remain sensitivity", distribution["axis"] == "contract_strike" and distribution["unit"]["spot_shock_fraction"] == 0.01 and distribution["distribution"][-1]["cumulative_portfolio_sensitivity"] == distribution["portfolio_sensitivity"])
    reversed_book = replace(base, positions=tuple(reversed(base.positions)))
    check("B2 position permutation leaves results invariant", endpoint_rehedge(reversed_book, 100, 105) == up and strike_sensitivity_distribution(reversed_book, 100) == distribution)
    split = book(p("low_a", 95, 400), p("low_b", 95, 600), p("high", 105))
    check("B2 position splitting preserves endpoint and distribution total", close(endpoint_rehedge(split, 100, 105)["totals"]["endpoint_hedge_trade_notional"], up["totals"]["endpoint_hedge_trade_notional"]) and close(strike_sensitivity_distribution(split, 100)["portfolio_sensitivity"], distribution["portfolio_sensitivity"]))
    multipliers = book(p("hundred", n=3, multiplier=100), p("fifty", n=4, multiplier=50))
    multiplier_result = endpoint_rehedge(multipliers, 100, 105)
    equivalent = endpoint_rehedge(book(p("equivalent", n=5, multiplier=100)), 100, 105)
    check("B2 heterogeneous multipliers are applied before aggregation", close(multiplier_result["totals"]["endpoint_hedge_trade_notional"], equivalent["totals"]["endpoint_hedge_trade_notional"]))
    unit_multiplier = endpoint_rehedge(book(p("one", n=5, multiplier=1)), 100, 105)
    check("B2 multiplier unit scaling is linear", close(equivalent["totals"]["endpoint_hedge_trade_notional"], 100 * unit_multiplier["totals"]["endpoint_hedge_trade_notional"]))
    scaled_distribution = strike_sensitivity_distribution(base, 100, amount_scale=1e6)
    check("B2 dollar-to-million sensitivity scaling is explicit", close(scaled_distribution["portfolio_sensitivity"] * 1e6, distribution["portfolio_sensitivity"]))

    # Identical snapshot Gamma tables contain insufficient finite-move information.
    matched = {}
    for label, first, second in [("maturity", p("different", time=7/365), p("different", time=180/365)),
                                 ("iv", p("different", iv=0.1), p("different", iv=0.5))]:
        ga = european_greeks(100, first.strike, first.remaining_years, first.iv, first.kind)["gamma"]
        gb = european_greeks(100, second.strike, second.remaining_years, second.iv, second.kind)["gamma"]
        second = replace(second, signed_contracts=first.signed_contracts * ga / gb)
        a, b = book(first, p("common", 110)), book(second, p("common", 110))
        da, db = strike_sensitivity_distribution(a, 100), strike_sensitivity_distribution(b, 100)
        ha, hb = endpoint_rehedge(a, 100, 110), endpoint_rehedge(b, 100, 110)
        check("B2 matched Gamma different " + label + " remains distinguishable", all(close(x["portfolio_sensitivity"], y["portfolio_sensitivity"]) for x, y in zip(da["distribution"], db["distribution"])) and abs(ha["totals"]["endpoint_hedge_trade_notional"] - hb["totals"]["endpoint_hedge_trade_notional"]) > 1e6)
        matched[label] = {"book_A": asdict(a), "book_B": asdict(b), "distribution_A": da,
                          "distribution_B": db, "endpoint_A": ha, "endpoint_B": hb}
    # Locally gamma-neutral does not imply delta-neutral under a finite move.
    neutral_pair = matched["maturity"]
    pa = Position(**neutral_pair["book_A"]["positions"][0])
    pb = Position(**neutral_pair["book_B"]["positions"][0])
    neutral_book = book(replace(pa, position_id="near"), replace(pb, position_id="far", signed_contracts=-pb.signed_contracts))
    neutral_distribution = strike_sensitivity_distribution(neutral_book, 100)
    neutral_endpoint = endpoint_rehedge(neutral_book, 100, 110)
    check("B2 zero current Gamma does not imply zero finite rehedge", abs(neutral_distribution["portfolio_sensitivity"]) < 1e-8 and abs(neutral_endpoint["totals"]["endpoint_hedge_trade_notional"]) > 1e6)
    errors = []
    for h in (0.1, 0.01, 0.001, 0.0001):
        exact_h = endpoint_rehedge(base, 100, 100+h)["totals"]["endpoint_hedge_trade_notional"]
        local = -(100+h) * math.fsum(r["portfolio_gamma_units_per_spot"] for r in distribution["coverage"]["rows"]) * h
        errors.append({"spot_change": h, "exact_H": exact_h, "whole_book_local_approx_H": local,
                       "relative_error": abs(local-exact_h)/abs(exact_h)})
    check("B2 decreasing small shocks converge to whole-book local approximation", all(a["relative_error"] > b["relative_error"] for a, b in zip(errors, errors[1:])) and errors[-1]["relative_error"] < 1e-5)
    iv_change = endpoint_rehedge(book(p("iv_shift")), 100, 100, target_ivs={"iv_shift": 0.3})
    time_change = endpoint_rehedge(book(p("time_shift")), 100, 100, elapsed_years=1/365)
    check("B2 unchanged spot with changed IV is not forced to zero", abs(iv_change["totals"]["endpoint_hedge_trade_notional"]) > 1)
    check("B2 unchanged spot with time passage is not forced to zero", abs(time_change["totals"]["endpoint_hedge_trade_notional"]) > 1)

    missing_book = book(p("good", 95), replace(p("missing", 105), iv=None))
    missing = endpoint_rehedge(missing_book, 100, 100)
    missing_distribution = strike_sensitivity_distribution(missing_book, 100)
    check("B2 missing Greek inputs keep complete endpoint unknown even for no move", missing["totals"]["endpoint_hedge_trade_notional"] is None and missing["eligible_partial_totals"]["endpoint_hedge_trade_notional"] == 0 and missing["coverage"]["unavailable_row_count"] == 1)
    check("B2 incomplete strike bucket and cumulative sensitivity remain null", missing_distribution["portfolio_sensitivity"] is None and missing_distribution["distribution"][1]["portfolio_sensitivity"] is None and missing_distribution["distribution"][1]["cumulative_portfolio_sensitivity"] is None)
    unknown_strike = strike_sensitivity_distribution(book(p("good", 95), replace(p("missing"), strike=None)), 100)
    check("B2 unknown strike not discarded from cumulative coverage", unknown_strike["unbucketed_position_ids"] == ["missing"] and all(r["cumulative_portfolio_sensitivity"] is None for r in unknown_strike["distribution"]))
    incomplete_population = endpoint_rehedge(replace(base, population_complete=False), 100, 105)
    check("B2 complete supplied rows do not imply complete population", incomplete_population["totals"]["endpoint_hedge_trade_notional"] is None and incomplete_population["eligible_partial_totals"]["endpoint_hedge_trade_notional"] is not None)
    unavailable = endpoint_rehedge(Book("SYNTH", "USD", None, False), 100, 105)
    empty_unknown = endpoint_rehedge(book(complete=False), 100, 105)
    empty_known = endpoint_rehedge(book(complete=True), 100, 105)
    check("B2 absent or incomplete empty book unknown, explicitly complete empty book zero", unavailable["totals"]["endpoint_hedge_trade_notional"] is None and empty_unknown["eligible_partial_totals"]["endpoint_hedge_trade_notional"] is None and empty_known["totals"]["endpoint_hedge_trade_notional"] == 0)
    invalid_cases = {}
    for field, value in [("signed_contracts", None), ("multiplier", None), ("remaining_years", None), ("kind", None),
                         ("iv", 0.0), ("remaining_years", 0.0), ("remaining_years", "unknown"),
                         ("iv", float("nan")), ("strike", -1.0), ("exercise_style", "american")]:
        result = endpoint_rehedge(book(replace(p("invalid"), **{field: value})), 100, 105)
        name = field + "=" + str(value)
        check("B2 invalid or unavailable field stays unknown: " + name, result["totals"]["endpoint_hedge_trade_notional"] is None and result["eligible_partial_totals"]["endpoint_hedge_trade_notional"] is None)
        invalid_cases[name] = result
    expired = endpoint_rehedge(book(p("expires", time=1/365)), 100, 101, elapsed_years=1/365)
    check("B2 crossing expiry is unsupported state, never T floor", expired["totals"]["endpoint_hedge_trade_notional"] is None)
    mixed_currency = endpoint_rehedge(book(p("USD"), replace(p("bad_EUR", currency="EUR"), iv=None)), 100, 105)
    check("B2 currency mismatch cannot hide in ineligible row", mixed_currency["coverage"]["status"] == "rejected_scope" and mixed_currency["eligible_partial_totals"]["endpoint_hedge_trade_notional"] is None)
    missing_currency = endpoint_rehedge(book(replace(p("missing"), currency=None)), 100, 105)
    check("B2 missing currency never assumed USD", missing_currency["coverage"]["status"] == "rejected_scope")
    wrong_underlying = endpoint_rehedge(book(p("one"), replace(p("other"), underlying="OTHER")), 100, 105)
    check("B2 mixed underlying rejected", wrong_underlying["coverage"]["status"] == "rejected_scope")
    duplicate_ids = endpoint_rehedge(book(p("same"), p("same", 105)), 100, 105)
    check("B2 duplicate position identity rejected", duplicate_ids["coverage"]["status"] == "rejected_scope")
    rejected("B2 invalid target spot rejected", lambda: endpoint_rehedge(base, 100, 0))
    rejected("B2 missing target spot explicitly rejected", lambda: endpoint_rehedge(base, 100, None))
    rejected("B2 amount scaling overflow explicitly rejected", lambda: strike_sensitivity_distribution(base, 100, amount_scale=1e-320))
    huge_book = book(p("huge_a", n=5e305, multiplier=1), p("huge_b", n=5e305, multiplier=1))
    rejected("B2 finite rows but aggregate overflow explicitly rejected", lambda: endpoint_rehedge(huge_book, 100, 400))
    rejected("B2 unknown IV override identity rejected", lambda: endpoint_rehedge(base, 100, 105, target_ivs={"absent": 0.2}))
    # Reuse accepted descending 20-contract witness under a fixed signed-inventory scenario.
    chain_positions = tuple([p("call_"+str(j), 95+j*0.01, 100) for j in range(10)] +
                            [p("put_"+str(j), 105+j*0.01, -100, kind="put") for j in range(10)])
    chain_book = book(*chain_positions)
    chain_results = {}
    for current in (98.0, 101.0):
        grid = [current*(0.75+0.005*j) for j in range(101)]
        result = analyze_gamma_curve(book_gamma_evaluator(chain_book), grid, current)
        check("B1 accepted descending options witness corrected at spot " + str(current), result["current_regime"] == ("positive" if current == 98 else "negative") and len(result["root_features"]) == 1 and result["root_features"][0]["orientation"] == "positive_to_negative")
        chain_results[str(current)] = result
    ascending_chain = replace(chain_book, positions=tuple(replace(x, signed_contracts=-x.signed_contracts) for x in chain_book.positions))
    ascending_chain_result = analyze_gamma_curve(book_gamma_evaluator(ascending_chain), [75 + 0.5*j for j in range(101)], 101)
    check("B1 mirrored options chain ascending control stays correct", ascending_chain_result["current_regime"] == "positive" and ascending_chain_result["root_features"][0]["orientation"] == "negative_to_positive")
    incomplete_curve = analyze_gamma_curve(book_gamma_evaluator(missing_book), [95, 100, 105], 100)
    check("B1 partial book cannot claim complete Gamma regime", incomplete_curve["current_regime"] == "unknown")
    reversed_chain = replace(chain_book, positions=tuple(reversed(chain_book.positions)))
    check("B1 options book permutation invariant", analyze_gamma_curve(book_gamma_evaluator(reversed_chain), [95, 100, 105], 101) == analyze_gamma_curve(book_gamma_evaluator(chain_book), [105, 95, 100], 101))
    details["B1_options_witness"] = {"book": asdict(chain_book), "results": chain_results}
    details["B2"] = {"base_book": asdict(base), "no_move": zero, "up": up, "down": down,
        "short": short, "put_up": put_up, "more_lower_inventory": more_low, "synthetic_forward": synthetic_forward,
        "distribution": distribution, "heterogeneous_multipliers": multiplier_result, "matched_gamma": matched,
        "gamma_neutral_book": asdict(neutral_book), "gamma_neutral_endpoint": neutral_endpoint,
        "small_shock_convergence": errors, "iv_only": iv_change, "time_only": time_change,
        "missing": missing, "missing_distribution": missing_distribution, "unknown_strike": unknown_strike,
        "incomplete_population": incomplete_population, "unavailable": unavailable,
        "empty_unknown": empty_unknown, "empty_known": empty_known, "invalid_cases": invalid_cases,
        "expired": expired, "mixed_currency": mixed_currency, "missing_currency": missing_currency,
        "wrong_underlying": wrong_underlying, "duplicate_ids": duplicate_ids}
    return {"status": "PASS", "assertion_count": len(checks), "checks": checks, "details": details}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write a NEW results JSON; existing files require --replace-results")
    parser.add_argument("--replace-results", action="store_true", help="Allow replacement of this reference's explicitly selected results artifact")
    args = parser.parse_args()
    result = run_fixtures()
    result["provenance"] = {
        "purpose": "isolated research reference for owner adaptation; no production implementation or activation",
        "python": platform.python_version(), "dependencies": "Python standard library only",
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "reference_model": "European Black-Scholes, r=q=0, positive T/IV; no exercise or expiry limits",
        "source_brief": "OWNER_REPAIR_BRIEFS.md sections B1 and B2",
        "source_witness": "options-mechanics-witness.md and its original pinned source citations",
        "terminal_source_pin": "a049d46fa2415d3949aae5efc0ee515b6667c7a0",
        "macro_source_pin": "6f5e78e94e8808582a650cdfa0fc3357040a179c",
        "law_pin_supplied_by_principal": "20adcaf65c2dd1bb734ab06e215feb1a0eb65659",
        "authority": {"research_only": True, "production_changes": False, "network": False,
                      "provider_or_M2_calls": False, "dealer_inventory_inference": False, "predictive_claim": False}}
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        if args.output.exists() and not args.replace_results:
            raise SystemExit("Refusing to overwrite an existing artifact without --replace-results")
        args.output.write_text(text)
        print(json.dumps({"status": result["status"], "assertions": result["assertion_count"],
                          "output": str(args.output), "bytes": len(text.encode()),
                          "sha256": hashlib.sha256(text.encode()).hexdigest()}, indent=2))
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
