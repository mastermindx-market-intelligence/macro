# Historical regime input windows: source-basis repair

Operation: `regime-window-basis-20261002-astra-001`.
Parent: existing #7088 / WS:RATES-INFLATION-COMMAND.
Source base: Macro `b4f95f98ef80b8cbb4636afbd723b5091658e1f1`.
Protected procedure: Mastermind `bdf2a972e68a70270c24d4b5d61a4d60edc4f288`,
compatible Skillpack 1.0.1, bootstrap major 1. SESSION_RELIABILITY not enrolled.

## Capability and limits

The existing history builder now distinguishes current-source coverage from the
source basis of the actual inputs to a slow component. This is an additive
explanation on the existing historical Parquet and divergence sidecar, not a
new regime engine, history store, collector, forecast, risk rule or scheduler.
The live axes, feature builder, scoring, hysteresis and transition math are unchanged.
The existing `pit_class` and `fallback_notes` are preserved verbatim.

An older current-value `pit_vintage` label can coexist with a trend that depends
on revised pre-coverage values. A synthetic actual-owner discriminator keeps the
current payroll value at 100, changes only its pre-coverage history from 50 to
150, and flips the actual payroll trend from +1 to -1. Legacy `pit_class` stays
`pit_vintage`; the new input-window basis identifies the revised dependency.

## Exact scope

The diagnostic consumes the same aligned raw features and component-active masks
already used by `build_frames`. It adds:

- `macro_window_basis`: initial_vintage_inputs, revised_fallback_inputs,
  unknown_inputs, or no_active_macro_components.
- `macro_window_revised_legs` and `macro_window_unknown_legs`: explicit leg names.
- `macro_window_active_count`: observed active slow-component count.

The existing divergence JSON gains `macro_window_provenance`, including per-leg
counts, dependency definitions and explicit false qualification flags. The existing
CLI serializes both outputs and prints the new basis counts and their limits.
The existing source registry documents the additive columns. No production data
is regenerated or committed by this source change.

## Dependency semantics

The four plain differences depend on their actual endpoints, not every intermediate
row: payrolls 63, industrial production 252, WEI 65, GDPNow 63 aligned feature rows.
Sticky CPI compares two 63-row rolling means separated by 63 rows, each requiring
at least 21 non-null inputs. Only actual non-null contributors count; missing inputs
are not revised observations and do not justify a universal fixed embargo.

The dependency description is metadata within the existing builder. A regression
checks it against the actual monthly_sign call arguments in engine/axes.py and
the actual rolling mean in engine/inputs.py. A future owner-window change must
update this metadata and its tests; no second scoring implementation is introduced.
Offsets are business-day feature-grid rows, not calendar months or exchange sessions.

An absent component activity series or coverage key is unknown. Explicit None
coverage means the builder has no vintage source and uses latest-revised fallback.
Inactive components cannot manufacture a positive vintage-support claim. Active
components with insufficient/nonfinite endpoint support remain unknown. The output
keeps unavailable and revised causes separate instead of silently dropping them.

## What this does not certify

Even `initial_vintage_inputs` is not complete historical as-of information. The
existing input stream retains initial releases, not every subsequent vintage or
intra-quarter update. Source-region and transformation support do not prove market
input availability, the state machine's full history, model fitting cutoffs, or
actual historical issuance. All corresponding qualification flags remain false.
No regime-conditional efficacy, allocation, timing edge or predictive improvement
is claimed. The richer history/forecast work in #7015/#7165/#8133 remains separately
owned, and the production-capture denial is not retried or weakened.

## Tests and actual-source diagnostic

Sixteen discriminators failed on the original source before implementation. The
new suite exercises all lag boundaries, sticky-CPI rolling/minimum support, absent
and malformed inputs, no-active states, prefix invariance, unchanged source arrays,
actual-owner score sensitivity, dependency binding and existing code-gate ownership.

The synthetic integration runs the actual feature alignment, axes, classifier,
flags, state machine, builder and CLI writers. Only source transport is synthetic.
It verifies numerical history and legacy basis parity, then reads both newly saved
Parquet/JSON outputs back. It does not replace the existing real-store tests.

The related history and seasonality campaign passed 85 tests, with 12 existing
full-store skips and 239 warnings (inherited pandas fragmentation and host temporary
cleanup). The skips remain explicit; this is not a full-store build or full CI pass.
Three in-memory forbidden mutations were killed: current-only endpoints (five
failures), discarded smoothing (one), disconnected serialized consumer (two).
No source file was modified by the mutation processes.

A separate saved-source diagnostic uses exact Git bytes: five economic source
series, their initial-vintage table, and SPY close solely to establish the feature
grid. All other source reads are absent. On this reduced input panel, 8,785 rows
span 1993-01-29 through 2026-10-01. There are 65 rows from 2020-04-21 through
2020-07-20 where legacy current-value `pit_vintage` coexists with a revised slow
input window. This is not the full market regime output or an investment outcome.
The prefix comparison is identical, and the source-basis pass took about 0.017
seconds in this single local measurement. Input hashes and full aggregate counts
are retained in the sibling evidence JSON; no raw vendor payload is republished.

## Integration and continuation

The formerly grandfathered `tests/test_regime_v2_pit.py` is added to the existing
`unrun-scoring-engine` code job, with one baseline removal and no new job/exemption.
#8301 adds a different suite at the same CI owner; compose both without dropping
either. #8303 retains its Prophet research namespace and may consume this richer
basis only after its own qualification. #7871 already owns the INDPRO/NEWORDER/
ISRATIO full-vintage collector extension; do not duplicate it or copy credentials.

Direct work is justified by the exact pre-effect worker limitation and the compact
repair of the source defect already reproduced in this mission. No Executive Job,
reviewer START, provider invocation or autonomous watcher is claimed. Review and
release remain held until independent exact-source review, repository checks and
current-base integration are complete. The parent mission remains incomplete.

Prepublication composition found the two test additions competing at the same
CI insertion point. This candidate moves only its own step earlier in the same
existing code job; the frozen #8301 source is untouched. No test or gate is removed.
