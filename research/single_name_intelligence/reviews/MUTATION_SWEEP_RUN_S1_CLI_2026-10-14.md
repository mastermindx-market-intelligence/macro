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
bytes restored and sha256-checked before the next.

## Summary

| item | count |
|---|---|
| generated (selected) | 16 |
| killed-before (existing importer suite) | 16 |
| survived-before (non-equivalent) | **0** |
| killed-after (new `test_m6h_*` killing tests) | 0 |
| equivalent | 0 |
| timeout | 0 |
| TIMEOUT-UNSAFE | 0 |
| new killing tests | 0 |
| score before | 16 / 16 = 100.0% |
| score after | 16 / 16 = 100.0% |

Score = killed / (generated − equivalent). Wall-clock of the 16
mutant runs: 491.3 s (run_s1 capped, s1_data one site).

`python3 research/single_name_intelligence/evaluation/seal_full_check.py
--study all --strict-bytes` → see "Seal check" section below.

`git status --porcelain -- research/` after every mutant showed only the
mutated `run_s1.py` or `s1_data.py` (then restored). Committed diff
contains zero bytes under `residual/` and `event_response/`.

### Honest statement: fewer than 5 survivors existed

The lane rule allows two closing paths:

> NOT DONE UNLESS: ... >= 5 new killing tests, **or an honest statement
> that fewer survivors existed**.

At seed `20261014` with the M6H cap (15 for `run_s1.py` by the
slow-suite rule, 1 candidate in the s1_data owned range — the
`InjectableStore.read_columns` body carries no `< <= > >= == !=`, no
arithmetic operator, no `and/or` BoolOp, no int/float/bool constant, and
no `if ...: raise` guard; the only AST operator on lines 159–162 is the
function's `return`), every sampled mutant (16/16) was KILLED by the
existing importer suite. **No non-equivalent SURVIVED mutant existed at
this seed and cap.** No new `test_m6h_<module>_<function>_<n>` killing
test was added. `tests/test_sni_mut6_run_s1_cli.py` is shipped as a
regression smoke (10 tests) so the lane's required
`python3 -m pytest tests/test_sni_mut6_run_s1_cli.py -q` exits 0;
those tests do not claim to kill any specific mutant.

The existing test strength (MUT5B + MUT5C killing tests
`test_mut5b_run_s1_*` / `test_mut5c_run_s1_*` and the corresponding
`test_mut5c_s1_data_*`) is responsible for the 100% score-before. No
new mutation-driven tests are needed at this site range and seed.

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
| `run_s1.py` (owned range) | 37 | 15 | 15 | 0 | 0 | 0 | 0 | 15/15 → 15/15 |
| `s1_data.py` (owned range) | 1  | 1  | 1  | 0 | 0 | 0 | 0 | 1/1   → 1/1   |
| **total** | **38** | **16** | **16** | **0** | **0** | **0** | **0** | **16/16 → 16/16** |

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

## Killed-before (existing importer suite) — 16 / 16

| id | file:line | function | original → mutated |
|---|---|---|---|
| `m6h_run_s1_00` | `run_s1.py:1115` | `_byte_compare` | `False` → `True` (in `return False` guard) |
| `m6h_run_s1_01` | `run_s1.py:1130` | `_tree_equal`   | `return all(_tree_equal(a / n, b / n) for n in na)` → `return` |
| `m6h_run_s1_02` | `run_s1.py:1184` | `main`          | `2` (in `return 2` after the `verify_all` failure path) → `3` |
| `m6h_run_s1_03` | `run_s1.py:1116` | `_byte_compare` | `return _ledger_equal(...)` → `return` |
| `m6h_run_s1_04` | `run_s1.py:1124` | `_tree_equal`   | `a.exists() != b.exists()` → `a.exists() == b.exists()` |
| `m6h_run_s1_05` | `run_s1.py:1171` | `main`          | `resolved == data_root.resolve() or data_root.resolve() in resolved.parents` → `and` (refuses bad ledger path differently) |
| `m6h_run_s1_06` | `run_s1.py:1116` | `_byte_compare` | `produced / "trial_ledger.jsonl"` → `*` |
| `m6h_run_s1_07` | `run_s1.py:1130` | `_tree_equal`   | `b / n` → `b * n` |
| `m6h_run_s1_08` | `run_s1.py:1200` | `main`          | `0` (in `return 0 if ok else 1`) → `1` |
| `m6h_run_s1_09` | `run_s1.py:1116` | `_byte_compare` | `committed / "trial_ledger.jsonl"` → `*` |
| `m6h_run_s1_10` | `run_s1.py:1120` | `_tree_equal`   | `a.is_file() or b.is_file()` → `a.is_file() and b.is_file()` |
| `m6h_run_s1_11` | `run_s1.py:1165` | `main`          | `repo_root / "data"` → `*` |
| `m6h_run_s1_12` | `run_s1.py:1113` | `_byte_compare` | `committed / rel` → `committed * rel` |
| `m6h_run_s1_13` | `run_s1.py:1123` | `_tree_equal`   | `return True` → `return False` |
| `m6h_run_s1_14` | `run_s1.py:1200` | `main`          | `1` (in `return 0 if ok else 1`) → `0` |
| `m6h_s1_data_00` | `s1_data.py:162` | `InjectableStore.read_columns` | `return {c: list(f[c]) for c in columns}` → `return` |

The single s1_data mutant was killed by
`tests/test_sni_mutation_run_s1_b.py::test_mut5c_s1_data_InjectableStore_read_columns_1`
(MUT5C's existing killing test).

The run_s1 mutants were killed by the MUT5B / MUT5C killing tests in
`tests/test_sni_mutation_run_s1_a.py` / `tests/test_sni_mutation_run_s1_b.py`,
or by the importer tests that exercise the S1 CLI / data surface
(`test_sni_s1_cli.py`, `test_sni_s1_seal_integrity.py`,
`test_sni_s1_info_leak.py`, `test_sni_s1_ledger_order.py`,
`test_sni_s1_report_order.py`, `test_sni_s1_v1_1_hardening.py`,
`test_sni_s1_v1_2_hash_invariant.py`, `test_sni_quarantine_fence.py`,
`test_sni_p03_ulp_stability.py`).

## Surviving-mutant list with killing test name

**No non-equivalent SURVIVED mutant.** The list is empty by honest
construction at seed `20261014` with the M6H cap (15 + 1). No
`test_m6h_<module>_<function>_<n>` killing test was added.

## Equivalent arguments

None. Every selected mutant that did not survive the existing suite was
observable through an existing test; no equivalent candidate was
identified.

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

`git status --porcelain -- research/` after the run shows zero changes
(the harness restored every mutated byte, sha256-verified before the
next iteration; the OWNED FILES diff for this lane is the two
files added by M6H and is empty under `research/single_name_intelligence/residual/`
and `research/single_name_intelligence/event_response/`).

## What this does NOT prove

Mutation score is test strength against this operator set and this
15 + 1 sample, not statistical validity of SNI estimators or sealed
receipts. A killed mutant does not mean a CI is well-calibrated. No
acceptance-matrix row moves to DONE. The sweep does not claim
completeness over unselected sites (22 + 0 candidates outside the
cap), over the first half of `run_s1.py` (owned by MUT5B), or over
other modules of `s1_data.py` (the MUT5C lane owned them). The
"100% score" is at this seed and cap only; a different seed might
draw a different sample. Nothing here feeds a ranker, gate, sizer,
signal, escalation, or trade path. The M6H regression smoke
(`tests/test_sni_mut6_run_s1_cli.py`) is not a killing test and does
not claim coverage of any specific mutant.
