# Seat ruling — T1 envelope, audit round 6 (R168–R178)

Adjudicator: the CDV-1 Meta-CEO seat (session 251f88c8, running Opus 5.5 under the fable-mode doctrine).

Source: the independent Opus re-audit of the round-5 repair at `135a67a3e12` (PR #7905). The audit was READ_ONLY. It ran as four independent groups, and all four returned **REJECT**. The report is committed beside this record as `OPUS_T1_ENVELOPE_AUDIT_R6_2026-09-25.md`, with each group's report verbatim.
- The findings:
  - nine blockers: G1-B1–B3, G2-B1–B2, G3-B1–B3 and G4-B1;
  - one major, G1-M1;
  - minors G1-m1, G1-m2, G2-m1, G4-m1 and G4-m2; nits G4-n1; observations G3-O1–O3.
- The seat found two more blockers of its own:
  - S1, text decoded twice, in its read of the decoding path while grounding G1-B2 (R175);
  - S2, characters Python 3.12 and 3.14 read differently, in its check that the repair reads alike on both interpreters (R178).
- The seat re-ran each group's probe file at `135a67a3e12` and with the repair. G1 runs on Python 3.14 with html5lib 1.1, the others on 3.12 with only pytest and pyyaml.

  | group | cases | at `135a67a3e12` | with the repair |
  |---|---|---|---|
  | G1 | 5,883 | 303 failed, 5,580 passed | 122 failed, 5,761 passed; each accounted for below |
  | G2 | 18 | 18 failed | 11 failed, 7 passed; the 11 are G2-B1's relocations, accepted by ruling (R176) |
  | G3 | 157 | 41 failed, 107 passed, 9 skipped | 148 passed, 9 skipped |
  | G4 | 14 (i1–i5 read the audited worktree's git state and do not run on a copy) | 5 failed, 9 passed | 14 passed |

  - G1's 122 failures with the repair all fail at `135a67a3e12` too. None is a present fact:
    - 114 place a `<table>` or `</table>` tag inside a `--!>` or unterminated comment. Each document is refused `unknown_table` before R163 runs, and the probe expects the detail `comment`. G1's report calls these its own exact-detail expectation, not a finding.
    - `b1_variant[Q3-segment_cell]` is refused `unknown_table:t11` before R163 runs, as G1's report says.
    - `b1_variant[Q2-title_cell]` never builds its document. The probe finds no cell holding "Ended" in the earnings table's first three rows and raises `StopIteration`, at `135a67a3e12` and with the repair. G1's report says the case is refused `unknown_table:t4`, but the probe never reaches the engine.
    - Six are the label cases of `test_g1_B1_tbody_end_tag_in_a_cell_refuses_the_document`. The probe first requires the reader to diverge on a document the engine admits. R171 refuses the document at admission, so that precondition cannot hold. R6's frozen `</tbody>` cases pin the refusal: `markup_unreadable:table`, no present fact, and the workspace validates.
    - R178 changes none of the 5,883 outcomes. The failure set is identical with and without it.

- The audit confirmed the positive work:
  - round 5's B1 and B3 are closed on their constructions and on every variant, and B2, m1, m2 and m3 on their own constructions;
  - R167's witness table reproduces exactly, row for row, and R163 made no R143–R162 rule unreachable;
  - the span double reading shows 0 divergences between the engine, R163 and html5lib 1.1 in 40,000 seeded attribute strings;
  - the repair adds no `try`, `raise`, per-release literal or probe-specific branch, and no path to `extract` skips R163;
  - the six frozen suites pass on 3.12 and 3.14 (537), the gate line gives 1361 passed and 174 skipped, `curated_exclusive` passes, and the a5a and capital-structure suites match the `f8e4af5aa4c` baseline test by test (213 passed).
- Hosted CI at `135a67a3e12` concluded after the audit's read: every binding check passed and `ci-gate` reported. The only red is `ci-authority/codex/merge-queue-pilot`, which is non-binding.

This record amends R116–R167 only where it says so. Everything else there stands.
- One frozen file changes: `headers_over` in `tests/test_pg_envelope_f1.py`, the independent oracle of which headers stand over a cell, moves with R168. Nothing else in that file changes.
- The `_r1` to `_r5` suites and `tests/fixtures/pg_envelope/` stay byte-identical.
- The rulings below are enforced by the new frozen suite `tests/test_pg_envelope_f1_probes_r6.py` (R177).
- The seat grounded every factual premise below in its own runs on the six originals, in memory with the engine's reader. No finding is ruled on the audit's word alone.

## Severity

The bars are the commission's review standard: (a) wrong bind, (b) present fact outside F1-Q, (c) validator acceptance of a tampered workspace, (d) integrity, and (e) positional or literal admission.

| finding | audit | seat | ruling |
|---|---|---|---|
| G3-B1, a value spanning two year columns binds the year of its first column | BLOCKER (e, a) | BLOCKER; the label side of the same rule too | R168 |
| G3-B2, a forbidden unit cell carrying an invisible format character is not read | BLOCKER (a) | BLOCKER; fullwidth and small lookalikes read with it | R169 |
| G3-B3, a header naming a second year in another form adds no year | BLOCKER (e) | BLOCKER | R170 |
| G1-B1, R163 admits `</tbody>` inside a cell | BLOCKER (b; a on the reader's grid) | BLOCKER | R171 |
| G1-B3, R163 admits `<isindex>` | BLOCKER (b), reader-defined | BLOCKER | R171 |
| G1-B2, a reference that `html.unescape` drops sits beside a bound literal | BLOCKER (b) | BLOCKER | R172 |
| G1-m2, `&#11;` | minor, in G1-B2's class | in G1-B2's class | R172 |
| G1-m1, a literal NUL in cell text | minor, fail-closed | minor, fail-closed | R172 |
| G1-M1, the prior-year note is read from text a reader never prints | MAJOR | MAJOR; repaired | R173 |
| G4-B1, a relocation onto a literal glued to printed text through markup is accepted | BLOCKER (c) | BLOCKER; repaired in code, and the limit is not widened | R174 |
| S1 (seat), a cell's text is decoded a second time | — | BLOCKER (e) | R175 |
| S2 (seat), the same bytes read differently on Python 3.12 and 3.14 | — | BLOCKER (a); on 3.12, which the gate job declares, it is G3-B3's wrong bind | R178 |
| G2-B1, relocations the R166 list does not name are accepted | BLOCKER (c) by the letter | the list is restated as the rule it summarises; the check is unchanged | R176 |
| G2-B2, tampered rows make the validator raise `TypeError` | BLOCKER (d) | BLOCKER | R176 |
| G2-m1, JSON normalisation erases the int/float distinction | minor (c) | minor; repaired | R176 |
| G4-m1, the seat's account of the round-5 probe file at `135a67a3e12` | minor (testimony) | accepted; corrected here | R177 |
| G4-m2, twelve R163 branches have no isolating witness | minor | accepted; nine isolated, and three named as defence in depth | R177 |
| G4-n1; G3-O1–O3 | nit; observations | disposed of below | R177 |

- **Three blockers are one rule: a pin's reading holds over every grid position a value occupies, and over every form in which a header names a year.**
  - G3-B1 is R147's "two years over the cell" reached through a span instead of a banner.
  - The seat read the label side of the same geometry. A value spanning into a row whose label is `Basic`, or into an unlabelled row, bound at `135a67a3e12`, because R145 read the label of the value's first row only.
  - G3-B3 is R165's rule through a year the engine did not read as one: `2025/26`, `'26`, `20252026`, or digits that are not ASCII.
- **Five blockers and the major are one class: the engine read text or markup that a reader reads another way.** This is G1-B1, G1-B2, G1-B3, G3-B2, G1-M1 and S1. Each repair refuses the document or leaves the metric unlocated. None models the reader's reading, so every repair moves toward refusal.
- **S2 is R169's and R170's readings taken from the interpreter's own Unicode version.** R178 does not model any one version. It fixes the characters the envelope admits to Unicode 3.2, and reads every letter that a later version might call a numeral as a possible one, so it too moves toward refusal.
- **G4-B1 is repaired in code.** It is round 5's B3 through markup instead of a text bracket. The audit offered two repairs: (a) reach through the markup in the validator, or (b) add the form to R166's list. R174 takes (a), because (b) accepts a value a reader prints as part of a longer token, and R114 forbids relaxing the validator.
- **G2-B1 is a finding against R166's prose, not against the check.**
  - The eleven relocations are whole tokens of text the engine reads, outside the tables: the wrapper header, prose, text after `</html>`, and seven raw-text elements. R155's check never claimed placement. Replay's deep equality (R143) pins placement, and the seam replaces exactly that receipt.
  - The alternative the seat rejected is a cell-containment check in the validator. It would need a second table reading there: either not independent of the extractor's, or a second grammar that must track R163's. A relocation from one cell to another would still pass it.
  - Family 11 bears this out: in 8,172 fuzz documents no extractor span left its cell.
  - R114 is kept, because the validator is neither relaxed nor changed for these cases. R176 restates the limit as a rule and freezes the eleven cases as accepted.
- **G2-B2 is integrity (d).** A validator that raises `TypeError` on a tampered row has not refused it.
- **The fullwidth and small `$` and `%` (G3-B2's non-blocking sub-case) are read as the characters they stand for (R169).** They bound at `135a67a3e12` and are unlocated with the repair.
- **G1's coverage note is accepted as the cost of a finite envelope.** R163 refused 1,875 single-construct fuzz documents whose pinned cells a reader reads unchanged. The P&G originals use none of those constructs, and the envelope is P&G only.

## Rulings

- **R168 (G3-B1; amends R145, R147, R156 and R165). A value locates only when every grid position it occupies reads the pin alike.**
  - **Header.** Each column the value's cell occupies is read alone, as a one-column view of the cell. The cell is a hit only when every view reads under the pin:
    - the pin's header stands over that column;
    - when the pin names a year, the years over that column are exactly that year (R156, R165);
    - that column's period title matches (R147).
  - **Label.** The cell's row label must be the pin's label in every grid row the cell occupies, that is, its own row and every row its rowspan reaches.
  - **The witnesses.**
    - `1.63` widened over the `2026` and `2025` columns (Q3 highlights DIL, primary and second statements) leaves DIL unlocated;
    - the same widening leaves Q3 highlights CORE, Q1 earnings DIL and Q2 CORE unlocated;
    - DIL spanning into a row labelled `Basic`, or into an unlabelled row, leaves DIL unlocated.
  - **The controls.** A value spanning two columns of its own year binds, and so does a value spanning two rows that both print its label.
  - **The oracle.** `headers_over` in `tests/test_pg_envelope_f1.py` is the independent model through which the round-1 geometry test computes its expectations. It now yields the headers standing over every column the cell occupies. Two round-1 expectations move with it:
    - **`highlights_2026_colspan_plus1`.** At `135a67a3e12`, the prior-year cell's first column read a second `2026`. So DIL was unlocated, and PDIL, CORE and PCORE conflicted. With the repair, DIL binds 1.63, which sits wholly under `2026`, and the cells straddling the two years are unlocated.
    - **`segdrivers_price_colspan_plus1`.** Price binds 1.0. Reported, organic, volume, mix and other, whose cells straddle the widened header, are unlocated.
    - The two sides move together. With only the new oracle the two cases fail, with only the repaired engine they fail, and with both they pass.
  - **Verified on the originals.** On each F1-Q exhibit, 34 pinned cells occupy more than one column and none spans rows. Every one reads under its pin in each column it occupies. Admission and the built workspace are byte-identical at `135a67a3e12` and with the repair, on all six originals (the workspace's sha256).

- **R169 (G3-B2; amends R159 and R164). A unit cell is read as a reader sees it.**
  - A neighbour's text is normalised with NFKC, then keeps only printable ASCII and the em dash, then is stripped. The unit test and the printed test (R159, R164) both read that text.
  - A cell holding only characters a reader does not see is not printed. So it cannot shield the unit cell beyond it.
  - **The witnesses.**
    - `$&#8203;`, `&#8203;$`, `$&#65279;` and `$&#173;` beside a percent value leave it unlocated. There are twelve cases across the segment drivers, the drivers and the organic reconciliation of Q1–Q3.
    - A cell holding only `&#8203;` between a percent value and a `$` leaves the value unlocated, in all three quarters.
  - **The controls.** The same four forms with `%` beside a percent value bind, in the twelve positions.
  - **Also read.** Fullwidth `＄`/`％` and small `﹩`/`﹪` normalise to `$` and `%`. A character outside R159's grammar that NFKC leaves alone, such as `€` or `£`, reads as empty. (`💲` is refused at admission since R178.) The nearest printed cell beyond it is then read, which only adds constraints.
  - **Verified on the originals.** On the three F1-Q exhibits every cell reads the same before and after. On the other three, only cells holding a typographic apostrophe change, and none of them is a unit cell either way.

- **R170 (G3-B3; amends R147, R156 and R165). A header's years are ASCII `20dd` or a parsed period title. Any other figure makes them unreadable.**
  - Each header value over the view that holds a numeric character is read in turn:
    - **a parsed period title** adds its year;
    - **a single figure** (digits with thousands separators and a decimal part, optionally in parentheses, with `$` or `%`) adds nothing;
    - **any other value** still holding a numeric character, once each ASCII `20dd` not bounded by digits and each footnote marker `(d)` is removed, makes the years unreadable;
    - **otherwise** the value adds each ASCII `20dd`.
  - Unreadable years fail every year check and every period check, so the value does not locate.
  - **Widened by R178.** A numeric character here is one Python calls numeric, or any character Unicode 3.2 files as an other letter.
  - **The witnesses.** A banner over the highlights, in any of seven forms, leaves PDIL and PCORE unlocated on Q1–Q3 (21 cases). The forms are `2025/26`, `2025-26`, `2025&#8211;26`, `20252026`, Arabic-Indic `٢٠٢٦`, fullwidth `２０２６` and `'26`.
  - **The controls.** `2025 (1)`, `2025(1)` and `(1) 2025` name 2025 and bind.
  - **Verified on the originals.** The years become unreadable over 50, 113 and 112 cells of Q1–Q3. Each has a figure over it, such as a cash-flow amount or a `Q3` label. None of them is a cell any pin binds, and the built workspace is byte-identical.

- **R171 (G1-B1, G1-B3; amends R163). A cell closes only on its own end tag, and `isindex` is unread.**
  - Inside a cell, an end tag named in the table grammar or in the unread elements, other than the cell's own, refuses the document as `markup_unreadable:table`. A reader closes the cell there, or reads the section the engine does not model.
  - `isindex` joins the unread elements (`markup_unreadable:element`). The commission's reader, html5lib 1.1, expands it into printed text.
  - **The witnesses.** `</tbody>` or `</TBODY >` in a pinned label or value cell refuses the document: eight cases across Q1–Q3, DIL, PDIL, CORE, SALES, ORG and BEAUTY. `<isindex>` in a pinned cell refuses it in three.
  - **Verified on the originals.** None of the six uses `isindex`, and no cell holds such an end tag. Admission is unchanged.

- **R172 (G1-B2, G1-m1, G1-m2; amends R143, R163 and R166). Cell text holds only characters a reader prints as layout or text.**
  - A cell that holds either of the following is refused as `markup_unreadable:character`:
    - a character reference that `html.unescape` decodes to nothing;
    - a decoded character that is a control character (other than tab, LF, CR and FF) or whitespace that HTML does not treat as whitespace.
  - **The witnesses.** Six cases: `&#xFFFF;` before Q3 DIL, `&#127;` after it, `&#1;` before Q2 CORE, `&#xFDD0;` before Q1 BEAUTY, `&#x8;` after Q3 SALES, and `&#11;` before Q3 DIL (G1-m2).
  - **The controls.** `&#160;`, a raw no-break space, and `&#32;` followed by a tab before a pinned literal bind.
  - **G1-m1.** A literal NUL in a value cell is now refused as `character`. In a label cell the table is refused first, as `unknown_table`, because the label leaves the vocabulary and R163 runs last. Both are fail-closed.
  - **R166 corrected.** Its m2 bullet no longer describes an admitted document. `&#1;` beside a pinned literal is refused at admission.
  - **Verified on the originals.** No cell of the six holds such a reference or character, and admission is unchanged. The originals' references are `&#160;`, `&#8212;`, `&#38;`, `&#8217;` and other printable ones.

- **R173 (G1-M1; amends R157). The prior-year note is read from printed text.**
  - The text between the core reconciliation and the next table is read with the content of every raw-text element blanked, from its start tag to its end tag.
  - A note that exists only inside `script`, `style`, `title` or another raw-text element no longer gates PCORE's second statement. Reading the note from none of them can only leave PCORE unlocated.
  - **The witnesses.** The note moved into `<script>`, `<style>` or `<title>` leaves PCORE unlocated on Q3.
  - **The control.** The note in a paragraph binds PCORE 1.54.
  - **Verified on the originals.** Each note sits in printed prose, and the workspace is unchanged.

- **R174 (G4-B1; amends R155 and R166). The span check reads through markup the way a reader prints.**
  - The validator reads the source as units: comments, markup, separators (`td`, `th`, `tr`, `table`, `p`, `div` and `br` tags), text, and the content of raw-text elements.
  - A present row's span must be a whole printed token:
    - **inside a text unit,** or inside one raw-text unit of a kind a reader may print, the nearest printed character on each side is whitespace, a separator or the source's edge. Comments, other markup, and script or style content are skipped in that search. A printed raw-text neighbour glued to the span refuses it;
    - **wholly inside one comment, or one script or style unit,** the span passes. That is R166's limit, unchanged.
  - Otherwise the validator refuses: "present envelope observation span is not a whole printed token."
  - **The witnesses.** Five relocations through R143's seam are refused: `<p>9<b></b>1.63</p>`, `<p>-<b></b>1.63</p>` (a reader prints `-1.63`), `<p>9<!-- c -->1.63</p>`, `<p>1.63<b>9</b></p>` and `<p>2<i></i>1.63</p>`.
  - **The controls.** Four relocations onto a literal that markup separates are accepted, `<p>9</p><p>1.63</p>` among them.
  - **Verified on the originals.** Every receipt the extractor builds on the three F1-Q exhibits passes, and the frozen suites validate each one.

- **R175 (S1; amends R143 and R158). Text is decoded exactly once.**
  - `_units` decodes each reference in a cell's text once. `_norm` no longer applies `html.unescape` again. The period-title parser no longer rewrites a literal `&#160;` or `<br/>` in decoded text.
  - At `135a67a3e12`, a cell whose source is `&amp;#160;`, which a reader prints as `&#160;`, was read as a no-break space. A label or title a reader prints differently therefore still matched the pin's vocabulary.
  - **The witnesses.** The earnings table's diluted label, and its period title, printing `&#160;` as text leave the earnings table unknown (`unknown_table:t4`).
  - **The control.** A `&#160;` the source holds is decoded once and binds.
  - **The title hunk is defence in depth.** Through the black box the signature check refuses first. The seat measured it white-box:
    - with only the `_norm` hunk reverted, the title attack leaves three metrics `envelope_unlocated` and binds none;
    - with only the title hunk reverted, the attack still ends at `unknown_table:t4`.
  - **Verified on the originals.** No cell's decoded text changes under a second decode, and none holds a literal `&#160;` or `<br/>`. Admission and the workspace are unchanged.

- **R176 (G2-B1, G2-B2, G2-m1; restates R155 and R166's limit as a rule; amends R134 and R143).**
  - **The limit, as a rule.**
    - The span check proves only that the span is a whole token of the text the engine reads (R174's units), and that the token parses to the value. It proves neither that a reader shows that text nor where the text sits.
    - Placement is replay's job (R143). Through the seam, which replaces replay's receipt, a relocation onto such a token outside the tables is accepted, before and after R168–R175.
    - Eleven frozen cases pin the rule, each one accepted: the wrapper's description header; a prose paragraph; bare text before `</text>`; text after `</html>`; and `title`, `textarea`, `xmp`, `iframe`, `noscript`, `noembed` and `noframes` outside the tables.
  - **Refused, never raised (G2-B2).** A tampered row holding a value JSON cannot carry is refused with the validator's own error:
    - on the absence path, as the path already refuses a malformed value;
    - on the replay path, as "selected observation is not JSON data."
    - The witnesses are `missing_fields` = 5, `reason` = `{}`, `detail` = `Decimal("1")` and `rights_profile` = `{1}`.
  - **Rows compare as serialised JSON (G2-m1).** A present row is compared with its replay as sorted-key JSON text. An int where replay holds a float, or the reverse, is refused, in three witnesses.
    - **The control.** A list held as a tuple serialises identically and validates.
  - **Verified.** G2's family 10 re-run with the repair: 26,655 tampers over Q1–Q3, two mutations and a refused body. None raised. 82 were accepted, and each changes nothing JSON can see:
    - 28 hold a list as a tuple;
    - 54 set to null a field that is already null.

- **R177 (the round-6 freeze, the gate, the repair, the witness, the dispositions and the hold).**
  - **The freeze.** `tests/test_pg_envelope_f1_probes_r6.py` holds 163 cases, all authored by the seat from the audit's findings, the seat's widened constructions and its own finding S2.
    - At `135a67a3e12`, with the oracle already moved by R168, the seven suites give 105 failed and 595 passed on Python 3.12, with only pytest and pyyaml installed. Python 3.14 gives the same split.
    - The 105 are the 103 R6 witnesses, each failing for its finding's reason, and the two round-1 geometry cases whose expectation moved with the oracle.
    - The 60 R6 passes at `135a67a3e12` are:
      - the 32 controls, five of them R178's;
      - the eleven R176 relocations inside the restated rule;
      - the 17 R177 witnesses of R163's existing branches and order.
  - **The gate.** The `earnings-economic-dossier` job in `.github/ci/legacy-jobs.yml` adds the suite to its paths and its run line. The suite adds about a minute, within the 12-minute timeout. With the repair, the gate line gives 1524 passed and 174 skipped: round 5's 1361, plus the 163.
  - **The repair.** The rulings fix the code to the line, so the seat writes it itself, one commit per ruling.
    - R168–R173, R175 and R178 touch `engine/company_intelligence/pg_envelope.py`. R174 and R176 touch the validator, `engine/company_intelligence/economic_observations.py`.
    - With the repair, all seven envelope suites pass on 3.12 and 3.14 (700 cases).
    - Everything else must hold:
      - every other frozen file stays byte-identical;
      - the gate line and `curated_exclusive` pass;
      - the a5a and capital-structure suites match the baseline test by test.
  - **The witness.** Each ruling is load-bearing in the frozen suite. The seat reverted one ruling at a time in scratch copies, never in the worktree, and ran the R6 suite on 3.12 and 3.14. With nothing reverted, all 163 cases pass on both.

    | reverted | R6 cases failed |
    |---|---|
    | R168 | 7 |
    | R169 | 15 |
    | R170 | 21; 30 with R178's figure test, which rewrites R170's lines and is reverted with them |
    | R171 | 11 |
    | R172 | 6 |
    | R173 | 3 |
    | R174 | 5 |
    | R175 | 2 |
    | R176 | 7 |
    | R178 | 26 on 3.12; 20 on 3.14 |

    - The sets are disjoint, except that R170's run also reverts R178's figure test and so fails its nine figure witnesses. Together they are the 103 witnesses that fail at `135a67a3e12`, on both interpreters.
    - On 3.14, R178's set lacks the six 两 and 京 banners, because Python 3.14 already calls both numeric. Those six fail there only in R170's run, so the union is the same 103.
    - Every set is the same on both interpreters except R178's, and R178 is the ruling that makes them agree.
    - Hunk by hunk, over all seven suites:

      | hunk reverted | R6 cases failed | earlier cases failed |
      |---|---|---|
      | R168 label | 2 | 0 |
      | R168 header | 5 | 2 (the round-1 geometry pair) |
      | R171 cell end tags | 8 | 0 |
      | R171 `isindex` | 3 | 0 |
      | R175 `_norm` | 2 | 0 |
      | R175 title | 0 | 0; defence in depth, measured white-box above |
      | R176 absence path | 2 | 0 |
      | R176 replay path | 5 | 0 |
      | R178 admission check | 17 | 0 |
      | R178 figure test | 9 on 3.12; 3 on 3.14 (the 財 banners) | 0 |

  - **G4-m2: one witness per R163 branch.** Ten R6 cases each isolate a branch that round 5 left unwitnessed. The seat removed each branch alone, in memory, at the final text, and ran 25 cases: the isolation and order witnesses, R178's order witnesses, and round 5's two span cases. On Python 3.12 and on 3.14, each removal fails exactly its own case:
    - an unclosed raw-text element;
    - a start tag between rows;
    - a start tag in a row;
    - an end tag between rows;
    - an end tag in a row;
    - a row end inside a cell;
    - a table unclosed at the end;
    - a rowspan over the limit;
    - a span repeated alike;
    - a span the engine reads from another attribute.
  - **The three span checks shadow each other.** Removed alone, none fails a case. Removed in pairs, each pair fails its witnesses:
    - the engine-agreement check with the other-attribute check fails the last isolation case;
    - the engine-only check with the other-attribute check fails round 5's `span_named_in_another_attribute` and `span_suffix_of_another_name`.
    - The engine-agreement and engine-only checks are therefore defence in depth while the other-attribute check holds, as G4-n1 says. They are named here as R162 named its own.
  - **Order.** Seven cases pin R163 after every earlier admission check. Each adds `<p>9>1.63</p>` to a frozen refusal case, which must keep its own refusal: `type_ex_99_2` (`not_ex_99_1`), `generator_removed` (`generator_not_workiva`), `masthead_other_issuer` (`issuer_not_pg`), `table_injected` (`unknown_table`), `drivers_removed` (`required_table_missing`), `drivers_repeated` (`required_table_repeated`) and `q3_under_q2_scope` (`quarter_mismatch`). Moving the check first fails all seven, and R178's `text_gt` order witness with them, on both interpreters. R178's own place is pinned under R178.
  - **G4-m1, corrected.** At `135a67a3e12`, round 5's four failing probe cases are three B3 relocations and the OBSERVE case `attribute_gt_lt`. All four fail with `KeyError`, because the body is now refused at admission. The seat's round-5 account called all four OBSERVE cases. The outcome is the stronger one.
  - **G4-n1.**
    - `_START_TAG` re-spelling `_ATTRIBUTE`'s grammar, and the mutable `_SPAN_LIMITS`, are not wrong today. They are left for a refactor that changes no behaviour.
    - `_header_years` reads years from ASCII digits only (R170). Any other numeral, or any character Unicode 3.2 files as an other letter, makes them unreadable (R178).
    - `_parse_year` still reads Unicode digits, but it reads only the pin's own header, which the engine writes in ASCII. A document header in other digits never equals that header under `_norm`. Its `\d` reads alike on both interpreters over every character R178 admits.
  - **G3-O1** (banners naming only the period year in another form leave pins unlocated or change the signature) is fail-closed, and a coverage cost.
  - **G3-O2** (non-`pg_` typed absences are not validated) is unchanged from `f8e4af5aa4c`. The validator checks only `pg_` rows there and here, so bar (d)'s non-`pg_` clause holds.
  - **G3-O3** is fail-closed and needs nothing.
  - **The R7 audit.** An independent Opus READ_ONLY audit then attacks the repair. Its floor adds:
    - R168–R176, each attacked in both directions: what each admits that a reader reads another way, and what each refuses on a legitimate layout;
    - the family-9 F2-A transplant and the second-statement tables, which round 6 left partial;
    - Cf characters and unit glyphs outside NFKC's reach, such as `€` and `£`;
    - a year over a rowspan whose cells start in different rows, and `_period_titles`' whole-table fallback;
    - G4-B1's class on other quarters and metrics, and inside the tables;
    - the restated R176 rule, and R173 and R174's readings of raw text;
    - dropped references and odd characters outside cells;
    - both interpreters;
    - R178 on both interpreters, and against a later Unicode, which the seat's verification does not cover;
    - Unicode case folding and Unicode whitespace in the engine's `re.I` HTML patterns. The seat tried raw-text end tags spelt with `ſ`, `İ` or `ı`, a `colſpan` attribute, and cell end tags holding U+2003, U+001C or U+0085, and R163's ASCII grammar refused each one;
    - hosted CI observed concluded on the repair head.
  - **Hold.** #7905 stays Draft/HOLD under Sol's direction (comment 5825632041, R114).

- **R178 (S2; amends R116's admission order, R169 and R170). The envelope reads its characters alike on Python 3.12 and 3.14.**
  - **The finding.** Each reader of a character that the envelope uses, such as NFKC, `isnumeric` or `\d`, answers from the interpreter's own Unicode database. Python 3.12 ships Unicode 15.0 and 3.14 ships 16.0, and the same bytes read differently:
    - a banner printing 2026 in Sunuwar digits (U+11BF0–U+11BF9) or outlined digits (U+1CCF0–U+1CCF9), both new in 16.0, left the prior-year pins under it bound on 3.12 and unlocated on 3.14. The gate job declares Python 3.12, and there it is G3-B3's wrong bind;
    - a cell printing only U+1CCF0, between the reported-sales-growth value and a `$`, left the value unlocated on 3.12 and bound on 3.14;
    - a banner printing 两 or 京, which 16.0 gives numeric values, left the six earnings-per-share pins under it unlocated on 3.14 and bound on 3.12.
  - **The rule.**
    - **Admission.** A document holding a character that Unicode 3.2 does not assign, raw or through a reference, is refused as `markup_unreadable:character`. The test reads `unicodedata.ucd_3_2_0`, the fixed Unicode 3.2 table that every Python version ships.
    - **Its place.** It runs after the filing-type and generator checks, which match an ASCII literal that no other character can change. It runs before the issuer, table, role, quarter and R163 checks, each of which reads printed text.
    - **The figure test (amends R170).** A character is a possible figure when Python calls it numeric, or when Unicode 3.2 files it as an other letter (`Lo`). A header value holding one names no year the envelope reads.
  - **Why this is enough on both interpreters.** For every code point Unicode 3.2 assigns, the seat compared the readers the envelope uses:
    - `isnumeric`, `isdigit`, `isdecimal`, `isspace`, `isalnum` and `isprintable`; `\d`, `\s` and `\w`; `casefold`, `lower` and `upper`; NFKC and NFC; and `re.I` matches of `k` and `s`.
    - They differ in two places only. `isnumeric` differs on ten ideographs that 16.0 gives numeric values: 两 京 俩 倆 拐 洞 皕 秭 鈎 钩. `upper` differs on two letters, ƛ and ɤ, and the envelope never calls it.
    - The figure test reads all ten alike. It also reads alike any other ideograph that a later Unicode gives a value.
    - `ucd_3_2_0.category` reads alike on both interpreters over every code point. Its numeric values do not (U+09F4 reads 0.0625 on 3.12 and 1.0 on 3.14), and R178 does not read them.
    - The verification covers Python 3.12 (Unicode 15.0) and 3.14 (16.0) only. A later Unicode is on the R7 floor.
  - **The witnesses (26).**
    - The U+1CCF0 cell, on Q1–Q3 (3).
    - The Sunuwar and outlined-digit banners, on Q1–Q3 (6).
    - U+1F4B2 HEAVY DOLLAR SIGN, as a reference or as the character, in a paragraph after the Q3 tables (2). Unicode 6.0 assigns it and both interpreters read it alike. At `135a67a3e12` the document bound every frozen value. It is refused because the envelope reads text outside the tables too, and Unicode 3.2 does not assign it.
    - A 两, 京 or 財 banner over the highlights, on Q1–Q3 (9). Exactly the six earnings-per-share pins are unlocated, every other value binds, and the workspace validates. 財 has no numeric value in either version, and its three cases pin the rule for the next ideograph a Unicode version gives one.
    - Six order witnesses. The frozen `masthead_other_issuer`, `table_injected`, `drivers_removed`, `drivers_repeated` and `q3_under_q2_scope` cases, and a paragraph printing a text `>` that R163 refuses, are each refused `character` once the U+1F4B2 paragraph is added.
  - **The controls (5).**
    - `&#8364; &#8482; € ™` in a paragraph binds.
    - A banner printing `é` or an em dash binds.
    - `type_ex_99_2` and `generator_removed` keep their own codes with the U+1F4B2 paragraph added.
  - **Hunk by hunk.**
    - With only the admission check reverted, 17 witnesses fail on both interpreters: the U+1CCF0 cells, the later-digit banners, the U+1F4B2 paragraphs and the six order witnesses.
    - With only the figure test reverted, the nine ideograph banners fail on 3.12. On 3.14 only the three 財 banners fail, because 3.14 already calls 两 and 京 numeric.
    - The two sets are disjoint.
  - **Order.** Moving the check first fails the two order controls. Moving it last fails the six order witnesses.
  - **R178 uses the `import unicodedata` that R169 adds.** The commit order keeps it in place.
  - **Verified on the originals.** No original holds a character that Unicode 3.2 does not assign or files as an other letter, raw or decoded, on either interpreter. On both interpreters, admission, the workspace's sha256 and the years over every printed cell are unchanged on all six. Before R178's cases were added, the seven suites made 1,139 admissions, and no document among them held a character Unicode 3.2 does not assign.
