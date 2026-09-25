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
    status: in_progress
    next_action: "Dispatch lane ind_t01_binding on m1; red-team the PR; merge on concluded green."
  - id: IND-W2
    title: "T02 issuer profiles || T04 pure result-to-cash derivations"
    status: todo
    depends_on: [IND-W1]
  - id: IND-W3
    title: "T03 case extractors || T05 editions and comparisons"
    status: todo
    depends_on: [IND-W2]
  - id: IND-W4
    title: "T06 closed financial dossier contract and thin shared adapter"
    status: todo
    depends_on: [IND-W3]
  - id: IND-W5
    title: "T07 private role, T08 typed view on the shared aggregator, T09 real-path proofs"
    status: todo
    depends_on: [IND-W4]
    next_action: "Wait for Semiconductor B's shared route family and aggregator on main; never build against #7870's branch."
next_action: >
  Consume the Opus READ_ONLY seam audit into R-IND-10+, finalize the T01 packet,
  dispatch ind_t01_binding, post START on #7789.
artifacts:
  - agentos/handoffs/GMI-INDUSTRIALS-2026-09-24-first-vertical-implementation.md
  - research/industrials/first_vertical_program/rulings/R-IND-2026-09-24-wave1.md
carrier:
  operation: gmi-industrials-fable-ceo-e2e-20260924-chairman-001
  research_pr: 7789
  records_pr: 7912
do_not_redo:
  - "Research Waves 1-14, the nine-task plan (blob a5462dc7) and the 56-requirement traceability are frozen - do not re-research Industrials economics."
  - "R14-01..R14-05, the R4 private-mechanism choice and the #7669 aggregator choice are decided - never reopen the GET route or a direct mount."
  - "Never put implementation on the research carrier #7789; never edit #7870's branch."
landmines:
  - "Shared files (issuer_profiles.py, event_workspace.py, refresh_event_workspaces.py, private_publication.py, app/earnings.py, the shared theme-research client/mount) stay owned by their incumbent workstreams and are touched at named seams only, serialized behind #7870 and #7905."
  - "Sparse worktrees truncate data/ and site/ on write."
  - "A new test wired into a gate:code run line without its paths: entry reds contract-delta fleet-wide."
  - "The sec_edgar rationale is not blanket clearance for issuer-authored text (A14-06)."
  - "No live Exponent/Pentair figure may become a fixture or a native receipt before G2."
---

# GMI Industrials — first vertical

Seat program record. Continuity lives in the handoff above; rulings in
`research/industrials/first_vertical_program/rulings/`. Modified shared files are
owned by their incumbent workstreams (`WS:EARNINGS-INTELLIGENCE-OS`, `WS:GMI-THEME-GRAPH`)
and are touched only at named seams. All rank/gate/size/originate/entry authority stays false.
