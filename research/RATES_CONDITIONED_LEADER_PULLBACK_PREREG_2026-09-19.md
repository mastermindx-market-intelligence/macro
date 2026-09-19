# Rates-Conditioned Leader-Pullback Diagnostic — Registered Before the Rate×Episode Join

**Operation:** `rates-conditioned-leader-pullback-prereg-20260919-sol-001`  
**Parent:** existing Rates & Inflation / Prophet / Live Entry Radar / Evaluation estate; no new program or evaluator.  
**Freeze base:** Macro `6f35b67d4a2655f2e8409406646f88adf852c2b6`.  
**Status:** **REGISTERED DIAGNOSTIC — NO RATE×EPISODE OUTCOMES OPENED UNDER THIS PROTOCOL. NO PROMOTION AUTHORITY.**

This protocol tests the Chairman's actual hypothesis in a bounded way:

> When a structurally strong stock is already offering an early pullback/turn setup, does **tactical easing in rates after prior rate pressure** distinguish durable entries from false starts?

Rates are a **condition**, not an entry trigger. The stock/price trigger and its decision clock remain fixed. The first experiment asks whether rate context adds incremental information to an already-defined opportunity. It does **not** invent a rates-only buy signal, move the entry time after seeing outcomes, or replace existing sector/stock selection.

---

## 0. Prior evidence and do-not-redo boundary

This registration is written after several adjacent results were already known. They are disclosed so this is not misrepresented as untouched confirmatory research.

1. **Generic daily rates add-on:** Research A V4 found no useful aggregate forecast improvement for its tested price baseline + 2y nominal / 10y nominal / 10y real construction. This protocol does not rerun or retune that model.
2. **Naive leader-reset family:** `PROPHET_US_TREND_INTELLIGENCE_MASTERPLAN_BY_FABLE.md §2.5` reports the already-killed construction  
   `RS63≥0.8 AND >50dMA AND fresh 2D cross AND NO veto`: n=938, median excess −1.50%, per-name median −2.12%, win 45.8%. **DO NOT REDO.** Rates may not be used as a cosmetic excuse to resurrect that timer.
3. **Early-turn geometry:** `EARLY_ADMISSION_BAKEOFF_2026-08-11.md` showed C1/C2r/C4 enter materially closer to the trough than the actioned incumbent, but with much higher false-start / stop-out risk. That is the open job: discriminate early opportunities, not merely fire earlier.
4. That bake-off already examined technical/structure/volume/trend/systemic-washout/theme-breadth features. The strongest reported discriminator was `f_k_cross`; theme breadth did not clear its pre-stated bar. This protocol does not search those features again.
5. The underlying price outcomes in the episode artifact have been seen in aggregate. **What remains unopened before this freeze is the exact rates-state × episode join and the statistics defined below.** Therefore this is a registered retrospective diagnostic, not an untouched promotion study. Any authority change requires later untouched/prospective evidence.

---

## 1. Canonical inputs — reuse, do not rebuild

### 1.1 Opportunity episodes

Primary episode source is the already-stored Early Admission episode artifact:

`research/prophet_us_audit/early_admission_bakeoff_episodes.parquet`

The existing study reports 39,877 episode rows. Use the stored rows; do not regenerate or retune the Early Admission study merely to obtain a different population.

**Primary trigger family:** `C2r` (recomputed grey-dot/early-turn family).  
**Secondary trigger family:** `C4` structure-confirm family.  
**Reference only:** the actioned incumbent C0-take may be printed descriptively but is not used to redefine the treatment population.

Episode identity, trigger timestamp, P0, stop geometry, feature snapshot, and outcomes remain the original study's definitions. No rates information may alter those fields.

### 1.2 Structural-strength subgroup

The first study is **stock-leader-like**, not yet a full sector-leader study.

A C2r/C4 episode is `leader_like = true` iff, at the original decision session T:

- `f_above200 == true`, and
- `f_rs63 > 0` (63-session relative strength versus SPY is positive).

This sign-based definition is frozen for interpretability and was conceptually defined before the old bake-off's outcome read. Do **not** choose top terciles or a best cutoff after looking at this experiment.

The complement is `nonleader_like`. It is a falsifier/control stratum, not a claim that those stocks are bad.

**Important:** this does not establish that the stock's *sector* was leading. Sector/theme leadership requires a separately qualified PIT archive and is Stage 2 (§10), not an inferred label added here.

### 1.3 Rates data

Use existing canonical daily rate series only:

- 10y nominal: DGS10 / existing `us10y` owner
- 2y nominal: DGS2 / existing `us2y` owner
- 10y real: DFII10 / existing `us10y_real` owner
- 10y breakeven: T10YIE / existing `breakeven_10y` owner, diagnostic decomposition only

No new collector, cache, curve, receipt DB, or alignment plane.

**Knowledge-clock rule for this retrospective diagnostic:** because historical intraday receipt timestamps are not certified, an episode on session T may use only rate source observations dated **T−1 or earlier**. Same-session Treasury values are excluded from the primary study even if present in current corrected history. This is conservative availability handling, not proof that T−1 was actually the exact production receipt.

Use genuine observed source rows. Do not interpret forward-filled grid rows as new measurements.

---

## 2. Frozen rate-state definitions

Let `d10_5` = 10y nominal change over the last five **observed source sessions** available by T−1, in bp.  
Let `d10_22` = analogous 22-observation change.  
Let `d2_5` = 2y nominal five-observation change.  
Let `dr10_5` = 10y real five-observation change.  
Let `dbe10_5` = 10y breakeven five-observation change.

No daily normalization across weekends/holidays. A Friday→Monday observation change is the total change between those observations.

### Primary state — EASING_AFTER_PRESSURE

`EASING_AFTER_PRESSURE = (d10_22 > 0) AND (d10_5 < 0) AND (dr10_5 <= 0)`

Interpretation: nominal pressure existed over the tactical month, but the latest week has eased and real rates are not worsening.

### Confirmation sensitivity — POLICY_CONFIRMED_RELIEF

`POLICY_CONFIRMED_RELIEF = EASING_AFTER_PRESSURE AND (d2_5 <= 0)`

This is one predeclared sensitivity, not a second primary hypothesis.

### Opposite-state falsifier — REACCELERATION

`REACCELERATION = (d10_22 > 0) AND (d10_5 > 0) AND (dr10_5 >= 0)`

### Magnitude sensitivity

One sensitivity only:

`ABS(d10_5) >= 5 bp`

No threshold optimization is permitted.

### Breakeven decomposition

`dbe10_5` is descriptive only. It may label relief as real-led / inflation-compensation-led / mixed, but it cannot rescue a failed primary result.

**No RSI, StochRSI, MACD, MACD-RSI, Elliott wave, max-pain, gamma/vanna/charm, or options-flow grid is admitted into this first rates experiment.** If simple rate state does not add information at a fixed price trigger, a larger oscillator search is not justified. Any later oscillator mechanism gets its own freeze before outcomes.

---

## 3. Decision unit and pseudo-replication guard

Rates are market-wide on a date. Hundreds of same-day stock episodes are **not hundreds of independent rate observations**.

Therefore:

- inference clusters at **decision date**;
- every table prints unique decision dates as well as episodes/names;
- no p-value/CI may use episode count as if rate treatment varied across names;
- a result with fewer than **30 unique dates** in either compared rate arm is `UNINFORMATIVE`, regardless of episode count.

This date-level law is mandatory.

---

## 4. Primary question

On fixed C2r `leader_like` episodes, does `EASING_AFTER_PRESSURE` reduce the existing bake-off **false-start rate** versus eligible non-relief dates?

The trigger timestamp is unchanged. Rates may classify the episode after its existing trigger is known; they do not move T.

### Primary estimand

For each decision date, compute the leader-like C2r false-start rate using the existing bake-off label.

Compare date-level mean false-start rate:

`EASING_AFTER_PRESSURE` vs all eligible `d10_22 > 0` dates that are not easing.

Report:

- date-level difference in percentage points;
- month-cluster/bootstrap interval;
- N dates, N episodes, N names;
- participation share: fraction of leader-like episodes retained by the easing state.

### Falsifier interaction

For dates with both leader-like and nonleader-like C2r episodes:

`gap_d = false_start_rate(leader_like,d) - false_start_rate(nonleader_like,d)`

Compare `gap_d` on easing vs non-easing pressure dates.

This asks whether rate relief is specifically useful for structurally strong pullbacks rather than merely identifying globally easier markets.

---

## 5. Secondary outcomes — no endpoint moving

Using the **same original episode T and the same original outcome endpoint/definitions**, report:

1. stop-A survival;
2. false-bounce rate;
3. MFE_42;
4. ≥2R-before-stop rate;
5. entry-vs-low and td→trough, as geometry checks only;
6. if the stored artifact already contains a lawful 10-session/21-session return field, print it; otherwise do not silently invent a new endpoint in the grading run.

C4 repeats the same analysis as a secondary trigger family.

A later rate-conditioned *entry-time* comparison is a different experiment. This one tests rates as context at a fixed trigger.

---

## 6. Missingness and population law

An episode is rate-eligible only when all primary rate features have the required observed endpoints by T−1.

- Missing rate endpoint => `RATE_CONTEXT_UNAVAILABLE`, never zero.
- Carried aligned value => may be displayed as stale context, never used as a new observed endpoint.
- Mixed-date nominal/real/breakeven values must disclose their own dates.
- No backfilling from later corrected artifacts into a claimed historical receipt.
- Every exclusion reason is counted.

Run the price/episode baseline on:
1. full eligible episode population,
2. the identical rates-covered subset,
3. then the rate-state split.

This separates **coverage selection** from **rate information**.

---

## 7. Result vocabulary and hurdle

This retrospective diagnostic cannot promote a signal.

For the primary false-start difference:

- **SUPPORTIVE_DIAGNOSTIC:** easing reduces false starts by **≥10 pp**, interval excludes zero in the favorable direction, sign is favorable in both temporal halves, and each arm has ≥30 decision dates.
- **SUGGESTIVE:** reduction ≥5 pp, same sign in both temporal halves, but the stronger hurdle is not met.
- **NULL:** smaller/inconsistent.
- **ADVERSE:** easing cohort is materially worse.
- **UNINFORMATIVE:** date floor, coverage, clock, or data-quality gate fails.

Even `SUPPORTIVE_DIAGNOSTIC` grants **no rank/gate/size/trade authority**. It authorizes only a separately registered prospective/untouched study.

The policy-confirmed sensitivity must agree in sign to strengthen the mechanism; it cannot override a NULL/ADVERSE primary.

---

## 8. Anti-overfit / multiplicity

Closed primary family:

1. C2r leader-like primary false-start difference.
2. C2r leader-vs-nonleader interaction falsifier.

Everything else is secondary/descriptive.

No best tenor, best lookback, best oscillator, best leader threshold, best detector, or best rate magnitude search. C4 is a declared robustness family, not a substitute winner if C2r fails.

Any post-result construction change is a new recorded trial.

---

## 9. What this experiment can and cannot establish

It can answer:

- whether a simple, economically interpretable rates-relief state adds discrimination to an already-defined early-turn opportunity;
- whether that value is stronger in structurally strong names;
- whether the apparent benefit is just coverage or a broad-market effect.

It cannot establish:

- historically exact production knowledge-time;
- intraday rate turning points;
- policy-meeting surprise;
- sector leadership;
- options-flow/dealer incremental value;
- optimal entry price;
- live profitability.

Those remain separate gates.

---

## 10. Staged continuation after this diagnostic

**Stage 1 — this prereg:** stock-level structural strength × fixed early-turn trigger × simple nominal/real-rate context.

**Stage 2 — sector leadership:** only after a PIT-qualified sector/theme leadership archive is admitted. Hold the Stage-1 rate state fixed; test whether a leader in a leading group gets additional lift. Do not reconstruct old sector leadership from today's membership/rank.

**Stage 3 — options incremental value:** on the same frozen opportunity IDs, compare baseline, rates-only, options-coverage-only, then rates+qualified-options. Flow, Package, Positioning and dealer-scenario fields remain distinct. Missing options intervals are not zero.

**Stage 4 — timing model:** only if rates context has incremental value at a fixed trigger. Then preregister whether earlier forming zones can be acted on without increasing false starts/tail loss. Oscillators, rate momentum tops/bottoms and price-time forecasts belong there.

---

## 11. Execution / stop contract

Before running:

1. freeze hashes for this prereg and its machine-readable companion;
2. bind exact episode artifact identity and exact rates-source files/digests;
3. prove no rate×episode result has been opened under this protocol before the freeze;
4. register the trial through the existing Evaluation/TrialLedger owner if that owner admits this study; do not create a parallel ledger;
5. execute once without tuning;
6. publish all cells, coverage exclusions, date Ns and adverse/null results.

**Stop immediately** if the episode artifact cannot supply the frozen leader features/outcomes, if rates endpoints cannot be reconstructed without using future rows, or if an existing owner has an active conflicting registered trial on the same population/question.

---

## 12. Why this is the correct next question

The failed historical lesson is not “leader pullbacks never work.” It is narrower: **a naive leader reset with vetoes removed did not work**, and early triggers buy closer to lows at the cost of many more false starts.

The Chairman's rates thesis gives a specific, orthogonal mechanism for that unresolved tradeoff:

> keep the early price trigger fixed; ask whether easing discount-rate pressure after a prior rate rise separates durable leader pullbacks from knives that are still falling.

That is the experiment frozen here.
