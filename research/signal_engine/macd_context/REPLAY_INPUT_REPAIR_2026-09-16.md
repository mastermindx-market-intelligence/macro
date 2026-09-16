# Historical implementation plan — execution results supersede the checklist

Current results and next gate: `REPLAY_INPUT_AND_CLOCK_RECOVERY_2026-09-16.md`. The checklist below preserves the original pre-execution plan; it is not current completion state.

# Replay Input Repair Implementation Plan

Goal: prevent absent sparse inputs and same-endpoint cache reuse from corrupting the existing Prophet historical control.
Architecture: repair `scripts/prophet_pit_replay.py`, not a second replay engine. Missing tracked price inputs come from the declared historical commit; cache identity incorporates actual price bytes.
Tech stack: existing Python, pandas, parquet and Git plumbing.
Spec: `research/PROPHET_PIT_REPLAY_HARNESS_V1.md`; existing MACD continuation and research-only holds.

## Scope and execution

Continue PR #7177, starting at `46403f4d42330f9e903b52e2fd7cd48ca54bfe61`, in its existing owned workspace and Remote Desktop Commander carrier. Protected procedure pin: Mastermind `8ba7deedde164c90298d3e88785d98e02fa5e2d2`.
Direct work reason: PRINCIPAL_JUDGMENT for separating input, source-clock, and scientific-validity failures; CRITICAL_PATH_SHORTCUT for bounded canonical-owner repairs.
No live ranking, sizing, plans, ledgers, board publication, fidelity waiver, source-era substitution, or merge authorization. The 85% fidelity floor stays unchanged. Preserve every prior adverse result and temporal-validation restriction.

## Task 1: missing historical price inputs

Complete the recovered synthetic fixture in `tests/test_prophet_pit_replay_sparse_inputs.py`.
- [ ] Prove `prepare_reconstruction_tree` currently leaves a tracked historical SPY absent when its directory or file is omitted.
- [ ] Check that a revised later cache cannot replace historical rows, and a later-only ticker cannot enter the vintage population.
- [ ] Restore missing declared ticker inputs from `batch_blobs(repo, vintage_commit, paths)`, truncate using the existing owner, and disclose restoration separately from overlay additions.
- [ ] Refuse missing/unreadable required historical bytes; preserve already-materialized files and all canonical stores.
- [ ] Run the new tests and the existing replay suite; inspect the diff and commit the bounded repair.

## Task 2: price-byte cache identity

- [ ] Add a synthetic test changing prices while holding path and endpoint constant; require a different `tree_fingerprint`.
- [ ] Hash the actual scanned file bytes in the existing fence's state digest; retain identical-tree reuse and date-fence semantics.
- [ ] Run new and existing tests, record real results, and commit with the recovery evidence.
