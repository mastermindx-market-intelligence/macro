# GTAA final per-asset caps — validation, 2026-11-11

## Result and scope

The corrected GTAA allocator enforces final per-asset weights of **30% / 40% / 55%** after volatility scaling and gross-exposure reduction. It does not redistribute released allocation or scale the capped book back up. On the paired historical replay, all **6,605 asset-date cap violations** disappear; every repaired held weight equals the corresponding original held weight clipped to its profile's cap.

This repairs the portfolio calculation and its consumers, not just the displayed percentages. The existing accounting, signals, warmup, holding cadence, benchmarks and cost conventions are unchanged. The repaired Moderate book remains a **CONFIRMER**: its advantage over the same capped allocator with constant conviction is not stable across evaluation folds or crisis omissions. The separate TSMOM overlay study retains its own classification and DSR; those results are not attributed to GTAA.

**Data endpoint:** 2026-11-10. **Validation date:** 2026-11-11. **Historical input and original-source commit:** [`20197727622e5bf4da2e7306bf612fb533466250`](https://github.com/mastermindx-market-intelligence/macro/tree/20197727622e5bf4da2e7306bf612fb533466250). These are dated research results. Generated HTML and JSON were checked through the actual builder; deployed-browser state is outside this evidence.

## 1. Allocation contract

| Profile | Volatility target | Gross cap | Final cap per asset |
|---|---:|---:|---:|
| Conservative | 7% | 1.2× | 30% |
| Moderate | 12% | 1.6× | 40% |
| Aggressive | 22% | 2.5× | 55% |

In [`engine/masterminds.py`](../engine/masterminds.py), the final clip follows the existing gross reduction and precedes the existing five-row sample-and-hold. Upstream weights are nonnegative. The final operation therefore cannot increase gross exposure. A constant cap also commutes with the hold, which supplies the paired historical invariant checked above.

The volatility target is subordinate to the exposure limits. Reducing a sleeve can remove a hedge, so the cap does not mathematically guarantee lower portfolio variance, a particular drawdown, or achievement of the volatility target. The report below measures the actual historical consequences instead of assuming them.

Preserved conventions:

- Each asset remains unavailable until **300 calendar days** after its first valid price.
- Targets change on every **fifth input observation**, without assuming a weekday.
- The portfolio backtester applies targets **one bar later**.
- Below 100% gross, residual capital earns the modeled bill rate. Above 100%, financed exposure pays that rate plus the existing **1 percentage point spread**.
- Turnover costs remain **3 bps** for GTAA. The existing benchmark constructions are unchanged.
- A zero finite realized volatility uses the existing volatility floors. A missing asset or unavailable history retains its existing zero-exposure treatment.

For example, two capped Aggressive sleeves total 110%, so the repair retains 10% financing. It does not normalize that book to 100%. An asymmetric discriminator verifies that capping `[3c, c/2]` produces `[c, c/2]`, without transferring allocation to the second sleeve.

## 2. Native inputs and reproducibility

The paired replay uses the complete configured cache-read closure: **167 Yahoo paths, 205 FRED paths and 24 additional fixed paths**, for **396 unique data files**. Every file is present at the input commit and was materialized with its exact Git blob identity. The configuration and selectors were not trimmed to the nine traded assets.

That matters because `build_features()` takes the start of its calendar from the earliest configured Yahoo history, while the drawdown-risk percentile is expanding. The actual native feature calendar contains **25,793 rows, 1927-12-30 through 2026-11-10**. The GTAA price panel contains the normal nine assets and **4,935 rows, 2007-05-01 through 2026-11-10**.

Native-return observation confirmed that the real `_conviction()` completed its regime calculation. Recession, drawdown and RORO ranks each have **4,682 usable observations after alignment, the two-row lag and percentile warmup**, starting 2008-05-01. Every asset's native regime contribution has nonzero history. The consumed gauges, component histories and regime contributions are identical before and after the repair. The historical qualification therefore does not rely on the missing-macro neutral fallback used in some synthetic tests.

| Runtime component | Version |
|---|---|
| Python | 3.14.7 |
| NumPy | 2.5.2 |
| pandas | 3.0.5 |
| PyArrow | 25.0.1 |

Selected unchanged numerical/input dependencies at the input commit:

| File | Git blob |
|---|---|
| `config.yml` | `5be75249c98033d7ee0fbe55928713b1f50af627` |
| `engine/masterminds.py` before repair | `932a9619107909d55082d9c93660c2ca2e6a8c37` |
| `engine/active_alloc.py` | `e72f916889c9e6f2d3eaabbf83f8b3ff7e363d9d` |
| `engine/conditions.py` | `d5c657d300d9d3a19d28bbb1ccf9fb5a2101f898` |
| `engine/validation.py` | `c9a09740cd630f920e52fd21b88ff36ff31366b6` |
| `engine/trial_ledger.py` | `b9b444015549a691b9ab917590cc920ef6c8bb89` |
| `data/trial_ledger.jsonl` | `0dda3d14723dd5d9b2a136ca623f50fb3f3636c5` |

The numerical replay called the native `_prices`, `_conviction`, `_weights`, `backtest`, portfolio accounting and validation functions. The explicitly labeled constant-conviction control changes only conviction to one; the same repaired sizing and accounting implement that control. No alternative estimator or synthetic market series supplies the historical headline.

For reproduction, use an isolated checkout of this change, retain the unchanged configuration, and materialize its configured market/macro input paths from the input commit above. The ledger comes from that same commit. Run:

```sh
python -m pytest tests/test_build_live_overlay.py tests/test_masterminds_hub.py tests/test_active_alloc.py -q
python scripts/mastermind_moderate_phase0.py
python -m scripts.build_masterminds
```

The ordinary project dependencies and normal test fixtures apply. Comparing the original and repaired engines on those identical inputs should reproduce the weight invariant and before/after table. Different data revisions can legitimately change later scorecards; the Signal Lab quote is explicitly dated.

## 3. Regression and consumer checks

The original allocator failed **13** of the new cap assertions. The first focused run returned **13 failed, 9 passed, 6 deselected**; those failures included all one- and two-rising-asset cases, no-redistribution, zero/changing volatility, holding/execution timing and a missing optional asset.

The final native run passed **65 tests** across the live-overlay, Masterminds hub and active-allocation suites. They include 21 new cap cases, five claim/availability cases and four read-only trial-budget cases. Four additional existing Signal Lab shape/citation/tier/template consumer tests passed (**27 unrelated tests deselected**).

The integrated synthetic cases supply 800 business-day price observations and external cache/bill-rate fixtures while executing the actual conviction, trend, sizing, backtest and JSON functions. Their settled allocations are:

| Rising assets | Conservative | Moderate | Aggressive |
|---|---:|---:|---:|
| Zero | 0% | 0% | 0% |
| One | 30% | 40% | 55% |
| Two | 30% each | 40% each | 55% each |
| Nine | 13.333% each | 17.778% each | 27.778% each |

Additional cases check unequal sleeves without redistribution; zero, missing and changing volatility; a missing optional asset; an asset with late-starting history; held targets between rebalance rows; next-bar execution; and settled-row cash/financing arithmetic. JSON weights come from the real output, without a formatting clamp.

Copy tests preserve the correct profile benchmark and both-halves CAGR claims while rejecting invented risk superiority. A CAGR winner with lower Sharpe and a deeper drawdown cannot claim risk-adjusted alpha. A missing split-half result is unavailable, not an observed failure. Zero or negative benchmark Sharpe is displayed through the measured values rather than a misleading multiple.

The new cap and ledger regressions reside in the already-owned `tests/test_build_live_overlay.py`; its existing CI owners include `hk-robustness-w5` and `unrun-builders-stores`. Hub claim tests remain in `tests/test_masterminds_hub.py`, owned by `engine-render-guards`. No new CI lane or routing rule was added. The four additional Signal Lab checks here are executed native evidence, not a claim that that entire test file is enrolled in hosted CI.

## 4. Paired full-history results

The return and weight windows are identical before and after repair. CAGR uses calendar elapsed time; Sharpe and drawdown use the unchanged native functions and their annualization convention. All figures below are net of the existing modeled costs and financing.

| Profile | CAGR before → after | Sharpe before → after | Max drawdown before → after | Maximum asset weight before → after | Violating asset-date cells before → after |
|---|---:|---:|---:|---:|---:|
| Conservative | 7.7356% → 7.8796% | 1.1006 → 1.1279 | −17.3302% → −14.7680% | 90.0000% → 30.0000% | 310 → 0 |
| Moderate | 11.1900% → 11.1937% | 1.0367 → 1.0581 | −24.2249% → −21.6207% | 98.6903% → 40.0000% | 1,455 → 0 |
| Aggressive | 16.5431% → 16.0132% | 0.9560 → 0.9811 | −35.0237% → −31.6856% | 143.9114% → 55.0000% | 4,840 → 0 |

Gross maxima remain **1.2 / 1.6 / 2.5**, within floating-point tolerance. Every previously compliant held weight remains unchanged. The cell counts refer to asset-date weights, not distinct trades.

On the same window, the native SPY buy-and-hold benchmark reports approximately **10.64% CAGR, 0.61 Sharpe and −55.2% maximum drawdown**. The 60/40 SPY/IEF benchmark reports **8.20%, 0.75 and −31.4%**. Conservative is compared with 60/40 in its cards; the other profiles use SPY. The cap improves the measured drawdown here but reduces Aggressive CAGR; neither outcome is assumed in advance.

## 5. Split halves and Moderate robustness

The engine's `oos.robust` flag concerns **CAGR only**. It is false for every repaired profile:

| Profile / benchmark | First-half CAGR: strategy / benchmark | Second-half CAGR: strategy / benchmark | Wins both CAGR halves? |
|---|---:|---:|---|
| Conservative / 60-40 | 7.49% / 7.03% | 8.27% / 9.40% | No |
| Moderate / SPY | 11.48% / 6.93% | 10.91% / 14.50% | No |
| Aggressive / SPY | 17.67% / 6.93% | 14.38% / 14.50% | No |

For Moderate, Sharpe is **1.11 / 1.01** across the two halves versus SPY **0.42 / 0.83**. Its drawdown is **−17.6% / −21.6%**, versus SPY **−55.2% / −33.7%**. Those measured comparisons do not change the failed both-halves CAGR result.

The existing five-fold diagnostic, with a 63-observation embargo, gives:

| Fold | Moderate Sharpe | SPY Sharpe | Difference |
|---|---:|---:|---:|
| 1 | 1.21 | 0.06 | +1.15 |
| 2 | 1.18 | 1.00 | +0.17 |
| 3 | 1.12 | 0.72 | +0.40 |
| 4 | 0.78 | 0.56 | +0.22 |
| 5 | 1.24 | 1.43 | −0.19 |

Each fold contains 924 observations. **Four of five**, not five of five, favor Moderate. The existing leave-one-crisis-out comparisons retain the full-sample Sharpe and drawdown advantage over SPY after each of the six omissions: 2008, 2011, 2015–16, 2018Q4, 2020 and 2022. These overlapping historical diagnostics are not six independent new experiments.

The 21-observation block bootstrap, **5,000 draws with seed 7**, gives a Sharpe 95% interval of **[0.59, 1.54]**, median **1.06**, and a maximum-drawdown interval of **[−32.9%, −13.0%]**, median **−19.8%**. The sampled probability of positive Sharpe is 1.0. These are absolute-book diagnostics, not confidence intervals for incremental timing alpha.

## 6. Existing trial budget and dated DSR

The old Phase-0 script used three profiles as its headline trial count. The existing canonical ledger already declares **eight** for family `mastermind_moderate_phase0`. Its record is an **estimated retrospective budget**, with zero itemized configurations; it is not evidence of eight preregistered trials.

The repaired script reads the existing ledger through `TrialLedger` and calls the existing `deflated_sharpe(ledger=..., family=...)` API. It does not register trials, initialize a second ledger or append records. Missing family evidence, read errors, corrupt lines or a budget below the exposed profile count stop qualification instead of silently falling back to one or three. The complete ledger remained byte-identical after validation.

| DSR calculation on the repaired Moderate return series | Result |
|---|---:|
| Legacy three-profile diagnostic, not the ledger headline | 0.9999 |
| **Existing ledger budget, N = 8** | **0.9992** |
| Heavier sensitivity, N = 16 | 0.9975 |

The native ledger-backed run reports annual Sharpe **1.06**, haircut reference Sharpe **0.34**, skew approximately **−0.41**, kurtosis **6.0**, and **4,935** observations. It retains the existing raw-observation DSR convention; the separate block bootstrap does not convert that calculation into an effective-sample-size DSR.

Signal Lab quotes **0.9992 at N=8, calculated 2026-11-11**, with the existing ledger family and a dated frozen-quote basis. The displayed numeric result is a snapshot: a later change in the ledger budget does not itself recompute DSR. The separate historical 60/40 + 30% TSMOM overlay **0.9952** remains attributed to that study, with no GTAA Sharpe attached to its numeric field.

## 7. Incrementality and retained CONFIRMER classification

The matched control fixes conviction at one while retaining the same repaired inverse-volatility sizing, 12% volatility target, 1.6× gross cap, 40% final asset cap, timing, costs and cash/financing treatment.

| Moderate construction | CAGR | Sharpe | Maximum drawdown |
|---|---:|---:|---:|
| Four-factor conviction | 11.1937% | 1.0581 | −21.6207% |
| Constant conviction = 1 | 11.3944% | 1.0017 | −27.4057% |
| Difference | −0.2007 pp | +0.0565 | +5.7850 pp |

The signal-minus-control Sharpe differences in the same five folds are **+0.3527, +0.3215, −0.4013, −0.0129 and −0.1694**. The signal loses in **three of five** folds. Its Sharpe increment also turns negative when omitting **2008 (−0.0477)** or **2022 (−0.0064)**. This supports retaining the existing CONFIRMER classification, without promoting the book on its high absolute DSR.

The existing no-regime ablation, with the other factor weights renormalized, reports **10.59% CAGR, 0.98 Sharpe and −22.2% drawdown**. It still beats the same SPY and 60/40 benchmarks on those risk metrics. However, revised-data carry remains. Disabling the regime leg does not establish point-in-time correctness or exclude every possible data-revision effect.

## 8. Actual rendered output and JSON agreement

The actual `scripts.build_masterminds.build()` produced all three detail pages, the hub and `data/regime/masterminds_latest.json`. A read-only return observer captured the real native backtest outputs used by that invocation. Verification parsed each allocation row by ticker and percentage, compared every allocation with the emitted JSON and native weights, and compared the rendered CAGR, Sharpe and drawdown with the JSON values. English and Chinese cap, accounting and qualification text were present.

The emitted JSON passes strict finite-number parsing, keeps schema `masterminds.latest.v2`, contains three cards, and reports **asof 2026-11-10** consistently:

| Profile | Rendered and JSON CAGR | Sharpe | Maximum drawdown | Rounded current gross |
|---|---:|---:|---:|---:|
| Conservative | 7.88% | 1.13 | −14.8% | 0.10× |
| Moderate | 11.19% | 1.06 | −21.6% | 0.15× |
| Aggressive | 16.01% | 0.98 | −31.7% | 0.25× |

All 396 historical input files were reverified after rendering. The consumer check used the real generator and templates, with no HTML-only clamp and no replacement accounting. The existing generated-output workflow owns later publication; this source repair does not claim that an older deployed page has already refreshed.

The profile descriptions now explain their actual targets and final limits. Detail verdicts and the hub report measured full-sample comparisons and the separate CAGR split-half result. They no longer promise stable Sharpe superiority, shallower drawdowns, or risk-adjusted alpha solely from a CAGR flag. The hub's unrelated CSS and the other Signal Lab rows are preserved.

## 9. Retained evidence identities

SHA-256 identities for the executed qualification artifacts:

| Evidence | SHA-256 |
|---|---|
| Original input/source materialization manifest | `b4b54a8c51dc2c87072f832ebbb7cc83e79550e7f7ee77f9036dc2956b654d24` |
| Original-engine replay summary | `b3cefc77d3a8efd048287f0aef16e62d7b3858c20a26b03efcb0124db5a26bec` |
| Repaired-engine replay summary | `603cec9e03a391c1da2bc4bb04a4152545c16c1c803c3c794839c0011653aa82` |
| Final native 65-test result | `1220ef2a9035b337af111e4fb192c86fb8a8a61573ac145c83475738118969c4` |
| Four Signal Lab consumer tests | `acb0beb2b4158c67436dddc961e488c2e4d5d0c2aea8c83708febbbe34b64665` |
| Final ledger-backed Phase-0 stdout | `e3d740ed6712b865618dd390cfdc64bdd9834fd00e7bf58168c0301c73fb2d3a` |
| Rendered-output/JSON acceptance record | `d4c57a5f1e1c541ed2d7ddbe0e97c861cb97df2ced52e979f6e8f92e81b3c127` |
| Generated `masterminds_latest.json` | `a87263853b1a25aa7c3f3e09a280953d47ba384b49bceb39b54874f6ad2d3275` |

The executable regression tests, corrected native Phase-0 script and this dated report accompany the allocator change. The original historical `mastermind-moderate-phase0.md` report is preserved as historical evidence; the changed Signal Lab rows cite this renewed qualification.
