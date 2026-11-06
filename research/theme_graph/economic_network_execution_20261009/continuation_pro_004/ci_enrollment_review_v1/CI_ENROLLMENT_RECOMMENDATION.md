# WP02 source-diagnostic kernel: independent CI enrollment recommendation

**Decision: recommend a distinct `gmi-source-diagnostic-kernel` job in the existing legacy-job manifest, with 32 explicit paths and a matching `CURATED_EXCLUSIVE` entry.** Preserve the existing company-relationship inspector owner and all current CI controls. This is a reviewable recommendation, not an applied change, native test result, or release approval.

Reviewer: `/root/ci_inventory_review`. Completed 2026-10-09 12:58:43 UTC. Native access used Remote Desktop Commander device `3f5ce987-e3eb-40a3-af9f-4b0ae54919cc` only; no Studio Direct calls were made for this assignment.

## Frozen authority and scope

The review binds native reads to Git objects at `7c1463015b8f1a3296f09d12a8052112939b4c25`, in the canonical pro004 workspace. The upstream comparison is the parent's already-fetched `40ebaebdbcd57eedaa627623f1cfd1860ff3ee3a`. Reads used explicit commit expressions; this reviewer did not fetch or alter refs. The parent's protected-procedure refresh to Mastermind `8c3bc581e747c8b7c066ff0adec3b54573231baf` is supplied context, not an independent protected-estate refresh by this reviewer.

The frozen author package has manifest SHA-256 `1dbf7da765127a4f32e5c80674399361b6daf0732fe6b1159c3fb1419a9fb075`. Independent scratch reads confirmed:

| Proposed canonical input | Bytes | SHA-256 |
|---|---:|---|
| `source_diagnostic_kernel_v1/source_diagnostic.py` | 77,308 | `80b12ec299e861d24c0c23f88805a475f44099af894fbea7d787296c72681d8f` |
| `tests/test_gmi_source_diagnostic_kernel.py` | 46,432 | `2c9d575614de6e41c1463ff252010e92711b21e8389034df698842c73e59bc05` |
| `source_diagnostic_kernel_v1/synthetic_example.py` | 7,312 | `37db957fff940f2e9557e36586c07ee4a1a3ea534d9b3e36a5c96630b1a5aa78` |
| `source_diagnostic_policy_v2/RECOMMENDED_SELECTION_POLICY.json` | 60,312 | `d41422d76219b1c5d3a3c9cbb19a1bc3124433031200b09499033bd4dc30d522` |
| `source_diagnostic_policy_adoption_v1/POLICY_ADOPTION.json` | 9,593 | `645a20a39842d9c5a03b4ff39a37280d1aa02c32ef545c061d0aa959f06e0016` |

The two JSON policy inputs also match the actual branch Git objects. They are absent from upstream `40eba...`, as expected for this branch's unpublished policy carrier; integration must preserve those branch inputs. The first, third, fourth, and fifth paths above are under `research/theme_graph/economic_network_execution_20261009/continuation_pro_004/`. The canonical suite is at repository `tests/` as shown.

Semantic correctness of the kernel is assigned to a different reviewer. This review inspects source imports, direct reads, runtime placement, pytest support, CI discovery, selector behavior, curated registration, and owner preservation.

## Concrete edits and insertion anchors

`LEGACY_JOB_INSERTION.yaml` is the complete insertion, correctly indented for the existing manifest's `jobs:` map. At both inspected heads, `.github/ci/legacy-jobs.yml` ends with `company-relationship-candidates`. Append the new job after that complete existing block, retaining its bytes. Do not append the WP02 suite to the company inspector job: their implementation ownership and semantic boundaries differ.

`CURATED_EXCLUSIVE_INSERTION.txt` is the complete set entry and provenance comment. Insert it inside `CURATED_EXCLUSIVE` in `tests/test_ci_pack.py`, after the existing `"company-relationship-candidates",` member and before the closing brace. Preserve every current member, test, assertion, helper, and packing ceiling. The static inventory equality is mandatory; the earlier inspector release demonstrated that omitting this separate registration produces a real hosted failure.

At the frozen head the manifest has 254 logical jobs, with no existing job named for a GMI source diagnostic kernel. The inspected relationship job owns three relationship-inspection/review suites and a different source graph. The proposed insertion should produce 255 jobs, adding exactly one new logical owner. It introduces no workflow, trigger, scope algorithm, registry, global invalidator, baseline, waiver, or control plane.

Expected new parsed job:

| Field | Expected value |
|---|---|
| Job ID | `gmi-source-diagnostic-kernel` |
| Gate | `code` |
| Scope / exclusive flag | `exclusive` / true |
| Declared paths | 32 unique concrete paths in `RUNTIME_PATHS.json` |
| Derived fallback paths after normal inference | Empty, under the existing exclusive mechanism |
| Runner / Python | `ubuntu-latest` / `3.12` |
| Dependency installation | `pip install pytest` |
| Sole suite invocation | `python -m pytest tests/test_gmi_source_diagnostic_kernel.py -q` |
| Expected balancing weight | 4 under the unchanged `_job_weight` formula |
| `if` | Existing manifest convention `${{ false }}`; execution remains owned by the pack runner |

Weight 4 follows from two `run:` steps, one `tests/test_` occurrence multiplied by two, and less than 800 characters of command text. It is an expected parsed value, not a measured execution duration. Do not add a fabricated historical duration to `OBSERVED_COMMAND_SECONDS`.

The proposed YAML was parsed in scratch and its unique ID, 32 unique sorted paths, scope, gate, `if` value, command count, and weight formula were checked. No native manifest parser was run against an applied insertion because this reviewer did not apply it.

## Complete tracked runtime path set and its justification

The exact list is in both `LEGACY_JOB_INSERTION.yaml` and `RUNTIME_PATHS.json`. It contains five direct WP02 inputs and 27 shared pytest/import/initializer inputs.

The direct five are the sole canonical suite, its dynamically loaded implementation, its dynamically loaded artificial example factory, and the two exact policy/adoption byte files. `KERNEL_DIR` resolves from the canonical `tests/` placement to the proposed research folder. The suite reads both JSON files during collection. Its CLI test invokes only the exact same implementation against temporary copies of the synthetic request and policy bytes. The implementation and helper use standard-library imports only. No research-package `__init__.py` is executed because loading uses `importlib.util.spec_from_file_location` on exact files.

The 27 shared inputs are:

```text
engine/__init__.py
engine/basket_breadth_divergence.py
engine/catalyst_tone.py
engine/desk_ledger.py
engine/gdelt_client.py
engine/marketing/__init__.py
engine/marketing/accounts.py
engine/marketing/authority.py
engine/marketing/chart_render.py
engine/marketing/charter.py
engine/marketing/claims.py
engine/marketing/cmo.py
engine/marketing/departments.py
engine/marketing/economics.py
engine/marketing/events.py
engine/marketing/ledgers.py
engine/marketing/logo_cache.py
engine/marketing/opportunity_bus.py
engine/marketing/publication.py
engine/marketing/state.py
engine/master_brain.py
lib/__init__.py
lib/config.py
scripts/__init__.py
scripts/worktree_sparse.py
tests/__init__.py
tests/conftest.py
```

These are not WP02 product dependencies. The existing shared pytest fixtures and collection hooks import them, including package initializers. `tests/conftest.py` imports GDELT, breadth divergence, marketing account/chart/logo helpers, master brain, and the sparse-checkout helper. Marketing's initializer imports `state`, which imports the listed marketing modules; master brain imports catalyst tone and desk ledger; applicable modules import `lib.config`. The complete bounded graph, each frozen blob and SHA-256, and source-head binding are preserved in `FROZEN_SHARED_IMPORT_CLOSURE.json`.

The derivation includes imports inside the shared conftest's executing fixture/hook functions, then follows import-time imports and package initialization in the imported modules. Dormant function-body imports in those modules do not become WP02 dependencies merely because their functions exist. A preliminary indiscriminate all-function import census stopped at its explicit 120-file bound; it was not used as the declared scope. The final derivation was checked against the actual fixture behavior and import-time statements. No production workflow, provider request, persisted market artifact, or source reader is called by the new test suite.

`lib.config` has an existing optional local dotenv import-time behavior; this review did not read a dotenv file or any secret. Neither the kernel nor the proposed job introduces that behavior. Hosted CI's checked-in dependency ownership does not include private ambient configuration. The suite's subprocess inputs are temporary synthetic files; its existing module guards and data/site write tripwires remain enabled. The declaration does not disable shared fixtures to obtain a smaller closure.

The checked-in synthetic input/output examples, implementation logs, review documents, package manifests, and archived `.py.txt` suite are not read by the canonical runtime invocation and are intentionally not added as executable dependencies. Editing narrative evidence alone need not run the kernel. Editing any of the five direct inputs must run it.

The complete 27-file shared graph is byte-identical between `7c146...` and `40eba...`, verified by an exact-path Git diff with empty output and exit 0. It is a frozen-source dependency recommendation. New code or fixture changes after these heads require the ordinary closure audit and source review to reconsider the scope.

## Discovery, closure, and selection contracts

The actual `audit_unrun_tests.py` suite filename regex accepts only names ending in `.py` with `test_...` or `..._test` shapes. Its `defines_tests` AST check recognizes the canonical suite's top-level `test_*` function definitions. The later runtime conversion of those functions into ordinary `unittest.TestCase` methods does not hide the suite from static discovery. Archiving the authored duplicate as `.py.txt` avoids registering a second executable suite. Do not leave an additional `test_gmi_source_diagnostic_kernel.py` under research.

The new `run:` command explicitly names the canonical suite, so the actual command inventory can attribute it to the new job. A named exact file avoids the fail-closed directory/glob discovery path. The standard-library unittest implementation remains collectable by pytest; the author-reported 90-test result is context only and was not rerun here.

The actual selector's exclusive branch preserves the declared paths and clears fallback paths. This is appropriate because this suite's general `subprocess.run` and dynamic path loading are concretely bounded to the implementation and temporary synthetic inputs inspected above. Allowing the generic inference fallback to widen the job to broad repository roots would create unrelated CI fan-out and risk the existing packing ceilings.

Curated scoping remains subject to the actual shared `curated_exclusive_closure_findings` implementation. That implementation re-infers all exclusive jobs with exclusivity disabled, checks every derived concrete closure path against the declaration, and fails if no closure exists. It is shared with contract-delta. The separate static `CURATED_EXCLUSIVE` equality must also match every manifest exclusive. Neither mechanism is changed by this recommendation.

The existing workflow already starts on every repository path and explicitly covers `research/**` and `tests/**`. No trigger change is needed. `.github` control-plane and conftest changes retain their existing broader invalidation behavior. The new declaration contains no packing-probe path, no broad wildcard, and no fallback. It therefore should not add a selected job for the existing homepage, free-content-builder, or Prophet plan-book probes. This expectation must be measured after the insertion rather than asserted as a passed native check now.

## Current upstream reconciliation

`CONTROL_SOURCE_IDENTITIES.json` records the exact hashes and Git blobs of the inspected control sources at both heads. The curated test, pack selector, dependency analyzer, trigger-closure checker, unrun-suite audit, and conftest are identical. Root-level `conftest.py`, `pytest.ini`, `pyproject.toml`, `setup.cfg`, and `tox.ini` were absent at the frozen head; the latter three and root conftest were also checked at the upstream comparison where applicable. No extra root pytest configuration or conftest dependency was discovered.

The manifest differs only in an existing backup step, adding PostgreSQL tool-path/precondition checks and the backup IW2 snapshot suite. The workflow adds its two backup trigger paths. Those independent upstream changes are disjoint from the insertion and must be retained. In particular, do not write a complete manifest reconstructed from `7c146...` over the integrated `40eba...` source.

Key manifest identities:

- Frozen branch: blob `4014af29fc8c7b1273a8d8c3783b7ceb9d831413`, SHA-256 `749e585ad375c00a80eed545cf74c6dcc5d7f5a608338a5548301f3166eb5777`.
- Upstream comparison: blob `204ca3e245799248a3922b41babb6951a20b8782`, SHA-256 `a7591369fc7c9abd3356f79886a17a4232c23fff78ce647ce70a5dbde81c6f3e`.
- Curated test at both heads: blob `9f1f22affb5a556652597ee7f0eabd590095d027`, SHA-256 `e2e7e0307a2e02fdd6703a40ff87f2efbd1d1fd82bf65d7ed365d579cccb8d52`.

Root remains responsible for live active-owner/PR collision checks before edits and publication. This reviewer did not operate on the separate observation PR #8711 or duplicate its CI monitoring.

## Minimum meaningful native checks after application

Run the actual canonical suite once through the proposed invocation, preserving shared pytest guards. Confirm the expected 90 collected and passed cases or investigate any changed count; do not assume the author's unittest result proves native pytest behavior.

```sh
python3 -m pytest tests/test_gmi_source_diagnostic_kernel.py -q
python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --validate-only
python3 -m pytest \
  tests/test_ci_pack.py::test_the_curated_exclusive_set_is_actually_declared \
  tests/test_ci_pack.py::test_every_declared_scope_in_the_real_manifest_is_covered \
  tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure \
  tests/test_ci_pack.py::test_exclusive_curation_narrows_ordinary_code_prs -q
```

Also perform bounded read-only native API checks after the canonical suite is tracked: the native suite discovery inventory must find exactly one canonical suite and no `.py.txt` duplicate; the parsed manifest must have exactly one new owner whose command names that suite; every one of the 32 paths must select the job; the three existing packing probes and an unrelated research narrative must not select it; a semantic manifest delta naming the new job must select it. Use the existing `load_legacy_jobs`, `infer_job_scopes`, `select_jobs`, and native audit functions. No new selector or test-discovery implementation is needed. Full trigger closure and unrun-suite gates remain part of hosted CI; do not create a baseline or waiver for this suite.

For the separate inverse-delta review, subtract the exact new job from the parsed after-manifest and compare all remaining job definitions and top-level fields with the actual integrated preimage. Likewise, remove only the proposed inventory member and compare all remaining test-file AST nodes and existing set members with the integrated preimage. Preserve an exact textual diff to expose comment loss or accidental scalar changes. This verifies preservation of the unrelated upstream backup repair as well as the existing company inspector job.

Never use local `run_ci_pack --execute` for these checks. Publication still needs genuine fresh hosted proof, the current tested merge composition, exact source identities, required release checks, and the existing merge procedure. This recommendation does not replace them.

## Process reconciliation and limits

All native processes started by this reviewer are concluded:

| PID | Purpose | Exit |
|---:|---|---:|
| 20961 | Frozen source identity/read inventory | 0 |
| 21850 | Import and CI contract locations | 0 |
| 23505 | Actual closure/discovery/curated contracts | 0 |
| 25116 | Preliminary all-function import census; explicit 120-file bound reached | 1 |
| 26550 | Selector and executing fixture inspection | 0 |
| 27667 | Bounded import-time closure and existing owner inventory | 0 |
| 27961 | Native dependency analyzer details | 0 |
| 29542 | Dependency/config behavior and job-weight formula | 0 |
| 30184 | Import-time call inspection | 0 |
| 31298 | Frozen branch/upstream control and policy identity comparison | 0 |
| 32472 | Exact upstream CI/backup diff | 0 |
| 34569 | Exact shared-import path comparison, empty diff | 0 |

No native files, refs, source, credentials, CI dispatches, PR state, stores, providers, or owner messages were modified. The only writes are this scratch recommendation package. There is no native kernel execution claim, no accepted insertion claim, and no source-admission, empirical-population, rights, predictive, or production-product promotion. The expected job gates a deterministic artificial research model and structural refusals under the project's existing holds.
