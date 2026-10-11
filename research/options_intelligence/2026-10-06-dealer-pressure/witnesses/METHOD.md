# SYNTHETIC dealer-pressure mechanics witness

**SYNTHETIC — no observed dealer book, no market data, no alpha, no market backtest.**

The script checks eight concrete accounting/numerical risks raised in the research commission and document audit. It extends the accepted reference-contract reasoning with small reproducible witnesses. It does not replace production pricing, source admission, inventory, publication or evaluation owners.

## Rerun

From this directory:

```bash
python dealer_pressure_witness.py --outdir .
```

From the commission workspace:

```bash
python /workspace/scratch/3972f54b39b5/lanes/witness/dealer_pressure_witness.py --outdir /workspace/scratch/3972f54b39b5/lanes/witness
```

Dependencies in the executed runtime: Python, NumPy 2.3.5, SciPy 1.17.0, Matplotlib 3.10.8. No network access or private market-data access is needed.

**Executed result: 62/62 assertions passed.** Individual named checks, tolerance/error values, the full invented book and numerical results are in `results.json`. The JSON records the script SHA-256 so later edits are distinguishable. The 3,200 × 2,200 PNG is `dealer_pressure_synthetic.png`.

## Scope and pricing conventions

The primary example is a 14-series, invented European SPX/SPXW book with initial index coordinate 6,000:

| Cohort | Invented series | Remaining economic time | Starting IV | Initial dealer-sign scenario |
|---|---:|---|---:|---|
| 0DTE | 6 SPXW PM calls/puts at 5,975 / 6,000 / 6,025 | 60 calendar minutes | 20% | Short all six |
| 1–7D | 4 SPXW PM calls/puts at 5,950 / 6,050 | 3 calendar days + 60 minutes | 22% | Long all four |
| 8+D | 4 SPX AM calls/puts at 5,800 / 6,200 | 30 calendar days + 60 minutes | 24% | Long all four |

Every quantity, price, time and rate is invented. These are abstract economic remaining times, not a claim about a listed calendar or an actual AM/PM expiry event. All chart horizons remain before fixing, so no exercise, settlement transition or hedge-unwind behavior is simulated.

Pricing is European Black–Scholes with synthetic continuous rate 4%, dividend yield 1.5%, ACT/365F and multiplier 100. Delta is the long-option premium derivative in the native index coordinate. IV is decimal annualized volatility. Calendar charm is the derivative with advancing time, equivalently minus the remaining-time derivative. Each expiry begins with a flat IV; scenario IV is frozen by strike plus a parallel change. American exercise, discrete dividends, actual forward calibration and a complete no-arbitrage surface engine are outside this witness.

The fixed-risk-coordinate hedge target is

```
B = −Σ h_i m_i Delta_i
Q = B1 − B0
H = S1 × Q
```

For SPX, B is common-index sensitivity in USD per index point; it is **not executable SPX shares**. H is endpoint-valued target notional, not cash paid or actual trading volume. A cash-equity purchase has cash consideration `−price × shares`; a futures contract's notional does not have that cash meaning.

## What each bounded witness proves

| Risk | Constructed check | Claim limit |
|---|---|---|
| Dealer non-identification | Identical ask execution, initial OI = 0, both sides opening and final OI = 10 admit dealer signed changes +10, 0 and −10 | No real-world probabilities assigned; ask execution does not identify capacity |
| Buying to close | Dealer h goes from −5 to zero on a five-contract buy-to-close; net OI can stay unchanged | Opening-only gating would incorrectly discard the inventory change |
| Endpoint versus marking/cash | `S1(B1−B0)` differs from `S1B1−S0B0` by old-hedge revaluation | Synthetic index/futures cash consideration remains null |
| Four-factor attribution | Spot, IV, advancing time and inventory Shapley contributions use exactly 16 unique corner values of B and sum to Q | All dollar contributions use the same final price; marked holdings are not attributed as trading |
| Changing h, m and Delta | With `r_i=m_i Delta_i`, exact and symmetric h/r decompositions reconcile; fixed-m formula deliberately fails the general case | Canonical deliverable rebasing/risk-coordinate conversion is required before real aggregation |
| Endpoint versus path | Direct holdings [0,10] and oscillating [0,8,−3,10] both net 10, but gross turnover is 10 versus 32 | Hypothetical exact tracking; no actual dealer execution estimated |
| Cross-product units | One half-delta SPX = ten half-delta XSP = one ES exposure; one half-delta NDX = 100 half-delta XND = 2.5 NQ | Matched factor sensitivity and no basis risk are assumed for arithmetic only |
| TTE floor | Exact-time, fixed-IV time-floor and same-price refitted-IV Greeks differ; special zero-carry equality is checked | A one-hour floor has no universal gamma multiplier independent of IV fitting |

Three additional central-difference checks verify gamma, decimal-IV vanna and advancing-calendar-time charm at one independent pricing state. They address the exact sign/unit risk in the plotted first-order approximation. No broad model search or market test was run.

## Commission shock: an arithmetic example

The specific hypothetical question is 6,000 → **5,979** (−0.35%), IV **+0.012** (+1.2 percentage points), and **+20 calendar minutes**. The inventory-update variant reduces the 0DTE 6,000 call holding by 35 contracts and increases the 0DTE 6,000 put holding by 20 contracts. Those increments are invented inputs, not classified trades.

| Synthetic endpoint component | USD target notional |
|---|---:|
| 0DTE | −296,984,668.63 |
| 1–7D | +14,171,203.10 |
| 8+D | +2,232,713.36 |
| **Joint total, full repricing** | **−280,580,752.17** |
| First-order Greeks plus initial-state inventory delta | −316,271,027.04 |
| **Exact minus first-order residual** | **+35,690,274.88** |

Negative means modeled target sales in the declared common-index coordinate. It does not mean this flow is observed, probable, executed or large relative to real liquidity. The residual is approximately 12.72% of the absolute exact endpoint response for this one invented example; it is not an empirical approximation-error estimate.

The four-factor Shapley allocation of the same exact total is:

| Factor | Endpoint-valued contribution |
|---|---:|
| Spot | −291,361,515.16 |
| Volatility | +257,632.91 |
| Advancing calendar time | −3,846,545.72 |
| Invented inventory change | +14,369,675.79 |
| **Sum** | **−280,580,752.17** |

For **fixed inventory** under the same spot/IV/time shock, the initial front-short/back-long scenario yields −292.800 million USD. Reversing only the 0DTE inventory signs yields +325.608 million USD; the call-long/put-short convention yields −12.393 million USD. These are mutually alternative assumptions on identical unsigned position magnitudes, not a posterior or a calibrated uncertainty band.

## The near-expiry refitting distinction

The separate ATM diagnostic deliberately sets r = q = 0. In that special Black–Scholes state, option price depends on `sigma × sqrt(tau)`. Refitting IV to the **same price** after flooring remaining time to one hour preserves that total-volatility quantity, delta and gamma. Keeping IV fixed while changing time generally changes both price and gamma.

At one second remaining, the fixed-IV one-hour floor retains only about 1/60 of exact gamma, while same-price refitting retains gamma in this special model. The script checks 1, 5, 15, 60, 300, 900, 1,800, 3,599, 3,600 and 3,601 seconds.

A second 15-second diagnostic with r = 4% and q = 1.5% preserves price after refitting but produces a gamma ratio of about **1.0265**, showing that the exact zero-carry equality is not universal. Neither example calibrates actual near-expiry market IV or establishes a general correction factor.

## Figure reading

- **A:** fixed-inventory full-repricing target notional across spot at 0, 20, 40 and 55 future minutes; all retain IV +1.2 points.
- **B:** three inventory-sign assumptions at +20 minutes, with no probability weights.
- **C:** the fully repriced joint inventory/spot/IV/time response versus its initial-Greek approximation; the marked dot is the commission shock.
- **D:** the special zero-carry ATM gamma-ratio witness for fixed-IV versus same-price-refitted time flooring.

All curves are model mechanics. No curve is a forecast path, observed order book, probable market outcome, support/resistance assertion or recommendation.
