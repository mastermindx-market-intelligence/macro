# Opus red-team of PR #7905 — round 13 (content head ef4931ee00be, 2026-09-24 ~22:05Z)

READ_ONLY Opus reviewer bounded to rulings R76–R80 (`SEAT_RULING_T1_PR_R12_2026-09-24.md`) with R27–R75 carried, under the stated acceptance bar. Recorded verbatim by the seat from the reviewer's report; the reviewer's 80 probe cases are frozen as `tests/test_pg_economic_observations_probes_r12.py` with f11, f12 and the "Q3'26" case of f15 struck by R81 and x25 adapted by R86 (39 of the remaining 77 RED at ef4931ee00be, 38 passed). Adjudication: `SEAT_RULING_T1_PR_R13_2026-09-24.md`.

# Opus T1 PR review — round 13 (PR #7905, content head ef4931ee00be, rulings R76–R80)

Reviewer: Opus (ROUTE: review / AUDIT, READ_ONLY). Probe file: `scratchpad/opus_r13_probes/test_r13_probes.py` (original synthetic HTML only).

## Verdict

STATUS: REJECT

Acceptance bar applied: REJECT if any of these holds. (a) A wrong bind. (b) A ruling violation that produces a wrong bind. (c) Frozen-suite drift or more than one author. (d) A materially false commit claim. (e) The validator accepts a forged workspace.
Blocking: (a)/(b) under R76, R77 and R79, plus shapes that no ruling covers. (e) under R80: the validator accepts a forged combined-subject absence.
Blocking rulings: **R76, R77, R79, R80**. R78 is PARTIAL.

Probe counts: **42 failed / 38 passed / 0 skipped** (80 cases).
- 28 wrong-bind failures: 16 extractor probes (w*) and 12 paired validator probes (v*). **Every paired validator probe ACCEPTS the wrong value.**
- 8 fail-closed refusals (f*).
- 2 gate failures (g20: a conflicting same-quarter volume sentence is skipped).
- 4 validator findings (x22 accepts a forged combined absence; x24 ×3 refuses or crashes on the extractor's own honest workspace).
- 0 nits.

## Baseline evidence (command tails)
- Twelve suites (original + r1..r11): `491 passed, 37 skipped in 25.07s`.
- Companions (disclosure_diff, binding, refresh): `59 passed in 4.80s`.
- Drift loop, run under bash (a first zsh attempt did not word-split and was discarded). Every file shows `drift=[]` against its freeze commit.
- Author loop: every file shows `authors=[Sol CEO,] commits=1`. Pairs checked: probes@7804e24a, r2@1970ea2b20, r3@fb50fdead4, r4@b371c84fc269, r5@1c7162e6678, r6@0cb12b40a96, r7@6ae7c4cb926, r8@03a47522942, r9@8c7ae72c649, r10@b64ce018534, r11@97fbeb6838a.
- r11 at head: `35 passed, 15 skipped`.
- r11 at 82c3df9a0043: `41 failed, 9 passed`. The `git archive` extract lived under the scratch folder and has been deleted.
- My probes: `PYTHONPATH=$PWD <venv python> -m pytest …/test_r13_probes.py -q -p no:cacheprovider --rootdir=$PWD -c /dev/null -W ignore` gives `42 failed, 38 passed in 6.79s`. The result is deterministic.

## Per-ruling verdicts
| Ruling | Verdict | Evidence (probe ids) |
|---|---|---|
| R76 years / band reading | NOT DISCHARGED | w01, w01b, w03 (+v01, v01b, v03 validator ACCEPTS); refusals f03, f11, f12; controls c18 (reversed, three-column) and c19 (drivers 2027 vs. 2026 / 2027 bind; 2026 / 2026 vs. 2025 refuse) pass |
| R77 hierarchy / title / labels | NOT DISCHARGED | w04 ×5, w05, w07 (+v04, v05, v07 ACCEPTS); refusals f13, f14, f15 ×2; controls c04, c05, c07 pass |
| R78 row groups / section rows | PARTIAL | c21 ×4 pass (two empty theads; stray `</thead>` then an empty thead; an empty tbody between groups; empty tfoot + empty thead + second thead). w10 (+v10 ACCEPTS): a section label row that carries a dash literal is never a section |
| R79 columns / marks / scans | NOT DISCHARGED | w02 (+v02 ACCEPTS); g20 ×2 falsifies "one that merely says 'the quarter' counts"; f16[US $] refusal; marks (iv) (ix) (x) (vi) (10a) (1b) pass; c16 (cy)/(ci) refuse as ruled |
| R80 validator | PARTIAL (blocking via x22) | x23 ×10 pass: forged plain absence refused for dil, prior, core, prior_core, tv, fx, beauty, rec, dash under the neutral-zero convention, and tv with an agreeing sentence. x25 (forged present) and x26 (forged period) refused; c23 honest dash absence accepted. **x22 ACCEPTS a forged combined absence over a present Mix value.** x24 ×3: the validator refuses or crashes on the extractor's own workspace |

## WRONG BINDS (each validator-accepted)

**W1 — the drivers heading judges only its first year (R76 violation).**
- Probes w01/v01 (Q4 FY2026): `<h2>Net Sales Change Drivers 2026 vs. 2023</h2>` with the standard drivers table. `pg_total_volume_growth_pct` = 1.0 binds, but a three-year stack is not the quarter's year-on-year change.
- Probes w01b/v01b (Q1 FY2027): `Net Sales Change Drivers 2027 vs. 2025` binds 1.0.
- Validator: ACCEPTS both.
- Cause: pg_profile.py:527 `_DRIVERS_YEARS` captures both years, but the judge at :632 compares only `m.group(1)`. `document_period_verdict` at :1003-1004 does the same.
- R76 admits the drivers heading only when it names the fiscal year "alone or beside its prior".
- Fix: require `int(m.group(2)) == fiscal_year - 1`, else foreign.

**W2 — a column-label metric's own column period is never judged (R79 construction flaw).**
- Probe w02/v02, drivers table under DRV:
  - Band row 1: `"" | "Three Months Ended June 30, 2026" (colspan 7) | "Three Months Ended June 30, 2025"`.
  - Band row 2: the seven driver headers, then `Net Sales Growth`.
  - Total P&G's last cell is `9.9%`.
- `pg_reported_sales_growth_pct` = 9.9 binds with period 2026-06-30. That is the prior-year quarter's value presented as current. Control c02: the current drivers still bind 1.0.
- Validator: ACCEPTS.
- Cause:
  - `_column` :1163-1172 decomposes the stack (the prior date is a recognised form, so the leftover is empty) and defers the period "elsewhere".
  - `_band_context` :355-357 returns "scope" whenever any one column is scope, so the foreign column is carried.
  - The column_label plan (:1205-1206) has no period form to match.
- Fix: for column-label metrics, `band_context` of the matched column's stack must not be foreign, annual or unknown.

**W3 — one non-matching column carrying the fiscal year flips the whole band to fiscal reading (R76 construction flaw).**
- Probe w03/v03 (Q1 FY2027): `SUB1` = `<h3>Three Months Ended September 30, 2026</h3>`, then band `"" | 2026 | 2025 | 2027 Guidance` and row `Diluted … | $3.20 | $3.07 | $13.00`.
- `pg_prior_diluted_eps` = **3.20** with period 2025-09-30. That is the current calendar-2026 quarter bound as the prior quarter.
- Validator: ACCEPTS.
- Also f03 (refusal): current `pg_diluted_eps` is missed.
- Cause: `_band_years` :1225-1232 collects every year in every band cell, so "2027 Guidance" sets `fiscal_mode`. `_band_headers` :1248-1255 then keeps "2026" as the prior form.
- Substitute rule: decide the reading only from columns whose stack is a pure bare year (the columns a plan can match). Refuse the table when those pure-year columns mix readings, or when a year appears only in a non-pure column.

**W4 — parentheticals are stripped before positive admission, so a forward or topic word in parentheses is invisible (R77 violation).**
- Probe w04 ×5 / v04: `<h2>Segment Organic Sales Growth (Outlook|Guidance|Long-Term Ambitions|Targets|Illustrative)</h2>` over GUIDE_T binds Beauty = 5.0. Control c04: `… Growth Outlook` refuses.
- Probe w05/v05: `<h2>Highlights (Pro Forma Combined Company)</h2>` + SUB + EPS table binds diluted EPS 3.07. Control c05: `Pro Forma Combined Company Highlights` refuses.
- Validator: ACCEPTS.
- Cause:
  - `_LABEL_NOISE` :572 strips any `\([^()]*\)` inside `_period_label_text` :742-747.
  - That feeds `_residual_words` :753-759, which both `_admits` :794 and `_is_neutral_topic` :849 use.
  - `_is_non_results_section` :860-863 returns "not non-results" on admission BEFORE its forward-word check, so the forward word never gets a look.
- Substitute rule: strip only the closed decoration set ("(unaudited)", "(in millions…)", footnote marks). Run the forward check on the full text before admission.

**W5 — a basis named at table level is not read.**
- Probe w06/v06: `<caption>Pro Forma Combined</caption>` on the EPS table binds 3.40 as GAAP diluted EPS.
- Probe w06b/v06b: `<p>Pro Forma (Unaudited)</p>` between SUB and the table binds 3.40.
- Validator: ACCEPTS.
- Cause: R79 recognises a basis word only inside the band stack over the matched column (:1163-1172). Captions are checked only for forward words (`_is_forward_caption` :828-833). A paragraph with no period token is prose and ignored (:967-968).
- Substitute rule: a caption or immediate label paragraph must decompose into period forms, decoration and route vocabulary, as headings must.

**W6 — the title exemption attaches to the first heading, not to a masthead (R77 construction flaw).**
- Probe w07/v07: `<p>Synthetic Co. reported results today.</p><h2>Supplemental Pro Forma Information</h2>` + SUB + EPS table binds 3.40. The first heading is a topic heading, and the exemption (`_SectionState.heading` :895, `self.seen == 1`) waives the topic rule.
- Control c07: the same h2 after a masthead h1 refuses.
- Validator: ACCEPTS.
- Substitute rule: extend the exemption only to an h1 whose words are issuer-name or neutral words. Any other first heading is judged as an ancestor.

**W7 — a caption inside an unclosed td is folded into the cell (declared open item 2; still a wrong bind).**
- Probe w08/v08: band YEARS, then `<tr><td>Diluted …</td><td>$12.00</td><td>$11.00</td><td><caption>Twelve Months Ended June 30, 2026</caption></tr>`.
- An HTML5 parser closes the cell and makes this the table caption. disclosure_diff.py:732-733 (`_append_text`) instead sends the text to the open cell, which lies outside the band width. Annual EPS 12.00 binds as Q4.
- Control c08: the caption in place refuses.
- Validator: ACCEPTS.

**W8 — a table nested in the thead of a twelve-month-captioned table (declared open item 1; still a wrong bind).**
- Probe w09/v09: the inner table is emitted as its own block ahead of the outer table. It inherits the TITLE heading, ignores the outer caption, and binds 12.00.
- Validator: ACCEPTS.

**W9 — a section label row that carries a dash is a data row (R78 PARTIAL).**
- Probe w10/v10: band YEARS, then `Twelve Months Ended June 30, 2026 | — | —`, then `Diluted … | $12.00 | $11.00`. 12.00 binds.
- Cause: `_section_text` :317 returns None when any cell is a literal, and a dash is a literal (:266).
- Validator: ACCEPTS.
- Realism is lower than W1–W6, but the shape is valid HTML and the value is annual.

## FAIL-CLOSED REFUSALS (non-blocking findings)
- f03 (R76): current EPS is missed under the `2027 Guidance` band (see W3). Minor.
- f11 (R76): the band `FY2027 | FY2026` in Q1 FY2027 refuses both EPS values. "fy2027" is a fiscal label, so `band_context` → "annual" (:725), and `_YEAR` has no word boundary inside "fy2027" (:529). Minor.
- f12 (R76): `First Quarter Segment Results 2026 vs. 2025` in Q1 FY2027 (the calendar spelling of the admitted quarter) refuses Beauty. `other_years_foreign` :649 accepts only the fiscal year and its prior. Minor.
- f13 (R77): `<h2>Fiscal Year 2026 Highlights</h2>` then `Three Months Ended June 30, 2026` refuses Q4 EPS. The ancestor is annual and a deeper heading cannot release it. Minor; this is common in Q4 releases.
- f14 (R77): `<h2>Q3 Highlights</h2>` in a Q3 FY2026 release refuses. "Q3" alone is an unknown token. Minor.
- f15 (R77): the labels `3Q FY26` and `Q3'26` refuse in Q3 FY2026; `Q3 FY26` binds. This is lexicon reliance (declared open). Minor.
- f16 (R79): the band mark `US $` (with a space) refuses. `_PLAIN_SUBCELL` :1107 needs `us$` contiguous. Nit-level minor.
- x24-entity (pre-existing receipt limit): a reconciliation paragraph that contains `&amp;` (for example "P&amp;G") is emitted absent: "not uniquely addressable in source bytes". A `&#36;3.07` cell or a comment inside the cell is also absent. The validator consequence is under VALIDATOR below.

## RULING-CONSTRUCTION FLAWS
1. R76 band reading (W3): "when the admitted fiscal year appears among its bare years" is judged over ALL band cells. It should be judged over pure-year columns only. The substitute rule is under W3.
2. R76 drivers years (W1): the implementation checks the first year only. Substitute: the second year must be the fiscal prior.
3. R77 title (W6): "the first heading block" is not "a masthead". Substitute rule under W6.
4. R77 decoration (W4): "whatever its punctuation or literals" becomes, in code, removal of every parenthetical before admission. Substitute rule under W4.
5. R79 "which period the stack names is judged elsewhere" (W2): for column-label metrics there is no "elsewhere". Substitute rule under W2.
6. R79 "one that merely says 'the quarter' counts" is false (g20 ×2). "Total P&amp;G volume decreased 2% in the quarter." and "… this quarter." are both skipped. `_other_period_sentence` :1480-1481 treats the residual "quarter" as a strong token, so the conflict never reaches `_volume_cross_check` and TV = 1.0 binds against a conflicting same-quarter sentence. Major (gate bypass), not counted as a wrong bind.

## VALIDATOR
- **x22 (blocking, bar (e))**: the drivers table carries both a `Volume/Mix` column and a separate `Mix` column. The extractor binds Mix = 0.5. A forged typed absence with subject `pg_mix_contribution_pp combined volume/mix` is ACCEPTED. economic_observations.py:264-273 checks only `combined_volume_mix_presentation` and never `pg_observation_present`, and R80 left this branch "unchanged".
  - Fix: refuse a combined absence when `pg_observation_present` is true.
- **x24 ×3 (major; an R80 regression and a false "full decision path" claim)**: `pg_observation_present` omits the extractor's receipt-minting step.
  - Entity paragraph: the extractor emits an honest absence (`_text_fact` :1593-1600). The validator then raises "typed_absence hides an observation the source uniquely addresses" (:1289-1290 accept the paragraph with no receipt), so the extractor's own workspace fails validation. Any real reconciliation paragraph that spells "P&amp;G" hits this.
  - `&#36;3.07` cell and `$3.<!-- x -->07` cell: `expected_receipt_span` returns None, and pg_profile.py:1309 `start, end = …` raises **TypeError** (only ValueError is caught at :1311). The validator crashes with a non-EconomicObservationError.
- Passes: forged plain absence refused across 10 classes (x23); forged present over an extractor refusal refused (x25, "replay_mismatch"); forged prior period refused (x26); honest dash absence without the convention accepted (c23).

## COMMIT-CLAIM CHECK
- 97fbeb6838a: every claim checks out.
  - 50 cases, none struck: 35 + 15 = 50.
  - RED at 82c3df9a0043 is 41 failed / 9 passed, reproduced.
  - Wiring into legacy-jobs.yml: 3-line diff.
- 51144e7194f: every claim checks out.
  - "Additive": the diff is only the new `group_layout`/`group_layout`/`table_groups` fields, their plumbing, and a comment. It is 16 lines and changes no existing reader.
  - 59 passed, reproduced.
- ef4931ee00be:
  - Checks out: the counts 491/37, 59 and 35/15 reproduce; `_PROSE_LITERAL` removed (2 → 0 occurrences).
  - **Materially false**: "`pg_observation_present` replays the extractor's decision path" (and ruling R80's "FULL decision path"). The receipt step is not replayed (x24). This is flagged under bar (d) as major; the verdict does not depend on it.
  - Also false: R79's "the quarter counts" (g20).

## FROZEN-SUITE INTEGRITY
All eleven frozen files show empty drift against their freeze commits at ef4931ee00be, and each has a single author (`Sol CEO`) and a single commit. No finding.

## Declared-open items probed
- Nested table in thead: W8 wrong bind.
- Caption in an unclosed td: W7 wrong bind.
- Plain-text table path: NOT probed. `parse_release_blocks` always passes `content_type: text/html`, and reaching the plain fallback (disclosure_diff.py:1013-1017) needs a tagless source that the `ws` fixture cannot produce. This remains a gap.
