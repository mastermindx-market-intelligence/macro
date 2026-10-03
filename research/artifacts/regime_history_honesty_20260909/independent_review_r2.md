## PASS — no introduced blocker found

**Reviewed head:** `e4d6bf36da7a8960ea46010a085fc46db854bdc1`  
**Base:** `d220f1127831ea02ed947f8418e05d9fbc7b386c`  
**Frozen scope reviewed:** `docs/superpowers/plans/2026-09-09-regime-history-honesty.md`  
**Tests:** **not run** — review was source/diff-only as directed.  
**Mutations / external activity:** none. No source, refs, working tree, data, config, permissions, tests, fitting, grading, or production actions were performed.

The repair satisfies the W0 temporal-honesty intent within the stated narrow scope:

- `_causal_filtered_pquad()` now correctly describes its historical output as a current-fit reconstruction, not as-issued history. It emits `history_basis="reconstructed_with_current_fit"`, `history_replay_eligible=False`, and a `model_fit_asof` equal to the final fitted observation. The historical forward recursion remains algorithmically filtered, but the code no longer treats that as a PIT/history certificate. [engine/regime_one.py](</Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/hmm-regime-research-20260909/engine/regime_one.py:261>)

- `_forward_read()` propagates those disclosures while keeping replay eligibility hard-false even if the HMM call is unavailable. [engine/regime_one.py](</Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/hmm-regime-research-20260909/engine/regime_one.py:378>)

- `quad_vector` explicitly labels transition momentum as calculated from reconstructed current-fit history and marks it non-replay-eligible. It does not modify probability, momentum-rate, label, rank, trading, or gross policy calculations. [engine/quad_vector.py](</Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/hmm-regime-research-20260909/engine/quad_vector.py:98>)

- `read_hmm_issuance()` reads only the existing `regime_fwd_hmm.jsonl` ledger. It has no fallback model fit, history/parquet read, reconstruction, maturation, or write path. Missing, unreadable, invalid, duplicate, and malformed evidence produce explicit unavailable statuses rather than an estimate. It suppresses realized outcome fields and keeps `historical_replay_eligible=False` for both legacy and metadata-bearing rows. [engine/regime_one.py](</Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/hmm-regime-research-20260909/engine/regime_one.py:964>)

- The CLI dispatches `--inspect-hmm-asof` before `_axis_scores`, accrual, maturity, grading, PIT probing, directory creation, and summary-file writing. `--accrue` and inspection are mutually exclusive. [scripts/validate_regime_fwd.py](</Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/hmm-regime-research-20260909/scripts/validate_regime_fwd.py:271>)

- The append path scans the entire existing ledger before write, refuses duplicate dates anywhere in it, regressed source dates, future source dates, malformed/ambiguous ledger state, non-newline-terminated populated files, invalid probabilities, and model/source-cutoff inconsistency. It preserves existing bytes and only appends one metadata-bearing row under the established writer path. [engine/regime_one.py](</Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/hmm-regime-research-20260909/engine/regime_one.py:1018>)

- The prior oversized-integer issue is repaired. `_valid_hmm_prediction()` short-circuits the range test before invoking `math.isfinite`: a `401`-digit positive integer fails `v <= 1`, and a negative one fails `0 <= v`, so neither reaches the potential float-conversion/overflow path in `math.isfinite`. The added regression covers both reader and append refusal. [engine/regime_one.py](</Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/hmm-regime-research-20260909/engine/regime_one.py:949>) [tests/test_regime_one.py](</Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/hmm-regime-research-20260909/tests/test_regime_one.py:576>)

Test coverage is appropriately targeted for the changed capability:

- Prefix-extension reconstruction disclosure;
- exact saved legacy-row read without fitting/parquet access;
- absent, missing-date, duplicate, malformed, invalid-date, and duplicate-JSON-member ledgers;
- nonfinite, boolean, negative, oversized, wrong-mass, missing/extra simplex-key, and wrong-modal cases;
- provenance metadata validity and continued non-certification;
- duplicate/old/regressed/corrupt ledger append refusal and byte preservation;
- CLI inspection ordering, read-only behavior, and `--accrue` mutual exclusion.

The test suite does not explicitly exercise the exact boundary values permitted by the four-decimal simplex tolerance (for example, sums of `0.9998` and `1.0002`). That is a minor **coverage gap**, not an introduced functional blocker: the implementation uses `abs_tol=0.00021`, which preserves those intended four-decimal rows while rejecting a larger error.

### Capability limits

This is only an inspection capability over saved ledger entries. A returned timestamp/model-cutoff record is not asserted to prove original-vintage inputs, and all `historical_replay_eligible` paths remain false. The endpoint is a current reconstructed HMM probability, not evidence of what was believed on earlier dates. No local source state has been treated as production, and this review confers no release, merge, runtime, or production authority.