# Q01 pre-registration amendment A2 (binds any future S4 run; not implemented by the current evaluate.py)

AMENDS_PREREG_SHA256=9e152194440979b96b9ee80658c844b699ce065bd9f6c25e2a610c03c568f60b
AMENDS_A1_SHA256=fd5bbe42ab0b7fd007b399bcbe6bb642531b524304d389ccc637180af56f9801

## Timing and status (disclosed)

* Written by the finisher after the independent audit (finding 7). This was after evaluation runs 1
  and 4 (`RUNS.log`). Both runs stopped at the S3 data gate with INSUFFICIENT_DATA (0 eligible
  sessions), so S4 never ran on market data. No market-data `D_s`, `L_bench` or `L_svi` exists, and
  none was read.
* The non-evidential synthetic S5 output (`synthetic_mechanics.json`, sha256
  `0ebff8d669ce60537510ad89c4f81d0a089b4af09bebda675da298ee519cd867`) had been read before this was
  written, and it motivated the change (`VERDICT.md` L6). It is seeded synthetic data with known
  truth, not a market outcome.
* No outcome of any kind is read after this file is written. `evaluate.py` is not re-run because of it.
* This file's sha256 is recorded in `FREEZE_A2.log` with a `date -u` timestamp. `PREREG.md`,
  `PREREG_AMENDMENT.md` and `FREEZE.log` are deliberately left unedited, because `evaluate.py` S0
  checks their recorded hashes.

## Effect

A2 binds the next owner. Before any S4 run on an eligible cohort, `evaluate.py` must:

1. implement A2.1–A2.4;
2. refuse at S0 unless this file's sha256 equals `AMENDMENT_A2_SHA256` in `FREEZE_A2.log`.

Both steps happen together with the PREREG §5 source-hash update that such a run already needs: a
later amendment, frozen before any data is read. An S4 result produced without A2 is invalid for KEEP.
A2 only adds conditions and reporting. It cannot turn any outcome into a KEEP that PREREG §8 alone
would reject.

## A2.1 — absolute out-of-band bar on `L_svi` (chord bias)

**Reason.** At a held-out interior node, the piecewise-linear benchmark is the chord between the two
neighbouring retained nodes. For a convex call-price curve the chord lies on or above the curve, so
`L_bench` carries an upward bias. That bias grows with curvature and node spacing and has nothing to do
with quote quality. `D_s = L_svi − L_bench` then rewards smoothness rather than in-band fidelity, and
the §8 non-inferiority margin (upper end of the CI of mean `D_s` ≤ 0.10) becomes easy for a smooth
parametric challenger. In the synthetic S5 run, `L_bench` was about 3.3–3.7 spread units while `L_svi`
was about 0.

**Change.** The §8 KEEP rule additionally requires that the upper end of the 95% block-bootstrap CI of
mean `L_svi(s)` is ≤ 0.10 spread units. The CI uses the same moving block bootstrap as §9: block 5,
B 2000, seed 101, chronological holdout. The existing `D_s` bar is retained. The two bars are joined
by AND, never OR.

## A2.2 — selection-free population for the absolute bar

**Reason.** By the §3 missing-value rule, `D_s` is defined only on sessions whose benchmark fit is
`ADMISSIBLE`. The paired comparison is therefore conditional on benchmark success, and a challenger
could look good on a subset that the benchmark selected.

**Change.**

* The A2.1 bar is computed on **all** holdout sessions that pass the §4 cohort contract, whatever the
  benchmark state.
* A held-out node in a slice that is not `ADMITTED` contributes 1.0 spread unit (the §3 rule,
  unchanged).
* A session where no SVI slice could be fitted contributes `L_svi = 1.0`.
* The count of holdout sessions by benchmark state is reported next to the paired N.

## A2.3 — reporting (does not affect the verdict)

* `L_bench` and `L_svi` are reported separately for the paired set: mean, median and the same
  bootstrap CI.
* **Node-retention sensitivity.** The holdout comparison is repeated with interior held-out indices
  `i % 4 == 1` instead of `i % 3 == 1`. It is a secondary diagnostic only, not a second trial, and it
  cannot change the verdict.
* A convex smoothing benchmark (for example a convex-spline LP) is **not** added as a competitor by A2.
  Adding one needs its own amendment, frozen before data is read, and counts as a new trial in the
  trial family.

## A2.4 — session counting at the S3 gate

**Reason.** The current S2 code sets `eligible_sessions` to 0 by construction when no source is
contract-complete. Otherwise it sets the field to `None`, and S3 then stops with exit 3 before the
value is used. This fails closed, but it does not count anything.

**Change.** The adapter amendment that admits a contract-complete source must:

* define how S2 counts eligible (session, root) snapshots from that source, using the §4 contract and
  honest N = distinct sessions;
* make S3 apply the §4 gate to that count.

The S3 stop (exit 3) on any contract-complete source without such an adapter is kept.

## Unchanged

Everything else stays as frozen in `PREREG.md` and A1, including:

* estimand, unit, clocks, cohort contract and data gate;
* hypotheses, competitors and the remaining effect bars;
* trial family (one primary trial), holdout design and chronological split;
* uncertainty method, falsifier and stop rule.
