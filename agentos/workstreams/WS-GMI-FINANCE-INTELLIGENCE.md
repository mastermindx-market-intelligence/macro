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
  - engine/sector_intelligence/finance_research_registration.py
  - app/finance_intelligence.py
  - scripts/build_finance_intelligence_page.py
  - templates/finance_intelligence.html.j2
  - templates/finance_intelligence.js
  - templates/finance_intelligence.css
  - templates/_finance_sector_deep_dive.html.j2
  - tests/test_finance_intelligence_*.py
  - tests/test_finance_overlap.py
  - tests/test_finance_research_registration.py
  - tests/test_finance_owner_preservation.py
  - tests/test_finance_private_publication.py
  - tests/js/finance_intelligence.test.mjs
  - research/finance/implementation/
  - mockups/evidence/finance-t11-conformance/
decisions:
  - DEC:FINANCE-IMPL-CARRIER-IS-SEAT-PR-TASKS-SHIP-OFF-MAIN
  - DEC:FINANCE-EVIDENCE-GRAMMAR-MIRRORS-SHARED-ASSERTION-NEVER-FORKS
  - DEC:FINANCE-DOSSIER-SPEC-SURFACE-TIERS-STATE-SCOPED-FRESHNESS-AND-ANSWER-FIRST-COMPOSITION
  - DEC:FINANCE-INTEGRATES-INTO-SHARED-FOUNDATION-NEVER-REBUILDS-BASE
  - DEC:FINANCE-DOSSIER-SPEC-T11-ERRATA
  - DEC:FINANCE-ZH-MARKS-UNTRANSLATED-SOURCE-PROSE-NEVER-MACHINE-TRANSLATES
  - DEC:FINANCE-REGISTRATION-OMISSIONS-ARE-A-CLOSED-VOCABULARY-AND-EVIDENCE-EMBEDS-THE-VALIDATORS-COPY
  - DEC:FINANCE-COMPOSER-NEVER-MINTS-AN-EVIDENCE-REF
  - DEC:FINANCE-AN-OBSERVATION-HAS-ONE-DATE
artifacts:
  - agentos/handoffs/GMI-FINANCE-INTELLIGENCE-2026-09-24.md
  - agentos/handoffs/GMI-FINANCE-INTELLIGENCE-2026-09-27.md
  - agentos/handoffs/GMI-FINANCE-INTELLIGENCE-2026-09-28.md
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
  2026-09-28 wave closed (handoff GMI-FINANCE-INTELLIGENCE-2026-09-28; the one before it,
  GMI-FINANCE-INTELLIGENCE-2026-09-27, carries the history of T1-T3, T8-T11 and the composer
  follow-ups #8113 to #8138). This wave closed every composer item the 09-27 handoff left open:
  #8146 (the registration limitations read theme evidence through the composer's own gate) MERGED
  3b9a451f; #8159 (an owner input reads the same whatever container holds its rows) MERGED
  a4236bb0, with its independent review answered in #8165 MERGED e2fb0a01; and #8167 (an
  observation has one date, which every reader reads through one helper, and a timestamp parted
  by a space dates its row and its published clocks) MERGED 867b6b87
  (DEC:FINANCE-AN-OBSERVATION-HAS-ONE-DATE). The page stays NOT CONNECTED by design
  (FI_READ_URL = "") and T4/T5/T6/T7 stay HELD
  (DEC:FINANCE-INTEGRATES-INTO-SHARED-FOUNDATION-NEVER-REBUILDS-BASE). The seat's T10/T11 lane ids
  are not the waves list's original "Tasks 10-11" breadth verticals, which remain todo in W4.
  Next, all gated on other owners: (1) when #7870 (the Semiconductors shared base) merges, open
  the integration wave: the adapter onto source_record.v1 / evidence_claim.v1 /
  sector_intelligence_packet.v1, then the serving route once accepted, then set FI_READ_URL
  (DSC:FINANCE-PAGE-READS-THE-BARE-READ-MODEL-NOT-THE-RESEARCH-ENVELOPE: the page accepts only the
  bare read model), then a connected browser proof on live data. The T6 publish step MUST run
  validate_contract on the composed document before serving: the composer does not, and the
  sealed contract is the only complete key check. The adapter also owns two input duties the
  composer does not: refuse a malformed owner container per record, as a named omission (the
  composer crashes, closed, on 70 of 184 malformed container shapes on the default fixture), and
  write a source record's own clocks as dates (the contract refuses a timestamp there). (2) Wire
  the Financials launch include when #7669 merges. (3) Carry the deferred review MINORs and the
  T10 gaps (the #7870 owner-bundle wire grammar is not adopted; the round trip is a strict xfail
  until §8 sector_profile is adjudicated) into the integration wave.
---

# Finance Intelligence workstream

Operation `gmi-finance-fable-ceo-e2e-20260924-chairman-001` (parent research operation
`gmi-finance-sector-research-20260923-sol-001`, carrier PR #7786). The Fable seat owns
architecture adjudication, current-main/custody reconciliation, worker routing, integration,
privacy/identity/basket law, independent-review response, browser/production acceptance and
the completion ruling. Bounded fabric workers own task-sized code/test/transcription labor.
