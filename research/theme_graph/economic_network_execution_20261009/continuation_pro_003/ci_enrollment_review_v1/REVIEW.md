# Independent pro-003 CI enrollment review

## Verdict

**PASS for the bounded source/composition review.** The native manifest change enrolls exactly the two new observation paths and the fourth observation suite in the existing `company-relationship-candidates` owner. It changes that owner's descriptive comment and test-step name. No additional job, removed owner path, broad path pattern, dependency installation, gate, runner selection or test-inventory edit is indicated.

The new-module implementation review remains the separate frozen v2 PASS. This review does not independently certify the reviewer's earlier pure-reader repair and does not repeat module implementation adjudication.

**Native CI tests remain NOT RUN by this reviewer.** Root owns the application suite already running under PID 46814 and all subsequent validation. That process was neither polled nor interrupted by this lane. The five-function existing CI gate below is the bounded next validation; no local `run_ci_pack --execute` is proposed.

## Native source and accepted comparison

Native read location: `/Volumes/Mastermind/agent-workspaces/macro/web/gmi-economic-observations-20261009-pro-003`, observed host `m2studio`, platform Darwin. Root supplied HEAD `dfa8533b07f1f603ef9f9bb6fbf957e4b1c112a1`; this lane performed no Git operation to reverify it. Native reads used Remote Desktop Commander on device `3f5ce987-e3eb-40a3-af9f-4b0ae54919cc`, with bytecode writes disabled. The read-only interpreter reported Python 3.14.7; that does not constitute a native Python 3.12 application test.

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| Current `.github/ci/legacy-jobs.yml` | 1,248,094 | `3c23ea9dcc9094a10a3e5874b8281998f203227f522752d00f578820c5b9e581` |
| Accepted comparison manifest | See retained accepted-source receipt | `8754604c46e236023fab35aa6914196bc2462d9308772d406efed96c58dce7b2` |
| `tests/test_ci_pack.py` | 304,249 | `e2e7e0307a2e02fdd6703a40ff87f2efbd1d1fd82bf65d7ed365d579cccb8d52` |
| `scripts/run_ci_pack.py` | 223,426 | `65564916a55eb806d3d9fb0cd4e12726f05fec953f6e47ccd9240f5a141049df` |
| `engine/company_intelligence/relationship_observations.py` | 42,756 | `85c07b309ff7b7220ec12f2b3f25c924a2ef4c9ab495ce9030f61038cbb9e8c7` |
| `tests/test_company_relationship_observations.py` | 49,406 | `a73700e639c8e97a4ff84951b48358abe63b1f5048560d03b0e40f2310ac44da` |

The current owner block was read in full at native manifest lines 22340–22429. Its accepted counterpart is retained in `lanes/pr8705_final_ci_review/immutable_source_read_001.json`, bound to the accepted full-manifest digest. Both the CI tests and planner remain byte-identical to their accepted pins.

## Exact delta and inverse

The complete owner delta is preserved in `OWNER_DELTA.diff`. It contains exactly:

1. Replace the first descriptive comment with private analyst inspection and immutable retained-observation wording.
2. Add `engine/company_intelligence/relationship_observations.py` as a literal path.
3. Add `tests/test_company_relationship_observations.py` as a literal path.
4. Change the test-step display name to `File, pinned-source and immutable observation replay contracts`.
5. Append `tests/test_company_relationship_observations.py` to the existing pytest command.

The path list grows from **69 to 71**, stays unique and literal, and removes nothing. The test command retains its original three suites in the same order, then adds the fourth suite. Python remains 3.12, dependencies remain `pytest pyyaml requests`, and the owner remains `gate: code`, `scope: exclusive`, `runs-on: ubuntu-latest`. Its existing legacy `if` value is unchanged. This review does not interpret that catalog field as a new executable workflow gate.

A native read-only inverse checker replaced exactly those five current byte strings with their accepted counterparts. It required each replacement source to occur exactly once and asserted that the complete inverse bytes hash to accepted `8754604c...`. It then parsed both full manifests with `yaml.safe_load`, asserted dictionary-shaped `jobs`, equal job-key sets, equal values for every non-owner job, the 69/71 literal path inventory and the unchanged code/exclusive owner. Those assertions all preceded—and were reached before—the later reviewer-only import-resolution error described below.

That exact inverse binds preservation of all other manifest bytes, including the accepted QLedger changes. The parsed equality independently corroborates preservation of non-owner job definitions. This is a component result established before an unrelated checker failure; the entire failed checker is **not** reported as exit-zero validation.

## Import enrollment

The two application/test files' native hashes equal the independently reviewed prepared v2 files. Static AST inspection of those byte-identical prepared files includes `TYPE_CHECKING` imports and the embedded child program. The required first-party modules are already in the owner list:

| Import use | Existing owner paths |
| --- | --- |
| Module's real inspector | `engine/company_intelligence/relationship_candidates.py` and parent initializers |
| `TYPE_CHECKING` store protocol | `engine/research_vault/r2_store.py` and parent initializers |
| New module imported by test | Newly enrolled `engine/company_intelligence/relationship_observations.py` and incumbent package initializers |
| Test's span-receipt helpers | `engine/earnings_release/receipts.py` and parent initializers |
| Test's actual LocalStore | `engine/research_vault/r2_store.py` and parent initializers |
| Test's pure Registry | `lib/dataos/registry.py` and parent initializers |
| Embedded child application imports | The same LocalStore, observation module and pure Registry paths |

There is no missing direct first-party owner path in those imports. The module's store type import remains part of static closure accounting even though it does not execute at runtime. The child has no parent test-module import. Its deliberately denied dynamic import controls are not application dependencies that must load successfully; their exact coverage was reviewed in the separate implementation receipt. This does not assert that every possible dynamic import has been independently resolved by an executed planner.

Existing native and shared pytest initialization remain enrolled. No first-party dependency installation is introduced. The actual transitive/opaque-construct interpretation belongs to the existing curated-closure gate below; this static review does not substitute an ad hoc resolver for that gate.

## Minimal existing native CI gate

Use the existing **five-function bounded gate**, once on the final applied composition. It provides five specific checks without rerunning the entire large `test_ci_pack.py` file:

| Existing test | Concrete purpose for this delta |
| --- | --- |
| `test_every_declared_scope_in_the_real_manifest_is_covered` | Loads the actual manifest using the incumbent planner and rejects command/read coverage gaps introduced by the fourth suite. |
| `test_the_curated_exclusive_set_is_actually_declared` | Confirms the native parsed exclusive inventory still equals the existing curated set; no new owner or inventory entry should be needed. |
| `test_curated_exclusive_scopes_cover_their_own_import_closure` | Runs the incumbent transitive closure check on the real manifest, including package initialization and the new test's relevant imports/reads. The implementation is shared with contract-delta. |
| `test_plan_is_deterministic` | Builds a real nonempty plan twice, checks full plan equality and digest equality after the command and suite inventory change. |
| `test_exclusive_curation_narrows_ordinary_code_prs` | Measures the unchanged fixed packing probes and ceilings, catching selection/weight spillover from the added suite instead of widening limits. |

The exact native test bodies were read from the current byte-bound `tests/test_ci_pack.py`: lines 904–906, 4657–4660, 4676–4699, 2920–2926, and 4819–5463 respectively. The packing function has a long historical docstring; the operative body calls `packing_probe_measurements` and `packing_probe_breaches` and asserts no breach. A compact receipt retains the operative bodies; no new assertion or ceiling is proposed.

Run from the canonical workspace with the already resolved native Python 3.12 executable:

```bash
PYTHONDONTWRITEBYTECODE=1 python3.12 -B -m pytest -p no:cacheprovider -q \
  tests/test_ci_pack.py::test_every_declared_scope_in_the_real_manifest_is_covered \
  tests/test_ci_pack.py::test_the_curated_exclusive_set_is_actually_declared \
  tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure \
  tests/test_ci_pack.py::test_plan_is_deterministic \
  tests/test_ci_pack.py::test_exclusive_curation_narrows_ordinary_code_prs
```

The existing application suite invocation should independently contain all four files:

```text
tests/test_company_relationship_candidates.py
tests/test_company_pinned_relationship_candidates.py
tests/test_company_relationship_review_set.py
tests/test_company_relationship_observations.py
```

Root's in-progress run already owns that application validation. This review does not call for a duplicate run unless its actual result or source binding requires one. No whole CI-pack execution, new job, broad path fallback, curated-set edit, packing-ceiling increase or additional optional CI sweep is warranted by the inspected delta.

## Process accounting and limitation

| Operation | Result |
| --- | --- |
| Native read/hash/selected-source process PID 49667 | Exit 0; all returned source hashes and selected content retained. |
| Native inverse/schema/import checker PID 52181 | Exit 1 at the reviewer resolver assertion for `engine/company_intelligence.py`; the preceding full inverse/schema assertions completed. |
| Corrected native read-only command | RDC rejected it with `Command not allowed` before a PID. It was not retried through that process route. |
| Direct `read_multiple_files` fallback | Read-only success, explicitly limited to the first 700 manifest lines; not misrepresented as a complete source copy. |
| Local AST/package resolution against the complete native owner list | PASS for direct first-party imports in native-byte-identical prepared files, including embedded child and type-only imports. |
| Native application/pytest/store/Git/source-capture effects by reviewer | NOT RUN. |

The reviewer-only resolver initially formed `.py` for every imported module and therefore mishandled a package import. The correct resolution is `engine/company_intelligence/__init__.py` plus the imported `relationship_observations.py`; both are enrolled. The error, rejected follow-up and exact first-attempt source are retained in the evidence. No application source, CI manifest, Git state or native store was changed by the reviewer.

The source-composition verdict is complete. Actual native CI results and the forthcoming real retained-source harness remain separate evidence gates owned by root and its assigned witness builder.
