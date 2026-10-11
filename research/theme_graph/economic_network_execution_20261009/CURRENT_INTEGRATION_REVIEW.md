# PR #8667 — independent current integration review

Review date: 2026-10-09 UTC. Reviewer: `/root/current_integration_review`.

## Verdict

**Composition review: PASS for the exact tested merge below. Native release freshness: NOT PASS at the observed snapshot.** The application source, both test suites, all 68 declared candidate dependencies, and the 22 nonshared owned files survive the current merge unchanged. Both shared CI files preserve the entire accepted upstream content plus only this PR's already reviewed additions. No new application defect or material application dependency change was found.

The current hosted plan demonstrably tests the candidate against a newer main commit, but every current native proof anchor still names the older base. The existing release helper consequently returns `stale=True`. That live result supersedes the earlier inference that a source-preserving close/reopen would suffice. A bounded integration refresh through the incumbent authorized path is warranted once the current run concludes, followed by fresh head-bound checks and another actual freshness read. This review does not authorize a merge, change the controller, or claim that all checks have concluded.

## Exact objects and custody

| Object | Exact identity |
|---|---|
| Repository and PR | `mastermindx-market-intelligence/macro`, [#8667](https://github.com/mastermindx-market-intelligence/macro/pull/8667) |
| Canonical workspace inspected | `/Volumes/Mastermind/agent-workspaces/macro/web/gmi-economic-network-execution-20261009-pro-001` |
| Published source head reviewed | `037a23cf0fb232012bcb1a85f9cb714973782194` |
| Prior integrated source base | `94a20f53cdb2d866d07089df50567f059bf1073e` |
| Actual new plan base | `63245e035e2067f19ef9c75077dc920895b2eb17` |
| Actual tested synthetic merge | `51ef92908ec060f50194e485497f0d64e7f52a1b` |
| Independently read merge parents, in order | `63245e035e2067f19ef9c75077dc920895b2eb17`, `037a23cf0fb232012bcb1a85f9cb714973782194` |
| Fetched main available during composition review | `d28a9fbe913846bff7d72a503d3951618a8a5b86` |
| Hosted CI run | [37880934128](https://github.com/mastermindx-market-intelligence/macro/actions/runs/37880934128) |
| Plan schema and role | `ci.pack_plan.v2`; workflow `ci`; event `pull_request`; role `pr_head` |
| Canonical plan digest | `fa36020b49533d1c1b50686788b831115dd08bfe9438b94819a345e19aaf190c` |
| Raw downloaded plan SHA-256 | `216ff28c7f4a342229aef5c795ffe1d00e9af4157e98d6972bc3467ae113c230` |

The plan was read from the already downloaded native artifact at `/Users/chriswong/Library/Caches/Mastermind/economic-network-20261009/ci-plan-37880934128-1/ci-plan.json`. It reports 24 changed paths, `authority_changed=true`, active scope, 181 code-gate legacy jobs and 99 eligible selected jobs. Those counts are the plan's vocabulary; they are not a claim that the complete manifest contains only 181 definitions.

The candidate job is now in pack 9. Its executable identity remains `5ff9e1dd799a76ff34ad59e95d95cafbc10cea6c6f4cb58da6922bb28801ff6f`, and its test-step specification remains `a1222ca89024b1b434b98d3544d92a0171b5f5d8534a5cbfba63be0fb7d8d421`. The reviewed test command still runs the manual and pinned candidate suites. A pack assignment change is not a source change or proof of completed execution.

The canonical worktree was clean at the beginning and the final local composition read. The reviewer used existing Git objects and read-only GET helpers. The reviewer did not fetch, edit native source, create a worktree, commit, push, arm a label, dispatch CI, close/reopen a PR, invoke a reproof mutation, execute a pack locally, or merge. Root remains the sole source writer and owner of CI observation and delivery.

## Scope and byte preservation

The reviewed ownership set was reconstructed from the 21 paths in `pinned-final-integration.json`, plus the three paths introduced between `2a00eff6125d07cc2303b1edbafa00ba1d50d4a5` and the current head. The result is exactly 24 paths:

1. `.github/ci/legacy-jobs.yml`
2. `agentos/decisions/DEC-GMI-ECONOMIC-RELATIONSHIP-CANDIDATE-EXECUTION.md`
3. `engine/company_intelligence/pinned_relationship_candidates.py`
4. `engine/company_intelligence/relationship_candidates.py`
5. `research/theme_graph/economic_network_execution_20261009/CI_SCOPE_REPAIR.json`
6. `research/theme_graph/economic_network_execution_20261009/EXECUTION_COLLISION_REFRESH.md`
7. `research/theme_graph/economic_network_execution_20261009/EXECUTION_FRONTIER_ADJUDICATION.md`
8. `research/theme_graph/economic_network_execution_20261009/EXECUTION_STATUS.md`
9. `research/theme_graph/economic_network_execution_20261009/INDEPENDENT_REVIEW.md`
10. `research/theme_graph/economic_network_execution_20261009/MICRON_REPLAY_RECEIPT.json`
11. `research/theme_graph/economic_network_execution_20261009/MICRON_SOURCE_CASE.json`
12. `research/theme_graph/economic_network_execution_20261009/NATIVE_DATAOS_CONTRACT_REVIEW.md`
13. `research/theme_graph/economic_network_execution_20261009/NATIVE_SOURCE_ADAPTER_SEAM.md`
14. `research/theme_graph/economic_network_execution_20261009/PINNED_SOURCE_EXECUTION.md`
15. `research/theme_graph/economic_network_execution_20261009/PINNED_SOURCE_INDEPENDENT_REVIEW.md`
16. `research/theme_graph/economic_network_execution_20261009/PINNED_SOURCE_VERIFICATION.json`
17. `research/theme_graph/economic_network_execution_20261009/README.md`
18. `research/theme_graph/economic_network_execution_20261009/VERIFICATION_RECEIPT.json`
19. `research/theme_graph/economic_network_execution_20261009/replay_micron_witness.py`
20. `tests/test_company_pinned_relationship_candidates.py`
21. `tests/test_company_relationship_candidates.py`
22. `research/theme_graph/economic_network_execution_20261009/CI_INVENTORY_INDEPENDENT_REVIEW.md`
23. `research/theme_graph/economic_network_execution_20261009/CI_INVENTORY_REPAIR.json`
24. `tests/test_ci_pack.py`

Twenty-two of these files are byte-identical between the current source head and the actual tested merge. The only differences are the two shared CI files, whose new upstream additions were independently separated and verified below. The 68 dependency paths were read from the current job's explicit `paths` declaration, then compared using exact Git blob bytes. There are **zero changes across all 68 paths** both from source head to tested merge and from tested base to fetched main `d28a9fbe`.

The new inventory patch itself consists of exactly two explanatory comments and the single `"company-relationship-candidates",` entry. No assertion, ceiling, selection logic, or incumbent inventory member is deleted or weakened.

### Shared manifest

The current head contains the prior upstream manifest followed by this PR's exact 3,818-byte addition. Its SHA-256 is `a82338f3851cfa30b9f4e79be8ef076d753d0fdf8af78ea33a6cd8e327808eaa`. The exact addition occurs once in the tested merge. Removing that byte sequence, including its two leading separator newlines, reproduces the tested-base manifest **byte-for-byte**.

The manifest was also parsed independently. Every upstream job and its entire parsed specification is preserved. The only extra job compared with the tested base is `company-relationship-candidates`; its entire specification is identical to the reviewed head. These two checks establish both byte preservation and semantic job preservation.

A preliminary regex extraction omitted the two separator newlines and therefore did not reproduce the upstream byte stream. That was an extraction-boundary issue, not a merge defect. The final exact original addition comparison above resolved it; the 3,818-byte authoritative addition digest matches the previously sealed repair evidence.

### Shared curated inventory test

Removing this exact three-line insertion once from the tested merge reproduces the tested-base `tests/test_ci_pack.py` **byte-for-byte**:

```python
    # 2026-10-09 PR #8667: file and pinned-source relationship inspection.
    # Register the reviewed 68-path owner; closure audits and ceilings stay fixed.
    "company-relationship-candidates",
```

Upstream's International additions remain intact, including the curated entries for `itr-turn-rotation`, `international-workspace-pure-js`, `international-workspace-foundation`, and `international-workspace-browser`.

### Important verified digests

| Path | SHA-256 / scope |
|---|---|
| `engine/company_intelligence/relationship_candidates.py` | `27543f4a37202820f34071607b5cbdb1e48a04c30577a876ba1f803e1c41891d`; unchanged in tested merge |
| `engine/company_intelligence/pinned_relationship_candidates.py` | `1000497dcfef316f1ad0726c08bcba7ba12dbe305175887e191d6f96512649bd`; unchanged in tested merge |
| `tests/test_company_relationship_candidates.py` | `0a8c73d5e5b968fd3795fed1e08305597f9c254cc5702b9946b702b8f31bdbd4`; unchanged in tested merge |
| `tests/test_company_pinned_relationship_candidates.py` | `3c85ace77022c2b37c8abfab915ae8bf97ee711a8f315ea9e3b6f27d01872406`; unchanged in tested merge |
| `AGENTS.md` | `463ea7c70ea9a1ddbb5154b9f65b7c745d0093dc15485db216936fa9bddf057c`; head and tested merge |
| `CLAUDE.md` | `3c2016ddb9a67a6488f7938e665cb5f37b767b7d39c2122057cb9d110149d329`; head and tested merge |
| `scripts/merge_on_green.py` | `8eac1e841a5508605f4dceec014bffb05fa2a012d830607dfd2a240882bc7423`; head and tested merge |
| `scripts/run_ci_pack.py` | `65564916a55eb806d3d9fb0cd4e12726f05fec953f6e47ccd9240f5a141049df`; head and tested merge |
| `tests/test_ci_pack.py`, source head | `c7fc028a53f58f6a9310cb874c535dee1fa1556b211691ea4bf5c873fae41357` |
| `tests/test_ci_pack.py`, tested merge | `96582f4ef8db62c68c550e6f3bfd51c3847f564f16ec8987fe7c3b32acb1ca70`; upstream additions independently preserved |
| `CI_INVENTORY_INDEPENDENT_REVIEW.md` | `48337b90b80d4fd3fe19ed1db38ddcb6489ed1a7778d186d7169f90e1ab6fa0f`; unchanged in tested merge |
| `CI_INVENTORY_REPAIR.json` | `9f345dce71f416445fdd0fb1aeb2808ddb6fdfa4f6b8246eb93e310abbeb4cc3`; unchanged in tested merge |

The file lists under `.github`, `scripts`, `AGENTS.md`, and `CLAUDE.md` were compared from the old base to the tested base. The only changed `.github` path is the existing legacy job manifest. No workflow, release helper, CI selector, `AGENTS.md`, or `CLAUDE.md` changed. The two changed scripts are `scripts/build_international_macro.py` and `scripts/build_intl.py`; neither belongs to the 68 candidate dependencies. The same control/path comparison from tested base to `d28a9fbe` is empty.

## Accepted upstream changes and their consequences

Main added three code jobs: `international-workspace-browser`, `international-workspace-foundation`, and `international-workspace-pure-js`. Main also changed seven existing job specifications. These are accepted upstream changes, not changes authored by this PR.

| Existing job | Upstream change | Command effect |
|---|---|---|
| `biocatalyst-serving` | 27 explicit paths added | Commands unchanged |
| `dashboard-render-contract` | 3 explicit paths added | Commands unchanged |
| `intelligence-registry` | 20 explicit paths added | Commands unchanged |
| `itr-turn-rotation` | 235 explicit paths added; scope becomes `exclusive` | Commands unchanged |
| `nw-lobe-unfreeze` | 44 explicit paths added | Commands unchanged |
| `nyse-calendar-freshness` | 1 path and 1 named test added | Adds `tests/test_jpx_exchange_notice.py` to the existing calendar pytest command; other steps unchanged |
| `unrun-picks-boards` | 2 explicit paths added | Commands unchanged |

None of the seven jobs loses a declared path or changes its gate. The three new jobs and ITR scope change explain the new inventory additions. Their preservation is verified; this review does not re-adjudicate those owners' implementation. The changed gate definitions are material to *integration proof*: they cannot be dismissed merely because the application dependency closure is unchanged. The fresh hosted plan and packing check must use the combined manifest, and the native release protocol must recognize a current proof base.

The sole commit between the tested base and the fetched `d28a9fbe` tip is `render-public: public pages + asset stamps`. It changes 5,827 paths. All are under `site/` or `data/` except `templates/about.html` and `templates/index.html`. The complete diffs of both templates each change only the `onboard.js` version token, `c3718f20` to `2ffdd9bd`; no template structure or application behavior was edited in those files.

At 04:01:48 UTC the existing native `files_of(d28a9fbe)` returned one pipeline sentinel, `truncated=False`, and zero paths outside its `data/` and `site/` pipeline trees. Its existing large-tree/template-stamp handling can therefore classify this render bake. The separate `sha_is_skip_ci_tick(d28a9fbe)` returned `False` because the message has no literal `[skip ci]` marker. That method is a marker check used for a different retry boundary; its `False` result is **not** an independent freshness failure. The decisive stale result described next crosses the earlier `63245e03` product/CI-definition change.

## Live native freshness discrepancy

At **03:57:23.461910 UTC**, existing GET-only native helpers produced:

```json
{
  "head": "037a23cf0fb232012bcb1a85f9cb714973782194",
  "pull_base": "94a20f53cdb2d866d07089df50567f059bf1073e",
  "merge_sha": "51ef92908ec060f50194e485497f0d64e7f52a1b",
  "snapshot_tip": "d28a9fbe913846bff7d72a503d3951618a8a5b86",
  "proof_base": "94a20f53cdb2d866d07089df50567f059bf1073e",
  "stale": true,
  "stale_detail": "main commit 63245e035e20 changed too many files to list, so it cannot be shown to be outside the surface",
  "baseline": "green",
  "baseline_detail": "63245e035e20 https://github.com/mastermindx-market-intelligence/macro/actions/runs/37880802935"
}
```

The reviewer subsequently read the exact native anchor associations. All 16 proof anchors available then identify the current head `037a23cf` and old base `94a20f53`. They include all 12 pack jobs of **the new run 37880934128**, plus the fence anchors. This is not an old-head check accidentally selected. Examples:

| Anchor | Check/job ID | Association base |
|---|---|---|
| `ci-pack-0` | `113660860059` | `94a20f53cdb2d866d07089df50567f059bf1073e` |
| `ci-pack-9` | `113660860099` | Same old base |
| `ci-pack-11` | `113660860273` | Same old base |
| `fence-pack` | `113660220861` | Same old base |
| `self-mod-fence` | `113660462375` | Same old base |
| `capability-broker` | `113660464666` | Same old base |
| `grader-manifest` | `113660467340` | Same old base |

By contrast, the actual CI plan and immutable merge parents identify base `63245e03`. Both facts are retained. The reviewer did not rewrite the pull payload, substitute plan metadata into check objects, monkeypatch the helper, or treat the narrower 68-path comparison as authority to override the full workflow surface.

The helper's `exact_proof_base()` explicitly takes bases from the repository-owned check associations. Its `stale_for()` explicitly treats a truncated product change or changed CI definitions after that base as stale. The observed result is therefore consistent with the current helper's implementation, even though it differs from what the actual tested merge proves about composition. This review does not assign the underlying metadata behavior to a confirmed GitHub defect; it establishes the discrepancy and its operational effect.

At the freshness snapshot, 12 packs remained in progress. `contract-delta`, the active `ci-authority/main`, plan, and fences had passed. The complementary pilot authority context was red and inactive under the already reviewed main-target rule. Root owns the final complete check census and must not use this partial snapshot as a merge verdict.

A later GET-only helper build at **04:01:48 UTC** observed main tip `4fd2d0e2b2fb0eeb5d98222e01c4a8b36d9e9396`. The reviewer did not fetch or assess that new commit. All composition conclusions here are explicitly bounded to the fetched `d28a9fbe` objects; a final premerge freshness and integration read remains necessary.

## Required next integration action and limits

The repository already supplies the relevant mechanism. `reprove()` states that `update-branch` merges main into the head, makes the new head unproven, and returns it to fresh CI. `attempt_update_branch()` supplies the controller's authorization, workload, and lease admission. Existing fixtures `test_a_stale_base_is_updated_instead_of_blocked` and `test_an_exact_proof_base_does_not_reprove_its_own_definition_commit` pin the expected-head update and the refreshed-base condition that terminates a reproof cycle.

No declared source-preserving mechanism was found that promises to refresh these association bases. A real synchronize has now produced a new tested merge and plan while retaining the old associations. That observation does not prove that close/reopen can never change them, but it removes the evidentiary basis for relying on that inferred path to satisfy the native guard. Ordinary reruns also do not provide a reliable new merge composition or anchor contract. The prudent authorized continuation is the existing integration/update path, with exact old/new head custody and fresh proof.

This is **not** a recommendation to invoke `reprove()` directly on the current unarmed PR. Its underlying gateway requires a live arm and a serialized sweep budget, and may require the incumbent refresh lease. Those cannot be fabricated or bypassed. Root should use the authorized owner integration path or the properly admitted incumbent update mechanism. Root should preserve the current run's concluded result before creating another run; no shared CI cancellation is warranted.

The concrete reason for another integration is the native `stale=True` evidence and actual changed CI definitions, including three new jobs and the calendar command addition. It is not a behind-count preference. The source owner can retain the accepted application review because the relevant source and 68 dependencies are unchanged. After integration, the narrow review obligation is to confirm the exact new merge/base/head, preserve these 22 nonshared owned files and both owned CI additions, preserve accepted upstream files, and obtain current native check associations plus a concluded fresh gate. If any dependency or owned application bytes change, reopen that specific review scope.

If fresh integration still leaves contradictory old association bases, stop the loop and record the actual protocol failure for its incumbent owner. Do not fabricate another source edit, relax the gate, repeatedly close/reopen, or change shared release code to force this PR through.

## Research and production boundaries

This is a source integration review, not new source acquisition, native runtime publication, semantic fact admission, identity resolution, historical eligibility, licensing authorization, or predictive validation. The source inspectors remain inspectable/non-admitted. The missing real retained native source pin/reader and the owner-controlled fact, dataset, time, identity, rights, and product admission steps remain unchanged. The project-wide mission is still incomplete even after a future successful source merge.

## Reproduction outline

Use the exact already available Git objects above and read-only operations:

1. Read the native downloaded plan and hash its exact bytes; inspect `subject_head_sha`, `base_sha`, `tested_tree_sha`, and the candidate semantic job entry.
2. Read `git show -s --format=%P 51ef92908ec060f50194e485497f0d64e7f52a1b` and compare both parents exactly.
3. Reconstruct the 24 owned paths from `pinned-final-integration.json` plus the three current repair paths. Compare `git show REV:PATH` byte strings at source head and tested merge.
4. Parse the candidate's 68 explicit paths from the reviewed head manifest; compare all exact bytes head-to-merge and tested-base-to-fetched-main.
5. Subtract the exact original 3,818-byte appended job from the merged manifest; compare the result with the tested-base manifest. Compare all parsed upstream job specifications and the candidate job separately.
6. Remove the exact three inventory lines once from the merged test and compare with the tested-base test. Inspect upstream inventory additions and changed job field sets.
7. With existing authenticated read access, call only `ProofFreshness.build`, `head_check_runs`, `proof_anchor_runs`, `exact_proof_base`, `stale_for`, `integration_baseline_state`, and the read-only pipeline classification helper. Preserve their actual output without substituting metadata.

No new execution test was necessary for this read-only composition review: the accepted application bytes and test command are unchanged, the new inventory repair was independently reviewed before publication, and the current hosted run is the live integration proof under observation by root. The release-freshness issue is a real remaining gate, not a reason to rerun unrelated local suites.
