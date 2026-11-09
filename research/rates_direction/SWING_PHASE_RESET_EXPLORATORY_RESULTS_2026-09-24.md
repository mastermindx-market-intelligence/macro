# Phase/reset exploratory result: technical phase alone still does not earn prediction authority

## Finding

The Chairman's more specific "oscillator reset inside a broader yield trend" hypothesis
was tested after the default crossover study failed. On the same two-year ^TNX proxy,
the frozen phase/reset construction did not produce a promotable result.

This is intentionally a seen-history exploratory study: the source outcomes had already
been examined by the prior crossover program. A positive result could only have selected
a candidate for prospective shadowing. The negative result does not rewrite the prior
experiments and does not reject all possible rate-cycle models.

## Frozen construction and data

Freeze commit: 8e6936cfa4218188cb366c848b1fa83005af5b07
Freeze time: 2026-09-24T15:01:12.467332+00:00

Input: preserved Yahoo ^TNX two-year hourly capture, SHA256
1dc7e9121fd6aa36c5019beba303b629257eb1cab752ae937e4cef1aa8161b76.

The study reused the exact source/session parser and 12-completed-bar observed-session
first-passage target from the frozen crossover study. It added only the predeclared
phase geometry described in SWING_PHASE_RESET_EXPLORATORY_V1.md.

The primary discovery partition has 1,597 scored forecast origins over 401 source
dates. Outcome counts: 483 lower-first, 473 upper-first, 641 no-hit, and 4 ambiguous.
The same 1,597 scored origins are used for every Brier comparison.

## Baselines

Lower three-class Brier is better.

| Model | Brier | Relative to prior 5-bar trend/vol |
|---|---:|---:|
| Unconditional expanding frequencies | 0.674413 | - |
| Prior 5-bar trend + volatility | **0.665530** | reference |
| EMA20 broad-trend + volatility | 0.669350 | **-0.574%** |

The broader EMA20 phase baseline was worse than the simpler five-bar trend/volatility
baseline. That matters because any apparent phase-model gain versus the EMA20 baseline
must not be misreported as a gain versus the incumbent comparator.

## Indicator phase candidates

Relative improvement below is versus the EMA20 phase baseline, not the stronger
five-bar baseline.

| Candidate | Brier | Relative improvement | Active origins | Resolved non-overlap episodes | Directional successes |
|---|---:|---:|---:|---:|---:|
| M_EARLY | 0.672552 | -0.478% | 115 | 34 | 11 |
| P_RESET | 0.669024 | +0.049% | 39 | 21 | 7 |
| R_RESET | 0.669582 | -0.035% | 134 | 43 | 16 |
| PR_RESET | 0.669109 | +0.036% | 26 | 15 | 6 |
| MPR_RESET | 0.669448 | -0.015% | 4 | 2 | 0 |
| SHALLOW_PR | 0.669418 | -0.010% | 19 | 12 | 4 |
| SHALLOW_MPR, PRIMARY | 0.669350 | 0.000% | 3 | 1 | 0 |

No candidate reaches the predeclared 50-resolved-active-episode descriptive floor.
The primary is effectively inactive. P_RESET and PR_RESET show tiny positive changes
versus the weaker EMA20 baseline, but neither is adequate and neither beats the
stronger incumbent baseline.

Date-averaged HAC diagnostics do not support a benefit: P_RESET t=0.377, p=0.7058;
PR_RESET t=0.394, p=0.6936. M_EARLY is directionally worse (t=-1.785, p=0.0742).
These are descriptive, not selection-adjusted inference.

## Failure anatomy

The motivating "shallow reset continuation" idea is especially weak on the rising-yield
side in this sample. A post-result diagnostic found SHALLOW_PR active on 13 rising-trend
origins with only one upper-first outcome; the six falling-trend active origins had
four lower-first outcomes. This asymmetry is post-outcome and tiny-sample evidence.
It may motivate a future hypothesis, but it cannot be promoted or selectively rescued.

The larger lesson is more important: confirmed crosses failed, and the simple early
phase/reset geometry also failed to add useful probability information. The visual
wave pattern is real as a description of the transformed series, but these tests do
not show that the oscillator state alone reliably predicts the next material yield
move.

That shifts the next research priority toward state-conditioned macro catalysts and
rate-driver information: policy-path repricing, real-yield pressure, growth/inflation
surprises, event density, auctions/supply and cross-asset response. Oscillator phase
can remain an observed timing/context feature inside that model rather than becoming
the model itself.

## Integrity and authority

Execution evidence:
- predictions SHA256: 3fd548c20debb2caf20283bc0b5fff08a5bcd4cd03e5f76febf5aca0de86e22a
- summary SHA256: 95b57f6a04973b2ec7ef0b5ad4aeae759dbcb9ec768cf802855f0b99a745f98e
- registration SHA256: 33d12b6726ebfa9b13fb9e478924ae3ef47c3cd1d6c51849c4c12ca470b9d02e
- seven append-only configurations in family ric_swing_phase_reset_v1

Same-author verification recomputed every partition/model Brier, checked 1,870 unique
forecast origins, finite normalized probabilities, purged training clocks, the exact
pre-registration TrialLedger prefix and the seven-row family suffix. It is not an
independent review.

No native Pine/TVC parity, historical point-in-time qualification, production forecast,
equity-risk authority, rank, gate, size or trade authority is claimed.
