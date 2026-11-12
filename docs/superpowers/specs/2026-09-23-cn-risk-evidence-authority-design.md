# China/HK/Canada Risk Radar Episode-Aware Evidence Authority Design

**Status:** Frozen for implementation

**Operation:** `cn-risk-p2-evidence-authority-20260923-solpro-001`

**Repository:** `mastermindx-market-intelligence/macro`

**Source base:** `8db6896dab2199a4b7fc61a005c225380cac7cd6`

**Protected Skillpack:** `a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`

## Outcome

The existing CN/HK/CA forward log remains the sole source ledger, but overlapping daily 21-session outcomes stop masquerading as independent authority evidence. The Risk Radar signal, states, probabilities, UI, weights, and forward rows do not change. `can_force` becomes the conjunction of the exact pre-repair authority gate and a new episode-aware gate, so this migration cannot grant authority that the prior implementation would refuse.

## Verified defect

The scorecard first checks `n_graded >= 30` and `n_alerts >= 8`, then calls `constitution.grant_authority` with `evidence.n = n_alerts`, `evidence.hits = alert_hit_count`, and floors `{min_n: 30, min_events: 8}`. The shared function applies `min_n` to `evidence.n` and `min_events` to hits. The effective gate is therefore 30 total graded rows, 30 loud rows, and 8 successful loud rows, not the documented 30 total / 8 loud contract. This is conservative but semantically inconsistent.

The daily rows are also dependent. Every row grades a 21-session forward window, so adjacent rows share almost the entire outcome path. July CN's five matured loud rows represent one unresolved stress episode, not five independent trials.

## Hard boundaries

- Do not modify `engine/risk_radar_intl.py`, templates, weights, `_GROSS`, Portfolio, Prophet, ranking, or any source signal.
- Do not rewrite or backfill historical forward rows.
- Do not create another ledger, episode store, lifecycle, event plane, or LLM authority step.
- Preserve nightly sole-writer and PIT behavior.
- Preserve existing scorecard keys and their meanings. New fields are additive.
- Do not change shared constitution semantics. Its current callers already provide independent trial units; the mismatch is local to the international adapter.

## Canonical row ordering

Episode derivation is a pure read of the existing `<market>_forward_log.jsonl`. The exact pre-v2 fence is evaluated from the raw graded rows, raw `alert=true` rows, raw alert hits, raw all-row base rate, and original last graded `asof`; those values are preserved explicitly as `legacy_*` metrics. The new episode view is ordered by valid ISO `asof`, with original file order as the stable tie-breaker. Invalid dates are excluded and a duplicate session keeps the first canonical row, so malformed or repeated rows cannot inflate episode evidence. `n_loud_rows` means canonical graded rows with `alert=true`, matching the historical alert denominator. An episode is loud when `alert` is true or `state` is `elevated` / `risk-off`. Grading and outcomes are never used to decide where an episode begins or ends.

## Loud episode law

1. The first loud row opens an episode and is its immutable anchor.
2. Consecutive loud rows remain in that episode.
3. Non-loud rows increment a quiet-session counter.
4. Any loud row before a reset belongs to the existing episode and resets the quiet counter to zero.
5. A reset occurs after either (a) 21 consecutive observed non-loud rows, or (b) at least one observed non-loud row and at least 42 calendar days since the last loud row.
6. The 42-day fallback is a conservative two-horizon buffer for sparse logs. A calendar gap with no observed quiet never resets an episode.
7. An episode contributes one authority trial only when its anchor row is graded. Its outcome is the anchor's `any_dd5_within_h21`; later rows and later hits in the same episode do not add trials.
8. Unmatured anchors are reported but excluded from authority evidence.

This rule is causal, deterministic, replayable, insensitive to persistent/alternating alert days, and separates the checked-in July and September CN streaks without treating the unmatured September streak as evidence.

## Independent base windows

The base drawdown rate is estimated from non-overlapping canonical observation blocks:

1. Select the earliest graded row as the first anchor.
2. A later graded row is eligible when either its canonical row index is at least 21 observations after the prior anchor or its `asof` is at least 42 calendar days later.
3. Select the earliest eligible graded row and repeat.
4. Each selected anchor contributes one binary `any_dd5_within_h21` outcome.
5. Ungraded rows count for observed-row spacing but never contribute outcomes.

The 42-day fallback is twice the 21-session horizon in calendar time and prevents sparse-but-long histories from collapsing into one trial. It remains conservative: invalid dates and duplicates are discarded, and the fallback never creates more than one anchor inside the two-horizon buffer.

## Statistical contract

The scorecard reports the raw compatibility inputs, descriptive canonical row metrics, and authority-grade episode metrics:

- `legacy_n_total_graded_rows`, `legacy_n_alert_rows`, `legacy_n_alert_hits`, `legacy_row_base_rate_dd5_h21`, `legacy_row_evidence_asof`;
- `n_total_graded_rows`, `n_loud_rows`, `n_row_hits`, `daily_row_precision`;
- `n_independent_episodes`, `n_loud_episodes`, `n_episode_hits`, `n_unmatured_loud_episodes`;
- `episode_precision` and `episode_base_rate_dd5_h21`;
- one-sided 90% Wilson lower bound for loud-episode precision;
- one-sided 90% Wilson upper bound for the independent base rate;
- `episode_lift_lb = precision_lower_90 / base_upper_90`;
- row and episode evidence as-of dates.

The upper base bound prevents a zero observed base rate from becoming infinite lift. No authority calculation uses fake smoothing, an LLM, or repeated daily rows as independent trials.

## Authority contract before

The exact pre-repair gate is retained as a compatibility fence:

- at least 30 total graded rows;
- at least 8 loud rows before invoking the shared gate;
- shared gate then effectively requires at least 30 loud rows and 8 row hits;
- row-level Wilson lower-bound lift above 1.25;
- fresh row evidence.

Its result is exposed as `row_gate_granted` and `row_gate_reason`.

## Authority contract after

The final grant is:

`can_force = row_gate_granted AND episode_gate_granted`

The episode gate requires all of:

- at least 30 total graded rows;
- at least 8 loud rows (the documented accrual floor);
- at least 30 independent base windows;
- at least 8 matured loud episodes;
- at least 8 successful loud episodes;
- non-null episode evidence as-of;
- episode Wilson lower-bound lift over the Wilson upper base-rate bound strictly above 1.25;
- evidence not future-dated and no older than 120 days.

Because the old gate remains conjunctive, this migration has a mechanical no-grant-more guarantee. A later governance decision may retire the compatibility fence only in a separate reviewed change with evidence; this operation does not do so.

## Compatibility and output

Existing fields (`n_graded`, `n_alerts`, `alert_precision`, `alert_hit_rate`, `force_lift`, `wilson_lift_lb`, `evidence_asof`) keep their row-level meanings. Additive fields carry episode-aware semantics. `grant_reason` becomes the final conjunctive authority reason, while explicit row/episode reason fields remove denominator ambiguity.

Governance transition events remain in the existing ledger and gain additive row/episode evidence. No historical event or forward row is rewritten.

## Required falsifiers

Tests must prove: one persistent episode; alternating loud/quiet states without a 21-row reset; repeated hits in one drawdown; genuinely separated episodes; sparse logs; stale, invalid, and future-dated evidence; no alerts; all hits; zero observed base; incomplete rows; deterministic replay; July-like and September-like streaks; HK/CA no-alert behavior; and `new_can_force => old_can_force` over adversarial synthetic mutations.
