# Pullback-underway implementation plan

**Goal:** extend the existing US/China Risk Radar with observed pullback depth, defensible remaining-downside ranges and the new native Paper presentation. Do not create another risk engine, observation lifecycle, recovery gate or publisher.

**Architecture ruling after source recovery:** PR #8188 already implements the causal raw-close observer (`lib/pullback_observation.py`) and China adapter (`lib/china_pullback_view.py`). Reuse that implementation and its original carrier. The new source slice is only deterministic loss-quantile arithmetic; no competing observer or presenter is published. The initially tested normalized-snapshot prototype remains unpublished scratch and is superseded for integration.

**Stack:** Python standard library and pytest. UI integration stays in the existing Jinja/shared-dialog/CSS system. Forecast fitting stays off the render path.

**Spec:** `PULLBACK_UNDERWAY_RESEARCH_2026-10-09.md`. This commission authorizes research, design and build initiation, not unsupported forecast publication or bypassing existing release gates.

## Source, ownership and custody

Protected Mastermind Skillpack `326c8469a21d7f50fc9ecb1848196bf1c6e66685`. Macro investigation `b29ba7102d35bebf6f322c1d6fadf8309726bf4e`; fresh publication base must be recorded in the source receipt. Existing observation candidate: #8188 head `ff27a268abaacfdb50534a60d1ca4ffe7a119938`, semantic source `2270b9f43dbc6b8e015adb1a00b950eb46533a5c`, original operation `cn-pullback-lifecycle-20260929-sol-001`.

#8188 is Draft/HOLD and was not mergeable at this recovery. Its historical tests and browser evidence are not current-base, new-design or production proof. Do not modify its branch/workspace, release its hold or substitute a new PR for that operation. #7029 recovery safety, #8132 warning delivery, #7875 semantics and #7592 breadth/null holds remain intact. #8648 carries the current alertful Risk Radar planning context.

Native Paper file `01M38EVF74SJWG1GANN5VP380Z`, page `p-1-0`: US `9TH-0`, China-unavailable `9WB-0`, mobile-stabilization `9ZG-0`. They are illustrative, not forecast evidence. The exact confirmed snapshot is a drift guard, not a revision or permission grant.

No worker has started for this operation; Executive V3 was observed readonly. No Job/Attempt or independent review is claimed. Local container files are a test kit, not the shared Mac checkout.

## Task 1 — additive depth arithmetic (this slice)

Create only `lib/pullback_depth_projection.py` and `tests/test_pullback_depth_projection.py` for code. Interface:

`project_total_drawdown(peak, current, trough, additional_loss_fractions) -> tuple[float, ...]`

The caller supplies a coherent, same-basis active observation from the existing observer and sorted loss quantiles from a separately qualified forecast. The helper does not accept a risk score, authenticate a forecast, detect an episode, read clocks, emit a source feed, or grant policy authority. It converts each additional loss A into `max(1-T/H, 1-(P/H)*(1-A))`.

1. Write tests first and observe their expected missing-module failure.
2. Implement the arithmetic and strict finite/domain/order validation.
3. Test exact examples, prior-trough floor, zero/total additional loss, scale invariance, invalid numbers and unordered quantiles.
4. Run the entire isolated kit command and compile the published helper. Record source/test hashes. A green kit is not a green Macro repository or forecast validation.

## Task 2 — consume the existing observation and release carrier

Reconcile #8188 on its original carrier: current-base conflicts, exact-head CI, admitted independent review and existing publication proof. Preserve its 63-close causal reference, 2%/two-close onset, 5% shock, frozen-peak retention, missing-session handling and explicit trend-repair/reclaim resolution as candidate contracts; this extension does not retune them. Unmerged candidate text does not become protected law merely by citation.

Use `lib/china_pullback_view.py`'s `snapshot`/`present` contract for China: benchmark `000001.SS`, `close`, `peak_close`, `low_close`, `peak_session`, `asof`, `source_digest`, `valid_until` and source availability. Its `loss_recovered_pct` is the fraction of the peak-to-low loss recovered, not the rebound return; preserve that distinction. Keep stale observations dated and non-current.

Qualify the US source/calendar/basis adapter for the same existing `observe()` implementation. Do not copy a detector into a US-specific module. SPY is the design example; the owning route's exact production benchmark and adjustment basis must be verified before binding. This is a source-adapter qualification task, not another history store. Chronicle/Reflex/QLedger remain owners of issued-event history; the observer's retrospective dates are not issued alerts.

## Task 3 — replace content in the existing shared popup

Join through `templates/_risk_radar_dlg.html.j2` and the existing `_pullback_observation` partial family after same-carrier reconciliation. Retain the existing opener, focus/escape/close behavior, scroll, backdrop, country context, source-clock evidence, localization, navigation and same-context return. No second modal framework, endpoint, route, token root or publisher.

Lead with observed depth, additional downside and implied total depth; show worst drawdown and the distinct rebound return. The chart is observed price plus projected cumulative worst episode depth, not a forecast price path. Preserve pre-pullback, forecast-unavailable, stale and partial-data states. Forecast absence never becomes zero risk.

Dark: graphite instrument surface and restrained damage field. Light: deliberately composed cool workspace, white material, hairline discipline and shadow instead of glow. The new pullback light design and dark/light × EN/ZH × 1440/390 evidence matrix remain release work, not a completed claim. Include keyboard focus/return, reduced motion, no-script and source-expiry checks. Preserve existing HK/Canada shared-dialog behavior and its evidence obligations.

## Task 4 — statistical pilot, separate from UI launch

Preregister bounded-horizon future-minimum targets for 5/10/21 local sessions. Compare conditional historical/volatility-filtered baselines against regularized conditional quantiles. Use causal raw data, real availability clocks, episode-grouped rolling out-of-sample folds, matured labels and overlap purging. Report independent episodes, pinball loss, interval coverage/width and tail exceedances by country and stress state.

Publish no numeric forecast until the exact market/benchmark/basis/horizon and licensing/validation receipt are accepted. A US receipt cannot authorize China. Missing calibration must render the designed unavailable state. A point-in-time price observation can ship independently of forecast promotion through the existing release gates.

## Task 5 — staged rollout and verification

The existing delivery path owns US/China publication. Use its existing feature-selection mechanism only after it is verified; do not invent a flag service. First verify measured-only states, then the qualified forecast in shadow, then scoped rollout. Rollback restores prior content without changing observation/history/engines. Confirm both served page and canonical machine artifact; a Paper screenshot, draft PR, green unit suite or merge alone is insufficient.

## Verification frontier

The outcome requested here is research + native design + source build initiation. Full US/China replacement, country-specific predictive qualification, independent release review and production acceptance remain obligations. No release hold is removed by this plan.
