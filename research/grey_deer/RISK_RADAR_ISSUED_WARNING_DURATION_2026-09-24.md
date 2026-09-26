# Risk Radar Issued Warning Duration — 2026-09-24

## Capability delta

Before, Risk Radar could show today's settled state, trajectory, evidence depth and
source disagreement, but it did not tell the user whether a caution-or-higher reading
was a one-session blip or had persisted across issued sessions.

After this slice, the existing settled Risk Envelope builder reads the incumbent US
Risk Radar forward ledger and carries one **display-only duration fact** into the
existing Risk Radar / Market internals surface.

When the current settled Radar state has been caution, elevated or risk-off for at
least five consecutive **issued NYSE sessions**, the existing metadata row adds:

`Risk pressure · N issued sessions · since YYYY-MM-DD`

with a Chinese twin. There is no new card, badge, alert, score, probability or policy.

## Research law

This implements the already-accepted display result:

- `research/grey_deer/RISK_RADAR_CAUTION_PERSISTENCE_PREREG_2026-09-21.md`
- `research/grey_deer/RISK_RADAR_CAUTION_PERSISTENCE_RESULTS_2026-09-21.md`

The five-session floor was frozen as one trading week before outcome inspection.
Corrected research found the condition useful as duration context but far too common
to become a prominent warning. This implementation therefore does not add predictive
language or alter any live state-machine threshold.

## Issued-only construction

Source: `data/risk_radar/forward_log.jsonl`, the incumbent keep-FIRST forward ledger.

A duration claim is admitted only when:

1. the settled Market State session has exactly one matching issued Radar row;
2. that row's state matches the settled Radar state;
3. every session in the backward run is an expected NYSE session with an issued row;
4. every row in the run is caution, elevated or risk-off.

A missing expected session breaks the streak. Duplicate/invalid rows or a state
mismatch fail closed to no duration claim. Weekends/NYSE holidays do not break a run.

Calm/watch carry an internal zero-duration fact and render no persistence copy.

This is actual issued-state duration, not a reconstructed historical replay and not a
prospective validation cohort.

## Architecture

The pure `engine/risk_envelope.py` composer is unchanged. No schema bump is required:
the fact rides in the existing `risk-radar-us` source-native `detail` object under
`mastermind.risk_envelope/v1`.

The live provisional Risk Envelope builder is unchanged and receives no duration
keyword, so live polling cannot create or extend the settled issued-duration fact.

## Verification

- focused ledger-duration tests: 5 passed;
- focused Radar duration rendering tests: 3 passed;
- full `tests/test_risk_envelope.py`: 61 passed, 2 skipped;
- full `tests/test_live_risk_envelope.py`: 45 passed;
- full `tests/test_risk_envelope_radar_integration.py`: 52 passed;
- full `tests/test_macro_risk_dialog.py`: 12 passed;
- Python compile: pass;
- `git diff --check`: pass.

Current committed ledger probe at implementation time:
- 53 issued rows;
- latest row: 2026-09-23, state `calm`;
- derived duration: 0 sessions / not persistent.

That probe is expected to render no duration line today. The feature becomes visible
only on a future genuinely issued five-session caution+ run.

## Authority ceiling

This slice changes no Risk Radar score, state, odds, gate, calibration, review law,
ranking, sizing, capital policy, forward-ledger writer, or live overlay. It does not
claim that a persistent reading is more likely to predict a drawdown. It only tells
the user how long the already-issued risk pressure has lasted.
