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
  Commit Option A (seat ruling of 2026-10-11, after the seat adversarial pass recorded below): an
  L2-penalized multinomial logistic regression (lambda 1.0, Newton-Raphson from zero, no tuning,
  no random draw) over the entire
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
  seat chose A over Z on 2026-10-11; merging this record with the identity file is that choice.
alternatives:
  - option: "Option Z: commit nothing, so the challenger arm is UNESTIMABLE (eval1_preregistration.v1.json:43)"
    why_not: >
      Lawful, and the fallback the registration itself names. On the arithmetic of the registration
      (eval1_preregistration.v1.json:133 records 63 family trials remaining after EVAL-1
      unconditionally) it does not demonstrably return the trial to the family, and it leaves EVAL-1
      with no challenger at all. Rejected by the seat on 2026-10-11: it leaves a booked trial unused.
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
  - "Seat adversarial pass 2026-10-11 at branch head a90729ec (origin/main 488cb027 merged in): check_eval1_challenger_identity.py OK, 7 elements, 90 citations resolved; tests/test_eval1_challenger_identity.py 15 passed; the cited engine and spec files are byte-identical from a3973926 to 488cb027 (the diff over that range touches only .github/ci/legacy-jobs.yml and the two D60 receipt JSONs)."
  - "No F_DEV label was read before this commit: on origin/main only tests/test_qledger_validity.py imports engine.k3e_eval1_forward, and its t1_label test (:775) feeds literal synthetic tuples; data/trial_ledger.jsonl has 0 K3E rows; horizon-21 labels for post-boundary episodes (boundary 2026-10-07T13:30Z) cannot exist before about 2026-11-05."
affects:
  - "WS:EVAL-OS-MEASUREMENT-LAW"
  - "WS:ALPHA-INTELLIGENCE-INTEGRATION"
  - "research/alpha_intelligence/expectation_market_dynamics/eval1_challenger_trial_identity.v1.json"
  - "research/alpha_intelligence/expectation_market_dynamics/check_eval1_challenger_identity.py"
confidence: medium
reversibility: one_way
decided_by: "seat: Information-to-Price Meta-CEO session 2fc05761 acting as EVAL-1 custodian under the Chairman directive of 2026-10-06 (not Sol); skeleton drafted 2026-10-07 by its orchestrator lane B (Opus 5.5); ruled, red-teamed and merged by the seat itself on 2026-10-11 (Claude Fable 5.1)"
decided_at: 2026-10-11
review_by: 2026-11-07
---

# EVAL-1 challenger trial identity (K3E, 2026-10-07)

**Status.** RULED 2026-10-11: the seat commits Option A. The skeleton was drafted by orchestrator
lane B on 2026-10-07; the seat red-teamed it itself (section below) and merges it. Merging spends
the single EVAL-1 challenger trial, and that spend is one-way.

**What is committed.**
research/alpha_intelligence/expectation_market_dynamics/eval1_challenger_trial_identity.v1.json.
Each of the seven identity elements carries file and line citations with the cited blob, and
research/alpha_intelligence/expectation_market_dynamics/check_eval1_challenger_identity.py
refuses a missing element, an uncited element, a feature outside the EXP-1 emitted set, a
tunable hyperparameter, or a preprocessing fit scope other than F_DEV.

**Options.**

| option | family member | features | cost | verdict |
| --- | --- | --- | --- | --- |
| A | L2 multinomial logistic, lambda 1.0, Newton-Raphson, no tuning | entire bound universe (3) | 1 trial, 1 BY test | committed (seat ruling 2026-10-11) |
| B | discrete-time competing-risks hazard | same 3 | 1 trial | FLAT as survival misfits the label |
| C | two nested binary logits | same 3 | 1 trial | no gain over A |
| W | L2 multinomial logistic | 3 plus covering count | 1 trial | count is raw-inspection only |
| Z | none | none | arm UNESTIMABLE | rejected 2026-10-11 |

**Label access.** None. The identity was written without calling t1_label or any outcome
loader, without reading any post-boundary row, and without fitting on any real row.

**Expected result.** A null. The fit is expected to sit near intercept-only, which is the
pooled F_DEV class frequency. B6 stratifies by metric, a row key the challenger may not use, so
the challenger is expected to tie or lose to B6.

**What this does not do.** It does not edit the registration or any merged file, write data/
or site/, read any label, fit on any real row, or grant promotion, product, rank, gate, size or
trade authority.

**Seat adversarial pass (2026-10-11).** Run by the seat itself, as Claude Fable 5.1, at branch
head a90729ec, which merges origin/main 488cb027 into the lane branch.

- Owned bytes unchanged since the lane commit: `git diff --stat 9e02220b..HEAD` over the identity
  JSON, the checker, the test file and this record is empty.
- Checker: `python research/alpha_intelligence/expectation_market_dynamics/check_eval1_challenger_identity.py --repo-root <tree>`
  prints `OK: EVAL-1 challenger trial identity: 7 elements, 90 citations resolved`, exit 0.
- Tests: `python -m pytest tests/test_eval1_challenger_identity.py -q` reports 15 passed.
- Cited sources unchanged: `git diff --stat a39739268d origin/main` over engine/k3e_expectation_surface.py,
  engine/k3e_eval1_forward.py, engine/k3e_eval_admission.py, the expectation_market_dynamics
  directory, the test file and .github/ci/legacy-jobs.yml lists only legacy-jobs.yml and the two
  D60 receipts (eval1_owner_acceptance.v1.json, eval1_activation_receipt.v1.json) across 610
  commits. Blob ids: engine/k3e_expectation_surface.py is 3032ad4e on 488cb027 and d83e25b5 at the
  boundary commit 01fcaf74, as the identity records; engine/k3e_eval1_forward.py is d2daf28c, with
  CLASSES and PRIMARY_HORIZON_SESSIONS = 21 at :21-22 and BOOTSTRAP_SEED = 480_336_034 at :34,
  matching the horizon and seed_policy elements.
- No label read has occurred: `git grep -l k3e_eval1_forward origin/main` over engine, scripts, app,
  collectors, lib, tests and research returns only tests/test_qledger_validity.py, whose t1_label
  test (:775) feeds literal synthetic tuples; data/trial_ledger.jsonl on origin/main has 0 K3E
  rows; inspect_eval1_admission admits on origin/main since D60 (#8599, b88076e8, 2026-10-11T11:07Z)
  and no horizon-21 label for a post-boundary episode can exist before about 2026-11-05. The
  identity's label_access element reads NONE, and the seat's pass read no label either.
- Trial accounting re-read from the identity file: trial_ordinal 1 of eval1_trials_allotted 1;
  the spend event is the merge that first puts the file on canonical main; a failed, UNESTIMABLE
  or never-run trial stays spent; any later change to any element is a second trial.
- Disclosed delta: PR 8583 widened rights_blocked to DISPLAY_ONLY labels after the boundary; the
  identity pins the boundary blob, so the feature definition does not move.

**Deviations recorded.**

- Timing. The skeleton was drafted on 2026-10-07. Both Opus orchestrators (A a386fb9c, B ab6ff200)
  died at 2026-10-07T12:07Z on an API weekly limit, so the ruling slipped to 2026-10-11 with the
  seat running as Claude Fable 5.1. No F_DEV label became readable in the interval (above), so the
  commit still precedes any label read, as the registration requires.
- Review round 1 (a Cursor composer lane) performed a FIX round it was not commissioned for, edited
  the PR body and dropped trailers. The seat verified the owned bytes unchanged across
  9e02220b, f615d95a and a90729ec. The lane commit 9e02220b carries a Cursor co-author trailer the
  seat did not choose.
- Review round 2 returned REVIEW_DEFERRED and minted PR 8632, closed unmerged. After two review
  cycles with no delta the seat ran the adversarial pass itself rather than commissioning a third.
- This record is a workstream-owner act of the seat, not a Sol ruling (is_sol_ruling false in the
  identity's custody block).
