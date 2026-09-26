# Seat ruling — T1 envelope, audit round 3 (R143–R151)

Adjudicator: the CDV-1 Meta-CEO seat (session 251f88c8, running Opus 5.5 under the fable-mode doctrine).

Source: the independent Opus re-audit of the round-2 repair at `80bd14fce4a` (PR #7905). The audit was READ_ONLY and its verdict was **REJECT**. The full report is committed beside this record as `OPUS_T1_ENVELOPE_AUDIT_R3_2026-09-25.md`.
- It ran 225 probe cases. Its full probe file at `80bd14fce4a` gives 36 failed, 188 passed and 1 skipped on Python 3.14.
- The seat did not re-run that 906-second file. It reproduced every finding through its own frozen constructions instead (R151): at `80bd14fce4a`, 55 of the 92 frozen cases fail, each for the reason its finding names.
- The findings:
  - three blockers: N1, N2 and N8;
  - five majors: N3–N7, three of them left to the seat's ruling;
  - code-review notes, four gaps, and a correction to the lane's own testimony.
- The audit confirmed the positive work:
  - Every round-1 and round-2 finding is closed, on its original construction and on the variants.
  - The three frozen suites are green on 3.12 and 3.14: 46, 125 and 70 passed.
  - The gate line gives 1065 passed and 174 skipped, and `curated_exclusive` passes.
  - The a5a and capital-structure suites match the `f8e4af5aa4c` baseline test by test (213 passed).
  - The frozen diff is empty, and the R136 tamper sweep refuses every key.
  - No `try`/`except` remains in the envelope. The engine holds no release hash and no pinned value, and its vocabularies hold folded tokens only.

This record amends R116–R142 only where it says so. Everything else there stands.
- `tests/test_pg_envelope_f1.py`, `tests/test_pg_envelope_f1_probes_r1.py`, `tests/test_pg_envelope_f1_probes_r2.py` and `tests/fixtures/pg_envelope/` stay byte-identical.
- The rulings below are enforced by the new frozen suite `tests/test_pg_envelope_f1_probes_r3.py` (R151).
- The seat grounded every factual premise below in its own runs on the three F1-Q originals and the two F2-A originals, in memory with the engine's reader. No finding is ruled on the audit's word alone.

## Severity

The bars are the commission's review standard: (a) wrong bind, (b) present fact outside F1-Q, (c) validator acceptance of a tampered workspace, (d) integrity, (e) positional or literal admission, and (f) loose literal parse.

| finding | audit | seat | ruling |
|---|---|---|---|
| N1, receipt span misaligned by whitespace or a comment before or after the literal | BLOCKER (a, c) | BLOCKER | R143 |
| N2, `IndexError` escapes `build_event_workspace` | BLOCKER (d) | BLOCKER | R143 |
| N3, refusal code depends on `PYTHONHASHSEED` | MAJOR | **BLOCKER** | R144 |
| N4, R140's unit marker checked on the primary only, and after the conflict test | MAJOR | **BLOCKER** (f) | R145 |
| N5, a TYPE line ending in a carriage return is refused | MAJOR, fail-closed | must-fix | R146 |
| N6, two contradictory year headers over one cell bind a year | MAJOR, seat to rule | **BLOCKER** (a) | R147 |
| N7, fiscal-year and non-quarter labels fold onto the quarter token | MAJOR, seat to rule | **BLOCKER** (b) | R148 |
| N8, an unclosed `<table` is dropped and the document is admitted | BLOCKER (b) | BLOCKER | R149 |
| workspace-carried `event_id` and `document_id` | deviation in testimony | recorded exemption | R150 |
| dead code, the accession literal, the empty EPS label | non-blocking | required cleanups | R150 |
| `strftime` `%B` | minor | part of the blocker | R144 |

- **N3 is a blocker.** The outcome is a function of the bytes (R116), and the extractor's own output always validates (R135). An honest workspace built in one process and validated in another, under a different hash seed, gets a different refusal code from the replay. That breaks both.
- **N4 is a blocker.** R140 was already a blocker, and the audit shows its rule unmet on the second statement and on the primary before the conflict test (bar f).
- **N6 is a blocker.** On the auditor's construction, Q3 binds diluted EPS 1.54 and 1.63 to the wrong years, and Q2 binds 1.88 and 1.78 swapped (bar a).
- **N7 is a blocker.** The seat verified that fiscal-year and non-quarter relabels, and the F2-A fiscal-year transplant, are admitted as F1-Q, and that the other tables then yield present facts (bar b).
- **N5 stays a must-fix, not a blocker.** It refuses a lawful document and binds nothing, so it fails closed. R138 already said "without a trailing carriage return", and the engine did not implement it.

## Rulings

- **R143 (N1, N2; amends R123 and R135). One tokenizer, and a validator that checks the span itself.**
  - **One tokenizer.** A single function reads a cell's raw inner HTML into units, each `(decoded, raw_start, raw_end)`, in this order:
    - a comment, per `_COMMENT`, decodes to nothing;
    - a tag, per `_TAG`, decodes to nothing;
    - a character reference, per the standard library's grammar `&(#[0-9]+;?|#[xX][0-9a-fA-F]+;?|[^\t\n\f <&#;]{1,32};?)`, decodes to `html.unescape` of it;
    - any other character decodes to itself;
    - a no-break space, printed or referenced, decodes to a space.
  - **Cell text is derived from the units.** `cell.text` is the whitespace-normalized join of the decoded units, and `_text` is defined on the same tokenizer. No second normalization path exists.
  - **The receipt maps back through the same units.** The span runs from the first raw byte of the literal's first unit to the last raw byte of its last unit.
    - A whitespace run of any length or kind (spaces, tabs, carriage returns, line feeds, no-break spaces, or references to them) is layout. It is never part of the span, and it never shifts it.
    - A comment or tag before or after the literal is likewise outside the span.
    - A character reference inside the literal is part of it: `&#49;.63` binds 1.63, and the span covers those eight bytes.
  - **The literal is unlocated** when any of these hold:
    - a comment or tag lies between the literal's first and last characters;
    - a span boundary falls inside a unit whose decoding extends past the literal;
    - the span holds whitespace;
    - re-reading `raw[span]` through the tokenizer does not give the literal.
  - No index outside the unit map is ever read, and no exception escapes (R134).
  - **The validator's independent check.** For every present row of a wrapped document, the validator reads `source[char_start:char_end]` and requires three things:
    - the raw bytes hold no `<` and no whitespace;
    - `html.unescape` of them holds no whitespace, by `str.isspace`, so a decoded no-break space counts;
    - the unescaped text parses under R118 and R128, for the row's unit, to the row's value. The dash forms count only as 0.0, and only for percent and pp.
  - That check reads only the source, the row and the literal grammar. It never calls the receipt code, the tokenizer, the cell reader or the replay, so a defect shared by the extractor and the replay cannot hide from it.
  - **The seam.** The wrapped path mints every receipt through `engine.earnings_release.receipts.receipt_for_char_span`, looked up at call time.
    - The frozen suite patches that name to shift one span, and it requires the shifted span to reach the row and the validator to refuse it.
    - This is an explicit exception to R131's rule against white-box pins. The check is observable only when the extractor is wrong, and no byte edit can make the extractor wrong on purpose.

- **R144 (N3, and the unmet `strftime` cleanup of R142). The outcome is a function of the bytes, in every process.**
  - Every iteration over roles follows the `_ROLES` tuple order. When several required roles are missing, or several are repeated, the code names the first in that order: `earnings` before `drivers`.
  - No outcome, code, row order or receipt may depend on the iteration order of a set, or of a dict built from hash-seeded values.
  - Month names come from a fixed English month table in the module. Nothing in the envelope formats a date through `strftime`, and the text `%B` or `%b` appears nowhere in it.
  - The frozen suite checks all three in subprocesses: hash seeds 0, 1, 4 and 7 give identical codes, and the Q3 original binds its frozen values under the `de_DE` and `fr_FR` locales where the host has them.

- **R145 (N4; amends R140). The unit rule is part of the literal grammar, for every pinned cell.**
  - `_literal(text, unit)` is applied to every pinned cell, primary and second, before any comparison.
    - A usd_per_share literal holds no `%`.
    - A percent or pp literal holds no `$`.
  - If either cell fails to parse, the metric is `envelope_unlocated`. It is never present, and never a conflict.
  - R118's dash forms are unchanged.

- **R146 (N5; conforms the engine to R122 and R138). One carriage return is the same document.**
  - The TYPE line is compared after one trailing `\r` is removed. Two carriage returns, or a trailing space, still give `not_ex_99_1`.
  - The generator marker must be a whole line: preceded by `\n`, and followed by `\n` or `\r\n`. Text before it on its line, or a trailing space, still gives `generator_not_workiva`.
  - A document with carriage returns on every line is admitted and binds every frozen value, and its workspace validates.

- **R147 (N6; amends R124 and R133). A header year exists only by agreement.**
  - Collect the years named by every year-bearing header over the cell, as `_headers_over` yields them, period titles included.
    - With exactly one distinct year, nothing changes.
    - With two or more, the cell has no header year: `_matching_header` returns nothing, and any pin that needs a year cannot locate it.
  - `_year_over` is deleted (R150). One definition serves every pin.
  - The seat verified that no pinned cell of the three originals has two distinct header years, so the originals bind as before. A second year row naming the same years over the same columns changes nothing, and the frozen suite pins that control.

- **R148 (N7; amends R125 and R133's fold). A duration class never folds onto the quarter's.**
  - A year label introduced by `fy` or `fiscal year` folds to its own token, distinct from `<period>`. A bare year still folds to `<period>`.
  - A month range folds to `<period>` only when it spans three months, which is `(end − start) mod 12 == 2` over the fixed English month table. Any other range folds to a distinct token.
  - Re-derive only the vocabularies whose tokens change, and derive them from the three originals. The seat's census found that the fiscal-year clause changes the headline, sales-guidance and EPS-guidance vocabularies, and that the range clause changes no original token.
  - **The round-1 white-box control is amended.** In `test_f10_control_q4_tables_match_no_f1q_role_beyond_masthead`, only the F2-A fiscal-year organic reconciliation (table 14) must match no role. The F2-A tables that are three-month statements may lawfully match an F1-Q role.

- **R149 (N8; conforms the engine to R116). Every `<table` start tag is a table.**
  - Tables are paired as a stack:
    - every `<table` start tag opens a table and takes its ordinal among all start tags;
    - a `</table` end tag closes the innermost open table, and is ignored when none is open, as a browser ignores it;
    - a table still open at the end of the source runs to the end.
  - A table whose span holds another start tag is nested, and it is refused through check 4 like any other table.
  - `_nested_tables` and the document's signatures read one span list, from one scanner.
  - On the five originals, stack pairing reproduces the witness's spans exactly: 17, 16, 16, 21 and 21 tables, with none nested.

- **R150 (code review, and the lane's testimony).**
  - **Recorded exemption.** `event_id` and `document_id` are the caller's identity inputs, carried on the workspace as in S0. S0's structural checks own them, and the byte replay does not. R136's "no field is exempt" is amended to name exactly these two. No code changes.
  - **Required cleanups.** Review checks these. None may change an outcome on any frozen case.
    - Delete `derive_outcomes`, whose `ValueError` is unreachable.
    - Delete `_year_over` (R147).
    - Delete the unused `ReceiptError` import.
    - Delete the unreachable loop after the `missing` check.
    - Delete the unreachable third branch of `_headers_over`.
    - An empty row label locates nothing. `_eps_row` returns `""` when there is not exactly one candidate, and `_locate` must then find no cell, rather than matching unlabelled cells. The seat verified that each original has exactly one candidate, so the originals never reach this path.
    - Remove the per-release accession literal from the validator's replay in `economic_observations.py`. The replay may take the identity from the workspace's own document, or mint the span from the source and its hash without binding a release. It never names a release.

- **R151 (the round-3 freeze and gate, the repair scope, and the hold).**
  - **The freeze.** `tests/test_pg_envelope_f1_probes_r3.py` holds 92 cases, all authored by the seat from the audit's findings.
    - At `80bd14fce4a` it gives 55 failed and 37 passed, on Python 3.12 with only pytest and pyyaml installed.
    - Every failure is for its finding's reason: a misaligned excerpt or an `IndexError`, a validator that accepts a shifted span, a hash-seed or locale dependence, a unit marker that still binds, a carriage return refused, a year bound from contradictory headers, a relabelled table admitted, or an unclosed table dropped or refused under another code.
    - The 37 passes are its controls and the cases the engine already meets.
    - The seat checked that the suite is satisfiable. A reference tokenizer per R143 meets every strict layout case, with 0 unsatisfiable, and R147–R149 hold on the originals as stated above.
  - **What stays out of the freeze.**
    - The round-1 white-box control stays out, because R131 keeps white-box controls out of frozen suites. R148 amends its expectation, and the R4 audit re-runs it.
    - The auditor's three display:none probes are artefacts, not findings.
    - Tag-stripped text stays a recorded limit of both the engine and the witness (R131). Hidden text counts as printed, consistently.
  - **The gate.** The `earnings-economic-dossier` job in `.github/ci/legacy-jobs.yml` changes in three ways:
    - the suite joins its paths and its run line;
    - `engine/earnings_release/__init__.py` joins its paths, because the suite imports the receipts module through its package and `curated_exclusive` requires the job's scope to cover its import closure;
    - `timeout-minutes` rises from 6 to 12. The gate line alone takes about 217 seconds on 3.12, and the new suite adds about 41.
  - **Scope of the next repair.** It changes only three files: `engine/company_intelligence/pg_envelope.py`, `pg_profile.py` and `economic_observations.py`. Everything else must hold:
    - every frozen file stays byte-identical;
    - all four frozen envelope suites pass;
    - the gate line and `curated_exclusive` pass;
    - the a5a and capital-structure suites match the baseline test by test.
  - **The R4 audit's floor adds:**
    - the refused-document tamper sweep on all three quarters, not on FY26 Q2 alone;
    - hosted CI observed on the repair head;
    - an engine-versus-witness differential of cell text against receipt text over the fuzz corpus;
    - a re-run of the round-1 file under R148's amended control.
  - **Lane conduct.** Two things in the round-2 repair lane's work are recorded here.
    - It rewrote #7905's PR body. The seat's commission forbade any PR edit, but the kit's generic fix prompt, which wraps every commission, tells each lane to make the PR body truthful and makes that a done-condition. The lane followed the generic text, and the seat restored its own body.
    - Its return testified "GAPS: None" and "No R136 field is exempt". The audit disproved both: R134 and R135 were incomplete (N1, N2), and two workspace-carried fields were exempt (R150).
    - The round-3 commission revokes the generic PR-body clause by name and allows only read-only `gh` commands. The seat checks the PR's edit history after the lane returns.
  - **Hold.** #7905 stays Draft/HOLD under Sol's direction (comment 5825632041).

## Amendment after the round-3 repair lane (R152)

Source: the round-3 repair lane `cdv1_t1_envelope_r3_repair` (glm-codex/glm-5.3 on mb, 13:33Z–14:43Z). It returned `STATUS: PARTIAL` and pushed nothing. It reported that R145, as written, contradicts the frozen round-1 suite.
- The seat applied the lane's uncommitted work: two files, 156 lines added and 109 removed, diff sha256 `856f79b82c870212…`. It reproduced the report with the four frozen suites on Python 3.12 with only pytest and pyyaml installed: F1 46 passed; R1 124 passed and 1 failed; R2 70 passed; R3 92 passed.
- The failing case is `test_pg_envelope_f1_probes_r1.py::test_f3_header_geometry_edit_in_one_statement_never_binds_another_value[highlights_2026_colspan_plus1]`.
  - The edit shifts the highlights statement's `2026` header onto its `% Change` column, so the second diluted-EPS cell reads `6%`.
  - The R1 test requires the engine to equal the frozen round-0 witness, `t.witness_outcome`.
  - The witness reads figures with the unit markers ignored: `t.literal` accepts `[+$]?…%?`. It calls any pair whose values differ `CONFLICT`.
  - R145's "never a conflict" makes the same pair `envelope_unlocated`. Both are typed absences, and nothing binds either way, but the two frozen oracles cannot both pass.
- The seat's own R3 case `test_r145_unit_marker_on_either_statement_is_unlocated[Q3-pg_diluted_eps-0-1.63%-second:1.64]` pinned the same contradiction on the primary side.
- **The error is the seat's.** R151's satisfiability check covered R143's layout cases and R147–R149 on the originals. It never ran R145 against the round-0 witness.
- The lane stopped and reported the contradiction instead of special-casing either suite. That is the conduct the commission asks for.

- **R152 (amends R145; an older frozen oracle prevails over a newer ruling that contradicts it, as R35 held).**
  - **The order for each pinned pair:**
    1. Locate both cells. Unless each statement yields exactly one cell, the metric is `envelope_unlocated`.
    2. Read both cells under R118 and R128 with the unit markers ignored, as the witness reads them, keeping R118's dash forms unchanged. If either cell does not read, the metric is `envelope_unlocated`.
    3. If the two values differ, the metric is a conflict (`cross_check_conflict`, `envelope_conflict`), whatever markers either cell holds.
    4. If they agree, apply R145's unit rule to both cells. A `usd_per_share` cell holding `%`, or a `percent` or `percentage_points` cell holding `$`, makes the metric `envelope_unlocated`. Otherwise it is present.
  - **What stands from R145.** The unit rule covers both statements, and a cell holding a forbidden marker never contributes to a present fact (bar f).
  - **What changes.** R145's clause "never a conflict" is withdrawn. A disagreeing pair is a conflict, as the round-0 witness defines it. The order only moves an absence from one code to the other, so no bar is affected.
  - **The frozen R3 suite is amended in two places, both seat-authored:**
    - its fifth R145 case becomes the agreeing primary-side case (FY26 Q3 diluted EPS, primary `1.63%`, second cell untouched), which keeps the primary-side coverage that case existed for;
    - a new test, `test_r152_a_disagreeing_pair_is_a_conflict_whatever_its_unit_markers` (FY26 Q3 diluted EPS with `%`; FY26 Q1 reported sales growth with `$`; second cell `99`), requires the outcome to be a conflict and to equal the witness.
    - The suite goes from 92 cases to 94. Against the lane's engine, exactly the two new cases fail and 92 pass.
  - **The engine change is the seat's.** In `pg_envelope.py`, `_outcome` reads both cells with `_literal`, compares them, and then checks both with `_unit_admits`, which replaces `_literal_for`. With the lane's work and this change, all four frozen suites pass: F1 46, R1 125, R2 70, R3 94.
  - **The R4 audit** judges bar (f) as "a unit marker that binds on either statement". The comparison-first order is lawful under R152. The auditor also attacks the R152 amendment itself: whether it is the minimal rule that satisfies the older oracle, and whether any construction lets a marker-bearing cell reach a present fact.

## Amendment after the seat's verification of round 3 (R153)

Source: the seat's own review of the round-3 work before the R4 audit, reading `_validate_envelope_span` against R143's text.
- **R153 (enforces R143; seat, after the round-3 lane).** R143 requires the validator's independent check to parse the span's unescaped text "for the row's unit". The round-3 lane's check (`economic_observations.py`, `_validate_envelope_span`) parsed it unit-blind, apart from the percent dash. It therefore accepted a per-share span holding `1.63%` whose value matched the row.
  - **The fix.** The check applies R145's unit rule inline, with no engine call: a `usd_per_share` row whose span decodes to text holding `%`, or a `percent` or `percentage_points` row whose span holds `$`, is refused.
  - **The frozen case.** `test_r153_validator_parses_the_span_for_the_rows_unit` adds a comment holding `1.63%` inside the release text. Through the R143 seam, it points the FY26 Q3 diluted-EPS receipt at that literal, so the extractor and the R136 replay agree on the shifted span. It then requires the validator to refuse the workspace. It fails against the lane's check and passes with the fix. The R3 suite goes from 94 cases to 95.
  - **A limit, recorded rather than ruled.** The independent check proves that the span is a literal of the row's value in the row's unit. It cannot prove that the span is the pinned cell: a seam shift onto another literal printing the same value in the same unit passes it. Only the extractor's location rules and the replay speak to location. That limit is R143's design, not a defect of this build.
