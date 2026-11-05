---
key: TREND-PERSISTENCE-STOPS-AT-WAVE-B
question: >
  After the pre-registered walk-forward comparison (Wave B2), does the trend-persistence
  path-shape family advance to a calibrated profile, a shadow snapshot or an advisory field
  in Mastermind?
answer: >
  No. The family stops at Wave B for these constructions. Nothing is built. The path
  features stay available as descriptive fields, and Waves C to F are not entered.
rationale: >
  The decision rule was fixed in the B2 pre-registration (section 8) before the run, and the
  one run returned its null branch. Added to a model of trailing returns, beta and volatility
  in detail, the features behind the 29 confirmed tests raise out-of-sample rank correlation
  with forward maximum drawdown by 0.0013 at 20 sessions and 0.0017 at 60, on a base of 0.49
  and 0.53. The tenth of stocks the model rates most at risk catches no more of the deepest
  drawdowns: +0.00 and -0.14 points of capture against a pre-set bar of 1.0. Neither gated
  horizon passes the value gates. A profile built on these features would not catch more
  drawdowns than the baseline it was compared with, so building one would add a field with
  no measured use.
alternatives:
  - option: Build a shadow advisory profile anyway, on the strength of the 29 of 29 holdout confirmations
    why_not: >
      A simulated market with only volatility passes the same holdout gates on 14 to 29 of
      the 29 tests, so the confirmations do not show anything beyond volatility, and the
      walk-forward comparison then measured the increment directly and found it immaterial.
  - option: Read the 20-session result under V2's older significance rule, where the first value gate passes
    why_not: >
      That lands in the pre-registered "detectable and immaterial" branch, which also builds
      nothing and stops the family. The older rule rejects a true zero about twice as often
      as stated on overlapping labels (fifth review).
  - option: Change the gates or the baseline and score the same dates again
    why_not: >
      Formation dates 2022-07-06 to 2026-06-02 have been scored twice. Moving the bar after
      seeing the result is not a test. A new claim needs later dates and a new pre-registration.
  - option: Promote the three distance-from-high tests labelled beyond simulated volatility
    why_not: >
      They are one overlapping family at about 0.01 rank correlation, the comparison is with
      two simulated markets only, and by the pre-registered rule the label carries nothing
      once the value question fails.
evidence:
  - "Mastermind PR 1155, squash-merged as 1c5bc0c3a978"
  - "Mastermind research/data/trend_persistence_b2_result.json — decision.outcome == no_model_value, decision.family_stops_at_wave_b == true; sha256 e0b177cb51dececc173e67817e76356f201d498626022440487cce0a3a2ba443"
  - "Mastermind research/data/trend_persistence_b2_attempt.json — one attempt, 2026-10-03T12:47:29Z, no retry; announced beforehand in PR comment 5969307706 (12:47:13Z)"
  - "Mastermind research/TREND_PERSISTENCE_READOUT.md section 11 (result) and section 4 (eight independent read-only reviews; the seventh recomputed every printed number, the gates and the decision from the committed result; the eighth confirmed a later re-serialization of the reference file changed no value)"
  - "Mastermind tests/test_trend_persistence_walkforward.py::test_the_committed_result_was_produced_once_under_the_pinned_files"
affects: [WS:TREND-PERSISTENCE, "Mastermind brain/trend_persistence.py", "Mastermind research/trend_persistence_*.py"]
confidence: high
reversibility: easy
decided_by: coo-fable (session 44653691), applying the pre-registered rule
decided_at: 2026-10-03
---

The null closes these 29 tests on this universe. It does not close the idea: other
constructions and sector or group persistence were not tested. The baseline model removes part
of what the features measure by construction (distance from the high and trailing drawdown are
close relatives of trailing return and volatility), so the result says the features add
nothing material to what is already cheap to know, not that they carry nothing.
