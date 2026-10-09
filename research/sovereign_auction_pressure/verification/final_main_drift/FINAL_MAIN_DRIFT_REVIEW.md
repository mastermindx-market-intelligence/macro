# Final bounded main-drift and preservation review

## Disposition

**PASS for the exact supplied Macro and Mastermind revisions.** Neither latest upstream revision changes an owned path or an applicable AGENTS/CLAUDE instruction relative to the previously verified revision. Both prior-main and latest-main merge simulations are clean. The newer simulated integration preserves the same owned-path bytes as the earlier simulation and preserves all latest-upstream paths outside the owned scope.

This is a read-only source integration review. It does not execute a merge, certify all CI checks, or change the mission's Draft HOLD boundary.

## Exact revisions

| Repository | Original source base | Owned source head |
|---|---|---|
| Macro | `d2eec4732abee359ebb578b245fa7359b3c01a7d` | `1eb1d44a0a54aad95d97bfb3128246803852c7a7` |
| Mastermind | `c7e47c859eb2925c5626931fd511800773ba09ac` | `ac9117b3305ba992ebb673a99242cdd54e2046ef` |

| Repository | Previously verified upstream | Latest supplied upstream |
|---|---|---|
| Macro | `4cbc94c117c5b4eb84c666cc88336228f0ff00a6` | `e80339cb921ac6851ae972775f7e2d784bf62007` |
| Mastermind | `64e9016c90a561a2017d2f2fd2ff75368df7397a` | `732cf7be88e7159b4995a8885fbd381cd1484e3e` |

Root supplied these exact remote identities from its fresh readback. Every requested commit object was locally available; no fetch or later-ref lookup was necessary. Merge bases resolve exactly to the original source bases above. Terminal was unchanged in the supplied handoff and was outside this follow-up comparison.

## Scope and instruction drift

The owned scope is every path changed between each original source base and its supplied owned head, including implementation, tests, fixtures and recorded evidence. No new PR census was performed.

| Check | Macro | Mastermind |
|---|---:|---:|
| Owned paths compared | 265 | 101 |
| Owned paths changed by prior → latest upstream | **0** | **0** |
| Applicable AGENTS/CLAUDE candidate paths checked | 150 | 52 |
| Changed or newly present applicable instructions | **0** | **0** |
| Present applicable instructions | Root AGENTS and CLAUDE | Root AGENTS and CLAUDE |

Candidate instruction paths include every ancestor directory of an owned path. The root instructions retain their previously reviewed bytes; all narrower candidate instruction files remain absent in the compared upstream trees. Exact path entries, instruction candidates, Git blobs and root-law SHA256 values are retained in `macro_drift.json` and `mastermind_drift.json`.

## Non-writing merge simulation

For each repository, the review ran `git merge-tree --write-tree --name-only --messages` twice: once with the previously verified upstream and once with the latest supplied upstream, each against the exact owned head.

Git's generated objects were directed to a newly allocated temporary object directory outside the source workspace. The repository object store was an alternate read source. Lazy fetches and optional locks were disabled. The temporary directories were removed after inspection. No source object-store, ref, index or worktree write was performed, and no merge commit was created.

All four simulations returned exit code 0.

| Preservation assertion | Macro | Mastermind |
|---|---:|---:|
| Owned-path differences between prior and latest simulated integrations | **0** | **0** |
| Latest-upstream paths modified outside owned scope | **0** | **0** |
| Source-only owned paths preserved exactly | **264/264** | **101/101** |
| Shared paths with earlier upstream edits | `.github/workflows/daily.yml` | None |

The Macro shared workflow has exactly the previously reviewed Theme Graph additions when comparing the owned workflow to the latest simulated workflow: the regional builder's step ID and its advisory witness upload. The complete 1,918-byte diff is retained in `macro_preserved_theme_graph.diff`. It retains those upstream additions alongside the owned build_feeds order repair. Every other Macro owned path, including the DAG contract and capture source, is preserved exactly.

### Simulated tree identities

| Repository | Prior-upstream simulation | Latest-upstream simulation |
|---|---|---|
| Macro | `d9da0535ba2a1bc18dd2db5bf6218cf8064630a2` | `1ff9e693ced0e0eb65307a39a69d33cc6acd45ef` |
| Mastermind | `8070749d9b78f724108aca3f521d7cd06d6bcebc` | `8e8693fa8df40a9968e0e55cab053c8e20231e2d` |

These identities describe temporary simulation output, not committed or published source. Their raw command output and complete preservation assertions are in the two `*_merge_review.json` files.

## Boundary

No new source collision or preservation requirement appears in the supplied drift interval. The existing Theme Graph preservation requirement remains satisfied. This review is bound to the exact revisions above; it does not chase later upstream updates or replace root's real test and CI receipts. Root retains all source-write, final-head binding and Draft HOLD decisions.

