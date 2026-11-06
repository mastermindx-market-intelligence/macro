---
key: M1-STORAGE-GUARD-HELP-MUTATES-20261003
claim: >
  M1 storage_floor_guard.py at SHA256
  71f7f7c8d289e6750a580f39ffe5679f0938e2e3c0c491dcb55c6a3a2cf18271
  does not dispatch --help before remediation. The observed 2026-10-03 help
  invocation started ssd_worktree_reaper.py --apply --json after a floor breach.
falsifier: >
  A reproducible source/control-flow analysis of these exact installed bytes of
  storage_floor_guard.py and ssd_worktree_reaper.py proving that --help exits
  before guard logic, or an independently authenticated incident record
  disproving the recorded parent/child launch attribution. A later fixed
  version does not falsify this version-bound observation.
so_what: >
  Inspect unknown maintenance programs statically before invoking even --help.
  Reconcile this exact interrupted apply through its existing receipt and ledger
  surfaces. Termination and an absent final report do not prove that no deletion
  occurred. Do not rerun remediation to reconstruct evidence.
kind: runtime
verified_at: 2026-10-03
verified_by: >
  M1 guard source and log, floor-guard-last-kick epoch 1791062123.516345,
  and observed process chain at 2026-10-03T21:15:23.516345Z:
  remote zsh 51055 -> storage_floor_guard.py --help 51063 ->
  ssd_worktree_reaper.py --apply --json 51064. The owned chain received TERM
  about 37 seconds later and the subsequent process census was empty.
  Reaper SHA256 was
  9967bed4b8abbc62a2342c7745fda2b996d81a0856b2ffc40cee2a1eb2de6f0d.
  No completed incident report or action-ledger entry was found.
scope: [macro, m1, storage-cleanup]
confidence: verified
---

The invocation was an agent inspection mistake. Launch is proven; deletion
effect remains **EFFECT_UNKNOWN**. The existing `sweep.py` process 90116 was
preserved. No cleanup retry, disk-floor change, or deletion was commissioned.

The canonical evidence surfaces are M1
`~/.local/state/mastermind/storage-cleanup/ssd-reaper-<epoch>.json`,
`ssd-reaper-ledger.jsonl`, and policy-root `.storage-receipts/*.json` beneath
`/Volumes/STORAGE/agent-workspaces`. Source inspection shows final reports are
written after processing; their absence cannot establish a no-effect result.
A complete, incident-bound action receipt could resolve the effect uncertainty
without changing the proven help-path defect.

The separate R2 raw-event retention audit is unrelated to this local filesystem
incident. It must not be used as deletion evidence or as a new retention policy.
