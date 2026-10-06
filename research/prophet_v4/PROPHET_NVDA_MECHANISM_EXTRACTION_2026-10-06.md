# Prophet NVDA Mechanism Extraction — Golden-Case Deep Census

**Date:** 2026-10-06  
**Scope:** exact Sep-2026 NVDA mechanism attribution, reproducibility, interaction extraction, higher-precision / higher-recall Prophet design  
**Authority:** research / evaluation only. No score, rank, gate, alert, sizing, trading, deployment, or promotion authority.  
**Source pin:** `mastermindx-market-intelligence/macro@2f2feec4851b45636f63a48ec61e6f0b02b8118a`  
**Sep-25 origination snapshot:** `data/prophet/origination_sources/716c0da79512aceb44b2e0359f755590631a0e53276d6bbb2860863d17a63ebe.json.gz`  
**Protected procedure pin:** `mastermindx-market-intelligence/Mastermind@877b1e7f275da0b6d3558d2667778b32d628bf67`

## Executive ruling

The NVDA win is **not attributable to one standalone signal**.

It is best explained as a **linked, overdetermined mechanism** with different components performing different jobs:

1. **Opportunity substrate / WHY THIS NAME:** catalyst, attention, flow/positioning and relative-strength evidence made NVDA unusually interesting before the entry window opened.
2. **Timing unlock / WHY NOW:** the cycle/ladder state changed sharply while price barely moved; the entry gauge changed from `extended` to `partial`, and the confluence tier changed from provisional T3 to confirmed T2.
3. **Admission / WHY A PLAN EXISTED:** the timing transition multiplied the name-level potential score from 4 to 51, moving conviction from `low` to `constructive`, while the entry status moved into an admitted class.
4. **Prioritization / WHY NVDA ROSE TO THE TOP:** C1 evidence-family fusion ranked NVDA #1 at 80.5. The retired v2 shadow ranked it #4. C1 improved salience, but because plan origination was lossless/no-cap it was not the sole reason a plan could exist.
5. **Execution / WHY THE ENTRY WAS NOT A BLIND CHASE:** the plan imposed an accumulate zone ($220.50–$225.10) and $226.90 chase ceiling.

The strongest extractable research hypothesis from the golden case is **not “T2 wins”**. Generic T2 and generic confirmation cohorts are poor. The strongest new discovery is a nonlinear **fresh technical confirmation × news/attention ignition** interaction, potentially strengthened by an independent flow/positioning leg.

This is exactly the class of behavior the existing Conditional Fusion ladder reserved for C3/C4. It should be developed there, not as a parallel NVDA-specific detector.

---

## 1. Exact Sep-24 → Sep-25 causal transition

The most important forensic fact is that **price hardly moved** while Prophet's internal action state changed dramatically.

| Field | Sep 24 | Sep 25 |
|---|---:|---:|
| price | $224.58 | $225.07 |
| board lane | watch | buy |
| state | TOP WATCH / NEARING A HIGH | TURN SIGNALED / BOTTOMING |
| signal tier | T3 shallow | T2 shallow |
| signal provisional | true | false |
| tier event date | null | 2026-09-25 |
| entry status | extended | partial |
| urgency | caution | now |
| act level | 0 | 3 |
| entry z | -32.3 | +64.2 |
| conviction / potential | 4 / low | 51 / constructive |
| cycle blocked | true | false |
| alignment | weekly rising · 3D turn · daily crossed | weekly rising · 3D turn · daily rising / ARMED |

The stock moved only about +0.22%, so this was not a score mechanically chasing price.

### Name-score trigger was load-bearing

The name-level potential-score components were nearly unchanged except for the timing trigger.

Sep 24:

- fuel ~0.077
- effective trigger ~0.075
- survive 1.0
- tailwind 1.05
- confidence ~0.943
- edge ~1.224
- resulting potential score: **4**

Sep 25:

- fuel ~0.074
- trigger **0.92**
- survive 1.0
- tailwind 1.05
- confidence ~0.964
- edge ~1.223
- resulting potential score: **51**

Thus the pre-existing edge remained almost the same. The major change was the cycle/entry timing state.

This matters causally because Prophet admission refuses `band == low` and refuses non-admitted entry statuses. On Sep 24 NVDA was low/extended. On Sep 25 it was constructive/partial.

### T2 is not itself the sole admission cause

T3 is already an allowed T1–T3 tier in the anticipation-era plan selector. Therefore the T3→T2 transition was **not by itself necessary** to originate a plan.

The truly load-bearing changes for plan admission were:

- conviction band: `low -> constructive`;
- entry status: `extended -> partial`;
- the associated cycle state becoming an open/half-size entry instead of a do-not-chase state.

The T2 confirmation strengthened the NOW state and guaranteed confluence consistency, but “T2 = cause” is too simplistic.

---

## 2. Exact C1 attribution: NVDA was an overdetermined evidence case

On the Sep-25 buy pool, NVDA's live `us_prophet_v3` C1 fusion score was **80.5**, rank **#1**.

Five evidence families voted:

| Family | NVDA family score |
|---|---:|
| F1 Technical Confluence | 71.59 |
| F2 Momentum / Extension | 68.84 |
| F4 Catalyst / Event | 93.48 |
| F5 Flow / Positioning | 69.93 |
| F8 Attention / Crowding | 98.55 |

The final score is the equal-weight mean of these present family scores.

Exact member percentiles carried by NVDA included:

- `tier_cascade`: 0.715909
- `alpha`: 0.434783
- `off_high`: 0.942029
- `sue_fresh`: 0.934783
- `insider_cluster`: 0.463768
- `smartmoney_add`: 0.934783
- `news_burst`: 0.985507

### Important non-attribution

F3 Theme Structure, F6 Macro Regime and F7 Quality/Fundamental **abstained** in the canonical C1 ranking that night.

NVDA did have strong AI/Mag7 context on display surfaces, but that context cannot honestly be claimed as the cause of its 80.5 canonical rank.

### Leave-one-family-out result

Removing any one family from the entire Sep-25 board and recomputing the same stage-aware order leaves NVDA at **rank #1**.

One-family-only diagnostic:

- F1 technical alone -> rank #6
- F2 momentum/extension alone -> rank #6
- F4 catalyst alone -> rank #1
- F5 flow alone -> rank #4
- F8 attention alone -> rank #1

Two-family diagnostics are similarly strong: most pairings keep NVDA top 1–4.

Dropping any two or even three of the five active families still leaves NVDA inside the top five.

### Ruling

The #1 rank was **not a one-factor accident**. NVDA was unusually strong across multiple independent evidence budgets.

But ranking and admission must remain separate:

- the family fusion answered **which interesting name rises**;
- the cycle/entry/conviction machinery answered **whether a plan may open**.

---

## 3. The obvious simplifications fail

Using the existing PIT candidate + forward-grade stores:

### Generic T2 is not the edge

At 10 sessions in the matured `us_prophet_v3` candidate history:

- all graded population: ~30.1% positive excess vs SPY
- buy lane: ~29.4%
- buyable: ~31.3%
- T2 buyable: ~29.9%
- live T2: ~22.5%
- confirmation T2: ~23.5%
- fresh confirmation T2 (ticks <=1): ~18.7%

At 21 sessions these generic cohorts are also weak.

Therefore:

> **Do not promote T2, confirmation, partial, or top rank as a standalone “NVDA mechanism.”**

### T3 → T2 transition alone also fails

A daily transition reconstruction over the available matured history found only a handful of T3→T2 events, and those events did not show positive 10d/21d excess.

The golden case is therefore not explained by “anticipation T3 becomes T2” alone.

### Near-high / relative strength alone also fails

Generic T2 rows near prior highs performed worse than the full T2 cohort in the historical board ledger. NVDA's strong `off_high` percentile was useful in its multi-family context, but “near the high” is not a standalone rule.

---

## 4. New discovery: technical confirmation × news/attention ignition

The strongest interaction found in the existing `us_prophet_v3` board ledger is:

> **T2 technical confirmation AND contemporaneous `news_burst`**

This is not a production rule. It is a discovered research hypothesis.

### 5-session results in the v3 era

Among buy-lane rows:

| Cohort | n | Positive excess vs SPY | Mean excess |
|---|---:|---:|---:|
| all buy rows | 1,098 | 34.2% | -1.08% |
| T2 | 327 | 37.9% | -0.57% |
| news burst, any tier | 18 | 66.7% | -0.63% |
| non-T2 + news | 7 | 28.6% | -7.24% |
| **T2 + news** | **11** | **90.9% (10/11)** | **+3.58%** |
| T2 + news + smart-money-add | 7 | 100% (7/7) | +3.70% |

For T2+news versus other T2 buy rows:

- Fisher exact odds ratio ~17.7
- one-sided p ~0.00036
- Wilson interval on the raw 10/11 rate ~62.3%–98.4%

These are discovery statistics, not promotion evidence.

### Repeated-name robustness

The 11 rows include repeated calls. Collapsing to the first T2+news occurrence per ticker:

- 7 unique tickers
- 6/7 positive excess = 85.7%
- mean 5d excess ~+3.82%

The names were TSLA, PG, PRIM, ADM, F, INTC and RKLB.

### Leave-one-out robustness

Removing any single ticker from the 11-row sample leaves the positive-excess rate at roughly 85.7%–100%.

Removing any single date leaves it at roughly 88.9%–100%.

Thus the v3 finding is not being driven solely by one ticker or one date.

### Same-date control

Across the seven v3 dates on which T2+news occurred, the T2+news subgroup beat the same-date T2/no-news cohort in mean excess on every date-level comparison used here.

Average date-level mean-excess advantage was roughly **+5.8 percentage points over five sessions**.

### Regime slices

The effect existed in both observed v3 macro/risk groups:

- Q2: 5/6 positive, mean excess +1.64%; T2/no-news control 39.6%, mean -0.23%
- Q3: 5/5 positive, mean excess +5.91%; control 27.0%, mean -1.95%

It also remained strong in both neutral and pressure rate states.

This argues against one single v3 regime cell explaining the whole result.

---

## 5. But it does not replicate uniformly across older product eras

The exact unchanged T2+news screen was applied to older board eras.

At 5 sessions:

- July `confluence` era: 1/5 positive, mean excess -1.08%
- `us_prophet_v1`: 2/3 positive, mean +0.49%
- `us_prophet_v3`: 10/11 positive, mean +3.58%

At 10 sessions, the v3 advantage weakens:

- T2+news: 5/10 positive, mean +0.84%
- T2/no-news: ~28.7% positive, mean -2.82%
- Fisher one-sided p ~0.136

### Ruling

The interaction is **not a timeless universal law**.

The current evidence supports a more specific hypothesis:

> In the current v3 population/market construction, fresh technical confirmation combined with a fresh attention/catalyst event may identify short-horizon ignition / follow-through much better than either signal alone.

Possible reasons the earlier era differs include:

- candidate-population changes;
- different board/ranking definitions;
- market/regime changes;
- coverage / semantics changes in the event evidence;
- real conditionality.

This is exactly why a conditional model is preferable to hard-coding a global AND rule.

---

## 6. The interaction appears short-horizon, not yet a durable-leader predictor

The impressive evidence is concentrated at five sessions.

At 10 sessions:

- T2+news positive excess: 50%
- mean excess: +0.84%
- still better than the T2/no-news cohort, but much less decisive.

At 21 sessions only one v3 T2+news episode is matured, so no inference is possible.

Therefore the golden NVDA case currently teaches us more about **ignition** than about **persistent leadership**.

NVDA's later durable leadership must not be retroactively attributed to the same five-session interaction until longer-horizon evidence exists.

This implies at least two separate research heads:

1. **Ignition / immediate follow-through**
2. **Leadership persistence / durability**

A single scalar should not answer both.

---

## 7. Precision is promising; recall is tiny

The T2+news signature is narrow.

Within the v3 5d buy-board history:

- T2+news: 90.9% positive-excess precision
- but it captures only ~2.7% of all positive-excess buy-board rows
- and ~4.2% of date-relative top-decile buy-board winners

T2+news+smart-money-add raises observed precision further in this tiny sample but reduces recall again.

Broadening to T1-or-T2 + news:

- 80% positive-excess precision
- does not materially improve top-decile winner recall in this sample.

### Product implication

There is no evidence that one narrow extracted rule can simultaneously deliver:

- very high precision;
- broad winner capture;
- early lead time;
- durable-leader persistence.

The route to both higher precision **and** higher recall is a multi-stage product:

### A. Broad emergence / research-attention head

Search the whole candidate universe for names whose evidence is becoming unusually interesting, including names not yet on the published action board.

This head is allowed to surface blocked / not-yet-enterable names for research attention.

### B. Ignition head

Estimate whether a currently emerging name is entering a short-horizon follow-through state, with explicit interactions such as:

- technical confirmation × attention burst;
- technical confirmation × catalyst freshness;
- catalyst × attention;
- technical × catalyst × flow;
- regime/setup routing of the above.

### C. Durability / leadership-persistence head

Separately estimate whether the ignition is likely to become a multi-week/month leader.

This needs group/theme leadership, RS persistence, revision breadth, price-volume sponsorship, and other durable evidence — not merely the five-day ignition signature.

### D. Entry Availability remains deterministic and separate

A high ignition/persistence score must never waive a stale quote, extension/chase block, invalidation, blackout, or strategy-specific Entry Availability verdict.

This preserves the R6/V4 separation between “important opportunity” and “enterable now.”

---

## 8. Why earlier detection requires a pre-board plane

Historical T2+news winners often had no board row on the immediately preceding session.

That means “look at yesterday's board one day earlier” is structurally insufficient for increasing recall.

NVDA was unusually visible beforehand: Sep-24 already showed strong underlying evidence but a WAIT/extended state.

For many other eventual T2+news winners, the predecessor needs to be found in the **full point-in-time candidate / emergence plane**, not the published board.

Therefore earlier detection should be built as:

> full-universe emergence -> research attention -> ignition confirmation -> deterministic entry availability

not:

> relax the current board's action gate.

This is a central design distinction.

---

## 9. The existing Conditional Fusion architecture is the correct owner

The current C1 ranker is explicitly:

- one equal-weight vote per evidence family;
- no interactions;
- no outcome-fitted weights.

The existing masterplan already reserves:

- **C2:** regularized fitted linear baseline;
- **C3:** nonlinear date-grouped ranker to test interactions;
- **C4:** context-dependent mixture/router using regime, setup species, liquidity, catalyst proximity, crowding, etc.;
- **C5:** separate Selection / Asymmetry / Entry / Fragility heads.

The NVDA finding is therefore **new evidence for the existing C3/C4/C5 thesis**, not grounds for a new subsystem.

### Current blocker remains real

The registered fold law requires:

- minimum 60 train dates;
- minimum 10 test dates;
- 3 folds;
- embargo at least the longest label horizon.

The current graded-board frame contains only **48 distinct dates** through its matured history.

With a 21-session embargo, the rough minimum frame depth is 111 distinct dates.

Current usable folds: **0**.

Therefore C2/C3/C4 cannot lawfully be fit/promoted on this frame today.

---

## 10. What should be frozen now

### H-IGNITION-1 — primary prospective discovery hypothesis

**Research-only / zero authority.**

Among the current `us_prophet_v3` population, an F1 technical T2 confirmation occurring with an F8 `news_burst` event predicts stronger **5-session** follow-through than T2 without the event.

This statement is frozen **after discovery**, so all existing rows are discovery data. Only future rows may provide confirmatory evidence.

Primary future measurements:

- P(excess_spy > 0) at H=5;
- mean and median excess;
- MFE and MDD;
- same-date T2/no-news matched difference;
- date-blocked uncertainty;
- top-decile precision and capture;
- repeated ticker episodes collapsed / clustered;
- beta/vol/size-neutralized sensitivity where available.

### Secondary hypotheses

Keep secondary and do not threshold-shop:

- F1 × F8 × F5 flow/positioning;
- F1 × F4 catalyst × F8;
- regime-routed F1×F8;
- whether F8 is positive ignition evidence early but negative crowding evidence after extension.

### Kill/fail criteria

The interaction should be killed or downgraded if future evidence shows:

- the v3 effect collapses outside the discovery sample;
- same-date matched advantage disappears;
- one sector/theme explains the result;
- drawdown cost offsets the hit-rate improvement;
- positive evidence exists only at H=5 but the product claim is durable leadership;
- data semantics/coverage changes explain the era split;
- a simpler main effect performs equivalently.

---

## 11. What should NOT be changed from this golden case

Do **not**:

- hard-code “T2 + news = buy”;
- promote news burst to standalone authority;
- increase T2 weight globally;
- credit theme/fundamental families that abstained on the actual Sep-25 rank;
- fit C3/C4 on 11 events;
- weaken Entry Availability to increase recall;
- use the raw 90.9% as an expected live win rate;
- train on future-winner-conditioned cohorts.

The evidence is strong enough to justify a research program, not a production shortcut.

---

## 12. Reproducibility assessment

### High confidence

- The **mechanical recommendation path** is reproducible: the same code path will produce the same state changes when equivalent PIT inputs occur.
- The NVDA plan was produced by a linked system, not hindsight.
- No single C1 family was necessary for its #1 rank.
- The Sep-24→Sep-25 timing transition was load-bearing for plan admission.
- Generic T2 / generic confirmation are insufficient explanations.

### Moderate-to-high research confidence

- A real current-era short-horizon interaction exists between technical confirmation and attention/catalyst ignition.
- The effect is strong enough to deserve a preregistered prospective shadow test.

### Low confidence / unproven

- The raw 90.9% discovery win rate will persist.
- The same interaction predicts 21–63 session durable leaders.
- One narrow rule can materially improve both precision and winner recall.
- The older-era failure is fully explained by product/regime differences.

---

## 13. Recommended Prophet upgrade path

1. **Preserve the incumbent NVDA path as a golden regression.**
2. **Add an outcome-free per-episode decision graph receipt** so every future winner can be decomposed into:
   - emergence evidence;
   - family contributions;
   - interaction candidates;
   - conviction transition;
   - entry transition;
   - availability state.
3. **Start prospective H-IGNITION-1 shadow accrual immediately** under the existing Conditional Fusion evaluation owner.
4. **Back-reconstruct only PIT-lawful F1/F4/F8/F5 evidence** on deeper history as stress evidence. Tag all reconstruction and survivorship limits. It cannot by itself promote.
5. **Accelerate the full-universe emergence plane** because board-only history cannot deliver earlier recall for names absent the prior session.
6. **Keep the ignition head separate from the durability head.**
7. **Advance C3/C4 only when the registered fold law becomes satisfiable or a separately preregistered, lawfully deeper frame exists.**
8. **Race the interaction-aware challenger on product metrics**, especially P@5/top-k excess, large-winner capture, large-loser rate and lead time.
9. **Require NVDA Sep winner + NVDA Aug weaker case + matched false positives** in the acceptance fixture suite.
10. **Do not alter production rank or entry authority from this study alone.**

## Bottom line

The golden case is valuable precisely because it reveals a **mechanism link**:

> **strong multi-family opportunity substrate + a sharp timing-state unlock + interaction-rich catalyst/attention context + deterministic entry geometry**

The most promising exploitable discovery is **not a single signal**. It is that the current equal-weight Prophet can see the ingredients, but it does not explicitly model the nonlinear interaction between them.

That is where the next generation of Prophet should become smarter.
