---
key: FINANCE-SEC-EVIDENCE-RIGHTS-HELD-UNTIL-FAMILY-ADMITTED
question: >
  Every first-vertical Finance source record cites an SEC EDGAR filing (10-K/10-Q/8-K
  exhibits) and config/theme_sources.yml carries no SEC family (only mastermind_curated,
  finviz_themes, ths_concepts), so finance_private.qualify_rights fails closed to
  SOURCE_RIGHTS_HELD for all eleven witnesses. Does the Finance program mint its own
  rights family, display the filings anyway as public-domain government records, or hold?
answer: >
  HOLD, typed. The read model serves the record's facts, business scope, metric, clocks and
  the five limitations fields with rights_state SOURCE_RIGHTS_HELD; the evidence drawer
  shows the state in words and withholds the outbound source_uri link and any excerpt
  until a `sec_edgar` family is admitted to config/theme_sources.yml by the rights
  registry owner (GMI W3A / the #7870 shared-assertion carrier), with rights_class
  direct_display_ok and the SEC fair-access attribution rule recorded in its review block.
  The Finance program never edits theme_sources.yml and never carries a second rights table.
rationale: >
  The registry is the single rights authority (engine/theme_graph/rights.py fails closed on
  an unknown family by design). Public-domain status of EDGAR filings is real but the
  attribution, retention and excerpt rules belong in the registry's review block, not in a
  consumer's if-branch. A typed hold keeps the product honest (the state is displayed, not
  hidden) and keeps the rerating map usable: metric values, periods and limitations are
  the record's own facts and are displayable; only the outbound link and excerpts wait.
alternatives:
  - option: >-
      Finance-local rights map inside finance_private.py
    why_not: >-
      a second rights owner; forbidden by the program's DO_NOT_REDO list and by the registry's single-authority design (rights.py fails closed on an unknown family on purpose)
  - option: >-
      Treat unknown families as direct_display_ok for SEC hosts
    why_not: >-
      silently widens rights for every future consumer of the registry; the fail-closed default exists to prevent exactly this
  - option: >-
      Block the whole first vertical until the family is admitted
    why_not: >-
      hides eleven researched records behind a rights chip that only governs a link and excerpts; violates 'nulls printed, not hidden'
evidence:
  - >-
    config/theme_sources.yml on origin/main (2026-09-24): families mastermind_curated,
    finviz_themes, ths_concepts; rights_class enum internal_only | derived_display_ok |
    direct_display_ok | unresolved; no SEC family.
  - >-
    Finance T4 packet (fin_t4_private): qualify_rights derives rights_state at read time and
    fails closed on an unknown family; staging never claims display rights.
  - >-
    R11 product freeze: SOURCE_RIGHTS_HELD is a mandatory rendered state, never an error.
affects:
  - "WS:GMI-FINANCE-INTELLIGENCE"
  - "WS:GMI-THEME-GRAPH"
  - "engine/sector_intelligence/finance_private.py"
  - "app/finance_intelligence.py"
  - "templates/finance_intelligence.js"
  - "config/theme_sources.yml"
confidence: high
reversibility: easy
review_by: 2026-10-08
decided_by: coo-fable
decided_at: 2026-09-24
---

Seat ruling R-FIN-6 (2026-09-24). Reversal cost: one registry edit (admitting `sec_edgar`) flips the derived state on the next API request; no Finance code or data changes. Request to the registry owner is posted on #7870 at the
Wave 2 boundary together with the Finance §14.1 extension request; until then the state is
held and displayed. The T7 API and the T8 drawer implement the hold as words, never as a
missing section.
