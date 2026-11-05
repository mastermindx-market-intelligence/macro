---
key: AGENTOS-W4-CAPTURE-BOUNDARY
question: >
  Where can the commissioned V1 ship-boundary assistance capture organizational
  metadata without turning Agent OS into execution authority or rewriting Stop behavior?
answer: >
  Capture only an already-created PR against one exactly bound existing workstream
  and wave at PostToolUse after literal PR creation, or through the same explicit
  Agent OS CLI. Leave the edit uncommitted for the ordinary next commit and push.
  Stop may report a missing committed handoff but never writes records or changes
  any ship-loop decision. Missing, malformed, ambiguous, conflicting or unsupported
  inputs produce an advisory report and no mutation. Enforcement stays report-only.
rationale: >
  The current Chairman closure handoff commissions W4 and calibration. MAS-129 is
  Canceled, so its stale MAS-130 dependency is not an execution prerequisite and its
  abandoned carrier is not revived. PR creation is a real existing boundary; updating
  tracked records after Stop approves a clean tree would create fresh unfinished work.
  Claims and owns_paths are existing knowledge identity hints, never live execution leases.
  The wave PR association is already consumed by status, brief and compile-context.
alternatives:
  - option: Write records after a successful Stop
    why_not: Creates uncommitted work after the completion guard has already evaluated it.
  - option: Infer the most likely active workstream or wave
    why_not: Fuzzy or status-based identity can write another workstream and invent ownership.
  - option: Add a capture daemon or parallel session record
    why_not: Existing execution planes own lifecycle and the canonical store already owns knowledge.
  - option: Wait indefinitely for the canceled MAS-129 carrier
    why_not: The current handoff authorizes fresh reconciliation; canceled historical work is not a live lease.
evidence:
  - "Chairman operation agent-os-v1-closure-20261003-astra-001, deliberately assigned and workspace exception approved"
  - "Macro base f9ed175800257b228166dabe8b3ac9a55e74e237; agentos/README.md rules 7-8 preserve nightly generation and Git-derived dates"
  - "MAS-130 current Todo; MAS-129 current Canceled, read at pickup"
  - "Initial 561-open-PR files census and fresh 560-open-PR refresh with 9 changed heads; no failed pages; exact-head reads for hook incumbents"
  - "PR #8107 remains open at 22a5d577f0b4427309348ce7e8a9360b039a1650, no local branch/worktree or active local modifier found; published source effect retained"
  - "#8107 changes root admission and PreToolUse; W4 must independently preserve that behavior and cannot depend on its acceptance"
  - "PR #6980 is an unaccepted design precursor; it is evidence, not a current execution lease"
affects:
  - WS:AGENT-OS
  - MAS-130
  - scripts/agentos.py
  - .claude/hooks/ship_loop_guard.py
confidence: high
reversibility: easy
decided_by: session
decided_at: 2026-10-04
---

The capture changes only an existing wave's PR association and, for a newly created PR,
`todo` or `in_progress` to `awaiting_ci`. It never marks a wave done, edits workstream
status or priority, stages or commits, creates a record, calls a network service, or
writes generated `created`/`updated` fields. The normal next commit derives freshness.
An equal PR is idempotent; a conflicting association needs ordinary authored reconciliation.

Binding uses an exact, nonexpired branch claim first. If no current exact claim exists,
every supplied changed path must resolve to the same sole owner using the existing
repository-aware path matcher. The submitted canonical Workstream and Wave must agree
with that result. No unique binding means no write. Advisory claim/release helpers
preserve the existing schema and cannot erase someone else's claim.

The PostToolUse adapter contains exceptions and enforces a bounded child deadline.
A separate Stop hook emits only a user-visible systemMessage; the existing Stop guard
remains unchanged. Neither helper changes guard state or emits a blocking decision.
The first capture produces ordinary tracked dirt and reports that explicitly. Only the
normal commit/PR/merge flow makes the knowledge durable. Implementation, exact-head CI,
independent review and cold recovery remain acceptance gates; this decision is not their receipt.
