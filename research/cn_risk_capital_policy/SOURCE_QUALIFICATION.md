# China Risk Radar historical-source qualification

Status: exact-head audit finding for `cn-risk-p4-capital-policy-20260923-solpro-001`; research only, Draft/HOLD, no live consumer.

## Ruling

The long China Radar replay is **causal/date-aligned in calculation but not authority-grade point-in-time history**. It is retained as a diagnostic counterfactual lane only. It may not satisfy the preregistered historical promotion gates or validate any gross coefficient.

This finding does not change a tested policy, mapping, crisis, metric, bootstrap, or promotion threshold after seeing outcomes. It enforces the preregistration and Chairman directive that historical reconstruction may carry authority only when PIT-honest.

## Evidence

The exact CN Radar state includes the `cn_breadth` leg at weight `1.0`. The breadth collector reads the current hand-curated `config["china"]["constituents"]` universe and downloads maximum available history for those names. The committed constituent inventory contains ticker, name, sector, and class but no `effective_from`, `effective_to`, `valid_from`, `valid_to`, or equivalent historical-membership dates. Historical breadth is therefore current-membership backfilled rather than membership-PIT.

The reconstructed macro source files also carry values indexed by observation date but no committed realtime/vintage metadata such as `vintage_date`, `realtime_start`, `first_observed`, or release timestamp. Their use is causal by date, but source-vintage PIT cannot be established from the exact carrier.

The source qualification is fingerprinted in `results/input_manifest.json` and emitted in `results/summary.json`. The harness fails promotion gates closed when `historical_authority_eligible` is false.

## Episode independence

The diagnostic episode atlas preserves the frozen 21-session post-alert outcome window. Where that window reaches the next alert, the earlier episode is marked `overlaps_next_episode=true` and excluded from independent reconstructed episode N. Open episodes without a complete 21-session outcome window remain censored.

These corrections preserve all diagnostic rows while preventing overlapping observations from being counted as independent authority evidence.

## Authority-bearing sample

Authority therefore falls back to the issued-forward CN ledger. It contains 34 issued rows, 16 matured rows, five matured loud rows, and only one independent matured loud episode. That episode contains risk-off; there are zero independent elevated-only episodes.

This sample cannot estimate five gross coefficients, discriminate elevated from risk-off sizing, validate `risk-off = ×0.62`, or support a promoted simpler policy.

## Product adjudication

The required capital-policy verdict is `INSUFFICIENT_INDEPENDENT_EPISODES`.

- Historical performance and crisis tables: diagnostic only.
- “Suggested size”: not supported.
- “Risk-budget reference”: not supported.
- `×0.62` as advice: not supported.
- “Half of normal”: not supported and numerically changes `0.62` to `0.50`.
- Supported authority: `DISPLAY_CONTEXT_ONLY`.
- Shadow policy: none earned.

No live `_GROSS` mapping, UI, `can_force`, Market State, ranking, selection, Portfolio execution, Prophet behavior, trade authority, or control plane is changed.
