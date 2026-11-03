---
key: PROPHET-RETENTION-SNAPSHOT-FAILURE-CAN-DISCARD-STAGED-WRITES
claim: >
  At Macro head 7444c5ba6add3b21d251087a3dc5960e985d0a69, a failed private-index
  snapshot copy after a late staged write makes retained-capture failure cleanup
  discard the staged preimage while leaving HEAD and working-file bytes unchanged.
falsifier: >
  Run tests/test_turn_watch_capture_retention.py::test_late_staged_preimage_survives_snapshot_failure
  against the exact 7444c5b source with both copy outcomes and both capture/unrelated
  paths; a failure-copy case preserving the exact staged bytes and real index would
  refute this source-specific finding. Passing on the repaired source closes the
  defect rather than falsifying its recorded historical occurrence.
so_what: >
  Review failure cleanup together with the preceding writer race. In retained-capture
  mode, a failure before ref/index installation must not rebuild the real index from
  HEAD; release only the invocation's still-empty owned lock and preserve changed or
  ambiguous lock state through the incumbent lock-identity owner.
kind: landmine
verified_at: 2026-10-19
verified_by: >
  Native four-case test_late_staged_preimage_survives_snapshot_failure RED at
  7444c5ba6add3b21d251087a3dc5960e985d0a69: two failed and two passed;
  https://github.com/mastermindx-market-intelligence/macro/pull/9634#issuecomment-6264253125.
scope:
  - macro
  - prophet-us
  - scripts/ci/options_signal_nightly.sh
  - scripts/ci/turn_watch_capture_retention.py
  - tests/test_turn_watch_capture_retention.py
confidence: verified
---

## Exact finding and repair boundary

The prior capture repair removed destructive working-file preparation and used
`oip_commit_locked_roots`. That protected normal success and ordinary late-staged
refusal, but did not protect their composition with an earlier snapshot-copy
failure. The generic failure branch called `oip_restore_locked_index` before the
retained overlay could validate the late preimage. This erased staging, not the
working-file bytes; no production occurrence is claimed.

The same-PR follow-up adds retained-capture mode to the incumbent non-restoring
failure branch. Broad engine and render-sync cleanup semantics remain unchanged.
There is no second lock, publisher, ref writer, queue, lifecycle or retry owner.
The existing lock identity helper releases only the invocation's still-empty
regular inode. Filled, replaced, symlinked and FIFO lock cases remain fail-closed.

## Discriminating proof

The native test covers late capture and unrelated staged paths, each with a
normal-copy control and an injected private-index copy failure. It verifies HEAD,
working bytes, staged bytes and exact real-index bytes. Four additional cases
verify modified/replaced/symlink/FIFO lock preservation on failure, and a success
case verifies that a writer changing the receipt after the private snapshot keeps
its working bytes while the retained commit/index use the exact accepted blob.

These tests remain under the original retention regression owner in PR #9634.
Author-side probes are not an independent approval. A source repair or passing
fixture test does not establish hosted release, natural producer publication,
authenticated visibility, executable entry or predictive value.
