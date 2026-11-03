---
key: VPS-MACRO-STORE-REGROWTH-IS-REACHABLE-DATA-ARTIFACT-HISTORY
claim: >
  After a full consolidation, the /opt/macro pull clone on 146.190.142.17 still holds about
  0.63 GiB a day of new history, and every byte of it is reachable from main, so no repack can
  reclaim it. On 2026-11-01 the 1,932 commits that landed on main after the 2026-10-19
  boundary commit 69dd6e77 held 688,313 objects totalling 8,701,900,199 bytes of on-disk pack
  size (blobs 8.58 GB, trees 0.12 GB, commits 1.2 MB). By path, 73.5% of those bytes are under
  data/, 13.2% under site/ and 13.3% elsewhere. Most of it is many small per-symbol files
  rewritten on every refresh, not a few large files: data/baskets holds 2.06 GB in 31,906 blob
  versions and data/yahoo 1.28 GB in 62,805. The largest single files are
  data/marketing/outbox/items.jsonl (235 MB over 144 versions),
  data/capital_structure/event_versions.parquet (136 MB over 10) and
  data/capital_structure/projection.json (129 MB over 14). Full-site renders delta well once
  repacked: site/ is only 1.15 GB of the 8.70 GB, and site/stocks is 0.84 GB of that.
  This refines DSC:VPS-PULL-CLONE-GROWS-ONE-92MB-PACK-PER-SITE-RENDER. Its ~92 MB per render
  is the size of an incoming thin fetch pack, which a repack shrinks. What stays after the
  repack is led by data/.
kind: runtime
verified_at: 2026-11-01
verified_by: >
  On 146.190.142.17, 2026-11-01, under systemd-run with low priority, against the consolidated
  store (3 packs, size-pack 13,731,295 KiB): 'git rev-list --objects 69dd6e77..HEAD' piped to
  'git cat-file --batch-check="%(objectname) %(objecttype) %(objectsize:disk) %(rest)"',
  then summed with awk by type, by top-level path, by second-level path and by file. Outputs
  are in /mnt/terminal_storage/macro-git-maint-20261101-incr/measure/ (since.objs 688,313
  lines; since.sz; since.bypath; since.byfile). 'git rev-list --count' gives 3,402 commits in
  all and 1,932 after the boundary. A whole-store walk over every ref, reflog and the index
  reaches 1,337,420 objects and 15,893,138,649 bytes, against 1,337,453 in count-objects, so
  the store holds essentially no unreachable objects after the consolidation.
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
  On 2026-11-01 the droplet root had 1.3 GiB free with 32.1 GiB in /opt/macro/.git, twelve days
  after the 2026-10-19 reclaim. Two incremental consolidations took the store to 14.9 GiB and
  root to 18.4 GiB free. This record measures what the store keeps after that: the bytes that
  are reachable, which the nightly cruft repack cannot touch. They grow at about 0.63 GiB a
  day, led by the per-symbol data trees.
evidence:
  - "since.sz sums: total 8,701,900,199; blob 8,579,720,171; tree 121,023,398; commit 1,156,630. 'git rev-list --count 69dd6e77..HEAD' = 1,932; 'git rev-list --count HEAD' = 3,402"
  - "since.bypath, top level: data 6,396,011,512 (150,348 entries); mockups 881,637,632 (2,516); site/stocks 835,229,403 (326,591); .github 92,036,218 (788); research 78,586,556 (3,396); tests 59,687,322 (2,409). site/ in all is 1,149,987,205"
  - "data/ by directory: baskets 2,056,537,556 (31,906); yahoo 1,279,919,977 (62,805); china_stocks 522,264,477 (14,956); capital_structure 491,944,987 (169); marketing 340,339,866 (1,258); china_stocks_raw 337,934,183 (14,893); stocks 149,662,745 (2,130); quiver 105,404,700 (394)"
  - "since.byfile, largest files: data/marketing/outbox/items.jsonl 235,168,567 (144 versions); data/capital_structure/event_versions.parquet 135,914,787 (10); data/capital_structure/projection.json 129,236,433 (14); .github/ci/legacy-jobs.yml 89,748,546 (238); data/chronicle/events.jsonl 60,050,018 (14); data/china_irm/qa.parquet 56,236,830 (10)"
  - "Whole-store walk: rev-list --objects --all --reflog --indexed-objects reached 1,337,420 objects; count-objects -v reported 1,337,453 (in-pack 1,323,000 plus 14,492 loose); summed disk size 15,893,138,649 bytes against a 15,630,696 KiB .git"
  - "Rate: 8.70 GB over the 12.9 days from 2026-10-19T08:50Z to 2026-11-01T06:21Z is about 0.63 GiB a day. With 18.4 GiB free on root and the 7 GiB pull floor from DEC:VPS-MACRO-GIT-STORE-KEPT-TIER-NIGHTLY-REPACK-AND-PULL-GUARD, the pull starts refusing around 2026-11-19 if nothing else on root grows"
falsifier: >
  (a) Re-run the same pipeline on the droplet from any later boundary commit B:
  'git -C /opt/macro rev-list --objects B..HEAD | git -C /opt/macro cat-file
  --batch-check="%(objectname) %(objecttype) %(objectsize:disk) %(rest)"', summed by path. If
  data/ falls below half of the bytes, the data-led attribution is wrong.
  (b) After the nightly macro-git-store-maintenance timer has run for a week, compare
  'du -sk /opt/macro/.git' day over day. If the store grows much faster than about 0.63 GiB a
  day, fetch packs are escaping the repack and the residue, not the history, is the driver.
  If it grows much slower, the rate here is wrong.
  (c) If 'git count-objects -v' after a nightly run is far above the walk count, unreachable
  objects are piling up and the "all reachable" reading no longer holds.
so_what: >
  Repacking cannot bound this store any more. It keeps the fetch-pack residue off the disk,
  but the reachable history alone fills about 0.63 GiB a day, which is roughly 18 days of
  runway at 18.4 GiB free. Ending the growth takes a change to how data artifacts are
  published: keep data/baskets, data/yahoo and the China stock trees out of main's history
  (object storage, or an orphan branch force-pushed with one commit per refresh), shard the
  outbox JSONL, and stop committing mockups/ and the generated CI file. Re-shallowing the clone
  is not a way out: MO-A-F04 forbids changing its depth, and issuer qualification calls
  'git merge-base --is-ancestor' from manifest code versions
  (engine/company_intelligence/issuer_disclosure_owner.py:369). That choice belongs to the
  operator and is set out in DEC:VPS-MACRO-GIT-STORE-KEPT-TIER-NIGHTLY-REPACK-AND-PULL-GUARD.
  Capacity planning on this host should now use the reachable-history rate, not the render
  cadence.
related:
  - "DSC:VPS-PULL-CLONE-GROWS-ONE-92MB-PACK-PER-SITE-RENDER"
  - "DSC:SMALL-FETCH-SKIPS-PACKED-OBJECTS-SO-A-PACK-SWAP-NEEDS-A-RESCUE"
  - "DSC:PACK-OBJECTS-OFF-FILESYSTEM-NEEDS-GIT-OBJECT-DIRECTORY"
  - "DSC:VPS-MACRO-STORE-REFILLED-ROOT-IN-12-DAYS-NIGHTLY-REPACK-NEVER-INSTALLED"
  - "DSC:VPS-MACRO-SHALLOW-ROOT-PINNED-BY-ISSUER-MANIFEST-CODE-VERSION"
  - "DEC:VPS-MACRO-GIT-STORE-KEPT-TIER-NIGHTLY-REPACK-AND-PULL-GUARD"
  - "WS:MARKET-OS"
---

Twelve days after the 2026-10-19 reclaim, the production droplet's root disk was nearly full
again, with 32.1 GiB in the `/opt/macro` pull clone. Two incremental consolidations on
2026-11-01 brought the store to 14.9 GiB and root to 18.4 GiB free.

The earlier record attributed growth to full-site render commits, each landing as a pack of
about 92 MB. That is the size of the incoming fetch pack. Once the store is repacked, renders
delta well, and site/ is only 13% of what the 1,932 commits since 10-19 added.

What stays is data. Nearly three quarters of the new bytes sit under `data/`. The biggest
share comes from per-symbol trees that every refresh rewrites: `data/baskets` and
`data/yahoo` alone hold 3.3 GB. All of it is reachable from `main`, so the nightly repack
cannot reclaim it. At about 0.63 GiB a day, the pull reaches its free-space floor around
2026-11-19 unless the way these artifacts are published changes.
