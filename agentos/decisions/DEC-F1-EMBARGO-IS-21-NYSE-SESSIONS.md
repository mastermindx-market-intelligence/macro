---
key: F1-EMBARGO-IS-21-NYSE-SESSIONS
question: >
  What purge must the F1 entry-vs-management out-of-sample evaluation apply between the
  training episodes and each test week so that no training label is realised inside the
  test window?
answer: >
  A training episode is kept only if its h21 label is realised STRICTLY BEFORE the test
  week starts: np.busday_offset(as_of, 21, roll="forward", holidays=<NYSE holiday
  calendar>) < week_start, equivalently as_of <= np.busday_offset(week_start, -22,
  roll="backward", holidays=<NYSE>). The embargo is the twenty-one TRADING-session
  horizon of the h21 label with a strict inequality, never a calendar-day count. The
  round-0 constant of 22 calendar days (about 15-16 sessions) let training labels
  realise after every test week's start; the round-1 literal "-21 sessions" let 138
  training rows (24 / 31 / 40 / 43 per fold) realise their label at the test Monday's
  close. The 22-calendar-day AUC is retained as a labelled sensitivity row.
rationale: >
  The label is an h21 excess return: it is realised 21 sessions after as_of. A purge
  stated in calendar days is shorter than the label by one to two weeks and shifts with
  holidays, so the OOS AUC of round 0 (0.5434) was computed with leakage in every fold.
  The round-0 Opus review (finding 1, run.py:38 and :544-545) also showed the purge
  pytest was circular (test_f1.py:26-58 re-derived the fold from the same constant).
  The round-1 Opus review (defect D6) showed that the literal -21 offset satisfies the
  session count but not the spec's "strictly before" intent for rows on the boundary,
  and that the round-1 purge test still could not fail (two forward-peek mutants passed).
  Stating the rule as the label-realisation comparison removes the off-by-one and gives
  the test one comparator to assert.
alternatives:
  - option: "Keep 22 calendar days and describe it as an approximate embargo"
    why_not: "It leaks by construction; an approximate purge is not a purge."
  - option: "Use 30 calendar days for margin"
    why_not: >
      Calendar days are the wrong clock for a session-horizon label; holidays move the
      true boundary, and the extra margin discards training weeks without reason.
  - option: "Keep the literal -21 session offset"
    why_not: >
      It keeps rows whose label is realised at the close of the test week's first
      session; the spec asks for labels realised strictly before the test window.
evidence:
  - "results/F1/code/run.py:38 and :544-545 (round-0 constant); test_f1.py:26-58 (circular purge test)"
  - "round-1: run.py:39 and :435-440 (np.busday_offset -21, NYSE holidays from lib/nyse_calendar); 138 boundary rows measured by the round-1 Opus review (defect D6); forward-peek mutants m_peek and m_peek_rec passed all round-1 tests (defect D1)"
  - "Opus reviews of F1 round 0 (findings 1-2) and round 1 (defects D1, D6)"
  - "scratch packets pkts/F1_r1.txt (SPEC AMENDMENT) and pkts/F1_r2.txt (SEAT RULING on the boundary)"
affects:
  - "WS:PROPHET-REGIME-TIMEFRAME-RESEARCH"
  - "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/F1/**"
confidence: high
reversibility: easy
decided_by: "coo-fable seat (Claude Code session f273dd7d), ruling on the Opus reviewers' findings"
decided_at: 2026-10-04
---

# F1 purge is the 21-session label horizon, strictly before the test week

The MIXED verdict of round 0 was robust to the leak (MANAGEMENT needed a deteriorated
share above 0.50 against 0.148 observed; SELECTION needed AUC >= 0.65, reached in 1.4%
of bootstrap draws in round 0 and 7.4% in round 1). The primary AUC is re-reported under
the strict boundary in round 2; the round-0 calendar-day number survives only as a
sensitivity row, and the round-1 literal-offset number is reported beside the round-2
value so the boundary's effect is visible.
