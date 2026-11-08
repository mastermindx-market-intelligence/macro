---
key: VPS-ROOT-REFILLED-IN-42-DAYS-AND-REPACK-IS-NOW-DISK-BLOCKED
claim: >
  The 2026-09-06 /opt/macro reclaim (100% -> 51%, 38 GiB free) fully reversed in 42 days to
  874 MiB free, and ~100% of the refill is /opt/macro/.git (2.99 GiB -> 42.53 GiB size-pack,
  ~0.9 GiB/day) because the recurrence-prevention cron line was never ratified; the surviving
  mechanism is gc.auto=0 plus reflog pinning ALONE, since the --depth 1 fetch that the
  2026-09-06 record names was removed by the F04 history-preservation patch. The prescribed
  remedy is no longer executable: repack -ad must write a multi-GiB pack beside the 42.53 GiB
  it is replacing, with 874 MiB free - so on this host the sufficient fix now needs an
  operator decision, not a repeat of the September sequence.
kind: landmine
verified_at: 2026-10-18
verified_by: >
  Read-only on 146.190.142.17 2026-10-18: df -h / (77G/76G/874M/99%); du -sh /opt/macro/.git
  (41G); git -C /opt/macro count-objects -vH (packs 263, size-pack 42.53 GiB, in-pack
  2291902, loose 28728/2.42 GiB, garbage 0); wc -l < .git/shallow (1839, vs 9020 on
  2026-09-06); grep -n depth /usr/local/bin/macro-update (single hit, line 263, the
  PROHIBITION comment - no fetch --depth); crontab -l + /etc/cron.d (only the 3-minutely
  macro-update line; no reflog/repack entry); git config gc.auto (0); free -m (available
  2431 MiB, swap 5041/8191 used, load 4.31 on 2 CPUs). Byte census via
  'git rev-list --objects {--all,--all --reflog} | cut -d" " -f1 |
  git cat-file --batch-check="%(objectsize:disk)"' summed.
scope:
  - macro
  - "VPS /opt/macro (146.190.142.17 production pull clone)"
  - app/deploy/update.sh
  - WS:MARKET-OS
confidence: verified
type: discovery
status: active
workstream: MARKET-OS
summary: >
  DSC:VPS-PULL-CLONE-REFLOG-PINS-PACK-DUPLICATION predicted this host would refill and
  re-approach exhaustion within weeks absent its proposed cron. It did, and this record
  carries the measured outcome plus three corrections to that record.
  (1) RECURRENCE CONFIRMED, RATE REFINED: 2026-09-06 left 38 GiB free; 2026-10-18 shows
  874 MiB free - 37.15 GiB consumed in 42 days = 0.884 GiB/day root-wide, against .git
  size-pack growth of 39.54 GiB = 0.941 GiB/day. The two rates matching means essentially
  the entire refill is the git store, not other services. The September estimate of
  1.35 GiB/day was ~50% high.
  (2) THE --depth 1 COMPONENT IS OBSOLETE: the September claim names
  'git fetch --depth 1 -q origin main' every 3 minutes. The installed updater no longer
  does this - 'depth' now occurs once in /usr/local/bin/macro-update, at line 263, as the
  comment forbidding it, and tests/test_deploy_git_history.py is a dedicated suite proving
  the acquisition stanza stays depth-free. Corroboration: .git/shallow fell 9020 -> 1839
  boundary commits instead of climbing. So packs still accumulate with depth removed; the
  cause is gc.auto=0 plus reflog pinning, and removing depth did not slow the refill.
  (3) OBJECT COUNTS OVERSTATE RECLAIMABLE BYTES BY ~13x: September reported '35.6x
  duplication' from counts (87,544 refs-only vs 3,115,777 in-pack). Measured in BYTES on
  2026-10-18 the ratio is 2.78x - refs-reachable 15.30 GiB and reflog-reachable 40.27 GiB
  of 42.53 GiB packed. Consequence: a plain 'git gc --prune=now' frees 2.26 GiB (5%), while
  'reflog expire --expire-unreachable=now --all' first frees >=27.23 GiB (64%). The
  duplicated objects are the small ones, so a count ratio is not a byte promise.
evidence:
  - "df -h / 2026-10-18: '/dev/vda1 77G 76G 874M 99% /' - against '38 GiB free / 51% used' recorded 2026-09-06, i.e. the entire 2026-09-06 reclaim is gone in 42 days"
  - "git -C /opt/macro count-objects -vH 2026-10-18: packs 263, size-pack 42.53 GiB, in-pack 2291902 index entries (1803810 unique), loose 28728 / 2.42 GiB, garbage 0, prune-packable 0 - against 'in-pack 87,544 at 2.99 GiB' immediately after the 2026-09-06 repack"
  - "Byte census 2026-10-18: refs-reachable 644,783 objects = 15.30 GiB; reflog-reachable 1,795,421 objects = 40.27 GiB; 1,803,810 unique packed objects = 42.53 GiB. 99.5% of packed objects are reflog-reachable because every 3-minutely 'reset --hard' writes a reflog entry, so the reflog - not the ref set - is what pins the bytes"
  - "grep -n depth /usr/local/bin/macro-update -> only '263:# Do not add --depth here: depth-one fetches sever the new tip from previously'. app/deploy/update.sh:263-268 gives the reason as breaking 'the native accepts_revision ancestry check even when both commit objects remain present', and the same file is sha256 42d7b3189cf5cd7292719fefe06d27754ac1a27e2dfead190029854779fa9334 in the repo, at /usr/local/bin/macro-update and at /opt/macro/app/deploy/update.sh"
  - "wc -l < /opt/macro/.git/shallow -> 1839 (2026-09-06 recorded 9020). A depth-one fetch every 3 minutes accumulates boundary commits; this fell, which is the fingerprint of depth-one acquisition having STOPPED"
  - "crontab -l + /etc/cron.d/* on 2026-10-18 contain only '*/3 * * * * /usr/local/sbin/terminal-volume-guard && ... /usr/local/bin/macro-update'. The '23 6 * * *' reflog-expire/repack line proposed on 2026-09-06 was never installed - the predicted recurrence is the measured cost of not ratifying it"
  - "Repack headroom is the binding constraint, not RAM: 874 MiB free must accommodate a new pack beside the 42.53 GiB being replaced (the 2026-09-06 output alone was 2.99 GiB), and .git/gc.log already records 'fatal: failed to run repack' from 2026-08-28 when exactly this was attempted near-full. free -m shows 2431 MiB available (adequate for pack.windowMemory=256m/threads=1) but swap at 5041/8191 MiB and load 4.31 on 2 CPUs make a repack hostile to the live services"
  - "Safe-now reclaim on this host is ~900 MB total and does NOT reach 'several GB': git prune --expire=now + prune-packed + worktree prune (garbage 292->0, size-garbage 552.89 MiB->0, prune-packable 1953->0) plus apt-get clean (113 MB->24 KB). Verified with 'git fsck --connectivity-only --no-dangling' -> rc=0 silent, and 42 running services before == 42 after"
  - "/opt/terminal is NOT on this filesystem: it is a bind mount from /mnt/terminal_storage/live-terminal on a separate 50 GB /dev/sda at 54% used (23 GB free). Terminal releases are not directly starved by '/', but '/' at 100% was already failing macro's own fetches - FETCH_HEAD resumed updating at 05:15:07 only after the prune"
falsifier: >
  Run on 146.190.142.17: (a) 'du -sh /opt/macro/.git' against 'df -h /' - if .git is not
  substantially all of the space consumed since 2026-09-06, the attribution of the refill to
  the git store is wrong; (b) 'grep -n depth /usr/local/bin/macro-update' - if it shows a
  live 'fetch --depth', then depth-one acquisition never stopped and correction (2) is wrong;
  (c) 'wc -l < /opt/macro/.git/shallow' - if it climbs back past 9020, depth-one fetching has
  resumed; (d) 'crontab -l; cat /etc/cron.d/*' filtered for reflog/repack - if the daily
  prevention line is present, the 'never ratified' premise is wrong and the refill needs
  another explanation; (e) the byte census
  'git rev-list --objects --all | cut -d" " -f1 | git cat-file --batch-check="%(objectsize:disk)"'
  summed, against the same with '--all --reflog' - if refs-only bytes approach size-pack,
  then a plain gc would suffice and correction (3) is wrong.
so_what: >
  Do NOT re-run the 2026-09-06 sequence on this host as written. It assumed headroom that no
  longer exists: 'repack -ad' must write its output beside the 42.53 GiB it replaces with
  874 MiB free, and .git/gc.log already shows that exact attempt failing mid-write on
  2026-08-28 and leaving debris packs that made the problem worse. In September the headroom
  came from deleting a 4.9 GiB untouched hand copy; no disposable multi-GiB object remains, so
  buying headroom is now an operator decision (move .git to the 23 GB /dev/sda volume, grow
  the droplet, or ratify the daily cron) and not something a session should take unilaterally.
  Second: quote BYTES, never object counts, before promising a reclaim on this clone - counts
  overstate by ~13x here, and the correct order is always
  'reflog expire --expire-unreachable=now --all' BEFORE any repack, because a bare gc frees
  only 5%. Third: safe-now reclaim (prune/prune-packed/apt clean) totals ~900 MB and buys
  days at 0.9 GiB/day, so do not report it as a fix. Serialize anything that writes against
  the service's own lock ('exec 9>/var/lock/macro-update.lock; flock -w 240 9') and verify
  with 'git fsck --connectivity-only', which is the correct and far cheaper post-prune check
  on a 42 GiB repo - prune breaks connectivity, not object content. Finally, do not conflate
  filesystems: /opt/terminal lives on a separate volume with 23 GB free, so a Terminal
  release is not what is at risk here - macro's own 3-minutely fetch is.
related:
  - "DSC:VPS-PULL-CLONE-REFLOG-PINS-PACK-DUPLICATION"
  - "DSC:GC-DISABLED-RUNNER-STORES-ACCUMULATE-EVERY-TRANSFER-PATHOLOGY-FOREVER"
  - "WS:MARKET-OS"
---

On 2026-10-18 the production VPS root filesystem was at 99% (874 MiB free), 42 days after the
2026-09-06 reclaim had left it at 51% with 38 GiB free. The refill is ~0.9 GiB/day and is
essentially all `/opt/macro/.git`, whose packed store went from 2.99 GiB to 42.53 GiB across
263 packs. The recurrence-prevention cron proposed on 2026-09-06 was never installed, which is
why this recurred on schedule.

This record corrects `DSC:VPS-PULL-CLONE-REFLOG-PINS-PACK-DUPLICATION` in three ways. Its
`--depth 1` mechanism no longer exists - the F04 history-preservation patch removed depth from
the acquisition stanza, `tests/test_deploy_git_history.py` holds it there, and `.git/shallow`
fell from 9,020 to 1,839 boundary commits rather than climbing. Packs still accumulate without
it, so the live cause is `gc.auto=0` plus reflog pinning: 99.5% of packed objects are
reflog-reachable because every 3-minutely `reset --hard` writes a reflog entry. And its
"35.6x duplication" is a count ratio; measured in bytes the ratio is 2.78x, so a plain
`git gc` frees 5% where a reflog expiry first frees 64%.

The operational consequence is that the September remedy is no longer available. A full repack
needs multi-GiB scratch beside the store it replaces, 874 MiB exists, and the one disposable
multi-GiB object was already consumed in September. Safe-now reclaim recovered ~900 MB with
`git fsck --connectivity-only` clean and all 42 services still active, but at 0.9 GiB/day that
buys days. The sufficient fix - relocating `.git` to the separate 23 GB volume, growing the
droplet, or ratifying the daily reflog-expire/repack cron - is an operator decision.
