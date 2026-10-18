# Q07 post-freeze disclosures (finisher, after the outcome was known)

This file was written by the finishing stage **after** RUNS.log run 2 had produced the verdict. It is
**not** a PREREG amendment: it changes no analysis choice, no threshold, no input and no result. It
records facts an independent audit found missing from the record (audit verdict PASS_WITH_FIXES,
0 blockers, 0 majors, 5 minors). `PREREG.md` is unchanged (sha256 `6d3b1962…d4de`, matching FREEZE.log).

## 1. The evaluator changed after the freeze, before the first run

| | sha256 | bytes | when (UTC) |
|---|---|---|---|
| PREREG frozen | `6d3b19623e58f65b2036aefcd4b0dde8f74c68bdbdf0bad28c118ebd3bbed4de` | 12,273 | 2026-10-09T09:34:35Z (FREEZE.log) |
| evaluate.py as first witnessed | `746f…` (prefix only; recorded by the orchestration witness) | 16,044 | witnessed 09:36:20Z |
| evaluate.py as run (both runs) | `dc5c1f75cac465aaf1dd9f2d79bc4c5347dc8105edf50db0f5068928a90bc58a` | 16,302 | file mtime 09:37:52Z |
| RUNS.log first written | — | — | 09:38:20Z (file appearance per the audit) |

- **The diff cannot be reproduced.** No copy of the `746f…` file was retained in the staging tree or
  the Q07 scratch directory, so the 258-byte change and its reason are not recoverable. The author's
  record is silent on it.
- **What can be attested:** RUNS.log holds exactly two entries (run 1 `reproduce-baseline`, run 2
  `evaluate`), and both record `evaluate.py` = `dc5c…`. `append_run` logs refusals (exit 3) and caught
  exceptions (exit 1), so any evaluation under `746f…` that reached `main()` would have left a RUNS.log
  line. None exists.
- **What cannot be attested:** a run of `746f…` that crashed at import time (before `main()`) would leave
  no line. The witness timing (the edit landed 92 s after the first witness and 28 s before run 1) makes
  this unlikely but does not exclude it.
- **Why the verdict still stands:** PREREG does not pin the evaluator hash; it pins the analysis. The
  audit read `dc5c…` against PREREG §4–§9 and found the analysis conforms (trailing features, `t + h ≤ c`
  embargo, training-only smearing / C3 scale / interval quantiles, 126-session paired circular block
  bootstrap, Newey–West lag 42, decision rule). The KEEP rests on that conformance, not on the edit
  being harmless by assumption.
- **Process fix for future briefs:** pin the evaluator sha256 in PREREG (or FREEZE.log) at freeze time.

## 2. RUNS.log entries carry no timestamp

`append_run` writes command, exit code, inputs, outputs and note, but no UTC time. Adding one would
require a wall-clock read in evaluate.py and a re-run under a changed evaluator, which this finishing
stage judged worse than the defect. Ordering against the freeze rests on FREEZE.log's timestamp, the
orchestration witness and file mtimes (above). Future evaluators should stamp each entry.

## 3. Back-adjusted prices are not point-in-time

The Yahoo `close` column is dividend- and split-adjusted as of the vintage (`macro-main/data/yahoo`
@ cdab6268; PREREG §3 discloses this). Later corporate actions rescale earlier prices, so the input
levels are not what a forecaster saw on each date.

- A pure multiplicative rescale of all earlier prices leaves every log return unchanged except across
  the adjustment date.
- Measured on the same 13 frozen files (data-structure diagnostic, no forecasts or losses; command
  `python3.12 _fabric/Q07-scratch/adj_check.py` under the staging root, exit 0): no split-like day
  (|Δ log return| > 5%) differs between `close` and `close_price`; the largest single-day difference is
  2.9% (XLE), and the adjusted series' mean squared daily log return differs from the raw series' by
  −0.01% (XLC) to −0.82% (XLRE) of its level.
- That shift moves the target and every model's inputs together, and it is at least ~20 times smaller
  than the smallest point margin in the primary table (15.8% vs C2). This bounds its plausible effect;
  it does not prove the ranking would be identical on point-in-time prices. It is disclosed as a
  limitation, not claimed to be zero.

## 4. Two training-only claims had no test

REQUIREMENTS.md row 2 claimed that the C3 level factor and the interval quantiles use only matured
training targets, but no test perturbed post-cutoff targets for them. Added:

- `test_req2_c3_scale_uses_matured_training_targets_only`
- `test_req2_interval_quantiles_use_matured_training_targets_only`

Each multiplies every unmatured / evaluation-period target (`t > c − h`) by 7 and requires the
forecast segment at cutoff `c` to stay bit-identical, and doubles every matured target and requires the
segment to scale by exactly 2. A mutation check that replaces the embargo with `t ≤ c` makes both tests
fail. These are test-only additions: the module and evaluate.py are unchanged, so no re-run was
needed and the results files are the run-2 bytes.

## 5. Headline wording

VERDICT.md's headline said H beats every simple control "by at least 3%". The 3% bar is met by the
**point estimate**; against EWMA the relative-CI lower bound is 2.8% and the HAC t is 1.85. The
headline now reads **KEEP (weak vs EWMA)** and says so.
