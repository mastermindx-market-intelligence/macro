# CPI catalyst-to-rates prospective shadow v1 — pre-outcome contract

Parent: WS:RATES-INFLATION-COMMAND / rates-direction-20260924-sol-001 / PR 7909.

Procedure pin: Mastermind 819abc8c23609cdded2b33f6e1bfc7854bd5c847,
Skillpack mastermind.sol_skillpack.v1 1.0.1 / bootstrap major 1.

## Job

Test a narrower causal sequence than the rejected technical and driver-state studies:

pre-release CPI expectation gap -> realized release catalyst -> Treasury direction.

This protocol is frozen before any eligible post-freeze CPI release. It consumes
existing Release Radar forward rows and the incumbent DGS10 market-history source.
It creates no forecast ledger, collector, scheduler, queue, promotion controller or
trade authority.

## Why this is distinct

The rejected rate-shock study conditioned an already-observed five-session yield
move on real/breakeven, term-premium, cross-asset and auction state. It did not know
the sign of the next macro catalyst.

The rejected oscillator studies tried to infer the next yield swing from transformed
price state. They did not predict the macro print.

This study asks whether a forecast that is already frozen before CPI can identify
whether the print will be hotter/cooler than the contemporaneous expectation context
well enough to anticipate the direction of the Treasury response.

## Forecast inputs: existing owners only

Source of model forecast:
data/release_forecast/forward_ledger.jsonl

Use only rows satisfying all of:
- row_type == shadow_projection
- model == coherent_ridge_v1
- release in {cpi_headline, cpi_core}
- model_epoch == coherent_ridge_v1
- target_epoch == alfred_same_release_vintage_proxy_v1
- display_only is true
- authority is false
- asof_night is exactly release_date minus one calendar day

The coherent-target model already fail-closes in its owning Release Radar producer.
This study does not refit it.

Source of expectation context:
the champion projection row in the SAME existing forward ledger with the identical
asof_night, release, period and release_date. Read only its frozen
expectation_read.expectation_median and expectation_read.sources. Do not consume the
legacy champion projection point, surprise-skew direction or model target.

The expectation context is NOT called market consensus. At freeze time all historical
stored expectation reads use only Cleveland Fed nowcasts. Future rows may include
other expectation sources already admitted by the existing Release Radar owner; their
exact source names remain attached to every event.

## Event construction

Headline and core are one CPI announcement, not independent observations.

For each component:
gap_pp = coherent_ridge projection_point - contemporaneous expectation_median.

Component state:
- HOT if gap_pp >= +0.05 percentage point
- COOL if gap_pp <= -0.05 percentage point
- INLINE otherwise

The 0.05pp threshold is fixed because CPI is published to one decimal place; it is
half a 0.1pp displayed-print increment. No threshold search is permitted.

Announcement signal:
- HOT if at least one component is HOT and neither is COOL
- COOL if at least one component is COOL and neither is HOT
- ABSTAIN if both are INLINE, they conflict, either coherent row is missing, or
  either expectation context is unavailable

The signal record preserves both component gaps, prediction IDs, expectation sources,
input hashes and source epochs.

## Prospective boundary

Freeze boundary: 2026-09-24.

Only release_date > 2026-09-24 is eligible for the prospective evaluation. Earlier
rows may be reported only as PRE_FREEZE_EXCLUDED source sanity and never enter any
metric. No historical backfill can satisfy the prospective sample floor.

The first possible eligible release is the next CPI release for which the existing
coherent-target owner actually emits both valid T-1 shadow rows and the existing
expectation context is present. The protocol does not fabricate a row when that
producer withholds one.

## Treasury outcome and baseline

Market source:
data/fred/DGS10.parquet, the existing daily nominal 10-year Treasury yield history.

For each eligible CPI release date:
- prior_close: last finite DGS10 observation strictly before release_date
- h0: DGS10 on release_date minus prior_close, in bp
- h1: next finite DGS10 observation after release_date minus prior_close, in bp
- h5: fifth finite DGS10 observation after release_date minus prior_close, in bp

No missing business day is filled and no intraday path is invented.

Primary outcome is h0 direction. A realized move of >= +2bp is UP, <= -2bp is DOWN,
otherwise INLINE. The 2bp floor is fixed before outcomes to avoid treating a one-tick
rounded daily change as a directional event.

Secondary outcomes use the same +/-2bp classification for h1 and h5.

Baseline is the sign of the five-observation DGS10 change ending at the last
observation before the release:
- >= +2bp -> UP
- <= -2bp -> DOWN
- otherwise INLINE

The baseline uses no release forecast information.

## Evaluation

Every CPI release date is one event.

For active HOT/COOL catalyst signals:
- primary catalyst accuracy = fraction whose h0 class matches the catalyst direction
- baseline accuracy is reported on the same active events
- paired catalyst-minus-baseline success difference is reported
- h1 and h5 use the same definitions as secondary diagnostics
- INLINE realized outcomes count as misses for an active directional forecast
- abstentions remain visible and are never removed from coverage reporting

Minimum descriptive floor: 12 eligible post-freeze CPI release events, with at least
8 active catalyst signals. No significance or promotion claim is allowed below both
floors. Twenty-four eligible events are required before any promotion review may even
be requested.

No parameter changes or candidate variants are authorized inside v1. Any amended
threshold, model, expectation construction, horizon or outcome definition is a new
TrialLedger configuration and a new model epoch/spec.

## Authority and acceptance

This is research shadow only.

Even a positive result does not alter RIC stance, equity risk-on/off state, alerting,
ranking, sizing, gating or trading. Stronger authority requires:
- genuinely prospective sample floors above;
- independent non-author review;
- exact source/clock audit;
- production-path consumer design;
- separate acceptance.

The existing policy-path constituent/prospective-ledger lane remains independent.
This study neither blocks nor substitutes for it.
