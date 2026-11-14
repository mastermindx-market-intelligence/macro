# Entry/regime mechanism pilot: findings and implementation decision

**Decision: research framework implemented and exercised; no new trading authority
or validated winner established.** None of the eleven preregistered primary
comparisons excluded zero in the multiple-comparison-adjusted interval. This is
not proof that every regime-conditioned strategy is useless, and it does not
invalidate a differently selected, context-rich live board. It does reject the
claim that this pilot demonstrates a win-rate or excess-return breakthrough.

## What was actually tested

The exact specification was committed at
`8212ce29603ef4f06196a63f877a7a845bbc2b03` before numerical outcomes. It fixes eleven
surviving names, January 2, 2015 through May 29, 2026, four price mechanisms and
three context versions, with eleven primary contrasts. The primary outcome is
21-session net return in excess of the same-window SPY return, equally weighted
by decision date. Fills occur at the next session's close; assumed round-trip
cost is 25 basis points, with 0/10/50-basis-point sensitivities retained.

The benchmark comparator is its gross same-window total-return price ratio; costs
are charged to the candidate trade. The experiment is not a risk-neutral portfolio,
an intraday stop/target simulation, a clean-liftoff win rate or a live-board replay.
The explicit technical T1/T2 core excludes the live basket waiver and event latch.
The fixed survivor population and reconstructed vendor-history limitations are
unchanged. Statistical resampling does not cure those limitations.

Execution completed successfully (original process exit 0). It evaluated 31,581
prefix observations, generated 2,851 trigger events and 5,702 event/horizon outcomes,
and emitted all 24 arm/horizon summaries. A separate implementation recomputed
all 5,702 outcomes and all 24 summaries/11 point contrasts from the captured prices;
maximum net-return arithmetic discrepancy was 4.45e-16. This is principal self-check
with independent arithmetic, NOT an independent reviewer or independent financial data.

Canonical evidence is in `entry_regime_2026_11_14/report.{json,md}` and
`verification.json`. The independent verifier does not recompute bootstrap interval
coverage or claim historical availability/selection validity.

## Results that answer the original win-rate question

Here 'positive-return rate' means positive net return at the fixed 21-session exit,
not target-before-stop accuracy. Returns and rates are equal-decision-date means.

| Mechanism/context | Events | Positive-net rate | Mean net return | Mean excess vs SPY |
|---|---:|---:|---:|---:|
| Technical T1/T2 core | 480 | 56.16% | +0.985% | -0.368% |
| T1/T2 + market-uptrend filter | 372 | 54.69% | +0.714% | -0.352% |
| T1/T2 + no-volatility-stress filter | 415 | 56.92% | +1.117% | -0.207% |
| Simple trend-state onset | 351 | 60.01% | +0.917% | -0.041% |
| Prior-63-session breakout | 987 | 57.26% | +0.762% | +0.054% |
| Pullback/reclaim | 1,033 | 57.53% | +1.030% | +0.015% |

The full report includes every context version and both horizons; the table above
is an explanation subset, not a selected winner list.

**A generic bull-market gate did not improve T1/T2's positive-return rate.** It
retained 77.5% of signals, lowered positive-return frequency by about 1.47 percentage
points, and reduced mean net return. Its excess-return difference was only +0.015
percentage points, with adjusted interval [-0.279, +0.383] percentage points, and
its chronological-half direction reversed after 2021.

**The stress filter was a plausible but unconfirmed research lead.** It retained
86.46% of T1/T2 events and lifted positive-return frequency by about 0.76 percentage
points. The primary excess-return delta was +0.160 percentage points. An unadjusted
interval was positive, but the prespecified eleven-comparison adjustment widened it
to [-0.042, +0.480] percentage points. Filtered T1/T2 mean excess itself remained
negative. Do not advertise a statistically qualified improvement or promote it.

**Win-rate optimization and payoff optimization differ even in this small sample.**
The simple trend alternative had a higher positive-return rate than T1/T2 but a
slightly lower mean net return. All three substitute-versus-T1/T2 primary adjusted
intervals straddled zero. No substitute earned replacement authority.

## Horizon and timing attribution

The descriptive 63-session T1/T2 result was +4.065% mean net return, +0.618% excess
and 64.04% positive-net frequency. The ranking of mechanisms differs from the
21-session view. This supports treating horizon as a separate research dimension;
it does NOT allow swapping the registered primary horizon after seeing results.

The predeclared auxiliary control compared each event with all common-qualified
entry dates for the same stock and calendar month, using the same fill/horizon/cost.
It evaluated 62,700 hypothetical date/horizon outcomes. Every unfiltered mechanism's
mean timing residual was negative at both horizons. For T1/T2 at 21 sessions,
event excess was -0.368% versus +0.519% for its matched asset/month controls:
residual -0.887 percentage points. The pullback/reclaim residual was closer to zero
(-0.226 percentage points) than the other unfiltered triggers.

This control is retrospective and descriptive: its monthly mean can include later
dates and the event itself, has thin months, and is not an independently tradable
strategy. No p-values or causal timing claim follow from it. It nevertheless warns
against attributing favorable stock/period selection to entry timing without a
proper comparator. The original primary report was not modified by this diagnostic.
See `timing_attribution.{json,md}` for every arm and the complete limitations.

The prefix audit also retained provisional observations rather than laundering
them into confirmed historical signals: 368 of 480 pooled T1/T2 events carried a
provisional flag at observation. T1/T2 and provisional strata are printed separately.
This experiment therefore must not be called a completed-higher-timeframe-only
signal study. A new confirmation-only experiment would need its own frozen protocol
and must respect the existing provisional-entry research, not be tuned from this table.

## First-principles synthesis after touching the actual evidence

The current evidence favors a research architecture, not a promoted rule:

1. **Selection asks why ownership should be rewarded.** Business expectations,
   valuation, catalysts or a well-defined flow mechanism must add information
   beyond the past-price transforms already in the timing signal.
2. **Timing asks when and at what price to express that thesis.** A cross can be
   a lagging confirmation, a useful repair signal or merely another correlated
   representation of the same price move. Compare simple alternatives and the
   cost of waiting instead of counting agreeing indicators.
3. **Context asks whether that particular mechanism should work now.** A universal
   bull/bear veto is not equivalent to mechanism-specific evidence. Trend,
   transition, stress and sector independence are different claims.
4. **Horizon, exits and execution determine what can be captured.** Keep entry
   experiments separate from exit experiments; compare net payoff and exposure,
   not win rate alone. Do not infer portfolio performance from overlapping trades.

The detailed, primary-source synthesis and falsifiers remain in
`ENTRY_REGIME_FIRST_PRINCIPLES_2026-11-14.md`. No LLM narrative, model complexity,
extra regime label or favorable secondary metric supplies missing empirical proof.

## Input defects and actual implementation delivered

The outcome-blind native-registry audit found 206,840 candidate rows but only 64
independent dates across five months. None of four examined native macro axes
meets the unchanged twelve-month-per-state floor; no native 21/63-session fold
qualifies on those candidate dates. This is different from the long price-only
pilot's historical dates. Do not combine the two histories and imply that all
fundamentals/context inputs existed throughout the price backtest.

A separate canonical membership bug was reproduced and repaired in PR #11242:
the PIT loader discarded index identity, allowing a requested sp500 population to
include sp400/sp600. Twelve new tests first yielded 9 failures; the corrected
grader/universe suites yield 179 passes/one optional-data skip, and nine real-source
consumer selections match exact group/tenure membership. Missing early small-cap
coverage is now unavailable rather than widened. This repair did not alter the
original pilot's immutable native source or its fixed survivor sample.

## What is and is not complete

Implemented and proven: fixed experiment protocol, causal-prefix adapters, immutable
source capture, common-coverage comparisons, uncertainty/cost/retention reporting,
readiness/estimability consumer, independent arithmetic readback, timing-attribution
control, first-principles synthesis and the separate population-correctness repair.
The owned research suite passes 79 tests. Aggregate evidence is durable and all
negative findings are retained.

Not established: a production-ready new alpha strategy, improvement on the actual
context-rich live board, complete historical economic inputs, out-of-sample
population-wide superiority, portfolio returns or live promotion. Exact-head
hosted checks, protected merge and their receipts are separate delivery evidence;
a Ready PR is not a merged release.

## Next evidence-bearing phase (not a threshold-retuning license)

Preserve the incumbent and all prior negative/frozen experiments. Qualify a broader
PIT population and actual source clocks through the existing owners before a new
confirmation or mechanism-specific interaction test. Separate unavailable histories
from measured neutral values; do not wait for an invented model to repair data.
Economic/event mechanisms need genuinely archived expectations/publication inputs;
PIT eligibility is necessary but not sufficient. Existing trial accounting, native
estimability and chronological floors, matched-risk controls, prospective confirmation
and earned-authority gates remain the path to a real production candidate.
