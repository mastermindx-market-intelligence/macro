---
key: TERMINAL-DATACACHE-IDB-COPY-HIDES-REFRESH-FAILURE
claim: >
  In a real browser, a Terminal `dataCache` read (default `swr: true`) of a key that has
  landed even once never reports `unavailable` again, however long the source stays
  down. The IndexedDB copy keeps standing in for the failed read. Every successful
  read is written through to IndexedDB. When the source then fails:
  - A stale read serves the memory copy and revalidates in the background.
  - The failed revalidate deletes only the memory entry
    (terminal/lib/dataCache.ts:244, `if (outcome.status !== "data") ... store.delete(url)`).
    The IndexedDB record stays.
  - The next read is therefore a full memory miss. It takes the IndexedDB read-back path,
    and `_seedDecision` classifies the persisted record as `stale-swr` (:375).
  - That path serves the old data as `{status:"data"}` and fires another background
    revalidate, which fails the same way.
  The docblock at :309 states the design ("Every cached/stale serve is `data`"), so
  `CacheOutcome` carries no age or staleness. A consumer cannot tell a served-stale
  record from a fresh answer.
  Measured with the Terminal's real `dataCache` + `idbJsonStore` against a fake
  IndexedDB and a fetch that always answers 503:
  - with a 10-minute-old IndexedDB record for `/data/manifest.json`, four reads returned
    `[data, data, data, data]` while all four network attempts failed;
  - the same sequence with no IndexedDB returned `[data, unavailable, unavailable]`.
falsifier: >
  Re-run the reproduction on the current Terminal master:
  - copy the `makeFakeIndexedDB()` harness from
    terminal/lib/__tests__/dataCachePersist.test.ts into a scratch test;
  - `idbPut("/data/manifest.json", {names:["SPY"]}, Date.now() - 600_000)`;
  - stub `fetch` to `new Response("down", {status: 503})`;
  - call `getJSONResult` four times with a 20 ms flush between calls
    (`cd terminal && npx vitest run lib/__tests__/<scratch>.test.ts`).
  The claim is false if any of those reads returns `unavailable` while the record is
  still in IndexedDB, or if the result carries an age/stale flag the caller can read.
  It is also false if a failed revalidate starts deleting or marking the IndexedDB record
  (dataCache.ts:244), or if `stale-swr` stops being the read-back decision for an
  expired record (:375).
  Either change would mean the trap has been fixed. A test that never installs
  `globalThis.indexedDB` cannot falsify this: under jsdom/node, persistence is a no-op
  and the control sequence is what you get.
so_what: >
  The failure-state law requires that a refresh which failed must keep the rows and
  say they are stale. On any surface that reads through `dataCache`, that label cannot
  be driven from `getJSONResult` in a real browser. The surface keeps showing an
  old copy, unlabelled, for as long as the source is down. TerminalShell persists
  `/data/manifest.json` (components/TerminalShell.tsx:1781 on master), so the Heatmap's "could not
  refresh" label (Terminal PR #891) is reachable only in unit tests, not in a browser.
  Three consequences:
  - Do not try to prove such a label with an e2e test. It will never appear, and a spec
    that "passes" without it has proved nothing.
  - Do not read `status:"data"` from `dataCache` as "the source answered just now".
  - The real fix is in `dataCache`: add age/staleness to `CacheOutcome`, or report a
    failed revalidate to the caller.
  Until then, prefer `flowGetResult` (terminal/lib/flowClientCache.ts) for a read whose
  refresh failure must be visible; it caches in memory only. A first read on a cold
  memory cache still reports an outage correctly, because no record exists yet.
kind: landmine
verified_at: 2026-10-09
verified_by: >
  Run on Terminal branch claude/gex-levels-load-failure-state at 27270b385. That branch
  does not modify dataCache.ts. Its base 5503f970 differs from origin/master
  c968e81bfd56 only in `getSliceAndOhlc` (#871), not in `getJSONResult` or `doFetch`.
  Command: `npx vitest run lib/__tests__/zzScratchIdbStaleFailure.test.ts`, using the
  `makeFakeIndexedDB()` harness from dataCachePersist.test.ts. Log lines:
  - `IDB present: [ 'data', 'data', 'data', 'data' ] fetches: 4`
  - `no IDB: [ 'data', 'unavailable', 'unavailable' ]` (control)
  Line anchors checked on origin/master c968e81bfd562102e7d878c93bbd34c7650727b1 via
  `git show origin/master:terminal/lib/dataCache.ts | grep -n`. Results: :244 (memory-only
  delete), :309 (docblock), :318 (`swr` default true), :375 (`stale-swr` read-back).
  e2e cross-check: a Heatmap refresh-failed crop could not be produced while
  TerminalShell had persisted the manifest; the tiles stayed up, unlabelled.
scope:
  - terminal
  - terminal/lib/dataCache.ts
  - terminal/components/heatmap/HeatmapView.tsx
  - any Terminal surface that shows a refresh-failed state from a dataCache read
confidence: verified
---

This is a sibling of DSC-A-FAILED-INDEX-READ-CANNOT-SET-THE-LEAF-ERROR. In both cases a
state the failure-state law requires cannot be produced because of a layer below the
view. Here it is the persistence tier, not a missing request.

Memory-only behaviour is correct: an outage after the memory entry is evicted reads as
`unavailable`. The IndexedDB tier was added so a revisit paints instantly. Its read-back
deliberately trusts the persisted record, and nothing tells it the source was just tried
and failed.

The trap does not affect the cold, first-ever read: with no record, a failure reports
`unavailable`. That is why load-error states (the Heatmap's "Could not load the heatmap")
remain reachable while the refresh-failed state does not.
