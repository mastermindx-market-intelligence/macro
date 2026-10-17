---
workstream: WS:DATA-OS-COMPLETION
session: claude/dataos-records-w3c-2026-10-14
model: fable
ended_because: ci_handoff
mission: Complete the equity-data contract through three real consumers under one declared view contract (Terminal daily OHLC + data-origin readout, DataWorkspace canonical read, basket composition), with independent proof and installed production reads; this handoff records the consumer, verification and acceptance waves as of 2026-10-17 12:2xZ.
state_before: Waves 1-2 landed (handoff 2026-10-13). Consumer wave (ORCH-3) and verification + acceptance wave (ORCH-4) delivered as DRAFT PRs over M2 fabric lanes; the seat wired every delivered lane into CI (legacy-jobs.yml jobs dataos-consumers / dataos-verification / dataos-acceptance), repaired the reds it owned, and merged C01-C03, the wire-3 exports and U03 at their exact heads.
changed:
- path: research/data_os_completion/2026-10-13/D00_SEMANTIC_DECISIONS.md
  what: "D00.D3 clarification (ABSENT vs UNRESOLVED) inserted before D00.D4; Amendments bullet D00.A2 (2026-10-17)."
- path: agentos/decisions/DEC-DATAOS-D00-D3-ABSENT-VS-UNRESOLVED.md
  what: "Seat ruling closing ORCH-4 finding Q01-F1: an INFERRED split observation makes the window UNRESOLVED and the SADJ / total-return views refuse NOT_CONFIRMED; the Q01 oracle pin was inverted in #9273 (b1ca917a0b7d), no library change."
- path: agentos/workstreams/WS-DATA-OS-COMPLETION.md
  what: "consumer wave prs extended (9185, 9188, 9210, 9218, 9220, 9226, 9234, 9236, 9237, 9241, 9539); verification-acceptance in_progress with [9273, 9275]; new decision listed; next_action rewritten for the merge/baseline/wire-5/R02/R03/C00 sequence."
- path: agentos/handoffs/DATA-OS-COMPLETION-2026-10-17.md
  what: "This handoff."
verified:
- claim: C01, C02, the lint heal, C03, wire-3 and U03 are merged and every path of each merged head is byte-identical on origin/main.
  command: git fetch origin main (alone, exit status checked); per path git rev-parse origin/main:<path> vs git rev-parse <head>:<path> (scratchpad/orch/o1/seat/land_proof.sh <pr> <head40>); transient 'cannot lock ref' races re-run, never read as a miss.
  result: "C01 #9188 squash 6b154e093573; C02 #9210 5a7d43b9ba04; heal #9234 80df7978789e; C03 #9218 91a67bb23cad (3 paths, 0 missing, 11:08Z); wire-3 #9220 8ab6617a8fdc; U03 #9236 a9939167d46b at exact head 884d2e2834f0 (4 paths, 0 missing, 12:15:53Z)."
- claim: Every red seen on the open DRAFT PRs on 2026-10-17 is attributed, and only one was the PR's own.
  command: gh api repos/mastermindx-market-intelligence/macro/actions/jobs/<id>/logs > file; grep -a -E '^.{0,40}(FAILED|ERROR) ' file | sort -u
  result: "(a) tests/test_recurring_briefs.py weekly-zh pair = main-inherited (reads committed site/master_brief.json; healed on main by #9517 at 11:42Z; remedy = refreshed merge ref via update-branch or the next push). (b) contract-delta uncovered-closure counts on dataos-verification (29) / dataos-acceptance (2) = closure gap after main's lib/dataos web seam grew; fixed by paths widenings 0e7ee91b73d4 (#9273) and a452b2c87885 (#9275). (c) #9273 ci-pack-11: Q03 smoke errored at setup because bench_q03.git_show read spec commit 5569baad… under the pack's fetch-depth 1 checkout; fixed by d21798328fd8 (_ensure_commit: git cat-file -e, else git fetch --depth=1 origin <sha>, mirroring ci.yml's contract-delta base fetch)."
- claim: The Q01 oracle finding F1 is closed by ruling, not by a library change.
  command: python3 -m pytest tests/verification/test_oracle_q01.py -q -p no:cacheprovider (in the verification lane tree at b1ca917a0b7d)
  result: "50 passed; test_Q01_06_not_confirmed_is_a_typed_refusal_by_ruling replaces the strict-xfail pin; Q01_ORACLE.md FINDING F1 CLOSED-BY-RULING."
- claim: The wire-4 export batch is concluded green at its exact head.
  command: gh pr checks 9539 --json name,state --jq '.[]|select(.state!="SUCCESS")'
  result: "Only the known-spurious ci-authority/codex/merge-queue-pilot FAILURE and fork-only SKIPPED rows remain at fd28501661d4 (145 names exported)."
unverified:
- claim: U04 #9241, C04 #9226, M01 #9237, verification #9273 and acceptance #9275 conclude green at their current heads and land.
  what_would_verify: One watcher per PR (watch_pr.py 180 s) reporting failed=0 pending=0; merge_exact.py at the exact head; land_proof.sh 0 missing against freshly fetched origin/main.
- claim: C04's sidecar is produced by the nightly and the Terminal readout leaves the unknown state.
  what_would_verify: The first daily.yml run after C04 lands commits data/stocks/_view_contract.json; an anonymous read of the Terminal chart status area shows basis = tradj and the per-ticker src (R03 / consumer A PRODUCTION_PROOF).
- claim: The Q03 shallow-checkout fix makes the smoke pins pass in CI.
  what_would_verify: ci-pack-11 SUCCESS on #9273 at d21798328fd8 (the pins skip on macOS, so only the ubuntu run proves it).
unresolved:
- "Q02-F1 (ORCH-4): an unreadable basket-history parquet is answered as basis=current_membership, so a read failure reads as 'no history yet' — route to the basket reader (U04 lineage, lib/dataos/basket_read.py) as a typed refusal after U04 lands."
- "A01-F1 (ORCH-4): VendorAliasTable grants rename continuity without evidence_sha256 on non-polygon vendors — route to the identity owner (lib/dataos/identity.py, M01 lineage); not a C00 blocker, recorded as a carried gap."
- "Q03 GAP 1 (ORCH-4): eager lib/dataos/__init__ imports of price_views / read_contract cost about +26 ms per CLI process (14 REGRESSION verdicts); the fix is a lazy export under lib/dataos/__init__.py, a seat edit (single writer) — schedule with wire-5. GAP 2: R3 describe is +92 B and its digest changes; accepted as a documented delta."
- "A03-F1 / A03-F3 / A03-F2 (ORCH-4): a mid-publish crash leaves a torn visible set under A's receipt and daily.yml commits it; a later refusal certifies the tear as last-good; refusals leave no durable failed-generation record; rollback is an operator git revert with no generation id or current pointer on data/reference — carried to C00 as EXPLICITLY UNFINISHED acceptance evidence unless a bounded publish-receipt packet is commissioned after R03."
- "A02 (ORCH-4): rights/refusal field on GenerationRef, current-mode price view, and the new-day + vendor-revision legs are unexercised by the acceptance journey — carried."
- "CI-authority freeze: #9241 (U04, edits .github/ci/legacy-jobs.yml) and #9226 (C04, edits daily.yml) will freeze their merged heads until a green ci.yml run on a main descendant; dispatch ONE baseline after they merge, never over a live run (39028524650 was live at 11:23Z)."
- "The verification and acceptance PRs both add a job to .github/ci/legacy-jobs.yml; the second to merge needs gh pr update-branch before its exact-head merge."
next_actions:
- "Consume the six watchers (U04 #9241 @4b087850b4ef, C04 #9226 @36bcb49aecd4, verification #9273 @d21798328fd8, acceptance #9275 @a452b2c87885, M01 #9237 @8f2852f79717, wire-4 #9539 @fd28501661d4): on concluded green, merge_exact.py <pr> <head40> --merge then land_proof.sh <pr> <head40>; on a genuine red, attribute from the job log before touching anything."
- "After the CI-authority merges: scratchpad/orch/o1/seat/baseline.sh preflight, then ONE gh workflow run ci.yml --ref main over a clear field; ONE watcher."
- "Wire-5 from the seat: export read_view (U03), the U04 names (read_basket, BasketRead, population_delta, PopulationKind, EvidenceMode, BasketRefusalCode, BasketReadRefusal) and the M01 names; fold the Q03 GAP 1 lazy import into the same single-writer edit."
- "R02 after R01 + A02 + M01: three separate receipts (installed, selected, consumed) per the seat closeout plan; Terminal release via the documented build script on the Terminal box, never reading its env."
- "R03 = the first nightly daily.yml after C04 lands; compare generation invariants cycle 1 to cycle 2; never dispatch daily.yml."
- "Final records PR: C00 closeout matrix (research/data_os_completion/2026-10-13/C00_CLOSEOUT_MATRIX.md) with every package at its proven rung, open carriers empty."
do_not_redo:
- "C01 #9188 (6b154e093573), C02 #9210 (5a7d43b9ba04), heal #9234 (80df7978789e), C03 #9218 (91a67bb23cad), wire-3 #9220 (8ab6617a8fdc), U03 #9236 (a9939167d46b) are merged and landed at their exact heads; do not re-judge, re-merge or re-heal them."
- "The Q01-F1 ruling (DEC:DATAOS-D00-D3-ABSENT-VS-UNRESOLVED) is taken; do not re-open the oracle pre-registration or change price_views to compute factor 1."
- "The paths widenings (0e7ee91b73d4, a452b2c87885) and the Q03 shallow-checkout fetch (d21798328fd8) are pushed; the edit scripts assert their anchors and must not be re-run."
- "ORCH-3 and ORCH-4 returned and were consumed; never re-spawn them. Terminal #996 is consumer A's PRODUCTION_PROOF; never redeploy or re-merge it. #9147 stays CLOSED (content landed via #9152)."
- "The weekly-brief red (tests/test_recurring_briefs.py) is healed on main by #9517; it is never a lane's red to fix."
danger_areas:
- "lib/dataos/__init__.py is STDLIB-ONLY at import time with one writer (the seat); wire-4 #9539 is that writer's batch — a lane must never edit the export list."
- "Any edit under .github/ci/**, .github/workflows/** or app/deploy/update.sh freezes the merged head's CI authority; only a green ci.yml run on a main descendant clears it, and a re-dispatch over a live main run cancels the proof every pinned session is waiting on."
- "A push into an armed merge-on-green PR can land after its merge with no error; the seat never arms the label and merges by hand at the exact head."
- "bench_q03.py reads a spec-pinned commit with git show; the CI pack checkout is fetch-depth 1, so any new spec commit must stay reachable through the _ensure_commit fetch (never assume a full clone in CI)."
- "Tiingo paths and the twenty PROPOSED Tiingo registry rows belong to WS:TIINGO-DATA-OS; declaring their names in a CI paths list is not touching them, editing them is."
- "A sparse session tree truncates committed data/ and site/ artifacts on an unredirected write; never git add -A, and read sparseness with scripts/worktree_sparse.missing_dirs(), not is_dir()."
---

## Reading order for the next session

1. `agentos/workstreams/WS-DATA-OS-COMPLETION.md` `next_action`, then this file's `next_actions`.
2. The seat's closeout plan and matrix draft live in the seat scratchpad (`orch/SEAT_CLOSEOUT_PLAN_R01_R03_C00.md`, `records/C00_CLOSEOUT_MATRIX_draft.md`); the final matrix is committed by the last records PR.
3. Verify every landing against freshly fetched `origin/main`; a merged PR is a fact about the pull request, never about the bytes in the folder you are standing in.
