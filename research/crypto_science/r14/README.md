# R14 CI-integration evidence

Existing Crypto/Vector operation crypto-vector-r2-20260926-sol-001 / draft PR8050. Baseline b74875a6171a4d52cb48decf70d608f106a9fa8e. The only runtime-affecting configuration change is two added dependency paths in the existing .github/ci/legacy-jobs.yml jobs; no product calculation, source collector or trading state changes.

## Recheck the semantic repair

```bash
python3 research/crypto_science/r14/verify_manifest.py
python3 research/crypto_science/r13/verify_receipts.py
```

The first uses the original planner and exact baseline manifest. It verifies both code and data gate selection, zero removed selections, exactly two changed job definitions, and unchanged runtime/checker/waiver source. The second reads the preserved R13 UI/input evidence rather than rerunning an old empirical study or claiming new screenshots.

## Actual recorded tests

- red_closure.txt: original CVD dependency omission,1failed43warnings.
- green_closure.txt: same existing test after two-line configuration correction,1passed43warnings.
- ci_pack_full.txt: first full planner run,3failed132passed43warnings. Failures name omitted tracked admin/hook source.
- sparse_dependency_recovery.json: only those tracked roots materialized at the same HEAD; no full checkout or service execution.
- green_dependency_recovery.txt: the three previously failing cases pass,3passed43warnings.
- ci_pack_full_materialized.txt: fresh complete planner suite after source materialization,135passed; isolated temporary directory,exit0.
- verification_final.txt: broad existing Crypto/Vector/storage/science439passed49warnings; unchanged R13 receipts, semantic selection proof, claim check, compilation and difference check all pass.

The counts above are separate runs. Do not add them to inflate unique test coverage or call them the full repository/hosted CI matrix. Temporary-directory cleanup warnings in prior runs are retained, not asserted repaired globally.

## Source integration and honest negative evidence

manifest_fix.patch contains exactly the two path additions. selection_initial_failure.txt preserves a local verifier mistake that only examined the code plane before being corrected to check code and data separately. sibling_integration_probe.json preserves four file-level comparisons: each earnings sibling individually accepts this fix, while the combined sibling text probe has the same four conflict hunks without the fix as with it. This is neither a real multi-parent branch merge nor permission to edit the earnings branches.

ci_failure_and_reproduction.json records the original exact-head failed CI jobs and matching local defect. Current-head hosted CI must be consumed separately after publication. No validator, job command, waiver, gate assignment, model, empirical result or prior-source identity was weakened. Independent review, held capacity/optional-test effects and live release remain separate unfinished dependencies.

The manifest lists exact artifact digests. It is evidence indexing only, not a new source, lifecycle or acceptance owner. Complete interpretation: research/CRYPTO_SCIENCE_R14_CI_INTEGRATION_RESULTS.md.
