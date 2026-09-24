# RD1 entrypoint repair (no new experiment)

The final-head CI pack 10 run 35976542851, job 107559262929, identified
scripts/research/ric_rates_direction.py as a newly unpinned direct-file entrypoint.
This was a candidate defect, not an inherited baseline failure. The baseline
rerun passed the same import-pinning test.

Repair: insert this checkout's resolved root before repository imports. An
adversarial subprocess test runs --help from a foreign directory with a shadow
engine package on PYTHONPATH; the correct checkout now wins.

Verification: the rates-research and import-pinning suites passed 27 tests.
No fit, outcome evaluation, new configuration, or TrialLedger write was executed.
Model mathematics, preregistration, original FREEZE_RECEIPT.json, all 48 original
trial registrations, predictions, and complete result bytes remain unchanged.

The original study is reproduced only from frozen commit
8796829eea9fe8792a73155f64d5c1dbe83ae3b6 using the recorded module invocation.
This maintenance head intentionally does NOT pass the original byte-freeze guard:
its bootstrap and test files changed after outcomes were known. The guard is not
weakened, and the freeze is not rewritten to pretend the repair predates outcomes.
Independent review and current-head CI/release acceptance remain separate.

Procedure pin: Mastermind 1a7d400294b0d37c460b963b8865b40a23173b58.
Carrier: original operation rates-direction-20260924-sol-001 / Macro PR 7909.
