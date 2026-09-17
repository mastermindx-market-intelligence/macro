---
workstream: WS:GMI-THEME-GRAPH
session: sol/sector-cycle-observations-r4-20260916
model: sol
ended_because: blocked
mission: >
  Advance the existing Finviz/Sector/Theme/Cycle Intelligence programme by qualifying the
  first real Matrix population and its cap, overlap, clock and identity requirements,
  without restarting accepted P1 review or changing the independent publication owner.
state_before: >
  P1 source/visual review and current-base compatibility were accepted at e6795e1a;
  P1 and freshness #7211 still had queued execution packs. Prior scope work knew aggregate
  cap coverage but not which whole themes disappeared or how the selected population changed.
changed:
  - path: research/sector_cycle_revamp/R8_REAL_ATLAS_SCOPE_QUALIFICATION_2026-09-17.md
    what: >
      Record source-bound per-group cap coverage, overlap and distinct-key diagnostics;
      preserve descriptive-only semantics, explicit next-scope constraints and the
      independently reviewed research result. Separate Terminal sizing finding is #609.
verified:
  - claim: P1 and publication source identities remain unchanged; prior reviews need not be redone.
    command: gh pr view 7252/7211; exact-head run reads; git rev-parse HEAD and git status; bounded new comments
    result: >
      P1 e6795e1ae34c84e32ae9092779d358660ae8e5f5, OPEN/DRAFT; publication
      9b01c9bcae2b12f23ab0a2ab3a5054f81dcade02, OPEN/APPROVED. P1 has four
      successful planning/admission/contract jobs and twelve queued packs; publication
      has seven successful jobs and nine queued. Compatibility returns 5721421695 and
      5721486423 are accepted existing evidence, not rerun by this research.
  - claim: Real scope and missing capitalization conserve the complete existing population.
    command: qualify_scope.py against hash-bound input_manifest.json and accepted P1 source
    result: >
      49 groups, 1020 appearances, 702 distinct source keys; 500 positive cap string matches,
      198 absent keys and four present-invalid entries. Thirteen groups complete, five
      with zero cap matches. Identity references all null; resolved issuer/security counts
      stay null. Source-key observations remain available even when size is missing.
  - claim: Different population weightings materially change the descriptive answer.
    command: set-based population calculation and pandas conservation cross-check over the same derived rows
    result: >
      Strict200 above/observed is 343/693 for the distinct-key union, 267/499 for cap-matched,
      76/194 for unmatched and 519/1010 for appearances. These are one-snapshot descriptive
      diagnostics, not independent-source verification, a market verdict or predictive evidence.
      The cap-based partition itself uses the later September17 cache.
  - claim: Discriminating input and missingness checks passed without production changes.
    command: python3 verify_scope.py --repo-root <accepted-P1-worktree>
    result: >
      Nineteen size/invalid boundary cases, two NumPy numerical checks, deterministic repeat,
      conservation checks and seven corrupt/duplicate/missing/permuted input cases passed.
      The inner pulse-binding case refreshes the outer manifest before requiring refusal.
  - claim: Independent research review actually executed and terminated.
    command: native reviewer 36f2e88c-71dc-4fa8-9181-33fa6b9896ff; before/after input hashes; final result readback
    result: >
      PASS for research conclusions, no blocker/major, exit0 and twelve turns. Read/Grep/Glob
      only, plan permissions, no MCP. Parent executed tests; reviewer did not. Minor precision
      and verification refinements incorporated without changing core counts. Child accepted
      and terminal in comment5721701884, no watcher or successor assignment.
  - claim: Existing Terminal CAP mode has a verified source-level semantic mismatch.
    command: pinned Terminal source inspection and Node execution of exact tileValue body, TS annotations removed only
    result: >
      Terminal75c22083249e7a1529be3d6baf819b9ad5ea509f: enabled CAP/市值 chooses
      price*volume while ingest already emits optional mcap that the UI join drops.
      Controlled 100x mcap change leaves weight unchanged;10x volume changes weight10x.
      Source-only finding retained in Terminal#609; no deployed/browser incident asserted.
unverified:
  - claim: Full exact-head CI and P1 production publication.
    what_would_verify: >
      Existing GitHub jobs conclude, source release is adjudicated, incumbent#7211 integrates
      actual-invocation and companion/detail checks, then authenticated production proof.
  - claim: Full cap-weighted, identity-resolved Matrix and lower-cap coverage.
    what_would_verify: >
      Existing cap/identity owners supply qualified complete scope, source clocks and rights;
      first shared real Grid/Clusters/Bubbles/table journey is implemented and browser-proven.
  - claim: Terminal#609 repaired or deployed.
    what_would_verify: >
      Lawful source custody, bounded label/typed-join repair, discriminating mounted tests,
      required CI, existing release procedure and production browser proof.
unresolved:
  - Shared execution queue remains with existing CI owner#6351; do not create or bypass a pool.
  - Publication source remains with incumbent#7211; updated integration contract5711957268 is not pickup evidence.
  - Cap date09/17 differs from observation09/16; no PIT or historical screen claim.
  - Public source rights and issuer/security resolution remain existing-owner decisions.
  - Research post-normalization duplicate-key refusal has no dedicated isolated test; do not claim otherwise.
next_actions:
  - Reconcile this records-only publication on the existing research branch and preserve Draft/HOLD.
  - Advance Terminal#609 only after its source/workspace/release custody is established; do not hide dollar volume behind cap labels.
  - Consume full P1/publication hosted proof without repeating accepted reviews or path-disjoint integration runs.
  - Build the first complete real house-catalogue view under the accepted P1/publication gate, retaining missing-size members and explicit scope.
do_not_redo:
  - R1–R7 Finviz archaeology, full R4 reproduction and R5/R6 synthetic renderer.
  - Accepted P1 source/math/visual repairs and both closed native reviewer assignments.
  - P1#5721421695 and publication#5721486423 current-base compatibility receipts absent material invalidator.
  - Reconstructing another graph, identity resolver, cap collector/cache, state store, publisher, queue or retry owner.
  - This R8 research review on unchanged conclusions; use the retained report and refinements.
danger_areas:
  - 702 source keys are not 702 verified securities or issuers.
  - Missing cap is not zero, a tiny bubble, or permission to erase a group.
  - Overlapping group appearances are not independent confirmation; different weighting is not contradictory data.
  - A read-only review PASS is not test execution by the reviewer or product acceptance.
  - Raw native event logs contain reasoning and must not be exported.
prs: [7234, 7252, 7211]
---

## Current authority and effect boundary

Current Chairman continuation is the same parent programme. Protected procedure pin:
Mastermind `b731149296a9d837d426730813f68d5acc6133ac`, Skillpack1.0.1.
Research publication remains the original #7234 branch `sol/sector-cycle-observations-r4-20260916`.
Preimage `b25bd018a15b9cd742e420002a222ffb64552eb2`. No product or publication branch was changed.

Exact research evidence root:
`/Volumes/Mastermind/agent-evidence/sector-cycle-atlas-scope-qualification-20260917-sol-001`.
The source-bound manifest, inputs, diagnostic scripts, results, tests and sanitized final review are retained.
Report/result hashes are in the R8 report; Terminal source counterexample is separately retained there.

The research reviewer operation `sector-cycle-atlas-scope-review-20260917-sol-001` is terminal.
No worker, watcher, source release, deployment or full-program completion is asserted by this handoff.
