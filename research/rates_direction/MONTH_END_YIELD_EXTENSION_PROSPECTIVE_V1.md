# Month-end Treasury-yield extension — prospective shadow v1

Parent: WS:RATES-INFLATION-COMMAND / operation rates-direction-20260924-sol-001 / PR 7909.

Procedure pin: Mastermind a29161fa0a44cca9927afe042b5f7ea25aae1736,
Skillpack mastermind.sol_skillpack.v1 1.0.1 / bootstrap major 1.

## Purpose

Resolve whether the long-run month-end Treasury-yield effect remains useful NOW,
without selecting the attractive post-result non-quarter subset or backfilling future
validation from already-seen history.

The direct-yield replication passed retrospectively, but post-result diagnostics found
recent attenuation and quarter-end heterogeneity. This shadow therefore freezes the
ORIGINAL generic month-end sign, not a repaired subgroup rule.

## Existing owners only

Calendar:
engine.rebalance_calendar.month_end_sessions(), the incumbent display/context calendar
owner. No new calendar engine.

Outcome:
data/fred/DGS10.parquet / us10y, the incumbent 10Y market-yield source.

Experiment accounting:
existing TrialLedger family d2_rates_calendar_flows. Family literal width must be 21
before this shadow; append exactly one prospective config.

No new collector, scheduler, event ledger, publication plane or authority owner.

## Frozen schedule

Freeze date: 2026-09-24.

At freeze, persist the NEXT 24 month-end NYSE session dates strictly after the freeze
date from engine.rebalance_calendar.month_end_sessions(). This exact schedule is the
prospective event set. It is not regenerated from future yield data.

An extraordinary exchange closure that makes a frozen schedule date invalid is a
calendar exception. Do not silently substitute another date; record the exception and
require an explicit amendment.

## Signal

On every frozen month-end session:

DGS10 expected direction = DOWN.

The sign never changes for quarter-end status, inflation releases, FOMC days,
oscillators, policy pricing or the post-result non-quarter diagnostic. Those may later
be compared as context, but they cannot rewrite this v1 signal.

Quarter-end month (Mar/Jun/Sep/Dec) is retained on each row solely as a diagnostic flag.

## Outcome

For each frozen event date once DGS10 is available:

- prior_close = last finite DGS10 observation strictly before event date
- raw_bp = (event-date DGS10 - prior_close) * 100
- other_month_mean_bp = mean of all finite close-to-close DGS10 changes in the same
  calendar month before the event observation
- excess_bp = raw_bp - other_month_mean_bp
- directional success = raw_bp < 0
- zero change is not a directional success

The event is pending until the exact frozen event date has a finite DGS10 observation.
No later date substitutes for a missing frozen event.

## Frozen prehistory guard

At freeze, record a canonical digest of every finite DGS10 date/value through the
latest observation then available. A later report recomputes that prefix digest.

If the historical prefix changes, the report must expose
historical_prefix_changed=true. It must not silently claim byte-for-byte source
continuity. Events whose baseline depends on changed pre-freeze values require review
before they can support promotion.

## Evaluation

Primary continuous metrics:
- mean raw_bp
- mean excess_bp

Secondary:
- fraction of events with raw_bp < 0
- chronological split-half means
- quarter-end vs non-quarter descriptive slices, explicitly NON-selective
- Newey-West HAC mean t-stat with the existing family rule:
  max(2, min(4, floor(sqrt(n)))) when n permits

Descriptive floor: 12 matured scheduled events.

Promotion review floor: 24 matured scheduled events. At that point the unchanged
retrospective gate is required for both raw and excess:
- mean < 0
- HAC t <= -2
- first chronological half mean < 0
- second chronological half mean < 0

There is one config and no threshold/grid search. Quarter-end/non-quarter results do
not become separate candidates inside v1.

## Initial state

The data source ended 2026-09-22 when this protocol was authored. Therefore no
post-freeze scheduled month-end outcome existed before freeze. The first scheduled
event is expected to be 2026-09-30 if that date appears in the frozen calendar.

## Authority

Research shadow only. authority=false.

A future PASS may support admission review for a display/context or rates-direction
feature, but does not itself create RIC score, equity-risk, alert, rank, size, gate or
trade authority.
