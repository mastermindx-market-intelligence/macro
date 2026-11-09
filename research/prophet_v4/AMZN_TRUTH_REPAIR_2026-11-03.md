# AMZN Prophet truth repair

Programme: WS:PROPHET-US-V4-RECOVERY / Macro #6805.
Current Chairman assignment: implement the diagnosed AMZN defects end to end.
This session owns implementation, integration and real-path verification; no old author is treated as a live approver.
Assessment: https://github.com/mastermindx-market-intelligence/macro/issues/6805#issuecomment-6619578523.
Recorded: 2026-11-04 UTC (Chairman request on November 3 local time).

## Source and custody

Protected procedure: Mastermind 910803421beca53ca25145392725ab2d84c7a8e9, skillpack 1.0.1.
Macro base: b4df44260aefb42afbabd5f85e3b0630c8fec506.
Terminal base: 801e1c6818f454863bdf8020fa79a9198cb11721.
New attended repair root: amzn-prophet-truth-20261103; immediate coordinator has that same operation identity. These are coordination metadata, not Runtime authentication.
Canonical workspace acquisitions:
- Macro: amzn-prophet-truth-macro-20261103, sol/web-amzn-prophet-truth-macro-20261103.
- Terminal: amzn-prophet-truth-terminal-20261103, sol/web-amzn-prophet-truth-terminal-20261103.
Both were acquired through the installed mmx-workspace owner on the external volume. No existing writer or uncertain effect is transferred.

## Outcome and completion ruler

A user inspecting a Prophet candidate can distinguish actual source time from candle position, original selection rank from later rankings, modeled evaluation from an order, and evaluation exit reason/window from a live current-entry decision. Invalid signal bytes cannot cross publication as accepted output. Existing B4 deterministic protection remains the sole entry authority, with unknown facts never promoted to PASS.
Completion requires changed source, focused regressions, required CI, protected release, and served-byte/browser proof. Tests, a PR or merge alone do not establish production acceptance.

## Ordered implementation

### P1 - admission and evaluation truth

Owner: Macro ledger/scorer/opportunity projection, current repair session.
Paths: scripts/grade_us_board.py, engine/track_scoring.py, scripts/build_opportunity_timeline.py and their existing tests.
- Preserve metadata at (admission date, ticker), not the ticker's latest board appearance. Declare and normalize ordinal basis once; do not apply a cross-market blanket increment.
- Preserve episode identities and all return calculations. Add actual evaluated exit date, reason and model-evaluation semantics without turning hypothetical fills into executions.
- Carry additive provenance through the existing opportunity timeline. Unknown historical values stay unknown; preserve original source receipts and corrections.
- Regress repeated appearances, multiple episodes, missing data, fill-pending and matured rows, source ordering, US zero-based positions and non-US existing rank semantics.

### P2 - reject invalid publication

Owner: existing Macro publication workflow and validator, current repair session.
Paths: .github/workflows/engine-render.yml, existing publication helper if applicable, narrow tests and CI dependency declarations.
- Validate the exact signal payload at the final publication boundary, including mutations caused by rebase/restoration. A logged error followed by exit zero is not success.
- Keep nightly data ownership unchanged. Do not manually regenerate historical canonical data, silently delete malformed history, weaken validation, or grant the render lane new data write authority.
- Preserve unrelated valid output when possible, but never allow rejected signal bytes to be newly published or invalid data to acquire a fresh acceptance clock.
- Exercise a validator nonzero exit and post-validation modification; verify the last-good / explicit unavailable behavior and final staged-byte fence.

### P3 - Terminal receipt and entry consumer

Owner: existing chart/opportunity consumers, current repair session.
Paths: terminal/components/ChartPanel.tsx, terminal/lib/signalVerdict.ts, terminal/lib/replayContract.ts and bounded helper/tests/browser fixture.
- Keep source date separate from resampled candle coordinate. D and 3D views must report the same candidate date.
- Show modeled entry and outcome semantics, source-qualified rank, return endpoint and exit reason. A loss is not necessarily a stop hit; oscillator 'target' is not a profitable price target.
- Replay must not expose a future fill/outcome. Legacy incomplete receipts degrade explicitly.
- Verify that current entry presentation remains independent of historical candidate performance and refuses unknown current entry evidence. No new strategy policy or forged candidate-plan join.
- Preserve #1252's active research/Oracle improvements and #1238's marker styling; their inspected changes are adjacent, not authority to alter those held carriers. Integrate narrow non-overlapping hunks on the acquired repair branch.

### P4 - release and verification

Publish through normal repository paths; consume exact-head CI and fix actual regressions. No self-approval, self-merge, admin bypass or modification of held sibling PRs. Use the existing eligible release controller where admitted. Verify fresh production source/bytes, authentic candidate receipt behavior on D/3D and responsive browser states. Missing auth or release evidence remains explicit, not a successful completion claim.

## Non-goals

No new anti-chase engine, stock-specific earnings veto, threshold changes, trading/size authority, data collection, frozen-study outcome reads, retrospective B4 decision or historic reason-array repair. The existing postmortem protocol and frozen Entry Timing W2 remain unchanged. Any later policy experiment is separately predeclared and must count winners forfeited and no-fill opportunities.

## Execution method

Use economical admitted Fabric labor for bounded independent work when available; retain principal integration and validation. WHY NOT FABLE: frozen repair contracts and focused regressions require no scarce frontier worker. Direct principal work is justified for publication-boundary judgment and cross-repo integration. Never dispatch a duplicate worker or replay an unknown/denied effect.

## Current verification

Two workspace acquisition receipts applied at the bases above; Macro workspace was clean. Bounded open-PR census identified Terminal #1252 and #1238 adjacency. No product edits, policy mutations, release or production proof yet. The first full worktree census was terminated after no output; it was read-only and is not evidence that every sibling workspace is inactive.

## Implementation milestone - P1 source qualified

Fabric run `amzn-truth-macro-ledger-20261103-01` returned terminal on its original carrier with root verified. The complete response digest is `57d6a56b184fb70ad613267a71e46e1ecf5643e693e0527c09c8584867ed6a9f`. It ran on ubuntu0, could not access the assigned M2 workspace and explicitly returned no edits, clone, worktree, fetch or running process. The parent verified the original M2 workspace clean at c287500ab7025d43366aa5da2b553cc39d6d8afa before continuing directly. No denied action was replayed or worker replaced. Direct rationale: UNIQUE_APPROVED_ACCESS / LOWER_TOTAL_OVERHEAD.

Implemented P1 on the original workspace: admission-keyed rank/tier/sector, explicit one-based US ordinal and null original knowledge clock, deterministic duplicate-conflict withholding, actual model exit/mark dates and additive opportunity provenance. Existing scoring and episode identities are preserved; no data or site artifact was regenerated. A source-as-of date is not an original delivery receipt: rank_known_at remains null, and the Terminal consumer must withhold that rank in historical replay without a genuine clock.

Verification: `python3 -m pytest tests/test_track_ledger_emitters.py tests/test_track_scoring.py tests/test_opportunity_timeline.py -q` passed 112 tests. The added admission regressions failed before the repair. The first integration exposed an existing continuity dependence on input ordering; sorting a copy of the boards repaired it without mutating callers. Identical duplicate input counts remain disclosed, while episode values and summaries are invariant. `git diff --check` passes. This is source qualification, not release or real-path acceptance.

Independent P2 source workspace: operation amzn-prophet-publication-20261103, branch sol/web-amzn-prophet-publication-20261103, same Macro base. Exact immutable-tree inspection found six current contract-rejected historical explanations (AMZN, EQIX, GOOGL, HST, KMI, MU). Strict publication checks are being qualified, but must not be blindly armed against that known baseline without a safe per-source last-good/withdrawal or correction boundary. Historical marker corrections remain separate from this P1 patch.

Terminal source currently passes 180 focused unit cases with source-date/coordinate separation, qualified ordinal handling, model exit semantics and conservative replay. Browser/CI/release/served-byte proof remain owed. Parent mission remains incomplete.
