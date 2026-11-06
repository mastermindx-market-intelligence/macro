# Opus re-audit R3: CDV-1 T1 F1-Q envelope at 80bd14fce4a5e4b3c38c5b3817a1453e4b6f8d48 (PR #7905)

Mode: READ_ONLY. Nothing in the repository was edited, committed or pushed; no `gh pr` command was run.
Bar: the commission's (a)-(f) under R116-R121, R122-R131 and R132-R142 (R139 amends bar d).
Probe file: `test_envelope_audit_probes_r3.py` (225 cases). Exploration scripts: `ex1.py`-`ex7.py`. Logs: `probes_batch1-6.log`, `probes_full.log`.

## STATUS: REJECT

There are three blockers:
- N1 (bars a and c): the receipt span is wrong and the validator accepts it.
- N2 (bar d / R134): an IndexError escapes `build_event_workspace`.
- N8 (bar b): an unclosed injected `<table>` is admitted.

All three come from shared engine code that the R136 replay cannot see. N1 and N2 are both in `_receipt`, and N8 is in `_table_spans`.

The repair otherwise holds:
- Every round-1 and round-2 finding is closed on its original construction and on the variants.
- All three frozen suites are green on 3.12 and 3.14, and so are the gate line and `curated_exclusive`.
- a5a and capital-structure are identical per test to f8e4af5aa4c.
- The frozen diff is empty.
- The R136 tamper sweep refuses every key.

Other findings:
- Majors N3–N7, which are ruling deviations or fail-closed defects.
- One round-1 white-box control still fails, as N7 explains.

## RESULT

| id | bar / sev | probe (test_envelope_audit_probes_r3.py) | observed | expected |
|---|---|---|---|---|
| N1 | a+c, BLOCKER | `test_n1_n2_whitespace_or_comment_before_literal_keeps_exact_span[two_spaces|crlf|tab_tab|comment_tail_two_char_entity-Q3-pg_diluted_eps / -Q2-pg_core_eps]` | 1.63 / 1.88 are bound with `display_excerpt '.63&#160;'` / `'.88&#160;'`, and the validator accepts | the span is exactly `1.63`/`1.88`, or the metric is unlocated; the validator refuses any other span |
| N2 | d (R134), BLOCKER | `...[newline_indent-*]`, `...[comment_tail_bare_amp-Q3|Q2]`, `...[two_spaces|crlf|tab_tab|comment_tail_two_char_entity-Q1-*]`, `test_f11_literal_fuzz...[14-Q3-pg_diluted_eps-0]` | `IndexError: list index out of range` escapes `build_event_workspace` | no exception |
| N8 | b, BLOCKER | `test_sp_stray_unclosed_table_token_after_last_table_is_not_silently_admitted` | admitted as F1-Q, every value bound, the validator accepts | refused `unknown_table:t16`, with no present fact |
| N3 | R135 determinism, MAJOR | `test_n3_refusal_code_is_independent_of_pythonhashseed` | the code is `required_table_missing:earnings` or `...:drivers`, depending on PYTHONHASHSEED | one code for the same bytes |
| N4 | R140, MAJOR | `test_n4_r140_unit_marker_on_either_statement_is_unlocated[*]` (5) | a second statement printed `1.63%` or `$7%` still binds; a primary `1.63%` against `1.64` gives a conflict | unlocated |
| N5 | R122/R138, MAJOR (fail-closed) | `test_n5_type_line_trailing_cr_is_tolerated[Q1,Q2,Q3]` | `not_ex_99_1` | the trailing CR is tolerated, and the document is admitted |
| N6 | a/e candidate, MAJOR (seat to rule) | `test_n6_two_contradictory_year_headers_never_bind[Q2,Q3]` | Q3 binds DIL 1.54 and PDIL 1.63; Q2 binds 1.88 and 1.78 (swapped) | unlocated (the witness finds 2 hits) |
| N7 | R125/R133 (e candidate), MAJOR | `test_n7_*` (3) | "FY 2026" folds to the quarter token `<period>`; a relabelled orgrec is admitted; F2-A t14 matches `organic_reconciliation` | `unknown_table:t11`; t14 matches no role |

### Findings in detail
### N1 — receipt span misaligned by a multi-character whitespace run before the literal (bar a + c; R123/R135) — BLOCKER
- Construction: FY26 Q3 earnings Diluted 2026 cell `>1.63&#160;<` -> `>  1.63&#160;<` (two spaces), or `>\r\n1.63&#160;<` (CRLF), or a comment tail holding a two-char entity (`<!-- >&acE; -->`).
- Observed: `pg_diluted_eps` bound 1.63 with `display_excerpt '.63&#160;'` (span starts one character late and swallows the entity). `validate_selected_facts` ACCEPTS it (the replay shares the defect).
- Expected: span covers exactly `1.63` (R123/R135), or the fact is unlocated; the validator must refuse any other span.
- Code: `engine/company_intelligence/pg_envelope.py:928-955` (`_receipt`). A whitespace run is appended as ONE extent (`:929-934`) but `html.unescape("".join(...))` (`:950`) yields one decoded character per raw whitespace character, so decoded index != extent index after any run of length >= 2 (and after any `&...;` extent that does not decode to exactly one character, e.g. `&acE;` -> 2 chars, or a bare `&` whose `find(";")` runs into a later tag, `:941-947`). `extents[start]` (`:954`) then indexes the wrong raw extent.
- This is exactly the "shared extractor defect replay cannot see" of the seat pointer: R136 replay re-runs the same `_receipt`.

### N2 — IndexError escapes build_event_workspace on an admitted document (bar d; R134, R122) — BLOCKER
- Construction: same cell, `>\n    1.63&#160;<` (newline + indent), or `><!-- >& -->1.63&#160;<` (comment tail with a bare `&`).
- Observed: `IndexError: list index out of range` raised out of `build_event_workspace`.
- Expected: no exception (R134 names IndexError explicitly); the metric unlocated or correctly bound.
- Code: `pg_envelope.py:955` `last = extents[start + len(cell.text) - 1]` with the misaligned index of N1; `_receipt` is called unguarded at `:1028`.

### N3 — refusal code depends on PYTHONHASHSEED (R135 "extractor output always validates"; determinism) — MAJOR (seat may escalate)
- Construction: FY26 Q3 with drivers AND earnings tables both removed (or both repeated).
- Observed across PYTHONHASHSEED 0..7: `required_table_missing:earnings` for seeds 0,1,2,3,5,6 and `required_table_missing:drivers` for seeds 4,7 (same split for `required_table_repeated`).
- Consequence: a workspace built in one process is refused by the validator in another process; stored workspaces are not reproducible.
- Code: `pg_envelope.py:606-614` iterates the frozenset `required_roles` (`_REQUIRED_ROLES = frozenset(...)`, `:51`) and returns `repeated[0]` / `missing[0]`.

### N4 — R140 unit marker checked on the primary statement only, and after the conflict test — MAJOR
- D0: FY26 Q3 highlights Diluted EPS (second statement) printed `1.63%` -> `pg_diluted_eps` binds 1.63; validator accepts. R140: a usd_per_share literal containing `%` does not parse -> unlocated.
- D2: second statement of `pg_reported_sales_growth_pct` printed `$7%` -> binds 7.0 (R140: percent literal with `$` does not parse).
- D1: primary `1.63%` with second `1.64` -> `cross_check_conflict`; R140/R128 say a non-parsing literal is `envelope_unlocated`, never a conflict.
- Code: `pg_envelope.py:893-899` (conflict tested before the unit check; unit check reads `primary[0].text` only).
- The bound value itself follows the primary cell, so bar (a) as worded is not breached; this is a ruling-conformance defect.

### N5 — a TYPE line with a trailing carriage return is refused `not_ex_99_1` (R122/R138 deviation; fail-closed) — MAJOR, non-blocking (coverage)
- Construction: `<TYPE>EX-99.1\n` -> `<TYPE>EX-99.1\r\n` only.
- Observed: every row `envelope_refused:not_ex_99_1`. R122: "a trailing carriage return is tolerated"; R138: "Its line, without a trailing carriage return, reads exactly `<TYPE>EX-99.1`".
- Code: `pg_envelope.py:591-592` compares `group(0)` of `<type>(.*)` (which captures `\r`) to the literal. A whole-CRLF body is additionally refused by the LF-only generator test at `:594`.

### N6 — two year headers over one earnings cell: the engine takes the first (farthest) one; the witness is ambiguous (family 9 divergence) — MAJOR, seat to rule (bar a/e candidate)
- Construction: FY26 Q3 earnings, an extra row inserted above the real year row printing `2025` over the 2026 column and `2026` over the 2025 column; highlights year headers swapped (the frozen `period_both` style).
- Observed: `pg_diluted_eps` binds 1.54 and `pg_prior_diluted_eps` binds 1.63; validator accepts. Without the highlights swap: conflict.
- Witness (`headers_over` + pins): both earnings cells carry the pinned header -> 2 hits -> unlocated.
- Code: `pg_envelope.py:732` / `:740-741` `_matching_header` returns the first year-bearing header over the cell, a positional resolution of contradictory year headers that R124/R132 do not authorise.


### Code review (family 8), non-blocking
- Dead code:
  - `derive_outcomes` (`pg_envelope.py:968-989`) has no caller in `engine/`, `app/` or `scripts/`, so its `ValueError("an admitted document cannot be read")` (`:973`) is unreachable. No byte edit reaches it.
  - `_year_over` (`:744-745`) is unused.
  - `ReceiptError` is imported but unused (`:15`).
  - The loop `for role in required_roles: if role not in roles` (`:615-617`) is unreachable after the `missing` check (`:612-614`).
  - The third branch of `_headers_over` (`:654-656`) is unreachable: two own cells in one row never share a `col0`.
- A per-release literal: the validator replay binds with `accession="0000080424-26-000056"` (`economic_observations.py:228`), which is FY26 Q3's accession.
  - It is inert, because no row field carries the accession: `_span` uses `bound.revision.source_sha256` and `bound.source` (`pg_profile.py:1897-1908`).
  - Family 10 confirms Q1 and Q2 still self-validate.
  - It is still a fixture-specific literal in engine code, and should be removed.
- Locale dependence: `_admission` (`:619`) and `_prior_note_present` (`:910`) still use `strftime` `%B`, which is LC_TIME-dependent. R142 asked for a format that does not depend on the platform, and `%-d` is gone. Minor.
- No `try`/`except` remains in `pg_envelope.py`.
  - No probe-specific strings, fixture hashes or pinned cell values are in the engine. Grep found none of the release sha256s and no pinned literal values.
  - The vocabularies hold folded tokens only; `'<month><n>,<period>'` replaces the literal month names.
  - The integrity-warning hunt found no special-casing of the frozen constructions, apart from the accession literal above.
- The `_eps_row` empty-label path: with two diluted-EPS rows, `eps_row == ""` (`:817-818`), and `_locate` then matches cells that have no label (`:780`).
  - My construction added an unlabelled row under Core(Non-GAAP) and gave the "Core EPS" sub-header cell a label. The metric stayed unlocated, so R130 holds on that construction.
  - The path is still structurally fragile. An empty-string row label should short-circuit to "not located".
- The engine grid reader mirrors the suite's `grid()` byte for byte. The shared defects this hides:
  - `_table_spans` versus the witness `tables()` on malformed markup. The witness raises on nested or unclosed tables, while the engine drops unclosed ones (N8).
  - Tag-stripped text semantics.
  - The raw-offset receipt mapping (N1 and N2), which the witness never computes; it checks only `byte_offset(cell.start) <= start`.
- The frozen `assert_envelope` would catch N1 if it were run on these constructions, because `literal(text('.63&#160;')) != 1.63`. No frozen case puts whitespace before a literal.

## PROGRESS LOG (appended as families complete; consolidated at the end)

### Batch 1 (N1-N6 probes): 29 run, 28 failed (`probes_batch1.log`)
- N1/N2 (18 cases: 6 edits x Q1/Q2/Q3): 17 failed. Q3 DIL and Q2 CORE bind `'.63&#160;'` / `'.88&#160;'` under two-space, CRLF, tab-tab and two-char-entity comment tails; newline+indent and bare-`&` comment tails raise IndexError on all three quarters. The one pass (Q1 SALES, bare-`&` comment tail) is not a counter-example.
- N3 1/1 failed; N4 5/5 failed; N5 3/3 failed; N6 2/2 failed (Q2 binds DIL 1.88 / PDIL 1.78 swapped; Q3 1.54 / 1.63).

### Round-1 and round-2 probe files re-run at 80bd14fce4a
- Round-1 (`probes_r1_rerun.log`): 4 failed, 99 passed. Three are the named probe artefacts (`f4 [2.0 pts]`, `f4 [— per share]`, `f7_drivers_title_date_removed`). The fourth, the white-box control `test_f10_control_q4_tables_match_no_f1q_role_beyond_masthead`, STILL FAILS (commission: must now pass). Diagnosis: of the five F2-A tables that match F1-Q roles, four are genuinely three-month tables (Q4 segment drivers "April - June 20xx", quarterly organic reconciliation, three-month cash-flow tables), which R133 lawfully lets match; the fifth, t14, is the fiscal-year organic reconciliation labelled "FY 2026"/"FY 2025", which folds to `<period>` — the same token as the quarter range title. -> N7.
- Round-2 (`probes_r2_rerun.log`): 1 failed, 67 passed. The one failure is `test_d_s0_validator_missing_fields_tamper_outcome_unchanged` (B11), superseded by the R139 ratification; its frozen replacement passes. B1-B10, M1, M2 original constructions all pass.

### N7 — a fiscal-year period label folds onto the quarter range token (R125/R133) — MAJOR (seat to rule on bar e); corroborates the failing round-1 control
- `_label_token` (`pg_envelope.py:129-130`): the range form folds to `<period>` (`:129`) and a bare fiscal-year label `FY 2026` / `fiscal year 2026` folds to `<period>` too (`:130`), so the twelve-month class and the three-month range class share one token, contrary to R125 ("the duration word stays, so a twelve-month (F2-A) title never folds onto a three-month one").
- Probes: `test_n7_fy_label_orgrec_is_unknown_not_organic_reconciliation`, `test_n7_f2a_fiscal_year_orgrec_matches_no_role[FY25Q4, FY26Q4]`.
- Effect inside F1-Q: a Q3 organic reconciliation relabelled "FY 2026" is admitted (its pins then unlocate for lack of a title, so no wrong value binds). Fail-closed on values; the admission code differs from R125.

### Batch 2 (family 0 variants + seat pointers): 40 run, 2 failed (`probes_batch2.log`)
- One failure was a probe artefact (the witness `after_table` raises on nested tables); corrected to use the engine span list and re-run in batch 3.
- Family 0 variants all hold: B1 (5 range variants), B2 (3 duration variants), B3 (3 day variants), B8 (4 unparseable titles, no exception), B9 (3 of 4 order variants; 4th re-run), B10 (5 isspace prefixes), M1 (3 second-TYPE variants), R141 (3 anchor variants), B7 (4 entity-before-literal variants).
- Seat pointers: `<TEXT>` in a header comment (control, refused), two diluted-EPS rows + unlabelled Core(Non-GAAP) cell (unlocated, R130 holds), drivers table with hidden current title + year-ago title (totals not bound), stray `<table>` before the balance sheet (refused).

### N8 — an injected, unclosed `<table>` after the last table is silently dropped; the document is admitted and binds all values (bar b) — BLOCKER
- Probe: `test_sp_stray_unclosed_table_token_after_last_table_is_not_silently_admitted`. Construction: FY26 Q3 with `<table><tr><td>Pro Forma Combined Company</td></tr>` (no `</table>`) after the last table.
- Observed: admitted F1-Q; every frozen value bound; validator accepts.
- Expected: R116 counts ordinals "among all `<table` start tags"; this start tag is an unknown table (its label is the frozen `INJECTED_TABLE` label) -> `unknown_table:t16`, no present fact. A browser renders the unclosed table (implicitly closed at end of body).
- Code: `pg_envelope.py:155-173` `_table_spans` only emits a span when depth returns to 0; an unclosed start tag emits nothing, so `document.signatures` never contains it and check 4 (`:599-605`) never sees it.

### Batch 4 (family 9 headers_over differential + family 11 fuzz): 101 run, 4 failed (`probes_batch4.log`)
- Family 9 differential (`test_f9_headers_over_differential_on_pinned_cells`): 20 bodies (3 originals, 9 frozen MUTATIONS, 7 frozen R2 range retitles, rowspan-2 earnings title on Q2 and Q3 — 21 incl. both rowspans) — every pinned cell's governing period titles are identical between the engine `_headers_over`/fallback and the witness `headers_over`/fallback. No divergence that changes a governing title on those bodies. The one divergence found is N6 (year headers, not titles), found by construction.
- Family 9 tag-stripped semantics: a comment holding `>` and "Nine Months Ended" inside the earnings title cell -> frozen values (engine strips comments before tags; the witness would read the comment tail as text — an engine/witness divergence in the SAFE direction, recorded not blocking). A `display:none` span " Nine" inside the title cell -> `unknown_table:t4` on Q1/Q2/Q3 (3 failures of my probe, which allowed only unlocated/frozen): a lawful fail-closed refusal, marked PROBE ARTEFACT. Hidden text counts as printed (R131 known limit), consistently in engine and witness.
- Family 11 fuzz: 10 title edits (unknown month, day 32, `031`, tags inside, entity-for-letter, empty, 5-digit year, 300-digit day, year 0000): no exception, own output validates. 16 literal edits x 4 pinned cells (Q3 DIL, Q2 SALES, Q1 COREG second, Q2 CORE): 63 of 64 hold (entity digits `&#49;.63`/`&#x31;.63` bind with an 8/9-byte span over the printed characters; tags/comment-interrupted literals unlocated; `&`, `&#0;`, `1.63;`, 400-digit runs unlocated; no exception). The one failure, `"  1.63"` in Q3 DIL, raises IndexError: a further N2 construction (a raw NBSP plus a space is a two-character whitespace run).

### Batch 5 (families 1-3, 7, 8 on Q1/Q2, plus R124 two titles): 37 passed, 1 skipped, 0 failed (`probes_batch5.log`)
- F1 cross-table swaps, 5 x Q1/Q2 (1 skipped: the two cells print the same literal in that quarter, so the swap is a no-op): conflict/unlocated/frozen, validator accepts.
- F2 duplicate pinned rows, 4 x Q1/Q2: unlocated.
- F3 header geometry (year colspan in earnings and highlights, Price colspan, OSG header shift), 4 x Q1/Q2: no other value bound.
- F7 R126/R127 on Q1/Q2: Q2 + Q1 prior-core table keeps frozen values; balance sheet dropped / cash flow repeated keep admission (R126); Q1 prior-core dropped -> `required_table_missing:prior_core_reconciliation`; repeated -> `required_table_repeated:prior_core_reconciliation`.
- F8 Q2 footnote: other date, moved after cvya, removed -> PCORE unlocated; a negated appendix is the shared substring limit (recorded).
- R124 two identical current titles over the core reconciliation on Q1/Q2/Q3 -> CORE unlocated.

### Batch 3 (family 10 R136 sweep, N7, B9 re-run): 20 run, 3 failed (`probes_batch3.log`, 12 min)
- `test_f10_every_key_tamper_is_refused` covers five row-kind cases, and all five pass. The row kinds:
  - FY26 Q1, Q2 and Q3 originals: present rows, plus the excluded REC row;
  - Q3 `period_single` + `note_removed`: conflict and unlocated rows;
  - Q2 relabelled EX-99.2: refused-document rows.
- For every pg_ row and every leaf key path, nested `source_span.*`, `source_span.locator.*`, `source_span.receipt.*` and `typed_absence.*` included:
  - a value tamper (str+"x", int+1, float+0.01, None->"x", list+item, bool flip) is refused;
  - a key deletion is refused.
- `test_f10_span_one_char_wider_narrower_recomputed_is_refused[Q1,Q2,Q3]` passes. Every present row's span was moved by ±1 byte at either end, with hashes and the excerpt recomputed, and each was refused.
- Multiplicity: duplicate, dropped and unknown `pg_forged` rows are refused; a reorder is accepted (the frozen treatment).
- Re-pointing a Q3-scope workspace at the caller-held Q2 bytes is refused.
- B9 order: 4 of 4 hold, the corrected Q3 nested-t3 variant included.
- N7: 3 of 3 fail (the finding).
- Batch 6 records one workspace-carried field: a consistent rename of `event_id`, with fact_ids recomputed, is ACCEPTED, exactly as in S0. `event_id` and `document_id` are identity inputs from the workspace. They are not derived from bytes and scope, so they are an implicit R136 exemption that the lane's "No R136 field is exempt" does not mention. This is not a bar (c) finding.

## Families: probes run / failed (225 cases; artefacts excluded from findings)
| family | run | failed | notes |
|---|---|---|---|
| N-series constructions (seat pointers: receipt, admission order, wrapper CR, year headers) | 29 | 28 | N1 ×10, N2 ×7 (+1 pass), N3, N4 ×5, N5 ×3, N6 ×2 |
| 0: round-2 findings, variants (B1 5, B2 3, B3 3, B7 4, B8 4, B9 4, B10 5, M1 3, R141 3) | 34 | 0 | all closed; the round-2 file re-run gives 67/68, and its 1 failure is the B11 differential superseded by R139 |
| 1: round-1 findings (re-run of the round-1 file) | 103 | 4 | 3 named artefacts; the white-box Q4 control still fails, and N7 explains it |
| seat pointers (other) | 6 | 1 | N8; controls: `<TEXT>` in a header comment, `_eps_row` empty label, hidden drivers title, stray `<table>` mid-document |
| 2: Q1/Q2 sweep, families 1–3, 7, 8, plus R124 two titles | 38 | 0 | 1 skip (no-op swap) |
| 4: R125 / N7 | 3 | 3 | N7 |
| 9: headers_over differential + tag-stripped | 27 | 3 | 21 bodies with no divergence; 3 display:none failures are probe artefacts (a lawful `unknown_table:t4`) |
| 10: R136 tamper sweep | 13 | 0 | plus the batch 6 event_id record (passes, recorded) |
| 11: R134 fuzz | 74 | 1 | N2 (NBSP + space) |

## EVIDENCE
- HEAD: `git rev-parse HEAD` gives 80bd14fce4a5e4b3c38c5b3817a1453e4b6f8d48.
- `git diff --stat 36beacf3da1 80bd14fce4a5e4b3c38c5b3817a1453e4b6f8d48 -- tests/ research/ .github/` prints nothing (0 lines).
- `git diff --stat 36beacf3da1 80bd14fce4a` touches only two files, which confirms the lane's claim:
  - `engine/company_intelligence/economic_observations.py` (137 lines);
  - `engine/company_intelligence/pg_envelope.py` (296 lines).
- Suites (`runs.sh`, `PYTHONPATH=.`, `-p no:cacheprovider`):
  - `tests/test_pg_envelope_f1.py`: 3.12 (venv312_min) gives `46 passed, 88 warnings in 21.69s`; 3.14 gives `46 passed ... in 28.98s`.
  - `tests/test_pg_envelope_f1_probes_r1.py`: 3.12 gives `125 passed ... in 68.10s`; 3.14 gives `125 passed ... in 103.30s`.
  - `tests/test_pg_envelope_f1_probes_r2.py`: 3.12 gives `70 passed ... in 44.25s`; 3.14 gives `70 passed ... in 44.16s`.
  - The gate line (legacy-jobs.yml `earnings-economic-dossier`, extracted verbatim to `gate_cmd.txt` and run through `bash -c`):
    - 3.12: `1065 passed, 174 skipped, 81 warnings in 217.57s`;
    - 3.14: `1065 passed, 174 skipped ... in 110.30s`.
  - `tests/test_ci_pack.py -k curated_exclusive` on 3.12 gives `2 passed, 119 deselected`.
  - a5a plus the four capital-structure suites on /opt/homebrew/bin/python3.12 give `213 passed, 80 warnings in 44.53s`.
    - The sorted `-rA` lines (`a5a_cs.txt`) against `baseline_a5a_cs_f8e4af5.txt` give an empty `diff`, rc=0.
- The lane's suite counts are confirmed: F1 46, R1 125, R2 70, gate 1065/174, curated 2, a5a/cs 213 identical.
- Runtime purity: `pg_envelope.py` imports `dataclasses`, `datetime`, `functools`, `html`, `re` and `typing`, plus engine modules.
  - It reads no file or fixture and makes no network call.
  - It mints no absence reason.
- Probe runs: batches 1–6 as logged; the full file is in `probes_full.log` (count below).

## GAPS
- Refused-document tamper sweep ran on FY26 Q2 (EX-99.2 relabel) only; present/unlocated/conflict/excluded kinds on all three quarters.
- N6 and N7 depend on seat rulings: two contradictory year headers, and the fiscal-year label class. Neither case is addressed by R124, R125 or R132 as written.
- N8 rests on R116's "among all `<table` start tags". The witness `tables()` raises on this input, so it cannot adjudicate it.
- Hosted CI was not observed; only local 3.12 and 3.14 runs.
- N1 and N2 were probed in the four pinned-cell classes (EPS primary, EPS second, percent primary, percent second). The same `_receipt` code serves every present metric.
- Tag-stripped semantics remain a shared known limit (R131). Hidden text counts as printed, consistently.

## DEVIATIONS
- The first continuation ended before anything was written to disk. That work was re-run.
- One batch-2 probe used the witness `after_table` on a nested-table body, where the witness raises. It was corrected to the engine span list and re-run in batch 3.
- The three display:none probes in family 9 were written too narrowly: they did not admit a lawful refusal. They are marked as artefacts, not findings.
- The lane's testimony is confirmed on counts, files touched and frozen byte-identity. It is not confirmed on three points:
  - "GAPS: None";
  - "No R136 field is exempt": event_id and document_id are workspace-carried, as in S0;
  - the implied completeness of R135 and R134 (N1, N2).

## Full probe file at 80bd14fce4a (venv_t1 3.14, `probes_full.log`)
`36 failed, 188 passed, 1 skipped in 906.73s`. Failures by test:
- N1/N2: 17
- N3: 1
- N4: 5
- N5: 3
- N6: 2
- N7: 3
- N8: 1
- f11 fuzz: 1 (N2 via NBSP + space)
- f9 display:none: 3 (probe artefacts; the engine gives the lawful `unknown_table:t4`)

That leaves 33 finding-bearing failures. Every blocker and major has at least one probe that fails at this head.
