---
key: VPS-MACRO-GIT-STORE-KEPT-TIER-NIGHTLY-REPACK-AND-PULL-GUARD
question: >
  DEC:VPS-MACRO-GIT-STORE-BOUNDED-BY-NIGHTLY-CRUFT-REPACK (2026-10-19) chose a nightly cruft
  repack to keep the /opt/macro pull clone on 146.190.142.17 bounded. Its PR (Macro #9666)
  never merged, so the timer never ran, and by 2026-11-01 05:15Z the root disk had 1.36 GiB
  free with 32 GiB in /opt/macro/.git. The 10-19 design also assumed the store stays near
  its 7 GiB live size and gated each repack on free space of at least the whole store plus
  3 GiB. The regrowth since then is reachable history on main, which no repack can drop, so
  that gate gets harder to pass every day and would soon refuse for good. How does the store
  stay maintainable, and the 3-minute pull stay safe, while reachable history keeps growing?
answer: >
  Keep the 10-19 design and amend it in three places, all in Macro #9666.
  (1) Kept tier. Each night, before and after the repack, every non-cruft pack of at least
  2 GiB (MACRO_GIT_MAINT_PROMOTE_KIB=2097152) that has an .idx gets a .keep file reading
  "macro-git-store-maintenance kept tier <date>". The repack runs with
  repack.packKeptObjects=false, so kept packs are neither rewritten nor counted again. A
  night rewrites only the packs that arrived since the last promotion, plus loose objects and
  the cruft pack. Cruft packs (.mtimes) are never kept, so unreachable objects still expire
  after the two-week grace. A .keep the job did not write is left alone.
  (2) Gate and fallback. The memory check runs first, so a deferred night (exit 75) freezes
  nothing. The repack then needs free space of at least the non-kept packs plus loose objects
  plus 3 GiB, instead of the whole store plus 3 GiB. On a shortfall a space fallback plans,
  largest pack first, how many more non-cruft packs it would have to freeze for the repack to
  fit, up to 16 (MACRO_GIT_MAINT_FALLBACK_MAX; 0 turns it off). It freezes them only if that
  plan fits. Otherwise it freezes nothing, logs "REFUSED ... no pack written" and exits 1.
  A .pack with no .idx and no .keep that is older than 6 h is an interrupted write. It is
  removed and never counted.
  (3) Pull guard. In update.sh, after 'flock -n 9' and before the fetch, a tick refuses the
  pull when the clone's object filesystem has less than 7 GiB free
  (MACRO_UPDATE_MIN_FREE_KIB=7340032), or when free space or the floor does not read as a
  whole number. It writes the reason to stderr and to 'logger -p user.err -t macro-update'
  and touches /run/macro-update-disk-refused. A refused tick skips only the fetch. It pins
  NEW to OLD without reading FETCH_HEAD, still reconciles the current checkout and installs
  units, and exits 1 at the end. The next passing tick removes the marker. The site keeps
  serving the last good checkout, and no fetch can fill the disk part-way.
  Everything else in the 10-19 decision stands: the timer at 02:40 UTC installed by
  update.sh, the lock discipline, the resource caps, the two-week cruft grace, gc.auto=0,
  and no fetch, deepening, unshallowing or .git/shallow edit (MO-A-F04).
  When the store has already outgrown root, recovery is the staged off-root consolidation run
  on 2026-11-01. It packs groups of packs on /mnt/terminal_storage with
  GIT_OBJECT_DIRECTORY pointed at the scratch store, then swaps each group in under the lock
  (alternates bridge, rescue, retire by rename, fsck, delete, copy home, cmp, fsck again).
  Reachable growth itself is not bounded by any of this. Its rate sets a runway, and the
  options for ending it are a Macro pipeline decision for the operator, set out in the body.
rationale: >
  Two facts from 2026-11-01 drive the amendments.
  First, the regrowth is reachable. The 10-19 reclaim worked because expiring reflogs
  released 337 commits from behind an old shallow boundary. Since then the pull has fetched
  main forward from a fixed boundary, and every commit after it stays reachable from
  origin/main. 73.5% of those bytes are under data/, not site/
  (DSC:VPS-MACRO-STORE-REGROWTH-IS-REACHABLE-DATA-ARTIFACT-HISTORY). A cruft repack only
  compresses them, so the store's floor rises every day.
  Second, a whole-store gate fails once the store passes about half the disk. With a 32 GiB
  store, the 10-19 gate needed 35 GiB free on a 77 GiB disk. Gating on the part that will
  actually be rewritten keeps the nightly need near one day of fetches, the newest
  sub-2-GiB pack, loose objects and 3 GiB, about 4-6 GiB, whatever the size of the kept
  history.
  The kept tier is what makes the smaller gate honest. Without the .keep files the repack
  would rewrite the whole store and could fail on ENOSPC under a gate that only counted part
  of it. The PR's tests pin that: a negative control that skips promotion fails the
  three-night test.
  The pull guard closes the failure mode seen on 11-01, when a fetch into a disk with
  1.36 GiB free could have failed mid-write next to a live checkout. Refusing before the
  fetch keeps the last good site serving and turns a silent fill into a logged error. The
  7 GiB floor sits above the nightly need, so pulls stop before maintenance does, and a
  refused tick still installs the units, so a fix shipped later can still reach the droplet.
alternatives:
  - option: Keep the 10-19 whole-store gate
    why_not: it needs free space above the whole store. With reachable growth that stops passing at about half the disk, and the job then refuses every night while the pull keeps filling the disk
  - option: Re-clone or re-shallow /opt/macro to drop old history
    why_not: MO-A-F04 forbids changing the clone's depth or editing .git/shallow. Issuer qualification also requires each manifest's code_version to be an ancestor of the local HEAD (accepts_revision runs 'merge-base --is-ancestor', engine/company_intelligence/issuer_disclosure_owner.py line 369), and issuer manifests on the droplet pin the shallow root a13962ee (DSC:VPS-MACRO-SHALLOW-ROOT-PINNED-BY-ISSUER-MANIFEST-CODE-VERSION), so a re-shallowed clone would fail issuer qualification. It would also swap the live checkout out from under macro-api
  - option: Move /opt/macro/.git onto /mnt/terminal_storage
    why_not: rejected on 2026-10-19 for coupling the Macro pull to the Terminal data volume. That volume is itself 86% used (6.8 GiB free on 2026-11-01), so it only moves the deadline
  - option: Grow the root disk
    why_not: a purchase, which this session may not make. It buys time at the current rate but does not stop growth. Listed for the operator in the body
  - option: Publish large rewritten data artifacts outside main's history
    why_not: not rejected. It is the change that would actually bound the store, but it changes the Macro publishing pipeline, so it is proposed for the operator's decision in the body instead of being made here
affects:
  - "WS:MARKET-OS"
  - app/deploy/macro-git-store-maintenance.sh
  - app/deploy/update.sh
  - app/deploy/README.md
  - tests/test_deploy_git_store_maintenance.py
  - tests/test_deploy_git_history.py
  - "VPS /opt/macro (146.190.142.17)"
evidence:
  - >
    Macro PR 9666 (claude/ssd-vps-git-store-bound-d714bd8de4409d68): kept tier, gate,
    greedy capped fallback, memory-first ordering and pull guard. At e020071d86e8,
    tests/test_deploy_git_store_maintenance.py passed 52 of 52 on the droplet's git 2.43.0,
    tests/test_deploy_git_history.py passed 19 of 19 on the Mac, and the 16 other test files that read update.sh passed 1544 with 3 skipped and 3 failures that also fail on main (two press-property checks against main's own update.sh, and one test that needs the site/ tree a sparse checkout omits). Every new
    behaviour has a negative control that fails when the behaviour is removed.
  - >
    Independent read-only audits (Opus, ROUTE AUDIT). The first, of 1d293793f3e0, returned
    REQUEST_CHANGES with ten findings (F1-F10), repaired at e2d859747. The second, of
    e2d859747, found that a refused tick still aborted on an empty FETCH_HEAD, that one
    frozen pack was not always enough, and that the memory check ran after promotion; those
    were repaired at e020071d86e8. A third read-only Opus audit of e020071d86e8, scoped to
    those repairs, returned APPROVE with two accepted non-blocking notes. First, a fetch that
    lands between the plan and the recount can make the run refuse after freezing its planned
    packs, which changes only .keep metadata. Second, on a low-memory night a space shortfall
    logs DEFERRED, not REFUSED.
  - >
    The 10-19 timer never ran because it was never installed: no unit, timer or journal entry
    exists since 2026-10-19, and the 10-31 15:30Z-18:37Z ENOSPC outage followed
    (DSC:VPS-MACRO-STORE-REFILLED-ROOT-IN-12-DAYS-NIGHTLY-REPACK-NEVER-INSTALLED, Macro PR
    10375). The shallow root is pinned by issuer manifests
    (DSC:VPS-MACRO-SHALLOW-ROOT-PINNED-BY-ISSUER-MANIFEST-CODE-VERSION, same PR).
  - >
    Production before, 2026-11-01 05:15Z: root 1,425,224 KiB free (99% used); .git
    33,563,180 KiB; 211 packs, size-pack 30,909,696 KiB; 22,588 loose objects
    (2,568,376 KiB); 56 abandoned tmp_* files.
  - >
    Stage 1 swap log, 05:54:27Z-05:56:03Z: 140 packs (16,573,468 KiB) became pack
    db918be22e46 (4,236,694,194 bytes). Rescue 0, fsck ok before the delete and after the
    copy home. Root free went from 1,322,952 KiB to 14,518,700 KiB.
  - >
    Stage 2 swap log, 06:09:51Z-06:10:55Z: 71 packs (7,390,327 KiB) became pack
    af2d8f829cfe (2,616,363,053 bytes, 163,119 objects). The pack step took 10 min 20 s at a
    1.1 GiB memory peak and the verify 2 min 38 s. Rescue 0, fsck ok before the delete and
    after the copy home. Root free went from 14,515,868 KiB to 19,353,604 KiB, and the store
    from 20,466,928 KiB to 15,629,180 KiB.
  - >
    Production after, 2026-11-01 07:10Z: root 19,319,284 KiB free (76% used); 3 packs,
    size-pack 13,731,295 KiB, and 14,492 loose objects (1,874,192 KiB) from pulls since.
    'git fsck --no-dangling' on a hard-link snapshot of the store, taken under
    /var/lock/macro-update.lock at 07:10:01Z (HEAD 88b70c0c9b86), exited 0 with no output
    after 44 min 33 s, at a 1.1 GiB memory peak. A live fsck run earlier, while 3-minute
    pulls were writing, reported five missing objects. That fits pulls adding packs after
    fsck had listed the store and then moving the refs it walked. The clean snapshot of the
    same store under the lock shows no damage, so it is the result of record.
confidence: high
reversibility: easy
decided_by: claude-opus (session 1cdae186, commissioned by session local_279c4491 for the 2026-11-01 VPS root-disk remediation)
decided_at: 2026-11-01
supersedes:
  - "DEC:VPS-MACRO-GIT-STORE-BOUNDED-BY-NIGHTLY-CRUFT-REPACK"
review_by: 2026-11-14
---

The 10-19 plan for the Macro droplet's pull clone was right about the mechanism and wrong
about the size. Its pull request never merged, so the nightly job never ran, and the store
grew from 7 GiB to 32 GiB in 13 days. Most of that growth is history that `main` still
reaches, so a repack can compress it but never drop it.

This decision keeps the nightly job and changes three things. Packs of 2 GiB or more are
frozen with a `.keep` file, so each night rewrites only what arrived since. The space check
counts only that unfrozen part, and freezes a few more packs when that is what makes the
repack fit. And the 3-minute pull now refuses, with a logged error, when the disk has less
than 7 GiB free, instead of fetching into a full disk.

## Runway

The store gains about 0.63 GiB a day of reachable history: 8.70 GB in the 12.9 days from
the 2026-10-19 boundary commit to 2026-11-01. With 18.4 GiB free on root at 07:10Z and a
7 GiB pull floor, the pull starts refusing in about 18 days, around 2026-11-19, if nothing
else on root grows. The nightly repack keeps fetch packs from piling up on top of that, so
this rate is the whole budget. Review this decision by 2026-11-14.

On 2026-11-02 at 06:36Z, after #9666 merged and its first maintenance run, root had 23.15 GiB
free. At the same rate that moves the floor to about 2026-11-27. The review date stays
2026-11-14.

## Decision needed from the operator

Since 2026-10-19, 1,932 of the store's 3,402 commits landed on `main`, holding 8.70 GB.
By path, 73.5% of those bytes are under `data/`, 13.2% under `site/` and 13.3% elsewhere.
Most of it is thousands of small per-symbol files rewritten on every data refresh, not a
few large files:

| Path | Blob versions since 10-19 | Bytes |
|---|---|---|
| `data/baskets/` | 31,906 | 2.06 GB |
| `data/yahoo/` | 62,805 | 1.28 GB |
| `data/china_stocks/` and `data/china_stocks_raw/` | 29,849 | 0.86 GB |
| `mockups/` | 2,516 | 0.88 GB |
| `site/stocks/` | 326,591 | 0.84 GB |
| `data/capital_structure/` | 169 | 0.49 GB |
| `data/marketing/` | 1,258 | 0.34 GB |
| `.github/ci/legacy-jobs.yml` | 238 | 0.09 GB |

Nothing in this decision changes that rate. These are the ways to end it, for the operator
to choose; none is being done here.

1. **Publish the per-symbol market data outside `main`'s history.** `data/baskets`,
   `data/yahoo` and the China stock folders are half of all growth. They could move to
   object storage, or to an orphan branch force-pushed with one commit per refresh, and
   the droplet fetches them separately. Superseded versions become unreachable, and the
   nightly cruft repack drops them after the two-week grace. This changes the pipelines
   that write them and the droplet's fetch, so it needs its own PR.
2. **Do the same for `site/` renders.** The orphan-branch or artifact pattern for `site/`
   removes another 13%.
3. **Stop rewriting large single artifacts in place.** The outbox JSONL
   (`data/marketing/outbox/items.jsonl`, 235 MB over 144 versions) could be split into
   dated shards so each commit adds only new rows. Parquet and large JSON under
   `data/capital_structure/` do not delta well and fit option 1 better.
4. **Stop committing `mockups/` and the generated CI file.** Design mockups and
   `.github/ci/legacy-jobs.yml` add about 1 GB between them.
5. **Grow the root disk.** This is a purchase. It buys time at the current rate.

Re-shallowing the clone is not an option. MO-A-F04 forbids it, and issuer qualification
checks that each manifest's `code_version`, which can be the shallow root a13962ee, is an
ancestor of the local HEAD
(DSC:VPS-MACRO-SHALLOW-ROOT-PINNED-BY-ISSUER-MANIFEST-CODE-VERSION).

Until one of these lands, the pull guard turns an approaching full disk into a logged
refusal, not a corrupt fetch.
