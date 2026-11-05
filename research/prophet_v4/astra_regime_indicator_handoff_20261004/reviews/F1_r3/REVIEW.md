# F1 ROUND 3 independent review

## STATUS

PASS (review completed; every commissioned item was checked).

## RESULT

**REQUEST_REPAIR.** Frozen science numbers did not move. H3/H5/H6/H7/H8/H9/H10 closed. Two MAJOR re-checks still fail: the leak tests do not fail under m_peek / m_peek_rec, and the record checker still reports 0 mismatches for `0.6738→0.1111` and `h1→0.9`.

Round-2 `result.json` sha256 (recorded first):
`cc1fbc620142f33f355a7b4027e397211294396055a11dff91e490aac381f485`

Round-3 `result.json` sha256:
`8315d69e2cd923513b959c255907c1c426a4dc08da33283eebc8d21d791c089b`

Current binding comparator (round-2 `run.py:439` `end_dates < ws_dt64`) is `results/F1/code/run.py:438` `return end_dates < ws_dt64` inside `_make_label_realisation_comparator`.

### Per-item verdicts

| Item | Verdict | file:line |
|---|---|---|
| H1 leak tests | **NOT FIXED** | `test_f1.py:88-101` (positive test reads committed `result.json`); `test_f1.py:104-116` (negative control hard-codes `comparator="m_10"`); `test_f1.py:119-130` (named-mutant factories, independent of the binding line); `run.py:438` (binding comparator) |
| H2 record checker | **PARTIAL** | `check_result_md.py:97` (`OOS AUC (primary)` → `oos_auc`, works); `check_result_md.py:141-145` (CI check reads only the **first** number after `95% week-cluster CI \| [`, the lower bound); `check_result_md.py:105` (`h1 (≤ 5)` bound to `n_h1=208`, not `hazard.overall.h1[0]`); `check_result_md.py:177-193` (hazard CI bounds only) |
| H3 fail-closed | **FIXED** | `run.py:1665-1678` (`status="TESTS_FAILED"`, `sys.exit(1)`). Scratch m_peek run: status `TESTS_FAILED`, exit 1, live `result.json` sha unchanged |
| H4 RESULT.md mutant names | **NOT FIXED** | `run.py:1635-1638` (hard-codes `failing_tests=["test_purge_embargo_actually_holds"]` from violation counts, never pytest); `RESULT.md:225-228` (same; does not name `test_purge_negative_control_with_weaker_embargo`) |
| H5 7.4% / 17.4% | **FIXED** | `RESULT.md:5`, `:184`, `:189`. No standalone `7.4%`. `17.4%` appears 3 times, rendered from `bootstrap.n_draws_ge_065=174 / 1000` |
| H6 support points | **FIXED** | `run.py:622-654`; `result.json` `entry_model.bootstrap`: `distinct_at_1e10=35`, `distinct_at_1e4=33`, `multiset_max=35`. Per-week-AUC sentence deleted from ANSWER FIRST and §8 |
| H7 write order / skips | **FIXED** | `run.py:1609-1620` (delete `hashes.txt` before pytest), `:1649-1656` (write `result.json`/`RESULT.md`), `:1654-1656` (pytest), `:1680-1685` (fold summary without wall-clock), `:1692-1693` (`hashes.txt` LAST). Skip sites `test_f1.py:244` and `:264`. Stability test `test_f1.py:283-323` re-runs `purged_oos_logistic` and compares **fold_records** shas (not full `result.json` shas; allowed fallback) |
| H8 hashes.txt blank line | **FIXED** | `run.py:1574-1592`; `hashes.txt` 12 lines, 0 blank, no `improperly formatted` |
| H9 embargo literal | **FIXED** | `run.py:1527-1528` (`embargo_rule_alt`); `result.json:112`; `RESULT.md:5`, `:58` (5 hits in md, 3 in json) |
| H10 c1 fail-closed | **FIXED** | `run.py:68-87` (`c1_available` iff status `== "OK"`); `run.py:344-350` (`join_c1`); `run.py:973-979` (`ledger_denom`); `test_f1.py:351-365` |
| Frozen numbers | **FIXED** | no science leaf moved vs round 2 (see leaf diff). Permitted round-3 leaves only: wording, bootstrap counts (H6), `mutant_runs`, `tests` string |

### Numbered defects (each with the closing re-check)

**D1 (H1, MAJOR).** Mutating the production embargo comparator does not make `test_purge_negative_control_with_weaker_embargo` fail. On scratch copies of `code/`, changing `run.py:438` `return end_dates < ws_dt64` to m_peek (`as_of < week_start + 5 calendar days`), to m_peek_rec (`as_of <= cutoff + 14 calendar days`), and to m_r1 (`end_dates <= ws_dt64`) and running `python3 -m pytest SCR/<copy> -q -p no:cacheprovider`:

- all three purge tests **PASSED** under every mutant (and under a clean copy);
- the only mutant-specific extra failure was `test_result_json_byte_stable_across_runs` (re-run of the mutated **binding** comparator vs committed folds).

A full scratch `run.py` under m_peek (RESULTS_DIR redirected) regenerated leaked folds (`oos_auc=0.7315`, n_oos=1267, 5 folds, verdict SELECTION) and then pytest failed **only** `test_purge_embargo_actually_holds`. `test_purge_negative_control_with_weaker_embargo` still **PASSED** because it always builds `comparator="m_10"` (`test_f1.py:108`) and never uses the production comparator.

The lane's own `mutant_runs` (`run.py:1461-1480`, `:1624-1644`) never run pytest: they count `strict_comparator_violations` on named-factory folds and hard-code `failing_tests=["test_purge_embargo_actually_holds"]`.

*Re-check that closes D1:* on a scratch copy, apply m_peek and m_peek_rec to the **binding** comparator (`run.py:438`). `pytest -k purge -v` must FAIL both `test_purge_embargo_actually_holds` and `test_purge_negative_control_with_weaker_embargo` under each of those two mutants (the tests must evaluate the shared strict comparator on folds produced by the code under test, not a committed `result.json` and not a hard-coded `m_10` factory). Clean suite must still pass the three purge tests. Paste the four pytest tails (clean, m_peek, m_peek_rec, m_r1).

**D2 (H2, MAJOR).** `check_result_md.py` is no longer fully vacuous, but two of the four specified mutations still report 0 mismatches.

| Mutation | mismatches | exit |
|---|---:|---:|
| clean | 0/31 | 0 |
| RESULT.md `0.6227→0.9999` | 1/31 (`OOS AUC (primary)`) | 1 |
| RESULT.md `0.6738→0.1111` | **0/31** | **0** |
| result.json `oos_auc→0.8123` | 1/31 | 1 |
| result.json `h1[0]→0.9` | **0/31** | **0** |
| result.json `h1` scalar `0.9` (extra) | crash `TypeError: 'float' object is not subscriptable` at `check_result_md.py:179` | 1 (not a mismatch report) |

Cause: the CI helper takes only the first number after `95% week-cluster CI | [` (`0.5715`, the lower bound). `h1 (≤ 5)` is wired to `n_h1` (208), and the hazard loop compares CI bounds, never the 0.1246 height.

*Re-check that closes D2:* the four specified mutations, each on a scratch copy of `{RESULT.md, result.json, code/check_result_md.py}`, must each print `≥ 1` mismatch (not a crash) and the clean pair must print `0/N`.

**D3 (H4, MINOR).** `RESULT.md` §12 names only `test_purge_embargo_actually_holds` under m_peek / m_peek_rec / m_r1 / m_10, with synthetic `pass=1, fail=1`. It does not name `test_purge_negative_control_with_weaker_embargo`. The H4 repair-table row claims both names. Counts are not from pytest (`run.py:1635-1638`).

*Re-check that closes D3:* after the D1 mutant pytest runs, §12 (generated from the payload, not hand-typed) names both `test_purge_embargo_actually_holds` and `test_purge_negative_control_with_weaker_embargo` as failing under m_peek and m_peek_rec, with the actual pass/fail counts from those pytest tails, plus the clean-run counts.

No frozen number may move while repairing D1–D3.

## EVIDENCE

### Round-2 sha (first action)

```
cc1fbc620142f33f355a7b4027e397211294396055a11dff91e490aac381f485  .../results_prev/F1_r2/result.json
8315d69e2cd923513b959c255907c1c426a4dc08da33283eebc8d21d791c089b  .../results/F1/result.json
```

### Known-fact pytest / skip explanation

Direct pytest on live `results/F1/code` (hashes.txt present):

```
FAILED .../test_f1.py::test_hashes_txt_checksum_passes - AssertionError: shasum -c failed: ['data/prophet/ledger.jsonl: FAILED']
1 failed, 15 passed in 5.64s
```

That single local failure is the data-vintage pin of `data/prophet/ledger.jsonl` (this checkout is newer than host head `052e02d085b0`). All other 15 tests passed, including the three purge tests, byte-stability, schema, H10, and `check_result_md` clean.

Lane `result.json["tests"]` = `"14 passed, 2 skipped"` and `test_summary.txt` matches. Whole explanation: `run.py:1613-1615` unlinks `hashes.txt` before pytest, so `test_f1.py:244` (`test_hashes_path_is_repo_relative`) and `test_f1.py:264` (`test_hashes_txt_checksum_passes`) `pytest.skip("hashes.txt not yet generated")`. Then hashes are written LAST (`run.py:1692-1693`). No other tests skip. Honest.

### H1 mutants

Binding line found at `run.py:438`. Mutations applied only on `SCR/<mutant>/code/run.py`:

- m_peek: `return as_of_dates < (ws_dt64 + np.timedelta64(5, "D"))`
- m_peek_rec: `cutoff_dt = np.busday_offset(ws_dt64, -22, ...); return as_of_dates <= (cutoff_dt + np.timedelta64(14, "D"))`
- m_r1: `return end_dates <= ws_dt64`

Full suite (`python3 -m pytest SCR/<copy>/code -q -p no:cacheprovider`):

| copy | summary | failing tests |
|---|---|---|
| m_peek | 3 failed, 13 passed in 6.39s | `test_hashes_txt_checksum_passes` (vintage); `test_result_json_byte_stable_across_runs` (binding re-run sha `c651d634…` vs live `7c4d56a3…`); `test_result_md_matches_result_json` (copy has no sibling RESULT.md — copy-only artifact) |
| m_peek_rec | 3 failed, 13 passed in 6.21s | same three; stability rerun sha `9ffa641c…` |
| m_r1 | 3 failed, 13 passed in 5.62s | same three; stability rerun sha `2dfadf3a…` |
| clean_copy | 2 failed, 14 passed in 5.51s | hashes vintage + check_result_md missing-sibling only; **byte-stability passed** |

Named purge tests (`pytest -k purge -v`):

```
m_peek:     test_purge_embargo_actually_holds PASSED
            test_purge_negative_control_with_weaker_embargo PASSED
            test_purge_forward_peek_mutants_fail PASSED
            3 passed, 13 deselected in 3.99s
m_peek_rec: all three PASSED (3.95s)
m_r1:       all three PASSED (3.94s)
clean_copy: all three PASSED (3.96s)
```

**Required:** `test_purge_negative_control_with_weaker_embargo` must FAIL under m_peek and m_peek_rec. It did not.

### H2 checker mutations

Each tree is `SCR/h2_*/{RESULT.md,result.json,code/check_result_md.py}`.

```
=== H2 CLEAN ===
check_result_md: 0/31 mismatches (all 31 labeled numbers present)
exit=0

=== H2 MD 0.6227->0.9999 ===
check_result_md: 1/31 mismatches
  {'label': 'OOS AUC (primary) | **', 'key': 'entry_model.oos_auc', 'md_val': 0.9999, 'rj_val': 0.6227445818504856}
exit=1

=== H2 MD 0.6738->0.1111 ===
check_result_md: 0/31 mismatches (all 31 labeled numbers present)
exit=0

=== H2 RJ oos_auc->0.8123 ===
check_result_md: 1/31 mismatches
  {'label': 'OOS AUC (primary) | **', 'key': 'entry_model.oos_auc', 'md_val': 0.6227, 'rj_val': 0.8123}
exit=1

=== H2 RJ h1[0]->0.9 ===
check_result_md: 0/31 mismatches (all 31 labeled numbers present)
exit=0
```

`0.6738` count in RESULT.md before replace: 4. After: 0. Still 0 mismatches.

### H3 fail-closed (scratch m_peek `run.py`)

Copied m_peek code to `SCR/h3/`, redirected `RESULTS_DIR` and pytest path to that tree, skipped the in-process named-factory dry-runs, ran `python3 SCR/h3/code/run.py` from the worktree. Live `result.json` sha before=after `8315d69e…`.

```
== pytest (clean) ==
{"label": "clean", "n_pass": 13, "n_fail": 1,
 "failing_tests": ["test_purge_embargo_actually_holds"],
 "summary": "1 failed, 13 passed, 2 skipped", "returncode": 1}
FAILED: clean_run returncode=1 n_fail=1
```

Scratch `result.json`: `status=TESTS_FAILED`, `tests="1 failed, 13 passed, 2 skipped"`, `verdict=SELECTION`, `oos_auc=0.7315118683689984`, `n_oos=1267`, 5 folds. Exit code 1. `test_summary.txt` starts with `TESTS_FAILED`.

This is the round-2 m_peek science (AUC 0.7315 / SELECTION) with the new fail-closed path. Negative control still did not fail (13 passed includes it). H3 itself is closed; it does not close D1.

### H4 payload vs pytest

Delivered `RESULT.md:225-228`:

```
- m_peek ...: pass=1, fail=1, failing=['test_purge_embargo_actually_holds']
- m_peek_rec ...: pass=1, fail=1, failing=['test_purge_embargo_actually_holds']
- m_r1 ...: pass=1, fail=1, failing=['test_purge_embargo_actually_holds']
- m_10 ...: pass=1, fail=1, failing=['test_purge_embargo_actually_holds']
```

`run.py:1635-1638` always writes that single name when `n_violations > 0`. Real m_peek pytest (H3 scratch) failing list is the same single name; the negative control is not in it.

### H5 / H6

```
grep -c "7.4%"  RESULT.md  → 3     # substring of "17.4%"
grep -c "17.4%" RESULT.md  → 3     # ≥ 2
grep -nE '[^0-9]7\.4%'     → NONE
percent tokens: 3 × 17.4%
```

No standalone stale `7.4%`. G8 row and ANSWER FIRST both say 17.4% and 35/33. `grep -n "four per-week AUCs"` / `"per-week AUCs are the source"` → none.

`entry_model.bootstrap`: `n_draws_valid=1000`, `n_draws_ge_065=174` (17.4%), `distinct_at_1e10=35`, `distinct_at_1e4=33`, `multiset_max=35`. H6 permitted this count to change vs round 2's prose "33".

### H7 / H8 / skip / C1 pin

`hashes.txt` (no blank line, newline-terminated, 12 lines):

```
# git hash: 052e02d085b01f29baf499357e224c836d8eb224
61bb8cc6…  data/us_board_ledger/retro_grades.parquet
3167509f…  data/prophet/ledger.jsonl
9361dbf0…  results/C1/rotation_state_daily.parquet
d51c5708e385849231a0f5193a06c2586c546b87c142b262ff3bafa1dba32749  results/C1/result.json
3234b87f…  results/F1/code/run.py
52cc8293…  results/F1/code/test_f1.py
7f747be0…  results/F1/code/check_result_md.py
8315d69e…  results/F1/result.json
69c580cd…  results/F1/RESULT.md
9028df01…  results/F1/test_summary.txt
```

`shasum -a 256 -c results/F1/hashes.txt` from repo root: 9 `: OK`, `data/prophet/ledger.jsonl: FAILED` (local vintage), `WARNING: 1 computed checksum did NOT match`, **0** `improperly formatted`. C1 pin `d51c5708…` is the C1 round-3 record.

Write order in `run.py __main__`: unlink hashes → (host: named-factory dry-runs) → `build_payload` → write result.json+RESULT.md → pytest → on fail TESTS_FAILED+exit 1; on pass fold summary without `\s+in\s+\d+\.\d+s` → rewrite result.json+RESULT.md → `write_hashes_txt` LAST.

Stability test (`test_f1.py:283-323`): two in-process `purged_oos_logistic` runs; sha256 of `json.dumps(fold_records, indent=2, default=str)`. Clean copy: passed (live fold sha `7c4d56a3801c91019135422c6d6b9641423189a03bb725ec139aa94394eb1800` matched rerun). RESULT.md text says "compares result.json shas"; the test compares fold_records. Allowed fallback ("say which") is in the test docstring, not in §12.

### H9

Literal `as_of <= week_start - 22 sessions`: 5 times in RESULT.md (ANSWER FIRST, §3 embargo row, SEAT RULING row, H9 row, deviations), 3 times in result.json (`embargo_rule`, `embargo_rule_alt` exactly that string, deviations[0]).

### H10

`c1_status()` returns UNKNOWN on missing/corrupt JSON; `c1_available()` is `status == "OK"`; `join_c1` and `ledger_denom` both refuse anything but OK (parquet existence is not enough). Live `prophet_ledger.c1_available=false`, `c1_status=BROKEN`. `test_c1_status_fails_closed_on_missing` passed in the live 15-passed set (monkeypatches `run.C1_RESULT_JSON`, asserts `join_c1` → `c1_available is False`).

### Frozen-number leaf diff (r2 vs r3)

Walk of every JSON leaf: `n_leaves_r2=191`, `n_leaves_r3=229`, `only_r2=0`, `only_r3=38`, `changed=3`.

Changed leaves (all wording / provenance, **no moved number**):

| leaf | r2 | r3 | class |
|---|---|---|---|
| `entry_model.embargo_rule` | `… equivalently as_of <= np.busday_offset(week_start, -22, …)` | `… equivalently as_of <= week_start - 22 sessions` | H9 wording |
| `deviations[0]` | same embargo paraphrase | H9 literal | wording |
| `tests` | `"15 passed"` | `"14 passed, 2 skipped"` | H7 skip honesty |

New r3-only leaves: `entry_model.embargo_rule_alt`, `entry_model.bootstrap.{distinct_at_1e10=35, distinct_at_1e4=33, multiset_max=35, n_draws_ge_065=174, n_draws_valid=1000}`, and the whole `mutant_runs.*` tree. Bootstrap 35/33 is the one number H6 allowed to change. `n_draws_ge_065=174` is the 17.4% already in round-2 prose.

Unchanged frozen values (r2 == r3):

- OOS AUC `0.6227445818504856` → 0.6227
- CI `[0.5715116526475553, 0.6737902559867878]` → [0.5715, 0.6738]
- n_oos 860 / n_test_weeks 4
- in-sample `0.7092234794623646` → 0.7092
- sensitivity `0.576850936082639` `[0.5274273370517502, 0.6497031768817177]` n=1267 / 5
- hazards `0.12462552426602756` / `0.15263518138261464` / `0.3158319870759289` on 208 / 223 / 391
- mix `0.14841849148418493` / `0.681265206812652` / `0.170316301703163` n_sev 822
- n_removed_strict 138; prose 24/31/40/43 per fold W32..W35
- fold n_train/n_test 73/93, 138/255, 227/363, 359/149; cutoffs 07-01 / 07-09 / 07-16 / 07-23

## GAPS

- Host-side `shasum -a 256 -c hashes.txt` with **0** non-OK lines was not reproduced here: local `data/prophet/ledger.jsonl` is a newer vintage than head `052e02d085b0` (known; 1 FAILED). F1 outputs and C1 pins check OK. Did not `git show 052e02d085b0:data/prophet/ledger.jsonl` into a private overlay because the vintage failure is already identified as the only hash miss.
- Did not re-run a **second** full `run.py` to reprint two byte-identical `result.json` shas (H7 "print the two shas"). The stability test on the clean copy showed identical fold_records shas `7c4d56a3…`.
- H3 demonstration skipped the in-process named-factory dry-runs (`_run_mutant_pytest`) and redirected RESULTS_DIR/pytest; it did not mutate the live tree. Live sha was snapshotted before and after.
- Did not run a full scratch `run.py` under m_peek_rec / m_r1 (purge pytest on those copies already showed the leak tests pass; H3 only required m_peek).
- H10 test asserts `join_c1` `c1_available is False`, not `ledger_denom()["c1_available"]`. Both call `c1_status()`; not re-tested via `prophet_ledger` directly.
- `check_result_md.py` sibling-path failure when pytest is pointed at a code-only copy is a reviewer-copy artifact, not a lane defect.

## DEVIATIONS

- Mutants were applied to `_make_label_realisation_comparator`'s `return end_dates < ws_dt64` (`run.py:438`), the current equivalent of round-2 `run.py:439`, not by switching the default `comparator=` string. Named factories `m_peek` / `m_peek_rec` / `m_r1` were left intact so the packet's "mutate the embargo comparison" re-check is what ran.
- H2 extra probe: `hazard.overall.h1 = 0.9` (scalar) in addition to `h1[0]=0.9`. Scalar crashes the checker; not one of the four required mutations.
- H3 scratch `run.py` skipped the four named-factory dry-runs to keep the fail-closed demonstration inside a few minutes; pytest path and RESULTS_DIR were redirected into `SCR/h3/` so live `results/F1/` was not written (live sha identical).
- Naive `grep -c "7.4%"` is 3 because it is a substring of `17.4%`. Verdict uses the standalone pattern; the stale figure is gone.
- All scratch work is under `SCR=.../scratchpad/review/F1_r3`. No tracked file, no `results/` write, no git write, no network.
