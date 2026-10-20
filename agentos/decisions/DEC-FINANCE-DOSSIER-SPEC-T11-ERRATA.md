---
key: FINANCE-DOSSIER-SPEC-T11-ERRATA
question: >-
  During T11 connected-state acceptance, the frozen Finance dossier spec
  (research/finance/implementation/FINANCE_DOSSIER_DESIGN_SPEC_2026-09-24.md) and the T11
  packet disagreed with the shipped page's structure, with CSS specificity, and with the
  house design system. Which rule governs in each case?
answer: >-
  Seven errata, taken by the seat and shipped in PR #8009: (a)-(d) in round 2, (e)-(f) in
  rounds 3b/3c with (e)'s claim corrected in round 3d, and (g) in round 3d.
  (a) The light-theme chip base rule is written
  :where(html[data-theme="light"]) .fi-chip { background: var(--fi-panel); }. Unwrapped,
  at specificity (0,2,1), it outranks every per-state chip rule (0,2,0) and paints every
  state chip white.
  (b) The identity chip is a STATE chip (fi-identity-chip, carrying its state word). It is
  not an evidence trigger or button.
  (c) The ZH source-language note is the first body line directly after each section's
  .fi-section-head. The packet's .fi-sowhat anchor exists nowhere in the spec or the page.
  (d) What-changed rows are the house DecisionRow that spec §B.1 pins (.mx-chg-row with
  .mx-chg-name / .mx-chg-what). .fi-change-list drops its UA bullets and indent, as the
  page's other lists do. The T8 build omitted it.
  (e) The phone exposure card lists the row's POPULATED first-vertical cells, in the table's
  column order: the identity chip, then role, materiality and the §D.8 exposure-state chip
  for each cell. It does not mirror the row. The table paints "No role recorded" for an
  empty slice column and shows basis, retained risk and evidence date; the card shows none
  of these, like the spec's macro cards, which also list populated cells only. Spec §B.5
  calls the cards "the table's first 8 rows", and the mockup card carries both chips. The
  card keeps the role word, which the mockup omits. (Rounds 3b/3c first claimed the card
  mirrors its row; the round-3c re-review F3 showed that was overstated, and round 3d
  corrected the claim, not the code.)
  (f) Spec copy defects are recorded here as amendment proposals, not applied. The page
  implements the spec's words exactly:
  - §B.7 constraint rows do not name their slice.
  - §D.7 gives near-synonyms for AUC_A and AUM in ZH (在管资产规模 / 在管资产).
  - §D.7 renders TRANSACTION_VOLUME as 交易笔数, which reads as a count.
  - §D.6 role DIRECT_DIVERSIFIED and §D.8 state DIRECT_DIVERSIFIED share the EN words
    "Direct, diversified".
  - §D.0 rule 1's glance words "No metric on file" read literally false for a QUALITATIVE
    record once the drawer prints its stated number (see (g)); "Qualitative read" is the
    proposed wording (round-3d independent re-review).
  (g) The evidence drawer's Value row is the RECEIPT. It prints a stated metric.value
  whatever its measurement_class, with every stated digit and never in exponent form, then
  unit, currency and period. §D.0 rule 1 (QUALITATIVE renders "No metric on file") governs
  the glance tier of the seven L1 sections, not the §B.0 aside, whose value only the rights
  rule may suppress. The T2 composer gives every classless observation the class QUALITATIVE
  with its value kept (DSC:FINANCE-QUALITATIVE-CLASS-DOES-NOT-MEAN-NO-NUMBER), so applying
  rule 1 in the drawer denied numbers the page's own composer publishes.
  In every case the observed page plus the house design system corrects the letter of the
  spec. The spec's intent (state colour, a plain-word note, the DecisionRow, states shown as
  words at every viewport) is unchanged.
rationale: >-
  Each erratum was found by measuring a real browser against the connected page (seat
  probe, 1440/390 x dark/light x EN/ZH plus keyboard), not by reading code.
  (a) is a cascade fact: a later, more specific base rule silently defeats the colour map
  in one theme only.
  (b) A chip that opens nothing must not be announced as a control.
  (c) An anchor that does not exist makes the insertion fall through to the end of the
  section, putting the note in the wrong place for every ZH reader.
  (d) The spec pins the house row so that change lists read identically across products.
  Recording the errata stops the next session from "restoring" the letter of the spec
  and re-breaking the page.
alternatives:
  - option: amend the frozen spec file in place
    why_not: the spec is a frozen, dated artifact that other packets cite by section; errata recorded beside it keep those citations stable
  - option: follow the packet letter (.fi-sowhat anchor, unwrapped base rule, identity as a trigger)
    why_not: each measurably breaks the connected page (probe checks 2, 4 and 10c fail)
evidence:
  - "PR #8009 round-2 seat commit 6ad670ae: probe 122 PASS / 0 FAIL / 4 INFO (126 checks), against 92/30/4 on round-1 head 68619ffe"
  - "negative control (pre-erratum note anchor plus an injected langchange tab reset) fails 10c x4 and 8/8b x4, showing the probe discriminates"
  - "grep -n 'fi-sowhat' research/finance/implementation/FINANCE_DOSSIER_DESIGN_SPEC_2026-09-24.md templates/finance_intelligence.html.j2 returns nothing"
  - "tests/test_finance_intelligence_page.py: test_light_chip_base_rule_cannot_outrank_the_state_chip_rules, test_identity_chip_is_a_state_chip_not_an_evidence_trigger, test_source_language_notes_follow_the_section_header_without_a_lang_attribute, test_what_changed_rows_are_the_house_decision_row"
  - "evidence receipt mockups/evidence/finance-t11-conformance (24/24 cells captured)"
  - "round 3d: test_the_receipt_prints_every_stated_number_in_plain_digits; red-proof 5/5 RED; independent Opus re-review PASS with no findings (plainDigits exact on 299,838 random finite doubles and the double extremes)"
  - "round 3b/3c: tests/test_finance_intelligence_hydration.py test_every_exposure_cell_names_its_exposure_state_in_words, test_a_phone_card_names_its_identity_state, test_a_phone_card_lists_its_table_rows_cells_in_column_order, run on a composer-built contract-valid document; red-proof replay rows r3c_*"
affects:
  - WS:GMI-FINANCE-INTELLIGENCE
  - templates/finance_intelligence.css
  - templates/finance_intelligence.js
  - research/finance/implementation/FINANCE_DOSSIER_DESIGN_SPEC_2026-09-24.md
confidence: high
reversibility: easy
decided_by: "seat 938d17d6 (Finance Intelligence CEO seat, operation gmi-finance-fable-ceo-e2e-20260924-chairman-001)"
decided_at: 2026-09-25
---
