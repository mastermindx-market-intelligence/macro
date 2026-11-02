# Seat ruling — T1 envelope, audit round 4 (R154–R162)

Adjudicator: the CDV-1 Meta-CEO seat (session 251f88c8, running Opus 5.5 under the fable-mode doctrine).

Source: the independent Opus re-audit of the round-3 work at `2a8d1eb1a9c` (PR #7905). The audit was READ_ONLY and its verdict was **REJECT**. The full report is committed beside this record as `OPUS_T1_ENVELOPE_AUDIT_R4_2026-09-25.md`.
- It ran 1133 probe cases. The findings:
  - four blockers, P1–P4;
  - three majors left to the seat's ruling, M1–M3;
  - code-review notes and four gaps.
- The seat re-ran every failing probe at `2a8d1eb1a9c`: 43 failed, each for the reason its finding names (4 × P1, 32 × P2, P3 × 2, P4, M1 × 2, M2, M3).
- The audit confirmed the positive work:
  - R152 is the minimal order that satisfies the round-0 witness.
  - The R153 case fails exactly when its rule is removed.
  - Outcomes are identical across hash seeds and locales.
  - The refused-document tamper sweep refuses every key on Q1–Q3, and the accession is source-derived.
  - 504 fuzz bodies raise no exception.
  - The four frozen suites are green on 3.12 and 3.14: 46, 125, 70 and 95 passed. The gate line gives 1160 passed and 174 skipped, `curated_exclusive` passes, and the a5a and capital-structure suites match the `f8e4af5aa4c` baseline test by test (213 passed).

This record amends R116–R153 only where it says so. Everything else there stands.
- `tests/test_pg_envelope_f1.py`, the `_r1`, `_r2` and `_r3` suites and `tests/fixtures/pg_envelope/` stay byte-identical.
- The rulings below are enforced by the new frozen suite `tests/test_pg_envelope_f1_probes_r4.py` (R161).
- The seat grounded every factual premise below in its own runs on the three F1-Q originals and the two F2-A originals, in memory with the engine's reader. No finding is ruled on the audit's word alone.

## Severity

The bars are the commission's review standard: (a) wrong bind, (b) present fact outside F1-Q, (c) validator acceptance of a tampered workspace, (d) integrity, and (e) positional or literal admission.

| finding | audit | seat | ruling |
|---|---|---|---|
| P1, a reference glued to the literal (`&nbsp1&#46;63`) enters the span | BLOCKER (a) | BLOCKER | R154 |
| P2, a span narrowed by one character through the seam is accepted (`7%`→`7`) | BLOCKER (c) | BLOCKER | R155 |
| P3, a period title's year overrides a contradicting year row; highlights skip the year check | BLOCKER (e) | BLOCKER | R156 |
| P4, a 400-digit figure binds `inf` | BLOCKER (a) | BLOCKER | R157 |
| M1, a seam relocation onto `1.63` inside a comment or an attribute value is accepted | MAJOR, seat to rule | **BLOCKER** (c) | R155 |
| M2, `</table>` inside a comment closes the table and hides a printed row | MAJOR, seat to rule | **BLOCKER** (a) | R158 |
| M3, a `%` unit cell beside a per-share value binds as usd_per_share | MAJOR, seat to rule | **BLOCKER** (a) | R159 |
| dead start guard in `_receipt` | minor | part of P1 | R154 |
| nine vocabulary tokens that no F1-Q original produces | non-blocking | required cleanup | R160 |

- **M1 is a blocker.** R153's recorded limit covers another printed literal of the same value and unit. It does not cover text that is not printed. The check accepted the relocation because it never tested that the span was a whole literal, and P2 has the same cause. One rule closes both.
- **M2 is a blocker.** A browser prints both Diluted rows. The engine saw one and bound 1.63, where R130 requires two candidate rows to leave the metric unlocated.
- **M3 is a blocker.** The bytes print a percent marker beside the value. Binding it as usd_per_share states a unit that the bytes contradict.
- **The vocabulary tokens are a required cleanup, not a blocker.** They widen admission, but every other check still gates. R148 already requires the vocabularies to be derived from the three originals.

## Rulings

- **R154 (P1; enforces R143). The start boundary is checked like the end boundary.**
  - `_receipt` compares the unit of the decoded character before the literal with the unit of the literal's first character. When they are one unit (`extents[first - 1][1] > extents[first][0]`), a span boundary falls inside a unit whose decoding extends past the literal, and the literal is unlocated.
  - That is the mirror of the existing end check, and it replaces the dead guard, which could never fire because two characters of one unit carry identical extents.
  - Under R143's grammar, `&nbsp1` is one unit, because a bare `&nbsp` absorbs the name characters after it. So on `>&nbsp1&#46;63` the primary statement's literal is unlocated, the metric is `envelope_unlocated`, and the workspace validates.
  - A reference that ends before the literal is still layout, and the literal binds. That covers `&nbsp;` ending at its semicolon, and a bare `&nbsp` ending where the literal's own `&#49;` begins.

- **R155 (P2, M1; amends R143's independent check). The span must be a whole literal.**
  - The validator's independent check gains one requirement. Take two stretches of the source:
    - from the last `>` before the span (or the source start) up to the span;
    - from the span's end up to the first `<` after it (or the source end).
  - `html.unescape` of each stretch must be empty or whitespace only, by `str.isspace`. Otherwise the validator refuses: "span is not a whole literal".
  - The check reads only the source around the span. It still never calls the receipt code, the tokenizer, the cell reader or the replay (R143).
  - It closes three constructions:
    - a span narrowed off a `%` or a sign, as in `7%` to `7` or `(1)%` to `(1)`, where a literal character is left beside it;
    - a relocation into a comment, glued or spaced, where the comment opener lies between the last `>` and the span;
    - a relocation into an attribute value, glued or spaced, where the tag's own text lies there.
  - The extractor's own spans pass it. Under R143, every unit between the literal and the markup around it decodes to whitespace, and `html.unescape` reads references with R143's grammar.
  - **The limit, restated (amends R153's).**
    - The check proves that the span is a whole literal of the row's value, in the row's unit, delimited by markup or whitespace. It cannot prove that the literal is the pinned cell, or that a reader sees it.
    - A seam shift onto another delimited literal of the same value and unit therefore passes. That literal may sit in another cell, in a hidden element, in script or style text, or in markup whose own characters put a `>` before it and a `<` after it.
    - Only the extractor's location rules and the replay speak to location.

- **R156 (P3; amends R147). The title's year joins the agreement set, and a year header needs its year alone.**
  - The years over a cell are the years `_parse_year` finds in the values `_headers_over` yields, period titles included, as R147 says.
  - **In `_period_matches`,** the period title that governs the pin (R124) adds its own year to that set.
    - A pin that needs a year (every pin whose header is not `% Chg` or `% Change`) locates only when the set is exactly the period's year.
    - The title's year no longer overrides a contradicting header.
  - **In `_locate`,** a pin whose header names a year locates only when the set is exactly that year. This holds in every role, whether or not the role requires a period title. The highlights role does not require one, and on the construction it bound PCORE and PDIL under the years 2025 and 2026.
  - `_matching_header` is deleted, since its only caller is gone. R147's "`_matching_header` returns nothing" now reads "the set is not a single year".
  - **Verified on the three originals:**
    - no pinned cell has two header years;
    - wherever a period title carries a year, it equals the header year over the cell, or the cell has none;
    - the frozen values bind as before.

- **R157 (P4; amends R118). A literal parses only to a finite number.**
  - `_literal` returns nothing when the parsed value is not finite. A figure too long for a float does not parse, so R145 makes the metric unlocated. With only one statement printing such a figure, the metric is still unlocated, never a conflict.
  - The validator's independent check uses the same literal grammar (R143), so it refuses a non-finite span for the same reason.

- **R158 (M2; amends R149). A comment is not structure.**
  - Every structural scan reads the source with each comment (`_COMMENT`) replaced by spaces of the same length, so no offset moves. That covers table pairing, nesting, rows, cells, and their spans and attributes.
  - A `<table`, `</table`, `<tr` or `<td` inside a comment therefore opens, closes or makes nothing. R149's "every `<table` start tag" means a start tag outside a comment.
  - Cell text is still read from the real source through the tokenizer (R143). A comment inside a cell still decodes to nothing, and it still leaves a literal unlocated when it splits it.
  - Three constructions follow:
    - On the auditor's construction, the earnings table holds both Diluted rows, and R130 leaves DIL unlocated.
    - A `<table>` inside a comment nests nothing, and the document binds every frozen value.
    - A commented copy of a pinned cell is not a cell. The columns do not move, and the printed value binds.
  - The seat verified that no comment in the five originals holds table, row or cell markup, so the originals' tables, spans and outcomes are unchanged. No frozen case puts such markup in a comment, so no case that compares with the round-0 witness changes.
  - Recorded limit: a structural tag inside another raw-text context, such as an attribute value, script or style, is outside the envelope.

- **R159 (M3; amends R145). The unit rule reads the unit cells beside a pinned value.**
  - For each pinned cell, primary and second, take the nearest non-empty cell on its left and on its right in its own row.
  - When either is a whole unit cell (`$` or `%`) that the pin's unit forbids, the cell does not parse under R145, and the metric is unlocated.
  - The rule applies where R152 applies the unit rule: after the unit-blind comparison, to an agreeing pair.
  - Both sides are read on purpose. A forbidden marker beside the value puts its unit in doubt, whichever value it was printed for. A layout outside the envelope that places one there is unlocated, which fails closed.
  - Admitted as before:
    - a `$` to the right of a per-share value, the next value's unit, as in the originals' `$ | 1.63 | $ | 1.54`;
    - a `%` to the right of a percent value.
  - The seat verified that no pinned cell of the three originals has a forbidden unit cell on either side.
  - The validator's independent check reads only the span, so this rule belongs to the extractor and the replay (R143's limit).

- **R160 (code review; conforms to R148). A vocabulary holds exactly the tokens the F1-Q originals produce.**
  - Delete these nine tokens:
    - `<period>` from `earnings` and `cash_flows`;
    - `<period>,<period>` from `drivers`, `core_reconciliation`, `prior_core_reconciliation`, `segment_results`, `cash_flow` and `cash_flow_reconciliation`;
    - `othernon-operatingincome/(expense),net` from `prior_core_reconciliation`.
  - The seat's census: no table that the three F1-Q originals admit to a role produces any of them for that role, and every role's other tokens are produced.
  - Some F2-A tables hold the `<period>` or `othernon-operating…` tokens. None of them matches a role those tokens are deleted from, so the F2-A outcomes are unchanged.
  - The frozen suite checks R160 by census: each vocabulary must equal the union of the label tokens of the tables the three originals admit to its role. This is a white-box check by necessity, because the rule is a property of the vocabularies, not of any one document. It is the second named exception to R131, after R143's seam.

- **R161 (the round-4 freeze, the gate, the repair, and the hold).**
  - **The freeze.** `tests/test_pg_envelope_f1_probes_r4.py` holds 136 cases, all authored by the seat from the audit's findings.
    - At `2a8d1eb1a9c` it gives 51 failed and 85 passed on Python 3.12, with only pytest and pyyaml installed.
    - Every failure is for its finding's reason:
      - 4 glued references bind;
      - 32 narrowed spans and 4 relocations are accepted;
      - CORE binds 1.59, and PCORE and PDIL bind 1.54 under contradicting years;
      - the 400-digit figure gives `inf`, or a conflict when only one statement prints it;
      - the hidden second row leaves DIL at 1.63, the commented `<table>` refuses the document, and the commented cell shifts the columns;
      - the forbidden unit cells bind 1.63, 1.54 and 3.0;
      - the census shows the nine tokens.
    - The 85 passes are the controls, and the 82 narrowings whose text no longer parses to the row's value.
  - **The gate.** The `earnings-economic-dossier` job in `.github/ci/legacy-jobs.yml` adds the suite to its paths and its run line. The suite adds about 53 seconds, within the 12-minute timeout.
  - **The repair.** The rulings fix the code to the line, so the seat writes the repair itself, in one commit per ruling, as it did for R152 and R153. It touches only `engine/company_intelligence/pg_envelope.py` and `economic_observations.py`. Everything else must hold:
    - every frozen file stays byte-identical;
    - all five frozen envelope suites pass;
    - the gate line and `curated_exclusive` pass;
    - the a5a and capital-structure suites match the baseline test by test.
  - **The R5 audit.** An independent Opus READ_ONLY audit then attacks the repair. Its floor adds the round-4 gaps:
    - the family-9 duration relabels on Q1 and Q2, not only Q3;
    - the family-10 sweep over present, unlocated and conflict rows;
    - the family-3 and family-11 fuzz over every pinned cell;
    - R155's delimiting on every legitimate layout form the earlier suites build;
    - hosted CI observed on the repair head.
  - **Hold.** #7905 stays Draft/HOLD under Sol's direction (comment 5825632041, R114).

- **R162 (the seat's witness audit; amends R161's freeze by addition only).** Every rule from R154 to R160, and every check in the validator's independent span check, now has a frozen case that fails when that rule alone is removed. Two checks cannot be isolated this way; they are covered under defence in depth below.
  - **The audit.** At `d678c8a4671` the seat removed one rule at a time, in memory and never on disk, and ran the five frozen envelope suites (472 cases).
    - Cases failed with each rule removed: R154, 4; R155, 36; R156, 1 for each half; R157, 2; R158, 3; R159, 3; R160, 1.
    - Removing R153's unit rule, or the check that the span parses to the row's value, failed no case.
      - R155 took over R153's frozen case. That case's target, `<!--1.63%-->`, sits in a comment, so R155 refuses it first.
      - No frozen case moved a receipt onto a delimited literal of another value.
  - **The witnesses.** `tests/test_pg_envelope_f1_probes_r4.py` gains four cases. Like R155's, they go through R143's seam. Each moves a present receipt onto a printed literal inside `<p>…</p>`, inserted before `</text>`, so it passes R155.
    - The first three literals parse to their row's value but carry a marker that row's unit forbids, so only R153 refuses them:
      - `1.63%` for Q3 diluted EPS;
      - `$3` for Q1 reported sales growth;
      - `$4` for the Q3 FX contribution, measured in points.
    - The fourth, `9.99` for Q3 diluted EPS, has the wrong value, so only the value check refuses it.
    - At `d678c8a4671` all four pass. Removing R153 fails exactly the first three. Removing the value check fails exactly the fourth. Removing any other rule fails the same cases as before and none of the four.
  - **Defence in depth.** The raw-literal check and the decodes-to-whitespace check have no witness, because no outcome can isolate them.
    - `html.unescape` keeps every whitespace character and every `<`. `_literal` returns nothing for text that holds whitespace, and its grammar has no `<`.
    - So the value check refuses every span that either of these checks refuses. Removing one of them alone changes only the reason the validator gives, never whether it refuses.
    - Both checks stay: they name the failure first, and R114 forbids relaxing the validator.
  - The suite now holds 140 cases. Its CI job, its paths and its run line are unchanged. #7905 stays Draft/HOLD.
