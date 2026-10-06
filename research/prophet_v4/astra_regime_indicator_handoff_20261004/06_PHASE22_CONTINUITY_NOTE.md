# 06 — Phase-22 continuity note (no outcome read)

Program: prophet-astra-ceo-fable-20261004-001 · Seat: Fable (Claude Code session f273dd7d) · Written 2026-10-04.

## What this note is

The wave-2 deliverable "Phase-22 continuity note (no outcome read)" from chapter 03 §4. It records how the
Astra → Fable program relates to the US Prophet Phase 22 prospective preregistration
(research/prophet_v4/US_PROPHET_PHASE22_FAST_CYCLE_REGIME_PROSPECTIVE_PREREG_2026-09-19.md) and states, once, what
this program may and may not say about it. It contains no return, statistic, or outcome of any Phase-22 arm.

## Phase-22 state as read on 2026-10-04

- Prereg §3 start boundary: six durable conditions (LER-C1 transport, LER-C3 real RTH event, same-cut C4 preservation
  without mutating the C2 identity, a source-qualified DFII10 go-forward clock, prereg hash registered in the TrialLedger,
  a recorded `live_forward_start` epoch). The prereg itself records that condition 3 is not met.
- Operational evidence viewed (allowed by §7): `data/trial_ledger.jsonl` rows matching Phase-22 identifiers = 1;
  rows matching `live_forward_start` = 0
0. No accrual counts or missingness beyond that were inspected.
- Truthful state per prereg §12: **FROZEN_WAITING_FOR_PROSPECTIVE_SOURCE**. Nothing done in this program moves it.

## What this program did NOT do (binding)

1. It did not read, compute, or peek at any Phase-22 arm, return, or statistic. Wave-1 lanes operate on
   FINAL-VINTAGE, survivor-selected stores and are retrospective by construction (chapter 03 §6); nothing from them can be
   relabelled prospective (prereg §3 item 6).
2. It did not touch the Phase-22 conditioner. The conditioner is the same-cut confirmed 2D **StochRSI** turn
   (`C4_MTF_TURN@1`). B1's "2D" variants are RSI-MACD cascades on 2-session bars with no StochRSI and no same-cut
   binding; they are a different object and no B1/C2 number describes the Phase-22 conditioner.
3. It did not alter the C2 event identity, the C4 detector, the TrialLedger, the W5 store, or any scheduler
   (prereg §12 falsifiers remain untriggered by this program).
4. It did not register a second temporal split or a new family in the TrialLedger.

## What this program hands to the Phase-22 owner (context only, no action implied)

- **Warm-up landmine** (`DSC:CANON-RSI-MACD-IS-NOT-THE-SERVED-INDICATOR`): engine.canon and the served path agree
  only after ~400 sessions. Any C4 snapshot computed through engine.canon rather than preserved from the served payload
  would differ at the start of a name's history. Phase 22 already requires preservation at event time (§12 bullet 2);
  this discovery is a second, independent reason for that rule.
- **Memory-direction correction** (`DEC:B1-MEMORY-FACTOR-DIRECTION`): if a future Phase-22 extension matches smoother
  memory across grains, k > 1 shortens memory; the matched constants are 1/2, 1/3, 3.
- **Rotation-state controls** (lane C1): a daily leadership-persistence variable with its AR(1) and leak gates.
  Whether it may serve as a Phase-22 covariate is a preregistration question for the Phase-22 owner, not a finding here.

## Boundaries that continue to bind after this program closes

- Phase-22 outcome reads happen only at the §7 floors (≥30 episodes, ≥12 decision months, effective-N ≥ 8) with the
  §7 bootstrap (5,000 decision-week blocks, seed 20260919), by the Phase-22 owner, on the prospective epoch.
- A later program that wants Phase-22 to consume any W1/W2 conditioning table must preregister that before the first
  qualified read; this note creates no such registration.
