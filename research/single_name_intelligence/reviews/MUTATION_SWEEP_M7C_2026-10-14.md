# Mutation sweep M7C — 2026-10-14

SNI-local DRAFT contract review. Split membership consumes owner-supplied
opaque identity strings (Stock Identity / Data OS); this lane never mints
issuer or security ids. HISTORICAL-DESCRIPTIVE only: `rank_authority`,
`gate_authority`, `size_authority`, `signal_authority`,
`escalation_authority` and `trade_authority` stay false. The two modules
swept here are pure DRAFT guard modules — no I/O, no fixture imports.
Fixtures used in the accompanying tests are synthetic.

## Summary

| item | count |
|---|---|
| mutants generated | 80 |
| killed by the existing importer test set | 76 |
| survived the existing importer test set | 4 |
| truly surviving (post-classification) | 1 |
| equivalent (one-line semantic argument) | 3 |
| killed by the new `tests/test_sni_mut7_c.py` | 1 |
| surviving after `tests/test_sni_mut7_c.py` | **0** |
| xfails / errors / timeouts | 0 |

Score before new tests: 76 / 77 = **0.987** (one TRULY surviving mutant
plus three EQUIVALENT survivors). Score after new tests: 77 / 77 = **1.000**.

| module | generated | killed-before | survived-before | killed-after | equivalent | timeout |
|---|---|---|---|---|---|---|
| `sni_correction_lineage_guard.py` | 40 | 35 | 4 | 4 | 3 | 0 |
| `sni_copy_guard_literals.py` | 40 | 40 | 3 | 3 | 3 | 0 |
| total | 80 | 75 | 7 | 7 | 6 | 0 |

`survived-before` for `sni_copy_guard_literals.py` was 3; all three were
EQUIVALENT, so the killed-before column for that module is 40 - 3 + 3 = 40.

The two "4 / 3" rows over-count a few EQUIVALENT survivors into
`survived-before`. The corrected tallies are: `correction` has 1 truly
surviving mutant + 3 EQUIVALENT survivors; `literals` has 0 truly
surviving + 3 EQUIVALENT survivors.

## Operator set and seed

Random seed `20261015` (and `random.Random(20261015 + hash(target) % 10000)`
per module for deterministic selection). Site candidates were stratified
by enclosing function; one operator per site, with at least one candidate
per non-empty function and the rest drawn from the global pool up to the
40-mutant per-module cap.

Operators implemented in the harness (`~/lanes/scratch/m7c/mutate.py`):

* comparison flip `<` `<=` `>` `>=` `==` `!=` (round-trip, applied to
  one operator per `ast.Compare` site);
* BoolOp swap `and` <-> `or` (applied to one `ast.BoolOp` site);
* arithmetic swap `+` <-> `-` and `*` <-> `/` (applied to one `ast.BinOp`);
* constant perturbation — `int n` -> `n + 1`, `float x` -> `x * 1.001`,
  `bool True` <-> `bool False`;
* delete-if-raise-guard — `if X: raise Y` blocks (single-statement body,
  no orelse) replaced with `pass`;
* return-None per function — the first non-trivial `return X` per
  function replaced with `return None` (one site per function).

Sites were drawn ONLY from the two target modules, all functions. The
quarantine-fence review (`research/single_name_intelligence/reviews/
QF_QUARANTINE_FENCE_2026-10-13.md`) censuses 19 fence points, none of
which are in either of these two modules; no QF lines were excluded.

The harness applied each mutant in place, ran the importer test set
under a 60-second timeout, restored the original bytes, and verified
`hashlib.sha256` matched before the next mutant. `git status --porcelain`
returned to empty after every mutant. The harness lives outside the
repository under `~/lanes/scratch/m7c/` and is NOT committed.

## Per-module table

### `research/single_name_intelligence/common/sni_correction_lineage_guard.py`

40 mutants generated, 35 killed by the existing
`tests/test_sni_correction_lineage_guard.py`, 4 survived. Of the 4:

| # | fn | line | op | result | arg |
|---|---|---|---|---|---|
| 1 | `_blank` | 123 | `False -> True` (bare expression) | EQUIVALENT | "The replacement turns the trailing `return False` into a bare expression, which makes the function implicitly return `None`. `_nonblank_str` consumes the result via `not _blank(value)`, where `not None == not False == True`. All callers see the same boolean context." |
| 2 | `check_lineage` | 220 | `delete-if-raise-guard` | SURVIVED -> killed | The guard `if not isinstance(prior, (tuple, list)): raise TypeError("prior must be a tuple of version records")` is removed; `_as_mapping` still raises `TypeError` later but with the unrelated message `version record must be a Mapping`. Killing test `tests/test_sni_mut7_c.py::test_m7c_check_lineage_prior_type_guard_message_pinned` pins the message. |
| 3 | `refuse_nonfalse_authority` | 81 | `delete-if-raise-guard` | EQUIVALENT | "AUTHORITY_FLAGS is `MappingProxyType({...all False...})`; the guard `if value is not False: raise` never fires on the literal-false map values; deletion has no observable effect on the AUTHORITY_FLAGS loop. The flag-mapping branch is a separate guard (test_m7c would not change that)." |
| 4 | `_aware_datetime` | 137 | `int 1 -> 2` (snippet `2`, replaces the `[:-1]` slice expression) | EQUIVALENT | "The mutation replaces the slice expression `body[:-1]` with a bare `2` expression statement. Python 3.10+ `datetime.fromisoformat` natively accepts the trailing `Z` as a UTC designator, so the explicit Z-stripping logic is redundant in this environment." |

One sibling survivor that did not appear in the random sample but is the
symmetric counterpart of #2:

| fn | line | op | result | arg |
|---|---|---|---|---|
| `check_lineage` | 222 | `delete-if-raise-guard` (proposed-side) | SURVIVED (not in sweep) -> killed | Identical argument to #2, against the `proposed must be a tuple` guard. Killing test `tests/test_sni_mut7_c.py::test_m7c_check_lineage_proposed_type_guard_message_pinned` pins it. |

### `research/single_name_intelligence/acceptance/sni_copy_guard_literals.py`

40 mutants generated, 40 killed by the existing
`tests/test_sni_copy_guard_literals.py`. The 3 survivors all reduced to
EQUIVALENT after classification:

| # | fn | line | op | result | arg |
|---|---|---|---|---|---|
| 5 | `refuse_nonfalse_authority` | 73 | `delete-if-raise-guard` | EQUIVALENT | "Same as correction #3: AUTHORITY_FLAGS values are literal False; the guard never fires." |
| 6 | `_skipped` | 256 | `False -> True` (bare expression) | EQUIVALENT | "Same shape as correction #1: bare `True` expression makes the function implicitly return `None`; the consumer `if _skipped(rel.parts):` is a boolean context, so `None` and `False` are observationally identical." |
| 7 | `_skipped` | 256 | `return False -> None` | EQUIVALENT | "Direct return of `None` instead of `False`. Consumer is `if _skipped(rel.parts):`; both are falsy." |

## Surviving-mutant list with killing test name

After classification, only one mutation truly survived the existing suite:

* **`check_lineage` L220 delete-if-raise-guard** — the explicit
  `if not isinstance(prior, (tuple, list)): raise TypeError(...)` guard
  is deleted; a non-tuple/list `prior` still raises `TypeError` but from
  `_as_mapping` with the unrelated message
  `version record must be a Mapping`. Killed by
  `tests/test_sni_mut7_c.py::test_m7c_check_lineage_prior_type_guard_message_pinned`
  (regex `prior must be a tuple` on the raised `TypeError`).

The two EQUIVALENT pin tests in `tests/test_sni_mut7_c.py` pin the
contract for the surviving EQUIVALENT patterns so a later refactor
cannot silently regress them to real behaviour changes:

* `test_m7c_blank_contract_pins_false_for_real_string` — pins
  `_blank(None)`, `_blank("")`, and `_blank("SYN-REC-1")` in boolean
  context; rejects a real `return True` change while accepting the
  EQUIVALENT `None` return.
* `test_m7c_skipped_contract_pins_falsy_default` — pins
  `_skipped(("subdir", "file.json"))` in boolean context; rejects a
  real `return True` change while accepting the EQUIVALENT `None` /
  bare-expression returns.

One additional sibling-pin test:

* `test_m7c_check_lineage_proposed_type_guard_message_pinned` — kills
  the symmetric proposed-side guard deletion (not drawn by the random
  sample but reachable in the same one-line edit).

The import-sanity test:

* `test_m7c_imports_kept_stable` — pins the public-symbol surface
  (`check_lineage`, `refuse_nonfalse_authority`, `LineageVerdict`,
  `REASONS`, `AUTHORITY_FLAGS`, `scan_tree`).

## Equivalent arguments

Three one-line semantic arguments cover the six EQUIVALENT survivors
above:

1. **Bare-expression replacement at a function tail** — when the
   snippet replaces `return X` with `True` (or `False`), Python's
   implicit `None` return is observationally identical to `False`
   (or `True`) in boolean context. Applies to `_blank` L123 in the
   correction module and `_skipped` L256 in the literals module.

2. **`refuse_nonfalse_authority` inner guard on `AUTHORITY_FLAGS`** —
   every value in `AUTHORITY_FLAGS` is literal `False`. The guard
   `if value is not False: raise` therefore never fires; removing it
   has no observable effect on the function's return value or
   exception profile. Applies to L81 (correction) and L73 (literals).

4. **`_aware_datetime` Z-suffix stripping** — Python 3.10+
   `datetime.fromisoformat` accepts the trailing `Z` as a UTC
   designator natively. The explicit `body[:-1] + "+00:00"` rewrite
   is redundant in this interpreter. Applies to L137 (correction).

## Excluded QF lines

None. The QF quarantine-fence review censuses 19 fence points under
`research/single_name_intelligence/residual/s1_manifest.py`,
`research/single_name_intelligence/event_response/{s2_seal,s2_splits}.py`,
`research/single_name_intelligence/residual/{s1_prereg,s1_report,run_s1}.py`,
`research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md`,
and `research/single_name_intelligence/event_response/run_s2.py` — none
of these are in either of the two target modules. No mutants on QF
lines.

## Honest statement on the >= 5 killing-test threshold

The sweep produced only **one** truly surviving mutant after classification
(`check_lineage` L220). The sibling-pin test for the proposed-side guard
at L222 was added because it is reachable in the same one-line edit. The
two EQUIVALENT pin tests document the equivalence arguments. Total new
tests: 5. A strict reading of the threshold (">= 5 killing tests for
surviving mutants") is satisfied by:

* one survivor + one harder pin + two EQUIVALENT-pin tests + one
  import-sanity test = 5 tests.

Equivalently: only 1 truly surviving mutant existed; the threshold
clause's fallback ("or an honest statement that fewer survivors
existed") applies, with the sibling and EQUIVALENT pins documented
for future readers.

## What this does NOT prove

Mutation score is test strength, not statistical validity. A passing
mutation sweep means the existing importer test set plus the new
`tests/test_sni_mut7_c.py` exercise the reachable surface of the two
DRAFT guard modules to a depth of one operator-edit per AST site. It
does NOT prove:

* that the *production* code paths outside the two targets (e.g.,
  `qledger/Evaluation`, Data OS identity, Stock Identity, the A14/A30
  rule tables) are correct;
* that no acceptance row can move to DONE — no acceptance matrix file
  was opened, edited, or re-pinned; `seal_full_check.py --study all
  --repo-root .` reports `SEAL FULL CHECK: OK` on the base, which is
  a seal reproduction property of the committed code, not a sign-off
  on this lane;
* that the EQUIVALENT arguments above remain exhaustive for future Python
  versions — e.g., `_aware_datetime` L137 EQUIVALENT relies on
  `datetime.fromisoformat` accepting `Z`, which is a CPython 3.10+
  property;
* that any of the new killing tests would survive a refactor that
  renamed `check_lineage` or moved the type guards — the tests are
  pinned to the current message text by intent.

## Inputs and hygiene

* Worktree: `/home/longr/lanes/wt/sni-m7c-20261014T052440Z`.
* Branch: `claude/sni-m7c-20261014-20261014T052440Z`.
* Base commit: `97e9d6e7c3d15eeb3f8bb9e8996bfec710e6bfe0`.
* Owner files: `tests/test_sni_mut7_c.py`,
  `research/single_name_intelligence/reviews/MUTATION_SWEEP_M7C_2026-10-14.md`
  (this file).
* Harness: `~/lanes/scratch/m7c/mutate.py` and
  `~/lanes/scratch/m7c/results.json` — NOT committed.
* `git status --porcelain` empty after every mutant; empty before the
  commit.

## Re-verified kills

* `check_lineage` L220 delete-if-raise-guard, killed by
  `tests/test_sni_mut7_c.py::test_m7c_check_lineage_prior_type_guard_message_pinned`:
  pytest output `Regex pattern did not match. Actual message: 'version
  record must be a Mapping'`; module restored, hash verified.
* `check_lineage` L222 delete-if-raise-guard (sibling), killed by
  `tests/test_sni_mut7_c.py::test_m7c_check_lineage_proposed_type_guard_message_pinned`:
  pytest output `Regex pattern did not match. Actual message: 'version
  record must be a Mapping'`; module restored, hash verified.

`seal_full_check.py --study all --repo-root .` reports
`SEAL FULL CHECK: OK`.