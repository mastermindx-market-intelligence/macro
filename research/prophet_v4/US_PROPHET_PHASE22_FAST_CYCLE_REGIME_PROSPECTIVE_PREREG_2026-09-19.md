# US Prophet Phase 22 — prospective fast-cycle × hidden-fragility preregistration

**Frozen:** 2026-09-19
**Operation:** `prophet-phase22-fast-cycle-regime-prereg-20260919-sol-001`
**Parent:** `WS:PROPHET-US-V4-RECOVERY`
**Expert owner:** `WS:LIVE-ENTRY-RADAR`
**Evaluation owner:** Evaluation OS / QLedger / existing Entry Radar W5 ruler
**Source base:** `macro@f95b2cc5807fd850c2378b4ad6e938d0e735d2a0`
**Protected procedure:** `Mastermind@9e796168b467c17d9853f139c4e4a6ccdf3a3a87`, Skillpack 1.0.1
**State:** FROZEN BEFORE PROSPECTIVE OUTCOME READ / RECORDS ONLY / ZERO TRADING AUTHORITY

## 1. Why this exists

The already-used US Prophet forensic set is development evidence, not an untouched validation surface.
The Phase-21 synthesis on Studio is SHA-256
`37b5ac78bd93c6d8ebc9b7effb260eb00c0fb77ef8c3259ecd29c231bd124ed6`.
It supports two interacting hypotheses without validating a new rule:

1. **remaining-opportunity defect at entry** — V3 often arrived after useful price progress;
   the large-winner tail had materially fresher 2D reacceleration than the severe-loss tail,
   while a blanket daily-overbought veto was contradicted by winners;
2. **hidden-fragility / management defect after entry** — rising real yields and weak
   equal-weight breadth coincided with materially worse later-hold outcomes even while SPY
   looked comparatively resilient.

Those observations may select this prospective question. They may not be quoted as validation
of the question.

## 2. One existing event population, no new detector

The validation population is every **future LIVE_FORWARD primary C2 event**
`C2_1D_TURN@1` after the experiment start receipt.

C2 is already the frozen 1D-turn expert. No new 1D signal is created.

The sole primary fast-cycle conditioner is the already-frozen, stratification-only C4
snapshot computed at the exact C2 candidate cut:

`C4_MTF_TURN@1.d2.turn`

C4 remains structurally unable to fire. It gets no QLedger family and no rank/gate/size/trade
authority. Its `d2.turn` value is an owner-native strict confirmed-2D StochRSI K×D bullish
cross observed at the same decision cut as C2.

All C2 events are retained, including false starts, later failures, never-confirmed cases,
missing context and losses. No outcome-selected candidate removal is permitted.

## 3. Required prospective start boundary

The experiment starts only after ALL of the following are durable:

1. LER-C1 private evidence transport is accepted on the canonical Radar path;
2. LER-C3 has proven one real RTH event through private spool -> existing
   `forward.parquet` -> existing QLedger;
3. the current C2 event's same-cut C4 snapshot is preserved through that existing path
   by an owner-approved transport/read-model receipt **without mutating the immutable
   C2 event identity**;
4. this exact prereg/config hash is registered in the existing TrialLedger before the
   first target outcome is opened;
5. a `live_forward_start` / experiment epoch is recorded. Nothing earlier may later be
   relabelled prospective.

Current source does not satisfy item 3: C4 is present in the live payload but is not a
directional event and is not registered by W5. This document authorizes no C3 implementation;
it freezes the future measurement requirement.

## 4. Q1 — primary fast-cycle question

**Question:** among future C2 1D-turn events, does a simultaneous confirmed 2D bullish turn
identify materially better remaining opportunity than C2 events without a simultaneous 2D turn?

Arms:
- `D2_TURN_NOW`: C4 `d2.turn == true` at the C2 decision cut;
- `D2_NOT_TURNING_NOW`: C4 `d2.turn == false` and C4 is source-qualified;
- unavailable C4 is retained in the census but excluded from the two-arm effect and reported
  separately. Missing never becomes false.

Primary outcome: existing W5 H=10 trading-session `excess_net`.

Primary estimand: mean-within-decision-date arm difference,
`D2_TURN_NOW - D2_NOT_TURNING_NOW`, then decision-week block bootstrap.

No cross-age threshold, StochRSI level threshold, off-high threshold or price-return threshold
may be tuned after outcomes.

## 5. Q2 — prespecified hidden-fragility interaction

The regime hypothesis is tested as an interaction, **not** as a candidate gate.

Only information available before the event decision may enter the regime cell.

Decision-time context:
- **real-yield impulse:** latest qualified 10y TIPS real-yield observation available before
  the event, compared with its value five completed market sessions earlier;
- **breadth divergence:** RSP/SPY close-to-close relative return over the five completed
  sessions ending at T-1;
- IWM/SPY and XLI/SPY are fixed diagnostics only.

Primary context cells:
- `HIDDEN_FRAGILITY`: 10y real-yield impulse > 0 **and** RSP/SPY prior-5 < 0;
- `RELIEF_BROADENING`: 10y real-yield impulse <= 0 **and** RSP/SPY prior-5 >= 0;
- mixed/unavailable states are retained and reported, not reassigned.

Same-session closing data are forbidden as decision-time inputs. If a real-yield observation
lacks historical availability/known-time support, it is unavailable for the as-observed cell.

Primary Q2 estimand is the difference-in-differences:

`(D2_TURN_NOW - D2_NOT_TURNING_NOW)_HIDDEN_FRAGILITY
 - (D2_TURN_NOW - D2_NOT_TURNING_NOW)_RELIEF_BROADENING`.

A negative value would mean the fresh-2D advantage is smaller in hidden fragility; a positive
value would mean it is larger. Direction is not assumed in advance.

## 6. Slow-confirmation mechanism, kept separate from returns

For every prospective C2 event, preserve the later B3 maturity path when source-qualified:

- time from C2 known time to `EARLY_CONFIRMATION`;
- time to `CONFIRMED`;
- never-confirmed / failed-to-trigger / decayed outcome where the owner can prove it;
- availability remains a separate B4 axis and is never inferred from maturity.

These are mechanism diagnostics, not entry permissions.

## 7. Floors and one-shot look law

Reuse W5's established confirmatory floors for every arm used in a verdict:

- >= 30 episodes;
- >= 12 distinct decision months;
- effective-N of distinct names (1/HHI) >= 8.

No return/statistic peek before the applicable floor. Operational accrual counts and
missingness may be viewed.

At the first qualified read, use 5,000 decision-week block-bootstrap resamples with seed
20260919. Report date and name effective-N. Overlapping events from the same name/date are not
treated as independent draws.

FIT/TEST reuse is not applicable to this genuinely forward epoch. If a second temporal validation
split is later required, it must be preregistered before the first primary outcome read; this
carrier cannot create it retrospectively.

## 8. Economic guardrails and diagnostics

The primary verdict is Q1 H10 `excess_net`. Q2 is a separately budgeted confirmatory
interaction.

Fixed diagnostics, never substitutes for the primaries:
1. H10 absolute net return;
2. H5 excess/net return;
3. false-start rate;
4. severe-loss incidence (<= -10%);
5. large-win incidence and large-winner payoff contribution (>= +10%);
6. MAE/MFE and time-to-positive;
7. C4 `d3.turn` and `recent_washout` states;
8. B3 slow-confirmation timing/failure path.

Any future actionable policy must show loss reduction **and** retained large-winner economics
after costs; a higher hit rate alone is insufficient.

## 9. Multiplicity / no-rescue contract

Trial family: `prophet_phase22_fast_cycle_regime`.

Before the first target outcome read, the existing TrialLedger must register one declared budget
covering exactly:
- Q1 fast-2D H10 primary;
- Q2 hidden-fragility interaction;
- the eight fixed diagnostics above.

No additional outcome-conditioned cells, alternative thresholds, alternate lookbacks, tenor
substitutions, detector subsets or horizon rescues may be added after results are visible.
A future amendment requires a new prospective epoch.

The TrialLedger is **not modified in this carrier** because open Tactical R1-B PR #7274 currently
owns `data/trial_ledger.jsonl`. Collision resolution and prefix preservation precede registration.

## 10. Existing-owner boundaries

- Radar owns C2/C4 facts and immutable expert identity.
- LER-C1/C3 own private transport and W5 prospective durability.
- QLedger/Evaluation OS own grading.
- B3 owns lifecycle/emergence/maturity projection.
- B4 will own deterministic present Entry Availability when built.
- Rates source owner supplies real-yield observations/clocks.
- market-data owner supplies SPY/RSP/IWM/XLI completed-session prices.
- D5/catalyst/thesis evidence stays orthogonal and all authority false in this experiment.

Do not modify PR #7418. It is a separate pre-outcome **nominal-rate × leader_reset** construction.
Do not modify Tactical R1-A/R1-B or create a new Radar event store, evaluator, ranker, regime
scorecard or Prophet gate.

## 11. Interpretation ceiling

A supportive Q1 result earns a separate strategy-policy/B4 research proposal; it does not make
`d2.turn` a gate.

A supportive Q2 result earns a separate prospective regime-conditioned management/availability
proposal; it does not make real rates or breadth an automatic veto.

A null/adverse result closes the tested construction without being rewritten around a different
threshold.

No output from this experiment may automatically rank, gate, size, originate, add, trim or exit a
position.

## 12. Pre-outcome falsifiers

Repair or abandon this experiment before outcomes if:
- C4 context cannot be bound to the exact immutable C2 event/decision cut;
- C4 is recomputed with later bars rather than preserved at event time;
- a same-session rate/close leaks into the decision-time regime state;
- missing context becomes zero/false/calm;
- C2 event identity or outcome changes because context is attached;
- the TrialLedger family collides with an existing registered family;
- a second W5 store, event plane, qledger or scheduler is introduced;
- the implementation would require changing C2/C4 detector hashes merely to observe context.

Until the start boundary in §3 is met, the only truthful state is
`FROZEN_WAITING_FOR_PROSPECTIVE_SOURCE`.
