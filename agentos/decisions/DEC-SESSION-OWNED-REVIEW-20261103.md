---
key: SESSION-OWNED-REVIEW-20261103
question: >
  Must Mastermind technical reviews depend on another top-level ChatGPT Web session,
  account, or external reviewer conversation when the assigned session can review
  directly or spawn a genuine independent technical-review subagent?
answer: >
  No. The assigned session owns its own review workflow. For an accepted
  FAST/STANDARD zero-external-review risk tier, adversarial self-check plus tests
  and required CI suffice without a separately commissioned reviewer.
  For review-sensitive work, a genuinely distinct-context read-only native
  subagent inside that same parent session (Web Pro when exposed, Codex, Claude,
  or an admitted Fabric child) may provide an independent technical assessment.
  Neither is an automatically submitted formal GitHub APPROVED review. Native
  branch protection, formal non-author approval where actually required,
  security holds, CI, custody and unresolved-effect fences remain intact.
rationale: >
  Chairman direct ruling of 2026-11-03 removes the third-party-session
  handoff as an organizational default. The burden should be the actual risk
  and trustworthy review evidence, not the number of open ChatGPT conversations.
  A source-building model's own second pass remains SELF_REVIEWED, while a
  true separately launched/returned child is a distinct technical reviewer.
  This decision is durable organizational memory, not ChatGPT server memory,
  source-release authorization, GitHub approval or runtime execution proof.
alternatives:
  - option: Require a different ChatGPT account/session for every PR review
    why_not: Blocks routine progression and mistakes a communication boundary for technical independence.
  - option: Relabel an author's own second pass as a formal non-author APPROVED review
    why_not: Misrepresents source independence and cannot satisfy GitHub's authenticated reviewer event.
  - option: Require paid Fabric for every review, even with native subagents or no additional risk demand
    why_not: Duplicates work and budgets; should be an optional qualified path under its real admission.
evidence:
  - "Chairman direct current-scope directive on 2026-11-03 (this is policy intent, not installed Project proof)"
  - "Mastermind proposed source PR #2026: docs/SESSION_LOCAL_REVIEW_POLICY.md and Web bootstrap change"
  - "Mastermind incumbent risk-tier relief #2018 and reviewer identity portability #1968 (open source candidates, not protected acceptance)"
  - "Macro current AGENTS.md/CLAUDE.md review guidance updated in the same change carrier"
affects:
  - AGENTS.md
  - CLAUDE.md
  - Mastermind/docs/SESSION_LOCAL_REVIEW_POLICY.md
  - mastermind-terminal/AGENTS.md
confidence: high
reversibility: easy
decided_by: chairman
decided_at: 2026-11-03
supersedes:
  - DEC:DEFAULT-FINISH-HANDS-WAIT-TO-SWEEPER
---

## Provenance and rollout state

The Chairman made the governance choice. At record creation, actual protected
acceptance, GitHub merge rules, installed ChatGPT Web Project instructions,
client-native subagent capabilities and fresh-session adoption are separate,
not inferred from this decision file.

Apply this as a memory/continuity pointer for future Web, Codex, Claude and
Fabric sessions. The source policy remains the protected Mastermind revision
once its PR is reviewed and accepted. Reconcile existing conflicting release
changes instead of creating a second review dispatcher, queue or state plane.

## Finish-to-release adjudication; supersedes unconditional CI handoff stop

The earlier `DEC:DEFAULT-FINISH-HANDS-WAIT-TO-SWEEPER` required termination after `CI_HANDOFF` even when a PR had never merged, and prohibited the current session from verifying completion. The Chairman's current directive supersedes **that unconditional terminal interpretation**, not the existing `merge-on-green` sweeper or finite REST-quota protections.

A truthful, verified `CI_HANDOFF` may release an **idle wait** to the original known sweeper when the candidate is reviewable, the exact head/required tests are observed, that watcher/trigger is proven functional and can return failed/held/merged outcomes to a reachable original-pr owner. The handoff is `DURABLE_EXECUTION_RUNNING` only with actual external execution and a genuine return path, **not** `PROVEN_OUTCOME`, completed PR, or permission to forget its failure. If no real return path or a red/blocked PR, the assigned owner works the concrete repair while able, saves the original carrier and names the reachable continuation when the current chat must end. Never force human-attended sessions to idle-poll checks or keep expensive agent loops awake during a proven sweeper wait. A valid hard HOLD remains `PARKED / HOLD-FOR-SOL` under its existing source law (Draft; no `merge-on-green` label or auto-merge; no Ready/merge until released). Separate source/CI/merge/deploy/live acceptance evidence is still required.

This decision changes **organizational policy** only; it does not prove `.claude/hooks/ship_loop_guard.py`, `ci_handoff.py`, the sweeper, or a ChatGPT Project instruction has been patched/enrolled or provides new Wake/return capability. Align actual enforcement through the existing owner, with targeted tests; do not create a second Stop hook, observer, queue, merge controller or memory plane.
