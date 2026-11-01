---
key: LEGACY-THEMATIC-COMPOSE-AGES-FIXTURES-ON-THE-WALL-CLOCK
claim: >
  `engine/neuralweb/thematic_state.compose` decides whether a leg is stale with `_is_stale`.
  That function measures `datetime.now(tz=timezone.utc) - as_of` in whole days against
  `_STALE_DAYS = 5`, so it reads the real wall clock. A test that composes the legacy
  thematic state from fixed-date fixtures, without pinning `thematic_state.datetime`, changes
  behaviour exactly five days after its oldest fixture date. At 2026-10-07T00:00Z the
  owner-adapter test world's narrative fixture (`as_of` 2026-10-02) crossed that line. The
  predecessor gained `stale_legs` strings. The adapter recorded each string as an
  `UNMATCHED_PREDECESSOR_LIST_RECORD` whose `prior_record` is a string, and
  `test_list_optional_receipts_match_stable_identity_and_retired_records_are_disposed`
  failed with `TypeError: string indices must be integers` on main. It failed the same way
  on every PR whose CI pack carried the test.
falsifier: >
  Run the unpinned test under a clock plugin that moves only `thematic_state.datetime` to
  2026-10-20 (the fix PR #8559 describes the plugin). If it passes, the claim is false.
  It is also false if `_is_stale` stops reading `datetime.now`.
so_what: >
  A main red that appears just after a UTC midnight, on a test that composes the legacy
  thematic state, is a fixture time bomb until shown otherwise. Read the failure time and
  rerun the test under a future clock before blaming the newest merge. Any new test that
  calls `thematic_state.compose` on fixture dates must pin `thematic_state.datetime`, using
  the `Clock` subclass idiom in `tests/test_theme_state_owner_adapter.py`. A rerun cannot
  heal a PR that inherited the red, because its merge ref keeps the old main; update the
  branch after the fix lands.
kind: landmine
verified_at: 2026-10-07
verified_by: >
  `gh run view 37548908961 --log-failed` (main at f8d4da2a) shows this one test failing in
  ci-pack-6 at 2026-10-07T00:10:00Z. The previous main proof, 37543947930 at aafb9e25, was
  green. The same test is the only failure in ci-pack-6 for #8552 (run 37549306615) and is
  red in the run for #8554 (37549029203). It reproduced locally at origin/main 0e371362.
  The offending entry is `{'path': '/stale_legs', 'status':
  'UNMATCHED_PREDECESSOR_LIST_RECORD', 'prior_record': 'narrative_emergence: stale
  (as_of=2026-10-02)'}`. The test fails the same way with the adapter as it was before #8539.
  The unpinned test passes with the clock at 2026-10-05 and fails at 2026-10-20. With #8559
  applied, the 9 theme-state test files pass at 2026-10-20 (428 passed). Four more files that
  call `compose` show the same results at the real clock, 2026-10-08T01Z and 2026-10-20:
  test_energy_economic_change_non_regression, test_gmi_cte_generation_bridge,
  test_state_of_themes and test_til_nw_citizenship. Their only 3 failures come from the
  sparse checkout, which lacks `site/` and `data/`.
scope:
  - macro
  - engine/neuralweb/thematic_state.py
  - tests/test_theme_state_owner_adapter.py
confidence: verified
---

Found on 2026-10-07 while landing G1 (#8539). Main went red ten minutes after the UTC date
changed, and the newest merge was G1, which edits `engine/neuralweb/theme_state_adapter.py`.
The obvious suspect was the wrong one: the same test fails identically with the pre-G1
adapter. The only input that changed was the calendar.

The same file already contained the right idiom.
`test_full_v1_candidate_reuses_incumbent_and_preserves_every_field` pins `legacy.datetime`
to a `Clock` subclass whose `now()` returns the test's `EMITTED` instant. The two tests that
broke composed their predecessor without that pin. The `world` fixture pins only the
adapter's capture clock (`adapter.dt`), never the incumbent's. The fix (#8559) copies the
sibling's pin into both tests and changes no product code.

The next date at risk was 2026-10-08T00:00Z, when legs dated on the fixture's `EFFECTIVE`
date (2026-10-03) turn five days old. The future-clock probe above covers that boundary and
2026-10-20, and finds no second failure in the files that compose the legacy state.
