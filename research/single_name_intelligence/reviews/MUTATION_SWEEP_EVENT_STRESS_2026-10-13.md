# SNI MUT2 mutation sweep — event-response + US-stress — 2026-10-13

Lane MUT2, commission 8659. AST mutation of six SNI modules; production
bytes unchanged. New tests consume owner-supplied opaque identity strings
and synthetic fixtures only. Every authority flag stays false. Residuals
and event-study numbers are descriptive, never causal, never a news-impact
claim.

Harness (scratch, not committed): `~/lanes/scratch/mut2/harness.py`.
BASE `2c0422bfda93fce61445c308c01e46ee1449e6f4`.

## Summary

| Measure | Count |
|---|---|
| Modules | 6 |
| Candidate sites | 668 |
| Sampled (run) | **218** (cap 40/module, 240 total) |
| Killed before new tests | **133** |
| Survived before | **84** |
| Timeout before | **1** |
| Equivalent (argument below) | **21** |
| Known finding (MNZ-F2), not re-tested | **1** |
| Leftover sampled survivors (no dedicated test) | **12** (all `s2_outcomes`) |
| Killed after new tests (re-verified) | **183** |
| New killing tests | **50** |
| Mutation score before | **133/218 = 61.0%** |
| Mutation score after (excl. equivalent) | **183/197 = 92.9%** |
| Pytest (this file) | **50 passed** |
| Importer tests (sparse, no runs/) | **158 passed** on fully-present files; **13 pre-existing fails** on missing `runs/` + `protocols/` |

Score = killed / (sampled − equivalent). Timeout and MNZ-F2 stay in the
denominator of the after score as not-killed.

## Operator set and seed

Operators (source-slice AST):

- comparison flip (`==`/`!=`, `<`/`>`, `<=`/`>=`, `is`/`is not`, `in`/`not in`)
- arithmetic swap (`+`/`-`, `*`/`/`, `//`/`%`)
- constant perturbation (`n → n+1`, `x → x*1.001`, `True ↔ False`)
- `return <expr>` → `return None`
- `and` ↔ `or`
- deletion of one `if ...: raise` guard (body is only `Raise`, no `else`)

Sample: `random.Random(20261014)`, round-robin stratified by enclosing
function, at most 40 mutants per module.

Per-mutant pytest: tests that import that module, `-x -q`, 120 s
subprocess timeout, original bytes restored and sha256-checked after
each mutant.

Importer tests used (deselected 13 nodeids that fail on this sparse
checkout for missing `runs/` and `protocols/`, named in GAPS):

| Module | Importer tests |
|---|---|
| `s2_stats` | `test_sni_s2_stats.py`, `test_sni_s2_mirror.py`, `test_sni_s2_abstain.py`, `test_sni_common_equivalence.py` |
| `s2_splits` | `test_sni_s2_property.py`, `test_sni_s2_v1_1_hardening.py`, `test_sni_quarantine_fence.py` |
| `s2_selection` | `test_sni_s2_selection.py`, `test_sni_s2_clock.py`, `test_sni_injection_safety.py`, `test_sni_s2_property.py`, `test_sni_s2_v1_1_hardening.py` |
| `s2_collapse` | `test_sni_s2_collapse.py`, `test_sni_s2_clock.py`, `test_sni_s2_property.py`, `test_sni_s2_v1_1_hardening.py` |
| `s2_outcomes` | `test_sni_s2_info_leak.py`, `test_sni_s2_mirror.py`, `test_sni_s2_v1_1_hardening.py` |
| `stress_set` | `test_sni_us_stress.py`, `test_sni_us_stress_onboarding.py`, `test_sni_us_stress_then_known.py` |

`tests/test_single_name_*.py` does not import these six modules.

## Per-module table

| Module | Candidates | Sampled | Killed before | Survived before | Timeout | Eq | Killed after | Score before → after |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `s2_stats` | 29 | 29 | 23 | 6 | 0 | 4 | 25 | 79.3% → 100% (of 25 non-eq) |
| `s2_splits` | 43 | 40 | 35 | 5 | 0 | 0 | 40 | 87.5% → 100% |
| `s2_selection` | 29 | 29 | 18 | 11 | 0 | 3 | 26 | 62.1% → 100% (of 26 non-eq) |
| `s2_collapse` | 63 | 40 | 26 | 13 | 1 | 3 | 36 | 65.0% → 97.3% (36/37 non-eq; 1 timeout) |
| `s2_outcomes` | 66 | 40 | 10 | 30 | 0 | 0 | 27 | 25.0% → 67.5% (27/40; 1 MNZ-F2 + 12 leftover) |
| `stress_set` | 438 | 40 | 21 | 19 | 0 | 11 | 29 | 52.5% → 100% (of 29 non-eq) |
| **total** | **668** | **218** | **133** | **84** | **1** | **21** | **183** | **61.0% → 92.9%** |

`stress_set` has 60 functions; the 40-mutant cap therefore samples 40 of
60 functions (one each).

## Survivors with killing test

Each row was re-applied from the sampled site and failed the named test
(`python3 -m pytest tests/test_sni_mutation_event_stress.py::<test> -q`).

### s2_stats (2)

| i | Site | Mutant | Killing test |
|---|---|---|---|
| 21 | `hit_rate_test` L56 | `k / n` → `k * n` | `test_mut2_s2_stats_hit_rate_test_21` |
| 22 | `hit_rate_test` L56 | `round(..., 6)` → `7` | `test_mut2_s2_stats_hit_rate_test_22` |

### s2_splits (5)

| i | Site | Mutant | Killing test |
|---|---|---|---|
| 26 | `canonical_line` L105 | `ensure_ascii=False` → `True` | `test_mut2_s2_splits_canonical_line_26` |
| 28 | `build_membership` L132 | `census_only=False` → `True` | `test_mut2_s2_splits_build_membership_28` |
| 29 | `build_membership` L138 | `census_only=True` → `False` | `test_mut2_s2_splits_build_membership_29` |
| 32 | `membership_table_rows` L173 | `counts.get(split, 0)` → `1` | `test_mut2_s2_splits_membership_table_rows_32` |
| 38 | `enrich_membership_rows_with_graded` L200 | `line + "\\n"` → `-` | `test_mut2_s2_splits_enrich_membership_rows_with_graded_38` |

### s2_selection (8)

| i | Site | Mutant | Killing test |
|---|---|---|---|
| 13 | `event_census_rows` L121 | `in selected_ids` → `not in` | `test_mut2_s2_selection_event_census_rows_13` |
| 15 | `earnings_census_rows` L156 | `ticker == "BABA"` → `!=` | `test_mut2_s2_selection_earnings_census_rows_15` |
| 21 | `event_source_cells` L223 | `return out` → `None` | `test_mut2_s2_selection_event_source_cells_21` |
| 22 | `coverage_census_rows` L234 | `cell == source_cell` → `!=` | `test_mut2_s2_selection_coverage_census_rows_22` |
| 23 | `coverage_census_rows` L240 | `issuer == "alibaba"` → `!=` | `test_mut2_s2_selection_coverage_census_rows_23` |
| 25 | `coverage_census_rows` L242 | `split(...)[0]` → `[1]` | `test_mut2_s2_selection_coverage_census_rows_25` |
| 27 | `coverage_census_rows` L243 | `split(...)[1]` → `[2]` | `test_mut2_s2_selection_coverage_census_rows_27` |
| 28 | `coverage_census_rows` L249 | `return rows` → `None` | `test_mut2_s2_selection_coverage_census_rows_28` |

### s2_collapse (10)

| i | Site | Mutant | Killing test |
|---|---|---|---|
| 00 | `Episode.confounded` L58 | `return len>1` → `None` | `test_mut2_s2_collapse_Episode_confounded_00` |
| 01 | `Episode.confounded` L58 | `>` → `<` | `test_mut2_s2_collapse_Episode_confounded_01` |
| 02 | `Episode.confounded` L58 | `> 1` → `> 2` | `test_mut2_s2_collapse_Episode_confounded_02` |
| 05 | `step0_admit` L78 | `disposition == EXCLUDED_AND_LISTED` → `!=` | `test_mut2_s2_collapse_step0_admit_05` |
| 06 | `step0_admit` L78 | `and` → `or` | `test_mut2_s2_collapse_step0_admit_06` |
| 19 | `step3_bundle.union` L183 | `ra != rb` → `==` | `test_mut2_s2_collapse_step3_bundle_19` |
| 20 | `step3_bundle` L191 | `idxs[1:]` → `idxs[2:]` | `test_mut2_s2_collapse_step3_bundle_20` |
| 28 | `_inside` L264 | HK `is not None` → `is None` | `test_mut2_s2_collapse__inside_28` |
| 30 | `_inside` L265 | HK `return True` → `False` | `test_mut2_s2_collapse__inside_30` |
| 39 | `_matching_exclusion` L329 | `family ==` → `!=` | `test_mut2_s2_collapse__matching_exclusion_39` |

### s2_outcomes (17)

| i | Site | Mutant | Killing test |
|---|---|---|---|
| 00 | module L34 | `INFO_LEAK_STEP_TOLERANCE` 1e-6 → 1.001e-6 | `test_mut2_s2_outcomes_info_leak_scan_00` |
| 01 | module L35 | `TRAILING63_SESSIONS` 63 → 64 | `test_mut2_s2_outcomes_trailing63_direction_01` |
| 04 | `resolve_window` L64 | `s_us - days` → `+` | `test_mut2_s2_outcomes_resolve_window_04` |
| 05 | `resolve_window` L64 | `days=1` → `2` | `test_mut2_s2_outcomes_resolve_window_05` |
| 06 | `resolve_window` L65 | `return window` → `None` | `test_mut2_s2_outcomes_resolve_window_06` |
| 08 | `leg_return` L75 | formula → `return None` | `test_mut2_s2_outcomes_leg_return_08` |
| 09 | `leg_return` L75 | `/` → `*` | `test_mut2_s2_outcomes_leg_return_09` |
| 10 | `leg_return` L75 | `- 1.0` → `+ 1.0` | `test_mut2_s2_outcomes_leg_return_10` |
| 11 | `leg_return` L75 | `1.0` → `1.001` | `test_mut2_s2_outcomes_leg_return_11` |
| 12 | `episode_excess` L81 | `w is None` → `is not None` | `test_mut2_s2_outcomes_episode_excess_12` |
| 18 | `episode_excess` L94 | OK payload → `None` | `test_mut2_s2_outcomes_episode_excess_18` |
| 20 | `episode_excess` L99 | `subj - bench` → `+` | `test_mut2_s2_outcomes_episode_excess_20` |
| 25 | `trailing63_direction` L125 | zero-close `return 0` → `1` | `test_mut2_s2_outcomes_trailing63_direction_25` |
| 31 | `info_leak_scan` L134 | `is not None` → `is None` | `test_mut2_s2_outcomes_info_leak_scan_31` |
| 33 | `info_leak_scan` L139 | empty-TUNE `return out` → `None` | `test_mut2_s2_outcomes_info_leak_scan_33` |
| 34 | `info_leak_scan` L146 | `q / q.shift(1)` → `*` | `test_mut2_s2_outcomes_info_leak_scan_34` |
| 37 | `info_leak_scan` L149 | `offenders.index[0]` → `[1]` | `test_mut2_s2_outcomes_info_leak_scan_37` |

### stress_set (8)

| i | Site | Mutant | Killing test |
|---|---|---|---|
| 03 | `AuthorityMap.setdefault` L100 | `key not in self` → `in` | `test_mut2_stress_set_AuthorityMap_setdefault_03` |
| 05 | `AuthorityMap.__copy__` L108 | `return self.copy()` → `None` | `test_mut2_stress_set_AuthorityMap___copy___05` |
| 06 | `AuthorityMap.__or__` L113 | `return dup` → `None` | `test_mut2_stress_set_AuthorityMap___or___06` |
| 07 | `AuthorityMap.__ror__` L118 | `return dup` → `None` | `test_mut2_stress_set_AuthorityMap___ror___07` |
| 08 | `AuthorityMap.__ior__` L122 | `return self` → `None` | `test_mut2_stress_set_AuthorityMap___ior___08` |
| 30 | `_earliest_close_date` L635 | `or` → `and` | `test_mut2_stress_set__earliest_close_date_30` |
| 37 | `_parquet_path_for` L944 | `"%s.parquet" % ticker` → `//` | `test_mut2_stress_set__parquet_path_for_37` |
| 38 | `_load_closes_map` L963 | `return closes` → `None` | `test_mut2_stress_set__load_closes_map_38` |

## Equivalent arguments

One line each. These 21 sampled survivors are behaviour-preserving on
all inputs the operator can reach, or dead on this host.

| Module | i | Argument |
|---|---|---|
| `s2_stats` | 13 | `total = 0.0`; `0.0 * 1.001 == 0.0` |
| `s2_stats` | 15 | `range(k, n+1)` → `n+2`; `math.comb(n, n+1) == 0` |
| `s2_stats` | 25 | reject threshold `0.05` → `0.05005`; no `round(binom, 6)` lands in `(0.05, 0.05005]` for `n ≤ 120` |
| `s2_stats` | 27 | `if n == 0` → `n == 1`; `block_bootstrap_ci` already returns `None` for `< 2` unique dates |
| `s2_selection` | 12 | `counter.replace("hkd_", "", 1)` → `2`; every COUNTER key has a single `hkd_` substring |
| `s2_selection` | 24 | `cell.split(".", 1)` → `split(".", 2)`; EVENT_SOURCE_CELL values have exactly one dot |
| `s2_selection` | 26 | same maxsplit `1` → `2` on the counter split |
| `s2_collapse` | 10 | `_programme_key` is defined and never called |
| `s2_collapse` | 11 | same dead function, `return None` |
| `s2_collapse` | 21 | `FAMILY_PRECEDENCE.get(f, 0)` default `0` → `1`; documented IL families all have explicit keys |
| `stress_set` | 11–16 | `_minimal_yaml_load` / `_parse_scalar` / `_split_key_value` / `_strip_inline_comment`; PyYAML is importable so the fallback parser is unreached |
| `stress_set` | 17 | `except ImportError: return _minimal_yaml_load` → `None`; yaml imports |
| `stress_set` | 18 | `except: return False` → `return None`; both are falsy in `if not _is_defined_number` |
| `stress_set` | 19 | `_is_bad_close` `<= 0.0`; `0.0 * 1.001 == 0.0` |
| `stress_set` | 21 | deleting the duplicate-date `raise` still hits `d <= prev` strictly-sorted `raise` |
| `stress_set` | 24 | `_beta` `(s - ms)` → `(s + ms)` in the covariance sum; extra `2*ms*(b-mb)` sums to 0 |

## Survivors that map to known findings (MNZ-F2, IDR-F*)

| Finding | Sampled site | Why not a new test |
|---|---|---|
| **MNZ-F2** | `s2_outcomes.leg_return` L73 `if not e0 or not e1` → `and` | Same truthiness guard that scores NaN as OK and +inf fill as −1.0. Formula mutants on L75 (`return None`, `/`↔`*`, `−`↔`+`, `1.0`→`1.001`) are a different hole and were killed. |
| **IDR-F1..F4** | none of the 40 `stress_set` samples | Profile-loader missing-refusal lines were not in this stratified sample (the 40/60 function cap skipped several `check_profile` / `load_profiles` sites). No duplicate IDR test. |

## Timeout

`s2_collapse.step3_bundle.find` L176 `parent[x] != x` → `==` is an infinite
loop on any non-empty event list. Classified TIMEOUT (120 s). A killing
test that hangs is not added.

## Leftover sampled survivors (no dedicated MUT2 test)

Twelve `s2_outcomes` sites remain killable and were not claimed equivalent:
`episode_excess` abstention returns and `is None`/`or` on missing endpoints
(L82–L90), `round(..., 10)` → `11` (L98/L99), `trailing63` `seen += 1` → `2`,
KeyError `return 0` → `None`, formula `1.0` → `1.001`, and
`max_abs_step` round 12 → 13. Existing info-leak tests do not pin those
fields. They sit in GAPS.

## What this does NOT prove

- Completeness of the operator set (no unary `not` deletion, no `<=`/`<`
  boundary flip, no statement deletion beyond `if raise`).
- Every function in `stress_set` (40 of 60 functions sampled).
- Every candidate in `s2_collapse` / `s2_outcomes` (40 of 63 / 66).
- Behaviour of `s2_outcomes` against real Yahoo parquets (`data/` is
  absent; engines use synthetic frames).
- That `block_bootstrap_ci` internals are killed; only the S2 wrapper
  sites were mutated.
- Cross-host fallback of `_minimal_yaml_load` (PyYAML is present here).
- Anything about rank, gate, size, signal, escalation, or trade paths
  (this lane never writes those flags true).
- Identity minting (ids stay caller-supplied opaque strings).
