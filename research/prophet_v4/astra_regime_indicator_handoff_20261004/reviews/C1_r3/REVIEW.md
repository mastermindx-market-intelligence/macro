# C1 ROUND 3 — independent read-only review

## STATUS

PASS (review completed; all listed re-checks were run)

## RESULT

**Recommended ruling: REQUEST_REPAIR**

Round 3 closed the round-2 include-t suite-survival hole (G1 Test A + `compute_cuts` on the pipeline path), rebuilt the E6(b) block-permutation null on the spec 6,942-session panel (G2), rescaled the positive-control drift and confirmed median lag-21 **+0.2533** (G3 numbers), and left `rotation_state_daily.parquet` byte-identical to round 2 (`sha256 9361dbf08018f0c23bc6e9b29fa014bc42429ed3289d359adf7a16f52be3e2dd`). The frozen rotation / agreement / contingency numbers are unchanged. CALIBRATED_FAIL holds under the lane null, the spec null, and the round-2 full-calendar null.

It does not close every specified re-check. G1 Test B is not implemented as specified and does not fail under the include-t mutant. G5’s specified `p95_lag21 = -0.5` tamper still passes. G3 never asserts `std(drifts)==cs_std` in a test and never discloses that `idio_std` equals `cs_std` to 4 dp.

### Per-item verdicts

| Item | Verdict | File:line |
|---|---|---|
| G2 null | **FIXED** | `code/run.py:623-660` (builder); description `run.py:709-714` / `result.json` `calibrated_control.null` |
| G1 leak tests | **PARTIAL** | Test A `code/test_C1.py:237-278`; `compute_cuts` `code/run.py:100-116` called at `:293` and `:331`; Test B gap `code/test_C1.py:343-392` |
| G3 positive control | **PARTIAL** | rescale `code/run.py:625-630`; idio `code/run.py:545-548`; panel trim `:613-621`; iid disclosure `RESULT.md:51`; missing pytest; missing 4-dp deviation `run.py:1020-1030` |
| G4 assertions | **FIXED** | windows `code/test_C1.py:483-497`; era κ `:539-558`; contingency `:570-591` |
| G5 calibrated_control test | **PARTIAL** | `code/test_C1.py:601-626` (status tamper fails; p95 tamper does not) |
| G6 ≤0.0003 vs 1e-4 wording | **FIXED** | `RESULT.md:122`; `result.json` `deviations[0]`; `code/run.py:1007-1015` |
| G7 hashes / wall-clock | **FIXED** | `code/run_all.py:58-64,198-229`; `result.json:185-187` (`tests_pass/skip/fail` only) |
| G8 ≈0.23 / unrendered f-string | **FIXED** | `RESULT.md:48-49` (rendered **+0.2533**; uncalibration attributed to the positive control); no `{pos['median_lag21']:+.4f}` in `RESULT.md` |
| Frozen table | **FIXED** | `rotation_state_daily.parquet` byte-identical to round-2 copy; agreement/controls/contingency leaves unchanged |

### Numbered defects (each with the re-check that closes it)

1. **G1 Test B is not the specified test and has no power against the include-t mutant.** `test_pipeline_cut_unchanged_when_v_prior_only` (`test_C1.py:343-392`) documents `v[t0]=+1e6` and “cut at t0+1 changes”, but the body perturbs XLK close ×1.5, never asserts t0+1, and **passed** under `compute_cuts` → `tercile_cuts(v_arr, min(i+1, n))`. **Re-check:** on a 1,100-session synthetic panel, set the pipeline’s unshifted V at one `t0≥800` to `+1e6`, re-run the same `compute_cuts` / sidecar path, assert cut(t0) identical and cut(t0+1) different; apply the include-t mutant to a scratch copy of `run.py:113` and show this named test FAIL.

2. **G3 required pytest for `std(drifts, ddof=0)==cs_std` is absent.** Rescale exists at `run.py:627-630` (`assert sd > 0` only). **Re-check:** a pytest asserts `abs(np.std(drifts, ddof=0) - cs_std) < 1e-12` (or equivalent); deleting the rescale line makes that named test FAIL.

3. **G3 4-dp equality of `idio_std` and `cs_std` is not disclosed as a deviation.** Reported values are `cs_std_median=0.030204` and `idio_std_median=0.030158` (`result.json` `calibrated_control.scales`). Rounded to 4 dp both are `0.0302`. The fallback at `run.py:1023` compares the 6-dp rounded floats for exact equality, so no deviation is emitted. **Re-check:** `RESULT.md` and `result.json` `deviations` contain the specified 4-dp disclosure.

4. **G5 specified tamper `null.p95_lag21 = -0.5` does not fail.** `test_calibrated_control_recompute` only re-evaluates the AND-rule from stored numbers. Observed `-0.0404 >= 0.5 × 0.2533 = +0.1267` is already false, so flipping p95 cannot change `CALIBRATED_FAIL`. Tamper `calibrated_status=PASS` does fail. **Re-check:** both packet tampers (`calibrated_status=PASS` **and** `p95_lag21=-0.5`) fail a named test — e.g. also assert stored `p95_lag21` against a frozen/recomputed null p95 at 1e-4.

## EVIDENCE

Workspace: `/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/astra-ceo-handoff-4a36a0`. Scratch: this directory. Lane host head recorded in `result.json`: `052e02d085b01f29baf499357e224c836d8eb224`. Vintage inputs taken from round-2 `fakerepo/` (byte-identical to `hashes.txt` `data/*` lines). Checkout `data/yahoo/*.parquet` and `data/fred/DFII10.parquet` are newer than that head, as the packet warned.

### Frozen parquet

```
shasum -a 256 <lane>/rotation_state_daily.parquet
9361dbf08018f0c23bc6e9b29fa014bc42429ed3289d359adf7a16f52be3e2dd

shasum -a 256 <results_prev>/C1_r2/rotation_state_daily.parquet
9361dbf08018f0c23bc6e9b29fa014bc42429ed3289d359adf7a16f52be3e2dd

cmp: BYTE_IDENTICAL rotation_state_daily.parquet

sidecar rotation_cuts_daily.parquet
484492539ae42cb3055416c12f144f93f748549bf21e4cf3de2f1e1eb6a002f8
```

### G2 — null builder vs spec

Spec: observed r21 panel + availability mask; **one** `rng.permutation` of sector identities per **non-overlapping** 21-session block, applied to **every row** of that block (r21 and availability jointly); 200 panels; `np.random.default_rng(20261004)`.

Lane `run.py:643-660`:

```python
for start in range(0, n_sessions, LAG):          # non-overlapping 21-session blocks
    end = min(start + LAG, n_sessions)
    perm = rng.permutation(n_sectors)            # ONE permutation per block
    r21_perm[start:end] = r21_perm[start:end][:, perm]
    avail_perm[start:end] = avail_perm[start:end][:, perm]
```

Panel is trimmed to the exported 6,942 sessions from 1999-02-25 (`run.py:615-621`). `block_len` / per-row `rng.shuffle` are gone.

**How it differs from the spec, if at all:** the **same** `default_rng(20261004)` is created at `run.py:623` and first consumed by 200 positive-control `rng.normal(0, idio_std, (6942, 11))` draws (`:633-641`) **before** any null permutation. Not per-row, not overlapping, not a permutation of the time series. `fillna(0)` then `DataFrame.where(avail)` is equivalent to permuting NaNs given the joint mask.

Rebuild (vintage fakerepo, seed 20261004, 200 panels), observed shifted lag-21 = **-0.0404**:

| Null | median | p5 | p95 | observed percentile | CALIBRATED vs obs |
|---|---:|---:|---:|---:|---|
| **Spec** (6942-row panel, **fresh** RNG, null only) | +0.0036 | −0.0465 | **+0.0539** | 7.0th | FAIL (`-0.0404 > 0.0539` is false) |
| **Lane-faithful** (6942-row, RNG after 200 pos draws) | +0.0017 | −0.0436 | **+0.0498** | 7.0th | FAIL |
| **Round-2 clone** (full 8475-row SPY calendar, fresh RNG, `blocknull.py`) | +0.0016 | −0.0487 | **+0.0419** | 9.5th | FAIL |

Lane-faithful rebuild matches the lane’s reported null (median +0.0017, p5 −0.0436, p95 +0.0498) and positive-control median **+0.2533** (p5 +0.2366, p95 +0.2711) exactly at 4 dp.

**+0.0498 vs +0.0419:** not RNG order alone.

- Same 6942-row panel, RNG order only: p95 **0.0539 → 0.0498** (Δ = **0.0041**, “a few 1e-3”).
- Round-2 **0.0419** is the **full 8,475-session** calendar permutation (structural vs spec’s 6,942 sessions from 1999-02-25). Spec-fresh p95 0.0539 vs round-2 0.0419 is Δ = 0.0120, too large to be RNG order.

The lane’s builder matches the written G2 spec (6942-row observed panel). Round-2’s 0.0419 is a different panel. Description at `RESULT.md:55` / `result.json` `null.description` matches the code that was run.

CALIBRATED_FAIL under **all three** nulls: observed −0.0404 is below every p95 **and** below `0.5 × 0.2533 = +0.1267`.

### G1 — leak tests and mutant

`compute_cuts` (`run.py:100-116`) is the expanding-window caller (`tercile_cuts(v_arr, i)` at `:113`). `build_rotation_state_daily` calls it at `:293`; `build_rotation_cuts` at `:331`. Sidecar `rotation_cuts_daily.parquet` is that call path, shifted by `DEFAULT_SHIFT`.

**Test A** (`test_pipeline_cuts_match_tercile_cuts`, `:237-278`): 1,100-session synthetic panel, 50 dates with `t ≥ MIN_TERCILE_HISTORY`, `sidecar[t] == tercile_cuts(v_arr, i_master - DEFAULT_SHIFT)` (exported cut at t = unshifted cut at t−1 = `v[:t-1]` after the required one-session shift).

**Mutant** (scratch copy only): `run.py:113` `tercile_cuts(v_arr, i, ...)` → `tercile_cuts(v_arr, min(i + 1, n), ...)`.

```
python3 -m pytest SCR/mut_g1 -q -p no:cacheprovider -k "pipeline_cuts_match or planted_include or pipeline_cut_unchanged or tercile_cut_uses or tercile_cut_power"
FAILED test_pipeline_cuts_match_tercile_cuts
  AssertionError: LP cut_lo at 2027-09-08: pipeline=-0.1424242424242426 vs tercile_cuts=-0.13636363636363635
  assert actual_lo == pytest.approx(expected_lo, abs=0, rel=0)
1 failed, 4 passed, 12 deselected in 9.65s
```

Named failing test under the specified mutant: **`test_pipeline_cuts_match_tercile_cuts`**. The other four, including **`test_pipeline_cut_unchanged_when_v_prior_only` (Test B)**, passed.

Clean copy of the same five tests: `5 passed, 12 deselected in 10.41s`.

Remove the planted monkeypatch (`test_C1.py:304` `monkeypatch.setattr(R, "tercile_cuts", leaked_cuts)`):

```
FAILED test_planted_include_t_leak_caught_by_cuts
  AssertionError: Planted include-t leak NOT detected ...
  assert leak_detected  (test_C1.py:335)
1 failed in 2.85s
```

Vacuous-when-unplanted is closed. The include-t mutant is visible to Test A.

**Sidecar recompute** (vintage unshifted series, 130 dates ≥ 756, 3 variables = 390 cells):

```
pipeline_compute_cuts_shifted: ok=390 bad=0
testA_tercile_cuts_i_minus_shift: ok=390 bad=0
naive expanding window on exported LP: ok=130 bad=0
```

**Test B gap:** docstring at `:346-348` claims `v[t0]=+1e6` and t0+1 changes. Body (`:361-392`) multiplies XLK close by 1.5 and only asserts sidecar cuts at `target_t` unchanged.

### G3 — positive control

Vintage rebuild of the lane procedure:

```
cs_std = 0.030204045854081374
idio_std = 0.030157792556544872
linspace_std before rescale = 0.019102715890212577
rescaled std(drifts, ddof=0) == cs_std : True
LANE_POS median=0.2533 p5=0.2366 p95=0.2711
panel n_sessions=6942 first=1999-02-25 n_sectors=11
```

Matches `result.json` `positive_control.median_lag21 = 0.2533` and `RESULT.md:54`. Distinct `idio_std` is implemented (`run.py:545-548`). iid-per-session disclosure is in `RESULT.md:51`. Simulated on the 6,942-session index with the availability mask (`run.py:613-621`, `result.json` `calibrated_control.panel`). No test asserts the drift-std equality. `idio_std` and `cs_std` are equal at 4 dp (`0.0302`); the deviation fallback never fires.

### G4 — targeted assertions / tampers

Scratch copies of `result.json` only (C1_REPO = tamrepo):

| Tamper | Test | Result |
|---|---|---|
| `window_n[fast:2020-11-09..2020-12-31].n_sessions = 1` | `test_window_n_recompute` | FAIL `json=1 vs recompute=37` (`test_C1.py:493`) |
| `kappa_by_era[<=2009].persistent = 0.99` | `test_agreement_table_values` | FAIL `json=0.99 vs recompute=0.0289` (`:552`) |
| `contingency_flag[mid][True] = 1` | `test_agreement_table_values` | FAIL `json=1 vs recompute=398` (`:575`) |

All three era κ (`<=2009`, `2010-2019`, `2020-2026`) and every flag/transition contingency cell are asserted inside `test_agreement_table_values`.

### G5 — calibrated_control tampers

| Tamper | Test | Result |
|---|---|---|
| `calibrated_status = CALIBRATED_PASS` | `test_calibrated_control_recompute` | FAIL `json=CALIBRATED_PASS vs recomputed=CALIBRATED_FAIL` (`:624`) |
| `null.p95_lag21 = -0.5` | same | **PASS** (`1 passed in 0.36s`) |
| mutate test threshold `0.5 * pos_median` → `0.0 * pos_median` | same, clean `result.json` | **PASS** (null-p95 clause still binds) |

### G6 / G8 wording

`RESULT.md:122` / `deviations[0]`: “Post-R7 … shifts … by ≤ 0.0003 **relative to the reviewer's pre-R7 values**; the 1e-4 tolerance … applies to recomputation from the exported parquet, which matches exactly.”

`RESULT.md:48-49`: positive-control median **+0.2533** — well below 0.5; uncalibration attributed to that median, not to “observed below null p95”. `rg '{pos[' RESULT.md` → no unrendered f-string. No `≈ 0.23` / `0.1821` in round-3 `RESULT.md`.

### G7 hashes and wall-clock

`hashes.txt` paths are repo-relative (23 lines, 0 absolute). `result.json` stores `tests_pass=15`, `tests_skip=2`, `tests_fail=0`; no `tests` wall-time string.

`shasum -a 256 -c hashes.txt` from a scratch tree laid out as repo root with **vintage** `data/*` plus the lane outputs: **0 non-OK** (23/23 OK).

From this checkout root (newer yahoo/fred vintages): 14 data-file FAILs, all C1 outputs OK:

```
data/yahoo/*.parquet: FAILED (12 files)
data/fred/DFII10.parquet: FAILED
data/regime/regime_v2_pit.parquet: OK
research/.../results/C1/{rotation_state_daily,rotation_cuts_daily,result.json,RESULT.md,code/*}: OK
shasum: WARNING: 14 computed checksums did NOT match
```

That 14-file mismatch is the packet’s local-vintage caveat, not a G7 format bug. Host report of 0 non-OK is consistent with vintage inputs.

### Frozen `result.json` leaf diff vs round 2

Unchanged: `lane`, `status=BROKEN`, `repo_head`, `n_sessions=6942`, `first_date/last_date`, entire `controls.*` (AR1 −0.0404, window means −0.0885 / −0.0881 / +0.1622 / −0.0030, κ, windows n, lag profile), entire `agreement.*`, entire `tercile_counts.*`, `gaps`.

Changed leaves (expected for G2/G3/G6/G7):

```
calibrated_control.null.median_lag5:  -0.0002 → 0.3269
calibrated_control.null.median_lag10: -0.0012 → 0.097
calibrated_control.null.p95_lag21:     0.0181 → 0.0498
calibrated_control.positive_control.median_lag5/10/21, p5_lag21
calibrated_control.scales.idio_std_median: 0.030204 → 0.030158
deviations[0], deviations[1] (G6 reword)
ADDED: null.description, null.median_lag21=0.0017, null.p5_lag21=-0.0436,
       panel.{n_sessions=6942,n_sectors=11,first_date}, positive_control.p95_lag21,
       tests_pass=15, tests_skip=2, tests_fail=0
REMOVED: tests = "11 passed, 1 skipped in 17.08s"
```

Primary `controls.status` remains **BROKEN**. Calibrated outcome remains **CALIBRATED_FAIL**.

### Lane-reported G1 mutant names

`RESULT.md:131-137` names `test_pipeline_cuts_match_tercile_cuts` (run.py:113 mutant) and `test_planted_include_t_leak_caught_by_cuts` (monkeypatch). Independent run confirms the first fails under the `compute_cuts` mutant and the second fails when the monkeypatch is removed. (The planted test **passes** when the monkeypatch is present — that is detection, not a failure.)

## GAPS

- Did not re-run the lane’s `run_all.py` / full 17-test suite against vintage inputs (would rewrite `results/C1/`, forbidden). Clean G1 subset on a scratch copy: 5 passed. Host claim “17 passed, 0 non-OK hashes” not re-executed on the host; locally `shasum -c` from the worktree root fails on 14 data files because this checkout’s `data/yahoo` and `data/fred/DFII10.parquet` are newer than `052e02d`.
- Did not re-simulate the positive-control lag-5/10 series beyond the median-lag-21 confirmation (not required once +0.2533 matched).
- Test B as specified was not present to run; the include-t mutant was run against the test the lane shipped instead.
- `shasum -c` “from the repo root works” was proven on a scratch vintage layout (`SCR/hashroot`), not on this checkout’s live `data/yahoo`.

## DEVIATIONS

- Vintage price/FRED files were reused from the round-2 reviewer’s `fakerepo/` after verifying each `data/*` sha256 against lane `hashes.txt`, rather than a fresh `git show 052e02d085b0:<path>` for every file. Content is the same bytes.
- Spec null was rebuilt two ways: (1) 6,942-row panel as G2’s text states, (2) round-2 `blocknull.py` full-calendar clone. Both are reported. Lane-faithful null was a third run that first burned the RNG on the positive control, matching `run.py` consumption order.
- G1/G4/G5 mutants and tampers were applied only under `SCR/` copies. `C1_REPO` pointed at those copies or at the worktree for imports; no tracked file was written.
- `probe_testB.py` used `compute_cuts` directly on a synthetic LP array with `v[900]=1e6`; that particular t0 did not move the t0+1 quantile (value already on the same side of the cut). It is supporting colour only; the pytest mutant is the G1 evidence.
- Did not spawn a reviewer subagent; the packet required this seat to run the mutants and write `SCR/REVIEW.md`.
