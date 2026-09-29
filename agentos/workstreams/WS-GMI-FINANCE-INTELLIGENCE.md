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
artifacts:
  - agentos/handoffs/GMI-FINANCE-INTELLIGENCE-2026-09-24.md
  - agentos/handoffs/GMI-FINANCE-INTELLIGENCE-2026-09-27.md
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
  2026-09-27 wave closed (handoff GMI-FINANCE-INTELLIGENCE-2026-09-27). Before it: T1-T3 contract,
  composer and overlap merged; T8 shell + hydration and four live-proof fixes merged and
  production-proven at 1440/390 x dark/light x EN/ZH with keyboard; T9 Theme Tracker entry live.
  This wave, each through independent Opus review and a seat red-proof: the seat's T10 lane
  #8006 (registration adapter onto the shared research shell) MERGED 977dca13
  (DEC:FINANCE-REGISTRATION-OMISSIONS-ARE-A-CLOSED-VOCABULARY-AND-EVIDENCE-EMBEDS-THE-VALIDATORS-COPY);
  the seat's T11 lane #8009 (connected-state conformance on a contract-valid read model) MERGED
  c58fdc16 (DEC:FINANCE-DOSSIER-SPEC-T11-ERRATA, DSC:FINANCE-QUALITATIVE-CLASS-DOES-NOT-MEAN-NO-NUMBER,
  DSC:FINANCE-A-LABEL-MAP-ENTRY-IS-NOT-A-PAINTED-WORD); and #8113, the inbound fail-open fix
  (an unknown freshness publishes NO_EVIDENCE, never FRESH), MERGED 74055425; and #8121, a
  latent owner-key leak through primary_metric closed by a closed metric vocabulary plus the
  forbidden-key guard actually running at emit, MERGED 808432ec
  (DSC:A-LEAK-TEST-OVER-A-CLEAN-FIXTURE-CANNOT-FAIL-PLANT-THE-OWNER-KEYS). Four composer
  follow-ups then closed what those reviews left open: #8130, a malformed owner value is refused
  by the contract, never by a crash (an in-suite positive control, no independent review), MERGED
  f6dae649; #8134, the composer never mints an evidence ref and a slice no owner ref backs
  publishes no reading and no date, MERGED 88ca79a3 (DEC:FINANCE-COMPOSER-NEVER-MINTS-AN-EVIDENCE-REF);
  and #8135, a slice publishes only its own valuation anchor and constraints and a conflict reads
  the reading its plane publishes, MERGED 2a937915
  (DSC:A-SLICE-WIDE-REF-LIST-VOUCHES-FOR-A-VALUE-BORROWED-FROM-ANOTHER-SLICE); and #8138, the
  knowledge cutoff binds every reader: one gate where the inputs enter reads each knowledge clock
  as the instant the contracts read and as the date the composer publishes, the registration
  adapter names and selects theme evidence through the same gate, a receipt reads DEGRADED when
  the cutoff withheld every row of its input, and a cutoff that names no instant is refused,
  MERGED fbd78d12 after three review rounds
  (DSC:A-KNOWLEDGE-CUTOFF-BINDS-ONLY-THE-READERS-THAT-APPLY-IT). The page stays
  NOT CONNECTED by design (FI_READ_URL = "") and T4/T5/T6/T7 stay HELD
  (DEC:FINANCE-INTEGRATES-INTO-SHARED-FOUNDATION-NEVER-REBUILDS-BASE). The seat's T10/T11 lane ids are
  not the waves list's original "Tasks 10-11" breadth verticals, which remain todo in W4.
  Next, all gated on other owners: (1) when #7870 (the Semiconductors shared base) merges, open
  the integration wave: the adapter onto source_record.v1 / evidence_claim.v1 /
  sector_intelligence_packet.v1, then the serving route once accepted, then set FI_READ_URL
  (DSC:FINANCE-PAGE-READS-THE-BARE-READ-MODEL-NOT-THE-RESEARCH-ENVELOPE: the page accepts only the
  bare read model), then a connected browser proof on live data. The T6 publish step MUST run
  validate_contract on the composed document before serving: the composer does not, and the
  sealed contract is the only complete key check. (2) Wire the Financials launch
  include when #7669 merges; (3) carry the deferred review MINORs and the T10 gaps (the #7870
  owner-bundle wire grammar is not adopted; the round trip is a strict xfail until §8
  sector_profile is adjudicated) into the integration wave; (4) optional before that wave: give
  the operating plane the valuation anchor's undated and tie rules, and the price plane a stated
  undated rule. The cutoff itself is one gate since #8138. (5) Two #8138 follow-ups: the
  registration limitations name owner_input_absent:theme_evidence when the cutoff withholds every
  assertion, and a container-totality lane derives receipts from the rows the gate kept and
  canonicalizes one-shot containers before the digest (the 09-27 handoff's next_actions).
---

# Finance Intelligence workstream

Operation `gmi-finance-fable-ceo-e2e-20260924-chairman-001` (parent research operation
`gmi-finance-sector-research-20260923-sol-001`, carrier PR #7786). The Fable seat owns
architecture adjudication, current-main/custody reconciliation, worker routing, integration,
privacy/identity/basket law, independent-review response, browser/production acceptance and
the completion ruling. Bounded fabric workers own task-sized code/test/transcription labor.
