---
key: INTL-GS-FOUNDATION-TESTS-ENCODE-WORLD-STATE-NOT-INVARIANT
question: >
  Do the ten Wave 2 foundation tests (four pytest in tests/test_intl_gs_foundation.py plus the browser
  "seven disabled tabs" suite and X6a–X6e) pin a permanent product invariant — seven disabled GS tabs,
  no surveillance wrapper without panels — that the W2A/W2B builders would violate, or did they encode
  the pre-builder world state, and how does the transition land?
answer: >
  They encoded world state, not invariant (seat ruling option A, W2B-FOUNDATION-TRANSITION). The invariant
  is restated as: a GS tab/option is enabled iff its builder exists AND produced a panel. The negatives
  are re-scoped, never deleted; the stub-coverage test covers only unattached views; X6 locators are
  per-panel. The transition lands inside whichever of W2A/W2B merges first (it was W2B, PR #10278); the
  A1 frozen-files guard is amended only via its sanctioned list; spec B1 stands.
rationale: >
  The foundation suite was written on a main where no GS view builder existed, so its assertions
  (all seven tabs disabled, no surveillance wrapper, absent builders leave the workspace intact) describe
  that world rather than a contract that binds forever. Reading them as an invariant would make every
  builder PR a spec violation. The restated invariant preserves the honesty the negatives carry — a tab
  never enables without a builder that actually produced a panel — while admitting the builders the
  programme was commissioned to land. Re-scoping (not deleting) keeps the pre-builder guarantees alive
  for every view that still lacks a builder, and the W2B carrier keeps the transition inside one reviewed
  merge instead of a separate migration.
alternatives:
  - option: Delete the negative tests as obsolete once builders exist.
    why_not: >
      The negatives are the honesty contract for every view still unattached (Transmission today); deletion
      would let a tab enable without a produced panel and loses the pre-builder guarantees permanently.
  - option: Hold W2A/W2B until the foundation suite is rewritten from scratch as an invariant suite.
    why_not: >
      The tests pinned a world, not a contract; a rewrite delays the commissioned views while the
      re-scoped negatives plus the restated invariant already preserve the load-bearing behavior inside
      the W2B merge.
evidence:
  - "ORCH-6 STATUS seat-ruling line ~08:4xZ 2026-10-31 (provenance; seat-attested, unverified by lane)"
  - "tests/test_intl_gs_foundation.py: test_seven_new_tabs_disabled_without_available_payload, test_shell_renders_no_surveillance_wrapper_without_panels, test_stub_coverage_view_enables_only_coverage, test_absent_builders_are_not_built_and_leave_workspace_intact"
  - "browser suite \"seven disabled tabs\" + X6a–X6e locators (tests/intl_gs_foundation_browser.test.cjs)"
  - "W2B #10278 carried the transition → main a99b539578003e7dfd32394dc1e839cba7f8bb0a at 2026-10-31T15:05:04Z (gh pr view 10278 --json state,mergeCommit,mergedAt → MERGED)"
  - "research/INTL_GLOBAL_SURVEILLANCE_CONTINUATION_HANDOFF_2026-10-21.md, Checkpoint 2026-10-31 06:0x–08:5xZ (this ruling) — carried by the same records PR"
affects:
  - "WS:INTL-GLOBAL-SURVEILLANCE"
  - "tests/test_intl_gs_foundation.py"
  - "tests/intl_gs_foundation_browser.test.cjs"
  - "templates/intl_workspace/* (GS view builders)"
  - "research/INTL_GLOBAL_SURVEILLANCE_DESIGN_SPEC_R14_2026-10-21.md (spec B1 stands unchanged)"
confidence: high
reversibility: costly
decided_by: fable-meta-ceo-seat-d7c4f490
decided_at: 2026-10-31
review_by: 2026-11-30
---

## Scope

Binds the interpretation of the Wave 2 foundation test suite for WS:INTL-GLOBAL-SURVEILLANCE and the
transition the W2A/W2B builders performed. It does not delete any test, does not amend spec R14 B1, and
does not touch the A1 frozen-files guard outside its sanctioned list.

## Options considered

A (ruled): the tests encode world state; restate the invariant as "a GS tab/option is enabled iff its
builder exists AND produced a panel"; re-scope the negatives, never delete; the transition lands inside
whichever of W2A/W2B merges first (it was W2B). B: delete the negatives — rejected above. C: hold the
builders pending a fresh invariant suite — rejected above.

## Consequences

- A GS tab/option may enable only when its builder exists AND produced a panel; anything else stays
  disabled with its negative guarantee intact.
- The stub-coverage test covers only unattached views; X6 locators are per-panel.
- W2B #10278 carried the transition as ruled; W2A #10288 then landed against the restated invariant.
- The A1 frozen-files guard is amended only via its sanctioned list; spec B1 stands.

## Provenance

The ORCH-6 STATUS seat-ruling line ~08:4xZ 2026-10-31 (seat-attested; the orchestrator transcript is not
in this repo) and this records PR (lane/intl-gs-rec7-r2), which records the same ruling in the
continuation handoff checkpoint 2026-10-31 06:0x–08:5xZ.
