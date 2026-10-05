# Opus red-team of PR #7905 — round 10 (content head fec2bbac89c4, 2026-09-24 ~19:35Z)

READ_ONLY Opus reviewer bounded to rulings R61–R65 (`SEAT_RULING_T1_PR_R9_2026-09-24.md`) with R27–R60 carried. Recorded verbatim by the seat from the reviewer's report; the reviewer's 60 probe cases are frozen as `tests/test_pg_economic_observations_probes_r9.py` with r03 struck by R66 (37 of the 59 frozen cases red at the freeze).

---

# Opus R10 red-team of PR #7905 @fec2bbac89c4 (rulings R61-R65; R27-R60 carried) — READ_ONLY

## VERDICT: REJECT. Blocking rulings: R62, R63 and R64 (wrong values that the validator accepts); R61 is PARTIAL (a wrong value from stray group end tags; the validator accepts it).

Probe file: `opus_r10_probes/test_r10_probes.py`, 60 cases: **38 failed, 22 passed**. Validator: every wrong value I built that the extractor binds is also ACCEPTED by `_verify_pg_replay`. Seven validator probes cover this (r04v, r06v, r10v, r13v, r20v, r30v, r31 through the shared scan), and none refused.

## Per-ruling table
| Ruling | Verdict | Evidence |
|---|---|---|
| R61 | PARTIAL | disclosure_diff.py:732/795 increments `row_group` on every thead/tbody/tfoot start and end tag, including stray end tags. HTML ignores those (no matching element in table scope). r04: YEARS, DILL row with `rowspan=2 $3.07`, a stray `</thead>`, then `Core EPS / $2.95`. A browser gives Core EPS = 3.07. The head clips the carried cell and binds **Core EPS = 2.95**, the prior-year cell. The validator ACCEPTS it (r04v). The same happens with stray `</tfoot>` (r05). disclosure_diff.py:76 uses Python `\s`, which accepts NBSP and U+3000 as leading whitespace (`colspan=" 2"` gives 2), but HTML skips only ASCII whitespace, so the value is 1 (r01 nbsp/ideographic). Discharged: `colspan="2 3"`=2, `&#50;`=2, `COLSPAN` on th=2, Persian digit=1, a rowspan clipped at an implied-tbody start tag (r07), uppercase `<H2>` level (r08), promoted all-caps level 0 (r34). |
| R62 | NOT DISCHARGED | **Regression (blocker):** pg_profile.py:295 `_RESIDUAL_MARKER` dropped `quarter`, and :312 now replaces the old `_PERIOD_MARKER` test. `_PERIOD_MARKER` (:489) is now dead code with no reference anywhere in engine/ or tests/. As a result "Third-Quarter Segment Results", "Quarter 3 Segment Results" and "Prior Quarter Segment Results" were `unknown` at af4212037b69 and are `None` at the head, verified by importing both modules side by side. The table under them binds **Beauty 4.0**, and the validator ACCEPTS it (r10, r10v, r10w). A period named without any marker word fails open: "Q3 2026", "3Q26", "2026 Q3", "Third Qtr.", "January to March 2026" all bind 4.0 (r10). Label paragraphs fail open too: a 64-char prefix plus "Three Months Ended March 31, 2026" (outside the :590 40-char bound), "March 31st, 2026", "Quarter Ended 31/03/2026", "Third-Quarter 2026" and "Three months to March 31, 2026" all bind the foreign drivers table, **TV 1.0**. The validator ACCEPTS the long-prefix case (r13, r13v). The converse of R62(b) is violated as well: "Q4 FY'26", "Q4 FY-26" and "Q4 FY ’26" give `annual`, because `_Q_FY` rejects `'`/`-` and `_FISCAL_YEAR_LABEL` then labels the text annual. "Fourth Quarter Fiscal-Year 2026" gives `unknown`. So the admitted year is refused where R62(b) says it binds (r11, 4 of 5 fail; this is fail-closed). R62(a)/(d) behave as ruled on r14 (the ordinary word "Fiscal Discipline" refuses the one drivers table, as the ruling requires), r15 and r16 (split-cell section label). |
| R63 | NOT DISCHARGED | pg_profile.py:635-638: a forward heading at a deeper level **re-bases** `self.level` downward. So Outlook(h2), then Guidance(h4), then Segment Results(h3) lets h3 release the h2 section. It binds **Beauty 4.0** and the validator ACCEPTS it (r20, r20v). The same flaw hits the reconciliation path: REC is present under Outlook > Guidance > Core EPS Reconciliation (r21). pg_profile.py:617: a heading that names the admitted quarter's results AND a next-year outlook ("Fourth Quarter Fiscal Year 2026 Results and Fiscal Year 2027 Outlook"; "...; Fiscal 2027 Guidance") is `foreign` by period_context, so it counts as forward. At h1 it then refuses **every** table in the release (DIL absent, r23 ×2). R63 says such a heading is "never forward-looking". Discharged: uppercase H2 Outlook governs h3 (r08); promoted OUTLOOK governs a real h3 and is released by h2 (r22, r22b); h1 Outlook refuses later h2 (r24, as ruled); "Segment Results vs. Expected" refuses (r25, as ruled). |
| R64 | NOT DISCHARGED | Code: pg_profile.py:843 `re.fullmatch(r"\$|\(.*\)", item)` is greedy, so "(Unaudited) Restated (Note 2)" counts as one parenthetical. The restated sub-column then binds **DIL 3.19** (r31). Construction: R64 makes any parenthetical plain, so "(As Reported)"/"(Restated)" sub-cells bind **DIL 3.19** from the restated column, and the validator ACCEPTS it (r30, r30v). Controls pass: three spanned columns with "", "(a)", "(b)" bind 3.07 (r32); "$" + "(unaudited)" binds 3.07 (r33). |
| R65 | PARTIAL | The eight frozen suites are byte-identical to their freeze commits. Each file has exactly one commit, by the single author "Sol CEO". The round-9 file differs from the reviewer's original in two disclosed places only: the docstring line and the q06 order-insensitive assertion. The gate job paths and run line include r8. False claim: fec2bbac's message says "with the parser, binding and refresh suites 369 passed". The companion suites give 59 passed, so the head total is 356+59=**415**. 369 is the round-11 base (310+59). This is the same arithmetic error R65 itself corrected. |

## Commit-message claims vs diff
- 03a47522942: the freeze, docstring, q06 adaptation and gate wiring are all TRUE. "32 failed / 20 passed at this head" was NOT verified (it would need a checkout).
- 9351cdb8db2:
  - "HTML rules for parsing non-negative integers (skip whitespace ...)" is PARTLY FALSE: Unicode whitespace is skipped, but HTML skips ASCII whitespace only.
  - "counts thead/tbody/tfoot boundaries (explicit or implied, start and end) ... clip rowspans the way HTML does" is FALSE for stray end tags, which HTML ignores.
  - "parser, binding and refresh suites green" is TRUE (59 passed).
- fec2bbac89c4:
  - "until a heading of the same or a higher level" is FALSE (re-base, r20).
  - "a heading naming the admitted quarter's results is never forward" is FALSE (r23).
  - "_FISCAL_YEAR_LABEL reads ... and a foreign year makes the text foreign" is TRUE for the forms listed. The admitted-year Q-FY variants are refused (r11).
  - "310 -> 356" is TRUE. "369" is FALSE (415). "46 passed, 6 skipped" is TRUE.
  - Undisclosed: `quarter` was removed from the fail-closed marker set, and `_PERIOD_MARKER` was left dead.

## Ruling-construction flaws (separate from code violations)
1. R61 "0 reads 1" and "bounded 1..64": HTML `rowspan="0"` spans to the end of the row group, and HTML clamps rather than resets (colspan ≤1000, rowspan ≤65534). The ruling's "exactly as HTML" claim is false for 0 and 65 (r02, r03).
2. R61 does not address visual order. With a tfoot before the tbody (HTML4-mandated order), the browser renders the tfoot last. `_row_contexts` walks DOM order, so a tfoot data row escapes a later twelve-month section and binds **Core EPS 12.5**. The validator ACCEPTS it (r06, r06v).
3. R62(a) lists markers (`ended|ending|month(s)|ytd|fiscal|fy`), and that contradicts its own headline "the rule, not a list". Periods named with no marker word fail open (Q3 2026, 3Q26, 2026 Q3, Third Qtr., month ranges).
4. R62(c): the forty-character bound leaves longer label paragraphs unread. Labels are recognised only in "pure" forms, so an unparseable label paragraph ("31st", "31/03/2026", "months to") is silently ignored instead of yielding `unknown`.
5. R63 depends on a closed forward vocabulary. "Looking Ahead", "Plan", "Framework" and similar are unlisted. The ruling also refuses its own admitted results when the title adds a next-year outlook, unless the scope test is "names the admitted quarter" rather than `period_context == "scope"`.
6. R64 "a parenthetical is plain": "(Restated)" / "(As Reported)" carry the same distinction as the unparenthesised forms in q22.

## Evidence (commands)
- Combined 9 committed suites: `356 passed, 6 skipped in 11.37s`.
- r8 alone: `46 passed, 6 skipped`.
- Companions (disclosure_diff, earnings_release_binding, company_intelligence_refresh): `59 passed`.
- Frozen drift: `git diff <freeze> fec2bbac89c4 --stat -- <file>` was empty for all 8 files. `git log --format=%an` gave 1 commit, "Sol CEO", for each.
- q06: `diff opus_r9_probes/test_r9_probes.py tests/test_pg_economic_observations_probes_r8.py` showed hunks at line 1 (docstring) and 71 (q06) only.
- Probes: `pytest opus_r10_probes/test_r10_probes.py` gave `38 failed, 22 passed`.

## Gaps
- The parent-head "32 failed" claim was not re-run.
- The volume-statement forward path (r26 passed) is inconclusive: the synthetic has no drivers table, so TV may never resolve through the volume path.
- Not tested: nested tables inside a thead, a caption inside an unclosed td, quarters other than Q4 as the identity, the plain-text table path, and round-6 disposition (a).
- Severity: the r04/r06 inputs (stray end tags, HTML4 tfoot order) are rarer in real EDGAR output than the R62/R63 shapes.
