---
key: AGENTOS-W4-REPORT-GENERATOR-BEFORE-HOOK
question: >
  Should Agent OS Phase 4 begin by editing the fleet-wide ship-loop Stop guard and
  automatically mutating Agent OS records, or by proving a separate deterministic
  report-only capability first?
answer: >
  Build and accept a pure, bounded `agentos.ship_report.v1` generator before any hook
  integration or claim/release write helper. W4A may read existing local Git and Agent OS
  inputs through a thin adapter, but it must never write, call a network service, infer
  liveness, or influence the ship-loop decision. W4B hook wiring and W4C advisory writes are
  separate held waves with their own authority, tests, and production proof.
rationale: >
  The current ship-loop guard is a large fleet-wide blocking lifecycle component whose Stop
  exceptions can themselves become a block. Agent OS owns durable organizational continuity,
  not session completion or merge/CI enforcement. Coupling unproven workstream resolution and
  record mutation to that guard would make an optional organizational aid capable of blocking
  the company. A pure report is independently useful, makes ambiguity and missing handoffs
  visible, provides an executable contract for any later sidecar, and permits exact no-effect
  proof before introducing a mutation family.
alternatives:
  - option: >
      Edit `.claude/hooks/ship_loop_guard.py` directly and perform report/update work during
      Stop.
    why_not: >
      Rejected for the first vertical because the guard owns fleet-wide blocking behavior,
      delegates across worktrees, and converts unexpected Stop failures into a blocking error.
      This would mix organizational reporting with lifecycle authority and make rollback/noise
      attribution difficult.
  - option: >
      Implement `agentos claim` and `agentos release` writes first, then infer the workstream
      from the advisory claim.
    why_not: >
      Rejected because claim notes are explicitly advisory and prove no live worker. A write
      helper cannot explain path ownership, overlap, missing handoffs, or terminal records
      before changing durable truth.
  - option: >
      Generate and commit handoff prose automatically from the Stop hook.
    why_not: >
      Rejected because mission, prior state, verified/unverified evidence, unresolved work,
      next actions, do-not-redo boundaries, and danger areas require source-author judgment.
      Automatically durable prose would be low-trust memory and could grant authority to
      transient tool output.
  - option: >
      Make no Phase 4 improvement and continue relying on worker memory.
    why_not: >
      Rejected because current continuation archaeology proved a fresh session can resolve the
      correct workstream yet still receive a stale handoff. A bounded read-only report closes a
      real usability gap without taking lifecycle or mutation authority.
evidence:
  - >
      Macro `20704f4b1bd1b133629325c25af756c5de03af94`:
      `.claude/settings.json` routes SessionStart and Stop through the existing
      ship-loop guard and hold wrapper.
  - >
      Macro `20704f4b1bd1b133629325c25af756c5de03af94`:
      `.claude/hooks/ship_loop_guard.py` owns SessionStart/Stop, CI/merge/hold reconciliation,
      cross-worktree delegation, and blocking `guard_error` handling.
  - >
      Macro `20704f4b1bd1b133629325c25af756c5de03af94`:
      `scripts/ship_loop_hold_wrapper.py` performs Git/GitHub/check reads and blocks pending or
      red ratified holds while preserving the canonical guard.
  - >
      Macro `20704f4b1bd1b133629325c25af756c5de03af94`:
      `scripts/agentos.py` labels `claim:` as an advisory author note that blocks nothing and
      proves no live activity.
  - >
      `research/MASTERMIND_AGENT_OS_V1_IMPLEMENTATION_PLAN.md` requires Phase 4 report-only
      behavior and an explicit no-block test, while its older combined hook/write shape predates
      the current guard size and responsibility growth.
  - >
      `research/MASTERMIND_AGENT_OS_ARCHITECTURE.md` assigns session lifecycle to ship-loop/CI
      machinery and says Agent OS emits a handoff at the boundary rather than reimplementing the
      gate.
  - >
      Current September 7 continuation work showed the literal request `Continue Agent OS Work`
      resolves `WS:AGENT-OS` but can surface an August handoff; W4A must report the gap without
      inventing a new lifecycle or auto-writing the record.
  - >
      Protected Mastermind procedure `d7ffac605c547da593bfa4b4ac2b45ccafd009d6`,
      Skillpack `mastermind.sol_skillpack.v1` 1.0.1 / bootstrap 1, preserves one canonical system,
      explicit effect reconciliation, and one independently useful capability per PR.
affects:
  - WS:AGENT-OS
  - docs/superpowers/specs/2026-09-07-agent-os-w4-report-only-ship-capture-design.md
  - engine/agentos_ship_report.py
  - scripts/agentos.py
  - tests/test_agentos_ship_report.py
  - .claude/hooks/ship_loop_guard.py
  - scripts/ship_loop_hold_wrapper.py
  - .claude/settings.json
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: 2026-09-07
review_by: 2026-10-07
---

# Agent OS W4: report generator before hook

## Decision boundary

This decision authorizes no implementation by itself. It freezes the order and authority
boundary for the existing Phase 4 objective:

```text
W4A pure report
→ accepted manual real-path proof
→ separate W4B nonblocking hook decision, if still useful
→ separate W4C explicit advisory write design, if still useful
```

## What W4A may do

- consume explicit repository, branch, SHA, changed-path, workstream, handoff, and optional
  pull-request evidence;
- reuse the existing Agent OS parser and repository-aware `owns_paths` semantics;
- distinguish resolved, ambiguous, unclaimed, terminal, source-unavailable, and refused input;
- report whether one same-workstream handoff is present in the change set;
- emit bounded recommendation codes and exact non-effects;
- render deterministic JSON and a fixed text view.

## What W4A may not do

- write Agent OS or Git;
- call GitHub, Slack, Linear, Executive OS, providers, browsers, or models;
- inspect process/session state;
- infer current worker liveness from branch, claim, commit, tab, process, or handoff;
- create a workstream or handoff;
- update `status`, `next_action`, `prs`, waves, claim, decision, or discovery;
- call or import the ship-loop guard/wrapper from the pure core;
- alter Stop, merge, CI, hold, or runtime lifecycle;
- truncate an oversized report;
- select a workstream by first-wins, recency, title similarity, or majority path count.

## Hook and mutation holds

`.claude/hooks/ship_loop_guard.py`, `scripts/ship_loop_hold_wrapper.py`, and
`.claude/settings.json` remain read-only for W4A. A future W4B must prove provider hook semantics,
nonblocking behavior under every failure, bounded invocation, rollback, and zero influence on the
canonical ship decision.

A future W4C must use explicit action, exact current record SHA, idempotency, compare-and-set,
validation, review, correction, and `EFFECT_UNKNOWN` reconciliation. Claim/release remains
advisory and cannot acquire a lease or prove worker presence.

## Acceptance

The decision is satisfied only when W4A has independent source review, current-base checks, a real
branch demonstration, and proof that Agent OS/Git/external state is byte-identical before and after
report generation. Until then the capability remains `SPEC_ONLY` or `BUILT_NOT_PROVEN` according
to the exact evidence; W4B and W4C remain `NOT_BUILT / HELD`.
