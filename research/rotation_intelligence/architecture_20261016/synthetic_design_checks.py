#!/usr/bin/env python3
"""Research-only mathematical witnesses; no market data or product imports.

Run: python synthetic_design_checks.py > synthetic_design_results.json
This does NOT qualify LR-W6/V3, reproduce T12/T13, or measure investment skill.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import random
from statistics import NormalDist
import sys

SEED = 20261016
REPLICATIONS = 20000
N_SECTORS = 11
N_DATES = 60
NORMAL = NormalDist()


def close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-11, abs_tol=1e-12)


def deterministic_witnesses() -> list[dict]:
    rows: list[dict] = []
    def record(name: str, condition: bool, evidence: dict) -> None:
        if not condition:
            raise AssertionError(name)
        rows.append({"name": name, "passed": True, "evidence": evidence})

    a, b = [100, 110, 90, 100], [100, 90, 110, 100]
    portfolio = [(x+y)/2 for x, y in zip(a, b)]
    high, low = (max(a)+max(b))/2, (min(a)+min(b))/2
    record("synchronized_extrema", high > max(portfolio) == min(portfolio) > low,
           {"basket_path": portfolio, "weighted_member_high": high,
            "weighted_member_low": low})
    market, beta = -0.05, 0.6
    sector = beta * market
    record("defensive_beta_is_not_alpha", close(sector-market, 0.02),
           {"market_return": market, "sector_return": sector,
            "return_difference": sector-market, "true_residual": 0.0})
    rw = (1+sector)/(1+market)-1
    record("wealth_ratio_is_not_return_difference", not close(rw, sector-market),
           {"relative_wealth": rw, "return_difference": sector-market})
    old, new = [-0.04, 0, 0], [0, 0, 0]
    record("rolling_window_carry", close(sum(new)-sum(old), 0.04),
           {"window_change": sum(new)-sum(old), "new_relative_log_return": 0.0})
    origins = [2, 7, 20, 49]
    leads = [(t+5)-t for t in origins]
    record("mechanical_confirmation_lead", set(leads) == {5},
           {"leads": leads, "economic_prediction_proven": False})
    k, n, total = 30, 60, 100
    bounds = [k/total, (k+total-n)/total]
    record("missing_breadth_identification_bounds", bounds == [0.3, 0.7],
           {"observed_fraction": k/n, "whole_population_bounds": bounds,
            "confidence_interval": False})
    shares_old, shares_new, split_ratio, nav = 100, 200, 2, 50
    creation = (shares_new-shares_old*split_ratio)*nav
    record("split_is_not_creation", creation == 0,
           {"unadjusted_notional": (shares_new-shares_old)*nav,
            "split_adjusted_creation_notional": creation})
    theme_one, theme_two = [0.8, 0.2], [0.8, 0.2]
    underlying = [0.5*x+0.5*y for x, y in zip(theme_one, theme_two)]
    record("duplicate_themes_do_not_diversify", underlying == theme_one,
           {"theme_labels": 2, "distinct_exposure_vectors": 1,
            "underlying_weights": underlying})
    origin, training_cutoff = 100, 80
    feature_available, label_end = 99, 120
    record("future_target_is_valid_not_a_future_feature",
           feature_available <= origin < label_end and label_end > training_cutoff,
           {"forecast_feature_admissible": True, "target_later_than_origin": True,
            "that_label_usable_at_training_cutoff": False})
    prices = [100, 99, 110, 105]
    record("horizon_performance_need_not_be_monotonic",
           prices[1] < prices[0] < prices[-1] < prices[-2],
           {"short_return": prices[1]/prices[0]-1,
            "middle_return": prices[-2]/prices[0]-1,
            "long_return": prices[-1]/prices[0]-1})
    p, labels = 0.2, [1, 0, 0, 0, 0]
    full_brier = sum((p-y)**2 for y in labels)/len(labels)
    record("success_only_selection_changes_estimand", close(full_brier, 0.16),
           {"full_population_brier": full_brier, "success_only_brier": (p-1)**2})
    cost, bill_daily = 0.001, 0.0001
    early = (1-cost)*(105/100)*(1-cost)
    delayed = (1+bill_daily)**5*(1-cost)*(105/95)*(1-cost)
    cash = (1+bill_daily)**20
    record("common_terminal_date_does_not_force_early_win", delayed > early > cash,
           {"terminal_session": 20, "early_terminal_wealth": early,
            "delayed_terminal_wealth": delayed, "bills_terminal_wealth": cash,
            "early_trades_charged": 2, "delayed_trades_charged": 2,
            "cash_trades_charged": 0, "illustrative_cost_not_market_estimate": cost})
    return rows


def wilson(k: int, n: int) -> list[float]:
    z, p = NORMAL.inv_cdf(0.975), k/n
    d = 1+z*z/n
    center = (p+z*z/(2*n))/d
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [center-half, center+half]


def oracle_dependence_experiment() -> list[dict]:
    """Exact Gaussian panel-mean distribution; covariance is KNOWN, not estimated.

    Cov(X[s,t], X[j,u]) = C_sector[s,j] * phi**abs(t-u), unit variances.
    C_sector has diagonal 1 and off-diagonal rho. Dates may be AR(1).
    Only the sufficient statistic (mean) is sampled. This is not a market replay.
    """
    rng = random.Random(SEED)
    z_draws = [rng.gauss(0, 1) for _ in range(REPLICATIONS)]
    cutoff = NORMAL.inv_cdf(0.95)
    naive_se = 1/math.sqrt(N_SECTORS*N_DATES)
    rows = []
    for rho, phi in [(0.0, 0.0), (0.6, 0.0), (0.6, 0.5)]:
        sector_inflation = 1+(N_SECTORS-1)*rho
        time_inflation = 1+2*sum((1-lag/N_DATES)*phi**lag
                               for lag in range(1, N_DATES))
        inflation = sector_inflation*time_inflation
        true_se = naive_se*math.sqrt(inflation)
        naive_count = sum(z*true_se/naive_se > cutoff for z in z_draws)
        oracle_count = sum(z > cutoff for z in z_draws)
        expected_naive = 1-NORMAL.cdf(cutoff/math.sqrt(inflation))
        for count, expected in [(naive_count, expected_naive), (oracle_count, 0.05)]:
            tolerance = 5*math.sqrt(expected*(1-expected)/REPLICATIONS)+1/REPLICATIONS
            if abs(count/REPLICATIONS-expected) > tolerance:
                raise AssertionError("Monte Carlo disagrees with declared closed form")
        power = []
        for delta in [0.1, 0.2]:
            count = sum(z+delta/true_se > cutoff for z in z_draws)
            power.append({"mean_effect_in_unit_sd": delta,
                          "oracle_rejection_rate": count/REPLICATIONS,
                          "closed_form": 1-NORMAL.cdf(cutoff-delta/true_se)})
        rows.append({"cross_sector_correlation": rho, "temporal_ar1": phi,
                     "variance_inflation_vs_iid": inflation,
                     "effective_n_under_declared_covariance": N_SECTORS*N_DATES/inflation,
                     "naive_false_positive_rate": naive_count/REPLICATIONS,
                     "naive_rate_closed_form": expected_naive,
                     "naive_mc_wilson95": wilson(naive_count, REPLICATIONS),
                     "oracle_false_positive_rate": oracle_count/REPLICATIONS,
                     "oracle_mc_wilson95": wilson(oracle_count, REPLICATIONS),
                     "illustrative_oracle_power": power})
    return rows


def main() -> None:
    result = {"scope": "synthetic_design_witnesses_only", "seed": SEED,
              "python_version": sys.version.split()[0],
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "market_data_read": False, "production_imports": False,
              "native_lr_qualification": False, "replications": REPLICATIONS,
              "panel_sectors": N_SECTORS, "panel_dates": N_DATES,
              "deterministic_witnesses": deterministic_witnesses(),
              "oracle_dependence_experiment": oracle_dependence_experiment()}
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))

if __name__ == "__main__":
    main()
