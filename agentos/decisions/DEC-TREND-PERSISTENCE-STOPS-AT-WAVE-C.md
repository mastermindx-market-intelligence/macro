---
key: TREND-PERSISTENCE-STOPS-AT-WAVE-C
question: >
  After the pre-registered Wave C development pass (C1, group persistence across the eleven
  GICS sectors), does any cell carry into the frozen C2 confirmation read, and does the
  trend-persistence family continue past Wave C?
answer: >
  No. The one C1 development run returned its null branch (C1-NULL): three cells were scored
  and none met the five carry conditions, so no cell carries, no n_read exists, no constants
  block was written and the C2 confirmation read is never made. The family stops at Wave C for
  the eleven-sector, as-of-now-labelled constructions of the C1 document's section 4 on this
  universe and these horizons. Nothing is built.
rationale: >
  The decision rule was fixed in research/TREND_PERSISTENCE_PREREG_C1.md section 8 before the
  run and the instrument applied it mechanically. Against the gating baseline B* (a member's own
  trailing returns and volatility in detail), the six surviving group features move the
  rank-linear fit of relative-to-SPY forward return by -0.0024 at 20 sessions (one-sided p 0.67,
  1 of 5 date blocks positive, n 192 formation dates) and +0.0019 at 60 sessions (p 0.32, 3 of
  5 blocks, n 184). The interaction cell adds -0.0009 at 20 sessions (p 0.91). Against the plain
  baseline B the same features read +0.0085 and +0.0232, and against zero +0.0062 and +0.0249
  (p 0.30 and 0.087), so whatever group information the features carry is already contained in
  a member's own trailing returns and volatility, which the design does not credit as group
  persistence. Every leave-one-sector-out fold shares the sign of the full-panel mean, so no
  single sector hides a carry. The B2 reproduction gate passed before scoring (both committed
  means reproduced to 1e-9), the run was made exactly once from the committed clean tree at
  Mastermind master 1644ace945a8, and the attempt record is public in research/data/.
alternatives:
  - option: Make the frozen C2 confirmation read anyway on formation dates after the freeze
    why_not: >
      Section 8 gives a C2 read only to a carried cell; with nothing carried there is no
      hypothesis to confirm, and a read on post-freeze dates without one would be a new claim
      made without a pre-registration.
  - option: Carry the 60-session cell on the strength of its positive mean and 3 of 5 positive blocks
    why_not: >
      It fails conditions i (mean below the pre-set bar), ii (p 0.32 against the pre-set level)
      and v (the leave-one-sector-out folds are not all positive). Carrying a cell that fails
      three of five conditions is moving the bar after seeing the result.
  - option: Relabel the 343 unlabelled names by ticker string and run the development pass again
    why_not: >
      Ticker-string labels on leavers were shown to be recycled tickers (C-0 handoff), the
      instrument's one-run guard and the public attempt record make the run single, and a second
      development run would be a fourth claim on formation dates already scored by V2, B2 and C1.
  - option: Test GICS industry-group or industry, basket or dynamic-theme constructions on the same dates now
    why_not: >
      Those constructions are untested and are not closed by this record, but formation dates
      2022-07-06 to 2026-06-02 have now been scored three times. Any new construction needs its
      own pre-registration first, written as a new document, never as an edit of the C1 text.
evidence:
  - "Mastermind PR 1230 (instrument research/trend_persistence_group.py plus 18 tests), squash-merged as 1644ace945a8"
  - "Mastermind PR 1252 (results), head c553e5a23ef25a70d3cf9f8ee6fb446b334747c3, squash-merged as 7eac3ec252475600147ec9a376b8ca16403ac4c5"
  - "Mastermind research/data/trend_persistence_c1_result.json - decision.outcome == C1-NULL, decision.carried == [], power.n_read == null; sha256 bcc1e259b83e319e39714f9cc84abc29cfbc43be10a8cd0ea90242a1f1533ccc"
  - "Mastermind research/data/trend_persistence_c1_attempt.json - one attempt, started 2026-10-05T00:06:21Z at git_head 1644ace945a8, retry_reason null; sha256 22137f608a01cf2d19801b8398d68557d6a5d822c505197d9bbb5e35e7fb949f"
  - "Pins carried in the result: prereg f22b0cee218c381dd3fd078d67301c985eb9415faa0e75ffdc57d520374bf4cc, B2 result e0b177cb51dececc173e67817e76356f201d498626022440487cce0a3a2ba443, sector snapshot cba7fc07da53a6230122fec5797b15163bbe3b31f78918839f5722e885c00de3 (macro data/breadth/sp1500_pit_sectors.parquet, label_asof 2026-10-04, era_correct False on every row)"
  - "Run log: python3 research/trend_persistence_group.py run exited 0 after 80 s; the log's decision line reads the section 8 null wording verbatim"
  - "python3.12 -m pytest tests/test_trend_persistence_group.py tests/test_ceo_submit_armed_composition.py::test_d8_template_topology_and_protected_defaults -q at c553e5a2: 19 passed"
affects: [WS:TREND-PERSISTENCE, "Mastermind research/trend_persistence_group.py", "Mastermind research/data/trend_persistence_c1_*.json", "Mastermind research/TREND_PERSISTENCE_PREREG_C1.md", "data/breadth/sp1500_pit_sectors.parquet"]
confidence: high
reversibility: easy
decided_by: coo-fable (session 3b488a7c), applying the pre-registered rule
decided_at: 2026-10-05
---

The null closes the eleven-sector, as-of-now-labelled group-persistence constructions of the
C1 document on the S&P 1500 point-in-time universe at 20 and 60 sessions. It does not close
the idea: industry-group or industry, basket and dynamic-theme constructions were not tested,
and the labels are as-of-now (a reclassified company carries its current sector), so a
licensed membership-era label could in principle change the panel. The result says that what
a sector's members do together, measured these seven ways, adds nothing material to what each
member's own trailing return and volatility already say about its next 20 or 60 sessions
relative to SPY. The family has now produced three pre-registered nulls (Wave B, B2, C1) on
the same formation dates; those dates carry no further claim.
