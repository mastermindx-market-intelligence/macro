# Opus red-team of PR #7905 — round 9 (content head af4212037b69, 2026-09-24 ~18:50Z)

READ_ONLY Opus reviewer bounded to rulings R55–R60 (`SEAT_RULING_T1_PR_R8_2026-09-24.md`) with R27–R54 carried. Recorded verbatim by the seat from the reviewer's report; the reviewer's 52 probe cases are frozen as `tests/test_pg_economic_observations_probes_r8.py` with q06 adapted order-insensitively by R65 (the reviewer's own finding).

---

# Opus R9 red-team of PR #7905 @af4212037b69 (rulings R55-R60; R27-R54 carried) — READ_ONLY

STATUS: FAIL — REJECT. Blocking rulings: R56, R57 (blocker); R55, R58, R59 (major). R60 discharged.

## Verdict per ruling

| Ruling | Verdict | Evidence |
|---|---|---|
| R55 | NOT DISCHARGED | Implemented: ordinal, first-wins, ASCII spans (disclosure_diff.py:71-85, 705-735). q04/q05/q07/q08/q09 pass, and q06 passes on substance. **q01 (major):** a `rowspan="2"` inside `<thead>` is carried into the `<tbody>` data row. HTML ends a rowspan at the edge of its row group. `_grid` (pg_profile.py:185) ignores row groups, so `$3.07` shifts under "2025" and **pg_prior_diluted_eps=3.07** (true value 2.93). The validator accepts it (q01v DID NOT RAISE). **q02/q03 (major, ruling-level):** `colspan="2.0"`, `"2_0"`, `"+2"` and `"3px"` are 2/2/2/3 under HTML's integer parsing but 1 in the parser (`[(1,1),(1,1),(1,1)]`). R55 requires this ("everything else is 1") while also saying it lays out "as HTML does". With `colspan="2.0"` the result is **prior EPS 3.07 (wrong)** and the validator accepts it (q02v). |
| R56 | NOT DISCHARGED (blocker) | **q10 ×5:** a foreign-quarter period paragraph (March 31, 2026) with ordinary decoration binds the drivers table as Q4, **TV=1.0**. Failing forms: "(Unaudited) (In millions)", "…2026: (Unaudited)", "…March 31, 2026 **and 2025**" (the standard EDGAR form), "— Unaudited", "Unaudited: …". Cause: `_LABEL_SUFFIX` (pg_profile.py:469) strips one parenthetical plus an optional colon, and a period paragraph that is not pure gets no scan at all (`_table_scan` pg_profile.py:588 only reads headings and pure-period paragraphs). The validator accepts (q10v). **q11:** the same label inside a `<div>` with other text binds TV=1.0. **q12 ×3:** "Fourth Quarter Fiscal '25", "FY-25" and "FY’25" bind Beauty=4.0. `_FISCAL_YEAR_LABEL` (pg_profile.py:454) misses these forms. `_marked_context` (pg_profile.py:279) only fails closed when `period_context` returns None, but the quarter word already returned "scope". Validator accepts (q12v). **q14:** a caption with a scope date and an unreadable "March 31st" marker binds. **q15:** a heading with a scope date and "Quarter Ended 31/03/2026" binds. **q16:** a reconciliation paragraph under "Fourth Quarter FY-25 Core EPS Reconciliation" is bound. The validator accepts q11, q14, q15 and q16. Controls q12 ×5 and q13 ×2 pass. |
| R57 | PARTIAL; the ruling's intent is violated (blocker) | The letter holds: `_section_label` (pg_profile.py:269) needs exactly one distinct text cell (p21/p22, q20, q21 pass). The definition fails open on every period row that carries more than one text cell. **q17:** a mid-table band row `["Twelve Months Ended June 30, 2026","2026","2025"]` (the common EDGAR stacked-period layout) is ignored, so twelve-month **Core EPS 12.50 binds as the quarter** (period 2026-06-30). The validator accepts (q17v). **q18:** the same happens with a second "(unaudited)" cell. **q19:** the same happens with a colspan section label beside a rowspan-carried text label. Validator accepts q18/q19. This also breaks R56 ("fail-closed everywhere a period can be named"): `_row_contexts` (pg_profile.py:315) reads no other row. |
| R58 | PARTIAL; the ruling's construction permits a wrong bind (major) | Implemented at pg_profile.py:766-785. q23/q24/q25 pass (a forged receipt on the p09 spanning literal is refused, and extractor and validator agree on identical-origin spans). **q22:** "Three Months Ended June 30, 2026" spans two sub-cells that both carry text ("As Reported" / "Restated"). The per-cell key uses only the top cell (pg_profile.py:769), so both columns share it. The single-literal rule (pg_profile.py:774) then binds the Restated column: **pg_diluted_eps=3.19** while the As Reported cell is empty. The validator accepts (q22v). The rule should apply only when the sub-cells do not tell the columns apart. |
| R59 | NOT DISCHARGED (major) | The letter holds for the listed inflections and for (topic, sub-label) (p31-p33, q28[Projected], q31 pass). **q26:** a table under `<h2>Outlook</h2><h3>Segment Results</h3>` binds Beauty=4.0. `_table_scan` replaces the topic at pg_profile.py:590, so the governing Outlook section heading is dropped. **q27:** a caption "Segment Outlook" binds. **q28:** "Targeting", "Projecting" and "Anticipated" are inflections missing from the list at pg_profile.py:465 (a ruling-level list gap, minor). **q30:** a paragraph under "Core EPS Outlook Reconciliation" is bound as pg_core_reconciliation_context. R59 covers tables only (pg_profile.py:1061 has no forward-looking check). **q29 (minor, availability):** an h1 "…Results and Outlook" stays the topic above a pure-period h3, which refuses every table it governs. The validator accepts q26, q27, q28 and q30. |
| R60 | DISCHARGED | All 7 frozen suites are byte-identical to their freeze commits and each has one author (Sol CEO, 1 commit). `grep -c "def test_p34"` returns 0 and the strike note is at r7:298. The r7 suite has 44 passing. 310 green combined. |

## Commit-message claims checked against the diffs
- 6ae7c4cb926: "19 failed / 25 passed" (44 cases) is consistent. r7 now has 44 passing. OK.
- 70f7cba7c0b: ordinal incl. implicit bare-td row (disclosure_diff.py:720-722), first-wins attrs used for hidden-markup and spans (`_is_nonvisible` 667, spans 722), and ASCII-digit spans: all TRUE as code. The ruling's framing ("as HTML does") is FALSE for spans (q03).
- af4212037b69: "a fiscal-year label naming another year makes the text foreign" is FALSE for "Fiscal '25", "FY-25" and "FY’25" (q12). "strips … a trailing parenthetical, colon or period" is true for exactly ONE parenthetical and a colon only after it (q10). "(325 with them)" does not reproduce: the three suites alone give **59 passed** (310+59=369, nit). The R55/R57/R58/R59 bullets match the code.

## Commands and tails
1. The 8 committed suites combined (clean venv): `310 passed in 11.05s`.
2. Frozen drift: `git diff <freeze> af4212037b69 --stat -- <file>` is empty for all 7. `git log --format=%an af4212037b69 -- <file> | sort | uniq -c` gives `1 Sol CEO` for each. `grep -c "def test_p34" tests/test_pg_economic_observations_probes_r7.py` gives `0`.
3. Probes: `pytest opus_r9_probes/test_r9_probes.py`: **33 failed, 19 passed (52 cases)**. q06 failed only on block order in my own assertion: the values `[[0],[1],[2]]` outer and `[[0],[2]]` inner are correct, so that is a substantive pass. Total: 32 substantive failures, 20 substantive passes.
4. `pytest tests/test_fundamental_forensics_disclosure_diff.py tests/test_earnings_release_binding.py tests/test_company_intelligence_refresh.py`: `59 passed`.
5. Validator agreement (direct `valid()` loop): ACCEPTED for q11, q14, q15, q16, q18, q19, q26, q27, q28 and q30. q01v, q02v, q10v, q12v, q17v and q22v: DID NOT RAISE.

Failing probes (substantive): q01, q01v, q02, q02v, q03, q10[two_parens, colon_then_paren, and_prior_year, emdash, prefix], q10v, q11, q12[Fiscal '25, FY-25, FY’25], q12v, q14, q15, q16, q17, q17v, q18, q19, q22, q22v, q26, q27, q28[Targeting, Projecting, Anticipated], q29, q30.

**The seat's "never a wrong bind" claim is false.** Every wrong-value shape above is also accepted by `_verify_pg_replay` (economic_observations.py:88). It replays the same `locate_pg_observation`/`_table_scan`/`pg_reconciliation_paragraph`, so it shares every extractor defect.

## Ruling-level gaps (separate from head violations)
- R55 requires a non-HTML span parse (q02/q03) while claiming HTML layout. It also ignores row-group rowspan clipping (q01).
- R57's "exactly one text cell" definition has no fail-closed fallback for period rows with several cells (q17-q19).
- R58's per-cell key ignores sub-cells that tell the columns apart (q22).
- R59 covers only tables and (topic, immediate), not captions, section hierarchy or reconciliation paragraphs. Its inflection list misses targeting, projecting and anticipated.

## GAPS (not tested)
- I did not check whether each failure is new this round or inherited: no probes were run at d2c5db6d632a.
- Not tested: `<tfoot>` placed before `<tbody>`; caption inside an unclosed `<td>`; nested-table value binding (left open for round 12); Q1-Q3 identities (all probes use Q4_FY2026); `pg_volume_cross_check` with colspan section rows; the plain-text table path.
