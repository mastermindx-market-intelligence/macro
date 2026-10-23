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

## 2026-10-03 repair (lane `claude/gri-8304-window-basis-repair-20261003`)

Five independent reviews of the candidate agreed on the same repair surface;
this section is a dated correction, not a rewrite of the history above.
The two review-pass rounds also landed F2 (source de-duplication), F6
(tz-aware source index) and F7 (bool/int/float coverage values).

- **Per-value provenance (W2).** The `revised` label is now decided from the
  per-value source date — the last index date at which the un-forward-filled
  leg series had a finite observation, carried forward the same way the value
  is. A forward-filled post-coverage row whose supplying observation
  pre-dates `first` is therefore still `revised_fallback_inputs`, never
  `initial_vintage_inputs`. A NaN initial-vintage value never upgrades a
  label. The function accepts a new keyword-only `sources=` argument; in
  `build_frames` it is the `overrides` dict (the merged live + panel
  series). When `sources` is None, or lacks a leg, that leg's per-value
  source date is UNKNOWN and every row that depends on it resolves to
  `unknown_inputs` — the forward-filled feature column is never used as
  its own source, because without the un-filled series the function
  cannot tell an observed value from one carried forward from before
  coverage. Synthetic test (a) — sparse source, pre-coverage ffill into
  the first N post-coverage rows — labels the window
  `revised_fallback_inputs` and was RED before the fix (`row 163 expected
  revised_fallback_inputs, got initial_vintage_inputs`) and GREEN after.
  Test (b) confirms a normal leg with finite initial values is unchanged.
  Test (c) discriminates: with finite leg columns and NO source supplied,
  every row is `unknown_inputs`; with `sources={"payrolls": ...}`, the
  lag window resolves per-value.
- **Source de-duplication (F2).** A duplicate stamp in the source index
  keeps the LAST row, matching `engine/inputs.put()`'s forward-fill rule,
  BEFORE the dropna pass — so a finite-then-NaN duplicate at the same
  stamp does not resurrect an earlier observation as the per-value source
  date. Test: a duplicate (5.0 then NaN) at `first` with a pre-coverage
  value forward-filled; row 163 (lag window fully post-coverage) is
  `revised_fallback_inputs`, not `initial_vintage_inputs`. RED first at
  cfe9a249 (no-dedup mutant returns `initial_vintage_inputs`).
- **Source-index timezone handling (F6).** A tz-aware source index is
  normalised to naive UTC before comparison; if any step raises, the leg
  is UNKNOWN and never escapes as an exception. Two tests cover F6:
  `test_tz_aware_source_index_normalises_to_naive_utc` (naive feature index
  vs America/New_York source, asserts `revised_fallback_inputs` at row 70
  and `initial_vintage_inputs` at row 164 derived from the payrolls spec
  constants lag_rows=63 / smooth_rows=1 / min_periods=1) and
  `test_all_three_tz_aware_inputs_fall_back_to_unknown_without_raising`
  (feature index, coverage start, and source all tz-aware: per-value
  comparison falls back to `unknown_inputs` without raising).
- **Non-string/date/Timestamp coverage (F7).** A coverage value that is
  bool, int or float (e.g. 0, 1.5, True) is unparseable and resolves the
  leg to `unknown_inputs`. Parametrised test covers 0, 1.5, True.
- **State scope (W3).** The audit gains `state_columns_qualified: false` and
  a measured `state_inheritance` object (count and first/last date of rows
  whose `macro_window_basis` is `initial_vintage_inputs` while the start of
  their current contiguous `quad` run has a different basis). The object is
  computed in `build_frames` after both `quad` and `macro_window_basis` are
  available, then attached to the audit. The source registry now spells out
  that the `macro_window_*` columns qualify slow-component INPUT windows
  only and do NOT qualify `quad`, `pending_quad` or any state column.
  `state_inheritance` is pinned to `{n_rows: 155, first_date: 2020-11-11,
  last_date: 2021-11-02}` on both the builder and CLI tests; an
  empty-mapping mutant fails (F4 quoted).
- **Explicit qualification flags (W1).** The function audit and the
  serialized sidecar both assert every `*_verified` /
  `legacy_pit_class_changed` / `numeric_model_changed` /
  `historical_replay_eligible` flag is False. Verified by flipping each flag
  in turn to True: every flip surfaces a failing test in the same set
  (the parameterized lag-endpoint test, the actual builder test, and the
  actual CLI test).
- **Key rename (W4).** The unread `MACRO_WINDOW_SPECS` key `feature` is
  renamed to `scored_feature` everywhere it is declared or serialized
  (dependencies block, dependency-description test). The committed
  `window_basis_verification_20261002.json` is a historical receipt and is
  left untouched; the new facts are written to
  `window_basis_repair_20261003.json` from fixture/synthetic runs only.
- **Unparseable coverage (W5).** An unparseable `coverage_start` value
  resolves that leg to `unknown_inputs` instead of raising; covered by a
  new test passing the string `"not-a-date"`.
- **Behaviour preservation (W6).** No pre-existing test changes except
  where it reads the renamed key OR passes an explicit `sources=`
  argument built from the same un-filled series the fixture already
  constructs. Parity is asserted on the SYNTHETIC fixture only; the
  seven real-store tests are skipped wherever the store is absent. The
  store is tracked at data/fred_vintage/vintages.parquet (and the
  regime_history.parquet — the regime history artifact — at data/regime/regime_history.parquet);
  a full checkout materialises the bytes and the seven tests run, while
  sparse session worktrees omit data/ and the tests are skipped on the
  `_HAVE_STORE` gate. No CI run was observed in this lane. The `pit_class`, `fallback_notes` and every numeric
  regime column are unchanged on the same inputs; the W2 window-basis
  labels are intentionally more conservative (the default path is now
  `unknown_inputs` and the per-value path may downgrade a row that
  row-date logic would have called `initial_vintage_inputs`). The
  builder was NOT run against any real or production data store, no
  producer outside `build_frames` calls `macro_window_provenance`, and
  nothing was written under `data/`. The size of the label change on
  real history is NOT measured in this PR.
