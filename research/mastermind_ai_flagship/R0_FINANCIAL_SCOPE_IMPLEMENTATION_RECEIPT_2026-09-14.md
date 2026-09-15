# R0 financial-analysis scope repair — implementation receipt

Operation: `mastermind-ai-flagship-r0-financial-scope-20260914-sol-001`.
Accountable source writer and acceptance owner: Sol. Parent design: Macro #7151.
Base: `878147de1cfbce89768ccf98a140d922ba1a6ce5`.
Skillpack: Mastermind `51b815ab9527e15c9218b049f622dc4d3e0bfbc4`, v1.0.1/bootstrap1.
State at source publication: **BUILT_NOT_PROVEN**. No production release claim.

## Capability and bounded change

The existing Brain prompt now explicitly admits financial scenarios, investment-thesis
analysis and standard financial arithmetic. Supplied assumptions stay assumptions;
missing values stay missing. Scenario outputs gain no house-signal or trade authority.
Only the SCOPE paragraph changes. Providers, quotas, tools, native facts, quote routing,
source readers, signal formulas, authority flags and the proprietary clause are unchanged.
The existing `SCOPE — THIS PRODUCT ONLY` heading is retained because it is also a
leak-screen sentinel; the earlier design's proposed heading rename is not implemented.
The replay fixture is a test oracle, not evidence of model correctness or a new evaluator.

## Observed local proof

Before production edits: Brain gateway + response evaluation baseline **430 passed**.
New contract on unchanged production source: **8 failed, 5 passed**, assertion failures.
After the scope edit: focused contract + baseline files **443 passed**.
Expanded run initially had **839 passed, 3 failed** because sparse checkout omitted
`site/mm_brain.js` and Data OS identity fixtures. No tests were weakened or skipped.
After canonical `scripts/worktree_sparse.py add data site`: **842 passed**, 5 existing
framework deprecation warnings, 18.72 seconds. Generated data/site diffs remained empty.

Reproduction command (Python 3.12, no network/model calls):
```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3.12 -m pytest \
  tests/test_brain_financial_scope_contract.py tests/test_brain_gateway.py \
  tests/test_response_eval.py tests/test_brain_streaming.py \
  tests/test_brain_instant_lane.py tests/test_brain_gateway_quota_safety.py \
  -q -p no:cacheprovider
```
The execution used a private operation-specific pytest basetemp to avoid shared cleanup.
RED log SHA256: `fef7bd641dbb748dfefceb39d2bdb53ee0c7e3719260c8015e1b2b94b8b802ef`.
842-pass log SHA256: `00257f36c70e46e904f6d0867533730f54f0310ed53953bd21931c5fb55db1d6`.
`check_contract_delta.py --base origin/main`: zero introduced, zero inherited.
`run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --pack-index 0 --pack-count 12
--validate-only --scope-mode off`: validated 212 existing jobs; no new job introduced.
`git diff --check`: pass. The new test file is registered in the existing Brain job.

## Release and acceptance still owed

Independent exact-head review, concluded applicable CI, current-base compatibility,
normal Macro deployment/restart and real customer before/after behavior remain owed.
`app/deploy/update.sh` already includes `brain_gateway.py` in its API restart gate.
A health GET before release returned status ok, process commit `ae28f27d6e`, checkout
`878147de1c`; health is not proof this candidate is live or that the model answers well.
The original successful-transport refusal is preserved in #7151. Its separate P2
HTTP524 probe remains backend-effect-unknown and was not replayed during this repair.
Next: review this candidate, release only after checks conclude, then test exact P1,
English/Chinese variants and the widget path; do not equate prompt tests with model quality.
