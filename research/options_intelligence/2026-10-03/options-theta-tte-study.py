"""Synthetic TTE/IV sensitivity witness; no market data or ThetaData calls.

Black-Scholes European calls with r=q=0, ACT/365F.
Price and Greeks are per underlying unit, not per option contract.
Vega and vanna are per absolute volatility unit (0.01 = one vol point).
Charm is d(delta)/d(calendar time), per calendar year, with S and sigma fixed.
This demonstrates mathematical possibilities; it does not prove vendor behavior.
"""

import json
import math
from pathlib import Path

YEAR_SECONDS = 365 * 24 * 3600


def normal_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def normal_pdf(x):
    return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)


def call_metrics(spot, strike, sigma, seconds_remaining):
    if min(spot, strike, sigma, seconds_remaining) <= 0:
        raise ValueError("positive spot, strike, volatility and TTE required")
    t = seconds_remaining / YEAR_SECONDS
    d1 = (math.log(spot / strike) + 0.5 * sigma * sigma * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    return {
        "price": spot * normal_cdf(d1) - strike * normal_cdf(d2),
        "iv": sigma,
        "delta": normal_cdf(d1),
        "gamma": normal_pdf(d1) / (spot * sigma * math.sqrt(t)),
        "vega_per_vol_unit": spot * normal_pdf(d1) * math.sqrt(t),
        "vanna_per_vol_unit": -normal_pdf(d1) * d2 / sigma,
        "charm_per_year": normal_pdf(d1) * d2 / (2 * t),
        "theta_per_year": -spot * normal_pdf(d1) * sigma / (2 * math.sqrt(t)),
    }


def refit_iv(price, spot, strike, seconds_remaining):
    lo, hi = 1e-9, 10.0
    for _ in range(150):
        mid = (lo + hi) / 2
        if call_metrics(spot, strike, mid, seconds_remaining)["price"] > price:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def run():
    rows = []
    for seconds in [3600, 1800, 900, 300, 60]:
        exact = call_metrics(100, 100, 0.20, seconds)
        fixed = call_metrics(100, 100, 0.20, 3600)
        refit = call_metrics(100, 100, refit_iv(exact["price"], 100, 100, 3600), 3600)
        rows.append({
            "seconds_remaining": seconds,
            "exact_time": exact,
            "floored_fixed_iv": fixed,
            "floored_refit_iv": refit,
            "fixed_iv_gamma_ratio": fixed["gamma"] / exact["gamma"],
            "refit_gamma_ratio": refit["gamma"] / exact["gamma"],
            "refit_vega_ratio": refit["vega_per_vol_unit"] / exact["vega_per_vol_unit"],
            "refit_charm_ratio": refit["charm_per_year"] / exact["charm_per_year"],
        })
    result = {
        "scope": "Synthetic Black-Scholes call; S=K=100; r=q=0; sigma_true=0.20; ACT/365F. Not vendor data and not a vendor implementation proof. Greeks per underlying unit; raw vega per absolute volatility unit; charm/theta per calendar year.",
        "rows": rows,
    }
    destination = Path(__file__).with_suffix(".json")
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print("seconds fixed_IV_gamma_ratio refit_IV refit_gamma_ratio refit_vega_ratio refit_charm_ratio")
    for row in rows:
        print(row["seconds_remaining"], *(f"{value:.6f}" for value in [
            row["fixed_iv_gamma_ratio"], row["floored_refit_iv"]["iv"],
            row["refit_gamma_ratio"], row["refit_vega_ratio"], row["refit_charm_ratio"],
        ]))


if __name__ == "__main__":
    run()
