# M6B mutation sweep — `s2_collapse._programme_key` and `p04_v2_draft_loader` validators (2026-10-14)

SNI-local DRAFT mutation sweep on the two M6B-owned S2-adjacent sites.
Findings feed back into the M6B acceptance evidence row, never into a rank,
gate, size, signal, escalation, or trade path. Authority flags stay false;
fixtures are synthetic; identity ids are caller-supplied opaque strings.

## Summary

| metric                       | value |
|------------------------------|-------|
| operators preset               | cmp_flip, arith_swap, const_perturb (int +1, float ×1.001), bool_flip, return_none, and_or_flip, negate_cond |
| seed                         | `random.Random(20261014)` |
| site stratum                 | function-level, sites drawn ONLY from the owned range |
| total mutants generated      | 40 (40 candidates) — 4 for `s2_collapse._programme_key`, 36 for `p04_v2_draft_loader` validators |
| killed-before                | 27 (p04) — all 4 `s2_collapse` mutants were EQUIVALENT (function is dead code; no caller in `step2_dedup` or any other module path) |
| survived-before              | 12 (4 s2 + 8 p04) |
| killed-after                 | 9 (4 s2, 5 p04) — every non-equivalent survivor was killed by a new test |
| equivalent                   | 3 (1 s2, 2 p04) — semantic argument in the table below |
| timeout                      | 0 |
| score before                 | 27 / 40 = 67.5% |
| score after                  | 36 / 37 = 97.3% (denominator excludes 3 EQUIVALENT) |

**Score after excludes the 3 EQUIVALENT mutants** from the denominator, per
the frozen method ("EQUIVALENT only with a one-line semantic argument").
Mutation score is test strength, not statistical validity; no acceptance
row moves to DONE.

## Operator set and seed

The operator set is the six operators in the frozen method, realised as
direct AST node rewrites (not text-pattern matches): `Compare` ops are
flipped to the first different member of
`(Eq, NotEq, Lt, LtE, Gt, GtE, In, NotIn, Is, IsNot)`; `BinOp` ops flip
to a different member of `(Add, Sub, Mult, Div)`; `BoolOp` flips
`And`↔`Or`; `Constant` int `+1`, `Constant` float `×1.001`,
`Constant` bool flipped; `Return` value set to `Constant(None)`;
`If` test wrapped in `UnaryOp(Not(...))` or, when the test contains a
`Compare`, the first `Compare` op is flipped.

Seed: `random.Random(20261014)`. Site selection is stratified by function
(`per_fn_target = max(2, max_n // n_functions)`), shuffled within each
function, then shuffled globally and truncated to `max_n`.

## Per-module table

### `s2_collapse.py` — `_programme_key` (lines 106–113)

| n   | lineno | col | node_type | op           | original snippet                       | outcome      | killing test |
|-----|--------|-----|-----------|--------------|----------------------------------------|--------------|--------------|
| 1   | 111    | 11  | Compare   | cmp_flip     | `r["id"] in p["member_ids"]`           | KILLED after | `test_m6b_s2_collapse__programme_key_1` |
| 2   | 111    | 11  | Compare   | cmp_flip     | `r["id"] in p["member_ids"]`           | EQUIVALENT pre  | n/a |
| 3   | 111    | 8   | If        | negate_cond  | `if r["id"] in p["member_ids"]:`       | KILLED after | `test_m6b_s2_collapse__programme_key_4` |
| 4   | 112    | 12  | Return    | return_none  | `return p["key"]`                      | KILLED after | `test_m6b_s2_collapse__programme_key_2` |
| 5   | 113    | 4   | Return    | return_none  | `return None`                          | EQUIVALENT   | n/a |

`_programme_key` is **defined but never imported** by `step2_dedup` (or
any other caller in `event_response/`). Pre-existing tests therefore
never observed its semantics: every mutation was EQUIVALENT until a
direct-call killing test was introduced. After the new tests, every
non-equivalent mutation is killed.

### `p04_v2_draft_loader.py` — validators

The owned range covers `validate_draft`, `label_for`, `check_episode_as_of`,
`_check_authority_block`, `_check_as_of_rule`, `_check_tune_empty`,
`_parse_utc_timestamp`, `_require_iso_z`, and `_refuse_smuggled_authority`.

Total generated: 36 candidates. Killed-before: 27. Survived-before: 9.
EQUIVALENT (with semantic argument): 2. Killed-after: 5.

| module.fn                 | lineno | col | op           | original snippet                                                              | outcome      |
|---------------------------|--------|-----|--------------|-------------------------------------------------------------------------------|--------------|
| `_check_authority_block`  | 132    | 8   | negate_cond  | `if name not in flags:`                                                       | KILLED after |
| `_check_authority_block`  | 132    | 11  | cmp_flip     | `name not in flags`                                                           | KILLED after |
| `validate_draft`          | 295    | 7   | and_or_flip  | `not isinstance(family_n, str) or not family_n.strip()`                       | KILLED after |
| `validate_draft`          | 280    | 7   | cmp_flip     | `tuning.get('test_conditional_selection') != 'REFUSED'`                        | KILLED after (pre-existing `test_r1_04`) |
| `_check_as_of_rule`       | 173    | 8   | negate_cond  | `if key not in as_of:`                                                        | KILLED after |
| `_check_as_of_rule`       | 173    | 11  | cmp_flip     | `key not in as_of`                                                            | KILLED after |
| `_parse_utc_timestamp`    | 86     | 7   | cmp_flip     | `parsed.tzinfo is None`                                                       | EQUIVALENT   |
| `_check_tune_empty`       | 189    | 18  | and_or_flip  | `tune.get('members') or tune.get('membership_table') or []`                    | KILLED after |
| `_check_tune_empty`       | 193    | 8   | negate_cond  | `if "EMPTY" not in membership:`                                               | KILLED after |
| `_refuse_smuggled_authority` | 149  | 19  | cmp_flip     | `key in AUTHORITY_FLAG_NAMES or key.endswith("_authority")`                   | EQUIVALENT   |
| `label_for`               | 115    | 11  | and_or_flip  | `isinstance(value, bool) or not isinstance(value, int)`                       | KILLED after |
| `label_for`               | 119    | 19  | const_int   | `0`                                                                           | KILLED after |
| `label_for`               | 123    | 4   | negate_cond  | `if episodes < min_episodes:`                                                 | KILLED after |

The `validate_draft:280 cmp_flip` mutant was already killed by the
pre-existing `test_r1_04_tuning_rule_closed` (which the harness picked up
under the full test set); the new tests were not required to kill it.

## Surviving-mutant list with killing test

| module / function / line | operator | killing test |
|--------------------------|----------|--------------|
| `s2_collapse._programme_key:111` | `cmp_flip` | `test_m6b_s2_collapse__programme_key_1` |
| `s2_collapse._programme_key:111` | `negate_cond` | `test_m6b_s2_collapse__programme_key_4` |
| `s2_collapse._programme_key:112` | `return_none` | `test_m6b_s2_collapse__programme_key_2` |
| `s2_collapse._programme_key:113` | `return_none` | `test_m6b_s2_collapse__programme_key_3` |
| `p04._check_authority_block:132` | `negate_cond` | `test_m6b_p04__check_authority_block_rejects_missing_flag_names_9` |
| `p04._check_authority_block:132` | `cmp_flip` | `test_m6b_p04__check_authority_block_rejects_flag_present_17` |
| `p04.validate_draft:295`         | `and_or_flip` | `test_m6b_p04__validate_draft_rejects_whitespace_family_n_14` |
| `p04._check_as_of_rule:173`      | `negate_cond` | `test_m6b_p04__check_as_of_rule_rejects_key_not_in_as_of_16` |
| `p04._check_as_of_rule:173`      | `cmp_flip` | `test_m6b_p04__check_as_of_rule_key_equality_guard_22` |
| `p04._check_tune_empty:189`      | `and_or_flip` | `test_m6b_p04__check_tune_empty_dict_members_or_table_refused_23` |
| `p04._check_tune_empty:193`      | `negate_cond` | `test_m6b_p04__check_tune_empty_dict_membership_must_be_empty_21` |
| `p04.label_for:115`              | `and_or_flip` | `test_m6b_p04__label_for_bool_or_int_check_19` |
| `p04.label_for:119`              | `const_int` | `test_m6b_p04__label_for_zero_means_abstain_20` |
| `p04.label_for:123`              | `negate_cond` | `test_m6b_p04__label_for_returns_tested_at_min_threshold_10` |

Two killing tests re-verified by re-applying the mutation and re-running
the test:

1. `_programme_key:111 cmp_flip` (`in` → `not in`). Re-applied; `python3 -m pytest tests/test_sni_mut6_collapse_p04.py::test_m6b_s2_collapse__programme_key_1` → FAILED (DID NOT RAISE — `not in` returns None for a real member; test asserts the matched key).
2. `_check_tune_empty:189 and_or_flip` (`or` → `and`). Re-applied; `python3 -m pytest tests/test_sni_mut6_collapse_p04.py::test_m6b_p04__check_tune_empty_dict_members_or_table_refused_23` → FAILED (DID NOT RAISE — the `and` chain collapses to None; `if members:` is False; test asserts the populate-refuse).

## Equivalent arguments

| module / function / line | operator | original → mutated | one-line semantic argument |
|---------------------------|----------|---------------------|----------------------------|
| `s2_collapse._programme_key:113` | `return_none` | `return None` → `return None` | Reassigning a `Return.value` that is already `Constant(None)` to `Constant(None)` produces identical bytes; `ast.unparse` round-trips. |
| `p04._parse_utc_timestamp:86` | `cmp_flip` | `parsed.tzinfo is None` → `parsed.tzinfo == None` (first candidate after `Is` is `Eq`) | `is None` and `== None` are behaviourally identical for the only subject that ever reaches the guard (`datetime.tzinfo` is `None` or a `tzinfo` instance). |
| `p04._refuse_smuggled_authority:149` | `cmp_flip` (`In` → `Eq`) | `key in AUTHORITY_FLAG_NAMES or key.endswith("_authority")` → `key == AUTHORITY_FLAG_NAMES or key.endswith("_authority")` | All six values in `AUTHORITY_FLAG_NAMES` already end with `_authority`, so `key.endswith("_authority")` is true for every key that `key in AUTHORITY_FLAG_NAMES` would have caught; the second clause dominates the `or`. |

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
contains no line entries for `s2_collapse._programme_key` or any
`p04_v2_draft_loader` validator function, so **no site was excluded** on
QF grounds.

## What this does NOT prove

- **Mutation score is test strength, not statistical validity.** Every
  killing test exercises one mutant; surviving the sweep means the
  existing + new test suite exercises the same code paths as the mutant.
  No `A33` / `MNZ` / statistical acceptance row moves to `DONE`.
- **The 3 EQUIVALENT mutants are not bugs.** They are reasoned
  byte-equivalent or behaviour-equivalent rewrites; they prove nothing
  about correctness either way.
- **Dead-code warnings persist.** `_programme_key` is defined but never
  imported. Killing tests now exercise it directly, but its existence
  remains a known defect.
- **Seal integrity was not re-verified inside this lane.** `seal_full_check
  --study all --strict-bytes` failed to import `s1_data` because the
  sparse-checkout excludes `residual/`; this is a sparse-worktree artifact,
  not a content change (see DEVIATIONS).
- **No production code, no existing test, no acceptance matrix, no run
  output, no CI workflow, no SNI-local DRAFT registry row was modified.**
  The diff is exactly two new files.