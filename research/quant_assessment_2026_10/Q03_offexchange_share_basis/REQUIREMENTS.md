# Q03 requirements → tests / artifacts

| # | Requirement (brief) | Hermetic test (tests/test_offexchange_share_basis.py) | Empirical artifact |
|---|---|---|---|
| 1 | A known 2:1 or 10:1 split cannot mechanically change same-basis participation | `test_req1_known_split_cannot_change_same_basis_participation[2.0]`, `[10.0]` | results/baseline.json: fixture restores 0.02 → 0.2, and AVGO D_corr is −0.016 against D_raw +2.287. results/events.csv: all 7 holdout events have \|E_corr\| ≤ 0.102, inside the ±log 1.25 = 0.223 bar; raw-basis \|E_raw\| ≥ 0.740 on all 7 (primary support). Secondary: results/primary.json holdout median E_corr is +0.038 with a coarse 4-block CI of [+0.001, +0.047] |
| 2 | Reverse splits, multiple actions and adjusted-volume conventions are distinguished | `test_req2_reverse_split_is_distinguished_and_corrected`, `test_req2_multiple_actions_compose`, `test_req2_volume_conventions_are_distinguished`, `test_req2_ambiguous_ratio_is_a_boundary_not_a_factor` | events.csv: HUT 1:5 reverse split, E_corr +0.026. attrition.csv: GE 1.253 is classed `R1_KIND_AMBIGUOUS` |
| 3 | Revised factors change result identity while preserving the earlier vintage | `test_req3_revised_factor_changes_identity_and_preserves_earlier_vintage` (`result_id` binds the vintage hash; the `append_read` ledger is append-only and rejects id collisions) | The baseline `result_id` is recorded in results/baseline.json. No local owner-published revision vintages exist; see the limitation in VERDICT.md §3 |
| 4 | Unknown factors are not estimated from the observed participation jump | `test_req4_unknown_factor_is_never_estimated_from_the_jump` (UNATTESTED → BASIS_INCOMPATIBLE / NONCOMPARABLE; `raw_participation` stays visible, no factor is inferred) | results/primary.json `coverage.unattested_break_names`: 19 names with an incumbent break are left unrepaired |
| 5 | Zero, missing, negative and incompatible denominators are classified separately | `test_req5_denominator_classes_are_separate` (classes DENOM_MISSING / DENOM_NONFINITE / DENOM_NEGATIVE / DENOM_ZERO / NUMERATOR_INVALID / BASIS_INCOMPATIBLE) | Per-read `counts`. The events used VALID rows only, with support counts in events.csv `valid_pre` / `valid_post` |
| 6 | Nonsplit controls and the frozen PSS-AF1 construction remain unchanged | `test_req6_nonsplit_control_unchanged_and_no_pss_af1_surface` | results/primary.json gate (c): 390 control names have corrected == raw bitwise. This is a construction invariant, not a discriminating empirical test, because with no actions corrected = num·1.0/den = raw (PREREG_AMENDMENT.md A2.4). The discriminating evidence for req6 is the hermetic test. Gate (d): panel and panel_deep sha are unchanged and short columns are never read |
| — | Bounded inputs and validation | `test_bounded_inputs_and_validation` | — |
| — | No silent activation | `test_no_silent_activation` (`RESEARCH_ONLY`, docstring header, a `contract()` with no registers/writes/direction/short_ratio, no I/O) | MANIFEST lists only new files. Nothing imports the module except the tests and evaluate.py |

## Commission gates

| Gate | Evidence |
|---|---|
| Incumbent / collision check | PREREG.md §12 Non-duplication |
| Baseline reproduced | RUNS.log line 1: `python evaluate.py --stage baseline`, exit 0, input sha256s |
| PREREG frozen first | FREEZE.log carries the sha256 and the `date -u` timestamp. Changes went to PREREG_AMENDMENT.md only |
| Freeze refusal | evaluate.py `main()` exits 2 on a PREREG hash mismatch (demonstration recorded in VERDICT.md). The module hash is recorded in RUNS.log but not enforced in code; the binding rule is PREREG_AMENDMENT.md A2.3 |
| Shipped = evaluated bytes | The shipped module sha256 `193c006c…d6ca` equals FREEZE.log and both RUNS.log lines. The shipped evaluate.py `48dea05f…56d5` equals both RUNS.log lines (A2.1, A2.2) |
| One dependence-aware comparison | Chronological 40/60 split, quarter-block bootstrap, honest N reported as events/tickers/blocks, attrition.csv, a single primary run |
| Focused pytest exits 0 | 12 passed |
