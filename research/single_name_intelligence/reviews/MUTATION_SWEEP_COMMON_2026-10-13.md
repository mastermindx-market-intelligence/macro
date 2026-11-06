# MUT1A mutation sweep — sni_inference / sni_seal — 2026-10-13

SNI-local DRAFT contract review. This sweep measures **test strength** of
the existing import tests against the two statistical-core modules. It does
not move any acceptance row to DONE. Authority flags stay false; identity
ids remain caller-supplied opaque strings. Fixtures in the killing tests
are synthetic.

Existing tests that import these modules:

- `tests/test_sni_common_inference.py` — `sni_inference`
- `tests/test_sni_common_seal.py` — `sni_seal`
- `tests/test_sni_common_equivalence.py` — both (`s1_prereg` / `s1_stats` /
  `s2_stats` plus common)

Kill suite used for scoring: the two common files plus equivalence with
`test_eq_06*` deselected (sparse worktree has no `runs/` JSON; those two
tests fail collection-time file reads on unmutated code and would
mis-label every mutant as KILLED).

## Summary

| item | count |
|---|---|
| generated (selected) | 60 |
| killed-before | 32 |
| survived-before | 28 |
| killed-after | 28 |
| equivalent | 0 |
| timeout | 0 |
| score before | 32/60 = 53.3% |
| score after | 60/60 = 100% |
| new killing tests | 28 |

Candidate sites before sampling: 225 in `sni_inference.py`, 109 in
`sni_seal.py`. Cap 30 per module, seed `20261013`, stratified by function.

## Operator set and seed

Harness (scratch only, `~/lanes/scratch/mut1a/harness.py`, not committed):

- comparison flip: `<`↔`>`, `<=`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: `int n → n+1`, `float x → x*1.001`, `True`↔`False`
- `return x` → `return None` (one return per function)
- `and`↔`or`
- deletion of one `if ...: raise` guard (`pass`)

`random.Random(20261013)` round-robin over shuffled per-function site lists.
Identity mutants (`0.0 * 1.001 == 0.0`) were dropped before sampling.

Each mutant was applied in place, then
`timeout 60 python3 -m pytest <import tests> -x -q -p no:cacheprovider`
ran, then original bytes were restored and sha256-checked before the next.

## Per-module table

| module | candidates | selected | killed-before | survived-before | killed-after | equivalent | timeout | score before | score after |
|---|---|---|---|---|---|---|---|---|---|
| `sni_inference.py` | 225 | 30 | 17 | 13 | 13 | 0 | 0 | 17/30 | 30/30 |
| `sni_seal.py` | 109 | 30 | 15 | 15 | 15 | 0 | 0 | 15/30 | 30/30 |
| **total** | **334** | **60** | **32** | **28** | **28** | **0** | **0** | **32/60** | **60/60** |

## Surviving-mutant list with killing test name

All 28 non-killed mutants were re-applied against the named new test and
failed (KILLED-after).

### sni_inference.py

| file:line | original → mutated | killing test |
|---|---|---|
| `sni_inference.py:81` | `1029` → `1030` (`_BINOM_COMB_FLOAT_LIMIT`) | `test_mut1a_sni_inference_module_1` |
| `sni_inference.py:88` | `frozen=True` → `False` | `test_mut1a_sni_inference_InferenceResult_1` |
| `sni_inference.py:105` | `to_dict` body → `return None` | `test_mut1a_sni_inference_InferenceResult_to_dict_1` |
| `sni_inference.py:282` | `p0 == 1.0` → `p0 == 1.001` | `test_mut1a_sni_inference__binom_tail_ge_1` |
| `sni_inference.py:290` | `return 1.0` → `return 1.001` (`k >= n`) | `test_mut1a_sni_inference__binom_tail_le_1` |
| `sni_inference.py:246` | empty-logs `return 0.0` → `None` | `test_mut1a_sni_inference__logsumexp_exp_1` |
| `sni_inference.py:220` | n==1 `return float(xs[0])` → `None` | `test_mut1a_sni_inference__percentile_linear_1` |
| `sni_inference.py:144` | delete unexpected-kwargs `TypeError` | `test_mut1a_sni_inference__reject_authority_1` |
| `sni_inference.py:159` | `n_i < 0 or k_i < 0` → `and` | `test_mut1a_sni_inference__require_n_k_1` |
| `sni_inference.py:177` | `not finite or not in [0,1]` → `and` | `test_mut1a_sni_inference__require_p0_1` |
| `sni_inference.py:206` | `alpha == 0.1` → `0.1001` | `test_mut1a_sni_inference__z_for_alpha_1` |
| `sni_inference.py:526` | `p0=0.5` default → `0.5005` | `test_mut1a_sni_inference_binom_p_two_sided_1` |
| `sni_inference.py:416` | `hi_q = 1.0 - lo_q` with `1.0` → `1.001` | `test_mut1a_sni_inference_cluster_mean_ci_1` |

### sni_seal.py

| file:line | original → mutated | killing test |
|---|---|---|
| `sni_seal.py:62` | `_HARD_FALSE_AUTHORITY` `False` → `True` | `test_mut1a_sni_seal_module_1` |
| `sni_seal.py:177` | `isinstance(key, str) and endswith("_id")` → `or` | `test_mut1a_sni_seal__check_identity_id_values_1` |
| `sni_seal.py:139` | non-str key `return False` → `True` | `test_mut1a_sni_seal__is_forbidden_authority_key_1` |
| `sni_seal.py:139` | non-str key `return False` → `None` | `test_mut1a_sni_seal__is_forbidden_authority_key_2` |
| `sni_seal.py:108` | `len==64 and all(hex)` → `or` | `test_mut1a_sni_seal__is_hex64_1` |
| `sni_seal.py:233` | protocol budget `n <= 0` → `n <= 1` | `test_mut1a_sni_seal__normalize_budgets_1` |
| `sni_seal.py:243` | delete exact `{path, sha256}` raise | `test_mut1a_sni_seal__normalize_manifest_1` |
| `sni_seal.py:190` | delete cell field str/int raise | `test_mut1a_sni_seal__parse_cell_1` |
| `sni_seal.py:128` | `_validate_sealed_at_utc` `return value` → `None` | `test_mut1a_sni_seal__validate_sealed_at_utc_1` |
| `sni_seal.py:292` | delete empty-lane raise | `test_mut1a_sni_seal_build_seal_1` |
| `sni_seal.py:488` | delete `render_seal_md` non-dict raise | `test_mut1a_sni_seal_render_seal_md_1` |
| `sni_seal.py:92` | delete `sha256_bytes` type guard | `test_mut1a_sni_seal_sha256_bytes_1` |
| `sni_seal.py:104` | `sha256_file` return digest → `None` | `test_mut1a_sni_seal_sha256_file_1` |
| `sni_seal.py:98` | delete `sha256_text` type guard | `test_mut1a_sni_seal_sha256_text_1` |
| `sni_seal.py:551` | delete `write_seal` non-dict raise | `test_mut1a_sni_seal_write_seal_1` |

## Equivalent arguments

None. Every selected mutant that the existing suite did not kill was
observable through a new test. `_HARD_FALSE_AUTHORITY` is unread by
production callers in this file; the new test pins its values anyway
because the table is the hard-false authority contract.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
censuses 19 fence points in `residual/s1_manifest.py`, `s1_prereg.py`,
`s1_report.py`, `run_s1.py`, `event_response/s2_seal.py`, `s2_splits.py`,
`run_s2.py`, and `protocols/S0_PROTOCOL_REGISTER.md`. **None of those
lines are in `sni_inference.py` or `sni_seal.py`.** No mutant sites were
excluded under the QF fence.

## What this does NOT prove

Mutation score is test strength against this operator set and this
30-per-module sample, not statistical validity of SNI estimators. A
killed mutant does not mean a CI is well-calibrated. No acceptance-matrix
row moves to DONE. The sweep does not claim completeness over unselected
sites (225+109 candidates, 60 applied). Equivalence tests that read
committed `runs/` JSON were not in the kill suite on this sparse
worktree. Nothing here feeds a ranker, gate, sizer, signal, escalation,
or trade path.
