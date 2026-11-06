---
key: A-FAILED-INDEX-READ-CANNOT-SET-THE-LEAF-ERROR
claim: >
  When a surface is read through a TWO-LEVEL chain - an index read that yields the list of
  point-in-time stamps, then a frame read for the selected stamp - putting the honest
  "read failed" state only on the LEAF read leaves the chain's most common failure
  reported as ABSENCE. A failed index read produces no stamp, the frame fetch is never
  issued, and the leaf's `frameError` therefore CANNOT be set; the empty surface falls
  through to the "no data yet / nothing is hidden" copy and asserts, falsely, that the
  session simply has nothing. In the Terminal this was exact:
  `terminal/components/surface/replayContext.tsx:122` sets `setIndexError(true)` and
  leaves `stamps`/`indexDate` untouched, while
  `terminal/components/surface/SurfacePane.tsx` keyed its empty state on `frameError`
  alone. The same shape appeared one level up in the scrubber, where an index that never
  loaded borrowed `replayRefreshFailed` ("retaining stored frames") - a retention claim
  that is a lie when nothing was ever admitted to retain.
falsifier: >
  Make the index failure path populate a stamp (so a frame read is issued and the leaf
  error can fire), collapse the index and frame reads into one request, or give the leaf
  read an independent failure signal that does not depend on having a stamp to request.
  Any of these breaks the "the leaf error can never be set" step. Concretely: in
  terminal/lib/__tests__/surfaceReplayMounted.test.tsx, the test "reports a cold index
  transport failure as unavailable, not absence or retention" must go red when
  `readFailed` in SurfacePane.tsx:352 is reduced back to `frameError`.
so_what: >
  Apply the failure-state law at EVERY read level in a chain, not just at the leaf, and
  test each level with its own cold-transport case. Distinguish the two failures in copy:
  a refresh that failed while frames are already held is RETENTION ("retaining stored
  frames"); an index that never landed is UNAVAILABILITY ("frame list not loaded") and
  must never borrow the retention string. A surface whose empty state is driven by one
  boolean is almost certainly under-reporting - count the reads between the user and the
  bytes first, then count the failure states.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  terminal/components/surface/replayContext.tsx:114-123 (isSurfaceIndexForContext gate;
  the else branch sets only indexError and leaves stamps/indexDate as they were);
  terminal/components/surface/SurfacePane.tsx:341 (frameError state), :346 + :581
  (frameError is set only around an issued frame fetch), :352 (the repair:
  `readFailed = frameError || (indexError && indexDate == null)`), :1617 + :1621 (the two
  empty-state ternaries);
  terminal/components/surface/ReplayBar.tsx:238 + :241 (index-failure copy) and :247 (the
  retention notice now requires hasFrames);
  mastermindx-market-intelligence/mastermind-terminal PR #608, head
  aa9333502ecad41054b5d392a4fae9138b163e04. Discriminating RED/GREEN recorded in
  terminal/docs/evidence/options-workbench-r0-20260917/review-hardening-v3-20260929/
  (cold-index-red.log, cold-index-green.log) - reducing readFailed to frameError alone
  reds the cold-index test while the rest of the surface family stays green.
scope: [terminal, "terminal/components/surface/**"]
confidence: verified
---

## Detail

The law "a read that did not land is NOT an empty result" was already known and already
applied here - and the surface still lied, because it was applied at one level of a
two-level read.

The chain is: `surface_idx:<root>` returns `{date, stamps[]}`; the replay cursor picks a
stamp; `surface_at:<root>:<stamp>` returns the frame. Failure handling had been built
around the second request, which is the one that visibly "loads data". But the second
request is *conditional on the first succeeding*. When the index read fails, there is no
stamp, so no frame request is ever issued, so the frame error state is unreachable by
construction. Every symptom of the index failure therefore arrived at the UI as the
absence of frames - which the surface rendered with copy that explicitly reassures the
user that nothing is hidden and the materializer merely has not painted yet.

The second half is subtler and is the part worth remembering. The scrubber *did* have an
index-failure notice: `replayRefreshFailed`, "Refresh unavailable · retaining stored
frames". That string is correct for the failure it was written for - a 60s poll that
fails after frames are already held. Reused for a cold index failure it becomes a
different false claim: it asserts retention of stored frames when nothing was ever
admitted. Honest degradation is not one string per subsystem; it is one string per
*state*, and "failed while holding data" and "failed holding nothing" are two states.

Both halves were found by an independent read-only audit of an otherwise finished,
CI-green change, not by the reviewer of the original defect and not by the tests: every
existing case satisfied the cheaper conditions, so nothing was red. The cost of the
repair was 68 lines. The cost of shipping it would have been a surface that tells a
subscriber their session is empty when the truth is that the terminal could not read.
