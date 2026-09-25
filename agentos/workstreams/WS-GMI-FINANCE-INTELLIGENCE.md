---
key: GMI-FINANCE-INTELLIGENCE
title: Finance Intelligence — owner-preserving Finance sector dossier (first vertical Financial Rails & Market Infrastructure)
objective: >
  Ship a paid, evidence-backed Finance Intelligence journey (Theme Tracker / Sector
  Intelligence → Financials → Finance Intelligence → Money Movement → company/evidence →
  Securities Infrastructure → existing stock/basket/sector workflow) as ONE read-only
  projection over existing owners, with exact missing/conflict states, authenticated
  private full-fidelity data, and browser proof at 1440/390 × light/dark × EN/ZH plus a
  keyboard-only journey. Done = first vertical PROVEN_LIVE on the accepted release; the
  broader 52-slice programme stays PARTIAL until its breadth waves are proven.
status: active
program: sector-rotation-intelligence
repos: [macro]
owner: coo-fable
class: build
blast_radius: user_facing
ambiguity: scoped
depends_on:
  - WS:GMI-THEME-GRAPH
owns_paths:
  - contracts/sector_intelligence/finance_intelligence_read_model.v1.schema.json
  - data/sector_intelligence/fixtures/finance_intelligence_read_model.v1.valid.json
  - engine/sector_intelligence/finance_projection.py
  - engine/sector_intelligence/finance_overlap.py
  - engine/sector_intelligence/finance_private.py
  - app/finance_intelligence.py
  - scripts/build_finance_intelligence_page.py
  - templates/finance_intelligence.html.j2
  - templates/finance_intelligence.js
  - templates/finance_intelligence.css
  - templates/_finance_sector_deep_dive.html.j2
  - tests/test_finance_intelligence_*.py
  - tests/test_finance_overlap.py
  - tests/test_finance_owner_preservation.py
  - tests/test_finance_private_publication.py
  - tests/js/finance_intelligence.test.mjs
  - research/finance/implementation/
decisions:
  - DEC:FINANCE-IMPL-CARRIER-IS-SEAT-PR-TASKS-SHIP-OFF-MAIN
  - DEC:FINANCE-EVIDENCE-GRAMMAR-MIRRORS-SHARED-ASSERTION-NEVER-FORKS
artifacts:
  - agentos/handoffs/GMI-FINANCE-INTELLIGENCE-2026-09-24.md
landmines:
  - "#7786 (sol/finance-sector-research-20260923, head 615f1050) is records-only: 26k files behind main; never rebase it in, never merge it to reach the research — read by exact path/SHA."
  - "The shared curation assertion (#7870) requires scope.canonical_theme_id + subject.company_node_id; Finance has no canonical theme and unvalidated witness identities — consume by reference, request the R11 §14.1 extension sections on #7870, never fork."
  - "templates/basket_detail.html.j2 is held by #7669 (draft, 358 files — R12's 'not listed' was a paginated read). The Financials launch module waits on that owner or lands as a one-line guarded include after coordination."
  - "Lane hosts run SPARSE clones: a new fixture under data/ must be staged with `git add --sparse <path>`; never touch an existing data/ or site/ file from a lane."
do_not_redo:
  - "R1–R12 Finance research, the 73-record census, the R10 casebook, the 52-slice atlas, the four-plane/three-map separation, denominator/clock laws, basket coexistence law, first-vertical selection, R11 UX hierarchy, R12 owner/collision architecture (all on #7786 @615f1050)."
  - "Registry auto-discovery check: engine/sector_intelligence/contracts.py::_discover_records rglobs contracts/sector_intelligence/*.schema.json — no contracts.py edit is needed to register a new contract."
  - "Private data-path census: the accepted owner is engine/earnings_narrative/private_publication.py over engine/research_vault/r2_store (build_store precedence local_dir → RESEARCH_LOCAL_STORE → R2_RESEARCH_BUCKET); the API host receives R2_RESEARCH_* through .github/workflows/deploy-api-secrets.yml."
waves:
  - id: W0
    title: "Pickup, procedure pin, current-main + custody reconciliation, carrier freeze"
    status: done
  - id: W1
    title: "Finance read contract + fixture; pure projection; overlap; private/rights qualification (Tasks 1–4)"
    status: in_progress
  - id: W2
    title: "Real Money Movement + Securities Infrastructure evidence; authenticated API (Tasks 5–7)"
    status: todo
  - id: W3
    title: "Finance dossier shell/UI; Theme Tracker + Financials entry (Tasks 8–9)"
    status: todo
  - id: W4
    title: "Banking/Credit/Mortgage/Private Credit; Asset/Wealth/Insurance (Tasks 10–11)"
    status: todo
  - id: W5
    title: "Global/regional + structural disruption semantics (Task 12)"
    status: todo
  - id: W6
    title: "Candidate-basket context and overlap without admission (Task 13)"
    status: todo
  - id: W7
    title: "Degraded/accessibility/privacy qualification, independent review, real browser proof, production acceptance (Tasks 14–16)"
    status: todo
next_action: >
  Wave 1 closed 2026-09-24 08:29Z (T1 #7896, T3 #7900, records #7887/#7902/#7913/#7939 merged); T2
  composer #7920 MERGED 11:53Z (e4ac3730). D1 CLOSED: spec FROZEN at 2e5c3df6, mockup accepted at
  ce7fc986 after browser proof, #7903 MERGED 14:58Z (0293b9cf)
  (DEC:FINANCE-DOSSIER-SPEC-SURFACE-TIERS-STATE-SCOPED-FRESHNESS-AND-ANSWER-FIRST-COMPOSITION,
  DSC:EXTERNAL-REPAIR-LANES-OVER-EDIT-LONG-SPECS-EVEN-WHEN-SURGICAL-CAP-THE-AUDITS-AND-LET-THE-SEAT-CLOSE).
  T8 shell + hydration MERGED 16:11Z (#7952, 4c191a3e) behind the builder's `FI_READ_URL = ""`
  constant, so the page stays not-connected. #7956 (6b1483f4) fixed the edge: a public shell needs FOUR
  Caddyfile registrations beside site_access.yml
  (DSC:PUBLIC-SHELL-ASSETS-NEED-FOUR-REGISTRATIONS-SITE-ACCESS-PLUS-CADDY-EDGE). The live browser
  proof found four more shell defects. All four fixes are MERGED and production-proven on 2026-09-25
  at 1440/390 × dark/light × EN/中文: theme.js was never loaded (#7968, 5600bb63; keyboard also
  proven); the dark canvas was white outside the shell (#7974, c90af106); and the connected-state
  names now follow the page language, together with the independent Opus review response (#7973,
  836379db, which carries #7969, closed as superseded)
  (DSC:NEW-PAGE-SHELL-DEFECTS-HIDE-FROM-TESTS-THEME-JS-CANVAS-AND-RENDER-TIME-ARIA-NAMES). T9
  entries MERGED 2026-09-24 17:14Z (#7957, dafc546f). The Theme Tracker card has been LIVE since the
  2026-09-25 00:48Z nightly bake (proof comment 5825108176 on #7957). Its 中文 accessible-name fix,
  #7977, MERGED 01:47Z (05b559b8) and goes live at the next rebuild of the page. render.yml is wedged
  on `render-linux` pending an operator relabel, so the nightly engine bake is the path; re-check
  recipe in the handoff. The Financials launch partial stays DORMANT until #7669 merges.
  Chairman directive (Astra CEO): Finance integrates into the Semiconductor-built shared foundation and
  never rebuilds base layers, so T4/T5/T6/T7 are HELD
  (DEC:FINANCE-INTEGRATES-INTO-SHARED-FOUNDATION-NEVER-REBUILDS-BASE).
  Next: (1) confirm #7977 live after the next bake; (2) the integration wave once #7870 lands:
  an adapter to the foundation's source_record.v1 / evidence_claim.v1 / sector_intelligence_packet.v1
  as recorded in the handoff, then set FI_READ_URL once the serving route is accepted (nothing else in
  the shell changes), with the three open questions for the shared owner and a connected proof that
  re-reads ZH aria-labels on live data; (3) wire the Financials launch include when #7669 merges;
  (4) the deferred review MINORs (handoff list) ride the integration wave.
---

# Finance Intelligence workstream

Operation `gmi-finance-fable-ceo-e2e-20260924-chairman-001` (parent research operation
`gmi-finance-sector-research-20260923-sol-001`, carrier PR #7786). The Fable seat owns
architecture adjudication, current-main/custody reconciliation, worker routing, integration,
privacy/identity/basket law, independent-review response, browser/production acceptance and
the completion ruling. Bounded fabric workers own task-sized code/test/transcription labor.
