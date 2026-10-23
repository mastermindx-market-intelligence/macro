# Prophet NVDA Mechanism Attribution — Golden-Case Deep Census

**Date:** 2026-10-06  
**Status:** research / evaluation only  
**Authority:** zero rank, gate, size, trade, deployment, or promotion authority  
**Companion:** `PROPHET_NVDA_CONVERSION_CAUSALITY_AUDIT_2026-10-06.md`  
**Macro pin:** `2f2feec4851b45636f63a48ec61e6f0b02b8118a`  
**Protected procedure pin:** `Mastermind@877b1e7f275da0b6d3558d2667778b32d628bf67`

## Executive conclusion

The September NVDA win was **not produced by one magic predictive indicator**.

It was produced by a more interesting architecture:

1. Prophet had already recognized NVDA as an unusually strong **latent opportunity** before it was actionable.
2. One root technical timing transition on Sep-25 caused the buy-readiness machinery to unlock.
3. That one root transition propagated through several **correlated gates** that all represented the same broad state change in different forms.
4. Once the name became admissible, the independent evidence-family fusion ranked NVDA #1 because several additional evidence families were unusually positive.
5. The structure-anchored entry geometry allowed participation without treating the already-rising print as permission to chase.
6. The subsequent market leadership outcome cannot be causally attributed to Mastermind; Mastermind selected the opportunity before the move. The market move is the outcome being predicted, not an effect caused by the system.

The right abstraction is therefore:

> **latent-leader recognition -> timing unlock -> correlated admission cascade -> independent evidence prioritization -> bounded entry availability -> continuation**

The most important distinction is that **the activation was nearly a single root mechanism, while the high-confidence prioritization was multi-mechanism**.

---

## 1. Exact point-in-time source

This audit reconstructed and verified the exact board snapshot consumed by Prophet for Sep-25 rather than recomputing the row from current code.

`site/prophet/index.json` identifies:

- source board as-of: `2026-09-25`
- frozen snapshot:
  `data/prophet/origination_sources/716c0da79512aceb44b2e0359f755590631a0e53276d6bbb2860863d17a63ebe.json.gz`
- declared content SHA-256:
  `716c0da79512aceb44b2e0359f755590631a0e53276d6bbb2860863d17a63ebe`

The compressed Git object was decoded and decompressed separately. The decompressed JSON hash matched that declared identity exactly.

That is the source used for every Sep-25 attribution below.

---

## 2. The strongest causal fact: the trigger explains almost the whole recommendation unlock

On Sep-24 NVDA already had strong latent edge but was not actionable:

- lane: `watch`
- cycle state: `TOP WATCH`
- direction/tone: `caution`
- conviction band: `low`
- buy-readiness score: **4**
- selection edge percentile: **95**
- timing score: **4**
- cycle blocked: **true**
- alignment blocked: **true**
- signal tier: **T3**
- provisional: **true**
- entry status: **extended**
- act level: **0**
- entry z: **-32.3**
- potential trigger component: **0.075**
- potential edge multiplier: **1.224**
- potential fuel: **0.077**
- price: **224.58**
- off high: **-4.5%**

On Sep-25:

- lane: `continuation`
- cycle state: `TURN SIGNALED`
- tone: `up`
- conviction band: `constructive`
- buy-readiness score: **51**
- selection edge percentile: **98**
- timing score: **51**
- cycle blocked: **false**
- alignment: **ARMED**
- signal tier: **T2**
- provisional: **false**
- entry status: **partial**
- urgency: **now**
- act level: **3**
- entry z: **+64.2**
- potential trigger component: **0.92**
- potential edge multiplier: **1.223**
- potential fuel: **0.074**
- price: **225.07**
- off high: **-4.3%**

The stock price changed only about 0.2% between those closes. The latent fuel and edge components barely changed.

The name-potential formula is:

```
score =
100
* trigger
* (0.4 + 0.6 * fuel)
* survive
* tailwind
* confidence
* edge_mult
```

Using the exact Sep-24 and Sep-25 components:

- actual Sep-24 reconstructed raw score: ~**4.06**
- actual Sep-25 reconstructed raw score: ~**50.61**
- Sep-25 non-trigger components with the old Sep-24 trigger: ~**4.13**
- Sep-24 non-trigger components with only the new Sep-25 trigger: ~**49.75**

Therefore roughly **98.1% of the raw score jump** is explained by changing the trigger while holding the other Sep-24 components fixed.

### Ruling

The immediate Sep-25 recommendation unlock was overwhelmingly a **technical timing transition**, not a sudden discovery of new fundamental/news/flow evidence.

---

## 3. What created the trigger jump

The trigger is itself a linked calculation.

### Sep-24

The cycle ladder was `TOP WATCH`, whose base trigger is 0.15.

The entry status was `extended`, whose confirmation multiplier is 0.50.

Therefore:

```
0.15 * 0.50 = 0.075
```

### Sep-25

The cycle ladder became `TURN SIGNALED`, whose base trigger is 0.92.

The entry state was no longer an extended/caution state, so the trigger retained the 0.92 base.

Thus the effective trigger moved:

```
0.075 -> 0.92
```

That is a roughly **12.3x activation multiplier**.

At the same time the signal cascade moved:

```
T3 provisional
  ->
T2 confirmed
```

The T2 contract is itself a fresh confluence condition: the 2D RSI-MACD has just crossed while the 3D StochRSI has crossed recently and remains constructive/not topped.

The same underlying technical change also moved:

- alignment blocked -> ARMED;
- daily/3D relationship;
- cycle blocked -> clear;
- entry `extended -> partial`;
- urgency `caution -> now`;
- act level `0 -> 3`;
- stage -> `live`;
- conviction band `low -> constructive`.

### Important architecture observation

These are **not six independent discoveries**.

Several are correlated projections of the same underlying timing evidence.

The current bridge then asks, among other things, for:

- conviction band not low;
- actionable signal tier T1/T2/T3;
- admitted entry status;
- acceptable direction.

So one technical turn can clear several downstream gates at once.

This makes the Sep-25 move a **correlated gate cascade**.

That cascade can be desirable because it is selective, but it must not be mistaken for six independent confirmations when estimating confidence.

---

## 4. One mechanism or multiple mechanisms?

There are three different answers depending on the causal question.

### A. What caused the plan to become admissible?

**Mostly one root mechanism.**

The load-bearing event was the timing transition that changed the cycle/entry state and opened the trigger.

The conviction band, entry status, T2 confirmation, alignment state, stage and act-level changes were multiple linked manifestations of that transition.

If this root unlock did not happen, the plan would still have been refused despite the pre-existing edge.

### B. What caused NVDA to be prioritized above other newly actionable names?

**Multiple mechanisms.**

Once admissible, NVDA received a canonical `us_prophet_v3` fusion score of **80.5**, rank **#1**.

Active family contributions:

| Family | Sep-25 contribution |
|---|---:|
| F1 Technical confluence | 71.59 |
| F2 Momentum / extension | 68.84 |
| F4 Catalyst / event | 93.48 |
| F5 Flow / positioning | 69.93 |
| F8 Attention / crowding | 98.55 |

The ranker is an unfitted equal-weight mean of active evidence families.

Counterfactual leave-one-family-out on the exact Sep-25 board:

- remove F1 -> NVDA remains #1
- remove F2 -> #1
- remove F4 -> #1
- remove F5 -> #1
- remove F8 -> #1

No single family was necessary for rank #1.

F1+F2 alone would have left NVDA around rank #3. The sparse F4/F8 positives provided unusual additional separation.

Therefore its **relative prioritization** was robustly multi-family even though its **action unlock** was primarily one technical transition.

### C. What caused NVDA to become a future market leader?

Unknown from one case.

Mastermind did not cause the stock to rally. The system detected conditions preceding the rally.

The market-economic causes may include earnings/revision expectations, AI/semiconductor demand, positioning, capital flows, sector/theme leadership, and other factors. A single winning stock cannot identify their causal weights.

---

## 5. Ranking was not necessary for plan existence

This distinction matters.

Sep-25 plan intake had no positional cap:

- 69 buy rows;
- 39 admitted;
- 22 plans originated;
- no top-N slice.

The live bridge originates every admitted row unless blocked by duplicate/open-plan/validation constraints.

Therefore NVDA did **not** become a plan because it ranked #1.

The rank increased priority and visibility, but the **admission transition** caused plan eligibility.

This lets us separate:

- **discovery / prioritization**;
- **entry availability**;
- **plan origination**.

They should remain separate in the successor architecture.

---

## 6. Featured was not the winning mechanism

Despite rank #1, NVDA was:

```
featured = false
featured_blocked_by = ["alpha_below_floor"]
```

Residual alpha on the exact board was slightly negative.

Therefore the flagship Featured shelf did not cause this detection and would actually have hidden it from that narrower surface.

This is a valuable product finding:

> a high-quality transition can exist even when a different Featured-screen veto correctly refuses to call the same name a Featured setup.

Do not remove the alpha floor from Featured based on this case. Instead, evaluate whether a separate **Latent Leader / Transition Desk** should surface this class without changing Featured authority.

---

## 7. The historical test rejects the easy extraction

The exact board fossil ledger contains 49 PIT board snapshots. The existing graded board ledger supplies forward results.

The analysis used the historical `us_prophet_v3` period and did not condition on future winners.

### Generic T2 confirmation

Within the v3 BUY lane:

#### H=5

- all buy rows: n=1,098, 20 dates
- mean SPY excess: -1.08%
- positive SPY excess: 34.2%

T2 + `partial/buy_now`:

- n=147
- 19 dates
- mean SPY excess: **-1.62%**
- median SPY excess: **-1.99%**
- positive SPY excess: **29.9%**

#### H=10

All BUY:

- n=923
- 16 dates
- mean excess: -2.71%
- positive excess: 29.3%

T2 confirmation:

- n=130
- mean excess: **-3.40%**
- positive excess: **25.4%**

#### H=21

All BUY:

- n=407
- 7 dates
- mean excess: -5.56%
- positive excess: 15.7%

T2 confirmation:

- n=57
- mean excess: **-6.85%**
- positive excess: **10.5%**

### Ruling

**T2 confirmation by itself is not the reusable winner mechanism.**

Promoting T2 or admitting more T2 names would be contrary to the observed record.

---

## 8. “High latent edge + unlock” also fails as a simple rule

The next hypothesis was closer to NVDA:

> only trust T2 confirmations when the name was already a very high latent-edge name on the prior board.

That also failed as a generic rule.

For prior `score_edge >= 90`:

### H=5

- n=10 fires
- 5 distinct names
- 6 dates
- mean excess: **-3.40%**
- positive excess: **20%**

The closest matured analogue to the NVDA state transition was ADM on Sep-9:

- prior state: extended
- prior edge: 90
- prior timing: 4
- cycle blocked: true
- next state: buy_now / T2
- trigger: 0.075 -> 1.0

ADM then delivered:

- approximately +0.73% SPY excess at 5d;
- approximately -7.27% SPY excess at 10d.

### Ruling

The technical unlock is mechanically reproducible, but it is **not sufficient to reproduce NVDA-like market outcomes**.

This is the strongest evidence against turning the golden case into a direct hard-coded rule.

---

## 9. Sparse contextual evidence is interesting but currently unproven

NVDA also had rare contextual positives on Sep-25:

- fresh positive SUE;
- smart-money add;
- six recent news items;
- strong event/revision edge;
- AI / semiconductor / Mag7 context;
- coiled / washout context;
- sector and theme tailwinds.

An exploratory historical filter of T2 confirmations carrying at least two of:

- fresh SUE;
- smart-money add;
- news burst

initially appeared very strong:

- 5 historical rows;
- 4/5 positive at 5d;
- about +2.13% mean SPY excess.

But four of those five rows were repeated ADM observations.

There were only **two distinct names: ADM and ISRG**.

ADM's later 10d outcomes turned negative.

### Ruling

That apparent edge is pseudo-replicated and far too small for a claim.

It is a useful hypothesis for forward accrual, not a promotion result.

---

## 10. Why the current result is still highly valuable despite the nulls

The negative tests make the golden case more useful, not less.

They tell us exactly what *not* to do:

- do not boost all T2 names;
- do not simply require high prior edge;
- do not just buy top-ranked names;
- do not admit `buy_soon` earlier;
- do not interpret multiple correlated timing gates as independent evidence;
- do not hard-code SUE/news/smart-money conjunctions from two names.

Instead, NVDA exposes an architecture opportunity:

### Prophet currently mixes three jobs

1. **latent leader discovery** — who deserves intense monitoring before entry;
2. **entry availability** — when the window actually opens;
3. **outcome conviction** — how likely this actionable setup is to become a durable leader.

NVDA demonstrates that job 1 worked before job 2.

The system had a ~95th-percentile latent-edge reading while correctly refusing entry on Sep-24.

But there is no first-class Prophet product state that says:

> “This is one of the highest-quality latent opportunities in the market. Do not buy yet. Watch for the specific transition that will make it actionable.”

That is the capability to extract.

---

## 11. Reproducibility assessment

### Mechanical reproducibility of the Sep-25 recommendation transition: HIGH

The calculations are deterministic and PIT-derived.

If the same inputs recur, the same cycle / signal / entry / band gates should recur, assuming current and correct data.

The management freshness defect discovered in the companion audit must be repaired because stale data is an operational threat to that reproducibility.

### Reproducibility of NVDA-like winner outcomes from the trigger alone: LOW

The historical v3 cohort rejects generic T2 confirmation and generic high-edge confirmation as standalone winner selectors.

### Reproducibility of the exact full NVDA phenotype: UNKNOWN

The full phenotype is too rare to estimate.

Some of the apparently independent features are actually correlated projections.

Some sparse contextual features have too little independent sample.

### Likelihood that a better mechanism can be extracted: MEANINGFUL / MODERATE-HIGH RESEARCH UPSIDE

This is not because the current golden pattern backtests well.

It is because:

- the system already captured the opportunity before the entry;
- the transition graph is interpretable;
- candidate/episode PIT data already exists;
- current architecture exposes enough independent evidence families for conditional testing;
- the existing outcome graders can test any successor without inventing a new evaluation plane;
- the golden case reveals exactly where discovery, entry, ranking and product surfacing are conflated.

There is therefore a realistic path to a materially better Prophet, but **not by copying the NVDA rule literally**.

---

## 12. How to increase winner coverage without sacrificing entry quality

The main design recommendation is a two-stage detection architecture.

### Stage A — Latent Leader Radar

High recall.

Purpose:

> identify stocks that could become future leaders before their entry opens.

Candidate features may include existing PIT observations:

- selection/event edge;
- persistent relative strength;
- sector/theme strength;
- revisions / SUE;
- coiled / washout lifecycle;
- quality / fundamental context where legally available;
- flow/positioning evidence that has earned incremental authority;
- transition proximity;
- breadth of truly independent evidence.

Output must be research/monitoring priority at first, **not a buy signal**.

A stock can be:

```
LATENT_LEADER_HIGH
ENTRY_CLOSED
```

without contradiction.

NVDA on Sep-24 is the reference composition.

### Stage B — Entry Availability / Transition Desk

High precision.

Consumes:

- the latent episode;
- fresh confluence;
- entry geometry;
- extension;
- exact quote/session freshness;
- strategy/horizon policy.

Outputs:

```
ENTRY_OPEN
APPROACHING_ENTRY
WAIT_PULLBACK
RAN_DONT_CHASE
INVALIDATED
UNAVAILABLE_DATA
```

This belongs with the existing B4 Entry Availability architecture rather than a second action engine.

### Stage C — Conditional Outcome Confidence

This is the missing research layer.

Question:

> conditional on a latent leader becoming actionable, which evidence makes it more likely to become a durable market leader rather than an ordinary signal?

This must be learned/evaluated from PIT history and prospective shadow data.

It may use interactions among evidence families, but only after:

- time-ordered validation;
- outcome-independent feature registration;
- distinct-name / distinct-episode honest N;
- sector/date clustering;
- held-out evaluation;
- forward shadow accrual.

The output must not be called calibrated conviction until calibration is actually proven.

---

## 13. Important anti-double-counting requirement

The Sep-25 recommendation looks like many confirmations:

- T2;
- partial;
- urgency now;
- cycle clear;
- alignment armed;
- stage live;
- conviction band constructive;
- trigger 0.92.

But much of that evidence shares the same technical ancestry.

A successor confidence engine must carry an **evidence-dependence graph**.

Correlated derivatives of the same underlying technical event must not be counted as independent evidence votes.

This is likely one of the highest-value lessons from the case.

The system should distinguish:

```
root observation family
  -> derived state A
  -> derived state B
  -> derived gate C
```

from:

```
independent root family 1
independent root family 2
independent root family 3
```

Only the latter should increase independent-evidence confidence multiplicatively.

---

## 14. What the fusion score can and cannot tell us

On Sep-25 NVDA's family breadth was genuinely unusual.

However:

- F4 catalyst and F8 attention were sparse/near-constant on many historical boards;
- current W3 family diagnostics describe ordering contribution, not predictive alpha;
- the prospective W3 canonical-vs-shadow race has only **1 matured H=10 paired session** against its preregistered **20-session** lawful-read floor.

Therefore:

- we can say F4/F8 materially helped NVDA's Sep-25 relative rank;
- we cannot say F4/F8 caused future returns;
- we cannot yet say fusion is prospectively superior to the retired shadow ranker.

The golden case must not be used to bypass W3's preregistered maturity law.

---

## 15. A stronger research target than “find another NVDA”

The better target is an episode taxonomy.

Every future candidate should be classifiable as one of:

1. **ordinary confirmation**;
2. **latent leader awaiting trigger**;
3. **latent leader freshly unlocked**;
4. **late leader / do not chase**;
5. **false unlock / failed confirmation**;
6. **leader without conventional Prophet trigger**;
7. **context-driven catalyst transition**;
8. **theme/sector-driven participation transition**.

Then estimate:

- conversion rate;
- 5/10/21/42/63-session excess;
- MFE / MAE;
- probability of entering top-decile RS leadership;
- leadership persistence;
- missed-winner rate;
- false-activation rate.

This creates a reusable mechanism library rather than overfitting one exemplar.

---

## 16. Exact next experiments

### E1 — Transition-delta ledger

Use the existing candidate-episode / evaluation owner.

Stamp PIT transition deltas, not merely states:

- previous/current cycle;
- previous/current signal tier;
- provisional -> confirmed;
- previous/current entry status;
- previous/current cycle blocked;
- previous/current alignment;
- trigger delta;
- entry-z delta;
- extension;
- evidence-family contributions;
- latent-edge measures;
- theme/sector state;
- quote/session freshness.

Do not create a second lifecycle store.

### E2 — Latent-leader target

Evaluate the *discovery* question separately:

> among names visible tonight, which become top-decile relative-strength leaders over the next 5/10/21/42/63 sessions?

This is a different label from “should buy now.”

Use full-universe PIT cohorts, not only existing BUY rows.

### E3 — Transition hazard

Evaluate:

> among latent leaders, what predicts an actionable transition in the next 1–3 sessions?

This can improve warning lead-time without buying earlier.

### E4 — Conditional winner model

Within transition events only:

> what predicts durable leader outcome after the entry opens?

Compare simple registered baselines first.

Do not train a complicated learner until enough independent episodes exist.

### E5 — Negative-control suite

Must include:

- NVDA Aug-2026 weaker plan;
- ADM Sep-9 closest matured unlock analogue;
- T2 false positives;
- high-edge false positives;
- top-ranked losers;
- unconverted winners;
- leaders that never use this transition path.

### E6 — Featured disconnect

Measure whether rank-high / Featured-vetoed names systematically differ from rank-high Featured names.

NVDA proves the states can disagree; it does not prove the Featured alpha floor is wrong.

### E7 — management repair

Complete the stale-frame / ordered-bar replay repair before any study uses management timestamps as event truth.

---

## 17. Expected opportunity for better win rate and better winner coverage

These two goals should not be optimized with one threshold.

### More winner coverage

Most likely route:

- widen **observation**, not action;
- score the full candidate/episode universe for latent-leader probability;
- keep entry authority closed until the existing deterministic gate opens.

This can increase recall without automatically creating more trades.

### Higher win rate

Most likely route:

- condition entry-open events on independently validated winner-quality evidence;
- remove pseudo-confirmation from correlated signals;
- use regime/theme/sector interactions only if held-out evidence earns them;
- calibrate confidence separately from rank.

### Both at once

Possible, but harder.

The architecture that gives the best chance is:

```
broad discovery
    ->
strict availability
    ->
conditional quality
```

rather than one global score trying to maximize recall and precision simultaneously.

---

## 18. Current likelihood judgment

These are research judgments, not statistical posterior probabilities.

| Question | Current judgment | Why |
|---|---|---|
| Can the exact mechanical Sep-25 state transition be reproduced when similar inputs recur? | **High** | deterministic rules; explicit PIT inputs |
| Does generic T2 confirmation reproduce NVDA-like winners? | **Low** | historical cohort underperforms broader BUY cohort |
| Does high prior latent edge + T2 solve it? | **Low as a standalone rule** | historical high-edge confirmations also underperform |
| Is the exact full NVDA phenotype proven repeatable? | **Unknown** | too few independent analogues |
| Can Prophet surface similar future leaders earlier than today? | **High engineering feasibility** | Sep-24 already contained the latent evidence; product state is missing |
| Can a conditional successor materially improve selection quality? | **Moderate-to-high research potential** | rich PIT substrate + separable evidence families + existing graders |
| Is a dramatically higher win rate already supported by this case? | **No** | one golden case plus negative cohort tests cannot establish it |
| Can winner recall rise without loosening trade gates? | **High architectural feasibility** | separate latent-leader observation from Entry Availability |

---

## 19. Recommended use of the golden case

Do **not** “promote the NVDA formula.”

Instead use NVDA as:

1. a golden regression;
2. an architecture probe;
3. a positive example for latent-leader discovery;
4. a positive example for action unlock;
5. a warning about correlated evidence masquerading as independent confirmation;
6. a prompt to create a full transition phenotype study;
7. an acceptance test for R6/V4/B4;
8. one data point in a prospective Transition Desk.

The goal is to extract the **general mechanism class**, not the ticker-specific configuration.

---

# Astra Pro continuation recommendation

Astra Pro is recommended for the **next research phase**, but it is not needed to establish the core attribution above.

The core result is already sufficiently identified:

> NVDA's plan unlock was almost entirely one technical trigger transition propagated through correlated admission gates; its #1 prioritization was multi-family; neither generic T2 nor generic high-edge confirmation is historically sufficient to reproduce the win.

What remains is the large, multi-phase problem Astra is well suited to:

- full fossil-ledger episode reconstruction;
- full-universe latent-leader target construction;
- transition clustering / taxonomy;
- matched controls;
- family-dependence graph;
- sector/theme/regime conditioning;
- prospective evaluation design;
- R6/V4 architecture recommendation;
- adversarial review against overfitting.

## Commission for Astra Pro

### Mission

Determine whether the NVDA Sep-2026 episode belongs to a reproducible class of **latent leader -> actionable transition -> durable leadership** events, and design the strongest lawful Prophet successor that can increase early winner detection and action precision without hindsight leakage or duplicated authority.

### Required starting evidence

Consume, do not redo:

- this mechanism-attribution audit;
- `PROPHET_NVDA_CONVERSION_CAUSALITY_AUDIT_2026-10-06.md`;
- exact Sep-25 frozen origination snapshot identified above;
- W3 race preregistration and current W3 status;
- current B1/B2/B3/B4 Prophet V4 ownership and Entry Availability architecture;
- current candidate + grade stores;
- current management replay defect.

### Required hypotheses

Test separately:

**H1 — latent-leader discovery**  
Can PIT evidence identify future top-decile RS leaders before entry opens?

**H2 — transition hazard**  
Among latent leaders, can the next 1–3-session action unlock be predicted earlier than the current confirmation without materially increasing false activations?

**H3 — conditional winner quality**  
Once entry opens, can independent evidence distinguish durable leaders from ordinary/failed confirmations?

**H4 — evidence independence**  
How much of apparent confluence is duplicate information derived from the same root technical event?

**H5 — regime / theme conditionality**  
Are successful unlocks concentrated in themes/sectors entering persistent leadership, and is that information incremental rather than retrospective?

**H6 — product separation**  
Does splitting latent discovery, entry availability and outcome confidence outperform the current conflated user experience without changing trade authority prematurely?

### Mandatory negative controls

- NVDA Aug-2026;
- ADM Sep-9;
- matched T2 losers;
- high-edge losers;
- top-ranked losers;
- winners Prophet sighted but never converted;
- future leaders never represented by the NVDA path.

### Evaluation law

- PIT decision cut only;
- no future-winner-conditioned training denominator;
- first occurrence / episode grain primary;
- repeated ticker/date fires clustered, not treated as independent names;
- date and ticker dependence accounted for;
- time-ordered holdouts;
- report nulls;
- no threshold tuned on final holdout;
- no live promotion from this research.

### Desired output

A decision-ready package containing:

1. exact mechanism DAG;
2. episode taxonomy;
3. latent-leader detection scorecard;
4. transition-hazard scorecard;
5. conditional-winner scorecard;
6. independence/redundancy map;
7. precision/recall frontier;
8. false-positive and missed-winner audit;
9. proposed Prophet architecture changes;
10. forward shadow plan and promotion gates;
11. explicit list of mechanisms that should **not** be promoted.

### Done when

We can answer, with honest out-of-sample evidence:

- which facts should make Prophet notice a stock early;
- which facts should make it actionable;
- which facts should raise outcome confidence;
- which apparent confirmations are duplicates;
- how many additional leaders the new architecture would have caught;
- what false-positive cost it pays;
- whether it improves on the incumbent rather than merely explaining NVDA.
