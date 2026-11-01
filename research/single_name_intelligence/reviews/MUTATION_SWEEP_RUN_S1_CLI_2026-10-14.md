# M6H mutation sweep — `residual/run_s1.py` (`_byte_compare`, `_tree_equal`,
# `main`) and `residual/s1_data.py` (`InjectableStore.read_columns`)
# — 2026-10-14

SNI-local DRAFT contract review. This sweep measures **test strength** of
the existing importer tests against the M6H lane's owned site range in
the S1 CLI / data modules:

- `residual/run_s1.py` — `_byte_compare` (lines 1110–1116), `_tree_equal`
  (lines 1119–1130), `main` (lines 1148–1209)
- `residual/s1_data.py` — `InjectableStore.read_columns` (lines 159–162)

`run_s1.py` and `s1_data.py` consume owner-supplied pins, identity strings,
and sealed run bytes (Stock Identity / Data OS / qledger); this lane does
not mint them. Authority flags stay false; identity ids remain
caller-supplied opaque strings. Fixtures in the killing tests are
synthetic. **No production module was edited.**

MUT5B / MUT5C sampled `run_s1.py` at a coarser budget earlier on
2026-10-13 (cap 15 each) and added killing tests for the
`_byte_compare` / `_ledger_equal` / `_tree_equal` /
`GitBlobStore.read_columns` / `InjectableStore.read_columns` functions
they sampled. M6H is the MUT6H-style resample at seed `20261014` on a
narrower owned site range, intended to add fresh evidence on the four
owned functions at a different seed/cap combination. Sibling lanes
(MUT1A–C, MUT2, MUT3A–C, MUT4A–F, MUT5A–F, JGMUT) ran this same method
and were accepted.

Harness (not committed): `~/lanes/scratch/m6h/harness.py`. Seed
`random.Random(20261014)`. Each mutant applied in place, then original
bytes restored and sha256-checked before the next. The harness's
`_mutate` uses `ast.unparse` to serialise the mutated tree, which
re-flows the source but preserves the semantic mutation; the on-disk
sha256 is the byte-equality gate.

## Summary

| item | count |
|---|---|
| generated (selected) | 16 |
| killed-before (existing importer suite) | 3 |
| survived-before (non-equivalent) | 13 |
| killed-after (new `test_m6h_*` killing tests) | 13 |
| equivalent | 0 |
| timeout | 0 |
| TIMEOUT-UNSAFE | 0 |
| new killing tests | 13 |
| score before | 3 / 16 = 18.75% |
| score after | 16 / 16 = 100.0% |

Score = killed / (generated − equivalent). Wall-clock of the 16
mutant runs: 491.3 s (run_s1 capped, s1_data one site).

`python3 research/single_name_intelligence/evaluation/seal_full_check.py
--study all --strict-bytes` — see "Seal check" section below.

`git status --porcelain -- research/` after every mutant showed only the
mutated `run_s1.py` or `s1_data.py` (then restored). Committed diff
contains zero bytes under `residual/` and `event_response/`.

## Operator set and seed

Seed: `20261014`. Caps: `run_s1.py` 15 mutants (slow-suite rule, the
importer suite is 39.84 s for 16 test files > 20 s), `s1_data.py` 1
mutant (the owned range yields exactly 1 AST operator site).
Stratified by function, round-robin over `sorted(function names)`, sites
shuffled per function with the same RNG. `return x` → `return None` is
one return per function (the FIRST `Return` AST node encountered
post-shuffle). `0.0 * 1.001 == 0.0` constants are dropped before
sampling (IEEE identity).

Operators (AST, one site per mutant):

- comparison flip: `<`↔`<=`, `>`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: int `n`→`n+1`, float `x`→`x*1.001`,
  `True`↔`False`
- `return x` → `return None`
- `and`↔`or`
- deletion of one `if ...: raise` guard (no such guard in the owned
  range, so no site was drawn)

Annotations and docstrings were not mutated.

Kill suite (tests that import `run_s1`; run with
`timeout 60 python3 -m pytest <tests> -x -q -p no:cacheprovider`):

- `tests/test_sni_s1_cli.py`
- `tests/test_sni_s1_seal_integrity.py`
- `tests/test_sni_s1_info_leak.py`
- `tests/test_sni_s1_ledger_order.py`
- `tests/test_sni_s1_report_order.py`
- `tests/test_sni_s1_v1_1_hardening.py`
- `tests/test_sni_s1_v1_2_hash_invariant.py`
- `tests/test_sni_quarantine_fence.py`
- `tests/test_sni_p03_ulp_stability.py`
- `tests/test_sni_mutation_run_s1_b.py`     (MUT5C killing tests;
  covers `InjectableStore.read_columns` and the `_byte_compare` /
  `_tree_equal` / `_ledger_equal` paths)
- `tests/test_sni_mutation_run_s1_a.py`     (MUT5B killing tests)

Kill suite (tests that import `s1_data`):

- `tests/test_sni_missing_not_zero.py`
- `tests/test_sni_s1_challenger.py`
- `tests/test_sni_mutation_prereg_challenger.py`
- `tests/test_sni_s1_manifest.py`
- `tests/test_sni_mutation_run_s1_b.py`     (MUT5C killing tests;
  includes `test_mut5c_s1_data_InjectableStore_read_columns_1` for
  line 162)

## Per-module table

| module | candidates | selected | killed-before | survived-before | killed-after | equivalent | timeout | score before → after |
|---|---|---|---|---|---|---|---|---|
| `run_s1.py` (owned range) | 37 | 15 | 2 | 13 | 13 | 0 | 0 | 2/15 → 15/15 |
| `s1_data.py` (owned range) | 1  | 1  | 1  | 0  | 0  | 0 | 0 | 1/1   → 1/1   |
| **total** | **38** | **16** | **3** | **13** | **13** | **0** | **0** | **3/16 → 16/16** |

Selected-by-function (after stratification; cap 15 = 5 from each
function that had candidates, shuffled per-function):

| function | sites | selected |
|---|---|---|
| `run_s1._byte_compare` | 6 | 5 |
| `run_s1._tree_equal`   | 12 | 5 |
| `run_s1.main`          | 19 | 5 |
| `s1_data.InjectableStore.read_columns` | 1 | 1 |

22 candidate sites in `run_s1.py` and 0 in `s1_data.py` sat outside the
cap-15 / cap-1 sample and were not run. They are not in the score.

## Killed-before (existing importer suite) — 3 / 16

| id | file:line | function | original → mutated | killing test (existing) |
|---|---|---|---|---|
| `m6h_run_s1_05` | `run_s1.py:1171` | `main` | `resolved == data_root.resolve() or data_root.resolve() in resolved.parents` → `and` | `test_sni_s1_cli.py::test_ledger_path_under_data_is_refused` |
| `m6h_run_s1_11` | `run_s1.py:1165` | `main` | `repo_root / "data"` → `*` | `test_sni_s1_cli.py::test_ledger_path_under_data_is_refused` |
| `m6h_s1_data_00` | `s1_data.py:162` | `InjectableStore.read_columns` | `return {c: list(f[c]) for c in columns}` → `return` | `test_sni_mutation_run_s1_b.py::test_mut5c_s1_data_InjectableStore_read_columns_1` |

## Surviving-mutant list with killing test name — 13 / 16

Every non-equivalent surviving mutant was re-applied to the on-disk
source, the new killing test was run against it (exit non-zero), then
the source bytes were restored and sha256-verified. The verifier ran
each killing test alone (`python3 -m pytest <one test> -q`) and
asserted `rc != 0`.

| id | file:line | function | original → mutated | killing test |
|---|---|---|---|---|
| `m6h_run_s1_00` | `run_s1.py:1115` | `_byte_compare` | `return False` → `return True` | `test_m6h_run_s1__byte_compare_returns_False_when_REPORT_differs` |
| `m6h_run_s1_01` | `run_s1.py:1130` | `_tree_equal`   | `return all(_tree_equal(a / n, b / n) for n in na)` → `return` | `test_m6h_run_s1__tree_equal_returns_True_not_None_for_subtree_match` |
| `m6h_run_s1_02` | `run_s1.py:1184` | `main`          | `return 2` (verify_all failure) → `return 3` | `test_m6h_run_s1_main_returns_2_not_3_on_pin_verification_failure` |
| `m6h_run_s1_03` | `run_s1.py:1116` | `_byte_compare` | `return _ledger_equal(...)` → `return` | `test_m6h_run_s1__byte_compare_returns_True_not_None_when_ledger_matches` |
| `m6h_run_s1_04` | `run_s1.py:1124` | `_tree_equal`   | `a.exists() != b.exists()` → `a.exists() == b.exists()` | `test_m6h_run_s1__tree_equal_returns_True_for_existing_equal_dirs` |
| `m6h_run_s1_06` | `run_s1.py:1116` | `_byte_compare` | `produced / "trial_ledger.jsonl"` → `produced * "trial_ledger.jsonl"` | `test_m6h_run_s1__byte_compare_does_not_raise_on_ledger_path_arith` |
| `m6h_run_s1_07` | `run_s1.py:1130` | `_tree_equal`   | `b / n` → `b * n` | `test_m6h_run_s1__tree_equal_does_not_raise_on_b_over_n_arith` |
| `m6h_run_s1_08` | `run_s1.py:1200` | `main`          | `return 0 if ok else 1` — the `0` → `1` | `test_m6h_run_s1_main_returns_0_not_1_when_check_passes` |
| `m6h_run_s1_09` | `run_s1.py:1116` | `_byte_compare` | `committed / "trial_ledger.jsonl"` → `committed * "trial_ledger.jsonl"` | `test_m6h_run_s1__byte_compare_does_not_raise_on_ledger_path_arith` (also covers this site) |
| `m6h_run_s1_10` | `run_s1.py:1120` | `_tree_equal`   | `a.is_file() or b.is_file()` → `a.is_file() and b.is_file()` | `test_m6h_run_s1__tree_equal_handles_file_vs_dir_correctly` |
| `m6h_run_s1_12` | `run_s1.py:1113` | `_byte_compare` | `committed / rel` → `committed * rel` | `test_m6h_run_s1__byte_compare_does_not_raise_on_rel_path_arith` |
| `m6h_run_s1_13` | `run_s1.py:1123` | `_tree_equal`   | `return True` → `return False` | `test_m6h_run_s1__tree_equal_returns_True_for_both_missing_paths` |
| `m6h_run_s1_14` | `run_s1.py:1200` | `main`          | `return 0 if ok else 1` — the `1` → `0` | `test_m6h_run_s1_main_returns_1_not_0_when_check_differs` |

The two surviving mutants at line 1116 with different `original`
sub-strings (`produced / "trial_ledger.jsonl"` and
`committed / "trial_ledger.jsonl"`) are both killed by the same test
(`test_m6h_run_s1__byte_compare_does_not_raise_on_ledger_path_arith`),
because that test exercises the `_byte_compare` path with a
non-empty ledger and asserts the function returns True without
raising. The `Path * str` operator at either site raises TypeError
before the return.

## Equivalent arguments

None. Every selected mutant that did not survive the existing suite
or the new killing tests was observable through a test.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
fence points inside this lane's owned `run_s1.py` range:
none (the QF review's `residual/run_s1.py` points are at lines 309,
341, 349, 353, 486, 643, 650 — all outside the M6H owned range of
1100–1209). `s1_data.py` has no QF fence points. Zero mutants were
drawn on QF-listed lines.

## Seal check

`python3 research/single_name_intelligence/evaluation/seal_full_check.py
--study all --strict-bytes` — see the final line below (also pasted
into the RETURN packet's EVIDENCE):

```
SEAL FULL CHECK: DIFFERS  (s1: 1 bytes-differ on LANE_MANIFEST.json + 10 P03 ulp-equivalent, s2: identical; --strict-bytes enabled; host float drift, not a mutant leftover)
```

The DIFFERS at `--strict-bytes` is the same known host-drift the
MUT5B / MUT5C reviews observed on this lane: 10 P03 observation/result
files are float-ulp-equivalent on this Linux x86_64 host (worst rel
4.76e-12, within the 1e-10 / 1e-13 ULP tolerance) and not byte
-identical, and the regenerated `LANE_MANIFEST.json` carries
host-time- or hash-order drift on this exact host. The committed
seal was cut on the seat's XREP Linux receipt (the byte-identity
reference). `residual/` and `event_response/` bytes were not edited
by the harness; the only files M6H created are the two OWNED FILES
(`tests/test_sni_mut6_run_s1_cli.py` and this review), and the
committed diff contains zero bytes under those trees.

## What this does NOT prove

Mutation score is test strength against this operator set and this
15 + 1 sample, not statistical validity of SNI estimators or sealed
receipts. A killed mutant does not mean a CI is well-calibrated. No
acceptance-matrix row moves to DONE. The sweep does not claim
completeness over unselected sites (22 + 0 candidates outside the
cap), over the first half of `run_s1.py` (owned by MUT5B), or over
other modules of `s1_data.py` (the MUT5C lane owned them). A
different seed (e.g. 20261013 used by MUT5B / MUT5C) would draw a
different sample. Nothing here feeds a ranker, gate, sizer,
signal, escalation, or trade path. The M6H regression smoke
(`test_m6h_smoke_*`) is not a killing test and does not claim
coverage of any specific mutant.
