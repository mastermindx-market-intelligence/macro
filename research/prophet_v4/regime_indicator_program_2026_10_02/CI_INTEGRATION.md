# Existing CI integration -- prepared, not automatically enrolled

The independent #8303 review comment `5965501070` correctly found that the old green CI run did not execute this program's 48 tests. Two different repairs are required: discovery and execution ownership. Do not claim either from the other.

## Completed

All five suites now have Test-prefixed unittest.TestCase classes. The exact native `scripts/audit_unrun_tests.py` `defines_tests` function from macro `b4f95f98ef80b8cbb4636afbd723b5091658e1f1`, executed on the materialized exact program files, returns true for every suite. No general discovery guard or grandfather list was weakened.

The exact program at `bd7a4c63a6ef74008b0796efe8ece553f2c7351c` passed **94 unittest tests** on the connected host. The proposed pytest invocation was separately executed on those same five files and passed **94 tests plus 38 subtests**. These are the same 94 tests under two runners, not 188 independent tests or economic validation. The study scripts were not invoked by pytest, and no market-data source or provider was read by the synthetic suites.

`CI_ENROLLMENT.patch` adds Node using an existing manifest action/version pattern and one explicit five-suite pytest step to the existing **`unrun-factor-research` / `gate: code`** job. No new workflow, job, scope override, threshold, collector, model or promotion mechanism is introduced. Existing dependency installation already includes pytest/numpy/pandas/pyarrow; the native-excerpt tests additionally require Node. The chosen Node 20 pattern is inherited from this exact manifest, not a recommendation to upgrade/downgrade the organization's runtime. Hosted execution still must verify the actual environment.

The proposed in-memory transformation was applied to three exact saved manifests and parsed. Each retained all **240 total manifest jobs** and changed only `unrun-factor-research`; this total is distinct from previously reported gate-filtered code-job counts. Other jobs, including the sibling `unrun-scoring-engine` changes, were byte/structure-preserved. These are individual-base composition checks, not a claim of accepted combined-main composition.

| Source manifest | Original Git blob | Proposed whole-file SHA-256 |
|---|---|---|
| Base `b4f95f98ef80b8cbb4636afbd723b5091658e1f1` | `70cb3d353f6c7c37b0046ec36519d26933b26732` | `bba77fc104bdc6bf97367e6fae6dbd7634de6dace8ef373b26dfe408a9849190` |
| #8301 `f6665b70b6307f667d31e148fa288e90daa2c6bf` | `fe383a6a8316bbbd5d60a6da225c01944f63863b` | `2182711c9d91521789f31aaad99b1c031a07060e106928dc917376c53728562a` |
| #8304 `a2e8d6aa6fa749e4b473fc549e9ea83a3c5adc85` | `2b344a0c7d5c631a3495a03b9fb09075ccc23de1` | `8905dd81e55d218481e5b310d84d5fecc77640b682d71dca99b115189dbef888` |

Patch SHA-256: `e96d2a85b46d992b1b9f0bb58c61e0e988ea81f94f03c80eb25444db88de13f7`; local and connected-host bytes match. Retained evidence under `/Volumes/Mastermind/research/prophet-regime-indicator-program-20261002/factorial-bd7a4c63a6ef/`: `ci-enrollment-proposal-proof.json`, `pytest-ci-shape.txt`, and `CI_ENROLLMENT.patch`.

## Still owed

The live/shared manifest has NOT been modified by this patch artifact. Current #8301 and #8304 remain independently held and own neighboring shared-manifest composition. Resolve that integration through the existing source owner, not by overwriting its file or adding another CI system.

After the patch is applied to the accepted composed candidate, verify actual native planner selection for EACH module-only and test-only change. Full-directory collection or a parseable YAML does not establish that a future edit will select this code job. Then inspect concluded exact-head hosted logs that name all five suites and show all 94 tests executed. The native `infer_job_scopes` uses suite import/read closure; dynamic source loading and subprocess fixtures may conservatively widen it. Do not suppress those paths merely to make CI faster.

A pytest command containing explicit files is intentional. An untracked local runner, an always-green report, a data-only gate, or a new `if: false` escape does not satisfy automatic coverage. The legacy manifest's existing `if` handling belongs to the current pack runner; do not enable a duplicate standalone workflow.

Scientific review remains separate: paired quarter inference, provenance/parent reuse, completed versus live observation, native indicator identity, calendar amendment, survivor ETF panel, non-independent trials and no-promotion conclusions all need an independent reviewer. No reviewer ACK, START, approval, worker execution or autonomous wake is implied by this prepared integration artifact.
