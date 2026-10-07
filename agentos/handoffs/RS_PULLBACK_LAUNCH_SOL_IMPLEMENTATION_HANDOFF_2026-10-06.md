# RS Pullback Launch — Sol Implementation Handoff

**Parent research commission:** RS Pullback Launch / Intraday Low-Detection Intelligence  
**Research status:** COMPLETE  
**Parent program implementation status:** NOT STARTED  
**MISSION_COMPLETE:** false for the total build program  
**Authority:** Chairman has asked Sol to take the completed research forward; this handoff itself grants no production/trading authority.

## Mission

Take the completed RS Pullback Launch research into engineering and empirical validation end to end.

The goal is to determine whether, among already-qualified relative-strength leaders in controlled pullbacks, Mastermind can detect a PIT intraday state in which relative performance / selling-pressure evidence improves before absolute price visibly reverses — and whether that state improves downside control, launch forecasting, or economic timing enough to justify product integration.

Do not assume the edge exists.

## Highest-authority starting points

1. Re-pin current protected `mastermindx-market-intelligence/Mastermind:docs/sol_skills/INDEX.md` and load required same-commit procedures.
2. Read the research package:
   - `research/live_entry_radar/rs_pullback_launch/RS_PULLBACK_LAUNCH_RESEARCH_2026-10-06.md`
3. Treat the research evidence pins inside that document as evidence anchors, not current admission.
4. Re-census current Macro and Terminal heads before any code change.

Persistence base observed when this handoff was saved:
`macro/main@309f88c6c209bdc9fb611de0018fb619d9351b37`.

## Core ruling

Build this as an **extension of existing Entry Radar / canonical entry evidence owners**, not a parallel entry engine.

Reuse:

- `engine/us_leader_pullback.py` for daily leader/pullback context;
- Entry Radar readings/events/detectors/live episode ledger;
- PIT observation construction and null law;
- TrialLedger / experiments registry;
- existing cost / replay infrastructure where semantics match;
- Prophet deterministic availability boundaries;
- Terminal intraday storage/qualification after current re-census.

Do not revive archived `bot/phase2.py` as an active owner.

## Research claims to keep separate

H1: incremental launch information.  
H2: lower remaining downside / better MAE.  
H3: net economic timing improvement.

Passing one does not imply the others.

## Immediate execution target

### PHASE 1 — DATA ADMISSION + PILOT EPISODE PANEL

Do this before UI, scoring or production wiring.

1. Re-census exact intraday data holdings and owner semantics.
2. Freeze a canonical 1m→15m/30m bar law with explicit `known_at`.
3. Establish identity, adjustment basis, session calendar, missing-bar and revision law.
4. Bind PIT daily leader/pullback context and incumbent Entry Engine inputs.
5. Construct a small complete pilot panel containing successes, failures, nonfires, missing inputs and ambiguity cases.
6. Implement PIT mutation tests — changing future bars or later corrections must not alter an earlier detector state.
7. Produce a coverage/refusal census and an admission verdict.
8. Stop before outcome-driven threshold tuning if the data plane is not admitted.

### Phase-1 DONE_WHEN

A fresh session can reproduce the pilot population, feature rows, clocks and labels from immutable inputs and every exclusion/refusal is named; OR the program has a defensible `NOT_ADMITTED` result naming the missing evidence.

## V1 research state model

`ELIGIBLE_LEADER → PULLBACK → EXHAUSTION → ARMED → PIVOT_FORMED → PIVOT_CONFIRMED → LAUNCH`

with transitions to:

`INVALIDATED | DISTRIBUTION | TREND_BREAK | EXPIRED`

Critical meanings:

- `ARMED`: attention / optional research probe only; reversal not confirmed.
- `PIVOT_FORMED`: fully completed 30m pivot exists; high/low are now fixed.
- `PIVOT_CONFIRMED`: a later completed observation crosses fixed pivot high + registered buffer.
- `LAUNCH`: outcome only; never feeds backward into the detector.

An unfinished 30m bar may be described as developing using completed 15m information, but its eventual 30m high/low/close are unavailable.

## Primary proposed labels

Let `E` be the prescribed entry-reference price and `A` the frozen volatility scale.

Primary 120m launch:

- upper barrier = `E + 1.0A`
- lower barrier = `E - 0.5A`
- label = upper reached before lower.

Primary downside:

`MAE_ATR = max(0, E - min(future_low)) / A`

Primary low-in label:

`MAE_ATR <= 0.25`

Low-in and launch stay separate.

## Required controls

- random qualified-leader timestamp;
- any pullback in a qualified leader;
- RSI turn;
- MACD-histogram turn;
- first green 15m;
- first green 30m;
- completed 30m pivot + break;
- common-MA pullback;
- faithful incumbent Entry Engine assessment.

Strong B0 must already include primitive stock, market and sector returns plus leadership, pullback geometry, location, time-of-day, volatility, liquidity, catalyst context and incumbent assessment. RS must earn incremental information over that baseline.

## Frozen proposed acceptance gates

Freeze before outcome access; do not relax after seeing results.

- H1 launch information: ≥2% relative Brier improvement over B0 + positive-effect evidence.
- H2 downside: ≥0.10 ATR mean-MAE improvement at equal coverage + adverse-tail guardrail.
- H3 economics: ≥0.10 common-budget R improvement per eligible episode, positive expectancy under doubled costs + tail guardrail.
- Stability: positive direction in ≥70% quarterly folds with adequate name/period diversity.
- Prospective review: ≥90 sessions with actual availability, latency and cost observations.

## Hard prohibitions

Do not:

- build a second lifecycle, event store, trial ledger, scheduler or notifier;
- grant rank/gate/size/order authority;
- reuse C4 as a firing detector;
- use reserved F1 as a shortcut;
- invent probabilities before calibration;
- create a 0–100 score first;
- require L2/L3 before L1/OHLCV incremental value is proven;
- infer “no news” from missing coverage;
- hindsight-select support/pivots;
- condition the study only on episodes that later confirm.

## Likely paths, subject to current owner recensus

- `engine/entry_radar/`
- `engine/entry_radar/replay/` or an adjacent versioned intraday-outcome namespace
- `research/live_entry_radar/rs_pullback_launch/`
- bounded research scripts under `scripts/`
- discriminating tests under `tests/`
- Terminal intraday qualification paths only if current source law confirms that owner.

## Total-program DONE_WHEN

The mission is complete only when:

1. the data/source law is accepted;
2. historical controls and ablations are complete;
3. claimed effects pass frozen gates;
4. prospective first-seen validation passes;
5. probability output, if any, is calibrated;
6. canonical owner integration is complete without authority widening;
7. all human/machine consumers read the same canonical evidence;
8. paired prospective evidence shows whether this improves the actual incumbent Mastermind decision process;
9. the existing decision/sizing owner separately admits any binding use.

If the edge fails, close the program with a falsification record. Do not force a signal into production.

## First response expected from the Sol implementation session

Recover current source, then immediately advance Phase 1. Return a current owner/collision census, exact research operation boundary, data-availability matrix, and the first concrete implementation/result — not another generic plan.
