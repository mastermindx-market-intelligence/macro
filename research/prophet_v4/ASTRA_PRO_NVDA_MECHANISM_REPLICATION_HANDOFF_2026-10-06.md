# Astra Pro Research Commission — Prophet Golden-Case Mechanism Replication

**Date:** 2026-10-06  
**Mission type:** deep research / forensic evaluation / architecture recommendation  
**Implementation authority:** NONE unless separately granted by the Chairman.  
**Trading authority:** NONE.  
**Canonical research carrier:** macro draft PR #8495, branch `sol/prophet-nvda-conversion-audit-20261006`  
**Current branch head at handoff:** `b31dd90bca1709afcc972f9a19d19361e64e1dbd`  
**Primary source pin used by the prior census:** `macro@2f2feec4851b45636f63a48ec61e6f0b02b8118a`

## Commission

Lead the next research phase on the September 2026 NVDA Prophet golden case.

Do **not** begin by redoing the completed census. Read the two research artifacts on PR #8495 first:

1. `research/prophet_v4/PROPHET_NVDA_CONVERSION_CAUSALITY_AUDIT_2026-10-06.md`
2. `research/prophet_v4/PROPHET_NVDA_MECHANISM_EXTRACTION_2026-10-06.md`

Treat their accepted measurements as the current frontier unless you find contradictory primary evidence.

Your job is to determine how much of the NVDA success is a reproducible mechanism, what parts are merely correlated context, how to increase both early winner recall and decision precision without overfitting the golden case, and how this should change the Prophet roadmap.

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

### H2 — ignition interaction

In the current v3 population, fresh technical confirmation has much higher immediate follow-through when accompanied by a fresh attention/catalyst event.

Do not assume the exact interaction is `T2 AND news_burst`. Treat that as the discovery seed and search for the underlying stable construct.

Possibilities include:

- F1 technical x F8 attention;
- F1 x F4 catalyst;
- F1 x F4 x F8;
- F1 x F8 x F5 flow;
- state transition x evidence arrival;
- an interaction that is positive pre-extension but negative as crowding after extension.

### H3 — separate ignition and durability

The discovered interaction may predict 3–10 session ignition but not 21–63 session leadership persistence.

Test whether Prophet needs separate heads:

- emergence;
- ignition/follow-through;
- durability/leadership persistence;
- deterministic Entry Availability.

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

### 2. Explain the era split

The T2+news interaction is strong in v3 and weak in the July confluence era.

Determine whether this is explained by:

- changed candidate populations;
- changed entry semantics;
- changed `news_burst` semantics/coverage;
- different signal-tier construction;
- regime composition;
- survivor/selection effects;
- data availability;
- genuine context dependence.

Do not pool incompatible eras to make the effect look stable.

### 3. Construct a PIT-safe episode study

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
- attention/news burst;
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

### 8. Reconcile with R6/V4

R6 did not produce the Sep NVDA hit.

Use NVDA as a golden regression against the incumbent.

Ensure any R6 recommendation preserves:

- early emergence;
- timing unlock;
- evidence-family provenance;
- deterministic availability;
- anti-chase geometry.

Pair Sep NVDA with the weaker Aug NVDA case and matched false positives.

### 9. Decide what should accrue prospectively now

Recommend the smallest zero-authority shadow telemetry that materially accelerates learning.

At minimum evaluate whether to accrue an explicit research-only interaction receipt containing:

- episode id;
- F1/F4/F5/F8 state;
- interaction keys;
- decision cut;
- later H=5/H=10/H=21 outcomes;
- lead-time milestones.

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

## DONE_WHEN

This research phase is complete only when it leaves:

- an exact causal/mechanistic attribution for NVDA;
- a reproducibility assessment with uncertainty;
- an interaction study with era/regime/negative-control analysis;
- a precision-recall/lead-time frontier;
- an ignition-vs-durability ruling;
- a current C1–C5/R6 ownership map;
- a bounded prospective experiment plan;
- a prioritized Prophet upgrade recommendation;
- no production authority falsely inferred from a golden case.

If GitHub write is available, append the finished report to PR #8495's existing branch after re-reading the branch head and checking for collisions. Otherwise return a complete report for the parent session to persist.

Do not change live Prophet behavior from this commission.
