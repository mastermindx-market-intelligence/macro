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
  - research/ORCHESTRATOR_PROJECT_CONTINUITY_W3_NATIVE_EVIDENCE_BRIEF.md
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
      compact and sibling-negative canaries. Changed-decision proof is blocked:
      no later accepted Tiingo decision exists in main. Reconcile genuine project
      source needs, then have its existing source-acquisition owner deliver an
      accepted change before Secretary resumes the exact canary. Do not invent a test decision.
  - id: W2
    title: Publish the project plan and recoverable checkpoint in Agent OS
    status: in_progress
    next_action: >
      Reuse merged Macro PR 9967 and Mastermind PR 1700 (a4525e3e).
      Publish the current four-file checkpoint through independent changed-head
      review and an eligible non-author release actor; PR 10181 is not yet canonical.
  - id: W3
    title: Compose and qualify full semantic continuation through existing owners
    status: in_progress
    next_action: >
      PR 1673 is incorporated and closed. PR 656 passed fresh review and entered
      the protected queue; consume its final release readback. PR 1676 passed
      independent composition review and merged into PR 1289 as 0b0eac4f.
      Correct the existing source-status docs and qualify native input evidence
      before a capsule ACK connection; keep PR 1289 Draft/production HOLD.
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
  - research/ORCHESTRATOR_PROJECT_CONTINUITY_W3_NATIVE_EVIDENCE_BRIEF.md
  - mastermind:integrations/session_bridge/AGENTOS_SESSION_START.md
next_action: >
  PR 1700 merged through the protected queue at 2026-10-25T12:08:55Z.
  Consume PR 656's protected-queue result and advance the integrated PR 1289
  source/evidence frontier on its existing carrier. Keep W1's real changed-decision
  proof open. Obtain changed-head review and independent merge-on-green release
  for Macro PR 10181. Exact-thread return watchers are verified; W4 retains its
  source, delivery, runtime arming and admission gates.
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
  admission at 2026-10-25T11:26:51Z. PR 1700 **merged at
  2026-10-25T12:08:55Z** as `a4525e3e7e9251951567a9142392df962bd06ba2`.
  Queue [CI 40188919977](https://github.com/mastermindx-market-intelligence/Mastermind/actions/runs/40188919977)
  and [Mastermind OS 40188919976](https://github.com/mastermindx-market-intelligence/Mastermind/actions/runs/40188919976)
  passed; protected master readback matched at 12:10:56Z. No self-approval occurred.
  [Release STOP](https://mastermindxgroup.slack.com/archives/C0CBC6AEAQZ/p1792930293345659)
  closed that release operation. This checkpoint remains proposed in Macro
  [PR 10181](https://github.com/mastermindx-market-intelligence/macro/pull/10181)
  until independent release; it is not accepted Agent OS state yet.
- **W3:** Fresh Cursor [review 5643182746](https://github.com/mastermindx-market-intelligence/Mastermind/pull/656#pullrequestreview-5643182746)
  passed #656 at a9c685a; non-author approval 5643188322 followed. Actual cloud
  writer custody was reconciled before protected-queue admission 34181749523
  at 12:36:22Z. Queue CI 40193870548 is running; admission is not merge.
  Fresh stack [review 5643238757](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1676#pullrequestreview-5643238757)
  passed the #1676/#1289 composition. #1676 **merged into #1289 at 12:47:12Z**
  as `0b0eac4f2aa2030f58e8a90e2724e5dfb2f3f6b8`; its tree exactly matches the
  reviewed stack. New #1289 CI 40194668383 is running. #1289 remains Draft /
  production HOLD; this receiver does not approve or self-release it.
- **Checkpoint:** Independent review 5643229107 passed previous source head
  4a001017. This newer delta needs review on the same operation. Macro main is
  unprotected and uses its existing merge-on-green controller; an eligible
  non-author admission actor is still required for authored PR 10181. The
  [release-route correction](https://github.com/mastermindx-market-intelligence/macro/pull/10181#issuecomment-6397682990)
  records that boundary. The dated handoff records exact-thread watch receipts.
- **W4:** the installed Executive owner reported `ceo_submit_armed: false` at
  2026-10-25T12:07:42Z. The earlier caller Codex target projection was empty. Staged
  `f608f52f` lacks the W3 builder and Runtime/Harness PREPARE/ACK additions;
  even arming it does not qualify this canary. Require the later accepted installed
  and selected W3 source closure plus actual admitted delivery and consumption.

The complete latest recovery record is
[the 2026-10-25 handoff](../handoffs/WS-ORCHESTRATOR-PROJECT-CONTINUITY-2026-10-25.md).
