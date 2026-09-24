# Opus red-team of PR #7905 — round 8 (content head d2c5db6d632a, 2026-09-24 ~18:05Z)

READ_ONLY Opus reviewer bounded to rulings R49–R54 (`SEAT_RULING_T1_PR_R7_2026-09-24.md`) with R27–R48 carried. Recorded verbatim by the seat from the reviewer's report; the reviewer's 35 throwaway probe functions (45 cases) are frozen as `tests/test_pg_economic_observations_probes_r7.py` with p34 struck by R60 (19 of the 44 frozen cases red at the freeze).

---

# Opus R8 red-team of PR #7905 @d2c5db6d632a (rulings R49-R54; R27-R48 carried) — READ_ONLY

## STATUS: REJECT. Blocking rulings: R49, R51. R50 and R54 are PARTIAL.

The committed suites are green, but novel probes show the head binds wrong values and the validator accepts them:
- R49: a prior-quarter diluted EPS is bound to the current quarter's literal.
- R51: a twelve-month Core EPS is bound as a quarterly value.
- R50: a quarterly segment value is bound under a foreign caption.
- R54: a quarterly EPS is bound under an Outlook heading.

In every one of these cases `validate_selected_facts` ACCEPTS the wrong present value.

## Per-ruling verdicts

| Ruling | Verdict | Evidence |
|---|---|---|
| R49 grid | **NOT DISCHARGED** (blocker p01; minor p02/p03/p05/p06b) | **p01**: an empty `<tr></tr>` whose slot is covered by a `rowspan="2"` in the row above. The HTML occupancy algorithm counts the empty row and uses up the rowspan. The parser drops rows that have no cells (`disclosure_diff.py`: the `if table.current_row` / `if cells:` guards), so `_grid` (pg_profile.py:193-208) carries the cell into the NEXT real row and shifts that row's cells right. Result: `pg_prior_diluted_eps = 3.07` (the current literal), and it VALIDATES. **p06b**: a fully covered band row (`<tr></tr>` under an all-`rowspan=2` band) misaligns the whole drivers table, so every value is absent (fail-closed; the HTML reading is 1.0). The trailing carry loop (pg_profile.py:209-211) also stops at the first uncarried column, so a carried cell beyond a gap is lost (code reading only). **p02**: `<td colspan="1" colspan="2">`. HTML keeps the first attribute, but `attr_map` (disclosure_diff.py, `{key: value for key, value in attrs}`) keeps the last, so organic volume binds −3.0 from the FX column and validates. **p03**: `colspan="２"` (full-width digit) parses as 2 and `colspan="1_0"` as 10, because Python `int()` accepts them (`_span_attribute`, disclosure_diff.py:71-77). The ruling says garbage means 1. **p05**: a stacked header where only the top row spans (`colspan=2` "Three Months Ended June 30, 2026" over "" / "(unaudited)", with a `$ | 3.07` split). One column matches by the joined form (tuple key) and the other by a per-cell form (int key) (pg_profile.py:712-715). The keys differ, so the single-literal rule never fires and DIL/PRIOR are absent. That is recall loss, fail-closed. |
| R50 vocabulary fail-closed | **PARTIAL** (major) | The unknown rule applies only to value-column stacks (pg_profile.py:271-277). The caption and the label-column band cells go through `period_context` alone (pg_profile.py:268-270). **p12**: `<caption>Three Months Ended March 31st, 2026</caption>` (foreign quarter, unreadable date) does not refuse, so Beauty = 4.0 validates. The same text in a value-column band row IS refused (p12c passes). R50 makes the caption "a band label" and the band fail-closed, so this is inconsistent. **p13**: a label-column band cell "Quarter ended 31/03/2026" behaves the same (Beauty = 4.0). The rest of the vocabulary holds: "3 Months Ended Jun. 30," (p16), reversed date order with "Ending" in a pure paragraph (p17), an ordinal-date value column refused as unknown (p15), an unknown month treated as foreign (p19), and a scope caption plus an annual column refused (p20). |
| R51 row sections | **NOT DISCHARGED** (blocker) | **p21**: the section label is a single `<td colspan="3">Twelve Months Ended June 30, 2026</td>`. HTML sees one cell carrying only a label, but `_grid` copies it into every column, so `_label_row` (pg_profile.py:253-255) sees text in `row[1:]` and opens no section. Core EPS 12.50 (twelve-month) binds as Q4 and VALIDATES. The control with a label-only first cell is refused (p21c passes), and a scope section after an annual one works (p23 passes). The fix is to judge "label only" by origin (every position of the row is the first cell's origin, or the others are empty). |
| R52 validator replay | **DISCHARGED** | p24: a forged receipt on a cell in an excluded section is refused. p25: a receipt on a comment copy inside a cell is refused. p26: a receipt on a comment copy inside the reconciliation paragraph is refused. p27: multibyte text and entities before the paragraph keep parity. p28: total volume that agrees with one statement and conflicts with another is refused. Code: economic_observations.py (the `expected_receipt_span` equality check for cells and paragraphs, and `pg_volume_cross_check`) and pg_profile.py:365-366. |
| R53 statements | **DISCHARGED** | p29 (both variants): "volumes decreased 4%" and "unit volumes were down 4 percent" count as conflicts. `_VOLUME_TERM` is at pg_profile.py:924. |
| R54 uniqueness / forward-looking | **PARTIAL** (major) | Uniqueness is judged before the length check (p30 passes; pg_profile.py:1011-1014), and an Outlook sub-heading between the topic and the table refuses (p33 passes). Two violations: **p31**: `<h2>Outlook</h2>` followed by a pure-period paragraph "Three Months Ended June 30, 2026" and then an EPS table. `governing` = (the period label, "Outlook"), and `_quarterly_tables` admits if ANY governing heading matches (pg_profile.py:650-655). The Outlook topic is outvoted, so DIL 3.07 / PRIOR 2.93 validate. **p32**: `_FORWARD_LOOKING` (pg_profile.py:436) misses inflections. "Segment Outlooks", "Estimated Segment Results", "Forecasted Segment Results" and "Targeted Segment Results" each admit the segment table (Beauty = 4.0, validates). |

## Commit-message claims checked against the diffs
- 0cb12b40a96: The r6 file is added, and its docstring's only line names the freeze. The r6 path is in the gate job's `paths` and run line (`grep -c probes_r6.py .github/ci/legacy-jobs.yml` = 2). I did not re-verify "20 failed / 12 passed at this head" because that needs a checkout at the freeze.
- 8189ff1d646: **FALSE in part**. "an attribute value outside 1..64 or unparseable counts as 1" fails for `２` and `1_0` (p03). The "only the real attributes count" claim is weakened by the last-duplicate-wins behaviour (p02). The "Additive only" claim matches the diff: `to_dict` and the `stable_id` arguments are untouched.
- d2c5db6d632a:
  - **FALSE**: "_grid places cells by the HTML occupancy algorithm" (p01, p06b).
  - **FALSE in part**: "the single-literal rule covers the joined form" (p05).
  - **FALSE in part**: "Captions are band labels" (p12). Captions are classified, but not fail-closed like the rest of the band.
  - **FALSE**: "R51: label-only rows … open sections" fails for the colspan'd label, which is the usual EDGAR form (p21).
  - **FALSE**: "governing headings naming outlook/… admit no table" fails for p31 and p32.
  - True: `_COLSPAN` and the source-window re-read are gone (grep finds no `_COLSPAN`; `document_period_verdict`'s `source` parameter is kept but unused, pg_profile.py:559-566, and the validator call was updated).
  - True: R52 and R53.
  - True: "266 passed" (verified).

## Evidence (commands and output tails)
1. Committed suites: `PYTHONPATH="$PWD" <venv>/python -m pytest tests/test_pg_economic_observations.py tests/test_pg_economic_observations_probes{,_r2,_r3,_r4,_r5,_r6}.py -q -p no:cacheprovider --rootdir="$PWD" -c /dev/null -W ignore` → `266 passed in 8.05s`.
2. Frozen drift: `git diff <freeze> d2c5db6d632a --stat -- <file>` returned empty for all six (probes@7804e24a, r2@1970ea2b20, r3@fb50fdead4, r4@b371c84fc269, r5@1c7162e6678, r6@0cb12b40a96).
3. Single author: `git log --format=%an d2c5db6d632a -- <file> | sort | uniq -c` → `1 Sol CEO` for each of the six files.
4. Probes: `opus_r8_probes/test_r8_probes.py` has 35 test functions and 45 executed cases → `20 failed, 25 passed in 6.44s`. A side script confirmed that the wrong present values validate: `p01 {prior_diluted_eps: 3.07} VALIDATES`, `p02 {organic_volume: -3.0} VALIDATES`, `p12 {beauty: 4.0} VALIDATES`, `p18 {total_volume: 1.0} VALIDATES`, `p21 {core_eps: 12.5} VALIDATES`, `p31 {diluted_eps: 3.07} VALIDATES`, `p32 {beauty: 4.0} VALIDATES`.

### Failing probes (assertion messages)
- p01 `('prior EPS bound to the current-quarter literal after an empty <tr>', …) assert 3.07 in (None, 2.93)` — R49 violation
- p02 `('organic volume read under the last duplicate colspan', -3.0)` — R49 violation (minor)
- p03 `[(2, 1), (10, 1), (1, 1)] == [(1, 1), (1, 1), (1, 1)]` — R49 violation (minor)
- p05 `('single-literal rule not applied to a partly spanning stack', …) (None, None) == (3.07, 2.93)` — R49 violation (minor, fail-closed)
- p06b `('HTML-aligned drivers table unread after a fully covered band row', …) None == 1.0` — R49 violation (minor, fail-closed)
- p09 `('one literal spanning both period columns bound as the current quarter', …) 3.07 is None` — GAP
- p12 `('caption naming an unreadable quarter did not refuse the table', 4.0)` — R50 violation
- p13 `('label-column band cell naming an unreadable quarter did not refuse', 4.0)` — R50 violation
- p14 `('keyword heading naming an unreadable quarter admitted the table', 4.0)` — GAP
- p18 ×3 `('Three Months Ended March 31, 2026 (Unaudited)' | '…:' | 'For the …', 1.0)` — GAP
- p21 `('twelve-month Core EPS bound under a colspan section label', 12.5)` — R51 violation
- p22 `('twelve-month Core EPS bound under a second-column section label', 12.5)` — GAP
- p31 `('an Outlook-governed table admitted through its period sub-label', …) 3.07 is None` — R54 violation
- p32 ×4 `('Segment Outlooks' | 'Estimated …' | 'Forecasted …' | 'Targeted …', 4.0)` — R54 violation
- p34 `("non-forward-looking 'Target' heading refused", …) None == 4.0` — GAP (the rule refuses too much)

### Passing probes
p04, p06, p07, p08, p10, p11, p11b, p12c, p15, p16, p17, p19, p20, p21c, p23, p24, p25, p26, p27, p28, p29×2, p30, p33, p35.

## Gaps no ruling covers (for the seat to rule on; not graded as violations)
- g1 (p09): one data literal whose colspan covers both the current and prior columns binds as the current quarter. The prior column is refused only because `_cell_at` returns the leftmost position.
- g2 (p14): a heading with an unresolved period marker leaves the context unchanged. The fail-closed "unknown" rule reaches value columns and section rows (pg_profile.py:293-294) but not headings, so a keyword heading ("Segment Results for the Three Months Ended March 31st, 2026") admits a foreign table.
- g3 (p18): a period-label paragraph with a suffix or prefix ("(Unaudited)", a trailing colon, "For the …") is not read as a pure label, so a foreign-quarter label is ignored. TV 1.0 then binds from a Q3-labelled table and validates.
- g4 (p22): a section label in the second column is not a section.
- g5 (p34): "Target" as a proper noun or ordinary word refuses actual results. The rule is over-broad, but fail-closed.
- g6: `_volume_statements` treats "volumes, excluding acquisitions, increased …" (with a comma) as a total-volume statement, because the lookahead needs whitespace. That is a false conflict, fail-closed. Found by reading the code, not by a probe.
- g7: `period_context` sees only the quarter word when a column is headed "Q4 FY26" over "Fiscal year 2025", and the year label is checked only when no verdict exists (pg_profile.py:497). A contradicting fiscal-year label is therefore ignored. Found by reading the code, not by a probe.

## Round-11 open items (documented only, not graded)
- Nested tables (p11b): a `$3.07` inside a nested table makes current EPS absent while prior binds 2.93, and extractor/validator parity holds. The outer-cell span contains the inner cells, so `_cell_at` would resolve an inner receipt to the outer cell.
- The forged plain absence and the Q1/Q2 forms were not probed, per the commission. From code reading: a band stacked "Q2" over "2026" has no period marker and no verdict, and its "2026" cell matches a current form. This is round 11's Q1/Q2 item.

## GAPS (untested)
- I did not re-run `tests/test_fundamental_forensics_disclosure_diff.py` or `tests/test_earnings_release_binding.py`, so the "Additive only" claim was checked by diff reading only.
- I did not verify the "20 failed → 32 passed" claim at the freeze commit (no checkout allowed).
- Not probed: a receipt minted against a different source with the same visible text; colspan-spanning section rows inside the drivers table's volume cross-check; the 64-column width limit on real grids; rowspan="0".
- No live PG text was used, so every finding comes from synthetic markup.

## DEVIATIONS
None. Read-only. Files were written only under the scratchpad. There were no gh calls, no spawns, and no full repository suite run.
