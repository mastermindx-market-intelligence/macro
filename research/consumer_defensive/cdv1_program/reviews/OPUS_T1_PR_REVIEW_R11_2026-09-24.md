# Opus red-team of PR #7905 — round 11 (content head 0f974054e6bb, 2026-09-24 ~20:30Z)

READ_ONLY Opus reviewer bounded to rulings R66–R70 (`SEAT_RULING_T1_PR_R10_2026-09-24.md`) with R27–R65 carried. Recorded verbatim by the seat from the reviewer's report; the reviewer's 59 probe cases are frozen as `tests/test_pg_economic_observations_probes_r10.py` with s07 struck by R71 and s25 struck by R73 (45 of the remaining 57 RED at 0f974054e6bb, 12 passed). Adjudication: `SEAT_RULING_T1_PR_R11_2026-09-24.md`.

# Opus R11 red-team of PR #7905 @0f974054e6bb (rulings R66-R70; R27-R65 carried) — READ_ONLY

STATUS: REJECT. Blocking rulings: R66, R67, R68, R69. R70 is PARTIAL because two count claims are false.

Probe file: `scratchpad/opus_r11_probes/test_r11_probes.py`. 59 executed cases: **46 failed, 13 passed**.
- 29 failures are wrong binds, where a wrong value is presented as the admitted quarter's value.
- 11 failures are validator checks on those wrong binds. In every one the validator ACCEPTS the wrong value.
- 12 failures are fail-closed wrong refusals, where a correct value is missed.
- 1 failure is a nit.
- The 13 passes are the controls, plus the li/div label cases.

## Per-ruling verdict
| Ruling | Verdict | Evidence |
|---|---|---|
| R66 | NOT DISCHARGED | pg_profile.py:213 sorts EVERY thead first and EVERY tfoot last. disclosure_diff start-tag handler (`table.group_kind = tag`) records every thead/tfoot as a header or footer group. CSS 2.1 §17.2 says only the FIRST table-header-group or table-footer-group is a header or footer; the others render as row groups in source order. s01: a second `<thead>` written after the "Twelve Months Ended" label is hoisted above it, and Core EPS **12.50 (twelve-month) is bound as quarterly; the validator accepts** (s01v). s02: a second `<tfoot>` in source position is sunk below the annual label, so Core EPS 2.95 is refused (fail-closed). s07 (nit): `rowspan="-0"` reads 1; HTML integer rules give 0 (`_SPAN_VALUE` has no sign). Controls pass: s03 (rowspan 0 in thead is clipped at the group), s04, s05, s06. |
| R67 | NOT DISCHARGED | The residual lexicon `_PERIOD_TOKEN` (pg_profile.py:508-513) is still a closed list. Each of these headings binds Beauty 4.0 (s10, 14 cases): `H2 2026`, `1H26`, `TTM`, `LTM`, `CY2026`, `Calendar 2026`, `52 Weeks`, `2026-03-31`, `03/31/2026`, `31.03.2026`, `Q-3`, `Q 3 2026`, `Fourth Quarter ’25`, `Fourth Quarter '25`. The validator accepts all five that were tested (s10v). Causes: numeric dates lose their year to `_YEAR` (line 603-605) and leave no token; `\d{0,2}q[1-4]` needs the digit adjacent, so `Q-3` and `Q 3` pass; two-digit apostrophe years are not tokens, so `_QUARTER_WORD` without a tail reads scope (line 615). s11: for Q1 FY2027, **"First Quarter 2026" is scope** because `current_years` at line 608 adds the calendar year to the ordinal-quarter test at line 615, **and the validator accepts** (s11v). s12: the drivers heading "… 2026 vs. 2025 — Fourth Quarter ’25" binds TV 1.0. s21: "Third Quarter FY2026: **Next Quarter** Segment Guidance" binds 5.0, because `_QUARTER_CAPTION` (line 621-622) erases any "quarter" once a form exists. Label rule (line 707-716): a 121-character foreign label is ignored and TV binds 1.0 (s15). s18: a prose "label" naming Q4 re-opens scope under a "Third Quarter" heading and binds 4.0; **validator accepts** (s18v). s16 and s17: prose sentences become labels and refuse correct tables (fail-closed). s13: "FY26 Q4" is unknown, so the commit's "Q-FY in every spelling" is false. Control s14 passes ("… 2026 vs 2025": scope wins, which I agree with). s19 li/div labels are refused correctly. |
| R68 | NOT DISCHARGED | `_is_non_results` (line 719-728) treats any heading with a results word as a results heading unless a closed `_FORWARD_LOOKING` word is present (line 524-527). s20, for Q3 FY2026: "Looking Ahead: Segment Organic Sales", "Segment Organic Sales Goals" and "Segment Sales Plan" all bind a fiscal-year goal column "2026" = **5.0 as Q3 Beauty growth; validator accepts** (s20v). The ruling names "Looking Ahead" and "Plan" as non-results, but its own results-word test overrides them. s21 (above): a heading with a scope form is results "whatever else it says", even when that is next-quarter guidance. s22: a company-name masthead `<h1>` opens a level-1 non-results section that no h2-h6 can release, so the whole release is refused (fail-closed). s23: `<h2>Overview</h2>` over `<h3>Segment Results</h3>` is refused (fail-closed; matches the ruling). Controls s24, s25 and s26 pass. |
| R69 | NOT DISCHARGED | `_PLAIN_SUBCELL` (line 929) is fullmatched on raw, un-normalised text (line 970). s31: "(cy)/(py)" and "(rp)/(cc)" are treated as footnote marks, so **2.88 under "(py)" is bound as current diluted EPS; validator accepts** (s31v). s30 (fail-closed): "(Unaudited)" with a capital U, "(A)/(B)", "(1)(2)" and a bare "**" all refuse. Control s32 ("(restated)") passes. |
| R70 | PARTIAL | Frozen drift is empty for all nine files. Each file has a single author (`Sol CEO`). `grep -c "def test_r03"` = 0. r9 alone gives 53 passed, 6 skipped (true). The combined ten suites give **409 passed, 12 skipped**, not "(6 skipped)": r8 and r9 each skip 6. "With the parser, binding and refresh suites 415 passed" is false: those three suites alone give 59 passed, so the total is 468. 415 = 356 + 59 fits only the pre-r9 suites. |

## Wrong-value shapes and validator behaviour (`_verify_pg_replay`)
Every one of these shapes is ACCEPTED by `validate_selected_facts`:
- s01v: Core EPS 12.50 (second thead)
- s10v ×5: TTM, 2026-03-31, Q-3, Fourth Quarter '25, H2 2026
- s11v: Q1 "First Quarter 2026"
- s18v: prose override
- s20v: Looking Ahead
- s31v: (py)

The validator also shares the engine for s12, s15, s21, s20 (Goals/Plan) and s31 (cc), which were not separately validator-probed. Because the validator replays the same `_table_scan`, it inherits every extractor defect.

## Ruling-construction flaws (separate from code violations)
1. **R66** mandates "every thead … every tfoot" in drawn order. This contradicts CSS 2.1 §17.2, and it produces a wrong bind (s01). The rule should be: first thead is the header, first tfoot is the footer, all other groups stay in source order.
2. **R67** again enumerates a closed lexicon: half-year abbreviations, TTM/LTM, calendar/CY, weeks, numeric dates, spaced Q-numbers and apostrophe years are all missing. That is the same class of flaw R67 claimed to replace.
3. **R67** also accepts the calendar year for the whole classifier. That is correct for a bare column header, but wrong when the year qualifies an ordinal quarter (s11).
4. **R67**'s caption-word exemption erases relative quarters such as "next", "following" and "preceding" beside a scope form (s21).
5. **R67**'s label rule has a length cut-off (s15 wrong bind at 121 characters), and it promotes prose to a governing label. That both re-opens scope (s18, wrong bind) and refuses correct tables (s16/s17, fail-closed).
6. **R68**'s positive-evidence test is overridden by any results word. The forward vocabulary is still closed: goals, plan, looking ahead, going forward are absent (s20, wrong bind). "Shallowest level governs" lets a non-results h1 masthead refuse a whole release (s22, fail-closed).
7. **R69**'s "footnote mark" admits any two lowercase letters or digits, so "(py)" is plain (s31, wrong bind). It is also case-sensitive where the rest of the classifier normalises ("(Unaudited)", s30, fail-closed).

## Commit-claim check
- **8c7ae72c649:** stat matches (r9 +263 lines, gate yml, two records). Could not verify "37 failed / 22 passed" at fec2bbac without checking out the old head (GAP).
- **eadf33f98ea:**
  - True: stray-end-tag rule, rowspan 0 kept, >64 flagged, plain-text path in one tbody.
  - "All additive": TableCell.rowspan can now be 0, where it was 1. The only consumer is pg_profile (grep), so this is effectively true. The field comment "1 when absent or invalid" is now stale.
  - "HTML rules for non-negative integers": misses "-0" (nit).
- **0f974054e6bb:**
  - False:
    - "drawn order" (s01, s02)
    - "any leftover year, month, quarter number or period word is unknown" (s10)
    - "Q-FY in every spelling" (s13)
    - "_PLAIN_SUBCELL allows only $, (unaudited) and footnote marks" (it admits "(py)" and rejects "(Unaudited)")
    - "(6 skipped)"
    - "415 passed"
  - True: removal of `_residual_marker`/`_RESIDUAL_MARKER`/`_PERIOD_MARKER`/`_LABEL_SHAPE`/`_ForwardState`/`_is_forward`/`_admissible_heading` (grep empty), `_marked_context` alias (line 307), and `replay_table_layout` refusing non-results sections (line 417).

## Commands (tails)
- The ten committed suites, combined: `409 passed, 12 skipped in 15.53s`
- Per file:
  - original: 43
  - probes: 20
  - r2: 21
  - r3: 33
  - r4: 39
  - r5: 78
  - r6: 32
  - r7: 44
  - r8: 46 passed + 6 skipped
  - r9: 53 passed + 6 skipped
- Parser, binding and refresh suites: `59 passed`
- Drift (`bash -c` loop, `git diff <freeze> 0f974054e6bb --stat -- <file>`): empty for all nine; `git log --format=%an` gives `1 Sol CEO` for each.
- r11 probes: `46 failed, 13 passed in 12.81s`

## GAPS
- Not tested, because the ruling defers them to round 14: nested tables inside thead, a caption inside an unclosed td, the plain-text pipe table path, and the volume-statement path under a non-results section.
- Frozen RED counts at fec2bbac not reproduced.
- Reconciliation-paragraph path not probed with the new lexicon gaps. It uses the same `_marked_context`, so the same gaps are expected.
- Non-Q4 identities only for Q1 FY2027 and Q3 FY2026.
