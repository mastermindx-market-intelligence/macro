---
workstream: RUNNER-FLEET-RESILIENCE
checkpoint_kind: CHECKPOINTED_CONTINUATION
mission_complete: false
checkpoint_date: 2026-09-21
skillpack_repo: mastermindx-market-intelligence/Mastermind
skillpack_sha: 4ca1b97e65de9d4ba8c868b9d708fb7620a8a76f
agentos_repo: mastermindx-market-intelligence/macro
agentos_base_sha: 7c6e35163c9f67087ffe174a7ab3810f47ce6a45
intended_resume_surface: fresh Sol session
---

# M2 storage reclaim + Samsung migration checkpoint

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION  
MISSION_COMPLETE: false

## Mission

Recover durable free space and reduce storage/resource amplification on the M2 without deleting
canonical work, active evidence, or unresolved source state. Chairman-authorized current storage
intent:

1. move the non-Mastermind Personal media and WeChat archive from the M2 Mastermind SSD to the
   Samsung SSD mounted as `/Volumes/Worktrees`;
2. continue safe cleanup of stale/offloaded/quarantine/proof material on `/Volumes/Mastermind`;
3. **do not touch the Windows D-drive backup yet** — Chairman will review it separately;
4. preserve M1 Theta/options availability; any M2 Theta copy is secondary recovery only, never a
   normal-operation dependency.

This continuation belongs under existing `WS-RUNNER-FLEET-RESILIENCE`; do not create a second
storage/runner lifecycle or scheduler.

## Verified current state at checkpoint

### M2 Mastermind volume

Readback on 2026-09-21:

- `/Volumes/Mastermind`: 3.6 TiB filesystem, about 3.0 TiB used, **633 GiB free, 84% used**.
- Earlier in this work the same APFS container was 95.5% used with only ~181 GiB unallocated.
- This proves substantial reclaim occurred before this checkpoint, but the full parent storage
  mission is not complete.

Known current path state:

- `/Volumes/Mastermind/Personal`: **PRESENT**.
- `/Volumes/Mastermind/Offloaded/WeChat`: **PRESENT**.
- `/Volumes/Mastermind/Offloaded/Temp-quarantine-20260914`: **ABSENT**.
  It was previously measured at ~146 GiB; do not redo this cleanup.
- `/Volumes/Mastermind/Offloaded/mb-20260917`: **PRESENT**.
- `/Volumes/Mastermind/ops/ubuntu-native-migration-20260916/d-drive-files-20260916.tar.zst`:
  **PRESENT / HOLD — DO NOT TOUCH**. Earlier measured at about 63 GiB.

### Samsung SSD mounted as Worktrees

Current readback:

- `/Volumes/Worktrees`: 931 GiB filesystem, about 589 GiB used, **342 GiB free, 64% used**.
- Existing destination directories:
  - `/Volumes/Worktrees/Documents/Personal Media`
  - `/Volumes/Worktrees/Documents/WeChat`

The media migration is **partial and idle**, not complete:

| Dataset | Source | Source size | Current Samsung target | Target size | State |
|---|---|---:|---|---:|---|
| Personal | `/Volumes/Mastermind/Personal` | 340,403,608 KiB (~324.6 GiB) | `/Volumes/Worktrees/Documents/Personal Media` | 21,257,472 KiB (~20.3 GiB) | PARTIAL |
| WeChat | `/Volumes/Mastermind/Offloaded/WeChat` | 134,782,156 KiB (~128.5 GiB) | `/Volumes/Worktrees/Documents/WeChat` | 5,597,056 KiB (~5.3 GiB) | PARTIAL |

No active `rsync`, `ditto`, or copy process for these paths was observed at checkpoint.

Remaining source bytes are about **427.6 GiB**, while the Samsung has only about
342 GiB free. Therefore the Samsung currently **cannot finish both copies**. Before resuming both,
reclaim or relocate enough Samsung-resident data to provide at least ~428 GiB for remaining payload
plus safety margin. Prefer **>=500 GiB free** before the combined continuation.

File counts are not a reliable equality check on this NTFS-labelled Samsung target because macOS may
create AppleDouble `._*` metadata sidecars. Verify content by source-relative payload files,
byte totals and/or hashes/manifests rather than raw file count alone.

## Earlier measured reclaim candidates — revalidate before deletion

These were measured during the same storage audit and are useful priority candidates, but their
current existence/size must be re-read before any destructive action:

- `Offloaded/mb-20260917`: ~102 GiB (still PRESENT at checkpoint).
- `Offloaded/Sol-runs`: ~74 GiB.
- `h0-prestage-20260916`: ~65 GiB.
- `Offloaded/Codex`: ~44 GiB.
- `Offloaded/Build-runners`: ~29 GiB.
- `transfers`: ~29 GiB.
- assorted M1/M2 cleanup generations, proof checkouts, project archives and old quarantines.

The volume also has very high metadata amplification (earlier filesystem census around 50 million
in-use entries) from worktrees, pytest-style temp forests, agent workspaces, proof/evidence bundles
and repeated source checkouts. Avoid another broad recursive `du` wave on the whole volume: it
materially increased M2 I/O/load during the audit. Use bounded, one-namespace-at-a-time reads.

## Theta/options storage facts that constrain cleanup

Verified during this parent investigation:

- ThetaTerminal is on the M1 and listens locally on ports 25503/25520.
- The actual data-bearing Theta EOD tree measured about 61 GiB at
  `/Volumes/STORAGE/macro-data/thetadata_eod`.
- The logical `~/theta-ops-wt/data/thetadata_eod` path resolves through
  `~/flow-ops-wt/data/thetadata_eod` and contained only manifest/control metadata during the audit.
  Do **not** treat that tiny logical tree as the full historical store.
- An R2 off-host copy exists and had a zero-failure sync receipt in the audit.
- M2/Samsung storage may become a verified secondary recovery replica later, but M1 production must
  not depend on the M2 or the 10GbE network path for normal options operation.
- Existing Runner Fleet law still rejects generic M1 `macstudio` CI. Only the bounded
  `theta-m1` `collect_tail` concept remains eligible after its W4 gates.

## Exact continuation order

1. **Audit Samsung capacity only far enough to reclaim target headroom.**
   Preserve unknown/valuable Samsung contents; do not blind-delete. Reach preferably >=500 GiB free
   before attempting to finish both Personal + WeChat copies.
2. **Resume into the existing destination directories** rather than creating another copy tree.
   Use a resumable one-way transfer and preserve source until verification.
3. **Verify destination completeness** using payload-relative path/size and hashes or a manifest.
   Do not infer success from destination existence or raw file count.
4. Only after verified copy success, remove the corresponding source tree from
   `/Volumes/Mastermind`, then re-read free space.
5. Continue bounded reclaim of current stale/offloaded generations, starting with the large candidates
   above. For every candidate: prove no active process/source custody/effect uncertainty before delete.
6. **Do not delete or relocate the Windows D-drive archive.**
7. Stop broad storage scans if they begin materially loading M2; switch to targeted namespace reads.
8. After Mastermind storage is comfortably below the high-water mark (target <=75% used, preferably
   >=1 TiB free), design/prove the M1 -> M2 Theta secondary replica without moving the live store.

## DO_NOT_REDO

- Do not delete either Personal or WeChat source yet; Samsung copies are incomplete.
- Do not restart the combined Personal+WeChat transfer before resolving Samsung free-space shortfall.
- Do not recreate `Temp-quarantine-20260914`; it is already absent.
- Do not touch `d-drive-files-20260916.tar.zst` until Chairman explicitly reviews it.
- Do not repeat a whole-volume recursive accounting scan merely to regenerate a prettier storage pie
  chart; the prior audit already proved metadata amplification and those scans materially loaded M2.
- Do not move live ThetaTerminal/Theta EOD operation to M2 or make options depend on the M2 network.
- Do not restore generic M1 CI merely because M1 has spare momentary compute; current
  `WS-RUNNER-FLEET-RESILIENCE` law still forbids it.

## Return point / highest-authority sources

- Procedure: `mastermindx-market-intelligence/Mastermind` protected master
  `4ca1b97e65de9d4ba8c868b9d708fb7620a8a76f`.
- Agent OS workstream base:
  `mastermindx-market-intelligence/macro@7c6e35163c9f67087ffe174a7ab3810f47ce6a45`,
  `agentos/workstreams/WS-RUNNER-FLEET-RESILIENCE.md`.
- This handoff is a continuation checkpoint only; it does not mark W4/W5 or the parent mission done.
