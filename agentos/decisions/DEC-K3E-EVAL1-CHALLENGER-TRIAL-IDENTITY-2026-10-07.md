---
key: K3E-EVAL1-CHALLENGER-TRIAL-IDENTITY-2026-10-07
question: >
  K3E-EVAL-1-V1 allots one challenger trial in the REGULARIZED_LINEAR_OR_HAZARD family. The
  registration requires the full trial identity on canonical main before any F_DEV label is read,
  every element citing an owner-authored spec line, and features restricted to derived
  expectation-surface components that EXP-1 emits with printed denominators and that exist on
  canonical main at the boundary commit. With no identity the challenger arm is UNESTIMABLE. What
  identity, if any, does the custodian commit?
answer: >
  SKELETON PENDING SEAT RULING. Recommended: commit Option A, an L2-penalized multinomial logistic
  regression (lambda 1.0, Newton-Raphson from zero, no tuning, no random draw) over the entire
  bound feature universe of three EXP-1 fields: the rights_blocked_state indicator, and
  true_missing_share and invalid_or_inconsistent_excluded_share, both over the
  capture_clock_bounded_relevant_records denominator (the EMS:61 total). Preprocessing (null
  imputation, standardization, fixed winsorization) is fit on F_DEV only and frozen for F_VAL,
  F_HOLD and shadow rows. The identity file is
  research/alpha_intelligence/expectation_market_dynamics/eval1_challenger_trial_identity.v1.json
  and research/alpha_intelligence/expectation_market_dynamics/check_eval1_challenger_identity.py
  enforces its shape. Merging it spends trial 1 of the 1 EVAL-1 trial (family
  k3e_expectation_market_dynamics_v1, family maximum 64). Only the seat merges it.
rationale: >
  Owner-authored lines. Every element cites a line already on canonical main: the owner-authored
  EVAL-0 sources (EVALUATION_PREREG.md, eval0_preregistration.v1.json, EXPECTATION_MODEL_SPEC.md),
  the custodian-frozen EVAL-1 registration and its rationale, and the EXP-1 emitter. The rationale
  (EVAL1_PREREGISTRATION_RATIONALE_2026-10-07.md:116) says no owner-authored spec names a T1
  feature set and that writing a feature list would originate a hypothesis. This identity
  therefore selects nothing: it takes the whole bound universe under a mechanical rule.

  The bound universe is small. At the boundary commit 01fcaf74 the EXP-1 emitter is a raw
  declared-capture inspection: normalized_baseline.value is always None, the freshness policy is
  UNAVAILABLE, and revision inference across native periods is refused. None of the EMS:51-58
  aggregates exist. What EXP-1 does emit is the EMS:59 rights and missingness state with the
  EMS:61-63 denominators, and the three features are exactly those categories (rights-blocked,
  unavailable, dropped) over the total.

  Boundary commit. eval1_preregistration.v1.json:120 defines the boundary from the first canonical
  origin/main commit containing the registration digest, which is
  01fcaf748c2794aa717b25d3e34ad1f53c539801, boundary instant 2026-10-07T13:30Z. PR 8583
  (expectation_state) and PR 8615 (ALIAS identity gate) landed after it, so their fields are
  excluded. The ALIAS gate adds no eligible component: unresolved rows stay in every other
  denominator, so the three features are unaffected. PR 8583 does widen rights_blocked to
  DISPLAY_ONLY labels. The pinned emitter blob governs and the delta is disclosed in the identity.

  Why commit rather than leave the arm UNESTIMABLE. The registration books the one trial as
  allotted either way, so not committing saves no certain budget. Committing costs one more
  Benjamini-Yekutieli test in the family and a near-certain null: three data-quality features are
  not expected to predict revision direction better than the metric-stratified B6 base rate. The
  choice between A and Z is the merge decision of the seat.
alternatives:
  - option: "Option Z: commit nothing, so the challenger arm is UNESTIMABLE (eval1_preregistration.v1.json:43)"
    why_not: >
      Lawful, and the fallback the registration itself names. On the arithmetic of the registration
      (eval1_preregistration.v1.json:133 records 63 family trials remaining after EVAL-1
      unconditionally) it does not demonstrably return the trial to the family, and it leaves EVAL-1
      with no challenger at all. Kept open as the alternative the seat can choose at merge time.
  - option: "Option B: discrete-time competing-risks hazard (UP or DOWN events per session, FLAT as survival to session 21)"
    why_not: >
      P(FLAT) as survival to session 21 does not match the registered three-class label, and the fit
      needs per-session event-time labels that t1_label does not expose. More moving parts for the
      same three features.
  - option: "Option C: two nested binary logits (change versus FLAT, then UP versus DOWN)"
    why_not: >
      Same features, same family, more parameters and a second penalty to fix. It adds nothing the
      multinomial form lacks.
  - option: "Option W: wide universe adding the provider-reported covering-analyst count (EMS:53)"
    why_not: >
      That count is emitted only inside the snapshot block stamped RAW_CAPTURE_INSPECTION_ONLY, not as
      a surface aggregate with a printed denominator, so admitting it would stretch the feature
      restriction of the registration.
  - option: "Seat-authored feature list under the custody DEC"
    why_not: >
      The rationale says writing a feature list would make the registration originate a hypothesis,
      and the custody DEC froze only values cited to owner lines. A subset chosen by the seat would be
      an uncited selection.
evidence:
  - "research/alpha_intelligence/expectation_market_dynamics/eval1_preregistration.v1.json:43-48 (absent-trial policy, family, trial_count 1, trial identity and commit rule)."
  - "research/alpha_intelligence/expectation_market_dynamics/eval1_preregistration.v1.json:120 (partitions strictly after the boundary set by the first canonical commit with the digest), :121-124 (T1 endpoint, horizon 21, log loss, B0 and B6 comparators), :130-134 (1 trial allotted, failed trials count, family maximum 64, FDR family)."
  - "research/alpha_intelligence/expectation_market_dynamics/EVALUATION_PREREG.md:144 (12 trials for the regularized linear/logistic or hazard family), :151-153 (trial identity elements, failed jobs count)."
  - "research/alpha_intelligence/expectation_market_dynamics/EXPECTATION_MODEL_SPEC.md:47-63 (derived surface components and the denominator law), :85-88 (no later outcomes or labels)."
  - "research/alpha_intelligence/expectation_market_dynamics/EVAL1_PREREGISTRATION_RATIONALE_2026-10-07.md:116-122 (features bound, not chosen)."
  - "engine/k3e_expectation_surface.py blob 3032ad4e on main and blob d83e25b5 at boundary commit 01fcaf74: the emitter lines cited per element in the identity file (rights_state, denominators, RAW_CAPTURE_INSPECTION_ONLY, value None, freshness UNAVAILABLE)."
  - "engine/k3e_eval1_forward.py:21-22 (classes and horizon), :34 (seed 480_336_034), :122 (t1_label), :279 (class-absent refusal)."
  - "engine/k3e_eval_admission.py:271-327 checks the registration and receipts, not a trial-ledger row or this identity (census lane itp_b6_challenger_census_r1)."
  - "data/trial_ledger.jsonl on main: 0 K3E rows of 1770 (census lane itp_b6_challenger_census_r1). The nightly is its only advancer, so this change writes no ledger row."
affects:
  - "WS:EVAL-OS-MEASUREMENT-LAW"
  - "WS:ALPHA-INTELLIGENCE-INTEGRATION"
  - "research/alpha_intelligence/expectation_market_dynamics/eval1_challenger_trial_identity.v1.json"
  - "research/alpha_intelligence/expectation_market_dynamics/check_eval1_challenger_identity.py"
confidence: medium
reversibility: one_way
decided_by: "seat: Information-to-Price Meta-CEO session 2fc05761 acting as EVAL-1 custodian under the Chairman directive of 2026-10-06 (not Sol); drafted by its orchestrator lane B (Opus 5.5)"
decided_at: 2026-10-07
review_by: 2026-11-07
---

# EVAL-1 challenger trial identity (K3E, 2026-10-07)

**Status.** Skeleton drafted by orchestrator lane B. The seat rules, red-teams and merges.
Merging it spends the single EVAL-1 challenger trial, and that spend is one-way.

**What is committed.**
research/alpha_intelligence/expectation_market_dynamics/eval1_challenger_trial_identity.v1.json.
Each of the seven identity elements carries file and line citations with the cited blob, and
research/alpha_intelligence/expectation_market_dynamics/check_eval1_challenger_identity.py
refuses a missing element, an uncited element, a feature outside the EXP-1 emitted set, a
tunable hyperparameter, or a preprocessing fit scope other than F_DEV.

**Options.**

| option | family member | features | cost | verdict |
| --- | --- | --- | --- | --- |
| A | L2 multinomial logistic, lambda 1.0, Newton-Raphson, no tuning | entire bound universe (3) | 1 trial, 1 BY test | recommended |
| B | discrete-time competing-risks hazard | same 3 | 1 trial | FLAT as survival misfits the label |
| C | two nested binary logits | same 3 | 1 trial | no gain over A |
| W | L2 multinomial logistic | 3 plus covering count | 1 trial | count is raw-inspection only |
| Z | none | none | arm UNESTIMABLE | lawful fallback |

**Label access.** None. The identity was written without calling t1_label or any outcome
loader, without reading any post-boundary row, and without fitting on any real row.

**Expected result.** A null. The fit is expected to sit near intercept-only, which is the
pooled F_DEV class frequency. B6 stratifies by metric, a row key the challenger may not use, so
the challenger is expected to tie or lose to B6.

**What this does not do.** It does not edit the registration or any merged file, write data/
or site/, read any label, fit on any real row, or grant promotion, product, rank, gate, size or
trade authority.
