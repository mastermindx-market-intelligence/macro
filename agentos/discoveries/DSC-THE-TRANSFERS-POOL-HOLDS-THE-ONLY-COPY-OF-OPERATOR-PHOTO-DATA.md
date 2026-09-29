---
key: THE-TRANSFERS-POOL-HOLDS-THE-ONLY-COPY-OF-OPERATOR-PHOTO-DATA
claim: >
  `/Volumes/Mastermind/transfers/runner-fleet-resilience-worktrees-photoslib-20260924.tar` is
  **195.28 GiB in one file** and contains `Photos Library.photoslibrary/` with `originals/`,
  `database/`, `resources/` and `scopes/` — **the operator's personal photo library**. There is
  no `.photoslibrary` in `~/Pictures` and none anywhere on `/Volumes/Mastermind` at depth ≤ 3,
  so it appears to be the **only copy on this machine's accessible storage** — not a redundant
  backup sitting beside a live library. It must never be deleted, moved, truncated or
  "reclaimed". Three properties make it a landmine rather than a note. (1) **Its name is
  fleet-infrastructure vocabulary** — `runner-fleet-resilience-worktrees-…` — so it reads as
  reclaim residue from a 2026-09-24 worktree operation; the sibling pre-transfer manifests in
  `Offloaded/runner-fleet-resilience-worktrees-reclaim-20260922-sol-001/`
  (`personal-source-manifest-pretransfer.json`,
  `personal-destination-manifest-pretransfer.json`) show that operation moved PERSONAL data, not
  fleet data. Those manifests enumerate private personal filenames and must not be reproduced in
  any report. (2) **Every one of its 70 neighbours is machine residue** — `PR7574_CHECKPOINT_*.json`,
  `HANDOFF_CHINA_HEATMAP_*.md`, `pr884_*` review packets, `r15green-*`/`r18-astra-*` round
  scratch, `executive-os-convergence-20260918` (28.54 GiB) — so a directory named `transfers`
  whose contents are overwhelmingly agent scratch is the worst possible home for irreplaceable
  personal data, and any sweeper deleting "stale transfer artifacts older than 7 days" destroys
  the library. (3) **It was invisible to the census built to measure that pool.** The census ran
  every instrument this fleet had already repaired (bare-store detection, marker-anywhere
  HUMAN-class screen, origin-partitioned landedness) and still reported **37.97 GiB for a
  233.25 GiB pool**, because it iterated `x.is_dir()`: 57 dirs = 37.97 GiB were seen, 14 files =
  195.28 GiB (**83.7%**) were not. The largest object on the pool was not misjudged or refused —
  it was absent from the instrument's field of view, and the instrument reported a clean number.
falsifier: >
  `ls -l '/Volumes/Mastermind/transfers/runner-fleet-resilience-worktrees-photoslib-20260924.tar'`
  shows ~209.7 GB / 195.28 GiB, mtime 2026-09-24. `tar -tf <tar> | head` lists
  `Photos Library.photoslibrary/` with `originals/`, `database/`, `resources/`, `scopes/`.
  `ls -d ~/Pictures/*.photoslibrary` finds nothing and
  `find /Volumes/Mastermind -maxdepth 3 -name '*.photoslibrary'` returns empty — the
  only-copy claim is disproved the moment either finds a live library, or a copy is confirmed on
  an off-host destination (the destination manifest names one; whether that transfer COMPLETED is
  not established here and is the weakest link in the claim). The invisibility half is reproduced
  by `find /Volumes/Mastermind/transfers -maxdepth 1 -type f` (14 entries, 195.28 GiB) against
  `-type d` (57 entries, 37.97 GiB); disproved if a dir-only iteration ever accounts for the
  pool total.
so_what: >
  Three things change. (1) **`/Volumes/Mastermind/transfers` is REPORT-ONLY for every automated
  path**, joining `/Volumes/Worktrees` — no sweeper, retention rule, age gate or `du`-driven
  reclaim may target it, and an operator asked to "clean transfers" must be shown this file
  first. The correct follow-up is not reclaim but **relocation to a real backup destination**,
  which is an operator act. (2) **Census FILES as well as directories, at every level.** A pool
  measured by directory iteration carries an unstated precondition — that nothing large is stored
  as a file — and this volume violated it by 195 GiB. A census that cannot state its own REACH
  over both entry kinds is not evidence about a pool. (3) **When the largest object in a pool
  carries an infrastructure name, open it before classifying it**: the name described the
  operation that moved the object, never the object's contents, and every neighbour genuinely
  being machine residue is exactly what made the name plausible. Generalizes the pattern in
  `DSC:A-SECOND-EXTERNAL-VOLUME-HOSTS-FLEET-WORKTREES-UNGOVERNED` — a storage instrument's
  blind spot is structural, silent, and reads as a result.
kind: landmine
verified_at: 2026-09-28
verified_by: >
  `find /Volumes/Mastermind/transfers -maxdepth 1 -type f`/-type d with per-entry `stat`/`du -sk`
  (14 files 195.28 GiB vs 57 dirs 37.97 GiB, 71 entries 233.25 GiB total);
  `tar -tf` on the tar's leading members (Photos Library.photoslibrary/ with originals, database,
  resources, scopes); `ls -d ~/Pictures/*.photoslibrary` (none) and
  `find /Volumes/Mastermind -maxdepth 3 -name '*.photoslibrary'` (none); directory listing of
  Offloaded/runner-fleet-resilience-worktrees-reclaim-20260922-sol-001/ (pre-transfer personal
  source and destination manifests present; contents deliberately not reproduced);
  research/WORKTREE_GC_POLICY.md §"`transfers` — the seventh pool"
scope:
  - macro
  - research/WORKTREE_GC_POLICY.md
  - scripts/worktree_gc.py
  - config/worktree_gc.json
confidence: verified
---
