---
key: TERMINAL-L01A02-CHECKER-DROPS-WRITES-AFTER-A-THEN-CALLBACK
claim: >
  In charting-app, the L01-A02 source-read check in
  `terminal/lib/__tests__/chartEngineGapLiveReplay.test.ts` (scanGuardedWrites, lines
  191-226) ends an `await` continuation at the next line that matches `.then(`, `.catch(`,
  `.finally(` or a timer call, and gives that callback a range covering only its own
  parenthesised body. A guarded write that sits after such a callback and before the next
  `await` inside ChartPanel's data-load async IIFE therefore falls in no range and is
  skipped, counted as neither guarded nor unguarded. Adding one promise callback to that
  IIFE makes the check fail as a shortfall (guarded below the floor of 14, zero unguarded)
  even though no guard was removed.
falsifier: >
  From `terminal/` run `npx vitest run lib/__tests__/chartEngineGapLiveReplay.test.ts` on
  Terminal commit 65bc60875 (train 3 after merging master 367f488e5) and on 94d77c61d (the
  same tree with E19's inline `staleServe.revalidation.then(...)` moved into the
  module-level `recordOhlcCopy` helper, ChartPanel.tsx line 616, called at line 9137). The
  claim is false if 65bc60875 does not fail the ">= 14 guarded sites, zero unguarded" case
  with 12 guarded and 0 unguarded, if 94d77c61d does not pass it with 14 guarded and 0
  unguarded, or if `git diff 65bc60875 94d77c61d -- terminal/components/ChartPanel.tsx`
  adds or removes any `cancelled` / `epochRef.current !== epoch` guard line.
so_what: >
  When L01-A02 fails with a guarded count below 14 and zero unguarded sites, look for a new
  callback line inside ChartPanel's data-load async IIFE before concluding a merge dropped
  guards. Keep promise callbacks out of that IIFE body by moving them into a module-level
  helper that takes the epoch check as a closure, which keeps the behavior and restores the
  count. Never lower the floor of 14, edit the checker, or reorder writes to satisfy it.
kind: landmine
verified_at: 2026-10-18
verified_by: >
  Terminal landing train 3 (#960), fold round 7, 2026-10-18: the full vitest suite on merge
  commit 65bc60875 failed only L01-A02 with 12 guarded and 0 unguarded; the same file on
  94d77c61d passed with 14 guarded and 0 unguarded, and the diff between them touches only
  ChartPanel.tsx and adds no guard line. scanGuardedWrites read on that head: an `await`
  range runs `while` neither `await` nor CALLBACK matches, a CALLBACK line opens a range
  closed by bracket depth, and a write with no containing range hits `continue`. A
  read-only fabric reviewer (minimax lane e20-fold7-review-m) accepted the move as
  behavior-preserving.
scope:
  - "charting-app"
  - "terminal/components/ChartPanel.tsx"
  - "terminal/lib/__tests__/chartEngineGapLiveReplay.test.ts"
  - "WS:TERMINAL-ENHANCEMENTS20"
confidence: verified
---

## Grounds

The checker models each async continuation as a line range. An `await` opens a range that
runs to the next suspension point, and a callback handed to `.then`/`.catch`/`.finally` or
a timer is its own continuation, closed when its bracket depth returns to zero. The
innermost range containing a write must show a guard at or above the write. Writes with no
containing range are synchronous setup by the checker's model and are skipped. That model
is sound for a callback that is the last statement before the next `await`, but code after
the callback's closing parenthesis is neither inside the callback nor inside an `await`
range, so the writes there drop out of the count.

E19 (chart capture and the saved-copy label) registered `staleServe.revalidation.then(...)`
right after the OHLC read in the data-load IIFE. Master's #999-#1046 closure added the
floor of 14 to the test. Each change was green alone, and only the merged tree showed the
shortfall. The two hidden sites were real, guarded writes.

## What a session does with this

- Read the failure's numbers before diagnosing. A shortfall with an empty `unguardedSites`
  list means writes were hidden from the checker, while an unguarded site means a guard is
  really missing.
- Put the callback in a module-level helper (the pattern is `recordOhlcCopy(copyRef,
  staleServe, stillOwner)` in ChartPanel.tsx) and call it from the same point in the IIFE.
- Any ChartPanel.tsx edit also reds the three ChartPanel-pinned evidence packets; see the
  Terminal memory `chartpanel-evidence-recapture-gate` and recapture them for real.
- Related: DEC:TERMINAL-E20-LANDING-TRAINS-ONE-CI-ONE-SQUASH (the train runs the full suite
  on the merged tree, which is where this surfaced).
