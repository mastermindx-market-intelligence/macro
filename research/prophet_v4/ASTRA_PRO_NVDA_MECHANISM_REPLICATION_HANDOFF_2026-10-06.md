# Astra Pro Research Commission — Prophet Golden-Case Mechanism Replication

**Date:** 2026-10-06  
**Mission type:** deep research / forensic evaluation / architecture recommendation  
**Implementation authority:** NONE unless separately granted by the Chairman.  
**Trading authority:** NONE.  
**Canonical research carrier:** macro draft PR #8495, branch `sol/prophet-nvda-conversion-audit-20261006`  
**Parent research head immediately before this handoff commit:** `b31dd90bca1709afcc972f9a19d19361e64e1dbd`  
**Primary source pin used by the prior census:** `macro@2f2feec4851b45636f63a48ec61e6f0b02b8118a`

## Commission

Lead the next research phase on the September 2026 NVDA Prophet golden case.

Do **not** begin by redoing the completed census. Read the two research artifacts on PR #8495 first:

1. `research/prophet_v4/PROPHET_NVDA_CONVERSION_CAUSALITY_AUDIT_2026-10-06.md`
2. `research/prophet_v4/PROPHET_NVDA_MECHANISM_EXTRACTION_2026-10-06.md`

Treat their accepted measurements as the current frontier unless you find contradictory primary evidence.

Your job is to determine how much of the NVDA success is a reproducible mechanism, what parts are merely correlated context, how to increase both early winner recall and decision precision without overfitting the golden case, and how this should change the Prophet roadmap.

### Chairman refinement — do not treat older eras or `news_burst` as cleanly comparable by default

The Chairman added four material hypotheses after the first census. Treat these as **research priors to adjudicate**, not conclusions to assume:

1. **July confluence-era intelligence maturity may be materially lower than v3.** Repository history shows major intelligence substrate was still being built during July:
   - 2026-07-07: stock flow-to-price / 13F + short-flow work (#1833);
   - 2026-07-10: verified smart-money roster/backfill (#2191) and Ownership Intelligence Desk (#2192);
   - 2026-07-10: narrative-flare witness engine (#2147);
   - 2026-07-30: Intelligence Desk V2 (#4006).
   Therefore an unchanged `T2 + news_burst` cross-era comparison may mix **feature semantics / coverage / maturity drift** with true predictive drift.

2. **June–July 2026 was a materially different semiconductor/AI-hardware regime.** Do not call it a broad-market crash without evidence. External and internal market data should adjudicate whether the correct label is semiconductor correction, AI-capex/growth scare, rate-pressure rotation, value-over-growth rotation, or some combination. The observed July selloff in semiconductors/memory makes regime comparability a first-class question.

3. **Yesterday's Trend Persistence study returned C1-NULL, but its null is construction-scoped.** Canonical result: `Mastermind@7eac3ec252475600147ec9a376b8ca16403ac4c5`, `research/data/trend_persistence_c1_result.json`. It closes only the tested eleven-GICS-sector, 20/60-session, rank-linear construction with as-of-now / non-era-correct labels and a survivor-tilted labelled universe. Its own wording says GICS industry-group/industry, basket and dynamic-theme constructions remain untested. Do not interpret this as “leadership persistence does not exist.”

4. **`news_burst` is probably a proxy for information arrival / rerating, not the complete causal class.** Important reratings can occur without a ticker-specific news burst: earnings/guidance, analyst estimate or target revisions, peer read-through, sector-wide pricing/capacity changes, hyperscaler capex, supply-demand/inventory evidence, contracts/policy, smart-money/flow, or theme/regime rotation may be the true rerating driver.

The revised commission must therefore search for the stable **rerating-conditioned ignition mechanism**, not optimize a literal `T2 && news_burst` rule.

## Established facts — do not waste the run rediscovering them

### NVDA decision transition

The critical transition occurred from Sep-24 to Sep-25 while price barely moved:

- price: ~$224.58 -> ~$225.07;
- lane: watch -> buy;
- state: TOP WATCH / NEARING A HIGH -> TURN SIGNALED / BOTTOMING;
- signal: provisional T3 -> confirmed T2;
- entry status: extended -> partial;
- act level: 0 -> 3;
- entry z: -32.3 -> +64.2;
- conviction/potential: 4 / low -> 51 / constructive;
- cycle blocked true -> false.

The name-score event/edge substrate barely changed. The potential-score trigger was the load-bearing numerical change: effective trigger ~0.075 -> 0.92.

T3 itself was already an admissible tier. The plan became possible because the conviction and entry-status gates changed together.

### Exact Sep-25 C1 attribution

NVDA was rank #1, C1 score 80.5.

Active family contributions:

- F1 Technical Confluence: 71.59
- F2 Momentum / Extension: 68.84
- F4 Catalyst / Event: 93.48
- F5 Flow / Positioning: 69.93
- F8 Attention / Crowding: 98.55

F3 Theme, F6 Macro and F7 Quality/Fundamental abstained from the canonical C1 rank.

Member percentiles include:

- tier_cascade 0.715909
- alpha 0.434783
- off_high 0.942029
- sue_fresh 0.934783
- insider_cluster 0.463768
- smartmoney_add 0.934783
- news_burst 0.985507

Legacy v2 shadow rank was #4.

Leave-one-family-out keeps NVDA #1 no matter which one of the five families is removed. Dropping two or three families still keeps it within the top five. This is an overdetermined multi-family rank case.

### Generic simplifications are falsified

Do not propose:

- “T2 is the secret”;
- “T3->T2 is the secret”;
- “partial is the secret”;
- “near-high RS is the secret”;
- “rank #1 is the secret.”

The existing matured cohorts do not support those claims.

### Discovered interaction

In the matured `us_prophet_v3` 5-session board history:

- all buy rows: n=1,098, 34.2% positive excess vs SPY, mean -1.08%;
- T2: n=327, 37.9%, mean -0.57%;
- news burst any tier: n=18, 66.7%;
- non-T2 + news: n=7, 28.6%, mean -7.24%;
- **T2 + news: n=11, 10/11 = 90.9%, mean +3.58%;**
- T2 + news + smartmoney-add: n=7, 7/7 positive, mean +3.70%.

T2+news vs T2/no-news Fisher OR ~17.7, one-sided p ~0.00036.

Collapse to first call per ticker: 6/7 positive, mean +3.82%.

Leave-one-ticker/date tests stay roughly 86–100% positive.

Same-date T2/no-news controls were worse on every observed date-level comparison; average date-level mean-excess advantage ~+5.8pp at H=5.

The effect weakens at H=10 and is not mature at H=21.

### Critical caveats

- The interaction was selected after seeing NVDA. It is discovery, not preregistered confirmation.
- The 11 measured v3 rows all predate NVDA's Sep-25 signal (Aug-21 through Sep-17), so NVDA is a later temporal corroboration but not a lawful independent holdout.
- The unchanged T2+news screen fails to replicate uniformly in older product eras. July confluence-era H=5 was 1/5 positive. v1 was 2/3. v3 was 10/11.
- The registered Conditional Fusion fold law is still unsatisfied: current board ledger has 48 distinct dates, versus roughly 111 needed for 3 folds with min 60 train / 10 test and a 21-session embargo. Current usable folds: zero.
- Do not weaken the fold law to obtain a fitted result.

## Central hypotheses to adjudicate

### H1 — linked mechanism

The NVDA win is caused by a sequence:

```
high-value opportunity substrate
    -> timing/cycle unlock
    -> admission gates clear
    -> interaction-rich catalyst/attention confirmation
    -> family fusion prioritizes the name
    -> deterministic entry geometry controls chase risk
```

Determine which edges in that sequence are necessary, sufficient, merely amplifying, or incidental.

### H2 — rerating-conditioned ignition interaction

In the current v3 population, fresh technical confirmation appears to have much higher immediate follow-through when accompanied by a fresh **rerating / information-arrival event**.

`T2 AND news_burst` is only the discovery seed. Do not make “news” the ontology.

Construct and compare a point-in-time rerating taxonomy, including where lawful:

- earnings surprise / post-earnings drift;
- guidance raise/cut or KPI inflection;
- analyst estimate revisions / target changes / upgrade clusters;
- peer earnings or customer/supplier read-through;
- sector pricing, capacity, inventory, utilization or supply-demand changes;
- hyperscaler / major-customer capex or procurement signals;
- government contracts / policy / regulatory change;
- smart-money / ownership / positioning change where the clock is lawful;
- options/flow as confirmer, never source of a fabricated event;
- theme/sector breadth and relative-strength rerating;
- technical reacceleration with **no identifiable discrete information event**;
- ordinary ticker-level `news_burst`.

Ask whether the stable construct is **technical confirmation × rerating arrival**, and whether event species determines the horizon.

Candidate interactions include:

- F1 technical × F8 attention;
- F1 × F4 catalyst;
- F1 × F4 × F8;
- F1 × F8 × F5 flow;
- technical transition × revision acceleration;
- technical transition × sector/theme rerating;
- technical transition × peer read-through;
- state transition × any new independent evidence family;
- an interaction that is positive pre-extension but becomes negative crowding after extension.

The goal is a causal/typed mechanism, not an ever-growing additive catalyst score.

### H3 — separate ignition and durability; persistence remains open after C1-NULL

The discovered interaction may predict 3–10 session ignition but not 21–63 session leadership persistence.

Yesterday's Trend Persistence C1-NULL is a **negative control for one persistence construction**, not a veto on this head. It failed to show incremental persistence for the tested eleven-sector rank-linear feature family after controlling for member trailing return/volatility. It did **not** test the same object Prophet needs here.

Test whether Prophet needs separate heads:

- **emergence / research attention** — “this opportunity is becoming unusually important”;
- **ignition / follow-through** — “a rerating is being accepted now”;
- **leadership persistence / durability** — “this ignition is likely to remain a leader rather than mean-revert”;
- **deterministic Entry Availability** — “entry is/is not open at this price and strategy.”

For the durability head, explicitly test constructions left open by C1-NULL:

- stock-level persistence conditional on a known ignition episode;
- industry-group / industry persistence;
- basket / dynamic-theme persistence;
- leader retention and RS persistence **after** the rerating cut;
- revision/catalyst persistence;
- breadth and participation persistence;
- relative-strength depth and dip-recovery behavior;
- survival/hazard framing: continue leadership vs stall vs breakdown/mean reversion.

Do not simply rerun the failed eleven-sector C1 model under a new name.

### H4 — recall bottleneck is upstream of the board

Many historical T2+news winners had no published board row on the prior session.

Test whether the correct earlier-detection surface is the full candidate / candidate-episode plane rather than a relaxed action board.

## Required work

### 1. Reproduce the exact NVDA decision graph

Independently verify the Sep-24 and Sep-25 source snapshots and code path.

Produce a causal graph separating:

- source observations;
- derived states;
- gates;
- ranking-only fields;
- display-only fields;
- plan-admission fields;
- execution geometry.

For every edge, name whether it could have changed the existence of the plan, its rank, its entry state, or only its narrative.

### 2. Explain the era split as two separate problems: data-plane maturity and market regime

The T2+news interaction is strong in v3 and weak in the July confluence era. Do **not** read that immediately as predictive non-replication.

#### 2A. Intelligence-data-plane maturity audit

Build an era-by-era matrix for every evidence leg used in the comparison:

- producer existed yet?;
- historical depth actually available?;
- PIT/availability semantics?;
- serving coverage?;
- cross-sectional variation?;
- stale/snapshot/forward-only state?;
- same definition as v3 or changed semantics?;
- whether the feature was actually consumed by Prophet at that time.

At minimum audit `news_burst`, attention, smart-money/13F, SUE/catalyst, analyst revisions, options/flow, theme evidence and the candidate universe.

Explicitly determine whether July has a **measurement-comparability failure**. If a v3 feature did not exist, was sparse, had different semantics, or had materially weaker source coverage, the cross-era outcome is “not comparable on this dimension,” not “the mechanism failed.”

#### 2B. Market-regime comparability audit

Independently reconstruct June–July vs August–September regime using PIT market data.

At minimum measure:

- SOX/SMH and memory-relative drawdown;
- SPY/QQQ and equal-weight market behavior;
- growth-vs-value rotation;
- rates / rate pressure;
- volatility;
- semiconductor breadth;
- AI-hardware vs software dispersion;
- memory / equipment / designers separately;
- market-wide vs sector-specific stress.

Adjudicate whether July was a semiconductor/AI-hardware correction, capex/growth scare, rate-pressure rotation, broad-market risk-off, or a mixture.

Then test the interaction **within comparable regimes and comparable data-plane eras**.

Other differences to preserve:

- changed candidate populations;
- changed entry semantics;
- different signal-tier construction;
- survivor/selection effects;
- true context dependence.

Do not pool incompatible eras to make the effect look stable or unstable.

### 3. Build a PIT-safe rerating-event ontology and episode study

Before modeling outcomes, define the event species available at the decision cut.

For every candidate episode, distinguish:

- no identifiable rerating event;
- ticker-specific news/attention;
- earnings/guidance;
- analyst/revision;
- peer/customer/supplier read-through;
- sector/theme fundamental rerating;
- macro/rate/policy rerating;
- ownership/flow/positioning;
- multi-source convergence.

Keep source provenance and independent-family budgets so multiple articles repeating one fact do not become multiple events.

Then construct the episode study.


Primary unit should be candidate episode / first relevant transition, not duplicate nightly rows.

Preserve:

- decision cut;
- board definition;
- selection era;
- source availability clocks;
- ticker clustering;
- date clustering;
- non-overlapping episode logic.

Never condition the sample on future winners.

### 4. Measure precision and winner capture together

For H=3/5/10/21/42/63 where data exists, report:

- P(excess_SPY > 0);
- mean/median excess;
- MFE/MAE/MDD;
- date-relative top-decile winner precision;
- top-decile winner capture/recall;
- large-loser rate;
- lead time;
- sector-relative excess when lawful;
- same-date matched controls.

A 90% rule that catches 2% of winners is not a complete Prophet solution.

### 5. Study lead time

For eventual winners, reconstruct the earliest lawful observation of:

- candidate emergence;
- first rerating evidence of any species;
- attention/news burst;
- earnings/guidance or analyst-revision change;
- peer/sector/theme read-through;
- catalyst freshness;
- technical anticipation;
- confirmed technical ignition;
- RS leadership;
- board inclusion;
- plan origination;
- Entry Availability.

Determine how much earlier a full-universe research-attention surface could have seen the opportunity than the existing action board.

### 6. Test interactions without p-hacking

The T2+news result has already been observed.

For retrospective exploration, disclose every attempted interaction and multiplicity.

For true confirmation, freeze a small prospective interaction set before reading future outcomes.

Do not threshold-search dozens of variants and report the winner.

### 7. Reconcile with Conditional Fusion C1–C5

The existing owner is `WS:PROPHET-CONDITIONAL-FUSION`.

C1 is equal-weight and interaction-free.

C3/C4 already exist specifically to answer nonlinear/context-dependent weighting.

C5 already reserves multiple heads.

Recommend extensions inside this ladder. Do not create a parallel fusion/rank/control plane.

### 8. Reconcile the failed Trend Persistence study with the new durability head

Read and cite the canonical C1-NULL result before proposing a durability design:

- `Mastermind@7eac3ec252475600147ec9a376b8ca16403ac4c5`
- `research/data/trend_persistence_c1_result.json`
- `research/TREND_PERSISTENCE_PREREG_C1.md`

Return a scope table with three columns:

1. what C1-NULL actually falsified;
2. what remains untested;
3. what Prophet's leadership-persistence head specifically needs.

The new durability work must be hypothesis-distinct from the failed construction. Prefer episode-conditioned, group-granular and hazard/survival formulations over another unconditional sector-level rank-linear persistence score.

### 9. Reconcile with R6/V4

R6 did not produce the Sep NVDA hit.

Use NVDA as a golden regression against the incumbent.

Ensure any R6 recommendation preserves:

- early emergence;
- timing unlock;
- evidence-family provenance;
- deterministic availability;
- anti-chase geometry.

Pair Sep NVDA with the weaker Aug NVDA case and matched false positives.

### 10. Decide what should accrue prospectively now

Recommend the smallest zero-authority shadow telemetry that materially accelerates learning.

At minimum evaluate whether to accrue an explicit research-only interaction receipt containing:

- episode id;
- rerating-event species and source provenance;
- evidence-arrival timestamp / decision cut;
- F1/F3/F4/F5/F8 state where lawful;
- technical state before and after the event;
- interaction keys;
- group/theme context;
- later H=3/H=5/H=10/H=21/H=42/H=63 outcomes as they mature;
- lead-time milestones;
- durability transition / terminal state.

Do not make it a new state/control plane; write through the existing evaluation owner.

## Required falsifiers / negative controls

Include:

- NVDA Aug 2026 weaker plan;
- same-sector T2 failures;
- high C1 rank failures;
- T2+news failures;
- news without T2;
- T2 without news;
- blocked/bounce-wait winners;
- unconverted future winners;
- cases where short-horizon ignition succeeded but 21/63 durability failed.

## Decision questions to answer

Return explicit rulings on:

1. Is the golden case one mechanism or a linked chain?
2. Which component was load-bearing for **recommendation**?
3. Which component appears most predictive of **subsequent performance**?
4. What is the best current estimate of reproducibility for similar future cases?
5. How much of the observed 90.9% can plausibly survive shrinkage/out-of-era testing?
6. Can the mechanism materially raise win rate?
7. Can it materially raise winner recall?
8. What architecture is required to improve both at once?
9. What can be built now at zero authority?
10. What must wait for lawful data depth?
11. What exact evidence would justify promotion later?
12. Was the July confluence era actually comparable to v3 on intelligence coverage and semantics?
13. How much of the July/v3 difference is attributable to semiconductor/regime state versus data-plane maturity?
14. What rerating-event ontology captures winners that `news_burst` misses?
15. What did Trend Persistence C1-NULL truly falsify, and what distinct durability study should replace it?

## DONE_WHEN

This research phase is complete only when it leaves:

- an exact causal/mechanistic attribution for NVDA;
- a reproducibility assessment with uncertainty;
- an interaction study with era/regime/negative-control analysis;
- an explicit **data-plane maturity / comparability matrix** for July through v3;
- an adjudicated June–July semiconductor/market regime reconstruction;
- a typed **rerating-event ontology** broader than ticker news;
- a precision-recall/lead-time frontier by rerating species;
- an ignition-vs-durability ruling;
- a Trend Persistence C1-NULL scope reconciliation and a hypothesis-distinct persistence research design;
- a current C1–C5/R6 ownership map;
- a bounded prospective experiment plan;
- a prioritized Prophet upgrade recommendation;
- no production authority falsely inferred from a golden case.

If GitHub write is available, append the finished report to PR #8495's existing branch after re-reading the branch head and checking for collisions. Otherwise return a complete report for the parent session to persist.

Do not change live Prophet behavior from this commission.
