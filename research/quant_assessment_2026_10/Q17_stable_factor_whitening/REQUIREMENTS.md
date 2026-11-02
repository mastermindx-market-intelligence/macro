# Q17 — requirements map

**Module:** `engine/factor_stable_whitening.py`. It is a research reference, not wired:
`RESEARCH_ONLY = True`, `CONSUMERS = ()`, `TRIAL_BUDGET_CHARGE = 0`. Recorded verdict:
**REJECT**.

**Test file:** `tests/test_factor_stable_whitening.py`. It is hermetic: synthetic data
only, no repo reads, no wall clock. It reports 12 passed.

## Requirements and the tests that pin them

**req1 — near-duplicate columns**
- What is required: bounded amplification, with an `unstable` diagnostic.
- Tests:
  - `test_req1_near_duplicate_columns_bounded_amplification_and_flagged_unstable`
  - `test_req1_well_conditioned_control_is_not_flagged`
- Empirical counterpart: M3 in `results/per_month.csv`. The floor never bound and no
  month was flagged unstable.

**req2 — partially missing rows**
- What is required: missing indicators and n_measured are kept, row_status is emitted,
  and a missing leg is filled by its conditional expectation, not by 0.
- Tests:
  - `test_req2_partially_missing_rows_keep_missing_indicators`
  - `test_req2_missing_leg_is_filled_by_conditional_expectation_not_zero`
- Empirical counterpart: M4. The incumbent presents 12,457 partial rows as complete; the
  challenger presents 0.

**req3 — permuting the factor order**
- What is required: the order does not privilege the first factor (symmetric Löwdin
  form).
- Test: `test_req3_permuting_factor_order_does_not_privilege_first_factor`

**req4 — resampling**
- What is required: resampling reports subspace and output instability.
- Tests:
  - `test_req4_resampling_reports_subspace_and_output_instability`. On the near-duplicate
    panel it asserts:
    - the incumbent's amplified-direction sine is above 0.3;
    - the control's sine is below 0.2;
    - the challenger's sine equals the incumbent's where the challenger's floor does not
      bind, because shrinkage toward I and flooring keep eigenvectors.
  - `test_req4_amplified_direction_sine_discriminates_when_the_floor_binds`. When the
    challenger's floor binds the duplicate block, the incumbent's sine is above 0.3, the
    challenger's degenerate-subspace sine is below 0.05, and the ratio is more than 10×.
  - `test_req4_degenerate_amplified_block_is_a_subspace_not_an_arbitrary_vector`
  - `test_req4_bootstrap_support_follows_each_methods_own_rule`. The bootstrap uses
    pairwise support for the challenger, the same rule `stable_whiten` applies, and
    complete cases for the incumbent.
- Empirical counterpart: M5 (`bootstrap_instability`, n_boot 50 per test month).

**req5 — sparse support**
- What is required: a sparse-support fallback is identified as `untransformed_fallback`,
  never passed off silently.
- Test: `test_req5_sparse_fallback_is_identified_as_untransformed`
- Empirical counterpart: attrition shows 0 fallbacks for either method across 23 test
  months.

**req6 — preservation**
- What is required: live ranks, Atlas ownership and the trial budget are preserved.
  - The input is untouched.
  - Columns are kept, and a non-monotone index keeps its order, with no sort or
    re-rank.
  - The outputs share no memory with the input, and mutating them leaves the input
    unchanged.
  - The module exposes no public callable named for ranking, scoring, compositing,
    writing, saving, persisting, registering or publishing.
  - `CONSUMERS == ()` and `TRIAL_BUDGET_CHARGE == 0`.
- Test: `test_req6_live_ranks_atlas_ownership_and_trial_budget_preserved`

**Contract — no silent activation**
- What is required:
  - `RESEARCH_ONLY` is set.
  - The docstring prefix is present.
  - There is no register/main/run/activate/publish hook.
  - Only the math, numpy and pandas modules are imported.
  - Non-finite input is refused.
- Test: `test_no_silent_activation_module_contract`
- This test checks the module's own attributes only and scans no repo files.

## Assessment gates (brief "NOT DONE UNLESS")

1. **Non-duplication:** PREREG.md §1 covers factor_orthogonal, the Factor Atlas, R-ORTH
   and `DNR:KILL-OOS-DECAY-ORTHOGONALITY`, Q08, the composite DNRs, and other whiten
   code.
2. **Baseline reproduced:** RUNS.log record 1 (`baseline_repro.py`, exit 0).
3. **PREREG frozen before outcomes:** FREEZE.log holds sha256 51c58c37…6fb0, stamped
   2026-10-09T10:29:16Z (`date -u`).
4. **evaluate.py:**
   - It refuses on a PREREG hash mismatch, an input-table mismatch, or a module change.
     The module is hashed with its verdict token normalized.
   - It appends command, exit code, input sha256s and output sha256s to RUNS.log
     (record 2).
   - Since `PREREG_AMENDMENT.md` it also refuses unless that file's sha256 matches its
     FREEZE.log line. The amended module row replaces the PREREG row. Record 3 is the
     single authorized re-run, and it reproduced every number exactly.
5. **One dependence-aware comparison on licensed retained local data:**
   - chronological 14/23 split
   - leg set chosen in training only, with no tuning
   - moving-block bootstrap (block 3, 2000 reps, seed 17)
   - honest N = 22 pairs / 7 blocks
   - attrition and support reported in `results/`
   - run once
6. **The pytest command exits 0:** 12 passed.
7. **Required files:** VERDICT.md, REQUIREMENTS.md and the `_handoff/` files are
   present.
