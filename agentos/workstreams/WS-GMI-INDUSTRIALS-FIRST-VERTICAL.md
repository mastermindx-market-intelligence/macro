---
key: GMI-INDUSTRIALS-FIRST-VERTICAL
title: "GMI Industrials — first vertical: Exponent/Pentair result-to-cash dossiers (Fable Meta-CEO program)"
objective: >
  Implement the frozen Industrials nine-task plan on the Semiconductor-led shared
  foundation as fabric-built PRs in dependency order. Done means both real, signed-in
  Exponent and Pentair dossiers pass the T09 real-path proofs (two journeys, correction,
  revocation, ordinary refresh, non-interference) with every one of the 56 inherited
  requirements executed — never a merged slice alone.
status: active
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
    next_action: "T04 half is DONE - MERGED 2026-09-27 06:04Z as 50549f8e839eff38a86568cbc2beb9d29fe0de81 from cd46f9452c77 (the adjudicated 0e3344a9071f plus one base-refresh merge; module and suite byte-identical), ci-gate and all twelve packs green on run 36296953418. Only the T02 half of this wave remains, and it is BLOCKED: it edits issuer_profiles.py / event_workspace.py / event_workspace_build.py / refresh_event_workspaces.py - FOUR seam files, not the three this record used to list. Re-checked 2026-09-27: #7905 (OPEN/DRAFT b6808dfcc166) holds only issuer_profiles.py; #7870 (OPEN/DRAFT a0d7b054ff23) holds all four. Do not dispatch T02 until they release the seam. CORRECTED 2026-09-29 (IND-T04c, #8160): the seam is a real LANDING gate but is NOT the binding blocker, and treating it as one invites waiting for a merge that cannot unblock the work. Of the 56 requirement ids the frozen plan's section 6 names, 41 have NO obligation text anywhere in this repository or on carrier #7789 - the texts are inherited 'unchanged from r1/r2/W12' and those specs are absent - so with both PRs merged no seat could write an honest test for T02-T09. The 15 ids that do appear in the tree are exactly T01's and T04's and appear only BECAUSE landed code cites them, so reachability is downstream of delivery and is not a gate. The unblock is the r1/r2/W12 corpus (a path or blob shas), asked for on #7789 as comment 5881951284; if that text is gone, T02-T09 need re-specification, which is this carrier's decision and not a seat's inference. Enforced meanwhile: research/industrials/first_vertical_program/requirement_index.md marks all 41 anchor_basis=NO_SOURCE and the dependency-binding suite refuses to anchor one."
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
  SPECIFICATION AUTHORITY RESOLVED 2026-09-29 - SOL RULING / CONTINUE (#7789 comment
  5894127980), which consumes this seat's asks 5881951284 / 5882425483 / 5894142128.
  RECOVERY SUCCEEDED AND NO RE-SPECIFICATION IS AUTHORIZED OR NEEDED. The original corpus was
  never deleted; it is simply not vendored at any path on main. Read this clause before every
  sub-wave next_action below: those entries were written when the binding blocker was believed
  to be missing requirement text, and that belief is now closed.
  THE RECOVERED ORIGINAL AUTHORITY, at commit 40d91e50a38c604e26255c1451eda5ddc95fb9cc on the
  original #7789 source line sol/industrials-sector-research-20260923. All three blobs are
  present in this host's object store and were read directly to verify the counts below:
  r1 = docs/superpowers/specs/2026-09-23-industrials-result-cash-dossier-design.md,
  blob 40fd1e3783102c28fe748fe35b927484d4f3dddb (28638 B), IND-D01..IND-D30 - VERIFIED 30
  unique IND-D ids in the blob's own bytes.
  r2 = the same path with the -r2 suffix, blob 9c98e106b954d0a48610afad418de2a9eeb1e58b
  (20947 B), IND-R201..IND-R218 - VERIFIED 18 unique IND-R ids; it explicitly preserves r1.
  W12 = research/industrials/INDUSTRIALS_WAVE12_SEMICONDUCTOR_FOUNDATION_ALIGNMENT_2026-09-24.md,
  blob b343cbd7bc1f52cfc6fbb5e18ab8d9e9f9392f6c (21187 B), IND-SF01..IND-SF08 - VERIFIED 8
  unique IND-SF ids; it preserves the prior D/R corpus.
  30 + 18 + 8 = 56 with zero missing and zero extra against the frozen plan's table. The frozen
  plan itself is docs/superpowers/plans/2026-09-24-industrials-shared-foundation-increment-implementation.md,
  blob a5462dc7f36aea08c57ce43a8a230ef00ebae802, likewise tracked at no path on main and pinned
  host-locally as refs/salvage/ind-first-vertical-plan-a5462dc7.
  DISPOSITION PER THE RULING: no requirement id is retired, superseded, renumbered or reworded.
  The earlier claim that 41 obligations have NO RETRIEVABLE AUTHORITY is SUPERSEDED - they are
  not vendored on main, but their original wording is recoverable from the blobs above. The
  #8160 anti-fabrication guard stays and stays fail-closed: when a substantive change first
  touches one of those 41 ids, update that row's source basis to the exact recovered blob/path
  IN THAT SAME CHANGE. Never silently reword recovered text, and never label a new
  clarification as recovered original text; a genuinely new obligation needs an explicitly
  versioned amendment plus an explicit disposition of the affected old id.
  NEXT ACTION IS PRODUCT WORK, NOT BOOKKEEPING. Do NOT open another traceability-only
  increment; a minimal source-reference correction is supporting work inside the first
  substantive product build, never its outcome. Build and test PATH-DISJOINT product work now
  toward the preserved vertical: theme/company entry -> economic change ->
  earnings/cash/conditions -> exact evidence + falsifier -> correct company navigation/return,
  for Exponent and Pentair, preserving publication/refresh/correction behaviour, access and
  revocation behaviour, and legacy/cross-sector non-interference. Use the existing Company
  Intelligence, Fundamental Forensics, Earnings, private-publication, route and shared-theme
  owners; create no second schema, store, router, registry, traceability plane, rights plane,
  lifecycle or authority plane.
  THE RULING CLOSES ONLY THE CORPUS GAP. It does NOT release the independent holds or incumbent
  ownership on #7870 or #7905, so T02 is still gated on #7905's profile_for_ticker signature
  (R-IND-12) even though its three obligations IND-D04, IND-D05 and IND-R210 now have recovered
  text. Where landing or real-path proof still depends on an incumbent seam, return THAT EXACT
  GATE rather than waiting broadly or substituting more bookkeeping. #7780 is
  research/specification/handoff evidence, never runtime source.
  UNCHANGED AND STILL BINDING: do not dispatch T05 (args_ind_t05_source_history.json stays
  PARKED; rulings_t05 R8 forbids it); tests/test_industrials_issuer_enrollment.py is not
  created and no anchor-map row exists for a T02 requirement while T02 is unstarted. Do not
  re-run the index/traceability audit - it is recorded in requirement_index.md and on #7789.
  Return with the exact candidate head, tests tied to the RECOVERED ORIGINAL WORDING, and the
  strongest available Exponent/Pentair journey proof; claim no acceptance until the real user
  path satisfies the whole outcome. Re-arm the approved exact-carrier wait/watch path after the
  next nonterminal return, or report the exact WATCH_UNAVAILABLE condition.
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
