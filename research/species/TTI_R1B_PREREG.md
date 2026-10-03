# TTI R1-B preregistration — exhaustion/reclaim versus continuation

**Status: candidate preregistration; NOT REGISTERED; NOT RUN.**

This document freezes the next independent Terminal Tactical Intelligence question before any R1-B outcome column is opened. It is long-side only and uses the existing Live Entry Radar / Setup-Species / Evaluation ownership model. It creates no scanner, event store, lifecycle, scientific registry, order route, paid-provider dependency, or production authority.

## 1. Question and relation to R1-A

Primary question: after a liquid stock makes a meaningful fresh regular-session low, does **price exhaustion followed by a causal reclaim** identify more remaining 60-minute opportunity than comparable fresh-low episodes, while explicitly separating premature fade attempts from healthy downside continuation?

This is not an outcome-conditioned rescue of R1-A. The exhaustion/reclaim-versus-continuation design existed on Macro #7270 before R1-A outcomes. R1-A found that one strict AH→premarket persistence construction did not earn promotion; R1-B neither relaxes those thresholds nor adds options/news/regime filters to that study.

The primary selector is `EXHAUSTION_RECLAIM`. `CONTINUATION_RISK` is an opposing price-action control, not a long recommendation. No short/HOD symmetry is inferred; the top-side program requires a separate preregistration and must reconcile the existing `WS:TOP-ANATOMY` owner before creating any new top detector.

## 2. Fixed data population and evidence class

Universe: AMD, NVDA, MU, AVGO, QCOM, AAPL, JPM, XOM. QQQ is the benchmark. The study uses the exact already-captured Terminal D0 five-minute population, source hashes and session calendar qualified by Terminal dependency `c0f36cb16fadd190ad747fc47a28405d9ec0fca4`.

Window: 2025-06-16 through 2026-09-11. The early/late split (through 2026-07-10 versus from 2026-07-13) is a retrospective stability split only, not a claimed untouched holdout. Current-universe survivorship/composition limits remain explicit. INTC is not queried or inferred from this batch.

Admission is corrected-history exploratory only. Historical per-bar availability, exact live fills and contemporaneous NBBO are not proven. R1-B therefore cannot promote a production signal regardless of retrospective outcome.

Primary decisions use five-minute RTH bars only. The current Massive capability record establishes stock minute/second aggregate and trade/quote entitlement, and Radar already has a bounded minute-reader seam, but R1-B does **not** create or assume a durable one-minute archive. Minute data may later resolve specific ambiguous episodes only after the existing data owner qualifies its history/clock path.

The six-value chart projection does not preserve exact vendor VWAP/transaction-count detail. R1-B therefore makes no aggressor-flow, dealer-inventory, market-maker, insider or exact-trade-VWAP claim from OHLCV.

## 3. Session and decision clock

Only normal 09:30–16:00 ET sessions are eligible. Early-close sessions are retained in exclusion counts and never stretched to a normal-session clock.

Candidate decisions are evaluated every five minutes from 09:45 through 14:30 ET inclusive. At decision time `t`, the candidate bar is the bar that ended at `t`; no bar starting at or after `t` may affect candidate identity or its forming features.

All timestamps are derived from the accepted session calendar / UTC inversion. Machine-local timezone and file order are never the session clock.

A candidate, confirmation or entry bar must exist exactly once and have finite positive OHLC values. Candidate/confirmation evidence requires positive reported volume. Missing, duplicate, malformed, wrong-basis or otherwise invalid observations yield explicit unavailable/censored states, never a negative signal.

## 4. Prior-only normalizations

`A(t)` is prior-session ATR20 built only from complete regular sessions ending before the current session. A missing/non-positive ATR makes the candidate unavailable.

Beta is covariance(stock, QQQ)/variance(QQQ) over up to 60 paired prior scheduled-session close-to-close returns with at least 40 valid pairs, clipped to [0,3]. No current-session return enters beta.

Previous regular close, ATR20, beta and any market context used at decision time must all be knowable before the candidate bar. Current-day final high/low/close are forbidden predictors.

## 5. Base fresh-low episode

Let `Lpre(t)` be the minimum low of all completed RTH bars strictly before the candidate bar. The candidate bar is a **fresh low** only when its low `L(t)` is strictly below `Lpre(t)`.

The base episode additionally requires:

1. `(previous_RTH_close - L(t)) / ATR20 >= 0.50`.
2. The trailing three completed five-minute bars including the candidate show `(open_of_oldest_trailing_bar - L(t)) / ATR20 >= 0.20`.
3. Candidate volume is positive.
4. The decision is inside the frozen clock window and all prior-only normalizations are available.

The strict new-low comparison never uses a centered pivot or a later bar. Equal lows do not start a fresh-low episode.

`BASE_FRESH_LOW` fires at candidate decision time. Its price-reference entry is the exact next five-minute bar open (the same instant as candidate-bar completion), labeled a price reference rather than a guaranteed fill.

## 6. Forming exhaustion geometry

For a valid fresh-low candidate with non-zero range:

`close_location = (close - low) / (high - low)`.

`fresh_low_extension_atr = (Lpre(t) - L(t)) / ATR20`.

`EXHAUSTION_FORMING` requires `close_location >= 0.60` and `fresh_low_extension_atr <= 0.15`, in addition to the base episode. This is an interpretable OHLCV exhaustion proxy: it says downside progress beyond the prior running low was modest and the completed bar closed materially off its low. It does **not** prove buyer exhaustion, seller exhaustion, absorption, order-flow direction or final LOD.

The forming event is measured from the next-bar price reference even if it later fails. Failed forming calls remain in the denominator.

## 7. Confirmation race: reclaim versus continuation

For every base candidate freeze two levels at candidate time:

- reclaim level = `Lpre(t)`, the running session low that the candidate broke;
- continuation level = `L(t) - 0.25 * ATR20`.

Inspect at most the next three **completed** five-minute bars in chronological order. On each completed bar:

- **RECLAIM** when close is strictly above the frozen reclaim level;
- **CONTINUATION** when close is at or below the frozen continuation level;
- otherwise remain unresolved.

These close-based conditions are mutually exclusive on a bar. The first one observed wins. If neither occurs within three bars, the candidate expires. No threshold is moved after the candidate forms.

`RECLAIM_ONLY` is the first base candidate per symbol/session whose confirmation race ends in RECLAIM.

`EXHAUSTION_RECLAIM` is the first `EXHAUSTION_FORMING` candidate per symbol/session whose confirmation race ends in RECLAIM.

`CONTINUATION_RISK` is the first base candidate per symbol/session whose race ends in CONTINUATION before a reclaim. It exists to identify the precise environment where buying a fresh low was premature; it is not trade authority.

Confirmed-family price-reference entry is the exact next five-minute bar open after the confirming bar. Confirmation delay in bars/minutes is preserved. No event is backpainted onto the candidate extreme.

Each selector emits at most its first qualifying event per symbol/session. Different selectors may reference the same candidate anchor; dependence is handled at the date/episode level rather than pretending those rows are independent trades. Re-entry is disabled in R1-B.

## 8. Outcome families

Frozen horizons are 30 minutes, 60 minutes, 120 minutes and scheduled RTH close. An outcome is available only when the exact entry bar and every nominal five-minute bar through the endpoint exist and validate. A later observed bar never substitutes for a missing endpoint. Late candidates that cannot supply a full 120-minute path are censored for that horizon, not dropped from the fire count.

For every available horizon report:

- raw stock return from the price-reference entry open;
- net return after 10/25/50 bp round-trip cost sensitivities;
- QQQ return over the same timestamps;
- prior-beta residual return and cost-adjusted beta residual;
- MFE and MAE from post-entry RTH highs/lows;
- candidate-to-entry confirmation delay cost `(entry_open - candidate_low)/ATR20`;
- remaining distance to previous RTH close `(previous_close - entry_open)/ATR20`.

The fixed 10/25/50 bp costs are early-stage sensitivities, not measured NBBO. Any later Radar promotion must use the existing canonical measured-spread/liquidity-floor cost law rather than treating these sensitivities as execution proof.

## 9. Local reversal and LOD diagnostics

For each horizon define target = `entry + 0.50*ATR20` and adverse = `entry - 0.50*ATR20`. Record target-first, adverse-first, neither, censored, and same-five-minute-bar ambiguous. Same-bar ambiguity is never resolved optimistically from OHLC.

Minute evidence, if later qualified by the existing data owner, may resolve a specifically enumerated ambiguous episode without changing the five-minute candidate/confirmation identity. No new minute archive or alternate research store is authorized by this preregistration.

Candidate LOD survival is a separate diagnostic: no subsequent eligible RTH low may be strictly below the frozen candidate low through scheduled close. A profitable local bounce may still fail LOD survival, and a final LOD may still offer poor entry quality. These labels are never collapsed into one success boolean.

## 10. Deterministic matched controls

The primary comparison is not an unconditional hit rate. For each selected event, build a BASE_FRESH_LOW control pool **without using outcomes**.

A control must have the same ticker, the same early/late retrospective partition, the same 30-minute decision-time bin, the same displacement bucket `[0.50,0.75), [0.75,1.00), [1.00,1.50), [1.50,+inf)`, the same sign of QQQ open-to-decision return, and the same confirmation-delay bar count used by the selected event. The selected date itself is excluded.

For a confirmed selector with delay `d` bars, the matched base control is measured from the base candidate shifted by the same `d` completed bars before taking the next-bar entry reference. This prevents a confirmed family from being compared with an artificially earlier baseline entry.

If fewer than 10 matched controls exist, the selected event is marked `no_control`. There is no fallback to a wider bucket, another ticker, another partition or an outcome-selected neighbor.

The primary event delta is selected 60-minute net beta-residual return at 25 bp minus the mean of its lawful matched-control returns. Primary study effect is the mean of event deltas after first averaging selected events within each calendar date.

Report unmatched counts and overlap explicitly. A matched observational comparison measures enrichment conditional on these frozen covariates; it is not a randomized causal treatment estimate.

## 11. Trial family and full grid

Registered selector grid: BASE_FRESH_LOW, EXHAUSTION_FORMING, RECLAIM_ONLY, EXHAUSTION_RECLAIM, CONTINUATION_RISK × 30m/60m/120m/close × 10/25/50 bp = **60 cells**.

All 60 cells must be appended to the existing `entry_radar` TrialLedger before any R1-B outcome computation. No new trial family, subfamily, registry or replay authority is created. Registration cannot occur while the shared R1-A TrialLedger carrier is unresolved; prereg/config may be frozen on this docs-only branch first.

The full grid, including negative, empty, censored and no-control cells, is reported. No post-outcome threshold relaxation, selector addition, ticker-specific threshold, news filter, regime filter, sector filter or options witness may be inserted into R1-B.

## 12. Uncertainty and concentration

For the primary matched deltas, average within calendar date first so correlated names on the same market shock do not masquerade as independent observations. Resample calendar-week blocks with 4,000 bootstrap replicates, seed 20260917, and report the 95% percentile interval.

Report fire count, distinct dates, ticker coverage, per-ticker sign, early/late partition sign, single-ticker fire concentration, time-bin concentration, no-control fraction, censoring and ambiguous-touch counts.

R1-B does not claim promotion-grade p-values, Sharpe, DSR or calibrated probabilities. The Setup-Species registry is not transitioned by this batch.

## 13. Frozen prospective-candidate gate

Only `EXHAUSTION_RECLAIM` is eligible to advance to a **separate prospective/shadow preregistration**, and only if all hold:

- at least 300 eligible fires, 100 distinct dates and 6 tickers;
- primary 60-minute/25 bp matched-delta 95% interval lower bound is above zero;
- early and late retrospective partition primary deltas have the same sign;
- no single ticker contributes more than 35% of fires;
- source/missingness checks reveal no systematic admission artifact that explains the result.

Passing this gate still grants no live rank, alert, sizing or trade authority. Failing it rejects or demotes only this exact construction. `RECLAIM_ONLY`, `EXHAUSTION_FORMING` and `CONTINUATION_RISK` remain comparators/context unless a later independent preregistration says otherwise.

## 14. Leak and mutation tests required before outcome execution

Implementation tests must prove that changing any future bar after candidate decision cannot alter candidate identity or forming features; changing bars after confirmation cannot move the confirmation timestamp earlier; a future duplicate/corrupt row cannot erase an earlier lawful candidate; and a missing/corrupt outcome bar censors only that outcome rather than deleting the fire.

Tests must also prove strict-low equality does not fire, zero-range/zero-volume candidate refusal, exact three-bar race expiry, no reclaim after continuation invalidation, no lookahead in ATR/beta/QQQ context, exact matched-control delay, no fallback below the 10-row control floor, and same-bar target/adverse ambiguity.

## 15. Product and ownership boundary

R1-B is research evidence for the approved Terminal opportunity workflow. It does not mint a new `mastermind.entry_event.v1` family. Existing C1/C2 Radar detectors remain separate 1D-live oscillator mechanisms; R1-B must not rewrite their specs, event identities or episode lifecycle. R1-B also does not consume C4 higher-timeframe washout depth as arming authority, preserving `DNR:KILL-WASHOUT-TURN`.

If R1-B later earns prospective evidence, the Live Entry Radar owner decides the versioned event integration. Terminal remains a consumer and should eventually display candidate time, confirmation time, entry reference, invalidation, continuation evidence, remaining target space, contradictory evidence, data freshness and calibration status. No backpainted bottom marker or opaque probability is authorized.

AH/PM context is not a gating feature in R1-B. R1-A already tested one frozen extended-hours construction. Any interaction between R1-B and overnight/premarket state requires a new registered experiment rather than a post-hoc rescue.

Options flow/packages/positioning and 0DTE expressions remain separate later witnesses. An underlying local-turn result cannot establish contract profitability.

## 16. Publication and stop condition

Before any empirical run: commit this preregistration and `tti_r1b/config.json`; record exact hashes; reconcile R1-A/shared TrialLedger state; then append the complete 60-cell budget through the canonical TrialLedger writer.

After execution: publish aggregate methods/results, hashes, complete cell table, failure/censor counts, leak audit and an explicit no-promotion or prospective-candidate disposition. Raw licensed bars remain outside Git.

The correct stop for this prereg carrier is **frozen design, no outcomes**. Empirical implementation begins only after the shared R1-A source/TrialLedger gate is reconciled on its existing carrier.
