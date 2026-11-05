# MUT5D mutation sweep — `run_s2.py` first half — 2026-10-13

SNI-local DRAFT contract review. This sweep measures **test strength** of
the existing importer tests against functions defined in
`event_response/run_s2.py` before line 481 (`generate_outputs`, exclusive):
`proper_score_line_for` .. `maybe_log_retirement`. It does not move any
acceptance row to DONE. Authority flags stay false; identity ids remain
caller-supplied opaque strings owned by Stock Identity / Data OS. Fixtures
in the killing tests are synthetic. Residuals and event-study numbers are
descriptive, never causal, never a news-impact claim (A24). An unestimable
family still ABSTAINS (A25).

This module is an SNI-local DRAFT contract that consumes owner-supplied
values (pinned blobs, split labels, opaque issuer keys, ledger rows). This
sweep does not re-implement Data OS identity, Company Event/Earnings, FIF,
Capital Structure, Stock Identity, Options, Research Vault, or
qledger/Evaluation. No production module was edited.

Harness (not committed): `~/lanes/scratch/mut5d/harness.py`. Seed
`random.Random(20261013)`. Each mutant applied in place, then original
bytes restored and sha256-checked before the next. `git status
--porcelain -- research/` after every mutant: no `runs/` writes
(0 TIMEOUT-UNSAFE). Wall-clock of the 30 runs: 60.2 s.

Existing tests that import `run_s2`:

- `tests/test_sni_s2_abstain.py` — `abstention_state`, `plain_word_null`, `build_block`
- `tests/test_sni_s2_info_leak.py` — `maybe_log_retirement`
- `tests/test_sni_s2_v1_1_hardening.py` — `run_s2` module, `generate_outputs`, `verify_seal`, `evaluate_family`, `compute_outcomes`, `proper_score_line_for`
- `tests/test_sni_s2_seal_integrity.py` — `verify_seal`
- `tests/test_sni_quarantine_fence.py` — `render_report`

`tests/test_sni_s2_cli.py` names `run_s2.py` as a subprocess path and does
not import the module; it was kept out of the kill suite so a mutant never
runs `main()` against the committed `runs/` tree. `tests/test_sni_injection_safety.py`
mentions the path as a string. `tests/test_sni_mutation_build_seal.py`
installs a fake `run_s2` module.

Unmutated importer tests: 53 passed in 2.18 s (under the 20 s cap, so the
30-mutant budget applied). New killing tests: 13 passed in 0.57 s on
unmutated code. Importer tests plus the new file: 66 passed in 2.34 s
(0 new failures).

## Summary

| item | count |
|---|---|
| generated (selected sites) | 30 |
| killed-before (existing importer suite) | 17 |
| survived-before (non-equivalent) | 13 |
| killed-after (new `test_mut5d_*`) | 13 |
| equivalent | 0 |
| timeout | 0 |
| timeout-unsafe | 0 |
| score before | 17 / 30 = 56.7% |
| score after | 30 / 30 = 100% |
| new killing tests | 13 |

Score = killed / (generated − equivalent). Candidate sites before sampling:
66 in the owned function range. 36 unselected sites are unscored.

## Operator set and seed

Seed: `20261013`. Max 30 mutants, stratified by function (round-robin over
`sorted(function names)`, sites shuffled per function with the same RNG).

Operators (AST, one site per mutant):

- comparison flip: `<`↔`<=`, `>`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: int `n`→`n+1`, float `x`→`x*1.001`, `True`↔`False`
- `return x` → `return None` (bare `return` / `return None` skipped; one return per function)
- `and`↔`or`
- deletion of one `if ...: raise` guard

Annotations and docstrings were not mutated. `is` / `in` / `**` are
outside the operator set. Module-level constants and functions defined at
or after line 481 (`generate_outputs` and later) were not collected.
CPython 3.12 comparison and binop operator nodes carry no `lineno`; the
harness located the operator token in the source slice between operands.

Kill suite (tests that import the module; run with
`timeout 60 python3 -m pytest <tests> -x -q -p no:cacheprovider`):

- `tests/test_sni_s2_abstain.py`
- `tests/test_sni_s2_info_leak.py`
- `tests/test_sni_s2_v1_1_hardening.py`
- `tests/test_sni_s2_seal_integrity.py`
- `tests/test_sni_quarantine_fence.py`

## Per-module table

| module | candidate sites | selected | killed-before | survived-before | equivalent | timeout | killed-after | score before → after |
|---|---|---|---|---|---|---|---|---|
| `run_s2.py` (owned range) | 66 | 30 | 17 | 13 | 0 | 0 | 13 | 17/30 → 30/30 |

Selected-by-function (after stratification):

| module | function | sites | selected |
|---|---|---|---|
| run_s2 | `abstention_state` | 6 | 4 |
| run_s2 | `base_commit_detected_at` | 3 | 3 |
| run_s2 | `build_block` | 18 | 3 |
| run_s2 | `compute_outcomes` | 2 | 2 |
| run_s2 | `episode_identity` | 1 | 1 |
| run_s2 | `episode_purged` | 1 | 1 |
| run_s2 | `evaluate_family` | 21 | 3 |
| run_s2 | `exclusion_index_by_family` | 1 | 1 |
| run_s2 | `maybe_log_retirement` | 3 | 3 |
| run_s2 | `plain_word_null` | 2 | 2 |
| run_s2 | `pooled_prior` | 3 | 3 |
| run_s2 | `proper_score_line_for` | 1 | 1 |
| run_s2 | `refuse_data_path` | 4 | 3 |

`build_block` (15 of 18) and `evaluate_family` (18 of 21) sites sat outside
the 30-cap sample and were not run. They are not in the score.

## Surviving-mutant list with killing test name

All 13 non-equivalent survivors were re-applied after the new tests were
added and failed the named test (13/13 KILLED-AFTER).

| id | file:line | function | original → mutated | killing test |
|---|---|---|---|---|
| run_s2_02 | `run_s2.py:89` | `base_commit_detected_at` | `return parsed.isoformat()` → `return None` | `test_mut5d_run_s2_base_commit_detected_at_1` |
| run_s2_03 | `run_s2.py:325` | `build_block` | `r["hit"] or 0` → `or 1` | `test_mut5d_run_s2_build_block_1` |
| run_s2_05 | `run_s2.py:111` | `episode_identity` | `return mk(...)` → `return None` | `test_mut5d_run_s2_episode_identity_1` |
| run_s2_06 | `run_s2.py:118` | `episode_purged` | `return purge_flag(...)` → `return None` | `test_mut5d_run_s2_episode_purged_1` |
| run_s2_07 | `run_s2.py:170` | `evaluate_family` | `baseline == BASELINE_ALWAYS_LONG` → `!=` | `test_mut5d_run_s2_evaluate_family_1` |
| run_s2_13 | `run_s2.py:102` | `refuse_data_path` | `SystemExit(2)` → `SystemExit(3)` | `test_mut5d_run_s2_refuse_data_path_1` |
| run_s2_16 | `run_s2.py:314` | `build_block` | `split_label(...) == split` → `!=` | `test_mut5d_run_s2_build_block_2` |
| run_s2_21 | `run_s2.py:277` | `pooled_prior` | `sum(excesses) / len(excesses)` → `*` | `test_mut5d_run_s2_pooled_prior_1` |
| run_s2_22 | `run_s2.py:98` | `refuse_data_path` | `== ... or ... in parents` → `and` | `test_mut5d_run_s2_refuse_data_path_2` |
| run_s2_25 | `run_s2.py:325` | `build_block` | `r["hit"] or 0` → `and 0` | `test_mut5d_run_s2_build_block_3` |
| run_s2_26 | `run_s2.py:157` | `evaluate_family` | `retired: bool = False` → `True` | `test_mut5d_run_s2_evaluate_family_2` |
| run_s2_28 | `run_s2.py:274` | `pooled_prior` | `cluster-N < MIN_TRAIN_CLUSTERS_POOLED_PRIOR` → `<=` | `test_mut5d_run_s2_pooled_prior_2` |
| run_s2_29 | `run_s2.py:98` | `refuse_data_path` | `resolved == repo_data` → `!=` | `test_mut5d_run_s2_refuse_data_path_3` |

Re-verify FAIL lines (two samples; all 13 killed):

- run_s2_02 / `test_mut5d_run_s2_base_commit_detected_at_1`:
  `assert None == '2026-10-12T01:59:47+00:00'`
- run_s2_13 / `test_mut5d_run_s2_refuse_data_path_1`:
  `assert 3 == 2` (`SystemExit(3).code`)

The existing importer suite never called `base_commit_detected_at`,
`episode_identity`, `episode_purged`, or `refuse_data_path` directly, never
built a TESTED `build_block` with mixed 0/1 hits, never passed
`BASELINE_ALWAYS_LONG` through `evaluate_family` without `retired=True`,
and never pinned the TRAIN pooled-prior mean or the exact-2-cluster
boundary.

## Equivalent arguments

None. Every selected survivor was distinguishable by a targeted test.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
censuses one fence point in this file:

- `event_response/run_s2.py:941` — report prose census window past `2026-10-01`

Line 941 sits after `generate_outputs` and is outside this lane's owned
range. The same review names `run_s2.py:319` (post-hoc QUARANTINE count)
as not a fence point. **No mutant sites were excluded under the QF fence.**

## What this does NOT prove

Mutation score is test strength against this operator set and this sampled
site list, not statistical validity of S2 hit-rate tests, pooled TRAIN
prior, or sealed prereg bytes. Unselected `build_block` (15 of 18) and
`evaluate_family` (18 of 21) sites are unscored. Functions at or after
line 481 (`generate_outputs` and later) belong to the sibling MUT5E lane.
No acceptance-matrix row moves to DONE. Nothing here feeds a ranker,
gate, sizer, signal, escalation, or trade path.
