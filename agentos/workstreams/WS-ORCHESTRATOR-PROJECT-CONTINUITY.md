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
owner: codex
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
    status: awaiting_ci
    next_action: >
      Qualify Mastermind PR 1664. Review the held private adapter delta before
      changing installed bindings; native trust remains a separate gate.
  - id: W1
    title: Supply existing Agent OS context at startup and compaction
    status: awaiting_ci
    next_action: >
      Qualify PR 1666 and the Macro compiler. Resolve read latency and diagnostic
      process settlement before the complete native-delivery canary.
  - id: W2
    title: Publish the project plan and recoverable checkpoint in Agent OS
    status: awaiting_ci
    next_action: >
      Qualify Macro PR 9967 and retain its source proof and exact remaining
      delivery gaps. Advance the shared owner checkout through its normal owner.
  - id: W3
    title: Compose and qualify full semantic continuation through existing owners
    status: in_progress
    next_action: >
      Review PR 1673 into PR 656 and integration PR 1676 into PR 1289.
      Reconcile accepted dependency heads while preserving production hold and custody.
  - id: W4
    title: Prove normal and interrupted long-project execution across providers
    status: todo
    depends_on: [W0, W1, W2, W3]
    next_action: >
      Prove paid START, retained return, review, acceptance, compaction and continued
      phases. Repeat with interruption and qualify each provider separately.
discoveries:
  - DSC:CODEX-STOP-ADAPTER-DRIFT-SUPPRESSES-ATTENTION
do_not_redo:
  - "Reuse Agent OS and Mastermind runtime owners; no second task registry, priority queue or memory store (agentos/README.md)."
  - "Use ops.fabric_launch.agentos.read_context for exact owner expansion; ContextResolver selects references (Mastermind d010b161)."
  - "122 return/preflight tests and 62 context/owner/guard tests passed; reuse exact source evidence in the handoff. Hosted CI remains separate."
landmines:
  - "A matching static hook pin is not native loading or original-parent consumption; see DSC:CODEX-STOP-ADAPTER-DRIFT-SUPPRESSES-ATTENTION."
  - "The compiler may preserve mandatory material beyond its requested budget; inspect exclusions and the adapter's complete-output limit (agentos/README.md)."
  - "Keep exact per-path Git date semantics: the older batch helper loses merge-resolution dates (scripts/agentos.py)."
  - "This authored workstream and its owner field establish no live lease, runtime assignment or transfer of an older parent's workers (agentos/README.md)."
artifacts:
  - research/ORCHESTRATOR_PROJECT_CONTINUITY_IMPLEMENTATION.md
  - mastermind:integrations/session_bridge/AGENTOS_SESSION_START.md
next_action: >
  Finish source qualification and the focused owner-composition proof, then obtain
  the exact private-adapter review permission and native Codex review/trust needed
  for the held installation and interrupted-session canary.
---

## Scope

This is the 2026-10-21 Chairman-requested harness continuity project. It uses the
existing executive-os program and existing knowledge/execution owners. It does
not replace WS:EXECUTIVE-ECOSYSTEM-COMPLETION or inherit that workstream's active
workers, readiness canaries, runtime arms or acceptance obligations.

The outcome is continued, goal-directed execution with evidence. A source PR,
a generated context bundle or a session claiming to remember its goal is an
intermediate fact. The implementation plan records the exact acceptance ladder.
