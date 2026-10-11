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
decisions:
  - DEC:CHAIRMAN-INDUSTRY-INTELLIGENCE-META-CEO-CONSOLIDATION-2026-10-11
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
    status: in_progress
    depends_on: [IND-W3]
    next_action: "SIX of the nine T06 obligations are covered as of #8213 (squash 28a3ab1e7cb2): IND-D23, IND-R201, IND-R215, IND-R218 and IND-SF04 by assemble_evidence_view in engine/company_intelligence/financial_dossier.py, plus the all-present control. This wave opened AHEAD of its depends_on IND-W3 because Sol commissioned the capability directly (#7789 comment 5894912727) as ONE user-facing behaviour rather than five isolated anchors - W3 was not skipped silently and T03/T05 sequencing is unchanged. R7-R8 still bind and are honoured: the view QUOTES already-derived result-to-cash values or reports their refusal, re-derives nothing, and pins no receipt_id literal or golden receipt. IND-D03, IND-D22 and IND-R213 remain UNCOVERED because their seams are unmerged - do not author tests for them against a branch. Do not re-point IND-D23 or IND-R215 at the dossier tests: they keep their result-to-cash anchors, and re-pointing would trade unit coverage for page coverage rather than add it."
  - id: IND-W5
    title: "T07 private role, T08 typed view on the shared aggregator, T09 real-path proofs"
    status: todo
    depends_on: [IND-W4]
    next_action: "Wait for Semiconductor B's shared route family and aggregator on main; never build against #7870's branch."
next_action: >
  2026-10-11 CONSOLIDATION (DEC:CHAIRMAN-INDUSTRY-INTELLIGENCE-META-CEO-CONSOLIDATION-2026-10-11): T02 carrier #8250
  (codex/industrials-t02-issuer-enrollment-20260930-sol-001) was adjudicated at 20b853e2907e the same
  day (#8250 comment 6105257496, independent READ_ONLY Opus review consumed by the seat, VERDICT
  REPAIR_REQUIRED) and rebuilt on e4bce058 as head 20e7e9ac63759099704a46506e85b61d00b487fc
  (comment 6105272573, Draft, NON_AUTHOR_READ: PENDING at the time; the standalone non-author
  read of e4bce058..20e7e9ac returned ACCEPT_MANIFEST_COMMIT, consumed in #8250 comment
  6106622707); hosted checks at 20e7e9ac went RED (run 38110427910: contract-delta,
  ci-pack-0, ci-gate) on a curated-closure contract that lives only on origin/main
  (nw-lobe-unfreeze and ticker-news-qbus are scope: exclusive there and declare
  issuer_profiles.py, whose lazy import of industrials_profiles.py left the closure uncovered);
  repaired by merging origin/main f191b7f1 into the carrier (03d29dfea9d8) plus a two-line
  path widening (1db9cad104437dc0c9bb4b27cf45781040302fb2, pushed 2026-10-11, local closure
  check {} and the two curated-scope tests pass locally); it lands on main first per the #7870
  landing order (comment 6105402719 line 18) once, at 1db9cad1, four conditions are in hand:
  (1) ALL_CONCLUDED green from the one bound watcher (in hand: 2026-10-11T06:24:44Z, 26 check runs (1 failure; 4 skipped; 21 success; 6106622707 line 26 wrote 15; the 26 is from 6106264920 line 8 and from the 2026-10-11T07:39:39Z check-runs readback recorded in the verified block of handoff GMI-SEMICONDUCTORS-2026-10-11-meta-ceo-consolidation), the only failure ci-authority/codex/merge-queue-pilot, which is not a gate: no check is GitHub-required on main (readback 2026-10-11T07:39:39Z: GET repos/mastermindx-market-intelligence/macro/branches/main/protection/required_status_checks returned 'HTTP 404 Branch not protected' and GET repos/.../rules/branches/main returned rule types (empty list); that is true of all 26 checks, ci-gate included, so it does not single this one out), and merge-queue-pilot concluded failure on the head sha of all 14 PRs merged to main on 2026-10-11 through 08:26:47Z (#8755, #8760, #8758, #8764, #8670, #8767, #7869, #8768, #8769, #8774, #8771, #8775, #8777, #8778; list read 2026-10-11T08:34:57Z, conclusions read 08:35:20Z, recorded in the verified block of handoff GMI-SEMICONDUCTORS-2026-10-11-meta-ceo-consolidation), so the seat's own gates, not that pilot, decide merge readiness); (2) the
  non-author READ_ONLY review chain from Sol's reviewed head e4bce058 (REVIEW 5925055036,
  CONTINUE 5925110889 with REVIEW_REUSE_ALLOWED) to 1db9cad1 (in hand, two legs: the first
  candidate 20b853e2 was adjudicated REPAIR_REQUIRED by the READ_ONLY audit consumed in #8250
  comment 6105257496 and is not an ancestor of 20e7e9ac; e4bce058..20e7e9ac, the rebuilt +5
  manifest commit, returned ACCEPT_MANIFEST_COMMIT in the standalone non-author read consumed
  in #8250 comment 6106622707 (6105272573 recorded NON_AUTHOR_READ: PENDING and carries no
  verdict; 6106622707 also corrects the gate-ledger line in 6106321419 that cited it as a
  manifest ACCEPT); 20e7e9ac..1db9cad1,
  the merge commit 03d29dfe diffed against origin/main f191b7f1 only, the other side covered by the seat's tree-identity proof b94a9852 == 03d29dfe^{tree} that the reviewer did not re-run, plus the two-line commit, returned
  ACCEPT_REPAIR, consumed in #8250 comment 6106321419: scope PASS over exactly the 7 owned
  paths; the tip is the exact two-line widening of the closure lists of jobs nw-lobe-unfreeze
  (.github/ci/legacy-jobs.yml:10407, unquoted) and ticker-news-qbus (:21058, quoted), not of
  industrials-result-cash (:22605); 0 conflict markers and each def and table once in
  issuer_profiles.py; that comment supersedes the earlier 'twins at the Industrials job'
  wording of comment 6106264920); Sol's CONTINUE 5925110889 grants REVIEW_REUSE_ALLOWED for the accepted product/identity semantics and names exactly one bounded CI-closure repair (the five paths: additions), while 1db9cad1 adds a merge of main plus a second closure repair, neither of which the reuse grant names: the second repair's only non-author cover is 6106321419, and the merge of main (f191b7f1, merged as 03d29dfea9d8) is covered only by 6106321419's diff of the merge commit 03d29dfe against f191b7f1 (6106321419 line 4: 379 lines, exactly the 7 owned paths) plus the seat's own tree-identity proof (merge-tree b94a9852 == 03d29dfe^{tree}), which 6106321419's reviewer did not re-run; and 5925055036 is PASS on product semantics with FINALIZATION_CLASSIFICATION REQUEST_REPAIR, which is why 6106622707 calls it REQUEST_REPAIR and 6105272573 and 6106321419 call it PASS; the release DECISION must state both points; (3) Source Continuity gate (4) applied to #8250 in its own
  terms (owed): the verifier run at #8250's own release head from protected Mastermind master
  at re-run time, with --external-effect-evidence-fingerprint = sha256 of #8250's recorded
  external-effect artifact (the git ls-remote line plus the pulls/8250 head/state/draft read;
  da6a8c45d80757e2ef3eda821dd56e24db64149c92e8a6c6d3bb231846cc0c06 at 1db9cad1,
  seat-only-checkable until the exact hashed bytes are posted, because 6106395498 paraphrases
  the ls-remote line and summarizes the pulls/8250 read), with the verifier's source SHA
  recorded in the #8250 DECISION and its JSON quoted verbatim there, returning
  REMOTE_COMPLETE_VERIFIED; or a non-seat acceptance (the Chairman or Sol, by cited id) of
  #8250's own substitute, quoted in the #8250 release DECISION, recorded at
  1db9cad1 in #8250 comment 6106395498 (git ls-remote == HEAD; GitHub commit tree
  7a9ee2b823bcf3058e62dffdea3d4440868c33e9 == HEAD^{tree}; fully paginated pulls/8250/files
  == git diff --name-only f191b7f1..1db9cad1, 7 paths; open-PR count 634 at 06:31:56Z;
  own-path collision census of 2026-10-11T06:37:16Z to 06:40:30Z over 634 open PRs with 0
  enumeration failures: 183 other open PRs touch an owned path, 182 of them only
  .github/ci/legacy-jobs.yml, #7870 that file plus issuer_profiles.py, none of the 183
  containing 1db9cad1, 10 with a base other than main; census JSON sha256
  e039b80f2a41d32091a74d2756a7b806cd9bdf7d6a649e44e98d52d825dc70d8, seat-only-checkable),
  under the narrowed rule of #7870 comment 6106134520 and its addendum 6106495383 (roster-size
  REMOTE_CENSUS_INCOMPLETE only, shown by the attribution test around an actual run at that
  head, the seat's own tightening posted in the addendum and recorded in WS:GMI-SEMICONDUCTORS
  gate (4); every other refusal code RELEASE_BLOCKED regardless; until one branch is in hand
  #8250 is RELEASE_BLOCKED on gate (4) exactly as #7870 is, 6106134520 section 1(iii), with the block that continues after #8250's substitute was recorded stated in addendum 6106495383 section 3 (substitute recorded, not accepted) and section 5 (RELEASE: BLOCKED_PENDING_NON_SEAT_RULING for #7870 and #8250); the
  verifier has not been run on #8250 and would be expected to
  refuse at the census step, roster 634 > _MAX_COLLISION_PRS = 490 per GraphQL
  pullRequests(states:OPEN).totalCount at 2026-10-11T05:59:21Z, 633 at 06:17:20Z and 634 at
  06:31:56Z, which is an expectation, not a run); and (4) the custody reconciliation below
  (owed). Custody basis for the seat's
  two pushes to codex/industrials-t02-issuer-enrollment-20260930-sol-001 (20e7e9ac, 1db9cad1):
  Ruling C-1 of DECISION 6105015260 names Industrials #7789/#8250 as this seat's, and #8250
  comment 6105257496 line 22 records the seat's execution of the mechanical rebuild as an
  exception while the fabric is unreachable; the last child-side edge on #8250 is Sol's
  CONTINUE 5925110889 (2026-10-01T05:04Z). The Codex child's writer-lease state in Executive
  OS is UNVERIFIED from this seat (connector unreachable); a custody reconciliation through
  the Executive owner is owed before #8250's Ready/merge. The seam gate on issuer_profiles.py
  is shared with Mining T02 and CDV-1; land order is decided by this seat, not by whichever
  lane finishes first.
  .
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
  2026-10-11 17:49Z: gate (4) for #8250 is applied under the five-leg substitute criterion now
  recorded as DSC:SOURCE-CONTINUITY-CENSUS-PASS-CRITERION-FOR-MACRO-CARRIERS-OVER-THE-490-CAP:
  6106395498 at 1db9cad1 satisfies legs (1) head identity, (2) ownership and (5) one substitute
  per carrier per head; leg (4) fingerprint by shape only (the hashed ls-remote line is
  paraphrased and the pulls/8250 read summarized there); leg (3) attribution (roster read
  immediately before and after the run plus the run's call/byte/wall totals) is not recorded.
  The release-head re-run records all five. #8250's head at this write is unchanged at 1db9cad1 (no #8250 act this
  window); #7870 is at 1eb871d6 with its own substitute superseded (WS:GMI-SEMICONDUCTORS SB-W1).
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
