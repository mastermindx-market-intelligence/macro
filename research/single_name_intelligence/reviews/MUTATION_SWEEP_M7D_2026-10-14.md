# MUTATION SWEEP M7D — 2026-10-14

Bounded mutation sweep over two SNI DRAFT guard modules, run per the frozen
MUT-lane method (31 sibling lanes MUT1A-C … M6A-M6J preceded it). The sweep
measures TEST STRENGTH of the existing per-module suites; it changes no
production code. Lane M7D, branch `claude/sni-m7d-20261014-20261014T052441Z`,
base `97e9d6e7c3d15eeb3f8bb9e8996bfec710e6bfe0`.

- `research/single_name_intelligence/common/sni_ads_ratio_guard.py` (all functions)
- `research/single_name_intelligence/common/sni_identity_binding_guard.py` (all functions)

SNI DRAFT contract language holds throughout: the guards consume
owner-supplied opaque identity strings (Stock Identity / Data OS), never mint
identifiers, keep every authority flag literal False, and feed no ranker,
gate, sizer, signal, escalation, or trade path. New fixtures are synthetic.

## Summary

| metric | value |
|---|---|
| mutants generated (drawn) | 60 (30 per module, of 125 / 75 candidates) |
| killed by the EXISTING suite ("killed-before") | 42 |
| survived the existing suite ("survived-before") | 18 |
| killed-after (survivors killed by `tests/test_sni_mut7_d.py`, each re-verified by re-applying the mutant) | 15 |
| equivalent (one-line semantic argument below) | 3 |
| timeout | 0 |
| mutation score before | 42/60 = 70.0% |
| mutation score after | 57/57 non-equivalent = 100% (raw 57/60 = 95.0%; the 3 equivalents are unkillable by construction) |
| new tests | 16 (15 killing tests + 1 hardening test for an undrawn site) |

Unmutated baselines: `tests/test_sni_ads_ratio_guard.py` 46 passed (~0.8 s),
`tests/test_sni_identity_binding_guard.py` 43 passed (~0.7 s); both far under
the 20 s cap, so the full 30-per-module budget applied (cap 40/module,
60 total). After the new tests: 105 passed in 1.4 s across all three files.

Importer-test sets (grep over `tests/test_sni_*.py` at the base commit): each
module is imported by exactly one existing file — `tests/test_sni_ads_ratio_guard.py`
and `tests/test_sni_identity_binding_guard.py` respectively. No other
`tests/test_sni_*.py` imports either module.

## Operator set and seed

Operators (frozen method): comparison flip (`<`↔`<=`, `>`↔`>=`, `==`↔`!=`);
arithmetic swap (`+`↔`-`, `*`↔`/`); constant perturbation (int n→n+1,
float x→x*1.001, `True`↔`False`); one `return <expr>`→`return None` per
function (first eligible); `and`↔`or` (first connector per BoolOp); deletion
of one `if ...: raise` guard (raise body→`pass`).

Selection: AST harness (scratch, `~/lanes/scratch/m7d/`, NOT committed) with
`random.Random(20261015)` fresh per module, stratified by function
(round-robin over sorted function groups, each group shuffled by the rng).
Ads module: 30 mutants over 19 functions (11 const, 9 ret, 6 cmp, 4 boolop).
Identity module: 30 mutants over 16 functions (10 const, 11 ret, 5 cmp,
3 boolop, 1 guard). Each mutant applied in place inside the lane worktree,
then `timeout 60 python3 -m pytest <importer tests> -x -q -p no:cacheprovider`;
original bytes restored and sha256-verified after EVERY mutant and at the end
(ads `312b03103549864b…`, identity `88071be3b621d0af6…` — both byte-identical
to base at commit time; `git diff --stat <base> -- …/common/` is empty).

## Per-module table

| module | candidates | drawn | killed-before | survived-before | killed-after | equivalent | timeout | score before → after (non-equiv) |
|---|---|---|---|---|---|---|---|---|
| `common/sni_ads_ratio_guard.py` | 125 | 30 | 22 | 8 | 6 | 2 | 0 | 22/30 (73.3%) → 28/28 (100%) |
| `common/sni_identity_binding_guard.py` | 75 | 30 | 20 | 10 | 9 | 1 | 0 | 20/30 (66.7%) → 29/29 (100%) |
| **total** | 200 | **60** | **42** | **18** | **15** | **3** | **0** | 42/60 (70.0%) → 57/57 (100%) |

## Surviving-mutant list with killing test name

All 15 non-equivalent survivors are killed by `tests/test_sni_mut7_d.py`;
every kill was re-verified by re-applying the stored mutant source and
re-running the three test files (each run: exactly the named test FAILED,
104 passed).

| mutant id | site (file:line, original -> mutated) | killing test |
|---|---|---|
| `sni_ads_ratio_guard_02` | `sni_ads_ratio_guard.py:244` `_ack_ids` `return ()` -> `return None` | `test_m7d_ads_ratio_guard__ack_ids_02` |
| `sni_ads_ratio_guard_03` | `sni_ads_ratio_guard.py:126` `_as_date` `return date.fromisoformat(text[:10])` -> `return None` | `test_m7d_ads_ratio_guard__as_date_03` |
| `sni_ads_ratio_guard_04` | `sni_ads_ratio_guard.py:138` `_as_datetime` `return datetime(...)` -> `return None` | `test_m7d_ads_ratio_guard__as_datetime_04` |
| `sni_ads_ratio_guard_21` | `sni_ads_ratio_guard.py:126` `_as_date` slice `text[:10]` -> `text[:11]` | `test_m7d_ads_ratio_guard__as_date_21` |
| `sni_ads_ratio_guard_22` | `sni_ads_ratio_guard.py:134` `_as_datetime` `len(text) == 10` -> `== 11` | `test_m7d_ads_ratio_guard__as_datetime_22` |
| `sni_ads_ratio_guard_25` | `sni_ads_ratio_guard.py:107` `_blank` `if value is None: return True` -> `return False` | `test_m7d_ads_ratio_guard__blank_25` |
| `sni_identity_binding_guard_02` | `sni_identity_binding_guard.py:131` `_as_date` `return date.fromisoformat(text[:10])` -> `return None` | `test_m7d_identity_binding_guard__as_date_02` |
| `sni_identity_binding_guard_03` | `sni_identity_binding_guard.py:143` `_as_datetime` `return datetime(...)` -> `return None` | `test_m7d_identity_binding_guard__as_datetime_03` |
| `sni_identity_binding_guard_04` | `sni_identity_binding_guard.py:172` `_available_as_of` `return False` -> `return None` | `test_m7d_identity_binding_guard__available_as_of_04` |
| `sni_identity_binding_guard_10` | `sni_identity_binding_guard.py:221` `_id_looks_derived` empty-needles `return False` -> `return True` | `test_m7d_identity_binding_guard__id_looks_derived_10` |
| `sni_identity_binding_guard_11` | `sni_identity_binding_guard.py:180` `_opaque_id` `and` -> `or` | `test_m7d_identity_binding_guard__opaque_id_11` |
| `sni_identity_binding_guard_18` | `sni_identity_binding_guard.py:131` `_as_date` slice `text[:10]` -> `text[:11]` | `test_m7d_identity_binding_guard__as_date_18` |
| `sni_identity_binding_guard_19` | `sni_identity_binding_guard.py:139` `_as_datetime` `len(text) == 10` -> `== 11` | `test_m7d_identity_binding_guard__as_datetime_19` |
| `sni_identity_binding_guard_24` | `sni_identity_binding_guard.py:218` `_id_looks_derived` `if listing is None: return False` -> `return None` | `test_m7d_identity_binding_guard__id_looks_derived_24` |
| `sni_identity_binding_guard_29` | `sni_identity_binding_guard.py:128` `_as_date` `len(text) < 10` -> `< 11` | `test_m7d_identity_binding_guard__as_date_29` |

The surviving-mutant classes are telling: the existing suites exercise the
public refusal contract well (nearly every reason-path, comparison, and
guard-deletion mutant died) but never pin (a) the date/datetime parser edge
lengths, (b) literal-`False` vs falsy return contracts, (c) `_blank(None)`
for keys absent from a record (only blank-string `""` was covered), and
(d) `_opaque_id` type/blank discrimination.

`test_m7d_ads_ratio_guard__covers_day_issuer_hardening` covers the
`_covers_day` issuer-mismatch site (`sni_ads_ratio_guard.py:221-222`), which
the draw did not select; it is hardening, not a killing test, and is not
counted in killed-after.

## Equivalent arguments

1. `sni_ads_ratio_guard_12` — `sni_ads_ratio_guard.py:200`
   `_interval_usable` `if not ok or start is None: return False` -> `True`:
   the only caller that lacks its own re-check is the `matched` comprehension
   feeding `_intervals_overlap`, and `_intervals_overlap` already returns
   `False` for exactly the records this mutant admits (`not aok or not bok
   or a0 is None or b0 is None` guard); `_covers_day` re-checks
   `_interval_usable` AND `not ok or start is None` itself, so no observable
   verdict changes.
2. `sni_ads_ratio_guard_26` — `sni_ads_ratio_guard.py:225` `_covers_day`
   `return False` (under `if not ok or start is None:`) -> `True`: that
   branch is unreachable-true — `_covers_day` returns `False` earlier at the
   `_interval_usable` check for exactly the records where
   `not ok or start is None` holds. Confirmed empirically: the targeted test
   could not distinguish it (re-run rc=0), which is how the dead branch was
   found.
3. `sni_identity_binding_guard_12` — `sni_identity_binding_guard.py:119`
   `_present` `return not _blank(...)` -> `return None`: `_present` has NO
   call site in the module (dead helper, duplicated from the ads guard);
   unreachable from any public entry point.

## Excluded QF lines

`reviews/QF_QUARANTINE_FENCE_2026-10-13.md` censuses fence points in
`residual/s1_manifest.py`, `residual/s1_prereg.py`, `residual/s1_report.py`,
`residual/run_s1.py`, `event_response/s2_seal.py`, `event_response/s2_splits.py`,
`event_response/run_s2.py`, and `protocols/S0_PROTOCOL_REGISTER.md` — none in
either swept `common/` module. **Zero mutants were excluded** for QF fence
lines (no overlap between the fence census and this lane's owned site range).

## What this does NOT prove

- A mutation score measures TEST STRENGTH only. It says nothing about the
  statistical validity, calibration, or usefulness of either guard, and
  nothing about SNI research conclusions.
- **No acceptance row moves to DONE**; this sweep adds killing tests and a
  review record only.
- The draw is bounded: 60 of 200 candidate sites (30/module cap, seed-fixed
  and stratified but not exhaustive); undrawn sites remain unswept.
- EQUIVALENT verdicts are semantic arguments (two rest on dead/redundant
  code, one on an uncalled helper), not machine proofs.
- The two dead-branch findings (`_12`/`_26` in the ads guard, `_present` in
  the identity guard) are redundancy observations about DRAFT code, not
  defects; fixing them is owner/lane work outside this sweep's scope (no
  production edits).

## Reproduction

Scratch harness (not committed): `~/lanes/scratch/m7d/mutate.py`
(`--module <guard> --tests <importer test> --repo-root <worktree> --budget 30
--seed 20261015`), results JSON + stored mutant sources alongside; kill
re-verification via `~/lanes/scratch/m7d/verify_kills.py` (re-applies each
stored survivor mutant, runs all three test files, restores + sha256-checks
the module bytes per iteration).
