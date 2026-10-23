---
key: NATIVE-CHART-ENGINE
title: Native Chart Engine — portable main-chart API, owned Canvas2D renderer, preserved workflows
objective: >
  Replace only the rented renderer (lightweight-charts 5.2.0) behind the Terminal's own
  chart-engine contract (terminal/lib/chart-engine/api.ts) with an original Canvas2D
  renderer, while every existing workflow (drawings, live bars, bar replay, pane sync,
  indicators, keyboard access) keeps behaving identically. Done means the "mm" engine
  passes the factory-agnostic conformance corpus, ChartPanel runs on it behind a dark-launch
  selector with a one-flag rollback to "lwc", and production renders the same crops.
status: blocked
program: terminal-charting
repos: [terminal]
owner: ceo-sol
class: build
blast_radius: user_facing
ambiguity: scoped
owns_paths:
  - terminal/lib/chart-engine/**
  - terminal/lib/__tests__/chartEngine*.test.ts
  - terminal/lib/__tests__/lwcAdapter.test.ts
  - terminal/components/ChartPanel.tsx
  - terminal/bench/chart-engine.cadence.bench.ts
  - docs/chart-engine/**
  - docs/chart-engine-completion/**
  - docs/CHART_ENGINE_MASTERPLAN.md
discoveries:
  - DSC:LANE-RECONCILIATION-HOLD-CLOSES-HOST
  - DSC:CANVAS-ENGINE-INPUT-CONTROLLER-UNWIRED-AT-PR969
  - DSC:CHART-ENGINE-PRESENTED-INTERVAL-IS-INPUT-BOUND
  - DSC:CHART-ENGINE-Q03B-ZOOM-P95-GAP-IS-ACK-PACED-PHASE
  - DSC:CHART-ENGINE-Q03B-FIRST-WHEEL-IS-RENDERER-IDLE-WAKEUP
  - DSC:CHART-ENGINE-Q03B-V2-FIRST-WHEEL-ELEVATION-PERSISTS-WITH-HEARTBEAT
  - DSC:CHART-ENGINE-Q03B-CDP-WHEEL-HELD-BEHIND-VISUAL-STATE-CALLBACK
  - DSC:CHART-ENGINE-PERF-C-FRAME-COST-CUT
  - DSC:CHART-ENGINE-Q03B-NEXT-FRAME-ANSWER-IS-NOT-THE-WHEELS-OWN-FRAME
blocked_by:
  - >
    The Q03 zoom half is HELD on the VALID FAIL Q03b v2 receipt (mm zoom p95 21.655 / p99
    42.429 ms vs <= 20 / <= 33.4). The Chairman commissioned a new protocol on 2026-10-18; its
    v3 draft failed its own pre-registered B1 check before any receipt, and the Chairman ruled
    the v4 rule the same day (DEC:CHART-ENGINE-Q03B-PROTOCOL-V4-OWN-FRAME-SWAP-END:
    own EventLatency frame, forward anchor minus the capped busy bias, GPU swap end).
    P5-DEFAULT-FLIP and P6-LWC-RETIREMENT wait on the one official v4 mm receipt at a merged
    master head carrying Terminal PR 1050.
waves:
  - id: P2-CONTRACT
    title: Portable main-chart contract — api.ts widened, LWC adapter implements it, census + reference-semantics dossier
    status: done
    pr: 969
  - id: P3-RENDERER-LIBRARY
    title: Owned canvas renderer as pure library — model, series, scales, ticks, input, axis gestures, crosshair, paint, keyboard, LOD, snapshot, decorations; wave-4 hardening F-01..F-16 (PR 991)
    status: done
    pr: 991
  - id: P3-CHARTPANEL-MIGRATION
    title: Migrate ChartPanel.tsx raw lightweight-charts call sites onto the engine contract (M01 primary series, M02 studies, M03 decorations) with the ?engine=mm mount selector and the F-13 impl guard
    status: done
    pr: 992
    depends_on: [P3-RENDERER-LIBRARY]
  - id: P3B-BOUNDARY-CLOSURE
    title: migration2 — ChartPanel boundary closure, PaneHandle identity ruling, Q04 accessibility proofs, forced-lwc fallback removed so ?engine=mm mounts the owned engine for real
    status: done
    pr: 999
    depends_on: [P3-CHARTPANEL-MIGRATION]
    next_action: >
      Done. PR 999 merged as master 9938c0cb0 (2026-10-17); deployed as ce8 through the
      git-gated build (VERIFY OK: deployment-id == gitsrc HEAD == served dpl); live engine
      proof --mm-expect mm --probe 4/4 PASS at 07:57Z: P01-A01 impl=mm with no fallback
      warning, A02a/b lwc with storage untouched, A03 trackingMode refusal -> lwc.
  - id: P4-PERF
    title: Canvas performance wave — O(1) live extents, float-index zoom anchor, paint budget
    status: done
    pr: 994
    depends_on: [P3-RENDERER-LIBRARY]
  - id: P4-CADENCE-Q03
    title: Presented-frame cadence instrument (PR 995) and Q03b per-input presentation latency + measured vsync (PR 998); official receipts rule the P03 flip gate
    status: done
    pr: 998
    depends_on: [P4-PERF]
  - id: P4-Q03C-PROTOCOL-V2
    title: Q03b protocol v2 — wall-clock CDP wheel dispatch, harness rAF awake start, protocol-tagged receipt and INVALID rules (branch claude/ce-q03c-1013)
    status: done
    pr: 1027
    depends_on: [P4-CADENCE-Q03]
    next_action: >
      Done. The v2 receipt was taken once at 1b7ec6a6b and is a VALID FAIL (mm zoom
      input_to_present p95 21.655 / p99 42.429 ms vs <= 20 / <= 33.4; pan p95 8.905 / p99 9.686
      PASS; the lwc comparator fails the same budgets). PR 1027 shipped the instrument only, no
      receipt, merged as master 3c115e5d1 and deployed as ce9. PR 1028 (harness-only readiness
      retry for the navigation race that aborted lwc run 3) merged as master fb72315fa
      (harness-only; shipped inside ce10, no deploy of its own). Not to be re-run; the zoom
      half moves only through a prospective new-protocol decision.
  - id: P4-Q03B-PROTOCOL-V4
    title: Q03b protocol v4 — the wheel's own EventLatency frame to its GPU swap end, anchored at the Browser forward minus the capped main-thread busy bias, with v4 INVALID rules, plus PERF-C frame-cost cut (arithmetic time ticks, streaming line LOD)
    status: in_progress
    pr: 1050
    depends_on: [P4-Q03C-PROTOCOL-V2]
    next_action: >
      Ruled by the Chairman 2026-10-18 under DEC:CHART-ENGINE-Q03B-PROTOCOL-V4-OWN-FRAME-SWAP-END
      (budgets and workload unchanged; the v3 draft was never measured, see
      DSC:CHART-ENGINE-Q03B-NEXT-FRAME-ANSWER-IS-NOT-THE-WHEELS-OWN-FRAME). The v4 code is on
      Terminal PR 1050 at d0dc7aa09595 (99 cadence tests, 12 mutations red, independent oracle 0
      mismatches; audit fail-closed repairs F1-F3 change no diag row; a counts-only mechanism check in receipt categories had 60 marks / 60 mapped
      / 0 fallbacks / map max 0.023 ms on its VALID-shaped mm attempt). Land PR 1050 (instrument
      plus PERF-C, no receipt), deploy and live-prove it, then take the official v4 receipt once
      at the merged master head (mm and lwc, port 3111, load1 < 24, NEXT_PUBLIC_CHART_BENCH=1
      prod build, headed, dpr 2, 3 runs). An INVALID (q03b-v4) run is repeated unread; a VALID
      FAIL keeps the hold with no re-run or amendment. Report the INVALID attempt count with
      the receipt.
  - id: P4-ACCEPTANCE-DARK-LAUNCH
    title: Conformance corpus green on "mm", engine selector dark launch, production crops, rollback drill, acceptance-gap closure (PR 993) and census follow-ups (PR 997)
    status: done
    pr: 993
    depends_on: [P3B-BOUNDARY-CLOSURE]
    next_action: >
      Done. PR 993 merged as 24fd0ce6f (ce10) and PR 997 as 3e6e9591d (ce11); each merged
      master was deployed through the git-gated build and live-proven (P01-A01..A04, rollback
      P01-A03 engineProbe=refuse -> lwc). The acceptance ledger closed at 102 ACCEPTED / 31
      UNRESOLVED / 3 EXCLUDED of 136 rows in Terminal PR 1036 (docs-only, not deployed by
      policy). Production: 3e6e9591d21b.
  - id: P5-DEFAULT-FLIP
    title: P03 — flip the default engine to "mm" (LWC stays selectable as the rollback for >= 1 release)
    status: todo
    depends_on: [P4-Q03B-PROTOCOL-V4, P4-ACCEPTANCE-DARK-LAUNCH]
    next_action: >
      HELD by DEC:CHART-ENGINE-Q03B-PROTOCOL-V4-OWN-FRAME-SWAP-END until the official v4 mm zoom
      receipt passes (VALID and zoom input_to_present p95 <= 20 / p99 <= 33.4 ms); the pan half is already
      lifted. The flip is carried on claude/ce-p03b-1018 (4fb2c86ae465, superseding
      claude/ce-p03-1013), which still has two blockers to fix before it can ship: the mm
      tickMarkFormatter receives the tick weight instead of LWC's TickMarkType
      (lib/chart-engine/canvas/frame.ts), and ChartPanel attaches SessionShadingPrimitive
      unguarded, which mm rejects. The ChartPanel edit needs the three evidence recaptures.
      The v2 receipt FAILED (VALID (zoom input_marks 60 = dispatch.scheduled 60, input_unpresented 0, dispatch_dev_max_ms 0.988 <= 2, heartbeat_mode through with leadin_presentations 0) and FAIL: mm zoom input_to_present p95 21.655 ms > 20 and p99 42.429 ms > 33.4 (runs p95 25.8 / 21.7 / 24.6, p99 42.8 / 42.4 / 38.9; median run 2 by pan p95); pan input_to_present p95 8.905 / p99 9.686 PASS. lwc comparator: runs 1-2 zoom p95 25.5 / 25.3, p99 42.6 / 35.7 (both fail the same budgets); run 3 aborted by a bench-harness navigation race ('Execution context was destroyed' in waitReady, bench/chart-engine.cadence.bench.ts:169), so that session wrote no lwc receipt file; the complete ledger-only lwc comparator taken at 2026-10-14T07:57:33Z (same head, port 3111, load1 17.98) failed in all three runs (zoom p95 26.2 / 24.8 / 25.6, p99 41.6 / 52.3 / 47.2; median receipt cadence-lwc-1b7ec6a6b5ed80f49db2b9d4353cadb98a3f79a8-m2studio.json, budget_ok false, not committed) - a ledger comparator, not a ruling input or a condition of the mm ruling receipt), so the hold stands; the next legitimate
      step was a prospective new-protocol decision with a new falsifiable diagnosis, not a
      re-measurement (now v4, above).
  - id: P6-LWC-RETIREMENT
    title: P04 — retire the lightweight-charts adapter and dependency
    status: todo
    depends_on: [P5-DEFAULT-FLIP]
    next_action: >
      Held at least one release behind the P03 flip; never before a production release has
      run with mm as the default and the rollback row still proven.
landmines:
  - >
    Editing terminal/components/ChartPanel.tsx reds `npm test` until the three ChartPanel-locked
    evidence packets (b_pl_6 batch-1, optionsLevelAxis, visualIntelligence) are recaptured on a
    Mac; budget the recapture before every PR that touches ChartPanel.
  - >
    ChartPanel.tsx, lib/paneSync.ts and lib/chart-engine/index.ts have one writer (the seat
    session); lanes return PROPOSED_PATCHES for those three files instead of editing them.
  - >
    No `lightweight-charts` import may appear in lib/chart-engine/api.ts or lib/chart-engine/canvas/;
    the integration merge script refuses the lane otherwise.
  - >
    master is strictly protected (three CI contexts, strict: true) and raced by 20+ auto-merge
    armed PRs from other sessions: every landing puts a waiting PR BEHIND, and the controller's
    bot refresh deadlocks that PR's pull_request run as action_required until Terminal PR 989
    lands. Bring seat PRs current one at a time with the user-token update-branch; approve or
    re-run a held run only on your own head.
  - >
    claude/ce-q03c-1013 descends from PR 998's final branch head e206cd046 while master carries
    998's squash; a natural merge or rebase re-conflicts on the bench, its test and bench.md.
    Only the explicit-base plumbing stack merge (parent e206cd046) is correct.
  - >
    D10 and the v2 DEC bind the bench budgets, workload and protocol prospectively: a FAIL is
    recorded and the hold stands, an INVALID run is repeated unread, and nothing is amended
    after a result (no warm-up wheel, larger n, first-input exclusion, lwc-parity substitute,
    or product-level rAF keep-awake).
  - >
    The official receipt needs load1 < 24 on the reference Mac (M2 Studio, 100 Hz panel,
    dpr 2); other sessions routinely drive load1 to 50-150, so build ahead and start the bench
    the moment the window opens, never by killing another session's process.
do_not_redo:
  - >
    The 24 wave-1/2 lanes and the decor lane are merged and deterministically accepted
    (Terminal PR 969 plus branch claude/ce-integrate2-1012); do not re-run their packets.
  - >
    The C02 contract widening forced typing fixes on the paneSync and conformance test fakes
    (Terminal commits ca17729c6 and 8fb010a91); extend those fakes when api.ts grows instead
    of rewriting them.
  - >
    Q03 is adjudicated, not open: the official presented-frame receipt at 453f92fb4 lifted the
    PAN half; the ZOOM half rules only on the Q03b per-input latency metric. The official Q03b
    v1 receipt at e206cd046 (mm zoom p95 20.562 / p99 37.175, lwc p99 38.407) FAILED and the
    hold stands; protocol v2 (DEC:CHART-ENGINE-Q03B-PROTOCOL-V2-WALL-CLOCK-INPUT) is the only
    sanctioned re-measurement and it is taken once.
  - >
    normalizeEngineOptions IS wired (canvas/index.ts:141 and :502); the 2026-10-12 "unwired
    gate" gap was a misreading (census F-5). Do not open a lane to wire it.
  - >
    The PaneHandle identity question is ruled (migration2): a handle denotes ONE pane for its
    lifetime, index() reports the pane's CURRENT slot after swapPanes/movePane, and the
    disposal ladder mirrors LwcPaneHandle. Do not re-litigate it per adapter.
artifacts:
  - docs/CHART_ENGINE_MASTERPLAN.md
  - docs/chart-engine/
  - docs/chart-engine-completion/
  - terminal/lib/chart-engine/
  - terminal/bench/chart-engine.cadence.bench.ts
next_action: >
  Programme delivered to its held gate. Production serves 3e6e9591d21b with mm opt-in and lwc
  default; rollback is re-proven at every deploy. The acceptance ledger is closed (102 ACCEPTED
  / 31 UNRESOLVED / 3 EXCLUDED of 136 rows). The Q03 zoom half stays HELD on the VALID FAIL v2
  receipt (mm zoom p95 21.655 / p99 42.429 ms vs <= 20 / <= 33.4), so the P03 default flip
  (claude/ce-p03-1013 @ 9576169f9) and P04 LWC retirement stay held. Next: the Chairman decides
  whether to commission a prospective Q03b protocol v3 with a new falsifiable diagnosis (stage
  breakdown of the first wheel and per-frame mm zoom cost at equal phase), budgets and workload
  unchanged. The Chairman commissioned it on 2026-10-18; the v3 draft failed its own
  pre-registered B1 check before any receipt, and the Chairman ruled v4 the same day
  (DEC:CHART-ENGINE-Q03B-PROTOCOL-V4-OWN-FRAME-SWAP-END; wave P4-Q03B-PROTOCOL-V4, Terminal PR 1050).
  Next: land PR 1050, take the one official v4 receipt, and on a PASS ship P03 then P04. The
  lightweight-charts attribution (attributionLogo false at 7 sites, no NOTICE link) is DEFERRED
  by Chairman override 2026-10-18 ("we do it in future when i say so"); do not add it until the
  Chairman asks.
---

# Native Chart Engine

Programme of record: `docs/CHART_ENGINE_MASTERPLAN.md` in the Terminal repository, produced
from the Chairman's masterplan archive of 2026-10-11. The renderer is replaced behind the
contract, never the product: `ChartPanel.tsx` keeps every workflow and the `lwc` engine
stays selectable as the rollback path throughout.

Delivery runs as m2 agent-pools fabric lanes that each own a bounded package, commit to
`claude/ce-<pkg>-<wave>`, prove a mutant falsifier RED→GREEN, and return a RESULT.md that the
integration session digests before merging. Waves 1-3 (2026-10-12, suffix `-1012`) ran under
a two-hour Grok/GLM burn directive that the Chairman ended the same day; from wave 4 (suffix
`-1013`) routing follows the normal law: `pool plan` sizes every fan-out, operator-class
commissions go to grok-4.6/glm-5.3 operators that dispatch MiniMax/Qwen executors with
qwen3.8-max review, and Opus suborchestrators (ROUTE: ORCHESTRATION) coordinate multi-lane
commissions under the Fable seat, which keeps PR, merge, deploy and live verification.

## Shipped 2026-10-13 to 2026-10-17 (each merged master deployed with the git-gated build and live-proven)

| PR | Branch | What | Live |
| --- | --- | --- | --- |
| 969 | claude/ce-integrate-1012 | contract, canvas renderer library, workflows, conformance corpus | 04:04Z merge |
| 992 | claude/ce-migration-1013 | ChartPanel M01-M03 migration, mount selector, F-13 guard | ce3, dpl 0e011e81c, 14:41Z |
| 991 | claude/ce-integrate4-1013 | wave-4 P04 hardening F-01..F-16 + ACCEPT gaps | ce4, dpl 175ad49e8, 16:58Z |
| 994 | claude/ce-perf-1013 | perf wave | ce5, dpl 2c16b32e6, 18:11Z |
| 995 | claude/ce-cadence-1013 | Q03 presented-frame cadence instrument + F-4 canvas locale | ce6, dpl fdc7c7f96, 20:14Z |
| 998 | claude/ce-cadence2-1013 | Q03b per-input presentation latency + measured vsync | ce7, dpl 34e390257, 21:10Z |
| 999 | claude/ce-migration2-1013 | boundary closure, PaneHandle ruling, Q04 a11y proofs, forced-lwc fallback removed | ce8, dpl 9938c0cb0, 2026-10-17T07:57Z |
| 1027 | claude/ce-q03c-1013 | Q03b protocol v2 instrument (no receipt; v2 receipt VALID FAIL recorded) | ce9, dpl 3c115e5d1, 2026-10-17T08:53Z |
| 993 | claude/ce-gaps-1013 | GAPS: 31 ledger rows pinned, 4 defect fixes | ce10, dpl 24fd0ce6f, 2026-10-17T11:55Z |
| 997 | claude/ce-census-tests-1013 | census follow-ups C01-A01..A03 | ce11, dpl 3e6e9591d, 2026-10-17T12:56Z |
| 1028 | claude/ce-bench-ready2-1017 | bench readiness retry (harness-only) | merged fb72315fa; shipped in ce10 |

Every live proof ran the four P01 rows (`engine=mm`, default, `engine=bogus`,
`engine=mm&engineProbe=refuse`) against the served `data-dpl-id`; through PR 998 the mm row
sits at the F-13 stage (mm created, guard mounts lwc with the F-13 warning) by design;
from PR 999 (ce8) `?engine=mm` mounts the owned engine with no warning.

## Acceptance state at close (2026-10-17)

| Row | State | Evidence |
| --- | --- | --- |
| P01-A01 opt-in `?engine=mm` mounts the owned canvas engine | PROVEN at ce8 (dpl 9938c0cb0, 2026-10-17T07:57Z: impl=mm, no fallback warning) and re-proven at every deploy through ce11 | live proof `--mm-expect mm --probe` at the ce8 deploy (P01-A01 impl=mm, no fallback warning) |
| P01-A02a/b default and bogus `?engine=` stay on lwc, storage untouched | PROVEN at every deploy ce3..ce11 | live proof cases A02a/A02b, dpl read from the wire |
| P01-A03 `engineProbe=refuse` → typed refusal → lwc | PROVEN at every deploy ce3..ce11 | live proof case A03 (trackingMode refusal wording) |
| Q03 pan half (per-input presentation latency) | LIFTED | official Q03b v1 receipt at e206cd046: mm p95 9.138 / p99 9.639 |
| Q03 zoom half | HELD. The official protocol-v2 receipt (2026-10-14T07:11:40Z, head 1b7ec6a6b, load1 19.71 before / 19.62 at run / 18.66 after) was VALID and FAILED: VALID (zoom input_marks 60 = dispatch.scheduled 60, input_unpresented 0, dispatch_dev_max_ms 0.988 <= 2, heartbeat_mode through with leadin_presentations 0) and FAIL: mm zoom input_to_present p95 21.655 ms > 20 and p99 42.429 ms > 33.4 (runs p95 25.8 / 21.7 / 24.6, p99 42.8 / 42.4 / 38.9; median run 2 by pan p95); pan input_to_present p95 8.905 / p99 9.686 PASS. lwc comparator: runs 1-2 zoom p95 25.5 / 25.3, p99 42.6 / 35.7 (both fail the same budgets); run 3 aborted by a bench-harness navigation race ('Execution context was destroyed' in waitReady, bench/chart-engine.cadence.bench.ts:169), so that session wrote no lwc receipt file; the complete ledger-only lwc comparator taken at 2026-10-14T07:57:33Z (same head, port 3111, load1 17.98) failed in all three runs (zoom p95 26.2 / 24.8 / 25.6, p99 41.6 / 52.3 / 47.2; median receipt cadence-lwc-1b7ec6a6b5ed80f49db2b9d4353cadb98a3f79a8-m2studio.json, budget_ok false, not committed) - a ledger comparator, not a ruling input or a condition of the mm ruling receipt. Per DEC:CHART-ENGINE-Q03B-PROTOCOL-V2-WALL-CLOCK-INPUT the hold stands, the result is recorded (a shared mm+lwc failure recorded as shared), budgets and workload do not move, and the protocol is not amended after the fact. P03 (default → mm) and P04 (LWC retirement) stay HELD; the Q03c PR ships the v2 instrument only, with no receipt committed. | official protocol-v2 receipt, seat, port 3111, head 1b7ec6a6b |
| P03 default flip / P04 LWC retirement | HELD (gated on the zoom half) | branch `claude/ce-p03-1013` @ 9576169f9 held; P04 ≥ 1 release behind P03 |
| Contract census C01-A01..A03 | ACCEPTED | 136-row ledger (102 ACCEPTED / 31 UNRESOLVED / 3 EXCLUDED of 136 rows, docs/chart-engine-completion/acceptance-ledger.md); F-5 corrected C01-A02 to PROVEN (5ef43528b) |

Rollback is one flag: `?engine=lwc` / `mm.engine` storage, or the `resolveMountEngineImpl` default; the lwc adapter stays in the bundle until P4/P6 retire it.
