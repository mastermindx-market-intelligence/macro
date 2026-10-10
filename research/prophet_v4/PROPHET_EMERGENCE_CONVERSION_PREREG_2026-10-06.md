# Prophet Emergence / Research-Attention Prospective Pre-Registration

**Date frozen:** 2026-10-06  
**Program owner:** existing Prophet candidate-episode / Conditional Fusion evaluation plane  
**Authority:** ZERO — research / shadow accrual only  
**Production effect:** NONE  
**Discovery source:** PR #8495 / `PROPHET_NVDA_PRO_REAUDIT_2026-10-06.md`  
**Historical discovery cutoff:** observations on or before 2026-09-25 are discovery/golden-case evidence only.

## 0. Purpose

Freeze a distinct prospective test for the **Emergence / Research-Attention** problem.

The target is deliberately **not** five-day return and deliberately **not** immediate trade admission.

Primary hypothesis:

> **H-EMERGENCE-CONVERSION:** among unresolved/non-enterable candidates, point-in-time-valid convergence of multiple independent evidence families identifies a subset with materially higher probability of later valid technical confirmation than ordinary unresolved candidates.

The intended product state is:

> **“Unusually important emerging candidate — entry is not open yet.”**

This state may increase research attention and candidate continuity only.

It must not:

- create a trade plan;
- bypass Entry Availability;
- relax freshness;
- bypass blackout/extension/chase controls;
- change position sizing;
- change canonical buy ranking;
- create a parallel lifecycle or memory plane.

Candidate continuity must remain owned by the existing candidate-episode architecture.

---

# 1. Why a separate emergence head is required

The NVDA golden case showed two different persistence problems:

1. **research persistence** — keep an important unresolved candidate alive while entry is closed;
2. **leadership persistence** — after ignition, estimate whether leadership will survive.

They are not the same model.

Historical NVDA evidence:

- raw preserved watch/emergence state existed by Sep-04;
- T1 `buy_now` arrived Sep-23, about 11 observed board sessions later;
- final T2 partial state arrived Sep-25.

The emergence state therefore produced useful **lead time**, not an immediate H5 buy.

A matched historical reconstruction also showed:

- within 3 sessions, >=2-evidence watch candidates almost never converted;
- within 5 sessions, conversion remained rare;
- around 10-12 observed board sessions, conversion was higher than same-date ordinary watch controls in the small discovery sample.

This motivates a conversion/lead-time objective rather than near-term return.

---

# 2. Unit of account

Primary unit:

> **one emergence episode for one ticker**

An emergence episode begins at the first decision cut where all of the following are true:

1. the candidate is **not currently actionable** under the incumbent Entry Availability / admission owner;
2. the candidate is present in the existing candidate/watch episode plane;
3. at least two **registered independent evidence families** are active;
4. the episode is not already inside the same unresolved emergence episode.

Required identity:

- ticker;
- emergence_episode_id;
- first_emergence_observed_at;
- source board/candidate definition;
- selection era;
- evidence-family identities;
- known-at clocks for each counted family;
- candidate state / lane;
- current technical tier, if any;
- Entry Availability state and refusal reason.

Nightly echoes are not independent episodes.

A candidate remaining important across days must update the same episode, not mint a new one each night.

---

# 3. Exposure definition

## 3.1 Evidence convergence

Primary exposure:

`independent_evidence_families >= 2`

A family counts only if it has:

- direction/semantic definition;
- point-in-time availability;
- source identity;
- duplicate-control semantics;
- explicit staleness.

Initial eligible families may include:

### A. Information / attention arrival

Direction-neutral.

Examples:

- unusual news/information burst;
- abnormal attention acceleration;
- high-confidence new event cluster.

Must not equate article count with independent evidence.

### B. Positive fundamental / estimate rerating

Examples:

- positive earnings surprise with true known-at;
- guidance raise;
- estimate-revision acceleration;
- positive KPI revision.

Legacy `sue_fresh_days` based on synthetic `period_end + 60d` is not sufficient as an event clock.

### C. Ownership / positioning accumulation

Examples:

- directionally explicit institutional `new` / `add`;
- other registered accumulation facts.

Stale 13F remains context unless its age is explicitly allowed by the registered family definition.

### D. Peer / customer / supplier read-through

Only after typed provenance and direction exist.

### E. Sector / industry / theme rerating

Examples:

- pricing/capacity/inventory changes;
- hyperscaler capex acceleration;
- group breadth/leadership rotation;
- industry-specific demand inflection.

Must use group definitions that are stable and point-in-time known.

### F. Policy / contract / external catalyst

Only when event identity and availability are explicit.

## 3.2 Independence

Two observations do not count as two families when they derive from the same upstream fact.

Examples:

- three articles about one earnings release = one information event;
- guidance raise plus an article summarizing the guidance raise = one fundamental event plus one duplicated narrative echo, not two independent families;
- two 13F holders may strengthen one ownership family but do not automatically create two evidence families.

The prospective evaluator must record a family-level evidence graph or duplicate cluster so independence is inspectable.

---

# 4. Primary endpoint

Primary endpoint:

> **conversion to an incumbent valid T1/T2 technical confirmation within 12 observed board sessions after emergence**

Why 12:

- the golden NVDA episode required 11 observed board sessions from the first preserved >=2-evidence watch snapshot to T1 `buy_now`;
- shorter 3-5 session windows systematically misclassify the intended research-persistence use case as failure;
- 12 sessions remains bounded enough to measure useful lead time rather than indefinite watch persistence.

The endpoint does **not** require that a formal trade plan be published.

Formal plan publication is a separate downstream metric because source freshness/publication can lag otherwise valid technical confirmation.

Secondary conversion endpoints:

- T1/T2 within 5 sessions;
- T1/T2 within 20 sessions;
- buy-lane T1/T2;
- Entry Availability open;
- formal provenance-clean plan publication;
- first realistic executable price after publication.

---

# 5. Control population

Primary control:

> same-date unresolved/watch candidates with fewer than two valid independent evidence families.

Controls must be matched or stratified by:

- observation date / market regime;
- sector or industry;
- market-cap/liquidity bucket;
- current lane/state;
- distance from technical confirmation where measurable;
- current relative-strength regime;
- extension/chase state.

The evaluator must not compare emergence episodes only against the whole market.

Same-date controls are required because regime and market breadth materially affect conversion.

---

# 6. Primary metrics

For exposed and control episodes measure:

- 12-session T1/T2 conversion rate;
- relative risk and odds ratio;
- absolute conversion-rate uplift;
- median sessions to confirmation;
- fraction reaching buy-lane T1/T2;
- fraction reaching Entry Availability open;
- fraction receiving a valid formal plan;
- fraction whose valid entry window closes before plan publication;
- false-attention burden: episodes consuming research attention without later confirmation.

Post-confirmation metrics are secondary:

- 5/10/21-session absolute return;
- excess vs SPY;
- sector-relative excess;
- MFE / MAE / MDD;
- leadership survival.

Do not use post-confirmation returns to define the emergence exposure.

---

# 7. Evaluation fences

The hypothesis is **not** considered supported merely because the point estimate is positive.

Required evidence before any promotion discussion:

1. unique ticker episodes, not nightly rows;
2. no leakage from future prices or future event labels;
3. true known-at clocks for counted evidence families;
4. same-date controls;
5. issuer-deduplicated results;
6. date-blocked uncertainty;
7. at least two temporal evaluation slices with the same effect direction;
8. no single ticker, event family, sector, or date cluster explains the result;
9. effect remains positive after controlling for baseline technical proximity / state;
10. no Entry Availability authority is granted by this test.

A future promotion packet must state the accrued sample size and uncertainty.

This preregistration deliberately sets **no numeric ship threshold** today; the current historical discovery sample is too small to choose one without overfitting. A later operator-reviewed promotion rule may set thresholds only after sufficient prospective accrual, and must not retroactively redefine success.

---

# 8. Product semantics if eventually supported

A successful emergence head should produce language like:

- “High-priority emerging candidate.”
- “Rerating evidence is converging.”
- “Entry is not open yet.”
- “Waiting for technical acceptance / reset.”
- “Research priority elevated.”

It should not produce:

- “Buy.”
- “High probability winner.”
- “Guaranteed leader.”
- “Plan ready.”

Emergence score and Entry Availability must be visually and semantically separate.

---

# 9. Required observability

Every emergence episode should accrue:

- first seen;
- latest seen;
- evidence-family set;
- evidence additions/removals;
- known-at clocks;
- research-attention priority;
- current technical state;
- current Entry Availability;
- refusal reason;
- first T1/T2 timestamp;
- first buy-lane timestamp;
- first Entry Availability-open timestamp;
- first formal-plan timestamp;
- first executable-price timestamp;
- terminal state / expiry reason.

This is an evaluation projection over the existing candidate episode, not a new lifecycle authority.

---

# 10. Historical discovery is quarantined

The following historical observations are discovery only:

- NVDA Sep-2026;
- the legacy >=2-evidence watch conversion census;
- FORM / PWR / WDC historical conversions;
- any same-date control uplift observed in PR #8495;
- T2 + multi-family convergence discovery.

They may motivate the hypothesis but may not be counted as prospective confirmation.

---

---

# 11. Existing Research Priority owner — no competing score

Live Entry Radar already owns `mastermind.research_priority.v1` (RP1).

RP1 is:

- deterministic;
- ACCRUING;
- a research-attention ordering;
- explicitly **not** probability, edge, confidence or Prophet;
- computed from structural quality, reset quality, resilience and recovery quality;
- explicitly excludes attention hotness, lobe nomination count, sentiment, historical outcomes and LLM output.

Therefore this preregistration does **not** authorize a second “Research Priority” score.

The emergence-convergence hypothesis must first accrue as a **typed research evidence state / cohort label**, for example:

- evidence convergence present / absent;
- evidence-family identities;
- evidence known-at clocks;
- emergence first-seen / latest-seen;
- current technical confirmation state;
- current Entry Availability state.

If operators need an ordering before the hypothesis is validated, consume the existing RP1 where its live Radar contract applies.

If prospective H-EMERGENCE-CONVERSION evidence later supports using rerating convergence in prioritization, that requires an explicit owner-level decision:

- either extend/version the existing Research Priority policy through its owner and scientific gate; or
- register a Conditional Fusion challenger that remains non-authoritative until promoted.

Do not create a Prophet-specific “emergence priority score” beside RP1.


# Final preregistered question

> **Can Mastermind reliably recognize important unresolved candidates 1-3 weeks before valid technical confirmation, without turning that early research state into a premature trade signal?**

That is the Emergence / Research-Attention problem.
