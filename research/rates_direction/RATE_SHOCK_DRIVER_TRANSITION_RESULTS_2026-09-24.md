# Rate-shock driver transition v1 — result: composition did not improve the recent transition forecast

## Finding

A large five-session 10-year Treasury impulse was not made more forecastable by the
predeclared real-vs-breakeven decomposition, PIT Kim-Wright term-premium state,
credit/oil/curve state, or recent Treasury-auction absorption context.

The primary 2022-2025 sample met the declared 50-event descriptive floor. Every
layer beyond impulse direction worsened the three-class Brier score. This exact
construction is not promoted.

This does NOT establish that real yields, term premium, auctions or cross-assets are
economically irrelevant. It says that discretizing their recent states this way did
not improve the probability of continuation/reversal/no-hit after an already-large
five-session 10Y move.

## Frozen construction

Freeze commit: cc3b56c1e5c30d1a323f114d460a20315003c599
Freeze time: 2026-09-24T15:14:13.304403+00:00

The study:
- identified a non-overlapping event only when the absolute five-session DGS10 move
  crossed max(15bp, the prior-252-observation 80th percentile);
- made the current observation unable to set its own threshold by shifting the
  rolling percentile one row;
- started the outcome at t+1 and looked ten business observations forward;
- used a symmetric max(10bp, 20-session yield-volatility * sqrt(5)) barrier;
- classified the outcome as continuation, reversal or no-hit;
- used release-basis ALFRED availability for Kim-Wright THREEFYTP10;
- kept rolling policy futures out because their current six-month history is
  contract-roll contaminated until RD2 qualifies constituent repricing;
- stopped the retrospective sample at 2025-12-31, excluding the motivating
  September 2026 event.

The study is retrospective seen-history research. Market-source correction vintages
for the ordinary rate/OAS/oil proxies are not preserved in this construction.

## Primary result: 2022-2025

57 scored non-overlapping forecast events met the >=50 primary floor.

Outcomes:
- continuation: 24
- reversal: 22
- no-hit: 11

Driver-state mix:
- REAL: 45
- MIXED: 9
- INFLATION: 3
- CONFLICT: 0

Lower Brier is better.

| Model | Brier | Relative vs impulse-direction baseline |
|---|---:|---:|
| Unconditional | 0.666119 | -0.153% |
| Impulse direction | **0.665101** | reference |
| + nominal/real/breakeven decomposition | 0.672208 | **-1.068%** |
| + PIT term-premium state (PRIMARY) | 0.682122 | **-2.559%** |
| + credit/oil/curve state | 0.691956 | **-4.038%** |
| + recent auction state | 0.700381 | **-5.304%** |

The primary decomp+term model therefore failed its frozen hurdle: it was worse than
the impulse-direction baseline by 2.559% on Brier. Additional cross-asset and auction
conditioning degraded the score further.

Direction diagnostics are also not a rescue:
- recent upward impulses: 28 forecasts; direction baseline 0.659507 versus
  decomp+term 0.674052;
- recent downward impulses: 29 forecasts; direction baseline 0.670503 versus
  decomp+term 0.689915.

These direction splits are post-result diagnostics, not independently registered
hypotheses.

## Earlier partition is not evidence of a regime edge

The 2017-2021 development partition has only TWO forecast events after the
30-event training warm-up. Its numerically lower driver-model Brier is therefore
underpowered and must not be described as a successful pre-2022 regime.

A later post-result diagnostic split showed 2022-2023 was closer to flat while
2024-2025 degraded more strongly as hierarchy depth increased. That observation may
motivate future work but is not a selected regime rule.

## What this rules out and what it does not

Rejected for promotion:
- "real-led shock => continuation/reversal" as a direct categorical rule;
- PIT term-premium confirmation as an automatic next-move edge;
- stacking credit, oil, curve and auction labels as more independent confirmation.

Still unresolved:
- whether the *catalyst surprise itself* can be forecast before a release;
- whether genuine constituent-level Fed-path repricing improves the state once RD2
  removes rolling-contract effects;
- whether event-specific intraday response after a known catalyst can identify
  continuation earlier than daily data;
- whether oscillator phase adds timing value only conditional on a validated catalyst
  state.

This result strengthens the case for separating vulnerability, catalyst and response:
the pre-shock state can explain why rates are fragile without predicting the sign of
the next surprise.

## Integrity and authority

Same-author verification:
- 89 non-overlapping shock events;
- 59 forecast rows after warm-up;
- 57 primary scored events;
- all forecast origins unique;
- every training outcome ended before its forecast origin;
- all class probabilities finite, positive and normalized;
- every partition/model Brier recomputed exactly;
- pre-registration TrialLedger prefix preserved;
- exactly five appended family configurations in
  ric_rate_shock_driver_transition_v1.

Evidence hashes:
- registration: 44b95cccccbf8f3c4cdf90c2b07b39fb7937ab8cadfc6718b53fe6cb2460e1d5
- events: e438f628b9013467af1129731fe11980982dca091ee48b3174da2da208c324c2
- predictions: 6ba88d1e39c5bd281ceb24d59f8fa57368a0a4c13c7a6213f2586bbcc669052b
- summary: e1eab40ca21d956bd2e39ca28f583c1c9bd50a69234c7684e6f25df9acc24b3a

This is same-author verification, not independent statistical review. No production
forecast, alert, rank, size, gate, trade or equity-risk authority is created.
