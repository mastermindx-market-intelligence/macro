---
key: VPS-PULL-CLONE-GROWS-ONE-92MB-PACK-PER-SITE-RENDER
claim: >
  The /opt/macro pull clone on 146.190.142.17 grows mainly by one pack per full-site render
  commit on main ('engine-render: regime recompute + re-render', 'render: site re-render' and
  full 'engine: regime update' commits, each rewriting 3,500-4,700 files). Most of these packs
  are about 92 MB. There were 13 such commits on 2026-10-18 UTC, and that day's packs totalled
  1.4 GB. Nearly all of that growth is reclaimable without loss: after
  'reflog expire --expire-unreachable=now --all', a consolidation over every ref, reflog and
  the index took the store from 263 packs / 42.5 GiB to 3 packs / 6.78 GiB. 99.92% of the
  1,174,134 dropped objects belong to 337 commits that are all ancestors of GitHub main.
  The .git/shallow line count is not a fetch-mode signal: 'git prune' rewrites it to the
  boundaries that are still reachable (1,839 -> 678 lines across the 2026-10-19 swap, with no
  fetch in between).
kind: runtime
verified_at: 2026-10-19
verified_by: >
  On 146.190.142.17, 2026-10-19:
  (1) the mtime/size list of the 263 pre-swap packs (10-18: 19 packs, 1418.1 MB; nine of them
  91.5-97.9 MB, each within 5 minutes of a full-site render commit on main);
  (2) 'git log origin/main --name-only' over 2026-10-18 UTC, counting commits that touch
  300+ paths;
  (3) a census of the dropped set (old-pack objects minus the consolidated pack). Each
  dropped commit was checked for membership in 'git rev-list origin/main' from a full local
  clone, and for presence through 'gh api repos/mastermindx-market-intelligence/macro/commits/<sha>';
  (4) wc -l .git/shallow before the swap and in swap/shallow.after, captured under the
  updater lock after prune-packed and 'prune --expire=2.weeks.ago'.
  A local fixture confirmed the shallow rule: depth-1 fetches, then reflog expiry, then
  'git prune' took .git/shallow from 5 lines to 1, and prune alone with reflogs still pinning
  left it at 4 of 4.
scope:
  - macro
  - "VPS /opt/macro (146.190.142.17 production pull clone)"
  - app/deploy/update.sh
  - app/deploy/macro-git-store-maintenance.sh
  - WS:MARKET-OS
confidence: verified
type: discovery
status: active
workstream: MARKET-OS
summary: >
  On 2026-10-19 the droplet's root disk was full again: 746 MiB free, with 41 GiB in
  /opt/macro/.git. The store was consolidated with scratch on /mnt/terminal_storage (see
  DSC:PACK-OBJECTS-OFF-FILESYSTEM-NEEDS-GIT-OBJECT-DIRECTORY) and swapped in under the updater
  lock, which was held for 1 min 55 s. Root went from 746 MiB to 37 GiB free (53% used) and
  .git from 41G to 7.4G. The pull, macro-api and the site stayed up.
  This record pins three facts for the next session.
  First, growth tracks the full-site render commits, not pull frequency. Most 3-minute
  pulls fetch a few small data commits. A full-site commit rewrites about 3,800 site files, and
  its thin pack, completed by index-pack --fix-thin, usually lands as one ~92 MB pack. On
  2026-10-18, 10 of the 13 full-site commits matched packs of that size (two of them shared one
  199 MB pack), and two landed as ~30 MB packs. That day came to 1.4 GB, in line with the
  0.94 GiB/day average measured in
  DSC:VPS-ROOT-REFILLED-IN-42-DAYS-AND-REPACK-IS-NOW-DISK-BLOCKED.
  Second, nothing reclaimed was unique. The 337 dropped commits (2026-09-19 to 2026-10-12,
  mostly render-sync, data, earnings-wire and engine automation) are behind the shallow
  boundary and are all ancestors of GitHub main. The 893 remaining objects (97 blobs and 796
  trees, likely fix-thin delta bases) are referenced by no dropped commit and are kept at
  /mnt/terminal_storage/recovery/macro-git-orphans-20261019.git.
  Third, this corrects one piece of evidence in the 2026-10-18 record. Its correction (2)
  reads the 9,020 -> 1,839 fall in .git/shallow as "the fingerprint of depth-one acquisition
  having STOPPED". That reading does not hold: prune drops shallow entries for commits that
  are no longer reachable, so the September reclaim alone explains the fall. The conclusion
  itself still stands on the grep of /usr/local/bin/macro-update, which has no 'fetch --depth'.
evidence:
  - "Pre-swap pack list, 2026-10-18 UTC: 19 packs totalling 1418.1 MB. The ~92 MB packs at 01:48, 03:33, 07:30, 07:54, 09:30, 10:54, 12:30, 14:00 and 19:00 each follow a full-site render commit on main by 2-5 minutes (e.g. 52dbcf8abe8d engine-render at 10:51:14Z -> pack af635fa290 at 10:54:25Z). The 199 MB pack at 06:33 covers two (58d9e2a38dec engine-render 06:28Z + e35e04468075 regime update, 4,185 paths, 06:31Z). e113ed4060d5 (00:20Z) and 77fa41e64054 (04:58Z) landed as 30.7 MB and 31.3 MB packs. The 227 MB pack at 08:15 follows no full-site commit"
  - "git log origin/main --since=2026-10-18T00:00Z --until=2026-10-19T00:00Z --name-only: 13 dashboard-bot full-site commits touching 3,563-4,654 paths each (8 engine-render, 4 'render: site re-render', 1 'engine: regime update'). The others were two earnings-wire commits of 1,018 paths (3.5 MB and 3.3 MB packs) and one 308-path regime update. Every other commit that day touched fewer than 300 paths"
  - "Swap log ($M=/mnt/terminal_storage/macro-git-maint-20261019/swap/log): locked 08:51:49Z with root free 3,286,432 KiB; post-snapshot objects 4,265, rescue 0; retired 263 packs; fsck1 ok; consolidated pack installed; fsck2 ok with the alternates bridge removed; unlocked 08:53:44Z with root free 37,988,904 KiB"
  - "count-objects -vH after: packs 3, size-pack 6.78 GiB, count 6,357 loose / 569 MiB, garbage 0. Before: packs 263, size-pack 42.53 GiB, 28,756 loose / 2.42 GiB. df -h /: 77G 41G 37G 53%"
  - "Dropped-set census ($M/dropset): 1,174,134 objects in the old packs and not the new one. 1,173,241 are reachable from 337 commits, all of them ancestors of GitHub origin/main (0 not on main). The 893 others are preserved in recovery/macro-git-orphans-20261019.git as pack-90078f00d2dd (14.2 MB, .keep), and its object list diffs empty against the orphan list"
  - "The 337 became unreachable through 'git reflog expire --expire-unreachable=now --all', run under the updater lock before the consolidation. HEAD's reflog now starts at 2026-10-13T00:24Z and has 888 entries"
  - "wc -l .git/shallow: 1,839 before the swap, 678 in swap/shallow.after. The only writers inside the lock were prune-packed and 'prune --expire=2.weeks.ago', and no fetch ran. git prune calls prune_shallow() when the repository is shallow"
  - "Fixture (git 2.46, macOS): a clone at depth 1 followed by four depth-1 fetches with reset --hard left 5 shallow lines. reflog expire --expire-unreachable=now plus prune --expire=now left 1. A second fixture without the reflog expiry stayed at 4 lines out of 4 after prune"
falsifier: >
  (a) On 146.190.142.17, after the nightly maintenance job is live, list the packs
  ('ls -l --time-style=+%FT%TZ /opt/macro/.git/objects/pack/*.pack') against
  'git log origin/main --name-only' for the same day. If most new packs larger than 50 MB do
  not sit within minutes of a commit touching 3,000+ paths, the render attribution is wrong.
  (b) Take any sha from $M/dropset/drop-commits-meta.txt and run
  'git merge-base --is-ancestor <sha> origin/main' in a full clone. A non-zero exit for any of
  the 337 means the "nothing unique was dropped" claim is wrong.
  (c) In a shallow fixture, run depth-1 fetches with reset --hard, then reflog expire and
  'git prune --expire=now'. If .git/shallow does not shrink, the prune_shallow reading is wrong
  and the 2026-10-18 record's fingerprint stands.
so_what: >
  Plan root-disk capacity on this host from the render cadence (usually about 92 MB per
  full-site render, about 13 a day), not from the 3-minute pull count. More renders per day means faster
  growth whatever the pull interval.
  The bounded fix is the nightly macro-git-store-maintenance job
  (DEC:VPS-MACRO-GIT-STORE-BOUNDED-BY-NIGHTLY-CRUFT-REPACK). A one-off reclaim on this clone
  is safe once reflogs are expired, because what it drops is already on GitHub main. Still run
  the census before deleting anything: the 893 objects were not from any dropped commit.
  Do not use .git/shallow line counts to argue about fetch depth. Prune rewrites the file, so
  only a grep of the installed updater (or a trace of its fetch) shows whether depth is in use.
related:
  - "DSC:VPS-ROOT-REFILLED-IN-42-DAYS-AND-REPACK-IS-NOW-DISK-BLOCKED"
  - "DSC:VPS-PULL-CLONE-REFLOG-PINS-PACK-DUPLICATION"
  - "DSC:PACK-OBJECTS-OFF-FILESYSTEM-NEEDS-GIT-OBJECT-DIRECTORY"
  - "DSC:SMALL-FETCH-SKIPS-PACKED-OBJECTS-SO-A-PACK-SWAP-NEEDS-A-RESCUE"
  - "DEC:VPS-MACRO-GIT-STORE-BOUNDED-BY-NIGHTLY-CRUFT-REPACK"
  - "WS:MARKET-OS"
---

On 2026-10-19 the production droplet's root filesystem was full for the third time. The
`/opt/macro` pull clone held 41 GiB in 263 packs. It was consolidated with scratch space on
the separate `/mnt/terminal_storage` volume and swapped in under the updater lock. Root went
from 746 MiB to 37 GiB free, and the 3-minute pull, macro-api and the site stayed up.

The growth comes from the site renders. Most 3-minute pulls bring a few small data commits.
A full-site render commit rewrites about 3,800 files and usually lands as one pack of about
92 MB. With about 13 of them a day, that accounts for the roughly 1 GiB a day the disk has
been losing since September.

None of what the consolidation dropped was unique. Expiring unreachable reflog entries
released 337 automation commits from behind the shallow boundary, and every one of them is
on GitHub `main`. The 893 objects that no dropped commit references were kept in a small
recovery repository rather than deleted.

The swap also corrects one piece of evidence in the 2026-10-18 record. That record read the
fall in `.git/shallow` from 9,020 to 1,839 lines as proof that depth-one fetching had
stopped. `git prune` rewrites that file to the boundaries that are still reachable, and on
this swap it took the file from 1,839 to 678 lines with no fetch involved. The conclusion
still holds, but it rests on the grep of the installed updater, not on the line count.
