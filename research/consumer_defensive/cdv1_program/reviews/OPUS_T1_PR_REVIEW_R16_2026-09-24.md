# Opus red-team of PR #7905 — round 16 (content head 6a59d80bf261, reviewed 2026-09-24)

READ_ONLY Opus reviewer bounded to rulings R97–R105 (`SEAT_RULING_T1_PR_R15_2026-09-24.md`) with R27–R96 carried, under the stated acceptance bar. Recorded verbatim by the seat from the reviewer's report file. The reviewer's 155 probe cases are frozen as `tests/test_pg_economic_observations_probes_r15.py` with five cases struck at freeze (R113): 150 cases, RED at 6a59d80bf261 60 failed, 53 passed, 37 skipped. Adjudication: `SEAT_RULING_T1_PR_R16_2026-09-24.md`.

# Opus review R16 — PR #7905 (CDV-1 T1) at content head 6a59d80bf261

Reviewer: Opus 5.5, ROUTE: review / AUDIT, MODE: READ_ONLY. Probe file:
`scratchpad/opus_r16_probes/test_r16_probes.py` (original synthetic HTML only).

## Verdict: REJECT

Bars hit: (a)/(b) wrong binds, every one validator-ACCEPTED (bar e); (f) the validator raises AttributeError.

## Probe summary at head 6a59d80bf261

`65 failed, 53 passed, 37 skipped` (155 cases). Command:
`PYTHONPATH="<wt>" <venv>/bin/python -m pytest <probe> -q -p no:cacheprovider --rootdir="<wt>" -c /dev/null -W ignore`

Blocking failures = w*/v* pairs in families W-A..W-E, plus x10 source_bytes. Non-blocking failures: c01 (2), f07 (3), l02 (1),
w04/v04[l_figure_unlisted] (lexicon), x10 fact_metric_int / fact_empty_dict (see X).

## Blocking wrong binds (metric pg_diluted_eps unless stated; expected = no value; actual = 3.40; validator = ACCEPTS)

Shared tail: `TITLE + SUB + <X> + PF_T` where PF_T = `<table><tr><td></td><td>2026</td><td>2025</td></tr><tr><td>Diluted Net Earnings per Common Share</td><td>$3.40</td><td>$2.93</td></tr></table>`.

### W-A — listed-term variants (R99 lexicons; R105 blocking: spelling/hyphenation/entity/whitespace variants) — 12 binds
Prose paragraph `<p>…</p>` before PF_T:
- re_stated: "The results below are re-stated for the merger." (listed: restated)
- re_cast: "The results below are re-cast for the merger." (listed: recast)
- non_recurring_space: "Amounts below are before non recurring items." (listed: non-recurring)
- nonrecurring: "Amounts below are before nonrecurring items."
- one_time_space: "Amounts below are before one time items." (listed: one-time)
- proforma_nbhyphen: "…on a pro&#8209;forma basis." (U+2011; `pro[\s-]*forma` only ASCII hyphen)
- proforma_endash: "…on a pro&#8211;forma basis."
- nongaap_nbhyphen / nongaap_endash: "The following table presents non&#8209;GAAP / non&#8211;GAAP results." (`_NON_GAAP_SPELLING = \bnon[\s-]?gaap\b`)
- constant_nbhyphen: "Amounts below are on a constant&#8209;currency basis."
- as_adjusted_nbhyphen: "The results below are as&#8209;adjusted for the merger."
- combined_nbhyphen_company: "The results are presented for the combined&#8209;company."
Root cause: `_PRESENTATION_BASIS`/`_MEASURE_BASIS` (pg_profile.py:953-963) and `_NON_GAAP_SPELLING` (:484) accept only `[\s-]`
between parts, and "non-recurring"/"one-time" are literal with a mandatory ASCII hyphen; `_normal` (:488) folds no Unicode dashes.
Controls that DID refuse: "give\neffect", "before special items", "combined-company results", "Successor".

### W-B — basis in a structural cell (R105: band/row cell) — 7 binds
- footer_row_proforma: PF_T with extra last row `<tr><td colspan="3">Pro forma combined company</td></tr>`
- footer_row_nongaap: same, cell "Non-GAAP"
- th_colspan_last: same, `<tr><th colspan="3">Pro Forma</th></tr>`
- section_row_adjusted: row `["As Adjusted:", "", ""]` above the diluted row
- stub_header_proforma: header row `["Pro Forma Combined", "2026", "2025"]` (the stub cell of the band)
- stub_header_nongaap: header row `["Non-GAAP", "2026", "2025"]`
- own_footer_row: `<p>Amounts exclude the acquired business.</p>` + PF_T with footer row cell "Amounts exclude the acquired business" —
  R99's own refusing example sentence is excused by `_names_own_basis` (:971) because every body row's first cell is a "name".
Controls that DID refuse: band "2026 As Adjusted", band "Non-GAAP" over YEARS, band "2026 Excluding Charges", caption "As Adjusted".
Root cause: labels = caption + paragraphs; no band stub cell, section row or footer row is read for basis, and `_names_own_basis`
treats any body-row first cell (including a footer note row) as a name that licenses the same words in prose.

Contestable (reported blocking, seat to adjudicate): own_row_core_eps — `<p>All per-share amounts in the table below are presented as
Core EPS.</p>` + table with rows Diluted (3.40) and "Core EPS" → DIL binds 3.40; the "core eps" measure match is excused as a
repetition of the row name although the sentence declares the table's basis.

### W-C — stretch boundaries (R105: "the stretch boundaries") — 3 binds
- para_before_topic: `TITLE + <p>All amounts in this release are pro forma combined company results.</p> + <h2>Financial Highlights</h2> + SUB + PF_T`
- section_prose_then_subtopic: `TITLE + <h2>Financial Highlights</h2><p>Amounts in this section are presented on a pro forma combined basis.</p><h3>Diluted Net Earnings per Common Share</h3> + SUB + PF_T`
- note_after_second_table: `TITLE + SUB + PF_T + <table>(2026/2025; Net Sales $21,000/$20,000)</table><p>The tables above present pro forma combined company results.</p>` — the note reaches only table 2's after-stretch; table 1 binds.
Controls that DID refuse: note_before_first_table ("The tables below present pro forma combined company results." then a Net Sales table then PF_T; PF_T refused — cause not traced, so the stretch law is not claimed to be what refuses it), after_period_heading, label_after_period_heading.

### W-D — visible text the parser drops (R100 / R105 unread markup) — 3 binds
- svg_text: `<svg width="300" height="20"><text x="0" y="15">Pro Forma Combined</text></svg>` before PF_T (svg is in `_NONVISIBLE_TAGS`, disclosure_diff.py:690, but `<text>` renders)
- aria_hidden_visible: `<p aria-hidden="true">Pro Forma Combined</p>` (aria-hidden hides from assistive tech only; it renders) — `_is_nonvisible` :741
- ix_exclude: `<p>Diluted EPS <ix:exclude>Pro Forma Combined</ix:exclude></p>` (ix:exclude content is displayed; it is excluded only from the fact value)
Controls that DID refuse: nested div text, inline `<b>`, `<br>` in div, stray text between rows, text after table in div, `<section>` text,
`<summary>`, `<dt>`, `<font>`, `<tr>Pro Forma Combined</tr>`. `display:none` stays invisible (c06 binds, correct).

### W-E — R98 results word in an outlook title — 1 bind (metric pg_beauty_organic_sales_growth_pct, wrong 5.0)
- announces_date: `<h1>P&amp;G Announces Fourth Quarter Fiscal Year 2026 Earnings Date and Outlook</h1><h2>Segment Organic Sales Growth</h2>` + GUIDE_T → BEAUTY binds 5.0, validator ACCEPTS.
  Literal R98 admits it ("announces"/"earnings" + scope form in the non-forward clause), so this is a construction flaw of R98 that produces a wrong bind.
All other forward-clause spellings refused (q4_bare, fourth-hyphen, quarter-ended, Q4 FY26, month range, FY 2026, fourth fiscal quarter).

### X — validator surface (bar f)
- x10 source_bytes: `source_texts={k: v.encode()}` → validator raises **AttributeError: 'bytes' object has no attribute 'encode'** at economic_observations.py:324 (`source_bytes = source.encode("utf-8")`; :321-323 checks only `source is None`, never `isinstance(source, str)`). Blocking, bar (f). Any non-str source (int, list) takes the same path.
- x10 fact_metric_int (`facts[0]["metric"] = 7`) and fact_empty_dict (append `{}` to facts): validator ACCEPTS the malformed workspace (minor; no PG value forged — the PG facts are untouched).
- x08 forged present over refused tables (note_after, center, non-GAAP prose, row-gap text, div-after text): all REFUSED (pass).
- x09 forged absence over own-name core / (FY-pair skipped: not bound): REFUSED; honest workspace validates.

## Non-blocking findings
- c01 fy_pair_q1 "Net Sales Change Drivers FY27 vs. FY26" (Q1 FY2027) and fiscal_pair_q2 "Net Sales Change Drivers Fiscal 2027 vs. 2026" (Q2) refuse (fail-closed honest).
- f07 nongaap_footnote_after "Core EPS is a non-GAAP measure; see the reconciliation below." after the EPS table refuses DIL (seat open item); "Results exclude no items." refuses; all-caps masthead paragraph refuses (seat open item).
- l02: title "Fourth Quarter Fiscal Year 2026 Earnings Preview" + GUIDE_T binds 5.0 — "preview" is not in `_FORWARD_LOOKING` (title-lexicon gap).
- l_figure_unlisted: "Post-Acquisition Entity Results 5%" is prose by the figure test and neither lexicon names it → binds (LEXICON finding under R105).

## Per-ruling verdicts
| Ruling | Verdict |
|---|---|
| R97 | HOLDS — 8 three-year / prior-pair forms refuse (w01 all pass); two honest FY-label / "Fiscal" pairs over-refuse (non-blocking) |
| R98 | PARTIAL — other-spelling forward clauses all refuse; "Announces … Earnings Date and Outlook" binds guidance (W-E) |
| R99 | FAILS — W-A (12 variant binds), W-B (7 structural cell binds incl. own-name via footer row), W-C (3 boundary binds) |
| R100 | PARTIAL — the R100-scope cases all refuse; svg/aria-hidden/ix:exclude visible text still dropped (W-D) |
| R101 | HOLDS for the after-stretch as defined; note beyond the next table escapes (W-C note_after_second_table) |
| R102 | HOLDS for non-mapping facts; empty mapping / int metric accepted; bytes sources raise AttributeError (X) |
| R103 | Not re-litigated |
| R104 | HOLDS — r14 frozen, wired, RED 55/61/18 at 4e9706aa070d reproduced |
| R105 | Applied as the standard above |

## Commit-claim verdicts
- 86cfa154284: r14 at 4e9706aa070d = `55 failed, 61 passed, 18 skipped` — REPRODUCED.
- 872bedf642b: companions `59 passed`; fourteen prior suites (main + probes..r13) `648 passed, 66 skipped`; r14 `55 failed, 61 passed, 18 skipped` — all REPRODUCED.
- 6a59d80bf26: fifteen frozen suites `739 passed, 109 skipped`; r14 `91 passed, 43 skipped`; companions `59 passed` — all REPRODUCED. Its claim to discharge R99/R100 is refuted by W-A..W-D.

## Frozen-suite integrity
All fourteen probe suites: blob at HEAD == blob at freeze commit; single commit each; sole author "Sol CEO"; each path appears twice in
`.github/ci/legacy-jobs.yml` (paths + run line) for `earnings-economic-dossier`. Note: that job carries `if: ${{ false }}` like all 232
legacy jobs (it runs through the ci-pack runner), not a defect.

## Old-head comparison (context, not a bar)
Same probe file on a git-archive tree of 4e9706aa070d: `95 failed, 34 passed, 26 skipped`. Round 18 closed 30 cases (R97 three-year forms,
R100 div/table stray text, several prose lexicon hits); W-A..W-E and the bytes AttributeError survive and are largely pre-existing
construction gaps that R99/R100/R105 now bring inside the blocking standard.

## Repair pointers (for the seat; not prescriptions)
- W-A: fold Unicode dashes (U+2010-2015, U+2011, U+2212) and optional hyphen/space into every multi-part lexicon term in `_normal` or the
  patterns (`non[\s-]?recurring`, `one[\s-]?time`, `re-?stated`, `re-?cast`).
- W-B: read the band stub cell, full-width/section rows and trailing note rows as labels; restrict `_names_own_basis` names to cells
  that carry values (not note rows).
- W-C: decide whether a document- or section-level basis sentence (before a topic heading, or naming "the tables above/below") reaches
  every table it names.
- W-D: treat svg `<text>`, aria-hidden and ix:exclude content as visible text (unread or read), not dropped.
- W-E: require a results word that is not a mere "announces … date" (or treat "date"/"call"/"webcast" as non-results).
- X: type-check `source_texts` values in the validator.
