# Predictive learning: incumbent contract witness

This executable witness supports [the cross-engine expansion contract](../PREDICTIVE_LEARNING_EXPANSION_2026-11-09.md). It imports the existing Data OS reader and verifies temporal/replay/coverage mechanics with synthetic fixtures. It does not modify Data OS or enroll a producer.

## Reproduce

From the Macro repository root, using Python with the repository on its import path:

```bash
PYTHONPATH=. python research/market_memory/predictive_learning_20261109/verify_incumbent_contracts.py
```

The command emits a JSON report and exits nonzero if a case fails. It uses Python's standard library and makes no network calls. To preserve a new result, redirect it to a new deliberately named evidence file; do not overwrite a prior result without acknowledging the changed source.

The committed `incumbent_contract_proof.json` records the actual run on Git-blob-verified owner source at `f3a547cc09872d9aaa719759a6a2daa2832edad5`. Its SHA-256 values identify the tested module bytes. The constant census pin documents the original study basis; on a different checkout, inspect the emitted module hashes and do not call it an exact-pin rerun merely because that constant is unchanged.

## Result and limits

Thirteen synthetic cases passed: public versus system-observed reconstruction, later revisions, known future schedules, explicit clocks, missing dependencies, generation selection, exact/missing/tampered replay, fixed population accounting, timestamp/profile refusals and input immutability.

The fixture publishing receipts are synthetic. The result does not authenticate a production publisher or prove Sector Intelligence enrollment, Prophet capture, real historical coverage, complete forecast population, label-maturity integration, learned skill or training/promotion authority. All operational/scientific proof flags remain false.

The two existing suites `tests/test_dataos_temporal.py` and `tests/test_dataos_read_contract.py` separately passed all 175 tests after task-local dependency installation and completion of the selected pinned source snapshot. `owner_test_proof.json` records the final result and earlier environment-recovery attempts. These two suites and the witness do not replace normal repository CI or the programme's real-consumer acceptance.
