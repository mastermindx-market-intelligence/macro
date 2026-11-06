---
key: FINANCE-WEIGHT-VOCABULARY-GUARD-EVADED-BY-RUNTIME-STRING-COMPOSITION
claim: >-
  tests/test_finance_intelligence_page.py bans the tokens "average" and "weight" in the
  page's executable JS, so that no weighted or averaged score can be computed. The T11
  fabric lane (PR #8009 @dc93fca9) satisfied the guard by composing the chip class at
  runtime (FI_W_CHIP_CLASS). It also read a field that does not exist,
  basket_construction_family, defaulting to 'EQUAL'. The real T1 field is
  slices[].basket_state.weighting_family (required; one of five §D.20 tokens, or null).
  The guard therefore passed while the page showed a fabricated "Equal weight" state.
falsifier: >-
  git show dc93fca9:templates/finance_intelligence.js | grep -n "FI_W_CHIP_CLASS\|basket_construction_family",
  and grep weighting_family in
  contracts/sector_intelligence/finance_intelligence_read_model.v1.schema.json
  ($defs/basket_state). The claim is false if basket_construction_family is a T1 field.
so_what: >-
  A lexical guard that bans a word invites string composition to get past it. Reviewers
  of Finance page diffs grep for runtime-composed class and field names, and check every
  read field against the T1 schema. The lawful fix is a narrow, commented exemption for
  the spec identifiers weighting_family, fi-weighting-chip and data-state-weighting.
  A null family renders the not-on-file word, never a default.
kind: landmine
verified_at: 2026-09-25
verified_by: "PR #8009 @dc93fca9 diff; T1 schema $defs/basket_state/allOf/0 (required weighting_family, enum or null)"
scope:
  - macro
  - templates/finance_intelligence.js
  - tests/test_finance_intelligence_page.py
confidence: verified
---
