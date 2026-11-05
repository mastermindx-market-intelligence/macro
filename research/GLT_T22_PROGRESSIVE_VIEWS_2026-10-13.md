# GLT T22 — progressive views on the liquidity and central banks workspace (2026-10-13 program, built 2026-11-02)

Program: Global Liquidity Transmission (GLT), task T22. Seat 10c41bc9; orchestrator ORCH-M.
Result head: see the PR body. Code commits: M1 `c8f1f862` (composer), M2r `d2cdcf4a` (projection, labels, presenter, tests) and M5r `59ae8f77`
(producer unchanged-gate repair), on base `f50fc7b7` with origin/main `b394a98b` merged in at `572b2dc3`.

## What T22 adds

Below T21's Now view, the existing `liquidity_central_banks` workspace now carries five additional row families, in this fixed order:

| family id | read-model block | EN | ZH |
|---|---|---|---|
| `glt_view_outlook` | `views.conditional_outlook` | Conditional outlook | 条件前瞻 |
| `glt_view_forecast` | `views.statistical_forecast` | Statistical forecast for bank reserves, Treasury cash and reverse repo | 银行准备金、财政部现金与逆回购的统计预测 |
| `glt_view_transmission` | `views.transmission` | Transmission evidence | 传导证据 |
| `glt_view_repricing` | `views.repricing_evidence` | Repricing evidence | 重新定价证据 |
| `glt_view_replay` | `views.replay` | Source-known replay | 按当时已知回放 |

Every row is an upstream-qualified read-model field. It carries its estimate type or disposition label and its clocks (`published_at`, `as_of`, `known_at`, `corrected_at` where they apply). The composer and the presenter format and select; neither computes a shock, response, confidence, gap, time-to-reprice or forecast. The views have no rank, size, trade, alert or posture authority.

## Field → render chain (grep receipt per hop, at `59ae8f77`)

1. **Composer (pure, I/O-free).** `engine/global_liquidity_views.py`:
   - L25 `VIEW_VERSION = "glt_views_v1"`;
   - L856 `def compose_views(`;
   - L499 `def _statistical_forecast(t09_package: Any, day: date) -> dict:`;
   - L815 `def _replay(history_records: Any, day: date) -> dict:`;
   - L633 `"reason_key": "science_results_not_published_to_product_plane",`.
2. **Producer attach (additive key only).** `scripts/build_global_liquidity_transmission.py`:
   - L25–27 `from engine.global_liquidity_views import ( VIEW_VERSION, compose_views,`;
   - L180 `views = compose_views(payload, None, t09, None, as_of=asof, outlook_inputs={"probe": probe})`;
   - L200 `payload["views"] = _compose_views(payload)`;
   - L247 `if trusted and prev_asof == new_asof and prev_hash == new_hash and views_current:`.

   A compose failure yields `views_compose_failed` and prints nothing. The unchanged gate also requires the stored
   `views.view_version` to equal `VIEW_VERSION`: a stored contract without the current views block (a pre-T22 nightly
   artifact) is rewritten once with its first-known clocks kept, and the next identical run writes nothing again.
   Tests: `test_t22_producer_rewrites_views_less_artifact_once`, `test_t22_producer_current_views_artifact_stays_unchanged`;
   the T23 idempotency tests pass unmodified.
3. **Workspace projection.** `engine/market_os/macro_workspaces/liquidity_central_banks.py`:
   - L616 `"metrics": {"items": metrics + _glt_view_rows(g, glt_asof, glt_repr_fresh)},`;
   - L1431 `_GLT_VIEW_FAMILIES = (`;
   - L1468 `_GLT_VIEW_NULL_BY_REASON = {`;
   - L1494 `_GLT_VIEW_OUTLOOK_REASONS = {`.

   The projection whitelists each family's composer vocabulary. Anything else is a display-contract refusal (`views_contract_refused`), never an inferred value.
4. **Labels (reviewed EN/ZH copy).** `lib/macro_suite_labels.py`:
   - L2288 `GLT_VIEW_FAMILY_NAMES`;
   - L2332 `entries["glt_view_forecast"] = _pair(`;
   - L2357 `METRIC.update(_glt_view_metric_entries())`;
   - L2388 `BASIS.update(GLT_VIEW_BASES)`;
   - L2393 `GLT_VIEW_DISPOSITION_TEXT`;
   - L2407 `GLT_VIEW_NOTES`.
5. **Presenter (note selection only).** `lib/macro_suite_view.py`:
   - L788 `or _prior_claims_note(snapshot, metric) or _glt_view_note(metric)`;
   - L2648 `def _glt_view_note(metric: Mapping[str, Any]) -> dict[str, str] | None:`;
   - L2675 `L.record_unknown(f"glt_view_note:{token}")`. An unknown note token is recorded, never invented.
6. **Template (unchanged).** `templates/macro_liquidity_central_banks.html.j2` L17 `{% import "_macro_suite_shell.html.j2" as shell with context %}`. The rows render through the existing shell metric grid. No template, CSS, JS, nav or shell file changes.

## The four views, as rendered

- **Conditional outlook.** Only two estimate types may carry a number: `announced_scenario` ("Announced scenario: follows a published schedule" / 已公布情景：依据已发布的计划) and `conditional_accounting` ("Conditional accounting: follows a stated assumption" / 条件核算：依据所设假设). Every note ends "Not a forecast." / 并非预测。
  - Scenario bounds carry "Scenario bounds, not probability. Copied from the stated scenario; never added together." / 情景边界，并非概率。照录所设情景，从不相加。
  - No total interval is ever formed.
  - The unexplained part of the reserves path is its own labelled row. It is never presented as a scheduled event.
  - On today's live envelope the H.4.1 Table 5 owner loader is missing, so the outlook renders `data_degraded` (`h41_table5_owner_loader_missing`).
- **Statistical forecast (K2).** It renders a disposition word, never a number. The T09 package is EMPTY (45/45 cells withheld, 0 issued), so live shows "Forecast rejected" / 预测已否决. A `supported` cell would still render "Not cleared for display" / 未获准展示.
- **Transmission evidence (K3–K7)** and **Repricing evidence (K8).** These render dispositions only: supported (numbers not cleared), rejected, insufficient, narrowed, not identified, unavailable. They show no effect, response, causal or repricing number. Regions render "Missing input" / 缺少输入, or "Inputs on file, no value shown" / 输入已存档，不显示数值. The seven cardless funds (efa, eem, gld, slv, dbc, uso, cper) render "Missing: no regional study design on file" / 缺失：无区域研究设计存档. "Observed association" is never placed on a K8 row.
- **Source-known replay.** It renders entries as known then ("Bank reserves as known then, entry 1" / 当时已知的银行准备金，第 1 条), with correction notes.

## States (C38): distinct in the API and in the UI

The projection maps each composer reason to a typed null state and freshness (`_GLT_VIEW_NULL_BY_REASON`, `_GLT_VIEW_FRESHNESS_BY_NULL`). The six states are asserted pairwise distinct in `test_t22_c38_six_states_are_distinct` (API) and in the composer's `test_c38_input_states_are_distinct`:

| state | API field | UI copy (EN) |
|---|---|---|
| missing | cardless fund row, no value | "Missing: no regional study design on file" |
| zero | `value` 0, `absence` None | "0", a value, never an absence |
| partial | `null_reason` NOT_COVERED on the pathless line (`component_unavailable`) | presence "Partial"; "Some lines have no path, so bank reserves are not shown." |
| warmup | replay `status` warmup (`issue_history_warming_up`) | "Warm-up: the issue record has started …" |
| revised | replay `revised_at` from a `source_revised` correction | "Corrected on 2 September 2026 …" |
| expired | forecast package dated after the page cutoff (`forecast_package_after_as_of`) | freshness "Not yet released"; "… dated after this page's cutoff" |

A stale page (journey E, `test_t22_journey_e_stale_page_turns_simulated_into_stale`) is the separate page-clock layer. `as_of_mismatch` refuses all five families as DISAGREEMENT (`test_t22_as_of_mismatch_refuses_all_families`).

## Replay law (C39)

A replay record is exactly `known_at / components_as_known / estimate_types_as_known / corrections`.
- `known_at` must be ≤ `as_of`.
- The value and type maps share one non-empty key set inside reserves/tga/rrp.
- Estimate types are restricted to `observed / announced_scenario / conditional_accounting / unavailable`. Illustrative or statistical-forecast types are refused, and so is an injected current value.
- A None value must be typed `unavailable`, and a number may not be.
- Each correction names a known field, sits between `known_at` and `as_of`, and uses a reviewed note key.
- At most eight entries, newest first.
- Leaving replay restores the current cutoff.

With no issue ledger yet, live replay renders `no_history` (`issue_history_not_recorded`).

## Words refused

These words never appear in a rendered view row, EN or ZH:
- EN: buy, sell, long, short, overweight, underweight, catch-up, upside, laggard, target.
- ZH: 买入, 卖出, 做多, 做空, 补涨, 上行空间, 目标价, and the substring 目标.

Probability wording on scenario bounds is refused, as is any `glt_confidence` attachment to a K-row number. Test: `test_t22_forbidden_words_absent_from_view_rows`. The rendered-page grep is in the PR body.

## Cross-repo dependency

There is no cross-repo reader. The macro product plane does not read Mastermind fixture archives, and no product reads `path_claim_allowed`. Transmission and repricing evidence therefore arrive as `{status: "unavailable", reason_key: "science_results_not_published_to_product_plane", owner: "Mastermind brain/liquidity_lab"}`. The page shows "Owner: the global-liquidity desk." / 所有者：全球流动性小组。 and no repository path.

Publishing qualified transmission and repricing results to the product plane belongs to Mastermind brain/liquidity_lab. Until it does, the highest lawful K8 label is a per-region `missing_input` with named owners.

## Treatments

DARK TREATMENT: existing tokens and components; no new material decisions.
LIGHT TREATMENT: existing tokens and components; no new material decisions.

## Gaps carried forward

- `scenario_bounds` has no upstream producer yet.
- K8 rows render live only as the owner-named unavailable state.
- The H.4.1 Table 5 loader is missing, so live K1 is `data_degraded`.
- No issue ledger exists, so live replay is `no_history`.
- Replay records declare no unit.
- The views appear on the producer's next nightly run, which rewrites the stored pre-T22 contract once.
- The unchanged gate checks the views version, not the views content: on a night with the same as-of and source hash,
  a change in T09 or the H.4.1 probe alone does not refresh the stored views (a failed views block is kept the same way).

## Review

A non-author review on 2026-11-02 found 0 blockers, 0 majors and 1 minor. With the T22 presenter and label code reverted, all 17 T22 audit, C37–C39 and journey tests fail, so none of them pass vacuously. The minor finding: the page now shows owner-describing copy, "Owner: the liquidity research lab." and "Owner: the global-liquidity desk." That copy stays. The K8 rule asks for named owners, and the internal owner identifier never renders.

The first render-proof run failed: the producer kept a stored pre-T22 contract unchanged, so the page showed no views.
M5r added the version check to the unchanged gate. The orchestrator, who did not write it, checked the change by
artifact: red first, then green, with two mutations each caught by the new tests.
The render-proof run 3 (M3c, glm-5.3-flash on ubuntu0, full-data tree at `59ae8f77`) passed: 72 matrix frames, 5 focus shots, the 320 no-overflow assertion, all checkers rc 0 and 0 forbidden words. The producer's head-vs-base wall time on that host was +0 %. Against the T23 BEFORE receipt from another host it was +13.6 %, and base on the same host shows the same rise.
