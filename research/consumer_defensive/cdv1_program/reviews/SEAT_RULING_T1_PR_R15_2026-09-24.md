# Seat ruling — PR #7905 round 15 (on `OPUS_T1_PR_REVIEW_R15_2026-09-24.md`, content head 4e9706aa070d)

Adjudicator: the CDV-1 Meta-CEO seat (session 251f88c8, running Opus 5.5 under the fable-mode doctrine). The review is ACCEPTED in full: its four wrong-bind families W-A…W-D (25 wrong binds, every one validator-accepted), its refusal findings (f04 ×4), its validator nit (x14 `fact_not_dict`) and its commit-claim findings. The head is REJECTED under the stated acceptance bar. The reviewer's 134 probe cases are frozen with no case struck (R104).

- **R97 (drivers years; amends R87).** Whether the text names the fiscal year is judged on the WHOLE text — bare years, "FY27"-style labels and apostrophe years — before the drivers pair is removed. It is no longer judged on the residual. A bare year beside the admitted quarter is "prior" when it is fiscal year − 1. It is also "prior" when it is the year before the quarter-end calendar year, but only if the text names no fiscal year. In Q1 and Q2 FY2027, "Net Sales Change Drivers 2027 vs. 2026 vs. 2025" therefore refuses (w01b, w01c), like its frozen Q4 analogue (r13 c01b).
- **R98 (title; amends R93).** The title's clauses split as in R93. A forward word in the level-1 title governs unless both of these hold:
  - a clause WITHOUT a forward word names RESULTS ("result(s)", "earnings", "report(s/ed)", "announce(s/d)", "deliver(s/ed)") together with a scope form of the admitted quarter;
  - no clause WITH a forward word names the admitted quarter.

  These titles head the quarter: "… Results and Fiscal Year 2027 Outlook" (c02) and "… Results and Outlook" (frozen Q29). These govern: "Fourth Quarter and Fiscal Year 2026 Outlook", "… — Outlook", "… &amp; Guidance", "… | Outlook", "First Quarter and Fiscal Year 2027 Outlook" and "…: Outlook" (W-B ×8), and so does "… Results; Fourth Quarter Fiscal Year 2026 Outlook".
- **R99 (what stands around a table; amends R89).** A table's stretch is every paragraph between its topic heading (or the previous table) and it, plus every paragraph after it up to the next topic heading or table (R101). Pure period headings do not end the stretch.
  - **Labels vs prose.** A paragraph is a LABEL unless it ends in ".", "!" or "?" or states a figure ("$" before a digit, a percent). The bullet "Diluted EPS of $3.07, up 5% versus the prior year" is therefore prose (f04).
  - **Labels.** Labels and the caption are read positively, against the R89/R90 vocabularies, or must be one of the closed notes:
    - the dash convention;
    - the rounding note (f04);
    - the lead-in "The following table(s) presents/shows/sets forth/summarizes the results/amounts/figures", or "The results/amounts/figures (for the quarter/period) were/are as follows" (f04). A trailing colon is allowed.
  - **Prose.** Prose cannot be admitted positively, because the frozen P5, Q31, S16, S17 and R32d suites bind beside narrative. It is read by two CLOSED lexicons:
    - **PRESENTATION basis**, which refuses the table for every metric: "pro forma" in any spelling (including "proforma"); "combined" or "merged" before company, results, basis, entity, group, business(es) or operations; "as though" / "as if"; "give/gives/given/giving effect"; "supplemental"; "illustrative"; "hypothetical"; "recast"; "restated"; "successor"; "predecessor".
    - **MEASURE basis**: "non-GAAP"; "core" before basis, EPS, earnings, results or measures; "adjusted" before basis, results, EPS, earnings, amounts, figures or measures; "as adjusted"; "exclude(s/d)" and "excluding"; "constant currency"; "currency neutral"; "comparable basis"; "before special / one-time / non-recurring items". It refuses the table for every metric whose own basis is not core or organic.
  - **Own-name exception.** A measure word does not refuse when it lies inside a repetition of one of the table's own column or row names. "Total P&G volume excluding acquisitions and divestitures increased 3%" names the table's own column (frozen R32d), and "Core EPS increased 5%" names its row. "Amounts below exclude the acquired business" names the table's basis and refuses.
  - **Where each lexicon is read.** The measure lexicon is read per metric in `_candidate_tables`, which the validator replay shares. The presentation lexicon, the labels and the unread flags (R100) make the band unknown in `_table_scan`. W-C is closed (9 cases), and so are the f04 refusals.
- **R100 (unread text; parser, additive).** `DisclosureBlock` gains `unread_before` and `unread_after`. They are layout facts, kept out of `to_dict` and out of every id and hash, and default False. They are set when visible text reaches no emitted block, marking the next block (or the last block at the end). That text is:
  - text outside every block;
  - a `<center>` or `<figcaption>` outside a block;
  - text directly inside a `div` that is never emitted;
  - stray text inside a table outside its cells and caption.

  The engine treats a table whose stretch holds unread text as unreadable. This closes W-D's `<center>`, `<figcaption>` and bare `<span>` cases, in the extractor and the validator alike.
- **R101 (after the table).** The stretch after a table is read exactly like the stretch before it: labels, notes, both lexicons and unread flags. "The table above presents pro forma combined company results." refuses, for both the EPS and the segment table (W-D note_after). A label placed above a pure period heading is inside the stretch (W-D label_above_heading).
- **R102 (validator).** A `facts` entry that is not a mapping raises `EconomicObservationError` (x14 `fact_not_dict`).
- **R103 (commit claims).** 4e9706aa070's counts stand. Its claim to have discharged R87, R89 and R93 is refuted by W-A…W-D. That is major as a consequence of the wrong binds, not a false count. 491d63ffe59 and d9a689756b4 are reproduced as claimed.
- **R104 (fourteen frozen suites; gate).** The fourteenth frozen suite, `tests/test_pg_economic_observations_probes_r14.py`, joins the gate job `earnings-economic-dossier` in both its paths and its run line. No case is struck. RED at 4e9706aa070d is 55 failed / 61 passed / 18 skipped (134 cases), reproduced by the seat on a git-archive tree of that head.
- **R105 (review standard for the prose lexicons, from round 16).** R99's reading of prose is closed by necessity, since the frozen suites bind beside narrative. A basis paraphrase that neither lexicon names is recorded as a LEXICON finding. The seat folds the term into the lexicon in the next repair, and such a finding does not block acceptance on its own. It stays BLOCKING under bar (a)/(b) when:
  - it is a spelling, hyphenation, entity or whitespace variant of a listed term;
  - a listed term fails to match (a defect of the lexicon's own grammar);
  - the basis rides a structural path rather than prose (a label, a caption, a heading, a band or row cell, unread markup, or the stretch boundaries).

  Whether a paragraph is a label or prose is decided by R99's closed test.

Reviewer construction flaws and their dispositions:
- R87's fiscal-year test on the residual → R97.
- R93's clause split, which exempted any quarter clause → R98.
- R89's negative list, its backward-only scan and its label test that ignored figures → R99 and R101.
- Markup the parser drops → R100.

Left open for round 19:
- The plain-text table path, which is unreachable through the fixture.
- Q2 identities on the segment route.
- The all-caps masthead paragraph that the parser promotes to a heading. It fails closed, and is to be measured against a real release at live verification.
- Real-release refusals from the measure lexicon beside a reported table, for example a non-GAAP footnote directly after the consolidated earnings table. These fail closed and are measured at live verification.

Process note: this round changes three files.
- `engine/company_intelligence/pg_profile.py`: R97–R99 and R101.
- `engine/fundamental_forensics/disclosure_diff.py`: R100. The change is additive: two new block fields plus the tracking that sets them, with no existing field, id or reader changed.
- `engine/company_intelligence/economic_observations.py`: R102, one guard. The validator still replays the extractor through the same `_table_scan` and `_candidate_tables`; the latter is now passed the metric's basis string.
