# Opus red-team of PR #7905 — round 14 (content head 62ea826af1c4, reviewed 2026-09-24)

READ_ONLY Opus reviewer bounded to rulings R81–R86 (`SEAT_RULING_T1_PR_R13_2026-09-24.md`) with R27–R80 carried, under the stated acceptance bar. Recorded verbatim by the seat from the reviewer's report; the reviewer's 110 probe cases are frozen as `tests/test_pg_economic_observations_probes_r13.py` with the "last year" case of f11 struck by R94 (40 of the remaining 109 RED at 62ea826af1c4, 69 passed). Adjudication: `SEAT_RULING_T1_PR_R14_2026-09-24.md`.

# Opus review R14 — PR #7905, CDV-1 T1 (content head 62ea826af1c4), rulings R81–R86

Reviewer: Opus (ROUTE: review / AUDIT, READ_ONLY). Probe file:
`scratchpad/opus_r14_probes/test_r14_probes.py`, 110 cases, all original synthetic HTML.

**Acceptance bar:** REJECT only for (a) a wrong bind, (b) a ruling violation that produces a wrong bind, (c) a frozen-suite
integrity failure, (d) a materially false commit or ruling claim, (e) the validator ACCEPTING a forged workspace, or
(f) the validator raising something other than EconomicObservationError, or refusing the extractor's own honest workspace.
Fail-closed refusals are findings, but they do not block.

## Verdict

**STATUS: REJECT.** Blocking rulings: **R81, R82, R83, R84**. I found 8 wrong-bind shapes (17 cases), and the validator
ACCEPTS every one of them (17/17). The validator surface for R85 is clean.

Probe file result: **41 failed / 69 passed / 0 skipped**. Of the 41 failures, 17 are wrong binds (w*), 17 are
validator-accepted wrong binds (v*), 7 are fail-closed refusals (c01×2, f01, f08, f11×3), and none are nits.

## Command tails
- Thirteen suites: `556 passed, 49 skipped in 19.84s` (matches the claim).
- Companions (disclosure_diff, binding, refresh): `59 passed in 3.56s`.
- r12 alone at head: `65 passed, 12 skipped`. r12 at ef4931ee00be (a git archive extract, since deleted): `39 failed, 38 passed`.
- Drift loop: all 12 frozen files show `drift=[]`.
- Author loop: all 12 show `authors=[Sol CEO,]`.
- Probe file: `41 failed, 69 passed in 10.49s`.

## Per-ruling verdicts
| Ruling | Verdict | Evidence |
|---|---|---|
| R81 | NOT DISCHARGED | w01×3 plus v01×3 (wrong bind, validator accepts). c01×2 and f01 are refusals. f08 is a refusal. Controls pass: c07a–d (Q2 identities), c09a–c (pure-year marks, prior-only years), c19×4 (prior quarter beside a year-level drivers heading). |
| R82 | NOT DISCHARGED | w02×3 plus v02×3 (the units-note regex hides a basis). w08×2 plus v08×2 (outlook masthead exempt). Controls pass: c18×2, c18b, c18c, c02. |
| R83 | NOT DISCHARGED | w03×2, w04×2, w05×2, w06×2, each with its v pair (all accepted). c04 passes. |
| R84 | NOT DISCHARGED | w07 plus v07 (a footnote mark in a label row). f11×3 are refusals. Controls pass: c10, c10b, g11×2, c20×2. |
| R85 | DISCHARGED | x12 ×14: every honest workspace validates, including unit mismatch, conflict sentence, dash, out-of-scope, duplicate row, span, nbsp, comment and combined-only. x12b passes on Q2. x13 ×7: forged plain absences are refused. x14 ×2: forged combined absences are refused. x15 and x16: forged present values are refused. x17 ×5: malformed rows raise only EconomicObservationError. |
| R86 | DISCHARGED | The counts are verified exactly (see the command tails). Drift and authors are clean. The gate wiring adds the r12 path and run entry (legacy-jobs.yml). |

## WRONG BINDS (every one validator-ACCEPTED)
1. **W-A, R81: the drivers pair is judged only for the "vs." spelling.** In Q1 FY2027, the heading
   `Net Sales Change Drivers 2027 versus 2025` binds TV=1.0. So do `… 2027 compared with 2025` (Q1) and `… 2027 versus 2025` (Q2 FY2027).
   - Cause: `_DRIVERS_YEARS` at pg_profile.py:535 requires `vs\.?`. Otherwise the bare-year fallback at pg_profile.py:714 marks
     2025 as "prior", because `year in {fiscal_year - 1, current_end.year - 1}` includes current_end.year-1 = 2025. Then `_admits`
     (pg_profile.py:858-864) accepts {year, prior} on the drivers route. document_period_verdict (:1089) has the same gap.
   - This violates R81's "'2027 vs. 2025' are other tables" in another spelling. The inverse is a refusal: `2027 versus 2026`
     and `2027 compared with 2026` refuse (c01), because 2026 reads as "calendar".
   - Fix: judge any drivers year pair whatever the connective. In fiscal reading, "prior" must equal fiscal_year-1 only.
2. **W-B, R82: the `_DECORATION` units-note alternative is open-ended.** `in\s+(?:millions|thousands|billions)[^()]*`
   (pg_profile.py:582-586) treats everything up to ")" as decoration.
   - Probes: the heading `Three Months Ended June 30, 2026 (in millions, except per share amounts; pro forma combined company)`,
     the caption `(In millions, except per share amounts, pro forma combined company)`, and the paragraph `(In millions, pro forma combined)`.
   - All three bind DIL=3.40.
   - Fix: a closed units grammar (`in millions|thousands|billions[, except per share (amounts|data)]`) whose residual words stay words.
3. **W-C, R83: only the LAST paragraph is the table's label.** The paragraphs `Pro Forma Combined` then `(In millions, except per share amounts)`
   (or then `(Unaudited)`) sit over the table, and DIL binds 3.40.
   - Cause: pg_profile.py:1048-1051 overwrites `table_label` on every paragraph.
   - Fix: every consecutive short paragraph between the last heading or table and this table is a label, and each must be admissible.
4. **W-D, R83: word-count sentence detection.** Two probes bind DIL=3.40:
   - `Supplemental Unaudited Pro Forma Combined Company Information` (6 words, over the 5-word limit PG_TABLE_LABEL_WORDS=5 at :906).
   - `Pro Forma Combined Company Results for the Three Months Ended June 30, 2026`. This has 4 content words, more than
     PG_LABEL_CONTENT_WORDS=3, so it is not a period label. It is also longer than 5 words, so it is not a table label. It is
     treated as prose, and prose refuses only on a foreign or annual form.
   - This extends the open "Pro Forma." note: any basis-bearing paragraph over a table, whatever its length, must refuse.
5. **W-E, R83: the label vocabulary is the UNION of every route** (pg_profile.py:916). It includes the reconciliation route's
   `non-gaap`, `core`, `gaap` and `measures`.
   - The caption `Non-GAAP Results` and the paragraph `Core Results` over a table with a `Diluted Net Earnings per Common Share` row
     both bind 3.40 as GAAP diluted EPS.
   - Fix: use this plan's route vocabulary plus neutral and units words only. A basis word (`core`, `non-gaap`, `adjusted`)
     should refuse a GAAP metric's table.
6. **W-F, R83 parser: the OUTER table of a nested table stays readable after losing the nested text.**
   - Probe 1: the outer band cells hold nested tables `Three Months Ended March 31, 2026` and `… 2025`, over `2026 | 2025`.
     DIL binds 3.40 under the June heading.
   - Probe 2: a nested table in the outer's label column holds `Twelve Months Ended June 30, 2026`, and DIL binds 12.00 as Q4.
   - Cause: disclosure_diff.py:761 flags only the inner table (`nested=bool(self.tables)`), and `_append_text` (:732-738) routes the
     inner text away from the outer cell. pg_profile.py:1057 checks only `block.table.nested`.
   - Fix: flag the outer table too (a `contains_nested` field), and make it unreadable.
7. **W-G, R84: a label row with a footnote mark is a data row.** The row `Twelve Months Ended June 30, 2026 | (1) | —` is followed by
   the DIL row, and DIL binds 12.00 as Q4.
   - Cause: `_CURRENCY_PATTERN` (:131) reads "(1)" as a literal, and `_section_text` (:318) only exempts dashes.
   - Fix: value cells that are dashes, blanks or plain marks (`_PLAIN_SUBCELL`/decoration) keep the row a label row.
8. **W-H, R77/R82 title exemption: an outlook masthead naming the admitted quarter is exempt.** Two probes bind
   Beauty=5.0 from a goal table:
   - `<h1>Q4 Outlook</h1>` over `Segment Organic Sales Growth`.
   - `<h1>Fourth Quarter Fiscal Year 2026 Outlook</h1>` over the same heading.
   - Cause: pg_profile.py:951 exempts any forward word that sits beside a scope form. The form here qualifies the outlook itself.
   - Fix: a forward word in the title governs unless the title minus the forward clause is admitted as results
     (e.g. "... Results and FY2027 Outlook").

## FAIL-CLOSED REFUSALS (non-blocking)
- **c01 ×2:** `Net Sales Change Drivers 2027 versus 2026` and `… compared with 2026` refuse in Q1 (W-A cause). Severity: minor.
- **f01:** `Net Sales Change Drivers 2025 vs. 2026` refuses in Q4, because `_DRIVERS_YEARS` is order-sensitive. Severity: nit/minor.
- **f08:** `Quarter 3 Highlights` refuses in Q3. `_Q_BARE` at :530 reads only `q[\s-]?N`. By contrast, `Q-3`, `Q 3` and `q3` bind. Severity: minor.
- **f11 ×3:** the sentences `Total P&G volume increased 4% this fiscal year.`, `… for the fiscal year.` and `… last year.` count as
  same-quarter conflicts, so TV refuses. `_other_period_sentence` skips a sentence only on an explicit token. This is by R84's own construction.
  Severity: minor ruling-construction flaw, refusal only.

## RULING-CONSTRUCTION FLAWS
- **R81:** "names the admitted fiscal year AGAINST its prior" is implemented as one regex spelling (`vs.`). The bare-year path's "prior" set
  still includes current_end.year-1 beside a fiscal year (W-A).
- **R82:** the decoration set is not closed: the units note has an open tail (W-B). The title exemption's "scope form" test
  cannot tell "Q4 Results and FY27 Outlook" from "Q4 Outlook" (W-H).
- **R83:** has three flaws. The label is one paragraph, not the run of paragraphs (W-C). A word count stands in for sentence
  detection (W-D). The vocabulary is the union of all routes (W-E). The nested-table rule covers only the inner table (W-F).
- **R84:** the label-row exemption covers dashes only (W-G). "Explicit token only" makes year-level sentences refuse (f11).

## VALIDATOR
- Clean on every probe (x12–x17: 30 cases).
- The validator accepts every wrong bind above because it replays the same decision path. None of them is a forged workspace.
- No non-EconomicObservationError exception was raised. The extractor's own honest workspace always validated.

## COMMIT-CLAIM CHECK
- **40caa684703:** "77 executed cases" holds (65+12). "RED at ef4931ee00be: 39 failed, 38 passed" is verified. The gate
  wiring is present. Honest.
- **17689c5d76b:** "Parser, binding and refresh suites: 59 passed" is verified. "Additive: no existing field, id or reader changes"
  is true of the fields. However, the caption-in-cell close changes existing cell end offsets and row composition for that
  input. The new comment "carries none of the outer caption or band, so consumers treat it as unreadable" describes only the
  inner table and hides the outer-table loss (W-F). Severity: minor (not materially false).
- **62ea826af1c4:** the counts are verified. The R81 bullet "`_DRIVERS_YEARS` judged on both years (heading and document verdict)" is
  literally true but covers only the "vs." spelling. The claims that R81–R84 are discharged are refuted by W-A–W-H. Severity:
  major, as a consequence of the wrong binds rather than as a false count.

## FROZEN-SUITE INTEGRITY
- All twelve files show empty drift against their freeze commits (7804e24a … 40caa684703) at 62ea826af1c4, and each has the
  single author `Sol CEO`. Clean.

## GAPS
- The plain-text pipe-table path was not probed. Consistent with the seat's note, the fixture wraps HTML, and I did not find
  a route to it within budget.
- Q2 identities were probed on the EPS and drivers routes only, not the segment route.
