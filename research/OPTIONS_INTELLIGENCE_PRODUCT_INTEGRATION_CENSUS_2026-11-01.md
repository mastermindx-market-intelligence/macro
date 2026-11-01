# Options Intelligence — product/integration census, Journey A checklist, P09 and W3B (2026-11-01)

**Author:** ORCH-2, an Opus sub-orchestrator of the Options Intelligence CEO seat (root `a1c77f0e-56b9-4edf-8d4f-3d31a338a8ed`, parent run `oi-a1c77f0e-orch2`).

**What this is:** a records document. It is not a release, a production proof, or acceptance. No switch was turned on and no owner decision was taken. Every seat-only act is listed in §8 and none of them was performed.

## 0. Pins

| Name | Value |
|---|---|
| TERM | `mastermindx-market-intelligence/mastermind-terminal` master `db6168c20ce42217ed99d9fa53e6048683505da5` |
| MACRO pin | `820f33b539c39f21f48f5e57a799cdbb5c196c6e` (engine reads). `engine/options_payoff.py` sha prefix `9123da75262b7e98` is the same at 820f33b5 and at main `8a446523`. |
| MACRO main at this commit | `8a446523bebc2fbaf831967c11c570f1d11818a8` |
| Incumbent ledger | `origin/claude/options-intelligence-e2e-program-20261011` @ `107f80d0af`. Read by line range only (D107 = L2580-2596). |

Claim classes used throughout:

- **observed** means read in a primary artifact at the stated pin.
- **calculated** means arithmetic on observed values.
- **interpreted** means ORCH-2's judgement.

`UNKNOWN` is never written as zero.

Appendices live in `research/options_intelligence_product_integration_2026-11-01/`:

| Appendix | Content |
|---|---|
| A | L2A, Journey A steps 1–3: route map plus the 15-cell state-truth table. Fabric oi2-l2a-r1, sha256 `14b1a229…`. |
| B1 | L1A rows AC37–AC46. Fabric oi2-l1a-r1, `8cfdb77e…`. |
| B2 | L1B rows AC47–AC56 and AC60. Fabric oi2-l1b-r2, `f88b2927…`. |
| C | P09 `options_exposure_node`: activation-OFF switch dossier. |
| D | AC40 W3B decision memo (the seat rules). |

## 1. L1 — row dispositions (AC37–AC56, AC60)

Each row has exactly one disposition. The evidence column cites the appendix line ORCH-2 opened, and through it the primary record.

| Row | Disposition | Evidence (opened) | Note |
|---|---|---|---|
| AC37 | DO_NOT_REDO_ACCEPTED | B1 L18. TERM `docs/OPTIONS_R1_PROGRAM.md`@69e8e9f0 L92. Compare 69e8e9f0…db6168c2 touches no W1A file. | The accepted live receipt still matches current source. |
| AC38 | DO_NOT_REDO_ACCEPTED | B1 L19. Same doc, L79: investigation `f7874c02…`, revision 1, "Matches the saved source". | |
| AC39 | DO_NOT_REDO_ACCEPTED | B1 L20. #1104 merged at 0aecf8e9. R15 = #1104 comment 6343024596. | |
| AC40 | GATED | B1 L21. #1104 comment 6526883926 has no answer. Appendix D proves the premise for option B (macro `engine/options_hub.py:184,188-189,226`). | **The seat rules** (§6). |
| AC41 | GATED | B1 L22. R1 doc L119. The #599 scan has 0 w3c hits. | Needs signed-in production watch → review proof. |
| AC42 | OWNER_HELD | B1 L23. #804 head `00cf938d`, draft, dirty. | Incumbent; read-only. |
| AC43 | OWNER_HELD | B1 L24. #804 fields; no reconcile receipt in #599. | L1A records this as GATED on an original-operation reconcile. That gate sits inside the incumbent's #804 lane, so per the commission it is OWNER_HELD. |
| AC44 | OWNER_HELD | B1 L25. R70 comment 6382806783; the repair is not on master. | #804 |
| AC45 | ACTIONABLE_NOW | B1 L26. R17 = #1144 comment 6539302833. `pinnedResearchSharingPreviewTruth.test.tsx`@db6168c2 → 404. | → L3 Series A (§4). |
| AC46 | ACTIONABLE_NOW | B1 L27; ledger L1900. | The 4,214-portfolio rational oracle was run on `terminal/lib/optionsPayoff.ts` at #781 head 85d9f4ea. **That file is absent on master db6168c2** (observed). The live Plan engine is macro `engine/options_payoff.expiry_payoff`, and no Fraction oracle exists in macro tests (observed). The action is to port the existing oracle onto `expiry_payoff` single/vertical as a dated receipt. That is a port, not a redo. Not executed → GAPS. |
| AC47 | DO_NOT_REDO_ACCEPTED | B2 L9. TERM `terminal/app/api/options/plan/expiry/route.ts#L49-L51`. | |
| AC48 | GATED | B2 L10. R35@820f33b5 L57-59 (private install, installation proof, independent review). | |
| AC49 | DO_NOT_REDO_ACCEPTED | B2 L11. #1183 merged at fd010145. | Source and CI only; **not** PRODUCTION_PROOF. |
| AC50 | DO_NOT_REDO_ACCEPTED | B2 L12. #1182 merged at b1ba8e7c; #599 comment 6540472904. | |
| AC51 | OWNER_HELD | B2 L13. Macro #8920 head 23bd4769 is open. | |
| AC52 | OWNER_HELD | B2 L14. R73@820f33b5; #599 comment 6333686799 is open. | ExposureMap `returnCheck` is not touched. |
| AC53 | DO_NOT_REDO_ACCEPTED | B2 L15. `options-ia-responsive.spec.ts` (blob d3e5eb34). | The W3B question is AC40, not this row. |
| AC54 | ACTIONABLE_NOW | B2 L16. Code search found `axe` in 6 e2e files, none of them options; `checkA11y` found 0. | W5 a11y. Not executed → GAPS. |
| AC55 | DO_NOT_REDO_ACCEPTED | B2 L17. #599 R12 comment 6504497416. | The deployed tip b1ba8e7c lags master. The delta is covered by the standing deploy process. |
| AC56 | OWNER_HELD | B2 L18. coo-fable (R06 L16); macro #7728 / #10065. | |
| AC60 | GATED | B2 L19. R02@820f33b5 L95 `decided_by: ceo-sol`. | Closeout by the existing decision owner. |

Totals: 8 DO_NOT_REDO_ACCEPTED, 6 OWNER_HELD, 3 ACTIONABLE_NOW, 4 GATED, for 21 rows.

## 2. L2 — ENTITLED-RENDER CHECKLIST (Journey A, D107 steps 1–4 and 6)

**Who runs it:** the seat, signed in with an account entitled to `terminal_live_options` (or tier `unlimited`). ORCH-2 and its workers never sign in.

**Origin:** `<TERMINAL>` is the production Terminal origin.

- `terminal/next.config.ts` has no `basePath` (observed), so routes sit at the origin root.
- Source names `https://app.mastermind-x.com` as the Terminal app host, for example `terminal/app/embed/chart/EmbedChart.tsx:87` (observed).
- That this is the origin serving `/options` today is **unverified**. The seat confirms it.

**Run conditions:**

- Theme: **dark only**. Terminal is DARK-ONLY, so there is no light cell.
- Language: use the in-app language control. ZH follows the red-up convention.
- Run during the US regular session (Mon–Fri 09:30–16:00 ET) for the "regular" cells. 2026-11-01 is a Sunday, so a weekend run must expect the closed-session values marked †.

**Viewport × language grid.** Each step is one row; mark every box. Viewports follow `terminal/playwright.config.ts:65-67`. The 820×1180 ZH cell is required, because ZH is tablet-bound in `options-ia-responsive.spec.ts:13-19`.

| Step | 1440×900 EN | 1440×900 ZH | 820×1180 EN | **820×1180 ZH** | 390×844 EN | 390×844 ZH | a11y (keyboard / focus / live) |
|---|---|---|---|---|---|---|---|
| 1 Reach Options/Flow | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 2 SPY tape current (r4) | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 3 One SPY call, exact terms | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 4 Expiry payoff (research expression) | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 6 Selected-node watch is OFF | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

Step 5 (Save) is **GATED** and not exercised. The Save gate is at `terminal/components/researchlab/OptionsResearchLab.tsx:185`, owned by incumbent #804. Do not click any save or persist control.

### Step 1 — the entitled user reaches Options/Flow

1. Open `<TERMINAL>/options`. Expect the workspace, not the paywall.
   - Gate: `terminal/app/(shell)/options/page.tsx:34-38`. Denied renders `OptionsPaywall`; unavailable renders `OptionsServiceUnavailable`.
   - **Fail** if either the paywall or the unavailable screen appears for the entitled account.
2. Expect the default tab, Tape ("Tape"/"逐笔", `terminal/lib/i18n.tsx:1289`).
3. Open `<TERMINAL>/options?tab=desk`. Expect "Flow Desk"/"资金流台" (i18n L1288), with the FeedPane list.
4. Optional, for the denial cell: in a private window that is signed out, `/options` shows the paywall. Signing out is the seat's own act.
5. a11y: the tab list is reachable by Tab, focus outlines are complete, and the active tab is announced.

### Step 2 — the SPY tape is current under r4

The bound is r4: `asof − cycle_started_at` of the **same** `live_flow.meta/v2` receipt (D107 L2580-2596). For the r1 receipt that was 1692.632 s (calculated). A root is current iff its `last_source_success` falls inside the cycle that produced `asof`.

1. On `/options`, read the freshness receipt (`terminal/components/flowdesk/FlowFreshnessReceipt.tsx:17-25`). Expect these labels: "Connected"/"已连接", "Snapshot"/"快照", "Source responses"/"源响应", "Observed cycle"/"实测周期".
   - **Fail** if it shows "Timing unavailable"/"时间信息不可用" for more than one 25 s refresh. A single flash is a known RISK (Appendix A cell 2.4).
   - † Outside the session it reads "Market closed"/"市场休市" or "Last session"/"上一交易时段" (`terminal/lib/flowFreshness.ts:161-193`). That is a pass for the closed-session cell, not a fail.
2. Open `/options?tab=statistics` and select SPY. Expect **"Acquisition: Latest scheduled source request succeeded"** / "数据获取: 最近计划的数据源请求成功" (`terminal/components/options/OptionsStatisticsView.tsx:52`, decoded at `terminal/lib/optionsObservedStatistics.ts:80-92` from `meta.root_catalog`).
   - "Latest scheduled source request failed", "Not requested in the latest cycle" or "Current source status unknown" is a **fail** for step 2.
3. Optional numeric r4 check. This is one authenticated GET, `<TERMINAL>/api/flow?f=meta`, in the same signed-in tab. Record:
   - `asof`, `cycle_started_at`, and the bound `asof − cycle_started_at` in seconds;
   - SPY `root_catalog[root=SPY].last_source_success`.

   Pass iff `cycle_started_at ≤ last_source_success ≤ asof`. Do not GET `/api/flow/ticker/QQQ`. QQQ is excluded (r2).
4. Client stale rule: an `asof` older than 600 s shows the "delayed" chip (`isStale`, Appendix A §1.2). During the session, a delayed chip is a fail. † After the session it is expected.

### Step 3 — one SPY call with exact terms

1. On Tape, find a SPY row with right **C**.
   - Expect: time (24 h ET), `SPY`, the side pill, `C`, contract `${strike}C MM/DD`, DTE and moneyness chips, size, and premium. Source: Appendix A §1.3, `terminal/components/OptionsHubView.tsx` tape row.
   - Write down the strike, expiry and premium.
2. On Desk, the same contract's FlowCard reads `$strike · YYYY-MM-DD · Nd` (`terminal/components/flowdesk/FlowCard.tsx`).
   - OI and IV render **nothing** when absent, never 0 (FlowCard L224-235).
3. **Known defect, check it explicitly.** If a card has no flow score, the ring currently shows **0** (FlowCard L122-123, ring L168). WatchlistRail does the same (L98). Until L3 Series B merges, this cell is an expected **FAIL** of "unknown is never zero". Record it as such; do not pass it.
4. "Long" is the user's research assumption. The tape side pill is an inferred print side, not the user's position. Exact terms (multiplier 100, physical settlement) are confirmed only in Step 4. D107 r10 records step 3 terms/multiplier coverage as UNKNOWN.

### Step 4 — research expression (expiry payoff via macro `engine/options_payoff.py`)

Chain at TERM: `/options?tab=screener` ("Screener"/"筛选", i18n L1294) → preset "ΔOI Builds"/"持仓增长" → pin the SPY call (ContractPinButton) → tray (`OptionsHubView.tsx:3645-3652`) → "Plan from pinned contracts"/"用固定合约创建计划" → the `OptionsPlanPayoffPanel` editor.

1. Enter side = long, quantity 1, and an entry assumption **P** in USD for the call with strike **K**. Press "Calculate expiry payoff"/"计算到期损益".
2. Two outcomes are truthful. A curve that appears without a READY state is a fail.

**READY outcome** (`terminal/components/options/OptionsPlanPayoffPanel.tsx:133-140`):

- Expected values (calculated oracle, multiplier 100):
  - "Worst expiry outcome"/"最差到期结果" = **−P × 100** USD.
  - "Best expiry outcome"/"最佳到期结果" = **"Unbounded gain"/"收益无上限"** (L113).
  - "Breakeven underlying price"/"标的盈亏平衡价" = **K + P**.
- Limit copy (L140): "Hypothetical expiry prices; fees, early exercise and assignment are excluded. This is not a current valuation or fill."
- Coverage lines (L129-132): "Dated reference coverage: N SPY contracts · Expiry: …" and "Dated terms as of … · Captured …". These dates are the terms clock. Record them.
- ZH profit stroke is red-up, rgb(240,86,107); EN is rgb(38,194,129) (`terminal/e2e/options-plan-payoff.spec.ts`).

**UNAVAILABLE outcome** (L128): "Contract terms unavailable. Your draft is kept here; check the selected contracts before calculating again." / "合约条款暂不可用。…"

- There is **no curve svg**. The coverage line may still list the dated expiries. Pick a contract on a listed expiry and calculate once more.
- This is a truthful pass of the "unavailable" cell. It is not step 4 READY.
- Server cause: macro `engine/options_plan_expiry.prepare_expiry_payoff` returns 422 `contract_terms_unavailable` when no Massive reference observation shows multiplier 100, 100 underlying shares and physical settlement.

**Conditional vertical scenario** (optional; a scenario only, never a recommendation): long K1 call, short K2 call, same expiry, net debit D.

- Worst = **−D × 100**; Best = **(K2 − K1 − D) × 100**; Breakeven = **K1 + D**.
- `classify_shape` labels it "vertical" (`engine/options_payoff.py:296-316`).
- Mixed expiries must show "Use contracts with the same expiry for this curve." / "此曲线须使用相同到期日的合约。" (L114).

**Other cells:**

- 390×844: the editor reflows below 620 px (`options-shortlist-plan.spec.ts`).
- On close, focus returns to the opener.
- Access cell, if the entitlement lapses mid-run: "Sign in with Options access to check terms. Your draft stays here." (L127).

### Step 6 — selected-node watch is OFF (observe only)

1. Open `/options?tab=gex` ("Exposure"/"敞口", i18n L1302; `OptionsHubView.tsx:4042-4044` → `GexDeskView` → `ExposureMap`). Select any node.
   - Expected: **no** watch/entry control under the node. `terminal/components/exposure-map/FrozenNodeEntry.tsx:25-27` returns `null` while `NEXT_PUBLIC_MM_OPTIONS_FROZEN_ENTRY_ENABLED` is OFF, and the mount is at `ExposureMap.tsx:271`.
   - **Fail** if any entry control renders.
2. Settings has no URL. Open it from the account menu → Settings → "Alert delivery"/"提醒送达" (`SettingsPanel` nav L59; i18n L2002).
   - Expect the chip "Price nears an exposure level I selected"/"价格接近我选定的敞口价位".
   - Expect the note "Notification preference only. Exposure-level alerts are not available yet." / "这仅保存通知偏好。敞口价位提醒尚未开放。" (`terminal/components/settings/SectionAlertDelivery.tsx:474`).
   - **Do NOT toggle the chip.** Toggling writes an account preference.

## 3. State-truth table — steps 4 and 6 at TERM db6168c2

The 15 cells for steps 1–3 are in Appendix A §2.

| Step | State | Locator | Rendered truth | Verdict |
|---|---|---|---|---|
| 4 | idle / empty | `OptionsPlanPayoffPanel.tsx:124` | A sentence telling the user what to do. | OK |
| 4 | loading | L122 `aria-busy`, L125 `role="status"` | Text "Checking contract terms…". There is no true-geometry skeleton. | RISK (interpreted, minor): a design-law gap on a short POST |
| 4 | incomplete | L114-116, L126 | One of three exact reasons (expiry / unsupported / legs). | OK |
| 4 | access 401/403 | L104, L127 | The alert keeps the draft. | OK |
| 4 | unavailable / error | L104, L108, L111, L128-132 | Says what failed, that the draft is kept, and gives a recalculation path. Dated coverage is shown when allowlisted. A parse failure is unavailable (fail-closed). | OK |
| 4 | ready | L109-110, L133-140 | Worst / Best / Breakeven. UNBOUNDED is mapped (L113). The limit copy is present. | OK |
| 4 | stale terms | L129-132 | The dated `as_of` / `captured_at` is shown, with copy that this is not a current chain. | OK |
| 4 | engine | macro `engine/options_plan_expiry.py` (blob 90adf015); `engine/options_payoff.py:296-316, 868+` @820f33b5 | 422 when terms are not proven. NullStates QUOTE_MISSING, MULTIPLIER_UNKNOWN and INCOMPLETE_LEGS. Outcome `conditional_not_realized`. | OK |
| 6 | entry control | `terminal/components/exposure-map/FrozenNodeEntry.tsx:25-27`; `ExposureMap.tsx:271` | `null` while OFF. No fake control. | OK (OFF) |
| 6 | server entry | `terminal/lib/frozenNodeEntryServer.ts:18` | 409 `frozen_entry_disabled`. | OK (OFF) |
| 6 | settings copy | `terminal/components/settings/SectionAlertDelivery.tsx:474` | States that this is a preference only. | OK |

## 4. L3 — defect repair

Both series were built by Fabric lane oi2-l3-r1 (§7). ORCH-2 then:

- exported the artifact `OI2_L3_PATCH.md` (sha256 67869247…) and verified it;
- applied each mbox with `git am` onto TERM db6168c2 and reproduced the worker's trees exactly (A `77f670f4`, B `71404b2f`);
- read both diffs;
- confirmed no file overlap with #1194, #1195 or #804 (the PR file lists were read 2026-11-01).

Each PR is a single commit on master db6168c2. Both are DRAFT; ORCH-2 did not mark either ready, label, arm or merge it.

**Series A — terminal #1197** (head `20d41a4918ebf896fc2dba15cb5d0b4f11f5b948`)

- **Defects:** AC45. `PinnedResearchSharing` showed "no saved scenario" for a failed preview read: HTTP 401/404/500/503, wrong id or revision, wrong status, or a missing manifest.
- **Fix:** a missing manifest now goes to `setScenario("failed")` ("could not be verified" / "无法核实"). An exact empty manifest still shows none. Refresh recovers with no share or revoke write.
- **Files:** `terminal/components/settings/PinnedResearchSharing.tsx` and the new `terminal/lib/__tests__/pinnedResearchSharingPreviewTruth.test.tsx`.
- **Tests (worker-reported; trees reproduced by ORCH-2):**
  - against the unchanged component: 18 failed / 6 passed;
  - with the guard: 24 passed;
  - the existing suite: 22 passed;
  - `tsc` exit 0.
- **Red check, named and diagnosed (observed, CI run 41293618917, job 124809797160):** "Terminal unit + typecheck (shard)" fails with `Test Files 1 failed | 1029 passed | 5 skipped`. The one failure has nothing to do with Series A. It is `terminal/lib/__tests__/reportedOwnershipPanel.test.tsx:290` ("does not treat an old REPORT date as staleness on a fresh acquisition"; blob 9ee56afd at TERM db6168c2).
  - Cause: the fixture pins `PAST_ACQUIRED = "2026-10-02T04:52:16Z"` at L35, while the panel validates against the real clock (the comment at L32-34 says so).
  - From 2026-11-01 the acquisition is 30 days old, so the panel prints "Retrieved 30 days ago (30-day disclosure threshold)" and the `not.toContain("disclosure threshold")` assertion fails.
  - It is a wall-clock time bomb that predates this change, and it hits every Terminal PR run on or after 2026-11-01. Master pushes run only `sweep` and CodeQL, so master shows no red for it.
  - The "plain-language" error annotations in the same job are the guard's self-test fixture receipt (`terminal/components/Bad.tsx:2`). The guard's own C1–C3 tests pass, so they do not block.

**Series B — terminal #1198** (head `719fff3694feac5413685116311c36a329202c3c`)

- **Defects:** an unknown flow score rendered as 0:
  - `FlowCard` L122;
  - `InspectorPane`, which also defaulted an unknown tier to LOW;
  - `WatchlistRail` best-of, which used `?? 0`.

  Separately, `FeedPane` showed skeletons forever on a failed feed read, because `FlowDeskView` dropped `status` and `retry`.
- **Fix:** `RingGauge` accepts a null value: the track only, "—", a muted tone, and a localized label. A tier chip renders only when the tier is known. `FeedPane` gains load-error, absent and refresh-failed states, and the watchlist rail gains unavailable and absent notes. New strings are added in EN/ZH.
- **Files:** 9 in total:
  - `terminal/components/flowdesk/{FeedPane,FlowCard,FlowDeskView,InspectorPane,WatchlistRail}.tsx`;
  - `terminal/components/ui/RingGauge.tsx`;
  - `terminal/lib/flowdeskStrings.ts`;
  - two new tests.
- **Tests (worker-reported):**
  - RED against the unchanged sources: 10 failed / 4 passed, and 7 failed / 4 passed;
  - GREEN: 25 passed;
  - 17 related suites: 289 passed;
  - `tsc` exit 0;
  - plain-language guard: 0 blocking;
  - Playwright: chain-heat failure 3 passed; card geometry plus freshness 6 passed (desktop/tablet/mobile); w2a plus chrome 30 passed / 1 failed.
- **Red checks, named and diagnosed:**
  - The w2a failure (`w2a-workspaces.spec.ts:876`) reproduces on a clean db6168c2, so it predates this change.
  - Evidence-lock test `terminal/lib/__tests__/eodHeatmapFlowdeskLoadFailureEvidence.test.ts` ("each layoutFiles sha256 matches the file on disk") goes red. `terminal/docs/pr-crops/eod-heatmap-flowdesk-load-failure/EVIDENCE.yml` sha256-locks `FlowDeskView.tsx` (`7c4ee44e…`) and `flowdeskStrings.ts` (`7b2a88ac…`), and this PR changes both.
  - The evidence-lock repair is to recapture with `terminal/e2e/tools/capture_eod_heatmap_flowdesk_load_failure.cjs` and restamp `layoutFiles`. It is open (§8).
  - Observed in CI, check run 124809824137 "Terminal unit + typecheck (shard)": exactly two failures.
    - `eodHeatmapFlowdeskLoadFailureEvidence.test.ts:93`: "FlowDeskView.tsx changed without a recapture: expected '36d99a98…' to be '7c4ee44e…'". This is the expected lock.
    - The same `reportedOwnershipPanel.test.tsx:290` wall-clock time bomb as Series A, which predates this change.
    - Ingest + signal-layer tests and Quote Hub tests are SUCCESS at 719fff36.

The independent review of both PRs (and of this record) is the combined review lane (oi2-rv-r1, r2, then r3 if admitted; §7). Its outcome is recorded there.

## 5. L4 — P09 dossier

See Appendix C. The four activation-OFF switches plus the fifth delivery gate are all OFF. The observed production value of `OPTIONS_FROZEN_DELIVERY_ENABLED` is UNKNOWN.

## 6. L5 — AC40 W3B memo

See Appendix D. Recommendation (interpreted): **B**, which anchors interpolated dates to the payload `asof`; **C** is the minimal alternative. Option B's premise is proven at macro `engine/options_hub.py:184,188-189,226`. The counterexample σ(7)=33.166247903554% (calculated) shows the mixed clock. The seat rules; ORCH-2 decides nothing.

## 7. Lane table (Fabric only; 0 native Agent/Task/Workflow calls)

14 of 14 lanes used: 5 DELIVERED (4 census and 1 build), 9 refused before any worker started. Fabric acceptance (observed, `fabric_task.py status`): oi2-l1a-r1, oi2-l1b-r2 and oi2-l2a-r1 are `ACCEPTED` by reviewer (`VALIDATED_OUTCOME`). oi2-l3-r1 is `NOT_ACCEPTED`; ORCH-2 deliberately did not accept it, because its independent review never ran. Every lane is C1_ROUTINE_BOUNDED on host ubuntu1. Unless noted, placement was pool `glm`, model `glm-5.3-flash`. That is observed in `ext/state/remote_sub/<id>.provider.json` (`provider: glm`, `model: glm-5.3-flash`) and in each request log's `LEASE_OK pool=glm`. Review lanes are placed on pool `grok` (`grok-4.7`) with `--subject-pool glm`, so the reviewer is on a different pool and model from the author.

| Run id | Class | Final state | Digest (remote stdout sha256 / artifact) | Adjudication |
|---|---|---|---|---|
| oi2-l1a-r1 | census | DELIVERED | c3d05e6b / `L1A_ROWS.md` 8cfdb77e | ACCEPT, opened (B1) |
| oi2-l1b-r1 | census | REFUSED `temperature_at_or_above_limit` | c21780dc | burned |
| oi2-l1b-r2 | census | DELIVERED | dbfe2fa1 / `L1B_ROWS.md` f88b2927 | ACCEPT, opened (B2) |
| oi2-l2a-r1 | census | DELIVERED | d945247c / `L2A_JOURNEY_1_3.md` 14b1a229 | ACCEPT, opened (A) |
| oi2-l2b-r1 | census | REFUSED pre-dispatch: no eligible mode (ubuntu0/2/3 disk, ubuntu1 thermal, ubuntu4 qualification) | — | burned; ORCH-2 direct reads |
| oi2-l4-r1/r2/r3 | census | REFUSED `temperature_at_or_above_limit` | 9f824445 / 5451af31 / a3bf5a7c | burned; ORCH-2 direct reads |
| oi2-l5-r1 | census | REFUSED `temperature_at_or_above_limit` | b7134b9b | burned; ORCH-2 direct reads |
| oi2-l3-r1 | build | DELIVERED rc=0 (worker STATUS PARTIAL: evidence-lock recapture not run) | 9a714cc3 / `OI2_L3_PATCH.md` 67869247 | ACCEPT pending review. ORCH-2 opened it, reproduced both trees with `git am`, and pushed them as terminal #1197 and #1198. |
| oi2-recrv-r1 | review (grok-4.7) | REFUSED `host_temperature_at_or_above_limit` | c62b0111 | burned |
| oi2-rv-r1 | review (grok-4.7), combined #1197 + #1198 + this record | REFUSED `host_temperature_at_or_above_limit` (09:42Z; load1 4.2/24, active 2) | 878421e9 | burned |
| oi2-rv-r2 | review (grok-4.7), same combined packet, records head b83a324b | REFUSED pre-dispatch: `no eligible remote mode` (ubuntu0/2/3 disk, ubuntu1 thermal, ubuntu4 automatic-qualification), rc=75, no remote stdout | — | burned |
| oi2-rv-r3 | review (grok-4.7), same combined packet, records head 29c5557f | Read-only `preview` at 09:57:19Z showed `grok`/`grok-4.7` on ubuntu1 (`selection_rechecked_at_request`). The request got `LEASE_OK pool=grok` and launched, then remote admission returned `REMOTE_SUB_ADMISSION_REFUSED` `host_temperature_at_or_above_limit` (load1 5.596/24, active 2), rc=75 | 1b3ab3f7 | burned; lane budget 14/14 spent |

## 8. GAPS, DEVIATIONS, seat-only acts

**GAPS:**

- **Independent review of #1197, #1198 and this record has not run.** This is the main open obligation. All three combined review lanes (oi2-rv-r1, r2, r3) were refused before any reviewer started:
  - ubuntu1 refused on `host_temperature_at_or_above_limit`;
  - the pre-dispatch blockers were ubuntu0/2/3 disk and ubuntu4 automatic-qualification;
  - the 14-lane budget is now spent.

  The repair diffs are therefore built (oi2-l3-r1) and opened by ORCH-2, but not independently reviewed, and the build lane stays NOT_ACCEPTED. The packet to reuse unchanged under a fresh id is `oi2-rv-r3.pkt` in ORCH-2's scratchpad, with 4.1–4.8, static review and READ_ONLY. Its blocker is capacity plus budget, not code. Resolution: a seat-granted lane budget once a router `preview` shows an eligible host and the remote temperature gate is clear, or a seat-commissioned read-only auditor.
- **Series B recapture and repair have not run.** No lane remains. The blocker is at TERM db6168c2: `terminal/docs/pr-crops/eod-heatmap-flowdesk-load-failure/EVIDENCE.yml` `layoutFiles` pins `FlowDeskView.tsx` at `7c4ee44e…`, and `eodHeatmapFlowdeskLoadFailureEvidence.test.ts:93` enforces that pin. Clearing it needs a run of `terminal/e2e/tools/capture_eod_heatmap_flowdesk_load_failure.cjs`, which starts next dev plus Playwright and is CPU-heavy. ORCH-2 does not run it on M2, which would route around the O-14 host-load refusal; it belongs on a Fabric lane.

- AC46 oracle port: not executed because of capacity.
- AC54 options axe coverage: not executed.
- `OPTIONS_FROZEN_DELIVERY_ENABLED` observed value: UNKNOWN.
- Terminal origin serving `/options`: unverified.
- The Series B evidence lock (#1198) is red until a recapture with `terminal/e2e/tools/capture_eod_heatmap_flowdesk_load_failure.cjs` and a restamp of `terminal/docs/pr-crops/eod-heatmap-flowdesk-load-failure/EVIDENCE.yml` `layoutFiles`, which pin `FlowDeskView.tsx` at `7c4ee44e…` and `flowdeskStrings.ts` at `7b2a88ac…`, at TERM db6168c2.
- `terminal/lib/__tests__/reportedOwnershipPanel.test.tsx:290` at TERM db6168c2 (blob 9ee56afd) is a wall-clock time bomb. `PAST_ACQUIRED = "2026-10-02T04:52:16Z"` (L35) crossed the panel's 30-day disclosure threshold on 2026-11-01. "Terminal unit + typecheck (shard)" is therefore red for #1197, #1198 and every other Terminal PR run today. This is outside ORCH-2's rows and files. The test-only repair is to pin the clock (`vi.useFakeTimers()` + `vi.setSystemTime`) or derive the fixture from `Date.now()`. No open Terminal PR touches the file (search 2026-11-01).
- `w2a-workspaces.spec.ts:876` ("an unreadable row is present, disabled, and no write fires on click") fails on a clean db6168c2 as well. It predates this work and is not caused by #1197 or #1198.
- L3 candidates not commissioned:
  - The OptionsHubView SSE skeleton (L1614/L2711). It overlaps #804/#1195, so it is left alone.
  - `RingGauge`'s known-value aria label, `${displayValue} out of ${max}`, which is still EN-only at #1198 `terminal/components/ui/RingGauge.tsx:130`. #1198 localizes only the unavailable label.
  - The violet `tierTone` for ELITE at `InspectorPane.tsx:422-426`. Violet is lock-only; this predates the work.
  - FlowGauge rendering missing components as zero (worker note B8, not in #1198).
  - The chain-heat Playwright route pattern is exact-match (worker note B9).

**DEVIATIONS:**

- L2 steps 4 and 6, L4 and L5 were done by ORCH-2's targeted direct source reads, after the Fabric refusals above and before any worker started. This is lawful under "no worker started + principal tools + no conflict".
- No production GET was made.
- **One combined independent review lane.** The review packet covers #1197, #1198 and this record, instead of one review lane per PR-bound artifact. Cause: 9 of the first 13 lane requests were refused before any worker started (§7): 7 on ubuntu1 temperature and 2 pre-dispatch, with no eligible host. The 14th and last lane is spent on this review (oi2-rv-r3), and only after a read-only `preview` shows an eligible placement, so it is not burned on a known-refusing host. The Series B repair or recapture therefore has no lane and is a GAP (§8).
- The §7 placement line in head c16b472d said "minimax MiniMax-M3", which was wrong. It is corrected here to `glm` / `glm-5.3-flash`, from the provider records.

**Seat-only acts (not performed):**

- the signed-in entitled render of §2;
- the AC40 ruling;
- any switch activation;
- marking a PR ready, labelling, arming, merging, or approving a review.
