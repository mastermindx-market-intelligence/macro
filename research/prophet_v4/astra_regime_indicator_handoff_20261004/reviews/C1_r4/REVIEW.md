# C1 ROUND 4 independent review

Reviewer: read-only. Checkout `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/astra-host2-052e02d-690b56cac98b57f7` was not written. All mutants/tampers ran on copies under this scratchpad. `run.py` was never executed against the checkout.

## STATUS

PASS

## RESULT

**Recommended ruling: ACCEPT**

Round 4 closed M1..M4 without moving any frozen numeric leaf. Both parquets are byte-identical to the pinned shas and to round 3. Every mutant/tamper named in the packet fails a named test on a scratch copy. The clean copied suite is green.

### Per-item verdict

| Item | Verdict | file:line |
|---|---|---|
| Frozen numbers | FIXED | `rotation_state_daily.parquet` sha256 `9361dbf0…e2dd`; `rotation_cuts_daily.parquet` sha256 `48449253…02f8`; `result.json` sha256 `142de0f2…ea2f` vs R3 `d51c5708…2749` |
| M1 (Test B) | FIXED | `code/test_C1.py:343-383` (`test_pipeline_cut_unchanged_when_v_prior_only`); pipeline helper `code/run.py:111-129` / call site `code/run.py:348`; include-t mutant at `code/run.py:126` |
| M2 (rescale test) | FIXED | `code/test_C1.py:643-653` (`test_positive_control_drifts_std_equals_cs_std`); rescale `code/run.py:167-170` |
| M3 (4-dp disclosure) | FIXED | comparison `code/run.py:1158-1163`; needle `RESULT.md:124` and `result.json:399`; constant `code/run.py:73-76` |
| M4 (p95 tamper power) | FIXED | `code/test_C1.py:592-640` (`test_calibrated_control_recompute`); draws `result.json` `calibrated_control.null.draws` (200 values); stored p95 `0.0498` |
| Tests + write order | FIXED | clean copy `19 passed in 31.01s`; skip identity `test_test_summary_sidecar_full_string_and_mtime` at `code/test_C1.py:720`; hashes mtime after `result.json`/`RESULT.md` |
| Provenance | FIXED | `result.json:401-411` `provenance.host`; `RESULT.md:132-137` `## Provenance`; `shasum -a 256 -c hashes.txt` from repo root = 0 non-OK |
| Return packet | PARTIAL | `RESULT.md:137` has both parquet sha256s and “Frozen tables this round (unchanged)”; `RESULT.md:140-151` names each mutant/tamper with file:line; missing explicit `M1 FIXED`…`M4 FIXED` labels and the sentence that **every table value** is unchanged |

### Numbered defects

None that reopen M1..M4 or move a frozen number.

Residual documentation miss (does not change the ruling; substance is in `## Tests` / `## Provenance`):

1. `RESULT.md` never writes the four strings `M1 FIXED` … `M4 FIXED` with file:line of the fix, and never states that every positive-control / agreement / contingency / calibrated_control **summary-table** value is unchanged (it only freezes the two parquets). **Re-check that closes it:** `rg -n 'M1 FIXED|M2 FIXED|M3 FIXED|M4 FIXED|every table value is unchanged' RESULT.md` returns hits; hashes.txt restamped last.

## EVIDENCE

### Environment

```
/opt/homebrew/bin/python3 → 3.14.7
pandas 3.0.5 / numpy 2.5.2 / pyarrow 25.0.1 / scipy 1.18.0 / pytest 9.1.1
```

### Frozen numbers — parquet shas

```
shasum -a 256 results/C1/rotation_state_daily.parquet
9361dbf08018f0c23bc6e9b29fa014bc42429ed3289d359adf7a16f52be3e2dd

shasum -a 256 results/C1/rotation_cuts_daily.parquet
484492539ae42cb3055416c12f144f93f748549bf21e4cf3de2f1e1eb6a002f8
```

Round-3 preserved copies are byte-identical (same two shas). Packet pins: state `9361dbf08018f0c2…e2dd`, cuts `48449253…`. Round-4 `result.json` sha256 `142de0f2541513d9bbe660ff562678c63139e05def86d0048da5db1703cfea2f` matches the packet prefix `142de0f2…`. Round-3 `result.json` sha256 `d51c5708e385849231a0f5193a06c2586c546b87c142b262ff3bafa1dba32749` matches `d51c5708…`.

### Frozen numbers — result.json leaf diff vs R3

Flattened JSON leaf diff (lists-of-scalars treated as one leaf plus per-index leaves). **Removed leaves: 0.** **Numeric leaves of `controls`, `agreement`, `tercile_counts`, and `calibrated_control` summary tables: none changed.**

**CHANGED (3):**

| leaf | R3 | R4 | class |
|---|---|---|---|
| `tests_pass` | 15 | 18 | repair bookkeeping (admissible) |
| `tests_skip` | 2 | 1 | repair bookkeeping (admissible) |
| `deviations` (list object) | len 2 | len 3 | additive deviation text (admissible) |

**ADDED (classified):**

| leaf | value | class |
|---|---|---|
| `calibrated_control.null.draws` | list of **200** floats, first `-0.03255192129945978`, last `-0.0724071289374269` | M4 required additive |
| `calibrated_control.null.draws[0]` … `draws[199]` | 200 indexed scalars (all new) | same as above |
| `deviations[2]` | `idio_std and cs_std agree at 4 dp (0.0302): the positive control's idiosyncratic and cross-sectional scales are not distinguishable at that precision` | M3 required additive |
| `provenance.host.hostname` | `m2studio` | HOST required additive |
| `provenance.host.python` | `3.14.7` | HOST |
| `provenance.host.python_path` | `/opt/homebrew/opt/python@3.14/bin/python3.14` | HOST |
| `provenance.host.pandas` | `3.0.5` | HOST |
| `provenance.host.numpy` | `2.5.2` | HOST |
| `provenance.host.pyarrow` | `25.0.1` | HOST |
| `provenance.host.scipy` | `1.18.0` | HOST |
| `provenance.host.pytest` | `9.1.1` | HOST |

Unchanged (spot-checked, equal in R3 and R4): `controls.status=BROKEN`, `controls.ar1_lag21=-0.0404`, window means `-0.0885 / -0.0881 / 0.1622 / -0.003`, `kappa_persistent=-0.0129`, `kappa_fast=0.0004`, era n `1975 / 2516 / 1633`, join `6880 / 6124 / 756 / 2026-07-02`, `calibrated_control.positive_control.median_lag21=0.2533`, `calibrated_control.null.p95_lag21=0.0498`, `calibrated_control.calibrated_status=CALIBRATED_FAIL`, `scales.cs_std_median=0.030204`, `scales.idio_std_median=0.030158`. No numeric leaf of those tables moved.

### M1 (Test B)

`test_pipeline_cut_unchanged_when_v_prior_only` (`test_C1.py:343`):

- builds a synthetic panel with `_write_panel(..., n_sessions=1100)` and asserts `len(v_arr) >= 1100`
- takes unshifted LP via the pipeline helper `_unshifted_value_arrays()` (same arrays `compute_cuts` / the sidecar consume)
- runs `R.compute_cuts(v_arr)` — the pipeline’s own helper (`run.py:348` `cut_low, cut_high = compute_cuts(...)`; sidecar `run.py:386` `cl, ch = compute_cuts(s.to_numpy())`)
- chooses one `t0 >= 800` with finite cuts; sets **unshifted V** `v1[t0] = 1.0e6` (not a close)
- asserts `cut(t0)` identical **and** `cut(t0+1)` different

Clean `run.py:126` is `tercile_cuts(v_arr, i, ...)`. Include-t mutant applied on `SCR/code_m1` only:

```
126:        cl, ch = tercile_cuts(v_arr, min(i + 1, n), lo_q=lo_q, hi_q=hi_q, min_history=min_history)
```

Suite on the mutant copy:

```
FAILED .../code_m1/test_C1.py::test_pipeline_cut_unchanged_when_v_prior_only
AssertionError: cut at t0=800 changed after v[800]=+1e6:
(-0.11818181818181818, 0.1393939393939392) -> (-0.1121212121212122, 0.14545454545454545)
2 failed, 17 passed in 30.76s
```

Named test **FAILS**. (The other failure is `test_pipeline_cuts_match_tercile_cuts`, also include-t power, not required by M1.)

### M2 (rescale)

`test_positive_control_drifts_std_equals_cs_std` (`test_C1.py:648-653`) asserts `abs(np.std(drifts, ddof=0) - cs_std) < 1e-12` for `cs_std in (0.030204, 0.01, 1.0)`.

Rescale block deleted on `SCR/code_m2` (`run.py:168-170` `sd = …; assert sd > 0; drifts = drifts * (cs_std / sd)`):

```
FAILED .../code_m2/test_C1.py::test_positive_control_drifts_std_equals_cs_std
AssertionError: std(drifts, ddof=0)=0.01910268688954515 vs cs_std=0.030204
1 failed, 18 deselected in 0.46s
```

Named test **FAILS**. (Lane RESULT.md quoted `0.01910` vs `0.030204`; this run `0.01910268688954515`.)

### M3 (4-dp disclosure)

```
rg -n 'agree at 4 dp \(0.0302\)'
RESULT.md:124: - idio_std and cs_std agree at 4 dp (0.0302): ...
result.json:399: "idio_std and cs_std agree at 4 dp (0.0302): ..."
code/run.py:74: constant IDIO_CS_4DP_DEVIATION (same sentence)
```

Code now compares at 4-dp rounding, not 6-dp exact equality:

```
code/run.py:1158-1163
    cs4 = round(float(calibrated["scales"]["cs_std_median"]), 4)
    idio4 = round(float(calibrated["scales"]["idio_std_median"]), 4)
    if cs4 == idio4:
        deviations.append(IDIO_CS_4DP_DEVIATION)
```

`cs_std_median=0.030204`, `idio_std_median=0.030158` → both `round(..., 4) == 0.0302`.

### M4 (p95 tamper power)

`calibrated_control.null.draws` length **200**. Recompute from stored draws (`numpy.percentile` default `linear`):

| stat | from draws | stored | |Δ| vs 1e-4 |
|---|---|---|---|
| p95 | `0.04984484099840291` | `0.0498` | `4.48e-5` < 1e-4 |
| median | `0.0017455286220487256` (`np.median`) | `0.0017` | `4.55e-5` < 1e-4 |
| p5 | `-0.043599566944382426` | `-0.0436` | `4.3e-7` < 1e-4 |

Stored p95 is **+0.0498**. Draws reproduce the summary at 1e-4.

Tamper mechanism: tests read `R.OUT_RESULT_JSON` (`C1_REPO/.../results/C1/result.json`) with **no per-file override**. Live file was **not** tampered. Copies of `result.json` were placed in scratch shadow repos (`SCR/shadow_status`, `SCR/shadow_p95`) with `data/` and the two parquets symlinked read-only; suite pointed at the shadow via `C1_REPO`.

Status tamper `calibrated_status=CALIBRATED_PASS`:

```
FAILED .../code_m4/test_C1.py::test_calibrated_control_recompute
AssertionError: calibrated_status json=CALIBRATED_PASS vs recomputed=CALIBRATED_FAIL
1 failed, 18 deselected in 0.52s
```

p95 tamper `p95_lag21=-0.5`:

```
FAILED .../code_m4/test_C1.py::test_calibrated_control_recompute
AssertionError: p95 from draws=0.04984484099840291 vs stored -0.5
1 failed, 18 deselected in 0.51s
```

Both named-test **FAIL**. Live `result.json` still `CALIBRATED_FAIL` / `p95_lag21=0.0498` / sha256 `142de0f2…`.

### Tests + write order

Command (copy of `code/` under SCR; `C1_REPO` = checkout so tests read live records, not rewrite them):

```
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest SCR/code -q -p no:cacheprovider -rs
19 passed in 31.01s
```

19 tests collected (list in the collect-only log). Lane stamped `18 passed, 1 skipped in 29.77s` (`code/_test_summary.txt` and `RESULT.md` fence).

**Skip identity (lane’s orchestrated pytest):** `test_test_summary_sidecar_full_string_and_mtime`. `run.py` writes `tests_pass: 0` before pytest; the test does `if not res.get("tests_pass"): pytest.skip("Orchestrator has not yet stamped result.json")` at `test_C1.py:720`. Reproduction on a shadow with `tests_pass=0` and hashes present: that test SKIPPED, `test_hashes_txt_repo_relative` PASSED. This is the write-order skip of a record-existence test (pytest runs before the stamp; hashes are written last). It is **not** a missing-`hashes.txt` skip — leftover `hashes.txt` already exists during pytest.

Post-hoc with `hashes.txt` present and `tests_pass=18`: **does not skip** (`19 passed`).

If `hashes.txt` is deleted, `test_hashes_txt_repo_relative` skips at `test_C1.py:764` (`hashes.txt not yet written`) — that is the hashes-last skip, and it was **not** the lane’s 1 skip.

**mtimes (`st_mtime_ns`):**

```
result.json                 1791098911531022004
RESULT.md                   1791098911531331127
code/_test_summary.txt      1791098911531742625
hashes.txt                  1791098911920930155
DONE                        1791098981864876925
```

`hashes.txt` is newer than `result.json` and `RESULT.md` (and the sidecar). `DONE` is later, as the HOST+COMPLETION last act. Write order matches orchestrator: stamp `result.json` → `RESULT.md` → sidecar → hashes LAST.

### Provenance

`result.json` `provenance.host`: hostname `m2studio`, python `3.14.7`, python_path `/opt/homebrew/opt/python@3.14/bin/python3.14`, pandas `3.0.5`, numpy `2.5.2`, pyarrow `25.0.1`, scipy `1.18.0`, pytest `9.1.1`.

`RESULT.md` `## Provenance` states the same host and the same five library versions (plus python).

```
cd <repo root> && shasum -a 256 -c research/prophet_v4/astra_regime_indicator_handoff_20261004/results/C1/hashes.txt
```

23 lines, all `OK`, exit 0, **0 non-OK**, no caveat. Paths in `hashes.txt` are repo-relative (`data/yahoo/...`, `research/prophet_v4/.../results/C1/...`).

### Return packet

`RESULT.md` `## Provenance` prints both parquet sha256s and “Frozen tables this round (unchanged)”. `## Tests` lists include-t / rescale-deleted / status tamper / p95 tamper with file:line and the failing test name, plus `18 passed, 1 skipped in 29.77s`. It does **not** contain `M1 FIXED` / `M2 FIXED` / `M3 FIXED` / `M4 FIXED`, and does not say every table value is unchanged. Verdict PARTIAL; not a number or power hole.

## GAPS

- Did not run `results/C1/code/run.py` against the checkout (it rewrites `results/C1/`; no output-directory override). No independent rebuild of the 200-panel calibrated control. Draws-vs-summary was checked from the stored array at 1e-4; that does not re-prove the draws were produced by the block-permutation generator in this round.
- Lane’s original pytest stdout is not in this scratchpad; skip identity of the stamped `1 skipped` is inferred from `run.py` writing `tests_pass: 0` plus a shadow reproduction, then confirmed by the post-hoc 19-passed run.
- `MUTANT_POWER_DOC` in `run.py` is empty; the mutant narrative in `RESULT.md` was filled by some path other than the default `write_result_md` (hashes still match the delivered `RESULT.md`). Not re-derived.

## DEVIATIONS

- Tests ran on copies of `code/` under `SCR/` with `C1_REPO` pointing at the live checkout (or a scratch shadow for M4) so `run.py`’s `_find_repo()` would not walk into the sparse worktree and so live `results/C1/` was never written.
- M4 tampers used scratch shadow repos (`SCR/shadow_status`, `SCR/shadow_p95`) with `result.json` copied and tampered, `data/` and the two parquets symlinked read-only, because `test_calibrated_control_recompute` reads `R.OUT_RESULT_JSON` with no file override. Live `result.json` was not modified.
- M1/M2 mutants applied with a Python string replace on `SCR/code_m1/run.py` and `SCR/code_m2/run.py` (equivalent to the specified sed).
- Pytest invoked as `PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3 -m pytest SCR/<copy> -q -p no:cacheprovider` from the checkout as cwd. Extra flags used only for diagnosis: `-rs`, `--tb=short`/`--tb=line`, `-k` for named-test tampers, `--collect-only`.
- Did not spawn subagents; review executed in this process.
- No git writes, no `gh`, no ssh, no network.
