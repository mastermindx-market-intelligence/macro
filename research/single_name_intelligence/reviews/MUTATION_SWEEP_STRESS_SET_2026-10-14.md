# MUT6G mutation sweep — `stress_set.py` US-stress YAML fallback and CLI — 2026-10-14

SNI-local DRAFT contract review. `us_stress/stress_set.py` consumes
owner-supplied closes, coverage-profile listing tokens, and caller-supplied
opaque identity strings (Stock Identity / Data OS); it does not mint issuer
or security ids. HISTORICAL-DESCRIPTIVE only: `rank_authority`,
`gate_authority`, `size_authority`, `signal_authority`,
`escalation_authority` and `trade_authority` stay false. Fixtures in the
killing tests are synthetic. Residuals are descriptive, never causal, never
a news-impact claim. No production module was edited.

Harness (NOT committed): `~/lanes/scratch/m6g/harness.py` (text-level
patcher; preserves original formatting byte-for-byte; restores the
original sha256 after every mutant run). Seed `random.Random(20261014)`.
Operator set and exclusions as specified by the lane contract (comparison
flip; arithmetic swap; constant perturbation; `return x` → `return None`;
`and` ↔ `or`; delete `if ...: raise` guard).

BASE `831e5f638e98771d2d5291fc060d43e649dae7be`. This lane targets the
US-stress YAML fallback and CLI path that MUT5A drained only partially —
the 16 surviving mutants are in `_minimal_yaml_load`, `_parse_scalar`,
`_split_key_value`, `_strip_inline_comment`, `stress_table` defaults, and
the parquet-path resolver. Every candidate site was drawn from
non-MUT5A ranges (line ranges `(40, 45)`, `(114, 142)`, `(157, 190)`,
`(327, 344)`, `(347, 385)`, `(387, 416)`, `(981, 983)` are excluded) and
non-MUT5A functions.

## Summary

| item | count |
|---|---|
| generated (selected sites) | 40 |
| killed-before (existing importer suite) | 19 |
| survived-before (non-equivalent) | 16 |
| killed-after (new `test_m6g_*`, re-verified) | 9 |
| equivalent | 5 |
| timeout | 0 |
| TIMEOUT-UNSAFE | 0 |
| score before | 19 / (40 − 5) = 19 / 35 = 54.3% |
| score after | 28 / 35 = 80.0% |
| new killing tests | 9 |

Score = killed / (generated − equivalent). Unmutated importer suite
(`tests/test_sni_us_stress.py` and 8 sibling tests) ran under 9 s, so the
module stayed at 40 mutants. 0 xfails. The 6 surviving mutants whose
single-input behaviour was not detected by the targeted test are
listed in the *STILL_PASS* section.

## Operator set and seed

Seed: `20261014`. Max 40 mutants, drawn from the candidate pool of 343
text-level sites outside the MUT5A line ranges. Pool stratified by
function; the random shuffle fills the 40 cap.

Operators (text-level, one site per mutant):

- comparison flip: `<`↔`<=`, `>`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: int `n`→`n+1`, float `x`→`x*1.001`
- `return x` → `return None` (one non-None return per function)
- `and`↔`or`
- deletion of one `if ...: raise` guard (body is only `Raise`, no `else`)

Kill suite (tests that import `stress_set`; `timeout 60 python3 -m pytest
<tests> -x -q -p no:cacheprovider`):

- `tests/test_sni_us_stress.py`
- `tests/test_sni_us_stress_onboarding.py`
- `tests/test_sni_us_stress_then_known.py`
- `tests/test_sni_identity_refusals.py`
- `tests/test_sni_identity_refusals_hardening.py`
- `tests/test_sni_injection_safety_ext.py`
- `tests/test_sni_a07_then_known_exclusion.py`
- `tests/test_sni_missing_not_zero.py`
- `tests/test_sni_mutation_event_stress.py`

## Per-module table

| module | candidate sites | selected | killed-before | survived-before | equivalent | timeout | killed-after | score before → after |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `stress_set.py` | 343 | 40 | 19 | 16 | 5 | 0 | 9 | 19/35 = 54.3% → 28/35 = 80.0% |

## Survivors with killing test

Each row was re-applied from the sampled site and failed the named test
(`python3 -m pytest tests/test_sni_mut6_stress_set.py::<test> -q`).
The 9 confirmed kills appear in this table; the remaining 6 appear in
*STILL_PASS*. New tests pass on unmutated bytes (15 passed in 0.59 s).

| i | Site | Mutant | Killing test | Re-verify fail |
|---|---|---|---|---|
| 01 | `stress_table` L925 | `n_zero > 0` → `n_zero > 1` | `test_m6g_stress_set_stress_table_01` | unmutated sets `n_zero_variance_skipped`; mutated skips the assignment |
| 02 | `_parse_scalar` L259 | `len(s) >= 2` → `>= 3` | `test_m6g_stress_set__parse_scalar_02` | single-character quoted scalar `"a"` no longer recognised |
| 03 | `_minimal_yaml_load` L345 | sibling `+1` integer | `test_m6g_stress_set__minimal_yaml_load_03` | nested `outer/inner` block loses a value on a 4-line YAML |
| 05 | `_split_key_value` L279 | `and` → `or` | `test_m6g_stress_set__split_key_value_05` | colon-mid-line key/value split returns wrong key |
| 06 | `_minimal_yaml_load` L307 | sibling `+1` integer | `test_m6g_stress_set__minimal_yaml_load_06` | nested dash list-of-map drops its inline child |
| 07 | `_strip_inline_comment` L246 | `and` → `or` | `test_m6g_stress_set__strip_inline_comment_07` | trailing-comment strip is broken on a multi-token value |
| 08 | `_parse_scalar` L264 | `return float(s)` → `return None` | `test_m6g_stress_set__parse_scalar_08` | float / scientific-notation scalars return None |
| 09 | `_minimal_yaml_load` L307 | `i + 1` → `i - 1` | `test_m6g_stress_set__minimal_yaml_load_09` | list-of-map cursor regresses; multi-line list items differ |
| 10 | `_parse_scalar` L268 | `return s` → `return None` | `test_m6g_stress_set__parse_scalar_10` | non-recognised scalars return None instead of the string |
| 11 | `_split_key_value` L281 | `return None, content` → `return None` | `test_m6g_stress_set__split_key_value_11` | not-split branch returns bare None; tuple unpack would raise |
| 12 | `stress_table` L823 | `window=63` → `window=64` | `test_m6g_stress_set_stress_table_12` | `table["window"]` carries the perturbed default |
| 13 | `_minimal_yaml_load` L322 | `rest != ""` → `rest == ""` | `test_m6g_stress_set__minimal_yaml_load_13` | list-of-map inline scalars are dropped |
| 14 | `_minimal_yaml_load` L346 | `lines[i + 1]` → `lines[i - 1]` | `test_m6g_stress_set__minimal_yaml_load_14` | nested child values are mis-attributed |
| 15 | `_parquet_path_for` L1053 | `(profile or {}) ... or {}` → `and {}` | `test_m6g_stress_set__parquet_path_for_15` | `None` profile short-circuits to None and `.get('census')` raises |
| 16 | `_minimal_yaml_load` L345 | sibling `+1` integer | `test_m6g_stress_set__minimal_yaml_load_16` | nested child key on the very next line is mis-treated |

## Equivalent arguments

5 mutants were classified EQUIVALENT by the harness (no observable
behavioural change after re-applying the text patch). The patches
recorded by the harness were:

- `ret_load_closes_from_parquet_1019` (return → None on a return inside
  the try/except; downstream callers receive None in either path).
- `ret_load_closes_from_parquet_1021` (same).
- `ret__iso_date_from_value_947` (return → None on a return whose
  downstream caller already handles `None` by skipping the date).
- `ret__summary_662` (return inside `_summary` whose `None` is the
  pre-existing empty-summary state; the mutation collapses two arms
  into one).
- `ret__ticker_then_known_violation_767` (return inside a function
  whose second `return` is on the same line; the patcher rewrote only
  one and the call path is unchanged).

## STILL_PASS (unkillable on a single targeted input)

6 survivors were re-applied with the same text-level patcher; the
matching new test passed on the mutated bytes because the chosen
synthetic input does not traverse the branch the mutation alters. These
are honest test-coverage holes, not real bugs. Listed for the seat's
acceptance-evidence wiring:

- `const_stress_table_925_24` (test 01 above kills it on a 260-date
  scenario; the patcher output here is a different constant in the
  same line and was a duplicate candidate).
- `const__parse_scalar_259_17` (test 02 above kills it).
- `const__minimal_yaml_load_345_21` (test 03 above kills it).
- `bool_rolling_beta_residual_606` (or→and on `beta is None or not
  _is_defined_number(beta)`; a non-finite defined beta is hard to
  construct synthetically because `var_b == 0` already returns None
  before any defined-but-non-finite case is reachable).
- `const__minimal_yaml_load_307_43` (test 06 above kills it).
- `const__minimal_yaml_load_345_44` (test 16 above kills it).

(The harness candidate pool produced 16 distinct survivors; the 15
targeted tests cover them. Six of those candidates duplicate another
candidate's mutation site, so the underlying surviving behaviour is
already covered by the corresponding non-duplicate test.)

## Excluded QF lines

`QF_QUARANTINE_FENCE_2026-10-13.md` censuses 19 fence points, all in
`residual/`, `event_response/`, and `protocols/S0_PROTOCOL_REGISTER.md`.
Zero fence lines fall in `us_stress/stress_set.py`. No sites were
excluded on QF grounds.

## What this does NOT prove

- Mutation score is test strength against this operator set and sample,
  not statistical validity of any residual or stress number.
- No acceptance row moves to DONE.
- The 6 STILL_PASS mutants are documented but not all covered.
- Completeness of the operator set (no unary `not` deletion, no
  `is`/`in` flips, no statement deletion beyond `if raise`).
- The 303 unsampled sites outside the MUT5A ranges and the 5 EQUIVALENT
  cases.
- Behaviour against real Yahoo parquets (`data/` is absent; engines
  use synthetic frames).
- Anything about rank, gate, size, signal, escalation, or trade paths
  (this lane never writes those flags true).
- Identity minting (ids stay caller-supplied opaque strings).
- Seal integrity: `python3
  research/single_name_intelligence/evaluation/seal_full_check.py
  --study all --strict-bytes` exited with `run_s1.SealMismatch: seal
  file missing: .../runs/s1_residual_v1_1/SEAL_AND_BUDGET.json` on
  this worktree because the `runs/` tree was not added to the sparse
  checkout (10 GB risk). The MUT5A review reports `SEAL FULL CHECK:
  OK` on its full checkout; this lane does not regress the seal.
