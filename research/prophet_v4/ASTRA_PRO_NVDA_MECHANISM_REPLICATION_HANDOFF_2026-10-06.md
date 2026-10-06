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

Do **not** begin by redoing the completed census. Read these research artifacts on PR #8495 first, IN THIS ORDER:

1. `research/prophet_v4/PROPHET_NVDA_PRO_REAUDIT_2026-10-06.md` — **latest corrective frontier; supersedes loose headline interpretations in the earlier studies**
2. `research/prophet_v4/PROPHET_NVDA_CONVERSION_CAUSALITY_AUDIT_2026-10-06.md`
3. `research/prophet_v4/PROPHET_NVDA_MECHANISM_EXTRACTION_2026-10-06.md`

Where an earlier report says “90.9% win rate,” use the re-audit's corrected semantics: 10/11 H5 board rows had positive **excess vs SPY**, not 10/11 profitable trades; first observation per issuer was 6/7 positive SPY excess and 4/7 positive absolute return.

Treat the re-audit's accepted measurements as the current frontier unless you find contradictory primary evidence.

Your job is to determine how much of the NVDA success is a reproducible mechanism, what parts are merely correlated context, how to increase both early winner recall and decision precision without overfitting the golden case, and how this should change the Prophet roadmap.

### Chairman refinement — do not treat older eras or `news_burst` as cleanly comparable by default

The Chairman added four material hypotheses after the first census. Treat these as **research priors to adjudicate**, not conclusions to assume:

1. **July confluence-era intelligence maturity may be materially lower than v3, and the Prophet product itself had not yet reached the later US architecture.** Repository history shows:
   - 2026-07-07: stock flow-to-price / 13F + short-flow work (#1833);
   - 2026-07-10: verified smart-money roster/backfill (#2191) and Ownership Intelligence Desk (#2192);
   - 2026-07-10: narrative-flare witness engine (#2147);
   - 2026-07-30: Intelligence Desk V2 (#4006);
   - 2026-08-02: `us_prophet_v1` priority engine + unified US pick surface (#4331);
   - 2026-08-09: Prophet US ANTICIPATION program / patience-first architecture (#4972/#4976);
   - 2026-08-15: C1 evidence-family fusion becomes canonical `us_prophet_v3` (#5753).
   Therefore July's `confluence` era is **not an old sample of the same v3 product**. An unchanged `T2 + news_burst` comparison can mix product-definition drift, candidate-population drift, feature semantics / coverage / maturity drift, and true predictive drift.

2. **June–July 2026 was a materially different semiconductor/AI-hardware regime.** Do not call it a broad-market crash without evidence. External and internal market data should adjudicate whether the correct label is semiconductor correction, AI-capex/growth scare, rate-pressure rotation, value-over-growth rotation, or some combination. The observed July selloff in semiconductors/memory makes regime comparability a first-class question.

3. **Yesterday's Trend Persistence study returned C1-NULL, but its null is construction-scoped.** Canonical result: `Mastermind@7eac3ec252475600147ec9a376b8ca16403ac4c5`, `research/data/trend_persistence_c1_result.json`. It closes only the tested eleven-GICS-sector, 20/60-session, rank-linear construction with as-of-now / non-era-correct labels and a survivor-tilted labelled universe. Its own wording says GICS industry-group/industry, basket and dynamic-theme constructions remain untested. Do not interpret this as “leadership persistence does not exist.”

4. **`news_burst` is probably a proxy for information arrival / rerating, not the complete causal class.** Important reratings can occur without a ticker-specific news burst: earnings/guidance, analyst estimate or target revisions, peer read-through, sector-wide pricing/capacity changes, hyperscaler capex, supply-demand/inventory evidence, contracts/policy, smart-money/flow, or theme/regime rotation may be the true rerating driver.

The revised commission must therefore search for the stable **rerating-conditioned ignition mechanism**, not optimize a literal `T2 && news_burst` rule.

## Pro re-audit correction — detection, entry, and plan publication are separate outcomes

The latest Pro re-audit established an important chronology:

- a real watchlist sentinel alert was generated at `2026-09-25T09:02:33Z` and first committed at 09:20 UTC / 05:20 ET, before the US market open;
- the producer uses `datetime.now(timezone.utc)`, so this is a real wall-clock generation timestamp;
- it read an older board state (board as-of Sep-23 / signal basis Sep-22) that already had NVDA `buy_now`, T1, buy zone $223.30–$228.90, chase ceiling $231.10;
- NVDA's Sep-25 opening price (~$225.13) was inside that zone, so the broader Entry Signal / watchlist stack exposed a potentially executable pre-move entry;
- the formal plan `NVDA-BULL-20260917` was first added Sep-26, after the Sep-25 close, and its tighter no-chase ceiling was $226.90; do NOT use that later plan as proof of an executable Sep-25 plan;
- the old Aug NVDA plan had already closed Sep-21, so duplicate-plan suppression did not cause the lag;
- on Sep-25 the new NVDA candidate cleared admission but formal plan validation correctly refused stale/mixed-vintage source data;
- Sep-25 Prophet checkpoints had `mixed_vintage=true` and originated **zero new plans** across the intake;
- Sep-26 source freshness became clean/current and 22 plans originated, including NVDA.

Therefore the Astra study must grade four clocks separately:

1. **detection / research attention**;
2. **Entry Availability / actionable window**;
3. **formal plan publication**;
4. **realistically executable price after publication**.

A recommendation system that detects a winner early but cannot publish a provenance-clean plan until the entry window has passed has an infrastructure/latency problem even if its selection intelligence is good.

Do not weaken the clock-provenance validator. Investigate and reduce the upstream source-freshness lag and align freshness semantics across alert, board and plan surfaces.


### Latest frozen prospective hypothesis

Read `research/prophet_v4/PROPHET_IGNITION_CONVERGENCE_PREREG_2026-10-06.md` after the Pro re-audit.

The research frontier is now narrower than “T2 + news”:

> **H-IGNITION-CONVERGENCE:** a fresh T2 second-timescale acceptance event may have materially higher H5 follow-through when at least two independent, PIT-valid rerating evidence families are concurrently active.

Historical support is discovery-only:

- first-T2-per-ticker T2 + two evidence legs: 5/5 positive vs SPY and sector, 4/5 positive absolute;
- T1 + two-leg and generic multi-leg convergence do **not** reproduce the result;
- same-date T2 controls were worse on all 7 observed dates, average mean-excess gap ~+4.19 pp;
- exploratory Fisher p values are post-selection and confer no authority.

The prospective pre-registration freezes:

- unique T2 episode as unit of account;
- H5 SPY-relative follow-through as primary, with absolute/sector/MFE/MAE companions;
- only directionally/PIT-valid evidence families;
- NVDA and all historical observations as discovery/golden-case evidence, never confirmation;
- separate detection, Entry Availability, plan publication and executable-price clocks.

Do not alter this frozen primary exposure after reading future outcomes.

### Persistence frontier

Among 134 first-T2 episodes with both H5/H10 grades, 55 were SPY-positive at H5 and 35/55 (63.6%) remained positive at H10; only 9/79 H5 non-responders became H10 winners.

Treat this as architectural evidence that durability should be studied as **P(persistence | ignition has already been accepted)**, with a dynamic post-ignition survival update, not as proof of any current persistence feature.


## Architecture reuse / owner routing discovered by the Pro re-audit

Do **not** create a new candidate-memory, lifecycle, evidence, or all-candidate plane.

Current main already has the required substrate:

- `prophet.candidate_episode/v1` B1 is PROVEN_LIVE.
- B1 intake already consumes TURN WATCH, the full candidate store, Prophet Doors, and Entry Radar observations.
- `engine/us_candidate_lanes.py` already owns the lossless all-candidate partition and preserves off-board/forming candidates without changing rank/gate authority.
- R6 B03 is explicitly chartered to **deliver the lossless searchable opportunity field** over that plane.
- R6 B04 owns the episode evidence dossier and already has active/draft carriers (#7869, #8004). Do not spawn a competing dossier implementation.

Important measured live limitation from the Oct-04 B1 reconciliation receipt (current HEAD generation `peg:2303e8ef44ff...`):

- candidate input: 4,543;
- candidate mapped to canonical episodes: 1,005;
- candidate suppressed: 3,538;
- TURN WATCH input: 374;
- TURN WATCH mapped: 9;
- TURN WATCH suppressed: 365.

The reason is architectural, not mysterious: unanchored candidate/door/radar observations may attach to an already-active canonical episode, but when no active episode exists they fail closed with `MISSING_STRUCTURAL_ANCHOR`. Today only registered structural anchors may open a B1 episode.

R6 B02 already ruled that B03/B04 do **not** need a new anchor species for their first version. Preserve that ruling.

Therefore:

1. **Emergence / Research Attention product projection belongs in B03 / the existing all-candidate field**, not in a new episode identity plane.
2. Where a canonical B1 episode exists, attach typed evidence/read-model state to that episode through existing B04/D5 interfaces.
3. Where no B1 episode exists, keep the candidate visible in the lossless B03 field with honest “no canonical episode yet” semantics. Do not fabricate a ticker/date episode or widen anchor vocabulary merely to make the row fit.
4. A future new anchor species requires its own existing R6/D02/B02 custody and evidence gate; this research does not authorize one.
5. Entry Availability remains independent and deterministic.

Current implementation-carrier check at the time of this re-audit:

- no open B03 implementation PR was found;
- B04 has active/draft work on #7869 and #8004;
- route any bounded product implementation through the existing R6 B03 owner/carrier after exact-head/custody reconciliation.


### Existing research-priority owner (do not duplicate)

Live Entry Radar already owns `mastermind.research_priority.v1` (RP1), a deterministic ACCRUING research-attention ordering.

RP1 is **not** the same object as the new rerating-convergence hypothesis:

- RP1 ranks developing Radar episodes from structural/reset/resilience/recovery measures;
- RP1 explicitly excludes attention hotness, lobe counts, sentiment and outcome-conditioned features;
- H-EMERGENCE-CONVERSION asks whether independently sourced rerating evidence predicts later valid confirmation.

Therefore:

- do not create a new Prophet “Research Priority” score;
- accrue emergence convergence first as a typed evidence/cohort state;
- use existing RP1 where a Radar research-attention ordering is needed;
- any future integration of rerating evidence into an ordering must go through the existing RP1 owner or a registered Conditional Fusion challenger and its promotion gate.


## New prospective freeze

Read and preserve:

- `research/prophet_v4/PROPHET_EMERGENCE_CONVERSION_PREREG_2026-10-06.md`

It freezes H-EMERGENCE-CONVERSION with a **12 observed board-session** primary conversion endpoint.

Historical result motivating the freeze (discovery only):

- raw preserved >=2-evidence unresolved watch states: ~23% T1/T2 conversion by 11–12 observed board sessions;
- mean same-date ordinary-watch control conversion: ~6–7%;
- NVDA first preserved >=2-evidence watch snapshot: Sep-04;
- NVDA T1 `buy_now`: Sep-23, 11 observed board sessions later.

Do not optimize this head on H5 return. Its intended job is early research attention + continuity while entry remains closed.


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

### Discovered interaction — corrected semantics

In the matured `us_prophet_v3` H=5 board history, T2+news remains an interesting **relative-performance discovery**, not a demonstrated trade win rate:

- n=11 board rows / 7 issuers;
- 8/11 positive absolute five-session returns;
- 10/11 positive excess vs SPY;
- 9/11 positive sector excess;
- mean SPY excess +3.58%.

First observation per issuer:

- 7 issuers;
- 4/7 positive absolute return;
- 6/7 positive SPY excess;
- 5/7 positive sector excess;
- mean SPY excess +3.82%.

At H=10 the result weakens materially:

- 10 rows / 6 issuers;
- 5/10 positive absolute;
- 5/10 positive SPY excess;
- mean SPY excess +0.84%;
- excluding INTC, mean SPY excess falls to about **-1.28%**.

Also note: NVDA's `news_burst` itself was six recent items with **neutral sentiment** (0 positive / 0 negative), so this feature is better understood as attention/information arrival than bullish news.

A broader OR across `news_burst || sue_fresh || smartmoney_add` did **not** improve T2.

The more interesting discovery seed is **T2 + at least two independent evidence legs**:

- H=5 n=12 rows / 5 issuers;
- 10/12 positive SPY excess;
- 9/12 positive absolute return;
- first observation per issuer: 5/5 positive SPY excess, 4/5 positive absolute;
- mean first-issuer SPY excess +3.66%.

This is extremely small and discovered after inspection. Treat it as a hypothesis for **independent evidence convergence × ignition**, not as a rule or expected live win rate.

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

Also produce a **Prophet-definition timeline** from July `confluence` -> `us_prophet_v1` -> ANTICIPATION -> `us_prophet_v3`, naming which population, gate, rank, and evidence semantics changed at each break.

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
- alert-generation / board-publication / plan-publication clocks as separate fields;
- realistically executable first price after each publication clock;
- ticker clustering;
- date clustering;
- non-overlapping episode logic.

Never condition the sample on future winners.

### 4. Measure precision and winner capture together

For H=3/5/10/21/42/63 where data exists, report:

- positive absolute return rate;
- P(excess_SPY > 0);
- sector-relative positive rate;
- mean/median absolute, SPY-relative and sector-relative returns;
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
- first provenance-clean formal plan publication;
- first realistic executable price after publication;
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
- lead-time milestones across detection, availability, plan publication and executable price;
- stale/mixed-vintage state at every milestone;
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
16. How much winner lead time is currently lost between detection, Entry Availability, and formal plan publication?
17. Which freshness/data-plane failure modes consume that lead time, and how should existing owners eliminate them without weakening provenance gates?
18. Does independent multi-family convergence explain ignition better than any single event proxy?

## DONE_WHEN

This research phase is complete only when it leaves:

- an exact causal/mechanistic attribution for NVDA;
- a reproducibility assessment with uncertainty;
- an interaction study with era/regime/negative-control analysis;
- an explicit **data-plane maturity / comparability matrix** for July through v3;
- an adjudicated June–July semiconductor/market regime reconstruction;
- a typed **rerating-event ontology** broader than ticker news;
- a precision-recall/lead-time frontier by rerating species, with absolute vs relative outcomes separated;
- a detection -> availability -> plan-publication -> executable-price latency decomposition;
- an ignition-vs-durability ruling;
- a Trend Persistence C1-NULL scope reconciliation and a hypothesis-distinct persistence research design;
- a current C1–C5/R6 ownership map;
- a bounded prospective experiment plan;
- a prioritized Prophet upgrade recommendation;
- no production authority falsely inferred from a golden case.

If GitHub write is available, append the finished report to PR #8495's existing branch after re-reading the branch head and checking for collisions. Otherwise return a complete report for the parent session to persist.

Do not change live Prophet behavior from this commission.
