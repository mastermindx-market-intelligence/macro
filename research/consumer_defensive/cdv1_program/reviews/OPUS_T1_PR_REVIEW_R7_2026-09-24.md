# Opus red-team of PR #7905 — round 7 (content head 8f632470d8ab, 2026-09-24 ~16:40Z)

READ_ONLY Opus reviewer bounded to rulings R43–R48 (`SEAT_RULING_T1_PR_R6_2026-09-24.md`) with R27–R42 carried. Recorded verbatim by the seat from the reviewer's report; the reviewer's 32 throwaway probes are frozen unchanged as `tests/test_pg_economic_observations_probes_r6.py` (20 red at the freeze).

---

# Opus R7 red-team of PR #7905 @8f632470d8a (rulings R43-R48; R27-R42 carried) — READ_ONLY

VERDICT: REJECT. Blocking: R43 (blocker), R44 (major), R46 (major). Partial: R47 (minor). Discharged: R45 (nit), R48 (nit), and R27-R42 as carried by the frozen suites. There are also ruling-level gaps (below).

## Commands
- Six committed suites, seat checkout, venv_t1, one pytest per file: original suite 43 passed; probes 20 passed; r2 21 passed; r3 33 passed; r4 39 passed; r5 78 passed. Total 234 passed, 0 failed.
- Frozen drift (`git diff <freeze> 8f632470d8a --stat -- <file>`): probes.py@7804e24a EMPTY; r2@1970ea2b20 EMPTY; r3@fb50fdead4 EMPTY; r4@b371c84fc269 EMPTY; r5@1c7162e6678 EMPTY.
- Authors (`git log --format=%an 8f632470d8a -- <file>`): each frozen file has exactly one commit, by `Sol CEO`.
- Gate job wiring: .github/ci/legacy-jobs.yml:13581-13585 list the paths; the run line at :13596 runs all six files.
- R26 grep over pg_profile.py and economic_observations.py: no output, exit 1 (empty).
- R7 probes: scratchpad/opus_r7_probes/test_r7_probes.py. 32 tests, 20 FAILED / 12 passed.

## Per-ruling table
| Ruling | Verdict | Evidence at 8f632470d8a |
|---|---|---|
| R43 | NOT DISCHARGED (blocker) | **Colspan source.** `_grid` does not take colspan from the parser. It re-reads the raw markup with a regex, `_COLSPAN` (pg_profile.py:134, applied at :189-192). That regex:<br>• matches `data-colspan="2"`, because `\bcolspan` finds a word boundary after `-` (r43a);<br>• misses `colspan=" 2"`, which HTML parses as 2 (r43b);<br>• misses a colspan that sits more than 400 characters into the tag, behind a long `style` attribute (r43c).<br>This is a second, regex-shaped reading of table structure, which R36/R38 forbid.<br>**Rowspan.** Rowspan is not modelled at all, so the second band row shifts left (r43d).<br>**Result.** Each probe produces a wrong bind that the validator ACCEPTS: the pair agrees, because both sides read one grid, and `valid()` passed before each assertion failed.<br>**Negative sign.** Under a spanning header over `$ (` / `3.07` / `)`, the rule at :593-594 binds +3.07 for a rendered negative (r43f).<br>**Standard EDGAR layout not addressed.** `Three Months Ended June 30,` (colspan 4) over `2026`/`2025` (colspan 2 each), over `$`/`3.07`/`$`/`2.93`: the stacked form "Three Months Ended June 30, 2026" matches first (:588). It has no single-cell origin, so `object()` is minted per column (:591-592), the spanning filter at :593 never fires, and both current and prior diluted EPS are typed absences (r43e).<br>**Passed.** `$` / `(3.07` / `)` stays absent (r43g). |
| R44 | NOT DISCHARGED (major) | The vocabulary is closed and fails open: an unrecognised band label returns None, and the heading context then binds the table (pg_profile.py:342-351, :407-409, :447). Each of these band labels binds a foreign or cumulative drivers table as the admitted quarter (all r44a):<br>• `9 Months Ended March 31, 2026` (Q3)<br>• `12 Months Ended June 30, 2026` (Q4)<br>• `3 Months Ended March 31, 2026` (Q4)<br>• `Three Months Ending March 31, 2026` (Q4)<br>• `Quarter Ended 31 March 2026` (Q4)<br>• `YTD` (Q3)<br>• `FY26` (Q4)<br>**Pure-period headings.** `_PURE_PERIOD_HEADING` (:416-420) does not recognise "Three-Month Period Ended …" or "Quarterly Period Ended …". Such a sub-heading replaces the drivers topic, and TV becomes absent (r44b). This contradicts R44's last sentence and the 8f632470d8a message ("_PURE_PERIOD_HEADING recognises the same forms").<br>**Passed.** `Quarter Ended March 31 2026`, `Three-Month Period Ended March 31, 2026`, `First Nine Months`, `Fiscal 2026`. |
| R45 | DISCHARGED (nit) | There is one selection, `_reconciliation_paragraph` (:841-862), used by `_text_fact` (:879) and by the validator (economic_observations.py:114-119). The receipt is converted from bytes (:110). The parity probe passed: multibyte text before and after the tables, `&nbsp;`/`&#160;`/`&amp;` in cells and headers, a colspan EPS table and the reconciliation paragraph all bind, and the validator accepts the extractor's own workspace (r45a). A partial receipt cannot pass, because the receipt text must equal the value (:342) and the value must equal the paragraph text (:118).<br>Nit: paragraphs over 240 characters are filtered out before the uniqueness count (:860-862), so a long second reconciliation paragraph never makes the short one ambiguous. |
| R46 | PARTIAL (major) | `locate_pg_observation` replays the plan (:635-649), and the frozen r42d-f pass. Two gaps:<br>**(1) Cross-check not replayed.** The validator never replays `_volume_cross_check`. A present total volume that the extractor refused as `cross_check_conflict` (R32; "Total P&G volume increased 4%" against a 1.0% cell) VALIDATES when forged (r46a). economic_observations.py:121-146 has no cross-check.<br>**(2) Receipt on markup.** "Visible text" is checked by text equality, not position (economic_observations.py:127; pg_profile.py:294). A receipt on the attribute copy `data-note="1.0%"` inside the cell validates (r46b), although R46 says the replayed bytes are never markup. The mask_markup docstring (receipts.py:224-226) says EDGAR puts `width:x%` on every cell. The value is unchanged, so this part is minor on its own. |
| R47 | PARTIAL (minor) | Whole-word qualifiers (:785). `percent` is accepted (:779). The subject may appear anywhere (:827). Sentences split on `.;!?` (:786).<br>**Passed:** "declined by 4 percent", "Total P&G's volume", "was down 4%", and an agreeing "1 percent!" (r47a/b).<br>**Missed:** "Total P&G volumes grew 4%" — `\bvolume\b` (:776) does not match the plural, so a conflicting statement of the same measure lets the drivers value bind (r47a[plural_volumes]). |
| R48 | DISCHARGED (nit) | The combined subject requires exactly one admitted drivers table (:726). The validator uses the same `_candidate_tables` (:563-565). With two admitted tables, one combined and one split, the extractor binds TV from the split table, the validator accepts it, and a forged combined absence is refused (r48a). A combined table under a twelve-month heading is ignored (r48b).<br>The five frozen suites are wired. 1c7162e6678 is honest: 4 files, no engine hunk. 8f632470d8a: every named hunk is present, but the `_PURE_PERIOD_HEADING` equivalence claim is false (see R44). |
| R27 | DISCHARGED | r42e (validator heading governance) passes via `_candidate_tables` (:542-548). |
| R28 | DISCHARGED | One locator, `replay_table_layout` (:273-300), used by both sides (:757; economic_observations.py:130). |
| R29/R30/R31/R33 | DISCHARGED | Frozen probes green. |
| R32 | PARTIAL (major; validator side only) | Extractor side green. The validator does not enforce it (r46a, see R46). |
| R34/R41 | DISCHARGED | Under R48's corrected wording, the fixture hardcodes only the filing clock, asof and the ordinal map (earnings_economic_fixtures.py:20-23, :45, :185, :190). |
| R35/R38/R39/R40/R42 | DISCHARGED | r5 78/78 green. R38 is by definition: parser blocks are the visible text (but see the caption gap). |
| R36 | PARTIAL (major) | Folded into R43: `_COLSPAN` is a regex re-read of the markup beside the parser. |
| R37 | superseded by R43 | Band depth logic unchanged; the rowspan misalignment is under R43. |

## Failing probes (20)
- test_r43a_data_colspan_attribute_is_not_a_colspan — ('organic volume bound from the FX column via data-colspan', -3.0)
- test_r43b_colspan_with_leading_space_is_two_columns — ("Price bound from the organic-volume column (colspan=' 2')", 2.0)
- test_r43c_colspan_after_long_style_attribute — ('Price bound from the organic-volume column (colspan past 400 chars)', 2.0)
- test_r43d_rowspan_band_keeps_columns_aligned — ('total volume bound from the organic column under a rowspan band', 3.0)
- test_r43e_edgar_two_row_band_spanning_year_over_dollar_split — ('R43 $/amount split not addressed under a two-row band', <typed absence rows>)
- test_r43f_spanning_header_split_negative_sign — ('rendered $ (3.07) bound with a positive sign', 3.07)
- test_r43h_mid_table_cumulative_section_row_not_bound_as_quarter — (…, 1.0) [ruling-level gap]
- test_r44a_band_label_refuses_the_table[9_months_digits_q3 | 12_months_digits_q4 | 3_months_digits_foreign_q4 | three_months_ending_foreign_q4 | quarter_ended_day_first_foreign_q4 | ytd_q3 | fy26_q4] — ("band '<label>' bound as the admitted quarter", 1.0)
- test_r44b_three_month_period_subheading_is_a_pure_period_heading — ('R44 pure-period heading form replaced the drivers topic', <typed absence>)
- test_r44c_caption_period_label_refuses_the_table — ('nine-month table (caption) bound as the quarter', 1.0) [ruling-level gap]
- test_r44d_bold_paragraph_period_label_refuses_the_table — ('nine-month table (bold paragraph label) bound as the quarter', 1.0) [ruling-level gap]
- test_r46a_validator_refuses_present_volume_the_extractor_refused_as_conflict — Failed: DID NOT RAISE EconomicObservationError
- test_r46b_receipt_on_attribute_copy_of_visible_text_refused — Failed: DID NOT RAISE EconomicObservationError
- test_r47a_same_period_statement_conflicts[plural_volumes] — ('Total P&amp;G volumes grew 4%.', 1.0)

## Ruling-level gaps (for the seat's adjudication, not ruling violations)
- (g1) A `<caption>` period label is visible text, but the parser discards it: table text outside a cell is dropped (disclosure_diff.py:647-651). A nine-month table with a caption binds as the quarter (r44c).
- (g2) A styled-paragraph period label (`<p><b>Nine Months Ended …</b></p>`) is not a parser heading, and `_table_scan` reads only headings (:434-449). Such a table binds as the quarter (r44d).
- (g3) A period section row in the middle of a table, below the band, is never classified (r43h).
- (g4) Bounded text has the same receipt-on-markup class as r46b. R45's wording does not forbid it.

Suggested repair direction (seat's call):
- Take colspan and rowspan from the parser's own attribute map, and place cells with the HTML table-occupancy algorithm.
- Make band and period classification fail-closed: any band cell carrying a month, year, "months", "YTD" or "FY" token that is not positively the admitted quarter refuses the table.
- Give each stacked spanning form the origin set of its cells, so the `$` split filter applies.
- Replay `_volume_cross_check` in the validator.
- Check receipt position against visible (masked) text, not text equality.

## GAPS (not tested)
- Nested tables. A reading of the code gives at most a missed bind (`_cell_at` returns the outer cell first, and the extractor's own replay then refuses); not probed.
- colspan="0" and garbage values. A reading of `_grid` gives width 1, which agrees with HTML; not probed.
- Q1/Q2 scopes for the R44 forms. Only Q3 and Q4 were probed.
- Disposition items (a) and (c) were deliberately not re-litigated. The R48 forged combined absence was tested only where it hides nothing.
