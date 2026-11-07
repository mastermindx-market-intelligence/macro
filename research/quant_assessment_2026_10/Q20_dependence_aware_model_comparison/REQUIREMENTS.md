# Q20 — Requirements traceability

Each of the brief's six requirements is listed below. For each one: where the module
implements it, which hermetic test pins it, and what the empirical run produced. The test
file is `tests/test_challenger_spa_comparison.py`. Run it with:

```
PYTHONPATH=<Q20 staging root> PYTHONDONTWRITEBYTECODE=1 python3.12 -m pytest tests/test_challenger_spa_comparison.py --noconftest -p no:cacheprovider -q
```

Result: 12 passed, exit 0.

## req1 — Candidates map to generation-time trial IDs; no losing trial disappears

- **Module:** `trial_config_hash` re-derives the ledger's config-hash rule as a pure
  function. `map_candidates_to_trials` raises `UnmappedCandidateError` for a candidate that
  has no ledger row, and `MissingTrialError` when a recorded trial would vanish from the
  comparison. `original_trial_budget` carries the declared maximum.
- **Tests:**
  - `test_req1_candidates_map_to_generation_time_trials_and_no_losing_trial_vanishes`
  - `test_req1_cross_source_budget_trials_are_attrition_not_silently_dropped`. The
    missing-trial check is scoped to the given family and source. A same-family trial from
    another source stays in `original_trial_budget` as attrition, and with `source=None`
    the check covers it and raises `MissingTrialError`.
- **Empirical:** all 4 `vector`/`alloc_variant` candidates map to their 2026-07-02
  generation-time hashes. The other 67 budgeted trials have no retained loss panel. They
  are counted in the budget of 71 as `UNAVAILABLE_LOSS_PANEL` and are not dropped. The
  `_raw` columns have no trial identity, so they are excluded and named in the output.

## req2 — Resampling preserves time and cross-model dependence; block-length sensitivity

- **Module:**
  - `stationary_bootstrap_indices` builds one common index matrix that every candidate
    shares.
  - `spa_test` is Hansen's studentised SPA with p_l, p_c and p_u.
  - `block_length_sensitivity` covers blocks {7, 14, 21, 42, 63}.
  - `effective_sample_size` (Newey–West) and `honest_n_blocks` measure the usable sample.
- **Tests:**
  - `test_req2_resampling_preserves_dependence_and_reports_block_sensitivity`
  - `test_req2_spa_pvalue_ordering_and_discrimination`
  - `test_newey_west_and_naive_selection_discriminator`
- **Simulation (§8):**
  - Under correlated nulls the SPA p_c size is 0.055–0.071.
  - The naive best-candidate rate reaches 0.382, which shows the discriminator is needed.
  - Power on the planted edge is 0.901.
- **Empirical:** p_c is 0.245–0.283 across all five block lengths.

## req3 — Chronological holdouts are not replaced by shuffled CV or PBO

- **Module:** `chronological_split` produces the train/evaluation split, and beta is
  estimated on the training window only. `cscv_pbo` returns `role=supplementary`,
  `can_set_verdict=False` and `replaces_chronological_holdout=False`. `claim_decision`
  reads only the SPA result on the chronological evaluation window.
- **Test:** `test_req3_chronological_holdout_not_replaced_by_shuffled_cv_or_pbo`.
- **Empirical:** PBO = 0.599 is reported as supplementary only. The verdict comes from SPA
  on the 2021-01-01 to 2026-10-07 holdout.

## req4 — Adding null correlated candidates cannot lower the trial budget

- **Module:** `trial_budget_after_adding` returns a value that is non-decreasing and never
  below `original_trial_budget`.
- **Test:** `test_req4_adding_null_correlated_candidates_never_lowers_the_budget`.
- **Simulation:** adding 0, 10 or 50 null candidates at rho 0.5, 0.9 or 0.99 always gives
  71. `never_below_original` and `non_decreasing` are both true.

## req5 — Reused windows are disclosed and never presented as fresh confirmation

- **Module:** `window_reuse_disclosure` assigns REUSED, FRESH_UNDERPOWERED or FRESH, using
  `MIN_INDEPENDENT_BLOCKS = 10`. `fresh_confirmation_allowed` is true only for FRESH.
  `assemble_report` forces `fresh_confirmation=False` unless the window is FRESH.
- **Test:** `test_req5_reused_windows_disclosed_never_marketed_as_fresh`.
- **Empirical:**
  - The evaluation window is REUSED: "reused outcome window — not fresh confirmation".
  - The post-generation slice (97 days, 4 blocks) is REUSED. It would be
    FRESH_UNDERPOWERED if nightly display reruns were ignored. It is descriptive only and
    untested.

## req6 — No denied core read, gate bypass, new ledger, automatic promotion or source-policy change

- **Module:** `RESEARCH_ONLY = True` and `PROMOTION_AUTHORITY = False`. It imports only
  stdlib, numpy, scipy and pandas. It does no file I/O, writes no ledger, registers
  nothing, reads no wall clock and has no side effects at import. `engine/validation.py`
  was never opened or imported.
- **Tests:**
  - `test_req6_no_core_read_no_gate_bypass_no_ledger_no_promotion`, which includes a
    subprocess import check.
  - `test_no_silent_activation`.

## Module byte history

RUNS.log binds each run to the module bytes it used.

| Run | Module sha256 |
|---|---|
| baseline and simulate | `2ac04a986cfdb81ff0231900a92a47d9aaec84079211d2ac075e3d8c3efed6c1` |
| empirical | `da665dcf9769b41bc4bf59145d91040ef3035292ca3c6d1780bb5c110e57d704` |
| replay-empirical | `4fdea54e006003ea21635b2f28a2d8ed805dbc3005f971db2dc0a77dc8b30d61` |
| replay-baseline, replay-simulate, replay-empirical (final) | `5c0a8beedbc517d1ac2ba9c5c76e083441ea446af884feaf27ecfdd4f49b97dc` |

Only module docstrings changed between these versions. The last change, made after the
independent audit, documents the source scope of the missing-trial check in
`map_candidates_to_trials`.

1. **Before the empirical run:** the previous author's docstring stated an empirical
   outcome that had not yet been computed. That sentence was replaced with a neutral
   pointer to VERDICT.md.
2. **After the empirical run:** the docstring was updated to state the recorded VANISHES
   outcome.

The final replay stages (RUNS.log entries 5–7) recomputed all three results files from the
final module bytes, and each matched byte for byte:
- `baseline_repro.json` `d1c8b06dbb479f34332bb65563dd0d14bcaa169d01cd8e87bf86bb53794aecff`
- `simulation_controls.json` `6ae8b228322362d03b08e0b94570f202df70d8b8bc3440cc68fca38961d5078a`
- `empirical_comparison.json` `a588404ed3839b2efbbe7496a52dccd34763f7fca6fd0d63340759f5018d2851`

The original bytes of the pre-run docstring sentence (item 1 above) were not kept; see the
provenance note in VERDICT.md §1. The test file was
tidied in the same pass: a no-op assertion and its unused `math` import were removed. No
test logic changed.
