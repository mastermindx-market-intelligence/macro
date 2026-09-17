---
key: OPTIONS-WORKBENCH-R0-REPLAY-GEOMETRY-FAILURES
claim: >
  On Terminal base 75c22083249e7a1529be3d6baf819b9ad5ea509f,
  actual-renderer and mounted/browser tests reproduce nonuniform-price band
  misalignment, missing same-root index refresh and layout-driven replay-time
  reset. Terminal #608 now corrects geometry and cache/cursor helpers, but its
  provider/view/pane integration remains unapplied after a new tool-call refusal.
falsifier: >
  At the original pinned Terminal base, npx vitest run
  lib/__tests__/heatSeriesGeometry.test.ts from Terminal #608 passes, or the
  screenshots/assertions are shown not to exercise the actual SurfaceView,
  SurfacePane and replay consumers under the documented synthetic inputs.
so_what: >
  Resume Terminal #608 at its current partial-correction head, not another
  competitor teardown. Preserve corrected geometry and the remaining red replay
  regressions. A generic tool permission setting does not supersede a particular
  tool-call refusal; never reroute the held integration through another worker
  or tool. Synthetic browser success is not live-market acceptance.
kind: runtime
verified_at: 2026-09-17
verified_by: >
  mastermind-terminal #608 at bd578978746fac3ce8974c9a769484f5486d855f;
  terminal:docs/evidence/options-workbench-r0-20260917/geometry-correction/verification.json;
  original reproduction 2699f9e6b20fec922c779b2427156206c973de79;
  actual renderer/browser red-green evidence and full Vitest result in #608.
scope:
  - terminal
  - options-intelligence
  - terminal:terminal/components/surface
  - terminal:terminal/lib/heatSeries.ts
confidence: verified
---

## Mission, authority and preserved owners

Chairman approved the Options Workbench recovery and subsequent continuation on
17 September 2026, explicitly reaffirming write access and permitting Desktop
Commander. Parent tracker is Terminal #603. This discovery creates no program,
worker, runtime, source writer, release authority or data store. Existing
#591/#592, #598/#599 and Macro #6604 retain their scope and custody.

Terminal carrier: `claude/options-workbench-r0-replay-20260917-sol-001`.
Current head: `bd578978746fac3ce8974c9a769484f5486d855f`.
Base: `75c22083249e7a1529be3d6baf819b9ad5ea509f`.
Current protected Skillpack: `7a191cc11039199843d4734c7df8d5523280e09c`.
Capability: PARTIAL / BUILT_NOT_PROVEN, not deployed or accepted parity.

## Historical reproduction, retained rather than rewritten

Original head `2699f9e6b20fec922c779b2427156206c973de79` had no production
source edits. Existing renderer/replay baseline: 80 pass. Six-file reproduction
run: 86 pass and 14 fail of 100. Six real Next-route browser cases failed in EN/ZH
at desktop/tablet/mobile with zero retries. Eighteen synthetic captures remain.
The initial edit attempts were refused and reconciled as no effect.

## Applied correction and new proof

The current continuation successfully applied three source changes using Desktop
Commander on the same branch: map every heat band through actual price coordinates;
add an awaited refresh option to the existing HTTP cache while preserving default
SWR and in-flight deduplication; retain a paused timestamp instead of its changing
array index when earlier observations are inserted or one is removed with an
available preceding observation.

Renderer tests: 37 pass. Cache/reducer tests: 56 pass. Real browser pixel tests:
six pass across normal/inverted/logarithmic axes and DPR 1/2. Restoring the original
renderer makes all six fail; the candidate is restored and byte-checked. Actual
/options?tab=surface alignment cases: six pass across EN/ZH and 1440/820/390;
numeric band proportions remain 1:5:9 and horizontal document overflow is absent.
Twelve additional synthetic captures and their hashes are committed.

Full Vitest: 336 files, 335 passing and one failing; 5,525 tests pass, five fail,
four existing todo. The five failures are the retained mounted replay integration
cases. Fresh TypeScript exits zero. There is no all-green or production claim.
The cache refresh is not wired into the displayed index loop. Latest-loaded does
not establish live freshness. If every remaining stamp is later than a withdrawn
historic cursor, the reducer still needs an explicit unavailable-state design.

## Exact remaining tool boundary

Permission inspection returned Allow all actions for both Remote Desktop Commander
and Studio Direct. No setting was changed. Desktop Commander executed source edits
and tests; Studio Direct executable tools were not exposed in this conversation.

The separate attempt to change replayContext.tsx, SurfaceView.tsx and SurfacePane.tsx
was refused by ChatGPT's tool-call safety check before execution. Same-carrier
tracked diff/readback confirms those files remain unchanged. This is not a Mac
filesystem permission failure, missing Chairman approval or a diagnosed feed outage.
It must not be retried through another tool, worker or carrier. There is no unknown
source effect. The earlier blanket 'all source edits blocked' state is superseded
only for the three successful library changes above.

## Independent numerical lane and existing repair review

Macro #7271 at `4bb58c0eb4566a21e3cb3d2b1bdd2a6a2cf962c5` is a path-disjoint
local gamma-regime correction within the same recovery mission. It retains the
existing pricing profile and chooses regime from its current-spot sign, not the
orientation of the nearest crossing. Actual compute_gex synthetic consumer output
is now consistent. New original-source cases: five fail/five controls pass;
candidate expanded engine/state/hub/matrix family: 333 pass after materializing
tracked site fixtures through the existing sparse-worktree tool. Independent
numerical review, current-head CI and production proof remain owed. No trade or
forecast authority, adaptive-grid change or expiry-clock correction is claimed.

A source-semantics COMMENT review was added to existing Terminal #592 at
`87969fb4aff5836410ffd166cc39289b562a41bc` (review 5242156602). No source blocker
was found in its two production-file changes. Local current-master merge-tree was
clean, despite stale normalized mergeable metadata. This is not a formal GitHub
approval, new test execution, hosted integration proof or release authority.
The original source writer and release gates remain unchanged.

## Product correction and next action

The UI already groups its 16 registered views into category and view rows. Preserve
that grouping; the initial report's '16 peer top-level tabs' characterization was
incorrect. Improve coherent pane composition, time identity and analytics instead.

After an actual applicable tool recovery/authorization change, reconcile and finish
the held replay integration on #608 without weakening its regression tests. Keep
#608 draft while they fail. The independent numerical review/release lane on #7271
must continue under existing owners; do not use it as a replay-edit bypass. No
review worker START or durable autonomous execution is established. Do not redo the
competitor study, accepted red reproductions or successful geometry correction.
The full gamma/charm scenario field, expiry clock, adaptive profile, coherent
workbench and real-session product acceptance remain unfinished.
