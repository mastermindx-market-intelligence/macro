# MUT4F mutation sweep — `s1_report.py` / `s2_seal.py` — 2026-10-13

SNI-local DRAFT contract review. These modules consume caller-supplied
blocks, opaque subject tokens, and owner-supplied identity strings
(Stock Identity / Data OS); they do not mint issuer or security ids.
HISTORICAL-DESCRIPTIVE only: `rank_authority`, `gate_authority`,
`size_authority`, `signal_authority`, `escalation_authority` and
`trade_authority` stay false. Fixtures in the killing tests are
synthetic. No production module was edited.

Harness (not committed): `~/lanes/scratch/mut4f/harness.py`. Seed
`random.Random(20261013)`. Each mutant applied in place, then original
bytes restored and sha256-checked before the next. `git status
--porcelain -- research/` after every mutant: no `runs/` writes
(0 TIMEOUT-UNSAFE).

## Summary

| item | count |
|---|---|
| generated (selected sites) | 60 |
| killed-before (existing importer suite) | 38 |
| survived-before (non-equivalent) | 22 |
| killed-after (new `test_mut4f_*`) | 22 |
| equivalent | 0 |
| timeout | 0 |
| score before | 38 / 60 = 63.3% |
| score after | 60 / 60 = 100% |
| new killing tests | 22 |

Score = killed / (generated − equivalent). Wall-clock of the 60 runs:
608.6 s. 0 xfails. Unmutated importer times: `s1_report` 18.57 s
(64 passed; under the 20 s cap, so 30 mutants), `s2_seal` 4.74 s
(1046 passed; 30 mutants). Combined existing importers + new file:
1113 passed in 23.08 s (0 new failures).

## Operator set and seed

Seed: `20261013`. Max 30 mutants per module, stratified by function
(round-robin over `sorted(function names)`, sites shuffled per function
with the same RNG).

Operators (AST, one site per mutant):

- comparison flip: `<`↔`<=`, `>`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: int `n`→`n+1`, float `x`→`x*1.001`, `True`↔`False`
- `return x` → `return None` (bare `return` / `return None` skipped)
- `and`↔`or`
- deletion of one `if ...: raise` guard

Annotations and docstrings were not mutated. `is` / `in` / `**` are
outside the operator set.

Kill suite (tests that import the module; run with
`timeout 60 python3 -m pytest <tests> -x -q -p no:cacheprovider`):

- `s1_report`: `tests/test_sni_p03_ulp_stability.py`,
  `tests/test_sni_s1_v1_1_hardening.py`,
  `tests/test_sni_quarantine_fence.py`,
  `tests/test_sni_s1_report_order.py`
- `s2_seal`: `tests/test_sni_s2_abstain.py`,
  `tests/test_sni_s2_ledger_order.py`,
  `tests/test_sni_s2_info_leak.py`,
  `tests/test_sni_s2_property.py`,
  `tests/test_sni_s2_collapse.py`,
  `tests/test_sni_injection_safety.py`,
  `tests/test_sni_mutation_event_stress.py`,
  `tests/test_sni_quarantine_fence.py`,
  `tests/test_sni_s2_v1_1_hardening.py`,
  `tests/test_sni_run_seal_repro.py`

`tests/test_sni_no_ticker_branches.py` mentions both paths as strings
and does not import either module. `tests/test_sni_s2_seal_integrity.py`
does not import `s2_seal`.

## Per-module table

| module | candidate sites | selected | killed-before | survived-before | equivalent | timeout | killed-after | score before → after |
|---|---|---|---|---|---|---|---|---|
| `s1_report.py` | 148 | 30 | 13 | 17 | 0 | 0 | 17 | 13/30 → 30/30 |
| `s2_seal.py` | 39 | 30 | 25 | 5 | 0 | 0 | 5 | 25/30 → 30/30 |
| total | 187 | 60 | 38 | 22 | 0 | 0 | 22 | 38/60 → 60/60 |

Selected-by-function (after stratification):

| module | function | sites | selected |
|---|---|---|---|
| s1_report | `_appendix_section` | 1 | 1 |
| s1_report | `_below_floor_receipt` | 4 | 2 |
| s1_report | `_coverage_section` | 10 | 2 |
| s1_report | `_render_version_record_md` | 1 | 1 |
| s1_report | `_sanitize_finding_words` | 5 | 2 |
| s1_report | `appendix_cells` | 5 | 2 |
| s1_report | `below_floor_count` | 4 | 2 |
| s1_report | `block_key` | 1 | 1 |
| s1_report | `block_lead` | 6 | 1 |
| s1_report | `cells_with_unadjusted_p` | 5 | 1 |
| s1_report | `criterion_met_rows` | 3 | 1 |
| s1_report | `empty_exclusions` | 6 | 1 |
| s1_report | `exemplar_table` | 3 | 1 |
| s1_report | `family_alpha` | 3 | 1 |
| s1_report | `family_effective_n` | 4 | 1 |
| s1_report | `family_wise_clearing` | 6 | 1 |
| s1_report | `is_retired_block` | 2 | 1 |
| s1_report | `lead_change_counts` | 14 | 1 |
| s1_report | `m2_over_m1_sentence` | 10 | 1 |
| s1_report | `make_block` | 2 | 1 |
| s1_report | `parse_block_key` | 8 | 1 |
| s1_report | `render_report_md` | 10 | 1 |
| s1_report | `s0_criterion_holds` | 13 | 1 |
| s1_report | `verdict_bucket` | 11 | 1 |
| s1_report | `version_record_obj` | 11 | 1 |
| s2_seal | `<module>` | 21 | 12 |
| s2_seal | `build_prereg_spec` | 3 | 3 |
| s2_seal | `canonical_json` | 3 | 3 |
| s2_seal | `itemized_grid` | 1 | 1 |
| s2_seal | `ledger_family` | 1 | 1 |
| s2_seal | `prereg_digest` | 1 | 1 |
| s2_seal | `refuse_nonfalse_authority` | 8 | 8 |
| s2_seal | `sha256_hex` | 1 | 1 |

Nine `s2_seal` `<module>` constant sites sat outside the 30-cap sample
and were not run. They are not in the score.

## Surviving-mutant list with killing test name

All 22 non-equivalent survivors were re-applied after the new tests
were added and failed the named test (22/22 KILLED-AFTER).

| id | file:line | function | original → mutated | killing test |
|---|---|---|---|---|
| s1_report_02 | `s1_report.py:368` | `_below_floor_receipt` | BoolOp `or` → `and` (`statistic` fallback) | `test_mut4f_s1_report__below_floor_receipt_1` |
| s1_report_05 | `s1_report.py:357` | `_sanitize_finding_words` | `return {k: ...}` → `return None` | `test_mut4f_s1_report__sanitize_finding_words_1` |
| s1_report_06 | `s1_report.py:169` | `appendix_cells` | `pv < 0.05` → `pv <= 0.05` | `test_mut4f_s1_report_appendix_cells_1` |
| s1_report_07 | `s1_report.py:254` | `below_floor_count` | `n = 0` → `n = 1` | `test_mut4f_s1_report_below_floor_count_1` |
| s1_report_09 | `s1_report.py:116` | `block_lead` | TUNE-RETIRED `return (f"criterion not assessable...")` → `return None` | `test_mut4f_s1_report_block_lead_1` |
| s1_report_12 | `s1_report.py:69` | `empty_exclusions` | `return {excluded_listed: 0, ...}` → `return None` | `test_mut4f_s1_report_empty_exclusions_1` |
| s1_report_15 | `s1_report.py:127` | `family_effective_n` | fallback `return 0` → `return None` | `test_mut4f_s1_report_family_effective_n_1` |
| s1_report_16 | `s1_report.py:159` | `family_wise_clearing` | `pv < a` → `pv <= a` | `test_mut4f_s1_report_family_wise_clearing_1` |
| s1_report_18 | `s1_report.py:277` | `lead_change_counts` | BoolOp `and` → `or` (TRAIN BLOCKED-AS-EVIDENCE) | `test_mut4f_s1_report_lead_change_counts_1` |
| s1_report_19 | `s1_report.py:244` | `m2_over_m1_sentence` | BoolOp `or` → `and` (HK verdict fallback) | `test_mut4f_s1_report_m2_over_m1_sentence_1` |
| s1_report_22 | `s1_report.py:476` | `render_report_md` | BoolOp `or` → `and` (default `seal_path`) | `test_mut4f_s1_report_render_report_md_1` |
| s1_report_23 | `s1_report.py:94` | `s0_criterion_holds` | BoolOp `or` → `and` (`test` fallback) | `test_mut4f_s1_report_s0_criterion_holds_1` |
| s1_report_25 | `s1_report.py:323` | `version_record_obj` | `escalation: False` → `True` | `test_mut4f_s1_report_version_record_obj_1` |
| s1_report_26 | `s1_report.py:367` | `_below_floor_receipt` | BoolOp `or` → `and` (`ci` fallback) | `test_mut4f_s1_report__below_floor_receipt_2` |
| s1_report_28 | `s1_report.py:359` | `_sanitize_finding_words` | list-comp `return` → `return None` | `test_mut4f_s1_report__sanitize_finding_words_2` |
| s1_report_29 | `s1_report.py:169` | `appendix_cells` | `0.05` → `0.05*1.001` | `test_mut4f_s1_report_appendix_cells_2` |
| s1_report_30 | `s1_report.py:258` | `below_floor_count` | `n += 1` → `n += 2` | `test_mut4f_s1_report_below_floor_count_2` |
| s2_seal_01 | `s2_seal.py:216` | `<module>` | `INFO_LEAK_STEP_TOLERANCE` `1e-6` → `1e-6*1.001` | `test_mut4f_s2_seal_module_1` |
| s2_seal_16 | `s2_seal.py:100` | `refuse_nonfalse_authority` | delete `if not isinstance(mapping, dict): raise` | `test_mut4f_s2_seal_refuse_nonfalse_authority_1` |
| s2_seal_26 | `s2_seal.py:96` | `refuse_nonfalse_authority` | delete missing-`authority_flags` raise | `test_mut4f_s2_seal_refuse_nonfalse_authority_2` |
| s2_seal_28 | `s2_seal.py:197` | `<module>` | `TRAILING63_SESSIONS` `63` → `64` | `test_mut4f_s2_seal_module_2` |
| s2_seal_30 | `s2_seal.py:194` | `<module>` | `MIN_TRAIN_CLUSTERS_POOLED_PRIOR` `2` → `3` | `test_mut4f_s2_seal_module_3` |

Re-verify FAIL lines (two samples; all 22 killed):

- s1_report_02 / `test_mut4f_s1_report__below_floor_receipt_1`:
  `assert {} == {'delta_R2': 0.01}` (`statistic` fallback became `{}`)
- s2_seal_01 / `test_mut4f_s2_seal_module_1`:
  `assert 1.0009999999999998e-06 == 1e-06`

The existing importer suite never called `_below_floor_receipt` or
`empty_exclusions` directly, never passed a dict/list through
`_sanitize_finding_words`, never hit `p == 0.05` / `p == α` boundaries,
never rendered a report without `seal_path`, and never pinned
`INFO_LEAK_STEP_TOLERANCE`, `TRAILING63_SESSIONS`, or
`MIN_TRAIN_CLUSTERS_POOLED_PRIOR` as literals.

## Equivalent arguments

None. Every selected survivor was distinguishable by a targeted test.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
censuses four fence points in these two files:

- `event_response/s2_seal.py:177` — `SPLIT_QUARANTINE_START = date(2026, 10, 1)`
- `event_response/s2_seal.py:416` — sealed TUNE/QUARANTINE split strings
- `event_response/s2_seal.py:419` — sealed TUNE-purge string
- `residual/s1_report.py:417` — report prose TUNE window `2024-01-01..2026-10-01`

Three candidate sites on `s2_seal.py:177` (`2026`→`2027`, `10`→`11`,
`1`→`2`) were excluded. Lines 416, 419, and `s1_report.py:417` are
string literals and produced no operator-set sites.

## What this does NOT prove

Mutation score is test strength against this operator set and this
sampled site list, not statistical validity of S0 criterion, family-wise
α, or sealed prereg bytes. Unselected `s1_report` sites (118 of 148)
and unselected `s2_seal` `<module>` constants (9 of 21) are unscored.
No acceptance-matrix row moves to DONE. Nothing here feeds a ranker,
gate, sizer, signal, escalation, or trade path.
