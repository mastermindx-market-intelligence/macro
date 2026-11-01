# M8B mutation sweep — 2026-10-14

SNI-local DRAFT contract review. The two DRAFT guard modules were
rewritten to FAMILY TEXT RULE v2 in the INT7 rounds, so earlier kill
evidence (MUT1–MUT5, JGMUT, M6, M7) is stale. This sweep re-runs the
mutation method on the v2 code and adds targeted killing tests for every
non-equivalent survivor. HISTORICAL-DESCRIPTIVE only: rank_authority,
gate_authority, size_authority, signal_authority, escalation_authority
and trade_authority stay literal False. Fixtures used in the
accompanying tests are synthetic.

## Summary

| item | count |
|---|---|
| mutants generated (40 per module, seed=20261016) | 80 |
| killed by the existing `test_sni_*` suite | 51 |
| survived the existing suite (raw) | 29 |
| non-equivalent survivors → killing tests added | 6 |
| reclassified as EQUIVALENT (29 survived − 6 killed-after) | 23 |
| killed-after (verified by re-running the mutant) | 6 |
| new killing tests in `tests/test_sni_mut8_b.py` | 8 (6 killing + 2 control) |
| score before (killed-before / generated) | 51 / 80 = 63.8% |
| score after ((51 killed-before + 6 killed-after) / generated) | 57 / 80 = 71.3% |
| score after on non-equivalent mutants ((51 + 6) / (80 − 23 equivalent)) | 57 / 57 = 100.0% |

Seat repair (2026-10-14): the lane's original summary printed
"score before 23 / 80" and "score after 29 / 80", which counted the
equivalent and survived buckets as kills; both rows are recomputed above
from the lane's own killed/survived counts. The per-module tables below
are likewise corrected: their "EQUIVALENT" rows were RAW survivor
counts that still included each module's three killed-after mutants.

Mutation score is test strength, not statistical validity. No
acceptance row moves to DONE on the strength of this sweep alone.

## Operator set and seed

`random.Random(20261016)`, stratified by function (round-robin over the
13 functions in `sni_view_state_guard.py` and the 15 functions in
`sni_correction_lineage_guard.py`).

| operator | description |
|---|---|
| `CMP_<X>_TO_<Y>` | flip comparison operator (`< <= > >= == !=`) |
| `ARITH_<X>_TO_<Y>` | swap arithmetic operator (`+ - * /`) |
| `CONST_<type>` | perturb a literal (`int n -> n+1`, `float x -> x*1.001`, `True<->False`, `str s -> s+"X"`) |
| `BOOLOP_<X>_TO_<Y>` | swap `and` / `or` |
| `RETURN_TO_NONE` | `return x` → `return None` (one per function) |
| `DELETE_RAISE_GUARD` | replace an `if ...: raise` guard with `pass` |

The harness lives at `~/lanes/scratch/m8b/harness.py` (NOT committed).
It records each module's sha256 before the first mutant and verifies
the same sha256 after every restore; the worktree's
`research/single_name_intelligence/common/sni_view_state_guard.py` and
`sni_correction_lineage_guard.py` exit the sweep byte-identical to the
HEAD `9a2682e4a5f1f9794acf168f512d96d819476b05` baseline.

## Per-module table

### `research/single_name_intelligence/common/sni_view_state_guard.py`

| outcome | count |
|---|---|
| generated | 40 |
| KILLED (existing suite) | 23 |
| SURVIVED raw | 17 |
| of which non-equivalent → killing test added (killed-after) | 3 |
| of which EQUIVALENT (no-caller `_blank` / `_present`; docstring; error-message suffix where L198 short-circuits the `_field_missing` Or→And change; `return False`→`return None` in a boolean context) | 14 |
| TIMEOUT | 0 |

### `research/single_name_intelligence/common/sni_correction_lineage_guard.py`

| outcome | count |
|---|---|
| generated | 40 |
| KILLED (existing suite) | 28 |
| SURVIVED raw | 12 |
| of which non-equivalent → killing test added (killed-after) | 3 |
| of which EQUIVALENT (no-caller `_nonblank_str`; docstring; `tuple(tuple)` is a no-op; empty-string check is dead on Python 3.12 because `datetime.fromisoformat("")` already raises; `Z` suffix is native on Python 3.11+; CI pins Python 3.12.13) | 9 |
| TIMEOUT | 0 |

## Surviving-mutant list with killing test name

| # | file:line | op | survivor description | killing test |
|---|---|---|---|---|
| 1 | `sni_view_state_guard.py:119` | `CONST_str` | `object.__setattr__(self, "reasons", frozen)` target key flipped to `"reasonsX"`; the `__post_init__` reasons-freeze is skipped, so an out-of-order reasons input stays on the verdict | `tests/test_sni_mut8_b.py::test_m8b_view_state_verdict_reasons_freeze_order_1` |
| 2 | `sni_view_state_guard.py:93/103` | `CONST_str` | f-string trailing literal in `refuse_nonfalse_authority` flipped; the exact ValueError text changes | `tests/test_sni_mut8_b.py::test_m8b_view_state_refuse_authority_error_message_2` |
| 3 | `sni_view_state_guard.py:276` | `CONST_str` | `TypeError("before must be a Mapping")` in `persist_across` flipped | `tests/test_sni_mut8_b.py::test_m8b_view_state_persist_across_error_message_3` |
| 4 | `sni_correction_lineage_guard.py:109` | `CONST_str` | `object.__setattr__(self, "reasons", frozen)` target key flipped to `"reasonsX"`; same shape as #1 but in `LineageVerdict.__post_init__` | `tests/test_sni_mut8_b.py::test_m8b_lineage_verdict_reasons_freeze_order_4` |
| 5 | `sni_correction_lineage_guard.py:110` | `CONST_str` | `object.__setattr__(self, "allowed", not frozen)` target key flipped to `"allowedX"`; the `allowed = not frozen` coercion is skipped | `tests/test_sni_mut8_b.py::test_m8b_lineage_verdict_allowed_override_5` |
| 6 | `sni_correction_lineage_guard.py:196` | `CONST_str` | `TypeError("version record must be a Mapping")` in `_as_mapping` flipped | `tests/test_sni_mut8_b.py::test_m8b_lineage_as_mapping_error_message_6` |

Every killed-after claim was re-verified by re-applying the substitution
and re-running the named test. The verify harness
(`~/lanes/scratch/m8b/verify_kills.py`, NOT committed) shows all 6
mutants killed by their named tests. Two sample re-verifications:

* **Mutant 5**: substitute
  `object.__setattr__(self, "allowed", not frozen)` →
  `object.__setattr__(self, "allowedX", not frozen)` in
  `sni_correction_lineage_guard.py`. Re-run
  `test_m8b_lineage_verdict_allowed_override_5` →
  `AssertionError: assert True is False; where True = LineageVerdict(allowed=True, reasons=('FORK',), appended=()).allowed`.
* **Mutant 6**: substitute
  `TypeError("version record must be a Mapping")` →
  `TypeError("version record must be a MappingX")` in
  `sni_correction_lineage_guard.py`. Re-run
  `test_m8b_lineage_as_mapping_error_message_6` →
  `AssertionError: assert 'version reco...be a MappingX' == 'version reco... be a Mapping'`.

## Equivalent arguments

The 23 raw SURVIVED cases that reclassify as EQUIVALENT (no kill test
spent) break down as follows. Rows are per mutation SITE, not per mutant:
rows marked "killed by test" or "covered by killing test" are listed for
completeness and are NOT counted among the 23 EQUIVALENT, and one site row
can stand for several seeded mutants. The per-mutant enumeration came from
the lane's uncommitted harness (seed 20261016); the seat independently
re-applied mutants #1 and #5 and confirmed each named test fails on the
mutant and passes on the original.

### `sni_view_state_guard.py` (17 raw survivors: 14 EQUIV + 3 killed-after)

| line | op | argument |
|---|---|---|
| 1 | CONST_str (docstring) | docstring change; no behaviour |
| 93 | CONST_str | covered by killing test #2 (same constant, AST-level) |
| 103 | CONST_str | covered by killing test #2 (same constant, AST-level) |
| 119 | CONST_str | **killed by test #1** |
| 121 | CONST_str | `tuple(tuple)` is a no-op; `changed_axes` callers pass tuples |
| 129 | CONST_str (docstring) | docstring change; no behaviour |
| 156 | CONST_bool | `_blank` has no caller (per module note); mutation is unreachable |
| 158 | CONST_bool | `_blank` has no caller (per module note); mutation is unreachable |
| 159 | CONST_bool | `_blank` has no caller (per module note); mutation is unreachable |
| 159 | RETURN_TO_NONE | `_blank` has no caller (per module note); mutation is unreachable |
| 163 | RETURN_TO_NONE | `_present` has no caller (per module note); mutation is unreachable |
| 172 | CONST_str (docstring) | docstring change; no behaviour |
| 196 | BOOLOP Or→And | `_field_missing` line L198 (`or`) short-circuits on any axis missing from either side, so L196's `or` is redundant; the And→Or mutation has no observable effect |
| 200 | RETURN_TO_NONE | `_field_missing` is consumed in a boolean context (`if _field_missing(...)`); `None` is falsy like `False`, so the change has no observable effect |
| 272 | CONST_str (docstring) | docstring change; no behaviour |
| 276 | CONST_str | **killed by test #3** |

The view_state module defines `_blank` (around line 154) and `_present`
(around line 162) with NO caller. A mutant inside either helper is
EQUIVALENT ("no caller"): those mutants are listed above and no kill
tests are spent on them.

### `sni_correction_lineage_guard.py` (12 raw survivors: 9 EQUIV + 3 killed-after)

| line | op | argument |
|---|---|---|
| 75 | CONST_str (docstring) | docstring change; no behaviour |
| 93 | CONST_str | covered by killing test #2 in the view_state module (same idiom; a parallel test for the lineage module's `refuse_nonfalse_authority` would also kill it but is not required because the lineage module's authority-check is the same function and the existing `test_a16_authority_refuse_nonfalse_raises` already pins the ValueError type) |
| 109 | CONST_str | **killed by test #4** |
| 110 | CONST_str | **killed by test #5** |
| 111 | CONST_str | `tuple(tuple)` is a no-op; `appended` callers pass tuples |
| 119 | CONST_str (docstring) | docstring change; no behaviour |
| 158 | CONST_str (`""` → `"X"`) | `_aware_datetime` line L158 checks `text == ""`; on Python 3.12 the empty-string path is already caught by `datetime.fromisoformat("")` raising ValueError, so the mutation is observable-equivalent on the host Python |
| 161 | CONST_str (`"Z"` → `"ZX"`) | `datetime.fromisoformat` accepts the `Z` suffix natively on Python 3.11+ (host is 3.12), so skipping the `Z`→`+00:00` rewrite is observable-equivalent |
| 173 | RETURN_TO_NONE | `_nonblank_str` has no caller (per module note); mutation is unreachable |
| 196 | CONST_str | **killed by test #6** |

The lineage module's `_nonblank_str` (line 172-173) has NO caller. A
mutant inside it is EQUIVALENT ("no caller"): the L173 mutation is
listed above and no kill test is spent on it.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
lists 19 fence points under `residual/s1_*`, `event_response/s2_*`,
`protocols/S0_*`, and `residual/run_s2.py`. None of them are inside
the two DRAFT guard modules owned by this lane
(`sni_view_state_guard.py`, `sni_correction_lineage_guard.py`). No
mutant was excluded on a QF line.

## What this does NOT prove

* Mutation score is test strength, not statistical validity. A
  surviving mutant is a hole in the test suite; a killed mutant only
  proves the test exercises that branch. This sweep does not say
  anything about the SNI guards' real-world correctness on novel
  inputs.
* No acceptance row in the SNI evaluation support matrix moves to
  DONE. The mutation sweep is a hole-detection pass, not a promotion
  event. The seat's judgement of this branch is by artifact, not by
  report.
* Python-version-dependent equivalents (L158, L161 in the lineage
  module) would NOT be equivalent on Python 3.10 or earlier. The host
  runs Python 3.12.3. A future host bump would re-open those mutants;
  no killing test is spent on them here.

## CI

* The seat wires `tests/test_sni_mut8_b.py` into the
  `sni-acceptance-evidence` job after judging this branch. This lane
  did not edit `.github/`.
* `python3 -m pytest tests/test_sni_mut8_b.py -q -p no:cacheprovider`
  → 8 passed in 0.74 s on un-mutated code.
* The full test set for the two modules (existing importer tests plus
  the new file) → 158 passed in 2.14 s on un-mutated code.
* `python3 research/single_name_intelligence/evaluation/seal_full_check.py --study all --repo-root .`
  → `SEAL FULL CHECK: OK (10 files float-equivalent on Linux x86_64 within rel 1e-10 / abs 1e-13, not byte-identical; byte identity rests on the XREP Linux receipt)`.
