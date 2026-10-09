# Session 2 cumulative-window contract

Scope: production-inert extension of the existing research reference, on the same PR/branch. No blocked source reads, benchmark edits, fresh-main comparison, source activation or market outcomes. Direct execution rationale: LOWER_TOTAL_OVERHEAD for a bounded continuation of the owned reference; no worker is displaced.

`window_pressure.measure_windows(bars, memberships, segments, *, start_utc_s, end_utc_s, cutoff_utc_s, config, mode="as_observed")` consumes the existing Bar/Membership/Segment types. The caller still owns identity, calendar, rights, basis and revision qualification. The reducer computes BVC once at the explicit cutoff, then joins security-minute observations to many factors. It never signs precomputed later-cutoff values as earlier knowledge.

The supplied contiguous same-session calendar segments must cover the exact half-open window. Expected cells are members times scheduled minute slots; absent rows are missing, never inferred zero. Explicit zero-volume rows remain zero. All known gross survives even when direction is unavailable. Full-window estimated net requires all expected rows and a numeric estimate in each; policy-neutral gross stays separate from directionally usable gross. Numeric completeness is not accuracy.

Baseline references use the existing MatchKey/Reference, with an identity binding actual sorted membership, mode, estimator, monetary basis, calendar reference and ET anchor/phase shape. Absolute session date does not enter the matching identity. References are absent for incomplete windows or corrected-history mode. All contributing history availability is carried conservatively; it is not independently authenticated by this reducer. No benchmark/market data is invented.

Test-first steps: establish missing-function failures; implement reducer; prove complete/missing/neutral/window/basis/cutoff boundaries; prove split sessions, overlapping union and deterministic replay; then exercise native BVC -> window -> baseline on explicit fabricated prior-session fixtures. Preserve prior source and tests unchanged. Evidence is scoped fixture proof, not market admission or whole-repository CI.
