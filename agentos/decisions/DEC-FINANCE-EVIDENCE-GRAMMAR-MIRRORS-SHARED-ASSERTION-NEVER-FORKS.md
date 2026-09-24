---
key: FINANCE-EVIDENCE-GRAMMAR-MIRRORS-SHARED-ASSERTION-NEVER-FORKS
question: >
  The shared theme_graph.curation_assertion.v1 (#7870, not yet on main) requires
  scope.canonical_theme_id and subject.company_node_id, but Finance has no canonical theme
  and its witnesses are RESEARCH_HINT_UNVALIDATED identities. How does the Finance read
  model carry source evidence without forking the shared assertion or minting a Finance
  evidence ledger?
answer: >
  finance_intelligence_read_model.v1 carries DISPLAY-TIER source_records[] whose field
  names mirror the shared assertion's source / observation / temporal / limitations
  sub-shapes (publisher, source_uri, locator, published_at, observed_at, retained_at,
  native_digest; value, unit, quantity_basis, gross_net_basis, stock_flow, estimate_status;
  business_valid_from/to; establishes / does_not_establish) plus an evidence_ref that is the
  accepted assertion's curation_revision when one exists and null otherwise. Canonical
  evidence lives only in the shared assertion + private Research Vault owner; the read model
  never becomes a store, never is written by a curation path, and never ships full-fidelity
  bodies publicly. The R11 §14.1 Finance sections (finance_scope / finance_measurement /
  finance_rerating_context) are requested from the #7870 first author as an extension of the
  ONE shared payload.
rationale: >
  A display projection with the same vocabulary lets the UI, tests and later the shared
  assertion converge without a second grammar, while identity gaps stay honest
  (IDENTITY_UNRESOLVED) instead of being hidden behind a fake company_node_id or a
  fabricated canonical theme. Forking the assertion is DO_NOT_REDO by the handoff §12.
alternatives:
  - option: "Wait for #7870 to merge and for the Finance extension to be accepted before any Finance evidence work"
    why_not: "Blocks Waves 1–3 on a sibling DRAFT/HOLD lane with an open R4 decision; the projection and UI can be built and proven on synthetic + display-tier records now."
  - option: "Bind Finance assertions to fintech_payments as canonical_theme_id"
    why_not: "Only the payments domain has a canonical theme; capital-markets slices would need a minted Finance theme, which the handoff forbids."
evidence:
  - "git show 2deb758859d7:contracts/theme_graph/curation_assertion.v1.schema.json — required sub-fields listed in the Finance handoff record."
  - "research/finance/FINANCE_PRODUCT_EXPERIENCE_AND_OWNER_PRESERVING_DATA_CONTRACT_2026-09-23.md §14.1 at #7786 @615f1050."
  - "GMI-FINANCE-MASTER-FABLE-CEO-HANDOFF-2026-09-24.md §12 (do not fork curation_assertion; do not create a Finance graph/ledger)."
affects:
  - "WS:GMI-FINANCE-INTELLIGENCE"
  - "WS:GMI-THEME-GRAPH"
  - "contracts/sector_intelligence/finance_intelligence_read_model.v1.schema.json"
confidence: medium
reversibility: easy
review_by: 2026-10-08
decided_by: coo-fable
decided_at: 2026-09-24
---

# Finance evidence grammar

Display-tier mirroring of the shared assertion vocabulary; canonical evidence stays with the
shared owner. Revisit once #7870 lands and the Finance extension sections are ruled.
