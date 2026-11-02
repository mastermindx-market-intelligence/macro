---
key: FINANCE-INTEGRATES-INTO-SHARED-FOUNDATION-NEVER-REBUILDS-BASE
question: >
  The Finance implementation plan carried four base-layer tasks — T4 (a Finance private
  evidence store over the Research Vault), T5 (a private staging transcriber), T6 (a
  secrets-bearing publish workflow) and T7 (an authenticated serving route). The
  Semiconductor session is building the shared GMI foundation (#7870: assertion, evidence,
  admission, rights, identity, private binding under Sol's R4 ruling, serving routes).
  Does Finance build its own copies now or integrate into the foundation later?
answer: >
  INTEGRATE LATER, never rebuild. Chairman directive 2026-09-24 (relayed from Astra CEO):
  the Semiconductor session builds the base out; Finance does not rebuild it. Finance
  tasks T4, T5, T6 and T7 are HELD (their lane packets quarantined, the T4 lane that had
  started on m1 was killed before delivering). Finance continues ONLY the sector-specific
  layers — the read-model contract (T1, merged), overlap/basket-state context (T3),
  the pure projection composer (T2, owner-input dataclass boundary), the dossier design
  (D1a/D1b), the page shell + hydration behind ONE endpoint constant (T8) and the entry
  points (T9) — and binds to the foundation's private store, publication lane and
  serving route when those are accepted on main.
rationale: >
  Two private bindings, two publication lanes and two serving routes for one product are
  the duplicate-owner failure the DO_NOT_REDO list exists to prevent; the R4 ruling already
  fixed ONE native owner. Finance's real content is the rerating-first read model and its
  surface, which need no base of their own.
alternatives:
  - option: >-
      Finish T4–T7 now as Finance-local pieces and migrate to the foundation later
    why_not: >-
      Every migrated piece is thrown away; meanwhile two owners publish protected bodies
      under two conventions and the nonce-proof privacy gate must be proven twice.
  - option: >-
      Pause the whole Finance program until the foundation lands
    why_not: >-
      T2, D1, T8 and T9 are foundation-independent and the contract already fixes the
      integration seam; pausing them wastes the fabric window for nothing.
evidence:
  - >-
    Chairman message to the Finance seat, 2026-09-24 ~07:46Z (relaying Astra CEO):
    "do not rebuild the base … integrate into that foundation later and let the
    Semiconductors session build that base out".
  - >-
    #7870 head d5b0c00d772e ships contracts/theme_graph/{curation_assertion,evidence}.v1
    and engine/theme_graph/{admission,curation_assertion,rights}.py; Sol ruling
    SOL-R4-PRIVATE-BINDING-20260924-HEALTHCARE-R11 (#7780 comment 5808854275) fixes one
    Research Vault owner, immutable publish fencing, a nonce-object privacy proof and the
    shared /api/themes/v1/research/{query,evidence} routes.
  - >-
    m1 lane fin_t4_private killed 07:47Z before any commit; args for fin_t4/t5/t6/t7
    renamed *.HELD-foundation-integration-20260924 in the seat kit.
affects:
  - "WS:GMI-FINANCE-INTELLIGENCE"
  - "WS:GMI-THEME-GRAPH"
  - "contracts/sector_intelligence/finance_intelligence_read_model.v1.schema.json"
confidence: high
reversibility: easy
review_by: 2026-10-08
decided_by: coo-fable
decided_at: 2026-09-24
---

Seat ruling R-FIN-8, superseding R-FIN-7's route stance: Finance mints NO serving route of
its own; the T8 page hydrates through one constant (`FI_READ_URL`) that is bound to the
foundation's serving route at integration time. Integration items Finance will owe once
the foundation is accepted: (1) an adapter from the shared assertion/evidence bodies to
`finance_intelligence_read_model.v1.source_records[]` (field names already mirror the
shared assertion, DEC:FINANCE-EVIDENCE-GRAMMAR-MIRRORS-SHARED-ASSERTION-NEVER-FORKS);
(2) the Finance first-vertical research packet transcribed INTO the shared assertion
admission path, not a Finance-private store; (3) a composed-dossier serving kind on the
foundation's route family, requested from the shared owner rather than built beside it.
The completion standard is unchanged (real signed-in journey with browser proof) and is
now gated on the foundation's serving route, which the records will say plainly.
