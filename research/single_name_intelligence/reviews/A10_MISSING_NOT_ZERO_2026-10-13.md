# A10 missing KPI is not zero or silently carried forward

SNI-local numeric-path evidence toward acceptance row A10. Draft contract
only: consumes owner-supplied closes and caller-supplied opaque identity
ids. Does not feed a ranker, gate, sizer, signal, escalation, or trade
path. Authority flags stay literal false. Fixtures are synthetic.

Pinned against BASE `d8e1d87e5436586c17ced147edab5e013bb2c069`. Tests:
`tests/test_sni_missing_not_zero.py`, `SEEDS = range(200)` (200 seeded
cases per property). Runner: Python 3.12.3.

## Summary

On the US stress set, a missing, non-finite, or non-positive close stays
in the series and sets the two touching simple returns to `None`. The
next good close does not bridge the gap. `_summary.n` is the count of
defined finite numbers (sample stdev, n-1). A rolling-beta or hist-vol
window that contains a missing value is skipped (`None`);
`_window_defined` is `all(_is_defined_number)`. `stress_table` names
calendar mismatches as `dropped_stock_dates` / `dropped_bench_dates` and
abstains with `DATE_JOIN_MISMATCH` when `join_policy` is None; `inner`
matches a hand-computed inner join.

S1 `closes_from_frame` drops NaN/None from the date-to-close map and
does not count the drop (MNZ-F1). `daily_log_returns` then omits that
date; it never emits 0.0 for it. `+inf` is kept as a valid positive
close and can emit `inf`/`-inf` log returns (MNZ-F3).

S2 `OutcomeEngine.leg_return` returns `None` on a missing index date
(KeyError) or a falsy 0.0 close. A NaN close is truthy, so
`episode_excess` scores `state=OK` with `subject_ret=nan`. An `+inf`
fill close scores `subject_ret=-1.0` (MNZ-F2). `test_mnz_07` is
`xfail(strict=True)` for that finding.

sni_inference refuses NaN/inf/None in `cluster_mean_ci` with
`ValueError("values must be finite real numbers")`. Count APIs
(`wilson_ci`, binomial, sign test) take ints and refuse a NaN `p0` or
NaN `k`. Empty input abstains with `ABSTAIN_NO_EPISODES` and `n_obs=0`.
A real 0.0 observation is counted.

Three source mutants (None eligible; `n=len(values)`; forward-fill)
were killed and reverted.

Row A10 stays PARTIAL: this is SNI-local evidence. The C3 KPI compiler
is not on main and is gated; the owner test does not exist here.

## Existing-coverage table

| Test file | What it already pins | Gap versus A10 |
|---|---|---|
| `tests/test_sni_us_stress.py` | `test_r1_02_gaps_never_bridged`: one NaN and one None in a 4-point dated series; touching returns `None`; next good pair computed; parquet NaN becomes `None`. `test_r1_03_nonfinite_nonpositive_closes`: spot nan/inf/neg/0 close series all `[None, None]`; one rolling-beta nan mix; `_summary` n=1 on mixed missing; one stress_table nan close stays finite. `test_r2_06_*`: calendar mismatch abstains `DATE_JOIN_MISMATCH` by default; `join_policy="inner"` emits and records dropped dates. | Spot cases, not 200-seed properties. Does not assert a missing return is never 0.0 or -1.0, never a silent n count, or never a zero-filled rolling window. |
| `tests/test_sni_s1_property.py` | `N_CASES=60`. `window_log_ret` is None when a date key is deleted or an endpoint is 0/negative. `daily_log_returns` breaks the chain on non-positive closes. `decompose_unit` abstains `ABSTAIN_MISSING_ENDPOINT` when coverage is deleted. Vintage series skips none/nan/nonpos without inventing steps. | Does not go through `InjectableStore` / `closes_from_frame`. Does not count silent NaN drops. Does not inject inf. |
| `tests/test_sni_s2_property.py` | Clock, split, collapse, selection, membership. Synthetic events. | No price series, no event-window return, no missing close. |
| `tests/test_sni_s2_abstain.py` | Abstention ladder, `sign_exact(0)==0`, no 0.5/50/50 tokens in pooling copy, plain-word null. | Does not put a missing close inside an S2 window. |
| `tests/test_sni_common_inference.py` | `cluster_mean_ci` raises on NaN/inf (`test_r1_01`). Bool/str refused. Empty input abstains. `p0=nan` raises. Wilson n=0 abstains. | Does not pin a NaN-as-0 counterfactual, does not table every public function, does not run 200 seeds on the missing class. |

## Per-function convention table

Observed on this BASE. "Missing input" is None / NaN / inf / non-positive
close (or NaN in a return array). Verdict is A10-local: never 0, never
forward-fill, never silent n, disclosed.

| function | missing input | output | disclosed? | verdict |
|---|---|---|---|---|
| `_is_defined_number` | None, non-numeric, NaN, inf | False | predicate | pass |
| `_is_defined_number` | 0.0 | True | 0 is a defined number | pass (0 is real) |
| `_is_bad_close` | None, NaN, inf, 0.0, negative | True | predicate | pass |
| `_close_or_none` | None, NaN, inf, unparsable | None | None | pass |
| `_close_or_none` | 0.0 | 0.0 | 0 kept; `_is_bad_close` later | pass |
| `_simple_return_values` / `simple_returns` | bad close at t | touching returns `None` (never NaN); slot kept; no bridge | None vs float | pass; no gap-span (documented) |
| `_window_defined` | any non-defined in seq | False; empty seq True (`all([])`) | predicate | pass; zeros `[0.0, 0.0]` are defined |
| `rolling_beta_residual` | hole in `[t-window, t]` or at t | `out[t] is None` (skip) | None slot | pass; not the 0-fill counterfactual |
| `hist_vol_normalize` | hole in trailing window or at t | `out[t] is None` | None slot | pass |
| `_summary` | None/NaN/inf in values | n = count of defined finites; mean/stdev on those; n=1 stdev None (sample n-1) | n only; no `n_missing` | pass on n; missing count not named |
| `_empty_summary` | no closes | n=0, mean None, `reason` | reason token | pass |
| `_dropped_return_dates` | extra return-end dates on one leg | those dates | dropped_* lists | pass; value-holes on a shared calendar are not listed |
| `_inner_join_returns` | dated returns | shared dates, including None returns | join length | pass |
| `stress_table` join_policy None | calendar mismatch | `DATE_JOIN_MISMATCH`, n=0, dropped_* named | reason + dropped lists | pass |
| `stress_table` join_policy `"inner"` | calendar mismatch | inner-join numbers = hand rolling-beta + hist-vol + `_summary`; dropped_* named; `join_policy="inner"` | yes | pass |
| `InjectableStore.frame` | NaN/inf/0/neg in close list | `float(v)` kept | access_log `('frame', path, cols)` | pass through |
| `InjectableStore.frame` | None in close list | `TypeError` (`float(None)`) | raise | refuse |
| `closes_from_frame` | None or NaN | date omitted from map; dates list unchanged | no drop count | MNZ-F1 |
| `closes_from_frame` | +inf, 0.0, negative | kept in map | silent keep | inf: MNZ-F3; 0/neg handled downstream |
| `daily_log_returns` | date missing or close `<=0` | date omitted; chain restarts (no span) | omission | pass never-0 |
| `daily_log_returns` | +inf close | `inf` / `-inf` log return; RuntimeWarning divide by zero | no abstain | MNZ-F3 |
| `window_log_ret` | missing / `<=0` endpoint | None | None | pass |
| `window_log_ret` | +inf endpoint | inf/-inf | no abstain | MNZ-F3 |
| `decompose_unit` | missing fill/coverage in map | `ABSTAIN_MISSING_ENDPOINT` | abstention token | pass (existing S1 property) |
| `OutcomeEngine.leg_return` | date absent (KeyError) | None | None | pass |
| `OutcomeEngine.leg_return` | 0.0 close (`not e0`) | None | None | pass |
| `OutcomeEngine.leg_return` | NaN close (truthy) | nan | scored | MNZ-F2 |
| `OutcomeEngine.leg_return` | +inf fill, finite coverage | -1.0 | scored as -100% | MNZ-F2 |
| `OutcomeEngine.episode_excess` | `leg_return` None | `ABSTAIN_MISSING_ENDPOINT` | state token | pass on KeyError/0.0 |
| `OutcomeEngine.episode_excess` | NaN/inf fill | `state=OK`, nan or -1.0 | not abstained | MNZ-F2 |
| `cluster_mean_ci` | NaN/inf/None in values | `ValueError("values must be finite real numbers")` | raise | pass (refuse; not 0) |
| `cluster_mean_ci` | empty lists | abstain `ABSTAIN_NO_EPISODES`, n_obs=0 | reason | pass |
| `cluster_mean_ci` | real 0.0 values | counted in n_obs | n_obs | pass |
| `wilson_ci` | n=0 | abstain `ABSTAIN_NO_EPISODES` | reason, n_obs=0 | pass |
| `wilson_ci` | k=NaN (float) | `ValueError` (not a strict int) | raise | pass |
| `binom_p_one_sided_greater` / `binom_p_two_sided` | p0=NaN | `ValueError` | raise | pass |
| `sign_test_two_sided` | pos=0, neg=0 | `ValueError` (unestimable) | raise | pass |
| `label_for` | non-abstained NaN CI | `ValueError("finite CI")` | raise | pass |

## Mutation proofs

Done in this worktree and reverted. `git status --porcelain` was empty
of production edits before commit. Mutant kill = the named test failed.

### m1 — `_is_bad_close` returns False for None

Patch: `if x is None: return False` at the top of `_is_bad_close`, so
None is eligible for `float(cur)/float(prev)-1`.

```
FAILED test_mnz_01_simple_returns_never_zero_fill
Failed: mutant kill: TypeError on missing close (seed=0, case='undated'):
float() argument must be a string or a real number, not 'NoneType'
FAILED test_mnz_02_no_forward_fill
Failed: mutant kill: TypeError on missing close (seed=0, case='hole=125 kind=zero n=202'):
float() argument must be a string or a real number, not 'NoneType'
2 failed in 0.66s
```

Kill: TypeError, caught by the tests and reported as `pytest.fail`
(mutant kill). Reverted; suite green.

### m2 — `_summary` sets `n = len(values)`

Patch: `n = len(values)` instead of `n = len(xs)`.

```
FAILED test_mnz_03_summary_n_excludes_missing
AssertionError: (0, 'n=217 injected=89'): n=217 want 128
1 failed in 0.74s
```

Kill: seed 0, 217 values with 89 injected None/NaN; mutant reports
n=217, defined count is 128. Reverted; suite green.

### m3 — `_simple_return_values` forward-fills missing closes

Patch: walk the series, replace a bad close with the previous good
close, then compute simple returns on the filled series.

```
FAILED test_mnz_02_no_forward_fill
AssertionError: (0, 'hole=125 kind=zero n=202'): defined returns 200 != adjacent good pairs 134
1 failed in 0.60s
```

Kill: seed 0. Forward-fill created 200 defined returns against 134
adjacent good pairs. Reverted; suite green.

## Findings

### MNZ-F1 — S1 NaN drop is silent

- Path: `InjectableStore.frame` -> `closes_from_frame` ->
  `daily_log_returns` / `window_log_ret`.
- Seed/case: every seed in `test_mnz_06`; representative seed=0, interior
  hole, kind=`nan`.
- Observation: NaN is omitted from the date-to-close map. The missing
  date never yields 0.0 (property holds). `access_log` records only
  `('frame', path, ('close',))`. There is no n_dropped, exclusion log,
  or manifest counter for the omitted row.
- A10: missing is not zero; it is also not disclosed.

### MNZ-F2 — S2 scores NaN as OK nan and +inf fill as -1.0

- Path: `OutcomeEngine.leg_return` / `episode_excess`.
- Seed/case: `test_mnz_07` (xfail), 200 seeds; prototype
  `s_us=2020-01-09`, h=5, NaN on fill ->
  `{'state': 'OK', 'subject_ret': nan, ...}`; +inf on fill ->
  `subject_ret=-1.0` (`100/inf - 1`).
- Cause: `if not e0 or not e1` treats 0.0 as missing and misses NaN
  (`bool(nan)` is True) and inf. `float(e1)/float(e0)-1` then runs.
- A10: a missing inf close becomes a -100% return; a NaN close is
  scored, not abstained. `test_mnz_07` is
  `xfail(strict=True, reason="MNZ-F2: ...")`.
- KeyError (date absent) and 0.0 close still return None and, through
  `episode_excess`, `ABSTAIN_MISSING_ENDPOINT`.

### MNZ-F3 — S1 treats +inf as a valid close

- Path: `daily_log_returns` (`c is None or c <= 0` only);
  `window_log_ret` (`a <= 0 or b <= 0` only).
- Seed/case: `test_mnz_06` seeds that inject `pinf`; RuntimeWarning
  `divide by zero encountered in log` at
  `s1_decomposition.py:86` and `:97`.
- Observation: +inf stays in the map. `log(inf/prev)` is inf;
  `log(next/inf)` is -inf. Not 0.0, and not an abstain. `-inf` is
  `<= 0` and does break the chain.

## What this does NOT prove

This is SNI-local numeric-path evidence on the sealed S1/S2 helpers and
the US stress set. The C3 KPI compiler is not on main and is gated.
Row A10 stays PARTIAL until the owner test exists.

It does not prove:

- parquet / Data OS production frames (only `InjectableStore` and
  synthetic dated lists);
- Company Event/Earnings, FIF, Capital Structure, Options, Research
  Vault, or qledger/Evaluation owners;
- that a missing KPI in a compiled scorecard cannot be zero or carried
  forward (that is the gated C3 test);
- causal "news impact" (A24) or a 50/50 default (A25) — those are out
  of scope here;
- HK/US issuer identity resolution (ids stay caller-supplied / null).

## Gaps

- `_summary` does not emit `n_missing`; callers who only see `n` cannot
  recover how many slots were dropped unless they still hold the input.
- `dropped_*_dates` name calendar mismatches of return-end dates, not
  dates whose close was None/NaN on an aligned calendar.
- `test_mnz_07` is an expected fail (MNZ-F2) until `leg_return` refuses
  non-finite closes the same way it refuses 0.0 / KeyError.
- Production S1/S2 code was not edited (lane law). Fixes for MNZ-F1/F2/F3
  belong to those owners.
- Sparse checkout: S1/S2 consumer modules and US stress profiles were
  added with `git sparse-checkout add` so the required pytest command
  could import them. No `data/` or `site/` writes.
- numpy/pandas used only where the module under test already imports
  them (S1 decomposition, S2 outcomes). Stress and inference properties
  are stdlib + `random.Random(seed)`.
