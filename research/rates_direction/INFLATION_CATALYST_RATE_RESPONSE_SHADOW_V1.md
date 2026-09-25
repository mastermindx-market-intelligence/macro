# Inflation catalyst -> Treasury response prospective shadow v1

Parent: WS:RATES-INFLATION-COMMAND / operation rates-direction-20260924-sol-001 / PR 7909.

Procedure pin: Mastermind a29161fa0a44cca9927afe042b5f7ea25aae1736,
Skillpack mastermind.sol_skillpack.v1 1.0.1 / bootstrap major 1.

## Job

Test the part of the rates problem that the rejected technical/state models did not know:

official inflation print versus the frozen pre-release expectation -> Treasury direction after the print.

This is a forward research shadow, not another release ledger. It consumes the existing
Release Radar forward ledger and the incumbent DGS10 history. It creates no collector,
scheduler, queue, publication plane, rank, size, gate or trade authority.

The existing CPI pre-release shadow asks whether Mastermind can predict the catalyst
before the print. This protocol asks a distinct downstream question: once the official
print is actually known, does its surprise versus the already-frozen expectation give
a useful same-session/near-term Treasury directional prior?

## Existing source owners only

### Frozen expectation context

Read data/release_forecast/forward_ledger.jsonl.

For each component, use only the champion row satisfying all of:
- row_type == projection
- model is null
- exact release / period / release_date match
- asof_night == release_date - 1 calendar day
- expectation_read.expectation_median is finite
- expectation_read.sources is a non-empty string list
- sigma_scale_pp is finite and strictly positive

This is the Release Radar owner's frozen expectation context. It is not renamed
"market consensus". At freeze time the admitted CPI/PCE expectation source is the
Cleveland Fed nowcast.

### Official actual

Use scored rows from the SAME existing Release Radar ledger, but accept an actual
only when an official receipt is present:
- row_type == scored
- exact release / period / release_date match
- actual_basis == official_published_metric
- actual_source == official_release_document
- non-empty actual_receipt_id
- finite actual_first (fallback actual)
- actual_observed_at is a timezone-aware timestamp
- the receipt was observed no later than 16:00 America/New_York on release day

Multiple model score rows may carry the same actual receipt. Deduplicate by
actual_receipt_id. If more than one official receipt exists, use the earliest
observed receipt: this study is about the initial knowable print, not a later
correction.

A late-captured official receipt is ineligible for the h0 actionable test even if its
numeric print is historically correct. Unknown availability never becomes same-day
availability.

## Event families

Two announcement families are eligible:
- CPI: cpi_headline + cpi_core
- PCE: pce_headline + pce_core

Headline and core from one publication form ONE event, never two observations.
Both components must have the same period, release date and exact T-1 expectation
cutoff. Missing one component means ABSTAIN / unavailable.

## Frozen catalyst rule

For each component:

z_actual = (official_initial_print - expectation_median) / sigma_scale_pp

Component state:
- HOT if z_actual >= +0.35
- COOL if z_actual <= -0.35
- INLINE otherwise

The +/-0.35 threshold reuses the incumbent Release Radar expectation-read scale; it is
not searched here.

Announcement signal:
- HOT if at least one component is HOT and neither is COOL
- COOL if at least one component is COOL and neither is HOT
- ABSTAIN if both are INLINE, the components conflict, or required evidence is absent

The event record preserves exact expectation sources, medians, sigma scales, official
actual receipt IDs and observation timestamps.

## Prospective boundary

Freeze date: 2026-09-24.

Only release dates strictly AFTER 2026-09-24 enter evaluation. Pre-freeze joined rows
may be reported only as source sanity and never enter accuracy metrics.

The first possible event is the next CPI/PCE publication for which Release Radar
actually preserves exact T-1 expectation rows and same-day official receipts. No
historical backfill can satisfy the prospective floor.

## Treasury outcome

Source: incumbent data/fred/DGS10.parquet.

Signal time is the latest accepted official component observation timestamp.
Because DGS10 is daily rather than an 08:30 ET tape, h0 is explicitly a
release-day close proxy, not a pure post-08:30 intraday move.

For each event:
- prior_close = last finite DGS10 observation strictly before release date
- h0 = release-date DGS10 close minus prior_close, bp
- h1 = next finite DGS10 observation after release date minus prior_close, bp
- h5 = fifth finite DGS10 observation after release date minus prior_close, bp

No missing date is filled and no intraday path is invented.

Directional class at every horizon:
- UP if move >= +2 bp
- DOWN if move <= -2 bp
- INLINE otherwise

An active HOT catalyst predicts UP; an active COOL catalyst predicts DOWN.
INLINE realized outcomes are misses for an active directional signal.

## Baseline and evaluation

Baseline on the SAME active events: sign of the five-observation DGS10 change ending
at the last observation before release, using the same +/-2 bp floor. INLINE baseline
is retained as an abstention, not silently discarded from candidate coverage.

Primary: h0 catalyst directional accuracy.
Secondary: h1 and h5 catalyst accuracy.

Report:
- all prospective event count, active/abstained count and missing-evidence reasons
- catalyst hit fraction at h0/h1/h5
- prior-yield baseline hit fraction on identical candidate-active events
- paired candidate-minus-baseline success difference where baseline is directional
- per-family diagnostics for CPI and PCE
- exact event records and evidence identities

Minimum descriptive floor: 12 eligible prospective events AND 8 active signals.
Promotion review cannot even be requested before 24 eligible prospective events.
No significance or authority claim is allowed below those floors.

There is exactly ONE candidate configuration. No threshold, family, horizon or
availability-rule search is authorized inside v1.

## Relationship to other rates lanes

- The pre-release CPI catalyst shadow remains separate and immutable.
- The RD2/#7923 policy-path measurement and #7940 prospective retention remain
  independent. Future policy-repricing confirmation may be a separately frozen
  incremental candidate only after that source is lawfully live.
- The rejected oscillator/crossover/phase-reset, post-shock driver-state and DNS
  point-forecast studies remain null and are not retuned here.
- Existing Release Radar reaction rows remain their owner's descriptive artifact.
  This shadow does not write or replace them.

## Authority

Research shadow only. authority=false.

A positive forward result still requires independent review, exact clock/source audit
and a separate product admission before any RIC stance, equity risk state, alert,
rank, size, gate or trade behavior can change.
