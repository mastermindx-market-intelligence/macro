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
