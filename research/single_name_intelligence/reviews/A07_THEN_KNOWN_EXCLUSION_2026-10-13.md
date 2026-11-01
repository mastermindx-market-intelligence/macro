# A07 then-known exclusion — 2026-10-13

SNI-local DRAFT contract review. This lane attacks existing then-known /
information-leak guards with seeded property tests and mutation proofs. It
does not build a then-known compiler. Identity ids are caller-supplied
opaque strings owned by Stock Identity / Data OS; this lane never mints
them. rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay literal false. Fixtures are
synthetic. Residual and stress statistics are descriptive.

## Summary

Acceptance row A07 ("Post-cutoff facts cannot enter a then-known view") is
backed here by `tests/test_sni_a07_then_known_exclusion.py` against three
existing guards: S1 `vintage_series` / `detect`, S2 `OutcomeEngine.info_leak_scan`,
and US-stress `_ticker_then_known_violation` / `_bench_then_known_violation` /
`stress_table`. Each property test draws at least 200 cases from
`random.Random(seed)` with `SEEDS = range(200)`. Failures print `seed=` and
`case=`.

S1 `detect` refuses a step strictly before the earliest TUNE anchor or
strictly after `last_bar`, and flags a step on either endpoint. Unusable
raw columns yield `VINTAGE_UNVERIFIABLE` and `detect` returns None. NaN /
None rows between two vintages leave the step attributed to the first
usable date after the gap.

S2 `info_leak_scan`, driven through the same in-memory `_SyntheticLoader`
idiom as `tests/test_sni_s2_info_leak.py`, reports a strictly post-anchor
step and a step on the last bar, and stays silent for a pre-anchor step
and for an empty window (anchor after the last session). A step dated
exactly on `first_tune_anchor` is dropped: the scan filters `q` to
`index >= anchor` before differencing, so the first comparison has no
pre-anchor predecessor. That is finding **F-A07-01** (strict xfail,
seed=0 case=on_anchor).

US-stress ticker/listing `valid_from` strictly later than the earliest
close date abstains every benchmark (`TICKER_NOT_THEN_KNOWN`). Equality
of earliest close and `valid_from` is not a violation. A `sector_etf`
entry abstains only the matching benchmark value. Injecting a post-cutoff
`then_known` fact into a deepcopy of a committed Mag-7 profile abstains
`stress_table`; the committed YAML files stay byte-identical.

The row stays PARTIAL: this is SNI-local guard evidence, and S2 currently
lets a vintage step on the cutoff date through.

## Existing-coverage table

| test file | what it pins |
|---|---|
| `tests/test_sni_s1_info_leak.py` | End-to-end S1 pipeline: one synthetic BABA step inside TUNE writes ledger + `LANE_MANIFEST` retirements for P01/P03; no-step path writes none; HK series stay `VINTAGE_UNVERIFIABLE` and are not retired; TRAIN is never retired. `test_predicate_details` is one 4-row hand example (step 2024-06-13 in a wide window; later anchor returns None; all-None raw column is unverifiable). |
| `tests/test_sni_s2_info_leak.py` | One 30-day synthetic BABA jump at bar 10 with anchor 2026-06-05: `info_leak_scan` leak True and `maybe_log_retirement` writes a TUNE holdout_retired row. No-jump path does not retire. Empty TUNE (`tune_anchor is None`) is `EMPTY — retirement not applicable`. HK / TRAIN pins are string constants in `s2_seal`, not a scan. |
| `tests/test_sni_us_stress_then_known.py` | Committed Mag-7 profiles load and `check_profiles`. Verified `then_known` entries need a git-resolvable `path@sha` evidence pointer and must not carry `contradiction`. A deepcopy with `verified: true` and no evidence is reported. Does not call `_ticker_then_known_violation`, `_bench_then_known_violation`, or `stress_table` abstention. |
| `tests/test_sni_s1_property.py` | 60 seeded cases: clean q has no steps; above-tolerance persistent jump is detected; below-tolerance is not; `detect` is None when the window starts after the step or ends before it; unverifiable / single-row series; inserting one invalid price into a constant-q series does not invent a step. Does not walk 0–4 random steps, does not pin inclusive cutoff / last_bar / empty-window edges, and does not put a gap between two different vintages. |
| `tests/test_sni_s2_property.py` | Clock-law, collapse, splits, and selection properties. Does not call `info_leak_scan`. |

Missing before this lane: ≥200 seeded cases at cutoff−1 / cutoff / cutoff+1 / last bar / empty window; first_offending_date and count_of_steps_in_window across several planted steps; NaN rows between two vintages; S2 scan at those same edges; ticker/listing and sector_etf `valid_from` vs earliest close; post-cutoff injection into a committed profile; mutation proofs that a weakened guard fails the new tests.

## New properties

| test | property | cases generated |
|---|---|---|
| `test_a07_01_s1_boundary` | `detect` is non-None iff at least one vintage step date `d` satisfies `anchor <= d <= last_bar`; `first_offending_date` is the earliest such `d` in step order; `count_of_steps_in_window` equals that count. Per seed: random 30–300 business-day calendar with 0–4 steps, plus explicit on-anchor (flagged), previous session (not flagged), on last_bar (flagged), after last_bar (not flagged), empty window `last_bar < anchor` (not flagged). | 200 seeds × 6 = 1200 |
| `test_a07_02_s1_unverifiable_never_retires_but_is_disclosed` | All-None / NaN / `close_price <= 0` / fewer than two usable rows: `vintage_series` state is `VINTAGE_UNVERIFIABLE`, steps `[]`, `detect` returns None. The public disclosure of that state is the `vintage_series` return value (and its docstring). | 200 |
| `test_a07_03_s1_nan_rows_cannot_hide_a_step` | A gap of None/NaN/`close_price <= 0` rows between two distinct q vintages leaves exactly one step, dated at the first usable session after the gap. | 200 |
| `test_a07_04_s2_scan_boundary` | Through `_SyntheticLoader` + `OutcomeEngine`: a step on the previous session is not reported; a step strictly after the anchor is reported with that date; a step on the last bar is reported; an anchor after the last session is an empty scan (`leak` False). | 200 seeds × 4 = 800 |
| `test_a07_04_s2_scan_on_anchor_inclusive` | S1-equivalent: a step dated exactly on `first_tune_anchor` is reported. | 1 (seed=0 case=on_anchor); strict xfail F-A07-01 |
| `test_a07_05_us_stress_ticker_then_known` | `_ticker_then_known_violation` returns the max ticker/listing `valid_from` strictly later than the earliest close, else None. `valid_from` None or `""` never trigger. `share_class` is ignored. `stress_table` abstains every benchmark with `TICKER_NOT_THEN_KNOWN` iff a violation exists. Earliest close == `valid_from` is not a violation. | 200 seeds × 2 = 400 |
| `test_a07_06_us_stress_bench_then_known` | Matching `sector_etf` value with `valid_from` after the earliest bench close abstains only that benchmark (`BENCH_NOT_THEN_KNOWN`). A different value (`OTHER_ETF`) abstains none. None / `""` / equality / earlier `valid_from` never trigger. | 200 seeds × 2 = 400, plus four vf pins per seed |
| `test_a07_07_post_cutoff_fact_injection` | Deepcopy of a committed Mag-7 profile; inject ticker/listing `valid_from` = earliest synthetic close + 1 day. Control deepcopy (no injection) has no ticker violation. `stress_table` abstains all benchmarks with `TICKER_NOT_THEN_KNOWN`. Profile YAML bytes stay identical. | 200 |

Python 3.12.3, `python3 -m pytest tests/test_sni_a07_then_known_exclusion.py -q -p no:cacheprovider -rs`: 7 passed, 1 xfailed, 0 failed.

## Boundary semantics found

Quoted from the code at pin `d8e1d87e5436586c17ced147edab5e013bb2c069`.

**S1 `detect` — inclusive on both ends.**

```
offending = [(d, s) for d, s in steps if earliest_tune_anchor <= d <= last_bar]
```

A step on the earliest TUNE anchor is an offence. A step on `last_bar` is an
offence. A step on the previous session, or after `last_bar`, is not. An
empty window (`last_bar < earliest_tune_anchor`) has no offending step.

**S1 `vintage_series` — skip then attribute to the later usable date.**

```
if c is None or cp is None or cp != cp or c != c or cp <= 0:
    continue
...
steps = [(dOK[i], abs(q[i] / q[i - 1] - 1.0))
         for i in range(1, len(q))
         if abs(q[i] / q[i - 1] - 1.0) > STEP_TOLERANCE]
```

Unusable rows are dropped from `dOK`. The step date is `dOK[i]`, the first
usable date after the gap. Fewer than two usable rows returns
`([], "VINTAGE_UNVERIFIABLE")`. `detect` returns None when `state != "OK"`.

**S2 `info_leak_scan` — inclusive filter on the level, exclusive on the first difference; no independent last_bar cut.**

```
lo = pd.Timestamp(first_tune_anchor)
...
q = q[q.index >= lo]
steps = (q / q.shift(1) - 1.0).abs().dropna()
offenders = steps[steps > INFO_LEAK_STEP_TOLERANCE]
```

`q.index >= lo` keeps the bar on the anchor. `q.shift(1)` at that first
kept bar is NaN and is dropped, so a vintage change whose later date is
exactly the anchor is not an offender. A change whose later date is
strictly after the anchor still has its predecessor in the filtered
series (when anchors and step dates are members of the same sorted
session calendar) and is reported. `last_bar` in the scan output is
`max(self.nyse_sessions)`; the scan does not take a separate upper bound.

**US-stress ticker/listing — strict `<` on the earliest close.**

```
if vf is not None and earliest < vf:
    violated.append(vf)
...
return max(violated)
```

`_valid_from_of` returns None for `valid_from is None` or `valid_from == ""`.
Earliest close == `valid_from` is not a violation because the comparison
is `<`. The docstring of `stress_table` says a stock window that starts
*before* ticker or listing `valid_from` abstains all benchmarks
(`TICKER_NOT_THEN_KNOWN`). Equality means the window does not start
before `valid_from`, so the window is treated as then-known. That matches
the code and is the pin test 05 attacks.

**US-stress sector_etf — value must match the benchmark under test.**

```
if entry.get("field") != _THEN_KNOWN_BENCH_FIELD:
    continue
if entry.get("value") != bench_name:
    continue
if vf is not None and earliest < vf:
    violated.append(vf)
```

A `sector_etf` fact for XLK does not abstain SPY or QQQ. Same `<`
equality rule as ticker.

## Mutation proofs

Applied in this worktree, then reverted with `git checkout --` on the
touched production file. `git status --porcelain` was empty of production
edits before commit.

| mutant | expected | observed |
|---|---|---|
| m1: `s1_infoleak.detect` `earliest_tune_anchor <= d` changed to `< d` | `test_a07_01_s1_boundary` fails | FAIL `test_a07_01_s1_boundary` — `AssertionError: seed=0 case=on_anchor` (`hit is None` for a step on the anchor). Reverted; subsequent full file run 7 passed, 1 xfailed. |
| m2: `stress_set._ticker_then_known_violation` `earliest < vf` changed to `earliest <= vf` | `test_a07_05_us_stress_ticker_then_known` fails | FAIL `test_a07_05_us_stress_ticker_then_known` — `AssertionError: seed=0 case=equality` (got `'2021-02-16'` for earliest == valid_from). Reverted. |
| m3: `stress_set._bench_then_known_violation` deleted `if entry.get("value") != bench_name: continue` | `test_a07_06_us_stress_bench_then_known` fails | FAIL `test_a07_06_us_stress_bench_then_known` — `AssertionError: seed=0 case=match_xlk` (XLK `valid_from` also flagged SPY). Reverted. |

After all three reverts: `python3 -m pytest tests/test_sni_a07_then_known_exclusion.py -q -p no:cacheprovider -rs` → `7 passed, 1 xfailed in 2.21s`. Existing
`tests/test_sni_s1_info_leak.py tests/test_sni_s2_info_leak.py tests/test_sni_us_stress_then_known.py` → 13 passed.

## Findings

| id | seed / case | one line |
|---|---|---|
| F-A07-01 | seed=0 case=on_anchor | S2 `info_leak_scan` filters `q` to `index >= first_tune_anchor` before differencing, so a vintage step dated exactly on the earliest TUNE anchor is not reported (`leak` False). |

No S1 or US-stress property in this file failed against current code. The
S2 on-anchor miss is the one post-cutoff-adjacent fact the existing S2
guard lets through. A pre-anchor S2 step stays silent; a strictly later
S2 step is reported.

## What this does NOT prove

This is SNI-local guard evidence only. The owner then-known compiler
(row A07's named owner task) is not built here, and the row stays PARTIAL
until that owner test exists.

These tests do not compile a then-known view of prices, events, or
identity. They do not bind Stock Identity, Data OS, Company Event/Earnings,
FIF, Capital Structure, Options, Research Vault, or qledger/Evaluation.
They do not show that a full S1/S2 pipeline run on pinned market parquet
refuses every post-cutoff fact. They do not show that S2's `last_bar`
upper bound is independently enforced, because the scan's last bar is
always the last loaded session. They do not claim validation, forecast
skill, or any authority flag.

## Gaps

- `detect()` returns None both for "no leak" and for `VINTAGE_UNVERIFIABLE`.
  The unverifiable state is disclosed by `vintage_series`'s state string.
  Pipeline `LANE_MANIFEST.vintage_states` is already pinned in
  `tests/test_sni_s1_info_leak.py` and is not re-run here.
- S2 has no exported pure-function predicate; the scan is the method on
  `OutcomeEngine`. Construction used the existing synthetic loader, not a
  pinned historical git ref.
- S2 cannot host a date after `last_bar` inside the loaded series;
  "after last_bar" is checked as an empty window (anchor after the last
  session) plus the tautology that reported offender dates are inside the
  series.
- `first_offending_date` in S1 is the first in-window step in input order.
  Calendars in these tests are sorted, so that is also the earliest date.
- Committed META/GOOGL/TSLA profiles already carry non-null ticker or
  listing `valid_from`. Test 07 starts synthetic closes in 2024 so the
  injected fact is the sole ticker/listing violation; it does not replay
  those names' historical listing dates.
- pandas is required to construct `OutcomeEngine`. It was present
  (3.0.6) on this host. No `pip` install was used.
