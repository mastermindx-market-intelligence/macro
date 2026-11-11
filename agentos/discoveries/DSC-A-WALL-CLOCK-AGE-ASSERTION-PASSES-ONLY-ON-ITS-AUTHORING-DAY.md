---
key: A-WALL-CLOCK-AGE-ASSERTION-PASSES-ONLY-ON-ITS-AUTHORING-DAY
claim: >
  A test that constructs a fixture at a fixed CALENDAR date and asserts a rendered AGE
  ("captured 32 d ago") against code that reads `datetime.now(...)` passes only on the day
  it was written, and every review of it is therefore also only valid that day. Measured
  2026-09-26 on macro PR #7930: `tests/test_foresight_cascade.py::test_failed_refresh_
  discloses_the_retained_qualified_capture` built its capture at `datetime(2026, 9, 23) -
  timedelta(days=31)` and asserted `captured 32 d ago`, but drove the chip through
  `engine.fda_scarcity.compute_fda_scarcity`, which takes `now = datetime.now(timezone.utc)`
  (fda_scarcity.py:334) and passes `max_capture_age=None`. Age was measured against the real
  clock and constructed against a frozen one, so the label gained one day per elapsed day.
  The suite was green for six independent Opus review rounds and an exact-head ACCEPT on
  2026-09-24; it read `34 d ago` and failed two days later, with nothing on main having
  touched any of the four D1 modules (`git log 9abf409a..origin/main -- <them>` empty).
  Sibling assertions in the same file survived because they inject `now` into
  `summarize_supply(...)`, so construction and assertion share one clock.
falsifier: >
  `git show 9abf409a:tests/test_foresight_cascade.py` into a tree and run
  `python3 -m pytest tests/test_foresight_cascade.py::test_failed_refresh_discloses_the_retained_qualified_capture -q`
  on any date after 2026-09-24: it fails with an off-by-N-days label diff whose N is the
  days elapsed. It would be disproved by that test passing on a later date, or by
  `compute_fda_scarcity` taking an injected clock.
so_what: >
  Two things change. (1) When writing a test whose expectation contains an age, duration or
  "N days ago", anchor the fixture to the SAME clock the code under test reads — inject
  `now` into the callee, or derive the fixture from `datetime.now(...)` so the asserted
  number is the fixture's own offset. Never pin the fixture to a calendar date and the
  expectation to a literal count. (2) An acceptance run is proof for the head and the DAY it
  ran, not for a later merge: before merging any PR that has waited overnight, re-run its
  own job suites on the merged head rather than trusting the accept. This is cheap and it is
  the only thing that catches clock rot, because CI green on the authoring day looks
  identical to CI green that is about to expire.
kind: landmine
verified_at: 2026-09-26
verified_by: >
  direct observation — macro PR #7930: the accepted head 9abf409a re-run on 2026-09-26 gave
  `1 failed, 126 passed` with the diff `- captured 32 d ago / + captured 34 d ago`; repair
  commit 4a6cf768 (anchors the fixture to the product's clock) restores `127 passed`;
  seat ruling R-D1-MERGE-01 in research/healthcare/hc_program/reviews/SEAT_RULINGS_D1_MERGE_2026-09-26.md
scope:
  - mastermindx-market-intelligence/macro
  - engine/fda_scarcity.py
  - tests/test_foresight_cascade.py
  - tests/**
confidence: verified
---
