# Q19 PREREG amendment, Addendum C (finisher pass, written before the reproducibility re-run)

Written Fri Oct  9 20:43:32 UTC 2026, after an independent audit (verdict PASS_WITH_FIXES:
0 blockers, 3 majors, 5 minors) and BEFORE the single re-run it describes. `PREREG.md`
(sha256 `dedbe342…`, FREEZE.log) is not edited. `PREREG_AMENDMENT.md` is restored to the
original bytes RUNS.log entry 2 hashed (`b306c8bc0d6485f216d0df43ee330005ca8ed7732cdb243966a8e1ee44a1ca25`). Addendum B now
lives in `PREREG_AMENDMENT_ADDENDUM_B.md`. All amendment-family hashes are recorded in
`AMENDMENT_SEAL.log`.

No new outcome has been read to write this addendum. The only outcome figures this
addendum knows of are the ones RUNS.log entry 2 already produced.

## C1 Module bytes (audit major 1)

The primary (entry 2) ran engine bytes `bd11dc00…ef52d`. Afterwards, verdict prose was
written into the module docstring (`7852c07d…`). The `bd11dc00` bytes were not preserved
and cannot be reconstructed exactly. The finisher removed all verdict text from the
module. The docstring now only points to `VERDICT.md`, so verdict writing can never move the
module hash again. No function body changed: the diff against `7852c07d` touches docstring
lines only.

## C2 Attrition label (audit minor; Addendum B item B1)

`write_attrition_csv` put the 26 undated pending units under split `TRAIN`. They are in
neither split. They are now labelled `UNDATED`. This is a reporting-only change.
`build_units`, the TRAIN/TEST date boundary, b, E, E_p, the bootstrap, LOTO and the
verdict rule are untouched. The units are NOT re-dated, because that would be the
repeated holdout evaluation PREREG section 17 forbids.

## C3 Evaluator provenance additions

`evaluate.py` now also hashes `PREREG_AMENDMENT_ADDENDUM_B.md` and
`PREREG_AMENDMENT_ADDENDUM_C.md` into RUNS.log inputs, and accepts `--purpose`, which is
recorded in the RUNS.log note. Neither touches computation.

## C4 The one re-run, and its purpose

The "Run discipline" clause allows a re-run only for a crash or a demonstrable
implementation defect, described here before it happens. There are two defects: the C2
mislabel, and the mismatch between the module bytes the primary used and the bytes shipped
(C1). The re-run has ONE purpose: reproducibility of the shipped code. It runs
`--mode primary` exactly once, under the shipped module, the shipped evaluator and the
same pinned data prefixes.

- The verdict-bearing result stays bound to RUNS.log entry 2. The re-run is not a second
  trial. It does not count as a new look at the holdout, and nothing is adopted from it.
- Pass condition: `results/primary.json` is byte-identical to entry 2's output
  (`d4ef29bf…`). `primary.json` embeds no input hashes, so identical bytes mean the shipped
  code reproduces the primary exactly.
- If any verdict-bearing number differs, that is reported as a DEFECT in VERDICT.md. The
  entry-2 numbers and verdict stand, and the difference is not adopted or tuned against.
- `results/attrition.csv` is expected to change in labels only (C2). Its per-class
  totals must match entry 2's file.

## C5 Eligibility gate and brief-level verdict (audit major 3)

The brief's input-eligibility rule reads: "Use a cohort only after its owner explicitly
admits this path-dependent question." No owner of the options signal-episode cohort
(`engine/options_signal_episode.py`, its ledgers under
`data/options_signal_episode/`) has admitted a barrier/first-passage question. The
empirical trial is therefore EXPLORATORY and outside the eligibility gate. Its
pre-registered outcome (REJECT under PREREG section 15) is disclosed as an exploratory
finding only. The brief-level empirical verdict is INSUFFICIENT_DATA: no admitted cohort
exists.

Blocked action: the owner of `engine/options_signal_episode.py` (the options
signal-episode session-outcome ledger) explicitly admits a path-dependent barrier
first-passage question for that cohort. No agentos workstream record names that owner,
so admission routes through the incumbent owner of that module in the Macro repository.
The pure reference module and its synthetic tests (requirements 1-6) do not depend on this
gate.

## C6 Amendment timing honesty (audit major 2)

The witness log cannot order the amendment before the primary run. RUNS.log entry 2 proves
only that the amendment bytes (A1-A13 and Run discipline, `b306c8bc…`) existed when the
run started. It does not prove they were written before any outcome was read. Also,
`evaluate.py`'s A5 code path (`37b160e5`) is the only witnessed form of that rule. The
amendment's own claim that it was written before the primary is the author's statement,
not a witnessed fact. `AMENDMENT_SEAL.log` is a post-hoc seal written on the finisher pass.
It does not establish earlier timing.

## C7 Baseline provenance (audit minor)

`results/baseline.json` (`6fc9ec37…`) was produced by `evaluate.py` `ea8e6f68…` (RUNS.log
entry 1), an earlier evaluator whose bytes were not preserved. It is not re-run (one re-run
only, C4). The baseline is a status-ruler census with no outcome values, and it feeds no
verdict.

## C8 Structural diagnostic

RUNS.log entry 3 cites `undated_diag.py` (`2a1687fe…`). Its exact bytes now ship in this
directory as `undated_diag.py`. It computes no barrier, state, E or bound.
