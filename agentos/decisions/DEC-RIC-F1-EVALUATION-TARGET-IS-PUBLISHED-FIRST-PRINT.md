---
key: RIC-F1-EVALUATION-TARGET-IS-PUBLISHED-FIRST-PRINT
question: >
  What may the Release Radar track record show about inherited release-forecast accuracy, given that the
  scored history mixes legacy cross-vintage proxy targets with official first prints and no release yet has
  twelve clean first-print scores?
answer: >
  The evaluation target is the official published first print (actual basis official_published_metric) under
  one target epoch. A release reaches display only when every clean score is first-print matched under a single
  epoch, at least 12 scores exist, and the prospective-accrual owner (E1) supplies a valid two-number MAE
  interval; without that interval the state is interval_pending and the error stays hidden. Shown errors carry
  their interval and read "Early, n = k" below 24 scores and "n = k, verdict pending" from 24. Legacy
  cross-vintage and mixed-target scores stay readable as counts but never show an error. accuracy_claim stays
  withheld.
rationale: >
  The previous scoreboard printed an MAE over mixed legacy cross-vintage targets, so the number described no
  single forecastable quantity (A04, A11). E0 §5 allows a forward MAE from 12 episodes only with its CI and the
  "early, n = k" label, and reserves the verdict for 24 post-freeze episodes. The producer cannot compute that
  interval honestly from retrospective rows, so it fails closed until E1 supplies it. Today no release has 12
  clean first-print scores, so every live row shows a count and a state, never an error.
alternatives:
  - option: Show the MAE from 12 scores without an interval, labelled "reference only".
    why_not: >
      Contradicts E0 §5 (CI required with any displayed forward MAE) and invites readers to treat a point
      estimate over a dozen episodes as a measured accuracy.
  - option: Compute a bootstrap interval inside build_release_forecast.py now.
    why_not: >
      E0 assigns the prospective display and its interval to E1; computing it here would create a second
      evaluation owner and could run over pre-freeze rows that E0 says can never promote.
  - option: Keep the legacy cross-vintage MAE visible with a footnote.
    why_not: >
      The target is incoherent across rows, so no footnote makes the number a measurement of first-print error.
evidence:
  - "scripts/build_release_forecast.py _track_record_summary: display states no_clean_scores, benchmark_only, proxy_or_mixed_target, accruing, interval_pending, display_only; TRACK_RECORD_DISPLAY_MIN_N = 12, TRACK_RECORD_VERDICT_MIN_N = 24, FIRST_PRINT_ACTUAL_BASIS = official_published_metric"
  - "templates/dashboard.html.j2 rrTrackRecordBlock / rrTrackRecordLine / rrTrackMissCi / rrTrackEarly (EN/ZH)"
  - "tests/test_release_forecast_producer.py test_track_record_never_shows_mae_without_its_interval and the parametrized display-state cases; tests/test_release_radar_ui.py track-record tests (wired into CI in the same change)"
  - "research/rates_inflation_command/seat_20261014/E0_RESEARCH_PROTOCOL.md §5 (merged #9212)"
  - "DEC:RIC-E0-RETROSPECTIVE-FALSIFIES-PROSPECTIVE-PROMOTES"
affects:
  - WS:RATES-INFLATION-COMMAND
  - scripts/build_release_forecast.py
  - templates/dashboard.html.j2
  - site/macro.html
confidence: high
reversibility: easy
decided_by: fc3dfe4b-8c15-4c7b-ab42-5741f284f47b
decided_at: 2026-10-14
---

## Context

Rates & Inflation e2e completion programme, Chairman masterplan 2026-10-13, task-graph row F1 (acceptance
cases A04, A08, A11). F1 replaces the fabricated scoreboard MAE on the Release Radar with a first-print track
record. The interval and the prospective accrual belong to E1, which executes the frozen E0 protocol; when E1
publishes `mae_ours_ci` for a release with 12 or more clean first-print scores, the radar shows the error with
no further change here.
