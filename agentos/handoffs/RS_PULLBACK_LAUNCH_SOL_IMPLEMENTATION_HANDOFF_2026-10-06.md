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
  - claim: "The CLI binds imports to this repository even when a foreign package precedes an ambient root."
    command: "python3 -m pytest tests/test_check_script_import_pinning.py -q; actual CLI invocation with hostile engine decoy and repo root later on PYTHONPATH"
    result: "11 passed; decoy not executed; CLI admission output byte-identical. Conditional pin repaired without baseline or waiver changes."
  - claim: "The corrected code-CI step passes all 30 RS conformance tests and 27 existing frozen-panel tests."
    command: "python3 -m pytest tests/test_research_price_panel.py tests/test_entry_radar_rs_pullback_phase1.py -q"
    result: "57 passed, 85 subtests passed after six independent review findings were repaired; unrelated existing temporary-directory cleanup warnings."
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
  - claim: "Hosted source-delivery acceptance."
    what_would_verify: "Concluded required checks and merge status on the pull request for this branch; local passing tests and this evidence checkpoint do not imply production or scientific admission."
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

## Current delivery and next-source checkpoint — 2026-10-07

Observed at: 2026-10-07T08:35:06.650491Z. Parent `WS:LIVE-ENTRY-RADAR`; **MISSION_COMPLETE: false**.

Phase 1 is complete through its permitted negative result. The overall market panel remains **NOT_ADMITTED**, H1/H2/H3 remain **NOT_TESTED**, and every authority flag remains false. The historical Phase-1 event and research contract remain below. The current source-delivery evidence and next actions are recorded here.

### Delivered retention component

[Macro #8571](https://github.com/mastermindx-market-intelligence/macro/pull/8571) merged the original Phase-1 result as `47a3a248ba9228b498376d2bdc170fd61e38dac0`. `PHASE1_ADMISSION_2026-10-07.json` remains exact at SHA-256 `a4e00a5c191917dc8c64fb74ca3348827ab9bd47d9ad8a03a1130a50fde36e9f`: 29 refusals and no market pilot or outcome claim.

The source-retention slice is delivered in [Macro #8581](https://github.com/mastermindx-market-intelligence/macro/pull/8581), merge `45dd4e26166f8676f548631f24978580b4d8a723`, and [Terminal #840](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/840), merge `d21fa05ad8d934bb4d70731587ab2df64a28c194`. Hosted checks, reviewed source identities, Macro installation and the canonical Terminal build were verified. Terminal deployment finished at 06:38:17Z; at 06:39:02Z the deployment identifier, origin HTML and public HTML all matched the accepted Terminal commit and served HTTP 200.

At 06:41:04Z, the actual installed producer/helper and Macro reader/harness passed all 12 injected conformance assertions through atomic temporary stores. The complete installed receipt is retained in Macro #8581, SHA-256 `ac1ec230ce6ba56d0f24a05e8fb00bea36f94a5cb3737ec80ea10d58d59cfc32`. It establishes installed engineering behavior at that observation time. It enrolled no runtime cohort, fetched no provider bars, and did not admit an adjustment basis or market pilot. The original synthetic conformance artifact remains historical and byte-identical.

### Calendar and identity delivery

[Calendar PR #8602](https://github.com/mastermindx-market-intelligence/macro/pull/8602) is ready for review at `2f5821fbbdde835bc013b52d03337d10edeb7d20`, with hosted delivery CI running. It binds the exact Terminal session projection through an actual single bounded read and preserves its original clock/capsule for replay. Invalid visible calendar input refuses only the affected candidate. The first hosted run found a real CI selection regression; the correction preserves fresh main's price-panel/PTSE suites and uses a separately curated calendar test job. The local differential gate passed with zero introduced or inherited violations, keeping the 132-job content-probe limit unchanged. Semantic review, CI-scope review and final proof freeze passed. Calendar merge and installed-path proof remain pending at this checkpoint.

[Native identity PR #8607](https://github.com/mastermindx-market-intelligence/macro/pull/8607) remains **DRAFT**, without merge-on-green, at `7e799fdca2efd9bab7c927fda44ec18ed7a515ff`. Source and actual artifact review passed for draft delivery. Only MU received a native binding; SPY/QQQ/SMH remain explicit canonical-owner refusals. The original four native reference observations and actual owner-input clock are retained. A CI fixture that dropped the three new native evidence columns was repaired and independently verified; canonical time guards remain intact.

The native draft has a binding data blocker: current official listing inputs yield **718 total / 707 resolved / 11 unresolved** against the unchanged limit of 10. Both affected data gates remain red. An untouched current-base builder reproduces the count. PSKY is the additional unresolved name; a fresh official-directory diagnostic also found it absent, which is not proof of delisting. Do not raise or skip the cap, replace the gate with baseline equality, restore stale artifact counts, force a binding, or merge this draft because code CI passes. Exact input/artifact hashes and the diagnostic receipt are in the PR. Preserve the separate FISV owner's scope.

### Current declaration and basis-refusal slice

Operation `rs-pullback-launch-basis-binding-20261007-sol-005` uses protected Mastermind `1fc040f7343dde73fec3556dd3bf9bc8c1b18129`; the prior retention/calendar/reference operations retain their original protected pin `ee120e80f5d5e0344c453dd7cbf4108b9c429b38`.

The current candidate extends the existing Terminal capture envelope and Macro decoder. It preserves sealed v1 prefixes, records v2 response adjustment declarations, and retains declaration changes even when OHLCV values are equal. A complete incompatible response remains evidence while the existing chart stays unchanged. Suppressed captures do not create new minute revisions. Terminal's four-file producer passed 325 affected/D0 tests and independent real-writer review, and is committed as `29224303b192bf70c2692227239a62cde1ee0c6b` in [draft PR #843](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/843). Its hosted checks are running; its producer release remains held for the compatible Macro reader. Macro's source passed 165 tests plus 85 subtests. Independent review reproduced and closed future-version visibility and malformed outer-schema failures; all 19 joint conformance checks reproduce exactly against the committed Terminal source. The accepted new proof SHA-256 is `8fbb51cc41e9acf7bb70be23cd4d86d030dfa15c42b38c2d1e3d9ff7aaa4ed49`. Their isolated branches are both `claude/rs-pullback-basis-v2-20261007`; Macro prepares against the immutable reviewed calendar dependency above.

The Macro candidate removes scalar basis inheritance. Every retained Terminal row carries null basis and a typed `TERMINAL_BASIS_UNPROVEN` refusal; identifiable source rows stay unavailable even if a caller overwrites their scalar label. No basis-file reader, invented owner-attestation schema or positive admission method is introduced. The new `SOURCE_BASIS_DECLARATION_CONFORMANCE_2026-10-07.json` distinguishes immutable raw evidence and source unavailability from separate direct-input synthetic aggregation controls. A response flag, self-sealed metadata, and a separately fetched latest factor table do not establish a shared adjustment vintage.

The compatible reader checks envelope integrity, seals, sequence and capture IDs immediately, while payload-version and ordering semantics apply only after explicit receipt enrollment and visibility. Thus an intact unsupported future record preserves every earlier raw row, revision identity and full frame; it refuses when visible. The CI delivery repair transfers the entire bridge suite to the existing exclusive calendar job, preserves other price-panel/PTSE suites and covers the 12-file literal dependency closure with 17 explicit paths. Independent scope/freeze review passed. Full differential gate process 55503 passed with zero introduced or inherited findings; the content probe remains 132 jobs / 5,415 seconds / 10 packs within unchanged limits.

### Authorized continuation

Finish the calendar's required hosted checks, merge the reviewed head, and verify the installed reader against the installed projection. Complete current-main integration and hosted delivery checks for the independently accepted declaration slice. Deliver the compatible Macro reader before any Terminal v2 producer deployment, then run paired installed conformance with injected transport and temporary files. Keep the native identity draft blocked until the existing owner resolves its real data gates.

The next source implementation is active as `rs-pullback-launch-split-evidence-20261007-sol-006`, under the same protected `1fc040f7343dde73fec3556dd3bf9bc8c1b18129`. Source inspection at Macro `d69dd101c3cc2d2f430332ad66bad185ed63e4f8` established the concrete owner path: opt-in split-history acquisition alongside CorpActions, a family adapter using the existing `market_memory_source_kernel` object/receipt/generation/HEAD primitives, and one row in the existing dataset registry. The worker has a five-path source/test/document claim and must establish clean custody at fresh main. It has no provider, credential, production-store, schedule, commit or push authorization. The new opt-in route is explicitly `https://api.massive.com/stocks/v1/splits`; the existing close-pass split/dividend endpoints, configuration and consumers remain unchanged. Preserve exact decimal tokens, actual nanosecond clocks, complete-empty and failed attempts, and A/B/A acquisition history. Use the generic kernel; do not copy SPY's daily identity, availability policy or content-only capture identity.

Current Terminal captures request `adjusted=true`. A separately fetched split snapshot cannot prove the factor vintage of those values. Positive basis admission therefore still requires a separately reviewed unadjusted capture path through the existing Terminal owner or actual provider-documented response-atomic vintage evidence. Do not invert old adjusted prices with new factors, introduce another catalog, or accept a caller's self-sealed positive attestation. Split endpoint and convention facts are grounded in [Massive's split API](https://massive.com/docs/rest/stocks/corporate-actions/splits) and [split coverage/migration guidance](https://massive.com/knowledge-base/article/does-massive-support-normal-and-reverse-splits). This bounded slice retains evidence; reconstruction, provider equivalence and live admission remain separate gates.

Other open admission dependencies remain: the complete pilot/nonfire/failure population, actual first-seen 1m cohort/cadence/history, stable benchmark/sector identity, PIT daily leader/pullback receipts, and the faithful `engine/entry_signal.py::assess` incumbent path used by `scripts/build_stock_library.py`. Catalyst coverage stays unknown where evidence is incomplete. The 900-second finality rule still makes the newest nominal 15-minute window unavailable; the 4096-attempt retention cap is not a 90-session accrual guarantee. Global source licensing is already closed by the operator-confirmed `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md` and must not be reopened without new evidence.

No outcome tuning, detector authority, score, probability, UI admission, new ledger, scheduler, publication owner or decision engine is authorized by these component receipts. Preserve the negative result and continue the next safe existing-owner dependency in the same session.


## Current cumulative Phase-1 checkpoint — 2026-10-07

Operation: `rs-pullback-launch-phase1-20261007-sol-001`. Parent: `WS:LIVE-ENTRY-RADAR`.
Procedure: Mastermind `9a24ef2c4b27ac95a4d1f72f5eae1073657cd7c2`, skillpack 1.0.1/bootstrap 1.
Macro census `309f88c6c209bdc9fb611de0018fb619d9351b37`; fresh implementation base
`007e0cccbd06f089605ba122efc658f406043dd3`. Relevant Entry Radar/daily/incumbent source
is unchanged across that base movement. Terminal `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Phase-1 market-data verdict: NOT_ADMITTED. Parent MISSION_COMPLETE: false.**
The new adapter produces input frames only. No detector or label implementation is claimed.
Independent review of source candidate `1c76e954f74a8cf74c3b8e7fce7a0d3b81f49d6a` found
six bounded receipt/causality defects; all were repaired with seven added regression methods.
The exact code-CI step passes 57 tests (30 RS + 27 frozen-panel). The final source head and
hosted checks belong to this branch's pull request; this checkpoint preserves the evidence
frontier without claiming a future merge. The current immutable census includes an explicitly
identified caller-bound qualification-window envelope, preserving original owner-output fields.
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

## Continuation: retained source observations (2026-10-07)

Operation: `rs-pullback-launch-source-retention-20261007-sol-002`.

The preceding Phase-1 checkpoint is historical. Its delivery completed in [Macro PR #8571](https://github.com/mastermindx-market-intelligence/macro/pull/8571), squash `47a3a248ba9228b498376d2bdc170fd61e38dac0`. The concluded hosted gate and merged-file identity were verified. Phase 1 closed through its permitted negative result: **NOT_ADMITTED**, 29 refusals, H1/H2/H3 **NOT_TESTED** and all authority false. Its admission artifact remains byte-identical.

The next source-retention slice uses Terminal's existing producer and per-symbol atomic store. [Terminal PR #840](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/840) adds an explicit bounded 1m capture option, immutable capture-prefix receipts and retained corrections/failures. Existing scheduled defaults remain unchanged. Macro's new `engine/entry_radar/replay/terminal_minute_observations.py` reads actual bytes, creates an actual owner-read receipt and decodes eligible observations for an explicitly supplied decision cutoff. The existing Phase-1 selector remains the revision and aggregation owner.

Recover this slice through:

- [Reader/source contract](../../research/live_entry_radar/rs_pullback_launch/SOURCE_RETENTION_READER_CONTRACT_2026-10-07.md).
- [Exact local synthetic conformance receipt](../../research/live_entry_radar/rs_pullback_launch/SOURCE_RETENTION_CONFORMANCE_2026-10-07.json).
- Reproducer: `scripts/entry_radar_rs_pullback_source_retention_check.py --terminal-source /absolute/path/to/mastermind-terminal`.
- Focused suite: `tests/test_entry_radar_terminal_minute_observations.py`, added to the existing frozen-panel/RS code-CI step.

The joint proof uses the real producer, atomic temporary file, bounded reader and canonical selector with injected transport and clocks. It checks A/B/A, fractional volume, entire earlier-frame invariance, future malformed semantic isolation, late-first-read conflict and partial-failure refusal. The contemporaneous latest 15m/full frame stays unavailable under the unchanged 900-second finality rule.

Independent review exposed the omitted-cutoff path, enabled empty-file recovery, contradictory pagination identity and automatic HTTP redirects. Their discriminating regressions and final source identities are recorded in the paired delivery evidence. Review, hosted CI, merge, deployed source identity and market admission remain separate gates; this source checkpoint does not claim an unrecorded delivery result.

No provider fetch, runtime cohort enrollment, new schedule, outcome experiment or owner authority is established by the synthetic receipt. Before actual accrual, bind cohort/cadence/finality/capacity through the existing source owner and attach the existing operator-confirmed `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md`, which already closes the global licensing gate for minute aggregates, research and archival retention. The 4096-attempt cap is not a 90-session guarantee. Continue by resolving the next concrete existing-owner admission dependency: stable listing identity and basis, calendar law, actual daily/incumbent receipts, or actual first-seen observation custody. Preserve nonfires, failures and all remaining refusals. The parent program is incomplete.
