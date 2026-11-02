# Opus red-team of PR #7905 — round 15 (content head 4e9706aa070d, reviewed 2026-09-24)

READ_ONLY Opus reviewer bounded to rulings R87–R96 (`SEAT_RULING_T1_PR_R14_2026-09-24.md`) with R27–R86 carried, under the stated acceptance bar. Recorded verbatim by the seat from the reviewer's report file (the reviewer reached its turn limit after writing the report and before sending its return packet; the seat reproduced the counts independently). The reviewer's 134 probe cases are frozen as `tests/test_pg_economic_observations_probes_r14.py` with no case struck (55 RED at 4e9706aa070d, 61 passed, 18 skipped). Adjudication: `SEAT_RULING_T1_PR_R15_2026-09-24.md`.

STATUS: REJECT

# Opus round-15 red-team of PR #7905 (CDV-1 T1) at content head 4e9706aa070d, rulings R87-R96

Probe file: opus_r15_probes/test_r15_probes.py (134 cases): **55 failed, 61 passed, 18 skipped**.
The 55 failures break down as 25 wrong binds (w), 25 validator acceptances paired with them (v), 4 fail-closed refusals (f), and 1 validator nit (x14).
Every wrong bind below is ACCEPTED by validate_selected_facts.

## Blocking findings (acceptance bar a/b)

### W-A: FY-2 beside the drivers pair reads as "prior" in Q1/Q2 (R87 violation, bar b)
- Probes: test_w01b_three_year_drivers_q1, test_w01c[three_year_q2]; validator checks test_v01c[three_year_q1, three_year_q2].
- Input: `<h1>First|Second Quarter Fiscal Year 2027 Results</h1><h2>Net Sales Change Drivers 2027 vs. 2026 vs. 2025</h2>` above the drivers table.
- Expected: refusal. The frozen Q4 analogue "2026 vs. 2025 vs. 2024" refuses (r13 c01b).
- Actual: pg_total_volume_growth_pct = 1.0 is bound, and the validator accepts it.
- Cause: pg_profile.py:704 removes the pair (2027, 2026) from the residual. At :742, `fiscal_year not in years` then tests only the residual years, so 2025 == current_end.year-1 is read as "prior".
- R87 says: "a bare year beside the fiscal year is 'prior' only when it is fiscal year − 1". This heading names the fiscal year, so reading 2025 as prior violates that rule.
- Controls that hold: "2027 vs. 2026 and 2026 vs. 2025" and "2027 versus 2026 (2025 Basis)" both refuse. Every separator variant of a {2026, 2025} pair also refuses in Q1/Q2 (for, colon, comma+versus, em dash, slash; w01, 6 cases).

### W-B: R93's clause split lets an OUTLOOK title head the quarter (bar a; the ruling construction is itself the defect)
- Probes: test_w02 (4 cases) and test_w02b (4 cases); validator checks test_v02 and test_v02b (all 8 accepted).
- Inputs (level-1 title + table, wrong value bound):
  - "Fourth Quarter and Fiscal Year 2026 Outlook" over a segment goal table: BEAUTY 5.0.
  - "Fourth Quarter Fiscal Year 2026 — Outlook": BEAUTY 5.0.
  - "… &amp; Guidance": BEAUTY 5.0.
  - "… | Outlook": BEAUTY 5.0.
  - "Fourth Quarter and Fiscal Year 2026 Guidance" + SUB + a DILL table: DIL 3.40.
  - "Fourth Quarter Fiscal Year 2026 — Outlook" + drivers table: TV 1.0.
  - Q1 "First Quarter and Fiscal Year 2027 Outlook" over a segment table: BEAUTY 5.0.
  - Q2 "Second Quarter Fiscal Year 2027: Outlook" over a DILL table: DIL 3.40.
- Cause: pg_profile.py:1001 (`_TITLE_CLAUSE`) and :1017-1019. Splitting at "and", "&", ":", "|" or a spaced dash cuts the forward word off from the quarter it qualifies. The quarter clause with no forward word then exempts the title.
- Compare: frozen w08 "Fourth Quarter Fiscal Year 2026 Outlook" refuses, but adding " — " or "and" flips it to a bind.
- Controls that hold: "Q4 Outlook: Fourth Quarter Fiscal Year 2026" and "Q4 and Fiscal Year 2026 Guidance" refuse. "… Results and Fiscal Year 2027 Outlook" binds actuals (c02).

### W-C: prose presentation basis outside the R89 negative list (bar a)
- Probes: test_w03 (6 cases) and test_w03b[segment_proforma, drivers_combined, q1_non_gaap]; validator checks test_v03 and test_v03b (all 9 accepted).
- Inputs: a prose paragraph between the heading and the table.
  - DIL 3.40 bound under each of: "Proforma combined results are presented below.", "The following table presents non-GAAP results.", "Combined results are presented below.", "…give effect to the merger as though it closed…", "Amounts below exclude restructuring charges.", "…shown on a core basis."
  - Segment "…shown on a proforma basis.": BEAUTY 4.0.
  - Drivers "…presented on a combined basis with the acquired business.": TV 1.0.
  - Q1 FY2027 "…presents non-GAAP results.": DIL 3.40.
- Cause: pg_profile.py:943-945 (`_PRESENTATION_BASIS`) and :1129.
  - "proforma" as one word is an unlisted spelling of a LISTED term, since `pro[\s-]+forma` requires a separator.
  - "non-GAAP" and "core" are the very bases R90 keeps off GAAP EPS labels, yet in prose they pass.

### W-D: a basis named after the table, above its heading, or in markup the parser drops (bar a)
- Probes: test_w04[note_after, center, figcaption, bare_span, label_above_heading] and test_w03b[segment_note_after]; validator checks v04 and v03b (all 6 accepted).
- Inputs:
  - A table followed by `<p>The table above presents pro forma combined company results.</p>`: DIL 3.40. The segment version binds BEAUTY 4.0.
  - `<center>Pro Forma Combined</center>`, `<figure><figcaption>Pro Forma Combined</figcaption><table>`, or a top-level `<span>Pro Forma Combined</span>` directly above the table: DIL 3.40.
  - `<p>Pro Forma Combined</p>` placed above the SUB heading: DIL 3.40.
- Cause:
  - `_table_scan` looks only backwards and resets `run` at every heading or table (pg_profile.py:1106, :1132). No trailing note is ever read.
  - disclosure_diff.py:679 `_BLOCK_TAGS` omits center and figcaption, and inline text at body level is not a block. That text never reaches the engine or the validator replay.
- Controls that hold: a title row inside the table, "2026 Pro Forma" band columns and a "Pro Forma Diluted…" row label all refuse.

## Non-blocking findings
- **Refusal, major.** test_f04 (4 cases): honest tables are refused because of the R89 "any length, no terminal punctuation" rule and the negative list. Honest diluted EPS 3.07 is not bound under each of:
  - a `<li>` bullet "Diluted EPS of $3.07, up 5% versus the prior year";
  - "The results for the quarter were as follows:";
  - "Amounts may not add due to rounding";
  - benign prose containing "Adjusted" ("Adjusted for the reclassification of prior-period amounts, …").

  Bullets and colon lead-ins between a heading and its table are common in releases. Cause: pg_profile.py:963 `_label_shaped` and :1129.
- **Nit.** test_x14[fact_not_dict]: a non-mapping entry appended to `facts` is accepted. The validator only keeps `pg_` mapping rows (economic_observations.py validate_selected_facts, the facts filter at approximately lines 35-41). It is not a forged observation. The other malformed shapes (empty sources, facts not a list, a string scope) raise EconomicObservationError only.
- Validator surface is otherwise clean:
  - x11: the extractor's own honest workspaces validate in 8 new shapes.
  - x12: forged absences are refused in 4 cases.
  - x13: forged present values over refused tables (two-line label, core label, contains_nested, outlook title) are refused in 4 cases, raising EconomicObservationError only.

## Per-ruling verdicts
| Ruling | Verdict | Evidence |
|---|---|---|
| R87 | NOT DISCHARGED | W-A. Connectives and separators otherwise hold (w01 ×6, c01, r13 c01/f01/w01). |
| R88 | DISCHARGED | w07 ×4 refuse; c07 ×2 bind; r13 w02/c02 pass. |
| R89 | NOT DISCHARGED | W-C and W-D wrong binds; f04 refusals. |
| R90 | DISCHARGED | w08 ×3 refuse GAAP EPS; r13 w05 passes. |
| R91 | DISCHARGED | w09 (nested table in a later row) refuses; x13 contains_nested forge refused; parser change additive (491d diff). |
| R92 | DISCHARGED | w06, w06b and c06 all pass. |
| R93 | NOT DISCHARGED | W-B: the code matches the ruling text, and the ruling construction produces wrong binds. |
| R94 | DISCHARGED | "Quarter N" beside YTD, nine months, a year or fiscal year refuses (w05 ×5); quarter phrases inside a year-level phrase still conflict (g11 ×2). |
| R95 | Counts reproduced | 62ea826af1c4 r13 RED is 40 failed / 69 passed. |
| R96 | DISCHARGED | r13 wired at .github/ci/legacy-jobs.yml:13593/13604; RED count reproduced. |

## Commit claims
- d9a689756b4, "RED at 62ea826af1c4: 40 failed, 69 passed (109 executed)": REPRODUCED (`40 failed, 69 passed in 3.57s` on a git-archive tree of 62ea826af1c4 with the frozen r13 file).
- 491d63ffe59: REPRODUCED.
  - Companions: `59 passed in 2.97s`.
  - r13: `40 failed, 69 passed in 3.30s`.
  - pg_profile.py is byte-identical to 62ea826; the diff is additive (a new field plus propagation).
- 4e9706aa070: counts REPRODUCED.
  - Fourteen suites: `648 passed, 66 skipped in 29.27s`.
  - r13: `92 passed, 17 skipped in 4.29s`.
  - Companions: `59 passed in 3.35s`.
  - economic_observations.py unchanged 62ea826..4e9706 (git diff --quiet).
  - Its claim to have discharged R87, R89 and R93 is refuted by W-A..W-D. Per the R95 precedent this is major, as a consequence of the wrong binds, not a false count.
- Frozen suites: all 13 are byte-identical to their freeze commits (freeze blob = HEAD blob = worktree), each with one commit and the single author "Sol CEO".

## Gaps
- The plain-text table path was not probed.
- The all-caps masthead heading promotion was not probed (the ruling already names it as a refusal).
- The volume-sentence skip was probed only for quarter-inside-year phrasing.
