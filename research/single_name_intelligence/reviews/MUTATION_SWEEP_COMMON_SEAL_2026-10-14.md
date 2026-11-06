# MUT6F mutation sweep — `common/sni_seal.py` (2026-10-14)

Lane M6F (build route), SNI commission 8659. Target module:
`research/single_name_intelligence/common/sni_seal.py` — owned site range is
ONLY `verify_seal` and the helpers it (transitively) calls:
`canonical_json`, `sha256_bytes`, `sha256_text`, `_is_hex64`, `_is_str_or_int`,
`_require_hex64`, `_validate_sealed_at_utc`, `authority_key_path`,
`_is_forbidden_authority_key`, `_collect_nested_authority`,
`_record_validator_violation`, `_parse_cell`, `_normalize_string_list`.
No production code was changed; the committed diff is tests + this review only.

## Summary

| generated | killed-before | survived-before | killed-after | equivalent | timeout | timeout-unsafe |
|---|---|---|---|---|---|---|
| 40 | 36 | 4 | 3 (39 total killed) | 1 | 0 | 0 |

- Mutation score before: **36/40 = 0.900**
- Mutation score after: **39/40 = 0.975** (39/39 = 1.000 over non-equivalent mutants)
- Killing tests added: **3** (fewer than 5 because only 3 non-equivalent
  survivors existed within the 40-mutant budget).
- Baseline importer suite (unmutated): 1199 passed, 1 skipped, ~14 s (< 20 s
  cap, so the full 40-mutant budget applied). After the new tests: 1202
  passed, 1 skipped, 0 failures.
- Target-module baseline sha256 (restored and verified after every mutant):
  `c93a445af2ad373b8468c4c7395612a9c207832875492fc51cb21e66fb493584`

Importer test set (tests that import the module; the only tests run per mutant):
`tests/test_sni_common_equivalence.py`, `tests/test_sni_common_seal.py`,
`tests/test_sni_injection_safety_ext.py`, `tests/test_sni_mutation_common.py`,
`tests/test_sni_run_seal_repro.py` — run as
`python3 -m pytest <set> -x -q -p no:cacheprovider` under `timeout 60`.

## Operator set and seed

Operators (frozen method): comparison flip (`< ⇄ >=`, `<= ⇄ >`, `== ⇄ !=`);
arithmetic swap (`+ ⇄ -`, `* ⇄ /`); constant perturbation (int n → n+1,
float x → x·1.001, `True ⇄ False`); `return x → return None` (one return per
function, the last valued one); `and ⇄ or`; deletion of one `if …: raise`
guard (body exactly one Raise, no else). 58 candidate sites within the owned
function ranges; 40 selected deterministically with `random.Random(20261014)`
stratified by function (round-robin over functions, shuffled within each).
Each mutant was applied by a single byte-span edit, tested, restored, and the
restore verified against the baseline sha256; `git status --porcelain --
research/` was checked after every mutant run (no mutant wrote anything).

## Per-module table

| module | site range | candidates | mutants run | killed | survived | equivalent | timeout | score before → after |
|---|---|---|---|---|---|---|---|---|
| `common/sni_seal.py` | `verify_seal` + helpers | 58 | 40 | 36 → 39 | 4 → 1 | 1 | 0 | 0.900 → 0.975 |

## Per-mutant results

| id | function | line | operator | original → mutated | status |
|---|---|---|---|---|---|
| M01 | `_authority_key_path` | 133 | ret-none | `return f"{path}.{key}"` → `return None` | KILLED |
| M02 | `_is_forbidden_authority_key` | 139 | const-bool | `False` → `True` | KILLED |
| M03 | `_is_hex64` | 108 | const-int | `64` → `65` | KILLED |
| M04 | `_is_str_or_int` | 112 | ret-none | full return → `None` | KILLED |
| M05 | `_normalize_string_list` | 259 | del-guard | non-str item guard deleted | KILLED |
| M06 | `_parse_cell` | 187 | cmp | `!=` → `==` | KILLED |
| M07 | `_require_hex64` | 118 | ret-none | `return value` → `return None` | SURVIVED → EQUIVALENT |
| M08 | `_validate_sealed_at_utc` | 128 | ret-none | `return value` → `return None` | KILLED |
| M09 | `canonical_json` | 80 | ret-none | full return → `None` | KILLED |
| M10 | `sha256_bytes` | 94 | ret-none | full return → `None` | KILLED |
| M11 | `sha256_text` | 98 | del-guard | non-str guard deleted | KILLED |
| M12 | `verify_seal` | 432 | cmp | `<=` → `>` | KILLED |
| M13 | `_is_forbidden_authority_key` | 139 | ret-none | `return False` → `return None` | KILLED |
| M14 | `_is_hex64` | 108 | boolop | first `and` → `or` | KILLED |
| M15 | `_is_str_or_int` | 112 | boolop | `or` → `and` | KILLED |
| M16 | `_normalize_string_list` | 255 | del-guard | non-list guard deleted | KILLED |
| M17 | `_parse_cell` | 190 | del-guard | field-type guard deleted | KILLED |
| M18 | `_require_hex64` | 116 | del-guard | hex64 guard deleted | KILLED |
| M19 | `_validate_sealed_at_utc` | 122 | del-guard | Z-string guard deleted | KILLED |
| M20 | `canonical_json` | 82 | const-bool | `True` → `False` | KILLED |
| M21 | `sha256_bytes` | 92 | del-guard | bytes-type guard deleted | KILLED |
| M22 | `sha256_text` | 100 | ret-none | full return → `None` | KILLED |
| M23 | `verify_seal` | 416 | cmp | `!=` → `==` | KILLED |
| M24 | `_is_hex64` | 108 | ret-none | full return → `None` | KILLED |
| M25 | `_normalize_string_list` | 262 | ret-none | `return sorted(out)` → `None` | KILLED |
| M26 | `_parse_cell` | 192 | ret-none | full return → `None` | KILLED |
| M27 | `_validate_sealed_at_utc` | 122 | boolop | `or` → `and` | SURVIVED → killed-after |
| M28 | `canonical_json` | 84 | const-bool | `False` → `True` | KILLED |
| M29 | `verify_seal` | 413 | cmp | `!=` → `==` | KILLED |
| M30 | `_is_hex64` | 108 | cmp | `==` → `!=` | KILLED |
| M31 | `_parse_cell` | 187 | del-guard | cell-shape guard deleted | KILLED |
| M32 | `canonical_json` | 86 | arith | `+` → `-` | KILLED |
| M33 | `verify_seal` | 350 | boolop | `or` → `and` | KILLED |
| M34 | `_is_hex64` | 108 | boolop | second `and` → `or` | KILLED |
| M35 | `_parse_cell` | 187 | boolop | `or` → `and` | SURVIVED → killed-after |
| M36 | `canonical_json` | 85 | const-bool | `False` → `True` | KILLED |
| M37 | `verify_seal` | 439 | cmp | `==` → `!=` | KILLED |
| M38 | `verify_seal` | 426 | boolop | `or` → `and` | SURVIVED → killed-after |
| M39 | `verify_seal` | 452 | cmp | `!=` → `==` | KILLED |
| M40 | `verify_seal` | 390 | const-bool | `is not True` → `is not False` | KILLED |

## Surviving-mutant list with killing test name

| mutant | site | mutation | killing test (all re-verified by re-running the mutant) |
|---|---|---|---|
| M27 | `common/sni_seal.py:122` `_validate_sealed_at_utc` | `or` → `and` in the non-Z guard | `test_m6f_sni_seal__validate_sealed_at_utc_1` |
| M35 | `common/sni_seal.py:187` `_parse_cell` | `or` → `and` in the shape guard | `test_m6f_sni_seal__parse_cell_1` |
| M38 | `common/sni_seal.py:426` `verify_seal` | `or` → `and` in the per-family budget check | `test_m6f_sni_seal_verify_seal_1` |

Re-verification evidence (mutant applied → new-test run): M27 →
`FAILED tests/test_sni_mut6_common_seal.py::test_m6f_sni_seal__validate_sealed_at_utc_1`;
M35 → `FAILED ...::test_m6f_sni_seal__parse_cell_1`;
M38 → `FAILED ...::test_m6f_sni_seal_verify_seal_1`. All three tests pass on
unmutated code.

## Equivalent arguments

- **M07** (`_require_hex64` L118 `return value` → `return None`): the return
  value of `_require_hex64` is discarded at every call site —
  `verify_seal` calls it only through `_record_validator_violation` (which
  ignores the return and records only the raise), `build_seal` L307 calls it
  as a statement, and `_normalize_manifest` L249 calls it as a statement.
  No caller consumes the return, so `return None` is behaviorally
  indistinguishable inside this module. (The guard itself is separately
  mutation-tested and killed as M18.)

## Excluded QF lines

`reviews/QF_QUARANTINE_FENCE_2026-10-13.md` covers fence lines, but a grep
for `sni_seal`/`verify_seal` in that review returns no hits — no line of
`common/sni_seal.py` is a QF fence line, so no mutant was excluded on QF
grounds. (QF review inspected read-only; not modified.)

## What this does NOT prove

- A mutation score measures test strength against this operator set, seed,
  and 40-of-58 site sample — it is not statistical validity of any estimate,
  residual, or stress statistic produced under the seal.
- No acceptance row moves to DONE; this sweep adds evidence only.
- 18 of 58 candidate sites were not sampled (budget cap) and other operator
  families (e.g. off-by-one slices, statement deletion beyond guard removal)
  were not tried.
- `verify_seal`'s `file_bytes` manifest cross-check lines drew no selected
  mutant this run; they remain covered by line coverage but were not
  mutation-proven here.
- The sweep ran in a sparse worktree; collection initially required
  sparse-adding `research/single_name_intelligence/{common,residual,
  us_transfer,event_response,evaluation,acceptance,us_stress,runs}`,
  `contracts/single_name_intelligence/sni_seal.v1.schema.json`, and `tests`.
  These paths were read to run the importer suite; none were modified.
