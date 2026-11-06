---
workstream: WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY
session: claude/r2-wire-scenario-surface-1021
model: fable
ended_because: complete
mission: >
  R2 TerraShade commission (acceptance.json schema mastermind.options.parity-research.v1,
  rows P01–P76, every row SPECIFIED_NOT_PRODUCTION_ACCEPTED): deliver the exposure
  intelligence program through the existing Terminal Options workflow as parent-owned
  slices. PR-1 qualified per-cell DEX extension + node reducer ported from the attached
  oracle; PR-2 Exposure map shell redesigned from the Paper R2 pin; PR-3 stored-session
  replay; PR-4 session review; PR-5 Discover scan table; PR-6 local linear scenario; PR-7
  strike × expiry surface. Separable slices were built on admitted fabric lanes (ubuntu3
  glm, pinned BASE sha, no fetch) and consumed by the parent, which wired them into the
  map. Delivery follows the Terminal chain commit → PR → merge-on-green → git-gated
  deploy → authenticated live verification.
prs: [1098, 1109, 1112, 1116, 1122]
decisions: ["DEC:OPTIONS-R2-ORACLE-OUTRANKS-FREEZE-TEXT"]
discoveries:
  - "DSC:TERMINAL-GLOBALS-CSS-EDIT-RELOCKS-THREE-EVIDENCE-PACKETS"
  - "DSC:FABRIC-LANE-BASE-DRIFT-FROM-HOST-FETCH"
state_before: >-
  Terminal master at 061e76255 (#1108). PR-1 (#1109, branch claude/r2-pr1-dex-reducer-1021,
  content head 52aa270aa) and PR-2 (#1098, branch claude/r2-exposure-map-ui-1021, content
  heads a8200a9cc + 20825722f) were open with the merge-on-green label and native
  auto-merge armed; the controller had refreshed both onto master (merge commits 43bd2204e
  and a955ad977) and CI was re-running. Lane branches were on origin and gate-verified:
  claude/r2-replay-frames-1021 d7d1c5c9f, claude/r2-session-review-1021 805d7dae1,
  claude/r2-local-scenario-1021 bd0201973, claude/r2-exposure-surface-1021 93db338cf.
  The PR-5 scan lane (r2-pr5-scan-1021-v1, BASE 52aa270aa) was still running on ubuntu3.
  The final design lives on the Paper page "Options · Exposure Intelligence · R2 ·
  2026-10-20" (file 01M3NSZGE8JWN2EZCSF0DT05RM, nine boards); the Astra mockups on the
  earlier page are reference only. The design pin, the F1 contract freeze and the
  acceptance coverage ledger existed only in the session scratchpad.
changed:
  - path: "mastermind-terminal:terminal/lib/exposureNodeReducer.ts"
    what: "PR-1 (#1109): node reducer v1 — net / gross / knownGross, dominant with tie set, runner-up ratio ≥ 0.9 contested, absolute-weight center, scope identity (basis); scanner_score and distance_fit ported literally from quant_oracles.py (distance_fit returns number | null)."
  - path: "mastermind-terminal:terminal/lib/exposureMapProjection.ts"
    what: "PR-1: qualifiedDeltaExtension validators V1–V10 for the per-cell DEX extension; receipt must match the parent's root, input_sha256, population_id, kind, position_basis, scale and unit; typed refusals wrong_root / receipt_mismatch / invalid_metric."
  - path: "mastermind-terminal:terminal/components/exposure-map/ExposureMap.tsx"
    what: "PR-2 (#1098): shell redesigned from the Paper pin (clocks strip, lens rail, stat strip, field with sticky axes, keyboard ±/0, inspector). Wiring branch (#1116): seven book-anatomy detail tabs (expiries, values, changes, replay, review, scenario, surface) with onLoadSession from the desk, the ExposureReviewTab / ExposureScenarioTab / ExposureSurfaceTab hosts, pin and Open-in-Exposure links from the surface."
  - path: "mastermind-terminal:terminal/app/globals.css"
    what: "PR-2: --exposure-positive / --exposure-negative / --exposure-selected tokens; this edit relocked three evidence packets that were recaptured in commit 20825722f (see the discovery)."
  - path: "mastermind-terminal:terminal/lib/exposureMap.ts"
    what: "PR-1: reader validates the DEX extension on readSource. Wiring branch: the reader returns projection(lens), the validated QualifiedProjection behind a qualified or dated data read (null for legacy / unqualified / reference-only books), so the surface never derives a second projection."
  - path: "mastermind-terminal:terminal/lib/exposureWorkspace.ts"
    what: "Wiring branch: moves admission factored into admittedExposureMoves; exposureMoveSigmaPct returns the 1σ percent (expected_move.pct / band_mult) under the same admission as exposureMoveDistance."
  - path: "mastermind-terminal:terminal/components/exposure-map/useReplayColumns.ts"
    what: "Wiring branch: one read plane (gex_dates index then the newest stored books before the live session, reduced per column with the live book last) shared by the replay scrubber and the session review; reviewFramesFromColumns drops gap columns instead of inventing zero-touch rows."
  - path: "mastermind-terminal:terminal/components/exposure-map/exposureScenarioBasis.ts"
    what: "Wiring branch: scenarioBasisFromRead builds the ScenarioBasis from the reader's own gamma / vanna / charm net totals plus the moves owner's 1σ; null when the read is not data or spot is not positive."
  - path: "mastermind-terminal:terminal/components/exposure-map/usePriorProjection.ts"
    what: "Wiring branch: reads the prior stored session (selectReplaySessions over the gex_dates index, then gex_at) and validates its exposure_projection receipt with qualifiedExposureProjection for surface provenance; status loading / ready / none / unavailable."
  - path: "mastermind-terminal:terminal/components/exposure-map/ExposureReplay.tsx"
    what: "Lane PR-3 component (with ExposureReplay.module.css, exposureReplayStrings.ts, lib/exposureReplayFrames.ts and tests); wiring commit switched it to useReplayColumns and keyed the active frame to its column set."
  - path: "mastermind-terminal:terminal/components/exposure-map/ExposureSessionReview.tsx"
    what: "Lane PR-4 component (with .module.css, exposureSessionReviewStrings.ts, lib/exposureSessionReview.ts and tests): first / last touch, excursion and close-versus-level per session around each frame's stored dominant level; 10-minute bars."
  - path: "mastermind-terminal:terminal/components/exposure-map/ExposureScenario.tsx"
    what: "Lane PR-6 component (with .module.css, exposureScenarioStrings.ts, lib/exposureScenario.ts and tests): local linear value over the admitted summary; data-scenario-status ready / not-admitted / summary-unavailable / out-of-range / invalid; repricing held and labelled."
  - path: "mastermind-terminal:terminal/components/exposure-map/ExposureSurface.tsx"
    what: "Lane PR-7 component (with .module.css, exposureSurfaceStrings.ts, lib/exposureSurface.ts and tests): SVG strike × expiry surface over projection cells; windows 2/4/8 %, expiry caps 5/9/15, rotate / elevation never change a cell; prior cells matched on equal population_id feed changeMn."
  - path: "mastermind-terminal:terminal/lib/exposureScan.ts"
    what: "Lane PR-5 (consumed at 29ffeb06b, six owned files against BASE 52aa270aa; #1112): scan records over the node reducer — SCAN_VERSION exposure-scan/v1, SCAN_ROLLOUT SPY QQQ SPXW IWM NDXP, books fetched only for rollout roots, identity_unadmitted rows without a fetch, typed null-score reasons, frozen original revision 1 and refreshScan deltas (node moved, contested, score)."
  - path: "mastermind-terminal:terminal/components/exposure-map/ExposureScanTable.tsx"
    what: "Lane PR-5 component (with .module.css, exposureScanStrings.ts and two tests): ranked table with data-scan-status loading / ready / empty and data-scan-revision; Open in Exposure wired, Watch hidden when no owner is passed."
  - path: "mastermind-terminal:terminal/components/exposure-map/ExposureBoard.tsx"
    what: "#1112 (parent-owned mount): the Discover board keeps the glance scanner and mounts ExposureScanTable beneath it over SCAN_ROLLOUT ∪ GEX_AUTOCOMPLETE_ROOTS (41 presets); e2e case asserts ready at revision 1 and the counts line."
  - path: "mastermind-terminal:terminal/components/gexdesk/GexDeskView.tsx"
    what: "Wiring branch: the desk's stored-book opener (loadSession) is passed to the map as onLoadSession so replay and review can open an archived session."
  - path: "mastermind-terminal:terminal/e2e/options-exposure-map.spec.ts"
    what: "PR-2 restyle cases plus three wiring cases that open the replay/review, scenario and surface tabs and assert their status attributes with no page errors at 1440 / 820 / 390."
  - path: "mastermind-terminal:docs/OPTIONS_R2_DESIGN_PIN_2026-10-20.md"
    what: "Repository copy of the design pin (also OPTIONS_R2_F1_CONTRACT_FREEZE_2026-10-21.md with the oracle-outranks-text errata, and OPTIONS_R2_ACCEPTANCE_COVERAGE_2026-10-22.md, the P01–P76 disposition ledger)."
  - path: "agentos/decisions/DEC-OPTIONS-R2-ORACLE-OUTRANKS-FREEZE-TEXT.md"
    what: "This PR: the ruling that the attached oracle outranks the freeze prose (distance_fit trapezoid, number | null)."
  - path: "agentos/discoveries/DSC-TERMINAL-GLOBALS-CSS-EDIT-RELOCKS-THREE-EVIDENCE-PACKETS.md"
    what: "This PR: landmine — any app/globals.css edit relocks three evidence packets."
  - path: "agentos/discoveries/DSC-FABRIC-LANE-BASE-DRIFT-FROM-HOST-FETCH.md"
    what: "This PR: landmine — a host-side fetch of origin/master under a running lane makes the lane diff show master's newer files as reverts."
verified:
  - claim: The attached oracle reproduces in full under an isolated interpreter.
    command: python3 -I quant_oracles.py --output oracle_run/out.json --fixtures-output oracle_run/fixtures.json
    result: all_passed true, checks 499, passed 499, failed 0 (Python 3.14.7); sha256 of the script starts e23eb6a3.
  - claim: The PR-1 reducer and DEX validators match the oracle goldens and refuse the mismatched receipts.
    command: cd terminal && npx vitest run lib/__tests__/exposureNodeReducer.test.ts lib/__tests__/exposureMapProjection.test.ts
    result: green on branch claude/r2-pr1-dex-reducer-1021 at 52aa270aa after the Opus read-only F1 audit's repairs R1–R12 (verdict REPAIR_REQUIRED, then repaired).
  - claim: The wiring head's affected unit suites, types, lint and plain-language guard are clean.
    command: cd terminal && npx vitest run lib/__tests__/exposure lib/__tests__/useReplayColumns lib/__tests__/usePriorProjection && npx tsc --noEmit && npx eslint <changed ts/tsx> && node scripts/check_plain_language.mjs --mode enforce-added --diff-file <git diff --unified=0 origin/master HEAD -- ':/terminal'>
    result: "on 205508dcb the affected suites passed (8 files / 64 tests in the surface step after two hook-test repairs), tsc rc=0, eslint rc=0, guard rc=0; on the final #1116 head 9ef0160bb (master e54fc7f02 merged) 30 files / 421 tests, tsc rc=0, guard rc=0, eslint only the pre-existing GexDeskView.tsx 540 / 577 findings that master carries."
  - claim: The responsive Playwright spec passes on the wiring head at all three viewports, including the three new tab cases.
    command: cd terminal && TERMINAL_E2E_PORT=3141 npx playwright test e2e/options-exposure-map.spec.ts
    result: 22 passed (31.2s) on 205508dcb and 22 passed / 2 skipped (46.1s) on the final head 9ef0160bb, in the W1 worktree (real node_modules; Turbopack refuses a symlinked node_modules).
  - claim: Each lane branch touches only its owned files against master.
    command: git diff --name-only origin/master...origin/claude/r2-exposure-surface-1021 (and the replay, review, scenario branches)
    result: six owned files each (component, module.css, strings, lib module, two tests); the review lane's two "Restore beta ops/tests files" commits net to nothing against master.
  - claim: The three evidence packets relocked by the globals.css edit were recaptured and match.
    command: cd terminal && npx vitest run lib/__tests__/conductorFitBadgeZhEvidence.test.ts lib/__tests__/eodHeatmapFlowdeskLoadFailureEvidence.test.ts lib/__tests__/gexLevelsHeatmapLoadFailureEvidence.test.ts
    result: "green at commit 20825722f on #1098."
  - claim: The PR-5 lane's owned files and the Discover mount pass the gate set and the responsive spec on the merged #1109 master.
    command: cd terminal && npx vitest run lib/__tests__/exposure lib/__tests__/useReplayColumns lib/__tests__/usePriorProjection && npx tsc --noEmit && npx eslint <changed ts/tsx> && node scripts/check_plain_language.mjs --mode enforce-added --diff-file <diff> && TERMINAL_E2E_PORT=3141 npx playwright test e2e/options-exposure-map.spec.ts
    result: on 85bbd0bf0 (lane 29ffeb06b + mount 49c3f486f + master 38723cef6) 20 files / 331 tests, tsc rc=0, eslint rc=0, guard rc=0, 16 passed / 2 skipped; the diff against master is exactly the nine scan files.
  - claim: The #1109 master is live on production through the git-gated build.
    command: ssh root@146.190.142.17 '/opt/terminal/terminal-build.sh --target-sha 38723cef63e87e478b1652d42322a69bdec462fd' then git -C /opt/terminal/.gitsrc rev-parse HEAD, cat /opt/terminal/terminal/.deployment-id, curl -s https://app.mastermind-x.com/options | grep -o 'data-dpl-id="[^"]*"'
    result: "\"[build] DONE — target=production live = origin/master @ 38723cef63e8 (app + runtime code, git-gated, healthy)\"; .gitsrc HEAD, the marker and the live data-dpl-id all equal 38723cef63e87e478b1652d42322a69bdec462fd; anonymous /options returns 200 (04:15Z)."
  - claim: The #1098 master is live on production through the git-gated build.
    command: ssh root@146.190.142.17 "nohup /opt/terminal/terminal-build.sh --target-sha e54fc7f02481d7f66ae962bf8ddf03453382a5cf" then the .gitsrc / .deployment-id / data-dpl-id triple
    result: "\"[build] DONE — target=production live = origin/master @ e54fc7f02481\"; all three equal e54fc7f02481d7f66ae962bf8ddf03453382a5cf; anonymous /options 200 (05:12Z)."
  - claim: The #1116 evidence-lock red was repaired by a real recapture, not a hash edit.
    command: cd terminal && TERMINAL_CROP_PORT=3571 node e2e/tools/capture_eod_heatmap_flowdesk_load_failure.cjs; TERMINAL_CROP_PORT=3572 node e2e/tools/capture_gex_levels_heatmap_load_failure.cjs; npx vitest run lib/__tests__/eodHeatmapFlowdeskLoadFailureEvidence.test.ts lib/__tests__/gexLevelsHeatmapLoadFailureEvidence.test.ts lib/__tests__/conductorFitBadgeZhEvidence.test.ts
    result: "126 + 114 crops rewritten at 9ef0160bb; 12 + 12 crops changed by one relative-age digit (21 px / 46 px bboxes); only the header and the GexDeskView.tsx row (0f7bd0a8 → 4d7b3ac3) changed among non-crop lines; 18/18 green; pushed as bb68cd7d8 with the diff explained on #1116."
  - claim: The final R2 master is live on production through the git-gated build.
    command: ssh root@146.190.142.17 "nohup /opt/terminal/terminal-build.sh --target-sha 4615f80dc8a6855041103c404e4457a6597445f0" then the .gitsrc / .deployment-id / data-dpl-id triple
    result: "LIVE_MATCH 4615f80dc8a6855041103c404e4457a6597445f0 at 2026-10-22T06:52Z; anonymous /options 200."
  - claim: The new tabs render their honest states on the fixture book in a browser.
    command: preview of the W1 worktree with the Playwright fixture env (FLOW_FIXTURE=1, TERMINAL_E2E_FIXTURE=1) at /options?tab=prism&symbol=SPY&view=chart
    result: the fixture SPY book is legacy (session 2026-07-10), so Scenario shows not-admitted and Surface shows "No qualified projection for this session"; desktop and mobile screenshots of all four tabs are in the session report.
unverified:
  - claim: The replay, review, scenario and surface tabs render on a qualified live book.
    what_would_verify: "the authenticated journey on https://app.mastermind-x.com after #1116 deploys, on a session whose SPY/QQQ book carries exposure_projection (P76 row of the coverage ledger)."
  - claim: P74 performance on a 13k-contract book.
    what_would_verify: a profiled run of buildExposureSurface and the map field at the largest stored QQQ book; not run in this program.
  - claim: The scan table ranks a qualified live book end to end.
    what_would_verify: "the Discover board on production after #1112 deploys, with a rollout root whose stored book carries exposure_projection; the dev fixture SPY book yields \"41 presets · 0 scored · 41 unscored\" because it is legacy."
unresolved:
  - "P76 (authenticated production journey) is still a human-only step: all four R2 PRs are merged (#1112 2026-10-22T05:35Z, #1116 2026-10-22T06:31Z) and master 4615f80dc is live, but anonymous production shows the paywall, so no acceptance row has closed."
  - Held rows P17, P25, P29–P31, P39, P48, P61–P67, P75 need owners outside this program (velocity history, alerts contract, annual anchor, calibration, path scenarios, producer schedule record, recap card, sharing/export, Discord adapter, prospective validation).
  - The second package in Downloads (R1 / GammaPulse MASTERPLAN and FABLE_HANDOFF) is a different commission and was not touched.
next_actions:
  - Run the authenticated Exposure journey on https://app.mastermind-x.com (master 4615f80dc): Replay / Review / Scenario / Surface tabs on a SPY or QQQ session whose book carries exposure_projection, the Discover scan table, and the metric_units three-key check; then move the P76 row from PENDING to its measured result in docs/OPTIONS_R2_ACCEPTANCE_COVERAGE_2026-10-22.md.
  - Let Terminal #1122 (docs-only: the P76 row records master 4615f80dc live) merge through the controller; it needs no deploy.
  - Find owners for the held rows (P17, P25, P29–P31, P39, P48, P61–P67, P75) and schedule the P74 13k-contract profile; none of them is Terminal wiring work.
  - Report holds as holds; nothing in the ledger closes a row until P76 is recorded against a deployed master.
do_not_redo:
  - Do not rebuild distance_fit or scanner_score from the freeze prose; the oracle governs and the reducer already ports it (DEC:OPTIONS-R2-ORACLE-OUTRANKS-FREEZE-TEXT).
  - "Do not re-run the Opus F1 read-only audit for unchanged reducer code; its REPAIR_REQUIRED verdict was consumed and repairs R1–R12 are on #1109."
  - Do not derive a second projection for the surface or the scenario; the reader's projection(lens) accessor and the moves owner's 1σ are the only inputs.
  - Do not re-run lane gates for the four consumed lanes unless their files change; they were verified at consumption and again on the wiring head.
  - Do not redesign from the Astra mockup page; the pinned page and docs/OPTIONS_R2_DESIGN_PIN_2026-10-20.md are the contract.
  - Do not recapture the three evidence packets unless app/globals.css changes again.
  - Do not treat the dev fixture SPY book as qualified; its legacy session is why the scenario and surface show their refusal states locally.
  - "Do not rebase or reopen #1116; it was opened after #1098 merged with master merged in. The ExposureMap.tsx / .module.css conflicts were resolved with the branch side because master's copies were byte-identical to 20825722f, the PR-2 content the branch carries (git diff 20825722f origin/master -- <files> was empty)."
  - "Do not re-run or re-consume the PR-5 lane; its six owned files were verified against BASE 52aa270aa at 29ffeb06b and mounted in #1112."
  - Do not deploy 38723cef6, e54fc7f02 or 4615f80dc again; each was built and verified live. A later deploy targets a newer master sha only.
  - Do not delete the R2 branches again; claude/r2-scan-table-1021, claude/r2-wire-replay-review-1021 and the four consumed lane branches were removed after their PRs merged.
  - Do not create a Terminal-local mirror of these records; the Macro agentos/ store is canonical.
danger_areas:
  - Any edit to terminal/app/globals.css relocks three evidence packets (conductor-fit-badge-zh, eod-heatmap-flowdesk-load-failure, gex-levels-heatmap-load-failure) and any edit to terminal/components/gexdesk/GexDeskView.tsx relocks the last two; recapture serially, and before pushing run the census (for each file in the branch diff, grep the docs/pr-crops/*/EVIDENCE.yml files) and the gates it names, not only the suites near the change.
  - Fetching origin/master on the fabric host while a lane runs drifts its base; packets must pin BASE=<sha> and forbid fetch.
  - The one-expiry lens's exp is optional (string | undefined); guard lens.kind === "one" && lens.exp before using it as a focus cell.
  - Next 16 allows one dev server per project directory and Turbopack refuses a symlinked node_modules; stop the preview before Playwright and run e2e only in a worktree with real node_modules.
  - React act() flushes immediately-resolving mocked promises, so a loading state is only observable behind a deferred promise.
  - gh pr view headRefOid lags the real tip after a controller refresh; git ls-remote is authoritative, and update-branch returns 422 when the controller already refreshed.
  - The deploy is git-gated to merged master only; a working-tree rsync is not a deployment.
  - A branch that carries another open PR's commits conflicts with that PR's squash on every shared file; when master's copy equals the carried content, the branch side is the whole resolution, otherwise master's extra delta must be applied on top.
  - The Theta publication-only hold, the last-good full book rule (never replaced by a canary) and the no-parallel-store rule remain binding for anything that touches the options data plane.
---

# R2 exposure intelligence: all four PRs merged and live; P76 remains the human step

## Where the work is

Seven slices, seven owners. PR-1 (#1109, 03:45Z) and PR-2 (#1098, 04:45Z) merged and
were each deployed and verified live. PR-3, PR-4, PR-6 and PR-7 were built as fabric
lanes, gate-checked at consumption and merged into the wiring branch, which merged as
#1116 (2026-10-22T06:31Z); PR-5 was consumed from its lane and mounted on the Discover board as
#1112 (2026-10-22T05:35Z). Master 4615f80dc carries all of it and is live (LIVE_MATCH 2026-10-22T06:52Z).
The three governing documents (design pin, freeze with errata, coverage ledger) are
under the Terminal `docs/` directory. The only CI red in the program was #1116's
evidence lock on GexDeskView.tsx, repaired by a real recapture of both packets.

## How the wiring stays honest

Every tab reads an owner that already existed: the replay and review tabs share one read
plane over the stored-session index; the scenario reads the reader's own net totals and
the moves owner's one-sigma; the surface draws the reader's own validated projection and
takes provenance only from a prior session with the same population id. The local fixture
book is legacy, so the scenario and surface show their refusal states there; that is the
expected rendering, not a defect.

## What a successor must not mistake for done

Nothing closes an acceptance row until the authenticated live journey runs against a
deployed master. The held rows need owners this program does not reach. The second
package in Downloads belongs to a different commission.
