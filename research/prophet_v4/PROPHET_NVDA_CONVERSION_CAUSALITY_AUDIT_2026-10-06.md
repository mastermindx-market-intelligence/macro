# Prophet NVDA Golden-Episode + Conversion-Causality Audit

**Date:** 2026-10-06  
**Scope:** US Prophet, September 2026 NVDA episode, plan-conversion hypothesis, management replay integrity  
**Authority:** research / evaluation only; **no rank, gate, size, trade, or production-control authority**  
**Source pin:** `mastermindx-market-intelligence/macro@2f2feec4851b45636f63a48ec61e6f0b02b8118a`  
**Protected procedure pin:** `mastermindx-market-intelligence/Mastermind@877b1e7f275da0b6d3558d2667778b32d628bf67`

## Executive ruling

The September NVDA call is a real Prophet success and is suitable as a **golden regression episode**, but the current evidence does **not** license the claim that Prophet's plan-conversion policy itself is already proven causal alpha.

Three distinct claims must remain separate:

1. **Ranking / emergence discrimination:** supported directionally at the very top of the board, but not monotonically across the whole scored lane.
2. **Conversion / entry-policy incremental value:** not yet causally identified in the persisted graded cohort because the converted-to-plan exposure is not stamped into the same point-in-time candidate/grade rows.
3. **NVDA management replay fidelity:** materially defective during the winning episode. The plan was early, but the management state lagged the tape and stamped the first trigger later than the market actually crossed it.

The correct product decision is therefore:

- preserve the incumbent behavior that produced the Sep NVDA episode;
- do **not** promote new score/rank authority from this audit;
- register NVDA Sep 2026 as a golden case plus negative controls;
- close the conversion-causality identification gap inside the existing evaluation owner;
- repair management freshness/replay under the existing Prophet owner, without creating a second state/control plane.

---

## 1. The September NVDA episode is genuine, not hindsight

The frozen plan `site/prophet/plans/NVDA-BULL-20260917.json` records:

- signal date: 2026-09-25
- tier: T2
- selection era: `anticipation-v1-2026-08-08`
- admission class: confirmation
- entry basis date: 2026-09-25
- entry: about 225.10
- trigger: 226.90
- invalidation: 184.10
- targets: about 286.60 / 348.10
- priority score: 80.5
- entry state during the completed session: partial / accumulate zone

Independent persisted evidence shows the plan was actually surfaced on Sep 25, not reconstructed after the run:

- the marketing radar emitted `radar-prophet-NVDA-2026-09-25` from `site/prophet/index.json`;
- the watchlist alert ledger emitted a Sep-25 `buy_zone_enter` event for NVDA;
- the dossier signal history shows the progression from Sep-14 cycle low, Sep-17 3D stochastic turn, Sep-18 BUY ZONE, Sep-22 relative-strength leadership / positive daily MACD, and Sep-25 renewed BUY SETUP.

The state evolved during the session: an early Sep-25 alert saw `buy_now/T1`; the final frozen plan ended as `partial/T2`. That is useful provenance, not a contradiction: it proves the signal path was live and stateful.

### Negative control

The earlier plan `NVDA-BULL-20260805` is an important control. It had materially weaker setup quality and did not produce the same continuation. Prophet therefore was not merely permanently bullish NVDA; the September configuration was meaningfully different from the August episode.

**Acceptance implication:** R6/V4 must be tested against both the Sep winner and the Aug weaker control. A successor that only reproduces the winner after seeing the outcome is not acceptable.

---

## 2. What the live mechanism can legitimately be credited for

The production path that created the September episode is the pre-R6 anticipation system, not the later V4/R6 architecture.

The live US path separates:

- confluence / signal tier;
- entry state;
- residual / relative edge;
- extension / anti-chase;
- coiled / washout context;
- stage / grouping;
- downstream plan admission.

The important entry doctrine is already explicit in code:

- conviction answers “is it worth owning?”;
- entry status answers “should it be bought now?”;
- T1/T2/T3 are actionable while T4 is excluded;
- T2 is ranked as the best cascade entry quality;
- `buy_now` and `partial` are confirmation admission;
- patience statuses such as `bounce_wait` / `wait_pullback` / `hold` are handled separately;
- anti-chase and structure-anchored zones are designed to avoid paying a late print.

The Sep NVDA episode therefore supports the hypothesis that useful behavior came from a **transition sequence** rather than from one scalar score:

> early emergence -> fresh confluence -> relative-strength transition -> bounded entry availability -> anti-chase geometry -> continuation.

That is the behavior the golden regression must preserve.

---

## 3. Ranking evidence: useful at the very top, not a universal alpha proof

The current `priority_score_scorecard` joins the zero-authority candidate store to the forward-grade store.

Coverage:

- 51,974 graded candidate rows
- 22 stamp dates at 10d
- 1,875 rows with a non-null Prophet priority score
- score coverage: 3.61%, because the score exists only on the buy/scored lane

At 10 sessions:

- full-population mean excess vs SPY: **-2.168%**
- buy-lane mean excess vs SPY: **-2.468%**
- buy-lane positive-excess rate: **30.84%**
- rank IC: **+0.0407** across 22 dates
- P@1: **59.1%** vs base **47.2%** -> **+11.9 pp lift**
- P@5: **55.5%** -> **+8.3 pp**
- P@10: **57.7%** -> **+10.6 pp**
- P@25: **48.2%** -> only **+1.0 pp**

The deciles are not cleanly monotonic. The top-minus-bottom mean-excess spread is not robustly positive.

At 21 sessions:

- rank IC rises to **+0.1139** over 13 dates;
- P@1 falls to **46.2%** vs base **44.7%**;
- P@5 is **52.3%**, +7.6 pp vs base;
- the buy lane as a whole still has negative mean excess.

### Ruling

The scorecard says:

- **top-of-list discrimination exists directionally**;
- the scalar priority score is **not** a universal monotone alpha function;
- the buy lane as a whole was not a clean SPY-beating portfolio in this sample;
- NVDA cannot be explained by “priority score 80.5 was simply a proven high-return score.”

This strengthens the need to study the **conversion / state-transition policy** rather than over-credit the scalar.

---

## 4. Entry-status evidence does not justify post-hoc “buy-now was the alpha” claims

The existing `entry_status_scorecard` is a useful guardrail because it measures legacy board admissions by entry status.

For the BUY cohort:

### 5d

- `buy_now`: n=236, win rate 47.88%, median excess -0.172%
- `partial`: n=380, win rate 39.47%, median excess -1.260%
- `buy_soon`: n=189, win rate 46.03%, median excess -0.492%
- `wait_pullback`: n=113, win rate 44.25%, median excess -0.291%
- `extended`: n=171, win rate 50.88%, median excess +0.085%
- `blocked`: n=85, win rate 30.59%, median excess -1.068%

### 10d

- `buy_now`: n=179, win 32.96%, median excess -2.658%
- `partial`: n=326, win 33.74%, median excess -2.539%
- `buy_soon`: n=121, win 42.15%, median excess -1.112%
- `wait_pullback`: n=74, win 45.95%, median excess -0.748%
- `await_confluence`: n=156, win 46.79%, median excess -0.735%
- `blocked`: n=67, win 23.88%, median excess -2.527%

### 21d

- `buy_now`: n=129, win 31.01%, median excess -4.718%
- `partial`: n=256, win 28.12%, median excess -4.231%
- `wait_pullback`: n=59, win 35.59%, median excess -2.689%
- `await_confluence`: n=135, win 38.52%, median excess -3.333%
- `extended`: n=96, win 39.58%, median excess -2.088%

These cells mix vintages, selection eras, and old price bases. The scorecard itself explicitly says the differential entry-status ordering has **no authority** and the entry-value map remains neutral unless its preregistered bar is met.

### Ruling

Do not tell the story that NVDA proves `buy_now` or `partial` is globally superior. The broad historical status table does not support that. The likely edge, if real, is more conditional: **specific transition geometry under a particular setup/regime**, not a universal status label.

---

## 5. Why the 24/121 “converted runner” number is not a causal study

The miss audit reports:

- 121 top-runner names were “sighted”;
- 24 converted into Prophet plans;
- conversion rate 19.83%;
- NVDA is one of the converted names.

This is operationally interesting but statistically unsafe as a conversion-effect estimate.

The 121-name denominator is selected using future realized performance (the top 63-day runner population). Conditioning on future winners before comparing converted vs unconverted creates survivor / collider bias.

Therefore the following comparison is **forbidden** as a promotion argument:

> future top runners that converted vs future top runners that did not convert.

It answers “which future winners were converted?” but not “did conversion select better future outcomes at decision time?”

---

## 6. The conversion-causality question is presently not fully identifiable

The correct causal cohort must be formed **before** future outcomes are known.

The existing point-in-time candidate and forward-grade stores are the right substrate, but the current persisted scorecard does not stamp a direct `converted_to_plan` exposure into each candidate/grade row.

That means the exact desired comparison cannot be reproduced from the published aggregate telemetry alone without reconstructing plan origination from the existing plan records.

This is an **evaluation instrumentation gap**, not a reason to create a new data/control plane.

### Correct exposure

For each point-in-time candidate episode, derive using existing records:

- whether a plan was originated;
- exact plan id;
- origination decision cut;
- selection era;
- admission class;
- entry status;
- signal tier;
- zone class;
- first eligible / conversion lag where applicable.

This must be joined only using facts knowable at or before the decision cut.

---

## 7. Preregistered conversion study

### Unit

Primary unit: point-in-time candidate episode / first eligible admission opportunity, not future winner and not every duplicate nightly echo.

Secondary robustness unit: candidate-day with ticker/date clustering.

### Treatment

`converted = 1` iff an actual Prophet plan was originated from the episode at that decision cut under the incumbent selection era.

### Controls

Eligible / sighted episodes that did not convert, with no future-outcome filtering.

### Matching / adjustment

At minimum match or stratify by:

- stamp date / market regime;
- sector or theme family;
- signal tier;
- entry status;
- stage;
- priority-score decile when available;
- extension / anti-chase state;
- liquidity / price basis;
- selection era.

Do not match on any feature first observed after the conversion decision.

### Outcomes

Use existing graders where possible:

- 5d / 10d / 21d / 42d / 63d return;
- excess vs SPY;
- sector-relative excess where PIT sector benchmark exists;
- forward MFE;
- forward MDD / MAE;
- probability of becoming a top cross-sectional runner;
- persistence of relative-strength leadership;
- target / invalidation competing-risk outcomes where the existing plan outcome ledger supports them.

### Estimands

Report:

1. raw converted-minus-control difference;
2. same-date / same-sector matched difference;
3. doubly robust / regression-adjusted difference only if sample size supports it;
4. selection lift at P@k;
5. effect heterogeneity by T tier, entry status, extension state, and score bucket.

### Uncertainty

- cluster by date;
- cluster or block by ticker for repeated episodes;
- use time-ordered folds / era splits;
- disclose thin cells;
- no random shuffled CV;
- no threshold selection on the final holdout.

### Kill conditions

Conversion-policy alpha is **not proven** if:

- the sign fails across time halves;
- effect disappears under same-date / same-sector matching;
- benefit is driven by one ticker or one theme;
- the converted group wins only by taking materially worse drawdown;
- outcome lift exists only in the future-winner-conditioned sample;
- the result depends on post-decision features;
- confidence intervals remain too wide for the claimed authority.

---

## 8. Golden regression suite

### Golden positive: NVDA Sep 2026

Required replay:

1. Sep-14 cycle low / emerging episode recognized without future knowledge.
2. Sep-17 oversold turn preserved.
3. Sep-18 BUY ZONE / early availability preserved.
4. Sep-22 RS-leadership transition preserved.
5. Sep-25 plan origination preserved or any intentional successor deviation explained by stronger PIT evidence.
6. Anti-chase / structure zone prevents a late-price interpretation.
7. Trigger crossing is stamped on the first actual eligible bar.
8. MFE/MAE and T1/T2 timestamps replay from intervening bars, not from catch-up run date.
9. By the current date, the episode can move to ran/hold without being presented as a fresh chase.

### Negative control: NVDA Aug 2026

R6/V4 must not blindly force the Sep interpretation onto the earlier weaker episode.

### Matched false-positive controls

Select at least:

- one same-sector high-score episode that failed;
- one T2 confirmation that failed;
- one `partial` confirmation that failed;
- one anti-chase veto that correctly withheld entry;
- one unconverted sighting that later became a leader, to measure missed-opportunity cost.

A successor passes only if it improves aggregate evidence without overfitting these named examples.

---

## 9. Management replay defect: confirmed architectural cause

The Sep plan trigger is 226.90.

The persisted market sequence crossed that threshold before the management state acknowledged it. Historical state snapshots remained `pre_trigger` through Sep-28 and Sep-30 while still effectively priced from the Sep-25 close, then changed to `triggered_pre_t1` on Oct-1 and stamped `_first_trigger_ts = 2026-10-01`.

The code explains why:

- `price_frame_freshness()` treats a management frame as current until lag is **greater than 3 business days**;
- management evaluates only the last supplied close;
- `_first_trigger_ts`, `_first_t1_ts`, `_first_t2_ts`, MFE, and MAE are accumulated from prior state;
- when a later run sees the level crossed, it stamps the current `asof`, not the historical missing bar that first crossed it;
- there is no automatic replay of skipped intervening bars before state accumulation.

So the winning plan was real, but the management telemetry lagged and then misdated the first trigger.

### Severity

**High for trust / evaluation integrity; lower for original selection validity.**

The defect does not erase the Sep-25 recommendation. It does contaminate:

- first-cross timestamps;
- phase chronology;
- MFE/MAE path telemetry;
- pace / management confidence history;
- any study that treats those state timestamps as market-event truth.

---

## 10. Required management repair contract

Repair in the existing Prophet management owner; do not create another state machine.

### A. Active-plan freshness

For an actively managed plan, a prior-session close must not remain action-current merely because it is within a generic 3-business-day tolerance.

At minimum:

- expose exact `last_close_date`;
- refuse current action when the required regular-session bar is missing;
- distinguish market holiday / halt / true no-session from feed lag using the existing market-clock owner.

The origination tolerance and active-management tolerance may be different policies, but they must remain one canonical freshness contract rather than duplicated detectors.

### B. Ordered bar replay

When the feed catches up after missing one or more sessions:

- replay unseen bars strictly in timestamp order;
- update trigger/T1/T2 crossings on the first crossing bar;
- accumulate MFE/MAE across every replayed bar;
- never stamp the catch-up run date when an earlier missing bar established the event;
- never read bars after the requested decision cut.

### C. Idempotency

Replaying the same caught-up bar set twice must not change:

- first trigger timestamp;
- first T1/T2 timestamp;
- MFE/MAE;
- phase history.

### D. Historical regression fixture

Pin the NVDA Sep-25 -> Sep-28 -> Sep-30 -> Oct-1 sequence as a regression.

Expected:

- trigger date = the first bar that actually crosses 226.90;
- management state cannot remain current-looking on stale Sep-25 tape;
- catch-up on Oct-1 cannot rewrite the first-cross date to Oct-1.

---

## 11. R6 / V4 acceptance ruling

R6 cannot take credit for this hit because the plan is stamped `selection_era: anticipation-v1-2026-08-08`.

R6/V4 should instead consume the episode as **incumbent behavior to beat without breaking**.

Minimum acceptance:

- preserve / explain the Sep positive case;
- preserve / explain the Aug negative control;
- add per-family contribution provenance so an 80.5 priority score can be audited without post-hoc storytelling;
- prove the new lifecycle / availability architecture does not erase the early-emergence -> confirmation -> availability path;
- require current-session management truth and replay-correct event timestamps;
- compare successor policy against incumbent on the full PIT cohort, not hand-picked wins.

---

## 12. Current decision

### Proven now

- Sep NVDA was a real, timely Prophet recommendation.
- Prophet showed useful top-of-list discrimination in the measured 10d scorecard.
- The score itself is not globally monotonic alpha.
- Historical entry-status labels alone do not explain the hit.
- The 24/121 future-runner conversion statistic is not a valid causal estimate.
- Management replay/freshness was wrong during the winning episode.

### Not proven now

- that plan conversion itself adds causal alpha;
- that `buy_now` / `partial` universally outperform patience statuses;
- that AI/Semiconductor theme context caused the Sep plan unless the contemporaneous scored-family provenance shows it;
- that R6 improves the incumbent;
- that current options premium equals net common-equity inflow.

### Exact next implementation/evaluation steps

1. add a **read-only derived conversion label** to the existing evaluation join using incumbent plan records;
2. run the preregistered full-cohort matched study;
3. register NVDA Sep + Aug + matched false-positive controls as R6 acceptance fixtures;
4. repair active-plan freshness + ordered bar replay in the existing management owner;
5. rerun the conversion study after replay-corrected state timestamps where management-derived outcomes are used;
6. keep all resulting authority at zero until held-out / forward evidence passes existing promotion law.

No live score/rank/gate/trade change is justified by this audit alone.
