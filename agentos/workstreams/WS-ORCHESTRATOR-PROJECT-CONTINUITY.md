---
key: ORCHESTRATOR-PROJECT-CONTINUITY
title: Durable project direction and recovery across Codex and Claude orchestrators
objective: >
  Enable an assigned Astra, Codex or Claude orchestrator to preserve one recorded
  project goal, phase plan, accepted work and next action across compaction and
  interruption, then continue a real multi-phase project through delegation,
  review and acceptance without repeated human instructions to continue.
status: active
program: executive-os
p0: EXECUTIVE_OS
repos: [macro, mastermind]
owner: sol
class: build
blast_radius: reversible
ambiguity: scoped
owns_paths:
  - mastermind:integrations/session_bridge/fabric_stop_preflight.py
  - mastermind:integrations/session_bridge/agentos_session_start.py
  - mastermind:integrations/session_bridge/AGENTOS_SESSION_START.md
  - mastermind:tests/test_fabric_stop_preflight.py
  - mastermind:tests/test_agentos_session_start.py
  - scripts/agentos.py
  - tests/test_agentos_compile.py
  - agentos/workstreams/WS-ORCHESTRATOR-PROJECT-CONTINUITY.md
  - agentos/discoveries/DSC-CODEX-STOP-ADAPTER-DRIFT-SUPPRESSES-ATTENTION.md
  - agentos/handoffs/WS-ORCHESTRATOR-PROJECT-CONTINUITY-*
  - research/ORCHESTRATOR_PROJECT_CONTINUITY_IMPLEMENTATION.md
depends_on: []
waves:
  - id: W0
    title: Expose installed Codex return-binding drift
    status: done
    next_action: >
      Reuse merged Mastermind PR 1664 and its read-only drift proof.
      Keep the separately held subscribed Stop-hook activation out of this completed source slice.
  - id: W1
    title: Supply existing Agent OS context at startup and compaction
    status: in_progress
    next_action: >
      Reuse Secretary-approved installation A and native startup, Tiingo resume,
      compact and sibling-negative canaries. Verify the remaining changed-decision
      behavior and current owner-source delivery; reconcile paired resume/compact
      context with Secretary before any hook change.
  - id: W2
    title: Publish the project plan and recoverable checkpoint in Agent OS
    status: in_progress
    next_action: >
      Reuse merged Macro PR 9967. Observe the normal protected merge queue for
      independently approved PR 1700 at 6846da09, admitted by non-author
      mastermindx-3, then publish the current records through normal review.
  - id: W3
    title: Compose and qualify full semantic continuation through existing owners
    status: in_progress
    next_action: >
      PR 1673 is incorporated and closed; obtain fresh independent review of
      PR 656 at a9c685a, then the PR 1676 aee76c3 / PR 1289 a1c213b composition.
      Their current hosted CI is green. Preserve production HOLD and real custody.
  - id: W4
    title: Prove normal and interrupted long-project execution across providers
    status: todo
    depends_on: [W0, W1, W2, W3]
    next_action: >
      Require the accepted W3 composition in the installed and selected release,
      a real admitted capsule delivery/consumption path, and runtime arming plus
      exact admission/custody readback. Arming staged f608f52f alone is insufficient.
      Then prove START, return, review, acceptance, two phases and interruption.
discoveries:
  - DSC:CODEX-STOP-ADAPTER-DRIFT-SUPPRESSES-ATTENTION
do_not_redo:
  - "Reuse Agent OS and Mastermind runtime owners; no second task registry, priority queue or memory store (agentos/README.md)."
  - "Use ops.fabric_launch.agentos.read_context for exact owner expansion; ContextResolver selects references (Mastermind d010b161)."
  - "Mastermind PRs 1664/1666 and Macro PR 9967 are merged; reuse their reviewed source tests and merge receipts."
  - "PR 1673 is superseded by the same repaired builder on PR 656; do not reopen or duplicate it."
  - "Secretary installed and natively trusted W1 hook A; reuse exact native receipts. Do not reinstall, forge trusted_hash, or repeat the held private-adapter disclosure."
landmines:
  - "A matching static hook pin is not native loading or original-parent consumption; see DSC:CODEX-STOP-ADAPTER-DRIFT-SUPPRESSES-ATTENTION."
  - "The compiler may preserve mandatory material beyond its requested budget; inspect exclusions and the adapter's complete-output limit (agentos/README.md)."
  - "Keep exact per-path Git date semantics: the older batch helper loses merge-resolution dates (scripts/agentos.py)."
  - "This authored workstream and its owner field establish no live lease, runtime assignment or transfer of an older parent's workers (agentos/README.md)."
artifacts:
  - research/ORCHESTRATOR_PROJECT_CONTINUITY_IMPLEMENTATION.md
  - mastermind:integrations/session_bridge/AGENTOS_SESSION_START.md
next_action: >
  Observe Mastermind PR 1700's protected merge queue at approved head 6846da09
  (admitted 2026-10-25T11:26:51Z); require a merge receipt before calling it merged.
  Then close W1 changed-decision evidence with the existing installation owner
  and advance independent W3 review. W4 stays held on the unarmed runtime.
---

## Scope

This is the 2026-10-21 Chairman-requested harness continuity project. It uses the
existing executive-os program and existing knowledge/execution owners. It does
not replace WS:EXECUTIVE-ECOSYSTEM-COMPLETION or inherit that workstream's active
workers, readiness canaries, runtime arms or acceptance obligations.

The outcome is continued, goal-directed execution with evidence. A source PR,
a generated context bundle or a session claiming to remember its goal is an
intermediate fact. The implementation plan records the exact acceptance ladder.

## Leadership and current evidence — 2026-10-25

The Chairman assigned current leadership to the receiving ChatGPT3 principal.
The accountable role is now Sol; this changes no live source lease, native session,
STARTed worker or effect custody. The source-only takeover is recorded on
[Mastermind PR 1700](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1700#issuecomment-6387454117).
The implementation plan carries architecture and the bounded acceptance sequence;
this workstream and its dated handoff carry the current organizational frontier.

- **W0:** PR 1664 merged as `3905e79ed7996c52a42d78838ebc9df16ed2818a`.
- **W1:** PR 1666 merged as `7ab47f0b62d9a22ff16a13f6b99b96b681874a93`.
  Installed adapter bytes match the reviewed SHA256. Secretary decision D4 accepted
  independent Cursor B1 review for installation A; actual Codex-written trust and
  native startup/resume/compact context were read back. Full behavioral acceptance
  remains narrower than delivery. See the plan's native evidence table.
- **W2:** Macro PR 9967 merged as `1c99ae69ad45eda700f74337485669ee7a692e5b`.
  [PR 1700 review](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1700#pullrequestreview-5639488681)
  approves `6846da093b01870f342f4498c84bd4daa78383cb`; exact-head CI
  [40119407486](https://github.com/mastermindx-market-intelligence/Mastermind/actions/runs/40119407486)
  passed. [Secretary's returned seat restriction](https://mastermindxgroup.slack.com/archives/C0CBC6AEAQZ/p1792926945886959)
  was consumed: its identity cannot approve or merge. The current connector
  mastermindx-3 authored none of this PR's commits and submitted it to the normal
  protected controller. GitHub timeline event 34179003728 records merge-queue
  admission at 2026-10-25T11:26:51Z. Queue admission is not completed merge.
- **W3:** #656, #1676 and #1289 remain source review/integration obligations. All
  three unchanged heads have green required checks. #1289 retains production HOLD.
- **W4:** the installed Executive owner reported `ceo_submit_armed: false` at
  2026-10-25T11:18:43Z. The native Codex target projection is empty. Staged
  `f608f52f` lacks the W3 builder and Runtime/Harness PREPARE/ACK additions;
  even arming it does not qualify this canary. Require the later accepted installed
  and selected W3 source closure plus actual admitted delivery and consumption.

The complete latest recovery record is
[the 2026-10-25 handoff](../handoffs/WS-ORCHESTRATOR-PROJECT-CONTINUITY-2026-10-25.md).
