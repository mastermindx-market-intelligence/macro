# Pullback stage-1 deviation log (Grey Deer W3, prereg §12)

**Program:** `WS:GREY-DEER-RISK-INTELLIGENCE` / MAS-258 · **Operation:** `risk-radar-pullback-20261009`
· **Seat:** Fable principal, session `da1ad7ad` · **Prereg:** `PULLBACK_PREREGISTRATION_2026-10-11.md`
(blob `49a68b5e9c65`) · **Manifest:** v1.0.0 (blob `38925409555d`).

Prereg §12 allows a code defect found after outcomes to be fixed only if the fix changes no frozen
choice. The original output is kept, the fix is made, the run is repeated, and this log names the
defect, the fix and both results. One deviation was taken.

## Deviation 1 — `INC_LABEL_INDEX`

| Field | Value |
|---|---|
| Section affected | INC incumbent replay (prereg rung 2; own `CURRENT_VINTAGE` table, never a gate) |
| Defect | `run_inc` read the `date` of `native_forward_labels(...)` as a column (`drop_duplicates(subset="date")`). That function returns a date-indexed frame, so the call raised `KeyError: Index(['date'])`. The broad `except` then typed the code defect as `INC_SOURCE_UNAVAILABLE`, which misreports a bug as an absent source. |
| Found | Reading the frozen-run output: INC was blocked although the incumbent audit script is on main. |
| Fix | Commit `fbeff30d34ed`. New `native_event_on_dates` aligns native events on the index (first of any duplicate date, NaN where no complete window). Exception typing is split: import/OS/runtime errors stay `INC_SOURCE_UNAVAILABLE`, and anything else is `INC_REPLAY_ERROR`, so a future code defect cannot pass as an absent source. `--rerun-of` and `--rerun-defect` record the deviation inside the artifact and refuse to overwrite the original output directory. |
| Frozen choices changed | None. Sample, folds, horizons, thresholds, quantile levels, cost ratios, block length, power floor, configurations, trial budget and verdict words are untouched. |
| Regression tests | `tests/test_grey_deer_pullback_stage1.py`: `test_native_event_on_dates_aligns_index_labels` (uses the real `native_forward_labels` and pins the old idiom's `KeyError`), `test_native_event_on_dates_keeps_first_duplicate_and_handles_empty`, `test_run_inc_types_a_code_defect_apart_from_an_absent_source`, `test_rerun_of_refuses_to_overwrite_the_original_output`. 16 passed at `fbeff30d34ed`. |

## Both results

| | Original | Rerun |
|---|---|---|
| Commit | `1e8fa7185d55` (output kept at `dd67262e7ab8`) | `fbeff30d34ed` |
| Files | `PULLBACK_STAGE1_RESULTS_2026-10-11.{json,md}` | `pullback_stage1_r1/PULLBACK_STAGE1_RESULTS_2026-10-11.{json,md}` |
| Gates (12 claims) | all "underpowered/blocked claim" | identical |
| Episodes, comparison sets, folds, abstention, LOEO, negative control, census, sample, manifest, prereg, trial budget | — | byte-identical JSON sections |
| INC | `BLOCKED: INC_SOURCE_UNAVAILABLE` | populated, "accepted descriptive measurement" |
| `early_warning.hN.INC` | null | populated |
| Deviations | none | `CODE_DEFECT_RERUN` naming this defect |

A key-by-key JSON comparison found differences only in `run` (commit, script/test blobs, timestamp),
`inc`, `early_warning.*.INC` and `deviations`. No list in either artifact holds more than 40 entries;
both are aggregates only, with no row-level prices.

The trial ledger was not inflated. `trial_ledger_scope` deduplicates on family, n and reason, so the
rerun added no line to `data/trial_ledger.jsonl` (budget 69, family `grey_deer_pullback_v1`).

## Rerun INC table (descriptive only)

The incumbent replay scores the current incumbent against its own native forward label, so look-ahead
is disclosed (`look_ahead_disclosed: true`). It is never pooled, never a reference model and never a
gate. Its native label also differs slightly from the protocol label (events 11 / 35 / 113 against
11 / 36 / 117).

| h | covered | events | Brier | AUC | V@b |
|---|---|---|---|---|---|
| h5 | 1001/1001 | 11 | 0.0108829 | 0.890 | −0.0347 |
| h10 | 996/996 | 35 | 0.0353746 | 0.772 | 0.0533 |
| h21 | 985/985 | 113 | 0.102132 | 0.666 | 0.0861 |

Early warning against protocol episodes (alarm `p >= b_h`): cluster recall 1.00 at h5 (4 clusters),
0.75 at h10 (8), 0.89 at h21 (9). Median lead is 4.5, 6 and 16 sessions.

Reading: these numbers describe a `CURRENT_VINTAGE` incumbent, not a forecast record, and cannot
be compared with the M3/Q3 rows, which are walk-forward. They do not change any stage-1 verdict.

## What did not change

- The stage-1 conclusion stands. Every claim is underpowered (4–7 SPY episodes against a floor of
  10). M3 BSS is negative at every horizon, and the shifted negative control sits at or below zero.
- `RuntimeWarning: invalid value encountered in subtract` at the B1/B2-vs-B0 V-draw difference appears
  in both runs. It comes from `-inf − -inf` on draws where V is undefined. The next line overwrites
  those draws with `-inf` before any bound is taken, so it is not a defect and no deviation was taken.

## Reproduce

```bash
git show dd67262e7ab8 --stat
git diff dd67262e7ab8 fbeff30d34ed -- scripts/research/grey_deer_pullback_stage1.py
python -m pytest -q tests/test_grey_deer_pullback_stage1.py
python scripts/research/grey_deer_pullback_stage1.py --out-dir research/grey_deer/pullback_stage1_r1 \
  --rerun-of dd67262e7ab8 --rerun-defect "INC_LABEL_INDEX: ..."   # needs the Massive store hydrated
```
