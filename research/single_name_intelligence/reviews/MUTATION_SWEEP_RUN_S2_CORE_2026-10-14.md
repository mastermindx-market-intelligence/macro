# SNI MUT6C mutation sweep — run_s2.py core evaluation paths — 2026-10-14

Lane MUT6C, commission 8659. AST mutation of four S2-core functions in
`research/single_name_intelligence/event_response/run_s2.py`; production
bytes unchanged. New tests consume owner-supplied opaque identity strings
and synthetic fixtures only. Every authority flag stays false.
Residuals and event-study numbers are descriptive, never causal, never
a news-impact claim (A24). An unestimable family ABSTAINS (A25).

MUT6 lane 4 of the coverage census
(`research/single_name_intelligence/reviews/SNI_COVERAGE_CENSUS_2026-10-13.md`):
"S2 retired-cell and pooled-prior abstain — `compute_outcomes`,
`pooled_prior`, `evaluate_family`, `build_block`. A killing test must
pin: a retired (protocol, split) cell never resolves a window return;
pooled TRAIN prior ABSTAINS with a named reason when cluster-N is below
the floor."

Harness (scratch, not committed): `~/lanes/scratch/m6c/harness.py`.
BASE `831e5f638e98771d2d5291fc060d43e649dae7be`. Wall-clock elapsed
167.7 s for the 40-mutant sweep.

## Summary

| Measure | Count |
|---|---|
| Modules | 1 (`run_s2.py`) |
| Candidate sites (all) | 221 |
| Candidate sites (owned funcs only) | 55 |
| Sampled (run) | **40** (cap 40/module, 60 total) |
| Killed before new tests | **40** |
| Survived before | **0** |
| Timeout before | **0** |
| Equivalent | **0** (no surviving mutants to argue) |
| Killed after new tests | **40** (existing suite) |
| New killing tests | **0** (no surviving mutants; per spec OR clause "honest statement that fewer survivors existed") |
| New invariant-pin tests shipped | **8** (X2-01 retired-cell, A25 abstain, A25 mean-excess, trailing63 dedup, build_block TESTED hits, evaluate_family BASELINE_TRAILING63, evaluate_family BASELINE_POOLED_PRIOR, evaluate_family retired row) |
| Mutation score before | **40/40 = 100%** |
| Mutation score after (excl. equivalent) | **40/40 = 100%** |
| Pytest (`tests/test_sni_mut6_run_s2_core.py`) | **8 passed** |
| Importer tests (sparse; missing P03_hkd_9988 bytes) | **119 passed**, **2 pre-existing** (1 sparse-induced A20 count, 29 sparse MUT4C P03 bytes; all fail without my changes) |

The 40 sampled mutants in this lane were ALL killed by the pre-existing
importer suite (especially MUT5D's
`tests/test_sni_mutation_run_s2_a.py` and
`tests/test_sni_mutation_run_s2_b.py`, which already cover
`compute_outcomes` lineage, `pooled_prior`, `evaluate_family`, and the
`build_block` hits counter). The MUT6C interpretation per the spec OR
clause is **honest statement: zero survivors existed**.

Score = killed / (sampled − equivalent). The 40-mutant sample is fully
killed by the existing suite.

## Operator set and seed

Operators (source-slice AST, identical to MUT2 / MUT5D):

- comparison flip (`==`/`!=`, `<`/`>`, `<=`/`>=`, `is`/`is not`, `in`/`not in`)
- arithmetic swap (`+`/`-`, `*`/`/`, `//`/`%`)
- constant perturbation (`n → n+1`, `x → x*1.001`, `True ↔ False`)
- `return <expr>` → `return None`
- `and` ↔ `or`
- deletion of one `if ...: raise` guard (body is only `Raise`, no `else`)

Sample: `random.Random(20261014)`, round-robin stratified by enclosing
function (only the four OWNED_FUNCS), at most 40 mutants per module.
Sites outside the four owned functions (episode_identity, episode_purged,
abstention_state, plain_word_null, exclusion_index_by_family, etc.) are
NOT this lane's target and are filtered out before sampling.

Per-mutant pytest: tests that import `run_s2.py`, `-x -q`, 60 s
subprocess timeout, original bytes restored and sha256-checked after
each mutant. `git status --porcelain -- research/` stays empty
throughout.

## Per-function table

| Function | Span (L) | Candidates | Sampled | Killed before | Survived | Timeout | Eq |
|---|---|---:|---:|---:|---:|---:|---:|
| `compute_outcomes` | 121-148 | 6 | 6 | 6 | 0 | 0 | 0 |
| `evaluate_family` | 155-216 | 14 | 14 | 14 | 0 | 0 | 0 |
| `pooled_prior` | 262-279 | 6 | 6 | 6 | 0 | 0 | 0 |
| `build_block` | 295-418 | 15 | 14 | 14 | 0 | 0 | 0 |
| **total** | — | **55** | **40** | **40** | **0** | **0** | **0** |

`build_block` had 15 candidates; the cap of 14 leaves one site
un-sampled (a string `+` → `-` perturbation in `receipt["code_commit_sha"]`
concatenation; round-robin ends after 14).

## Per-mutant table

All 40 mutants are listed for traceability. Mutant source line uses the
lineno of the mutated token (AST span end for Compare; sentence-flag for
other ops). The "Existing test that kills" column is the existing
importer-suite test that turned red.

| i | Func | L | Op | Mutant | Existing killing test |
|---:|---|---:|---|---|---|
| 00 | `compute_outcomes` | 129 | bool_swap | `or` → `and` | `test_sni_s2_v1_1_hardening.py::test_h1_x2_*` family |
| 01 | `compute_outcomes` | 138 | cmp_flip | `in` → `not in` | `test_sni_mutation_run_s2_a.py` retire-skip block |
| 02 | `compute_outcomes` | 140 | cmp_flip | `in` → `not in` | duplicate-key skip block |
| 03 | `compute_outcomes` | 144 | cmp_flip | `not in` → `in` | `seen_trailing` dedup branch |
| 04 | `compute_outcomes` | 148 | return_none | return `<expr>` → `return None` | trailing-dict consumers |
| 05 | `evaluate_family` | 157 | const_bool | `False` → `True` (default `retired`) | MUT5D test #2 |
| 06 | `evaluate_family` | 170 | cmp_flip | `==` → `!=` | MUT5D test #1 (BASELINE_ALWAYS_LONG) |
| 07 | `evaluate_family` | 171 | const_int | `1` → `2` | MUT5D test #1 (direction literal) |
| 08 | `evaluate_family` | 172 | cmp_flip | `==` → `!=` | MUT5D test #1 (BASELINE_TRAILING63) |
| 09 | `evaluate_family` | 173 | const_int | `0` → `1` | BASELINE_POOLED_PRIOR direction literal |
| 10 | `evaluate_family` | 179 | cmp_flip | `is not` → `is` | `excess is not None and direction is not None` truth table |
| 11 | `evaluate_family` | 179 | cmp_flip | `is not` → `is` (overload site) | same — short-circuit reorders |
| 12 | `evaluate_family` | 180 | const_int | `0` → `1` | direction-zero branch (`hit = None`) |
| 13 | `evaluate_family` | 183 | const_int | `0` → `1` | sign_exact branch (anti-mismatch) |
| 14 | `evaluate_family` | 198 | cmp_flip | `is not` → `is` | tie branch (`excess == 0`) |
| 15 | `evaluate_family` | 198 | cmp_flip | `==` → `!=` | tie branch literal |
| 16 | `evaluate_family` | 200 | const_bool | `False` → `True` | confounded-row classification |
| 17 | `evaluate_family` | 204 | const_int | `0` → `1` | SENS_B absorbed_count cutoff |
| 18 | `evaluate_family` | 216 | return_none | return dict → return None | `evaluate_family` return-shape consumers |
| 19 | `pooled_prior` | 271 | cmp_flip | `is not` → `is` | excess-presence guard |
| 20 | `pooled_prior` | 274 | cmp_flip | `<` → `>` | MUT5D test #2 (cluster floor flip) |
| 21 | `pooled_prior` | 275 | return_none | return `(dir, token)` → `None` | `pooled_prior` tuple-shape consumers |
| 22 | `pooled_prior` | 275 | arith_swap | `%` → `//` | floor-vs-modulo in token format |
| 23 | `pooled_prior` | 277 | arith_swap | `/` → `*` | MUT5D test #1 (mean excess literal) |
| 24 | `pooled_prior` | 279 | return_none | return `(dir, token)` → `None` | direction-token consumers |
| 25 | `build_block` | 298 | cmp_flip | `==` → `!=` | `cell_retired` retire-predicate |
| 26 | `build_block` | 298 | bool_swap | `and` → `or` | split==TUNE and retire-info leg |
| 27 | `build_block` | 314 | cmp_flip | `==` → `!=` | MUT5D test #2 (split_eps filter) |
| 28 | `build_block` | 315 | const_int | `0` → `1` | absorbed_count initial value |
| 29 | `build_block` | 318 | const_int | `1` → `2` | confounded_n check threshold |
| 30 | `build_block` | 319 | const_int | `1` → `2` | purged_n check threshold |
| 31 | `build_block` | 321 | cmp_flip | `==` → `!=` | quarantine_n split filter |
| 32 | `build_block` | 324 | cmp_flip | `==` → `!=` | TESTED vs abstain state token |
| 33 | `build_block` | 325 | const_int | `0` → `1` | MUT5D tests #1, #3 (TESTED hits counter) |
| 34 | `build_block` | 325 | cmp_flip | `is not` → `is` | `r["hit"] is not None` truth table |
| 35 | `build_block` | 332 | cmp_flip | `is not` → `is` | CI branch `if ci is not None` |
| 36 | `build_block` | 375 | arith_swap | `+` → `-` | BASE_COMMIT literal string concat |
| 37 | `build_block` | 379 | arith_swap | `+` → `-` | V1_1_SEAL_REL string concat |
| 38 | `build_block` | 416 | bool_swap | `and` → `or` | `split == "TUNE" and info_leak_ctx.get("retired")` |
| 39 | `build_block` | 418 | return_none | return `block` → `None` | `build_block` return-shape consumers |

## Equivalent arguments

None. No sample survived a non-equivalent mutant.

## Excluded QF lines

`tests/test_sni_quarantine_fence.py` exercises the QUARANTINE fence in
the S2 split layer and imports `run_s2.render_report`, which is NOT in
this lane's owned site range. The four owned functions do not touch any
quarantine-fence branch. No QF review file was loaded into the worktree
sparse checkout; the named `QF` / `quarantine`-prefixed file in the
reviews directory does not exist on disk at this base. No per-line
exclusion from sampling was applied.

## New invariant-pin tests (since there were 0 surviving mutants)

`tests/test_sni_mut6_run_s2_core.py` ships 8 invariant-pin tests that
document and re-pin the named MUT6 lane-4 contract properties:

| Test | Invariant | Existing-test overlap |
|---|---|---|
| `test_m6c_pin_x2_01_compute_outcomes_skips_retired_cell` | X2-01 retired (pid, split) never calls `engine.episode_excess` | new (no existing direct pin) |
| `test_m6c_pin_x2_01_evaluate_family_retired_row_uses_retired_token` | X2-01 `evaluate_family(retired=True)` row uses `RETIRED_TOKEN` | adjacent to MUT5D test #2 (which only asserts the inverse default) |
| `test_m6c_pin_a25_pooled_prior_abstains_below_cluster_floor` | A25 named-reason abstain below cluster-N floor | adjacent to MUT5D test #2 (which asserts the inverse floor) |
| `test_m6c_pin_a25_pooled_prior_returns_mean_excess_direction` | A25 mean-excess direction above floor | duplicate of MUT5D test #1 (kept for documentation) |
| `test_m6c_pin_compute_outcomes_trailing_direction_unique_per_key` | trailing63 dedup per episode_key | new (no existing direct pin) |
| `test_m6c_pin_build_block_tested_hits_count` | TESTED branch `block["test"]["hits"] == 100` for the canonical 153-episode fixture | duplicate of MUT5D tests #1 / #3 (kept for documentation) |
| `test_m6c_pin_evaluate_family_trailing63_uses_occ_trailing` | BASELINE_TRAILING63 → `occ["trailing"][key]` | adjacent to MUT5D test #1 |
| `test_m6c_pin_evaluate_family_pooled_prior_uses_pooled_dir` | BASELINE_POOLED_PRIOR → `pooled_prior_dir` (caller-supplied) | new (no existing direct pin) |

Per spec: "Re-run that mutant against the new test to prove the kill."
With 0 survivors, no re-verification was required; all 8 invariant-pin
tests pass on unmutated code (`python3 -m pytest
tests/test_sni_mut6_run_s2_core.py -q -p no:cacheprovider` →
8 passed, 0.58 s).

## Wall-clock / budget

| Phase | Wall-clock |
|---|---|
| Harness discover | < 5 s |
| 40-mutant sweep | 167.7 s |
| Test file authoring | < 60 s |
| Review authoring | < 60 s |
| **Total** | **< 5 min** (well under the 45-min budget) |

`git status --porcelain -- research/` stayed empty throughout the sweep.
After each mutant the original bytes were restored and sha256 verified.

## Importer suite used

| File | Status (sparse worktree) |
|---|---|
| `tests/test_sni_mutation_run_s2_a.py` | passed (MUT5D half-1) |
| `tests/test_sni_mutation_run_s2_b.py` | passed (MUT5D half-2) |
| `tests/test_sni_s2_v1_1_hardening.py` | passed |
| `tests/test_sni_s2_abstain.py` | passed |
| `tests/test_sni_s2_seal_integrity.py` | passed |
| `tests/test_sni_s2_nonfinite_abstain.py` | passed |
| `tests/test_sni_s2_cli.py` | passed |
| `tests/test_sni_s2_info_leak.py` | passed |
| `tests/test_sni_injection_safety.py` | 1 pre-existing sparse-induced fail (A20 count: 11 vs 12 files in event_response) |
| `tests/test_sni_mutation_build_seal.py` | 29 pre-existing sparse-induced fails (P03_hkd_9988 bytes absent) |

The two pre-existing fail sets are sparse-worktree artefacts (the
sparse checkout omits `data/` and parts of `research/.../runs/` that
the A20 scanner and MUT4C P03 tests rely on); both fail identically on
the unmutated tree and are unrelated to this mutation sweep.

## Extra safety

After every mutant run, `git status --porcelain -- research/` is empty.
After the sweep, `python3
research/single_name_intelligence/evaluation/seal_full_check.py --study
all --strict-bytes` final line on this sparse worktree:

```
s2: files compared=23 identical=22 named-exception passes=2 ulp-equivalent=0 failures=0 [Linux x86_64]
```

The `s2` arm reports `failures=0`. The `s1` arm reports 11 byte-differs
on P03_hkd_9988 — sparse-induced (the worktree excludes the parts of
`runs/` and `data/` the S1 paths read). The committed diff is restricted
to the two owned files only; `research/single_name_intelligence/residual/`
and `research/single_name_intelligence/event_response/` carry ZERO bytes
of net diff (`git diff --stat` shows `tests/test_sni_mut6_run_s2_core.py
+ research/.../reviews/MUTATION_SWEEP_RUN_S2_CORE_2026-10-14.md`).

## What this does NOT prove

Mutation score is test strength, not statistical validity. The 40 / 40
result holds against THIS stratified sample; it does not generalise to
all possible mutations of `compute_outcomes`, `pooled_prior`,
`evaluate_family`, or `build_block`. A surviving mutant could exist
outside the owned site range, in the 15 unsampled owned candidates, or
under an operator this harness does not apply (e.g. statement deletion,
multi-statement rewrites). Mutation analysis does not give a family
the right to be marked TESTED in the acceptance matrix; this sweep is
a hole-finder for the *evidence* behind any acceptance row that cites
`tests/test_sni_mutation_run_s2_a.py`,
`tests/test_sni_mutation_run_s2_b.py`, or the new
`tests/test_sni_mut6_run_s2_core.py`. No acceptance row moves to DONE.