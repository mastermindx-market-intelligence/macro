# Native Macro producer — protected-main reconciliation candidate

## Problem and exact inputs

The existing [Macro #11258 release-controller receipt](https://github.com/mastermindx-market-intelligence/macro/pull/11258#issuecomment-6882061629) at 2026-11-14T18:15:46Z reports that every check concluded clean, but protected main changed the CI definitions and a real source conflict prevents the normal refresh. The existing release request remains armed.

This candidate reconciles exactly:

- Native producer owner: `5f464a227fd33799210bcfca294b8b63099d5c4a`, tree `6ca9d5f6b96657d14e7b546b59b717e347bd6bf3`.
- Protected main input: `bd7fc985d2de7112641b12d9a2a19c3ab9d3dd81`, tree `01c92373b84ac61488392b5ab4bc8894ee328c41`.
- Common source: `2cd28dc84c750303d1edce21c72137659663f976`.
- Governing Mastermind law: `199fd4f91ecc426b1d974eb3bf47f5162476cf24`.

The resulting commit uses the existing producer head as first parent and the protected main input as its second parent. Its tree begins with the complete protected main tree; the eighteen producer paths and this record are the only changes on that tree. This preserves every disjoint protected source/data change without enumerating or replaying them individually.

This is an **isolated, linked, non-releasing source candidate**, not a replacement release carrier for #11258. It does not advance the original branch, change either label, replay its opt-in, clear a hold, deploy or claim that stale CI is current.

## Writer custody

The exact owner commit names `mastermindxryan` as author and committer at 2026-11-14T15:44:48Z. Its [durable continuation record](https://github.com/mastermindx-market-intelligence/macro/blob/5f464a227fd33799210bcfca294b8b63099d5c4a/research/market_intelligence_productization/NATIVE_MACRO_EXPERIENCE_2026-11-14.md) retains the existing branch, GitHub carrier, exact-parent CAS and new-head checks. It provides no subsequent writer handoff. A partial/unjoined runtime observation provides no contrary PR/session/grant binding.

The writer therefore remains active/unknown. The original `sol/market-ontology-native-experience-20261114-c3` ref and its `merge-on-green` / `merge-blocked` labels are preserved. No external message, review request, new release request or alternate mutation carrier is used.

## Complete conflict census and minimal union

The GitHub owner-to-main comparison reaches the 300-file response limit, so it is not used as a complete conflict list. Instead, the exact common-source-to-owner comparison contains eight commits and all eighteen changed paths. Bounded Git tree reads resolve those paths in all three immutable inputs, including their modes.

Seventeen paths have unchanged protected-main preimages (or are still absent for owner additions) and retain the owner postimage exactly. The only both-changed path is `.github/ci/legacy-jobs.yml`; all existing modes agree. In particular, `app/deploy/update.sh` retains mode `100755`.

A real three-way `git merge-file` reports **one conflict**, at the workspace job's curated-path insertion point. The resolution retains:

- The owner's `engine/release_target_cohort.py` and `engine/release_target_truth.py`.
- Main's `engine/inflation_intelligence.py` and `engine/rates_command_basis.py`.
- The shared `pandas pyarrow` dependency suffix exactly once.
- All other owner and main CI changes, including main's two SI rotation checks and the owner's source-binding/payroll curated scopes.

Resolved CI blob: `e295205a2c4b0b58ffc926a5e6a733483a4aa6c3`.

Parsed YAML qualification preserves **all 402 job identities**. Twenty-nine jobs differ on the owner side, three on main, with only one overlap. Every single-side changed job is semantically identical to its source version; untouched jobs are identical to the common source. For the overlapping workspace job, all non-path fields are identical on both sides and in the result; the path list is the duplicate-free union. The existing eighteen-suite pytest command is unchanged. No test, required check, gate, workflow, runner, capacity rule or controller is removed or weakened.

| Producer path | Exact owner postimage | Candidate treatment |
| --- | --- | --- |
| `.github/ci/legacy-jobs.yml` | `25ff68e2a07a48113ef1f23d227ba89e9367ddd7` | Deliberate three-way union below |
| `app/deploy/update.sh` | `0ef889dec9c3fa69927fcf18c70d185feac8c500` | Exact owner blob retained |
| `engine/market_os/macro_workspaces/build.py` | `3a5abe636d4062fdb658da59f3a367f2589a23b0` | Exact owner blob retained |
| `engine/market_os/macro_workspaces/financial_conditions.py` | `534836f6a970fae6f68517d78623ca63ac7e14ef` | Exact owner blob retained |
| `engine/market_os/macro_workspaces/growth.py` | `6dafcc7a99c4857d43b2d7e8155551b9fd44fdae` | Exact owner blob retained |
| `engine/market_os/macro_workspaces/history.py` | `cc28c14ad32a08daf46a12fa613481001415c0d4` | Exact owner blob retained |
| `engine/market_os/macro_workspaces/labor.py` | `7953e90156711ae92935ec314532ef79053f173f` | Exact owner blob retained |
| `engine/market_os/macro_workspaces/liquidity_regime.py` | `d1cc8c4be4bb7956f5daaed2a86f07e9bfaa904d` | Exact owner blob retained |
| `engine/market_os/macro_workspaces/payroll_revision_sources.py` | `1b76e70c803a3cd31773eff053a1fa3e20f6c8ca` | Exact owner blob retained |
| `engine/market_os/macro_workspaces/payroll_revisions.py` | `571cd98948c75ae2635c653c3b99934a96b742f7` | Exact owner blob retained |
| `engine/market_os/macro_workspaces/source_bindings.py` | `e2dd974ab3c60b2767f884c9472ede95dd56daff` | Exact owner blob retained |
| `engine/release_cpi_target_history.py` | `6269133e294e021fed7d3e33b43ca2291a5356c7` | Exact owner blob retained |
| `engine/release_target_cohort.py` | `1b88b1d87588d1cc612ce5d93531944a28de2fc8` | Exact owner blob retained |
| `lib/macro_suite_labels.py` | `1687b76767b6c10a6c5869e07a3f19f218f6dae5` | Exact owner blob retained |
| `lib/macro_suite_view.py` | `e3d178ab60ff31ede68197ee14d3458d05e46a00` | Exact owner blob retained |
| `research/market_intelligence_productization/NATIVE_MACRO_EXPERIENCE_2026-11-14.md` | `a236aafad8a502bfc4fa6c14bc515b7883163f8b` | Exact owner blob retained |
| `tests/test_macro_suite_pages.py` | `01b13dece96b3cd393515e7f9c02d3a8c5add079` | Exact owner blob retained |
| `tests/test_macro_workspace_build.py` | `67964db9c18d96c832fb644a22eb027d8ece62ba` | Exact owner blob retained |

## Executed source and consumer qualification

The isolated source qualification uses all seventeen exact owner source postimages, the reconciled manifest, protected main's Inflation owner-publication regression, and exact protected source dependencies and committed workspace fixtures.

**216 distinct tests pass**, with one existing optional real-artifact test skipped because `data/release_forecast/inflation_intelligence.json` is absent. The passing tests cover the complete native workspace-build suite, suite-page/label/render checks and Inflation suite, including the new real owner-Parquet publication regressions.

Initial collection/render failures were caused by missing files in the sparse local qualification: the CLI builder, Release Target helper, page templates, committed workspace fixture tree and two shared-shell assets. Exact protected-source files were restored, byte-verified, and the affected checks rerun. The final full attempt passed 173 checks; the 43 fixture-dependent page checks then passed after the final two asset dependencies were restored. No test or fixture content was modified to make an assertion pass.

The qualification restores 54 explicit protected dependency/fixture inputs with Git blob verification. The committed `site/macrodata/workspaces` tree is the exact pinned main snapshot. It is not represented as a network-served publication, fresh data acquisition, or authenticated native browser proof. Other supporting imports remain from the previously verified source qualification; this is not a claim that a full repository checkout ran locally.

The manifest's real three-way merge and 402-job semantic preservation are independently checked from the source graph. Hosted CI on the eventual source accepted by the existing carrier must still run the current definitions and unchanged guards. A feature-base authority outcome must be honored rather than worked around.

## Existing accepted work and programme return

Protected [#11277](https://github.com/mastermindx-market-intelligence/macro/pull/11277) Inflation proof is already merged as `8b882407ff590a61a38c5a0257f00e15beb3fc5b`; this candidate preserves that work through protected ancestry and the CI union. It does not redo or release it again.

[Terminal #1533](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1533) and [Growth #1550](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1550) retain their separate source/consumer qualification. This backend reconciliation does not replace the native UI, its latest responsive evidence, or the current source/evidence writer lane. The independent Growth-date owner [#6969](https://github.com/mastermindx-market-intelligence/macro/pull/6969) also retains its admission/publication obligation and hold.

### Exact next action and acceptance

Resolve current writer custody before integrating this candidate into the original producer ref. Re-read original head, current protected main, labels, reviews/holds and controller effects. If the owner or relevant protected source moved, reconcile the exact deltas rather than overwrite them. Once current custody authorizes source integration, use the original GitHub carrier with an exact-head lease, preserve the original opt-in and let the existing controller consume fresh binding checks. No direct-main or second release route is authorized by this candidate.

Then continue the existing producer build/served-byte proof, protected selected-reader and canonical registry/export chain, final Terminal admission and authenticated deployed daily Macro → Economy → workspace → source → return journeys. The original daily risk/actions and full Market Ontology masterplan remain binding. **MORE_WORK_EXISTS**.
