# MUT4B mutation sweep — `s1_manifest.py` / `s1_synth.py` — 2026-10-13

SNI-local DRAFT contract review. These modules consume caller-supplied
opaque identity strings (Stock Identity / Data OS) and never mint issuer
or security ids. HISTORICAL-DESCRIPTIVE only: `rank_authority`,
`gate_authority`, `size_authority`, `signal_authority`,
`escalation_authority` and `trade_authority` stay false. Fixtures in the
killing tests are synthetic. No production module was edited.

Harness (not committed): `~/lanes/scratch/mut4b/harness.py`. Seed
`random.Random(20261013)`. Each mutant applied in place, then original
bytes restored and sha256-checked before the next. After every mutant,
`git status --porcelain -- research/` was compared with the mutated
module path excluded; 0 TIMEOUT-UNSAFE writes to `runs/`.

## Summary

| item | count |
|---|---|
| generated (selected sites) | 45 |
| killed-before (existing importer suite) | 22 |
| survived-before (non-equivalent) | 22 |
| killed-after (new `test_mut4b_*`) | 22 |
| equivalent | 1 |
| timeout | 0 |
| score before | 22 / 44 = 50.0% |
| score after | 44 / 44 = 100% |
| new killing tests | 22 |

Score = killed / (generated − equivalent). Unmutated `s1_synth`
importer suite measured 28.76 s (> 20 s), so that module was capped at
15 mutants. Unmutated `s1_manifest` importer suite measured 1.40 s
(37 passed); cap 30. 0 xfails. 0 TIMEOUT-UNSAFE.

## Operator set and seed

Seed: `20261013`. Max 30 mutants per module (15 for `s1_synth` after
the 20 s rule), stratified by function (round-robin over
`sorted(function names)`, sites shuffled per function with the same
RNG).

Operators (AST, one site per mutant):

- comparison flip: `<`↔`>`, `<=`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: int `n`→`n+1`, float `x`→`x*1.001`, `True`↔`False`
- `return x` → `return None` (one non-`None` return per function)
- `and`↔`or`
- deletion of one `if ...: raise` guard (`pass`)

Identity float mutants (`x * 1.001 == x`) were dropped before sampling.
QF fence lines (below) were dropped before sampling.

Kill suite (tests that import the module; run with
`timeout 60 python3 -m pytest <tests> -x -q -p no:cacheprovider`):

- `s1_manifest`: `tests/test_sni_s1_manifest.py`,
  `tests/test_sni_quarantine_fence.py`, `tests/test_sni_s1_stats.py`,
  `tests/test_sni_mutation_stats_direction.py`
- `s1_synth`: `tests/test_sni_s1_manifest.py`,
  `tests/test_sni_s1_challenger.py`, `tests/test_sni_s1_decomposition.py`,
  `tests/test_sni_s1_cli.py`, `tests/test_sni_s1_ledger_order.py`,
  `tests/test_sni_s1_info_leak.py`, `tests/test_sni_s1_report_order.py`,
  `tests/test_sni_s1_v1_1_hardening.py`,
  `tests/test_sni_s1_seal_integrity.py`

`tests/test_sni_no_ticker_branches.py` names `s1_synth.py` as a scanned
path string and does not import the module; it was not in the kill
suite.

## Per-module table

| module | candidate sites | selected | killed-before | survived-before | equivalent | timeout | killed-after | score before → after |
|---|---|---|---|---|---|---|---|---|
| `s1_manifest.py` | 67 (75 raw − 8 QF) | 30 | 18 | 11 | 1 | 0 | 11 | 18/29 → 29/29 |
| `s1_synth.py` | 64 | 15 | 4 | 11 | 0 | 0 | 11 | 4/15 → 15/15 |
| total | 131 | 45 | 22 | 22 | 1 | 0 | 22 | 22/44 → 44/44 |

Selected-by-function (after QF drop and stratification):

| module | function | sites | selected |
|---|---|---|---|
| s1_manifest | `<module>` | 9 | 3 |
| s1_manifest | `build_rows` | 5 | 2 |
| s1_manifest | `canonical_line` | 4 | 2 |
| s1_manifest | `episode_key_for` | 1 | 1 |
| s1_manifest | `first_anchor` | 8 | 2 |
| s1_manifest | `first_session_strictly_after` | 2 | 2 |
| s1_manifest | `is_session_fn` | 2 | 2 |
| s1_manifest | `label_unit` | 5 | 2 |
| s1_manifest | `last_session_before` | 4 | 2 |
| s1_manifest | `manifest_bytes` | 1 | 1 |
| s1_manifest | `rolling_grid` | 8 | 2 |
| s1_manifest | `session_n_back` | 5 | 2 |
| s1_manifest | `session_n_forward` | 5 | 2 |
| s1_manifest | `session_n_forward_on_non_session` | 5 | 2 |
| s1_manifest | `split_digests` | 1 | 1 |
| s1_manifest | `time_split` | 2 | 2 |
| s1_synth | `<module>` | 3 | 3 |
| s1_synth | `_spec` | 1 | 1 |
| s1_synth | `sessions_hk` | 6 | 3 |
| s1_synth | `sessions_us` | 6 | 2 |
| s1_synth | `synth_frames` | 20 | 2 |
| s1_synth | `walk` | 6 | 2 |
| s1_synth | `write_synthetic_repo` | 22 | 2 |

## Surviving-mutant list with killing test name

All 22 non-equivalent survivors were re-applied against the named new
test and failed (KILLED-after).

### s1_manifest.py

| file:line | original → mutated | killing test |
|---|---|---|
| `s1_manifest.py:35` | `400` → `401` (`_MAX_WALK_DAYS`) | `test_mut4b_s1_manifest_module_1` |
| `s1_manifest.py:199` | `ensure_ascii=False` → `True` | `test_mut4b_s1_manifest_canonical_line_1` |
| `s1_manifest.py:93` | `return session_n_forward_on_non_session(...)` → `None` | `test_mut4b_s1_manifest_first_session_strictly_after_1` |
| `s1_manifest.py:93` | `n=1` → `n=2` | `test_mut4b_s1_manifest_first_session_strictly_after_2` |
| `s1_manifest.py:47` | delete `if market not in (MARKET_US, MARKET_HK): raise` | `test_mut4b_s1_manifest_is_session_fn_1` |
| `s1_manifest.py:54` | `d - timedelta(days=1)` → `d + timedelta(days=1)` | `test_mut4b_s1_manifest_last_session_before_1` |
| `s1_manifest.py:154` | `s is None or s > last_bar` → `and` | `test_mut4b_s1_manifest_rolling_grid_1` |
| `s1_manifest.py:155` | `return []` → `return None` | `test_mut4b_s1_manifest_rolling_grid_2` |
| `s1_manifest.py:87` | `if seen == n` → `if seen != n` | `test_mut4b_s1_manifest_session_n_forward_1` |
| `s1_manifest.py:104` | `if seen == n` → `if seen != n` | `test_mut4b_s1_manifest_session_n_forward_on_non_session_1` |
| `s1_manifest.py:105` | `return c` → `return None` | `test_mut4b_s1_manifest_session_n_forward_on_non_session_2` |

### s1_synth.py

| file:line | original → mutated | killing test |
|---|---|---|
| `s1_synth.py:15` | `parents[3]` → `parents[4]` | `test_mut4b_s1_synth_module_1` |
| `s1_synth.py:18` | `sys.path.insert(0, p)` → `insert(1, p)` | `test_mut4b_s1_synth_module_2` |
| `s1_synth.py:134` | `return build_spec()` → `return None` | `test_mut4b_s1_synth__spec_1` |
| `s1_synth.py:46` | default start year `2019` → `2020` | `test_mut4b_s1_synth_sessions_hk_1` |
| `s1_synth.py:46` | default start month `1` → `2` | `test_mut4b_s1_synth_sessions_hk_2` |
| `s1_synth.py:46` | default start day `2` → `3` | `test_mut4b_s1_synth_sessions_hk_3` |
| `s1_synth.py:37` | default start month `1` → `2` | `test_mut4b_s1_synth_sessions_us_1` |
| `s1_synth.py:37` | default start day `2` → `3` | `test_mut4b_s1_synth_sessions_us_2` |
| `s1_synth.py:73` | `3033.HK` walk seed `7` → `8` | `test_mut4b_s1_synth_synth_frames_1` |
| `s1_synth.py:55` | default `vol=0.01` → `0.01001` | `test_mut4b_s1_synth_walk_1` |
| `s1_synth.py:59` | `start * prod(exp(r))` → `/` | `test_mut4b_s1_synth_walk_2` |

## Equivalent arguments

`s1_manifest.py:117` `first_anchor`: `subject_dates[MIN_HISTORY_BARS - 1]`
→ `MIN_HISTORY_BARS - 2`. Starting the scan one subject bar earlier
cannot admit an anchor until `D(s)` already holds 252 bars, so the
first accepted session is unchanged. Classified EQUIVALENT; no killing
test.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
census points 1–3 sit in `s1_manifest.py` and were excluded before
sampling (8 candidate sites on those exact lines):

| QF # | file:line | dropped operators |
|---|---|---|
| 1 | `s1_manifest.py:26` (`TUNE_END = date(2026, 10, 1)`) | `2026`→`2027`, `10`→`11`, `1`→`2` |
| 2 | `s1_manifest.py:133` (`time_split`: `s < TUNE_END`) | `<`→`>` |
| 3 | `s1_manifest.py:144` (`label_unit` TUNE `coverage >= TUNE_END`) | `==`→`!=`, two `and`→`or`, `>=`→`<=` |

`s1_synth.py` has no QF census lines. 0 selected mutants fell on
excluded lines.

## What this does NOT prove

Mutation score is test strength against this operator set and this
30/15-per-module sample, not statistical validity of SNI residual
membership or synthetic fixtures. A killed mutant does not move any
acceptance-matrix row to DONE. The sweep does not claim completeness
over unselected sites (67+64 candidates, 45 applied). Existing
`session_n_forward` grid tests compare the builder to the same helper
and so missed the `==`→`!=` mutant. Nothing here feeds a ranker, gate,
sizer, signal, escalation, or trade path.
