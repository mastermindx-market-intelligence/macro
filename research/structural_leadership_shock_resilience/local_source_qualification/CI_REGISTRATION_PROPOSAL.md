# Prepared CI registration outside the commissioned write scope

This is a proposal only; no CI authority file was changed. The commission permits
only the local_source_qualification subtree and synthetic test files. The existing
contract-delta gate rejects a new collecting suite named by no workflow run step.
If that gate confirms this condition, merging requires one additional authorized
path: `.github/ci/legacy-jobs.yml`. Do not waive the suite or change the baseline.

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

The standalone proposal passed the incumbent `scripts/run_ci_pack.py --workflow
<external ci-job-proposal.yml> --validate-only` validator, exit 0. The suite
dependency analysis reports seven files and **no ambiguities**. This validates
the prepared job shape; it does not execute hosted CI or authorize its installation.
