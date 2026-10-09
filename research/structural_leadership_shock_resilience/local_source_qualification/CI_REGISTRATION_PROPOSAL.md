# CI registration authorized and applied

The Chairman directly authorized `.github/ci/legacy-jobs.yml` solely to register
this suite in the continuation handoff. The entry below is now applied; no other
job, baseline, workflow or waiver was changed.

Proposed bounded code job (three focused suites, synthetic/current code only):

```yaml
  slr-local-source-qualification:
    if: ${{ false }}
    gate: code
    paths:
      - research/structural_leadership_shock_resilience/local_source_qualification/**
      - tests/test_slr_local_source_qualification.py
      - tests/test_winner_autopsy.py
      - tests/test_dataos_identity.py
    runs-on: ubuntu-latest
    timeout-minutes: 8
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: install minimal deps
        run: pip install pytest numpy pandas pyyaml
      - name: SLR source qualification and incumbent identity/detector tests
        run: >-
          PYTHONDONTWRITEBYTECODE=1 python -m pytest
          tests/test_slr_local_source_qualification.py
          tests/test_winner_autopsy.py tests/test_dataos_identity.py -q
```

The incumbent planner derives additional dependency scope from the named suites;
this proposal deliberately does not claim exclusive scope. Before applying it,
validate the manifest and its inferred import closure using the existing checker,
then obtain exact-head hosted CI and independent review. Preserve all existing
jobs, dependencies, budgets and authority checks.

The full manifest passes `python3 scripts/run_ci_pack.py --workflow
.github/ci/legacy-jobs.yml --validate-only` (exit 0). The pack loader requires
`if: ${{ false }}` to prevent duplicate GitHub VMs; it still executes each
selected logical job's semantic `run:` steps. `ci.yml` consumes the hashed plan
with `--gate code --plan-json ... --execute`. No runner condition was removed.

A local pre-commit planner observation selected this job into pack 6 and emitted
the pytest proof step. The new suite's prior seven-file static import receipt
is distinct from the complete three-suite job closure: the incumbent inference
includes thirteen effective path entries and eight conservative fallback patterns.
Scope remains non-exclusive, preserving dependency-trigger coverage. Actual hosted
execution must be proven from the exact-head plan and semantic fragment, not from
this declaration or the advisory local plan.

Fresh local focused verification: 418 passed in 5.44s, exit 0. The adapter and
synthetic-test digests remain identical to repair snapshot
`9253bbbaf1f91a09ad0f86cae2db6b59ddd074a0`. Evidence digests are recorded in
LOCAL_TEST_RECEIPTS.json. Source admission remains NOT_ADMITTED.
