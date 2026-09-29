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
  **The blindness is real; the reclaimable bytes are not.** Running the GC's own report over the
  pool by hand (207 registrations — the 203 directories plus 4 whose checkout is already gone)
  classifies **3 trees / 1.81 GiB as `SAFE_MERGED`, i.e. 0.9 % of the pool**. 122.45 GiB across 125
  trees is `DIRTY` or `UNPUSHED` — unlanded work no reclaim law may touch — and 99.94 GiB across 103
  trees is HUMAN-class (`sol*`/`review*`), which standing law never auto-reclaims at all. So the
  grant repairs a broken safety net and buys **~1.8 GiB of stock today**, not 201.
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
  **THAT THIRD CLAUSE FIRED (2026-09-28).** `worktree_gc.py --report` run by hand over the pool
  (`gc_macro_main.json`, 233 registrations of which 207 are in this pool, 201.13 GiB) verdicts
  `DIRTY 68/95.43G · LOCKED 43/40.49G · UNPUSHED 57/27.01G · RECENT 11/13.12G · OPEN_PR 15/8.48G ·
  ORPHAN 5/7.72G · LIVE_PROC 1/7.05G · SAFE_MERGED 3/1.81G · MISSING 4/0G`. The blindness stands on
  its own evidence (16 faults, 73 escalations); the PAYOFF claim is hereby corrected to 1.81 GiB.
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
  silence will be read as success. **Fourth, and the correction the falsifier forced: do not sell the
  grant on bytes.** Its immediate stock yield is 1.81 GiB of 201.13. What it actually buys is (a) a
  floor guard whose remediation runs at all — today every breach ends in `REMEDIATOR FAULT`, so the
  safety net is absent rather than slow — and (b) reach for the reclaim-at-merge FLOW gate over the
  fleet's busiest pool, which is where the bytes come from over time. Two further facts kill the
  obvious follow-on levers here: all 43 `LOCKED` trees in this pool carry **real seat text, zero
  content-free helper stamps** — the exact inverse of the SSD pool where 282 of 285 were stamps — so
  the `worktree_gc.py:501` lock short-circuit fix is worth a CEILING of 17.01 GiB here (15 non-human
  locked trees) and probably far less; and the pool is large by COUNT, not by fatness — 181 of 207
  trees are already sparse (<1 GiB) and still total 88.99 GiB, while 16 un-sparsified FULL trees hold
  98.41 GiB. A population cap, not a sparseness retrofit, is the lever this pool is asking for.
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

## How much a Full Disk Access grant would actually free (measured, 2026-09-28)

This record pre-registered exactly this check as its own third falsifier, and the check **fired**.
`worktree_gc.py --report` run by hand as a principal that CAN read `~/Documents`:

| verdict | trees | GiB | reclaimable? |
|---|---:|---:|---|
| `DIRTY` | 68 | 95.43 | no — uncommitted work |
| `LOCKED` | 43 | 40.49 | no — all 43 carry real seat text |
| `UNPUSHED` | 57 | 27.01 | no — unlanded work |
| `RECENT` | 11 | 13.12 | no — under the min-age gate |
| `OPEN_PR` | 15 | 8.48 | no — in flight |
| `ORPHAN` | 5 | 7.72 | needs its own decision |
| `LIVE_PROC` | 1 | 7.05 | no — process cwd inside |
| **`SAFE_MERGED`** | **3** | **1.81** | **yes** |
| `MISSING` | 4 | 0.00 | already gone |

**0.9 % of the pool.** 50 % of it (103 trees / 99.94 GiB) is HUMAN-class `sol*`/`review*` — which
`DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM` never auto-reclaims, because a web conversation's
attachment is undetectable. 61 % is `DIRTY`+`UNPUSHED`, i.e. work that has not landed.

So the honest case for the grant is not bytes. It is that **the remediator currently does not run at
all** — every breach since 2026-09-24 ends in `REMEDIATOR FAULT` — and that the reclaim-at-merge flow
gate cannot reach the fleet's busiest pool. The stock is already nearly all live or unlanded work.

Two follow-on levers die here on measurement. The `worktree_gc.py:501` lock short-circuit, worth
41 trees / 26.6 GiB on the SSD pool where 282 of 285 locks were the helper's content-free stamp, is
worth a **ceiling of 17.01 GiB** here and likely much less: **zero** of these 43 locks is a stamp.
And retrofit-to-sparse is not the lever either — 181 of 207 trees are already sparse and still total
88.99 GiB, so this pool is large by **count** (207 registrations), not by fatness. The matching lever
is the per-root population cap in §9, not a thinner tree.
