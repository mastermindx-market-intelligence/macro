# Original Fabric new-Macro sparse-workspace contract

**Prepared:** 2026-10-14; corrected 2026-10-15. **State:** reviewed source / opt-in / **not installed on the live Ubuntu host clones until the original Fabric owner records a per-host install**. This describes the existing Macro worktree creator's new narrow API, not a new worktree lifecycle or authority.

## Why this path exists

Two real Ubuntu0 GLM frontier tasks, `dataos-p05-1` and `dataos-p06-1`, started under original Fabric with `cwd=~/lanes/repos/macro`. Each later created a full `~/lanes/wt/<run-id>` Macro checkout of roughly 10 GiB, even though most work did not need tracked generated data, mockups or site assets. The tasks finished, but their original branch HEADs were not locally remote-contained; those checkouts **were not deleted**. A global after-the-fact sparse hook would risk rewriting incumbent/resumed work.

Macro already owns `scripts/worktree_sparse.py` and `config/sparse_worktree.json`. This PR only adds a deliberately narrow opt-in extension.

## Macro-owned API

```sh
# Only when the original Fabric transaction has already admitted a truly NEW
# task/workspace, obtained its provider and physical host lease, and pinned a
# donor Git commit from an authorized source:
MASTERMIND_FABRIC_SPARSE_NEW=1 \
  python3 scripts/worktree_sparse.py fabric-mint "$ORIGINAL_RUN_ID" "$PINNED_COMMIT_SHA40"
```

`fabric-mint` validates a bounded run-ID leaf, a lowercase 40-hex commit present in the original donor repository, an exact immediate `~/lanes/wt/<run>` checkout root and explicit flag `1`. It invokes the incumbent `mint_session_worktree(..., fetch=False, reuse_existing=False, strict=True)`. The original minter does **`git worktree add --no-checkout` before sparse materialization**. It refuses an existing destination/branch and does not silently adopt old worktrees; all heavy-directory `add/full` opt-ins still work.

**It has no authority to request a worker, authenticate a provider, choose a host, acquire a lease, change Git history or remove an old checkout.** An arbitrary model prompt, globally exported environment flag or unqualified direct CLI use must never become a new-workspace grant.

## Existing original Fabric launch integration candidate

The existing M2 Fabric `fabric_task.py` → `remote_sub.sh` → immutable host `remote_sub_exec.py` is the original execution owner. The single deployment candidate is the combined sparse-workspace + CPU-scope patch in Mastermind [PR #1404](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1404): [`FABRIC_COMBINED_SPARSE_AND_CPU_SCOPE_20261015.patch`](https://github.com/mastermindx-market-intelligence/Mastermind/blob/sol/ubuntu-thermal-headroom-20261013/integrations/fleet/ubuntu_thermal_headroom_20261013/FABRIC_COMBINED_SPARSE_AND_CPU_SCOPE_20261015.patch) (SHA-256 `a610dea2dffba37f45c74506592f3044cbfb10104ce568c7e346b143224fdff8`, Git blob `6b89b304e6d8aac465b4a5b69d53bc15840c3a46`). It pins this helper's Git blob below. The earlier `FABRIC_SPARSE_PRELAUNCH_CANDIDATE_20261014.patch` is superseded and must not be applied separately.

That candidate adds explicit `--new-macro-worktree <SHA40>`, restricts mode/Ubuntu host and requires original root/parent and donor Macro CWD. **Only after** the existing physical `LaneLease.acquire` succeeds does it invoke this exact Macro helper, checking its pinned code blob, original run identity, nonexistence of the checkout, verified lease and expected source SHA. It then checks actual resulting `HEAD`, `lane/<run>` branch, sparse enabled, clean Git, original worktree registry and donor Git metadata before changing the **new worker process's** CWD. Normal requests retain their historical arguments and startup.

A mint subprocess error, timeout, missing result, mismatched hash or unverified checkout is an original-carrier **effect-unknown** hold once creation may have begun, **not permission to retry**. Existing worker processes and source do not get the opt-in flag.

## Test and publication separation

- Source file `scripts/worktree_sparse.py` Git blob `75297acb10d0cef4d01730a59fdcad19c7cfd3e6` (supersedes `620927823770362b5c1d1e0dec6584612624d848`, which lacked the sparse-rule guard); test file `tests/test_fabric_lane_sparse_root.py` blob `e8a194c31d582d0e3fba0d29cee6d1116f464054`.
- `auto_profile` now fails closed (rc 1, no rewrite) when `core.sparseCheckout=true` but `git sparse-checkout list` returns no rules. This applies to **every** session worktree, not only Fabric lanes; a git timeout or lock on that probe is reported the same way.
- Thirteen added isolated Git tests plus original safety suites: **105 passed** on Ubuntu3. Includes strict pinned-commit creation, old checkout preservation, no duplicate mint, invalid/missing source and branch refusal, and the inconsistent-sparse-state refusal.
- A failed mint after `git worktree add` removes the new checkout but leaves the `lane/<run>` branch; with the no-retry rule that branch is reconciliation evidence, not something to re-mint over.
- The separate original Fabric candidate passed six standalone real-Git/mock-lease tests and controller mock-routing tests; **no paid worker was dispatched**.
- A mechanical compatibility test applied the existing Mac external-SSD draft #6939 source patch to an isolated copy of this helper using zero-fuzz hunks; **105 tests passed** there as well (re-run against blob `75297acb`). This is not source-owner signoff for #6939.
- The branch's earlier hosted CI failure came from an inherited absolute-path prune test in an SNI safety suite and an unrelated artifact DNS failure; current Macro main now uses `path.relative_to(SNI_ROOT).parts`, the correct scoped predicate. Full current-head CI must re-run and be accepted; do not waive it.

## Actual release requirements

A production adoption requires the original Fabric owner to install/reconcile this reviewed Macro helper on the selected Linux host's donor repository (without force-resetting an active source clone), to enable the original immutable launch candidate behind an explicit authorized flag, and to prove an **actual new paid worker** has a thin sparse checkout *before START* and returns on the same original lease/root/parent. Review both PRs' actual latest CI. No backfill or sparse conversion of the previously blocked SNI worktrees is authorized by this specification.

No BIOS or CPU power-policy action is included here: Ubuntu2/3's physical 9950X thermal-limit maintenance remains an independently attended host action.
