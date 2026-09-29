---
key: THE-SWEEPER-IS-TCC-BLIND-TO-THE-LARGEST-INTERNAL-WORKTREE-POOL
claim: >
  The largest agent-worktree pool on this host is **`/Users/chriswong/Documents/Cluade/macro-main/
  .claude` — 201.13 GiB across 203 session worktrees** — and the fleet GC has never been able to
  see it. `storage_floor_guard.py` (launchd, every 1800 s) invokes `worktree_gc_launchd.py` when the
  internal floor is breached, and since **2026-09-24 05:49:53** that remediation has failed with
  `REMEDIATOR FAULT: sweeper BLIND: denied: PermissionError: [Errno 1] Operation not permitted:
  '/Users/chriswong/Documents'` — **16 faults**, alongside **73 `ESCALATION` lines**. The one
  remediation that did complete (2026-09-26 16:56) reclaimed **−0.1 GiB** and logged
  `automated reclaim is NOT keeping up`. **This is not the roots-scope defect**
  (`DSC:A-HOST-CHECKOUT-BELT-MAKES-A-WIDER-ROOTS-LIST-INERT`): `.claude/worktrees` is already in
  `config/worktree_gc.json` `roots`, the config is `armed: true`, and `macro-main` is a host
  checkout the GC expands its repo-relative roots under **by design**. The blocker is macOS TCC:
  `~/Documents` is a protected location, and the launchd job's interpreter — `/usr/bin/python3`,
  which resolves to `/Applications/Xcode.app/Contents/Developer/usr/bin/python3` — has no Full Disk
  Access. An interactive session inherits its terminal's grant and reads the same path fine, which
  is why every hand-run census has seen this pool and every automated sweep has not.
falsifier: >
  `grep -c 'REMEDIATOR FAULT' ~/Library/Logs/mastermind/storage-floor-guard.out.log` = 16, first
  `2026-09-24 05:49:53`, last `2026-09-27 16:33:53`; `grep -c ESCALATION` = 73; the 2026-09-26
  16:56:38 pair reads `internal remediation START (internal floor breached)` then
  `DONE rc=0 free 255.7 -> 255.6 GiB (reclaimed -0.1 GiB)`. `du -sxk ~/Documents` = 480,104,404 KB
  (457.9 GiB); `~/Documents/Cluade/macro-main/.claude` = 201.13 GiB; `ls -1
  ~/Documents/Cluade/macro-main/.claude/worktrees | wc -l` = 203. `.claude/worktrees` appears in
  `config/worktree_gc.json` `roots` and `armed` is `true`. `/usr/bin/python3 -c 'import sys;
  print(sys.executable)'` prints the Xcode path. Disproved by a sweep that traverses `~/Documents`
  without a Full Disk Access grant, by the pool turning out to be outside `roots` after all, or —
  the one to actually check before acting — by the 203 trees classifying as overwhelmingly
  NOT-reclaimable, which would make the blindness real but the payoff small.
so_what: >
  **Three storage defects have now been found in this program and only this one is a bug in the
  sense of something being broken.** The roots list and the host-checkout belt are scope decisions
  awaiting ratification; this is a working, armed, correctly-scoped sweeper that simply cannot read
  its own target. Fixing it needs no code, no config and no ratification — it needs a Full Disk
  Access grant, **which is a security setting only the operator may make**; `TCC.db` is
  SIP-protected and no session may edit it. Second: **the grant is broader than it looks and should
  be stated honestly.** All five storage jobs — `storage-floor-guard`, `storage-sweeper`,
  `worktree-gc`, `worktree-salvage`, `fleet-remote-sweeper` — share `/usr/bin/python3`, so one grant
  repairs all five but also extends full disk access to anything else that interpreter runs; the
  tighter alternative is a dedicated interpreter for these jobs with the grant scoped to it. Third,
  and the reason this record exists at all: **an automated remediator that cannot see its target
  fails exactly like one with nothing to do.** The floor guard kept reporting `OK` between breaches
  and the fault line only appears when a breach triggers remediation, so a 201 GiB pool went
  unreclaimed for days behind a green-looking instrument. Any reclaim lane must assert its own
  REACH — enumerate what it could not read and report that count beside its verdict — or its
  silence will be read as success.
kind: constraint
verified_at: 2026-09-28
verified_by: >
  `~/Library/Logs/mastermind/storage-floor-guard.out.log` (fault/escalation counts and the 09-26
  remediation pair); `du -sxk /Users/chriswong/Documents` and `…/Documents/*` and
  `…/Documents/Cluade/*` (457.9 GiB total; Cluade 400.92, macro-main 210.40, `Macro Dashboard`
  81.22, charting-app 56.10); `du -sxk` over macro-main's children (`.claude` 201.13 GiB);
  `ls -1 …/macro-main/.claude/worktrees | wc -l` = 203; `config/worktree_gc.json` (`armed: true`,
  `.claude/worktrees` among `roots`); `plutil -lint` on the LaunchAgents plists (all OK — a
  `plistlib` parse failure on six of them was the reader being stricter than launchd, not a broken
  job); `plistlib` read of `com.mastermind.storage-floor-guard.plist` and
  `com.macro.worktree-gc.plist` for their programs and 1800 s interval; the floor guard's own most
  recent rows (`internal /System/Volumes/Data free 316.8 GiB (floor 260) OK`).
scope:
  - macro
  - research/WORKTREE_GC_POLICY.md
  - config/worktree_gc.json
  - scripts/worktree_gc.py
confidence: verified
---

## Why every census missed it and every sweep failed

The two run as different principals.

| asks | can read `~/Documents` | what it concluded |
|---|---|---|
| an interactive session (inherits the terminal's TCC grant) | yes | "the internal agent bytes are scratchpads + runner stores" |
| `launchd` → `/usr/bin/python3` (no grant) | **no** | `PermissionError`, 16 faults, 73 escalations |

Both are correct about what they can see. Neither states its REACH, so the hand census under-counted
by 201 GiB and the automated sweeper reported a fault that nobody was reading.

## What this does not change

The floor is not currently breached: internal free is **316.8 GiB against a floor of 260**, and the
last breach was 2026-09-26. The broken thing is the safety net, not the disk — which is precisely
why it could stay broken since 09-24 without anyone noticing.
