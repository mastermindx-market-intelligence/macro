---
key: A-PASS-COUNT-RECONCILIATION-CATCHES-A-VANISHED-SUITE
claim: >
  A differential that compares only FAILURE NAMES between a baseline and a returned head cannot
  detect a suite that stopped running. Require the arithmetic
  `baseline_passed + fixed + newly_added == child_passed` and a vanished file, a silently skipped
  test and a renamed test all become visible in one check. Measured 2026-09-25 on Mastermind
  IAC-P1 B2-0: the accepted head `0c0fd718` gave `1959 passed, 2 skipped, 0 failed` against a pinned
  PARENT `87117418` of `9 failed, 1943 passed, 2 skipped`, and `1943 + 9 + 7 = 1959` closes exactly.
  The same run on the lane host reported `1943 passed` while one of the 42 suite files was NOT
  COLLECTED AT ALL - the same pass count as the baseline, reached by a different route. A
  name-only differential would have read that as "no new failures".
falsifier: >
  Take a green differential that compares failure names only, delete one suite file from the child
  invocation, and re-run. If the differential still reports "no new failures, none fixed", it is
  blind to a vanished suite and the pass-count identity is load-bearing. To confirm the identity is
  the thing doing the work, re-run WITH the reconciliation: it must fail with a residual equal to
  the number of tests in the deleted file.
so_what: >
  Any acceptance whose evidence is "no new failures" is incomplete without a count that closes.
  Two independent runs can agree on a pass TOTAL for unrelated reasons - one having fixed nine
  tests and added seven, the other having lost a whole file to a collection error - so the total by
  itself is not evidence either. Publish the identity, not the total: baseline, fixed, added, and
  the residual. A residual of zero is the claim; a non-zero residual names exactly how many tests
  went missing and sends you looking for the file rather than for a regression that is not there.
kind: law
verified_at: 2026-09-25
verified_by: >
  Ran the 42-file dialogue consumer set on one interpreter with a fresh `mktemp -d` temproot at
  Mastermind `87117418` (`9 failed, 1943 passed, 2 skipped`) and at `0c0fd718`
  (`1959 passed, 2 skipped`), comparing sorted FAILED node ids: 0 new, 9 fixed, and the seven new
  tests accounted for. The lane's own gate line for the same commit was
  `4 failed, 1943 passed, 2 skipped` over 41 of 42 files, with
  `tests/test_workspace_agent_return_service.py` uncollectable on that host - the concrete instance
  of a pass total agreeing for the wrong reason.
scope:
  - any RED->GREEN acceptance differential
  - any brief whose CONSUMER_GATE is a pytest summary line
  - cross-host or cross-venv verification
confidence: verified
---

The subtle part is that the pass total looked *reassuring* precisely because it matched. Two runs
reporting `1943 passed` invites the inference that nothing moved, when in one of them nine tests had
been repaired, seven added, and an entire suite file had stopped being collected. Matching totals
are a coincidence to be explained, not a result.
