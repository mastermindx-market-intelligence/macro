# Lane F1 — Entry vs management decomposition on the served Prophet ledger

**Data class.** The price stores are FINAL-VINTAGE (as observed today, not point-in-time) and the universes are SURVIVOR-SELECTED (current membership only). The retro-grade ledger is the served retro_grade panel; C1's rotation state table is BROKEN on its AR(1)-21 control (corr=-0.04 vs >0.5; per C1 result.json `controls.status`=`BROKEN`), so all by-rotation tables are reported as `INSUFFICIENT SUPPORT (C1 BROKEN)`.

**ANSWER FIRST.** On the served retro-grade ledger, with the **binding** seat-ruling embargo (label-realisation comparison: training as_of kept iff `busday_offset(as_of, 21, forward, holidays=NYSE) < week_start`, equivalently `as_of <= week_start - 22 sessions`) the lever is **MIXED** under the pre-declared rule: purged OOS AUC = **0.6227** (95% week-cluster CI [0.5715, 0.6738], built on **4 week clusters** / 860 OOS episodes), deteriorated-after-non-negative-H10 share = **0.1484** (CI [0.129, 0.174]), immediate-failure share = **0.6813**. Both gate conditions fail (MANAGEMENT needs AUC ≤ 0.55 AND det > 0.50; SELECTION needs AUC ≥ 0.65 AND imm > 0.50). IMMEDIATE failure dominates: it exceeds 0.50 in every one of the 1000 week-cluster resamples; the OOS AUC 95% CI upper bound (0.6738) straddles the 0.65 cut, and 17.4% of the 1000 bootstrap draws reach ≥ 0.65 — the bootstrap support has 35 distinct AUC values at 1e-10 (and 33 at 1e-4) across 4 clusters (multiset maximum = 35). The primary (21-session strict) and the sensitivity (22-cal-day) rows use different test sets because the binding embargo drops W31's 407 OOS episodes (n_train=0). The product implication is descriptive only: **no management lever is supported; the selection-vs-mixed question needs more test weeks (forward log).**

## 1. Honest-N

| Metric | Value |
|---|---:|
| Episodes kept (all 3 horizons non-null) | **1669** |
| Distinct as_of dates | **28** |
| Distinct as_of ISO weeks | **9** |
| Distinct tickers | **661** |
| Severe (h21 excess ≤ −0.07 OR mae ≤ −0.07) | **822** |
| Target (excess_h21 ≥ +0.07 and not SEVERE) | **219** |
| Neither | **628** |

Episodes by `rank_by`:

| rank_by | Count |
|---|---:|
| bottoming-alignment | 227 |
| confluence | 582 |
| us_prophet_v1 | 93 |
| us_prophet_v2 | 255 |
| us_prophet_v3 | 512 |

## 2. Drop accounting (by reason)

| Reason | n | Note |
|---|---:|---|
| Rows in lanes buy+leaders | 7334 | pre-filter |
| Unique episodes | 3167 | after (ticker, as_of, rank_by) dedup |
| Episodes kept (all 3 horizons non-null) | **1669** | working panel |
| Episodes dropped — horizons incomplete | 1498 | of which: |
| ↳ Structural — conviction family (rank_by=conviction, 2026-06-15..2026-06-22, no h21) | 437 | silently absent from panel |
| ↳ Structural — bottoming-alignment family (2026-06-23..2026-06-24, no h10/h21) | 174 | silently absent from panel |
| ↳ Structural total (437 + 174) | 611 | both windows cluster 2026-06-15..06-24 |
| ↳ Right-censored us_prophet_v3 (2026-08-26..2026-09-17, no h21 yet) | 886 | served vintage cuts off h21 |
| ↳ Mid-panel WBS confluence (2026-07-27, has h5/h10, no h21) | 1 | label not yet realised |
| ↳ Other-censored (uncategorised) | 0 | should be 0; if non-zero the audit list is incomplete |

Within the kept panel, missing covariate cells (NOT off_high/score):

| Covariate | n missing |
|---|---:|
| archetype | 137 |
| quad_hard_label | 34 |
| vol_regime | 34 |
| off_high | 0 |
| score | 0 |

## 3. Entry-state model — purged OOS logistic (binding: 21-session label horizon, strict-before-week-start)

| Metric | Value |
|---|---:|
| Embargo (label horizon, NYSE sessions) | **21** (binding: keep iff `busday_offset(as_of, 21, forward) < week_start`, equivalently `as_of <= week_start - 22 sessions`) |
| Sensitivity embargo (calendar days, labelled) | 22 calendar-day wholesale pricing (sensitivity only, NOT binding) |
| n_oos episodes | 860 |
| n_test_weeks | **4** (derived from fold_records, not hard-coded) |
| OOS AUC (primary) | **0.6227** |
| 95% week-cluster CI | [0.5715, 0.6738] |
| In-sample AUC | 0.7092 |
| Removed by binding rule vs old -21-session rule (138 expected) | 138 |
| Sensitivity OOS AUC (22-cal-day, NOT binding) | 0.5769 |
| Sensitivity 95% CI | [0.5274, 0.6497] |
| Sensitivity n_oos | 1267 |
| Sensitivity n_test_weeks | 5 |

### 3.1 Per-fold records (the CI is built on these `n_test_weeks` clusters)

| Test week | week_start | train_cutoff | max_train_as_of | n_train | n_test | per-week AUC |
|---|---|---|---|---:|---:|---:|
| 2026-W32 | 2026-08-03 | 2026-07-01 | 2026-07-01 | 73 | 93 | 0.6549 |
| 2026-W33 | 2026-08-10 | 2026-07-09 | 2026-07-09 | 138 | 255 | 0.6818 |
| 2026-W34 | 2026-08-17 | 2026-07-16 | 2026-07-15 | 227 | 363 | 0.5838 |
| 2026-W35 | 2026-08-24 | 2026-07-23 | 2026-07-21 | 359 | 149 | 0.5317 |

### 3.2 Top three coefficients (in-sample fit, names → β)

| Coefficient | β |
|---|---:|
| sector_etf=XLE | -1.0519 |
| sector_etf=XLY | +1.0152 |
| rank_by=bottoming-alignment | -0.9252 |

Coefficients are L2-penalised IRLS with λ=1.0 (intercept unpenalised); standardisation and one-hot encoding are fit on each training fold only, per fold.

## 4. Hazard model — discrete-time, first severe-bucket

| Bucket | n at h | height (×h<sub>i</sub>) | 95% week-cluster CI |
|---|---:|---:|---|
| h1 (≤ 5) | 208 | **0.1246** | [0.0599, 0.1771] |
| h2 (6–10 \| not severe by 5) | 223 | **0.1526** | [0.1257, 0.1917] |
| h3 (11–21 \| not severe by 10) | 391 | **0.3158** | [0.2593, 0.3661] |
| none | 847 | — | — |

`h3` is the largest conditional hazard — episodes surviving h10 still face a ~32% chance of going severe within h21. This is the path-mode signal the entry-state model is NOT picking up.

### Hazard by rotation_tercile

| tercile | n | h1 | h2 | h3 |
|---|---:|---:|---:|---:|
| fast | — | — | — |
| mid | — | — | — |
| persistent | — | — | — |

> All three rotation_tercile rows = `INSUFFICIENT SUPPORT (C1 BROKEN)`.
## 5. Attribution split (among SEVERE episodes; n = 822)

| Bucket | share | 95% week-cluster CI |
|---|---:|---|
| deteriorated after non-negative H10 (excess_h10 ≥ 0) | **0.1484** | [0.129, 0.174] |
| immediate failure (excess_h5 < 0 AND excess_h10 < 0) | **0.6813** | [0.607, 0.742] |
| other | **0.1703** | — |

Counts: deteriorated=122, immediate=560, other=140 (sum = 822 = n_severe).

### 5.1 Attribution by `rank_by` (with CIs; null where n_clusters < 2)

| rank_by | n_severe | n_clusters | deteriorated | deteriorated CI | immediate | immediate CI |
|---|---:|---:|---:|---|---:|---|
| bottoming-alignment | 72 | 3 | 0.2639 | [0.182, 0.333] | 0.5556 | [0.417, 0.731] |
| confluence | 303 | 3 | 0.1353 | [0.092, 0.190] | 0.7162 | [0.429, 0.774] |
| us_prophet_v1 | 43 | 1 | 0.0930 | null | 0.6512 | null |
| us_prophet_v2 | 132 | 1 | 0.1591 | null | 0.6894 | null |
| us_prophet_v3 | 272 | 2 | 0.1360 | [0.109, 0.150] | 0.6765 | [0.622, 0.783] |

### 5.2 Attribution by `rotation_tercile`

All values = `INSUFFICIENT SUPPORT (C1 BROKEN)`.

## 6. Prophet ledger denominator (`ledger.jsonl`, joined by `signal_date`)

### 6.1 By outcome (counts + means + medians)

| outcome | n | median_stock_result_pct | mean_stock_result_pct | median_days_held | mean_days_held |
|---|---:|---:|---:|---:|---:|
| EXPIRED | 116 | -2.0503 | -0.3992 | 45.0 | 45.4 |
| INVALIDATED | 69 | -8.2630 | -10.3860 | 19.0 | 20.2 |
| NO_ENTRY | 39 | null | null | 45.0 | 45.6 |
| T1_HIT | 43 | +13.9714 | +17.1152 | 17.0 | 19.2 |
| T2_HIT | 3 | +13.0271 | +71.6744 | 8.0 | 7.7 |

`stock_result_pct` is reported as null (not NaN) for NO_ENTRY because there is no stock-side result. The enum adds NO_ENTRY per repair-block item 8.

### 6.2 By outcome × `rotation_tercile`

All rows = `INSUFFICIENT SUPPORT (C1 BROKEN)`.

## 7. Verdict (pre-declared rule)

> MANAGEMENT iff OOS AUC ≤ 0.55 AND share 'deteriorated after non-negative H10' > 0.50 among SEVERE.
> SELECTION iff OOS AUC ≥ 0.65 AND share 'immediate failure' > 0.50.
> MIXED otherwise.

Under the **binding** 21-NYSE-session-strict embargo:

- OOS AUC = **0.6227** → not ≤ 0.55 (MANAGEMENT condition fails).
- deteriorated share = **0.1484** → not > 0.50 (MANAGEMENT condition fails).
- OOS AUC = 0.6227 → not ≥ 0.65 (SELECTION condition fails).
- immediate share = 0.6813 → > 0.50 in every resample, BUT AUC < 0.65 → SELECTION condition fails.
- → **MIXED**.

Under the **sensitivity** 22-calendar-day embargo (labelled, NOT binding):

- sensitivity OOS AUC = 0.5769 on 1267 OOS episodes across 5 test weeks.

**SMALL-N caveat.** The verdict rests on **4 test weeks / 860 OOS episodes / 822 SEVERE**. The 95% CI is built on 4 week clusters, not 9 — per spec the cluster unit is the as_of ISO week; only 4 weeks had both classes in the test fold. Per-week AUC variance is wide, and a single re-stamp could move the verdict. The verdict is descriptive; nothing is promoted here.

## 8. SPEC AMENDMENT + SEAT RULING + G1..G8 + H1..H10 + P1..P4 (each FIXED with file:line)

| # | Severity | Description | Status | file:line |
|---|---|---|---|---|
| SPEC AMENDMENT | — | Training h21 labels realise strictly before the test week: keep iff `busday_offset(as_of, 21, forward) < week_start`. 22-calendar-day rule kept as labelled sensitivity. | FIXED | run.py:464 |
| SEAT RULING | — | Switched purge from literal -21 sessions (`as_of + 21 sessions == week_start`, labels inside test week) to label-realisation comparison (`busday_offset(as_of, 21, forward) < week_start`, equivalently `as_of <= week_start - 22 sessions`). 138 training rows (24/31/40/43 per fold) excluded by the new boundary; round-1 numbers reported alongside the new primary. | FIXED | run.py (constant), run.py (label-realisation comparator), run.py (max_train_as_of) |
| G1 | MAJOR | Purge test reads ACTUAL `fold_records` from result.json (week_start, train_cutoff, max_train_as_of, n_train, n_test) with ONE strict comparator `busday_offset(max_train_as_of, 21, forward) < week_start`; negative control on a 10-session embargo fold FAILS the same predicate; forward-peek mutants (train-end-of-week, cutoff+14d) included. | FIXED | test_f1.py, run.py (strict_comparator_violations), run.py (comparator factories) |
| G2 | MAJOR | RESULT.md is generated by `render_result_md` from the same payload dict as result.json; `code/check_result_md.py` parses every LABELED number in RESULT.md and matches it to result.json at rendered precision (mutations on either side produce >= 1 mismatch). | FIXED | render_result_md, code/check_result_md.py |
| G3 | MAJOR | ONE `c1_status()` reads `results/C1/result.json` `controls.status`; both `join_c1` and `ledger_denom` use it; `prophet_ledger.c1_available=False`; every by-rotation / by-outcome-x-rotation block carries `INSUFFICIENT SUPPORT (C1 BROKEN)`. | FIXED | run.py (c1_status), run.py (join_c1), run.py (ledger_denom) |
| G4 | MINOR (provenance) | repo_head and pytest summary WITHOUT wall-clock timing folded into payload before any hash; result.json written ONCE after pytest; hashes.txt written LAST; `shasum -a 256 -c hashes.txt` from repo root passes with 0 non-OK lines; result.json sha256 identical across two consecutive runs. | FIXED | run.py (write order), run.py (wall-clock strip) |
| G5 | MINOR | 887-censored bucket split into `right_censored_us_prophet_v3_2026_08_26_to_09_17` (886), `mid_panel_wbs_confluence_2026_07_27` (1, WBS), and `other_censored` (0). Conviction range corrected from 06-15..06-24 to **06-15..06-22**. | FIXED | build_episodes |
| G6 | MINOR | Stale 'week-cluster count (5)' text replaced; citations in §8 emitted from the table here (file:line points at lines containing the change). | FIXED | render_result_md §8 table |
| G7 | MINOR | `_ci_or_null` returns `null` plus `n_clusters` when n_clusters < 2; applied to attribution `by_rank_by` (v1/v2 emit null because n_clusters=1 each); by_rotation tables emit `INSUFFICIENT SUPPORT (C1 BROKEN)` per G3. | FIXED | run.py (_ci_or_null), run.py (per-rank CIs) |
| G8 | (answer wording) | ANSWER FIRST names MIXED with the small-N caveats — IMMEDIATE > 0.50 in every resample, AUC CI upper bound straddles 0.65, 17.4% of 1000 draws reach ≥ 0.65, 35 distinct support points at 1e-10 / 33 at 1e-4 (multiset max 35), primary vs sensitivity use different test sets — and the product implication as 'no management lever is supported; the selection vs mixed question needs more test weeks (forward log)'. | FIXED | render_result_md ANSWER FIRST paragraph |
| H1 | MAJOR | test_f1.py mutants evaluate the SHARED strict comparator on fold records produced by the configured comparator (binding/m_peek/m_peek_rec/m_r1/m_10). `test_purge_embargo_actually_holds` PASSES on the binding fold and FAILS on each mutant fold; `test_purge_negative_control_with_weaker_embargo` reports >=1 violation on every mutant; clean suite passes. | FIXED | test_f1.py, run.py (comparator factories + strict_comparator_violations) |
| H2 | MAJOR | check_result_md.py parses each LABELED number in RESULT.md (ANSWER FIRST numbers, fold table, repair table, hazards, attribution, sensitivity) and compares to SPECIFIC result.json key at rendered precision; RESULT.md mutations (0.6227→0.9999, 0.6738→0.1111) and result.json mutations (oos_auc=0.8123, h1=0.9) each produce >= 1 mismatch. | FIXED | code/check_result_md.py |
| H3 | MAJOR | run.py fails closed: when any pytest fails, result.json status = `TESTS_FAILED` (never DELIVERED), run.py exits non-zero. Demonstrated on m_peek. | FIXED | run.py main() |
| H4 | MINOR | RESULT.md §12 names the failing tests under each mutant (test_purge_embargo_actually_holds and test_purge_negative_control_with_weaker_embargo), generated from mutant runs performed in H1. | FIXED | render_result_md §12, run.py (mutant_runs) |
| H5 | MINOR | The G8 row renders 17.4% (pct>=0.65 of 1000 draws) and 35 distinct support points at 1e-10 (from payload); no stale fraction remains in the repair table. | FIXED | render_result_md §8 G8 row |
| H6 | MINOR | Distinct bootstrap support reported at 1e-10 (35) and 1e-4 (33); multiset maximum = 35 (C(7,4) over 4 test weeks with 7 averaged distinct week-AUC inputs); the per-week-AUC sentence is deleted from ANSWER FIRST and §8. | FIXED | run.py purged_oos_logistic (bootstrap counts), render_result_md (no per-week-AUC sentence) |
| H7 | MINOR | Write order: (1) payload + result.json + RESULT.md, (2) pytest, (3) tests summary folded into payload WITHOUT wall-clock timing, (4) hashes.txt LAST; byte-stability test re-runs the deterministic core (fit + bootstrap) on a scratch copy and compares result.json shas. | FIXED | run.py main(), run.py _strip_wall_clock |
| H8 | NIT | hashes.txt has no blank line; `shasum -a 256 -c hashes.txt` from repo root prints 0 non-OK lines. | FIXED | run.py main() hashes_writer |
| H9 | NIT | Literal string `as_of <= week_start - 22 sessions` appears >= 1 time in result.json (`entry_model.embargo_rule_alt`) and >= 1 time in RESULT.md (§3 row). | FIXED | run.py (embargo_rule_alt), render_result_md §3 |
| H10 | NIT | c1_status() returns OK / BROKEN / UNKNOWN; only OK is treated as available. Missing results/C1/result.json yields prophet_ledger.c1_available == false (test added). | FIXED | run.py c1_status, run.py c1_available, test_f1.py test_c1_status_fails_closed_on_missing |
| P1 | MAJOR | Three purge tests call the production fold builder with `_make_label_realisation_comparator` on a synthetic 4-role panel and assert exact included/excluded label-id sets. Mutant pytest runs via subprocess on scratch copies of code/ with the BINDING_CMP line mutated; failing names come from pytest output. | FIXED | test_f1.py:99, run.py:521, run.py:1466 |
| P2 | MAJOR | check_result_md.py parses BOTH CI bounds of `95% week-cluster CI \| [lo, hi]`, binds `h1 (≤ 5)` to hazard.overall.h1[0] (height), compares every hazard height, and reports a scalar h1 as a schema MISMATCH (no TypeError). | FIXED | check_result_md.py:4, check_result_md.py:307 |
| P3 | MINOR | RESULT.md §12 is generated from `mutant_runs` pytest payload (failing test names and pass/fail counts from pytest output, never hard-typed). | FIXED | run.py:1472 |
| P4 | MINOR | Frozen science leaves unchanged vs round 3; hashes.txt LAST; 0 skips on this host; provenance.host recorded. | FIXED | run.py:26, run.py:95 |

## 9. Deviations

- **SEAT RULING (binding, supersedes SPEC AMENDMENT).** Round-1 used the -21-session literal `as_of + 21 sessions == week_start` (labels realises at test-week Monday, INSIDE the test week). Round-2 uses the label-realisation comparison `busday_offset(as_of, 21, forward) < week_start`, equivalently `as_of <= week_start - 22 sessions`. 138 training rows (24/31/40/43 per fold) are removed by the new boundary. The 22-calendar-day rule is kept as the labelled sensitivity row only.
- The 2026-07-27 confluence row for WBS is the lone right-censored entry inside the working panel window; it has h5 and h10 but no h21.
- Conviction family spans 2026-06-15..2026-06-22 (NOT ..2026-06-24); bottoming-alignment family 2026-06-23..2026-06-24 is a separate window. Both windows cluster in the earliest served period.
- The OOS CI is built on 4 week clusters (not 9); only 4 weeks had both classes in the test fold under the binding embargo. W31 is skipped because the strict-before cutoff excludes every training row.

## 10. Gaps

- C1 is BROKEN on its AR(1)-21 control; all by-rotation analysis is replaced with `INSUFFICIENT SUPPORT (C1 BROKEN)`. Rotation covariates do not enter the entry-state model.
- **Conviction family (rank_by=conviction, as_of 2026-06-15..2026-06-22, 437 episodes) is silently absent** from the panel because those rows do not have an h21 outcome (only h5/h10). Bottoming-alignment family 174 episodes (as_of 2026-06-23..2026-06-24) likewise has only h5. Both families are clustered in the earliest served window; their absence is structural, not stochastic.
- The verdict rests on **4 test weeks / 860 OOS episodes / 822 SEVERE**, and the 95% CI is built on 4 week clusters. Per-week AUCs vary; the verdict is descriptive, not a promotion.
- The 9-distinct-as_of-weeks in the working panel includes burn-in weeks (the first 5) that do not enter the OOS evaluation because the training set would be too small under the strict-before embargo.
- The Prophet ledger's T2_HIT bucket has only 3 rows — medians are unstable.

## 11. Repo head

`052e02d085b01f29baf499357e224c836d8eb224`

## Provenance

- hostname: `m2studio`
- python: 3.14.7 (`/opt/homebrew/opt/python@3.14/bin/python3.14`)
- pandas 3.0.5 / numpy 2.5.2 / pyarrow 25.0.1 / scipy 1.18.0 / pytest 9.1.1

## 12. Tests

```
17 passed
```

**Clean run** (binding comparator, live code/): pass=17, fail=0, skip=0.

Clean pytest tail:
```
17 passed
```

**Mutant pytest (P1)** — scratch copies of `code/` with the production binding line `return end_dates < ws_dt64` mutated; failing test names and pass/fail counts are parsed from pytest output (never hard-typed):

- m_peek (`as_of < week_start + 5 calendar days`): pass=10, fail=5, failing=['test_purge_embargo_actually_holds', 'test_purge_negative_control_with_weaker_embargo', 'test_purge_forward_peek_mutants_fail', 'test_result_json_byte_stable_across_runs', 'test_result_md_matches_result_json']

m_peek pytest tail:
```
5 failed, 10 passed, 2 skipped
FAILED test_purge_embargo_actually_holds
FAILED test_purge_negative_control_with_weaker_embargo
FAILED test_purge_forward_peek_mutants_fail
FAILED test_result_json_byte_stable_across_runs
FAILED test_result_md_matches_result_json
```

- m_peek_rec (`as_of <= cutoff + 14 calendar days`): pass=10, fail=5, failing=['test_purge_embargo_actually_holds', 'test_purge_negative_control_with_weaker_embargo', 'test_purge_forward_peek_mutants_fail', 'test_result_json_byte_stable_across_runs', 'test_result_md_matches_result_json']

m_peek_rec pytest tail:
```
5 failed, 10 passed, 2 skipped
FAILED test_purge_embargo_actually_holds
FAILED test_purge_negative_control_with_weaker_embargo
FAILED test_purge_forward_peek_mutants_fail
FAILED test_result_json_byte_stable_across_runs
FAILED test_result_md_matches_result_json
```

- m_r1 (`end_dates <= week_start`): pass=10, fail=5, failing=['test_purge_embargo_actually_holds', 'test_purge_negative_control_with_weaker_embargo', 'test_purge_forward_peek_mutants_fail', 'test_result_json_byte_stable_across_runs', 'test_result_md_matches_result_json']

m_r1 pytest tail:
```
5 failed, 10 passed, 2 skipped
FAILED test_purge_embargo_actually_holds
FAILED test_purge_negative_control_with_weaker_embargo
FAILED test_purge_forward_peek_mutants_fail
FAILED test_result_json_byte_stable_across_runs
FAILED test_result_md_matches_result_json
```

**Record-checker mutations (P2)** — scratch copies of {RESULT.md, result.json, code/check_result_md.py}:

- clean pair: n_mismatch=0, exit=0, output=`check_result_md: 0/42 mismatches (all 42 labeled numbers present)`
- RESULT.md 0.6227→0.9999: n_mismatch=1, exit=1, output=`check_result_md: 1/42 mismatches
  {'label': 'OOS AUC (primary) | **', 'key': 'entry_model.oos_auc', 'md_val': 0.9999, 'rj_val': 0.6227445818504856}`
- RESULT.md 0.6738→0.1111: n_mismatch=1, exit=1, output=`check_result_md: 1/42 mismatches
  {'label': 'oos_auc_ci[1]', 'key': 'entry_model.oos_auc_ci[1]', 'md_val': 0.1111, 'rj_val': 0.6737902559867878}`
- result.json oos_auc→0.8123: n_mismatch=1, exit=1, output=`check_result_md: 1/42 mismatches
  {'label': 'OOS AUC (primary) | **', 'key': 'entry_model.oos_auc', 'md_val': 0.6227, 'rj_val': 0.8123}`
- result.json hazard.overall.h1[0]→0.9: n_mismatch=2, exit=1, output=`check_result_md: 2/42 mismatches
  {'label': 'h1 (≤ 5)', 'key': 'hazard.overall.h1.0', 'md_val': 0.1246, 'rj_val': 0.9}
  {'label': 'hazard.h1[0]', 'key': 'hazard.overall.h1[0]', 'md_val': 0.1246, 'rj_val': 0.9}`
- result.json hazard.overall.h1 scalar 0.9: n_mismatch=2, exit=1, output=`check_result_md: 2/40 mismatches
  {'label': 'h1 (≤ 5)', 'key': 'hazard.overall.h1.0', 'md_val': 0.1246, 'rj_val': 0.9, 'reason': 'schema violation: key path did not resolve to a number'}
  {'label': 'h1 (≤ 5)', 'key': 'hazard.overall.h1', 'md_val': 0.1246, 'rj_val': 0.9, 'reason': 'schema violation: expected [height, lo, hi]'}`

Test file: `code/test_f1.py` (P1 production-comparator purge tests on a synthetic 4-role panel; P2 record-checker mutation battery; AUC tied scores; AUC equals brute force; IRLS recovers known coefficients; result.json schema complete; drop accounting matches; n_test_weeks derived from fold; hashes paths repo-relative; fold_records persist max_train_as_of; result.json byte-stable across two runs; RESULT.md numeric match to result.json at rendered precision; hashes.txt shasum passes; c1_status fails closed on missing result.json).
