---
workstream: WS:LIVE-ENTRY-RADAR
session: claude/rs-pullback-launch-phase1-20261007
model: sol
ended_because: blocked
mission: "Advance RS Pullback Launch Phase 1 through source census, reproducible admission/refusal, and offline input conformance; parent signal program remains incomplete."
state_before: "Research complete at macro@21e7ece49b682d65a63f73ba6045853aded782f0; implementation not started."
changed:
  - path: engine/entry_radar/replay/rs_pullback_launch_data.py
    what: "Pure complete-minute input adapter and source-owner census evaluation; no detector or authority registration."
  - path: scripts/entry_radar_rs_pullback_phase1.py
    what: "Offline reproducible census/input-frame entrypoint, no live-source or ledger writes."
  - path: research/live_entry_radar/rs_pullback_launch/PHASE1_SOURCE_CENSUS_2026-10-07.json
    what: "Pinned source and read-only production inventory/qualifier receipts."
  - path: research/live_entry_radar/rs_pullback_launch/PHASE1_ADMISSION_2026-10-07.json
    what: "Reproducible NOT_ADMITTED verdict with 29 named refusals."
verified:
  - claim: "The input adapter passes its initial conformance suite."
    command: "python3 -m pytest tests/test_entry_radar_rs_pullback_phase1.py -q"
    result: "23 passed, 38 subtests passed; unrelated existing temporary-directory cleanup warnings."
  - claim: "The actual source census does not support the commissioned market pilot."
    command: "python3 scripts/entry_radar_rs_pullback_phase1.py --census research/live_entry_radar/rs_pullback_launch/PHASE1_SOURCE_CENSUS_2026-10-07.json"
    result: "NOT_ADMITTED; 29 refusals; H1/H2/H3 NOT_TESTED; all authority false."
  - claim: "Existing deployed Terminal qualification was executed without source/data modification."
    command: "ingest.intraday_qualification.qualify_store on SPY/QQQ/SMH/MU 1m and SPY 5m; 2026-09-28 through 2026-10-05; cutoff 1791244800; as_observed; read-only process 61222."
    result: "Required 1m files missing; complete-grid SPY 5m control still has zero as-observed rows and pit_proven=false."
unverified:
  - claim: "A real immutable first-seen one-minute leader/pullback pilot can be constructed."
    what_would_verify: "Existing data owners supply retained 1m revisions with listing identity, basis, calendar and actual daily/incumbent receipts; rerun Phase 1."
  - claim: "Historical or prospective H1/H2/H3 edge."
    what_would_verify: "Admitted data, TrialLedger preregistration, strong B0 and controls/ablations, then prospective paired incumbent validation."
  - claim: "Source delivery and hosted integration acceptance."
    what_would_verify: "Exact candidate review and concluded required GitHub checks; this working checkpoint does not claim merge or production acceptance."
unresolved:
  - "Missing 1m archive and historical first-seen/revision lineage on the inspected canonical store."
  - "Per-row stale daily context and missing faithful historical Entry Engine input/output receipts."
  - "No real pilot, detector registration, calibrated probability, or production signal authority."
next_actions:
  - "Complete review and required CI of this offline Phase-1 candidate on its existing branch."
  - "Reconcile a bounded source-owner extension with incumbent minute-resolution/capture owners before any collector or live-path change."
  - "Obtain owner-qualified immutable inputs and rerun Phase 1 before baseline/outcome work."
do_not_redo:
  - "Do not rerun the completed broad research commission."
  - "Do not substitute 5m history or corrected-history backfills for true 1m historical first-seen evidence."
  - "Do not duplicate Macro #7274/#7275, Fable Terminal #784 performance work, or Terminal #814 intraday route changes."
  - "Do not register a detector, write TrialLedger/shared ledgers, let C4 fire, use F1, or grant rank/gate/size/order authority."
danger_areas:
  - "Bar end is not publication/receipt time; Terminal ET display epochs are not true UTC instants."
  - "Synthetic conformance is not a real market pilot or evidence of an edge."
  - "Fresh top-level daily publication does not refresh stale constituent rows."
---

## Current cumulative Phase-1 checkpoint — 2026-10-07

Operation: `rs-pullback-launch-phase1-20261007-sol-001`. Parent: `WS:LIVE-ENTRY-RADAR`.
Procedure: Mastermind `9a24ef2c4b27ac95a4d1f72f5eae1073657cd7c2`, skillpack 1.0.1/bootstrap 1.
Macro census `309f88c6c209bdc9fb611de0018fb619d9351b37`; fresh implementation base
`007e0cccbd06f089605ba122efc658f406043dd3`. Relevant Entry Radar/daily/incumbent source
is unchanged across that base movement. Terminal `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Phase-1 market-data verdict: NOT_ADMITTED. Parent MISSION_COMPLETE: false.**
The new adapter produces input frames only. No detector or label implementation is claimed.
The original research and proposed scientific gates below remain preserved; the current
[Phase-1 result](../../research/live_entry_radar/rs_pullback_launch/PHASE1_RESULT_2026-10-07.md)
owns the latest engineering/evidence disposition.

# RS Pullback Launch — Sol Implementation Handoff

**Parent research commission:** RS Pullback Launch / Intraday Low-Detection Intelligence  
**Research status:** COMPLETE  
**Parent program implementation status:** PHASE 1 — DATA NOT_ADMITTED; offline input implementation built, source acceptance pending  
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
