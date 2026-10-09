# Macro ci-pack-11: exact-head final CI triage

## Verdict

The source patch introduces a DAG registry order mismatch. Correct the existing daily engine lane in `config/dag.yml` to reflect the authorized relocation of the one existing `build_feeds` workflow step before the engine-output commit. A separate failure occurs while replaying the CI base because a test assumes that Git `origin` is a GitHub URL, whereas the replay uses a local repository path.

No source files, remotes, CI runs, settings, gates, or provider jobs were changed during this read-only triage.

## Exact execution identity

- Repository: `mastermindx-market-intelligence/macro`
- PR: `8657`
- Source head: `9ea66297a31688123ae62845c655a74db03fa9c1`
- Source branch base used for attribution: `d2eec4732abee359ebb578b245fa7359b3c01a7d`
- CI run: `37861101577`
- Job: `113597264930`, `ci-pack-11`
- Job result: completed / failure; started 2026-10-08T23:46:18Z, completed 2026-10-09T00:28:18Z.
- The job log identifies its tested merge as `1ce146dd4`, merging the exact source head into `b86c4ada64533320232a98278cf199978a369a92`.
- Full downloaded job-log SHA-256: `79cd52922d72e7bacb3a4e73ff4a5b28b1c34157b29e036b5a696aa4dcec971d`; size 323444 bytes. Only scoped excerpts are retained here.

## Source-owned failure and narrow remedy

Annotation: `legacy-job-dag-conformance` — step `DAG conformance check (hard — exits 1 on undeclared lane drift)` exited 1.

The exact error is a SERIAL ORDER MISMATCH in `.github/workflows/daily.yml / engine` at position 163. The declared serial sequence has `scripts.check_template_site_sync`; the live workflow has `scripts.build_feeds`. Both sequences have 167 serial entries and differ in the adjacent positions 163 and 164:

| Position | Declared DAG | Live workflow |
| --- | --- | --- |
| 162 | scripts.build_options_flow_attention | scripts.build_options_flow_attention |
| 163 | scripts.check_template_site_sync | scripts.build_feeds |
| 164 | scripts.build_feeds | scripts.check_template_site_sync |
| 165 | scripts.publish_r2 | scripts.publish_r2 |
| 166 | scripts.audit_r2 | scripts.audit_r2 |

The exact source diff moves the existing `assemble machine-consumable feeds (site/feeds -> R2)` step from after `commit engine outputs` to immediately before it. The step still has its existing fail-soft behavior. The added comment explains that the tracked event calendar must exist before the existing data/site commit, while retaining its nested source clocks.

At source head, `config/dag.yml` lines 1748–1750 hold the existing `id: build_feeds` block. Move that whole block immediately before `id: check_template_site_sync_fix` at line 1739. This makes it follow `build_options_flow_attention` and precede the commit helper's discovered template-sync invocation. Leave IDs, flags, checker behavior, existing divergences, and other execution order unchanged. No dependency or extra workflow step is needed for this observed mismatch.

The governing contract is stated in `config/dag.yml` meta: it is the workflow-step lane inventory and conformance against the live YAML is hard enforced. The exact source `.github/ci/legacy-jobs.yml` lines 5820–5823 supplies the verification commands:

```sh
python scripts/check_dag_conformance.py --verbose
python -m pytest tests/test_dag_conformance.py -q
```

No specific CODEOWNERS file or nested config AGENTS file exists at the exact source revision. Root retains the complete repository/mission laws and owns any authorized write.

## Separate CI base-replay failure

The replay reaches a passing DAG check: `DAG conformance OK — 27 lane(s) checked, 2 suspect drift(s) visible above.`

It later fails `tests/test_nightly_liveness.py::test_default_repo_matches_the_git_remote` at line 293. The test derives a repository slug from `git remote get-url origin`, then compares it with `DEFAULT_REPO`.

- Expected: `mastermindx-market-intelligence/macro`.
- Replay-derived actual value: `home/runner/work/_temp/ci-base-replay-ljznkr6m/origin`.
- Result: 1 failed, 79 passed; preceding nightly-liveness selftest passed.
- The log resets to the observed CI base `b86c4ada6` after this replay.

Attribution: replay infrastructure / test environment mismatch, separate from the auction change. It is not evidence that the auction code modified the fallback slug, test, or replay harness.

Exact source-base-to-head blob equality confirms these files were unchanged:

| File | Identical Git blob at source base and head |
| --- | --- |
| config/dag.yml | 68ca8883b6f09c64564f4f7904708684c3a55ee1 |
| tests/test_nightly_liveness.py | 38c41c161f9787c414e6051be7deee160c5a3f8d |
| scripts/check_nightly_liveness.py | 402d49c2468115f31c2836932345525526f72566 |
| scripts/check_dag_conformance.py | 99473b961bc843d3a4849a88bd9ddd1dc62848a4 |

The known CI base object was already available locally. Comparing that exact object with the source branch base found those four files unchanged and only ten added lines in daily.yml among the relevant inspected paths. The current local main branch was never used for attribution.

## Receipts

- `job_metadata_annotations.raw.json`: completed job metadata and all 16 annotations.
- `exact_log_excerpt.raw.json`: raw relevant log lines, full-log digest, and parsed serial-order windows.
- `source_diff_receipt.raw.json`: exact source workflow diff (changed-file inventory is capped; workflow diff is complete).
- `remedy_context.raw.json`: exact DAG block and existing CI verification commands.
- `unchanged_source_proof.raw.json`: exact blob identity and observed CI base comparison.
- `observed_ci_base_drift.raw.json`: exact ten-line daily workflow drift from source base to observed CI base.
- Additional scoped context is retained in the other raw JSON receipts.

## Recommended authorized next action

Root should make only the existing DAG registry order correction and run the two focused conformance commands, plus the source delivery tests root already owns. Keep the nightly replay URL mismatch as a separate infrastructure finding; this read-only worker did not rerun CI or alter its tests, remotes, gates, or workflow semantics.
