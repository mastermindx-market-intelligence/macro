# Risk Radar Prospective Probability Identity — 2026-09-23

## Capability delta

Before, the existing US Risk Radar forward ledger stored the issued state,
probabilities, receipt clock, and realized outcomes, but historical rows could
not prove which exact model implementation/calibration produced them. The
scorecard therefore correctly marked publication timing and current-model
validation false.

After this slice, **new nightly rows on the same forward ledger** carry a
`forecast_issue` receipt with:

- `risk_radar_forward_issue.v1` contract;
- prospective epoch;
- exact ledger `issued_at` equal to the first-write `logged_at`;
- nightly + first-writer-wins custody;
- `engine/risk_radar.py` SHA-256 for direct debugging;
- a source-bundle SHA-256 over `engine/risk_radar.py`,
  `engine/indicators.py`, `lib/nyse_calendar.py`, `lib/store.py`, and
  `lib/config.py`;
- effective calibration SHA-256;
- canonical model fingerprint over source bundle + calibration identity.

The existing scorecard gains an additive `probability_audit.prospective` block
that selects only the latest exact epoch+fingerprint cohort. Old model rows are
reported separately and never blended into the current cohort.

## Honesty boundary

This establishes **forward-ledger issue timing**, not public-page first
publication. The legacy top-level audit remains descriptive and keeps
`publication_timing_verified=false` and `current_model_validated=false`.

The prospective block also keeps `current_model_validated=false` regardless of
row count or event mix. A future validation claim requires a separate accepted
promotion protocol.

Historical rows without the new receipt remain historical. They are never
backfilled from today's code, calibration, git history, or inferred timestamps.

## Failure behavior

Model identity is deliberately conservative: any byte change in the declared
probability/state source bundle rotates the source-bundle hash, and any effective
calibration overlay change rotates the calibration hash. This may split cohorts
more often than a hand-curated semantic version, but cannot silently mix different
implementations when shared signal/calendar/store helpers change.

If identity generation fails, the incumbent ledger row still writes so risk
accountability is not interrupted; that row simply cannot enter the prospective
cohort.

## Verification

- prospective writer/fingerprint/idempotency tests: 4 focused tests passed;
- prospective scorecard cohort/timing/roundtrip tests: 6 focused tests passed;
- full `tests/test_risk_radar_audit.py`: 10 passed;
- full `tests/test_risk_radar_scorecard.py`: 74 passed;
- card/lane/ledger compatibility suites: 47 passed;
- Python compile and `git diff --check`: pass.

No second ledger, scheduler, grader, calibration writer, probability change,
state/gate change, policy change, sizing change, ranking change, or capital
authority was created.
