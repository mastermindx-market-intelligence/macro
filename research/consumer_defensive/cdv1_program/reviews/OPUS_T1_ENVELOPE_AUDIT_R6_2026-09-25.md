# Opus re-audit R6: CDV-1 T1 F1-Q envelope at 135a67a3e1244f87257f7866e96c2d0c12551620 (PR #7905)

MODE: READ_ONLY. The round ran as four independent Opus auditors, one per family group. All four worked on the same head, and each confirmed `git rev-parse HEAD` and an empty `git status --porcelain` before its first run and after its last.
- Each group's report follows verbatim, in group order.
- Probe files and raw outputs stayed in the seat's scratch directory. Nothing was written inside the worktree.

## STATUS: REJECT (all four groups)

| group | families | status | blocking | other findings |
|---|---|---|---|---|
| G1 | 0 (round-5 B1, B3), 3, 9, 15 | REJECT | G1-B1, G1-B2, G1-B3 | G1-M1 (major); G1-m1, G1-m2 |
| G2 | 4, 5, 10, 11 | REJECT | G2-B1, G2-B2 | G2-m1 |
| G3 | 6 (units), 8 (years), the Q1–Q3 sweep, 0 (round-5 B2, m1–m3), 1, 2 | REJECT | G3-B1, G3-B2, G3-B3 | O1–O3 (observations) |
| G4 | 12, 13, 14 | REJECT | G4-B1 | G4-m1, G4-m2; G4-n1 (nits) |

The seat's ruling on every finding is in `SEAT_RULING_T1_ENVELOPE_R6_2026-09-25.md`, beside this record.

---

## Group G1: families 0, 3, 9 and 15 (verbatim)

# G1: Opus round-6 audit, CDV-1 T1 F1-Q envelope at 135a67a3e1244f87257f7866e96c2d0c12551620 (PR #7905)

MODE: READ_ONLY. Families 0 (B1, B3), 3, 9 and 15.
- Probes: `test_envelope_audit_probes_r6_g1.py`. `test_g1_B*` are the blocking findings; all 16 fail at HEAD.
- Tools: `g1lib.py` (html5lib 1.1 grid reader and the differential), `fuzz.py`, `capture.py`, `agg.py`.
- Raw outputs: `fuzz_{0,1,2}.jsonl`, `capture.jsonl`, `probes_*.log`.
- HEAD was `135a67a3e12…` and `git status --porcelain` was empty, both before the first run and after the last.

## STATUS: REJECT
R163 still admits markup that html5lib 1.1 reads differently, and the difference reaches pinned cells. That gives three blocking findings (bar b).

B1 and B3 from round 5 are closed: their original constructions and every variant are refused.

## RESULT

### G1-B1: blocking (bar b; also bar a when judged on the reader's grid). R163 admits `</tbody>` inside a cell.
- **Code.** In the cell-state end-tag branch of `_unreadable_markup` (`engine/company_intelligence/pg_envelope.py:339-342`), an end tag other than the cell's own name that is not in `_TABLE_NAMES` (`:52`, which is `table`, `tr`, `td`, `th`) is silently ignored.
- **How a reader differs.** In "in cell" mode, HTML5 treats `</tbody>` as "close the cell, then reprocess". Because `<tr>` sits directly under `<table>`, the parser always inserts an implied `<tbody>`, so `</tbody>` is always in table scope.
  - The reader therefore closes the cell, the row and the tbody at that point.
  - The rest of the row is laid out as a new, label-less row starting at column 0.
- **Example (Q3).** `Diluted</tbody>` in the earnings label cell.
  - The reader's row 24 holds only `Diluted`. Its row 25 is `$ | 1.63 | … | $ | 1.54`, and the table grows from 36 to 37 rows.
  - The engine still binds DIL = 1.63 and PDIL = 1.54, and the validator accepts.
- **Probe.** `test_g1_B1_tbody_end_tag_in_a_cell_refuses_the_document`, 8 cases, all failing at HEAD:
  - Q3 DIL, `</tbody>` in the label cell;
  - Q3 DIL, `</tbody>` in the value cell;
  - Q3 DIL, `</TBODY >` in the label cell;
  - Q1 SALES, Q2 CORE, Q3 BEAUTY and Q1 ORG, each in the label cell;
  - Q2 PDIL, in the value cell.
- **Expected:** refused at admission, with no present fact. **Observed:** admitted as F1-Q, and every metric binds.
- **In the fuzz,** 25 of the 69 admitted documents with a pinned-reaching divergence carry `</tbody>` in some spelling.
- **Repair hint.** In the cell state, refuse `</tbody>`, `</thead>` and `</tfoot>`. Also refuse the end tags `</caption>`, `</col>`, `</colgroup>`, `</body>` and `</html>`: a reader ignores them, but refusing costs nothing.

### G1-B2: blocking under the bar as written (bar b, with R143's "printed literal"). A numeric reference that `html.unescape` drops but a reader prints may sit next to a bound literal.
- **Code.** `_units` decodes each reference with `html.unescape` (`pg_envelope.py:137`).
- **How a reader differs.** `html.unescape` returns `""` for the code points it treats as invalid: `&#1;`–`&#8;`, `&#11;`, `&#14;`–`&#31;`, `&#127;`, the C1 controls outside the windows-1252 table, `&#xFDD0;`–`&#xFDEF;` and `&#x…FFFE;`/`&#x…FFFF;`.
  - HTML5 (html5lib 1.1) keeps each of those code points, reporting a parse error.
  - R163 checks no character reference.
- **Effect.** A reference glued to the pinned literal contributes no extent, so R154's shared-unit test never fires. The metric binds with the bare literal as its span. The reader's cell token is, for example, `￿1.63`, `1.63\x7f` or `\x011.88`.
- **Probe.** `test_g1_B2_a_reference_the_engine_drops_beside_the_literal_is_not_bound`, 5 cases, all failing at HEAD: Q3 DIL with `&#xFFFF;` before, Q3 DIL with `&#127;` after, Q2 CORE with `&#1;` before, Q1 BEAUTY with `&#xFDD0;` before, and Q3 SALES with `&#x8;` after.
  - **Expected:** the metric is not present. **Observed:** present, with a span equal to the bare literal.
- **In family 3,** 171 of 4849 cases fail, and every one is this class: `ctrl_before` (`&#1;`), `ctrl_after` (`&#1;`) and `del_ref_after` (`&#127;`), on every present pin of Q1–Q3.
- **In the fuzz,** this is the largest non-tbody group of pinned divergences: `&#1;` 14 docs, `&#xFFFF;` 11, `&#127;` 8.
- **Relation to m2 (owned by G3).** R166 records m2 only as a limit on seam shifts in the validator. This is the extractor binding such a cell directly, so R166 does not cover it.
  - The digits a user sees do equal the bound value, so the seat may rule the invisible-control subset in or out.
  - U+FFFF and U+FDD0 are noncharacters, which a renderer typically draws as a replacement glyph.
- **Repair hint.** Either refuse a numeric reference whose code point `html.unescape` drops (a `markup_unreadable:reference` kind), or treat such a reference as a unit that shares an extent with the adjacent literal.

### G1-B3: blocking under the bar as written, reader-defined (bar b). R163 admits `<isindex>`, which html5lib 1.1 expands into printed text.
- **How the reader differs.** html5lib 1.1 applies the pre-2016 `isindex` rewrite: it inserts `form`, `hr`, a label reading "This is a searchable index. Enter search keywords:", and an `input`.
  - With that inside a pinned or title cell, the reader's cell text changes, while the engine binds the value unchanged.
- **Probe.** `test_g1_B3_isindex_in_a_pinned_cell_refuses_the_document`, 3 cases (Q3 DIL, Q1 SALES, Q2 CORE), all failing at HEAD.
  - **Expected:** refused, or not present. **Observed:** admitted and bound.
- **Caveat.** Current WHATWG HTML dropped this rewrite, and browsers treat `isindex` as an unknown element. The finding is blocking only because the commission designates html5lib 1.1 as the reader.
- **Fix:** add `isindex` to `_UNREAD_ELEMENTS` (`:47`).

### G1-M1: major, not blocking under the bar's reach list (no cell, header or title). The prior-year note is read from text a reader never prints.
- **Code.** `_prior_note_present` (`pg_envelope.py:1078-1088`) applies `_text` to the raw bytes between the core reconciliation and the next table. `_text` keeps the contents of `script`, `style` and `title`, which R163 admits outside tables when they hold no `<` or `>`.
- **Effect.** The no-adjustment note gates PCORE's second statement.
  - On Q3, with the note moved into `<script>…</script>`, `<style>…</style>` or `<title>…</title>`, a reader shows no note, yet PCORE binds 1.54 (F1-Q).
  - With the note removed, the frozen `note_removed` mutation expects PCORE `unlocated`.
- **A second difference.** RAWTEXT elements (script, style, xmp, iframe, noembed, noframes) do not decode references for a reader, but `_text` does.
- **Probe.** `test_observe_prior_note_inside_raw_text_still_gates_pcore` (OBSERVE, prints `PCORE <script>{}</script> 1.54 F1-Q`).
- **Seat to rule.** Either refuse raw-text elements between the core reconciliation and the next table, or read the note only from printed text.

### Minor / coverage
- **G1-m1.** A literal NUL in cell text: the reader drops it and the engine keeps it. This fails closed: the literal breaks or the label leaves the vocabulary, so the table is unknown. It appears in 3 pinned-reaching fuzz documents, each a header-column cell whose outcome is unchanged.
- **G1-m2.** `&#11;` (VT) belongs to the B2 class: the engine drops it and the reader keeps U+000B, which is not HTML whitespace. Family 3's `vt_ref_before` passes only because my token normalisation uses Python's `split()`. Count it with G1-B2.
- **Coverage (non-blocking).** In 1875 single-construct fuzz documents, R163 refused the markup although the reader's pinned cells equal the original's. Frequent constructs:
  - a `<!--` inside a quoted attribute;
  - `<?xml ?>` and `<?x?>`;
  - `<frameset>` and `<select>`;
  - a second span attribute (`COLSPAN="1"` added to a cell that already has one);
  - `rowspan=1/`, `data-colspan` and `title="colspan=3"`;
  - `</p\xa0>` and `<p/ >`;
  - `colspan="&#49;"` and `colspan="1000"`;
  - `<!--->`, which is correctly refused as B1.

  Estimate for SEC EX-99 exhibits: Workiva P&G exhibits carry none of these, since the six originals pass. Across generators, `<?xml …?>`, DOCTYPE, `tbody`/`thead` and `&nbsp;` between cells are common, perhaps 20–40% of non-Workiva exhibits. That cost is irrelevant to the P&G-only F1-Q envelope.

### Closed from round 5 (family 0)
- **B1.** The originals all refuse with `markup_unreadable:comment`: the 3 openers in the DIL cell, the 3 second-row cases and the unclosed comment after the earnings table.
  - 5 variants in other quarters, tables and spellings refuse with `comment`: Q1 SALES `<!-->`, Q2 CORE `<!--->`, Q1 BEAUTY `<!-- a --!>`, Q2 PRICE `<!----!>` and Q3 COREG `<!-- x -- --!>`.
  - Unclosed `<!--` variants:
    - before the first table (Q1): refused `comment`;
    - inside a Q2 title cell and after a Q3 BEAUTY cell: refused earlier, as `unknown_table:t4` and `t11`, because R163 runs last.
  - None of these yields a present fact, and every one validates.
- **B3.** 10 of 10 pass: the original `gt`, `lt` and CDATA forms on Q3 DIL, plus variants.
  - The variants: `1.63>9`, `<<1.63`, `<?x 1.63?>`, Q2 CORE `9>`, Q1 SALES `< x`, Q2 SALES `</ 1.63>` and Q1 DIL `x>`.
  - Each body is refused at admission with the expected kind. Built past the gate and relocated through R143's seam, the validator refuses each.

### Family 9 (G1 part)
- **Structural tags inside comments:** 900 cases. The forms are well-formed, `<!-->`, `<!--->`, `--!>` and unterminated. The tags are `<table>`, `</table>`, `<tr>`, `</tr>`, `<td>` and `</td>`, placed between rows and inside the primary pinned cell, in the 5 primary-pin tables of each of Q1–Q3.
  - Every well-formed case binds the original values and shows no pinned reader divergence.
  - Every other form is refused: `markup_unreadable:comment`, or, for `<table>`/`</table>` inside `--!>` and unterminated comments (114 cases), the earlier `unknown_table:*`, because R158's blanking does not blank those comments, so the nested-table check fires first.
  - No case yields a present fact, and every workspace validates. The 114 failures in `probes_main.log` are my test's exact-detail expectation, not a finding.
- **Unclosed tables:** 90 cases, all pass. The constructions are an unclosed pinned table, a nested table (closed or unclosed) inside a pinned cell, a stray `</table>` inside a cell, one between rows, and one after the table.
  - A stray `</table>` after the table is admitted, binds the original values and shows no pinned reader divergence.
  - Every other construction yields no present fact.
- **Not run:** the F2-A fiscal-year transplant (see GAPS).

## EVIDENCE
- **Family 15 differential** (html5lib 1.1, `treebuilder="etree"`, HTML table model with colspan/rowspan clamps and row-group truncation; text from `itertext()`, NBSP folded, whitespace collapsed):
  - **(i) + (ii) Capture.** Wrapping `build_event_workspace` in-process while the six frozen suites ran gave 537 passed in 236.62s and captured 336 unique sources, which include all six originals.
    - 0 exceptions; 237 admitted F1-Q; 293 grammar-admitted.
    - **0 divergences** on any grammar-admitted document; the Q3 original alone also shows 0.
    - Refusals by code: `unknown_table` 35, `not_ex_99_1` 11, `issuer_not_pg` 6, `generator_not_workiva` 4, `quarter_mismatch` 3, `required_table_missing` 2 and `required_table_repeated` 2.
    - `markup_unreadable` refusals by kind: `comment` 7, `table` 7, `element` 6, `span` 6, `tag` 5, `grid` 2, `lt` 2 and `gt` 1.
  - **(iii) Fuzz.** Seed 20260925, 9000 documents in 3 shards, built from the three F1-Q originals with 1–3 inserts each.
    - Insertion sites, weighted: pinned cell interior 25, a pinned cell's start tag (attributes only) 10, between cells 15, between rows 15, title/header cells 10, label 5, anywhere in a table 10, anywhere 10.
    - The construct list is in `fuzz.py` (`CONSTRUCTS` has 166 items, `ATTRS` 26). It covers every R163 kind, every seat pointer and the HTML5 cell and body specials.
    - 0 exceptions; 1489 admitted F1-Q; 1562 grammar-admitted.
    - **Divergences in admitted documents:** `text` 151, `grid` 39, `row_count` 20. 69 documents reach a pinned cell, a header or a title:
      - `</tbody>` in some spelling: 25;
      - dropped references: `&#1;` 14, `&#xFFFF;` 11, `&#127;` 8 (with overlaps);
      - `<isindex>`: 8;
      - NUL: 3.

      Divergences that reach no pinned cell: NUL 7, and one each for `&#13;`, `</colgroup>`, `&nbsp1` and `<nobr>`, all in combination with others.
    - Refusals by code: `unknown_table` 3209; `markup_unreadable:table` 1726, `tag` 956, `element` 802, `span` 464, `comment` 168, `lt` 109, `gt` 62 and `grid` 8; `quarter_mismatch` 6; `generator_not_workiva` 1.
  - **Command:** `PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:$G:tests /opt/homebrew/bin/python3 $G/fuzz.py 20260925 {0,1,2} 3 9000 …`, then `agg.py`.
- **Probe runs,** each `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests:$G /opt/homebrew/bin/python3 -m pytest -p no:cacheprovider -q -rf --tb=line $G/test_envelope_audit_probes_r6_g1.py`:
  - `-k "not test_f3"` (families 0, 9, B1): `124 failed, 899 passed, 4849 deselected in 382.17s`. The failures are the 8 G1-B1 cases, 114 family-9 cases (exact-detail expectation only), and 2 B1 unclosed variants refused by an earlier code.
  - `-k "test_f3 and Q1"`: `57 failed, 1558 passed in 833.27s`, all `ctrl_*` and `del_ref_after`.
  - `-k "test_f3 and (Q2 or Q3)"`: `114 failed, 3120 passed in 1669.66s`, all `ctrl_*` and `del_ref_after`.
  - `-k "B2 or B3 or observe or g1_B1"`: `16 failed, 13 passed`. All 16 `test_g1_B*` fail at HEAD; the 13 passes are the 3 OBSERVE cases plus 10 earlier-appended cases.
- **Probes run and failed, per family:**

  | Family | Run | Failed | Findings |
  |---|---|---|---|
  | 0-B1 | 15 | 2 | 0; refused by an earlier code |
  | 0-B3 | 10 | 0 | 0 |
  | 3 | 4849 | 171 | G1-B2 |
  | 9 | 990 | 114 | 0; refused by an earlier code |
  | 15 | 336 + 9000 documents | — | G1-B1, G1-B2, G1-B3; G1-M1 by code read and OBSERVE probe |
  | Blocking probes | 16 | 16 | as intended |

## GAPS
- **F2-A fiscal-year transplant (family 9) was not run.** I did not locate its frozen helper within budget. Family 9's structural sweep covered only the 5 primary-pin tables per quarter.
  - The second-statement tables (drivers, change_versus_year_ago, prior_core_reconciliation) were reached only by the fuzz's pinned-cell and between-cell sites, which do include second cells.
- **The reader is html5lib 1.1 alone.** G1-B3 depends on it. G1-B1 and G1-B2 are standard WHATWG behaviour.
- **Family 3's reader token check** uses Python `split()`. U+000B, U+001C–U+001F, U+0085 and U+3000 count as whitespace there, not as HTML whitespace, so part of the B2 class (`&#11;`) is under-counted.
- **Refused documents** were compared with the original only at pinned (table, row, col0) anchors, so an inserted row shifts the anchors. The 1875 figure is therefore a lower bound on the coverage cost.
- **Other families.** Relocations, the validator's independence, determinism across processes and both caches, and the capital-structure suites belong to G2–G4 and were not run here.

## DEVIATIONS
- While the four background Python processes ran, I briefly ran `cat` and `grep` in the foreground, momentarily exceeding four processes.
- I edited my own probe file once with `sed -i` (the OBSERVE case).
- The capture step wrote per-source summaries to `capture.jsonl`, not the sources themselves. The sources stayed in memory.
- The background runs set `PYTHONHASHSEED=0`.
- I did not use `gh` or the network, and wrote nothing inside the worktree.

---

## Group G2: families 4, 5, 10 and 11 (verbatim)

# Opus T1 envelope audit — round 6, group G2 (families 4, 5, 10, 11)

Head: `135a67a3e1244f87257f7866e96c2d0c12551620`. `git rev-parse HEAD` = head and `git status --porcelain` empty,
checked before the first run and after every batch. Interpreter `$MY/venv_t1/bin/python` (3.14.7),
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.`, run from `$WT`. At most four processes at a time. Everything here lives in this
directory: `g2common.py`, `fam4.py`, `fam4g.py`, `fam4g2.py`, `fam5_docs.py`, `fam5.sh`, `fam10.py`, `fam10b.py`, and
`fam11.py`, with their outputs `*.jsonl`, `*.log` and `*.out`. The first pass (turn-capped) is kept as `*.first_pass.md.bak`.

STATUS (G2 families): **REJECT**, on G2-B1 (bar c, by the commission's letter) and G2-B2 (bar d, R134).

## Static read
- **Independence (family 4).** `_validate_envelope_span` (`economic_observations.py:220-263`) reads the source bytes,
  the row, `html.unescape` and `pg_envelope._literal` (`pg_envelope.py:980-991`, the literal grammar only). It calls no
  tokenizer, cell reader, receipt code, `_document`, `admit`, `extract` or replay, so independence holds.
- **Replay (family 10).** The replay (`economic_observations.py:266-346`) calls the same `admit` (R163 runs last,
  `pg_envelope.py:769-770`), `_document` and `extract` as the build path (`pg_profile.py:2172-2175`). It then compares
  rows by `json.loads(json.dumps(row)) == replayed` (`:340-342`). The json round-trip is outside every `try`.

## Family 4: seam shifts, relocations, and the gate
Files: `fam4full_Q{1,2,3}.jsonl`, `fam4g.jsonl`, `fam4g2.out`.
- **Coverage.** All 57 present rows of Q1–Q3, 19 per quarter.
- **One-byte shifts, widenings and narrowings.** 429 run, **0 accepted**.
- **Relocations.** 38 targets on every row (2,166 runs), plus 159 other-cell relocations onto cells that print the same
  literal. No exceptions.
  - **Accepted and inside R166's list, so not findings (614):**
    - another cell: 158/159;
    - a well-formed comment with `>` before and `<` after the literal: 57/57;
    - script or style outside tables: 171/171;
    - hidden text (`display:none`, `hidden`): 114/114;
    - after a bare legacy reference (`&nbsp1.63`): 57/57;
    - after a dropped code point (`&#1;`): 57/57.
  - **Refused, 0 accepted:** every early-closing, bang or unterminated comment; a comment without brackets or between
    rows; every attribute-value form (double-quoted, single-quoted, unquoted, bracketed); script or style inside a table;
    CDATA, with and without brackets; a literal glued to a text `>` or `<`; `<?…?>`; `<!x …>`.
  - **Accepted and OUTSIDE R166's list: 684, all 12 targets on all 57 rows. This is G2-B1.**
- **A workspace built past the gate, for every R163 kind (`fam4g`).** 36 constructions cover all eight kinds: the 29
  UNREADABLE cases, the 3 early closers in the pinned cell and around a second row, and the unclosed comment. Each was
  built with `_unreadable_markup` replaced for the build only.
  - Each binds 16 to 19 present rows, and the validator refuses every one: "selected observation does not replay from
    source bytes".
- **The same, with DIL also relocated through the seam onto `<p>1.63</p>` (`fam4g2`).** 33 constructions, all eight
  kinds. The relocation binds in 31. **The validator accepts 0.**

### G2-B1 (BLOCKING, bar c by the commission's letter): the independent check accepts relocations R166 does not list
- **The check.** `_validate_envelope_span` (`economic_observations.py:238-248`) proves only that the span is bounded by
  the nearest `>` and `<` with whitespace between. It has no notion of where the literal sits.
- **What passes (684/684).** A seam shift of any present row's receipt onto the same literal in each of these places:
  - the EDGAR wrapper `<DESCRIPTION>` value, before `<TEXT>`. This is SEC header metadata, not exhibit content;
  - visible prose outside every table: `<p>1.63</p>`, bare `\n1.63\n`, `<div> 1.63 </div>`;
  - text after `</html>`;
  - `<title>`, `<textarea>`, `<xmp>`, `<iframe>`, `<noembed>`, `<noframes>` or `<noscript>` outside tables. R163
    admits all seven raw-text elements, but R166 names only script and style.
- **The documents.** Every such document is admitted F1-Q, because the fragment is readable markup.
- **Observed:** accepted. **Expected:** refused, or named in R166's limit.
- **Probe:** `test_g2_b1_relocation_outside_r166_list_is_refused[*]`, 11 cases on Q3 DIL. All 11 fail at the head.
- **Impact.**
  - Seam-only. Under the real extractor, the replay's deep equality pins the exact span. Across 8,172 fuzz documents
    (family 11), no extractor span left its cell.
  - It is still a bar (c) acceptance outside the recorded limit. The wrapper-header case shows that the check does not
    even confine the span to `<TEXT>`.
- **Remedy (the seat's choice).** Either refuse spans outside `<TEXT>`…`</TEXT>` in code and extend R166's list by
  ruling to prose, RCDATA and the other raw-text elements, or restate the limit generically.

## Family 10: replay completeness
Files: `fam10full_*.jsonl`, `fam10b.out`, `r150.out`.
- **Admitted F1-Q workspaces (Q1, Q2 and Q3 originals).** 19 present rows and 1 excluded row each (20 `pg_` rows).
  - Every key, including every nested key of `source_span`, `receipt`, `locator` and `typed_absence`, was tampered:
    value mutation, key deletion, key addition at every dict, type-equal substitution, and (Q3) exotic values.
  - **No true tamper was accepted.** The only acceptances fall into two groups:
    - (i) type-equal substitutions, which Python's `==` erases after JSON normalisation: `value` 5.0→5, and int→float on
      `document_version`, `locator.segment_index/span_start_byte/span_end_byte` and
      `receipt.segment_bytes/segment_index`. This is G2-m1;
    - (ii) no-ops: `list_to_tuple`, which R136 rules equal, and `None`→`None` on `source_span.unreplayable_reason`.
- **Refused-document rows (`fam10b`).** One document per `markup_unreadable:<kind>` for seven kinds (element, grid, gt,
  lt, span, table, tag), with every key of every row tampered: **16,240 tampers, 0 accepted.** The comment kind is in the
  fam10 run (see the addendum).
- **Exempt set observed.**
  - **Row level: none.** A lone `event_id` or `document_id` edit anywhere is refused.
  - **Workspace level (R150).**
    - A consistent rename of `event_id`, with `fact_id` recomputed, is **accepted** on a present and on a refused workspace.
    - A consistent rename of `document_id` across the sources, spans, absences and the `source_texts` key is **accepted
      on the refused workspace** and **refused on the admitted Q3 workspace**. There the present rows' spans do not
      replay under the new identity.
    - So `document_id` is exempt only for absence rows. This is stricter than R150 states. Not a defect; recorded.
- **Exceptions: G2-B2.**

### G2-B2 (BLOCKING, bar d / R134): tampered rows make the validator raise `TypeError`
Four paths each let a tampered workspace raise `TypeError` out of `validate_selected_facts`, where
`EconomicObservationError` is expected:
- `typed_absence.missing_fields` holding a non-iterable (`5`). `tuple(...)` at `economic_observations.py:170-172` sits
  inside `try/except ValueError`. This path is inherited: `e1dd9caa3fa` has the same line, at :259.
- `typed_absence.reason` holding a dict or list. `documents.py:511` (`self.reason not in ABSENCE_REASONS`) raises
  `TypeError`, which the `except ValueError` at `:175` does not catch.
- Any field of a present or absent `pg_` row holding a non-JSON value (`Decimal`, `set` or `bytes`): `unit`, `basis`,
  every `source_span` key, `typed_absence.detail`, `event_id` or `document_id`. `json.dumps` at
  `economic_observations.py:340` raises `TypeError`. This path is new with the envelope (R136).

Observed counts:
- fam10: 29 per path per exotic type on Q3, on every `source_span` key;
- fam10b: 20 per path per kind, on every refused kind.

- **Expected:** `EconomicObservationError`.
- **Probe:** `test_g2_b2_a_tampered_row_is_refused_not_raised[*]`, 4 cases. All 4 fail at the head with `TypeError`.
- **Scope note.** R134's own text lists `ReceiptError`/`ValueError`/`IndexError`/`KeyError` escaping
  `build_event_workspace`. The commission's bar (d) covers "an exception escapes … the validator". The json path is
  envelope-introduced.

### G2-m1 (minor, bar c by the letter): JSON-normalised `==` erases the int/float distinction
- **Where.** `economic_observations.py:340-342`. `_validate_envelope_span` type-checks only the receipt's start and end
  (`:228-236`).
- **Observed:** 454 acceptances, all of them numerically identical. The serialised workspace differs (`5` against `5.0`).
- **Probe:** `test_g2_m1_*`, 3 cases. All 3 fail at the head.
- **For the seat:** decide whether "any field" reaches the JSON type.

## Family 5: determinism
Files: `fam5_*.json`, `fam5.out`, `fam5_interleave.json`.
- **Documents: 51.**
  - Q1–Q3 originals and all 29 R163 UNREADABLE constructions (refused).
  - The 7 KEPT controls (admitted).
  - R164 (`%` carried, `$` carried, spanning value) and R165 (two-year header in highlights and in the core
    reconciliation).
  - R158 (a table held in a comment between rows), an R156 header-year edit, and two mutations.
  - 3 builds past the gate (gt, table, grid).
- **Separate processes: 12.** `PYTHONHASHSEED` 0, 1, 42 and 4294967295, crossed with `LC_ALL` C, de_DE.UTF-8 and
  tr_TR.UTF-8, with `locale.setlocale(LC_ALL, "")`. Each run records the admission code, the pg-row digest, the outcome
  digest and the validator verdict per document. **All 12 outputs are byte-identical** (sha d53fc7062e44).
- **In one process.** 4 interleaved passes over the 51 sources (more than 8, so both caches evict):
  - reversed order;
  - shuffled with seed 20260925;
  - equal strings as fresh objects;
  - random `cache_clear()` of `_unreadable_markup`, `_structure` and `_cached_document`.

  **0 mismatches** against the cold first pass.

## Family 11: no-exception fuzz and differential
Files: `fam11v3_Q{1,2,3}.jsonl`, one record per document.
- **Corpus: 8,172 edited documents.** 314 distinct cells (every pinned primary and second cell, plus every header and
  title cell over them, in Q1–Q3) × 62 edits. The edits cover:
  - long digit runs and references (first or last character as decimal or hex, `&amp;`, bare `&nbsp`, `&#1;`, `&#0;`,
    huge, surrogate and over-long);
  - comments in five forms, and one construct per R163 kind, plus span attributes (0, rowspan 2, 1000, duplicated);
  - whitespace kinds, signs, dashes and non-ASCII digits;
  - year, label and title edits (two-year forms, `20٢٦`, `2026(a)`, `FY25/26`, six- and twelve-month labels,
    February 30).
- **Admission.**
  - F1-Q: 4,926.
  - `unknown_table`: 1,642.
  - `markup_unreadable`: comment 656, span 330, gt 132, and tag, lt, element and table 114 each, grid 9.
  - `quarter_mismatch`: 21.
- **Exceptions:** 0 escaping `build_event_workspace`, and 0 escaping the validator.
- **The validator's rejections of the extractor's own output: 0 of 8,172.**
- **`html.unescape(source[span])` against the engine's cell literal.** Each present row's span is matched to the pinned
  cell the extractor's `_receipt` read (recorded by wrapping `_receipt` in-process). **0 divergences over 90,395 present
  rows.**
- **An earlier pass is superseded.** The v1/v2 files came from budget-limited or broken-mapping runs, and v3 replaces them.

## Probes run and failed, per family
- **Family 4.**
  - Shifts: 429 run, 0 accepted.
  - Relocations: 2,325 run, 684 accepted outside R166.
  - Past the gate: 36 run, 0 accepted.
  - Past the gate with relocation: 33 run, 0 accepted.
  - Probe file: 11 run, **11 fail** (G2-B1).
- **Family 5.** 12 process runs and 4 interleaved passes: 0 differences.
- **Family 10.**
  - Admitted: about 2,850 logged tampers. The acceptances are type-equal or no-op only; 0 real tampers accepted.
  - Refused: 16,240 tampers, 0 accepted.
  - Probe file: 3 G2-m1 and 4 G2-B2 cases. **All 7 fail.**
- **Family 11.** 8,172 documents: 0 exceptions, 0 self-rejections, 0 divergences.
- **Probe file total:** `18 failed in 6.94s` at the head.

## Addendum: the complete family-10 run (`fam10full.summary`)
- **Coverage: all five row kinds.**
  - present and excluded: Q1, Q2 and Q3;
  - conflict: `mut:period_single`;
  - unlocated: `mut:note_removed`;
  - refused, with detail `markup_unreadable:comment`: `refused:comment`.

  The other seven refusal kinds are in fam10b.
- **Tampers: 26,655.**
  - **Accepted: 709. Every one is type-equal or a no-op.**
    - `list_to_tuple` on `missing_fields`: 28;
    - int↔float on `value`, `document_version`, `locator.segment_index/span_start_byte/span_end_byte` and
      `receipt.segment_bytes/segment_index`: 627 (G2-m1);
    - `None`→`None` on `unreplayable_reason`: 54.
  - No real tamper on any key of any row kind was accepted.
- **Exceptions: 4,738, all `TypeError`, on every row kind (G2-B2).**
- **Workspace-level renames.** The fam10 string-replace renames do not recompute `fact_id`, so their `event_id` result is
  superseded by `r150.out`.
  - A consistent `event_id` rename is accepted.
  - A consistent `document_id` rename is accepted only on a refused workspace.

Final check after the last run: `git rev-parse HEAD` = `135a67a3e12…` and `git status --porcelain` is empty.

---

## Group G3: units, years and the Q1–Q3 sweep (verbatim)

# Opus R6 audit, group G3 (units, years, Q1/Q2/Q3 sweep): CDV-1 T1 envelope at 135a67a3e1244f87257f7866e96c2d0c12551620 (PR #7905)

## STATUS: REJECT (three blocking findings; B2, m1, m2 and m3 closed as far as their own constructions go)

Head confirmed `135a67a3e1244f87257f7866e96c2d0c12551620`, `git status --porcelain` empty, before the first run (and after the last; see EVIDENCE).
All runs: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.`, pytest `-p no:cacheprovider`, at most four processes. Nothing written inside the worktree.

## Findings

### G3-B1: blocking (bar e, with a): a year-bound cell that spans two year columns binds the year of its first column
- **Code.** `_headers_over` (`engine/company_intelligence/pg_envelope.py:792-806`) keeps only header cells with `other.col0 <= cell.col0 < other.col1` (lines 803 and 806), i.e. the headers over the cell's **first column only**. `_header_years` (`:891-892`, R165) and the `_locate` year check (`:938-940`) and `_period_matches` (`:875-888`) all read that list. A header over any other column the cell occupies is never read.
- **Construction** (`g3lib.fam8` sub `span2`; probe `test_BLOCK_g3_b1_value_spanning_two_year_headers_is_unlocated`). Widen a pinned year cell's `colspan` so that it also covers the next year's column, and remove the cells it now covers (the grid stays whole, so R163 admits it).
  - Q3 highlights `Diluted EPS`: `1.63` over `2026` and `2025` -> DIL **present 1.63**, validator accepts.
  - Q3 highlights `Core EPS`: `1.59` over `2026` and `2025` -> CORE **present 1.59**.
  - Earnings `Diluted` (primary): `1.63` widened over the `2026` and `2025` columns -> DIL present (Q3 1.63; Q1 1.95 over 2025/2024; Q2 1.78).
  - Reproduced on all three quarters: 9 of 9 constructions bind (span2 rows in `f82_Q*.jsonl`).
- **Expected.** Unlocated. The value is printed under two year headers, which is R147's "two or more years over the cell" and bar (e)'s "year bound from contradictory headers". A reader lays the cell under both headers.
- **Smallest repair.** Read headers over every column `cell.col0 .. cell.col1-1` (overlap, not first-column containment) in `_headers_over`, or refuse a year-bound cell whose span crosses a header boundary.

### G3-B2: blocking (bar a, R159/R164): a forbidden unit cell carrying an invisible format character is not read
- **Code.** `_neighbours_admit` (`pg_envelope.py:1065-1075`) treats a neighbour as a unit cell only when `text in _UNIT_CELLS` (`:1074`, `_UNIT_CELLS = {"$", "%"}` at `:27`), and it counts any non-empty `text` as printed (`:1069`). `_text` (`:142-143`) collapses only `str.split()` whitespace, so the format characters U+200B, U+FEFF and U+00AD (all category Cf, not rendered) survive.
- **Constructions** (`g3lib.fam6` kinds `own_*_invis` and `shield_*:zwsp`; probes `test_BLOCK_g3_b2_*`):
  - the nearest cell prints `$` to a reader, with a ZWSP, BOM or soft hyphen before or after it (`$&#8203;`, `&#8203;$`, `$&#65279;`, `$&#173;`): the percent or pp value beside it binds. The same with `%&#8203;` etc. beside a per-share value in the highlights (DIL, CORE, PCORE second/primary cells).
  - a cell that holds only `&#8203;` sits between the value and a `$`/`%` cell: the ZWSP cell is taken as the nearest printed cell, and the value binds.
  - Across Q1-Q3: every percent/pp pin (segment drivers and drivers, 7 metrics) and every highlights per-share cell bind; totals in the family-6 table below.
- **Asymmetry.** The same ZWSP inside the value cell makes `_literal` return None (`:981-985`), which is fail-closed. Beside the value it is fail-open.
- **Expected.** Unlocated: the nearest printed cell is a `$` (or `%`) that the pin's unit forbids.
- **Non-blocking sub-case.** Fullwidth `&#65284;` (＄) and `&#65285;` (％) also bind. They are lookalikes, not the characters R159 names; record them as a coverage decision for the seat.
- **Smallest repair.** Strip Unicode Cf characters (stdlib `unicodedata.category`) before the `_UNIT_CELLS` test and the printed test, or treat any neighbour whose text contains the forbidden character as a forbidden unit cell.

### G3-B3: blocking under bar (e) as written (R165): a header value naming a second year in any form other than an ASCII `20dd` adds no year
- **Code.** `_header_years` (`pg_envelope.py:891-892`) reads `(?<!\d)(20\d{2})(?!\d)` only. It does not read:
  - two-digit continuations: `2025/26`, `2025-26`, `2025&#8211;26`, `2024-25`, `2026-27`;
  - apostrophe years: `'25`, `'26`;
  - concatenated years: `20252026` (the look-arounds reject both halves);
  - all-non-ASCII digits: Arabic-Indic `٢٠٢٦` and fullwidth `２０２６` (the literal `20` prefix is ASCII). Mixed `20٢٦` IS read, because `\d` is Unicode, so `int()` yields 2026.
- **Construction** (`g3lib.fam8` sub `banner`: a single-cell row inserted at the top of each pinned table; probe `test_BLOCK_g3_b3_two_year_or_non_ascii_year_banner_over_highlights`). A banner `2025/26` over the highlights leaves DIL and CORE unlocated (their year, 2026, is not the set), but binds **PDIL and PCORE** on every quarter. The same holds in every year-bound table: earnings, both reconciliations, drivers, segment drivers and organic reconciliation. There, the metric whose year the banner's four-digit half names is bound.
  - Of the 29 banner values x 7 tables x 3 quarters, the bad counts are in the family-8 table.
- **Rule text.** R165 defines "the years over a cell" as every `20\d{2}`, so the engine meets the ruling's letter. The bar (e) text ("a header value that names two years") and bar (a) ("a header value that names a year other than the period's") are broader, and `2025/26` is the ordinary way a fiscal-year column is printed. The seat must either widen R165 (for example, fail closed on any header over a year-bound cell that holds a digit run other than one ASCII `20dd` or the pin's own header) or rule these forms outside the envelope. Until then this is blocking under the bar as written.
- Plausibility (coverage estimate, no fetch): `2025/26` or `2025-26` banners occur in a small share of EX-99 exhibits, mostly non-calendar filers. Non-ASCII digits: effectively never.

### Observations (non-blocking)
- **O1 (coverage).** Banners that name only the period year's cells in a form R165 reads as another value leave pins unlocated (`cover` counts in the family-8 table; for example `FY2025` and `FY26` change the table signature and the document is refused). This is fail-closed.
- **O2 (for G2/G4, outside G3's families).** The validator accepts a tamper of **every** key of the non-`pg_` typed absence `revenue` (Q3 row 0: schema, authority, reason, subject, detail, missing_fields, event_id and document_id each accepted). This is the generic issuer path, not an envelope row; bar (d) requires non-`pg_` behaviour to be unchanged from `f8e4af5aa4c`, which I did not check. Handed to G2/G4.
- **O3.** DIL/CORE primary cells (earnings, core reconciliation) with an invisible-character `%` neighbour are unlocated rather than bound. That is fail-closed; the fail-open cases are the highlights cells.

## Family coverage (probes run / failed)
### Family 6 (R145/R152/R159/R164), every pinned cell of Q1-Q3, both statements
| construction | kind | run | bad (bound) | admitted |
|---|---|---|---|---|
| carried_above1 | block | 288 | 0 | 288 |
| carried_above1_allow | control | 144 | 3 | 144 |
| carried_above2 | block | 240 | 0 | 240 |
| carried_above2_allow | control | 120 | 3 | 120 |
| incell_after | block | 228 | 0 | 228 |
| incell_before | block | 228 | 0 | 228 |
| incell_conflict | conflict | 228 | 0 | 228 |
| own | block | 504 | 0 | 504 |
| own_allow | control | 168 | 0 | 168 |
| own_invis | invis | 714 | 582 | 714 |
| shield | block | 143 | 0 | 143 |
| shield | invis | 143 | 123 | 143 |
| spans_down | block | 84 | 0 | 84 |
| **total** | | 3232 | 711 | |

Per quarter: {'Q1': 1076, 'Q3': 1078, 'Q2': 1078} exceptions: 0

### Family 8 (R147/R156/R165), metric-level judgements
| sub-family | judgements | bad (bound although a second year is named) | cover (fail-closed) |
|---|---|---|---|
| banner | 2958 | 650 | 132 |
| hl_dup | 12 | 12 | 0 |
| hl_rm | 12 | 0 | 0 |
| hl_swap | 24 | 0 | 0 |
| span2 | 12 | 9 | 0 |
| title | 148 | 12 | 0 |
| title2 | 148 | 0 | 0 |

Banner values: the per-value bad counts are in `f82_Q*.jsonl` (sub `banner`). Every single ASCII four-digit year and every reference-coded ASCII year binds correctly. Bad counts come from `2025/26`, `2025-26`, `2025&#8211;26`, `2024-25`, `2026-27`, `20252026`, `'25`/`'26`, and Arabic-Indic and fullwidth digits (G3-B3).

### Family 2 (duration relabels): 102 documents, 0 with a pinned-role fact present, 0 with any present fact, 0 exceptions; refusal details: {('envelope_refused:unknown_table:t2',): 12, ('envelope_refused:unknown_table:t3',): 9, ('envelope_refused:unknown_table:t4',): 18, ('envelope_refused:unknown_table:t6',): 18, ('envelope_refused:unknown_table:t9',): 30, ('envelope_refused:unknown_table:t11',): 12, ('envelope_refused:unknown_table:t12',): 3}

Harness artefacts, which are not findings:
- `hl_dup`: a duplicated highlights year row. The expectation was mis-set to None; the 12 "bad" rows are the correct *present* control.
- `title`: 12 rows. In each, a core-reconciliation title was edited and the metric flagged is governed by the **other** title (Q2 c3/c21, Q3 c3/c27). Every governed cell unlocated correctly.
- The `carried_above*_allow` controls: 6 rows changed COREG (Q3) from present to unlocated. This is fail-closed coverage.

Family 6's `block` kinds cover literal `%`/`$`, `&#37;`, `&percnt;`, `&#36;` and `&dollar;`, and each of these placements: own-row nearest, shielded by empty cells, carried by rowspan from 1 and 2 rows above, and the pinned cell spanning down into a row with a forbidden neighbour. Result: **0 of 1,715 bind**. So R164 holds for every construction its text names on every pinned cell of Q1-Q3. The in-cell markers (before, after, entity) give 0 of 456 bound. The marker-plus-disagreeing-value pairs all give `conflict` (228/228). Family 2 (duration relabels: six-, nine- and twelve-month, fiscal year, year, "three and six", six-/nine-/twelve-month ranges, and the highlights quarter word) refused all 102 documents with `unknown_table`, and no present fact reached any of them.

### Probe file `test_envelope_audit_probes_r6_g3.py` (157 cases)
- 3.14 (`venv_t1`): 41 failed, 107 passed and 9 skipped. The 41 failures are exactly the `test_BLOCK_*` cases: G3-B1 5, G3-B2 15, G3-B3 21.
- 3.12 (`venv312_min`): 41 failed, 107 passed and 9 skipped. The set is identical.
- The skips are B2 depth-2 variants whose layout has no same-extent cell two rows up. Where the layout allows, those variants are realised in fam6.
- Passing variants:
  - family 0: B2 original plus 8 variants (Q1/Q2/Q3, `%`, `&#37;`, `&percnt;`, a `$` carried beside a percent value);
  - m1 extractor side (4) and m3 (5: the seat witness plus 4 variants across other tables and quarters);
  - m2 OBSERVE (4);
  - family 7: 42 TYPE-line refusals and 6 CR/CRLF admissions;
  - family 1: 36 variants.

## Family 0 (G3's part)
- **B2: closed.** The original construction (R5 probe `test_b2_rowspan_carried_percent_cell_beside_a_per_share_value`) passes at the head. Nine further pytest variants and 1,715 family-6 constructions also pass, including carries from two rows above and the pinned cell spanning down. G3-B2 is a new hole beside R164, not a reopening of B2.
- **m1: inside R166.** R5 OBSERVE `bare_nbsp_then_digits` and `bare_nbsp_then_ref` are still accepted, which is the recorded limit. On the extractor side, `&nbsp1.95` (Q1), `&nbsp1.78` and `&amp1.78` (Q2), and `&nbsp1&#46;63` (Q3) in the DIL cell each leave DIL unlocated (R154 holds).
- **m2: inside R166.** On the extractor side, `&#1;`, `&#x1;`, `&#11;` and `&#65534;` before the literal bind with the span equal to the literal, and the workspace validates. That is value-correct: the dropped code point lies outside the span. Recorded, not a finding.
- **m3: closed** for four-digit years: `2026/2025`, `2025/2026`, `2025 2024`, `2025,2026` and `2026(a) 2025` over five tables and three quarters all unlocate. Its generalisation to other year spellings is G3-B3.

## Family 1 (one new variant per round-1..4 finding): 36 passed, 0 failed
- R1: F-D1 (a lowercase CRLF wrapper), F-C1/F-C2/R2-B6 (a dropped or unknown metric is refused), F-E1 (a non-pinned value edited still admits), F-E2/F-B1/R2-B9 (a repeated or missing table binds nothing), F-F1/F-F2 (fullwidth, inner-space and Arabic-Indic literals; a bare dash without `%`).
- R2: B3 (day mismatch on Q1 and Q3), B4/R4-P2 (span width ±1), B5 (`pg_` typed-absence detail), B7/R3-N1 (three layout prefixes), B8/R3-N2 (a truncated pinned row), B10 (VT/FF, BOM plus CRLF, and U+3000 before the wrapper). B1 and B2 are covered by family 2's range relabels and nine- and twelve-month relabels.
- R3: N3 (cache and order independence over 11 refused and banner sources), N4 (a marker on the second statement only), N6 (two single-year banners), N8 (two unclosed-table forms). N5 and M1 are covered by family 7, and N7 by family 2's "Fiscal Year".
- R4: P4 (400-digit literals), M2 (structural tags inside a well-formed comment). P1 is covered by the m1 extractor variants, P3 by the family-8 banners, and M3 by family 6. M1 is G2's (R166).
- Not varied by G3: R2-B11 and the S0 behaviour (G4), R4-M1 and the seam (G2).

## EVIDENCE
- `git rev-parse HEAD` -> `135a67a3e1244f87257f7866e96c2d0c12551620` and `git status --porcelain` -> empty, before the first run and after the last.
- `git diff c691b7a98b0 135a67a3e12 -- engine/`: R164 rewrites `_neighbours_admit` (`:1065-1075`) and R165 rewrites `_header_years` (`:891-892`).
- Sweeps: `g3lib.py fam6|fam8|fam2 Q1|Q2|Q3`, output in `f6_Q*.jsonl` and `f82_Q*.jsonl`. `*.err` is empty (0 bytes), and there were 0 exceptions over 3,232 + 3,314 + 102 builds.
- Probe runs (tails): 3.14 `41 failed, 107 passed, 9 skipped in 66.62s`; 3.12 `41 failed, 107 passed, 9 skipped in 70.76s`.
- R5 probe file at the head (3.14): `4 failed, 11 passed in 8.34s`. The failures are B3's three cases and `attribute_gt_lt` (KeyError, refused at admission). All four are G1/G4's to account for. B2 and both m1 OBSERVE cases pass.

## GAPS
- R165's rowspan-carried year rows were probed only as controls, through the highlights year-row duplicate, swap and removal. A year cell carried *into* a row over a pinned column from a multi-cell origin row, where it does not cover `col0`, was not built separately. G3-B1's repair must cover it.
- The non-governing `_period_titles` fallback (a table whose only title does not cover the cell) was not constructed.
- The invisible-character class was tested with U+200B, U+FEFF and U+00AD. Other Cf characters (U+2060, U+200C/D, bidi marks) are expected to behave the same but were not run.
- O2 (non-`pg_` typed-absence tampers accepted) was not compared against `f8e4af5aa4c`.

---

## Group G4: families 12, 13 and 14 (verbatim)

STATUS: REJECT (G4 scope) — 1 blocker (G4-B1, bar c), 0 majors, 2 minors (G4-m1, G4-m2), nits (G4-n1).

# Summary
- **G4-B1 (bar c).** `engine/company_intelligence/economic_observations.py:248-254` counts any tag or comment as a delimiter. A seam relocation of the Q3 DIL receipt onto `1.63` glued to printed text through markup is accepted, in 5 of 5 forms. One form is `<p>-<b></b>1.63</p>`, where a reader prints `-1.63`. None of the five is on R166's list.
  - Expected: the validator refuses. Observed: it accepts.
  - Probe: `test_b1_relocation_onto_a_literal_glued_by_markup_is_refused[*]`.
  - Smallest repair, either:
    - (a) in `_validate_envelope_span`, skip tags and comments when looking for the printed neighbour, and require the nearest printed character on each side to be whitespace, or a cell/block boundary tag (`td`, `th`, `tr`, `table`, `p`, `div`, `br`); or
    - (b) a seat ruling that adds "a literal glued to printed text through inline markup" to R166's list. That ruling contradicts R163's own rationale for B3.
- **G4-m1.** The seat's account of the round-5 probe file at HEAD is wrong. The 4 failures are 3 B3 cases and 1 OBSERVE case, all `KeyError` because the body is now refused. The seat called all 4 OBSERVE cases. The outcome is acceptable.
- **G4-m2.** R167's witness holds at kind granularity only. Twelve `_unreadable_markup`/`_spans_read_alike` branches have no isolating R5 witness (`pg_envelope.py:247, 250, 252, 254, 293, 303, 307, 329, 333, 341, 343`, and the rowspan limit at `:52`).
  - Smallest repair: freeze one case per branch. The 6 positive probes in the G4 file are ready-made.
- **G4-n1.**
  - `_START_TAG` duplicates `_ATTRIBUTE`'s grammar (`:33-40`).
  - `_SPAN_LIMITS` is a mutable dict (`:52`).
  - The engine-agreement branches `:247` and `:252` are unreachable while `:254` holds.
  - `_header_years` uses Unicode `\d` (`:891-892`).
- **Everything else in scope holds:**
  - integrity: git diffs and log exactly as required;
  - the six suites: 537/537 on 3.12 and on 3.14;
  - the gate line: 1361 passed, 174 skipped;
  - `curated_exclusive`: 2 passed;
  - a5a and capital-structure: per-test identical to `f8e4af5aa4c` (213);
  - the earlier probe files: every change accounted for;
  - R167's witness table reproduced exactly (15/15 rows);
  - the census: 0/476 earlier cases and 41/61 R5 cases reach the new refusal;
  - the dead-rule sweep: R163 made no R143–R162 rule dead;
  - the span double reading: 0 divergences in 40,000 attribute strings (engine = R163 = html5lib).

# Family coverage (probes/runs, failed)
| family | runs/probes | failed / finding |
|---|---|---|
| NOT DONE runs | 6 suites × 2 interpreters, gate, curated, cs × 2 revisions, 5 earlier probe files | 0 unexplained |
| 14(i) witness table | 15 in-memory removals on the R5 suite, plus the freeze at a1220205b09 | 15/15 match R167; 45 fail / 16 pass at a122 |
| 14(ii) open constructions | 5 glued-by-markup relocations + 1 control | 5 → G4-B1 |
| 14(iii)–(v) | code read + existing runs | none |
| 14(iv) sub-rule isolation | 26 sub-rule removals + 6 positive probes | 12 unisolated → G4-m2; 6/6 positive pass |
| 14(vi) census | 537 cases | 41, all in R5 |
| 13 dead-rule sweep | 12 rules × (HEAD, HEAD − R163) = 24 six-suite runs | 0 dead; raw and ws unwitnessed as R162 records |
| 13 span differential | 40,000 seeded attribute strings | 0 |
| 13 code read | 3 commits + envelope diff | G4-n1 |
| 12 hosted CI | 2 reads, once each | packs 1, 5, 8 and 9 in progress; no ci-gate (GAP) |
| G4 probe file | 19 cases, on 3.14.7+html5lib and on 3.12 | 5 failed (G4-B1), 14 passed, on both |

---

# Opus re-audit R6, group G4: CDV-1 T1 F1-Q envelope at 135a67a3e1244f87257f7866e96c2d0c12551620 (PR #7905)

MODE: READ_ONLY. Scope: G4 NOT DONE UNLESS runs, families 12, 13, 14. (Report written incrementally.)

## Integrity (git)
- HEAD = 135a67a3e12…; `git status --porcelain` empty (before first run).
- `git diff --stat 4eeba3807d7 HEAD -- tests/ research/ .github/`: empty.
- `git diff --stat a1220205b09 4eeba3807d7`: legacy-jobs.yml (+1/-1 run line, +1 path), OPUS R5 record, SEAT R5 ruling, R5 suite (434 lines). Nothing else.
- `git log a1220205b09..HEAD --name-only`: 4eeba3807d7 (freeze: 4 files above), then c691b7a98b0 (R163), 97bf82cc88d (R164), 135a67a3e12 (R165), each touching only engine/company_intelligence/pg_envelope.py.
- Five earlier suites + tests/fixtures/pg_envelope/ byte-identical a1220205b09..HEAD.

## Runs at HEAD
- six suites 3.12 (venv312_min): 537 passed, 80 warnings in 170.87s
- six suites 3.14 (venv_t1): 537 passed, 80 warnings in 165.50s
- gate run line (earnings-economic-dossier job, venv312_min): 1361 passed, 174 skipped, 80 warnings in 193.87s (seat: 1361/174 in 195.78s — matches)
- `tests/test_ci_pack.py -k curated_exclusive` (/opt/homebrew/bin/python3.12): 2 passed, 119 deselected, 80 warnings in 232.61s
- a5a + four capital-structure suites at HEAD (/opt/homebrew/bin/python3.12, -rA): 213 passed, 80 warnings in 38.96s.
- The same five suites at f8e4af5aa4c, from my own `git archive` tree under g4/f8e: 211 passed, 2 failed.
  - `cs.diff` (7 lines, 526 bytes) accounted line by line:
    - `< FAILED …authenticated_read.py::test_authenticated_read_fails_closed_without_trust` and `< FAILED …companyfacts.py::test_noop_runs_do_not_inflate_receipt_chain_and_caps_are_fail_closed`: both are `FileNotFoundError: …/g4/f8e/config.yml` raised from `lib/config.py:31` — my archive excluded the root `config.yml`. **Harness artifact**, not an outcome change.
    - `> PASSED` of the same two tests at HEAD: the counterpart lines.
  - Independent cross-check: HEAD's 213 PASSED node ids equal the seat's `baseline_a5a_cs_f8e4af5.txt` exactly (diff empty). Closing re-run of the two tests with `config.yml` restored: see addendum.

## Earlier probe files at HEAD (3.14, venv_t1), against round 5
- R1 (`audit_t1_envelope/test_envelope_audit_probes.py`): 4 failed, 99 passed. Same set as round 5: `f4[2.0 pts]`, `f4[— per share]`, `f7_drivers_title_date_removed`, `f10_control_q4…` (recorded artefacts / original reading). No change.
- R2: 1 failed, 67 passed — `test_d_s0_validator_missing_fields_tamper_outcome_unchanged` (B11, superseded by R139). No change.
- R3: see addendum (running).
- R4: 13 failed, 1092 passed, 27 skipped (743.70s). Failure set byte-identical to round 5's `old_r4_probes.log` (8 `long_named_ref_33`, 3 title-fuzz artefacts, `f14_OBSERVE_same_value_relocation_accepted_limit`, `f14_r153_case_fails_exactly_without_the_inline_unit_rule`). No change.
- R5 (15 cases): round 5 = 11 failed, 4 passed; HEAD = **4 failed, 11 passed**. Case by case:
  - 3 × `test_b1_text_a_reader_prints_inside_the_pinned_cell_is_not_hidden[…]`, 3 × `test_b1_a_second_diluted_row…`, `test_b1_an_unclosed_comment…`: F→P. The document is refused `markup_unreadable:comment`, so DIL is not present — the probe's expectation.
  - `test_b2_rowspan_carried_percent_cell…`: F→P (R164; DIL unlocated).
  - 3 × `test_b3_relocation…[text_gt_before, text_lt_after, cdata_bogus]`: F→F, **reason changed**: `KeyError: 'source_span'`. The relocated body is refused at admission (`gt`, `lt`, `tag`), so there is no present DIL row to relocate; the probe cannot reach its assertion. The substance (relocation built past the gate is refused by the validator's replay) is carried by the frozen `test_r163_a_relocation_onto_a_literal_beside_a_text_bracket_is_refused[gt,lt,tag]`, which passes at HEAD and fails (AttributeError, no gate) at a1220205b09. Stronger outcome: accepted.
  - `test_OBSERVE_relocation_inside_r155_limit_is_accepted[attribute_gt_lt]`: P→F, `KeyError: 'source_span'` — `<p title=">1.63<">` is now refused `markup_unreadable:tag`; R166 moves this form outside the envelope. Stronger outcome.
  - `OBSERVE[script_text]`, `OBSERVE[bare_nbsp_then_digits]`, `OBSERVE[bare_nbsp_then_ref]`: P→P (inside R166's restated limit).
  - **Seat testimony is inaccurate** (G4-m1): it says "the 4 are the OBSERVE relocation cases"; the 4 failures are 3 B3 cases and 1 OBSERVE case. Outcome acceptable; the record is wrong.

## Family 14 (i): R167 witness table, reproduced with my own harness (`g4/g4_mut.py`, in memory; R5 suite, venv312_min)
My harness restores R164 and R165 by executing a1220205b09's own `_neighbours_admit` / `_header_years` (AST-extracted from `git show`), not the seat's re-implementations. Kind removal = the check returns None when its first kind is that kind (same semantics as R167's note).

| removed | seat R167 | G4 | cases failing (G4) |
|---|---|---|---|
| none | 0 | 0 | — |
| whole R163 | 41 | 41 | 36 markup + 2 replay + 3 relocation |
| comment | 8 | 8 | 3 in-cell closers, 3 second-row closers, unclosed comment, replay[comment] |
| gt | 2 | 2 | M[gt_text], relocation[gt] |
| lt | 3 | 3 | M[lt_text], M[lt_in_the_pinned_cell], relocation[lt] |
| tag | 6 | 6 | 5 M[tag_*], relocation[tag] |
| element | 6 | 6 | 6 M[element_*] |
| table | 7 | 7 | 7 M[table_*] |
| span | 6 | 6 | 6 M[span_*] |
| grid | 3 | 3 | M[grid_hole], M[grid_overlap], replay[grid] |
| three early closers | 7 | 7 | 6 closer cases + replay[comment] |
| raw text in a table | 1 | 1 | M[element_script_in_the_pinned_cell] |
| span limits | 1 | 1 | M[span_over_the_limit] |
| R164 (a1220205b09 function) | 2 | 2 | r164[carried_cell], r164[spanning_value] |
| R165 (a1220205b09 function) | 2 | 2 | both r165 witnesses |

**Reproduced exactly.** The freeze at a1220205b09 (tree `git archive 4eeba3807d7`, whose engine file `cmp`-equals a1220205b09's): 45 failed, 16 passed on venv312_min — matches R167. Failure reasons: markup cases fail with present rows (detail set contains None, i.e. admitted and bound); 5 AttributeError (no `_unreadable_markup` to replace: 2 replay + 3 relocation); R164 `1.63 == 'unlocated'` ×2; R165 `1.59 == 'unlocated'` and the PCORE/PDIL tuple.

## Family 14 (vi): census
Recorder wrapped around `_unreadable_markup` across all six suites (537 cases, venv312_min): refusals in **41** test node ids, **all 41 in `test_pg_envelope_f1_probes_r5.py`, 0 in the 476 earlier cases**. First-kind distribution comment 8, table 7, element 6, span 6, tag 6, grid 3, lt 3, gt 2 (= 41, identical to the kind rows of R167). 77 non-None calls in total (the validator replay re-calls). Reproduced.

## Addendum A (closures)
- f8e4af5aa4c re-run of the two artifact tests with `config.yml` restored (`git show f8e4af5aa4c:config.yml`): 2 passed. So per-test outcomes at f8e4af5aa4c = HEAD = 213 PASSED; `cs.diff` is entirely harness artifact.
- Earlier R3 probe file at HEAD (3.14): 4 failed, 220 passed, 1 skipped (923.71s). Failure set identical to round 5 (`n4[Q3-DIL-0-1.63%-second:1.64]` conflict sanctioned by R152; 3 × `f9…span_display_none` R151 artefacts). No change.

## Family 14 (ii)–(v) and family 13: findings

### G4-B1 — blocking (bar c; 14(ii): B3's class left open). A seam relocation onto a literal glued to printed text through markup is accepted.
- Probe: `test_b1_relocation_onto_a_literal_glued_by_markup_is_refused[digit_then_empty_inline_element, minus_then_empty_inline_element, digit_then_comment, literal_then_inline_digit, decimal_split_by_element]` — **5/5 FAIL at HEAD** (`assert not True`: the validator accepts). Control `test_control_relocation_onto_a_literal_in_its_own_paragraph_is_accepted` passes.
- Construction (as the frozen R5 relocation cases do: `r4.reseat` through R143's seam, fragment inserted before `</text>`; R163 admits each fragment — asserted in the probe):
  - `<p>9<b></b>1.63</p>` — a reader prints `91.63`;
  - `<p>-<b></b>1.63</p>` — a reader prints **`-1.63`, a different value**, and the validator certifies a DIL receipt of 1.63 on it;
  - `<p>9<!-- c -->1.63</p>` (`91.63`), `<p>1.63<b>9</b></p>` (`1.639`), `<p>2<i></i>1.63</p>` (`21.63`).
- Expected: refused — each is "a value a reader prints as part of a longer token", the exact class the seat's R163/R166 rationale says R114 forbids accepting (SEAT_RULING_T1_ENVELOPE_R5 §"One admission rule closes the class"). Observed: accepted.
- Classification against R166's list: not "another cell", not hidden text, not script/style, not inside a comment between `>` and `<`, not after a bare legacy reference, not after a dropped code point. **Outside the list → blocking under the bar as written.** The seat may argue R166's prose "delimited by markup or whitespace" covers it; if so, the list is incomplete and the ruling contradicts its own rationale for B3.
- Cause: `engine/company_intelligence/economic_observations.py:248-254` bounds the gap by the nearest raw `>` / `<`, so any tag or comment counts as a delimiter even when the reader's text flow glues the neighbours. R163 closed only *text* brackets. Pre-existing since R155 (not a regression of the repair), but it is an open construction of a finding round 5 raised.

### G4-m1 — minor (testimony). The seat's account of the round-5 probe file at HEAD is wrong.
- Seat: "11 passed and 4 failed. The 4 are the OBSERVE relocation cases." Observed: the 4 failures are 3 × `test_b3_relocation…` and 1 × `test_OBSERVE…[attribute_gt_lt]`, all `KeyError: 'source_span'` because the body is now refused at admission; the other 3 OBSERVE cases pass. Outcome acceptable (stronger); record inaccurate.

### G4-m2 — minor (14(iv): freeze isolation). R167's "each rule is load-bearing" holds only at kind granularity; twelve R163 branches have no isolating R5 witness.
Removing each alone (in memory, `g4_mut.py sub_*`, R5 suite) fails **0** cases:
- raw-text element with no end tag, `pg_envelope.py:293` (`close is None`);
- non-`tr` start tag in table state `:303`; non-cell start tag in row state `:307` (both shadowed by the text-in-table check);
- end tag other than `</table>` in table state `:329`; other than `</tr>` in row state `:333`; table-name end tag inside a cell `:341`;
- unclosed table at end of source `:343`;
- rowspan limit (`_SPAN_LIMITS["rowspan"]`, `:52`) — only the colspan limit is witnessed;
- duplicate span `:250` (shadowed by the digits check in `span_repeated`), engine agreement `:252`, engine-only `:247`, span text in another attribute `:254` (the last two shadow each other).
Branches that *are* isolated (fail ≥1): `>`-start closer 3, `->`-start 2, `--!>` 2, unclosed comment 1, text `>` 2, text in table 1, raw-text bracket 2, row tag outside a table 1, overlap 1, hole 2, start tag in a cell 1, colspan limit 1, span digits 1, `_UNREAD_ELEMENTS` 3.
My positive probes `test_sub_rule_refuses_with_its_kind[…]` show the unwitnessed branches do fire with the right kind on constructions of their own (see run). Mutual shadowing means a later edit can delete one of each pair with the suite green.

### G4-n1 — nit/code quality (family 13)
- `_START_TAG` (`pg_envelope.py:37-40`) re-spells `_ATTRIBUTE`'s grammar (`:33-36`) inline; the two must stay equal for `_span_attributes` to re-tokenise exactly what `_START_TAG` accepted. Not wrong today.
- `_SPAN_LIMITS` (`:52`) is a mutable module dict read at call time (the seat's harness mutates it); a frozen mapping would match the file's other constants.
- `engine is None or engine.group(1) != values[0]` (`:252`) and `if engine is not None: return False` (`:247`) are unreachable while `:254` holds (defence in depth). Differential: 40,000 seeded attribute strings (seed 20260925), every `<td …>` R163 admits gives engine `_SPAN_PATTERNS` value = R163 value = html5lib 1.1 attribute value (`test_c1_…` passes) — **the double reading leaves no value both read and wrong** in that corpus.
- `_header_years` (`:891-892`) and `_parse_year` (`:895-897`) use Unicode `\d`; `20٢٥` reads as 2025 (pre-existing in `_parse_year`; G3's family 8 owns the outcome).
- No `try`/`except`, `raise`, new import, per-release literal or probe-specific branch in the repair (AST check `test_i4` passes; diff read).
- `extract` refuses any non-`F1-Q` admission (`pg_envelope.py:1143`); both callers (`pg_profile.py:2173-2175`, `economic_observations.py:276-278`) pass an `admit()` result, so no path skips R163.
- Minimality: `_neighbours_admit` (`:1065-1075`) and `_header_years` are minimal for R164/R165. `_unreadable_markup` maps branch-for-branch to R163's text.

### Family 14 (iii)–(v)
- (iii) R131 exceptions. `ungated` (R5 suite `:190-194`) replaces `_unreadable_markup` inside `monkeypatch.context()` for the build only; validation runs after the context exits against the real, un-polluted `lru_cache`d function, so the replay witnesses test the real gate. `r4.reseat` stays patched through validation (R143's seam, as in R4). Sound. R160's census exception is not used by the R5 suite.
- (iv) Controls. The eight KEPT controls, R164's `$` control and R165's `2025/2025` control pass at HEAD and at a1220205b09, and each asserts the full expected value map plus validation — they prove admission and unchanged binding, not reader equivalence (that is G1's differential). The two order witnesses pin R163 after `quarter_mismatch` and after `unknown_table`; they do not pin it after `not_ex_99_1`, `generator_not_workiva`, `issuer_not_pg`, `required_table_repeated/missing`. The code puts it last (`pg_envelope.py:770-771`), so this is witness breadth only (folded into G4-m2).
- (v) No R5 case contradicts an earlier frozen case: all 476 earlier cases pass at HEAD, and the census shows none reaches R163. `comment_holding_brackets` is consistent with R158/R143 (a well-formed comment is blanked and forms one unit).
- Sub-rule positive probes (`test_sub_rule_refuses_with_its_kind`, 6 cases) pass: raw text unclosed → `element`; `rowspan="65535"` → `span`; last `</tr>` removed before `</table>` → `table`; `</tr><tr>` in place of DIL's `</td>` → `table`; stray `</td>` between rows → `table` (a reader ignores that stray end tag: coverage cost, not a finding); last table left unclosed → `table` (the unclosed-table branch `:343` is reachable only for the last table — every earlier table left unclosed is refused first as `unknown_table:tN`).

## Probe file run (`g4/test_envelope_audit_probes_r6_g4.py`, 19 cases)
- /opt/homebrew/bin/python3 (3.14.7, html5lib 1.1): 5 failed, 14 passed in 10.08s — the 5 are G4-B1.
- venv312_min (3.12): 5 failed, 14 passed in 12.54s (the html5lib leg of `test_c1` is skipped by import there; the engine-vs-R163 leg runs).

## Family 13: dead-rule sweep over R143–R162 (six suites, 537 cases, venv312_min, in memory)
The seat's round-4 mutation definitions (`mutate_run.py`; each `patch()` asserts that its text was found) were run twice: at HEAD (`d_*`), and at HEAD with the whole R163 check also removed (`dc_*`). R163 alone fails 41.

| rule removed | R162 matrix at d678c8a | at HEAD | HEAD with R163 removed (−41) | verdict |
|---|---|---|---|---|
| R154 start check | 4 | 4 | 45 (4) | live |
| R155 whole-literal gap | 36 | 36 | 77 (36) | live |
| R153 inline unit | (R162 witnesses) | 3 | 44 (3) | live |
| value parse | — | 1 | 42 (1) | live |
| raw-literal check | 0 (defence in depth) | 0 | 41 (0) | unwitnessed, as R162 records; **not** made dead by R163 |
| decodes-to-whitespace | 0 (defence in depth) | 0 | 41 (0) | unwitnessed, as R162 records; not made dead by R163 |
| R156 period half | 1 | 2 | 43 (2) | live (+1 is R165's first witness) |
| R156 locate half | 1 | 2 | 43 (2) | live |
| R157 finite | 2 | 2 | 43 (2) | live |
| R158 comment blanking | 3 | 3 | 44 (3) | live — R163 still admits well-formed comments, whose tags R158 must blank |
| R159/R164 neighbours | 3 | 5 | 46 (5) | live (+2 are R164's witnesses) |
| R160 vocabularies | 1 | 1 | 42 (1) | live |

**R163 made no R143–R162 rule unreachable in the suite:** every rule fails the same count with and without R163. The only zero-witness checks are the two R162 already names as defence in depth.

## Family 12: hosted CI at 135a67a3e12 (one read each)
- check-runs total_count 25. Concluded success: ci-pack-0, 2, 3, 4, 6, 7, 10, 11; ci-plan; contract-delta; fence-pack; fences-family (grader-manifest, capability-broker, self-mod-fence); ci-authority; ci-authority/main. `ci-authority/codex/merge-queue-pilot` failure (known, non-binding). trusted-ci and three fork-guard checks skipped.
- **In progress: ci-pack-1, ci-pack-5, ci-pack-8, ci-pack-9. No `ci-gate` check-run yet.**
- `earnings-economic-dossier`: local plan `run_ci_pack.py --validate-only --changed-from 8a8ecbe868f` (merge-base with local origin/main, which may lag the hosted base) places it in **pack 8** — in progress, no conclusion.
- Run list: `ci` 36175048268 at 135a67a3e12 in_progress; `fences` 36175047945 and `ci-authority` 36175046645 success. The `ci` runs at a1220205b09, d678c8a4671, 2a8d1eb1a9c and a0b222033fa all concluded `cancelled` (superseded). Not polled, re-run or cancelled.

## Final state
- After the last run: `git rev-parse HEAD` = 135a67a3e1244f87257f7866e96c2d0c12551620; `git status --porcelain` empty.

## (status restated at top)

## GAPS
- Hosted `ci-pack-1/5/8/9` and `ci-gate` not concluded at my single read; earnings-economic-dossier's pack (8, local plan) has no conclusion.
- The pack mapping is local, computed against a possibly stale local origin/main merge-base.
- The census counts refusals per test node id (first kind per case); the 34-of-36 "DIL binds 1.63" sub-claim of R167 was checked by failure class only, not per case.
- G4-B1 was probed on Q3 DIL only, with inserted fragments before `</text>`; other quarters, metrics and in-table placements are not enumerated (G2 owns the full seam sweep).
- The sweep ran on 3.12 only; the witness table on 3.12 only.

## DEVIATIONS
- `runs2.sh` lane 4 invoked `g4_mut.py` while I was editing it; eleven `d_*` runs died on a SyntaxError and were re-run from `runs5.sh`/`runs4.sh` (results above are the re-runs). `d_r163only` over the six suites was not re-run; the census plus `w_r163` (41) cover it.
- My first f8e4af5aa4c archive omitted the root `config.yml` (two artifact failures, closed above). My first a1220205b09 freeze run (`PYTHONPATH` prepend) imported the worktree engine and was discarded; the authoritative run used a `git archive 4eeba3807d7` tree whose engine `cmp`-equals a1220205b09's.
- I killed one of my own wait loops, because its process filter also matched other groups' probe files. I touched no other group's process.
