# SNI coverage census 2026-10-13

Scope: base `5b6fd2e8798886141e074d50a4468c063d44ad28`; method = stdlib `sys.monitoring` LINE events on SNI code objects plus `ast` function-body statements (docstrings excluded); `coverage` was not importable; suite result `2679 passed, 1 skipped, 96 xfailed, 20 warnings in 959.38s (0:15:59)` (pytest exit 0). Measurement and census only; no production code or test was changed.

Authority flags (literal false everywhere this census refers to them):

- `rank_authority`: false
- `gate_authority`: false
- `size_authority`: false
- `signal_authority`: false
- `escalation_authority`: false
- `trade_authority`: false

This file does not feed a ranker, gate, sizer, signal, escalation, or trade path. Identity ids remain caller-supplied opaque strings owned by Stock Identity / Data OS. Residuals and stress statistics named below are descriptive.

## Summary

35 modules from `git ls-files 'research/single_name_intelligence/*.py'` (count matches Table 1). 5840 executable function-body statement lines; 5085 executed (87.07%). 520 top-level functions and methods: 16 NEVER, 176 PARTIAL, 328 EXECUTED.

NEVER functions per zone: SEALED-S2-ADJACENT 5, SEAL-TOOLING 1, DRAFT-GUARD 0, SEALED-S1 3, OTHER 7.

Zone line coverage: SEALED-S2-ADJACENT 1145/1281 (89.38%), SEAL-TOOLING 649/723 (89.76%), DRAFT-GUARD 627/704 (89.06%), SEALED-S1 1403/1513 (92.73%), OTHER 1261/1619 (77.89%).

Executable lines are unique `ast` statement line numbers inside function and method bodies, including nested defs, excluding the body's docstring. A function is EXECUTED when every such line was hit, PARTIAL when some were hit, NEVER when none were. Module-level `if __name__ == "__main__"` statements are outside function bodies and are not counted.

Paths in the tables are relative to `research/single_name_intelligence/`.

## Table 1 — Per-module

Sorted by zone (SEALED-S2-ADJACENT, SEAL-TOOLING, DRAFT-GUARD, SEALED-S1, OTHER) then ascending executed %. NEVER/PARTIAL columns are function counts.

| module | zone | executable lines | executed lines | % | NEVER functions | PARTIAL functions |
|---|---|---:|---:|---:|---:|---:|
| `event_response/p04_v2_draft_loader.py` | SEALED-S2-ADJACENT | 182 | 148 | 81.32 | 0 | 7 |
| `event_response/run_s2.py` | SEALED-S2-ADJACENT | 468 | 381 | 81.41 | 4 | 8 |
| `event_response/s2_outcomes.py` | SEALED-S2-ADJACENT | 73 | 68 | 93.15 | 0 | 3 |
| `event_response/build_seal.py` | SEALED-S2-ADJACENT | 101 | 98 | 97.03 | 0 | 2 |
| `event_response/s2_clocklaw.py` | SEALED-S2-ADJACENT | 34 | 33 | 97.06 | 0 | 1 |
| `event_response/s2_collapse.py` | SEALED-S2-ADJACENT | 145 | 141 | 97.24 | 1 | 0 |
| `event_response/s2_selection.py` | SEALED-S2-ADJACENT | 73 | 72 | 98.63 | 0 | 1 |
| `event_response/s2_splits.py` | SEALED-S2-ADJACENT | 75 | 74 | 98.67 | 0 | 1 |
| `event_response/s2_loaders.py` | SEALED-S2-ADJACENT | 34 | 34 | 100.00 | 0 | 0 |
| `event_response/s2_seal.py` | SEALED-S2-ADJACENT | 33 | 33 | 100.00 | 0 | 0 |
| `event_response/s2_state.py` | SEALED-S2-ADJACENT | 42 | 42 | 100.00 | 0 | 0 |
| `event_response/s2_stats.py` | SEALED-S2-ADJACENT | 21 | 21 | 100.00 | 0 | 0 |
| `evaluation/seal_full_check.py` | SEAL-TOOLING | 305 | 263 | 86.23 | 1 | 10 |
| `evaluation/sni_eval_ledger.py` | SEAL-TOOLING | 418 | 386 | 92.34 | 0 | 13 |
| `common/sni_join_guard.py` | DRAFT-GUARD | 185 | 152 | 82.16 | 0 | 8 |
| `common/sni_seal.py` | DRAFT-GUARD | 301 | 274 | 91.03 | 0 | 10 |
| `common/sni_inference.py` | DRAFT-GUARD | 218 | 201 | 92.20 | 0 | 12 |
| `residual/s1_prereg.py` | SEALED-S1 | 33 | 27 | 81.82 | 0 | 1 |
| `residual/run_s1.py` | SEALED-S1 | 616 | 554 | 89.94 | 2 | 11 |
| `residual/s1_data.py` | SEALED-S1 | 86 | 78 | 90.70 | 1 | 4 |
| `residual/build_seal.py` | SEALED-S1 | 117 | 108 | 92.31 | 0 | 4 |
| `residual/s1_manifest.py` | SEALED-S1 | 98 | 91 | 92.86 | 0 | 6 |
| `residual/s1_challenger.py` | SEALED-S1 | 68 | 64 | 94.12 | 0 | 3 |
| `residual/s1_report.py` | SEALED-S1 | 294 | 282 | 95.92 | 0 | 5 |
| `residual/s1_decomposition.py` | SEALED-S1 | 92 | 90 | 97.83 | 0 | 1 |
| `residual/s1_direction.py` | SEALED-S1 | 22 | 22 | 100.00 | 0 | 0 |
| `residual/s1_infoleak.py` | SEALED-S1 | 17 | 17 | 100.00 | 0 | 0 |
| `residual/s1_stats.py` | SEALED-S1 | 20 | 20 | 100.00 | 0 | 0 |
| `residual/s1_synth.py` | SEALED-S1 | 50 | 50 | 100.00 | 0 | 0 |
| `us_stress/stress_set.py` | OTHER | 662 | 456 | 68.88 | 7 | 26 |
| `acceptance/ticker_branch_scan.py` | OTHER | 453 | 344 | 75.94 | 0 | 22 |
| `acceptance/a33_reference_evidence_check.py` | OTHER | 162 | 134 | 82.72 | 0 | 8 |
| `acceptance/render_matrix.py` | OTHER | 108 | 101 | 93.52 | 0 | 4 |
| `us_transfer/a8_draft_loader.py` | OTHER | 82 | 78 | 95.12 | 0 | 2 |
| `acceptance/sni_copy_guard.py` | OTHER | 152 | 148 | 97.37 | 0 | 3 |

Table 1 row count = 35 = `git ls-files 'research/single_name_intelligence/*.py'` count.

## Table 2 — Top 40 untested functions

Rows 1–16 are the complete NEVER set, ranked by (zone weight × executable body lines) with weights SEALED-S2-ADJACENT=4, SEAL-TOOLING=4, DRAFT-GUARD=3, SEALED-S1=2, OTHER=1. Only 16 functions have zero body-line hits, so rows 17–40 are PARTIAL functions ranked by (zone weight × unhit body lines). The `lines` column is unhit body-statement count (equal to executable lines for NEVER).

| rank | module | function | line span | zone | lines | why it matters |
|---:|---|---|---|---|---:|---|
| 1 | `event_response/run_s2.py` | `main` | 1089-1120 | SEALED-S2-ADJACENT | 25 | dispatches S2 generate vs `--check` and calls the data/ ledger refusal |
| 2 | `event_response/run_s2.py` | `run_check` | 1058-1086 | SEALED-S2-ADJACENT | 21 | byte-compares regenerated S2 outputs against the sealed tree |
| 3 | `us_stress/stress_set.py` | `_minimal_yaml_load` | 284-361 | OTHER | 61 | parses nested profile YAML when PyYAML is absent |
| 4 | `event_response/run_s2.py` | `refuse_data_path` | 92-102 | SEALED-S2-ADJACENT | 8 | exits 2 when `--trial-ledger-path` resolves under `data/` |
| 5 | `residual/run_s1.py` | `_tree_equal` | 1119-1130 | SEALED-S1 | 11 | recursively byte-compares sealed S1 trees during `--check` |
| 6 | `event_response/run_s2.py` | `_fmt` | 743-748 | SEALED-S2-ADJACENT | 5 | formats report numbers and writes an em-dash for None |
| 7 | `us_stress/stress_set.py` | `_parse_scalar` | 251-268 | OTHER | 17 | coerces YAML null/bool/float/quoted scalars in the fallback parser |
| 8 | `evaluation/seal_full_check.py` | `_print_result` | 650-659 | SEAL-TOOLING | 4 | prints per-study compared/identical/ulp/failures counts |
| 9 | `event_response/s2_collapse.py` | `_programme_key` | 106-113 | SEALED-S2-ADJACENT | 4 | maps an execution row to its programme via `member_ids` |
| 10 | `us_stress/stress_set.py` | `main` | 1150-1170 | OTHER | 15 | CLI writes the stress table or the data-absent stub |
| 11 | `us_stress/stress_set.py` | `_write_table_report` | 1103-1147 | OTHER | 13 | writes `STRESS_SET.json` and the descriptive markdown report |
| 12 | `us_stress/stress_set.py` | `_split_key_value` | 271-281 | OTHER | 10 | splits YAML `key:value` while ignoring colons inside quotes |
| 13 | `us_stress/stress_set.py` | `_strip_inline_comment` | 238-248 | OTHER | 10 | strips `#` comments outside quoted YAML scalars |
| 14 | `residual/run_s1.py` | `_byte_compare` | 1110-1116 | SEALED-S1 | 5 | drives S1 `--check` over report, manifest, results, observations, ledger |
| 15 | `us_stress/stress_set.py` | `_write_absent_report` | 1080-1100 | OTHER | 6 | writes the data-absent stub with every authority flag false |
| 16 | `residual/s1_data.py` | `InjectableStore.read_columns` | 159-162 | SEALED-S1 | 3 | returns injected columns without the float coerce used by `frame()` |
| 17 | `evaluation/seal_full_check.py` | `main` | 662-726 | SEAL-TOOLING | 18 | PARTIAL (18 of 45 unhit); CLI exit 2 on missing input_ref, exit 1 on porcelain drift or DIFFERS |
| 18 | `event_response/p04_v2_draft_loader.py` | `validate_draft` | 186-308 | SEALED-S2-ADJACENT | 17 | PARTIAL (17 of 101 unhit); refuses unsafe P04 v2 DRAFT states before any register or seal |
| 19 | `residual/run_s1.py` | `main` | 1148-1209 | SEALED-S1 | 22 | PARTIAL (22 of 53 unhit); S1 CLI `--check` path and `data/` ledger refusal |
| 20 | `evaluation/sni_eval_ledger.py` | `_validate_score` | 631-698 | SEAL-TOOLING | 9 | PARTIAL (9 of 48 unhit); refuses SCORE rows on BRIER_MISMATCH, unsorted ids, and exclusion-count drift |
| 21 | `evaluation/sni_eval_ledger.py` | `EvalLedger.verify_chain` | 754-793 | SEAL-TOOLING | 8 | PARTIAL (8 of 32 unhit); recomputes hashes and re-runs kind validation on the prefix |
| 22 | `common/sni_seal.py` | `verify_seal` | 331-483 | DRAFT-GUARD | 10 | PARTIAL (10 of 117 unhit); verifies DRAFT seal bytes, authority flags, and canonical cells |
| 23 | `common/sni_join_guard.py` | `_as_datetime` | 209-223 | DRAFT-GUARD | 8 | PARTIAL (8 of 14 unhit); parses then-known timestamps including `Z` and date-only forms |
| 24 | `evaluation/seal_full_check.py` | `_walk_authority` | 147-167 | SEAL-TOOLING | 6 | PARTIAL (6 of 17 unhit); raises if a nested authority flag is not literal false |
| 25 | `event_response/p04_v2_draft_loader.py` | `_check_tune_empty` | 157-183 | SEALED-S2-ADJACENT | 6 | PARTIAL (6 of 25 unhit); refuses a TUNE split that describes members |
| 26 | `event_response/run_s2.py` | `compute_outcomes` | 121-148 | SEALED-S2-ADJACENT | 6 | PARTIAL (6 of 18 unhit); skips window returns for retired (protocol, split) cells |
| 27 | `event_response/run_s2.py` | `pooled_prior` | 262-279 | SEALED-S2-ADJACENT | 6 | PARTIAL (6 of 13 unhit); ABSTAINS the pooled TRAIN prior when cluster-N is below the floor |
| 28 | `acceptance/ticker_branch_scan.py` | `_minimal_yaml_load` | 208-285 | OTHER | 20 | PARTIAL (20 of 61 unhit); fallback YAML parser for profile ticker literals when PyYAML is absent |
| 29 | `event_response/run_s2.py` | `render_report` | 751-983 | SEALED-S2-ADJACENT | 5 | PARTIAL (5 of 160 unhit); writes the sealed REPORT.md family×h×split block order |
| 30 | `acceptance/ticker_branch_scan.py` | `_match_pattern_constants` | 469-500 | OTHER | 19 | PARTIAL (19 of 31 unhit); extracts compare/match/dispatch constants that would mint ticker branches |
| 31 | `common/sni_join_guard.py` | `validate_fact` | 242-304 | DRAFT-GUARD | 6 | PARTIAL (6 of 51 unhit); rejects join facts that are not then-known at as_of |
| 32 | `evaluation/seal_full_check.py` | `_load_s1_build_seal` | 481-508 | SEAL-TOOLING | 4 | PARTIAL (4 of 16 unhit); loads residual/build_seal.py by path so S2's builder cannot bind instead |
| 33 | `event_response/p04_v2_draft_loader.py` | `_parse_utc_timestamp` | 78-88 | SEALED-S2-ADJACENT | 4 | PARTIAL (4 of 10 unhit); refuses naive or unparseable vintage timestamps |
| 34 | `event_response/run_s2.py` | `build_block` | 295-418 | SEALED-S2-ADJACENT | 4 | PARTIAL (4 of 24 unhit); builds one family×h×split evaluation block including the pooled-prior leg |
| 35 | `event_response/run_s2.py` | `evaluate_family` | 155-216 | SEALED-S2-ADJACENT | 4 | PARTIAL (4 of 29 unhit); evaluates one family at one horizon and split, including RETIRED cells |
| 36 | `acceptance/a33_reference_evidence_check.py` | `structural_errors` | 103-187 | OTHER | 15 | PARTIAL (15 of 51 unhit); rejects malformed A33 coverage reports before a floor claim |
| 37 | `residual/run_s1.py` | `evaluate_p03` | 472-517 | SEALED-S1 | 6 | PARTIAL (6 of 35 unhit); P03 ULP/stability evaluation of sealed residual families |
| 38 | `residual/s1_prereg.py` | `_forbidden_truthy_authority` | 116-132 | SEALED-S1 | 6 | PARTIAL (6 of 13 unhit); walks nested objects and raises on a truthy authority key |
| 39 | `common/sni_join_guard.py` | `JoinVerdict.__post_init__` | 163-181 | DRAFT-GUARD | 4 | PARTIAL (4 of 12 unhit); freezes ALLOWED/REFUSED and raises if any authority flag is not false |
| 40 | `common/sni_join_guard.py` | `check_join` | 372-447 | DRAFT-GUARD | 4 | PARTIAL (4 of 37 unhit); decides ALLOWED vs REFUSED for a join request |

## Proposed MUT6 lanes

No lane proposes editing `residual/`.

1. **S2 CLI seal-check** — `event_response/run_s2.py` `main`, `run_check`, `refuse_data_path`, `_fmt`. A killing test must pin: `--check` byte-compares regenerated outputs to the sealed tree and returns 1 on any named difference; `--trial-ledger-path` under `data/` prints REFUSED and exits 2; `_fmt(None)` is the em-dash. Zone rule: SEALED-S2-ADJACENT — edits only if the S2 seal check stays at failures=0.

2. **S2 programme key** — `event_response/s2_collapse.py` `_programme_key`. A killing test must pin: a row whose `id` is listed in `programme["member_ids"]` returns that programme key; an unmatched id returns None and does not merge. Zone rule: SEALED-S2-ADJACENT — edits only if the S2 seal check stays at failures=0.

3. **P04 v2 DRAFT refuse paths** — `event_response/p04_v2_draft_loader.py` `validate_draft`, `_check_tune_empty`, `_check_authority_block`, `_parse_utc_timestamp`. A killing test must pin: TUNE that describes members refuses; any authority flag not literal false refuses; a naive or unparseable vintage timestamp refuses; the loader never registers or seals. Zone rule: SEALED-S2-ADJACENT — edits only if the S2 seal check stays at failures=0.

4. **S2 retired-cell and pooled-prior abstain** — `event_response/run_s2.py` `compute_outcomes`, `pooled_prior`, `evaluate_family`, `build_block`. A killing test must pin: a retired (protocol, split) cell never resolves a window return; pooled TRAIN prior ABSTAINS with a named reason when cluster-N is below the floor (never a 50/50 fill). Zone rule: SEALED-S2-ADJACENT — edits only if the S2 seal check stays at failures=0.

5. **Seal-full-check CLI** — `evaluation/seal_full_check.py` `main`, `_print_result`, `_walk_authority`, `_load_s1_build_seal`. A killing test must pin: missing input_ref returns 2 without fetching; porcelain drift after regeneration returns 1; a nested truthy authority flag raises; `_load_s1_build_seal` binds residual/build_seal.py even when event_response/ is earlier on sys.path. Zone rule: SEAL-TOOLING.

6. **Eval ledger SCORE and chain** — `evaluation/sni_eval_ledger.py` `_validate_score`, `EvalLedger.verify_chain`. A killing test must pin: BRIER_MISMATCH, SCORED_IDS_UNSORTED, exclusion-count drift, SEQ_MISMATCH, and PREV_HASH_MISMATCH all refuse or report a named violation; validation does not consult wall-clock time. Zone rule: SEAL-TOOLING.

7. **DRAFT join-guard then-known** — `common/sni_join_guard.py` `_as_datetime`, `validate_fact`, `JoinVerdict.__post_init__`, `check_join`. A killing test must pin: unparseable / `Z` / date-only timestamps; a fact known after as_of is refused; ALLOWED cannot carry reasons; every authority flag on the verdict is literal false. Zone rule: DRAFT-GUARD.

8. **DRAFT seal verify remainder** — `common/sni_seal.py` `verify_seal`. A killing test must pin the remaining unhit branches of seal verification (authority flags, canonical cells, mismatched bytes) so a mutated verifier cannot return OK. Zone rule: DRAFT-GUARD.

9. **US stress YAML fallback and CLI** — `us_stress/stress_set.py` `_minimal_yaml_load`, `_parse_scalar`, `_split_key_value`, `_strip_inline_comment`, `main`, `_write_absent_report`, `_write_table_report`. A killing test must pin: the fallback parser without PyYAML; CLI with no loaded stock closes writes the data-absent stub; both reports keep `descriptive_only: true`, `causal_claims: none`, and all authority flags false. Zone rule: OTHER.

10. **S1 `--check` helpers (tests only)** — `residual/run_s1.py` `_tree_equal`, `_byte_compare`, `main`; `residual/s1_data.py` `InjectableStore.read_columns`; `residual/s1_prereg.py` `_forbidden_truthy_authority`. A killing test must pin: `--check` tree/ledger compare; `read_columns` returning raw injected columns; a nested truthy `*_authority` key raising. Zone rule: SEALED-S1 — tests only, `residual/` bytes may not change.

## Existing mutation sweeps

MUTATION_SWEEP_A33_MATRIX_2026-10-13.md
MUTATION_SWEEP_BRANCH_COPY_2026-10-13.md
MUTATION_SWEEP_BUILD_SEAL_2026-10-13.md
MUTATION_SWEEP_COMMON_2026-10-13.md
MUTATION_SWEEP_DECOMP_INFOLEAK_2026-10-13.md
MUTATION_SWEEP_DRAFT_LOADERS_2026-10-13.md
MUTATION_SWEEP_EVENT_STRESS_2026-10-13.md
MUTATION_SWEEP_LEDGER_SEAL_2026-10-13.md
MUTATION_SWEEP_MANIFEST_SYNTH_2026-10-13.md
MUTATION_SWEEP_PREREG_CHALLENGER_2026-10-13.md
MUTATION_SWEEP_REPORT_S2SEAL_2026-10-13.md
MUTATION_SWEEP_S2_STATE_LOADERS_2026-10-13.md
MUTATION_SWEEP_STATS_DIRECTION_2026-10-13.md

## What this census does NOT prove

Coverage is not correctness. Executed is not asserted: a line hit by a test that asserts nothing is still listed as executed. PARTIAL means some body statements ran; the unhit branch may be the one that refuses, ABSTAINS, or compares sealed bytes. NEVER CLI entry points (`main`, `run_check`) can still be live in operator runs. `sys.monitoring` LINE events count Python statement lines, not bytecode branches inside a line. Import-time execution of a def's decorator is not a function-body hit. This census does not claim mutation-kill power, causal news impact, or any authority grant.
