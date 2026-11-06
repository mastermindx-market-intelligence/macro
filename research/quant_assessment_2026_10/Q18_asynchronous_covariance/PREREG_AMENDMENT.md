# Q18 — PREREG amendment A1 (audit fixes; reporting and input guards only)

Status: written BEFORE the reproducibility rerun it authorises and before any new
outcome was read. `PREREG.md` is unchanged.

* Frozen `PREREG.md` sha256: `1c9ee1ef6a71a5d4667f8de197b96f1d4bb2bc0c976151ae86411fc0e49d028c`
  (it matches `FREEZE.log` `PREREG_SHA256`).
* Code state before this amendment:
  * `engine/async_session_covariance.py` sha256 `4af5c1c0ea33c09252d51cbe15a007d7fb580d25cacdf5b7e3d24cd3611d4743`
  * `evaluate.py` sha256 `111365229adc750afbbd1de3c64f99c88db5b873013dfc72d195c5384ebfd148`
* Holdout outputs before this amendment:
  * `results/primary_results.json` sha256 `08c3049c5f8fbdea854b842682bf5897ab72ab7d2c4b0227933be440d2be9cb5`
  * `results/per_block.csv` sha256 `345ec0dc66ad30205bf4c2a651b3390f4a5589b06ca95127d687aa863b893bf3`

Author of this amendment: Claude Opus 5.5 (`claude-opus-5-5`), Q18 finisher seat. This
seat is separate from the author seat and the independent auditor.

## Reason

The independent audit returned PASS_WITH_FIXES (0 blockers, 1 major, 8 minors). The
major finding was that brief requirement 3 ("daily data never yields invented intraday
covariance precision") was not tested as a discriminating requirement.

One code path it found: `lag_aligned` checked only `lag < 0`. A float lag such as `0.5`,
a boolean or an array would silently be treated as a sub-day or vector lag
specification. That would let daily data appear to carry intraday lag precision.

## Changes (none touch the trial family)

1. **`engine/async_session_covariance.py`.**
   * `lag_aligned` now raises `TypeError` unless `lag` is a non-boolean integer (Python
     `int` or numpy integer). It still raises `ValueError` for negative values.
   * The module docstring no longer hard-codes the verdict numbers. It points to
     `VERDICT.md` instead and keeps the `RESEARCH REFERENCE — NOT WIRED` prefix.
   * The study calls only `lag=1` (an int), so neither change can affect an estimate.
2. **`evaluate.py`.** The `__main__` RUNS.log record also stores `script_sha256` (for
   evaluate.py) and `module_sha256` (for the engine module), as provenance. The
   computation path, the outputs and the verdict logic are unchanged.
3. **Tests.** Discriminating tests were added for brief requirements 1, 3, 5 and 6:
   * clock-class assertions;
   * integer-lag refusal;
   * no intraday or lag-search output keys;
   * no causal or lead labels;
   * honest-N counted in time blocks.

## Explicitly unchanged

The following are unchanged: pairs, inputs and their hashes, estimators E0 to E3, the
40-pair minimums, the winsor rule, the split, the 27 holdout quarters, the bars for H1
and H2, MBB (block 4, B = 5000, seed 18), Newey–West lag 3, and the verdict rules.

## Rerun

`evaluate.py` is rerun once, as a reproducibility check of the post-amendment code. The
study is deterministic: fixed seeds, the same inputs, and no estimate path changed. The
expected result is byte-identical `primary_results.json` and `per_block.csv`.

* **If the outputs differ,** the difference is reported in `VERDICT.md` as a code
  defect, and the earlier run stays the primary record.
* **If they match,** the verdict stands as recorded.

Both runs stay in `RUNS.log`. This is not a second holdout search: nothing is selected
from the rerun.

---

# Q18 — PREREG amendment A2 (reporting-only additions and process disclosure)

Status: appended BEFORE the A1 reproducibility rerun of `evaluate.py` was executed and
before any new outcome was read. `PREREG.md` is unchanged (sha256
`1c9ee1ef6a71a5d4667f8de197b96f1d4bb2bc0c976151ae86411fc0e49d028c`). A1 above is
unchanged. Code state at the time of writing:

* `engine/async_session_covariance.py` sha256
  `f25c9bf20b18c4a6ff6532214ab4454882540b46fa6cf4c63744decc3df356e5`; `evaluate.py` sha256
  `f5011c8df16a9522533f4fad6170e81202b4a65657c04a05e5cd02192e2631b4`.

Author: Claude Opus 5.5 (`claude-opus-5-5`), Q18 finisher seat (continuation).

## Reason

The independent audit's MINOR findings 1, 4, 5 and 6 ask for: the clock class of each
studied pair in a results artifact; the effective number of bootstrap blocks; a RUNS.log
note naming line 1 as the pre-freeze, training-only baseline; and a record of the
post-freeze smoke run. None of these may touch the trial family, so they are added as a
separate reporting-only artifact rather than as edits to the primary outputs. This keeps
the A1 rerun's byte-identity check meaningful.

## Additions (reporting only)

1. **New script `report_support.py`** writes `results/support_report.json` and appends its
   own RUNS.log record (script sha256, exit code, output sha256). It reads no market
   data. It computes:
   * `asc.classify_pair_clock` for every studied clock pairing (SSE vs NYSE, HKEX_INDEX
     vs NYSE, NYSE vs NYSE, SSE vs HKEX_INDEX) over every weekday of the frozen holdout
     period (2020Q1..2026Q3, from the frozen constants in `evaluate.py`). The class
     depends only on the declared clocks and the dates, not on prices.
   * The effective bootstrap block count: H1 `n_time_blocks` from the existing
     `results/primary_results.json` divided by the frozen MBB block length 4, plus the
     block length itself.
   It selects nothing and changes no estimate, bar or verdict rule.
2. **Process notes in `RUNS.log`** are appended as JSON records with `"kind": "note"`
   (never edits of earlier lines):
   * RUNS.log line 1 (sha256 of the line including its newline
     `c0c858c27a5506313ee10e9bd59207c336ec148e2f81ad991f6b4f60a95ec035`) is the
     pre-freeze baseline reproduction. It used training rows only (dates before
     2020-01-01) and is disclosed in PREREG §7.
   * The post-freeze smoke run: `_fabric/Q18-work/smoke_eval.py` (sha256
     `7a43d7a42ec7c0a906ffbfe69a2a51426bbfed45f92d2b015ed1e23a52a6f425`) imported
     `evaluate.py` and monkeypatched its module globals in memory (INPUTS pointed at
     truncated copies containing only rows before 2020-01-01, pseudo-holdout
     2015Q1..2019Q4, lowered minimums, scratch CSV path). The shipped `evaluate.py` file
     was not edited and its `__main__` block was not executed, so no RUNS.log record was
     written. No holdout row was read. Its scratch output is not shipped.

## Explicitly unchanged

Everything listed as unchanged in A1, plus `results/primary_results.json` and
`results/per_block.csv` field sets. The A1 rerun's byte-identity expectation stands.
