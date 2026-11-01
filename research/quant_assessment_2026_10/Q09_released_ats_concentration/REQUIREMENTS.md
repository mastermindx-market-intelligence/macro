# Q09 requirements → proof

Test file: `tests/test_offexchange_venue_concentration.py`
Module: `engine/offexchange_venue_concentration.py`

| # | Requirement (brief) | Tests | Artifact evidence |
|---|---|---|---|
| 1 | The reporting week is never used as the information-availability date. | `test_req1_unknown_availability_is_never_admitted_even_after_reporting_week`, `test_req1_witness_reporting_period_cannot_replace_publication`, `test_req1_release_identity_qualification_separates_store_bound_from_publisher`, `test_req1_split_clock_enforced_refuses_leaky_split` | PREREG §0/§3: store-first-seen upper bounds only. results.json `release_identity` (0/21 publisher identity) and `split.split_respects_store_clock=true`; evaluate.py now REFUSES (SystemExit) when the split violates the clock (PREREG_AMENDMENT A3). |
| 2 | T1/T2 or other staggered coverage cannot be combined as if simultaneously complete. | `test_req2_t1_only_state_is_partial_and_combination_refused`, `test_req2_complete_state_uses_latest_tier_time_as_of`, `test_req2_tier_gated_combination_excludes_unrequired_tier` | Confirmatory comparison: T1/T2 only, with tier-ambiguous tickers dropped (results.json `support`, 413 in 20260629). Descriptive concentration: also T1+T2 only, gated by `coverage_snapshot` + `combine_tier_volumes` (results.json `descriptive.coverage` all `complete`; excluded OTCE fraction 0.039 ATS / 0.285 non-ATS printed; PREREG_AMENDMENT A2). Only the verbatim incumbent baseline reproduction stays all-tier, labelled as such. The OTCE gap in the collector is noted in VERDICT. |
| 3 | Venue shares conserve the reported denominator and account for unknown/unmapped mass. | `test_req3_unknown_and_unmapped_mass_is_kept_not_dropped`, `test_req3_reported_total_below_rows_raises`, `test_req3_incumbent_style_empty_mpid_filter_would_lose_all_nonats_mass` | results.json `incumbent_mpid_filter_on_nonats_dropped_fraction=1.0`, `nonats_unknown_share_de_minimis=0.256` (T1+T2). |
| 4 | Corrections create a new result vintage without erasing the earlier public state. | `test_req4_correction_appends_vintage_and_keeps_history`, `test_req4_out_of_order_or_unknown_time_vintage_refused` | VintageLedger is append-only. No corrections exist in the store (git: add-only). |
| 5 | Synthetic concentration cases recover one-venue and equal-venue limits. | `test_req5_equal_venue_limit[1,2,5,40]`, `test_req5_one_venue_limit_and_bounds_bracket`, `test_req5_decomposition_is_exact_and_bootstrap_is_block_based`, `test_req5_ratio_bootstrap_matches_inline_reference_draws` | results.json `descriptive` (exact decomposition, HHI bounds); ratio CI via module `moving_block_bootstrap_ratio` with `bootstrap_caveat` (~4 effective blocks). |
| 6 | No institutional accumulation, net buying, live-print or short-interest interpretation is emitted. | `test_req6_vocabulary_guard_rejects[*]`, `test_req6_vocabulary_guard_catches_separator_and_inflection_variants[*]`, `test_req6_guard_walks_keys_and_nested_containers`, `test_req6_descriptive_record_passes_guard_and_names_category` | evaluate.py calls `assert_no_forbidden_interpretation` on the WHOLE results dict and the baseline output before writing (separator-normalised, inflection-aware; PREREG_AMENDMENT A4). Prose (VERDICT/PR_BODY) states restrictions as negations and is reviewed by hand. |
| — | No silent activation (module contract). | `test_no_silent_activation_contract` | `RESEARCH_ONLY=True`, `WIRED=False`. Nothing imports the module. |

Process gates: PREREG.md was frozen (FREEZE.log) before evaluation and never edited. The
post-audit changes live in PREREG_AMENDMENT.md (post-hoc, non-confirmatory; sha256 in
AMENDMENT.log, written before the re-run). evaluate.py refuses to run on a PREREG, amendment
or input hash mismatch, or on a clock-violating split. RUNS.log records 3 runs, all exit 0:
runs 1–2 identical; run 3 (post-amendment) reproduces every confirmatory number and the
baseline output byte-identically, and attests recomputed input hashes plus only the outputs
it wrote.
