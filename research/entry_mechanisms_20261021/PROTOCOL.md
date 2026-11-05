# Mechanism-led entry research: frozen design

Registered 2026-10-21, before this continuation's executable-return tables were calculated. This is exploratory falsification on already exposed historical data. It is not a fresh holdout, a causal experiment, a parameter search, or a production strategy.

## Questions and reasons

1. **Objective audit:** do the already selected pivot signals have useful executable entry or exit outcomes even when they fail to identify an early durable extreme? Reuse all 34 frozen finalists; select no new oscillator parameter combination.
2. **Selection versus timing:** does an ordinary price recovery in an established price leader improve on comparable ordinary entries? Does Stoch RSI add useful information to those same price events? A fixed factorial distinguishes leadership from a recent reset. This is not a replication or replacement of the existing residual-momentum engine.
3. **Path versus endpoint:** can the positive fixed-horizon fraction survive one explicit, unoptimized loss-control policy? Keep the original durable-pivot outcome separate throughout.

The prior census motivates these questions: residual momentum has only context-level support after the internal PIT rerun; short-term reversal differs from stock selection; the old tuned bottom report is test-leaked; waiting for a two-week washout turn harmed one systemic-bear construction; the defensive V11 study found high six-month endpoint fractions but materially lower stopped-trade fractions. These different constructions are not interchangeable.

## Inputs and scope

Use only the retained, hash-verified 50-asset input snapshot of `../durable_pivots_20261021`, through 2026-10-08. Its 48 exchange-traded assets and two crypto assets remain separate. Current-survivor selection, current-vintage prices, imperfect corporate-action/dividend accounting, and the already examined sample limit inference. No new provider fetch, fundamentals, headlines, PIT membership, delisted history, or chart-parity claim is introduced.

Audit the inherited periods 1995–2013, 2014–2019, and 2020–2026. Both decision and complete outcome must lie within one period. These are descriptive historical strata, not newly independent training/validation/test sets. Use the original completed-bar indicators, original false-to-true events and 21-session cooldown unchanged. Original candle anchors remain fixed.

## Execution and outcomes

- Signal after close at session t; enter at t+1 open; fixed exits at t+21 and t+63 close. Thus the primary holding period is 63 entry sessions, and 21 is secondary. No same-close fills.
- Signals use split-adjusted, dividend-unadjusted OHLC as in the baseline. Return accounting uses the provider's daily adjclose/close factor on entry/exit prices as a dividend-return proxy. This is not a cash-dividend ledger or a historical bid/ask simulation.
- Long net return is `(adjusted_exit/adjusted_entry) * (1-c/2)/(1+c/2) - 1`, c=0.002 primary roundtrip friction; c=0.005 is a fixed cost sensitivity. These are assumptions, not measured historical execution costs.
- Bottom rules are long-entry diagnostics. Top rules measure the return forgone by exiting and remaining in zero-yield cash until the fixed endpoint; report avoided long return less c. This is not a short-sale strategy, and contains no borrow, taxes, or cash interest.
- One bottom risk diagnostic: stop = next entry open minus 3×signal-date daily ATR14 in the split-adjusted price basis. On the first subsequent low at/below stop, fill at the lower of that day's open and stop. No profit target. Exit at the horizon if no stop. This preserves opening gaps and does not infer high/low ordering.
- Report positive fraction, mean, median, mean winner/loser, 5th percentile, mean of worst 5%, maximum entry-relative adverse excursion, stop frequency, and stopped return distribution. A stop diagnostic is not a recommended risk policy or a threshold optimization.
- Record unique dates, quarters, assets, calendar concentration, and overlapping holdings. Also report a greedy per-rule/per-asset nonoverlap subset: accept the first event, then the next signal at/after the preceding fixed exit session. This rule never reads outcomes.
- No portfolio CAGR, Sharpe, maximum portfolio drawdown, sizing, calibrated future success probability, or guaranteed low/top is inferred from event returns.

## Comparable ordinary entries

For each asset, build ordinary next-open entry outcomes on every date with the same inherited indicator readiness and complete horizon. Form leave-one-out same-asset × signal half-year × own SMA200 regime × SPY SMA200 regime means and hit fractions; require at least 10 other eligible dates. Report match coverage rather than silently filling unavailable matches. These are descriptive conditional comparators, not randomized counterfactuals. They may share forward price paths.

Also report same-date, same-asset-class peer outcomes excluding the focal asset, and SPY at the same dates where available. Require at least two other peers for exchange assets; crypto has only one and is explicitly a two-name diagnostic. Use paired event-minus-comparator differences, not a ratio of unrelated aggregate returns. These comparators distinguish broad market/sector exposure from signal timing without claiming perfect factor neutrality.

Calendar uncertainty uses 2,000 circular bootstrap resamples of consecutive two-half-year blocks, with seed 20261021; preserve all names within each sampled block. Resampling reduces false precision from common episodes but does not cure survivor selection, research selection, or overlapping boundary paths. Intervals are exploratory and not multiplicity-adjusted. Do not rank a winner by the largest point estimate or report a discovery p-value.

## One leadership/reset construction

Use only the 22 retained US individual stocks. A fixed coarse sector map is recorded in code; a sector ETF must actually exist with sufficient trailing history. Do not backfill a missing ETF. Sector membership is a fixed research approximation, not historical GICS reconstruction.

**Lagged leadership:** at t-21, the stock closed above its SMA200, that SMA200 exceeded its value 20 sessions earlier, and its total return from t-21-252 to t-21-21 exceeded the contemporaneous SPY and sector ETF returns. This snapshot precedes the reset search window. Missing stock, SPY, or sector history is UNKNOWN and excluded from both leader and nonleader, with a missing-input count. No cross-sectional threshold fitting or fundamental-quality label.

**Chronological reset:** let p be the most recent highest high in the preceding 20 sessions, excluding t; let q be the most recent lowest low after p and before t. Require q to be in the preceding ten sessions, `(high_p-low_q)/ATR14_p >= 2`, and `0 <= (high_p-close_t)/ATR14_p <= 3`. No post-peak session means no reset. Thus peak precedes pullback, and the trigger remains below the old peak. This is a temporary weakness descriptor, not proof of forced selling or a floor. The 2-ATR convention is fixed, not optimized. This chronology replaces an earlier drafting idea after independent design review and before any new outcome table.

**Price recovery trigger:** the close at t crosses above EMA10 from at/below EMA10 at t-1. All definitions use only information known at t.

First show the descriptive 2×2 state census: leader/nonleader × reset/no-reset. State-day observations overlap and are not independent trades.

Then use one shared, price-trigger event roster with the inherited 21-session cooldown and report: all reset+reclaim events; its leader and nonleader subsets; and the exact leader-event roster partitioned by completed weekly Stoch curl, daily Stoch curl, and neither gate. Oscillators filter the original event; they do not postpone entry to a later, more favorable price. No threshold or anchor search is allowed.

In addition to the common comparators above, give leader/reset/market-state matched ordinary entries for the leadership events: same asset × half-year × pre-reset leader × reset × SPY regime, at least 10 other observations. Compare oscillator-accepted versus oscillator-rejected events, preserving the rejected observations in the report. This tests incremental association and coverage cost, not causality.

Report results across the inherited periods and market regimes, per asset and fixed sector grouping, including 2020 exclusion and semiconductor exclusion as two inherited concentration checks. No post-result regime-specific policy is installed. Any newly suggested explanation belongs in the hypothesis ledger, not in a repaired winning rule.

## Interpretation / falsifiers

- Positive raw returns with no improvement on matched ordinary entries support exposure or selection, not oscillator timing skill.
- A higher fixed-horizon hit fraction with materially worse tails or low stopped hit fraction does not meet a stable-return claim.
- If adding Stoch reduces coverage without improving the same underlying price-event distribution, retain it as context only.
- Report unstopped positive endpoints converted into stopped losses on exactly the same entries. Early stops do not create replacement trades or change the nonoverlap roster.
- If a conclusion depends on a few names or one crisis, keep it cohort-specific.
- Do not call price leadership business quality. Fundamental/event branches remain untested without an audited as-of information source.
- Do not resurrect killed constructions by renaming them. Any different construction must state its changed economic mechanism and evidence requirement.

The output is a research decision record and a proposed system architecture. Production promotion requires a separately frozen executable portfolio mandate and stronger data/prospective evidence.
