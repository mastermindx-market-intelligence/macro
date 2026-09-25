# Seat ruling — T1 envelope, audit round 5 (R163–R167)

Adjudicator: the CDV-1 Meta-CEO seat (session 251f88c8, running Opus 5.5 under the fable-mode doctrine).

Source: the independent Opus re-audit of the round-4 work at `a1220205b09` (PR #7905). The audit was READ_ONLY and its verdict was **REJECT**. The full report is committed beside this record as `OPUS_T1_ENVELOPE_AUDIT_R5_2026-09-25.md`.
- It ran 15 probe cases and re-ran the five frozen suites on both interpreters. The findings:
  - three blockers, B1–B3;
  - three minors, m1–m3;
  - gaps: a six-turn cap left families 2, 3, 5–11 and 13, and the family-14 mutation matrix, unexecuted.
- The seat re-ran the probe file at `a1220205b09`: 11 failed and 4 passed, each for the reason its finding names (7 × B1, B2, 3 × B3). The 4 passes are the OBSERVE cases.
- The audit confirmed the positive work:
  - P1–P4 and M1–M3 are closed on their constructions and on the seat's widened variants. B1 and B2 reopen the classes of M2 and M3 by other routes.
  - R154's start check fires only when the preceding decoded character shares the literal's first unit, and exactly R160's nine tokens are gone.
  - R162's defence-in-depth argument holds by code read.
  - The five frozen suites pass on 3.12 and 3.14: 46, 125, 70, 95 and 140. The gate line gives 1300 passed and 174 skipped on both, `curated_exclusive` passes, and the a5a and capital-structure suites match the `f8e4af5aa4c` baseline test by test (213 passed).

This record amends R116–R162 only where it says so. Everything else there stands.
- `tests/test_pg_envelope_f1.py`, the `_r1` to `_r4` suites and `tests/fixtures/pg_envelope/` stay byte-identical.
- The rulings below are enforced by the new frozen suite `tests/test_pg_envelope_f1_probes_r5.py` (R167).
- The seat grounded every factual premise below in its own runs on the six originals (the three F1-Q exhibits, the two F2-A exhibits and the Colgate release), in memory with the engine's reader. No finding is ruled on the audit's word alone.

## Severity

The bars are the commission's review standard: (a) wrong bind, (b) present fact outside F1-Q, (c) validator acceptance of a tampered workspace, (d) integrity, and (e) positional or literal admission.

| finding | audit | seat | ruling |
|---|---|---|---|
| B1, a comment a reader closes early (`<!-->`, `<!--->`, `--!>`) or never closes hides printed text from the engine | BLOCKER (a, b) | BLOCKER | R163 |
| B2, a `%` cell carried by rowspan beside a per-share value is not read | BLOCKER (a) | BLOCKER | R164 |
| B3, a relocation onto a literal glued to a text `<` or `>` is accepted | BLOCKER (c); repair by widening R155's limit | BLOCKER; repaired in code, and the limit is not widened | R163, R166 |
| m1, R155's premise that `html.unescape` reads references with R143's grammar | minor | minor; the premise is corrected | R166 |
| m2, `&#1;` decodes to nothing | minor, inside the limit | minor, inside the limit | R166 |
| m3, `_parse_year` reads only a header value's first year | minor, code read only | **BLOCKER** (e) | R165 |

- **B1 and B3 are one class, and the seat found more of it.** In each construction the engine, or the validator, reads markup by a grammar an HTML reader does not share. A value then binds where a reader sees no such literal, or sees another. At `a1220205b09` all 36 of the seat's constructions of the class are admitted and validate, and DIL binds 1.63 in 34 of them. Beyond the audit's comment and bracket forms they cover:
  - a `<` glued to the pinned value (`1.63<9.99`), which a reader prints as part of one token;
  - a `<` or `>` inside a quoted attribute value, where the engine's tag pattern ends the tag early. In the pinned cell, `<img alt="9.99>1.63<">` binds 1.63 out of an attribute;
  - script or template text inside a cell, which a reader does not print there, and elements such as `plaintext` or `tfoot` whose content a reader reads or places differently;
  - table structure a reader repairs: a row or cell end it implies, text it moves out of the table, a `<div>` between rows;
  - spans a reader reads another way (zero, signed, repeated or over the limit, or span text inside another attribute), and grids a reader builds with a hole or an overlap.
- **One admission rule closes the class.** The audit's comment-only check closes B1 and leaves the other forms open. Its B3 repair would widen R155's limit to a literal glued to a printed `<` or `>`. That accepts, by ruling, a value a reader prints as part of a longer token, and R114 forbids relaxing the validator. So R163 admits only markup the engine reads the way a reader does, and refuses every other document at admission.
- **m3 is a blocker.** It is P3's rule inside one header value. The seat probed what the audit only read. At `a1220205b09` a row naming `2026/2025` over the core reconciliation leaves CORE at 1.59, and `2025/2026` over the highlights leaves PCORE and PDIL at 1.54. A header naming two years does not name the pin's year alone, which is what R156 requires.
- **m1 and m2 stay minors.** In both, a reader sees the relocated literal delimited, by a no-break space or by an invisible control character. Both fall inside R155's limit, and R166 corrects the ruling text.

## Rulings

- **R163 (B1, B3; amends R143, R149, R155 and R158). The envelope admits only markup it reads the way an HTML reader does.**
  - `_admission` gains one check, after every earlier check. `_unreadable_markup` reads the whole source once, left to right, and names the first construct that a reader would read another way. The document is then refused with the admission code `markup_unreadable:<kind>`.
  - Every row is then absent under the existing reason `no_span_addressable_evidence`, with the detail `envelope_refused:markup_unreadable:<kind>`. No absence reason is added.
  - The grammar, by kind:
    - **`comment`.** A comment opens at `<!--` and closes at the next `-->`. A `<!--` with no later `-->` is refused. So is a comment whose interior starts with `>` or `->`, or holds `--!>`, because a reader closes it elsewhere.
    - **`gt` and `lt`.** Text holds no `>`. It holds no `<` either, unless that `<` opens markup: a `<` not followed by a letter, `/`, `!` or `?` is `lt`.
    - **`tag`.** Every other `<` opens a well-formed comment, start tag or end tag.
      - A start tag is a name, then attributes, each preceded by HTML whitespace (space, tab, LF, CR or FF), then an optional `/`. A value is double-quoted, single-quoted or unquoted, and holds no `<` or `>`.
      - An end tag is a name and optional HTML whitespace.
      - Anything else is refused: a CDATA section or any other `<!` or `<?` construct, an attribute value holding a bracket, an attribute on an end tag, a no-break space before an attribute.
    - **`element`.**
      - Elements a reader parses in a way the engine does not model are refused: `plaintext`, `template`, `svg`, `math`, `select`, `object`, `embed`, `frameset`, `frame`, `caption`, `colgroup`, `col`, `thead`, `tbody` and `tfoot`. The originals use none of them.
      - A raw-text element (`script`, `style`, `title`, `textarea`, `xmp`, `iframe`, `noembed`, `noframes`, `noscript`) is read only outside a table, up to its end tag, and only when its text holds no `<` or `>`.
    - **`table`.** Inside a table, markup follows `table`, then `tr`, then `td` or `th`, each with its own end tag.
      - Only whitespace and comments stand between rows or between cells.
      - No table, row or cell tag appears out of that order.
      - A cell closes with its own end tag, and every table closes before the source ends.
      - A row or cell tag outside a table is refused. End tags outside a table are ignored, as a reader ignores them.
    - **`span`.** A `colspan` or `rowspan` is one decimal from 1 to the reader's limit (1000 and 65534). It is given once, and the engine's `_SPAN_PATTERNS` read the same value. Span text in any other attribute's name or value is refused, because the engine's pattern may read it.
    - **`grid`.** In the grid a reader builds from the spans, no cell overlaps a cell carried from above. Every row's occupied columns run from the first column without a gap.
  - **What stays admitted,** because a reader reads it the same way. A frozen control pins each form:
    - a well-formed comment, with brackets inside it;
    - a comment between rows;
    - upper-case markup;
    - stray end tags outside tables;
    - whitespace between a row and a cell;
    - single-quoted and unquoted spans;
    - script outside tables.
  - **The originals.** All six pass the grammar, so no original's outcome changes. They use the same nineteen element names, none of them refused.
  - **The order.** The check runs last, so every earlier refusal keeps its code. Two frozen witnesses pin `quarter_mismatch` and `unknown_table:t7` on bodies that also hold unreadable markup.
  - **The validator.** It replays admission (R143), so it refuses a workspace built past the gate, and it needs no change.
    - The frozen replay witnesses build past the gate by replacing `_unreadable_markup` for the build only.
    - The frozen R166 and relocation cases go through R143's seam.
    - Replacing the gate is the third named exception to R131, after R143's seam and R160's census.
  - **B3 in these terms.** `9>1.63` is `gt`, `1.63< x` is `lt`, and the CDATA form is `tag`. Each document is refused at admission, and a workspace built past the gate onto each fails validation.
  - **Unchanged.** R158's comment blanking and R143's comment unit stay as they are. Every comment that reaches them is now one a reader closes where they close it.

- **R164 (B2; amends R159). The unit rule reads beside a value in every grid row the value occupies.**
  - For each pinned cell, R159's nearest non-empty cells on the left and on the right are taken in every row of the grid that holds the cell. That is its own row and any row its rowspan reaches. A cell carried into that row by rowspan counts, as it does for a reader.
  - When any of them is a whole unit cell that the pin's unit forbids, the metric is unlocated, as R159 says.
  - The witnesses:
    - a `%` carried beside DIL from the Basic row leaves DIL unlocated;
    - DIL spanning into a row where a `%` sits beside it leaves DIL unlocated.
  - The control: a `$` carried beside DIL binds every expected value.
  - Verified on every original: for every printed cell, the unit cells R164 reads beside it are the ones R159 read. Each P&G exhibit holds eight spanning cells.

- **R165 (m3; amends R147 and R156). A header value names every year it holds.**
  - The years over a cell are every `20\d{2}` not bounded by digits, in every value `_headers_over` yields. A header value naming two years adds both, not only the first.
  - R156's rules therefore read the whole value:
    - a pin that needs a year locates only when the set is exactly the period's year;
    - a year header locates only when the set is exactly its year.
  - `_parse_year` keeps its first-year reading for the pin's own header in `_locate`.
  - The witnesses:
    - `2026/2025` over the core reconciliation leaves CORE unlocated;
    - `2025/2026` over the highlights leaves PCORE and PDIL unlocated.
  - The control: `2025/2025` names one year and binds every expected value.
  - Verified on the five P&G exhibits: the header years over every printed cell are unchanged. The Colgate release changes (895 cells), but the envelope refuses it at admission, before any location reads a header.

- **R166 (m1, m2, B3; restates R155's limit).**
  - R155's check stays exactly as it is (R114).
  - **The limit, restated.**
    - The check proves that the span is a whole literal of the row's value, in the row's unit, delimited by markup or whitespace. It cannot prove that the literal is the pinned cell.
    - A seam shift onto another delimited literal of the same value and unit, in a document R163 admits, therefore still passes. That literal may sit:
      - in another cell;
      - in hidden text, which counts as printed (R151);
      - in script or style text outside tables;
      - inside a well-formed comment, where the comment's own text puts a `>` before it and a `<` after it;
      - after a bare legacy reference (m1), or after a code point that `html.unescape` drops (m2).
  - **Now outside the envelope, by R163:**
    - a literal glued to a text `<` or `>` (B3);
    - a literal inside an attribute value that holds `<` or `>` (the attribute form of R155's limit);
    - script text inside a table.
  - **The premise, corrected (m1).**
    - `html.unescape` does not read references with R143's grammar. It reads a bare legacy name by its longest known prefix, where R143's unit takes the whole greedy name class.
    - The two differ only on a bare legacy reference glued to name characters, such as `&nbsp1.63`.
    - R154 keeps the extractor's spans off such a unit, so the difference reaches only a seam shift. There the literal is delimited by the no-break space a reader sees.
  - **m2.** `&#1;` decodes to nothing under `html.unescape`, where a reader renders U+0001, an invisible control character. The literal stays delimited to a reader.
  - Four frozen cases pin the restated limit: `<script>1.63</script>`, `<!-- x>1.63<y -->`, `<p>&nbsp1.63</p>` and `<p>&#1;1.63</p>`. Each passes before and after the repair.

- **R167 (the round-5 freeze, the gate, the repair, the witness and the hold).**
  - **The freeze.** `tests/test_pg_envelope_f1_probes_r5.py` holds 61 cases, all authored by the seat from the audit's findings and the seat's widened constructions.
    - At `a1220205b09` it gives 45 failed and 16 passed on Python 3.12, with only pytest and pyyaml installed. Every failure is for its finding's reason:
      - the 36 comment and markup constructions are admitted and validate, and DIL binds 1.63 in 34 of them;
      - the two replay witnesses and the three relocations fail because that head has no gate to replace. The seat's per-construction runs show their substance there: the `<!-->` and grid-hole bodies validate, and the audit's B3 probes show the three relocations accepted;
      - the two R164 witnesses bind DIL at 1.63;
      - the two R165 witnesses bind CORE at 1.59, and PCORE and PDIL at 1.54.
    - The 16 passes are the two order witnesses, the eight markup controls, the R164 and R165 controls, and the four R166 cases.
  - **The gate.** The `earnings-economic-dossier` job in `.github/ci/legacy-jobs.yml` adds the suite to its paths and its run line. The suite adds about 30 seconds, within the 12-minute timeout.
  - **The repair.** The rulings fix the code to the line, so the seat writes the repair itself, one commit per ruling, as for R152–R160.
    - It touches only `engine/company_intelligence/pg_envelope.py`. The validator is unchanged, because it replays admission.
    - With the repair, all six envelope suites pass on 3.12 and 3.14 (537 cases).
    - Everything else must hold:
      - every frozen file stays byte-identical;
      - the gate line and `curated_exclusive` pass;
      - the a5a and capital-structure suites match the baseline test by test.
  - **The witness.** Each rule is load-bearing in the frozen suite. The seat removed one at a time, in memory and never on disk, and ran the R5 suite. With nothing removed, all 61 cases pass.

    | removed | R5 cases failed |
    |---|---|
    | the whole R163 check | 41 |
    | kind `comment` | 8 |
    | kind `gt` | 2 |
    | kind `lt` | 3 |
    | kind `tag` | 6 |
    | kind `element` | 6 |
    | kind `table` | 7 |
    | kind `span` | 6 |
    | kind `grid` | 3 |
    | the three early closers alone (`<!-->`, `<!--->`, `--!>`) | 7 |
    | the raw-text-inside-a-table refusal alone | 1 |
    | the span limits alone | 1 |
    | R164 (R159's own-row reading restored) | 2 |
    | R165 (the first year of each value only) | 2 |

    - Removing a kind means that the check stops refusing a document whose first unreadable construct is of that kind.
    - Removing the whole check also fails the replay witnesses and the relocations, because the validator's replay then admits the document.
  - **The earlier suites.** No case of the five earlier frozen suites reaches the new refusal, so R163 changes no earlier frozen outcome.
    - The seat recorded every refusal the check made while those 476 cases ran, and there were none.
    - The same recorder, run on the R5 suite, records 41.
  - **The R6 audit.** An independent Opus READ_ONLY audit then attacks the repair. Its floor adds the round-5 gaps:
    - the families round 5 did not execute: 2, 3, 5–11 and 13, and the family-14 mutation matrix;
    - R163's grammar itself, in both directions. Markup it admits that a reader reads another way is a finding. Markup it refuses that a reader reads the same way, on a legitimate layout, is a coverage cost. The audit uses an HTML5 tokenizer differential where one is installed;
    - comments and unreadable markup in every other pinned table, not only earnings;
    - R164 and R165 on every pinned cell of Q1–Q3;
    - hosted CI observed on the repair head.
  - **Hold.** #7905 stays Draft/HOLD under Sol's direction (comment 5825632041, R114).
