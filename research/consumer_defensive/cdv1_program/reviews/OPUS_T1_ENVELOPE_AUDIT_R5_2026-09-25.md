# Opus re-audit R5: CDV-1 T1 F1-Q envelope at a1220205b09894acf1e628677db7a125506cfabf (PR #7905)

MODE: READ_ONLY. Probe file: `audit_t1_envelope_r5/test_envelope_audit_probes_r5.py`. Run it from the checkout root with `PYTHONPATH=.`: 11 failed, 4 passed (the 4 passes are the OBSERVE cases).

## STATUS: REJECT

## Findings

### B1: blocking (bars a and b). The engine's comment grammar is not the one an HTML reader uses.
- **Code.** `_COMMENT` and the comment branch of `_UNIT` are `<!--.*?-->` (`engine/company_intelligence/pg_envelope.py:29-30`). `_structure` (`:181-183`) blanks each match for every structural scan (R158). `_units` (`:111-118`) drops each match from cell text (R143).
- **How a reader differs.** The HTML5 tokenizer closes a comment at `<!-->`, `<!--->` and `--!>`, and an unclosed `<!--` hides everything after it. The engine keeps going to the next `-->`, and it does not treat an unclosed `<!--` as a comment at all.
- **Probes:**
  - `test_b1_text_a_reader_prints_inside_the_pinned_cell_is_not_hidden[<!-->, <!--->, <!-- a --!>]` (3 cases). The Q3 DIL primary cell becomes `<opener>9.99<!-- z -->1.63`, which a reader prints as `9.991.63`.
    - Observed: DIL is present at 1.63, span `1.63`, and the validator accepts.
    - Expected: DIL is not present.
    - Origin: the R143 grammar, so this predates the round.
  - `test_b1_a_second_diluted_row_a_reader_prints_is_not_hidden[...]` (3 cases). A second Diluted row (9.99 / 9.98) sits between `<opener>` and `<!-- z -->` in the Q3 earnings table.
    - Observed: DIL is present at 1.63 and the validator accepts. The round-0 witness gives `unlocated`.
    - Expected: `unlocated` (R130).
    - Origin: introduced by R158. Before R158, the structural scan saw this row.
  - `test_b1_an_unclosed_comment_hides_every_later_table_from_a_reader`. A `<!--` with no later `-->` is placed after the earnings table.
    - Observed: SALES 7.0, CORE 1.59 and DIL 1.63 bind from tables a reader never renders, and the validator accepts.
    - Expected: no present fact from a table a reader cannot see.
    - Origin: predates the round.
- **Why the validator accepts.** The replay uses the same grammar. The R155 gap scan ends at the `>` of `-->`, so it sees an empty gap.

#### The coordinator's three questions, answered
1. **Is this inside the envelope?**
   - The documents are outside F1-Q. The three originals hold exactly two comments each, both well-formed Wdesk comments in `<head>` at offsets 140 and 178. None holds `<!-->`, `<!--->`, `--!>` or an unclosed `<!--`.
   - That is why this is blocking, not an exemption. R114 makes the envelope finite, and the envelope contract fails closed. Bar (b) says a document outside F1-Q yields no present fact.
   - The seat applied this rule itself in round 4. It raised M2 to a blocker although `<!-- </table> -->` occurs in no original.
2. **Does a present value have to be one a reader of the rendered document sees?**
   - Yes. All seven cases bind a value that a reader of the rendered bytes does not see as that literal in that place: `9.991.63`, a second visible Diluted row, or tables hidden by the comment.
   - This breaks R158's own premise ("a browser prints both Diluted rows") and R143's "comments lie outside the span". A comment has to be one the reader also closes where the engine closes it.
3. **Smallest repair: fail closed at admission. Do not model HTML5 comments.**
   - In `_admission`, after the Wdesk check and before the table loop, refuse the document when either holds:
     - some `<!--` in the source does not begin a `_COMMENT` match (an unclosed comment);
     - some `_COMMENT` match's interior starts with `>` or `->`, or contains `--!>`.
   - One check covers both paths, because `_structure` and `_units` share `_COMMENT`. The validator replays admission, so it needs no change.
   - The refusal is an admission code under the existing reason `no_span_addressable_evidence`. It adds no absence reason. The seat names the code.
   - The frozen well-formed-comment cases stay green: the R158 controls, the r1 `f5` comment control, and the R4 relocations, whose comments are all well-formed.
   - Refusing every comment outside `<head>` would be smaller still, but it would break R158's frozen controls.

### B2: blocking (bar a, R159). A `%` cell carried by rowspan beside a per-share value is ignored.
- **Code.** `_neighbours_admit` filters on `other.row == cell.row` (`pg_envelope.py:930-938`), so it never considers a cell carried by rowspan. A reader sees that cell in the value's row.
- **Probe.** `test_b2_rowspan_carried_percent_cell_beside_a_per_share_value`. The Q3 earnings `Basic` row's `$` cell becomes `<td rowspan="2">%</td>`, and the Diluted row's own `$` cell is removed, so a reader sees `% | 1.63`.
  - Observed: DIL is present at 1.63 as usd_per_share, PDIL is 1.54, and the validator accepts.
  - Expected: DIL is unlocated. The same construction in the value's own row (`%` in place of the row's own `$`) is unlocated at this head.
- **Smallest repair.** Drop `other.row == cell.row` from `_neighbours_admit`, so the grid row, carried cells included, supplies the nearest neighbours. The seat must re-verify that no pinned cell in the three originals has a carried forbidden unit cell beside it. R159's census covered own-row cells only.

### B3: blocking under the bar as written (c, R155). A relocation onto a same-value substring delimited by a text `<` or `>` is accepted.
- **Code.** `economic_observations.py:248-254` treats any `>` or `<` byte as a delimiter. A raw `>` or `<` in text is printed.
- **Probe.** `test_b3_relocation_onto_a_literal_glued_to_a_text_angle_bracket_is_refused[text_gt_before, text_lt_after, cdata_bogus]`. The DIL receipt is moved through the R143 seam onto `1.63` in each of:
  - `<p>9>1.63</p>`, which a reader prints as `9>1.63`;
  - `<p>1.63< x</p>`, which prints as `1.63< x`;
  - `<![CDATA[>1.63<]]>`, which prints as `1.63<]]>`, because the bogus comment ends at the first `>`.
  - Observed: all three are accepted.
  - Expected: refused. The span is not a whole printed literal, and the adjacent `<` or `>` is text, not the "markup whose own characters" named in R155's limit.
- **Substance.** Value and unit still match. The loss is location only, which the limit already gives up for hidden, script and attribute literals.
- **Smallest repair.** A ruling amendment, with no code: widen R155's limit to "a literal delimited on either side by a raw `<` or `>` byte, whether markup or text". Telling text from markup needs a tokenizer, and R143 forbids the independent check from using one.

### Minor
- **m1.** R155's premise "`html.unescape` reads references with R143's grammar" is false.
  - R143's `_UNIT` reads `&nbsp1.63` as one unit, through the greedy name class `[^\t\n\f <&#;]{1,32}`. `html.unescape` reads `&nbsp` + `1.63`, by longest legacy prefix.
  - Consequence: relocations onto `1.63` or `1&#46;63` after a bare `&nbsp` are accepted (the OBSERVE cases `bare_nbsp_*`).
  - A reader sees an NBSP-delimited literal, so these fall inside the limit. They still violate R143's span definition, which R154 enforces on the extractor side.
  - Repair: correct the ruling text.
- **m2.** `html.unescape` drops invalid code points: `&#1;` decodes to an empty string, where a reader renders U+0001. The relocation onto `<p>&#1;1.63</p>` was accepted in exploration (not in the probe file). This is an invisible glued control character, and I treat it as inside the limit.
- **m3 (code read, not probed).** `_parse_year` (`pg_envelope.py:760-762`) returns only the first `20\d{2}`. A header value naming two years (`2026/2025`) adds one year to `_header_years`, so "a year header needs its year alone" (R156) is not enforced inside a single header value. The effect is untested; see GAPS.

## Earlier findings: closure
- **P1–P4 and M1–M3.** Closed on their original constructions and on the seat's widened variants. The frozen R4 suite passes 140/140 on 3.12 and on 3.14.
  - M2 is closed for `<!-- ... -->`, but B1 reopens its class through the other comment forms.
  - M3 is closed for own-row unit cells, but B2 reopens it through rowspan.
- **Dead start guard (R154, `:988`).** Replaced by the mirror of the end check. Code read confirms it fires only when the preceding decoded character shares the literal's first unit.
- **The nine vocabulary tokens (R160).** Removed. The diff shows exactly the nine deletions, and the R160 census case passes.
- **The R4 OBSERVE limit case** (relocation onto the printed highlights `1.63`) is still accepted, inside R155's limit.

## Family coverage (probes run / failed)
| family | run | failed | note |
|---|---|---|---|
| R158 comment grammar (B1) | 7 | 7 | B1 |
| R159 neighbours (B2 plus an own-row control) | 2 | 1 | B2; the own-row control is unlocated, which is correct |
| R155 relocations (B3 plus OBSERVE) | 8 | 3 | B3; the 4 in-limit forms are recorded; `&#1;` was exploration only |
| Frozen five suites × 2 interpreters | 476 × 2 | 0 | |
| Earlier probe files r1 / r2 | 103 / 68 | 4 / 1 | unchanged from round 4: r1 has 3 named artefacts plus the f10 control (original reading), and r2 has B11 (superseded by R139) |

Families 2, 3, 5, 6, 7, 8, 9 (beyond B1), 10, 11 and the family-14 mutation matrix were not executed this round (see GAPS).

## Family 14 (code read only)
- **(vi) R162's defence-in-depth argument holds by code read.**
  - `html.unescape` never turns whitespace into non-whitespace and never removes a raw `<`.
  - `_literal` rejects whitespace, and its grammar has no `<`.
  - So any span that the raw-literal check or the decodes-to-whitespace check refuses also fails the value check.
  - The one exception is invalid code points that `unescape` drops. They are neither whitespace nor `<`, so the conclusion is unaffected.
- The seat's mutation matrix was not re-run.

## EVIDENCE
- **Head and tree.** `git rev-parse HEAD` returned a1220205b09894acf1e628677db7a125506cfabf, and `git status --porcelain` was empty.
- **Frozen files unchanged by the repair.** `git diff --stat 6a51a60e7cc d678c8a4671 -- tests/ research/ .github/` is empty.
- **The R162 amendment.** `git diff -U0 d678c8a4671 a1220205b09` touches only `SEAT_RULING_T1_ENVELOPE_R4_2026-09-25.md` and `tests/test_pg_envelope_f1_probes_r4.py`. It removes only the ruling's title line and five docstring lines.
- **Commit log.** `git log 6a51a60e7cc..a1220205b09` lists fefc133e606 (R154), d35fabde65a (R155, `economic_observations.py`), 585e001e8f3 (R157), 5125b3ef99d (R156), 03faf4c2383 (R158), 17c6f886481 (R159) and d678c8a4671 (R160). Each touches only its engine file. They are followed by a1220205b09, which touches the suite and the ruling only.
- **Frozen suites** (`-p no:cacheprovider`), on both `venv312_min` and 3.14:
  - F1: 46 passed;
  - R1: 125 passed;
  - R2: 70 passed;
  - R3: 95 passed;
  - R4: 140 passed.
- **Earlier probe files at head (3.14).**
  - R1: 4 failed, 99 passed. The failures are `f4[2.0 pts]`, `f4[— per share]`, `f7_drivers_title_date_removed` and `f10_control_q4...`, the same set as round 4.
  - R2: 1 failed, 67 passed. The failure is B11.
- **Hosted CI at a1220205b09.**
  - Check-runs total 10. fences, fence-pack, ci-authority, ci-authority/main, capability-broker, self-mod-fence and grader-manifest succeeded. `ci-authority/codex/merge-queue-pilot` failed, which is known and non-binding.
  - `ci` run 36165188013 is pending. There is no `ci-pack-*` check, no `ci-gate`, and no conclusion for the pack that carries earnings-economic-dossier.
  - The `ci` run at 2a8d1eb1a9c (36152784715) is still `in_progress` and may be holding the PR concurrency group. I observed this and did not act on it.
- **Originals census.** Q1–Q3 each hold comments only at offsets 140 and 178, the Wdesk and copyright comments in `<head>`.

## GAPS
- **Runs started but not concluded when I stopped at the coordinator's cutoff.** Their logs keep landing in `audit_t1_envelope_r5/`:
  - the gate run line on 3.12 (97% at last read) and on 3.14;
  - `test_ci_pack.py -k curated_exclusive`;
  - the a5a and capital-structure diff against `f8e4af5aa4c` (`a5a_cs.diff`);
  - the round-3 and round-4 earlier probe files. At last read the R4 file showed 8 F in the `long_named_ref_33` region, consistent with the recorded artefacts.
- **Hosted CI:** no `ci-pack-*` or `ci-gate` conclusion at the head.
- **Not executed this round:**
  - family 2 (the Q1/Q2 sweep);
  - families 3, 5 (determinism), 6, 7, 8 (including the R156 multi-year header, m3), 9 (duration relabels, stray `</table>`) and 10 (tamper sweep over present, unlocated and conflict rows);
  - family 11's full pinned-cell fuzz and differential;
  - family 13's full code review;
  - family 14 (i)'s mutation matrix;
  - comments in the other pinned tables.
- `_structure`'s lru_cache is a pure function of `source`. I reviewed it by reading the code only.

## DEVIATIONS
- The coordinator capped the audit at six probe turns and ordered the report written, so the commission's family floor is not met. The absence of further findings carries only the bounds above.
- `h.py` in `x/` is an exploration helper. The probe file is self-contained.

## Addendum: the earlier probe files concluded after the report was written (3.14, at head)
- **Round 3: 4 failed, 220 passed, 1 skipped (719 s).** Every failure is accounted for, and the set is identical to round 4:
  - `n4[Q3-DIL-0-1.63%-second:1.64]` is a conflict, which R152 sanctions;
  - three `span_display_none` cases are artefacts under R151.
- **Round 4: 13 failed, 1092 passed, 27 skipped (571 s).** The set is identical to the seat's run at d678c8a4671:
  - eight `long_named_ref_33` cases and three title-fuzz cases are the recorded artefacts, lawful `unknown_table` refusals;
  - `test_f14_OBSERVE_same_value_relocation_accepted_limit` records R155's accepted limit;
  - `test_f14_r153_case_fails_exactly_without_the_inline_unit_rule` fails because R155 now refuses R153's commented R3 target first. With the R153 rule removed, all 95 R3 cases pass.
    - R162's first three witnesses answer this sufficiently: each fails when R153 is removed, by the seat's matrix, which I did not re-run.
- No outcome changed without an account. The gate, `curated_exclusive` and the a5a/capital-structure runs remain in GAPS.

## Addendum 2: the gate, curated and a5a/capital-structure runs concluded (at head)
- gate 3.12: 1300 passed, 174 skipped, 80 warnings in 189.10s (0:03:09)
- gate 3.14: 1300 passed, 174 skipped, 80 warnings in 177.88s (0:02:57)
- curated_exclusive: 2 passed, 119 deselected, 80 warnings in 212.67s (0:03:32)
- a5a + capital-structure (3.12 with pandas and jsonschema): 213 passed, 80 warnings in 36.84s; per-test diff against f8e4af5aa4c: diff rc=0 
