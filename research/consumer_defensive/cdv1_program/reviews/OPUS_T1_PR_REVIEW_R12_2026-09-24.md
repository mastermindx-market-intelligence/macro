# Opus red-team of PR #7905 — round 12 (content head 82c3df9a0043, 2026-09-24 ~21:20Z)

READ_ONLY Opus reviewer bounded to rulings R71–R75 (`SEAT_RULING_T1_PR_R11_2026-09-24.md`) with R27–R70 carried, under the stated acceptance bar (REJECT only for wrong binds, ruling violations producing wrong binds, frozen-suite integrity failures or materially false commit claims; fail-closed refusals are findings). Recorded verbatim by the seat from the reviewer's report; the reviewer's 50 probe cases are frozen as `tests/test_pg_economic_observations_probes_r11.py` with no case struck (41 RED at 82c3df9a0043, 9 passed). Adjudication: `SEAT_RULING_T1_PR_R12_2026-09-24.md`.

# Opus T1 PR review, round 12: PR #7905 at content head 82c3df9a0043 (rulings R71–R75)

Reviewer: Opus (ROUTE: review / AUDIT, MODE: READ_ONLY). The only file written is the probe file
`scratchpad/opus_r12_probes/test_r12_probes.py`. A temporary `git archive` extract of 0f974054e6b was made under the same
scratch folder to check the commit-message counts, then deleted.

**Acceptance bar applied:** REJECT only for (a) a wrong bind, (b) a ruling violation that produces a wrong bind, (c) a frozen-suite
integrity failure, or (d) a materially false commit-message claim. Fail-closed refusals are findings and do not block.

## VERDICT

`STATUS: REJECT`. Blocking rulings: **R72** (wrong binds W-A and W-B), **R73** (wrong binds W-A ancestors, W-D and W-E), and
**R71** (wrong bind W-C).

- 17 extractor wrong-bind failures across 15 distinct shapes. There are 15 paired validator probes and **the validator ACCEPTS
  every one of them**.
- 8 fail-closed refusals, 1 check on validator surface (a), and 9 controls that pass.
- 13 of the failures are **regressions introduced by 82c3df9a**: they PASS against 0f974054e6b and FAIL at head. They are w01–w06,
  w15, w16, w20×3, f32[1a], f32[roman_ii] and f33.

## Command tails

| Check | Result |
|---|---|
| Eleven suites (original + ten frozen) | `456 passed, 22 skipped in 19.86s` (matches the claim) |
| Companions (disclosure_diff, binding, refresh) | `59 passed in 4.00s` (matches) |
| Frozen r10 suite alone at head | `47 passed, 10 skipped` (matches) |
| 0f974054e6b extract: ten suites | `409 passed, 12 skipped` (confirms R75's correction) |
| 0f974054e6b extract: r10 | `45 failed, 12 passed` (confirms the b64ce018534 claim) |
| My probes at head | **`41 failed, 9 passed`** (0 skipped) |
| My probes at 0f974054e6b | `18 failed, 23 passed, 9 skipped` |

- **Drift loop.** For all ten files, `git diff <freeze> 82c3df9a0043 --stat` is empty. Each file was added in its own freeze commit:
  7804e24a144, 1970ea2b209, fb50fdead46, b371c84fc26, 1c7162e6678, 0cb12b40a96, 6ae7c4cb926, 03a47522942, 8c7ae72c649 and
  b64ce018534.
- **Author loop.** `git log --format=%an` gives exactly `Sol CEO` for all ten files.

Probe command:
`PYTHONPATH="$PWD" venv_t1/bin/python -m pytest scratchpad/opus_r12_probes/test_r12_probes.py -q -p no:cacheprovider --rootdir="$PWD" -c /dev/null -W ignore --tb=short`

## Per-ruling verdicts

| Ruling | Verdict | Evidence |
|---|---|---|
| R71 drawn order | **NOT DISCHARGED** | Wrong binds w09/v09 and w10/v10. Controls c11–c14 pass. |
| R72 forms / prior / calendar year | **NOT DISCHARGED** | Wrong binds w01–w08 with v01–v08. Refusal f31. |
| R73 positive admission / hierarchy / two-layer context | **NOT DISCHARGED** | Wrong binds w03/w04 (ancestor), w15, w16, w17 and w20×3, with v03/v04/v15/v16/v17/v20. Refusals f30 and f34. Controls c18, c19, c21, c22 pass. |
| R74 plain sub-cells | **PARTIAL** | Frozen s30/s31 pass. Refusals f32 for "(1a)", "(ii)", "US$" and "†". "(1a)" and "(ii)" are regressions against 0f97. None of this produces a wrong bind. |
| R75 counts / corrections | **DISCHARGED** | 456+22, 59, r10 47/10, 0f97 409+12 and r10 45F/12P all reproduced. "468 with companions" is 409 + 59. The companions could not run in the extract (fixture tree absent), but the parser is byte-identical, so 59 is inferred there. |

## WRONG BINDS (blocker; all validator-ACCEPTED)

### W-A: a bare PRIOR year is treated as neutral (R72 "prior … neutral in a heading", R73 ancestor rule). Regression in 82c3df9a.

**Cause.**
- `_period_forms` gives a bare year its "prior" verdict at pg_profile.py:650.
- `period_context` returns **None** for a text whose only verdict is "prior" (:675–680). So the text sets no heading context
  (:868–870) and no label context (:877–882).
- `_is_non_results_section` refuses an ancestor only when `_marked_context` is in `_EXCLUDED` (:816), and None is not in it.
- `_admits` lets year-level forms through for the drivers route unless one of them is "fiscal" (:769–771), so "prior" admits.
- `_is_admitted_heading` admits any pure-period text whose context is None (:789).

| id | Text probed | Case | Bound | Validator |
|---|---|---|---|---|
| w01/v01 | `<h2>Net Sales Change Drivers 2025</h2>` + drivers table | Q4 FY2026 | TV 1.0 | ACCEPTS |
| w02/v02 | `<h2>Net Sales Change Drivers</h2><p>2025</p>` + drivers table | Q4 FY2026 | TV 1.0 | ACCEPTS |
| w03/v03 | `<h2>2025 Results</h2><h3>Net Sales Change Drivers</h3>` + drivers table | Q4 FY2026 | TV 1.0 | ACCEPTS |
| w04/v04 | `<h2>2025 Results</h2><h3>Core EPS Reconciliation</h3><p>Core EPS excludes a synthetic restructuring item of 0.10.</p>` | Q4 FY2026 | REC paragraph | ACCEPTS |
| w05/v05 | `<h2>Net Sales Change Drivers 2025</h2>` (non-Q4 identity) | Q3 FY2026 | TV 1.0 | ACCEPTS |

**Construction flaw.** "Prior is neutral" is only correct BESIDE a current form. Substitute rule: a text whose only period forms are
prior-year forms is **foreign** everywhere — heading, label, ancestor and every route including drivers. "prior" stays neutral only
when a scope or year form for the admitted period sits in the same text.

### W-B: the quarter-end CALENDAR year is a current form (R72 plus plan `current_forms`)

**Cause.** Bare years in `current_years = {fiscal_year, current_end.year}` are all treated as current (:636, :650, :694–695). The plan
also adds `str(current_end.year)` as a CURRENT header form (:958). For Q1 and Q2 FY2027 the calendar year is 2026, which is also the
prior fiscal year.

| id | Text probed | Case | Bound | Validator |
|---|---|---|---|---|
| w07/v07 | T1 title + band `"" \| 2027 \| 2026`, row `Diluted Net Earnings per Common Share \| $3.20 \| $3.07` | Q1 FY2027 | **DIL 3.07 (the prior fiscal column)** | ACCEPTS |
| w08/v08 | T1 + `<h2>Segment Results</h2>` + band `2027 \| 2026`, `Beauty \| 5.0% \| 4.0%` | Q1 FY2027 | **Beauty 4.0 (prior column)** | ACCEPTS |
| w06/v06 | T1 + `<h2>Net Sales Change Drivers 2026</h2>` + drivers table | Q1 FY2027 | TV 1.0 | ACCEPTS |

- w07 and w08 are unambiguous. The band itself names fiscal 2027, so "2026" beside it can only be the prior fiscal year. Neither
  column verdict is excluded, and only "2026" matches a current form. These also fail at 0f97, so they are pre-existing and R72 did
  not close them.
- w06 is an internal inconsistency. Control c06 shows the engine reads `Net Sales Change Drivers 2026 vs. 2025` as **foreign**,
  because `_DRIVERS_YEARS` compares to the fiscal year alone (:622). The same heading without "vs. 2025" is read as year-level
  current. This is a regression.

**Substitute.** When a band or heading carries the fiscal year, every other bare year in it is prior, including the calendar year. In
general, a bare year counts as current only as the fiscal year. Also drop `str(current_end.year)` from `current_forms` whenever
`current_end.year != fiscal_year`, or make that form conditional on the fiscal year not appearing in the same band.

### W-C: R71 implementation — an EMPTY first `thead`/`tfoot` is still the first header/footer group (CSS 2.1 §17.2)

**Cause.**
- `_grid` computes `first` only over groups that carry rows (:209–215).
- The parser appends to `row_layout` only on `<tr>`/`<td>` (disclosure_diff.py:757–759, :770–773). Opening a group (:760–765)
  records nothing.
- So `<thead></thead>` or `<tfoot></tfoot>` is invisible, and the SECOND group is promoted. In CSS the empty element still
  generates the first table-header-group or table-footer-group box, so the second one renders in place.

| id | Structure (source order) | Bound | Validator |
|---|---|---|---|
| w09/v09 | `<thead></thead>`, tbody[YEARS, DIL], tbody[`Twelve Months Ended June 30, 2026`], thead[YEARS, `Core EPS \| $12.50 \| $11.90`] | **Core EPS 12.50 (twelve-month)** | ACCEPTS |
| w10/v10 | `<tfoot></tfoot>`, thead[YEARS], tbody[DIL, `Twelve Months Ended June 30, 2026`], tfoot[`Core EPS \| $12.50`], tbody[`Three Months Ended June 30, 2026`, Net Sales] | **Core EPS 12.50**: the second tfoot is sunk below the scope label | ACCEPTS |

- The rule R71 states is correct. The implementation cannot be correct while the "parser untouched" constraint stands: the parser
  must record every row-group open, including empty ones.
- Side note, not a finding: the HTML "forming a table" model (as distinct from CSS drawing) moves ALL tfoots to the end. R71
  chose CSS drawing, which is what a reader sees.

### W-D: R73 hierarchy — the title exemption and ancestor gaps

| id | Text probed | Case | Bound | Validator |
|---|---|---|---|---|
| w15/v15 | FIRST heading `<h1>Outlook</h1>`, then `<h2>Segment Organic Sales Growth</h2>` + goal table (`2026` column) | Q3 FY2026 | Beauty 5.0 (goal) | ACCEPTS |
| w16/v16 | T3 + `<h2>Ambitions</h2><h3>Segment Organic Sales Growth</h3>` + goal table | Q3 FY2026 | Beauty 5.0 | ACCEPTS |
| w17/v17 | TITLE + `<h2>Cumulative Results</h2><h3>Segment Results</h3>` + SEG_T | Q4 FY2026 | Beauty 4.0 | ACCEPTS |

- **w15** is a regression. The title exemption at :834–835 returns before ANY judgement, so positive forward evidence in the first
  heading block is discarded. Substitute: the title is exempt from neutral-topic refusal only (s22 masthead). A forward word, or a
  non-scope period, in the title still opens a non-results section.
- **w16** is the gap the seat declared open ("unlisted forward cues in ANCESTOR"). It is still a wrong bind under the acceptance
  bar. It is also a regression: 0f97 refused it.
- **w17** fails the same way for an unlisted cumulative cue. Neither "cumulative" nor "annualized" is in `_ANNUAL_QUALIFIER`
  (:498–503) or `_PERIOD_TOKEN` (:523–529).
- Substitute for w16/w17: ancestors admit by positive evidence too. An ancestor must be admitted by some route, or be a member of a
  closed neutral list ("Overview", "Highlights", the title). Otherwise it refuses.

### W-E: R73 label-vs-sentence — a label by shape is demoted to prose by punctuation or a literal. Regression.

**Cause.**
- `_pure_period_label` rejects any paragraph ending in `.`/`!`/`?` or carrying a `_PROSE_LITERAL` (:752).
- Prose refuses only on `_OUT_OF_SCOPE` = annual/foreign (:884–886).
- An UNREADABLE foreign period is "unknown", so it is silently ignored.

| id | Label paragraph between DRV and the drivers table | Bound | Validator |
|---|---|---|---|
| w20[q3_dot] | `<p>Q3 2026.</p>` | TV 1.0 | ACCEPTS (v20) |
| w20[jan_mar_dot] | `<p>January to March 2026.</p>` | TV 1.0 | (same shape as v20) |
| w20[q3_literal] | `<p>Q3 2026 (in $000s)</p>` | TV 1.0 | (same shape) |

- Controls behave as intended: c21 `Three Months Ended June 30, 2026.` binds, and c22 `Three Months Ended March 31, 2026.` refuses.
  The hole is specifically *unreadable + sentence-shaped*.
- Substitute: between a governing heading and its table, any paragraph whose residual carries an unreadable period token refuses,
  whether it is a label or a sentence. Alternatively, classify a paragraph as a label when, after period forms, noise and glue are
  removed, no more than N content words remain, regardless of terminal punctuation.

### W-F: basis — a non-period, non-plain band cell over a single matched column is never examined

**Cause.** `_column` matches the per-cell form "2026" (:1046). Residual band cells are inspected only when several columns share a
key (:1058–1066), so a lone "Pro Forma" over one column is ignored.

| id | Band | Bound | Validator |
|---|---|---|---|
| w23/v23 | row 1 `"" \| Pro Forma \| ""`, row 2 `"" \| 2026 \| 2025`, `DIL \| $3.40 \| $2.93` | **GAAP diluted EPS 3.40 from the Pro Forma column** | ACCEPTS |

- This fails at 0f97 as well, so it is pre-existing.
- Substitute: extend R74's rule to every match. Any band cell stacked over the matched column that is not part of the matched form
  must be plain.

## FAIL-CLOSED REFUSALS (findings; non-blocking)

| id | Probe | Rule / line | Severity |
|---|---|---|---|
| f30 | `<h2>Reconciliation of Non-GAAP Measures</h2><p>Three Months Ended June 30, 2026</p><p>Core EPS excludes …</p>` → REC absent | `_reconciliation_paragraph` recomputes `active` from a pure period LABEL (:1357–1361). A label never carries the key word, so any label switches the section off. | major |
| f31 | `<h2>Fourth Quarter Segment Results 2026 vs. 2025</h2>` + SEG_T → absent | Any bare year other than the fiscal year makes an untailed ordinal quarter foreign (:638, :645). This contradicts R72's "2026 vs 2025 neutral". | minor |
| f32 | Spanned sub-cells `(1a)`, `(ii)`, `US$`, `†` → DIL absent | `_PLAIN_SUBCELL` (:1018). "(1a)" and "(ii)" were accepted at 0f97, so these are regressions. The rest are by ruling. | minor |
| f33 | `<p>Total P&G volume increased 3% in Q3 2026.</p>` beside the bound drivers table → TV absent (cross-check conflict) | `_volume_statements` skips only annual/foreign sentences (:1333). An "unknown" other-period sentence counts. Regression. | minor |
| f34 | `<h2>Non GAAP Reconciliation</h2>` → REC absent | :1361 requires the literal "non-gaap". | nit |

## VALIDATOR

- Every wrong bind above has a paired `validate_selected_facts` probe (v01–v10, v15, v16, v17, v20, v23). **All 15 ACCEPT.** The
  validator replays the same `_table_scan`/`_select_cell`/`_reconciliation_paragraph`, so it cannot catch an engine-level misread.
- **x40 (surface (a), still open):** after `_forge_absent(w, "pg_diluted_eps", ...)` replaces a uniquely addressable diluted EPS of
  3.07 with a typed absence, the validator **ACCEPTS**. This is round-6 disposition (a), carried as open by the seat. No new
  forged-present path was found: the validator re-derives the value from the replayed cell (economic_observations.py:186–195).

## COMMIT-CLAIM CHECK

- **b64ce018534 — true.**
  - "57 executed cases" = 47 + 10 at head.
  - "RED at 0f974054e6bb: 45 failed, 12 passed" was reproduced.
  - The gate wiring is a 3+/1- change to `.github/ci/legacy-jobs.yml`. It was confirmed only at stat level.
- **82c3df9a0043 — true:**
  - "Parser untouched": the stat is pg_profile.py only.
  - "Removes `_RESULTS_WORD` … `PG_PERIOD_LABEL_MAX`": none of the nine names remain in engine/, tests/ or scripts/.
  - The counts 456/22, 59 and r10 47/10 all reproduce.
- **82c3df9a0043 — materially overstated:**
  - "R71: `_grid` draws only the FIRST thead first and only the FIRST tfoot last … (CSS 2.1 §17.2)" is false for an empty first
    group (W-C).
  - "ancestors refuse on … a non-scope period" is false for a bare prior year (w03/w04).
  - Both hold only for the shapes then probed, the same defect class R75 recorded against 0f974054e6bb.

## FROZEN-SUITE INTEGRITY

Clean. All ten files show zero drift from their freeze commits, and every one has the single author "Sol CEO".

## Probe file result

`41 failed, 9 passed` at head, broken down as:
- 17 wrong-bind failures (15 shapes)
- 15 validator-ACCEPTS failures
- 8 refusals
- 1 surface-(a) check
- 9 passing controls (c06, c11, c12, c13, c14, c18, c19, c21, c22)

The run is deterministic.
