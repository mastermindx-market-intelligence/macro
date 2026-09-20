---
key: PROPHET-PHASE21-TWO-DEFECT-MECHANISM-AND-PHASE22-PROSPECTIVE-TEST
claim: >
  The outcome-contaminated V3 forensic evidence supports two distinct mechanisms
  requiring prospective validation: consumed remaining opportunity at entry and
  hidden-fragility damage during the hold; existing C2 plus same-cut C4 d2.turn
  can test the fast-cycle mechanism without minting another detector.
falsifier: >
  Re-read the Phase-21 synthesis at SHA256
  37b5ac78bd93c6d8ebc9b7effb260eb00c0fb77ef8c3259ecd29c231bd124ed6
  and current Entry Radar C2/C4 source; this discovery is falsified if Phase-21
  does not preserve the two mechanisms separately, or C4 d2.turn is not a
  same-cut stratification-only observation on the primary C2 population.
so_what: >
  Do not fit another threshold on the 209 V3 development episodes. Preserve the
  frozen Phase-22 prospective C2 x C4 test, retain all future false starts and
  losses, and keep rates/breadth as prespecified context interactions rather than
  promoting them into a Prophet gate.
kind: architecture
verified_at: 2026-09-19
verified_by: >
  Phase-21 synthesis SHA256 37b5ac78bd93c6d8ebc9b7effb260eb00c0fb77ef8c3259ecd29c231bd124ed6;
  engine/entry_radar/challengers.py C2/C4 source at macro f95b2cc5807fd850c2378b4ad6e938d0e735d2a0;
  Phase-22 prereg carrier sol/prophet-phase22-fast-cycle-regime-prereg-20260919.
scope:
  - macro
  - WS:PROPHET-US-V4-RECOVERY
  - WS:LIVE-ENTRY-RADAR
  - WS:EVAL-OS-MEASUREMENT-LAW
  - research/prophet_v4/
confidence: probable
---

## Discovery

The already-used V3 forensic population should no longer be asked to choose another threshold.
It supports two mechanism hypotheses that require a new prospective epoch:

1. **remaining opportunity at entry** — recent severe losses are associated with already-consumed
   opportunity; the large-winner tail shows fresher 2D reacceleration than the severe-loss tail,
   while daily overbought/age alone does not separate safely;
2. **hidden fragility during the hold** — rising real yields and weakening equal-weight breadth
   line up with later-hold damage even when SPY appears comparatively resilient.

The mechanisms are separable. A slow confirmation can arrive after a useful move even in a benign
market; a sound entry can also be damaged by an adverse regime transition after entry.

## Development evidence boundary

Studio Phase-21 synthesis:
`/Volumes/Mastermind/research/US_Prophet_Phase21_FAST_SLOW_REGIME_SYNTHESIS.md`
SHA-256:
`37b5ac78bd93c6d8ebc9b7effb260eb00c0fb77ef8c3259ecd29c231bd124ed6`.

That analysis is development-visible and outcome-contaminated. It does not validate a live filter.

Notable development observations retained as motivation only:
- recent V3 damage worsened materially after the shorter holding window;
- date-block outcome deterioration co-moved with realized real-yield pressure and weak RSP/SPY;
- Risk Radar's current top-level state was too late/coarse to explain or prevent most V3 damage;
- blanket daily stretched/overbought vetoes retain both major winners and severe losers;
- winner-tail 2D reacceleration was materially fresher than severe-loss-tail 2D reacceleration;
- mechanically entering old 1D/2D/3D crosses improves selected-candidate means while also creating
  many new catastrophic paths, proving that "earlier" without a fresh-valid opportunity is not the fix.

## Existing-owner composition

No new signal family is required for the first clean test.

- `C2_1D_TURN@1` is the existing frozen 1D-turn expert.
- `C4_MTF_TURN@1` is already a stratification-only same-cut 2D/3D snapshot on the primary C2
  population and is structurally unable to fire.
- Existing W5/QLedger owns prospective outcomes.
- B3 will own orthogonal maturity; B4 will own Entry Availability when built.

Current implementation gap: C4 context is published in the live Radar payload but is not a
directional event and is not presently durable inside the W5 live-forward path. The prospective
test therefore cannot start until the owner-approved secure transport/read model preserves that
same-cut context without changing immutable C2 event identity.

## Phase-22 decision

Freeze one prospective validation family:
`prophet_phase22_fast_cycle_regime`.

Primary fast-cycle question: future C2 events with same-cut `C4.d2.turn=true` versus source-qualified
`false` at H10, preserving every false start and loss.

Prespecified regime interaction: compare that fast-cycle contrast between:
- prior-session hidden fragility = 10y real yield rising over five completed sessions AND
  RSP underperforming SPY over those five completed sessions;
- relief/broadening = real yield non-rising AND RSP not underperforming SPY.

Same-session closing information is forbidden as decision context. Mixed/missing regime states are
diagnostic rather than reassigned.

Exact scientific contract:
`research/prophet_v4/US_PROPHET_PHASE22_FAST_CYCLE_REGIME_PROSPECTIVE_PREREG_2026-09-19.md` and
`research/prophet_v4/us_prophet_phase22_fast_cycle_regime_prereg_v1.json`.

## Holds

- LER-C1 secure private spool remains blocked on its existing credential/proof gate.
- LER-C3 final prospective reconnect depends on C1.
- TrialLedger registration is deliberately not attempted while open Tactical R1-B PR #7274 owns
  `data/trial_ledger.jsonl`.
- PR #7418 is a separate nominal-rate x leader-reset prereg and is not amended by Phase 22.
- No C2/C4 hash, Prophet rank, entry gate, size, trade or management rule changes.

## Do not redo

Do not rerun the 209-V3 threshold hunt to choose a 2D age, daily oscillator level, off-high cutoff,
stop, or hold cap. Use the prospective event population and the frozen existing-owner features.

Do not create another forward ledger, event store, qledger, regime scorecard or early-entry engine.
