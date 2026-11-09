# Seat ruling — PR #7905 round 16 (on `OPUS_T1_PR_REVIEW_R16_2026-09-24.md`, content head 6a59d80bf261)

Adjudicator: the CDV-1 Meta-CEO seat (session 251f88c8, running Opus 5.5 under the fable-mode doctrine). The review is ACCEPTED:
- its five wrong-bind families W-A…W-E (26 wrong binds, every one validator-accepted);
- the contestable own_row_core_eps, which the seat adopts as blocking;
- its validator finding X (bytes sources raise AttributeError, bar f; an int metric and an empty mapping are accepted);
- its lexicon findings l02 and l_figure_unlisted;
- its commit-claim verdicts.

The head is REJECTED under the stated acceptance bar. The reviewer's 155 probe cases are frozen, with five struck at freeze (R113).

- **R106 (one lexicon reading; amends R99, R105).**
  - Every closed lexicon (presentation, measure, and the forward-looking title words) reads text through one reading:
    1. NFKC fold;
    2. invisible format characters removed (soft hyphen, zero-width characters, word joiner, BOM and their kin);
    3. every dash (U+2010–U+2015, U+2212, U+2E3A/B, U+FE58, U+FE63, U+FF0D) read as a hyphen;
    4. diacritics dropped;
    5. then `_normal`.
  - Text that cannot be read as written names every lexicon, so it refuses. That covers a bidirectional control, or a letter outside plain Latin (a Cyrillic "а", a small-capital "ʟ").
  - Only the PROSE reading reads a whole word in a script with no Latin look-alike (Han, kana, Hangul) as a foreign word the lexicons do not name. The frozen main fixture's "全球品牌 demand was stable…" is such a case. A word that mixes such a script with Latin letters is never read this way.
  - Labels, captions, headings and cells keep the strict reading. The positive label reading still refuses every word outside its vocabularies.
- **R107 (label cells and note rows; amends R99, R105).**
  - **Label cells.** A table's band-row stub cells, and every label-only row above its last value row, are LABELS. They are read positively like R89/R90 labels. Beyond the period tokens, which the band and row contexts classify (R37, R51), every word must belong to the label vocabularies or be a profile row name; otherwise the cell must be a closed note. "Pro Forma Combined" and "Non-GAAP" as the stub cell of the band, and a label row "As Adjusted:", refuse the table (W-B).
  - **Note rows.** A label-only row AFTER the last value row is a NOTE row. It is read like prose, by both closed lexicons, because the frozen S02 binds beside a free-text footer note. A full-width "Pro forma combined company", "Non-GAAP" or "Pro Forma" last row therefore refuses (W-B).
  - **Own-name exception.** R99's exception now reaches only the table's band cells and the names of its VALUE rows; a note row is not a name. It also requires a sentence that states a figure and carries no declaration word (R108).
    - "Amounts exclude the acquired business", as a footer row and in prose, refuses (own_footer_row).
    - So does "All per-share amounts in the table below are presented as Core EPS." (own_row_core_eps).
  - **R105 amendment.** A basis paraphrase outside the lexicons in a NOTE row is a LEXICON finding, as in prose. A band stub cell, or a label row above the last value row, stays a blocking structural path.
- **R108 (where each lexicon reads; amends R99, R101).**
  - **PRESENTATION** is read release-wide, over every heading, paragraph, caption, label cell and note row. Visible text anywhere in the release that the parser read into no block (R100, R109) is unread. Either one makes every table's band unknown. This closes W-C: para_before_topic, section_prose_then_subtopic and note_after_second_table.
  - **MEASURE** is read over the table's containing sections: its stretch (R99, R101), plus the paragraphs and topic headings of every topic section that contains it. Pure period headings are transparent here, as they end no stretch. The frozen main fixture forces section scope for narrative: its sibling "Non-GAAP Measures" section says "Core EPS excludes an incremental charge of 0.20…" while the frozen suites bind GAAP EPS in another section.
  - **Measure declarations.** A measure DECLARATION reaches every table in the release, wherever it stands. That is a sentence holding a measure-basis term together with either:
    - a declaration word: "table(s)", "below", "above", "following", "herein", "present(s/ed)", "shown", "stated", "reflect(s/ed)", "amounts", "figures", "all", "basis"; or
    - a scope word: "release", "document", "section", "exhibit", "schedule", "attachment", "appendix".

    Unreadable text counts as a declaration.
- **R109 (drawn text the parser drops; parser, additive; amends R100).** Inside a subtree the extractor drops, the parser now tracks whether text is DRAWN:
  - A metadata or script tag, `display:none`, or the `hidden` attribute with no inline display draws nothing beneath it.
  - `visibility:hidden` or `collapse` draws nothing until a descendant sets `visibility:visible`.
  - Everything else the parser drops is drawn: svg `<text>`, `ix:exclude` and `noscript` content, `aria-hidden` content (hidden from assistive technology only), and a "hidden" class, whose effect depends on a stylesheet the parser does not read.

  Drawn text sets R100's unread flags. An inline style is read with comments and whitespace removed; the last declaration wins unless an earlier one is `!important`. This closes W-D. The change is additive: one tracking list feeding the existing flags, with no field, id, hash or reader changed.
- **R110 (the title's results clause; amends R98).**
  - A results clause names results by a results NOUN only, "result(s)" or "earnings". The verbs "report(s/ed)", "announce(s/d)" and "deliver(s/ed)" no longer qualify.
  - A clause that also names a schedule word ("date(s)", "call(s)", "webcast(s)", "conference(s)", "schedule(d)", "timing", "time(s)") announces an event, not results. "P&G Announces Fourth Quarter Fiscal Year 2026 Earnings Date and Outlook" therefore governs (W-E).
  - "Preview" joins the forward-looking title words (l02).
- **R111 (validator input types; amends R102).** `validate_selected_facts` raises `EconomicObservationError` in two cases:
  - a `source_texts` key or value is not a string: bytes, int or list (x10 source_bytes, bar f);
  - a fact lacks a non-empty string `metric` (x10 fact_metric_int and fact_empty_dict).
- **R112 (lexicon folds, per R105).**
  - After R106's dash fold, every multi-part lexicon term takes `[\s-]*` between its parts. That covers "non-GAAP", "non-recurring", "one-time", "re-stated", "re-cast", "pro forma", "constant currency", "as adjusted" and "combined company". This closes W-A (12).
  - The presentation lexicon gains "post-" and "pre-" before acquisition, merger, combination or transaction, which closes l_figure_unlisted ("Post-Acquisition Entity Results 5%"). It also gains "restatement(s)".
  - The measure lexicon gains "core diluted …", "adjusted diluted …", "excl" and "exclusion(s)".
- **R113 (strikes at freeze).** Five of the reviewer's 155 cases are struck at freeze. Each is a fail-closed refusal of an honest document at the reviewed head, and each is recorded as a T1b finding rather than a blocker:
  - f07 nongaap_footnote_after: "Core EPS is a non-GAAP measure; see the reconciliation below." after the EPS table. It names "below", so it is a measure declaration under R108.
  - f07 forward_statements_after: "Results exclude no items." after the table.
  - f07 masthead_label: the all-caps "THE PROCTER & GAMBLE COMPANY AND SUBSIDIARIES" above the table. This has been open since R15.
  - c01 fy_pair_q1: "Net Sales Change Drivers FY27 vs. FY26" in Q1 FY2027.
  - c01 fiscal_pair_q2: "Net Sales Change Drivers Fiscal 2027 vs. 2026" in Q2 FY2027.

  Freezing them would pin, as T1's correct answer, a reading that T1b must settle against real releases. The f07 control unaudited_paren binds at the reviewed head and is kept.
- **R114 (tactic change: no round 17; T1 completes on a source envelope).** Round 19 consumes R16, and the synthetic red-team cycle stops there. No round-17 prose or grammar red-team is commissioned.
  - **Why.** Sixteen rounds have hardened a universal reading of synthetic markup, yet on real releases it binds 0 of 20 metrics (below). Every wrong bind the rounds found was also accepted by the validator, because the validator replays the same interpretation.
  - **Source.** This adopts, on the seat's own measurement, the GMI Meta-CEO direction on #7905 (comment 5825632041, 2026-09-25T02:22:28Z).
  - **New completion criterion for T1.** T1 is complete when it holds a finite first-release source/layout ENVELOPE, made of:
    - exact original issuer documents;
    - expected bindings authored and frozen independently of the production parser and validator (issuer, fiscal period, metric, unit/basis, source table/row/column);
    - structural admission kept separate from semantic extraction, so a document outside the envelope refuses with a typed unavailable state rather than inheriting a nearby grammar;
    - for each admitted family, one positive original-source witness, one near-neighbour refusal witness, and period/row/column/basis swap mutations.
  - **Suites.** The fifteen frozen suites stay as regressions. They are no longer the completion metric.
  - **Merge.** #7905 stays DRAFT, with no merge-on-green and no Ready, until the envelope lands and the carrier's hold is released. The T1b work below becomes T1's own remaining scope.
- **R115 (fifteen frozen suites; gate).** The fifteenth frozen suite, `tests/test_pg_economic_observations_probes_r15.py`, joins the gate job `earnings-economic-dossier` in both its paths and its run line. RED at 6a59d80bf261 is 60 failed, 53 passed, 37 skipped (150 cases). That is the reviewer's 65 failed, 53 passed, 37 skipped, less the five struck cases, which all failed.

Real-release measurement: a scratch-only diagnostic, not in any suite and not a gate.
- **Result.** The five most recent P&G earnings releases were read: 8-K Exhibit 99.1, FY25 Q4 through FY26 Q4, fetched from EDGAR. On each, the extractor binds 0 of 20 metrics at this head, as it did at 6a59d80bf261. The validator accepts each honest all-absent workspace.
- **Measured causes:**
  1. **No heading tags.** The Workiva template renders titles and section headings as bold `<font>` runs inside divs, so no table has a topic heading.
  2. **Unread text on every release.**
     - The SEC SGML `<DOCUMENT>` wrapper (TYPE, SEQUENCE, FILENAME, DESCRIPTION) before `<html>` flags block 0 on all five.
     - On FY26 Q1–Q3, the reconciliation-table titles ("Organic sales growth:", "Adjusted free cash flow …:") sit as direct text in a div that also holds the table, and that div is never emitted.

     Under R108, either one makes every band unknown.
- **Predicted by reading, not measured.** Causes 1 and 2 refuse first, so this was read rather than run: the Reg G paragraph ("the following provides definitions of the non-GAAP measures") is a measure declaration under R108 and will refuse GAAP metrics.
- **Remaining T1 scope (R114).** Called "T1b" in this record, the real P&G template envelope is now T1's own remaining scope, not a follow-up task. Its work:
  - read only the exhibit's `<TEXT>` body;
  - emit direct div text that sits beside a block child;
  - recognize the Workiva bold title and heading idiom;
  - settle the Reg G definitions paragraph and the five R113 strikes against real releases.

  It must do all of this without relaxing R99–R112. It is proven against the independently frozen expected bindings, never against the extractor's own scan.

Reviewer construction flaws and their dispositions:
- Dash-blind, ASCII-hyphen-only lexicon grammar → R106, R112.
- Labels confined to captions and paragraphs, and an own-name exception that counted note rows as names → R107.
- Stretch-bounded prose reading → R108.
- `_NONVISIBLE_TAGS` treating drawn content as invisible → R109.
- A verb-based results clause → R110.
- Untyped validator inputs → R111.

Left open for the envelope work (T1b, R114), and not blockers:
- The five R113 strikes.
- The real-template causes above.
- The plain-text table path, still unreachable through the fixture.
- Q2 identities on the segment route.

Process note: this round changes three engine files.
- `engine/company_intelligence/pg_profile.py`: R106–R108, R110 and R112.
- `engine/fundamental_forensics/disclosure_diff.py`: R109, additive.
- `engine/company_intelligence/economic_observations.py`: R111, two guards.

The validator still replays the extractor through the same `_table_scan` and `_candidate_tables`.
