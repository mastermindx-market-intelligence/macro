---
workstream: WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY
session: claude/r2-wire-scenario-surface-1021
model: fable
ended_because: ci_handoff
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
prs: [1098, 1109]
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
    what: "PR-2 (#1098): shell redesigned from the Paper pin (clocks strip, lens rail, stat strip, field with sticky axes, keyboard ±/0, inspector). Wiring branch: five book-anatomy detail tabs (expiries, values, changes, replay, review, scenario, surface) with onLoadSession from the desk, the ExposureReviewTab / ExposureScenarioTab / ExposureSurfaceTab hosts, pin and Open-in-Exposure links from the surface."
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
    result: on 205508dcb the affected suites passed (8 files / 64 tests in the surface step after two hook-test repairs), tsc rc=0, eslint rc=0, guard rc=0 (legacy findings are non-blocking).
  - claim: The responsive Playwright spec passes on the wiring head at all three viewports, including the three new tab cases.
    command: cd terminal && TERMINAL_E2E_PORT=3141 npx playwright test e2e/options-exposure-map.spec.ts
    result: 22 passed (31.2s) on 205508dcb in the W1 worktree (real node_modules; Turbopack refuses a symlinked node_modules).
  - claim: Each lane branch touches only its owned files against master.
    command: git diff --name-only origin/master...origin/claude/r2-exposure-surface-1021 (and the replay, review, scenario branches)
    result: six owned files each (component, module.css, strings, lib module, two tests); the review lane's two "Restore beta ops/tests files" commits net to nothing against master.
  - claim: The three evidence packets relocked by the globals.css edit were recaptured and match.
    command: cd terminal && npx vitest run lib/__tests__/conductorFitBadgeZhEvidence.test.ts lib/__tests__/eodHeatmapFlowdeskLoadFailureEvidence.test.ts lib/__tests__/gexLevelsHeatmapLoadFailureEvidence.test.ts
    result: green at commit 20825722f on #1098.
  - claim: The new tabs render their honest states on the fixture book in a browser.
    command: preview of the W1 worktree with the Playwright fixture env (FLOW_FIXTURE=1, TERMINAL_E2E_FIXTURE=1) at /options?tab=prism&symbol=SPY&view=chart
    result: the fixture SPY book is legacy (session 2026-07-10), so Scenario shows not-admitted and Surface shows "No qualified projection for this session"; desktop and mobile screenshots of all four tabs are in the session report.
unverified:
  - claim: The replay, review, scenario and surface tabs render on a qualified live book.
    what_would_verify: the authenticated journey on https://app.mastermind-x.com after the wiring PR deploys, on a session whose SPY/QQQ book carries exposure_projection (P76 row of the coverage ledger).
  - claim: P74 performance on a 13k-contract book.
    what_would_verify: a profiled run of buildExposureSurface and the map field at the largest stored QQQ book; not run in this program.
  - claim: The PR-5 scan table matches the frozen scanner_score goldens end to end.
    what_would_verify: consuming RESULT_PR5.md on ubuntu3, running its tests against BASE 52aa270aa, and the Discover board mount.
unresolved:
  - PR-5 scan lane r2-pr5-scan-1021-v1 was still POLL_PENDING (poll 80 at 02:59Z); consume it, verify owned files against BASE 52aa270aa, mount ExposureScanTable on the Discover board after #1109 lands.
  - The combined wiring PR (branch claude/r2-wire-scenario-surface-1021, which contains claude/r2-wire-replay-review-1021) opens only after #1098 merges; it then needs merge origin/master, the gate set, push, label, auto-merge, deploy and live verification.
  - Held rows P17, P25, P29–P31, P39, P48, P61–P67, P75 need owners outside this program (velocity history, alerts contract, annual anchor, calibration, path scenarios, producer schedule record, recap card, sharing/export, Discord adapter, prospective validation).
  - The second package in Downloads (R1 / GammaPulse MASTERPLAN and FABLE_HANDOFF) is a different commission and was not touched.
next_actions:
  - When #1098 merges, in a worktree on claude/r2-wire-scenario-surface-1021 run git merge origin/master, the gate set above, push, open the PR against master, add merge-on-green and arm gh pr merge --auto --squash --delete-branch.
  - After each R2 merge deploy that master sha through /opt/terminal/terminal-build.sh --target-sha <sha> on the VPS and verify .gitsrc, .deployment-id and data-dpl-id on https://app.mastermind-x.com, then the authenticated Exposure journey and the metric_units three-key check; record P76 per row in docs/OPTIONS_R2_ACCEPTANCE_COVERAGE_2026-10-22.md.
  - After #1109 merges delete claude/r2-dex-extension-1021, claude/r2-node-reducer-1021 and claude/r2-pr1-audit-repairs-1021; after the wiring PR merges delete claude/r2-wire-replay-review-1021 and the four consumed lane branches.
  - Consume the PR-5 lane; the scan table mounts on the Discover board as a parent-owned change in its own PR.
  - Report holds as holds; nothing in the ledger closes a row until P76 is recorded against a deployed master.
do_not_redo:
  - Do not rebuild distance_fit or scanner_score from the freeze prose; the oracle governs and the reducer already ports it (DEC:OPTIONS-R2-ORACLE-OUTRANKS-FREEZE-TEXT).
  - Do not re-run the Opus F1 read-only audit for unchanged reducer code; its REPAIR_REQUIRED verdict was consumed and repairs R1–R12 are on #1109.
  - Do not derive a second projection for the surface or the scenario; the reader's projection(lens) accessor and the moves owner's 1σ are the only inputs.
  - Do not re-run lane gates for the four consumed lanes unless their files change; they were verified at consumption and again on the wiring head.
  - Do not redesign from the Astra mockup page; the pinned page and docs/OPTIONS_R2_DESIGN_PIN_2026-10-20.md are the contract.
  - Do not recapture the three evidence packets unless app/globals.css changes again.
  - Do not treat the dev fixture SPY book as qualified; its legacy session is why the scenario and surface show their refusal states locally.
  - Do not open the wiring PR before #1098 merges; its diff would carry PR-2's commits and burn a CI cycle.
  - Do not create a Terminal-local mirror of these records; the Macro agentos/ store is canonical.
danger_areas:
  - Any edit to terminal/app/globals.css relocks three evidence packets (conductor-fit-badge-zh, eod-heatmap-flowdesk-load-failure, gex-levels-heatmap-load-failure); recapture serially.
  - Fetching origin/master on the fabric host while a lane runs drifts its base; packets must pin BASE=<sha> and forbid fetch.
  - The one-expiry lens's exp is optional (string | undefined); guard lens.kind === "one" && lens.exp before using it as a focus cell.
  - Next 16 allows one dev server per project directory and Turbopack refuses a symlinked node_modules; stop the preview before Playwright and run e2e only in a worktree with real node_modules.
  - React act() flushes immediately-resolving mocked promises, so a loading state is only observable behind a deferred promise.
  - gh pr view headRefOid lags the real tip after a controller refresh; git ls-remote is authoritative, and update-branch returns 422 when the controller already refreshed.
  - The deploy is git-gated to merged master only; a working-tree rsync is not a deployment.
  - The Theta publication-only hold, the last-good full book rule (never replaced by a canary) and the no-parallel-store rule remain binding for anything that touches the options data plane.
---

# R2 exposure intelligence: lanes consumed, map wired, delivery in flight

## Where the work is

Seven slices, seven owners. PR-1 (#1109) and PR-2 (#1098) are open with the
controller armed. PR-3, PR-4, PR-6 and PR-7 were built as fabric lanes, gate-checked at
consumption and merged into `claude/r2-wire-scenario-surface-1021` together with the
parent-owned wiring commits; that branch opens as one PR once #1098 merges. PR-5 is still
on its lane. The three governing documents (design pin, freeze with errata, coverage
ledger) are committed under the Terminal `docs/` directory on the wiring branch.

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
