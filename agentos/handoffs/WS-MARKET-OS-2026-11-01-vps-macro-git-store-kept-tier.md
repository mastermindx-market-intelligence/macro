---
workstream: WS:MARKET-OS
session: claude/ssd-agentos-vps-git-store-1101-717088cb6d789d87
model: opus
ended_because: complete
mission: >-
  Stop the production droplet's root disk (146.190.142.17) from refilling from
  /opt/macro/.git, durably, without breaking the Macro Dashboard's 3-minute deploy pull or
  the Terminal's deploy. Done when root has at least 15 GiB free, the growth mechanism is
  addressed and verified to run, the decision is recorded and merged, and the leftover
  snapshots are reported to their owner.
state_before: >-
  2026-11-01 05:15Z: root had 1.36 GiB free (99% used) with 32.0 GiB in /opt/macro/.git across
  211 packs. Macro #9666, the 10-19 nightly cruft-repack design, had never merged, so no
  maintenance timer existed on the droplet
  (DSC:VPS-MACRO-STORE-REFILLED-ROOT-IN-12-DAYS-NIGHTLY-REPACK-NEVER-INSTALLED). The 10-19 gate (free space of at least the whole
  store plus 3 GiB) could no longer pass, because the store's reachable history had grown.
  update.sh had no free-space guard, so a pull on a full disk could leave a partial pack.
changed:
  - path: "app/deploy/macro-git-store-maintenance.sh (Macro #9666)"
    what: "kept tier for packs of at least 2 GiB, gate on non-kept packs plus loose plus 3 GiB, memory gate first, greedy capped space fallback (16, 0 off) planned before any freeze, orphan .pack removal"
  - path: "app/deploy/update.sh (Macro #9666)"
    what: "7 GiB pull floor with marker /run/macro-update-disk-refused; a refused tick skips the fetch, pins NEW to OLD without reading FETCH_HEAD, still reconciles and installs units, then exits 1"
  - path: "app/deploy/macro-git-store-maintenance.{service,timer}, app/deploy/README.md, tests (Macro #9666)"
    what: "units with MemoryHigh=640M / MemoryMax=900M; runbook; tests/test_deploy_git_store_maintenance.py and tests/test_deploy_git_history.py"
  - path: "VPS /opt/macro/.git (146.190.142.17)"
    what: "two incremental consolidations under the updater lock: 211 packs / 32.0 GiB to 3 packs / 14.9 GiB; root 1.26 GiB to 18.46 GiB free"
  - path: "agentos/decisions/DEC-VPS-MACRO-GIT-STORE-KEPT-TIER-NIGHTLY-REPACK-AND-PULL-GUARD.md"
    what: "new decision; supersedes DEC:VPS-MACRO-GIT-STORE-BOUNDED-BY-NIGHTLY-CRUFT-REPACK"
  - path: "agentos/discoveries/DSC-VPS-MACRO-STORE-REGROWTH-IS-REACHABLE-DATA-ARTIFACT-HISTORY.md"
    what: "new discovery: residual growth is reachable data/ history, about 0.63 GiB a day"
verified:
  - claim: "root has at least 15 GiB free after the consolidation"
    command: "ssh root@146.190.142.17 df -k /"
    result: "before: 2026-11-01 05:15Z, 1.36 GiB free (99% used); after: 2026-11-02 06:36Z, 24,275,892 KiB (23.15 GiB) free, 70% used"
  - claim: "the consolidated store is complete"
    command: "git -C <snapshot of /opt/macro/.git taken under /var/lock/macro-update.lock> fsck --no-dangling"
    result: "exit 0, no output, 44 min 33 s, 1.1 GiB peak; snapshot under the lock at 07:10:01Z, HEAD 88b70c0c9b86 (a live fsck during pulls had reported five missing objects; the snapshot is the result of record)"
  - claim: "the nightly maintenance unit is installed by the deploy pull and runs within its memory cap"
    command: "cmp /usr/local/sbin/macro-git-store-maintenance /opt/macro/app/deploy/macro-git-store-maintenance.sh (and both units against /etc/systemd/system); systemctl list-timers macro-git-store-maintenance.timer; systemctl show -p ExecMainStartTimestamp,ExecMainExitTimestamp,ExecMainStatus,Result,MemoryPeak macro-git-store-maintenance.service; journalctl -u macro-git-store-maintenance.service"
    result: "#9666 merged 2026-11-02T05:55:25Z (3676df52). The 05:57Z pull installed the script and both units, all byte-identical to app/deploy. The timer started 05:59:22Z and, having no earlier stamp (Persistent=true), fired at 05:59:32Z. The run ended 06:15:17Z: Result=success, ExecMainStatus=0, MemoryPeak 640.5 MiB (held at MemoryHigh 640M, under MemoryMax 900M), swap peak 282.9 MiB. Store 17,190,175 to 14,974,678 KiB (7 packs, 3 kept); root free 22,186,736 to 24,277,012 KiB. Next run 2026-11-03 02:43:48Z"
  - claim: "the Macro deploy pull succeeds and the site and the Terminal answer"
    command: "tail -n 40 /var/log/macro-update.log (root crontab, every 3 min); ls /run/macro-update-disk-refused; curl -sS -o /dev/null -w '%{http_code}' https://www.mastermind-x.com/; curl -sS -o /dev/null -w '%{http_code}' https://app.mastermind-x.com/terminal; systemctl is-active terminal"
    result: "2026-11-02 06:31:07Z tick pulled 5085667c..bca436e58f7; no refusal marker; www.mastermind-x.com 200; app.mastermind-x.com/terminal 200; terminal.service active. Every tick still ends 'deploy finished with status 1 (frozen lanes: w2c)', a W2C lane freeze that predates this work"
  - claim: "the residual growth is reachable data/ history"
    command: "git -C /opt/macro rev-list --objects 69dd6e77..HEAD | git -C /opt/macro cat-file --batch-check='%(objectname) %(objecttype) %(objectsize:disk) %(rest)'"
    result: "688,313 objects, 8,701,900,199 bytes; data/ 73.5%, site/ 13.2%, other 13.3%; data/baskets 2.06 GB, data/yahoo 1.28 GB"
  - claim: "leftover snapshots outside the Git store were cleared by someone other than this session"
    command: "ls -la /opt/mastermind-runtime-maintenance/ /mnt/terminal_storage/recovery; df -h /mnt/terminal_storage"
    result: "2026-11-02 06:45Z: the pr1677-20261021 and pr1677-20261021-ff16 snapshots (3.2 GiB on root) were gone, directory changed 2026-11-01T19:35:40Z; /mnt/terminal_storage/recovery was down from 16 GiB to 14 MiB (only macro-git-orphans-20261019.git), changed 2026-11-02T02:38:14Z, with this session's consolidation logs removed at the same time; that volume is 35% used"
unverified:
  - claim: "the first calendar-scheduled nightly run succeeds (the 05:59Z run was the timer's catch-up on arming, not a 02:40Z slot)"
    what_would_verify: "journalctl -u macro-git-store-maintenance.service --since '2026-11-03 02:40' on the droplet: exit 0 and a store near 14.3 GiB plus one day of growth"
unresolved:
  - "Reachable history grows about 0.63 GiB a day. At 23.15 GiB free (2026-11-02 06:36Z) and the 7 GiB pull floor, the pull starts refusing around 2026-11-27. Ending the growth needs an operator choice among the options in DEC:VPS-MACRO-GIT-STORE-KEPT-TIER-NIGHTLY-REPACK-AND-PULL-GUARD (publish data/baskets, data/yahoo and the China stock trees outside main; shard the outbox JSONL; stop committing mockups/ and the generated CI file; or grow the disk, which is a purchase)"
next_actions:
  - "By 2026-11-14 (the DEC review date) the operator picks a data-artifact publication option from the DEC; the session that implements it opens its own Macro PR"
  - "After the next 02:40Z window, read journalctl -u macro-git-store-maintenance.service once and confirm exit 0 and a flat store"
do_not_redo:
  - "Do not re-shallow /opt/macro or edit .git/shallow. MO-A-F04 forbids changing its depth, and issuer qualification runs merge-base --is-ancestor from manifest code versions (engine/company_intelligence/issuer_disclosure_owner.py:369); issuer manifests pin the shallow root a13962ee (DSC:VPS-MACRO-SHALLOW-ROOT-PINNED-BY-ISSUER-MANIFEST-CODE-VERSION, Macro PR 10375)"
  - "Do not run another full consolidation by hand while the nightly timer is armed; the kept tier and nightly repack own the store now"
  - "The 2026-11-01 consolidation is done and fsck-verified; do not repeat it"
danger_areas:
  - "Never delete packs before fsck passes; take the fsck from a snapshot under /var/lock/macro-update.lock, because a live fsck races the 3-minute pull and reports objects missing"
  - "A fetch that fails part-way truncates FETCH_HEAD to empty; any script that reads it under set -e must not run on a refused tick"
  - "Never touch /var/lib/macro-*, /opt/macro/site*, ohlc.served, swapfiles or /opt/terminal during store work"
prs: ["#9666"]
decisions: ["DEC:VPS-MACRO-GIT-STORE-KEPT-TIER-NIGHTLY-REPACK-AND-PULL-GUARD"]
discoveries: ["DSC:VPS-MACRO-STORE-REGROWTH-IS-REACHABLE-DATA-ARTIFACT-HISTORY", "DSC:VPS-MACRO-STORE-REFILLED-ROOT-IN-12-DAYS-NIGHTLY-REPACK-NEVER-INSTALLED", "DSC:VPS-MACRO-SHALLOW-ROOT-PINNED-BY-ISSUER-MANIFEST-CODE-VERSION", "DSC:VPS-QUOTE-HUB-LRU-EVICTION-INFO-FLOODS-SYSLOG"]
---

# WS:MARKET-OS — VPS Macro Git store: kept tier, nightly repack and pull guard (2026-11-01)

**Before and after.** On 2026-11-01 at 05:15Z the droplet root had 1.36 GiB free, with
32.0 GiB in `/opt/macro/.git` across 211 packs. Two incremental consolidations under the
updater lock took the store to 3 packs and 14.9 GiB. After Macro #9666 merged and its first maintenance run, root has 23.15 GiB free (2026-11-02 06:36Z) and the store is 14.3 GiB in 7 packs, 3 of them kept. The pull, the
site and the Terminal stayed up throughout.

**What keeps it there.** Macro #9666 adds a nightly repack that freezes packs of at least
2 GiB as a kept tier and rewrites only what arrived since. It also adds a 7 GiB free-space
guard to the deploy pull, so a full disk refuses the pull instead of writing a partial pack.

**What it cannot fix.** The store still grows about 0.63 GiB a day, and all of that is history
`main` reaches. Nearly three quarters is under `data/`, led by the per-symbol trees
`data/baskets` and `data/yahoo`. At this rate the pull reaches its floor around 2026-11-27.
The operator's options are in the decision record. Re-shallowing the clone is not one of them.

**Related findings from the same incident** (Macro PR 10375, a parallel census session):
DSC:VPS-MACRO-STORE-REFILLED-ROOT-IN-12-DAYS-NIGHTLY-REPACK-NEVER-INSTALLED covers the refill,
the 10-31 ENOSPC outage, and the 10-19 timer that was never installed.
DSC:VPS-MACRO-SHALLOW-ROOT-PINNED-BY-ISSUER-MANIFEST-CODE-VERSION shows why the clone cannot be
re-shallowed. DSC:VPS-QUOTE-HUB-LRU-EVICTION-INFO-FLOODS-SYSLOG records a separate source of
root-disk writes on the same host.

`MISSION_COMPLETE: true` for the disk task. The growth decision is open for the operator.
