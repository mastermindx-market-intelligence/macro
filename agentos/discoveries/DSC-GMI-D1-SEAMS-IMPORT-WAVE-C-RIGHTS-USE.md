---
key: GMI-D1-SEAMS-IMPORT-WAVE-C-RIGHTS-USE
claim: >
  The Wave D1 selection-cohort publication seams on PR #8417
  (`engine/theme_graph/selection_cohort_publication.py:48`) import `capture_capability` from
  `engine.theme_graph.rights_use`, a module that exists only on the Wave C PR #8485
  (`rights_use.py:286` at head 74467f24300a) and not on main. Until #8485 lands, every
  merge-ref CI run of #8417 fails exactly one unit —
  `tests/test_first_party_import_names.py::test_every_first_party_import_resolves` in the
  legacy pack carrying `nyse-calendar-freshness` — and that red is a composition dependency,
  not a defect of D1.
falsifier: >
  A merge-ref ci.yml run of #8417 that is red on `test_every_first_party_import_resolves` after
  `engine/theme_graph/rights_use.py` exporting `capture_capability` is present on origin/main;
  or `git grep capture_capability origin/main -- engine/theme_graph/rights_use.py` returning a
  hit while the unit still fails.
so_what: >
  Release order is #8485 -> #8417 -> #8486. Do not vendor or duplicate `rights_use` into #8417
  to make it green (that would create two definitions of the rights capture surface), and do
  not classify the #8417 red as the lane's fault. After #8485 merges, re-prove #8417 with a
  plain merge-of-main push preceded by a freshness re-read of its held carrier.
kind: constraint
verified_at: 2026-10-05
verified_by: >
  ci.yml run 37299950277 job 111731226761 log (pack-10 `nyse-calendar-freshness`): the single
  failing test names selection_cohort_publication.py:48; `rights_use.py:286` on #8485 head
  74467f24300a defines capture_capability; the path is absent on origin/main 20eb503a09.
scope:
  - macro
  - engine/theme_graph/
confidence: verified
cited_by:
  - WS:GMI-THEME-GRAPH
---

Found while attributing the ci-pack red on #8417 on 2026-10-05. The Wave C and Wave D1 lanes
were commissioned in parallel from one frozen spec that named `rights_use` as the capture
surface; D1 correctly consumed the contract, so the dependency is by design and the fix is
ordering, not code.
