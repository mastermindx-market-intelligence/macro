# Copilot feature continuation — scoped queue Stop host prepared; widget consumer held

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION (publication/readback required)
MISSION_COMPLETE: false
Capability: PARTIAL / BUILT_NOT_PROVEN / NOT_RELEASED
Operation: MMX-AI-TERMINAL-ENV-BUILD-20260924-SOL-001
Parent carrier: Macro #7151, cumulative comment 5846488699.

## Mission, authority and current procedure

Give Mastermind AI useful, controlled access to Terminal charts: preserve human studies/drawings, operate on the intended chart, use qualified observations, and report actual outcomes rather than assumptions. Current Chairman continuation retains the requested Pro surface and feature-first sequencing. Tests, typechecking/compilers, browser/model qualification stay deferred to the combined final pass. Nothing waives acceptance. Existing review waiver: #7151 comment 5826034970.

Protected Mastermind pin: fda6ed3911cdda24eb63b2ccbe1b174121cf404f. INDEX blob 94d1af402598894372858793a5b1931019c5fa77, compatible mastermind.sol_skillpack.v1 / 1.0.1 / bootstrap1. Cold/active/delegation/reconcile/review/closeout/delivery companions were loaded from this same commit and are unchanged from previously consumed governing blobs. Source-only work does not invoke Executive runtime. Current assignment supplies intent; source/permission/effect fences remain separate. Scope receipt #8014 comment 5852487159 was created/read back.

## Exact published source and custody

Terminal #757, branch claude/cmx-a4-native-ta-skillpack-20260925: **05dca6c1fa68bfd876bfdbe686868eec06294449**. Original remote branch read back this exact commit after non-force push. Workspace remains /Users/chriswong/Documents/Cluade/charting-app/.claude/worktrees/cmx-a4-native-ta-skillpack-20260925.

Eight owned paths were staged after exact HEAD/index/postimage checks: chartBus.ts, useChartBus.ts, mastermindBrain.ts, BrainWidget.tsx, TerminalShell.tsx, two new Terminal tests, and the existing feature contract. The independent untracked terminal/e2e/brain-targeted-readout.spec.ts remains untouched/excluded, SHA256 6eeb12bc08017a818541a33443ab634625a5d927a02566260fc1d61025338a3c. No globally clean Terminal workspace or general source-lease release is claimed.

Macro #8014, branch claude/cmx-a2c-stream-command-ack-20260925: this record's containing continuation commit, parent **69b9b47b0e454a85cdaba76e38c1236a0658e162**. The final PR/#7151 receipt must identify the containing SHA and this file's blob/digest after publication. Same workspace under /Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/. Still stacked on #8005, Draft/HOLD. This Macro commit is records/specifications only, not a widget/backend feature implementation.

## New source delta — host side only

The existing CommandQueue now tags entries with their already-host-issued batch id. cancelBatches validates a bounded exact batch list and removes only matching pending entries, preserving unrelated entries/FIFO and their existing timer due time. It reuses existing cancellation callbacks/ACK semantics, handles callback failure without running the removed action, and does not recancel later work introduced by listeners. Empty/malformed scopes do nothing, never cancel-all. Existing cancelPending still means all currently pending actions; no second queue, identity generator or cancellation ledger was introduced.

The typed optional local bridge is onChartStop({scope:"received_batches", batch_ids}) -> {scope:"received_batches", cancelled}. TerminalShell wires it to that existing queue. BrainWidget installs the callback after initial CFG creation, relinquishes only its own binding and makes a captured retired callback inert. Older hosts without the optional callback return no cancellation result. A count is local queue removal, not proof of delivery, undo, provider termination or rendered pixels.

**The shared production widget does not yet invoke this bridge.** Do not advertise working Stop-reply cancellation, cold-replay suppression, retained effect notes or a changed composer behavior. The existing visible Cancel queued control is retained; this new source is the prepared host half of a coupled feature.

## Intended consuming behavior — NOT IMPLEMENTED

The design in Terminal docs/research/CMX_COPILOT_CONFIGURED_STUDIES_2026-09-26.md calls for:
- the existing per-turn holder/run/cursor to track chart handoff and up to 64 existing batch ids, not a new command log;
- late stopped/done/retracted/obsolete reply events to stop forwarding chart mutations;
- Stop after any chart callback to keep the question and an honest effect note, including when no answer delta arrived or a host callback threw;
- Stop to cancel only the reply's already-received pending batches through the prepared optional callback;
- a cold reconstructed reply to restore text without replaying chart actions, while an ordinary reconnect keeps the same live turn/cursor behavior;
- missing/failed stop callbacks to be disclosed, without auto-retry or a fabricated cancellation count.

These are planned semantics. The code was not applied. No new claim about original-chart targeting or historical-candle causal correctness follows from this design.

## Exact failure/effect boundary

The first consuming-widget write attempt failed on a FileNotFoundError while checking site/mm_brain.js BEFORE ANY source write. One bounded diagnostic established the generated path has Git skip-worktree flag S, is absent from this sparse workspace, and the canonical templates/mm_brain.js remained SHA256 2a93db87caf50914a82024a985fd20adb6757e36cc05bd005f6b014bfafb7828. The template is canonical; final release must use the existing build to materialize its generated asset.

The corrected same-carrier widget implementation request was then blocked BEFORE DISPATCH by the platform: it could not determine the request's safety status. Classify this exact action TOOL_DEGRADED / EFFECT_NONE; do not infer a permissions grant, technical payload issue or permission to retry via a smaller call, another tool, account, mode or worker. It has NOT been applied.

A genuinely separate bounded read for grouped-annotation replacement/recovery analysis was also blocked before dispatch. No grouped-annotation source was changed. This second refusal does not prove the whole tool lane unavailable: exact scoped publication of the already-authored Terminal source subsequently succeeded. Preserve action-level evidence rather than a blanket Pro/tool outage claim.

The older original-target inspection and selected-candle projection write holds also remain untouched. No repeated denied effect, new worker, alternate carrier or reset was used. Own modifying effects are reconciled: **EFFECT_UNKNOWN: none**. Cause of the platform refusals beyond the returned message remains unknown.

## Specifications and proof boundary

New Terminal executable specifications: terminal/lib/__tests__/chartQueueStopScope.test.ts and terminal/lib/__tests__/brainWidgetChartStop.test.ts. They cover scoped/all-pending cancellation, partial progress, unrelated timer/FIFO preservation, legacy untagged work, malformed scopes, reentrant listeners, callback exceptions, first-mount registration, remount/rebinding and old callback cleanup. They were authored, NOT RUN.

The authored widget specifications depend on functions that were NOT implemented because of the refusal. They were therefore moved out of test discovery to research/CMX_WIDGET_STOP_DEFERRED_TESTS_2026-09-26.py.txt. They are a SPEC_ONLY proposal, not passing or executable feature proof. The separate earlier native-selection specification files remain unchanged.

No test runner, compiler/typecheck, browser/model/provider run, CI polling, merge, deployment, sparse-checkout change or production configuration action was invoked. Only source integrity, whitespace, owned-path staging, commit/push and exact original-branch readback support the new publication claim. This feature has not reached final acceptance.

## Retained work / DO_NOT_REDO

Keep merged Terminal #740/#751 and Macro #7999/#8037; #8005 race-repair candidate d33286edc81478a62ebe847c58dee95c8d1f54fd. Keep all retained native renderer/headless evidence, exact selected samples, exact range control, configured guidance, Data Window output, additive indicator edits/selective AI clear, original target receiver, feedback/cancellation, dense-state delivery, inert command snapshots and truthful receipt outcomes.

Native boundary return was already consolidated unchanged at Macro 55999405ece25b512db879f2916f9004061a2eea under return 5851985582 and ruling 5852234150. Receipt/intake source is retained at Macro 69b9b47b0e454a85cdaba76e38c1236a0658e162 / Terminal f39454be5e4a3e617cf2c42f1a3db48cef2daf42. No foreign source remains to reintegrate by assumption. Data Window mc.rsi14 is not native RSI Ultimate. The existing Cancel queued remains pending-at-click only, not whole-reply/provider cancellation or undo.

## Exact next action and justified continuation boundary

Consume a genuinely permitted platform recovery or admitted same-operation source return for the consuming-widget action, then reconcile its source against Terminal 05dca6c1 before completing the existing template/host path. Do not treat another Continue or model change as permission to replay the refused action. The two pre-existing semantic gaps remain: original-pane target frozen before model work with legitimate-only revision adoption; selected-candle native events restricted to their confirmation/knowability basis. No source/consumer acceptance is claimed for either.

After feature construction and these holds are resolved, perform the deliberately deferred combined native/target/historical/cancellation/range/old-client/receipt/Stop/replay/browser/model/dark-light/EN-ZH/responsive qualification and normal #8005 -> #8014 release gates. Source publication and green CI alone are not acceptance.

This boundary preserves a published host/queue interface while its planned consuming operation is explicitly held, plus a separately refused investigation. It is not elapsed-time completion, mission closure, custody transfer or a background wake. Direct execution rationale: coupled queue/widget semantics and incumbent principal source custody; another worker would overlap or reproduce held work. No Fable, runtime child or watcher was created. Intended next mode: requested Pro for remaining cross-system integration judgment; actual served-model and future capability remain unverified.


## 2026-09-27 Extra High chunk — read-only mounted-pane context

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION after this handoff's containing commit, PR metadata and #7151 cumulative frontier are read back. MISSION_COMPLETE: false. Capability remains PARTIAL / BUILT_NOT_PROVEN / NOT_RELEASED. The Chairman requested Extra High for write-heavy progress and bounded chunks to avoid session failure; tests/typechecks/compilers/browser/model qualification remain deliberately deferred to the combined final pass, not waived.

Protected Mastermind procedure pin for this chunk: `d7c949d31f3893d95822a4ee8e5e4be9edaf5593`. INDEX and all required enrolled law blobs were read from that exact commit; their blobs remain the same previously consumed compatible 1.0.1/bootstrap1 procedure versions. No Executive runtime or provider was invoked.

### Exact published source

Terminal #757 advanced on the same incumbent branch/worktree to **4f8035a27c83f954d4d34c68a17b58d627ba7d6e** (`feat(copilot): expose read-only mounted pane context`). Original remote branch readback matched. The unrelated untracked `terminal/e2e/brain-targeted-readout.spec.ts` remains untouched/excluded at SHA256 **6eeb12bc08017a818541a33443ab634625a5d927a02566260fc1d61025338a3c**.

Macro #8014 advanced on the same incumbent branch/worktree to feature commit **58a6e59865b909086ced252198c986db3531b24d** (`feat(copilot): qualify read-only mounted pane context`). Original remote branch readback matched. The Macro workspace was clean after publication.

### Capability delta in source

Before this chunk, Copilot's numerical/native chart observation callback existed only for the active chart pane. A 2-pane comparison or 4-pane same-symbol MTF layout therefore did not expose the mounted sibling panes through the live chart-state read.

The existing chart-state mirror now has an additive **`chart.pane_contexts.v1`** read-only projection for up to four mounted panes:
- each row preserves its pane id, symbol, timeframe, paneSync calendar viewport, and current renderer-native observation packet when available;
- ChartPanel remains the only native computation owner; every pane reuses the same `computeSuite()` bundle/projector path already used to paint that pane;
- the active pane remains the sole mutation authority. Reading another pane does not activate it, retarget a command, change symbol/timeframe, or increment `ai_context_client.v1.context_revision`;
- stale symbol/timeframe/settings/replay/locked-bar native packets become explicit unavailable evidence rather than being relabeled current;
- malformed/duplicate/out-of-range producer rows make the cross-pane packet unavailable rather than silently shrinking the comparison;
- single-pane layouts retain the established root chart-state shape without a multi-pane packet.

The existing receipt-first payload reducer now treats `pane_contexts` as optional comparison evidence and withholds it **before** active-pane native/Data Window evidence under the 60 KiB transport budget, reporting the omission in the existing `mirror_coverage`. ACK identity, active target identity and real chart stores remain untouched.

The Brain gateway structurally qualifies the packet with the same existing native-observation qualifier. It checks exact origin/revision, active pane identity, 2–4 row count, unique bounded pane ids, symbol/timeframe text and finite ordered viewport ranges. Each pane's native packet is qualified against a pane-specific view of the same session/configuration census. The active row must agree with the separately qualified root `session.native_observations`; model-visible output references that active root instead of duplicating its large packet. Output is itself bounded and carries fixed server-owned basis language: inactive panes are evidence-only, freshness is chart-loaded rather than independently live-attested, and missing/partial evidence is not negative evidence.

Technician protocol advanced to v7 so multi-pane comparisons keep each pane's symbol/timeframe/evidence basis separate and never treat a read-only pane as a chart-command target.

### Specifications / proof boundary

Authored, **NOT RUN**:
- Terminal `terminal/lib/__tests__/useChartBusPaneContexts.test.ts` — mounted-pane mirror/revision, single-pane compatibility and transport-priority behavior.
- Macro `tests/test_brain_pane_contexts.py` — read-only basis, active identity/native agreement, malformed pane ids/viewports, mirror-budget omission and real `read_chart_state` consumption.

Only exact-head/source fences, path-scoped staging, `git diff --check`, commits, non-force pushes and original-branch readbacks were used. No local test runner, TypeScript/Python compiler, browser/model/provider execution, CI polling, merge, deployment or production configuration action occurred. Authored test files are specifications until the deferred qualification phase.

One independent exploratory read attempting to inspect the Data Window projection for a possible per-pane extension was blocked before dispatch by the platform. EFFECT_NONE; it was not retried. This chunk therefore extends multi-pane **native renderer evidence and viewport identity only**, while preserving the existing active-pane Data Window packet. Do not claim classic/Data-Window values exist for every pane.

### Held work / exact next action

DO_NOT_REDO all previously accepted/published source: Terminal #740/#751, Macro #7999/#8037, #8005 stale-revision repair candidate, native renderer/headless projection, exact ranges, additive study edits/selective AI clear, receipt-first delivery, command-input hardening, truthful outcomes/cancellation, and the reply-scoped queue Stop host at Terminal 05dca6c1.

The previously refused actions remain held and were not replayed through Extra High: the shared widget Stop consumer, original-pane target freezing / legitimate-only revision adoption, selected-candle confirmation-filtered event projection, and grouped-annotation investigation. A mode change is not permission recovery.

Next bounded chunk: first consume any genuinely permitted platform recovery or same-operation source return for one of those held semantic actions. If none exists, continue another path-disjoint product capability that materially improves Copilot without recreating control/identity/observation owners. Once feature construction ends, execute the combined native/multi-pane/target/historical/cancellation/range/old-client/receipt/Stop/replay/browser/model/dark-light/EN-ZH/responsive qualification, then normal #8005 → #8014 release gates. Green CI alone is not acceptance.

Own effects in this chunk are reconciled. EFFECT_UNKNOWN: none. No child, watcher, provider activation or automatic wake was created.


## 2026-09-27 Extra High chunk — six-sample native recent window

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION after containing commit and external readbacks. MISSION_COMPLETE: false. Capability remains PARTIAL / BUILT_NOT_PROVEN / NOT_RELEASED. Chairman continues Extra High for write-heavy progress with bounded turns; test/typecheck/compiler/browser/model qualification remains intentionally deferred to the final combined pass.

Protected Mastermind pin for this chunk: `b2e0b905bfac975766afda3cf65527897bc0e25a`. INDEX and required enrolled law blob identities are unchanged from the previously consumed compatible 1.0.1/bootstrap1 set.

### Exact published source

Terminal #757 advanced to **83ca35be96e0b1cfe5d8093ab2ee443c244d3f74** (`feat(copilot): expose short native series history`) on the same incumbent branch/worktree. Exact original-branch readback matched. The independent untracked browser spec remains untouched at SHA256 **6eeb12bc08017a818541a33443ab634625a5d927a02566260fc1d61025338a3c**.

Macro #8014 advanced to **2a63f87f82e7e84961e6d926f100c389e2b95bfb** (`feat(copilot): qualify short native series history`) on the same incumbent branch/worktree. Exact original-branch readback matched; workspace was clean after publication.

### Capability delta in source

The shared native observation projector previously selected only the newest **two** points from each returned native series. It now selects up to the newest **six** raw source samples per series, newest first. This is a richer observation window, not a new historical-data endpoint or a derived signal.

Producer semantics:
- same exact `SuiteRenderBundle` already used by renderer/headless research adapter;
- each sample remains raw `{index,value,age_bars}`; null remains null, never backfilled;
- per-series window is capped at six via `NATIVE_OBSERVATION_SERIES_SAMPLE_LIMIT`;
- exact locked-bar `selected_sample` remains independent and may point outside the six-bar recent window;
- live packet still has the existing 7168-byte cap; the compact/headless projector retains its existing byte owner. A larger row can cause the existing whole-row selector to omit more series, with coverage counts remaining authoritative.

Brain qualification:
- accepts 1–6 samples for backward compatibility with older 1–2 sample clients;
- requires unique indices in strict decreasing/newest-first order;
- rejects duplicate, reordered, out-of-range, nonfinite, or >6 sample windows;
- recomputes `age_bars` from qualified indices instead of trusting client age prose;
- publishes fixed basis `recent_series: up_to_6_newest_source_samples_per_returned_series`.

Technician protocol advanced to **v8**. The model may describe only the short observed path represented by those raw samples (for example rising/falling/turning over those bars); it must not convert the six-bar window into a calibrated forecast, probability, or substitute for the requested longer horizon.

### Authored specifications / proof boundary

Existing Terminal native observation spec gained a six-sample newest-first/null-preservation case. Existing Macro native boundary spec gained six-sample acceptance and duplicate/reordered/>6 rejection cases. **Authored/modified, NOT RUN.**

Only exact head/index fences, source diff review, `git diff --check`, sample-limit parity checks, path-scoped staging, commits, non-force pushes and exact branch readbacks occurred. No local test runner, TypeScript/Python compiler, browser/model/provider run, CI polling, merge, deployment or production config action.

### Held lanes / next

The exact-bar command idea was deliberately NOT implemented: source review showed a programmatic bar-selection mutation would inherit the separately held original-chart-target-freezing gap. Do not widen mutation surface until that semantic owner is resolved.

The previously refused actions remain held: shared widget Stop consumer; original-pane target freezing / legitimate-only revision adoption; selected-candle confirmation-filtered native event projection; grouped-annotation inspection. A prior per-pane Data Window read remains held. No replay or alternate carrier.

Retain the preceding read-only multi-pane source: Terminal **4f8035a27c83f954d4d34c68a17b58d627ba7d6e**, Macro feature **58a6e59865b909086ced252198c986db3531b24d** and all prior DO_NOT_REDO work.

Exact next chunk: consume a genuinely permitted recovery/return for one of the held core semantic actions if one exists; otherwise continue a path-disjoint feature that improves Copilot without expanding unsafe mutation authority. Final combined qualification remains owed. EFFECT_UNKNOWN: none. No worker/watcher/provider activation or automatic wake.


## 2026-09-27 Extra High chunk — viewport-aware active rendered price window

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION after this handoff's containing commit, PR metadata and cumulative #7151 frontier are read back. MISSION_COMPLETE: false. Capability remains PARTIAL / BUILT_NOT_PROVEN / NOT_RELEASED. Chairman continues feature-first Extra High work in bounded chunks; local tests/typechecks/compilers/browser/model qualification remain deliberately deferred to the final combined pass and are not waived.

Protected Mastermind pin: **b2e0b905bfac975766afda3cf65527897bc0e25a**. INDEX and required enrolled law blob identities remain the same compatible 1.0.1/bootstrap1 set already consumed. Source-only work did not invoke Executive runtime.

### Exact published source

Terminal #757 advanced on the same incumbent branch/worktree to **dbc5002d586f139fbda2debe0cb4ae2390246d83** (`feat(copilot): expose active rendered price window`). Original remote branch readback matched. The unrelated untracked `terminal/e2e/brain-targeted-readout.spec.ts` remains untouched/excluded at SHA256 **6eeb12bc08017a818541a33443ab634625a5d927a02566260fc1d61025338a3c**.

Macro #8014 advanced on the same incumbent branch/worktree to **38beb6e84ebb221ebb9bade42d25169c6b50b63e** (`feat(copilot): qualify active rendered price window`). Original remote branch readback matched; Macro workspace was clean after publication.

### Capability delta in source

Before this chunk, Copilot had qualified native-indicator observations and exact latest/locked Data Window samples, but no bounded sequence of the active chart's raw rendered candles. `chart_digest` is a separate daily/weekly structural source and cannot establish what an intraday/replay screen is actually showing.

The existing chart-state mirror now carries **`chart.price_window.v1`**:
- source is the active ChartPanel's existing `ChartReadoutMeta.bars`, which is the accepted rendered bar set and is already replay-sliced; no new fetch, resample, bar store, indicator compute or signal plane;
- at most **12** raw OHLCV bars are returned oldest→newest;
- when paneSync has an actual active-pane calendar viewport, selection is `visible_tail`: only loaded bars inside that viewport are eligible. A viewport with no loaded overlap reports unavailable rather than substituting off-screen latest bars;
- before the first viewport is available, selection is `loaded_tail`, ending exactly at the accepted rendered series tail;
- every row carries exact source index/time/open/high/low/close/volume and `age_bars_from_loaded_end`;
- replay context is carried as `basis.data_status = replay_slice`; the ordinary path says `loaded_chart_cache_not_live_attestation`;
- newest bar closed status is explicitly **unknown**. This packet is raw source evidence, not a signal, forecast or probability.

The existing state budget treats cross-pane comparison as the first optional packet and this active price window as the next optional packet. It can therefore be replaced by a fixed `chart_state_budget` unavailable receipt before established native/Data Window evidence or ACK identity is sacrificed. `mirror_coverage.omitted_fields` now structurally permits `price_window`.

The Brain gateway adds a bounded qualifier with fixed server-owned semantics:
- exact root origin/revision is required by `read_chart_state`;
- packet symbol/timeframe must match the active chart;
- replay/load status is an enum and survives sanitization;
- source count/coverage arithmetic, 12-bar cap and oldest→newest declaration are checked;
- source indices must be strictly consecutive/increasing; loaded-tail must end at the actual loaded source tail;
- string bar times use the same YYYY-MM-DD axis semantics as Terminal `timeToMs`; numeric times remain epoch seconds;
- times must be strictly increasing; visible-tail bars must lie within the declared viewport;
- OHLC must be finite with high >= low; volume is nullable or finite/nonnegative;
- client age annotations are ignored and recomputed server-side;
- arbitrary client basis prose is discarded. Model-visible output fixes `predictive_validation:false`, `signal_authority:false`, `last_bar_closed:unknown`, and chart-loaded-not-independent-live freshness.

Technician protocol advanced to **v9**. It tells the model that price-window bars are descriptive raw price evidence only, that visible-tail must not be replaced with off-screen bars, that replay_slice is history/replay rather than the current market, that omitted bars bound the claimable context, and that the newest candle cannot be called closed/confirmed without separate qualified evidence.

### Related source-quality repair

The previous mounted-pane implementation scheduled a mirror for any pane id passed to `noteViewport`. This chunk narrowed that behavior: only the active pane or a pane actually present in the incumbent `getPaneContextSnapshots` mounted-pane census can schedule a POST. A stale/stray id may update the local viewport cache but cannot create network churn or model evidence. No second mounted-pane owner was created.

### Specifications / proof boundary

Authored or extended, **NOT RUN**:
- Terminal `terminal/lib/__tests__/chartPriceWindow.test.ts`: loaded tail, exact visible tail, no-overlap refusal, replay labeling, malformed/nonmonotone source refusal.
- Terminal `terminal/lib/__tests__/useChartBusStateMirror.test.tsx`: real state-mirror integration from replay-safe rendered bars + active viewport.
- Macro `tests/test_brain_price_window.py`: server age recompute/input immutability, visible-tail basis, replay preservation, index/time/OHLCV fail-closed cases, viewport containment, loaded-tail ending and real `read_chart_state` replacement.

Only exact-head/remote fences, source/diff review, `git diff --check`, schema/budget parity, foreign-file hash preservation, path-scoped staging, non-force commits/pushes and exact branch readback support this publication. No test runner, TypeScript/Python compiler, browser/model/provider run, CI poll, merge, deployment or production config action was invoked.

### Held lanes / next

The separately held mutation/control actions remain untouched: shared widget Stop consumer; original-pane target freezing / legitimate-only revision adoption; selected-candle confirmation-filtered event projection; grouped-annotation inspection. The previous per-pane Data Window read remains held. This chunk did not retry or route around any refusal.

DO_NOT_REDO the preceding mounted-pane and six-sample-native work: Terminal **4f8035a27c83f954d4d34c68a17b58d627ba7d6e** / **83ca35be96e0b1cfe5d8093ab2ee443c244d3f74**, Macro feature **58a6e59865b909086ced252198c986db3531b24d** / history **2a63f87f82e7e84961e6d926f100c389e2b95bfb**, plus all older accepted source.

Exact next chunk: consume a genuinely permitted recovery/return for a held semantic action if one exists. Otherwise continue another path-disjoint Copilot capability that reuses incumbent read owners and does not widen unsafe mutation authority. Final combined native/price/multi-pane/target/historical/cancellation/range/old-client/receipt/Stop/replay/browser/model/dark-light/EN-ZH/responsive qualification remains owed, followed by normal #8005 → #8014 release gates.

Own effects reconciled. EFFECT_UNKNOWN: none. No worker, watcher, provider activation, deployment or autonomous wake.


### Post-publication transport correction — cumulative #7151 comment not advanced

After price-window source publication, Agent OS readback, and both Draft-PR body readbacks, the attempted update of cumulative parent comment **#7151 / 5846488699** was blocked by the platform **before dispatch**. Read-only fetch confirms that comment still ends at the preceding six-sample-native chunk. Classify this exact comment-update action **TOOL_DEGRADED / EFFECT_NONE**; it was not retried through a smaller payload, alternate tool, carrier, worker, account or mode.

Therefore the canonical durable continuation for the price-window chunk is this Agent OS file plus current PR #757/#8014 exact-source metadata/readbacks, not an asserted new #7151 comment receipt. The older #7151 comment remains useful history but is stale for this latest chunk. This correction supersedes any conditional wording above that implied the price-window #7151 frontier had already been advanced/read back.

No product/source behavior changed in this correction. EFFECT_UNKNOWN remains none.


## 2026-09-27 Extra High chunk — mounted-pane raw price context

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION after this handoff's containing commit and PR readbacks. MISSION_COMPLETE: false. Capability remains PARTIAL / BUILT_NOT_PROVEN / NOT_RELEASED. Chairman's current outer directive is continued feature-first execution in bounded chunks; test/typecheck/compiler/browser/model qualification remains deferred to the final combined pass, not waived.

Protected Mastermind pin: **deed35f6b0d8794987ab9692dd8d46b1549a720f**. INDEX is compatible mastermind.sol_skillpack.v1 / 1.0.1 / bootstrap1. Required ACTIVE_EXECUTION/RECONCILE/CLOSEOUT/delivery/routing law blobs were loaded from this exact commit and match the previously consumed compatible blob identities.

DIRECT_EXECUTION_REASON: **PRINCIPAL_JUDGMENT + CRITICAL_PATH_SHORTCUT** — the slice couples the incumbent renderer identity, chart-state transport, pane comparison projection and Brain structural qualifier; splitting it across a new writer would add collision/review overhead larger than the bounded change. **WHY NOT FABLE:** architecture is already frozen and the work is a path-disjoint extension of existing owners, not unresolved principal ambiguity.

### Exact published source

Terminal #757 advanced on the incumbent branch/worktree to **082d9e6a9c85762c876e7e615399bfc0ce0118d3** (`feat(copilot): add raw price context across panes`). Original remote branch readback matched. The independent untracked `terminal/e2e/brain-targeted-readout.spec.ts` remains untouched/excluded at SHA256 **6eeb12bc08017a818541a33443ab634625a5d927a02566260fc1d61025338a3c**.

Macro #8014 advanced on the incumbent stacked branch/worktree to feature commit **e3789adac66765199b9023f792884cf79c29a2c8** (`feat(copilot): qualify raw price context across panes`). Original remote branch readback matched; Macro workspace was clean after publication.

### Capability delta in source

The mounted-pane read-only context now carries each **inactive pane's own raw rendered price window** alongside its already-supported renderer-native observations.

Terminal:
- every ChartPanel can publish the accepted rendered bar array it already owns; no new fetch, resample, bar store, Data Window callback or indicator computation was introduced;
- publication is source-identity bound to the accepted symbol/timeframe and replay state;
- a compact recent-tail signature suppresses duplicate callbacks, while a new accepted array, replay transition or live recent-bar change republishes;
- symbol/timeframe identity changes and unmount retire that pane source; late callbacks from a prior symbol/timeframe/replay epoch are ignored;
- Terminal stores pane sources only in a pane-indexed ref. At state-POST time the existing `buildChartPriceWindow` projector applies that pane's own paneSync viewport;
- the active pane does **not** duplicate its root price/native packets inside pane_contexts. It carries exact references `session.price_window` and `session.native_observations`; only inactive panes embed separately projected evidence;
- `ChartPriceWindowSource` now carries symbol/timeframe identity itself, so a stale source cannot be relabeled to the current pane;
- no inactive pane receives mutation, Data Window value lookup, active selection, or context-revision authority.

Brain:
- active pane row must use both exact root references and may not include duplicate embedded active price/native packets;
- inactive panes may not reference root packets; their embedded price/native packets are independently qualified by the existing owners;
- a qualified pane price window must match the **same paneSync viewport** declared by that pane row: viewport present => visible_tail with exactly equal range; viewport absent => loaded_tail with no visible range;
- active and inactive unavailable/partial price/native evidence makes pane_contexts partial rather than falsely complete;
- model-visible active row keeps references instead of duplicating large packets; inactive rows carry qualified evidence;
- basis explicitly says inactive panes provide price + native evidence only and never become command targets;
- technician protocol advanced to **v10**, requiring each pane's symbol/timeframe/viewport/price/native basis to remain separate and applying replay/visibility/unknown-close rules to inactive panes too.

### Specifications / proof boundary

Authored or extended, **NOT RUN**:
- Terminal `chartPriceWindow.test.ts`: source identity is now part of the projector contract.
- Terminal `useChartBusPaneContexts.test.ts`: root packet references, no active duplication, inactive raw price projection.
- Terminal `useChartBusStateMirror.test.tsx`: active price-source identity update.
- Macro `test_brain_pane_contexts.py`: root references, inactive price qualification, active/inactive reference misuse refusal, pane-price viewport binding, read_chart_state projection.

Only exact-head/remote fences, source/diff review, `git diff --check`, callback/reference contract inspection, foreign-file hash preservation, path-scoped staging, non-force commits/pushes and exact branch readbacks support this publication. No test runner, TypeScript/Python compiler, browser/model/provider execution, CI polling, merge, deployment or production config action occurred.

### Durable/transport boundary

The previously attempted cumulative parent comment update on **#7151 / comment 5846488699** remains action-specifically blocked before dispatch. No new platform evidence established recovery, so this chunk did **not** retry that exact comment mutation. That comment therefore remains stale after the six-sample-native chunk. Current durable truth is this Agent OS handoff plus exact PR #757/#8014 source metadata/readbacks. EFFECT_UNKNOWN: none.

### Held lanes / exact next action

Held actions remain untouched: shared widget Stop consumer; original-pane target freezing / legitimate-only revision adoption; selected-candle confirmation-filtered native event projection; grouped-annotation inspection; prior per-pane Data Window read. Mode/turn continuation is not permission to replay those refusals.

DO_NOT_REDO all preceding accepted/published source, including active price window Terminal **dbc5002d586f139fbda2debe0cb4ae2390246d83** / Macro **38beb6e84ebb221ebb9bade42d25169c6b50b63e**, mounted-pane context, six-sample native history and earlier command/control work.

Exact next chunk: first consume any genuinely new permitted recovery/return for a held semantic lane. If none exists, continue another path-disjoint read-only Copilot capability using incumbent owners. Final combined native/price/multi-pane/target/historical/cancellation/range/old-client/receipt/Stop/replay/browser/model/dark-light/EN-ZH/responsive qualification remains owed, followed by normal #8005 -> #8014 release gates.

Own effects reconciled. No worker, watcher, provider activation, deployment or autonomous wake.


## 2026-09-27 Extra High chunk — chart presentation context

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION after this handoff's containing commit and exact PR/source readbacks. MISSION_COMPLETE: false. Capability remains PARTIAL / BUILT_NOT_PROVEN / NOT_RELEASED. Chairman continues feature-first execution in bounded chunks; local tests/typechecks/compilers/browser/model qualification remain deliberately deferred to the final combined pass and are not waived.

Protected Mastermind pin for this chunk: **c01d890f6536539496f2d6744f3143ff49da296d**. INDEX is compatible `mastermind.sol_skillpack.v1` / 1.0.1 / bootstrap1. Required COLD_START, ACTIVE_EXECUTION, RECONCILE_STATE, CLOSEOUT, delivery and dialogue/routing law blobs were loaded from this exact commit. Their blob identities remain byte-identical to the previously consumed compatible procedures. The optional bootstrap supporting reference was unavailable through the installed skill URI; no claim is made that it was loaded. Protected INDEX source ownership law remained available and governed this source operation.

DIRECT_EXECUTION_REASON: **PRINCIPAL_JUDGMENT + CRITICAL_PATH_SHORTCUT** — this slice joins the incumbent ChartPane renderer/settings owner, chart-state transport, mounted-pane projection and Brain sanitizer in one bounded interface. A new writer would add source collision/review overhead larger than the change. **WHY NOT FABLE:** architecture is frozen and no unresolved principal ambiguity requires scarce Fable capacity.

### Exact published source

Terminal #757 advanced on the same incumbent branch/worktree to **1811dc68aa4af20e7bd91b3b827670f5181a50cc** (`feat(copilot): expose chart presentation context`). Exact original-branch readback matched. The independent untracked `terminal/e2e/brain-targeted-readout.spec.ts` remains untouched/excluded at SHA256 **6eeb12bc08017a818541a33443ab634625a5d927a02566260fc1d61025338a3c**.

Macro #8014 advanced on the same incumbent stacked branch/worktree to feature commit **35734c7f0d234baa89619b316739aa55b3ec68ff** (`feat(copilot): qualify chart presentation context`). Exact original-branch readback matched; Macro workspace was clean after publication.

### Capability delta in source

The existing chart-state mirror now carries additive **`chart.presentation.v1`** read-only context so Copilot can distinguish underlying market evidence from the way Terminal currently renders it.

Terminal projection:
- source is committed ChartPane/ChartFrameBar state already driving the renderer; no DOM scraping, screenshot/OCR, second settings store, mutation command or control owner;
- presentation waits for BOTH shell preference hydration and pane-local chart-settings hydration, preventing transient defaults from being telemetered as the user's committed view;
- exact identity is pane id + symbol + timeframe. Terminal also rejects late callbacks whose chart type, replay state or day-trade mode no longer matches the current pane;
- chart type is closed to candles / hollow / heikin / bars / line / line-markers / step / area / baseline;
- price scale is closed to normal / log / percent / indexed-to-100 plus invert, side and autoscale;
- session view carries replay, day-trade mode and extended-hours requested/eligible/effective. Extended-hours eligibility is effective only on supported intraday panes, matching the renderer's intraday fetch path rather than a merely requested daily checkbox;
- display projection is only interpretation-relevant booleans/precision: price/last-value lines, grid, OHLC, volume, indicator titles, watermark, candle body/border/wicks and extended price line;
- Visual Intelligence carries its five boolean layer toggles only;
- active comparison overlays are capped at four and preserve symbol, price-vs-percent mode, normalized fixed color, line style, width, and actual visible/hidden state from the existing compare hidden owner;
- arbitrary chart titles, labels, background/theme strings and other UI prose are excluded. Comparison color is retained only to identify a plotted overlay;
- output basis explicitly says `control_authority:none` and `render_application:committed_settings_not_pixel_attestation`.

Single/multi-pane transport:
- the root active chart carries one `session.presentation`;
- active `pane_contexts` references `session.presentation`, `session.price_window` and `session.native_observations` instead of duplicating large root packets;
- inactive mounted panes embed their own presentation/price/native evidence independently;
- presentation is optional transport evidence: under chart-state budget pressure the reducer withholds `pane_contexts` first, then root `presentation`, before active price/native/Data Window packets or command receipts; `mirror_coverage.omitted_fields` structurally permits `presentation`.

Brain qualification:
- exact connected origin/revision and root symbol/timeframe/pane identity remain required;
- all chart-type/scale/session/display/Visual Intelligence/comparison enums, booleans, fixed color/style/width/visibility and extended-hours consistency are revalidated server-side;
- arbitrary client labels/basis prose are discarded and replaced by fixed server semantics;
- presentation replay must agree with the same pane's qualified price-window basis (`replay_slice` vs loaded chart cache). Contradictions fail presentation closed rather than choosing the convenient packet;
- active pane rows must use root refs when root presentation is observed and may not duplicate embedded active packets;
- inactive panes may never borrow root refs; their presentation is independently qualified;
- pre-presentation/older clients remain compatible: missing presentation becomes explicit unavailable evidence and pane context degrades to PARTIAL rather than becoming invalid;
- missing/partial presentation/price/native evidence propagates PARTIAL rather than false-complete comparison.

Technician protocol advanced to **v11**:
- presentation is evidence, never control authority;
- log/percent/indexed/inverted scales change visual geometry, not raw-price arithmetic;
- line/area/baseline do not visibly expose candle bodies/wicks despite raw OHLCV being available;
- Heikin-Ashi bodies are transformed presentation while `price_window` remains underlying raw market OHLCV; Heikin visual O/C must never be quoted as source-market O/C;
- comparison `visible:false` means configured-but-hidden; percent comparison overlays may be rescaled and are not direct compared-symbol price coordinates;
- multi-pane presentation/replay/extended-hours/price/native bases stay distinct.

### Specifications / proof boundary

Authored or extended, **NOT RUN**:
- Terminal `terminal/lib/__tests__/chartPresentation.test.ts` — chart type, scale, extended-hours, comparisons and malformed projection.
- Terminal `chartStatePayload.test.ts` — presentation is withheld before numerical evidence under transport pressure while ACKs survive.
- Terminal `useChartBusPaneContexts.test.ts` — active root presentation ref, inactive embedded presentation and no active duplication.
- Terminal `useChartBusStateMirror.test.tsx` — single-pane presentation mirror without inventing pane context.
- Macro `tests/test_brain_presentation.py` — structural sanitization, arbitrary-prose stripping, invalid enums/compare forms, replay-vs-price mismatch and real `read_chart_state` replacement.
- Macro `tests/test_brain_pane_contexts.py` — active/inactive presentation refs, old-client compatibility, replay-vs-price consistency and pane projection.

Only exact-head/remote fences, source/diff review, `git diff --check`, schema/transport/reference inspections, foreign-file hash preservation, path-scoped staging, non-force commits/pushes and exact branch readbacks support this publication. No test runner, TypeScript/Python compiler, browser/model/provider execution, CI polling, merge, deployment or production configuration action occurred.

### Durable / held boundaries

The cumulative parent #7151 comment update remains action-specifically blocked from the earlier pre-dispatch refusal. No new platform recovery evidence appeared, so this turn did **not** retry that exact effect. Current durable truth is this Agent OS handoff plus exact PR #757/#8014 source metadata/readbacks. EFFECT_UNKNOWN: none.

Held semantic actions remain untouched: shared widget Stop consumer; original-pane target freezing / legitimate-only revision adoption; selected-candle confirmation-filtered native event projection; grouped-annotation inspection; prior per-pane classic Data Window read. A new turn/model mode is not permission to replay those refusals.

DO_NOT_REDO all preceding accepted/published source, including mounted-pane raw price Terminal **082d9e6a9c85762c876e7e615399bfc0ce0118d3** / Macro **e3789adac66765199b9023f792884cf79c29a2c8**, root price window, mounted native context, six-sample native history and older command/control work.

Exact next chunk: first consume genuinely new permitted recovery/return for one held semantic lane if such evidence exists. Otherwise continue another path-disjoint read/intelligence capability using incumbent owners and without widening mutation authority. Final combined native/price/presentation/multi-pane/target/historical/cancellation/range/old-client/receipt/Stop/replay/browser/model/dark-light/EN-ZH/responsive qualification remains owed, followed by normal #8005 -> #8014 release gates.

Own effects reconciled. No worker, watcher, provider activation, deployment or autonomous wake.
