---
key: GMI-INDUSTRIALS-FIRST-VERTICAL
title: "GMI Industrials — first vertical: Exponent/Pentair result-to-cash dossiers (Fable Meta-CEO program)"
objective: >
  Implement the frozen Industrials nine-task plan on the Semiconductor-led shared
  foundation as fabric-built PRs in dependency order. Done means both real, signed-in
  Exponent and Pentair dossiers pass the T09 real-path proofs (two journeys, correction,
  revocation, ordinary refresh, non-interference) with every one of the 56 inherited
  requirements executed — never a merged slice alone.
status: awaiting_ci
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
    next_action: "T04 half is adjudicated closed over two rounds and awaits ci-gate on head 0e3344a9071f. T02 half is BLOCKED: it edits issuer_profiles.py / event_workspace.py / refresh_event_workspaces.py, which #7870 (base owner) and #7905 (held under audit) both edit - do not dispatch it until those release the seam."
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
  Land #8062 (T04) once its ci-gate concludes green, then patch the checkpoint with the
  merge sha. After that the Industrials product chain has no dispatchable lane: T02 waits
  on the shared seam held by #7870 and #7905, T03 waits on T02, T05 on T03, T06 on T01-T05,
  T07-T09 on Semiconductor B reaching main (G1). The unblocking act is not owned by this
  program - re-check both PRs' changed-file lists before dispatching T02, and never edit
  base-owned files ahead of the base.
artifacts:
  - agentos/handoffs/GMI-INDUSTRIALS-2026-09-24-first-vertical-implementation.md
  - research/industrials/first_vertical_program/rulings/R-IND-2026-09-24-wave1.md
  - research/industrials/first_vertical_program/reviews/OPUS_T01_REDTEAM_2026-09-24.md
  - research/industrials/first_vertical_program/reviews/OPUS_T04_REDTEAM_2026-09-26.md
carrier:
  operation: gmi-industrials-fable-ceo-e2e-20260924-chairman-001
  research_pr: 7789
  records_pr: [7912, 7915, 7919, 8070, 8072, 8073]
do_not_redo:
  - "Research Waves 1-14, the nine-task plan (blob a5462dc7) and the 56-requirement traceability are frozen - do not re-research Industrials economics."
  - "R14-01..R14-05, the R4 private-mechanism choice and the #7669 aggregator choice are decided - never reopen the GET route or a direct mount."
  - "Never put implementation on the research carrier #7789; never edit #7870's branch."
  - "T01 (#7924) and T04 (#8062) are adjudicated closed - T01 after five lane rounds and three READ_ONLY red-teams, T04 after two lane rounds that each self-reported PASS and each carried defects (six blockers, then a seventh). Do not re-review either finding set and do not re-derive T04's arithmetic, which was clean throughout and deliberately left alone. Reviews: reviews/OPUS_T01_REDTEAM_2026-09-24.md, reviews/OPUS_T04_REDTEAM_2026-09-26.md."
landmines:
  - "Shared files (issuer_profiles.py, event_workspace.py, refresh_event_workspaces.py, private_publication.py, app/earnings.py, the shared theme-research client/mount) stay owned by their incumbent workstreams and are touched at named seams only, serialized behind #7870 and #7905."
  - "Sparse worktrees truncate data/ and site/ on write."
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
