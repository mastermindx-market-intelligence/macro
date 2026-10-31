---
key: CHART-ENGINE-Q03B-V4-OFFICIAL-RECEIPT-PASS-LIFTS-P03
question: >
  DEC:CHART-ENGINE-Q03B-PROTOCOL-V4-OWN-FRAME-SWAP-END commissioned ONE official Q03b v4 receipt
  for the owned engine ("mm") at a merged master head carrying Terminal PR 1050, ruled on zoom
  input_to_present p95 <= 20 ms and p99 <= 33.4 ms (VALID receipt), with budget_ok explicitly
  NOT the criterion. That receipt has now been taken. What did it show, is the Q03 zoom hold
  lifted, and may P03 (default engine flip to mm) and P04 (LWC retirement) proceed?
answer: >
  PASS. The official q03b-v4 receipt was taken once by the seat at merged master head
  69e8e9f0eaad94180a83b108d05f16ad48c48950 (2026-10-31T06:23:50Z; M2 Studio, 100 Hz panel,
  dpr 2, port 3111, headed prod build with NEXT_PUBLIC_CHART_BENCH=1; load1 22.01 before /
  21.69 at run / 22.83 after, inside the < 24 admission). mm receipt run (run 2, the median by
  pan p95, seed 1371552513): zoom input_to_present p50 / p95 / p99 = 13.466 / 19.300 / 20.356 ms
  (<= 20 and <= 33.4 -> PASS); all three runs p95 16.4 / 19.3 / 16.6, p99 17.4 / 20.4 / 19.0;
  pan input_to_present p95 9.815 / p99 9.943 ms. VALID under every v2/v3/v4 rule: input_marks
  60 = scheduled 60, dispatched 60, input_unpresented 0, dispatch_dev_max_ms 0.334 <= 2,
  heartbeat "through" (260.5 ms) with leadin_presentations 0, forwards 60, paired 60,
  stamp_to_forward 0.582-10.295 ms within [0, 30], own_frame.mapped 60 = scheduled, fallback 0,
  map_max_ms 0.005 <= 0.1, bias_p50 0 / bias_max 4.143 ms, main_tasks 1023 >= 1; the mm session
  had 0 INVALID attempts. The receipt's aggregate budget_ok is false for exactly one metric,
  zoom.presented_p95_ms 20.005 > 20, the vsync-quantized presented-frame INTERVAL on the 100 Hz
  panel that DEC:CHART-ENGINE-Q03-PAN-LIFTED-ZOOM-RULES-ON-INPUT-LATENCY already excludes from
  the zoom ruling; it is recorded here and the budget_ok:false JSON is kept out of
  docs/chart-engine-completion/receipts/ as that decision requires. Ledger comparator only (not
  a ruling input): lwc receipt run (run 2, seed 1371552512) zoom p50 / p95 / p99 = 17.786 /
  26.278 / 41.341 ms (runs p95 26.3 / 30.1 / 24.8, p99 41.3 / 39.6 / 35.7), pan p95 9.578 / p99
  17.719, VALID (mapped 60, fallback 3 <= mapped, map_max 0.005, main_tasks 1139) after 2
  INVALID attempts in run 2 (attempt 1: input_marks 51, unpresented 4, paired 48, mapped 47;
  attempt 2: dispatch_dev_max_ms 3.489 > 2); lwc FAILS both latency budgets. The Q03 zoom hold
  is LIFTED; both Q03 halves are now passed on the ruling metric. P03 (default flip to mm, LWC
  selectable as the rollback) proceeds on claude/ce-p03b-1018 (Terminal PR 1064), and P04 (LWC
  retirement) follows at least one production release after P03 ships with the rollback row
  re-proven. The protocol, budgets and workload are not amended; v4 is not re-run.
rationale: >
  The v4 decision pre-registered the criterion (VALID and zoom input_to_present p95 <= 20 / p99
  <= 33.4 on the single official mm receipt), the environment (reference Mac, port 3111, load1
  < 24, headed prod build), the ruling script semantics and the explicit statement that
  budget_ok false on the interval limits is not the criterion. The receipt satisfies every
  validity rule and both latency budgets with a 0.70 ms p95 margin and a 13.0 ms p99 margin, so
  the pre-registered PASS branch applies mechanically; reading it any other way would be the
  after-the-fact amendment D10 forbids. The interval violation is the known 20.004 ms vsync
  quantization of an input-bound ~50 Hz wheel stream on a 100 Hz panel
  (DSC:CHART-ENGINE-PRESENTED-INTERVAL-IS-INPUT-BOUND), already ruled out of the zoom criterion.
  The lwc comparator is kept for the ledger so the shared-floor history stays visible, but the
  v2 and v4 decisions make the mm receipt alone the ruling input. own_frame.fallback is a count
  of mapped forwards answered by the next committed frame (validator: fallback <= mapped only),
  not an INVALID rule, so lwc's 3 fallbacks do not invalidate its comparator run.
alternatives:
  - option: Rule on the receipt's aggregate budget_ok (false) and keep the hold
    why_not: >
      DEC:CHART-ENGINE-Q03-PAN-LIFTED-ZOOM-RULES-ON-INPUT-LATENCY and the v4 decision both state
      that the presented-frame interval cannot rule an input-bound zoom and that a v4 PASS
      receipt still reads budget_ok false at 20.004 ms; applying budget_ok now would change the
      criterion after the result.
  - option: Re-run to widen the 0.70 ms p95 margin before flipping
    why_not: >
      The protocol is taken ONCE; a repeat would be a second sample under the same protocol,
      which D10 and the v4 decision forbid in both directions (never re-run a VALID FAIL, never
      cherry-pick among VALID PASSes).
  - option: Treat lwc's own_frame.fallback=3 as INVALID and discard the comparator
    why_not: >
      fallback is a counted answer mode (the terminated-EventLatency rule in the v4 decision),
      bounded only by fallback <= mapped in lib/chart-engine/bench/cadence.ts; it is not among
      the v4 INVALID rules (mapped != scheduled, map_max_ms > 0.1, main_tasks < 1). The
      comparator is ledger-only anyway and does not condition the mm ruling.
evidence:
  - >
    Receipt directory on the seat Mac: q03/receipts-69e8e9f0eaad/ (cadence-mm-69e8e9f0ea...-m2studio.json,
    cadence-lwc-69e8e9f0ea...-m2studio.json, run.log, sidecar.json, displays.txt); taken with the
    persisted runner handoff_kits/meta-ceo-b-2026-09-08/ext/ce-scratch-1013/launch/q03_official.sh
    (Q03_BUILD_ONLY=1 build at the head, then Q03_REUSE_BUILD=1 run once load1 < 24), ruled with
    launch/q03_v4_rule.py -> "RULING: PASS (mm zoom p95 19.30000001192093 <= 20.0 and p99
    20.35599994659424 <= 33.4)"; "INVALID attempts before a valid run: {'lwc': 2}".
  - >
    mm receipt JSON gesture.zoom: input_to_present_p50/p95/p99_ms 13.466 / 19.300 / 20.356;
    presented_p95_ms 20.005 (the only violation); dispatch {scheduled 60, dispatched 60,
    dispatch_dev_max_ms 0.334, seed 1371552513}; forward {forwards 60, paired 60,
    stamp_to_forward_min/p50/max_ms 0.582 / 6.355 / 10.295}; own_frame {mapped 60, fallback 0,
    map_max_ms 0.005, bias_p50_ms 0, bias_max_ms 4.143, main_tasks 1023}; awake_start
    {heartbeat_mode through, heartbeat_ms 260.5, leadin_presentations 0}; protocol "q03b-v4";
    generated_at 2026-10-31T06:23:50Z; sidecar load1 22.01 / 21.69 / 22.83; displays.txt 100 Hz.
  - >
    lwc receipt JSON gesture.zoom: input_to_present p50/p95/p99 17.786 / 26.278 / 41.341;
    own_frame {mapped 60, fallback 3, map_max_ms 0.005, main_tasks 1139}; dispatch_dev_max_ms
    1.409; two CADENCE_INVALID lines for lwc run 2 attempts 1-2 in run.log.
  - >
    Validator semantics: terminal/lib/chart-engine/bench/cadence.ts at 69e8e9f0e — INVALID
    (q03b-v4) only for own_frame.mapped != dispatch.scheduled, map_max_ms > CADENCE_V4_EL_MAP_MAX_MS
    (0.1) and main_tasks < 1; fallback is bounded by "fallback must be <= mapped" (a schema
    error, not a protocol INVALID).
  - >
    Head provenance: 69e8e9f0eaad is merged master containing Terminal PR 1050 (v4 instrument +
    PERF-C) and PR 1085 (mm parity); production served the same head at receipt time.
  - >
    Pre-registered expectation in DEC:CHART-ENGINE-Q03B-PROTOCOL-V4-OWN-FRAME-SWAP-END (mm v4
    diag 18.065 / 18.962 ms, "PASS, ~2 ms p95 margin — may still fail"; lwc 28.839 / 44.898
    FAIL): the receipt landed 1.2 ms above the diag p95 and inside the budget, and lwc failed
    as expected.
affects:
  - "WS:NATIVE-CHART-ENGINE"
  - terminal/lib/chart-engine/select.ts
  - terminal/components/ChartPanel.tsx
  - docs/chart-engine-completion/**
confidence: high
reversibility: easy
decided_by: >
  seat session 6dfa7fe4-64c1-4a36-a3bc-af2fa0e5ba79 (Fable principal) applying the
  Chairman-ruled v4 criterion mechanically; the flip itself ships through the ordinary
  Terminal delivery chain (PR 1064, CI, merge-on-green, git-gated deploy, live proof)
decided_at: 2026-10-31
---

# DEC-CHART-ENGINE-Q03B-V4-OFFICIAL-RECEIPT-PASS-LIFTS-P03

The single official Q03b v4 receipt commissioned by
`DEC-CHART-ENGINE-Q03B-PROTOCOL-V4-OWN-FRAME-SWAP-END` was taken on 2026-10-31 at merged master
`69e8e9f0eaad` and PASSES: mm zoom input_to_present p95 19.300 ms / p99 20.356 ms against
<= 20 / <= 33.4, VALID on every v2/v3/v4 rule, zero INVALID attempts. The Q03 zoom hold is
lifted; P03 proceeds and P04 follows at least one release later. Workstream
`agentos/workstreams/WS-NATIVE-CHART-ENGINE.md`.

## Receipt summary (ms; receipt run = median run by pan p95)

| engine | zoom p50 | zoom p95 | zoom p99 | runs p95 | runs p99 | pan p95 / p99 | validity | INVALID attempts | outcome |
|---|---|---|---|---|---|---|---|---|---|
| mm | 13.466 | 19.300 | 20.356 | 16.4 / 19.3 / 16.6 | 17.4 / 20.4 / 19.0 | 9.815 / 9.943 | VALID (mapped 60, fallback 0, map max 0.005, main tasks 1023) | 0 | **PASS** |
| lwc (ledger only) | 17.786 | 26.278 | 41.341 | 26.3 / 30.1 / 24.8 | 41.3 / 39.6 / 35.7 | 9.578 / 17.719 | VALID (mapped 60, fallback 3, map max 0.005, main tasks 1139) | 2 (run 2) | FAIL |

`budget_ok` is false on both receipts for `zoom.presented_p95_ms` (20.005 / 20.008 > 20), the
vsync-quantized interval the zoom ruling excludes; the JSON therefore stays uncommitted and the
numbers live here, exactly as the v4 decision prescribes.

## What this does and does not change

- Lifts the Q03 zoom hold recorded by `DEC-CHART-ENGINE-Q03B-ZOOM-HOLD-STANDS-TWO-DEFECTS` and
  the v2 VALID FAIL; both Q03 halves now pass on the ruling metric.
- P03 (`claude/ce-p03b-1018`, Terminal PR 1064: BUILD_DEFAULT_ENGINE = "mm", storage-aware mount
  selection, engine telemetry, mm session shading, mm tickMarkFormatter TickMarkType) may ship
  through the normal chain; the three ChartPanel-bound evidence packets must be green at its
  final head.
- P04 (LWC retirement) stays at least one production release behind P03.
- Nothing about the protocol, budgets, workload or environment moves; v4 is not re-run.
