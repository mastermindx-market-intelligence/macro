# CN/HK/CA Risk Radar Episode-Aware Authority Replay

**Operation:** `cn-risk-p2-evidence-authority-20260923-solpro-001`

**Base:** `8db6896dab2199a4b7fc61a005c225380cac7cd6`

**Contract:** `risk_radar_intl.authority.v2`

**Status:** Draft/HOLD evidence; no signal, UI, weight, or source-ledger change

## Current bug reproduction

A synthetic ledger with 30 total graded rows, 8 loud rows, and 8 loud hits reproduces the pre-repair mismatch:

```json
{
  "n_graded": 30,
  "n_alerts": 8,
  "alert_hit_rate": 1.0,
  "force_lift": 3.75,
  "can_force": false,
  "grant_reason": "insufficient-n: n=8 < min_n=30"
}
```

The documented precheck is 30 total / 8 loud, but the shared call receives `n=8` with `min_n=30`; its `min_events=8` floor is applied to hits. The effective pre-repair contract is therefore 30 total rows, 30 loud rows, 8 loud-row hits, Wilson lift above 1.25, and fresh evidence.

## Derived episode law

- A first loud row opens an immutable episode anchor.
- Repeated loud rows remain one episode.
- Re-arm requires either 21 consecutive observed non-loud rows, or at least one observed non-loud row plus 42 calendar days since the last loud row.
- A gap with no observed quiet cannot re-arm.
- Only the anchor's matured h21 outcome contributes one episode trial.
- Independent base anchors are greedily separated by 21 canonical observations or 42 calendar days.
- Invalid dates and duplicate sessions cannot add evidence; the first canonical row for a session wins.
- All derivation is pure and read-only over the existing forward JSONL.

The 42-day fallback was added after falsifying a strict observed-row-only rule against the sparse checked-in ledger: that stricter rule incorrectly merged the separated July and September CN streaks.

## CN replay

### Old row-level view

| Metric | Value |
|---|---:|
| Total graded rows | 16 |
| Loud rows | 5 |
| Loud-row hits | 2 |
| Daily-row precision | 0.400000 |
| All-row h21 drawdown base rate | 0.562500 |
| Point lift | 0.71 |
| Row evidence as-of | 2026-08-25 |
| `can_force` | false |

The five matured loud rows from July 10–16 collapse to one matured episode rather than five trials.

### New episode-aware view

| Metric | Value |
|---|---:|
| Independent base windows | 2 |
| Independent base hits | 1 |
| Base rate | 0.500000 |
| One-sided 90% base upper bound | 0.879148 |
| Matured loud episodes | 1 |
| Episode hits | 1 |
| Episode precision | 1.000000 |
| One-sided 90% precision lower bound | 0.269831 |
| Conservative episode lift lower bound | 0.306923 |
| Unmatured loud episodes | 1 |
| Episode evidence as-of | 2026-07-10 |
| `can_force` | false |

Independent anchors are `2026-06-26` and `2026-08-20`. The matured loud anchor is `2026-07-10`. The current September streak is one unmatured episode anchored `2026-09-03`; it contributes zero authority trials.

## HK replay

| Metric | Value |
|---|---:|
| Total graded rows | 15 |
| Loud rows / row hits | 3 / 0 |
| Daily-row precision | 0.000000 |
| Independent base windows / hits | 2 / 0 |
| Base rate / 90% upper | 0.000000 / 0.575013 |
| Matured loud episodes / hits | 1 / 0 |
| Episode precision / lower bound | 0.000000 / 0.000000 |
| Episode evidence as-of | 2026-07-14 |
| `can_force` | false |

Independent anchors are `2026-06-26` and `2026-08-20`; the single matured loud episode is anchored `2026-07-14`.

## Canada replay

| Metric | Value |
|---|---:|
| Total graded rows | 27 |
| Loud rows / row hits | 0 / 0 |
| Independent base windows / hits | 2 / 0 |
| Base rate / 90% upper | 0.000000 / 0.575013 |
| Matured loud episodes | 0 |
| Episode evidence as-of | none |
| `can_force` | false |

Independent anchors are `2026-06-26` and `2026-08-07`. With no loud episodes, episode precision is intentionally undefined rather than fabricated.

## Authority contract after repair

The scorecard names all denominators. The final authority result is:

```text
can_force = legacy_row_gate_granted AND episode_gate_granted
```

The legacy row gate preserves the exact pre-repair effective behavior as a migration fence, using the raw graded-row count, raw `alert=true` count, raw alert hits, raw all-row base rate, and original last graded `asof`. The episode gate separately requires 30 canonical graded rows, 8 canonical alert rows, 30 independent base windows, 8 matured loud episodes, 8 episode hits, a valid, non-future, fresh evidence date, and conservative Wilson lift above 1.25 using the base-rate upper bound. Episode loudness may also recognize an elevated/risk-off state, but it cannot enlarge the legacy alert denominator. Therefore the migration cannot grant where the pre-repair code refused, even if malformed dates or duplicate sessions exist.

## Ledger integrity

Read-only replay before/after SHA-256 values were identical:

- CN: `11577f99d426d3b8295acf5870d27e8ce3758c0c7003e2d0dd4f08b434602b7e`
- HK: `0e4567196e0adf8437bcd380ceb2730f2f5385464bf2cf664e00416eb91421c4`
- CA: `e26e572056af91728817458aebc89aab6ffc36389dddaeb2682660fd93cc4472`

No historical row was rewritten, appended, or reordered.

## Shared constitution caller audit

`engine/neuralweb/constitution.py` is unchanged. Production callers are:

- `engine/neuralweb/cortex.py`: its fallback passes attention-track-record hits and N with floors 25/8.
- `engine/altdata_brain.py`: it passes `n_dates`, explicitly documented as independent qledger date clusters, with floors 25/8.
- `engine/risk_radar_intl_audit.py`: now uses a local denominator-explicit adapter, then invokes the unchanged shared Wilson/freshness primitive for the legacy row gate and the episode gate.

Because the generic callers already define their own independent trial unit, changing shared constitution semantics would create unnecessary blast radius. The repair remains local without duplicating Wilson or freshness logic.
