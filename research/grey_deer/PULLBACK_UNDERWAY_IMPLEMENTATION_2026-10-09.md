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

## Measured-only fragment contract — implementation increment

Files: `templates/_risk_radar_pullback_depth.html.j2`, its `.css.j2` companion, and `tests/test_risk_radar_pullback_depth_template.py`. Interface: `detail(mkt, view)`, where `view` is the existing `china_pullback_view.present()` shape, not a new observer result. The fragment validates display-domain inputs but never detects or reclassifies episodes. Both country consumers share this fragment; the US raw-source adapter still needs its own qualification.

The component shows current drawdown, retained worst drawdown and rebound return as distinct observations. Every further-depth forecast remains unavailable, even if a caller passes the incumbent probability or an unqualified forecast. Source time and market identity remain explicit. Missing/malformed or contradictory source shape does not become a calm reading. This is an unconnected component until the existing held source carrier is reconciled; no production popup has been silently changed.

The fragment keeps `.pbx-heading`, `.pbx-current`, `.pbx-expiry`, and `data-pb-valid-until` for the existing observation expiry owner. It creates no dialog, opener, event listener, timer, fetcher or history store. Production integration must load the existing expiry owner exactly once. Dynamic labels/attributes are escaped even when the legacy Jinja environment disables autoescape. Chart HTML is trusted server-generated `lib.illus` output, not arbitrary user input.

Dark treatment is a graphite instrument with restrained luminance separation. Light treatment is a white headline/metric field, a cool research canvas and two white evidence cards with hairlines and canonical shadow. Directional numbers follow EN/ZH up/down conventions; fixed health/uncertainty labels do not flip. No new palette or token root.

The new tests were observed RED before implementation. The first focused batch (new fragment, arithmetic and existing shared-dialog tests) passed 103 tests. Full integration/current-source/browser evidence and repository CI remain separate gates. Both new suites are registered in the existing engine-render-guards run step; no new CI job or exemption.

## US price-basis qualification — selected source contract

The source census resolved the US ambiguity. At source `a6ca347527689fe4eba01967fabd5c98f8a50602`, `collectors/yahoo.py` (blob `c4a16844e604f577b21a7eb30459ed6b89bfcb14`) defines `close_price` as split-adjusted but dividend-unadjusted and `close` as split-and-dividend-adjusted. The existing Risk Radar reads `close`; a new observed price-depth adapter must deliberately select and label `close_price`, not quietly reuse the incumbent forecast series. No existing risk calculation is retuned by this choice.

The direct local store census had 8,481 rows, both columns complete, through 2026-10-08, file SHA256 `6c785d556c22e20f85f89f55597b10469f0fc4c40a577b8efb04bc11964a3152`. At the observed 2026-10-10 00:07 UTC check, the owning NYSE calendar expected the October 9 close, so the native observer correctly returned `unavailable/delayed`. This is a dated source snapshot, not current served-market evidence. Replaying only through the last stored session demonstrates why the distinction matters: the price basis retained a recovering episode, while the total-return basis was already monitoring. Neither reading is an entry signal or newly accepted forecasting result.

The next US adapter contract is therefore: the existing `lib.pullback_observation.observe()` consumes untouched `yahoo/SPY.close_price` daily observations, `lib.nyse_calendar` supplies the expected session and successor deadline, and the caller carries `price_basis=split_adjusted_dividend_unadjusted_close` with explicit user copy. Missing `close_price` must be unavailable, never a fallback to `close`. Intraday timestamps, missing expected sessions, source revisions and prior-trough retention keep the existing observer's rules. Implement this adapter only against the reconciled existing observer dependency, not a second copied detector.

The shared component remains unconnected to production. Its current validation is 206 passing focused arithmetic/fragment/shared-dialog/country-wiring tests, plus 16 browser cases exercising both countries, both languages and both themes at 1440/390. Browser checks verify native disclosure keyboard behavior and the existing producer-deadline expiry mechanism, including hiding stale metrics. The first browser probe caught missing global spacing/radius definitions; canonical design-system fallback values now preserve 24px desktop/20px mobile header padding and 14px panel radius without a new token root. Full-repository acceptance and the original held source release remain separate gates.

The component also keeps observed chart ink visible without JavaScript and before scrolling into view. A real no-JavaScript mobile probe first failed with a 665.5px stroke offset (shared reveal choreography), then passed after a component-scoped final-state override. The shared illustration renderer and its global styles/JavaScript are unchanged. This is an intentional critical-information visibility choice, not a new chart engine. Final evidence lives in `research/grey_deer/pullback_depth_evidence/r3/`; earlier scratch captures are superseded and are not publication inputs.

## October 9 resumed implementation — bounded US page wiring

This source increment extends the original draft #8721 without changing the held #8188 observer or China dialog. It remains **BUILT_NOT_PROVEN** until current-base CI, admitted review, merged dependencies, real browser and release proof.

- `lib/us_pullback_observation.py` consumes the existing `lib.pullback_observation.observe` dynamically when available. The sole price source is `yahoo/SPY.close_price` (split-adjusted, dividend-unadjusted). The existing NYSE session calendar supplies the expected settlement and next expiry. Absence of `close_price` **never** falls back to the dividend-adjusted `close` field; an unmerged/missing observer, invalid data, gaps, and delayed closes stay unavailable.
- The local read-only integration smoke bound to held observer blob `54e7f0443d5b58d08a2a7327326e62766cc1ca0d` reconstructed a recovering SPY episode at the 2026-10-08 settlement, and correctly abstained at the 2026-10-09 expected settlement because the stored last close was October 8. The dated source does not prove a current live assessment or entry permission.
- `present()` uses the existing `lib.illus` renderer with an explicit SPY accessibility label; it does not accept, reclassify or publish a forecast/probability.
- `scripts/build_site.py` adds one view-model input to the existing macro/US dashboard render calls; `templates/dashboard.html.j2` keeps the original `#dlg-risk` modal and opener, switching to the Paper-derived measured-first fragment only for a current **active** price phase (`underway`, `stabilizing`, `recovering`). The incumbent forecast and risk-driver content remains inside an accessible disclosure and is not relabeled as remaining-depth probability. Missing/stale/monitoring sources leave the prior popup intact. No second dialog, risk engine, source feed, identity system or policy writer.
- The original US risk dialog exists on the Macro mode page; the stocks-mode fixture does not expose that specific dialog, so this change does not invent another stocks modal.
- The adapter contract suite, same-page modal render tests and build-site hook tests were RED against missing code and then GREEN. The larger focused suite must exclude one inherited test that directly reads sparse-omitted `site/theme.css` until canonical site materialization is separately admitted. That environment failure is not a successful real-page browser acceptance.
- New full-page dark/light × EN/ZH visual proof, exact-source CI, independent review, the held #8188 reconciliation, China replacement, qualified remaining-downside forecast and served-route verification remain open. No deployment/merge approval or active external worker is implied.

Next critical integration: reconcile the original #8188 carrier and join the new fragment into its existing China shared modal, preserving all price/expiry and country semantics. Then validate both served US and China pages in browser and qualify forecast models separately.
