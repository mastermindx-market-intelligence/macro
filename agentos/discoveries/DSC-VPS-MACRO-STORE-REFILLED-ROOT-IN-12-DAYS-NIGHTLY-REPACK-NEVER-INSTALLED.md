---
key: VPS-MACRO-STORE-REFILLED-ROOT-IN-12-DAYS-NIGHTLY-REPACK-NEVER-INSTALLED
claim: >
  The 2026-10-19 consolidation of /opt/macro/.git (3 packs, 6.78 GiB) was undone in 12 days:
  by 2026-10-31 the store was 32G (211 packs, 22,570 loose objects, 56 tmp_pack files), it
  filled the 77G root disk and the 3-minutely macro-update fetch failed with ENOSPC from
  about 15:30Z to 18:37Z, because the nightly repack that
  DEC:VPS-MACRO-GIT-STORE-BOUNDED-BY-NIGHTLY-CRUFT-REPACK specifies was never installed (no
  timer on the host, no unit in app/deploy on main). On-disk growth without consolidation is
  about 2.1 GiB/day, more than double the 0.94 GiB/day measured before 10-19, and 13.5 of the
  31.6 GB packed was the same reachable objects stored again by successive --fix-thin fetch
  packs.
kind: landmine
verified_at: 2026-11-01
verified_by: >
  Read-only on 146.190.142.17, 2026-11-01 04:30Z-07:45Z: df -h /; du -sh /opt/macro/.git;
  git -C /opt/macro count-objects -vH; ls .git/objects/pack | grep -c tmp_pack;
  systemctl list-timers --all | grep macro-git (no match); ls /etc/systemd/system | grep
  macro-git (no match); journalctl -u macro-git-store-maintenance.service --since 2026-10-19
  (No entries); grep -nE 'No space|invalid index-pack' /var/log/macro-update.log.1;
  zgrep 'No space left on device' /var/log/syslog.2.gz. Byte census under
  /mnt/terminal_storage/macro-git-maint-20261101/census from
  'git rev-list --objects --all' plus per-pack 'git show-index' sizes. On the repo side,
  git ls-tree -r --name-only origin/main app/deploy at a7628775265b (100 files, none matching
  git-store or maint).
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
  This is the third refill of the same root disk (2026-09-06, 2026-10-19, 2026-10-31), and
  the first one fast enough to cause a production fetch outage before anyone looked.
  (1) WHY IT CAME BACK SO FAST: DEC:VPS-MACRO-GIT-STORE-BOUNDED-BY-NIGHTLY-CRUFT-REPACK
  (2026-10-19) says update.sh installs and self-arms macro-git-store-maintenance.timer on its
  next tick. On 2026-11-01 no such timer, unit file or journal entry exists on the host, and
  origin/main app/deploy has no maintenance unit. The decision record merged; its
  implementation did not. gc.auto stays 0, so nothing consolidated the store for 12 days.
  The journald cap from the same decision (10-macro-vps-cap.conf) IS installed, which makes
  the gap easy to miss when spot-checking the host.
  (2) WHY IT IS FASTER THAN BEFORE: right after a consolidation, nearly every object lives in
  one large base pack. Each 3-minutely fetch arrives as a thin pack that index-pack
  completes with --fix-thin by appending full copies of the bases it deltas against. Those
  appended bases already exist in the base pack, so they are pure duplication. On 2026-10-31
  every unique packed object was reachable, the smallest copy of each summed to 18.07 GB,
  and the packs held 31.60 GB, so 13.5 GB (43%) was duplicate copies. Reflog pinning, the
  cause before 10-19, is no longer the main term.
  (3) THE OUTAGE: from 2026-10-31 15:30:37Z to 18:37:28Z the fetch failed every tick
  ("sha1 file '.git/objects/pack/tmp_pack_Q6EkYV' write error. Out of diskspace",
  "fetch-pack: invalid index-pack output", "write error: No space left on device"), so the
  published site stopped updating for about 3 hours and each failed tick left a tmp_pack
  file behind (56 in all). rsyslogd itself logged 53,359 ENOSPC lines. It recovered after
  about 1.5 GB was freed near 18:33Z by an actor nobody has identified.
  (4) THE 2026-11-01 RECOVERY: a consolidation staged on the separate sda volume took the
  store to 4 packs, 13.18 GiB, 0 tmp_pack (session local_fff9f7a7, Macro PR 9666 carries
  the durable nightly job). The week's 609 MB syslog.1 was compressed into the empty
  syslog.2.gz slot (0.55 GB). / ended at 76% used, 19.77 GB free. Even consolidated, the
  store roughly doubled in 13 days (6.78 to 13.18 GiB), so reachable history grows by about
  0.5 GiB/day on its own.
evidence:
  - >
    DEC:VPS-MACRO-GIT-STORE-BOUNDED-BY-NIGHTLY-CRUFT-REPACK rationale records the 2026-10-19
    swap "263 packs / 42.5 GiB to 3 / 6.78 GiB" and states that update.sh arms the timer on
    the next pull. 2026-11-01: 'systemctl list-timers --all | grep macro-git' and
    'ls /etc/systemd/system | grep macro-git' both empty; journalctl for
    macro-git-store-maintenance.service since 2026-10-19 prints "-- No entries --";
    'git ls-tree -r --name-only origin/main app/deploy' at a7628775265b lists 100 files and
    'grep -icE "git-store|maint"' on them is 0. /etc/systemd/journald.conf.d/10-macro-vps-cap.conf
    is present.
  - >
    2026-11-01 ~04:30Z before any change: df -h / showed 77G size, 1.4G free (99%);
    du -sh /opt/macro/.git 32G; count-objects 211 packs = 31.60 GB, 22,570 loose objects
    (~2.44 GiB), 56 tmp_pack_* files (55 MB). (32 - 6.78) GiB / 12 days = 2.1 GiB/day,
    against 0.94 GiB/day in DSC:VPS-ROOT-REFILLED-IN-42-DAYS-AND-REPACK-IS-NOW-DISK-BLOCKED.
  - >
    Byte census (files allcopies.txt, reach-min.txt, census-perpack.txt under
    /mnt/terminal_storage/macro-git-maint-20261101/census): every unique packed object is
    reachable from refs; reachable objects at their smallest existing copy sum to 18.07 GB;
    all copies sum to 31.60 GB. The 10-19 base pack c00537ca (7.16 GB) holds the smallest
    copy of 644,852 reachable objects, so a consolidation must keep it.
  - >
    /var/log/macro-update.log.1 lines 26581-26620: 40 error lines, the first being
    "fatal: sha1 file '.git/objects/pack/tmp_pack_Q6EkYV' write error. Out of diskspace" then
    alternating "fatal: fetch-pack: invalid index-pack output" /
    "fatal: write error: No space left on device". The current macro-update.log has 0 such
    lines. The log has no timestamps; the 15:30:37Z-18:37:28Z window comes from syslog
    updater lines read on 2026-11-01. rsyslogd's own ENOSPC lines in syslog.2.gz span
    2026-10-31T15:48:16Z to 18:33:26Z (53,359 of 53,377 'No space left on device' lines).
  - >
    After the 2026-11-01 recovery, 07:31Z: count-objects 4 packs, size-pack 13.18 GiB,
    0 tmp_pack; df / 76% used, 19,767,408 KiB free; .git/FETCH_HEAD updated 07:30:05Z,
    so the 3-minutely fetch is succeeding again.
falsifier: >
  On 146.190.142.17: (a) 'systemctl list-timers --all | grep macro-git' and
  'journalctl -u macro-git-store-maintenance.service --since 2026-10-19' - any entry dated
  before 2026-10-31 means the nightly job did run and the refill needs another explanation;
  (b) 'git -C /opt/macro count-objects -vH' on two days with no consolidation between them -
  size-pack growing by well under 1 GiB/day refutes the 2.1 GiB/day rate; (c) recompute the
  census with 'git rev-list --objects --all' piped to
  'git cat-file --batch-check="%(objectname) %(objectsize:disk)"' against the per-pack sizes
  from 'git show-index < pack-*.idx' - if the sum over all copies approaches the
  smallest-copy sum, the fix-thin duplication claim is wrong; (d)
  'grep -nE "No space|invalid index-pack" /var/log/macro-update.log.1' returning nothing
  refutes the outage (the file rotates weekly; after 2026-11-08 read macro-update.log.2.gz).
so_what: >
  Do not treat DEC:VPS-MACRO-GIT-STORE-BOUNDED-BY-NIGHTLY-CRUFT-REPACK as live until
  'systemctl list-timers' on the host shows macro-git-store-maintenance.timer and its journal
  shows a successful run; a merged decision record is not an installed unit. Until the
  nightly job lands (Macro PR 9666), budget about 2 GiB/day on /: from 19.77 GB free on
  2026-11-01 the disk drops below 15% free (11.6 GB) in about 4 days and fills in about
  9-10 days. Any consolidation must keep base pack c00537ca and should stage on the sda
  volume (/mnt/terminal_storage), because a single pass needs ~11 GB of scratch. When / is
  near full, look for tmp_pack_* growth in .git/objects/pack and for
  "invalid index-pack output" in /var/log/macro-update.log, which is how the outage shows up;
  the updater log has no timestamps, so correlate with syslog.
related:
  - "DEC:VPS-MACRO-GIT-STORE-BOUNDED-BY-NIGHTLY-CRUFT-REPACK"
  - "DSC:VPS-ROOT-REFILLED-IN-42-DAYS-AND-REPACK-IS-NOW-DISK-BLOCKED"
  - "DSC:VPS-PULL-CLONE-GROWS-ONE-92MB-PACK-PER-SITE-RENDER"
  - "DSC:VPS-PULL-CLONE-REFLOG-PINS-PACK-DUPLICATION"
  - "DSC:VPS-MACRO-SHALLOW-ROOT-PINNED-BY-ISSUER-MANIFEST-CODE-VERSION"
  - "DSC:VPS-QUOTE-HUB-LRU-EVICTION-INFO-FLOODS-SYSLOG"
  - "WS:MARKET-OS"
---

On 2026-10-31 the production VPS root disk filled for the third time, 12 days after the
2026-10-19 consolidation. The 3-minutely `macro-update` fetch failed with ENOSPC from about
15:30Z to 18:37Z, so the published site stopped updating for about three hours and 56
`tmp_pack_*` files were left in `/opt/macro/.git/objects/pack`.

The 2026-10-19 decision says a nightly, space-gated repack keeps the store bounded and that
`update.sh` installs it automatically. It was never installed: the host has no timer, unit
or journal entry for it, and `app/deploy` on main has no such unit. With nothing
consolidating, the store grew about 2.1 GiB/day on disk. Most of the extra rate is
duplication: each thin fetch pack completed with `--fix-thin` appends full copies of base
objects the store already holds, and on 2026-10-31 that accounted for 13.5 of 31.6 GB.

On 2026-11-01 a consolidation staged on the sda volume brought the store to 13.18 GiB and
`/` to 19.77 GB free. That buys about 4 days above 15% free at the unconsolidated rate. The
durable fix is the nightly job in Macro PR 9666; until a host check shows it running, treat
the disk as refilling.
