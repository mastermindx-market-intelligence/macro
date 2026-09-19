---
workstream: WS:PROPHET-US-V4-RECOVERY
session: claude/prophet-lab-earnings-view-20260917
model: sol
ended_because: ci_handoff
mission: Deliver the existing native earnings-evidence presentation through the canonical private Prophet
  Lab, preserving D5 identity, decision clocks, corrections and authority.
state_before: A tested four-path candidate existed only in development evidence. No native source branch
  or PR existed. D5 PR 6705 is already merged and must not be rebuilt.
changed:
- path: app/prophet_lab.py
  what: Adds the private research-view endpoint over the existing D5 reader; reuses entitlement, kill
    switch and privacy headers.
- path: engine/prophet_lab/earnings_view.py
  what: Provides escaped EN/ZH earnings JSON/HTML presentation; preserves decision-time figures and later
    corrections.
- path: tests/test_prophet_lab_earnings_view.py
  what: Registers 37 native tests, including auth, identity, correction, null and authority boundaries.
- path: .github/ci/legacy-jobs.yml
  what: Adds only the new test path and command to the existing prophet-lab code gate.
- path: research/prophet_v4/earnings_view/2026-09-17-native-source-proof.json
  what: Records exact source hashes, actual native test results, prior browser evidence and unclosed release
    limits.
verified:
- claim: Exact development patch applies to current source without semantic modification.
  command: git apply --check native_integration.patch; git apply native_integration.patch; SHA-256 comparison
    of the four source files
  result: Pass on base c2ac0b8d3196cabfb84d9629b587ee3365509614; source hashes match the supplied tested
    candidate.
- claim: Native seven-suite battery passes in the linked source worktree with its real conftest.
  command: python3 -m pytest -q -p no:cacheprovider tests/test_prophet_lab.py tests/test_prophet_lab_api.py
    tests/test_prophet_lab_earnings_view.py tests/test_company_intelligence_workspace_chain.py tests/test_prophet_lab_timeparse.py
    tests/test_prophet_lab_commissioning.py tests/test_caddy_hub_boundary.py
  result: 490 passed, zero failures/errors/skips; 10 framework/OpenAPI warnings. Exact committed metadata
    prerequisites restored, no outcome file opened.
- claim: Candidate-owned module/router paths have no competing open PR in the observed field.
  command: Open PR heads plus exact merge-base path diffs, unresolved heads reconciled by GitHub changed-file
    reads
  result: 291 PRs checked; zero direct overlaps. PR 6625 changes the adjacent sources.py owner, not this
    slice. Shared manifest edits require hunk-level current integration.
- claim: Manifest remains parseable under its existing runner.
  command: python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --validate-only
  result: Exit 0; 214 jobs validated. This is not hosted execution.
unverified:
- claim: Hosted required CI and independent review pass on the published semantic head.
  what_would_verify: Concluded exact-head CI/security and actual independent review; not a review request
    or same-author comment.
- claim: A user can open the evidence in the entitled production frontend.
  what_would_verify: Mount on the actual private Operator Lab/Prophet path with a canonical B1 episode,
    then real entitled covered/unavailable/correction HTTP and browser proof.
unresolved:
- Existing Macro Pick Lab is not Operator Lab. Current Terminal plan types do not expose a B1 episode
  binding; do not invent a ticker-to-episode join.
- The separate +1y expectation-revision compiler remains NOT_CONNECTED. Its original compiler, B-17 population,
  identity, source/rights and Evaluation OS gates are not replaced by event evidence.
next_actions:
- Publish this exact branch once; reconcile push/PR effects before any retry.
- Conclude applicable hosted CI, obtain independent review and current-base integration proof without
  an ancestry-only rewrite.
- Mount the view through an exact canonical B1 episode path; never join an existing plan to an earnings
  episode using ticker alone.
- Use the existing normal deployment owner; prove entitled real source reads and browser behavior before
  PROVEN_LIVE.
do_not_redo:
- D5 Earnings compiler and PR 6705
- B1 identity, B3/B4 state, B-17 population and Evaluation OS
- 'The #7200 collector audit and comment 5233152327'
- The unchanged native earnings view and its tests unless material source/evidence changes
danger_areas:
- A same-author GitHub connection cannot supply independent approval.
- A later correction must never repaint the original decision-time values.
- Event revenue/guidance is not the forward-year EPS/revenue revision species.
- No rank, size, entry, hold, order or strategy-performance authority is created.
- Local build, source publication, CI, deployment and production acceptance are separate.
---

## Current authority and continuity

Current Chairman instruction continues the original native Lab upgrade. This operation owns only its new branch; no incumbent branch or runtime worker is reassigned. Direct delivery uses the existing tested candidate under LOWER_TOTAL_OVERHEAD. The correct source and durable organizational homes are Macro GitHub and this Agent OS handoff. No new runtime, queue, store, authenticator or publication service is introduced.
