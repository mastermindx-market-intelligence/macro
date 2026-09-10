# Leadership Persistence RPH-0 — Architecture Freeze and Preregistration

**Date:** 2026-09-10
**Operation:** `leadership-persistence-rph0-20260910-sol-001`
**Program:** `sector-rotation-intelligence`
**Cross-owner dependency:** `WS:TEMPORAL-GRAIN-INTELLIGENCE`
**Protected procedure:** `mastermindx-market-intelligence/Mastermind@dd553d1b0b8eed9511da2d3d5ec02cc9cd8edca1`
**Pickup base:** `mastermindx-market-intelligence/macro@d675bbece0848e8587e4070b576e7585e02b5a19`
**Capability at freeze:** `SPEC_ONLY`
**Authority at birth:** research/display context only; rank, gate, size, trade, Prophet, Oracle and portfolio authority all false

## 1. Outcome and bounded scientific question

The user needs Mastermind to distinguish three facts that can disagree:

1. whether a published theme remains highly ranked;
2. whether that leadership state is still strengthening or already reversing;
3. whether a strategy-specific signal has enough remaining economic life to admit a new entry.

RPH-0 tests only the first two on the existing point-in-time **published US theme-output archive**.
It asks:

> How persistent are the rankings and published score/breadth states emitted by the current US
> thematic intelligence system, how rapidly do top-quartile themes leave leadership, and does the
> recent surface look continuation-dominant, reversal-dominant, multiscale or unresolved?

This wave does **not** choose a MACD timeframe, reproduce TradingView, infer usefulness from chart
geometry, or open an entry. Those questions remain governed by the existing Temporal Grain sequence
and Prophet Entry Truth.

## 2. Why this is not a duplicate system

Current archaeology found four different owners whose scopes must stay separate:

- `engine/sector_pulse.py`, Rotation Events and Subsector Turn own published rotation state and
  event lifecycle.
- `engine/neuralweb/half_life.py` owns Signal Commons family-level holding-horizon/staleness decay;
  it does not measure cross-sectional theme-leadership survival.
- `WS:TEMPORAL-GRAIN-INTELLIGENCE` owns exact chart identity and G/A/K/D signal-grain mechanics.
  W1A implementation exists on open Draft PR #6803 but remains `BUILT_NOT_PROVEN`, unmerged and
  blocked on exact WMT/silver packets plus current release reconciliation.
- Prophet Entry Truth owns strategy-specific entry Availability and is not modified here.

RPH-0 is therefore a research projection over the existing `baskets` archive, not a new regime,
rotation, event, identity, membership, half-life, trial, publication or authority plane.

## 3. Frozen input and source semantics

Primary input:

`data/signal_archive/baskets.parquet`

The archive is the keep-first, append-only record of what the US thematic system published per
`asof`. The lossless `snapshot_json` contains `themes[]` rows with `id`, `rank`, `score`, `label`,
`components.breadth`, and other descriptive fields.

RPH-0 measures **published-output persistence**. It does not claim that current raw basket
membership is historically exact or that the output rank is an economic-return series.

The loader must:

- bind the exact input SHA-256;
- require `asof`, `logged_at` and `snapshot_json` columns;
- keep the first archive row for duplicate `asof` values and record every dropped duplicate;
- require snapshot `as_of` to equal the archive `asof` date;
- drop non-NYSE-session rows and record them;
- reject duplicate theme ids within a snapshot;
- reject non-finite/non-positive ranks, non-finite scores, and malformed theme arrays;
- preserve optional `label` and `components.breadth` as null rather than zero;
- never forward-fill missing archive snapshots for pair metrics.

## 4. Frozen horizons, windows and eligibility

Trading-session horizons:

`H = [1, 2, 3, 5, 7, 10, 15, 20]`

For an anchor session `t` and horizon `h`, the target is the exact `h`-th NYSE session after `t`.
A pair exists only when both endpoint snapshots exist. Missing intermediate snapshots do not change
that elapsed-session identity, but they are counted in archive-coverage receipts.

Cross-sectional pair eligibility:

- at least 10 common theme ids;
- common ids must be at least 80% of the union of the two endpoint theme sets;
- every metric uses only the common ids;
- no rank, score or breadth imputation.

Windows:

- `recent`: anchors inside the latest 20 NYSE sessions ending at the archive's latest valid `asof`;
- `prior`: every eligible anchor strictly before the recent-window start;
- `all`: all eligible anchors.

A cell is `MEASURED` only with at least 8 eligible anchor pairs. Otherwise it is
`INSUFFICIENT_HISTORY` and all estimates for that window are null.

## 5. Frozen pair metrics

For each eligible `(t, t+h)` pair:

### 5.1 Rank-state persistence

`rank_rho = Spearman(rank_t, rank_t_plus_h)`

Positive means the published ordering remains similar. This is a state-memory measurement, not a
return forecast.

### 5.2 Top-quartile survival

At each endpoint, top quartile is `rank <= ceil(n_common / 4)` after ranks are recomputed over the
common set with deterministic average ties.

- `topq_overlap = |Q1_t ∩ Q1_t+h| / |Q1_t|`
- `chance_overlap = |Q1_t+h| / n_common`
- `topq_overlap_lift = topq_overlap / chance_overlap`
- `leader_to_laggard = |Q1_t ∩ bottom_half_t+h| / |Q1_t|`
- `laggard_to_leader = |bottom_half_t ∩ Q1_t+h| / |bottom_half_t|`

### 5.3 Published-score continuation

`score_continuation_ic = Spearman(-rank_t, score_t+h - score_t)`

Positive means current leaders tend to gain published score; negative means current leaders tend to
lose score. This is not an economic-return IC and must never be labeled as alpha.

### 5.4 Breadth survival

For rows with finite `components.breadth`:

- `leader_breadth_delta = mean(breadth_t+h - breadth_t for Q1_t)`
- `breadth_rank_rho = Spearman(breadth_t, breadth_t+h)`

A breadth metric requires at least 80% finite breadth coverage within the common theme set.
Otherwise it is null with `INSUFFICIENT_BREADTH_COVERAGE`.

## 6. Aggregation and uncertainty

Each metric is first computed once per anchor date. Window estimates are the arithmetic mean over
eligible anchors.

Uncertainty is a deterministic moving-block bootstrap over anchor-date values:

- 2,000 resamples;
- seed `20260910 + 100*h + metric_index`;
- block length `min(max(1, h), max(1, floor(n/3)))`;
- 90% percentile interval;
- no CI when `n < 8`.

Adjacent horizons and anchors are dependent. RPH-0 reports intervals and sample sizes but performs
no multiple-hypothesis promotion decision.

## 7. Transition matrix and leader residency

### 7.1 Quartile transitions

For every eligible exact one-session pair, each common theme is mapped to `Q1`, `Q2`, `Q3` or `Q4`
using deterministic percentile buckets. Publish counts and row-normalized probabilities. No
transition is inferred across a missing one-session archive endpoint.

### 7.2 Top-quartile residency episodes

A theme's Q1 episode is stepped only across adjacent NYSE sessions whose snapshots both exist.

- a transition from non-Q1 to Q1 starts an observed episode;
- an episode beginning at the first available snapshot is left-censored;
- a missing next-session snapshot ends the observed interval as `archive_gap` right-censored;
- an observed exit from Q1 is an event;
- an episode still active at the archive end is right-censored.

Publish the episode table and a Kaplan-Meier survival curve. The KM median is null until there are at
least 8 episodes and at least 4 observed exits.

## 8. Honest half-life rule

A scalar rank half-life is attempted separately for each window only when:

1. at least four measured horizon cells exist;
2. the shortest-horizon mean `rank_rho` is finite and positive;
3. Spearman correlation between horizon and mean `rank_rho` is negative;
4. no later point rises by more than 0.05 over the preceding admissible point;
5. the curve crosses half of the shortest-horizon value.

The first crossing is linearly interpolated in trading sessions. Otherwise `half_life=null` with one
of:

- `INSUFFICIENT_HORIZONS`
- `NONPOSITIVE_START`
- `NON_DECAYING`
- `NON_MONOTONE`
- `NO_HALF_CROSSING`

The full surface remains primary. A null half-life is a successful result.

## 9. Frozen temporal-shape classifier

The classifier reads **published-score continuation**, not returns:

- `short` = median of measured recent cells at horizons 1, 2, 3 and 5;
- `long` = median of measured recent cells at horizons 10, 15 and 20.

Each side requires at least two measured cells.

- `MULTI_SCALE`: `short <= -0.05` and `long >= +0.05`
- `REVERSAL_DOMINANT`: `short <= -0.05` and `long < +0.05`
- `CONTINUATION_DOMINANT`: `short >= +0.05` and `long >= +0.05`
- `TRANSITIONAL`: all other measured combinations
- `INSUFFICIENT_HISTORY`: either side lacks two cells

This is a descriptive label about published output dynamics, not a market-regime authority or
holding-period instruction.

## 10. Exact result contract

The CLI writes strict JSON and Markdown into an explicitly supplied output directory:

`research.rotation_persistence_rph0.v1`

Required top-level fields:

- `schema_version`
- `operation_key`
- `produced_at`
- `source`
- `parameters`
- `quality`
- `surface`
- `transition_matrix`
- `residency`
- `half_life`
- `temporal_shape`
- `authority`
- `notes`

All JSON is UTF-8, sorted, deterministic except the explicitly injected `produced_at`, and rejects
NaN/Infinity. Authority is fixed to:

```json
{
  "is_context_only": true,
  "may_rank": false,
  "may_gate": false,
  "may_size": false,
  "may_trade": false,
  "may_modify_prophet": false,
  "may_modify_oracle": false
}
```

The CLI refuses an output directory inside `data/`, `site/`, `engine/`, `config/`, or the production
TrialLedger path. It performs no network access and imports no production writer.

## 11. Research interpretation boundaries

RPH-0 may conclude only:

- the current published-output persistence curve is measured or underpowered;
- top-quartile survival and transition behavior;
- whether the published-score shape meets the frozen label thresholds;
- whether a scalar half-life is admissible or honestly null.

It may not conclude:

- that 2D/3D MACD is economically inferior;
- a preferred trading timeframe;
- an entry, exit, rank, size, gate or trade;
- a causal driver;
- point-in-time raw business exposure;
- broad historical generalization beyond the archive's own date range.

## 12. Canonical continuation after RPH-0

- If the archive is underpowered, continue accrual and do not widen the estimator.
- If the surface is measured, Sol may design a separate preregistered deep-history reconstruction
  using point-in-time basket membership and owner price data.
- Exact MACD/timeframe usefulness remains behind Temporal Grain W1A/W1B and its exact chart packets.
- Any later product projection must extend Sector Pulse/Turn Desk or Sector Central; no new page or
  regime authority.
- Any Prophet use remains context-only until Entry Truth independently admits a strategy-specific
  consumer.
