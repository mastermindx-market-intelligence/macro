---
key: GMI-INDUSTRIALS-FIRST-VERTICAL
title: "GMI Industrials — first vertical: Exponent/Pentair result-to-cash dossiers (Fable Meta-CEO program)"
objective: >
  Implement the frozen Industrials nine-task plan on the Semiconductor-led shared
  foundation as fabric-built PRs in dependency order. Done means both real, signed-in
  Exponent and Pentair dossiers pass the T09 real-path proofs (two journeys, correction,
  revocation, ordinary refresh, non-interference) with every one of the 56 inherited
  requirements executed — never a merged slice alone.
status: blocked
program: earnings-intelligence
repos: [macro]
owner: fable-meta-ceo
class: build
blast_radius: user_facing
ambiguity: specified
owns_paths:
  - engine/company_intelligence/industrials_profiles.py
  - engine/company_intelligence/financial_dossier.py
  - engine/fundamental_forensics/industrials_result_cash.py
  - engine/market_ontology/industrials_theme_research.py
  - contracts/company_intelligence/financial_dossier.v1.schema.json
  - tests/industrials_result_cash_helpers.py
  - tests/test_industrials_*.py
  - tests/fixtures/industrials_result_cash/**
  - research/industrials/first_vertical_program/**
depends_on:
  - WS:EARNINGS-INTELLIGENCE-OS
  - WS:GMI-THEME-GRAPH
waves:
  - id: IND-W1
    title: "T01 synthetic corpus, helper harness, delivery-input validator, gate:code job industrials-result-cash"
    status: done
    pr: 7924
  - id: IND-W2
    title: "T02 issuer profiles || T04 pure result-to-cash derivations"
    status: in_progress
    pr: 8062
    depends_on: [IND-W1]
    next_action: "T04 half is DONE - MERGED 2026-09-27 06:04Z as 50549f8e839eff38a86568cbc2beb9d29fe0de81 from cd46f9452c77 (the adjudicated 0e3344a9071f plus one base-refresh merge; module and suite byte-identical), ci-gate and all twelve packs green on run 36296953418. Only the T02 half of this wave remains, and it is BLOCKED: it edits issuer_profiles.py / event_workspace.py / event_workspace_build.py / refresh_event_workspaces.py - FOUR seam files, not the three this record used to list. Re-checked 2026-09-27: #7905 (OPEN/DRAFT b6808dfcc166) holds only issuer_profiles.py; #7870 (OPEN/DRAFT a0d7b054ff23) holds all four. Do not dispatch T02 until they release the seam."
  - id: IND-W3
    title: "T03 case extractors, THEN T05 editions and comparisons (NOT parallel)"
    status: todo
    depends_on: [IND-W2]
    next_action: "Sequence is T03 then T05, not T03 || T05: the frozen plan lists T03 event/document refs among T05's consumed inputs, and T05's C0 gate also demands T02's industrials_profiles.py on main. A T05 lane dispatched early invents the document-reference shape rather than returning BLOCKED. The pre-built T05 payload stays parked."
  - id: IND-W4
    title: "T06 closed financial dossier contract and thin shared adapter"
    status: todo
    depends_on: [IND-W3]
    next_action: "T06 consumes T04 per rulings_t06.md R7-R8: quote T04's value or report T04's refusal, never re-derive; pin no receipt_id literal or golden receipt."
  - id: IND-W5
    title: "T07 private role, T08 typed view on the shared aggregator, T09 real-path proofs"
    status: todo
    depends_on: [IND-W4]
    next_action: "Wait for Semiconductor B's shared route family and aggregator on main; never build against #7870's branch."
next_action: >
  NOTHING IS DISPATCHABLE AT THIS SEAT. IND-T04b (#8105, 717e16cccc24) and the records pair
  #8109 (4e61869bfecd) are merged and verified in origin/main's own bytes; T01, T04, T02a and
  every records PR before them are closed. The honest state is ALL_SCOPED_LANES_BLOCKED:
  T02 waits on the shared seam held by #7870 and #7905, T03 on T02, T05 on T03, T06 on
  T01-T05, T07-T09 on Semiconductor B reaching main for G1. The unblocking act belongs to
  those PRs, not to this program - do not manufacture a lane, and do not dispatch T05
  (args_ind_t05_source_history.json stays PARKED; rulings_t05 R8 forbids it).
  Coverage is 15 of 56 as MEASURED (3 in T01, 12 in T04), never from the plan's table.
  Two absences are deliberate: tests/test_industrials_issuer_enrollment.py is not created
  and no anchor-map row exists for a T02 requirement - in both cases the absence is the
  honest signal that T02 is unstarted.
artifacts:
  - agentos/handoffs/GMI-INDUSTRIALS-2026-09-24-first-vertical-implementation.md
  - research/industrials/first_vertical_program/rulings/R-IND-2026-09-24-wave1.md
  - research/industrials/first_vertical_program/reviews/OPUS_T01_REDTEAM_2026-09-24.md
  - research/industrials/first_vertical_program/reviews/OPUS_T04_REDTEAM_2026-09-26.md
  - research/industrials/first_vertical_program/rulings/R-IND-2026-09-26-t05-source-editions.md
  - research/industrials/first_vertical_program/rulings/R-IND-2026-09-26-t06-financial-dossier.md
  - research/industrials/first_vertical_program/rulings/R-IND-2026-09-27-t02a-harness-gate.md
  - research/industrials/first_vertical_program/rulings/R-IND-2026-09-27-requirement-anchors.md
carrier:
  operation: gmi-industrials-fable-ceo-e2e-20260924-chairman-001
  research_pr: 7789
  records_pr: [7912, 7915, 7919, 8070, 8072, 8073, 8075, 8077, 8084, 8105, 8109]
do_not_redo:
  - "Research Waves 1-14, the nine-task plan (blob a5462dc7) and the 56-requirement traceability are frozen - do not re-research Industrials economics."
  - "R14-01..R14-05, the R4 private-mechanism choice and the #7669 aggregator choice are decided - never reopen the GET route or a direct mount."
  - "Never put implementation on the research carrier #7789; never edit #7870's branch."
  - "IND-T04b (#8105) delivers the 15 vendored anchor rows, the 13 built anchors and four cures (IND-D08 unit comparison, IND-D09 definition agreement, IND-D10 matched_pair_unequal, IND-R208 purpose comparison), mutation-verified 17/17. Do not re-derive them. Do not 'tidy' test_ind_d08_conversion_receipt_is_trusted_not_applied: it asserts the raw-magnitude value on purpose so that implementing the conversion FAILS it and the anchor is updated deliberately rather than drifting."
  - "T01 (#7924, merged c5e6f0bb5d39) and T04 (#8062, MERGED 50549f8e839e) are adjudicated closed and DELIVERED - T01 after five lane rounds and three READ_ONLY red-teams, T04 after two lane rounds that each self-reported PASS and each carried defects (round 1: five blockers and two majors; round 2: B6, the sixth blocker, which no reviewer saw). Do not re-review either finding set and do not re-derive T04's arithmetic, which was clean throughout and deliberately left alone. Reviews: reviews/OPUS_T01_REDTEAM_2026-09-24.md, reviews/OPUS_T04_REDTEAM_2026-09-26.md."
landmines:
  - "A plan-frozen example test is a requirement, never evidence the requirement is enforced. T02's mandated two-run test had one vacuous assertion (members() -> `return set()`, so `before <= members()` could not fail) and two that raised AttributeError (no get() on _PublicationHarness). Resolve every attribute against the owning CLASS and mutation-probe each assertion before dispatch: DSC:A-FROZEN-PLANS-EXAMPLE-TEST-CAN-BE-HALF-DEAD."
  - "run_refresh's empty-changes branch is byte-identical to the pre-T02a behaviour on purpose: the three merged run_refresh tests are T01's round-5 N3 cures and all pass changes={}. Refactoring that branch away reds them."
  - "A PLAN'S TRACEABILITY TABLE IS NOT COVERAGE: 13 of 15 named anchors did not exist across two merged, green tasks, because a pytest run names FILES and `pytest path::absent` reports `no tests ran` rather than a failure. Never report a requirement count from the table. Auditing existing tests BY NAME is the wrong instrument - build the anchor from the requirement text, which is how IND-D10 surfaced. DSC:A-PLANS-TRACEABILITY-TABLE-IS-NOT-COVERAGE."
  - "The synthetic helper comparison(purpose, cells) sets EVERY checked flag True, so a probe built on it excuses every comparability mismatch and mints phantom gaps. Build the receipt, then set the ONE flag under test False - the landed idiom, carried by the anchors as _unchecked()."
  - "`metric` encodes the period ROLE here (revenue_current / revenue_prior), not measure semantics - the measure lives in quality.definition. A first IND-D09 cure compared metric equality and broke eight landed tests that were right."
  - "Shared files (issuer_profiles.py, event_workspace.py, event_workspace_build.py, refresh_event_workspaces.py, private_publication.py, app/earnings.py, the shared theme-research client/mount) stay owned by their incumbent workstreams and are touched at named seams only, serialized behind #7870 and #7905."
  - "Sparse worktrees truncate data/ and site/ on write."
  - "A red pack on an Industrials PR may be a SIBLING seat's dangling agentos artifacts: entry, not your diff: self-mod-fence is always-on and refuses any [phantom-artifact] string anywhere in the store, so it reds any PR whose merge ref predates the referenced file. #8062 lost one run that way (DSC:A-DANGLING-ARTIFACT-ENTRY-REDS-EVERY-STALE-MERGE-REF). Triage the path at origin/main AND at refs/pull/<N>/merge before touching code; the cure is a base refresh, and rerunning the job reuses the stale merge commit."
  - "A new test wired into a gate:code run line without its paths: entry reds contract-delta fleet-wide."
  - "The sec_edgar rationale is not blanket clearance for issuer-authored text (A14-06)."
  - "No live Exponent/Pentair figure may become a fixture or a native receipt before G2."
  - "A lane's own PASS closes nothing here (DSC:A-LANE-SELF-VERDICT-IS-NOT-A-CLOSURE-GATE), and a review commissioned by naming a file path returns no verdict at all (DSC:A-PATH-ONLY-REVIEW-COMMISSION-BUYS-DISCOVERY-NOT-JUDGMENT). Budget an independent READ_ONLY pass per ROUND, commission it judgment-only with excerpts and probe output inline, and expect the seat to run the decisive probes."
  - "T04 widened the receipt_id digest, so receipt_id VALUES changed: dependents pin no receipt_id literal, receipt snapshot or golden receipt file, always pass formula= to qualify_operands, and treat the checked block as disclosure rather than authority - an omitted checked certifies nothing."
---

# GMI Industrials — first vertical

Seat program record. Continuity lives in the handoff above; rulings in
`research/industrials/first_vertical_program/rulings/`. Modified shared files are
owned by their incumbent workstreams (`WS:EARNINGS-INTELLIGENCE-OS`, `WS:GMI-THEME-GRAPH`)
and are touched only at named seams. All rank/gate/size/originate/entry authority stays false.
