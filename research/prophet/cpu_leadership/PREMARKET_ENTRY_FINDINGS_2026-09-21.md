# CPU / memory: missed leadership and entry-path findings

## Mission and scope

Chairman: the September 21 premarket strength in AMD, Intel, Arm and Micron makes the earlier-entry failure urgent. The objective remains timely, evidence-grounded leadership discovery and valid entries, not a cosmetic Buy Now label or CPU-always-first rule.

Procedure: protected Mastermind `74b475545e179a3256bfebe6b5226f54231cf1cb`, skillpack 1.0.1. Implementation carrier remains macro #7572 / `sol/us-prophet-candidate-visibility-20260921`. Data/source observation: macro `090ea27e53b481285fd0ea00c8baae971cc00dc4`. This unit changes research/test code only. Live model, entry gates, sizing, archive writes and UI are untouched.

The new `entry_battery.py` executes the incumbent technical gate and existing Door-R re-arm construction on each day's own truncated price prefix, then retains actual published gates, pool membership, leader observations and recorded Door sightings as separate evidence. It does not create a detector, ranker, store, execution rule, live candidate or historical trade.

## Current market context, separately sourced

Reuters' September 21 global-markets report describes Intel up 5.4% and AMD/Micron around 2% in premarket trading. Those are reported snapshots, not synchronized executable quotes. A synchronized current Arm premarket quote was not independently verified. The dedicated quote read returned values matching the September 18 regular closes; those values were not relabeled as premarket moves.

Primary economics already deserve separate treatment from price: AMD's August 4 results explicitly describe accelerating EPYC demand, but its 107% Data Center growth combines EPYC CPUs and Instinct GPUs. That number cannot be used as CPU-only growth. Neither the market report nor these four motivating cases proves that every semiconductor subtheme has the same earnings exposure or an executable entry.

Sources:
- Reuters, September 21: https://www.reuters.com/world/china/global-markets-global-markets-2026-09-21/
- AMD, August 4: https://ir.amd.com/news-events/press-releases/detail/1295/amd-reports-second-quarter-2026-financial-results

## What the system actually recorded

All rows below come from the pinned repository artifacts. Source dates are deliberately not harmonized.

| Name | Recorded research sighting | September 18 published gate/pool | September 17 leader observation |
|---|---|---|---|
| AMD | Door T, September 18; semiconductor membership present, Quantum Computing chosen as primary | T1 eligible, ticks 1; sector-cap displacement, no final score | LEADER; RS126 percentile 98.70; last 52-week high 55 sessions ago |
| INTC | Door T, September 10; Semiconductors rank 1 | Ineligible, ticks 3 | NONE; RS126 percentile 98.13; high recency 61 fails the 60-session leg |
| ARM | No matching Door flag found at this pin | Ineligible, ticks 54 | NONE; RS126 percentile 96.94; high recency 62 fails the 60-session leg; prior episode ended at anchor-high reclaim |
| MU | Door T, September 10; Semiconductors rank 1, memory subtheme | Ineligible, ticks 1 | LEADER; RS126 percentile 97.76; high recency 58; prior episode recovered without reset |

Door T flags are research observations, not recommended entries or filled trades. Their stored event dates are available; this audit does not prove when every recorded flag was first published. The existing leader percentiles use their own 126-session cross-section, and must not be compared as the same score as the Door ledger's 63-session field.

**Ruling:** the hypothesis 'the system never detected any of these names' is too broad. There are antecedent Intel/Micron research sightings and an AMD eligible signal. The product still fails if detection does not become a visible, retained, correctly prioritized and executable opportunity. Arm also exposes a discovery/entry-family gap.

## Exact-prefix technical reconstruction

Window: September 8 through September 18, nine sessions, four motivating cases. Each evaluation gets only closes at or before its session. The existing `signal_gate.gate` is called with `washout_waiver=False`; current mutable contextual waiver evidence and historical event-latch state are not synthesized. The existing `prophet_doors.door_r_legs` is reused, including its completed-bucket guard.

| Name | Eligible sessions in this reconstruction | September 18 reason | Door R fires in the window |
|---|---|---|---|
| AMD | September 17 and 18 | Buy fired; forward confirmation pending | None |
| INTC | September 9 and 11 | Buy blocked: bearish divergence | None |
| ARM | None | Flat: sell | None |
| MU | September 9 | Forming master already topping; not a fresh entry | None |

All four have `above200=true` and `weekly_bull=false` at the September 18 technical cut. The re-arm construction requires the weekly condition plus its other legs. Its returned oscillator-leg false defaults are **not measured negative oscillator evidence** when the earlier structural check short-circuits. The battery retains the entire leg record so this distinction can be inspected.

The stored September 10 Intel/Micron sightings and the reconstructed September 10 gate disagree. Preserve both. Possible causes include source vintage, price basis, contextual inputs and event/bucket state; this unit has not identified which caused that difference. A replay from a later adjusted-history vintage is not a byte-exact recreation of a historical production run. No completed trade or capturable return is claimed.

## Accepted direction; rejected shortcut

The current source already contains `prophet_doors` T/R/W, a leader-pullback organ, an early-turn classifier, a candidate-episode owner and a miss-audit. Do not start another parallel detector/ledger/identity pipeline simply because these four names are missing from the main product.

The published leader organ's 60-session high-recency threshold is a pullback-construction criterion, not a complete definition of economic leadership. Intel and Arm can have high measured RS while that specific construction returns NONE. Leadership recognition must be a separate dimension from this entry-family permission. Raising the cutoff merely until the four names appear would not establish a better model.

Importantly, `research/PROPHET_US_TREND_INTELLIGENCE_MASTERPLAN_BY_FABLE.md` section 2.5 already reports the generic no-veto leader-reset construction as negative (938 overlapping fires, median 21-session excess -1.50%, per-name statistic -2.12%; exploratory, not a new result of this turn). That result is not erased by today's rally. The brief earlier intention to test that generic alternative is superseded by its existing adverse evidence: retain the incumbent safeguards and evaluate distinct, context-conditioned routing/entry hypotheses under the existing preregistration owners.

## Next model work, in implementation order

1. **Conversion/retention:** reconstruct the fate of the already-recorded Intel/Micron semiconductor sightings and AMD's eligible signal using the existing candidate-episode and plan owners. Preserve them as research opportunities through a continuing thesis while separately displaying the current executable condition. No claim that a shadow record already authorized a trade.
2. **Conditioned continuation:** compare the existing theme-relay and re-arm paths with a properly preregistered concentrated-leadership continuation treatment. Evaluate the weekly/old-high restrictions by family and context, not by removing them globally. The four motivating cases become required regression cases, not the validation sample.
3. **Full-cohort measurement:** use all eligible and rejected members, failed rallies, non-semiconductor controls and matched historical regimes. Separate detection delay, opportunity retention, false starts, executable entries, adverse excursion, transaction costs and missed-winner cost. Use the existing source/clock and archival owner #7180 for exact generation evidence; do not wait to investigate model mechanics, but do not promote performance claims from incomplete archives.
4. **Economic exposure:** preserve separate CPU, memory, packaging and GPU evidence, with dated issuer statements and contradictory supply/demand evidence through the incumbent theme-thesis owner. A generic semiconductor membership or LLM summary must not directly grant trade authority.

Source implementation of a new live entry family and its controlled activation remain uncompleted. The measurable capability delivered now is a reusable, source-bound, no-future-input entry-path acceptance battery, not a trading-model promotion.

## Verification

Eleven new tests first failed because the battery did not exist; all eleven then passed. The existing candidate and shadow-door suites jointly passed **281 tests, zero failures, zero skips**. The tests cover future-price mutation, exact session cut, invalid/Boolean prices, duplicate sessions, error-as-unknown, unchanged source inputs, shadow-versus-live separation and disabling mutable contextual waiver reconstruction.

The real CLI completed 36 per-session evaluations across the four cases and read the pinned board, published gates, leader artifact, Door ledger and four raw close files. Five listed core engine-owner files were checked against the source pin before execution. This is listed-core source identity, not a claim that an entire historical runtime/environment has been recreated.

A separate attempt to inspect the existing historical Door grading lane was blocked by the tool platform. It was not rerouted or retried; no new door-performance/gauntlet result is claimed. No independent worker or autonomous wake was started. No source/effect custody transferred.
