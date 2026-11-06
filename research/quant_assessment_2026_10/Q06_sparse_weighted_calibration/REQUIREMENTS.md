# Q06: the six acceptance requirements and their evidence

| Item | Value |
|---|---|
| Module | `engine/calibration_sparse_weighted.py` (`RESEARCH_ONLY = True`, imported by nothing) |
| Test | `tests/test_calibration_sparse_weighted.py`: 7 tests, all passing |
| Run artifacts | Files in this directory, all appended to RUNS.log. The cited results come from the custody reruns (RUNS.log records 5–8) under CODE_PIN.json: module `0e0e302d…`, evaluate.py `f7e2bd94…`. The reruns are declared in PREREG_AMENDMENT_2.md and are byte-identical to the original outputs. |

Focused test command (exit 0, "7 passed"):

```
PYTHONPATH=<Q06> PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -m pytest <Q06>/tests/test_calibration_sparse_weighted.py \
  --rootdir <Q06> --noconftest -p no:cacheprovider -q
```

| # | Requirement | Status | Unit evidence (test) | Empirical / simulation evidence |
|---|---|---|---|---|
| 1 | Ties, unequal weights, empty cells and monotonicity tolerance are fully specified | MET | `test_req1_ties_unequal_weights_empty_cells_and_tolerance_are_specified`. It covers whole-tie grouping, zero-weight rows dropped and counted, invalid inputs refused, DP optimality against brute force, the lexicographic tie-break, B = min(10, G), infeasible or empty → `None`, the 1e-3 inclusive point tolerance, and max-stat broken / not broken / `None` with no valid replicates. | PROPOSED_AMENDMENT.md §A, clauses A1–A4 (exact text) |
| 2 | Weight ESS and dependence-adjusted uncertainty are not conflated | MET | `test_req2_kish_weight_ess_is_separate_from_anchor_block_count`: Kish N = 1000 while native Σw = 10 and there are 2 anchor blocks; support states `UNKNOWN` / `EMPTY` / `MEASURED_ZERO`; Σw = (T+L−1)/L; anchor-block bootstrap | s1.json reports Kish next to Σw and blocks (e.g. Kish 13,377 vs Σw 207 at H=21, T=4536). e1.json: 0_7 Kish 32.7 vs Σw 1.0; 8_90 Kish 189 vs Σw 1.05. Clause A5. |
| 3 | Simulation covers both false reassurance and decades-long infeasibility | MET | `test_req3_simulation_covers_false_reassurance_and_overconservative_infeasibility`: `gate_ratio(1/6, H=5)` gives T_inc 1200 vs T_alt 180; years > 50 at rate 1/66, H=21; R_inc NO_VERDICT `total_below_200` at T=252; T1 → R_alt FAIL | s1.json: false reassurance per truth × regime × cell (K1 failed, 0.105 in two T3 steady cells); R_inc support 0.00 in every cell up to 18 years; attrition.json; E1 window of 1–2 sessions |
| 4 | Calibration error and uncertainty are reported even where no point verdict is supportable | MET | `test_req4_error_and_uncertainty_reported_even_without_point_verdict`: at 5 blocks there is no verdict, yet the binned ECE and its 90% interval are present, `can_promote` is False, and the proposed decision only de-escalates | s1.json: ECE and 90% intervals present in 200/200 replicates of every cell, including H=21 T=252, where no rule has support |
| 5 | No frozen weight, sample membership, registration or outcome window is changed by the reference code | MET | `test_req5_reference_reproduces_frozen_weights_and_never_mutates_inputs`: hand case 0.375/0.375/0.75; brute-force oracle within 1e-12; boundary refusals; inputs not mutated; thresholds frozen | E1 F0 cross-check: native weights equal `lib.flow_score.uniqueness_weights_nyse_intervals` with max abs diff 0.0 on both buckets. Input sha256s are in RUNS.log. Read-only data access. PREREG frozen and hash-checked by evaluate.py. No outcome column was read in E1. |
| 6 | Opus recommendation, statistical acceptance and Fable ratification are reported as separate states | MET | `test_req6_opus_statistics_and_fable_states_are_separate`: three independent enums; invalid values refused; frozen dataclass | VERDICT.md §5 and PROPOSED_AMENDMENT.md show the three states per item. Current values: opus_recommendation PROPOSE_AMENDMENT (A1–A6) and RECOMMEND_REJECT (R_alt); statistical_acceptance NOT_REVIEWED; fable_ratification UNRATIFIED |
| — | No silent activation | MET | `test_no_silent_activation`: `RESEARCH_ONLY` is True; no I/O at import; the docstring starts "RESEARCH REFERENCE — NOT WIRED" | Nothing imports the module, and no wiring, registration or scheduling exists |

## Falsifier / stop-for-evidence rule (from the brief)

The rule applied. The retained sample supports no method:

- 0_7 has 1 fill session.
- 8_90 has 2 fill sessions.
- G_inc and G_alt are `NOT_YET_ESTIMABLE` for both buckets.

The result is therefore an explicit not-yet-estimable state, backed by power and feasibility evidence (s1.json,
attrition.json). Shrinkage-created certainty was detected and not counted as support: R_pool PASSed 61/200 against
R_alt's 4/200, and the de-escalate-only rule held.
