# M8C mutation sweep — `sni_denominator_guard.py` and `sni_comparison_guard.py` (2026-10-14)

Lane M8C (build route), SNI commission 8659. Re-sweep of the two
FAMILY TEXT RULE v2 DRAFT guards, replacing any stale kills recorded under
the pre-v2 contract. Target modules:

- `research/single_name_intelligence/common/sni_denominator_guard.py` — all functions
- `research/single_name_intelligence/common/sni_comparison_guard.py` — all functions

No production code was changed; the committed diff is one new test file
plus this review. The target-module baselines are byte-identical to the
base commit `9a2682e4a5f1f9794acf168f512d96d819476b05`.

## Summary

| generated | killed-before | survived-before | killed-after | equivalent | timeout |
|---|---|---|---|---|---|
| 80 (40 per module) | 46 | 34 | 60 (46 + 14 new-test kills) | 20 | 0 |

- Mutation score before: **46/80 = 0.575**
- Mutation score after: **60/80 = 0.750** (60/60 = 1.000 over non-equivalent mutants)
- Killing tests added: **15** (`tests/test_sni_mut8_c.py`); 14 of them kill
  mutants the existing importer suite missed, 1 anchors the
  all-False module-level `AUTHORITY_FLAGS` contract.
- Baseline importer suite (unmutated, existing tests only): 392 passed
  + 1 xfailed in ~2.79 s (< 20 s cap, so the full 40+40 mutant budget
  applied). With the new test file: 407 passed + 1 xfailed in ~3.48 s.
- Target-module baseline sha256 (restored and verified after every mutant):
  - `sni_denominator_guard.py`: `e6373bf142e3b551fdabfb08b8a9135c571997f13abff4e178a1c985fb29866b`
  - `sni_comparison_guard.py`: `a30696fb953c38d209b1f77cecf700fdc0f6919bf8a94f28a4c74aeea5f98a4b`

Importer test set (tests that import either module): grep over
`tests/test_sni_*.py` for `sni_denominator_guard` and
`sni_comparison_guard` returns seven files. They are split per module:

- For `sni_denominator_guard`:
  `tests/test_sni_denominator_guard.py`,
  `tests/test_sni_guard_family_invariants.py`,
  `tests/test_sni_guard_chain_composition.py`,
  `tests/test_sni_famdc_repair.py`,
  `tests/test_sni_mut7_f.py`.
- For `sni_comparison_guard`:
  `tests/test_sni_comparison_guard.py`,
  `tests/test_sni_guard_family_invariants.py`,
  `tests/test_sni_guard_chain_composition.py`,
  `tests/test_sni_mut7_g.py`.

Each was run as `python3 -m pytest <set> -x -q -p no:cacheprovider`
under `timeout 60`. The after-sweep re-runs the same union plus
`tests/test_sni_mut8_c.py`.

## Operator set and seed

Operators (frozen method): comparison flip (`< ⇄ <=`, `> ⇄ >=`,
`== ⇄ !=`); arithmetic swap (`+ ⇄ -`, `* ⇄ /`); constant perturbation
(int n → n+1, `True ⇄ False`); `return x` → `return None` on one return
statement per function; `and ⇄ or`; deletion of one `if …: raise` guard
(replaced with `pass`). Candidates were drawn deterministically with
`random.Random(20261016)` stratified by function (round-robin over
functions, shuffled within each). Each mutant was applied in place to
the target module, the importer test set was run, the original bytes
were restored, and the restore was verified against the baseline
sha256 before the next mutant. The harness lives outside the repo
(`~/lanes/scratch/m8c/harness.py`, not committed).

The denominator module yielded 79 candidate sites; 40 were selected and
applied. The comparison module yielded 72 candidate sites; 40 were
selected and applied. The candidate-pool threshold was therefore
unmet by the 60-mutant budget — `at most 40 mutants per module, 60
total` was raised to `80 (40 + 40)` to keep both modules at the
per-module 40-mutant ceiling, which the frozen method permits.

## Per-module table

| module | site range | candidates | mutants run | killed-before | survived-before | killed-after | equivalent | timeout | score before → after |
|---|---|---|---|---|---|---|---|---|---|
| `sni_denominator_guard.py` | all functions | 79 | 40 | 19 | 21 | 28 | 12 | 0 | 19/40 = 0.475 → 28/40 = 0.700 |
| `sni_comparison_guard.py` | all functions | 72 | 40 | 27 | 13 | 32 | 8 | 0 | 27/40 = 0.675 → 32/40 = 0.800 |
| **total** | | 151 | 80 | 46 | 34 | 60 | 20 | 0 | **0.575 → 0.750** |

## Surviving-mutant list with killing test name

After re-running the sweep with the new test file included, 20
non-equivalent-zero mutants remain. All 20 are EQUIVALENT under the
program law's one-line semantic argument (see "Equivalent arguments"
below). Each equivalent has a one-line argument; the 14 non-equivalent
survivors were killed by the targeted tests listed below.

### `sni_denominator_guard.py` (9 killing tests + 12 equivalents)

| # | mutant id | file:line | original → mutated | killing test |
|---|---|---|---|---|
| 1 | 4 | `_as_date:161:40` | `text[:10]` → `text[:11]` | `test_m8c_denom_as_date_slice_4` |
| 2 | 6 | `_as_datetime:173` | `return datetime(parsed.year, parsed.month, parsed.day)` → `return None` | `test_m8c_denom_as_datetime_date_only_6` |
| 3 | 19 | `refuse_nonfalse_authority:87-88` | delete `if not isinstance(flags, Mapping): raise ValueError(...)` | `test_m8c_denom_refuse_nonfalse_authority_non_mapping_19` |
| 4 | 21 | `_text_present:131:22` | `value[-1]` → `value[+1]` | `test_m8c_denom_text_present_minus_one_to_plus_one_21` |
| 5 | 23 | `_blank:144:15` | `return True` → `return False` | `test_m8c_denom_blank_empty_string_23` |
| 6 | 28 | `_finite_positive:224:23` | `return value > 0` → `return value > 1` | `test_m8c_denom_finite_positive_float_28` |
| 7 | 29 | `refuse_nonfalse_authority:79-83` | delete `if value is not False: raise ValueError(...)` (AUTHORITY_FLAGS loop) | `test_m8c_denom_refuse_nonfalse_authority_module_flags_29` (monkeypatch) |
| 8 | 30 | `_as_date:158:46` | `len(text) < 10` → `len(text) <= 10` | `test_m8c_denom_as_date_lt_to_le_30` |
| 9 | 38 | `_as_datetime:176:22` | `body[:-1]` → `body[:-2]` | `test_m8c_denom_as_datetime_z_suffix_38` |

### `sni_comparison_guard.py` (5 killing tests + 8 equivalents)

| # | mutant id | file:line | original → mutated | killing test |
|---|---|---|---|---|
| 1 | 2 | `_finite_positive_real:217:23` | `return value > 0` → `return value > 1` | `test_m8c_comp_finite_positive_real_one_2` |
| 2 | 8 | `_fx_reasons:281-282` | delete `if not isinstance(fx, Mapping): raise TypeError(...)` (defense-in-depth; the public `check_comparison` L335 already raises TypeError on the same input, so this guard is reachable only via a direct call to `_fx_reasons`) | `test_m8c_comp_fx_reasons_non_mapping_8` |
| 3 | 16 | `_text_present:151:22` | `value[-1]` → `value[+1]` | `test_m8c_comp_text_present_minus_to_plus_16` |
| 4 | 26 | `_text_present:150:22` | `value[0]` → `value[1]` | `test_m8c_comp_text_present_zero_to_one_26` |
| 5 | 37 | `_text_present:151:23` | `value[-1]` → `value[-2]` | `test_m8c_comp_text_present_minus_one_to_minus_two_37` |

### `sni_denominator_guard.py` — 12 equivalent survivors (one-line each)

| id | site | original → mutated | EQUIV argument |
|---|---|---|---|
| 2 | `_finite_positive:218` | `return False` → `return None` | caller uses `not _finite_positive(...)`; `None` is observationally identical to `False`. |
| 12 | `check_denominator:290:4` | `*` → `/` (PEP 570 keyword-only marker in `def check_denominator(request, observation, *, as_of=...)`) | no caller passes `as_of=` positionally, so positional-only `as_of` makes no observable difference. |
| 16 | `_aware_datetime:194` | `return None` → `return None` | no-op: the original line was already a literal `return None`. |
| 18 | `_finite_positive:223` | `return False` → `return None` | caller uses `not _finite_positive(...)`; `None` is observationally identical to `False`. |
| 20 | `_as_date:159` | `return None` → `return None` | no-op: the original line was already a literal `return None`. |
| 22 | `_as_datetime:172` | `return None` → `return None` | no-op. |
| 25 | `_correction_version_value:210` | `return None` → `return None` | no-op. |
| 27 | `_available_as_of:247` | `return False` → `return None` | caller uses `if not _available_as_of(...)`; `None` and `False` are observationally identical. |
| 32 | `_as_datetime:180` | `return None` → `return None` | no-op. |
| 33 | `_nested:202` | `return None` → `return None` | no-op. |
| 35 | `_correction_version_value:212` | `return None` → `return None` | no-op. |
| 36 | `_aware_datetime:192` | `return None` → `return None` | no-op. |

### `sni_comparison_guard.py` — 8 equivalent survivors (one-line each)

| id | site | original → mutated | EQUIV argument |
|---|---|---|---|
| 1 | `_present:169` | `return _text_present(fact.get(key))` → `return None` | `_present` is defined but has no callers anywhere in the SNI tree (grep); the mutation is unobservable. |
| 7 | `_as_aware_datetime:201` | `return None` → `return None` | no-op. |
| 9 | `_as_date:178` | `return None` → `return None` | no-op. |
| 10 | `_as_datetime:187` | `return None` → `return None` | no-op. |
| 18 | `_as_aware_datetime:209` | `return None` → `return None` | no-op. |
| 27 | `check_comparison:317:4` | `*` → `/` (PEP 570 keyword-only marker) | no caller passes `as_of=` positionally. |
| 36 | `_leg_reasons:238:4` | `*` → `/` (PEP 570 keyword-only marker) | no caller passes `as_of=`/`requested_role=` positionally. |
| 39 | `_as_aware_datetime:205` | `return None` → `return None` | no-op. |

## Equivalent arguments

The 20 equivalent survivors break down into four equivalence classes:

1. **Textual no-op (`return None` → `return None`)**: 11 of 20
   (ids 16, 20, 22, 25, 32, 33, 35, 36 in denominator; 7, 9, 10, 18, 39
   in comparison). The harness's return-site enumeration picked a line
   whose original value was already `ast.Constant(value=None)`; the
   mutation is a byte-identical no-op.

3. **Falsy-equivalent (`return False` → `return None`)**: 3 of 20
   (denom ids 2, 18, 27). Each call site coerces the return via `not
   …(...)` or `if not …(...)`, where `None` and `False` are
   observationally identical.

5. **Keyword-only-marker (`*` → `/`)**: 3 of 20 (denom id 12, comp
   ids 27, 36). These tokens sit on `def ...(*, as_of, ...)` /
   `def ...(..., /, as_of, requested_role)` parameter lists (PEP 570).
   All callers pass the affected parameters as keyword arguments, so
   reordering them to positional-only is a no-op at every call site.

7. **Unreachable / dead (`_present`)** in the comparison module: 1
   of 20. `_present` is defined but has no callers in any of the
   SNI modules (verified by grep over the whole tree).

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
censuses fence points in the S1/S2 manifest, build-spec, and
event_response modules; it mentions `sni_denominator_guard` /
`sni_comparison_guard` nowhere. **0 mutants were excluded** — no
owned site in either target module is a QF fence line.

## What this does NOT prove

- A mutation score measures TEST STRENGTH, not statistical validity: a
  higher score says the suite pins more of the module's local behavior,
  not that the A11 share-count binding or the A13 comparison-refusal
  idea is correct, calibrated, or predictive.
- 40 of 79 (denominator) and 40 of 72 (comparison) candidate sites
  were sampled (deterministic, stratified); the unsampled sites are
  unmeasured, and operators outside the frozen set (e.g., swapped
  argument order, off-by-one day, string mutations) were not tried.
- No acceptance row moves to DONE on this evidence; this sweep only
  strengthens the test behind rows that already cite the importer
  suite.
- The `_present` dead-code equivalence in the comparison module is
  observed today; a future caller that starts using `_present` would
  observe the change.

## Verification receipts

- New tests unmutated: `python3 -m pytest tests/test_sni_mut8_c.py -q
  -p no:cacheprovider -rs` → 15 passed.
- Combined unmutated (importer union + new): `python3 -m pytest
  tests/test_sni_comparison_guard.py tests/test_sni_denominator_guard.py
  tests/test_sni_guard_family_invariants.py
  tests/test_sni_guard_chain_composition.py tests/test_sni_famdc_repair.py
  tests/test_sni_mut7_g.py tests/test_sni_mut7_f.py
  tests/test_sni_mut8_c.py -q -p no:cacheprovider` → 407 passed,
  1 xfailed, 0 failed.
- Seal: `python3 research/single_name_intelligence/evaluation/seal_full_check.py
  --study all --repo-root .` → `SEAL FULL CHECK: OK`.
- Module bytes before/after the whole sweep and before commit:
  - `sni_denominator_guard.py`: `e6373bf142e3b551fdabfb08b8a9135c571997f13abff4e178a1c985fb29866b`
  - `sni_comparison_guard.py`:   `a30696fb953c38d209b1f77cecf700fdc0f6919bf8a94f28a4c74aeea5f98a4b`
  (both identical to base `9a2682e4a5f1f9794acf168f512d96d819476b05`).
- Every targeted killing test was re-verified by re-applying the exact
  mutant and running `python3 -m pytest tests/test_sni_mut8_c.py::<name>
  -p no:cacheprovider`: all 14 re-runs failed with rc=1 (test FAIL),
  and the module bytes were restored to baseline sha256 between every
  re-application (verified by the same script).