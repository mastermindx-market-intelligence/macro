---
workstream: WS:AGENT-EVAL-FABRIC
session: sol/agent-eval-fabric-continuation-20260919
model: sol
ended_because: ci_handoff
mission: Preserve the canonical Agent Evaluation program while advancing C2 and D1 from current source truth without redoing protected foundations.
state_before: Agent OS still projected merged #162 as a release hold and #398 at an obsolete repair head; C2's sealed provider/runner incompatibility and current OHF failure-path defect were not recorded.
next_actions:
  - >
    C2 is execution-held after #841 merged. Preserve preregistration
    sha256:91cb16860ee9e140d28052e5981b7c8f94aac4ecd42e788d3c7a75e3415e5cf8 unchanged:
    it seals anthropic/claude-sonnet-5 while #162 Fresh-Sol requires gpt-5.6-sol. Await the incumbent
    Fable program-owner ruling when that exact principal regains capacity; do not run the 12 executions,
    mutate the seal, or self-adopt draft #687/#692.
  - >
    D1 remains on Mastermind #398 at d79d2ec3537d8eb060055731a7c3cebee0c543eb.
    Source review/CI/current-protected proof are green and canonical current-Macro grounding is proven.
    No directive intent exists. Executive control remains STOPPED/UNARMED under incident #386: #760 is
    merged/do-not-redo and the next gate is the local Keychain-to-stdin service-account credential/readiness
    ceremony, then Gate B / Phase 1C-A / receipt-gated ARM before one untouched READ/A0 directive can be admitted.
do_not_redo:
  - "Mastermind #162 is merged/do-not-redo at d6eccb0d81c9db3d009eafa7b37ea97a4dc99bc8; do not recreate the runner release or its old identity hold."
  - "Mastermind #841 is merged/do-not-redo at 96c9ab97aa64bce65fe0da140c9d6c5bbf2c778e; do not recreate the OHF typed-failure repair or re-enqueue it."
  - "Mastermind #760 is merged/do-not-redo at d57d793b588fc7819559bdc2b408977dd01691e6; do not recreate the installed-binary readiness repair."
  - "Macro #7344 is merged/do-not-redo at 2834f2531f145ede66d5639b4a149633147beac7; this continuation record is canonical on main."
  - "Do not reopen #6699/#6711 or rebuild protected R0/C0/S1/OHF2/E1-preregistration foundations."
  - "Do not mutate the original E1 preregistration digest in place or reinterpret sealed provider/model fields as execution placeholders."
  - "Do not rerun OL-V1's real effect, E1 provider executions, or any EFFECT_UNKNOWN operation through a replacement carrier."
danger_areas:
  - "The E1 seal is prospective evidence, not an executable license after its provider/model no longer matches the sole named runner."
  - "The OHF typed-failure substrate defect is closed by merged #841; that release does not make historical E1 executable or grant provider authority."
  - "OL-V1 n=1 and E1 paired-pilot evidence remain descriptive and grant no routing, trading, sizing, gating, policy, or execution authority."
  - "The remaining D1 credential gate is secret-owning local human work: never retrieve, print, relay or infer the service-account Keychain token through chat/tool surfaces."
unresolved:
  - "C2 incumbent-Fable ruling/capacity and fresh future experiment authorization; #398 waits on #386's local credential/readiness/ARM sequence plus canonical Executive intent/effect gates; real E1, OL-V1 episode, F1, G1, and forward accepted value remain unproven."
changed:
  - path: agentos/workstreams/WS-AGENT-EVAL-FABRIC.md
    what: Reconciles #162 as merged, records #398 d79, and makes C2's sealed provider/runner mismatch plus OHF substrate defect explicit.
  - path: agentos/handoffs/AGENT-EVAL-FABRIC-2026-09-19.md
    what: Adds the compact current continuation frontier without rewriting the September 8 historical handoff.
  - path: tests/agent_eval_continuity_cases.py
    what: Moves the recovery regression to the new handoff and pins current do-not-redo and sealed-mismatch evidence.
verified:
  - claim: "Protected program foundations remain released."
    command: "Current GitHub/Agent OS reconciliation."
    result: "Macro #6760/#6713 and Mastermind #332/#333/#336/#337 remain completed inputs; no foundation rebuild is owed."
  - claim: "Mastermind #162 is released."
    command: "GitHub PR #162 + review 5134108615."
    result: "Semantic head df9a2ddab12563a3b054569a54c8e8f108269ed7 APPROVED; merge d6eccb0d81c9db3d009eafa7b37ea97a4dc99bc8 on 2026-09-13; old identity hold superseded."
  - claim: "C2 sealed provider/model cannot be supplied as one of its disclosed placeholders."
    command: "Read protected experiments/agent_eval/e1/preregistration.json and scripts/ohf/fresh_sol_eval.py."
    result: "Digest sha256:91cb16860ee9e140d28052e5981b7c8f94aac4ecd42e788d3c7a75e3415e5cf8 binds provider=anthropic and model_requested=claude-sonnet-5 in all six configurations; disclosed placeholders are instruction bundle, sandbox digest, environment digest; Fresh-Sol REQUIRED_MODEL is gpt-5.6-sol."
  - claim: "OHF typed request failures are repaired and protected."
    command: "Mastermind #841 exact-head review/CI/merge-queue release and protected-master readback."
    result: "Head 738454fa1716bae74d0e78216c4bce937b2913cf merged as 96c9ab97aa64bce65fe0da140c9d6c5bbf2c778e on 2026-09-19; protected master eb00ed9745f055d3413f483b985fe4f9d8a1f11d descends from it and retains both repaired blobs byte-identically."
  - claim: "Mastermind #398 source-rereview gate is approved at d79."
    command: "Independent Codex review operation olv1-pr398-date-fixture-independent-review-20260919-codex-004."
    result: "APPROVE; one test-line temporal correction only, host proof receipt sha256 e06f092c15b0fa1b7430e711a60fd90a5c0ddbbd39bd9e699c3296e649db2187; review return PR comment 5738872266."
  - claim: "D1 current-Macro grounding is solved and the blocker moved to canonical Executive runtime readiness."
    command: "Current Macro WorktreeCreate mint/readback plus Mastermind #386/#760 runtime reconciliation."
    result: "A clean canonical Macro session worktree was proven at action-time main; no directive intent was submitted. #760 merged as d57d793b588fc7819559bdc2b408977dd01691e6. #386 keeps Executive STOPPED/UNARMED pending the local service-account credential/readiness ceremony; the operator control socket therefore cannot yet admit OL-V1."
  - claim: "The September 19 Agent Eval continuation is protected."
    command: "Macro PR #7344 exact-head review/CI/merge/readback."
    result: "Reviewed head 211bc3c871db198ecf80f737c77fef9d0d9da3bf merged as 2834f2531f145ede66d5639b4a149633147beac7; this workstream/handoff is canonical on main."
unverified:
  - claim: "E1 can execute exactly as preregistered."
    what_would_verify: "A prospective accepted program-owner decision that resolves the provider/runner contradiction without rewriting historical evidence, plus released runner substrate and fresh live authorization."
  - claim: "OL-V1 real episode is production-proven."
    what_would_verify: "Complete #386 credential/readiness/ARM through its secret-owning local ceremony, prove the canonical control listener healthy, action-time refresh exact Macro grounding, admit/reconcile one untouched READ/A0 directive, then complete compose/seal/effect/evidence/external production proof and accepted merge."
prs: [162, 337, 398, 760, 841, 6760, 6713, 6998, 7344]
decisions:
  - DEC:AGENT-EVAL-FABLE-COO-DELEGATION
---
# Current continuation

The program remains the existing Fable-owned `WS:AGENT-EVAL-FABRIC`; this handoff creates no
replacement program, runner, authority plane, or provider execution.

B3 is complete: Mastermind #162 merged at
`d6eccb0d81c9db3d009eafa7b37ea97a4dc99bc8`. C2 is no longer blocked by that historical
release hold, but it is not executable as currently sealed: the E1 preregistration binds
Anthropic/Claude Sonnet 5 while its sole named Fresh-Sol runner requires GPT-5.6 Sol.
Provider/model are not placeholders. Preserve the original digest as prospective historical
evidence and resolve the mismatch prospectively.

The OHF typed-failure regression is closed: Mastermind #841 merged through the required merge queue
as `96c9ab97aa64bce65fe0da140c9d6c5bbf2c778e`; protected master
`eb00ed9745f055d3413f483b985fe4f9d8a1f11d` retains the repaired blobs byte-identically.

D1 remains independent on existing PR #398 at `d79d2ec3537d8eb060055731a7c3cebee0c543eb`.
Its source-review/CI/current-protected gates are green and a lawful current-Macro grounding path is
proven. The real OL-V1 effect is now held by the incumbent #386 Executive STOPPED/UNARMED
credential/readiness sequence; no directive intent exists. No policy/promotion authority follows.
