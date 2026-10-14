---
key: CHART-ENGINE-PRESENTED-INTERVAL-IS-INPUT-BOUND
claim: >
  The Q03 presented-frame interval (terminal/lib/chart-engine/bench/cadence.ts, receipt fields
  pan/zoom presented_p95_ms / presented_p99_ms) cannot be lower than the harness's own input
  dispatch interval, so on every host measured so far the zoom p95 sits at the wheel-dispatch
  spacing (about 20 ms at 46-49 Hz, quantized to the display's vsync slots: 30 ms on a 100 Hz
  panel) for BOTH engines while the trace shows exactly one presented frame per input and zero
  dropped frames; the number measures the driver's wheel cadence, not the renderer.
falsifier: >
  Run `NEXT_PUBLIC_CHART_BENCH=1 npm run build && npm run start -- -p 3111` then
  `BENCH_RUNS=3 BENCH_OUT_DIR=<dir> BENCH_BASE_URL=http://127.0.0.1:3111 npx playwright test -c
  playwright.bench.config.ts bench/chart-engine.cadence.bench.ts` on a host where the console
  CADENCE_DIAG line reports zoom input_hz >= 100 (input_floor_ms <= 10) and see zoom
  presented_p95_ms stay at 30 ms for mm, or find any receipt whose zoom presented_p95_ms is below
  its own input_floor_ms with presented_per_input ~ 1.0; either disproves the claim. A receipt
  with dropped > 0 or presented < inputs is a renderer finding and does not bear on this claim.
so_what: >
  Never read a cadence p95/p99 without the CADENCE_DIAG line (input_hz, input_floor_ms,
  presented_per_input) beside it, and never compare engines across hosts or sessions with
  different input_hz. A zoom p95 at the input floor is NAMED-INPUT-BOUND, not a renderer failure
  and not a pass; do not lower the 20 / 33.4 ms budgets to it (D10). The renderer-attributable
  quantity is per-input presentation latency (one performance.mark per dispatched input, interval
  from that mark to the next STATE_PRESENTED_ALL frame, intervals with no input pending dropped);
  that metric is commissioned as the Q03b follow-on on claude/ce-cadence-1013 and is what lifts the
  P03 hold in DEC:CHART-ENGINE-P03-FLIP-GATED-ON-PRESENTED-FRAME-CADENCE for the zoom gesture.
  Official receipts also need the display refresh pinned: the Mac has 50 Hz and 100 Hz panels and
  the budgets are 60 Hz figures (33.4 = 2 x 16.7).
kind: constraint
verified_at: 2026-10-13
verified_by: >
  Clean rehearsal on the Mac (M2 Ultra, 100 Hz display, load1 6.7-7.5, prod build at
  claude/ce-cadence-1013 c8401348e, BENCH_RUNS=3): mm pan 10.0/10.0 ms (input_hz 99.7, presented
  202/200, dropped 0), mm zoom 30.0/30.0 ms (input_hz 49.3, presented 60/60, dropped 0, p50 20.0);
  lwc pan 10.0/20.0 ms (dropped 2-3), lwc zoom 30.0/30.0 ms (input_hz 45.7, presented 61/60);
  second run at 8ce1b1af9 under load1 27.8-57.9: mm pan input_hz fell to 64-85 and pan p95 rose to
  20-40 ms with presented_per_input = 1 in every run; headless smoke on ubuntu1 (CADENCE-REV lane
  ce-cadence-rev3-1013): input_hz 22.3, pan p95 49.5 ms, zoom p95 63.1 ms, presented == inputs
  for zoom (60 == 60). Independent review finding F2 (qwen3.8-max, VERDICT ACCEPT_WITH_PATCHES)
  reached the same reading; the input-rate-floor section was added to
  docs/chart-engine-completion/bench.md and the CADENCE_DIAG print to the spec (commit 8ce1b1af9,
  merged as Terminal PR #995).
scope:
  - "WS:NATIVE-CHART-ENGINE"
  - mastermind-terminal terminal/lib/chart-engine/bench/**
  - mastermind-terminal terminal/bench/chart-engine.cadence.bench.ts
  - mastermind-terminal docs/chart-engine-completion/bench.md
confidence: verified
---

# DSC-CHART-ENGINE-PRESENTED-INTERVAL-IS-INPUT-BOUND

Found while adjudicating Q03 for the 2026-10-13 chart-engine completion wave (seat ruling 5,
`DEC-CHART-ENGINE-P03-FLIP-GATED-ON-PRESENTED-FRAME-CADENCE`). The presented-frame instrument is
correct about what it measures; the finding is about what that measurement can and cannot say.

## Reading a receipt

| Field | Meaning | Renderer evidence? |
|---|---|---|
| `presented_p95_ms` at or just above `input_floor_ms` with `presented_per_input` about 1.0 | the renderer kept up with every input; the interval is the input gap | no (input-bound) |
| `presented < inputs`, `dropped > 0`, or intervals well above `input_floor_ms` | frames were skipped or coalesced | yes |
| `presented_p95_ms` below the budget with `input_floor_ms` below the budget | the renderer presented within budget at an input rate fast enough to test it | yes (pass) |

The pan gesture dispatches near 100 Hz on the Mac and does test the renderer against the 20 ms
budget; the wheel gesture dispatches near 47 Hz and does not. The budgets, the gesture script, the
corpus and the run count were not changed after these results (D10).
