---
key: A-RUNNER-CHECKOUT-IS-87-PERCENT-GIT-STORE-SO-SPARSENESS-CANNOT-REACH-IT
claim: >
  The four self-hosted GitHub Actions runners on this host hold **177.26 GiB** in their `_work`
  trees — `actions-runner-2` 85.10, `-3` 68.18, `-4` 15.84, and the original 8.14 — and
  essentially all of it is one repo checkout each (`_work/macro/macro`). **87% of a runner checkout
  is `.git`, not the working tree.** Measured on the idle runner-3: checkout 66.34 GiB of which
  `.git` is **57.70** and the working tree only 8.6; inside `.git/objects`, **136 pack files
  totalling 57.20 GiB** against just 0.47 GiB of loose objects, largest pack 27.49 GiB.
  `actions-runner-2` holds **two** base-size packs — 31.63 + 28.61 GiB — i.e. two independent
  copies of the same history in one store. `_temp` is **0.00 GiB** on both, so the runners already
  clean the thing people assume is the problem. **This bounds what the R8 sparse-worktree program
  can achieve here to 12%:** its omitted set on that checkout is `data` 4.62 + `mockups` 1.98 +
  `site` 1.30 + `verify_shots` 0.12 = 8.02 GiB of 66.34. The lever is store maintenance
  (`git gc`/repack, or re-cloning blobless), and it is an **OPERATOR act, not a session's** — a
  `Runner.Worker` was live on runner-2 during measurement, repacking a store mid-job can break the
  job, and an aggressive repack on a 4-core box directly contends with the nightly, where the
  ~67-minute render budget is law.
falsifier: >
  `du -sxk /Users/chriswong/actions-runner*/_work` gives 83.91/66.76/14.67/5.77 GiB;
  `du -sxk …/actions-runner-3/_work/macro/macro/.git` = 57.70 GiB against 66.34 for the checkout;
  `ls -1 …/.git/objects/pack/*.pack | wc -l` = 136 and `du -sxk …/objects/pack` = 57.20 GiB while
  a `find`+`stat` sum over the non-pack object dirs totals 0.47 GiB;
  `find /Users/chriswong/actions-runner* -name '*.pack' -size +8G` returns exactly three packs,
  two of them in runner-2 (31.63 and 28.61 GiB); `pgrep -fl Runner.Worker` showed a live worker on
  runner-2. Disproved by a runner whose `.git` is a minority of its checkout, by `_temp` growing
  (which would mean the runner's own cleanup regressed and is then the cheaper fix), or after any
  repack — the numbers are a snapshot of an unmaintained store and must be re-measured, not cited
  forward.
so_what: >
  **The ENOSPC remediation program was aimed at the wrong bytes.** Sparse worktrees (R8), worktree
  GC, roots widening and population caps all target agent WORKING TREES, and R8's own measurement
  is that `data`/`site`/`mockups`/`verify_shots` are 87% of a worktree — but on a runner the same
  87% is `.git`, so the identical ratio points the opposite way and the sparse lever reaches 12%.
  Meanwhile 177.26 GiB of runner stores is **more than 3× the entire fleet worktree footprint on
  `/Volumes/Worktrees` (51.85 GiB)** and sits on the volume that actually crashed twice. Before
  proposing any further §9 storage work, attribute the target volume and check whether the bytes
  are tree or store. Second: **do not run the repack yourself.** Hand the operator a bounded,
  reversible act — `git gc` on an idle runner's store while its listener is drained, runner-2 first
  since it holds the duplicate base pack — and note that nothing is lost either way, because a
  runner store is 100% re-fetchable from `origin`. Third: this is the one pool in the whole triage
  with a real lever; `/Volumes/Worktrees` (93.5% operator data, ~5.4 GiB reachable) and
  `/private/tmp/claude-501` (160.43 GiB, 0.02 GiB provably dead,
  `DSC:A-SCRATCHPADS-KEYED-CHECKOUT-CAN-BE-GONE-WHILE-ITS-SESSION-IS-LIVE`) are both null, so this
  is where to spend operator attention.
kind: constraint
verified_at: 2026-09-28
verified_by: >
  `du -sxk /Users/chriswong/actions-runner{,-2,-3,-4}` (177.26 GiB total) and `…/_work/*`
  per-child (macro 83.29/66.34, `_temp` 0.00, `_tool` 0.18/0.00, `_actions` 0.01/0.00);
  `du -sxk …/actions-runner-3/_work/macro/macro/.git` 57.70 vs checkout 66.34, and its non-`.git`
  children (data 4.62, mockups 1.98, site 1.30, research 0.28, verify_shots 0.12);
  `ls -lS …/objects/pack/*.pack` + count (136 packs, 27.49 GiB largest) and
  `du -sxk …/objects/pack` 57.20 vs 0.47 GiB loose over 6,332 files;
  `find … -name '*.pack' -size +8G` (runner-2: 31.63 + 28.61 GiB);
  `pgrep -fl 'Runner.Worker|Runner.Listener'` (live worker on runner-2, listeners on all four);
  internal-volume census receipt scratchpad/internal_census.json
scope:
  - macro
  - research/WORKTREE_GC_POLICY.md
  - config/sparse_worktree.json
  - scripts/worktree_gc.py
confidence: verified
---
