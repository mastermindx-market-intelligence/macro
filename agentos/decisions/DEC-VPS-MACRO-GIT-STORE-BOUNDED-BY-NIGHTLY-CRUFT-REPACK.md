---
key: VPS-MACRO-GIT-STORE-BOUNDED-BY-NIGHTLY-CRUFT-REPACK
question: >
  The /opt/macro production pull clone on 146.190.142.17 keeps running the 77 GiB root disk
  out of space: auto-gc failed on a near-full disk on 2026-08-28, a hand reclaim was needed on
  2026-09-06, and the disk was full again on 2026-10-19. Each full-site render commit lands as a pack of
  about 92 MB, gc.auto has been 0 by hand since late August, and nothing else consolidates the
  store. What keeps the store bounded from now on, without risking the 3-minute pull, macro-api
  or the shallow-history rules of MO-A-F04?
answer: >
  A nightly, explicit, fail-closed maintenance job replaces auto-gc, and journald gets a cap.
  update.sh installs and self-arms both on its next tick, the same way it handles the other
  units, and setup.sh installs them on a fresh host.
  (1) macro-git-store-maintenance.timer fires at 02:40 UTC (RandomizedDelaySec=300,
  Persistent=true) and starts a oneshot service.
  (2) Under /var/lock/macro-update.lock the job runs
  'reflog expire --expire-unreachable=now --expire=90.days.ago --all' and
  'pack-refs --all --prune'. Both take seconds; a pull tick that meets the lock skips, as it
  does behind a slow tick.
  (3) It deletes tmp_pack_* / tmp_idx_* / tmp_rev_* older than 6 hours, which a killed repack
  leaves behind.
  (4) Gates. If free space on the object filesystem is below the store size plus 3 GiB, the
  unit fails (exit 1) and writes nothing. If the lock is busy or MemAvailable is low, it
  defers (exit 75, treated as success) and writes nothing.
  (5) Outside the lock it runs 'git repack -d -l --cruft --cruft-expiration=2.weeks.ago' with
  one thread and a 128 MB window, at nice 19 and idle I/O, inside a unit capped at
  CPUQuota=80%, MemoryHigh=640M, MemoryMax=900M and a 6-hour runtime. Recently unreachable
  objects keep a two-week grace period in a cruft pack, as 'git gc' does.
  (6) Under the lock again, 'git prune --expire=2.weeks.ago' removes loose objects past the
  same grace. If the lock stays busy, the prune is skipped for that night.
  gc.auto stays 0, so the pull never repacks by itself. The job never fetches, deepens,
  unshallows or edits .git/shallow.
  journald: /etc/systemd/journald.conf.d/10-macro-vps-cap.conf sets SystemMaxUse=300M,
  SystemKeepFree=2G and SystemMaxFileSize=50M. Before this, journald was uncapped and used
  790 MB of the same root disk.
  When the store has already outgrown the gate, the job refuses, and recovery is the hand
  procedure in app/deploy/README.md: consolidate off-root, then swap under the lock with a
  rescue step.
rationale: >
  The growth is inherent to how the site is published, not to how the pull fetches. A
  full-site render rewrites about 3,800 files, so its pack is large however it is fetched,
  and about 13 of them land a day (DSC:VPS-PULL-CLONE-GROWS-ONE-92MB-PACK-PER-SITE-RENDER).
  Almost all of it is reclaimable once unreachable reflog entries expire: the 2026-10-19 swap
  took 263 packs / 42.5 GiB to 3 / 6.78 GiB, and every dropped commit was on GitHub main.
  Doing that every night keeps the store near its live size, so a nightly repack writes about
  7 GiB, not 40. That is well inside the 37 GiB now free, and the store-plus-3-GiB gate keeps
  it from ever starting a repack that could end in ENOSPC.
  gc.auto=0 was set by hand after auto-gc failed on a nearly full disk (gc.log
  "fatal: failed to run repack", 2026-08-28), and no script ever set it. That reason still
  holds: auto-gc runs inside the pull, cannot be gated on space, and fails part-way on a full
  disk. A separate unit can be gated, deferred, resource-capped and observed.
  The 2026-09-06 fix proposed a daily cron line that was never installed (see
  DSC:VPS-ROOT-REFILLED-IN-42-DAYS-AND-REPACK-IS-NOW-DISK-BLOCKED). Installing from update.sh
  closes that gap, because the next pull after merge arms the timer without a hand step.
alternatives:
  - option: Re-enable gc.auto
    why_not: auto-gc repacks detached from inside the 3-minute pull, with no space or memory gate. That is what failed on 2026-08-28 and left gc.log behind, and a repack that hits ENOSPC can wedge the pull
  - option: Re-clone /opt/macro at depth 1 in a quiet window
    why_not: changes the clone's depth, which MO-A-F04 forbids, swaps out the live checkout under macro-api, and only resets the clock, because the render packs start piling up again the next day
  - option: Change update.sh's fetch flags (depth, filter, refspec) so the pull writes smaller packs
    why_not: the size comes from render commits that rewrite about 3,800 files. Any fetch of those commits brings their trees and blobs, and depth flags are ruled out by MO-A-F04
  - option: Move /opt/macro/.git onto /mnt/terminal_storage
    why_not: ties the Macro pull to the Terminal data volume and its bind mount, and still grows without bound. Bounding the store is needed either way
  - option: A plain 'repack -a -d' or 'git gc --prune=now' nightly
    why_not: drops recently unreachable objects with no grace. The PR's negative control shows a plain 'repack -a -d' loses a fresh object that a cruft repack keeps
affects:
  - "WS:MARKET-OS"
  - app/deploy/update.sh
  - app/deploy/setup.sh
  - app/deploy/macro-git-store-maintenance.sh
  - app/deploy/macro-git-store-maintenance.service
  - app/deploy/macro-git-store-maintenance.timer
  - app/deploy/journald-macro-vps.conf
  - app/deploy/README.md
  - "VPS /opt/macro (146.190.142.17)"
evidence:
  - "Macro PR #9666 (claude/ssd-vps-git-store-bound-d714bd8de4409d68): the units, script, journald drop-in, update.sh/setup.sh install, README recovery recipe, and tests/test_deploy_git_store_maintenance.py in a new deploy-git-store-maintenance CI job"
  - "Functional tests on a shallow fixture that mirrors the pull: consolidation keeps HEAD, .git/shallow, connectivity and a historical commit's bytes, and the next pull works; the grace period holds where plain 'repack -a -d' loses the fresh object; stale temporary packs go and fresh ones stay; a space refusal writes nothing; the job defers on a held lock and on low memory"
  - "Production, 2026-10-19: root free 746 MiB -> 37 GiB after the off-root consolidation and swap (lock held 1 min 55 s, rescue 0 of 4,265, fsck ok twice). Store 7.4G, so a nightly repack needs about 10.4 GiB under the gate"
  - "gc.auto history: 'git grep gc.auto origin/main' finds only CI runner-host cache scripts (ops/runner-host/pc/) and the local worktree hook (.claude/hooks/worktree_create_sparse.py) setting it; nothing in app/deploy or anything run on the droplet does. .git/gc.log read 'fatal: failed to run repack', dated 2026-08-28, and the setting was already present at the 2026-09-06 reclaim"
  - "journald before the cap: /var/log/journal 790M with no SystemMaxUse configured (2026-10-19 read-only survey)"
confidence: high
reversibility: easy
decided_by: claude-opus (session 2036a7c3, chairman-assigned 2026-10-19 VPS root-disk remediation)
decided_at: 2026-10-19
---

The Macro droplet's pull clone grows by about a gigabyte a day because every full-site render
lands as a large pack, and nothing had been consolidating them since auto-gc was turned off by
hand in August. This decision puts a nightly job in auto-gc's place. It runs at 02:40 UTC,
repacks only when the disk has room for the whole result plus 3 GiB, keeps recently
unreachable objects for two weeks, and takes the updater lock only for its few quick steps.
journald gets a 300 MB cap on the same disk.

Auto-gc stays off, the clone stays shallow at the depth MO-A-F04 fixes, and the 3-minute pull
is unchanged. Once the PR is merged, the next pull tick installs and arms the timer. If the
store ever outgrows the gate again, the job refuses and logs it, and the README's off-root
recovery recipe is the way back.
