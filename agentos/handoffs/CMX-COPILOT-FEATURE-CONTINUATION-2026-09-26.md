# Copilot Terminal — cumulative feature continuation

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION after this record's publication/readback.
MISSION_COMPLETE: false. Capability: PARTIAL / BUILT_NOT_PROVEN / NOT_RELEASED.
Operation: `MMX-AI-TERMINAL-ENV-BUILD-20260924-SOL-001`.
Parent: Macro #7151; cumulative checkpoint comment 5846488699.

## Mission, present intent and procedure

Give Mastermind AI useful, controlled access to the user's Terminal: exact chart targeting; selective study/AI-annotation edits that preserve human work; native numerical observations instead of invented indicator readings; truthful action outcomes and usable recovery. Do not reduce the product to schemas or status reports.

The Chairman's current directive is to continue in Pro with sustained, high-quality feature progress. The earlier explicit deferral of local tests, compilers/typechecking, browser/model qualification until the combined final pass remains. No test or release-proof waiver is inferred. No new local tests/compilers/browser/model calls, CI polling, merge or deployment were performed by this continuation. Eighteen new executable test cases were authored, not run. Source/whitespace/Git readback are persistence evidence only. Review waiver remains #7151 comment 5826034970; no independent approval claimed.

Protected Mastermind pin: `4c6b206d3fb7fbc6d077faf61ae361bedf259925`, compatible mastermind.sol_skillpack.v1 / 1.0.1 / bootstrap1. INDEX blob `94d1af402598894372858793a5b1931019c5fa77`; COLD_START `b11e58f083040144933cf2ddab76bf6c60a7e542`; ACTIVE_EXECUTION `9fed10f7cc7a2f4323d039b406f7c0715445e22e`; WEB_CEO_DELEGATION `2073a33f05506268b15f0b5ce292ce57d5b60ed3`; CLOSEOUT `4a9ec3782da001322604e977dbe91b9cf371f0b9`. Relevant current-source content was consumed from that same pin. Current bootstrap/assignment controls routine design choices and test ordering rather than another generic design-approval ceremony. This never grants a platform-denied action.

## Exact source and retained custody

Terminal PR #757 is on the SAME `claude/cmx-a4-native-ta-skillpack-20260925` branch/workspace:
`/Users/chriswong/Documents/Cluade/charting-app/.claude/worktrees/cmx-a4-native-ta-skillpack-20260925`.
Current own published source: **22a048f06e8a41f9b1834a8640ae2689eba1ad6d**, parent **dd8cb762bcae66b7613837d9a16e4762669ad5f3**. Original origin branch read back exactly 22a048f06e8a41f9b1834a8640ae2689eba1ad6d after a normal non-force push. Six own paths only were staged/committed. It remains Draft/HOLD.

The independent untracked `terminal/e2e/brain-targeted-readout.spec.ts` remains SHA256 **6eeb12bc08017a818541a33443ab634625a5d927a02566260fc1d61025338a3c**, unchanged, unstaged and unexecuted. The tracked source is clean after publication; the whole workspace is NOT called clean. Existing path-disjoint custody ruling: #757 comment 5851450815.

Macro PR #8014 remains on SAME `claude/cmx-a2c-stream-command-ack-20260925` branch/workspace:
`/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/cmx-a2c-stream-command-ack-20260925`.
Pickup head **28437b9b02bf13ee4a2f58ec92d49f0b256dbcc8**. This continuation's Macro publication changes ONLY protocol.md, this handoff, and research/CMX_NATIVE_SELECTION_DEFERRED_TESTS_2026-09-26.py.txt. The final PR/parent receipt supplies the exact resulting commit. #8014 remains stacked on #8005 and held; no retarget/merge this turn.

**Concurrent Macro source is preserved, not acquired:** uncommitted `engine/neuralweb/brain_gateway.py` and untracked `tests/test_brain_native_evidence_boundary.py` appeared from another writer. Last observed SHA256s: gateway `49d68413b2e43acb7a1444d27a3047134ad5be2e61e03791f97075d691977394`; foreign test `286362f25175f11411fac3f27739df48f443b3bc7913a967e7463d20cd5a10b6`. They are excluded from this continuation's commit and no testing/acceptance/publication is attributed here. Their native-settings equality/census/enum/number safeguards are source-return evidence, not a released result. A separately inserted redundant helper was removed by exact reverse edit; the incumbent `_native_live_settings_equal` remains the only proposed equality owner. Do not re-add a duplicate helper or stage foreign source.

Direct execution rationale: coupled source/consumer judgment and incumbent path custody with lower overhead than another conflicting worker. No worker/Fable, watcher, source-custody transfer, replacement branch/worktree or new control plane. Same Studio carrier. Initial scope/ruling receipt: #8014 comment 5851966615.

## New capability in this continuation

Before: optional chart geometry/native evidence could exceed the server's chart-state limit and block the entire snapshot, including command ACKs. Parallel state uploads could arrive out of order. Identity lookup consumed ACKs before it could fail.

After, in untested source: one receipt-first bounded projection and its consumer use the EXISTING chart-state route/accumulator/scheduler. `terminal/lib/chartStatePayload.ts`:
- uses a conservative 60 KiB bound beneath the existing 64 KiB server validator, accounting for ASCII-escaped Unicode, separator spacing and numeric printer differences;
- retains the previous shape for small packets;
- reduces only the TRANSPORT drawing representation, first to ids/ownership then to a bounded roster with explicit returned/omitted/detail-omitted counts;
- preserves exact actual indicator settings, context identity and command ACK identifiers;
- withholds verbose native parameter descriptions/optional numerical packets only with explicit unavailable/omission markers when required;
- batches at most 32 FIFO ACKs, retaining every unsent receipt and refusing to truncate an unfittable first ACK or essential identity.

`useChartBus` prepares the packet before consuming ACKs, catches identity-lookup failure, coalesces newer updates behind one in-flight POST and drains successful remaining ACK batches without another market tick. Failed/non-2xx/aborted receipts restore once before newer ACKs. A four-second stalled-request deadline releases transport; another attempt after failure requires actual new/coalesced input, not a periodic retry loop. Unmount prevents deferred new requests. Request abortion is NOT proof of server non-execution; receipt transport is idempotent existing ACK reporting, not chart-mutation replay.

Protocol v5 explicitly consumes `session.mirror_coverage`: omitted telemetry is not deletion, a partial roster is not full inventory, and pending receipts are not evidence of an unexecuted/cancelled command. No guess of missing geometry, automatic broad-clear substitution or same-oversized-request loop. Protocol source was 7,509 characters, not a proved total routed-budget/model-compliance result.

The delivery delta does not close the collective two-second Brain ACK wait, late target adoption, or rendered-pixel/model acceptance obligations. A 4s stalled upload can still outlast that wait; do not claim a live-latency guarantee.

## Retained substantive native feature from the incoming source

Do not redo Terminal **dd8cb762bcae66b7613837d9a16e4762669ad5f3** or Macro **28437b9b02bf13ee4a2f58ec92d49f0b256dbcc8**:
- the renderer supplies actual consumed computeSuite bundles through one shared live/headless compact projector;
- live schema chart.native_live_observations.v1, 7168-byte limit, exact context/settings/replay/selection binding;
- latest native samples and exact selected_sample; causal event confirmation timing; right-edge geometry; dashboard rows/footnotes; explicit module/coverage/omission meanings;
- backend structural/context qualification and server-owned basis language;
- exact range application via existing paneSync, not start-only jump;
- Data Window `mc.rsi14` remains distinct from native `rsix/eng`.
These incoming commits were recovered and inspected, not rebuilt by this continuation or treated as proven live. A renderer snapshot is not point-in-time feed history, entitlement attestation, probability or measured trading edge.

## New held findings and refused actions

1. Source inspection found target production still occurs at model-result handling rather than a frozen original pane; the stream adopts revisions from all observed receipts rather than only a matched accepted requested context transition. This can move dependent edits toward a user-changed chart. A deeper compound target/source-fence inspection was refused BEFORE dispatch. EFFECT_NONE, not a repair. No retry/split/reroute or mode-derived permission.
2. A selected-candle native projection implementation write was refused BEFORE dispatch. Its intended historical-event view, linear latest-sample scan, raw native-gap parity and budget-scan refinement are NOT applied. The original nativeObservationProjection.ts is preserved. Tests authored before that request were moved OUT of test discovery to `docs/research/CMX_NATIVE_SELECTION_DEFERRED_TESTS_2026-09-26.ts.txt` (Terminal) and `research/CMX_NATIVE_SELECTION_DEFERRED_TESTS_2026-09-26.py.txt` (Macro). They are proposed future specifications only, not implementation or passing tests. The settings cases now name the independently authored canonical equality helper, without claiming its tests ran.

Those exact actions remain TOOL_DEGRADED / EFFECT_NONE. The independent delivery/protocol writes succeeded and are not retries of either denied operation. Older denied effects remain held under their existing receipts. Unknown refusal cause is not assumed technical recovery. No bypass through another mode, carrier, account or worker.

## Evidence and deferred qualification

New executable cases, authored but not run: **11** in chartStatePayload.test.ts; **7** in useChartBusDelivery.test.tsx. They cover server-size accounting/Unicode, small-packet compatibility, 70-ACK FIFO delivery, drawing immutability/coverage, optional-data omission, huge ACK refusal, cycles, in-flight latest-context coalescing, failure restoration, throwing identity, stalled requests, no periodic retry and unmount. Source whitespace checks passed; no compilation or runtime inference.

Next combined qualification must include these plus retained native exact-bar/settings/replay/null/entitlement/omission cases, headless/live parity, actual range behavior, command targeting and same-turn reads, cancellation/no-retry, old clients, dark/light/EN-ZH/responsive/accessibility and real-model/browser/pixel proof. Ancestor tests/CI green do not qualify the expanded candidate.

## DO_NOT_REDO / exact next action

Retain prior merges #740 61d55a7e1d12a9104f90d17bfa2cd8b16982ac6f; #751 3cb7dbd8e89cd5d932fd07b2961ca79a0847d552; #7999 dd9640ef69c5f4a12a8970fa4691821c3218dcfd; #8037 a3f20fbe75a33c146c2477d0f1491a184da1e29f; #8005 race-repair candidate d33286edc81478a62ebe847c58dee95c8d1f54fd. Retain additive edits, selective AI clear, feedback 37afbd7d74d4cf90e91bf2d858f1972b96c55fc2 and queued cancellation be9d86b2494f8cf5926f5826ec79e9eee2222118; never recreate the queue/kernel/catalog/identity/ACK owners.

Next: reconcile the actual current foreign native-validation return on the existing Macro branch without overwriting/staging it. Consume a genuinely permitted recovery/owner return for frozen original-target semantics and selected-candle causal/native projection; do NOT repeat the exact refused inspection/write merely on continuation. Preserve this published delivery slice. When feature construction is complete and the testing deferral ends, run the combined production-path qualification and normal #8005→#8014 release sequence, not incidental CI-driven acceptance.

This boundary completes a coherent source delivery/consumer slice after the native/target implementation paths were held, not the parent product. Remaining work is explicit. Intended continuation surface: Pro for source-return adjudication and cross-system semantics; request Extra High only for a materially useful capability transition, not refusal evasion. No autonomous wake/background continuation. EFFECT_UNKNOWN: none for this turn's own reconciled effects after publication. Foreign source custody is NOT released by this checkpoint.
