---
key: GC-DISABLED-RUNNER-STORES-ACCUMULATE-EVERY-TRANSFER-PATHOLOGY-FOREVER
claim: >
  Every self-hosted runner clone on this host carries `gc.auto = 0`, and NO workflow and NO script
  in the repository performs any git maintenance on those stores. Nothing consolidates them, ever.
  Consequently each era's object-transfer behaviour accumulates permanently and independently:
  measured 2026-09-29 across the four `actions-runner*/_work/macro/macro` clones of THIS repo on
  one host, 141 GiB of pack data (of the 177.26 GiB those workspaces occupy), in two unrelated
  shapes. (1) PACK-COUNT pathology, pre-2026-09-23 blobless era: runner-1 holds **36,271** packs
  (36,271 of them `.promisor`) for only 5.3 GiB — one pack per lazy blob fetch, 145,084 files.
  (2) PACK-BYTES pathology, post-2026-09-23: the promisor-truncation fix removed `filter:
  blob:none` from the pack checkout, so every pack checkout now materialises the whole tree and
  writes a COMPLETE ~4.5 GiB blob pack. Measured directly: runner-4 wrote 4.53 GiB in 7 packs in
  one 00:01 burst on 09-29, 4.51 GiB of it a single pack — matching `ci.yml`'s own note that a
  pack materialises 105k blobs / ~5 GiB. Unconsolidated, that is per-checkout, not per-change:
  runner-2 = 72 GiB / 35 packs (two single packs of 28.61 and 31.63 GiB), runner-3 = 58 GiB /
  139 packs with **47.07 GiB written on 09-28 alone** against a 0.72-3.08 GiB/day baseline on the
  five days before it.
falsifier: >
  `grep -c 'auto = 0' <clone>/.git/config` on each of the four clones (expect 1 each), and
  `grep -rln 'repack\|gc --prune\|gc.auto' .github/workflows/ scripts/` (expect no git-maintenance
  hit; the only 2026-09-29 matches are 7 occurrences of the word "repackaged" in four unrelated
  engine scripts). If any clone self-gcs or any lane repacks these stores, this is false. Per-clone
  bytes: `du -sh <clone>/.git/objects/pack`; per-pack dates and sizes: `find <pack dir> -maxdepth 1
  -name '*.pack' -exec stat -f '%Sm %z' -t '%Y-%m-%d' {} \;`. Pack files are immutable once
  written, so pack mtime is creation time — this is the one place in this repo where an mtime gate
  is sound, and it is NOT subject to the observer-stamping that makes worktree file mtimes useless. BOUND IT THERE: a pack's mtime dates that pack's creation and
  nothing else. Reading "no pack dated today" as "this runner had no job today" is WRONG and
  was measured wrong on 2026-09-29 — `pgrep -f Runner.Worker` found a live worker on runner-2
  while its newest pack was dated the previous day. Pack dates measure file TRANSFERS; for
  "is this machine busy right now" ask the process table at the moment you act.
so_what: >
  **Do NOT "fix" this by restoring `filter: blob:none` to the pack checkout.** That filter was
  removed deliberately on 2026-09-23 (`DSC:CI-PROMISOR-OBJECT-FETCH-TRUNCATION`) because a blobless
  pack checkout lazily refetches the entire tree in ONE unretried, unresumable promisor request;
  three such requests died at 65-67 minutes (runs 35876013221, 35885173966, 35886408213). The
  storage cost measured here is the ACCEPTED PRICE of that correctness fix — the defect is not the
  price, it is that `gc.auto = 0` plus no maintenance lane means the price is charged on every
  checkout forever instead of once. The lever is therefore CONSOLIDATION, not re-filtering: these
  are 35-139 near-identical whole-tree snapshots, so cross-pack delta compression should collapse
  them toward a single tree's worth. Also note the general trap this is an instance of: a config
  difference that correlates perfectly with a cost difference is not thereby a misconfiguration —
  here the two cheap clones are cheap partly because they have served fewer unfiltered checkouts,
  and the expensive ones are expensive because they are doing the CORRECT thing more often. Reading
  the cheap side as "healthy" and the expensive side as "broken" produces a recommendation that
  reverts a correctness fix with three named production failures behind it.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  `du -sh`/`find`/`stat` over the four `actions-runner*/_work/macro/macro/.git/objects/pack`
  directories; `grep -c partialclonefilter` and `grep -c 'auto = 0'` over their `.git/config`;
  `.github/workflows/ci.yml` lines 4544-4550 (ci-plan `fetch-depth: 0`, "the blob:none filter keeps
  full history cheap") and 4905-4929 (packs, "NO `filter: blob:none` here — on purpose");
  `.github/workflows/earnings-public-wire.yml:47` (the same lazy-materialisation cost measured at
  13m09s in run 35020030398). `df -g /System/Volumes/Data` = 312 GiB free at 83%.
scope:
  - macro
  - .github/workflows/ci.yml
  - research/WORKTREE_GC_POLICY.md
confidence: verified
---

## The two pathologies are unrelated to each other and share one cause

| clone | `partialclonefilter` | packs | `.promisor` | pack bytes |
|---|---|---:|---:|---:|
| `actions-runner`   | `blob:none` | **36,271** | 36,271 | 5.3 GiB |
| `actions-runner-2` | absent | 35 | 0 | **72 GiB** |
| `actions-runner-3` | absent | 139 | 0 | **58 GiB** |
| `actions-runner-4` | `blob:none` | 47 | 46 | 5.7 GiB |

All four carry `gc.auto = 0`. The filter column looks like the explanation and is not: runner-4
*has* the filter and still wrote 4.53 GiB today, because an unfiltered fetch into a
filter-configured workspace still transfers everything. What actually separates the columns is how
many unfiltered pack checkouts each workspace has served since 2026-09-23 — and, for runner-1, how
many lazy promisor fetches it served before that date.

## The measuring trap that nearly hid it

`ls <pack dir>/*.pack | wc -l` reports **0** on runner-1 — not because there are no packs, but
because 36,271 paths overflow `ARG_MAX`, the glob fails, and `wc` counts an empty stream. Zero and
"too many to count" are the same reading. Use `find <dir> -maxdepth 1 -name '*.pack' | wc -l`,
which streams. This is the same family as the other storage-instrument failures recorded for this
host: the instrument answered a question about its own argument list, not about the disk.

## What is NOT a candidate

`actions-runner-3-repair-backup-20260814T2300Z` measures **24 KB** — a marker directory, not a
payload, exactly like `.ADSPOWER_GLOBAL` on the SSD. It should be struck from the reclaim
inventory rather than carried as an unknown.

Related: `DSC:CI-PROMISOR-OBJECT-FETCH-TRUNCATION` (why the filter is gone and must stay gone).
