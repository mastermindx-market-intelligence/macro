---
key: CI-PROMISOR-OBJECT-FETCH-TRUNCATION
claim: >
  A hosted ci-pack checkout that dies with "could not fetch <oid> from promisor
  remote" right after "N bytes of body are still expected / fatal: early EOF /
  fetch-pack: invalid index-pack output" is a truncated single-HTTP-response
  lazy fetch of the whole tree's blobs — the price of `filter: blob:none` on a
  job that then materialises every tracked file — and the OID it names is only
  the first index entry of the failed batch, never a corrupt object.
falsifier: >
  A failing pack checkout whose named OID is not the first blob line of
  `git ls-tree -r <tested sha>`; or whose "Checking out the ref" step died well
  under an hour; or `git cat-file -t` / `-s` of the named OID in a full clone
  reporting it missing or at a size other than the tree's — any one of those
  means a different defect than this record describes.
so_what: >
  Do not chase the named object and do not reopen the PR's own code: read the
  checkout step's duration (65–67 min = the transfer window), accept the ship
  loop guard's `missing_pack_fragment` verdict as correct infrastructure
  ambiguity, rerun the failed job (`gh run rerun <id> --failed`), and keep the
  hosted pack checkout UNFILTERED — `fetch-depth: 1` with no `filter:` — so the
  blob transfer sits inside actions/checkout's retried `git fetch` rather than
  in an unretried, unresumable promisor request issued by `git checkout`.
kind: landmine
verified_at: 2026-09-23
verified_by: >
  Job logs 107238846125 / 107264966712 / 107267933408 (runs 35876013221
  ci-pack-0 PR #7829, 35885173966 ci-pack-4 PR #7830, 35886408213 ci-pack-11
  PR #7825): `git checkout --progress --force <sha>` ran 66m21s, 67m23s and
  65m30s before the disconnect (25,719 / 35,379 / 27,331 bytes of the current
  chunk still expected), while the healthy rerun of ci-pack-0 checked out in
  9m10s. `git ls-tree -r origin/main | head -1` = 20ced73508fe
  .agents/skills/macro-sparse-worktree/SKILL.md, 2,349 bytes, unchanged since
  69268b06 (2026-08-23), readable locally. git promisor-remote.c
  promisor_remote_get_direct() dies on the FIRST still-missing promisor OID
  after try_promisor_remotes() fails; actions/checkout v4 wraps fetch() in
  RetryHelper(3, 10, 20) but runs checkout() once. Tree at origin/main: 105,301
  blobs, ~5.1 GiB of working files (data/ 3.62 GiB, site/ 0.99 GiB).
scope:
  - macro
  - .github/workflows/ci.yml
  - scripts/run_ci_pack.py
  - tests/test_ci_pack.py
  - tests/test_ci_pack_semantic.py
confidence: verified
---

## Mechanism

1. The hosted pack checkout fetched `--filter=blob:none --depth=1 <tested sha>`
   (commit + all trees, ~1 s), then `git checkout --progress --force <sha>`.
2. In a partial clone, checkout's `prefetch_cache_entries` asks the promisor
   remote for every missing blob in one child process:
   `git -c fetch.negotiationAlgorithm=noop fetch origin --no-tags
   --no-write-fetch-head --recurse-submodules=no --filter=blob:none --stdin`
   with the full OID list on stdin — every blob of the tree, as explicit wants,
   in one HTTP response, with no resume and no retry.
3. When that response is cut (all three receipts: ~66 minutes in, mid-chunk),
   `try_promisor_remotes()` fails, `promisor_remote_get_direct()` scans the
   remaining OIDs in index order and dies on the first one that is a promisor
   object. Index order is path order, and `.agents/` sorts first, so the object
   named is always `.agents/skills/macro-sparse-worktree/SKILL.md` until a path
   sorts before it — the name carries zero information about corruption.
4. The job's semantic fragment is never written, so `upload-artifact` warns
   `No files were found … ci-semantic-fragments/pack-N.json` and
   `ship_loop_guard.py` classifies the head `missing_pack_fragment`.

## Why the filter was worthless on this job

`test_ci_pack_partial_clone_keeps_history_without_historical_site_blobs`
records that packs need the whole current tree (legacy suites inspect committed
`site/` artifacts) and must not be sparse. Every blob is therefore downloaded
either way; `blob:none` only decided WHICH request carried them. In `git fetch`
the transfer is a normal single-commit want the server packs from reachability,
and actions/checkout retries the command three times. In the lazy path it is a
105k-entry explicit want-list served once, unretried.

## Mitigation shipped

The pack checkout keeps `fetch-depth: 1` and drops `filter: blob:none`
(PR: `claude/ci-pack-checkout-unfiltered-fetch-20260923`). The ci-plan job,
the fence packs and the one-file semantic-law checkout keep their filters — they
pair it with a sparse checkout, so it genuinely saves bytes there.
`scripts/run_ci_pack.py::_hydrate_exact_base_objects` already returns early when
no promisor remote is configured (pinned by
`test_base_replay_hydration_is_a_noop_without_a_promisor_remote`), and the
exact-base `git fetch --depth=1 origin <base>` brings the base's differing blobs
in a full clone.
