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
  - agentos/workstreams/WS-ORCHESTRATOR-PROJECT-CONTINUITY.md
  - agentos/handoffs/WS-ORCHESTRATOR-PROJECT-CONTINUITY-*
  - research/ORCHESTRATOR_PROJECT_CONTINUITY_IMPLEMENTATION.md
depends_on: []
waves:
  - id: W0
    title: Expose installed Codex return-binding drift
    status: awaiting_ci
    next_action: >
      Qualify Mastermind PR 1664 at b740b9afce945d15884076a14bbc6f9471716a46;
      preserve the separate private-source review and native trust gates before
      changing any installed adapter pin.
  - id: W1
    title: Supply existing Agent OS context at startup and compaction
    status: awaiting_ci
    next_action: >
      Qualify Mastermind PR 1666 at f48ed994cb1a1800ecfbf3d343fd4c98f27c17f5,
      then prove actual native loading,
      complete delivery and continued action in one intended Astra session.
  - id: W2
    title: Publish the project plan and recoverable checkpoint in Agent OS
    status: in_progress
    next_action: >
      Validate and publish this record, the implementation plan and the cumulative
      handoff; prove the incumbent compiler supplies their current objective and
      next action within the bounded attended-context adapter.
  - id: W3
    title: Compose and qualify full semantic continuation through existing owners
    status: todo
    depends_on: [W1, W2]
    next_action: >
      After native ingress is qualified, bind authentic SessionTruth and Executive
      observations to the existing continuation and turn-input owners. Implement
      missing production composition without fabricating PREPARE or supplied-input
      receipts; reconcile outstanding effects on their original carriers.
  - id: W4
    title: Prove normal and interrupted long-project execution across providers
    status: todo
    depends_on: [W0, W3]
    next_action: >
      Run the controlled project canary in the intended Astra entrypoint, including
      real paid Fabric START, retained return, review, acceptance, compaction and
      continued phase execution; then qualify each other provider adapter separately.
discoveries:
  - DSC:CODEX-STOP-ADAPTER-DRIFT-SUPPRESSES-ATTENTION
do_not_redo:
  - "Reuse Macro Agent OS, its compiler and Mastermind runtime owners; do not create another task registry, priority queue or memory store (agentos/README.md)."
  - "Reuse ops.fabric_launch.agentos.read_context for exact owner expansion; ContextResolver selects references and does not materialize mission prose (Mastermind d010b161)."
  - "121 return/preflight tests and 61 context/owner tests passed on M2; reuse their exact unchanged source evidence and rerun only for material changes or required release checks."
landmines:
  - "A matching static hook pin is not native loading or original-parent consumption; see DSC:CODEX-STOP-ADAPTER-DRIFT-SUPPRESSES-ATTENTION."
  - "The compiler may preserve mandatory material beyond its requested budget; inspect exclusions and the adapter's complete-output limit (agentos/README.md)."
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
