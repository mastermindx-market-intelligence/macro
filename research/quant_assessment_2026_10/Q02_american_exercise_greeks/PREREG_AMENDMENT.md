# Q02 PREREG amendment log (append-only)

PREREG.md stays frozen at sha256 `9ae188f15db34125161d6ea7ea6642d038c253411a7ebdcbc37c5c6b963d3676`
(FREEZE.log). Following PREREG line 5 and section 11, every change after the freeze is recorded
here: the reason, the hashes, and when it was written, which is always before any new outcome is
read. Each amendment's sha256 is appended to `AMENDMENT_FREEZE.log` before the run it
authorizes. `evaluate.py` refuses to run when the sha256 of this file differs from the last hash
in that log. Its one-run rule applies to each (PREREG hash, amendment hash) pair, so each
amendment authorizes exactly one evaluation run.

## A1: read-path fix after run 1 FAILED (SOFR date stored as the pandas index)

### What happened

Run 1 failed with `exit_code: 1`, status `FAILED KeyError: 'date'`. Its RUNS.log block is kept
unchanged.

- Command: `/opt/homebrew/opt/python@3.12/bin/python3.12 .../evaluate.py`.
- `evaluate.py` sha256 for run 1: `4fc136ee08b147cb52d4aa8867a25f24afa40a6ca627adfbd62c36ad311ccd15`.

The failure came from `load_sofr`. That function read
`data/ofr/FNYR-SOFR-A.parquet` (sha256
`02dca610d9d4857a002beee07aef0a3f96af943131efba5d0861c0d5b1ddc620`) through
`pq.read_table(...).to_pandas()`. The file's pandas metadata declares
`index_columns: ["date"]`, so pandas turned `date` into the index and the column lookup
`df["date"]` raised `KeyError`.

### No outcome was read

- `load_sofr` runs after the inventory (stage 1), the code baseline, the B1 absence
  (stage 2) and E1, and before the section-9 census (stage 3), the absence scan, gate HG
  (stage 4) and E2.
- Run 1 therefore produced no attrition, selector, absence-scan, gate, E2 or summary output,
  and no HG or E2 outcome exists from it.
- Before failing, run 1 wrote three files. They are preserved byte-for-byte in
  `results/run1_failed/` with these hashes, identical to those in RUNS.log:
  - `inventory.json` `145a64c03a66cd4dba4c3eb264e6e24d0cc9616491500d655ea75ec41ce218f6`
  - `baseline.json` `af2ee8535f69b07166bf72724bcd5f1ce35699ee87a26a9262a50dca2de6372e`
  - `e1_numerical.json` `e07750bb6f35e31f95a4121d044e787715255bed196f9ec7e10eca418e665bff`
- A1 changes nothing in the code paths that produced those three files.

### Diagnosis disclosure

The failure was diagnosed from the traceback and from one probe that read schema metadata
only. The probe read parquet footer and pandas metadata, with no row values, for the SOFR file
and the 28 frozen chain files. Its findings:

- SOFR is the only input whose pandas metadata names a data column as its index.
- All 28 chains carry a `RangeIndex`, so their column reads are unaffected.
- All 28 chains share one column-type signature over the columns that are read.

### Changes authorized by A1 (evaluate.py only; no change to PREREG.md, the module or the test)

1. **SOFR read.** `load_sofr` now reads
   `pq.read_table(path, columns=["date", "sofr"]).to_pandas(ignore_metadata=True)`.
   `date` stays a column, and the values are byte-identical.
2. **Summary reason.** It is now data-driven: the zero-support stage names come from the
   marginal census counts, not from fixed text.
3. **Amendment-aware guard (stage 0).**
   - When this file exists, its sha256 must equal the last hash in `AMENDMENT_FREEZE.log`;
     otherwise the run is refused with exit 2.
   - If `AMENDMENT_FREEZE.log` exists without this file, the run is also refused with exit 2.
   - Every RUNS.log block now records `amendment_sha256` and
     `amendment_freeze_recorded_sha256`.
   - The one-run rule counts COMPLETED, BLOCKED and FAILED runs per (PREREG hash, amendment
     hash) pair. A legacy block without an amendment field counts as amendment `none`, so run 1
     still uses up the un-amended PREREG hash.
4. **Inputs.** The sha256 of `evaluate.py` itself is now logged as an input of every run.

Change 3 was exercised on a synthetic data root before this amendment was written. The checks
were:

- unfrozen amendment refused (exit 2);
- frozen amendment runs (exit 0);
- second run under the same amendment refused (exit 3);
- appended but unfrozen amendment refused (exit 2);
- re-frozen amendment runs (exit 0);
- freeze log without an amendment refused (exit 2);
- a legacy FAILED block counted under `none` and not under an amendment hash.

`evaluate.py` sha256 after A1: `80b0f449c8f7314d724b0e084521009dc5c422e352bf21aa2a5b982be4444553`.

### What A1 does not change

A1 changes no threshold, grid, tolerance, split, stage definition, gate criterion, bootstrap
parameter, decision rule, input list or input hash. Specifically, it leaves the following
unchanged:

- PREREG sections 3 and 7–13;
- HG (a) ≥ 10 dates per half, (b) ≥ 10 test underlyings, (c) both legs priced;
- the train and test split of 14 and 14 dates;
- the Brent bracket [0.005, 5.0] and the 90 % train-inversion floor;
- the moving-block bootstrap: block 5, B = 2000, seed 2002;
- KEEP ≥ 0.5 vol points with lower bound > 0, and REJECT if the upper bound < 0.5.

The module (`engine/options_american_exercise.py`, sha256 `ba222da9…7cc7fe1`) and the test
(`tests/test_options_american_exercise.py`, sha256 `439a0428…65d7d5`) are byte-identical to the
hashes logged in run 1.

### Authorization

A1 authorizes exactly one evaluation run of the amended `evaluate.py` against the unchanged
frozen inputs. Any further run needs a further amendment, A2, written here with its reason
before that run.

## A2: independent-audit fixes (PASS_WITH_FIXES; 0 blockers, 0 majors, 4 minors)

Written after the independent audit and before any further evaluation run. No run-3 output
existed or had been read when this text was written. Run 2 (the A1 run, `COMPLETED`) and every
earlier RUNS.log block stay unchanged.

### M1: vanna bump leaving SIGMA_BOUNDS (module + test change)

- **Defect.** `qualify_fd` used `h = min(VOL_BUMP, 0.5 * sigma)`. For sigma in [0.01, 0.02) or
  (4.99, 5.0], which `SIGMA_BOUNDS = (0.01, 5.0)` admits, a bumped solve at `sigma +/- h` fell
  outside SIGMA_BOUNDS and `fd_solve` raised `ValueError`. Below 0.02 the bump also shrank
  below the frozen PREREG section 7 value of +/- 0.01.
- **Fix.** The bump is always the frozen `VOL_BUMP = 0.01`. When either `sigma - 0.01` or
  `sigma + 0.01` leaves SIGMA_BOUNDS, vanna is `UNAVAILABLE` with reason
  `vol_bump_out_of_bounds` and the bumped solves are skipped. Price, delta, gamma and charm
  come from the base solve, as before. The edges are inclusive: sigma = 0.02 and sigma = 4.99
  still report vanna. Clamping was rejected because it would change the PREREG bump.
- **Tests added (73 -> 81).** req4: sigma 0.015 and 4.995, American and European, give an
  UNAVAILABLE vanna with no exception and a 0.01 bump (4 tests); sigma 0.02 and 4.99 still give
  a vanna (2 tests). req6: `price_contract` at sigma 0.015 and 4.995 prices without raising,
  and vanna fails closed (2 tests).
- **Effect on results.** Every E1 case uses sigma 0.20 or 0.25, where the old and new bumps are
  both 0.01. The E1, baseline, selector and gate numbers are therefore expected to be unchanged.
  Only `inventory.json`, which records the module and test sha256, is expected to differ.
- Hashes:
  - module `engine/options_american_exercise.py`: `ba222da95f4cbed0eb341004cb2294f89f647e683321be3f5c5b87ef50cc7fe1`
    -> `0b27f3230a06fc0d01b7313d9cff5025b73501efd6a82e554249793a1a0eb38a`;
  - test `tests/test_options_american_exercise.py`: `439a04287d54a0a818d8c934ab591dc33460dc4cda8375c08c08a5e91965d7d5`
    -> `df9819305fe6978a4257c09f39540b8f6b0e53790de40fb28c7312bd8845e1f6`.

### M2: A1's synthetic guard runs were not retained (disclosure + retained re-exercise)

The six synthetic-root runs that A1 cites (exits 2, 0, 3, 2, 0, 2) were not kept: no RUNS.log,
digest or artifact exists for them, and none can be produced after the fact. To close the gap,
the same guard decisions were re-exercised before this amendment was written, and the evidence
is kept:

- Harness: `guard_check/guard_check.py`, sha256
  `c1eb9495a501633a37aa44bdb10215676544e2fd4fce5fef3a301adaf9c51df1`.
- Command: `/opt/homebrew/bin/python3.12 .../guard_check/guard_check.py <scratch WORK_DIR> .../guard_check/transcript.json`. Exit 0; all 8 steps pass.
- Transcript: `guard_check/transcript.json`, sha256
  `9c2860cd979fe9be458edca6c1540a660d20d01493778677eef79f45008afa35`. It embeds the synthetic
  RUNS.log, sha256 `1a239e07ed09c1844f92094e6fd5794f7f25d40c6152a357778ef49db83038ce`.
- The harness ran against `evaluate.py` sha256 `80b0f449…4444553`, unchanged by A2.
- The real `RUNS.log`, `results/` and data root were never touched.
- The data root was an empty synthetic directory, so an admitted run stops at the stage-1
  inventory with exit 4. A1's admitted runs reached exit 0 instead.
- The second-run refusal (exit 3) was exercised by seeding one labelled synthetic COMPLETED
  block, because an empty data root cannot produce a guard-passing status.

### M3: run 1's evaluate.py hash

Run 1's RUNS.log block has no `evaluate.py` input line, because logging that hash was itself
an A1 change. Its sha256 is recorded in A1 above:
`4fc136ee08b147cb52d4aa8867a25f24afa40a6ca627adfbd62c36ad311ccd15`. RUNS.log stays unedited.

### M4: the inlined greeks.py formula must be re-pinned by hand

The test inlines the `engine/greeks.py` formula (sha256 `d471f5ed…ba8d9c`). CI hygiene forbids
the test from opening repository files, so the suite cannot detect drift in that file. A
comment in the test now says so. `evaluate.py`'s inventory still refuses with
`hash_mismatch engine/greeks.py` when the hash differs. If `engine/greeks.py` ever changes, the
inlined copy must be re-pinned by hand.

### What A2 does not change

A2 changes nothing in PREREG.md or `evaluate.py`. It leaves unchanged every threshold, grid
(N = 100 / 200 / 400), refinement tolerance, split, stage definition, gate criterion, bootstrap
parameter, decision rule, input list and input hash. The vanna definition stays the
fixed-grid +/- 0.01 sigma bump. Everything A1 lists as unchanged stays unchanged.

### Authorization

A2 authorizes exactly one evaluation run of the unchanged `evaluate.py` (sha256
`80b0f449c8f7314d724b0e084521009dc5c422e352bf21aa2a5b982be4444553`). It runs against the
unchanged frozen inputs with the A2 module and test above. Any further run needs a further
amendment, A3, written here with its reason before that run.
