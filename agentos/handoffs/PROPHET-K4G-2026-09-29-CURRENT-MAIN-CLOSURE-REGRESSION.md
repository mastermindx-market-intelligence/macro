---
workstream: WS:PROPHET-US-V4-RECOVERY
session: claude/k4g-closure-regression-record-20260929
model: opus
ended_because: blocked
prs: [7426]
discoveries: ["DSC:EXCLUSIVE-SUITE-PATH-LITERALS-PULL-IMPORT-CLOSURE"]
mission: >
  Independent principal record for MACRO-02 (event correction clocks and reader explosion).
  Commission: adopt the existing #7426 carrier after source/ownership reconciliation rather
  than start a duplicate implementation, and own reproduction, current-tree integration,
  independent review, publication-ordering proof and durable closeout. This record exists
  because everything below was measured against a main that #7426's head predates, and none
  of it is visible from either tree alone.
state_before: >
  #7426 is OPEN, DRAFT, zero labels, autoMergeRequest null, reviewDecision empty, head
  7bc04876747d773861b47519061279ae033a148d, last carrier edge 2026-09-25. Its body records a
  HOLD-FOR-SOL with four remaining gates: a MastermindX1 exact-head review, a source-owner
  merge adjudication, R2 v3 publication with readback, and the #6797 entitled production
  proof. No durable record of the defects reproducing on live production bytes existed, and
  no publication-ordering proof had been produced by anyone.
changed:
  - path: "agentos/discoveries/DSC-EXCLUSIVE-SUITE-PATH-LITERALS-PULL-IMPORT-CLOSURE.md"
    what: "The mechanism and the measured reason the closure test's own prescribed remedy is the wrong one here. Records only - this carrier contains ZERO code paths and no part of the K4-G implementation."
  - path: "agentos/handoffs/PROPHET-K4G-2026-09-29-CURRENT-MAIN-CLOSURE-REGRESSION.md"
    what: "This record."
verified:
  - claim: "Both packet defects reproduce on live production bytes, read-only, with no credentials."
    command: "scratchpad repro_chain.py - walk of the public origin pub-f7ffb4441c5f4ad983ca56ec7c651c61.r2.dev/company_intelligence from the marker generation"
    result: "Marker generation 91d7f0f86e443ba593f89d00, schema event_workspace_manifest.v2, revision_index.json ABSENT. Chain depth 189, 190 requests, 47.746s against a 15-second consumer budget, 15450 workspace objects, schema histogram {v2:188, v1:1}. All 189 generations carry an identical generated_at of 2026-07-30T20:30:28Z while event_count genuinely varies (5, 6, 146, 142, 20, 14). Gate 3 is therefore demonstrably not done in production."
  - claim: "The carrier's payload integrates into current main as exactly 20 paths with the source unchanged."
    command: "git merge of 7bc04876747d into main pinned at 1df73c1ac9289a21e192aeb50088a4f9119aee82 -> ea77f5888519d5892de55887ad045a7b60a56559; git diff --stat against the pinned SHA"
    result: "20 paths, +4058/-89, patch digest 737633a7258f06750ccb580a99a45f576a411e198db6de27538e994351aec0c6, composition 12 modified-at-base and 8 new-in-payload. git diff --check clean, compileall clean."
  - claim: "Publication ordering holds under failure injected at every boundary."
    command: "scratchpad pub_order_harness.py - 11 injection points across write_workspace_generation_v3 and the R2 publication path"
    result: "11 boundaries, 0 ordering violations. workspaces -> revision_index.json -> immutable manifest.json -> marker LAST held at every boundary; no partial state exposed a marker ahead of its index. Typed classification correct throughout: 2 WorkspaceChainNotPublished, 5 WorkspaceChainIntegrityError."
  - claim: "The payload reds test_curated_exclusive_scopes_cover_their_own_import_closure only when it meets current main, and the cause is four string literals."
    command: "scripts.run_ci_pack.curated_exclusive_closure_findings(Path('.github/ci/legacy-jobs.yml')) across five tree states"
    result: "Payload applied 33 uncovered on ci-control-plane-contracts; tests/test_ci_pack.py alone reverted 0; only the four owned_sources source-module literals removed 0; those literals relocated to a prophet-lab-owned suite 0; restored 33. Base side clean at BOTH 1df73c1ac928 and 877754f2053c, so the red is payload-caused and not inherited."
  - claim: "Widening the job's paths - the remedy the test's own message prescribes - passes CI while silently putting that job on every PR in the subgraph."
    command: "select_jobs on four probe paths before and after adding the 33 paths; pytest -k 'curated_exclusive_scopes_cover_their_own_import_closure or exclusive_curation_narrows_ordinary_code_prs'"
    result: "2 passed with the widening applied. But engine/company_intelligence/event_workspace.py goes 84 jobs/1947 weight -> 85/3347 (+72%), engine/earnings_narrative/story.py 88/2248 -> 89/3648 (+62%), engine/neuralweb/company_intelligence_reader.py 84/2201 -> 85/3601, config/earnings_story_promotion.yml 86/2254 -> 87/3654. The packing probes sit on templates/index.html, scripts/build_free_content.py and engine/prophet/plan_book.py, none in the subgraph, so they cannot detect it."
  - claim: "Owner suites pass on the integrated tree."
    command: "python3 -m pytest on the four owner suites, then on the three remaining payload suites (Python 3.14.7, full non-sparse checkout)"
    result: "168 passed on the owner suites. 402 passed, 1 failed, 2 skipped on the remainder; the single failure is the closure test above and is not a defect in the PR's own source."
unverified:
  - claim: "The relocation remedy is the one the source owner should take."
    what_would_verify: "Owner adjudication. The measurement says relocation is clean at zero selection cost, but choosing between relocation, widening and dropping the assertion is the carrier owner's call, not a measurement's."
  - claim: "The 33-path finding still holds against whatever main exists when #7426 is finally rebased."
    what_would_verify: "Re-run curated_exclusive_closure_findings on the payload merged into the then-current main. Measured at 1df73c1ac928; base side separately re-checked clean at 877754f2053c."
unresolved:
  - "Gate 1 - MastermindX1 exact-head review. External. Deliberately NOT supplied by this session: the packet forbids manufacturing independent approval by changing accounts, and this fleet shares one GitHub identity."
  - "Gate 2 - source-owner merge and release adjudication. Sol's; DEC:SOL-HOLD-IS-A-MERGE-BARRIER in force."
  - "Gate 3 - R2 v3 publication with readback. R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET and R2_ENDPOINT all unset; no aws or rclone config; and logically downstream of merge."
  - "Gate 4 - #6797 entitled production proof. Needs operator-held authentication."
next_actions:
  - "Carrier owner: decide the closure remedy. Relocation is measured clean at zero cost; widening is measured harmful and invisible to the probes. Do not merge #7426 into current main before this is settled - it reds ci-control-plane-contracts on its own head."
  - "Whoever rebases #7426: re-run curated_exclusive_closure_findings against the then-current main before pushing, since this collision did not exist when the head was written."
  - "Gates 1-4 above, in that order. Nothing downstream of them is actionable by a session without the corresponding credential or authority."
do_not_redo:
  - "Do not re-reproduce the two defects. Both are measured on live production bytes above with exact counts; the production marker is still v2 with no revision_index."
  - "Do not rebuild the publication-ordering harness. 11 boundaries, 0 violations, already measured."
  - "Do not suspect the payload's records or docs files for the closure red - removing all seven leaves 33. Do not suspect the manifest edit - reverting it leaves 33; its only change sits under prophet-lab, a different job."
  - "Do not apply the widening remedy the test message prescribes without first re-reading the measured cost above."
  - "Do not open a competing implementation branch. The commission forbids it and #7426 is the adopted carrier. The integration tree here is a local proof artifact, fully reproducible from two SHAs and the published digest; it was deliberately not pushed."
danger_areas:
  - "origin/main moves under a worktree mid-session because .git is shared across all worktrees on this clone. Pin the base by SHA and diff against the SHA, never against the ref - comparing against the ref once produced a wrong 22-path/+4072-147 reading here."
  - "Additive bisection lies in this class of failure. Every additive step returned 0 because the causing file was never re-added, flatly contradicting the A/B result. Subtract from the COMPLETE payload."
  - "git checkout <base> -- <paths> aborts entirely when ANY pathspec is absent at that base, which is true for every file the payload creates. With stderr suppressed it is a silent no-op that looks like a successful revert and produced one wrong retraction here. Classify modified-at-base from new-in-payload first."
  - "This is a sparse worktree by default. The full suite must not be run in one; opt in with scripts/worktree_sparse.py full first."
---

Delivery ladder reached: **CI on an integration tree**. Not MERGED, not PRODUCTION_PROOF, not
ACCEPTANCE. The evidence above is posted on the carrier as #7426 comment 5896690771; the head
`7bc04876747d` was not mutated - no push, no label, no ready-for-review, no merge - and the
recorded hold was left intact.
