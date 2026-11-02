# F1 ROUND 4 — independent read-only review

Checkout: `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/astra-host2-052e02d-690b56cac98b57f7` (DETACHED `052e02d085b01f29baf499357e224c836d8eb224`).
Lane: `research/prophet_v4/astra_regime_indicator_handoff_20261004/results/F1/`.
Round-3 baseline: `scratchpad/results_prev/F1_r3/result.json` sha256 `8315d69e2cd923513b959c255907c1c426a4dc08da33283eebc8d21d791c089b` (verified).
Round-4 `result.json` sha256 `8ad46a1a5272c6191b3edfe8f8b7bea228ba6ecb19596f4d681a00308d2e3f2b`.
Host: `m2studio`; `/opt/homebrew/bin/python3` 3.14.7; pandas 3.0.5 / numpy 2.5.2 / pyarrow 25.0.1 / scipy 1.18.0 / pytest 9.1.1.

## STATUS

PASS

## RESULT

**Ruling: ACCEPT.**

Round-4 majors P1 (production-comparator purge tests + real subprocess mutants), P2 (record checker), and P3 (generated §12) are closed. The listed frozen science keys (AUC, CIs, shares, hazards, honest-N, attribution, fold records) are byte-identical to round 3. Verdict remains MIXED: purged OOS AUC 0.6227 [0.5715, 0.6738]; deteriorated share 0.1484; immediate-failure share 0.6813; `hazard.overall.h1[0]` 0.1246.

P4 is PARTIAL: three `top_coefficients[*][1]` leaves moved at ~1e-15–1e-14 (documented round-3 cross-host IRLS noise; 4-decimal RESULT.md values unchanged); the lane did not paste a leaf diff; two consecutive `run.py` result.json shas are not in the written record. Those residuals do not reopen P1–P3 and do not move the frozen verdict numbers.

### Per-item verdict

| Item | Verdict | file:line |
|---|---|---|
| P4 frozen numbers + hygiene | PARTIAL | `result.json:66-78` (coeff last digits); `RESULT.md` has no leaf-diff block; `result.json:5-16` + `RESULT.md:220-224` provenance.host present; `hashes.txt` newest content file then `DONE`; `run.py:1973` prints only one sha |
| P1 production-comparator purge tests | FIXED | `test_f1.py:41-67` (import, not re-implement); `test_f1.py:87-96` `_production_included`; `test_f1.py:99`, `:121`, `:136` (three purge tests); `run.py:457-464` `_make_label_realisation_comparator` / `return end_dates < ws_dt64  # BINDING_CMP`; `run.py:521` `apply_train_mask`; `run.py:531-579` synthetic panel + `included_label_ids`; `run.py:1667-1702` `_run_mutant_pytest` subprocess |
| P2 record checker | FIXED | `check_result_md.py:60-72` both CI bounds; `:129-131` `h1 (≤ 5)` → `hazard.overall.h1[0]` bold height; `:191-228` both primary CI bounds; `:291-341` every hazard height + CI; `:301-307` scalar h1 → schema MISMATCH no traceback; `:366-426` specified-mutation battery |
| P3 §12 generated from pytest payload | FIXED | `run.py:1539-1573` `render_result_md` §12 from `mutant_runs`; `RESULT.md:226-275` matches `result.json:440-541` names and counts |
| Hygiene (host, skips, hashes, C1 pin) | FIXED except dual-sha GAP | `result.json:5-16`; `RESULT.md:220-224`; clean pytest `17 passed` / 0 skipped; `hashes.txt` 10 OK / 0 FAILED / 0 WARNING; C1 pin `142de0f2…` == live C1 |

### Defect list

1. **P4 — three science-adjacent coefficient leaves moved at ~1e-15–1e-14** (`result.json:66-78` vs round 3).
   - `entry_model.top_coefficients[0][1]` (sector_etf=XLE): r3=`-1.051934041080038` → r4=`-1.0519340410800413` (Δ `-3.33e-15`)
   - `entry_model.top_coefficients[1][1]` (sector_etf=XLY): r3=`1.0152414277810524` → r4=`1.0152414277810493` (Δ `-3.11e-15`)
   - `entry_model.top_coefficients[2][1]` (rank_by=bottoming-alignment): r3=`-0.9251720328575119` → r4=`-0.9251720328575228` (Δ `-1.09e-14`)
   - AUC / CIs / shares / hazards / honest-N / attribution / fold records / verdict are byte-identical. RESULT.md still prints `-1.0519` / `+1.0152` / `-0.9252`. Round-3 packet already said not to chase ~1e-14 coefficient last digits across hosts; this round ran on `m2studio`.
   - **Re-check that closes it:** leaf-diff `top_coefficients[*][1]` against round-3 `8315d69e…`; either bit-identical or a seat-signed cross-host note naming these three paths.

2. **P4 — lane did not paste a leaf diff vs round 3** (`RESULT.md` has no “leaf” / changed-path block).
   - Independent diff is in EVIDENCE. Allowed-class changes are `mutant_runs`, `tests`, `provenance.host` plus the three coefficient last digits above.
   - **Re-check that closes it:** `RESULT.md` contains the full changed/added/removed leaf-path list matching an independent flatten of r4 vs r3.

3. **P4 — two consecutive `run.py` result.json sha256s not in the written record.**
   - `run.py:1973` prints one `result_json_sha` on stdout. RESULT.md / result.json do not store two identical shas. This review must not re-run live `run.py` (it rewrites `results/F1/`).
   - **Re-check that closes it:** two consecutive orchestrated runs print the same sha256 of `results/F1/result.json`, and both values appear in RESULT.md.

No P1 / P2 / P3 defects remain.

## EVIDENCE

### Round-3 sha (verified first)

```
8315d69e2cd923513b959c255907c1c426a4dc08da33283eebc8d21d791c089b  .../scratchpad/results_prev/F1_r3/result.json
```

Matches the packet. Checkout HEAD `052e02d085b01f29baf499357e224c836d8eb224`.

### P4 — full leaf diff vs round 3

Flattened leaves: r3=330, r4=364. CHANGED=15, ADDED=65, REMOVED=31.

**CHANGED (every path):**

| path | r3 | r4 | class |
|---|---|---|---|
| `entry_model.top_coefficients[0][1]` | -1.051934041080038 | -1.0519340410800413 | science-adjacent (1e-15) |
| `entry_model.top_coefficients[1][1]` | 1.0152414277810524 | 1.0152414277810493 | science-adjacent (1e-15) |
| `entry_model.top_coefficients[2][1]` | -0.9251720328575119 | -0.9251720328575228 | science-adjacent (1e-14) |
| `tests` | `14 passed, 2 skipped` | `17 passed` | allowed (`tests`) |
| `mutant_runs.clean.n_pass` | 14 | 17 | allowed |
| `mutant_runs.clean.summary` | `14 passed, 2 skipped` | `17 passed` | allowed |
| `mutant_runs.m_peek.n_fail/n_pass/summary` | 1 / 1 / synthetic n_violations | 5 / 10 / `5 failed, 10 passed, 2 skipped` | allowed |
| `mutant_runs.m_peek_rec.n_fail/n_pass/summary` | 1 / 1 / synthetic | 5 / 10 / pytest tail | allowed |
| `mutant_runs.m_r1.n_fail/n_pass/summary` | 1 / 1 / synthetic | 5 / 10 / pytest tail | allowed |

**ADDED (every path, roots only expanded):** `provenance.host.{hostname,python,python_executable,pandas,numpy,pyarrow,scipy,pytest}`; `mutant_runs.checker.{clean,md_auc_09999,md_cihi_01111,rj_auc_08123,rj_h1_09,rj_h1_scalar}.{returncode,output,n_mismatch,n_checked}`; `mutant_runs.clean.{n_skip,pytest_tail,returncode}`; per-mutant `{label,mutant,mutated_line,n_skip,pytest_tail,returncode,failing_tests[1..4]}`.

**REMOVED:** entire `mutant_runs.m_10.*`; per-mutant `{n_folds,n_violations,violating_weeks[*]}` (replaced by real pytest payload).

**Listed frozen science keys — EQUAL:** `entry_model.{oos_auc,oos_auc_ci,in_sample_auc,n_oos,n_test_weeks,n_removed_strict,per_week_aucs,fold_records,sensitivity,bootstrap}`, `honest_n`, `drop_counts`, `hazard`, `attribution`, `prophet_ledger`, `verdict`, `gaps`, `deviations`, `status`, `repo_head`.

Frozen numbers: oos_auc=`0.6227445818504856` → 0.6227; CI=`[0.5715116526475553, 0.6737902559867878]` → [0.5715, 0.6738]; deteriorated=`0.14841849148418493` → 0.1484; immediate=`0.681265206812652` → 0.6813; h1[0]=`0.12462552426602756` → 0.1246. Lever MIXED.

Lane pasted the same leaf diff? **No.** `RESULT.md` contains no leaf-path list.

### P1 — production comparator + mutants

`test_f1.py` imports `_make_label_realisation_comparator`, `apply_train_mask`, `build_synthetic_purge_panel`, `included_label_ids`, `synthetic_role_sets` from `run.py` and does not re-implement the comparator. Binding line is now `run.py:464` (`return end_dates < ws_dt64  # BINDING_CMP`; round 3 was `:438`).

Synthetic panel (week_start `2026-08-03`, cutoff `2026-07-01`):

| label_id | as_of | realisation (as_of+21 NYSE) | role | binding `<` |
|---|---|---|---|---|
| L_before | 2026-07-01 | 2026-07-31 | (i) strictly before week start | included |
| L_peek5 | 2026-07-06 | 2026-08-04 | (ii) inside +5d peek window | excluded |
| L_peek14 | 2026-07-13 | 2026-08-11 | (iii) as_of inside cutoff+14d | excluded |
| L_on_ws | 2026-07-02 | 2026-08-03 | (iv) realised ON week start | excluded |

Production included set `{'L_before'}`; excluded `{L_peek5, L_peek14, L_on_ws}`. Mutating line 464:

- m_peek (`as_of < ws+5d`): includes all four (all as_of in July).
- m_peek_rec (`as_of <= cutoff+14d`): includes all four (all as_of ≤ 2026-07-15).
- m_r1 (`end_dates <= ws`): includes `{L_before, L_on_ws}` only.

Purge-only pytest (`-k purge`) on scratch copies:

```
clean:        3 passed, 14 deselected in 0.33s   exit=0
m_peek:       3 failed, 14 deselected in 0.31s  FAIL test_purge_embargo_actually_holds, test_purge_negative_control_with_weaker_embargo, test_purge_forward_peek_mutants_fail
m_peek_rec:   3 failed, 14 deselected in 0.31s  FAIL same three (leaks L_peek5/L_peek14/L_on_ws)
m_r1:         3 failed, 14 deselected in 0.31s  FAIL same three (leaks L_on_ws only)
```

Full pytest on copies (`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest SCR/<copy> -q -p no:cacheprovider`), cwd = checkout:

```
clean full F1-tree copy (records+code so check_result_md parent.parent resolves):
  17 passed in 2.57s   exit=0   n_skip=0

m_peek (code-only copy, BINDING_CMP → m_peek):
  5 failed, 12 passed in 3.18s
  FAILED test_purge_embargo_actually_holds
  FAILED test_purge_negative_control_with_weaker_embargo
  FAILED test_purge_forward_peek_mutants_fail
  FAILED test_result_json_byte_stable_across_runs
  FAILED test_result_md_matches_result_json

m_peek_rec: 5 failed, 12 passed in 3.12s  (same five names)
m_r1:       5 failed, 12 passed in 2.54s  (same five names)
```

`result.json mutant_runs` failing_tests for each mutant = the same five names, in the same order. Lane counts are `5 failed, 10 passed, 2 skipped` because `_run_mutant_pytest` runs after `hashes.txt` is unlinked (`run.py:1840-1842`), so `test_hashes_path_is_repo_relative` and `test_hashes_txt_checksum_passes` skip. This read-only review cannot unlink live `hashes.txt`; those two tests therefore passed here. Failing purge-test names match. Payload fields (`n_pass`, `n_fail`, `failing_tests`, `pytest_tail`, `returncode`, `mutated_line`) are structured as a real subprocess pytest parse (`run.py:1610-1702`), not the round-3 synthetic `n_violations` strings.

Clean live analog (full tree copy): **17 passed, 0 skipped**, matching `mutant_runs.clean` and `result.json["tests"]="17 passed"`.

### P2 — six checker cases

Pointing method: copied `{RESULT.md, result.json, code/check_result_md.py}` to `SCR/checker_<case>/` mirroring the checker's default layout (`RESULTS_DIR = Path(__file__).resolve().parent.parent`). Ran `python3 SCR/checker_<case>/code/check_result_md.py` (no live-path read). The checker also accepts `--json/--md`; those were not needed.

| case | mutation | n_mismatch | n_checked | exit | traceback |
|---|---|---|---|---|---|
| clean | none | 0 | 42 | 0 | no |
| md_auc_09999 | RESULT.md `0.6227`→`0.9999` | 1 | 42 | 1 | no |
| md_cihi_01111 | RESULT.md `0.6738`→`0.1111` | 1 | 42 | 1 | no |
| rj_auc_08123 | result.json `oos_auc`→`0.8123` | 1 | 42 | 1 | no |
| rj_h1_09 | `hazard.overall.h1[0]`→`0.9` | 2 | 42 | 1 | no |
| rj_h1_scalar | `hazard.overall.h1` = scalar `0.9` | 2 | 40 | 1 | no |

Decisive outputs (match `mutant_runs.checker` exactly):

```
check_result_md: 0/42 mismatches (all 42 labeled numbers present)          exit=0
check_result_md: 1/42 mismatches  label=OOS AUC (primary) | **  md=0.9999  rj=0.6227445818504856
check_result_md: 1/42 mismatches  label=oos_auc_ci[1]  md=0.1111  rj=0.6737902559867878
check_result_md: 1/42 mismatches  label=OOS AUC (primary) | **  md=0.6227  rj=0.8123
check_result_md: 2/42 mismatches  h1 (≤ 5) → hazard.overall.h1.0  md=0.1246 rj=0.9
                                  hazard.h1[0] → hazard.overall.h1[0]  md=0.1246 rj=0.9
check_result_md: 2/40 mismatches  schema violation: key path did not resolve to a number
                                  schema violation: expected [height, lo, hi]
```

Both CI bounds parsed (`check_result_md.py:191-228`). `h1 (≤ 5)` bound to height `hazard.overall.h1[0]`, not `n_h1` (`:129`). Every hazard height compared (`:291-317`). Scalar h1 is a mismatch, not a TypeError.

### P3 — §12 vs mutant_runs

Programmatic compare of RESULT.md §12 vs `result.json["mutant_runs"]`:

- m_peek / m_peek_rec / m_r1: md `pass=10, fail=5` equals json; failing name lists equal; pytest_tail first line present in md.
- Clean: md `pass=17, fail=0, skip=0` equals json.
- Names `test_purge_embargo_actually_holds` and `test_purge_negative_control_with_weaker_embargo` appear in this reviewer's m_peek and m_peek_rec pytest output (and `test_purge_forward_peek_mutants_fail`).

§12 is rendered from the payload (`run.py:1556-1573`: “never hard-typed”).

### Hygiene

- `provenance.host` present in `result.json:5-16` (hostname `m2studio`, python 3.14.7, pandas 3.0.5, numpy 2.5.2, pyarrow 25.0.1, scipy 1.18.0, pytest 9.1.1) and RESULT.md `## Provenance` (`RESULT.md:220-224`).
- Two consecutive run shas: **not in the record** (GAP).
- Skips: lane final pytest line `17 passed` (`test_summary.txt`, `result.json["tests"]`); post-hoc full-tree copy `17 passed in 2.57s` — **0 skips**.
- hashes.txt newest content file (fractional mtime): result.json `…565.952845788` < RESULT.md `…565.955041561` < test_summary.txt `…565.955604723` < **hashes.txt `…565.956998378`** < DONE `…566.021530663`. Write order matches H7 + DONE last.
- From checkout root: `shasum -a 256 -c research/prophet_v4/astra_regime_indicator_handoff_20261004/results/F1/hashes.txt` → **10 OK, 0 FAILED, 0 WARNING, 0 improperly-formatted**. Literal `shasum -a 256 -c hashes.txt` at repo root fails (`hashes.txt: No such file`); the file lives under `results/F1/`. No blank lines in hashes.txt.
- C1 pin: hashes.txt `142de0f2541513d9bbe660ff562678c63139e05def86d0048da5db1703cfea2f` == live `results/C1/result.json`. Parquet `9361dbf08018f0c23bc6e9b29fa014bc42429ed3289d359adf7a16f52be3e2dd` unchanged. Packet C1 round-4 record matches. `run.py` prints `C1_SHA_LOAD` / `C1_SHA_END` to stdout only; those prints are not stored in result.json.

## GAPS

1. **Two consecutive `run.py` result.json sha256s.** Packet forbids running live `run.py` (it rewrites `results/F1/`). No output-directory override exists. Cannot reproduce dual-sha identity. One sha is printed at `run.py:1973` on stdout of a run this review does not have.
2. **C1 sha at LOAD vs END of the lane's orchestrated run.** Only the hashes.txt pin and the live file are observable now; they match (`142de0f2…`). LOAD/END stdout lines are not in the record.
3. **Lane mutant skip counts (2 skipped)** cannot be reproduced without unlinking live `hashes.txt` (forbidden write). Failing test names still match.
4. **Literal `cd $CHECKOUT && shasum -a 256 -c hashes.txt`** looks for a repo-root `hashes.txt` that does not exist. The passing command is `shasum -a 256 -c research/prophet_v4/astra_regime_indicator_handoff_20261004/results/F1/hashes.txt`.

## DEVIATIONS

1. Tests were executed only on copies under `SCR` (`code_clean`, `code_m_peek`, `code_m_peek_rec`, `code_m_r1`, `f1_tree/code`, `checker_*`). Checkout was not modified. `run.py` was never executed against the checkout.
2. Clean full-suite analog used a copy of the whole `results/F1` tree (`SCR/f1_tree/{result.json,RESULT.md,hashes.txt,test_summary.txt,code/}`) so `check_result_md.py`'s `Path(__file__).parent.parent` resolved to records. A code-only clean copy fails `test_result_md_matches_result_json` with `missing input: rj=False rmd=False` — layout artifact, not a live-record failure. The live-layout copy passed 17/17.
3. Mutant copies were code-only, matching `_run_mutant_pytest`. Binding line mutated at first occurrence of `return end_dates < ws_dt64  # BINDING_CMP` (line 464), same `replace(..., 1)` as production.
4. Checker cases used the checker's native parent.parent layout under `SCR/checker_<case>/`, not `--json/--md`.
5. Purge-only (`-k purge`) runs were extra diagnostics ahead of the specified full pytest command.
6. `python3` was `/opt/homebrew/bin/python3` (3.14.7), as specified.
7. No git writes, no gh, no ssh, no network. Read-only `git rev-parse HEAD` only.
