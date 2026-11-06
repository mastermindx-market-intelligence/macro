# Rates Direction prospective evidence ledger — 2026-09-24

Operation: `rates-direction-prospective-ledger-20260924-sol-004`.
Parent: `WS:RATES-INFLATION-COMMAND`.
Stacked dependency: Macro PR #7923 exact base `dbf8d03ed4f2a29ea349bb37a23b9048f18bc2db`.
Source carrier: Draft/HOLD Macro PR #7940, initial implementation commit `6791be6e01bfc608217a8ff3972d09ec6c50e422`.

## Capability

Before this slice, `data/rates_command/forward_log.jsonl` froze only coarse RIC
flags plus the legacy rolling 12-month path/gap. The newly measured
`policy_path_repricing` block from #7923 would be visible in `latest.json` but
would not survive as first-known prospective evidence.

This slice extends the incumbent nightly keep-FIRST row with the exact
`artifact["policy_path_repricing"]` object. It does not recompute, score,
normalize or reinterpret that object. A later rebuild on the same
`asof_night` is skipped by the pre-existing keep-FIRST law, so corrections cannot
rewrite the first nightly measurement.

No second ledger, archive, scheduler, forecast model, trial family, score, rank,
size, gate or trade authority is created.

## Evidence boundary

The source measurement still inherits every #7923 limitation: provider daily
Close is not authenticated exchange settlement; matched-contract movement includes
fixings and risk premia; historical availability is not certified; same-day bars
can be withheld; and the block is measurement context rather than a directional
forecast.

Prospective evidence starts only after the source dependency is accepted, released,
the nightly builder runs on the real store, and an actual row is read back from the
production path. Tests do not advance that clock.

## RED -> GREEN

Pre-repair regression:
`TestForwardLogLane::test_forward_log_freezes_policy_repricing_measurement_keep_first`
failed with `KeyError: 'policy_path_repricing'` because the incumbent row dropped
the new measurement.

Repair: add exactly one additive field to the existing stamp:
`policy_path_repricing = artifact.get("policy_path_repricing")`.

Verification:
- targeted regression: 1 passed;
- `tests/test_rates_command.py tests/test_fed_path.py tests/test_yield_momentum.py`:
  148 passed, 301 warnings;
- no model fit, outcome read, vendor request, production data write or empirical trial.

## Dependency / release law

This branch is intentionally stacked on #7923, not a replacement for it. #7923
still requires independent non-author source/financial-semantics review and normal
release proof. This slice must not be promoted ahead of that dependency. After
both sources are accepted, production proof is one real nightly
RIC input -> latest artifact -> keep-FIRST forward row -> readback showing the
same source digests/observation dates and authority=false measurement block.
