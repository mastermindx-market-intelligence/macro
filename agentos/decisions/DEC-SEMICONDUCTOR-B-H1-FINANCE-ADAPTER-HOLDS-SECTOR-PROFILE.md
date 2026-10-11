---
key: SEMICONDUCTOR-B-H1-FINANCE-ADAPTER-HOLDS-SECTOR-PROFILE
question: >
  The shared research shell on #7870 (engine/market_ontology/theme_research_registry.py,
  VerticalRegistration, 14 fields) requires a canonical anchor_theme_id plus non-empty
  slice_keys. Finance's section-8 facts are a sector_profile with neither. The Finance
  adapter's roundtrip test went RED on the shell (TypeError: 12 of 14 fields sent) and
  its inherited xfail(raises=ValueError) could not discriminate "shell absent" from
  "shell present and incompatible". How is H1 closed on the #7870 carrier?
answer: >
  Ruling B. The Finance adapter refuses with the typed hold
  `vertical_registration_held:sector_profile`, raised after the shell-availability check
  and before construction, whenever the facts lack a string anchor_theme_id or
  non-empty slice_keys. The adapter forwards its 12-field share unchanged; the
  12-versus-14 gap is pinned by a field-gap test, not papered over with invented
  defaults. The absorbing xfail is deleted and replaced by exact-string refusal
  assertions. Never invent an anchor to pass the hold. Option A (a registry
  `entry_kind` admitting sector_profile/company_profile with an optional anchor) is
  the follow-on carrier AFTER #7870, which Technology #7891 and Consumer Cyclical
  #7780 also need.
rationale: >
  #7870 is the shared foundation at approved scope; widening the registry's identity
  contract inside the foundation carrier would change the §8 dispatch grammar for
  every vertical under one PR's review. A typed hold keeps Finance honest (the real
  facts never reach the shell), keeps the shell's canonical-id invariant intact, and
  leaves the semantic change (Option A) to a carrier whose review can be scoped to it.
  The Chairman's consolidation (DEC:CHAIRMAN-INDUSTRY-INTELLIGENCE-META-CEO-CONSOLIDATION-2026-10-11)
  put both Finance files under this seat, which formally supersedes Sol's earlier
  "do not edit either Finance file" fence (#7870 comment 6105015260 section C-3).
alternatives:
  - option: "Option A inside #7870: add entry_kind to VerticalRegistration and make anchor optional."
    why_not: Changes the registry identity grammar for every vertical in the foundation carrier; the shell's canonical-id invariant and its 64 tests were reviewed at the narrower scope.
  - option: "Supply the two missing kwargs (view_keys, build_query) and keep the xfail."
    why_not: Lands on the anchor-grammar ValueError, which the refusal class wraps, so the xfail absorbs it and reports the same XFAIL as the shell-absent base. A false green that migrates nothing.
  - option: "Invent a finance anchor id to satisfy the grammar."
    why_not: Finance has no canonical theme; a minted anchor would be a fabricated identity in a shared registry.
evidence:
  - "#7870 comment 6104604040: H1 analysis (three states of the roundtrip test at head 4eafc4c06886; base XFAIL, head FAIL TypeError, 'repaired' XFAIL via absorption)."
  - "#7870 comment 6105015260 section C: the H1 ruling B and the section C-3 supersession of the Finance-file fence."
  - "Implemented at b76551be8a40 (ruling B), audit-repaired at acc72f3fb3efb1ad092359ce2ba4190de66d75e1 (PR head, pushed 2026-10-11)."
  - "Independent Opus audit (READ_ONLY, ROUTE: AUDIT) of b76551be: VERDICT ACCEPT_WITH_FIXES; findings F1 to F3 (comments/docstrings) and notes N4, N5, N6, N8 applied at acc72f3f; N7, N9 accepted as-is. The seat (the builder) judged the delta behaviour-neutral (test file 98 -> 100 passed); because that judgment is the builder's own, a fresh non-author review of the b76551be..acc72f3f delta was owed under DEC:FABLE-SEAT-IS-CEO-COEQUAL-WITH-SOL and is in hand as #7870 comment 6105402719 (independent READ_ONLY Opus, VERDICT ACCEPT_DELTA, 2026-10-11). That review is pinned to acc72f3f: any later release head extends it to acc72f3f..<new head> before release."
  - "Local evidence at acc72f3f in the #7870 worktree: tests/test_finance_research_registration.py 100 passed with the shell present (a forced-absent run has no recorded command and is listed as unverified in the 2026-10-11 handoff); tests/test_theme_research_registry.py 64 passed; positive control (predicate weakened to anchor-only) fails test_hold_requires_both_anchor_and_slices[string-anchor-empty-slices]."
affects:
  - WS:GMI-SEMICONDUCTORS
  - WS:GMI-FINANCE-INTELLIGENCE
  - WS:GMI-TECHNOLOGY-EX-SEMIS
  - WS:CONSUMER-CYCLICAL-V1
  - engine/sector_intelligence/finance_research_registration.py
  - tests/test_finance_research_registration.py
  - engine/market_ontology/theme_research_registry.py
confidence: high
reversibility: easy
decided_by: fable-meta-ceo
decided_at: 2026-10-11
---

## The law this records

An xfail pinned to a builtin exception type absorbs every domain refusal that
subclasses it. `FinanceRegistrationRefusal(ValueError)` plus
`xfail(raises=ValueError)` meant the base ("shell absent") and the "repaired" state
("shell present, grammar refused") reported identically. A hold that must
discriminate two causes needs an exact-string assertion on the refusal code in an
unmarked test. Ruling B makes that the contract.

## What Option A must carry

A registry `entry_kind` field admitting `sector_profile` and `company_profile`, an
optional `anchor_theme_id` for non-theme entries, the §8 sector-profile dispatch
semantics, and the adapter forwarding of `view_keys` and `build_query`. It is a
follow-on carrier; it is not #7870.
