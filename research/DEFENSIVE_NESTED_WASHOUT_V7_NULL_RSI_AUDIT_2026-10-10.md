# V7 Defensive Nested Washout — Null Falsification and RSI Source-Identity Audit

**Date:** 2026-10-10. **MISSION_COMPLETE: false**. Research-only milestone, not real-stock validation, trading, deployment or authorized allocation.

## Parent mission, existing scope and protected law

The user's hypothesis remains 2W/W StochRSI long washout followed by native 1D/2D RSI-MACD bullish recovery. Earlier V2 price-MACD and standalone RSI(2) trials did not test this. Do not transfer their rankings. Current protected Mastermind master was read from `326c8469a21d7f50fc9ecb1848196bf1c6e66685` with INDEX, COLD_START, ACTIVE_EXECUTION and SESSION_RELIABILITY all compatible at skillpack1.0.1/bootstrap1. Existing research owner branch before V7 was `8c61fa6aa2f93bb885c0b6b63f59b061f0ac67a5`.

The Chairman newly allowed using M2 Studio. A read-only tool capability preflight and independent mathematical and **synthetic-only** computations succeeded on host `m2studio`, Python 3.14.7. This grants no override of earlier denied operations.

**Preserve denial fence:** V3 result-table read and the V4 composite remote workspace/earlier price-acquisition operation had been refused. No retry, changed carrier, equivalent acquisition/export, blocked-results computation, privilege change or raw market-input substitution was performed. Existing files with real vendor histories on M2 were not accessed. No user funds, orders, broker, watcher, background worker, live sizing, repo production code change or deployment effect occurred.

## A. Exact source-level discrepancy — material

Read-only GitHub verified current `macro/engine/canon.py` blob `32116817bbb4c844c2c811905eb8d778482342c6`, lines353–365, from pinned macro `9bcdbb4d887f1e2a082e1743cb84af6261fb25b4` and the current default. It implements:

```python
rs = up / dn.replace(0, np.nan)
return 100 - 100 / (1 + rs)
```

With positive seeded Wilder average gain and **exact zero seeded average loss**, mathematical RSI tends to100, but the repository returns NaN. The V4/V5/V6 research oracle explicitly uses RSI100 in that case and RSI50 for flat 0/0; exact TradingView flat-case parity is not attested. No production fix was made.

Constructed 110-up-session seed plus oscillations: the reference histogram first becomes finite at native index77, versus repo-literal index183. Reference bullish cross indices134,151,170,189,208,227,246,265,284; repo-literal indices189,208,227,246,265,284. Independent M2 pure-Python reproduction: 106 positive-gain/zero-loss inputs returned NaN in repo-literal logic. This is a manufactured source-parity finding; **real-stock prevalence and trade impact are unknown**, and the discrepancy is especially sensitive to history starting within an uninterrupted advance. It is not a universal parity ruling. TradingView calculation reference: https://www.tradingview.com/support/solutions/43000502338-relative-strength-index-rsi/.

## B. Null-model falsification — synthetic only, NOT equity performance

To quantify selection bias, V7 ran 32 deterministic **iid shared-factor synthetic** trials, 16 independent seeds with zero daily expected log drift and 16 with +0.00035 daily expected log drift. Each trial had18 correlated synthetic stocks and4,200 manufactured weekday sessions. The oscillator has **no predictive relationship with future iid innovations** by construction. Using the frozen completed-W/2W native washout, first daily RSI-MACD cross, next-open entry, 126-session common end, 10bp round-trip event-study normalization, and minimum five complete trigger events to rank a stock:

| Null regime | Confirmed events across16 seeds | Median pooled confirmed positive fraction | Median **best-looking-stock** positive fraction | Seeds whose best qualified stock >=75% positive |
|---|---:|---:|---:|---:|
| Zero log drift | 2,830 | 53.25% | 80.0% | 11/16 |
| +0.035% daily drift | 2,794 | 64.89% | 90.0% | 16/16 |

These fractions are realized outcomes within this synthetic generator, **not** estimated predictive edge, probability of backtest overfitting for real equities, p-value for user's approach, allocation signal or actual MCD/WMT/WM/COST/PG performance. The drift-conditioned null has positive unconditional holding returns; common-factor dependencies make stock signals correlate. Ex-post best stock often has a striking hit fraction despite no conditioned future-return forecast.

The within-seed median policy-versus-immediate-watch return difference in the positive-drift null was -0.77 percentage points on a common 126-session event window, with only1/16 seed positive; zero-drift was roughly -0.03pp median. This demonstrates a testable **delay/opportunity-cost** issue, not evidence against the real strategy. No calendar holidays, jumps, dividends, real spread or chart parity.

A separate M2 one-seed pilot returned a best-selected hit fraction87.5% in its synthetic rising-drift environment. It uses a different simplifying clock implementation and is not pooled with the32-run result. Neither activity touched restricted market inputs.

## C. Implementation integrity and files

A serial 16-seed attempt exhausted the local timeout without an output. The exact output path/process were inspected: no remaining process/output. A changed tactic, four CPU workers, completed the full32-run contract in33.46 seconds. A separate missing-return-column edge on entirely incomplete horizons produced a failure; this was repaired with a regression test that preserves incomplete as unknown.

Fresh verified tests: V6 inherited **91/91** pass; V7 new **11/11** pass; 32 synthetic trials exist in JSON/CSV;3 scenario/provenance result tables, original V4 reference file hash verified unchanged. All ZIP members pass SHA and ZIP integrity.

- V7 compact deliverable `/mnt/data/Defensive_Nested_Washout_V7_Null_And_RSI_Source_Audit_2026-10-10.zip`, SHA256 `6db4c7e5739f633510839a4d63ff2bd2d9929fff2517e32c00d4b1f38e6fdaf2`.
- Detailed report `/mnt/data/defensive_nested_v7/RESEARCH_FINDINGS.md`, SHA256 `a075a4ce710686f235dfb9e75152ec789ff1e5d3196a6fe3099e2153eec2daee`.
- 16 archive entries,14 premanifest members verified; no actual stock prices in package. Original V4 code SHA256 remains `25e0e91dc69e91e870f49e44ec05dcbdf636b79eaca3737fc58e2f4ec2895fd9`.

## Adjudication and next action

**Before:** corrected V6 oscillator/event engine was only mechanically checked and market-data access restricted. **After:** added a falsifiable repeated null benchmark showing selection/drift illusions, and identified/reproduced an upstream RSI zero-denominator source mismatch that could alter chart event availability. Neither constitutes a production fix or real-market alpha validation.

Actual historical nested RSI-MACD results, chart-setting parity, 1D-vs2D rankings, optimal exits, causal regime alpha and allocation remain UNPROVEN. Next useful empirical operation, only with legitimately supplied native-price/indicator export and permitted source access: verify chart parity and source RSI edge; freeze identical W+2W washes, compare 1D/2D confirmations, completed/developing bars, rejected/missed opportunities, same-opportunity returns and full account risk, with correlation-aware selection diagnostics. Do not use M2 or any new carrier to repeat a refused operation. No automatic wake or human ceremony is claimed. The independent mathematical/synthetic lane is now complete and documented; the remaining direct market-data lane has no cleared admission/evidence.

Primary methodological source: TradingView confirmed/repainting higher-timeframe semantics https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/ and RSI calculations (above). No synthetic result is a user-trade recommendation.
