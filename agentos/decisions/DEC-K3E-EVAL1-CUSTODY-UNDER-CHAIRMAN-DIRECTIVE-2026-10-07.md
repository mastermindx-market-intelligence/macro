---
key: K3E-EVAL1-CUSTODY-UNDER-CHAIRMAN-DIRECTIVE-2026-10-07
question: >
  The K3E EVAL-1 forward registration cannot become admissible without an owner acceptance and an
  activation receipt from the evaluation-law owner, WS:EVAL-OS-MEASUREMENT-LAW (Eval-OS program,
  CEO Sol). Sol has not acted. PR #8504 (squash cab92332) already repaired the five code-side P1
  blockers. Who performs the owner act, and on what authority, without weakening blinding, creating
  a parallel evaluator, or resetting the trial budget?
answer: >
  The Information-to-Price Meta-CEO seat (session 2fc05761) acts as EVAL-1 custodian under the
  Chairman's 2026-10-06 directive. It does so openly and in its own name, never as Sol. The
  directive reads: "Run autonomously to complete this program, diagnose blockers and problems
  yourself and get them troubleshooted and resolved yourself… If there are blocks where u require
  some parent or owner or something, you should assess to see if u can do it yourself… or summon a
  child opus orchestrator lane to complete it."

  The custodian proceeds in three steps:
  (1) Freeze research/alpha_intelligence/expectation_market_dynamics/eval1_preregistration.v1.json
  as a canonical-main introduction commit, with every scientific value cited to an owner-authored
  line in EVAL1_PREREGISTRATION_RATIONALE_2026-10-07.md.
  (2) Commit eval1_owner_acceptance.v1.json. It names owner_workstream WS:EVAL-OS-MEASUREMENT-LAW,
  as engine/k3e_eval_admission.py requires, and carries an acting_custodian field naming this
  seat, the Chairman directive, and this DEC, so the file does not claim to be Sol's act.
  (3) Commit eval1_activation_receipt.v1.json through a merge that lands at or after the resolved
  boundary.

  The evaluation-law owner may supersede this custody at any time with a later registration.
rationale: >
  The handoff for this program lists five EVAL-1 P1 blockers. PR #8504 repaired the code side of
  all five, enforced in engine/k3e_eval_admission.py:
  - as_of_date is now refusal-only;
  - acceptance and activation must bind the exact digest's first canonical-main introduction
    commit;
  - the boundary is the first NYSE session open strictly after that commit;
  - main freshness is proven;
  - the EVAL-1 schema is enforced in _registration_reason.
  What remained was the owner act itself.

  Blinding does not depend on who performs that act. The admission code admits only outcomes whose
  session is at or after the boundary, and the boundary is fixed by canonical-main time ordering:
  no outcome on or after the first NYSE open following the introduction commit can exist when the
  registration bytes are written. The identity of the author or acceptor therefore cannot unblind
  anything.

  P1-2 was "self-authored owner/activation JSON can impersonate Eval OS authority." The answer to
  it is truthful recording, not code: the acceptance file and this DEC both state that the seat,
  not Sol, acted. The Chairman sits above Sol and delegated exactly this class of owner block to
  the seat. An explicit Chairman delegation overrides default role assumptions inside its stated
  scope.

  This DEC narrows a statement in DEC:ITP-SEAT-RELEASES-ADMINISTRATIVE-BLOCKS-UNDER-CHAIRMAN-2026-10-06.
  That record listed "EVAL-1 held-outcome custody" among the gates that are not administrative. Its
  release form (labels, holds, stale reviews) is still not used here. The narrowing is only this:
  the forward custody act is performed by the seat under the 2026-10-06 directive, because the
  outcomes it can unlock are by construction ones nobody can have seen. That release form remains
  inapplicable to EVAL-0's held retrospective eras, and nothing here touches them.
alternatives:
  - option: Wait for Sol, the Eval-OS owner, to author the acceptance and activation
    why_not: >
      The Chairman directive tells the seat to resolve owner blocks itself rather than bounce them
      to a human or to Sol. Sol has not acted on EVAL-1 since the 2026-10-05 handoff. Every day of
      waiting delays the forward boundary by one day, and the forward partitions accrue from that
      boundary, not before it.
  - option: Build a parallel evaluator or a separate admission path for EVAL-1
    why_not: >
      Forbidden by the program handoff ("Do not create a parallel evaluator. EVAL-0 remains
      immutable") and by the standing ban on duplicate control planes. The incumbent
      engine/k3e_eval_admission.py already enforces the exact contract.
  - option: Reset or re-baseline the trial budget so EVAL-1 starts fresh
    why_not: >
      EVAL-0's amendment law forbids it, the EVAL-1 schema enforces
      predecessor.prior_trial_budget_reset false, and a reset would launder search across
      registrations. EVAL-1 spends 1 trial from the unreset 64-trial family
      k3e_expectation_market_dynamics_v1.
  - option: Edit EVAL-0's eras to cover the August-2026 source start
    why_not: >
      EVAL-0 is immutable. Moving its dates is the "silently moving dates" failure the program file
      names. A change requires a new version with a new forward boundary, which is EVAL-1.
evidence:
  - "Chairman directive 2026-10-06 (quoted in the answer), relayed by the Meta-CEO seat's MISSION B commission (orch/MISSION_B_EVAL1_R4.md)."
  - "agentos/handoffs/ALPHA-INTELLIGENCE-INTEGRATION-2026-10-05-fable-program-ceo.md:338-345 (the five P1 blockers; repair through incumbent Eval OS custody; no parallel evaluator; EVAL-0 immutable)."
  - "PR #8504 squash cab92332: engine/k3e_eval_admission.py:37 FREEZE_BOUNDARY_RULE, :109 _first_nyse_session_open_strictly_after, :144 _introduction_commit, :172 _prove_main_freshness, :271 _registration_reason, :391-420 owner acceptance checks (owner_workstream must equal WS:EVAL-OS-MEASUREMENT-LAW; registration_source_commit must equal the introduction commit)."
  - "research/alpha_intelligence/expectation_market_dynamics/EVALUATION_PREREG.md:42-47 (boundary law), :80-83 (no post-hoc date change), :234-237 (amendment law)."
  - "research/alpha_intelligence/expectation_market_dynamics/INFORMATION_TO_PRICE_PROGRAM_2026-10-03.md:180 (source starts August 2026; not silently moving dates)."
  - "data/trial_ledger.jsonl at origin/main bb7847a33c5 has 0 K3E rows; eval0_activation_receipt.v1.json:15 records no EVAL-0 challenger trial."
affects:
  - "WS:EVAL-OS-MEASUREMENT-LAW"
  - "WS:ALPHA-INTELLIGENCE-INTEGRATION"
  - "research/alpha_intelligence/expectation_market_dynamics/eval1_*.json"
confidence: medium
reversibility: costly
decided_by: "seat: Information-to-Price Meta-CEO session 2fc05761 acting as EVAL-1 custodian under the Chairman directive of 2026-10-06 (not Sol); drafted by its orchestrator lane B (Opus 5.5)"
decided_at: 2026-10-07
review_by: 2026-11-07
---

# EVAL-1 custody under the Chairman directive (K3E, 2026-10-07)

**Who acted.** The Information-to-Price Meta-CEO seat (session 2fc05761), as custodian. Sol did not act, and no file in this chain claims Sol's authorship. The owner acceptance names the owner workstream because the admission code binds to it. Its `acting_custodian` field names this seat and this DEC.

**Why blinding holds.**
- Admission opens only outcomes dated at or after the boundary.
- The boundary is the first NYSE open strictly after the commit that introduces the exact registration digest on canonical main.
- Those outcomes do not exist when the registration bytes are written.
- Pre-boundary rows are never EVAL-1 rows (EVALUATION_PREREG.md:45-47).

**What this does not do.**
- It does not touch EVAL-0's bytes, its held retrospective eras, or its digest.
- It does not reset or re-baseline the trial budget.
- It does not create a second evaluator or admission path.
- It grants no promotion, product, rank, gate, size or trade authority. EVAL-1 is research-only.

**Why the reversibility is "costly".** The evaluation-law owner can supersede this custody at any time with a later registration that has its own forward boundary. Under EVAL-0's amendment law, however, any EVAL-1 outcomes already read stay attached to EVAL-1. Any trial already committed stays counted in the family.

**Current expected result.** Every forward partition will report `INSUFFICIENT_EPISODE_N` until the R1 identity owner delivers canonical `issuer_ref` at each cutoff. The R4 dry-run found it null on every row (R4_DRYRUN_RECEIPT_2026-10-06.md:123). That is a first-class result, not a failure of this act.
