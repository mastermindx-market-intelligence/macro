# Regime research readiness: distinguish the sample's scope

Operation: `regime-research-readiness-20261002-astra-001`.
Parent: Macro #7088 / WS:RATES-INFLATION-COMMAND.
Procedure: Mastermind `72676f23d51c72591cb1e88af7c1564bc6637451`, compatible Skillpack 1.0.1.
Source base: Macro `bf6921873ea40f5868e0428d04fd38f78cc62c11`.
Measurement input: immutable Macro `564c41074d0028c65a3c1a3621d07c7a8fb0985d`.
State: implemented and locally checked, not independently accepted or production-proven.

## User capability and bounded change

The existing research-readiness report now distinguishes an estimable **per-stock
price-trend** sample from an estimable **US market-context** sample. A long
bull/bear/choppy history no longer has to be interpreted as a long macro-regime
history by a downstream researcher. Unknown custom axes remain unspecified even
when their names or values look macro-like.

This extends `engine/regime_conditioning_coverage.py`, its existing `assess` result
and `format_report` consumer. It does not create another evaluator, source store,
registry service, ranker, signal, scheduler, historical model or research queue.
The old `estimable_axes` result remains available. New grouping is descriptive
column metadata, not an independent admission rule. All numerical statistics,
verdicts and frozen thresholds are unchanged.

The column meanings come from `engine/track_record.py` `_IDENTITY_COLS` and
`_make_row`/`_regime_at`: `regime_at_entry` is computed from that security's price
history; the five other named axes are the separately stamped US regime vector.
Metadata declares this contract; it does not verify that arbitrary caller data
really has that provenance. The result explicitly leaves historical availability
unassessed. Passing coverage/contrast never certifies forecast skill.

## Measured current denominator, without reading outcomes

Exact input: `data/signal_archive/track_record.parquet`, 10,903,975 bytes,
SHA-256 `52593efe19c6a248a56e956e5223b480fab9bb6a8838a750aace513f0e86be5b`.
Only date/provenance and regime-label columns were read, not future outcomes.
No model was fitted and none of the rejected historical studies was rerun.

The archive has 60,538 signal rows and 13,172 distinct signal dates, from
1962-11-29 through 2026-09-30. This is signal-archive coverage, not a census of
all listed securities or an automatically point-in-time-certified panel.

| Axis | Stamped rows | Distinct stamped dates | Distinct months | Within-stamping-window verdict |
|---|---:|---:|---:|---|
| Per-stock price trend | 60,535 | See machine receipt | 767 | Estimable for its declared scope |
| Macro quadrant | 583 | 40 | 3 | Insufficient contrast |
| Volatility regime | 583 | 40 | 3 | Single state |
| Fused risk label | 583 | 40 | 3 | Insufficient contrast |
| Rate pressure | 555 | 37 | 3 | Insufficient contrast |
| Risk-radar state | 583 | 40 | 3 | Insufficient contrast |

All five US market-context axes fail the full-archive coverage requirement. Merely
restricting to their own stamping period does not solve the problem: the existing
12-month-per-state contrast requirement still fails, and volatility remains one
observed state. No threshold was relaxed to make a candidate pass.

The joint complete sample contains 555 signal rows across 19 observed five-axis
combinations; no such cell spans more than two distinct months. Those are observed
combinations, not 19 independent regimes. The per-stock trend axis has multiple
states on 8,336 common signal dates, which is consistent with its per-security
scope and inconsistent with treating it as one global market label per date.
The receipt's own within-window counters contradict that picture in a way the
per-security reading does not explain: `fused_risk_label` carries more than one
state on 3 stamped dates, and `risk_radar_state` carries more than one state on
4 stamped dates, both over a stamping window of only 40 distinct stamped dates.
These are date-level repetitions of a US-context axis, so the within-window
multi-state count does not by itself prove independence across dates. The
counter-observation traces to the US-context vector's `vector_asof` lag of
0-3 days behind the signal `date`: across the 583 stamped rows, 6 rows carry a
`vector_asof` whose calendar month differs from the signal `date`'s calendar
month. Distinct-month counts throughout this report derive from the signal
`date`, never from the vector's as-of date, so a vector stamped on the last day
of one month still contributes to the next month's count.

Complete counts, state cells, source identity and scope-grouped output are in
`research_readiness_20261002.json`. That receipt compares the original and amended
owner on the same exact data: every old numerical field, verdict, gate and passing
axis remains identical. No raw price or vendor payload is copied into this report.

## Consequence for the parent programme

This result does not reject granular regime modelling. It rejects using the large
signal-row count as evidence that the current archive already supplies a deep
multidimensional macro history. The next scientific prerequisite is source and
time qualification of the existing historical owners, not another combinatorial
backtest over these nineteen thin cells.

Keep three evidence bases distinct when that work resumes:

1. Actual issued records: the existing saved-prediction/first-known owners, with
   native issuance and missing records preserved. Do not manufacture an old call.
2. Point-in-time reconstruction: features and training restricted to information
   legitimately available at each origin. A reconstruction is not proof that an
   historical model actually issued that forecast.
3. Retrospective description: later-revised or later-fit history may describe an
   episode, but must not be relabelled as an issued or tradable historical signal.

Existing #7015 owns recorded-HMM history and its native issuance consumer; #7165
owns the PIT macro-turnaround source/replay lane. They must be qualified through
their existing custody and release paths, not duplicated here. #8257 continues the
current conversational context; #7441 already owns the natural/coached answer
benchmark. No evaluator or chronology owner is replaced by this change.

## Scope of the axis-scope claim

The new `axis_scope` field reaches `engine.regime_conditioning_coverage.format_report`
readers only. The change does not propagate the scope into either of the two
existing regime consumers:

- `engine/seasonality/regime.py:110` still lists `regime_at_entry` under
  `"market"` in the `AUTHORIZED_AXES` allow-list. A research-readiness report
  that calls `regime_at_entry` "security_price_trend" therefore disagrees with
  the seasonality authorisation table on the same column.
- `scripts/regime_reliability_phase0.py:135-138` re-emits the per-axis result
  with `coverage / n_states / min_state_months / verdict / span` only; the
  `axis_scope` field is dropped on the way out and does not appear in the
  phase-0 owner record.

Both are open follow-ups for the existing owners; neither was modified by
this PR. Downstream readers of `format_report` see the new scope; the
seasonality and phase-0 reliability pipelines continue to operate on their
pre-existing, pre-scope axis naming.

The old #7015 Studio review carrier was inspected at its exact retained result
paths during this continuation: neither `review.exit` nor `result.md` was present,
and no matching command line was found. This does not establish that the old
unknown invocation never executed, and no duplicate review was launched. Its
source/release recovery stays with that original operation.

## Verification and release boundary

Of the 13 tests added against the amended module, twelve fail against the old
engine and the thirteenth asserts the new CI-ownership surface and fails only
against the pre-amendment CI files. The amended existing coverage suite passes
29 tests; that suite plus the track-record producer suite passes 95 tests. Four
host temporary-cleanup warnings remain; no guard was disabled. The previously
grandfathered coverage suite is now explicitly run by the existing
`unrun-scoring-engine` code job; exactly one baseline entry was removed. No new
job, workflow, runner, gate or exception was added.

The source diff and local result are not independent review, full hosted CI,
production adoption or predictive promotion. This bounded child remains held for
those applicable source gates. The parent programme is incomplete. The earlier
#8257 production-capture denial remains in force and was not retried here.
