---
key: CANONICAL-SESSION-GRID-CHANGES-BAR-COUNT
claim: >
  The canonical 2D/3D session grid changes the bar COUNT, not only the bar keys, because
  `open(0)` is unconditional: row 0 always opens a bucket even when its global session index
  is not a multiple of the grid. A truncated feed therefore always carries a PARTIAL leading
  bar, and a daily fixture sized to divide evenly by the multiple gains exactly one bar
  relative to the old feed-start `floor(i / mult)` grouping. Measured 2026-09-29 on the live
  document `https://app.mastermind-x.com/data/NVDA.json` (n=6963 sessions, 1999-01-22 ->
  2026-09-28, anchor 0): the old rule yields 2321 3D candles, the canonical grid yields 2322,
  and 0 of 2321 same-index bar keys match. Independently reproduced by TERMINAL-02 against the
  shipped `terminal/lib/sessionBars.ts` on a 261-session fixture: 88 buckets, not 87, with
  bucket 0 holding one session alone. The append condition is N = 1 (mod 3): at N=261 the
  next session COMPLETES a 2-of-3 tail and appends nothing, while at N=262 it opens a new
  bucket. A second, opposite-direction consequence: extending history BACKWARDS legitimately
  destroys exactly one bar boundary — the forced first bucket — because once real history
  precedes it, that row is no longer row 0 and its global index does not open a bar on its
  own. Every genuinely-phased bar (global G = 1 mod 3) keeps its phase.
falsifier: >
  A feed of N sessions at any anchor whose canonical bucket count equals ceil(N / mult) with
  no leading partial bucket; or a backfill after which `set(opens_before) == set(opens_after)`
  rather than differing by exactly the pre-backfill row-0 date. Check with
  `signal_layer/confluence.py::_3d_groups(close, anchor)` directly, comparing the first
  returned opening date to the feed's first session. A count that merely differs from the old
  grouping does NOT falsify this — the claim is specifically that the difference is +1 and
  that it comes from the leading partial.
so_what: >
  Any test, fixture, or downstream consumer that sizes a daily series to divide evenly by 2
  or 3 and asserts `count == N / mult` is latently wrong and fails by off-by-one, which reads
  as an indexing bug rather than a grouping change. Two specs in mastermind-terminal #773 hit
  exactly this. Resize the fixture and re-derive the tail rather than correcting the constant:
  deriving the expected count from `groupSessionBars` makes the assertion tautological and
  silently drops whatever the spec was actually covering. Equally important and easy to miss —
  APPENDING a session is safe for the grid, PREPENDING is not, so a fixture helper that walks
  backward from a fixed last session (as #773's `sessionDates` does) re-phases every interior
  boundary date when its size is raised. Assert bar keys by time, never by position; a
  position-indexed cross-check drifts by one against a key-indexed one.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  Live public-edge document fetched and both grids computed in one pass (old `floor(i/3)` vs
  canonical `open(0)=true, open(i) = (i-1+anchor) % 3 == 0`), reporting 2321 vs 2322 and
  0/2321 same-index key matches. Backfill direction verified against
  `signal_layer/confluence.py::_3d_groups` on a 60-session business-day calendar: a feed
  truncated at global 20 yields 9 opening dates; prepending 12 sessions yields 13, and the
  set difference is exactly {2024-01-29} — global index 20, where 20 % 3 == 2. Pinned by
  `tests/test_session_anchor.py::test_the_anchor_survives_the_nightly_appending_and_backfilling_history`
  in mastermind-terminal, which is red under three separate mutations of the contract
  (write-once stamp, index forced to row 0, `date` dropped). The 261-vs-262 arithmetic was
  derived independently by TERMINAL-02 from the rule and cross-checked against a live trial
  merge of the shipped code.
scope:
  - mastermind-terminal
  - terminal/lib/sessionBars.ts
  - signal_layer/confluence.py
  - any daily-series fixture or bar-count assertion
confidence: verified
---

The reason this is worth a record rather than a comment is that the count change is invisible
in the place you would look for it. The keys all move, which is loud and expected from the
repair; the count moving by one is quiet, arrives in a different file, and looks like an
ordinary off-by-one to whoever meets it. Both halves come from the same unconditional
`open(0)`, and neither is reconstructable from a diff of the grouping function alone.

Related: DEC-CANONICAL-SESSION-BAR-IDENTITY,
DSC-CHART-3D-GRID-DISAGREED-WITH-ENGINE-ON-EVERY-BAR.
