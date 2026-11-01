# Q17 PREREG amendment 1 — independent-audit fixes to diagnostic code

PREREG.md is unchanged (sha256 `51c58c37…6fb0`, frozen in FREEZE.log). This amendment
was written, hashed and recorded in FREEZE.log before the re-run of `evaluate.py` that it
authorizes, and before any new outcome was read.

## Reason

An independent audit returned PASS_WITH_FIXES (0 blockers, 0 majors, 5 minors). Three of
the minors require edits to the frozen challenger module. None of the edited code feeds the
frozen verdict: the primary decision uses only the drift ratio R (M2), the out-of-time
error difference (M1) and coverage, which come from `estimate_correlation`,
`whitening_matrix`, `conditional_fill`, `stable_whiten` and `transform_drift`. Those
functions are byte-identical to the frozen module. M5 (§5) is descriptive only, and §6
states that M5 does not change the verdict.

## Changes to `engine/factor_stable_whitening.py`

1. **Audit minor 1.** Removed `measured_composite`. It was unused, duplicated the
   incumbent `orthogonal_composite`, and sat against `DNR:KILL-FUSED-COMPOSITE`.
2. **Audit minor 4.** Replaced `_min_eigvec`, which returned `V[:, -1]`, an arbitrary
   vector when the eigenvalue floor binds two or more eigenvalues. Two functions replace
   it:
   - `amplified_subspace` returns the whole tied top block of W (relative tolerance
     1e-8).
   - `subspace_sine` returns the sine of the largest principal angle between the smaller
     and the larger subspace. For one-dimensional subspaces it reduces exactly to the old
     formula.

   `bootstrap_instability` now also reports `amplified_subspace_dim_base`,
   `amplified_subspace_dim_median` and the flag `amplified_subspace_degenerate`.
3. **Audit minor 5.** `bootstrap_instability` decides support with each method's own rule
   (new `_has_support`): pairwise available cases for `stable`, the rule `stable_whiten`
   applies, and complete cases for `incumbent`. The other changes:
   - Output change is still measured on the complete-case rows (`output_rows` is now
     reported).
   - With fewer than 3 such rows the output fields are NaN and `output_unstable` is None.
   - An unknown `method` is refused.

On the evaluation cohort every month has about 680 or more complete rows against a
support requirement of 30. Change 3 therefore cannot alter which months the M5 bootstrap
covers. Change 2 alters only the sine field, which `evaluate.py` does not consume. The
M5 fields `evaluate.py` does consume (status, n_boot, output_rel_change_median,
transform_rel_change_median, output_unstable) are computed by unchanged arithmetic on
unchanged rows with the same seeds. The re-run is expected to reproduce every recorded
number, and any difference will be reported, not explained away.

## Changes to `evaluate.py` (guard only)

The guard keeps every existing check. It additionally:
- requires that this file's sha256 match the `PREREG_AMENDMENT.md sha256=` line in
  FREEZE.log;
- lets the module row below replace the PREREG.md module row.

No metric, threshold, split, seed, input or decision rule changes.

## Amended frozen hash

| engine/factor_stable_whitening.py (normalized) | 499f71fe3e6cd0e16296db648278324923756f3042821b6925a0822927a6dbd3 |

The prior normalized hash `ac6d5098…cc7` (PREREG.md) covered the pre-audit module.
