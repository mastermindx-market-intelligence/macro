---
key: OPTIONS-ALPHA-FS-EVALUATION-CONTRACT
question: >
  What exact target, population, time-split/calibration discipline and acceptance ladder
  govern the existing Options Alpha FS family after Packet B found source-contract mismatches
  that could make a technically "deployable" artifact scientifically ineligible?
answer: >
  Preserve the existing FS family as a zero-authority, option-side-unsigned probability that
  the underlying outperforms SPY over its registered DTE-routed horizon: Y_H = 1[spy_excess_H > 0].
  Do not relabel it as absolute movement, option success, call/put thesis success, expected return
  or P&L. Fit/evaluate one immutable population per (source, detector_version, model_bucket,
  evaluation_spec_version); never pool tape_recon and live_feed in one model artifact. The current
  SPY-only tape_recon cohort is structurally ineligible for a SPY-excess target because benchmark-
  self excess is zero by construction; it remains measurement/diagnostic evidence only unless a
  future non-SPY tape cohort satisfies this contract. Preserve the registered no-eod_proxy verdict
  law. Replace row/calendar approximations with fail-closed NYSE-session partitions, exact label-
  interval purging, trading-session embargoes and the registered root-disjoint evaluation claim.
  Remove the current positive monotonic constraints on at_ask_share and vol_gt_oi_ratio for this
  target: "stronger attention/conviction" does not establish monotonic SPY outperformance. Do not
  compare constrained vs unconstrained variants and select the winner; the amended construction
  freezes unconstrained inputs before any fit. Calibration fit, calibration evaluation and final
  OOS must be ordered, disjoint and label-window separated; sparse or one-class slices fail closed.
  A model artifact may never gain statistical/promotion authority merely because local ECE/Brier/
  reliability checks pass. Registered OOS discrimination, effective-N, era/cell, multiple-testing,
  FS-5 and DNR promotion gates remain separate and mandatory. scoring.enabled stays false.
rationale: >
  Packet B inspected current Macro source and reproduced fit-free counterexamples showing that
  the implemented label is positive SPY-excess, the serving loader can concatenate registered
  sources, embargo logic uses calendar-day distance, time blocks can split sessions, a single-root
  fallback drops root exclusion, calibration can fit on rows later used for evaluation, CPCV paths
  are counted but not actually enumerated, and the local artifact deployable predicate omits the
  registered newest-era AUC/FS-5 acceptance layer. These are method-contract issues, not evidence
  that any profitable edge exists or that a promoted model is bad. Current gate.json remains
  scored=false with no model versions, so the correction is prospective and does not rewrite an
  accepted live model.
alternatives:
  - option: Preserve the current trainer/evaluation implementation unchanged and rely on FS-5 to catch defects later.
    why_not: >
      That permits known cohort/time/calibration contract mismatches to contaminate the evidence
      entering FS-5 and can create a locally ready artifact whose scientific population is invalid.
  - option: Change the target now to absolute movement or a right-conditioned call/put outcome.
    why_not: >
      Those are different statistical families and targets. Substituting them now would violate
      the existing OA-2 scope and prospective registration law rather than repair the current family.
  - option: Fit constrained and unconstrained variants and select whichever performs better.
    why_not: >
      That creates an unregistered selection branch after the issue is known. The current monotone
      assumptions do not justify SPY-outperformance monotonicity, so the amended construction freezes
      the unconstrained form before fitting.
evidence:
  - "Parent carrier mastermind-terminal#599; Packet B durable return comment 5740770584."
  - "Mastermind protected source pin 880e377cfa9d3fbdc921e931a55cc8c4143dc119; Skillpack 1.0.1/bootstrap1."
  - "Macro source base 6f35b67d4a2655f2e8409406646f88adf852c2b6."
  - "research/OPTIONS_ALPHA_FLOW_SCORE_AMENDMENT.md blob 8c90e56f04c823cafa16fda60ca4bb92beb28b28."
  - "config/flow_score.yml blob 878a70e1a51bb1baa249624b7105eec4f2f16b10."
  - "scripts/ops_train_flow_score.py blob 3b05edb11778be70e060d2a20c351202a06c172e."
  - "engine/flow_signals_grade.py blob 14afdd90e11f5d22f60ce3ed376fe70c5013db4c."
  - "lib/flow_score.py blob 9513513892f789ce7584dc5f2ae6d2b07e8deb10."
  - "data/flow_signals/gate.json blob fd81b7f7f2d7672352d04082179ce5713de59347: asof 2026-09-18, scored=false, model_versions={}, n_scored_total=0."
affects:
  - "WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY / OA-2"
  - "research/OPTIONS_ALPHA_FLOW_SCORE_AMENDMENT.md"
  - "config/flow_score.yml"
  - "scripts/ops_train_flow_score.py"
  - "lib/flow_score.py"
  - "tests/test_fs4_flow_trainer.py"
  - "existing Evaluation/qledger owners"
confidence: high
reversibility: costly
decided_by: ceo-sol
decided_at: 2026-09-19
authority: >
  Current Chairman instruction in the active session: take over the parent and move the project
  forward. This decision stays inside the existing ceo-sol Options Alpha/statistical-method
  authority and grants no model fit, promotion, merge, deployment or trading authority.
---

## Narrow supersession / preservation scope

This decision narrows ambiguous prose and implementation interpretations; it does not replace the
existing OA architecture or the registered FS family wholesale.

It clarifies that the existing family's machine target is exactly `Y_H = 1[spy_excess_H > 0]`,
rather than an absolute "move of this size" probability; that registered source/detector populations
cannot be pooled merely because the trainer can concatenate them; and that implementation fallbacks
cannot weaken trading-time, root-disjoint, calibration-isolation or FS-5 acceptance requirements.

It preserves:

- `Flow -> Package -> Positioning -> Candidate -> Outcome -> Calibration -> Decision Support`;
- Attention/Salience != calibrated probability != promoted authority;
- the FS family's unsigned-with-respect-to-option-right boundary;
- the existing DTE horizons and 36-cell BH-FDR family, with ineligible/unfilled cells remaining visible;
- `eod_proxy` as priors/pre-training only, never a calibration/OOS verdict cohort;
- `scoring.enabled=false` until separately accepted FS-5 and DNR promotion;
- the standing bans on new positioning/OI/GEX fusion, LLM origination, exact-option-return inference and trade authority.

Detailed frozen method and implementation acceptance live in
`research/options_estate/OPTIONS_ALPHA_FLOW_SCORE_EVALUATION_AMENDMENT_2026-09-19.md`.

This decision is records/source law only. It does not fit a model, mutate production data,
change `scoring.enabled`, or make OA-2 complete.
