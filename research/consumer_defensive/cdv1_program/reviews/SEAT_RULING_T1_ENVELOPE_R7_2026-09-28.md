# Seat ruling — T1 envelope, audit round 7 (R179–R186)

Adjudicator: the CDV-1 Meta-CEO seat (session 251f88c8, running Opus 5.5 under the fable-mode doctrine).

Source: the independent Opus re-audit of the round-6 repair at `b6808dfcc16` (PR #7905). The audit was READ_ONLY and ran as four independent groups. G1, G2 and G3 returned **REJECT**. G4's run ended at the Opus weekly usage limit, so its report is a working draft whose status reads PENDING; its blocker is complete. The report is committed beside this record as `OPUS_T1_ENVELOPE_AUDIT_R7_2026-09-25.md`, with each group's report verbatim.
- The findings:
  - eight blockers: G1-B1, G1-B2, G2-B1, G2-B3, G2-B4, G2-B5, G3-R7-B1 and G4-B1;
  - minors G1-m1, G2-m2, G3-R7-m1 and G4-m1; the nit G4-n1; observations G2-O1, G3-O1–O3 and G4-O1;
  - a note on the seat's round-6 testimony, which G4 left unclassified.
- The seat found two more blockers and one minor of its own:
  - S-R7-1, a present row whose period is a list or a mapping makes the validator raise `TypeError`, in its read of the refusal paths while grounding G2-B4 (R183);
  - S-R7-2, the span check reads a character reference as `html.unescape` decodes it, where a reader prints another character or the reference as written, in its reading of G2's `&#1;`-prefixed relocations and of G4-B1's repair against html5lib 1.1 (R185);
  - S-R7-3, the release parser this PR added converts a span's digits whole, so a span past Python's 4,300-digit limit raises `ValueError` before the envelope runs, in its re-run of G1-m1's seven-thousand-digit form through the public path (R181).
- The seat re-ran each group's probe file at `b6808dfcc16` and with the repair. G1 runs on Python 3.14 with html5lib 1.1; G2, G3 and G4 run on 3.12 and 3.14 with only pytest and pyyaml.

  | group | cases | at `b6808dfcc16` | with the repair |
  |---|---|---|---|
  | G1 | 914 | 12 failed, 902 passed | 5 failed, 909 passed; each accounted for below |
  | G2 | 41 | 41 failed on 3.12; 40 failed and 1 passed on 3.14, which is G2-m2's split | 18 failed and 23 passed, on both; the 18 are G2-B1's relocations, inside R176's rule (R182) |
  | G3 | 423 | 28 failed, 393 passed and 2 skipped, on both | 21 failed, 400 passed and 2 skipped, on both; each accounted for below |
  | G4 | 29; the file's seven integrity cases i1–i7 read the audited worktree's git state and do not run on a copy | 14 failed, 15 passed, on both | 29 passed, on both |

  - G1's five failures with the repair:
    - Three are `test_f0_B2[&#11-before-*]`, which fail at `b6808dfcc16` too. G1's report classifies them as its own construction: a `&#11` without a semicolon absorbs the literal's first digit (`&#111.63` reads `o.63`), the metric is unlocated and the workspace validates.
    - Two are G1's controls for `title` and `iframe` inside the note. G1 expects the note to bind, because a browser prints neither element's content in the page. R180 leaves the note absent around any raw text other than `script` and `style`, so PCORE is unlocated. That is fail-closed, and R180 names the cost.
  - G3's 21 failures with the repair:
    - 18 are the Q1 and Q2 parameters of G3-R7-B1's probe (16, eight figure forms) and of its plain-year control `test_f8_core_year_restored_by_a_plain_year_banner_binds` (2). They fail on G3's harness error `('core_reconciliation', 2026)`: the harness takes FY 2026 as the title year, while the Q1 and Q2 titles print calendar 2025. G3's report names the error. R179's witnesses realise the finding on Q1–Q3, each with its own title year.
    - Three are O1's `Fiscal Year` banner controls. G3 expects them to bind; the banner refuses the table's signature, fail-closed, as G3 says.
  - The four round-6 probe files give the same split with the repair as at `b6808dfcc16`:
    - G1's `g1_B` and OBSERVE subset: 6 failed, 13 passed, as R177 accounted;
    - G2: 11 failed, 7 passed, R176's eleven accepted relocations;
    - G3: 148 passed, 9 skipped;
    - G4: 5 failed, 14 passed. The five are i1–i5, which read the audited worktree.

- The audit confirmed the positive work:
  - every round-6 finding is closed on its construction and on the variants each group built: G1's B1–B3, M1, m1 and m2, S1 and R178's admission check; G3's B1 (17 new variants), B2 (117) and B3 (156);
  - G1's family-0 re-run reproduces R177's account of the round-6 G1 file's 122 failures exactly;
  - family 16 confirms R178's comparison over the 234,737 code points Unicode 3.2 assigns, on 3.11, 3.12 and 3.14. R163's ASCII grammar refused every case-folded or Unicode-spaced spelling G1 tried;
  - family 15 read 7,272 documents against html5lib 1.1, including 488 sources captured from the seven frozen suites. It found 1,134 admitted with 0 table or title divergences, and 0 exceptions;
  - family 11 read 11,175 fuzz documents. It found 0 exceptions from the build or the validator, 0 of the extractor's own outputs rejected, and 0 divergences between a span and its cell literal;
  - family 4 accepted none of 429 one-byte shifts, widenings and narrowings, and the validator refused each of 144 builds forced past the gate;
  - G4's integrity checks hold:
    - the freeze is followed by exactly ten commits, each touching only the two engine files;
    - the r1–r5 suites and the fixtures are byte-identical;
    - the seven suites pass on 3.12 and 3.14 (700), and `curated_exclusive` passes;
    - the a5a and capital-structure suites match `f8e4af5aa4c` test by test (213);
    - the five earlier probe files fail exactly round 6's sets, by name;
    - R177's testimony at the freeze reproduces (105 failed, 595 passed), once one harness artefact of G4's archive is discounted;
  - G4's code review finds two new `try` nodes, each ending in the validator's own refusal and reading no source. The new refusal messages are exactly R174's and R176's. There is no per-release literal, sentinel or probe-specific branch.
- Hosted CI at `b6808dfcc16`, read once by the seat after the audit: every binding check passed and `ci-gate` reported success. The only red is `ci-authority/codex/merge-queue-pilot`, which is non-binding. G4 had read it once while ci-pack-5 and ci-pack-6 were still running.

This record amends R116–R178 only where it says so. Everything else there stands.
- One frozen file changes. `tests/test_pg_envelope_f1_probes_r5.py` drops from R166's accepted list the case R185 refuses, and the docstring's clause naming it. Nothing else in that file changes.
- `tests/test_pg_envelope_f1.py`, the `_r1` to `_r4` and `_r6` suites, and `tests/fixtures/pg_envelope/` stay byte-identical.
- The rulings below are enforced by the new frozen suite `tests/test_pg_envelope_f1_probes_r7.py` (R186).
- The seat grounded every factual premise below in its own runs on the six originals, in memory with the engine's reader. No finding is ruled on the audit's word alone.

## Severity

The bars are the commission's review standard: (a) wrong bind, (b) present fact outside F1-Q, (c) validator acceptance of a tampered workspace, (d) integrity, and (e) positional or literal admission.

| finding | audit | seat | ruling |
|---|---|---|---|
| G3-R7-B1, a year-bound pin binds when its only year is printed as a figure | BLOCKER (e) | BLOCKER; on Q1–Q3, over CORE and PCORE | R179 |
| G3-R7-m1, title years read digits other than ASCII | minor | no bind reproduces; the title's reading is aligned with the header's as defence in depth | R179 |
| G1-B1, R173 blanks raw text a reader prints inside the note | BLOCKER (b) | BLOCKER | R180 |
| G1-B2, a reference the engine drops inside the note gates it | BLOCKER (b) | BLOCKER; and the odd characters G1 names beside it | R180 |
| G1-m1, a span is expanded to its full width before admission refuses it | minor (d) | minor; repaired. Its seven-thousand-digit form raised `ValueError` in the engine's grid | R181 |
| S-R7-3 (seat), the release parser raises `ValueError` on a span past Python's 4,300-digit limit | — | minor (d); G1-m1's public-path half, repaired with it | R181 |
| G2-B1, relocations into and inside the tables are accepted through the seam | BLOCKER (c) by the letter | inside R176's rule; the rule is restated to name them, and the check is unchanged | R182 |
| G2-B3, a numeric value too large for a float raises `OverflowError` | BLOCKER (d) | BLOCKER | R183 |
| G2-B4, a workspace `event_id` that is not a string raises `TypeError` | BLOCKER (d) | BLOCKER | R183 |
| G2-B5, workspace `sources` that are not a list raise `TypeError` | BLOCKER (d), inherited | BLOCKER | R183 |
| G2-m2, nesting deeper than the interpreter reads raises `RecursionError` | minor (d) | repaired; refused on both interpreters | R183 |
| S-R7-1 (seat), a present row whose period is a list or a mapping raises `TypeError` | — | BLOCKER (d) | R183 |
| G4-B1, the whole-token check reads characters Python calls space as a printed boundary | BLOCKER (c) | BLOCKER; R155's gap check has the same root | R184 |
| G4-m1, `str.isspace` in the gap check and the edge check | minor | the root of G4-B1; repaired with it | R184 |
| S-R7-2 (seat), the span check reads a character reference as Python decodes it | — | BLOCKER (c) | R185 |
| G4-n1; G2-O1, G3-O1–O3 and G4-O1; the testimony note | nit; observations; note | disposed of below | R186 |

- **G3-R7-B1 and G3-R7-m1 are one rule: a year is named only where a reader reads one.**
  - R170 skipped a single figure and read every other ASCII `20dd`. A `20dd` carrying a figure's sign, bracket, point or percent (`$2026`, `2026%`, `(2026)`, `+2026`, `#2026`, `2026.`) is not a figure under `_FIGURE`, which wants a separator past three digits. So its digits were read as the year, and the pin under it bound.
  - A period title read its day and year with `\d`, so a title printing `2٠26` named 2026 while the same characters in a header named none (R170). G3's Q1 and Q2 binds ran on titles its probe never edited; with each quarter's own year, all three quarters are refused `unknown_table`, before and after the repair.
  - R179 reads both with one ASCII grammar. Every form outside it names no year, so the repair moves toward unlocated pins.
- **G1-B1 and G1-B2 are R173's and R172's classes, carried into the note.**
  - R173 blanked every raw-text element in the note's region. Text a reader prints (`xmp`, `textarea`) was dropped from the sentence, so `for Core EPS<xmp> except a $0.12 restructuring charge</xmp>.` read as R157's sentence.
  - R172 refuses dropped references and odd characters inside cells only. The note is read outside every cell, so `no&#1; adjustments` read as the sentence while html5lib prints U+0001.
  - R180 reads the note only where every character of its region prints as the sentence. Each repair leaves the note absent, so PCORE's second statement moves toward unlocated.
- **G2-B3, G2-B4, G2-B5, G2-m2 and S-R7-1 are integrity (d).** A validator that raises on a tampered row has not refused it; that is R176's rule for G2-B2. R183 refuses each with the validator's own error.
- **G4-B1 and S-R7-2 are R174's rule read with Python's readers instead of a reader's.**
  - `str.isspace` calls `\x0b`, `\x1c`–`\x1f` and `\x85` space. HTML does not, and html5lib prints `-\x1c1.63` as one token, which is R174's own witness `-1.63`.
  - `html.unescape` decodes `&#1;` to nothing, so the check saw no character at the literal's edge where a reader prints U+0001.
  - `html.unescape` reads a reference and its neighbours as one run of text. `&#91.63` prints `[.63`, but the engine's span `1.63`, decoded apart from its left, reads `1.63`.
  - Inside raw text a reader may print a reference as written: an `xmp` prints `&nbsp1.63` as one token.
  - R184 and R185 read the token's edges, its gaps and its interior as a reader prints them. Each check refuses, so the repair moves toward refusal.
- **G2-B1 is inside R176's rule, and no code changes (R182).**
  - The eighteen relocations are whole tokens of text the engine reads. Each is a literal in one of three places:
    - a comment between a `>` and a `<` inside the pinned cell, the pinned row or the last table, which is R166's limit;
    - a new row of the last table;
    - another cell printing the same literal.
  - R176's rule is that the span check proves a whole token that parses to the value, and never where it sits. Placement is replay's job (R143). R176's prose said "outside the tables" because its eleven witnesses sat there; the rule never depended on it.
  - The alternative, a containment check in the validator, is rejected for R176's reasons. It needs a second table reading there: either the extractor's own, or a grammar that must track R163's. And a relocation from one cell to another would still pass it; G2's 958 accepted cell-to-cell relocations are that case.
  - R114 is kept: the validator is neither relaxed nor changed for these cases.
- **G1-m1 and S-R7-3 are repaired together (R181).**
  - G1-m1's cost is linear in the span's value (G1: 7.94 s at 10^7), and at ten digits the grid would hold 10^9 entries. Its seven-thousand-digit form raised `ValueError` in the engine's own grid at `b6808dfcc16`.
  - Through the public path the same form raised one step earlier. The release parser this PR added (R49–R66) converted the span's digits whole (S-R7-3).
    - The parser's span reading is this PR's own code: `git show 8a8ecbe868ff:engine/fundamental_forensics/disclosure_diff.py`, at the merge base, holds no `_span_value`, and neither does current `main`.
  - The seat swept every conversion of source digits to an integer in the four T1 modules: `pg_envelope.py`, `pg_profile.py`, `economic_observations.py` and `disclosure_diff.py`. Every other one reads a bounded run: years (`20\d{2}`, `[0-9]{4}`), days (`\d{1,2}`), heading levels, and R163's admitted spans (`[1-9][0-9]{0,4}`). `float()` does not raise on a long run of digits; it reads infinity, which R183's finiteness check refuses.

## Rulings

- **R179 (G3-R7-B1, G3-R7-m1; amends R147, R165 and R170). A year is named only where a reader reads one.**
  - **A header value.** A footnote marker `(d)` reads as a space. Then a `20dd` not bounded by digits names a year only when both of these hold:
    - **before it** stands the value's start, a letter or digit (`FY2026`, `CY2026`), an abbreviation's point (`Sept. 2026`), a comma or slash (`2025, 2026`, `2025/2026`), or a range dash (`2025-2026`, `2025 - 2026`), with spaces where the grammar allows them;
    - **after it** stands the value's end, a letter or digit (`2026E`), or such a separator followed by a letter, a digit or the end.
  - **Every other `20dd`** stays in the rest of the value. A numeric character left there makes the years unreadable (R170, R178). So `$2026`, `2026%`, `(2026)`, `$(2026)`, `+2026`, `-2026`, `#2026`, `$ 2026`, `2026.` and `2026.5` name no year, and neither does `2,026`. A value holding one leaves every pin under it unlocated.
  - **A period title** reads its day and year in ASCII digits only.
  - **The witnesses (48).** The governing core reconciliation's title loses its year. A banner across its table then prints the year only as a figure, in eight forms: `$2026`, `2026%`, `(2026)`, `$(2026)`, `+2026`, `-2026`, `#2026` and `2026.`. Each leaves CORE unlocated, and the same forms over the prior table leave PCORE unlocated, on Q1–Q3.
  - **The grammar (28).** Fifteen values name exactly their years, including `2025 (1)`, `(1) 2025`, `Fiscal 2025`, `No. 2025` and `2025 and 2026`. The eleven figures above name none. So do `2025 (a)` and `2025*`, which are the rule's recorded coverage cost: both named their year at `b6808dfcc16`, and the pins under them are now unlocated. These cases read `_named_years`, which `b6808dfcc16` lacks, so they fail there by construction; they pin the grammar.
    - **Amended by R188** (round 8, `SEAT_RULING_T1_ENVELOPE_R8_2026-09-29.md`): `No. 2025` and `2025x` name no year. Both left R179's table in the R7 suite and moved to `tests/test_pg_envelope_f1_probes_r8.py`.
  - **The controls.** The same banner printing the plain year binds CORE and PCORE to their frozen values (6). With the title's year removed and no banner, CORE and PCORE are unlocated (6).
  - **The title (9).** The core reconciliation's title printing its year in Arabic-Indic, mixed or full-width digits is refused `unknown_table`, on Q1–Q3, at `b6808dfcc16` and with the repair. The table's signature already reads only ASCII. R179's title hunk is defence in depth: reverted alone, it fails no case.
  - **Verified on the originals.** On both interpreters, the header years over every printed cell of the six originals are unchanged, and so are admission and the workspace's sha256 (the census, R186).

- **R180 (G1-B1, G1-B2; amends R157 and R173). The prior-year note is read only where every character of its region prints as the sentence.**
  - The region between the core reconciliation and the next table is read as before. Any one of three things leaves the note absent, so it does not gate PCORE's second statement:
    - **raw text other than `script` and `style`** in the region. A reader may print it (`xmp`, `textarea`) or not (`title`, `iframe`, `noscript`, `noembed`, `noframes`), and the engine does not model which;
    - **a character reference** that `html.unescape` decodes to nothing;
    - **a decoded character** that R172 refuses in cells: a control other than tab, LF, CR and FF, or whitespace HTML does not treat as whitespace.
  - `script` and `style` content is blanked, as R173 does.
  - **The witnesses (21), each leaving PCORE unlocated on Q3.**
    - Printed raw text inside or after the sentence (9): `xmp` and `textarea` in two places each, and `noscript`, `noembed`, `noframes`, `iframe` and `title` holding G1's clause.
    - A dropped reference in the sentence (6): `&#1;`, `&#127;`, `&#xFDD0;`, `&#xFFFE;`, `&#xFFFF;` and `&#x10FFFF;`.
    - An odd character in the sentence (6): `\x0b`, `\x1c`, `\x1f`, `\x85`, U+2028 and U+3000.
  - **The controls (5).** `script` or `style` inside the note binds PCORE 1.54. So does a no-break space inside the sentence, as `&#160;`, `&nbsp;` or the character.
  - **Hunk by hunk.** Each of the three checks, reverted alone, fails exactly its own witnesses: 9, 6 and 6.
  - **The cost.** G1's controls for `title` and `iframe` in the note are now unlocated: html5lib prints both, a browser prints neither in the page, and R180 does not choose. The P&G notes hold no raw text.
  - **Verified on the originals.** No note region holds raw text, a dropped reference or an odd character, and the workspace is unchanged (the census).

- **R181 (G1-m1, S-R7-3; amends R61's and R163's reading of spans). A span is read at its limit before it is converted or the grid is expanded.**
  - **The envelope.** `_grid` reads `colspan` and `rowspan` at most at their limits, 1000 and 65534. A value past six significant digits is read as the limit without being converted. R163 still refuses the document as `markup_unreadable:span`.
  - **The release parser.** `_span_value` reads a value past six significant digits as 10^6 without converting it.
    - R66 already reads every span above 64 as absurd: the cell is laid out as 1 and the overflow is flagged.
    - So no reading changes. Only the conversion that raised is gone.
  - **The witnesses.**
    - A ten-digit and a seven-thousand-digit `colspan` on the Q3 diluted-EPS cell are read by the grid as 1000 (2).
    - The same two spans, through the public path, refuse the document (2).
    - At `b6808dfcc16` the seven-thousand-digit form raised `ValueError`: in the grid when read directly, and in the release parser through the public path.
    - The ten-digit forms are not run there: without the clamp the grid expands 10^9 entries, which exhausts memory.
  - **Hunk by hunk.**
    - With only the grid hunk reverted, both seven-thousand-digit cases fail, because the public path expands the grid before admission refuses. The ten-digit cases are not run.
    - With only the release parser's hunk reverted, the public seven-thousand-digit case fails alone.
  - **Measured.** With the repair, admission refuses spans of 10^7 and 10^9, and the seven-thousand-digit span, in 0.03–0.05 s on 3.12. The unedited original admits in 0.09 s.
  - **Verified.**
    - The originals' largest span is far below every limit, and admission and the workspace are unchanged (the census).
    - The six release-parser test files outside the gate give the same outcome, test by test, at `b6808dfcc16` and with the repair: `test_fundamental_forensics_disclosure_diff`, `test_earnings_release_binding`, `test_company_intelligence_event_workspace`, `test_company_intelligence_refresh`, `test_capital_structure_document_terms` and `test_issuer_profiles_a5a`. All 289 outcomes match: 273 passed and 16 failed at both. The 16 read git state or `.github/workflows`, which the seat's scratch trees lack.

- **R182 (G2-B1; extends R176's rule). The span check proves a whole token; replay proves where it sits, inside the tables as outside them.**
  - R176's rule stands as written. Through the seam, which replaces replay's receipt, a relocation onto a whole token of the text the engine reads is accepted, wherever the token sits: outside the tables, inside a comment within a table, in a new row, or in another cell.
  - Without the seam, replay mints the receipt from the source bytes and refuses each relocation: "selected observation does not replay from source bytes."
  - **The frozen cases, each accepted through the seam and refused by replay without it (18).**
    - Four relocations into the tables on Q1–Q3 (12): a comment between a `>` and a `<` in the pinned cell, in the pinned row, and between rows of the last table; and a new row in the last table.
    - Two relocations onto another cell printing the same literal on Q1–Q3 (6).
  - No code changes, so R182 has no hunk. Its cases pass at `b6808dfcc16` and with the repair.

- **R183 (G2-B3, G2-B4, G2-B5, G2-m2, S-R7-1; amends R134 and R176). Refused, never raised.**
  - **A value too large for a float.** `10**400`, `-(10**400)` and `Fraction(10**400)` are refused as "numeric observation must be finite and non-boolean", on Q1–Q3 (9).
  - **An event identity that is not a string.** A workspace `event_id` of `7`, `null` or `["e"]` is refused as "workspace event identity is not a string", before replay, on Q1–Q3 (9).
  - **Sources that are not a list.** `null`, `5` and `true` are refused as "workspace sources must be a list" (3). A tuple is accepted: JSON cannot tell it from a list (R176).
  - **Nesting deeper than the interpreter reads.** A period, a unit, a rights profile or an absence's detail nested 100,000 deep is refused on both interpreters (4). The period is refused in `_fact_id`'s identity as "selected row is nested too deeply"; the other three are refused by the JSON comparison as "selected observation is not JSON data".
  - **A period that is not a scalar (S-R7-1).** A present row whose period is a list or a mapping, with its `fact_id` recomputed to follow it, is refused as "selected row period is not a scalar" (2).
  - **Hunk by hunk.** Each hunk, reverted alone, fails exactly its own witnesses:

    | hunk | R7 cases failed |
    |---|---|
    | event identity | 9 |
    | nesting in `_fact_id` | 1 |
    | finiteness | 9 |
    | the JSON comparison | 3 on 3.12; 0 on 3.14 |
    | scope key | 2 |
    | sources | 3 |

    - On 3.14 the JSON comparison already refuses the three deep values ("does not replay"), because its `json.dumps` does not raise at that depth. So that hunk's witnesses fail on 3.12 only, and R183's witness set is 27 on 3.12 and 24 on 3.14.
  - **Verified.** Every frozen case is unchanged. The six originals build and validate as before (the census).

- **R184 (G4-B1, G4-m1; amends R155 and R174). A token's edge, and R155's gap, are layout only where a reader lays them out.**
  - The layout characters are exactly space, tab, line feed, carriage return, form feed and no-break space.
  - `str.isspace` also calls `\x0b`, `\x1c`–`\x1f`, `\x85`, U+2028, U+3000 and others space. A reader does not lay them out.
  - Two checks read layout:
    - R174's edge check: the nearest printed character on each side of the span;
    - R155's gap check: the text between the span and the nearest markup on each side.
    - Both now read the layout set.
  - **The witnesses.**
    - Relocations glued by each of the six characters `\x0b`, `\x1c`–`\x1f` and `\x85` after a minus and markup (`<p>-<b></b>\x1c1.63</p>`) are refused (6).
    - The same after a letter and markup (2), and `\x0b` alone before the literal (1), are refused.
    - `_whole_printed_token` reads `<p>-X1.63</p>` as no whole token, for each of the six (6).
    - Each check alone refuses the relocation only it reads (12):
      - `<p>X 1.63</p>` puts the character in R155's gap, beside a space the edge check accepts;
      - `<p>-X<b></b>1.63</p>` puts it across markup, where R155's gap is empty.
  - **Also frozen.** The six relocations glued by a letter (`<p>xX1.63</p>`) are G4's b2 construction. As G4 observed, R155's gap check refused them at `b6808dfcc16` through the letter; they pin that outcome.
  - **The controls.**
    - Nine characters a reader lays out are token edges: space, tab, LF, CR, FF, the no-break space, `&#160;`, `&nbsp;` and `&#32;` (9).
    - Relocations set off by layout are accepted: `<p>-<b></b> 1.63</p>`, `<p>-<b></b>&#160;1.63</p>` and `<p>\xa01.63</p>` (3).
  - **Hunk by hunk.** With only the edge check reverted, 12 fail: the six grammar cases and the six across markup. With only the gap check reverted, 6 fail: the six in the gap. The nine glued witnesses fail only with both reverted, since each check refuses them.
  - **Verified on the originals.** Every receipt the extractor builds on the three F1-Q exhibits passes, and the frozen suites validate each one.

- **R185 (S-R7-2; amends R155, R166, R174 and R176). The span check reads a character reference as a reader prints it.**
  - **Five checks.** Each refuses the span as "not a raw literal", "not a whole literal" or "not a whole printed token":
    - **cut.** The span begins and ends where printed characters do. The units the span touches, decoded whole, must equal the three pieces before, in and after the span decoded apart. `&#91.63` decodes whole to `[.63`; the span `1.63` cut from it does not.
    - **edge.** A reference the engine drops is a printed character when the edge check reaches it across markup. `<p>&#1;<b></b>1.63</p>` is refused.
    - **gap.** A reference the engine drops in R155's gap is a printed character there. `<p>&#1; 1.63</p>` is refused.
    - **raw.** A reference the engine drops inside the span is a printed character inside the literal. `<p>1&#1;.63</p>`, spanning `1&#1;.63`, is refused.
    - **written.** Inside printed raw text, where a reader may print a reference as written, the literal is set off both as decoded and as written. `<xmp>&nbsp1.63</xmp>` prints `&nbsp1.63` as one token and is refused.
  - **The witnesses.**
    - The literal glued before or after each of six dropped references, `&#1;`, `&#127;`, `&#xFDD0;`, `&#xFFFE;`, `&#xFFFF;` and `&#x10FFFF;` (12). Both the edge and the gap check refuse each, so neither reverted alone fails them.
    - One isolating witness per check, per form (24): six cut forms (`&#9`, `&#x0a`, `&#10`, `&#32`, `&#13` and `&#160` without their semicolons, each absorbing the literal's `1`), and the edge, gap and raw forms for each of the six dropped references.
    - The written check (7):
      - `&nbsp1.63` inside `xmp`, `iframe`, `noembed` and `noframes`, whose content a reader prints as written (4);
      - the same inside `textarea`, `title` and `noscript` (3). There a reader decodes the reference, prints `\xa01.63`, and would set the literal off. The engine does not ask which raw-text element a reader decodes, so these three are refused too. They pin the rule, and they are coverage cost only.
  - **The controls.**
    - A reference a reader prints as the engine decodes it is accepted: `<p>&#32;1.63</p>`, `<p>&nbsp1.63</p>`, `<p>1&#46;63</p>` spanning `1&#46;63`, and `<p>&#49;.63</p>` spanning `&#49;.63` (4).
    - Inside each of the seven raw-text elements, `&nbsp 1.63` is set off both ways and accepted (7). So is `<xmp>&nbsp\r1.63</xmp>`, where a reader prints the carriage return as a line break (1).
  - **R166 amended.** Its fourth accepted relocation, `<p>&#1;1.63</p>`, is refused: a reader prints U+0001 at the literal's edge. The case leaves the R5 suite's accepted list, and the R7 suite pins it as `before_x01`. It was the only frozen case that R185 moves.
  - **G2's classification corrected.** G2 recorded 57 accepted `&#1;`-prefixed relocations outside the tables as inside R176's rule. The seat re-ran G2's family 4 with the repair. Its 4,124 runs raise nothing, and exactly those 57 move from accepted to refused. The 1,083 other acceptances outside the tables stand under R176.
  - **Why this is enough.** For each of the 66 forms of the seat's twin probe, the fifth check's decision matches the reading html5lib 1.1 gives, except the three pinned coverage costs. The forms are the literal set off or glued by a reference, as decoded and as written, in each raw-text element, in a paragraph and bare.
    - `script` and `style` content is accepted as R166's limit.
    - A comment-shaped form inside raw text (`<xmp><!--&nbsp-->1.63</xmp>`) is refused at admission as `markup_unreadable:element`. It never reaches the span check.
  - **Hunk by hunk.** Each of the five checks, reverted alone, fails exactly its own isolating witnesses: cut 6, edge 6, gap 6, raw 6 and written 7.
  - **Verified on the originals.** Every receipt the extractor builds on the three F1-Q exhibits passes the five checks. The originals' references are `&#160;`, `&#8212;`, `&#38;`, `&#8217;` and other printable ones, each set off or inside a literal a reader prints alike.

- **R186 (the round-7 freeze, the gate, the repair, the witness, the dispositions and the hold).**
  - **The freeze.** `tests/test_pg_envelope_f1_probes_r7.py` holds 272 cases, all authored by the seat. They come from the audit's findings, the seat's widened constructions, and its own findings S-R7-1 to S-R7-3.
    - At `b6808dfcc16`, the R7 suite gives 196 failed on Python 3.12 and 193 on 3.14, with only pytest and pyyaml installed. The two ten-digit R181 cases are not run there (R181).
    - The 196 are R179–R185's witnesses, each failing for its finding's reason. The three fewer on 3.14 are R183's three deep values, which 3.14 already refuses.
    - The R7 passes at `b6808dfcc16` are:
      - the controls and preconditions;
      - R179's title cases, R182's eighteen cases and R184's six letter-glued cases, which the base already refuses or accepts as ruled.
  - **The R5 amendment.** `test_r166_a_relocation_inside_the_restated_limit_is_accepted[code_point_unescape_drops]` leaves the R5 suite (R185).
    - With R185 reverted, the amended R5 suite passes all 60 of its cases on 3.12 and on 3.14. The amendment removes a case and adds none.
    - The eight envelope suites with the repair: 971 passed on 3.12 and on 3.14. They are the R7 suite's 272 and 699 earlier cases (46, 125, 70, 95, 140, 60 and 163 in the F1 suite and the R1–R6 probe suites).
  - **The gate.** The `earnings-economic-dossier` job in `.github/ci/legacy-jobs.yml` adds the suite to its paths and its run line. Its timeout moves from 12 to 15 minutes. At `b6808dfcc16` the hosted runner took 416 s for this job's line (run 36200249010, pack 9), 1.5 times the seat's 278 s for the same line. The repaired line takes the seat 414 s: 1,795 passed and 174 skipped against 1,524 and 174, the R7 suite's 272 cases less the R5 case R185 removes. At 1.5 times that is about 620 s on the runner, under 12 minutes by less than two and under 15 by nearly five.
  - **The repair.** The rulings fix the code to the line, so the seat writes it itself, one commit per ruling. R182 changes no code.
    - R179, R180 and R181 touch `engine/company_intelligence/pg_envelope.py`.
    - R181 also touches the release parser, `engine/fundamental_forensics/disclosure_diff.py`.
    - R183, R184 and R185 touch the validator, `engine/company_intelligence/economic_observations.py`.
    - Everything else must hold:
      - every other frozen file stays byte-identical;
      - the gate line and `curated_exclusive` pass;
      - the a5a and capital-structure suites match the baseline test by test.
  - **The witness.** Each ruling is load-bearing in the frozen suite. The seat reverted one ruling at a time in scratch copies, never in the worktree, and ran the R7 suite on 3.12 and 3.14. With nothing reverted, all 272 cases pass on both, inside the 971 above.

    | reverted | R7 cases failed on 3.12 | on 3.14 |
    |---|---|---|
    | R179 | 76 | 76 |
    | R180 | 21 | 21 |
    | R181, both hunks | 2 (its ten-digit cases not run) | 2 |
    | R183 | 27 | 24 |
    | R184 | 27 | 27 |
    | R185 | 43 | 43 |

    - The sets are disjoint. Together they are the 196 witnesses that fail at `b6808dfcc16` on 3.12, and the 193 on 3.14. No control fails in any run.
    - Hunk by hunk, over the R7 suite:

      | hunk reverted | R7 cases failed |
      |---|---|
      | R179 year grammar | 48 |
      | R179 title digits | 0; defence in depth (R179) |
      | R180 raw text; dropped reference; odd character | 9; 6; 6 |
      | R181 grid; release parser | 2 (its ten-digit cases not run); 1 |
      | R183 event identity; `_fact_id` nesting; finiteness; JSON; scope key; sources | 9; 1; 9; 3 on 3.12 and 0 on 3.14; 2; 3 |
      | R184 gap; edge | 6; 12 |
      | R185 cut; edge; gap; raw; written | 6; 6; 6; 6; 7 |

  - **Family 4 with the repair.** 4,124 runs over the 57 present rows of Q1–Q3, and 0 exceptions. The only change from `b6808dfcc16` is R185's 57. The fifth check alone changes none of the 4,124 outcomes.
  - **The census.** Admission, the workspace's sha256, the header years over every printed cell, and the cell texts R169 and R175 read, on the six originals: byte-identical to the census at `b6808dfcc16`, on 3.12 and on 3.14.
  - **G4-n1.** `_reads_under` recomputes four values per spanned column, and `_locate` scans every row for each cell. Both are harmless, and are left for a refactor that changes no behaviour.
  - **G4-O1.** The oracle's label side (`label_of`, `locate` in `tests/test_pg_envelope_f1.py`) reads a cell's first row only, while R168's label half is pinned by direct engine assertions.
    - No frozen case compares the oracle with the engine on a label-rowspan document, so the oracle does not move.
    - A frozen file moves only with a case that needs it, as R168's did. The comparison is on the R8 floor.
  - **The testimony note.** R177's table counted the round-6 G4 file's 14 cases that run on a copy, and named its other five, i1–i5, which read the audited worktree. The file holds 19. Nothing in R177 was wrong; this line restates it.
  - **G2-O1.** Seventeen workspace-level keys, and the fields of `sources` other than kind, receipt state and document identity, are not validated. The validator's contract is the selected `pg_` facts, and G2 records it only. It is unchanged, like R177's G3-O2.
  - **G3-O1–O3** are fail-closed and unchanged from round 6: the `Fiscal Year` banner, the year carried by a rowspan from the row above, and the carried `%` controls.
  - **The R8 audit.** An independent Opus READ_ONLY audit then attacks the repair. Its floor adds:
    - R179–R185, each attacked in both directions: what each admits that a reader reads another way, and what each refuses on a legitimate layout;
    - R185 against html5lib 1.1 and a browser, in each place a reference may sit:
      - in text and across markup;
      - in each raw-text element;
      - legacy named references without semicolons;
      - the RCDATA coverage cost;
    - R166's limit: a receipt wholly inside one comment passes the span check, including a comment inside an ordinary `<p>`;
    - R180's region: its end at the next table, and any other character the engine decodes there differently from a reader;
    - R179's grammar against every legitimate P&G header form, on both interpreters;
    - R183: any other exception a tampered workspace can raise, on both interpreters;
    - R181: any other exception crafted source bytes can raise on the public path, beyond the seat's sweep of integer conversions;
    - G2's unfinished families:
      - family 5, determinism across PYTHONHASHSEED, locale and a cold or warm cache;
      - the rest of family 10;
      - family 11 on 3.12;
      - family 4 past the gate for the eight R163 kinds;
    - G4-O1's oracle comparison, and G4's unfinished minus-one trees, as an independent re-run of this record's witness tables;
    - R178 against a later Unicode, which the seat's verification does not cover;
    - hosted CI observed concluded on the repair head.
  - **Hold.** #7905 stays Draft/HOLD under Sol's direction (comment 5825632041, R114).
