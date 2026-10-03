---
workstream: WS:PROPHET-US-V4-RECOVERY
session: sol/event-workspace-clock-index-k4g-20260918
model: sol
ended_because: complete
prs: [7426]
mission: >
  Close the two exact-head K4-G review blockers without reopening CI traffic-jam work:
  preserve legacy-current when first-v3 migration coincides with a correction, and make
  workflow retries reuse one stable logical-operation mint clock.
state_before: >
  PR 7426 source head cbd7a816 was development-proven, but an interrupted Sol turn left
  six uncommitted repair files and no verified effect receipt.
changed:
  - path: engine/company_intelligence/event_workspace.py
    what: Retain a distinct verified legacy-current revision before a fresh first-v3 self row.
  - path: scripts/refresh_event_workspaces.py
    what: Require and parse an explicit timezone-aware operation clock at the CLI boundary.
  - path: .github/workflows/company-intelligence.yml
    what: Resolve the stable workflow-run creation clock through the existing GitHub Actions plane.
  - path: research/company_intelligence/2026-09-20-k4g-migration-operation-clock-repair.json
    what: Exact source, TDD, verification and non-claim receipt for semantic head b4f0aeb0c0e176813c8e43f2170ba121075a8894.
verified:
  - claim: The interrupted turn had a known, same-carrier effect rather than no effect.
    command: local/remote head, worktree status, diff and process reconciliation.
    result: Exact remote/local parent cbd7a816; six bounded uncommitted files; no active writer process.
  - claim: Both blockers have discriminating RED/GREEN evidence.
    command: Test-only overlay on parent, then identical tests on repaired source.
    result: RED 8 failed/3 passed; GREEN 11 passed.
  - claim: The complete owning capability remains green.
    command: Eleven native Prophet/Company Intelligence suites.
    result: 596 passed, zero failures, 15 existing warnings.
  - claim: PR code-gate ownership still executes the source and regression suites.
    command: test_company_intelligence_workspace_chain_is_executed_by_pr_code_gate.
    result: 1 passed.
  - claim: Durable source remains structurally valid.
    command: git diff --check; py_compile; scripts/agentos.py validate.
    result: PASS; PASS; 1139 records, zero errors, 88 existing warnings.
unverified:
  - claim: R2 has accepted a real v3 publication.
    what_would_verify: Normal post-merge publication plus marker/index/workspace readback.
  - claim: A real entitled user can complete the covered and typed-unavailable journeys.
    what_would_verify: Existing issue 6797 production HTTP/browser acceptance.
  - claim: Independent review accepts exact semantic head b4f0aeb0c0e176813c8e43f2170ba121075a8894.
    what_would_verify: MastermindX1 exact-head review return.
unresolved:
  - PR remains DRAFT / HOLD-FOR-SOL, unmerged and undeployed.
  - CI pack congestion is deliberately not treated as a product-work blocker or as acceptance.
  - Quality Earnings +1y identity, B-17, rights and 21-session evaluation remain separate.
next_actions:
  - Push the exact semantic head and request fresh independent review.
  - Repair only a demonstrated exact-head finding.
  - After accepted review and ordinary merge, prove incumbent R2 v3 publication/readback.
  - Resume issue 6797 real entitled covered and typed-unavailable browser proof.
do_not_redo:
  - Do not replay the 178-generation source census without a material source-generation invalidator.
  - Do not rebuild v3, B1, D5, authentication, the candidate population or the +1y compiler.
  - Do not re-open the unrelated CI traffic-jam lane.
danger_areas:
  - Workflow-run created_at is a mint/reconciliation clock, not a legal source clock.
  - The repair does not merge, deploy, publish R2, authenticate a user or inspect market outcomes.
---

# K4-G migration and operation-clock repair

Exact semantic source head: `b4f0aeb0c0e176813c8e43f2170ba121075a8894`. Both bounded blockers are closed in source and native tests; release and production proof remain separate.
