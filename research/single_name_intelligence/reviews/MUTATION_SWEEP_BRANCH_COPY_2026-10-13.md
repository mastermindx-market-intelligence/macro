# MUT3B mutation sweep — ticker_branch_scan / sni_copy_guard — 2026-10-13

SNI-local DRAFT contract review. This sweep measures **test strength** of
the existing import tests against two acceptance-guard modules. It does
not move any acceptance row to DONE. Authority flags stay false; identity
ids remain caller-supplied opaque strings. Fixtures in the killing tests
are synthetic.

Existing tests that import these modules:

- `tests/test_sni_no_ticker_branches.py` — `ticker_branch_scan`
- `tests/test_sni_copy_guard.py` — `sni_copy_guard`

Kill suite used for scoring: those two files. Unmutated run:
`test_sni_no_ticker_branches.py` 6 passed in 0.93 s;
`test_sni_copy_guard.py` 20 passed in 4.94 s. Both under the 20 s cap,
so the sample stayed at 30 mutants per module.

## Summary

| item | count |
|---|---|
| generated (selected) | 60 |
| killed-before | 33 |
| survived-before (non-equivalent) | 24 |
| killed-after | 24 |
| equivalent | 3 |
| timeout | 0 |
| score before | 33/57 = 57.9% |
| score after | 57/57 = 100% |
| new killing tests | 24 |

Score = killed / (generated − equivalent). Raw pytest survivors were 27;
three of those are equivalent (arguments below). Candidate sites before
sampling: 224 in `ticker_branch_scan.py`, 92 in `sni_copy_guard.py`.
Cap 30 per module, seed `20261013`, stratified by function. One
`return x -> return None` site kept per function.

## Operator set and seed

Harness (scratch only, `~/lanes/scratch/mut3b/harness.py`, not committed):

- comparison flip: `<`↔`>`, `<=`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: `int n → n+1`, `float x → x*1.001`, `True`↔`False`
- `return x` → `return None` (one return per function)
- `and`↔`or`
- deletion of one `if ...: raise` guard (`pass`)

`random.Random(20261013)` round-robin over shuffled per-function site lists.
IEEE `0.0 * 1.001` identity sites were dropped before sampling.

Each mutant was applied in place, then
`timeout 60 python3 -m pytest <import tests> -x -q -p no:cacheprovider`
ran, then original bytes were restored and sha256-checked before the next.
`git status --porcelain -- research/` was compared after every mutant
(mutated module path ignored); extra dirt would have been
TIMEOUT-UNSAFE. None occurred. These modules only read files.

## Per-module table

| module | candidates | selected | killed-before | survived-before | killed-after | equivalent | timeout | score before | score after |
|---|---|---|---|---|---|---|---|---|---|
| `ticker_branch_scan.py` | 224 | 30 | 15 | 15 | 15 | 0 | 0 | 15/30 | 30/30 |
| `sni_copy_guard.py` | 92 | 30 | 18 | 9 | 9 | 3 | 0 | 18/27 | 27/27 |
| **total** | **316** | **60** | **33** | **24** | **24** | **3** | **0** | **33/57** | **57/57** |

## Surviving-mutant list with killing test name

All 24 non-equivalent survivors were re-applied against the named new test
and the test raised (KILLED-after).

### ticker_branch_scan.py

| file:line | original → mutated | killing test |
|---|---|---|
| `ticker_branch_scan.py:68` | `rank_authority` `False` → `True` | `test_mut3b_ticker_branch_scan_module_1` |
| `ticker_branch_scan.py:434` | `func.id == "dict"` → `!=` | `test_mut3b_ticker_branch_scan__dict_literal_1` |
| `ticker_branch_scan.py:637` | `_is_test_path` `return True` → `None` | `test_mut3b_ticker_branch_scan__is_test_path_1` |
| `ticker_branch_scan.py:284` | `lines[0][0]` → `lines[1][0]` | `test_mut3b_ticker_branch_scan__minimal_yaml_load_1` |
| `ticker_branch_scan.py:183` | `s[0] == s[-1]` → `!=` | `test_mut3b_ticker_branch_scan__parse_scalar_1` |
| `ticker_branch_scan.py:424` | constructor name-check `and` → `or` | `test_mut3b_ticker_branch_scan__sequence_str_constants_1` |
| `ticker_branch_scan.py:455` | `lineno > len(lines)` → `<` | `test_mut3b_ticker_branch_scan__snippet_1` |
| `ticker_branch_scan.py:199` | `ch == "'"` → `!=` | `test_mut3b_ticker_branch_scan__split_key_value_1` |
| `ticker_branch_scan.py:163` | `in_single = False` → `True` | `test_mut3b_ticker_branch_scan__strip_inline_comment_1` |
| `ticker_branch_scan.py:715` | path-miss `return False` → `None` | `test_mut3b_ticker_branch_scan_allowlist_matches_1` |
| `ticker_branch_scan.py:675` | missing-tree `return out` → `None` | `test_mut3b_ticker_branch_scan_iter_sni_python_files_1` |
| `ticker_branch_scan.py:355` | no-YAML `return frozenset()` → `None` | `test_mut3b_ticker_branch_scan_load_profile_ticker_literals_1` |
| `ticker_branch_scan.py:251` | nested-map `i < n` → `i > n` | `test_mut3b_ticker_branch_scan_parse_list_1` |
| `ticker_branch_scan.py:262` | `lines[i][0]` → `lines[i][1]` | `test_mut3b_ticker_branch_scan_parse_map_1` |
| `ticker_branch_scan.py:397` | `return TICKER_LITERALS` → `None` | `test_mut3b_ticker_branch_scan_refresh_ticker_literals_1` |

### sni_copy_guard.py

| file:line | original → mutated | killing test |
|---|---|---|
| `sni_copy_guard.py:40` | `AUTHORITY_FLAGS` values `False` → `True` | `test_mut3b_sni_copy_guard_module_1` |
| `sni_copy_guard.py:263` | fence predicate `return` → `None` | `test_mut3b_sni_copy_guard__is_fence_line_1` |
| `sni_copy_guard.py:364` | `Finding` subject `a14[0]` → `a14[1]` | `test_mut3b_sni_copy_guard_check_text_1` |
| `sni_copy_guard.py:379` | `finding.line == entry.line` → `!=` | `test_mut3b_sni_copy_guard_is_allowlisted_1` |
| `sni_copy_guard.py:388` | `unallowlisted` list `return` → `None` | `test_mut3b_sni_copy_guard_unallowlisted_1` |
| `sni_copy_guard.py:213` | longest-term `cand[1] - cand[0]` with `0` → `1` | `test_mut3b_sni_copy_guard__first_match_1` |
| `sni_copy_guard.py:263` | fence `or` → `and` | `test_mut3b_sni_copy_guard__is_fence_line_2` |
| `sni_copy_guard.py:400` | delete non-markdown suffix raise | `test_mut3b_sni_copy_guard__require_sni_md_1` |
| `sni_copy_guard.py:383` | allowlist hit `return True` → `False` | `test_mut3b_sni_copy_guard_is_allowlisted_2` |

## Equivalent arguments

- `sni_copy_guard.py:255` `i = j + 1` → `i = j - 1` in `mask_quoted`. For any
  non-empty quoted span, `j >= i+2`, so `j-1` still sits inside the already
  blanked range; the closer is skipped on the next step and the masked
  bytes are identical.
- `sni_copy_guard.py:338` `intent[0]` → `intent[1]` in
  `rule_a14_flow_intent`. `_negator_before` with the match end is true
  whenever it is true with the match start (`end > start`). A different
  answer would need a negator token inside the intent span; none of the
  frozen A14 intent phrases contain one as a whole word.
- `sni_copy_guard.py:350` `success[0]` → `success[1]` in
  `rule_a30_forecast_success`. Same span argument as the A14 case, against
  the frozen A30 success phrases.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
censuses 19 fence points in `residual/s1_manifest.py`, `s1_prereg.py`,
`s1_report.py`, `run_s1.py`, `event_response/s2_seal.py`, `s2_splits.py`,
`run_s2.py`, and `protocols/S0_PROTOCOL_REGISTER.md`. **None of those
lines are in `ticker_branch_scan.py` or `sni_copy_guard.py`.** No mutant
sites were excluded under the QF fence.

## What this does NOT prove

Mutation score is test strength against this operator set and this
30-per-module sample, not statistical validity. A killed mutant does not
mean an acceptance row is well-calibrated. No acceptance-matrix row moves
to DONE. The sweep does not claim completeness over unselected sites
(224+92 candidates, 60 applied). Nothing here feeds a ranker, gate, sizer,
signal, escalation, or trade path.
