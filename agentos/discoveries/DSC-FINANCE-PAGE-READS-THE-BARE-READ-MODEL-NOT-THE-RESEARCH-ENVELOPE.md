---
key: FINANCE-PAGE-READS-THE-BARE-READ-MODEL-NOT-THE-RESEARCH-ENVELOPE
claim: >-
  Connecting finance_intelligence.html is not a one-constant change. The page's boot()
  accepts only a document whose top-level contract_id is finance_intelligence_read_model.v1
  and renders contract_invalid otherwise. The shared-shell route instead returns the
  Finance research envelope: contract_id finance_intelligence_research.v1, with the T1
  read model nested under "dossier" beside generation, assertion_refs, limitations and
  authority. openEvidence() reads only records inside the document and never calls a
  generation-pinned evidence route.
falsifier: >-
  Read templates/finance_intelligence.js boot() (the contract_id check after
  fetchJson(FI_READ_URL)) and engine/sector_intelligence/finance_research_registration.py
  compose() (the envelope literal). The claim is false if boot() unwraps a "dossier" key,
  or if the envelope's top-level contract_id equals the read model's.
so_what: >-
  The integration wave, after #7870 and the §8 sector_profile ruling, owes a client
  change in the same PR as setting data-fi-read-url. That change must: unwrap "dossier";
  keep "generation" and pass it as expected_generation to evidence requests; render
  the envelope's limitations; and map the shell's refusal codes to the page's notice
  states. Setting FI_READ_URL alone ships a page that says the contract is invalid.
kind: architecture
verified_at: 2026-09-25
verified_by: "templates/finance_intelligence.js boot() contract_id check (main); finance_research_registration.py compose() envelope (PR #8006 @1d307ec0)"
scope:
  - macro
  - templates/finance_intelligence.js
  - engine/sector_intelligence/finance_research_registration.py
confidence: verified
---
