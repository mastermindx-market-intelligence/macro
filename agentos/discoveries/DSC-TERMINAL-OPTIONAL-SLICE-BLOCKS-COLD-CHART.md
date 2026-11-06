---
key: TERMINAL-OPTIONAL-SLICE-BLOCKS-COLD-CHART
claim: >
  At Terminal source 6cbc9a8c4a202fafba415996e479444a2fa30f92, the daily
  cold-chart path waits for optional slice metadata together with required OHLC,
  so a pending slice can delay bars and semantic data readiness after OHLC arrives.
falsifier: >
  Read terminal/lib/dataCache.ts:588-590 and terminal/components/ChartPanel.tsx:8707-8718
  at the named source, then repeat the PR #842 loopback controlled comparison with
  fast valid OHLC and an eight-second slice delay, observing the existing
  mm:terminal-visual-ready event for NVDA/3D. Data readiness while that slice is
  still pending disproves the runtime dependency; source no longer awaiting the
  joined result disproves applicability to the new source.
so_what: >
  Diagnose navigation-to-first-chart dependency ordering before proposing another CDN
  or treating compression as missing. A future bounded repair should let required
  bars become usable independently of optional slice enrichment while preserving all
  current readiness criteria, including indicator/render/coordinate checks. Emit the
  existing semantic data-ready event only when those criteria are met; never equate
  HTTP completion with readiness. Preserve current generation/epoch ownership, cache
  inflight deduplication, request-ownership guards, and empty/error outcomes. Reuse the
  existing readiness event for any passive timing observer; do not invent another signal.
kind: architecture
verified_at: 2026-10-07
verified_by: >
  Terminal PR #842 at 6cbc9a8c4a202fafba415996e479444a2fa30f92;
  terminal/lib/dataCache.ts:588-590; terminal/components/ChartPanel.tsx:8707-8718;
  loopback Playwright controlled comparison, two desktop cases / one worker / 20.0s;
  accepted diagnostic log sha256 69cbe53387ccabb64ff1fcc8e8f6e0df321a0b076ac5c0ae1cc21df7cdc2b3e9.
scope:
  - terminal
  - terminal/lib/dataCache.ts
  - terminal/components/ChartPanel.tsx
confidence: verified
---

## Source and evidence boundary

The assessed implementation is [Terminal #842](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/842),
source `6cbc9a8c4a202fafba415996e479444a2fa30f92`. The immutable broader assessment is
[docs/TERMINAL_HIGH_LATENCY_2026-10-07.md](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/6cbc9a8c4a202fafba415996e479444a2fa30f92/docs/TERMINAL_HIGH_LATENCY_2026-10-07.md).
`getSliceAndOhlc` joins `getOhlc` and `getSlice` with `Promise.all`. ChartPanel awaits
that joined result before constructing its daily bars. This record concerns that
cold daily path, not all timeframes, warm caches, or every user's startup.

## Controlled runtime comparison

The parent accepted the final source-custody and command/log receipt after direct
host readback: two desktop tests passed, one worker, 20.0 seconds. Both tracked and
staged `git diff --exit-code` checks passed, the head remained the named Terminal
source, and the temporary diagnostic spec was absent after cleanup. Both arms used
loopback traffic and aborted the external Brain script; no China, cruise, production,
or private-account traffic was measured.

| Arm | OHLC response end | Slice response end | Existing data-ready event | Other dependency |
|---|---:|---:|---:|---|
| Slice delayed | 133.9 ms | 8154.9 ms | 8225.8 ms | No data-ready event while slice pending |
| Manifest delayed | 127.6 ms | 126.6 ms | 700.9 ms | Manifest requested 732.1 ms; completed 8757.5 ms |

Times are navigation-relative, not module boottrace durations. The slice-delay
ready event was NVDA/3D, generation 1, outcome data. Both arms reported empty page-error
and readiness-diagnostic arrays. A prior attempt lacking the inlined fixture environment
was rejected and is not evidence. The valid build used Node 26.5; the local next start fixture server
and tests used Node 20.20.2. These two diagnostic cases demonstrate dependency ordering,
not a measured speedup or a production performance distribution.

The accepted valid diagnostic log `startup-optional-delay-valid-diagnostic.log`
has SHA256 `69cbe53387ccabb64ff1fcc8e8f6e0df321a0b076ac5c0ae1cc21df7cdc2b3e9`.
The fixture production-build log has SHA256
`526964703755334e385987cf5aa9fdb4d3b167e325541bd1c27f74c1fa2d6c66`.
The removed temporary spec had SHA256
`c17e163619cfa34fd8f9468d23b05c69be1af0e4a1412d50b6a18d870b0f27a9`.
These are accepted observation receipts, not promises that host scratch logs or the
removed test path remain available forever. Primary durable context is #842 and
its pinned assessment; no test source or implementation is shipped by this DSC.

Historical command, run from `terminal/` with cached Node 20 on PATH:

```bash
PATH=<cached-node20-dir>:$PATH TERMINAL_E2E_PORT=3137 <node20> node_modules/@playwright/test/cli.js test e2e/startup-optional-delay-diagnostic.spec.ts --project=desktop --workers=1 --reporter=list
```

The temporary spec was deliberately removed. That command alone is not currently
runnable. To recreate the falsifier in a separately owned diagnostic checkout:

1. Check out the named source and use the repository's unchanged Playwright fixture
   environment for both build and server, including values inlined at build time.
   Build afresh; reject a setup without those fixture values instead of counting it.
2. Add two temporary desktop cases using fresh browser contexts so in-memory/IDB
   data from an earlier visit cannot hide the cold dependency. Install a listener
   for existing `mm:terminal-visual-ready` before navigation; record navigation-relative
   request/response times, matching symbol/timeframe/generation/outcome, page errors,
   and readiness diagnostics. Restrict traffic to loopback and abort external Brain
   JavaScript identically in both arms.
3. In the slice arm, provide valid fast OHLC for NVDA/3D and delay only the existing
   slice route response by eight seconds. Assert no semantic data-ready event while
   the slice is pending; then require the existing data-ready event after completion.
   Reject either page errors or readiness diagnostics as a valid ordering proof.
4. In the control arm, provide fast OHLC and slice responses and delay only the
   manifest response by eight seconds. Require data readiness before manifest
   completion, again with no errors/diagnostics. This separates slice gating from
   the background manifest dependency.
5. Run the bounded two-case command above under Node 20, preserve the output and
   source pin, remove only the temporary spec, and confirm tracked/staged source
   unchanged. A changed ordering on a newer source is a new result, not a reason
   to reuse the old timings.

In the slice arm the pending snapshot at 4390.1 ms contained no ready event, page
error, or readiness diagnostic. Manifest was already requested at 4043.9 ms and
completed at 4050.8 ms; intel/fund/options requests also began before the delayed
slice completed. Background/fallback traffic can therefore start while the first
chart is delayed. No bandwidth-competition magnitude was measured, so do not
attribute a quantified delay to that traffic.

## Working transport and missing measurement

The immutable assessment already records functioning Tencent EdgeOne caching and
compression in sampled non-China traffic: repeating its initial 35 JS/CSS assets
with Brotli gave 1,012,061 bytes versus 1,031,424 gzip bytes, about 1.9 percent less.
Those observations do not establish the account's acceleration region, plan,
serving POPs, or cross-mainland routing feature. Hong Kong/Singapore assignment and
actual mainland-China/cruise loading remain unverified.

The inspected telemetry does not persist navigation-to-first-chart timing or RTT.
`ticker_view` is active-symbol state; boottrace marks stay local and use module-relative
timing. This is not a claim that chart timing has never been measured: the historical
cold-timeframe discovery below already contains controlled local measurements.
A future timing observer should reuse `mm:terminal-visual-ready`, with navigation
identity, generation, outcome, and elapsed timing; ticker timestamps and dwell are
not historical rendered-readiness evidence.

## Continuation and do not redo

This is an additive knowledge receipt, not an implementation release or an execution
permission. It creates no workstream, formal handoff parent, cache, telemetry store,
CDN configuration, or ready authority. Terminal #842 remains the startup-read carrier;
its synthetic server-to-Supabase saved-hop result is separate from this optional-slice
finding and from unmeasured China/cruise performance. Preserve existing lazy-loading
#654 and held SWR #707 and reconcile their current custody before touching their paths.

- `DSC:TERMINAL-COLD-CHART-LOADS-THE-SSR-DEFAULT-TIMEFRAME` / Terminal #478:
  settled discarded-default-timeframe startup work; do not duplicate it or call
  local boottrace a persisted historical timing stream.
- `DSC:TERMINAL-MOUNT-RESTORE-CAN-BE-STARVED` / Terminal #457:
  distinguish render from commit under CPU pressure; preserve semantic ordering proof.
- `DSC:TERMINAL-OBSOLETE-404-CAN-HIDE-RECOVERED-CHART-DATA` / Terminal #705:
  preserve the repaired common request-ownership boundary for success and absence;
  do not add another cache, generation store, or timer.
- `DSC:TERMINAL-QUOTE-DEMAND-SILENT-SLICE` / Terminal #429:
  that settled transport batch truncation is a different meaning of slice; preserve
  planned quote demand and do not raise the batch cap as a shortcut.

No existing WS or held owner record is updated. The existing Terminal canonicalization
workstream governs #483 deployment/repository reliability; its parked deployment alias
must not be reactivated to provide a parent for this assessment.
