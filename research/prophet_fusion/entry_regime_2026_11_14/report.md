# Entry/regime mechanism pilot

**RETROSPECTIVE_MECHANISM_PILOT_NOT_PROMOTION_BEARING**

This is a research consumer, not a buy list. No live authority is granted.

Source `6bbc4b0fc694c847077661ff5bf4c19ea41e4e81`; spec SHA256 `1f02b90917f69653b7659fc0b1883b6a7256224585ac22e1604293a8809b0a72`.
Window 2015-01-02 to 2026-05-29; next-session-close fills; 25 bps assumed round-trip costs.

## Data and interpretation limits

- Fixed survivor panel; not a point-in-time constituent universe or population estimate.
- Current price-history reconstruction is not original as-known vendor vintage data.
- Technical core excludes the live basket waiver and event latch; not board performance.
- Price adjustment basis has not been independently audited; no alpha or promotion claim.
- Fixed next-close returns are not executable stop/target outcomes or portfolio returns.
- Regime selection changes calendar exposure; beta residuals are descriptive, not a full risk-matched portfolio test.
- Historical eras were known before this study; pre-computation registration does not make them pristine out-of-sample data.
- No frozen W3/W2 race store, live rank, position size, trade or production service was changed.

## Fixed-horizon outcomes

Returns and positive-return rates below are equally weighted by decision date, not by ticker rows. Episodes exclude overlapping holding windows within a name. Different names can still share market risk.

### 21 sessions

| Arm | Events | Dates | Episodes | Net return | Excess vs SPY | Positive net | Retained |
|---|---:|---:|---:|---:|---:|---:|---:|
| technical_core_t12__unfiltered | 480 | 410 | 400 | 0.99% | -0.37% | 56.16% | 100.00% |
| technical_core_t12__market_uptrend | 372 | 329 | 308 | 0.71% | -0.35% | 54.69% | 77.50% |
| technical_core_t12__no_volatility_stress | 415 | 360 | 350 | 1.12% | -0.21% | 56.92% | 86.46% |
| trend_126_20_50__unfiltered | 351 | 319 | 303 | 0.92% | -0.04% | 60.01% | 100.00% |
| trend_126_20_50__market_uptrend | 281 | 253 | 245 | 1.11% | 0.10% | 61.82% | 80.06% |
| trend_126_20_50__no_volatility_stress | 325 | 297 | 281 | 1.18% | 0.18% | 61.03% | 92.59% |
| breakout_63__unfiltered | 987 | 786 | 520 | 0.76% | 0.05% | 57.26% | 100.00% |
| breakout_63__market_uptrend | 858 | 682 | 452 | 1.02% | 0.23% | 58.16% | 86.93% |
| breakout_63__no_volatility_stress | 949 | 755 | 503 | 0.86% | 0.08% | 57.60% | 96.15% |
| pullback_reclaim_20__unfiltered | 1033 | 809 | 590 | 1.03% | 0.01% | 57.53% | 100.00% |
| pullback_reclaim_20__market_uptrend | 892 | 690 | 511 | 1.07% | 0.12% | 57.16% | 86.35% |
| pullback_reclaim_20__no_volatility_stress | 944 | 746 | 549 | 1.03% | 0.02% | 57.12% | 91.38% |

### 63 sessions

| Arm | Events | Dates | Episodes | Net return | Excess vs SPY | Positive net | Retained |
|---|---:|---:|---:|---:|---:|---:|---:|
| technical_core_t12__unfiltered | 480 | 410 | 268 | 4.06% | 0.62% | 64.04% | 100.00% |
| technical_core_t12__market_uptrend | 372 | 329 | 214 | 3.53% | 0.59% | 61.20% | 77.50% |
| technical_core_t12__no_volatility_stress | 415 | 360 | 241 | 4.09% | 0.81% | 63.63% | 86.46% |
| trend_126_20_50__unfiltered | 351 | 319 | 234 | 3.58% | 0.26% | 63.61% | 100.00% |
| trend_126_20_50__market_uptrend | 281 | 253 | 191 | 3.59% | 0.33% | 63.60% | 80.06% |
| trend_126_20_50__no_volatility_stress | 325 | 297 | 218 | 3.99% | 0.67% | 64.45% | 92.59% |
| breakout_63__unfiltered | 987 | 786 | 300 | 3.16% | 0.36% | 61.21% | 100.00% |
| breakout_63__market_uptrend | 858 | 682 | 265 | 3.46% | 0.75% | 61.66% | 86.93% |
| breakout_63__no_volatility_stress | 949 | 755 | 296 | 3.23% | 0.45% | 61.58% | 96.15% |
| pullback_reclaim_20__unfiltered | 1033 | 809 | 311 | 3.87% | 0.46% | 61.92% | 100.00% |
| pullback_reclaim_20__market_uptrend | 892 | 690 | 279 | 3.79% | 0.74% | 62.02% | 86.35% |
| pullback_reclaim_20__no_volatility_stress | 944 | 746 | 295 | 3.88% | 0.60% | 61.96% | 91.38% |

## Prespecified primary contrasts

Paired 126-session calendar-block bootstrap; 11 prespecified contrasts. Familywise intervals use Bonferroni tail adjustment. This quantifies sampling uncertainty within the flawed historical panel; it does not repair survivor/vintage/basis bias or confer promotion eligibility.

| Challenger minus comparator | Delta excess | 95% interval | Familywise interval | Honest-N floor |
|---|---:|---|---|---|
| technical_core_t12__market_uptrend minus technical_core_t12__unfiltered | 0.02% | [-0.16%, 0.27%] | [-0.28%, 0.38%] | True |
| technical_core_t12__no_volatility_stress minus technical_core_t12__unfiltered | 0.16% | [0.01%, 0.37%] | [-0.04%, 0.48%] | True |
| trend_126_20_50__market_uptrend minus trend_126_20_50__unfiltered | 0.14% | [-0.14%, 0.44%] | [-0.28%, 0.61%] | True |
| trend_126_20_50__no_volatility_stress minus trend_126_20_50__unfiltered | 0.22% | [0.03%, 0.48%] | [-0.04%, 0.63%] | True |
| breakout_63__market_uptrend minus breakout_63__unfiltered | 0.18% | [-0.03%, 0.45%] | [-0.12%, 0.61%] | True |
| breakout_63__no_volatility_stress minus breakout_63__unfiltered | 0.02% | [-0.09%, 0.14%] | [-0.14%, 0.20%] | True |
| pullback_reclaim_20__market_uptrend minus pullback_reclaim_20__unfiltered | 0.10% | [-0.04%, 0.32%] | [-0.10%, 0.44%] | True |
| pullback_reclaim_20__no_volatility_stress minus pullback_reclaim_20__unfiltered | 0.01% | [-0.12%, 0.13%] | [-0.18%, 0.18%] | True |
| trend_126_20_50__unfiltered minus technical_core_t12__unfiltered | 0.33% | [-0.29%, 0.93%] | [-0.55%, 1.21%] | True |
| breakout_63__unfiltered minus technical_core_t12__unfiltered | 0.42% | [-0.38%, 1.12%] | [-0.74%, 1.42%] | True |
| pullback_reclaim_20__unfiltered minus technical_core_t12__unfiltered | 0.38% | [-0.13%, 0.99%] | [-0.35%, 1.23%] | True |

## Coverage

| Name | Sessions | Common qualified | Core unavailable |
|---|---:|---:|---:|
| AAPL | 2868 | 2850 | 15 |
| AMZN | 2868 | 2850 | 15 |
| AMT | 2868 | 2850 | 15 |
| CAT | 2868 | 2850 | 15 |
| DIS | 2868 | 2850 | 15 |
| JNJ | 2868 | 2850 | 15 |
| JPM | 2868 | 2850 | 15 |
| LIN | 2868 | 2850 | 15 |
| NEE | 2868 | 2850 | 15 |
| WMT | 2868 | 2850 | 15 |
| XOM | 2868 | 2850 | 15 |

Machine-readable report additionally retains rejected-trade results, winner retention, cost stress, beta-residual diagnostics, chronological halves, provisional/T1/T2 strata, source digests and the unchanged incumbent fold floors.
