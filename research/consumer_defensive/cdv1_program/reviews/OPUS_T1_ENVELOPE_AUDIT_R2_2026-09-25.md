# Opus re-audit R2: CDV-1 T1 F1-Q envelope at 5add1e2eefc492227dde578c0cc2f28605b745f2 (PR #7905)

Mode: READ_ONLY. Nothing in the repository was edited, committed or pushed. PR state was not touched.
Bar: the commission's review standard (a)-(f), under R116-R121 and R122-R131.
Probe file: `test_envelope_audit_probes_r2.py` (this directory). Each case asserts the outcome the bytes and rulings require, so a failing case is a finding.
Probe run (Python 3.14, venv_t1, one invocation): **42 failed, 26 passed** (`probes_r2.log`).

## STATUS: REJECT

Blockers remain on bars (a), (b), (c), (d) and (e).
- Every round-1 construction is closed. The re-run of the round-1 file went from 43 failed to 4. Three of the four are the probe artefacts round 1 already named. The fourth is a white-box control that now fails, and it corroborates B2 below.
- The frozen suites are green on 3.12 and 3.14.
- The gate line is green.
- The a5a and capital-structure suites match the f8e4af5aa4c baseline test by test. The counts are in EVIDENCE.
- The new attacks break R124 (period titles), R125 (duration folding), R123 (receipt span and validator completeness), R122 (wrapper whitespace), and the R116 check order.

## Findings

Each finding lists its bar and severity, then the probe (all in `test_envelope_audit_probes_r2.py`), what was observed, what was expected, and the code.

### B1: range title validates only the end month (YTD titles bind as the quarter)
- **Bar and severity:** b / a, blocker. This confirms the seat's hypothesis.
- **Probe:** `test_sp_range_title_must_span_the_quarter[*]`, 7 of 7 failed across FY26 Q1, Q2 and Q3.
- **Observed:** a title of "July - March 2026", "October - March 2026" or "Foo - March 2026" over the segment drivers binds all 7 total metrics with period 2026-03-31. "July - December 2025" does the same in FY26 Q2's segment drivers and organic reconciliation, and "April - September 2025" in FY26 Q1. The validator accepts each workspace.
- **Expected:** envelope_unlocated.
- **Code:**
  - `pg_envelope.py:721-726` reads only `group(2)` (the end month) and the year. The start month is neither a month check nor a three-month span check.
  - `pg_envelope.py:748` compares month and year only.
  - The folding at `pg_envelope.py:119` sends every "<word>-<word>20xx" to `<period>`, so admission holds.

### B2: nine- and twelve-month titles fold onto the three-month class (R125), and the R124 fallback lets a moved quarter title re-govern them
- **Bar and severity:** b, blocker.
- **Probes:**
  - `test_r125_duration_word_survives_folding[*]` (3 of 3 failed): a Q3 earnings title of "Twelve Months Ended March 31" or "Nine Months Ended March 31", or a Q1 prior-core title of "Twelve Months Ended September 30, 2024", is admitted. The expected outcome is `unknown_table:t4` or `t11`.
  - `test_r124_nine_month_title_over_cell_with_moved_quarter_title[Q2,Q3]` (2 of 2 failed): the earnings title is changed to "Nine Months Ended ..." and "Three Months Ended ..." is added as a bottom row. The engine then binds DIL, PDIL and REPG under a nine-month title: 1.63, 1.54 and 6.0 in Q3, and 1.78, 1.88 and -5.0 in Q2. The validator accepts.
- **Code:**
  - `pg_envelope.py:113-118` replaces the whole `(?:three|six|nine|twelve)monthsended…` match, including the duration word, with `three<period>` or `<period>`.
  - `pg_envelope.py:692-705`: `_period_titles` ignores any non-parsing text over the cell. The nine-month title is invisible, so governance falls back to the table's other title.
  - `_parse_period_title` (`:709-712`) knows only "Three Months Ended".
  - Corroboration: the round-1 white-box control `test_f10_control_q4_tables_match_no_f1q_role_beyond_masthead` now fails. FY25Q4's t3, t13, t14, t17 and t19 (including a fiscal-year organic reconciliation) match F1-Q roles. The F2-A refusal now rests only on the other unknown tables.

### B3: month/day title — the day is never compared when the year is printed
- **Bar and severity:** b, blocker.
- **Probe:** `test_r124_month_day_title_day_must_match[*]`, 4 of 4 failed.
- **Observed:**
  - A Q3 core-reconciliation title of "…March 30, 2026" or "…March 1, 2026" binds CORE = 1.59.
  - A Q2 title of "…December 1, 2025" binds CORE = 1.88.
  - A Q1 prior-core title of "…September 1, 2024" binds PCORE = 1.93.
- **Expected:** unlocated (R124: "Its month and day are those of the period end").
- **Code:** `pg_envelope.py:748`, `return title.month == period.month and title.year == period.year`. The day is checked only in the no-year sentinel branch at `:744-747`.

### B4: validator accepts a receipt span wider or narrower than the printed literal
- **Bar and severity:** c, blocker (R123).
- **Probe:** `test_r123_span_one_step_wider_or_narrower_is_refused[*]`, 6 of 7 failed. The one-byte-left-into-tag case is refused.
- **Observed:** the validator accepts the Q1, Q2 and Q3 DIL spans and the Q3 CORE span when widened by 6 bytes over the trailing `&#160;`. It also accepts the Q1 and Q3 SALES spans narrowed to drop the `%`. In each case display_excerpt, text_sha256 and the locator and receipt bytes were recomputed consistently.
- **Expected:** EconomicObservationError.
- **Code:** `economic_observations.py:284-291` checks only that the span lies inside the primary cell and that `_literal(_text(span)) == value`. `_text` strips tags and entities-as-spaces, and `%` is optional in the grammar. The span is never compared with the envelope's re-derived receipt.

### B5: validator does not hold typed-absence `subject` to the envelope outcome
- **Bar and severity:** c, blocker.
- **Probes:** `test_r123_absence_subject_suffix_is_refused[FY26Q1,Q2,Q3]` and `test_r123_refused_document_subject_suffix_is_refused` (4 of 4 failed).
- **Observed:** subject `"<metric> (forged)"` or `"<metric>_x"` is accepted, on admitted and refused documents alike.
- **Code:**
  - The wrapped branch relies on `_validate_row_structure` (`economic_observations.py:178`), which checks only `startswith(metric)`.
  - `_validate_envelope_rows` (`:296-309`) checks reason, detail, event_id and document_id, but never `subject == metric`.
  - R123 requires "every typed-absence key" to equal the re-derived outcome.

### B6: wrapped branch drops S0's "every fact names a metric" check
- **Bar and severity:** c, blocker (R123 "every structural check the S0 path makes").
- **Probe:** `test_r123_fact_without_metric_is_refused_as_s0_refuses` failed.
- **Observed:** a facts entry `{"schema": "event_fact.v1", "value": 9.99}` is accepted.
- **Expected:** refused, as the S0 path refuses it at `:438`.
- **Code:** `economic_observations.py:421-429` filters to `pg_` rows before any such check.

### B7: receipt span is not the printed literal when an entity precedes it; the extractor's own output is refused by its own validator
- **Bar and severity:** a, blocker (R123).
- **Probe:** `test_r123_entity_before_dash_literal_span_is_the_literal` failed.
- **Observed:** with `&#160;` before FY26 Q2's highlights `&#8212;%`, COREG binds 0.0 with display_excerpt `'#160;&#8212;%'`, a span starting mid-entity. `validate_selected_facts` then refuses that same workspace.
- **Code:** `pg_envelope.py:924-938`.
  - `char_start = cell.start + len(prefix) + (literal_start - len(prefix))` reduces to decoded-coordinate `literal_start`, which is used as a raw offset.
  - The end is "the next `%` after the first `;`", which hard-codes the `&#…;%` shape.

### B8: exceptions escape the envelope on an admitted document
- **Bar and severity:** d / R122 / R130. Blocker: R122 says "an exception inside the envelope is a defect". It is not a legacy route.
- **Probes:**
  - `test_r122_r130_unparseable_title_is_not_an_exception[*]` (3 of 3 failed). An earnings title of "Three Months Ended Marhc 31" or "…Foo 1" raises `ValueError: list.index` (`pg_envelope.py:734`). "…February 30" raises `ValueError: day 30 must be in range` (`:720`). The no-year branch at `:720` is unguarded, while the year branches at `:716-719` and `:723-726` wrap reading in `try/except ValueError`, which R130 forbids.
  - `test_r123_interrupted_or_entity_literal_never_raises[1.6<b></b>3, 1&#46;63]` (2 of 2 failed) raises `ReceiptError` (`pg_envelope.py:927`, `:933`). R123 says a literal interrupted by markup "is not located". An entity counts as a character, so `1&#46;63` should bind with a span over those characters, or at least not raise.
- **Seat pointer ruling:** an unknown month or impossible date reaches "not a title" only in the year-bearing forms, and only through a forbidden try/except. In the no-year form it raises out of `build_event_workspace`.
- `_parse_period_title` is also case- and whitespace-exact. The variants tested (lower case, upper case, double space, `&#160;`, `<br/>`) never mis-bind: they fall back or unlocate (control passed).

### B9: nested-table check runs before checks 2 and 3, and preempts earlier unknown tables
- **Bar and severity:** e, blocker (check order differs from R116/R129).
- **Probes:**
  - `test_r116_order_generator_before_nested_table` gives `unknown_table:t11`; `generator_not_workiva` was expected.
  - `test_r116_order_issuer_before_nested_table` gives `unknown_table:t11`; `issuer_not_pg` was expected.
  - `test_r116_first_unknown_in_document_order_with_later_nested` gives `unknown_table:t12`; `unknown_table:t7`, the first unmatched table in document order, was expected.
- **Code:** `pg_envelope.py:626-628` runs before the generator (`:629`), masthead (`:631`) and signature (`:634`) checks.
- All three are still refusals, but the codes are wrong and the validator will demand the same wrong code.

### B10: wrapper detection excludes form feed and vertical tab
- **Bar and severity:** d. Blocker if R122's "leading whitespace" includes them; the seat must adjudicate. FF is whitespace under both Python and HTML/WHATWG.
- **Probe:** `test_r122_other_whitespace_before_document_is_wrapped[\x0c, \x0b, ﻿\x0c]`, 3 of 3 failed.
- **Observed:** every row carries the legacy details ("No unique heading, row label…"). No present value was bound.
- **Code:** `pg_envelope.py:228`, `lstrip("﻿ \t\r\n")`.

### B11: S0 validator behaviour changed
- **Bar and severity:** d, blocker by letter. The change is in the safe direction (it tightens), and the seat may ratify it.
- **Probe:** `test_d_s0_validator_missing_fields_tamper_outcome_unchanged`. This is a differential against `e1dd9caa3fa`'s economic_observations, loaded from `eo_base_e1dd9caa3fa.py`.
- **Observed:** an S0 typed absence with `missing_fields=["basis"]` is now refused (EconomicObservationError). The base validator accepted it.
- **Code:** the S0 path now calls `_validate_fact_structure` and then `_validate_row_structure`, which adds `missing_fields == ()` at `economic_observations.py:180-181`. Base S0 never checked it. R123's premise that "S0 checks missing_fields" was not true of the base.
- The same refactor reorders which error fires first. For example, a bool value is now reported before a bad fact_id. Refusal sets are otherwise the same by reading.

### M1: a second TYPE line that is indented is not counted
- **Bar and severity:** b, minor. This is F-B2's class; F-B2 was minor in round 1.
- **Probe:** `test_r122_indented_second_type_line_refused`.
- **Observed:** a header of `<TYPE>EX-99.1\n <TYPE>EX-99.2` is admitted with all values.
- **Code:** `pg_envelope.py:623`, the regex `(?im)^<TYPE>` anchors at column 0.

### M2: the literal grammar ignores the unit marker
- **Bar and severity:** a (unit), major. R128's grammar allows an optional `%` on any metric, so the seat must rule.
- **Probe:** `test_r128_percent_marked_eps_never_binds_usd`.
- **Observed:** an EPS primary printed "1.63%" binds 1.63 usd_per_share (the second statement "1.63" agrees).
- **Code:** `pg_envelope.py:814-825`.

### Minor / code quality (R130)
- `admit()` still builds and discards a `Document` (`pg_envelope.py:611`). R130 names this for removal. `_labels` (`:232`) and `_OTHER_ROLES` (`:52`) are unused, and so is the `_scope` import in `_prior_note_present` (`:891`).
- `try/except ValueError` sits inside the envelope's own title reading (`:716-719`, `:723-726`), as described in B8.
- The core versus prior-core split is not "anchors alone". `_match_role` (`:586-600`) swaps the core anchor set on the presence of a token and excludes prior-core by a currency-token rule. The prior-core vocabulary (`:417-426`) still lists the currency tokens that the rule excludes. The outcome is correct on the originals, but it is a rule outside the signature.
- The balance-sheet vocabulary keeps literal month names (`'march<n>,<period>'`, etc., `:475-486`), which is a literal date part (R125). There is no admission effect within F1-Q, because the four quarter-end months are enumerated.
- The segment and organic vocabularies carry `'january-march<period>'` and similar entries (`:270-276`, `:390-393`). They are dead, because `:119` folds these titles to `<period>` first.
- `_year_over` and the sentinel: a full-form title with year 2000 is read as the no-year form (`:744`). No live path was found, because vocabulary gates the earnings table.
- `current_end.strftime("%B %-d, %Y")` (`:652`) is platform-dependent (`%-d` fails on Windows).
- The engine grid reader still mirrors the suite's `grid()`. `_headers_over` has diverged from the suite's `headers_over`: it uses own cells only and adds a single-cell branch and a period-title branch, so the witness no longer checks the engine's header logic. The shared defects this can hide are all tag-stripped text semantics (hidden text, comments with tags), rowspan-carried header handling, and the substring footnote test. B1-B3 are exactly the kind of engine-only header/title logic the frozen witness cannot see.

## Round-1 findings: closure (round-1 probe file re-run at the head)

`../audit_t1_envelope/test_envelope_audit_probes.py` gives **4 failed, 99 passed**. At c6bebf3 it gave 43 failed and 60 passed. Log: `probes_r1_rerun.log`.

- **Closed:** F-D1, F-C1, F-C2, F-A1, F-E1, F-E2, F-B1, F-F1, F-F2, F-B2, F-M1, F-M2, F-M3 and F-M4. All 39 of the finding-bearing failures now pass.
- **Still failing, all accounted:**
  - `test_f4_non_number_in_both_eps_statements_is_unlocated[2.0 pts]` and `[— per share]`: probe artefacts, as in round 1 (the document is lawfully refused `unknown_table:t2`).
  - `test_f7_drivers_title_date_removed`: probe artefact, as in round 1 (`unknown_table:t6`, the correct R116 order).
  - `test_f10_control_q4_tables_match_no_f1q_role_beyond_masthead`: newly failing. It is a white-box control that R131 removed from the frozen suite, but it corroborates B2: F2-A tables now fold onto F1-Q roles.
- The variants carried in R2 on Q1 and Q2 also hold: cross-table swaps, duplicate labels, year-header swaps, footnote removal and value forgery (see the controls below).

## Probes run / failed per attack family (R2 file: 68 run, 42 failed)

| family | run | failed | notes |
|---|---|---|---|
| SP seat pointers (range titles, Q1-Q3) | 7 | 7 | B1 |
| R124 titles (day, nine-month fallback, moved title, variants, two titles, range in untitled table) | 16 | 6 | B3 ×4, B2 ×2; controls 11 pass: moved-only, 5 spelling variants, two-titles, range in highlights ×3 |
| R125 duration folding | 3 | 3 | B2 |
| R122/R130 exceptions | 5 | 5 | B8 |
| R123 validator (span ±, subject, no-metric, Q1/Q2 value forgery) | 14 | 11 | B4 ×6, B5 ×4, B6; controls: one-byte-into-tag refused, Q1/Q2 value forgery refused |
| R123 receipt span | 1 | 1 | B7 |
| R122 wrapper (FF/VT, indented TYPE, TYPE after TEXT) | 5 | 4 | B10 ×3, M1; TYPE-after-TEXT control passes |
| R116/R126/R127/R129 order and multiplicity | 7 | 3 | B9 ×3; controls: unread table removed/repeated Q2/Q3, Q2 plus Q1 prior-core table, Q1 without prior-core refused |
| R130 EPS rows / R128 unit | 2 | 1 | M2; the two-EPS-row plus unlabelled-cell case stays unlocated |
| Q1/Q2 sweep, families 1-3 and 8 | 7 | 0 | cross-table swap, duplicate label and year-header swap each on Q1 and Q2; Q2 note removed |
| bar d S0 differential | 1 | 1 | B11 |

## Required evidence
(Counts are filled in below, from the logs in this directory.)

All runs are from the worktree root with `PYTHONPATH=.` and `-p no:cacheprovider`, at HEAD `5add1e2eefc`. The run script is `runs.sh`.

**Frozen files.** `git diff --stat f8e4af5aa4c 5add1e2eefc -- tests/ research/` prints nothing, so the frozen files are byte-identical.
- `git log f8e4af5aa4c..5add1e2eefc` shows three commits: 5584da955c7, 6fe10734f76 and 5add1e2eefc.
- `git diff --stat` over the same range touches only `pg_envelope.py`, `pg_profile.py` and `economic_observations.py`.

**Test runs.**

| run | log | result |
|---|---|---|
| `tests/test_pg_envelope_f1.py` on 3.12 (venv312_min: pytest and pyyaml only) | `f1_312.log` | 46 passed |
| `tests/test_pg_envelope_f1.py` on 3.14 | `f1_314.log` | 46 passed |
| `tests/test_pg_envelope_f1_probes_r1.py` on 3.12 | `r1_312.log` | 125 passed |
| `tests/test_pg_envelope_f1_probes_r1.py` on 3.14 | `r1_314.log` | 125 passed |
| Gate run line, `earnings-economic-dossier` (legacy-jobs.yml), on 3.12 | `gate_312.log` | 995 passed, 174 skipped, in 102.97s |
| Gate run line on 3.14 | `gate_314.log` | 995 passed, 174 skipped, in 148.29s |
| `tests/test_ci_pack.py -k curated_exclusive`, on 3.12 | `curated.log` | 2 passed, 119 deselected |
| a5a plus the four capital-structure suites, on /opt/homebrew python3.12 | `a5a_cs.raw` | 213 passed |

- The a5a and capital-structure result, as sorted `-rA` lines (`a5a_cs.txt`), is identical to `baseline_a5a_cs_f8e4af5.txt`. `diff` is empty (`a5a_cs.diff`).

**Runtime purity.** `pg_envelope.py` imports only stdlib modules (`dataclasses`, `datetime`, `functools`, `html`, `re`, `typing`) and engine modules. It reads no fixture, no file and no network. No absence reason was minted.

**Probe runs.**
- R2 probe file: 42 failed, 26 passed, in 24.34s (`probes_r2.log`).
- Round-1 probe file re-run: 4 failed, 99 passed (`probes_r1_rerun.log`).

## GAPS

- **Engine and witness readers.** Both still share tag-stripped cell semantics, so hidden text and comments holding tags were not probed. `_headers_over` has now diverged from the suite's reader. I did not run a full engine-versus-witness differential sweep over rowspan geometry on Q1/Q2, only the three family-3 constructions.
- **Unread tables.**
  - The F2-A-to-F1-Q fold (family 4) was shown white-box only (B2 corroboration). I did not build a doctored Q4 that clears every unknown table.
  - Label-only and label-free tables were not re-probed in R2; the frozen R1 suite covers them.
- **Other gaps.**
  - Hosted CI was not observed.
  - B10's severity depends on the seat's reading of "whitespace" in R122.
  - B11 is a safe-direction change, which the seat may ratify.
  - M2 depends on R128's grammar.
- **Not probed:** the R118 primary bare "—" beside a "%" cell, and the `_eps_row` empty-label path with a labelled second EPS row plus unlabelled cells in other columns. The one construction probed stayed unlocated.

## DEVIATIONS

- **First batch of runs.** My first background batch mis-built the gate command, and its gate log was discarded. The re-run (`runs.sh`) is the evidence.
- **B11 differential.** The probe loads the base `economic_observations.py` from `git show e1dd9caa3fa` into a scratch module (`eo_base_e1dd9caa3fa.py`), in memory. No repository file changed.
