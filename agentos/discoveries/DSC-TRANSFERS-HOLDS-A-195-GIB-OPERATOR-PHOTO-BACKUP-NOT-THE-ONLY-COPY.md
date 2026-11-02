---
key: TRANSFERS-HOLDS-A-195-GIB-OPERATOR-PHOTO-BACKUP-NOT-THE-ONLY-COPY
claim: >
  `/Volumes/Mastermind/transfers/runner-fleet-resilience-worktrees-photoslib-20260924.tar` is
  **195.28 GiB in one file** containing `Photos Library.photoslibrary/` with `originals/`,
  `database/`, `resources/` and `scopes/` — the operator's personal photo library, sitting among
  70 entries of agent scratch under a name whose first three words are fleet-infrastructure
  vocabulary (`runner-fleet-resilience-worktrees-…`). **It is never deletable**, and
  `/Volumes/Mastermind/transfers` is REPORT-ONLY for every automated path, joining
  `/Volumes/Worktrees`: any sweeper deleting "stale transfer artifacts older than 7 days"
  destroys it. **It is a BACKUP, not the only copy.** The live library is
  `/Volumes/Worktrees/Documents/Photos Library.photoslibrary` — **247 GB**, with `database/`,
  `external/`, `internal/`, `originals/`, `private/`, `resources/`, `scopes/` all present — and
  `PREFLIGHT.txt` for the operation the tar is named after lists that path as `protected=`,
  deliberately excluded alongside `Pictures` and `WeChat`; that operation's actual candidates
  were `Courses` (`COPIED_AND_HASH_VERIFIED`, 655 files, 2.68 MB), `Documents New` and
  `Jewelry`, the latter two halted `HELD_SOURCE_RACE|no_source_removal|partial_target_cleaned`.
  **The larger hazard is that neither copy is on a backup device.** Both the 247 GB live library
  and its 195.28 GiB tar sit on volumes the fleet writes to and sweeps — the live one on
  `/Volumes/Worktrees` (87% full, exFAT, also holding 9 fleet worktrees and the
  operator-protected AdsPower payload, see
  `DSC:A-SECOND-EXTERNAL-VOLUME-HOSTS-FLEET-WORKTREES-UNGOVERNED`), the tar on
  `/Volumes/Mastermind` among PR proof clones. The pre-transfer manifests beside `PREFLIGHT.txt`
  enumerate private personal filenames and must not be reproduced in any report.
falsifier: >
  `cat '/Volumes/Mastermind/Offloaded/runner-fleet-resilience-worktrees-reclaim-20260922-sol-001/PREFLIGHT.txt'`
  prints `protected=/Volumes/Worktrees/Documents/Photos Library.photoslibrary` with
  `source_volume=/Volumes/Worktrees`, `target_volume=/Volumes/Mastermind`, three `candidate=`
  lines and two `candidate_status=…|HELD_SOURCE_RACE|no_source_removal` lines.
  `ls -d '/Volumes/Worktrees/Documents/Photos Library.photoslibrary'/*/` lists the seven
  subdirectories and `du -sh` on it reports ~247 GB. `tar -tf` on the tar's leading members shows
  `Photos Library.photoslibrary/`. `find /Volumes/Mastermind/transfers -maxdepth 1 -type f`
  yields 14 entries / 195.28 GiB against 57 dirs / 37.97 GiB. Disproved if the live library is
  removed or relocated (then the tar IS the only copy and urgency rises), if a copy is confirmed
  on a genuine backup device (then neither location is load-bearing), or if `PREFLIGHT.txt` is
  superseded by a later receipt showing the protected path was moved after all.
so_what: >
  Four things change. (1) **`/Volumes/Mastermind/transfers` is REPORT-ONLY** — no sweeper,
  retention rule, age gate or `du`-driven reclaim may target it, and an operator asked to "clean
  transfers" must be shown this file first. (2) **Do not escalate this as an only-copy
  emergency.** Relocating a redundant backup is housekeeping; reporting it as an irreplaceable
  original spends operator attention the real gaps need. The actionable request is narrower and
  truer: **neither copy of the photo library is on a backup device**, and one of them shares an
  87%-full exFAT volume with fleet worktrees. (3) **A search reports its REACH, never a
  machine-wide absence.** The retracted claim came from searching `~/Pictures` and
  `/Volumes/Mastermind` at depth ≤ 3 and reporting the result as "nowhere on this machine" — the
  omitted volume was the one already documented as holding the operator's `Documents`. Enumerate
  mounted volumes (`mount`/`df`) and state which were searched before any absence claim; this is
  the sixth instance of a positional question standing in for a semantic one in one triage
  (`research/WORKTREE_GC_POLICY.md`, and the account-local
  `storage-instruments-fail-by-asking-a-positional-question`). (4) **Read a reclaim directory's
  `PREFLIGHT.txt` and `*-copy-receipt.json` before inferring anything from its name.** They name
  source/target volumes, every protected path, each candidate and its halt status, for the cost
  of one `cat` — and they revealed that two candidates halted with `no_source_removal`, so source
  data that operation meant to remove is still in place.
kind: landmine
verified_at: 2026-09-28
verified_by: >
  PREFLIGHT.txt and Courses-appledouble-copy-receipt.json in
  /Volumes/Mastermind/Offloaded/runner-fleet-resilience-worktrees-reclaim-20260922-sol-001/
  (protected paths, candidates, HELD_SOURCE_RACE statuses, COPIED_AND_HASH_VERIFIED);
  `ls -ld` + depth-1 `ls -d */` + `du -sh` on /Volumes/Worktrees/Documents/Photos
  Library.photoslibrary (247 GB, 7 subdirs); `tar -tf` on the tar's leading members;
  `find /Volumes/Mastermind/transfers -maxdepth 1 -type f`/-type d (14 files 195.28 GiB vs 57
  dirs 37.97 GiB, 233.25 GiB total); `df -h` on both volumes;
  research/WORKTREE_GC_POLICY.md §"`transfers` — the seventh pool"
scope:
  - macro
  - research/WORKTREE_GC_POLICY.md
  - scripts/worktree_gc.py
  - config/worktree_gc.json
confidence: verified
---
