# Prophet Ignition-Convergence Prospective Pre-Registration

**Date frozen:** 2026-10-06  
**Program owner:** existing `WS:PROPHET-CONDITIONAL-FUSION` evaluation lane  
**Authority:** ZERO — research / shadow accrual only  
**Production effect:** NONE  
**Discovery source:** PR #8495 / `PROPHET_NVDA_PRO_REAUDIT_2026-10-06.md`  
**Historical discovery cutoff:** all observations on or before 2026-09-17 are discovery data. NVDA Sep-2026 is golden-case corroboration, not confirmatory evidence.

## 0. Purpose

Freeze a falsifiable prospective test of the strongest mechanism discovered in the NVDA golden-case study:

> **H-IGNITION-CONVERGENCE:** a fresh T2 technical acceptance event has materially higher short-horizon follow-through when at least two independent, point-in-time-valid rerating evidence families are concurrently active.

This document does **not** grant the interaction rank, score, gate, alert, Entry Availability, plan-origination, sizing, trading or promotion authority.

No historical outcome may be re-labelled as confirmatory after this freeze.

---

# 1. Why this hypothesis and not the earlier T2+news rule

The discovery study falsified simpler stories:

- T2 alone was weak;
- one evidence leg alone was weak;
- T1 + multiple evidence legs was weak in the observed sample;
- a broad OR across news/SUE/smart-money was weak;
- news alone was not the stable causal category;
- NVDA's own `news_burst` was neutral-sentiment attention, not bullish news.

The historical v3 discovery seed was more specific:

- T2 + >=2 independent evidence legs: 10/12 H5 rows positive vs SPY;
- first T2 per ticker: 5/5 positive vs SPY and sector, 4/5 positive absolute;
- same-date mean excess advantage vs other T2 rows on all 7 observed dates.

Because this was discovered after outcome inspection, none of those values count toward confirmation.

---


# 1.1 Reconciliation with the 2026-10-04 timeframe/grain program

A concurrent Prophet timeframe study now on main reports:

- standalone 3D grain effect: **NOT SUPPORTED** at cost-adjusted SPY-excess H10 after matching elapsed memory;
- standalone 2D grain effect: **NOT SUPPORTED**;
- matched-memory effect: **NOT SUPPORTED**;
- C2 regime-conditioned grain: **INSUFFICIENT SUPPORT** because the upstream rotation-state control is BROKEN; its counterfactual is separately NOT SUPPORTED.

This is **not contradictory evidence** to H-IGNITION-CONVERGENCE, because the hypotheses differ materially:

- the timeframe program asks whether bar grain / slower confirmation itself improves H10 outcomes over matched-memory controls across a broad final-vintage survivor-selected panel;
- H-IGNITION-CONVERGENCE asks whether the existing **specific T2 state interacts with independently sourced rerating evidence** to improve short-horizon H5 follow-through in a PIT-serving context.

The new result strengthens two fences:

1. this preregistration must never claim “T2/2D/3D confirmation is alpha by itself”;
2. the confirmatory comparison must be **T2 + convergence versus same-date T2 without convergence**, not T2 versus generic lower-frequency signals.

If the prospective interaction does not outperform same-state controls, the hypothesis fails even if T2 looks good unconditionally.

The timeframe study's B1 label is a research-lane identifier (“grain vs memory”), **not** the R6 B1 `prophet.candidate_episode/v1` owner. Do not conflate the two B1s in implementation or records.

Evidence-level caveat on the concurrent study remains binding: final-vintage prices and survivor-selected universe. Its null is still decisive for the construction it tested and must be preserved as a negative control.

---

# 2. Unit of account

Primary unit:

> **one unique T2 ignition episode for one ticker**

A T2 episode begins on the first decision cut at which the ticker enters a fresh T2 event after not being in that same T2 episode.

Required episode identity must include:

- ticker;
- `tier_event_date`;
- `tier_observed_date`;
- signal anchor era;
- board definition;
- selection era.

Nightly echoes of the same T2 event are **not independent observations**.

If the historical candidate store lacks sufficient episode identity, do not infer it from future prices. Accrue the required identity prospectively through the existing evaluation owner.

---

# 3. Exposure definition

## 3.1 Technical leg

Primary technical state is the incumbent T2 construction, unchanged:

- recent 3D StochRSI cross;
- fresh 2D RSI-MACD cross;
- constructive confirmation context;
- RSI buy ceiling;
- not-topped veto;
- incumbent freshness window.

No threshold in the technical leg may be retuned for this experiment.

## 3.2 Independent evidence families

An episode is `convergence_2plus=true` only when **at least two independent evidence families** are valid and active at the decision cut.

Independence is by evidence family / upstream fact, not article count.

Initial registered families:

### A. Attention / information-arrival

Examples:

- unusual news / information burst;
- abnormal attention arrival.

Direction-neutral. A burst means “something is being repriced / discussed,” not “bullish.”

Must carry:

- source;
- known-at / capture time;
- event identity or cluster identity;
- duplicate-cluster control.

### B. Positive earnings / revisions

Must be directionally positive **and carry a real point-in-time availability clock**.

Eligible examples:

- positive SUE / earnings surprise with the actual filing / release known-at timestamp;
- upward estimate revision acceleration with the collector's decision-time snapshot;
- guidance raise;
- positive KPI revision.

Legacy `sue_fresh = bool(nonzero z)` is **not** sufficient serving semantics for this prospective exposure.

Nor is legacy `sue_fresh_days` a valid event-arrival clock: the current producer documents that the EPS panel uses a synthetic `period_end + 60 days` `asof_date` because the real filing date is absent. Until a true filing/release availability timestamp is carried, SUE may be contextual evidence but **must not count as a timed ignition-arrival leg** in the prospective primary exposure.

### C. Ownership / positioning accumulation

Eligible only where direction and knowability are explicit:

- A/B-grade `new` / `add` ownership;
- other registered accumulation evidence with a point-in-time availability clock.

Must carry staleness / filing-period age.

A stale 13F may qualify as context only if the registered family explicitly allows that age; it must never be presented as current flow.

## 3.3 Not in the primary exposure yet

The following may accrue as typed secondary evidence but do not silently enter `convergence_2plus` until separately registered:

- analyst upgrade / price-target clusters;
- peer/customer/supplier read-through;
- sector pricing / capacity / inventory;
- hyperscaler capex / procurement;
- contracts / policy;
- theme / group rerating;
- options / dealer positioning;
- insider evidence;
- alternative data.

They are important candidates for the broader rerating ontology, but adding a new family after seeing its outcomes would invalidate the frozen primary test.

---

# 4. Control groups

Primary control:

> T2 episodes with **0 or 1** registered active evidence families on the same dates.

Secondary controls:

1. T2 with zero registered evidence legs;
2. T2 with exactly one registered leg;
3. T1 with >=2 registered legs;
4. non-T2 buyable episodes with >=2 registered legs;
5. high-C1-score T2 episodes without convergence;
6. same-sector / same-date controls where sample permits.

Controls must use identical outcome clocks and availability rules.

---

# 5. Primary outcome and horizon

Primary horizon: **5 trading sessions** after the episode decision cut.

Co-primary reads:

1. positive excess return vs SPY;
2. mean excess return vs SPY.

Mandatory companion reads:

- absolute return;
- sector-relative excess;
- MFE;
- MAE / MDD;
- large-loser rate;
- realistic Entry Availability at the episode cut.

The experiment is not allowed to call positive SPY excess a “profitable trade.”

---

# 6. Secondary outcomes

Secondary horizons:

- H10;
- H21 as maturity permits;
- H42 / H63 only when enough prospectively accrued episodes exist.

Secondary questions:

- does the interaction predict only ignition or also durability?;
- does it improve top-decile winner capture?;
- does it improve lead time?;
- does it reduce false starts?;
- how often is a high-ignition episode not enterable at first detection?

No secondary horizon may replace H5 as the primary after outcomes are read.

---

# 7. Entry / publication clocks

Every episode must separately stamp:

1. detection / research-attention time;
2. evidence-arrival known-at time;
3. T2 event time;
4. Entry Availability time/state;
5. board publication time;
6. formal plan publication time, if any;
7. first realistic executable price after each publication;
8. stale / delayed / mixed-vintage state.

A high-quality predictor whose lead time is consumed by stale-data publication is a system failure on a different axis and must be reported separately.

The plan provenance gate is never weakened to improve apparent execution rate.

---

# 8. Prospective confirmation rules

Because the historical discovery is tiny, no production promotion threshold is created here.

This pre-registration asks a narrower question:

> Does the **direction and magnitude** of the T2 × convergence effect survive genuinely future episodes?

Required reporting after sufficient prospective accrual:

- number of unique episodes;
- number of unique tickers;
- number of decision dates;
- positive-excess rate with Wilson interval;
- mean / median excess;
- same-date T2-control difference;
- date-blocked uncertainty;
- ticker-clustered sensitivity;
- leave-one-sector-out;
- leave-one-ticker-out for concentration;
- event-family composition;
- Entry Availability distribution.

Do not repeatedly peek and redefine the exposure.

Any interim read must be explicitly labelled exploratory and must not alter the frozen primary definition.

---

# 9. Falsifiers

H-IGNITION-CONVERGENCE is weakened or killed if any of the following occurs on adequate future data:

- no advantage over same-date T2 controls;
- advantage is driven by one ticker, sector or event species;
- positive relative return comes with materially worse drawdown / large-loser rate;
- effect disappears under issuer-episode deduplication;
- effect exists only in stale / non-executable episodes;
- exposure requires post-decision information;
- one evidence family alone explains the result equally well;
- T1 or generic convergence performs equivalently, removing T2 specificity;
- effect reverses in a sufficiently represented comparable regime;
- source semantics or coverage cannot be made stable enough to define the exposure prospectively.

---

# 10. Durability follow-on

Leadership persistence is a separate head.

Do not use this H5 study to claim 21–63-session leadership.

For episodes that respond positively at H5, accrue a second-stage survival record:

- H5 acceptance state;
- H10 continuation;
- H21 / H42 / H63 continuation as mature;
- loss-of-leadership timestamp;
- RS depth;
- dip recovery;
- group/theme participation;
- revision/catalyst persistence;
- new evidence arrival.

This tests:

> **P(leadership survives | credible ignition already occurred)**

rather than repeating the failed unconditional sector persistence construction.

---

# 11. Integration owner

This experiment belongs inside the existing Conditional Fusion research/evaluation plane:

- C1 remains the incumbent equal-weight interaction-free ranker;
- C3 is the natural nonlinear interaction challenger;
- C4 is the natural context-conditioned challenger;
- C5 is the natural multi-head architecture for Emergence / Ignition / Durability / Fragility.

This pre-registration creates no new ranker, gate, memory store, lifecycle plane, or trading authority.

---

# 12. Emergence / research-attention companion hypothesis

The NVDA case also establishes a distinct upstream research question that is **not** the H5 primary:

> Can Mastermind preserve important unresolved candidates when independent evidence has accumulated but Entry Availability remains closed?

NVDA's first preserved raw-board >=2-evidence watch snapshot is Sep-04; the graded H5 ledger first shows the same pattern on Sep-08/09/10 while `entry_status=await_confluence`. It then reached T1 `buy_now` on Sep-23 and T2 `partial` on Sep-25. Sep-08 is therefore a grading-store boundary, not the beginning of the emergence episode.

Generic watch-lane multi-evidence convergence performed poorly at H5, so this companion head must not be optimized as another immediate-return screen.

Its prospective objectives are instead:

- lead time before eventual ignition;
- later conversion into a valid T1/T2/T3 ignition episode;
- eventual top-decile / leader capture;
- false-attention burden;
- time spent unresolved;
- whether the candidate remains supported by independent evidence;
- whether Entry Availability ever opens.

This companion accrual must use the existing candidate-episode / evaluation owners. It creates no new lifecycle or memory plane.

---

# 13. Current disposition

**Status:** PROSPECTIVE / ZERO AUTHORITY  
**Historical discovery:** suggestive, post-selected, insufficient for promotion  
**NVDA:** golden-case corroboration; excluded from confirmatory count  
**Next lawful action:** accrue prospective episode receipts without changing live behavior.

