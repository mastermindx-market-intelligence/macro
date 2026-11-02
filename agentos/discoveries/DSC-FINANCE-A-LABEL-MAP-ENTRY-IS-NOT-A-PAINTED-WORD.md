---
key: FINANCE-A-LABEL-MAP-ENTRY-IS-NOT-A-PAINTED-WORD
claim: >-
  On the Finance Intelligence page, a value having a word in FI_LABELS does not mean the page
  shows it. At T11 round 3b the contract-coverage test
  (test_every_value_the_contract_admits_has_a_page_word_in_both_languages, 56 enum paths)
  was green. Meanwhile the exposure matrix kept cells[].exposure.state only in
  data-state-exposure and never painted the spec §D.8 chip. So a cell whose exposure is not
  separately disclosed read like a measured one. The phone card, the only exposure surface
  below 768 px, also had no identity chip. It showed only the first six cells of any
  vertical. The seat found all three by checking the evidence receipt's own claim ("covers
  every exposure state") against the contract. It walked the schema's company-exposure enums
  over the capture document, found values missing, and then found that the page could not
  have shown them anyway.
falsifier: >-
  Revert exposureChip(cell) in templates/finance_intelligence.js and run
  tests/test_finance_intelligence_hydration.py. The claim is false if
  test_every_exposure_cell_names_its_exposure_state_in_words stays green, or if the coverage
  test goes red. The round-3c red-proof replay ($S/redproof_r3c.py) records exactly this row.
so_what: >-
  Pair every label-map coverage guard with a paint test. The paint test runs over a
  contract-valid document that exercises every value and asserts the words appear in the
  painted DOM, at every viewport's surface: table and phone card alike. Before an evidence
  receipt claims coverage of a state family, walk the schema's enums over the capture
  document; the capture tool validates nothing.
kind: landmine
verified_at: 2026-09-27
verified_by: "PR #8009 round 3b/3c: schema walk over the capture document; hydration tests on a composer-built contract-valid document; red-proof replay rows r3c_*"
scope:
  - macro
  - templates/finance_intelligence.js
  - tests/test_finance_intelligence_hydration.py
confidence: verified
---
