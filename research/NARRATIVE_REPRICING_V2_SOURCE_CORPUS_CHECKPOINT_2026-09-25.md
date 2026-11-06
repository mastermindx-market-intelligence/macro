# Narrative Repricing V2 — Source Corpus Checkpoint

Date: 2026-09-25
State: SOURCE_CORPUS_MILESTONE / RESEARCH_ONLY / NOT OUTCOME COMPLETION
Operation: geopolitical-relief-event-study-20260924-sol-001
Carrier: Macro PR #8012 / sol/geopolitical-relief-event-study-20260924
Checkpoint head before this artifact: 4df49a3625b6e40af9160378c9a58d81ff06b6d8

## 1. The milestone

The research now has 20 clock-tracked independent event clusters across the frozen
source-only waves plus clock-clean inspected development pilots.

That is a source-corpus milestone only.

It does NOT mean:
- 20 events have complete intraday outcomes;
- 20 events support the hypothesis;
- a threshold/model is fitted;
- a holdout has been opened;
- alpha exists;
- a product, alert, ranking, portfolio or execution path is accepted.

## 2. Corpus accounting

Frozen source-only rows:

- Wave 1: 10 clusters
  - 9 primary training events
  - 1 explicit weak/denial control
- Wave 2: 3 clusters
  - 2 official confirmation / execution-detail events
  - 1 weak mediation control
- Wave 3: 5 clusters
  - escalation, weak-rumor and mixed/conflict controls

Source-only subtotal: **18 clusters**.

Clock-clean inspected development pilots that are not unseen evidence:

- 2026-09-14 — step-by-step U.S.-Iran agreement report, exact Newsquawk live-feed clock
- 2026-09-24 — phased Hormuz/blockade relief report, earliest recovered market-distribution clock

Inspected-pilot subtotal: **2 clusters**.

Clock-tracked corpus total: **20 clusters**.

The contaminated July 20 late-republication replay and the earlier September 22 20:34/20:35
exploratory replay are not counted toward this milestone because their source clocks were not
clean enough for primary inference.

## 3. Family distribution

Across the 20 counted clusters:

- iran_oman_hormuz_navigation: 8
- us_iran_hormuz_deescalation: 5
- us_iran_diplomatic_reengagement: 2
- us_iran_hormuz_escalation: 2
- us_iran_ceasefire_mediation: 1
- iran_hormuz_restriction_rhetoric: 1
- us_iran_ceasefire_rumor: 1

This is still heavily concentrated in one geopolitical complex. The V2 preregistration's
preference for multiple narrative subfamilies is therefore only partially satisfied.

## 4. Outcome accounting

Wave 1 primary training events:

- complete +5→+35 SMH-vs-QQQ outcome: 5
- market-closed / response-tape / event-clock data gap: 4

Wave 1 explicit denial/conflict control:
- complete +5→+35 outcome: 1

Wave 2:
- source clocks frozen: 3
- outcomes inspected after freeze: **0**

Wave 3:
- source clocks frozen: 5
- outcomes inspected after freeze: **0**
- one row (July 14) is already source-confounded by an opposite geopolitical headline ten
  minutes later and is retained as a mixed control rather than a clean primary event.

Sep 14 and Sep 24:
- inspected development diagnostics, not unseen holdout.

Therefore the current research does NOT have 20 independent outcome observations. The
minimum complete-sample acceptance language remains unmet.

## 5. Missingness and session structure

The clock-clean corpus has already shown that event timing is not a nuisance variable:

- Sunday events can have no U.S.-ETF tape at the event clock.
- Very early UTC headlines can precede U.S. extended-hours liquidity.
- Some response ETFs are sparse even when USO/QQQ print.
- Opposite geopolitical headlines can arrive inside the same 30-35 minute outcome window.

Those rows must remain missing/confounded under the intraday V2 design. They may not be
shifted to a later liquid bar or next U.S. open to manufacture completeness.

This directly motivates a separate cross-session handoff study rather than contaminating the
same-session +5 design.

## 6. Current evidentiary state

What is already falsified:

- a simple oil-first / semis-later minute lead-lag on Sep 24;
- "credible relief + oil confirmation" as a sufficient semiconductor continuation rule;
- "pre-event oil strength + relief-direction reversal" as a sufficient continuation rule in
  the small Wave 1 training slice;
- "buy the most damaged semiconductor names" as a simple monotonic rule.

What remains legitimately open:

- source novelty / resolution-stage interactions;
- physical-channel specificity;
- source corroboration and conflict state;
- synchronized first-impulse breadth;
- volatility-normalized causal reversal;
- competing semiconductor / China / macro catalysts;
- session-handoff effects;
- whether a broader narrative family generalizes beyond the U.S.-Iran/Hormuz complex.

## 7. Holdout law

The prospective holdout remains empty/uninspected under
research/NARRATIVE_REPRICING_V2_EVALUATION_SPLIT_2026-09-25.json.

The 20-cluster source-corpus milestone grants no permission to open it.

Before holdout:
1. finish training/development feature definitions;
2. preserve exact source clocks and confounders;
3. obtain enough complete outcome rows for a meaningful development pass;
4. freeze the selected feature/threshold/model family;
5. only then admit future post-cutoff eligible events to the prospective holdout.

## 8. Exact continuation

- register a separate cross-session handoff preregistration for market-closed source events;
- expand source families beyond Hormuz where an economically explicit causal channel exists;
- keep Wave 2 and Wave 3 outcomes unscored until the existing outcome-access lane is lawfully
  available again;
- add first-impulse breadth and volatility-normalized causal features to the pure calculator;
- update the PR only with verified receipts, never with source-count language that implies
  statistical acceptance.
