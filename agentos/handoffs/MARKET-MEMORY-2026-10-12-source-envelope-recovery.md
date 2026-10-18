---
workstream: "WS:MARKET-MEMORY-W2C"
session: claude/ssd-market-memory-source-envelope-01a1333c-1e5ac1c3100c5bc2
model: codex
ended_because: ci_handoff
mission: >
  Continue the Chairman-assigned Market Memory program on parent PR 6528;
  repair the documented SPY source envelope and qualify the hosted page-test path.
state_before: >
  The installed October 10 source journal retained 30 malformed_bar observations
  and no valid digest. The parser required a ticker inside each aggregate row,
  although the single-ticker provider response binds ticker on its envelope.
  Source admission and the full production program remained unproven.
changed:
  - path: engine/neuralweb/market_memory_sources_spy.py
    what: Validate rows in explicit SPY envelope context while preserving strict standalone validation and exact result digests.
  - path: scripts/ingest_market_memory_sources_spy.py
    what: Require SPY and adjusted exactly false on the response envelope before admitting unchanged result rows.
  - path: tests/test_market_memory_m0d_v2.py
    what: Add envelope identity, adjustment, conflicting row, stability and original-byte regression cases.
  - path: .github/ci/legacy-jobs.yml
    what: Run the data-free page suite with its actual Node runtime inside the existing public-render-fastlane code job and normal inferred dependency closure.
verified:
  - claim: The complete owning M0D v2 suite passes after the reviewed repair is applied.
    command: python3 -m pytest tests/test_market_memory_m0d_v2.py -q --disable-warnings
    result: 206 passed in 19.30 seconds on base c62db362946cfb4e5a84685b3a7a79db68c3cee3.
  - claim: Independent principal review accepted the exact source proposal before integration.
    command: >
      Read science/PARSER_INDEPENDENT_REVIEW.json and hash the retained
      integration/patch/parser-envelope-unapplied.patch in the root evidence directory.
    result: >
      PASS on SHA256 d5cea3a2d04d76b83cc59f65439f68ea1525d3d8f21fb394af695df829f9b4ae;
      review caught and closed the response adjustment guard before acceptance.
  - claim: Page runtime and protected CI planning remain valid with the new registration.
    command: >
      Run the owning page suite and the focused CI authority, plan, semantic-change,
      loader and security regressions recorded in the source recovery PR.
    result: >
      Final combined render/page/glossary/finance command: 102 passed, one
      pre-existing deselection. The same nine suites now share one pytest process;
      explicit Node 20 runtime/preflight and all dependencies remain registered.
      On current-main union aaa11157958c20643b273e582943d0f629f1f360, protected
      planner measurements preserve every selected job and total weight on all
      three narrow-change probes: 134/5797/10, 134/5600/10 and 129/5560/10
      (jobs/weight/packs), within unchanged ceilings. Final applied-manifest
      loader/security checks passed 10; hosted contract-delta and code packs remain required.

unverified:
  - claim: Source repair is merged, installed and produces an authentic natural sealed capture.
    what_would_verify: >
      Concluded exact-head review and CI, normal merge/deployment, installed file hashes,
      then one ordinary scheduled 04:00-04:05 UTC seal with actual immutable receipts.
  - claim: Held issuer-intent repair and full Market Memory production capability are accepted.
    what_would_verify: >
      Preserve PR 8694, qualify its exact updated source through actual owning hosted tests
      and authenticated browser evidence, then complete the original program's population,
      retrieval, three consumers, three modes, rights, recovery and usefulness gates.
unresolved:
  - Source patch does not identify every discarded historical response or backfill missed captures.
  - Exact public catalog reads exceed the frozen ancestry budget; a distinct certified-lineage successor is accepted in design only.
  - Retained macro outputs remain training-ineligible; outcome-blind population and fit admission are separate obligations.
  - PR 6943 has a historical release but obsolete D1 next-action text; do not merge unchanged.
next_actions:
  - Finish this carrier's protected CI registration checks and source review, push and complete the normal ship chain.
  - Inspect installation and preserve the next natural seal receipt without replaying a writer.
  - Adopt the held UI carrier through controlled current-main integration, owning checks and browser proof before release.
  - Implement the accepted outcome-blind population and versioned certified-lineage contract under existing owners.
do_not_redo:
  - Preserve accepted August MM-G0 ABSTAINED and the installed D1 diagnostics; do not rerun the old gate.
  - Preserve the original parent operation market-memory-full-capability-20260827-sol-001 and PR 6528.
  - Keep held PR 8694 and its source delta; do not create a competing UI implementation.
  - Do not raise the v1 ancestry cap, return early, change source quality flags or mutate synthetic W4A/W5A profiles.
  - Do not change schedules, seal predicates, historical source bytes or the zero-byte September 4 record.
danger_areas:
  - A successful service exit, source test, CI job or merge is not a qualified natural capture.
  - A valid result row must not be labelled unadjusted solely because the request asked for adjusted=false.
  - The same source result bytes define the seal digest; do not insert synthetic row ticker fields.
prs: [6528, 6943, 8694, 9078]
---

The assigned native root is `01a1333c-a475-7052-95a8-72c623fb12e1`.
The published recovery checkpoint and concrete proposals are retained on the
[existing program carrier](https://github.com/mastermindx-market-intelligence/macro/pull/6528#issuecomment-6137839017).
That checkpoint's local SSD refusal was subsequently resolved: the approved helper
minted this sparse, protected source tree on the verified external pool.

Two verified Sol coordinators used the installed M2 shell Fabric. The science run
settled before model execution with a capacity refusal. The integration operator
on Ubuntu1/GLM5.3 returned through its original carrier and was consumed and accepted
for its bounded source census. No nested worker started and missing usage receipts
prevent a token/cost claim. No Executive plugin dispatch was used.

All 28 tasks and 49 acceptance cases remain in scope. This file is a continuation
record while the same root continues delivery, not a completed-program handoff.
