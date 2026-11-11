# MACD continuation: replay inputs repaired, calendar contamination reproduced

## Outcome and scope

The parent study remains PARTIAL. Its job is to distinguish price-MACD versus RSI-MACD mechanisms, 1D/2D/3D/weekly holding and exit policies, repair states, breadth/sector context, and incremental selection value. This continuation repairs a required measurement dependency; it does not turn infrastructure into an accepted Prophet upgrade.

Existing PR: #7177, `sol/macd-cycle-research-20260915-c3`, starting at `46403f4d42330f9e903b52e2fd7cd48ca54bfe61`. Protected Skillpack pin: Mastermind `bf843961c0e1b5bd45fa481f0138c71f2a87d4e2`; compatible INDEX and all five required companions loaded from that revision, byte-equal to the previously loaded procedures. Macro source comparison: `2801ae5209e3473e3446da3d2f5a44dd2f742151`; incumbent replay blob `785b91613b347eade7dedac04b56bfb67956100a` remains unchanged there.

Explicit Chairman continuation supplies research intent, not trading authority. Executive OS retains lifecycle/admission, Macro Agent OS continuity, GitHub implementation/evidence, and existing Evaluation/TrialLedger grading/accounting. No worker, Job, watcher, model/provider call, new registry, replay framework, clock service or live trading authority was created. Direct-work reasons remain PRINCIPAL_JUDGMENT and CRITICAL_PATH_SHORTCUT.

## Canonical replay repair

`prepare_reconstruction_tree` now restores missing declared ticker files from the pinned historical Git commit, never from today's revised history or a later-only ticker population. Existing historical rows remain authoritative; only the missing tail is appended through the declared pass ceiling. Corrupt or unavailable required historical blobs refuse. The restoration is idempotent and its provenance is carried through both passes into the existing final harness receipt.

A new two-stage test exposed an additional transition defect: after control-time truncation, an unchanged Git blob could prevent the replay pass from restoring its next session. The owner now also considers the working frame's endpoint. Source-object equality is not equality with a truncated working frame.

The existing fence/cache key now includes actual price-file SHA256 values. The tested same-endpoint price corrections now produce different keys. This is price-cache repair, NOT proof that every nonprice input, source version and wall-clock dependency is represented in the board cache.

Final replay source SHA256: `1cd6aaee24b837df431dffa96286d282f9eee19f5978ef42a4fb5ea521f0740d`.

## Verification

Four original regression cases were observed failing before the original edits. This continuation added six boundary cases and two integration cases. The two integration cases separately failed before their fixes: missing next-session tail, and lost restoration provenance in the pipeline result/receipt. The combined replay suite then passed **199 tests**, including 12 new input/cache cases and the existing 187 replay/alpha cases. Evidence and exact source hashes are in `replay_input_repair_20260916_r2/` beside this report; host receipts remain under the existing study root.

A real-input, benchmark-only proof used the existing owner to restore historical SPY through July 14 and advance it to July 15 from the SAME Git source. All **8,421 rows** match the pinned historical frame; exactly July 15 was appended on the second pass; repeating the operation rewrote nothing. Source SHA256 `583e61bfc184b349c8dd2bfe4df6971ac4e214a793212b5e0dcc7993c5961712`; output SHA256 `cf3edbb520bc4360b200ac08ad10a3cd801639ee44ce189073357574e7116c46`. This is real input-preparation proof, not a complete board-fidelity run.

Separately, the retained failed control's SPY and VIX frames match their pinned historical values through July 15: zero changed close values over 8,421 and 9,202 common rows respectively. Their different parquet byte hashes do not establish revisions to the in-scope historical values; only the frames through the declared cutoff were compared.

## Exact archived clock experiment

The read-only probe executes only `_next_monthly_opex_days` and `current_risk_overlay` extracted from `build_stock_library.py` at `ff745b1ab54256b0188688cc5815e6675e4edef5`. It uses that revision's literal FOMC calendar, unchanged retained VIX/regime files, and four declared metadata dates. It does not change the host clock, import a live provider, rebuild a board or compute outcomes.

| Injected calendar date | Options-expiry countdown | Risk-overlay stress | Risk driver |
|---|---:|---:|---|
| 2026-07-15 | 2 | 0.0 | None |
| 2026-07-17 | 0 | 0.0 | None |
| 2026-09-15 | 3 | 0.7 | `fomc` |
| 2026-09-16 | 2 | 0.7 | `fomc` |

This reproduces calendar sensitivity with the other inputs held unchanged. It confirms that price truncation alone does not make this risk context point-in-time correct. It does NOT prove that this channel explains the entire buy-set disagreement, certify the original run's exact clock, or authorize selecting the calendar that gives the highest fidelity. The parent log dates lack timezone; the two September dates are diagnostic anchors, not chosen execution clocks. The retained regime input is not newly certified as the original production vintage.

Source probe: `source/probe_historical_clock_dependencies.py`; SHA256 `ccc4e6a64305d7550ec590b963544db3ada12fe578f94b9485936d1b7b11e76d`. Full receipt: `replay_input_repair_20260916_r2/clock_sensitivity.json`.

## Boundaries and next action

The prior full control still has 39 reference buys, 43 rebuilt buys, 30 shared names and Jaccard 0.5769 against the unchanged 0.85 floor. That is reproduction agreement, not a trading win rate. No new full control, policy replay, fitted score, probability, rank, entry, sizing, plan or customer interface was produced.

A new bounded comparison of the retained reference/rebuilt prices and their input files was platform-blocked. `board_input_census.json` was confirmed absent by native metadata read. That exact action was not retried, split, reconstructed or moved to another tool, host or worker. The already-completed benchmark and clock probes are separate evidence and do not supply the refused census.

Next: after the specific comparison boundary is lawfully cleared, qualify the retained board's full input/source/publication clocks through the existing owners, then repair and re-run the same canonical control on a predeclared clock/input contract. Independent source/scientific review remains required. Do not silently turn a July-17-published board into a July-15-available decision, substitute today's engine as the historical champion, or relax the fidelity floor.

All completed crossover/factorial, repair-attribution, horizon/exit, five-benchmark, 48-contrast, context-join and archived-score evidence remains do-not-redo without a material invalidator. The adverse six-group score audit, lack of current-v3 H21 support, and absence of the specified SPY/RSP divergence examples remain unchanged. No live trading inference or default-main ledger application follows from this source repair. PR #7177 remains draft/HOLD-FOR-SOL pending its existing release gates.

## Release qualification

Final exact-source release run PID66110 passed199 tests with exit0. The existing Agent OS validator initially rejected this branch's inherited unstructured handoff for absent YAML frontmatter; its header now binds only this canonical replay-dependency contribution to `WS:PROPHET-US-AVAILABILITY`, explicitly named by the existing replay-authority decision. No workstream owner, status or wave changed, and the broad MACD/signal-quality program was not reclassified as availability. Native validation PID83857 exited0: zero errors,98 pre-existing warnings retained. The tested source, logs, real-input and clock receipts are included with their hashes. This is source qualification, not repository CI, independent scientific review or production acceptance.

## R4 source-review continuation — in progress

Same PR #7177 and source writer; starting head `9513a4d9353362c6e02fe56a402008f49b44b049`. Compatible protected Skillpack remains Mastermind `5ee11ab1e993616f3568cfca4069cb21fa61fd8f`. Current Chairman direction is to keep advancing executable dependencies. This is bounded repair of the existing replay owner, not a new engine, clock service, or trading rule; direct reason is PRINCIPAL_JUDGMENT while separating source fidelity from misleading successful statuses.

Five new synthetic failures reproduced missing tracked wide-panel substitution, erased historical membership, omitted later-deleted panels, corrupt-history fallback, and absent restoration receipts. Historical ticker and wide-panel restoration now share the same pinned-input helper. The first targeted run passed 17 tests. A broader run passed 207 and exposed one old substitution fixture that had incorrectly tracked its supposedly absent historical panel; that fixture now declares a genuinely absent-at-vintage panel while preserving its constituents-diff assertions. Its next exact-source run is pending at this checkpoint.

The new full/sparse integration cases execute real synthetic builder subprocesses through the unchanged two-pass pipeline and final harness receipt; no production data or blocked inspection is involved. Original cache bodies, historical full-control fidelity, scientific review and all existing promotion holds remain unresolved.

A separate synthetic probe proved that `build_board` currently accepts `python -c pass` when a correctly stamped pre-existing board is present. It copies that old board into the cache despite no output write. Evidence: existing host study `replay_sparse_panel_repair_20260916_r4/producer_noop_probe.json`. Next repair must preserve legitimate historical input reads, refuse a no-output successful process, and stop unproven or mismatched cache entries from bypassing that check. Do not delete the historical board before its builder can read it. No real full-board control was executed or waived.

The interrupted R4 checkpoint above is superseded for source status by `REPLAY_SPARSE_AND_PRODUCER_CORRECTNESS_2026-09-16.md` and its exact-source verification receipt. The historical-panel and no-output-producer repairs are implemented there, including preserved historical tails across control/replay. This supersession does not clear the real historical-control, input-qualification, independent-review or production holds.
