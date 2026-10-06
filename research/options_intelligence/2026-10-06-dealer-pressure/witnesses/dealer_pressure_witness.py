#!/usr/bin/env python3
"""SYNTHETIC dealer-pressure accounting and numerical witnesses.

No market data, observed positions, participant classification, alpha, backtest,
production model, runtime connection or repository change is involved.

Rerun:
    python dealer_pressure_witness.py --outdir .

Only NumPy, SciPy and Matplotlib are needed. The model is European Black-Scholes
with continuous carry, ACT/365F calendar time, long-option pricing delta, decimal
IV and fixed strike IV scenarios. It is a mechanics reference, not a model of
actual SPX/SPXW dealer inventory or execution.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import factorial
from pathlib import Path

import numpy as np
from scipy.optimize import brentq
from scipy.special import ndtr

YEAR_SECONDS = 365.0 * 24 * 60 * 60
YEAR_MINUTES = YEAR_SECONDS / 60
S0 = 6000.0
R = 0.04                  # Synthetic, not an observed rate.
DIVIDEND_YIELD = 0.015     # Synthetic continuous carry, not an observed dividend forecast.
DS_PCT = -0.35
DS = S0 * DS_PCT / 100
IV_SHIFT = 0.012
HORIZON_MINUTES = 20.0
S1 = S0 + DS
LABEL = "SYNTHETIC — no observed dealer book, no alpha, no market backtest"

CHECKS: list[dict] = []


def record_check(name: str, passed: bool, **details) -> None:
    CHECKS.append({"name": name, "passed": bool(passed), **details})
    if not passed:
        raise AssertionError(name + ": " + repr(details))


def check_close(name: str, actual: float, expected: float,
                atol: float = 1e-8, rtol: float = 1e-10) -> None:
    err = abs(float(actual) - float(expected))
    record_check(name, err <= atol + rtol * abs(float(expected)),
                 actual=float(actual), expected=float(expected), absolute_error=err,
                 absolute_tolerance=atol, relative_tolerance=rtol)


def bs(S, K, tau, sigma, is_call, r=R, q=DIVIDEND_YIELD):
    """Premium in native index points; Greeks of one LONG option.

    delta = d premium / dS
    gamma = d delta / dS
    vanna = d delta / d(decimal IV)
    charm_calendar = d delta / d(advancing calendar year) = -d delta/dtau.
    """
    S, K, tau, sigma, is_call = np.broadcast_arrays(
        np.asarray(S, dtype=float), np.asarray(K, dtype=float),
        np.asarray(tau, dtype=float), np.asarray(sigma, dtype=float),
        np.asarray(is_call, dtype=bool))
    if np.any(S <= 0) or np.any(K <= 0) or np.any(tau <= 0) or np.any(sigma <= 0):
        raise ValueError("Pricing requires positive spot, strike, remaining time and IV")
    root_t = np.sqrt(tau)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * tau) / (sigma * root_t)
    d2 = d1 - sigma * root_t
    pdf = np.exp(-0.5 * d1**2) / np.sqrt(2 * np.pi)
    dq = np.exp(-q * tau)
    dr = np.exp(-r * tau)
    call_price = S * dq * ndtr(d1) - K * dr * ndtr(d2)
    put_price = K * dr * ndtr(-d2) - S * dq * ndtr(-d1)
    delta = dq * (ndtr(d1) - (~is_call).astype(float))
    gamma = dq * pdf / (S * sigma * root_t)
    vanna = -dq * pdf * d2 / sigma
    d1_dtau = ((r - q + 0.5 * sigma**2) * tau - np.log(S / K)) / (
        2 * sigma * tau**1.5)
    charm = q * delta - dq * pdf * d1_dtau
    return {
        "price": np.where(is_call, call_price, put_price),
        "delta": delta, "gamma": gamma, "vanna": vanna,
        "charm_calendar": charm,
    }


@dataclass(frozen=True)
class Contract:
    id: str
    product: str
    cohort: str
    strike: float
    right: str
    remaining_minutes: float
    iv: float
    multiplier: float
    initial_h: float
    inventory_change: float = 0.0


def make_book() -> list[Contract]:
    # Every quantity and remaining time below is invented. No calendar or actual
    # listed series is asserted. All modeled horizons remain BEFORE fixing.
    rows = []
    for strike, hc, hp in [(5975, -160, -260), (6000, -400, -380), (6025, -240, -120)]:
        rows.extend([
            Contract(f"SPXW_0D_C_{strike}", "SPXW_PM", "0DTE", strike, "C", 60, .20,
                     100, hc, -35 if strike == 6000 else 0),
            Contract(f"SPXW_0D_P_{strike}", "SPXW_PM", "0DTE", strike, "P", 60, .20,
                     100, hp, 20 if strike == 6000 else 0),
        ])
    for strike, magnitude in [(5950, 80), (6050, 120)]:
        for right in ["C", "P"]:
            rows.append(Contract(f"SPXW_3D_{right}_{strike}", "SPXW_PM", "1-7D",
                                 strike, right, 3 * 1440 + 60, .22, 100, magnitude))
    for strike, magnitude in [(5800, 60), (6200, 40)]:
        for right in ["C", "P"]:
            rows.append(Contract(f"SPX_30D_{right}_{strike}", "SPX_AM", "8+D",
                                 strike, right, 30 * 1440 + 60, .24, 100, magnitude))
    return rows


BOOK = make_book()
K = np.array([c.strike for c in BOOK])
TAU0 = np.array([c.remaining_minutes / YEAR_MINUTES for c in BOOK])
SIGMA0 = np.array([c.iv for c in BOOK])
CALLS = np.array([c.right == "C" for c in BOOK])
MULT = np.array([c.multiplier for c in BOOK])
H0 = np.array([c.initial_h for c in BOOK])
DH = np.array([c.inventory_change for c in BOOK])
COHORTS = np.array([c.cohort for c in BOOK])


def greek_state(S: float, iv_shift: float = 0, elapsed_minutes: float = 0):
    tau = TAU0 - elapsed_minutes / YEAR_MINUTES
    return bs(S, K, tau, SIGMA0 + iv_shift, CALLS)


def hedge(S: float, iv_shift: float = 0, elapsed_minutes: float = 0,
          inventory: np.ndarray | None = None) -> float:
    h = H0 if inventory is None else np.asarray(inventory)
    return float(-np.sum(h * MULT * greek_state(S, iv_shift, elapsed_minutes)["delta"]))


def exact_change(S: float, iv_shift: float, elapsed_minutes: float,
                 h_start=H0, h_end=None) -> float:
    h_end = h_start if h_end is None else h_end
    return hedge(S, iv_shift, elapsed_minutes, h_end) - hedge(S0, 0, 0, h_start)


def linear_change(S: float, iv_shift: float, elapsed_minutes: float,
                  h_start=H0, dh=None) -> float:
    g = greek_state(S0)
    dh = np.zeros_like(h_start) if dh is None else dh
    delta_approx = (g["gamma"] * (S - S0) + g["vanna"] * iv_shift
                    + g["charm_calendar"] * elapsed_minutes / YEAR_MINUTES)
    # First-order flow delta uses the initial-state Greek. Exact interaction
    # between inventory changes and repricing is intentionally in the residual.
    return float(-np.sum(MULT * (h_start * delta_approx + dh * g["delta"])))


def inventory_scenarios() -> dict[str, np.ndarray]:
    front_long = H0.copy()
    front_long[COHORTS == "0DTE"] *= -1
    return {
        "front_short_back_long": H0.copy(),
        "front_long_back_long": front_long,
        "call_long_put_short": np.abs(H0) * np.where(CALLS, 1.0, -1.0),
    }


def witness_identifiability():
    # OI0 means initial OI, not an unchanged final OI.
    obs = {"prior_OI": 0, "quantity": 10, "bid": 9.90, "ask": 10.00,
           "trade_price": 10.00, "buyer_opens": 1, "seller_opens": 1,
           "following_OI": 10}
    cases = []
    for label, dealer_buyer, dealer_seller in [
        ("dealer buyer, nondealer seller", 1, 0),
        ("two nondealers", 0, 0),
        ("nondealer buyer, dealer seller", 0, 1),
    ]:
        dh = obs["quantity"] * (dealer_buyer - dealer_seller)
        doi = obs["quantity"] * (obs["buyer_opens"] + obs["seller_opens"] - 1)
        check_close("identical_OI_" + label, obs["prior_OI"] + doi, obs["following_OI"])
        cases.append({"case": label, "observables": dict(obs),
                      "dealer_inventory_change": dh})
    record_check("same_observation_different_dealer_change",
                 {c["dealer_inventory_change"] for c in cases} == {-10, 0, 10})
    record_check("observations_identical",
                 all(c["observables"] == cases[0]["observables"] for c in cases))
    return {"label": LABEL, "cases": cases,
            "interpretation": "Ask execution and OI0=0 do not identify dealer side. No probabilities assigned."}


def witness_buy_to_close():
    quantity, initial = 5, -5
    actual_change = quantity * (1 - 0)
    final = initial + actual_change
    check_close("buy_to_close_increases_h", actual_change, 5)
    check_close("buy_to_close_eliminates_short", final, 0)
    doi = quantity * (0 + 1 - 1)   # dealer closes short; seller opens short
    check_close("buy_to_close_mixed_transaction_has_zero_OI_change", doi, 0)
    incorrectly_open_gated_change = actual_change * 0
    record_check("opening_probability_gate_would_be_wrong",
                 incorrectly_open_gated_change != actual_change)
    return {"initial_signed_h": initial, "buy_to_close_contracts": quantity,
            "final_signed_h": final, "signed_change": actual_change,
            "OI_change_if_seller_opens": doi}


def witness_endpoint_and_cash():
    h, m, d0, d1 = 10, 100, .45, .63
    b0, b1 = -h * m * d0, -h * m * d1
    q = b1 - b0
    endpoint_notional = S1 * q
    marked_hedge_difference = S1 * b1 - S0 * b0
    revaluation = (S1 - S0) * b0
    check_close("endpoint_target_units", q, -180)
    check_close("old_hedge_revaluation_identity",
                marked_hedge_difference - endpoint_notional, revaluation)
    record_check("marked_holdings_change_is_not_trade_notional",
                 abs(marked_hedge_difference - endpoint_notional) > 1)
    cash_equity_change = -endpoint_notional  # ONLY a hypothetical cash-share trade
    check_close("cash_equity_consideration_has_opposite_sign",
                cash_equity_change, 1076220)
    spx_cash_change = None
    futures_cash_change = None
    record_check("synthetic_index_and_futures_cash_not_inferred",
                 spx_cash_change is None and futures_cash_change is None)
    return {
        "B0": b0, "B1": b1, "target_change": q,
        "endpoint_trade_notional_USD": endpoint_notional,
        "marked_holdings_difference_USD": marked_hedge_difference,
        "old_hedge_revaluation_USD": revaluation,
        "hypothetical_cash_equity_consideration_USD": cash_equity_change,
        "SPX_synthetic_cash_consideration": spx_cash_change,
        "futures_cash_consideration": futures_cash_change,
        "scope": "Cash=-price*shares only for a cash-equity purchase/sale; futures notional is not margin, cash or P&L.",
    }


def witness_shapley():
    names = ["spot", "volatility", "calendar_time", "inventory"]
    corners = {}
    for mask in range(16):
        S = S1 if mask & 1 else S0
        iv = IV_SHIFT if mask & 2 else 0
        dt = HORIZON_MINUTES if mask & 4 else 0
        h = H0 + DH if mask & 8 else H0
        corners[mask] = hedge(S, iv, dt, h)
    values = {}
    for j, name in enumerate(names):
        contribution = 0.0
        for mask in range(16):
            if mask & (1 << j):
                continue
            size = mask.bit_count()
            weight = factorial(size) * factorial(3 - size) / factorial(4)
            contribution += weight * (corners[mask | (1 << j)] - corners[mask])
        values[name] = contribution
    q_exact = corners[15] - corners[0]
    record_check("shapley_uses_exactly_16_corners", len(corners) == 16)
    check_close("four_factor_shapley_sums_to_target_change",
                sum(values.values()), q_exact)
    dollar_values = {k: v * S1 for k, v in values.items()}
    check_close("shapley_endpoint_dollars_use_common_endpoint_price",
                sum(dollar_values.values()), S1 * q_exact, atol=1e-5)
    check_close("shapley_full_corner_matches_direct",
                q_exact, exact_change(S1, IV_SHIFT, HORIZON_MINUTES, H0, H0 + DH))
    return {
        "factors": names, "corner_evaluations": len(corners),
        "B_corners_by_bitmask": {str(k): v for k, v in corners.items()},
        "attribution_hedge_units": values,
        "attribution_endpoint_USD": dollar_values,
        "target_change": q_exact, "endpoint_USD": S1 * q_exact,
        "rule": "Shapley decomposes B in a fixed risk coordinate, NOT S*B. Every USD contribution is valued at S1.",
    }


def witness_general_decomposition():
    h0 = np.array([12.0, -20.0])
    h1 = np.array([10.0, -23.0])
    m0 = np.array([100.0, 50.0])
    m1 = np.array([150.0, 20.0])
    d0 = np.array([.40, -.30])
    d1 = np.array([.55, -.20])
    r0, r1 = m0 * d0, m1 * d1
    dh, dr = h1 - h0, r1 - r0
    exact = float(-np.sum(h1 * r1 - h0 * r0))
    repricing = float(-np.sum(h0 * dr))
    inventory = float(-np.sum(dh * r0))
    interaction = float(-np.sum(dh * dr))
    check_close("h_multiplier_delta_general_identity",
                repricing + inventory + interaction, exact)
    symmetric = float(-np.sum(.5 * (h0 + h1) * dr + dh * .5 * (r0 + r1)))
    check_close("general_symmetric_allocation", symmetric, exact)
    wrong_fixed_m = float(-np.sum(m0 * (h0 * (d1 - d0)
                                       + dh * d0 + dh * (d1 - d0))))
    record_check("fixed_multiplier_formula_is_not_general",
                 abs(wrong_fixed_m - exact) > 1)
    # A unit rebasing must not manufacture a trade. Common-coordinate conversion
    # offsets doubled native share multiplier in this hypothetical 2:1 example.
    old_r = 100 * .4 * 1.0
    rebased_r = 200 * .4 * .5
    check_close("pure_reference_rebase_has_zero_common_risk_change", rebased_r, old_r)
    return {
        "h0": h0.tolist(), "h1": h1.tolist(), "m0": m0.tolist(), "m1": m1.tolist(),
        "delta0": d0.tolist(), "delta1": d1.tolist(),
        "r0": r0.tolist(), "r1": r1.tolist(),
        "exact_target_change": exact,
        "repricing_term": repricing, "inventory_term": inventory,
        "interaction_term": interaction,
        "incorrect_fixed_multiplier_result": wrong_fixed_m,
        "pure_rebase_common_risk_change": rebased_r - old_r,
        "scope": "Algebra in a fixed risk coordinate. Actual adjusted deliverables require canonical reference rebasing or a risk vector.",
    }


def witness_path():
    direct = np.array([0.0, 10.0])
    oscillating = np.array([0.0, 8.0, -3.0, 10.0])
    net_direct = float(np.diff(direct).sum())
    net_oscillating = float(np.diff(oscillating).sum())
    turnover_direct = float(np.abs(np.diff(direct)).sum())
    turnover_oscillating = float(np.abs(np.diff(oscillating)).sum())
    check_close("direct_path_telescopes", net_direct, 10)
    check_close("oscillating_path_telescopes", net_oscillating, 10)
    check_close("direct_turnover", turnover_direct, 10)
    check_close("oscillating_turnover", turnover_oscillating, 32)
    record_check("equal_net_does_not_equal_gross", turnover_oscillating > turnover_direct)
    return {
        "direct_target_holdings": direct.tolist(),
        "oscillating_target_holdings": oscillating.tolist(),
        "net_change_both": 10, "direct_turnover": turnover_direct,
        "oscillating_turnover": turnover_oscillating,
        "scope": "Hypothetical exact tracking of target units; no inferred real execution.",
    }


def witness_cross_product():
    delta = .5
    per_spx_point_spx = 1 * 100 * delta * 1
    per_spx_point_xsp = 10 * 100 * delta * .1
    es_point_value = 50
    per_ndx_point_ndx = 1 * 100 * delta * 1
    per_ndx_point_xnd = 100 * 100 * delta * .01
    nq_point_value = 20
    check_close("SPX_10XSP_common_sensitivity", per_spx_point_spx, per_spx_point_xsp)
    check_close("one_SPX_half_delta_ES_hedge", -per_spx_point_spx / es_point_value, -1)
    check_close("NDX_100XND_common_sensitivity", per_ndx_point_ndx, per_ndx_point_xnd)
    check_close("one_NDX_half_delta_NQ_hedge", -per_ndx_point_ndx / nq_point_value, -2.5)
    check_close("ES_option_no_extra_100", -(50 * delta) / es_point_value, -.5)
    check_close("NQ_option_no_extra_100", -(20 * delta) / nq_point_value, -.5)
    return {
        "assumptions": "Standard products, long option delta 0.5, matched futures/index sensitivity a_f=1, basis risk excluded only for this unit witness.",
        "SPX_1_contract_USD_per_SPX_point": per_spx_point_spx,
        "XSP_10_contracts_USD_per_SPX_point": per_spx_point_xsp,
        "hedge_ES_contracts": -1,
        "NDX_1_contract_USD_per_NDX_point": per_ndx_point_ndx,
        "XND_100_contracts_USD_per_NDX_point": per_ndx_point_xnd,
        "hedge_NQ_contracts": -2.5,
        "one_ES_option_half_delta_hedge_ES": -.5,
        "one_NQ_option_half_delta_hedge_NQ": -.5,
        "warning": "No actual hedge ratio, current basis, dealer allocation or ownership inferred.",
    }


def implied_vol(price: float, S: float, K_: float, tau: float, is_call=True, r=0, q=0):
    def err(vol):
        return float(bs(S, K_, tau, vol, is_call, r, q)["price"]) - price
    return brentq(err, 1e-6, 5.0, xtol=1e-14, rtol=1e-14)


def witness_tte_floor():
    rows = []
    seconds = [1, 5, 15, 60, 300, 900, 1800, 3599, 3600, 3601]
    for sec in seconds:
        tau = sec / YEAR_SECONDS
        floored_tau = max(sec, 3600) / YEAR_SECONDS
        actual = bs(S0, S0, tau, .20, True, 0, 0)
        price = float(actual["price"])
        fixed = bs(S0, S0, floored_tau, .20, True, 0, 0)
        refit_iv = implied_vol(price, S0, S0, floored_tau, True, 0, 0)
        refit = bs(S0, S0, floored_tau, refit_iv, True, 0, 0)
        check_close(f"same_price_refit_price_{sec}s", float(refit["price"]), price,
                    atol=2e-9, rtol=1e-9)
        check_close(f"zero_carry_same_price_gamma_{sec}s",
                    float(refit["gamma"]), float(actual["gamma"]),
                    atol=2e-9, rtol=1e-8)
        rows.append({
            "true_seconds_to_fixing": sec, "floored_seconds": max(sec, 3600),
            "true_iv": .20, "refit_iv": refit_iv,
            "actual_price_index_points": price,
            "fixed_IV_floor_price_index_points": float(fixed["price"]),
            "refit_price_index_points": float(refit["price"]),
            "actual_gamma_per_index_point": float(actual["gamma"]),
            "fixed_IV_floor_gamma_per_index_point": float(fixed["gamma"]),
            "refit_gamma_per_index_point": float(refit["gamma"]),
            "fixed_IV_gamma_ratio": float(fixed["gamma"] / actual["gamma"]),
            "refit_gamma_ratio": float(refit["gamma"] / actual["gamma"]),
        })
    record_check("fixed_IV_floor_suppresses_1s_gamma",
                 rows[0]["fixed_IV_gamma_ratio"] < .02)
    check_close("TTE_floor_inactive_after_one_hour",
                rows[-1]["fixed_IV_gamma_ratio"], 1)
    # Nonzero carry is a separate diagnostic; same-price gamma equality is
    # NOT asserted as universal.
    sec = 15
    actual = bs(S0, S0, sec / YEAR_SECONDS, .20, True, R, DIVIDEND_YIELD)
    iv = implied_vol(float(actual["price"]), S0, S0, 3600 / YEAR_SECONDS,
                     True, R, DIVIDEND_YIELD)
    refit = bs(S0, S0, 3600 / YEAR_SECONDS, iv, True, R, DIVIDEND_YIELD)
    check_close("nonzero_carry_refit_preserves_price",
                float(refit["price"]), float(actual["price"]), atol=2e-9)
    return {
        "zero_carry_ATM_rows": rows,
        "zero_carry_identity": "At fixed S,K and r=q=0, price depends on sigma*sqrt(tau); same-price refitting preserves delta/gamma while fixed-IV time flooring does not.",
        "nonzero_carry_15s_diagnostic": {
            "r": R, "q": DIVIDEND_YIELD, "refit_iv": iv,
            "exact_gamma": float(actual["gamma"]),
            "same_price_refit_gamma": float(refit["gamma"]),
            "refit_gamma_ratio": float(refit["gamma"] / actual["gamma"]),
        },
        "scope": "The exact equality is a special zero-carry identity, NOT a universal empirical or model-independent near-expiry claim.",
    }


def commission_scenario():
    g0 = greek_state(S0)
    g1 = greek_state(S1, IV_SHIFT, HORIZON_MINUTES)
    # One independent central-difference witness for each derivative used by
    # the approximation, addressing sign and unit risk without a large test grid.
    test_tau = 3 / 365
    oracle = bs(S0, 6010, test_tau, .22, True)
    spot_step, iv_step, year_step = .01, 1e-5, 1 / YEAR_SECONDS
    gamma_bump = (bs(S0 + spot_step, 6010, test_tau, .22, True)["delta"]
                  - bs(S0 - spot_step, 6010, test_tau, .22, True)["delta"]) / (2 * spot_step)
    vanna_bump = (bs(S0, 6010, test_tau, .22 + iv_step, True)["delta"]
                  - bs(S0, 6010, test_tau, .22 - iv_step, True)["delta"]) / (2 * iv_step)
    charm_bump = (bs(S0, 6010, test_tau - year_step, .22, True)["delta"]
                  - bs(S0, 6010, test_tau + year_step, .22, True)["delta"]) / (2 * year_step)
    check_close("gamma_matches_delta_spot_bump", float(oracle["gamma"]), float(gamma_bump), atol=1e-9, rtol=1e-6)
    check_close("vanna_uses_decimal_IV", float(oracle["vanna"]), float(vanna_bump), atol=1e-8, rtol=1e-6)
    check_close("calendar_charm_advances_time", float(oracle["charm_calendar"]), float(charm_bump), atol=1e-6, rtol=1e-6)
    h1 = H0 + DH
    fixed_q = -H0 * MULT * (g1["delta"] - g0["delta"])
    joint_q = -MULT * (h1 * g1["delta"] - H0 * g0["delta"])
    linear_q = linear_change(S1, IV_SHIFT, HORIZON_MINUTES, H0, DH)
    by_cohort = {}
    for cohort in ["0DTE", "1-7D", "8+D"]:
        mask = COHORTS == cohort
        by_cohort[cohort] = {
            "contract_series_count": int(mask.sum()),
            "fixed_inventory_hedge_change": float(fixed_q[mask].sum()),
            "joint_hedge_change": float(joint_q[mask].sum()),
            "joint_endpoint_notional_USD": float(S1 * joint_q[mask].sum()),
        }
    check_close("cohort_joint_sum", sum(r["joint_hedge_change"] for r in by_cohort.values()),
                float(joint_q.sum()))
    check_close("commission_direct_joint_reprice", float(joint_q.sum()),
                exact_change(S1, IV_SHIFT, HORIZON_MINUTES, H0, h1))
    scenarios = {}
    for name, h in inventory_scenarios().items():
        q = exact_change(S1, IV_SHIFT, HORIZON_MINUTES, h, h)
        scenarios[name] = {
            "fixed_inventory_hedge_change": q, "endpoint_notional_USD": S1 * q,
            "probability_weight": None,
        }
    record_check("inventory_alternatives_can_reverse_pressure_sign",
                 min(x["endpoint_notional_USD"] for x in scenarios.values()) < 0
                 < max(x["endpoint_notional_USD"] for x in scenarios.values()))
    return {
        "label": LABEL, "initial_spot": S0, "scenario_spot": S1,
        "spot_change_percent": DS_PCT, "IV_change_decimal": IV_SHIFT,
        "IV_change_percentage_points": 100 * IV_SHIFT,
        "elapsed_calendar_minutes": HORIZON_MINUTES,
        "initial_target_hedge_units": hedge(S0),
        "final_target_fixed_inventory": hedge(S1, IV_SHIFT, HORIZON_MINUTES, H0),
        "final_target_changed_inventory": hedge(S1, IV_SHIFT, HORIZON_MINUTES, h1),
        "fixed_inventory_hedge_change": float(fixed_q.sum()),
        "joint_hedge_change": float(joint_q.sum()),
        "joint_endpoint_notional_USD": float(S1 * joint_q.sum()),
        "first_order_joint_hedge_change": linear_q,
        "first_order_joint_endpoint_notional_USD": float(S1 * linear_q),
        "exact_minus_linear_endpoint_USD": float(S1 * (joint_q.sum() - linear_q)),
        "by_cohort": by_cohort,
        "inventory_sign_alternatives": scenarios,
        "hedge_unit_definition": "USD sensitivity per SPX index point; a modeled common-index coordinate, not executable SPX shares.",
        "execution_or_forecast_claim": False,
    }


def make_figure(path: Path, results: dict):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter, LogLocator, ScalarFormatter

    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.titlesize": 13, "axes.titleweight": "bold",
        "axes.labelsize": 10.5, "axes.edgecolor": "#8996A5",
        "axes.spines.top": False, "axes.spines.right": False,
        "grid.color": "#DCE3EB", "grid.linewidth": .65,
        "legend.frameon": False, "savefig.facecolor": "white",
        "figure.facecolor": "white",
    })
    fig, ax = plt.subplots(2, 2, figsize=(16, 11), dpi=200)
    fig.subplots_adjust(left=.075, right=.97, top=.825, bottom=.18,
                        hspace=.53, wspace=.24)
    fig.text(.075, .964, "SYNTHETIC | Dealer-pressure mechanics",
             fontsize=24, fontweight="bold", color="#10273F")
    fig.text(.075, .929, "No observed positions • No alpha or backtest • Conditional target hedges, not executed flow",
             fontsize=12, color="#526477")
    fig.text(.075, .895,
             "14 invented SPX/SPXW series   |   Initial SPX coordinate 6,000   |   European pricing, ACT/365F   |   Fixed carry: r = 4%, q = 1.5%",
             fontsize=10.5, color="#526477")

    changes = np.linspace(-1.0, 1.0, 241)
    spots = S0 * (1 + changes / 100)

    def usd_curve(dt, h_start=H0, h_end=None, linear=False):
        return np.array([
            s * (linear_change(s, IV_SHIFT, dt, h_start, (h_end - h_start) if h_end is not None else None)
                 if linear else exact_change(s, IV_SHIFT, dt, h_start, h_end))
            / 1e6 for s in spots])

    def format_pressure(a):
        a.axhline(0, color="#7C8EA1", lw=.8)
        a.axvline(DS_PCT, color="#778591", lw=1.1, ls=(0, (3, 3)))
        a.grid(axis="both", alpha=.8)
        a.set_xlim(-1, 1)
        a.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:+.1f}%"))
        a.set_xlabel("Hypothetical spot move from 6,000")
        a.set_ylabel("Incremental target hedge notional ($m)")
        a.tick_params(colors="#384B5F")

    a = ax[0, 0]
    for dt, color in [(0, "#A6BFD7"), (20, "#397CAA"), (40, "#126477"), (55, "#132C49")]:
        a.plot(changes, usd_curve(dt), color=color, lw=2.2,
               label=f"+{dt} min" + (" (5 min remain)" if dt == 55 else ""))
    format_pressure(a)
    a.set_title("A  Nonlinear demand across future times", loc="left", pad=30)
    a.text(0, 1.035, "IV +1.2 points; fixed front-short / back-long book",
           transform=a.transAxes, color="#657588", fontsize=9.5)
    a.legend(loc="lower right", fontsize=9)

    a = ax[0, 1]
    names = {
        "front_short_back_long": "Short 0DTE; long later",
        "front_long_back_long": "Long all expiries",
        "call_long_put_short": "Long calls; short puts",
    }
    for (name, h), color in zip(inventory_scenarios().items(), ["#146A81", "#CA6534", "#7858A6"]):
        a.plot(changes, usd_curve(20, h), color=color, lw=2.2, label=names[name])
    format_pressure(a)
    a.set_title("B  Inventory assumptions can reverse the sign", loc="left", pad=30)
    a.text(0, 1.035, "+20 min; IV +1.2 points; identical unsigned position magnitudes",
           transform=a.transAxes, color="#657588", fontsize=9.5)
    a.legend(loc="lower center", fontsize=9)

    a = ax[1, 0]
    exact = usd_curve(20, H0, H0 + DH)
    approx = usd_curve(20, H0, H0 + DH, linear=True)
    a.plot(changes, exact, color="#123D62", lw=2.4, label="Full repricing + inventory change")
    a.plot(changes, approx, color="#CC7734", lw=2.0, ls="--",
           label="First-order Greeks + initial flow delta")
    format_pressure(a)
    a.set_title("C  Local Greeks are an approximation", loc="left", pad=30)
    a.text(0, 1.035, "+20 min; IV +1.2 points; stated synthetic inventory update",
           transform=a.transAxes, color="#657588", fontsize=9.5)
    actual = results["commission_scenario"]["joint_endpoint_notional_USD"] / 1e6
    a.scatter([DS_PCT], [actual], color="#123D62", edgecolor="white", s=65, zorder=6)
    a.annotate(f"Commission shock\n−0.35%: {actual:+.1f}m",
               xy=(DS_PCT, actual), xytext=(-.90, actual + 80),
               fontsize=9.5, color="#123D62",
               arrowprops={"arrowstyle": "-", "color": "#123D62", "lw": .8},
               bbox={"boxstyle": "round,pad=.35", "fc": "white", "ec": "#D7E1EA", "alpha": .95})
    a.legend(loc="upper left", fontsize=8.8)

    a = ax[1, 1]
    rows = results["witnesses"]["tte_floor"]["zero_carry_ATM_rows"]
    xs = [r["true_seconds_to_fixing"] for r in rows]
    a.plot(xs, [r["refit_gamma_ratio"] for r in rows], color="#136F79",
           lw=2.4, marker="o", ms=4, label="Same price; refit IV")
    a.plot(xs, [r["fixed_IV_gamma_ratio"] for r in rows], color="#CA6534",
           lw=2.2, marker="o", ms=4, label="Keep IV fixed; floor time")
    a.set_xscale("log")
    a.set_xlim(.8, 5000)
    a.set_ylim(0, 1.12)
    a.set_xticks([1, 10, 60, 300, 900, 3600], labels=["1", "10", "60", "300", "900", "3,600"])
    a.grid(alpha=.8)
    a.set_ylabel("Computed gamma / exact-time gamma")
    a.set_xlabel("True time to fixing (seconds; logarithmic scale)")
    a.set_title("D  A one-hour TTE floor has no universal bias", loc="left", pad=30)
    a.text(0, 1.035, "Separate ATM diagnostic: r = q = 0; same option price",
           transform=a.transAxes, color="#657588", fontsize=9.5)
    a.legend(loc="lower right", fontsize=9)
    a.text(.025, .80, "Price refitting preserves gamma here\nby a special total-variance identity.",
           transform=a.transAxes, fontsize=9, color="#31606A", va="top")

    fig.text(.075, .104,
             "SIGN: positive means modeled purchases; negative means modeled sales. Dollar values use the scenario endpoint price.",
             fontsize=10, fontweight="bold", color="#344A60")
    fig.text(.075, .075,
             "Vertical dashed line: the commission's −0.35% spot shock. No expiry boundary is crossed in panels A–C. Scenario bands have no probability weights.",
             fontsize=9.6, color="#526477")
    fig.text(.075, .046,
             "SPX hedge units are a risk coordinate, not executable shares. Futures conversion requires a declared basis. Panel D is an identity witness, not a market finding.",
             fontsize=9.6, color="#526477")
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=LABEL)
    parser.add_argument("--outdir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    witnesses = {
        "identifiability": witness_identifiability(),
        "buy_to_close": witness_buy_to_close(),
        "endpoint_and_cash": witness_endpoint_and_cash(),
        "four_factor_shapley": witness_shapley(),
        "general_h_m_delta_decomposition": witness_general_decomposition(),
        "path_net_and_turnover": witness_path(),
        "cross_product_units": witness_cross_product(),
        "tte_floor": witness_tte_floor(),
    }
    scenario = commission_scenario()
    results = {
        "schema": "mastermind.synthetic_dealer_pressure_witness/v1",
        "label": LABEL,
        "generated_at_UTC": datetime.now(timezone.utc).isoformat(),
        "script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "model_conventions": {
            "pricing": "European Black-Scholes with continuous carry; no American exercise or settlement transition simulated",
            "day_count": "ACT/365F, 31,536,000 seconds per year",
            "spot": S0, "r_synthetic": R, "q_synthetic": DIVIDEND_YIELD,
            "IV_units": "decimal annualized; +1.2 percentage points = +0.012",
            "charm": "advancing calendar-year derivative; -dDelta/dremaining_year",
            "inventory": "invented signed contracts; no posterior or observed OI allocation",
            "vol_surface": "per-expiry flat starting IV, frozen strike IV plus parallel shock",
            "fixing": "invented positive economic remaining times; no actual series calendar or expiry crossing",
            "dollar_conversion": "common-index hedge-unit difference times endpoint index level; not cash consideration",
        },
        "book": [asdict(c) for c in BOOK],
        "witnesses": witnesses,
        "commission_scenario": scenario,
        "assertion_count": len(CHECKS),
        "assertions_passed": sum(c["passed"] for c in CHECKS),
        "checks": CHECKS,
        "artifacts": {
            "script": "dealer_pressure_witness.py",
            "results": "results.json",
            "figure": "dealer_pressure_synthetic.png",
            "method": "METHOD.md",
        },
    }
    result_path = args.outdir / "results.json"
    result_path.write_text(json.dumps(results, indent=2, allow_nan=False) + "\n")
    make_figure(args.outdir / "dealer_pressure_synthetic.png", results)
    print(LABEL)
    print(f"Assertions: {len(CHECKS)}/{len(CHECKS)} passed")
    print(f"Commission joint target change: {scenario['joint_hedge_change']:+,.6f} common-index hedge units")
    print(f"Commission endpoint notional: ${scenario['joint_endpoint_notional_USD']:+,.2f}")
    print(f"Exact minus first-order notional: ${scenario['exact_minus_linear_endpoint_USD']:+,.2f}")
    print(f"Results: {result_path.resolve()}")
    print(f"Figure: {(args.outdir / 'dealer_pressure_synthetic.png').resolve()}")


if __name__ == "__main__":
    main()
